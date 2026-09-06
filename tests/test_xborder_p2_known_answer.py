"""P2-08 known-answer test (PREREG 第 4 稿「執行様式のパイプライン既知正解テスト」).

Hand-made Binance and bitFlyer 50-minute series; five trades covering
  (a) signal -> fill at the NEXT bar's open,
  (b) exit on |m| < exit,
  (c) stop detected inside a bar, filled at the next open (gap taken on the
      adverse side),
  (d) deferral of a fill that lands on an empty minute (< 5 min blank),
  (e) 0.02% funding for every settlement instant (UTC 05:00/13:00/21:00)
      crossed while holding,
  (f) a trade holding across a >5-minute gap is EXCLUDED, and entry signals
      raised during a >5-minute blank run or within 5 minutes before it are
      DISCARDED (第 4 稿「優先順位」).
Every expected number is written out here BY HAND (formula in the comment),
and the ledger must match to 1e-9 bps.

Grid: bar i starts at T0 + i minutes, T0 = 2023-06-01 04:40 UTC, i = 0..49,
so the 05:00 settlement is bar i = 20.
Parameters: k = 1, thr = 1.0%, exit = 0.2%, stop = 1.0%, one-way cost 1.3 bps,
funding 0.02% per settlement, max gap 5 minutes, size 0.01 BTC.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from bot.research.xborder_p2 import (
    LEDGER_COLUMNS,
    big_gaps,
    block_permute_log_returns,
    count_settlements,
    daily_pnl,
    misprint_mask,
    momentum_signal,
    regime_of,
    sharpe_annual,
    simulate,
)

T0 = pd.Timestamp("2023-06-01 04:40:00", tz="UTC")
N = 50
INDEX = pd.date_range(T0, periods=N, freq="min")

K, THR, EXIT, STOP, COST_1W = 1, 1.0, 0.2, 1.0, 1.3

# ---- Binance closes c(i); with k = 1, m(i) = c(i)/c(i-1) - 1 -----------------
#  i   c(i)     m(i)                 role
#  0  100.0    NaN
#  1  101.2    +1.2000%  > thr        BUY signal            -> trade 1 entry at open(2)
#  2  101.5    +0.2964%  >= exit      hold
#  3  101.6    +0.0985%  < exit       EXIT signal           -> trade 1 exit at open(4)
#  4  101.6     0
#  5  101.6     0
#  6  100.5    -1.0827%  < -thr       SELL signal           -> trade 2 entry at open(7)
#  7  100.0    -0.4975%               hold
#  8   99.5    -0.5000%               hold (bf high(8) triggers the STOP)
#  9   99.5     0                                            trade 2 exit at open(9)
# 10   99.5     0
# 11  100.6    +1.1055%  > thr        BUY signal            -> trade 3, bar 12 EMPTY, entry at open(13)
# 12  101.0    +0.3976%               (pending entry, ignored)
# 13  101.4    +0.3960%               hold
# 14..21 +0.4 each: 101.8 102.2 102.6 103.0 103.4 103.8 104.2 104.6  (m ~ +0.39%) hold across 05:00
# 22  104.6     0        < exit       EXIT signal           -> trade 3 exit at open(23)
# 23  104.6     0
# 24  103.4    -1.1472%  < -thr       SELL signal           -> trade 4 entry at open(25)
# 25..29 -0.4 each: 103.0 102.6 102.2 101.8 101.4 (m ~ -0.39%) hold
# 30..35 -0.4 each: 101.0 100.6 100.2  99.8  99.4  99.0 (m ~ -0.40%) hold; bf 30..35 EMPTY (run of 6)
# 36   99.0     0        < exit       EXIT signal           -> trade 4 exit at open(37)
# 37   99.0     0
# 38  100.2    +1.2121%  > thr        BUY signal, DISCARDED (within 5 min before the run 40..45)
# 39  100.2     0
# 40  100.2     0                     bf EMPTY
# 41  100.2     0                     bf EMPTY
# 42   99.0    -1.1976%  < -thr       SELL signal, DISCARDED (during the run); bf EMPTY
# 43..45 99.0   0                     bf EMPTY
# 46  100.2    +1.2121%  > thr        BUY signal (first valid bar after the run: kept) -> trade 5 entry at open(47)
# 47  100.6    +0.3992%               hold (bf low(47) triggers the STOP on the entry bar)
# 48  100.6     0                     bf EMPTY -> stop fill deferred to open(49)
# 49  100.6     0
BINANCE_CLOSE = [
    100.0, 101.2, 101.5, 101.6, 101.6, 101.6, 100.5, 100.0, 99.5, 99.5,      # 0-9
    99.5, 100.6, 101.0, 101.4, 101.8, 102.2, 102.6, 103.0, 103.4, 103.8,     # 10-19
    104.2, 104.6, 104.6, 104.6, 103.4, 103.0, 102.6, 102.2, 101.8, 101.4,    # 20-29
    101.0, 100.6, 100.2, 99.8, 99.4, 99.0, 99.0, 99.0, 100.2, 100.2,         # 30-39
    100.2, 100.2, 99.0, 99.0, 99.0, 99.0, 100.2, 100.6, 100.6, 100.6,        # 40-49
]

# ---- bitFlyer bars (open, high, low, close) in JPY ---------------------------
# default bar: o 1,000,000 / h 1,001,000 / l 999,000 / c 1,000,000 (never
# touches a +-1% stop from a 1,000,000 entry). Overrides:
DEFAULT_BAR = (1_000_000.0, 1_001_000.0, 999_000.0, 1_000_000.0)
EMPTY = (np.nan, np.nan, np.nan, np.nan)
BF_OVERRIDES = {
    4: (1_004_000.0, 1_005_000.0, 1_003_000.0, 1_004_000.0),   # trade 1 exit fill open(4)
    8: (1_003_000.0, 1_012_000.0, 1_002_000.0, 1_011_000.0),   # short stop: high >= 1,010,000
    9: (1_015_000.0, 1_016_000.0, 1_014_000.0, 1_015_000.0),   # stop fill open(9), gapped past the level
    12: EMPTY,                                                 # (d) entry deferred (1-minute blank)
    23: (1_003_000.0, 1_004_000.0, 1_002_000.0, 1_003_000.0),  # trade 3 exit fill open(23)
    **{i: EMPTY for i in range(30, 36)},                       # (f) valid 29 -> 36 = 7 min gap
    37: (990_000.0, 991_000.0, 989_000.0, 990_000.0),          # trade 4 exit fill open(37)
    **{i: EMPTY for i in range(40, 46)},                       # (f) valid 39 -> 46 = 7 min gap
    47: (1_000_000.0, 1_001_000.0, 989_000.0, 990_000.0),      # long stop on entry bar: low <= 990,000
    48: EMPTY,                                                 # (d) stop fill deferred (1-minute blank)
    49: (985_000.0, 986_000.0, 984_000.0, 985_000.0),          # stop fill open(49), gapped past the level
}


def make_bf() -> pd.DataFrame:
    rows = [BF_OVERRIDES.get(i, DEFAULT_BAR) for i in range(N)]
    return pd.DataFrame(rows, columns=["open", "high", "low", "close"], index=INDEX)


def make_binance() -> pd.Series:
    return pd.Series(BINANCE_CLOSE, index=INDEX, name="close")


def ts(i: int) -> pd.Timestamp:
    return T0 + pd.Timedelta(minutes=i)


# ---- the five hand-computed trades ------------------------------------------
# gross_bps = side * (exit_px / entry_px - 1) * 1e4 ; cost_bps = 2 * 1.3 = 2.6
# funding_bps = n_settlements * 0.02% = n_settlements * 2.0 ; net = gross - cost - funding
EXPECTED = [
    # 1 (a)(b): long 1,000,000 -> 1,004,000: gross (1.004-1)*1e4 = 40.0 ; net 40 - 2.6 - 0 = 37.4
    dict(entry_ts=ts(2), exit_ts=ts(4), side=1, entry_px=1_000_000.0, exit_px=1_004_000.0,
         gross_bps=40.0, cost_bps=2.6, funding_bps=0.0, net_bps=37.4, exit_reason="exit",
         n_deferred=0, n_settlements=0, excluded_gap=False, regime="lightning_fx"),
    # 2 (c): short 1,000,000, stop level 1,010,000 hit by high(8) = 1,012,000, filled at
    #   open(9) = 1,015,000 (adverse gap kept): gross -(1.015-1)*1e4 = -150.0 ; net -152.6
    dict(entry_ts=ts(7), exit_ts=ts(9), side=-1, entry_px=1_000_000.0, exit_px=1_015_000.0,
         gross_bps=-150.0, cost_bps=2.6, funding_bps=0.0, net_bps=-152.6, exit_reason="stop",
         n_deferred=0, n_settlements=0, excluded_gap=False, regime="lightning_fx"),
    # 3 (d)(e): signal at 11, bar 12 empty -> entry open(13) = 1,000,000 (1 deferral);
    #   holds 04:53 -> 05:03 across the 05:00 settlement (1 x 0.02% = 2.0 bps);
    #   exit open(23) = 1,003,000: gross 30.0 ; net 30 - 2.6 - 2.0 = 25.4
    dict(entry_ts=ts(13), exit_ts=ts(23), side=1, entry_px=1_000_000.0, exit_px=1_003_000.0,
         gross_bps=30.0, cost_bps=2.6, funding_bps=2.0, net_bps=25.4, exit_reason="exit",
         n_deferred=1, n_settlements=1, excluded_gap=False, regime="lightning_fx"),
    # 4 (f): short 1,000,000 at open(25); bars 30..35 empty (valid 29 -> 36 = 7 min > 5)
    #   while holding; exit signal 36, fill open(37) = 990,000: gross -(0.99-1)*1e4 = +100.0 ;
    #   net 97.4 ; EXCLUDED (the signal at 24 is 5 bars before the run's t_a = 29: kept)
    dict(entry_ts=ts(25), exit_ts=ts(37), side=-1, entry_px=1_000_000.0, exit_px=990_000.0,
         gross_bps=100.0, cost_bps=2.6, funding_bps=0.0, net_bps=97.4, exit_reason="exit",
         n_deferred=0, n_settlements=0, excluded_gap=True, regime="lightning_fx"),
    # 5 (c)(d)(f): signals at 38 (t_a - 1) and 42 (inside the run 40..45) are DISCARDED;
    #   signal 46 kept -> long 1,000,000 at open(47); low(47) = 989,000 <= 990,000 stop on the
    #   entry bar; bar 48 empty -> stop filled at open(49) = 985,000 (1 deferral):
    #   gross (0.985-1)*1e4 = -150.0 ; net -152.6
    dict(entry_ts=ts(47), exit_ts=ts(49), side=1, entry_px=1_000_000.0, exit_px=985_000.0,
         gross_bps=-150.0, cost_bps=2.6, funding_bps=0.0, net_bps=-152.6, exit_reason="stop",
         n_deferred=1, n_settlements=0, excluded_gap=False, regime="lightning_fx"),
]
# daily pnl 2023-06-01 (excluded trade 4 dropped): 37.4 - 152.6 + 25.4 - 152.6 = -242.4
EXPECTED_DAILY_BPS = -242.4
TOL = 1e-9


def run_known_answer(bf: pd.DataFrame | None = None, **kw) -> pd.DataFrame:
    bf = make_bf() if bf is None else bf
    m = momentum_signal(make_binance(), K)
    return simulate(bf, m, thr=THR, exit_=EXIT, stop=STOP, cost_one_way_bps=COST_1W,
                    funding_pct_per_settlement=0.02, funding_times_utc=(5, 13, 21),
                    max_gap_min=5, **kw)


def _check_rows(ledger: pd.DataFrame, expected: list[dict]) -> None:
    assert list(ledger.columns) == LEDGER_COLUMNS
    assert len(ledger) == len(expected)
    for row, exp in zip(ledger.to_dict("records"), expected):
        for key, want in exp.items():
            got = row[key]
            if isinstance(want, float):
                assert abs(got - want) <= TOL, (key, got, want)
            elif isinstance(want, pd.Timestamp):
                assert pd.Timestamp(got) == want, (key, got, want)
            else:
                assert got == want, (key, got, want)


def test_known_answer_five_trades():
    ledger = run_known_answer()
    _check_rows(ledger, EXPECTED)
    assert len(ledger) == 5
    # descriptive extras
    assert ledger["n_deferred_entry"].tolist() == [0, 0, 1, 0, 0]
    assert ledger["n_deferred_exit"].tolist() == [0, 0, 0, 0, 1]
    assert ledger["hold_min"].tolist() == [2.0, 2.0, 10.0, 12.0, 2.0]
    assert ledger["straddles_gap"].tolist() == [False, False, False, True, False]
    assert ledger["entry_signal_ts"].tolist() == [ts(1), ts(6), ts(11), ts(24), ts(46)]
    assert ledger["exit_signal_ts"].tolist() == [ts(3), ts(8), ts(22), ts(36), ts(47)]
    # 0.01 BTC at 1,000,000 JPY -> 1 bps == 1 JPY, so pnl_jpy equals net_bps numerically
    np.testing.assert_allclose(ledger["pnl_jpy"], ledger["net_bps"], atol=TOL)
    # counts for the RESULTS tables
    a = ledger.attrs
    assert a["apply_masks"] is True
    assert a["n_entry_signal_bars"] == 7          # bars 1, 6, 11, 24, 38, 42, 46
    assert a["n_entry_signals_discarded"] == 2    # 38 and 42
    assert a["n_big_gaps"] == 2
    assert a["n_misprint_rows_blanked"] == 0
    assert a["n_excluded_gap"] == 1 and a["n_straddles_gap"] == 1
    assert a["n_deferred_total"] == 2


def test_known_answer_daily_pnl_and_sharpe():
    ledger = run_known_answer()
    d = daily_pnl(ledger)
    assert len(d) == 1
    assert d.index[0] == pd.Timestamp("2023-06-01", tz="UTC")
    assert abs(float(d.iloc[0]) - EXPECTED_DAILY_BPS) <= TOL
    # including the excluded trade: -242.4 + 97.4 = -145.0
    d_all = daily_pnl(ledger, include_excluded=True)
    assert abs(float(d_all.iloc[0]) - (-145.0)) <= TOL
    assert np.isnan(sharpe_annual(d))          # a single day has no sd
    # hand-checked Sharpe: [1, 2, 3] -> mean 2, sd 1, * sqrt(365)
    assert abs(sharpe_annual(pd.Series([1.0, 2.0, 3.0])) - 2.0 * np.sqrt(365)) < 1e-12
    assert np.isnan(sharpe_annual(pd.Series([1.0, 1.0])))
    # daily series spans every calendar day between first and last exit
    two = ledger.copy()
    two.loc[two.index[-1], "exit_ts"] = ts(49) + pd.Timedelta(days=2)
    d2 = daily_pnl(two)
    assert len(d2) == 3 and float(d2.iloc[1]) == 0.0


def test_known_answer_without_masks_hand_computed():
    """apply_masks=False: no discard, deferral across any blank, nothing excluded.
    The signal at 38 now becomes a trade: long open(39) = 1,000,000; m(39) = 0 -> exit
    signal at 39, fill deferred across 40..45 to open(46) = 1,000,000 (6 deferrals):
    gross 0 ; net -2.6 ; straddles the gap but is NOT excluded. Trade 4 keeps its
    numbers with excluded_gap False. Then 46 (flat again) -> trade 5 as before."""
    ledger = run_known_answer(apply_masks=False)
    exp = [dict(e) for e in EXPECTED]
    exp[3]["excluded_gap"] = False
    t4b = dict(entry_ts=ts(39), exit_ts=ts(46), side=1, entry_px=1_000_000.0,
               exit_px=1_000_000.0, gross_bps=0.0, cost_bps=2.6, funding_bps=0.0,
               net_bps=-2.6, exit_reason="exit", n_deferred=6, n_settlements=0,
               excluded_gap=False, regime="lightning_fx")
    _check_rows(ledger, exp[:4] + [t4b] + exp[4:])
    assert ledger["straddles_gap"].tolist() == [False, False, False, True, True, False]
    assert ledger.attrs["n_entry_signals_discarded"] == 0
    assert ledger.attrs["apply_masks"] is False
    # -242.4 + 97.4 - 2.6 = -147.6 (nothing dropped)
    assert abs(float(daily_pnl(ledger).iloc[0]) - (-147.6)) <= TOL


def test_known_answer_time_jump_variant_matches_empty_rows():
    """The same story with the empty rows REMOVED instead of NaN: identical
    ledger (absent rows and empty rows are the same thing to the rules)."""
    drop = [ts(i) for i in list(range(30, 36)) + list(range(40, 46)) + [48]]
    bf = make_bf().drop(index=drop)
    ledger = run_known_answer(bf)
    _check_rows(ledger, EXPECTED)
    g = big_gaps(bf, 5)
    assert g["kind"].tolist() == ["time_jump", "time_jump"]
    assert g["missing_min"].tolist() == [6, 6]
    g0 = big_gaps(make_bf(), 5)
    assert g0["kind"].tolist() == ["empty_rows", "empty_rows"]
    assert g0["gap_min"].tolist() == [7.0, 7.0]
    assert g0["t_a"].tolist() == [ts(29), ts(39)] and g0["t_b"].tolist() == [ts(36), ts(46)]


def test_gap_rule_boundary():
    """max_gap_min=5 == consecutive valid bars more than 5 minutes apart
    (the gaps_gt5min.txt convention). Empties 30..33 (29 -> 34, 5 min) is NOT a
    gap; empties 30..34 (29 -> 35, 6 min) is."""
    bf = make_bf()
    bf.loc[[ts(34), ts(35)]] = DEFAULT_BAR
    ledger = run_known_answer(bf)
    assert ledger["excluded_gap"].tolist() == [False] * 5
    assert ledger.attrs["n_big_gaps"] == 1
    bf.loc[ts(34)] = EMPTY
    ledger = run_known_answer(bf)
    assert ledger["excluded_gap"].tolist() == [False, False, False, True, False]
    assert ledger.attrs["n_big_gaps"] == 2


def _discard_fixture(signal_bar: int):
    """40 default bars, empties 20..25 (t_a = 19, t_b = 26); one 2% Binance jump at
    ``signal_bar`` (m = +2% there, 0 elsewhere)."""
    idx = pd.date_range("2023-06-02 10:00", periods=40, freq="min", tz="UTC")
    bf = pd.DataFrame([DEFAULT_BAR] * 40, columns=["open", "high", "low", "close"], index=idx)
    bf.iloc[20:26] = np.nan
    c = np.where(np.arange(40) >= signal_bar, 102.0, 100.0)
    return bf, momentum_signal(pd.Series(c, index=idx), 1)


def test_discard_window_is_five_minutes_before_the_run():
    """Signal at t_a - 4 (bar 15) is discarded; at t_a - 5 (bar 14) it is kept."""
    bf, m = _discard_fixture(15)
    led = simulate(bf, m, THR, EXIT, STOP, COST_1W)
    assert len(led) == 0 and led.attrs["n_entry_signals_discarded"] == 1
    bf, m = _discard_fixture(14)
    led = simulate(bf, m, THR, EXIT, STOP, COST_1W)
    assert len(led) == 1 and led.attrs["n_entry_signals_discarded"] == 0
    assert led.iloc[0]["entry_ts"] == bf.index[15] and led.iloc[0]["exit_ts"] == bf.index[16]
    # signal at t_a itself (bar 19) would fill inside the run: discarded, not deferred
    bf, m = _discard_fixture(19)
    led = simulate(bf, m, THR, EXIT, STOP, COST_1W)
    assert len(led) == 0 and led.attrs["n_entry_signals_discarded"] == 1
    led = simulate(bf, m, THR, EXIT, STOP, COST_1W, apply_masks=False)
    assert len(led) == 1 and led.iloc[0]["entry_ts"] == bf.index[26]   # deferred across the run
    assert led.iloc[0]["n_deferred"] == 6 and not led.iloc[0]["excluded_gap"]


def test_misprint_mask_blanks_spike_that_reverts():
    idx = pd.date_range("2023-06-03 10:00", periods=40, freq="min", tz="UTC")
    bf = pd.DataFrame([DEFAULT_BAR] * 40, columns=["open", "high", "low", "close"], index=idx)
    bf.iloc[10] = (1_000_000.0, 1_400_000.0, 1_000_000.0, 1_400_000.0)   # +40% then back
    bf.iloc[30] = (1_000_000.0, 1_400_000.0, 1_000_000.0, 1_400_000.0)   # +40% ...
    bf.iloc[31] = (1_400_000.0, 1_400_000.0, 1_390_000.0, 1_390_000.0)   # ... and stays: genuine
    mp = misprint_mask(bf)
    assert mp.sum() == 1 and bool(mp.iloc[10]) and not bool(mp.iloc[30])
    # short from open(8): the spike bar would stop it out; masked it does not
    c = [100.0] * 7 + [98.8, 98.4, 98.0, 97.6, 97.2] + [97.2] * 28   # SELL at 7, exit signal at 12
    m = momentum_signal(pd.Series(c, index=idx), 1)
    with_mask = simulate(bf.iloc[:20], m, THR, EXIT, STOP, COST_1W)
    without = simulate(bf.iloc[:20], m, THR, EXIT, STOP, COST_1W, apply_masks=False)
    assert with_mask.attrs["n_misprint_rows_blanked"] == 1
    assert with_mask.iloc[0]["exit_reason"] == "exit" and with_mask.iloc[0]["exit_ts"] == idx[13]
    assert without.iloc[0]["exit_reason"] == "stop" and without.iloc[0]["exit_ts"] == idx[11]


def test_stop_and_exit_same_bar_labelled_stop():
    """If a bar triggers both the stop and |m| < exit, the fill is the same
    (next open) and the reason is recorded as 'stop'."""
    bn = make_binance()
    bn.iloc[8] = 100.0                              # m(8) = 0 -> exit signal too
    ledger = simulate(make_bf(), momentum_signal(bn, K), THR, EXIT, STOP, COST_1W)
    assert ledger.iloc[1]["exit_reason"] == "stop"
    assert ledger.iloc[1]["exit_ts"] == ts(9)


def test_end_of_data_close():
    """Holding at the end of the series: closed at the last valid bar's close
    with reason 'end'."""
    bf = make_bf().iloc[:15]                        # trade 3 is open at bar 14
    ledger = run_known_answer(bf)
    last = ledger.iloc[-1]
    assert last["exit_reason"] == "end"
    assert last["exit_ts"] == ts(14)
    assert last["exit_px"] == DEFAULT_BAR[3]
    assert abs(last["gross_bps"] - 0.0) <= TOL and abs(last["net_bps"] - (-2.6)) <= TOL


def test_settlement_counting_convention():
    """entry_ts < s <= exit_ts: an exit filled AT 05:00 pays, an entry filled
    AT 05:00 does not; three instants per day."""
    d = pd.Timestamp("2023-06-01", tz="UTC")
    h = lambda x: d + pd.Timedelta(hours=x)  # noqa: E731
    assert count_settlements(h(4.98), h(5)) == 1
    assert count_settlements(h(5), h(5.02)) == 0
    assert count_settlements(h(4), h(22)) == 3
    assert count_settlements(h(4), h(4) + pd.Timedelta(days=1)) == 3
    assert count_settlements(h(6), h(12)) == 0
    assert count_settlements(h(6), h(7), funding_times_utc=(6.5,)) == 1


def test_regime_column():
    assert regime_of(pd.Timestamp("2023-12-17 23:59", tz="UTC")) == "lightning_fx"
    assert regime_of(pd.Timestamp("2024-03-27 23:59", tz="UTC")) == "lightning_fx"
    assert regime_of(pd.Timestamp("2024-03-28 00:00", tz="UTC")) == "crypto_cfd"
    shifted = make_bf().copy()
    shifted.index = shifted.index + pd.Timedelta(days=400)     # 2024-07-05
    bn = make_binance()
    bn.index = shifted.index
    led = simulate(shifted, momentum_signal(bn, K), THR, EXIT, STOP, COST_1W)
    assert set(led["regime"]) == {"crypto_cfd"}


def test_simulate_rejects_bad_inputs():
    with pytest.raises(ValueError):
        simulate(make_bf(), momentum_signal(make_binance(), K), -1.0, EXIT, STOP, COST_1W)
    with pytest.raises(ValueError):
        simulate(make_bf().drop(columns=["low"]), momentum_signal(make_binance(), K),
                 THR, EXIT, STOP, COST_1W)
    with pytest.raises(ValueError):
        simulate(make_bf().iloc[::-1], momentum_signal(make_binance(), K), THR, EXIT, STOP, COST_1W)


# ---- momentum_signal ---------------------------------------------------------

def test_momentum_signal_by_time_not_position():
    idx = pd.DatetimeIndex([T0 + pd.Timedelta(minutes=i) for i in (0, 1, 2, 4, 5)])
    close = pd.Series([100.0, 110.0, 121.0, 133.1, 146.41], index=idx)
    m = momentum_signal(close, 1)
    assert np.isnan(m.iloc[0])
    assert abs(m.iloc[1] - 0.1) < 1e-12 and abs(m.iloc[2] - 0.1) < 1e-12
    assert np.isnan(m.iloc[3])                      # t-1 = minute 3 is absent -> NaN, not row-shifted
    assert abs(m.iloc[4] - 0.1) < 1e-12
    m2 = momentum_signal(close, 2)
    assert np.isnan(m2.iloc[0]) and np.isnan(m2.iloc[1])
    assert abs(m2.iloc[2] - 0.21) < 1e-12           # 121/100 - 1
    assert abs(m2.iloc[3] - 0.1) < 1e-12            # 133.1/121 - 1 (minute 4 vs minute 2)
    assert np.isnan(m2.iloc[4])                     # minute 3 absent
    assert list(m.index) == list(idx)


def test_momentum_signal_rejects_bad_k_and_unsorted_index():
    with pytest.raises(ValueError):
        momentum_signal(make_binance(), 0)
    with pytest.raises(ValueError):
        momentum_signal(make_binance().iloc[::-1], 1)


# ---- block_permute_log_returns -----------------------------------------------

def _synthetic_close(days: int = 5, seed: int = 1) -> pd.Series:
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2023-06-01", periods=days * 1440, freq="min", tz="UTC")
    r = rng.normal(0, 1e-3, len(idx))
    return pd.Series(100.0 * np.exp(np.cumsum(r)), index=idx, name="close")


def test_block_permute_preserves_total_log_return_first_level_and_daily_order():
    close = _synthetic_close()
    out = block_permute_log_returns(close, np.random.default_rng(7), block="D")
    assert list(out.index) == list(close.index)
    assert out.iloc[0] == close.iloc[0]
    assert out.notna().all()
    assert abs(np.log(out.iloc[-1] / out.iloc[0]) - np.log(close.iloc[-1] / close.iloc[0])) < 1e-9
    # daily blocks of returns survive intact (internal order kept), in some order
    r_orig = np.diff(np.log(close.to_numpy()))
    r_perm = np.diff(np.log(out.to_numpy()))
    day = close.index[1:].floor("D")
    blocks_orig = [r_orig[np.asarray(day == d)] for d in day.unique()]
    used = [False] * len(blocks_orig)
    pos = 0
    for _ in blocks_orig:
        matched = False
        for bi, blk in enumerate(blocks_orig):
            if used[bi]:
                continue
            seg = r_perm[pos:pos + len(blk)]
            if len(seg) == len(blk) and np.allclose(seg, blk, atol=1e-9):
                used[bi] = True
                pos += len(blk)
                matched = True
                break
        assert matched, "a daily block was not found contiguous in the permuted series"
    assert all(used) and pos == len(r_perm)
    # actually permuted (not the identity) for this seed
    assert not np.allclose(out.to_numpy(), close.to_numpy())


def test_block_permute_keeps_nans_and_is_reproducible():
    close = _synthetic_close(days=3)
    close.iloc[100:110] = np.nan
    a = block_permute_log_returns(close, np.random.default_rng(3))
    b = block_permute_log_returns(close, np.random.default_rng(3))
    assert a.isna().to_numpy().tolist() == close.isna().to_numpy().tolist()
    np.testing.assert_allclose(a.dropna(), b.dropna())
    valid = close.dropna()
    a_valid = a.dropna()
    assert abs(np.log(a_valid.iloc[-1] / a_valid.iloc[0])
               - np.log(valid.iloc[-1] / valid.iloc[0])) < 1e-9
