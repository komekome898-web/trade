"""`scripts/jev_delegate.py` の抽出・保護パスの判定・段の合成・`calibrate` の抜き出しを検査する。

この道具は段を**選ばない**。出すのは確率と段の候補と印だけで、判断はリードとオーナーである
(オーナー逐語 L-218、`docs/JEV.md` §8 U8)。

ネットワークには一切触れない(`JevClient` を差し替えるか `--dry-run` を通す)。
固有の製品名はこのファイルにも書かない(`config/jev_delegation_tiers.yaml` から読む)。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import scripts.jev_delegate as D  # noqa: E402


# ---------------------------------------------------------------------------
# 合成した委任文
# ---------------------------------------------------------------------------
IMPLEMENTATION_PROMPT = """あなたは本リポジトリの実装エージェントです。出力は日本語。
Do not commit. Do not push。`src/bot/` に触れない。

【読了必須】docs/JEV.md、scripts/jev_check.py、config/jev_routes.yaml。

## 作るもの `scripts/nowhere_at_all.py`

【必須報告】
1. ファイルと行数
2. 実行コマンドと出力
3. テストの末尾行
"""

LOOSE_PROMPT = """委任の道具のあたりを見て、良さそうなら直しておいてください。
"""

PROTECTED_PROMPT = """.claude/hooks/deny_protected_paths.sh と settings.json を直してください。
"""


def _write(tmp_path: Path, name: str, text: str) -> Path:
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


# ---------------------------------------------------------------------------
# パスの抽出と state(すべて code)
# ---------------------------------------------------------------------------
def test_extract_paths_finds_relative_absolute_and_directories():
    paths = D.extract_paths(
        "docs/JEV.md と scripts/jev_check.py を読み、/home/user/trade の src/bot/ に触れない。"
    )
    assert "docs/JEV.md" in paths
    assert "scripts/jev_check.py" in paths
    assert "src/bot/" in paths
    assert "/home/user/trade" in paths


def test_extract_paths_skips_urls_and_numbers():
    paths = D.extract_paths("出典 https://docs.typesafe.ai/cookbooks/function_calling、割合 3/4。")
    assert not any(p.startswith("http") for p in paths)
    assert "3/4" not in paths


def test_extract_paths_is_deduplicated_and_ordered():
    paths = D.extract_paths("docs/JEV.md を読み、もう一度 docs/JEV.md を読む。config/a.yaml も。")
    assert paths.count("docs/JEV.md") == 1
    assert paths.index("docs/JEV.md") < paths.index("config/a.yaml")


def test_file_entry_counts_lines_of_existing_files():
    entry = D.file_entry("docs/JEV.md")
    assert entry["exists"] is True
    assert entry["lines"] > 0
    missing = D.file_entry("docs/this_file_does_not_exist_nowhere.md")
    assert missing["exists"] is False and missing["lines"] == 0


def test_build_state_has_exactly_the_specified_keys():
    state = D.build_state(IMPLEMENTATION_PROMPT)
    assert set(state) == {"task_text", "files_named", "n_files", "total_lines",
                          "touches_protected", "required_outputs", "has_stop_condition"}
    assert state["n_files"] == len(state["files_named"])
    assert state["total_lines"] == sum(f["lines"] for f in state["files_named"])


def test_task_text_is_capped():
    state = D.build_state("あ" * (D.MAX_TASK_CHARS + 500))
    assert len(state["task_text"]) == D.MAX_TASK_CHARS


def test_touches_protected_is_a_code_boolean():
    assert D.build_state(PROTECTED_PROMPT)["touches_protected"] is True
    assert D.build_state(IMPLEMENTATION_PROMPT)["touches_protected"] is True  # src/bot/
    assert D.build_state("docs/JEV.md を読む。")["touches_protected"] is False


@pytest.mark.parametrize("path, expected", [
    (".claude/hooks/x.sh", True),
    ("githooks/pre-push", True),
    ("config/risk_limits.yaml", True),
    ("src/bot/settings.py", True),
    ("settings.json", True),
    ("src/bot_helpers/x.py", False),
    ("docs/DELEGATION.md", False),
])
def test_protected_paths_one_by_one(path, expected):
    assert bool(D.PROTECTED_RE.search(path)) is expected


def test_required_outputs_counts_numbered_items():
    assert D.count_required_outputs(IMPLEMENTATION_PROMPT) == 3
    inline = "報告: (1) ファイルと行数、(2) 実行コマンド、(3) テストの末尾行、(4) 対応表。"
    assert D.count_required_outputs(inline) == 4
    assert D.count_required_outputs("好きにやってください。") == 0


def test_required_outputs_stops_at_the_next_bracket_heading():
    text = "【必須報告】\n1. あ\n2. い\n\n【制約】\n1. う\n2. え\n3. お\n"
    assert D.count_required_outputs(text) == 2


def test_has_stop_condition():
    assert D.build_state(IMPLEMENTATION_PROMPT)["has_stop_condition"] is True
    assert D.build_state("実送信はしない。")["has_stop_condition"] is True
    assert D.build_state(LOOSE_PROMPT)["has_stop_condition"] is False


# ---------------------------------------------------------------------------
# 問い(1 判断 1 問・肯定形・criteria は具体例つき)
# ---------------------------------------------------------------------------
def test_questions_shape():
    qs = D.questions()
    assert set(qs) == {"task_kind", "needs_cross_file_reasoning", "is_mechanical",
                       "needs_owner_approval", "is_bounded"}
    assert qs["task_kind"]["type"] == "choice"
    assert set(qs["task_kind"]["criteria"]) == {
        "implementation", "measurement_or_execution", "extraction_or_inventory",
        "judgment_or_design", "writing", "other"}
    for qid, spec in qs.items():
        if spec["type"] == "noul":
            assert set(spec["criteria"]) == {"true", "false"}
        for text in spec["criteria"].values():
            assert "Example" in text, f"{qid} の criteria に具体例が無い"


STOP_WORDS = ("止める", "通す", "合格", "却下", "採用")


def test_no_stop_or_pass_words_in_the_labels():
    """「止める / 通す」の語を出力に置かない(`docs/JEV.md` §4-1)。"""
    cfg = D.load_tiers()
    labels = [t["label"] for t in cfg["tiers"].values()]
    labels += [t.get("model_tier") or "" for t in cfg["tiers"].values()]
    labels += [m["label"] for m in cfg["marks"]]
    for label in labels:
        for word in STOP_WORDS:
            assert word not in label, (label, word)


# ---------------------------------------------------------------------------
# 段の表(config)
# ---------------------------------------------------------------------------
def test_config_threshold_matches_the_constant():
    cfg = D.load_tiers()
    assert cfg["thresholds"]["kind_confident"] == D.KIND_CONFIDENT


def test_config_rules_and_marks_point_at_existing_tiers():
    cfg = D.load_tiers()
    for rule in cfg["rules"]:
        assert rule["tier"] in cfg["tiers"]
    assert cfg["default_tier"] in cfg["tiers"]
    for tier in cfg["tiers"].values():
        assert tier["compares_as"] in cfg["tiers"]
    for tier_id in cfg["model_to_tier"].values():
        assert tier_id in cfg["tiers"]


def test_product_names_live_only_in_the_config():
    """固有の製品名はスクリプトにもテストにも書かない(段の名前は config の語で出す)。"""
    cfg = D.load_tiers()
    names = {str(t["model"]) for t in cfg["tiers"].values() if t.get("model")}
    names |= set(cfg["model_to_tier"])
    assert names, "config に製品名が 1 つも無い"
    for path in (REPO / "scripts" / "jev_delegate.py", Path(__file__)):
        source = path.read_text(encoding="utf-8")
        for name in names:
            assert name not in source, f"{path.name} に製品名 {name} が書かれている"


# ---------------------------------------------------------------------------
# 合成の分岐(段の候補)
# ---------------------------------------------------------------------------
def _answers(kind: str, confidence: float = 0.95, *, mechanical: float = 0.0,
             approval: float = 0.0, bounded: float = 1.0, cross: float = 0.5) -> dict:
    probs = {k: 0.0 for k in D.questions()["task_kind"]["criteria"]}
    probs[kind] = 0.9
    return {
        "task_kind": {"type": "choice", "choice": kind, "probabilities": probs,
                      "confidence": confidence},
        "needs_cross_file_reasoning": {"type": "noul", "noul": cross},
        "is_mechanical": {"type": "noul", "noul": mechanical},
        "needs_owner_approval": {"type": "noul", "noul": approval},
        "is_bounded": {"type": "noul", "noul": bounded},
    }


@pytest.mark.parametrize("kind, tier_id", [
    ("judgment_or_design", "no_delegation"),
    ("implementation", "implementation"),
    ("measurement_or_execution", "work"),
    ("extraction_or_inventory", "work"),
    ("writing", "work"),
    ("other", "coarse"),
])
def test_tier_branches_by_kind(kind, tier_id):
    cfg = D.load_tiers()
    rec = D.decide_tier(_answers(kind), cfg)
    assert rec["tier_id"] == tier_id
    assert rec["tier_label"] == cfg["tiers"][tier_id]["label"]


def test_mechanical_wins_over_the_kind_rules_except_judgment():
    cfg = D.load_tiers()
    assert D.decide_tier(_answers("implementation", mechanical=D.PRESENCE),
                         cfg)["tier_id"] == "no_model"
    # 規則は上から順。判断は `is_mechanical` より先に当たる。
    assert D.decide_tier(_answers("judgment_or_design", mechanical=0.99),
                         cfg)["tier_id"] == "no_delegation"


def test_mechanical_threshold_boundary():
    cfg = D.load_tiers()
    assert D.decide_tier(_answers("writing", mechanical=D.PRESENCE),
                         cfg)["tier_id"] == "no_model"
    assert D.decide_tier(_answers("writing", mechanical=D.PRESENCE - 0.01),
                         cfg)["tier_id"] == "work"


def test_low_confidence_falls_back_to_the_coarse_answer():
    """確信度が足りないときは細かい段を名指ししない(資料 E.16)。"""
    cfg = D.load_tiers()
    on = D.decide_tier(_answers("implementation", confidence=D.KIND_CONFIDENT), cfg)
    assert on["tier_id"] == "implementation" and on["kind_confident"] is True
    off = D.decide_tier(_answers("implementation", confidence=D.KIND_CONFIDENT - 0.01), cfg)
    assert off["tier_id"] == cfg["default_tier"] and off["kind_confident"] is False
    # 粗い答えでも、一致を数えるときは作業の段と同じものとして扱う
    assert D.compares_as("coarse", cfg) == D.compares_as("work", cfg)


def test_marks_are_separate_from_the_tier():
    cfg = D.load_tiers()
    labels = {m["id"]: m["label"] for m in cfg["marks"]}
    rec = D.combine(_answers("implementation", approval=D.PRESENCE, bounded=0.0), cfg)
    assert rec["tier_id"] == "implementation"
    assert set(rec["mark_labels"]) == {labels["needs_owner_approval"], labels["not_bounded"]}
    assert rec["flag"] is True
    clean = D.combine(_answers("implementation", approval=D.PRESENCE - 0.01, bounded=1.0), cfg)
    assert clean["mark_labels"] == [] and clean["flag"] is False


def test_mark_boundaries():
    cfg = D.load_tiers()
    ids = lambda rec: {m["id"] for m in rec["marks"]}  # noqa: E731
    assert "needs_owner_approval" in ids(D.combine(_answers("writing", approval=D.PRESENCE), cfg))
    # 「完了の形が無い」は反する側(1 - is_bounded)がしきい値以上のとき
    assert "not_bounded" in ids(D.combine(_answers("writing", bounded=1.0 - D.ATTENTION), cfg))
    assert "not_bounded" not in ids(
        D.combine(_answers("writing", bounded=1.0 - D.ATTENTION + 0.01), cfg))


def test_mark_records_the_side_that_triggered_it():
    """「反する側」で付いた印には 1 - noul を載せる(`docs/JEV.md` §4-3)。"""
    cfg = D.load_tiers()
    rec = D.combine(_answers("writing", approval=0.8, bounded=0.2), cfg)
    by_id = {m["id"]: m for m in rec["marks"]}
    assert by_id["needs_owner_approval"]["probability"] == pytest.approx(0.8)
    assert by_id["not_bounded"]["probability"] == pytest.approx(0.8)
    assert by_id["not_bounded"]["question"] == "is_bounded"


def test_combine_keeps_every_noul_probability():
    cfg = D.load_tiers()
    rec = D.combine(_answers("writing", mechanical=0.2, approval=0.3, bounded=0.4, cross=0.6), cfg)
    assert rec["nouls"] == {"needs_cross_file_reasoning": 0.6, "is_mechanical": 0.2,
                            "needs_owner_approval": 0.3, "is_bounded": 0.4}


# ---------------------------------------------------------------------------
# calibrate の抜き出し
# ---------------------------------------------------------------------------
def _transcript(tmp_path: Path, models: list[str]) -> Path:
    rows = [{"message": {"role": "user", "content": "最初の指示"}}]
    for i, model in enumerate(models, start=1):
        rows.append({"message": {"role": "assistant", "content": [
            {"type": "text", "text": "委任する"},
            {"type": "tool_use", "name": "Agent",
             "input": {"model": model, "subagent_type": "general-purpose",
                       "description": f"委任 {i}",
                       "prompt": f"委任 {i}。docs/JEV.md を読む。Do not commit."}},
        ]}})
    # Agent 以外の道具と、prompt が無い呼び出しは抜かない
    rows.append({"message": {"role": "assistant", "content": [
        {"type": "tool_use", "name": "Bash", "input": {"command": "ls"}},
        {"type": "tool_use", "name": "Agent", "input": {"model": "x"}},
    ]}})
    rows.append({"message": {"role": "user", "content": [{"type": "tool_result",
                                                          "content": "結果"}]}})
    path = tmp_path / "rec.jsonl"
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
                    encoding="utf-8")
    return path


def test_extract_delegations_takes_every_agent_call_in_order(tmp_path):
    cfg = D.load_tiers()
    models = list(cfg["model_to_tier"]) + ["未知のモデル"]
    calls = D.extract_delegations(_transcript(tmp_path, models))
    assert [c["model"] for c in calls] == models
    assert [c["index"] for c in calls] == list(range(1, len(models) + 1))
    assert all(c["prompt_head"] and c["prompt_chars"] > 0 for c in calls)
    assert len(calls[0]["prompt_head"]) <= D.PROMPT_HEAD_CHARS


def test_extract_delegations_survives_a_broken_line(tmp_path):
    path = _transcript(tmp_path, ["a"])
    path.write_text("これは JSON ではない\n" + path.read_text(encoding="utf-8"),
                    encoding="utf-8")
    assert len(D.extract_delegations(path)) == 1


# ---------------------------------------------------------------------------
# 模擬送信
# ---------------------------------------------------------------------------
class _FakeClient:
    calls: list[tuple] = []
    kind: str = "implementation"
    confidence: float = 0.95
    noul_by_qid: dict = {}

    def __init__(self, model=None, **kwargs):
        self.model = model

    def evaluate(self, state, questions):
        _FakeClient.calls.append((state, questions))
        answers = {}
        for qid, spec in questions.items():
            if spec["type"] == "noul":
                answers[qid] = {"type": "noul",
                                "noul": _FakeClient.noul_by_qid.get(qid, 0.1)}
            else:
                probs = {k: 0.0 for k in spec["criteria"]}
                probs[_FakeClient.kind] = 0.9
                answers[qid] = {"type": "choice", "choice": _FakeClient.kind,
                                "probabilities": probs,
                                "confidence": _FakeClient.confidence}
        return {"model": "fake", "answers": answers}


@pytest.fixture
def fake_client(monkeypatch):
    _FakeClient.calls = []
    _FakeClient.kind = "implementation"
    _FakeClient.confidence = 0.95
    _FakeClient.noul_by_qid = {}
    monkeypatch.setattr(D, "JevClient", _FakeClient)
    return _FakeClient


def test_plan_dry_run_sends_nothing(tmp_path, fake_client):
    src = _write(tmp_path, "p.txt", IMPLEMENTATION_PROMPT)
    out = tmp_path / "out"
    assert D.main(["plan", "--prompt", str(src), "--out", str(out), "--dry-run"]) == 0
    assert fake_client.calls == []
    records = _read_jsonl(next(out.glob("plan_*.jsonl")))
    assert records[-1]["kind"] == "_summary"
    assert records[-1]["dry_run"] is True
    assert records[-1]["n_requests"] == 0
    assert records[-1]["tier_label"] is None
    assert records[0]["sent"] is False


def test_plan_sends_one_request_and_records_the_tier(tmp_path, fake_client):
    cfg = D.load_tiers()
    src = _write(tmp_path, "p.txt", IMPLEMENTATION_PROMPT)
    out = tmp_path / "out"
    assert D.main(["plan", "--prompt", str(src), "--out", str(out)]) == 0
    assert len(fake_client.calls) == 1
    state, questions = fake_client.calls[0]
    # state は code が組んだ項目だけ。委任文の本文と数えた値が入っている。
    assert set(state) == {"task_text", "files_named", "n_files", "total_lines",
                          "touches_protected", "required_outputs", "has_stop_condition"}
    assert len(questions) == 5
    rec = _read_jsonl(next(out.glob("plan_*.jsonl")))[0]
    assert rec["sent"] is True
    assert rec["tier_id"] == "implementation"
    assert rec["tier_label"] == cfg["tiers"]["implementation"]["label"]
    assert rec["touches_protected"] is True
    assert rec["required_outputs"] == 3


def test_plan_summary_line_is_one_line_with_the_tier(tmp_path, fake_client, capsys):
    cfg = D.load_tiers()
    src = _write(tmp_path, "p.txt", IMPLEMENTATION_PROMPT)
    assert D.main(["plan", "--prompt", str(src), "--out", str(tmp_path / "out"),
                   "--summary"]) == 0
    printed = capsys.readouterr().out.strip().splitlines()
    assert len(printed) == 1
    assert cfg["tiers"]["implementation"]["label"] in printed[0]


def test_plan_reports_unreachable_and_exits_0(tmp_path, monkeypatch, capsys):
    def _boom(*a, **k):
        raise D.JevError("鍵が無い")
    monkeypatch.setattr(D, "JevClient", _boom)
    src = _write(tmp_path, "p.txt", IMPLEMENTATION_PROMPT)
    assert D.main(["plan", "--prompt", str(src), "--out", str(tmp_path / "out"),
                   "--summary"]) == 0
    assert "未到達" in capsys.readouterr().out


def test_plan_returns_2_and_sends_nothing_when_redaction_fails(tmp_path, monkeypatch,
                                                               fake_client):
    def _boom(_state):
        raise D.RedactionError("伏せ切れていない")
    monkeypatch.setattr(D, "clean_state", _boom)
    src = _write(tmp_path, "p.txt", IMPLEMENTATION_PROMPT)
    assert D.main(["plan", "--prompt", str(src), "--out", str(tmp_path / "out")]) == 2
    assert fake_client.calls == []


def test_plan_missing_file_returns_1(tmp_path):
    assert D.main(["plan", "--prompt", str(tmp_path / "nope.txt"),
                   "--out", str(tmp_path / "out")]) == 1


def test_calibrate_counts_agreement_with_the_lead_choice(tmp_path, fake_client):
    cfg = D.load_tiers()
    # 実装の段に写るモデルと、作業の段に写るモデルと、対応表に無いモデル
    by_tier = {tier: model for model, tier in cfg["model_to_tier"].items()}
    models = [by_tier["implementation"], by_tier["work"], "未知のモデル"]
    rec_path = _transcript(tmp_path, models)
    out = tmp_path / "out"
    # 推奨は全件「実装の段」になる(模擬の答えが implementation 固定)
    assert D.main(["calibrate", "--transcript", str(rec_path), "--out", str(out)]) == 0
    records = _read_jsonl(next(out.glob("calibrate_*.jsonl")))
    summary = records[-1]
    assert summary["n_delegations"] == 3
    assert summary["n_match"] == 1
    assert summary["n_mismatch"] == 1
    assert summary["n_unmapped"] == 1
    assert summary["n_unevaluated"] == 0
    assert [r["agreement"] for r in records[:-1]] == ["一致", "不一致", "対応表に無い"]
    assert len(fake_client.calls) == 3


def test_calibrate_dry_run_sends_nothing_and_still_lists_the_delegations(tmp_path,
                                                                        fake_client, capsys):
    cfg = D.load_tiers()
    models = list(cfg["model_to_tier"])
    rec_path = _transcript(tmp_path, models)
    out = tmp_path / "out"
    assert D.main(["calibrate", "--transcript", str(rec_path), "--out", str(out),
                   "--dry-run"]) == 0
    assert fake_client.calls == []
    printed = capsys.readouterr().out
    assert f"抜けた委任: {len(models)} 件" in printed  # one delegation per model in model_to_tier
    summary = _read_jsonl(next(out.glob("calibrate_*.jsonl")))[-1]
    assert summary["n_unevaluated"] == len(models)
    assert summary["n_match"] == summary["n_mismatch"] == 0
    assert summary["dry_run"] is True


def test_printed_output_has_no_stop_or_pass_words(tmp_path, fake_client, capsys):
    """表と末尾の 1 行にも「止める / 通す」を出さない。"""
    src = _write(tmp_path, "p.txt", IMPLEMENTATION_PROMPT)
    assert D.main(["plan", "--prompt", str(src), "--out", str(tmp_path / "out")]) == 0
    printed = capsys.readouterr().out
    for word in STOP_WORDS:
        assert word not in printed, word


def test_calibrate_missing_transcript_returns_1(tmp_path):
    assert D.main(["calibrate", "--transcript", str(tmp_path / "nope.jsonl"),
                   "--out", str(tmp_path / "out")]) == 1
