import json, glob, os
import numpy as np
S='/tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/w4/measure/runs/c2_owner_xvenue_wick'
R='/home/user/trade/docs/RESEARCH/cards'
JST=9*3600*10**9; NOTIONAL=600_000
files=[(f'c2_owner_xvenue_wick/{os.path.basename(f)[:-4]}',f) for f in sorted(glob.glob(f'{S}/[bc]_*.npz'))]
files+=[(f'{c}/{v}',f'{R}/{c}/measure/{v}/run.npz') for c,vs in [('c5_tokyo_fix_momentum',['default']),('c6_weekend_gap_revert',['usdjpy','btc']),('c7_barrier_race',['1h','1d','1w']),('c8_session_mean_revert',['jst_day','bf_maint'])] for v in vs]
out={}
for key,f in files:
    z=np.load(f); o=z['open']; dec=z['decided']; e=np.where(dec,z['exposure'],np.nan); t=z['end_ns']; n=len(o)
    r=np.full(n,np.nan); r[:-2]=o[2:]/o[1:-1]-1; P=e*r*1e4; ok=~np.isnan(P)
    day=(t+JST)//(86400*10**9); days,inv=np.unique(day[ok],return_inverse=True); dsum=np.bincount(inv,weights=P[ok])
    cum=np.cumsum(dsum); dd=float((np.maximum.accumulate(cum)-cum).max())
    mon=(t[ok]+JST).astype('datetime64[ns]').astype('datetime64[M]'); mu,mi=np.unique(mon,return_inverse=True); msum=np.bincount(mi,weights=P[ok])
    sv=np.sign(np.nan_to_num(e)); start=np.flatnonzero((sv!=0)&(np.r_[0,sv[:-1]]!=sv)); end=np.r_[start[1:],n]
    cP=np.r_[0,np.cumsum(np.nan_to_num(P))]; tp=[];hold=[]
    for a,b in zip(start,end):
        seg=sv[a:b]!=sv[a]; k=a+np.argmax(seg) if seg.any() else b
        tp.append(cP[k]-cP[a]); hold.append(k-a)
    tp=np.array(tp); hold=np.array(hold); nd=len(days)
    st=f'{R}/{key.split("/")[0]}/measure/{key.split("/")[1]}/daily_stats.json'
    s=json.load(open(st)) if os.path.exists(st) else None
    out[key]=dict(per_day_bp=float(dsum.mean()),check=(s['overall']['per_day_bp'] if s else None),ci=(s['ci']['block_1d']['per_day_bp']['ci'] if s else None),
        trades_per_day=len(tp)/nd,per_trade_bp=float(tp.mean()) if len(tp) else None,win=float((tp>0).mean()) if len(tp) else None,hold=float(np.median(hold)) if len(hold) else None,
        month_yen=float(dsum.mean()*30.4/1e4*NOTIONAL),dd=dd,worst_month=float(msum.min()),pos_month=float((msum>0).mean()),
        long=float(np.nansum(np.where(e>0,P,0))),short=float(np.nansum(np.where(e<0,P,0))),n_days=nd)
    print(key,json.dumps({k:(round(v,2) if isinstance(v,float) else v) for k,v in out[key].items()},ensure_ascii=False))
json.dump(out,open('/tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/lead/goal_table2.json','w'),ensure_ascii=False,indent=1)
