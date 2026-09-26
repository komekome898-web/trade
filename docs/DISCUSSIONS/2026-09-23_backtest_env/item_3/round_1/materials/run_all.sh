#!/bin/sh
# Item 3, round 1, table-maker: run the battery for the given targets twice
# (runs/ = 1st execution, runs_2/ = 2nd execution). Each execution itself runs
# every scene twice in separate processes (run_battery.py).
cd /home/user/trade
M=/home/user/trade/docs/DISCUSSIONS/2026-09-23_backtest_env/item_3/round_1/materials
W=/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/i3_r1_shiryo_work
for t in "$@"; do
  for d in runs runs_2; do
    s=$(date -u +%FT%TZ); s0=$(date +%s)
    mkdir -p "$W/${d}_$t"
    python3 tests/bt/battery/item_3/run_battery.py --target "$t" --out "$M/$d/$t.tsv" --workdir "$W/${d}_$t" > "$M/logs/${d}_$t.stdout" 2>&1
    rc=$?
    echo "$t	$d	start=$s	end=$(date -u +%FT%TZ)	secs=$(( $(date +%s) - s0 ))	rc=$rc"
  done
done
