#!/bin/sh
# Item 0, round 9, materials person.
# The scene-set fingerprint (logs/scene_set_fingerprint.txt) equals round 8's,
# so (delegation doc §3 "reuse of the opponents' results", L-435) the survey
# side (opp_* / repro_* configured targets) is reused from round 8's
# materials/runs, copied here and listed in logs/reused_from_round8.txt.
# The new implementation and the mutant run every round; the current
# implementation is re-run as well (cheap; reuse would also be allowed).
# run_battery.py runs each scene twice with a fresh adapter per run.
# Usage (from the repo root): sh docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/round_9/materials/run_all.sh
set -u
REPO=$(pwd)
M=docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/round_9/materials
M8=docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/round_8/materials
RUNNER=tests/bt/battery/item_0/run_battery.py
S=/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt
LOG=$M/logs/run_all.log
mkdir -p $M/runs $M/logs
: > $LOG

run() {  # $1 target
  s=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  (cd "$REPO" && BT_SCRATCH=$S PYTHONPATH=src timeout 400 python3 -B $RUNNER --target "$1" --out "$M/runs/$1.tsv" \
      >"$M/logs/$1.stdout" 2>"$M/logs/$1.stderr")
  rc=$?
  out=$(tail -1 "$M/logs/$1.stdout")
  e=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  echo "$1 interpreter=repo start=$s end=$e rc=$rc :: $out" >> $LOG
}

python3 -B $RUNNER --list-targets > $M/logs/list_targets.out
for t in new_impl mutant current_impl; do run "$t"; done

# reuse: every survey configured target listed by --list-targets, from round 8
: > $M/logs/reused_from_round8.txt
for t in $(cat $M/logs/list_targets.out); do
  case "$t" in
    opp_*|repro_*)
      if [ -f "$M8/runs/$t.tsv" ]; then
        cp "$M8/runs/$t.tsv" "$M/runs/$t.tsv"
        echo "$t $(sha256sum "$M8/runs/$t.tsv" | cut -c1-16)" >> $M/logs/reused_from_round8.txt
      else
        echo "$t MISSING_IN_ROUND8" >> $M/logs/reused_from_round8.txt
      fi ;;
  esac
done
# the round-8 log lines of the reused targets (their measured run lengths)
grep -E '^(opp_|repro_)' $M8/logs/run_all.log > $M/logs/run_all_round8_reused.log
echo ALL_DONE >> $LOG
