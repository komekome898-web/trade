"""`scripts/jev_design.py`(設計の段の判定)を検査する。

**ネットワークには一切触れない**(`JevClient` を差し替える。`tests/test_jev_check.py` と同じ作法)。
この道具は判定の中身を決めない。検査するのは、意図の行の取り出し・候補ファイルの読み込み・
問いの形・順位の計算・markdown に確率が 1 つも出ないこと・`--intent` の絞り・代替・不達の停止である。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import scripts.jev_design as D  # noqa: E402


# ---------------------------------------------------------------------------
# 合成した設計文書(§8 の形の小さな複製)
# ---------------------------------------------------------------------------
DESIGN_MD = """# 設計(複製)

## 8. INTENT_MAP(原文の意図 1 項 × この設計の要素)

印: ○ 一致 / △ 代理 / ✕ 未実装 / ＋ 意図に無い実装。

| # | 原文の意図(逐語) | この設計の要素 | 印 | 備考 |
|---|---|---|---|---|
| I-1 | 「**上がりすぎ下がりすぎやトレンド転換を捉えることができるか確認**」 | §3 (a)(b)(c) | **△** | 代理 |
| I-12 | 「**トレンド転換が起きるかまたはそれがトレンドになるのか**」 | §3 (b) 到達 | **△** | 代理 |
| I-13 | 「**簡単な観測**」 | 観測表 | **○** | |
| I-17 | (原文に無い) | §4 E | **＋** | ＋ は取らない |
"""

OBSERVABLES = {
    "bp_reactdir": "signed price change h minutes after the cascade, in bp",
    "reach_back_vwap": "whether price returned within h minutes to the preceding W-hour VWAP",
    "fwd_node": "whether price reached the next high-volume node in the cascade direction",
}
COVARIATES = {
    "dist_vwap_bp": "distance in bp from the cascade price to the preceding W-hour VWAP",
    "bin_pct": "thinness of the price bin where the cascade occurred",
}


def _design(tmp_path: Path) -> Path:
    path = tmp_path / "REACTION_DESIGN_2026-09-18.md"
    path.write_text(DESIGN_MD, encoding="utf-8")
    return path


def _yaml(tmp_path: Path, name: str, obj: dict) -> Path:
    import yaml

    path = tmp_path / name
    path.write_text(yaml.safe_dump(obj, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path


def _json(tmp_path: Path, name: str, obj: dict) -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# 送信の差し替え
# ---------------------------------------------------------------------------
class _FakeClient:
    calls: list[tuple] = []
    # 量ごとの確率の山(0〜4 の段)。既定は「2 の段」= 代理。
    probs_by_name: dict = {}
    noul_by_name: dict = {}

    def __init__(self, model=None, **kwargs):
        self.model = model

    def evaluate(self, state, questions):
        _FakeClient.calls.append((state, questions))
        answers = {}
        for qid, spec in questions.items():
            if spec["type"] == "score":
                name = qid.split("__", 1)[1]
                probs = _FakeClient.probs_by_name.get(name, {"2": 1.0})
                score = sum(float(k) * v for k, v in probs.items())
                answers[qid] = {"type": "score", "score": round(score, 2),
                                "confidence": 0.8, "probabilities": probs}
            else:
                answers[qid] = {"type": "noul",
                                "noul": _FakeClient.noul_by_name.get(qid, 0.1)}
        return {"model": "fake", "answers": answers, "usage": {"input_tokens": 1}}


@pytest.fixture
def fake_client(monkeypatch):
    _FakeClient.calls = []
    _FakeClient.probs_by_name = {}
    _FakeClient.noul_by_name = {}
    monkeypatch.setattr(D, "JevClient", _FakeClient)
    return _FakeClient


# ---------------------------------------------------------------------------
# 意図の行の取り出し
# ---------------------------------------------------------------------------
def test_intent_rows_take_marks_and_skip_plus(tmp_path):
    rows = D.design_intent_rows(_design(tmp_path))
    assert [D._intent_id(r) for r in rows] == ["I-1", "I-12", "I-13"]  # ＋ の I-17 は取らない
    assert rows[0]["mark"] == "△"
    assert "トレンド転換" in rows[0]["intent"]


def test_intent_filter_selects_only_named_rows(tmp_path):
    rows = D.design_intent_rows(_design(tmp_path), ["I-1", "I-12"])
    assert [D._intent_id(r) for r in rows] == ["I-1", "I-12"]


def test_intent_filter_raises_on_unknown_id(tmp_path):
    with pytest.raises(ValueError, match="I-99"):
        D.design_intent_rows(_design(tmp_path), ["I-99"])


def test_design_without_intent_table_raises(tmp_path):
    path = tmp_path / "EMPTY_DESIGN_2026.md"
    path.write_text("# 設計\n\n表は無い。\n", encoding="utf-8")
    with pytest.raises(ValueError, match="意図マップ"):
        D.design_intent_rows(path)


# ---------------------------------------------------------------------------
# 候補ファイルの読み込み
# ---------------------------------------------------------------------------
def test_load_candidates_reads_yaml_and_json(tmp_path):
    assert D.load_candidates(_yaml(tmp_path, "o.yaml", OBSERVABLES)) == OBSERVABLES
    assert D.load_candidates(_json(tmp_path, "o.json", OBSERVABLES)) == OBSERVABLES


def test_load_candidates_rejects_non_dict_and_non_text(tmp_path):
    with pytest.raises(ValueError):
        D.load_candidates(_json(tmp_path, "a.json", {}))
    bad = tmp_path / "b.json"
    bad.write_text(json.dumps({"x": 3}), encoding="utf-8")
    with pytest.raises(ValueError):
        D.load_candidates(bad)


# ---------------------------------------------------------------------------
# 問いの形
# ---------------------------------------------------------------------------
def test_observable_questions_use_a_criteria_list_and_are_sent_at_once(tmp_path, fake_client):
    res = D.rank_observables(_design(tmp_path), _yaml(tmp_path, "o.yaml", OBSERVABLES),
                             intent_ids=["I-1", "I-12"])
    assert res["status"] == "ok"
    assert len(fake_client.calls) == 1              # 1 回の送信に全問
    state, questions = fake_client.calls[0]
    assert len(questions) == 2 * len(OBSERVABLES)   # 意図 × 量
    assert set(questions) == {f"{i}__{n}" for i in ("I-1", "I-12") for n in OBSERVABLES}
    spec = questions["I-1__bp_reactdir"]
    assert spec["type"] == "score"
    assert isinstance(spec["criteria"], list) and len(spec["criteria"]) == 5
    assert "candidate_observables.bp_reactdir" in spec["instructions"]
    assert "purpose_intents.I-1" in spec["instructions"]
    # state は目的の欄 + 候補の辞書
    assert set(state) == {"purpose_intents", "candidate_observables"}
    assert set(state["purpose_intents"]) == {"I-1", "I-12"}
    assert "トレンド転換" in state["purpose_intents"]["I-1"]["intent_verbatim"]
    assert state["candidate_observables"] == OBSERVABLES


def test_covariate_questions_use_true_false_criteria(tmp_path, fake_client):
    res = D.rank_covariates("reach_back_vwap: ...", _yaml(tmp_path, "c.yaml", COVARIATES))
    assert res["status"] == "ok"
    assert len(fake_client.calls) == 1
    state, questions = fake_client.calls[0]
    assert set(questions) == set(COVARIATES)
    spec = questions["dist_vwap_bp"]
    assert spec["type"] == "noul"
    assert set(spec["criteria"]) == {"true", "false"}
    assert "covariates.dist_vwap_bp" in spec["instructions"]
    assert set(state) == {"judgment_quantity", "covariates"}


# ---------------------------------------------------------------------------
# 順位の計算(期待値)と語
# ---------------------------------------------------------------------------
def test_expected_value_matches_the_apis_score_scale():
    # probe の実測の形(0〜4 の段、score は 0 起点の期待値)
    ans = {"type": "score", "score": 3.79, "confidence": 0.82,
           "probabilities": {"0": 0.0, "1": 0.0, "2": 0.01, "3": 0.18, "4": 0.81}}
    assert D.expected_value(ans) == pytest.approx(3.80, abs=0.01)
    assert D.expected_value({"type": "score", "score": 1.5}) == pytest.approx(1.5)


def test_bands_follow_the_three_words():
    assert D.band(3.0) == D.LABEL_DIRECT
    assert D.band(2.9) == D.LABEL_PROXY
    assert D.band(2.0) == D.LABEL_PROXY
    assert D.band(1.99) == D.LABEL_UNRELATED


def test_ranking_is_by_expected_value(tmp_path, fake_client):
    fake_client.probs_by_name = {
        "bp_reactdir": {"3": 0.2, "4": 0.8},        # 期待値 3.8 → 直接
        "reach_back_vwap": {"1": 0.5, "2": 0.5},    # 期待値 1.5 → 無関係
        "fwd_node": {"2": 0.6, "3": 0.4},           # 期待値 2.4 → 代理
    }
    res = D.rank_observables(_design(tmp_path), _yaml(tmp_path, "o.yaml", OBSERVABLES),
                             intent_ids=["I-1"])
    ranking = res["intents"][0]["ranking"]
    assert [r["name"] for r in ranking] == ["bp_reactdir", "fwd_node", "reach_back_vwap"]
    assert [r["rank"] for r in ranking] == [1, 2, 3]
    assert [r["band"] for r in ranking] == [D.LABEL_DIRECT, D.LABEL_PROXY, D.LABEL_UNRELATED]


def test_covariate_label_uses_the_imported_threshold(tmp_path, fake_client):
    from scripts.jev_check import PRESENCE

    assert D.PRESENCE is PRESENCE  # 新しい数値を置かない
    fake_client.noul_by_name = {"dist_vwap_bp": PRESENCE, "bin_pct": PRESENCE - 0.01}
    res = D.rank_covariates("q", _yaml(tmp_path, "c.yaml", COVARIATES))
    assert [r["name"] for r in res["ranking"]] == ["dist_vwap_bp", "bin_pct"]
    assert [r["label"] for r in res["ranking"]] == [D.LABEL_MATCH, D.LABEL_NO_MATCH]


# ---------------------------------------------------------------------------
# markdown に確率が 1 つも出ないこと
# ---------------------------------------------------------------------------
_DECIMAL_RE = re.compile(r"\d\.\d")


def _md_body_without_model_line(md: str) -> str:
    # 見出しの行だけはモデル ID(jev-1.13.0)に点が入るので除いて数える
    return "\n".join(l for l in md.splitlines() if not l.startswith("## 設計の段の判定"))


def test_observables_md_has_the_heading_and_no_probability(tmp_path, fake_client):
    fake_client.probs_by_name = {"bp_reactdir": {"3": 0.23, "4": 0.77}}
    md = tmp_path / "o.md"
    out = tmp_path / "o.json"
    design = _design(tmp_path)
    obs = _yaml(tmp_path, "o.yaml", OBSERVABLES)
    D.rank_observables(design, obs, intent_ids=["I-1", "I-12"], out=out, md=md)
    text = md.read_text(encoding="utf-8")
    assert text.startswith("## 設計の段の判定(jev_design、")
    assert "モデル jev-1.13.0)" in text
    assert str(design) in text and str(obs) in text
    assert "I-1, I-12" in text
    for token in ("0.77", "0.23", "3.77", "probabilit"):
        assert token not in text
    assert not _DECIMAL_RE.search(_md_body_without_model_line(text))
    assert "| 1 | `bp_reactdir` | 直接(3 以上) |" in text
    # 確率と期待値は json にだけ
    got = json.loads(out.read_text(encoding="utf-8"))
    top = got["intents"][0]["ranking"][0]
    assert top["probabilities"] == {"3": 0.23, "4": 0.77}
    assert top["expected"] == pytest.approx(3.77)


def test_covariates_md_has_only_the_words(tmp_path, fake_client):
    fake_client.noul_by_name = {"dist_vwap_bp": 0.51, "bin_pct": 0.12}
    md = tmp_path / "c.md"
    out = tmp_path / "c.json"
    D.rank_covariates("reach_back_vwap: 戻り到達", _yaml(tmp_path, "c.yaml", COVARIATES),
                      out=out, md=md)
    text = md.read_text(encoding="utf-8")
    assert text.startswith("## 設計の段の判定(jev_design、")
    assert "| 1 | `dist_vwap_bp` | 合わせる |" in text
    assert "| 2 | `bin_pct` | 合わせなくてよい |" in text
    for token in ("0.51", "0.12"):
        assert token not in text
    assert not _DECIMAL_RE.search(_md_body_without_model_line(text))
    assert json.loads(out.read_text(encoding="utf-8"))["ranking"][0]["noul"] == 0.51


# ---------------------------------------------------------------------------
# 代替(Jev 不達)
# ---------------------------------------------------------------------------
RECORD_MD = """### 順位表(下位モデル 2 名)

| 順位 | 量 | 語 |
|---|---|---|
| 1 | `bp_reactdir` | 直接(3 以上) |

### 依存の表

| 変数 | 語 |
|---|---|
| dist_vwap_bp | 合わせる |
"""


def test_record_substitute_wraps_the_record(tmp_path):
    record = tmp_path / "rec.md"
    record.write_text(RECORD_MD, encoding="utf-8")
    md = tmp_path / "sub.md"
    res = D.record_substitute(record, md)
    assert res["status"] == "substitute"
    text = md.read_text(encoding="utf-8")
    assert text.startswith("## 設計の段の判定(jev_design、")
    assert f"### 代替(Jev 不達、記録 = {record})" in text
    assert "| 1 | `bp_reactdir` | 直接(3 以上) |" in text
    assert "| dist_vwap_bp | 合わせる |" in text


class _Dead:
    def __init__(self, model=None, **kwargs):
        pass

    def evaluate(self, state, questions):
        raise D.JevError("403: Must supply an API key")


def test_unreachable_stops_both_commands(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(D, "JevClient", _Dead)
    md = tmp_path / "o.md"
    res = D.rank_observables(_design(tmp_path), _yaml(tmp_path, "o.yaml", OBSERVABLES),
                             intent_ids=["I-1"], md=md)
    assert res["status"] == "stopped"
    assert "intents" not in res
    res2 = D.rank_covariates("q", _yaml(tmp_path, "c.yaml", COVARIATES))
    assert res2["status"] == "stopped"
    err = capsys.readouterr().err
    assert err.count("stopped") == 2 and "未到達" in err
    assert "停止(stopped)" in md.read_text(encoding="utf-8")


def test_cli_passes_the_intent_filter_and_exits_0(tmp_path, fake_client):
    design = _design(tmp_path)
    obs = _yaml(tmp_path, "o.yaml", OBSERVABLES)
    md = tmp_path / "o.md"
    rc = D.main(["rank-observables", "--purpose-from", str(design),
                 "--intent", "I-1,I-12", "--observables", str(obs), "--md", str(md)])
    assert rc == 0
    _state, questions = fake_client.calls[0]
    assert {q.split("__", 1)[0] for q in questions} == {"I-1", "I-12"}
    assert "### I-13" not in md.read_text(encoding="utf-8")
