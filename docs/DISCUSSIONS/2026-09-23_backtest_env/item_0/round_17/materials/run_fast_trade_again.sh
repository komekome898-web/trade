#!/bin/sh
# Round 17: in both passes of run_all.sh the configured target opp_fast_trade
# failed to start (rc=127: the interpreter of the venv named V5F in run_all.sh
# was gone; logs/opp_fast_trade.stderr). The tool was reinstalled from the
# wheel saved in the scene keeper's inspect step into an isolated venv
# (logs/item0_r17_materials_fast_trade_reinstall.log) and is run here for
# pass 1 and pass 2, the same way as run_all.sh's run(). The failed line of
# each pass's run_all.log is kept in run_all.rc127.log and replaced by the
# line of this run (make_tables.py reads the lengths from run_all.log).
set -u
REPO=$(pwd)
M=docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/round_17/materials
RUNNER=tests/bt/battery/item_0/run_battery.py
S=/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt
PY=$S/venvs/item_0/fast-trade-r17/bin/python
t=opp_fast_trade
for pass in run1 run2; do
  if [ $pass = run1 ]; then RD=$M/runs; LD=$M/logs; else RD=$M/runs_2; LD=$M/logs/run2; fi
  grep "^$t " $LD/run_all.log >> $LD/run_all.rc127.log
  s=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  (cd "$REPO" && BT_SCRATCH=$S PYTHONPATH=src timeout 400 "$PY" -B $RUNNER --target $t --out "$RD/$t.tsv" \
      >"$LD/$t.stdout" 2>"$LD/$t.stderr")
  rc=$?
  out=$(tail -1 "$LD/$t.stdout")
  e=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  line="$t interpreter=fast-trade-r17 start=$s end=$e rc=$rc :: $out"
  grep -v "^$t " $LD/run_all.log | grep -v '^ALL_DONE$' > $LD/run_all.log.tmp
  echo "$line" >> $LD/run_all.log.tmp
  echo ALL_DONE >> $LD/run_all.log.tmp
  mv $LD/run_all.log.tmp $LD/run_all.log
done
