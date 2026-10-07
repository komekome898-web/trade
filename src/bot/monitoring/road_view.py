"""The reader of the road record for the バックテスト tab (道の記録: <run dir>/road/, 版 road-record-7).

One run = one directory `<runs_dir>/<run_id>/` that holds record.json, repro.json and, for a road run, `road/`: the
tables signals / orders / fills / fx / ledger_fills / trades (gzip CSV, every cell a string, times in UTC ns) and
summary.json, and SCHEMA.json (the column list). The tables are written by bot.bt.road.tables on the main working
branch; this module only reads them (it imports nothing of bot.bt).

    status(run_dir)                  -> RoadStatus(ok, reason, schema, version): 版 and the files, no table is read
    load(run_dir)                    -> RoadData (cached by (path, mtime, size) of every file)
    RoadData.group(inst, rng)        -> Group: numpy columns of one (instrument, range), sorted by time
    layers(group, lo_ns, hi_ns, limit_ns, interval_s)  -> the chart layers of the visible range (binary search / prefix cuts)
    table_page(data, table, ...)     -> one page of one table: all the columns, sort, filter, page
    trace(data, table, row, ...)     -> the rows tied to one row by the id columns (signal -> order -> fill -> trade)
    headline(data, group, limit_ns)  -> the numbers computed from the tables, each with its formula

Not read for a road run: the pipeline's trades.json / metrics.json (SCHEMA read_from: their trade count is FIFO, not the
road's 0 -> 0 count). A run whose SCHEMA version is not in SUPPORTED, or whose tables are not all there, is not shown;
`status` says why. Rows stamped at or after `limit_ns` (the seal boundary, backtest_chart) are never returned.

Seal policy (one rule for every table; RoadData.visible): a row is shown only when EVERY time in it is before the limit
(an order counts the times of its own fills too: a state or filled_qty built from a later fill would show it), so a row that
began before the boundary and ended after it is not shown at all (cut whole, never trimmed: a trimmed row would say, by its
state or its end, what happened after). A run that crosses the boundary (its last time is at or after it) also hides the rows
still open at its end (a signal still on, an order still open, a trade not closed), since "open" is a statement about the
data after the boundary; and it serves no summary.json number (the numbers of the whole run).
"""
from __future__ import annotations

import gzip
import json
import os
import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np
import pandas as pd

ROAD_DIR = "road"
SCHEMA_FILE = "SCHEMA.json"
SUPPORTED = ("road-record-7",)
TABLES = ("signals", "orders", "fills", "fx", "ledger_fills", "trades", "summary")
CSV_TABLES = tuple(t for t in TABLES if t != "summary")
TABLE_JA = {"signals": "合図", "orders": "注文", "fills": "約定", "fx": "USDJPY", "ledger_fills": "帳簿の約定",
            "trades": "取引", "summary": "まとめ"}
RANGES = ("pessimistic", "optimistic")  # shown first: the pessimistic side
RANGE_JA = {"pessimistic": "悲観側", "optimistic": "楽観側"}
NO_SIGNAL = "無し"  # orders.signal_id of an order that does not come from a signal
ZERO_STATE = "量が 0 で出さない"  # orders.state of a level whose quantity came to 0
KEY_COL = {"signals": "start_t_ns", "orders": "placed_t_ns", "fills": "t_ns", "fx": "t_ns", "ledger_fills": "t_ns",
           "trades": "first_t_ns"}
SUMMARY_CUT_REASON = "この走らせは封印の境をまたぐので、まとめ(summary.json)は境の前で切れない。出さない(境の前の数は、画面が表から計算した数を見る)"
EXPECTED_COLUMNS = {  # road-record-7: the columns each table must have (bot.bt.road.tables.SCHEMA of the main branch)
    "road-record-7": {
        "fills": ["instrument", "range", "fill_id", "order_id", "signal_id", "t_ns", "venue_t_ns", "side", "qty", "px", "ccy", "fee", "liquidity", "notice_t_ns", "notice_seq", "fill_rule", "fill_exit_rule", "fill_case"],
        "fx": ["instrument", "range", "t_ns", "pair", "rate", "source"],
        "ledger_fills": ["instrument", "range", "fill_id", "t_ns", "side", "qty", "px", "ccy", "position_after", "avg_px_after", "pnl_quote", "usdjpy", "usdjpy_t_ns", "pnl_jpy", "pnl_jpy_cum", "trade_id", "opens_trade_id"],
        "orders": ["instrument", "range", "order_id", "origin", "signal_id", "side", "order_type", "limit_px", "qty", "placed_t_ns", "placed_seq", "sent_t_ns", "acked_t_ns", "acked_venue_t_ns", "cancel_sent_t_ns", "canceled_t_ns", "venue_closed_t_ns", "rejected_t_ns", "cancel_rejected_t_ns", "state_unknown_t_ns", "closed_t_ns", "closed_venue_t_ns", "closed_seq", "close_kind", "close_reason", "state", "filled_qty", "margin_jpy", "use_ratio", "levels", "size_px", "size_px_source", "quote_ccy", "usdjpy", "usdjpy_t_ns", "qty_raw", "qty_source", "position_at_send", "exit_pending_at_send", "reduce_only", "exit_kind", "attached_to", "sent_limit_px"],
        "signals": ["instrument", "range", "signal_id", "kind", "direction", "value_json", "start_t_ns", "end_t_ns", "end_reason"],
        "summary": ["instrument", "range", "fill_count", "closed_trades", "pnl_jpy", "open_trades"],
        "trades": ["instrument", "range", "trade_id", "signal_id", "first_fill_id", "fill_count", "first_t_ns", "last_t_ns", "direction", "levels", "max_position", "hold_ns", "pnl_jpy", "usdjpy", "usdjpy_t_ns", "status", "position", "avg_px"],
    },
}
NA = -1  # an empty time cell
BIG = 2 ** 62  # an end that does not exist (still open at the end of the data)
MAX_ITEMS = {"signals": 1500, "orders": 3000, "fills": 4000, "trades": 2000, "avg": 6000}
MAX_ROWS = 300  # rows per link in a trace
CACHE_RUNS = int(os.environ.get("BT_ROAD_CACHE_RUNS", "3"))

_LOCK = threading.RLock()


class RoadError(ValueError):
    """The road record cannot be shown (the sentence is Japanese and goes to the page)."""


@dataclass
class RoadStatus:
    ok: bool
    reason: str = ""
    schema: Optional[dict] = None
    version: Optional[str] = None
    files: dict = field(default_factory=dict)


def has_road(run_dir: str) -> bool:
    return os.path.isdir(os.path.join(run_dir, ROAD_DIR))


def _road_file(run_dir: str, name: str) -> str:
    if not name or os.sep in name or "/" in name or "\\" in name or ":" in name or name.startswith("."):
        raise RoadError(f"表のファイル名が安全でない: {name!r}")
    return os.path.join(run_dir, ROAD_DIR, name)


def status(run_dir: str) -> RoadStatus:
    """Can this run's road/ be shown? Reads SCHEMA.json only. (ok, reason, schema)."""
    p = os.path.join(run_dir, ROAD_DIR, SCHEMA_FILE)
    if not os.path.isdir(os.path.join(run_dir, ROAD_DIR)):
        return RoadStatus(False, "古い形の走らせ(道の記録 road/ が無い)")
    if not os.path.isfile(p):
        return RoadStatus(False, f"road/{SCHEMA_FILE} が無いので、表の列が分からない。表示しない")
    try:
        with open(p, "r", encoding="utf-8") as fh:
            schema = json.load(fh)
    except (OSError, ValueError) as exc:
        return RoadStatus(False, f"road/{SCHEMA_FILE} が読めない({type(exc).__name__})。表示しない")
    ver = schema.get("version") if isinstance(schema, dict) else None
    if ver not in SUPPORTED:
        return RoadStatus(False, f"知らない版の道の記録 {ver!r}(この画面が読めるのは {' / '.join(SUPPORTED)})。表示しない",
                          schema if isinstance(schema, dict) else None, ver)
    tabs = schema.get("tables")
    if not isinstance(tabs, dict):
        return RoadStatus(False, f"road/{SCHEMA_FILE} に tables が無い。表示しない", schema, ver)
    missing, files = [], {}
    want = EXPECTED_COLUMNS[ver]
    bad = []
    for t in TABLES:
        spec = tabs.get(t)
        if isinstance(spec, dict) and isinstance(spec.get("columns"), list):
            have = [c[0] if isinstance(c, list) and c else None for c in spec["columns"]]
            lost = [c for c in want[t] if c not in have]
            extra = [c for c in have if c not in want[t]]
            if lost or extra:
                bad.append(f"{t}(" + ("欠けた列: " + "・".join(lost) if lost else "") + ("、" if lost and extra else "") +
                           ("知らない列: " + "・".join(str(x) for x in extra) if extra else "") + ")")
    if bad:
        return RoadStatus(False, f"SCHEMA.json の版 {ver} の列の一覧と合わない: " + "、".join(bad) + "。表示しない", schema, ver)
    for t in TABLES:
        spec = tabs.get(t)
        if not isinstance(spec, dict) or not isinstance(spec.get("file"), str) or not isinstance(spec.get("columns"), list):
            missing.append(f"{t}(SCHEMA に無い)")
            continue
        try:
            f = _road_file(run_dir, spec["file"])
        except RoadError as exc:
            return RoadStatus(False, str(exc), schema, ver)
        if not os.path.isfile(f):
            missing.append(f"{t}({spec['file']} がディスクに無い)")
        else:
            files[t] = f
    if missing:
        return RoadStatus(False, "欠けた表がある: " + "、".join(missing) + "。表示しない", schema, ver)
    return RoadStatus(True, "", schema, ver, files)


def columns_of(schema: dict, table: str) -> list[dict]:
    return [{"name": c[0], "unit": c[1], "desc": c[2]} for c in schema["tables"][table]["columns"]]


def _signature(st: RoadStatus) -> tuple:
    out = []
    for t in TABLES:
        p = st.files[t]
        s = os.stat(p)
        out.append((p, s.st_mtime_ns, s.st_size))
    return tuple(out)


_CACHE: "OrderedDict[tuple, RoadData]" = OrderedDict()
_LOAD_LOCKS: dict = {}


def load(run_dir: str) -> "RoadData":
    """The tables of one run, read once and kept by (path, mtime, size) of every file (the three newest runs)."""
    st = status(run_dir)
    if not st.ok:
        raise RoadError(st.reason)
    key = _signature(st)
    with _LOCK:
        if key in _CACHE:
            _CACHE.move_to_end(key)
            return _CACHE[key]
        lock = _LOAD_LOCKS.setdefault(key, threading.Lock())
    with lock:  # two requests for one run read it once: the second waits and finds it in the cache
        with _LOCK:
            if key in _CACHE:
                _CACHE.move_to_end(key)
                return _CACHE[key]
        data = RoadData(run_dir, st)
        with _LOCK:
            _CACHE[key] = data
            while len(_CACHE) > max(1, CACHE_RUNS):
                _CACHE.popitem(last=False)
            _LOAD_LOCKS.pop(key, None)
        return data


def _read_table(path: str, cols: list[str], table: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(path, dtype=str, keep_default_na=False, na_filter=False,
                         compression="gzip" if path.endswith(".gz") else None)
    except (OSError, EOFError, ValueError, pd.errors.ParserError, gzip.BadGzipFile) as exc:
        raise RoadError(f"表 {table} が読めない({type(exc).__name__}: {exc})。表示しない") from None
    if list(df.columns) != cols:
        raise RoadError(f"表 {table} の列が SCHEMA.json の列と違う(CSV: {list(df.columns)[:6]}…)。表示しない")
    return df


class RoadData:
    """All the tables of one run, as strings (pandas) with numeric views made on demand."""

    def __init__(self, run_dir: str, st: RoadStatus) -> None:
        self.dir = run_dir
        self.schema = st.schema
        self.version = st.version
        self.cols = {t: [c[0] for c in st.schema["tables"][t]["columns"]] for t in TABLES}
        self.frames: dict[str, pd.DataFrame] = {t: _read_table(st.files[t], self.cols[t], t) for t in CSV_TABLES}
        try:
            with open(st.files["summary"], "r", encoding="utf-8") as fh:
                self.summary = json.load(fh)
        except (OSError, ValueError) as exc:
            raise RoadError(f"summary.json が読めない({type(exc).__name__})。表示しない") from None
        rows = self.summary.get("rows") if isinstance(self.summary, dict) else None
        if not isinstance(rows, list):
            raise RoadError("summary.json に rows が無い。表示しない")
        self.summary_rows = rows
        self._num: dict = {}
        self._ns: dict = {}
        self._groups: dict = {}
        pairs = set()
        for g in self.summary.get("groups") or []:
            if isinstance(g, list) and len(g) == 2:
                pairs.add((str(g[0]), str(g[1])))
        for r in rows:
            pairs.add((str(r.get("instrument")), str(r.get("range"))))
        for t in CSV_TABLES:
            df = self.frames[t]
            if len(df):
                pairs |= set(map(tuple, df[["instrument", "range"]].drop_duplicates().to_numpy().tolist()))
        self.pairs = sorted(pairs, key=lambda p: (p[0], RANGES.index(p[1]) if p[1] in RANGES else 9, p[1]))
        self.instruments = sorted({p[0] for p in self.pairs})
        self.ranges = [r for r in RANGES if any(p[1] == r for p in self.pairs)] + sorted(
            {p[1] for p in self.pairs} - set(RANGES))
        self.nbytes = int(sum(df.memory_usage(deep=False).sum() for df in self.frames.values()))

    # ---- numeric views ---------------------------------------------------------------------------------------
    def ns(self, table: str, col: str) -> np.ndarray:
        """int64 times (NA = -1 where the cell is empty)."""
        k = (table, col)
        if k not in self._ns:
            s = self.frames[table][col]
            self._ns[k] = pd.to_numeric(s.where(s != "", str(NA)), errors="coerce").fillna(NA).to_numpy(np.int64)
        return self._ns[k]

    def num(self, table: str, col: str) -> np.ndarray:
        """float64 (NaN where empty or not a number)."""
        k = (table, col)
        if k not in self._num:
            self._num[k] = pd.to_numeric(self.frames[table][col], errors="coerce").to_numpy(np.float64)
        return self._num[k]

    def smax(self, table: str) -> np.ndarray:
        """The latest time stamped anywhere in a row (every column whose unit is ns). The seal cuts a row when this is at or
        after the limit: a trade that began before the boundary but closed after it, or a signal that ended after it, shows
        a time of the sealed period and is not shown (not just the row's first time)."""
        k = (table, "__smax__")
        if k not in self._ns:
            cols = [c[0] for c in self.schema["tables"][table]["columns"] if c[1] == "ns"]
            n = len(self.frames[table])
            v = np.max(np.vstack([self.ns(table, c) for c in cols]), axis=0) if cols and n else np.full(n, NA, np.int64)
            if table == "orders" and n:  # an order shows what its fills show: one fill at or after the limit cuts the order row
                f, o = self.frames["fills"], self.frames["orders"]
                kf = (f["instrument"] + "\0" + f["range"] + "\0" + f["order_id"]).to_numpy()
                ko = (o["instrument"] + "\0" + o["range"] + "\0" + o["order_id"]).to_numpy()
                m = pd.Series(self.smax("fills")).groupby(kf).max() if len(f) else pd.Series(dtype=np.int64)
                v = np.maximum(v, pd.Series(ko).map(m).fillna(NA).to_numpy(np.int64))
            self._ns[k] = v
        return self._ns[k]

    def is_open(self, table: str) -> np.ndarray:
        """Rows with no end yet at the end of the data (a signal still on, an order still open, a trade not closed)."""
        k = (table, "__open__")
        if k not in self._ns:
            df = self.frames[table]
            if table == "signals":
                v = self.ns("signals", "end_t_ns") < 0
            elif table == "trades":
                v = (df["status"] != "closed").to_numpy()
            elif table == "orders":
                closed = np.max(np.vstack([self.ns("orders", c) for c in ("canceled_t_ns", "venue_closed_t_ns", "rejected_t_ns", "closed_t_ns")]), axis=0) \
                    if len(df) else np.array([], np.int64)
                st = df["state"].to_numpy()
                v = (closed < 0) & (st != "FILLED") & (st != ZERO_STATE)
            else:
                v = np.zeros(len(df), bool)
            self._ns[k] = np.asarray(v, bool)
        return self._ns[k]

    def visible(self, table: str, limit_ns: int, open_cut: bool = False) -> np.ndarray:
        """Rows that may be shown: every time in the row before the limit, and, when the run crosses the limit (`open_cut`),
        not a row that is still open at the end of the data (it would say what happened after the limit)."""
        m = self.smax(table) < limit_ns
        if open_cut:
            m = m & ~self.is_open(table)
        return m

    def is_numeric(self, table: str, col: str) -> bool:
        s = self.frames[table][col]
        nonempty = (s != "").to_numpy()
        if not nonempty.any():
            return False
        return not bool(np.isnan(self.num(table, col)[nonempty]).any())

    def group(self, inst: str, rng: str) -> "Group":
        k = (inst, rng)
        with _LOCK:
            if k not in self._groups:
                self._groups[k] = Group(self, inst, rng)
            return self._groups[k]


def _rowmax(*arrs: np.ndarray) -> np.ndarray:
    return np.max(np.vstack(arrs), axis=0) if arrs else np.array([], np.int64)


class Group:
    """One (instrument, range): the rows of each table sorted by their start time, with numpy columns."""

    def __init__(self, d: RoadData, inst: str, rng: str) -> None:
        self.d, self.inst, self.rng = d, inst, rng
        self.rows: dict[str, np.ndarray] = {}
        self.key: dict[str, np.ndarray] = {}
        for t in CSV_TABLES:
            df = d.frames[t]
            idx = np.flatnonzero(((df["instrument"] == inst) & (df["range"] == rng)).to_numpy())
            k = d.ns(t, KEY_COL[t])[idx]
            o = np.argsort(k, kind="stable")
            self.rows[t] = idx[o]
            self.key[t] = k[o]
        f, o, s, tr, lf = (d.frames[t] for t in ("fills", "orders", "signals", "trades", "ledger_fills"))
        # signals: interval [start, end]; no end = still on at the end of the data
        r = self.rows["signals"]
        self.sig_start = self.key["signals"]
        e = d.ns("signals", "end_t_ns")[r]
        self.sig_open = e < 0
        self.sig_end = np.where(self.sig_open, BIG, e)
        # orders: [placed, last of cancel / venue close / reject / close notice / last fill]
        r = self.rows["orders"]
        self.ord_start = self.key["orders"]
        closed = _rowmax(*(d.ns("orders", c)[r] for c in ("canceled_t_ns", "venue_closed_t_ns", "rejected_t_ns", "closed_t_ns")))
        fr = self.rows["fills"]
        oid_f = f["order_id"].to_numpy()[fr]
        tf = d.ns("fills", "t_ns")[fr]
        last_fill = pd.Series(tf).groupby(oid_f).max() if len(fr) else pd.Series(dtype=np.int64)
        lf_of = o["order_id"].to_numpy()[r]
        lastf = pd.Series(lf_of).map(last_fill).fillna(NA).to_numpy(np.int64) if len(r) else np.array([], np.int64)
        st = o["state"].to_numpy()[r]
        zero = st == ZERO_STATE
        full = (st == "FILLED")
        # closed -> its closing time (or the last fill); filled -> the last fill; a level not sent -> a point; else still open
        end = np.where(closed >= 0, np.maximum(closed, lastf), np.where(full, lastf, np.where(zero, self.ord_start, BIG)))
        end = np.where(end < 0, self.ord_start, end)
        self.ord_open = end >= BIG
        self.ord_end = end
        rej = d.ns("orders", "rejected_t_ns")[r] >= 0
        can = d.ns("orders", "canceled_t_ns")[r] >= 0
        ven = d.ns("orders", "venue_closed_t_ns")[r] >= 0
        fq = d.num("orders", "filled_qty")[r]
        kind = np.select([zero, rej, full, can, ven, np.nan_to_num(fq) > 0], ["zero", "rejected", "filled", "canceled", "venue_closed", "partial"],
                         default="open")
        self.ord_kind = kind
        # fills / ledger
        self.fl_t = self.key["fills"]
        self.lf_t = self.key["ledger_fills"]
        lr = self.rows["ledger_fills"]
        self.lf_pos = d.num("ledger_fills", "position_after")[lr]
        self.lf_avg = d.num("ledger_fills", "avg_px_after")[lr]
        self.lf_cum = d.num("ledger_fills", "pnl_jpy_cum")[lr]
        # trades: [first, last] (open: until the end of the data)
        r = self.rows["trades"]
        self.tr_start = self.key["trades"]
        e = d.ns("trades", "last_t_ns")[r]
        self.tr_open = (tr["status"].to_numpy()[r] != "closed")
        self.tr_end = np.where(self.tr_open, BIG, e)
        self.tr_pnl = d.num("trades", "pnl_jpy")[r]
        # price extent of each trade: min / max of its fills' prices (ledger_fills.px by trade_id)
        if len(lr):
            px = d.num("ledger_fills", "px")[lr]
            tid_c = lf["trade_id"].to_numpy()[lr]
            opn = lf["opens_trade_id"].to_numpy()[lr]
            has = opn != ""
            both = pd.DataFrame({"t": np.r_[tid_c, opn[has]], "px": np.r_[px, px[has]]})  # a fill that opens a trade is in it too (ドテン)
            g = both.groupby("t")["px"].agg(["min", "max"])
            tid = tr["trade_id"].to_numpy()[r]
            self.tr_lo = pd.Series(tid).map(g["min"]).to_numpy(np.float64)
            self.tr_hi = pd.Series(tid).map(g["max"]).to_numpy(np.float64)
        else:
            self.tr_lo = self.tr_hi = np.full(len(r), np.nan)

    # ---- cuts ----------------------------------------------------------------------------------------------
    def ok(self, table: str, limit_ns: int, open_cut: bool = False) -> np.ndarray:
        """Positions (into this group's arrays of the table) of the rows that may be shown (RoadData.visible)."""
        return np.flatnonzero(self.d.visible(table, limit_ns, open_cut)[self.rows[table]])

    def df(self, table: str, limit_ns: int = BIG, open_cut: bool = False) -> pd.DataFrame:
        return self.d.frames[table].iloc[self.rows[table][self.ok(table, limit_ns, open_cut)]]


def _ts(ns: np.ndarray) -> list:
    return [float(x) / 1e9 for x in ns]


def _end_s(e: int, hi_ns: int) -> float:
    return float(min(e, hi_ns)) / 1e9


def _overlap(start: np.ndarray, end: np.ndarray, lo: int, hi: int, okpos: np.ndarray) -> np.ndarray:
    """Positions (within okpos' rows) of the intervals that touch [lo, hi]."""
    st, en = start[okpos], end[okpos]
    return okpos[(st <= hi) & (en >= lo)]


def _bucket_last(t_ns: np.ndarray, interval_s: int) -> np.ndarray:
    """Index of the last row of each display bucket (a row is shown in the bucket it falls in)."""
    if t_ns.size == 0:
        return np.array([], np.int64)
    b = (t_ns - 1) // (interval_s * 10**9)  # an event stamped at a bar's END belongs to that bar (as in the chart above)
    return np.flatnonzero(np.r_[b[1:] != b[:-1], True])


def layers(g: Group, lo_ns: int, hi_ns: int, limit_ns: int, interval_s: int, last_ns: Optional[int] = None) -> dict:
    """The chart layers of one (instrument, range) for the visible range [lo_ns, hi_ns], rows before `limit_ns` only.
    A layer with more than MAX_ITEMS[layer] items in the range is not sent ('too_many'); the page asks for a closer look.
    An interval whose end does not exist (a signal still on, an order still open, a trade still open) ends at the end of
    the data (`last_ns`) or, without it, at the right edge of the range."""
    d = g.d
    hi_cut = min(hi_ns, limit_ns - 1)
    far = hi_cut if last_ns is None else min(last_ns, limit_ns)
    oc = last_ns is not None and last_ns >= limit_ns  # the run crosses the limit: rows still open at its end are not shown
    out: dict = {"counts": {}, "too_many": {}}
    # signals
    ix = _overlap(g.sig_start, g.sig_end, lo_ns, hi_ns, g.ok("signals", limit_ns, oc))
    out["counts"]["signals"] = int(ix.size)
    if ix.size > MAX_ITEMS["signals"]:
        out["too_many"]["signals"] = int(ix.size)
        out["signals"] = []
    else:
        df = d.frames["signals"]
        rows = g.rows["signals"][ix]
        sub = df.iloc[rows]
        out["signals"] = [{"row": int(r), "id": a, "kind": b, "direction": c, "value": v, "reason": rs, "t0": float(s) / 1e9,
                           "t1": _end_s(int(e) if e < BIG else far, far), "open": bool(op)}
                          for r, a, b, c, v, rs, s, e, op in zip(rows, sub["signal_id"], sub["kind"], sub["direction"],
                                                                 sub["value_json"], sub["end_reason"], g.sig_start[ix],
                                                                 g.sig_end[ix], g.sig_open[ix])]
    # orders (a limit order is a horizontal line at its sent price from placed to closed; zero-quantity ones a mark)
    ix = _overlap(g.ord_start, g.ord_end, lo_ns, hi_ns, g.ok("orders", limit_ns, oc))
    out["counts"]["orders"] = int(ix.size)
    if ix.size > MAX_ITEMS["orders"]:
        out["too_many"]["orders"] = int(ix.size)
        out["orders"] = []
    else:
        df = d.frames["orders"]
        rows = g.rows["orders"][ix]
        sub = df.iloc[rows]
        sent = pd.to_numeric(sub["sent_limit_px"], errors="coerce").to_numpy(np.float64)
        raw = pd.to_numeric(sub["limit_px"], errors="coerce").to_numpy(np.float64)
        px = np.where(np.isnan(sent), raw, sent)
        items = []
        for k, r in enumerate(rows):
            if np.isnan(px[k]):
                continue  # a market order has no price line (its fill is in the fills layer)
            e = int(g.ord_end[ix][k])
            items.append({"row": int(r), "id": sub["order_id"].iat[k], "signal": sub["signal_id"].iat[k], "side": sub["side"].iat[k],
                          "px": float(px[k]), "t0": float(g.ord_start[ix][k]) / 1e9, "t1": _end_s(e if e < BIG else far, far),
                          "kind": str(g.ord_kind[ix][k]), "qty": sub["qty"].iat[k], "filled": sub["filled_qty"].iat[k],
                          "levels": sub["levels"].iat[k], "state": sub["state"].iat[k], "close_reason": sub["close_reason"].iat[k],
                          "exit_kind": sub["exit_kind"].iat[k], "open": bool(g.ord_open[ix][k])})
        out["orders"] = items
    # fills (points)
    okf = g.ok("fills", limit_ns, oc)
    a = int(np.searchsorted(g.fl_t[okf], lo_ns, side="left"))
    e = int(np.searchsorted(g.fl_t[okf], hi_cut, side="right"))
    pf = okf[a:e]
    out["counts"]["fills"] = int(pf.size)
    if pf.size > MAX_ITEMS["fills"]:
        out["too_many"]["fills"] = int(pf.size)
        out["fills"] = []
    else:
        rows = g.rows["fills"][pf]
        sub = d.frames["fills"].iloc[rows]
        px = d.num("fills", "px")[rows]
        out["fills"] = [{"row": int(r), "id": i, "order": o, "signal": s, "side": sd, "qty": q, "px": float(p), "t": float(t) / 1e9,
                         "liquidity": lq, "case": fc, "rule": fr}
                        for r, i, o, s, sd, q, p, t, lq, fc, fr in zip(rows, sub["fill_id"], sub["order_id"], sub["signal_id"],
                                                                      sub["side"], sub["qty"], px, g.fl_t[pf], sub["liquidity"],
                                                                      sub["fill_case"], sub["fill_rule"])]
    # average entry price (a step line from the ledger) and the two lower lines
    okl = g.ok("ledger_fills", limit_ns, oc)
    lt, lpos, lavg, lcum = g.lf_t[okl], g.lf_pos[okl], g.lf_avg[okl], g.lf_cum[okl]
    a = int(np.searchsorted(lt, lo_ns, side="left"))
    e = int(np.searchsorted(lt, hi_cut, side="right"))
    out["counts"]["avg"] = max(0, e - a)
    base_pos = float(lpos[a - 1]) if a > 0 else 0.0
    base_cum = float(lcum[a - 1]) if a > 0 else 0.0
    base_avg = float(lavg[a - 1]) if a > 0 and not np.isnan(lavg[a - 1]) else None
    if e - a > MAX_ITEMS["avg"]:
        out["too_many"]["avg"] = e - a
        out["avg"] = []
    else:
        out["avg"] = ([[lo_ns / 1e9, base_avg]] if a > 0 else []) + [
            [float(t) / 1e9, None if np.isnan(v) else float(v)] for t, v in zip(lt[a:e], lavg[a:e])]
    pts_t = lt[a:e]
    keep = _bucket_last(pts_t, interval_s)
    b0 = int((lo_ns - 1) // (interval_s * 10**9) * interval_s)
    pos = {b0: base_pos}
    cum = {b0: base_cum}
    for i in keep:
        k = int((pts_t[i] - 1) // (interval_s * 10**9) * interval_s)
        pos[k] = float(lpos[a + i])
        cum[k] = float(lcum[a + i])
    out["pos"] = [[k, v] for k, v in sorted(pos.items())]
    out["cum"] = [[k, v] for k, v in sorted(cum.items())]
    # trades (a box from the first to the last fill, over the prices of its fills)
    ix = _overlap(g.tr_start, g.tr_end, lo_ns, hi_ns, g.ok("trades", limit_ns, oc))
    out["counts"]["trades"] = int(ix.size)
    if ix.size > MAX_ITEMS["trades"]:
        out["too_many"]["trades"] = int(ix.size)
        out["trades"] = []
    else:
        rows = g.rows["trades"][ix]
        sub = d.frames["trades"].iloc[rows]
        out["trades"] = [{"row": int(r), "id": i, "signal": s, "direction": dr, "levels": lv, "status": stt, "pnl": None if np.isnan(p) else float(p),
                          "t0": float(t0) / 1e9, "t1": _end_s(int(t1) if t1 < BIG else far, far), "lo": None if np.isnan(l) else float(l),
                          "hi": None if np.isnan(h) else float(h), "open": bool(op), "hold_ns": hn}
                         for r, i, s, dr, lv, stt, p, t0, t1, l, h, op, hn in zip(
                             rows, sub["trade_id"], sub["signal_id"], sub["direction"], sub["levels"], sub["status"], g.tr_pnl[ix],
                             g.tr_start[ix], g.tr_end[ix], g.tr_lo[ix], g.tr_hi[ix], g.tr_open[ix], sub["hold_ns"])]
    return out


# ---- the table screen ------------------------------------------------------------------------------------------
OPS = ("contains", "eq", "ne", "gt", "ge", "lt", "le", "empty", "nonempty")
OPS_JA = {"contains": "含む", "eq": "=", "ne": "≠", "gt": ">", "ge": "≥", "lt": "<", "le": "≤", "empty": "空", "nonempty": "空でない"}


def table_columns(d: RoadData, table: str) -> list[dict]:
    cols = columns_of(d.schema, table)
    for c in cols:
        c["numeric"] = bool(table != "summary" and d.is_numeric(table, c["name"]))
    return cols


def _mask_scope(d: RoadData, table: str, inst: Optional[str], rng: Optional[str], limit_ns: int, open_cut: bool = False) -> np.ndarray:
    df = d.frames[table]
    m = np.ones(len(df), bool)
    if inst:
        m &= (df["instrument"] == inst).to_numpy()
    if rng and rng != "all":
        m &= (df["range"] == rng).to_numpy()
    m &= d.visible(table, limit_ns, open_cut)  # a row with any time at or after the limit is never shown
    return m


def _unit(d: RoadData, table: str, col: str) -> str:
    return next((c[1] for c in d.schema["tables"][table]["columns"] if c[0] == col), "-")


def _natural_order(v: np.ndarray) -> np.ndarray:
    """Order strings of the form <prefix><number> (road-2 before road-10) by prefix, then by the number."""
    ser = pd.Series(v.astype(str))
    ex = ser.str.extract(r"^(.*?)(\d+)$")
    pre = ex[0].fillna(ser).to_numpy().astype(str)
    num = pd.to_numeric(ex[1]).fillna(-1).to_numpy(np.float64)
    return np.lexsort((num, pd.factorize(pre, sort=True)[0]))


def table_page(d: RoadData, table: str, inst: Optional[str] = None, rng: Optional[str] = None, limit_ns: int = BIG,
               sort: Optional[str] = None, desc: bool = False, filters: Optional[list] = None, page: int = 0,
               size: int = 100, open_cut: bool = False, cut_summary: bool = False) -> dict:
    if table not in TABLES:
        raise RoadError(f"表の名前が違う: {table!r}")
    size = max(1, min(int(size), 1000))
    cols = table_columns(d, table)
    names = [c["name"] for c in cols]
    if table == "summary":
        if cut_summary:
            raise RoadError(SUMMARY_CUT_REASON)
        rows = [{n: ("" if r.get(n) is None else str(r.get(n))) for n in names} for r in d.summary_rows]
        keep = [i for i, r in enumerate(rows) if (not inst or r["instrument"] == inst) and (not rng or rng == "all" or r["range"] == rng)]
        for i in keep:
            rows[i]["_row"] = i
        sel = [rows[i] for i in keep]
        return {"table": table, "columns": cols, "rows": [[r[n] for n in names] for r in sel], "row_ids": [r["_row"] for r in sel],
                "total": len(rows), "matched": len(sel), "page": 0, "pages": 1, "size": size, "sort": None, "desc": False}
    df = d.frames[table]
    m = _mask_scope(d, table, inst, rng, limit_ns, open_cut)
    total = int(m.sum())
    for f in filters or []:
        if not (isinstance(f, (list, tuple)) and len(f) == 3):
            raise RoadError(f"絞り込みの形が違う: {f!r}")
        col, op, val = f
        if col not in names:
            raise RoadError(f"絞り込みの列が無い: {col!r}")
        if op not in OPS:
            raise RoadError(f"絞り込みの種類が無い: {op!r}(使えるのは {', '.join(OPS)})")
        s = df[col]
        if op == "contains":
            m &= s.str.contains(str(val), regex=False).to_numpy()
        elif op == "empty":
            m &= (s == "").to_numpy()
        elif op == "nonempty":
            m &= (s != "").to_numpy()
        elif op in ("eq", "ne") and not d.is_numeric(table, col) and _unit(d, table, col) != "ns":
            m &= ((s == str(val)) if op == "eq" else (s != str(val))).to_numpy()
        elif _unit(d, table, col) == "ns":  # a time is an int64 of ns: compared as one (a float loses the last digits)
            try:
                xi = int(str(val).strip())
            except ValueError:
                raise RoadError(f"時刻(ns)の列は整数で比べる: {val!r}(列 {col})") from None
            v = d.ns(table, col)
            m &= {"eq": v == xi, "ne": v != xi, "gt": v > xi, "ge": v >= xi, "lt": v < xi, "le": v <= xi}[op]
        else:
            try:
                x = float(val)
            except (TypeError, ValueError):
                raise RoadError(f"数で比べる絞り込みに数でない値: {val!r}(列 {col})") from None
            v = d.num(table, col)
            with np.errstate(invalid="ignore"):
                m &= {"eq": v == x, "ne": v != x, "gt": v > x, "ge": v >= x, "lt": v < x, "le": v <= x}[op]
    idx = np.flatnonzero(m)
    if sort:
        if sort not in names:
            raise RoadError(f"並べ替えの列が無い: {sort!r}")
        if d.is_numeric(table, sort):
            v = d.num(table, sort)[idx]
            order = np.argsort(np.where(np.isnan(v), np.inf, -v if desc else v), kind="stable")
        else:
            v = df[sort].to_numpy()[idx]
            order = _natural_order(v)
            if desc:
                order = order[::-1]
        idx = idx[order]
    matched = int(idx.size)
    pages = max(1, -(-matched // size))
    page = max(0, min(int(page), pages - 1))
    sel = idx[page * size:(page + 1) * size]
    sub = df.iloc[sel]
    return {"table": table, "columns": cols, "rows": sub.to_numpy().tolist(), "row_ids": [int(x) for x in sel], "total": total,
            "matched": matched, "page": page, "pages": pages, "size": size, "sort": sort, "desc": bool(desc)}


# ---- following the ids ------------------------------------------------------------------------------------------
def _rows_out(d: RoadData, table: str, idx: np.ndarray) -> dict:
    idx = np.asarray(idx, np.int64)
    names = d.cols[table]
    sel = idx[:MAX_ROWS]
    return {"table": table, "label": TABLE_JA[table], "columns": names, "count": int(idx.size),
            "rows": d.frames[table].iloc[sel].to_numpy().tolist(), "row_ids": [int(x) for x in sel]}


def _in_scope(d: RoadData, table: str, inst: Optional[str], rng: Optional[str], pairs: list) -> np.ndarray:
    """Rows of one (instrument, range) whose column `col` is in `vals`, for any of the (col, vals) pairs (an OR)."""
    df = d.frames[table]
    base = ((df["instrument"] == inst) & (df["range"] == rng)).to_numpy()
    hit = np.zeros(len(df), bool)
    for col, vals in pairs:
        vals = [v for v in set(vals) if v != ""]
        if vals:
            hit |= df[col].isin(vals).to_numpy()
    return np.flatnonzero(base & hit)


def trace(d: RoadData, table: str, row: int, limit_ns: int = BIG, open_cut: bool = False) -> dict:
    """The row, and the rows tied to it by numbers (signal_id / order_id / fill_id / trade_id), all of the same
    (instrument, range). trade -> its fills (ledger_fills, fills), orders, signals; order -> its signal, fills, trades,
    attached orders; signal -> its orders, fills, trades; fill -> its order, signal, ledger row, trade. A fill that closes
    one trade and opens the next (ドテン) belongs to both: ledger_fills.trade_id is the one it closed, opens_trade_id the one
    it opened, and trades.first_fill_id is the first fill of a trade. Rows the seal cuts are not in a link (RoadData.visible)."""
    if table not in CSV_TABLES:
        raise RoadError(f"この表の行はたどれない: {table!r}")
    df = d.frames[table]
    if not (0 <= row < len(df)):
        raise RoadError(f"行 {row} が無い(表 {table} は {len(df)} 行)")
    if not d.visible(table, limit_ns, open_cut)[row]:
        raise RoadError("この行には封印の境以後の時刻がある(または境をまたぐ走らせの終わりまで開いたまま)。出さない")
    r = df.iloc[row]
    inst, rng = r["instrument"], r["range"]
    links: list[dict] = []

    def add(t: str, pairs: list, label: Optional[str] = None) -> np.ndarray:
        ix = _in_scope(d, t, inst, rng, pairs)
        ix = ix[d.visible(t, limit_ns, open_cut)[ix]]
        out = _rows_out(d, t, ix)
        if label:
            out["label"] = label
        links.append(out)
        return ix

    def vals(t: str, ix: np.ndarray, col: str) -> list:
        return d.frames[t][col].to_numpy()[ix].tolist()

    def trade_ids(lf: np.ndarray) -> list:
        return vals("ledger_fills", lf, "trade_id") + vals("ledger_fills", lf, "opens_trade_id")

    def lf_of_fills(f: np.ndarray) -> np.ndarray:
        return _in_scope(d, "ledger_fills", inst, rng, [("fill_id", vals("fills", f, "fill_id"))])

    if table == "signals":
        sid = r["signal_id"]
        add("orders", [("signal_id", [sid])])
        f = add("fills", [("signal_id", [sid])])
        lf = lf_of_fills(f)
        tix = _in_scope(d, "trades", inst, rng, [("signal_id", [sid]), ("trade_id", trade_ids(lf))])
        tix = tix[d.visible("trades", limit_ns, open_cut)[tix]]
        links.append(_rows_out(d, "trades", tix))
    elif table == "orders":
        oid = r["order_id"]
        add("signals", [("signal_id", [r["signal_id"]] if r["signal_id"] != NO_SIGNAL else [])])
        f = add("fills", [("order_id", [oid])])
        lf = add("ledger_fills", [("fill_id", vals("fills", f, "fill_id"))])
        add("trades", [("trade_id", trade_ids(lf))])
        add("orders", [("attached_to", [oid])], "注文(この注文に付いた決済の注文)")
        if r["attached_to"]:
            add("orders", [("order_id", [r["attached_to"]])], "注文(この決済の親の建ての注文)")
    elif table == "fills":
        add("orders", [("order_id", [r["order_id"]])])
        add("signals", [("signal_id", [r["signal_id"]] if r["signal_id"] != NO_SIGNAL else [])])
        lf = add("ledger_fills", [("fill_id", [r["fill_id"]])])
        add("trades", [("trade_id", trade_ids(lf))])
    elif table == "ledger_fills":
        add("fills", [("fill_id", [r["fill_id"]])])
        add("trades", [("trade_id", [r["trade_id"], r["opens_trade_id"]])])
    elif table == "trades":
        tid = r["trade_id"]
        lf = add("ledger_fills", [("trade_id", [tid]), ("opens_trade_id", [tid])])
        f = add("fills", [("fill_id", vals("ledger_fills", lf, "fill_id") + [r["first_fill_id"]])])
        add("orders", [("order_id", vals("fills", f, "order_id"))])
        add("signals", [("signal_id", [r["signal_id"]] + vals("fills", f, "signal_id"))])
    t_ns = int(d.ns(table, KEY_COL[table])[row])
    end_ns = None
    if table == "trades" and r["status"] == "closed":
        end_ns = int(d.ns("trades", "last_t_ns")[row])
    elif table == "signals" and r["end_t_ns"]:
        end_ns = int(r["end_t_ns"])
    return {"table": table, "row": int(row), "record": {n: r[n] for n in d.cols[table]}, "instrument": inst, "range": rng,
            "t_s": None if t_ns < 0 else t_ns / 1e9, "t_end_s": None if end_ns is None else end_ns / 1e9, "links": links}


# ---- the headline numbers ---------------------------------------------------------------------------------------
def _q(v: np.ndarray, qs=(0, 5, 25, 50, 75, 95, 100)) -> Optional[list]:
    if v.size == 0:
        return None
    return [[q, float(np.percentile(v, q))] for q in qs]


def _fnum(x) -> Optional[float]:
    return None if x is None or (isinstance(x, float) and not np.isfinite(x)) else float(x)


def headline(d: RoadData, g: Group, limit_ns: int = BIG, open_cut: bool = False) -> dict:
    """Numbers of one (instrument, range) computed from the tables (rows before `limit_ns` only), each with its formula."""
    tr = g.df("trades", limit_ns, open_cut)
    closed = tr[tr["status"] == "closed"]
    opened = tr[tr["status"] != "closed"]
    pnl = pd.to_numeric(closed["pnl_jpy"], errors="coerce").to_numpy(np.float64)
    hold = pd.to_numeric(closed["hold_ns"], errors="coerce").to_numpy(np.float64) / 6e10  # minutes
    lev = pd.to_numeric(closed["levels"], errors="coerce").to_numpy(np.float64)
    wins, losses = int((pnl > 0).sum()), int((pnl < 0).sum())
    out: dict = {"instrument": g.inst, "range": g.rng}
    out["trades"] = {
        "closed": int(len(closed)), "open": int(len(opened)), "wins": wins, "losses": losses, "flat": int((pnl == 0).sum()),
        "win_rate": (wins / len(closed)) if len(closed) else None,
        "pnl_sum": _fnum(pnl.sum()) if len(closed) else None, "pnl_mean": _fnum(pnl.mean()) if len(closed) else None,
        "pnl_dist": _q(pnl), "hold_min_dist": _q(hold[~np.isnan(hold)]),
        "levels_dist": [[int(k), int(v)] for k, v in pd.Series(lev[~np.isnan(lev)]).value_counts().sort_index().items()],
        "formulas": {
            "closed": "trades の status = closed の行数(建玉 0 → 0 を 1 取引。途中の取引は含めない)",
            "wins": "closed のうち pnl_jpy > 0 の数 / losses = pnl_jpy < 0 の数 / win_rate = wins ÷ closed",
            "pnl_sum": "closed の pnl_jpy の合計(円。経費は入っていない)",
            "pnl_dist": "closed の pnl_jpy の 0・5・25・50・75・95・100 パーセンタイル(線形補間)",
            "hold_min_dist": "closed の hold_ns ÷ 60,000,000,000(分)の同じパーセンタイル",
            "levels_dist": "closed の levels(段の数 = 建てる向きの約定の数)ごとの取引の数",
        }}
    # per signal
    sg = g.df("signals", limit_ns, open_cut)
    n_sig = int(len(sg))
    sig_ids = [s for s in closed["signal_id"].tolist() if s and s != NO_SIGNAL]
    per_sig = pd.DataFrame({"s": [s for s in closed["signal_id"].tolist()], "p": pnl}).groupby("s")["p"].sum() if len(closed) else pd.Series(dtype=float)
    traded = set(per_sig.index) - {NO_SIGNAL, ""}
    with_trade = len(traded & set(sg["signal_id"].tolist()))
    out["signals"] = {
        "count": n_sig, "with_closed_trade": with_trade, "without_closed_trade": n_sig - with_trade,
        "pnl_per_signal_mean": _fnum(per_sig[list(traded)].mean()) if traded else None,
        "pnl_per_signal_dist": _q(per_sig[list(traded)].to_numpy(np.float64)) if traded else None,
        "formulas": {
            "count": "signals の行数",
            "with_closed_trade": "closed の取引の signal_id(最初の約定の合図)になっている合図の数",
            "pnl_per_signal_mean": "合図ごとに、その合図が最初の約定の合図である closed の取引の pnl_jpy を足し、その平均(取引のある合図だけ)",
        }}
    _ = sig_ids
    # orders
    od = g.df("orders", limit_ns, open_cut)
    state = od["state"].to_numpy()
    zero = state == ZERO_STATE
    fq = pd.to_numeric(od["filled_qty"], errors="coerce").fillna(0).to_numpy(np.float64)
    sent = ~zero
    unfilled = sent & (fq <= 0)
    kinds = g.ord_kind[g.ok("orders", limit_ns, open_cut)]
    out["orders"] = {
        "count": int(len(od)), "zero_qty": int(zero.sum()), "sent": int(sent.sum()), "unfilled": int(unfilled.sum()),
        "unfilled_ratio": (float(unfilled.sum()) / float(sent.sum())) if sent.sum() else None,
        "unfilled_by": {k: int(((kinds == k) & unfilled).sum()) for k in ("canceled", "venue_closed", "rejected", "open")},
        "formulas": {
            "zero_qty": "orders の state = 「量が 0 で出さない」の行数(出していない段)",
            "unfilled": "出した注文(zero_qty でない)のうち filled_qty = 0 の数",
            "unfilled_ratio": "unfilled ÷ 出した注文の数(出した注文 = orders の行数 − zero_qty)",
        }}
    # fills and fees
    fl = g.df("fills", limit_ns, open_cut)
    fee = pd.to_numeric(fl["fee"], errors="coerce").fillna(0).to_numpy(np.float64)
    out["fills"] = {
        "count": int(len(fl)), "fee_sum": _fnum(fee.sum()),
        "liquidity": {k: int(v) for k, v in fl["liquidity"].value_counts().items()},
        "case": {(k or "(空)"): int(v) for k, v in fl["fill_case"].value_counts().items()},
        "formulas": {
            "fee_sum": "fills の fee の合計(口座の通貨)。帳簿の損益(pnl_jpy)には入っていない(L-741)。経費の前の損益",
            "liquidity": "fills の liquidity(maker / taker)ごとの数 / case = fill_case ごとの数",
        }}
    # a drawdown of the cumulative realised profit (ledger_fills.pnl_jpy_cum)
    cum = g.lf_cum[g.ok("ledger_fills", limit_ns, open_cut)]
    cum = cum[~np.isnan(cum)]
    out["drawdown"] = {"max": _fnum((np.maximum.accumulate(np.r_[0.0, cum]) - np.r_[0.0, cum]).max()) if cum.size else None,
                       "formula": "ledger_fills の pnl_jpy_cum(確定損益の累計。0 から始める)の、それまでの最大からの落ち込みの最大(円)"}
    return out


def summary_rows(d: RoadData) -> list[dict]:
    return [dict(r) for r in d.summary_rows]


# ---- the run's record.json ---------------------------------------------------------------------------------------
_REC: "OrderedDict[tuple, dict]" = OrderedDict()  # (record path, mtime_ns, size) -> the fields the tab reads
RECORD_KEEP = ("config", "data", "engine", "git_sha", "diff_hash", "purpose", "currency", "setup", "seed", "version")


def record_of(run_dir: str) -> dict:
    p = os.path.join(run_dir, "record.json")
    st = os.stat(p)
    key = (p, st.st_mtime_ns, st.st_size)
    with _LOCK:
        if key in _REC:
            _REC.move_to_end(key)
            return _REC[key]
    with open(p, "r", encoding="utf-8") as fh:
        rec = json.load(fh)
    keep = {k: rec[k] for k in RECORD_KEEP if k in rec}
    with _LOCK:
        _REC[key] = keep
        while len(_REC) > 1200:
            _REC.popitem(last=False)
    return keep


def engine_period(rec: dict, inst: Optional[str] = None) -> tuple[Optional[int], Optional[int]]:
    """(first_time_ns, last_time_ns) from record.json's engine: {range: {instrument: {first_time_ns, last_time_ns}}} (the
    road runs of bot.bt.pipeline), or a flat engine. With `inst`, only that instrument's entries."""
    first: list = []
    last: list = []

    def walk(o: Any, name: Optional[str]) -> None:
        if not isinstance(o, dict):
            return
        if "first_time_ns" in o and "last_time_ns" in o and (inst is None or name == inst):
            if type(o["first_time_ns"]) is int and type(o["last_time_ns"]) is int:
                first.append(o["first_time_ns"])
                last.append(o["last_time_ns"])
        for k, v in o.items():
            if isinstance(v, dict):
                walk(v, k)

    eng = rec.get("engine") or {}
    walk(eng, None)
    if not first and inst is not None:
        return engine_period(rec, None)
    return (min(first) if first else None), (max(last) if last else None)
