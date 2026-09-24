#!/bin/sh
# Item 0, round 3, materials person: run every target through the scene set
# (run_battery.py runs each scene twice with a fresh adapter per run) and
# keep the TSVs and one log line per target (start/end UTC, rc, runner summary).
# Usage (from the repo root): sh docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/round_3/materials/run_all.sh
set -u
REPO=$(pwd)
M=docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/round_3/materials
RUNNER=tests/bt/battery/item_0/run_battery.py
V=/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/venvs/item_0
V5F=/tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/v5f
LOG=$M/logs/run_all.log
mkdir -p $M/runs $M/logs
: > $LOG

run() {  # $1 target, $2 interpreter, $3 venv label
  s=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  out=$(cd "$REPO" && PYTHONPATH=src timeout 300 "$2" $RUNNER --target "$1" --out $M/runs/"$1".tsv 2>$M/logs/"$1".stderr)
  rc=$?
  e=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  echo "$1 interpreter=$3 start=$s end=$e rc=$rc :: $out" >> $LOG
}

run current_impl python3 repo
run new_impl python3 repo
run mutant python3 repo
for pair in opp_basana:basana opp_ziplime:ziplime opp_zipline_reloaded:zipline-reloaded \
            opp_lib_pybroker:lib-pybroker opp_qf_lib:qf-lib opp_backtrader:backtrader \
            opp_hftbacktest:hftbacktest opp_rqalpha:rqalpha opp_pybotters:pybotters \
            opp_backtesting:backtesting opp_qstrader:qstrader opp_quantcore:quantcore \
            opp_quanttrader:quanttrader opp_pyalgotrade:pyalgotrade opp_freqtrade:freqtrade \
            opp_vnpy:vnpy opp_finmarketpy:finmarketpy; do
  t=${pair%%:*}; v=${pair#*:}
  if [ -x "$V/$v/bin/python" ]; then
    run "$t" "$V/$v/bin/python" "$v"
  else
    echo "$t interpreter=$v NOT_RUN: $V/$v/bin/python does not exist" >> $LOG
  fi
done
run opp_fast_trade "$V5F/bin/python" v5f
for p in tests/bt/battery/item_0/opponents/repro_*.py; do
  t=$(basename "$p" .py)
  run "$t" python3 repo
done
cat $LOG
