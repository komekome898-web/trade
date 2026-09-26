#!/bin/sh
# Round 16: md5sum of the two orientations of each pair (mapping.tsv), then
# cmp; and pass 1 vs pass 2 tables of the same table id.
B=docs/DISCUSSIONS/2026-09-23_backtest_env/item_0
M=$B/round_16/materials
f() { awk -F'\t' -v t="$2" '$1==t{print $2}' "$1/mapping.tsv"; }
echo "# md5sum of the two orientations of each pair (materials/mapping.tsv), then cmp"
for p in current survey mutant; do
  a=$(f $M ${p}_1); b=$(f $M ${p}_2)
  md5sum $B/round_16/$a $B/round_16/$b
  if cmp -s $B/round_16/$a $B/round_16/$b; then echo "$p: identical ($a $b)"; else echo "$p: differ ($a $b) :: $(cmp $B/round_16/$a $B/round_16/$b 2>&1)"; fi
done
for d in pass2_tables pass2_tables_ownlog; do
  echo "# pass 1 table vs pass 2 table of the same id ($d; pass 2 built from runs_2/)"
  for t in current_1 current_2 survey_1 survey_2 mutant_1 mutant_2; do
    a=$B/round_16/$(f $M $t); b=$M/$d/$(f $M/$d $t)
    if cmp -s $a $b; then echo "$t: identical"; else echo "$t: differ :: $(diff $a $b | head -4 | cut -c1-300 | tr '\n' ' ')"; fi
  done
done
