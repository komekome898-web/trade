"""改良案 I1 の門 dev_setting(L-970)の試験: 引数の検めと、門の判断(建ての線の中心からの距離 ÷ 幅)。"""
import pytest

from bot.strategy.matilda_simple import BASE_PARAMS, PARAM_KEYS, MatildaSimple, _params


def _snap(dev, width=100.0, vola=10.0, entry=4):
    p = dict(BASE_PARAMS, dev_setting=dev, entry_setting=entry, break_delay=0)
    m = MatildaSimple(p)
    m.ind = {"vola": vola, "range_max": 1050.0, "range_min": 1050.0 - width, "range_max2": 1050.0,
             "range_min2": 1050.0 - width, "width": width, "center": 1000}
    return m._make_snap(1000.0)


def test_param_default_and_check():
    assert "dev_setting" in PARAM_KEYS and BASE_PARAMS["dev_setting"] is None
    _params(dict(BASE_PARAMS, dev_setting=0.49))
    with pytest.raises(ValueError):
        _params(dict(BASE_PARAMS, dev_setting=-0.1))
    with pytest.raises(ValueError):
        _params({k: v for k, v in BASE_PARAMS.items() if k != "dev_setting"})


@pytest.mark.parametrize("dev, ok", [(None, True), (0.3, True), (0.4, True), (0.41, False), (0.49, False)])
def test_gate_uses_entry_line_distance_over_width(dev, ok):
    # 建ての線 = 中心 ± 4 × 10 = ± 40、幅 100 → 0.4
    sn = _snap(dev)
    assert sn["dev_ok"] is ok
    assert sn["gate"] is True  # 他の門には触れない


def test_zero_width_is_closed_when_gate_set():
    assert _snap(0.1, width=0.0)["dev_ok"] is False
    assert _snap(None, width=0.0)["dev_ok"] is True
