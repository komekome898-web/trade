"""K1 取引所横断(`docs/PHASE2/K1/XVENUE_PREREG.md` §3 Deliverable C)。

合成足で 3 点を固定する:
1. `simulate(..., prices=None)` は既定(引数を渡さない)と完全に同一
2. `prices` に別の(シフト・スケールした)価格列を渡すと、各取引のリターンは
   `sign × (prices[exit] / prices[entry] - 1) × 1e4` に等しく、entry/exit の添字は
   価格列を渡さない実行と同一
3. 分の内部結合 + 畳み込みは両取引所で時刻が完全に一致し、正しい分だけを落とす
"""
from __future__ import annotations

import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import measure_katsuo_effect as eff  # noqa: E402
import measure_katsuo_dispersion as base  # noqa: E402
import measure_katsuo_xvenue as xv  # noqa: E402

PRICE = 10_000.0


def walk(n: int, seed: int, sd_bp: float = 20.0, wick_bp: float = 25.0, start_ts: int = 0):
    rng = random.Random(seed)
    bars, c = [], PRICE
    for i in range(n):
        o = c
        c = o * (1.0 + rng.gauss(0.0, sd_bp) / 1e4)
        top = max(o, c) + abs(rng.gauss(0.0, wick_bp)) * o / 1e4
        bot = min(o, c) - abs(rng.gauss(0.0, wick_bp)) * o / 1e4
        bars.append((start_ts + 60 * i, o, top, bot, c))
    return bars


# ---------------------------------------------------------------------------
# 1. prices=None は既定と同一
# ---------------------------------------------------------------------------

def test_prices_none_matches_default():
    bars = walk(20_000, seed=201)
    sig = eff.delay_signals(eff.signals(bars, 19.0, 24.0, flip_body=True))
    for keep in (None, "weak", "strong"):
        for use_invalid in (True, False):
            base_trades = eff.simulate(bars, sig, keep, use_invalid=use_invalid)
            explicit_none = eff.simulate(bars, sig, keep, use_invalid=use_invalid, prices=None)
            assert base_trades == explicit_none
    assert len(base_trades) > 50  # テストが空でないことの確認


# ---------------------------------------------------------------------------
# 2. prices を差し替えると、その価格列で計算したリターンに一致する
# ---------------------------------------------------------------------------

def test_prices_override_changes_fill_but_not_decisions():
    bars = walk(30_000, seed=203)
    close = [b[4] for b in bars]
    sig = eff.delay_signals(eff.signals(bars, 19.0, 24.0, flip_body=True))
    # シフト・スケールした別の価格列(全て正)
    prices = [c * 3.7 + 1_234.5 for c in close]

    for keep in (None, "weak", "strong"):
        for use_invalid in (True, False):
            unpriced = eff.simulate(bars, sig, keep, use_invalid=use_invalid)
            priced = eff.simulate(bars, sig, keep, use_invalid=use_invalid, prices=prices)
            assert len(priced) == len(unpriced)
            for (ei_u, _r_u, h_u, w_u), (ei_p, r_p, h_p, w_p) in zip(unpriced, priced):
                # entry/exit の添字(entry_i と保有本数)、決済理由は不変
                assert ei_u == ei_p and h_u == h_p and w_u == w_p
                exit_i = ei_p + h_p
                sign = sig[ei_p][0]
                assert sign != 0
                want = sign * (prices[exit_i] / prices[ei_p] - 1.0) * 1e4
                assert math.isclose(r_p, want, rel_tol=0, abs_tol=1e-9)
    assert len(priced) > 50


def test_prices_le_zero_skipped_like_bars_close():
    bars = walk(5_000, seed=205)
    sig = eff.delay_signals(eff.signals(bars, 19.0, 24.0, flip_body=True))
    close = [b[4] for b in bars]
    prices = list(close)
    # 何本かの価格を壊す(0 以下)。bars 側の終値は変えない
    broken = {17, 403, 1_999, 4_500}
    for i in broken:
        prices[i] = 0.0 if i % 2 == 0 else -5.0

    priced = eff.simulate(bars, sig, "weak", use_invalid=False, prices=prices)
    # 壊した足では新規建て・決済・ドテンのどれも起きていないこと(entry にも exit にも出ない)
    for entry_i, _r, hold, _why in priced:
        exit_i = entry_i + hold
        assert entry_i not in broken
        assert exit_i not in broken


# ---------------------------------------------------------------------------
# 3. 分の内部結合 + 畳み込み
# ---------------------------------------------------------------------------

def test_inner_join_drops_the_right_minutes_and_folds_identically():
    # シグナル側: 0..99 分(100 分)。価格側: 50..149 分(100 分)。共通は 50..99(50 分)
    sig_rows = [(60 * i, 100.0, 101.0, 99.0, 100.0 + i * 0.01) for i in range(100)]
    price_rows = [(60 * i, 200.0, 202.0, 198.0, 200.0 + i * 0.02) for i in range(50, 150)]

    sig_j, price_j, common_ts, sig_map, price_map = xv.join_minutes(sig_rows, price_rows)

    # 落とした分が正しい: 共通は 50 分(50..99)だけ
    assert common_ts == [60 * i for i in range(50, 100)]
    assert len(sig_j) == len(price_j) == 50
    # シグナル側 0..49 分・価格側 100..149 分が落ちている
    dropped_sig = {r[0] for r in sig_rows} - set(common_ts)
    dropped_price = {r[0] for r in price_rows} - set(common_ts)
    assert dropped_sig == {60 * i for i in range(0, 50)}
    assert dropped_price == {60 * i for i in range(100, 150)}

    # 結合済みの行は元の取引所の値そのもの(結合で値は書き換わらない)
    for t, s_row, p_row in zip(common_ts, sig_j, price_j):
        assert s_row == sig_map[t]
        assert p_row == price_map[t]

    # 畳み込み(足 5 分・15 分)は両取引所で時刻が完全に一致する
    for foot in (1, 3, 5, 15, 30, 60):
        sig_bars, price_bars = xv.fold_joined(sig_j, price_j, foot)
        assert [b[0] for b in sig_bars] == [b[0] for b in price_bars]
        assert len(sig_bars) > 0


def test_fold_joined_raises_when_timestamps_would_diverge():
    # 意図的に結合前の行を渡す(実装ミスの検出用: fold 前に結合していないと時刻が割れる)
    sig_rows = [(60 * i, 1.0, 1.0, 1.0, 1.0) for i in range(0, 20)]
    price_rows = [(60 * i, 1.0, 1.0, 1.0, 1.0) for i in range(0, 20, 2)]  # 偶数分だけ
    try:
        xv.fold_joined(sig_rows, price_rows, 1)
    except AssertionError:
        return
    raise AssertionError("結合していない行を渡しても時刻の不一致が検出されなかった")
