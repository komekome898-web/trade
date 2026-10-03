#!/usr/bin/env python3
"""カード 9 (a) の追加の計算 その 3(2026-10-03、関門 ② の 3 回目の監査「止める 3」「直す 9」「直す 14」への対応)。

1. **対照 (iv) の日の幅を変えた 2 版**: (iv) と同じ帯 4 つ(材料 15・材料 9・|m10|・|m60| の 10 分位)・同じ候補の条件
   (10 秒格子・前後 15 分に清算無し・材料が有限・清算の zip のある日)・置換なし・同じ距離で、探す日だけを変える。
   - `d0` = 同じ日だけ(日のずれ 0)。代替の記録の回答者 A・B が「日(同じ日の中から選ぶ)」を合わせる変数に置いたため。
   - `d7` = 0, −1, +1, …, −7, +7 日の順に探す(±3 日の (iv) を広げた版)。
   値動き(react・mfe・mae・giveback・mfe_minus_react、h 12 本)は `reactions_from_anchor` で約定の生データから計算する。
2. **帯ごとの無清算の割合**: 走らせの全日(各日 1 回)の 10 秒格子のうち材料が有限な時刻を、|m10| の帯(10 分位、(iv) の境)
   ごとに数え、「前後 15 分に清算無し」を満たす割合を出す。
3. **(iv-h) が取れなかった原因**: (iv-h) が取れなかったプリントごとに、±3 日の格子で帯 5 つ(4 つ + UTC の時)が同じ時刻を、
   清算の条件なし / 前後 15 分に清算無し / それに zip のある日、で数える((iv) の原因の数え方と同じ)。

読むもの: `backtest_data/binance_cm_o3c_20260913/`、`data/c9_run_a/full_20230625_20241014/` の `anchors_prints.csv.gz`・
`run_meta.json`、`run_a/control_iv_out/control_iv_meta.json`、`run_a/control_ivh_out/controls_ivh.csv.gz`。
書くもの: `--out`(既定 `run_a/control_iv_days_out/`)だけ。既存の scripts/・src/ は変えない。ネットワークを使わない。

    PYTHONPATH=src python3 docs/RESEARCH/cards/c9_liquidation_cascade/run_a/control_iv_days.py
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(HERE))
from bot.research import liq_cascade_v2 as v2  # noqa: E402
import control_iv as civ  # noqa: E402
import control_ivh as cih  # noqa: E402

KEYS4 = ("m15", "m9", "a10", "a60")
KEYS5 = KEYS4 + ("hour",)
VARIANTS = {"d0": (0,), "d7": tuple([0] + [s * k for k in range(1, 8) for s in (-1, 1)])}
BACK, FWD = 8, 15   # ±7 日の候補の直前の状態 + 1 週の h


def match_gen(tv: dict, cands_by_offset: dict, cuts: dict, keys, offsets):
    """`control_iv.match_iv` と同じ順・同じ距離。探す日のずれの列 `offsets` だけを引数にした。"""
    tb = {k: v2.band_of(tv[k], cuts[k]) for k in keys}
    n = tv["m15"].size
    off = np.full(n, 99, dtype=np.int64)
    pick = np.full(n, -1, dtype=np.int64)
    for o in offsets:
        c = cands_by_offset.get(o)
        if c is None or c["t"].size == 0:
            continue
        cb = c["_b4"]
        for r in range(n):
            if pick[r] >= 0 or any(tb[k][r] < 0 for k in keys):
                continue
            m = ~c["used"]
            for k in keys:
                m &= cb[k] == tb[k][r]
            idx = np.flatnonzero(m)
            if idx.size == 0:
                continue
            dist = np.abs(c["m15"][idx] - tv["m15"][r]) + np.abs(c["m9"][idx] - tv["m9"][r])
            j = int(idx[int(np.argmin(dist))])
            c["used"][j] = True
            pick[r], off[r] = j, o
    return off, pick


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--start", default="2023-06-25")
    ap.add_argument("--end", default="2024-10-14")
    ap.add_argument("--run", default=str(civ.RUN))
    ap.add_argument("--iv", default=str(HERE / "control_iv_out"))
    ap.add_argument("--ivh", default=str(HERE / "control_ivh_out"))
    ap.add_argument("--data-root", default=str(v2.DEFAULT_DATA_ROOT))
    ap.add_argument("--out", default=str(HERE / "control_iv_days_out"))
    a = ap.parse_args(argv)
    t_all = time.time()
    run, data_root, out = Path(a.run), Path(a.data_root), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    meta_run = json.loads((run / "run_meta.json").read_text(encoding="utf-8"))
    ivm = json.loads((Path(a.iv) / "control_iv_meta.json").read_text(encoding="utf-8"))
    days = v2.day_range(date.fromisoformat(a.start), date.fromisoformat(a.end))
    run_days = v2.day_range(date.fromisoformat(meta_run["期間"][0]), date.fromisoformat(meta_run["期間"][1]))
    pr = v2.load_prints(data_root, date.fromisoformat(run_days[0]) - timedelta(days=civ.PRINT_MARGIN_DAYS),
                        date.fromisoformat(run_days[-1]) + timedelta(days=civ.PRINT_MARGIN_DAYS))
    liq_ts = pr.ts.copy()
    no_zip = {d for d in civ.window_days(run_days[0], 8, len(run_days) + 8) if not civ.liq_zip_exists(data_root, d)}

    cols = ["print_id", "day", "ts_ms", "sign", "m10_signed", "m60_signed", civ.MAT15, civ.MAT9]
    P = pd.read_csv(run / "anchors_prints.csv.gz", usecols=cols, dtype={"day": str, "print_id": str})
    P["a10"], P["a60"] = P["m10_signed"].abs(), P["m60_signed"].abs()
    P["hour"] = pd.to_datetime(P["ts_ms"], unit="ms", utc=True).dt.hour
    cuts = {k: np.array(v) for k, v in ivm["帯の境"].items()}
    cuts5 = dict(cuts) | {"hour": np.arange(1, 24, dtype=float)}
    pb = {"m15": v2.band_of(P[civ.MAT15].to_numpy(float), cuts["m15"]),
          "m9": v2.band_of(P[civ.MAT9].to_numpy(float), cuts["m9"]),
          "a10": v2.band_of(P["a10"].to_numpy(float), cuts["a10"]),
          "a60": v2.band_of(P["a60"].to_numpy(float), cuts["a60"]),
          "hour": P["hour"].to_numpy(np.int64)}
    P["code5"] = cih.band_code(pb, KEYS5)
    ivh_got = set(pd.read_csv(Path(a.ivh) / "controls_ivh.csv.gz", usecols=["ref_id"], dtype={"ref_id": str})["ref_id"])

    store = v2.TradeStore(data_root)
    caches = {k: {} for k in VARIANTS}
    grid_stats: dict = {}
    parts = {k: [] for k in VARIANTS}
    cause5 = []
    for day in days:
        t = time.time()
        tr, _miss = store.window(civ.window_days(day, BACK, FWD))
        for o in range(-7, 8):
            d2 = civ.shift(day, o)
            if d2 in caches["d7"]:
                continue
            d0 = v2.day_start_ms(d2)
            grid = d0 + np.arange(v2.MS_DAY // v2.CTRL_GRID_MS, dtype=np.int64) * v2.CTRL_GRID_MS
            pre = v2.pre_state_arrays(tr, grid)
            fin = np.isfinite(pre["mat15"]) & np.isfinite(pre["mat9"])
            b = {"m15": v2.band_of(pre["mat15"], cuts["m15"]), "m9": v2.band_of(pre["mat9"], cuts["m9"]),
                 "a10": v2.band_of(np.abs(pre["raw_m10"]), cuts["a10"]),
                 "a60": v2.band_of(np.abs(pre["raw_m60"]), cuts["a60"]),
                 "hour": ((grid - d0) // 3_600_000).astype(np.int64)}
            noliq = v2.no_liq_mask(grid, liq_ts, v2.CTRL2_NO_LIQ_MS)
            cand = fin & noliq & (d2 not in no_zip)
            code5 = cih.band_code(b, KEYS5)
            entry = {"n_all5": Counter(code5[fin & (code5 >= 0)].tolist()),
                     "n_noliq5": Counter(code5[fin & noliq & (code5 >= 0)].tolist()),
                     "n_cand5": Counter(code5[cand & (code5 >= 0)].tolist())}
            if d2 in set(run_days) and d2 not in grid_stats:
                bb = b["a10"]
                grid_stats[d2] = {int(k): (int(((bb == k) & fin).sum()), int(((bb == k) & fin & noliq).sum()))
                                  for k in range(10)}
            for var in VARIANTS:
                caches[var][d2] = {"t": grid[cand], "m15": pre["mat15"][cand], "m9": pre["mat9"][cand],
                                   "a10": np.abs(pre["raw_m10"])[cand], "a60": np.abs(pre["raw_m60"])[cand],
                                   "dir": pre["dir10"][cand], "used": np.zeros(int(cand.sum()), bool),
                                   "_b4": {k: b[k][cand] for k in KEYS4}} | entry
        D = P[P["day"] == day]
        if len(D):
            tv = {k: D[k].to_numpy(float) for k in ("a10", "a60", "hour")} | \
                {"m15": D[civ.MAT15].to_numpy(float), "m9": D[civ.MAT9].to_numpy(float)}
            for var, offs in VARIANTS.items():
                cb = {o: caches[var][civ.shift(day, o)] for o in offs}
                off, pick = match_gen(tv, cb, cuts, KEYS4, offs)
                got = pick >= 0
                if not got.any():
                    continue
                tt = np.array([cb[o]["t"][j] for o, j in zip(off[got], pick[got])], dtype=np.int64)
                dd = np.array([cb[o]["dir"][j] for o, j in zip(off[got], pick[got])], dtype=float)
                rx = v2.reactions_from_anchor(tr, tt, dd)
                row = {"kind": f"(iv)_{var}", "day": day, "anchor_ms": tt, "dir": dd,
                       "ref_id": D["print_id"].to_numpy()[got], "day_offset": off[got]}
                for k in ("a10", "a60"):
                    row[f"cand_{k}"] = np.array([cb[o][k][j] for o, j in zip(off[got], pick[got])])
                    row[f"print_{k}"] = tv[k][got]
                row["t0_ms"], row["p0"] = rx["t0_ms"], rx["p0"]
                for h in v2.HORIZONS_S:
                    for k in v2.REACTION_KEYS:
                        row[f"{k}_{h}"] = rx[f"{k}_{h}"]
                parts[var].append(pd.DataFrame(row))
            for pid, c5 in zip(D["print_id"], D["code5"]):
                if pid in ivh_got:
                    continue
                n_all = n_noliq = n_cand = 0
                if c5 >= 0:
                    for o in v2.CTRL2_DAY_OFFSETS:
                        c = caches["d7"][civ.shift(day, o)]
                        n_all += c["n_all5"].get(int(c5), 0)
                        n_noliq += c["n_noliq5"].get(int(c5), 0)
                        n_cand += c["n_cand5"].get(int(c5), 0)
                cause5.append((pid, day, int(c5 < 0), n_all, n_noliq, n_cand))
        store.drop_before(civ.shift(day, 1 - BACK))
        for var in VARIANTS:
            for k in [k for k in caches[var] if k < civ.shift(day, 1 - 7)]:
                del caches[var][k]
        print(f"[days] {day} プリント {len(D)} {time.time() - t:.1f}s 経過 {time.time() - t_all:.0f}s", flush=True)

    meta = {"期間": [a.start, a.end], "所要_秒": None, "取れた": {}}
    for var in VARIANTS:
        df = pd.concat(parts[var], ignore_index=True)
        df.to_csv(out / f"controls_iv_{var}.csv.gz", index=False, float_format="%.8g")
        meta["取れた"][var] = int(len(df))
    gs = []
    for k in range(10):
        n_f = sum(v[k][0] for v in grid_stats.values())
        n_n = sum(v[k][1] for v in grid_stats.values())
        gs.append({"a10_band": k + 1, "格子の時刻(材料が有限)": n_f, "うち前後15分に清算無し": n_n,
                   "無清算の割合": n_n / n_f if n_f else np.nan})
    pd.DataFrame(gs).to_csv(out / "grid_band_noliq.csv", index=False, float_format="%.8g")
    pd.DataFrame(cause5, columns=["print_id", "day", "帯が欠け", "n_all_pm3", "n_noliq_pm3", "n_cand_pm3"]).to_csv(
        out / "ivh_unmatched_cause.csv.gz", index=False)
    meta["格子の日数"] = len(grid_stats)
    meta["(iv-h)の取れなかったプリント"] = len(cause5)
    meta["所要_秒"] = round(time.time() - t_all, 1)
    meta["注"] = "走らせ直しではなく、走らせと同じ生データからの追加の計算。Jev は呼んでいない。"
    (out / "control_iv_days_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    print(json.dumps(meta, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
