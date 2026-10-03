"""The data behind the dashboard's バックテスト tab: the theme tree, the family axes, and the chart of one run.

    catalog(runs_dir)                        -> {themes: [{id, title, summary, sources, strategies: [{id, title, description,
                                                sources, axes: [{key, label, source, values: [{value, label, note}]}],
                                                runs: [{run_id, group, axes: {key: value}}], default_run_id}]}], ...}
    run_summary(runs_dir, run_id, root)      -> {stats, currency, period, ranges, price: {...}} or {blocked: reason}
    run_chart(runs_dir, run_id, ...)         -> {bars, pnl, trades, interval_s, ...} for the visible range only

Axes and their values are read from each run's record.json (backtest_themes.AXES says which config key is which axis
and what it means); the ledger only groups the runs.

Prices (L-D06). A run's chart does not read the run's own data files. Each instrument has ONE price store (MARKETS:
one row per exchange and symbol, files in git); the store is built once from its 1-minute files (read through the data
layer's door, SealRegistry.read_checked, after the seal boundary cut) into the display frames FRAMES (1 m, 5 m, 15 m,
1 h, 4 h, 1 d), cached on disk outside the repository (_cache_root), and a chart request only slices the visible range
of the frame the page asked for. A run supplies its trades only. When the bars a run read are not the store's bars
(derived files) the page says so (FALLBACK_NOTE).

Seal. The boundary is computed as scripts/share_backtest_runs.py computes it (seal_rule over bot.bt.data.allowlist.
SealRegistry: the earliest cutoff of the crypto / fx units); a ledger that cannot be read, or a unit the rule does not
know, blocks everything (SealBlocked: no price, no trade, the reason is shown). Layers, each cutting on its own: a
file is read only through read_checked and its rows at or after the boundary are dropped when parsed; a cached frame
is cut again when it is loaded; a chart request cuts again at the index; the trades of a run are cut at
limit_ns = boundary (+1 ns when every data entry of the run is a bar, as share_backtest_runs.reaches does) when they are
loaded, and again in the chart. A run that lies wholly after the boundary shows no number.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shutil
import sys
import threading
import time
import zlib
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import numpy as np

from bot.bt.data.allowlist import DEFAULT_ALLOWLIST
from bot.bt.data.errors import PathRefused
from bot.monitoring import backtest_cards as CARDS
from bot.monitoring import backtest_themes as T
from bot.monitoring import backtest_view as BV

REPO_ROOT = Path(__file__).resolve().parents[3]

#: display frames (s) a store is built for, smallest first. A chart request uses one of these.
FRAMES = (60, 300, 900, 3600, 14400, 86400)
INTERVALS = FRAMES
DEFAULT_MAX_BARS = 1200
HARD_MAX_BARS = 20000  # 4-hour bars of 2015-2023 (about 19,700) fit
MAX_TRADES = 2000  # more trades than this in the visible range: none are sent, the page asks for a closer look

#: The price stores: one row per exchange and symbol (the symbol is a run's config.instrument). Only files in git
#: (checked with `git ls-files backtest_data/<dir>` on 2026-10-03). A symbol of another exchange or market (USDJPY, ...)
#: is one more row: "dir" + "pattern" (a file per year, the year in group 1) or "files" (explicit paths), "cols" =
#: (time, open, high, low, close) as the files name them, "label" shown on the page.
MARKETS: dict[str, dict] = {
    "XBTUSD": {"label": "BitMEX XBTUSD", "files": ["backtest_data/k1_newenv_a_20260927/xbtusd_1m_2017_2019.csv.gz"],
               "cols": ("start_ts", "o", "h", "l", "c")},
    "FX_BTC_JPY": {"label": "bitFlyer FX_BTC_JPY", "dir": "backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906",
                   "pattern": r"candles_1m_(\d{4})\.csv\.gz", "cols": ("ts", "open", "high", "low", "close")},
    "BTC_JPY": {"label": "bitFlyer BTC_JPY(現物)", "dir": "backtest_data/bitflyer_lightchart_BTC_JPY_1m_20260906",
                "pattern": r"candles_1m_(\d{4})\.csv\.gz", "cols": ("ts", "open", "high", "low", "close")},
    "BTCUSDT": {"label": "Binance BTCUSDT", "dir": "backtest_data/binance_BTCUSDT_1m_20170801_20231231",
                "pattern": r"binance_BTCUSDT_1m_(\d{4})\.csv\.gz", "cols": ("open_time", "open", "high", "low", "close")},
}
FALLBACK_NOTE = "価格は元の 1 分足から作った。実行が読んだ足と同じではない"
CACHE_MAX_MB = 1024

_LOCK = threading.RLock()


class ChartError(ValueError):
    pass


class SealBlocked(ChartError):
    """The seal boundary cannot be decided: nothing is shown."""


class AfterSeal(ChartError):
    """The run lies wholly after the seal boundary: no number is shown."""


# ---- the catalog ----------------------------------------------------------------------------------------------
_REC: "OrderedDict[tuple, dict]" = OrderedDict()  # (record path, mtime_ns, size) -> the fields the tab reads


def _record(d: str) -> dict:
    p = os.path.join(d, "record.json")
    st = os.stat(p)
    key = (p, st.st_mtime_ns, st.st_size)
    with _LOCK:
        if key in _REC:
            _REC.move_to_end(key)
            return _REC[key]
    with open(p, "r", encoding="utf-8") as fh:
        rec = json.load(fh)
    keep = {k: rec[k] for k in ("config", "data", "engine", "git_sha", "diff_hash", "purpose", "currency", "setup") if k in rec}
    with _LOCK:
        _REC[key] = keep
        while len(_REC) > 1200:
            _REC.popitem(last=False)
    return keep


def _label(axis: dict, value: str) -> tuple[str, str]:
    known = axis["values"].get(value)
    if known:
        return known[0], known[1]
    if axis.get("unit") and value not in ("—", None):
        return f"{value} {axis['unit']}", ""
    return str(value), ""


def _axis_values(runs: list[dict], key: str) -> Optional[list[str]]:
    vals = {r["raw"].get(key) for r in runs}
    vals.discard(None)
    if not vals:
        return None
    ax = T.AXES[key]
    try:
        return [str(v) for v in sorted(vals, key=lambda v: ax["order"](v))]
    except Exception:  # noqa: BLE001 -- a value the order key cannot read: plain string order
        return sorted(str(v) for v in vals)


def _strategy_entry(st: dict, runs: list[dict], theme_title: str) -> dict:
    keys = [k for k in st["axes"] if k != "version"]
    for r in runs:
        r["axes"] = {k: ("—" if r["raw"].get(k) is None else str(r["raw"][k])) for k in keys}
    seen: dict[tuple, int] = {}
    for r in runs:
        combo = tuple(r["axes"][k] for k in keys)
        seen[combo] = seen.get(combo, 0) + 1
    if "version" in st["axes"] and any(n > 1 for n in seen.values()):
        keys.append("version")
        for r in runs:
            r["axes"]["version"] = "—" if r["raw"].get("version") is None else str(r["raw"]["version"])
    axes = []
    for k in keys:
        spec = T.AXES[k]
        values = _axis_values(runs, k)
        if values is None:
            continue
        if "—" in {r["axes"][k] for r in runs} and "—" not in values:
            values.append("—")
        entries = []
        for v in values:
            lab, note = _label(spec, v)
            entries.append({"value": v, "label": lab, "note": note})
        axes.append({"key": k, "label": spec["label"], "source": spec["source"], "values": entries,
                     "fixed": len(entries) == 1, "secondary": k == "version"})
    order = {a["key"]: {e["value"]: i for i, e in enumerate(a["values"])} for a in axes}
    runs.sort(key=lambda r: (tuple(order[a["key"]].get(r["axes"][a["key"]], 99) for a in axes), r["run_id"]))
    for r in runs:
        r["axes"] = {a["key"]: r["axes"][a["key"]] for a in axes}
        del r["raw"]
    return {"id": st["id"], "kind": st["kind"], "title": st["title"], "description": st["description"],
            "sources": st["sources"], "groups": st["groups"], "theme": theme_title, "axes": axes, "runs": runs,
            "n_runs": len(runs), "default_run_id": runs[0]["run_id"] if runs else None}


def catalog(runs_dir: Any) -> dict:
    """The theme tree with every run placed in it. Runs whose 組 is in no strategy of the ledger are listed under
    「台帳に無い実行」; ledger groups that hold no run are named in `missing_groups`. The research cards (backtest_cards.py) are
    themes of their own (`is_card`), one per card of backtest_runs_shared/cards/manifest.json; their variants are runs with the id
    "cards/<card>/<variant>"."""
    by_group = T.strategy_groups()
    found = BV.find_runs(runs_dir)
    placed: dict[str, list[dict]] = {}
    loose: dict[str, list[dict]] = {}
    for rid, d, group in found:
        rec = _record(d)
        raw = {k: ax["get"](rec) for k, ax in T.AXES.items()}
        item = {"run_id": rid, "group": group, "raw": raw}
        if group in by_group:
            placed.setdefault(by_group[group][1]["id"], []).append(item)
        else:
            loose.setdefault(group, []).append(item)
    themes = []
    for th in T.THEMES:
        strategies = []
        for st in th["strategies"]:
            runs = placed.get(st["id"], [])
            if runs:
                strategies.append(_strategy_entry(st, runs, th["title"]))
        themes.append({"id": th["id"], "title": th["title"], "summary": th["summary"], "sources": th["sources"],
                       "strategies": strategies})
    if loose:
        strategies = []
        for group, runs in sorted(loose.items()):
            for r in runs:
                r["axes"] = {"run": r["run_id"][:12]}
                del r["raw"]
            runs.sort(key=lambda r: r["run_id"])
            strategies.append({
                "id": f"{T.UNLISTED_THEME}:{group}", "kind": "unlisted", "title": group or "(組なし)",
                "description": ["この組はテーマの台帳に載っていない。実行の設定から読める説明はまだ無い。"], "sources": [],
                "groups": [group], "theme": T.UNLISTED_TITLE,
                "axes": [{"key": "run", "label": "実行 ID", "source": "実行 ID の先頭 12 文字", "fixed": len(runs) == 1,
                          "values": [{"value": r["axes"]["run"], "label": r["axes"]["run"], "note": ""} for r in runs]}],
                "runs": runs, "n_runs": len(runs), "default_run_id": runs[0]["run_id"]})
        themes.append({"id": T.UNLISTED_THEME, "title": T.UNLISTED_TITLE,
                       "summary": "テーマの台帳に載っていない組の実行。", "sources": [], "strategies": strategies})
    present = {g for _, _, g in found}
    card_themes, n_cards, card_notes = CARDS.catalog_themes(runs_dir)
    if card_themes:  # the cards come before 「台帳に無い実行」, which stays last
        at = next((i for i, t in enumerate(themes) if t["id"] == T.UNLISTED_THEME), len(themes))
        themes[at:at] = card_themes
    return {"themes": themes, "n_runs": len(found) + n_cards, "n_card_runs": n_cards, "card_notes": card_notes,
            "missing_groups": sorted(g for g in by_group if g not in present)}


@dataclass
class Target:
    """What a run id names: a run directory with its record, or a card variant (backtest_cards) with a record shaped like one."""
    run_id: str
    dir: str
    rec: dict
    card: Optional[Any] = None


def _tp(tg: "Target") -> dict:
    return {"path": str(Path(tg.dir) / "trades.json.gz")} if tg.card is not None else {}


def _target(runs_dir: Any, run_id: str) -> Target:
    ref = CARDS.resolve(runs_dir, run_id)  # None: not the card form; BacktestViewError: not in the manifest / not displayable
    if ref is None:
        d = BV._run_dir(runs_dir, run_id)
        return Target(run_id, d, _record(d))
    return Target(run_id, str(ref.dir), CARDS.record_of(ref), ref)


# ---- the seal -------------------------------------------------------------------------------------------------
_SH: list = []
_RULES: dict = {}


def _share():
    """scripts/share_backtest_runs.py as a module (its seal_rule / bars_only / reaches are the one rule)."""
    if not _SH:
        scripts = str(REPO_ROOT / "scripts")
        if scripts not in sys.path:
            sys.path.insert(0, scripts)
        import share_backtest_runs  # noqa: PLC0415
        _SH.append(share_backtest_runs)
    return _SH[0]


def seal_rule(root: Any) -> dict:
    """The share script's rule for this data root ({boundary_ns, registry, ...}); SealBlocked when it cannot be had."""
    key = str(root)
    with _LOCK:
        hit = _RULES.get(key)
        if hit and time.time() - hit[0] < 60:
            rule = hit[1]
        else:
            try:
                rule = _share().seal_rule(key)
            except Exception as exc:  # noqa: BLE001 -- fail closed
                rule = {"error": f"{type(exc).__name__}: {exc}"}
            _RULES[key] = (time.time(), rule)
    if "error" in rule:
        raise SealBlocked("封印の境を決められないので、価格も取引も出さない(止める側に倒す): " + str(rule["error"]))
    return rule


@dataclass
class Cut:
    b: int  # the boundary, ns
    bars: bool  # every data entry of the run is a bar (share_backtest_runs.bars_only)
    limit_ns: int  # an event stamped before this may be shown
    lo_ns: int
    hi_ns: int  # the run's own period, clipped
    first_ns: int
    last_ns: int


def _period_ns(rec: dict) -> tuple[Optional[int], Optional[int]]:
    return T._engine_ns(rec)


def _run_bar_s(rec: dict) -> int:
    inst = (rec.get("config") or {}).get("instrument")
    vals = [int(((e.get("spec") or {}).get("bar") or {}).get("interval_s") or 0) for e in rec.get("data") or []
            if (e.get("spec") or {}).get("symbol") == inst]
    return max([v for v in vals if v] or [0])


def run_cut(rec: dict, rule: dict) -> Cut:
    first, last = _period_ns(rec)
    if first is None or last is None:
        raise ChartError("実行の記録に期間(engine.first_time_ns / last_time_ns)が無い")
    b = int(rule["boundary_ns"])
    bars = bool(_share().bars_only(rec))
    limit = b + (1 if bars else 0)  # share_backtest_runs.reaches: a bar run may end AT the boundary, others must end before
    lo, hi = max(0, first - _run_bar_s(rec) * 10**9), min(last, limit)
    if first >= limit or not lo < hi:
        raise AfterSeal(f"この実行は封印の境({_iso(b / 1e9)})より後で、数字を出さない(期間 {_iso(first / 1e9)}〜{_iso(last / 1e9)})")
    return Cut(b, bars, limit, lo, hi, first, last)


def _iso(s: float) -> str:
    return datetime.fromtimestamp(s, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---- trades ---------------------------------------------------------------------------------------------------
@dataclass
class TradeSet:
    et: np.ndarray  # entry time, ns
    xt: np.ndarray  # exit time, ns (sorted ascending)
    ep: np.ndarray
    xp: np.ndarray
    side: np.ndarray  # +1 buy, -1 sell
    qty: np.ndarray
    pnl: np.ndarray  # money (NaN when the record holds only bp)
    bp: np.ndarray  # pnl per unit over the entry price, in bp
    cum: np.ndarray
    cum_bp: np.ndarray
    reason: Optional[list]
    ranges: list = field(default_factory=list)
    ranges_identical: Optional[bool] = None
    entry_sorted: bool = True
    pnl_derived: bool = False  # True: the record holds bp only; no money amount exists

    @property
    def n(self) -> int:
        return int(self.xt.size)


def _from_arrays(et, xt, ep, xp, side, qty, pnl, reason, bp=None) -> TradeSet:
    et, xt = np.asarray(et, np.int64), np.asarray(xt, np.int64)
    ep, xp, qty = (np.asarray(v, np.float64) for v in (ep, xp, qty))
    side = np.asarray(side, np.int64)
    derived = pnl is None
    pnl = np.full(xt.size, np.nan) if derived else np.asarray(pnl, np.float64)
    bp = None if bp is None else np.asarray(bp, np.float64)
    if xt.size > 1 and np.any(xt[1:] < xt[:-1]):
        o = np.argsort(xt, kind="stable")
        et, xt, ep, xp, side, qty, pnl = (v[o] for v in (et, xt, ep, xp, side, qty, pnl))
        bp = None if bp is None else bp[o]
        reason = [reason[i] for i in o] if reason is not None else None
    if bp is None:
        with np.errstate(divide="ignore", invalid="ignore"):
            bp = np.where((ep * qty) != 0, pnl / (ep * qty) * 1e4, 0.0)
    ts = TradeSet(et, xt, ep, xp, side, qty, pnl, bp, np.cumsum(pnl), np.cumsum(bp), reason)
    ts.entry_sorted = bool(et.size < 2 or not np.any(et[1:] < et[:-1]))
    ts.pnl_derived = derived
    return ts


def _build(rows: list) -> TradeSet:
    """The row form {"data": [{entry_px, entry_t_ns, exit_px, exit_t_ns, pnl, qty, side: "buy"|"sell", reason}]}."""
    def col(k: str, dtype) -> np.ndarray:
        return np.array([r.get(k) for r in rows], dtype=dtype)
    return _from_arrays(col("entry_t_ns", np.int64), col("exit_t_ns", np.int64), col("entry_px", np.float64),
                        col("exit_px", np.float64), [1 if r.get("side") == "buy" else -1 for r in rows],
                        col("qty", np.float64), col("pnl", np.float64), [r.get("reason") for r in rows])


def _build_columns(doc: dict) -> TradeSet:
    """The column form {"version": 1, "t_unit": "ns", entry_t_ns, entry_px, exit_t_ns, exit_px, side: [1|-1], qty,
    pnl_bp}. It holds no money amount (a money value from bp would multiply by an average exposure the record does
    not state), so only bp is shown: `pnl_derived` is True and the money fields are None."""
    if doc.get("t_unit", "ns") != "ns":
        raise ChartError(f"trades t_unit {doc.get('t_unit')!r} is not supported")
    return _from_arrays(doc["entry_t_ns"], doc["exit_t_ns"], doc["entry_px"], doc["exit_px"], doc["side"], doc["qty"],
                        None, None, bp=doc["pnl_bp"])


def _same(a: TradeSet, b: TradeSet) -> bool:
    return (a.n == b.n and np.array_equal(a.et, b.et) and np.array_equal(a.xt, b.xt) and np.array_equal(a.ep, b.ep)
            and np.array_equal(a.xp, b.xp) and np.array_equal(a.pnl, b.pnl) and np.array_equal(a.side, b.side))


def read_trades(doc: Any, range_name: Optional[str] = None) -> TradeSet:
    """The one place the two trades.json shapes are read (row form and column form)."""
    if isinstance(doc, dict) and "data" not in doc and "entry_t_ns" in doc:
        return _build_columns(doc)
    rows = doc["data"]
    ranges = list(dict.fromkeys(r["range"] for r in rows if "range" in r))
    pick = range_name if range_name in ranges else (ranges[0] if ranges else None)
    ts = _build([r for r in rows if r.get("range") == pick] if ranges else rows)
    ts.ranges = ranges
    if len(ranges) > 1:
        ts.ranges_identical = all(_same(_build([r for r in rows if r.get("range") == ranges[0]]),
                                        _build([r for r in rows if r.get("range") == o])) for o in ranges[1:])
    return ts


def truncate(ts: TradeSet, limit_ns: int) -> TradeSet:
    """The trades that exited before `limit_ns` (a trade at or after it is not part of the run as shown)."""
    k = int(np.searchsorted(ts.xt, limit_ns, side="left"))
    if k >= ts.n:
        return ts
    out = TradeSet(ts.et[:k], ts.xt[:k], ts.ep[:k], ts.xp[:k], ts.side[:k], ts.qty[:k], ts.pnl[:k], ts.bp[:k],
                   np.cumsum(ts.pnl[:k]), np.cumsum(ts.bp[:k]), None if ts.reason is None else ts.reason[:k],
                   ts.ranges, ts.ranges_identical, ts.entry_sorted, ts.pnl_derived)
    return out


_TRADES: "OrderedDict[tuple, TradeSet]" = OrderedDict()


def _raw(path: str) -> Any:
    doc = BV._load(path)
    return doc["data"] if isinstance(doc, dict) and isinstance(doc.get("data"), dict) else doc


def load_trades(run_dir: str, range_name: Optional[str] = None, limit_ns: Optional[int] = None, path: Optional[str] = None) -> TradeSet:
    """The run's trades (trades.json[.gz], either form) as arrays sorted by exit time, cut at `limit_ns`. A run through
    bot.bt.pipeline writes every trade once per fill range: `range_name` picks one (default: the first)."""
    p = path or BV._export_path(run_dir, "trades")  # a card variant passes its trades.json.gz: the file the completeness check looked at
    if p is None:
        raise ChartError("この実行に trades の出力が無い")
    st = os.stat(p)
    key = (p, st.st_mtime_ns, st.st_size, range_name, limit_ns)
    with _LOCK:
        if key in _TRADES:
            _TRADES.move_to_end(key)
            return _TRADES[key]
    ts = read_trades(_raw(p), range_name)
    if limit_ns is not None:
        ts = truncate(ts, limit_ns)
    with _LOCK:
        _TRADES[key] = ts
        while len(_TRADES) > 8:
            _TRADES.popitem(last=False)
    return ts


def _f(x: float) -> Optional[float]:
    return None if x != x else float(x)


def trade_stats(ts: TradeSet) -> dict:
    """取引数・勝率・累計損益・最大の落ち込み, from the trades (bp = pnl per unit / entry price). Money fields are None
    when the record holds bp only."""
    n = ts.n
    if n == 0:
        return {"n": 0, "wins": 0, "win_rate": None, "total": None if ts.pnl_derived else 0.0, "total_bp": 0.0,
                "max_dd": None if ts.pnl_derived else 0.0, "max_dd_bp": 0.0, "mean_bp": None}
    wins = int(((ts.bp if ts.pnl_derived else ts.pnl) > 0).sum())

    def dd(cum: np.ndarray) -> float:
        c = np.concatenate(([0.0], cum))
        return float((np.maximum.accumulate(c) - c).max())
    return {"n": n, "wins": wins, "win_rate": wins / n, "total": None if ts.pnl_derived else float(ts.cum[-1]),
            "total_bp": float(ts.cum_bp[-1]), "max_dd": None if ts.pnl_derived else dd(ts.cum),
            "max_dd_bp": dd(ts.cum_bp), "mean_bp": float(ts.bp.mean())}


# ---- the price stores ------------------------------------------------------------------------------------------
def _safe(path: Path, root: Path) -> Optional[str]:
    """None when `path` may be read, else why not: the data layer's own allow-list (case-insensitive; refuses qa_*,
    o3c_*, phase2_runs, phase2_sealed and anything outside the allowed roots, on the written and the real path) and
    only under backtest_data."""
    if not Path(path).is_file():
        return f"ファイルがディスクに無い({Path(path).name})"
    try:
        chk = DEFAULT_ALLOWLIST.check(str(root), str(path))
    except PathRefused as exc:
        return f"データ層が拒む: {exc}"
    if Path(chk.rel_real).parts[:1] != ("backtest_data",):
        return "backtest_data の外のファイルは読まない"
    return None


@dataclass
class Plan:
    market: Optional[str]
    files: list = field(default_factory=list)  # [(Path, repo-relative str)]
    label: str = ""
    note: str = ""
    reason: str = ""
    same_source: bool = False
    run_files: list = field(default_factory=list)


def market_files(key: str, root: Path, boundary_s: int) -> tuple[list, str]:
    """([(Path, rel)], reason): the store's 1-minute files, a year-named file only when its year starts before the
    boundary (a file wholly after it is never opened)."""
    m = MARKETS[key]
    by_year = datetime.fromtimestamp(boundary_s, tz=timezone.utc).year
    rels: list[str] = list(m.get("files") or [])
    if "dir" in m:
        d = Path(root) / m["dir"]
        try:
            names = sorted(os.listdir(d))
        except OSError:
            return [], f"価格の置き場 {m['dir']} がディスクに無い"
        for n in names:
            mt = re.fullmatch(m["pattern"], n)
            if mt and int(mt.group(1)) <= by_year:
                rels.append(f"{m['dir']}/{n}")
    out = []
    for rel in rels:
        why = _safe(Path(root) / rel, Path(root))
        if why:
            return [], f"{m['label']} の価格の置き場が読めない: {why}"
        out.append((Path(root) / rel, rel))
    if not out:
        return [], f"{m['label']} の 1 分足のファイルが無い"
    return out, ""


def price_plan(rec: dict, root: Path, rule: dict) -> Plan:
    inst = (rec.get("config") or {}).get("instrument")
    if inst not in MARKETS:
        return Plan(None, reason=f"価格の置き場の台帳(MARKETS)に銘柄 {inst!r} が無い")
    files, why = market_files(inst, Path(root), int(rule["boundary_ns"]) // 10**9)
    m = MARKETS[inst]
    if not files:
        return Plan(inst, label=m["label"], reason=why)
    card = rec.get("_card")
    if card is not None:  # a card variant: its trades are on the ledger's instrument; provenance names the directories it read
        dirs = card.get("data_dirs_read") or []
        same = bool(m.get("dir")) and m["dir"] in dirs
        note = (f"価格は、カードが読んだ {m['label']} の 1 分足と同じ置き場(provenance の data_dirs_read にある)から表示の足に畳んだ。"
                "取引の値段はこの足の始値(約定の模型)" if same else
                f"{FALLBACK_NOTE}({m['label']} の 1 分足から作った。カードの provenance の data_dirs_read にこの置き場が無い)")
        return Plan(inst, files, m["label"], note, "", same, [Path(x).name for x in dirs])
    run_files = [e["path"] for e in rec.get("data") or [] if (e.get("spec") or {}).get("symbol") == inst]
    rels = {r for _, r in files}
    same = bool(run_files) and set(run_files) <= rels
    names = ", ".join(Path(p).name for p in run_files[:4]) + ("…" if len(run_files) > 4 else "")
    if same:
        note = f"価格は実行が読んだ足と同じファイル由来({m['label']} の 1 分足)から表示の足に畳んだ"
    else:
        note = f"{FALLBACK_NOTE}({m['label']} の 1 分足から作った。実行が読んだのは {names or '記録なし'})"
    return Plan(inst, files, m["label"], note, "", same, run_files)


def _cache_root() -> Path:
    env = os.environ.get("BT_CHART_CACHE_DIR")
    if env:
        return Path(env)
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    else:
        base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / "trade_bt_chart_cache"


def _dir_bytes(d: Path) -> int:
    return sum(f.stat().st_size for f in d.iterdir() if f.is_file())


def _evict(root: Path, keep: Path) -> None:
    """Delete the oldest store directories while the cache exceeds CACHE_MAX_MB."""
    try:
        dirs = [d for d in root.iterdir() if d.is_dir() and not d.name.startswith(".")]
        sizes = {d: _dir_bytes(d) for d in dirs}
        limit = int(os.environ.get("BT_CHART_CACHE_MAX_MB", CACHE_MAX_MB)) * 1024 * 1024
        for d in sorted(dirs, key=lambda d: (d / "meta.json").stat().st_mtime if (d / "meta.json").exists() else 0):
            if sum(sizes.values()) <= limit:
                break
            if d != keep:
                shutil.rmtree(d, ignore_errors=True)
                sizes.pop(d, None)
    except OSError:
        pass


def _parse(raw: bytes, name: str, cols: tuple, boundary_s: int) -> tuple:
    """(t seconds, o, h, l, c) of one csv(.gz) held in memory: complete OHLC rows that start before the boundary."""
    import pandas as pd  # noqa: PLC0415 -- only the parse needs it
    df = pd.read_csv(io.BytesIO(raw), usecols=list(cols), compression="gzip" if name.endswith(".gz") else None)
    t = (pd.to_datetime(df[cols[0]], utc=True) - pd.Timestamp("1970-01-01", tz="UTC")) // pd.Timedelta(seconds=1)
    df = df.assign(_t=t.astype("int64")).dropna(subset=list(cols[1:]))
    df = df[df["_t"] < boundary_s].sort_values("_t", kind="stable").drop_duplicates("_t", keep="last")
    return (df["_t"].to_numpy(np.int64), *(df[c].to_numpy(np.float64) for c in cols[1:]))


def _read_file(path: Path, rel: str, rule: dict, cols: tuple) -> tuple:
    """One file through the data layer's door (SealRegistry.read_checked, range (0, boundary)), then parsed and cut."""
    b = int(rule["boundary_ns"])
    raw, _ent = rule["registry"].read_checked(os.path.realpath(path), rel, (0, b))
    return _parse(raw, path.name, cols, b // 10**9)


def _fold(t, o, h, l, c, width: int) -> tuple:
    """Fold rows (bar starts t, ascending) into bars of `width` seconds aligned on the UTC epoch."""
    if t.size == 0:
        return t, o, h, l, c
    b = t // width * width
    starts = np.flatnonzero(np.r_[True, b[1:] != b[:-1]])
    last = np.r_[starts[1:] - 1, t.size - 1]
    return b[starts], o[starts], np.maximum.reduceat(h, starts), np.minimum.reduceat(l, starts), c[last]


@dataclass
class Store:
    key: str
    frames: dict  # frame s -> (t, o, h, l, c)
    lo_s: int
    hi_s: int  # exclusive: the last 1-minute row's start + 60
    rows: int
    build_s: Optional[float]
    cache_bytes: int
    from_cache: bool


_STORES: "OrderedDict[str, Store]" = OrderedDict()
_BUILD: dict = {}
_COLS = ("t", "o", "h", "l", "c")


def _signature(plan: Plan, rule: dict) -> str:
    m = MARKETS[plan.market]
    parts = [plan.market, str(rule["boundary_ns"]), json.dumps(m["cols"])]
    parts += sorted(rule["registry"].records_read.values())
    for p, rel in plan.files:
        st = p.stat()
        parts.append(f"{rel}|{st.st_size}|{st.st_mtime_ns}")
    return hashlib.sha1("\n".join(parts).encode()).hexdigest()[:20]


def _cut_frames(frames: dict, boundary_s: int) -> dict:
    """Cut every frame once more at the boundary (also what is read back from the cache)."""
    out = {}
    for w, arrs in frames.items():
        k = int(np.searchsorted(arrs[0], boundary_s, side="left"))
        out[w] = tuple(a[:k] for a in arrs)
    return out


def _load_dir(d: Path) -> dict:
    return {w: tuple(np.load(d / f"i{w}_{c}.npy", mmap_mode="r") for c in _COLS) for w in FRAMES}


def get_store(plan: Plan, rule: dict) -> Store:
    """The price store of the plan's instrument: memory, else the disk cache, else built ONCE from the 1-minute files."""
    sig = _signature(plan, rule)
    key = f"{plan.market}-{sig}"
    b_s = int(rule["boundary_ns"]) // 10**9
    with _LOCK:
        if key in _STORES:
            _STORES.move_to_end(key)
            return _STORES[key]
        lock = _BUILD.setdefault(key, threading.Lock())
    with lock:
        with _LOCK:
            if key in _STORES:
                return _STORES[key]
        root = _cache_root()
        d = root / key
        t0 = time.time()
        frames, from_cache = None, False
        if (d / "meta.json").exists():
            try:
                frames, from_cache = _load_dir(d), True
                os.utime(d / "meta.json")
            except (OSError, ValueError):
                frames = None
        if frames is None:
            cols = MARKETS[plan.market]["cols"]
            parts = [_read_file(p, rel, rule, cols) for p, rel in plan.files]
            cat = [np.concatenate([a[i] for a in parts]) for i in range(5)]
            order = np.argsort(cat[0], kind="stable")
            cat = [a[order] for a in cat]
            keep = np.ones(cat[0].size, dtype=bool)
            keep[1:] = cat[0][1:] != cat[0][:-1]
            base = tuple(a[keep] for a in cat)
            frames = {w: (base if w == 60 else _fold(*base, w)) for w in FRAMES}
            frames = _cut_frames(frames, b_s)
            try:
                root.mkdir(parents=True, exist_ok=True)
                tmp = root / f".{key}.{os.getpid()}.{threading.get_ident()}.tmp"
                shutil.rmtree(tmp, ignore_errors=True)
                tmp.mkdir()
                for w, arrs in frames.items():
                    for c, a in zip(_COLS, arrs):
                        np.save(tmp / f"i{w}_{c}.npy", a)
                (tmp / "meta.json").write_text(json.dumps({"market": plan.market, "rows": int(base[0].size)}))
                if d.exists():
                    shutil.rmtree(tmp, ignore_errors=True)
                else:
                    os.replace(tmp, d)
                _evict(root, d)
                frames = _load_dir(d)
            except OSError:
                pass  # no cache directory: the frames stay in memory
        frames = _cut_frames(frames, b_s)
        t1 = frames[60][0]
        size = _dir_bytes(d) if d.exists() else 0
        st = Store(plan.market, frames, int(t1[0]) if t1.size else 0, int(t1[-1]) + 60 if t1.size else 0, int(t1.size),
                   None if from_cache else round(time.time() - t0, 2), size, from_cache)
        with _LOCK:
            _STORES[key] = st
            while len(_STORES) > 2:
                _STORES.popitem(last=False)
        return st


def pick_interval(span_s: float, max_bars: int) -> int:
    for i in FRAMES:
        if span_s / i <= max_bars:
            return i
    return FRAMES[-1]


# ---- the chart ------------------------------------------------------------------------------------------------
def _summary_price(plan: Plan) -> dict:
    return {"available": plan.market is not None and not plan.reason, "market": plan.market, "label": plan.label,
            "note": plan.note, "reason": plan.reason, "same_source": plan.same_source,
            "run_files": [Path(p).name for p in plan.run_files], "frames": list(FRAMES)}


def run_summary(runs_dir: Any, run_id: str, root: Path = REPO_ROOT, range_name: Optional[str] = None) -> dict:
    try:
        tg = _target(runs_dir, run_id)
    except CARDS.CardPreparing as exc:  # in the manifest with display_ok, but the files are not complete: not an error of the page
        return {"run_id": run_id, "preparing": str(exc), "card": {"variant": run_id}}
    d, rec = tg.dir, tg.rec
    try:
        rule = seal_rule(root)
        cut = run_cut(rec, rule)
    except (SealBlocked, AfterSeal) as exc:
        return {"run_id": run_id, "purpose": rec.get("purpose"), "blocked": str(exc), "after_seal": isinstance(exc, AfterSeal)}
    ccy = BV.run_currency(rec)
    try:
        ts = load_trades(d, range_name, cut.limit_ns, **_tp(tg))
    except (OSError, EOFError, ValueError, KeyError, zlib.error) as exc:
        if tg.card is None:
            raise
        return {"run_id": run_id, "preparing": f"準備中: trades を読めない(書きかけ): {type(exc).__name__}", "card": {"variant": run_id}}
    plan = price_plan(rec, Path(root), rule)
    mbar = _run_bar_s(rec)
    out = {"run_id": run_id, "purpose": rec.get("purpose"), "instrument": (rec.get("config") or {}).get("instrument"),
            "currency": ccy, "unit_label": ccy if ccy else BV.NO_CURRENCY, "stats": trade_stats(ts),
            "ranges": ts.ranges, "ranges_identical": ts.ranges_identical, "pnl_derived": ts.pnl_derived,
            "range": range_name if range_name in ts.ranges else (ts.ranges[0] if ts.ranges else None),
            "measure_interval_s": mbar or None,
            "period": {"first_s": cut.first_ns // 10**9, "last_s": cut.last_ns // 10**9, "last_incl_s": cut.last_ns // 10**9 - 1,
                       "first_iso": _iso(cut.first_ns / 1e9), "last_iso": _iso(cut.last_ns / 1e9)},
            "price": _summary_price(plan), "seal_boundary_s": cut.b // 10**9, "seal_boundary_iso": _iso(cut.b / 1e9)}
    if tg.card is not None:
        out["card"] = CARDS.info(tg.card, ts.n)
        out["stats"], out["card"]["headline"] = CARDS.headline(tg.card, out["stats"], ts.n)
    return out


def run_chart(runs_dir: Any, run_id: str, from_s: Optional[float] = None, to_s: Optional[float] = None,
              max_bars: int = DEFAULT_MAX_BARS, range_name: Optional[str] = None, root: Path = REPO_ROOT,
              interval_s: Optional[int] = None) -> dict:
    """Bars (from the instrument's price store), cumulative profit and loss and trades (from the run) of the visible
    range [from_s, to_s] (UTC seconds; default: the run's period). The range may leave the run's period; it is clipped
    to the store's data and to the seal boundary. Bars use the display frame `interval_s` (rounded up to a frame), or the
    smallest frame that gives at most `max_bars` bars; more than HARD_MAX_BARS bars narrow the range around its centre
    (`narrowed`)."""
    try:
        tg = _target(runs_dir, run_id)
    except CARDS.CardPreparing as exc:
        raise ChartError(str(exc)) from None
    d, rec = tg.dir, tg.rec
    rule = seal_rule(root)
    cut = run_cut(rec, rule)
    try:
        ts = load_trades(d, range_name, cut.limit_ns, **_tp(tg))
    except (OSError, EOFError, ValueError, KeyError, zlib.error) as exc:
        if tg.card is None:
            raise
        raise ChartError(f"準備中: trades を読めない(書きかけ): {type(exc).__name__}") from None
    plan = price_plan(rec, Path(root), rule)
    price = _summary_price(plan)
    store = None
    if price["available"]:
        try:
            store = get_store(plan, rule)
        except SealBlocked:
            raise
        except Exception as exc:  # noqa: BLE001 -- the page shows why there is no chart
            price.update(available=False, reason=f"価格の置き場を作れない({type(exc).__name__}: {exc})")
    if store is not None and store.rows:
        lo_s, hi_s = float(store.lo_s), float(min(store.hi_s, cut.b // 10**9))
    else:
        store = None
        lo_s, hi_s = cut.lo_ns / 1e9, cut.hi_ns / 1e9
    max_bars = max(50, min(int(max_bars), HARD_MAX_BARS))
    f = (cut.lo_ns / 1e9 if from_s is None else float(from_s))
    t = (cut.hi_ns / 1e9 if to_s is None else float(to_s))
    f, t = max(lo_s, f), min(hi_s, t)
    if not f < t:
        f, t = max(lo_s, cut.lo_ns / 1e9), min(hi_s, cut.hi_ns / 1e9)
    if not f < t:
        f, t = lo_s, hi_s
    span = t - f
    if interval_s:
        interval = next((w for w in FRAMES if w >= int(interval_s)), FRAMES[-1])
    else:
        interval = pick_interval(span, max_bars)
    narrowed = None
    if span / interval > HARD_MAX_BARS:
        narrowed = {"requested_bars": int(span / interval), "max_bars": HARD_MAX_BARS}
        c, half = (f + t) / 2, HARD_MAX_BARS * interval / 2
        f, t = max(lo_s, c - half), min(hi_s, c + half)
        span = t - f
    out: dict = {"run_id": run_id, "from_s": f, "to_s": t, "interval_s": interval, "frames": list(FRAMES),
                 "chart_lo_s": lo_s, "chart_hi_s": hi_s, "bars": [], "price": price, "narrowed": narrowed,
                 "measure_interval_s": _run_bar_s(rec) or None}
    if store is not None:
        tt, o, h, l, c_ = store.frames[interval]
        a = int(np.searchsorted(tt, int(f // interval * interval), side="left"))
        e = int(np.searchsorted(tt, min(int(np.ceil(t)), cut.b // 10**9), side="left"))  # a bar starting at the boundary never
        out["bars"] = [[int(x), float(y1), float(y2), float(y3), float(y4)]
                       for x, y1, y2, y3, y4 in zip(tt[a:e], o[a:e], h[a:e], l[a:e], c_[a:e])]
    # profit and loss and trades of the range: binary searches on the sorted arrays (a run can hold 800,000 trades)
    f_ns, t_ns = int(f * 1e9), int(t * 1e9)
    lim = int(np.searchsorted(ts.xt, cut.limit_ns, side="left"))
    a = min(int(np.searchsorted(ts.xt, f_ns, side="left")), lim)
    e = min(int(np.searchsorted(ts.xt, t_ns, side="right")), lim)
    base_cum, base_bp = (_f(ts.cum[a - 1]), float(ts.cum_bp[a - 1])) if a > 0 else (0.0 if not ts.pnl_derived else None, 0.0)
    pts = {int(f // interval * interval): [base_cum, base_bp]}
    if e > a:
        bt = ts.xt[a:e] // 10**9 // interval * interval
        last = np.flatnonzero(np.r_[bt[1:] != bt[:-1], True]) + a
        for k, ci in zip(bt[last - a], last):
            pts[int(k)] = [_f(ts.cum[ci]), float(ts.cum_bp[ci])]
    out["pnl"] = [[k, v[0], v[1]] for k, v in sorted(pts.items())]
    if ts.entry_sorted:
        c = min(int(np.searchsorted(ts.et, t_ns, side="right")), lim)
        idx = np.arange(a, c) if c > a else np.arange(0)
    else:
        idx = a + np.flatnonzero(ts.et[a:lim] <= t_ns)
    out["trades_in_range"] = int(idx.size)
    out["too_many"] = bool(idx.size > MAX_TRADES)
    out["max_trades"] = MAX_TRADES
    out["trades"] = [] if out["too_many"] else [
        {"i": int(i), "side": int(ts.side[i]), "et": int(round(ts.et[i] / 1e9)), "ep": float(ts.ep[i]),
         "xt": int(round(ts.xt[i] / 1e9)), "xp": float(ts.xp[i]), "pnl": _f(ts.pnl[i]), "bp": float(ts.bp[i]),
         "reason": None if ts.reason is None else ts.reason[i]} for i in idx]
    out["trades_total"] = ts.n
    out["ranges"] = ts.ranges
    out["range"] = range_name if range_name in ts.ranges else (ts.ranges[0] if ts.ranges else None)
    out["pnl_derived"] = ts.pnl_derived
    return out


# ---- static files (the chart library and the tab's own script / style: no CDN) ---------------------------------
STATIC_DIR = Path(__file__).resolve().parent / "static"
_CTYPES = {".js": "application/javascript; charset=utf-8", ".css": "text/css; charset=utf-8",
           ".txt": "text/plain; charset=utf-8"}


def static_file(name: str) -> Optional[tuple[str, bytes]]:
    """(content type, bytes) of a file directly in STATIC_DIR, or None. A name with a separator or a dot-dot is not
    looked up; only the directory's own listing is served."""
    if not name or "/" in name or "\\" in name or name.startswith("."):
        return None
    try:
        if name not in os.listdir(STATIC_DIR):
            return None
        data = (STATIC_DIR / name).read_bytes()
    except OSError:
        return None
    return _CTYPES.get(Path(name).suffix, "text/plain; charset=utf-8"), data
