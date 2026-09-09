"""**手 1 — 機構の仮説を測る**(`docs/PHASE2/K1/HANDOFF.md` §3)。

`RESULT.md` §4.5 の仮説:

    足の中で戻りが終わっているかどうかが符号を決める。
    下ヒゲ + 陽線(戻り切った)  → その後は下がる      … 「強い」が逆を向く理由
    下ヒゲ + 陰線(戻り切っていない)→ その後に戻る    … 「弱い」が合う理由

**これは仮説であって測っていなかった。** ここで測る。

## 測り方

向きが決まる全足(`int(under) ≠ int(top)`)を母集団にして、次の 3 軸で層に切る:

    ヒゲ長 wbp   = 勝った側のヒゲ / 終値 × 10⁴          … 層 W
    実体比 ratio = |実体| / 勝った側のヒゲ                … 層 R
    強さ         = 実体の符号がシグナルの向きと同じか      … strong / weak

**ヒゲ長を固定して実体だけを動かしたとき**に後続リターン(建玉なし、h 本先の終値)が
どう変わるかを見る。仮説が正しければ:

    同じ W の中で、strong は負・weak は正
    strong の中で、ratio が大きい(陽線の実体が大きい = 戻りが強い)ほど負が深い

門 `s19/b24`(当時の規則)は上の母集団の部分集合なので、同じ層で別に出す。

## 再現ゲート(HANDOFF §3 手 1)

- 向き・強さ・門の判定は `measure_katsuo_effect.signals()` を **import** して使う。
  自前で計算した w・ratio は、その判定と**一致することを assert** する
- 層を全部合わせた `s19/b24` の (n, 平均) が `signal_horizon.json` の該当セルと
  **一致することを検査してから**出力する。一致しなければ止まる
- 区間は `measure_katsuo_signal_horizon.day_bootstrap` / `cell_rng` を import(方法を揃える)

## 出さないもの

判定・帰無・MDE・経費。探索区間 2017-2019 のみ。判定区間 2020-2021 には触れない。

    PYTHONPATH=src:scripts python scripts/measure_katsuo_body_wick.py
"""
from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from pathlib import Path

import measure_katsuo_dispersion as base
import measure_katsuo_effect as eff
from measure_katsuo_signal_horizon import cell_rng, day_bootstrap

REPO = Path(__file__).resolve().parents[1]
SH = REPO / "docs" / "PHASE2" / "K1" / "signal_horizon.json"

EXPLORE_START = date(2017, 1, 1)
EXPLORE_END = date(2019, 12, 31)

FEET = (1, 3, 5, 15, 30, 60)
HORIZONS = (1, 2, 3, 5, 10)
# 層の境界。上限は含まない。最後の層は上限なし
WICK_BINS = (0.0, 5.0, 10.0, 19.0, 24.0, 40.0, 70.0)      # bp
RATIO_BINS = (0.0, 0.25, 0.5, 0.75, 1.0, 2.0)               # |実体| / ヒゲ
GATES = {"all": (None, None), "s19/b24": (19.0, 24.0)}


def bin_of(x, edges):
    """`edges` の区間に落とす。返すのは区間のラベル文字列。"""
    for i in range(len(edges) - 1):
        if edges[i] <= x < edges[i + 1]:
            return f"[{edges[i]:g},{edges[i + 1]:g})"
    return f"[{edges[-1]:g},+)"


def direction_and_shape(o, h, l, c):
    """向き(原典の int() 比較)と、勝った側のヒゲ・実体。`eff.signals` と同じ式。"""
    candle = c - o
    if candle == 0 or c <= 0:
        return 0, 0.0, 0.0, 0
    csign = 1 if candle > 0 else -1
    top, under = (h - c, o - l) if csign == 1 else (h - o, c - l)
    if int(top) > int(under):
        return -1, top, abs(candle), csign
    if int(under) > int(top):
        return 1, under, abs(candle), csign
    return 0, 0.0, 0.0, csign


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--feet", type=int, nargs="+", default=list(FEET))
    ap.add_argument("--out", default=str(REPO / "docs" / "PHASE2" / "K1" / "body_wick.json"))
    args = ap.parse_args()

    ref = json.loads(SH.read_text("utf-8"))["cells"] if SH.exists() else {}

    print(f"探索区間 {EXPLORE_START} 〜 {EXPLORE_END}(判定区間 2020-2021 には触れない)")
    seconds = base.load_seconds(EXPLORE_START, EXPLORE_END)
    print(f"  秒バー {len(seconds):,} 行")

    cells = {}
    baseline = {}
    repro = []

    for foot in args.feet:
        bars = base.fold(seconds, foot)
        n_bars = len(bars)
        ts = [b[0] for b in bars]
        close = [b[4] for b in bars]
        day = [t // 86400 for t in ts]

        fwd = {}
        for h in HORIZONS:
            arr = [None] * n_bars
            tot = 0.0
            cnt = 0
            for i in range(n_bars - h):
                if close[i] > 0:
                    v = (close[i + h] / close[i] - 1.0) * 1e4
                    arr[i] = v
                    tot += v
                    cnt += 1
            fwd[h] = arr
            baseline[f"{foot}|{h}"] = {"n": cnt, "mean_fwd_bp": round(tot / cnt, 4) if cnt else None}

        # 向き・形は自前で計算し、門ごとの判定は eff.signals で取る。両者の一致を assert
        shape = [direction_and_shape(o, h_, l, c) for (_t, o, h_, l, c) in bars]
        for gate_name, (s, b) in GATES.items():
            if gate_name == "all":
                member = [(i, sg, ("strong" if sg == cs else "weak"))
                          for i, (sg, _w, _bd, cs) in enumerate(shape) if sg != 0]
            else:
                sig = eff.signals(bars, s, b)
                member = []
                for i, (sg, _lc, _cs, strength) in enumerate(sig):
                    if sg == 0:
                        continue
                    assert shape[i][0] == sg, (foot, i, "向きが eff.signals と食い違う")
                    assert strength == ("strong" if sg == shape[i][3] else "weak"), (foot, i)
                    member.append((i, sg, strength))

            # 層ごとに集計
            acc: dict[tuple, dict] = {}
            for i, sg, strength in member:
                _sg, w, body, _cs = shape[i]
                wbp = w / close[i] * 1e4
                ratio = body / w if w > 0 else float("inf")
                wb = bin_of(wbp, WICK_BINS)
                rb = bin_of(ratio, RATIO_BINS)
                for h in HORIZONS:
                    v = fwd[h][i]
                    if v is None:
                        continue
                    r = sg * v
                    d = day[i]
                    # 層のセルに加えて、**周辺**(片方の軸を畳んだもの、記号 "*")も
                    # 正式なセルとして持つ。個々の層は n が数百で読めないので、
                    # 仮説の主張(実体比の向き / ヒゲ長の向き)は周辺で読む。
                    # ("*","*") は層を全部合わせたもの = 再現ゲートと同じ量
                    for key in ((gate_name, foot, wb, rb, strength, h),
                                (gate_name, foot, wb, "*", strength, h),
                                (gate_name, foot, "*", rb, strength, h),
                                (gate_name, foot, "*", "*", strength, h)):
                        a = acc.setdefault(key, {"n": 0, "tot": 0.0, "dsum": {}, "dn": {},
                                                 "buy": [0.0, 0], "sell": [0.0, 0]})
                        a["n"] += 1
                        a["tot"] += r
                        a["dsum"][d] = a["dsum"].get(d, 0.0) + r
                        a["dn"][d] = a["dn"].get(d, 0) + 1
                        side = a["buy"] if sg == 1 else a["sell"]
                        side[0] += v
                        side[1] += 1

            for key, a in acc.items():
                if a["n"] < 30:
                    continue
                gate_name_, foot_, wb, rb, strength, h = key
                k = f"{gate_name_}|{foot_}|{wb}|{rb}|{strength}|{h}"
                lo, hi = day_bootstrap(a["dsum"], a["dn"], cell_rng("body_wick", k))
                cells[k] = {
                    "gate": gate_name_, "foot": foot_, "wick_bin": wb, "ratio_bin": rb,
                    "strength": strength, "h": h,
                    "n": a["n"], "mean_bp": round(a["tot"] / a["n"], 4),
                    "ci95_bp": [round(lo, 4), round(hi, 4)],
                    "buy_n": a["buy"][1],
                    "buy_fwd_bp": round(a["buy"][0] / a["buy"][1], 4) if a["buy"][1] else None,
                    "sell_n": a["sell"][1],
                    "sell_fwd_bp": round(a["sell"][0] / a["sell"][1], 4) if a["sell"][1] else None,
                }

            # 再現ゲート: 層を全部合わせた s19/b24 が signal_horizon.json と一致するか
            if gate_name == "s19/b24" and ref:
                for strength in ("strong", "weak"):
                    for h in HORIZONS:
                        # ("*","*") のセル = 層を全部合わせたもの
                        a_all = acc.get((gate_name, foot, "*", "*", strength, h))
                        if a_all is None:
                            continue
                        n_all, tot_all = a_all["n"], a_all["tot"]
                        rc = ref.get(f"{foot}|s19/b24|{strength}|{h}")
                        if rc is None:
                            continue
                        ok = (n_all == rc["n"]) and abs(tot_all / n_all - rc["mean_bp"]) < 1e-3
                        repro.append({"foot": foot, "strength": strength, "h": h,
                                      "n_here": n_all, "n_ref": rc["n"],
                                      "mean_here": round(tot_all / n_all, 4),
                                      "mean_ref": rc["mean_bp"], "ok": ok})
                        if not ok:
                            raise SystemExit(f"再現ゲート不一致: {foot}分 {strength} h={h} "
                                             f"n {n_all} vs {rc['n']}, mean {tot_all / n_all:.4f}"
                                             f" vs {rc['mean_bp']}")
        print(f"  {foot:>3}分 完了({sum(1 for v in cells.values() if v['foot'] == foot)} セル)")

    Path(args.out).write_text(json.dumps({
        "note": ("ヒゲ長 × 実体比 × 強さ の層ごとの h 本先リターン(建玉なし)。"
                 "探索区間 2017-2019 のみ。判定・帰無・MDE・経費は無し。"),
        "bins": {"wick_bp": list(WICK_BINS), "ratio": list(RATIO_BINS)},
        "horizons": list(HORIZONS), "gates": list(GATES),
        "reproduction_gate": repro,
        "baseline_unconditional": baseline,
        "cells": cells,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n再現ゲート {sum(r['ok'] for r in repro)}/{len(repro)} 一致。セル {len(cells)} 件 → {args.out}")


if __name__ == "__main__":
    main()
