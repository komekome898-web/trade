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


def test_questions_are_one_per_kind():
    assert list(J.question_for("negative_claim", {})) == ["scope_and_method_attached"]
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

    def evaluate(self, state, questions):
        _FakeClient.calls.append((state, questions))
        qid = next(iter(questions))
        if questions[qid]["type"] == "noul":
            return {"model": "fake", "answers": {qid: {"type": "noul", "noul": 0.1}}}
        return {"model": "fake", "answers": {qid: {
            "type": "choice", "choice": "contradicts",
            "probabilities": {"consistent": 0.1, "contradicts": 0.85, "unrelated": 0.05},
        }}}


@pytest.fixture
def fake_client(monkeypatch):
    _FakeClient.calls = []
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
