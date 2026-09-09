"""出荷前検査(`scripts/preflight_prereg.py`)が、**実際に起きた欠陥を捕まえる**ことを固定する。

**検査を書くだけでは足りない。** 何も検出しない検査は、無いより悪い —
「検査を通った」が「正しい」の代用品になるからである。
そこで各検査に、**2026-09-09 に実際に起きた欠陥を再現した文書**を食わせ、
発火することを確かめる(陽性)。あわせて健全な文書で黙ることも見る(陰性)。

対応表(検査 → 拾えたはずの事故):

| 検査 | 事故 |
|---|---|
| C1 数え上げ | L-049 アブレーションを「6 種」と書いて実際は 7 種 |
| C2 記号の一意性 | I-004 同じ記号 `sd` を 3 つの量に使い回した |
| C3 射程の漏れ | L-048 §0 で射程外とした経費を §5 の判定バーにした |
| C4 未処理の残留 | I-005 3 水準が「未測定」のまま完成と称した |
| C5 用語 | L-049 専門語がオーナーに一つも通じなかった |
| C6 網羅性・一致 | I-005 準備測定が族の一部しか埋めず、値も定義と違う実装から出ていた |
| C7 判定条件の出所 | I-004 判定バー 5 bp の出所を 2 回とも誤表示した |
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import preflight_prereg as pf  # noqa: E402

K1 = REPO / "docs" / "PHASE2" / "K1" / "PREREG.md"
K1_MEASURED = REPO / "docs" / "PHASE2" / "K1" / "dispersion.json"


def _codes(findings) -> set[str]:
    return {f.check.split()[0] for f in findings}


# --------------------------------------------------------------- 陽性 --------


def test_c1_fires_on_the_miscount_that_actually_happened(tmp_path: Path):
    """L-049 の再現: 「7 種」と書いて 6 行しかない表。"""
    doc = tmp_path / "p.md"
    doc.write_text(
        "## 7. アブレーション — **7 種**\n\n"
        "| # | 内容 |\n|---|---|\n"
        + "".join(f"| {i} | x |\n" for i in range(1, 7)),
        encoding="utf-8",
    )
    assert "C1" in _codes(pf.c1_counts_match(doc.read_text("utf-8"), pf.split_sections(doc.read_text("utf-8"))))


def test_c2_fires_on_the_symbol_reuse_that_actually_happened():
    """I-004 の再現: `sd` を全足のばらつきと 1 取引のばらつきの両方に使う。"""
    text = (
        "- **`sd`** = 全足の値動きの幅。符号なし\n"
        "\n| 記号 | 意味 |\n|---|---|\n"
        "| **`sd`** | 1 取引の符号付き損益のばらつき |\n"
    )
    findings = pf.c2_symbol_defined_once(text)
    assert "C2" in _codes(findings)
    assert "`sd`" in findings[0].detail


def test_c3_fires_when_a_cost_bar_returns_to_the_judgment(tmp_path: Path):
    """L-048 の再現: §0 で射程外と書いた経費が、判定条件に肯定形で戻る。"""
    text = (
        "## 0. この単位が答える問い\n\n答えない:\n- 執行を含めた損益(**経費**・手数料)は層 ②\n\n"
        "## 5. 採用基準\n\n### 5.3 候補と呼ぶ条件\n\n"
        "1. `mean(r)` が往復の手数料 5 bp を超える\n"
        "2. 帰無の 95 点を超える\n"
    )
    assert "C3" in _codes(pf.c3_scope_leak(pf.split_sections(text)))


def test_c4_fires_on_an_unmeasured_level_left_in_the_table():
    """I-005 の再現: 族の一部が「未測定」のまま本文に残る。"""
    text = "## 5. 検出力\n\n| 足 | sd |\n|---|---|\n| 30 分 | 未測定 |\n"
    assert "C4" in _codes(pf.c4_no_unfinished(pf.split_sections(text)))


def test_c5_fires_when_jargon_has_no_glossary():
    """L-049 の再現: 帰無・アブレーション・サニティを説明なしに使う。"""
    text = "## 6. 帰無と多重性\n\n帰無 1,000 回・アブレーション 6 種・サニティ 5 種を行う。\n"
    findings = pf.c5_jargon_explained(text, pf.split_sections(text))
    assert "C5" in _codes(findings)
    assert "用語の節が無い" in findings[0].detail


def test_c6_fires_when_the_family_is_only_partly_measured(tmp_path: Path):
    """I-005 の再現: 族に 6 水準あるのに、準備測定は 3 水準しか埋まっていない。"""
    measured = tmp_path / "m.json"
    measured.write_text(
        json.dumps({"feet": {f: {"sd_trade_bp": 1.0} for f in ("5", "15", "60")}}),
        encoding="utf-8",
    )
    text = "| **足** `foot` | 1 / 3 / 5 / 15 / 30 / 60 分 | 6 |\n1.0 bp\n"
    findings = pf.c6_coverage(text, measured)
    assert "C6" in _codes(findings)
    assert "'1'" in findings[0].detail and "'30'" in findings[0].detail


def test_c6_fires_when_the_document_disagrees_with_the_measurement(tmp_path: Path):
    """I-005 の核心: 事前登録の数値が、測定出力と違う(手で書いた値が残っている)。"""
    measured = tmp_path / "m.json"
    measured.write_text(json.dumps({"feet": {"15": {"sd_trade_bp": 92.8}}}), encoding="utf-8")
    text = "15 分の sd_trade は **255.2 bp** である\n"  # 旧・誤りの値
    findings = pf.c6_coverage(text, measured)
    assert any("92.8" in f.detail for f in findings)


def test_c7_fires_on_a_bare_threshold_in_the_judgment(tmp_path: Path):
    """I-004 の再現: 判定条件に、出所タグの無い裸の数値バーが置かれる。"""
    text = "## 5. 採用基準\n\n### 5.3 候補と呼ぶ条件\n\n1. `mean(r) > 5 bp`(線 B)\n"
    assert "C7" in _codes(pf.c7_provenance_on_thresholds(pf.split_sections(text)))


# --------------------------------------------------------------- 陰性 --------


def test_a_correct_count_is_silent():
    text = "## 7. ア — **3 種**\n\n| # | x |\n|---|---|\n| 1 | a |\n| 2 | b |\n| 3 | c |\n"
    assert not pf.c1_counts_match(text, pf.split_sections(text))


def test_a_declaration_that_a_cost_is_excluded_is_silent():
    """「経費は使わない」と宣言する行で発火してはいけない(宣言と混入は違う)。"""
    text = (
        "## 0. この単位が答える問い\n\n答えない:\n- **経費**を含む損益\n\n"
        "## 5. 採用基準\n\n### 5.3 候補と呼ぶ条件\n\n1. 経費は**使わない**\n"
    )
    assert not pf.c3_scope_leak(pf.split_sections(text))


def test_a_table_header_is_not_a_definition():
    """表の見出し行の列名を定義と誤認しないこと(この誤検出は実際に出た)。"""
    text = "| 足 | **`sd_trade`** | n |\n|---|---|---|\n| 15 分 | 92.8 bp | 38,609 |\n"
    assert not pf.c2_symbol_defined_once(text)


# ----------------------------------------------------- 本番の事前登録 --------


@pytest.mark.skipif(not K1.exists(), reason="K1 の事前登録が無い")
def test_k1_passes_preflight():
    """**K1 は層 1 を通っていること。** 実行の前提(層 1 の不合格条件)。"""
    findings = pf.run(K1, K1_MEASURED)
    assert not findings, "\n".join(str(f) for f in findings)
