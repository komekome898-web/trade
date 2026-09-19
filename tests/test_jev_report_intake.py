"""`scripts/jev_report_intake.py` の受領検査を測る。

検査するもの: 必須項目の見出しの検査 / 判定の語の抽出 / 数値の突き合わせ / 模擬送信 / 印の境界。

この道具は何も止めない。出すのは確率と要確認の印だけである(オーナー逐語 L-218)。
ネットワークには一切触れない(`JevClient` を差し替えるか `--dry-run`)。
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
import scripts.jev_report_intake as I  # noqa: E402


# ---------------------------------------------------------------------------
# 合成した報告
# ---------------------------------------------------------------------------
RESEARCH_MD = """# 研究報告

## 1. 探索区間の全構成表

| 構成 | n | ネット |
|---|---|---|
| A | 120 | 1.4 |

## 2. 判定区間の結果

判定区間は一度だけ走らせた。

## 3. 逆選択の反実仮想

taker で入った場合と比べた。

## 4. アブレーション

条件を 1 つずつ外した。

## 5. サニティ

ルックアヘッド 0、決定性あり。

## 6. なぜそうなるのか

板が薄い時間帯に注文が並ぶ機構である。

## 7. 注意点・限界

サンプルが足りない。
"""

# 「アブレーション」は見出しでも先頭 2 行でもなく、本文の奥にだけ書いてある
DEEP_WORD_MD = """# 報告

## 結果

1 行目。
2 行目。
3 行目。
アブレーションはここにしか書いていない。
"""

VERDICT_MD = """# 報告

## 結果

この族は採用しない。次の族は有望である。

判定の語の混じらない文。

```
ここは棄却と書いてあるがコード柵の中なので本文ではない
```
"""

NUMBER_MD = """# 報告

| 名前 | 値 |
|---|---|
| 取引数 | 340 |

本文では 340 取引を測った。別に 77 という数も書く。

```
出力: 12 件
```

コードブロックの 12 は突き合わせ先にある。

> 引用の中の 55 も突き合わせ先である。

本文の 55 はそれで裏が取れる。
"""


def _write(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


# ---------------------------------------------------------------------------
# 1(a) 必須項目の検査(code)
# ---------------------------------------------------------------------------
def test_required_items_all_found_for_a_full_research_report():
    items = I.check_required_items(RESEARCH_MD, "research")
    assert len(items) == 7
    assert all(it["found"] for it in items), [it for it in items if not it["found"]]


def test_required_items_report_which_one_is_missing():
    text = RESEARCH_MD.replace("## 4. アブレーション\n\n条件を 1 つずつ外した。\n\n", "")
    missing = [it["item"] for it in I.check_required_items(text, "research") if not it["found"]]
    assert missing == ["ablation"]


def test_heading_match_looks_only_at_the_heading_and_the_first_two_lines():
    """規則: 語の一致は見出しと先頭 2 行だけ。本文の奥にある語は当たらない。"""
    scopes = I.heading_scopes(DEEP_WORD_MD)
    assert all("アブレーション" not in s for s in scopes), scopes
    found = {it["item"]: it["found"] for it in I.check_required_items(DEEP_WORD_MD, "research")}
    assert found["ablation"] is False


def test_kinds_have_their_own_item_lists():
    assert set(I.KINDS) == {"research", "survey", "implementation"}
    assert len(I.REQUIRED_ITEMS["research"]) == 7
    assert [it["item"] for it in I.check_required_items("# x\n", "survey")] == [
        "plan", "sources", "findings", "alt_route", "candidates"]
    assert [it["item"] for it in I.check_required_items("# x\n", "implementation")] == [
        "files", "tests", "off_spec", "mapping"]


# ---------------------------------------------------------------------------
# 1(b) 「なぜ」の節(code)
# ---------------------------------------------------------------------------
def test_why_heading_present_and_absent():
    assert I.why_headings(RESEARCH_MD) == ["6. なぜそうなるのか"]
    assert I.why_headings(VERDICT_MD) == []
    recs = I.code_records(VERDICT_MD, "research")
    why = [r for r in recs if r["kind"] == "why_heading"][0]
    assert why["flag"] is True and why["reason"] == "missing"


# ---------------------------------------------------------------------------
# 1(c) 判定の語の抽出(code)
# ---------------------------------------------------------------------------
def test_verdict_sentences_are_split_per_sentence_and_skip_code_fences():
    claims = [r["claim"] for r in I.extract_verdict_sentences(VERDICT_MD)]
    assert "この族は採用しない。" in claims
    assert "次の族は有望である。" in claims
    assert all("コード柵" not in c for c in claims), claims
    assert all("判定の語の混じらない文" not in c for c in claims), claims


# ---------------------------------------------------------------------------
# 1(d) 数値の突き合わせ(code)
# ---------------------------------------------------------------------------
def test_numbers_present_in_tables_code_or_quotes_are_not_listed():
    nums = {r["number"] for r in I.extract_unsourced_numbers(NUMBER_MD)}
    assert "340" not in nums, "表にある数値は突き合わせ先にある"
    assert "12" not in nums, "コードブロックにある数値は突き合わせ先にある"
    assert "55" not in nums, "引用にある数値は突き合わせ先にある"
    assert "77" in nums, "本文にしかない数値は列挙する"


def test_source_lines_are_counted_by_kind():
    _source, counts = I.source_text_of(NUMBER_MD)
    assert counts["table"] >= 3 and counts["code"] >= 3 and counts["quote"] == 1


# ---------------------------------------------------------------------------
# 2 Jev の問い(形)
# ---------------------------------------------------------------------------
def test_questions_are_positive_single_judgment_with_examples():
    for questions in (I.questions_verdict(), I.questions_prompt(), I.questions_origin()):
        for qid, spec in questions.items():
            assert spec["type"] == "noul", qid
            assert set(spec["criteria"]) == {"true", "false"}, qid
            assert "Example" in spec["criteria"]["true"], qid
            assert "Example" in spec["criteria"]["false"], qid
    assert list(I.questions_prompt()) == ["scope_widened", "required_items_addressed"]


def test_why_section_question_is_the_one_from_jev_check():
    pair = {"kind": "why_section", "a_role": "a", "b_role": "b"}
    assert I.question_for("why_section", pair) == J.question_for("why_section", pair)


# ---------------------------------------------------------------------------
# 3 印の境界(しきい値は `jev_check` から import したもの)
# ---------------------------------------------------------------------------
def test_thresholds_come_from_jev_check():
    assert I.ATTENTION is J.ATTENTION and I.PRESENCE is J.PRESENCE


def test_verdict_flag_at_presence_boundary():
    assert I.combine_verdict({"pronounces_verdict": {"noul": I.PRESENCE}})["flag"] is True
    assert I.combine_verdict({"pronounces_verdict": {"noul": I.PRESENCE - 0.01}})["flag"] is False


def test_origin_flag_at_attention_boundary():
    on = I.combine_origin({"origin_stated": {"noul": 1.0 - I.ATTENTION}})
    off = I.combine_origin({"origin_stated": {"noul": 1.0 - I.ATTENTION + 0.01}})
    assert on["flag"] is True and off["flag"] is False
    assert on["question"] == "origin_stated"


def test_prompt_flags_use_presence_for_scope_and_attention_for_items():
    widened, items = I.combine_prompt({
        "scope_widened": {"noul": I.PRESENCE},
        "required_items_addressed": {"noul": 1.0 - I.ATTENTION},
    })
    assert widened["flag"] is True and items["flag"] is True
    widened2, items2 = I.combine_prompt({
        "scope_widened": {"noul": I.PRESENCE - 0.01},
        "required_items_addressed": {"noul": 1.0 - I.ATTENTION + 0.01},
    })
    assert widened2["flag"] is False and items2["flag"] is False


def test_why_flag_uses_the_contradicts_probability():
    answers = {"relation": {"probabilities": {"consistent": 0.1, "contradicts": I.ATTENTION,
                                              "unrelated": 0.05}}}
    assert I.combine_why(answers)["flag"] is True
    answers["relation"]["probabilities"]["contradicts"] = I.ATTENTION - 0.01
    assert I.combine_why(answers)["flag"] is False


# ---------------------------------------------------------------------------
# 4 模擬送信
# ---------------------------------------------------------------------------
class _FakeClient:
    calls: list[tuple] = []
    noul_by_qid: dict = {}

    def __init__(self, model=None, **kwargs):
        self.model = model

    def evaluate(self, state, questions):
        _FakeClient.calls.append((state, questions))
        answers = {}
        for qid, spec in questions.items():
            if spec["type"] == "noul":
                answers[qid] = {"type": "noul",
                                "noul": _FakeClient.noul_by_qid.get(qid, 0.9)}
            else:
                answers[qid] = {"type": "choice", "choice": "contradicts",
                                "probabilities": {"consistent": 0.1, "contradicts": 0.85,
                                                  "unrelated": 0.05}}
        return {"model": "fake", "answers": answers}


@pytest.fixture
def fake_client(monkeypatch):
    _FakeClient.calls = []
    _FakeClient.noul_by_qid = {}
    monkeypatch.setattr(I, "JevClient", _FakeClient)
    return _FakeClient


def test_dry_run_sends_nothing_and_still_flags_the_code_checks(tmp_path, fake_client, capsys):
    art = _write(tmp_path, "r.md", VERDICT_MD)
    out = tmp_path / "out"
    assert I.main(["check", str(art), "--kind", "research", "--out", str(out),
                   "--dry-run"]) == 0
    assert fake_client.calls == []
    records = _read_jsonl(out / "r.jsonl")
    summary = records[-1]
    assert summary["dry_run"] is True and summary["n_requests"] == 0
    assert all(r.get("sent") is False for r in records if r["kind"] != "_summary")
    # code の検査は --dry-run でも印が付く
    assert summary["flag_by_kind"]["required_item"] >= 1
    assert summary["flag_by_kind"]["why_heading"] == 1
    assert "--dry-run" in capsys.readouterr().out


def test_one_request_per_sentence_and_per_number(tmp_path, fake_client):
    art = _write(tmp_path, "s.md", VERDICT_MD)
    out = tmp_path / "out"
    assert I.main(["check", str(art), "--kind", "research", "--out", str(out)]) == 0
    records = _read_jsonl(out / "s.jsonl")
    summary = records[-1]
    n_verdict = len([r for r in records if r["kind"] == "verdict_sentence"])
    n_number = len([r for r in records if r["kind"] == "unsourced_number"])
    assert summary["n_requests"] == len(fake_client.calls) == n_verdict + n_number
    # state は code が組む(判定される側が書かない)
    state, _q = fake_client.calls[0]
    assert set(state) == {"sentence", "nearby_context"}
    # 既定の 0.9 では判定の語に印が付く(pronounces_verdict >= PRESENCE)
    assert summary["flag_by_kind"]["verdict_sentence"] == n_verdict


def test_prompt_pair_is_one_request_and_two_records(tmp_path, fake_client):
    art = _write(tmp_path, "p.md", RESEARCH_MD)
    prompt = _write(tmp_path, "prompt.md", "1. 全構成表を出す\n2. アブレーションを出す\n")
    out = tmp_path / "out"
    assert I.main(["check", str(art), "--kind", "research", "--prompt", str(prompt),
                   "--out", str(out)]) == 0
    records = _read_jsonl(out / "p.jsonl")
    rows = [r for r in records if r["kind"] == "prompt_vs_report"]
    assert len(rows) == 2
    assert {r["question"] for r in rows} == {"scope_widened", "required_items_addressed"}
    prompt_calls = [c for c in fake_client.calls if "delegation_prompt" in c[0]]
    assert len(prompt_calls) == 1, "対は 1 要求(問いを 2 つ並べる)"
    state, _q = prompt_calls[0]
    assert set(state) == {"delegation_prompt", "report_headings", "report_conclusion"}
    assert state["report_headings"][0] == "研究報告"
    assert records[-1]["prompt"] is True


def test_without_prompt_no_prompt_pair_is_built(tmp_path, fake_client):
    art = _write(tmp_path, "np.md", RESEARCH_MD)
    out = tmp_path / "out"
    assert I.main(["check", str(art), "--kind", "research", "--out", str(out)]) == 0
    records = _read_jsonl(out / "np.jsonl")
    assert [r for r in records if r["kind"] == "prompt_vs_report"] == []
    assert records[-1]["prompt"] is False


def test_number_questions_are_capped(tmp_path, fake_client, monkeypatch):
    monkeypatch.setattr(I, "MAX_NUMBER_QUESTIONS", 2)
    body = "# 報告\n\n" + "\n".join(f"本文の {n} 番目。" for n in range(101, 110))
    art = _write(tmp_path, "cap.md", body)
    out = tmp_path / "out"
    assert I.main(["check", str(art), "--kind", "research", "--out", str(out)]) == 0
    records = _read_jsonl(out / "cap.jsonl")
    nums = [r for r in records if r["kind"] == "unsourced_number"]
    assert len(nums) == 9
    assert sum(1 for r in nums if r["sent"]) == 2
    assert all(r["reason"] == "truncated" for r in nums if not r["sent"])


def test_summary_line_is_the_last_line(tmp_path, fake_client, capsys):
    art = _write(tmp_path, "sum.md", VERDICT_MD)
    out = tmp_path / "out"
    assert I.main(["check", str(art), "--kind", "research", "--out", str(out),
                   "--summary"]) == 0
    printed = capsys.readouterr().out.strip().splitlines()
    assert len(printed) == 1 and printed[0].startswith("印 ")


def test_unreachable_is_shown_when_nothing_got_through(tmp_path, monkeypatch, capsys):
    class _Dead:
        def __init__(self, *a, **k):
            raise I.JevError("鍵が無い")

    monkeypatch.setattr(I, "JevClient", _Dead)
    art = _write(tmp_path, "dead.md", VERDICT_MD)
    out = tmp_path / "out"
    assert I.main(["check", str(art), "--kind", "research", "--out", str(out)]) == 0
    printed = capsys.readouterr().out.strip().splitlines()
    assert printed[-1].startswith("jev: 未到達")


def test_returns_2_and_sends_nothing_when_redaction_check_fails(
        tmp_path, fake_client, monkeypatch):
    monkeypatch.setattr(J, "redact_json", lambda obj: obj)
    art = _write(tmp_path, "leak.md", "# 報告\n\n連絡先 someone@example.com は棄却する。\n")
    out = tmp_path / "out"
    assert I.main(["check", str(art), "--kind", "research", "--out", str(out)]) == 2
    assert fake_client.calls == []


def test_missing_files_return_1(tmp_path, capsys):
    out = tmp_path / "out"
    assert I.main(["check", str(tmp_path / "nope.md"), "--out", str(out)]) == 1
    art = _write(tmp_path, "ok.md", "# 報告\n")
    assert I.main(["check", str(art), "--prompt", str(tmp_path / "nope.md"),
                   "--out", str(out)]) == 1
    capsys.readouterr()


def test_output_never_says_stop_or_pass(tmp_path, fake_client, capsys):
    """出力に「止める / 通す」の語を置かない(`docs/JEV.md` §4-1)。"""
    art = _write(tmp_path, "w.md", RESEARCH_MD)
    out = tmp_path / "out"
    assert I.main(["check", str(art), "--kind", "research", "--out", str(out)]) == 0
    printed = capsys.readouterr().out
    assert "止める" not in printed and "通す" not in printed
    assert "印であって判断ではない" in printed
