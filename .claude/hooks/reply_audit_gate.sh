#!/bin/sh
# Stop フック — 2026-09-13、オーナー指示(L-156)により新設 / 同日 4 本の監査を受けて作り直し。
#
# オーナー逐語:
#   「**穴1 返答しようとするときにその出力に監査をかければいいのでは？**」
#   「**監査役の出力をそのままここに出力すればいいだけ。
#     指摘されたことを出さずに後でまとめて出すから書き換えるんやろ**」
#   「**そしてまたもや理由もなく手段を考えもせずできないと断定している。**」
#
# **初版の欠陥(監査 3 本が全部指摘。すべて実測で確認済み)**:
#   1. `prompt_id` だけを鍵にしており、**返答本文を一切見ていなかった。**
#   2. 判定の抽出がファイル末尾まで伸び、後の節の「判定: 通す」が前の関門を開けた。
#   3. push 側にある「監査役の名前」「本文 8 行以上」の確認が入っていなかった。
#   4. `prompt_id` や python3 が取れないと素通りだった。
#   5. 「判定: 止める」で詰んだとき、オーナーへ上申する経路が無かった(L-112 違反)。
#
# **2 版の欠陥(4 本目の監査が実測した。これがこの版で直すもの)**:
#   6. **上申の出口が文字列 2 つで開いた。**本文のどこかに `判定: 止める` があり、
#      行頭に `上申:` の行があれば通った。**その判定が監査役のものである保証が無く、
#      本文の残りを一切見ていなかった。**実測で「監査を一度も通していない任意の本文」が通った。
#      リードは「黙って先へ進む抜け道にはならない」と書いていたが、**事実と違った。**
#   7. **穴 3 に機械が付いていなかった。**逐語 8 行以上を要求していたのは
#      **ACTION_LOG の中身**であって、**オーナーが見る返答本文ではなかった。**
#      オーナーの語は「**監査役の出力をそのままここに出力すればいい**」である。
#
# **4 版(2026-09-18、L-197「全てOKです。」でオーナーが承認した検査の形)**:
#   L-196 オーナー逐語「**監査役の効果が信頼できるので、監査役の逐語は私が求めた時に出力するようにしてください**」
#   により、「逐語 8 行以上を返答本文に貼る」検査(3 版の穴 3 の機械)を外し、代わりに
#   **返答本文に、その監査の記録がある ACTION_LOG の節の名前(例: ACTION_LOG 057)があること**を要求する。
#   逐語は台帳の節に残す(8 行以上はそちらで要求する)。指紋は今までどおり返答本文から計算して節を探す。
#   上申の文面(返答 057 §4、監査 9 巡で通したもの): 「ACTION_LOG の節に逐語・監査役の名前・行頭の判定があり、
#   本文にはその節の名前(例: ACTION_LOG 057)だけを置く。指紋(返答 sha256)は今と同じく関門が本文から計算して節を探す」
#
# **この版の判定(両方の出口に同じ実体を要求する)**:
#   ACTION_LOG に「返答sha256: <この返答の指紋>」の節があり、その節が
#     - `owner-model-auditor` を含み
#     - 「### 監査役の返答(逐語)」の塊を持ち、その実質行が 8 行以上あり
#     - **その節を含む「## 」見出しの名前(先頭の語。例: 057 / 抜き取り 005)が、返答本文に
#       「ACTION_LOG <名前>」の形で書かれている**  ← 4 版の機械(逐語は台帳、本文は節の名前)
#   そのうえで、節の判定が
#     - 「判定: 通す」          → 通す
#     - 「判定: 止める」        → **行頭「上申:」の行があるときだけ**通す(L-112 の 2 つ目の出口)
#   それ以外は通さない。**判定できないときは通さない。**
#
# **5 版(2026-09-18、L-200 オーナー指示)**:
#   オーナー逐語「**・返答の関門を「オーナーが明示した最終報告にだけ掛ける」形に直す(L-198「途中経過には掛けない」を
#   機械に反映する。フックの変更なので指示が要る)。早急にこの3点を実施してください。**」
#   経緯: 返答の関門が状況報告(監査を掛けるなという指示のもとの返答)にも掛かり、会話が終われなくなった。
#   **この版の機械**: 返答本文に行頭「【最終報告】」の行があるときだけ上の判定を行う。
#   無ければ途中経過・状況報告として通す(exit 0)。最終報告かどうかを決めるのはリードが本文に置く印であり、
#   印の無い返答は監査を通っていないことを意味する(台帳にも節が無い)。

# --- 指紋の照合(フック・設定・監査役の定義)。返答のときも必ず走らせる ---
sh "$(dirname "$0")/_verify_manifest.sh" </dev/null || exit 2

INPUT="$(cat)"
ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
cd "$ROOT" 2>/dev/null || exit 0

command -v python3 >/dev/null 2>&1 || {
  echo "[返答の関門] python3 が無く判定できない。**判定できないときは通さない。**" >&2; exit 2; }

# **本文はファイルに落としてから扱う。**コマンド置換 `$(...)` は末尾の改行を削るので、
# 変数に入れた時点で指紋が「末尾の改行が落ちた版」になってしまう(2026-09-13 の実測で判明)。
# 環境変数に載せると長い本文で上限にも当たる。
mkdir -p /tmp/hookprobe 2>/dev/null
RF=/tmp/hookprobe/last_reply.txt
printf '%s' "$INPUT" | python3 -c 'import json,sys
try: sys.stdout.write(json.load(sys.stdin).get("last_assistant_message") or "")
except Exception: pass' > "$RF" 2>/dev/null

# 返答本文の指紋。**これが「その出力に監査をかける」の実体。**
SHA="$(sha256sum "$RF" | cut -c1-16)"

[ -s "$RF" ] || { echo "[返答の関門] 返答本文が取れず判定できない。**判定できないときは通さない。**" >&2; exit 2; }

# **5 版(L-200)**: 行頭「【最終報告】」の印が無い返答は途中経過・状況報告として通す。
if ! grep -q '^【最終報告】' "$RF" 2>/dev/null; then
  exit 0
fi

LOG="docs/AUDITOR/ACTION_LOG.md"
RESULT="$(REPLY_FILE="$RF" SHA="$SHA" LOG="$LOG" python3 - <<'PY' 2>/dev/null
import os, sys, io

sha   = os.environ.get("SHA", "")
log   = os.environ.get("LOG", "")
try:
    reply = io.open(os.environ.get("REPLY_FILE", ""), encoding="utf-8").read()
except Exception:
    print("NOREPLY"); sys.exit(0)

def out(tok, *rest):
    print("\t".join([tok] + [str(r) for r in rest]))
    sys.exit(0)

try:
    lines = io.open(log, encoding="utf-8").read().split("\n")
except Exception:
    out("NOLOG")

key = "返答sha256: " + sha
start = None
for i, l in enumerate(lines):
    if l.startswith(key):   # **行頭に固定**(14 本目の監査の一括点検。地の文の引用を拾わない)
        start = i
if start is None:
    out("NOSEC")

# 節はこの見出しからで切る(旧版はファイル末尾まで拾い、後の節の判定を借りていた)
end = len(lines)
for j in range(start + 1, len(lines)):
    if lines[j].startswith("## "):
        end = j
        break
sec = lines[start:end]

if not any("owner-model-auditor" in l for l in sec):
    out("NONAME")

# 「### 監査役の返答(逐語)」の塊を取り出す
vb_start = None
for j, l in enumerate(sec):
    if l.startswith("###") and "監査役の返答" in l:
        vb_start = j + 1
        break
if vb_start is None:
    out("NOVERBATIM")
vb_end = len(sec)
for j in range(vb_start, len(sec)):
    if sec[j].startswith("###"):
        vb_end = j
        break
verbatim = sec[vb_start:vb_end]

# **穴 3 の機械**: 逐語の塊の実質行が、返答本文の中に逐語で存在するか数える。
# 実質行 = 記号や囲みを除いた中身が 10 文字以上の行(表の罫線・空行・``` を数えないため)
def substantive(l):
    s = l.strip().lstrip("#>*-| ").strip()
    return len(s) >= 10 and s not in ("```",)

cand = [l for l in verbatim if substantive(l)]
if len(cand) < 8:
    out("FEWVERB", len(cand))

# **4 版の機械(L-197)**: 節を含む「## 」見出しの名前が返答本文に「ACTION_LOG <名前>」の形であるか。
# 見出し「## 057 — …」→ 名前 057、「## 抜き取り 005 — …」→ 名前 抜き取り 005。
import re
sec_name = None
for k in range(start, -1, -1):
    if lines[k].startswith("## "):
        m = re.match(r"^## +(.+?)(?: +[—-].*)?$", lines[k])
        if m:
            sec_name = m.group(1).strip()
        break
if not sec_name:
    out("NOHEAD")
pat = re.compile(r"ACTION_LOG`?\s*" + re.escape(sec_name) + r"(?!\d)")
if not pat.search(reply):
    out("NOREF", sec_name)

# **判定は「行頭が 判定: の行」のうち最後のものだけを見る。**
# 5 本目の監査の指摘: 押し出し側は 2 本目の教訓(引用文中の「判定: 通す」が鍵になった)を受けて
# 「最後の行頭の判定」に直したのに、こちらは「最初の一致」のままで**非対称**だった。
# 「同じ種類の穴を一方だけ塞いで他方は塞がない」ことへの指摘。
verdict = ""
for l in sec:
    if l.startswith("判定:"):
        verdict = l.strip()
if not verdict:
    out("NOVERDICT")

if verdict.startswith("判定: 通す"):
    out("OK")
if verdict.startswith("判定: 止める"):
    for l in reply.split("\n"):
        if l.startswith("上申:"):
            out("OK_ESCALATE")
    out("STOPNOESC")
out("BADVERDICT", verdict)
PY
)"

TOKEN="$(printf '%s' "$RESULT" | head -1 | cut -f1)"
case "$TOKEN" in
  OK|OK_ESCALATE) exit 0 ;;
esac

case "$TOKEN" in
  NOREPLY)    WHY="返答本文のファイルが読めず判定できない。**判定できないときは通さない。**" ;;
  NOLOG)      WHY="ACTION_LOG.md が読めない" ;;
  NOSEC)      WHY="この返答本文(sha256 先頭 16 桁: $SHA)の節が ACTION_LOG に無い。**まだ監査を通していない。**" ;;
  NONAME)     WHY="節に監査役の名前 owner-model-auditor が無い" ;;
  NOVERBATIM) WHY="節に「### 監査役の返答(逐語)」の塊が無い" ;;
  FEWVERB)    WHY="節の「### 監査役の返答(逐語)」の塊の実質行が 8 行に足りない(あるのは $(printf '%s' "$RESULT" | cut -f2) 行)。逐語は台帳に全文残す" ;;
  NOHEAD)     WHY="節を含む「## 」見出しが見つからない" ;;
  NOREF)      WHY="**返答本文に、監査の記録がある節の名前が無い**(必要: 「ACTION_LOG $(printf '%s' "$RESULT" | cut -f2)」)。逐語は本文に貼らない(L-196)が、どの節に記録があるかは本文に書く(L-197 で承認した形)" ;;
  NOVERDICT)  WHY="節に行頭の「判定:」が無い" ;;
  STOPNOESC)  WHY="監査の判定が「止める」である。**リードが単独で退けることはできない**(L-112)。直すか、行頭「上申:」でオーナーへ渡すこと" ;;
  BADVERDICT) WHY="判定が通す/止めるのどちらでもない: $(printf '%s' "$RESULT" | cut -f2)" ;;
  *)          WHY="判定に失敗した。**判定できないときは通さない。**" ;;
esac

cat >&2 <<EOF
[返答の関門] このターンを終わらせない。

理由: ${WHY}

オーナー逐語(2026-09-13、L-156):
「**返答しようとするときにその出力に監査をかければいいのでは？**」
「**監査役の出力をそのままここに出力すればいいだけ。指摘されたことを出さずに
  後でまとめて出すから書き換えるんやろ**」

**鍵は返答本文そのもの。**本文が 1 文字でも変われば指紋も変わる。
**逐語は本文に貼らない(L-196)。台帳の節に逐語を残し、本文にはその節の名前を書く(L-197)。**
(2 版は「判定: 止める」と「上申:」という文字列 2 つで開いた。4 本目の監査が実測した。)

手順:
 1. 返答の原文は /tmp/hookprobe/last_reply.txt にある(いま書き出した)
 2. \`owner-model-auditor\` を呼ぶ。渡すのは (a) この一手 (b) 応えているオーナーの逐語
    (c) **上の原文**
 3. ACTION_LOG に次を含む節を作る(「## <名前> — …」の見出しの下):
      「返答sha256: $SHA」/ 「owner-model-auditor」/
      「### 監査役の返答(逐語)」+ 逐語(実質 8 行以上。後でまとめない)/ 行頭の「判定:」
 4. **返答本文に「ACTION_LOG <名前>」を書く**(逐語は本文に貼らない = L-196。求められたら出す)
 5. 判定が「止める」なら、直すか、行頭「**上申:**」の行を本文に入れてオーナーへ渡す
 6. **本文を 1 文字でも変えたら指紋が変わる。**変えたなら 2 からやり直す
EOF
exit 2
