# リードが書いた。委任・批評家を通していない(数えるだけ)。
# 基準にあって本に無い取引(合図の時刻で突き合わせ)のうち保有 0 分の帯(出の時刻 = 建ての時刻)の、出の理由ごとの本数・和・1 本(円)。
# 前半・後半の境 2019-12-09。使い方(リポジトリの根から): python3 docs/RESEARCH/matilda_main/zero_reason.py <本の名前> ...
import sys
import pandas as pd

R = "backtest_runs_shared/matilda_main_trades/"
CUT = pd.Timestamp("2019-12-09", tz="UTC")


def load(name):
    t = pd.read_csv(R + name + "/trades.csv.gz")
    for c in ("signal_t", "entry_t", "exit_t"):
        t[c] = pd.to_datetime(t[c], utc=True)
    return t


b = load("base")
b["h0"] = b["exit_t"] == b["entry_t"]
print("| 本 | 区切り | 出の理由 | 本数 | 和(円) | 1 本(円) |")
print("|---|---|---|---|---|---|")
for name in sys.argv[1:]:
    r = load(name)
    o = b[~b["signal_t"].isin(set(r["signal_t"]))]
    for lab, m in (("前半", o["signal_t"] < CUT), ("後半", o["signal_t"] >= CUT)):
        x = o[m & o["h0"]]
        for reason, g in x.groupby("exit_reason"):
            print(f"| {name} | {lab} | {reason} | {len(g):,} | {g['pnl_jpy'].sum():+,.0f} | {g['pnl_jpy'].mean():+.1f} |")
