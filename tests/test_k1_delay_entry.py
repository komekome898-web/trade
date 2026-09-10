"""H3(`docs/PHASE2/K1/H3_PREREG.md` §2)の規則をテストで固定する。

1. `delay_signals()` は行動(向き・ライン・強さ)を 1 本ずらし、色は実際の足のものを保つ。先頭はシグナル無し
2. 遅らせた機構では、各取引の建玉足 `entry_i` に**前の足**のシグナルがあり、リターンは `close[entry_i]`(= 次の足の終値)から計算される
3. 遅らせない経路は原典と同一(`delay_signals` を通さなければ何も変わらない)
4. シグナル数は遅らせても同じ(先頭・末尾を除く)
"""
from __future__ import annotations

import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import measure_katsuo_effect as eff  # noqa: E402

PRICE = 10_000.0


def walk(n: int, seed: int, sd_bp: float = 20.0, wick_bp: float = 25.0):
    rng = random.Random(seed)
    bars, c = [], PRICE
    for i in range(n):
        o = c
        c = o * (1.0 + rng.gauss(0.0, sd_bp) / 1e4)
        top = max(o, c) + abs(rng.gauss(0.0, wick_bp)) * o / 1e4
        bot = min(o, c) - abs(rng.gauss(0.0, wick_bp)) * o / 1e4
        bars.append((60 * i, o, top, bot, c))
    return bars


def test_delay_shifts_action_but_keeps_actual_colour():
    bars = walk(20_000, seed=51)
    sigs = eff.signals(bars, 19.0, 24.0)
    d = eff.delay_signals(sigs)
    assert len(d) == len(sigs)
    assert d[0][0] == 0 and d[0][3] == "" and d[0][2] == sigs[0][2]
    for j in range(1, len(sigs)):
        assert d[j][0] == sigs[j - 1][0] and d[j][1] == sigs[j - 1][1] and d[j][3] == sigs[j - 1][3]
        assert d[j][2] == sigs[j][2], "色は実際の足のもの"
    n_sig = sum(1 for s in sigs if s[0] != 0)
    n_del = sum(1 for s in d if s[0] != 0)
    assert n_del in (n_sig, n_sig - 1)


def test_delayed_trades_enter_on_the_bar_after_the_signal():
    bars = walk(60_000, seed=53)
    close = [b[4] for b in bars]
    sigs = eff.signals(bars, 19.0, 24.0)
    d = eff.delay_signals(sigs)
    for keep in (None, "weak", "strong"):
        for use_invalid in (True, False):
            trades = eff.simulate(bars, d, keep, use_invalid=use_invalid)
            assert len(trades) > 100
            for entry_i, ret, hold, _why in trades:
                s = sigs[entry_i - 1][0]                      # 前の足のシグナルで建てている
                assert s != 0 and (keep is None or sigs[entry_i - 1][3] == keep)
                want = s * (close[entry_i + hold] / close[entry_i] - 1.0) * 1e4
                assert math.isclose(ret, want, rel_tol=0, abs_tol=1e-9)
            # 遅らせない経路とは違う結果になる(テストが空でないことの確認)
            assert trades != eff.simulate(bars, sigs, keep, use_invalid=use_invalid)


def test_without_delay_nothing_changes():
    bars = walk(20_000, seed=55)
    sigs = eff.signals(bars, 19.0, 24.0)
    assert eff.simulate(bars, sigs, None) == eff.simulate(bars, sigs, None, use_invalid=True)
