"""The one reading door of the backtest data layer (item 1).

    result = load(root, datasets, allowlist=DEFAULT_ALLOWLIST)

`root` is the data root (the repository root in normal use). `datasets` is a
list of mappings, one per dataset:

    {"name": str, "paths": [path, ...], "spec": {...}, "range_ns": [lo, hi]}

`paths` are relative to `root` (or absolute under it); two or more paths make
ONE dataset whose files are generations / pieces of the same series.
`spec` is the declaration (spec.py) -- the same door reads every asset of
every market (crypto trades / books / funding / liquidations, FX quotes, JPX
bars) by its declaration, with no reader per source. `range_ns` (optional)
keeps rows in the half-open range [lo, hi) (a bar is kept when its whole
interval [start, start + interval) lies inside).

Every file is checked by the allow-list and the seal records
(allowlist.py) before its bytes are used; its bytes are read ONCE, and the
sha256 recorded is of exactly those bytes (compressed, as on disk), the same
bytes that are then decompressed and parsed.

What a result offers:

* `records(name)` -- every kept row, normalised (times int64 UTC ns), in
  delivered order (files in the given order, rows in file order). Nothing is
  merged, dropped or reordered here.
* `anomalies(name)` -- what the checks found (anomalies.py), always, whether
  or not events are asked for.
* `events(name, resolve)` / `streams(resolve)` -- the core's event objects
  for `CoreEngine`. When a dataset has anomalies, every kind present must be
  named in `resolve` with a policy (anomalies.POLICIES); otherwise
  `UnresolvedAnomalyError`: the layer never merges, drops or reorders rows
  silently. The policies applied are recorded (`resolutions`).
* `files()`, `hashes()`, `manifest()` -- the record of what was read: path
  as given, real path, size, sha256, seal unit if any, and the seal records
  consulted, for the run record (item 3).

Rows are validated by the core's own event classes as they are read (price
> 0, a bar's high/low invariant, a book side's price order, ...), so a row
the core would refuse is refused here, with its file and line.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import math
import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Iterable, Mapping, Optional

from ..core.errors import EventValidationError
from ..core.events import (BarEvent, BookSnapshotEvent, Event, FundingEvent, LiquidationEvent,
                           TradeEvent)
from . import anomalies as A
from .allowlist import DEFAULT_ALLOWLIST, AllowList, SealRegistry, seal_time_ns
from .errors import DataError, ParseError, SealedRangeError, SpecError, TimeParseError, UnresolvedAnomalyError
from .spec import Spec, parse_spec

_NUM = re.compile(r"^[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?$")


@dataclass(frozen=True)
class FileRecord:
    dataset: str
    given: str
    real: str
    rel_real: str
    size: int
    sha256: str
    sealed_unit: Optional[str]
    rows_read: int
    rows_kept: int


@dataclass
class Row:
    """One kept row: its record, its core event, where it came from, and
    what the checks compare (time, key, identity)."""
    record: dict
    event: Event
    file_index: int
    line: int
    time_ns: int  # t_ns, or a bar's start
    key: Optional[Any]
    identity: tuple
    synthetic: bool = False


@dataclass
class _Dataset:
    name: str
    spec: Spec
    range_ns: Optional[tuple[int, int]]
    paths: tuple[str, ...]
    rows: list[Row] = field(default_factory=list)
    anomalies: tuple = ()
    checks: tuple = ()


def _num(value: Any, where: str) -> float:
    t = type(value)
    if t is str:
        text = value.strip()
        if not _NUM.match(text):
            raise ParseError(f"{where}: {value!r} is not a decimal number")
        f = float(text)
    elif t is int:
        f = float(value)
    elif t is Decimal:
        f = float(value)
    else:
        raise ParseError(f"{where}: {value!r} ({t.__name__}) is not a number")
    if not math.isfinite(f):
        raise ParseError(f"{where}: {value!r} is not finite")
    return f


def _text_of(value: Any) -> str:
    if type(value) is str:
        return value
    if value is None or type(value) in (bool, int, Decimal):
        return json.dumps(value) if type(value) is not Decimal else str(value)
    raise ParseError(f"{value!r} ({type(value).__name__}) is not a scalar")


def _blank(value: Any) -> bool:
    return value is None or (type(value) is str and value.strip() == "")


def _dig(obj: Any, path: str, where: str) -> Any:
    cur = obj
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            raise ParseError(f"{where}: no field {path!r}")
        cur = cur[part]
    return cur


def _without(obj: Any, paths: Iterable[str]) -> Any:
    """A deep copy of a JSON object without the given dotted leaf paths."""
    out = json.loads(json.dumps(obj, default=str))
    for p in paths:
        parts = p.split(".")
        cur = out
        for part in parts[:-1]:
            cur = cur.get(part) if isinstance(cur, dict) else None
        if isinstance(cur, dict):
            cur.pop(parts[-1], None)
    return out


class _Cells:
    """Uniform access to a row's cells, whatever the format."""

    def __init__(self, spec: Spec, row: Any, where: str, names: Optional[tuple] = None) -> None:
        self.spec, self.row, self.where, self.names = spec, row, where, names

    def get(self, col: str) -> Any:
        if self.spec.format == "jsonl":
            return _dig(self.row, col, self.where)
        if col not in self.row:
            raise ParseError(f"{self.where}: no column {col!r}")
        return self.row[col]

    def rest(self) -> Any:
        """What the row carries beyond the declared columns (compared by the
        duplicate check as written)."""
        used = set(self.spec.columns_used())
        if self.spec.format == "jsonl":
            return json.dumps(_without(self.row, used), sort_keys=True)
        return tuple((k, v) for k, v in self.row.items() if k not in used)


def _side(spec: Spec, raw: Any, where: str, allowed: tuple) -> str:
    key = _text_of(raw)
    if spec.side_map is not None:
        if key not in spec.side_map:
            raise ParseError(f"{where}: side {key!r} is not in side_map {sorted(spec.side_map)}")
        side = spec.side_map[key]
    else:
        side = key
    if side not in allowed:
        raise ParseError(f"{where}: side {side!r} must be one of {list(allowed)}")
    return side


def _build(spec: Spec, cells: _Cells, reader, where: str) -> tuple[dict, Event, int, Optional[Any]]:
    tcols = spec.time.columns
    tvals = [cells.get(c) for c in tcols]
    for c, v in zip(tcols, tvals):
        if _blank(v):
            raise ParseError(f"{where}: time column {c!r} is blank")
    if len(tvals) == 2:
        tv = f"{_text_of(tvals[0]).strip()}{spec.time.join}{_text_of(tvals[1]).strip()}"
    else:
        tv = tvals[0]
    try:
        t = reader.read(tv)
    except TimeParseError as exc:
        raise TimeParseError(f"{where}: {exc}") from None
    f = spec.fields
    k = spec.kind

    def num(name: str) -> float:
        v = cells.get(f[name])
        if _blank(v):
            raise ParseError(f"{where}: field {name!r} (column {f[name]!r}) is blank")
        return _num(v, f"{where} field {name!r}")

    try:
        if k == "trade":
            px, qty = num("px"), num("qty")
            side = _side(spec, cells.get(f["side"]), where, ("buy", "sell", "")) if "side" in f else ""
            raw_id = cells.get(f["id"]) if "id" in f else None
            tid = "" if _blank(raw_id) else _text_of(raw_id)  # blank / null id: no id (unkeyed)
            rec = {"t_ns": t, "px": px, "qty": qty, "side": side, "id": tid}
            ev = TradeEvent(received_time_ns=t, price=px, size=qty, side=side, trade_id=tid)
            key = {"id": tid or None, "time": t}.get(spec.key) if spec.key else None
            return rec, ev, t, key
        if k == "quote":
            bid, ask, bq, aq = num("bid"), num("ask"), num("bid_qty"), num("ask_qty")
            rec = {"t_ns": t, "bid": bid, "ask": ask, "bid_qty": bq, "ask_qty": aq}
            ev = BookSnapshotEvent(received_time_ns=t, bids=((bid, bq),), asks=((ask, aq),))
            return rec, ev, t, (t if spec.key == "time" else None)
        if k == "bar":
            iv = spec.bar.interval_ns
            start = t if spec.bar.label == "start" else t - iv
            vals = {n: num(n) for n in ("open", "high", "low", "close", "volume")}
            rec = {"start_ns": start, **vals}
            ev = BarEvent(received_time_ns=start + iv, start_time_ns=start, **vals)
            key = start if spec.key in ("start", "time") else None
            return rec, ev, start, key
        if k == "book":
            sides = {}
            for side in ("bid", "ask"):
                levels, hole = [], None
                for i, (pc, sc) in enumerate(zip(f[f"{side}_px"], f[f"{side}_sz"])):
                    pv, sv = cells.get(pc), cells.get(sc)
                    if _blank(pv) and _blank(sv):
                        hole = i if hole is None else hole
                        continue
                    if _blank(pv) or _blank(sv):
                        raise ParseError(f"{where}: {side} level {i + 1}: one of price / size is blank")
                    if hole is not None:
                        raise ParseError(f"{where}: {side} level {i + 1} follows the blank level {hole + 1}")
                    levels.append([_num(pv, f"{where} {pc}"), _num(sv, f"{where} {sc}")])
                sides[side] = levels
            rec = {"t_ns": t, "bids": sides["bid"], "asks": sides["ask"]}
            ev = BookSnapshotEvent(received_time_ns=t, bids=tuple(map(tuple, sides["bid"])),
                                   asks=tuple(map(tuple, sides["ask"])))
            return rec, ev, t, (t if spec.key == "time" else None)
        if k == "funding":
            rate = num("rate")
            rec = {"t_ns": t, "rate": rate}
            mark = None
            if "mark_price" in f:
                mark = num("mark_price")
                rec["mark_price"] = mark
            ev = FundingEvent(received_time_ns=t, rate=rate, mark_price=mark)
            return rec, ev, t, (t if spec.key == "time" else None)
        # liquidation
        px, qty = num("px"), num("qty")
        side = _side(spec, cells.get(f["side"]), where, ("buy", "sell"))
        rec = {"t_ns": t, "px": px, "qty": qty, "side": side}
        ev = LiquidationEvent(received_time_ns=t, price=px, size=qty, side=side)
        return rec, ev, t, (t if spec.key == "time" else None)
    except EventValidationError as exc:
        raise ParseError(f"{where}: the row is not a valid {k}: {exc}") from None
    except KeyError as exc:
        raise ParseError(f"{where}: no column {exc}") from None


def _decode(raw: bytes, spec: Spec, given: str) -> str:
    is_gz = raw[:2] == b"\x1f\x8b"
    if spec.compression == "gzip":
        if not is_gz:
            raise ParseError(f"{given!r}: declared gzip, but the file is not gzip")
        try:
            raw = gzip.decompress(raw)
        except (OSError, EOFError) as exc:
            raise ParseError(f"{given!r}: gzip data is broken: {exc}") from None
    elif is_gz:
        raise ParseError(f"{given!r}: the file is gzip, but the declaration says compression 'none'")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ParseError(f"{given!r}: not UTF-8: {exc}") from None
    return text[1:] if text.startswith("﻿") else text


def _rows_csv(text: str, spec: Spec, given: str):
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=spec.delimiter, strict=True)
    names = spec.names
    try:
        for cells in reader:
            if not cells:
                continue
            if names is None:
                names = tuple(c.strip() for c in cells)
                if len(set(names)) != len(names):
                    raise ParseError(f"{given!r}: the header repeats a column name: {list(names)}")
                missing = [c for c in spec.columns_used() if c not in names]
                if missing:
                    raise ParseError(f"{given!r}: the header has no column(s) {missing} (header: {list(names)})")
                continue
            if len(cells) != len(names):
                raise ParseError(f"{given!r} line {reader.line_num}: {len(cells)} cells, the header has {len(names)}")
            yield reader.line_num, dict(zip(names, cells))
    except csv.Error as exc:
        raise ParseError(f"{given!r} line {reader.line_num}: {exc}") from None
    if names is None:
        raise ParseError(f"{given!r}: declared with a header, but the file has no line at all")


def _reject_constant(name: str):
    raise ValueError(f"{name} is not a JSON number")


def _rows_jsonl(text: str, spec: Spec, given: str):
    for i, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line, parse_float=Decimal, parse_constant=_reject_constant)
        except ValueError as exc:
            raise ParseError(f"{given!r} line {i}: not JSON: {exc}") from None
        if not isinstance(obj, dict):
            raise ParseError(f"{given!r} line {i}: a line must be a JSON object")
        yield i, obj


def _parse_datasets(datasets: Any) -> list[_Dataset]:
    if isinstance(datasets, (str, bytes)) or not isinstance(datasets, Iterable):
        raise SpecError("datasets must be a list of {name, paths, spec[, range_ns]}")
    out, seen = [], set()
    for i, d in enumerate(datasets):
        if not isinstance(d, Mapping):
            raise SpecError(f"datasets[{i}] must be a mapping")
        extra = sorted(set(d) - {"name", "paths", "spec", "range_ns"})
        if extra:
            raise SpecError(f"datasets[{i}]: unknown key(s) {extra}")
        name = d.get("name")
        if type(name) is not str or not name:
            raise SpecError(f"datasets[{i}].name must be a non-empty str")
        if name in seen:
            raise SpecError(f"dataset name {name!r} given twice")
        seen.add(name)
        paths = d.get("paths")
        if not isinstance(paths, (list, tuple)) or not paths or any(type(p) is not str for p in paths):
            raise SpecError(f"datasets[{name!r}].paths must be a non-empty list of str")
        spec = parse_spec(d.get("spec"))
        rng = d.get("range_ns")
        if rng is not None:
            if (not isinstance(rng, (list, tuple)) or len(rng) != 2
                    or any(type(x) is not int for x in rng) or rng[0] >= rng[1]):
                raise SpecError(f"datasets[{name!r}].range_ns must be [lo, hi] ints with lo < hi, got {rng!r}")
            rng = (rng[0], rng[1])
        out.append(_Dataset(name, spec, rng, tuple(paths)))
    if not out:
        raise SpecError("no dataset given")
    return out


def _in_range(spec: Spec, t: int, rng: Optional[tuple[int, int]]) -> bool:
    if rng is None:
        return True
    lo, hi = rng
    if spec.kind == "bar":
        return lo <= t and t + spec.bar.interval_ns <= hi
    return lo <= t < hi


class LoadResult:
    def __init__(self, root: str, datasets: list[_Dataset], files: list[FileRecord],
                 seals: SealRegistry, allowlist: AllowList) -> None:
        self.root = root
        self._ds = {d.name: d for d in datasets}
        self._order = [d.name for d in datasets]
        self._files = files
        self._seals = seals
        self._allow = allowlist
        self.resolutions: dict[str, dict] = {}

    def names(self) -> list[str]:
        return list(self._order)

    def _get(self, name: str) -> _Dataset:
        if name not in self._ds:
            raise DataError(f"no dataset {name!r} in this load (have {self._order})")
        return self._ds[name]

    def kind(self, name: str) -> str:
        return self._get(name).spec.kind

    def records(self, name: str) -> list[dict]:
        """Kept rows, normalised, in delivered order. Fresh copies."""
        return [json.loads(json.dumps(r.record)) for r in self._get(name).rows]

    def provenance(self, name: str) -> list[tuple[str, int]]:
        d = self._get(name)
        return [(d.paths[r.file_index], r.line) for r in d.rows]

    def anomalies(self, name: str) -> list[dict]:
        return [dict(a) for a in self._get(name).anomalies]

    def checks(self, name: str) -> list[str]:
        """The checks that ran for this dataset (a check that could not run --
        no key, no 24x7 session -- is absent, so a clean result is not read
        as more than it is)."""
        return list(self._get(name).checks)

    def events(self, name: str, resolve: Optional[Mapping[str, str]] = None) -> tuple[Event, ...]:
        d = self._get(name)
        rows, applied = A.resolve(d.name, d.rows, d.anomalies, resolve or {})
        self.resolutions[name] = applied
        return tuple(r.event for r in rows)

    def streams(self, resolve: Optional[Mapping[str, Mapping[str, str]]] = None, *,
                default: Optional[Mapping[str, str]] = None) -> dict[str, tuple[Event, ...]]:
        """{dataset name: events} for CoreEngine. `resolve` maps a dataset
        name to its policy map; `default` is the policy map for the datasets
        `resolve` does not name. A name in `resolve` that is not a dataset of
        this load is refused (a typo must not leave a dataset unresolved)."""
        resolve = dict(resolve or {})
        unknown = sorted(set(resolve) - set(self._order))
        if unknown:
            raise SpecError(f"streams: resolve names no dataset of this load: {unknown} (have {self._order})")
        return {name: self.events(name, resolve.get(name, default or {})) for name in self._order}

    def files(self) -> list[FileRecord]:
        return list(self._files)

    def hashes(self) -> dict[str, str]:
        """{path as given: sha256 of its bytes on disk}."""
        return {f.given: f.sha256 for f in self._files}

    def manifest(self) -> dict:
        return {
            "root": self.root,
            "files": [f.__dict__.copy() for f in self._files],
            "seal_records": dict(self._seals.records_read),
            "allowlist": {"roots": ["/".join(r) for r in self._allow.roots],
                          "deny": [p for p, _ in self._allow.deny]},
            "datasets": {n: {"spec": json.loads(json.dumps(self._ds[n].spec.source, default=str)),
                             "range_ns": list(self._ds[n].range_ns) if self._ds[n].range_ns else None,
                             "rows": len(self._ds[n].rows),
                             "checks": list(self._ds[n].checks),
                             "anomalies": A.count(self._ds[n].anomalies),
                             "resolution": self.resolutions.get(n)}
                         for n in self._order},
        }


def load(root: str, datasets: Any, *, allowlist: Optional[AllowList] = None) -> LoadResult:
    """Read every dataset (see module docstring). Refuses (a `DataError`)
    on the first path, seal, declaration or row it cannot read exactly."""
    if type(root) is not str or not root:
        raise SpecError("root must be a non-empty str (the data root)")
    allow = DEFAULT_ALLOWLIST if allowlist is None else allowlist
    if not isinstance(allow, AllowList):
        raise SpecError("allowlist must be an AllowList")
    parsed = _parse_datasets(datasets)
    seals = SealRegistry(root)
    files: list[FileRecord] = []
    # every path of every dataset is checked before any row is read
    checked = [[allow.check(root, p) for p in d.paths] for d in parsed]
    for d, cps in zip(parsed, checked):
        reader = d.spec.time.reader()
        for fi, cp in enumerate(cps):
            with open(cp.real, "rb") as fh:
                raw = fh.read()
            sha = hashlib.sha256(raw).hexdigest()
            ent = seals.match(cp.real, len(raw), sha)
            if ent is not None:
                seals.check_range(ent, cp.given, d.range_ns)
            text = _decode(raw, d.spec, cp.given)
            rows = _rows_csv(text, d.spec, cp.given) if d.spec.format == "csv" else _rows_jsonl(text, d.spec, cp.given)
            n_read = n_kept = 0
            for line, row in rows:
                n_read += 1
                where = f"{cp.given!r} line {line}"
                cells = _Cells(d.spec, row, where)
                rec, ev, t, key = _build(d.spec, cells, reader, where)
                if not _in_range(d.spec, t, d.range_ns):
                    continue
                if ent is not None:
                    try:
                        st = seal_time_ns(cells.get(ent.time_column))
                    except ParseError:
                        raise SealedRangeError(f"{where}: the file is sealed on column {ent.time_column!r}, "
                                               f"which the row does not have") from None
                    except SealedRangeError as exc:
                        raise SealedRangeError(f"{where}: {exc}") from None
                    if st >= ent.cutoff_ns:
                        raise SealedRangeError(
                            f"{where}: kept by the range, but its seal time ({ent.time_column!r}) is at or after "
                            f"the seal cutoff {ent.cutoff_ns} ns (unit {ent.unit}); end the range earlier")
                n_kept += 1
                synth = False
                if d.spec.synthetic is not None:
                    synth = _text_of(cells.get(d.spec.synthetic[0])) in d.spec.synthetic[1]
                d.rows.append(Row(rec, ev, fi, line, t, key, (json.dumps(rec, sort_keys=True), cells.rest()), synth))
            files.append(FileRecord(d.name, cp.given, cp.real, cp.rel_real, len(raw), sha,
                                    ent.unit if ent else None, n_read, n_kept))
        d.anomalies, d.checks = A.detect(d.spec, d.rows, len(d.paths))
    return LoadResult(root, parsed, files, seals, allow)
