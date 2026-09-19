"""反証者レビュー(2026-09-19、SIGNAL 探索段)の「計算」印の主要な値をリードが再計算する。
入力: backtest_data/o3c_reaction_20260918_full/gap60_w8/table.csv(+ gap30_w8 / gap180_w8 の清算行)。
"""
import csv, math, statistics, collections, sys
P='backtest_data/o3c_reaction_20260918_full/'
def f(x):
    try: return float(x)
    except: return None
rows=list(csv.DictReader(open(P+'gap60_w8/table.csv')))
side={r['liq_id'] if 'liq_id' in r else r.get('id'):r['side'] for r in rows if r['kind']=='liq'}
liq=[r for r in rows if r['kind']=='liq']; cm=[r for r in rows if r['kind']=='control_matched']; cu=[r for r in rows if r['kind']=='control_uniform']
print('行数 liq/control_matched/control_uniform =',len(liq),len(cm),len(cu))
# 1. anchor_lag_ms==0 の割合
for name,g in (('liq',liq),('control_matched',cm),('control_uniform',cu)):
    lags=[f(r['anchor_lag_ms']) for r in g]; lags=[x for x in lags if x is not None]
    print(f'{name}: lag==0 割合 {sum(1 for x in lags if x==0)/len(lags):.4f}  中央値 {statistics.median(lags):.1f} ms')
# 2. 清算側の h 形状(平均・日クラスタ SE)
def mean_se_cluster(vals_days):
    v=[x for x,_ in vals_days]; n=len(v); m=sum(v)/n
    byday=collections.defaultdict(float)
    for x,d in vals_days: byday[d]+=x-m
    G=len(byday); se=math.sqrt(sum(s*s for s in byday.values()))/n*math.sqrt(G/(G-1))
    return m,se,n,G
print('清算側 平均 ± 日クラスタSE / naive SE')
r1={}
for h in (1,5,15,30,60,240):
    vd=[(f(r[f'bp_{h}m_reactdir']),r['day']) for r in liq if f(r[f'bp_{h}m_reactdir']) is not None]
    m,se,n,G=mean_se_cluster(vd); sd=statistics.pstdev([x for x,_ in vd]); print(f'  h={h}: {m:.3f} ± {se:.3f} (naive {sd/math.sqrt(n):.3f}) n={n} 日={G}')
# r240 - r1 (同じ行)
for h in (5,15,240):
    vd=[(f(r[f'bp_{h}m_reactdir'])-f(r['bp_1m_reactdir']),r['day']) for r in liq if f(r[f'bp_{h}m_reactdir']) is not None and f(r['bp_1m_reactdir']) is not None]
    m,se,n,G=mean_se_cluster(vd); print(f'  r{h}-r1 = {m:.3f} ± {se:.3f}(日クラスタ) n={n}')
# 3. 幅 0・単発の束
w0=[r for r in liq if f(r['bundle_width_ms'])==0 and f(r['bundle_n_events_dedup'])==1]
v=[f(r['bp_1m_reactdir']) for r in w0 if f(r['bp_1m_reactdir']) is not None]
print(f'幅0・単発 n={len(w0)} ({len(w0)/len(liq):.4f}) 1分平均 {sum(v)/len(v):.3f}')
# 4. 対照(一様)の日平均に束の符号 → h=240
sgn=lambda s: -1.0 if s=='SELL' else 1.0
liq_by_day=collections.defaultdict(list)
for r in liq: liq_by_day[r['day']].append(sgn(r['side']))
# 対照 (i) 一様: 生の bp 列名を確認
raw=[c for c in rows[0].keys() if c.startswith('bp_240m') and 'reactdir' not in c]
print('生の 240m 列:',raw)
cu_day=collections.defaultdict(list)
for r in cu:
    x=f(r[raw[0]])
    if x is not None: cu_day[r['day']].append(x)
acc=[]
for r in liq:
    d=r['day']
    if cu_day.get(d): acc.append(-sgn(r['side'])*sum(cu_day[d])/len(cu_day[d]))  # reactdir = -bp*(SELL:+1,BUY:-1) = bp*sgn? 確認用に両符号を出す
print(f'対照(一様) 日平均×束の符号 h=240: {sum(acc)/len(acc):+.3f}(符号の向きは下の対照(ii)と同じ定義に合わせて読む)')
# 対照 (ii) の h=240 平均(道具の定義: 相手の side を借りる)
cm240=[f(r['bp_240m_reactdir']) for r in cm if f(r['bp_240m_reactdir']) is not None]
print(f'対照(ii) h=240 reactdir 平均 {sum(cm240)/len(cm240):+.3f} n={len(cm240)}')
# 5. bitFlyer の反応(清算側)
for h in (1,5,15):
    v=[f(r[f'bf_bp_{h}m_reactdir']) for r in liq if f(r[f'bf_bp_{h}m_reactdir']) is not None]
    print(f'bitFlyer 清算側 h={h}: 平均 {sum(v)/len(v):.3f} n={len(v)}')
# 6. gap 感度(清算側 1 分)
for g in ('gap30_w8','gap180_w8'):
    v=[f(r['bp_1m_reactdir']) for r in csv.DictReader(open(P+g+'/table.csv')) if r['kind']=='liq' and f(r['bp_1m_reactdir']) is not None]
    print(f'{g} 清算側 1分平均 {sum(v)/len(v):.3f} 反転割合 {sum(1 for x in v if x<0)/len(v):.3f} n={len(v)}')
# 7. 対照が付かなかった清算
has=set(r['matched_liq_id'] for r in cm if r.get('matched_liq_id'))
idcol='liq_id' if 'liq_id' in liq[0] else [c for c in liq[0] if c.endswith('id')][0]
print('id 列:',idcol)
no=[f(r['bp_1m_reactdir']) for r in liq if r[idcol] not in has]; yes=[f(r['bp_1m_reactdir']) for r in liq if r[idcol] in has]
print(f'対照なし n={len(no)} 1分平均 {sum(no)/len(no):.3f} / 対照あり n={len(yes)} 1分平均 {sum(yes)/len(yes):.3f}')
# 8. タイ
for name,g in (('liq',liq),('cm',cm)):
    v=[f(r['bp_1m_reactdir']) for r in g if f(r['bp_1m_reactdir']) is not None]
    print(f'{name} 1分 r==0 割合 {sum(1 for x in v if x==0)/len(v):.4f}')
