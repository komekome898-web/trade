#!/bin/sh
# ④ 作業単位を短く切る — PreToolUse(全件)+ UserPromptSubmit(数え直し)
#
# オーナー承認 2026-09-14、L-169。
#
# **根拠(実測)**: McMillan 2026、Claude Code CLI の **1,650 セッション / 16,050 観測**。
#   ファイルサイズ(p=0.16, BF10=0.096)・指示の位置(p=0.83)・分割構成(p=0.19)・
#   矛盾の併存(+0.33pp, p=0.912)は**いずれも検出されず**、
#   **生成関数 1 つごとに遵守オッズが 5.6% 低下(OR=0.944, 95%CI [0.937,0.951], p=1.08e-49)**。
#   Laban et al.: 毎ターン全要件を再掲しても 76.6 で、FULL の 93.0 には戻らない。
#   → **「思い出させる」には上限がある。効くのは単位を短く切ることである。**
#
# **閾値をまだ置かない(A-12)。**
#   McMillan の OR は「**生成した関数 1 個ごと**」で、「道具呼び出し 1 回ごと」ではない。
#   **単位が違うので、文献から直接 T を決められない。**
#   2026-09-14 の実測(このリポジトリ、`scripts/trace_metrics.py`):
#       1 手あたりの道具呼び出し数  中央値 4 / 最大 214(80 手)
#   **2026-09-28 までに P5 を貯め、その中央値で閾値を置く。それまでこのフックは表示だけで、拒否しない。**
#   閾値を入れるときは `docs/AUDITOR/PROCESS_METRICS.md` に根拠を書いてから入れる。
#
# 表示は **1 行だけ**にする。警報疲労(Joint Commission / Drew 2014: 警報の 85〜99% は
# 介入を要しない)を避けるため、規則の再掲はしない。
set -u
INPUT="$(cat 2>/dev/null || true)"
ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null)}"
[ -n "$ROOT" ] || ROOT="$(pwd)"
STATE="$ROOT/.claude/state"
CNT="$STATE/move_counter"
mkdir -p "$STATE" 2>/dev/null

EVENT="$(printf '%s' "$INPUT" | python3 -c '
import json,sys
try: d=json.load(sys.stdin)
except Exception: sys.exit(0)
print(d.get("hook_event_name",""))
' 2>/dev/null)"

if [ "$EVENT" = "UserPromptSubmit" ]; then
  echo 0 > "$CNT" 2>/dev/null
  exit 0
fi

N=$(cat "$CNT" 2>/dev/null || echo 0)
N=$((N + 1))
echo "$N" > "$CNT" 2>/dev/null

# 表示だけ。**拒否しない。**閾値は測ってから置く(A-12)。
# 節目は 2026-09-14 実測の中央値 4 ではなく、その 10 倍と 20 倍に置いた
# (中央値で毎回出すと警報疲労になるため。この 2 つの数字も暫定であり、
#  P5 が 2 週間貯まったら置き換える)。
if [ "$N" = "40" ] || [ "$N" = "80" ]; then
  echo "[④] この手は道具 $N 回目(2026-09-14 の中央値は 4、最大は 214)。委任か区切りを検討。" >&2
fi
exit 0
