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
    """I-005 の再現: 族の直積のうち一部しか測っていない。

    L-052 で族が 3 軸(足 × 門 × 強さ)になったので、**全軸**を見る。
    旧版は足の軸しか見ておらず、独立監査 #8 に「隣の軸に同じ穴が残っている」と
    指摘された — **検査そのものが網羅性を欠いていた**。"""
    measured = tmp_path / "m.json"
    measured.write_text(
        json.dumps({
            "family": {"feet": [5, 15], "gates": ["s19/b24", "s19/b-"], "strengths": ["both"]},
            "cells": {"5|s19/b24|both": {"n": 1, "sd_trade_bp": 1.0}},
        }),
        encoding="utf-8",
    )
    findings = pf.c6_coverage("1.0", measured)
    assert "C6" in _codes(findings)
    assert "3 セルが未測定" in findings[0].detail


def test_c6_fires_when_the_family_size_in_the_text_disagrees(tmp_path: Path):
    """L-046 の再現: `h` を軸から外したのに §6 が族の大きさを直し忘れていた。"""
    measured = tmp_path / "m.json"
    measured.write_text(
        json.dumps({
            "family": {"feet": [5], "gates": ["a", "b"], "strengths": ["x", "y"]},
            "cells": {f"5|{g}|{s}": {"n": 1, "sd_trade_bp": 1.0}
                      for g in ("a", "b") for s in ("x", "y")},
        }),
        encoding="utf-8",
    )
    findings = pf.c6_coverage("族の大きさ = 1 × 2 × 3 = 6 である。1.0", measured)
    assert any("測定出力は **4** セル" in f.detail for f in findings)


def test_c6_fires_when_the_document_disagrees_with_the_measurement(tmp_path: Path):
    """I-005 の核心: 事前登録の数値が、測定出力と違う(手で書いた値が残っている)。"""
    measured = tmp_path / "m.json"
    measured.write_text(
        json.dumps({
            "family": {"feet": [15], "gates": ["s19/b24"], "strengths": ["both"]},
            "cells": {"15|s19/b24|both": {"n": 1, "sd_trade_bp": 112.6}},
        }),
        encoding="utf-8",
    )
    findings = pf.c6_coverage("15 分の sd_trade は **255.2 bp** である\n", measured)
    assert any("112.6" in f.detail for f in findings)


def test_c7_fires_on_a_bare_threshold_in_the_judgment(tmp_path: Path):
    """I-004 の再現: 判定条件に、出所タグの無い裸の数値バーが置かれる。"""
    text = "## 5. 採用基準\n\n### 5.3 候補と呼ぶ条件\n\n1. `mean(r) > 5 bp`(線 B)\n"
    assert "C7" in _codes(pf.c7_provenance_on_thresholds(pf.split_sections(text)))


# --------------------------------------------------------------- 陰性 --------


def test_c1_ignores_a_count_that_is_not_a_declaration():
    """「11 通りの組がある」「最大 144 通りの探索面」のように、**主張の直後に表が来ない**ものは
    「これからこの数だけ並べる」という宣言ではないので照合しない。
    K1 で実際に誤検出した。**誤検出を放置すると「どうせ誤検出」で本物を見逃す。**"""
    text = (
        "## 3. 族\n\n残るのは **11 通り**: a b c。\n\n"
        "**必ず入れる 3 つの参照点**:\n\n| 組 | 意味 |\n|---|---|\n"
        "| a | 1 |\n| b | 2 |\n| c | 3 |\n"
    )
    assert not pf.c1_counts_match(text, pf.split_sections(text))


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


# 2 回目の独立監査で出た**未処理の指摘**。トリアージで直したらここから消す。
# **「0 件」と主張する代わりに「既知の分だけ」と主張する**ことで、
# 新しい欠陥が入った瞬間に赤くなる一方、既知の未処理を隠さずに済む。
KNOWN_OPEN = {
    "「**判定区間の判定規則**」が事前登録に無い",       # 監査 2 回目 #13
    "「**信頼区間の算出方法**」が事前登録に無い",       # 監査 2 回目 #17
    "「**補助帰無の手順**」が事前登録に無い",           # 監査 2 回目 #26
}


@pytest.mark.skipif(not K1.exists(), reason="K1 の事前登録が無い")
def test_k1_preflight_has_only_the_known_open_findings():
    """**K1 は層 1 を通っていないこと自体は隠さない。**

    2 回目の独立監査で重大 18 件が出ており、K1 は実行できる状態にない。
    ここで「0 件」を主張すると、直っていないものを直ったことにしてしまう。
    そこで**既知の未処理と完全に一致すること**を主張する:

    - 新しい欠陥が入れば **知らない指摘が増えて赤くなる**
    - 既知の未処理を直せば **KNOWN_OPEN から消し忘れて赤くなる**

    どちらの向きにも効く。**K1 の実行可否は `KNOWN_OPEN` が空になってから。**
    """
    current = {f.detail for f in pf.run(K1, K1_MEASURED)}
    unexpected = current - KNOWN_OPEN
    assert not unexpected, "**新しい欠陥**:\n" + "\n".join(sorted(unexpected))
    fixed = KNOWN_OPEN - current
    assert not fixed, ("直ったのに KNOWN_OPEN に残っている(消すこと):\n"
                       + "\n".join(sorted(fixed)))


@pytest.mark.skipif(not K1.exists(), reason="K1 の事前登録が無い")
def test_k1_is_not_executable_while_findings_remain():
    """**未処理がある間は「実行してよい」と言えない**ことを、テストとして固定する。"""
    if KNOWN_OPEN:
        assert pf.run(K1, K1_MEASURED), "KNOWN_OPEN が空でないのに層 1 が 0 件を返している"


# ------------------------------------- L-054 で足した 3 つ(型を潰す検査) ----


def test_c8_fires_when_the_document_is_hand_edited(tmp_path: Path):
    """L-054: 数値を手で書ける限り、直した端から測定とずれる。

    **PREREG.md は生成物**であり、`.tmpl` + 測定出力から作り直せなければならない。
    ここでは「手で編集された文書」を再現して発火を見る。"""
    (tmp_path / "dispersion.json").write_text(
        json.dumps({"family": {"feet": [15], "gates": ["g"], "strengths": ["both"]},
                    "cells": {"15|g|both": {"n": 10, "sd_trade_bp": 112.6, "capped_share": 0.0}}}),
        encoding="utf-8")
    (tmp_path / "PREREG.md.tmpl").write_text("sd は {{cell:15|g|both.sd_trade_bp}} bp\n", encoding="utf-8")
    doc = tmp_path / "PREREG.md"
    doc.write_text("sd は 999 bp\n", encoding="utf-8")  # 手で書き換えられた状態
    findings = pf.c8_generated_not_typed(doc)
    assert "C8" in _codes(findings)
    assert "一致しない" in findings[0].detail


def test_c8_fires_when_a_reference_cannot_be_resolved(tmp_path: Path):
    """参照が解決できないのは、数値が欠けているのと同じ。黙って空にしない。"""
    (tmp_path / "dispersion.json").write_text(
        json.dumps({"family": {"feet": [15], "gates": ["g"], "strengths": ["both"]}, "cells": {}}),
        encoding="utf-8")
    (tmp_path / "PREREG.md.tmpl").write_text("{{cell:15|g|both.sd_trade_bp}}\n", encoding="utf-8")
    (tmp_path / "PREREG.md").write_text("x\n", encoding="utf-8")
    assert "C8" in _codes(pf.c8_generated_not_typed(tmp_path / "PREREG.md"))


def test_c8_is_silent_when_the_document_is_freshly_generated(tmp_path: Path):
    (tmp_path / "dispersion.json").write_text(
        json.dumps({"family": {"feet": [15], "gates": ["g"], "strengths": ["both"]},
                    "cells": {"15|g|both": {"n": 10, "sd_trade_bp": 112.6, "capped_share": 0.0}}}),
        encoding="utf-8")
    (tmp_path / "PREREG.md.tmpl").write_text("sd は {{cell:15|g|both.sd_trade_bp}} bp\n", encoding="utf-8")
    (tmp_path / "PREREG.md").write_text("sd は 112.6 bp\n", encoding="utf-8")
    assert not pf.c8_generated_not_typed(tmp_path / "PREREG.md")


def test_c9_fires_on_each_rule_that_was_actually_missing():
    """L-054: **書かれていないものは、読んでも見つからない。**

    2 回目の独立監査の重大 18 件のうち 4 件が「規則そのものが無い」だった。
    必須項目は**実際に抜けた実例からだけ**足す(想像で増やさない)。"""
    findings = pf.c9_required_sections("何も書いていない事前登録")
    assert len(findings) == len(pf.REQUIRED)
    assert any("判定区間の判定規則" in f.detail for f in findings)


def test_c9_is_silent_when_every_required_rule_is_present():
    text = "\n".join(f"### {marker}\n本文\n" for marker, _ in pf.REQUIRED)
    assert not pf.c9_required_sections(text)


def test_c10_fires_on_the_arithmetic_that_was_actually_wrong():
    """L-054 の実例: アブレーションの探索面を「144 通り」と書いたが、実際は 48 通り。
    **掛け算を 1 回すれば分かった。** 検査器が式を評価して突き合わせる。"""
    findings = pf.c10_computations_check_out("探索面は【計算: 2*3*2*4 = 144】通りある。")
    assert "C10" in _codes(findings)
    assert "48" in findings[0].detail


def test_c10_fires_on_the_significance_claim_that_was_backwards():
    """もう一つの実例: 「198 セルの最大の 95 点は 2.49 sd 相当」(実際は 3.65)。
    片側/両側と多重性を含む逆関数なので、**書く前に評価するしかない**。"""
    findings = pf.c10_computations_check_out("最大の 95 点は【計算: 0.95**(1/198) = 0.5】である。")
    assert "C10" in _codes(findings)


def test_c10_is_silent_when_the_computation_is_right():
    assert not pf.c10_computations_check_out("族は【計算: 6*11*3 = 198】セルである。")


def test_c10_rejects_an_expression_it_cannot_verify():
    """評価できない式を「計算した」と称せないこと。**印だけ付けて中身が無いのを防ぐ。**"""
    findings = pf.c10_computations_check_out("【計算: __import__('os').getpid() = 1】")
    assert "C10" in _codes(findings)
