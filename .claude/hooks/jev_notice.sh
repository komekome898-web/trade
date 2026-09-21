#!/bin/sh
# Stop フック — Jev の検査結果を**表示するだけ**。何も止めない。必ず exit 0。
#
# オーナー逐語(L-218、2026-09-19):
#   「**表示だけの形でStopに足せ。そもそも止めるとjev出させようとするのは間違った運用で、
#     判断はLLMと私の役割である。**」
#
# やること: 返答の切れ目で、この作業木で変わった docs/ 配下の Markdown(記録系を除く、最大 5 本)に
# `scripts/jev_check.py audit --summary` を当て、その末尾 1 行を systemMessage として表示する。
# 加えて `.claude/state/jev_last_notice.txt` に同じ行を残す(リードが次の手で読むため)。
# Jev に届かないときはスクリプトが「未到達」と出す。スクリプト自体が落ちたら「実行失敗」と出す。
# 沈黙は「対象の文書が無かった」ときだけ。
set -u
INPUT="$(cat 2>/dev/null || true)"
ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null)}"
[ -n "$ROOT" ] || ROOT="$(pwd)"
cd "$ROOT" 2>/dev/null || exit 0
EVENT="$(printf '%s' "$INPUT" | python3 -c 'import json,sys
try: print(json.load(sys.stdin).get("hook_event_name",""))
except Exception: print("")' 2>/dev/null)"
[ "$EVENT" = "Stop" ] || exit 0

# 対象: 作業木の変更 + 追跡外 + 直近 3 コミット の docs/**/*.md。記録系は除く。
FILES="$( { git diff --name-only HEAD -- 'docs/*.md' 'docs/**/*.md' 2>/dev/null
            git ls-files --others --exclude-standard -- 'docs/*.md' 'docs/**/*.md' 2>/dev/null
            git diff --name-only HEAD~3..HEAD -- 'docs/*.md' 'docs/**/*.md' 2>/dev/null; } \
          | grep -vE 'OWNER_LOG|OWNER_STATUS|OWNER_PROCEDURES|ACTION_LOG|INCIDENTS|HOOK_MANIFEST|/TRACE/|/VERDICTS/|/before/|/answers/|DATA_CONSUMPTION_LOG|NEGATIVE_FACTS|docs/DATA\.md|/READDO/|_inventories/' \
          | sort -u | head -5 )"
# 返答そのもの(最後の assistant 発言)の検査 — 取れない × 経路一覧、対応表の左右(L-220 の 2)。表示だけ。
REPLY_LINE="$(PYTHONPATH="$ROOT" timeout 60 python3 "$ROOT/scripts/jev_reply.py" --last-assistant --summary 2>/dev/null | tail -1)"
[ -n "$REPLY_LINE" ] || REPLY_LINE="jev: 実行失敗(返答の検査が出力を返さなかった)"
[ -n "$FILES" ] || FILES=""

STATE="$ROOT/.claude/state"; mkdir -p "$STATE" 2>/dev/null
OUT=""
for f in $FILES; do
  [ -f "$f" ] || continue
  line="$(PYTHONPATH="$ROOT" timeout 60 python3 "$ROOT/scripts/jev_check.py" audit "$f" --out "$ROOT/data/jev/check" --summary 2>/dev/null | tail -1)"
  [ -n "$line" ] || line="jev: 実行失敗(スクリプトが出力を返さなかった)"
  OUT="${OUT}${f}: ${line}
"
done
OUT="返答: ${REPLY_LINE}
${OUT}"
printf '%s' "$OUT" > "$STATE/jev_last_notice.txt" 2>/dev/null
printf '%s' "$OUT" | python3 -c 'import json,sys
msg=sys.stdin.read().rstrip("\n")
print(json.dumps({"systemMessage": "jev(表示だけ、判断は LLM とオーナー):\n"+msg}, ensure_ascii=False))' 2>/dev/null
exit 0
