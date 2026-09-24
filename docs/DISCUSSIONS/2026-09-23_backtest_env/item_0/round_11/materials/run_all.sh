#!/bin/sh
# Item 0, round 11, materials person: run every configured target of
# `run_battery.py --list-targets` through the scene set (run_battery.py runs
# each scene twice with a fresh adapter per run) and keep the TSVs and one log
# line per target (start/end UTC, rc, runner summary).
# Round 11: the scene-set fingerprint differs from round 9's (round 10 has no
# materials), so every configured target is run (L-435). Two whole passes
# (RUNTAG=run1 / run2) into runs/ and runs_2/, to check that the tables built
# from each pass are byte-identical; the tables use runs/ (run1).
# Targets carry a configuration label (`base@label`); each configured target
# is one run file.
# The interpreter is chosen by the base name (the part before '@').
# Usage (from the repo root): sh docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/round_11/materials/run_all.sh
set -u
REPO=$(pwd)
M=docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/round_11/materials
RUNNER=tests/bt/battery/item_0/run_battery.py
S=/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt
V=$S/venvs/item_0
V5F=/tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/v5f
RUNTAG=${RUNTAG:-run1}
if [ "$RUNTAG" = run1 ]; then RD=$M/runs; LD=$M/logs; else RD=$M/runs_2; LD=$M/logs/run2; fi
LOG=$LD/run_all.log
mkdir -p $RD $LD
: > $LOG

venv_of() {  # base target -> venv directory name ("" = repo python3)
  case "$1" in
    current_impl|new_impl|mutant|repro_*) echo "" ;;
    opp_basana) echo basana ;; opp_ziplime) echo ziplime ;; opp_zipline_reloaded) echo zipline-reloaded ;;
    opp_lib_pybroker) echo lib-pybroker ;; opp_qf_lib) echo qf-lib ;; opp_backtrader) echo backtrader ;;
    opp_hftbacktest) echo hftbacktest ;; opp_rqalpha) echo rqalpha ;; opp_pybotters) echo pybotters ;;
    opp_backtesting) echo backtesting ;; opp_qstrader) echo qstrader ;; opp_quantcore) echo quantcore ;;
    opp_quanttrader) echo quanttrader ;; opp_pyalgotrade) echo pyalgotrade ;; opp_freqtrade) echo freqtrade ;;
    opp_vnpy) echo vnpy ;; opp_finmarketpy) echo finmarketpy ;; opp_luczinsritter) echo luczinsritter ;;
    opp_mihircoding_lob) echo c98 ;; opp_nickgardi_orderbooksim) echo c99 ;; opp_daniyalmlk_slippage) echo c105 ;;
    opp_akurkar07_orderbook) echo c101 ;; opp_3yit_lob) echo c102 ;; opp_jxm35_lob) echo c104 ;;
    opp_pysystemtrade) echo c3 ;; opp_predictivedev_tradesim) echo c37 ;; opp_sarthak_execsim) echo c33 ;;
    opp_sigc) echo c107 ;; opp_homerun) echo c91 ;; opp_aat) echo c65 ;; opp_gobacktest) echo c69 ;;
    opp_pineforge) echo c70 ;; opp_barter) echo c61 ;; opp_pytrendfollow) echo c87 ;;
    opp_isaaccheng_obsim) echo c103 ;; opp_fast_trade) echo v5f ;;
    *) echo "UNKNOWN" ;;
  esac
}

run() {  # $1 target, $2 interpreter, $3 venv label
  s=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  (cd "$REPO" && BT_SCRATCH=$S PYTHONPATH=src timeout 400 "$2" -B $RUNNER --target "$1" --out "$RD/$1.tsv" \
      >"$LD/$1.stdout" 2>"$LD/$1.stderr")
  rc=$?
  out=$(tail -1 "$LD/$1.stdout")
  e=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  echo "$1 interpreter=$3 start=$s end=$e rc=$rc :: $out" >> $LOG
}

python3 -B $RUNNER --list-targets > $LD/list_targets.out
for t in $(cat $LD/list_targets.out); do
  base=${t%%@*}
  v=$(venv_of "$base")
  if [ "$v" = "" ]; then
    run "$t" python3 repo
  elif [ "$v" = "v5f" ]; then
    run "$t" "$V5F/bin/python" v5f
  elif [ "$v" = "UNKNOWN" ]; then
    echo "$t interpreter=? NOT_RUN: no venv mapping for base $base" >> $LOG
  elif [ -x "$V/$v/bin/python" ]; then
    run "$t" "$V/$v/bin/python" "$v"
  else
    echo "$t interpreter=$v NOT_RUN: $V/$v/bin/python does not exist" >> $LOG
  fi
done
echo ALL_DONE >> $LOG
