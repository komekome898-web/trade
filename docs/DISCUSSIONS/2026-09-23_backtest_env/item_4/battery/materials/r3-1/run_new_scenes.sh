#!/bin/bash
# Run the scenes added / changed in round r3-1 for every target (rule 4), 6 targets at a time.
cd /home/user/trade
B=/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/finish_scene_r3-1
SC=i4-13-stop-on-time-bar,i4-13-stop-on-time-bar-maker,i4-13-stop-on-time-bar-two-models,i4-14-maker-mask-false,i4-16-maker-mask-false-not-missed,i4-16-maker-mask-false-two-models,i4-16-same-side-keeps-limit,i4-16-same-side-two-models
echo "start $(date -u +%FT%TZ)"
PYTHONPATH=src python3 tests/bt/battery/item_4/run_battery.py --list-targets | cut -f1 | \
  xargs -P 6 -I{} sh -c "PYTHONPATH=src timeout 900 python3 tests/bt/battery/item_4/run_battery.py --target {} --out $B/runs/{}.tsv --scenes $SC > $B/runs/{}.log 2>&1; echo {} rc=\$?"
echo "end $(date -u +%FT%TZ)"
