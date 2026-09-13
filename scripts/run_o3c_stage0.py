#!/usr/bin/env python3
"""O-3c 段0(Q1)判定区間の実行スクリプト。事前登録 PREREG.md のとおりに測る。

固定値(PREREG §6、変更禁止):
  gap_ms=60_000 / size_tolerance=0.25 / staleness(起点・反応窓とも)=300_000 / max_attempts=200
反応窓(PREREG §3): 1,5,15,60 分
族(PREREG §3): 向き long/short の2水準のみ(mixed は記述のみ)× 反応窓4 × 主張2(行きすぎ/転換) = 16
対照(PREREG §4): 主=プラセボ(規模一致) / 副=無清算窓
判定区間(PREREG §5): 2024-06-13〜2024-10-14(124日)のみ

速度優先の実装上の工夫(§3に記録する。固定値は変えていない):
  - 価格系列は aggTrades の全ティックではなく「1分バーの終値」に集約してから
    PriceSeries.from_ohlc_bars に渡す(全ティックを Trade dataclass にすると
    ~24.3M件・ピークメモリ 5.2GB・113秒かかることを実測したため)。
    anchor/future の staleness は 300_000ms(5分)なので、1分粒度の系列で
    近傍点が見つからない状況はほぼ生じない(空白が5分以上ある場合のみ NaN)。
  - 出来高バー(プラセボ抽出用)も同じ1分粒度で作る。
"""
from __future__ import annotations

import csv
import random
import sys
import time
import zipfile
from datetime import date
from pathlib import Path

sys.path.insert(0, "/home/user/trade/src")

import numpy as np

from bot.research import liq_response as lr

ROOT = Path("/home/user/trade/backtest_data/binance_cm_o3c_20260913")
OUT_DIR = Path("/home/user/trade/results/o3c_stage0")
OUT_DIR.mkdir(parents=True, exist_ok=True)

START = date(2024, 6, 13)
END = date(2024, 10, 14)
GAP_MS = 60_000
SIZE_TOL = 0.25
STALENESS_MS = 300_000
MAX_ATTEMPTS = 200
HORIZONS = (1, 5, 15, 60)
SEED_BASE = 42  # 固定・報告に明記

t_start_all = time.time()
log = []


def log_(msg: str) -> None:
    print(msg)
    log.append(msg)


# --------------------------------------------------------------------- #
# 1. 清算イベント読み込み・カスケード構成
# --------------------------------------------------------------------- #
t0 = time.time()
events = lr.load_binance_cm_liquidations(ROOT / "liquidationSnapshot" / "BTCUSD_PERP", START, END)
t_load_liq = time.time() - t0
log_(f"liquidation events loaded: n={len(events)} time={t_load_liq:.1f}s "
     f"range={min(e.ts_ms for e in events)}..{max(e.ts_ms for e in events)}")

real_all = lr.build_cascades(events, "binance_cm", gap_ms=GAP_MS)
long_all = [c for c in real_all if c.direction == "long"]
short_all = [c for c in real_all if c.direction == "short"]
mixed_all = [c for c in real_all if c.direction == "mixed"]
log_(f"cascades: total={len(real_all)} long={len(long_all)} short={len(short_all)} mixed={len(mixed_all)}")

# --------------------------------------------------------------------- #
# 2. 1分バー(終値・出来高)を aggTrades からストリーム構築(速度優先)
# --------------------------------------------------------------------- #
t0 = time.time()
price_bars: list[tuple[int, float]] = []  # (minute_start_ms, close)
vol_bars: list[tuple[int, int, float]] = []  # (start_ms, end_ms, volume)

cur_minute = None
cur_vol = 0.0
cur_close = None
n_rows = 0
n_files = 0
agg_root = ROOT / "aggTrades" / "BTCUSD_PERP"
for zpath in sorted(agg_root.glob("*-aggTrades-*.zip")):
    day = date.fromisoformat("-".join(zpath.stem.rsplit("-", 3)[1:]))
    if day < START or day > END:
        continue
    n_files += 1
    with zipfile.ZipFile(zpath) as zf:
        names = [n for n in zf.namelist() if n.endswith(".csv")]
        assert len(names) == 1, (zpath, names)
        with zf.open(names[0]) as fh:
            reader = csv.reader((line.decode("utf-8") for line in fh))
            header = next(reader, None)
            assert header is not None and header[0] == "agg_trade_id", (zpath, header)
            for row in reader:
                if not row:
                    continue
                _id, price_s, _qty, _first, _last, ts_s, _ibm = row[:7]
                ts = int(ts_s)
                price = float(price_s)
                qty = float(_qty)
                n_rows += 1
                minute = ts - (ts % 60_000)
                if cur_minute is None:
                    cur_minute = minute
                if minute != cur_minute:
                    price_bars.append((cur_minute, cur_close))
                    vol_bars.append((cur_minute, cur_minute + 60_000, cur_vol))
                    cur_minute = minute
                    cur_vol = 0.0
                cur_vol += qty
                cur_close = price
if cur_minute is not None:
    price_bars.append((cur_minute, cur_close))
    vol_bars.append((cur_minute, cur_minute + 60_000, cur_vol))
t_bars = time.time() - t0
log_(f"1min bars built: files={n_files} rows={n_rows} bars={len(price_bars)} time={t_bars:.1f}s")

prices = lr.PriceSeries.from_ohlc_bars(
    [(ts, c, c, c, c) for ts, c in price_bars], ts_unit="ms"
)

# --------------------------------------------------------------------- #
# 3. 対照群(プラセボ・無清算窓)
# --------------------------------------------------------------------- #
t0 = time.time()
span_start = min(e.ts_ms for e in events)
span_end = max(e.ts_ms for e in events)

placebo_long = lr.sample_placebo_windows(long_all, vol_bars, events, "binance_cm",
                                          size_tolerance=SIZE_TOL, rng=random.Random(SEED_BASE))
placebo_short = lr.sample_placebo_windows(short_all, vol_bars, events, "binance_cm",
                                           size_tolerance=SIZE_TOL, rng=random.Random(SEED_BASE + 1))
noliq_long = lr.sample_no_liquidation_windows(long_all, events, "binance_cm", span_start, span_end,
                                               rng=random.Random(SEED_BASE + 2), max_attempts=MAX_ATTEMPTS)
noliq_short = lr.sample_no_liquidation_windows(short_all, events, "binance_cm", span_start, span_end,
                                                rng=random.Random(SEED_BASE + 3), max_attempts=MAX_ATTEMPTS)
t_controls = time.time() - t0
log_(f"controls built: placebo_long={len(placebo_long)} placebo_short={len(placebo_short)} "
     f"noliq_long={len(noliq_long)} noliq_short={len(noliq_short)} time={t_controls:.1f}s "
     f"(seeds {SEED_BASE}..{SEED_BASE+3})")

# --------------------------------------------------------------------- #
# 4. 反応窓の計算(先読み防止の compute_reactions を通す)
# --------------------------------------------------------------------- #
t0 = time.time()
groups = {
    "real_long": long_all,
    "real_short": short_all,
    "real_mixed": mixed_all,
    "placebo_long": placebo_long,
    "placebo_short": placebo_short,
    "noliq_long": noliq_long,
    "noliq_short": noliq_short,
}
rows_by_group: dict[str, list[dict]] = {}
for name, cascades in groups.items():
    rows_by_group[name] = lr.compute_reactions(
        cascades, prices, horizons_min=HORIZONS,
        anchor_max_staleness_ms=STALENESS_MS, future_max_staleness_ms=STALENESS_MS,
    )
t_react = time.time() - t0
log_(f"reactions computed: time={t_react:.1f}s")

# 内部方向(カスケード/窓の開始→終了の価格変化の符号)を全群に一律に付与
for name, rows in rows_by_group.items():
    for r in rows:
        start_anchor = prices.at_or_before(r["start_ms"], STALENESS_MS)
        end_price = r["anchor_price"]
        if start_anchor is None or end_price != end_price:  # NaN check
            r["internal_bp"] = float("nan")
        else:
            sp = start_anchor[1]
            r["internal_bp"] = (end_price - sp) / sp * 10_000.0 if sp else float("nan")

# --------------------------------------------------------------------- #
# 5. CSV 出力(1行=1カスケード/窓、群タグ付き)
# --------------------------------------------------------------------- #
extra_cols = ("group", "internal_bp")
all_rows = []
for name, rows in rows_by_group.items():
    for r in rows:
        r2 = dict(r)
        r2["group"] = name
        all_rows.append(r2)
csv_path = OUT_DIR / "stage0_binance_cm_2024-06-13_2024-10-14.csv"
cols = list(lr.CSV_COLUMNS) + ["group", "internal_bp"]
with csv_path.open("w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=cols)
    w.writeheader()
    for r in all_rows:
        w.writerow({k: r.get(k, "") for k in cols})
log_(f"csv written: {csv_path} rows={len(all_rows)}")

# --------------------------------------------------------------------- #
# 6. 統計(ブートストラップ 10,000回、種固定)
# --------------------------------------------------------------------- #
BOOT_N = 10_000
BOOT_SEED = 20260913
rng_boot = np.random.default_rng(BOOT_SEED)


def arr(rows, key):
    return np.array([r[key] for r in rows], dtype=float)


def clean(a):
    return a[~np.isnan(a)]


def boot_diff_ci(a, b, n=BOOT_N, rng=rng_boot):
    """ベクトル化ブートストラップ: (n, len(a)) の添字行列を一括生成して平均を取る。"""
    a = clean(a)
    b = clean(b)
    if len(a) == 0 or len(b) == 0:
        return float("nan"), float("nan"), float("nan"), len(a), len(b)
    idx_a = rng.integers(0, len(a), size=(n, len(a)))
    idx_b = rng.integers(0, len(b), size=(n, len(b)))
    means_a = a[idx_a].mean(axis=1)
    means_b = b[idx_b].mean(axis=1)
    diffs = means_a - means_b
    point = a.mean() - b.mean()
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    return point, lo, hi, len(a), len(b)


MDE = {
    (1, "long"): 2.04, (1, "short"): 2.23,
    (5, "long"): 5.18, (5, "short"): 5.57,
    (15, "long"): 6.86, (15, "short"): 8.47,
    (60, "long"): 12.09, (60, "short"): 15.44,
}

results = []
for direction in ("long", "short"):
    real_rows = rows_by_group[f"real_{direction}"]
    placebo_rows = rows_by_group[f"placebo_{direction}"]
    noliq_rows = rows_by_group[f"noliq_{direction}"]
    real_size = arr(real_rows, "total_size")
    for h in HORIZONS:
        bp_col = f"bp_{h}m"
        real_bp = arr(real_rows, bp_col)
        placebo_bp = arr(placebo_rows, bp_col)
        noliq_bp = arr(noliq_rows, bp_col)

        real_size_clean_mask = ~np.isnan(real_bp) & (real_size > 0)
        real_bp_per_size = np.where(real_size > 0, real_bp / np.where(real_size == 0, np.nan, real_size), np.nan)
        placebo_size = arr(placebo_rows, "total_size")
        placebo_bp_per_size = np.where(placebo_size > 0, placebo_bp / np.where(placebo_size == 0, np.nan, placebo_size), np.nan)

        # 規模あたりのインパクト(主): 各行 bp/size、real vs placebo
        pt_sz, lo_sz, hi_sz, n_r_sz, n_p_sz = boot_diff_ci(real_bp_per_size, placebo_bp_per_size)
        # 平均bp(副): real vs placebo
        pt_bp, lo_bp, hi_bp, n_r_bp, n_p_bp = boot_diff_ci(real_bp, placebo_bp)
        # 転換: reversal_score = -sign(internal_bp) * bp_h
        def reversal(rows_):
            out = []
            for r in rows_:
                ib = r["internal_bp"]
                bp = r[bp_col]
                if ib != ib or bp != bp or ib == 0:
                    out.append(float("nan"))
                else:
                    out.append(-np.sign(ib) * bp)
            return np.array(out, dtype=float)
        real_rev = reversal(real_rows)
        placebo_rev = reversal(placebo_rows)
        pt_rev, lo_rev, hi_rev, n_r_rev, n_p_rev = boot_diff_ci(real_rev, placebo_rev)

        # 副の対照(無清算窓): 同じ3つ
        noliq_size_note = "no_liq total_size=0 (測定器の仕様。規模を持たない)"
        real_mean_size = np.nanmean(real_size[real_size > 0]) if (real_size > 0).any() else float("nan")
        real_bp_per_realmeansize = real_bp / real_mean_size if real_mean_size == real_mean_size and real_mean_size != 0 else np.full_like(real_bp, np.nan)
        noliq_bp_per_realmeansize = noliq_bp / real_mean_size if real_mean_size == real_mean_size and real_mean_size != 0 else np.full_like(noliq_bp, np.nan)
        pt_sz_nl, lo_sz_nl, hi_sz_nl, n_r_sz_nl, n_p_sz_nl = boot_diff_ci(real_bp_per_realmeansize, noliq_bp_per_realmeansize)
        pt_bp_nl, lo_bp_nl, hi_bp_nl, n_r_bp_nl, n_p_bp_nl = boot_diff_ci(real_bp, noliq_bp)
        noliq_rev = reversal(noliq_rows)
        pt_rev_nl, lo_rev_nl, hi_rev_nl, n_r_rev_nl, n_p_rev_nl = boot_diff_ci(real_rev, noliq_rev)

        mde = MDE[(h, direction)]
        judge_bp = "○" if (lo_bp >= -mde and hi_bp <= mde) else "×"
        judge_rev = "○" if (lo_rev >= -mde and hi_rev <= mde) else "×"

        n_nan_real = int(np.isnan(real_bp).sum())
        n_nan_placebo = int(np.isnan(placebo_bp).sum())
        n_nan_noliq = int(np.isnan(noliq_bp).sum())

        results.append(dict(
            direction=direction, horizon=h, mde=mde,
            n_real=len(real_rows), n_placebo=len(placebo_rows), n_noliq=len(noliq_rows),
            n_nan_real=n_nan_real, n_nan_placebo=n_nan_placebo, n_nan_noliq=n_nan_noliq,
            sz_point=pt_sz, sz_lo=lo_sz, sz_hi=hi_sz,
            bp_point=pt_bp, bp_lo=lo_bp, bp_hi=hi_bp, judge_bp=judge_bp,
            rev_point=pt_rev, rev_lo=lo_rev, rev_hi=hi_rev, judge_rev=judge_rev,
            nl_sz_point=pt_sz_nl, nl_sz_lo=lo_sz_nl, nl_sz_hi=hi_sz_nl,
            nl_bp_point=pt_bp_nl, nl_bp_lo=lo_bp_nl, nl_bp_hi=hi_bp_nl,
            nl_rev_point=pt_rev_nl, nl_rev_lo=lo_rev_nl, nl_rev_hi=hi_rev_nl,
        ))

stats_csv = OUT_DIR / "stage0_stats.csv"
stat_cols = list(results[0].keys())
with stats_csv.open("w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=stat_cols)
    w.writeheader()
    for r in results:
        w.writerow(r)
log_(f"stats csv written: {stats_csv} rows={len(results)}")

t_total = time.time() - t_start_all
log_(f"TOTAL TIME: {t_total:.1f}s")

# 画面表示用の要約表
print("\n=== summary ===")
for r in results:
    print(f"{r['direction']:5s} {r['horizon']:3d}min  n_real={r['n_real']:5d} n_pb={r['n_placebo']:4d} n_nl={r['n_noliq']:4d}  "
          f"bp diff={r['bp_point']:.3f} CI[{r['bp_lo']:.3f},{r['bp_hi']:.3f}] judge={r['judge_bp']}  "
          f"rev diff={r['rev_point']:.3f} CI[{r['rev_lo']:.3f},{r['rev_hi']:.3f}] judge={r['judge_rev']}  "
          f"sz diff={r['sz_point']:.6g} CI[{r['sz_lo']:.6g},{r['sz_hi']:.6g}]")

with open(OUT_DIR / "run_log.txt", "w", encoding="utf-8") as fh:
    fh.write("\n".join(log) + "\n")
