#!/bin/sh
# PreToolUse hook (matcher: Bash) — L-112: git push の直前に「納品前の監査」を思い出させる導線。
# 表示のみ。チェックもブロックもしない。常に exit 0。
set -e
INPUT="$(cat 2>/dev/null || true)"
case "$INPUT" in
  *"git push"*) ;;
  *) exit 0 ;;
esac
MSG="[権限の順位 L-112] オーナー > 監査役 > リード。docs/ の納品物(事前登録・報告・調査・手順)を push する前に owner-auditor を通したか。監査の記録 docs/AUDITOR/VERDICTS/ に ID があるか。「止める」をリード単独で退けていないか(直す か オーナーへ上申)。"
ESCAPED="$(printf '%s' "$MSG" | sed 's/\\/\\\\/g; s/"/\\"/g')"
printf '{"systemMessage":"%s","hookSpecificOutput":{"hookEventName":"PreToolUse","additionalContext":"%s"}}' "$ESCAPED" "$ESCAPED"
exit 0
