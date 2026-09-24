"""scripts/check_bt_delegation.py: mechanical pre-audit checks on the backtest-env delegation."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("cbd", Path(__file__).resolve().parents[1] / "scripts" / "check_bt_delegation.py")
cbd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cbd)

LOG = "| L-407 | d | k | 「**C 案1**」 | x |\n| L-418 | d | k | 「**案1 共有**」 | x |\n"
DOC = ("## 0. 表\n| a | L-407「**C 案1**」+ L-418「**案1 共有**」 |\n## 1. 材料\n"
       "**周回の数え方と止める条件(…)**: 本文\n**要件**: 通過の判定(§0 の L-407・L-418 の行)はオーナーだけが変える。\n")
VER = "### 監査役の出力(逐語)\n1. [直す] 全文。\n### リードの処置\n(…)\n"


def test_clean_document_passes():
    assert cbd.check(DOC, LOG, VER) == []


def test_missing_owner_row_and_non_verbatim_quote():
    errs = cbd.check(DOC.replace("L-418「**案1 共有**」", "L-419「**案1 共有**」"), LOG, VER)
    assert any("L-419" in e and "行が無い" in e for e in errs)
    errs = cbd.check(DOC.replace("案1 共有", "案1 共有する"), LOG, VER)
    assert any("逐語で無い" in e for e in errs)


def test_owner_only_list_must_be_in_section_0():
    errs = cbd.check(DOC.replace("L-407・L-418 の行", "L-407・L-418・L-420 の行"), LOG + "| L-420 | d | k | q | x |\n", VER)
    assert any("L-420" in e and "§0 の表に無い" in e for e in errs)


def test_single_definition_and_no_abbreviated_auditor_output():
    errs = cbd.check(DOC + "**周回の数え方と止める条件(再)**: 二重\n", LOG, VER)
    assert any("定義が 2 回" in e for e in errs)
    errs = cbd.check(DOC, LOG, "### 監査役の出力(逐語)\n1. [直す] 前半(…)後半\n")
    assert any("(…)" in e for e in errs)


def test_quoted_ellipsis_in_auditor_text_is_not_a_cut():
    assert cbd.check(DOC, LOG, "### 監査役の出力(逐語)\n1. [聞く] 記録が「(…)」で切られている。\n") == []


def test_every_agent_call_in_the_script_carries_the_scrutiny_text():
    good = "const SCRUTINY = 'x'\nconst a = await agent(`作業 ${SCRUTINY}`, { label: `作る`, model: M })\n" \
           "const j = await agent(`判定。返す前の吟味: 数え直す`, { label: `盲検`, model: M })\n" \
           "const au = await agent(`検査`, { label: `監査役`, agentType: 'owner-auditor', model: M })\n"
    assert cbd.check_script(good) == []
    bad = good + "const t = await agent(`表を作る`, { label: `表:1`, model: M })\n"
    errs = cbd.check_script(bad)
    assert len(errs) == 1 and "表:1" in errs[0]
    auditor_with_parens = "const b = await agent(`検査`, { label: `監査役(表):1`, agentType: 'owner-auditor', model: M })\n"
    assert cbd.check_script(good + auditor_with_parens) == []
