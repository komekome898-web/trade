"""Card 1 of W4 (xborder_mom): hand-made small inputs whose exposures and kinds are known.

Each test names the item of docs/RESEARCH/cards/c1_xborder_mom/INTENT_MAP.md it checks.
Inputs: bitFlyer 1-minute bars ending at T0 + (i+1) min; the Binance rows stamped at the start of their minute
(row time = open_time, as in the store) with lag 60 s (CARD.md 測定の設定). Leader prices are written as
exp(log-move) so the momentum over k minutes is known by construction.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from bot.bt.core import BarEvent
from bot.bt.data.reference import reference_series
from bot.research.cards import CardError, run_card
from bot.research.cards.library.c1_xborder_mom import (BUY, CLOSE, EXIT_PCT, HOLD, K, LAG_NS, LEADER,
                                                       MAX_AGE_INTERVALS, MINUTE_NS, SELL, THR_PCT, XborderMom)
from bot.strategy.base import SignalType
from bot.strategy.xborder_momentum import XborderMomentumStrategy

ROOT = Path(__file__).resolve().parents[4]
NS = 1_000_000_000
M = 60 * NS
T0 = 1_704_067_200 * NS  # 2024-01-01T00:00:00Z (a test time; the card has no calendar)
DECL = {LEADER: {"lag_ns": 60 * NS, "source": "試験の入力(行の時刻 = 分の始まり)"}}


def bars_n(n, *, missing=(), empty=()):
    out = []
    miss, emp = set(missing), set(empty)
    for i in range(n):
        if i in miss:
            continue
        out.append(BarEvent(received_time_ns=T0 + (i + 1) * M, exchange_time_ns=T0 + (i + 1) * M,
                            start_time_ns=T0 + i * M, open=100.0, close=100.0, high=100.0, low=100.0,
                            volume=0.0 if i in emp else 1.0))
    return out


def run(leader, *, n=None, card=None, missing_rows=(), missing_bars=(), empty_bars=(), decl=None):
    """leader[j] = the close of minute j (starting T0 + j min), stamped at its start T0 + j min (open_time).
    Returns (exposure per bar, the card)."""
    n = len(leader) if n is None else n
    card = XborderMom() if card is None else card
    skip = set(missing_rows)
    rows = [(T0 + j * M, float(v)) for j, v in enumerate(leader) if j not in skip]
    decl = DECL if decl is None else decl
    refs = {LEADER: reference_series(LEADER, rows, declarations=decl)}
    r = run_card(card, bars_n(n, missing=missing_bars, empty=empty_bars), references=refs, declarations=decl,
                 venue="bitflyer", symbol="FX_BTC_JPY")
    return r, card


def path_with_move(n, at, move, *, base=100.0, k=K):
    """A flat leader at `base`, then from minute `at` on a level so that ln(leader[at] / leader[at-k]) = move."""
    lv = [base] * n
    for j in range(at, n):
        lv[j] = base * math.exp(move)
    return lv


# I-3 / I-4 / I-5 / I-7: the levels are the bot's settings (config/config.yaml), the bars are 1 minute,
# the leader is Binance BTCUSDT.
def test_defaults_are_the_bot_settings():
    cfg = yaml.safe_load((ROOT / "config" / "config.yaml").read_text(encoding="utf-8"))
    p = cfg["strategy"]["params"]
    assert cfg["strategy"]["name"] == "xborder_momentum"
    assert (K, THR_PCT, EXIT_PCT) == (p["k"], p["thr_pct"], p["exit_pct"])
    assert MINUTE_NS == int(cfg["candle_interval_sec"]) * NS
    assert cfg["leader"] == {"exchange": "binance", "symbol": "BTCUSDT"}
    import inspect

    from bot.market_data.external_feed import BinanceFeed
    assert inspect.signature(BinanceFeed.close_for).parameters["max_age_intervals"].default == MAX_AGE_INTERVALS
    c = XborderMom()
    assert c.thr == float(p["thr_pct"]) / 100 and c.exit_band == float(p["exit_pct"]) / 100
    assert [(s.name, s.lag_ns) for s in c.requires] == [(LEADER, LAG_NS)] and LAG_NS == 60 * NS


# I-5: mom > +thr -> 買い, e = +1 (and I-2: the move is the leader's over k minutes)
def test_buy_above_threshold():
    n = 80
    r, c = run(path_with_move(n, 60, 0.009), n=n)
    t, kinds = c.kinds()
    i = 60  # the first bar whose leader minute is 60
    assert kinds[i] == BUY and r.exposure[i] == 1.0
    assert all(kd == CLOSE for kd in kinds[K + 1:60])  # flat leader: |mom| = 0 <= band
    # the move stays in the window for k minutes (minutes 60..89 vs 30..59); n = 80 keeps it inside
    assert all(kd == BUY for kd in kinds[60:n])


# I-6: mom < -thr -> 売り, e = -1
def test_sell_below_threshold():
    n = 70
    r, c = run(path_with_move(n, 60, -0.009), n=n)
    _t, kinds = c.kinds()
    assert kinds[60] == SELL and r.exposure[60] == -1.0


# I-7: |mom| <= band -> 決済, e = 0 (after a 買い); I-8: between band and thr -> 様子見 keeps e
def test_close_and_hold_after_buy():
    # leader level exp(0.009) from minute 40 (bar 40: +0.9% -> 買い); bar 70 compares 70 with 40 -> 0 (決済);
    # level exp(0.012) from minute 72, so bar 72 compares with minute 42: +0.3% (between band and thr)
    n = 120
    lv = [100.0] * n
    for j in range(40, n):
        lv[j] = 100.0 * math.exp(0.009)
    for j in range(72, n):
        lv[j] = 100.0 * math.exp(0.012)
    r, c = run(lv, n=n)
    _t, kinds = c.kinds()
    assert kinds[40] == BUY and r.exposure[40] == 1.0
    assert kinds[69] == BUY  # minute 69 vs 39: +0.9%
    assert kinds[70] == CLOSE and r.exposure[70] == 0.0  # minute 70 vs 40: 0
    assert kinds[71] == CLOSE
    assert kinds[72] == HOLD and r.exposure[72] == 0.0  # 0.3%: between; previous e (0) kept
    # leave it at 0.3% for long: still 様子見, e still 0
    assert kinds[90] == HOLD and r.exposure[90] == 0.0


# I-8: 様子見 keeps the previous e (+1 after 買い, -1 after 売り)
@pytest.mark.parametrize("sign", [+1, -1])
def test_hold_keeps_previous_exposure(sign):
    n = 100
    lv = [100.0] * n
    for j in range(40, n):
        lv[j] = 100.0 * math.exp(sign * 0.009)
    for j in range(70, n):  # minute 70 vs 40: sign * 0.003 -> between band and thr
        lv[j] = 100.0 * math.exp(sign * 0.012)
    r, c = run(lv, n=n)
    _t, kinds = c.kinds()
    assert kinds[40] == (BUY if sign > 0 else SELL)
    assert kinds[70] == HOLD and r.exposure[70] == float(sign)
    assert all(r.exposure[70:n] == float(sign))


# I-13: before any signal the card holds 0; I-15 (＋, kept): fewer than k + 2 bars -> 様子見
def test_initial_zero_and_insufficient_history():
    n = K + 5
    r, c = run([100.0] * n, n=n)
    _t, kinds = c.kinds()
    assert all(kd == HOLD for kd in kinds[:K + 1]) and all(r.exposure[:K + 1] == 0.0)
    assert c.last is not None and kinds[K + 1] == CLOSE  # k + 2 bars visible from bar k + 1 on


# I-9 / I-10: a missing leader row is replaced by at most 2 earlier minutes; beyond that, 様子見 with e kept
def test_leader_fallback_two_minutes():
    n = 80
    lv = path_with_move(n, 60, 0.009)
    # rows of minutes 61 and 62 missing: bars 61, 62 use minute 60's close (1 and 2 back) -> still 買い
    r, c = run(lv, n=n, missing_rows=(61, 62))
    _t, kinds = c.kinds()
    assert kinds[61] == BUY and kinds[62] == BUY
    # rows 61, 62, 63 missing and 60 too: bar 63 has minutes 63, 62, 61 all missing -> gap -> 様子見, e kept
    r2, c2 = run(lv, n=n, missing_rows=(60, 61, 62, 63))
    _t2, kinds2 = c2.kinds()
    assert kinds2[62] == HOLD and c2.last is not None
    assert kinds2[63] == HOLD and r2.exposure[63] == r2.exposure[59]
    assert kinds2[64] == BUY  # minute 64 present again


# I-9 / I-10 on the past side: the minute k back is missing -> up to 2 earlier minutes, then 様子見
def test_past_side_fallback():
    n = 80
    lv = path_with_move(n, 60, 0.009)
    r, c = run(lv, n=n, missing_rows=(30,))  # bar 60's past minute is 30 -> uses 29 (same flat level)
    assert c.kinds()[1][60] == BUY
    r2, c2 = run(lv, n=n, missing_rows=(28, 29, 30))
    assert c2.kinds()[1][60] == HOLD


# Code-side ＋ item (past <= 0 -> 様子見): the bot's guard, kept as in the code
def test_past_non_positive_is_gap():
    n = 50
    lv = [100.0] * n
    lv[10] = 0.0  # bar 40 compares minute 40 with minute 10
    r, c = run(lv, n=n)
    _t, kinds = c.kinds()
    assert kinds[40] == HOLD and c.kinds()[1][41] == CLOSE


# I-12 / no look-ahead: the decision at bar i (end t) reads the row of the minute that ends at t (row time t - 60 s),
# which becomes available at t and not earlier
def test_reads_the_minute_ending_at_t():
    n = 70
    lv = [100.0] * n
    lv[60] = 100.0 * math.exp(0.009)  # a one-minute spike in minute 60 only
    r, c = run(lv, n=n)
    _t, kinds = c.kinds()
    assert kinds[59] == CLOSE  # the spike's row (minute 60, available at its end) is not visible at bar 59
    assert kinds[60] == BUY  # visible at the end of bar 60
    assert kinds[61] == CLOSE


# The series must be declared with lag 60 s (row time = open_time); a series declared otherwise -- lag 0, which on
# open_time rows would read each close one minute early -- is refused
def test_other_lag_is_refused():
    decl = {LEADER: {"lag_ns": 0, "source": "試験: 分の始まりの時刻 + 遅れ 0(未来を読む宣言)"}}
    with pytest.raises(CardError):
        run([100.0] * 40, decl=decl)


# I-2 (k = Binance minutes): bitFlyer bars missing in between do not change which Binance minutes are compared
def test_window_is_k_binance_minutes():
    n = 80
    lv = path_with_move(n, 60, 0.009)
    full, c_full = run(lv, n=n)
    gap, c_gap = run(lv, n=n, missing_bars=range(45, 55))
    t_full, k_full = c_full.kinds()
    t_gap, k_gap = c_gap.kinds()
    by_t = dict(zip(t_full.tolist(), k_full))
    assert all(by_t[t] == kd for t, kd in zip(t_gap.tolist(), k_gap))


# I-11: decided only at the end of non-empty bars (an empty bar is not a decision of its own)
def test_empty_bars_not_decided():
    n = 70
    r, c = run(path_with_move(n, 60, 0.009), n=n, empty_bars=(60,))
    t, kinds = c.kinds()
    assert not r.decided[60] and len(kinds) == n - 1
    assert kinds[60] == BUY  # bar 61 (the 61st call) still sees the move


# I-12: the kind is recorded per call, in call order, and `last` is the latest
def test_kind_log_matches_calls():
    n = 70
    r, c = run(path_with_move(n, 60, 0.009), n=n)
    t, kinds = c.kinds()
    assert len(kinds) == int(r.decided.sum()) and np.array_equal(t, r.end_ns[r.decided])
    assert c.last.kind == kinds[-1] and c.last.t_ns == int(t[-1]) and c.last.e == r.exposure[-1]


# Whole-card check against the bot's own code on the same input (gap-free bitFlyer minutes; Binance rows with
# holes): the card's kind equals the bot's signal on every bar.
def test_same_kinds_as_the_bot_code():
    rng = np.random.default_rng(20261002)
    n = 3000
    lv = list(100.0 * np.exp(np.cumsum(rng.normal(0.0, 0.003, n))))
    holes = set(rng.choice(np.arange(5, n), size=150, replace=False).tolist())
    holes |= {500, 501, 502, 503}  # a hole longer than 2 minutes
    r, c = run(lv, n=n, missing_rows=holes)
    _t, kinds = c.kinds()

    strat = XborderMomentumStrategy({"k": K, "thr_pct": THR_PCT, "exit_pct": EXIT_PCT})
    t0s = T0 // NS
    closes = {t0s + 60 * j: v for j, v in enumerate(lv) if j not in holes}

    def close_for(start, max_age_intervals=2):  # BinanceFeed.close_for over the same closes
        for back in range(max_age_intervals + 1):
            p = closes.get(start - back * 60)
            if p is not None:
                return p
        return None

    starts = [t0s + 60 * i for i in range(n)]
    lead = pd.Series([close_for(s) for s in starts], dtype="float64")
    want = {SignalType.BUY: BUY, SignalType.SELL: SELL, SignalType.CLOSE: CLOSE, SignalType.HOLD: HOLD}
    got_bot = []
    for i in range(n):
        df = pd.DataFrame({"start": starts[:i + 1], "close": [100.0] * (i + 1)})
        df["leader_close"] = lead[:i + 1].values
        got_bot.append(want[strat.on_candles(df).type])
    assert kinds == got_bot
    assert {BUY, SELL, CLOSE, HOLD} <= set(kinds)
