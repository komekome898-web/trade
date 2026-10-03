#!/usr/bin/env python3
"""カード 9 (a) の追加の計算(2026-10-03、関門 ② の監査「止める 1」「聞く 18」への対応)。

1. **対照 (iv)**: 対照 (ii)(材料 15 = m10÷m60 と材料 9 = 向き×5 秒の成行の偏り の 10 分位の帯が同じ)に、
   **直前の値動きの大きさ |m10|・|m60| の 10 分位の帯**も同じであることを足した時刻。
   候補(10 秒刻み・前後 15 分に清算無し・材料が有限 = `liq_cascade_v2.grid_candidates`)、日のずれの順
   (0, −1, +1, −2, +2, −3, +3 = `CTRL2_DAY_OFFSETS`)、置換なし、距離 |Δ材料15| + |Δ材料9| の最小、
   直前の状態の作り方(`pre_state_arrays`、t − 1 ms 以前の約定)は (ii) と同じ。
   (ii) と違う点は 2 つだけ:
   - 帯に |m10|・|m60| を足した(`match_across_days` は帯を 2 つしか受け取らないので、同じ規則を
     帯 4 つで書いた `match_iv`。中身は `control_matched` と同じ順と同じ距離)。
   - **清算の zip が無い日の候補を使わない**(その日は「前後 15 分に清算無し」を確かめられない。
     監査の直す 10)。(ii) はこの日の候補も使っていた。
   帯の境は、この走らせのプリント全体から作る((ii) の材料 15・9 の境は `run_meta.json` の値をそのまま使う)。
   値動き(react・mfe・mae・giveback・mfe_minus_react)は `reactions_from_anchor` で約定の生データから計算する。
2. **(ii) の再現**: 同じ処理で (ii) の選び方(`match_across_days`)も流し、`controls.csv.gz` の (ii) の時刻と
   一致するかを数える(この台本の読み方が走らせと同じであることの確かめ)。
3. **起点を清算の約定より後にした react**(聞く 18):
   - 版 A = 走らせと同じ起点(ts 以後の最初の約定)。`anchors_prints.csv.gz` の react と一致するかの確かめ用。
   - 版 B = 版 A の約定の時刻より**厳密に後**の最初の約定。
   - 版 C = ts + 1 秒 以後の最初の約定(状態機械の遅れ 1 秒と同じ入りの時刻)。
   react の h は 12 本全部。react の作り方(穴 300 秒、h 以前の最後の約定)は `reactions_from_anchor` と同じ。

読むもの: `backtest_data/binance_cm_o3c_20260913/`(約定・清算の生データ)、
`data/c9_run_a/full_20230625_20241014/` の `anchors_prints.csv.gz`・`controls.csv.gz`・`run_meta.json`。
書くもの: `--out`(既定 `run_a/control_iv_out/`)の下だけ。既存の scripts/・src/ は変えない(import するだけ)。
ネットワークは使わない。Jev は呼ばない。判定はしない。

    PYTHONPATH=src python3 docs/RESEARCH/cards/c9_liquidation_cascade/run_a/control_iv.py
    (試し: --end 2023-06-27 --out <別の置き場>)
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import date, timedelta
from pathlib import Path
import sys

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
sys.path.insert(0, str(REPO / "src"))
from bot.research import liq_cascade_v2 as v2  # noqa: E402

RUN = REPO / "data" / "c9_run_a" / "full_20230625_20241014"
BACK_DAYS, FWD_DAYS, PRINT_MARGIN_DAYS = 4, 11, 4      # scripts/c9_run_a.py と同じ
MAT15, MAT9 = v2.MAT_COL[15], v2.MAT_COL[9]


def shift(day: str, k: int) -> str:
    return (date.fromisoformat(day) + timedelta(days=k)).isoformat()


def window_days(day: str, back: int, fwd: int) -> list[str]:
    return [shift(day, k) for k in range(-back, fwd + 1)]


def liq_zip_exists(data_root: Path, day: str) -> bool:
    return (data_root / "liquidationSnapshot" / v2.SYMBOL /
            f"{v2.SYMBOL}-liquidationSnapshot-{day}.zip").exists()


def match_iv(tv: dict, cands_by_offset: dict, cuts: dict) -> tuple[np.ndarray, np.ndarray]:
    """(ii) の `match_across_days` + `control_matched` と同じ順・同じ距離で、帯を 4 つ
    (材料 15・材料 9・|m10|・|m60|)にしたもの。戻り値 = (日のずれ, 候補の添字)。取れなければ (99, −1)。"""
    keys = ("m15", "m9", "a10", "a60")
    tb = {k: v2.band_of(tv[k], cuts[k]) for k in keys}
    n = tv["m15"].size
    off = np.full(n, 99, dtype=np.int64)
    pick = np.full(n, -1, dtype=np.int64)
    for o in v2.CTRL2_DAY_OFFSETS:
        c = cands_by_offset.get(o)
        if c is None or c["t"].size == 0:
            continue
        if "_b" not in c:
            c["_b"] = {k: v2.band_of(c[k], cuts[k]) for k in keys}
        cb = c["_b"]
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


def react_only(tr: v2.Trades, anchor_ms: np.ndarray, direction: np.ndarray) -> dict:
    """`reactions_from_anchor` の react と同じ規則(t₀ = anchor 以後の最初の約定、p(t₀+h) = t₀+h 以前の最後、
    穴 300 秒)で react だけを返す(最大順行などの走査をしない)。"""
    a = np.asarray(anchor_ms, dtype=np.int64)
    sg = np.asarray(direction, dtype=float)
    i0, ok0 = v2.idx_at_or_after(tr.times, a)
    ok0 &= np.isfinite(sg)
    t0 = np.where(ok0, tr.times[i0] if tr.times.size else -1, -1).astype(np.int64)
    p0 = np.where(ok0, tr.prices[i0] if tr.times.size else np.nan, np.nan)
    out = {"t0_ms": t0, "p0": p0}
    for h in v2.HORIZONS_S:
        ie, oke = v2.idx_at_or_before(tr.times, t0 + h * v2.MS_S)
        px = np.where(oke & ok0, tr.prices[ie] if tr.times.size else np.nan, np.nan)
        with np.errstate(invalid="ignore", divide="ignore"):
            out[f"react_{h}"] = sg * (px - p0) / p0 * 1e4
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--start", default="2023-06-25")
    ap.add_argument("--end", default="2024-10-14")
    ap.add_argument("--run", default=str(RUN))
    ap.add_argument("--data-root", default=str(v2.DEFAULT_DATA_ROOT))
    ap.add_argument("--out", default=str(HERE / "control_iv_out"))
    a = ap.parse_args(argv)
    t_all = time.time()
    run, data_root, out = Path(a.run), Path(a.data_root), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    meta_run = json.loads((run / "run_meta.json").read_text(encoding="utf-8"))
    start, end = date.fromisoformat(a.start), date.fromisoformat(a.end)
    days = v2.day_range(start, end)
    run_days = v2.day_range(date.fromisoformat(meta_run["期間"][0]), date.fromisoformat(meta_run["期間"][1]))

    # 清算(走らせと同じ範囲を読む: 走らせの期間 ± 4 日)
    pr = v2.load_prints(data_root, date.fromisoformat(run_days[0]) - timedelta(days=PRINT_MARGIN_DAYS),
                        date.fromisoformat(run_days[-1]) + timedelta(days=PRINT_MARGIN_DAYS))
    liq_ts = pr.ts.copy()
    no_zip = {d for d in window_days(run_days[0], 3, len(run_days) + 2) if not liq_zip_exists(data_root, d)}

    cols = ["print_id", "day", "ts_ms", "sign", "m10_signed", "m60_signed", MAT15, MAT9, "t0_ms"] + \
        [f"react_{h}" for h in v2.HORIZONS_S]
    P = pd.read_csv(run / "anchors_prints.csv.gz", usecols=cols, dtype={"day": str, "print_id": str})
    idx_of = {pid: i for i, pid in enumerate(pr.print_id.tolist())}
    pi = np.array([idx_of[x] for x in P["print_id"]], dtype=np.int64)
    assert np.array_equal(pr.ts[pi], P["ts_ms"].to_numpy(np.int64)), "print_id と時刻が走らせと合わない"
    P["a10"] = P["m10_signed"].abs()
    P["a60"] = P["m60_signed"].abs()
    cuts = {"m15": np.array(meta_run["対照(ii)の帯の境"]["mat15"]),
            "m9": np.array(meta_run["対照(ii)の帯の境"]["mat9"]),
            "a10": v2.decile_cuts(P["a10"].to_numpy(float)),
            "a60": v2.decile_cuts(P["a60"].to_numpy(float))}

    C = pd.read_csv(run / "controls.csv.gz", usecols=["kind", "anchor_ms", "ref_id"], dtype={"ref_id": str})
    ii_old = C[C["kind"] == "(ii)合わせた時刻"].set_index("ref_id")["anchor_ms"].to_dict()

    store = v2.TradeStore(data_root)
    cache_ii: dict = {}
    cache_iv: dict = {}
    iv_parts, ra_parts, ii_rep = [], [], []
    for day in days:
        t = time.time()
        tr, _miss = store.window(window_days(day, BACK_DAYS, FWD_DAYS))
        D = P[P["day"] == day]
        n = len(D)
        if n:
            # ---- 起点を変えた react ----
            sg = D["sign"].to_numpy(float)
            ts = D["ts_ms"].to_numpy(np.int64)
            rA = react_only(tr, ts, sg)
            rB = react_only(tr, rA["t0_ms"] + 1, sg)
            rC = react_only(tr, ts + 1000, sg)
            ra = {"print_id": D["print_id"].to_numpy(), "day": day, "ts_ms": ts,
                  "t0_A": rA["t0_ms"], "p0_A": rA["p0"], "t0_B": rB["t0_ms"], "p0_B": rB["p0"],
                  "t0_C": rC["t0_ms"], "p0_C": rC["p0"]}
            for h in v2.HORIZONS_S:
                ra[f"reactA_{h}"] = rA[f"react_{h}"]
                ra[f"reactB_{h}"] = rB[f"react_{h}"]
                ra[f"reactC_{h}"] = rC[f"react_{h}"]
            ra_parts.append(pd.DataFrame(ra))

        # ---- 候補(日ごと。(ii) の再現用と (iv) 用で「使った」の印を別に持つ) ----
        for o in v2.CTRL2_DAY_OFFSETS:
            d2 = shift(day, o)
            if d2 not in cache_ii:
                g = v2.grid_candidates(d2, tr, liq_ts)
                pre = v2.pre_state_arrays(tr, g["t"])
                g["a10"], g["a60"] = np.abs(pre["raw_m10"]), np.abs(pre["raw_m60"])
                cache_ii[d2] = g
                ok = np.ones(g["t"].size, bool) if d2 not in no_zip else np.zeros(g["t"].size, bool)
                cache_iv[d2] = {"t": g["t"][ok], "m15": g["mat15"][ok], "m9": g["mat9"][ok],
                                "a10": np.abs(pre["raw_m10"])[ok], "a60": np.abs(pre["raw_m60"])[ok],
                                "dir": g["dir"][ok], "used": np.zeros(int(ok.sum()), bool)}
        if n:
            t15 = D[MAT15].to_numpy(float)
            t9 = D[MAT9].to_numpy(float)
            # (ii) の再現
            c_ii = {o: cache_ii[shift(day, o)] for o in v2.CTRL2_DAY_OFFSETS}
            off2, pick2 = v2.match_across_days(t15, t9, c_ii, cuts["m15"], cuts["m9"])
            for pid, o, j in zip(D["print_id"], off2, pick2):
                new = int(c_ii[o]["t"][j]) if j >= 0 else None
                a10 = float(c_ii[o]["a10"][j]) if j >= 0 else np.nan
                a60 = float(c_ii[o]["a60"][j]) if j >= 0 else np.nan
                ii_rep.append((pid, day, new, ii_old.get(pid), a10, a60))
            # (iv)
            tv = {"m15": t15, "m9": t9, "a10": D["a10"].to_numpy(float), "a60": D["a60"].to_numpy(float)}
            c_iv = {o: cache_iv[shift(day, o)] for o in v2.CTRL2_DAY_OFFSETS}
            off4, pick4 = match_iv(tv, c_iv, cuts)
            got = pick4 >= 0
            if got.any():
                tt = np.array([c_iv[o]["t"][j] for o, j in zip(off4[got], pick4[got])], dtype=np.int64)
                dd = np.array([c_iv[o]["dir"][j] for o, j in zip(off4[got], pick4[got])], dtype=float)
                rx = v2.reactions_from_anchor(tr, tt, dd)
                row = {"kind": "(iv)大きさも合わせた時刻", "day": day, "anchor_ms": tt, "dir": dd,
                       "ref_id": D["print_id"].to_numpy()[got], "day_offset": off4[got]}
                for k in ("m15", "m9", "a10", "a60"):
                    row[f"cand_{k}"] = np.array([c_iv[o][k][j] for o, j in zip(off4[got], pick4[got])])
                    row[f"print_{k}"] = tv[k][got]
                row["t0_ms"], row["p0"] = rx["t0_ms"], rx["p0"]
                for h in v2.HORIZONS_S:
                    for k in v2.REACTION_KEYS:
                        row[f"{k}_{h}"] = rx[f"{k}_{h}"]
                iv_parts.append(pd.DataFrame(row))
        store.drop_before(shift(day, 1 - BACK_DAYS))
        for k in [k for k in cache_ii if k < shift(day, 1 - 3)]:
            del cache_ii[k]
            del cache_iv[k]
        print(f"[iv] {day} プリント {n} {time.time() - t:.1f}s 経過 {time.time() - t_all:.0f}s", flush=True)

    IV = pd.concat(iv_parts, ignore_index=True) if iv_parts else pd.DataFrame()
    RA = pd.concat(ra_parts, ignore_index=True)
    IV.to_csv(out / "controls_iv.csv.gz", index=False, float_format="%.8g")
    RA.to_csv(out / "prints_reanchor.csv.gz", index=False, float_format="%.8g")
    rep = pd.DataFrame(ii_rep, columns=["print_id", "day", "anchor_new", "anchor_run", "cand_a10", "cand_a60"])
    rep.to_csv(out / "ii_reproduction.csv.gz", index=False)

    # 確かめ: 版 A の react と走らせの react の一致
    M = RA.merge(P[["print_id"] + [f"react_{h}" for h in v2.HORIZONS_S]], on="print_id")
    chkA = {}
    for h in v2.HORIZONS_S:
        x, y = M[f"reactA_{h}"].to_numpy(float), M[f"react_{h}"].to_numpy(float)
        both = np.isfinite(x) & np.isfinite(y)
        chkA[str(h)] = {"両方有限": int(both.sum()), "片方だけNaN": int((np.isfinite(x) != np.isfinite(y)).sum()),
                        "最大の差_bp": float(np.max(np.abs(x[both] - y[both]))) if both.any() else None}
    same = rep["anchor_new"].notna() & rep["anchor_run"].notna() & (rep["anchor_new"] == rep["anchor_run"])
    meta = {
        "期間": [a.start, a.end], "日数": len(days), "プリント": int(len(RA)),
        "対照(iv)取れた": int(len(IV)),
        "対照(iv)日のずれ別": {str(o): int((IV["day_offset"] == o).sum()) for o in v2.CTRL2_DAY_OFFSETS} if len(IV) else {},
        "帯の境": {k: v.tolist() for k, v in cuts.items()},
        "清算のzipが無く候補から外した日": sorted(no_zip),
        "(ii)の再現": {"プリント": int(len(rep)),
                     "走らせで取れた": int(rep["anchor_run"].notna().sum()),
                     "この台本で取れた": int(rep["anchor_new"].notna().sum()),
                     "両方で取れて時刻が同じ": int(same.sum()),
                     "両方で取れて時刻が違う": int((rep["anchor_new"].notna() & rep["anchor_run"].notna() & ~same).sum()),
                     "片方だけ取れた": int((rep["anchor_new"].notna() != rep["anchor_run"].notna()).sum())},
        "版Aのreactと走らせのreactの一致": chkA,
        "所要_秒": round(time.time() - t_all, 1),
        "注": "測り直しではなく、走らせの出力と同じ生データからの追加の計算。Jev は呼んでいない。",
    }
    (out / "control_iv_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    print(json.dumps({k: meta[k] for k in ("対照(iv)取れた", "(ii)の再現", "所要_秒")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
