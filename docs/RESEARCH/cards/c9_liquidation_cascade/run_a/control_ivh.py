#!/usr/bin/env python3
"""カード 9 (a) の追加の計算 その 2(2026-10-03、関門 ② の 2 回目の監査「止める 2」「直す 7」への対応)。

1. **対照 (iv-h)**: 対照 (iv) の帯(材料 15・材料 9・|m10|・|m60| の 10 分位)に、**UTC の時(0〜23)**も同じで
   あることを足した時刻。候補・日のずれの順・置換なし・距離・清算の zip の無い日を外すことは (iv) と同じ
   (`control_iv.match_iv` に帯を 1 つ足しただけ)。値動きは `reactions_from_anchor` で約定の生データから計算する。
2. **起点の版を対照の側にも当てる**(止める 2 の (b)):
   - 版A = 起点の時刻以後の最初の約定(走らせと同じ。プリントは清算の時刻 ts、対照は格子の時刻)
   - 版B = 版A の約定より厳密に後の最初の約定
   - 版C = 起点の時刻 + 1 秒 以後の最初の約定
   - 版D = 起点の時刻以後の、**押した向きの成行(taker)**の最初の約定。プリントは清算の向き(SELL の清算 = 売りの
     成行 = `is_buyer_maker` が True)、対照は `dir`(直前 10 秒の変位の符号)の向き。清算の約定は清算の向きの
     成行なので、版D はプリントと対照に**同じ規則**で置ける起点。
   版B・C・D は react だけ(h 12 本)。プリントは全件、対照は (iv) と (iv-h) の全件。
3. **(iv) が取れなかった原因の切り分け**(直す 7): (iv) が取れなかったプリントごとに、±3 日の 10 秒格子のうち
   帯 4 つが同じ時刻の数を、(a) 清算の条件を掛けない全部の格子(材料が有限なもの)、(b) 「前後 15 分に清算無し」と
   「清算の zip がある日」の条件を掛けた候補、で数える。(a) が 0 = ±3 日に同じ帯の時刻が無い、(a) > 0 かつ (b) = 0 =
   清算の条件で消えた、(b) > 0 = 候補はあったが置換なしで先に使われた。

読むもの: `backtest_data/binance_cm_o3c_20260913/`、`data/c9_run_a/full_20230625_20241014/` の `anchors_prints.csv.gz`・
`run_meta.json`、`run_a/control_iv_out/controls_iv.csv.gz`。書くもの: `--out`(既定 `run_a/control_ivh_out/`)だけ。
既存の scripts/・src/ は変えない。ネットワークを使わない。Jev は呼ばない。判定はしない。

    PYTHONPATH=src python3 docs/RESEARCH/cards/c9_liquidation_cascade/run_a/control_ivh.py
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
import control_iv as civ  # noqa: E402  (同じ置き場の第 2 稿の台本。match_iv・react_only を使う)

RUN = civ.RUN
KEYS4 = ("m15", "m9", "a10", "a60")


def band_code(bands: dict, keys) -> np.ndarray:
    code = np.zeros(next(iter(bands.values())).size, dtype=np.int64)
    bad = np.zeros(code.size, dtype=bool)
    for k in keys:
        code = code * 100 + bands[k]
        bad |= bands[k] < 0
    return np.where(bad, -1, code)


def first_taker_idx(tr: v2.Trades, t_arr, direction) -> tuple[np.ndarray, np.ndarray]:
    """t 以後の、向き `direction`(−1 = 売りの成行 = maker True、+1 = 買いの成行)の最初の約定の添字。"""
    t = np.asarray(t_arr, dtype=np.int64)
    d = np.asarray(direction, dtype=float)
    out = np.zeros(t.size, dtype=np.int64)
    ok = np.zeros(t.size, dtype=bool)
    for sgn, mk in ((-1.0, True), (1.0, False)):
        sel = np.flatnonzero(d == sgn)
        if sel.size == 0:
            continue
        idx = np.flatnonzero(tr.maker == mk)
        if idx.size == 0:
            continue
        j = np.searchsorted(tr.times[idx], t[sel], side="left")
        has = j < idx.size
        jj = np.clip(j, 0, idx.size - 1)
        i0 = idx[jj]
        good = has & ((tr.times[i0] - t[sel]) <= v2.STALENESS_MS)
        out[sel] = i0
        ok[sel] = good
    return out, ok


def react_from_idx(tr: v2.Trades, i0, ok0, direction) -> dict:
    """起点の約定の添字 i0 から react_h(`react_only` と同じ規則)。"""
    sg = np.asarray(direction, dtype=float)
    ok0 = np.asarray(ok0, bool) & np.isfinite(sg)
    t0 = np.where(ok0, tr.times[i0] if tr.times.size else -1, -1).astype(np.int64)
    p0 = np.where(ok0, tr.prices[i0] if tr.times.size else np.nan, np.nan)
    out = {"t0_ms": t0, "p0": p0}
    for h in v2.HORIZONS_S:
        ie, oke = v2.idx_at_or_before(tr.times, t0 + h * v2.MS_S)
        px = np.where(oke & ok0, tr.prices[ie] if tr.times.size else np.nan, np.nan)
        with np.errstate(invalid="ignore", divide="ignore"):
            out[f"react_{h}"] = sg * (px - p0) / p0 * 1e4
    return out


def versions(tr, t, d) -> dict:
    """版 B・C・D の react(版A は呼び出し側にある)。"""
    a = civ.react_only(tr, t, d)
    out = {}
    rB = civ.react_only(tr, a["t0_ms"] + 1, d)
    rC = civ.react_only(tr, np.asarray(t, np.int64) + 1000, d)
    iD, okD = first_taker_idx(tr, t, d)
    rD = react_from_idx(tr, iD, okD, d)
    for v_, r in (("B", rB), ("C", rC), ("D", rD)):
        out[f"t0_{v_}"] = r["t0_ms"]
        out[f"p0_{v_}"] = r["p0"]
        for h in v2.HORIZONS_S:
            out[f"react{v_}_{h}"] = r[f"react_{h}"]
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--start", default="2023-06-25")
    ap.add_argument("--end", default="2024-10-14")
    ap.add_argument("--run", default=str(RUN))
    ap.add_argument("--iv", default=str(HERE / "control_iv_out"))
    ap.add_argument("--data-root", default=str(v2.DEFAULT_DATA_ROOT))
    ap.add_argument("--out", default=str(HERE / "control_ivh_out"))
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
    no_zip = {d for d in civ.window_days(run_days[0], 3, len(run_days) + 2) if not civ.liq_zip_exists(data_root, d)}
    assert sorted(no_zip) == sorted(ivm["清算のzipが無く候補から外した日"])

    cols = ["print_id", "day", "ts_ms", "sign", "m10_signed", "m60_signed", civ.MAT15, civ.MAT9]
    P = pd.read_csv(run / "anchors_prints.csv.gz", usecols=cols, dtype={"day": str, "print_id": str})
    P["a10"], P["a60"] = P["m10_signed"].abs(), P["m60_signed"].abs()
    P["hour"] = pd.to_datetime(P["ts_ms"], unit="ms", utc=True).dt.hour
    cuts = {k: np.array(v) for k, v in ivm["帯の境"].items()}
    IV = pd.read_csv(Path(a.iv) / "controls_iv.csv.gz", usecols=["ref_id", "anchor_ms", "dir"], dtype={"ref_id": str})
    iv_got = set(IV["ref_id"])
    pb = {"m15": v2.band_of(P[civ.MAT15].to_numpy(float), cuts["m15"]),
          "m9": v2.band_of(P[civ.MAT9].to_numpy(float), cuts["m9"]),
          "a10": v2.band_of(P["a10"].to_numpy(float), cuts["a10"]),
          "a60": v2.band_of(P["a60"].to_numpy(float), cuts["a60"])}
    P["code4"] = band_code(pb, KEYS4)

    store = v2.TradeStore(data_root)
    cache: dict = {}
    ivh_parts, pv_parts, ivv_parts, cause_rows = [], [], [], []
    IVd = {d: g for d, g in pd.read_csv(Path(a.iv) / "controls_iv.csv.gz", usecols=["ref_id", "day", "anchor_ms", "dir"],
                                         dtype={"ref_id": str, "day": str}).groupby("day")}
    for day in days:
        t = time.time()
        tr, _miss = store.window(civ.window_days(day, civ.BACK_DAYS, civ.FWD_DAYS))
        for o in v2.CTRL2_DAY_OFFSETS:
            d2 = civ.shift(day, o)
            if d2 in cache:
                continue
            d0 = v2.day_start_ms(d2)
            grid = d0 + np.arange(v2.MS_DAY // v2.CTRL_GRID_MS, dtype=np.int64) * v2.CTRL_GRID_MS
            pre = v2.pre_state_arrays(tr, grid)
            fin = np.isfinite(pre["mat15"]) & np.isfinite(pre["mat9"])
            b = {"m15": v2.band_of(pre["mat15"], cuts["m15"]), "m9": v2.band_of(pre["mat9"], cuts["m9"]),
                 "a10": v2.band_of(np.abs(pre["raw_m10"]), cuts["a10"]),
                 "a60": v2.band_of(np.abs(pre["raw_m60"]), cuts["a60"])}
            code = band_code(b, KEYS4)
            noliq = v2.no_liq_mask(grid, liq_ts, v2.CTRL2_NO_LIQ_MS)
            cand = fin & noliq & (d2 not in no_zip)
            hours = ((grid - d0) // 3_600_000).astype(np.int64)
            cache[d2] = {"n_all": Counter(code[fin & (code >= 0)].tolist()),
                         "n_noliq": Counter(code[fin & noliq & (code >= 0)].tolist()),
                         "n_cand": Counter(code[cand & (code >= 0)].tolist()),
                         "t": grid[cand], "m15": pre["mat15"][cand], "m9": pre["mat9"][cand],
                         "a10": np.abs(pre["raw_m10"])[cand], "a60": np.abs(pre["raw_m60"])[cand],
                         "hour": hours[cand].astype(float), "dir": pre["dir10"][cand],
                         "used": np.zeros(int(cand.sum()), bool)}
        D = P[P["day"] == day]
        if len(D):
            sg = D["sign"].to_numpy(float)
            ts = D["ts_ms"].to_numpy(np.int64)
            pv = {"print_id": D["print_id"].to_numpy(), "day": day} | versions(tr, ts, sg)
            pv_parts.append(pd.DataFrame(pv))
            # (iv) が取れなかった原因
            for pid, c4 in zip(D["print_id"], D["code4"]):
                if pid in iv_got:
                    continue
                n_all = n_noliq = n_cand = 0
                if c4 >= 0:
                    for o in v2.CTRL2_DAY_OFFSETS:
                        c = cache[civ.shift(day, o)]
                        n_all += c["n_all"].get(int(c4), 0)
                        n_noliq += c["n_noliq"].get(int(c4), 0)
                        n_cand += c["n_cand"].get(int(c4), 0)
                cause_rows.append((pid, day, int(c4 < 0), n_all, n_noliq, n_cand))
            # (iv-h)
            tv = {"m15": D[civ.MAT15].to_numpy(float), "m9": D[civ.MAT9].to_numpy(float),
                  "a10": D["a10"].to_numpy(float), "a60": D["a60"].to_numpy(float),
                  "hour": D["hour"].to_numpy(float)}
            cuts5 = dict(cuts) | {"hour": np.arange(1, 24, dtype=float)}
            c5 = {o: cache[civ.shift(day, o)] for o in v2.CTRL2_DAY_OFFSETS}
            off, pick = match5(tv, c5, cuts5)
            got = pick >= 0
            if got.any():
                tt = np.array([c5[o]["t"][j] for o, j in zip(off[got], pick[got])], dtype=np.int64)
                dd = np.array([c5[o]["dir"][j] for o, j in zip(off[got], pick[got])], dtype=float)
                rx = v2.reactions_from_anchor(tr, tt, dd)
                row = {"kind": "(iv-h)大きさと時も合わせた時刻", "day": day, "anchor_ms": tt, "dir": dd,
                       "ref_id": D["print_id"].to_numpy()[got], "day_offset": off[got]}
                for k in ("m15", "m9", "a10", "a60", "hour"):
                    row[f"cand_{k}"] = np.array([c5[o][k][j] for o, j in zip(off[got], pick[got])])
                    row[f"print_{k}"] = tv[k][got]
                row["t0_ms"], row["p0"] = rx["t0_ms"], rx["p0"]
                for h in v2.HORIZONS_S:
                    for k in v2.REACTION_KEYS:
                        row[f"{k}_{h}"] = rx[f"{k}_{h}"]
                row |= versions(tr, tt, dd)
                ivh_parts.append(pd.DataFrame(row))
        # (iv) の対照の版 B・C・D
        g = IVd.get(day)
        if g is not None and len(g):
            ivv_parts.append(pd.DataFrame({"ref_id": g["ref_id"].to_numpy(), "day": day,
                                           "anchor_ms": g["anchor_ms"].to_numpy(np.int64)} |
                                          versions(tr, g["anchor_ms"].to_numpy(np.int64), g["dir"].to_numpy(float))))
        store.drop_before(civ.shift(day, 1 - civ.BACK_DAYS))
        for k in [k for k in cache if k < civ.shift(day, 1 - 3)]:
            del cache[k]
        print(f"[ivh] {day} プリント {len(D)} {time.time() - t:.1f}s 経過 {time.time() - t_all:.0f}s", flush=True)

    IVH = pd.concat(ivh_parts, ignore_index=True)
    PV = pd.concat(pv_parts, ignore_index=True)
    IVV = pd.concat(ivv_parts, ignore_index=True)
    CZ = pd.DataFrame(cause_rows, columns=["print_id", "day", "帯が欠け", "n_all_pm3", "n_noliq_pm3", "n_cand_pm3"])
    IVH.to_csv(out / "controls_ivh.csv.gz", index=False, float_format="%.8g")
    PV.to_csv(out / "prints_versions.csv.gz", index=False, float_format="%.8g")
    IVV.to_csv(out / "controls_iv_versions.csv.gz", index=False, float_format="%.8g")
    CZ.to_csv(out / "iv_unmatched_cause.csv.gz", index=False)
    meta = {"期間": [a.start, a.end], "プリント": int(len(PV)), "対照(iv-h)取れた": int(len(IVH)),
            "(iv)の取れなかったプリント": int(len(CZ)), "所要_秒": round(time.time() - t_all, 1),
            "注": "走らせ直しではなく、走らせと同じ生データからの追加の計算。Jev は呼んでいない。"}
    (out / "control_ivh_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    print(json.dumps(meta, ensure_ascii=False))
    return 0


def match5(tv: dict, cands_by_offset: dict, cuts: dict):
    """`control_iv.match_iv` と同じ順・同じ距離で、帯を 5 つ(4 つ + UTC の時)にしたもの。"""
    keys = ("m15", "m9", "a10", "a60", "hour")
    tb = {k: v2.band_of(tv[k], cuts[k]) for k in keys}
    n = tv["m15"].size
    off = np.full(n, 99, dtype=np.int64)
    pick = np.full(n, -1, dtype=np.int64)
    for o in v2.CTRL2_DAY_OFFSETS:
        c = cands_by_offset.get(o)
        if c is None or c["t"].size == 0:
            continue
        if "_b5" not in c:
            c["_b5"] = {k: v2.band_of(c[k], cuts[k]) for k in keys}
        cb = c["_b5"]
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


if __name__ == "__main__":
    raise SystemExit(main())
