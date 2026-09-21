"""`scripts/jev_owner_log.py`(U13 オーナー発言の種別と紐付け / U16 事故の同型判定)の検査。

この道具は何も判定しない。出すのは確率と候補だけで、**記録に書き込むのはリード**
(オーナー逐語 L-218: 「**判断はLLMと私の役割である**」)。
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

import scripts.jev_owner_log as O  # noqa: E402


# ---------------------------------------------------------------------------
# 合成した入力(実物 `docs/OWNER_STATUS.md` / `OWNER_LOG.md` / `INCIDENTS.md` の形を写す)
# ---------------------------------------------------------------------------
STATUS = """# オーナー側の状態板

**進行中(L-221、2026-09-19)**: 済 = 1・2・3。**次はオーナーの指示待ち。**<br>(前)**進行中の合意(L-220)**: オーナーの指示待ちだった前の版。<br>(前)**進行中(L-217)**: これも前の版で、承認待ちと書いてある。

**いまオーナーに求めていること: 無し(急ぐものは無い)。**

- 「事前に煮詰めておきたいこと」3 件は引き続き止めている(オーナーの指示待ち)。

| 項目 | 状態 | 根拠 | 次の一手(オーナー) |
|---|---|---|---|
| 文書整理 | 提示済み | L-108 | (3) で一覧を見て承認 / 却下 |
| 恒久規則: サーバーの賃借 | 済 | L-124 | — |
| 次の検証 = O-3c | 破棄 | L-153 | 無し(測定器の検証が通ったら開ける) |
| 同 先物・オプション口座 | 未 | L-003 | 入金(約 10 万円)→ 1348.T を 1 口 SOR で買う |

流れの中の現在地: ① K1(今ここ)。
"""

OWNER_LOG_MD = """# オーナー報告・決定の台帳

| ID | 日付 | 種別 | オーナーの言葉 | リードの対応 |
|---|---|---|---|---|
| L-001 | 2026-08-28 | 完了報告 | 225Labo の xlsx を取得して共有 | `backtest_data/` |
| L-002 | 2026-09-06 | 決定 | 「fableは70%、全モデル70%まで許容します」 | §8 |
| L-058 | 2026-09-09 | 指示 + **測定の実行と報告** | 「**建玉を持たないシグナルの評価をお願いします**」 | 実施 |
| L-070 | 2026-09-10 | **決定(改良案の選択、意図の追加)** | 「**1を回してください**」 | 第 10 部 |
| L-141 | 2026-09-12 | **指摘(範囲)** | 「調査範囲を広げないのはおかしくないですか？」 | 調査班 |
これは表の行ではない。
"""

INCIDENTS_MD = """# インシデント台帳(追記のみ)

| ID | 日付 | 事象 | 原因 | 再発防止 |
|---|---|---|---|---|
| I-001 | 2026-09-06 | オーナーの口座開設の進捗を記録しなかった | 会話にしか無かった | 状態板 |
| I-002 | 2026-09-06 | スナップショットが push されていなかった | `git add` の対象漏れ | bat を修正 |

## 〔取り下げ〕旧 I-008 — 見出しであって表の行ではない

## 現行の I-012

| ID | 日付 | 事象 | 原因 | 再発防止 |
|---|---|---|---|---|
| I-012 | 2026-09-19 | **フックの削除を先にしたので道具が全部止まった** | 順序 | 1 回にまとめる |
| I-013 | 2026-09-19 |  | 要旨が空の行 | — |
"""

UTTERANCE = "残りの用途も順次進めてください"


def _write(tmp_path: Path, name: str, text: str) -> Path:
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


# ---------------------------------------------------------------------------
# 待ち項目の切り出し
# ---------------------------------------------------------------------------
def test_pending_items_come_from_the_table_column_and_the_marked_sentences():
    items = O.extract_pending_items(STATUS)
    ids = [i["id"] for i in items]
    assert ids == [f"W{n}" for n in range(1, len(items) + 1)]  # 一意・出た順
    texts = [i["text"] for i in items]
    assert any("次はオーナーの指示待ち" in t for t in texts)
    assert any("事前に煮詰めておきたいこと" in t for t in texts)
    assert any(t.startswith("文書整理:") for t in texts)
    assert any(t.startswith("同 先物・オプション口座:") for t in texts)
    assert [i["source"] for i in items].count("表(次の一手)") == 2


def test_pending_items_drop_the_none_rows_the_stale_versions_and_the_dash_cells():
    texts = [i["text"] for i in O.extract_pending_items(STATUS)]
    # 「いまオーナーに求めていること: 無し」= 印の直後が「無し」なので取らない
    assert not any("急ぐものは無い" in t for t in texts)
    # `(前)` で始まる断片は古い版なので取らない
    assert not any(t.startswith("(前)") for t in texts)
    assert not any("前の版" in t for t in texts)
    # `—` だけのセルと「無し」で始まるセルは取らない
    assert not any(t.startswith("恒久規則") for t in texts)
    assert not any(t.startswith("次の検証") for t in texts)


def test_pending_items_are_capped_and_clipped():
    body = "オーナーの指示待ち" + "あ" * 500
    text = "\n\n".join(f"{i} 件目。{body}" for i in range(30))
    items = O.extract_pending_items(text)
    assert len(items) == O.PENDING_MAX_ITEMS
    assert all(len(i["text"]) <= O.PENDING_MAX_CHARS for i in items)


def test_pending_items_deduplicate_identical_bodies():
    text = "オーナーの指示待ち: 同じ文\n\nオーナーの指示待ち: 同じ文\n"
    assert len(O.extract_pending_items(text)) == 1


def test_pending_items_are_empty_when_nothing_is_waiting():
    assert O.extract_pending_items("# 板\n\n進行中の作業は無い。\n") == []


# ---------------------------------------------------------------------------
# OWNER_LOG の読み(表の読み方は `jev_trace_export.load_owner_log` の再利用)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("cell,expected", [
    ("決定", "決定"),
    ("**決定(改良案の選択、意図の追加)**", "決定"),
    ("指示 + **測定の実行と報告**", "指示"),
    ("質問(返答 054 の後)", "質問"),
    ("実測結果の共有(P8 §1)", "実測結果の共有"),
    ("所感・方針の指摘", "所感・方針の指摘"),
])
def test_normalize_kind_takes_the_word_before_the_bracket(cell, expected):
    assert O.normalize_kind(cell) == expected


def test_load_owner_rows_reads_id_kind_and_quote(tmp_path):
    rows = O.load_owner_rows(_write(tmp_path, "OWNER_LOG.md", OWNER_LOG_MD))
    assert [r["id"] for r in rows] == ["L-001", "L-002", "L-058", "L-070", "L-141"]
    by_id = {r["id"]: r for r in rows}
    assert by_id["L-058"]["kind"] == "指示"
    assert by_id["L-058"]["kind_raw"] == "指示 + 測定の実行と報告"
    assert by_id["L-070"]["kind"] == "決定"
    assert "1を回してください" in by_id["L-070"]["quote"]
    assert "**" not in by_id["L-070"]["quote"]          # 逐語は強調記号を外して読む
    assert by_id["L-002"]["date"] == "2026-09-06"


def test_load_owner_rows_returns_nothing_for_a_missing_file(tmp_path):
    assert O.load_owner_rows(tmp_path / "無い.md") == []


def test_kind_distribution_counts_and_marks_what_is_outside_the_options(tmp_path):
    rows = O.load_owner_rows(_write(tmp_path, "OWNER_LOG.md", OWNER_LOG_MD))
    dist = O.kind_distribution(rows)
    assert dist == {"決定": 2, "完了報告": 1, "指示": 1, "指摘": 1}
    assert [k for k in dist if k not in O.KIND_OPTIONS] == ["完了報告"]


# ---------------------------------------------------------------------------
# INCIDENTS の読み
# ---------------------------------------------------------------------------
def test_load_incidents_reads_the_event_column_and_reports_the_missing_ones(tmp_path):
    found, missing = O.load_incidents(_write(tmp_path, "INCIDENTS.md", INCIDENTS_MD))
    assert list(found) == ["I-001", "I-002", "I-012"]
    assert missing == ["I-013"]                          # 要旨が空の行
    assert found["I-012"].startswith("フックの削除を先にした")   # 強調記号は外す
    assert all(len(v) <= O.INCIDENT_SUMMARY_MAX_CHARS for v in found.values())


def test_load_incidents_ignores_headings_that_mention_a_withdrawn_id(tmp_path):
    found, _ = O.load_incidents(_write(tmp_path, "INCIDENTS.md", INCIDENTS_MD))
    assert "I-008" not in found                          # 見出しは表の行ではない


def test_load_incidents_clips_the_summary(tmp_path):
    long_row = "| I-099 | 2026-09-19 | " + "あ" * 900 + " | 原因 | 対策 |\n"
    found, _ = O.load_incidents(_write(tmp_path, "INCIDENTS.md", INCIDENTS_MD + long_row))
    assert len(found["I-099"]) == O.INCIDENT_SUMMARY_MAX_CHARS


def test_real_repository_files_are_readable():
    """実物が読めることを測る(仕様の入力そのもの)。件数は書かない — 台帳は増える。"""
    rows = O.load_owner_rows()
    assert rows and rows[0]["id"] == "L-001"
    found, missing = O.load_incidents()
    assert {"I-001", "I-010", "I-011", "I-012"} <= set(found)
    assert missing == []
    items = O.extract_pending_items(O.DEFAULT_STATUS.read_text(encoding="utf-8"))
    assert 0 < len(items) <= O.PENDING_MAX_ITEMS


# ---------------------------------------------------------------------------
# 問いの組み立て(合成)
# ---------------------------------------------------------------------------
def test_utterance_questions_have_the_four_ids_and_the_none_option():
    pending = O.extract_pending_items(STATUS)
    qs = O.questions_for_utterance(pending)
    assert list(qs) == ["kind", "answers_pending", "contains_new_rule",
                        "requires_record_now"]
    assert list(qs["kind"]["criteria"]) == ["指示", "決定", "質問", "報告", "指摘", "その他"]
    assert list(qs["answers_pending"]["criteria"]) == \
        [p["id"] for p in pending] + [O.NONE_OPTION]
    # 各選択肢の説明 = 項目の本文
    assert qs["answers_pending"]["criteria"][pending[0]["id"]] == pending[0]["text"]
    for q in qs.values():
        assert q["type"] in ("choice", "noul")
        assert q["instructions"]
    for side in ("true", "false"):
        assert "Example" in qs["contains_new_rule"]["criteria"][side]
        assert "Example" in qs["requires_record_now"]["criteria"][side]


def test_kind_options_carry_one_real_example_each_from_the_owner_log():
    for label, text in O.KIND_OPTIONS.items():
        assert "L-" in text, label            # OWNER_LOG の行番号つきの実例
        assert "「" in text and "」" in text, label


def test_incident_questions_offer_every_incident_plus_none():
    found, _ = O.load_incidents()
    qs = O.questions_for_incident(found)
    assert list(qs) == ["same_type_as", "type_label"]
    assert list(qs["same_type_as"]["criteria"]) == list(found) + [O.NONE_OPTION]
    assert qs["same_type_as"]["criteria"]["I-001"] == found["I-001"]
    assert list(qs["type_label"]["criteria"]) == [
        "記録の欠落", "設定・順序の誤り", "断定・検証不足", "用語のすり替え",
        "打ち切りの欠如", "範囲の逸脱", "その他"]


def test_the_confidence_gate_hides_the_name_below_the_threshold():
    ans = {"kind": {"choice": "指示", "confidence": O.KIND_CONFIDENT}}
    assert O._choice(ans, "kind") == ("指示", O.KIND_CONFIDENT, "指示")
    low = {"kind": {"choice": "指示", "confidence": O.KIND_CONFIDENT - 0.01}}
    assert O._choice(low, "kind")[2] == O.NONE_OPTION
    assert O._choice({"kind": {"choice": "none", "confidence": 0.99}}, "kind")[2] == "none"
    assert O._choice({}, "kind") == (None, None, O.NONE_OPTION)


# ---------------------------------------------------------------------------
# 模擬送信
# ---------------------------------------------------------------------------
class _FakeClient:
    calls: list[tuple] = []
    confidence: float = 0.95
    noul: float = 0.9
    choices: dict = {}

    def __init__(self, model=None, **kwargs):
        self.model = model

    def evaluate(self, state, questions):
        _FakeClient.calls.append((state, questions))
        answers = {}
        for qid, spec in questions.items():
            if spec["type"] == "noul":
                answers[qid] = {"type": "noul", "noul": _FakeClient.noul}
            else:
                choice = _FakeClient.choices.get(qid, list(spec["criteria"])[0])
                answers[qid] = {"type": "choice", "choice": choice,
                                "confidence": _FakeClient.confidence,
                                "probabilities": {choice: _FakeClient.confidence}}
        return {"model": "fake", "answers": answers}


@pytest.fixture
def fake_client(monkeypatch):
    _FakeClient.calls = []
    _FakeClient.confidence = 0.95
    _FakeClient.noul = 0.9
    _FakeClient.choices = {}
    monkeypatch.setattr(O, "JevClient", _FakeClient)
    return _FakeClient


def _classify_args(tmp_path: Path, *extra: str) -> list[str]:
    return ["classify",
            "--text", str(_write(tmp_path, "L-224.txt", UTTERANCE)),
            "--pending-from", str(_write(tmp_path, "STATUS.md", STATUS)),
            "--out", str(tmp_path / "out"), *extra]


def test_classify_dry_run_sends_nothing(tmp_path, fake_client, capsys):
    assert O.main(_classify_args(tmp_path, "--dry-run")) == 0
    assert _FakeClient.calls == []
    summary = _read_jsonl(tmp_path / "out" / "classify__L-224.jsonl")[-1]
    assert summary["dry_run"] is True and summary["n_requests"] == 0
    assert summary["n_pending"] > 0 and summary["unreachable"] is None
    text = capsys.readouterr().out
    assert "1 件も送っていない" in text
    assert "記録に書き込むのはリード" in text


def test_classify_sends_one_request_and_records_the_answers(tmp_path, fake_client):
    _FakeClient.choices = {"kind": "指示", "answers_pending": "W2"}
    assert O.main(_classify_args(tmp_path)) == 0
    assert len(_FakeClient.calls) == 1
    state, questions = _FakeClient.calls[0]
    assert state["utterance"] == UTTERANCE                 # state は code が組む
    assert state["pending_item_count"] == len(state["pending_items"])
    assert set(questions) == {"kind", "answers_pending", "contains_new_rule",
                              "requires_record_now"}
    recs = _read_jsonl(tmp_path / "out" / "classify__L-224.jsonl")
    rec = recs[0]
    assert rec["sent"] is True and rec["model"] == "fake"
    assert rec["kind_choice"] == "指示" and rec["kind_reported"] == "指示"
    assert rec["answers_pending_reported"] == "W2"
    assert rec["new_rule_flag"] is True and rec["record_now_flag"] is True
    assert rec["record_attention"] is True
    assert [r["kind"] for r in recs[1:-1]] == ["pending"] * (len(recs) - 2)


def test_classify_keeps_the_raw_choice_when_the_confidence_is_low(tmp_path, fake_client):
    _FakeClient.confidence = O.KIND_CONFIDENT - 0.01
    _FakeClient.choices = {"kind": "決定"}
    assert O.main(_classify_args(tmp_path)) == 0
    rec = _read_jsonl(tmp_path / "out" / "classify__L-224.jsonl")[0]
    assert rec["kind_choice"] == "決定"                    # 生の答えは捨てない
    assert rec["kind_reported"] == O.NONE_OPTION           # 名前は出さない


def test_classify_marks_the_record_at_the_lower_bar(tmp_path, fake_client):
    _FakeClient.noul = (O.ATTENTION + O.PRESENCE) / 2      # 0.35 以上・0.50 未満
    assert O.main(_classify_args(tmp_path)) == 0
    rec = _read_jsonl(tmp_path / "out" / "classify__L-224.jsonl")[0]
    assert rec["record_now_flag"] is False
    assert rec["record_attention"] is True                 # I-001 の型なので低い方でも印


def test_classify_clips_the_utterance_at_four_thousand_chars(tmp_path, fake_client):
    long_text = _write(tmp_path, "長い.txt", "あ" * 5_000)
    assert O.main(["classify", "--text", str(long_text),
                   "--pending-from", str(_write(tmp_path, "S.md", STATUS)),
                   "--out", str(tmp_path / "out")]) == 0
    state, _ = _FakeClient.calls[0]
    assert len(state["utterance"]) == O.UTTERANCE_MAX_CHARS
    summary = _read_jsonl(tmp_path / "out" / "classify__長い.jsonl")[-1]
    assert summary["utterance_truncated"] is True


def test_classify_works_without_a_status_board(tmp_path, fake_client):
    assert O.main(["classify", "--text", str(_write(tmp_path, "u.txt", UTTERANCE)),
                   "--pending-from", str(tmp_path / "無い.md"),
                   "--out", str(tmp_path / "out")]) == 0
    state, questions = _FakeClient.calls[0]
    assert state["pending_items"] == []
    assert list(questions["answers_pending"]["criteria"]) == [O.NONE_OPTION]
    summary = _read_jsonl(tmp_path / "out" / "classify__u.jsonl")[-1]
    assert summary["status_missing"] is True and summary["n_pending"] == 0


def test_classify_reports_an_unreachable_send(tmp_path, monkeypatch, fake_client, capsys):
    def boom(self, state, questions):
        raise O.JevError("401")
    monkeypatch.setattr(_FakeClient, "evaluate", boom)
    assert O.main(_classify_args(tmp_path)) == 0
    assert "jev: 未到達" in capsys.readouterr().out
    assert _read_jsonl(tmp_path / "out" / "classify__L-224.jsonl")[-1]["unreachable"] == "401"


def test_classify_missing_text_file_returns_one(tmp_path, fake_client):
    assert O.main(["classify", "--text", str(tmp_path / "無い.txt"),
                   "--out", str(tmp_path / "out")]) == 1


def test_summary_only_prints_one_line(tmp_path, fake_client, capsys):
    assert O.main(_classify_args(tmp_path, "--summary")) == 0
    assert len(capsys.readouterr().out.strip().splitlines()) == 1


# ---------------------------------------------------------------------------
# calibrate
# ---------------------------------------------------------------------------
def _calibrate_args(tmp_path: Path, *extra: str) -> list[str]:
    return ["calibrate",
            "--log", str(_write(tmp_path, "OWNER_LOG.md", OWNER_LOG_MD)),
            "--out", str(tmp_path / "out"), *extra]


def test_calibrate_dry_run_reports_rows_and_the_distribution(tmp_path, fake_client, capsys):
    assert O.main(_calibrate_args(tmp_path, "--dry-run")) == 0
    assert _FakeClient.calls == []
    summary = _read_jsonl(tmp_path / "out" / "calibrate.jsonl")[-1]
    assert summary["n_rows"] == 5 and summary["n_requests"] == 0
    assert summary["kind_distribution"] == {"決定": 2, "完了報告": 1, "指示": 1, "指摘": 1}
    assert summary["n_outside_options"] == 1               # 完了報告
    text = capsys.readouterr().out
    assert "選択肢に無い" in text and "1 件も送っていない" in text


def test_calibrate_counts_agreement_with_the_existing_kind_column(tmp_path, fake_client):
    _FakeClient.choices = {"kind": "決定"}                  # 全部「決定」と答える
    assert O.main(_calibrate_args(tmp_path)) == 0
    assert len(_FakeClient.calls) == 5
    recs = _read_jsonl(tmp_path / "out" / "calibrate.jsonl")
    summary = recs[-1]
    assert summary["n_same"] == 2 and summary["n_diff"] == 3
    assert summary["n_unmatched"] == 0
    states = {r["id"]: r["state"] for r in recs if r["kind"] == "row"}
    assert states == {"L-001": "不一致", "L-002": "一致", "L-058": "不一致",
                      "L-070": "一致", "L-141": "不一致"}


def test_calibrate_sends_the_quote_without_any_pending_item(tmp_path, fake_client):
    assert O.main(_calibrate_args(tmp_path)) == 0
    state, questions = _FakeClient.calls[0]
    assert state["pending_items"] == [] and state["pending_item_count"] == 0
    assert list(questions["answers_pending"]["criteria"]) == [O.NONE_OPTION]
    assert "225Labo" in state["utterance"]


def test_calibrate_prints_the_mismatches_without_interpreting_them(tmp_path,
                                                                   fake_client, capsys):
    _FakeClient.choices = {"kind": "決定"}
    assert O.main(_calibrate_args(tmp_path)) == 0
    text = capsys.readouterr().out
    assert "不一致の一覧" in text and "中身の解釈は書かない" in text
    assert "L-001" in text and "L-141" in text


def test_calibrate_missing_log_returns_one(tmp_path, fake_client):
    assert O.main(["calibrate", "--log", str(tmp_path / "無い.md"),
                   "--out", str(tmp_path / "out")]) == 1


# ---------------------------------------------------------------------------
# incident
# ---------------------------------------------------------------------------
def _incident_args(tmp_path: Path, body: str, *extra: str) -> list[str]:
    return ["incident",
            "--text", str(_write(tmp_path, "新しい事故.txt", body)),
            "--incidents", str(_write(tmp_path, "INCIDENTS.md", INCIDENTS_MD)),
            "--out", str(tmp_path / "out"), *extra]


def test_incident_dry_run_sends_nothing_and_counts_the_missing_summaries(
        tmp_path, fake_client, capsys):
    assert O.main(_incident_args(tmp_path, "順序を誤って道具が止まった", "--dry-run")) == 0
    assert _FakeClient.calls == []
    summary = _read_jsonl(tmp_path / "out" / "incident__新しい事故.jsonl")[-1]
    assert summary["dry_run"] is True and summary["n_requests"] == 0
    assert summary["n_incidents"] == 3 and summary["n_missing"] == 1
    assert summary["missing_ids"] == ["I-013"]
    text = capsys.readouterr().out
    assert "要旨が抜けた 1 件" in text and "記録に書き込むのはリード" in text


def test_incident_reports_the_number_only_above_the_confidence_bar(tmp_path, fake_client):
    _FakeClient.choices = {"same_type_as": "I-012", "type_label": "設定・順序の誤り"}
    assert O.main(_incident_args(tmp_path, "順序を誤って道具が止まった")) == 0
    rec = _read_jsonl(tmp_path / "out" / "incident__新しい事故.jsonl")[0]
    assert rec["same_type_as_choice"] == "I-012"
    assert rec["same_type_as_reported"] == "I-012"
    assert rec["type_label"] == "設定・順序の誤り"
    assert rec["sent"] is True and rec["model"] == "fake"


def test_incident_hides_the_number_below_the_confidence_bar(tmp_path, fake_client):
    _FakeClient.confidence = O.KIND_CONFIDENT - 0.01
    _FakeClient.choices = {"same_type_as": "I-012"}
    assert O.main(_incident_args(tmp_path, "順序を誤って道具が止まった")) == 0
    rec = _read_jsonl(tmp_path / "out" / "incident__新しい事故.jsonl")[0]
    assert rec["same_type_as_choice"] == "I-012"           # 生の答えは捨てない
    assert rec["same_type_as_reported"] == O.NONE_OPTION   # 番号は出さない


def test_incident_writes_the_past_incidents_as_records(tmp_path, fake_client):
    assert O.main(_incident_args(tmp_path, "本文", "--dry-run")) == 0
    recs = _read_jsonl(tmp_path / "out" / "incident__新しい事故.jsonl")
    past = [r for r in recs if r["kind"] == "past_incident"]
    assert [r["id"] for r in past] == ["I-001", "I-002", "I-012"]


def test_incident_without_any_past_incident_returns_one(tmp_path, fake_client):
    assert O.main(["incident", "--text", str(_write(tmp_path, "a.txt", "本文")),
                   "--incidents", str(_write(tmp_path, "空.md", "# 何も無い\n")),
                   "--out", str(tmp_path / "out")]) == 1


def test_incident_on_the_real_ledger_offers_i001_to_i012(tmp_path, fake_client):
    """`--dry-run` を `INCIDENTS.md` 自身の記述で当てる(仕様)。"""
    found, _ = O.load_incidents()
    body = found["I-011"]
    assert O.main(["incident", "--text", str(_write(tmp_path, "I-011.txt", body)),
                   "--out", str(tmp_path / "out"), "--dry-run"]) == 0
    summary = _read_jsonl(tmp_path / "out" / "incident__I-011.jsonl")[-1]
    assert summary["n_missing"] == 0 and summary["n_incidents"] >= 12


# ---------------------------------------------------------------------------
# 規則(`docs/JEV.md` §4)
# ---------------------------------------------------------------------------
def test_the_output_never_carries_a_verdict_word(tmp_path, fake_client, capsys):
    _FakeClient.choices = {"kind": "指示", "answers_pending": "W1"}
    assert O.main(_classify_args(tmp_path)) == 0
    assert O.main(_calibrate_args(tmp_path)) == 0
    assert O.main(_incident_args(tmp_path, "本文")) == 0
    text = capsys.readouterr().out
    for word in ("止めるべき", "通してよい", "採用", "棄却"):
        assert word not in text


def test_the_state_goes_through_the_redaction_check(tmp_path, monkeypatch, fake_client,
                                                    capsys):
    def boom(state):
        raise O.RedactionError("鍵らしきものが 1 件")
    monkeypatch.setattr(O, "clean_state", boom)
    assert O.main(_classify_args(tmp_path)) == 0
    assert _FakeClient.calls == []                         # 掛かったら送らない
    assert "jev: 未到達" in capsys.readouterr().out


def test_the_model_id_is_pinned_by_default(tmp_path, fake_client):
    assert O.DEFAULT_MODEL == "jev-1.13.0"
    assert O.main(_classify_args(tmp_path)) == 0
    summary = _read_jsonl(tmp_path / "out" / "classify__L-224.jsonl")[-1]
    assert summary["model"] == "jev-1.13.0"
    assert summary["thresholds"] == {"presence": O.PRESENCE, "attention": O.ATTENTION,
                                     "kind_confident": O.KIND_CONFIDENT}
