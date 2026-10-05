#!/bin/sh
# 分析のコミットの門: 台帳の検査が「問題 0」かつ仮置きが 0 件のときだけ、docs/ をコミットする。
#
# 目的: 台帳の検査で問題 2 件が出ていたのにコミット・押し出しした(3fb6c4e7、直しは bb5d22b1)、「後で書き足す」の
# 仮置きが残った(カード 1・2・3・9)のを、自分の注意でなく門で止める
# (docs/DISCUSSIONS/2026-10-05_analysis_mechanism/PROPOSAL.md §2・要件 R3・R4)。
# 経緯: オーナーの指示 L-705「今日の分析方法(分析スキル・アドバイザーfableとの2人作業・なぜ分解と台帳記入)を
# 再利用可能な仕組み化してほしい。要件を詰めたいので案を出してください。」と L-706「1.y 2.y だが、
# アドバイザー含め渡す情報はどうする？今回は何を渡した？ 3.y」。案 A の 3(作業用の一時置き場の commit_card.sh を
# repo に移したもの)。
#
# 使い方: sh scripts/analysis/commit_gate.sh "<コミットのメッセージ>"
#   メッセージはそのまま git commit -m に渡す(添え書きの行も含めて呼ぶ側が書く)。
#   押し出しはしない(押し出しの門は別。案 C の githooks/pre-push はオーナーの指示があるときだけ。A-16)。
# 止める(何もせず終了コード 1): scripts/check_findings_ledger.py の終了コードが 0 でない、または最後の行が
#   「問題 0」で終わらない / scripts/analysis/check_placeholders.py(既定の docs/ANALYSIS/*.md)の終了コードが 0 でない。
# 終了コード 2: メッセージが無い。
set -eu
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
cd "$ROOT"
if [ $# -lt 1 ] || [ -z "$1" ]; then
  echo "使い方: sh scripts/analysis/commit_gate.sh \"<コミットのメッセージ>\"" >&2
  exit 2
fi

rc=0
out=$(python3 scripts/check_findings_ledger.py 2>&1) || rc=$?
last=$(printf '%s\n' "$out" | tail -n 1)
if [ "$rc" -ne 0 ] || ! printf '%s\n' "$last" | grep -q '問題 0$'; then
  printf '%s\n' "$out"
  echo "止めた: 台帳の検査が問題 0 でない(終了コード $rc)。コミットしない" >&2
  exit 1
fi
echo "$last"

rc=0
ph=$(python3 scripts/analysis/check_placeholders.py 2>&1) || rc=$?
if [ "$rc" -ne 0 ]; then
  printf '%s\n' "$ph"
  echo "止めた: 分析の文書に仮置きがある(終了コード $rc)。コミットしない" >&2
  exit 1
fi
printf '%s\n' "$ph" | tail -n 1

git add -A docs/
git commit -q -m "$1"
git log --oneline -1 | cat
