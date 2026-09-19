"""段 A 出力の不変条件の検査(L-231「なんでないって言えない？」への答えの根拠)。判定には触れない。"""
import pandas as pd, numpy as np
H=[1,5,15,30,60,240]
def load(p):
    cols=['kind','cascade_id','side','p_liq','doi_pre_1h','dist_vwap_bp','dist_node_bp','p_tgt_back_vwap','reach_back_vwap_sec']+[f'reach_back_vwap_{h}m' for h in H]+[f'bp_{h}m' for h in H]+[f'bp_{h}m_reactdir' for h in H]+[f'mfe_{h}m_reactdir' for h in H]+[f'mae_{h}m_reactdir' for h in H]
    return pd.read_csv(p, usecols=cols)
t8=load('backtest_data/o3c_reaction_20260918_full/gap60_w8/table.csv'); t24=load('backtest_data/o3c_reaction_20260918_full/gap60_w24/table.csv')
print('kind の内訳 W8', t8['kind'].value_counts().to_dict(), '/ W24', t24['kind'].value_counts().to_dict())
for name,t in (('W8',t8),('W24',t24)):
    liq=t[t['kind']=='liq']
    r=liq[[f'reach_back_vwap_{h}m' for h in H]].to_numpy(); mono=bool(np.all((np.diff(r,axis=1)>=0) | np.isnan(np.diff(r,axis=1))))
    sec=liq['reach_back_vwap_sec'].to_numpy(); bad=0
    for h in H:
        col=liq[f'reach_back_vwap_{h}m'].to_numpy(); m=~np.isnan(col)&~np.isnan(sec)
        bad+=int(np.sum((col[m]==1)!=(sec[m]<=h*60))); m2=~np.isnan(col)&np.isnan(sec); bad+=int(np.sum(col[m2]==1))
    d=liq['dist_vwap_bp'].to_numpy(); pt=liq['p_tgt_back_vwap'].to_numpy(); pl=liq['p_liq'].to_numpy(); m=~np.isnan(d)&~np.isnan(pt)
    rel=float(np.nanmax(np.abs(pt[m]/pl[m]-1-d[m]/1e4)))
    s=np.where(liq['side'].to_numpy()=='SELL',1,-1)
    sg=float(np.nanmax(np.abs(liq['bp_240m_reactdir'].to_numpy()+liq['bp_240m'].to_numpy()*s)))
    mfe=liq['mfe_240m_reactdir'].to_numpy(); mae=liq['mae_240m_reactdir'].to_numpy(); bpr=liq['bp_240m_reactdir'].to_numpy(); m=~np.isnan(mfe)&~np.isnan(mae)&~np.isnan(bpr)
    bounds=int(np.sum((mfe[m]<bpr[m]-1e-6)|(mae[m]>bpr[m]+1e-6)|(mfe[m]<-1e-6)|(mae[m]>1e-6)))
    print(f'{name}: 清算行 {len(liq)} / 到達の h 単調 {mono} / 到達秒と h の食い違い {bad} 行 / 目標価格=p_liq×(1+dist/1e4) の最大ずれ {rel:.2e} / reactdir = −bp×(SELL:+1,BUY:−1) の最大ずれ {sg:.2e} / mfe≥bp≥mae, mfe≥0≥mae の破れ {bounds} 行')
    ad=np.abs(d); rr=liq['reach_back_vwap_240m'].to_numpy(); bins=[0,10,25,50,100,1e9]
    print(f'   |dist_vwap_bp| の分位(清算行): 25% {np.nanpercentile(ad,25):.1f} / 50% {np.nanpercentile(ad,50):.1f} / 75% {np.nanpercentile(ad,75):.1f} bp / 240 分の到達率 {np.nanmean(rr):.3f}')
    print('   |dist| の帯ごとの 240 分到達率:', {f'{bins[i]}-{bins[i+1] if bins[i+1]<1e9 else "∞"}': (int(np.sum((ad>=bins[i])&(ad<bins[i+1]))), round(float(np.nanmean(rr[(ad>=bins[i])&(ad<bins[i+1])])),3)) for i in range(len(bins)-1)})
a=set(t8.loc[t8['kind']=='liq','cascade_id']); b=set(t24.loc[t24['kind']=='liq','cascade_id']); print('清算の束の集合 W8 と W24: 同一', a==b, '/ 数', len(a), len(b))
m=t8[t8['kind']=='liq'].merge(t24[t24['kind']=='liq'], on='cascade_id', suffixes=('_8','_24'))
print('同じ束で p_liq・side・bp_240m が同一:', bool((m['p_liq_8']==m['p_liq_24']).all()), bool((m['side_8']==m['side_24']).all()), float(np.nanmax(np.abs(m['bp_240m_8']-m['bp_240m_24']))))
print('同じ束で |dist_vwap| の中央値 W8', float(np.nanmedian(np.abs(m['dist_vwap_bp_8']))), '/ W24', float(np.nanmedian(np.abs(m['dist_vwap_bp_24']))), '/ W24 の方が遠い割合', float(np.nanmean(np.abs(m['dist_vwap_bp_24'])>np.abs(m['dist_vwap_bp_8']))))
print('=== 出発点の距離(W8) ===')
t=t8; cut=-14472.33333333332
for k in ('liq','control_matched','control_uniform'):
    s=t[t['kind']==k]; ad=np.abs(s['dist_vwap_bp']); an=np.abs(s['dist_node_bp'])
    print(f'{k:16s} n={len(s):6d} |dist_vwap| 中央値 {np.nanmedian(ad):6.1f} bp(25% {np.nanpercentile(ad,25):5.1f} / 75% {np.nanpercentile(ad,75):6.1f}) |dist_node| 中央値 {np.nanmedian(an):6.1f} / 240 分 VWAP 到達率 {np.nanmean(s["reach_back_vwap_240m"]):.3f}')
d1=t[(t['kind']=='liq')&(t['doi_pre_1h']<=cut)]; c1=t[(t['kind']=='control_matched')&(t['doi_pre_1h']<=cut)]
for name,s in (('D1 清算',d1),('D1 対照(ii) 生の表の符号',c1)):
    ad=np.abs(s['dist_vwap_bp'])
    print(f'  {name:22s} n={len(s):5d} |dist_vwap| 中央値 {np.nanmedian(ad):6.1f} bp / 240 分到達率 {np.nanmean(s["reach_back_vwap_240m"]):.3f} / bp_reactdir 平均: ' + ' '.join(f'{h}m {np.nanmean(s[f"bp_{h}m_reactdir"]):+.1f}' for h in H))
print('--- D1 清算行: |dist_vwap| の帯ごとの 240 分到達率と、同じ切り値の対照(ii)の同じ帯')
for i in range(len(bins)-1):
    a_=d1[(np.abs(d1['dist_vwap_bp'])>=bins[i])&(np.abs(d1['dist_vwap_bp'])<bins[i+1])]; b_=c1[(np.abs(c1['dist_vwap_bp'])>=bins[i])&(np.abs(c1['dist_vwap_bp'])<bins[i+1])]
    print(f'  {bins[i]:>4.0f}-{bins[i+1] if bins[i+1]<1e9 else 999:>4.0f} bp: 清算 n={len(a_):4d} 到達 {np.nanmean(a_["reach_back_vwap_240m"]):.3f} / 対照 n={len(b_):4d} 到達 {np.nanmean(b_["reach_back_vwap_240m"]):.3f}')
for h in (1,240):
    print(f'--- D1 清算行の bp_reactdir の分位({h} 分): ', {q: round(float(np.nanpercentile(d1[f'bp_{h}m_reactdir'],q)),1) for q in (10,25,50,75,90)}, '/ 負(反転)の割合', round(float(np.nanmean(d1[f'bp_{h}m_reactdir']<0)),3))
