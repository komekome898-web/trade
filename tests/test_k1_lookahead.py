"""K1 深掘り §3 — **先読み・符号の検査**(`docs/PHASE2/K1/DEEPDIVE_PLAN.md`)。

`RESULT.md` §3.5 が「先読みの検査は走らせていない」と書いていた項目を、合成足で
**テストとして固定**する。合成足はすべて種を固定しており、実データには触れない。

    1. `signals()` の足 i の出力は、i より後の足を変えても・切り落としても変わらない
    2. `fold()` の窓境界(ts=59 → 0、ts=60 → 60、+20 秒ずれた行も正しい分)と o/h/l/c
    3. `simulate()` の各取引のリターンは、建てた足と決済した足の**終値だけ**から出ている
    4. 前方リターンの添字が `close[i+h]`(h 本ぴったり)であること
    5. **植え込み回収**: シグナルの直後に +X bp を植えると、r_3 の平均が X を回収する
    6. `day_bootstrap` は全日同一の値なら区間 = その値

加えて、設計書 §6 の前提「`vol_prev` 100 本は先読みを含まない(実装(テストで固定))」も
ここで固定する。
"""
from __future__ import annotations

import math
import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import measure_katsuo_dispersion as base  # noqa: E402
import measure_katsuo_effect as eff  # noqa: E402
import measure_katsuo_robustness as rb  # noqa: E402
from measure_katsuo_signal_horizon import cell_rng, day_bootstrap  # noqa: E402

SMALL, BIG = 19.0, 24.0          # 当時の門(bp)
PRICE = 10_000.0                 # 1 ドル = 1 bp になる値段。int() 切り捨ての効き方も実データ寄り


def walk(n: int, seed: int, sd_bp: float = 20.0, wick_bp: float = 25.0):
    """ランダムウォークの合成足 [(ts, o, h, l, c), ...]。**決定的**(種を固定)。"""
    rng = random.Random(seed)
    bars = []
    c = PRICE
    for i in range(n):
        o = c
        c = o * (1.0 + rng.gauss(0.0, sd_bp) / 1e4)
        top = max(o, c) + abs(rng.gauss(0.0, wick_bp)) * o / 1e4
        bot = min(o, c) - abs(rng.gauss(0.0, wick_bp)) * o / 1e4
        bars.append((60 * i, o, top, bot, c))
    return bars


# ---------------------------------------------------------------- 1. signals

def test_signals_do_not_depend_on_later_bars():
    """足 i の出力は、i より後を切り落としても・作り替えても変わらない。"""
    bars = walk(600, seed=11)
    full = eff.signals(bars, SMALL, BIG)

    for k in (1, 2, 37, 199, 599, 600):
        assert eff.signals(bars[:k], SMALL, BIG) == full[:k], f"切り落とし k={k} で変わった"

    rng = random.Random(99)
    for cut in (5, 123, 400):
        tampered = list(bars[:cut])
        for ts, o, h, l, c in bars[cut:]:
            f = 1.0 + rng.gauss(0.0, 0.01)
            tampered.append((ts, o * f, h * f * 1.02, l * f * 0.98, c * f))
        assert eff.signals(tampered, SMALL, BIG)[:cut] == full[:cut], \
            f"i>={cut} を作り替えたら i<{cut} の出力が変わった"

    # 強さ・向きも同じ(タプル全体で比べているが、意図を明示する)
    assert {s[3] for s in full} <= {"", "strong", "weak"}
    assert any(s[0] != 0 for s in full), "この合成足ではシグナルが 1 本も出ていない"


# ---------------------------------------------------------------- 2. fold

def test_fold_window_boundaries_and_ohlc():
    """ts=59 はバケット 0、ts=60 はバケット 60。+20 秒ずれた行も正しい分に入る。"""
    secs = [
        (0, 100.0, 101.0, 99.0, 100.5),     # 0 分
        (20, 100.5, 104.0, 100.0, 103.0),
        (59, 103.0, 103.5, 95.0, 96.0),     # 59 秒 → まだ 0 分
        (60, 96.0, 97.0, 96.0, 96.5),       # 60 秒 → 1 分の先頭
        (80, 96.5, 99.0, 90.0, 91.0),       # 分の境界に乗っていない行も 1 分に入る
        (180, 91.0, 92.0, 91.0, 91.5),      # 3 分(2 分は欠測 = 行を作らない)
    ]
    bars = base.fold(secs, 1)
    assert [b[0] for b in bars] == [0, 60, 180]
    assert bars[0] == (0, 100.0, 104.0, 95.0, 96.0)      # o=最初 h=max l=min c=最後
    assert bars[1] == (60, 96.0, 99.0, 90.0, 91.0)
    assert bars[2] == (180, 91.0, 92.0, 91.0, 91.5)

    # 5 分足でも同じ規則。ts=299 は最初の窓、ts=300 は次の窓
    bars5 = base.fold([(0, 1.0, 1.0, 1.0, 1.0), (299, 2.0, 2.0, 2.0, 2.0),
                       (300, 3.0, 3.0, 3.0, 3.0)], 5)
    assert [b[0] for b in bars5] == [0, 300]
    assert bars5[0][1] == 1.0 and bars5[0][4] == 2.0


# ---------------------------------------------------------------- 3. simulate

def test_simulate_returns_use_only_entry_and_exit_closes():
    """各取引の bp は 建てた足の終値と決済した足の終値だけから再計算できる。"""
    bars = walk(1500, seed=23)
    close = [b[4] for b in bars]
    for keep in (None, "strong", "weak"):
        sigs = eff.signals(bars, SMALL, BIG)
        trades = eff.simulate(bars, sigs, keep)
        assert trades, f"keep={keep} で取引が 1 件も無い"
        for entry_i, ret, hold, why in trades:
            assert hold >= 1 and entry_i + hold < len(bars)
            s = sigs[entry_i][0]
            assert s != 0 and (keep is None or sigs[entry_i][3] == keep)
            want = s * (close[entry_i + hold] / close[entry_i] - 1.0) * 1e4
            assert math.isclose(ret, want, rel_tol=0, abs_tol=1e-9), (entry_i, ret, want, why)


# ---------------------------------------------------------------- 4. 前方リターンの添字

def test_forward_return_index_is_exactly_h_bars():
    """単調増加の合成列で `r_h` が `close[i+h]` を使っている(h 本ぴったり)。

    診断 D1 の材料 `FootData.fwd` を検査する。D1 は第 4 部の
    `signal_horizon.json` と n・平均・区間が全部一致することを再現ゲートで確認しているので、
    ここで添字を固定すれば第 4 部の添字も固定される。
    """
    n = 40
    bars = [(60 * i, 100.0 + i, 100.0 + i, 100.0 + i, 100.0 + i) for i in range(n)]
    fd = rb.FootData(bars)
    for h in rb.HORIZONS:
        arr = fd.fwd[h]
        for i in range(n - h):
            want = ((100.0 + i + h) / (100.0 + i) - 1.0) * 1e4
            assert math.isclose(float(arr[i]), want, rel_tol=1e-12), (h, i)
        for i in range(n - h, n):
            assert math.isnan(float(arr[i])), (h, i)     # 先が無い足は値を持たない
    # D3(1 本遅らせた入口)は分母が close[i+1]
    for h in (2, 3, 5, 10):
        arr = fd.fwd_delayed[h]
        for i in range(n - h):
            want = ((100.0 + i + h) / (100.0 + i + 1) - 1.0) * 1e4
            assert math.isclose(float(arr[i]), want, rel_tol=1e-12), (h, i)
        assert math.isnan(float(fd.fwd_delayed[1][0])), "h=1 の遅らせた入口は定義しない"


# ---------------------------------------------------------------- 5. 植え込み回収

def _isolated(sigs, gap: int):
    """前後 `gap` 本に他のシグナルが無い足だけを拾う(植え込みが重ならないように)。"""
    idx = [i for i, s in enumerate(sigs) if s[0] != 0]
    out = []
    for k, i in enumerate(idx):
        prev_ok = k == 0 or i - idx[k - 1] > gap
        next_ok = k == len(idx) - 1 or idx[k + 1] - i > gap
        if prev_ok and next_ok:
            out.append(i)
    return out


@pytest.mark.parametrize("plant_bp", [30.0, -30.0])
def test_planted_drift_is_recovered_with_the_right_sign(plant_bp):
    """シグナルの直後 3 本の終値に `sig × X bp` を植えると、`r_3` の平均が X を回収する。

    符号が逆なら(あるいは添字が 1 本ずれていれば)落ちる。植える**前**の平均が
    ほぼ 0 であることも同じ材料で確かめる。
    """
    h = 3
    bars = walk(60_000, seed=7, sd_bp=15.0, wick_bp=10.0)
    sigs = eff.signals(bars, SMALL, BIG)
    idx = _isolated(sigs, gap=h)
    assert len(idx) > 1_000, f"検出力が足りない(孤立シグナル {len(idx)} 本)"

    # 測るのは診断 D1 の材料そのもの(`FootData.fwd`)。式を書き写さない
    def mean_r(rows):
        arr = rb.FootData(rows).fwd[h]
        got = [sigs[i][0] * float(arr[i]) for i in idx if not math.isnan(float(arr[i]))]
        assert len(got) >= len(idx) - 1
        return sum(got) / len(got), got

    m_before, before = mean_r(bars)
    se = (sum((x - m_before) ** 2 for x in before) / (len(before) - 1) / len(before)) ** 0.5
    assert abs(m_before) < 4 * se + 1.0, f"植える前の平均が 0 から離れている: {m_before:.2f} bp"

    # 直後 h 本の終値に上乗せ(符号はシグナルの向き)。孤立シグナルだけなので重ならない
    planted = [list(b) for b in bars]
    for i in idx:
        for j in range(i + 1, min(i + h, len(bars) - 1) + 1):
            planted[j][4] *= 1.0 + sigs[i][0] * plant_bp / 1e4
    m_after, _ = mean_r([tuple(b) for b in planted])

    assert m_after - m_before == pytest.approx(plant_bp, abs=1.0), (
        f"回収できていない: 前 {m_before:.2f} → 後 {m_after:.2f}(植えたのは {plant_bp:+.1f} bp)")
    assert m_after * plant_bp > 0, "符号が逆"


# ---------------------------------------------------------------- 6. day_bootstrap

def test_day_bootstrap_is_degenerate_when_every_day_is_identical():
    """全日が同じ平均なら、どう抽出しても平均はその値 = 区間はその点に潰れる。"""
    value = 4.25
    day_n = {d: 1 + (d % 7) for d in range(1000, 1120)}      # 日ごとの件数はばらばら
    day_sum = {d: value * n for d, n in day_n.items()}
    lo, hi = day_bootstrap(day_sum, day_n, cell_rng("test|degenerate"))
    assert lo == pytest.approx(value, abs=1e-9)
    assert hi == pytest.approx(value, abs=1e-9)

    # ばらつきがあれば区間は潰れない(退化テストが常に通る仕掛けでないことの確認)
    day_sum2 = dict(day_sum)
    for d in list(day_sum2)[:40]:
        day_sum2[d] = -value * day_n[d]
    lo2, hi2 = day_bootstrap(day_sum2, day_n, cell_rng("test|spread"))
    assert lo2 < hi2

    # numpy 版(D2 以降)も同じ流儀 = 同じ退化をする
    import numpy as np
    days = sorted(day_n)
    lo3, hi3 = rb.np_boot(np.array([day_sum[d] for d in days]),
                          np.array([float(day_n[d]) for d in days]), "test|degenerate")
    assert lo3 == pytest.approx(value, abs=1e-9) and hi3 == pytest.approx(value, abs=1e-9)


# ---------------------------------------------------------------- 前提: vol_prev に先読みが無い

def test_vol_prev_uses_only_earlier_bars():
    """`vol_prev[i]` は i より後の足を作り替えても変わらない。i<=100 の足は値を持たない。"""
    bars = walk(400, seed=31)
    fd = rb.FootData(bars)
    cut = 250
    rng = random.Random(5)
    tampered = list(bars[:cut])
    for ts, o, h, l, c in bars[cut:]:
        f = 1.0 + rng.gauss(0.0, 0.05)
        tampered.append((ts, o * f, h * f, l * f, c * f))
    fd2 = rb.FootData(tampered)

    for i in range(cut + 1):
        a, b = float(fd.vol_prev[i]), float(fd2.vol_prev[i])
        assert (math.isnan(a) and math.isnan(b)) or math.isclose(a, b, rel_tol=1e-12), i
    assert all(math.isnan(float(fd.vol_prev[i])) for i in range(rb.VOL_WINDOW + 1))
    assert not math.isnan(float(fd.vol_prev[rb.VOL_WINDOW + 1]))

    # 定義そのもの: 直前 100 本の |log リターン| の平均(i-100..i-1)
    close = [b[4] for b in bars]
    i = 137
    want = sum(abs(math.log(close[j] / close[j - 1])) * 1e4
               for j in range(i - rb.VOL_WINDOW, i)) / rb.VOL_WINDOW
    assert math.isclose(float(fd.vol_prev[i]), want, rel_tol=1e-9)
