#!/bin/sh
# PreToolUse hook (matcher: Agent) — L-102/L-103: 規則を読む導線(表示のみ・チェックも
# ブロックも行わない)。CLAUDE.md §5.2 の該当行を実行時に grep して表示するので、
# 本文を書き換えても文言はドリフトしない。失敗しても常に exit 0(作業を止めない)。

set -e

export LC_ALL=C.utf8 2>/dev/null || true

ROOT="$(cd "$(dirname "$0")/../.." && pwd)" || exit 0
CLAUDE_MD="$ROOT/CLAUDE.md"

RULE=""
if [ -f "$CLAUDE_MD" ]; then
    RULE="$(grep -m1 "取れない・無い" "$CLAUDE_MD" 2>/dev/null || true)"
    # 太字記号を落とし、先頭3文で止める(マルチバイト境界で切らないよう、
    # 固定バイト数の cut ではなく句点(。)単位で切る)
    RULE="$(printf '%s' "$RULE" | sed -E 's/^- //; s/\*\*//g' | sed -E 's/^([^。]*。[^。]*。[^。]*。).*/\1/')"
fi

if [ -z "$RULE" ]; then
    RULE="(CLAUDE.md §5.2 の該当行が見つからない。CLAUDE.md §5.2 を直接確認してください)"
fi

MSG="[規則を読む導線] CLAUDE.md §5.2: ${RULE}
調達票: 経路 3 つ以上・到達確認の日付・プローブの生ログ"

# JSON文字列としてエスケープ(改行->\n, ダブルクオート->\", バックスラッシュ->\\)
ESCAPED="$(printf '%s' "$MSG" | sed 's/\\/\\\\/g; s/"/\\"/g' | awk '{printf "%s\\n", $0}' | sed 's/\\n$//')"

printf '{"systemMessage":"%s","hookSpecificOutput":{"hookEventName":"PreToolUse","additionalContext":"%s"}}' "$ESCAPED" "$ESCAPED"

exit 0
