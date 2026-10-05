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
#   メッセージはそのまま git commit -m に渡す。添え書きの行(Claude-Session: …)も呼ぶ側が書く。
#   押し出しはしない(押し出しの門は別。案 C の githooks/pre-push はオーナーの指示があるときだけ。A-16)。
# 止める(何もせず終了コード 1):
#   - メッセージに「Claude-Session:」の行が無い
#   - 検査の台本(scripts/check_findings_ledger.py・scripts/analysis/check_placeholders.py)が無い
#   - 台帳の検査の終了コードが 0 でない、または最後の行が「問題 0」で終わらない(両方を見る)
#   - 仮置きの検査(docs/ANALYSIS/ の下の .md 全部。下の階層も)の終了コードが 0 でない
#   - index(git add 済み)に docs/ の外のファイルがある(この門は docs/ だけをコミットする)
# 終了コード 2: メッセージが無い。
set -eu
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
cd "$ROOT"
if [ $# -lt 1 ] || [ -z "$1" ]; then
  echo "使い方: sh scripts/analysis/commit_gate.sh \"<コミットのメッセージ>\"" >&2
  exit 2
fi
if ! printf '%s\n' "$1" | grep -q '^Claude-Session: '; then
  echo "止めた: メッセージに「Claude-Session: …」の行が無い。コミットしない" >&2
  exit 1
fi

LEDGER_CHECK=scripts/check_findings_ledger.py
PH_CHECK=scripts/analysis/check_placeholders.py
for f in "$LEDGER_CHECK" "$PH_CHECK"; do
  if [ ! -f "$f" ]; then
    echo "止めた: 検査の台本 $f が無い。コミットしない" >&2
    exit 1
  fi
done

rc=0
out=$(python3 "$LEDGER_CHECK" 2>&1) || rc=$?
last=$(printf '%s\n' "$out" | tail -n 1)
if [ "$rc" -ne 0 ] || ! printf '%s\n' "$last" | grep -q '問題 0$'; then
  printf '%s\n' "$out"
  echo "止めた: 台帳の検査が問題 0 でない(終了コード $rc、最後の行「$last」)。コミットしない" >&2
  exit 1
fi
echo "$last"

rc=0
ph=$(python3 "$PH_CHECK" 2>&1) || rc=$?
if [ "$rc" -ne 0 ]; then
  printf '%s\n' "$ph"
  echo "止めた: 分析の文書に仮置きがある(終了コード $rc)。コミットしない" >&2
  exit 1
fi
printf '%s\n' "$ph" | tail -n 1

outside=$(git diff --cached --name-only | grep -v '^docs/' || true)
if [ -n "$outside" ]; then
  printf '%s\n' "$outside"
  echo "止めた: index に docs/ の外のファイルがある(上の一覧)。この門は docs/ だけをコミットする" >&2
  exit 1
fi

git add -A docs/
git commit -q -m "$1"
git log --oneline -1 | cat
