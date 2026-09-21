"""探索段 2 の反証者レビュー(2026-09-19)の「計算」印の主要な値をリードが再計算する。
入力: backtest_data/o3c_signal_explore2_20260919/rows_gap60.csv.gz + backtest_data/o3c_reaction_20260918_full/gap60_w8/table.csv
"""
import gzip,csv,collections,math,statistics
R='backtest_data/o3c_signal_explore2_20260919/rows_gap60.csv.gz'
def f(x):
    try: return float(x)
    except: return None
rows=[r for r in csv.DictReader(gzip.open(R,'rt')) if r['kind']=='liq']
by=collections.defaultdict(dict)
for r in rows: by[r['cascade_id']][r['delta_sec']]=r
def mse(vd):
    v=[x for x,_ in vd]; n=len(v); m=sum(v)/n
    byday=collections.defaultdict(float)
    for x,d in vd: byday[d]+=x-m
    G=len(byday); return m, math.sqrt(sum(s*s for s in byday.values()))/n*math.sqrt(G/(G-1)), n
# 1. bounce(Δ) vs r_Δ(Δ=0 の行)、bounce+r_60
for d in ('1','5','10','30','60'):
    a=[];b=[];s=[]
    for cid,dd in by.items():
        if d in dd and '0' in dd:
            bo=f(dd[d]['bounce']); r0=f(dd['0'][f'r_{d}']); r60=f(dd[d]['r_60'])
            if None not in (bo,r0,r60): a.append(bo); b.append(r0); s.append(bo+r60)
    n=len(a); ma=sum(a)/n; mb=sum(b)/n
    cov=sum((x-ma)*(y-mb) for x,y in zip(a,b))/n; corr=cov/math.sqrt(sum((x-ma)**2 for x in a)/n*sum((y-mb)**2 for y in b)/n)
    print(f'Δ={d}: bounce 平均 {ma:.4f} / r(0,Δ) 平均 {mb:.4f} / 相関 {corr:.5f} / 平均|差| {sum(abs(x-y) for x,y in zip(a,b))/n:.3f} / bounce+r(Δ,60) 平均 {sum(s)/n:.4f}')
# 2. 次の束が 120 秒以内 (1 周目の表の start/end)
t=[r for r in csv.DictReader(open('backtest_data/o3c_reaction_20260918_full/gap60_w8/table.csv')) if r['kind']=='liq']
t.sort(key=lambda r:(r['day'],int(r['start_ms'])))
nxt={}
for i,r in enumerate(t[:-1]):
    q=t[i+1]
    if q['day']==r['day']: nxt[r['cascade_id']]=(int(q['start_ms'])-int(r['end_ms']), q['side']==r['side'])
    # 日をまたぐ場合は次の日の最初の束まで測る
    else: nxt[r['cascade_id']]=(int(q['start_ms'])-int(r['end_ms']), q['side']==r['side'])
close=[cid for cid,(g,same) in nxt.items() if g<=120_000]
print(f'次の束が 120 秒以内: {len(close)}/{len(t)} = {len(close)/len(t):.4f}、同側 {sum(1 for c in close if nxt[c][1])/len(close):.3f}')
g1=[(f(by[c]['60']['r_60']),by[c]['60']['day']) for c in close if c in by and f(by[c]['60']['r_60']) is not None]
g2=[(f(by[c]['60']['r_60']),by[c]['60']['day']) for c in by if c not in set(close) and f(by[c]['60']['r_60']) is not None]
for name,g in (('120秒以内',g1),('それ以外',g2)):
    m,se,n=mse(g); print(f'  Δ=60 h=60 {name}: {m:+.4f} ± {se:.4f} n={n}')
far=set(c for c,(g,_) in nxt.items() if g>=180_000)
for d,h in (('60','60'),('60','300'),('60','900'),('0','60'),('0','300'),('0','900')):
    g=[(f(by[c][d][f'r_{h}']),by[c][d]['day']) for c in far if c in by and d in by[c] and f(by[c][d][f'r_{h}']) is not None]
    m,se,n=mse(g); print(f'  次の束まで 180 秒以上 Δ={d} h={h}: {m:+.4f} ± {se:.4f} n={n}')
# 3. lag==0 / lag>0(Δ=0 h=60)
a=[(f(by[c]['0']['r_60']),by[c]['0']['day']) for c in by if f(by[c]['0']['anchor_lag_ms'])==0]
b=[(f(by[c]['0']['r_60']),by[c]['0']['day']) for c in by if f(by[c]['0']['anchor_lag_ms'])!=0]
for name,g in (('lag==0',a),('lag>0',b)):
    m,se,n=mse(g); print(f'  Δ=0 h=60 {name}: {m:+.4f} ± {se:.4f} n={n}')
# 4. bitFlyer のちょうど 0 の割合(Δ=0)
for h in ('1','30','60'):
    v=[f(by[c]['0'][f'bf_r_{h}']) for c in by if f(by[c]['0'][f'bf_r_{h}']) is not None]
    print(f'  bitFlyer Δ=0 h={h}: ちょうど 0 の割合 {sum(1 for x in v if x==0)/len(v):.4f} n={len(v)}')
# 5. 台形近似: r(Δ,60) を Δ〜U(0,60) で平均
e1={}
for c in by:
    for d in ('0','1','5','10','30','60'):
        if d in by[c] and f(by[c][d]['r_60']) is not None: e1.setdefault(d,[]).append(f(by[c][d]['r_60']))
pts=[(int(d),sum(v)/len(v)) for d,v in e1.items()]; pts.sort()
area=sum((pts[i+1][0]-pts[i][0])*(pts[i][1]+pts[i+1][1])/2 for i in range(len(pts)-1))/60
print(f'  r(Δ,60) の Δ〜U(0,60) 平均(台形): {area:+.3f} bp')
