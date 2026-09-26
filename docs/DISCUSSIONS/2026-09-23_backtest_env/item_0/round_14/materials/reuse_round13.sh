#!/bin/sh
# Round 14, materials person: the scene-set fingerprint equals round 13's
# (logs/scene_set_fingerprint.txt), so by L-435 the round 13 results of
# current_impl and of every survey-side configured target (opp_* / repro_*)
# are reused: copied from round_13/materials/runs{,_2}/ with their round 13
# log lines. new_impl and mutant are NOT copied (run again, run_new.sh).
# Usage (from the repo root).
set -eu
B=docs/DISCUSSIONS/2026-09-23_backtest_env/item_0
M=$B/round_14/materials
R13=$B/round_13/materials
for d in runs runs_2; do
  for f in $R13/$d/*.tsv; do
    n=$(basename "$f" .tsv)
    case "$n" in new_impl|mutant) continue ;; esac
    cp "$f" "$M/$d/"
  done
done
grep -vE '^(new_impl|mutant) |^ALL_DONE' $R13/logs/run_all.log > $M/logs/run_all_reused_round13.log
grep -vE '^(new_impl|mutant) |^ALL_DONE' $R13/logs/run2/run_all.log > $M/logs/run2/run_all_reused_round13.log
echo "# sha256 of the reused files (round 13 source = round 14 copy):"
for d in runs runs_2; do
  for f in $M/$d/*.tsv; do
    a=$(sha256sum "$R13/$d/$(basename "$f")" | cut -c1-64); b=$(sha256sum "$f" | cut -c1-64)
    [ "$a" = "$b" ] && echo "$d/$(basename "$f") $b same" || echo "$d/$(basename "$f") DIFFERENT"
  done
done
echo "copied: runs=$(ls $M/runs/*.tsv | wc -l) runs_2=$(ls $M/runs_2/*.tsv | wc -l) log lines=$(wc -l < $M/logs/run_all_reused_round13.log)/$(wc -l < $M/logs/run2/run_all_reused_round13.log)"
