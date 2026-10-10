"""earn_loss_map.out で前半・後半とも同じ並びだった 2 つ(1 段目の値段から中心までの距離 ÷ 幅 が深い・日本時間 04〜12 時を避ける)を、
基準の取引の部分集合で重ねる。走らせではない(建てなかった分で持ち高が空いて建つ別の取引は入らない)ので、目安の点の値と区間。
区間の決まりは earn_loss_map.py と同じ。【試験の無い台本の値】
    python3 docs/RESEARCH/matilda_main/stage2/earn_loss_combo.py <base の lines.csv> > docs/RESEARCH/matilda_main/stage2/earn_loss_combo.out
"""
import sys
import numpy as np
import pandas as pd

CUT = "2019-12-09"
DAYS = {"前半": pd.date_range("2015-12-01", "2019-12-08"), "後半": pd.date_range(CUT, "2023-12-17")}
rng = np.random.default_rng(20261004)


def ci(daily, days):
    v = daily.reindex(days.strftime("%Y-%m-%d"), fill_value=0).to_numpy()
    n, b = len(v), 5
    st = rng.integers(0, n, size=(1000, int(np.ceil(n / b))))
    idx = (st[:, :, None] + np.arange(b)).reshape(1000, -1)[:, :n] % n
    m = v[idx].mean(axis=1)
    return f"{v.mean():+.1f} [{np.percentile(m, 2.5):+.1f}, {np.percentile(m, 97.5):+.1f}]"


t = pd.read_csv("backtest_runs_shared/matilda_main_trades/base/trades.csv.gz")
t["entry_t"] = pd.to_datetime(t.entry_t, utc=True)
ln = pd.read_csv(sys.argv[1])
ln["entry_t"] = pd.to_datetime(ln.start + 60_000_000_000, utc=True)
t = t.merge(ln.drop(columns=["side"]), on="entry_t", how="left")
t["day"] = t.signal_t.str[:10]
t["half"] = np.where(t.day >= CUT, "後半", "前半")
t["dev"] = (t.side * (t.center - t.px)) / t.width
h = (t.entry_t.dt.hour + 9) % 24
deep, morn = t.dev >= 0.49, (h >= 4) & (h < 12)
print("| 部分集合 | 前半 本 | 前半 円/日 [区間] | 後半 本 | 後半 円/日 [区間] |")
print("|---|---|---|---|---|")
for lab, m in (("全部", t.dev.notna()), ("深い(≥ 0.49 幅)", deep), ("04〜12 時を避ける", ~morn), ("深い かつ 04〜12 時を避ける", deep & ~morn)):
    r = [lab]
    for hh in ("前半", "後半"):
        x = t[m & (t.half == hh)]
        r += [f"{len(x):,}", ci(x.groupby("day").pnl_jpy.sum(), DAYS[hh])]
    print("| " + " | ".join(r) + " |")
