"""前提の直接の測り(D1b)担当 G1 の 4 項目(# 1・# 2・# 3・# 9)で共有する道具。

委任文: docs/DISCUSSIONS/2026-10-06_held_batches/DELEGATION_d1b_impl.md(担当 G1)
表の行: docs/DISCUSSIONS/2026-10-06_held_batches/D1B_FRAMINGS.md の # 1・# 2・# 3・# 9

読み口: 封印の門(bot.bt.data の load / load_reference)を通す scripts/w4_measure/common.py の既にある口
(load_bars・binance_ref_dataset・usdjpy_ref_dataset)。ここでは import するだけで、common.py は変えない。
終わりは委任文の決まりで 2023-12-17T15:00Z(HI_MAX)。これより後を読まない・使わない(h が越える値は NaN にして数える)。

区間(委任文の共通の決まり): 日の塊のブートストラップ = bot.bt.validation.block_bootstrap_ci(循環、塊 5 日、
1,000 回、種 20261006)。日 = 日本時間の暦日。期間の全部の暦日(件数 0 の日も)を並べ、日の番号を再標本にして、
  1 件あたりの値 = 再標本の日の Σ値 ÷ 再標本の日の Σ件数(scripts/w4_measure/daily_stats.py の _boot と同じ作り)
  1 日あたりの値 = 再標本の日の和の平均
を出す。se = 再標本の標準偏差(ddof 1)、MDE = 2.8 × se(委任文)。前半・後半 = 日数で 2 つ(前半 = 日数 // 2 日)。
後半 − 前半 の区間は出さない(委任文に無い。同じ種で 2 つの半分を選び直すと差の区間が狭く出る)。年ごとの表は記述。
"""
from __future__ import annotations

import json
import math
import os
import sys
from datetime import datetime, timezone

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
W4 = os.path.join(ROOT, "scripts", "w4_measure")
if W4 not in sys.path:
    sys.path.insert(0, W4)

NS = 1_000_000_000
MIN_NS = 60 * NS
DAY_NS = 86_400 * NS
JST_NS = 9 * 3600 * NS
BP = 10_000.0
SEED = 20261006
N_RES = 1000
BLOCK_DAYS = 5
ALPHA = 0.05
MDE_K = 2.8
HI_MAX_ISO = "2023-12-17T15:00:00Z"  # 委任文「2023-12-17T15:00Z より後を読まない」


def iso_ns(s: str) -> int:
    d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return int(d.timestamp()) * NS


HI_MAX = iso_ns(HI_MAX_ISO)


def ns_iso(ns: int) -> str:
    return datetime.fromtimestamp(int(ns) // NS, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")  # 切り捨て(小数の丸めで日をまたがない)


def check_hi(hi_ns: int) -> None:
    if hi_ns > HI_MAX:
        raise SystemExit(f"拒否: 終わり {ns_iso(hi_ns)} は {HI_MAX_ISO} より後(委任文の決まり)")


def jst_day(t_ns) -> np.ndarray:
    """日本時間の暦日の番号(1970-01-01 からの日数)。"""
    return (np.asarray(t_ns, dtype=np.int64) + JST_NS) // DAY_NS


def day_iso(d: int) -> str:
    return str(np.datetime64(int(d), "D"))


def day_year(d) -> np.ndarray:
    return np.asarray(d).astype("datetime64[D]").astype("datetime64[Y]").astype(np.int64) + 1970


# ---------------------------------------------------------------------------------------------- 読み込み
def bars_np(d: str, symbol: str, lo_ns: int, hi_ns: int) -> dict:
    """1 分足を年ごとに封印の門(common.load_bars)から読み、空でない足(volume > 0)だけの配列にする。
    start = 足の始まり、end = 足の終わり(= start + 60 秒)。"""
    from common import load_bars
    check_hi(hi_ns)
    cols = {k: [] for k in ("start", "end", "open", "high", "low", "close")}
    files = {}
    y = datetime.fromtimestamp(lo_ns / 1e9, tz=timezone.utc).year
    a = lo_ns
    while a < hi_ns:
        b = min(hi_ns, iso_ns(f"{y + 1}-01-01T00:00:00Z"))
        bars, _kinds, h = load_bars(d, symbol, a, b)
        files.update(h)
        ne = [x for x in bars if x.volume > 0]
        cols["start"].append(np.array([int(x.start_time_ns) for x in ne], dtype=np.int64))
        cols["end"].append(np.array([int(x.exchange_time_ns) for x in ne], dtype=np.int64))
        for k in ("open", "high", "low", "close"):
            cols[k].append(np.array([float(getattr(x, k)) for x in ne], dtype=float))
        del bars, ne
        a, y = b, y + 1
    out = {k: np.concatenate(v) if v else np.empty(0) for k, v in cols.items()}
    out["files"] = files
    return out


def ref_np(dataset: dict, name: str, decl: dict) -> tuple[np.ndarray, np.ndarray, list]:
    """参照の系列を封印の門(load_reference)から読み、(行の時刻, 値, manifest)。"""
    from bot.bt.data.reference import load_reference
    s = load_reference(ROOT, dataset, declarations={name: decl[name]})
    return np.array(s.times_ns, dtype=np.int64), np.array(s.values, dtype=float), [list(m) for m in s.manifest]


def binance_ohlc(lo_ns: int, hi_ns: int, kind: str, cols=("open", "high", "low", "close")) -> dict:
    """Binance の 1 分足の 4 本値(行の時刻 = 分の始まり)。kind = "spot"(現物 BTCUSDT)/ "um"(USD-M BTCUSDT)。
    宣言はカード 2 の CARD.md の宣言(binance_open など。遅れ 60 秒)をそのまま使う。"""
    from common import BIN_DIR, BIN_FILE, binance_ref_dataset, paths
    from bot.research.cards import cardmd
    check_hi(hi_ns)
    with open(os.path.join(ROOT, "docs/RESEARCH/cards/c2_owner_xvenue_wick/CARD.md"), encoding="utf-8") as fh:
        st, problems = cardmd.settings(cardmd.parse(fh.read()))
    if problems:
        raise SystemExit(f"カード 2 の CARD.md の宣言が読めない: {problems}")
    decl = dict(st.declarations)
    prefix, d, f = {"spot": ("binance", BIN_DIR, BIN_FILE),
                    "um": ("binance_um", "backtest_data/binance_um_BTCUSDT_1m_20261002",
                           "binance_um_BTCUSDT_1m_{y}.csv.gz")}[kind]
    out, man = {}, {}
    for c in cols:
        name = f"{prefix}_{c}"
        ds = binance_ref_dataset(name, c, lo_ns, hi_ns)
        ds["paths"] = paths(d, f, lo_ns, hi_ns)
        t, v, m = ref_np(ds, name, decl)
        if "t" in out and not np.array_equal(out["t"], t):
            raise SystemExit(f"{name} の行の時刻が他の列と違う")
        out["t"], out[c] = t, v
        man[name] = m
    out["manifest"] = man
    return out


# ---------------------------------------------------------------------------------------------- 値を引く
def asof_idx(times: np.ndarray, q) -> np.ndarray:
    """times(昇順)の中で q 以下の最後の位置。無ければ −1。"""
    return np.searchsorted(times, np.asarray(q, dtype=np.int64), side="right") - 1


def exact_idx(times: np.ndarray, q) -> np.ndarray:
    """times の中で q と同じ値の位置。無ければ −1。"""
    q = np.asarray(q, dtype=np.int64)
    i = np.searchsorted(times, q, side="left")
    ok = (i < len(times)) & (times[np.minimum(i, len(times) - 1)] == q) if len(times) else np.zeros(q.shape, bool)
    return np.where(ok, i, -1)


def take(v: np.ndarray, i: np.ndarray) -> np.ndarray:
    """v[i]、i < 0 は NaN。"""
    i = np.asarray(i)
    out = np.full(i.shape, np.nan)
    m = i >= 0
    out[m] = v[i[m]]
    return out


def path_extremes(ends: np.ndarray, high: np.ndarray, low: np.ndarray, t0, t1) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """足の終わりが (t0, t1] に入る足の、高値の最大・安値の最小・足の数。足が無ければ NaN・NaN・0。
    疎な表(稀な最大・最小)で O(1) に引く。"""
    t0 = np.asarray(t0, dtype=np.int64)
    t1 = np.asarray(t1, dtype=np.int64)
    a = np.searchsorted(ends, t0, side="right")
    b = np.searchsorted(ends, t1, side="right")  # [a, b)
    n = b - a
    hi = np.full(t0.shape, np.nan)
    lo = np.full(t0.shape, np.nan)
    m = n > 0
    if m.any():
        hi[m] = _range_reduce(high, a[m], b[m], np.maximum)
        lo[m] = _range_reduce(low, a[m], b[m], np.minimum)
    return hi, lo, n


def _range_reduce(v: np.ndarray, a: np.ndarray, b: np.ndarray, op) -> np.ndarray:
    """v[a:b] の op(最大・最小)を、2 の冪の疎な表で引く(a < b)。"""
    n = len(v)
    L = int(np.max(b - a))
    levels = [v]
    k = 1
    while 2 * k <= L:
        prev = levels[-1]
        levels.append(op(prev[:-k], prev[k:]) if len(prev) > k else prev[:0])
        k *= 2
    ln = b - a
    j = np.floor(np.log2(ln)).astype(int)
    out = np.empty(len(a))
    for jj in np.unique(j):
        m = j == jj
        tab = levels[jj]
        w = 1 << jj
        out[m] = op(tab[a[m]], tab[b[m] - w])
    del n
    return out


# ---------------------------------------------------------------------------------------------- 区間
def _boot_stat(sums: np.ndarray, cnts: np.ndarray, per: str) -> tuple:
    from bot.bt.validation import block_bootstrap_ci
    D = len(sums)
    if D < 2:
        return None
    reps = []

    def stat(xs):
        i = xs.astype(np.int64)
        if per == "event":
            c = cnts[i].sum()
            v = sums[i].sum() / c if c > 0 else np.nan
        else:
            v = sums[i].mean()
        reps.append(v)
        return float(v) if np.isfinite(v) else 0.0  # 再標本の値は reps から取る(件数 0 の再標本は数える)

    L = min(BLOCK_DAYS, D)
    block_bootstrap_ci([float(i) for i in range(D)], block_len=L, n_resamples=N_RES, seed=SEED, alpha=ALPHA,
                       method="circular", statistic=stat)
    return np.array(reps[:N_RES], dtype=float)


def summarize(sums: np.ndarray, cnts: np.ndarray, per: str = "event") -> dict:
    """日ごとの和 sums・件数 cnts(期間の全部の暦日)から、点・区間・se・MDE。per = "event"(1 件あたり)/ "day"(1 日あたり)。"""
    sums = np.asarray(sums, dtype=float)
    cnts = np.asarray(cnts, dtype=float)
    n = int(cnts.sum())
    D = len(sums)
    if per == "event":
        est = float(sums.sum() / n) if n > 0 else float("nan")
    else:
        est = float(sums.mean()) if D else float("nan")
    out = {"n": n, "n_days": D, "estimate": est}
    reps = _boot_stat(sums, cnts, per) if (n > 0 or per == "day") else None
    if reps is None:
        out.update(ci=[None, None], se=None, mde=None, n_resample_empty=None)
        return out
    good = reps[np.isfinite(reps)]
    lo, hi = np.quantile(good, [ALPHA / 2, 1 - ALPHA / 2]) if len(good) > 1 else (np.nan, np.nan)
    se = float(np.std(good, ddof=1)) if len(good) > 1 else float("nan")
    out.update(ci=[float(lo), float(hi)], se=se, mde=MDE_K * se, n_resample_empty=int((~np.isfinite(reps)).sum()))
    out["_reps"] = reps
    return out


def by_day(values: np.ndarray, days: np.ndarray, all_days: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """値(NaN は除く)を暦日ごとに和と件数へ。all_days = 期間の全部の暦日(昇順)。"""
    v = np.asarray(values, dtype=float)
    d = np.asarray(days, dtype=np.int64)
    m = np.isfinite(v)
    pos = np.searchsorted(all_days, d[m])
    if len(pos) and (pos.max() >= len(all_days) or not np.array_equal(all_days[pos], d[m])):
        raise ValueError("期間の外の日の値がある")
    s = np.bincount(pos, weights=v[m], minlength=len(all_days))
    c = np.bincount(pos, minlength=len(all_days)).astype(float)
    return s, c


def table(values: np.ndarray, days: np.ndarray, all_days: np.ndarray, per: str = "event",
          with_years: bool = True) -> dict:
    """全期間・年ごと(記述)・前半・後半。"""
    s, c = by_day(values, days, all_days)
    v = np.asarray(values, dtype=float)
    out = {"n_nan": int((~np.isfinite(v)).sum())}
    full = summarize(s, c, per)
    out["全期間"] = _strip(full, all_days)
    if with_years:
        ys = day_year(all_days)
        out["年ごと(記述)"] = {str(int(y)): _strip(summarize(s[ys == y], c[ys == y], per), all_days[ys == y])
                            for y in np.unique(ys)}
    D = len(all_days)
    h = D // 2
    a = summarize(s[:h], c[:h], per)
    b = summarize(s[h:], c[h:], per)
    out["前半"] = _strip(a, all_days[:h])
    out["後半"] = _strip(b, all_days[h:])
    # 後半 − 前半 の区間は出さない(委任文の共通の決まりに無い。2 つの半分を同じ種で選び直すと再標本どうしが似て、差の区間が
    # 狭く出るため。要るならリードが種の決め方を決めてから足す)
    return out


def _strip(r: dict, days: np.ndarray) -> dict:
    r = {k: v for k, v in r.items() if k != "_reps"}
    if len(days):
        r["days"] = [day_iso(days[0]), day_iso(days[-1])]
    return r


def all_days_between(lo_ns: int, hi_ns: int) -> np.ndarray:
    """[lo, hi) に掛かる日本時間の暦日を全部(昇順)。"""
    return np.arange(int(jst_day(lo_ns)), int(jst_day(hi_ns - 1)) + 1, dtype=np.int64)


def quantiles(v: np.ndarray, qs=(0.05, 0.25, 0.5, 0.75, 0.95)) -> dict:
    v = np.asarray(v, dtype=float)
    v = v[np.isfinite(v)]
    if not len(v):
        return {}
    return {f"q{int(q * 100):02d}": float(np.quantile(v, q)) for q in qs}


# ---------------------------------------------------------------------------------------------- 件数
def count_table(days: np.ndarray, all_days: np.ndarray) -> dict:
    """件数だけ(値を見ない): 全期間・年ごと・前半・後半の件数と日数。"""
    d = np.asarray(days, dtype=np.int64)
    ys_all = day_year(all_days)
    h = len(all_days) // 2
    first = all_days[:h]
    out = {"全期間": {"n": int(len(d)), "n_days": int(len(all_days))}}
    out["年ごと"] = {str(int(y)): {"n": int((day_year(d) == y).sum()) if len(d) else 0,
                                 "n_days": int((ys_all == y).sum())} for y in np.unique(ys_all)}
    if h:
        out["前半"] = {"n": int((d <= first[-1]).sum()), "n_days": h, "days": [day_iso(all_days[0]), day_iso(first[-1])]}
        out["後半"] = {"n": int((d > first[-1]).sum()), "n_days": len(all_days) - h,
                     "days": [day_iso(all_days[h]), day_iso(all_days[-1])]}
    return out


# ---------------------------------------------------------------------------------------------- 書き出し
def _clean(o):
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating, float)):
        f = float(o)
        return f if math.isfinite(f) else None
    return o


def write_json(obj, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(_clean(obj), fh, ensure_ascii=False, indent=1)
        fh.write("\n")


def fmt(x, nd=2, sign=True) -> str:
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return "—"
    return f"{x:+.{nd}f}" if sign else f"{x:.{nd}f}"


def md_stat_rows(label: str, t: dict, nd: int = 2) -> list[str]:
    """table() の結果を Markdown の行に(全期間・前半・後半・年ごと)。"""
    rows = []

    def one(name, r):
        ci = r.get("ci") or [None, None]
        rows.append(f"| {label} | {name} | {r.get('n', '')} | {r.get('n_days', '')} | {fmt(r.get('estimate'), nd)} | "
                    f"[{fmt(ci[0], nd)}, {fmt(ci[1], nd)}] | {fmt(r.get('mde'), nd, False)} |")
    for k in ("全期間", "前半", "後半"):
        if k in t:
            one(k, t[k])
    for y, r in t.get("年ごと(記述)", {}).items():
        one(f"{y}(記述)", r)
    return rows


MD_STAT_HEAD = ["| 量 | 区切り | 件数 | 日数 | 点 | 95% 区間 | MDE(2.8 × se) |", "|---|---|---|---|---|---|---|"]


def md_counts(title: str, ct: dict, unit: str) -> list[str]:
    L = [f"### {title}", "", f"| 区切り | {unit} | 日数 |", "|---|---|---|"]
    L.append(f"| 全期間 | {ct['全期間']['n']} | {ct['全期間']['n_days']} |")
    for k in ("前半", "後半"):
        if k in ct:
            L.append(f"| {k}({ct[k]['days'][0]}〜{ct[k]['days'][1]}) | {ct[k]['n']} | {ct[k]['n_days']} |")
    for y, r in ct["年ごと"].items():
        L.append(f"| {y} | {r['n']} | {r['n_days']} |")
    return L + [""]
