"""第 5 周(`docs/PHASE2/K1/ROUND5_PREREG.md` §3)の規則をテストで固定する。

1. (a') 決済理由別の (n × 分解量) の重み付き和が、全体の分解量(第 13 部と同じ式)と一致する
2. (c)-iii 経路の h = 保有 での値が、取引の機構リターンと一致する(決済は終値で行われるので、
   どの決済理由でも成り立つはず)
3. 層の割り当て(ヒゲ/実体比・ヒゲ長・保有・局所ボラ三分位)が定義どおり(境界値を含む)
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import measure_katsuo_delay_decomp as dec  # noqa: E402
import measure_katsuo_effect as eff  # noqa: E402
import measure_katsuo_round5 as r5  # noqa: E402
from test_k1_delay_entry import walk  # noqa: E402


def _cell_decomp(arms):
    """第 13 部と同じ式(`measure_katsuo_delay_decomp.main` の decomp_bp)を独立に計算する。"""
    ee, de, ed = arms["EE"], arms["DE"], arms["ED"]
    n = len(ee)
    return {"entry_delay": sum(b[1] - a[1] for a, b in zip(ee, de)) / n,
            "exit_delay": sum(b[1] - a[1] for a, b in zip(ee, ed)) / n}


def test_reason_weighted_sums_reproduce_whole_cell_decomposition():
    bars = walk(60_000, seed=71)
    for flip, use_invalid in ((False, True), (True, False), (True, True)):
        sigs = eff.signals(bars, 19.0, 24.0, flip_body=flip)
        for keep in (None, "weak", "strong"):
            tr = eff.simulate(bars, sigs, keep, use_invalid=use_invalid)
            if len(tr) < 30:
                continue
            arms, _dropped, _z = dec.reprice(bars, sigs, tr)
            n = len(arms["EE"])
            whole = _cell_decomp(arms)
            years = [0] * len(bars)                    # 年は本テストの対象外なのでダミー
            reasons = r5.split_by_reason(arms, years)
            w_entry = sum(v["n"] * v["entry_delay_exact"] for v in reasons.values()) / n
            w_exit = sum(v["n"] * v["exit_delay_exact"] for v in reasons.values()) / n
            assert sum(v["n"] for v in reasons.values()) == n
            assert math.isclose(w_entry, whole["entry_delay"], abs_tol=1e-9)
            assert math.isclose(w_exit, whole["exit_delay"], abs_tol=1e-9)
            if not use_invalid:
                assert "invalidated" not in reasons


def test_path_at_hold_equals_mechanism_return():
    bars = walk(40_000, seed=73)
    close = [b[4] for b in bars]
    n_bars = len(bars)
    for flip in (False, True):
        sigs = eff.signals(bars, 19.0, 24.0, flip_body=flip)
        for use_invalid in (True, False):
            tr = eff.simulate(bars, sigs, "strong", use_invalid=use_invalid)
            assert len(tr) > 20
            checked = 0
            for i, ret, hold, _why in tr:
                if i + hold >= n_bars:
                    continue                            # 4 腕と同じく末尾は外す(reprice と同じ扱い)
                pr = r5.path_return(close, sigs[i][0], i, hold)
                assert math.isclose(pr, ret, abs_tol=1e-9), (i, hold, pr, ret)
                checked += 1
            assert checked > 20


def test_layer_bin_assignment_matches_definition():
    # ヒゲ/実体比 r = w / |実体|。(1,1.5],(1.5,2],(2,3],(3,+)。実体 0 は最後のビン
    assert r5.ratio_bin_of(wbp=15.0, bodybp=10.0) == "(1,1.5]"           # r = 1.5 ちょうど → 含む
    assert r5.ratio_bin_of(wbp=15.0001, bodybp=10.0) == "(1.5,2]"        # わずかに超える → 次のビン
    assert r5.ratio_bin_of(wbp=20.0, bodybp=10.0) == "(1.5,2]"           # r = 2.0 ちょうど → 含む
    assert r5.ratio_bin_of(wbp=30.0, bodybp=10.0) == "(2,3]"             # r = 3.0 ちょうど → 含む
    assert r5.ratio_bin_of(wbp=30.0001, bodybp=10.0) == "(3,+)"
    assert r5.ratio_bin_of(wbp=50.0, bodybp=0.0) == "(3,+)"              # 実体 0 → 最後のビン

    # ヒゲ長 bp。[19,24),[24,40),[40,80),[80,+)(事前登録の 3 ビンに [19,24) を足したもの)
    assert r5.wick_bin_of(19.0) == "[19,24)"
    assert r5.wick_bin_of(23.999) == "[19,24)"
    assert r5.wick_bin_of(24.0) == "[24,40)"
    assert r5.wick_bin_of(39.999) == "[24,40)"
    assert r5.wick_bin_of(40.0) == "[40,80)"
    assert r5.wick_bin_of(79.999) == "[40,80)"
    assert r5.wick_bin_of(80.0) == "[80,+)"
    assert r5.wick_bin_of(500.0) == "[80,+)"

    # 保有本数。[1,3),[3,10),[10,30),[30,+)
    assert r5.hold_bin_of(1) == "[1,3)"
    assert r5.hold_bin_of(2) == "[1,3)"
    assert r5.hold_bin_of(3) == "[3,10)"
    assert r5.hold_bin_of(9) == "[3,10)"
    assert r5.hold_bin_of(10) == "[10,30)"
    assert r5.hold_bin_of(29) == "[10,30)"
    assert r5.hold_bin_of(30) == "[30,+)"
    assert r5.hold_bin_of(1000) == "[30,+)"

    # 局所ボラ三分位。edges = (q1, q2)、v < q1 → low、q1 <= v < q2 → mid、v >= q2 → high
    edges = (10.0, 20.0)
    assert r5.vol_tercile_of(9.999, edges) == "low"
    assert r5.vol_tercile_of(10.0, edges) == "mid"
    assert r5.vol_tercile_of(19.999, edges) == "mid"
    assert r5.vol_tercile_of(20.0, edges) == "high"
    assert r5.vol_tercile_of(1000.0, edges) == "high"
