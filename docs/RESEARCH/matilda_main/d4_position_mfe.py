# リードが書いた。委任・批評家を通していない(数えるだけ)。L-918(L-916 の持ち越しにしたものを今やる)。
# D4 の負けた取引の 2 群「一度は MFE > 0 だったのに負けた」「MFE ≤ 0 のまま負けた」は、1 段目の約定の値段に対する値動き(move_bp)の
# MFE で分けている(diag_paths.py:106-112)。同じ取引を、持ち高全体(その時点で建っている段の量と平均の値段)の含み(円)の最大で分け直し、
# 何本入れ替わるか・群の円の和がどう変わるかを、32 本全部で数える。
# 持ち高の含み = 向き × (有利な側の端 − 平均の値段) × 量。足は diag_paths と同じ「建ての時刻(1 段目の足の終わり)から出の時刻まで」に始まる足。
# 1 分足の中で段が約定した時刻と高値・安値の順は分からないので、各足の持ち高を 2 通りで取る:
#   前 = その足より前の足で約定した段だけ(その足の中の約定は入れない)/ 後 = その足の中の約定まで入れる
# 約定の列は backtest_runs_shared/matilda_main/<本>/fills.csv.gz、取引の行は backtest_runs_shared/matilda_main_trades/<本>/trades.csv.gz。
# 含みが 1e-6 円以下は 0 とみなす(1 段だけの levels_1 では 1 段目の MFE と一致するはずで、それを検めに使う)。
# 使い方(リポジトリの根から): PYTHONPATH=src:scripts/w4_measure python3 docs/RESEARCH/matilda_main/d4_position_mfe.py > docs/RESEARCH/matilda_main/d4_position_mfe.out
import csv
import gzip
import os
import sys
from collections import Counter

import numpy as np

sys.path.insert(0, "scripts/analysis")
import diag_paths as dp  # noqa: E402
from bot.bt.simple.common import to_ns  # noqa: E402

F = "backtest_runs_shared/matilda_main/"
T = "backtest_runs_shared/matilda_main_trades/"
runs = sorted(x for x in os.listdir(T) if os.path.isdir(T + x)) if len(sys.argv) < 2 else sys.argv[1:]

from common import SEAL, to_ns as w4_to_ns  # noqa: E402
bars = dp.load_bitflyer_bars(to_ns("2015-11-30T00:00:00+00:00"), w4_to_ns(SEAL))
print(f"1 分足 {len(bars.t):,} 本を読んだ\n")
print("| 本 | 負けた取引(足の後まで持った) | 1 段目の MFE > 0 | 持ち高の含み > 0(前) | 持ち高の含み > 0(後) | 入れ替わり(前): 1 段目 ≤ 0 → 持ち高 > 0 | 入れ替わり(前): 1 段目 > 0 → 持ち高 ≤ 0 | 入れ替わり(後): ≤0→>0 | 入れ替わり(後): >0→≤0 | 円の和: 1 段目 MFE > 0 の群 / ≤ 0 の群 | 円の和: 持ち高(前)> 0 / ≤ 0 |")
print("|---|---|---|---|---|---|---|---|---|---|---|")
for run in runs:
    fills = []
    with gzip.open(F + run + "/fills.csv.gz", "rt", encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            fills.append((to_ns(r["ts"]), r["side"], float(r["qty"]), float(r["px"])))
    # 建玉 0 → 0 の塊(simple_trades.py と同じ切り方)。最初の約定の時刻で引く
    chunks, cur, pos = {}, [], 0.0
    for f in fills:
        cur.append(f)
        pos += f[2] if f[1] == "buy" else -f[2]
        if abs(pos) < 1e-12:
            chunks[cur[0][0]] = cur
            cur, pos = [], 0.0
    c = Counter()
    sums = Counter()
    with gzip.open(T + run + "/trades.csv.gz", "rt", encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            if r.get("in_measure", "True") == "False":
                continue
            pnl = float(r["pnl_jpy"])
            if pnl >= 0:
                continue
            en, ex, s, e = to_ns(r["entry_t"]), to_ns(r["exit_t"]), int(float(r["side"])), float(r["entry_price"])
            ts, hs, ls = bars.span(en, ex)
            if len(ts) == 0:
                continue
            ch = chunks[to_ns(r["signal_t"])]
            opens = [f for f in ch if (f[1] == "buy") == (s > 0)]  # 建てる側の約定(段)
            fav = hs if s > 0 else ls
            mfe1 = float(np.max(s * (fav / e - 1.0)))
            res = {}
            for mode in ("前", "後"):
                best = -np.inf
                for i, b in enumerate(ts):
                    fs = [f for f in opens if (f[0] < b if mode == "前" else f[0] <= b)]
                    q = sum(f[2] for f in fs)
                    if q <= 0:
                        continue
                    avg = sum(f[2] * f[3] for f in fs) / q
                    best = max(best, s * (fav[i] - avg) * q)
                res[mode] = best > 1e-6  # 平均の値段の浮動小数の誤差で、建値ちょうどの足を含み益と数えないため(1 段の levels_1 で 45 本ずれた)
            a = mfe1 > 0
            c["n"] += 1
            c["mfe1"] += a
            c["前"] += res["前"]
            c["後"] += res["後"]
            c["前 ≤→>"] += (not a) and res["前"]
            c["前 >→≤"] += a and not res["前"]
            c["後 ≤→>"] += (not a) and res["後"]
            c["後 >→≤"] += a and not res["後"]
            sums["1>"] += pnl if a else 0
            sums["1≤"] += 0 if a else pnl
            sums["前>"] += pnl if res["前"] else 0
            sums["前≤"] += 0 if res["前"] else pnl
    print(f"| {run} | {c['n']:,} | {c['mfe1']:,} | {c['前']:,} | {c['後']:,} | {c['前 ≤→>']:,} | {c['前 >→≤']:,} | {c['後 ≤→>']:,} | {c['後 >→≤']:,} | "
          f"{sums['1>']:+,.0f} / {sums['1≤']:+,.0f} | {sums['前>']:+,.0f} / {sums['前≤']:+,.0f} |", flush=True)
