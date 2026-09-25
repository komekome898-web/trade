#!/bin/sh
# Round 14, materials person: run the targets that are run every round
# (new_impl, mutant; L-435) through the scene set with the repo python3.
# run_battery.py runs each scene twice with a fresh adapter per run (the
# reproducibility field). Two whole passes (RUNTAG=run1 -> runs/,
# RUNTAG=run2 -> runs_2/) to check that the tables built from each pass are
# byte-identical; the delivered tables use runs/ (run1).
# Usage (from the repo root): sh .../round_14/materials/run_new.sh
set -u
REPO=$(pwd)
M=docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/round_14/materials
RUNNER=tests/bt/battery/item_0/run_battery.py
S=/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt
for RUNTAG in run1 run2; do
  if [ "$RUNTAG" = run1 ]; then RD=$M/runs; LD=$M/logs; else RD=$M/runs_2; LD=$M/logs/run2; fi
  LOG=$LD/run_all.log
  mkdir -p $RD $LD
  : > $LOG
  for t in new_impl mutant; do
    s=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    (cd "$REPO" && BT_SCRATCH=$S PYTHONPATH=src timeout 400 python3 -B $RUNNER --target "$t" --out "$RD/$t.tsv" \
        >"$LD/$t.stdout" 2>"$LD/$t.stderr")
    rc=$?
    out=$(tail -1 "$LD/$t.stdout")
    e=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    echo "$t interpreter=repo start=$s end=$e rc=$rc :: $out" >> $LOG
  done
  echo ALL_DONE >> $LOG
done
echo BOTH_DONE > $M/logs/run_new.done
