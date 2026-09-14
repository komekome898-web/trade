#!/bin/sh
# ⑤ 危機時の read-do を開く条件を、機械が決める
#
# オーナー承認 2026-09-14、L-169。
#
# **なぜ日常の規則集と分けるか(実測)**:
#   Arriaga et al., NEJM 2013(無作為割付、17 チーム × 106 の模擬危機):
#     **危機時の read-do チェックリストで、救命手順の不遵守 6%(あり)対 23%(なし)、P<0.001。**
#   一方、日常型の do-confirm は実地で再現に失敗している
#     (Urbach et al., NEJM 2014: 101 病院 21.5 万件で死亡 OR 0.91 P=0.13、合併症 OR 0.97 P=0.29。
#      病院側の自己申告コンプライアンスは 98%)。
#   **効くのは短い read-do の方で、長い do-confirm ではない。混ぜてはいけない。**
#
# **開く条件をリードの自覚に任せない。**「今は危機だ」と判断させると、
#   今日 1 日で繰り返した「自分で書いた逸脱を自分で通す」型になる。
#
# **表示は 1 行だけ。全文は出さない。**警報疲労を避ける
#   (Drew 2014: ICU の不整脈警報 115 万件のうち **88.8% が偽陽性**)。
set -u
INPUT="$(cat 2>/dev/null || true)"
ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null)}"
[ -n "$ROOT" ] || ROOT="$(pwd)"
RD="docs/AUDITOR/READDO"

EVENT="$(printf '%s' "$INPUT" | python3 -c '
import json,sys
try: d=json.load(sys.stdin)
except Exception: sys.exit(0)
print(d.get("hook_event_name",""))
' 2>/dev/null)"

case "$EVENT" in
  PostToolUse)
    # C1: 監査役が「止める」を返した
    if printf '%s' "$INPUT" | grep -q '判定: 止める'; then
      echo "[⑤] 監査役が止めた → $RD/audit_stop.md を 1 項目ずつ実行すること。" >&2
    fi
    ;;
  UserPromptSubmit)
    # D1: オーナーが否定的な語を出した
    if printf '%s' "$INPUT" | grep -qE '違う|やめろ|何言って|おかしい|却下|なんで|意味が'; then
      echo "[⑤] オーナーの否定 → $RD/owner_objection.md を 1 項目ずつ実行すること。" >&2
    fi
    ;;
esac
exit 0
