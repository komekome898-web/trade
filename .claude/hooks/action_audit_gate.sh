#!/bin/sh
# PreToolUse(Bash)— 2026-09-13 オーナー指示により新設。
#
# **これは表示ではない。条件を満たさなければ exit 2 で git push を拒否する。**
# 既存の 6 本のフックはすべて `exit 0`(表示のみ)で、2026-09-13 にリードが
# 「監査役を通したか」の表示を見たうえで push した。表示はリードを止められない。
#
# 規則(CLAUDE.md §8): 納品物は監査役を通さずにオーナーへ出さない。
# 本フックは「push するには、その push に監査の記録が含まれていること」を機械で要求する。
#
# 判定: push しようとしている未反映のコミット群に docs/AUDITOR/ACTION_LOG.md の変更が
#       含まれていなければ拒否する。
# 塞いだ経路(2026-09-13、実際にコマンド文字列で確認した範囲):
#   git push / git -C <path> push / /usr/bin/git push / gh (repo 書き込み系) /
#   bash -c '...' や sh -c '...' の中の上記 / 区切り(; & |)の後ろの上記
# **塞げていない経路(実測ではなく、この環境で利用可能なツール一覧から列挙)**:
#   mcp__github__create_or_update_file / push_files / merge_pull_request 等(Bash を経ない)
#     → これらは settings.json の matcher に追加して同じ関門に掛ける
#   ~~オーナーへの会話の返答そのもの(ツールを経ないので、フックでは原理的に掛けられない)~~
#   **【誤り。2026-09-13 にオーナーが否定し、実測で覆った】** Stop フックの payload に
#   `last_assistant_message` が入っており、返答本文に関門を掛けられる。`reply_audit_gate.sh` が担当。
#   測定の実行・データの破棄・事前登録の作成・委任の発注(push より前に完了する行動)
# **このファイル自体をリードが書き換えられる。**ただしこの環境は毎回リポジトリを
# 新しく clone するため、こっそり緩めても次のセッションで消え、
# 恒久的に緩めるには commit が要り、それは差分に出る。
# **全経路を試した結果ではない。上は「この環境のツール一覧を見て列挙した範囲」である。**

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

# **復旧路は常に開ける。**2026-09-13 の実測: 指紋の照合を全操作に広げた直後、
# フック自身の指紋が変わって**復旧手順(再生成)まで拒否され、関門が自分を直せなくなった。**
# 監査役はこれを事前に予言していた(「オーナーが禁じたまさにその行動へリードを追い込む形になっている」)。
case "$CMD" in *regen_hook_manifest.sh*) exit 0 ;; esac

# **指紋の照合を、コマンドの種類を見る前に行う。**2026-09-13 の監査の指摘:
# 旧版は push 系以外を先に落としてから照合していたため、実質 push のときしか見ていなかった。
# 「食い違えば全操作を拒否」という OWNER_LOG L-156 の記述は、その時点では事実と違っていた。
sh "$(dirname "$0")/_verify_manifest.sh" </dev/null || exit 2

# コマンドの各区切りの先頭が `git push` のものだけを対象にする(誤発火を避ける)
# push に相当する操作を、区切り・パス・ラッパを跨いで拾う。
# (2026-09-13 の監査で `git -C <path> push` が素通りすることが判明したため書き直した)
NORM="$(printf '%s' "$CMD" | tr ';&|' '\n' | sed "s/^[[:space:]]*//; s/^bash -c ['\"]//; s/^sh -c ['\"]//")"
printf '%s\n' "$NORM" | grep -Eq '^(/[^ ]*/)?git( +-C +[^ ]+)?( +-[^ ]+)* +push' && FIRE=1
# gh は**書き込み系だけ**。`gh pr view` / `gh api`(読み取り)まで止めると、調べない方向に効く
# (2026-09-13 の 2 回目の監査の指摘 5。オーナー: 「私が提案しないと調査範囲を広げないのはおかしくないですか？」)
printf '%s\n' "$NORM" | grep -Eq '^(/[^ ]*/)?gh +(pr +(create|merge|close|edit|review|comment|ready)|repo +(create|delete|edit|fork|rename|archive)|release +(create|delete|edit|upload)|workflow +(run|enable|disable)|api +(-X *)?(POST|PUT|PATCH|DELETE))' && FIRE=1
[ "$MCP" = "1" ] || [ "${FIRE:-0}" = "1" ] || exit 0

ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
cd "$ROOT" 2>/dev/null || exit 0

LOG="docs/AUDITOR/ACTION_LOG.md"

# 未反映のコミット範囲を求める。上流が無い(初回 push)場合は HEAD の 1 つ手前から。
if UPSTREAM="$(git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null)" && [ -n "$UPSTREAM" ]; then
  RANGE="$UPSTREAM..HEAD"
else
  RANGE="HEAD~1..HEAD"
fi

CHANGED="$(git diff --name-only "$RANGE" 2>/dev/null)"

# 範囲が取れない = 判定できない。**判定できないときは通さない。**
if [ -z "$CHANGED" ] && ! git rev-parse "$RANGE" >/dev/null 2>&1; then
  cat >&2 <<'EOF'
[行動監査の関門] push を拒否した。

理由: 未反映のコミット範囲を判定できなかった。**判定できないときは通さない。**
(2026-09-13 の教訓: 判定できないものを「たぶん大丈夫」で通すのが、この体制の失敗の型)

対処: 範囲を確認してから、docs/AUDITOR/ACTION_LOG.md に今回の行動の監査記録を追記して commit すること。
EOF
  exit 2
fi

if printf '%s\n' "$CHANGED" | grep -qx "$LOG"; then
  # ログが触られただけでは通さない。今回の範囲の追記に、監査が実際に走った形跡
  # (監査役の名前 + 判定行 + 指摘の本文)が含まれることを要求する。
  ADDED="$(git diff "$RANGE" -- "$LOG" 2>/dev/null | grep '^+' | grep -v '^+++')"
  MISS=""
  printf '%s' "$ADDED" | grep -q 'owner-model-auditor' || MISS="${MISS} 監査役の名前"
  # **判定は「最後に現れた行」だけを見る。**
  # 2026-09-13 の 2 回目の監査で判明した欠陥: 文字列 `判定: 通す` を追記のどこかから拾う実装だと、
  # 「リードが自分で『判定: 通す』と書けば通る」という**指摘の本文の引用が、そのまま鍵になる**。
  # 止まらないと書いた文章そのものが、止まらない鍵になっていた。
  # 判定は「**行頭が `判定:` の行**のうち、最後のもの」だけを見る。
  # 行頭に限るのは、地の文の中の引用(例: 「リードが自分で『判定: 通す』と書けば通る」)を
  # 判定として拾わないため。2026-09-13 の 2 回目の監査で、まさにそれが起きた。
  VERDICT_LINE="$(printf '%s\n' "$ADDED" | grep '^+判定:' | tail -1)"
  if [ -z "$VERDICT_LINE" ]; then
    MISS="${MISS} 行頭の「判定:」の行"
  else
    case "$VERDICT_LINE" in
      "+判定: 通す"*) ;;
      *) MISS="${MISS} 最後の判定が [${VERDICT_LINE#+}] (行頭の判定が「判定: 通す」でなければ push しない)" ;;
    esac
  fi
  # 指摘の本文が 8 行以上(見出しだけの空の追記を弾く)
  [ "$(printf '%s' "$ADDED" | wc -l)" -ge 8 ] || MISS="${MISS} 指摘の本文"
  if [ -z "$MISS" ]; then exit 0; fi
  cat >&2 <<EOF
[行動監査の関門] push を拒否した。

理由: ACTION_LOG.md は変更されているが、監査が実際に走った形跡が足りない。
不足:${MISS}

**これは「記録を省いて通すための空の追記」を弾く判定である**
(オーナー指摘 2026-09-13:「指摘の件数を上げるだけの意味のないものになっています」)。

**判定はリードが書くものではない。**オーナー逐語(2026-09-13):
「**判定をあなたが書かなければいい。監査の判定をそのまま書いてそれに従え**」
→ 監査役が返した 3 行(オーナーの負荷 / 品質 / 判定)を**逐語で転記**すること。
書き換え・要約・自分の判断での上書きをしない。
EOF
  exit 2
fi

cat >&2 <<'EOF'
[行動監査の関門] push を拒否した。

理由: この push に含まれるコミットに docs/AUDITOR/ACTION_LOG.md の追記が無い。

規則(CLAUDE.md §8): 納品物は監査役を通さずにオーナーへ出さない。
2026-09-13、リードは push 直前の「監査役を通したか」という**表示**を見たうえで push した。
だからこのフックは表示ではなく拒否する。

通すには、次を満たしてから commit し直すこと:

  1. `owner-model-auditor` を呼ぶ。渡すのは
       (a) これからやろうとしている一手
       (b) それが応えているオーナーの逐語(引用と出典)
  2. 返ってきた「判定: 通す / 止める」と、指摘と、その処置を
     docs/AUDITOR/ACTION_LOG.md に追記する
  3. **「止める」が残っている間は push しない。**直すか、両論を添えてオーナーへ上申する
     (監査役の「止める」をリードが単独で退けることはできない = L-112)

記録を省いて通すために空の追記をすること自体が、
オーナーが 2026-09-13 に指摘した「**指摘の件数を上げるだけの意味のないもの**」に当たる。
EOF
exit 2
