#!/bin/sh
# PreToolUse(Bash / MCP の書き込み)— 2026-09-13 オーナー指示により新設、5 本目の監査で作り直し。
#
# **これは表示ではない。条件を満たさなければ exit 2 で操作を拒否する。**
# 既存の 6 本のフックはすべて `exit 0`(表示のみ)で、2026-09-13 にリードが
# 「監査役を通したか」の表示を見たうえで押し出した。表示はリードを止められない。
#
# 規則(CLAUDE.md §8): 納品物は監査役を通さずにオーナーへ出さない。
#
# **この関門は二重のうちの外側である(2026-09-13、5 本目の監査を受けた作り直し)。**
# 5 本目の監査が静的読解で抜け道を挙げ、**実機で 8 件とも再現した**:
#   env git push / "git" push / git "push" / git${IFS}push / eval '...' /
#   xargs 経由 / command git push / \git push
# いずれも旧版の「行頭が git であること」を要求する正規表現を外れる。
# **個別に潰しても、シェルの言い換えは無限にある。方式そのものが弱い。**
# → 内側の関門を **git 自身**(`githooks/pre-push`)に置いた。どう呼ばれても押し出すのは
#   git なので、呼び出しの書き方では迂回できない。**そちらが本体である。**
#   この関門は、語単位に分解して押し出しらしさを見る外側の層として残す
#   (git に届く前に、理由を添えて止めるため)。
#
# 塞げていない経路(実測ではなく列挙):
#   測定の実行・データの破棄・事前登録の作成・委任の発注(押し出しより前に完了する行動)
#   → 返答の関門(`reply_audit_gate.sh`)がオーナーへの出力の側を受け持つ。
# **このファイル自体をリードが書き換えられる。**指紋の台帳はそれを**防がない**。
# しているのは「改変がコミットの差分に残る」ことと「食い違ったまま操作できない」ことだけ。

# --mcp: Bash を経ない GitHub 書き込みツール。コマンド文字列が無いので無条件に関門へ。
MCP=0
[ "$1" = "--mcp" ] && MCP=1

INPUT="$(cat)"

CMD="$(printf '%s' "$INPUT" | python3 -c 'import json,sys
try:
    d=json.load(sys.stdin)
    print(d.get("tool_input",{}).get("command",""))
except Exception:
    print("")
' 2>/dev/null)"

[ "$MCP" = "1" ] || [ -n "$CMD" ] || exit 0

# **復旧路は開けるが、「鍵」にはしない。**2026-09-13 の実測: 指紋の照合を全操作に広げた直後、
# フック自身の指紋が変わって**復旧手順(再生成)まで拒否され、関門が自分を直せなくなった。**
# 監査役はこれを事前に予言していた(「オーナーが禁じたまさにその行動へリードを追い込む形になっている」)。
#
# **4 本目の監査で実測された欠陥**: 旧版は `*regen_hook_manifest.sh*` という**部分一致**で、
#   `git push origin main # regen_hook_manifest.sh` → exit 0(監査の記録ゼロで押し出しが通った)
# **コメントを 1 つ足すだけで、指紋の照合も押し出しの関門も丸ごと素通りする万能の鍵だった。**
# → **コマンド全体が復旧手順そのものであるときだけ**通す。
CMD_LINES="$(printf '%s\n' "$CMD" | grep -c '')"
case "$CMD" in
  *';'*|*'&'*|*'|'*|*'#'*|*'`'*|*'$('*|*'>'*|*'<'*) ;;
  *)
    if [ "$CMD_LINES" = "1" ]; then CAND="$CMD"; else CAND="(multiline)"; fi
    case "$(printf '%s' "$CAND" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')" in
      "sh scripts/regen_hook_manifest.sh"|"sh ./scripts/regen_hook_manifest.sh"|\
      "bash scripts/regen_hook_manifest.sh"|"bash ./scripts/regen_hook_manifest.sh"|\
      "scripts/regen_hook_manifest.sh"|"./scripts/regen_hook_manifest.sh"|\
      "sh scripts/install_git_hooks.sh"|"sh ./scripts/install_git_hooks.sh"|\
      "scripts/install_git_hooks.sh"|"./scripts/install_git_hooks.sh")
        exit 0 ;;
    esac ;;
esac

# **指紋の照合を、コマンドの種類を見る前に行う。**2026-09-13 の 3 本目の監査の指摘:
# 旧版は押し出し系以外を先に落としてから照合していたため、実質押し出しのときしか見ていなかった。
sh "$(dirname "$0")/_verify_manifest.sh" </dev/null || exit 2

# --- 押し出しらしさの判定を、正規表現から**語単位**に変える ---
# 旧版は「行頭が git」を要求していたので env / eval / 引用符 / ${IFS} で外れた。
# ここでは引用符と \ を外し、${IFS} を空白に戻し、区切りを空白にしてから語に割り、
# **どこかに git という語があり、そのあとに push という語があれば**掛ける。
# 誤って掛かっても失うのは「監査の記録を書く手間」だけ。素通りは取り返しがつかない。
if [ "$MCP" != "1" ]; then
  FIRE="$(printf '%s' "$CMD" | python3 -c '
import sys, re
s = sys.stdin.read()
s = s.replace("${IFS}", " ").replace("$IFS", " ")
s = re.sub(r"[\"'"'"'`\\\\]", " ", s)
s = re.sub(r"[;&|()\n\t]", " ", s)
toks = [t for t in s.split() if t]
base = [t.rsplit("/", 1)[-1] for t in toks]
fire = 0
for i, b in enumerate(base):
    if b == "git" and "push" in base[i + 1:]:
        fire = 1
    if b == "gh":
        rest = set(base[i + 1:])
        if rest & {"create", "merge", "close", "edit", "review", "comment", "ready",
                   "delete", "fork", "rename", "archive", "upload", "run",
                   "enable", "disable", "POST", "PUT", "PATCH", "DELETE"}:
            fire = 1
print(fire)
' 2>/dev/null)"
  [ "${FIRE:-0}" = "1" ] || exit 0
fi

# 判定そのものは共有部品に集約する(5 本目の監査:「同じ種類の穴を一方だけ塞ぐな」)。
# git 側の `githooks/pre-push` も同じ部品を呼ぶので、2 つの関門の判定が食い違わない。
exec sh "$(dirname "$0")/_require_action_audit.sh"
