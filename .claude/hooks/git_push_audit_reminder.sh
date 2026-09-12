#!/bin/sh
# PreToolUse hook (matcher: Bash) — L-112: git push の直前に「納品前の監査」を思い出させる導線。
# 表示のみ。チェックもブロックもしない。常に exit 0。
#
# 発火条件(L-144 で限定。以前は入力文字列のどこかに "git push" があれば発火し、
# ヒアドキュメント内の説明文にも誤発火していた):
#   (1) 実行するコマンドのいずれかの区切りが `git push` で始まる、かつ
#   (2) docs/ 配下の納品物がステージされている
set -e

INPUT="$(cat 2>/dev/null || true)"

FIRE="$(printf '%s' "$INPUT" | python3 -c '
import json, re, sys
try:
    cmd = json.load(sys.stdin).get("tool_input", {}).get("command", "")
except Exception:
    sys.exit(0)
# &&, ||, ;, | , 改行 で区切った各セグメントの先頭が git push か
for seg in re.split(r"&&|\|\||;|\||\n", cmd):
    if re.match(r"\s*git\s+push\b", seg):
        print("1")
        break
' 2>/dev/null || true)"

[ "$FIRE" = "1" ] || exit 0

ROOT="$(cd "$(dirname "$0")/../.." && pwd)" || exit 0
STAGED="$(git -C "$ROOT" diff --cached --name-only 2>/dev/null | grep '^docs/' || true)"
[ -n "$STAGED" ] || exit 0

MSG="[権限の順位 L-112] オーナー > 監査役 > リード。docs/ の納品物(事前登録・報告・調査・手順)を push する前に owner-auditor を通したか。監査の記録 docs/AUDITOR/VERDICTS/ に ID があるか。「止める」をリード単独で退けていないか(直す か オーナーへ上申)。"
ESCAPED="$(printf '%s' "$MSG" | sed 's/\\/\\\\/g; s/"/\\"/g')"
printf '{"systemMessage":"%s","hookSpecificOutput":{"hookEventName":"PreToolUse","additionalContext":"%s"}}' "$ESCAPED" "$ESCAPED"
exit 0
