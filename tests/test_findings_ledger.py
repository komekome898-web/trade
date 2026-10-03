"""知見台帳の検査(`scripts/check_findings_ledger.py`)が、合意 L-603〜L-607 の決まりで実際に止まることを固定する。"""
from __future__ import annotations

import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "check_findings_ledger", REPO / "scripts" / "check_findings_ledger.py"
)
cfl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cfl)

GOOD_ROW = """
## 観察

### K-001 見出し
- 観察: 短く持った取引で稼ぎ、長く持った取引で失っている
- 対象: 仕組み
- 出所: `docs/RESEARCH/FINDINGS_LEDGER.md` の表 1
- 測った日: 2026-10-03
- 射程: Binance の 5 分足、2017-08〜2023-12
- 大きさ: +3.2bp / 取引
- 確かさ: 未監査
- 監査: なし
- 否定を含む: いいえ
- 渡す先: カツオ(ヒゲ逆張り)の降り方の改良
- 次の問い: 長く持ったときの降り方を変えて測る
- 状態: 開いている
"""

GOOD_CARD = """
## カード

### カード: カツオ(ヒゲ逆張り、カード 2)
- 状態: 測定中
- 場面ごとの効き: K-001
- なぜ: 未
- 安定: 未
- 重なり: 未
- 経費と約定: 未
- bitFlyer で効くか: 未
- 改良の周: 0(この節)
- 次に打てる手: 長く持ったときの降り方を変える
"""


def _errs(text: str) -> list[str]:
    return cfl.check_ledger_text(text, repo=REPO)


def test_good_row_and_card_pass():
    assert _errs(GOOD_ROW + GOOD_CARD) == []


def test_real_ledger_passes():
    assert _errs(cfl.DEFAULT_LEDGER.read_text(encoding="utf-8")) == []


def test_examples_in_fences_are_not_counted():
    text = "```\n### K-001 x\n- 観察: 知見なし\n```\n"
    assert _errs(text) == []


def test_missing_field_stops():
    errs = _errs(GOOD_ROW.replace("- 次の問い: 長く持ったときの降り方を変えて測る\n", ""))
    assert any("次の問い" in e and "無い" in e for e in errs)


def test_no_finding_as_exit_stops():
    for bad in ("知見なし", "言えない", "なし"):
        errs = _errs(GOOD_ROW.replace("長く持ったときの降り方を変えて測る", bad))
        assert errs, bad


def test_kikyakuzumi_anywhere_stops():
    errs = _errs(GOOD_ROW.replace("短く持った取引で稼ぎ", "既に棄却済みの形で、短く持った取引で稼ぎ"))
    assert any("棄却済み" in e for e in errs)


def test_certainty_enum_and_audited_needs_record():
    assert _errs(GOOD_ROW.replace("確かさ: 未監査", "確かさ: たぶん"))
    errs = _errs(GOOD_ROW.replace("確かさ: 未監査", "確かさ: 監査済"))
    assert any("監査の記録" in e for e in errs)
    ok = GOOD_ROW.replace("確かさ: 未監査", "確かさ: 監査済").replace("監査: なし", "監査: ACTION_LOG 079")
    assert _errs(ok) == []


def test_before_zensute_stops():
    errs = _errs(GOOD_ROW.replace("2026-10-03", "2026-09-07"))
    assert any("全捨て" in e for e in errs)


def test_negative_needs_period_in_scope():
    neg = GOOD_ROW.replace("否定を含む: いいえ", "否定を含む: はい")
    assert _errs(neg) == []
    errs = _errs(neg.replace("Binance の 5 分足、2017-08〜2023-12", "Binance の 5 分足"))
    assert any("射程" in e for e in errs)


def test_source_must_exist():
    errs = _errs(GOOD_ROW.replace("docs/RESEARCH/FINDINGS_LEDGER.md", "docs/NO_SUCH_FILE.md"))
    assert any("リポジトリに無い" in e for e in errs)
    errs = _errs(GOOD_ROW.replace("`docs/RESEARCH/FINDINGS_LEDGER.md`", "どこか"))
    assert any("パス" in e for e in errs)


def test_state_reference_must_exist():
    errs = _errs(GOOD_ROW.replace("状態: 開いている", "状態: 覆った(K-009)"))
    assert any("K-009" in e for e in errs)
    assert _errs(GOOD_ROW.replace("状態: 開いている", "状態: しまった"))


def test_duplicate_id_stops():
    assert any("2 回" in e for e in _errs(GOOD_ROW + GOOD_ROW.replace("## 観察\n", "")))


def test_closing_card_is_heavy():
    closed = GOOD_CARD.replace("状態: 測定中", "状態: 閉じた")
    errs = _errs(GOOD_ROW + closed)
    assert any("改良の周が 0" in e for e in errs)
    assert _errs(GOOD_ROW + closed.replace("改良の周: 0", "改良の周: 2")) == []
    errs = _errs(GOOD_ROW + closed.replace("改良の周: 0", "改良の周: 2").replace(
        "次に打てる手: 長く持ったときの降り方を変える", "次に打てる手: なし"))
    assert any("次に打てる手" in e for e in errs)


def test_card_axis_reference_must_exist():
    errs = _errs(GOOD_ROW + GOOD_CARD.replace("場面ごとの効き: K-001", "場面ごとの効き: K-002"))
    assert any("K-002" in e for e in errs)


def test_report_needs_section_with_next_move():
    ledger = GOOD_ROW
    assert cfl.check_report_text("# 報告\n## なぜ\nx\n", ledger)
    ok = "# 報告\n## 知見台帳に足した行\n- K-001。次の手: 降り方を変えて測る\n## 限界\n"
    assert cfl.check_report_text(ok, ledger) == []
    assert cfl.check_report_text(ok.replace("次の手", "次"), ledger)
    assert cfl.check_report_text(ok.replace("K-001", "K-005"), ledger)
