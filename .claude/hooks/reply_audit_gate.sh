#!/bin/sh
# Stop フック — 2026-09-13、オーナー指示(L-156)により新設。
#
# オーナー逐語:
#   「**穴1 返答しようとするときにその出力に監査をかければいいのでは？**」
#   「**そしてまたもや理由もなく手段を考えもせずできないと断定している。**」
#
# リードは「返答はツールを経ないので関門を掛けられない」と断定していた。**誤りだった。**
# Stop フックは `exit 2` でターンの終了を実際に止め、payload に
# `last_assistant_message`(返答そのもの)と `prompt_id`(このターンの識別子)を含む。
# (2026-09-13 に調査用フックで実測。憶測ではない。)
#
# 判定: **この prompt_id について、ACTION_LOG に監査の記録(判定: 通す)が無ければターンを終わらせない。**
#       返答の原文は /tmp/hookprobe/ に出すので、監査役にはそれを読ませる。

INPUT="$(cat)"
ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
cd "$ROOT" 2>/dev/null || exit 0

PID="$(printf '%s' "$INPUT" | python3 -c 'import json,sys
try: print(json.load(sys.stdin).get("prompt_id","") or "")
except Exception: print("")' 2>/dev/null)"
[ -n "$PID" ] || exit 0

# 返答の原文を書き出す(監査役に読ませるため)
mkdir -p /tmp/hookprobe 2>/dev/null
printf '%s' "$INPUT" | python3 -c 'import json,sys,os
try:
    d=json.load(sys.stdin)
    open("/tmp/hookprobe/last_reply.txt","w").write(d.get("last_assistant_message","") or "")
except Exception: pass' 2>/dev/null

LOG="docs/AUDITOR/ACTION_LOG.md"
SHORT="$(printf '%s' "$PID" | cut -c1-8)"

# この prompt_id の節に、行頭の「判定: 通す」があるか
if [ -f "$LOG" ] && grep -q "prompt_id: $SHORT" "$LOG"; then
  SEC="$(awk -v k="prompt_id: $SHORT" 'index($0,k){f=1} f' "$LOG")"
  V="$(printf '%s\n' "$SEC" | grep '^判定:' | tail -1)"
  case "$V" in
    "判定: 通す"*) exit 0 ;;
  esac
fi

cat >&2 <<EOF
[返答の関門] このターンを終わらせない。

理由: この一手(prompt_id: $SHORT)について、監査の記録が ACTION_LOG に無い。

オーナー逐語(2026-09-13、L-156):
「**返答しようとするときにその出力に監査をかければいいのでは？**」
「**監査役の出力をそのままここに出力すればいいだけ。
  指摘されたことを出さずに後でまとめて出すから書き換えるんやろ**」

やること:
 1. **いまの返答の原文は /tmp/hookprobe/last_reply.txt にある。**これを監査役に読ませる
 2. \`owner-model-auditor\` を呼ぶ。渡すのは (a) この一手 (b) 応えているオーナーの逐語
    (c) **上の返答の原文**
 3. 返ってきた指摘と 3 行の判定を、**逐語でこの会話に出す**(後でまとめない)
 4. ACTION_LOG に「prompt_id: $SHORT」を含む節を作り、監査役の返答を逐語で貼る
    (判定の 3 行は行頭・逐語。引用記号も語の追加もしない)
 5. 「判定: 止める」なら直してから再監査。**通すまでターンは終わらない**
EOF
exit 2
