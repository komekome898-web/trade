#!/bin/sh
# 持ち越しの 2・3(L-909・L-927・L-933・L-934): 読み口 diag_paths の D5 に 24 時間前の対照と前半・後半(--cut 2019-12-09、D1 と同じ境)を足して、
# 狙いに要る 11 本だけを作る。基準の走らせ 1 本(建てた合図を 24 時間前の対照で読む)と、門の族の 10 本の門で外した合図
# (--blocked-from 基準。門を通った合図の群も同じ出力に入る)。3 本ずつ並べて回す。
T=backtest_runs_shared/matilda_main_trades
M=docs/RESEARCH/matilda_main
CUT=2019-12-09
{
  echo "$T/base||$M/base/diag_paths.md"
  for g in range_lo:range_lo_none,range_lo_p10,range_lo_p25,range_lo_p50 range_hi:range_hi_p75,range_hi_p90,range_hi_none vola_gate:vola_gate_p10,vola_gate_p25,vola_gate_p50; do
    fam=${g%%:*}
    for r in $(echo ${g#*:} | tr ',' ' '); do echo "$T/$r|$T/base|$M/$fam/blocked_$r.md"; done
  done
} | xargs -P 3 -I{} sh -c '
  run=$(echo "{}" | cut -d"|" -f1); bl=$(echo "{}" | cut -d"|" -f2); out=$(echo "{}" | cut -d"|" -f3)
  mkdir -p $(dirname $out)
  if [ -n "$bl" ]; then extra="--blocked-from $bl"; else extra=""; fi
  s=$(date +%s)
  PYTHONPATH=src python3 scripts/analysis/diag_paths.py --run $run $extra --cut '"$CUT"' --out $out >/dev/null 2>$out.err && echo "ok $out $(( $(date +%s) - s ))s" || echo "FAIL $out"
'
echo REGEN_DONE
