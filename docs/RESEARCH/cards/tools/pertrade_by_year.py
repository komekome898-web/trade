"""年ごとの取引の回数・1 取引あたり・勝率・中央値・保有(カード 2 と カード 1 の「なぜ」の診断、diag_leadlag/README.md と diag_why/README.md)。
使い方: python pertrade_by_year.py <run の npz> [...]
npz は測定の走らせで保存した 1 分ごとの記録(open・exposure・decided・end_ns)。カード 2 の (a)(b)(c) とカード 1 の npz はリポジトリに入れていない
(大きいので。各 measure/README.md の走らせ方で作り直せる)。
取引 = 持ち高の向き(符号)が続いた区間。1 取引の損益 = その区間の P_t の合計(P_t = e_t × (open_{t+2}/open_{t+1} − 1) × 100、%。L-920 で bp は値動き率だけの名前)。1 分の値動きは値動き率(bp)。
年 = 取引の始まりの日本時間の年。1 日あたりの回数の分母 = その年に決定のある日本時間の日の数。
"""
import sys
import numpy as np

JST = 9 * 3600 * 10**9
for path in sys.argv[1:]:
    z = np.load(path)
    o = z['open']; e = np.where(z['decided'], z['exposure'], np.nan); t = z['end_ns']; n = len(o)
    r = np.full(n, np.nan); r[:-2] = o[2:] / o[1:-1] - 1; P = np.nan_to_num(e * r * 100)
    sv = np.sign(np.nan_to_num(e)); st = np.flatnonzero((sv != 0) & (np.r_[0, sv[:-1]] != sv)); en = np.r_[st[1:], n]
    cP = np.r_[0, np.cumsum(P)]; tp = []; ts = []; hd = []
    for a, b in zip(st, en):
        seg = sv[a:b] != sv[a]; k = a + np.argmax(seg) if seg.any() else b
        tp.append(cP[k] - cP[a]); ts.append(t[a]); hd.append(k - a)
    tp = np.array(tp); hd = np.array(hd)
    yr = ((np.array(ts) + JST) // 10**9).astype('datetime64[s]').astype('datetime64[Y]').astype(int) + 1970
    dy = ((t + JST) // 10**9).astype('datetime64[s]').astype('datetime64[D]'); dyy = dy.astype('datetime64[Y]').astype(int) + 1970
    lr = np.abs(np.diff(np.log(o))); lyy = dyy[1:]
    print(path)
    for y in np.unique(yr):
        m = yr == y; nd = len(np.unique(dy[dyy == y]))
        print(f'  {y} trades/day {m.sum()/nd:5.1f} per_trade(%) {tp[m].mean():8.4f} win {(tp[m]>0).mean():.2f} '
              f'median(%) {np.median(tp[m]):8.4f} hold_med {np.median(hd[m]):5.0f} mean|1m move| {np.nanmean(lr[lyy==y])*1e4:5.2f}bp')
