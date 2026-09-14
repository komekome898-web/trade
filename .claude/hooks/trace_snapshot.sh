#!/bin/sh
# ① 行動チャネルの記録 — SessionStart(在処を保存)/ Stop(TRACE を更新)
#
# オーナー承認 2026-09-14、L-169。
#
# ここでやるのは 2 つだけ。
#   1. 会話の記録(JSONL)の在処を `.claude/state/transcript_path` に落とす。
#      ハーネスがフックに渡す `transcript_path` は、リードが書いたものではない。
#   2. 返答の切れ目で `scripts/trace_metrics.py` を走らせ、TRACE を更新する。
#
# **何も止めない。**必ず exit 0 する(記録が失敗しても作業を止めない。
#  記録が無いこと自体は `trace_metrics.py` が例外で知らせる)。
set -u
INPUT="$(cat 2>/dev/null || true)"
ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null)}"
[ -n "$ROOT" ] || ROOT="$(pwd)"
STATE="$ROOT/.claude/state"
mkdir -p "$STATE" 2>/dev/null

TP="$(printf '%s' "$INPUT" | python3 -c '
import json,sys
try: d=json.load(sys.stdin)
except Exception: sys.exit(0)
print(d.get("transcript_path","") or "")
' 2>/dev/null)"
[ -n "$TP" ] && printf '%s\n' "$TP" > "$STATE/transcript_path" 2>/dev/null

EVENT="$(printf '%s' "$INPUT" | python3 -c '
import json,sys
try: d=json.load(sys.stdin)
except Exception: sys.exit(0)
print(d.get("hook_event_name",""))
' 2>/dev/null)"

if [ "$EVENT" = "Stop" ]; then
  python3 "$ROOT/scripts/trace_metrics.py" >/dev/null 2>&1 || true
fi
exit 0
