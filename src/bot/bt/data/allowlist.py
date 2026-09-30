"""What the data layer may read: the allow-list and the seal records.

Default deny. A path is read only when BOTH its written form (normalised,
`..` resolved lexically) and its real form (every symlink resolved) lie
under one of the allowed roots of the data root, and no component of either
form matches a refused pattern. The refused patterns always include the
mandatory set below (they cannot be removed; a caller may add more):

  qa_*            synthetic known-answer packets (docs/DATA.md section 6,
                  CLAUDE.md section 2: not market data)
  o3c_*           research intermediates (CLAUDE.md section 2). A raw
                  dataset whose name merely CONTAINS o3c (binance_cm_o3c_*)
                  is not refused: the pattern matches a component's start
  phase2_runs     research run outputs (docs/DATA.md section 6)
  phase2_sealed   the seal ledger itself (not data)

Components are compared case-insensitively (QA_x is refused too).

Seals: every ``backtest_data/phase2_sealed/<unit>/SEALED.json`` under the
data root is read (the same records `bot.research.sealed.load_sealed`
guards). A file listed there may be read only with an explicit time range
whose end is at or before its cutoff = min(seal_from_ts, forward_start)
(the half-open range [start, end) then holds no sealed row), AND every row
kept must have its value in the SEAL's time column before the cutoff, read
as the seal read it (`seal_time_ns`; e.g. a JPX bar at 08:45 JST on a date
the seal counts as sealed is refused although its UTC time is the evening
before). A row whose seal time cannot be read is refused.
Limits: `forward_start` is applied to the files the seal record lists (not
to every dataset of the unit, which the layer cannot name); an edited copy
of a sealed file is another file. A file is recognised
as sealed by its real path, and also by its bytes (a copy of a sealed file
under another name has the same size and the same bytes).

What is read before a refusal (round 2 of the k1 env fixes, 2026-09-27): the
one door is `SealRegistry.read_checked(real, given, range_ns)`, which returns
a file's bytes only after the seals allowed them. A file the seal record
names by its real path is refused BEFORE it is opened (0 bytes read). A file
under another name can be a copy only if its size (os.stat, no read) equals a
sealed file's size; only such a file has its bytes hashed and compared before
they are handed on, and the comparison is with the digest the seal record
wrote (`md5`), so the sealed file itself is not opened. A seal entry without
an `md5` is compared with the sha256 of the sealed file's bytes (the sealed
file is then read; no ledger in backtest_data/phase2_sealed lacks it on
2026-09-27). A copy of a sealed file edited after the seal record was
written is not recognised by bytes (the record names the bytes it sealed).
A copy has to be read whole to be recognised (a digest of the whole file is
all the record holds), but its bytes are never decoded or parsed before the
refusal. A seal record that cannot
be read makes every load refuse (fail closed: the layer cannot tell which
files are sealed). Reading the sealed window itself goes through
`load_sealed`'s gates only; this layer has no way to do it.
"""
from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import re
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from typing import Iterable, Optional

from ..core.errors import TimestampUnitError
from ..core.time import to_nanos
from .errors import PathRefused, SealedRangeError

DEFAULT_ROOTS: tuple[str, ...] = ("backtest_data", "data", "paper_logs/tape")
MANDATORY_DENY: tuple[tuple[str, str], ...] = (
    ("qa_*", "synthetic known-answer data (qa_*)"),
    ("o3c_*", "research intermediate (o3c_*)"),
    ("phase2_runs", "research run outputs (phase2_runs)"),
    ("phase2_sealed", "the seal ledger (phase2_sealed)"),
)
SEAL_DIR = ("backtest_data", "phase2_sealed")


def _parts(rel: str) -> list[str]:
    return [p for p in rel.replace(os.sep, "/").split("/") if p not in ("", ".")]


@dataclass(frozen=True)
class CheckedPath:
    given: str  # as the caller wrote it
    abs_lexical: str
    real: str  # every symlink resolved
    rel_real: str  # relative to the real data root


class AllowList:
    def __init__(self, roots: Iterable[str] = DEFAULT_ROOTS,
                 extra_deny: Iterable[tuple[str, str]] = ()) -> None:
        roots = tuple(roots)
        if not roots:
            raise PathRefused("an allow-list needs at least one root")
        self.roots = tuple(tuple(_parts(r)) for r in roots)
        for r in self.roots:
            if not r or ".." in r:
                raise PathRefused(f"allow-list root {r!r} must be a plain relative path")
        extra = tuple((str(p), str(why)) for p, why in extra_deny)
        self.deny = MANDATORY_DENY + extra

    def _refused_by(self, parts: list[str]) -> Optional[str]:
        for comp in parts:
            low = comp.lower()
            for pat, why in self.deny:
                if fnmatch.fnmatchcase(low, pat.lower()):
                    return f"{why}: component {comp!r}"
        return None

    def _under_root(self, parts: list[str]) -> bool:
        return any(tuple(parts[:len(r)]) == r and len(parts) > len(r) for r in self.roots)

    def check(self, root: str, path: str) -> CheckedPath:
        if type(path) is not str or not path:
            raise PathRefused(f"a data path must be a non-empty str, got {path!r}")
        root_real = os.path.realpath(root)
        root_abs = os.path.abspath(root)
        abs_lex = os.path.normpath(path if os.path.isabs(path) else os.path.join(root_abs, path))
        # the written form, relative to the root as written (or as resolved:
        # a caller may pass an absolute path through the root's real name)
        rel_lex = None
        for base in (root_abs, root_real):
            r = os.path.relpath(abs_lex, base)
            if not (r == ".." or r.startswith(".." + os.sep)):
                rel_lex = r
                break
        if rel_lex is None:
            raise PathRefused(f"{path!r} is outside the data root")
        real = os.path.realpath(abs_lex)
        rel_real = os.path.relpath(real, root_real)
        if rel_real == ".." or rel_real.startswith(".." + os.sep):
            raise PathRefused(f"{path!r} resolves to {real!r}, outside the data root")
        for form, rel in (("written", rel_lex), ("real", rel_real)):
            parts = _parts(rel)
            why = self._refused_by(parts)
            if why:
                raise PathRefused(f"{path!r} refused ({form} path {'/'.join(parts)}): {why}")
            if not self._under_root(parts):
                allowed = ["/".join(r) for r in self.roots]
                raise PathRefused(f"{path!r} ({form} path {'/'.join(parts)}) is not under an allowed root {allowed}")
        if not os.path.isfile(real):
            raise PathRefused(f"{path!r} is not a regular file")
        return CheckedPath(path, abs_lex, real, rel_real)


DEFAULT_ALLOWLIST = AllowList()


@dataclass(frozen=True)
class SealEntry:
    unit: str
    path: str  # as the seal record writes it (relative to the data root)
    real: str
    time_column: str
    cutoff_ns: int
    md5: Optional[str] = None  # the digest the seal record wrote of the sealed bytes


class SealRegistry:
    """The seal records under one data root, read once per load."""

    def __init__(self, root: str) -> None:
        self.root = root
        self.entries: list[SealEntry] = []
        self.records_read: dict[str, str] = {}  # seal record path -> sha256
        self._by_real: dict[str, SealEntry] = {}
        self._by_size: dict[int, list[SealEntry]] = {}
        self._hash_cache: dict[str, Optional[str]] = {}
        base = os.path.join(os.path.realpath(root), *SEAL_DIR)
        if not os.path.isdir(base):
            return
        for unit in sorted(os.listdir(base)):
            rec = os.path.join(base, unit, "SEALED.json")
            if not os.path.exists(rec):
                continue
            try:
                with open(rec, "rb") as fh:
                    raw = fh.read()
                self.records_read[rec] = hashlib.sha256(raw).hexdigest()
                data = json.loads(raw.decode("utf-8"))
                fwd = self._iso(data["forward_start"], rec, "forward_start")
                files = data["files"]
                if not isinstance(files, list):
                    raise ValueError("'files' is not a list")
                for i, e in enumerate(files):
                    p, col = e["path"], e["time_column"]
                    if type(p) is not str or type(col) is not str or not p or not col:
                        raise ValueError(f"files[{i}] path/time_column must be non-empty str")
                    cut = min(self._iso(e["seal_from_ts"], rec, f"files[{i}].seal_from_ts"), fwd)
                    real = os.path.realpath(os.path.join(root, p))
                    md5 = e.get("md5")
                    if md5 is not None and (type(md5) is not str or not re.fullmatch(r"[0-9a-f]{32}", md5)):
                        raise ValueError(f"files[{i}].md5 must be 32 lowercase hex digits")
                    ent = SealEntry(str(data.get("unit", unit)), p, real, col, cut, md5)
                    self.entries.append(ent)
                    self._by_real[real] = ent
            except SealedRangeError:
                raise
            except Exception as exc:  # noqa: BLE001 -- any unreadable record fails closed
                raise SealedRangeError(
                    f"seal record {rec} cannot be read ({type(exc).__name__}: {exc}); refusing every "
                    f"load under this root until it is readable") from None
        for ent in self.entries:
            try:
                size = os.stat(ent.real).st_size
            except OSError:
                continue
            self._by_size.setdefault(size, []).append(ent)

    @staticmethod
    def _iso(value, rec: str, where: str) -> int:
        try:
            return int(to_nanos(value, "iso"))
        except TimestampUnitError as exc:
            raise SealedRangeError(f"seal record {rec}: {where}: {exc}") from None

    def _sealed_sha256(self, ent: SealEntry) -> Optional[str]:
        """The sha256 of a sealed file's bytes: only for an entry whose record has no md5 (reads the sealed file)."""
        if ent.real not in self._hash_cache:
            try:
                with open(ent.real, "rb") as fh:
                    self._hash_cache[ent.real] = hashlib.sha256(fh.read()).hexdigest()
            except OSError:
                self._hash_cache[ent.real] = None
        return self._hash_cache[ent.real]

    def by_path(self, real: str) -> Optional[SealEntry]:
        """The seal entry naming this real path (no file is opened)."""
        return self._by_real.get(real)

    def read_checked(self, real: str, given: str,
                     range_ns: Optional[tuple[int, int]]) -> tuple[bytes, Optional[SealEntry]]:
        """The one door to a data file's bytes: (bytes, the seal entry covering the file or None).
        A file the seal record names by path is refused before it is opened; a file of a sealed file's size is
        compared by its bytes before they are returned (see the module docstring). `check_range` refuses a sealed
        file read without a range that ends at or before its cutoff."""
        ent = self._by_real.get(real)
        if ent is not None:
            self.check_range(ent, given, range_ns)  # before any byte is read
        with open(real, "rb") as fh:
            size = os.fstat(fh.fileno()).st_size
            cands = () if ent is not None else self._by_size.get(size, ())
            raw = fh.read()
        if cands:
            md5 = hashlib.md5(raw).hexdigest()
            sha = None
            for cand in cands:
                if cand.md5 is not None:
                    hit = cand.md5 == md5
                else:
                    sha = sha or hashlib.sha256(raw).hexdigest()
                    hit = self._sealed_sha256(cand) == sha
                if hit and len(raw) == size:
                    ent = cand
                    break
            if ent is not None:
                try:
                    self.check_range(ent, given, range_ns)
                except SealedRangeError:
                    del raw
                    raise
        return raw, ent

    @staticmethod
    def check_range(ent: SealEntry, given: str, range_ns: Optional[tuple[int, int]]) -> None:
        if range_ns is None:
            raise SealedRangeError(
                f"{given!r} is sealed (unit {ent.unit}) from {ent.cutoff_ns} ns; give range_ns with an "
                f"end at or before it (the sealed window is read only through load_sealed's gates)")
        if range_ns[1] > ent.cutoff_ns:
            raise SealedRangeError(
                f"{given!r}: range end {range_ns[1]} ns is after the seal cutoff {ent.cutoff_ns} ns "
                f"(unit {ent.unit}); the half-open range would reach sealed rows")


_YYYYMMDD = re.compile(r"^\d{8}$")
_NUMBER = re.compile(r"^[+-]?(\d+(\.\d*)?|\.\d+)$")


def seal_time_ns(value) -> Fraction:
    """A cell of a seal's time column, read the way the seal was made
    (`bot.research.sealed.parse_ts`: YYYYMMDD and ISO without an offset are
    UTC; a bare number is epoch seconds / ms / us by its magnitude), but
    exactly (no float) and strictly: what cannot be read is refused, since
    a row whose seal time is unknown is not known to be before the seal."""
    text = value.strip() if type(value) is str else (str(value) if type(value) in (int, Decimal) else None)
    if not text:
        raise SealedRangeError(f"seal time {value!r} cannot be read")
    try:
        if _YYYYMMDD.match(text):
            return Fraction(int(to_nanos(f"{text[:4]}-{text[4:6]}-{text[6:]}T00:00:00Z", "iso")))
        if _NUMBER.match(text):
            v = Fraction(Decimal(text))
            a = abs(v)
            factor = 10**3 if a >= 10**15 else 10**6 if a >= 10**12 else 10**9 if a >= 10**8 else None
            if factor is None:
                raise SealedRangeError(f"seal time {value!r}: a number below 1e8 is no epoch time")
            return v * factor
        from .timestamps import TimeReader
        return Fraction(TimeReader("iso", "UTC", (-(2**63), 2**63 - 1)).read(text))
    except SealedRangeError:
        raise
    except Exception as exc:  # noqa: BLE001 -- any unreadable seal time fails closed
        raise SealedRangeError(f"seal time {value!r} cannot be read: {exc}") from None
