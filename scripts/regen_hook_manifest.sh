#!/bin/sh
# フックの指紋を再生成する。**オーナーの指示でフックを変えたときだけ実行する。**
# 同じコミットで OWNER_LOG に指示の逐語を記録すること。
cd "${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}" || exit 1
HEAD_TXT="$(sed -n '1,/^$/p' docs/AUDITOR/HOOK_MANIFEST.sha256)"
{
  printf '%s\n' "$HEAD_TXT"
  for f in .claude/hooks/*.sh .claude/settings.json; do
    case "$f" in *_probe_*) continue;; esac
    printf '%s  %s\n' "$(sha256sum "$f" | cut -d' ' -f1)" "$f"
  done
} > docs/AUDITOR/HOOK_MANIFEST.sha256
echo "再生成した。OWNER_LOG に指示の逐語を記録したか確認すること。"
