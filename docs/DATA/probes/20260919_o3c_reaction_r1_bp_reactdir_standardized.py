"""L-233 への答え: 1 周目の判定の表(gap60_w8)から、D1 の bp_reactdir を距離の 10 分位でそろえて対照 C と比べる。観測であって判定ではない(事前登録の外)。"""
import pandas as pd, numpy as np
H=[1,5,15,30,60,240]; cut=-14472.33333333332
t=pd.read_csv('backtest_data/o3c_reaction_20260918_full/gap60_w8/table.csv', usecols=['kind','cascade_id','matched_liq_id','side','doi_pre_1h','dist_vwap_bp']+[f'bp_{h}m' for h in H]+[f'bp_{h}m_reactdir' for h in H])
mixed=set(pd.read_csv('backtest_data/o3c_reaction_20260918_full/gap60_w8/table_mixed.csv', usecols=['cascade_id'])['cascade_id'])
liq=t[t['kind']=='liq']; d1=liq[liq['doi_pre_1h']<=cut].copy()
side=dict(zip(liq['cascade_id'], liq['side']))
c=t[(t['kind']=='control_matched')&(t['doi_pre_1h']<=cut)&(~t['matched_liq_id'].isin(mixed))].copy()
sgn=c['matched_liq_id'].map(side).map({'SELL':-1.0,'BUY':1.0})
for h in H: c[f'r_{h}']=c[f'bp_{h}m']*sgn; d1[f'r_{h}']=d1[f'bp_{h}m_reactdir']
print('D1', len(d1), '/ 対照 C', len(c))
ad=np.abs(d1['dist_vwap_bp']); ac=np.abs(c['dist_vwap_bp'])
edges=list(np.nanpercentile(ad, np.linspace(0,100,11))); edges[0]=0; edges[-1]=1e9
rng=np.random.default_rng(1)
print('h   D1平均   C平均(生)  差(生)   SE(生)   C平均(距離をそろえた) 差(そろえた)  SE(ブートストラップ1000)  D1で反転の割合  Cで反転の割合')
for h in H:
    x=d1[f'r_{h}'].to_numpy(); y=c[f'r_{h}'].to_numpy()
    mx=np.nanmean(x); my=np.nanmean(y); se=np.sqrt(np.nanvar(x,ddof=1)/np.sum(~np.isnan(x))+np.nanvar(y,ddof=1)/np.sum(~np.isnan(y)))
    # 標準化
    def std_diff(xv, yv, adv, acv):
        num=0; den=0
        for i in range(10):
            ml=(adv>=edges[i])&(adv<edges[i+1])&~np.isnan(xv); mc=(acv>=edges[i])&(acv<edges[i+1])&~np.isnan(yv)
            w=ml.sum(); num+=w*(np.mean(xv[ml])-np.mean(yv[mc])); den+=w
        return num/den
    d_std=std_diff(x,y,ad.to_numpy(),ac.to_numpy())
    boots=[]
    for _ in range(1000):
        ix=rng.integers(0,len(x),len(x)); iy=rng.integers(0,len(y),len(y))
        boots.append(std_diff(x[ix],y[iy],ad.to_numpy()[ix],ac.to_numpy()[iy]))
    print(f'{h:>3} {mx:+7.2f}  {my:+7.2f}   {mx-my:+7.2f}  {se:6.2f}   {mx-d_std:+7.2f}              {d_std:+7.2f}      {np.std(boots,ddof=1):6.2f}                 {np.nanmean(x<0):.3f}          {np.nanmean(y<0):.3f}')
