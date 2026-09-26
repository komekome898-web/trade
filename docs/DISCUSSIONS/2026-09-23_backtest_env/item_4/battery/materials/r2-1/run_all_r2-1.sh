#!/bin/bash
# Item 4 round r2-1 scene-keeper: run every target of i4_targets.py through the battery runner (each scene twice).
set -u
S=/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/i4_r2-1_scenekeeper
R=tests/bt/battery/item_4/run_battery.py
PYTHONPATH=src:tests/bt/battery/item_4 python3 $R --list-targets | cut -f1 > $S/targets.txt
one() {
  t=$1
  s=$(date -u +%s); echo "$t start $(date -u +%FT%TZ)"
  PYTHONPATH=src python3 $R --target "$t" --out "$S/runs/$t.tsv" --workdir "$S/work_$t" > "$S/logs/$t.log" 2>&1
  rc=$?; e=$(date -u +%s); echo "$t end $(date -u +%FT%TZ) rc=$rc secs=$((e-s))"
}
export -f one
export S R
cat $S/targets.txt | xargs -P 4 -I{} bash -c 'one "$@"' _ {}
echo ALL_DONE $(date -u +%FT%TZ)
