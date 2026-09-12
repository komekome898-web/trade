#!/bin/sh
# UserPromptSubmit hook — I-006 / L-130: 状態板を「書く場所」から「毎回読む対象」にする導線。
# オーナーが発言するたびに、状態板の要点(共有経路の死活・進行中の順序と現在地・
# オーナーに今求めている行動・恒久規則)をリードの目の前に出す。表示のみ。
# 状態板に書いただけでは読まれない(I-006 の根本原因)ので、読む側を機械で保証する。
# 失敗しても常に exit 0。

export LC_ALL=C.utf8 2>/dev/null || true
ROOT="$(cd "$(dirname "$0")/../.." && pwd)" || exit 0
cd "$ROOT" 2>/dev/null || exit 0

HEART="共有経路: 不明"
if command -v git >/dev/null 2>&1 && [ -d "$ROOT/.git" ]; then
    LAST_TS="$(git log -1 --format=%ct -- paper_logs 2>/dev/null || true)"
    if [ -n "$LAST_TS" ]; then
        AGE_H=$(( ($(date +%s) - LAST_TS) / 3600 ))
        LAST_STR="$(git log -1 --format=%ci -- paper_logs 2>/dev/null || true)"
        if [ "$AGE_H" -gt 26 ]; then
            HEART="!!! 共有が途絶えている: 最後の paper_logs 共有コミット ${LAST_STR}(${AGE_H} 時間前)。届くと約束しない"
        else
            HEART="共有経路: 最後の共有コミット ${LAST_STR}(${AGE_H} 時間前)"
        fi
    fi
fi

BUDGET="$(grep -E "^\| 週間トークン上限" "$ROOT/docs/OWNER_STATUS.md" 2>/dev/null | awk -F"|" '{print $3}' | cut -c1-200 || true)"
ROWS=""
if [ -f "$ROOT/docs/OWNER_STATUS.md" ]; then
    # 太字で始まる行 = 進行中の項目と恒久規則。各行は 320 文字で切る(要点だけ)。
    ROWS="$(grep -E '^\| \*\*' "$ROOT/docs/OWNER_STATUS.md" 2>/dev/null | cut -c1-320 || true)"
    NEXT="$(grep -E '^\| PC 運用' "$ROOT/docs/OWNER_STATUS.md" 2>/dev/null | awk -F'|' '{print $5}' | cut -c1-300 || true)"
fi

MSG="[状態板の要点 — 返答の前に読む(I-006)]
${HEART}
トークン(最終報告値。自主上限 70% を超えたら重い工程を止める = 規則、提案ではない):${BUDGET}
オーナーに今求めている行動:${NEXT:- (無し)}
進行中の項目と恒久規則:
${ROWS:-(状態板が読めない)}
規則: オーナーに見える文は日本語のみ / 有料インフラは提案しない / 出力の再送を求めない(共有で届くものは自分で確認)"

ESCAPED="$(printf '%s' "$MSG" | sed 's/\\/\\\\/g; s/"/\\"/g' | awk '{printf "%s\\n", $0}' | sed 's/\\n$//')"
printf '{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"%s"}}' "$ESCAPED"
exit 0
