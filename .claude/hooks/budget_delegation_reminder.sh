#!/bin/sh
# PreToolUse hook (matcher: Read|Write) — I-007 / L-136: リードのトークン消費を抑える導線(表示のみ)。
# 大きいファイルをリードが丸ごと読む / 長い文書をリードが自分で書く のは Fable の枠を最も削る型。
# Read: offset/limit なしで 300 行超のファイル → 「要点抽出を下位モデルに委任」を表示。
# Write: docs/ 以下に 150 行超を書く → 「下位モデルに書かせてリードは差分を読む」を表示。
# 失敗しても常に exit 0。
export LC_ALL=C.utf8 2>/dev/null || true
INPUT="$(cat 2>/dev/null || true)"
TOOL="$(printf '%s' "$INPUT" | sed -n 's/.*"tool_name" *: *"\([^"]*\)".*/\1/p' | head -n1)"
FILE_PATH="$(printf '%s' "$INPUT" | sed -n 's/.*"file_path" *: *"\([^"]*\)".*/\1/p' | head -n1)"
[ -z "$FILE_PATH" ] && exit 0
MSG=""
case "$TOOL" in
  Read)
    if [ -f "$FILE_PATH" ] && ! printf '%s' "$INPUT" | grep -q '"offset"\|"limit"'; then
      N="$(wc -l < "$FILE_PATH" 2>/dev/null | tr -d ' ')"
      if [ "${N:-0}" -gt 300 ]; then
        MSG="[消費の導線 I-007] ${N} 行のファイルをリードが丸ごと読もうとしている。要点だけ要るなら下位モデルに抽出を委任する(L-080)。必要な範囲だけなら offset/limit で読む。"
      fi
    fi ;;
  Write)
    case "$FILE_PATH" in
      */docs/*|docs/*)
        N="$(printf '%s' "$INPUT" | sed -n 's/.*"content" *: *"\(.*\)"[^"]*$/\1/p' | awk -F'\\\\n' '{print NF}')"
        if [ "${N:-0}" -gt 150 ]; then
          MSG="[消費の導線 I-007] docs/ に約 ${N} 行をリードが自分で書こうとしている。骨子(見出しと 1 行ずつの要点)だけ書いて本文は下位モデルに委任し、リードは差分を読む(L-080)。"
        fi ;;
    esac ;;
esac
[ -z "$MSG" ] && exit 0
E="$(printf '%s' "$MSG" | sed 's/\\/\\\\/g; s/"/\\"/g')"
printf '{"systemMessage":"%s","hookSpecificOutput":{"hookEventName":"PreToolUse","additionalContext":"%s"}}' "$E" "$E"
exit 0
