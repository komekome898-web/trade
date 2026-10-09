# リードが書いた。委任・批評家を通していない(数えるだけ)。
# 基準にあって本に無い合図(合図の時刻で突き合わせ)のうち、本の取引の 建て〜出 の間に合図の時刻が入る本数
# (= 持ち高の違いで建たなかった合図の上限の目安。分析のスキル D5)。前半・後半の境 2019-12-09。
# 使い方: python3 held_blocked.py <本の名前> [<本の名前> ...]
import sys
import numpy as np
import pandas as pd

R = "backtest_runs_shared/matilda_main_trades/"
CUT = pd.Timestamp("2019-12-09", tz="UTC")


def load(name):
    t = pd.read_csv(R + name + "/trades.csv.gz")
    for c in ("signal_t", "entry_t", "exit_t"):
        t[c] = pd.to_datetime(t[c], utc=True)
    return t


base = load("base")
print("| 本 | 区切り | 基準だけの合図 | うち本の持ち高の間 | 割合 | その和(円) |")
print("|---|---|---|---|---|---|")
for name in sys.argv[1:]:
    run = load(name)
    only = base[~base["signal_t"].isin(set(run["signal_t"]))]
    r = run.sort_values("entry_t")
    ent = r["entry_t"].to_numpy()
    ext = r["exit_t"].to_numpy()
    s = only["signal_t"].to_numpy()
    i = np.searchsorted(ent, s, side="right") - 1
    held = (i >= 0) & (s < ext[np.clip(i, 0, None)])
    for lab, m in (("前半", only["signal_t"] < CUT), ("後半", only["signal_t"] >= CUT)):
        m = m.to_numpy()
        n, h = int(m.sum()), int((m & held).sum())
        print(f"| {name} | {lab} | {n:,} | {h:,} | {h / max(n, 1):.1%} | {only['pnl_jpy'].to_numpy()[m & held].sum():+,.0f} |")

