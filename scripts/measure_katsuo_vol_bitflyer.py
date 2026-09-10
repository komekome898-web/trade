"""K1 フレッシュ確認 — bitFlyer のボラ三分位(`FRESH_BITFLYER_PREREG.md` §2、第 15 部と同じ手順)。

固定した設計(判定と同じ、L-082 の設計を bitFlyer に当てる): 門 `s19/b24`、足 5 分・15 分、
H1(`flip_body=True`)+ H2a(`use_invalid=False`)+ H3(`delay_signals`)、強さは **「弱い」だけ**。

境目(D8 の `measure_katsuo_robustness.FootData.vol_prev` = 直前 100 本の
`|log(close/close[-1])| × 1e4` の平均、33/66 パーセンタイル)は
**bitFlyer の 2017〜2019 の設計の取引の入口 `vol_prev` だけ**から決め、
2017〜2026 の全年をその境目で分類する(2020〜2026 は見ずに当てる)。
参考として BitMEX で決めた固定の境目(5 分 [21.79, 35.17] bp、15 分 [29.58, 48.68] bp、
`FRESH_BITFLYER_PREREG.md` §2)を当てた列も同じ形で出す。

bitFlyer は封印もメモリ制約も無いので、2 パスに分けず 1 回だけ読み、
foot ごとに `fold()` する(既定の読み込み範囲 2017-01-01〜2026-08-31、約 5M 行 → 十分小さい)。

    PYTHONPATH=src:scripts python scripts/measure_katsuo_vol_bitflyer.py \
        --out docs/PHASE2/K1/bitflyer/vol_terciles.json
"""
from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np

import k1_source
import measure_katsuo_dispersion as base
import measure_katsuo_effect as eff
import measure_katsuo_robustness as rb

REPO = Path(__file__).resolve().parents[1]
DEFAULT_OUT = REPO / "docs" / "PHASE2" / "K1" / "bitflyer" / "vol_terciles.json"

FEET = (5, 15)
GATE_NAME = "s19/b24"
SMALL, BIG = 19.0, 24.0
EDGE_TRAIN_START = date(2017, 1, 1)
EDGE_TRAIN_END = date(2019, 12, 31)
BITMEX_FIXED_EDGES = {5: (21.79, 35.17), 15: (29.58, 48.68)}


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
        y = datetime.fromtimestamp(ts[entry_i], tz=timezone.utc).year
        out.append((y, r, v))
    return out


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


def per_year_tercile(all_trades, edges, years):
    out = {}
    for y in years:
        buckets: dict[str, list[float]] = {"low": [], "mid": [], "high": []}
        for yy, r, v in all_trades:
            if yy != y:
                continue
            b = bucket_of(v, edges)
            if b is not None:
                buckets[b].append(r)
        out[str(y)] = {
            name: {
                "n": len(rs),
                "mean_bp": round(sum(rs) / len(rs), 3) if rs else None,
                "total_bp": round(sum(rs), 1) if rs else 0.0,
            }
            for name, rs in buckets.items()
        }
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start", type=date.fromisoformat, default=k1_source.default_start("bitflyer"))
    ap.add_argument("--end", type=date.fromisoformat, default=k1_source.default_end("bitflyer"))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()

    print(f"bitflyer 区間 {args.start} 〜 {args.end}")
    seconds = k1_source.load_bars("bitflyer", args.start, args.end)
    load_meta = dict(k1_source.last_load)
    years = list(range(args.start.year, args.end.year + 1))

    result = {
        "note": ("bitFlyer のボラ三分位。境目は bitFlyer 2017-2019 の設計(H1+H2a+H3、弱い、s19/b24)の"
                 "取引の入口 vol_prev(直前 100 本の対数リターン絶対値の平均)の 33/66 パーセンタイルから決め、"
                 "全年(2017-2026)をその境目で分類する(2020-2026 は見ずに当てる)。"
                 "参考列は BitMEX で決めた固定の境目を同じ集合に当てたもの。帰無・MDE・判定バーは作っていない。"),
        "gate": GATE_NAME,
        "design": {"flip_body": True, "use_invalid": False, "delay_entry": True, "keep": "weak"},
        "vol_window": rb.VOL_WINDOW,
        "edges_computed_on": [EDGE_TRAIN_START.isoformat(), EDGE_TRAIN_END.isoformat()],
        "bitmex_fixed_edges_bp": {str(k): list(v) for k, v in BITMEX_FIXED_EDGES.items()},
        "range": [args.start.isoformat(), args.end.isoformat()],
        "load": load_meta,
        "feet": {},
    }

    for foot in FEET:
        print(f"foot={foot} 分")
        bars = base.fold(seconds, foot)
        all_trades = judgement_trades(bars)
        train_trades = [t for t in all_trades if EDGE_TRAIN_START.year <= t[0] <= EDGE_TRAIN_END.year]
        edges_own = edges_from(train_trades)
        n_no_vol = sum(1 for _y, _r, v in all_trades if np.isnan(v))

        result["feet"][str(foot)] = {
            "n_bars": len(bars),
            "edges_bp_own": [round(edges_own[0], 2), round(edges_own[1], 2)] if edges_own else None,
            "edges_bp_bitmex_fixed": list(BITMEX_FIXED_EDGES[foot]),
            "n_no_vol": n_no_vol,
            "n_trades_total": len(all_trades),
            "n_trades_2017_2019": len(train_trades),
            "per_year_own_edges": per_year_tercile(all_trades, edges_own, years),
            "per_year_bitmex_fixed_edges": per_year_tercile(all_trades, BITMEX_FIXED_EDGES[foot], years),
        }
        print(f"  境目(own bp) = {result['feet'][str(foot)]['edges_bp_own']}"
              f" / 取引合計 {len(all_trades):,} 件(2017-2019 {len(train_trades):,} 件)"
              f" / vol 無し {n_no_vol:,} 件")
    del seconds

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n→ {out_path}")


if __name__ == "__main__":
    main()
