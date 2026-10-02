"""取引ごとの勝ち・負け・0 の割合と、勝ち・負けそれぞれの平均(W4_overnight_RESULTS.md の「勝ち負けの形」)。
使い方: python winloss_shape.py <run の npz> [...]。取引の数え方は goal_table2.py と同じ。"""
import sys
import numpy as np
for path in sys.argv[1:]:
    z = np.load(path); o = z['open']; e = np.where(z['decided'], z['exposure'], np.nan); n = len(o)
    r = np.full(n, np.nan); r[:-2] = o[2:] / o[1:-1] - 1; P = np.nan_to_num(e * r * 1e4)
    sv = np.sign(np.nan_to_num(e)); st = np.flatnonzero((sv != 0) & (np.r_[0, sv[:-1]] != sv)); en = np.r_[st[1:], n]
    cP = np.r_[0, np.cumsum(P)]; tp = []
    for a, b in zip(st, en):
        seg = sv[a:b] != sv[a]; k = a + np.argmax(seg) if seg.any() else b; tp.append(cP[k] - cP[a])
    tp = np.array(tp)
    print(path, 'n', len(tp), 'zero', round((tp == 0).mean(), 3), 'win', round((tp > 0).mean(), 3), 'loss', round((tp < 0).mean(), 3),
          'win_mean', round(tp[tp > 0].mean(), 2), 'loss_mean', round(tp[tp < 0].mean(), 2))
