"""`scripts/jev_audit_loop.py`(U9 監査の無限ループの検出)の検査。

この道具は何も判定しない。出すのは「同じ指摘が N 巡続いている」という事実と確率だけで、
**打ち切りの判断は規則(L-200)とリード・オーナーが行う**(オーナー逐語 L-218)。
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

import scripts.jev_audit_loop as L  # noqa: E402


# ---------------------------------------------------------------------------
# 合成した入力(監査役の逐語の形を写したもの)
# ---------------------------------------------------------------------------
ROUND1 = """# 監査(owner-auditor)— 1 巡目

## 監査役の返答(逐語)

> 1. [止める] `docs/X.md:54` — 「19〜48」という数値が `table.csv` と合わない。

> 2. [直す] `docs/Y.md` — 記号 sd が 2 か所で違う意味に使われている。

## 2. 処置
本文。
"""

ROUND2 = """# 監査(owner-auditor)— 2 巡目

## 監査役の返答(逐語)

> 1. [止める] 数値「19〜48」の出所が `table.csv` と一致しない(前の巡で直したはずである)。

> 2. [聞く] 判定区間の日数はどこに書いてあるか。
"""

ROUND3 = """# 監査(owner-auditor)— 3 巡目

## 監査役の返答(逐語)

> 1. [止める] 「19〜48」はまだ `table.csv` と合わない。
"""

EMPTY_ROUND = "# 監査 — 指摘の形が 1 つも無い記録\n\n本文だけ。\n"


def _write(tmp_path: Path, name: str, text: str) -> Path:
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def _rounds(tmp_path: Path) -> list[str]:
    return [str(_write(tmp_path, "a_prereg.md", ROUND1)),
            str(_write(tmp_path, "a_prereg_r2.md", ROUND2)),
            str(_write(tmp_path, "a_prereg_r3.md", ROUND3))]


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


# ---------------------------------------------------------------------------
# 巡の並べ替え
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("name,expected", [
    ("2026-09-18_reaction_prereg.md", 1),
    ("2026-09-18_reaction_prereg_r2.md", 2),
    ("2026-09-18_reaction_prereg_r10.md", 10),
    ("何もついていない.md", 1),
])
def test_r_number_reads_the_suffix(name, expected):
    assert L.r_number(Path(name)) == expected


def test_order_paths_keeps_the_argument_order_by_default_and_says_it_differs():
    # 殻の展開の順(辞書順)。r10 が r2 の前に来る
    given = [Path(f"v/2026-09-18_reaction_prereg{s}.md") for s in ("", "_r10", "_r2")]
    kept, differs = L.order_paths(given, "args")
    assert [p.name for p in kept] == [p.name for p in given]
    assert differs is True


def test_order_paths_sorts_by_the_r_number_when_asked():
    given = [Path(f"v/p{s}.md") for s in ("", "_r10", "_r2")]
    sorted_, differs = L.order_paths(given, "rnumber")
    assert [p.name for p in sorted_] == ["p.md", "p_r2.md", "p_r10.md"]
    assert differs is True


def test_order_paths_reports_no_difference_when_already_in_order():
    given = [Path(f"v/p{s}.md") for s in ("", "_r2", "_r3")]
    _kept, differs = L.order_paths(given, "args")
    assert differs is False


# ---------------------------------------------------------------------------
# 読み込みと state の組み立て
# ---------------------------------------------------------------------------
def test_load_rounds_gives_unique_ids_per_round(tmp_path):
    rounds = L.load_rounds([Path(p) for p in _rounds(tmp_path)])
    assert [r["round"] for r in rounds] == [1, 2, 3]
    assert [len(r["findings"]) for r in rounds] == [2, 2, 1]
    assert [f["id"] for f in rounds[0]["findings"]] == ["r1#1", "r1#2"]
    assert [f["id"] for f in rounds[2]["findings"]] == ["r3#1"]
    assert rounds[0]["findings"][0]["severity"] == "止める"


def test_load_rounds_disambiguates_a_repeated_number(tmp_path):
    doubled = ROUND1 + "\n> 1. [直す] 同じ番号がもう一度出る記録。\n"
    rounds = L.load_rounds([_write(tmp_path, "d.md", doubled)])
    assert [f["id"] for f in rounds[0]["findings"]] == ["r1#1", "r1#2", "r1#1-2"]


def test_state_holds_the_finding_and_the_previous_round_heads(tmp_path):
    rounds = L.load_rounds([Path(p) for p in _rounds(tmp_path)])
    state = L.state_for(rounds[1]["findings"][0], rounds[0]["findings"])
    assert set(state) == {"finding", "previous_findings"}
    assert "19〜48" in state["finding"]
    assert [p["id"] for p in state["previous_findings"]] == ["r1#1", "r1#2"]
    assert all(len(p["text"]) <= L.PREV_HEAD_CHARS for p in state["previous_findings"])
    # 前の巡の本文は先頭 300 字だけ(改行は空白に畳む)
    assert "\n" not in state["previous_findings"][0]["text"]


def test_head_clips_at_300_chars():
    assert L.head("あ" * 400) == "あ" * L.PREV_HEAD_CHARS
    assert L.head("a\nb") == "a b"


def test_questions_list_the_previous_ids_plus_none(tmp_path):
    rounds = L.load_rounds([Path(p) for p in _rounds(tmp_path)])
    qs = L.questions_for(rounds[0]["findings"])
    assert set(qs) == {"same_issue_as", "resolved_then_reopened"}
    assert qs["same_issue_as"]["type"] == "choice"
    assert set(qs["same_issue_as"]["criteria"]) == {"r1#1", "r1#2", "none"}
    assert qs["resolved_then_reopened"]["type"] == "noul"
    assert set(qs["resolved_then_reopened"]["criteria"]) == {"true", "false"}


# ---------------------------------------------------------------------------
# 確信の門
# ---------------------------------------------------------------------------
def test_linked_id_needs_the_confidence():
    ids = {"r1#1", "r1#2"}
    assert L.linked_id("r1#1", 0.95, ids) == ("r1#1", None)
    assert L.linked_id("r1#1", L.SAME_CONFIDENT, ids) == ("r1#1", None)  # ちょうどは通す
    assert L.linked_id("r1#1", L.SAME_CONFIDENT - 0.01, ids)[0] is None
    assert "低確信" in L.linked_id("r1#1", L.SAME_CONFIDENT - 0.01, ids)[1]
    assert L.linked_id("none", 0.99, ids) == (None, None)
    assert L.linked_id("r9#9", 0.99, ids)[0] is None       # 一覧に無い id
    assert L.linked_id(None, 0.99, ids)[0] is None


# ---------------------------------------------------------------------------
# 連鎖の合成(code)
# ---------------------------------------------------------------------------
def _fake_rounds(sizes: list[int]) -> list[dict]:
    return [{"round": k, "file": f"r{k}.md", "path": f"r{k}.md",
             "findings": [{"id": f"r{k}#{i}"} for i in range(1, n + 1)]}
            for k, n in enumerate(sizes, start=1)]


def test_build_chains_counts_consecutive_rounds():
    rounds = _fake_rounds([2, 2, 1])
    links = {"r2#1": "r1#1", "r3#1": "r2#1"}
    streak, chains = L.build_chains(rounds, links)
    assert streak["r1#1"] == 1 and streak["r2#1"] == 2 and streak["r3#1"] == 3
    assert streak["r1#2"] == 1 and streak["r2#2"] == 1
    assert ["r1#1", "r2#1", "r3#1"] in chains
    assert max(len(c) for c in chains) == 3


def test_build_chains_handles_a_branch():
    rounds = _fake_rounds([1, 2])
    links = {"r2#1": "r1#1", "r2#2": "r1#1"}
    _streak, chains = L.build_chains(rounds, links)
    assert sorted(chains) == [["r1#1", "r2#1"], ["r1#1", "r2#2"]]


def test_round_rows_split_same_and_new():
    rounds = _fake_rounds([2, 2])
    links = {"r2#1": "r1#1"}
    streak, _chains = L.build_chains(rounds, links)
    rows = L.round_rows(rounds, links, streak)
    assert (rows[0]["n_same_as_previous"], rows[0]["n_new"]) == (0, 2)
    assert (rows[1]["n_same_as_previous"], rows[1]["n_new"]) == (1, 1)
    assert rows[1]["longest_streak"] == 2


# ---------------------------------------------------------------------------
# 模擬送信
# ---------------------------------------------------------------------------
class _FakeClient:
    calls: list[tuple] = []
    confidence: float = 0.95
    noul: float = 0.9
    choice: str | None = None  # None = 前の巡の 1 件目を選ぶ

    def __init__(self, model=None, **kwargs):
        self.model = model

    def evaluate(self, state, questions):
        _FakeClient.calls.append((state, questions))
        answers = {}
        for qid, spec in questions.items():
            if spec["type"] == "noul":
                answers[qid] = {"type": "noul", "noul": _FakeClient.noul}
            else:
                choice = _FakeClient.choice or state["previous_findings"][0]["id"]
                answers[qid] = {"type": "choice", "choice": choice,
                                "confidence": _FakeClient.confidence,
                                "probabilities": {choice: _FakeClient.confidence}}
        return {"model": "fake", "answers": answers}


@pytest.fixture
def fake_client(monkeypatch):
    _FakeClient.calls = []
    _FakeClient.confidence = 0.95
    _FakeClient.noul = 0.9
    _FakeClient.choice = None
    monkeypatch.setattr(L, "JevClient", _FakeClient)
    return _FakeClient


def test_dry_run_sends_nothing_and_reports_the_expected_requests(tmp_path, fake_client, capsys):
    out = tmp_path / "out"
    assert L.main(["rounds"] + _rounds(tmp_path) + ["--out", str(out), "--dry-run"]) == 0
    assert _FakeClient.calls == []
    summary = _read_jsonl(out / "a_prereg__3rounds.jsonl")[-1]
    assert summary["dry_run"] is True and summary["n_requests"] == 0
    assert summary["n_rounds"] == 3 and summary["n_findings"] == 5
    assert summary["n_requests_expected"] == 3   # 2 巡目 2 件 + 3 巡目 1 件
    assert summary["max_state_chars"] > 0        # 送らなくても大きさは分かる
    text = capsys.readouterr().out
    assert "測っていない" in text and "打ち切りの判断は規則" in text


def test_one_request_per_finding_from_the_second_round(tmp_path, fake_client):
    out = tmp_path / "out"
    assert L.main(["rounds"] + _rounds(tmp_path) + ["--out", str(out)]) == 0
    assert len(_FakeClient.calls) == 3
    # 前の巡だけを渡す(全巡を渡さない)
    state, questions = _FakeClient.calls[-1]
    assert [p["id"] for p in state["previous_findings"]] == ["r2#1", "r2#2"]
    assert "r1#1" not in questions["same_issue_as"]["criteria"]
    recs = _read_jsonl(out / "a_prereg__3rounds.jsonl")
    findings = [r for r in recs if r["kind"] == "finding"]
    assert [r["sent"] for r in findings] == [False, False, True, True, True]
    assert findings[0]["link_note"] == "前の巡が無い"
    assert findings[2]["linked_to"] == "r1#1"
    assert findings[2]["resolved_then_reopened_flag"] is True   # 0.9 >= PRESENCE


def test_chain_and_round_records_are_written(tmp_path, fake_client, capsys):
    out = tmp_path / "out"
    assert L.main(["rounds"] + _rounds(tmp_path) + ["--out", str(out)]) == 0
    recs = _read_jsonl(out / "a_prereg__3rounds.jsonl")
    rows = [r for r in recs if r["kind"] == "round"]
    assert [(r["round"], r["n_same_as_previous"], r["n_new"]) for r in rows] == [
        (1, 0, 2), (2, 2, 0), (3, 1, 0)]
    chains = [r for r in recs if r["kind"] == "chain"]
    assert chains[0]["length"] == 3 and chains[0]["ids"] == ["r1#1", "r2#1", "r3#1"]
    summary = recs[-1]
    assert summary["longest_chain"] == 3 and summary["n_same_in_last_round"] == 1
    text = capsys.readouterr().out
    assert "同じ指摘が 3 巡続いている" in text
    assert "止めるべき" not in text          # 判定の語は出さない(`docs/JEV.md` §4-1)


def test_low_confidence_is_not_counted_as_the_same(tmp_path, fake_client):
    out = tmp_path / "out"
    _FakeClient.confidence = L.SAME_CONFIDENT - 0.01
    assert L.main(["rounds"] + _rounds(tmp_path) + ["--out", str(out)]) == 0
    recs = _read_jsonl(out / "a_prereg__3rounds.jsonl")
    findings = [r for r in recs if r["kind"] == "finding"]
    assert all(r["linked_to"] is None for r in findings)
    # 生の答えは捨てない
    assert findings[2]["same_issue_as"] == "r1#1"
    summary = recs[-1]
    assert summary["n_low_confidence"] == 3 and summary["longest_chain"] == 1


def test_none_breaks_the_chain(tmp_path, fake_client):
    out = tmp_path / "out"
    _FakeClient.choice = "none"
    assert L.main(["rounds"] + _rounds(tmp_path) + ["--out", str(out)]) == 0
    summary = _read_jsonl(out / "a_prereg__3rounds.jsonl")[-1]
    assert summary["n_linked"] == 0 and summary["n_low_confidence"] == 0
    assert summary["longest_chain"] == 1 and summary["n_chains_2_or_more"] == 0


def test_a_round_with_no_findings_sends_nothing_for_the_next_round(tmp_path, fake_client):
    out = tmp_path / "out"
    paths = [str(_write(tmp_path, "b.md", EMPTY_ROUND)),
             str(_write(tmp_path, "b_r2.md", ROUND2))]
    assert L.main(["rounds"] + paths + ["--out", str(out)]) == 0
    assert _FakeClient.calls == []
    recs = _read_jsonl(out / "b__2rounds.jsonl")
    findings = [r for r in recs if r["kind"] == "finding"]
    assert all(r["link_note"] == "前の巡に指摘が 1 件も無い" for r in findings)
    assert recs[-1]["n_requests_expected"] == 0


def test_missing_file_exits_1(tmp_path, fake_client, capsys):
    assert L.main(["rounds", str(tmp_path / "無い.md")]) == 1
    assert "ファイルが無い" in capsys.readouterr().err


def test_summary_flag_prints_one_line(tmp_path, fake_client, capsys):
    out = tmp_path / "out"
    assert L.main(["rounds"] + _rounds(tmp_path)
                  + ["--out", str(out), "--dry-run", "--summary"]) == 0
    lines = [l for l in capsys.readouterr().out.splitlines() if l.strip()]
    assert len(lines) == 1 and "1 件も送っていない" in lines[0]
    assert lines[0].startswith("巡 3、指摘 5 件")


def test_unreachable_is_reported_and_exits_0(tmp_path, monkeypatch, capsys):
    class _Dead:
        def __init__(self, model=None, **kwargs):
            raise L.JevError("鍵が無い")

    monkeypatch.setattr(L, "JevClient", _Dead)
    out = tmp_path / "out"
    assert L.main(["rounds"] + _rounds(tmp_path) + ["--out", str(out), "--summary"]) == 0
    line = capsys.readouterr().out.strip()
    assert line.startswith("jev: 未到達(")   # 沈黙を「異常なし」と読ませない(§4-9)
    assert _read_jsonl(out / "a_prereg__3rounds.jsonl")[-1]["unreachable"] == "鍵が無い"


def test_redaction_failure_stops_the_send(tmp_path, monkeypatch, fake_client, capsys):
    def _boom(state):
        raise L.RedactionError("鍵らしき文字列")

    monkeypatch.setattr(L, "clean_state", _boom)
    out = tmp_path / "out"
    assert L.main(["rounds"] + _rounds(tmp_path) + ["--out", str(out)]) == 0
    assert _FakeClient.calls == []
    summary = _read_jsonl(out / "a_prereg__3rounds.jsonl")[-1]
    assert summary["n_requests"] == 0
    assert "送っていない" in summary["unreachable"]


# ---------------------------------------------------------------------------
# 実物(送らない。切り出しの件数だけ)
# ---------------------------------------------------------------------------
def test_the_real_ten_rounds_are_ordered_and_counted():
    paths = sorted((REPO / "docs" / "AUDITOR" / "VERDICTS").glob(
        "2026-09-18_reaction_prereg*.md"))
    ordered, differs = L.order_paths(paths, "rnumber")
    assert differs is True   # 辞書順では r10 が r2 の前に来る
    assert [p.name for p in ordered][:3] == ["2026-09-18_reaction_prereg.md",
                                             "2026-09-18_reaction_prereg_r2.md",
                                             "2026-09-18_reaction_prereg_r3.md"]
    rounds = L.load_rounds(ordered)
    assert [len(r["findings"]) for r in rounds] == [25, 23, 23, 22, 19, 18, 20, 19, 20, 18]
