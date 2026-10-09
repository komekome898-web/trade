"""監査の後の診断(関門 ② は未通過)。W4_batch2_LEAD_REVIEW.md の約束: c6 = 窓の大きさの 3 分位ごとの損益、c8 = 回帰の時間の形。"""
import json, numpy as np
R='/home/user/trade/docs/RESEARCH/cards'
out={}
def P_of(z):
    o=z['open']; e=np.where(z['decided'],z['exposure'],np.nan); n=len(o)
    r=np.full(n,np.nan); r[:-2]=o[2:]/o[1:-1]-1; return np.nan_to_num(e*r*100), np.nan_to_num(e)  # P は %(L-920 で bp は値動き率だけの名前)
# c6
for v in ['usdjpy','btc']:
    z=np.load(f'{R}/c6_weekend_gap_revert/measure/{v}/run.npz'); P,e=P_of(z); t=z['end_ns']
    d=json.load(open(f'{R}/c6_weekend_gap_revert/measure/{v}/diagnostics.json'))['per_week']
    r=np.array(d['r_ns'],dtype=np.int64); g=np.array(d['g_usdjpy'])
    wk=np.searchsorted(r,t,side='right')-1; held=(e!=0)&(wk>=0)
    Pw=np.bincount(wk[held],weights=P[held],minlength=len(r))
    a=np.abs(g); q=np.quantile(a,[1/3,2/3]); grp=np.digitize(a,q)
    res={}
    for k,name in enumerate(['小','中','大']):
        m=grp==k; res[name]={'weeks':int(m.sum()),'abs_gap_bp_range':[float(a[m].min()*1e4),float(a[m].max()*1e4)],'sum_pct':float(Pw[m].sum()),'per_week_pct':float(Pw[m].mean()),'win':float((Pw[m]>0).mean())}
    res['check_total_sum_pct']=float(Pw.sum()); res['npz_total_P_pct']=float(P.sum())
    out[f'c6_{v}']=res; print('c6',v,json.dumps(res,ensure_ascii=False))
# c8
for v in ['jst_day','bf_maint']:
    z=np.load(f'{R}/c8_session_mean_revert/measure/{v}/run.npz'); c=z['close']; o=z['open']; e=np.nan_to_num(np.where(z['decided'],z['exposure'],0)); n=len(c)
    sv=np.sign(e); st=np.flatnonzero((sv!=0)&(np.r_[0,sv[:-1]]!=sv))
    st=st[st+62<n]
    # 建てた足の次の足の始値(約定)からの、向きをつけた値動き(bp)。k 本後の始値まで。
    base=o[st+1]; s=sv[st]; res={}
    for k in (1,2,3,5,10,20,30,60):
        mv=s*(o[st+1+k]/base-1)*1e4; res[k]={'mean_bp':float(np.nanmean(mv)),'median_bp':float(np.nanmedian(mv)),'share_pos':float(np.nanmean(mv>0))}
    out[f'c8_{v}']={'n_entries':int(len(st)),'by_k_bars':res}
    print('c8',v,len(st),{k:round(x['mean_bp'],2) for k,x in res.items()})
json.dump(out,open('/tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/w4/diag/c6c8.json','w'),ensure_ascii=False,indent=1)
