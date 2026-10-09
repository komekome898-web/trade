"""カード 4 の測定の出力(各 measure/<変種>/)から、目標と比べる表の列を作る。数え方は goal_table2.py と同じ。
使い方: python goal_table_c4.py <変種> ...   出力: 1 行 1 変種の JSON(標準出力)"""
import csv, json, sys
import numpy as np
def _pd(d):  # 1 日あたり(%)。L-920 より前の daily_stats.json は per_day_bp(率 × 1 万)なので / 100
    return d["per_day_pct"] if "per_day_pct" in d else d["per_day_bp"] / 100
def _ci(d):
    return d["per_day_pct"]["ci"] if "per_day_pct" in d else [x / 100 for x in d["per_day_bp"]["ci"]]
def _ci_of(b):
    d = b["per_day_pct"] if "per_day_pct" in b else {k: ([x / 100 for x in v] if k == "ci" else (v / 100 if k == "mde" and v is not None else v)) for k, v in b["per_day_bp"].items()}
    return d
R = 'docs/RESEARCH/cards/c4_owner_matilda_range/measure'
JST = 9 * 3600 * 10**9
for v in sys.argv[1:]:
    d = f'{R}/{v}'
    s = json.load(open(f'{d}/daily_stats.json'))
    z = np.load(f'{d}/run.npz'); o = z['open']; e = np.where(z['decided'], z['exposure'], np.nan); n = len(o)
    r = np.full(n, np.nan); r[:-2] = o[2:] / o[1:-1] - 1; P = np.nan_to_num(e * r * 100)  # %(L-920)
    sv = np.sign(np.nan_to_num(e)); st = np.flatnonzero((sv != 0) & (np.r_[0, sv[:-1]] != sv)); en = np.r_[st[1:], n]
    cP = np.r_[0, np.cumsum(P)]; tp = []; hd = []
    for a, b in zip(st, en):
        seg = sv[a:b] != sv[a]; k = a + np.argmax(seg) if seg.any() else b; tp.append(cP[k] - cP[a]); hd.append(k - a)
    tp = np.array(tp); hd = np.array(hd)
    allrows = list(csv.reader(open(f'{d}/daily.csv'))); rows = allrows[1:]
    k_ = 100.0 if allrows[0][1] == 'pnl_bp' else 1.0  # L-920 より前の daily.csv は率 × 1 万
    p = np.array([float(x[1]) / k_ for x in rows]); cum = np.cumsum(p)
    dd = float((np.maximum.accumulate(np.r_[0, cum]) - np.r_[0, cum]).max())
    m = {}
    for x, q in zip(rows, p): m[x[0][:7]] = m.get(x[0][:7], 0) + q
    mv = np.array(list(m.values())); pd = _pd(s['overall']); nd = len(p)
    out = dict(variant=v, per_day_pct=pd, ci_1d=_ci(s['ci']['block_1d']), ci_5d=_ci(s['ci']['block_5d']),
               mde=_ci_of(s['ci']['block_1d']).get('mde'), trades_per_day=len(tp) / nd, per_trade_pct=float(tp.mean()) if len(tp) else None,
               win=float((tp > 0).mean()) if len(tp) else None, hold_med_min=float(np.median(hd)) if len(hd) else None,
               month_yen=pd * 30.4 / 100 * 600000, max_dd_pct=dd, worst_day_pct=float(p.min()), worst_month_pct=float(mv.min()),
               pos_month=float((mv > 0).mean()), long_pct=float(np.nansum(np.where(e > 0, P, 0))), short_pct=float(np.nansum(np.where(e < 0, P, 0))),
               nonzero=s['frequency']['nonzero_share'], year={y: (_pd(w) if isinstance(w, dict) else w) for y, w in s['year'].items()})
    print(json.dumps(out, ensure_ascii=False))
