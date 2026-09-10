"""H3 の分解(`docs/PHASE2/K1/H3_DECOMP_PREREG.md` §1)の規則をテストで固定する。

1. EE は原典の取引そのもの(k+1 が無い末尾の取引を除く)
2. 無効化を外した土台では DD = 第 12 部 ② の機構(`delay_signals` + `simulate`)と取引ごとに一致
3. 4 腕の取引数は同一で、DE / ED の値付けは定義どおり
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import measure_katsuo_delay_decomp as dec  # noqa: E402
import measure_katsuo_effect as eff  # noqa: E402
from test_k1_delay_entry import walk  # noqa: E402


def test_ee_is_the_original_and_arms_share_trades():
    bars = walk(30_000, seed=61)
    sigs = eff.signals(bars, 19.0, 24.0)
    for keep in (None, "weak", "strong"):
        tr = eff.simulate(bars, sigs, keep)
        arms, dropped, _z = dec.reprice(bars, sigs, tr)
        assert len(tr) - dropped == len(arms["EE"]) and dropped <= 1
        assert len({len(arms[a]) for a in dec.ARMS}) == 1
        for (i, r, h, w), (i2, r2, h2, w2) in zip(tr, arms["EE"]):
            assert (i, h, w) == (i2, h2, w2) and math.isclose(r, r2, abs_tol=1e-9)


def test_dd_matches_delayed_mechanism_without_invalidation():
    bars = walk(60_000, seed=63)
    for flip in (False, True):
        sigs = eff.signals(bars, 19.0, 24.0, flip_body=flip)
        for keep in (None, "weak", "strong"):
            tr = eff.simulate(bars, sigs, keep, use_invalid=False)
            arms, _d, _z = dec.reprice(bars, sigs, tr)
            mech = eff.simulate(bars, eff.delay_signals(sigs), keep, use_invalid=False)
            assert len(mech) == len(arms["DD"]) > 100
            for (i, r, h, w), (mi, mr, mh, mw) in zip(arms["DD"], mech):
                assert mi == i + 1 and mh == h and mw == w
                assert math.isclose(r, mr, abs_tol=1e-9)


def test_de_and_ed_pricing():
    bars = walk(20_000, seed=65)
    close = [b[4] for b in bars]
    sigs = eff.signals(bars, 19.0, 24.0)
    tr = eff.simulate(bars, sigs, None)
    arms, _d, zero_de = dec.reprice(bars, sigs, tr)
    n_zero = 0
    for (i, r_de, h, _w), (_i2, r_ed, _h2, _w2) in zip(arms["DE"], arms["ED"]):
        pos = sigs[i][0]
        k = i + h
        assert math.isclose(r_de, pos * (close[k] / close[i + 1] - 1.0) * 1e4, abs_tol=1e-9)
        assert math.isclose(r_ed, pos * (close[k + 1] / close[i] - 1.0) * 1e4, abs_tol=1e-9)
        if k == i + 1:
            n_zero += 1
            assert r_de == 0.0
    assert n_zero == zero_de
