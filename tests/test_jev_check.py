"""`scripts/jev_check.py` の抽出器・しきい値・伏せ字・`--dry-run` を検査する。

この道具は何も止めない。出すのは確率と要確認の印だけである(オーナー逐語 L-218)。

ネットワークには一切触れない(`JevClient` を差し替える)。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import scripts.jev_check as J  # noqa: E402


# ---------------------------------------------------------------------------
# 合成した成果物
# ---------------------------------------------------------------------------
NEGATIVE_MD = """# 調達の報告

## 結論

清算の履歴は**どこにも無い**。Binance Vision の該当ファイルが 404 だった。
他の取引所は試していない。
"""

SYMBOL_MD = """# 事前登録

## 用語

- `sd` = その `h` 本後リターンの標準偏差(bp)。相場のノイズの大きさである。

## 表

この表の `sd` は符号つきの 1 取引あたりの損益である。
"""

SCOPE_BAR_MD = """# K1

## 0. 射程

答えない(射程外): 執行を含めた損益。対象は層 2。

## 5. 採用基準

新規メイカー / 決済テイカーの往復 +5 bp を判定バーにする。
"""

WHY_MD = """# 報告

## なぜそうなるのか

板が薄い時間帯に約定が偏るためである。

## 結果

平均 +2.18 bp、片側 p = 0.03。
"""

VERIFICATION_MD = """# 監査の報告

## 経緯

指摘 34 件は多すぎる。誤警報が多いと判断した。

## 数え直し

件数は数え直した。

```
$ grep -c "止める" verdicts.md
6
```
"""

UNIVERSAL_MD = """# 既知解

## 集合

この 16 件が過去の指摘の全件である。根拠は後述する。

## 内訳

内訳はすべて表にした。
"""

MEASURED_MD = """# 報告

## 測定対象

足の形(ヒゲの向き・長さ)だけを測る。建玉状態は持たない。
"""

INTENT_MAP_MD = """# 意図マップ

| # | 意図 | 実装 | 判定 |
|---|---|---|---|
| I-8 | 反発の根拠が壊れたら降りる | `exit_on_break` | ○ |
| I-9 | 未実装 | — | ✕ |
"""


def _write(tmp_path: Path, name: str, text: str) -> Path:
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def _kinds(pairs) -> list[str]:
    return [p["kind"] for p in pairs]


# ---------------------------------------------------------------------------
# 抽出器(種類ごとに 1 件以上)
# ---------------------------------------------------------------------------
def test_extract_negative_claim(tmp_path):
    art = _write(tmp_path, "neg.md", NEGATIVE_MD)
    pairs = [p for p in J.extract_pairs(NEGATIVE_MD, art) if p["kind"] == "negative_claim"]
    assert len(pairs) >= 1
    first = pairs[0]
    assert "どこにも無い" in first["a"]
    assert first["b"]  # 同じ段落の残り
    assert first["anchor"] >= 1
    assert len(first["a"]) <= J.MAX_FRAGMENT_CHARS


def test_extract_symbol_definition(tmp_path):
    art = _write(tmp_path, "sym.md", SYMBOL_MD)
    pairs = [p for p in J.extract_pairs(SYMBOL_MD, art) if p["kind"] == "symbol_definition"]
    sd = [p for p in pairs if p["term"] == "sd"]
    assert len(sd) >= 1
    assert "標準偏差" in sd[0]["a"]
    assert "損益" in sd[0]["b"]


SCOPE_DECL_MD = """# 報告

## 5. 言えないこと・射程

| 【言えない】 | 未見のデータで効くか(4 周とも同じデータ)。|
執行の損益は測っていないので取れない。

## 6. 結論

清算の履歴はどこにも無い。
"""

TABLE_SYMBOL_MD = """# 報告

## 表

| 取引所 | h=1 | h=3 | h=10 |
|---|---|---|---|
| A | -1.0 | -1.5 | -1.7 |

## 用語

- `h` = 何本後の足の終値までを見るかである。
- `bp` = 0.01%。
"""


def test_scope_declaration_section_is_not_a_negative_claim(tmp_path):
    art = _write(tmp_path, "scope_decl.md", SCOPE_DECL_MD)
    pairs = [p for p in J.extract_pairs(SCOPE_DECL_MD, art) if p["kind"] == "negative_claim"]
    # 「言えないこと・射程」の節の中の文は対にしない
    assert all("未見のデータ" not in p["a"] for p in pairs), [p["a"] for p in pairs]
    assert all("執行の損益" not in p["a"] for p in pairs), [p["a"] for p in pairs]
    # 節の外の可用性の断定は残る
    assert any("どこにも無い" in p["a"] for p in pairs), [p["a"] for p in pairs]


def test_scope_declaration_ranges_cover_the_whole_section(tmp_path):
    ranges = J.scope_declaration_ranges(SCOPE_DECL_MD)
    assert len(ranges) == 1
    lo, hi = ranges[0]
    lines = SCOPE_DECL_MD.splitlines()
    assert lines[lo - 1].startswith("## 5.")
    assert any("未見のデータ" in l for l in lines[lo - 1:hi])
    assert all("どこにも無い" not in l for l in lines[lo - 1:hi])


def test_unavailability_criteria_names_scope_declarations():
    q = J.question_for("negative_claim", {})["is_unavailability_claim"]
    assert "scope statement" in q["criteria"]["false"]
    assert "言えないこと" in q["criteria"]["false"]


def test_table_cells_and_numeric_assignments_are_not_definitions(tmp_path):
    art = _write(tmp_path, "tbl.md", TABLE_SYMBOL_MD)
    pairs = [p for p in J.extract_pairs(TABLE_SYMBOL_MD, art)
             if p["kind"] == "symbol_definition"]
    # 表のセル `h=1` `h=3` `h=10` は定義候補にならないので、`h` の定義文は 1 つだけ = 対は 0
    assert [p for p in pairs if p["term"] == "h"] == []
    # `bp` = 0.01%(数値だけ)も定義ではない
    assert [p for p in pairs if p["term"] == "bp"] == []


def test_prose_definition_is_still_a_definition(tmp_path):
    md = ("# 用語\n\n- `sd` = その `h` 本後リターンの標準偏差(bp)。\n\n"
          "## 表\n\n| 足 | `sd` = 1 |\n\nこの表の `sd` は符号つきの損益である。\n")
    art = _write(tmp_path, "prose.md", md)
    pairs = [p for p in J.extract_pairs(md, art)
             if p["kind"] == "symbol_definition" and p["term"] == "sd"]
    assert len(pairs) == 1
    assert "標準偏差" in pairs[0]["a"] and "符号つき" in pairs[0]["b"]


def test_extract_verification_claim(tmp_path):
    art = _write(tmp_path, "ver.md", VERIFICATION_MD)
    pairs = [p for p in J.extract_pairs(VERIFICATION_MD, art)
             if p["kind"] == "verification_claim"]
    assert len(pairs) >= 1
    got = [p for p in pairs if "数え直した" in p["a"]]
    assert got, [p["a"] for p in pairs]
    # b には同じ段落の残りに加えて、直後のコードブロックが入る
    assert "grep -c" in got[0]["b"] and "```" in got[0]["b"]


def test_verification_claim_without_code_block(tmp_path):
    md = "# 報告\n\n34 件の指摘は全部読んだ。的外れだった。\n"
    art = _write(tmp_path, "v2.md", md)
    pairs = [p for p in J.extract_pairs(md, art) if p["kind"] == "verification_claim"]
    assert len(pairs) == 1
    assert "読んだ" in pairs[0]["a"]
    assert "```" not in pairs[0]["b"]


def test_extract_universal_claim(tmp_path):
    art = _write(tmp_path, "uni.md", UNIVERSAL_MD)
    pairs = [p for p in J.extract_pairs(UNIVERSAL_MD, art) if p["kind"] == "universal_claim"]
    assert len(pairs) >= 2
    assert any("全件" in p["a"] for p in pairs)
    assert any("すべて" in p["a"] for p in pairs)


def test_extract_scope_vs_bar(tmp_path):
    art = _write(tmp_path, "scope.md", SCOPE_BAR_MD)
    pairs = [p for p in J.extract_pairs(SCOPE_BAR_MD, art) if p["kind"] == "scope_vs_bar"]
    assert len(pairs) == 1
    assert "射程" in pairs[0]["a"]
    assert "採用基準" in pairs[0]["b"]


def test_extract_why_section(tmp_path):
    art = _write(tmp_path, "why.md", WHY_MD)
    pairs = [p for p in J.extract_pairs(WHY_MD, art) if p["kind"] == "why_section"]
    assert len(pairs) == 1
    assert "なぜ" in pairs[0]["a"]
    assert "結果" in pairs[0]["b"]


def test_extract_intent_vs_measured(tmp_path):
    _write(tmp_path, "INTENT_MAP.md", INTENT_MAP_MD)
    art = _write(tmp_path, "report.md", MEASURED_MD)
    pairs = [p for p in J.extract_pairs(MEASURED_MD, art) if p["kind"] == "intent_vs_measured"]
    assert len(pairs) == 1  # ○ の行は 1 行だけ
    assert "I-8" in pairs[0]["a"]
    assert "測定対象" in pairs[0]["b"]


def test_intent_vs_measured_absent_without_intent_map(tmp_path):
    art = _write(tmp_path, "report.md", MEASURED_MD)
    assert "intent_vs_measured" not in _kinds(J.extract_pairs(MEASURED_MD, art))


def test_extract_number_vs_source(tmp_path):
    art = _write(tmp_path, "num.md", "本文\n\n平均は 2.18 bp、件数は 41 件。\n")
    (tmp_path / "table.csv").write_text("metric,value\nmean_bp,2.18\n", encoding="utf-8")
    nums = [p for p in J.extract_pairs(art.read_text(encoding="utf-8"), art)
            if p["kind"] == "number_vs_source"]
    found = {p["number"] for p in nums}
    assert "2.18bp" not in found  # csv に現れる数値は挙がらない
    assert "41" in found          # csv に無い数値は挙がる
    assert all(p["no_source_files"] is False for p in nums)


def test_number_vs_source_marks_missing_source_files(tmp_path):
    art = _write(tmp_path, "num.md", "本文\n\n平均は 2.18 bp。\n")
    nums = [p for p in J.extract_pairs(art.read_text(encoding="utf-8"), art)
            if p["kind"] == "number_vs_source"]
    assert nums and all(p["no_source_files"] is True for p in nums)


# ---------------------------------------------------------------------------
# しきい値と印の境界
# ---------------------------------------------------------------------------
def test_attention_threshold_boundary():
    assert J.ATTENTION == 0.35
    assert not hasattr(J, "STOP")
    assert J.flag_for(0.3499) is False
    assert J.flag_for(J.ATTENTION) is True
    assert J.flag_for(0.9999) is True
    assert J.flag_for(1.0) is True


def test_violation_probability_noul_is_one_minus_noul():
    qid, p = J.violation_probability(
        "negative_claim", {"scope_and_method_attached": {"type": "noul", "noul": 0.9}})
    assert qid == "scope_and_method_attached"
    assert p == pytest.approx(0.1)
    qid, p = J.violation_probability(
        "symbol_definition", {"same_meaning": {"type": "noul", "noul": 0.2}})
    assert qid == "same_meaning"
    assert p == pytest.approx(0.8)


def test_violation_probability_choice_uses_contradicts():
    qid, p = J.violation_probability("scope_vs_bar", {"relation": {
        "type": "choice", "choice": "contradicts",
        "probabilities": {"consistent": 0.1, "contradicts": 0.85, "unrelated": 0.05},
    }})
    assert qid == "relation"
    assert p == pytest.approx(0.85)


def test_presence_composition_boundary():
    """negative_claim は presence と scope の**両方**を満たしたときだけ印が付く。"""
    assert J.PRESENCE == 0.50
    # presence が足りない: 印は付かず、理由が残る(捨てない)
    assert J.decide_flag("negative_claim", 0.9, 0.49) == (False, "not_unavailability_claim")
    assert J.decide_flag("negative_claim", 0.9, None) == (False, "not_unavailability_claim")
    # presence 丁度 0.50 は満たす側
    assert J.decide_flag("negative_claim", 0.9, J.PRESENCE) == (True, None)
    # presence は満たすが scope は満たさない(反する側が ATTENTION 未満)
    assert J.decide_flag("negative_claim", 0.3499, 0.9) == (False, None)
    assert J.decide_flag("negative_claim", J.ATTENTION, 0.9) == (True, None)
    # scope_and_method_attached <= 1 - ATTENTION が境界(noul=0.65 は印が付く側)
    _qid, viol = J.violation_probability(
        "negative_claim", {"scope_and_method_attached": {"type": "noul", "noul": 0.65}})
    assert J.decide_flag("negative_claim", viol, 0.9) == (True, None)
    _qid, viol = J.violation_probability(
        "negative_claim", {"scope_and_method_attached": {"type": "noul", "noul": 0.66}})
    assert J.decide_flag("negative_claim", viol, 0.9) == (False, None)
    # 他の種類は presence を見ない
    assert J.decide_flag("scope_vs_bar", 0.4, None) == (True, None)
    assert J.decide_flag("scope_vs_bar", 0.2, None) == (False, None)


def test_presence_composition_for_the_two_new_kinds():
    for kind, qid in (("verification_claim", "is_verification_claim"),
                      ("universal_claim", "is_universal_claim")):
        assert J.presence_qid(kind) == qid
        reason = "not_" + qid.removeprefix("is_")
        assert J.decide_flag(kind, 0.9, 0.49) == (False, reason)
        assert J.decide_flag(kind, 0.9, None) == (False, reason)
        assert J.decide_flag(kind, 0.9, J.PRESENCE) == (True, None)
        assert J.decide_flag(kind, 0.3499, 0.9) == (False, None)
        assert J.decide_flag(kind, J.ATTENTION, 0.9) == (True, None)


def test_questions_for_the_two_new_kinds():
    q = J.question_for("verification_claim", {})
    assert set(q) == {"evidence_attached", "is_verification_claim"}
    q = J.question_for("universal_claim", {})
    assert set(q) == {"enumeration_attached", "is_universal_claim"}
    for kind in ("verification_claim", "universal_claim"):
        for spec in J.question_for(kind, {}).values():
            assert spec["type"] == "noul"
            assert set(spec["criteria"]) == {"true", "false"}


def test_violation_probability_for_the_two_new_kinds():
    qid, p = J.violation_probability(
        "verification_claim", {"evidence_attached": {"type": "noul", "noul": 0.2}})
    assert qid == "evidence_attached" and p == pytest.approx(0.8)
    qid, p = J.violation_probability(
        "universal_claim", {"enumeration_attached": {"type": "noul", "noul": 0.2}})
    assert qid == "enumeration_attached" and p == pytest.approx(0.8)


def test_new_kinds_end_to_end_keep_both_probabilities(tmp_path, fake_client):
    fake_client.noul_by_qid = {"is_verification_claim": 0.9, "evidence_attached": 0.1}
    art = _write(tmp_path, "ver.md", VERIFICATION_MD)
    out = tmp_path / "out"
    assert J.main(["audit", str(art), "--out", str(out)]) == 0
    recs = [r for r in _read_jsonl(out / "ver.jsonl") if r["kind"] == "verification_claim"]
    assert recs
    for rec in recs:
        assert rec["presence_probability"] == 0.9
        assert rec["violation_probability"] == pytest.approx(0.9)
        assert rec["flag"] is True and rec["reason"] is None
    _state, questions = fake_client.calls[0]
    assert set(questions) == {"evidence_attached", "is_verification_claim"}


def test_presence_probability_only_for_negative_claim():
    assert J.presence_probability(
        "negative_claim", {"is_unavailability_claim": {"type": "noul", "noul": 0.7}}) == 0.7
    assert J.presence_probability("scope_vs_bar", {}) is None
    assert J.presence_qid("scope_vs_bar") is None


def test_negative_claim_keeps_both_probabilities(tmp_path, fake_client):
    fake_client.noul_by_qid = {"is_unavailability_claim": 0.49}
    art = _write(tmp_path, "neg.md", NEGATIVE_MD)
    out = tmp_path / "out"
    assert J.main(["audit", str(art), "--out", str(out)]) == 0
    negs = [r for r in _read_jsonl(out / "neg.jsonl") if r["kind"] == "negative_claim"]
    assert negs
    for rec in negs:
        assert rec["presence_probability"] == 0.49
        assert rec["violation_probability"] == pytest.approx(0.9)
        assert rec["flag"] is False
        assert rec["reason"] == "not_unavailability_claim"
    # 1 対 = 1 要求、その 1 要求に 2 問
    state, questions = fake_client.calls[0]
    assert set(questions) == {"scope_and_method_attached", "is_unavailability_claim"}
    assert len(fake_client.calls) == len(negs)


def test_negative_claim_flags_when_both_conditions_hold(tmp_path, fake_client):
    art = _write(tmp_path, "neg.md", NEGATIVE_MD)
    out = tmp_path / "out"
    assert J.main(["audit", str(art), "--out", str(out)]) == 0
    negs = [r for r in _read_jsonl(out / "neg.jsonl") if r["kind"] == "negative_claim"]
    assert negs and all(r["flag"] is True and r["reason"] is None for r in negs)


def test_negative_claim_pairs_are_capped_at_40(tmp_path):
    body = "\n\n".join(f"{i} 番目の経路は存在しない。" for i in range(45))
    art = _write(tmp_path, "many.md", "# 報告\n\n" + body + "\n")
    pairs = J.extract_pairs(art.read_text(encoding="utf-8"), art)
    assert sum(1 for p in pairs if p["kind"] == "negative_claim") == 45
    kept, n_dropped = J.cap_negative_claims(pairs)
    assert J.MAX_NEGATIVE_PAIRS == 40
    assert sum(1 for p in kept if p["kind"] == "negative_claim") == 40
    assert n_dropped == 5
    # negative_claim 以外は 1 件も落ちない
    assert ([p["kind"] for p in kept if p["kind"] != "negative_claim"]
            == [p["kind"] for p in pairs if p["kind"] != "negative_claim"])


def test_truncated_pairs_is_recorded(tmp_path, fake_client):
    body = "\n\n".join(f"{i} 番目の経路は存在しない。" for i in range(45))
    art = _write(tmp_path, "many.md", "# 報告\n\n" + body + "\n")
    out = tmp_path / "out"
    assert J.main(["audit", str(art), "--out", str(out), "--dry-run"]) == 0
    summary = _read_jsonl(out / "many.jsonl")[-1]
    assert summary["truncated_pairs"] == 5


def test_flag_counts_is_counts_and_kinds_only():
    total, by_kind = J.flag_counts([
        {"kind": "negative_claim", "flag": True},
        {"kind": "negative_claim", "flag": True},
        {"kind": "scope_vs_bar", "flag": False},
        {"kind": "number_vs_source", "flag": True},
    ])
    assert total == 3
    assert by_kind == {"negative_claim": 2, "number_vs_source": 1}
    assert J.flag_counts([]) == (0, {})


def test_questions_per_kind():
    # negative_claim だけ 2 問(presence の判定を別の問いに分ける)。同じ state なので 1 要求。
    q = J.question_for("negative_claim", {})
    assert list(q) == ["scope_and_method_attached", "is_unavailability_claim"]
    assert q["is_unavailability_claim"]["type"] == "noul"
    assert set(q["is_unavailability_claim"]["criteria"]) == {"true", "false"}
    assert list(J.question_for("symbol_definition", {"term": "sd"})) == ["same_meaning"]
    for kind in ("scope_vs_bar", "intent_vs_measured", "why_section"):
        q = J.question_for(kind, {})
        assert list(q) == ["relation"]
        assert set(q["relation"]["criteria"]) == {"consistent", "contradicts", "unrelated"}


# ---------------------------------------------------------------------------
# 送信の差し替え
# ---------------------------------------------------------------------------
class _FakeClient:
    calls: list[tuple] = []

    def __init__(self, model=None, **kwargs):
        self.model = model

    # 既定: scope は 0.1(= 反する側 0.9)、presence は 0.9(不在の主張である)
    noul_by_qid: dict = {}

    def evaluate(self, state, questions):
        _FakeClient.calls.append((state, questions))
        answers = {}
        for qid, spec in questions.items():
            if spec["type"] == "noul":
                default = 0.9 if qid == "is_unavailability_claim" else 0.1
                answers[qid] = {"type": "noul",
                                "noul": _FakeClient.noul_by_qid.get(qid, default)}
            else:
                answers[qid] = {"type": "choice", "choice": "contradicts",
                                "probabilities": {"consistent": 0.1, "contradicts": 0.85,
                                                  "unrelated": 0.05}}
        return {"model": "fake", "answers": answers}


@pytest.fixture
def fake_client(monkeypatch):
    _FakeClient.calls = []
    _FakeClient.noul_by_qid = {}
    monkeypatch.setattr(J, "JevClient", _FakeClient)
    return _FakeClient


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def test_dry_run_sends_nothing(tmp_path, fake_client):
    art = _write(tmp_path, "neg.md", NEGATIVE_MD)
    out = tmp_path / "out"
    rc = J.main(["audit", str(art), "--out", str(out), "--dry-run"])
    assert rc == 0
    assert fake_client.calls == []  # 1 件も送っていない
    records = _read_jsonl(out / "neg.jsonl")
    summary = records[-1]
    assert summary["kind"] == "_summary"
    assert summary["dry_run"] is True
    assert summary["n_requests"] == 0
    assert summary["n_flag"] == 0
    assert summary["unreachable"] is None
    assert all(r["flag"] is False for r in records if r["kind"] != "_summary")
    assert any(r["kind"] == "negative_claim" for r in records)


def test_audit_sends_one_request_per_pair_and_flags(tmp_path, fake_client):
    art = _write(tmp_path, "scope.md", SCOPE_BAR_MD)
    out = tmp_path / "out"
    rc = J.main(["audit", str(art), "--out", str(out)])
    assert rc == 0
    records = _read_jsonl(out / "scope.jsonl")
    summary = records[-1]
    # number_vs_source は送らない。送った要求の数 = 送った対の数。
    sent = [r for r in records if r.get("sent")]
    assert summary["n_requests"] == len(sent) == len(fake_client.calls)
    assert all(r["kind"] != "number_vs_source" for r in sent)
    scope = [r for r in records if r["kind"] == "scope_vs_bar"][0]
    assert scope["violation_probability"] == pytest.approx(0.85)
    assert scope["flag"] is True
    assert summary["n_flag"] >= 1
    assert summary["flag_by_kind"]["scope_vs_bar"] == 1
    # 「止める」「通す」の語は出力に出さない
    assert "route" not in summary and "route" not in scope
    # state は code が組む(見られる側が書かない): 断片と役割だけを送っている
    state, _questions = fake_client.calls[0]
    assert set(state) == {"kind", "fragment_a_role", "fragment_a", "fragment_b_role", "fragment_b"}


def test_number_vs_source_is_never_sent(tmp_path, fake_client):
    art = _write(tmp_path, "num.md", "本文\n\n平均は 2.18 bp、件数は 41 件。\n")
    (tmp_path / "table.csv").write_text("metric,value\nmean_bp,2.18\n", encoding="utf-8")
    out = tmp_path / "out"
    assert J.main(["audit", str(art), "--out", str(out)]) == 0
    records = _read_jsonl(out / "num.jsonl")
    nums = [r for r in records if r["kind"] == "number_vs_source"]
    assert nums
    assert all(r["sent"] is False for r in nums)
    assert all(r["flag"] is True for r in nums)  # 突き合わせ先があるので比較が成立する
    assert fake_client.calls == []


def test_summary_line_and_summary_flag(tmp_path, fake_client, capsys):
    art = _write(tmp_path, "scope.md", SCOPE_BAR_MD)
    out = tmp_path / "out"
    assert J.main(["audit", str(art), "--out", str(out), "--summary"]) == 0
    printed = capsys.readouterr().out.strip().splitlines()
    assert len(printed) == 1  # 末尾の 1 行だけ
    assert printed[0].startswith("印 ")
    assert "scope_vs_bar 1 件" in printed[0]


def test_summary_line_reports_unreachable_and_exits_0(tmp_path, monkeypatch, capsys):
    class _Dead:
        def __init__(self, model=None, **kwargs):
            pass

        def evaluate(self, state, questions):
            raise J.JevError("403: Must supply an API key")

    monkeypatch.setattr(J, "JevClient", _Dead)
    art = _write(tmp_path, "scope.md", SCOPE_BAR_MD)
    out = tmp_path / "out"
    assert J.main(["audit", str(art), "--out", str(out), "--summary"]) == 0
    printed = capsys.readouterr().out.strip().splitlines()
    assert len(printed) == 1
    assert printed[0].startswith("jev: 未到達(")
    summary = _read_jsonl(out / "scope.jsonl")[-1]
    assert summary["unreachable"]
    assert summary["n_requests"] == 0


# ---------------------------------------------------------------------------
# 伏せ字で送信を取りやめること
# ---------------------------------------------------------------------------
def test_clean_state_raises_when_redaction_is_bypassed(monkeypatch):
    from scripts.jev.redact import RedactionError
    monkeypatch.setattr(J, "redact_json", lambda obj: obj)
    with pytest.raises(RedactionError):
        J.clean_state({"fragment_a": "連絡先は someone@example.com である"})


def test_audit_returns_2_and_sends_nothing_when_redaction_check_fails(
        tmp_path, fake_client, monkeypatch):
    monkeypatch.setattr(J, "redact_json", lambda obj: obj)
    art = _write(tmp_path, "leak.md", "# 報告\n\n連絡先 someone@example.com は取れない。\n")
    out = tmp_path / "out"
    rc = J.main(["audit", str(art), "--out", str(out)])
    assert rc == 2
    assert fake_client.calls == []


def test_clean_state_redacts_by_default():
    state = J.clean_state({"fragment_a": "連絡先は someone@example.com である"})
    assert "someone@example.com" not in state["fragment_a"]


# ---------------------------------------------------------------------------
# score
# ---------------------------------------------------------------------------
def test_score_counts_detection_miss_and_false_positive(tmp_path, capsys):
    out = tmp_path / "out"
    out.mkdir()
    rows = [
        ("A.md", 1),   # has_answer=1 → 検出
        ("B.md", 0),   # has_answer=1 → 見逃し
        ("C.md", 2),   # has_answer=0 → 誤検出
        ("D.md", 0),   # has_answer=0 → 該当なし
    ]
    for name, n_flag in rows:
        (out / f"{Path(name).stem}.jsonl").write_text(
            json.dumps({"file": name, "kind": "_summary", "n_flag": n_flag,
                        "flag_by_kind": {}, "n_pairs": 1, "n_sent": 1,
                        "n_requests": 1, "dry_run": False, "unreachable": None},
                       ensure_ascii=False) + "\n", encoding="utf-8")
    labels = tmp_path / "labels.csv"
    labels.write_text("file,has_answer\nA.md,1\nB.md,1\nC.md,0\nD.md,0\nE.md,1\n",
                      encoding="utf-8")
    assert J.main(["score", "--labels", str(labels), "--dir", str(out)]) == 0
    text = capsys.readouterr().out
    assert "検出 1 件 / 見逃し 1 件 / 誤検出 1 件 / 該当なし・印なし 1 件 / 未評価 1 件" in text


def _write_summary(out: Path, name: str, n_flag: int) -> None:
    (out / f"{Path(name).stem}.jsonl").write_text(json.dumps(
        {"file": name, "kind": "_summary", "n_flag": n_flag, "flag_by_kind": {},
         "n_pairs": 1, "n_sent": 1, "n_requests": 1, "dry_run": False,
         "unreachable": None}, ensure_ascii=False) + "\n", encoding="utf-8")


def test_score_controls_are_counted_as_no_correction(tmp_path, capsys):
    out = tmp_path / "out"
    out.mkdir()
    ctrl_dir = tmp_path / "controls"
    ctrl_dir.mkdir()
    (ctrl_dir / "CTRL-A.md").write_text("対照 A", encoding="utf-8")
    (ctrl_dir / "CTRL-B.md").write_text("対照 B", encoding="utf-8")
    lone = tmp_path / "CTRL-C.md"
    lone.write_text("対照 C", encoding="utf-8")

    _write_summary(out, "KA-01.md", 2)   # has_answer=1 → 検出
    _write_summary(out, "CTRL-A.md", 0)  # 対照・印なし → 該当なし
    _write_summary(out, "CTRL-B.md", 1)  # 対照・印あり → 誤検出
    _write_summary(out, "CTRL-C.md", 0)  # ファイル指定の対照 → 該当なし
    labels = tmp_path / "labels.csv"
    labels.write_text("file,has_answer\nKA-01.md,1\n", encoding="utf-8")

    assert J.main(["score", "--labels", str(labels), "--dir", str(out),
                   "--controls", str(ctrl_dir), str(lone)]) == 0
    text = capsys.readouterr().out
    assert ("検出 1 件 / 見逃し 0 件 / 誤検出 1 件 / 該当なし・印なし 2 件 / 未評価 0 件"
            "(うち対照 3 件)") in text
    assert "CTRL-A.md" in text and "CTRL-C.md" in text


def test_score_controls_do_not_override_labels(tmp_path, capsys):
    out = tmp_path / "out"
    out.mkdir()
    _write_summary(out, "KA-01.md", 1)
    ctrl_dir = tmp_path / "controls"
    ctrl_dir.mkdir()
    (ctrl_dir / "KA-01.md").write_text("同名", encoding="utf-8")
    labels = tmp_path / "labels.csv"
    labels.write_text("file,has_answer\nKA-01.md,1\n", encoding="utf-8")
    assert J.main(["score", "--labels", str(labels), "--dir", str(out),
                   "--controls", str(ctrl_dir)]) == 0
    text = capsys.readouterr().out
    # ラベル側の 1 行だけが残り、誤検出には数えられない
    assert "検出 1 件 / 見逃し 0 件 / 誤検出 0 件" in text
    assert "うち対照" not in text


def test_score_treats_dry_run_and_unreachable_as_unevaluated(tmp_path, capsys):
    out = tmp_path / "out"
    out.mkdir()
    (out / "A.jsonl").write_text(json.dumps(
        {"file": "A.md", "kind": "_summary", "n_flag": 0, "flag_by_kind": {},
         "n_pairs": 1, "n_sent": 0, "n_requests": 0, "dry_run": True,
         "unreachable": None}, ensure_ascii=False) + "\n", encoding="utf-8")
    (out / "B.jsonl").write_text(json.dumps(
        {"file": "B.md", "kind": "_summary", "n_flag": 0, "flag_by_kind": {},
         "n_pairs": 1, "n_sent": 0, "n_requests": 0, "dry_run": False,
         "unreachable": "403"}, ensure_ascii=False) + "\n", encoding="utf-8")
    labels = tmp_path / "labels.csv"
    labels.write_text("file,has_answer\nA.md,1\nB.md,1\n", encoding="utf-8")
    assert J.main(["score", "--labels", str(labels), "--dir", str(out)]) == 0
    text = capsys.readouterr().out
    assert "検出 0 件 / 見逃し 0 件 / 誤検出 0 件 / 該当なし・印なし 0 件 / 未評価 2 件" in text


# ---------------------------------------------------------------------------
# 問いと測定の照合(L-238 の事例。`docs/JEV.md` §9)
# ---------------------------------------------------------------------------
# 今日の設計 `REACTION_DESIGN_2026-09-18.md` §8 の表の形の小さな複製(列と印だけ同じ)
DESIGN_INTENT_MD = """# 段 A の設計

## 8. INTENT_MAP(原文の意図 1 項 × この設計の要素)

印: ○ 一致 / △ 代理 / ✕ 未実装 / ＋ 意図に無い実装。

| # | 原文の意図(逐語) | この設計の要素 | 印 | 備考 |
|---|---|---|---|---|
| I-1 | 「**清算の監視による値段の上がりすぎ下がりすぎやトレンド転換を捉えることができるか確認**」 | §3 (a)(b)(c) | **△** | 直接あたる観測量が無い |
| I-3 | 「**海外取引所の高レバ市場**」 | Binance COIN-M | **○** | |
| I-6 | 「**bitmex を最初に使って検証**」 | 段 A では使わない | **✕** | 清算イベントが無い |
| I-12 | 「**トレンド転換が起きるか**」 | §3 (b) | **△**(2026-09-18 に ○ から下げた) | 代理 |
| I-17 | (原文に無い) | §4 E 換算レバレッジ | **＋** | 出所は L-194 |
"""

PREREG_MD = """# 事前登録

## 6. 主指標と帰無

主指標 = 戻り到達(W 時間 VWAP へ h 分以内に戻ったか)の割合。

## 6.1 対照 (ii) の作り方

同じ日の清算の無い時刻を、ビンの薄さで 1 対 1 に合わせる。出発点の距離は合わせない。

## 9. 採用基準の型

置くバーは |t| ≥ 3.925 だけ。
"""

RESULT_MD = """# 結果の読み

## 1. 判定

**F1 の読み = 「F1 の反証」**。戻り到達は対照より低く、想定とは逆の向きが出た。

## 4. なぜそうなるのか

候補 1: 機構にエッジが無い。差は 6.5 ポイントで、検出されずの行が 11 ある。
"""


def test_extract_intent_rows_from_design(tmp_path):
    _write(tmp_path, "REACTION_DESIGN_2026-09-18.md", DESIGN_INTENT_MD)
    art = _write(tmp_path, "PREREG.md", PREREG_MD)
    rows = J.extract_intent_rows(art)
    # ○ / △ / ✕ の全行を取る。＋(意図に無い実装)は取らない
    assert [r["mark"] for r in rows] == ["△", "○", "✕", "△"]
    assert "上がりすぎ下がりすぎ" in rows[0]["row"]
    assert all(r["source"] == "REACTION_DESIGN_2026-09-18.md" for r in rows)


def test_intent_rows_empty_without_intent_map(tmp_path):
    art = _write(tmp_path, "PREREG.md", PREREG_MD)
    assert J.extract_intent_rows(art) == []


def test_quantity_and_control_sections_are_one_each(tmp_path):
    # 判定の量は 主指標 → 採用基準 → 判定に使う の順で 1 つだけ。
    # 「判定」を含むだけの節(§3 分割)は拾わない
    q = J.quantity_sections(PREREG_MD)
    assert len(q) == 1 and "主指標" in q[0]["title"]
    c = J.control_sections(PREREG_MD)
    assert len(c) == 1 and "対照" in c[0]["title"]      # 帰無は §6 と同じ節なので次点の 対照
    assert c[0]["lineno"] != q[0]["lineno"]
    md = "# x\n\n## 3. 分割(探索 / 判定の境界)\n\n本文。\n\n## 9. 採用基準の型\n\nバー。\n"
    q2 = J.quantity_sections(md)
    assert len(q2) == 1 and "採用基準" in q2[0]["title"]


def test_purpose_vs_quantity_pairs(tmp_path):
    _write(tmp_path, "REACTION_DESIGN_2026-09-18.md", DESIGN_INTENT_MD)
    art = _write(tmp_path, "PREREG.md", PREREG_MD)
    pairs = [p for p in J.extract_pairs(PREREG_MD, art) if p["kind"] == "purpose_vs_quantity"]
    # 意図の行 4 × 判定の量の節 1 = 4(意図の行ごとに 1 対)
    assert len(pairs) == 4
    one = pairs[0]
    assert set(one["state"]) == {"owner_purpose", "judgment_quantity"}
    assert "上がりすぎ下がりすぎ" in one["state"]["owner_purpose"]
    assert "主指標" in one["state"]["judgment_quantity"]
    assert [p["intent_id"] for p in pairs] == ["I-1", "I-3", "I-6", "I-12"]


def test_control_vs_quantity_is_one_pair(tmp_path):
    art = _write(tmp_path, "PREREG.md", PREREG_MD)
    pairs = [p for p in J.extract_pairs(PREREG_MD, art) if p["kind"] == "control_vs_quantity"]
    assert len(pairs) == 1
    assert set(pairs[0]["state"]) == {"control_group", "judgment_quantity"}
    assert "出発点の距離は合わせない" in pairs[0]["state"]["control_group"]
    assert pairs[0]["state"]["control_group"] != pairs[0]["state"]["judgment_quantity"]


def test_report_kinds_are_not_applied_to_a_prereg(tmp_path):
    _write(tmp_path, "REACTION_DESIGN_2026-09-18.md", DESIGN_INTENT_MD)
    art = _write(tmp_path, "PREREG.md", PREREG_MD)
    kinds = _kinds(J.extract_pairs(PREREG_MD, art))
    assert J.looks_like_report(PREREG_MD, art) is False
    for kind in ("conclusion_vs_purpose", "other_cause_named", "direction_supported"):
        assert kind not in kinds


def test_looks_like_report(tmp_path):
    art = _write(tmp_path, "RESULT_2026-09-19.md", "# 何か\n\n本文。\n")
    assert J.looks_like_report(art.read_text(encoding="utf-8"), art) is True
    art2 = _write(tmp_path, "x.md", RESULT_MD)     # 表題に「結果の読み」
    assert J.looks_like_report(RESULT_MD, art2) is True
    # 事前登録の §10「結果の読みで必ず出す表」はレベル 2 なので報告にしない
    md = "# 事前登録\n\n## 10. 結果の読みで必ず出す表\n\n本文。\n"
    art3 = _write(tmp_path, "PREREG_x.md", md)
    assert J.looks_like_report(md, art3) is False


def test_conclusion_lines_drop_table_rows(tmp_path):
    rows = "\n".join(f"| 系統 {i} | 検出されず |" for i in range(15))
    md = ("# 結果の読み\n\n## 0. 前置き\n\n差ありに見えるが前置きである。\n\n"
          "## 1. 判定\n\n読みは反証である。\n\n" + rows + "\n")
    dropped: list = []
    lines = J.conclusion_lines(md, dropped)
    # 表のデータ行は結論の行にしない(外した行番号は残す)
    assert [b for _ln, b in lines] == ["読みは反証である。"]
    assert len(dropped) == 15
    # 見出しに「判定 / 読み / なぜ」を含む節の外(§0 前置き)は拾わない
    assert all("前置き" not in b for _ln, b in lines)


def test_conclusion_lines_are_capped(tmp_path):
    body = "\n".join(f"- {i} 番目は検出されずである。" for i in range(15))
    md = "# 結果の読み\n\n## 1. 判定\n\n" + body + "\n"
    assert len(J.conclusion_lines(md)) == J.MAX_CONCLUSION_LINES == 10


def test_conclusion_vs_purpose_and_other_cause_pairs(tmp_path):
    _write(tmp_path, "REACTION_DESIGN_2026-09-18.md", DESIGN_INTENT_MD)
    art = _write(tmp_path, "RESULT.md", RESULT_MD)
    pairs = J.extract_pairs(RESULT_MD, art)
    concl = [p for p in pairs if p["kind"] == "conclusion_vs_purpose"]
    other = [p for p in pairs if p["kind"] == "other_cause_named"]
    assert concl and other
    assert all(set(p["state"]) == {"report_conclusion", "owner_purpose"} for p in concl)
    assert all(set(p["state"]) == {"report_conclusion", "conclusion_section"} for p in other)
    assert any("反証" in p["state"]["report_conclusion"] for p in concl)


def test_direction_supported_falls_back_to_the_prereg(tmp_path):
    # 報告に 判定の量 / 対照 の節が無ければ、同じディレクトリの事前登録(名前順の最後)から取る
    _write(tmp_path, "REACTION_PREREG_2026-09-18.md", PREREG_MD)
    art = _write(tmp_path, "RESULT.md", RESULT_MD)
    pairs = [p for p in J.extract_pairs(RESULT_MD, art) if p["kind"] == "direction_supported"]
    assert len(pairs) == 1
    assert set(pairs[0]["state"]) == {"report_conclusion", "judgment_quantity", "control_group"}
    assert "逆" in pairs[0]["state"]["report_conclusion"]
    assert pairs[0]["sections_from"] == "REACTION_PREREG_2026-09-18.md"
    # 事前登録も無ければ作らない
    alone = tmp_path / "alone"
    alone.mkdir()
    art2 = _write(alone, "RESULT.md", RESULT_MD)
    assert [p for p in J.extract_pairs(RESULT_MD, art2)
            if p["kind"] == "direction_supported"] == []


def test_prereg_named_in_the_report_wins(tmp_path):
    """(b) 報告の本文が名指しした事前登録を使う(検収 2 の未決 1)。"""
    for name in ("REACTION_PREREG_2026-09-18.md", "REACTION_R2_PREREG_2026-09-19.md",
                 "REACTION_PREREG_DRAFT_2026-09-18.md"):
        _write(tmp_path, name, PREREG_MD)
    md = ("# 結果の読み — 2026-09-19\n\n"
          "事前登録: `REACTION_PREREG_2026-09-18.md`。\n\n"
          "## 1. 判定\n\n読みは反証で、想定とは逆の向きが出た。\n")
    art = _write(tmp_path, "RESULT.md", md)
    assert J.latest_prereg(art, md).name == "REACTION_PREREG_2026-09-18.md"
    pairs = [p for p in J.extract_pairs(md, art) if p["kind"] == "direction_supported"]
    assert len(pairs) == 1
    assert pairs[0]["sections_from"] == "REACTION_PREREG_2026-09-18.md"


def test_prereg_falls_back_to_the_older_ones(tmp_path):
    """(c) 名指しが無ければ、報告より古いもののうち名前順の最後。"""
    for name in ("REACTION_PREREG_2026-09-18.md", "REACTION_R2_PREREG_2026-09-19.md",
                 "REACTION_PREREG_DRAFT_2026-09-18.md"):
        _write(tmp_path, name, PREREG_MD)
    md = "# 結果の読み — 2026-09-19\n\n## 1. 判定\n\n読みは反証である。\n"
    art = _write(tmp_path, "RESULT.md", md)
    assert J.latest_prereg(art, md).name == "REACTION_PREREG_DRAFT_2026-09-18.md"
    # 報告に日付が無ければ全部から名前順の最後
    md2 = "# 結果の読み\n\n## 1. 判定\n\n読みは反証である。\n"
    art2 = _write(tmp_path, "RESULT2.md", md2)
    assert J.latest_prereg(art2, md2).name == "REACTION_R2_PREREG_2026-09-19.md"


def test_purpose_questions_and_violation_direction():
    for kind, qid in [("purpose_vs_quantity", "quantity_measures_purpose"),
                      ("control_vs_quantity", "quantity_confounded_by_start"),
                      ("conclusion_vs_purpose", "conclusion_answers_purpose"),
                      ("other_cause_named", "other_cause_named"),
                      ("direction_supported", "conclusion_direction_supported")]:
        q = J.question_for(kind, {})
        assert list(q) == [qid]
        assert q[qid]["type"] == "noul"
        assert set(q[qid]["criteria"]) == {"true", "false"}
    # 肯定形の問いは「1 - noul」が反する側。交絡の問いだけは true 側がそのまま反する側
    answers = {"quantity_measures_purpose": {"noul": 0.07}}
    assert J.violation_probability("purpose_vs_quantity", answers)[1] == pytest.approx(0.93)
    answers = {"quantity_confounded_by_start": {"noul": 0.75}}
    assert J.violation_probability("control_vs_quantity", answers)[1] == pytest.approx(0.75)
    answers = {"other_cause_named": {"noul": 0.09}}
    assert J.violation_probability("other_cause_named", answers)[1] == pytest.approx(0.91)


def test_purpose_pairs_are_capped(tmp_path):
    # 結論の行は 10 行で切れるので、対 4 は上限 40 に届かない(検収の指示 9)
    _write(tmp_path, "REACTION_DESIGN_2026-09-18.md", DESIGN_INTENT_MD)
    body = "\n".join(f"- {i} 番目の判定は差ありである。" for i in range(60))
    art = _write(tmp_path, "RESULT_many.md", "# 結果の読み\n\n## 1. 判定\n\n" + body + "\n")
    dropped: dict = {}
    pairs = J.extract_purpose_pairs(art.read_text(encoding="utf-8"), art, dropped)
    assert J.MAX_PURPOSE_PAIRS == J.MAX_NEGATIVE_PAIRS == 40
    assert sum(1 for p in pairs if p["kind"] == "other_cause_named") == 10
    assert dropped == {}
    # 集約する種類は「群」の数で切る(群を割らない)
    many = [{"kind": "conclusion_vs_purpose", "anchor": i} for i in range(50) for _ in range(3)]
    cut: dict = {}
    kept = J._capped(many, J.MAX_PURPOSE_PAIRS, cut)
    assert len({p["anchor"] for p in kept}) == 40
    assert len(kept) == 120 and cut["conclusion_vs_purpose"] == 30


def test_summary_line_reports_zero_purpose_pairs(tmp_path, fake_client, capsys):
    art = _write(tmp_path, "plain.md", "# 覚書\n\n板が薄い。\n")
    out = tmp_path / "out"
    assert J.main(["audit", str(art), "--out", str(out), "--summary"]) == 0
    last = capsys.readouterr().out.strip().splitlines()[-1]
    assert "対 0 件" in last
    assert "意図マップ: なし" in last


def test_summary_line_lists_each_purpose_kind(tmp_path, fake_client, capsys):
    _write(tmp_path, "REACTION_DESIGN_2026-09-18.md", DESIGN_INTENT_MD)
    art = _write(tmp_path, "PREREG.md", PREREG_MD)
    out = tmp_path / "out"
    assert J.main(["audit", str(art), "--out", str(out), "--summary"]) == 0
    last = capsys.readouterr().out.strip().splitlines()[-1]
    for kind in J.PURPOSE_KINDS:
        assert kind in last
    assert "報告向けの 3 種は当てない" in last
    summary = _read_jsonl(out / "PREREG.jsonl")[-1]
    assert summary["purpose_pairs"]["purpose_vs_quantity"] == 4
    assert summary["purpose_pairs"]["control_vs_quantity"] == 1
    assert summary["purpose_inputs"]["intent_rows"] == 4


def test_purpose_aggregate_is_a_ranking_without_a_flag(tmp_path, fake_client):
    _write(tmp_path, "REACTION_DESIGN_2026-09-18.md", DESIGN_INTENT_MD)
    art = _write(tmp_path, "PREREG.md", PREREG_MD)
    out = tmp_path / "out"
    assert J.main(["audit", str(art), "--out", str(out)]) == 0
    recs = _read_jsonl(out / "PREREG.jsonl")
    pv = [r for r in recs if r["kind"] == "purpose_vs_quantity"]
    singles = [r for r in pv if not r.get("aggregate")]
    agg = [r for r in pv if r.get("aggregate")]
    assert len(singles) == 4 and all(r["flag"] is False and r["reason"] == "aggregated"
                                     for r in singles)
    # 集約の行は**順位の表示だけ**で印を付けない(検収 2 の追加 1)
    assert len(agg) == 1 and agg[0]["flag"] is False
    assert agg[0]["reason"] == "ranking_only"
    assert "直接測る意図(高い順)" in agg[0]["a"] and "測らない意図(低い順)" in agg[0]["a"]
    assert [x["intent_id"] for x in agg[0]["ranking"]] and len(agg[0]["ranking"]) == 4
    assert "purpose_vs_quantity" not in (recs[-1]["flag_by_kind"] or {})
    assert recs[-1]["purpose_pairs"]["purpose_vs_quantity"] == 4  # 対の数は集約を含まない


def test_ranking_is_on_the_last_line(tmp_path, fake_client, capsys):
    _write(tmp_path, "REACTION_DESIGN_2026-09-18.md", DESIGN_INTENT_MD)
    art = _write(tmp_path, "PREREG.md", PREREG_MD)
    out = tmp_path / "out"
    assert J.main(["audit", str(art), "--out", str(out), "--summary"]) == 0
    last = capsys.readouterr().out.strip().splitlines()[-1]
    assert "直接測る意図(高い順)" in last
    # 順位の行に確率は出さない
    assert "0." not in last.split("直接測る意図", 1)[1]


def test_repeat_kinds_are_sent_three_times_and_averaged(tmp_path, fake_client):
    art = _write(tmp_path, "PREREG.md", PREREG_MD)
    out = tmp_path / "out"
    assert J.REPEATS == 3
    assert J.REPEAT_KINDS == ("control_vs_quantity", "direction_supported",
                              "other_cause_named")
    assert J.main(["audit", str(art), "--out", str(out)]) == 0
    cv = [r for r in _read_jsonl(out / "PREREG.jsonl")
          if r["kind"] == "control_vs_quantity"]
    assert len(cv) == 1
    assert len(cv[0]["repeats"]) == 3
    assert cv[0]["violation_probability"] == pytest.approx(
        sum(cv[0]["repeats"]) / 3, abs=1e-4)
    assert cv[0]["near_threshold"] is False        # 既定は 0.75(= |0.75-0.35| > 0.10)
    n_control = sum(1 for s, _q in fake_client.calls if "control_group" in s)
    assert n_control == 3


def test_near_threshold_band(tmp_path, fake_client):
    assert J.NEAR_BAND == 0.10
    assert J.near_threshold(J.ATTENTION) is True
    assert J.near_threshold(J.ATTENTION + 0.10) is True
    assert J.near_threshold(J.ATTENTION + 0.1001) is False
    art = _write(tmp_path, "PREREG.md", PREREG_MD)
    out = tmp_path / "out"
    fake_client.noul_by_qid = {"quantity_confounded_by_start": 0.40}
    assert J.main(["audit", str(art), "--out", str(out)]) == 0
    recs = _read_jsonl(out / "PREREG.jsonl")
    cv = [r for r in recs if r["kind"] == "control_vs_quantity"][0]
    assert cv["near_threshold"] is True and cv["flag"] is True
    assert recs[-1]["n_near_threshold"] == 1


def test_purpose_state_has_named_fields_only(tmp_path, fake_client):
    _write(tmp_path, "REACTION_DESIGN_2026-09-18.md", DESIGN_INTENT_MD)
    art = _write(tmp_path, "PREREG.md", PREREG_MD)
    out = tmp_path / "out"
    assert J.main(["audit", str(art), "--out", str(out)]) == 0
    sent = [s for s, q in fake_client.calls if "owner_purpose" in s]
    assert sent
    assert all("fragment_a" not in s for s in sent)


# ---------------------------------------------------------------------------
# 今日の実物(設計は同じディレクトリ)
# ---------------------------------------------------------------------------
_PREREG = REPO / "docs/PHASE2/O3C/PRICE_LEVEL/REACTION_PREREG_2026-09-18.md"


@pytest.mark.skipif(not _PREREG.is_file(), reason="実物が無い")
def test_real_prereg_makes_purpose_pairs():
    text = _PREREG.read_text(encoding="utf-8")
    stats: dict = {}
    pairs = J.extract_pairs(text, _PREREG, stats)
    assert stats["purpose_inputs"]["intent_rows"] > 0
    assert stats["purpose_pairs"]["purpose_vs_quantity"] > 0
    assert stats["purpose_pairs"]["control_vs_quantity"] > 0
    assert any("上がりすぎ下がりすぎ" in p["state"]["owner_purpose"]
               for p in pairs if p["kind"] == "purpose_vs_quantity")
