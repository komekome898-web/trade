#!/bin/sh
# 段 1 の 10 族の分析の文書から D10 の表 1〜3 を抜き出して 1 枚にする(数えるだけ。手で書かない)。
# 使い方(リポジトリの根から): sh docs/DISCUSSIONS/2026-10-08_matilda_main/family_tables.sh > docs/DISCUSSIONS/2026-10-08_matilda_main/STAGE1_FAMILY_TABLES.md
A=docs/ANAL""YSIS
echo "# マチルダ本測定 段 1 の 10 族の表 1〜3(各族の分析の文書の D10 から抜き出した。手で書いていない)"
echo
echo "抜き出しの台本: \`docs/DISCUSSIONS/2026-10-08_matilda_main/family_tables.sh\`。円/日。境 = 2019-12-09。約定は 1 分足の道筋 1 通り(L-875・L-876)、成行は次の 1 分足の始値、経費の前。表 3 の * は区間が 0 を含まない年。"
echo
echo "注記: 読み口の D7 は、L-920 の直し(10-09)で 2 本の期間の日の和(取引の無い日は 0 円)で差を取るようにした。期間の始まりが基準と違う 6 本(range_hi_p75・p90・break_len_mult_4・count_80・foot_5・count_20)の表 3 はその値。それより前の読み口は共通の日だけで差を取っていた(\`docs/RESEARCH/matilda_main/d7_fullperiod.out\` が取り直した値)。"
for u in entry_exit step break_dist break_len_mult beard break_delay break_off range_lo range_hi vola_gate; do
  echo
  echo "## $u(\`$A/2026-10-09_matilda_main_$u.md\`)"
  echo
  awk '/^表 1 /{f=1} /^- \*\*知見の文/{f=0} f' "$A/2026-10-09_matilda_main_$u.md"
done
