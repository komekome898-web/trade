#!/usr/bin/env python3
"""SURVEY (exploratory, not a judgment -- no PREREG): Nikkei 225 constituent-change
closing-auction effect, 2000-01..2026-09.

Deterministic: reads the frozen snapshot in backtest_data/nk225_events_20260904/
(events.csv built from the official Nikkei history PDF; px/*.csv daily OHLC from
Yahoo chart API fetched 2026-09-04). Does not hit the network. No strategy
recommendation or parameter selection here -- that is the lead's job per
docs/RESEARCH_REPORT_2026-09-04ao.md and .claude/skills/research-protocol.

Usage:
    PYTHONPATH=src python scripts/research_nk225_events.py
"""
import csv
import math
import os
import random
import statistics as st
from collections import defaultdict

DATA_DIR = "backtest_data/nk225_events_20260904"
EVENTS_CSV = os.path.join(DATA_DIR, "events.csv")
PX_DIR = os.path.join(DATA_DIR, "px")
N225_CSV = os.path.join(PX_DIR, "IDX_N225.csv")

ERAS = [("2000-2008", 2000, 2008), ("2009-2016", 2009, 2016), ("2017-2026", 2017, 2026)]

random.seed(20260904)  # deterministic control sample


def era_of(year: int) -> str:
    for name, lo, hi in ERAS:
        if lo <= year <= hi:
            return name
    return "other"


def load_series(path):
    """date -> dict(open,high,low,close) as floats, sorted date list."""
    rows = {}
    with open(path) as f:
        for r in csv.DictReader(f):
            try:
                rows[r["date"]] = dict(
                    open=float(r["open"]), high=float(r["high"]),
                    low=float(r["low"]), close=float(r["close"]))
            except (TypeError, ValueError):
                continue  # missing bar (e.g. halt) -- Yahoo emits nulls
    dates = sorted(rows)
    return rows, dates


def load_all_series():
    tickers = set()
    with open(EVENTS_CSV) as f:
        for r in csv.DictReader(f):
            tickers.add(r["ticker"])
    series = {}
    for t in tickers:
        p = os.path.join(PX_DIR, f"{t}.csv")
        if os.path.exists(p):
            series[t] = load_series(p)
    return series


def trading_day_index(dates, target):
    """Index in `dates` of the first date >= target (bisect), or len(dates) if none."""
    lo, hi = 0, len(dates)
    while lo < hi:
        mid = (lo + hi) // 2
        if dates[mid] < target:
            lo = mid + 1
        else:
            hi = mid
    return lo


def get_calendar_points(dates, effective_date, announce_lag_td=20, fwd5=5):
    """Given a ticker's own trading-date list and the official effective_date,
    return the calendar dict of dates needed, or None if out of range.

    rebalance_day = last trading day strictly before effective_date (JP passive
    funds trade the CLOSING AUCTION of the day before implementation -- see
    docs/KNOWLEDGE_JP.md and RESEARCH_REPORT_2026-09-04ao.md).
    next_day       = first trading day >= effective_date (normally == effective_date).
    prev_day       = trading day before rebalance_day (for the close-close pressure leg).
    plus5_day      = 5 trading days after rebalance_day.
    announce_day   = ESTIMATED: rebalance_day minus `announce_lag_td` trading days.
                     NOT an observed announcement date -- see caveats in the report.
    """
    i_next = trading_day_index(dates, effective_date)
    if i_next == 0 or i_next >= len(dates):
        return None
    i_reb = i_next - 1
    i_prev = i_reb - 1
    i_plus5 = i_reb + fwd5
    i_ann = i_reb - announce_lag_td
    if i_prev < 0 or i_ann < 0 or i_plus5 >= len(dates):
        return None
    # next_day should equal effective_date itself in the vast majority of cases;
    # if the exchange skipped it (rare data gap) we still use the next available bar.
    return dict(
        announce_day=dates[i_ann], prev_day=dates[i_prev], rebalance_day=dates[i_reb],
        next_day=dates[i_next], plus5_day=dates[i_plus5])


def lret(a, b):
    """log return b/a"""
    if a is None or b is None or a <= 0 or b <= 0:
        return None
    return math.log(b / a)


def compute_event_legs(stock_rows, stock_dates, n225_rows, n225_dates, effective_date):
    pts = get_calendar_points(stock_dates, effective_date)
    if pts is None:
        return None
    # need matching N225 bars on the same calendar dates
    needed = [pts["announce_day"], pts["prev_day"], pts["rebalance_day"], pts["next_day"], pts["plus5_day"]]
    if any(d not in n225_rows for d in needed):
        return None
    if any(d not in stock_rows for d in needed):
        return None

    s = stock_rows
    m = n225_rows

    def madj(stock_leg, mkt_leg):
        if stock_leg is None or mkt_leg is None:
            return None
        return stock_leg - mkt_leg

    legs = {}
    # run-up: announce close -> rebalance close (ESTIMATED announce date)
    legs["runup"] = madj(
        lret(s[pts["announce_day"]]["close"], s[pts["rebalance_day"]]["close"]),
        lret(m[pts["announce_day"]]["close"], m[pts["rebalance_day"]]["close"]))
    # auction pressure vs today's open
    legs["press_vs_open"] = madj(
        lret(s[pts["rebalance_day"]]["open"], s[pts["rebalance_day"]]["close"]),
        lret(m[pts["rebalance_day"]]["open"], m[pts["rebalance_day"]]["close"]))
    # auction pressure vs prior close
    legs["press_vs_prevclose"] = madj(
        lret(s[pts["prev_day"]]["close"], s[pts["rebalance_day"]]["close"]),
        lret(m[pts["prev_day"]]["close"], m[pts["rebalance_day"]]["close"]))
    # next-day reversal: the tradeable cell -- open(next)/close(rebalance)
    legs["reversal_nextopen"] = madj(
        lret(s[pts["rebalance_day"]]["close"], s[pts["next_day"]]["open"]),
        lret(m[pts["rebalance_day"]]["close"], m[pts["next_day"]]["open"]))
    # next-day full
    legs["nextday_full"] = madj(
        lret(s[pts["rebalance_day"]]["close"], s[pts["next_day"]]["close"]),
        lret(m[pts["rebalance_day"]]["close"], m[pts["next_day"]]["close"]))
    # 5-day
    legs["plus5"] = madj(
        lret(s[pts["rebalance_day"]]["close"], s[pts["plus5_day"]]["close"]),
        lret(m[pts["rebalance_day"]]["close"], m[pts["plus5_day"]]["close"]))
    legs["rebalance_close_price"] = s[pts["rebalance_day"]]["close"]
    return legs


def tstat(vals):
    n = len(vals)
    if n < 2:
        return None
    mean = st.mean(vals)
    sd = st.stdev(vals)
    if sd == 0:
        return None
    return mean / (sd / math.sqrt(n))


def summarize(vals):
    n = len(vals)
    if n == 0:
        return dict(n=0, mean_bps=float("nan"), t=float("nan"), win=float("nan"))
    mean_bps = st.mean(vals) * 1e4
    t = tstat(vals)
    win = 100.0 * sum(1 for v in vals if v > 0) / n
    return dict(n=n, mean_bps=mean_bps, t=(t if t is not None else float("nan")), win=win)


def fmt_row(label, s):
    return f"{label:<12} n={s['n']:>4}  mean={s['mean_bps']:>7.2f}bps  t={s['t']:>6.2f}  win%={s['win']:>5.1f}"


def main():
    n225_rows, n225_dates = load_series(N225_CSV)
    series = load_all_series()

    events = list(csv.DictReader(open(EVENTS_CSV)))
    n_events = len(events)

    per_event = []  # list of dict: action, era, legs
    n_missing_series = 0
    n_missing_calendar = 0
    n_reuse_flagged = 0
    used_tickers = set()

    for e in events:
        tkr = e["ticker"]
        eff = e["effective_date"]
        action = e["action"]
        year = int(eff[:4])
        era = era_of(year)
        if tkr not in series:
            n_missing_series += 1
            continue
        rows, dates = series[tkr]
        if not dates:
            n_missing_series += 1
            continue
        # code-reuse guard: if the ticker's own price history does not bracket
        # the event date with enough runway either side, or the earliest
        # available bar is AFTER the event (later company recycled the code),
        # skip -- get_calendar_points already requires 20 trading days before
        # and 5 after within the series, so this also drops thin/short series.
        if dates[0] > eff:
            n_reuse_flagged += 1
            continue
        legs = compute_event_legs(rows, dates, n225_rows, n225_dates, eff)
        if legs is None:
            n_missing_calendar += 1
            continue
        used_tickers.add(tkr)
        per_event.append(dict(action=action, era=era, year=year, ticker=tkr,
                               name=e["name"], effective_date=eff, **legs))

    print("=" * 100)
    print(f"NK225 constituent-change event study -- {n_events} events "
          f"({n_events // 2} swaps), {len(per_event)} usable after data filters")
    print(f"  missing price series (no Yahoo data / delisted): {n_missing_series}")
    print(f"  series present but insufficient calendar runway: {n_missing_calendar}")
    print(f"  dropped as likely ticker-code reuse (series starts after event):"
          f" {n_reuse_flagged}")
    print("=" * 100)

    leg_names = [
        ("runup", "run-up"),
        ("press_vs_open", "close-vs-open (rebal day)"),
        ("press_vs_prevclose", "close-vs-prevclose (rebal day)"),
        ("reversal_nextopen", "next-open reversal (tradeable)"),
        ("nextday_full", "next-day full"),
        ("plus5", "+5 day"),
    ]

    print("\n--- BY ACTION x ERA (market-adjusted log returns, deletions & additions"
          " reported with raw sign; deletions positive == price recovering after"
          " being sold at the close; additions negative == price giving back"
          " after being bought at the close) ---\n")
    for action in ("add", "delete"):
        for era_name, _, _ in ERAS:
            sub = [e for e in per_event if e["action"] == action and e["era"] == era_name]
            print(f"[{action:6s} {era_name}] n_events={len(sub)}")
            for key, label in leg_names:
                vals = [e[key] for e in sub if e[key] is not None]
                print("  " + fmt_row(label, summarize(vals)))
            print()

    print("\n--- BY ACTION, ALL ERAS POOLED ---\n")
    for action in ("add", "delete"):
        sub = [e for e in per_event if e["action"] == action]
        print(f"[{action:6s} pooled] n_events={len(sub)}")
        for key, label in leg_names:
            vals = [e[key] for e in sub if e[key] is not None]
            print("  " + fmt_row(label, summarize(vals)))
        print()

    # ---------------- matched random control ----------------
    # Same tickers as the event set, random non-event trading days (excluded
    # window +/-10 trading days around ANY real event for that ticker), same
    # "next-open reversal" cell, market-adjusted. Sanity check only.
    print("\n--- MATCHED RANDOM CONTROL (same tickers, random non-event days,"
          " next-open-reversal cell only) ---\n")
    event_days_by_ticker = defaultdict(set)
    for e in events:
        if e["ticker"] in series:
            event_days_by_ticker[e["ticker"]].add(e["effective_date"])

    control_vals = []
    SAMPLES_PER_TICKER = 8
    for tkr in sorted(used_tickers):
        rows, dates = series[tkr]
        ev_idx = sorted(trading_day_index(dates, d) for d in event_days_by_ticker[tkr])
        excluded = set()
        for i in ev_idx:
            for j in range(max(0, i - 10), min(len(dates), i + 11)):
                excluded.add(j)
        candidates = [i for i in range(20, len(dates) - 6) if i not in excluded]
        if len(candidates) < SAMPLES_PER_TICKER:
            continue
        picks = random.sample(candidates, SAMPLES_PER_TICKER)
        for i in picks:
            reb_day, next_day = dates[i], dates[i + 1]
            if reb_day not in n225_rows or next_day not in n225_rows:
                continue
            v = lret(rows[reb_day]["close"], rows[next_day]["open"]) - \
                lret(n225_rows[reb_day]["close"], n225_rows[next_day]["open"])
            if v is not None:
                control_vals.append(v)
    print("  " + fmt_row("control", summarize(control_vals)))

    # ---------------- unit cost (capital feasibility, deletions) ----------------
    print("\n--- UNIT COST, DELETIONS (100 shares x close(rebalance day), JPY) ---\n")
    del_costs = sorted(e["rebalance_close_price"] * 100 for e in per_event
                        if e["action"] == "delete")
    if del_costs:
        def pct(p):
            k = (len(del_costs) - 1) * p
            f = math.floor(k)
            c = math.ceil(k)
            if f == c:
                return del_costs[int(k)]
            return del_costs[f] + (del_costs[c] - del_costs[f]) * (k - f)
        print(f"  n={len(del_costs)}  min={del_costs[0]:,.0f}  "
              f"p25={pct(.25):,.0f}  median={pct(.5):,.0f}  "
              f"p75={pct(.75):,.0f}  max={del_costs[-1]:,.0f}  "
              f"mean={st.mean(del_costs):,.0f}")

    print("\nDone.")


if __name__ == "__main__":
    main()
