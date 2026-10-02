"""Card 6 of W4 (週末ギャップの1時間平均回帰): hand-made small inputs whose exposures are known.

Each test names the item of docs/RESEARCH/cards/c6_weekend_gap_revert/INTENT_MAP.md it checks.
Clock of the inputs (UTC): FRI = Friday 2024-01-05 00:00, SUN = Sunday 2024-01-07 00:00. The JST week changes at
Monday 2024-01-08 00:00 JST = SUN + 15 h. USDJPY rows are stamped at the START of their minute with lag 60 s (as in
the store, not shifted; CARD.md 測定の設定), so the row of minute m becomes available at the end of minute m.
bitFlyer bars need not be contiguous (a missing minute is a minute with no trade; the card is not called there).

Base weekend: the last quote change before the closure is the row FRI 21:59 (close 144.40); flat rows at 144.40
follow on Friday night and on Sunday (the store's Sunday day files have rows; CARD.md 使うデータと遅れ), including
SUN 15:00 (the first row of the new JST week, still flat); the first new-week row off 144.40 is SUN 22:00 = R.
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from bot.bt.core import BarEvent
from bot.bt.data.reference import reference_series
from bot.research.cards import SeriesSpec, run_card
from bot.research.cards.library.c6_weekend_gap_revert import FX, GAPS, HOLD_NS, WeekendGapRevert, jst_week_index

NS = 1_000_000_000
M = 60 * NS
H = 60 * M
FRI = 1_704_412_800 * NS  # 2024-01-05T00:00:00Z, a Friday
SUN = FRI + 2 * 24 * H  # 2024-01-07T00:00:00Z, a Sunday
R = SUN + 22 * H  # the week-open row of the base weekend
DECL = {FX: {"lag_ns": 60 * NS, "source": "試験の入力"}}


def base_fx(open_close=145.00):
    rows = [(FRI + 21 * H + 55 * M + k * M, 144.00 + 0.10 * k) for k in range(5)]  # 21:55..21:59, last 144.40
    rows += [(FRI + 22 * H, 144.40), (FRI + 23 * H + 59 * M, 144.40)]  # flat while shut (Friday night)
    rows += [(SUN, 144.40), (SUN + 14 * H + 59 * M, 144.40), (SUN + 15 * H, 144.40), (R - M, 144.40)]
    rows += [(R, open_close)] + [(R + k * M, open_close + 0.01 * k) for k in range(1, 70)]
    return rows


def base_bars(fri_close=6_000_000.0, open_bar_close=5_900_000.0, skip=()):
    """bitFlyer bars: FRI 21:50..22:09 and SUN 21:50..23:09 (start times). The bar starting R closes at
    `open_bar_close`; other Sunday bars at 5,950,000."""
    starts = [FRI + 21 * H + 50 * M + k * M for k in range(20)] + [R - 10 * M + k * M for k in range(80)]
    out = []
    for s in starts:
        if s in skip:
            continue
        c = fri_close if s < SUN else (open_bar_close if s == R else 5_950_000.0)
        out.append((s, c))
    return out


def run(gap, fx_rows, bars):
    evs = [BarEvent(received_time_ns=s + M, exchange_time_ns=s + M, start_time_ns=s, open=c, close=c, high=c,
                    low=c, volume=1.0) for s, c in bars]
    refs = {FX: reference_series(FX, fx_rows, declarations=DECL)}
    r = run_card(WeekendGapRevert(gap), evs, references=refs, declarations=DECL, venue="bitflyer",
                 symbol="FX_BTC_JPY")
    ends = np.array([s + M for s, _ in bars], dtype=np.int64)
    return ends, np.asarray(r.exposure)


def by_end(ends, x):
    return {int(t): float(e) for t, e in zip(ends, x)}


def test_mouth_and_clock():
    c = WeekendGapRevert("usdjpy")
    assert c.name == "c6_weekend_gap_revert_usdjpy"
    assert tuple(c.requires) == (SeriesSpec(FX, 60 * NS),)
    assert set(GAPS) == {"usdjpy", "btc"}
    assert HOLD_NS == 3_600 * NS
    for bad in ("fx", "1h", None):
        with pytest.raises(ValueError):
            WeekendGapRevert(bad)
    # The JST week changes at Monday 00:00 JST = Sunday 15:00 UTC, not at Sunday 00:00 UTC or Monday 00:00 UTC.
    assert jst_week_index(SUN + 15 * H - NS) + 1 == jst_week_index(SUN + 15 * H)
    assert jst_week_index(FRI) == jst_week_index(SUN)
    assert jst_week_index(SUN + 15 * H) == jst_week_index(SUN + 39 * H - NS)


def test_i3_i4_hold_against_the_usdjpy_gap_for_the_first_hour():
    """I-3 (最初の1時間) and I-4 (縮小(回帰) -> hold against the gap), variant "usdjpy". A gap up (144.40 -> 145.00)
    sells from the bar ending R + 1 min to the bar ending R + 59 min; the bar ending R + 60 min returns 0."""
    ends, x = run("usdjpy", base_fx(145.00), base_bars())
    e = by_end(ends, x)
    assert all(e[t] == 0.0 for t in e if t < R + M)
    assert all(e[t] == -1.0 for t in e if R + M <= t < R + HOLD_NS)
    assert all(e[t] == 0.0 for t in e if t >= R + HOLD_NS)
    assert sum(1 for t in e if R + M <= t < R + HOLD_NS) == 59
    ends, x = run("usdjpy", base_fx(143.80), base_bars())  # a gap down buys
    e = by_end(ends, x)
    assert all(e[t] == 1.0 for t in e if R + M <= t < R + HOLD_NS)


def test_i2_btc_variant_is_the_bitflyer_move_over_the_closure():
    """I-2 (variant "btc"): g = ln(bitFlyer as of the end of the open row) - ln(bitFlyer as of the end of the last
    quote change, FRI 22:00). 6,000,000 -> 5,900,000 is a fall: buy, whatever the USDJPY gap's sign."""
    ends, x = run("btc", base_fx(145.00), base_bars(6_000_000.0, 5_900_000.0))
    e = by_end(ends, x)
    assert all(e[t] == 1.0 for t in e if R + M <= t < R + HOLD_NS)
    assert all(e[t] == 0.0 for t in e if t < R + M or t >= R + HOLD_NS)
    ends, x = run("btc", base_fx(145.00), base_bars(6_000_000.0, 6_100_000.0))  # a rise: sell
    assert all(v == -1.0 for t, v in by_end(ends, x).items() if R + M <= t < R + HOLD_NS)
    ends, x = run("btc", base_fx(145.00), base_bars(6_000_000.0, 6_000_000.0))  # no move: 0 throughout
    assert np.all(x == 0.0)


def test_i1_flat_rows_while_shut_are_not_the_open():
    """I-1 / C-5: the open is the first new-week row whose close differs from the earlier week's last close.
    (a) A row at SUN 15:00 that differs (144.90) is the open: hold for the hour after it.
    (b) The base weekend: SUN 15:00 is flat (144.40), so it is not the open; with bars around SUN 15:00 the card
    holds 0 there and holds only after R."""
    fx = [row for row in base_fx(145.00) if row[0] < SUN + 15 * H] + [(SUN + 15 * H, 144.90)]
    fx += [(SUN + 15 * H + k * M, 144.90) for k in range(1, 5)]
    bars = [(SUN + 15 * H + k * M, 5_950_000.0) for k in range(-3, 70)]
    ends, x = run("usdjpy", fx, bars)
    e = by_end(ends, x)
    r = SUN + 15 * H
    assert all(e[t] == -1.0 for t in e if r + M <= t < r + HOLD_NS)
    assert all(e[t] == 0.0 for t in e if t < r + M or t >= r + HOLD_NS)
    # The base weekend: rows at SUN 15:00 and R - 1 min are flat; the open is R, not SUN 15:00.
    bars = [(SUN + 15 * H + k * M, 5_950_000.0) for k in range(0, 70)] + base_bars()[20:]
    ends, x = run("usdjpy", base_fx(145.00), sorted(set(bars)))
    e = by_end(ends, x)
    assert all(e[t] == 0.0 for t in e if t < R + M)
    assert all(e[t] == -1.0 for t in e if R + M <= t < R + HOLD_NS)


def test_c4_a_midweek_holiday_gap_is_not_a_week_open():
    """C-4: a one-day gap Tue -> Thu inside one JST week is not a week open (the card holds 0)."""
    tue = FRI - 3 * 24 * H  # Tuesday 2024-01-02 00:00 UTC
    fx = [(tue + 23 * H + k * M, 141.0 + 0.01 * k) for k in range(5)]
    fx += [(tue + 2 * 24 * H + k * M, 142.0 + 0.01 * k) for k in range(70)]  # Thursday, a jump of about 1 yen
    bars = [(tue + 2 * 24 * H + k * M, 5_950_000.0) for k in range(70)]
    for g in GAPS:
        _, x = run(g, fx, bars)
        assert np.all(x == 0.0)


def test_c6_the_first_row_ever_has_no_earlier_week():
    """C-6: when the series starts in the new week, there is no earlier close, no gap, and the card holds 0."""
    fx = [row for row in base_fx(145.00) if row[0] >= SUN + 15 * H]
    for g in GAPS:
        _, x = run(g, fx, base_bars())
        assert np.all(x == 0.0)


def test_c8_empty_bitflyer_minute_at_the_open():
    """C-8: no bitFlyer trade in minute R (the bar ending R + 1 min is missing). The card still finds the open row
    at its next call (bar ending R + 2 min) and holds from there. Variant "btc": bitFlyer as of R + 1 min is the
    bar of the previous call (ending R, close 5,950,000), so 6,000,000 -> 5,950,000 is a fall: buy."""
    bars = base_bars(skip=(R,))
    ends, x = run("usdjpy", base_fx(145.00), bars)
    e = by_end(ends, x)
    assert R + M not in e
    assert e[R + 2 * M] == -1.0
    ends, x = run("btc", base_fx(145.00), bars)
    e = by_end(ends, x)
    assert e[R + 2 * M] == 1.0
    assert all(e[t] == 1.0 for t in e if R + M <= t < R + HOLD_NS)


def test_c7_btc_reference_when_the_last_quote_change_minute_has_no_bitflyer_bar():
    """C-7: the last quote change is FRI 21:59 (available at FRI 22:00). With no bitFlyer bar starting 21:59, the
    reference is the bar of the previous call (ending 21:59). Make that bar 5,800,000 and the open bar 5,900,000:
    a rise from the reference: sell (while the FRI 22:00-ending bar, if used, would give a fall)."""
    s_ref = FRI + 21 * H + 58 * M
    bars = [(s, (5_800_000.0 if s == s_ref else c)) for s, c in base_bars(skip=(FRI + 21 * H + 59 * M,))]
    ends, x = run("btc", base_fx(145.00), bars)
    assert all(v == -1.0 for t, v in by_end(ends, x).items() if R + M <= t < R + HOLD_NS)


def test_no_bitflyer_bar_in_the_first_hour_holds_nothing():
    bars = [(s, c) for s, c in base_bars() if not (R - 10 * M <= s < R + HOLD_NS - M)]
    for g in GAPS:
        _, x = run(g, base_fx(145.00), bars)
        assert np.all(x == 0.0)


def test_no_look_ahead():
    """The open row R becomes available only at R + 1 min: changing its value (or any later row or bar) does not
    change any exposure before R + 1 min."""
    ends, a = run("usdjpy", base_fx(145.00), base_bars())
    _, b = run("usdjpy", base_fx(143.80), base_bars())
    early = ends < R + M
    np.testing.assert_array_equal(a[early], b[early])
    assert not np.array_equal(a[~early], b[~early])
    bars = [(s, (1.0 if s >= R else c)) for s, c in base_bars()]  # later bitFlyer bars changed
    _, c = run("btc", base_fx(145.00), bars)
    _, d = run("btc", base_fx(145.00), base_bars())
    np.testing.assert_array_equal(c[early], d[early])


def test_rows_with_another_lag_are_refused():
    from bot.research.cards import CardError
    decl0 = {FX: {"lag_ns": 0, "source": "試験の入力"}}
    evs = [BarEvent(received_time_ns=R + M, exchange_time_ns=R + M, start_time_ns=R, open=1.0, close=1.0, high=1.0,
                    low=1.0, volume=1.0)]
    refs = {FX: reference_series(FX, [(R, 145.0)], declarations=decl0)}
    with pytest.raises(CardError):
        run_card(WeekendGapRevert("usdjpy"), evs, references=refs, declarations=decl0, venue="bitflyer",
                 symbol="FX_BTC_JPY")


def test_same_input_same_output_and_bounds():
    for g in GAPS:
        _, a = run(g, base_fx(145.00), base_bars())
        _, b = run(g, base_fx(145.00), base_bars())
        np.testing.assert_array_equal(a, b)
        assert set(np.unique(a)) <= {-1.0, 0.0, 1.0}
        assert np.any(a != 0.0)



def test_i5_i7a_a_one_tick_gap_holds_in_full():
    """I-5 (no selection of weeks) and I-7a (no size or volatility filter): a one-tick USDJPY gap (144.40 ->
    144.401) and a 1-yen bitFlyer move still hold the full -1 / +1 for the 59 bars."""
    ends, x = run("usdjpy", base_fx(144.401), base_bars())
    e = by_end(ends, x)
    held = [t for t in e if R + M <= t < R + HOLD_NS]
    assert len(held) == 59 and all(e[t] == -1.0 for t in held)
    ends, x = run("btc", base_fx(145.00), base_bars(6_000_000.0, 5_999_999.0))
    e = by_end(ends, x)
    assert all(e[t] == 1.0 for t in held)
