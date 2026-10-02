"""Goal-facing stats per card run, from the saved per-bar arrays (no new card runs).
P_t = e_t * (open[t+2]/open[t+1] - 1) * 1e4  (W1 C2), over decided bars."""
import json, glob, os, sys
import numpy as np
S='/tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/w4/measure/runs'
R='/home/user/trade/docs/RESEARCH/cards'
JST=9*3600*10**9
NOTIONAL=600_000  # 資金 30 万円 x 2 倍(計画 1-2 の上側)
out={}
for card in ['c1_xborder_mom','c2_owner_xvenue_wick','c3_yen_premium_revert']:
  for f in sorted(glob.glob(f'{S}/{card}/*.npz')):
    v=os.path.basename(f)[:-4]
    z=np.load(f); o=z['open']; e=np.where(z['decided'],z['exposure'],np.nan); t=z['end_ns']
    n=len(o)
    r=np.full(n,np.nan); r[:-2]=o[2:]/o[1:-1]-1
    def pnl(ex):
      p=ex*r*1e4; return p
    P=pnl(e); ok=~np.isnan(P)
    # 1 bar later (exposure acted on one bar late)
    e1=np.full(n,np.nan); e1[1:]=e[:-1]; P1=pnl(e1); ok1=~np.isnan(P1)
    day=((t+JST)//(86400*10**9))
    days,inv=np.unique(day[ok],return_inverse=True)
    dsum=np.bincount(inv,weights=P[ok])
    cum=np.cumsum(dsum); dd=float((np.maximum.accumulate(cum)-cum).max())
    mon=((t[ok]+JST).astype('datetime64[ns]').astype('datetime64[M]'))
    mu,mi=np.unique(mon,return_inverse=True); msum=np.bincount(mi,weights=P[ok])
    # trades = runs of constant sign != 0
    s=np.sign(np.nan_to_num(e)); s[~z['decided']]=np.nan
    sv=np.nan_to_num(s)
    start=np.flatnonzero((sv!=0)&(np.r_[0,sv[:-1]]!=sv))
    end=np.r_[start[1:],n]
    tp=[]; hold=[]
    cP=np.r_[0,np.cumsum(np.nan_to_num(P))]
    for a,b in zip(start,end):
      k=a+np.argmax(sv[a:b]!=sv[a]) if np.any(sv[a:b]!=sv[a]) else b
      tp.append(cP[k]-cP[a]); hold.append(k-a)
    tp=np.array(tp); hold=np.array(hold)
    longP=np.nansum(np.where(e>0,P,0)); shortP=np.nansum(np.where(e<0,P,0))
    nd=len(days)
    st=json.load(open(f'{R}/{card}/measure/{v}/daily_stats.json')) if os.path.exists(f'{R}/{card}/measure/{v}/daily_stats.json') else None
    out[f'{card}/{v}']=dict(
      n_days=nd, per_day_bp=float(dsum.mean()), check_vs_daily_stats=(st['overall']['per_day_bp'] if st else None),
      ci_day_block=(st['ci']['block_1d']['per_day_bp']['ci'] if st else None),
      gross_month_pct=float(dsum.mean()*30.4/100), gross_month_yen_at_600k=float(dsum.mean()*30.4/1e4*NOTIONAL),
      trades=int(len(tp)), trades_per_day=float(len(tp)/nd), per_trade_bp=float(tp.mean()) if len(tp) else None,
      win_rate=float((tp>0).mean()) if len(tp) else None, median_hold_min=float(np.median(hold)) if len(hold) else None,
      long_sum_bp=float(longP), short_sum_bp=float(shortP),
      max_drawdown_bp=dd, worst_day_bp=float(dsum.min()), worst_month_bp=float(msum.min()),
      positive_month_share=float((msum>0).mean()), daily_sd_bp=float(dsum.std()),
      one_bar_late_per_day_bp=float(np.nansum(P1)/nd))
    print(v, json.dumps(out[f'{card}/{v}'],ensure_ascii=False))
json.dump(out,open('/tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/lead/goal_table.json','w'),ensure_ascii=False,indent=1)
