#!/bin/sh
# SessionStart hook — L-102/L-103: 規則を読む導線(表示のみ・チェックもブロックも
# 行わない)。直近7日でデータ共有ディレクトリに届いたファイルの一覧と、
# docs/OWNER_STATUS.md の冒頭を表示する。パスと件数のみ・秘密情報は出さない。
# 失敗しても常に exit 0(起動を止めない)。

set -e

export LC_ALL=C.utf8 2>/dev/null || true

ROOT="$(cd "$(dirname "$0")/../.." && pwd)" || exit 0
cd "$ROOT" 2>/dev/null || exit 0

FILES=""
if command -v git >/dev/null 2>&1 && [ -d "$ROOT/.git" ]; then
    FILES="$(git log --since=7.days --name-only --pretty=format: -- \
        'backtest_data/auto_*' 'paper_logs' 'data/tape' 'data/latency' 2>/dev/null \
        | sed '/^$/d' | sort -u || true)"
fi

TOTAL=0
[ -n "$FILES" ] && TOTAL="$(printf '%s\n' "$FILES" | sed '/^$/d' | wc -l | tr -d ' ')"

if [ -z "$FILES" ] || [ "$TOTAL" = "0" ]; then
    LIST_BLOCK="新着なし"
else
    if [ "$TOTAL" -gt 40 ]; then
        REMAIN=$((TOTAL - 40))
        LIST_BLOCK="$(printf '%s\n' "$FILES" | head -n 40)
...and ${REMAIN} more"
    else
        LIST_BLOCK="$FILES"
    fi
fi

STATUS_HEAD=""
if [ -f "$ROOT/docs/OWNER_STATUS.md" ]; then
    STATUS_HEAD="$(head -n 15 "$ROOT/docs/OWNER_STATUS.md" 2>/dev/null || true)"
else
    STATUS_HEAD="(docs/OWNER_STATUS.md が見つからない)"
fi

MSG="前回以降に届いた共有ファイル
${LIST_BLOCK}

--- docs/OWNER_STATUS.md (先頭15行) ---
${STATUS_HEAD}"

ESCAPED="$(printf '%s' "$MSG" | sed 's/\\/\\\\/g; s/"/\\"/g' | awk '{printf "%s\\n", $0}' | sed 's/\\n$//')"

printf '{"systemMessage":"%s","hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"%s"}}' "$ESCAPED" "$ESCAPED"

exit 0
