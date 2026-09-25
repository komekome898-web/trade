#!/bin/sh
# Round 13: two whole passes, one after the other (not concurrent, so the
# passes do not share scratch state at the same time).
M=docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/round_13/materials
RUNTAG=run1 sh $M/run_all.sh
RUNTAG=run2 sh $M/run_all.sh
echo BOTH_DONE > $M/logs/run_both.done
