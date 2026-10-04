"""Reference series (参照の系列): rows of (time, value) that a strategy may
read only from the time each row became available (W1 spec C3,
docs/DISCUSSIONS/2026-10-02_W1_spec.md).

A reference series is declared with how its rows become available, in one
of two forms, each with its source (where that availability is written):

    {"lag_ns": int >= 0, "source": str}         available_at = row time + lag (a constant lag)
    {"available_at": "per_row", "source": str}  each row carries its own available_at (a second time column)

The per-row form is for series published at a fixed local time on a
calendar (a weekly report published on Friday 15:30 New York time, later in a
holiday week): a constant lag in ns cannot follow a daylight-saving change or
a holiday, and a constant taken from a summer row reads a winter row one hour
before it is published. A series without a declaration is refused when it is
read (`SpecError`), and so is a declaration without a source.

    series = reference_series(name, rows, declarations={name: {...}, ...})
    series = load_reference(root, dataset, declarations={...})   # from a file, through the allow-list and the seals
    events = series.events()                                     # for CoreEngine, one stream per series

A `ReferenceSeries` checks itself when it is made (`__post_init__`): times
strictly increasing int ns, values finite, available_at >= the row's time and
never decreasing, and, for a constant lag, available_at == time + lag on
every row. It carries its declaration, so a run can compare it with the
declarations it was given (bot.research.cards.run checks every series it
receives).

Each row becomes one event
whose `exchange_time_ns` is the row's time and whose `received_time_ns` is
its available_at, so the core delivers it to the strategy at available_at
and never earlier (the core's own rule: an event reaches the strategy at its
received time, engine.py). The availability is put into the event here, by
the data layer; a strategy never adds it by hand.

Carrier: the core has no event type that carries a free value, and this
layer does not change the core. A row travels as a `ClockEvent` (not a
market event: it never reaches the fill model or the account) whose `tag`
is the value written by `float.__repr__` (which reads back to the same
float exactly); `reference_value(event)` reads it back. Which series an
event belongs to is the name of the input stream it was handed over in
(`Event.stream`, set by the engine). Note on the merge order (ordering.py):
at one instant the core delivers input events in (received time, merge
position) order and CLOCK merges after BAR, so a lag-0 row whose time equals
a bar's close is delivered after that bar; a reader that must see every row
available at t reads after every delivery at t (a timer at t, phase 4).

Rows: (time_ns, value) for a constant lag, (time_ns, value, available_ns) for
per-row availability; times strictly increasing (a repeated time is two
values for one instant and is refused, never merged), values finite.

File form (`load_reference`): a CSV (optionally gzip) with a header,
declared like a dataset of the reading door (`load`), with the value column
named by `value`:

    {"name": str, "paths": [path, ...], "range_ns": [lo, hi] (optional),
     "spec": {"format": "csv", "header": true, "delimiter": ",",
              "compression": "none" | "gzip" (optional),
              "time": {"columns": [col], "unit": s|ms|us|ns|iso, "tz": zone (optional)},
              "value": col,
              "available": col (required for a per-row declaration, refused otherwise; read
                           like the time column)}}

Every path passes the allow-list and the seal records exactly as in `load`
(allowlist.py): a file the seal records name is refused unopened unless the
range ends at or before its cutoff, and every kept row of a sealed file must
have its seal time before the cutoff.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import io
import math
import re
from dataclasses import dataclass
from typing import Any, Iterable, Iterator, Mapping, Optional

from ..core.events import ClockEvent, Event
from ..core.time import validate_nanos
from .allowlist import DEFAULT_ALLOWLIST, AllowList, SealRegistry, seal_time_ns
from .errors import ParseError, SealedRangeError, SpecError
from .timestamps import UNITS, TimeReader

REFERENCE_KIND = "reference"
_NUM = re.compile(r"^[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?$")
_DATASET_KEYS = {"name", "paths", "spec", "range_ns"}
_SPEC_KEYS = {"format", "header", "delimiter", "compression", "time", "value", "available"}
PER_ROW = "per_row"
_TIME_KEYS = {"columns", "unit", "tz"}


@dataclass(frozen=True)
class ReferenceDecl:
    """The declaration of one series: a constant lag (`lag_ns`, int ns >= 0) or
    per-row availability (`lag_ns` None), and its source (non-empty text)."""
    name: str
    lag_ns: Optional[int]
    source: str

    def __post_init__(self) -> None:
        if type(self.name) is not str or not self.name:
            raise SpecError(f"a reference series needs a non-empty str name, got {self.name!r}")
        if self.lag_ns is not None and (type(self.lag_ns) is not int or self.lag_ns < 0):
            raise SpecError(f"reference series {self.name!r}: lag_ns must be an int >= 0 (ns), got {self.lag_ns!r}")
        if type(self.source) is not str or not self.source.strip():
            raise SpecError(f"reference series {self.name!r}: the declaration needs its source (where the "
                            f"availability is written), got {self.source!r}")

    @property
    def per_row(self) -> bool:
        return self.lag_ns is None

    def as_dict(self) -> dict:
        if self.per_row:
            return {"available_at": PER_ROW, "source": self.source}
        return {"lag_ns": self.lag_ns, "source": self.source}


def parse_decl(name: str, raw: Any) -> ReferenceDecl:
    m = _mapping(raw, f"declaration of {name!r}")
    if "lag_ns" in m and "available_at" in m:
        raise SpecError(f"declaration of {name!r}: give lag_ns or available_at, not both")
    if "lag_ns" in m:
        _only(m, {"lag_ns", "source"}, f"declaration of {name!r}")
        return ReferenceDecl(name, m["lag_ns"], m.get("source"))
    if m.get("available_at") == PER_ROW:
        _only(m, {"available_at", "source"}, f"declaration of {name!r}")
        return ReferenceDecl(name, None, m.get("source"))
    raise SpecError(f"declaration of {name!r} must be {{'lag_ns': int, 'source': str}} or "
                    f"{{'available_at': {PER_ROW!r}, 'source': str}}, got {dict(m)!r}")


def declared(name: str, declarations: Mapping[str, Any]) -> ReferenceDecl:
    """The declaration of `name` from `declarations` (name -> declaration); a
    series without one is refused (W1 spec C3: 宣言の無い系列は読み込みを拒む)."""
    if not isinstance(declarations, Mapping):
        raise SpecError("declarations must be a mapping of series name -> declaration")
    if name not in declarations:
        raise SpecError(f"reference series {name!r} has no declaration of its availability; a series without "
                        f"one is refused (declared: {sorted(declarations)})")
    return parse_decl(name, declarations[name])


@dataclass(frozen=True)
class ReferenceSeries:
    name: str
    decl: ReferenceDecl
    times_ns: tuple[int, ...]  # row times, strictly increasing
    values: tuple[float, ...]
    available_ns: tuple[int, ...]  # when each row could first be read
    manifest: tuple = ()  # (given path, sha256, rows read, rows kept) per file, for a file-read series

    def __post_init__(self) -> None:
        if type(self.decl) is not ReferenceDecl or self.decl.name != self.name:
            raise SpecError(f"reference series {self.name!r} must carry its own ReferenceDecl")
        for field_name in ("times_ns", "values", "available_ns"):
            if type(getattr(self, field_name)) is not tuple:
                raise SpecError(f"reference series {self.name!r}: {field_name} must be a tuple")
        n = len(self.times_ns)
        if len(self.values) != n or len(self.available_ns) != n:
            raise SpecError(f"reference series {self.name!r}: times, values and available_at differ in length")
        prev_t = prev_a = None
        lag = self.decl.lag_ns
        for i, (t, v, a) in enumerate(zip(self.times_ns, self.values, self.available_ns)):
            for what, x in (("time", t), ("available_at", a)):
                if type(x) is not int:
                    raise ParseError(f"reference series {self.name!r} row {i}: {what} must be int ns, got "
                                     f"{type(x).__name__} {x!r}")
                validate_nanos(x)
            if type(v) is not float or not math.isfinite(v):
                raise ParseError(f"reference series {self.name!r} row {i}: value {v!r} is not a finite float")
            if prev_t is not None and t <= prev_t:
                raise ParseError(f"reference series {self.name!r} row {i}: time {t} is not after the previous "
                                 f"row's {prev_t} (rows must be strictly increasing in time)")
            if a < t:
                raise ParseError(f"reference series {self.name!r} row {i}: available_at {a} is before the row's "
                                 f"time {t}")
            if prev_a is not None and a < prev_a:
                raise ParseError(f"reference series {self.name!r} row {i}: available_at {a} is before the "
                                 f"previous row's {prev_a} (a later row cannot be published earlier)")
            if lag is not None and a != t + lag:
                raise ParseError(f"reference series {self.name!r} row {i}: available_at {a} is not time + the "
                                 f"declared lag {lag}")
            prev_t, prev_a = t, a

    @property
    def lag_ns(self) -> Optional[int]:
        return self.decl.lag_ns

    def __len__(self) -> int:
        return len(self.times_ns)

    def available_at(self, i: int) -> int:
        return self.available_ns[i]

    def events(self) -> Iterator[ClockEvent]:
        """One ClockEvent per row, in row order: exchange time = the row's time,
        received time = available_at, tag = the value (float repr)."""
        for t, v, a in zip(self.times_ns, self.values, self.available_ns):
            yield ClockEvent(received_time_ns=a, exchange_time_ns=t, tag=float.__repr__(v))


def reference_value(event: Event) -> float:
    """The value a reference row's event carries (the inverse of `events`)."""
    if type(event) is not ClockEvent:
        raise ParseError(f"a reference row travels as a ClockEvent, got {type(event).__name__}")
    try:
        v = float(event.tag)
    except ValueError:
        raise ParseError(f"event tag {event.tag!r} is not a reference value") from None
    if not math.isfinite(v):
        raise ParseError(f"event tag {event.tag!r} is not a finite reference value")
    return v


def _checked_rows(decl: ReferenceDecl, rows: Iterable[Any]) -> tuple[tuple, tuple, tuple]:
    name = decl.name
    width = 3 if decl.per_row else 2
    shape = "(time_ns, value, available_ns)" if decl.per_row else "(time_ns, value)"
    times: list[int] = []
    values: list[float] = []
    avail: list[int] = []
    for i, row in enumerate(rows):
        try:
            parts = tuple(row)
        except TypeError:
            parts = ()
        if len(parts) != width:
            raise ParseError(f"reference series {name!r} row {i}: a row is {shape} for this declaration")
        t, v = parts[0], parts[1]
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise ParseError(f"reference series {name!r} row {i}: value must be a number, got {type(v).__name__} {v!r}")
        if type(t) is not int:
            raise ParseError(f"reference series {name!r} row {i}: time must be int ns, got {type(t).__name__} {t!r}")
        times.append(t)
        values.append(float(v))
        avail.append(parts[2] if decl.per_row else t + decl.lag_ns)
    return tuple(times), tuple(values), tuple(avail)


def reference_series(name: str, rows: Iterable[Any], *, declarations: Mapping[str, Any]) -> ReferenceSeries:
    """A series from in-memory rows, with its declaration (module docstring)."""
    decl = declared(name, declarations)
    times, values, avail = _checked_rows(decl, rows)
    return ReferenceSeries(name, decl, times, values, avail)


def _mapping(v: Any, where: str) -> Mapping:
    if not isinstance(v, Mapping):
        raise SpecError(f"{where} must be a mapping, got {type(v).__name__}")
    return v


def _only(m: Mapping, allowed: set, where: str) -> None:
    extra = sorted(set(m) - allowed)
    if extra:
        raise SpecError(f"{where}: unknown key(s) {extra} (allowed: {sorted(allowed)})")


def _parse_dataset(dataset: Any) -> tuple[str, tuple[str, ...], Optional[tuple[int, int]], dict]:
    d = _mapping(dataset, "reference dataset")
    _only(d, _DATASET_KEYS, "reference dataset")
    name = d.get("name")
    if type(name) is not str or not name:
        raise SpecError("reference dataset: name must be a non-empty str")
    paths = d.get("paths")
    if not isinstance(paths, (list, tuple)) or not paths or any(type(p) is not str for p in paths):
        raise SpecError(f"reference dataset {name!r}: paths must be a non-empty list of str")
    rng = d.get("range_ns")
    if rng is not None:
        if (not isinstance(rng, (list, tuple)) or len(rng) != 2 or any(type(x) is not int for x in rng)
                or rng[0] >= rng[1]):
            raise SpecError(f"reference dataset {name!r}: range_ns must be [lo, hi] ints with lo < hi, got {rng!r}")
        rng = (rng[0], rng[1])
    s = _mapping(d.get("spec"), f"reference dataset {name!r}: spec")
    _only(s, _SPEC_KEYS, f"reference dataset {name!r}: spec")
    for req in ("format", "header", "delimiter", "time", "value"):
        if req not in s:
            raise SpecError(f"reference dataset {name!r}: spec requires {req!r}")
    if s["format"] != "csv":
        raise SpecError(f"reference dataset {name!r}: spec.format must be 'csv', got {s['format']!r}")
    if s["header"] is not True:
        raise SpecError(f"reference dataset {name!r}: spec.header must be true (columns are named by the header)")
    delim = s["delimiter"]
    if type(delim) is not str or len(delim) != 1 or delim in "\r\n\"":
        raise SpecError(f"reference dataset {name!r}: spec.delimiter must be one character, got {delim!r}")
    comp = s.get("compression", "none")
    if comp not in ("none", "gzip"):
        raise SpecError(f"reference dataset {name!r}: spec.compression must be 'none' or 'gzip', got {comp!r}")
    t = _mapping(s["time"], f"reference dataset {name!r}: spec.time")
    _only(t, _TIME_KEYS, f"reference dataset {name!r}: spec.time")
    cols = t.get("columns")
    if not isinstance(cols, (list, tuple)) or len(cols) != 1 or type(cols[0]) is not str or not cols[0]:
        raise SpecError(f"reference dataset {name!r}: spec.time.columns must be one column name, got {cols!r}")
    unit = t.get("unit")
    if unit not in UNITS:
        raise SpecError(f"reference dataset {name!r}: spec.time.unit must be one of {list(UNITS)}, got {unit!r}")
    value = s["value"]
    if type(value) is not str or not value:
        raise SpecError(f"reference dataset {name!r}: spec.value must be a column name, got {value!r}")
    avail = s.get("available")
    if avail is not None and (type(avail) is not str or not avail):
        raise SpecError(f"reference dataset {name!r}: spec.available must be a column name, got {avail!r}")
    spec = {"delimiter": delim, "compression": comp, "time_col": cols[0], "unit": unit, "tz": t.get("tz"),
            "value": value, "available": avail}
    return name, tuple(paths), rng, spec


def _decode(raw: bytes, compression: str, given: str) -> str:
    is_gz = raw[:2] == b"\x1f\x8b"
    if compression == "gzip":
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


def load_reference(root: str, dataset: Any, *, declarations: Mapping[str, Any],
                   allowlist: Optional[AllowList] = None, explore_window: Optional[str] = None) -> ReferenceSeries:
    """Read one reference series from its files (module docstring). The
    declaration is checked before any path is touched."""
    if type(root) is not str or not root:
        raise SpecError("root must be a non-empty str (the data root)")
    name, paths, rng, spec = _parse_dataset(dataset)
    decl = declared(name, declarations)
    if decl.per_row and spec["available"] is None:
        raise SpecError(f"reference dataset {name!r} is declared per-row: spec.available must name the column")
    if not decl.per_row and spec["available"] is not None:
        raise SpecError(f"reference dataset {name!r} is declared with a constant lag: spec.available is refused")
    allow = DEFAULT_ALLOWLIST if allowlist is None else allowlist
    if not isinstance(allow, AllowList):
        raise SpecError("allowlist must be an AllowList")
    checked = [allow.check(root, p) for p in paths]  # every path before any byte is read
    seals = SealRegistry(root, explore_window)
    seals.log_explore_access("load_reference", [(name, rng)])  # a line before any byte is read
    reader = TimeReader(spec["unit"], spec["tz"])
    rows: list[tuple] = []
    manifest = []
    for cp in checked:
        raw, ent = seals.read_checked(cp.real, cp.given, rng)
        sha = hashlib.sha256(raw).hexdigest()
        text = _decode(raw, spec["compression"], cp.given)
        rd = csv.reader(io.StringIO(text, newline=""), delimiter=spec["delimiter"], strict=True)
        header = None
        n_read = n_kept = 0
        try:
            for cells in rd:
                if not cells:
                    continue
                if header is None:
                    header = tuple(c.strip() for c in cells)
                    need = [c for c in (spec["time_col"], spec["value"], spec["available"])
                            if c is not None and c not in header]
                    if need:
                        raise ParseError(f"{cp.given!r}: the header has no column(s) {need} (header: {list(header)})")
                    if ent is not None and ent.time_column not in header:
                        raise SealedRangeError(f"{cp.given!r}: the file is sealed on column {ent.time_column!r}, "
                                               f"which its header does not have")
                    continue
                if len(cells) != len(header):
                    raise ParseError(f"{cp.given!r} line {rd.line_num}: {len(cells)} cells, "
                                     f"the header has {len(header)}")
                n_read += 1
                row = dict(zip(header, cells))
                where = f"{cp.given!r} line {rd.line_num}"
                t = reader.read(row[spec["time_col"]])
                if rng is not None and not (rng[0] <= t < rng[1]):
                    continue
                if ent is not None:
                    st = seal_time_ns(row[ent.time_column])
                    if st >= ent.cutoff_ns:
                        raise SealedRangeError(f"{where}: kept by the range, but its seal time "
                                               f"({ent.time_column!r}) is at or after the seal cutoff "
                                               f"{ent.cutoff_ns} ns (unit {ent.unit}); end the range earlier{ent.note}")
                text_v = row[spec["value"]].strip()
                if not _NUM.match(text_v):
                    raise ParseError(f"{where}: value {text_v!r} is not a decimal number")
                if decl.per_row:
                    rows.append((t, float(text_v), reader.read(row[spec["available"]])))
                else:
                    rows.append((t, float(text_v)))
                n_kept += 1
        except csv.Error as exc:
            raise ParseError(f"{cp.given!r} line {rd.line_num}: {exc}") from None
        if header is None:
            raise ParseError(f"{cp.given!r}: declared with a header, but the file has no line at all")
        manifest.append((cp.given, sha, n_read, n_kept))
    times, values, avail = _checked_rows(decl, rows)
    return ReferenceSeries(name, decl, times, values, avail, tuple(manifest))


__all__ = ["PER_ROW", "REFERENCE_KIND", "ReferenceDecl", "ReferenceSeries", "declared", "load_reference",
           "parse_decl", "reference_series", "reference_value"]
