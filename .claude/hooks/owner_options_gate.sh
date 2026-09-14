#!/bin/sh
# ③(b) 選択を待つ間は止まる — オーナー選択「**案 A(全面停止)**」(2026-09-14、L-169)
#
# オーナー逐語(L-168):
#   「**「着手前の対応表に右が空の行があるとき、規則とゴールに則り案をいくつか提示し、
#     オーナーが選択するまで次の道具を呼べないようにする。」なら検討の価値はあります**」
# オーナー選択(L-169): 「**→A**」= **全面停止。**
#   リードが提案した部分停止(案 B =「依存しない部分は続行する」)は**採らない。**
#   逃げ道を作らない、というのがオーナーの決定である。
#
# 2 つのイベントで呼ばれる。
#   PreToolUse      : 待ち状態なら**すべての道具を拒否する**(matcher は全件)。
#   UserPromptSubmit: オーナーが発言したので待ち状態を解除する。
#
# 待ち状態の作り方: `.claude/skills/owner-options` が
#   `.claude/state/awaiting_owner_choice` に「何を聞いているか」の 1 行を書く。
#
# **発火条件は 2 系統ある(`PLAN.md` ③(b))。**
#   自己申告系: リードが「表に空欄がある」と書いたとき → スキルが待ち状態を作る。
#               **表を書かなければ発火しない。**Theorem 2 が「テキストからは検出できない」と
#               言う channel そのものである。
#   行動系    : オーナーの発言以降にゴールを一度も読まずに新しい作業単位の最初の Write を
#               出そうとしたとき。**こちらはログ上の事実で発火するので、記述に依存しない。**
#               → 下の GOAL 検査。
set -u
INPUT="$(cat 2>/dev/null || true)"
ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null)}"
[ -n "$ROOT" ] || ROOT="$(pwd)"
STATE="$ROOT/.claude/state"
WAIT="$STATE/awaiting_owner_choice"
SEEN="$STATE/goal_seen_this_turn"

EVENT="$(printf '%s' "$INPUT" | python3 -c '
import json,sys
try: d=json.load(sys.stdin)
except Exception: sys.exit(0)
print(d.get("hook_event_name",""))
' 2>/dev/null)"

# --- オーナーが発言した: 待ちを解除し、ゴール既読の印も落とす ---
if [ "$EVENT" = "UserPromptSubmit" ]; then
  rm -f "$WAIT" "$SEEN" 2>/dev/null
  exit 0
fi

# --- 待ち状態なら、道具を 1 つも通さない(案 A = 全面停止) ---
if [ -f "$WAIT" ]; then
  cat >&2 <<EOF
[関門] オーナーの選択待ちなので、道具を呼べない(全面停止)。

聞いていること:
$(cat "$WAIT" 2>/dev/null | head -20)

オーナー逐語(L-168 / 選択は L-169 の「→A」):
「**オーナーが選択するまで次の道具を呼べないようにする**」

**「その行に依存しない部分は続行する」という部分停止(案 B)はオーナーが採らなかった。**
選択が返るまで待つこと。**待ち状態の解除はオーナーの発言だけが行う。**
EOF
  exit 2
fi

mkdir -p "$STATE" 2>/dev/null

TOOL="$(printf '%s' "$INPUT" | python3 -c '
import json,sys
try: d=json.load(sys.stdin)
except Exception: sys.exit(0)
print(d.get("tool_name",""))
' 2>/dev/null)"
FP="$(printf '%s' "$INPUT" | python3 -c '
import json,sys
try: d=json.load(sys.stdin)
except Exception: sys.exit(0)
print((d.get("tool_input") or {}).get("file_path","") or "")
' 2>/dev/null)"

# ゴール・逐語を読んだら印を付ける(この手ではもう聞かない)
case "$TOOL:$FP" in
  Read:*PROJECT_GOAL.md|Read:*OWNER_MODEL_SOURCE.md|Read:*OWNER_INTENT*)
    : > "$SEEN" 2>/dev/null; exit 0 ;;
esac

# --- 行動系: ゴールを読まずに書き始めようとしたら止める ---
case "$TOOL" in
  Write|Edit|NotebookEdit) ;;
  *) exit 0 ;;
esac
[ -f "$SEEN" ] && exit 0

# 記録そのものを書く手は例外(止めると逐語が貼れなくなり、I-009 を悪化させる)
case "$FP" in
  *OWNER_LOG.md|*OWNER_STATUS.md|*ACTION_LOG.md|*/docs/AUDITOR/TRACE/*) exit 0 ;;
esac

cat >&2 <<EOF
[関門] この手では、まだゴールとオーナーの逐語を一度も開いていない。

止めた操作: $TOOL $FP

2026-09-14 の実測: この会話の道具呼び出し 1,054 回のうち
  docs/PROJECT_GOAL.md            を開いた回数 = **0**
  docs/OWNER_INTENT_2026-09-12.md を開いた回数 = **0**(書き換えは 1 回)
一方、監査役は 50 回とも、検査の前にオーナーの逐語を必ず読む定義になっている。

**この関門はテキストではなく行動で発火する。**「読んだ」と書いても通らない。
次のどちらかをしてから、もう一度この操作をすること:
  1. docs/PROJECT_GOAL.md か docs/AUDITOR/OWNER_MODEL_SOURCE.md を Read で開く
  2. §0.1 の対応表に空行があるなら /owner-options で案を出し、オーナーの選択を待つ
EOF
exit 2
