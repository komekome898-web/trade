"""L-241: 印ではなく「選ぶ・順位付ける」使い方を今日の事例で試す(観測。数値は data/jev に残す)。"""
import json, sys
sys.path.insert(0, 'scripts')
from jev.client import JevClient
c = JevClient(model='jev-1.13.0')
purpose = "Owner's purpose (verbatim Japanese): 清算の監視による値段の上がりすぎ下がりすぎやトレンド転換を捉えることができるか確認 — i.e. confirm whether monitoring liquidation cascades lets us detect price overshoot/undershoot and whether a trend reverses or continues afterwards."
observables = {
 "bp_reactdir": "signed price change h minutes after the cascade, in bp; negative = moved against the cascade direction (reversal), positive = continued",
 "reach_back_vwap": "whether price returned within h minutes to the volume-weighted average price of the preceding W hours (binary per cascade)",
 "reach_back_node": "whether price returned within h minutes to the nearest high-volume price node of the preceding W hours (binary)",
 "fwd_node": "whether price reached, within h minutes, the next high-volume node in the cascade direction (binary; undefined for 82% of cascades)",
 "time_to_reach": "seconds until the reach-back target was first touched (NaN if never)",
 "mfe_mae": "maximum favorable and maximum adverse excursion in bp within h minutes, measured in the cascade direction",
 "doi_post": "change in open interest (contracts) from the cascade to h minutes later",
 "reach_rate_vs_control": "difference in reach-back rate between cascades and control times (a derived comparison of reach_back_vwap)",
}
# 1) 候補の量を目的に対して点数化(score)
S1 = {"owner_purpose": purpose, "candidate_observables": observables}
Q1 = {k: {"type": "score", "instructions": f"How directly does `candidate_observables.{k}` express what `owner_purpose` asks (overshoot followed by reversal, or continuation, after a cascade)?",
          "criteria": ["does not express it, or only through an unrelated proxy", "weak proxy: related but its value is mostly determined by something else (e.g. a fixed reference level)", "partial: expresses one side (e.g. continuation only) or is undefined for many cases", "direct: its sign or value directly says reversal versus continuation", "direct and complete: reversal versus continuation and its size, defined for every cascade"]} for k in observables}
r1 = c.evaluate(S1, Q1)
# 2) 対照で合わせるべき変数を「量が依存するか」で選ぶ(noul の同時送信)
covariates = {
 "dist_vwap_bp": "distance in bp from the cascade price to the preceding W-hour VWAP at the moment of the cascade",
 "bin_pct": "thinness of the price bin where the cascade occurred (share of volume in that bin)",
 "doi_pre_1h": "change in open interest over the hour before the cascade",
 "side": "whether the cascade liquidated longs or shorts",
 "time_of_day": "UTC hour of the cascade",
 "cascade_size": "number of liquidation events in the cascade",
}
S2 = {"judgment_quantity": "reach_back_vwap: whether price returned within h minutes to the preceding W-hour VWAP", "covariates": covariates}
Q2 = {k: {"type": "noul", "instructions": f"By construction of `judgment_quantity`, is its value strongly determined by `covariates.{k}` regardless of any liquidation mechanism, so that a control group must be matched on it for a fair comparison?", "criteria": {"true": "yes: the quantity's value depends mechanically on this covariate (e.g. how far price must travel)", "false": "no: the covariate may correlate with the outcome but does not determine it by construction"}} for k in covariates}
r2 = c.evaluate(S2, Q2)
out = {"observables_score": r1, "covariates_dependence": r2}
json.dump(out, open('data/jev/probe/20260919_L241_select_rank.json','w'), ensure_ascii=False, indent=1)
def show_score(ans):
    for k,v in ans.items():
        d=v.get('score') or v.get('distribution') or v
        if isinstance(d, dict) and all(isinstance(x,(int,float)) for x in d.values()):
            ev=sum(float(kk)*vv for kk,vv in d.items()); print(f"  {k:24s} 期待値 {ev:.2f}  分布 {{{', '.join(f'{kk}:{vv:.2f}' for kk,vv in d.items())}}}")
        else: print(f"  {k:24s} {v}")
print("=== 候補の量 × 目的(score 1〜5、期待値の高い順) ===")
a1=r1.get('answers', {}); 
rows=[]
print('  (生の形の例)', json.dumps(next(iter(a1.values())), ensure_ascii=False)[:200])
for k,v in a1.items():
    if isinstance(v,dict) and isinstance(v.get('score'), list):
        v={'score': {str(i+1): x for i,x in enumerate(v['score'])}}
    d=v.get('score') if isinstance(v,dict) else None
    if isinstance(d, dict):
        try: ev=sum(float(kk)*vv for kk,vv in d.items())
        except Exception: ev=float('nan')
        rows.append((ev,k,d))
for ev,k,d in sorted(rows, reverse=True): print(f"  {k:24s} 期待値 {ev:.2f}  " + ', '.join(f'{kk}:{vv:.2f}' for kk,vv in sorted(d.items())))
if not rows: print(json.dumps(r1, ensure_ascii=False)[:800])
print("=== 対照で合わせる変数(量が構造的に依存するか、yes の確率) ===")
a2=r2.get('answers', {})
for k,v in sorted(a2.items(), key=lambda kv: -(kv[1].get('noul',0) if isinstance(kv[1],dict) else 0)): print(f"  {k:16s} {v.get('noul') if isinstance(v,dict) else v}")
print('usage', r1.get('usage'), r2.get('usage'))
