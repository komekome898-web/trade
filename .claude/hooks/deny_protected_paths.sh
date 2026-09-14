#!/bin/sh
# ③(a) 構造的に不可能にする — PreToolUse(Write / Edit / NotebookEdit)
#
# オーナー承認 2026-09-14、L-169「**A-16 ①③④⑤ のフック配線(4 件) →yes**」。
#
# **なぜ「規則に書く」ではなく「拒否する」か。**
#   Reason の分類(`docs/DISCUSSIONS/2026-09-14_instruction_adherence/03_人的要因と安全科学.md` §5):
#   逸脱を**自分で書いてから進んだ**ものは error ではなく **violation** である。
#   violation は情報不足で起きていないので、**規則の追記・強調・再掲では原理的に直らない。**
#   効くのは (a) 逸脱しなくても仕事が終わる経路、(b) 構造的に不可能にすること、の 2 つだけ。
#   ビンクリスチンの事例では、誤ラベル防止・分離保管・専門病棟限定・**独立二重確認とタイムアウト**・
#   警告ラベルが全滅した後、**ミニバッグ(脊椎針に物理的に刺さらない)だけが効いた**。
#
# **限界を先に書く(§5.0 と同じ形)**:
#   - **解除ファイルはリードが作れる。**WHO のカリウム撤去文書が自ら挙げた「病棟での在庫の
#     再蓄積」、Pin Index の「ピンが取り外された」事例と同じ型である。
#     **構造的な不可能性ではない。**回避は ⑥ の R1・R4 で測る。測らないうちは「塞いだ」と書かない。
#   - このフック自体、`~/.claude.json` の `hasTrustDialogAccepted` が false なら走らない
#     (2026-09-14 の段 0)。**走っているかは、止まるはずの操作をして確かめるしかない。**
set -u
INPUT="$(cat 2>/dev/null || true)"

FP="$(printf '%s' "$INPUT" | python3 -c '
import json,sys
try: d=json.load(sys.stdin)
except Exception: sys.exit(0)
print((d.get("tool_input") or {}).get("file_path","") or "")
' 2>/dev/null)"
[ -n "$FP" ] || exit 0

ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null)}"
[ -n "$ROOT" ] || ROOT="$(pwd)"
# **末尾一致で判定する。**絶対パスで来ても相対パスで来ても、$CLAUDE_PROJECT_DIR が
# 何であっても同じ結果になる。前版は "${FP#"$ROOT"/}" で剥がしていたため、
# ROOT が違うと剥がれず、**保護対象を素通りさせていた**(2026-09-14、verify_gates で検出)。
REL="$FP"

deny() {
  cat >&2 <<EOF
[関門] この場所への書き込みを拒否した: $REL

理由: $1

解除: $2 が存在するときだけ通る。**この解除ファイルはオーナーが作るものである。**
(リードが自分で作れてしまうことは CLAUDE.md §5.0 に限界として書いてある。
 作った回数は ⑥ の R4 で数える。)
EOF
  exit 2
}

case "$REL" in
  */docs/PROJECT_GOAL.md|docs/PROJECT_GOAL.md|*/OWNER_MODEL_SOURCE.md|OWNER_MODEL_SOURCE.md|*OWNER_INTENT*)
    if [ -f "$ROOT/.claude/state/owner_unlock_intent" ]; then
      # **無言で通さない。**通したこと自体を記録に出す(35 本目の監査)。
      echo "[関門] 解除ファイル owner_unlock_intent があるので通した: $REL" >&2
      exit 0
    fi
    deny "**オーナーの逐語とゴールは、リードが書き換えるものではない。**2026-09-14 の実測では、この会話の 1,054 回の道具呼び出しのうち \`PROJECT_GOAL.md\` を開いたのは 0 回で、\`OWNER_INTENT\` は 0 回読んで 1 回書き換えていた。" \
      ".claude/state/owner_unlock_intent" ;;
  */.claude/hooks/*|.claude/hooks/*|*/.claude/settings.json|.claude/settings.json|*/.claude/agents/*|.claude/agents/*)
    if [ -f "$ROOT/.claude/state/owner_unlock_hooks" ]; then
      echo "[関門] 解除ファイル owner_unlock_hooks があるので通した: $REL" >&2
      exit 0
    fi
    deny "**A-16 / A-15 の機械化。**オーナー逐語(L-156): 「**なんでフックを自分で書き換える前提で話してる？私が指示した時以外変えないものでないとフックの意味をなさない**」。2026-09-14 に \`settings.json\` を 3 回、オーナーの指示なく触っている。" \
      ".claude/state/owner_unlock_hooks" ;;
esac

exit 0
