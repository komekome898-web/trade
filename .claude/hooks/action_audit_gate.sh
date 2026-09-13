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
# 抜け道は残る(このファイル自体をリードが書き換えられる)。ただしこの環境は毎回
# リポジトリを新しく clone するため、**こっそり緩めても次のセッションで消え、
# 恒久的に緩めるには commit が要り、それは差分に出る。**

INPUT="$(cat)"

CMD="$(printf '%s' "$INPUT" | python3 -c 'import json,sys
try:
    d=json.load(sys.stdin)
    print(d.get("tool_input",{}).get("command",""))
except Exception:
    print("")
' 2>/dev/null)"

[ -z "$CMD" ] && exit 0

# コマンドの各区切りの先頭が `git push` のものだけを対象にする(誤発火を避ける)
printf '%s' "$CMD" | tr ';&|' '\n' | sed 's/^[[:space:]]*//' | grep -q '^git push' || exit 0

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
  exit 0
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
