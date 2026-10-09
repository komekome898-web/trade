"""カード 4: 約定の遅れの診断(L-576)。gate_diag.py の probe.npz を読む。

門の無いカードの持ち高 e_t を、(1) W1 の測定器どおり次の足の始値から次の次の足の始値まで持つ P と、
(2) 判定した足の終値から次の足の終値まで持つ P(判定した値段でそのまま約定した場合 = 遅れ 0 の上限)を、
日本時間の年ごとの 1 日あたりで並べる。(2) は終値の跳ね(売買の向きで終値が買値・売値に寄る)を含むので甘い側。
    python3 fill_delay.py <probe.npz の置き場>
"""
import sys

import numpy as np

z = np.load(sys.argv[1] + "/probe.npz")
# 損益は %(L-920 で bp は値動き率だけの名前)。L-920 より前の probe.npz は pnl_bp(率 × 1 万)なので / 100
bt, e = z["bar_t"], z["exposure"]
P = z["pnl_pct"] if "pnl_pct" in z.files else z["pnl_bp"] / 100
rt, c = z["rec_t"], z["close"]
idx = np.searchsorted(bt, rt)
ok = (idx < len(bt)) & (bt[np.minimum(idx, len(bt) - 1)] == rt)
cl = np.full(len(bt), np.nan)
cl[idx[ok]] = c[ok]
Pcc = e[:-1] * (cl[1:] / cl[:-1] - 1) * 100
m = np.isfinite(Pcc)
JST, DAY = 9 * 3600 * 10**9, 86400 * 10**9
day = (bt[:-1] + JST) // DAY
yrs = np.array([np.datetime64(int(d), "D").astype(object).year for d in day])
print("年 次の始値(W1) 判定の終値(遅れ0)  (1 日あたり、%)")
for y in sorted(set(yrs.tolist())):
    k = (yrs == y) & m
    nd = len(np.unique(day[k]))
    print(y, round(P[:-1][k].sum() / nd, 3), round(Pcc[k].sum() / nd, 3))
nd = len(np.unique(day[m]))
print("全期間", round(P[:-1][m].sum() / nd, 3), round(Pcc[m].sum() / nd, 3))
