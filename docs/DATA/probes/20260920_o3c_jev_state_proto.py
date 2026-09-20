"""§6 の状態を実物で組む試作(前半だけ。境界 = 前半の五分位)。"""
import json, math, re, numpy as np, pandas as pd
M = pd.read_csv('backtest_data/o3c_signal_materials_20260920/rows_materials.csv.gz', low_memory=False)
C = pd.read_csv('backtest_data/o3c_signal_continue_20260920/rows_continue.csv.gz', low_memory=False)
P = pd.read_csv('backtest_data/o3c_signal_explore5_20260920/rows_prints.csv.gz', low_memory=False)
P = P[P.kind == 'print'].sort_values('ts_ms')
R = M.merge(C[['print_id','mat1_elapsed_since_burst_s','mat3_notional_raw','mat8_amt_5bp','mat8_amt_20bp','mat8_covered',
               'mat9_taker_imbalance_5s','mat13_taker_imbalance_trend','mat10_taker_ls_ratio','mat10_funding_rate','mat5_distance_to_liquidation_node']], on='print_id', how='left')
FH = R[R.half == '前半']
BANDS = ['bottom fifth', 'second fifth', 'middle fifth', 'fourth fifth', 'top fifth']
def cuts(col, sub=None):
    v = (sub if sub is not None else FH)[col].astype(float).dropna()
    v = v[np.isfinite(v)]
    return [float(v.quantile(q)) for q in (0.2, 0.4, 0.6, 0.8)]
def band(x, c):
    if x is None or not math.isfinite(x): return 'unknown'
    return BANDS[int(np.searchsorted(c, x, side='right'))]
Q = {  # 境界は前半だけから。定数として 1 箇所に置く
 'notional': cuts('mat3_notional_raw'), 'trade_count_60s': cuts('cand_14'), 'move_60s_bp': None,
 'ratio_10s_60s': cuts('cand_15'), 'range_ratio': cuts('cand_11'), 'day_extreme_bp': cuts('cand_C3'),
 'vol_ratio_5m_1h': cuts('cand_C4'), 'chain_notional': cuts('cand_F3', FH[FH.cand_F3.notna()]),
 'last10s_notional': cuts('cand_F5', FH[FH.cand_F5 > 0]) if 'cand_F5' in FH else None,
 'oi_ahead_20bp': cuts('mat8_amt_20bp', FH[FH.mat8_amt_20bp > 0]), 'interval_ratio': cuts('cand_2', FH[FH.cand_2.notna()]),
}
def pct(x): return None if x is None or not math.isfinite(x) else round((1 + x) / 2 * 100)
def state_for(pid):
    r = R[R.print_id == pid].iloc[0]; ts = int(r.ts_ms); side = r.side
    sgn = 1 if side == 'BUY' else -1
    w = P[(P.ts_ms >= ts - 60000) & (P.ts_ms < ts)]
    same = w[w.side == side]; opp = w[w.side != side]
    same_list = [f"{(ts - t)/1000:.1f} s ago, size {band(n, Q['notional'])}" for t, n in zip(same.ts_ms, same.notional)]
    cnt = int(r.cand_1); el = r.mat1_elapsed_since_burst_s
    if cnt == 0: pos = 'first same-side liquidation in the last 60 seconds (no cascade in progress)'
    else: pos = (f"print number {cnt + 1} of a same-side cascade that began {el:.0f} s ago; "
                 f"notional liquidated so far in this cascade: {band(r.cand_F3, Q['chain_notional'])} of first-half cascades")
    a6 = r.cand_A6; r1 = r.cand_R1 if 'cand_R1' in r else float('nan')
    if math.isfinite(a6) and a6 <= 1.0: ext = f"price set a new 60-second extreme in the liquidation direction {a6:.1f} s ago (no pullback yet)"
    elif math.isfinite(a6): ext = f"the 60-second extreme was set {a6:.0f} s ago; price has since pulled back {max(r1, 0):.1f} bp against the liquidation direction" if math.isfinite(r1) else f"extreme set {a6:.0f} s ago"
    else: ext = 'unknown'
    cov = int(r.mat8_covered) if math.isfinite(r.mat8_covered) else 0
    if not cov: ahead = 'coverage unknown (open-interest map does not cover this price range)'
    elif r.mat8_amt_20bp <= 0: ahead = 'no open interest within 20 bp ahead in the liquidation direction'
    else: ahead = (f"open interest within 20 bp ahead: {band(r.mat8_amt_20bp, Q['oi_ahead_20bp'])} of first-half prints that had any; "
                   f"within 5 bp: {'some' if r.mat8_amt_5bp > 0 else 'none'}; nearest liquidation level ahead: "
                   + (f"{r.cand_5p:.0f} bp away" if math.isfinite(r.cand_5p) else 'none within the mapped range'))
    st = {
     'this_print': {'side': f"{side} liquidation ({'longs' if side=='SELL' else 'shorts'} being force-closed)",
                    'size': f"{band(r.mat3_notional_raw, Q['notional'])} of first-half prints", 'time_utc': {0:'00-06 UTC',1:'06-12 UTC',2:'12-18 UTC',3:'18-24 UTC'}.get(int(r.cand_6), 'unknown')},
     'position_in_cascade': pos,
     'recent_same_side_prints': same_list or 'none in the last 60 seconds',
     'same_side_notional_last_10s': ('none' if not math.isfinite(r.cand_F5) or r.cand_F5 <= 0 else f"{band(r.cand_F5, Q['last10s_notional'])} of first-half prints that had any") if 'cand_F5' in r else 'unknown',
     'opposite_side_prints_last_60s': f"{int(r.cand_A9_count)} print(s)" if r.cand_A9_count > 0 else 'none',
     'price_extreme': ext,
     'price_move': {'last_10s_vs_60s': f"{band(r.cand_15, Q['ratio_10s_60s'])} (share of the 60-second move that happened in the last 10 seconds)",
                    'print_size_vs_60s_range': band(r.cand_11, Q['range_ratio'])},
     'taker_flow': {'last_5s_share_in_liquidation_direction_pct': pct(r.mat9_taker_imbalance_5s),
                    'trend_5s_minus_30s': 'more one-sided now' if r.mat13_taker_imbalance_trend > 0.1 else ('less one-sided now' if r.mat13_taker_imbalance_trend < -0.1 else 'about the same')},
     'positions_ahead': ahead,
     'oi_and_funding': {'taker_long_short_ratio': round(float(r.mat10_taker_ls_ratio), 2) if math.isfinite(r.mat10_taker_ls_ratio) else 'unknown',
                        'funding_rate': 'positive' if r.mat10_funding_rate > 0 else ('negative' if r.mat10_funding_rate < 0 else 'zero')},
     'day_context': {'distance_from_day_extreme': band(r.cand_C3, Q['day_extreme_bp']), 'vol_5m_vs_1h': band(r.cand_C4, Q['vol_ratio_5m_1h']),
                     'trade_count_60s': band(r.cand_14, Q['trade_count_60s'])},
    }
    return st
if __name__ == '__main__':
    print('境界(前半の五分位、定数):'); 
    for k, v in Q.items():
        if v: print(f"  {k}: " + ', '.join(f"{x:.4g}" for x in v))
    for pid in ('2023-08-17_00168', '2023-07-13_00128', '2023-11-02_00090'):
        r = M[M.print_id == pid].iloc[0]
        print(f"\n== {pid}({r.pos_label})"); print(json.dumps(state_for(pid), ensure_ascii=False, indent=1))
