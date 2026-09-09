"""規約 `research-protocol` の規則が散文から静かに消えないように固定する。

今週だけで、規則が 1 箇所にしか無かったせいで飛ばされた例が複数出た。
**中身の良し悪しは測れないので、要求が存在することだけを見る。**

ここで固定するのは 2026-09-09 に追加された 2 群:

- **§1 出所の 3 分類と記号の一意性**(I-004。同じ記号 `sd` を 3 つの量に使い回した)
- **§3.1 単位の位置に合うコストだけを扱う**(L-048。上流の単位に下流の制約を持ち込んだ)
"""
from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PROTOCOL = REPO / ".claude" / "skills" / "research-protocol" / "SKILL.md"
K1_PREREG = REPO / "docs" / "PHASE2" / "K1" / "PREREG.md"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_provenance_classes_and_who_assumed_it():
    """数値には 一次資料 / 実測 / 仮定 の印を付け、**仮定には誰の仮定かを書く**。
    「リードの記憶は仮定である」を名指しで残す — ここが I-004 で 2 回falsifyされた点。"""
    text = _text(PROTOCOL)
    for token in ("一次資料", "実測", "仮定", "誰の仮定か"):
        assert token in text, token
    assert "リードの記憶は「仮定」である" in text


def test_symbol_uniqueness_rule():
    """量が変わったら記号も変える。訂正は古い定義を消してから。"""
    text = _text(PROTOCOL)
    assert "記号を別の量に使い回さない" in text or "使い回さない" in text
    assert "古い定義を消してから" in text


def test_cost_belongs_to_the_stage_that_can_measure_it():
    """§3.1: 上流の単位ではコストを引かず、水準も仮定しない。

    L-048 の核心は「**外すのはその数字ではなくコストという入力そのもの**」で、
    古い数字を新しい数字に差し替えるだけでは同じ誤りが 1 段ずれて残る。"""
    text = _text(PROTOCOL)
    assert "3.1" in text
    assert "上流" in text and "下流" in text
    assert "水準を仮定もしない" in text or "水準も仮定しない" in text
    # 移す先を書かずに外すと、コストの検査が忘れられる
    assert "関門" in text


def test_upstream_units_are_exempt_from_the_net_expectancy_bar():
    """§4 の採用基準にも例外が書かれていること。
    §3.1 だけに書くと、§4 のチェックリストを見た回で復活する。"""
    text = _text(PROTOCOL)
    bar = text.index("ネット期待値バー")
    assert "上流の単位" in text[bar : bar + 400]


def test_upstream_negative_is_scoped_by_mde_not_by_a_bar():
    """バーが無い単位では **MDE がそのまま陰性の射程**になる。
    これが無いと、バーを外した瞬間に陰性 / 不明の区別まで一緒に消える。"""
    assert "MDE を陰性の射程" in _text(PROTOCOL) or "MDE を超える効果は不在" in _text(PROTOCOL)


def test_k1_prereg_carries_no_fee_bar():
    """K1(上流の単位)の事前登録に、経費由来の判定バーが残っていないこと。

    L-048 で削除した具体物を名指しで禁じる — 抽象的な規則だけだと、
    次の改訂で「今度の数字は妥当だから」と戻ってくる。"""
    text = _text(K1_PREREG)
    assert K1_PREREG.exists()
    # 削除した 3 本の線の数値バーが、判定条件として復活していないこと
    assert "mean(r) > 5 bp" not in text
    assert "MDE > 5 bp" not in text
    # 経費を扱わない宣言と、移した先が書かれていること
    assert "経費は**本単位に一切入れない**" in text or "経費を一切含んでいない" in text
    assert "L-048" in text


def test_preparatory_measurements_are_held_to_the_same_standard():
    """§1.1: 事前登録の数値を作る測定にも、定義との突き合わせ・サニティ・
    独立再現・網羅性を課す(I-005)。

    K1 では準備測定が §4.2 の決済ルールの片方の枝を実装しておらず、その値が
    事前登録に載り、オーナーの指示を覆す根拠にまでなっていた。"""
    text = _text(PROTOCOL)
    assert "1.1" in text
    assert "準備測定も測定である" in text
    # 4 つの要求がすべて残っていること
    assert "条項ごとの突き合わせ" in text or "条項を 2 つ読むだけ" in text
    assert "決定を覆す測定は、独立に再現するまで根拠にしない" in text
    assert "網羅性" in text


def test_k1_numbers_and_family_are_enforced_by_the_preflight():
    """事前登録の数値・族の大きさ・網羅性の照合は、**出荷前検査に一本化した**。

    ここに同じ検査を書くと、族の形が変わるたびに 2 箇所を直すことになり、
    片方だけ直して食い違う(**まさに I-005 と L-052 で起きた失敗**)。
    実体は `scripts/preflight_prereg.py` の C6 にあり、
    `tests/test_preflight_prereg.py` が「過去の欠陥で発火すること」まで固定している。
    本テストは**その一本化が外れていないこと**だけを見る。
    """
    import sys

    sys.path.insert(0, str(REPO / "scripts"))
    import preflight_prereg as pf

    assert pf.c6_coverage.__doc__ and "網羅性" in pf.c6_coverage.__doc__
    # **K1 が層 1 を通っているかは、ここでは主張しない。**
    # 実行可否の判定は `tests/test_preflight_prereg.py` の KNOWN_OPEN 側に一本化してある
    # (2 箇所で同じことを主張すると、片方だけ直して食い違う = I-005 と同じ失敗)。
    # ここが見るのは「網羅性の検査が出荷前検査側に存在すること」だけ。
    assert "C6" in pf.CHECKS and "C8" in pf.CHECKS
