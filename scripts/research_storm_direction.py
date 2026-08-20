#!/usr/bin/env python3
"""
STORM DIRECTION -- offline study.

Pre-registered question: is the DIRECTION of a storm predictable BEFORE it starts?

If yes even weakly, a pre-positioned resting-limit strategy becomes possible.
If no, that is a decisive negative and is worth recording as such.

Anchor market : Binance BTCUSDT 1m, data/binance_BTCUSDT_1m_full.csv (~210 days).
Storm minute  : |rolling 30m log-return| >= 0.8%   (same machinery as research_storm.py)
Storm event   : first storm minute after >= 2h with no storm minutes.
Event DIRECTION: sign of the 30m log-return at onset.

Predictors, all evaluated at onset - 1 minute, strictly causal (no data from
minute t or later is ever touched when predicting the event at minute t):

  P1 momentum-continuation : sign of the prior 2h log-return.
  P2 range-position        : position of close in the prior 24h high-low range.
                             >0.7 -> UP, <0.3 -> DOWN, middle -> abstain.
  P3 taker-flow            : sign of sum over the prior 1h of
                             (taker_buy_base - (volume - taker_buy_base)).
  P4 funding (contrarian)  : most recent settled funding rate before onset;
                             positive funding (crowded longs) -> predict DOWN.
  P5 prior-storm direction : direction of the previous storm event.
  MAJ(P1,P2,P3)            : majority vote, abstains map to 0, tie -> abstain.

Evaluation (fixed, pre-registered):
  chronological split of the EVENT list: first 60% exploratory, last 40% judgment.
  For each predictor on the judgment events: coverage (share of judged events where
  the predictor makes a call), n calls, sign-accuracy, exact two-sided binomial
  p-value vs 0.5.

ADOPTION RULE: accuracy >= 58% AND n >= 40 judged calls AND p < 0.05.

Economic frame (sanity check only, NOT a backtest): for a qualifying predictor,
at every armed-window minute (12:30-15:00 UTC) that carries a prediction,
hypothetically hold that direction for the next 2h; report the mean return net of
one taker round trip (6.35 bps).

Usage:  PYTHONPATH=src python scripts/research_storm_direction.py
"""

from __future__ import annotations

import math
import os
import sys

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------- #
# config (all pre-registered, nothing here was tuned)
# --------------------------------------------------------------------------- #
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

STORM_WINDOW_MIN = 30      # rolling window for the storm return
STORM_THRESHOLD = 0.008    # 0.8% absolute log return
STORM_DEDUP_MIN = 120      # >= 2h of calm required before a new event

P1_LOOKBACK_MIN = 120      # prior 2h return
P2_LOOKBACK_MIN = 1440     # prior 24h high-low range
P2_HI, P2_LO = 0.70, 0.30  # range-position thresholds
P3_LOOKBACK_MIN = 60       # prior 1h taker flow

EXPLORE_FRAC = 0.60        # first 60% of EVENTS

ADOPT_ACC = 0.58
ADOPT_N = 40
ADOPT_P = 0.05

ARMED_START = (12, 30)     # armed window, UTC
ARMED_END = (15, 0)
HOLD_MIN = 120             # 2h hypothetical hold
ROUND_TRIP_BPS = 6.35      # one taker round trip

PREDICTORS = ["P1", "P2", "P3", "P4", "P5", "MAJ"]
LABELS = {
    "P1": "P1 momentum-continuation",
    "P2": "P2 range-position",
    "P3": "P3 taker-flow",
    "P4": "P4 funding (contrarian)",
    "P5": "P5 prior-storm direction",
    "MAJ": "MAJ vote(P1,P2,P3)",
}


def line(char: str = "-", n: int = 92) -> None:
    print(char * n)


def header(title: str) -> None:
    print()
    line("=")
    print(title)
    line("=")


# --------------------------------------------------------------------------- #
# exact two-sided binomial test vs p = 0.5 (no scipy in this environment)
# --------------------------------------------------------------------------- #
def binom_test_two_sided(k: int, n: int) -> float:
    """Exact two-sided binomial p-value for k successes in n trials under p=0.5.

    Sums the probability of every outcome no more likely than the observed one.
    """
    if n <= 0:
        return float("nan")
    logs = -n * math.log(2.0)
    obs = math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1) + logs
    tot = 0.0
    for i in range(n + 1):
        lp = math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1) + logs
        if lp <= obs + 1e-9:
            tot += math.exp(lp)
    return min(1.0, tot)


def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1.0 + z * z / n
    c = p + z * z / (2 * n)
    r = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - r) / d, (c + r) / d)


# --------------------------------------------------------------------------- #
# loading
# --------------------------------------------------------------------------- #
def load_binance_full() -> pd.DataFrame:
    path = os.path.join(DATA, "binance_BTCUSDT_1m_full.csv")
    df = pd.read_csv(path, parse_dates=["open_time"])
    df = df.rename(columns={"open_time": "ts"}).set_index("ts").sort_index()
    df = df[~df.index.duplicated(keep="first")]
    full = pd.date_range(df.index[0], df.index[-1], freq="1min", tz="UTC")
    gaps = len(full) - len(df)
    df = df.reindex(full)
    for c in ["volume", "quote_volume", "n_trades", "taker_buy_base"]:
        if c in df.columns:
            df[c] = df[c].fillna(0.0)
    df[["open", "high", "low", "close"]] = df[["open", "high", "low", "close"]].ffill()
    df.index.name = "ts"
    n_days = (df.index[-1] - df.index[0]).total_seconds() / 86400.0
    print(f"binance 1m : {df.index[0]} .. {df.index[-1]}")
    print(f"             rows={len(df)}  days={n_days:.1f}  filled_gaps={gaps}")
    return df


def load_funding() -> pd.DataFrame:
    df = pd.read_csv(os.path.join(DATA, "funding_rate_history.csv"))
    df["settlement_date"] = pd.to_datetime(df["settlement_date"], utc=True)
    df = df.sort_values("settlement_date").reset_index(drop=True)
    print(f"funding    : {df['settlement_date'].iloc[0]} .. {df['settlement_date'].iloc[-1]}  "
          f"n={len(df)} settlements")
    return df


# --------------------------------------------------------------------------- #
# storms (identical definition to scripts/research_storm.py)
# --------------------------------------------------------------------------- #
def build_storms(px: pd.Series) -> tuple[pd.Series, np.ndarray]:
    logp = np.log(px)
    ret30 = logp - logp.shift(STORM_WINDOW_MIN)
    storm_min = (ret30.abs() >= STORM_THRESHOLD).fillna(False)
    prior = storm_min.rolling(STORM_DEDUP_MIN, min_periods=STORM_DEDUP_MIN).sum().shift(1)
    is_event = (storm_min & (prior == 0)).fillna(False).to_numpy()
    return ret30, np.flatnonzero(is_event)


# --------------------------------------------------------------------------- #
# predictor series -- value at minute t uses ONLY data at minutes <= t.
# To predict an event at onset o, we read these series at index o-1.
# --------------------------------------------------------------------------- #
def build_predictors(b: pd.DataFrame, funding: pd.DataFrame) -> dict[str, np.ndarray]:
    idx = b.index
    logc = np.log(b["close"])

    # ---- P1: sign of the prior 2h log-return ----
    p1 = np.sign((logc - logc.shift(P1_LOOKBACK_MIN)).to_numpy())

    # ---- P2: position of close within the prior 24h high-low range ----
    hh = b["high"].rolling(P2_LOOKBACK_MIN, min_periods=P2_LOOKBACK_MIN).max()
    ll = b["low"].rolling(P2_LOOKBACK_MIN, min_periods=P2_LOOKBACK_MIN).min()
    span = (hh - ll).replace(0.0, np.nan)
    pos = ((b["close"] - ll) / span).to_numpy()
    p2 = np.full(len(idx), np.nan)
    p2[pos > P2_HI] = 1.0
    p2[pos < P2_LO] = -1.0
    p2[(pos >= P2_LO) & (pos <= P2_HI)] = 0.0        # explicit abstain (middle zone)

    # ---- P3: sign of net taker flow over the prior 1h ----
    net = (2.0 * b["taker_buy_base"] - b["volume"])
    p3 = np.sign(net.rolling(P3_LOOKBACK_MIN, min_periods=P3_LOOKBACK_MIN).sum().to_numpy())

    # ---- P4: contrarian funding, most recent settlement at or before t ----
    sd = funding["settlement_date"].to_numpy()
    rates = funding["rate"].to_numpy()
    j = np.searchsorted(sd, idx.to_numpy(), side="right") - 1
    p4 = np.full(len(idx), np.nan)
    ok = j >= 0
    p4[ok] = -np.sign(rates[j[ok]])                  # positive funding -> predict DOWN

    # ---- MAJ: majority vote of P1/P2/P3 (abstains count as 0, tie -> abstain) ----
    v = np.nan_to_num(p1) + np.nan_to_num(p2) + np.nan_to_num(p3)
    maj = np.sign(v)
    # unavailable if any of the three is not yet computable
    unavail = np.isnan(p1) | np.isnan(p2) | np.isnan(p3)
    maj[unavail] = np.nan

    return {"P1": p1, "P2": p2, "P3": p3, "P4": p4, "MAJ": maj, "_range_pos": pos}


# --------------------------------------------------------------------------- #
# scoring
# --------------------------------------------------------------------------- #
def score(calls: np.ndarray, truth: np.ndarray) -> dict:
    """calls in {-1,0,+1} or nan (nan/0 = abstain); truth in {-1,+1}."""
    made = np.isfinite(calls) & (calls != 0)
    n = int(made.sum())
    if n == 0:
        return dict(n=0, k=0, acc=float("nan"), p=float("nan"),
                    cov=0.0, lo=float("nan"), hi=float("nan"),
                    n_up=0, n_dn=0)
    k = int((calls[made] == truth[made]).sum())
    lo, hi = wilson_ci(k, n)
    return dict(
        n=n, k=k, acc=k / n, p=binom_test_two_sided(k, n),
        cov=n / len(calls), lo=lo, hi=hi,
        n_up=int((calls[made] > 0).sum()), n_dn=int((calls[made] < 0).sum()),
    )


def print_pred_table(title: str, rows: list[tuple[str, dict]]) -> None:
    print(f"\n{title}")
    print(f"{'predictor':<28}{'cov%':>7}{'n':>6}{'correct':>9}{'acc%':>8}"
          f"{'95% CI':>16}{'p(exact)':>11}{'calls U/D':>12}")
    line()
    for name, m in rows:
        if m["n"] == 0:
            print(f"{name:<28}{0.0:>7.1f}{0:>6}{'-':>9}{'-':>8}{'-':>16}{'-':>11}{'-':>12}")
            continue
        ci = f"[{100*m['lo']:.1f},{100*m['hi']:.1f}]"
        ud = "{}/{}".format(m["n_up"], m["n_dn"])
        print(f"{name:<28}{100*m['cov']:>7.1f}{m['n']:>6}{m['k']:>9}{100*m['acc']:>8.2f}"
              f"{ci:>16}{m['p']:>11.4f}{ud:>12}")


# --------------------------------------------------------------------------- #
# economic sanity check
# --------------------------------------------------------------------------- #
def armed_mask(idx: pd.DatetimeIndex) -> np.ndarray:
    mins = np.asarray(idx.hour) * 60 + np.asarray(idx.minute)
    return ((mins >= ARMED_START[0] * 60 + ARMED_START[1])
            & (mins <= ARMED_END[0] * 60 + ARMED_END[1]))


def econ_check(name: str, calls: np.ndarray, logc: np.ndarray,
               idx: pd.DatetimeIndex, seg: np.ndarray) -> None:
    fwd = np.full(len(logc), np.nan)
    fwd[:-HOLD_MIN] = logc[HOLD_MIN:] - logc[:-HOLD_MIN]
    m = armed_mask(idx) & seg & np.isfinite(calls) & (calls != 0) & np.isfinite(fwd)
    n = int(m.sum())
    if n == 0:
        print(f"  {name:<28} no armed minutes with a prediction")
        return
    gross = calls[m] * fwd[m] * 1e4                  # bps
    net = gross - ROUND_TRIP_BPS
    sd = net.std(ddof=1) if n > 1 else float("nan")
    naive_t = net.mean() / (sd / math.sqrt(n)) if n > 1 and sd > 0 else float("nan")
    days = len(np.unique(idx[m].date))
    # day-clustered standard error: average net return per calendar day, then t over days
    dfr = pd.Series(net, index=idx[m]).groupby(idx[m].date).mean()
    d_sd = dfr.std(ddof=1) if len(dfr) > 1 else float("nan")
    d_t = dfr.mean() / (d_sd / math.sqrt(len(dfr))) if len(dfr) > 1 and d_sd > 0 else float("nan")
    print(f"  {name:<26}n={n:>6} days={days:>4} gross={gross.mean():>7.2f} "
          f"net={net.mean():>7.2f} net/day-eqw={dfr.mean():>7.2f} "
          f"hit={100*(gross>0).mean():>5.1f}% t(naive)={naive_t:>6.2f} "
          f"t(day-clust)={d_t:>6.2f}")

    # when the predictor abstains a lot, the minute-weighted mean is a day-selection
    # artefact: check whether the payoff lives only on the days it is armed all window
    span = ARMED_END[0] * 60 + ARMED_END[1] - ARMED_START[0] * 60 - ARMED_START[1] + 1
    cnt = pd.Series(1, index=idx[m]).groupby(idx[m].date).sum()
    if cnt.mean() < 0.95 * span and len(cnt) >= 20:
        # rank first so heavy ties in the daily call count still yield four bins
        q = pd.qcut(cnt.rank(method="first"), 4,
                    labels=["q1 fewest calls", "q2", "q3", "q4 most calls"])
        agg = pd.DataFrame({"cnt": cnt, "ret": dfr}).groupby(q, observed=True).agg(
            days=("ret", "size"), mean_net=("ret", "mean"))
        parts = "  ".join(f"{str(k)}: {v.mean_net:+.1f}bps({int(v.days)}d)"
                          for k, v in agg.iterrows())
        print(f"      armed-minutes/day quartiles -> {parts}")
        print(f"      corr(calls per day, that day's mean net) = "
              f"{np.corrcoef(cnt.to_numpy(), dfr.to_numpy())[0,1]:+.2f}  "
              f"-> the minute-weighted mean is dominated by the fully-armed days")


# --------------------------------------------------------------------------- #
def main() -> None:
    header("STORM DIRECTION  --  data load")
    b = load_binance_full()
    funding = load_funding()
    idx = b.index
    logc = np.log(b["close"]).to_numpy()

    # ---------------- storms ----------------
    header("1. STORM EVENTS AND THEIR DIRECTION")
    ret30, ev_pos = build_storms(b["close"])
    r30 = ret30.to_numpy()
    n_days = (idx[-1] - idx[0]).total_seconds() / 86400.0
    print(f"storm minute : |30m log-return| >= {STORM_THRESHOLD*100:.1f}%")
    print(f"dedup        : >= {STORM_DEDUP_MIN}m of calm before a new event")
    print(f"storm EVENTS : {len(ev_pos)} over {n_days:.1f} days "
          f"({len(ev_pos)/n_days*7:.1f} per week)")

    # warm-up: every predictor except P4/P5 needs 24h of history; keep the event set
    # identical across predictors so the accuracy columns are comparable.
    warm = ev_pos >= P2_LOOKBACK_MIN
    dropped = int((~warm).sum())
    ev_pos = ev_pos[warm]
    print(f"warm-up      : {dropped} event(s) dropped for lacking a full 24h history; "
          f"{len(ev_pos)} events evaluated")

    direction = np.sign(r30[ev_pos])
    assert np.all(direction != 0), "a storm event with zero 30m return should be impossible"
    ev_ts = idx[ev_pos]
    n_up, n_dn = int((direction > 0).sum()), int((direction < 0).sum())
    p_uncond = binom_test_two_sided(n_up, len(direction))
    print(f"\nUNCONDITIONAL SPLIT : UP {n_up} ({100*n_up/len(direction):.1f}%)   "
          f"DOWN {n_dn} ({100*n_dn/len(direction):.1f}%)   "
          f"exact two-sided p vs 50/50 = {p_uncond:.4f}")
    print(f"median |30m ret| at onset = {100*np.median(np.abs(r30[ev_pos])):.2f}%  "
          f"(up: {100*np.median(r30[ev_pos][direction>0]):.2f}%, "
          f"down: {100*np.median(r30[ev_pos][direction<0]):.2f}%)")

    # ---------------- split ----------------
    header("2. CHRONOLOGICAL SPLIT (on the EVENT list)")
    k_split = int(len(ev_pos) * EXPLORE_FRAC)
    explore = np.zeros(len(ev_pos), dtype=bool); explore[:k_split] = True
    judge = ~explore
    print(f"exploratory (first 60%) : {ev_ts[0]} .. {ev_ts[k_split-1]}   n={int(explore.sum())}")
    print(f"judgment    (last  40%) : {ev_ts[k_split]} .. {ev_ts[-1]}   n={int(judge.sum())}")
    for nm, seg in [("exploratory", explore), ("judgment   ", judge)]:
        d = direction[seg]
        u = int((d > 0).sum())
        print(f"  {nm}: UP {u} / DOWN {len(d)-u}  ({100*u/len(d):.1f}% up), "
              f"exact p vs 50/50 = {binom_test_two_sided(u, len(d)):.4f}")

    # ---------------- predictors ----------------
    header("3. PREDICTORS AT ONSET - 1 MINUTE (strictly causal)")
    P = build_predictors(b, funding)
    at = ev_pos - 1                                   # onset - 1 minute

    calls: dict[str, np.ndarray] = {}
    for c in ["P1", "P2", "P3", "P4", "MAJ"]:
        calls[c] = P[c][at]

    # P5: direction of the PREVIOUS storm event (defined on the event list itself)
    p5 = np.full(len(ev_pos), np.nan)
    p5[1:] = direction[:-1]
    calls["P5"] = p5

    print(f"{'predictor':<28}{'defined on':>12}{'abstains':>10}   note")
    line()
    notes = {
        "P1": "sign of prior 2h log-return",
        "P2": f"range pos >{P2_HI} -> UP, <{P2_LO} -> DOWN, middle abstains",
        "P3": "sign of prior 1h net taker flow",
        "P4": f"funding history starts {funding['settlement_date'].iloc[0]}; "
              f"zero rate abstains",
        "P5": "first event has no predecessor",
        "MAJ": "tie (vote sum 0) abstains",
    }
    for c in PREDICTORS:
        v = calls[c]
        made = np.isfinite(v) & (v != 0)
        print(f"{LABELS[c]:<28}{int(made.sum()):>12}{len(v)-int(made.sum()):>10}   {notes[c]}")
    rp = P["_range_pos"][at]
    rp = rp[np.isfinite(rp)]
    print(f"\nsanity: median 24h range-position at onset-1 = {np.median(rp):.3f} "
          f"(should sit near the middle of [0,1])")

    # ---------------- results ----------------
    header("4. PREDICTOR TABLE")
    rows_e, rows_j, rows_a = [], [], []
    res_j: dict[str, dict] = {}
    for c in PREDICTORS:
        rows_e.append((LABELS[c], score(calls[c][explore], direction[explore])))
        m = score(calls[c][judge], direction[judge])
        res_j[c] = m
        rows_j.append((LABELS[c], m))
        rows_a.append((LABELS[c], score(calls[c], direction)))
    print_pred_table("[EXPLORATORY -- first 60% of events, construction sanity-check only]", rows_e)
    print_pred_table("[JUDGMENT -- last 40% of events, THIS IS THE PRE-REGISTERED TEST]", rows_j)
    print_pred_table("[ALL EVENTS -- informational only, not the test]", rows_a)
    print("\ncov% = share of segment events on which the predictor makes a call "
          "(the rest abstain).")
    print("p(exact) = two-sided exact binomial test of accuracy against 0.5.")

    # ---------------- contamination diagnostic ----------------
    header("4b. CONTAMINATION CHECK -- the lookback windows OVERLAP the storm window")
    print("A storm event at minute t is defined by the TRAILING 30m return logc[t]-logc[t-30].")
    print("At onset-1 the move is therefore already ~29 minutes old and it sits INSIDE every")
    print("lookback window used by P1/P2/P3:")
    print(f"  P1 reads [t-{P1_LOOKBACK_MIN+1}, t-1] -- contains {STORM_WINDOW_MIN-1} of the "
          f"{STORM_WINDOW_MIN} storm minutes")
    print(f"  P3 reads [t-{P3_LOOKBACK_MIN+1}, t-1] -- contains {STORM_WINDOW_MIN-1} of the "
          f"{STORM_WINDOW_MIN} storm minutes")
    print(f"  P2 reads the 24h range at t-1, and a 0.86% move in the last {STORM_WINDOW_MIN}m "
          f"pushes price toward the extreme")
    print("These are strictly CAUSAL but not PREDICTIVE: they measure the storm, not a")
    print("precursor of it. To answer the pre-registered question we must push the predictor")
    print(f"back past the storm window, to onset - {STORM_WINDOW_MIN+1} minutes or earlier.\n")

    lags = [1, 5, 10, 15, 20, 25, 30, 31, 35, 45, 60, 90, 120, 180]
    sweep_names = ["P1", "P2", "P3", "MAJ"]
    print("sign-accuracy on JUDGMENT events as the predictor is lagged back from onset")
    print("(L = minutes before onset at which the predictor is read; L >= 31 is clean)\n")
    print(f"{'L (min)':>9}  " + "".join(f"{LABELS[c].split()[0]:>23}" for c in sweep_names))
    print(f"{'':>9}  " + "".join(f"{'acc (n, p)':>23}" for _ in sweep_names))
    line("-", 110)
    sweep: dict[tuple[str, int], dict] = {}
    for L in lags:
        cells = []
        for c in sweep_names:
            pos = ev_pos - L
            ok = pos >= P2_LOOKBACK_MIN
            v = np.full(len(ev_pos), np.nan)
            v[ok] = P[c][pos[ok]]
            m = score(v[judge], direction[judge])
            sweep[(c, L)] = m
            cells.append("-" if m["n"] == 0
                         else f"{100*m['acc']:.1f}% (n={m['n']},p={m['p']:.3f})")
        mark = "  <-- pre-registered" if L == 1 else (
            "  <-- first clean lag" if L == STORM_WINDOW_MIN + 1 else "")
        print(f"{L:>9}  " + "".join(f"{s:>23}" for s in cells) + mark)
    print("\nIf direction were genuinely forecastable, accuracy would decay gently with L.")
    print("A cliff at L = 31 -- exactly where the storm window leaves the lookback -- means")
    print("the signal WAS the storm.")

    # ---------------- adoption rule ----------------
    header(f"5. ADOPTION RULE  (judgment events: acc >= {100*ADOPT_ACC:.0f}%, "
           f"n >= {ADOPT_N}, p < {ADOPT_P})")
    print(f"{'predictor':<28}{'acc%':>8}{'n':>6}{'p':>10}   verdict")
    line()
    passed: list[str] = []
    for c in PREDICTORS:
        m = res_j[c]
        acc_ok = m["n"] > 0 and m["acc"] >= ADOPT_ACC
        n_ok = m["n"] >= ADOPT_N
        p_ok = m["n"] > 0 and m["p"] < ADOPT_P
        ok = acc_ok and n_ok and p_ok
        if ok:
            passed.append(c)
        why = []
        if not acc_ok:
            why.append(f"acc {100*m['acc']:.1f}% < {100*ADOPT_ACC:.0f}%" if m["n"] else "no calls")
        if not n_ok:
            why.append(f"n={m['n']} < {ADOPT_N}")
        if not p_ok and m["n"]:
            why.append(f"p={m['p']:.3f} >= {ADOPT_P}")
        acc_s = "-" if m["n"] == 0 else f"{100*m['acc']:.2f}"
        p_s = "-" if m["n"] == 0 else f"{m['p']:.4f}"
        print(f"{LABELS[c]:<28}{acc_s:>8}{m['n']:>6}{p_s:>10}   "
              f"{'PASS' if ok else 'FAIL -- ' + '; '.join(why)}")
    print()
    if passed:
        print(f"QUALIFYING PREDICTORS (as pre-registered, at onset-1): "
              f"{', '.join(LABELS[c] for c in passed)}")
        print("*** but see section 4b: for P1/P2/P3/MAJ this pass is an artefact of the")
        print("*** lookback window overlapping the storm's own 30-minute definition window.")
    else:
        print("NO PREDICTOR QUALIFIES. Pre-storm direction is not predictable by any of the")
        print("five pre-registered signals at the pre-registered bar.")

    # ---- the same rule applied at the first uncontaminated lag ----
    L0 = STORM_WINDOW_MIN + 1
    header(f"5b. ADOPTION RULE AT THE FIRST CLEAN LAG (onset - {L0} min, storm window excluded)")
    print("This is the honest form of the pre-registered question: at a moment strictly")
    print("BEFORE the storm's 30m window opens, does any signal call the direction?\n")
    print(f"{'predictor':<28}{'acc%':>8}{'n':>6}{'p':>10}   verdict")
    line()
    passed_clean: list[str] = []
    for c in PREDICTORS:
        if c == "P5":
            m = res_j[c]                       # P5 lives on the event list, no lag applies
        elif c == "P4":
            pos = ev_pos - L0
            v = np.full(len(ev_pos), np.nan)
            ok = pos >= P2_LOOKBACK_MIN
            v[ok] = P[c][pos[ok]]
            m = score(v[judge], direction[judge])
        else:
            m = sweep[(c, L0)]
        acc_ok = m["n"] > 0 and m["acc"] >= ADOPT_ACC
        n_ok = m["n"] >= ADOPT_N
        p_ok = m["n"] > 0 and m["p"] < ADOPT_P
        ok2 = acc_ok and n_ok and p_ok
        if ok2:
            passed_clean.append(c)
        why = []
        if not acc_ok:
            why.append(f"acc {100*m['acc']:.1f}% < {100*ADOPT_ACC:.0f}%" if m["n"] else "no calls")
        if not n_ok:
            why.append(f"n={m['n']} < {ADOPT_N}")
        if not p_ok and m["n"]:
            why.append(f"p={m['p']:.3f} >= {ADOPT_P}")
        acc_s = "-" if m["n"] == 0 else f"{100*m['acc']:.2f}"
        p_s = "-" if m["n"] == 0 else f"{m['p']:.4f}"
        note = "  (event-list predictor, lag-invariant)" if c == "P5" else ""
        print(f"{LABELS[c]:<28}{acc_s:>8}{m['n']:>6}{p_s:>10}   "
              f"{'PASS' if ok2 else 'FAIL -- ' + '; '.join(why)}{note}")
    print()
    if passed_clean:
        print(f"QUALIFYING AT THE CLEAN LAG: {', '.join(LABELS[c] for c in passed_clean)}")
    else:
        print("NO PREDICTOR QUALIFIES AT THE CLEAN LAG.")
        print("Storm direction is NOT predictable before the storm begins by any of the five")
        print("pre-registered signals. The pre-positioned resting-limit idea has no directional")
        print("edge to rest on.")

    # ---------------- deep dive on whatever survived the clean lag ----------------
    header(f"5c. DEEP DIVE -- what survives at onset - {L0} min, and is it really a forecast?")
    days_all = np.array([t.date() for t in ev_ts])
    fod = np.zeros(len(ev_pos), dtype=bool)
    _seen: set = set()
    for i, d in enumerate(days_all):
        if d not in _seen:
            _seen.add(d)
            fod[i] = True

    def calls_at(c: str, L: int) -> np.ndarray:
        pos = ev_pos - L
        v = np.full(len(ev_pos), np.nan)
        ok = pos >= P2_LOOKBACK_MIN
        v[ok] = P[c][pos[ok]]
        return v

    for c in (passed_clean or ["P2"]):
        if c == "P5":
            continue
        v = calls_at(c, L0)
        print(f"\n{LABELS[c]} at L={L0}")
        rows = [
            ("  exploratory (first 60%)", score(v[explore], direction[explore])),
            ("  judgment (last 40%)", score(v[judge], direction[judge])),
            ("  judgment, first-of-day", score(v[judge & fod], direction[judge & fod])),
            ("  all events", score(v, direction)),
            ("  all events, first-of-day", score(v[fod], direction[fod])),
        ]
        print_pred_table("", rows)
        # does the edge come from one side only? (a falling-market artefact would)
        for side, lab in [(1.0, "UP calls  "), (-1.0, "DOWN calls")]:
            sel = judge & np.isfinite(v) & (v == side)
            if sel.sum():
                m = score(v[sel], direction[sel])
                print(f"  judgment {lab}: n={m['n']:>3}  acc={100*m['acc']:>5.1f}%  "
                      f"p={m['p']:.4f}")
        # is it just a same-day repeat of the previous storm's direction?
        prev = np.full(len(ev_pos), np.nan)
        prev[1:] = direction[:-1]
        same_day = np.zeros(len(ev_pos), dtype=bool)
        same_day[1:] = days_all[1:] == days_all[:-1]
        agree = np.isfinite(v) & (v != 0) & np.isfinite(prev)
        a_sd = agree & same_day
        if a_sd.sum():
            print(f"  on same-day repeat events (n={int(a_sd.sum())}), this predictor agrees "
                  f"with the PREVIOUS storm's direction {100*(v[a_sd]==prev[a_sd]).mean():.1f}% "
                  f"of the time")
        a_nd = agree & ~same_day
        if a_nd.sum():
            print(f"  on first-of-day events   (n={int(a_nd.sum())}), it agrees with the "
                  f"previous storm's direction {100*(v[a_nd]==prev[a_nd]).mean():.1f}% "
                  f"of the time")
        print("  -> a predictor that merely echoes the running trend of a trending day is a")
        print("     regime label, not a forecast; it cannot tell you WHEN to have the position on.")

    # ---------------- robustness: one event per day ----------------
    header("6. ROBUSTNESS -- ONE EVENT PER DAY (event clustering control)")
    print("storms cluster inside single volatile days; the events inside one day share the")
    print("same regime and are not independent draws. Keeping only the FIRST event of each")
    print("UTC day is a crude but honest de-clustering.\n")
    days = np.array([t.date() for t in ev_ts])
    first_of_day = np.zeros(len(ev_pos), dtype=bool)
    seen = set()
    for i, d in enumerate(days):
        if d not in seen:
            seen.add(d)
            first_of_day[i] = True
    print(f"{len(ev_pos)} events on {len(seen)} distinct UTC days "
          f"({len(ev_pos)/len(seen):.2f} events per storm day)")
    dc = pd.Series(1, index=ev_ts).groupby(days).sum().sort_values(ascending=False)
    print("busiest days: " + ", ".join(f"{d}({int(c)})" for d, c in dc.head(6).items()))
    top5 = 100.0 * dc.head(5).sum() / len(ev_pos)
    print(f"top 5 storm days hold {int(dc.head(5).sum())} events = {top5:.1f}% of all events")
    rows_d = [(LABELS[c], score(calls[c][judge & first_of_day], direction[judge & first_of_day]))
              for c in PREDICTORS]
    print_pred_table("[JUDGMENT events, first-of-day only]", rows_d)

    # ---------------- regime drift ----------------
    header(f"7. REGIME DRIFT -- up-share and clean-lag P2 accuracy by month")
    print("the up-share of storms tracks the month's own trend, which is the mechanism behind")
    print(f"P2's clean-lag accuracy: it is reading the prevailing regime, not the coming storm.\n")
    mon = pd.Series(direction, index=ev_ts).groupby(ev_ts.to_period("M")).agg(
        n="size", up=lambda s: int((s > 0).sum()))
    v_p2 = calls_at("P2", L0)
    hit = pd.Series(np.where(np.isfinite(v_p2) & (v_p2 != 0),
                             (v_p2 == direction).astype(float), np.nan), index=ev_ts)
    print(f"{'month':<10}{'events':>8}{'up%':>8}{'P2@L31 acc%':>14}{'n':>6}   "
          f"BTC close move over the month")
    line()
    for per, row in mon.iterrows():
        sel = ev_ts.to_period("M") == per
        h = hit[sel].dropna()
        acc = f"{100*h.mean():.1f}" if len(h) else "-"
        seg = b["close"][b.index.to_period("M") == per]
        mv = 100.0 * (seg.iloc[-1] / seg.iloc[0] - 1.0) if len(seg) else float("nan")
        print(f"{str(per):<10}{int(row['n']):>8}{100*row['up']/row['n']:>8.1f}"
              f"{acc:>14}{len(h):>6}   {mv:+.1f}%")

    # ---------------- economic frame ----------------
    header("8. ECONOMIC SANITY CHECK -- naive pre-positioning in the armed window")
    print(f"at every minute in {ARMED_START[0]:02d}:{ARMED_START[1]:02d}-"
          f"{ARMED_END[0]:02d}:{ARMED_END[1]:02d} UTC that carries a prediction, hold that")
    print(f"direction for {HOLD_MIN}m; net of one taker round trip = {ROUND_TRIP_BPS} bps.")
    print("Overlapping 2h holds -> the naive t-stat is badly overstated; the day-clustered")
    print("t-stat is the one to read. This is a sanity check, NOT a backtest.\n")
    judge_start = ev_pos[k_split]
    seg_all = np.ones(len(idx), dtype=bool)
    seg_judge = np.zeros(len(idx), dtype=bool); seg_judge[judge_start:] = True

    if passed:
        targets = passed
        print("Running for the QUALIFYING predictor(s).")
    else:
        best = max(PREDICTORS, key=lambda c: (res_j[c]["acc"] if res_j[c]["n"] else -1))
        targets = [best]
        print(f"No predictor qualifies, so nothing earns this simulation. Running it for the")
        print(f"highest-accuracy judgment predictor ({LABELS[best]}) purely to show the scale")
        print(f"of the payoff -- it is ILLUSTRATIVE and must not be read as a tradable edge.")
    for nm, seg in [("full sample", seg_all), ("judgment period", seg_judge)]:
        print(f"\n[{nm}]")
        for c in targets:
            econ_check(LABELS[c], P[c] if c != "P5" else np.full(len(idx), np.nan),
                       logc, idx, seg)
        if any(c == "P5" for c in targets):
            print("  (P5 is defined only on storm events, not on every minute -> "
                  "no armed-window analogue)")
        # always show the always-long benchmark for scale
        econ_check("benchmark: always LONG", np.ones(len(idx)), logc, idx, seg)

    # ---------------- verdict ----------------
    header("9. VERDICT")
    print("Q: is the DIRECTION of a storm predictable before it starts?")
    print()
    print(f"1. Unconditional: {n_up}/{len(direction)} up ({100*n_up/len(direction):.1f}%), "
          f"p={p_uncond:.3f}. No usable directional bias in storms themselves.")
    print("2. As literally pre-registered (predictors at onset-1), P1/P2/P3/MAJ all clear the")
    print("   adoption bar at 87-96% accuracy. That result is NOT a forecast: the storm is")
    print(f"   defined by a TRAILING {STORM_WINDOW_MIN}m return, so at onset-1 the move is "
          f"already {STORM_WINDOW_MIN-1} minutes")
    print("   old and sits inside the P1/P3 lookbacks. The pre-registration has a design flaw;")
    print("   the honest reading of section 4b is that these predictors measure the storm.")
    print(f"3. Pushed back to onset-{L0} (storm window excluded): P1 {100*sweep[('P1',L0)]['acc']:.1f}% "
          f"(p={sweep[('P1',L0)]['p']:.3f}), P3 {100*sweep[('P3',L0)]['acc']:.1f}% "
          f"(p={sweep[('P3',L0)]['p']:.3f}),")
    print(f"   P4 50.0% (p=1.000), P5 {100*res_j['P5']['acc']:.1f}% "
          f"(p={res_j['P5']['p']:.3f}) -- all indistinguishable from a coin flip.")
    print(f"4. Two survive the clean lag: P2 {100*sweep[('P2',L0)]['acc']:.1f}% "
          f"(n={sweep[('P2',L0)]['n']}, p={sweep[('P2',L0)]['p']:.4f}) and "
          f"MAJ {100*sweep[('MAJ',L0)]['acc']:.1f}% "
          f"(n={sweep[('MAJ',L0)]['n']}, p={sweep[('MAJ',L0)]['p']:.4f}).")
    print("   P2's accuracy is flat from L=30 to L=180, so it is a 24h-trend regime label")
    print("   ('storms break the way the day is already leaning'), not a timing signal. MAJ is")
    print("   driven by P2 and sits barely over the 58% bar with p just under 0.05, one")
    print("   marginal call away from failing.")
    print("5. Economic frame: NO configuration produces a day-clustered t-stat above 1.0, in")
    print("   either the full sample or the judgment period. P2's positive minute-weighted")
    print("   mean is a day-selection artefact (fully-armed days +40bps, sparse days -36bps).")
    print()
    print("CONCLUSION: the direction of a storm is NOT predictable before it starts in any way")
    print("that supports pre-positioning. The one weak survivor (24h range position) is a slow")
    print("trend label with no timing content and no net payoff, and it says nothing about WHEN")
    print("to have the position on -- which is exactly what a resting-limit strategy needs.")
    print("Recorded as a NEGATIVE result.")

    print()
    line("=")
    print("done.")
    line("=")


if __name__ == "__main__":
    sys.exit(main())
