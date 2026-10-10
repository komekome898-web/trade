"""L-964 の振り返り(計画 第 5 版 段 4 の合成器は「場面の変数に対する期待値」を使う)のための表:
基準の取引を、建てた時点の幅 ÷ 1 段目の約定値段(判断の時点で分かる値)の帯で分け、前半・後半の 1 日あたりの円を出す。
帯の境は PLAN.md §1.4 の全期間の分布の 10・25・50・75・90% 点(帯の境は標本の中)。幅は r4_lines_dump.py の書き出し(1 段目の約定の直前の ind["width"])。
結び方: 書き出しの行の start(1 段目の足の始まり)+ 1 分 = 取引の entry_t。区間は付けていない(点の値)。【試験の無い台本の値】
    python3 docs/RESEARCH/matilda_main/stage2/r5_width_scene.py <lines.csv> > docs/RESEARCH/matilda_main/stage2/r5_width_scene.out
"""
import sys
import pandas as pd

CUT = "2019-12-09"
DAYS = {"前半": 1469, "後半": 1470}
EDGES = [0, 0.001857, 0.003010, 0.005133, 0.008844, 0.014995, 1]
LAB = ["〜10%点", "10〜25%", "25〜50%", "50〜75%", "75〜90%", "90%点〜"]
ln = pd.read_csv(sys.argv[1], usecols=["start", "px", "width"])
ln["entry_t"] = pd.to_datetime(ln.start + 60_000_000_000, utc=True)
t = pd.read_csv("backtest_runs_shared/matilda_main_trades/base/trades.csv.gz", usecols=["entry_t", "signal_t", "pnl_jpy"])
t["entry_t"] = pd.to_datetime(t.entry_t, utc=True)
m = t.merge(ln, on="entry_t", how="left")
print(f"取引 {len(t):,} 本・結べた {m.width.notna().sum():,} 本\n")
m["band"] = pd.cut(m.width / m.px, EDGES, labels=LAB, right=False)
m["half"] = (m.signal_t.str[:10] >= CUT).map({False: "前半", True: "後半"})
print("| 幅の帯(全期間の分布の点) | 前半 本 | 前半 円/日 | 前半 1 本あたり | 後半 本 | 後半 円/日 | 後半 1 本あたり |")
print("|---|---|---|---|---|---|---|")
for b in LAB:
    r = [b]
    for h in ("前半", "後半"):
        x = m[(m.band == b) & (m.half == h)].pnl_jpy
        r += [f"{len(x):,}", f"{x.sum() / DAYS[h]:+.1f}", f"{x.mean():+.2f}"]
    print("| " + " | ".join(r) + " |")
