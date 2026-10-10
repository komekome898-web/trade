"""待ちを短くした 2 本(L-945)で、利確が「利益 1 円の値段」(`matilda_simple.py:283`、玉の段数 h のとき損益 = h 円)で付いた本数を数える
(相方 04_D10 の指摘 1)。印: 利確(close)で 段あたりの損益(pnl_jpy ÷ levels)が 0.5 円より大きく 1.5 円以下 = 「1 円の値段」の付近の利確。
境の出所: 1 円の値段の利確は段あたり 1 円(定義)。実際は 0.98 円などに散る(初版の |pnl − levels| < 0.005 では 5 分の 20 分超… の大半を取りこぼした)ので、1 円の両側 0.5 円を取った(リードの選択。0.5 円以下・1.5 円より大きい側は満額側に入る)。
注意: 「1 円の値段」の利確は、待ちを越えて緩めたときと、緩めなくても中心 − 3·vola が 1 円の値段より不利なとき(`_tp_px` の better = 1 円の値段)の両方で付く。
この台本はその 2 つを分けない(取引の行に緩めたかの列が無い)。【試験の無い台本の値】
    python3 docs/RESEARCH/matilda_main/alert/alert_loosen.py > docs/RESEARCH/matilda_main/alert/alert_loosen.out
"""
import pandas as pd

T = "backtest_runs_shared/matilda_main_trades"
CUT = "2019-12-09"


def load(run):
    d = pd.read_csv(f"{T}/{run}/trades.csv.gz", usecols=["signal_t", "pnl_jpy", "exit_reason", "levels"])
    d["half"] = (d.signal_t.str[:10] >= CUT).map({False: "前半", True: "後半"})
    x = d.pnl_jpy / d.levels
    d["one"] = (d.exit_reason == "close") & (x > 0.5) & (x <= 1.5)
    return d


runs = {r: load(r) for r in ("base", "alert_10", "alert_5")}
print("## 利確のうち「1 円の値段」で付いた本数(円)\n")
print("| 本 | 半分 | 利確 本 | うち 1 円の値段 本(割合) | その和 | それ以外の利確 本 | 和 | 1 本あたり |")
print("|---|---|---|---|---|---|---|---|")
for r, d in runs.items():
    for h in ("前半", "後半"):
        c = d[(d.half == h) & (d.exit_reason == "close")]
        o, n = c[c.one], c[~c.one]
        print(f"| {r} | {h} | {len(c)} | {len(o)}({len(o) / len(c):.1%}) | {o.pnl_jpy.sum():+.0f} | {len(n)} | {n.pnl_jpy.sum():+.0f} | {n.pnl_jpy.mean():+.2f} |")

for r in ("alert_5", "alert_10"):
    m = runs["base"].merge(runs[r], on="signal_t", suffixes=("_b", "_a"))
    m = m[(m.exit_reason_b == "close") & (m.exit_reason_a == "close")]
    m["diff"] = m.pnl_jpy_a - m.pnl_jpy_b
    print(f"\n## 基準でも {r} でも利確の取引({len(m)} 本、差の和 {m['diff'].sum():+.0f} 円)を「1 円の値段」で割る\n")
    print("| 半分 | 基準 | " + r + " | 本 | 差の和(円) | 1 本あたり |")
    print("|---|---|---|---|---|---|")
    for h in ("前半", "後半"):
        x = m[m.half_b == h]
        for ob in (False, True):
            for oa in (False, True):
                y = x[(x.one_b == ob) & (x.one_a == oa)]
                if len(y):
                    print(f"| {h} | {'1 円' if ob else '満額側'} | {'1 円' if oa else '満額側'} | {len(y)} | {y['diff'].sum():+.0f} | {y['diff'].mean():+.2f} |")

# 満額側どうしの利確を、段数(levels)が同じか違うかで割る(「1 円の値段」で説明されない分の在処)
for r in ("alert_5", "alert_10"):
    m = runs["base"].merge(runs[r], on="signal_t", suffixes=("_b", "_a"))
    m = m[(m.exit_reason_b == "close") & (m.exit_reason_a == "close") & ~m.one_b & ~m.one_a]
    m["diff"] = m.pnl_jpy_a - m.pnl_jpy_b
    print(f"\n## 満額側どうしの利確({r}、{len(m)} 本)を段数で割る\n")
    print("| 半分 | 段数 | 本 | 差の和(円) | 1 本あたり |")
    print("|---|---|---|---|---|")
    for h in ("前半", "後半"):
        x = m[m.half_b == h]
        for lab, y in (("同じ", x[x.levels_a == x.levels_b]), (f"{r} が少ない", x[x.levels_a < x.levels_b]), (f"{r} が多い", x[x.levels_a > x.levels_b])):
            if len(y):
                print(f"| {h} | {lab} | {len(y)} | {y['diff'].sum():+.0f} | {y['diff'].mean():+.2f} |")
