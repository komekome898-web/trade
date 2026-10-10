"""基準の走らせで (1) 1 段目と同じ 1 分足で閉じた取引 と (2) 同じ 1 分足で利確した後にブレイクに入った取引 を数える(L-957)。

- (1) 同分で閉じた取引: 出の足 = 1 段目の足(trades の exit_t ≦ entry_t。どちらも約定した足の終わり。K-328 と同じ切り方)。
- (2) 同分で利確 → ブレイク: 利確(exit_reason close)で閉じた取引のうち、出の足(exit_t − 1 分 = 足の始まり)に
  ブレイクの合図(signals.csv の kind「ブレイク」の start_ts = 足の始まり)が始まったもの。玉を持ったままブレイクに入れば
  逆指値で閉じて出の理由が break になるので、出の理由が利確でその足にブレイクが始まったなら、利確が先でブレイクが後。
  このときブレイクの損切りは起きていない(玉が無い)。1 段目と同じ足の取引(同分)と、前の足から持ち越した取引に分ける。
- 前半・後半は出の UTC の日で 2019-12-09 から後半(K-328 と同じ)。損益は pnl_jpy(円、経費の前)。【試験の無い台本の値】
    python3 docs/RESEARCH/matilda_main/base/same_minute_tp_break.py > docs/RESEARCH/matilda_main/base/same_minute_tp_break.out
"""
import pandas as pd

R = "backtest_runs_shared/matilda_main"
t = pd.read_csv(f"{R}_trades/base/trades.csv.gz", usecols=["entry_t", "exit_t", "pnl_jpy", "exit_reason", "levels"])
s = pd.read_csv(f"{R}/base/signals.csv.gz")
brk = set(pd.to_datetime(s.loc[s.kind == "ブレイク", "start_ts"]))
t["entry"] = pd.to_datetime(t.entry_t)
t["exit"] = pd.to_datetime(t.exit_t)
t["half"] = (t.exit_t.str[:10] >= "2019-12-09").map({False: "前半", True: "後半"})
t["same"] = t.exit <= t.entry
t["brk_bar"] = (t.exit - pd.Timedelta("1min")).isin(brk)
NAME = {"close": "利確", "break": "ブレイク", "market": "成行"}


def row(label, x):
    return f"| {label} | {len(x)} | {x.pnl_jpy.sum():+,.0f} | " + " | ".join(
        f"{len(x[x.half == h])} / {x[x.half == h].pnl_jpy.sum():+,.0f}" for h in ("前半", "後半")) + " |"


print(f"全部の取引 {len(t)} 本・和 {t.pnl_jpy.sum():+,.0f} 円\n")
print("## (1) 1 段目と同じ 1 分足で閉じた取引\n")
print("| 群 | 本 | 和(円) | 前半 本 / 和 | 後半 本 / 和 |")
print("|---|---|---|---|---|")
x = t[t.same]
print(row("同分で閉じた 全部", x))
for r in ("close", "break", "market"):
    print(row(f"うち {NAME[r]}", x[x.exit_reason == r]))
print("\n## (2) 同じ 1 分足で利確した後にブレイクに入った取引(その足のブレイクの損切りは無い)\n")
print("| 群 | 本 | 和(円) | 前半 本 / 和 | 後半 本 / 和 |")
print("|---|---|---|---|---|")
y = t[(t.exit_reason == "close") & t.brk_bar]
print(row("利確 → 同じ足でブレイク 全部", y))
print(row("うち 1 段目と同じ足(同分で閉じた)", y[y.same]))
print(row("うち 前の足から持ち越した", y[~y.same]))
print(f"\n- ブレイクの合図の数 {len(brk)}。利確で閉じた取引 {int((t.exit_reason == 'close').sum())} 本")
