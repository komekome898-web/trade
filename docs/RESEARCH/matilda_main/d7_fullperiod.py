# リードが書いた。委任・批評家を通していない(数えるだけ)。関門 ② 3 族 1 回目の指摘 1 の確かめ。
# 読み口 diag_tables.py の D7 は 2 本の「期間の日」の共通部分だけで差を取る(:367)。期間の始まりが基準と違う本(最初の約定が遅い本)では、
# 基準だけが取引した日が落ちる。ここでは基準の期間の日で、取引の無い日を 0 円として日ごとの差を取り直す。区間は読み口と同じ(循環の日の塊 5 日・1,000 回・種 20261004)。
# 使い方(リポジトリの根から): PYTHONPATH=src python3 docs/RESEARCH/matilda_main/d7_fullperiod.py <本の名前> ...
import sys
import pandas as pd
from bot.bt.validation import block_bootstrap_ci

R = "backtest_runs_shared/matilda_main_trades/"
CUT = "2019-12-09"


def daily(name):
    t = pd.read_csv(R + name + "/trades.csv.gz", usecols=["exit_t", "pnl_jpy"])
    d = pd.to_datetime(t["exit_t"], utc=True).dt.strftime("%Y-%m-%d")
    return t.groupby(d)["pnl_jpy"].sum()


def ci(x):
    c = block_bootstrap_ci([float(v) for v in x], block_len=5, n_resamples=1000, seed=20261004, alpha=0.05,
                           method="circular", statistic="mean")
    return c


base = daily("base")
days = pd.date_range(base.index.min(), base.index.max(), freq="D").strftime("%Y-%m-%d")
b = base.reindex(days, fill_value=0.0)
print("| 本 | 区切り | 日数 | 本の最初の取引の日 | 差 円/日 [区間] |")
print("|---|---|---|---|---|")
for name in sys.argv[1:]:
    r0 = daily(name)
    r = r0.reindex(days, fill_value=0.0)
    diff = r - b
    for lab, m in (("全期間", slice(None)), ("前半", diff.index < CUT), ("後半", diff.index >= CUT),
                   ("2015", diff.index.str[:4] == "2015")):
        x = diff[m]
        c = ci(x.values)
        print(f"| {name} | {lab} | {len(x)} | {r0.index.min()} | {x.mean():+.1f} [{c.lo:+.1f}, {c.hi:+.1f}] |")
