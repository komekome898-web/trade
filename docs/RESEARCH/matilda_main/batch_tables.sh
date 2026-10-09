#!/bin/sh
# 族の報告の型の表を、残りの族の全部の本について先に作る(既にある台本を順に回すだけ。L-895 の改善案 1)。
# 読み口 diag_tables(基準と比べ、有効期間 = alert_count × 2)、族ごとの compare_family・scenes・market_side、half_diff。
T=backtest_runs_shared/matilda_main_trades
M=docs/RESEARCH/matilda_main
FAMS="count:count_20,count_80 alert:alert_x1,alert_x2 entry_exit:entry_exit_3_2,entry_exit_2_1 step:step_2,step_4 break_dist:break_dist_0.25,break_dist_1 break_len_mult:break_len_mult_4 beard:beard_off break_delay:break_delay_2,break_delay_3,break_delay_4,break_delay_8 break_off:break_off range_lo:range_lo_none,range_lo_p10,range_lo_p25,range_lo_p50 range_hi:range_hi_p75,range_hi_p90,range_hi_none vola_gate:vola_gate_p10,vola_gate_p25,vola_gate_p50"
ALL=""
for fr in $FAMS; do
  fam=${fr%%:*}; runs=$(echo ${fr#*:} | tr ',' ' ')
  mkdir -p $M/$fam
  for r in $runs; do
    ALL="$ALL $r"; mkdir -p $M/$r
    v=$(python3 -c "import json;print(int(2*json.load(open('backtest_runs_shared/matilda_main/$r/run.json'))['params']['alert_count']))")
    [ -f $M/$r/diag_tables.md ] || PYTHONPATH=src python3 scripts/analysis/diag_tables.py --run $T/$r --vs $T/base --out $M/$r/diag_tables.md --valid-min $v >/dev/null && echo "$r tables ok (valid-min $v)"
  done
  PYTHONPATH=src python3 $M/compare_family.py $runs > $M/$fam/compare.md && echo "$fam compare ok"
  PYTHONPATH=src:scripts/w4_measure python3 $M/scenes.py $runs > $M/$fam/scenes.out && echo "$fam scenes ok"
  PYTHONPATH=src python3 $M/market_side.py $runs > $M/$fam/market_side.out && echo "$fam market ok"
done
PYTHONPATH=src python3 $M/half_diff.py $ALL > $M/half_diff_rest.out && echo "half_diff ok"
echo BATCH_DONE
