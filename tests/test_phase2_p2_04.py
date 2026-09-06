"""P2-04 (JPX calendar anomalies) — the tests the frozen PREREG requires
before the unit may be run.

PREREG「執行様式のパイプライン既知正解テスト」: the daily/板寄せ pipeline itself
already has a known-answer record, but "**暦規則の日付集合の生成**(祝日導出・
第 2 金曜・月替わり)は既知正解が無いので、手作りカレンダー(2 年分)で各規則の
日付を手計算した表と突き合わせるテストを追加してから実行する".

So this module holds:

  1. a HAND-MADE 2-year synthetic trading calendar (2021-2022, Mon-Fri minus a
     hand-listed set of holidays) whose TOM / 2nd-Friday / holiday-eve dates
     are written out BY HAND below and asserted exactly, plus the mechanical
     holiday derivation that has to reproduce the hand-listed holiday set;
  2. the placebo fold-back rule (PREREG 対照 2: a shifted date that lands back
     inside the original rule set is removed from the placebo set and counted);
  3. a planted-effect recovery: a synthetic tape with a known edge planted on
     one rule's days must come back through the same statistics the run script
     uses.
"""
from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.phase2.p2_04_run import (  # noqa: E402
    ITER1_OUT_DIR,
    OUT_DIR,
    RULES,
    SIGN_LABELS,
    TERCILE_LABELS,
    build_close_pairs,
    build_rule_day_sets,
    derive_holidays,
    diff_ci,
    etf_tick_yen,
    holiday_eves,
    label_sign,
    label_tercile,
    major_sq_marked_days,
    main,
    mean_ci,
    primary_series_vol20,
    prior_day_sign,
    run_iteration1,
    run_iteration2,
    second_friday,
    shift_trading_days,
    sq_days,
    tercile_cutpoints,
    tom_days,
    weekday_days,
)

# ---------------------------------------------------------------------------
# 1. the hand-made 2-year calendar
# ---------------------------------------------------------------------------

# Hand-listed closures for the synthetic exchange. Chosen to exercise every
# branch of the rules: a holiday ON a 2nd Friday (2021-05-14 -> SQ shifts back
# to Thu 2021-05-13), a holiday on the LAST business day of a month
# (2021-09-30 -> the month's last TRADING day becomes 2021-09-29), a holiday on
# the FIRST business day of a month (2022-08-01), a two-day block
# (2022-03-21..22), and the year-end/new-year break, which the derivation must
# treat as holidays even where the dates fall on a weekend.
HAND_HOLIDAYS = [
    "2021-01-01", "2021-02-11", "2021-05-14", "2021-07-22", "2021-09-30",
    "2021-11-03", "2021-12-31",
    "2022-01-03", "2022-03-21", "2022-03-22", "2022-05-05", "2022-08-01",
    "2022-11-23", "2022-12-30",
]


def _hand_calendar() -> list[date]:
    """Every Mon-Fri of 2021-01-01..2022-12-31 except HAND_HOLIDAYS.

    Built by walking the calendar, not by copying the production code, so the
    two implementations only agree if the rules really match.
    """
    closed = {pd.Timestamp(d).date() for d in HAND_HOLIDAYS}
    out: list[date] = []
    cur, last = date(2021, 1, 1), date(2022, 12, 31)
    while cur <= last:
        if cur.weekday() < 5 and cur not in closed:
            out.append(cur)
        cur += timedelta(days=1)
    return out


def _d(*dates: str) -> list[date]:
    return [pd.Timestamp(x).date() for x in dates]


CAL = _hand_calendar()


def test_hand_calendar_shape():
    """The synthetic calendar is what the hand-listed answers below assume."""
    assert CAL[0] == date(2021, 1, 4)          # 2021-01-01 is a listed holiday
    assert CAL[-1] == date(2022, 12, 29)       # 2022-12-30 is a listed holiday
    # 2021-01-01..2022-12-31 holds 521 weekdays; all 14 hand-listed closures
    # fall on a weekday, so the synthetic exchange trades 507 days.
    assert len(CAL) == 521 - 14 == 507
    assert all(pd.Timestamp(h).weekday() < 5 for h in HAND_HOLIDAYS)
    assert all(d.weekday() < 5 for d in CAL)


def test_derive_holidays_reproduces_the_hand_list():
    """The mechanical rule must recover exactly the closures inside the span.

    The span starts at the first TRADING day (2021-01-04) and ends at the last
    (2022-12-29), so 2021-01-01 and 2022-12-30/31 fall outside it and are not
    derivable; every other hand-listed closure must come back, and nothing else
    may (in particular no weekend, since 週末は含めない).
    """
    got = set(derive_holidays(CAL))
    hand_inside = {pd.Timestamp(d).date() for d in HAND_HOLIDAYS
                   if CAL[0] < pd.Timestamp(d).date() < CAL[-1]}
    # the only additions are the two WEEKEND new-year dates the year-end clause
    # adds on purpose (asserted in the next test); nothing else appears.
    assert got - hand_inside == {date(2022, 1, 1), date(2022, 1, 2)}
    assert hand_inside <= got
    assert all(h.weekday() < 5 or h.month in (1, 12) for h in got)


def test_derive_holidays_treats_year_end_new_year_as_holidays():
    """12-31 / 01-01..01-03 count even when they fall on a weekend.

    2022-01-01 is a Saturday and 2022-01-02 a Sunday; both are inside the span
    and neither is a trading day, so the year-end/new-year clause (and not the
    weekday clause) has to put them in the holiday set.
    """
    got = set(derive_holidays(CAL))
    assert date(2022, 1, 1) in got and date(2022, 1, 1).weekday() == 5
    assert date(2022, 1, 2) in got and date(2022, 1, 2).weekday() == 6
    assert date(2022, 1, 3) in got
    # an ordinary weekend day is NOT a holiday
    assert date(2021, 6, 5) not in got and date(2021, 6, 6) not in got


def test_holiday_eves_hand_listed():
    """PH: the trading day immediately before each derived holiday.

    Hand-computed from the calendar above:
      2021-02-11 Thu -> eve 2021-02-10 Wed
      2021-05-14 Fri -> eve 2021-05-13 Thu
      2021-07-22 Thu -> eve 2021-07-21 Wed
      2021-09-30 Thu -> eve 2021-09-29 Wed
      2021-11-03 Wed -> eve 2021-11-02 Tue
      2021-12-31 Fri -> eve 2021-12-30 Thu
      2022-01-03 Mon (and 01-01 Sat / 01-02 Sun, same eve) -> 2021-12-30 Thu
      2022-03-21 Mon + 03-22 Tue -> eve 2022-03-18 Fri (one eve, two holidays)
      2022-05-05 Thu -> eve 2022-05-04 Wed
      2022-08-01 Mon -> eve 2022-07-29 Fri
      2022-11-23 Wed -> eve 2022-11-22 Tue
    2021-01-01 and 2022-12-30/31 are outside the trading-day span, so they
    contribute no eve.
    """
    expected = _d("2021-02-10", "2021-05-13", "2021-07-21", "2021-09-29",
                  "2021-11-02", "2021-12-30", "2022-03-18", "2022-05-04",
                  "2022-07-29", "2022-11-22")
    assert holiday_eves(CAL) == expected


def test_second_friday_hand_listed():
    """The calendar-only 2nd Friday, before any holiday shift."""
    assert second_friday(2021, 1) == date(2021, 1, 8)
    assert second_friday(2021, 5) == date(2021, 5, 14)
    assert second_friday(2022, 4) == date(2022, 4, 8)
    assert second_friday(2022, 7) == date(2022, 7, 8)
    # a month starting ON a Friday: 2021-10-01 is a Friday -> 2nd Friday = 10-08
    assert date(2021, 10, 1).weekday() == 4
    assert second_friday(2021, 10) == date(2021, 10, 8)


def test_sqm_hand_listed_with_holiday_shift():
    """SQm = every month's 2nd Friday, moved back when it is not a trading day.

    Hand-computed: every 2nd Friday of 2021-01..2022-12 is a trading day except
    2021-05-14 (a listed holiday), which shifts back to Thursday 2021-05-13.
    """
    expected = _d(
        "2021-01-08", "2021-02-12", "2021-03-12", "2021-04-09", "2021-05-13",
        "2021-06-11", "2021-07-09", "2021-08-13", "2021-09-10", "2021-10-08",
        "2021-11-12", "2021-12-10",
        "2022-01-14", "2022-02-11", "2022-03-11", "2022-04-08", "2022-05-13",
        "2022-06-10", "2022-07-08", "2022-08-12", "2022-09-09", "2022-10-14",
        "2022-11-11", "2022-12-09",
    )
    assert sq_days(CAL) == expected


def test_sqq_hand_listed():
    """SQq = the same rule restricted to the Mar/Jun/Sep/Dec contract months."""
    expected = _d("2021-03-12", "2021-06-11", "2021-09-10", "2021-12-10",
                  "2022-03-11", "2022-06-10", "2022-09-09", "2022-12-09")
    assert sq_days(CAL, months=(3, 6, 9, 12)) == expected
    assert set(sq_days(CAL, months=(3, 6, 9, 12))) <= set(sq_days(CAL))


def test_tom_hand_listed_2021():
    """TOM = each month's last trading day + its first 3 trading days.

    Hand-computed for 2021 from the calendar above. The interesting months:
      * January: 2021-01-01 is closed, so the first three trading days are
        01-04/05/06 and the month's last is 01-29 (a Friday).
      * September: 09-30 is a listed holiday, so the month's last trading day
        is 09-29.
      * October: 10-01 is a Friday, so the first three trading days straddle a
        weekend: 10-01, 10-04, 10-05.
      * December: 12-31 is a listed holiday -> last trading day 12-30.
    """
    expected_2021 = _d(
        "2021-01-04", "2021-01-05", "2021-01-06", "2021-01-29",
        "2021-02-01", "2021-02-02", "2021-02-03", "2021-02-26",
        "2021-03-01", "2021-03-02", "2021-03-03", "2021-03-31",
        "2021-04-01", "2021-04-02", "2021-04-05", "2021-04-30",
        "2021-05-03", "2021-05-04", "2021-05-05", "2021-05-31",
        "2021-06-01", "2021-06-02", "2021-06-03", "2021-06-30",
        "2021-07-01", "2021-07-02", "2021-07-05", "2021-07-30",
        "2021-08-02", "2021-08-03", "2021-08-04", "2021-08-31",
        "2021-09-01", "2021-09-02", "2021-09-03", "2021-09-29",
        "2021-10-01", "2021-10-04", "2021-10-05", "2021-10-29",
        "2021-11-01", "2021-11-02", "2021-11-04", "2021-11-30",
        "2021-12-01", "2021-12-02", "2021-12-03", "2021-12-30",
    )
    got_2021 = [d for d in tom_days(CAL) if d.year == 2021]
    assert got_2021 == expected_2021


def test_tom_hand_listed_edges_2022():
    """The 2022 edges: a closed 1st business day, and the truncated last month.

    2022-08-01 (Mon) is a listed holiday, so August's first three trading days
    are 08-02/03/04. The series ends 2022-12-29, so December's "last trading
    day" is 12-29 (12-30 is closed and 12-31 is outside the span).
    """
    got = set(tom_days(CAL))
    assert _d("2022-08-02")[0] in got
    assert _d("2022-08-03")[0] in got
    assert _d("2022-08-04")[0] in got
    assert _d("2022-08-01")[0] not in got     # not a trading day at all
    assert _d("2022-08-05")[0] not in got     # the 4th trading day of August
    assert _d("2022-12-29")[0] in got
    # March 2022: 03-21/22 closed, so the month's last trading day is 03-31
    assert _d("2022-03-31")[0] in got
    assert _d("2022-03-01")[0] in got and _d("2022-03-02")[0] in got
    assert _d("2022-03-03")[0] in got and _d("2022-03-04")[0] not in got


def test_tom_count_is_four_per_interior_month():
    """Interior months contribute exactly 4 TOM days (last + first three).

    The set is a union, so a month whose last trading day is also one of its
    own first three would collapse — no month here is that short, so 2 years =
    24 months x 4, minus the 3 first-month days that have no preceding
    month-end... none: January 2021 still contributes its own first three and
    its own last day. Hence exactly 24*4 = 96.
    """
    assert len(tom_days(CAL)) == 96


def test_weekday_sets_partition_the_calendar():
    sets = [weekday_days(CAL, i) for i in range(5)]
    assert sum(len(s) for s in sets) == len(CAL)
    assert set().union(*[set(s) for s in sets]) == set(CAL)
    assert all(d.weekday() == 0 for d in sets[0])
    # 2021-02-11 (Thu) is closed, so that week has no Thursday
    assert date(2021, 2, 11) not in sets[3]


def test_build_rule_day_sets_has_the_nine_rules():
    sets = build_rule_day_sets(CAL)
    assert sorted(sets) == sorted(
        ["TOM", "WD-Mon", "WD-Tue", "WD-Wed", "WD-Thu", "WD-Fri", "PH", "SQm", "SQq"])
    assert sets["PH"] == holiday_eves(CAL)
    assert sets["TOM"] == tom_days(CAL)
    assert sets["SQq"] == sq_days(CAL, months=(3, 6, 9, 12))


def test_major_sq_marked_days_are_the_sq_day_and_its_predecessor():
    marked = major_sq_marked_days(CAL)
    for s in sq_days(CAL, months=(3, 6, 9, 12)):
        assert s in marked
        prev = CAL[CAL.index(s) - 1]
        assert prev in marked
    # exactly 2 days per major SQ (none of them coincide in this calendar)
    assert len(marked) == 2 * len(sq_days(CAL, months=(3, 6, 9, 12)))


# ---------------------------------------------------------------------------
# 2. the placebo fold-back rule (PREREG 対照 2)
# ---------------------------------------------------------------------------

def test_placebo_foldback_weekday_rule_has_no_foldback():
    """Shifting Mondays by +-1/+-2 trading days can only land back on a Monday
    across a holiday gap; this calendar has such gaps, so the count is reported
    rather than assumed zero — but the returned placebo set never intersects
    the original."""
    mondays = weekday_days(CAL, 0)
    for k in (-2, -1, 1, 2):
        placebo, n_fold, n_out = shift_trading_days(mondays, CAL, k)
        assert not (placebo & set(mondays))
        assert n_fold >= 0 and n_out >= 0
        assert len(placebo) + n_fold + n_out == len(mondays)


def test_placebo_foldback_counts_tom_window_returns():
    """TOM is a 4-day contiguous window, so a 1-day shift folds most of it back.

    Shifting the window [last(M), 1st, 2nd, 3rd of M+1] by −1 trading day gives
    [2nd-last(M), last(M), 1st, 2nd], of which three members are still TOM
    days: exactly one NEW day survives per window. With 24 months (23 interior
    windows plus edges) the placebo set is far smaller than the rule set and
    the removed count is reported.
    """
    tom = tom_days(CAL)
    placebo, n_fold, n_out = shift_trading_days(tom, CAL, -1)
    assert not (placebo & set(tom))
    assert n_fold > 0
    assert len(placebo) + n_fold + n_out == len(tom)
    # each 4-day window contributes exactly one new day at k=-1
    assert len(placebo) == 24


def test_placebo_shift_is_in_trading_days_and_offset_by_k():
    """A placebo date really is the k-th trading day away from a rule date."""
    pos = {d: i for i, d in enumerate(CAL)}
    ph = holiday_eves(CAL)
    placebo, _, _ = shift_trading_days(ph, CAL, 2)
    for p in placebo:
        assert p in pos
        assert any(pos.get(r) is not None and pos[r] + 2 == pos[p] for r in ph)


def test_placebo_counts_dates_shifted_off_the_calendar():
    """A shift that would run past either end is counted, not silently kept."""
    first_two = CAL[:2]
    placebo, n_fold, n_out = shift_trading_days(first_two, CAL, -2)
    assert n_out == 2 and not placebo and n_fold == 0


# ---------------------------------------------------------------------------
# 3. helpers used by the run script
# ---------------------------------------------------------------------------

def test_etf_tick_by_price_band():
    bands = {"up_to_1000_yen": 1, "up_to_3000_yen": 1, "up_to_5000_yen": 1,
             "up_to_10000_yen": 1, "up_to_30000_yen": 5, "up_to_50000_yen": 10,
             "over_50000_yen": 10000}
    assert etf_tick_yen(900.0, bands) == 1
    assert etf_tick_yen(10000.0, bands) == 1      # inclusive upper bound
    assert etf_tick_yen(10000.5, bands) == 5
    assert etf_tick_yen(21480.0, bands) == 5
    assert etf_tick_yen(40000.0, bands) == 10
    assert etf_tick_yen(9e7, bands) == 10000


def test_build_close_pairs_endpoint_rule_and_nights():
    df = pd.DataFrame({
        "date": pd.to_datetime(["2021-01-04", "2021-01-05", "2021-01-08",
                                "2021-01-12"]),
        "close": [100.0, 110.0, 121.0, 121.0],
    })
    p = build_close_pairs(df)
    assert len(p) == 3                              # last row has no successor
    assert list(pd.to_datetime(p["date"]).dt.date) == _d(
        "2021-01-05", "2021-01-08", "2021-01-12")
    assert p["r_bps"].iloc[0] == pytest.approx(1000.0)
    assert list(p["nights"]) == [1, 3, 4]


# ---------------------------------------------------------------------------
# 4. planted-effect recovery
# ---------------------------------------------------------------------------

def _planted_days(rule: str = "WD-Wed") -> tuple[list[date], np.ndarray]:
    """The 12-year Mon-Fri calendar and the rule mask over its EXIT days."""
    days = []
    cur = date(2005, 1, 3)
    while cur < date(2017, 1, 1):
        if cur.weekday() < 5:
            days.append(cur)
        cur += timedelta(days=1)
    marked = set(build_rule_day_sets(days)[rule])
    return days, np.array([d in marked for d in days[1:]])


def _planted_returns(seed: int, effect_bps: float, rule: str = "WD-Wed") -> np.ndarray:
    """The exact per-pair return series the tape is built from (the answer)."""
    days, is_rule = _planted_days(rule)
    rng = np.random.default_rng(seed)
    return rng.normal(0.0, 100.0, size=len(days) - 1) + is_rule * effect_bps


def _planted_tape(seed: int, effect_bps: float, rule: str = "WD-Wed"
                  ) -> tuple[pd.DataFrame, np.ndarray]:
    """A 12-year Mon-Fri tape whose `rule` days carry a planted extra return.

    Noise is iid lognormal-ish (a fixed 100bps daily sigma), so the recovered
    mean on the rule's days should be the planted effect up to sampling error,
    and the rule-minus-non-rule difference should be the same effect.
    """
    days, is_rule = _planted_days(rule)
    # returns are attributed to the EXIT day t, i.e. days[1:]
    r = _planted_returns(seed, effect_bps, rule)
    close = [10000.0]
    for x in r:
        close.append(close[-1] * (1.0 + x / 1e4))
    return pd.DataFrame({"date": pd.to_datetime(days), "close": close}), is_rule


def test_planted_effect_is_recovered_on_the_rule_days():
    planted = 30.0
    df, is_rule = _planted_tape(seed=7, effect_bps=planted)
    pairs = build_close_pairs(df)
    assert len(pairs) == len(is_rule)
    gross = pairs["r_bps"].to_numpy(dtype=float)

    # the pair returns reproduce the planted series exactly (the price path is
    # built by compounding them, so this is a round-trip identity check)
    assert gross == pytest.approx(_planted_returns(seed=7, effect_bps=planted))

    # sigma is 100bps, so SE(rule mean) ~= 4.0bps and SE(difference) ~= 4.5bps;
    # the tolerances below are 3 SE.
    mean_rule, lo, hi = mean_ci(gross[is_rule])
    assert mean_rule == pytest.approx(planted, abs=12.0)
    assert lo < planted < hi
    assert lo > 0                                   # the planted edge is found

    d, dlo, dhi = diff_ci(gross[is_rule], gross[~is_rule])
    assert d == pytest.approx(planted, abs=14.0)
    assert dlo < planted < dhi
    assert dlo > 0


def test_no_planted_effect_gives_a_ci_containing_zero():
    """The same machinery must NOT manufacture an edge when none is planted."""
    df, is_rule = _planted_tape(seed=11, effect_bps=0.0)
    gross = build_close_pairs(df)["r_bps"].to_numpy(dtype=float)
    mean_rule, lo, hi = mean_ci(gross[is_rule])
    assert lo < 0 < hi
    d, dlo, dhi = diff_ci(gross[is_rule], gross[~is_rule])
    assert dlo < 0 < dhi


def test_planted_effect_lands_on_the_right_calendar_days():
    """The planted days really are the rule's days, not an off-by-one."""
    df, is_rule = _planted_tape(seed=3, effect_bps=200.0)
    pairs = build_close_pairs(df)
    exit_dates = pd.to_datetime(pairs["date"]).dt.date
    hit = pairs.loc[is_rule, "r_bps"].mean()
    miss = pairs.loc[~is_rule, "r_bps"].mean()
    assert hit - miss == pytest.approx(200.0, abs=15.0)
    assert set(exit_dates[is_rule]) <= set(weekday_days(list(exit_dates), 2))


# ---------------------------------------------------------------------------
# 5. ITERATION 1 — the vol tercile: train-fixed cutpoints, no look-ahead
# ---------------------------------------------------------------------------

def test_tercile_cutpoints_use_only_the_train_rows():
    """Cutpoints must come ONLY from rows where train_mask is True.

    A val-only outlier (100x every train value) must not move q1/q2 at all --
    the defining "no look-ahead" property of a train-fixed cutpoint.
    """
    train_vals = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0])
    mask_train_only = np.array([True] * len(train_vals))
    q1_ref, q2_ref = tercile_cutpoints(train_vals, mask_train_only)

    val_outlier = np.array([900.0, -900.0, 500.0])
    combined = np.concatenate([train_vals, val_outlier])
    combined_mask = np.concatenate([mask_train_only, [False, False, False]])
    q1, q2 = tercile_cutpoints(combined, combined_mask)

    assert q1 == pytest.approx(q1_ref)
    assert q2 == pytest.approx(q2_ref)
    # sanity: the outlier really would have moved the cutpoints had it leaked in
    q1_leaked, q2_leaked = tercile_cutpoints(combined, np.ones(len(combined), dtype=bool))
    assert q1_leaked != pytest.approx(q1) or q2_leaked != pytest.approx(q2)


def test_tercile_cutpoints_ignore_nan_and_need_three_train_obs():
    vals = np.array([1.0, np.nan, 2.0, 3.0])
    mask = np.array([True, True, True, True])
    q1, q2 = tercile_cutpoints(vals, mask)
    assert np.isfinite(q1) and np.isfinite(q2)          # 3 finite train obs is enough

    q1_few, q2_few = tercile_cutpoints(np.array([1.0, np.nan]), np.array([True, True]))
    assert np.isnan(q1_few) and np.isnan(q2_few)         # <3 finite train obs -> undefined


def test_label_tercile_splits_train_into_thirds_and_marks_nan_empty():
    train_vals = np.arange(1.0, 10.0)                    # 1..9, evenly spaced
    q1, q2 = tercile_cutpoints(train_vals, np.ones(len(train_vals), dtype=bool))
    labels = label_tercile(train_vals, q1, q2)
    counts = pd.Series(labels).value_counts()
    assert set(labels) == set(TERCILE_LABELS)
    assert counts[TERCILE_LABELS[0]] == 3
    assert counts[TERCILE_LABELS[1]] == 3
    assert counts[TERCILE_LABELS[2]] == 3
    assert list(label_tercile(np.array([np.nan]), q1, q2)) == [""]
    assert list(label_tercile(np.array([1.0]), float("nan"), float("nan"))) == [""]


def test_label_tercile_applies_fixed_train_cutpoints_to_val_without_recentring():
    """The defining no-look-ahead behaviour: val data shifted well above the
    train range must NOT relabel itself into a fresh set of thirds -- it must
    fall almost entirely into the top train-defined tercile.
    """
    train_vals = np.arange(1.0, 10.0)                    # 1..9
    q1, q2 = tercile_cutpoints(train_vals, np.ones(len(train_vals), dtype=bool))
    val_vals = np.arange(100.0, 109.0)                   # far above every train value
    val_labels = label_tercile(val_vals, q1, q2)
    assert set(val_labels) == {TERCILE_LABELS[2]}         # every val row is "high"
    # a same-split (val-only) tercile would instead spread these across all 3 labels
    q1_val_only, q2_val_only = tercile_cutpoints(val_vals, np.ones(len(val_vals), dtype=bool))
    assert q1_val_only != pytest.approx(q1)
    relabelled = label_tercile(val_vals, q1_val_only, q2_val_only)
    assert set(relabelled) == set(TERCILE_LABELS)


def test_primary_series_vol20_uses_only_returns_realised_before_entry():
    """vol20 attributed to exit day t must be std(returns t-20..t-1) -- NOT
    including t's own return. Perturbing only the return realised ON t must
    leave the value assigned to day t unchanged (and change day t+1's, which
    legitimately depends on it).
    """
    n = 40
    days = pd.date_range("2020-01-01", periods=n, freq="B")
    rng = np.random.default_rng(0)
    r = rng.normal(0.0, 0.01, size=n - 1)
    close_a = np.concatenate([[100.0], 100.0 * np.cumprod(1.0 + r)])
    df_a = pd.DataFrame({"date": days, "close": close_a})
    vol_a = primary_series_vol20(df_a)

    r2 = r.copy()
    r2[25] *= 50.0                                       # blow up ONE day's return
    close_b = np.concatenate([[100.0], 100.0 * np.cumprod(1.0 + r2)])
    df_b = pd.DataFrame({"date": days, "close": close_b})
    vol_b = primary_series_vol20(df_b)

    # r[25] is close(26)'s OWN return (cc[26] = r[25]): the day-26 pair's own
    # exit-day return, which its own vol20 must NOT see.
    day_own_exit = days[26]
    # day 27 is the first exit day whose trailing-20 window (cc[7..26]) reaches
    # back far enough to include cc[26] -- its vol20 legitimately changes.
    day_next_exit = days[27]
    assert vol_a[day_own_exit] == pytest.approx(vol_b[day_own_exit])
    assert vol_a[day_next_exit] != pytest.approx(vol_b[day_next_exit])

    # hand-check the formula directly. cc[k] (close→close return ending day k)
    # equals r[k-1]; the first day with a defined vol20 is day 21 (cc[1..20]
    # is the first full 20-return window, shift(1) moves it onto day 21), and
    # its value is std(cc[1..20]) = std(r[0..19]), ddof=1 (pandas default).
    idx = 21
    expected = pd.Series(r[idx - 21:idx - 1]).std(ddof=1)
    assert vol_a[days[idx]] == pytest.approx(expected)
    assert np.isnan(vol_a[days[idx - 1]])                 # one day earlier: still undefined


# ---------------------------------------------------------------------------
# 5b. ITERATION 2 — the prior-day return sign: no look-ahead
# ---------------------------------------------------------------------------

def test_label_sign_positive_nonpositive_and_nan():
    r = np.array([1.0, 0.0, -1.0, np.nan])
    assert list(label_sign(r)) == [SIGN_LABELS[1], SIGN_LABELS[0], SIGN_LABELS[0], ""]


def test_prior_day_sign_uses_the_return_ending_at_t_minus_1_not_t():
    """Row i's label must be row i−1's OWN return's sign. Perturbing row i's
    OWN return must NOT change row i's label (no look-ahead into the pair's
    own outcome) but MUST change row i+1's label (whose "prior day" is row i).
    """
    r = np.array([10.0, -20.0, 5.0, -5.0, 30.0, -1.0, 2.0])
    labels_a = prior_day_sign(r)
    r2 = r.copy()
    r2[3] = -r2[3] * 1000.0                               # flip + blow up row 3's own return
    labels_b = prior_day_sign(r2)
    assert labels_a[3] == labels_b[3]                     # row 3's own label: unaffected
    assert labels_a[4] != labels_b[4]                     # row 4's label uses row 3's return
    assert labels_a[0] == ""                              # no prior pair for the first row
    # hand check against the definition directly
    expected = label_sign(np.concatenate([[np.nan], r[:-1]]))
    assert list(labels_a) == list(expected)


def test_iteration1_output_is_still_byte_identical_after_adding_iteration2(tmp_path):
    """Adding `run_iteration2` (which reuses iteration 1's dataset builder)
    must not change one byte of iteration 1's own output.
    """
    ref_dir = ITER1_OUT_DIR
    if not ref_dir.exists():
        pytest.skip("no committed iteration-1 reference run in this checkout")
    out = tmp_path / "iter1_rerun"
    assert run_iteration1(out_dir=out) == 0
    compared = []
    for f in sorted(ref_dir.glob("*.csv")):
        assert (out / f.name).read_bytes() == f.read_bytes(), (
            f"iteration 1's {f.name} is no longer byte-identical")
        compared.append(f.name)
    assert len(compared) >= 4


def test_iteration2_produces_54_cumulative_configurations(tmp_path):
    out = tmp_path / "iter2_scratch"
    assert run_iteration2(out_dir=out) == 0
    ind = pd.read_csv(out / "iter2_indicators.csv")
    # 9 rules x (1 unconditional + 2 signs) x 2 splits = 54 rows
    assert len(ind) == len(RULES) * 3 * 2
    summary = pd.read_csv(out / "iter2_val_summary.csv")
    assert len(summary) == len(RULES) * 2                 # 18 conditional val rows
    null_df = pd.read_csv(out / "iter2_joint_permutation_null.csv")
    assert set(null_df["n_configs"]) == {54}
    run = json.loads((out / "RUN.json").read_text(encoding="utf-8"))
    assert run["cumulative_N"] == 54 and run["n_added_this_iteration"] == 18
    assert "any_configuration_meets_it" in run["stopping_rule"]


# ---------------------------------------------------------------------------
# 6. ITERATION 0 byte-identity (adding --iteration 1 must not touch it)
# ---------------------------------------------------------------------------

def test_iteration0_output_is_byte_identical_to_the_committed_reference(tmp_path):
    """The frozen PREREG requires iteration 0's default behaviour to be
    untouched by adding the `--iteration 1` mode. `skip_edge_trend=True` is
    used ONLY for test speed -- it affects `edge_trend_*.csv` and RESULTS.md
    §11 alone (excluded from this comparison), every other file below is
    computed identically either way. The reference directory was generated
    by the ORIGINAL (pre-iteration-1) script.
    """
    ref_dir = OUT_DIR
    if not ref_dir.exists():
        pytest.skip("no committed iteration-0 reference run in this checkout")
    out = tmp_path / "iter0_scratch"
    assert main(out_dir=out, skip_edge_trend=True) == 0
    compared = []
    for f in sorted(ref_dir.glob("*.csv")):
        if f.name.startswith("edge_trend_"):
            continue
        got_path = out / f.name
        assert got_path.exists(), f"iteration 0 no longer writes {f.name}"
        assert got_path.read_bytes() == f.read_bytes(), (
            f"{f.name} is no longer byte-identical to the committed iteration-0 reference")
        compared.append(f.name)
    assert len(compared) >= 20
    assert "main_indicators.csv" in compared and "train_val.csv" in compared


# ---------------------------------------------------------------------------
# 7. ITERATION 1 smoke test (the conditioning ladder step itself)
# ---------------------------------------------------------------------------

def test_iteration1_unconditional_rows_reproduce_iteration0_train_val():
    """RESULTS.md §2 claims iteration 1's independently-rebuilt `pairs`/`p1321`
    give the SAME unconditional train/val numbers as iteration 0's committed
    `train_val.csv` -- this is the test that backs that claim.
    """
    ref_path = OUT_DIR / "train_val.csv"
    if not ref_path.exists():
        pytest.skip("no committed iteration-0 reference run in this checkout")
    ref = pd.read_csv(ref_path).set_index(["rule", "split"])

    from scripts.phase2.p2_04_run import (
        ITER1_UNCOND_LABEL,
        _load_and_build_dataset_iter1,
        _population_for_rule,
        conditional_indicator,
    )
    ds = _load_and_build_dataset_iter1()
    for rule in RULES:
        frame, emask, _series = _population_for_rule(rule, ds["pairs"], ds["p1321"],
                                                      ds["keep_mask"])
        ev = frame.loc[emask].reset_index(drop=True)
        rm = ev[f"is_{rule}"].to_numpy(dtype=bool)
        net = ev["r_net_bps_cons"].to_numpy(dtype=float)
        gross = ev["r_bps"].to_numpy(dtype=float)
        splitcol = ev["split"].to_numpy()
        for split in ("train", "val"):
            sm = splitcol == split
            got = conditional_indicator(net[sm], gross[sm], rm[sm])
            want = ref.loc[(rule, split)]
            assert got["n"] == int(want["n"]), (rule, split)
            if got["n"] > 0:
                assert got["net_mean_cons_bps"] == pytest.approx(
                    want["net_mean_cons_bps"], abs=1e-9), (rule, split)
            if np.isfinite(want["ci_lo"]):
                assert got["net_ci_lo"] == pytest.approx(want["ci_lo"], abs=1e-6)
                assert got["net_ci_hi"] == pytest.approx(want["ci_hi"], abs=1e-6)


def test_iteration1_produces_36_configurations_per_split(tmp_path):
    out = tmp_path / "iter1_scratch"
    assert run_iteration1(out_dir=out) == 0
    ind = pd.read_csv(out / "iter1_indicators.csv")
    # 9 rules x (1 unconditional + 3 terciles) x 2 splits = 72 rows
    assert len(ind) == len(RULES) * 4 * 2
    summary = pd.read_csv(out / "iter1_val_summary.csv")
    assert len(summary) == len(RULES) * 3                # 27 conditional val rows
    null_df = pd.read_csv(out / "iter1_joint_permutation_null.csv")
    assert set(null_df["n_configs"]) == {36}
    run = json.loads((out / "RUN.json").read_text(encoding="utf-8"))
    assert run["cumulative_N"] == 36 and run["n_added_this_iteration"] == 27
    assert "any_configuration_meets_it" in run["stopping_rule"]
