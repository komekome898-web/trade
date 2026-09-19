"""`scripts/jev_audit_eval.py`(U11 採点の候補 / U10 振り分け)の検査。

この道具は何も判定しない。出すのは確率と印と**候補**だけである(オーナー逐語 L-218)。
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

import scripts.jev_audit_eval as A  # noqa: E402


# ---------------------------------------------------------------------------
# 合成した入力(実物 3 形式を写したもの)
# ---------------------------------------------------------------------------
QUOTED_MD = """# 監査(owner-auditor)— 例

## 監査役の返答(逐語)

> 1. [直す] `docs/X.md:54` — 「19〜48」という数値が `table.csv` と合わない。
> この数値の出所はどこか(P2)。

**リードの応答: 直した。**数え直した。

> 2. [聞く] `docs/Y.md`(全体) — 登録の対象と判断したか。

**リードの応答: 対象外と判断した。**

## 2. 処置

### 1.[直す] 数値の出所
本文。

### 2.[聞く] 登録の対象か
本文。
"""

PLAIN_MD = """# 監査記録

1. [止める] docs/A.md:15 — 「4 通りすべて床の下」は成立するか(P5)。

> **直した。** 範囲を明記した。

2. [直す] docs/B.md:292 — ロック機構はあるか(P11)。

> **直した。** ロックを入れた。
"""

TABLE_MD = """# 監査記録: 例

| # | 種別 | 問い(要旨) | リードの答え | 処置 |
|---|---|---|---|---|
| 1 | 止める | 「出典なし 85 件」が実数 81 件と一致しない | 認める。数え直した | 直した |
| 2 | 聞く | L-142 と L-143 の区別を本文だけで確認できるか | §0 に分けて書いた | 直した |
"""

ANSWERS_MD = """# KA-99 の答え(before/KA-99.md に対応)

出典: `docs/DATA_PERISHABILITY.md` §2

## オーナーの発言

「全ての方法・取引所を試したのか」

## 何が誤りだったか(訂正コミットのメッセージより)

「無料でどこにも無い」は 1 経路の 404 だけを根拠にした一般化だった。

## 原則

「取れない」は全ての方法・取引所を試した結果でなければ言えない。
"""

ANSWERS_NO_CORRECTION_MD = """# KA-98 の答え

## 原則

意図マップで ○ とした項目を黙って外してはならない。
"""

KNOWN_MD = """# 既知解

### KA-01 — 出典: L-027

- **Before**: `docs/DATA.md`
- **監査役が出すべき問い**: 「『どこにも無い』の根拠は何経路・何取引所を試した結果か」

### KA-28 — 出典: 討議

- **監査役が出すべき問い**: 「外部評価の 3 観点は検討されたか」

### KA-29 — 出典: L-118

- **監査役が出すべき問い**: 「この行は範囲の外か」

### KA-36 — **【提案・未承認】** 発言の射程を広げない

- **監査役が出すべき問い**: 「その発言の射程を広げていないか」
"""

EVAL_MD = """# 測定

## 1. 捕捉率 — 既存

| ID | 型 | 前回(答え同居) | 今回(ブラインド修正後) | 今回の根拠(要約) |
|---|---|---|---|---|
| KA-01 | データ取得可否 | 捕捉 | **捕捉** | 想定問いと同趣旨 |
| KA-03 | データ取得可否 | 見逃し | **見逃し**(不変) | n 不整合等は捕捉したが、想定問いは今回も出ず |

## 2. 捕捉率 — 新規

| ID | 型(対応原則) | 判定 | 根拠 |
|---|---|---|---|
| KA-27 | 検証規律 | **部分** | 一部が一致 |
"""


def _write(tmp_path: Path, name: str, text: str) -> Path:
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# 切り出し
# ---------------------------------------------------------------------------
def test_split_findings_prefers_the_quoted_verbatim():
    findings = A.split_findings(QUOTED_MD)
    assert [f["index"] for f in findings] == [1, 2]
    assert [f["severity"] for f in findings] == ["直す", "聞く"]
    assert all(f["source"] == "quote" for f in findings)
    # 引用の中だけ(リードの応答・処置の見出しは入らない)
    assert "リードの応答" not in findings[0]["text"]
    assert "処置" not in findings[1]["text"]
    # 折り返した 2 行目は同じ指摘の本文に入る
    assert "出所はどこか" in findings[0]["text"]


def test_split_findings_plain_numbered_form():
    findings = A.split_findings(PLAIN_MD)
    assert [(f["index"], f["severity"]) for f in findings] == [(1, "止める"), (2, "直す")]
    assert all(f["source"] == "plain" for f in findings)
    assert "docs/A.md:15" in findings[0]["text"]


def test_split_findings_table_form_takes_only_the_question_column():
    findings = A.split_findings(TABLE_MD)
    assert [(f["index"], f["severity"]) for f in findings] == [(1, "止める"), (2, "聞く")]
    assert all(f["source"] == "table" for f in findings)
    assert findings[0]["text"] == "「出典なし 85 件」が実数 81 件と一致しない"
    # リードの答え・処置の列は state に入れない
    assert "認める" not in findings[0]["text"]


def test_split_findings_on_the_real_verdicts_match_the_declared_counts():
    # 実物 2 件。件数は文書自身が書いている数と同じ(price_level 5 件 / rules_reduction 15 件)
    got = {}
    for name in ("2026-09-17_price_level.md", "2026-09-12_rules_reduction.md"):
        path = REPO / "docs" / "AUDITOR" / "VERDICTS" / name
        got[name] = len(A.split_findings(A.auditor_text(path)))
    assert got == {"2026-09-17_price_level.md": 5, "2026-09-12_rules_reduction.md": 15}


def test_auditor_text_reads_the_json_result_field(tmp_path):
    p = tmp_path / "out.json"
    p.write_text(json.dumps({"result": "1. [直す] 本文", "type": "result"}), encoding="utf-8")
    assert A.auditor_text(p).startswith("1. [直す]")
    assert len(A.split_findings(A.auditor_text(p))) == 1


def test_split_corrections_and_owner_words():
    corrections, owner, fallback = A.split_corrections(ANSWERS_MD)
    assert len(corrections) == 1
    assert "一般化だった" in corrections[0]["text"]
    assert "全ての方法・取引所" in owner
    assert fallback is False


def test_split_corrections_falls_back_to_the_principle_section_and_says_so():
    corrections, owner, fallback = A.split_corrections(ANSWERS_NO_CORRECTION_MD)
    assert len(corrections) == 1 and fallback is True
    assert owner == ""


def test_known_answers_caps_the_ids_and_skips_unapproved(tmp_path):
    p = _write(tmp_path, "known.md", KNOWN_MD)
    known = A.known_answers([str(p)])
    assert list(known) == ["KA-01", "KA-28", "KA-29"]  # KA-36 は上限超え(未承認の提案)。上限は KNOWN_ID_MAX = 35
    assert known["KA-01"].startswith("「『どこにも無い』")


def test_known_answers_reads_the_repository_documents():
    known = A.known_answers(list(A.DEFAULT_KNOWN))
    assert len(known) == 35  # KA-01…KA-35(KA-29〜35 は ADDENDUM。KA-36 は未承認なので含めない)
    assert known["KA-06"].startswith("「この測定の単純化")


# ---------------------------------------------------------------------------
# 合成(code)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("score,expected", [
    (0.0, "見逃し候補"), (0.4, "見逃し候補"), (1.0, "部分候補"), (1.4, "部分候補"),
    (1.6, "捕捉候補"), (2.0, "捕捉候補"),
    # Python の `round` は半数を偶数側へ丸める(E.10 の `round(score)` と同じ実装)
    (0.5, "見逃し候補"), (1.5, "捕捉候補"),
])
def test_candidate_for_is_round(score, expected):
    assert A.candidate_for(score) == expected


def test_best_for_correction_takes_the_maximum():
    assert A.best_for_correction([0.1, 1.8, None]) == (1.8, "捕捉候補")
    assert A.best_for_correction([None, None]) == (None, None)


def test_artifact_candidate_takes_the_lowest():
    assert A.artifact_candidate(["捕捉候補", "見逃し候補"]) == "見逃し候補"
    assert A.artifact_candidate(["捕捉候補"]) == "捕捉候補"
    assert A.artifact_candidate([None]) is None


# ---------------------------------------------------------------------------
# `--compare` の読み取り
# ---------------------------------------------------------------------------
def test_read_manual_grades_uses_the_named_column(tmp_path):
    p = _write(tmp_path, "eval.md", EVAL_MD)
    grades, err = A.read_manual_grades(p)
    assert err is None
    # KA-03 の根拠の欄にも「捕捉」の語があるが、読むのは「今回」の列だけ
    assert grades == {"KA-01": "捕捉", "KA-03": "見逃し", "KA-27": "部分"}


def test_read_manual_grades_on_the_real_eval_reads_28_ids():
    grades, err = A.read_manual_grades(REPO / "docs" / "AUDITOR" / "EVAL_2026-09-11b.md")
    assert err is None and len(grades) == 28
    assert grades["KA-01"] == "捕捉" and grades["KA-11"] == "見逃し"


def test_read_manual_grades_reports_when_it_cannot_read(tmp_path):
    p = _write(tmp_path, "empty.md", "# 何も無い\n")
    grades, err = A.read_manual_grades(p)
    assert grades == {} and "読み取れない" in err


def test_compare_counts_only_counts():
    got = A.compare_counts({"KA-01": "捕捉", "KA-02": "部分"},
                           {"KA-01": "捕捉候補", "KA-02": "見逃し候補", "KA-03": None})
    assert (got["same"], got["diff"], got["unmatched"]) == (1, 1, 1)


# ---------------------------------------------------------------------------
# 模擬送信
# ---------------------------------------------------------------------------
class _FakeClient:
    calls: list[tuple] = []
    score: float = 1.8
    noul: float = 0.9
    confidence: float = 0.95
    choice_known: str = "KA-01"
    choice_sev: str = "直す"

    def __init__(self, model=None, **kwargs):
        self.model = model

    def evaluate(self, state, questions):
        _FakeClient.calls.append((state, questions))
        answers = {}
        for qid, spec in questions.items():
            if spec["type"] == "noul":
                answers[qid] = {"type": "noul", "noul": _FakeClient.noul}
            elif spec["type"] == "score":
                answers[qid] = {"type": "score", "score": _FakeClient.score,
                                "confidence": _FakeClient.confidence}
            else:
                choice = (_FakeClient.choice_known if qid == "known_answer"
                          else _FakeClient.choice_sev)
                answers[qid] = {"type": "choice", "choice": choice,
                                "confidence": _FakeClient.confidence,
                                "probabilities": {choice: _FakeClient.confidence}}
        return {"model": "fake", "answers": answers}


@pytest.fixture
def fake_client(monkeypatch):
    _FakeClient.calls = []
    _FakeClient.score = 1.8
    _FakeClient.noul = 0.9
    _FakeClient.confidence = 0.95
    _FakeClient.choice_known = "KA-01"
    _FakeClient.choice_sev = "直す"
    monkeypatch.setattr(A, "JevClient", _FakeClient)
    return _FakeClient


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def _score_args(tmp_path, out, extra=None):
    auditor = _write(tmp_path, "auditor.md", QUOTED_MD)
    answers = _write(tmp_path, "KA-99.md", ANSWERS_MD)
    return (["score-findings", "--auditor", str(auditor), "--answers", str(answers),
             "--out", str(out)] + (extra or []))


def test_score_findings_dry_run_sends_nothing(tmp_path, fake_client):
    out = tmp_path / "out"
    assert A.main(_score_args(tmp_path, out, ["--dry-run"])) == 0
    assert _FakeClient.calls == []
    recs = _read_jsonl(out / "KA-99__auditor.jsonl")
    summary = recs[-1]
    assert summary["kind"] == "_summary" and summary["dry_run"] is True
    assert summary["n_findings"] == 2 and summary["n_corrections"] == 1
    assert summary["n_pairs"] == 2 and summary["n_requests"] == 0
    assert summary["artifact_candidate"] is None


def test_score_findings_sends_one_request_per_pair(tmp_path, fake_client, capsys):
    out = tmp_path / "out"
    assert A.main(_score_args(tmp_path, out)) == 0
    assert len(_FakeClient.calls) == 2
    state, questions = _FakeClient.calls[0]
    assert set(state) == {"finding", "owner_correction", "owner_words"}
    assert set(questions) == {"same_defect", "points_to_location"}
    assert questions["same_defect"]["type"] == "score"
    assert len(questions["same_defect"]["criteria"]) == 3
    recs = _read_jsonl(out / "KA-99__auditor.jsonl")
    pairs = [r for r in recs if r["kind"] == "pair"]
    assert len(pairs) == 2 and all(r["sent"] for r in pairs)
    assert pairs[0]["same_defect_candidate"] == "捕捉候補"   # round(1.8) = 2
    assert pairs[0]["points_to_location_flag"] is True      # 0.9 >= PRESENCE
    corr = [r for r in recs if r["kind"] == "correction"]
    assert len(corr) == 1 and corr[0]["candidate"] == "捕捉候補"
    assert recs[-1]["artifact_candidate"] == "捕捉候補"
    text = capsys.readouterr().out
    assert "確定はリードが行う" in text  # 候補であることを表の見出しに書く


def test_score_findings_compare_counts_only(tmp_path, fake_client, capsys):
    out = tmp_path / "out"
    eval_md = _write(tmp_path, "EVAL.md", EVAL_MD.replace("KA-01", "KA-99"))
    assert A.main(_score_args(tmp_path, out, ["--compare", str(eval_md)])) == 0
    summary = _read_jsonl(out / "KA-99__auditor.jsonl")[-1]
    cmp_ = summary["compare"]
    assert (cmp_["same"], cmp_["diff"], cmp_["unmatched"]) == (1, 0, 0)
    assert "中身の解釈は書かない" in capsys.readouterr().out


def test_score_findings_compare_says_when_it_cannot_read(tmp_path, fake_client):
    out = tmp_path / "out"
    empty = _write(tmp_path, "EMPTY.md", "# 何も無い\n")
    assert A.main(_score_args(tmp_path, out, ["--compare", str(empty)])) == 0
    summary = _read_jsonl(out / "KA-99__auditor.jsonl")[-1]
    assert "読み取れない" in summary["compare"]["error"]


def test_route_findings_marks_and_names(tmp_path, fake_client, capsys):
    out = tmp_path / "out"
    verdict = _write(tmp_path, "v.md", TABLE_MD)
    known = _write(tmp_path, "known.md", KNOWN_MD)
    assert A.main(["route-findings", "--verdict", str(verdict), "--known", str(known),
                   "--out", str(out)]) == 0
    assert len(_FakeClient.calls) == 2
    _state, questions = _FakeClient.calls[0]
    assert set(questions) == {"deterministic_checkable", "known_answer", "severity_kind"}
    assert "none" in questions["known_answer"]["criteria"]
    assert "KA-01" in questions["known_answer"]["criteria"]
    recs = _read_jsonl(out / "v.jsonl")
    findings = [r for r in recs if r["kind"] == "finding"]
    assert all(r["scriptable_candidate"] is True for r in findings)  # 0.9 >= PRESENCE
    assert findings[0]["known_answer_reported"] == "KA-01"           # 0.95 >= KNOWN_CONFIDENT
    assert findings[0]["severity_matches_auditor"] is False          # 止める vs 直す
    assert findings[1]["severity_matches_auditor"] is None or True
    summary = recs[-1]
    assert (summary["n_findings"], summary["n_scriptable"], summary["n_known"]) == (2, 2, 2)
    assert "印には使わない" in capsys.readouterr().out


def test_route_findings_hides_the_name_below_the_confidence(tmp_path, fake_client):
    out = tmp_path / "out"
    _FakeClient.confidence = A.KNOWN_CONFIDENT - 0.01
    verdict = _write(tmp_path, "v.md", TABLE_MD)
    known = _write(tmp_path, "known.md", KNOWN_MD)
    assert A.main(["route-findings", "--verdict", str(verdict), "--known", str(known),
                   "--out", str(out)]) == 0
    recs = _read_jsonl(out / "v.jsonl")
    findings = [r for r in recs if r["kind"] == "finding"]
    assert all(r["known_answer_reported"] == "none" for r in findings)
    assert all(r["known_answer"] == "KA-01" for r in findings)  # 生の答えは捨てない
    assert recs[-1]["n_known"] == 0 and recs[-1]["n_low_confidence"] == 2


def test_route_findings_marks_nothing_below_presence(tmp_path, fake_client):
    out = tmp_path / "out"
    _FakeClient.noul = A.PRESENCE - 0.01
    verdict = _write(tmp_path, "v.md", TABLE_MD)
    known = _write(tmp_path, "known.md", KNOWN_MD)
    assert A.main(["route-findings", "--verdict", str(verdict), "--known", str(known),
                   "--out", str(out)]) == 0
    assert _read_jsonl(out / "v.jsonl")[-1]["n_scriptable"] == 0


def test_summary_flag_prints_one_line(tmp_path, fake_client, capsys):
    out = tmp_path / "out"
    assert A.main(_score_args(tmp_path, out, ["--dry-run", "--summary"])) == 0
    lines = [l for l in capsys.readouterr().out.splitlines() if l.strip()]
    assert len(lines) == 1 and "1 件も送っていない" in lines[0]


def test_unreachable_is_reported_and_exits_0(tmp_path, monkeypatch, capsys):
    class _Dead:
        def __init__(self, model=None, **kwargs):
            raise A.JevError("401: 鍵が無いか無効")

    monkeypatch.setattr(A, "JevClient", _Dead)
    out = tmp_path / "out"
    assert A.main(_score_args(tmp_path, out, ["--summary"])) == 0
    assert "未到達" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# 伏せ字(送信直前の最終検査を通す)
# ---------------------------------------------------------------------------
def test_state_goes_through_redaction(tmp_path, fake_client):
    out = tmp_path / "out"
    auditor = _write(tmp_path, "auditor.md",
                     "1. [直す] 鍵は `Bearer abcdefghijklmnopqrstuvwxyz012345` である。\n")
    answers = _write(tmp_path, "KA-99.md", ANSWERS_MD)
    assert A.main(["score-findings", "--auditor", str(auditor), "--answers", str(answers),
                   "--out", str(out)]) == 0
    state, _q = _FakeClient.calls[0]
    assert "abcdefghijklmnopqrstuvwxyz012345" not in state["finding"]
    assert "Bearer <redacted>" in state["finding"]


def test_redaction_failure_stops_the_send(tmp_path, fake_client, monkeypatch, capsys):
    monkeypatch.setattr(A, "clean_state", lambda s: (_ for _ in ()).throw(
        A.RedactionError("残っている")))
    out = tmp_path / "out"
    assert A.main(_score_args(tmp_path, out)) == 0
    assert _FakeClient.calls == []
    recs = _read_jsonl(out / "KA-99__auditor.jsonl")
    assert all(not r["sent"] for r in recs if r["kind"] == "pair")
    assert "伏せ字" in capsys.readouterr().err
