"""The dataset declaration (spec): how a file's columns become records.

A spec is a plain mapping (JSON-able). It is read strictly: an unknown key,
a missing required key or a value of the wrong kind is refused (`SpecError`)
before any file is opened, so a typo cannot fall back to a default.

Keys:
  format       "csv" | "jsonl" (one JSON object per line; a column name of a
               jsonl file is a dotted path into the object: "raw.o.T")
  header       csv only, required: bool (False requires `names`)
  names        csv without header: the column names, in order
  delimiter    csv only, required: one character
  compression  "none" | "gzip" (optional, default "none"; the file's magic
               bytes must agree with it either way)
  kind         "trade" | "quote" | "bar" | "book" | "funding" | "liquidation"
  symbol       str (non-empty)
  asset        "crypto" | "fx" | "jpx"
  time         {"columns": [col] or [col, col], "join": str (two columns),
                "unit": s|ms|us|ns|iso, "tz": zone (optional),
                "plausible_ns": [lo, hi] (optional)}
  fields       logical field -> column (per kind, below)
  side_map     raw value -> "buy" | "sell" | "" (optional)
  bar          kind "bar" only, required: {"interval_s": int > 0,
               "label": "start" | "end", "session": "24x7" (optional)}
  key          "id" | "start" | "time" (optional): the key that identifies a
               row for the duplicate / conflict / generation checks
  synthetic    {"column": col, "values": [text, ...]} (optional): a column
               that marks a row as synthetic (a filled bar in a real
               series); such rows are reported (anomaly "synthetic") and
               reach events only by a named policy (drop / accept)

Fields per kind (required unless marked optional):
  trade        px, qty; side (optional; absent = "" aggressor unknown),
               id (optional)
  quote        bid, ask, bid_qty, ask_qty
  bar          open, high, low, close, volume
  book         levels (int > 0), bid_px, bid_sz, ask_px, ask_sz (lists of
               `levels` column names, best level first)
  funding      rate; mark_price (optional)
  liquidation  px, qty, side
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

from .errors import SpecError
from .timestamps import UNITS, TimeReader, check_zone

FORMATS = ("csv", "jsonl")
KINDS = ("trade", "quote", "bar", "book", "funding", "liquidation")
ASSETS = ("crypto", "fx", "jpx")
COMPRESSIONS = ("none", "gzip")
KEYS = ("id", "start", "time")
SIDES = ("buy", "sell", "")

_TOP = {"format", "header", "names", "delimiter", "compression", "kind", "symbol", "asset",
        "time", "fields", "side_map", "bar", "key", "synthetic"}
_SYNTH = {"column", "values"}
_TIME = {"columns", "join", "unit", "tz", "plausible_ns"}
_BAR = {"interval_s", "label", "session"}

FIELDS: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    # kind -> (required, optional)
    "trade": (("px", "qty"), ("side", "id")),
    "quote": (("bid", "ask", "bid_qty", "ask_qty"), ()),
    "bar": (("open", "high", "low", "close", "volume"), ()),
    "book": (("levels", "bid_px", "bid_sz", "ask_px", "ask_sz"), ()),
    "funding": (("rate",), ("mark_price",)),
    "liquidation": (("px", "qty", "side"), ()),
}


@dataclass(frozen=True)
class TimeSpec:
    columns: tuple[str, ...]
    join: Optional[str]
    unit: str
    tz: Optional[str]
    plausible_ns: Optional[tuple[int, int]]

    def reader(self) -> TimeReader:
        return TimeReader(self.unit, self.tz, self.plausible_ns)


@dataclass(frozen=True)
class BarSpec:
    interval_ns: int
    label: str
    session: Optional[str]


@dataclass(frozen=True)
class Spec:
    format: str
    header: Optional[bool]
    names: Optional[tuple[str, ...]]
    delimiter: Optional[str]
    compression: str
    kind: str
    symbol: str
    asset: str
    time: TimeSpec
    fields: Mapping[str, Any]
    side_map: Optional[Mapping[str, str]]
    bar: Optional[BarSpec]
    key: Optional[str]
    synthetic: Optional[tuple[str, frozenset]] = None
    source: Mapping[str, Any] = field(repr=False, compare=False, default=None)

    def columns_used(self) -> tuple[str, ...]:
        cols = list(self.time.columns) + ([self.synthetic[0]] if self.synthetic else [])
        for name, col in self.fields.items():
            if name == "levels":
                continue
            cols.extend(col if isinstance(col, tuple) else (col,))
        return tuple(cols)


def _text(value: Any, where: str) -> str:
    if type(value) is not str or not value:
        raise SpecError(f"{where} must be a non-empty str, got {value!r}")
    return value


def _choice(value: Any, allowed: tuple, where: str) -> Any:
    if type(value) is not str or value not in allowed:
        raise SpecError(f"{where} must be one of {list(allowed)}, got {value!r}")
    return value


def _mapping(value: Any, where: str) -> Mapping:
    if not isinstance(value, Mapping):
        raise SpecError(f"{where} must be a mapping, got {type(value).__name__}")
    for k in value:
        if type(k) is not str:
            raise SpecError(f"{where} keys must be str, got {k!r}")
    return value


def _unknown(m: Mapping, allowed: set, where: str) -> None:
    extra = sorted(set(m) - allowed)
    if extra:
        raise SpecError(f"{where}: unknown key(s) {extra} (allowed: {sorted(allowed)})")
    nulls = sorted(k for k, v in m.items() if v is None)
    if nulls:
        raise SpecError(f"{where}: key(s) {nulls} given as null; leave an optional key out instead")


def _pos_int(value: Any, where: str) -> int:
    if type(value) is not int or value <= 0:
        raise SpecError(f"{where} must be an int > 0, got {value!r}")
    return value


def parse_spec(raw: Any) -> Spec:
    """Read a declaration strictly; returns a frozen `Spec`."""
    m = _mapping(raw, "spec")
    _unknown(m, _TOP, "spec")
    for req in ("format", "kind", "symbol", "asset", "time", "fields"):
        if req not in m:
            raise SpecError(f"spec: missing required key {req!r}")
    fmt = _choice(m["format"], FORMATS, "spec.format")
    kind = _choice(m["kind"], KINDS, "spec.kind")
    symbol = _text(m["symbol"], "spec.symbol")
    asset = _choice(m["asset"], ASSETS, "spec.asset")
    compression = _choice(m.get("compression", "none"), COMPRESSIONS, "spec.compression")

    header = names = delimiter = None
    if fmt == "csv":
        for req in ("header", "delimiter"):
            if req not in m:
                raise SpecError(f"spec: csv requires {req!r}")
        header = m["header"]
        if type(header) is not bool:
            raise SpecError(f"spec.header must be true or false, got {header!r}")
        delimiter = m["delimiter"]
        if type(delimiter) is not str or len(delimiter) != 1 or delimiter in "\r\n\"":
            raise SpecError(f"spec.delimiter must be one character (not a quote or newline), got {delimiter!r}")
        if not header:
            if "names" not in m:
                raise SpecError("spec: a csv without header requires 'names'")
        if "names" in m:
            if header:
                raise SpecError("spec: 'names' is only for a csv without header")
            raw_names = m["names"]
            if not isinstance(raw_names, (list, tuple)) or not raw_names:
                raise SpecError(f"spec.names must be a non-empty list, got {raw_names!r}")
            names = tuple(_text(n, f"spec.names[{i}]") for i, n in enumerate(raw_names))
            if len(set(names)) != len(names):
                raise SpecError(f"spec.names has a repeated name: {list(names)}")
    else:
        for bad in ("header", "names", "delimiter"):
            if bad in m:
                raise SpecError(f"spec: {bad!r} is for csv only (format {fmt!r})")

    t = _mapping(m["time"], "spec.time")
    _unknown(t, _TIME, "spec.time")
    if "columns" not in t or "unit" not in t:
        raise SpecError("spec.time requires 'columns' and 'unit'")
    cols = t["columns"]
    if not isinstance(cols, (list, tuple)) or len(cols) not in (1, 2):
        raise SpecError(f"spec.time.columns must be a list of 1 or 2 names, got {cols!r}")
    cols = tuple(_text(c, f"spec.time.columns[{i}]") for i, c in enumerate(cols))
    unit = _choice(t["unit"], UNITS, "spec.time.unit")
    join = t.get("join")
    if len(cols) == 2:
        if type(join) is not str:
            raise SpecError("spec.time: two columns require 'join' (the text put between them)")
        if unit != "iso":
            raise SpecError("spec.time: two time columns are joined into an ISO text; unit must be 'iso'")
    elif "join" in t:
        raise SpecError("spec.time.join is for two columns only")
    tz = check_zone(t.get("tz"), unit)
    pl = t.get("plausible_ns")
    if pl is not None:
        if not isinstance(pl, (list, tuple)) or len(pl) != 2:
            raise SpecError(f"spec.time.plausible_ns must be [lo, hi], got {pl!r}")
        pl = (pl[0], pl[1])
    tspec = TimeSpec(cols, join, unit, tz, pl)
    tspec.reader()  # validates the window

    f = _mapping(m["fields"], "spec.fields")
    required, optional = FIELDS[kind]
    _unknown(f, set(required) | set(optional), f"spec.fields (kind {kind!r})")
    for r in required:
        if r not in f:
            raise SpecError(f"spec.fields: kind {kind!r} requires {r!r}")
    fields: dict[str, Any] = {}
    if kind == "book":
        levels = _pos_int(f["levels"], "spec.fields.levels")
        fields["levels"] = levels
        for name in ("bid_px", "bid_sz", "ask_px", "ask_sz"):
            v = f[name]
            if not isinstance(v, (list, tuple)) or len(v) != levels:
                raise SpecError(f"spec.fields.{name} must list {levels} column names, got {v!r}")
            fields[name] = tuple(_text(c, f"spec.fields.{name}[{i}]") for i, c in enumerate(v))
    else:
        for name, col in f.items():
            fields[name] = _text(col, f"spec.fields.{name}")

    if names is not None:
        used = list(tspec.columns) + [c for n, c in fields.items() if n != "levels"
                                      for c in (c if isinstance(c, tuple) else (c,))]
        missing = [c for c in used if c not in names]
        if missing:
            raise SpecError(f"spec.names has no column(s) {missing} (names: {list(names)})")

    side_map = None
    if "side_map" in m:
        sm = _mapping(m["side_map"], "spec.side_map")
        for k, v in sm.items():
            if type(v) is not str or v not in SIDES:
                raise SpecError(f"spec.side_map[{k!r}] must be one of {list(SIDES)}, got {v!r}")
        if kind not in ("trade", "liquidation"):
            raise SpecError(f"spec.side_map is for kinds trade / liquidation, not {kind!r}")
        side_map = dict(sm)

    bar = None
    if kind == "bar":
        if "bar" not in m:
            raise SpecError("spec: kind 'bar' requires 'bar' (interval_s, label)")
        b = _mapping(m["bar"], "spec.bar")
        _unknown(b, _BAR, "spec.bar")
        if "interval_s" not in b or "label" not in b:
            raise SpecError("spec.bar requires 'interval_s' and 'label'")
        iv = _pos_int(b["interval_s"], "spec.bar.interval_s")
        label = _choice(b["label"], ("start", "end"), "spec.bar.label")
        session = b.get("session")
        if session is not None:
            _choice(session, ("24x7",), "spec.bar.session")
        bar = BarSpec(iv * 1_000_000_000, label, session)
    elif "bar" in m:
        raise SpecError(f"spec.bar is for kind 'bar' only, not {kind!r}")

    key = m.get("key")
    if key is not None:
        _choice(key, KEYS, "spec.key")
        if key == "id" and "id" not in fields:
            raise SpecError("spec.key 'id' requires fields.id")
        if key == "start" and kind != "bar":
            raise SpecError("spec.key 'start' is for kind 'bar'")

    synthetic = None
    if "synthetic" in m:
        sy = _mapping(m["synthetic"], "spec.synthetic")
        _unknown(sy, _SYNTH, "spec.synthetic")
        if "column" not in sy or "values" not in sy:
            raise SpecError("spec.synthetic requires 'column' and 'values'")
        vals = sy["values"]
        if not isinstance(vals, (list, tuple)) or not vals or any(type(v) is not str for v in vals):
            raise SpecError(f"spec.synthetic.values must be a non-empty list of str, got {vals!r}")
        synthetic = (_text(sy["column"], "spec.synthetic.column"), frozenset(vals))
        if names is not None and synthetic[0] not in names:
            raise SpecError(f"spec.names has no column {synthetic[0]!r} (spec.synthetic.column)")

    return Spec(fmt, header, names, delimiter, compression, kind, symbol, asset, tspec,
                fields, side_map, bar, key, synthetic, source=m)
