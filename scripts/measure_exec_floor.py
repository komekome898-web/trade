#!/usr/bin/env python3
"""④-1 執行層の経費の床(`docs/PHASE2/EXEC/EXEC_FLOOR_PREREG.md` §2/§8)。

表 E-a〜E-i を生成し `docs/PHASE2/EXEC/exec_floor.json` に書く。過去の経費の数値は
一つも引用しない(`CLAUDE.md` §5.1)。すべて今回生のテープ/板/約定/資金調達率/遅延
ファイルから作る。実弾は使わない(K1 の値は RESULT.md §18.2 から**並べるだけ**で
再計算しない)。

データ:
    backtest_data/auto_bitflyer_executions_20260905/
        executions_YYYYMMDD.csv.gz  ts,price,size,side      2026-08-20〜09-05
        ticker_YYYYMMDD.csv.gz      ts,best_bid,best_ask,best_bid_size,best_ask_size
        board_top5_YYYYMMDD.csv.gz  ts,bid_px_1..5,bid_sz_1..5,ask_px_1..5,ask_sz_1..5
                                    2026-08-20〜08-26 のみ(7 日)
    data/funding_rate_history.csv  calculation_date,settlement_date,rate
    data/latency/ws_vm.csv         rts,exec_date,delay_s
    Binance/Bybit 1 分足(`k1_source.load_bars`)                2026-08-20〜08-31

    PYTHONPATH=src:scripts python scripts/measure_exec_floor.py
"""
from __future__ import annotations

import bisect
import csv
import gzip
import hashlib
import json
import math
import random
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
for p in (REPO / "src", REPO / "scripts"):
    sp = str(p)
    if sp not in sys.path:
        sys.path.insert(0, sp)

from bot.research.board import walk_cost_bp  # noqa: E402

import k1_source  # noqa: E402
import measure_katsuo_dispersion as base  # noqa: E402
import measure_katsuo_effect as eff  # noqa: E402

DATA_DIR = REPO / "backtest_data" / "auto_bitflyer_executions_20260905"
OUT_JSON = REPO / "docs" / "PHASE2" / "EXEC" / "exec_floor.json"

TICKER_START = date(2026, 8, 20)
TICKER_END = date(2026, 9, 5)
BOARD_START = date(2026, 8, 20)
BOARD_END = date(2026, 8, 26)
K1_START = date(2026, 8, 20)
K1_END = date(2026, 8, 31)

SIZES = (0.01, 0.05, 0.1, 0.5)
ADV_HORIZONS = (10, 60, 300)
MAKER_T = (60, 300)
BOOTSTRAP_REPS = 200
VOL_WINDOW = 100
QUOTE_GAP_EXCLUDE_SEC = 300.0  # data-hygiene threshold (documented, not a bar)
HOUR_BUCKET_WIDTH = 3
WEEKDAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
SIZE_BINS = ((0.0, 0.01, "<0.01"), (0.01, 0.05, "0.01-0.05"), (0.05, 0.1, "0.05-0.1"),
             (0.1, 0.5, "0.1-0.5"), (0.5, float("inf"), ">=0.5"))
MAIN_GATE_SMALL, MAIN_GATE_BIG = 19.0, 24.0
FEET_EF = (5, 15)


def daterange(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def parse_ts(s: str) -> float:
    return datetime.fromisoformat(s).timestamp()


def hour_bucket(ts: float) -> str:
    h = datetime.utcfromtimestamp(ts).hour
    h0 = (h // HOUR_BUCKET_WIDTH) * HOUR_BUCKET_WIDTH
    return f"{h0:02d}-{h0 + HOUR_BUCKET_WIDTH:02d}"


HOUR_BUCKET_LABELS = [f"{h:02d}-{h + HOUR_BUCKET_WIDTH:02d}" for h in range(0, 24, HOUR_BUCKET_WIDTH)]


def weekday_name(ts: float) -> str:
    return WEEKDAY_NAMES[datetime.utcfromtimestamp(ts).weekday()]


def size_bin(sz: float) -> str:
    for lo, hi, name in SIZE_BINS:
        if lo <= sz < hi:
            return name
    return SIZE_BINS[-1][2]


def edges_from_values(vals):
    vals = [v for v in vals if v is not None and v == v]
    if not vals:
        return None
    srt = sorted(vals)
    n = len(srt)

    def q(p):
        k = (n - 1) * p
        lo, hi = math.floor(k), math.ceil(k)
        return srt[int(k)] if lo == hi else srt[lo] * (hi - k) + srt[hi] * (k - lo)
    return (float(q(1 / 3)), float(q(2 / 3)))


def bucket_of(v, edges):
    if edges is None or v is None or v != v:
        return None
    q1, q2 = edges
    if v < q1:
        return "low"
    if v < q2:
        return "mid"
    return "high"


def unweighted_stats(values):
    n = len(values)
    if n == 0:
        return {"n": 0, "mean_bp": None, "p50_bp": None, "p90_bp": None, "p10_bp": None}
    srt = sorted(values)

    def pct(p):
        k = (n - 1) * p
        lo, hi = math.floor(k), math.ceil(k)
        return srt[int(k)] if lo == hi else srt[lo] * (hi - k) + srt[hi] * (k - lo)
    return {"n": n, "mean_bp": round(sum(values) / n, 4), "p10_bp": round(pct(0.10), 4),
            "p50_bp": round(pct(0.50), 4), "p90_bp": round(pct(0.90), 4)}


def weighted_stats(pairs):
    """``pairs`` = [(value, weight), ...]. Time-weighted p10/p50/p90 (nearest rank)."""
    if not pairs:
        return {"n": 0, "total_weight": 0.0, "p10_bp": None, "p50_bp": None, "p90_bp": None}
    pairs = sorted(pairs, key=lambda x: x[0])
    vals = [p[0] for p in pairs]
    wts = [p[1] for p in pairs]
    cum = []
    running = 0.0
    for w in wts:
        running += w
        cum.append(running)
    total = cum[-1]
    out = {"n": len(pairs), "total_weight_sec": round(total, 1)}
    for label, q in (("p10_bp", 0.10), ("p50_bp", 0.50), ("p90_bp", 0.90)):
        if total <= 0:
            out[label] = None
            continue
        target = q * total
        idx = bisect.bisect_left(cum, target)
        idx = min(idx, len(vals) - 1)
        out[label] = round(vals[idx], 4)
    return out


def seed_for(table: str, stratum: str) -> int:
    h = hashlib.sha256(f"{table}|{stratum}".encode("utf-8")).hexdigest()
    return int(h[:8], 16)


def day_block_bootstrap(values, day_keys, table: str, stratum: str, reps: int = BOOTSTRAP_REPS):
    """Day-block bootstrap 95% interval of the mean. Returns (lo, hi) or (None, None).

    Resampling whole days with replacement and taking the pooled mean is
    equivalent to resampling (day_sum, day_count) pairs and dividing the
    resampled totals -- the pooled mean never needs the day's individual
    values, only its sum and count. This turns each rep from O(n) into
    O(n_days), which matters here: some strata have hundreds of thousands
    of underlying executions/minutes.
    """
    if not values:
        return (None, None)
    by_day: dict = {}
    for v, d in zip(values, day_keys):
        s, c = by_day.get(d, (0.0, 0))
        by_day[d] = (s + v, c + 1)
    blocks = list(by_day.values())
    n_days = len(blocks)
    if n_days == 0:
        return (None, None)
    rng = random.Random(seed_for(table, stratum))
    means = []
    for _ in range(reps):
        tot_s = 0.0
        tot_c = 0
        for _ in range(n_days):
            s, c = blocks[rng.randrange(n_days)]
            tot_s += s
            tot_c += c
        if tot_c:
            means.append(tot_s / tot_c)
    if not means:
        return (None, None)
    means.sort()
    lo = means[int(0.025 * (len(means) - 1))]
    hi = means[int(0.975 * (len(means) - 1))]
    return (round(lo, 4), round(hi, 4))


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_ticker_day(d: date):
    path = DATA_DIR / f"ticker_{d:%Y%m%d}.csv.gz"
    out = []
    if not path.exists():
        return out
    with gzip.open(path, "rt", newline="") as f:
        r = csv.reader(f)
        next(r, None)
        for row in r:
            out.append((parse_ts(row[0]), float(row[1]), float(row[2]), float(row[3]), float(row[4])))
    return out


def load_exec_day(d: date):
    path = DATA_DIR / f"executions_{d:%Y%m%d}.csv.gz"
    out = []
    if not path.exists():
        return out
    with gzip.open(path, "rt", newline="") as f:
        r = csv.reader(f)
        next(r, None)
        for row in r:
            out.append((parse_ts(row[0]), float(row[1]), float(row[2]), row[3]))
    return out


def load_board_day(d: date):
    path = DATA_DIR / f"board_top5_{d:%Y%m%d}.csv.gz"
    out = []
    if not path.exists():
        return out
    with gzip.open(path, "rt", newline="") as f:
        r = csv.reader(f)
        next(r, None)
        for row in r:
            ts = parse_ts(row[0])
            bid_px = [float(x) if x != "" else None for x in row[1:6]]
            bid_sz = [float(x) if x != "" else None for x in row[6:11]]
            ask_px = [float(x) if x != "" else None for x in row[11:16]]
            ask_sz = [float(x) if x != "" else None for x in row[16:21]]
            out.append((ts, bid_px, bid_sz, ask_px, ask_sz))
    return out


def board_row_valid(bid_px, ask_px):
    bvals = [x for x in bid_px if x is not None]
    avals = [x for x in ask_px if x is not None]
    if not bvals or not avals:
        return False
    if any(bvals[i] < bvals[i + 1] for i in range(len(bvals) - 1)):
        return False
    if any(avals[i] > avals[i + 1] for i in range(len(avals) - 1)):
        return False
    if bvals[0] >= avals[0]:
        return False
    return True


print("=== ④-1 執行層の経費の床: データ読み込み ===")

ticker_all = []   # (ts, bid, ask, bid_sz, ask_sz)
exec_all = []      # (ts, price, size, side)
board_by_day = {}  # date -> rows
per_day_check = {}

for d in daterange(TICKER_START, TICKER_END):
    tick = load_ticker_day(d)
    ex = load_exec_day(d)
    crossed = sum(1 for _, b, a, _, _ in tick if b >= a)
    regress = sum(1 for i in range(1, len(ex)) if ex[i][0] < ex[i - 1][0])
    entry = {
        "ticker_rows": len(tick), "crossed_count": crossed,
        "exec_rows": len(ex), "exec_regression_count": regress,
    }
    if BOARD_START <= d <= BOARD_END:
        bd = load_board_day(d)
        nonmono = sum(1 for _ts, bpx, _bsz, apx, _asz in bd if not board_row_valid(bpx, apx))
        entry["board_rows"] = len(bd)
        entry["board_nonmonotone_count"] = nonmono
        board_by_day[d] = bd
    per_day_check[d.isoformat()] = entry
    ticker_all.extend(tick)
    exec_all.extend(ex)
    print(f"  {d}: ticker {len(tick):,} / exec {len(ex):,} rows"
          + (f" / board {entry.get('board_rows', 0):,}" if d in board_by_day else ""))

ticker_all.sort(key=lambda x: x[0])
exec_all.sort(key=lambda x: x[0])
print(f"合計: ticker {len(ticker_all):,} / exec {len(exec_all):,} / board 日数 {len(board_by_day)}")

# ---------------------------------------------------------------------------
# データ検査
# ---------------------------------------------------------------------------

print("\n=== データ検査 ===")


def day_bounds(d: date):
    start = datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp()
    return start, start + 86400.0


def attribute_to_days(t0, t1):
    out = {}
    t = t0
    while t < t1:
        d = datetime.utcfromtimestamp(t).date()
        _dstart, dend = day_bounds(d)
        seg_end = min(t1, dend)
        out[d] = out.get(d, 0.0) + (seg_end - t)
        t = seg_end
    return out


gaps = []
for i in range(1, len(ticker_all)):
    gap = ticker_all[i][0] - ticker_all[i - 1][0]
    if gap > QUOTE_GAP_EXCLUDE_SEC:
        gaps.append((ticker_all[i - 1][0], ticker_all[i][0], gap))

missing_by_day: dict = {}
for t0, t1, _g in gaps:
    for d, sec in attribute_to_days(t0, t1).items():
        missing_by_day[d] = missing_by_day.get(d, 0.0) + sec

global_first, global_last = ticker_all[0][0], ticker_all[-1][0]


def day_span(d: date) -> float:
    dstart, dend = day_bounds(d)
    lo, hi = max(dstart, global_first), min(dend, global_last)
    return max(0.0, hi - lo)


total_crossed = sum(e["crossed_count"] for e in per_day_check.values())
total_ticker_rows = sum(e["ticker_rows"] for e in per_day_check.values())
total_regress = sum(e["exec_regression_count"] for e in per_day_check.values())
total_exec_rows = sum(e["exec_rows"] for e in per_day_check.values())
total_nonmono = sum(e.get("board_nonmonotone_count", 0) for e in per_day_check.values())
total_board_rows = sum(e.get("board_rows", 0) for e in per_day_check.values())

for d_iso, entry in per_day_check.items():
    d = date.fromisoformat(d_iso)
    span = day_span(d)
    entry["quote_missing_share"] = (round(missing_by_day.get(d, 0.0) / span, 4) if span > 0 else None)

data_check = {
    "note": ("日ごとの気配欠測時間の割合(300秒超の ticker ギャップを『欠測』とする、データ衛生上の"
             "しきい値。帰無・MDE・判定バーではない)、best_bid≥best_ask の件数、板5段の非単調"
             "件数、約定タイムスタンプの逆行件数。異常な時間帯・行は当該テーブルから個別に除外し、"
             "除外した割合をここに記録する(全量からの一括除外ではない: 気配欠測は時間区間として"
             "E-a/E-c/E-d/E-e から、板の非単調行は当該 1 秒サンプルのみ E-b から、crossed ticker 行は"
             "その気配の有効区間のみ E-a/E-c/E-d/E-e から、約定逆行は当該約定行のみ E-c/E-d から除外)。"),
    "quote_gap_exclude_threshold_sec": QUOTE_GAP_EXCLUDE_SEC,
    "per_day": per_day_check,
    "overall": {
        "ticker_rows": total_ticker_rows,
        "crossed_count": total_crossed,
        "crossed_share": round(total_crossed / total_ticker_rows, 6) if total_ticker_rows else None,
        "exec_rows": total_exec_rows,
        "exec_regression_count": total_regress,
        "exec_regression_share": round(total_regress / total_exec_rows, 6) if total_exec_rows else None,
        "board_rows": total_board_rows,
        "board_nonmonotone_count": total_nonmono,
        "board_nonmonotone_share": round(total_nonmono / total_board_rows, 6) if total_board_rows else None,
        "quote_missing_seconds": round(sum(missing_by_day.values()), 1),
        "quote_missing_share": round(sum(missing_by_day.values()) / (global_last - global_first), 6),
        "span_sec": round(global_last - global_first, 1),
        "n_gaps_over_threshold": len(gaps),
        "largest_gaps_sec": sorted([round(g, 1) for _t0, _t1, g in gaps], reverse=True)[:5],
    },
}
print(f"  ticker {total_ticker_rows:,} 行 / crossed {total_crossed} ({data_check['overall']['crossed_share']:.4%}) "
      f"/ 気配欠測 {data_check['overall']['quote_missing_share']:.4%} "
      f"({len(gaps)} 区間、最大 {data_check['overall']['largest_gaps_sec'][:2]} 秒)")
print(f"  板 {total_board_rows:,} 行 / 非単調 {total_nonmono} ({data_check['overall']['board_nonmonotone_share']:.4%})")
print(f"  約定 {total_exec_rows:,} 行 / 逆行 {total_regress}")

# ---------------------------------------------------------------------------
# 気配の有効ルックアップ(crossed を除く。空区間 = 欠測とみなす)
# ---------------------------------------------------------------------------

valid_ticker = [(t, b, a) for t, b, a, _bs, _as in ticker_all if b < a and (b + a) > 0]
valid_ts = [x[0] for x in valid_ticker]


def lookup_quote(t: float):
    """最後の有効気配(t 以前)。300 秒より古ければ欠測として None。"""
    idx = bisect.bisect_right(valid_ts, t) - 1
    if idx < 0:
        return None
    ts0, b0, a0 = valid_ticker[idx]
    if t - ts0 > QUOTE_GAP_EXCLUDE_SEC:
        return None
    return ((b0 + a0) / 2.0, b0, a0)


# ---------------------------------------------------------------------------
# bitFlyer 1 分足(約定テープから構築)と局所ボラ三分位
# ---------------------------------------------------------------------------

print("\n=== bitFlyer 1 分足(約定テープ由来)とボラ三分位 ===")

minute_close: dict = {}
for ts, price, _size, _side in exec_all:
    m = int(ts // 60) * 60
    minute_close[m] = price  # exec_all は ts 昇順 -> 最後の代入がその分の close

minutes_sorted = sorted(minute_close)
closes = [minute_close[m] for m in minutes_sorted]
n_min = len(closes)
rets = [0.0] * n_min
for i in range(1, n_min):
    rets[i] = abs(closes[i] / closes[i - 1] - 1.0) if closes[i - 1] > 0 else 0.0
cum = [0.0] * (n_min + 1)
for i in range(1, n_min):
    cum[i + 1] = cum[i] + rets[i]
vol_prev_arr = [None] * n_min
for i in range(VOL_WINDOW + 1, n_min):
    vol_prev_arr[i] = (cum[i] - cum[i - VOL_WINDOW]) / VOL_WINDOW
minute_vol = {minutes_sorted[i]: vol_prev_arr[i] for i in range(n_min) if vol_prev_arr[i] is not None}
vol_edges = edges_from_values(minute_vol.values())


def vol_of_ts(t: float):
    return minute_vol.get(int(t // 60) * 60)


print(f"  1 分足 {n_min:,} 本(約定 0 の分は行を作らない = 欠測)。ボラ三分位の境目(直前{VOL_WINDOW}分"
      f"の|close/close-1|平均) = {vol_edges}")

# ---------------------------------------------------------------------------
# E-a 気配スプレッド
# ---------------------------------------------------------------------------

print("\n=== E-a 気配スプレッド ===")


def build_quote_intervals():
    """(spread_bp, weight_sec, t0) のリスト。crossed/欠測ギャップは除外。"""
    out = []
    excluded_weight = 0.0
    total_weight = 0.0
    for i in range(len(ticker_all) - 1):
        t0, b0, a0, _bs, _as = ticker_all[i]
        t1 = ticker_all[i + 1][0]
        w = t1 - t0
        if w <= 0:
            continue
        total_weight += w
        if w > QUOTE_GAP_EXCLUDE_SEC or b0 >= a0 or (b0 + a0) <= 0:
            excluded_weight += w
            continue
        mid = (b0 + a0) / 2.0
        spread_bp = (a0 - b0) / mid * 1e4
        out.append((spread_bp, w, t0))
    return out, excluded_weight, total_weight


quote_intervals, ea_excluded_w, ea_total_w = build_quote_intervals()
print(f"  区間 {len(quote_intervals):,} 件、除外重み {ea_excluded_w:,.0f}s / 全重み {ea_total_w:,.0f}s "
      f"({ea_excluded_w / ea_total_w:.4%})")

e_a_overall = weighted_stats([(sp, w) for sp, w, _t in quote_intervals])

by_hour: dict = {lbl: [] for lbl in HOUR_BUCKET_LABELS}
by_weekday: dict = {w: [] for w in WEEKDAY_NAMES}
by_vol: dict = {"low": [], "mid": [], "high": []}
for sp, w, t0 in quote_intervals:
    by_hour[hour_bucket(t0)].append((sp, w))
    by_weekday[weekday_name(t0)].append((sp, w))
    vb = bucket_of(vol_of_ts(t0), vol_edges)
    if vb:
        by_vol[vb].append((sp, w))

e_a = {
    "note": ("(ask-bid)/mid の bp、区間の秒数で時間加重した p10/p50/p90(最近接ランク)。"
             "crossed 気配・300秒超のギャップは除外(データ検査)。"),
    "excluded_weight_share": round(ea_excluded_w / ea_total_w, 6) if ea_total_w else None,
    "overall": e_a_overall,
    "by_hour_utc": {k: weighted_stats(v) for k, v in by_hour.items()},
    "by_weekday": {k: weighted_stats(v) for k, v in by_weekday.items()},
    "by_vol_tercile": {k: weighted_stats(v) for k, v in by_vol.items()},
}
print(f"  overall p50={e_a_overall['p50_bp']} p90={e_a_overall['p90_bp']} bp (n={e_a_overall['n']:,})")

# per-minute time-weighted average spread (for E-f's minute-level comparison).
# Single forward pass over ticker_all with a persistent pointer -- O(n_ticker + n_minutes).
minute_starts = list(range(int(global_first // 60) * 60, int(global_last // 60) * 60 + 60, 60))
ea_by_minute: dict = {}
_n_ticker = len(ticker_all)
_j = 0
for m0 in minute_starts:
    m1 = m0 + 60.0
    while _j + 1 < _n_ticker and ticker_all[_j + 1][0] <= m0:
        _j += 1
    acc_w = 0.0
    acc_val = 0.0
    t_cursor = m0
    k = _j
    while t_cursor < m1 and k < _n_ticker:
        t0k, b0k, a0k, _bs, _as = ticker_all[k]
        t1k = ticker_all[k + 1][0] if k + 1 < _n_ticker else m1
        seg_end = min(m1, t1k)
        if seg_end <= t_cursor:
            k += 1
            continue
        w = seg_end - t_cursor
        if w > QUOTE_GAP_EXCLUDE_SEC or b0k >= a0k or (b0k + a0k) <= 0 or (t1k - t0k) > QUOTE_GAP_EXCLUDE_SEC:
            pass  # excluded interval: crossed / missing gap
        else:
            mid = (b0k + a0k) / 2.0
            acc_val += (a0k - b0k) / mid * 1e4 * w
            acc_w += w
        t_cursor = seg_end
        k += 1
    if acc_w > 0:
        ea_by_minute[m0] = acc_val / acc_w
    _j = max(_j, k - 1)

print(f"  分単位系列 {len(ea_by_minute):,} / {len(minute_starts):,} 分に値あり")

# ---------------------------------------------------------------------------
# E-b 成行の片道コスト(板を歩く)
# ---------------------------------------------------------------------------

print("\n=== E-b 板を歩くコスト ===")

board_samples = []  # (ts, mid, bid_levels, ask_levels)
board_excluded = 0
board_total = 0
for d, rows in sorted(board_by_day.items()):
    for ts, bpx, bsz, apx, asz in rows:
        board_total += 1
        if not board_row_valid(bpx, apx):
            board_excluded += 1
            continue
        mid = (bpx[0] + apx[0]) / 2.0
        bid_levels = [(bpx[i], bsz[i]) for i in range(5) if bpx[i] is not None and bsz[i] is not None]
        ask_levels = [(apx[i], asz[i]) for i in range(5) if apx[i] is not None and asz[i] is not None]
        board_samples.append((ts, mid, bid_levels, ask_levels))

print(f"  板サンプル {board_total:,} 件、非単調で除外 {board_excluded:,} 件 "
      f"({board_excluded / board_total:.4%})、有効 {len(board_samples):,} 件")

# 0.01 BTC の片道/往復コストは E-f でも使うので分単位で引けるように保存する
eb001_by_minute: dict = {}

eb_cells: dict = {}  # size -> {"buy":[...], "sell":[...], "roundtrip":[...]} of (bp, ts)
eb_exhausted: dict = {}  # size -> {"buy":0, "sell":0, "either":0}
for x in SIZES:
    eb_cells[x] = {"buy": [], "sell": [], "roundtrip": []}
    eb_exhausted[x] = {"buy": 0, "sell": 0, "either": 0}

for ts, mid, bid_levels, ask_levels in board_samples:
    for x in SIZES:
        buy_bp, _fb, exh_b = walk_cost_bp(ask_levels, x, mid, "buy")
        sell_bp, _fs, exh_s = walk_cost_bp(bid_levels, x, mid, "sell")
        if exh_b:
            eb_exhausted[x]["buy"] += 1
        if exh_s:
            eb_exhausted[x]["sell"] += 1
        if exh_b or exh_s:
            eb_exhausted[x]["either"] += 1
        if buy_bp is not None:
            eb_cells[x]["buy"].append((buy_bp, ts))
        if sell_bp is not None:
            eb_cells[x]["sell"].append((sell_bp, ts))
        if buy_bp is not None and sell_bp is not None:
            rt = buy_bp + sell_bp
            eb_cells[x]["roundtrip"].append((rt, ts))
            if x == 0.01:
                eb001_by_minute.setdefault(int(ts // 60) * 60, []).append(rt)

# 分あたり複数の 1 秒サンプルがあるので、その分の最初の有効サンプルを代表値にする
eb001_by_minute = {m: vals[0] for m, vals in eb001_by_minute.items()}


def eb_side_stats(pairs):
    vals = [v for v, _t in pairs]
    return unweighted_stats(vals)


def eb_breakdown(pairs):
    by_h = {lbl: [] for lbl in HOUR_BUCKET_LABELS}
    by_v = {"low": [], "mid": [], "high": []}
    for v, t in pairs:
        by_h[hour_bucket(t)].append(v)
        vb = bucket_of(vol_of_ts(t), vol_edges)
        if vb:
            by_v[vb].append(v)
    return ({k: unweighted_stats(v) for k, v in by_h.items()},
            {k: unweighted_stats(v) for k, v in by_v.items()})


e_b = {
    "note": ("板の 1 秒サンプル(2026-08-20〜08-26、7 日)を best から順に食ったときの片道コスト"
             "(bp、vs mid)。板の外(5 段で足りない)を『exhausted』として件数を数える(板5段のみ"
             "なので、この件数と往復コストは滑りの下限)。往復 = 同一サンプルの買い片道 + 売り片道。"
             "非単調(データ検査)なサンプルは全サイズ共通で除外。"),
    "excluded_share": round(board_excluded / board_total, 6) if board_total else None,
    "n_samples_valid": len(board_samples),
    "sizes": {},
}
for x in SIZES:
    overall = {side: eb_side_stats(eb_cells[x][side]) for side in ("buy", "sell", "roundtrip")}
    by_hour_side = {}
    by_vol_side = {}
    for side in ("buy", "sell", "roundtrip"):
        bh, bv = eb_breakdown(eb_cells[x][side])
        by_hour_side[side] = bh
        by_vol_side[side] = bv
    e_b["sizes"][str(x)] = {
        "overall": overall,
        "exhausted_count": eb_exhausted[x],
        "exhausted_share_of_valid_samples": {
            k: round(v / len(board_samples), 6) if board_samples else None
            for k, v in eb_exhausted[x].items()
        },
        "by_hour_utc": by_hour_side,
        "by_vol_tercile": by_vol_side,
    }
    print(f"  X={x} BTC: buy p50={overall['buy']['p50_bp']} sell p50={overall['sell']['p50_bp']} "
          f"roundtrip p50={overall['roundtrip']['p50_bp']} p90={overall['roundtrip']['p90_bp']} bp "
          f"(n={overall['roundtrip']['n']:,}, exhausted either={eb_exhausted[x]['either']:,})")

# ---------------------------------------------------------------------------
# E-c 実現スプレッド / E-d 逆選択(代理)
# ---------------------------------------------------------------------------

print("\n=== E-c 実現スプレッド / E-d 逆選択(代理) ===")

# 各約定について: 直前の有効気配(E-c)と、10/60/300 秒後の有効気配(E-d)。
# ルックアップが欠測(300秒より古い/無い)なら、その約定はその表から除外する。
ec_rows = []   # (realized_bp, side, ts, day, vol_bucket, size_bin)
ed_rows = {h: [] for h in ADV_HORIZONS}  # h -> (signed_bp, side, ts, day, vol_bucket, size_bin)
ec_excluded = 0
ed_excluded = {h: 0 for h in ADV_HORIZONS}

for ts, price, size, side in exec_all:
    q = lookup_quote(ts)
    if q is None:
        ec_excluded += 1
        for h in ADV_HORIZONS:
            ed_excluded[h] += 1
        continue
    mid_now, _b, _a = q
    day = datetime.utcfromtimestamp(ts).date()
    vb = bucket_of(vol_of_ts(ts), vol_edges)
    sb = size_bin(size)
    realized_bp = abs(price - mid_now) / mid_now * 1e4
    ec_rows.append((realized_bp, side, ts, day, vb, sb))
    side_sign = 1.0 if side == "BUY" else -1.0
    for h in ADV_HORIZONS:
        qf = lookup_quote(ts + h)
        if qf is None:
            ed_excluded[h] += 1
            continue
        mid_future, _bf, _af = qf
        signed_bp = side_sign * (mid_future - mid_now) / mid_now * 1e4
        ed_rows[h].append((signed_bp, side, ts, day, vb, sb))

print(f"  約定 {len(exec_all):,} 件、直前気配欠測で E-c/E-d から除外 {ec_excluded:,} "
      f"({ec_excluded / len(exec_all):.4%})")
for h in ADV_HORIZONS:
    print(f"  E-d {h}s: さらに将来気配欠測で除外 {ed_excluded[h] - ec_excluded:,} "
          f"(採用 {len(ed_rows[h]):,} 件)")


def side_scopes(rows, side_idx=1):
    return {"ALL": rows, "BUY": [r for r in rows if r[side_idx] == "BUY"],
            "SELL": [r for r in rows if r[side_idx] == "SELL"]}


def ec_breakdown(rows):
    by_hour = {lbl: [] for lbl in HOUR_BUCKET_LABELS}
    by_vol = {"low": [], "mid": [], "high": []}
    by_size = {name: [] for _lo, _hi, name in SIZE_BINS}
    for v, _side, ts, _day, vb, sb in rows:
        by_hour[hour_bucket(ts)].append(v)
        if vb:
            by_vol[vb].append(v)
        by_size[sb].append(v)
    return {
        "overall": unweighted_stats([r[0] for r in rows]),
        "by_hour_utc": {k: unweighted_stats(v) for k, v in by_hour.items()},
        "by_vol_tercile": {k: unweighted_stats(v) for k, v in by_vol.items()},
        "by_size_bin": {k: unweighted_stats(v) for k, v in by_size.items()},
    }


e_c = {
    "note": ("各約定について |約定価格 − 直前の有効気配の mid| / mid(bp)。直前の有効気配が"
             "300秒より古い/無い約定は除外(件数は上に記録)。"),
    "excluded_count": ec_excluded, "excluded_share": round(ec_excluded / len(exec_all), 6),
    "by_side": {side: ec_breakdown(rows) for side, rows in side_scopes(ec_rows).items()},
}
for side, rows in side_scopes(ec_rows).items():
    st = unweighted_stats([r[0] for r in rows])
    print(f"  E-c {side}: n={st['n']:,} p50={st['p50_bp']} p90={st['p90_bp']} bp")


def ed_breakdown_with_ci(table_key, rows):
    by_hour = {lbl: [] for lbl in HOUR_BUCKET_LABELS}
    by_vol = {"low": [], "mid": [], "high": []}
    by_size = {name: [] for _lo, _hi, name in SIZE_BINS}
    for v, _side, ts, day, vb, sb in rows:
        by_hour[hour_bucket(ts)].append((v, day))
        if vb:
            by_vol[vb].append((v, day))
        by_size[sb].append((v, day))

    def stat_with_ci(pairs, stratum):
        vals = [v for v, _d in pairs]
        days = [d for _v, d in pairs]
        st = unweighted_stats(vals)
        lo, hi = day_block_bootstrap(vals, days, table_key, stratum)
        st["ci95_bp"] = [lo, hi]
        return st

    overall_pairs = [(v, day) for v, _side, _ts, day, _vb, _sb in rows]
    return {
        "overall": stat_with_ci(overall_pairs, "overall"),
        "by_hour_utc": {k: stat_with_ci(v, f"hour={k}") for k, v in by_hour.items()},
        "by_vol_tercile": {k: stat_with_ci(v, f"vol={k}") for k, v in by_vol.items()},
        "by_size_bin": {k: stat_with_ci(v, f"size={k}") for k, v in by_size.items()},
    }


e_d = {
    "note": ("約定の H 秒後(10/60/300)の有効気配 mid の変化を、テイカー側の向きに符号を付けて"
             "(BUY=+1, SELL=-1)平均(bp)。直前/H秒後どちらかの有効気配が欠測な約定は除外。"
             "95%区間は日単位ブロックブートストラップ(200 反復、種 = sha256(table|stratum))。"),
    "excluded_by_horizon": {str(h): ed_excluded[h] for h in ADV_HORIZONS},
    "excluded_share_by_horizon": {str(h): round(ed_excluded[h] / len(exec_all), 6) for h in ADV_HORIZONS},
    "by_horizon": {},
}
for h in ADV_HORIZONS:
    e_d["by_horizon"][str(h)] = {
        side: ed_breakdown_with_ci(f"e_d|{h}s|{side}", rows)
        for side, rows in side_scopes(ed_rows[h]).items()
    }
    ov = e_d["by_horizon"][str(h)]["ALL"]["overall"]
    print(f"  E-d {h}s ALL: n={ov['n']:,} mean={ov['mean_bp']} bp CI95={ov['ci95_bp']}")

# ---------------------------------------------------------------------------
# E-e 指値の代理量(触れられ率・触れられた後の逆選択)
# ---------------------------------------------------------------------------

print("\n=== E-e 指値の代理量 ===")

exec_ts = [e[0] for e in exec_all]
exec_price = [e[1] for e in exec_all]


def execs_touching(t0, t1, want_le=None, want_ge=None):
    """(t0, t1] の約定価格の中に want_le 以下(買い指値の代理)/ want_ge 以上
    (売り指値の代理)を満たす最初のものがあれば (touch_ts, price) を返す。"""
    lo = bisect.bisect_right(exec_ts, t0)
    hi = bisect.bisect_right(exec_ts, t1)
    for i in range(lo, hi):
        p = exec_price[i]
        if want_le is not None and p <= want_le:
            return exec_ts[i], p
        if want_ge is not None and p >= want_ge:
            return exec_ts[i], p
    return None


ee_by_minute: dict = {}   # minute -> {T: {"touched_buy":bool,"touched_sell":bool,"drift_buy":.., "drift_sell":..}}
ee_valid_minutes = 0
ee_no_quote_minutes = 0

for m0 in minute_starts:
    q = lookup_quote(m0)
    if q is None:
        ee_no_quote_minutes += 1
        continue
    ee_valid_minutes += 1
    _mid0, bid0, ask0 = q
    entry = {}
    for T in MAKER_T:
        t_end = m0 + T
        hit_buy = execs_touching(m0, t_end, want_le=bid0)
        hit_sell = execs_touching(m0, t_end, want_ge=ask0)
        cell = {"touched_buy": hit_buy is not None, "touched_sell": hit_sell is not None,
                "drift_buy_bp": None, "drift_sell_bp": None}
        if hit_buy is not None:
            touch_ts, _p = hit_buy
            q_touch = lookup_quote(touch_ts)
            q_after = lookup_quote(touch_ts + T)
            if q_touch is not None and q_after is not None and q_touch[0] > 0:
                cell["drift_buy_bp"] = (q_after[0] - q_touch[0]) / q_touch[0] * 1e4
        if hit_sell is not None:
            touch_ts, _p = hit_sell
            q_touch = lookup_quote(touch_ts)
            q_after = lookup_quote(touch_ts + T)
            if q_touch is not None and q_after is not None and q_touch[0] > 0:
                cell["drift_sell_bp"] = -1.0 * (q_after[0] - q_touch[0]) / q_touch[0] * 1e4
        entry[T] = cell
    ee_by_minute[m0] = entry

print(f"  分 {len(minute_starts):,} 件、開始時の有効気配あり {ee_valid_minutes:,} "
      f"/ 欠測で除外 {ee_no_quote_minutes:,}")


def ee_aggregate(T, filt=None):
    """filt(m0) -> bool でサブセットする。touched_share と drift の (n, mean, p50, CI) を返す。"""
    n_valid = 0
    n_touch_buy = n_touch_sell = 0
    drift_vals = []
    drift_days = []
    for m0, entry in ee_by_minute.items():
        if filt is not None and not filt(m0):
            continue
        n_valid += 1
        cell = entry[T]
        if cell["touched_buy"]:
            n_touch_buy += 1
            if cell["drift_buy_bp"] is not None:
                drift_vals.append(cell["drift_buy_bp"])
                drift_days.append(datetime.utcfromtimestamp(m0).date())
        if cell["touched_sell"]:
            n_touch_sell += 1
            if cell["drift_sell_bp"] is not None:
                drift_vals.append(cell["drift_sell_bp"])
                drift_days.append(datetime.utcfromtimestamp(m0).date())
    return n_valid, n_touch_buy, n_touch_sell, drift_vals, drift_days


def ee_cell(T, stratum_label, filt=None):
    n_valid, n_tb, n_ts_, drift_vals, drift_days = ee_aggregate(T, filt)
    drift_stats = unweighted_stats(drift_vals)
    lo, hi = day_block_bootstrap(drift_vals, drift_days, f"e_e|T{T}", stratum_label)
    drift_stats["ci95_bp"] = [lo, hi]
    return {
        "n_valid_minutes": n_valid,
        "touched_share_buy": round(n_tb / n_valid, 4) if n_valid else None,
        "touched_share_sell": round(n_ts_ / n_valid, 4) if n_valid else None,
        "post_touch_drift_bp": drift_stats,
    }


e_e = {
    "note": ("毎分の開始時点で有効な best_bid に買い指値・best_ask に売り指値を仮定。T 秒以内に"
             "約定テープがその価格以下(買い)/以上(売り)で印字したら『触れられた』(列の順番・"
             "部分約定は分からない代理量、約定の上限)。触れられた場合、そのタッチのT秒後の"
             "有効気配 mid の変化を、指値の向き(買い指値なら+、売り指値なら-)で符号付けした"
             "ものを逆選択の代理として集計(買い・売りのタッチをまとめた符号付きプールに95%区間、"
             "日単位ブロックブートストラップ)。指値開始時点で有効気配が欠測の分は除外。"),
    "excluded_no_quote_minutes": ee_no_quote_minutes,
    "by_T": {},
}
for T in MAKER_T:
    e_e["by_T"][str(T)] = {
        "overall": ee_cell(T, "overall"),
        "by_hour_utc": {lbl: ee_cell(T, f"hour={lbl}",
                                      filt=lambda m0, lbl=lbl: hour_bucket(m0) == lbl)
                        for lbl in HOUR_BUCKET_LABELS},
        "by_vol_tercile": {vb: ee_cell(T, f"vol={vb}",
                                        filt=lambda m0, vb=vb: bucket_of(vol_of_ts(m0), vol_edges) == vb)
                           for vb in ("low", "mid", "high")},
    }
    ov = e_e["by_T"][str(T)]["overall"]
    print(f"  T={T}s: touched_buy={ov['touched_share_buy']:.2%} touched_sell={ov['touched_share_sell']:.2%} "
          f"drift mean={ov['post_touch_drift_bp']['mean_bp']} bp CI95={ov['post_touch_drift_bp']['ci95_bp']}")

# ---------------------------------------------------------------------------
# E-f シグナル分の床(Binance / Bybit、2026-08-20〜08-31)
# ---------------------------------------------------------------------------

print("\n=== E-f シグナル分の床 ===")


def k1_day_range_seconds(start: date, end: date):
    s = int(datetime(start.year, start.month, start.day, tzinfo=timezone.utc).timestamp())
    e = int(datetime(end.year, end.month, end.day, tzinfo=timezone.utc).timestamp()) + 86400
    return s, e


K1_MIN_TS, K1_MAX_TS = k1_day_range_seconds(K1_START, K1_END)

e_f_sources = {}
signal_minute_sets = {}  # (source, foot) -> list of next_minute_ts

for source in ("binance", "bybit"):
    rows_1m, n_read, n_dropped = (
        k1_source.load_binance_minutes(K1_START, K1_END) if source == "binance"
        else k1_source.load_bybit_minutes(K1_START, K1_END)
    )
    print(f"  {source}: 1 分足 {len(rows_1m):,} 行(読み込み {n_read:,}、落とし {n_dropped:,})")
    per_foot = {}
    for foot in FEET_EF:
        bars = base.fold(rows_1m, foot)
        sigs = eff.signals(bars, MAIN_GATE_SMALL, MAIN_GATE_BIG, flip_body=True)
        next_minutes = []
        for i, (sig, _lc, _cs, strength) in enumerate(sigs):
            if sig == 0 or strength != "weak":
                continue
            bar_ts = bars[i][0]
            nm = bar_ts + foot * 60
            if K1_MIN_TS <= nm < K1_MAX_TS:
                next_minutes.append(nm)
        signal_minute_sets[(source, foot)] = next_minutes
        per_foot[str(foot)] = {"n_signal_bars_weak": len(next_minutes), "n_bars": len(bars)}
        print(f"    足{foot}分: 弱いシグナル(門 s19/b24)のバー {len(next_minutes):,} / 全バー {len(bars):,}")
    e_f_sources[source] = per_foot


def unconditional_minutes_in_range(lo_ts, hi_ts):
    return [m for m in minute_starts if lo_ts <= m < hi_ts]


uncond_minutes_k1 = unconditional_minutes_in_range(K1_MIN_TS, K1_MAX_TS)
uncond_minutes_k1_board = [m for m in uncond_minutes_k1
                            if BOARD_START <= datetime.utcfromtimestamp(m).date() <= BOARD_END]


def ea_values_for(minutes):
    return [ea_by_minute[m] for m in minutes if m in ea_by_minute]


def eb001_values_for(minutes):
    return [eb001_by_minute[m] for m in minutes if m in eb001_by_minute]


def ee_touch_drift_for(minutes, T):
    n_valid = n_tb = n_ts_ = 0
    drift = []
    for m in minutes:
        entry = ee_by_minute.get(m)
        if entry is None:
            continue
        n_valid += 1
        cell = entry[T]
        if cell["touched_buy"]:
            n_tb += 1
            if cell["drift_buy_bp"] is not None:
                drift.append(cell["drift_buy_bp"])
        if cell["touched_sell"]:
            n_ts_ += 1
            if cell["drift_sell_bp"] is not None:
                drift.append(cell["drift_sell_bp"])
    return n_valid, n_tb, n_ts_, drift


e_f_unconditional = {
    "e_a_same_days": unweighted_stats(ea_values_for(uncond_minutes_k1)),
    "e_b_001_same_days_board_window": unweighted_stats(eb001_values_for(uncond_minutes_k1_board)),
    "e_e": {},
}
for T in MAKER_T:
    n_valid, n_tb, n_ts_, drift = ee_touch_drift_for(uncond_minutes_k1, T)
    e_f_unconditional["e_e"][str(T)] = {
        "n_valid_minutes": n_valid,
        "touched_share_buy": round(n_tb / n_valid, 4) if n_valid else None,
        "touched_share_sell": round(n_ts_ / n_valid, 4) if n_valid else None,
        "post_touch_drift_bp": unweighted_stats(drift),
    }

e_f_cells = {}
for (source, foot), minutes in signal_minute_sets.items():
    minutes_board = [m for m in minutes
                      if BOARD_START <= datetime.utcfromtimestamp(m).date() <= BOARD_END]
    cell = {
        "n_signal_minutes": len(minutes),
        "n_signal_minutes_in_board_window": len(minutes_board),
        "e_a": unweighted_stats(ea_values_for(minutes)),
        "e_b_001": unweighted_stats(eb001_values_for(minutes_board)),
        "e_e": {},
    }
    for T in MAKER_T:
        n_valid, n_tb, n_ts_, drift = ee_touch_drift_for(minutes, T)
        cell["e_e"][str(T)] = {
            "n_valid_minutes": n_valid,
            "touched_share_buy": round(n_tb / n_valid, 4) if n_valid else None,
            "touched_share_sell": round(n_ts_ / n_valid, 4) if n_valid else None,
            "post_touch_drift_bp": unweighted_stats(drift),
        }
    e_f_cells[f"{source}|{foot}"] = cell
    print(f"  {source} 足{foot}分: シグナル分 n={len(minutes):,}(板window内 {len(minutes_board):,}) "
          f"E-a p50={cell['e_a']['p50_bp']} bp / E-b(0.01) p50={cell['e_b_001']['p50_bp']} bp")

e_f = {
    "note": ("海外(Binance/Bybit)のK1設計シグナル(flip_body=True、弱いのみ、門 s19/b24、足5・15分、"
             "1本delay= 信号バー確定後の次の1分)が出た分の bitFlyer 側 E-a・E-b(0.01BTC)・E-e を、"
             "同じ日(2026-08-20〜08-31)の無条件の値(全分)と横に。E-b は板が2026-08-20〜08-26しか"
             "無いため、その7日に落ちるシグナル分だけを別掲(件数を明記)。K1 の成績(勝敗・リターン)"
             "そのものは測っていない -- signal_bars を数えるだけ。"),
    "sources": e_f_sources,
    "unconditional_same_days": e_f_unconditional,
    "cells": e_f_cells,
}

# ---------------------------------------------------------------------------
# E-g 資金調達率
# ---------------------------------------------------------------------------

print("\n=== E-g 資金調達率 ===")

FUNDING_PATH = REPO / "data" / "funding_rate_history.csv"
funding_rows = []
with open(FUNDING_PATH, newline="", encoding="utf-8") as f:
    r = csv.DictReader(f)
    for row in r:
        funding_rows.append((row["calculation_date"], row["settlement_date"], float(row["rate"])))

abs_rates = sorted(abs(r[2]) for r in funding_rows)
calc_dates = sorted(r[0] for r in funding_rows)


def plain_pct(srt, p):
    n = len(srt)
    if n == 0:
        return None
    k = (n - 1) * p
    lo, hi = math.floor(k), math.ceil(k)
    return srt[int(k)] if lo == hi else srt[lo] * (hi - k) + srt[hi] * (k - lo)


p50_rate = plain_pct(abs_rates, 0.50)
p90_rate = plain_pct(abs_rates, 0.90)
e_g = {
    "note": ("data/funding_rate_history.csv(8時間ごと、3回/日の資金調達率)。標本は"
             f"{calc_dates[0]}〜{calc_dates[-1]}({len(funding_rows)}行)。標本が短いので"
             "頻度の統計は出さない、水準だけ。daily_equivalent は 1 日 3 回分の単純合算"
             "(複利化していない近似)。"),
        "sample_dates": [calc_dates[0], calc_dates[-1]],
        "n": len(funding_rows),
        "abs_rate_p50": p50_rate,
        "abs_rate_p90": p90_rate,
        "daily_equivalent_p50": None if p50_rate is None else round(p50_rate * 3, 6),
        "daily_equivalent_p90": None if p90_rate is None else round(p90_rate * 3, 6),
}
print(f"  標本 {calc_dates[0]}〜{calc_dates[-1]}({len(funding_rows)}行) "
      f"|rate| p50={p50_rate} p90={p90_rate} 日次換算 p50={e_g['daily_equivalent_p50']}")

# ---------------------------------------------------------------------------
# E-h 遅延
# ---------------------------------------------------------------------------

print("\n=== E-h 遅延 ===")

LATENCY_PATH = REPO / "data" / "latency" / "ws_vm.csv"
delays = []
lat_first = lat_last = None
with open(LATENCY_PATH, newline="", encoding="utf-8") as f:
    r = csv.DictReader(f)
    for row in r:
        delays.append(float(row["delay_s"]))
        if lat_first is None:
            lat_first = row["exec_date"]
        lat_last = row["exec_date"]

delays_sorted = sorted(delays)
e_h = {
    "note": ("data/latency/ws_vm.csv: WS 受信遅れ(この VM、`rts` − 取引所 `exec_date`)。"
             "オーナー PC の値ではない。**注文応答(order-ack)の遅延は未測定**"
             "(この単位のデータには存在しない -- CLAUDE.md / EXEC_FLOOR_PREREG.md §5)。"),
    "sample_range": [lat_first, lat_last],
    "n": len(delays),
    "delay_s_p10": round(plain_pct(delays_sorted, 0.10), 6) if delays_sorted else None,
    "delay_s_p50": round(plain_pct(delays_sorted, 0.50), 6) if delays_sorted else None,
    "delay_s_p90": round(plain_pct(delays_sorted, 0.90), 6) if delays_sorted else None,
    "order_ack_latency": "unmeasured",
}
print(f"  n={len(delays)} 標本 {lat_first}〜{lat_last} delay_s p50={e_h['delay_s_p50']} p90={e_h['delay_s_p90']}")
print("  注文応答(order-ack)の遅延は未測定")

# ---------------------------------------------------------------------------
# E-i 床のまとめ
# ---------------------------------------------------------------------------

print("\n=== E-i 床のまとめ ===")

rt001 = e_b["sizes"]["0.01"]["overall"]["roundtrip"]
rt001_high_vol = e_b["sizes"]["0.01"]["by_vol_tercile"]["roundtrip"]["high"]
ee60_overall = e_e["by_T"]["60"]["overall"]
ee300_overall = e_e["by_T"]["300"]["overall"]

e_f_rt001_by_cell = {}
for key, cell in e_f_cells.items():
    e_f_rt001_by_cell[key] = {
        "n": cell["e_b_001"]["n"], "p50_bp": cell["e_b_001"]["p50_bp"], "p90_bp": cell["e_b_001"]["p90_bp"],
    }

e_i = {
    "note": ("往復の成行コスト(0.01 BTC、E-b)の p50/p90: 無条件(板7日) / 高ボラ三分位(板7日) / "
             "K1シグナル分(E-f、板window内のみ。件数が少ないことに注意)。指値の触れられ率・"
             "触れられた後の逆選択(E-e)。K1の経費前の値(RESULT.md §18.2、2022〜2026、"
             "門s19/b24、弱い。**再計算していない、並べるだけ、引き算はしない**)。"),
    "roundtrip_taker_cost_001btc_bp": {
        "unconditional": {"p50": rt001["p50_bp"], "p90": rt001["p90_bp"], "n": rt001["n"]},
        "high_vol_tercile": {"p50": rt001_high_vol["p50_bp"], "p90": rt001_high_vol["p90_bp"],
                              "n": rt001_high_vol["n"]},
        "k1_signal_minutes_by_source_foot": e_f_rt001_by_cell,
    },
    "maker_touched_share_and_post_touch_drift": {
        "T60": {"touched_share_buy": ee60_overall["touched_share_buy"],
                "touched_share_sell": ee60_overall["touched_share_sell"],
                "post_touch_drift_bp": ee60_overall["post_touch_drift_bp"]},
        "T300": {"touched_share_buy": ee300_overall["touched_share_buy"],
                 "touched_share_sell": ee300_overall["touched_share_sell"],
                 "post_touch_drift_bp": ee300_overall["post_touch_drift_bp"]},
    },
    "k1_pre_cost_bp_per_trade_RESULT_18_2_not_recomputed": {
        "5min": {"mean_bp": 0.70, "ci95_bp": [-3.20, 4.81], "n": 5066,
                 "source": "docs/PHASE2/K1/RESULT.md §18.2 (Bybit->bitFlyer 横断、2022-2026)"},
        "15min": {"mean_bp": 1.75, "ci95_bp": [-1.51, 5.06], "n": 5591,
                  "source": "docs/PHASE2/K1/RESULT.md §18.2 (Bybit->bitFlyer 横断、2022-2026)"},
    },
}
print(f"  往復0.01BTC 無条件 p50={rt001['p50_bp']} p90={rt001['p90_bp']} bp / "
      f"高ボラ p50={rt001_high_vol['p50_bp']} p90={rt001_high_vol['p90_bp']} bp")
print("  K1 経費前(並べるだけ): 5分 +0.70 / 15分 +1.75 bp/取引")

# ---------------------------------------------------------------------------
# 書き出し
# ---------------------------------------------------------------------------

payload = {
    "note": ("④-1 執行層の経費の床(EXEC_FLOOR_PREREG.md)。過去の経費の数値は一つも引用していない"
             "(CLAUDE.md §5.1)。すべて今回、backtest_data/auto_bitflyer_executions_20260905 の"
             "テープ/板/約定と data/funding_rate_history.csv・data/latency/ws_vm.csv・"
             "Binance/Bybit 1分足から生成。実弾は使っていない。帰無・MDE・判定バーは作っていない。"),
    "data_ranges": {
        "ticker_executions": [TICKER_START.isoformat(), TICKER_END.isoformat()],
        "board_top5": [BOARD_START.isoformat(), BOARD_END.isoformat()],
        "k1_signal_overlap": [K1_START.isoformat(), K1_END.isoformat()],
    },
    "data_check": data_check,
    "vol_tercile_edges_bp_like": vol_edges,
    "e_a_quoted_spread": e_a,
    "e_b_board_walk_cost": e_b,
    "e_c_realized_spread": e_c,
    "e_d_adverse_selection": e_d,
    "e_e_maker_proxy": e_e,
    "e_f_signal_minute_floor": e_f,
    "e_g_funding_rate": e_g,
    "e_h_latency": e_h,
    "e_i_floor_summary": e_i,
}

OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
print(f"\n→ {OUT_JSON}")

