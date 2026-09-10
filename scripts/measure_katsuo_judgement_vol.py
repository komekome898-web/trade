"""K1 判定 — 経年劣化の読み: D8 のボラ三分位を判定区間に当てる(`JUDGEMENT_PREREG.md` §4)。

**固定した設計(判定、L-082)**: 門 `s19/b24`、足 5 分・15 分、H1(`flip_body=True`)+
H2a(`use_invalid=False`)+ H3(`delay_signals`)、強さは **「弱い」だけ**(`keep="weak"`)。

三分位の境目(D8 と同じ定義。`measure_katsuo_robustness.FootData.vol_prev` = 直前 100 本の
`|log(close/close[-1])| × 1e4` の平均)は **2017-2019 の判定設計の取引の入口 `vol_prev`
だけ**から決める(33 / 66 パーセンタイル)。2020-2021 の取引はその境目で分類する
(境目自体は 2020-2021 を見ない)。**推定・決定**: 母集団は D8 の「全シグナル足」ではなく
判定設計そのもの(=「弱い」の取引)の入口とした。境目・取引の対象は同じ集合。

**メモリの都合で 2 パス**: 2017-2019 と 2020-2021 を別々に読み、5 分・15 分に畳んだら
秒バーは捨てる(同時に両方の秒バーを持たない)。2020-2021 を読むには封印を開ける
(`--open-seal` + 環境変数 `K1_SEAL_APPROVAL=L-085`、`k1_source.resolve_range` 経由)。

出すもの: 足ごとに 2017-2019 で決めた境目と、年(2017-2021)× 三分位(low/mid/high)の
n・mean_bp・total_bp。

    K1_SEAL_APPROVAL=L-085 PYTHONPATH=src:scripts python scripts/measure_katsuo_judgement_vol.py \
        --open-seal --out docs/PHASE2/K1/judgement/vol_terciles_2017_2021.json
"""
from __future__ import annotations

import argparse
import gc
import json
from datetime import date, datetime
from pathlib import Path

import numpy as np

import k1_source
import measure_katsuo_dispersion as base
import measure_katsuo_effect as eff
import measure_katsuo_robustness as rb

REPO = Path(__file__).resolve().parents[1]
DEFAULT_OUT = REPO / "docs" / "PHASE2" / "K1" / "judgement" / "vol_terciles_2017_2021.json"

FEET = (5, 15)
GATE_NAME = "s19/b24"
SMALL, BIG = 19.0, 24.0
YEARS = (2017, 2018, 2019, 2020, 2021)
TERCILES = (("low", -np.inf), ("mid", None), ("high", None))  # 境目は edges から埋める


def judgement_trades(bars):
    """判定の設計(H1+H2a+H3、keep='weak')の取引を出し、各取引の入口 `year` と `vol_prev` を添える。

    返すのは (year, ret_bp, vol_prev) のリスト。`vol_prev` は `nan` のことがある
    (足の先頭 `VOL_WINDOW+1` 本)。
    """
    fd = rb.FootData(bars)
    sig = eff.signals(bars, SMALL, BIG, flip_body=True)
    sig = eff.delay_signals(sig)                       # H3
    trades = eff.simulate(bars, sig, keep="weak", use_invalid=False)  # H2a
    ts = [b[0] for b in bars]
    out = []
    for entry_i, r, _hold, _why in trades:
        v = float(fd.vol_prev[entry_i])
        y = datetime.utcfromtimestamp(ts[entry_i]).year
        out.append((y, r, v))
    return out


def load_folded(start: date, end: date, foot: int, open_seal: bool):
    """秒バーを読んで畳んだらすぐ捨てる。行数を報告用に返す。"""
    args = argparse.Namespace(source="bitmex", start=start, end=end, open_seal=open_seal)
    lo, hi = k1_source.resolve_range(args)
    seconds = k1_source.load_bars("bitmex", lo, hi)
    n_seconds = len(seconds)
    bars = base.fold(seconds, foot)
    print(f"  読み込み {lo} 〜 {hi}(foot={foot}分): 秒バー {n_seconds:,} 行 → 足 {len(bars):,} 本")
    del seconds
    gc.collect()
    return bars, lo, hi, n_seconds


def edges_from(trades_2017_19):
    v = np.array([vv for _y, _r, vv in trades_2017_19 if not np.isnan(vv)])
    if v.size == 0:
        return None
    return float(np.quantile(v, 1 / 3)), float(np.quantile(v, 2 / 3))


def bucket_of(v: float, edges) -> str | None:
    if edges is None or np.isnan(v):
        return None
    q1, q2 = edges
    if v < q1:
        return "low"
    if v < q2:
        return "mid"
    return "high"


def per_year_tercile(all_trades, edges):
    out = {}
    for y in YEARS:
        row = {name: {"n": 0, "mean_bp": None, "total_bp": 0.0} for name in ("low", "mid", "high")}
        buckets: dict[str, list[float]] = {"low": [], "mid": [], "high": []}
        for yy, r, v in all_trades:
            if yy != y:
                continue
            b = bucket_of(v, edges)
            if b is not None:
                buckets[b].append(r)
        for name, rs in buckets.items():
            row[name] = {
                "n": len(rs),
                "mean_bp": round(sum(rs) / len(rs), 3) if rs else None,
                "total_bp": round(sum(rs), 1) if rs else 0.0,
            }
        out[str(y)] = row
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--open-seal", action="store_true",
                    help="2020-2021 を読むのに要る(環境変数 K1_SEAL_APPROVAL=L-085 も要る。"
                         "docs/PHASE2/K1/JUDGEMENT_PREREG.md §1/§7)")
    args = ap.parse_args()

    result = {
        "note": ("D8(measure_katsuo_robustness.FootData.vol_prev)の三分位を判定区間に当てる。"
                 "境目は 2017-2019 の判定設計(H1+H2a+H3、弱い)の取引の入口 vol_prev だけから決め、"
                 "2020-2021 はその境目で分類する(境目自体は 2020-2021 を見ない)。"
                 "帰無・MDE・判定バーは作っていない。経費は引いていない。"),
        "gate": GATE_NAME,
        "design": {"flip_body": True, "use_invalid": False, "delay_entry": True, "keep": "weak"},
        "vol_window": rb.VOL_WINDOW,
        "edges_computed_on": ["2017-01-01", "2019-12-31"],
        "feet": {},
    }

    for foot in FEET:
        print(f"foot={foot} 分")
        bars_in, lo_in, hi_in, n_in = load_folded(date(2017, 1, 1), date(2019, 12, 31), foot,
                                                   open_seal=False)
        trades_in = judgement_trades(bars_in)
        n_bars_in = len(bars_in)
        del bars_in
        gc.collect()

        edges = edges_from(trades_in)

        bars_seal, lo_seal, hi_seal, n_seal = load_folded(date(2020, 1, 1), date(2021, 12, 31), foot,
                                                          open_seal=args.open_seal)
        trades_seal = judgement_trades(bars_seal)
        n_bars_seal = len(bars_seal)
        del bars_seal
        gc.collect()

        all_trades = trades_in + trades_seal
        n_no_vol = sum(1 for _y, _r, v in all_trades if np.isnan(v))

        result["feet"][str(foot)] = {
            "edges_bp": [round(edges[0], 2), round(edges[1], 2)] if edges else None,
            "n_no_vol": n_no_vol,
            "load": {
                "2017_2019": {"range": [lo_in.isoformat(), hi_in.isoformat()],
                              "seconds_rows": n_in, "bars": n_bars_in},
                "2020_2021": {"range": [lo_seal.isoformat(), hi_seal.isoformat()],
                              "seconds_rows": n_seal, "bars": n_bars_seal},
            },
            "n_trades_2017_2019": len(trades_in),
            "n_trades_2020_2021": len(trades_seal),
            "per_year": per_year_tercile(all_trades, edges),
        }
        print(f"  境目(bp) = {result['feet'][str(foot)]['edges_bp']}"
              f" / 取引 2017-2019 {len(trades_in):,} 件 2020-2021 {len(trades_seal):,} 件"
              f" / vol 無し {n_no_vol:,} 件")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n→ {out_path}")


if __name__ == "__main__":
    main()
