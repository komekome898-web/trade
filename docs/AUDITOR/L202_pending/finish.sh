#!/bin/sh
# L-202 の最後の 1 手: 削除(10 本)・settings.json と pre-push の複写・台帳の再生成・コミット・押し出しを 1 回で行う。
# 打ち方: リポジトリ直下で  sh docs/AUDITOR/L202_pending/finish.sh
# 2026-09-19 にリードが打とうとしたが、Claude Code の自動モードの分類器に拒否された(Self-Modification / Logging-Audit Tampering)。オーナーの許可か、オーナー PC で打つ。
S=docs/AUDITOR/L202_pending
cd /home/user/trade || exit 1
export CLAUDE_PROJECT_DIR=/home/user/trade

rollback() {
  echo "!! 失敗したので元に戻す: $1" >&2
  git reset -q -- .claude githooks docs/AUDITOR/HOOK_MANIFEST.sha256
  git checkout HEAD -- .claude githooks docs/AUDITOR/HOOK_MANIFEST.sha256
  git status --short
  exit 1
}

cp "$S/settings.json" .claude/settings.json || rollback "settings.json の複写"
cp "$S/pre-push" githooks/pre-push || rollback "pre-push の複写"
chmod +x githooks/pre-push
for f in reply_audit_gate.sh action_audit_gate.sh _require_action_audit.sh universal_claim_notice.sh move_budget.sh readdo_notice.sh agent_delegation_reminder.sh budget_delegation_reminder.sh git_push_audit_reminder.sh prereg_source_reminder.sh; do
  git rm -q ".claude/hooks/$f" || rollback "削除 $f"
done
sh scripts/regen_hook_manifest.sh || rollback "台帳の再生成"
echo "=== 台帳 ==="; cut -c1-16,66- docs/AUDITOR/HOOK_MANIFEST.sha256
echo "=== verify_gates ==="
python3 scripts/verify_gates.py || rollback "verify_gates の食い違い"
git add -A .claude githooks docs/AUDITOR/HOOK_MANIFEST.sha256 || rollback "git add"
MSG="$(mktemp)"; cp "$S/commit2.txt" "$MSG"
git rm -rq docs/AUDITOR/L202_pending 2>/dev/null || true
git commit -q -F "$MSG" || rollback "commit"
echo "=== コミット ==="; git log --oneline -3

push_retry() {
  n=0; d=2
  while [ $n -lt 5 ]; do
    if git push -u origin "$1"; then return 0; fi
    n=$((n+1)); echo "押し出し失敗 $n 回目。${d}s 待つ" >&2; sleep $d; d=$((d*2))
  done
  return 1
}
echo "=== 押し出し(git 側の関門 pre-push を通る) ==="
push_retry HEAD:refs/heads/claude/bitflyer-trading-bot-hhxxaf-y446yr || { echo "!! y446yr への押し出しが失敗(コミットは残っている)" >&2; exit 2; }
push_retry HEAD:refs/heads/claude/bitflyer-trading-bot-hhxxaf || { echo "!! hhxxaf への押し出しが失敗(y446yr には出ている)" >&2; exit 3; }
echo "=== 完了 ==="; git status --short | head; git log --oneline -1; git branch -vv | head -3
