#!/bin/bash
# Run the scenes added / changed in round r3-1 for every target (rule 4), 6 targets at a time.
cd /home/user/trade
B=/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/finish_scene_r3-1
SC=i4-1-ref-taker,i4-1-ref-maker,i4-3-ref-signal-first,i4-11-wick-short-history,i4-11-wick-entry-bar-close,i4-16-exit-same-side-keeps-limit,i4-16-exit-same-side-two-models,i4-14-blocked-opposite-keeps-limit,i4-14-sides-opposite-keeps-limit,i4-14-sides-opposite-two-models,i4-8-refuse-bad-bar,i4-10-zero-rate-refused,i4-8-negative-fee,i4-16-zero-timeout-refused
echo "start $(date -u +%FT%TZ)"
PYTHONPATH=src python3 tests/bt/battery/item_4/run_battery.py --list-targets | cut -f1 | \
  xargs -P 6 -I{} sh -c "PYTHONPATH=src timeout 900 python3 tests/bt/battery/item_4/run_battery.py --target {} --out $B/runs3/{}.tsv --scenes $SC > $B/runs3/{}.log 2>&1; echo {} rc=\$?"
echo "end $(date -u +%FT%TZ)"
