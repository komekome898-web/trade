#!/bin/sh
# 全称語の検査 — Stop(返答の直前)。**表示だけで、止めない**(選択ウ、2026-09-30 まで)。
#
# オーナー逐語:
#   L-174(2026-09-16): 「**フックの変更してOK**」/ 強さは 3 案から「**ウ: 2 週間測ってから止めに切り替える**」/
#                     対象は「上申したこの 1 件でよろしいですか」に「**それでいい**」
#   L-182(2026-09-16): 「**研究の段 1 の前に作ってください。**」
#
# 経緯(L-173、2026-09-14): I-008 の台帳を直す一手で、リードは「全文検索して確定」「全部数えた」と
# 書きながら、実際に打っていたのは範囲を切った検索だった(`| grep -v ACTION_LOG` 付き、
# `grep -rn 'P1〜P6' docs/ CLAUDE.md`)。2 度続けて数え落とし、監査役が実物で拾った。
# 対策は `CLAUDE.md` §3 の 1 文だけで、機械が無かった(A-17)。これがその機械である。
#
# 何を見るか(L-174 の設計どおり):
#   引き金 = 数える・直す・検索するに係る全称語
#            「全部数え」「全件」「全文検索」「漏れなく」「1 件残らず」「すべて直した」
#            (「1件残らず」は同じ語の空白違いとして同じ扱い)
#   「限界を全部書く」のような、数えることに係らない全称語は引かない
#            (`CLAUDE.md` §5.0 に実在するので、素朴な語一致だと毎回鳴る。Drew 2014: 警報の 85〜99% は介入を要しない)
#   証拠   = 同じ返答に、範囲を切っていない検索のコマンドがあるか
#            (`CLAUDE.md` §3 の数え直しの型 `git ls-files -z | xargs -0 grep`。実装上の具体化はリード)
#            無ければ「範囲を切った」と書いてあるか
#   引き金があり、証拠がどちらも無いときだけ鳴る。
#
# 選択ウ: 鳴った回数と本物だった回数を記録し、誤警報率が出てから止めに切り替える。
#   記録先 = `.claude/state/universal_claim_hits.jsonl`(リポジトリ外。1 行 1 返答。引き金があった返答は
#   証拠の有無にかかわらず書く。鳴ったのは evidence=false の行)。
#   本物かの判定は週次でリードが `docs/AUDITOR/TREND.md` に書く。
#   **止めに切り替えるのは、その結果を見てオーナーが指示したときだけ(A-16)。**このファイルは自分では止めない。
#
# 表示は 1 行だけ(systemMessage)。終了コードは常に 0。
set -u
INPUT="$(cat 2>/dev/null || true)"
ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null)}"
[ -n "$ROOT" ] || ROOT="$(pwd)"
STATE="$ROOT/.claude/state"
mkdir -p "$STATE" 2>/dev/null
command -v python3 >/dev/null 2>&1 || exit 0

# 入力はファイル経由で渡す(ヒアドキュメントが標準入力を占有するため。初版はこれで一度も動かなかった = 実測)
IN="$(mktemp 2>/dev/null || echo "$STATE/universal_claim_in.$$")"
printf '%s' "$INPUT" > "$IN"
IN_FILE="$IN" STATE_DIR="$STATE" python3 - <<'PY' 2>/dev/null
import json, sys, os, hashlib, datetime, re
try:
    d = json.load(open(os.environ["IN_FILE"], encoding="utf-8"))
except Exception:
    sys.exit(0)
reply = d.get("last_assistant_message") or ""
if not reply:
    sys.exit(0)

TRIGGERS = ["全部数え", "全件", "全文検索", "漏れなく", "1 件残らず", "1件残らず", "すべて直した"]
hit_words = [w for w in TRIGGERS if w in reply]
if not hit_words:
    sys.exit(0)

# 証拠: 範囲を切っていない検索(CLAUDE.md §3 の型)か、「範囲を切った」の明記
EVIDENCE_CMD = re.compile(r"git ls-files -z\s*\|\s*xargs -0 grep")
evidence = bool(EVIDENCE_CMD.search(reply)) or ("範囲を切った" in reply)

rec = {
    "ts": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "sha16": hashlib.sha256(reply.encode("utf-8")).hexdigest()[:16],
    "words": hit_words,
    "evidence": evidence,
    "true_positive": None,   # 週次でリードが埋める(TREND.md に転記)。機械は埋めない
}
try:
    with open(os.path.join(os.environ["STATE_DIR"], "universal_claim_hits.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
except Exception:
    pass

if evidence:
    sys.exit(0)
msg = ("[全称語] この返答に「" + "」「".join(hit_words) +
       "」があるが、範囲を切っていない検索のコマンドも「範囲を切った」の明記も無い"
       "(L-174、表示のみ。2026-09-30 まで記録)。")
print(json.dumps({"systemMessage": msg}, ensure_ascii=False))
sys.exit(0)
PY
rm -f "$IN" 2>/dev/null
exit 0
