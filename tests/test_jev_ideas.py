"""`scripts/jev_ideas.py` の案の切り出し・集計・模擬送信を検査する。

この道具は何も止めない。出すのは分類と確率、「不確か」の印、code が数えた件数表だけである
(オーナー逐語 L-218)。**順位・重みは作らない。**
ネットワークには一切触れない(`--dry-run` か、差し替えた偽の client でしか通さない)。

**CLAUDE.md §5.1(全捨て)・§0.2 A-5 の検査**: 文書に過去の判定語が混ざっていても、
抽出は案の本文だけなので state に写らないこと(`test_state_carries_only_the_idea_body`、
`test_multi_id_note_bullet_is_not_an_idea`)。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import scripts.jev_ideas as I  # noqa: E402


# ---------------------------------------------------------------------------
# 合成した案の一覧(本物と同じ形。過去の判定語をわざと混ぜてある)
# ---------------------------------------------------------------------------
IDEAS_MD = """# 戦略案(判定なし・優先順位なし)

書いてはいけないもの: 数値、判定、期待値、「有望」「筋が悪い」等の評価、過去の結果への参照。

## 1. オーナー由来

- **O-1 レンジ中心回帰グリッド(マチルダの戦略ロジック)**: 1分足で直近40分ほどのレンジを毎分計算する。
  中心から離れた位置で建て、中心近くで利確する往復を重ねる。
  出所: オーナーの言語化。
- **O-3 / O-6 の到達点(2026-09-11、L-118。評価ではなく「どこまで測ったか」)**: K1 として検証し、
  条件付きの理解として閉じた。残った形は弱いだけ。
- **O-4 厚い板の手前に置く指値**: 一定サイズ以上の板を探し、その数円手前に指値を置く。

## 2. 引き継いだ案

- **#37 OI系**: 建玉の急増や、ロング・ショート比の極端な値が、翌日の値動きを予測できるか。
- **#66 ON1(日経225先物オーバーナイト)**: 先物の夜間セッションを買い持ちすることで、
  日中セッションより高いリターンが得られるか。
"""


def _answers(*, family="price_derived", family_conf=0.9, market="crypto", market_conf=0.9,
             in_inv=0.8, needs_exec=0.1, weight_level=0, weight_conf=0.9,
             horizon="hours", horizon_conf=0.9) -> dict:
    def choice(top, conf, options):
        rest = (1.0 - conf) / max(len(options) - 1, 1)
        probs = {o: (conf if o == top else rest) for o in options}
        return {"type": "choice", "choice": top, "probabilities": probs, "confidence": conf}

    wprobs = {str(i): (weight_conf if i == weight_level else
                       (1.0 - weight_conf) / (I.WEIGHT_LEVELS - 1))
              for i in range(I.WEIGHT_LEVELS)}
    return {
        "state_variable_family": choice(family, family_conf, I.FAMILIES),
        "market": choice(market, market_conf, I.MARKET_OPTIONS),
        "data_in_inventory": {"type": "noul", "noul": in_inv},
        "needs_execution_model": {"type": "noul", "noul": needs_exec},
        "implementation_weight": {"type": "score", "score": float(weight_level),
                                  "probabilities": wprobs, "confidence": weight_conf},
        "horizon": choice(horizon, horizon_conf, I.HORIZONS),
    }


class _FakeClient:
    """送った state を貯めるだけの偽の client。ネットワークへは触れない。"""

    def __init__(self, sent: list, answers_for=None, model: str = "jev-1.13.0", **_kw):
        self.sent = sent
        self.model = model
        self._answers_for = answers_for or (lambda state: _answers())

    def evaluate(self, state, questions):
        self.sent.append({"state": state, "questions": questions})
        return {"model": self.model, "answers": self._answers_for(state)}


# ---------------------------------------------------------------------------
# 切り出し
# ---------------------------------------------------------------------------
def test_scan_bullets_reads_one_idea_per_bullet():
    ideas, skipped = I.scan_bullets(IDEAS_MD)
    assert [i["idea_id"] for i in ideas] == ["O-1", "O-4", "#37", "#66"]
    assert [s["anchor"] for s in skipped] == [10]


def test_multi_id_note_bullet_is_not_an_idea():
    """`O-3 / O-6 の到達点…` は案 1 件ではないので切り出さない(A-5)。"""
    ideas, skipped = I.scan_bullets(IDEAS_MD)
    joined = json.dumps(ideas, ensure_ascii=False)
    assert "弱いだけ" not in joined and "閉じた" not in joined
    assert skipped[0]["head"].startswith("O-3 / O-6")


def test_body_joins_continuation_lines_and_stops_at_a_blank_line():
    ideas = I.extract_ideas(IDEAS_MD)
    o1 = next(i for i in ideas if i["idea_id"] == "O-1")
    assert "中心近くで利確する" in o1["idea_text"]
    assert o1["idea_text"].endswith("出所: オーナーの言語化。")
    assert "O-3" not in o1["idea_text"]


def test_idea_name_is_the_head_without_the_id():
    ideas = I.extract_ideas(IDEAS_MD)
    assert next(i for i in ideas if i["idea_id"] == "O-1")["idea_name"] == \
        "レンジ中心回帰グリッド(マチルダの戦略ロジック)"


def test_idea_text_is_clipped_at_the_limit():
    long_md = "- **#99 長い案**: " + "あ" * (I.MAX_IDEA_CHARS + 50) + "\n"
    idea = I.extract_ideas(long_md)[0]
    assert len(idea["idea_text"]) == I.MAX_IDEA_CHARS
    assert idea["truncated"] is True and idea["chars"] == I.MAX_IDEA_CHARS + 50


def test_real_ideas_file_is_readable():
    text = I.DEFAULT_IDEAS.read_text(encoding="utf-8")
    ideas, _ = I.scan_bullets(text)
    assert len(ideas) >= 40
    assert all(i["idea_id"] and i["idea_name"] and i["idea_text"] for i in ideas)


# ---------------------------------------------------------------------------
# state(A-5: 過去の判定・結果を入れない)
# ---------------------------------------------------------------------------
def test_state_carries_only_the_idea_body():
    idea = next(i for i in I.extract_ideas(IDEAS_MD) if i["idea_id"] == "O-1")
    state = I.state_for(idea, ["FX_BTC_JPY 1分足チャート"])
    assert set(state) == {"idea_id", "idea_name", "idea_text", "inventory_names", "markets"}
    blob = json.dumps(state, ensure_ascii=False)
    for word in ("有望", "筋が悪い", "判定", "過去の結果", "弱いだけ"):
        assert word not in blob
    assert state["markets"] == I.MARKETS


def test_verbatim_check_rejects_a_body_that_is_not_in_the_source():
    idea = next(i for i in I.extract_ideas(IDEAS_MD) if i["idea_id"] == "O-1")
    I._assert_verbatim(idea, IDEAS_MD)  # 本物なら通る
    tampered = dict(idea, parts=["この行は元の文書に無い"], idea_text="この行は元の文書に無い")
    try:
        I._assert_verbatim(tampered, IDEAS_MD)
    except ValueError:
        return
    raise AssertionError("元の文書に無い本文が検査を通ってしまった")


# ---------------------------------------------------------------------------
# 合成
# ---------------------------------------------------------------------------
def test_combine_map_reads_answers_by_key():
    rec = I.combine_map(_answers(family="orderbook", market="stock", weight_level=2,
                                 horizon="days_or_longer"))
    assert rec["family"] == "orderbook" and rec["market"] == "stock"
    assert rec["implementation_weight_level"] == 2
    assert rec["horizon"] == "days_or_longer"
    assert rec["flag"] is False and rec["uncertain"] == []


def test_uncertain_flag_is_gated_at_the_confidence_threshold():
    on = I.combine_map(_answers(market_conf=I.UNCERTAIN_CONFIDENCE - 0.01))
    off = I.combine_map(_answers(market_conf=I.UNCERTAIN_CONFIDENCE))
    assert on["flag"] is True and on["uncertain"] == ["market"]
    assert off["flag"] is False and off["reason"] == "confidence_at_or_above_uncertain"


def test_data_in_inventory_is_gated_at_presence():
    assert I.combine_map(_answers(in_inv=I.PRESENCE))["data_in_inventory"] is True
    assert I.combine_map(_answers(in_inv=I.PRESENCE - 0.01))["data_in_inventory"] is False
    assert I.combine_map(_answers(needs_exec=I.PRESENCE))["needs_execution_model"] is True


def test_combine_map_leaves_everything_unset_for_an_empty_answer():
    rec = I.combine_map({})
    assert rec["family"] is None and rec["market"] is None
    assert rec["data_in_inventory"] is None and rec["implementation_weight_level"] is None


# ---------------------------------------------------------------------------
# 集計(code が数える)
# ---------------------------------------------------------------------------
def test_aggregate_counts_the_grid_and_names_the_empty_cells():
    records = [
        dict(I.combine_map(_answers(family="price_derived", market="crypto"))),
        dict(I.combine_map(_answers(family="price_derived", market="crypto"))),
        dict(I.combine_map(_answers(family="orderbook", market="stock", weight_level=2,
                                    horizon="days_or_longer", in_inv=0.1))),
    ]
    agg = I.aggregate(records)
    assert agg["family_market"]["price_derived"]["crypto"] == 2
    assert agg["family_market"]["orderbook"]["stock"] == 1
    assert agg["n_cells"] == len(I.FAMILIES) * len(I.MARKET_OPTIONS)
    assert agg["n_empty_cells"] == agg["n_cells"] - 2
    assert ["composite", "fx"] in agg["empty_cells"]
    assert agg["data_in_inventory"] == {"あり": 2, "無し": 1, "未分類": 0}
    assert agg["implementation_weight"]["0"] == 2 and agg["implementation_weight"]["2"] == 1
    assert agg["horizon"]["hours"] == 2 and agg["horizon"]["days_or_longer"] == 1


def test_aggregate_counts_unclassified_records_as_unplaced():
    agg = I.aggregate([{"anchor": 1}, {"anchor": 2}])
    assert agg["unplaced"] == 2 and agg["n_empty_cells"] == agg["n_cells"]
    assert agg["data_in_inventory"]["未分類"] == 2


# ---------------------------------------------------------------------------
# 問い
# ---------------------------------------------------------------------------
def test_questions_have_the_shapes_the_api_requires():
    qs = I.questions_map()
    assert set(qs) == {"state_variable_family", "market", "data_in_inventory",
                       "needs_execution_model", "implementation_weight", "horizon"}
    assert set(qs["state_variable_family"]["criteria"]) == set(I.FAMILIES)
    assert set(qs["market"]["criteria"]) == set(I.MARKET_OPTIONS)
    assert set(qs["horizon"]["criteria"]) == set(I.HORIZONS)
    levels = qs["implementation_weight"]["criteria"]
    assert isinstance(levels, list) and len(levels) == I.WEIGHT_LEVELS
    for q in qs.values():
        assert q["instructions"] and q["type"] in {"choice", "noul", "score"}


# ---------------------------------------------------------------------------
# CLI(`--dry-run` は 1 件も送らない)
# ---------------------------------------------------------------------------
def _write_ideas(tmp_path: Path) -> Path:
    p = tmp_path / "IDEAS.md"
    p.write_text(IDEAS_MD, encoding="utf-8")
    return p


def test_cli_dry_run_sends_nothing_and_lists_each_idea(tmp_path, capsys):
    art = _write_ideas(tmp_path)
    out = tmp_path / "out"
    assert I.main(["map", "--ideas", str(art), "--out", str(out), "--dry-run"]) == 0
    printed = capsys.readouterr().out
    assert "--dry-run" in printed and "O-1" in printed and "#66" in printed
    assert "案として扱わなかった箇条書き" in printed
    recs = [json.loads(x) for x in
            (out / "IDEAS_map.jsonl").read_text(encoding="utf-8").splitlines()]
    summary = recs[-1]
    assert summary["kind"] == "_summary" and summary["mode"] == "map"
    assert summary["n_ideas"] == 4 and summary["n_requests"] == 0
    assert summary["n_skipped_bullets"] == 1
    assert all(r["sent"] is False for r in recs if r["kind"] != "_summary")


def test_cli_summary_line_reports_ideas_and_empty_cells(tmp_path, capsys):
    art = _write_ideas(tmp_path)
    out = tmp_path / "out"
    assert I.main(["map", "--ideas", str(art), "--out", str(out),
                   "--dry-run", "--summary"]) == 0
    last = capsys.readouterr().out.strip().splitlines()[-1]
    assert last.startswith("印 ") and "案 4 件" in last
    assert f"0 件のセル {len(I.FAMILIES) * len(I.MARKET_OPTIONS)} 個" in last


def test_cli_reports_a_missing_file(tmp_path, capsys):
    assert I.main(["map", "--ideas", str(tmp_path / "no.md"),
                   "--out", str(tmp_path / "out")]) == 1


# ---------------------------------------------------------------------------
# 模擬送信(偽の client。ネットワークへは触れない)
# ---------------------------------------------------------------------------
def test_simulated_send_classifies_every_idea(tmp_path, capsys, monkeypatch):
    sent: list = []

    def by_market(state):
        text = state["idea_name"] + state["idea_text"]
        market = "stock" if "日経" in text else "crypto"
        family = "orderbook" if "板" in text else "price_derived"
        return _answers(family=family, market=market)

    monkeypatch.setattr(I, "JevClient",
                        lambda **kw: _FakeClient(sent, by_market, **kw))
    art = _write_ideas(tmp_path)
    out = tmp_path / "out"
    assert I.main(["map", "--ideas", str(art), "--out", str(out)]) == 0
    assert len(sent) == 4
    recs = [json.loads(x) for x in
            (out / "IDEAS_map.jsonl").read_text(encoding="utf-8").splitlines()]
    summary = recs[-1]
    assert summary["n_requests"] == 4 and summary["dry_run"] is False
    assert summary["unreachable"] is None
    grid = summary["aggregate"]["family_market"]
    assert grid["orderbook"]["crypto"] == 1      # O-4 厚い板の手前に置く指値
    assert grid["price_derived"]["stock"] == 1   # #66 ON1
    assert grid["price_derived"]["crypto"] == 2
    assert summary["aggregate"]["n_empty_cells"] == summary["aggregate"]["n_cells"] - 3
    assert all(r["model"] == "jev-1.13.0" for r in recs if r["kind"] == "idea")


def test_simulated_send_never_carries_a_past_verdict_into_state(tmp_path, monkeypatch):
    sent: list = []
    monkeypatch.setattr(I, "JevClient", lambda **kw: _FakeClient(sent, None, **kw))
    art = _write_ideas(tmp_path)
    assert I.main(["map", "--ideas", str(art), "--out", str(tmp_path / "out")]) == 0
    blob = json.dumps([s["state"] for s in sent], ensure_ascii=False)
    for word in ("有望", "筋が悪い", "弱いだけ", "条件付きの理解として閉じた", "L-118"):
        assert word not in blob, f"過去の判定語が state に入った: {word}"
    for s in sent:
        assert set(s["state"]) == {"idea_id", "idea_name", "idea_text",
                                   "inventory_names", "markets"}
        assert len(s["state"]["inventory_names"]) <= 200


def test_simulated_send_marks_uncertain_classifications(tmp_path, capsys, monkeypatch):
    sent: list = []
    monkeypatch.setattr(
        I, "JevClient",
        lambda **kw: _FakeClient(sent, lambda _s: _answers(
            market_conf=I.UNCERTAIN_CONFIDENCE - 0.1), **kw))
    art = _write_ideas(tmp_path)
    out = tmp_path / "out"
    assert I.main(["map", "--ideas", str(art), "--out", str(out)]) == 0
    printed = capsys.readouterr().out
    assert "不確か" in printed
    summary = json.loads((out / "IDEAS_map.jsonl").read_text(
        encoding="utf-8").splitlines()[-1])
    assert summary["n_flag"] == 4 and summary["flag_by_kind"] == {"idea": 4}
    assert summary["threshold"]["uncertain_confidence"] == I.UNCERTAIN_CONFIDENCE


def test_output_never_contains_a_ranking_word(tmp_path, capsys, monkeypatch):
    sent: list = []
    monkeypatch.setattr(I, "JevClient", lambda **kw: _FakeClient(sent, None, **kw))
    art = _write_ideas(tmp_path)
    out = tmp_path / "out"
    assert I.main(["map", "--ideas", str(art), "--out", str(out)]) == 0
    printed = capsys.readouterr().out
    body = (out / "IDEAS_map.jsonl").read_text(encoding="utf-8")
    for word in ("有望", "効かない", "rank_score", "優先度"):
        assert word not in printed and word not in body
