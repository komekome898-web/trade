#!/usr/bin/env python3
"""
STORM PRECURSORS -- PHASE B: pre-registered options/derivatives/microstructure test.

Phase A (scripts/research_storm.py) is imported directly so that the storm
definition, the causal percentile helper and the metric code are *identical*,
not merely similar:

    storm minute : |rolling 30m log-return| >= 0.8%
    storm EVENT  : first storm minute after >= 2h with no storm minute
    horizons     : 2h / 6h
    metrics      : duty%, P(storm within H | ON), lift, recall, lead

Anchor: data/binance_BTCUSDT_1m_full.csv (210 days, extended in step 1).

Hypotheses G1..G7 were fixed by the lead before this script was written.
Nothing here is tuned; every threshold is transcribed from the brief.

Hourly sources (Deribit DVOL, OKX OI, OKX long/short ratio) are aligned to the
1m grid strictly causally: the bar labelled H covers [H, H+1) and is only
knowable from H+1 onwards, so a minute t uses the last COMPLETED hour's close.

Usage:  PYTHONPATH=src python scripts/research_storm_b.py
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import research_storm as A  # noqa: E402  (phase A: exact storm/metric machinery)

DATA = A.DATA

HORIZONS = A.HORIZONS                 # [120, 360]
PCT_1M = A.PCT_WINDOW_MIN             # 20160 = 14d on the 1m grid
H14D = 14 * 24                        # 336 hourly bars = 14d
H30D = 30 * 24                        # 720 hourly bars = 30d
MAX_STALE_MIN = 180                   # drop a minute if its hourly source is >3h old

ADOPT_LIFT = A.ADOPT_LIFT             # 2.0
ADOPT_RECALL = A.ADOPT_RECALL         # 0.10
ADOPT_MIN_EVENTS = A.ADOPT_MIN_EVENTS # 30

PRIMARY = (pd.Timestamp("2026-01-24", tz="UTC"), pd.Timestamp("2026-05-22", tz="UTC"))
SECONDARY_DAYS = 90

FEATS = ["G1", "G2", "G3", "G4", "G5", "G6", "G7"]
LABELS = {
    "G1": "G1 DVOL-low (complacency)",
    "G2": "G2 DVOL-rising 24h",
    "G3": "G3 clock 12:30-15:00 UTC",
    "G4": "G4 OI-build z>=+2",
    "G5": "G5 OI-build + quiet range",
    "G6": "G6 LS-ratio extreme",
    "G7": "G7 stealth-size",
}
FRESH_OK = {"G1": True, "G2": True, "G3": True, "G4": False, "G5": False, "G6": False, "G7": True}


def line(c: str = "-", n: int = 96) -> None:
    print(c * n)


def header(t: str) -> None:
    print()
    line("=")
    print(t)
    line("=")


# --------------------------------------------------------------------------- #
# loading
# --------------------------------------------------------------------------- #
def load_anchor() -> pd.DataFrame:
    p = os.path.join(DATA, "binance_BTCUSDT_1m_full.csv")
    df = pd.read_csv(p, parse_dates=["open_time"]).set_index("open_time").sort_index()
    df = df[~df.index.duplicated(keep="first")]
    full = pd.date_range(df.index[0], df.index[-1], freq="1min", tz="UTC")
    gaps = len(full) - len(df)
    df = df.reindex(full)
    for c in ["volume", "quote_volume", "n_trades", "taker_buy_base"]:
        df[c] = df[c].fillna(0.0)
    df[["open", "high", "low", "close"]] = df[["open", "high", "low", "close"]].ffill()
    df.index.name = "ts"
    span = (df.index[-1] - df.index[0]).total_seconds() / 86400.0
    print(f"binance 1m full : {df.index[0]} .. {df.index[-1]}")
    print(f"                  rows={len(df)}  span={span:.1f} days  filled_gaps={gaps}  "
          f"cols={list(df.columns)}")
    return df


def load_hourly(fname: str, label: str) -> pd.DataFrame:
    df = pd.read_csv(os.path.join(DATA, fname), parse_dates=["ts"]).set_index("ts").sort_index()
    df = df[~df.index.duplicated(keep="first")]
    span = (df.index[-1] - df.index[0]).total_seconds() / 86400.0
    exp = int(span * 24) + 1
    print(f"{label:<16}: {df.index[0]} .. {df.index[-1]}  rows={len(df)}  "
          f"span={span:.1f} days  missing_hours={max(0, exp - len(df))}")
    return df


def align_causal(s: pd.Series, idx: pd.DatetimeIndex, name: str) -> pd.Series:
    """Hourly bar labelled H is complete only at H+1h -> shift availability +1h,
    then forward-fill onto the minute grid. A minute whose newest source bar is
    older than MAX_STALE_MIN is left NaN (source gap, not carried forward)."""
    av = s.copy()
    av.index = av.index + pd.Timedelta(hours=1)
    av = av[~av.index.duplicated(keep="first")].sort_index()
    out = av.reindex(idx, method="ffill")
    # staleness in minutes, computed in int64 nanoseconds (tz-safe)
    av_ns = np.asarray(av.index.astype("int64"), dtype="float64")
    idx_ns = np.asarray(idx.astype("int64"), dtype="float64")
    last = pd.Series(av_ns, index=av.index).reindex(idx, method="ffill").to_numpy()
    stale = (idx_ns - last) / 6e10
    bad = ~np.isfinite(stale) | (stale > MAX_STALE_MIN)
    n_before = int(out.notna().sum())
    out[bad] = np.nan
    dropped = n_before - int(out.notna().sum())
    ok = np.isfinite(stale) & ~bad
    med = float(np.median(stale[ok])) if ok.any() else float("nan")
    print(f"  align {name:<22} minutes_with_value={int(out.notna().sum()):>7}  "
          f"median_staleness={med:.0f}m  max_kept={MAX_STALE_MIN}m  dropped_stale={dropped}")
    return out


# --------------------------------------------------------------------------- #
# features
# --------------------------------------------------------------------------- #
def build_features(b: pd.DataFrame, dvol: pd.DataFrame, oi: pd.DataFrame,
                   ls: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    idx = b.index
    f = pd.DataFrame(index=idx)
    av = pd.DataFrame(index=idx)

    # ---------------- price-side helpers (1m grid, phase-A conventions) -------
    high, low = b["high"], b["low"]

    def realized_range(win: int) -> pd.Series:
        return np.log(high.rolling(win, min_periods=win).max() / low.rolling(win, min_periods=win).min())

    print("\n[price-side percentiles on the 1m grid, 14d trailing window, shifted 1m]")
    rng_1h = realized_range(60)
    rng_6h = realized_range(360)
    pct_rng_1h = A.causal_pct_rank(rng_1h, PCT_1M)
    pct_rng_6h = A.causal_pct_rank(rng_6h, PCT_1M)
    print(f"  median pct_rng_1h={pct_rng_1h.median():.3f}  median pct_rng_6h={pct_rng_6h.median():.3f}"
          "   (should sit near 0.500)")

    # ---------------- G1 / G2  DVOL ------------------------------------------
    print("\n[DVOL -> 1m]")
    dv_close_h = dvol["close"]
    pct_dv_h = A.causal_pct_rank(dv_close_h, H30D)                 # 30d rolling, shifted 1 bar
    chg24_h = dv_close_h - dv_close_h.shift(24)                    # 24h change, vol points
    pct_chg_h = A.causal_pct_rank(chg24_h, H30D)                   # rank vs its own 30d window

    pct_dv = align_causal(pct_dv_h, idx, "DVOL pctile(30d)")
    pct_chg = align_causal(pct_chg_h, idx, "DVOL 24h-chg pctile")
    f["G1"] = pct_dv <= 0.10
    av["G1"] = pct_dv.notna()
    f["G2"] = pct_chg >= 0.90
    av["G2"] = pct_chg.notna()

    # ---------------- G3  clock window ---------------------------------------
    mod = idx.hour * 60 + idx.minute
    f["G3"] = pd.Series((mod >= 12 * 60 + 30) & (mod < 15 * 60), index=idx)
    av["G3"] = pd.Series(True, index=idx)

    # ---------------- G4 / G5  OKX open interest ------------------------------
    print("\n[OKX OI -> 1m]")
    oi_h = oi["oi"]
    d6 = oi_h - oi_h.shift(6)                                      # 6h OI change
    mu = d6.rolling(H14D, min_periods=H14D).mean().shift(1)        # 14d, causal
    sd = d6.rolling(H14D, min_periods=H14D).std().shift(1)
    z_h = (d6 - mu) / sd.replace(0.0, np.nan)
    z_oi = align_causal(z_h, idx, "OI 6h-change z(14d)")
    f["G4"] = z_oi >= 2.0
    av["G4"] = z_oi.notna()
    f["G5"] = f["G4"] & (pct_rng_6h < 0.30)
    av["G5"] = av["G4"] & pct_rng_6h.notna()

    # ---------------- G6  OKX long/short account ratio ------------------------
    print("\n[OKX long/short ratio -> 1m]")
    pct_ls_h = A.causal_pct_rank(ls["ratio"], H14D)
    pct_ls = align_causal(pct_ls_h, idx, "LS-ratio pctile(14d)")
    f["G6"] = (pct_ls >= 0.90) | (pct_ls <= 0.10)
    av["G6"] = pct_ls.notna()

    # ---------------- G7  stealth size ---------------------------------------
    vol_1h = b["volume"].rolling(60, min_periods=60).sum()
    trd_1h = b["n_trades"].rolling(60, min_periods=60).sum()
    avg_size = vol_1h / trd_1h.replace(0.0, np.nan)
    pct_size = A.causal_pct_rank(avg_size, PCT_1M)
    f["G7"] = (pct_size >= 0.90) & (pct_rng_1h < 0.30)
    av["G7"] = pct_size.notna() & pct_rng_1h.notna()
    print(f"\n[stealth size] median avg trade size = {avg_size.median():.5f} BTC/trade "
          f"(1h basis), median pctile = {pct_size.median():.3f}")

    for c in FEATS:
        f[c] = f[c].fillna(False).astype(bool)
        av[c] = av[c].fillna(False).astype(bool)
    f["_pct_rng_1h"] = pct_rng_1h
    f["_pct_rng_6h"] = pct_rng_6h
    return f, av


# --------------------------------------------------------------------------- #
# reporting helpers
# --------------------------------------------------------------------------- #
def episodes(sig: np.ndarray, mask: np.ndarray) -> tuple[int, int, float]:
    s = sig & mask
    if not s.any():
        return 0, 0, float("nan")
    starts = np.flatnonzero(s & ~np.r_[False, s[:-1]])
    ends = np.flatnonzero(s & ~np.r_[s[1:], False])
    runs = ends - starts + 1
    return int(s.sum()), len(starts), float(np.median(runs))


def print_table(rows: list[tuple[str, dict]], horizon: int, seg: str) -> None:
    print(f"\n[{seg}]  horizon = {horizon}m ({horizon // 60}h)")
    print(f"{'feature':<28}{'duty%':>8}{'P(storm|ON)':>13}{'base':>9}{'lift':>8}"
          f"{'recall':>9}{'caught/ev':>12}{'med_lead':>10}{'ON min':>9}{'episodes':>10}")
    line()
    for name, m in rows:
        p_on = "-" if not np.isfinite(m["p_on"]) else f"{m['p_on'] * 100:.2f}%"
        lift = "-" if not np.isfinite(m["lift"]) else f"{m['lift']:.2f}"
        lead = "-" if not np.isfinite(m["med_lead"]) else f"{m['med_lead']:.0f}m"
        base = "-" if not np.isfinite(m["base"]) else f"{m['base'] * 100:.2f}%"
        duty = "-" if not np.isfinite(m["duty"]) else f"{m['duty']:.2f}"
        print(f"{name:<28}{duty:>8}{p_on:>13}{base:>9}{lift:>8}{m['recall']:>9.3f}"
              f"{str(m['caught']) + '/' + str(m['n_events']):>12}{lead:>10}"
              f"{m['n_on']:>9}{m['_eps']:>10}")


def segment_summary(name: str, seg: np.ndarray, idx, events, b, tag: str) -> None:
    n = int(seg.sum())
    if n == 0:
        print(f"{name}: empty")
        return
    lo, hi = idx[np.argmax(seg)], idx[len(seg) - 1 - np.argmax(seg[::-1])]
    pos = idx.get_indexer(events)
    n_ev = int(sum(1 for p in pos if p >= 0 and seg[p]))
    days = (hi - lo).total_seconds() / 86400.0
    print(f"\n{name} [{tag}]")
    print(f"  span      : {lo} .. {hi}   ({days:.1f} days, {n} minutes)")
    print(f"  storm ev  : {n_ev}  ({n_ev / days * 7:.1f} per week)")
    for H in HORIZONS:
        fwd = A.event_flag_forward(idx, events, H)
        obs = seg & ~np.isnan(fwd)
        print(f"  base rate P(storm event begins within {H // 60}h | random minute) = "
              f"{100 * np.nanmean(fwd[obs]):.2f}%   (over {int(obs.sum())} minutes)")
    ret30 = (np.log(b["close"]) - np.log(b["close"]).shift(A.STORM_WINDOW_MIN)).abs().to_numpy()
    v = ret30[seg]
    v = v[~np.isnan(v)]
    print(f"  regime    : median |30m ret| = {100 * np.median(v):.3f}%, "
          f"p95 = {100 * np.percentile(v, 95):.3f}%, "
          f"storm-minute share = {100 * (v >= A.STORM_THRESHOLD).mean():.2f}%")


def crosstab(g3: np.ndarray, sig: np.ndarray, name: str, mask: np.ndarray,
             fwd: np.ndarray, H: int) -> None:
    obs = mask & ~np.isnan(fwd)
    base = float(np.nanmean(fwd[obs]))
    print(f"\n  horizon {H // 60}h   cell base (whole admissible mask) = {100 * base:.2f}%")
    print(f"  {'cell':<26}{'minutes':>10}{'share%':>9}{'P(storm)':>11}{'lift':>8}")
    line("-", 66)
    for lab, sel in [
        (f"G3 off & {name} off", obs & ~g3 & ~sig),
        (f"G3 off & {name} ON ", obs & ~g3 & sig),
        (f"G3 ON  & {name} off", obs & g3 & ~sig),
        (f"G3 ON  & {name} ON ", obs & g3 & sig),
    ]:
        n = int(sel.sum())
        if n == 0:
            print(f"  {lab:<26}{0:>10}{0.0:>9.2f}{'-':>11}{'-':>8}")
            continue
        p = float(np.nanmean(fwd[sel]))
        print(f"  {lab:<26}{n:>10}{100 * n / obs.sum():>9.2f}{100 * p:>10.2f}%{p / base:>8.2f}")


# --------------------------------------------------------------------------- #
def main() -> None:
    header("PHASE B  --  DATA LOAD  (step 1 confirmation)")
    b = load_anchor()
    dvol = load_hourly("deribit_dvol_1h.csv", "deribit DVOL 1h")
    oi = load_hourly("okx_btc_oi_1h.csv", "okx OI 1h")
    ls = load_hourly("okx_btc_lsratio_1h.csv", "okx LS-ratio 1h")
    idx = b.index

    header("1. STORM DEFINITION  (imported verbatim from scripts/research_storm.py)")
    storm_min, events = A.build_storms(b["close"])
    n_days = (idx[-1] - idx[0]).total_seconds() / 86400.0
    print(f"storm minute  : |{A.STORM_WINDOW_MIN}m log-return| >= {A.STORM_THRESHOLD * 100:.1f}%")
    print(f"dedup         : first storm minute after >= {A.STORM_DEDUP_MIN}m clean")
    print(f"storm minutes : {int(storm_min.sum())} of {len(idx)} ({100 * storm_min.mean():.2f}%)")
    print(f"storm EVENTS  : {len(events)} over {n_days:.1f} days ({len(events) / n_days * 7:.1f}/week)")
    print("\nstorm events per calendar week over the extended 210-day window:")
    for d, c in pd.Series(1, index=events).resample("7D").sum().items():
        print(f"  {d.date()}  {int(c):>3}  " + "#" * int(c))

    header("2. FEATURES  (pre-registered G1..G7, all causal)")
    f, av = build_features(b, dvol, oi, ls)
    print("\navailability and duty over every minute where the feature is defined:")
    print(f"{'feature':<28}{'defined from':<28}{'defined minutes':>17}{'duty%':>9}")
    line()
    for c in FEATS:
        a = av[c].to_numpy()
        first = idx[np.argmax(a)] if a.any() else None
        duty = 100.0 * f[c].to_numpy()[a].mean() if a.any() else float("nan")
        print(f"{LABELS[c]:<28}{str(first):<28}{int(a.sum()):>17}{duty:>9.2f}")

    header("2b. DUTY DIAGNOSTIC  (realized duty vs the duty the threshold nominally implies)")
    print("A trailing-percentile threshold only fires ~its nominal share of the time when the")
    print("underlying series is stationary. A persistently trending series sits at one end of")
    print("its own trailing window for months, so realized duty can be far off nominal.\n")
    nominal = {"G1": 10.0, "G2": 10.0, "G3": 150 / 14.40, "G4": float("nan"),
               "G5": float("nan"), "G6": 20.0, "G7": 10.0}
    print(f"{'feature':<28}{'nominal duty%':>15}{'realized duty%':>16}   comment")
    line()
    for c in FEATS:
        a = av[c].to_numpy()
        d = 100.0 * f[c].to_numpy()[a].mean() if a.any() else float("nan")
        nom = f"{nominal[c]:.1f}" if np.isfinite(nominal[c]) else "n/a (compound)"
        note = ""
        if np.isfinite(nominal[c]) and np.isfinite(d) and nominal[c] > 0:
            r = d / nominal[c]
            if r > 1.8:
                note = f"{r:.1f}x nominal -- underlying is TRENDING, not mean-reverting"
            elif r < 0.55:
                note = f"{r:.1f}x nominal"
        print(f"{LABELS[c]:<28}{nom:>15}{d:>16.2f}   {note}")
    print("\nDVOL monthly mean close (explains the G1 duty):")
    mm = dvol["close"].resample("MS").mean()
    print("  " + "  ".join(f"{p.strftime('%Y-%m')}={v:.1f}" for p, v in mm.items()))

    header("3. SEGMENTS")
    prim = (idx >= PRIMARY[0]) & (idx < PRIMARY[1])
    sec_lo = idx[-1] - pd.Timedelta(days=SECONDARY_DAYS)
    sec = idx >= sec_lo
    oi_seg = av["G4"].to_numpy() | av["G6"].to_numpy()
    segment_summary("PRIMARY (fresh, untouched by any prior study)", prim, idx, events, b,
                    "2026-01-24 -> 2026-05-22")
    segment_summary("SECONDARY (recent 90d, already seen in phase A)", sec, idx, events, b,
                    "reference only")
    segment_summary("OI/LS window (G4/G5/G6 only)", oi_seg, idx, events, b,
                    "INSUFFICIENT / informational")

    header("4. FEATURE EVALUATION  (mask = segment AND feature-defined minutes)")
    print("NOTE: 'base' is the base rate on that feature's own admissible mask, so lift is")
    print("      always measured against the population the feature could actually fire in.")
    results: dict[tuple[str, str, int], dict] = {}
    seg_defs = [("PRIMARY", prim, FEATS), ("SECONDARY-90d", sec, FEATS),
                ("OI/LS-30d", oi_seg, ["G4", "G5", "G6"])]
    for seg_name, seg, cols in seg_defs:
        for H in HORIZONS:
            fwd = A.event_flag_forward(idx, events, H)
            rows = []
            for c in cols:
                mask = seg & av[c].to_numpy()
                m = A.eval_feature(f[c].to_numpy(), fwd, mask, idx, events, H)
                n_on, eps, med_run = episodes(f[c].to_numpy(), mask)
                m["_eps"] = eps
                m["_med_run"] = med_run
                results[(seg_name, c, H)] = m
                rows.append((LABELS[c], m))
            print_table(rows, H, seg_name)

    header("5. INDEPENDENT ON-EPISODES  (phase A caveat #2: minutes are not independent)")
    for seg_name, seg, cols in seg_defs:
        print(f"\n[{seg_name}]")
        print(f"{'feature':<28}{'admissible min':>16}{'ON minutes':>12}{'ON episodes':>13}"
              f"{'median run':>12}{'events in mask':>16}")
        line()
        for c in cols:
            mask = seg & av[c].to_numpy()
            n_on, eps, med_run = episodes(f[c].to_numpy(), mask)
            m = results[(seg_name, c, 120)]
            med = "-" if not np.isfinite(med_run) else f"{med_run:.0f}m"
            print(f"{LABELS[c]:<28}{int(mask.sum()):>16}{n_on:>12}{eps:>13}{med:>12}"
                  f"{m['n_events']:>16}")

    header("6. ADOPTION RULE  (PRIMARY segment; lift>=2.0 at 2h OR 6h, recall>=0.10, >=30 events)")
    n_ev_prim = int(sum(1 for p in idx.get_indexer(events) if p >= 0 and prim[p]))
    print(f"storm events in the whole PRIMARY segment: {n_ev_prim}"
          f"  ->  binomial SE on a recall estimate ~ +/-{np.sqrt(0.25 / max(n_ev_prim, 1)):.3f}\n")
    print(f"{'feature':<28}{'lift2h':>8}{'lift6h':>8}{'rec2h':>8}{'rec6h':>8}{'events':>8}   verdict")
    line()
    qualified: list[str] = []
    for c in FEATS:
        if not FRESH_OK[c]:
            print(f"{LABELS[c]:<28}{'-':>8}{'-':>8}{'-':>8}{'-':>8}{'-':>8}   "
                  f"CANNOT QUALIFY -- no data on the fresh segment (30d source only)")
            continue
        m2, m6 = results[("PRIMARY", c, 120)], results[("PRIMARY", c, 360)]
        lift_ok = (m2["lift"] >= ADOPT_LIFT) or (m6["lift"] >= ADOPT_LIFT)
        rec_ok = ((m2["lift"] >= ADOPT_LIFT and m2["recall"] >= ADOPT_RECALL)
                  or (m6["lift"] >= ADOPT_LIFT and m6["recall"] >= ADOPT_RECALL))
        ev_ok = m2["n_events"] >= ADOPT_MIN_EVENTS
        ok = bool(lift_ok and rec_ok and ev_ok)
        why = []
        if not lift_ok:
            why.append("lift<2.0 at both horizons")
        if lift_ok and not rec_ok:
            why.append("recall<0.10 on the qualifying horizon")
        if not ev_ok:
            why.append(f"only {m2['n_events']} events in mask (<{ADOPT_MIN_EVENTS})")
        if ok:
            qualified.append(c)
        l2 = f"{m2['lift']:.2f}" if np.isfinite(m2["lift"]) else "-"
        l6 = f"{m6['lift']:.2f}" if np.isfinite(m6["lift"]) else "-"
        print(f"{LABELS[c]:<28}{l2:>8}{l6:>8}{m2['recall']:>8.3f}{m6['recall']:>8.3f}"
              f"{m2['n_events']:>8}   {'PASS' if ok else 'FAIL -- ' + ', '.join(why)}")
    print(f"\nqualifying features: {', '.join(qualified) if qualified else '(none)'}")

    header("7. OVERLAP WITH G3  (does the feature add anything beyond the clock?)")
    g3 = f["G3"].to_numpy()
    non_clock = [c for c in ["G1", "G2", "G7"] if np.isfinite(results[("PRIMARY", c, 120)]["lift"])]
    targets = [c for c in qualified if c != "G3"]
    if not targets:
        if qualified == ["G3"]:
            print("The only qualifying feature IS G3, so a G3 x qualifier cross-tab is degenerate.")
            print("The pre-registered question behind it -- 'does DVOL add anything beyond the")
            print("clock?' -- is still answered below by cross-tabbing G3 against each non-clock")
            print("feature on the PRIMARY segment. These are descriptive: none of them qualified.")
        else:
            print("No non-clock feature qualified; the cross-tabs below are descriptive only.")
        targets = non_clock
    for c in targets:
        if c == "G3":
            continue
        mask = prim & av[c].to_numpy()
        sig = f[c].to_numpy()
        both = int((mask & g3 & sig).sum())
        on_c = int((mask & sig).sum())
        on_g3 = int((mask & g3).sum())
        jac = both / max(1, on_c + on_g3 - both)
        print(f"\n{LABELS[c]}  x  {LABELS['G3']}   [PRIMARY, admissible minutes only]")
        print(f"  ON({c})={on_c}  ON(G3)={on_g3}  both={both}  "
              f"P(G3|{c} ON)={both / max(1, on_c):.3f}  Jaccard={jac:.3f}")
        for H in HORIZONS:
            crosstab(g3, sig, c, mask, A.event_flag_forward(idx, events, H), H)

    header("7b. STABILITY OF THE QUALIFYING FEATURE(S) WITHIN THE PRIMARY SEGMENT")
    print("Not a new hypothesis -- just the same metric recomputed month by month, so a lift")
    print("driven by one cluster of storm days is visible as such.")
    for c in qualified:
        print(f"\n{LABELS[c]}")
        print(f"{'month':<12}{'minutes':>10}{'events':>8}{'duty%':>8}{'base2h':>9}"
              f"{'P|ON 2h':>10}{'lift2h':>8}{'lift6h':>8}")
        line("-", 76)
        months = pd.PeriodIndex(idx, freq="M")
        for per in sorted(set(months[prim])):
            sub = prim & np.asarray(months == per) & av[c].to_numpy()
            if sub.sum() < 1440:
                continue
            m2 = A.eval_feature(f[c].to_numpy(), A.event_flag_forward(idx, events, 120),
                                sub, idx, events, 120)
            m6 = A.eval_feature(f[c].to_numpy(), A.event_flag_forward(idx, events, 360),
                                sub, idx, events, 360)
            l2 = f"{m2['lift']:.2f}" if np.isfinite(m2["lift"]) else "-"
            l6 = f"{m6['lift']:.2f}" if np.isfinite(m6["lift"]) else "-"
            p2 = f"{100 * m2['p_on']:.2f}%" if np.isfinite(m2["p_on"]) else "-"
            print(f"{str(per):<12}{int(sub.sum()):>10}{m2['n_events']:>8}{m2['duty']:>8.2f}"
                  f"{100 * m2['base']:>8.2f}%{p2:>10}{l2:>8}{l6:>8}")

    header("8. G4 / G5 / G6  --  INSUFFICIENT, INFORMATIONAL ONLY")
    print("OKX rubik endpoints return a fixed ~30-day window and cannot be paged back, so")
    print("these three features do not exist on the fresh PRIMARY segment at all. After the")
    print("14-day rolling reference window they leave only the tail shown in section 3/4.")
    print("They CANNOT qualify this round under the pre-registered adoption rule.")
    for c in ["G4", "G5", "G6"]:
        m2, m6 = results[("OI/LS-30d", c, 120)], results[("OI/LS-30d", c, 360)]
        l2 = f"{m2['lift']:.2f}" if np.isfinite(m2["lift"]) else "-"
        l6 = f"{m6['lift']:.2f}" if np.isfinite(m6["lift"]) else "-"
        print(f"  {LABELS[c]:<28} lift2h={l2:>6}  lift6h={l6:>6}  "
              f"recall2h={m2['recall']:.3f}  caught={m2['caught']}/{m2['n_events']}  "
              f"ON_episodes={m2['_eps']}")

    header("9. CAVEATS")
    print("1. Regime coverage: the fresh PRIMARY window is one contiguous ~118-day stretch of")
    print("   2026 price action; sections 1 and 3 print its event count, weekly event bars and")
    print("   |30m ret| distribution so the reader can judge how much of it is one regime.")
    print("2. Warm-up eats the head of the PRIMARY segment: the 30d DVOL percentile window")
    print("   (G1/G2) and the 14d 1m percentile windows (G5/G7) are only defined some way")
    print("   into the segment. Section 2 prints the first defined minute per feature and")
    print("   section 5 the admissible-minute count; lift is always computed against the base")
    print("   rate of exactly those minutes.")
    print("3. Forward-fill: hourly DVOL/OI/LS values are held flat for up to 59 minutes (bar")
    print("   labelled H used only from H+1h). Consecutive minutes inside one hour therefore")
    print("   carry an identical value -- ON-runs are hour-quantised and the effective sample")
    print("   is the episode count in section 5, not the minute count.")
    print("4. Episode counts: a feature with few independent ON-episodes can post a large lift")
    print("   from one or two clusters. Read duty%, episodes and caught/events together.")
    print("5. Storm events cluster on a handful of days (phase A caveat), so recall estimates")
    print("   carry roughly the binomial SE printed in section 6 -- at best.")
    print("6. Threshold semantics (section 2b): G1 fires on ~35-40% of minutes, not ~10%, because")
    print("   DVOL fell from ~54 (Mar) to ~35 (Aug) and a falling series lives at the bottom of")
    print("   its own trailing 30d window. G1 as pre-registered is therefore closer to a")
    print("   'DVOL is in a downtrend' flag than to a 1-in-10 complacency flag; same mechanism")
    print("   inflates G6. This is reported, not corrected -- the definitions were pre-registered.")
    print("7. G3 was promoted from a phase A informational finding measured on the recent 90")
    print("   days; the PRIMARY segment never contributed to that finding, so its PRIMARY")
    print("   numbers are an out-of-sample read, while its SECONDARY numbers are not.")

    print()
    line("=")
    print("done.")
    line("=")


if __name__ == "__main__":
    sys.exit(main())
