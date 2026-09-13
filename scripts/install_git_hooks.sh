#!/bin/sh
# git 側の関門(githooks/pre-push)を有効にする。
# **新しい clone のたびに 1 回実行する。**`.git/` はリポジトリに入らないため、
# クローン直後は git 側の関門が効いていない。
cd "${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}" || exit 1
chmod +x githooks/* 2>/dev/null
git config core.hooksPath githooks || exit 1
echo "git 側の関門を有効にした: core.hooksPath = $(git config core.hooksPath)"
echo "確認: $(ls -1 githooks | tr '\n' ' ')"
