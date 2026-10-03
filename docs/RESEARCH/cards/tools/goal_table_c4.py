"""カード 4 の測定の出力(各 measure/<変種>/)から、目標と比べる表の列を作る。数え方は goal_table2.py と同じ。
使い方: python goal_table_c4.py <変種> ...   出力: 1 行 1 変種の JSON(標準出力)"""
import csv, json, sys
import numpy as np
R = 'docs/RESEARCH/cards/c4_owner_matilda_range/measure'
JST = 9 * 3600 * 10**9
for v in sys.argv[1:]:
    d = f'{R}/{v}'
    s = json.load(open(f'{d}/daily_stats.json'))
    z = np.load(f'{d}/run.npz'); o = z['open']; e = np.where(z['decided'], z['exposure'], np.nan); n = len(o)
    r = np.full(n, np.nan); r[:-2] = o[2:] / o[1:-1] - 1; P = np.nan_to_num(e * r * 1e4)
    sv = np.sign(np.nan_to_num(e)); st = np.flatnonzero((sv != 0) & (np.r_[0, sv[:-1]] != sv)); en = np.r_[st[1:], n]
    cP = np.r_[0, np.cumsum(P)]; tp = []; hd = []
    for a, b in zip(st, en):
        seg = sv[a:b] != sv[a]; k = a + np.argmax(seg) if seg.any() else b; tp.append(cP[k] - cP[a]); hd.append(k - a)
    tp = np.array(tp); hd = np.array(hd)
    rows = list(csv.reader(open(f'{d}/daily.csv')))[1:]
    p = np.array([float(x[1]) for x in rows]); cum = np.cumsum(p)
    dd = float((np.maximum.accumulate(np.r_[0, cum]) - np.r_[0, cum]).max())
    m = {}
    for x, q in zip(rows, p): m[x[0][:7]] = m.get(x[0][:7], 0) + q
    mv = np.array(list(m.values())); pd = s['overall']['per_day_bp']; nd = len(p)
    out = dict(variant=v, per_day_bp=pd, ci_1d=s['ci']['block_1d']['per_day_bp']['ci'], ci_5d=s['ci']['block_5d']['per_day_bp']['ci'],
               mde=s['ci']['block_1d']['per_day_bp'].get('mde'), trades_per_day=len(tp) / nd, per_trade_bp=float(tp.mean()) if len(tp) else None,
               win=float((tp > 0).mean()) if len(tp) else None, hold_med_min=float(np.median(hd)) if len(hd) else None,
               month_yen=pd * 30.4 / 1e4 * 600000, max_dd_bp=dd, worst_day_bp=float(p.min()), worst_month_bp=float(mv.min()),
               pos_month=float((mv > 0).mean()), long_bp=float(np.nansum(np.where(e > 0, P, 0))), short_bp=float(np.nansum(np.where(e < 0, P, 0))),
               nonzero=s['frequency']['nonzero_share'], year={y: (w['per_day_bp'] if isinstance(w, dict) else w) for y, w in s['year'].items()})
    print(json.dumps(out, ensure_ascii=False))
