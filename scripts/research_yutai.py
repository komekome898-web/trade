#!/usr/bin/env python3
"""SURVEY (exploratory, not a judgment -- no PREREG): Japanese 株主優待/配当
権利落ち seasonality, cash-long only (100-share unit, closing-auction orders,
0 commission). 2015-01..2026-09.

Deterministic: reads the frozen snapshot in backtest_data/yutai_20260904/
(universe.csv from JPX listed-issues file x kabuyutai.com screener;
px.tar.gz daily OHLC+dividend from Yahoo chart API fetched 2026-09-04).
Does not hit the network. No strategy recommendation or parameter selection
here -- that is the lead's job per docs/SURVEY_JP_YUTAI.md and
.claude/skills/research-protocol.

Usage:
    PYTHONPATH=src python scripts/research_yutai.py
"""
import csv
import math
import os
import random
import statistics as st
import tarfile
from collections import defaultdict

DATA_DIR = "backtest_data/yutai_20260904"
UNIVERSE_CSV = os.path.join(DATA_DIR, "universe.csv")
PX_TARBALL = os.path.join(DATA_DIR, "px.tar.gz")
PX_DIR = os.path.join(DATA_DIR, "px")
N225_CSV = os.path.join(PX_DIR, "IDX_N225.csv")

ERAS = [("2015-2019", 2015, 2019), ("2020-2026", 2020, 2026)]

random.seed(20260904)


def ensure_extracted():
    if os.path.isdir(PX_DIR) and os.path.exists(N225_CSV):
        return
    if not os.path.exists(PX_TARBALL):
        raise SystemExit(f"missing {PX_TARBALL} and no extracted {PX_DIR}/")
    with tarfile.open(PX_TARBALL) as tf:
        tf.extractall(DATA_DIR)


def era_of(year):
    for name, lo, hi in ERAS:
        if lo <= year <= hi:
            return name
    return None  # outside survey window


def load_series(path):
    rows = {}
    with open(path) as f:
        for r in csv.DictReader(f):
            try:
                rows[r["date"]] = dict(
                    open=float(r["open"]), high=float(r["high"]),
                    low=float(r["low"]), close=float(r["close"]),
                    dividend=(float(r["dividend"]) if r.get("dividend") else None))
            except (TypeError, ValueError):
                continue
    dates = sorted(rows)
    return rows, dates


def bisect_ge(dates, target):
    lo, hi = 0, len(dates)
    while lo < hi:
        mid = (lo + hi) // 2
        if dates[mid] < target:
            lo = mid + 1
        else:
            hi = mid
    return lo


def lret(a, b):
    if a is None or b is None or a <= 0 or b <= 0:
        return None
    return math.log(b / a)


def madj(stock_leg, mkt_leg):
    if stock_leg is None or mkt_leg is None:
        return None
    return stock_leg - mkt_leg


def compute_event(rows, dates, n225_rows, n225_dates, i_d):
    """i_d = index in `dates` of the ex-dividend date D. Returns leg dict or None."""
    if i_d < 10 or i_d + 10 >= len(dates):
        return None
    d = dates[i_d]
    dm1 = dates[i_d - 1]   # D-1 = 権利付き最終日
    dm5 = dates[i_d - 5]
    dm10 = dates[i_d - 10]
    dp5 = dates[i_d + 5]
    dp10 = dates[i_d + 10]
    needed = [dm10, dm5, dm1, d, dp5, dp10]
    if any(x not in n225_rows for x in needed) or any(x not in rows for x in needed):
        return None
    s, m = rows, n225_rows
    div = s[d]["dividend"] or 0.0
    close_dm1 = s[dm1]["close"]

    legs = {}
    legs["runup10"] = madj(lret(s[dm10]["close"], s[dm1]["close"]),
                            lret(m[dm10]["close"], m[dm1]["close"]))
    legs["runup5"] = madj(lret(s[dm5]["close"], s[dm1]["close"]),
                           lret(m[dm5]["close"], m[dm1]["close"]))
    legs["finalday_auction"] = madj(lret(s[dm1]["open"], s[dm1]["close"]),
                                     lret(m[dm1]["open"], m[dm1]["close"]))
    raw_drop = lret(close_dm1, s[d]["open"])
    legs["exdrop_raw"] = madj(raw_drop, lret(m[dm1]["close"], m[d]["open"]))
    div_frac = (div / close_dm1) if close_dm1 > 0 else 0.0
    exdrop_adj = (raw_drop + div_frac) if raw_drop is not None else None
    legs["exdrop_divadj"] = madj(exdrop_adj, lret(m[dm1]["close"], m[d]["open"]))
    legs["post_open_close"] = madj(lret(s[d]["open"], s[d]["close"]),
                                    lret(m[d]["open"], m[d]["close"]))
    legs["post5"] = madj(lret(s[d]["close"], s[dp5]["close"]),
                          lret(m[d]["close"], m[dp5]["close"]))
    legs["post10"] = madj(lret(s[d]["close"], s[dp10]["close"]),
                           lret(m[d]["close"], m[dp10]["close"]))
    legs["unit_cost_jpy"] = close_dm1 * 100
    legs["ex_date"] = d
    legs["month"] = int(d[5:7])
    legs["year"] = int(d[:4])
    return legs


def load_universe():
    rows = list(csv.DictReader(open(UNIVERSE_CSV)))
    return rows


def load_all_series(codes):
    out = {}
    for c in codes:
        p = os.path.join(PX_DIR, f"{c}.csv")
        if os.path.exists(p):
            out[c] = load_series(p)
    return out


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


def fmt_row(label, s, w=28):
    return (f"{label:<{w}} n={s['n']:>5}  mean={s['mean_bps']:>8.2f}bps  "
            f"t={s['t']:>6.2f}  win%={s['win']:>5.1f}")


LEG_NAMES = [
    ("runup10", "run-up close(D-10)->close(D-1)"),
    ("runup5", "run-up close(D-5)->close(D-1)"),
    ("finalday_auction", "final-day auction open->close(D-1)"),
    ("exdrop_raw", "ex-drop raw close(D-1)->open(D)"),
    ("exdrop_divadj", "ex-drop div-adjusted (excess drop)"),
    ("post_open_close", "post open(D)->close(D)"),
    ("post5", "post close(D)->close(D+5)"),
    ("post10", "post close(D)->close(D+10)"),
]


def print_table(events, header):
    print(f"\n--- {header} (n_events={len(events)}) ---")
    for key, label in LEG_NAMES:
        vals = [e[key] for e in events if e.get(key) is not None]
        print("  " + fmt_row(label, summarize(vals)))


def main():
    ensure_extracted()
    n225_rows, n225_dates = load_series(N225_CSV)
    universe = load_universe()
    codes = [r["code"] for r in universe]
    series = load_all_series(codes)
    print(f"universe rows: {len(universe)}  price series loaded: {len(series)}  "
          f"N225 bars: {len(n225_dates)}")

    perk_events = []
    nonperk_events = []
    n_missing_series = 0
    n_no_divs = 0
    n_insufficient_window = 0

    for r in universe:
        code = r["code"]
        is_perk = r["perk_flag"] == "1"
        if code not in series:
            n_missing_series += 1
            continue
        rows, dates = series[code]
        if not dates:
            n_missing_series += 1
            continue
        div_dates = [d for d in dates if rows[d]["dividend"]]
        if not div_dates:
            n_no_divs += 1
            continue
        for d in div_dates:
            i_d = dates.index(d)  # dates list is short per ticker (~2800); fine
            legs = compute_event(rows, dates, n225_rows, n225_dates, i_d)
            if legs is None:
                n_insufficient_window += 1
                continue
            era = era_of(legs["year"])
            if era is None:
                continue
            rec = dict(code=code, name=r["name"], market=r["market"],
                       kenri_month=r.get("kenri_month", ""), era=era, **legs)
            (perk_events if is_perk else nonperk_events).append(rec)

    print(f"missing price series: {n_missing_series}  no dividend events in series: "
          f"{n_no_divs}  insufficient calendar window: {n_insufficient_window}")
    print(f"usable events -- perk: {len(perk_events)}  non-perk: {len(nonperk_events)}")

    # ---- perk vs non-perk, pooled ----
    print("\n" + "=" * 100)
    print("SECTION 1: perk vs non-perk, all eras pooled")
    print("=" * 100)
    print_table(perk_events, "PERK stocks")
    print_table(nonperk_events, "NON-PERK (dividend-paying control universe) stocks")

    # ---- by era ----
    print("\n" + "=" * 100)
    print("SECTION 2: perk vs non-perk, by era")
    print("=" * 100)
    for era_name, _, _ in ERAS:
        print_table([e for e in perk_events if e["era"] == era_name], f"PERK -- {era_name}")
        print_table([e for e in nonperk_events if e["era"] == era_name], f"NON-PERK -- {era_name}")

    # ---- by 権利月 group: Mar/Sep (fiscal-year-end-heavy) vs other ----
    print("\n" + "=" * 100)
    print("SECTION 3: perk stocks, by ex-dividend calendar month group")
    print("=" * 100)
    mar_sep = [e for e in perk_events if e["month"] in (3, 9)]
    other = [e for e in perk_events if e["month"] not in (3, 9)]
    print_table(mar_sep, "PERK -- ex-div month in {3,9}")
    print_table(other, "PERK -- ex-div month other")
    np_mar_sep = [e for e in nonperk_events if e["month"] in (3, 9)]
    np_other = [e for e in nonperk_events if e["month"] not in (3, 9)]
    print_table(np_mar_sep, "NON-PERK -- ex-div month in {3,9}")
    print_table(np_other, "NON-PERK -- ex-div month other")

    # ---- random-date control on same stocks ----
    print("\n" + "=" * 100)
    print("SECTION 4: matched random-date control (same tickers, non-event days,"
          " same legs, market-adjusted)")
    print("=" * 100)
    for label, events, all_codes in (("perk", perk_events, [r["code"] for r in universe if r["perk_flag"] == "1"]),
                                      ("non-perk", nonperk_events, [r["code"] for r in universe if r["perk_flag"] != "1"])):
        event_days_by_code = defaultdict(set)
        for e in events:
            event_days_by_code[e["code"]].add(e["ex_date"])
        control_events = []
        used_codes = sorted({e["code"] for e in events})
        for code in used_codes:
            if code not in series:
                continue
            rows, dates = series[code]
            ev_idx = sorted(bisect_ge(dates, d) for d in event_days_by_code[code])
            excluded = set()
            for i in ev_idx:
                for j in range(max(0, i - 15), min(len(dates), i + 16)):
                    excluded.add(j)
            candidates = [i for i in range(10, len(dates) - 10) if i not in excluded]
            if len(candidates) < 4:
                continue
            picks = random.sample(candidates, min(4, len(candidates)))
            for i in picks:
                legs = compute_event(rows, dates, n225_rows, n225_dates, i)
                if legs is not None:
                    control_events.append(legs)
        print_table(control_events, f"RANDOM CONTROL -- {label} stocks")

    # ---- unit cost distribution, perk stocks ----
    print("\n" + "=" * 100)
    print("SECTION 5: cash-long unit cost (100 shares x close(D-1)), perk stocks, JPY")
    print("=" * 100)
    costs = sorted(e["unit_cost_jpy"] for e in perk_events)
    if costs:
        def pct(p):
            k = (len(costs) - 1) * p
            f, c = math.floor(k), math.ceil(k)
            if f == c:
                return costs[int(k)]
            return costs[f] + (costs[c] - costs[f]) * (k - f)
        print(f"  n={len(costs)}  min={costs[0]:,.0f}  p10={pct(.10):,.0f}  "
              f"p25={pct(.25):,.0f}  median={pct(.5):,.0f}  p75={pct(.75):,.0f}  "
              f"p90={pct(.90):,.0f}  max={costs[-1]:,.0f}  mean={st.mean(costs):,.0f}")
        n_over_1m = sum(1 for c in costs if c > 1_000_000)
        print(f"  events with unit cost > ¥1,000,000 (100 shares): {n_over_1m} "
              f"({100*n_over_1m/len(costs):.1f}%)")

    print("\nDone.")


if __name__ == "__main__":
    main()
