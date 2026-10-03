"""参照と段階 G の片側だけの取引の分け方(`scripts/w4_measure/c2_ref_vs_g_cause.py` の D1〜D10)を、表を見る前に固める。"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("c2_ref_vs_g_cause", REPO / "scripts" / "w4_measure" / "c2_ref_vs_g_cause.py")
cz = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cz)

NONE, JOIN, N0, BOTH = cz.NONE, cz.JOIN, cz.N0, cz.BOTH


def mk(ws, acts, F=300, last=None):
    ws = np.array(ws, dtype=np.int64)
    return {"w": ws, "act": np.array(acts, dtype=np.int64), "F": F, "idx": {int(x): j for j, x in enumerate(ws)},
            "last": np.array(last if last is not None else [w + F - 60 for w in ws], dtype=np.int64)}


# ---------------------------------------------------------------- D2・D3 足の作り方
def _rows():
    # 5 分の区切り 0 の中の 5 行。t=60 の高値がヒゲを作る(bitFlyer に無い分)、t=240 は n_trades == 0
    t = [0, 60, 120, 180, 240]
    o = [100.0, 100.0, 100.5, 101.0, 101.0]
    h = [100.0, 103.0, 100.5, 101.0, 101.0]
    lo = [100.0, 100.0, 100.5, 101.0, 101.0]
    c = [100.0, 100.5, 101.0, 101.0, 101.0]
    nt = [5, 5, 5, 5, 0]
    b = {"t": np.array(t, dtype=np.int64), "o": np.array(o), "h": np.array(h), "l": np.array(lo), "c": np.array(c),
         "nt": np.array(nt, dtype=np.int64)}
    bf_t = np.array([0, 120, 180, 240], dtype=np.int64)
    return b, bf_t


def test_build_bars_four_ways_drop_the_right_rows():
    b, bf_t = _rows()
    got = {c: cz.build_bars(b, bf_t, 300, c, 0) for c in (NONE, JOIN, N0, BOTH)}
    for c in got:
        assert list(got[c]["w"]) == [0]
    # 最後の分: n0 を落とすと t=240 が抜ける
    assert [int(got[c]["last"][0]) for c in (NONE, JOIN, N0, BOTH)] == [240, 240, 180, 180]
    # 合図: t=60 の上ヒゲは結合で落ちる → 陽線・上ヒゲ(弱い売り)が消える
    assert cz.sig_at(got[NONE], 0) == -1 and cz.sig_at(got[N0], 0) == -1
    assert cz.sig_at(got[JOIN], 0) == 0 and cz.sig_at(got[BOTH], 0) == 0
    assert cz.sig_at(got[NONE], 300) == 0  # 足が無い区切りは 0


def test_window_rule_for_off_minute_rows():
    # 分の頭に無い行 t=270: 参照の区切りは ((270+59)//300)*300 = 300、段階 G は分の頭 240 に切り下げて区切り 0
    b = {"t": np.array([0, 270], dtype=np.int64), "o": np.array([1.0, 1.0]), "h": np.array([1.0, 1.0]),
         "l": np.array([1.0, 1.0]), "c": np.array([1.0, 1.0]), "nt": np.array([1, 1], dtype=np.int64)}
    bf_t = np.array([0, 240], dtype=np.int64)
    assert list(cz.build_bars(b, bf_t, 300, NONE, 0)["w"]) == [0, 300]
    assert list(cz.build_bars(b, bf_t, 300, JOIN, 0)["w"]) == [0, 300]  # 結合は分の頭で見るが、区切りは参照の式
    assert list(cz.build_bars(b, bf_t, 300, BOTH, 0)["w"]) == [0]


def test_lo_drops_earlier_rows():
    b, bf_t = _rows()
    assert int(cz.build_bars(b, bf_t, 300, NONE, 120)["last"][0]) == 240
    assert cz.sig_at(cz.build_bars(b, bf_t, 300, NONE, 120), 0) == 0


# ---------------------------------------------------------------- D4 機械
def test_machine_acts_on_previous_bar_signal_at_bar_end():
    bars = mk([0, 300, 600, 900, 1200], [1, 0, -1, 0, 0])
    tr, st = cz.machine(bars, lambda j: 100.0 + 10 * j)
    assert tr == [(600, 1, 1200, 110.0, 130.0)]
    assert st == [(600, 1), (1200, 0)]


def test_machine_previous_bar_is_previous_in_sequence_not_adjacent_window():
    bars = mk([0, 900], [-1, 0])  # 300・600 の区切りが無い
    tr, st = cz.machine(bars, lambda j: 1.0)
    assert st == [(1200, -1)]


def test_machine_same_side_does_nothing_and_no_price_skips():
    bars = mk([0, 300, 600, 900], [1, 1, 0, 0])
    _tr, st = cz.machine(bars, lambda j: 1.0)
    assert st == [(600, 1)]
    _tr, st = cz.machine(bars, lambda j: None if j == 1 else 1.0)
    assert st == [(900, 1)]


def test_ref_price_minute_is_last_minute_starting_at_or_before_E_minus_60():
    t = np.array([0, 60, 180], dtype=np.int64)
    assert cz.ref_price_minute(t, 300) == 2  # 240 以下で最後 = 180
    assert cz.ref_price_minute(t, 240) == 2
    assert cz.ref_price_minute(t, 239) == 1
    assert cz.ref_price_minute(t, 59) is None


def test_next_end_and_signal_window():
    bars = mk([0, 300, 900], [0, 0, 0])
    assert cz.next_end(bars, 300) == 1200
    assert cz.next_end(bars, 900) is None
    assert cz.signal_window(bars, 1200) == 300
    assert cz.signal_window(bars, 300) is None  # 1 つ前が無い
    assert cz.signal_window(bars, 900) is None  # 600 の足が無い


# ---------------------------------------------------------------- D7 帰属
@pytest.mark.parametrize("v,exp", [
    ({NONE: 1, JOIN: 0, N0: 1, BOTH: 0}, cz.CAT_A),
    ({NONE: 1, JOIN: 1, N0: 0, BOTH: 0}, cz.CAT_B),
    ({NONE: 1, JOIN: 0, N0: 0, BOTH: 0}, cz.CAT_AB_ANY),
    ({NONE: 1, JOIN: 1, N0: 1, BOTH: 0}, cz.CAT_AB_PAIR),
])
def test_attribute_from_ref_side(v, exp):
    assert cz.attribute(v, NONE, BOTH) == exp


def test_attribute_from_g_side_toggles_one_element_off():
    # P = 段階 G(both)。(a) だけ外す = n0、(b) だけ外す = join
    assert cz.attribute({NONE: 1, JOIN: 0, N0: 1, BOTH: 0}, BOTH, NONE) == cz.CAT_A
    assert cz.attribute({NONE: 1, JOIN: 1, N0: 0, BOTH: 0}, BOTH, NONE) == cz.CAT_B


# ---------------------------------------------------------------- D6・D8 分類
def _world_sig_join():
    # 参照の作り方では区切り 300 の合図 +1、結合すると 0
    w = [0, 300, 600, 900]
    return {NONE: mk(w, [0, 1, 0, 0]), N0: mk(w, [0, 1, 0, 0]), JOIN: mk(w, [0, 0, 0, 0]), BOTH: mk(w, [0, 0, 0, 0])}


def test_classify_signal_difference_join():
    assert cz.classify_action(_world_sig_join(), "ref", 900, 1) == (cz.KIND_SIG, cz.CAT_A)


def test_classify_signal_difference_from_g_side_n0():
    w = [0, 300, 600, 900]
    world = {NONE: mk(w, [0, 0, 0, 0]), JOIN: mk(w, [0, 0, 0, 0]), N0: mk(w, [0, -1, 0, 0]), BOTH: mk(w, [0, -1, 0, 0])}
    assert cz.classify_action(world, "g", 900, -1) == (cz.KIND_SIG, cz.CAT_B)


def test_classify_time_difference_join():
    full, cut = [0, 300, 600, 900], [0, 300, 900]
    world = {NONE: mk(full, [0, 1, 0, 0]), N0: mk(full, [0, 1, 0, 0]), JOIN: mk(cut, [0, 1, 0]), BOTH: mk(cut, [0, 1, 0])}
    assert cz.classify_action(world, "ref", 900, 1) == (cz.KIND_TIME, cz.CAT_A)
    assert cz.classify_action(world, "g", 1200, 1) == (cz.KIND_TIME, cz.CAT_A)


def test_classify_action_raises_when_own_signal_missing():
    with pytest.raises(RuntimeError):
        cz.classify_action(_world_sig_join(), "ref", 900, -1)


def _st(states):
    return (states, [x[0] for x in states])


def test_classify_trade_via_position_traces_origin():
    # 区切り 0 の合図 −1 は参照の作り方だけ(結合で消える)→ 参照は 200 で閉じ、段階 G は持ち続ける。
    # 区切り 200 の合図 +1 は両方 → 参照は 400 で入り、段階 G は同じ向きで何もしない
    F = 100
    w = [0, 100, 200, 300]
    world = {NONE: mk(w, [-1, 0, 1, 0], F), N0: mk(w, [-1, 0, 1, 0], F), JOIN: mk(w, [0, 0, 1, 0], F),
             BOTH: mk(w, [0, 0, 1, 0], F)}
    st = {"ref": _st([(100, 1), (200, 0), (400, 1)]), "g": _st([(100, 1)])}
    c = cz.classify_trade(world, st, "ref", 400, 1)
    assert c["kind"] == cz.KIND_POS and c["via_pos"] and c["cause"] == cz.CAT_A
    assert c["origin_t"] == 200 and c["origin_kind"] == cz.KIND_SIG and c["origin_side"] == "ref"


def test_classify_trade_direct_and_unknown_and_start():
    world = _world_sig_join()
    st = {"ref": _st([(900, 1)]), "g": _st([])}
    assert cz.classify_trade(world, st, "ref", 900, 1) == {"kind": cz.KIND_SIG, "cause": cz.CAT_A, "via_pos": False}
    # 両方に合図があり時刻も同じで、直前の持ち高も同じ → 不明
    w = [0, 300, 600, 900]
    same = {c: mk(w, [0, 1, 0, 0]) for c in (NONE, JOIN, N0, BOTH)}
    assert cz.classify_trade(same, {"ref": _st([(900, 1)]), "g": _st([])}, "ref", 900, 1)["cause"] == cz.UNKNOWN
    # 50 で参照だけ −1、100 で段階 G だけ +1 → 持ち高は 50 から違い続け、その前は無い(読み始め)
    c3 = cz.classify_trade(same, {"ref": _st([(50, -1), (600, 0), (900, 1)]), "g": _st([(100, 1)])}, "ref", 900, 1)
    assert c3 == {"kind": cz.KIND_POS, "cause": cz.OTHER_START, "via_pos": True}
    assert cz.origin_time({"ref": _st([(50, -1), (600, 0)]), "g": _st([(100, 1)])}, 900) is None


def test_action_side():
    st = _st([(100, 1), (200, 0), (300, -1)])
    assert cz.action_side(*st, 100) == 1
    assert cz.action_side(*st, 200) == -1
    assert cz.action_side(*st, 300) == -1


# ---------------------------------------------------------------- D1・D5 突き合わせ
def test_split_year_matches_match_script_counts():
    ref = [(100, 1, 200, 5.0), (300, -1, 400, -2.0), (500, 1, 600, 1.0)]
    g = [(100, 1, 250, 3.0), (300, -1, 400, -2.0), (700, -1, 800, 4.0)]
    common, r_only, g_only = cz.split_year(ref, g)
    m = cz.mm.match_year(ref, g)
    assert (len(common), len(r_only), len(g_only)) == (m["common_n"], m["r_only_n"], m["g_only_n"])
    assert r_only == [(500, 1, 600, 1.0)] and g_only == [(700, -1, 800, 4.0)]


def test_pair_shifts_one_to_one_smallest_first_same_side_within_foot():
    F = 300
    r_only = [(1000, 1, 0, 1.0), (2000, -1, 0, 2.0), (5000, 1, 0, 3.0)]
    g_only = [(1300, 1, 0, 4.0), (1100, 1, 0, 5.0), (2100, 1, 0, 6.0), (5301, 1, 0, 7.0)]
    pairs, rr, gg = cz.pair_shifts(r_only, g_only, F)
    assert pairs == [(r_only[0], g_only[1])]  # 差 100 が 300 より先。2000 は向きが違う。5000↔5301 は差が足を越える
    assert rr == [r_only[1], r_only[2]]
    assert gg == [g_only[0], g_only[2], g_only[3]]
    pairs2, _, _ = cz.pair_shifts([(1000, 1, 0, 1.0)], [(1300, 1, 0, 1.0)], F)
    assert len(pairs2) == 1  # 差がちょうど 1 足は組む


# ---------------------------------------------------------------- D9 値の違いの元
def test_leg_cause():
    g_bars = mk([300], [0], 300, last=[480])
    bfv_t = np.array([480, 540], dtype=np.int64)
    b = {"fl": np.array([480], dtype=np.int64), "nt": np.array([3], dtype=np.int64)}
    assert cz.leg_cause(b, bfv_t, g_bars, 600) == "(c): Binance にその分が無い"
    b2 = {"fl": np.array([480, 540], dtype=np.int64), "nt": np.array([3, 0], dtype=np.int64)}
    assert cz.leg_cause(b2, bfv_t, g_bars, 600) == "(c): n_trades == 0"
    assert cz.leg_cause(b2, np.array([420], dtype=np.int64), g_bars, 600) == "(e) または不明"
    assert cz.leg_cause(b2, np.array([480], dtype=np.int64), g_bars, 600) == cz.UNKNOWN
