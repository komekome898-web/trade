#!/bin/sh
# UserPromptSubmit hook — I-006 / L-130: 状態板を「書く場所」から「毎回読む対象」にする導線。
# オーナーが発言するたびに、状態板の要点(共有経路の死活・オーナーに今求めている行動)を
# リードの目の前に出す。表示のみ。
# 状態板に書いただけでは読まれない(I-006 の根本原因)ので、読む側を機械で保証する。
# 2026-10-01、L-488 7(a): 規則 2 行(日本語のみ / 有料インフラ / リードの規則)の再掲を外した。
# 規則は CLAUDE.md §0.2 にあり、毎回の再掲は要らない。
# 失敗しても常に exit 0。

export LC_ALL=C.utf8 2>/dev/null || true
ROOT="$(cd "$(dirname "$0")/../.." && pwd)" || exit 0
cd "$ROOT" 2>/dev/null || exit 0

# L-984・L-986(2026-10-11): 共有の死活は、作業ブランチの paper_logs ではなく、PC の共有が届く既定ブランチに
# 合流していないコミットがあるかで見る(門 G1、scripts/data_gates.py。git fetch もここで打つ)。旧版は作業ブランチだけを見て
# 「途絶」と出し続け、リードは誤報と決めて 10 回以上読み流した。止めるのは data_gates.sh の門。
HEART="$(timeout 50 python3 "$ROOT/scripts/data_gates.py" digest-line 2>/dev/null || echo "!!! 門 G1: 共有の状態を取れなかった")"

BUDGET="$(grep -E "^\| 週間トークン上限" "$ROOT/docs/OWNER_STATUS.md" 2>/dev/null | awk -F"|" '{print $3}' | cut -c1-200 || true)"
if [ -f "$ROOT/docs/OWNER_STATUS.md" ]; then
    NEXT="$(grep -E '^\| PC 運用' "$ROOT/docs/OWNER_STATUS.md" 2>/dev/null | awk -F'|' '{print $5}' | cut -c1-300 || true)"
fi

# L-144 で 3 行に縮小。進行中の項目の一覧はここに貼らない
# (在庫を毎回目の前に置くと、そこからしか考えられなくなる = L-142 の原因 3)。
# 必要なら docs/OWNER_STATUS.md を自分で読む。
MSG="[状態板の要点 — 返答の前に読む(I-006)]
${HEART}
トークン(最終報告値。自主上限 70% を超えたら重い工程を止める = 規則、提案ではない):${BUDGET}
オーナーに今求めている行動:${NEXT:- (無し)}
詳細は docs/OWNER_STATUS.md(必要なときに自分で読む)"

ESCAPED="$(printf '%s' "$MSG" | sed 's/\\/\\\\/g; s/"/\\"/g' | awk '{printf "%s\\n", $0}' | sed 's/\\n$//')"
printf '{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"%s"}}' "$ESCAPED"
exit 0
