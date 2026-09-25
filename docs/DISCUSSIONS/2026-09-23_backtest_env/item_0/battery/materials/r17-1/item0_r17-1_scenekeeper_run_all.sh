#!/bin/sh
# Item 0, round r17-1, scene keeper: run every configured target of `run_battery.py --list-targets` once through the
# scene set (each scene twice inside), after the refusal grade (critic i0-r16-04) was added. Interpreter mapping = round r13-1's.
set -u
REPO=/home/user/trade
RUNNER=tests/bt/battery/item_0/run_battery.py
R=/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/r17-1
. $R/item0_r17-1_scenekeeper_venv_of.sh
RD=$R/runs; LD=$R/logs; LOG=$LD/run_all.log
mkdir -p $RD $LD; : > $LOG
cd "$REPO" && python3 -B $RUNNER --list-targets > $LD/list_targets.out
for t in $(cat $LD/list_targets.out); do
  py=$(py_of "$t")
  if [ "$py" = UNKNOWN ]; then echo "$t NOT_RUN (no interpreter)" >> $LOG; continue; fi
  s=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  (cd "$REPO" && BT_SCRATCH=$S PYTHONPATH=src timeout 600 "$py" -B $RUNNER --target "$t" --out "$RD/$t.tsv" >"$LD/$t.stdout" 2>"$LD/$t.stderr")
  rc=$?; out=$(tail -1 "$LD/$t.stdout"); e=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  echo "$t interpreter=$py start=$s end=$e rc=$rc :: $out" >> $LOG
done
echo ALL_DONE >> $LOG
