#!/bin/bash
# Item 4 round 2 table-maker: run every target of i4_targets.py through the battery runner twice
# (1st -> materials/runs/, 2nd -> materials/runs_2/). Each runner call itself runs every scene twice (repro column).
# Usage: sh run_all.sh  (from the repo root). Log lines: start/end UTC and seconds per target and run.
set -u
M=docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/round_2/materials
R=tests/bt/battery/item_4/run_battery.py
PAR=${PAR:-4}
export TMPDIR=/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/i4_r2_shiryo_tmp
python3 $R --list-targets | cut -f1 > $M/targets.txt
one() {
  t=$1
  for d in runs runs_2; do
    s=$(date -u +%s); echo "$t $d start $(date -u +%FT%TZ)"
    python3 $R --target "$t" --out "$M/$d/$t.tsv" > "$M/logs/${t}_${d}.log" 2>&1
    rc=$?; e=$(date -u +%s); echo "$t $d end $(date -u +%FT%TZ) rc=$rc secs=$((e-s))"
  done
}
export -f one 2>/dev/null || true
export M R
cat $M/targets.txt | xargs -P "$PAR" -I{} bash -c 'one "$@"' _ {}
echo ALL_DONE $(date -u +%FT%TZ)
