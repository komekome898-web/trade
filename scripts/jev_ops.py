#!/usr/bin/env python3
"""運用の通知・取引所の告知・自律 AI の判断の記録に、狭い問いを当てる道具。

出所: `docs/JEV.md` §8 の **U15(運用の通知の仕分け)・U17(取引所の告知・外部の文章の分類)・
U18(自律 AI トレーダーの判断の事後検査)**。

**この道具の出力は表示と記録だけである。**印と確率を出すだけで、何も止めず、何も良しとしない
(オーナー逐語 L-218:「**そもそも止めるとjev出させようとするのは間違った運用で、判断はLLMと
私の役割である**」)。とくに:

- **U15(`notify`)と U17(`announce`)は表示と記録のみで、注文の判断には使わない。**
  この道具は `src/bot/` から import されないし、`src/bot/` を import もしない
  (`docs/JEV.md` §4-8「取引の経路には置かない」)。注文・建玉・Kill Switch・リスク上限の
  どれにも触れない。
- **U18(`decision-review`)は事後のみ。**記録(JSON)を読むだけで、注文には触れない。
- ネットワークは **読み取りの GET だけ**(取引所の状態ページと `gethealth`)。
  **注文系の端点(`/v1/me/sendchildorder` など)は呼ばない。**

数える・日付の順序・確率の合成は **code**(`docs/JEV.md` §4-4)。Jev に聞くのは
「この文はどの型か」「この文は product に関わるか」だけである。

使い方:
  python3 scripts/jev_ops.py notify --jsonl tests/fixtures/jev_ops/notifications.jsonl --dry-run
  python3 scripts/jev_ops.py notify --text <通知の文面.txt> [--dry-run] [--summary]
  python3 scripts/jev_ops.py announce --url https://status.bitflyer.com/ [--dry-run] [--summary]
  python3 scripts/jev_ops.py announce --text <告知.txt> [--dry-run] [--summary]
  python3 scripts/jev_ops.py decision-review --record <判断の記録.json> [--dry-run]
"""
from __future__ import annotations

import argparse
import html as _html
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.jev.client import JevClient, JevError  # noqa: E402
from scripts.jev.redact import RedactionError  # noqa: E402
# しきい値・伏せ字の作法・末尾 1 行・印の数え方は `jev_check` から import する(複製しない)。
from scripts.jev_check import (  # noqa: E402
    ATTENTION,
    PRESENCE,
    DEFAULT_MODEL,
    clean_state,
    flag_counts,
    summary_line,
)

# ---------------------------------------------------------------------------
# 定数(しきい値はこの 1 箇所。ATTENTION / PRESENCE は import したまま書き直さない)
# ---------------------------------------------------------------------------
DEFAULT_OUT_DIR = REPO / "data" / "jev" / "ops"
MAX_MESSAGE_CHARS = 1_500      # state に入れる文面の上限
MAX_BODY_CHARS = 1_500         # state に入れる告知の本文の上限
RECENT_CONTEXT = 3             # 同じ出所の直前の通知を state に入れる件数(仕様)
MAX_NOTICES = 20               # 1 回の `announce` で扱う告知の上限
HTTP_TIMEOUT = 20.0            # 秒(GET のみ)

# **読み取りの GET だけ**。注文系の端点は書かない(書けば `_assert_read_only` が落ちる)。
STATUS_URL = "https://status.bitflyer.com/"
HEALTH_URL = "https://api.bitflyer.com/v1/gethealth?product_code=FX_BTC_JPY"
PRODUCT_CODE = "FX_BTC_JPY"
# 状態ページ上で `FX_BTC_JPY` に当たる部品の名前(bitFlyer Crypto CFD への改称後の表記)。
PRODUCT_COMPONENT = "bitFlyer Crypto CFD"
USER_AGENT = "trade-research/1.0 (read-only status check)"
# 注文状態を変える端点(`src/bot/exchange/resilience.py: ORDER_ENDPOINTS` と同じ並び)。
# この道具はこの語を含む URL を叩かない。**import ではなく写し**(`src/bot/` に依存しない)。
ORDER_ENDPOINT_WORDS = (
    "/v1/me/sendchildorder", "/v1/me/cancelchildorder", "/v1/me/cancelallchildorders",
    "/v1/me/sendparentorder", "/v1/me/cancelparentorder", "/v1/me/",
)

# U15: 通知の出所(仕様の 4 つ + どれでもない)
SOURCES = ("bot", "watchdog", "intake", "quality", "unknown")
# `src/bot/main.py` の `notifier.send(` / `self._notify(` が出す題(読んで写した。**読むだけ**)
BOT_TITLES = (
    "BOT START", "BOT STOPPED", "STATUS", "KILL SWITCH",
    "OVERLAY SUPPRESSING ENTRIES", "LIVE BOOT: POSITION ADOPTED",
    "LIVE BOOT: UNSENT ORDER RECORDS RESOLVED", "LIVE BOOT RECONCILIATION FAILED",
)
_WATCHDOG_RE = re.compile(r"watchdog|ウォッチドッグ|restart_all|プロセス監視", re.I)
_INTAKE_RE = re.compile(r"intake|受領|台帳|INTAKE\.jsonl", re.I)
_QUALITY_RE = re.compile(r"quality|欠測|gap|QUALITY\.json|データ品質", re.I)

# U15: `attention` の段(低い順)。**「notify 以上」は code がこの並びで決める。**
ATTENTION_LEVELS = ("ignore", "log", "notify", "urgent")
ATTENTION_AT_OR_ABOVE_NOTIFY = ("notify", "urgent")
# U15: 既知の型。鍵は英語(問いは英語 = `docs/JEV.md` §4-3)、表示はオーナーの語(仕様の 7 つ)。
KNOWN_KINDS = {
    "start_or_stop": "起動停止",
    "periodic_status": "定時状態",
    "ambiguous_order_failure": "注文の曖昧な失敗",
    "connectivity_or_rate_limit": "接続・レート制限",
    "data_gap": "データの欠測",
    "budget": "予算",
    "other": "その他",
}

# U17: 取引所の状態の段
SERVICE_STATES = ("normal", "degraded", "maintenance_scheduled", "suspended", "unclear")
MARKET_RELEVANCE = ("none", "liquidity", "settlement_or_funding",
                    "listing_or_delisting", "regulation", "unclear")

# U18: 受け口の JSON の必須の鍵(この道具が形を決める)
DECISION_ACTIONS = ("buy", "sell", "hold", "close")
DECISION_REQUIRED = ("cycle_id", "proposed_action", "rationale", "evidence")
DECISION_OPTIONAL = ("policy_excerpt", "policy_ref", "constraints", "constraints_ref")


def _clip(text: str, limit: int) -> tuple[str, bool]:
    text = (text or "").strip()
    return (text, False) if len(text) <= limit else (text[:limit], True)


# ---------------------------------------------------------------------------
# U15: 運用の通知の仕分け(表示と記録のみ。注文の判断には使わない)
# ---------------------------------------------------------------------------
def parse_notification_text(text: str) -> dict:
    """1 通の通知の文面を (題, 本文) に割る。

    `src/bot/monitoring/notifier.py: DiscordNotifier.send` が組む形をそのまま戻す:
    先頭行が `🚨 **題**`(至急のときだけ `🚨 `)、2 行目以降が本文。
    先頭行がその形でなければ、先頭行を題、残りを本文として扱う。
    """
    lines = (text or "").replace("\r\n", "\n").split("\n")
    head = lines[0].strip() if lines else ""
    head = head.removeprefix("🚨").strip()
    m = re.match(r"^\*\*(?P<title>.+?)\*\*$", head)
    title = m.group("title").strip() if m else head
    message = "\n".join(lines[1:]).strip()
    return {"title": title, "message": message}


def infer_source(title: str, message: str) -> str:
    """出所を code が決める(決定論的)。どれにも当たらなければ `unknown`。

    順序は題 → 出所を名乗る語 → 商品名。**当たらなかったことを `unknown` として残す**
    (「bot だろう」と埋めない)。
    """
    blob = f"{title}\n{message}"
    if title.strip() in BOT_TITLES:
        return "bot"
    if _WATCHDOG_RE.search(blob):
        return "watchdog"
    if _INTAKE_RE.search(blob):
        return "intake"
    if _QUALITY_RE.search(blob):
        return "quality"
    if PRODUCT_CODE in blob:
        return "bot"
    return "unknown"


def load_notifications(*, text_path: Path | None = None,
                       jsonl_path: Path | None = None) -> list[dict]:
    """通知の列を読む。`--text` は 1 通、`--jsonl` は 1 行 1 通。

    `--jsonl` の行に `source` があり `SOURCES` のどれかなら**それを使う**(収集側が知っている)。
    無ければ `infer_source`。`urgent`(bot 自身の旗)は記録に残すが **state には入れない**
    ── 入れると「至急か」の答えを先に渡すことになるので、印と突き合わせられなくなる。
    """
    out: list[dict] = []
    if text_path is not None:
        raw = text_path.read_text(encoding="utf-8", errors="replace")
        parsed = parse_notification_text(raw)
        parsed["anchor"] = 1
        parsed["given_source"] = None
        parsed["urgent"] = None
        out.append(parsed)
    if jsonl_path is not None:
        for i, line in enumerate(jsonl_path.read_text(encoding="utf-8",
                                                      errors="replace").splitlines(), 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            rec = json.loads(line)
            given = rec.get("source")
            out.append({
                "anchor": i,
                "title": str(rec.get("title") or "").strip(),
                "message": str(rec.get("message") or "").strip(),
                "given_source": given if given in SOURCES else None,
                "urgent": rec.get("urgent"),
            })
    for item in out:
        item["source"] = item["given_source"] or infer_source(item["title"], item["message"])
        item["message"], item["truncated"] = _clip(item["message"], MAX_MESSAGE_CHARS)
    return out


def recent_context(items: list[dict], index: int) -> list[dict]:
    """同じ出所の**直前** `RECENT_CONTEXT` 件(古い順)。無ければ空。"""
    src = items[index]["source"]
    prev = [it for it in items[:index] if it["source"] == src]
    return [{"title": it["title"], "message": it["message"]}
            for it in prev[-RECENT_CONTEXT:]]


def state_for_notification(item: dict, context: list[dict]) -> dict:
    state = {
        "title": item["title"],
        "message": item["message"],
        "source": item["source"],
    }
    if context:
        state["recent_context"] = context
    return state


def _with_options(questions: dict, expected: dict) -> dict:
    """選択の問いの選択肢が、先頭に置いた定数と同じであることを確かめて返す。

    定数と criteria がずれると、`combine_*` の確率の足し方(「notify 以上」「normal 以外」)が
    黙って変わる。**ずれたらその場で落とす。**
    """
    for qid, options in expected.items():
        got = set(questions[qid]["criteria"])
        if got != set(options):
            raise ValueError(f"{qid} の選択肢が定数と違う: {sorted(got ^ set(options))}")
    return questions


def questions_notify() -> dict:
    """1 通 1 要求。3 問を並べる(投機的な fan-out、`docs/JEV.md` §4-3)。

    問いは 1 判断 1 問・肯定形・criteria は具体例つき・英語(state の断片は日本語のまま)。
    """
    return _with_options({
        "attention": {
            "type": "choice",
            "instructions": (
                "How much of an operator's attention does this notification need, judged by "
                "`title` and `message` alone?"
            ),
            "criteria": {
                "ignore": (
                    "Nothing is reported beyond the fact that the message was sent. Example: "
                    "a heartbeat or a test post with no state in it."
                ),
                "log": (
                    "Routine operation, worth keeping but not worth reading now. Example: the "
                    "hourly STATUS report of a running bot, or \"BOT START mode=PAPER\"."
                ),
                "notify": (
                    "Something changed that an operator should look at within the day, but "
                    "nothing is stuck and nothing is unsafe. Example: a shared feed stopped "
                    "arriving, a rate limit was hit repeatedly, a data file stopped growing."
                ),
                "urgent": (
                    "Something is stopped or in an unknown state and a person has to act now. "
                    "Example: \"KILL SWITCH\" with trading halted, an order whose outcome the "
                    "system could not determine, a process that exited unexpectedly."
                ),
            },
        },
        "known_kind": {
            "type": "choice",
            "instructions": "Which kind of operational event does `message` report?",
            "criteria": {
                "start_or_stop": (
                    "A process started or stopped. Example: \"BOT START mode=PAPER "
                    "product=FX_BTC_JPY\", \"BOT STOPPED\"."
                ),
                "periodic_status": (
                    "A report of the current state sent on a timer, with no new event in it. "
                    "Example: an hourly report of equity, position and trade count."
                ),
                "ambiguous_order_failure": (
                    "An order request whose outcome is unknown: the request may or may not have "
                    "reached the exchange, and the record is held rather than retried. Example: "
                    "a read timeout on an order endpoint, STATE_UNKNOWN, a record waiting for "
                    "reconciliation."
                ),
                "connectivity_or_rate_limit": (
                    "The connection to the exchange or a data source failed, was throttled, or "
                    "slowed down. Example: HTTP 429, repeated 5xx, a websocket that reconnects, "
                    "latency rising."
                ),
                "data_gap": (
                    "Data that should be arriving is missing or stale. Example: a recorder wrote "
                    "no rows for 30 minutes, a candle series has a hole, a snapshot is older "
                    "than expected."
                ),
                "budget": (
                    "A spending or quota limit is being approached or was passed. Example: a "
                    "weekly token budget at 70%, an API quota nearly exhausted."
                ),
                "other": (
                    "It reports something none of the above covers. Example: an unexpected "
                    "exception with a stack trace, a configuration file that failed to load."
                ),
            },
        },
        "is_new_pattern": {
            "type": "noul",
            "instructions": (
                "The message describes a situation that none of the listed known kinds covers."
            ),
            "criteria": {
                "true": (
                    "The situation does not fit start/stop, a periodic status report, an "
                    "ambiguous order failure, a connectivity or rate-limit problem, a data gap "
                    "or a budget limit. Example: an unhandled exception type nobody has seen "
                    "before, or a message reporting a state the operator has no procedure for."
                ),
                "false": (
                    "The situation is one of those kinds, even if the wording is new. Example: "
                    "a new phrasing of \"the feed is stale\" is still a data gap."
                ),
            },
        },
    }, {"attention": ATTENTION_LEVELS, "known_kind": tuple(KNOWN_KINDS)})


def _probs(answers: dict, qid: str) -> dict:
    return (answers.get(qid) or {}).get("probabilities") or {}


def _argmax(probs: dict) -> str | None:
    return max(probs, key=probs.get) if probs else None


def _conf(answers: dict, qid: str) -> float | None:
    c = (answers.get(qid) or {}).get("confidence")
    return None if c is None else float(c)


def _noul(answers: dict, qid: str) -> float | None:
    v = (answers.get(qid) or {}).get("noul")
    return None if v is None else float(v)


def combine_notify(answers: dict) -> dict:
    """印 = `attention` が notify 以上(確率 >= PRESENCE)**または** `is_new_pattern` >= PRESENCE。

    「notify 以上」の確率は、同じ 1 つの分布の中の `notify` と `urgent` の確率の**和**として
    code が出す(選択の確率は 1 つの分布なので足せる。**別の問い**の確率とは足さない ──
    `docs/JEV.md` §2「はい/いいえ と 選択 の確率は互いに換算できない」)。
    """
    probs = _probs(answers, "attention")
    p_at_or_above = (sum(float(probs.get(k, 0.0)) for k in ATTENTION_AT_OR_ABOVE_NOTIFY)
                     if probs else None)
    new_pattern = _noul(answers, "is_new_pattern")
    kind = _argmax(_probs(answers, "known_kind"))
    reasons = []
    if p_at_or_above is not None and p_at_or_above >= PRESENCE:
        reasons.append("attention_at_or_above_notify")
    if new_pattern is not None and new_pattern >= PRESENCE:
        reasons.append("is_new_pattern")
    return {
        "attention": _argmax(probs),
        "attention_probabilities": probs,
        "attention_confidence": _conf(answers, "attention"),
        "attention_at_or_above_notify": (
            None if p_at_or_above is None else round(p_at_or_above, 4)),
        "known_kind": kind,
        "known_kind_label": KNOWN_KINDS.get(kind or "", None),
        "known_kind_probabilities": _probs(answers, "known_kind"),
        "known_kind_confidence": _conf(answers, "known_kind"),
        "is_new_pattern_probability": None if new_pattern is None else round(new_pattern, 4),
        "flag": bool(reasons),
        "flag_reasons": reasons,
        "reason": None if reasons else "below_presence",
    }


# ---------------------------------------------------------------------------
# U17: 取引所の告知・外部の文章の分類(表示と記録のみ)
# ---------------------------------------------------------------------------
_TAG_RE = re.compile(r"(?s)<[^>]+>")
_SCRIPT_RE = re.compile(r"(?is)<(script|style)[^>]*>.*?</\1>")
_BR_RE = re.compile(r"(?i)<br\s*/?>")


def _text_of(fragment: str) -> str:
    """HTML の断片から表示される文字だけを取り出す(タグを落として空白を畳む)。"""
    fragment = _SCRIPT_RE.sub(" ", fragment or "")
    fragment = _BR_RE.sub("\n", fragment)
    fragment = _TAG_RE.sub("", fragment)
    fragment = _html.unescape(fragment)
    lines = [ln.strip() for ln in fragment.split("\n")]
    return "\n".join(ln for ln in lines if ln).strip()


_PAGE_STATUS_RE = re.compile(
    r'(?s)<div class="page-status\s+(?P<cls>[^"]*)">\s*<h2 class="status[^"]*">(?P<text>.*?)</h2>')
_COMPONENT_RE = re.compile(
    r'(?s)class="component-inner-container\s+(?P<cls>[^"]*)"\s*'
    r'data-component-status="(?P<status>[^"]*)"(?P<rest>.*?)'
    r'(?=class="component-inner-container|\Z)')
_NAME_RE = re.compile(r'(?s)<span class="name"[^>]*>(?P<name>.*?)</span>')
_COMPONENT_STATUS_RE = re.compile(
    r'(?s)<span\s*class="component-status[^"]*"[^>]*>(?P<text>.*?)</span>')
_DAY_DATE_RE = re.compile(r'(?s)<h3 class="date[^"]*">(?P<date>.*?)</h3>')
_INCIDENT_TITLE_RE = re.compile(
    r'(?s)<div class="incident-title\s+(?P<impact>[^"]*)">(?P<title>.*?)</div>')
_UPDATE_STATE_RE = re.compile(r'(?s)<strong>(?P<state>.*?)</strong>')
_UPDATE_BODY_RE = re.compile(r'(?s)<span class="whitespace-pre-wrap">(?P<body>.*?)</span>')
_UPDATE_TIME_RE = re.compile(r'(?s)<small>(?P<time>.*?)</small>')


def _impact_of(class_list: str) -> str | None:
    """`incident-title impact-maintenance font-large` の class から `impact-…` だけを取る。"""
    for token in (class_list or "").split():
        if token.startswith("impact-"):
            return token
    return None


def parse_status_page(html: str) -> dict:
    """状態ページの HTML から、見出し・項目・日時を抜く。**規則はここに全部書く。**

    抜き方(Statuspage の作りに合わせた、決定論的な規則):

    1. **全体の見出し** = `<div class="page-status …">` の直後の `<h2 class="status …">` の文字。
       class の `status-none` / `status-minor` などもそのまま記録する。
    2. **部品の一覧** = `class="component-inner-container …" data-component-status="…"` ごとに、
       同じ塊の中の `<span class="name">`(名前)と `<span class="component-status">`(表示の状態)。
    3. **告知の一覧** = `Past Incidents` 以降を `<div class="status-day` で日ごとに割り、
       各日の見出し `<h3 class="date …">` を日付、その日の `<div class="incident-container">`
       ごとに 1 件とする。1 件の中身は `incident-title impact-<影響>` の題と、
       `<div class="update …">` ごとの (状態の語, 本文, 時刻)。
       **時刻は文字列としてそのまま持つ**(日付の順序は Jev に読ませない = `docs/JEV.md` §4-4)。
    4. 「No incidents reported」しかない日は告知 0 件として数えない。

    戻り値の `notices` が「抜けた項目」。**1 件も無ければ 0 件と書く**(「取れない」とは書かない)。
    """
    m = _PAGE_STATUS_RE.search(html or "")
    overall = _text_of(m.group("text")) if m else None
    overall_class = m.group("cls").strip() if m else None

    components: list[dict] = []
    for cm in _COMPONENT_RE.finditer(html or ""):
        block = cm.group("rest")
        nm = _NAME_RE.search(block)
        sm = _COMPONENT_STATUS_RE.search(block)
        components.append({
            "name": _text_of(nm.group("name")) if nm else None,
            "status": cm.group("status"),
            "status_text": _text_of(sm.group("text")) if sm else None,
            "css_class": cm.group("cls").strip(),
        })

    notices: list[dict] = []
    tail = html.split('id="past-incidents"', 1)[-1] if html else ""
    for day in tail.split('<div class="status-day')[1:]:
        dm = _DAY_DATE_RE.search(day)
        date = _text_of(dm.group("date")) if dm else None
        for chunk in day.split('<div class="incident-container">')[1:]:
            tm = _INCIDENT_TITLE_RE.search(chunk)
            if not tm:
                continue
            updates = []
            for up in chunk.split('<div class="update ')[1:]:
                sm = _UPDATE_STATE_RE.search(up)
                bm = _UPDATE_BODY_RE.search(up)
                tmm = _UPDATE_TIME_RE.search(up)
                updates.append({
                    "state": _text_of(sm.group("state")) if sm else None,
                    "body": _text_of(bm.group("body")) if bm else None,
                    "time": _text_of(tmm.group("time")).replace("\n", " ") if tmm else None,
                })
            notices.append({
                "date": date,
                "impact": _impact_of(tm.group("impact")),
                "title": _text_of(tm.group("title")),
                "updates": updates,
            })
    return {"overall": overall, "overall_class": overall_class,
            "components": components, "notices": notices[:MAX_NOTICES],
            "n_notices_found": len(notices)}


def _assert_read_only(url: str) -> None:
    """注文系の端点を含む URL は叩かない(`docs/JEV.md` §4-8 の機械的な担保)。"""
    low = (url or "").lower()
    for word in ORDER_ENDPOINT_WORDS:
        if word in low:
            raise ValueError(f"注文系・私用の端点は叩かない: {url}")
    if not low.startswith("https://"):
        raise ValueError(f"https の GET だけを許す: {url}")


def http_get(url: str, timeout: float = HTTP_TIMEOUT) -> tuple[str | None, int | None, str | None]:
    """GET を 1 回。(本文, HTTP コード, 失敗の理由)。

    **取れなくても続行する**(`CLAUDE.md` §5.2 / §0.2 O-2: 「取れない」と書かずに、
    HTTP コードか例外の型を記録して先へ進む)。
    """
    _assert_read_only(url)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace"), resp.status, None
    except urllib.error.HTTPError as e:
        return None, e.code, f"HTTPError {e.code}"
    except Exception as e:  # noqa: BLE001 - 取れなかった事実だけを記録して続行する
        return None, None, type(e).__name__


def fetch_health(url: str = HEALTH_URL) -> dict:
    """`gethealth` の `status` を取る。取れなければ HTTP コード / 例外の型を残す。"""
    body, code, err = http_get(url)
    out = {"url": url, "http_code": code, "error": err, "status": None}
    if body is None:
        return out
    try:
        out["status"] = (json.loads(body) or {}).get("status")
    except json.JSONDecodeError as e:
        out["error"] = f"JSONDecodeError:{e.msg}"
    return out


def notices_from_text(text: str) -> list[dict]:
    """`--text` で渡した 1 件の告知(先頭行 = 題、残り = 本文)。"""
    lines = (text or "").replace("\r\n", "\n").split("\n")
    title = lines[0].strip() if lines else ""
    body = "\n".join(lines[1:]).strip()
    return [{"date": None, "impact": None, "title": title,
             "updates": [{"state": None, "body": body, "time": None}]}]


def state_for_notice(notice: dict, page: dict, health: dict | None) -> dict:
    """告知 1 件の state。**判断に要る事実だけ**を入れる(`docs/JEV.md` §2)。"""
    body = "\n".join(
        " - ".join(part for part in (u.get("state"), u.get("body")) if part)
        for u in notice.get("updates") or [] if u.get("body") or u.get("state"))
    body, truncated = _clip(body, MAX_BODY_CHARS)
    state = {
        "notice_title": notice.get("title"),
        "notice_body": body,
        "notice_times": [u.get("time") for u in notice.get("updates") or [] if u.get("time")],
        "notice_date": notice.get("date"),
        "product_code": PRODUCT_CODE,
        "product_component_name": PRODUCT_COMPONENT,
        "exchange_components": [c.get("name") for c in page.get("components") or []
                                if c.get("name")],
    }
    if page.get("overall"):
        state["page_overall_status"] = page["overall"]
    if health and health.get("status"):
        state["product_health_endpoint_status"] = health["status"]
    state["_truncated"] = truncated
    return state


def questions_announce() -> dict:
    """1 告知 1 要求(仕様)。4 問を並べる。"""
    return _with_options({
        "service_state": {
            "type": "choice",
            "instructions": (
                "What does this notice say about the state of the exchange's service at the time "
                "the notice was written?"
            ),
            "criteria": {
                "normal": (
                    "The notice reports that service is running, or that a past problem is "
                    "finished. Example: \"All systems operational\", \"the incident has been "
                    "resolved\", \"the scheduled maintenance has been completed\"."
                ),
                "degraded": (
                    "Service is running but worse than usual: slower, partly failing, or "
                    "unstable. Example: \"order processing is delayed\", \"connections may be "
                    "unstable for a few minutes\", \"partial outage on the spot exchange\"."
                ),
                "maintenance_scheduled": (
                    "Planned work is announced for a future time, and service is normal until "
                    "then. Example: \"we will conduct maintenance on Thursday from 4:00 to "
                    "4:30\"."
                ),
                "suspended": (
                    "Trading or order acceptance is stopped. Example: \"order acceptance has "
                    "been halted\", \"major outage\", \"the service is unavailable\"."
                ),
                "unclear": (
                    "The notice does not say anything about the state of the service. Example: "
                    "a note about a web page redesign or a campaign."
                ),
            },
        },
        "affects_product": {
            "type": "noul",
            "instructions": (
                "The notice concerns `product_code`, the component named in "
                "`product_component_name`, or the whole exchange, as opposed to an unrelated "
                "product."
            ),
            "criteria": {
                "true": (
                    "The notice names that product or component, or it applies to every service "
                    "of the exchange. Example: \"all services may experience connection "
                    "instability\", \"bitFlyer Crypto CFD: degraded performance\"."
                ),
                "false": (
                    "The notice is limited to something else on the exchange. Example: a notice "
                    "that names only the spot exchange for another coin pair, or only the "
                    "consumer buy/sell page, and says nothing about the whole exchange."
                ),
            },
        },
        "time_window_stated": {
            "type": "noul",
            "instructions": "A start time and an end time are both stated in `notice_body`.",
            "criteria": {
                "true": (
                    "Both ends of the window appear. Example: \"from approx. 4:00 to 4:30 am "
                    "(JST)\", \"9月17日 4時00分頃から4時30分頃まで\"."
                ),
                "false": (
                    "Only one time, or no time at all, is stated. Example: \"maintenance will "
                    "start at 4:00\" with no end, or \"we are investigating\"."
                ),
            },
        },
        "market_relevance": {
            "type": "choice",
            "instructions": (
                "If this notice matters to how the market trades, in which way does it matter?"
            ),
            "criteria": {
                "none": (
                    "Nothing in it would change how the market trades. Example: a website "
                    "redesign, a change to a help page."
                ),
                "liquidity": (
                    "It would change how easily orders trade: the venue being slow, halted, or "
                    "unable to accept orders. Example: \"order acceptance is delayed\", "
                    "\"matching is suspended\"."
                ),
                "settlement_or_funding": (
                    "It concerns settlement, margin, funding or swap payments, deposits or "
                    "withdrawals. Example: \"the funding rate collection time changes\", "
                    "\"withdrawals are suspended\"."
                ),
                "listing_or_delisting": (
                    "A product or pair is added, removed or renamed. Example: \"trading in this "
                    "pair ends on the 30th\"."
                ),
                "regulation": (
                    "It concerns a rule, a licence, a tax treatment or an authority's order. "
                    "Example: \"following administrative guidance, new account opening is "
                    "suspended\"."
                ),
                "unclear": (
                    "The notice does not give enough to place it in any of the above. Example: "
                    "\"we are investigating\" with nothing said about what is affected."
                ),
            },
        },
    }, {"service_state": SERVICE_STATES, "market_relevance": MARKET_RELEVANCE})


def combine_announce(answers: dict) -> dict:
    """印 = `service_state` が normal 以外(確率 >= PRESENCE)**かつ** `affects_product` >= PRESENCE。

    「normal 以外」の確率は、同じ分布の `normal` 以外の確率の和(= 1 − P(normal))として
    code が出す。**`unclear` もここに入る**(normal だと言い切っていないので)。
    """
    probs = _probs(answers, "service_state")
    p_normal = float(probs.get("normal", 0.0)) if probs else None
    p_non_normal = None if p_normal is None else 1.0 - p_normal
    affects = _noul(answers, "affects_product")
    window = _noul(answers, "time_window_stated")
    flag = bool(p_non_normal is not None and p_non_normal >= PRESENCE
                and affects is not None and affects >= PRESENCE)
    reason = None
    if not flag:
        if p_non_normal is None or affects is None:
            reason = "no_answer"
        elif p_non_normal < PRESENCE:
            reason = "service_state_reads_normal"
        else:
            reason = "not_this_product"
    return {
        "service_state": _argmax(probs),
        "service_state_probabilities": probs,
        "service_state_confidence": _conf(answers, "service_state"),
        "non_normal_probability": None if p_non_normal is None else round(p_non_normal, 4),
        "affects_product_probability": None if affects is None else round(affects, 4),
        "time_window_stated_probability": None if window is None else round(window, 4),
        "market_relevance": _argmax(_probs(answers, "market_relevance")),
        "market_relevance_probabilities": _probs(answers, "market_relevance"),
        "market_relevance_confidence": _conf(answers, "market_relevance"),
        "flag": flag,
        "reason": reason,
    }


# ---------------------------------------------------------------------------
# U18: 自律 AI トレーダーの判断の事後検査(**設計と受け口だけ**)
# ---------------------------------------------------------------------------
def _resolve_config_line(ref: dict | None) -> dict | None:
    """`{"file": "config/risk_limits.yaml", "key": "MAX_ORDER_SIZE_JPY"}` を該当行に直す。

    **code が `config/` の該当行を引く**(記録を書いた側の言い換えを信じない)。
    `config/` の下のファイルだけを読む。見つからなければ `line: None` と理由を残す。
    """
    if not ref:
        return None
    rel = str(ref.get("file") or "")
    key = str(ref.get("key") or "")
    out = {"file": rel, "key": key, "line": None, "lineno": None, "error": None}
    path = (REPO / rel).resolve()
    config_dir = (REPO / "config").resolve()
    if not str(path).startswith(str(config_dir) + "/"):
        out["error"] = "config/ の外は読まない"
        return out
    if not path.is_file():
        out["error"] = "ファイルが無い"
        return out
    pattern = re.compile(rf"^\s*{re.escape(key)}\s*:")
    for i, line in enumerate(path.read_text(encoding="utf-8",
                                            errors="replace").splitlines(), 1):
        if pattern.match(line):
            out["line"] = line.strip()
            out["lineno"] = i
            return out
    out["error"] = "その鍵の行が無い"
    return out


def load_decisions(path: Path) -> list[dict]:
    """判断の記録を読む(1 件の object か、その配列)。**この道具が受け口の形を決める**:

    ```json
    {"cycle_id": "2026-09-19T12:00:00Z#1",
     "proposed_action": "buy|sell|hold|close",
     "rationale": "なぜその行動を選んだかの文",
     "policy_excerpt": "方針の文",            // または policy_ref
     "policy_ref": {"file": "config/risk_limits.yaml", "key": "MAX_ORDER_SIZE_JPY"},
     "evidence": [{"name": "…", "value": …}], // 数値の一覧(**比較は code、Jev は読むだけ**)
     "constraints": "リスク上限の文",          // または constraints_ref(同じ形)
     "constraints_ref": {"file": "config/risk_limits.yaml", "key": "MAX_DAILY_LOSS_JPY"}}
    ```

    `*_ref` があれば code が `config/` の該当行を引いて `*_excerpt` に入れる
    (記録側の文字列より `config/` の実物を優先する)。
    """
    data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    records = data if isinstance(data, list) else [data]
    out: list[dict] = []
    for i, rec in enumerate(records, 1):
        missing = [k for k in DECISION_REQUIRED if not rec.get(k)]
        policy = _resolve_config_line(rec.get("policy_ref"))
        constraints = _resolve_config_line(rec.get("constraints_ref"))
        out.append({
            "anchor": i,
            "cycle_id": rec.get("cycle_id"),
            "proposed_action": rec.get("proposed_action"),
            "rationale": _clip(str(rec.get("rationale") or ""), MAX_MESSAGE_CHARS)[0],
            "evidence": rec.get("evidence"),
            "policy_excerpt": (policy or {}).get("line") or rec.get("policy_excerpt"),
            "policy_source": policy,
            "constraints": (constraints or {}).get("line") or rec.get("constraints"),
            "constraints_source": constraints,
            "missing_fields": missing,
            "optional_fields_given": [k for k in DECISION_OPTIONAL if rec.get(k)],
            "unknown_action": rec.get("proposed_action") not in DECISION_ACTIONS,
        })
    return out


def state_for_decision(rec: dict) -> dict:
    state = {
        "cycle_id": rec.get("cycle_id"),
        "proposed_action": rec.get("proposed_action"),
        "rationale": rec.get("rationale"),
        "policy_excerpt": rec.get("policy_excerpt"),
        "evidence": rec.get("evidence"),
        "constraints": rec.get("constraints"),
    }
    return {k: v for k, v in state.items() if v not in (None, "", [])}


def questions_decision() -> dict:
    """1 記録 1 要求。3 問(仕様)。**事後のみ** ── 注文には触れない。"""
    return {
        "consistent_with_policy": {
            "type": "noul",
            "instructions": (
                "`proposed_action` is allowed by the rule written in `policy_excerpt` and "
                "`constraints`."
            ),
            "criteria": {
                "true": (
                    "Nothing in the quoted rule forbids the action, or the rule explicitly "
                    "allows it. Example: the rule caps one position at 130,000 JPY and the "
                    "action opens a 11,000 JPY position."
                ),
                "false": (
                    "The quoted rule forbids the action or sets a limit the action passes. "
                    "Example: the rule allows one open order at a time and the action adds a "
                    "second, or the rule requires a human approval the record does not have."
                ),
            },
        },
        "rationale_cites_evidence": {
            "type": "noul",
            "instructions": (
                "Every reason given in `rationale` points at something listed in `evidence`."
            ),
            "criteria": {
                "true": (
                    "Each claim in the reasoning names a measurement that appears in the "
                    "evidence list. Example: \"the 40-minute range midpoint is 3 sigma away\" "
                    "with a range-midpoint distance in the evidence."
                ),
                "false": (
                    "At least one reason rests on something not in the evidence list. Example: "
                    "\"the market feels weak\", or a reference to a past result no measurement "
                    "in the list supports."
                ),
            },
        },
        "irreversible_without_gate": {
            "type": "noul",
            "instructions": (
                "The action described would change money, an account or an order at the "
                "exchange, and the record shows no human approval for it."
            ),
            "criteria": {
                "true": (
                    "It sends, changes or cancels a real order, moves funds, or changes an "
                    "account setting, and no approval is recorded. Example: a buy with real "
                    "money and no approval field."
                ),
                "false": (
                    "It changes nothing outside the process, or an approval is recorded. "
                    "Example: holding, a paper-mode order, or a real order with a recorded "
                    "owner approval."
                ),
            },
        },
    }


def combine_decision(answers: dict) -> dict:
    """印。**これは判断ではない。**② の段で人か LLM が読む材料である。

    肯定形の問いなので、「反する側」は code が `1 − noul` にする(`jev_check` と同じ作法)。
    """
    consistent = _noul(answers, "consistent_with_policy")
    cites = _noul(answers, "rationale_cites_evidence")
    irreversible = _noul(answers, "irreversible_without_gate")
    reasons = []
    if consistent is not None and 1.0 - consistent >= ATTENTION:
        reasons.append("may_conflict_with_policy")
    if cites is not None and 1.0 - cites >= ATTENTION:
        reasons.append("rationale_may_lack_evidence")
    if irreversible is not None and irreversible >= PRESENCE:
        reasons.append("irreversible_without_gate")
    return {
        "consistent_with_policy_probability": (
            None if consistent is None else round(consistent, 4)),
        "rationale_cites_evidence_probability": None if cites is None else round(cites, 4),
        "irreversible_without_gate_probability": (
            None if irreversible is None else round(irreversible, 4)),
        "flag": bool(reasons),
        "flag_reasons": reasons,
        "reason": None if reasons else "below_threshold",
    }


# ---------------------------------------------------------------------------
# 共通(送信・書き出し・表示)
# ---------------------------------------------------------------------------
def preview_state(state: dict) -> tuple[dict, str | None]:
    """`--dry-run` で見せる state。**伏せ字を当ててから**見せる・書く。

    当たらなかったら(`RedactionError`)生の state は見せずに、掛かった理由だけを残す。
    送信のときと同じ検査を dry-run でも通すので、送る前に伏せ字の失敗が見える。
    """
    try:
        return clean_state(state), None
    except RedactionError as e:
        return {"_redaction_error": str(e)}, str(e)


def _send(client, state: dict, questions: dict) -> tuple[dict | None, str | None]:
    try:
        cleaned = clean_state(state)
    except RedactionError as e:
        return None, f"redaction:{e}"
    try:
        return client.evaluate(state=cleaned, questions=questions), None
    except JevError as e:
        return None, str(e)


def _write(out_dir: Path, stem: str, records: list[dict], summary: dict) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{stem}.jsonl"
    with out_path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        fh.write(json.dumps(summary, ensure_ascii=False) + "\n")
    return out_path


def _client_or_none(args) -> tuple[object | None, str | None]:
    if args.dry_run:
        return None, None
    try:
        return JevClient(model=args.model), None
    except JevError as e:
        return None, str(e)


def _run_units(units: list[dict], *, args, client, questions, state_of, combine,
               label_of) -> tuple[list[dict], int, str | None]:
    """単位ごとに state を組んで送り、記録を作る。**dry-run では 1 件も送らない。**"""
    records: list[dict] = []
    n_requests = 0
    unreachable: str | None = None
    for unit in units:
        rec = dict(unit["record"])
        rec["flag"] = False
        rec["reason"] = None
        rec["sent"] = False
        if args.dry_run or client is None:
            rec["state_preview"], rec["redaction_error"] = preview_state(state_of(unit))
            records.append(rec)
            continue
        resp, err = _send(client, state_of(unit), questions)
        if resp is None:
            if err and err.startswith("redaction:"):
                print(f"[jev_ops] 伏せ字の最終検査に掛かったので送信しない: {err}",
                      file=sys.stderr)
                raise SystemExit(2)
            unreachable = err
            print(f"[jev_ops] 送信に失敗({label_of(unit)}): {err}", file=sys.stderr)
            records.append(rec)
            continue
        n_requests += 1
        rec.update(combine(resp.get("answers") or {}))
        rec["sent"] = True
        rec["model"] = resp.get("model")
        records.append(rec)
    return records, n_requests, unreachable


def _finish(args, *, stem, records, summary) -> Path:
    return _write(Path(args.out), stem, records, summary)


# ---------------------------------------------------------------------------
# notify(U15)
# ---------------------------------------------------------------------------
def cmd_notify(args) -> int:
    """運用の通知を仕分ける(U15)。

    **この道具の出力は表示と記録だけである。注文の判断には使わない。**
    印は「見るだけ / 記録 / 至急」の当てはめであって、止める合図ではない(L-218)。
    """
    text_path = Path(args.text) if args.text else None
    jsonl_path = Path(args.jsonl) if args.jsonl else None
    for p in (text_path, jsonl_path):
        if p is not None and not p.is_file():
            print(f"[jev_ops] 入力が無い: {p}", file=sys.stderr)
            return 1
    items = load_notifications(text_path=text_path, jsonl_path=jsonl_path)
    if not items:
        print("[jev_ops] 通知が 1 件も無い", file=sys.stderr)

    contexts = [recent_context(items, i) for i in range(len(items))]
    units = [{
        "item": it, "context": ctx,
        "record": {"file": (jsonl_path or text_path).name if (jsonl_path or text_path) else "-",
                   "kind": "notification", "anchor": it["anchor"], "title": it["title"],
                   "source": it["source"], "given_source": it["given_source"],
                   "urgent_flag_from_bot": it["urgent"], "truncated": it["truncated"],
                   "n_recent_context": len(ctx)},
    } for it, ctx in zip(items, contexts)]

    client, unreachable = _client_or_none(args)
    records, n_requests, err = _run_units(
        units, args=args, client=client, questions=questions_notify(),
        state_of=lambda u: state_for_notification(u["item"], u["context"]),
        combine=combine_notify, label_of=lambda u: u["item"]["title"])
    unreachable = err or unreachable
    if args.dry_run or not items or n_requests > 0:
        unreachable = None

    by_source: dict[str, int] = {}
    for it in items:
        by_source[it["source"]] = by_source.get(it["source"], 0) + 1
    n_flag, by_kind = flag_counts(records)
    stem = "notify_" + ((jsonl_path or text_path).stem if (jsonl_path or text_path) else "stdin")
    summary = {"file": stem, "kind": "_summary", "mode": "notify",
               "n_notifications": len(items), "by_source": by_source,
               "n_sent": sum(1 for r in records if r["sent"]),
               "n_requests": n_requests, "n_flag": n_flag, "flag_by_kind": by_kind,
               "dry_run": bool(args.dry_run), "unreachable": unreachable,
               "use": "display_and_record_only",
               "threshold": {"attention": ATTENTION, "presence": PRESENCE}}
    out_path = _finish(args, stem=stem, records=records, summary=summary)

    if not args.summary:
        print(f"通知: {len(items)} 件  出所: "
              + " / ".join(f"{k} {v}" for k, v in sorted(by_source.items()))
              + f"  送った要求の数: {n_requests}"
              + ("  (--dry-run: 1 件も送っていない)" if args.dry_run else ""))
        if args.dry_run or n_requests == 0:
            print(f"{'行':>4}  {'出所':<9}{'直前':>4}  {'題':<34}文面の先頭")
            for u in units:
                it = u["item"]
                head = it["message"].replace("\n", " ")[:46]
                print(f"{it['anchor']:>4}  {it['source']:<9}{len(u['context']):>4}  "
                      f"{it['title'][:32]:<34}{head}")
            print("送るはずだった state(伏せ字を当てた後。--dry-run なので 1 件も送っていない):")
            for u in units:
                state, _err = preview_state(state_for_notification(u["item"], u["context"]))
                print(f"  {u['item']['anchor']:>2}: "
                      + json.dumps(state, ensure_ascii=False)[:300])
        else:
            print(f"{'行':>4}  {'出所':<9}{'注意':<9}{'notify以上':>10}{'新型':>7}  {'既知の型':<12}印")
            for rec in records:
                p = rec.get("attention_at_or_above_notify")
                n = rec.get("is_new_pattern_probability")
                print(f"{rec['anchor']:>4}  {rec['source']:<9}"
                      f"{str(rec.get('attention') or '-'):<9}"
                      f"{('-' if p is None else f'{p:.3f}'):>10}"
                      f"{('-' if n is None else f'{n:.3f}'):>7}  "
                      f"{str(rec.get('known_kind_label') or '-'):<12}"
                      + ("要確認(" + "・".join(rec.get("flag_reasons") or []) + ")"
                         if rec.get("flag") else ""))
        print(f"(印 = attention が notify 以上の確率 >= {PRESENCE} または "
              f"is_new_pattern >= {PRESENCE}。**表示と記録のみ。注文の判断には使わない**)")
        print(f"書いた先: {out_path}")
    print(summary_line(summary) + f" / 通知 {len(items)} 件(表示と記録のみ)")
    return 0


# ---------------------------------------------------------------------------
# announce(U17)
# ---------------------------------------------------------------------------
def cmd_announce(args) -> int:
    """取引所の告知を分類する(U17)。

    **この道具の出力は表示と記録だけである。注文の判断には使わない。**
    網は読み取りの GET だけ(状態ページと `gethealth`)で、注文系の端点は呼ばない。
    取れなければ HTTP コードを記録して続行する(「取れない」とは書かない)。
    """
    page = {"overall": None, "overall_class": None, "components": [], "notices": [],
            "n_notices_found": 0}
    fetch = {"status_page": None, "health": None}
    if args.text:
        path = Path(args.text)
        if not path.is_file():
            print(f"[jev_ops] 入力が無い: {path}", file=sys.stderr)
            return 1
        raw = path.read_text(encoding="utf-8", errors="replace")
        if "<" in raw and "status-day" in raw:
            page = parse_status_page(raw)
        else:
            page["notices"] = notices_from_text(raw)
            page["n_notices_found"] = len(page["notices"])
        fetch["status_page"] = {"url": str(path), "http_code": None, "error": None}
        source_name = path.name
    else:
        url = args.url or STATUS_URL
        try:
            body, code, err = http_get(url)
        except ValueError as e:
            print(f"[jev_ops] {e}", file=sys.stderr)
            return 1
        fetch["status_page"] = {"url": url, "http_code": code, "error": err}
        if body is not None:
            page = parse_status_page(body)
        fetch["health"] = fetch_health()
        source_name = "status_page"

    health = fetch["health"]
    units = [{
        "notice": n, "record": {
            "file": source_name, "kind": "notice", "anchor": i,
            "date": n.get("date"), "impact": n.get("impact"), "title": n.get("title"),
            "n_updates": len(n.get("updates") or []),
            "times": [u.get("time") for u in n.get("updates") or [] if u.get("time")],
        },
    } for i, n in enumerate(page["notices"], 1)]

    client, unreachable = _client_or_none(args)
    records, n_requests, err = _run_units(
        units, args=args, client=client, questions=questions_announce(),
        state_of=lambda u: state_for_notice(u["notice"], page, health),
        combine=combine_announce, label_of=lambda u: u["notice"].get("title") or "-")
    unreachable = err or unreachable
    if args.dry_run or not units or n_requests > 0:
        unreachable = None

    n_flag, by_kind = flag_counts(records)
    summary = {"file": source_name, "kind": "_summary", "mode": "announce",
               "n_notices": len(units), "n_notices_found": page["n_notices_found"],
               "page_overall": page["overall"], "page_overall_class": page["overall_class"],
               "components": page["components"],
               "health": health, "fetch": fetch,
               "n_sent": sum(1 for r in records if r["sent"]),
               "n_requests": n_requests, "n_flag": n_flag, "flag_by_kind": by_kind,
               "dry_run": bool(args.dry_run), "unreachable": unreachable,
               "use": "display_and_record_only",
               "threshold": {"attention": ATTENTION, "presence": PRESENCE}}
    out_path = _finish(args, stem=f"announce_{Path(source_name).stem}",
                       records=records, summary=summary)

    if not args.summary:
        sp = fetch["status_page"] or {}
        print(f"状態ページ: {sp.get('url')}  HTTP={sp.get('http_code')}"
              + (f"  失敗={sp.get('error')}" if sp.get("error") else "")
              + f"  抜けた項目: {page['n_notices_found']} 件"
              + (f"(扱うのは先頭 {len(units)} 件)"
                 if page["n_notices_found"] > len(units) else ""))
        print(f"全体の見出し: {page['overall'] or '-'}({page['overall_class'] or '-'})")
        for c in page["components"]:
            print(f"  部品: {c.get('name')} = {c.get('status')}({c.get('status_text')})")
        if health is not None:
            print(f"gethealth: status={health.get('status')}  HTTP={health.get('http_code')}"
                  + (f"  失敗={health.get('error')}" if health.get("error") else ""))
        else:
            print("gethealth: 未取得(--text のときは叩かない)")
        if args.dry_run or n_requests == 0:
            for u in units:
                n = u["notice"]
                print(f"{u['record']['anchor']:>4}  {n.get('date') or '-':<14}"
                      f"{n.get('impact') or '-':<20}{(n.get('title') or '-')[:40]}")
                for up in n.get("updates") or []:
                    print(f"       - {up.get('state') or '-'} / {up.get('time') or '-'} / "
                          f"{(up.get('body') or '')[:60]}")
        else:
            print(f"{'行':>4}  {'状態':<24}{'normal以外':>10}{'当該商品':>9}{'窓':>7}  "
                  f"{'相場への関わり':<22}印")
            for rec in records:
                def _f(v):
                    return "-" if v is None else f"{v:.3f}"
                print(f"{rec['anchor']:>4}  {str(rec.get('service_state') or '-'):<24}"
                      f"{_f(rec.get('non_normal_probability')):>10}"
                      f"{_f(rec.get('affects_product_probability')):>9}"
                      f"{_f(rec.get('time_window_stated_probability')):>7}  "
                      f"{str(rec.get('market_relevance') or '-'):<22}"
                      + ("要確認" if rec.get("flag") else ""))
        print(f"(印 = service_state が normal 以外の確率 >= {PRESENCE} かつ "
              f"affects_product >= {PRESENCE}。**表示と記録のみ。注文の判断には使わない**)")
        print(f"書いた先: {out_path}")
    print(summary_line(summary)
          + f" / 告知 {len(units)} 件、gethealth="
          + str((health or {}).get("status") if health else "未取得"))
    return 0


# ---------------------------------------------------------------------------
# decision-review(U18。**② の段で使う。今は材料が無い**)
# ---------------------------------------------------------------------------
def cmd_decision_review(args) -> int:
    """**② の段で使う。今は材料が無い。**

    自律 AI トレーダーが 1 周期ごとに残す「判断の記録」を**事後に**読むための受け口である。
    この道具は記録を読むだけで、注文にも建玉にも Kill Switch にも触れない
    (`docs/JEV.md` §4-8)。実装はここまで ── 受け口の形と 3 つの問いまでで、
    本番の記録はまだ 1 件も無い(合成した 2 件でしか動かしていない)。
    """
    path = Path(args.record)
    if not path.is_file():
        print(f"[jev_ops] 判断の記録が無い: {path}", file=sys.stderr)
        return 1
    decisions = load_decisions(path)
    units = [{"rec": d, "record": {
        "file": path.name, "kind": "decision", "anchor": d["anchor"],
        "cycle_id": d["cycle_id"], "proposed_action": d["proposed_action"],
        "missing_fields": d["missing_fields"], "unknown_action": d["unknown_action"],
        "policy_source": d["policy_source"], "constraints_source": d["constraints_source"],
    }} for d in decisions]

    client, unreachable = _client_or_none(args)
    records, n_requests, err = _run_units(
        units, args=args, client=client, questions=questions_decision(),
        state_of=lambda u: state_for_decision(u["rec"]),
        combine=combine_decision, label_of=lambda u: str(u["rec"].get("cycle_id")))
    unreachable = err or unreachable
    if args.dry_run or not units or n_requests > 0:
        unreachable = None

    n_flag, by_kind = flag_counts(records)
    summary = {"file": path.name, "kind": "_summary", "mode": "decision-review",
               "n_records": len(units), "n_sent": sum(1 for r in records if r["sent"]),
               "n_requests": n_requests, "n_flag": n_flag, "flag_by_kind": by_kind,
               "dry_run": bool(args.dry_run), "unreachable": unreachable,
               "use": "post_hoc_only", "stage": "② の段で使う。今は材料が無い",
               "threshold": {"attention": ATTENTION, "presence": PRESENCE}}
    out_path = _finish(args, stem=f"decision_{path.stem}", records=records, summary=summary)

    if not args.summary:
        print(f"判断の記録: {path.name}  件数: {len(units)}  送った要求の数: {n_requests}"
              + ("  (--dry-run: 1 件も送っていない)" if args.dry_run else ""))
        for u in units:
            d = u["rec"]
            src = d["policy_source"] or {}
            print(f"{d['anchor']:>4}  {str(d['cycle_id'])[:28]:<30}"
                  f"{str(d['proposed_action']):<7}"
                  f"方針={src.get('file') or '-'}:{src.get('lineno') or '-'} "
                  f"{(src.get('line') or d.get('policy_excerpt') or '-')[:40]}")
            if d["missing_fields"]:
                print(f"       欠けている鍵: {', '.join(d['missing_fields'])}")
            if d["unknown_action"]:
                print(f"       proposed_action が {DECISION_ACTIONS} のどれでもない")
        if args.dry_run or n_requests == 0:
            print("送るはずだった state(伏せ字を当てた後。--dry-run なので 1 件も送っていない):")
            for u in units:
                state, _err = preview_state(state_for_decision(u["rec"]))
                print(f"  {u['rec']['anchor']:>2}: "
                      + json.dumps(state, ensure_ascii=False)[:400])
        if n_requests:
            print(f"{'行':>4}  {'方針と整合':>10}{'根拠を引く':>10}{'不可逆':>8}  印")
            for rec in records:
                def _f(v):
                    return "-" if v is None else f"{v:.3f}"
                print(f"{rec['anchor']:>4}  "
                      f"{_f(rec.get('consistent_with_policy_probability')):>10}"
                      f"{_f(rec.get('rationale_cites_evidence_probability')):>10}"
                      f"{_f(rec.get('irreversible_without_gate_probability')):>8}  "
                      + ("要確認(" + "・".join(rec.get("flag_reasons") or []) + ")"
                         if rec.get("flag") else ""))
        print("(**② の段で使う。今は材料が無い。事後のみで、注文には触れない**)")
        print(f"書いた先: {out_path}")
    print(summary_line(summary) + f" / 判断の記録 {len(units)} 件(事後のみ)")
    return 0


# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="運用の通知・取引所の告知・判断の記録に狭い問いを当てる"
                    "(表示と記録のみ。注文の判断には使わない)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("notify", help="運用の通知の仕分け(U15)")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--text", help="通知の文面のファイル(1 通)")
    g.add_argument("--jsonl", help="通知の列(1 行 1 通)")
    p.add_argument("--out", default=str(DEFAULT_OUT_DIR))
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--summary", action="store_true")
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.set_defaults(func=cmd_notify)

    p = sub.add_parser("announce", help="取引所の告知・外部の文章の分類(U17)")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--url", help=f"状態ページの URL(既定 {STATUS_URL}。GET のみ)")
    g.add_argument("--text", help="告知のファイル(状態ページの HTML か、素の文章)")
    p.add_argument("--out", default=str(DEFAULT_OUT_DIR))
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--summary", action="store_true")
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.set_defaults(func=cmd_announce)

    p = sub.add_parser("decision-review", help="自律 AI の判断の事後検査(U18、受け口だけ)")
    p.add_argument("--record", required=True, help="判断の記録(JSON。1 件か配列)")
    p.add_argument("--out", default=str(DEFAULT_OUT_DIR))
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--summary", action="store_true")
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.set_defaults(func=cmd_decision_review)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
