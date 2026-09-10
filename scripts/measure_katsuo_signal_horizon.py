"""**建玉を持たずに、シグナル単体の予測力を測る。**

2026-09-09、オーナーの指示「建玉を持たないシグナルの評価をお願いします」。

`measure_katsuo_effect.py` は**機構**(4 分岐 + 決済ルール)を測る。その `mean(r)` は
**向きの情報と決済の構造を混ぜた量**で、`RESULT.md` §3.3 のとおり
「ヒゲに予測力があるか」には答えていない。ここでは決済を外し、**足の数で固定した先の値動き**
だけを見る。

**この測定は機構の測定を置き換えない。並べる。**
(2026-09-09 に「建玉状態を外す」提案が却下されたのは、**機構の測定から**外そうとしたため。
 ここでは機構の測定はそのまま残っている。)

## 測るもの

シグナルの出た足 i について、**h 本先の終値までの符号付きリターン**:

    r_h = sig × ( close[i+h] / close[i] − 1 ) × 10⁴   [bp]

- **建玉状態を持たない。** 同じ足に別のシグナルが出ていても独立に数える
- **決済ルールを使わない。** 無効化もドテンも無い
- **経費は引かない**
- 窓は重なるので、信頼区間は**日単位のブロックブートストラップ**

## 引き算をしない代わりに、横に並べるもの(L-057 の方針)

1. **買いシグナルの後の値動き**と**売りシグナルの後の値動き**を、**符号を付けずに**別々に出す。
   向きの偏り(§3.4)があっても、これなら**両側それぞれの予測力**が読める
2. **全足の無条件の先の値動き**(同じ足・同じ h)。相場そのものの drift
3. 勝率(`r_h > 0` の割合)と年ごとの平均

**h は足の本数**であって時間ではない。約定の無い足は行が無いので、`i+h` が
公称時間(h × foot 分)からずれることがある。**ずれた割合を出力に含める。**

    PYTHONPATH=src python scripts/measure_katsuo_signal_horizon.py
"""
from __future__ import annotations

import argparse
import json
import math
import random
from datetime import date, datetime
from pathlib import Path

import k1_source
import measure_katsuo_dispersion as base
import measure_katsuo_effect as eff

REPO = Path(__file__).resolve().parents[1]

EXPLORE_START = date(2017, 1, 1)
EXPLORE_END = date(2019, 12, 31)

FEET = (1, 3, 5, 15, 30, 60)
HORIZONS = (1, 2, 3, 5, 10, 20, 50)     # 足の本数
STRENGTHS = ("strong", "weak", "both")

BOOTSTRAP = 200
SEED = 20260909


def cell_rng(*parts) -> random.Random:
    """**セルごとに独立な乱数**。種はセルの名前から決まるので、
    他のセルを足しても・順番を変えても・一部の足だけ回しても、そのセルの区間は同じになる。"""
    return random.Random(f"{SEED}|" + "|".join(str(p) for p in parts))


def day_bootstrap(day_sum, day_n, rng, reps=BOOTSTRAP):
    """日単位のブロックブートストラップで平均の 95% 区間を返す。

    **日ごとの (合計, 件数) を先に畳んでから日を復元抽出する。**
    抽出した日の値を全部プールして平均を取るのと**厳密に同じ**で、
    プールを毎回作り直さない分だけ速い(セル数が 4 桁になるので必要)。

    `rng` は**セルごとに作る**(`cell_rng` 参照)。単一の乱数列を全セルで使い回すと、
    **測る項目を 1 つ足しただけで既に報告した区間が動く。** 実際 2026-09-09 に
    年ごとの区間を足したところ、全セルの区間がわずかに変わり、
    0 を跨がないセルの数が 767 → 770 に動いた。**「種 20260909」と書いてある以上、
    それは再現できなければならない。**
    """
    days = sorted(day_sum.keys())   # dict の並び順に依存させない
    if not days:
        return (float("nan"), float("nan"))
    sums = [day_sum[d] for d in days]
    ns = [day_n[d] for d in days]
    k = len(days)
    means = []
    for _ in range(reps):
        s = 0.0
        c = 0
        for _ in range(k):
            j = rng.randrange(k)
            s += sums[j]
            c += ns[j]
        if c:
            means.append(s / c)
    if not means:
        return (float("nan"), float("nan"))
    means.sort()
    return (means[int(0.025 * (len(means) - 1))], means[int(0.975 * (len(means) - 1))])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--feet", type=int, nargs="+", default=list(FEET))
    ap.add_argument("--out", default=None)
    ap.add_argument("--no-trunc", action="store_true",
                    help="向きの比較で int() 切り捨てを外す(HANDOFF §3 手 2。原典からの逸脱なので"
                         "既定の出力とは別ファイルに書く)")
    k1_source.add_source_args(ap)
    args = ap.parse_args()
    trunc = not args.no_trunc
    start, end = k1_source.resolve_range(args)
    if args.out is None:
        args.out = str(k1_source.out_dir(args.source)
                       / ("signal_horizon.json" if trunc else "signal_horizon_notrunc.json"))

    print(f"{args.source} 区間 {start} 〜 {end}(BitMEX の判定区間 2020-2021 には触れない)")
    seconds = k1_source.load_bars(args.source, start, end)
    gs = eff.gates()
    print(f"  バー {len(seconds):,} 行 / 族 = 足 {len(args.feet)} × 門 {len(gs)}"
          f" × 強さ {len(STRENGTHS)} × ホライズン {len(HORIZONS)}"
          f" = {len(args.feet) * len(gs) * len(STRENGTHS) * len(HORIZONS)} セル")

    cells = {}
    baseline = {}

    for foot in args.feet:
        bars = base.fold(seconds, foot)
        n_bars = len(bars)
        ts = [b[0] for b in bars]
        close = [b[4] for b in bars]
        day = [t // 86400 for t in ts]
        year = [datetime.utcfromtimestamp(t).year for t in ts]
        nominal = foot * 60

        # --- 無条件の先の値動き(相場そのもの)。符号を付けない
        fwd = {}
        for h in HORIZONS:
            arr = [None] * n_bars
            tot = 0.0
            cnt = 0
            gap = 0
            byear: dict[str, list] = {}
            for i in range(n_bars - h):
                if close[i] <= 0:
                    continue
                v = (close[i + h] / close[i] - 1.0) * 1e4
                arr[i] = v
                tot += v
                cnt += 1
                if ts[i + h] - ts[i] != nominal * h:
                    gap += 1
                b = byear.setdefault(str(year[i]), [0.0, 0])
                b[0] += v
                b[1] += 1
            fwd[h] = arr
            baseline[f"{foot}|{h}"] = {
                "foot": foot, "h": h, "n": cnt,
                "mean_fwd_bp": round(tot / cnt, 4) if cnt else None,
                "gap_share": round(gap / cnt, 4) if cnt else None,
                "per_year": {y: {"n": v[1], "mean_fwd_bp": round(v[0] / v[1], 4)}
                             for y, v in sorted(byear.items()) if v[1]},
            }

        for g in gs:
            sg = eff.signals(bars, g[0], g[1], trunc=trunc)
            idx = [(i, s[0], s[3]) for i, s in enumerate(sg) if s[0] != 0]
            for keep in STRENGTHS:
                sub = idx if keep == "both" else [x for x in idx if x[2] == keep]
                if len(sub) < 30:
                    continue
                for h in HORIZONS:
                    arr = fwd[h]
                    dsum: dict[int, float] = {}
                    dn: dict[int, int] = {}
                    tot = 0.0
                    sq = 0.0
                    cnt = 0
                    win = 0
                    buy_tot = sell_tot = 0.0
                    buy_n = sell_n = 0
                    ysum: dict[str, list] = {}
                    # 年ごとの区間も出す。年で符号が変わる行が誤差の範囲かを読むため
                    yday: dict[str, tuple[dict, dict]] = {}
                    ybuy: dict[str, list] = {}
                    for i, sig, _stg in sub:
                        v = arr[i]
                        if v is None:
                            continue
                        r = sig * v
                        tot += r
                        sq += r * r
                        cnt += 1
                        if r > 0:
                            win += 1
                        d = day[i]
                        dsum[d] = dsum.get(d, 0.0) + r
                        dn[d] = dn.get(d, 0) + 1
                        if sig == 1:
                            buy_tot += v
                            buy_n += 1
                        else:
                            sell_tot += v
                            sell_n += 1
                        ykey = str(year[i])
                        y = ysum.setdefault(ykey, [0.0, 0])
                        y[0] += r
                        y[1] += 1
                        ys, yn = yday.setdefault(ykey, ({}, {}))
                        ys[d] = ys.get(d, 0.0) + r
                        yn[d] = yn.get(d, 0) + 1
                        yb = ybuy.setdefault(ykey, [0.0, 0, 0.0, 0])
                        if sig == 1:
                            yb[0] += v
                            yb[1] += 1
                        else:
                            yb[2] += v
                            yb[3] += 1
                    if cnt < 30:
                        continue
                    mean = tot / cnt
                    var = (sq - cnt * mean * mean) / (cnt - 1) if cnt > 1 else float("nan")
                    key = f"{foot}|{eff.label(g)}|{keep}|{h}"
                    lo, hi = day_bootstrap(dsum, dn, cell_rng(key))
                    cells[key] = {
                        "foot": foot, "gate": eff.label(g), "strength": keep, "h": h,
                        "n": cnt,
                        "mean_bp": round(mean, 4),
                        "ci95_bp": [round(lo, 4), round(hi, 4)],
                        "sd_bp": round(math.sqrt(var), 1) if var == var and var >= 0 else None,
                        "hit": round(win / cnt, 4),
                        # 符号を付けない先の値動き。買い側と売り側を別々に
                        "buy_n": buy_n,
                        "buy_fwd_bp": round(buy_tot / buy_n, 4) if buy_n else None,
                        "sell_n": sell_n,
                        "sell_fwd_bp": round(sell_tot / sell_n, 4) if sell_n else None,
                        "per_year": {
                            y: {
                                "n": v[1],
                                "mean_bp": round(v[0] / v[1], 3),
                                "ci95_bp": [round(x, 3) for x in
                                            day_bootstrap(yday[y][0], yday[y][1],
                                                          cell_rng(key, y))],
                                "days": len(yday[y][0]),
                                "buy_n": ybuy[y][1],
                                "buy_fwd_bp": (round(ybuy[y][0] / ybuy[y][1], 3)
                                               if ybuy[y][1] else None),
                                "sell_n": ybuy[y][3],
                                "sell_fwd_bp": (round(ybuy[y][2] / ybuy[y][3], 3)
                                                if ybuy[y][3] else None),
                            }
                            for y, v in sorted(ysum.items()) if v[1]},
                    }
        done = [v for k, v in cells.items() if v["foot"] == foot]
        if done:
            b = max(done, key=lambda v: abs(v["mean_bp"]))
            print(f"  {foot:>3}分 完了({len(done)} セル)。最大 |mean| ="
                  f" {b['mean_bp']:+.2f} bp [{b['ci95_bp'][0]:+.2f}, {b['ci95_bp'][1]:+.2f}]"
                  f" n={b['n']:,} ({b['gate']}/{b['strength']}/h={b['h']})")

    Path(args.out).write_text(json.dumps({
        "note": ("建玉を持たず、シグナルの足から h 本先の終値までの符号付きリターン。"
                 "決済ルールを使わない。経費は引いていない。探索区間 2017-2019 のみ。"),
        "explore": [start.isoformat(), end.isoformat()],
        "source": args.source, "load": k1_source.last_load,
        "trunc": trunc,
        "bootstrap_reps": BOOTSTRAP, "seed": SEED,
        "family": {"feet": list(args.feet), "gates": [eff.label(g) for g in gs],
                   "strengths": list(STRENGTHS), "horizons": list(HORIZONS)},
        "baseline_unconditional": baseline,
        "cells": cells,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nセル {len(cells)} 件 → {args.out}")


if __name__ == "__main__":
    main()
