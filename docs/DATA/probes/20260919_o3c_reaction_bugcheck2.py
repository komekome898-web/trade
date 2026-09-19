"""報告の再監査(2026-09-19)の指摘 1・3・7 への答え: 判定の道具の D1 対照 (ii) を生の表から再構成し、距離の分布をそろえて比べる。判定には触れない。"""
import pandas as pd, numpy as np
t=pd.read_csv('backtest_data/o3c_reaction_20260918_full/gap60_w8/table.csv', usecols=['kind','cascade_id','matched_liq_id','doi_pre_1h','dist_vwap_bp','reach_back_vwap_240m'])
mixed=set(pd.read_csv('backtest_data/o3c_reaction_20260918_full/gap60_w8/table_mixed.csv', usecols=['cascade_id'])['cascade_id'])
cut=-14472.33333333332
d1=t[(t['kind']=='liq')&(t['doi_pre_1h']<=cut)]
c_all=t[(t['kind']=='control_matched')&(t['doi_pre_1h']<=cut)]
c1=c_all[~c_all['matched_liq_id'].isin(mixed)]; c2=c1[~c1['reach_back_vwap_240m'].isna()]
print('D1 対照(ii): 切り値だけ', len(c_all), '/ 相手が mixed の束を除く', len(c1), '/ 240 分の到達が NaN を除く', len(c2), '/ 判定の道具の n2 = 4101')
print('D1 清算 240 分到達 n', int(d1['reach_back_vwap_240m'].notna().sum()), '平均', round(float(d1['reach_back_vwap_240m'].mean()),6), '/ 判定の道具(f1_12cells.csv) 0.471276')
print('D1 対照(ii) 240 分到達 平均', round(float(c2['reach_back_vwap_240m'].mean()),6), '/ 判定の道具 0.536698')
ad=np.abs(d1['dist_vwap_bp'].to_numpy()); ac=np.abs(c2['dist_vwap_bp'].to_numpy()); rl=d1['reach_back_vwap_240m'].to_numpy(); rc=c2['reach_back_vwap_240m'].to_numpy()
for name,edges in (('5 帯',[0,10,25,50,100,1e9]),('清算の距離の 10 分位',None)):
    if edges is None:
        edges=list(np.nanpercentile(ad, np.linspace(0,100,11))); edges[0]=0; edges[-1]=1e9
    num=den=0; rows=[]
    for i in range(len(edges)-1):
        ml=(ad>=edges[i])&(ad<edges[i+1]); mc=(ac>=edges[i])&(ac<edges[i+1])
        pl=float(np.nanmean(rl[ml])); pc=float(np.nanmean(rc[mc])); w=int(ml.sum()); num+=pc*w; den+=w
        rows.append(f'{edges[i]:.1f}〜: 清算 {pl:.3f}(n {w}) 対照 {pc:.3f}(n {int(mc.sum())})')
    print(f'{name}: 清算の距離分布で加重した対照の到達率 {num/den:.3f} vs 清算 {np.nanmean(rl):.3f} → 距離をそろえた差 {np.nanmean(rl)-num/den:+.3f}(そろえる前 {np.nanmean(rl)-np.nanmean(rc):+.3f})')
    for r in rows: print('   ', r)
