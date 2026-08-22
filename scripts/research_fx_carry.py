#!/usr/bin/env python3
"""FX Study S5 -- carry as engineered income.  20+ years, honest risk accounting.

===============================================================================
PRE-REGISTRATION (fixed before any result was read; research-protocol sec.1)
===============================================================================

QUESTION
--------
Carry is beta, not alpha.  The owner's mandate is "stable income".  The question
is NOT whether USD/JPY carry has a positive expectation (it does, mechanically,
whenever the US-JP short-rate differential is positive and the broker's haircut
is smaller than it).  The question is whether the carry income stream can be
SHAPED -- by a trend gate or a vol target -- into something whose TAILS are
acceptable, measured across multiple rate regimes rather than one.

DATA (all fetched and snapshotted; reruns are offline-reproducible)
------------------------------------------------------------------
  backtest_data/fred_DEXJPUS.csv           USD/JPY noon NY buying rate, 1971-01-04 ->
  backtest_data/fred_DFF.csv               US effective fed funds, DAILY, 1954-07-01 ->
  backtest_data/fred_IRSTCI01JPM156N.csv   Japan immediate (<24h) call money /
                                           interbank rate, MONTHLY, 1985-07 ->
  backtest_data/fred_IR3TIB01JPM156N.csv   Japan 3M interbank (TIBOR), MONTHLY,
                                           2002-04 ->   [robustness arm only]
  backtest_data/fred_DGS2.csv              US 2y CMT, DAILY, 1976-06-01 ->
                                           [forward-looking differential arm only]
  backtest_data/gmo_swap_usdjpy.csv        GMO Coin ACTUAL published USD/JPY swap
                                           calendar (swapBuy / swapSell JPY per
                                           10,000 USD, swapDays), 2023-04 ->
  data/fx/USDJPY_1m.csv                    Dukascopy 1m bid, 2023-01-01 -> (validation)

JP SHORT-RATE SERIES CHOICE (documented, per instruction)
---------------------------------------------------------
The swap differential a retail broker passes through is an OVERNIGHT funding
differential.  The correct JP leg is therefore the overnight call rate, not a
term rate.  IRSTCI01JPM156N ("Immediate Rates (< 24 Hours): Call Money /
Interbank Rate: Total for Japan", monthly) is the only FRED series that is
(a) overnight, (b) interbank, (c) covering 1985-07 .. 2026-06.  It is matched
against DFF (US effective fed funds, overnight interbank) -- apples to apples.
IRSTCB01JPM156N (central bank policy rate) was rejected: it ENDS 2023-12 and so
misses the entire BOJ normalisation.  INTGSBJPM193N (T-bill) ends 2017-05.
IR3TIB01JPM156N (3M) is carried as a ROBUSTNESS arm only.
The monthly JP value is an average over its month and is only knowable after the
month ends, so it is LAGGED ONE MONTH before use (month M uses month M-1's
value).  This removes look-ahead at a negligible accuracy cost -- the BOJ call
rate is a policy-pinned step function.

SAMPLE / SPLIT (fixed before running)
-------------------------------------
Common support of price + both rate legs starts 1985-07-01 and the price series
ends at the last DEXJPUS observation.  The FULL depth is used (41 years, five
distinct rate regimes), not a 2005 truncation.  Chronological 60/40 by TRADING
ROW COUNT:
    EXPLORE = rows [0, 0.60*N)      JUDGE = rows [0.60*N, N)
The exact boundary date is printed by the script and reproduced in the report.
JUDGE is executed ONCE and reported as-is.

POSITION SIGN -- both variants enumerated, neither added later
--------------------------------------------------------------
  sign rule "follow"  : w = +1 if diff > 0, -1 if diff < 0, 0 if diff == 0.
                        (When JP pays more than the US, the receiving side of
                        the carry is SHORT USD/JPY.  The 1985-1995 sample
                        contains exactly this regime.)
  sign rule "longpos" : w = +1 if diff > 0, else 0 (long-only-when-positive).

FAMILIES -- exactly these three, no additions after the fact
------------------------------------------------------------
  C1  unconditional carry : hold the differential-sign position ALWAYS.
  C2  trend-gated         : C1, but FLAT whenever the position is on the losing
                            side of its 200-day SMA -- i.e. long is gated off
                            when P < SMA200, short is gated off when P > SMA200.
                            ONE parameter (200).  NOT swept.  Classic
                            carry-crash filter.
  C3  vol-targeted        : C1 scaled to a 10% annualised vol target using
                            63-day realised vol of COMPLETED daily returns,
                            scale = min(1.0, 0.10 / vol_ann).  Cap 1x.
                            No leverage: the cap binds, it never scales above 1.

  All features (SMA200, 63d vol) are computed on days STRICTLY BEFORE the day
  whose return is being earned.  Look-ahead is zero by construction.

REGISTERED DEVIATION FROM A HOUSE INVARIANT (declared, not discovered)
----------------------------------------------------------------------
KNOWLEDGE_FX.md sec.6 makes WEEKEND-FLAT a default invariant of this repo (median
weekend gap 4.4bps = 6x round-trip cost).  That invariant is in DIRECT CONFLICT
with a carry strategy: swap accrues over the weekend (it is booked on the
Wednesday 3-day roll) and a weekend-flat carry book forfeits ~2/7 of the income
while still paying 2 extra round trips a week.  For this strategy class the
weekend-flat invariant is EXPLICITLY WAIVED.  The weekend gap risk is not
avoided, it is PRICED: the Fri->Mon price move is carried in full in the return
series, and it is the dominant contributor to the tail statistics reported
below.  This waiver applies to the carry family ONLY and does not alter the
invariant for intraday/event strategies.

COSTS
-----
  entry/exit   : 0.71 bps round trip [KNOWLEDGE_FX.md sec.1, measured] charged as
                 0.355 bps x |change in position weight| on every day the weight
                 changes.  C1 pays it ~never; C2/C3 pay it on every gate flip /
                 rescale.
  overnight    : the modelled swap (below), charged/credited on the actual
                 calendar-day count spanned by each price step, so a Fri->Mon
                 step accrues 3 days.  Over any full week this sums to 7 days,
                 which is exactly what the Wednesday 3-day roll delivers.
  leverage     : NONE.  1x notional throughout.  25x (GMO's max) is NOT modelled
                 and is a separate owner decision.

SWAP MODEL -- calibrated against GMO's ACTUAL published calendar
-----------------------------------------------------------------
GMO's swap calendar was located behind the JS page at
    https://coin.z.com/api/v1/fx/master/getAllSwapListByDate?date=YYYYMMDD
(productId 100001 = USD_JPY; fields swapBuy / swapSell in JPY per 10,000 USD,
plus swapDays).  It covers 2023-04 -> present.  Converting to bps/day of JPY
notional and regressing against the interbank differential over that window
yields two constants:
    MID_RATIO   = median( gmo_mid_bps_day / interbank_bps_day )
    HALF_SPREAD = median( (|swapSell| - swapBuy)/2 in bps/day )
The primary model is then
    long  : carry_bps/day = MID_RATIO * interbank_bps_day - HALF_SPREAD
    short : carry_bps/day = -MID_RATIO * interbank_bps_day - HALF_SPREAD
i.e. the broker's bid/ask swap spread is a COST IN BOTH DIRECTIONS.
SENSITIVITY (reported alongside, never used for selection): the instructed
conservative fallback of a flat 25% multiplicative haircut,
    long  : 0.75 * interbank_bps_day when positive, 1.25 * it when negative
    short : the mirror.

SELECTION RULE (one config, fixed in advance)
----------------------------------------------
Among the 6 configs (3 families x 2 sign rules) pick the single highest EXPLORE
Sharpe.  That one config is carried to JUDGE.  All 6 JUDGE numbers are printed
for transparency, but if the JUDGE winner differs from the EXPLORE winner that
is recorded as CONFIG SWITCHING = an overfitting signal (research-protocol
sec.2), not as a reason to adopt the other one.

ADOPTION BARS (beta-type, registered before running; ALL must hold on JUDGE)
----------------------------------------------------------------------------
    Sharpe (ann, daily)        >= 0.70
    max drawdown               <= 12.0%
    positive calendar months   >= 60.0%
    total return after costs   >  0
These are BETA bars, deliberately different from the alpha bars in
research-protocol sec.4 (>=100 trades, >=+2bps/trade, t>=2.0): a carry book has
~no trades and its edge is an income stream, not a per-trade expectancy.  This
is declared here so it cannot be mistaken for a relaxed alpha standard.

MANDATORY REPORTING (regardless of pass/fail)
----------------------------------------------
  * PRICE P&L vs SWAP P&L decomposed separately, PER YEAR, for the whole sample.
    The owner must be able to see that the carry income is real AND that the
    price path dominates it.
  * Named stress windows with drawdown and recovery:
      2007-2008 carry crash        2007-07-01 .. 2009-03-31
      2022 MOF intervention        2022-09-01 .. 2022-12-31
      2024 MOF intervention        2024-04-01 .. 2024-05-31
      2024-08 yen-carry unwind     2024-07-01 .. 2024-09-30
  * Validation of DEXJPUS against data/fx/USDJPY_1m.csv daily closes (+-0.5%).
  * Swap day-count shown on a known Wednesday.
  * Determinism: the whole pipeline is run twice and the result hash compared.

Usage:  PYTHONPATH=src python scripts/research_fx_carry.py [--fetch]
        --fetch  re-downloads the snapshots (default: use snapshots if present)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.request
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SNAP = ROOT / "backtest_data"
FRED_IDS = ["DEXJPUS", "DFF", "IRSTCI01JPM156N", "IR3TIB01JPM156N", "DGS2"]
FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={}"
GMO_URL = "https://coin.z.com/api/v1/fx/master/getAllSwapListByDate?date={}"
GMO_PID = 100001
GMO_SWAP_CSV = SNAP / "gmo_swap_usdjpy.csv"
GMO_START = date(2023, 4, 1)

RT_COST_BPS = 0.71          # KNOWLEDGE_FX.md sec.1, measured
ONE_WAY_BPS = RT_COST_BPS / 2.0
SMA_WIN = 200
VOL_WIN = 63
VOL_TARGET = 0.10
SPLIT_FRAC = 0.60
TRADING_DAYS = 252.0

BAR_SHARPE = 0.70
BAR_MAXDD = 0.12
BAR_POSMON = 0.60

STRESS = [
    ("2007-08 carry crash", "2007-07-01", "2009-03-31"),
    ("2022 MOF intervention", "2022-09-01", "2022-12-31"),
    ("2024 MOF intervention", "2024-04-01", "2024-05-31"),
    ("2024-08 carry unwind", "2024-07-01", "2024-09-30"),
]

FAMILIES = ["C1", "C2", "C3"]
SIGN_RULES = ["follow", "longpos"]


def log(*a):
    print(*a, flush=True)


def hr(title=""):
    log("\n" + "=" * 79)
    if title:
        log(title)
        log("=" * 79)


# ---------------------------------------------------------------- fetch layer
def fetch_fred(force=False):
    SNAP.mkdir(parents=True, exist_ok=True)
    for sid in FRED_IDS:
        p = SNAP / f"fred_{sid}.csv"
        if p.exists() and not force:
            continue
        log(f"  fetching FRED {sid} ...")
        with urllib.request.urlopen(FRED_URL.format(sid), timeout=60) as r:
            p.write_bytes(r.read())


def fetch_gmo_swaps(force=False):
    """Idempotent: only pulls calendar days not already in the snapshot."""
    have = {}
    if GMO_SWAP_CSV.exists() and not force:
        df = pd.read_csv(GMO_SWAP_CSV)
        have = {r.date: r for r in df.itertuples()}
    end = date.today()
    d, rows, misses = GMO_START, [], 0
    fetched = 0
    while d <= end:
        key = d.isoformat()
        if key in have:
            h = have[key]
            rows.append((key, h.swap_buy, h.swap_sell, h.swap_days))
            d += timedelta(days=1)
            continue
        try:
            req = urllib.request.Request(
                GMO_URL.format(d.strftime("%Y%m%d")),
                headers={"User-Agent": "Mozilla/5.0"},
            )
            with urllib.request.urlopen(req, timeout=30) as r:
                j = json.loads(r.read().decode())
        except Exception as exc:  # network hiccup -> retry same day
            log(f"    gmo retry {d}: {exc}")
            time.sleep(2.0)
            continue
        fetched += 1
        data = j.get("data")
        if data:
            rec = next((x for x in data if x["productId"] == GMO_PID), None)
            if rec:
                rows.append((key, int(rec["swapBuy"]), int(rec["swapSell"]), int(rec["swapDays"])))
        else:
            misses += 1
        d += timedelta(days=1)
        time.sleep(0.25)
    if fetched:
        pd.DataFrame(rows, columns=["date", "swap_buy", "swap_sell", "swap_days"]).to_csv(
            GMO_SWAP_CSV, index=False
        )
        log(f"  gmo swap: {len(rows)} rows on file ({fetched} newly fetched, {misses} empty days)")


# ----------------------------------------------------------------- load layer
def load_fred(sid):
    df = pd.read_csv(SNAP / f"fred_{sid}.csv")
    df.columns = ["date", "value"]
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df.dropna().set_index("date")["value"].sort_index()


def build_panel():
    px = load_fred("DEXJPUS")
    us = load_fred("DFF")
    jp_m = load_fred("IRSTCI01JPM156N")
    jp3_m = load_fred("IR3TIB01JPM156N")
    dgs2 = load_fred("DGS2")

    # --- JP monthly -> daily, LAGGED ONE MONTH (month M uses month M-1's value)
    def monthly_to_daily(s, index):
        lagged = s.copy()
        lagged.index = lagged.index + pd.offsets.MonthBegin(1)
        return lagged.reindex(index.union(lagged.index)).ffill().reindex(index)

    idx = px.index
    jp = monthly_to_daily(jp_m, idx)
    jp3 = monthly_to_daily(jp3_m, idx)
    us_d = us.reindex(idx.union(us.index)).ffill().reindex(idx)
    dgs2_d = dgs2.reindex(idx.union(dgs2.index)).ffill().reindex(idx)

    df = pd.DataFrame({"px": px, "us": us_d, "jp": jp, "jp3": jp3, "us2y": dgs2_d})
    df = df.dropna(subset=["px", "us", "jp"])
    df["diff"] = df["us"] - df["jp"]                      # primary, overnight
    df["diff_3m"] = df["us"] - df["jp3"]                  # robustness arm
    df["diff_2y"] = df["us2y"] - df["jp3"]                # forward-looking arm
    df["days"] = df.index.to_series().diff().dt.days
    df.loc[df.index[0], "days"] = 1.0
    df["ret"] = df["px"].pct_change()
    return df


# --------------------------------------------------------- swap calibration
def calibrate_swap(panel):
    """Return (mid_ratio, half_spread_bps_day, diagnostics DataFrame)."""
    g = pd.read_csv(GMO_SWAP_CSV)
    g["date"] = pd.to_datetime(g["date"])
    g = g.set_index("date").sort_index()
    g = g[g["swap_days"] > 0].copy()

    px = panel["px"].reindex(g.index.union(panel.index)).ffill().reindex(g.index)
    diff = panel["diff"].reindex(g.index.union(panel.index)).ffill().reindex(g.index)
    g["px"] = px
    g["diff"] = diff
    g = g.dropna(subset=["px", "diff"])

    # JPY per 10,000 USD -> bps of JPY notional per accrual DAY
    notional_jpy = 10_000.0 * g["px"]
    g["buy_bps_day"] = g["swap_buy"] / notional_jpy * 1e4 / g["swap_days"]
    g["sell_bps_day"] = g["swap_sell"] / notional_jpy * 1e4 / g["swap_days"]
    g["mid_bps_day"] = (g["buy_bps_day"] - g["sell_bps_day"]) / 2.0
    g["half_spread"] = (-g["sell_bps_day"] - g["buy_bps_day"]) / 2.0
    g["ib_bps_day"] = g["diff"] / 100.0 / 365.0 * 1e4
    g["ratio"] = g["mid_bps_day"] / g["ib_bps_day"]

    mid_ratio = float(g["ratio"].median())
    half_spread = float(g["half_spread"].median())
    return mid_ratio, half_spread, g


def carry_bps_day(diff_pct, side, mid_ratio, half_spread, model="gmo"):
    """bps per accrual day for a unit position on `side` (+1 long, -1 short)."""
    ib = diff_pct / 100.0 / 365.0 * 1e4
    if model == "gmo":
        return side * mid_ratio * ib - half_spread * np.abs(side)
    if model == "haircut25":
        gross = side * ib
        return np.where(gross >= 0, 0.75 * gross, 1.25 * gross)
    raise ValueError(model)


# ------------------------------------------------------------------- families
def build_weights(panel, family, sign_rule):
    """Weight for day t, decided ONLY from information up to and including t-1."""
    d_prev = panel["diff"].shift(1)
    if sign_rule == "follow":
        base = np.sign(d_prev)
    elif sign_rule == "longpos":
        base = (d_prev > 0).astype(float)
    else:
        raise ValueError(sign_rule)
    base = pd.Series(base, index=panel.index).fillna(0.0)

    if family == "C1":
        w = base
    elif family == "C2":
        sma = panel["px"].shift(1).rolling(SMA_WIN).mean()
        p_prev = panel["px"].shift(1)
        ok_long = p_prev >= sma
        ok_short = p_prev <= sma
        gate = np.where(base > 0, ok_long, np.where(base < 0, ok_short, False))
        w = base * pd.Series(gate.astype(float), index=panel.index)
        w = w.where(sma.notna(), 0.0)
    elif family == "C3":
        rv = panel["ret"].shift(1).rolling(VOL_WIN).std() * np.sqrt(TRADING_DAYS)
        scale = (VOL_TARGET / rv).clip(upper=1.0)
        w = base * scale
        w = w.where(rv.notna(), 0.0)
    else:
        raise ValueError(family)
    return w.fillna(0.0)


def run_config(panel, family, sign_rule, mid_ratio, half_spread, model="gmo"):
    w = build_weights(panel, family, sign_rule)
    side = np.sign(w)
    cb = carry_bps_day(panel["diff"].shift(1).fillna(0.0).to_numpy(), side.to_numpy(),
                       mid_ratio, half_spread, model=model)
    cb = pd.Series(cb, index=panel.index).fillna(0.0)
    swap_ret = np.abs(w) * cb * panel["days"] / 1e4
    price_ret = w * panel["ret"].fillna(0.0)
    turn = w.diff().abs().fillna(w.abs())
    cost_ret = turn * ONE_WAY_BPS / 1e4
    total = price_ret + swap_ret - cost_ret
    out = pd.DataFrame({
        "w": w, "price": price_ret, "swap": swap_ret,
        "cost": -cost_ret, "ret": total,
    })
    out["equity"] = (1.0 + out["ret"]).cumprod()
    return out


# -------------------------------------------------------------------- metrics
def max_dd(equity):
    peak = equity.cummax()
    return float((equity / peak - 1.0).min())


def dd_and_recovery(equity):
    peak = equity.cummax()
    dd = equity / peak - 1.0
    trough_i = dd.idxmin()
    depth = float(dd.min())
    pre_peak = float(peak.loc[trough_i])
    after = equity.loc[trough_i:]
    rec = after[after >= pre_peak]
    if len(rec):
        rec_date = rec.index[0]
        rec_days = int((rec_date - trough_i).days)
        rec_s = f"{rec_date.date()} ({rec_days}d)"
    else:
        rec_s = "NOT RECOVERED in-window"
    return depth, str(trough_i.date()), rec_s


def metrics(res):
    r = res["ret"]
    n = len(r)
    mu, sd = float(r.mean()), float(r.std(ddof=1))
    sharpe = mu / sd * np.sqrt(TRADING_DAYS) if sd > 0 else float("nan")
    eq = res["equity"]
    total = float(eq.iloc[-1] - 1.0)
    years = (res.index[-1] - res.index[0]).days / 365.25
    cagr = (eq.iloc[-1]) ** (1 / years) - 1 if years > 0 else float("nan")
    key = [r.index.year, r.index.month]
    mon = (1 + r).groupby(key).prod() - 1
    posmon = float((mon > 0).mean())
    # a month in which the family was flat every single day earns exactly 0 and
    # therefore counts as NOT positive.  Report how many such months there are so
    # the bar is not mistaken for a loss rate.
    flatmon = res["w"].abs().groupby(key).max() < 1e-9
    nflat = int(flatmon.sum())
    live = mon[~flatmon.reindex(mon.index).fillna(False)]
    posmon_live = float((live > 0).mean()) if len(live) else float("nan")
    exposure = float((res["w"].abs() > 1e-9).mean())
    years = (res.index[-1] - res.index[0]).days / 365.25
    return dict(n=n, sharpe=float(sharpe), maxdd=max_dd(eq), total=total,
                cagr=float(cagr), posmon=posmon, nmon=len(mon),
                nflatmon=nflat, posmon_live=posmon_live,
                vol=float(sd * np.sqrt(TRADING_DAYS)), exposure=exposure,
                price=float(res["price"].sum()), swap=float(res["swap"].sum()),
                cost=float(res["cost"].sum()),
                swap_yr=float(res["swap"].sum() / years) if years > 0 else float("nan"),
                price_yr=float(res["price"].sum() / years) if years > 0 else float("nan"),
                turnover=float(res["w"].diff().abs().sum()))


def fmt_row(name, m):
    return (f"  {name:<22} n={m['n']:>5}  Sharpe={m['sharpe']:+.3f}  maxDD={m['maxdd']*100:7.2f}%  "
            f"CAGR={m['cagr']*100:+6.2f}%  tot={m['total']*100:+8.1f}%  "
            f"vol={m['vol']*100:5.2f}%  +mon={m['posmon']*100:5.1f}%  expo={m['exposure']*100:5.1f}%  "
            f"swap/yr={m['swap_yr']*100:+5.2f}%  px/yr={m['price_yr']*100:+6.2f}%  "
            f"flatmon={m['nflatmon']:>3}/{m['nmon']}")


# ------------------------------------------------------------------ validation
def validate_price(panel):
    hr("SANITY 1 -- DEXJPUS vs data/fx/USDJPY_1m.csv daily closes")
    p = ROOT / "data" / "fx" / "USDJPY_1m.csv"
    if not p.exists():
        log("  data/fx/USDJPY_1m.csv absent -- validation SKIPPED")
        return
    df = pd.read_csv(p, usecols=["timestamp", "close"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.set_index("timestamp")
    # DEXJPUS is the noon NY buying rate ~ 17:00 UTC (16:00 UTC under EDT).
    # Take the 1m bar nearest 16:30 UTC on each date as the comparison point.
    df["d"] = df.index.date
    tod = df.index.hour * 60 + df.index.minute
    df["off"] = np.abs(np.asarray(tod) - (16 * 60 + 30))
    pick = df.loc[df.groupby("d")["off"].idxmin()]
    dk = pd.Series(pick["close"].to_numpy(),
                   index=pd.to_datetime([str(x) for x in pick["d"]]))
    both = pd.DataFrame({"fred": panel["px"], "duka": dk}).dropna()
    rel = (both["duka"] / both["fred"] - 1.0) * 100
    log(f"  overlap days            : {len(both)}  ({both.index[0].date()} .. {both.index[-1].date()})")
    log(f"  median rel diff         : {rel.median():+.4f}%")
    log(f"  mean  rel diff          : {rel.mean():+.4f}%")
    log(f"  p95 |rel diff|          : {rel.abs().quantile(0.95):.4f}%")
    log(f"  max   |rel diff|        : {rel.abs().max():.4f}%")
    frac = float((rel.abs() <= 0.5).mean())
    log(f"  within +-0.5%           : {frac*100:.2f}%  ->  "
        f"{'PASS' if frac >= 0.95 else 'FAIL'}")


def validate_daycount(gcal):
    hr("SANITY 2 -- swap day-count on known Wednesdays (3-day roll)")
    g = gcal.copy()
    g["dow"] = g.index.dayofweek
    tab = g.groupby("dow")["swap_days"].agg(["count", "median", "mean"])
    names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    for d, row in tab.iterrows():
        log(f"  {names[d]}  n={int(row['count']):>4}  median days={row['median']:.0f}  mean={row['mean']:.2f}")
    for ds in ["2026-08-19", "2026-07-15", "2025-10-15", "2024-05-15"]:
        ts = pd.Timestamp(ds)
        if ts in g.index:
            r = g.loc[ts]
            log(f"  {ds} ({names[ts.dayofweek]}): swapDays={int(r['swap_days'])}  "
                f"buy={int(r['swap_buy'])} JPY/10k  sell={int(r['swap_sell'])} JPY/10k")
    wk = g[g["dow"] <= 4]
    log(f"  weekday accrual days per full week (median sum) = "
        f"{wk.groupby([wk.index.isocalendar().year, wk.index.isocalendar().week])['swap_days'].sum().median():.0f}"
        "  (expected 7)")


# ----------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true", help="force re-download of snapshots")
    args = ap.parse_args()

    hr("FX STUDY S5 -- CARRY AS ENGINEERED INCOME")
    log("[0] data acquisition (idempotent)")
    fetch_fred(force=args.fetch)
    if not GMO_SWAP_CSV.exists() or args.fetch:
        fetch_gmo_swaps(force=args.fetch)
    for sid in FRED_IDS:
        p = SNAP / f"fred_{sid}.csv"
        log(f"  {p.name:<34} {p.stat().st_size:>8} bytes")
    log(f"  {GMO_SWAP_CSV.name:<34} {GMO_SWAP_CSV.stat().st_size:>8} bytes")

    panel = build_panel()
    hr("PANEL")
    log(f"  rows                    : {len(panel)}")
    log(f"  span                    : {panel.index[0].date()} .. {panel.index[-1].date()} "
        f"({(panel.index[-1]-panel.index[0]).days/365.25:.1f} years)")
    log(f"  USD/JPY range           : {panel['px'].min():.2f} .. {panel['px'].max():.2f}")
    log(f"  differential (US-JP) %  : min={panel['diff'].min():+.2f}  "
        f"median={panel['diff'].median():+.2f}  max={panel['diff'].max():+.2f}")
    neg = float((panel["diff"] < 0).mean())
    log(f"  days with NEGATIVE diff : {neg*100:.2f}%  "
        f"({panel.index[panel['diff'] < 0].min().date() if neg else '-'} .. "
        f"{panel.index[panel['diff'] < 0].max().date() if neg else '-'})")

    validate_price(panel)

    mid_ratio, half_spread, gcal = calibrate_swap(panel)
    hr("SANITY 3 / CALIBRATION -- GMO actual swap calendar vs interbank differential")
    log(f"  GMO calendar rows       : {len(gcal)}  "
        f"({gcal.index[0].date()} .. {gcal.index[-1].date()})")
    log(f"  gmo mid / interbank     : median={mid_ratio:.4f}  "
        f"p25={gcal['ratio'].quantile(.25):.4f}  p75={gcal['ratio'].quantile(.75):.4f}")
    log(f"  implied HAIRCUT on mid  : {(1-mid_ratio)*100:+.2f}%   "
        f"(the instructed conservative fallback was 25%)")
    log(f"  half-spread (bps/day)   : median={half_spread:.4f}  "
        f"p25={gcal['half_spread'].quantile(.25):.4f}  p75={gcal['half_spread'].quantile(.75):.4f}")
    log(f"  long  received (bps/day): median={gcal['buy_bps_day'].median():+.4f}")
    log(f"  short paid     (bps/day): median={gcal['sell_bps_day'].median():+.4f}")
    log(f"  interbank      (bps/day): median={gcal['ib_bps_day'].median():+.4f}")
    log(f"  -> KNOWLEDGE_FX sec.1 [T] estimate was 0.6-1.6 bps/day; MEASURED long "
        f"receive is {gcal['buy_bps_day'].median():.3f} bps/day over "
        f"{gcal.index[0].date()}..{gcal.index[-1].date()}")
    by_yr = gcal.groupby(gcal.index.year).agg(
        n=("ratio", "size"), ratio=("ratio", "median"),
        hs=("half_spread", "median"), buy=("buy_bps_day", "median"))
    log("  per-year calibration:")
    for y, r in by_yr.iterrows():
        log(f"    {y}  n={int(r['n']):>3}  mid/ib={r['ratio']:.4f}  "
            f"half-spread={r['hs']:.4f} bps/d  long-receive={r['buy']:+.4f} bps/d")

    validate_daycount(gcal)

    # ---------------------------------------------------------------- split
    n = len(panel)
    cut = int(n * SPLIT_FRAC)
    boundary = panel.index[cut]
    explore = panel.iloc[:cut]
    judge = panel.iloc[cut:]
    hr("SPLIT (chronological 60/40 by row count)")
    log(f"  N={n}  cut index={cut}  boundary={boundary.date()}")
    log(f"  EXPLORE : {explore.index[0].date()} .. {explore.index[-1].date()}  n={len(explore)}")
    log(f"  JUDGE   : {judge.index[0].date()} .. {judge.index[-1].date()}  n={len(judge)}")

    configs = [(f, s) for f in FAMILIES for s in SIGN_RULES]

    def run_on(sub, model="gmo"):
        return {(f, s): run_config(sub, f, s, mid_ratio, half_spread, model)
                for f, s in configs}

    # C2/C3 need warm-up; run on the FULL panel then slice, so the JUDGE window
    # is not handicapped by a cold start (warm-up uses only EXPLORE-side data).
    full = run_on(panel)
    full_hc = run_on(panel, model="haircut25")

    def slice_res(res, sub):
        r = res.loc[sub.index].copy()
        r["equity"] = (1.0 + r["ret"]).cumprod()
        return r

    hr("EXPLORE WINDOW -- all 6 configs (selection happens HERE and only here)")
    ex_m = {}
    for f, s in configs:
        m = metrics(slice_res(full[(f, s)], explore))
        ex_m[(f, s)] = m
        log(fmt_row(f"{f}/{s}", m))
    winner = max(ex_m, key=lambda k: ex_m[k]["sharpe"])
    log(f"\n  EXPLORE WINNER (max Sharpe, pre-registered rule) = {winner[0]}/{winner[1]}")

    hr("JUDGE WINDOW -- executed once, reported as-is")
    ju_m = {}
    for f, s in configs:
        m = metrics(slice_res(full[(f, s)], judge))
        ju_m[(f, s)] = m
        mark = "  <== carried from EXPLORE" if (f, s) == winner else ""
        log(fmt_row(f"{f}/{s}", m) + mark)
    ju_win = max(ju_m, key=lambda k: ju_m[k]["sharpe"])
    log(f"\n  JUDGE max-Sharpe config = {ju_win[0]}/{ju_win[1]}")
    if ju_win != winner:
        log("  *** CONFIG SWITCHING between EXPLORE and JUDGE -> overfitting signal "
            "(research-protocol sec.2). The EXPLORE winner stands as the judged config.")
    else:
        log("  no config switching: EXPLORE and JUDGE agree on the same config.")

    hr("ADOPTION VERDICT -- registered bars applied to the EXPLORE winner on JUDGE")
    m = ju_m[winner]
    checks = [
        ("Sharpe >= 0.70", m["sharpe"], BAR_SHARPE, m["sharpe"] >= BAR_SHARPE, "{:+.3f}"),
        ("maxDD <= 12.0%", m["maxdd"] * 100, -BAR_MAXDD * 100, m["maxdd"] >= -BAR_MAXDD, "{:.2f}%"),
        ("positive months >= 60%", m["posmon"] * 100, BAR_POSMON * 100, m["posmon"] >= BAR_POSMON, "{:.1f}%"),
        ("total return > 0", m["total"] * 100, 0.0, m["total"] > 0, "{:+.1f}%"),
    ]
    log(f"  config: {winner[0]}/{winner[1]}   window: {judge.index[0].date()} .. {judge.index[-1].date()}")
    allpass = True
    for name, val, bar, ok, fmt in checks:
        allpass &= ok
        log(f"    {name:<26} actual={fmt.format(val):>10}   bar={fmt.format(bar):>10}   "
            f"{'PASS' if ok else 'FAIL'}")
    log(f"    (diagnostic) fully-flat months  = {m['nflatmon']}/{m['nmon']}; "
        f"positive months among NON-flat months = {m['posmon_live']*100:.1f}%")
    log(f"    (diagnostic) swap income {m['swap_yr']*100:+.2f}%/yr vs price P&L "
        f"{m['price_yr']*100:+.2f}%/yr on JUDGE")
    log(f"\n  VERDICT: {'ADOPT (all bars met)' if allpass else 'REJECT (at least one bar missed)'}")
    log("  (Every other config's JUDGE numbers are above and are DIAGNOSTIC ONLY -- "
        "research-protocol sec.8.2 forbids promoting a diagnostic to an adoption.)")

    # ------------------------------------------------------- full-sample view
    hr("FULL-SAMPLE (1985-2026) -- context, not a test")
    for f, s in configs:
        log(fmt_row(f"{f}/{s}", metrics(full[(f, s)])))
    log("\n  buy-and-hold USD/JPY long, NO carry, for reference:")
    bh = pd.DataFrame({"w": 1.0, "price": panel["ret"].fillna(0.0), "swap": 0.0,
                       "cost": 0.0, "ret": panel["ret"].fillna(0.0)}, index=panel.index)
    bh["equity"] = (1 + bh["ret"]).cumprod()
    log(fmt_row("buyhold(price only)", metrics(bh)))

    # ------------------------------------------------- price vs swap per year
    hr("MANDATORY DECOMPOSITION -- price P&L vs swap P&L, PER YEAR")
    for f, s in [(winner[0], winner[1]), ("C1", "follow")] if winner != ("C1", "follow") else [("C1", "follow")]:
        res = full[(f, s)]
        log(f"\n  --- {f}/{s} ---")
        log(f"  {'year':<6}{'price%':>9}{'swap%':>9}{'cost%':>8}{'total%':>9}"
            f"{'expo%':>8}{'|w|avg':>8}")
        yr = res.groupby(res.index.year).agg(
            price=("price", "sum"), swap=("swap", "sum"), cost=("cost", "sum"),
            ret=("ret", "sum"), expo=("w", lambda x: (x.abs() > 1e-9).mean()),
            wavg=("w", lambda x: x.abs().mean()))
        for y, r in yr.iterrows():
            log(f"  {y:<6}{r['price']*100:>9.2f}{r['swap']*100:>9.2f}{r['cost']*100:>8.3f}"
                f"{r['ret']*100:>9.2f}{r['expo']*100:>8.1f}{r['wavg']:>8.2f}")
        tp, ts_, tc = res["price"].sum(), res["swap"].sum(), res["cost"].sum()
        log(f"  {'TOTAL':<6}{tp*100:>9.2f}{ts_*100:>9.2f}{tc*100:>8.3f}"
            f"{(tp+ts_+tc)*100:>9.2f}")
        log(f"  swap P&L is {abs(ts_)/(abs(tp)+abs(ts_))*100:.1f}% of gross |P&L|; "
            f"price P&L annual sd = {(yr['price']*100).std():.2f}pp vs swap "
            f"{(yr['swap']*100).std():.2f}pp "
            f"-> price path is {(yr['price']*100).std()/max((yr['swap']*100).std(),1e-9):.1f}x "
            f"as volatile as the income stream")

    # ------------------------------------------------------- stress windows
    hr("NAMED STRESS WINDOWS -- drawdown and recovery (full-sample equity)")
    for f, s in configs:
        res = full[(f, s)]
        log(f"\n  --- {f}/{s} ---")
        for name, a, b in STRESS:
            sub = res.loc[a:b]
            if len(sub) < 5:
                continue
            eq = (1 + sub["ret"]).cumprod()
            depth, trough, rec_in = dd_and_recovery(eq)
            # recovery measured on the ONGOING equity beyond the window too
            full_eq = res["equity"]
            pre = full_eq.loc[:a].iloc[-1] if len(full_eq.loc[:a]) else full_eq.iloc[0]
            after = full_eq.loc[pd.Timestamp(trough):]
            recov = after[after >= pre]
            rec_glob = (f"{recov.index[0].date()} "
                        f"({(recov.index[0]-pd.Timestamp(trough)).days}d)"
                        if len(recov) else "never (to 2026)")
            ret_w = float(eq.iloc[-1] - 1)
            log(f"    {name:<24} ret={ret_w*100:+7.2f}%  in-window maxDD={depth*100:7.2f}%  "
                f"trough={trough}  recovered={rec_glob}")

    # ------------------------------------------------------- sensitivities
    hr("SENSITIVITY -- swap model: GMO-calibrated vs instructed flat 25% haircut")
    log("  (reported only; selection used the GMO-calibrated model as pre-registered)")
    for f, s in configs:
        a = metrics(slice_res(full[(f, s)], judge))
        b = metrics(slice_res(full_hc[(f, s)], judge))
        log(f"  {f}/{s:<8} JUDGE Sharpe  gmo={a['sharpe']:+.3f}  hc25={b['sharpe']:+.3f}  "
            f"(swap P&L gmo={a['swap']*100:+.1f}%  hc25={b['swap']*100:+.1f}%)")

    hr("SENSITIVITY -- JP rate leg (overnight call vs 3M interbank vs 2y-forward)")
    log("  (robustness only; the pre-registered leg is the overnight call rate)")
    for alt in ["diff_3m", "diff_2y"]:
        p2 = panel.copy()
        p2 = p2.dropna(subset=[alt])
        if len(p2) < 500:
            log(f"  {alt}: insufficient overlap ({len(p2)} rows) -- skipped")
            continue
        p2["diff"] = p2[alt]
        p2["days"] = p2.index.to_series().diff().dt.days.fillna(1.0)
        r2 = {(f, s): run_config(p2, f, s, mid_ratio, half_spread) for f, s in configs}
        jsub = p2.loc[p2.index >= boundary]
        log(f"  --- {alt}  span {p2.index[0].date()}..{p2.index[-1].date()}  "
            f"JUDGE n={len(jsub)}")
        for f, s in configs:
            rr = r2[(f, s)].loc[jsub.index].copy()
            rr["equity"] = (1 + rr["ret"]).cumprod()
            log(fmt_row(f"{f}/{s}", metrics(rr)))

    # ------------------------------------------------------- final sanities
    hr("SANITY 4 -- look-ahead audit")
    w = build_weights(panel, "C2", "follow")
    sma = panel["px"].shift(1).rolling(SMA_WIN).mean()
    log(f"  C2 gate uses SMA200 of px.shift(1): first non-NaN weight at "
        f"{panel.index[sma.notna()][0].date()} (= row {int(np.argmax(sma.notna().to_numpy()))}, "
        f"expected {SMA_WIN})")
    rv = panel["ret"].shift(1).rolling(VOL_WIN).std()
    log(f"  C3 scale uses 63d vol of ret.shift(1): first non-NaN at "
        f"{panel.index[rv.notna()][0].date()} (= row {int(np.argmax(rv.notna().to_numpy()))}, "
        f"expected {VOL_WIN + 1})")
    corr = float(pd.Series(w).corr(panel["ret"]))
    log(f"  corr(weight_t, return_t) over full sample = {corr:+.4f}  "
        f"(a large positive value would betray look-ahead)")
    log(f"  weight is a function of shift(1) series only -- verified structurally")
    dpy = panel.groupby(panel.index.year)["days"].sum()
    dpy = dpy.iloc[1:-1]
    log(f"  accrual days per FULL year: min={dpy.min():.0f} median={dpy.median():.0f} "
        f"max={dpy.max():.0f}  (expected 365/366 -- confirms the calendar-gap "
        f"aggregation reproduces the Wed 3-day roll over a year)")

    hr("SANITY 5 -- determinism")
    def digest():
        h = hashlib.sha256()
        for f, s in configs:
            r = run_config(panel, f, s, mid_ratio, half_spread)
            h.update(np.round(r["ret"].to_numpy(), 12).tobytes())
        return h.hexdigest()
    d1, d2 = digest(), digest()
    log(f"  run1 sha256 = {d1}")
    log(f"  run2 sha256 = {d2}")
    log(f"  determinism : {'PASS' if d1 == d2 else 'FAIL'}")

    hr("CAVEATS (honest limits)")
    for line in [
        f"1. Retail haircut is calibrated on GMO's ACTUAL calendar but only over "
        f"{gcal.index[0].date()}..{gcal.index[-1].date()} -- a single (positive-differential, "
        f"high-US-rate) regime. It is EXTRAPOLATED over 1985-2023. GMO did not exist "
        f"for most of the sample; the true 1985-2005 retail haircut was almost "
        f"certainly WORSE (wider retail spreads pre-electronic).",
        "2. The 25%-haircut sensitivity is the instructed conservative fallback and "
        "is materially harsher than GMO's measured pass-through; both are shown.",
        "3. JP rate leg is a MONTHLY average lagged one month. Intra-month BOJ moves "
        "are smeared. The overnight call rate is policy-pinned so the error is small, "
        "but 2024-2026 BOJ normalisation steps are smoothed by up to ~6 weeks.",
        "4. DEXJPUS is a single daily fix (noon NY). Intraday path, weekend gap shape, "
        "and 6:00 JST swap-boundary timing are invisible at this resolution. The "
        "reported maxDD is a CLOSE-TO-CLOSE floor -- true intraday drawdowns "
        "(and margin calls) are deeper.",
        "5. NO LEVERAGE is modelled. GMO offers 25x. Every drawdown number below "
        "scales roughly linearly with leverage: a 12% unlevered DD is a 100%+ "
        "wipe-out at 10x. Leverage is a separate owner decision and this study "
        "gives it NO support.",
        "6. Intervention tail (KNOWLEDGE_FX sec.2): MOF intervention is one-directional, "
        "unlimited and hundreds of bps per MINUTE. A daily-close study cannot see it. "
        "The tail rule (position cap + kill on >100bps/5min) remains mandatory and is "
        "NOT a substitute for the risk numbers here.",
        "7. Sharpe is computed on excess-of-zero daily returns (no risk-free "
        "subtraction). In a 5% JPY-funding world that would be a different number; "
        "for a JPY-based book funded at the JP call rate the convention used here "
        "(the swap already nets the funding) is the right one.",
    ]:
        log(f"  {line}")

    hr("END")


if __name__ == "__main__":
    sys.exit(main())
