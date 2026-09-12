"""意図とロジックの突き合わせ(`INTENT_MAP.md`)が規約から消えないようにする。

オーナー規定 2026-09-09(L-043): 結果が悪いときの原因は
**「機構にエッジが無い」「機構の構築が戦略意図を反映していない」「機構のバグ」**の 3 つで、
**検証を進めてからでは分離できない**。だから後の 2 つは測る前に潰す。

今週の教訓がここにも効く: **散文にしか無い規則は静かに消える**。
規則が 3 箇所(規約・プロトコル・委任)に揃っていることを固定する
(旧テンプレート `docs/PHASE2_TEMPLATES.md` §8 は 2026-09-12 の文書整理で
`research-protocol` skill §0.5/§15 に統合され、独立した入口ではなくなった)。
中身の良し悪しは測れないので、**要求が存在すること**だけを見る。
"""
from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]

PROTOCOL = REPO / ".claude" / "skills" / "research-protocol" / "SKILL.md"
DELEGATION = REPO / ".claude" / "skills" / "delegated-study" / "SKILL.md"
CLAUDE_MD = REPO / "CLAUDE.md"
WORKED_EXAMPLE = REPO / "docs" / "legacy" / "KATSUO_INTENT_MAP.md"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


@pytest.mark.parametrize("path", [PROTOCOL, DELEGATION, CLAUDE_MD])
def test_the_requirement_is_stated_wherever_a_unit_starts(path: Path):
    """単位を始めうる 4 つの入口すべてに要求が書かれていること。
    1 箇所だけだと、別の入口から入った回で飛ばされる。"""
    assert "INTENT_MAP" in _text(path), path.name


def test_the_protocol_orders_it_before_pre_registration():
    """**事前登録より前**であることが要点。後だと結果を見てから意図を書ける。"""
    text = _text(PROTOCOL)
    assert "§0.5" in text or "0.5 意図" in text
    intent = text.index("意図とロジックの突き合わせ")
    prereg = text.index("## 1. 事前登録")
    assert intent < prereg, "意図合わせが事前登録より後ろに来ている"
    assert "事前登録を書かない" in text or "受理しない" in text


def test_the_three_causes_are_named_verbatim():
    """3 つの原因を名指ししていること。抽象化すると運用で流れる。"""
    for path in (PROTOCOL, CLAUDE_MD):
        text = _text(path)
        assert "エッジが無い" in text, path.name
        assert "戦略意図を反映していない" in text, path.name
        assert "バグ" in text, path.name


def test_the_four_verdicts_exist_with_the_proxy_case():
    """○ / △代理 / ✕未実装 / ＋意図に無い実装 の 4 つ。
    とくに **△代理** と **＋意図に無い実装** が要る —
    この 2 つが無い突き合わせは「実装されているか」しか見ておらず、
    今回のカツオ(ヒゲは清算の代理)を捕まえられない。"""
    text = _text(PROTOCOL)
    assert "代理" in text
    assert "未実装" in text
    assert "意図に無い" in text


def test_a_negative_without_the_map_is_downgraded_to_unknown():
    """**陰性と不明を分ける**規律(CLAUDE.md §5.2)との接続。
    代理や未実装が残ったままの陰性は陰性ではない。"""
    text = _text(PROTOCOL)
    assert "陰性ではなく不明" in text or "陰性ではなく不明である" in text


def test_the_map_must_be_built_from_the_code_side_too():
    """意図 → 実装 の一方向だけでは **＋(意図に無い実装)を見落とす**。
    カツオでは決済の固定ドル階段と 2 本目の指値がそれだった。"""
    assert "見落とす" in _text(PROTOCOL)


def test_the_worked_example_exists_and_carries_all_four_verdicts():
    """手本が無い規約は読まれない。カツオの表が 4 つの印を実際に使っていること。"""
    text = _text(WORKED_EXAMPLE)
    for mark in ("○", "△", "✕", "＋"):
        assert mark in text, mark
    # 3 つの原因への言及と、意図の出所が書かれていること
    assert "エッジが無い" in text
    assert "OWNER_LOG" in text or "L-024" in text
