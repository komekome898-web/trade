"""The data behind the dashboard's バックテスト tab: the price stores, the seal, and the chart of one road run.

    catalog(runs_dir)                        -> road_catalog.catalog: themes -> strategies -> family axes -> runs
    run_summary(runs_dir, run_id, root)      -> {headline, summary rows, ranges, instruments, period, price: {...}} or {blocked: reason}
    run_chart(runs_dir, run_id, ...)         -> {bars, layers per range, pos / cum lines, ...} for the visible range only
    run_table(runs_dir, run_id, table, ...)  -> one page of one of the seven tables (road_view.table_page), cut at the seal
    run_trace(runs_dir, run_id, table, row)  -> the rows tied to one row by their numbers (road_view.trace)

What a run holds is the road record (road/, 版 road-record-7; road_view.py reads it). A run with no road/ is a 古い形の走らせ:
it is listed, and neither a chart nor a table is made for it (the pipeline's FIFO trade count is not the road's count).

Prices (L-D06). A run's chart does not read the run's own data files. Each instrument has ONE price store (MARKETS:
one row per exchange and symbol, files in git); the store is built once from its 1-minute files (read through the data
layer's door, SealRegistry.read_checked, after the seal boundary cut) into the display frames FRAMES (1 m, 5 m, 15 m,
1 h, 4 h, 1 d), cached on disk outside the repository (_cache_root), and a chart request only slices the visible range
of the frame the page asked for. A run supplies its tables only. When the bars a run read are not the store's bars
(derived files) the page says so (FALLBACK_NOTE).

Seal. The boundary is computed as scripts/share_backtest_runs.py computes it (seal_rule over bot.bt.data.allowlist.
SealRegistry: the earliest cutoff of the crypto / fx units); a ledger that cannot be read, or a unit the rule does not
know, blocks everything (SealBlocked: no price, no row, the reason is shown). Layers, each cutting on its own: a
file is read only through read_checked and its rows at or after the boundary are dropped when parsed; a cached frame
is cut again when it is loaded; a chart request cuts again at the index; the rows of the road tables are cut at
limit_ns = boundary (+1 ns when every data entry of the run is a bar, as share_backtest_runs.reaches does) in every
answer (chart, table page, trace, headline). A run that lies wholly after the boundary shows no number.
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
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import numpy as np

from bot.bt.data.allowlist import DEFAULT_ALLOWLIST
from bot.bt.data.errors import PathRefused
from bot.monitoring import backtest_view as BV
from bot.monitoring import road_catalog as RC
from bot.monitoring import road_strategies as RS
from bot.monitoring import road_view as RV

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
_record = RV.record_of


def catalog(runs_dir: Any) -> dict:
    return RC.catalog(runs_dir)


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


def _period_ns(rec: dict, inst: Optional[str] = None) -> tuple[Optional[int], Optional[int]]:
    return RV.engine_period(rec, inst)


def _run_bar_s(rec: dict, inst: Optional[str] = None) -> int:
    inst = inst or (rec.get("config") or {}).get("instrument")
    vals = [int(((e.get("spec") or {}).get("bar") or {}).get("interval_s") or 0) for e in rec.get("data") or []
            if (e.get("spec") or {}).get("symbol") == inst]
    return max([v for v in vals if v] or [0])


def run_cut(rec: dict, rule: dict, inst: Optional[str] = None) -> Cut:
    first, last = _period_ns(rec, inst)
    if first is None or last is None:
        raise ChartError("実行の記録に期間(engine.first_time_ns / last_time_ns)が無い")
    b = int(rule["boundary_ns"])
    bars = bool(_share().bars_only(rec))
    limit = b + (1 if bars else 0)  # share_backtest_runs.reaches: a bar run may end AT the boundary, others must end before
    lo, hi = max(0, first - _run_bar_s(rec, inst) * 10**9), min(last, limit)
    if first >= limit or not lo < hi:
        raise AfterSeal(f"この実行は封印の境({_iso(b / 1e9)})より後で、数字を出さない(期間 {_iso(first / 1e9)}〜{_iso(last / 1e9)})")
    return Cut(b, bars, limit, lo, hi, first, last)


def _iso(s: float) -> str:
    return datetime.fromtimestamp(s, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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


def price_plan(rec: dict, root: Path, rule: dict, inst: Optional[str] = None) -> Plan:
    inst = inst or (rec.get("config") or {}).get("instrument")
    if inst not in MARKETS:
        return Plan(None, reason=f"価格の置き場の台帳(MARKETS)に銘柄 {inst!r} が無い")
    files, why = market_files(inst, Path(root), int(rule["boundary_ns"]) // 10**9)
    m = MARKETS[inst]
    if not files:
        return Plan(inst, label=m["label"], reason=why)
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
    pinned: bool = False


_STORES: "OrderedDict[str, Store]" = OrderedDict()
_BUILD: dict = {}
_PROGRESS: dict = {}  # store key -> {market, label, stage, frame, frames, t0}: what a build is doing now (the page shows it)
_JOBS: dict = {}  # store key -> {thread, error, t_err}: background builds
_COLS = ("t", "o", "h", "l", "c")


# ---- the log of the tab's own work (logs/dashboard_bt.log: one line per event, read the next morning) -------------
_LOGLOCK = threading.Lock()


def _log_path() -> Path:
    env = os.environ.get("BT_LOG_PATH")
    return Path(env) if env else REPO_ROOT / "logs" / "dashboard_bt.log"


def bt_log(action: str, seconds: Optional[float], result: str) -> None:
    """Append "<UTC time>\t<action>\t<seconds>\t<result>" to the tab's log. A log that cannot be written is told on stderr
    once per call, never raised (a log must not stop the tab)."""
    line = "%s\t%s\t%s\t%s\n" % (datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), action,
                                  "-" if seconds is None else f"{seconds:.2f}s", " ".join(str(result).split())[:400])
    try:
        with _LOGLOCK:
            p = _log_path()
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "a", encoding="utf-8") as fh:
                fh.write(line)
    except OSError as exc:
        print(f"dashboard_bt.log: cannot write ({exc}): {line.strip()}", file=sys.stderr, flush=True)


def _signature(plan: Plan, rule: dict) -> str:
    m = MARKETS[plan.market]
    parts = [plan.market, str(rule["boundary_ns"]), json.dumps(m["cols"])]
    parts += sorted(rule["registry"].records_read.values())
    for p, rel in plan.files:
        st = p.stat()
        parts.append(f"{rel}|{st.st_size}|{st.st_mtime_ns}")
    return hashlib.sha1("\n".join(parts).encode()).hexdigest()[:20]


def store_key(plan: Plan, rule: dict) -> str:
    return f"{plan.market}-{_signature(plan, rule)}"


def _cut_frames(frames: dict, boundary_s: int) -> dict:
    """Cut every frame once more at the boundary (also what is read back from the cache)."""
    out = {}
    for w, arrs in frames.items():
        k = int(np.searchsorted(arrs[0], boundary_s, side="left"))
        out[w] = tuple(a[:k] for a in arrs)
    return out


def _load_dir(d: Path) -> dict:
    return {w: tuple(np.load(d / f"i{w}_{c}.npy", mmap_mode="r") for c in _COLS) for w in FRAMES}


_HOOK: list = []  # in a build child: [function(stage, frame)] that sends the progress to the parent


def _progress(key: str, plan: Plan, stage: str, frame: int = 0) -> None:
    if _HOOK:
        try:
            _HOOK[0](stage, frame)
        except Exception:  # noqa: BLE001 -- a lost progress message must not stop the build
            pass
    with _LOCK:
        pr = _PROGRESS.setdefault(key, {"market": plan.market, "label": MARKETS[plan.market]["label"], "t0": time.time()})
        pr.update(stage=stage, frame=frame, frames=len(FRAMES))


def get_store(plan: Plan, rule: dict) -> Store:
    """The price store of the plan's instrument: memory, else the disk cache, else built ONCE from the 1-minute files (one
    thread builds a key; a second request for it waits on the same lock and then finds the store in memory). A cache that
    cannot be written (a locked file on Windows, a full disk) is logged and the store stays in memory, pinned: it is not
    built again for every request."""
    key = store_key(plan, rule)
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
        _progress(key, plan, "reading", 0)
        frames, from_cache, pinned = None, False, False
        if (d / "meta.json").exists():
            try:
                frames, from_cache = _load_dir(d), True
                os.utime(d / "meta.json")
            except (OSError, ValueError):
                frames = None
        if frames is None:
            cols = MARKETS[plan.market]["cols"]
            parts = []
            for p, rel in plan.files:
                parts.append(_read_file(p, rel, rule, cols))
                _progress(key, plan, "reading", 0)
            cat = [np.concatenate([a[i] for a in parts]) for i in range(5)]
            order = np.argsort(cat[0], kind="stable")
            cat = [a[order] for a in cat]
            keep = np.ones(cat[0].size, dtype=bool)
            keep[1:] = cat[0][1:] != cat[0][:-1]
            base = tuple(a[keep] for a in cat)
            frames = {}
            for i, w in enumerate(FRAMES):
                _progress(key, plan, "folding", i + 1)
                frames[w] = base if w == 60 else _fold(*base, w)
            frames = _cut_frames(frames, b_s)
            _progress(key, plan, "saving", len(FRAMES))
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
                    shutil.rmtree(d, ignore_errors=True)  # a directory without a complete meta.json: replace it
                os.replace(tmp, d)
                _evict(root, d)
                frames = _load_dir(d)
            except (OSError, ValueError) as exc:
                pinned = True  # no usable cache directory: the frames stay in memory, and the failure is on the record
                shutil.rmtree(root / f".{key}.{os.getpid()}.{threading.get_ident()}.tmp", ignore_errors=True)
                bt_log("cache_write_failed", time.time() - t0, f"{key} {type(exc).__name__}: {exc} (the store stays in memory)")
                print(f"dashboard: price cache write failed for {key}: {type(exc).__name__}: {exc}; kept in memory", file=sys.stderr, flush=True)
        frames = _cut_frames(frames, b_s)
        t1 = frames[60][0]
        size = _dir_bytes(d) if d.exists() else 0
        st = Store(plan.market, frames, int(t1[0]) if t1.size else 0, int(t1[-1]) + 60 if t1.size else 0, int(t1.size),
                   None if from_cache else round(time.time() - t0, 2), size, from_cache)
        st.pinned = pinned
        with _LOCK:
            _STORES[key] = st
            while len(_STORES) > 2:
                victim = next((k for k, v in _STORES.items() if not getattr(v, "pinned", False) and k != key), None)
                if victim is None:
                    break
                _STORES.pop(victim)
            _PROGRESS.pop(key, None)
        bt_log("store_built" if not from_cache else "store_loaded", time.time() - t0, f"{key} rows={st.rows} cache_bytes={size}")
        return st


#: True: a store is built by a separate process (spawn: works on Windows), so the work of reading and folding 4 million rows
#: never takes the Python lock the request threads need; False: in a thread of this process (tests that patch the readers).
BUILD_IN_CHILD = True
_CHILD_LOCK = threading.Lock()  # one build child at a time


def _child_main(market: str, root: str, conn: Any) -> None:
    """The build child: makes the store of `market` into the disk cache (get_store writes it there) and tells the parent the
    progress, then {done, cached} or {error}. Module level and picklable arguments only (spawn)."""
    try:
        _HOOK.append(lambda stage, frame: conn.send({"stage": stage, "frame": frame}))
        rule = seal_rule(Path(root))
        plan = price_plan({"config": {"instrument": market}}, Path(root), rule)
        if not plan.files:
            raise RuntimeError(plan.reason or "no price files")
        get_store(plan, rule)
        conn.send({"done": True, "cached": (_cache_root() / store_key(plan, rule) / "meta.json").exists()})
    except BaseException as exc:  # noqa: BLE001 -- the parent is told, whatever it was
        try:
            conn.send({"error": f"{type(exc).__name__}: {exc}"})
        except Exception:  # noqa: BLE001
            pass
        raise SystemExit(2)


def _build_store_job(plan: Plan, rule: dict, key: str) -> None:
    """Run in the background thread of a store request: make the store, in a child process when BUILD_IN_CHILD. The parent only
    waits on a pipe and then reads the finished cache (memory-mapped). A child that could not write the cache, or died, leaves no
    cache: the store is then built in this process, in memory (the old way, logged), so the chart still comes."""
    if not BUILD_IN_CHILD:
        get_store(plan, rule)
        return
    import multiprocessing as mp  # noqa: PLC0415
    _progress(key, plan, "queued")
    result: dict = {}
    t0 = time.time()
    with _CHILD_LOCK:
        meta = _cache_root() / key / "meta.json"
        if not meta.exists():
            ctx = mp.get_context("spawn")
            rd, wr = ctx.Pipe(False)
            proc = ctx.Process(target=_child_main, args=(plan.market, str(rule["root"]), wr), daemon=True, name=f"bt-build-{plan.market}")
            proc.start()
            wr.close()
            bt_log("store_child", None, f"{key} pid={proc.pid}")
            _progress(key, plan, "reading", 0)
            while True:
                if rd.poll(0.5):
                    try:
                        msg = rd.recv()
                    except EOFError:
                        break
                    if "stage" in msg:
                        _progress(key, plan, msg["stage"], msg["frame"])
                    else:
                        result = msg
                elif not proc.is_alive():
                    break
            proc.join(10)
            if result.get("error"):
                raise RuntimeError(f"build process: {result['error']}")
            if not result.get("done"):
                raise RuntimeError(f"build process died (exit code {proc.exitcode})")
    key_cached = (_cache_root() / key / "meta.json").exists()
    if not key_cached:
        bt_log("store_child_no_cache", time.time() - t0, f"{key} the child left no cache: building in this process, in memory")
    get_store(plan, rule)  # from the cache (memory-mapped, quick), else built here in memory and pinned


def used_markets(runs_dir: Any) -> list[str]:
    """The instruments the tab really shows, most runs first: every finished run's config.instrument and config.instruments[].name.
    Only those that have a row in MARKETS. An instrument no run uses is not here: its store is built only when a request asks."""
    count: dict[str, int] = {}
    for _, d, _ in BV.find_runs(runs_dir):
        try:
            cfg = _record(d).get("config") or {}
        except (OSError, ValueError):
            continue
        names = {cfg.get("instrument")} | {i.get("name") for i in cfg.get("instruments") or [] if isinstance(i, dict)}
        for inst in names:
            if inst in MARKETS:
                count[inst] = count.get(inst, 0) + 1
    return [m for m, n in sorted(count.items(), key=lambda kv: (-kv[1], kv[0])) if n > 0]


def store_peek(plan: Plan, rule: dict) -> tuple[Optional[Store], Optional[dict]]:
    """(store, None) when the store is in memory or its disk cache exists (loading that is quick); else (None, status) after
    making sure a background thread is building it. `status` = {market, label, stage, frame, frames, elapsed_s} or {error}.
    The request never waits for a build."""
    key = store_key(plan, rule)
    with _LOCK:
        if key in _STORES:
            _STORES.move_to_end(key)
            return _STORES[key], None
    if (_cache_root() / key / "meta.json").exists():
        return get_store(plan, rule), None
    with _LOCK:
        job = _JOBS.get(key)
        if job and job.get("error") and time.time() - job["t_err"] < 60:
            return None, {"market": plan.market, "label": plan.label, "error": job["error"]}
        if not job or (not job["thread"].is_alive()):
            def run() -> None:
                t0 = time.time()
                try:
                    _build_store_job(plan, rule, key)
                    with _LOCK:
                        _JOBS.pop(key, None)
                except Exception as exc:  # noqa: BLE001 -- the page is told why there is no chart
                    with _LOCK:
                        _JOBS[key] = {"thread": threading.current_thread(), "error": f"{type(exc).__name__}: {exc}", "t_err": time.time()}
                        _PROGRESS.pop(key, None)
                    bt_log("store_build_failed", time.time() - t0, f"{key} {type(exc).__name__}: {exc}")
            th = threading.Thread(target=run, name=f"bt-store-{plan.market}", daemon=True)
            _JOBS[key] = {"thread": th, "error": None, "t_err": 0.0}
            _PROGRESS.setdefault(key, {"market": plan.market, "label": plan.label, "t0": time.time(), "stage": "starting", "frame": 0,
                                       "frames": len(FRAMES)})
            th.start()
        pr = dict(_PROGRESS.get(key) or {"market": plan.market, "label": plan.label, "t0": time.time(), "stage": "starting", "frame": 0,
                                         "frames": len(FRAMES)})
    pr["elapsed_s"] = round(time.time() - pr.pop("t0"), 1)
    return None, pr


def start_store_warmup(root: Path = REPO_ROOT, runs_dir: Any = None) -> threading.Thread:
    """At dashboard start: build, one after the other and in the background, the price store of the instruments the tab really
    uses (`used_markets(runs_dir)`, most runs first; one already in the disk cache is only read). An instrument no run uses is
    left alone until a request asks for it. With no `runs_dir` every instrument of MARKETS is made (the cards' one first)."""
    def run() -> None:
        t0 = time.time()
        try:
            rule = seal_rule(root)
        except SealBlocked as exc:
            bt_log("warmup", time.time() - t0, f"blocked: {exc}")
            return
        try:
            order = used_markets(runs_dir) if runs_dir is not None else sorted(MARKETS, key=lambda k: (k != "FX_BTC_JPY", k))
        except Exception as exc:  # noqa: BLE001
            bt_log("warmup", time.time() - t0, f"cannot tell the used instruments: {type(exc).__name__}: {exc}")
            return
        bt_log("warmup", None, "instruments: " + ", ".join(order))
        for m in order:
            t1 = time.time()
            try:
                plan = price_plan({"config": {"instrument": m}}, Path(root), rule)
                if not plan.files:
                    bt_log("warmup", time.time() - t1, f"{m}: no store ({plan.reason})")
                    continue
                store_peek(plan, rule)
                with _LOCK:
                    job = _JOBS.get(store_key(plan, rule))
                th = job["thread"] if job else None
                if th is not None:
                    th.join()
            except Exception as exc:  # noqa: BLE001 -- a warm-up must not stop the dashboard
                bt_log("warmup", time.time() - t1, f"{m}: {type(exc).__name__}: {exc}")
        bt_log("warmup", time.time() - t0, "done")
    th = threading.Thread(target=run, name="bt-store-warmup", daemon=True)
    th.start()
    return th


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


@dataclass
class Road:
    """A road run resolved for one request: its record, tables, the instrument and the seal cut."""
    run_id: str
    dir: str
    rec: dict
    data: Any  # road_view.RoadData
    inst: str
    cut: Cut


def _road(runs_dir: Any, run_id: str, root: Path, instrument: Optional[str]) -> Road:
    """Raises BacktestViewError (no such run), ChartError (not a road run / cannot be shown), SealBlocked, AfterSeal."""
    d = BV._run_dir(runs_dir, run_id)
    rec = _record(d)
    st = RV.status(d)
    if not st.ok:
        raise ChartError(st.reason)
    try:
        data = RV.load(d)
    except RV.RoadError as exc:
        raise ChartError(str(exc)) from None
    cfg = rec.get("config") or {}
    inst = instrument or cfg.get("instrument")
    if inst not in data.instruments:
        inst = data.instruments[0] if data.instruments else None
        if instrument and instrument not in data.instruments:
            raise ChartError(f"この走らせに銘柄 {instrument!r} は無い(あるのは {', '.join(data.instruments)})")
    if inst is None:
        raise ChartError("この走らせの道の記録に銘柄が無い")
    rule = seal_rule(root)
    cut = run_cut(rec, rule, inst)
    return Road(run_id, d, rec, data, inst, cut)


def _ranges(data: Any, range_name: Optional[str]) -> list[str]:
    if range_name in (None, "", "both"):
        return list(data.ranges) if range_name == "both" else [data.ranges[0]]
    if range_name not in data.ranges:
        raise ChartError(f"この走らせに約定の範囲 {range_name!r} は無い(あるのは {', '.join(data.ranges)})")
    return [range_name]


def run_summary(runs_dir: Any, run_id: str, root: Path = REPO_ROOT, range_name: Optional[str] = None,
                instrument: Optional[str] = None) -> dict:
    d = BV._run_dir(runs_dir, run_id)
    rec0 = _record(d)
    name = RC.strategy_name(rec0)
    led = RS.strategy_entry(name)
    base = {"run_id": run_id, "purpose": rec0.get("purpose"), "strategy": {"name": name, "title": led["title"], "fake": bool(led.get("fake")) or RC.is_synthetic(rec0)}}
    st = RV.status(d)
    if not st.ok:
        return {**base, "legacy": not RV.has_road(d), "unavailable": st.reason}
    try:
        tg = _road(runs_dir, run_id, Path(root), instrument)
    except (SealBlocked, AfterSeal) as exc:
        return {**base, "blocked": str(exc), "after_seal": isinstance(exc, AfterSeal)}
    data, rec, cut = tg.data, tg.rec, tg.cut
    plan = price_plan(rec, Path(root), seal_rule(root), tg.inst)
    mbar = _run_bar_s(rec, tg.inst)
    rng = _ranges(data, range_name)[0]
    crossing = cut.last_ns >= cut.limit_ns
    heads = {r: RV.headline(data, data.group(tg.inst, r), cut.limit_ns, crossing) for r in data.ranges}
    cfg = rec.get("config") or {}
    # a run that crosses the boundary: no summary.json number (it is the whole run's), and the row counts are those of the rows shown
    counts = ({t: int(data.visible(t, cut.limit_ns, True).sum()) for t in RV.CSV_TABLES} if crossing
              else {t: int(len(data.frames[t])) for t in RV.CSV_TABLES})
    return {**base, "road": {"version": data.version, "tables": counts, "bytes": int(data.nbytes), "counts_cut": crossing},
            "instrument": tg.inst, "instruments": data.instruments, "ranges": data.ranges,
            "range": rng, "range_ja": RV.RANGE_JA, "currency": "JPY" if _is_jpy(data) else None,
            "summary_rows": [] if crossing else [r for r in RV.summary_rows(data) if r.get("instrument") == tg.inst],
            "summary_cut": crossing, "summary_cut_reason": RV.SUMMARY_CUT_REASON if crossing else None, "headline": heads,
            "measure_interval_s": mbar or None,
            "period": {"first_s": cut.first_ns // 10**9, "last_s": cut.last_ns // 10**9, "last_incl_s": cut.last_ns // 10**9 - 1,
                       "first_iso": _iso(cut.first_ns / 1e9), "last_iso": _iso(cut.last_ns / 1e9)},
            "price": _summary_price(plan), "seal_boundary_s": cut.b // 10**9, "seal_boundary_iso": _iso(cut.b / 1e9),
            "config": {"strategy": cfg.get("strategy"), "fill": cfg.get("fill")}}


def _is_jpy(data: Any) -> bool:
    """Every money column the tab shows is in yen (pnl_jpy, pnl_jpy_cum): the road record is in yen by its SCHEMA."""
    return True


def run_chart(runs_dir: Any, run_id: str, from_s: Optional[float] = None, to_s: Optional[float] = None,
              max_bars: int = DEFAULT_MAX_BARS, range_name: Optional[str] = None, root: Path = REPO_ROOT,
              interval_s: Optional[int] = None, wait: bool = True, instrument: Optional[str] = None) -> dict:
    """Bars (from the instrument's price store) and the layers of the road tables (signals, orders, fills, the average
    entry price, trades, position and cumulative profit in yen) of the visible range [from_s, to_s] (UTC seconds; default:
    the run's period). `range_name` = pessimistic / optimistic / both. The range may leave the run's period; it is clipped
    to the store's data and to the seal boundary. Bars use the display frame `interval_s` (rounded up to a frame), or the
    smallest frame that gives at most `max_bars` bars; more than HARD_MAX_BARS bars narrow the range around its centre
    (`narrowed`). A layer with too many items in the range is not sent (`too_many`)."""
    tg = _road(runs_dir, run_id, Path(root), instrument)
    rec, cut, data = tg.rec, tg.cut, tg.data
    rule = seal_rule(root)
    rngs = _ranges(data, range_name)
    plan = price_plan(rec, Path(root), rule, tg.inst)
    price = _summary_price(plan)
    store = None
    building = None
    if price["available"]:
        try:
            if wait:
                store = get_store(plan, rule)
            else:  # the dashboard: never wait for a build; the page gets the progress and the numbers that need no price
                store, building = store_peek(plan, rule)
                if building and building.get("error"):
                    price.update(available=False, reason=f"価格の置き場を作れない({building['error']})")
                    building = None
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
    out: dict = {"run_id": run_id, "instrument": tg.inst, "instruments": data.instruments, "from_s": f, "to_s": t,
                 "interval_s": interval, "frames": list(FRAMES), "chart_lo_s": lo_s, "chart_hi_s": hi_s, "bars": [], "price": price,
                 "narrowed": narrowed, "measure_interval_s": _run_bar_s(rec, tg.inst) or None, "building": building,
                 "ranges": data.ranges, "range": range_name if range_name in (data.ranges + ["both"]) else rngs[0], "shown_ranges": rngs}
    if store is not None:
        tt, o, h, l, c_ = store.frames[interval]
        a = int(np.searchsorted(tt, int(f // interval * interval), side="left"))
        e = int(np.searchsorted(tt, min(int(np.ceil(t)), cut.b // 10**9), side="left"))  # a bar starting at the boundary never
        out["bars"] = [[int(x), float(y1), float(y2), float(y3), float(y4)]
                       for x, y1, y2, y3, y4 in zip(tt[a:e], o[a:e], h[a:e], l[a:e], c_[a:e])]
    f_ns, t_ns = int(f * 1e9), int(t * 1e9)
    out["layers"] = {r: RV.layers(data.group(tg.inst, r), f_ns, t_ns, cut.limit_ns, interval, cut.last_ns) for r in rngs}
    out["max_items"] = dict(RV.MAX_ITEMS)
    return out


def run_table(runs_dir: Any, run_id: str, table: str, root: Path = REPO_ROOT, instrument: Optional[str] = None,
              range_name: Optional[str] = None, sort: Optional[str] = None, desc: bool = False, filters: Optional[list] = None,
              page: int = 0, size: int = 100) -> dict:
    """One page of one table (every column), rows before the seal limit only. `range_name` = a side or "all"."""
    tg = _road(runs_dir, run_id, Path(root), instrument)
    rng = range_name if range_name else tg.data.ranges[0]
    if rng != "all" and rng not in tg.data.ranges:
        raise ChartError(f"この走らせに約定の範囲 {rng!r} は無い")
    try:
        out = RV.table_page(tg.data, table, tg.inst, rng, tg.cut.limit_ns, sort, desc, filters, page, size,
                            open_cut=tg.cut.last_ns >= tg.cut.limit_ns, cut_summary=tg.cut.last_ns >= tg.cut.limit_ns)
    except RV.RoadError as exc:
        raise ChartError(str(exc)) from None
    out.update(instrument=tg.inst, range=rng, run_id=run_id, table_ja=RV.TABLE_JA[table])
    return out


def run_trace(runs_dir: Any, run_id: str, table: str, row: int, root: Path = REPO_ROOT, instrument: Optional[str] = None) -> dict:
    tg = _road(runs_dir, run_id, Path(root), instrument)
    try:
        return RV.trace(tg.data, table, int(row), tg.cut.limit_ns, tg.cut.last_ns >= tg.cut.limit_ns)
    except RV.RoadError as exc:
        raise ChartError(str(exc)) from None


def run_files(runs_dir: Any, run_id: str, name: str) -> dict:
    """record.json or road/SCHEMA.json as written (the names are fixed; a name is never joined into a path)."""
    d = BV._run_dir(runs_dir, run_id)
    rel = {"record.json": "record.json", "SCHEMA.json": os.path.join(RV.ROAD_DIR, RV.SCHEMA_FILE)}.get(name)
    if rel is None:
        raise ChartError(f"見られるファイルは record.json と SCHEMA.json だけ: {name!r}")
    p = os.path.join(d, rel)
    if not os.path.isfile(p):
        raise ChartError(f"{name} が無い")
    with open(p, "r", encoding="utf-8") as fh:
        return {"run_id": run_id, "name": name, "json": json.load(fh)}


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
