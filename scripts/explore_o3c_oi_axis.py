#!/usr/bin/env python3
"""探索スクリプト(O-3c)。建玉の減少が『清算 vs プラセボ』の分離軸になるかを、
時刻ずれ 0..±14h の29通りで走査する。探索区間のみ使用。判定はしない。
測定器(liq_response.py / liq_bands.py)は書き直さず、そのまま呼び出す。
"""
from __future__ import annotations
import bisect, csv, random, sys, time, zipfile
from datetime import date
from pathlib import Path
sys.path.insert(0, "/home/user/trade/src")
import numpy as np
from bot.research import liq_response as lr
from bot.research import liq_bands as lb

ROOT = Path("/home/user/trade/backtest_data/binance_cm_o3c_20260913")

CHUNKS = [
    (date(2023,6,25), date(2023,9,8)),
    (date(2023,9,10), date(2023,9,22)),
    (date(2023,9,24), date(2023,9,24)),
    (date(2023,9,26), date(2023,11,18)),
    (date(2023,11,20), date(2024,3,3)),
    (date(2024,6,9), date(2024,6,10)),
]

GAP_MS = 60_000
SIZE_TOL = 0.25
STALENESS_MS = 300_000
HORIZONS = (1, 5, 15, 60)
OI_TOL_MS = 900_000  # OIの前後値探索の許容(15分)
OFFSETS_H = list(range(-14, 15))
SEED_BASE = 20260913

t_all = time.time()
log_lines = []
def log(msg):
    print(msg, flush=True)
    log_lines.append(msg)


def build_1min_bars(root_agg, start, end):
    price_bars, vol_bars = [], []
    cur_minute = None; cur_vol = 0.0; cur_close = None
    n_rows = 0; n_files = 0
    for zpath in sorted(root_agg.glob("*-aggTrades-*.zip")):
        day = date.fromisoformat("-".join(zpath.stem.rsplit("-", 3)[1:]))
        if day < start or day > end:
            continue
        n_files += 1
        with zipfile.ZipFile(zpath) as zf:
            names = [n for n in zf.namelist() if n.endswith(".csv")]
            with zf.open(names[0]) as fh:
                reader = csv.reader((line.decode("utf-8") for line in fh))
                header = next(reader, None)
                assert header[0] == "agg_trade_id", (zpath, header)
                for row in reader:
                    if not row:
                        continue
                    _id, price_s, qty_s, _f, _l, ts_s, _ibm = row[:7]
                    ts = int(ts_s); price = float(price_s); qty = float(qty_s)
                    n_rows += 1
                    minute = ts - (ts % 60_000)
                    if cur_minute is None:
                        cur_minute = minute
                    if minute != cur_minute:
                        price_bars.append((cur_minute, cur_close))
                        vol_bars.append((cur_minute, cur_minute + 60_000, cur_vol))
                        cur_minute = minute; cur_vol = 0.0
                    cur_vol += qty; cur_close = price
    if cur_minute is not None:
        price_bars.append((cur_minute, cur_close))
        vol_bars.append((cur_minute, cur_minute + 60_000, cur_vol))
    return price_bars, vol_bars, n_files, n_rows


def at_or_after(ts_list, val_list, target_ms, tol_ms):
    i = bisect.bisect_left(ts_list, target_ms)
    if i >= len(ts_list):
        return None
    found_ts = ts_list[i]
    if found_ts - target_ms > tol_ms:
        return None
    return found_ts, val_list[i]


def at_or_before(ts_list, val_list, target_ms, tol_ms):
    i = bisect.bisect_right(ts_list, target_ms) - 1
    if i < 0:
        return None
    found_ts = ts_list[i]
    if target_ms - found_ts > tol_ms:
        return None
    return found_ts, val_list[i]


all_real_rows = []   # dict per real cascade: chunk, cascade_id, start_ms, end_ms, reactions..
all_placebo_rows = []
oi_by_chunk = []  # (ts_list, val_list) per chunk, for later offset scans
window_by_chunk = []  # (real_list[(id,start,end)], placebo_list[(id,start,end)]) per chunk

n_chunk_missing_oi_cov = 0

for ci, (start, end) in enumerate(CHUNKS):
    t0 = time.time()
    events = lr.load_binance_cm_liquidations(ROOT / "liquidationSnapshot" / "BTCUSD_PERP", start, end)
    real_cascades = lr.build_cascades(events, "binance_cm", gap_ms=GAP_MS)
    t_liq = time.time() - t0

    t0 = time.time()
    price_bars, vol_bars, n_files, n_rows = build_1min_bars(ROOT / "aggTrades" / "BTCUSD_PERP", start, end)
    t_bars = time.time() - t0

    t0 = time.time()
    placebos = lr.sample_placebo_windows(
        real_cascades, vol_bars, events, "binance_cm",
        size_tolerance=SIZE_TOL, rng=random.Random(SEED_BASE + ci),
    )
    t_placebo = time.time() - t0

    prices = lr.PriceSeries.from_ohlc_bars([(ts, c, c, c, c) for ts, c in price_bars], ts_unit="ms")
    t0 = time.time()
    real_react = lr.compute_reactions(real_cascades, prices, horizons_min=HORIZONS,
                                       anchor_max_staleness_ms=STALENESS_MS, future_max_staleness_ms=STALENESS_MS)
    placebo_react = lr.compute_reactions(placebos, prices, horizons_min=HORIZONS,
                                          anchor_max_staleness_ms=STALENESS_MS, future_max_staleness_ms=STALENESS_MS)
    t_react = time.time() - t0

    oi_series, _ls = lb.load_binance_cm_metrics(ROOT / "metrics" / "BTCUSD_PERP", start, end)

    for r in real_react:
        r["chunk"] = ci
    for r in placebo_react:
        r["chunk"] = ci
    all_real_rows.extend(real_react)
    all_placebo_rows.extend(placebo_react)
    oi_by_chunk.append((oi_series.ts_ms, oi_series.price))

    log(f"chunk{ci} {start}..{end}: liq_events={len(events)} cascades={len(real_cascades)} "
        f"placebos={len(placebos)} oi_points={len(oi_series.ts_ms)} "
        f"agg_files={n_files} agg_rows={n_rows} bars={len(price_bars)} "
        f"t_liq={t_liq:.1f}s t_bars={t_bars:.1f}s t_placebo={t_placebo:.1f}s t_react={t_react:.1f}s")

log(f"total cascades(real)={len(all_real_rows)} placebo={len(all_placebo_rows)}")

import pickle
with open("/tmp/claude-0/-home-user-trade/fa7bf0d4-a5c4-55b7-991b-874b590e00a3/scratchpad/explore_cache.pkl", "wb") as f:
    pickle.dump({
        "all_real_rows": all_real_rows,
        "all_placebo_rows": all_placebo_rows,
        "oi_by_chunk": oi_by_chunk,
    }, f)
log("cache written")

# ---- 29通りのオフセットでOI変化を計算 ----
offset_table = []
per_offset_decreases = {}  # offset -> (real_list, placebo_list) of (chunk, cascade_id, decrease)
for off_h in OFFSETS_H:
    off_ms = off_h * 3_600_000
    real_dec = []
    placebo_dec = []
    for rows, sink in ((all_real_rows, real_dec), (all_placebo_rows, placebo_dec)):
        for r in rows:
            ts_list, val_list = oi_by_chunk[r["chunk"]]
            before = at_or_before(ts_list, val_list, r["start_ms"] + off_ms, OI_TOL_MS)
            after = at_or_after(ts_list, val_list, r["end_ms"] + off_ms, OI_TOL_MS)
            if before is None or after is None:
                dec = float("nan")
            else:
                dec = before[1] - after[1]  # 減少を正
            sink.append((r["chunk"], r["cascade_id"], dec))
    per_offset_decreases[off_h] = (real_dec, placebo_dec)
    real_arr = np.array([d for _, _, d in real_dec], dtype=float)
    pla_arr = np.array([d for _, _, d in placebo_dec], dtype=float)
    real_valid = real_arr[~np.isnan(real_arr)]
    pla_valid = pla_arr[~np.isnan(pla_arr)]
    med_real = float(np.median(real_valid)) if len(real_valid) else float("nan")
    med_pla = float(np.median(pla_valid)) if len(pla_valid) else float("nan")
    diff = med_real - med_pla
    offset_table.append({
        "offset_h": off_h, "n_real_valid": len(real_valid), "n_real_total": len(real_arr),
        "n_placebo_valid": len(pla_valid), "n_placebo_total": len(pla_arr),
        "median_real": med_real, "median_placebo": med_pla, "diff": diff,
    })

best = max(offset_table, key=lambda x: (x["diff"] if x["diff"] == x["diff"] else -1e18))
log(f"best offset by diff: {best}")

# 上位・下位も見ておく(離れた複数オフセットで同程度かの判断材料)
sorted_by_diff = sorted(offset_table, key=lambda x: (x["diff"] if x["diff"]==x["diff"] else -1e18), reverse=True)
log("top5 offsets by diff: " + str([(o["offset_h"], round(o["diff"],1)) for o in sorted_by_diff[:5]]))

# ---- 欠測率(offset=0時点、代表として) ----
real_dec0, placebo_dec0 = per_offset_decreases[0]
n_real_nan = sum(1 for _, _, d in real_dec0 if d != d)
n_placebo_nan = sum(1 for _, _, d in placebo_dec0 if d != d)
log(f"missing @offset0: real {n_real_nan}/{len(real_dec0)} ({100*n_real_nan/max(1,len(real_dec0)):.1f}%) "
    f"placebo {n_placebo_nan}/{len(placebo_dec0)} ({100*n_placebo_nan/max(1,len(placebo_dec0)):.1f}%)")

# ---- 確認A・Bを最良オフセットで ----
best_off = best["offset_h"]
real_dec_best, placebo_dec_best = per_offset_decreases[best_off]
real_arr = np.array([d for _, _, d in real_dec_best], dtype=float)
pla_arr = np.array([d for _, _, d in placebo_dec_best], dtype=float)
real_valid = real_arr[~np.isnan(real_arr)]
pla_valid = pla_arr[~np.isnan(pla_arr)]

def q(a, p):
    return float(np.percentile(a, p)) if len(a) else float("nan")

confA = {
    "real": {"n": len(real_valid), "median": float(np.median(real_valid)) if len(real_valid) else float("nan"),
             "q25": q(real_valid,25), "q75": q(real_valid,75)},
    "placebo": {"n": len(pla_valid), "median": float(np.median(pla_valid)) if len(pla_valid) else float("nan"),
                "q25": q(pla_valid,25), "q75": q(pla_valid,75)},
}
log(f"confA @best_offset={best_off}h: real n={confA['real']['n']} median={confA['real']['median']:.1f} "
    f"IQR=[{confA['real']['q25']:.1f},{confA['real']['q75']:.1f}] | "
    f"placebo n={confA['placebo']['n']} median={confA['placebo']['median']:.1f} "
    f"IQR=[{confA['placebo']['q25']:.1f},{confA['placebo']['q75']:.1f}]")

# 確認B: プラセボをOI減少量で3層化 → 層ごとに反応窓bp平均
placebo_dec_map = {}
for chunk, cid, dec in placebo_dec_best:
    placebo_dec_map[(chunk, cid)] = dec

placebo_valid_ids = [(chunk, cid) for chunk, cid, dec in placebo_dec_best if dec == dec]
placebo_valid_decs = np.array([placebo_dec_map[k] for k in placebo_valid_ids])
order = np.argsort(placebo_valid_decs)
n = len(order)
t1 = n // 3
t2 = 2 * n // 3
tier_low_ids = set(placebo_valid_ids[i] for i in order[:t1])       # 増えた(decが小さい/負)
tier_mid_ids = set(placebo_valid_ids[i] for i in order[t1:t2])     # 変わらない
tier_high_ids = set(placebo_valid_ids[i] for i in order[t2:])      # 大きく減った

placebo_react_by_id = {(r["chunk"], r["cascade_id"]): r for r in all_placebo_rows}
real_react_all = all_real_rows

def mean_bp(rows, horizons=HORIZONS):
    out = {}
    for h in horizons:
        vals = np.array([r[f"bp_{h}m"] for r in rows], dtype=float)
        vals = vals[~np.isnan(vals)]
        out[h] = float(np.mean(vals)) if len(vals) else float("nan")
    return out

confB = {
    "real": mean_bp(real_react_all),
    "placebo_high_decrease": mean_bp([placebo_react_by_id[k] for k in tier_high_ids]),
    "placebo_mid": mean_bp([placebo_react_by_id[k] for k in tier_mid_ids]),
    "placebo_low(increase)": mean_bp([placebo_react_by_id[k] for k in tier_low_ids]),
}
log(f"confB tiers n: high={len(tier_high_ids)} mid={len(tier_mid_ids)} low={len(tier_low_ids)}")
for k, v in confB.items():
    log(f"confB {k}: " + " ".join(f"{h}m={v[h]:.2f}bp" for h in HORIZONS))

# ---- 出力をファイルに保存(表作成用) ----
import json
out = {
    "offset_table": offset_table,
    "best_offset": best_off,
    "top5": [(o["offset_h"], o["diff"]) for o in sorted_by_diff[:5]],
    "missing_at_offset0": {
        "real_nan": n_real_nan, "real_total": len(real_dec0),
        "placebo_nan": n_placebo_nan, "placebo_total": len(placebo_dec0),
    },
    "confA": confA,
    "confB": confB,
    "n_real_total": len(all_real_rows),
    "n_placebo_total": len(all_placebo_rows),
}
with open("/tmp/claude-0/-home-user-trade/fa7bf0d4-a5c4-55b7-991b-874b590e00a3/scratchpad/explore_oi_axis_result.json", "w") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

log(f"TOTAL TIME: {time.time()-t_all:.1f}s")
with open("/tmp/claude-0/-home-user-trade/fa7bf0d4-a5c4-55b7-991b-874b590e00a3/scratchpad/explore_oi_axis_log.txt", "w") as f:
    f.write("\n".join(log_lines))
