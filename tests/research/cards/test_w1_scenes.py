"""C4: the scene variables, each against a brute-force computation written
from the spec's words, and the past-only property (changing what comes after
t changes nothing at or before t)."""
from __future__ import annotations

import numpy as np
import pytest

from bot.research.cards.pnl import pnl
from bot.research.cards.run import CardRun
from bot.research.cards.scenes import (DAY_NS, HOUR_NS, MINUTE_NS, POSITION_WINDOW_NS, local_vol, one_minute_moves,
                                       past_position, scene_vars, variance_ratio)

from w1_synth import T0

SEED = 7  # test value


def brute_position(times, values, window):
    out = []
    for k in range(len(times)):
        v = values[k]
        if not np.isfinite(v):
            out.append(np.nan)
            continue
        w = [values[j] for j in range(k) if times[j] > times[k] - window and np.isfinite(values[j])]
        if not w:
            out.append(np.nan)
            continue
        below = sum(1 for x in w if x < v)
        eq = sum(1 for x in w if x == v)
        out.append((below + 0.5 * eq) / len(w))
    return np.array(out)


def test_past_position_matches_brute_force():
    rng = np.random.default_rng(SEED)
    gaps = rng.integers(1, 4 * 3600, size=1500) * 10**9  # irregular, up to 4 hours apart
    times = T0 + np.cumsum(gaps)
    values = np.round(rng.normal(size=1500), 1)  # ties
    values[rng.choice(1500, 100, replace=False)] = np.nan
    for days in (1, 3, 7):
        got = past_position(times, values, days * DAY_NS)
        want = brute_position(list(times), list(values), days * DAY_NS)
        assert np.array_equal(np.isnan(got), np.isnan(want))
        assert np.allclose(got[~np.isnan(got)], want[~np.isnan(want)], rtol=0, atol=1e-12)


def _run_from(start, end, close, volume=None, refs=None):
    n = len(start)
    volume = np.ones(n) if volume is None else volume
    o = np.concatenate(([close[0]], close[:-1]))
    refs = refs or {}
    return CardRun("c", "venueA", "sym", np.asarray(start, dtype=np.int64), np.asarray(end, dtype=np.int64),
                   o, np.maximum(o, close), np.minimum(o, close), np.asarray(close, dtype=float), volume,
                   volume > 0, np.where(volume > 0, 0.0, np.nan),
                   {k: v[0] for k, v in refs.items()}, {k: v[1] for k, v in refs.items()}, {k: 0 for k in refs})


def _minute_run(n, seed=SEED, every=1):
    rng = np.random.default_rng(seed)
    idx = np.arange(n) * every
    start = T0 + idx * MINUTE_NS
    close = 100 * np.exp(np.cumsum(rng.normal(0, 1e-3, n)))
    return _run_from(start, start + MINUTE_NS, close)


def brute_moves(run):
    ne = [i for i in range(len(run.end_ns)) if run.volume[i] > 0]
    out = []
    for a, b in zip(ne[:-1], ne[1:]):
        if run.start_ns[b] == run.end_ns[a]:
            out.append((int(run.end_ns[b]), float(np.log(run.close[b] / run.close[a]))))
    return out


def test_one_minute_moves_skip_gaps_and_empty_bars():
    run = _minute_run(50)
    vol = run.volume.copy()
    vol[10] = 0.0
    keep = np.r_[0:20, 25:50]  # a gap of 5 bars
    run2 = _run_from(run.start_ns[keep], run.end_ns[keep], run.close[keep], vol[keep])
    t, m = one_minute_moves(run2)
    want = brute_moves(run2)
    assert list(t) == [w[0] for w in want] and np.allclose(m, [w[1] for w in want], rtol=0, atol=1e-15)
    # 45 bars kept: 44 neighbours; minus the pair across the gap, minus the 2 pairs at the empty bar
    assert len(want) == 44 - 1 - 2


def test_local_vol_and_variance_ratio_match_brute_force():
    run = _minute_run(3 * 1440)
    keep = np.r_[0:1000, 1003:3 * 1440]
    run = _run_from(run.start_ns[keep], run.end_ns[keep], run.close[keep])
    mt, mv = one_minute_moves(run)
    t = run.end_ns[::37]
    for w in (HOUR_NS, DAY_NS):
        got = local_vol(mt, mv, t, w)
        for k, tk in enumerate(t):
            x = mv[(mt > tk - w) & (mt <= tk)]
            want = np.std(x, ddof=1) if len(x) >= 2 else np.nan
            assert (np.isnan(got[k]) and np.isnan(want)) or abs(got[k] - want) < 1e-12
        q = 5
        got = variance_ratio(mt, mv, t, w, q)
        for k, tk in enumerate(t):
            inw = (mt > tk - w) & (mt <= tk)
            x = mv[inw]
            ts = mt[inw]
            qs = [x[j - q + 1:j + 1].sum() for j in range(q - 1, len(x))
                  if ts[j] - ts[j - q + 1] == (q - 1) * MINUTE_NS]
            if len(x) < 2 or len(qs) < 2:
                assert np.isnan(got[k])
                continue
            want = np.var(qs, ddof=1) / (q * np.var(x, ddof=1))
            assert abs(got[k] - want) < 1e-9


def test_hour_and_weekday_are_japan_time_and_regimes_and_venue():
    # 2024-01-01T00:00Z = Monday 09:00 JST; 2024-01-01T15:00Z = Tuesday 00:00 JST
    start = np.array([T0, T0 + 15 * HOUR_NS - MINUTE_NS, T0 + 20 * HOUR_NS, T0 + 21 * HOUR_NS], dtype=np.int64)
    run = _run_from(start, start + MINUTE_NS, np.array([100.0, 101, 102, 103]))
    p = pnl(run)  # decisions at the first two bars
    vs = {v.name: v for v in scene_vars(run, p, vr_q_bars=None, regimes=[(T0 + HOUR_NS, "A"), (T0 + 16 * HOUR_NS, "B")],
                                        ref_scenes={})}
    assert list(vs["hour_jst"].value) == ["09", "00"]
    assert list(vs["weekday_jst"].value) == ["0", "1"]
    assert list(vs["regime"].value) == ["", "A"]  # before the first boundary: no label
    assert list(vs["venue"].value) == ["venueA", "venueA"]
    assert "vr_1h" not in vs  # no horizon given -> no vr variable


def test_positions_are_used_only_365_days_after_the_start():
    run = _minute_run(400 * 24, every=60)  # one 1-minute bar an hour, 400 days
    pairs = np.sort(np.concatenate((np.arange(400 * 24) * 60, np.arange(400 * 24) * 60 + 1)))
    start = T0 + pairs * MINUTE_NS
    close = 100 * np.exp(np.cumsum(np.random.default_rng(1).normal(0, 1e-3, len(pairs))))
    run = _run_from(start, start + MINUTE_NS, close)
    p = pnl(run)
    vs = {v.name: v for v in scene_vars(run, p, vr_q_bars=None, regimes=None, ref_scenes={})}
    v = vs["vol_1d"]
    old = (p.t_ns - run.start_ns[0]) >= POSITION_WINDOW_NS
    assert old.any() and (~old).any()
    assert np.array_equal(v.eligible_position, old & np.isfinite(v.position))
    assert np.isfinite(v.position[~old]).any()  # the position exists earlier, it is only not used


def test_scene_values_do_not_depend_on_what_comes_after_t():
    n = 6 * 1440
    run = _minute_run(n)
    ref_t = np.where(np.arange(n) % 7 == 0, run.end_ns, -1)
    ref_v = np.where(np.arange(n) % 7 == 0, np.sin(np.arange(n)), np.nan)
    run = _run_from(run.start_ns, run.end_ns, run.close, refs={"R": (ref_t, ref_v)})
    p = pnl(run)
    a = scene_vars(run, p, vr_q_bars=4, regimes=None, ref_scenes={"R": "continuous"})
    cut = 4 * 1440
    close2 = run.close.copy()
    close2[cut:] *= np.exp(np.random.default_rng(3).normal(0, 0.05, n - cut))
    ref_v2 = ref_v.copy()
    ref_v2[cut:] = -ref_v2[cut:] * 3
    run2 = _run_from(run.start_ns, run.end_ns, close2, refs={"R": (ref_t, ref_v2)})
    b = scene_vars(run2, pnl(run2), vr_q_bars=4, regimes=None, ref_scenes={"R": "continuous"})
    upto = p.t_ns < run.end_ns[cut]  # decisions before the first changed bar closes
    changed_after = False
    for x, y in zip(a, b):
        assert x.name == y.name
        va, vb = x.value[upto], y.value[upto]
        assert all((u == w) or (u != u and w != w) for u, w in zip(va, vb)), x.name
        if x.position is not None:
            pa, pb = x.position[upto], y.position[upto]
            assert np.array_equal(np.isnan(pa), np.isnan(pb)) and np.array_equal(pa[~np.isnan(pa)], pb[~np.isnan(pb)])
            changed_after |= not np.allclose(np.nan_to_num(x.value[~upto]), np.nan_to_num(y.value[~upto]))
    assert changed_after  # the change is seen after t (the test is not vacuous)


def test_scene_vars_refuse_other_than_1_minute_bars():
    start = T0 + np.arange(10) * 5 * MINUTE_NS
    run = _run_from(start, start + 5 * MINUTE_NS, np.linspace(100, 101, 10))
    with pytest.raises(ValueError, match="1-minute"):
        scene_vars(run, pnl(run), vr_q_bars=None, regimes=None, ref_scenes={})
