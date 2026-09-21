"""`scripts/jev_ops.py`(U15 / U17 / U18)の読み・抜き出し・合成・模擬送信を検査する。

この道具は何も止めない。出すのは確率と印だけで、**表示と記録にしか使わない**
(オーナー逐語 L-218:「**判断はLLMと私の役割である**」)。

ネットワークには一切触れない(状態ページは `tests/fixtures/jev_ops/status_page.html` に
保存した断片で試し、送信は差し替えた偽の client でしか通さない)。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import scripts.jev_ops as O  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "jev_ops"
NOTIFICATIONS = FIXTURES / "notifications.jsonl"
STATUS_PAGE = FIXTURES / "status_page.html"
DECISIONS = FIXTURES / "decisions.json"


# ---------------------------------------------------------------------------
# 偽の client(送った state と問いを覚える。ネットワークには出ない)
# ---------------------------------------------------------------------------
class FakeClient:
    def __init__(self, answers: dict, model: str = "jev-1.13.0"):
        self.answers = answers
        self.model = model
        self.sent: list[dict] = []

    def evaluate(self, *, state, questions):
        self.sent.append({"state": state, "questions": questions})
        return {"model": self.model, "answers": self.answers}


class ExplodingClient:
    def evaluate(self, *, state, questions):  # pragma: no cover - 呼ばれたら失敗させる
        raise AssertionError("--dry-run なのに送信した")


def _install(monkeypatch, client):
    monkeypatch.setattr(O, "JevClient", lambda **kw: client)


def _choice(top: str, conf: float, options) -> dict:
    rest = (1.0 - conf) / max(len(options) - 1, 1)
    return {"type": "choice", "choice": top,
            "probabilities": {o: (conf if o == top else rest) for o in options},
            "confidence": conf}


def _noul(p: float) -> dict:
    return {"type": "noul", "noul": p}


def _notify_answers(*, attention="urgent", conf=0.9, kind="ambiguous_order_failure",
                    new_pattern=0.1) -> dict:
    return {"attention": _choice(attention, conf, O.ATTENTION_LEVELS),
            "known_kind": _choice(kind, 0.8, list(O.KNOWN_KINDS)),
            "is_new_pattern": _noul(new_pattern)}


def _announce_answers(*, service="degraded", conf=0.9, affects=0.9, window=0.2,
                      relevance="liquidity") -> dict:
    return {"service_state": _choice(service, conf, O.SERVICE_STATES),
            "affects_product": _noul(affects),
            "time_window_stated": _noul(window),
            "market_relevance": _choice(relevance, 0.8, O.MARKET_RELEVANCE)}


def _decision_answers(*, consistent=0.9, cites=0.9, irreversible=0.1) -> dict:
    return {"consistent_with_policy": _noul(consistent),
            "rationale_cites_evidence": _noul(cites),
            "irreversible_without_gate": _noul(irreversible)}


# ---------------------------------------------------------------------------
# U15: 通知の読み
# ---------------------------------------------------------------------------
def test_fixture_has_eight_notifications():
    items = O.load_notifications(jsonl_path=NOTIFICATIONS)
    assert len(items) == 8
    assert [it["anchor"] for it in items] == list(range(1, 9))
    assert {it["source"] for it in items} <= set(O.SOURCES)


def test_parse_notification_text_follows_the_notifier_shape():
    # `src/bot/monitoring/notifier.py` が組む形(至急は 🚨 が付く)
    parsed = O.parse_notification_text("🚨 **KILL SWITCH**\nreason=DAILY_LOSS\ndetail=...")
    assert parsed["title"] == "KILL SWITCH"
    assert parsed["message"].startswith("reason=DAILY_LOSS")
    plain = O.parse_notification_text("watchdog: restarted\nthe collector had stopped")
    assert plain["title"] == "watchdog: restarted"
    assert plain["message"] == "the collector had stopped"


def test_infer_source_is_deterministic_and_admits_unknown():
    assert O.infer_source("BOT START", "mode=PAPER product=FX_BTC_JPY") == "bot"
    assert O.infer_source("restarted", "the watchdog restarted the collector") == "watchdog"
    assert O.infer_source("受領", "INTAKE.jsonl に 3 件追記した") == "intake"
    assert O.infer_source("DATA GAP", "欠測が 31 分") == "quality"
    assert O.infer_source("hello", "何も手がかりが無い文") == "unknown"


def test_recent_context_takes_up_to_three_earlier_items_of_the_same_source():
    items = O.load_notifications(jsonl_path=NOTIFICATIONS)
    last_bot = max(i for i, it in enumerate(items) if it["source"] == "bot")
    ctx = O.recent_context(items, last_bot)
    assert len(ctx) == O.RECENT_CONTEXT == 3
    # 直前の 3 件であって、自分より後ろのものは入らない
    titles = [c["title"] for c in ctx]
    assert items[last_bot]["title"] not in titles
    first_quality = next(i for i, it in enumerate(items) if it["source"] == "quality")
    assert O.recent_context(items, first_quality) == []


def test_state_never_carries_the_bots_own_urgent_flag():
    items = O.load_notifications(jsonl_path=NOTIFICATIONS)
    kill = next(it for it in items if it["title"] == "KILL SWITCH")
    assert kill["urgent"] is True          # 記録には残る
    state = O.state_for_notification(kill, [])
    assert set(state) == {"title", "message", "source"}
    assert "urgent" not in json.dumps(state)


def test_text_input_makes_one_notification(tmp_path):
    path = tmp_path / "one.txt"
    path.write_text("**STATUS**\nPAPER FX_BTC_JPY equity=198,430 JPY", encoding="utf-8")
    items = O.load_notifications(text_path=path)
    assert len(items) == 1 and items[0]["source"] == "bot"


# ---------------------------------------------------------------------------
# U15: 合成(印の規則)
# ---------------------------------------------------------------------------
def test_notify_flag_when_attention_is_notify_or_above():
    out = O.combine_notify(_notify_answers(attention="urgent", conf=0.9))
    assert out["attention_at_or_above_notify"] >= O.PRESENCE
    assert out["flag"] and out["flag_reasons"] == ["attention_at_or_above_notify"]


def test_notify_no_flag_when_routine_and_known():
    out = O.combine_notify(_notify_answers(attention="log", conf=0.95,
                                           kind="periodic_status", new_pattern=0.05))
    assert out["flag"] is False and out["reason"] == "below_presence"


def test_notify_flag_on_a_new_pattern_even_when_attention_is_low():
    out = O.combine_notify(_notify_answers(attention="log", conf=0.95, kind="other",
                                           new_pattern=0.8))
    assert out["flag"] and out["flag_reasons"] == ["is_new_pattern"]


def test_notify_sums_notify_and_urgent_from_the_same_distribution():
    # notify 0.3 + urgent 0.3 = 0.6 >= PRESENCE。どちらの単独でも届かない
    answers = {"attention": {"type": "choice", "choice": "log",
                             "probabilities": {"ignore": 0.1, "log": 0.3,
                                               "notify": 0.3, "urgent": 0.3},
                             "confidence": 0.4},
               "known_kind": _choice("other", 0.5, list(O.KNOWN_KINDS)),
               "is_new_pattern": _noul(0.1)}
    out = O.combine_notify(answers)
    assert out["attention_at_or_above_notify"] == pytest.approx(0.6)
    assert out["flag"] is True


def test_known_kind_label_is_the_owners_wording():
    out = O.combine_notify(_notify_answers(kind="data_gap"))
    assert out["known_kind"] == "data_gap"
    assert out["known_kind_label"] == "データの欠測"
    assert set(O.KNOWN_KINDS.values()) == {
        "起動停止", "定時状態", "注文の曖昧な失敗", "接続・レート制限",
        "データの欠測", "予算", "その他"}


# ---------------------------------------------------------------------------
# U17: 状態ページの抜き出し(保存した HTML の断片で)
# ---------------------------------------------------------------------------
def test_status_page_headline_and_components():
    page = O.parse_status_page(STATUS_PAGE.read_text(encoding="utf-8"))
    assert page["overall"] == "All Systems Operational"
    assert page["overall_class"] == "status-none"
    names = [c["name"] for c in page["components"]]
    assert O.PRODUCT_COMPONENT in names
    cfd = next(c for c in page["components"] if c["name"] == O.PRODUCT_COMPONENT)
    assert cfd["status"] == "degraded_performance"
    assert cfd["status_text"] == "Degraded Performance"   # 属性は混ざらない


def test_status_page_notices_carry_date_impact_and_times_as_strings():
    page = O.parse_status_page(STATUS_PAGE.read_text(encoding="utf-8"))
    assert page["n_notices_found"] == 2           # 「No incidents reported」の日は数えない
    first = page["notices"][0]
    assert first["date"] == "Sep 18, 2026"
    assert first["impact"] == "impact-major"      # font-large は混ざらない
    assert first["updates"][0]["state"] == "Investigating"
    assert first["updates"][0]["time"] == "Sep 18, 21:40 JST"
    assert "注文の受付に遅延" in first["updates"][0]["body"]
    second = page["notices"][1]
    assert second["impact"] == "impact-maintenance"
    assert len(second["updates"]) == 2
    assert all(isinstance(u["time"], str) for u in second["updates"])


def test_status_page_without_incidents_reports_zero_not_a_failure():
    html = '<div class="page-status status-none"><h2 class="status font-large">OK</h2></div>' \
           '<h2 id="past-incidents">Past Incidents</h2>' \
           '<div class="status-day font-regular no-incidents">' \
           '<h3 class="date border-color font-large">Sep 19, 2026</h3>' \
           '<p class="color-secondary">No incidents reported today.</p></div>'
    page = O.parse_status_page(html)
    assert page["n_notices_found"] == 0 and page["notices"] == []
    assert page["overall"] == "OK"


def test_plain_text_notice_becomes_one_unit():
    notices = O.notices_from_text("メンテナンスのお知らせ\n9 月 17 日 4:00 から 4:30 まで")
    assert len(notices) == 1
    assert notices[0]["title"] == "メンテナンスのお知らせ"
    assert "4:30" in notices[0]["updates"][0]["body"]


def test_order_endpoints_are_refused_and_only_https_is_allowed():
    for bad in ("https://api.bitflyer.com/v1/me/sendchildorder",
                "https://api.bitflyer.com/v1/me/getpositions",
                "http://status.bitflyer.com/"):
        with pytest.raises(ValueError):
            O._assert_read_only(bad)
    O._assert_read_only(O.STATUS_URL)
    O._assert_read_only(O.HEALTH_URL)


def test_health_url_reads_the_product_and_nothing_else():
    assert O.HEALTH_URL.endswith("gethealth?product_code=FX_BTC_JPY")
    assert "/v1/me/" not in O.HEALTH_URL


def test_announce_state_holds_the_notice_and_the_component_names():
    page = O.parse_status_page(STATUS_PAGE.read_text(encoding="utf-8"))
    state = O.state_for_notice(page["notices"][0], page, {"status": "BUSY"})
    assert state["product_code"] == "FX_BTC_JPY"
    assert O.PRODUCT_COMPONENT in state["exchange_components"]
    assert state["product_health_endpoint_status"] == "BUSY"
    assert "Investigating" in state["notice_body"]
    assert state["notice_times"] == ["Sep 18, 21:40 JST"]


# ---------------------------------------------------------------------------
# U17: 合成(印の規則)
# ---------------------------------------------------------------------------
def test_announce_flag_needs_both_non_normal_and_this_product():
    hit = O.combine_announce(_announce_answers(service="suspended", affects=0.9))
    assert hit["flag"] and hit["non_normal_probability"] >= O.PRESENCE
    other = O.combine_announce(_announce_answers(service="suspended", affects=0.2))
    assert other["flag"] is False and other["reason"] == "not_this_product"
    normal = O.combine_announce(_announce_answers(service="normal", conf=0.95, affects=0.9))
    assert normal["flag"] is False and normal["reason"] == "service_state_reads_normal"


def test_announce_non_normal_is_one_minus_normal():
    out = O.combine_announce(_announce_answers(service="maintenance_scheduled", conf=0.6))
    probs = out["service_state_probabilities"]
    assert out["non_normal_probability"] == pytest.approx(1.0 - probs["normal"])


# ---------------------------------------------------------------------------
# U18: 受け口
# ---------------------------------------------------------------------------
def test_decision_records_resolve_the_policy_line_from_config():
    records = O.load_decisions(DECISIONS)
    assert len(records) == 2
    first = records[0]
    assert first["policy_source"]["file"] == "config/risk_limits.yaml"
    assert first["policy_source"]["line"].startswith("MAX_POSITION_SIZE_JPY:")
    assert first["policy_source"]["lineno"] > 0
    assert first["missing_fields"] == [] and first["unknown_action"] is False
    assert records[1]["constraints"].startswith("MAX_DAILY_LOSS_JPY:")


def test_config_lookup_refuses_paths_outside_config():
    out = O._resolve_config_line({"file": "src/bot/main.py", "key": "poll"})
    assert out["line"] is None and out["error"] == "config/ の外は読まない"
    missing = O._resolve_config_line({"file": "config/risk_limits.yaml", "key": "NOPE"})
    assert missing["line"] is None and missing["error"] == "その鍵の行が無い"


def test_decision_state_drops_empty_fields(tmp_path):
    path = tmp_path / "d.json"
    path.write_text(json.dumps({"cycle_id": "c1", "proposed_action": "hold",
                                "rationale": "", "evidence": []}), encoding="utf-8")
    rec = O.load_decisions(path)[0]
    assert sorted(rec["missing_fields"]) == ["evidence", "rationale"]
    state = O.state_for_decision(rec)
    assert set(state) == {"cycle_id", "proposed_action"}


def test_decision_flags_read_the_negative_side_in_code():
    clean = O.combine_decision(_decision_answers())
    assert clean["flag"] is False
    conflict = O.combine_decision(_decision_answers(consistent=0.2))
    assert conflict["flag"] and "may_conflict_with_policy" in conflict["flag_reasons"]
    thin = O.combine_decision(_decision_answers(cites=0.3))
    assert "rationale_may_lack_evidence" in thin["flag_reasons"]
    gate = O.combine_decision(_decision_answers(irreversible=0.8))
    assert "irreversible_without_gate" in gate["flag_reasons"]


# ---------------------------------------------------------------------------
# 問いの作法(`docs/JEV.md` §4-3: 1 判断 1 問・肯定形・具体例つき・英語)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("questions", [O.questions_notify(), O.questions_announce(),
                                       O.questions_decision()])
def test_every_question_has_instructions_and_criteria_with_examples(questions):
    for qid, q in questions.items():
        assert q["type"] in ("noul", "choice", "score"), qid
        assert q["instructions"].strip()
        if q["type"] == "noul":
            assert set(q["criteria"]) == {"true", "false"}, qid
        for text in (q["criteria"].values() if isinstance(q["criteria"], dict)
                     else q["criteria"]):
            assert "Example" in text, f"{qid} に具体例が無い"
        # 状態の断片は日本語のままだが、問いの本文は英語で書く
        assert not any("぀" <= ch <= "ヿ" for ch in q["instructions"]), qid


def test_choice_options_match_the_constants():
    assert set(O.questions_notify()["attention"]["criteria"]) == set(O.ATTENTION_LEVELS)
    assert set(O.questions_notify()["known_kind"]["criteria"]) == set(O.KNOWN_KINDS)
    assert set(O.questions_announce()["service_state"]["criteria"]) == set(O.SERVICE_STATES)
    assert set(O.questions_announce()["market_relevance"]["criteria"]) == set(O.MARKET_RELEVANCE)


# ---------------------------------------------------------------------------
# 模擬送信(偽の client。ネットワークには出ない)
# ---------------------------------------------------------------------------
def test_notify_sends_one_request_per_notification(tmp_path, monkeypatch):
    client = FakeClient(_notify_answers())
    _install(monkeypatch, client)
    code = O.main(["notify", "--jsonl", str(NOTIFICATIONS), "--out", str(tmp_path),
                   "--summary"])
    assert code == 0
    assert len(client.sent) == 8
    lines = [json.loads(ln) for ln in
             (tmp_path / "notify_notifications.jsonl").read_text(encoding="utf-8").splitlines()]
    summary = lines[-1]
    assert summary["kind"] == "_summary" and summary["n_requests"] == 8
    assert summary["use"] == "display_and_record_only"
    assert summary["by_source"] == {"bot": 6, "quality": 1, "watchdog": 1}
    assert all(r["model"] == "jev-1.13.0" for r in lines[:-1])
    assert all(r["flag"] for r in lines[:-1])   # 上の答えは attention=urgent


def test_notify_state_passes_through_redaction(tmp_path, monkeypatch):
    src = tmp_path / "leaky.jsonl"
    src.write_text(json.dumps({
        "source": "bot", "title": "STATUS",
        "message": "wrote /home/user/trade/paper_logs/bot.jsonl (mail: ops@example.com)",
    }, ensure_ascii=False) + "\n", encoding="utf-8")
    client = FakeClient(_notify_answers(attention="log", new_pattern=0.1))
    _install(monkeypatch, client)
    assert O.main(["notify", "--jsonl", str(src), "--out", str(tmp_path), "--summary"]) == 0
    sent = json.dumps(client.sent[0]["state"], ensure_ascii=False)
    assert "/home/user" not in sent and "ops@example.com" not in sent
    assert "<path>" in sent and "<email>" in sent


def test_dry_run_sends_nothing(tmp_path, monkeypatch):
    _install(monkeypatch, ExplodingClient())
    for argv in (["notify", "--jsonl", str(NOTIFICATIONS)],
                 ["announce", "--text", str(STATUS_PAGE)],
                 ["decision-review", "--record", str(DECISIONS)]):
        assert O.main([*argv, "--out", str(tmp_path), "--dry-run", "--summary"]) == 0
    for stem in ("notify_notifications", "announce_status_page", "decision_decisions"):
        lines = [json.loads(ln) for ln in
                 (tmp_path / f"{stem}.jsonl").read_text(encoding="utf-8").splitlines()]
        assert lines[-1]["dry_run"] is True and lines[-1]["n_requests"] == 0
        assert all(r["sent"] is False for r in lines[:-1])


def test_announce_sends_one_request_per_notice_without_touching_the_network(
        tmp_path, monkeypatch):
    client = FakeClient(_announce_answers())
    _install(monkeypatch, client)
    monkeypatch.setattr(O, "http_get", lambda *a, **k: pytest.fail("--text では GET しない"))
    assert O.main(["announce", "--text", str(STATUS_PAGE), "--out", str(tmp_path),
                   "--summary"]) == 0
    assert len(client.sent) == 2
    lines = [json.loads(ln) for ln in
             (tmp_path / "announce_status_page.jsonl").read_text(encoding="utf-8").splitlines()]
    summary = lines[-1]
    assert summary["n_notices"] == 2 and summary["n_requests"] == 2
    assert summary["health"] is None            # `--text` では gethealth を叩かない
    assert summary["page_overall"] == "All Systems Operational"
    assert all(r["flag"] for r in lines[:-1])   # degraded かつ当該商品


def test_announce_records_the_http_code_and_carries_on(tmp_path, monkeypatch):
    # 取れなくても止まらない(「取れない」と書かずに HTTP コードを残す)
    monkeypatch.setattr(O, "http_get", lambda url, **k: (None, 503, "HTTPError 503"))
    monkeypatch.setattr(O, "fetch_health",
                        lambda *a, **k: {"url": O.HEALTH_URL, "http_code": 503,
                                         "error": "HTTPError 503", "status": None})
    _install(monkeypatch, ExplodingClient())
    assert O.main(["announce", "--url", O.STATUS_URL, "--out", str(tmp_path),
                   "--summary"]) == 0
    summary = json.loads((tmp_path / "announce_status_page.jsonl")
                         .read_text(encoding="utf-8").splitlines()[-1])
    assert summary["fetch"]["status_page"]["http_code"] == 503
    assert summary["n_notices"] == 0 and summary["health"]["status"] is None


def test_decision_review_sends_one_request_per_record(tmp_path, monkeypatch):
    client = FakeClient(_decision_answers(consistent=0.2, cites=0.3))
    _install(monkeypatch, client)
    assert O.main(["decision-review", "--record", str(DECISIONS), "--out", str(tmp_path),
                   "--summary"]) == 0
    assert len(client.sent) == 2
    lines = [json.loads(ln) for ln in
             (tmp_path / "decision_decisions.jsonl").read_text(encoding="utf-8").splitlines()]
    assert lines[-1]["n_requests"] == 2 and lines[-1]["use"] == "post_hoc_only"
    assert all(r["flag"] for r in lines[:-1])
    # state は方針の逐語を含み、記録の外の値を足さない
    assert "MAX_POSITION_SIZE_JPY" in client.sent[0]["state"]["policy_excerpt"]


def test_unreachable_is_reported_not_swallowed(tmp_path, monkeypatch):
    class Dead:
        def evaluate(self, *, state, questions):
            raise O.JevError("503: dead")

    _install(monkeypatch, Dead())
    assert O.main(["notify", "--jsonl", str(NOTIFICATIONS), "--out", str(tmp_path),
                   "--summary"]) == 0
    summary = json.loads((tmp_path / "notify_notifications.jsonl")
                         .read_text(encoding="utf-8").splitlines()[-1])
    assert summary["unreachable"] == "503: dead"
    assert O.summary_line(summary).startswith("jev: 未到達")


# ---------------------------------------------------------------------------
# 取引の経路に置かない(`docs/JEV.md` §4-8)
# ---------------------------------------------------------------------------
def test_module_does_not_import_the_bot():
    source = Path(O.__file__).read_text(encoding="utf-8")
    assert "from bot" not in source and "import bot" not in source
    # `src/bot/` の名前は docstring の中にしか出ない(import はしない)
    body = source.split('"""', 2)[2]
    assert "from bot" not in body and "import bot" not in body


def test_thresholds_come_from_jev_check_and_are_not_redefined():
    source = Path(O.__file__).read_text(encoding="utf-8")
    assert "\nATTENTION =" not in source and "\nPRESENCE =" not in source
    assert O.ATTENTION == 0.35 and O.PRESENCE == 0.50


def test_dry_run_preview_is_redacted(tmp_path):
    state = {"title": "STATUS", "message": "/home/user/trade/paper_logs/bot.jsonl"}
    preview, err = O.preview_state(state)
    assert err is None
    assert "/home/user" not in json.dumps(preview, ensure_ascii=False)
