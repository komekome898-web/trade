#!/bin/sh
# フックの指紋を再生成する。**オーナーの指示でフックを変えたときだけ実行する。**
# 同じコミットで OWNER_LOG に指示の逐語を記録すること。
#
# 2026-09-13 の監査で判明した欠陥の修正: 旧版は `sed -n '1,/^$/p'` で見出しを取り出していたが
# 台帳に空行が無いためファイル全体が「見出し」になり、**再生成のたびに前の世代が積み上がっていた**。
# 結果 settings.json の期待値が 4 本並び、**監査の有無に関係なく全 push が拒否される**状態になっていた。
# 対策: 見出しは書かず、台帳は毎回まっさらに生成する。
cd "${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}" || exit 1
# **githooks/ も台帳に入れる(2026-09-13、5 本目の監査のあと)。**
# 押し出しの関門の本体は git 側の `githooks/pre-push` に移った。台帳に入れなければ、
# **オーナーが禁じた「無検知で書き換えられるフック」がまた増えることになる。**
# 関門の導入と再生成そのものを行うスクリプトも台帳に入れる(6 本目の監査の指摘)。
# `install_git_hooks.sh` を書き換えれば `core.hooksPath` を別の場所へ向けられるので、
# **関門の本体と同じ重さのファイルである。**
for f in .claude/hooks/*.sh githooks/* .claude/settings.json \
         .claude/agents/owner-model-auditor.md \
         scripts/install_git_hooks.sh scripts/regen_hook_manifest.sh \
         scripts/_research_audit_gate.py; do
  [ -f "$f" ] || continue
  printf '%s  %s\n' "$(sha256sum "$f" | cut -d' ' -f1)" "$f"
done | sort -k2 > docs/AUDITOR/HOOK_MANIFEST.sha256
echo "再生成した($(wc -l < docs/AUDITOR/HOOK_MANIFEST.sha256) 行)。OWNER_LOG に指示の逐語を記録したか確認すること。"
