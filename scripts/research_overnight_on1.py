"""ON1 judgment: Nikkei 225 futures overnight effect on tradable session prints.

Implements docs/PREREG_overnight_on1.md verbatim (frozen 2026-08-28 BEFORE any
overnight statistic was computed on the futures data).

Cell (unique, zero parameters): every trading day, long 1 unit at the day-session
closing auction (15:45), exit at the next trading day's day-session opening
auction (8:45).  r_t = ln(day_open(t+1) / day_close(t)).  Window: full
1990-01-04..2026-08-27.

Bars:
  (1) gross mean>0, plain t>=2.0, AND stationary block bootstrap (mean block
      10 days, 10,000 reps, seed 20260828) 95% CI lower bound > 0
  (2) era plateau: mean>0 in >=3 of [1990-1998][1999-2007][2008-2016][2017-2026]
      AND [2017-2026] positive
  (3) net mean>0 with t>=1.5 at conservative cost 1.10 bps/day RT
      (auction execution: fee 0.35 + 1-tick allowance 0.75; base 0.35 reported)

Mandatory diagnostics (report-only): cash ^N225 shrink ratio on the shared date
set, night-session decomposition 2007-26, yearly/weekday tables, B&H comparison
(incl. vol-matched leverage), micro-era subset (2023-05-29..), auction-volume
existence from 1-min bars, determinism (double run hash), zero look-ahead note.

Data: backtest_data/n225f_225labo_20260828/ (snapshot, MD5-pinned).
Cash series for the shrink diagnostic is read from the same repo snapshot if
present, else fetched read-only from Yahoo (diagnostic only, not a bar).

Run once, report as-is.  Seed 20260828.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import math
import random
import statistics
import urllib.request
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SNAP = ROOT / "backtest_data" / "n225f_225labo_20260828"
SEED = 20260828
COST_BASE_BPS = 0.35
COST_CONS_BPS = 1.10
ERAS = [(1990, 1998), (1999, 2007), (2008, 2016), (2017, 2026)]


def load_daily(fn: str) -> list[dict]:
    with gzip.open(SNAP / fn, "rt") as f:
        rows = []
        for r in csv.DictReader(f):
            rows.append(
                {
                    "date": date.fromisoformat(r["date"]),
                    "open": float(r["open"]),
                    "high": float(r["high"]),
                    "low": float(r["low"]),
                    "close": float(r["close"]),
                    "volume": float(r["volume"]) if r["volume"] else None,
                }
            )
    rows.sort(key=lambda r: r["date"])
    return rows


def tstat(xs: list[float]) -> tuple[float, float, float]:
    n = len(xs)
    m = statistics.fmean(xs)
    sd = statistics.stdev(xs)
    return m, sd, m / (sd / math.sqrt(n))


def stationary_bootstrap_ci(xs: list[float], mean_block: float, reps: int, seed: int) -> tuple[float, float]:
    rng = random.Random(seed)
    n = len(xs)
    p = 1.0 / mean_block
    means = []
    for _ in range(reps):
        total = 0.0
        i = rng.randrange(n)
        for _ in range(n):
            total += xs[i]
            if rng.random() < p:
                i = rng.randrange(n)
            else:
                i = (i + 1) % n
        means.append(total / n)
    means.sort()
    return means[int(0.025 * reps)], means[int(0.975 * reps) - 1]


def ann(mean_daily: float) -> float:
    return mean_daily * 245 * 100  # percent per year


def sharpe(xs: list[float]) -> float:
    return statistics.fmean(xs) / statistics.stdev(xs) * math.sqrt(245)


def max_drawdown(xs: list[float]) -> float:
    eq = 0.0
    peak = 0.0
    mdd = 0.0
    for r in xs:
        eq += r
        peak = max(peak, eq)
        mdd = min(mdd, eq - peak)
    return (math.exp(mdd) - 1) * 100  # percent


def build_overnight(day: list[dict]) -> tuple[list[date], list[float]]:
    dates, rets = [], []
    for a, b in zip(day, day[1:]):
        dates.append(a["date"])
        rets.append(math.log(b["open"] / a["close"]))
    return dates, rets


def main() -> None:
    day = load_daily("day_session_daily.csv.gz")
    dates, on = build_overnight(day)
    n = len(on)
    md5s = {p.name: hashlib.md5(p.read_bytes()).hexdigest()[:12] for p in sorted(SNAP.glob("*.csv.gz"))}

    print("=" * 100)
    print("ON1 JUDGMENT -- Nikkei 225 futures overnight (PREREG_overnight_on1.md, frozen 2026-08-28)")
    print("=" * 100)
    print(f"data: {SNAP.name}  md5[:12]: {json.dumps(md5s)}")
    print(f"cell: long day-close(15:45 auction) -> next day-open(8:45 auction), no filters, n={n}")
    print(f"window: {dates[0]} .. {dates[-1]}")

    # ---- Bar 1: gross ----
    m, sd, t = tstat(on)
    lo, hi = stationary_bootstrap_ci(on, 10.0, 10_000, SEED)
    bar1 = m > 0 and t >= 2.0 and lo > 0
    print("\n-- BAR 1  gross mechanism --")
    print(f"  mean {m*1e4:+.3f} bps/day  ann {ann(m):+.2f}%/y  t={t:+.2f}  "
          f"bootstrap95 [{lo*1e4:+.3f}, {hi*1e4:+.3f}] bps/day  -> {'PASS' if bar1 else 'FAIL'}")

    # ---- Bar 2: era plateau ----
    print("\n-- BAR 2  era plateau --")
    pos = 0
    recent_pos = False
    for y0, y1 in ERAS:
        sub = [r for d, r in zip(dates, on) if y0 <= d.year <= y1]
        em, _, et = tstat(sub)
        flag = em > 0
        pos += flag
        if (y0, y1) == (2017, 2026):
            recent_pos = flag
        print(f"  {y0}-{y1}: n={len(sub)}  mean {em*1e4:+.3f} bps/d  ann {ann(em):+.2f}%  t={et:+.2f}  {'pos' if flag else 'NEG'}")
    bar2 = pos >= 3 and recent_pos
    print(f"  positive eras {pos}/4, 2017-2026 {'pos' if recent_pos else 'NEG'}  -> {'PASS' if bar2 else 'FAIL'}")

    # ---- Bar 3: net at conservative cost ----
    print("\n-- BAR 3  net of costs --")
    results = {}
    for label, bps in (("base", COST_BASE_BPS), ("conservative", COST_CONS_BPS)):
        net = [r - bps / 1e4 for r in on]
        nm, _, nt = tstat(net)
        results[label] = (nm, nt)
        print(f"  {label:>12} ({bps:.2f} bps/d RT): mean {nm*1e4:+.3f} bps/d  ann {ann(nm):+.2f}%  t={nt:+.2f}")
    bar3 = results["conservative"][0] > 0 and results["conservative"][1] >= 1.5
    print(f"  -> {'PASS' if bar3 else 'FAIL'}")

    # =================== mandatory diagnostics (report-only) ===================
    print("\n" + "=" * 100)
    print("MANDATORY DIAGNOSTICS (report-only, not used for selection)")
    print("=" * 100)

    # cash shrink ratio
    cash = fetch_cash()
    if cash:
        shared_on_f, shared_on_c = [], []
        cd = sorted(cash)
        nxt = {}
        for a, b in zip(cd, cd[1:]):
            nxt[a] = b
        fmap = {d: r for d, r in zip(dates, on)}
        for d in dates:
            if d in cash and d in nxt and nxt[d] in cash and d in fmap:
                c0 = cash[d]
                c1 = cash[nxt[d]]
                shared_on_f.append(fmap[d])
                shared_on_c.append(math.log(c1[0] / c0[1]))  # cash open(t+1)/close(t)
        fm = statistics.fmean(shared_on_f)
        cm = statistics.fmean(shared_on_c)
        print(f"\ncash ^N225 shrink diagnostic (shared dates n={len(shared_on_f)}):")
        print(f"  futures ON mean {fm*1e4:+.3f} bps/d  cash ON mean {cm*1e4:+.3f} bps/d  "
              f"ratio futures/cash {fm/cm if cm else float('nan'):.2f}")
    else:
        print("\ncash series unavailable -- shrink diagnostic skipped (diagnostic only)")

    # night decomposition 2007-26
    night = load_daily("night_session_daily.csv.gz")
    nmap = {r["date"]: r for r in night}
    dmap = {r["date"]: r for r in day}
    legs = {"gap_1545_1700": [], "night_1700_0600": [], "gap_0600_0845": []}
    for a, b in zip(day, day[1:]):
        nb = nmap.get(b["date"])  # night session dated by the trading day it precedes
        if nb is None:
            continue
        legs["gap_1545_1700"].append(math.log(nb["open"] / a["close"]))
        legs["night_1700_0600"].append(math.log(nb["close"] / nb["open"]))
        legs["gap_0600_0845"].append(math.log(b["open"] / nb["close"]))
    print(f"\nnight decomposition (2007-2026, n={len(legs['night_1700_0600'])}):")
    for k, xs in legs.items():
        lm, _, lt = tstat(xs)
        print(f"  {k:>16}: mean {lm*1e4:+.3f} bps/d  ann {ann(lm):+.2f}%  t={lt:+.2f}")

    # yearly table
    print("\nyearly gross (bps/day, ann %):")
    years = sorted({d.year for d in dates})
    for y in years:
        sub = [r for d, r in zip(dates, on) if d.year == y]
        if len(sub) < 30:
            continue
        ym = statistics.fmean(sub)
        print(f"  {y}: {ym*1e4:+7.3f} bps/d  {ann(ym):+7.2f}%  n={len(sub)}")

    # weekday
    print("\nweekday of ENTRY day (gross bps/day):")
    for wd, name in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri"]):
        sub = [r for d, r in zip(dates, on) if d.weekday() == wd]
        wm, _, wt = tstat(sub)
        print(f"  {name}: mean {wm*1e4:+.3f}  t={wt:+.2f}  n={len(sub)}")

    # B&H comparison (full-day close-to-close on the same instrument)
    full = load_daily("full_day_daily.csv.gz")
    bh = [math.log(b["close"] / a["close"]) for a, b in zip(full, full[1:])]
    on_net = [r - COST_CONS_BPS / 1e4 for r in on]
    print("\nB&H comparison (same futures series, close-to-close, zero-cost B&H reference):")
    for name, xs in (("ON1 net(cons)", on_net), ("B&H", bh)):
        print(f"  {name:>14}: ann {ann(statistics.fmean(xs)):+.2f}%  Sharpe {sharpe(xs):.2f}  maxDD {max_drawdown(xs):.1f}%")
    lev = statistics.stdev(bh) / statistics.stdev(on_net)
    lev_x = [r * lev for r in on_net]
    print(f"  vol-matched ON1 (x{lev:.2f} leverage, costs scaled): ann {ann(statistics.fmean(lev_x)):+.2f}%  "
          f"Sharpe {sharpe(lev_x):.2f}  maxDD {max_drawdown(lev_x):.1f}%")

    # micro-era subset
    micro = [r for d, r in zip(dates, on) if d >= date(2023, 5, 29)]
    mm, _, mt = tstat(micro)
    print(f"\nmicro era (2023-05-29..): n={len(micro)}  mean {mm*1e4:+.3f} bps/d  ann {ann(mm):+.2f}%  t={mt:+.2f}")

    # auction volume existence from 1-min bars
    with gzip.open(SNAP / "bars_1min.csv.gz", "rt") as f:
        vol_0845, vol_1545 = [], []
        for r in csv.DictReader(f):
            if r["time"] == "08:45" and r["volume"]:
                vol_0845.append(float(r["volume"]))
            elif r["time"] == "15:45" and r["volume"]:
                vol_1545.append(float(r["volume"]))
    print(f"\nauction volume (1-min bars, large contract proxy series):")
    print(f"  08:45 bars n={len(vol_0845)} median {statistics.median(vol_0845):.0f}  "
          f"15:45 bars n={len(vol_1545)} median {statistics.median(vol_1545):.0f}")

    # determinism: hash of the return series and verdict inputs, computed twice
    def run_hash() -> str:
        h = hashlib.md5()
        for d, r in zip(dates, on):
            h.update(f"{d}{r:.12e}".encode())
        lo2, hi2 = stationary_bootstrap_ci(on, 10.0, 10_000, SEED)
        h.update(f"{lo2:.12e}{hi2:.12e}".encode())
        return h.hexdigest()[:16]

    h1, h2 = run_hash(), run_hash()
    print(f"\ndeterminism: run A {h1} / run B {h2}  identical={h1 == h2}")
    print("look-ahead: r_t uses close(t) and open(t+1) only; both are auction prints that the")
    print("order itself would join; no feature reads anything after its own decision instant.")

    # ---- verdict ----
    print("\n" + "=" * 100)
    print("VERDICT (PREREG sec.6 -- reading fixed before the run)")
    print("=" * 100)
    print(f"  BAR 1 gross mechanism : {'PASS' if bar1 else 'FAIL'}")
    print(f"  BAR 2 era plateau     : {'PASS' if bar2 else 'FAIL'}")
    print(f"  BAR 3 net of costs    : {'PASS' if bar3 else 'FAIL'}")
    if bar1 and bar2 and bar3:
        print("  >>> ALL BARS PASS -- present to owner: (i) B&H framing agreement, "
              "(ii) forward paper-tracking decision. NOT adoption. <<<")
    elif not (bar1 and bar2):
        print("  >>> REJECT -- the cash-index gap does not exist in tradable session prints "
              "(session-boundary artifact). <<<")
    else:
        print("  >>> COST-BOUND -- mechanism reproduces but does not clear conservative costs. "
              "No downgrade pass. <<<")


def fetch_cash() -> dict[date, tuple[float, float]]:
    """date -> (open, close) for ^N225; diagnostic only."""
    try:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/%5EN225?range=45y&interval=1d"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        d = json.load(urllib.request.urlopen(req, timeout=60))["chart"]["result"][0]
        q = d["indicators"]["quote"][0]
        out = {}
        for t, o, c in zip(d["timestamp"], q["open"], q["close"]):
            if o and c:
                out[datetime.utcfromtimestamp(t).date()] = (o, c)
        return out
    except Exception:
        return {}


if __name__ == "__main__":
    main()
