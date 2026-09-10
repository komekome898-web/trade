"""H1(`docs/PHASE2/K1/H1_PREREG.md` §2)の規則をテストで固定する。

1. 既定 `flip_body=False` の出力は原典と 1 bit も変わらない
2. 反転は「門を通った足」かつ「実体 ≥ 勝った側のヒゲ」だけで起き、`sig = -csign`、
   無効化ラインは新しい向きの側の極値、強さは必ず "weak"
3. 大門の枝を使わない門(`b=None`)では反転が起きない(小門は `w > body` を要求する)
4. 実体 < ヒゲ の足は反転版でも原典と同じ
"""
from __future__ import annotations

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


def shape(o, h, l, c):
    """原典と同じ式で (csign, sig0, w, body) を返す(テスト側の独立実装)。"""
    candle = c - o
    csign = 1 if candle > 0 else (-1 if candle < 0 else 0)
    if csign == 0:
        return 0, 0, 0.0, 0.0
    top, under = (h - c, o - l) if csign == 1 else (h - o, c - l)
    if int(top) > int(under):
        return csign, -1, top, abs(candle)
    if int(under) > int(top):
        return csign, 1, under, abs(candle)
    return csign, 0, 0.0, abs(candle)


def test_default_is_bit_identical_to_original():
    bars = walk(20_000, seed=3)
    for gate in ((19.0, 24.0), (None, None), ("off", 24.0), (10.0, 40.0)):
        assert eff.signals(bars, *gate) == eff.signals(bars, *gate, flip_body=False)


def test_flip_rule_body_ge_wick_only():
    bars = walk(60_000, seed=5)
    base = eff.signals(bars, 19.0, 24.0)
    flip = eff.signals(bars, 19.0, 24.0, flip_body=True)
    n_flipped = 0
    for (ts, o, h, l, c), a, b in zip(bars, base, flip):
        if a[0] == 0:                       # 門を通らない足は反転版でもシグナル無し
            assert b == a
            continue
        csign, sig0, w, body = shape(o, h, l, c)
        assert a[0] == sig0 and a[2] == csign
        if body >= w:
            n_flipped += a[0] != b[0]
            assert b[0] == -csign, "反転した足の向きは実体と逆"
            assert b[1] == (h if b[0] == -1 else l), "無効化ラインは新しい向きの側の極値"
            assert b[3] == "weak", "反転した足は必ず weak"
            assert b[2] == csign
        else:
            assert b == a, "実体 < ヒゲ の足は原典と同じ"
    assert n_flipped > 100, f"検出力が足りない(反転 {n_flipped} 本)"


def test_no_flip_without_big_gate():
    bars = walk(30_000, seed=9)
    for gate in ((None, None), (10.0, None), (19.0, None), (30.0, None)):
        assert eff.signals(bars, *gate) == eff.signals(bars, *gate, flip_body=True)
