#!/bin/bash
# Run the scenes added / changed in round r3-1 for every target (rule 4), 6 targets at a time.
cd /home/user/trade
B=/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/finish_scene_r3-1
SC=i4-5-fills,i4-5-outputs,i4-6-label,i4-6-signal-refused,i4-6-research-refused
echo "start $(date -u +%FT%TZ)"
PYTHONPATH=src python3 tests/bt/battery/item_4/run_battery.py --list-targets | cut -f1 | \
  xargs -P 6 -I{} sh -c "PYTHONPATH=src timeout 900 python3 tests/bt/battery/item_4/run_battery.py --target {} --out $B/runs5/{}.tsv --scenes $SC > $B/runs5/{}.log 2>&1; echo {} rc=\$?"
echo "end $(date -u +%FT%TZ)"
