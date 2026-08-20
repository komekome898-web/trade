#!/usr/bin/env python3
"""
STORM PRECURSORS -- offline study.

Pre-registered question: can calm-period features predict imminent violent moves?

Anchor market: Binance BTCUSDT 1m (90 days).
Storm minute : |rolling 30m log-return| >= 0.8%.
Storm event  : first storm minute after >= 2h with no storm minutes.

All features are causal (computed from data <= t). Percentiles use a trailing
14-day window shifted 1 minute (the reference window is t-20160 .. t-1, the
current value is ranked against it and never against itself).

Split: first 60% of minutes = train (construction sanity-check only, no tuning),
last 40% = evaluation. Judgement is on the evaluation segment.

Usage:  PYTHONPATH=src python scripts/research_storm.py
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------- #
# config (all pre-registered, nothing here was tuned)
# --------------------------------------------------------------------------- #
DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

STORM_WINDOW_MIN = 30          # rolling window for the storm return
STORM_THRESHOLD = 0.008        # 0.8% absolute log return
STORM_DEDUP_MIN = 120          # >= 2h of calm required before a new event
PCT_WINDOW_MIN = 14 * 24 * 60  # 14-day rolling reference window = 20160 minutes
HORIZONS = [120, 360]          # 2h and 6h
TRAIN_FRAC = 0.60

ADOPT_LIFT = 2.0
ADOPT_RECALL = 0.10
ADOPT_MIN_EVENTS = 30


def line(char: str = "-", n: int = 88) -> None:
    print(char * n)


def header(title: str) -> None:
    print()
    line("=")
    print(title)
    line("=")


# --------------------------------------------------------------------------- #
# loading
# --------------------------------------------------------------------------- #
def load_binance() -> pd.DataFrame:
    df = pd.read_csv(os.path.join(DATA, "binance_BTCUSDT_1m.csv"), parse_dates=["timestamp"])
    df = df.set_index("timestamp").sort_index()
    df = df[~df.index.duplicated(keep="first")]
    # reindex onto a strict 1-minute grid so all rolling windows are true clock windows
    full = pd.date_range(df.index[0], df.index[-1], freq="1min", tz="UTC")
    gaps = len(full) - len(df)
    df = df.reindex(full)
    df["volume"] = df["volume"].fillna(0.0)
    df[["open", "high", "low", "close"]] = df[["open", "high", "low", "close"]].ffill()
    df.index.name = "ts"
    print(f"binance 1m : {df.index[0]} .. {df.index[-1]}  rows={len(df)}  filled_gaps={gaps}")
    return df


def load_flow() -> pd.DataFrame:
    df = pd.read_csv(os.path.join(DATA, "flow_FX_BTC_JPY.csv"), parse_dates=["ts"])
    df = df.set_index("ts").sort_index()
    df = df[~df.index.duplicated(keep="first")]
    print(f"bitflyer   : {df.index[0]} .. {df.index[-1]}  rows={len(df)}")
    return df


def load_funding() -> pd.DataFrame:
    df = pd.read_csv(os.path.join(DATA, "funding_rate_history.csv"))
    df["settlement_date"] = pd.to_datetime(df["settlement_date"], utc=True)
    df = df.sort_values("settlement_date").reset_index(drop=True)
    print(f"funding    : {df['settlement_date'].iloc[0]} .. {df['settlement_date'].iloc[-1]}  n={len(df)}")
    return df


# --------------------------------------------------------------------------- #
# causal percentile rank against a trailing window shifted by 1 minute
# --------------------------------------------------------------------------- #
def causal_pct_rank(s: pd.Series, window: int = PCT_WINDOW_MIN) -> pd.Series:
    """Fraction of the previous `window` observations that are strictly below s[t].

    Window covers t-window .. t-1 (shifted by one minute); the current value is
    ranked against the past only, so the statistic is strictly causal.
    """
    rank_min = s.rolling(window + 1, min_periods=window + 1).rank(method="min")
    return (rank_min - 1.0) / float(window)


# --------------------------------------------------------------------------- #
# storms
# --------------------------------------------------------------------------- #
def build_storms(px: pd.Series) -> tuple[pd.Series, pd.DatetimeIndex]:
    logp = np.log(px)
    ret30 = logp - logp.shift(STORM_WINDOW_MIN)
    storm_min = (ret30.abs() >= STORM_THRESHOLD).fillna(False)

    # de-duplicate: an event is a storm minute preceded by >= 2h with no storm minute
    prior = storm_min.rolling(STORM_DEDUP_MIN, min_periods=STORM_DEDUP_MIN).sum().shift(1)
    is_event = storm_min & (prior == 0)
    events = px.index[is_event.fillna(False).to_numpy()]
    return storm_min, events


def event_flag_forward(index: pd.DatetimeIndex, events: pd.DatetimeIndex, horizon: int) -> np.ndarray:
    """True at minute t iff a storm event starts in (t, t+horizon]."""
    ev = np.zeros(len(index), dtype=np.float64)
    pos = index.get_indexer(events)
    ev[pos[pos >= 0]] = 1.0
    s = pd.Series(ev, index=index)
    # count of events in (t, t+H]  == reversed trailing sum
    fwd = s[::-1].rolling(horizon, min_periods=1).sum()[::-1].shift(-1)
    fwd = fwd.fillna(0.0)
    # the last `horizon` minutes cannot be fully observed -> mark them invalid
    valid = np.ones(len(index), dtype=bool)
    valid[-horizon:] = False
    out = (fwd.to_numpy() > 0).astype(float)
    out[~valid] = np.nan
    return out


# --------------------------------------------------------------------------- #
# features
# --------------------------------------------------------------------------- #
def build_features(b: pd.DataFrame, flow: pd.DataFrame, funding: pd.DataFrame) -> pd.DataFrame:
    idx = b.index
    close = b["close"]
    high = b["high"]
    low = b["low"]
    vol = b["volume"]
    logc = np.log(close)
    ret1 = logc.diff()

    f = pd.DataFrame(index=idx)

    # ---- realized ranges (log high/low over the trailing window) ----
    def realized_range(win: int) -> pd.Series:
        hh = high.rolling(win, min_periods=win).max()
        ll = low.rolling(win, min_periods=win).min()
        return np.log(hh / ll)

    rng_1h = realized_range(60)
    rng_30m = realized_range(30)
    pct_rng_1h = causal_pct_rank(rng_1h)
    pct_rng_30m = causal_pct_rank(rng_30m)

    # ---- F1: volume rise while price is quiet ----
    vol_1h = vol.rolling(60, min_periods=60).sum()
    avg_hourly_vol_24h = vol.rolling(1440, min_periods=1440).sum() / 24.0
    volume_ratio = vol_1h / avg_hourly_vol_24h
    f["F1"] = (volume_ratio > 1.5) & (pct_rng_1h < 0.30)

    # ---- F2: squeeze (6h realized vol of 1m returns, percentile < 10%) ----
    rv_6h = ret1.rolling(360, min_periods=360).std()
    pct_rv_6h = causal_pct_rank(rv_6h)
    f["F2"] = pct_rv_6h < 0.10

    # ---- F3: squeeze-release arm ----
    f2_recent_3h = f["F2"].rolling(180, min_periods=1).max().astype(bool)
    cross_up_50 = (pct_rng_30m > 0.50) & (pct_rng_30m.shift(1) <= 0.50)
    f["F3"] = f2_recent_3h & cross_up_50.fillna(False)

    # ---- F4: funding pressure (8h grain, past settlements only) ----
    f["F4"] = funding_pressure(idx, funding)

    # ---- F5: bitFlyer absorption (30-day span only) ----
    f5, f5_avail = bitflyer_absorption(idx, flow)
    f["F5"] = f5
    f["F5_avail"] = f5_avail

    # ---- F6: volume acceleration ----
    vol_15m = vol.rolling(15, min_periods=15).sum()
    vol_6h = vol.rolling(360, min_periods=360).sum()
    avg_15m_over_6h = vol_6h / 24.0
    f["F6"] = vol_15m > 3.0 * avg_15m_over_6h

    for c in ["F1", "F2", "F3", "F4", "F5", "F6"]:
        f[c] = f[c].fillna(False).astype(bool)

    # warm-up mask: all percentile/rolling inputs available
    warm = pct_rng_1h.notna() & pct_rv_6h.notna() & pct_rng_30m.notna() & volume_ratio.notna() & vol_6h.notna()
    f["warm"] = warm.fillna(False)

    # diagnostics kept for the sanity-check print
    f["_volume_ratio"] = volume_ratio
    f["_pct_rng_1h"] = pct_rng_1h
    f["_pct_rv_6h"] = pct_rv_6h
    return f


def funding_pressure(idx: pd.DatetimeIndex, funding: pd.DataFrame) -> pd.Series:
    """|most recent settled rate| >= 80th percentile of |rate| over the past 30 days.

    Both the "most recent" rate and the percentile threshold use only settlements
    whose settlement_date is <= t.
    """
    fd = funding.copy()
    fd["abs_rate"] = fd["rate"].abs()
    sd = fd["settlement_date"].to_numpy()
    ar = fd["abs_rate"].to_numpy()

    # threshold at each settlement: 80th pct of |rate| over settlements in (s-30d, s]
    thr = np.full(len(fd), np.nan)
    for i, s in enumerate(sd):
        mask = (sd <= s) & (sd > s - np.timedelta64(30, "D"))
        if mask.sum() >= 10:  # need a minimally populated window
            thr[i] = np.percentile(ar[mask], 80)
    on_at_settlement = ar >= thr  # NaN thr -> False

    # map each minute to the most recent settlement at or before it
    pos = np.searchsorted(sd, idx.to_numpy(), side="right") - 1
    out = np.zeros(len(idx), dtype=bool)
    ok = pos >= 0
    out[ok] = np.nan_to_num(on_at_settlement[pos[ok]].astype(float), nan=0.0).astype(bool)
    return pd.Series(out, index=idx)


def bitflyer_absorption(idx: pd.DatetimeIndex, flow: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    fl = flow.reindex(pd.date_range(flow.index[0], flow.index[-1], freq="1min", tz="UTC"))
    buy = fl["buy_vol"].fillna(0.0)
    sell = fl["sell_vol"].fillna(0.0)
    hi = fl["high"].ffill()
    lo = fl["low"].ffill()

    b1 = buy.rolling(60, min_periods=60).sum()
    s1 = sell.rolling(60, min_periods=60).sum()
    tot = b1 + s1
    imb = (b1 - s1).abs() / tot.replace(0.0, np.nan)

    rng = np.log(hi.rolling(60, min_periods=60).max() / lo.rolling(60, min_periods=60).min())
    # only ~30 days of bitFlyer data -> a full 14-day reference window leaves ~16 usable days
    pct_rng = causal_pct_rank(rng)

    sig = (imb > 0.25) & (pct_rng < 0.30)
    avail = imb.notna() & pct_rng.notna()

    return (
        sig.reindex(idx).fillna(False).astype(bool),
        avail.reindex(idx).fillna(False).astype(bool),
    )


# --------------------------------------------------------------------------- #
# evaluation
# --------------------------------------------------------------------------- #
def eval_feature(
    sig: np.ndarray,          # bool, signal ON
    fwd: np.ndarray,          # 1.0 if a storm event starts within horizon, nan if unobservable
    mask: np.ndarray,         # bool, minutes admissible for this feature/segment
    index: pd.DatetimeIndex,
    events: pd.DatetimeIndex,
    horizon: int,
) -> dict:
    obs = mask & ~np.isnan(fwd)
    base = float(np.nanmean(fwd[obs])) if obs.sum() else np.nan

    on = obs & sig
    n_on = int(on.sum())
    p_on = float(np.nanmean(fwd[on])) if n_on else np.nan
    lift = p_on / base if (n_on and base and base > 0) else np.nan
    duty = 100.0 * sig[mask].mean() if mask.sum() else np.nan

    # recall + lead time: storm events inside the masked segment
    pos_all = index.get_indexer(events)
    seg_events = [p for p in pos_all if p >= 0 and mask[p]]
    caught, leads = 0, []
    for p in seg_events:
        lo = max(0, p - horizon)
        win = sig[lo:p] & mask[lo:p]
        if win.any():
            caught += 1
            first = int(np.argmax(win))          # earliest ON minute inside the lookback
            leads.append(p - (lo + first))
    recall = caught / len(seg_events) if seg_events else np.nan
    med_lead = float(np.median(leads)) if leads else np.nan

    return dict(
        base=base, p_on=p_on, lift=lift, duty=duty, n_on=n_on,
        recall=recall, caught=caught, n_events=len(seg_events), med_lead=med_lead,
    )


def print_table(rows: list[tuple[str, dict]], horizon: int, seg: str) -> None:
    print(f"\n[{seg}]  horizon = {horizon}m ({horizon // 60}h)")
    print(f"{'feature':<26}{'duty%':>8}{'P(storm|ON)':>13}{'base':>9}{'lift':>8}"
          f"{'recall':>9}{'caught/ev':>12}{'med_lead':>10}")
    line()
    for name, m in rows:
        p_on = "-" if np.isnan(m["p_on"]) else f"{m['p_on'] * 100:.2f}%"
        lift = "-" if np.isnan(m["lift"]) else f"{m['lift']:.2f}"
        lead = "-" if np.isnan(m["med_lead"]) else f"{m['med_lead']:.0f}m"
        caught = f"{m['caught']}/{m['n_events']}"
        print(f"{name:<26}{m['duty']:>8.2f}{p_on:>13}{m['base'] * 100:>8.2f}%"
              f"{lift:>8}{m['recall']:>9.3f}{caught:>12}{lead:>10}")


# --------------------------------------------------------------------------- #
def main() -> None:
    header("STORM PRECURSORS  --  data load")
    b = load_binance()
    flow = load_flow()
    funding = load_funding()

    # ---------------- storms ----------------
    header("1. STORM DEFINITION")
    storm_min, events = build_storms(b["close"])
    idx = b.index
    n_days = (idx[-1] - idx[0]).total_seconds() / 86400.0
    print(f"storm minute  : |30m log-return| >= {STORM_THRESHOLD * 100:.1f}%")
    print(f"storm minutes : {int(storm_min.sum())} of {len(idx)} ({100 * storm_min.mean():.2f}% of minutes)")
    print(f"storm EVENTS  : {len(events)} over {n_days:.1f} days "
          f"({len(events) / n_days * 7:.1f} per week)")

    for H in HORIZONS:
        fwd = event_flag_forward(idx, events, H)
        print(f"base rate P(storm event begins within next {H // 60}h | random minute) = "
              f"{100 * np.nanmean(fwd):.2f}%")

    print("\nstorm events per calendar week (regime check):")
    wk = pd.Series(1, index=events).resample("7D").sum()
    for d, c in wk.items():
        print(f"  {d.date()}  {int(c):>3}  " + "#" * int(c))

    # ---------------- features ----------------
    header("2. FEATURES (causal)")
    f = build_features(b, flow, funding)
    warm = f["warm"].to_numpy()
    print(f"warm-up complete from {idx[np.argmax(warm)]}  "
          f"({int(warm.sum())} of {len(idx)} minutes usable)")
    print("\nduty cycle over all warm minutes:")
    for c in ["F1", "F2", "F3", "F4", "F5", "F6"]:
        m = warm & (f["F5_avail"].to_numpy() if c == "F5" else True)
        print(f"  {c}: {100 * f[c].to_numpy()[m].mean():>6.2f}%   ({int(f[c].to_numpy()[m].sum())} minutes ON"
              f"{', bitFlyer window only' if c == 'F5' else ''})")
    print(f"\nsanity: median 1h volume_ratio={f['_volume_ratio'].median():.2f}, "
          f"median pct_rng_1h={f['_pct_rng_1h'].median():.3f}, "
          f"median pct_rv_6h={f['_pct_rv_6h'].median():.3f}  (percentiles should sit near 0.5)")

    # ---------------- split ----------------
    split_i = int(len(idx) * TRAIN_FRAC)
    split_ts = idx[split_i]
    seg_train = np.zeros(len(idx), dtype=bool); seg_train[:split_i] = True
    seg_eval = np.zeros(len(idx), dtype=bool); seg_eval[split_i:] = True
    header("3. TIME SPLIT")
    print(f"train (60%) : {idx[0]} .. {split_ts}   ({split_i} minutes)")
    print(f"eval  (40%) : {split_ts} .. {idx[-1]}   ({len(idx) - split_i} minutes)")
    print(f"storm events -> train: {int(((idx.get_indexer(events)) < split_i).sum())}, "
          f"eval: {int(((idx.get_indexer(events)) >= split_i).sum())}")

    # volatility regime of each segment (raw, not percentile) -- explains base-rate gaps
    ret30_abs = (np.log(b["close"]) - np.log(b["close"]).shift(STORM_WINDOW_MIN)).abs()
    for nm, seg in [("train", seg_train), ("eval ", seg_eval)]:
        v = ret30_abs.to_numpy()[seg & warm]
        v = v[~np.isnan(v)]
        print(f"  {nm}: median |30m ret| = {100 * np.median(v):.3f}%, "
              f"p95 = {100 * np.percentile(v, 95):.3f}%, "
              f"storm-minute share = {100 * (v >= STORM_THRESHOLD).mean():.2f}%")

    # ---------------- feature table ----------------
    header("4. FEATURE EVALUATION")
    feat_names = ["F1", "F2", "F3", "F4", "F5", "F6"]
    labels = {
        "F1": "F1 vol-rise-price-quiet",
        "F2": "F2 squeeze",
        "F3": "F3 squeeze-release arm",
        "F4": "F4 funding-pressure",
        "F5": "F5 bitFlyer absorption*",
        "F6": "F6 volume acceleration",
    }
    combo_cnt = (f["F1"].astype(int) + f["F2"].astype(int)
                 + f["F3"].astype(int) + f["F6"].astype(int)).to_numpy()

    results: dict[tuple[str, str, int], dict] = {}
    for seg_name, seg in [("TRAIN", seg_train), ("EVAL", seg_eval)]:
        for H in HORIZONS:
            fwd = event_flag_forward(idx, events, H)
            rows = []
            for c in feat_names:
                mask = seg & warm
                if c == "F5":
                    mask = mask & f["F5_avail"].to_numpy()
                m = eval_feature(f[c].to_numpy(), fwd, mask, idx, events, H)
                results[(seg_name, c, H)] = m
                rows.append((labels[c], m))
            # combination
            m = eval_feature(combo_cnt >= 2, fwd, seg & warm, idx, events, H)
            results[(seg_name, "COMBO>=2", H)] = m
            rows.append(("COMBO count(F1,F2,F3,F6)>=2", m))
            print_table(rows, H, seg_name)
    print("\n* F5 is measured only on minutes where bitFlyer data + its 14d reference window exist;")
    print("  its 'base' column is therefore the base rate on that sub-window, not the full segment.")

    # per-event audit on the eval segment (verifies the zero-lift cells are real)
    header("4b. EVAL-SEGMENT STORM EVENTS -- which features were ON in the prior 6h")
    print(f"{'storm start (UTC)':<28}{'|30m ret|':>10}   features ON within prior 2h / prior 6h")
    line()
    ret30 = (np.log(b["close"]) - np.log(b["close"]).shift(STORM_WINDOW_MIN)).to_numpy()
    for p in idx.get_indexer(events):
        if p < split_i or not warm[p]:
            continue
        on2, on6 = [], []
        for c in feat_names:
            sig = f[c].to_numpy()
            if sig[max(0, p - 120):p].any():
                on2.append(c)
            if sig[max(0, p - 360):p].any():
                on6.append(c)
        print(f"{str(idx[p]):<28}{100 * abs(ret30[p]):>9.2f}%   "
              f"{','.join(on2) if on2 else '(none)':<22} / {','.join(on6) if on6 else '(none)'}")

    # combination breakdown
    header("5. COMBINATION BREAKDOWN (EVAL segment)")
    for H in HORIZONS:
        fwd = event_flag_forward(idx, events, H)
        obs = seg_eval & warm & ~np.isnan(fwd)
        base = np.nanmean(fwd[obs])
        print(f"\nhorizon {H // 60}h   base = {100 * base:.2f}%")
        print(f"{'count ON':<12}{'minutes':>10}{'duty%':>9}{'P(storm)':>11}{'lift':>8}")
        line("-", 50)
        for k in range(5):
            sel = obs & (combo_cnt == k)
            if sel.sum() == 0:
                print(f"{k:<12}{0:>10}{0.0:>9.2f}{'-':>11}{'-':>8}")
                continue
            p = np.nanmean(fwd[sel])
            print(f"{k:<12}{int(sel.sum()):>10}{100 * sel.sum() / obs.sum():>9.2f}"
                  f"{100 * p:>10.2f}%{p / base:>8.2f}")

    # ---------------- effective sample size ----------------
    header("5b. EFFECTIVE SAMPLE SIZE ON THE EVAL SEGMENT (overlap check)")
    print("minute-level rows are massively autocorrelated; what matters is the number of")
    print("independent ON-episodes (contiguous runs of signal) and of storm events.\n")
    print(f"{'feature':<26}{'ON minutes':>12}{'ON episodes':>13}{'median run':>12}")
    line()
    for c in feat_names:
        mask = seg_eval & warm & (f["F5_avail"].to_numpy() if c == "F5" else True)
        s = f[c].to_numpy() & mask
        starts = np.flatnonzero(s & ~np.r_[False, s[:-1]])
        ends = np.flatnonzero(s & ~np.r_[s[1:], False])
        runs = ends - starts + 1
        med = f"{np.median(runs):.0f}m" if len(runs) else "-"
        print(f"{labels[c]:<26}{int(s.sum()):>12}{len(starts):>13}{med:>12}")
    n_ev_eval = int(((idx.get_indexer(events)) >= split_i).sum())
    se = np.sqrt(0.25 / n_ev_eval) if n_ev_eval else float("nan")
    print(f"\nstorm events on the eval segment: {n_ev_eval} "
          f"-> worst-case binomial SE on a recall estimate = +/-{se:.2f}")

    # ---------------- adoption rule ----------------
    header("6. ADOPTION RULE  (EVAL segment; lift>=2.0 at 2h OR 6h, recall>=0.10, >=30 events)")
    n_warm_ev = int(sum(1 for p in idx.get_indexer(events) if p >= split_i and warm[p]))
    if n_warm_ev < ADOPT_MIN_EVENTS:
        print(f"NOTE: the eval segment contains only {n_warm_ev} storm events, below the "
              f"pre-registered minimum of {ADOPT_MIN_EVENTS}.")
        print("      The event-count criterion therefore fails for every feature by construction;")
        print("      lift and recall are still reported below, but no feature can qualify.\n")
    print(f"{'feature':<26}{'lift2h':>8}{'lift6h':>8}{'rec2h':>8}{'rec6h':>8}{'events':>8}   verdict")
    line()
    for c in feat_names + ["COMBO>=2"]:
        m2, m6 = results[("EVAL", c, 120)], results[("EVAL", c, 360)]
        lift_ok = (m2["lift"] >= ADOPT_LIFT) or (m6["lift"] >= ADOPT_LIFT)
        # recall is judged on the horizon that carried the lift
        rec_ok = ((m2["lift"] >= ADOPT_LIFT and m2["recall"] >= ADOPT_RECALL)
                  or (m6["lift"] >= ADOPT_LIFT and m6["recall"] >= ADOPT_RECALL))
        ev_ok = m2["n_events"] >= ADOPT_MIN_EVENTS
        ok = lift_ok and rec_ok and ev_ok
        why = []
        if not lift_ok:
            why.append("lift<2.0")
        if lift_ok and not rec_ok:
            why.append("recall<0.10 on the qualifying horizon")
        if not ev_ok:
            why.append(f"only {m2['n_events']} events (<{ADOPT_MIN_EVENTS})")
        name = labels.get(c, c)
        print(f"{name:<26}{m2['lift']:>8.2f}{m6['lift']:>8.2f}{m2['recall']:>8.3f}"
              f"{m6['recall']:>8.3f}{m2['n_events']:>8}   "
              f"{'PASS' if ok else 'FAIL -- ' + ', '.join(why)}")

    # ---------------- hour of day ----------------
    header("7. STORM BASE RATE BY UTC HOUR-OF-DAY (informational)")
    hours = pd.Series(events.hour).value_counts().reindex(range(24), fill_value=0)
    minutes_per_hour = pd.Series(idx.hour).value_counts().reindex(range(24), fill_value=0)
    rate = hours / minutes_per_hour * 60.0  # events per hour-slot-day
    exp = len(events) / 24.0
    print(f"{'hour':>5}{'events':>8}{'share%':>9}{'vs uniform':>12}  bar")
    line()
    for h in range(24):
        share = 100.0 * hours[h] / max(len(events), 1)
        print(f"{h:>5}{hours[h]:>8}{share:>9.1f}{hours[h] / exp:>12.2f}  " + "#" * int(hours[h]))
    top = hours.sort_values(ascending=False)
    print(f"\nbusiest UTC hours: " + ", ".join(f"{h:02d}h({c})" for h, c in top.head(4).items()))
    print(f"quietest UTC hours: " + ", ".join(f"{h:02d}h({c})" for h, c in top.tail(4).items()))

    # ---------------- concentration caveat ----------------
    header("8. REGIME CONCENTRATION CHECK")
    days = pd.Series(1, index=events).resample("1D").sum()
    days_nonzero = days[days > 0].sort_values(ascending=False)
    tot = len(events)
    print(f"{tot} storm events fall on {len(days_nonzero)} distinct UTC days "
          f"out of {int(n_days)} days observed.")
    for k in [1, 3, 5, 10]:
        if len(days_nonzero) >= k:
            share = 100.0 * days_nonzero.head(k).sum() / tot
            print(f"  top {k:>2} storm days hold {int(days_nonzero.head(k).sum()):>3} events "
                  f"= {share:>5.1f}% of all events")
    print("\n  busiest days: " + ", ".join(
        f"{d.date()}({int(c)})" for d, c in days_nonzero.head(6).items()))
    ev_eval = events[idx.get_indexer(events) >= split_i]
    if len(ev_eval):
        de = pd.Series(1, index=ev_eval).resample("1D").sum()
        de = de[de > 0].sort_values(ascending=False)
        print(f"\n  EVAL segment: {len(ev_eval)} events on {len(de)} distinct days; "
              f"top 3 days = {100 * de.head(3).sum() / len(ev_eval):.1f}% of eval events")

    print()
    line("=")
    print("done.")
    line("=")


if __name__ == "__main__":
    sys.exit(main())
