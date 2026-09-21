"""`scripts/jev_survey.py` の引用の抽出・項目の抽出・順位の重み・合成の境界を検査する。

この道具は何も止めない。出すのは確率と要確認の印、そして code が作った順位だけである
(オーナー逐語 L-218)。ネットワークには一切触れない(`--dry-run` でしか通さない)。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import scripts.jev_survey as S  # noqa: E402


# ---------------------------------------------------------------------------
# 合成した報告
# ---------------------------------------------------------------------------
VERIFY_MD = """# 一次資料の確認

## 主張

bitFlyer の公開約定履歴は 31 日で消える。

## 一次資料

- URL: https://example.invalid/docs/executions
- 取得日: 2026-09-19
- 取得方法: WebFetch(HTTP 200)

## 引用(原文そのまま)

> Executions are available for the last 31 days only.

## 別の引用

公式の説明にはこうある:「The endpoint returns the most recent 500 executions per page.」

## 応答の例

出典 https://example.invalid/api

```
GET /v1/executions -> 200
```
"""

TRIAGE_MD = """# 市場・環境調査 — 2026-09-19

### 出典

| URL | 方法 | 取得日 |
|---|---|---|
| https://example.invalid/a | WebFetch | 2026-09-19 |
| https://example.invalid/b | WebSearch | 2026-09-19 |

### 知見

| 知見 | 印(事実/推定/仮定) | このプロジェクトへの含意 |
|---|---|---|
| A 取引所は清算履歴を公開している | 事実 | 清算連鎖の単位で使える |
| B は手数料を下げた | 推定 | 無し |
"""


# ---------------------------------------------------------------------------
# verify
# ---------------------------------------------------------------------------
def test_extract_quotes_finds_three_types():
    types = {q["type"] for q in S.extract_quotes(VERIFY_MD)}
    assert types == {"blockquote", "corner_quote", "code_block"}


def test_corner_quote_needs_twenty_characters():
    short = "説明にはこうある:「短い引用」。\n"
    assert S.extract_quotes(short) == []


def test_verify_pairs_use_the_claim_section_when_no_sentence_is_above():
    pairs = S.extract_verify_pairs(VERIFY_MD)
    bq = next(p for p in pairs if p["kind"] == "citation_blockquote")
    assert "31 日で消える" in bq["state"]["claim"]
    assert "31 days" in bq["state"]["quoted_source"]


def test_verify_pairs_prefer_the_sentence_right_above_the_quote():
    pairs = S.extract_verify_pairs(VERIFY_MD)
    cq = next(p for p in pairs if p["kind"] == "citation_corner_quote")
    assert cq["state"]["claim"].startswith("公式の説明")


def test_citation_note_collects_url_date_and_http():
    pairs = S.extract_verify_pairs(VERIFY_MD)
    note = next(p for p in pairs if p["kind"] == "citation_blockquote")["state"]["citation_note"]
    assert "https://" in note and "取得日" in note and "HTTP" in note


def test_combine_verify_flags_says_nothing_at_threshold():
    answers = {
        "relation": {"probabilities": {"confirms": 0.6, "contradicts": 0.05,
                                       "says_nothing": S.ATTENTION}},
        "scope_stated": {"noul": 1.0},
    }
    rec = S.combine_verify(answers)
    assert rec["relation_flag"] is True and rec["flag"] is True
    answers["relation"]["probabilities"]["says_nothing"] = S.ATTENTION - 0.01
    assert S.combine_verify(answers)["flag"] is False


def test_combine_verify_flags_missing_scope():
    answers = {
        "relation": {"probabilities": {"confirms": 0.99, "contradicts": 0.0,
                                       "says_nothing": 0.01}},
        "scope_stated": {"noul": 1.0 - S.ATTENTION},
    }
    rec = S.combine_verify(answers)
    assert rec["scope_flag"] is True and rec["relation_flag"] is False and rec["flag"] is True


# ---------------------------------------------------------------------------
# triage
# ---------------------------------------------------------------------------
def test_extract_items_reads_both_tables():
    items = S.extract_items(TRIAGE_MD)
    kinds = [i["kind"] for i in items]
    assert kinds.count("source_row") == 2
    assert kinds.count("finding_row") == 2
    src = items[0]["item"]
    assert src["url"] == "https://example.invalid/a"
    assert src["method"] == "WebFetch"
    assert src["date"] == "2026-09-19"


def test_extract_items_skips_the_separator_row():
    for item in S.extract_items(TRIAGE_MD):
        assert "---" not in item["claim"]


def test_inventory_names_are_collected_from_the_ledgers():
    names = S.inventory_names()
    assert names, "在庫名が 1 件も集まらない"
    assert len(names) <= S.MAX_INVENTORY_NAMES


def test_rank_score_is_computed_by_code_with_the_fixed_weights():
    answers = {
        "relevance": {"noul": 0.8},
        "duplicate_of_inventory": {"noul": 0.25},
        "needs_probe": {"noul": 0.9},
        "source_type": {"probabilities": {"primary": 0.6, "secondary": 0.4}, "confidence": 0.6},
    }
    rec = S.combine_triage(answers)
    expected = 0.5 * 0.8 + 0.3 * 0.6 + 0.2 * (1 - 0.25)
    assert rec["rank_score"] == round(expected, 4)
    assert rec["source_type"] == "primary"
    assert rec["flag"] is True


def test_needs_probe_flag_is_gated_at_presence():
    base = {"relevance": {"noul": 0.5}, "duplicate_of_inventory": {"noul": 0.0},
            "source_type": {"probabilities": {"primary": 1.0}}}
    on = S.combine_triage(dict(base, needs_probe={"noul": S.PRESENCE}))
    off = S.combine_triage(dict(base, needs_probe={"noul": S.PRESENCE - 0.01}))
    assert on["flag"] is True and off["flag"] is False
    assert off["reason"] == "needs_probe_below_presence"


# ---------------------------------------------------------------------------
# CLI(--dry-run は 1 件も送らない)
# ---------------------------------------------------------------------------
def test_cli_verify_dry_run(tmp_path, capsys):
    art = tmp_path / "report.md"
    art.write_text(VERIFY_MD, encoding="utf-8")
    out = tmp_path / "out"
    assert S.main(["verify", str(art), "--out", str(out), "--dry-run"]) == 0
    printed = capsys.readouterr().out
    assert "--dry-run" in printed
    recs = [json.loads(x) for x in
            (out / "report_verify.jsonl").read_text(encoding="utf-8").splitlines()]
    assert recs[-1]["kind"] == "_summary" and recs[-1]["mode"] == "verify"
    assert recs[-1]["n_requests"] == 0
    assert all(r["sent"] is False for r in recs if r["kind"] != "_summary")


def test_cli_triage_dry_run_summary_line(tmp_path, capsys):
    art = tmp_path / "scan.md"
    art.write_text(TRIAGE_MD, encoding="utf-8")
    out = tmp_path / "out"
    assert S.main(["triage", str(art), "--out", str(out), "--dry-run", "--summary"]) == 0
    last = capsys.readouterr().out.strip().splitlines()[-1]
    assert last.startswith("印 ") and "項目 4 件" in last
    recs = [json.loads(x) for x in
            (out / "scan_triage.jsonl").read_text(encoding="utf-8").splitlines()]
    assert recs[-1]["n_items"] == 4
    assert recs[-1]["rank_weights"] == S.RANK_WEIGHTS
