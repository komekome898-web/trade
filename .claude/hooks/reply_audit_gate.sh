#!/bin/sh
# Stop フック — 2026-09-13、オーナー指示(L-156)により新設 / 同日 3 本の監査を受けて作り直し。
#
# オーナー逐語:
#   「**穴1 返答しようとするときにその出力に監査をかければいいのでは？**」
#   「**監査役の出力をそのままここに出力すればいいだけ。
#     指摘されたことを出さずに後でまとめて出すから書き換えるんやろ**」
#   「**そしてまたもや理由もなく手段を考えもせずできないと断定している。**」
#
# **初版の欠陥(監査 3 本が全部指摘した。すべて実測で確認済み)**:
#   1. `prompt_id` だけを鍵にしており、**返答本文を一切見ていなかった。**
#      → ACTION_LOG に一度「判定: 通す」が載れば、**本文をどう書き換えても通った。**
#      オーナーの語は「**その出力**に監査をかける」であって、ターンではない。
#   2. 判定の抽出が `awk`(該当行から**ファイル末尾まで**)だったため、
#      **後から別の節に書いた「判定: 通す」が、前の prompt_id の関門を開けた。**
#   3. push 側の関門にはある「監査役の名前」「本文 8 行以上」の確認が**入っていなかった。
#      塞いだはずの穴より弱かった。**
#   4. `prompt_id` や python3 が取れないと `exit 0`(素通り)だった。
#      push 側は「**判定できないときは通さない**」なのに逆向き。
#   5. **「判定: 止める」で詰んだとき、オーナーへ上申する経路が無かった。**
#      L-112 / CLAUDE.md §8 は「直す **か** 両論を添えてオーナーへ上申する」の 2 つの出口を
#      定めているのに、**関門が上申の側を物理的に塞いでいた。**

# --- 指紋の照合(フック・設定・監査役の定義)。返答のときも必ず走らせる ---
sh "$(dirname "$0")/_verify_manifest.sh" </dev/null || exit 2

INPUT="$(cat)"
ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
cd "$ROOT" 2>/dev/null || exit 0

command -v python3 >/dev/null 2>&1 || {
  echo "[返答の関門] python3 が無く判定できない。**判定できないときは通さない。**" >&2; exit 2; }

PID="$(printf '%s' "$INPUT" | python3 -c 'import json,sys
try: print((json.load(sys.stdin).get("prompt_id") or "")[:8])
except Exception: print("")' 2>/dev/null)"
REPLY="$(printf '%s' "$INPUT" | python3 -c 'import json,sys
try: sys.stdout.write(json.load(sys.stdin).get("last_assistant_message") or "")
except Exception: pass' 2>/dev/null)"

mkdir -p /tmp/hookprobe 2>/dev/null
printf '%s' "$REPLY" > /tmp/hookprobe/last_reply.txt

# 返答本文の指紋。**これが「その出力に監査をかける」の実体。**
SHA="$(printf '%s' "$REPLY" | sha256sum | cut -c1-16)"

[ -n "$PID" ] || { echo "[返答の関門] prompt_id が取れず判定できない。**判定できないときは通さない。**" >&2; exit 2; }

# --- 出口 2: オーナーへの上申(L-112 / CLAUDE.md §8) ---
# 「止める」をリードが単独で退けることはできないが、**両論を添えてオーナーへ上申する道は塞がない。**
# 上申と認めるのは、**返答本文に監査役の「判定: 止める」が逐語で含まれ、かつ「上申:」の行がある**場合だけ。
# = オーナーに止めの判定をそのまま見せたうえで渡す形。**黙って先へ進む抜け道にはならない。**
if printf '%s' "$REPLY" | grep -q '判定: 止める' && printf '%s' "$REPLY" | grep -q '^上申:'; then
  exit 0
fi

LOG="docs/AUDITOR/ACTION_LOG.md"
OK=0
if [ -f "$LOG" ]; then
  # **節はこの見出しからで切る**(旧版はファイル末尾まで拾い、後の節の判定を借りていた)
  SEC="$(awk -v k="返答sha256: $SHA" '
    index($0,k){f=1}
    f && /^## / && !index($0,k){ if(seen){exit} seen=1 }
    f{print}' "$LOG")"
  if [ -n "$SEC" ]; then
    V="$(printf '%s\n' "$SEC" | grep '^判定:' | head -1)"
    N="$(printf '%s\n' "$SEC" | grep -c '')"
    case "$V" in
      "判定: 通す"*)
        printf '%s\n' "$SEC" | grep -q 'owner-model-auditor' && [ "$N" -ge 8 ] && OK=1 ;;
    esac
  fi
fi
[ "$OK" = "1" ] && exit 0

cat >&2 <<EOF
[返答の関門] このターンを終わらせない。

理由: **いま出そうとしている返答本文**(sha256 先頭 16 桁: $SHA)について、
      ACTION_LOG に監査の記録が無い。

オーナー逐語(2026-09-13、L-156):
「**返答しようとするときにその出力に監査をかければいいのでは？**」

**鍵は prompt_id ではなく返答本文そのもの。**本文が 1 文字でも変われば、この指紋も変わる。
(初版は prompt_id を鍵にしており、一度通せば本文を書き換え放題だった。監査 3 本が指摘。)

出口は 2 つ。**どちらかを選ぶこと。**

【出口 1】監査を通す
 1. 返答の原文は /tmp/hookprobe/last_reply.txt にある(いま書き出した)
 2. \`owner-model-auditor\` を呼ぶ。渡すのは (a) この一手 (b) 応えているオーナーの逐語
    (c) **上の原文**
 3. 返ってきた指摘と 3 行の判定を、**逐語でこの会話に出す**(後でまとめない)
 4. ACTION_LOG に次を含む節を作る:
      「返答sha256: $SHA」/ 「owner-model-auditor」/ 監査役の返答の逐語(8 行以上)/
      行頭の「判定: 通す」
 5. **本文を 1 文字でも変えたら指紋が変わる。**変えたなら監査からやり直す

【出口 2】オーナーへ上申する(L-112 / CLAUDE.md §8)
 「止める」をリード単独で退けることはできないが、**両論を添えてオーナーへ渡す道は開いている。**
 返答本文に次の両方を入れること:
   - 監査役の「**判定: 止める**」を**逐語で**(オーナーに判定をそのまま見せる)
   - 行頭に「**上申:**」で始まる行(何を判断してほしいか)
 これを満たせばターンを終えられる。**黙って先へ進む抜け道にはならない。**
EOF
exit 2
