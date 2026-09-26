#!/bin/sh
# Item 1, round 1 (rebuild), table-maker: run the battery for the given targets
# twice (runs/ = 1st execution, runs_2/ = 2nd execution). Each execution itself
# runs every scene twice in separate processes (run_battery.py).
# --out is RELATIVE to the repository root, exactly the form of the usage lines
# at the top of run_battery.py, so each scene's root reaches the adapter as a
# relative path (the adapter hands root and paths to the engine unchanged).
cd /home/user/trade
M=docs/DISCUSSIONS/2026-09-23_backtest_env/item_1/round_1/materials
for t in "$@"; do
  for d in runs runs_2; do
    s=$(date -u +%FT%TZ); s0=$(date +%s)
    python3 tests/bt/battery/item_1/run_battery.py --target "$t" --out "$M/$d/$t.tsv" > "$M/logs/${d}_$t.stdout" 2>&1
    rc=$?
    echo "$t	$d	start=$s	end=$(date -u +%FT%TZ)	secs=$(( $(date +%s) - s0 ))	rc=$rc"
  done
done
