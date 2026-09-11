#!/bin/sh
# PreToolUse hook (matcher: Write|Edit) — L-102/L-103: 規則を読む導線(表示のみ・
# チェックもブロックも行わない)。対象パスが docs/PHASE2/**/*PREREG*.md または
# docs/**/*_PREREG.md に一致するときだけ、CLAUDE.md と research-protocol §1 の
# 該当行を実行時に読んで表示する。失敗しても常に exit 0(作業を止めない)。

set -e

export LC_ALL=C.utf8 2>/dev/null || true

INPUT="$(cat 2>/dev/null || true)"

FILE_PATH=""
if command -v jq >/dev/null 2>&1; then
    FILE_PATH="$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null || true)"
fi
if [ -z "$FILE_PATH" ]; then
    # jq が無い/失敗した場合の簡易フォールバック
    FILE_PATH="$(printf '%s' "$INPUT" | sed -n 's/.*"file_path" *: *"\([^"]*\)".*/\1/p' | head -n1)"
fi

[ -z "$FILE_PATH" ] && exit 0

MATCH=0
case "$FILE_PATH" in
    */docs/PHASE2/*PREREG*.md|docs/PHASE2/*PREREG*.md) MATCH=1 ;;
esac
case "$FILE_PATH" in
    */docs/*_PREREG.md|docs/*_PREREG.md) MATCH=1 ;;
esac

[ "$MATCH" = "1" ] || exit 0

ROOT="$(cd "$(dirname "$0")/../.." && pwd)" || exit 0
CLAUDE_MD="$ROOT/CLAUDE.md"
PROTOCOL="$ROOT/.claude/skills/research-protocol/SKILL.md"

RULE1=""
if [ -f "$CLAUDE_MD" ]; then
    RULE1="$(grep -m1 "取れない・無い" "$CLAUDE_MD" 2>/dev/null \
        | sed -E 's/^- //; s/\*\*//g' \
        | sed -E 's/^([^。]*。[^。]*。[^。]*。).*/\1/')"
fi

RULE2=""
if [ -f "$PROTOCOL" ]; then
    RULE2="$(grep -A3 -m1 "3 分類で明記" "$PROTOCOL" 2>/dev/null \
        | tr '\n' ' ' | sed -E 's/\*\*//g; s/ +/ /g' \
        | sed -E 's/^([^。]*。[^。]*。).*/\1/')"
fi

[ -z "$RULE1" ] && RULE1="(CLAUDE.md §5.2 の該当行が見つからない)"
[ -z "$RULE2" ] && RULE2="(research-protocol §1 の該当行が見つからない)"

MSG="[規則を読む導線] データの主張(CLAUDE.md §5.2): ${RULE1}
出所分類(research-protocol §1): ${RULE2}"

ESCAPED="$(printf '%s' "$MSG" | sed 's/\\/\\\\/g; s/"/\\"/g' | awk '{printf "%s\\n", $0}' | sed 's/\\n$//')"

printf '{"systemMessage":"%s","hookSpecificOutput":{"hookEventName":"PreToolUse","additionalContext":"%s"}}' "$ESCAPED" "$ESCAPED"

exit 0
