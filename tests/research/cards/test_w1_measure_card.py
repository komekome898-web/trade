"""The critic's fix 5 (the lead's answers 2 and 3, 2026-10-02).

2: no effect of interest in stages 2 and 3: every mean carries its 95%
interval's two ends and its MDE, and the word verdict reads 未判定.
3: vr_q_bars, day_zone and the reference declarations are fixed in CARD.md
(測定の設定) and `measure_card` reads them from there; a run made with other
declarations is refused."""
from __future__ import annotations

import inspect

import pytest

from bot.bt.data.reference import reference_series
from bot.research.cards import CardError, cardmd, run_card
from bot.research.cards.measure import NO_VERDICT, measure, measure_card

import w1_synth as W

SETTINGS = ("- vr_q_bars: 5 | 出所: 試験の値(測定の値ではない)\n"
            "- day_zone: Asia/Tokyo | 出所: 試験\n"
            "- 参照: S | lag_ns: 0 | 場面: category | 出所: " + W.DECL_T1["S"]["source"])


def _card(tmp_path, settings=SETTINGS):
    p = tmp_path / "CARD.md"
    p.write_text(f"# カード\n\n## 測定の設定\n{settings}\n", encoding="utf-8")
    return str(p)


@pytest.fixture(scope="module")
def small():
    bars, S, _s = W.t1_input()
    return bars[:5 * 1440], S


def test_measure_card_uses_the_settings_of_the_card(small, tmp_path):
    bars, S = small
    path = _card(tmp_path)
    st, problems = cardmd.settings(cardmd.parse(open(path, encoding="utf-8").read()))
    assert problems == []
    run = run_card(W.Always(), bars, references={"S": S}, declarations=st.declarations, venue="synthetic",
                   symbol="T1")
    out = measure_card(path, run, seed=W.SEED_BOOT, control_seed=W.SEED_CONTROL, regimes=None,
                       daily_path=str(tmp_path / "d.csv"))
    assert out["settings"]["day_zone"] == "Asia/Tokyo" and out["daily"]["zone"] == "Asia/Tokyo"
    assert out["settings"]["vr_q_bars"] == 5 and "vr_1h" in out["scenes"] and "ref:S" in out["scenes"]
    assert out["settings"]["from_card"]["declarations"]["S"] == W.DECL_T1["S"]
    m = out["overall"]["mean_pct"]
    assert m["ci"][0] < m["ci"][1] and m["mde"] > 0 and m["verdict"] == NO_VERDICT


def test_a_run_with_other_declarations_is_refused(small, tmp_path):
    bars, S = small
    other = {"S": {"lag_ns": 0, "source": "別の出所"}}  # the same lag, another source: not what the card fixed
    S2 = reference_series("S", list(zip(S.times_ns, S.values)), declarations=other)
    run = run_card(W.Always(), bars, references={"S": S2}, declarations=other, venue="synthetic", symbol="T1")
    path = _card(tmp_path)
    with pytest.raises(CardError, match="not the ones its settings declare"):
        measure_card(path, run, seed=1, control_seed=2, regimes=None, daily_path=str(tmp_path / "d.csv"))
    no_source = _card(tmp_path, SETTINGS.replace(" | 出所: 試験\n", "\n"))
    with pytest.raises(CardError, match="cannot be read"):
        measure_card(no_source, run, seed=1, control_seed=2, regimes=None, daily_path=str(tmp_path / "d.csv"))


def test_no_effect_of_interest_is_taken():
    assert "interest_bp" not in inspect.signature(measure).parameters
    assert "interest_bp" not in inspect.signature(measure_card).parameters
