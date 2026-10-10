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


# ---------------------------------------------------------------- 改良案 I6 の門 line_setting(L-974)
def _snap_line(ls, bd=None, bu=None, vola=10.0):
    p = dict(BASE_PARAMS, line_setting=ls, entry_setting=4, break_delay=1)
    m = MatildaSimple(p)
    m._up, m._dn = ([bu] if bu is not None else []), ([bd] if bd is not None else [])
    m.ind = {"vola": vola, "range_max": 1050.0, "range_min": 950.0, "range_max2": -1e9 if bu is None else 1050.0,
             "range_min2": 1e9 if bd is None else 950.0, "width": 100.0, "center": 1000}
    return m._make_snap(1000.0)


def test_line_param_check():
    assert BASE_PARAMS["line_setting"] is None
    _params(dict(BASE_PARAMS, line_setting=4.0))
    with pytest.raises(ValueError):
        _params(dict(BASE_PARAMS, line_setting=-1))


@pytest.mark.parametrize("ls, ok_long, ok_short", [(None, True, True), (3.0, True, True), (4.0, True, False), (6.0, True, False), (6.5, False, False)])
def test_line_gate_per_side(ls, ok_long, ok_short):
    # 建ての線 = 1000 ∓ 40。下のブレイクの線 900 → 買いの距離 60 = 6 ボラ、上のブレイクの線 1075 → 売りの距離 35 = 3.5 ボラ
    sn = _snap_line(ls, bd=900.0, bu=1075.0)
    assert sn["line_ok"][1] is ok_long and sn["line_ok"][-1] is ok_short


def test_line_gate_open_without_line():
    sn = _snap_line(10.0, bd=None, bu=None)
    assert sn["line_ok"] == {1: True, -1: True}
