"""H2a(`docs/PHASE2/K1/H2_PREREG.md` §2)の規則をテストで固定する。

1. 既定 `use_invalid=True` の出力は原典と同一
2. `use_invalid=False` は第 7 部 `measure_katsuo_exit_ablation.simulate(mode="opposite_only")` と
   取引ごとに一致する(同じ経路であることの再現ゲート、合成足)
3. `use_invalid=False` では決済理由に `invalidated` が現れない
4. H1 と併用しても 2 が成り立つ
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import measure_katsuo_effect as eff  # noqa: E402
import measure_katsuo_exit_ablation as abl  # noqa: E402

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


def test_default_is_identical_to_original():
    bars = walk(30_000, seed=41)
    sigs = eff.signals(bars, 19.0, 24.0)
    for keep in (None, "strong", "weak"):
        assert eff.simulate(bars, sigs, keep) == eff.simulate(bars, sigs, keep, use_invalid=True)


def test_no_invalidation_matches_exit_ablation_opposite_only():
    bars = walk(60_000, seed=43)
    for flip in (False, True):
        sigs = eff.signals(bars, 19.0, 24.0, flip_body=flip)
        for keep in (None, "strong", "weak"):
            mine = eff.simulate(bars, sigs, keep, use_invalid=False)
            ref = abl.simulate(bars, sigs, keep, "opposite_only")
            assert mine == ref, f"flip={flip} keep={keep}: 第 7 部の opposite_only と食い違う"
            assert len(mine) > 100
            assert all(why != "invalidated" for _i, _r, _h, why in mine)
            # 原典(無効化あり)とは違う結果になる(テストが空でないことの確認)
            assert mine != eff.simulate(bars, sigs, keep)
