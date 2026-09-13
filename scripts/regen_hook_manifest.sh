#!/bin/sh
# フックの指紋を再生成する。**オーナーの指示でフックを変えたときだけ実行する。**
# 同じコミットで OWNER_LOG に指示の逐語を記録すること。
#
# 2026-09-13 の監査で判明した欠陥の修正: 旧版は `sed -n '1,/^$/p'` で見出しを取り出していたが
# 台帳に空行が無いためファイル全体が「見出し」になり、**再生成のたびに前の世代が積み上がっていた**。
# 結果 settings.json の期待値が 4 本並び、**監査の有無に関係なく全 push が拒否される**状態になっていた。
# 対策: 見出しは書かず、台帳は毎回まっさらに生成する。
cd "${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}" || exit 1
for f in .claude/hooks/*.sh .claude/settings.json .claude/agents/owner-model-auditor.md; do
  [ -f "$f" ] || continue
  printf '%s  %s\n' "$(sha256sum "$f" | cut -d' ' -f1)" "$f"
done | sort -k2 > docs/AUDITOR/HOOK_MANIFEST.sha256
echo "再生成した($(wc -l < docs/AUDITOR/HOOK_MANIFEST.sha256) 行)。OWNER_LOG に指示の逐語を記録したか確認すること。"
