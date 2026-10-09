# リードが書いた。委任・批評家を通していない(数えるだけ)。
# 2 本の門の本で、基準にあって本に無い取引(合図の時刻で突き合わせ)がどれだけ重なるかを前半・後半で数える。
# 使い方(リポジトリの根から): python3 docs/RESEARCH/matilda_main/gate_overlap.py <本 A> <本 B>
import sys
import pandas as pd

R = "backtest_runs_shared/matilda_main_trades/"
CUT = pd.Timestamp("2019-12-09", tz="UTC")


def load(name):
    t = pd.read_csv(R + name + "/trades.csv.gz")
    t["signal_t"] = pd.to_datetime(t["signal_t"], utc=True)
    return t


a_name, b_name = sys.argv[1], sys.argv[2]
base = load("base")
oa = base[~base["signal_t"].isin(set(load(a_name)["signal_t"]))]
ob = base[~base["signal_t"].isin(set(load(b_name)["signal_t"]))]
both = oa[oa["signal_t"].isin(set(ob["signal_t"]))]
print(f"| 区切り | {a_name} で外れ 本 / 和(円) | {b_name} で外れ 本 / 和(円) | 両方で外れ 本 / 和(円) | 両方 ÷ {a_name} | 両方 ÷ {b_name} | {a_name} だけ 本 / 和(円) | {b_name} だけ 本 / 和(円) |")
print("|---|---|---|---|---|---|---|---|")
for lab, half in (("前半", lambda d: d[d["signal_t"] < CUT]), ("後半", lambda d: d[d["signal_t"] >= CUT])):
    x, y, z = half(oa), half(ob), half(both)
    print(f"| {lab} | {len(x):,} / {x['pnl_jpy'].sum():+,.0f} | {len(y):,} / {y['pnl_jpy'].sum():+,.0f} | {len(z):,} / {z['pnl_jpy'].sum():+,.0f} | {len(z) / len(x):.1%} | {len(z) / len(y):.1%} | {len(x) - len(z):,} / {x['pnl_jpy'].sum() - z['pnl_jpy'].sum():+,.0f} | {len(y) - len(z):,} / {y['pnl_jpy'].sum() - z['pnl_jpy'].sum():+,.0f} |")
