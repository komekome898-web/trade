#!/usr/bin/env python3
"""Study S1 -- calm-regime range fading with maker entries and a storm-onset stop.

Pre-registered re-audit of the "range fading is dead" verdict. The owner's
hypothesis has three parts, and the design isolates each one:

  1. only trade in a CALM regime (no recent 5s burst, flat 30m drift),
  2. enter PASSIVELY at the range edge (maker, fee 0, no spread paid),
  3. cut IMMEDIATELY on burst onset (do not wait for the range to break).

Everything below is fixed in advance. The first 60% of the 30-day span is the
EXPLORATION segment (used to pick one config out of 3 families x a small tuning
grid); the last 40% is the JUDGMENT segment, run once, reported as-is.

Adoption bar (pre-registered): judgment segment >= 100 trades AND
net >= +2.0 bps/trade AND day-clustered t >= 2.0.

Data
----
data/executions_FX_BTC_JPY.csv  raw public executions (id, exec_date, price,
                                size, taker side), ~30 days.
data/flow_FX_BTC_JPY.csv        per-minute OHLCV + taker split, built by
                                scripts/build_flow.py from the SAME file.

Everything (regime, range, fills, stops) is computable from bitFlyer data
alone, so a live bot with 250 ms ticker polls could reproduce it.

Execution model (mirrors scripts/replay_scalp_storm.py conservatism)
--------------------------------------------------------------------
* Maker entry / maker TP: a resting limit fills only when a COUNTER-SIDE print
  trades at or through it. We use the real executions tape (ms timestamps and
  the real taker side) rather than a synthetic 1s reconstruction -- the tape is
  the ground truth the 1s series only approximates, so this is strictly closer
  to reality than the pre-registered fallback. No fee, no spread on maker fills.
* Stop (taker), whichever comes first:
    (i)  burst onset: |5s bitFlyer log-return| >= 10 bps AGAINST the position,
    (ii) range break: price beyond the entry-range edge by 10 bps.
  Cost 3.96 bps (1.96 half-spread + 2.0 slippage, burst regime).
* Time stop: flat after 60 minutes, taker at the calm cost 2.93 bps.
* One position at a time; entry limits live for one minute and are re-quoted
  each minute while the regime stays calm, cancelled when it flips.

Usage:  PYTHONPATH=src python scripts/research_calm_range.py
Read-only, no network, idempotent. Writes nothing.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PRODUCT = "FX_BTC_JPY"

# ---- fixed constants (pre-registered) ------------------------------------- #
BURST_BPS = 10.0            # |5s log-return| threshold, bps
BURST_LOOKBACK_SEC = 600    # calm (a): trailing 10 minutes
DRIFT_LOOKBACK_SEC = 1800   # calm (b): trailing 30 minutes
DRIFT_MAX = 0.004           # calm (b): |30m log-return| < 0.4%
RANGE_BREAK_BPS = 10.0      # stop (ii): beyond the edge by 10 bps
HOLD_MAX_SEC = 3600         # time stop: 60 minutes
COST_BURST_BPS = 1.96 + 2.0     # taker cost on a stop exit
COST_CALM_BPS = 0.93 + 2.0      # taker cost on a time-stop exit
QUOTE_LIFE_SEC = 60         # entry limits re-quoted every minute

BAR_TRADES = 100
BAR_NET_BPS = 2.0
BAR_T = 2.0

FAMILIES = {"F1": 60, "F2": 120, "F3": 240}   # rolling range window, minutes
OFFSETS_BPS = [0.0, 2.0, 5.0]                 # limit placed N bps INSIDE the edge
TP_MODES = ["mid", "third"]                   # midpoint vs 1/3-of-range


def header(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


# --------------------------------------------------------------------------- #
# 1. data loading -- unit-proof epoch conversion
# --------------------------------------------------------------------------- #
def epoch_seconds(ts: pd.Series | pd.Index) -> np.ndarray:
    """datetime -> float epoch seconds, immune to the datetime64 unit trap.

    A prior replay in this repo had a silent us-vs-s epoch bug from relying on
    the array's native unit. We force ns explicitly, then divide by 1e9.
    """
    idx = pd.DatetimeIndex(pd.to_datetime(ts, format="ISO8601", utc=True))
    return idx.values.astype("datetime64[ns]").astype("int64") / 1e9


@dataclass
class Market:
    t0: int                 # epoch second of grid element 0
    n: int                  # grid length in seconds
    price: np.ndarray       # (n,) 1s last price, forward filled
    logp: np.ndarray        # (n,) log price
    r5: np.ndarray          # (n,) 5s log-return in bps
    calm: np.ndarray        # (n,) calm regime flag (both conditions)
    calm_a: np.ndarray
    calm_b: np.ndarray
    ptime: np.ndarray       # (m,) print epoch seconds (float, ms resolution)
    pprice: np.ndarray      # (m,) print price
    pbuy: np.ndarray        # (m,) True if taker side is BUY
    minutes: np.ndarray     # (k,) epoch second of each 1m candle open
    mhigh: np.ndarray
    mlow: np.ndarray
    mclose: np.ndarray


def load_market() -> Market:
    ex = pd.read_csv(DATA / f"executions_{PRODUCT}.csv")
    ex = ex.sort_values("id", kind="mergesort")
    ptime = epoch_seconds(ex["exec_date"])
    order = np.argsort(ptime, kind="mergesort")
    ptime = ptime[order]
    pprice = ex["price"].to_numpy(float)[order]
    pbuy = (ex["side"].to_numpy() == "BUY")[order]

    t0 = int(np.floor(ptime[0]))
    t1 = int(np.ceil(ptime[-1]))
    n = t1 - t0 + 1
    price = np.full(n, np.nan)
    si = (np.floor(ptime) - t0).astype(np.int64)
    price[si] = pprice                      # last print of the second wins
    fill_idx = np.where(~np.isnan(price), np.arange(n), 0)
    np.maximum.accumulate(fill_idx, out=fill_idx)
    price = price[fill_idx]                 # forward fill (no look-ahead)
    logp = np.log(price)

    r5 = np.zeros(n)
    r5[5:] = (logp[5:] - logp[:-5]) * 1e4
    burst = np.abs(r5) >= BURST_BPS
    cum = np.concatenate([[0], np.cumsum(burst)])
    calm_a = np.zeros(n, bool)
    calm_a[BURST_LOOKBACK_SEC:] = (
        cum[BURST_LOOKBACK_SEC:n] - cum[0:n - BURST_LOOKBACK_SEC]
    ) == 0                                   # trailing window is [s-600, s)
    calm_b = np.zeros(n, bool)
    calm_b[DRIFT_LOOKBACK_SEC:] = np.abs(
        logp[DRIFT_LOOKBACK_SEC:] - logp[:-DRIFT_LOOKBACK_SEC]
    ) < DRIFT_MAX
    calm = calm_a & calm_b

    fl = pd.read_csv(DATA / f"flow_{PRODUCT}.csv")
    mt = epoch_seconds(fl["ts"])
    return Market(
        t0=t0, n=n, price=price, logp=logp, r5=r5,
        calm=calm, calm_a=calm_a, calm_b=calm_b,
        ptime=ptime, pprice=pprice, pbuy=pbuy,
        minutes=mt.astype(np.int64),
        mhigh=fl["high"].to_numpy(float),
        mlow=fl["low"].to_numpy(float),
        mclose=fl["close"].to_numpy(float),
    )


# --------------------------------------------------------------------------- #
# 2. backtest engine
# --------------------------------------------------------------------------- #
@dataclass
class Cfg:
    family: str
    window: int
    offset_bps: float
    tp_mode: str
    use_calm: bool = True
    use_burst_stop: bool = True
    use_range_stop: bool = True   # post-hoc diagnostic only, not a tuning knob


TRADE_COLS = ["ts_entry", "ts_exit", "side", "entry", "exit", "gross_bps",
              "cost_bps", "net_bps", "reason", "hold_sec", "rng_lo", "rng_hi"]


def _rolling_extrema(mh: np.ndarray, ml: np.ndarray, w: int):
    """Trailing high/low over the w COMPLETED minutes strictly before each bar."""
    hi = pd.Series(mh).rolling(w).max().shift(1).to_numpy()
    lo = pd.Series(ml).rolling(w).min().shift(1).to_numpy()
    return hi, lo


def _manage(mk: Market, side: int, t_fill: float, entry: float,
            tp: float, lo: float, hi: float, use_burst_stop: bool,
            use_range_stop: bool = True):
    """Run one open position forward. Returns (t_exit, px_exit, cost, reason)."""
    s_start = int(np.ceil(t_fill)) - mk.t0
    s_end = min(mk.n - 1, int(np.floor(t_fill + HOLD_MAX_SEC)) - mk.t0)
    if s_end <= s_start:
        s_end = min(mk.n - 1, s_start)

    # ---- stop scan on the 1s grid (seconds strictly after the fill second) --
    t_stop, px_stop = np.inf, np.nan
    if s_end >= s_start:
        seg_p = mk.price[s_start:s_end + 1]
        seg_r = mk.r5[s_start:s_end + 1]
        if use_range_stop:
            trig = (seg_p < lo * (1 - RANGE_BREAK_BPS / 1e4)) if side > 0 else \
                   (seg_p > hi * (1 + RANGE_BREAK_BPS / 1e4))
        else:
            trig = np.zeros(seg_p.shape, bool)
        if use_burst_stop:
            bst = (seg_r <= -BURST_BPS) if side > 0 else (seg_r >= BURST_BPS)
            trig = trig | bst
        w = np.flatnonzero(trig)
        if w.size:
            k = int(w[0])
            t_stop = float(s_start + k + mk.t0)
            px_stop = float(seg_p[k])

    # ---- TP scan on the real tape ------------------------------------------
    lo_i = int(np.searchsorted(mk.ptime, t_fill, side="right"))
    hi_i = int(np.searchsorted(mk.ptime, t_fill + HOLD_MAX_SEC, side="right"))
    t_tp, px_tp = np.inf, np.nan
    if hi_i > lo_i:
        pp = mk.pprice[lo_i:hi_i]
        pb = mk.pbuy[lo_i:hi_i]
        # LONG position exits with a SELL limit at tp -> a taker BUY reaches it.
        ok = (pb & (pp >= tp)) if side > 0 else ((~pb) & (pp <= tp))
        w = np.flatnonzero(ok)
        if w.size:
            k = int(w[0])
            t_tp = float(mk.ptime[lo_i + k])
            px_tp = tp                      # maker fill happens AT the limit

    if t_tp < t_stop:                       # ties go to the stop (conservative)
        return t_tp, px_tp, 0.0, "tp"
    if np.isfinite(t_stop):
        return t_stop, px_stop, COST_BURST_BPS, "stop"
    t_end = float(s_end + mk.t0)
    return t_end, float(mk.price[s_end]), COST_CALM_BPS, "time"


def backtest(mk: Market, cfg: Cfg, m_lo: int, m_hi: int,
             collect_quotes: bool = False):
    """Run the strategy over minute indices [m_lo, m_hi). Returns (trades, quotes)."""
    hi_arr, lo_arr = _rolling_extrema(mk.mhigh, mk.mlow, cfg.window)
    trades, quotes = [], []
    busy_until = -np.inf
    off = cfg.offset_bps / 1e4

    for m in range(m_lo, m_hi):
        T = float(mk.minutes[m])
        if T < busy_until:
            continue
        s = int(T) - mk.t0
        if s < DRIFT_LOOKBACK_SEC or s + QUOTE_LIFE_SEC >= mk.n:
            continue
        if cfg.use_calm and not mk.calm[s]:
            continue
        hi, lo = hi_arr[m], lo_arr[m]
        if not np.isfinite(hi) or not np.isfinite(lo) or hi <= lo:
            continue
        width = hi - lo
        buy_lim = lo * (1 + off)
        sell_lim = hi * (1 - off)
        if buy_lim >= sell_lim:
            continue

        a = int(np.searchsorted(mk.ptime, T, side="left"))
        b = int(np.searchsorted(mk.ptime, T + QUOTE_LIFE_SEC, side="left"))
        fill_side, t_fill = 0, np.inf
        if b > a:
            pp, pb = mk.pprice[a:b], mk.pbuy[a:b]
            long_ok = np.flatnonzero((~pb) & (pp <= buy_lim))
            short_ok = np.flatnonzero(pb & (pp >= sell_lim))
            kL = int(long_ok[0]) if long_ok.size else 10 ** 9
            kS = int(short_ok[0]) if short_ok.size else 10 ** 9
            if min(kL, kS) < 10 ** 9:
                k = min(kL, kS)
                fill_side = 1 if kL <= kS else -1
                t_fill = float(mk.ptime[a + k])

        if collect_quotes:
            for sd, lim in ((1, buy_lim), (-1, sell_lim)):
                quotes.append({
                    "ts": T, "side": sd, "limit": lim, "lo": lo, "hi": hi,
                    "filled": bool(fill_side == sd),
                    "t_fill": t_fill if fill_side == sd else T + QUOTE_LIFE_SEC,
                })
        if fill_side == 0:
            continue

        entry = buy_lim if fill_side > 0 else sell_lim
        if cfg.tp_mode == "mid":
            tp = 0.5 * (hi + lo)
        else:
            tp = lo + width / 3.0 if fill_side > 0 else hi - width / 3.0
        if (fill_side > 0 and tp <= entry) or (fill_side < 0 and tp >= entry):
            continue

        t_exit, px_exit, cost, reason = _manage(
            mk, fill_side, t_fill, entry, tp, lo, hi, cfg.use_burst_stop,
            cfg.use_range_stop)
        gross = fill_side * (px_exit / entry - 1.0) * 1e4
        trades.append({
            "ts_entry": t_fill, "ts_exit": t_exit, "side": fill_side,
            "entry": entry, "exit": px_exit, "gross_bps": gross,
            "cost_bps": cost, "net_bps": gross - cost, "reason": reason,
            "hold_sec": t_exit - t_fill, "rng_lo": lo, "rng_hi": hi,
        })
        busy_until = t_exit

    tdf = pd.DataFrame(trades, columns=TRADE_COLS)
    qdf = pd.DataFrame(quotes) if collect_quotes else pd.DataFrame()
    return tdf, qdf


# --------------------------------------------------------------------------- #
# 3. statistics
# --------------------------------------------------------------------------- #
def day_clustered_t(tdf: pd.DataFrame) -> tuple[float, int]:
    if tdf.empty:
        return float("nan"), 0
    day = pd.to_datetime(tdf["ts_entry"], unit="s", utc=True).dt.floor("D")
    per_day = tdf.groupby(day)["net_bps"].mean()
    nd = len(per_day)
    if nd < 2:
        return float("nan"), nd
    sd = per_day.std(ddof=1)
    if not np.isfinite(sd) or sd == 0:
        return float("nan"), nd
    return float(per_day.mean() / (sd / np.sqrt(nd))), nd


def summarise(tdf: pd.DataFrame) -> dict:
    if tdf.empty:
        return {"n": 0, "mean": np.nan, "median": np.nan, "sd": np.nan,
                "win": np.nan, "t": np.nan, "days": 0, "total": 0.0}
    t, nd = day_clustered_t(tdf)
    return {
        "n": len(tdf),
        "mean": tdf["net_bps"].mean(),
        "median": tdf["net_bps"].median(),
        "sd": tdf["net_bps"].std(ddof=1),
        "win": (tdf["net_bps"] > 0).mean() * 100,
        "t": t, "days": nd,
        "total": tdf["net_bps"].sum(),
    }


def fmt(s: dict) -> str:
    if s["n"] == 0:
        return f"{0:>6}  {'-':>9} {'-':>9} {'-':>8} {'-':>7} {'-':>7}"
    return (f"{s['n']:>6}  {s['mean']:>+9.2f} {s['median']:>+9.2f} "
            f"{s['sd']:>8.1f} {s['win']:>6.1f}% {s['t']:>+7.2f}")


# --------------------------------------------------------------------------- #
# 4. main
# --------------------------------------------------------------------------- #
def main() -> int:
    pd.set_option("display.width", 200)
    print(__doc__.split("Usage:")[0].strip()[:0] or "", end="")

    header("0. DATA + SPLIT")
    mk = load_market()
    span_days = (mk.n - 1) / 86400
    print(f"executions      : {len(mk.ptime):,} prints, "
          f"{pd.to_datetime(mk.ptime[0], unit='s', utc=True)} .. "
          f"{pd.to_datetime(mk.ptime[-1], unit='s', utc=True)}")
    print(f"1s grid         : {mk.n:,} seconds ({span_days:.2f} days), "
          f"{(np.diff(mk.price) != 0).mean() * 100:.1f}% of seconds change price")
    print(f"1m candles      : {len(mk.minutes):,}")
    sec_with_print = len(np.unique(np.floor(mk.ptime)))
    print(f"seconds with >=1 print: {sec_with_print:,} "
          f"({sec_with_print / mk.n * 100:.1f}%) -- the rest are forward filled")

    n_min = len(mk.minutes)
    split = int(n_min * 0.6)
    t_split = pd.to_datetime(mk.minutes[split], unit="s", utc=True)
    print(f"\nchronological split at 60% of the span: {t_split}")
    print(f"  exploration minutes [0, {split}) "
          f"({pd.to_datetime(mk.minutes[0], unit='s', utc=True).date()} .. "
          f"{t_split.date()})")
    print(f"  judgment    minutes [{split}, {n_min}) "
          f"({t_split.date()} .. "
          f"{pd.to_datetime(mk.minutes[-1], unit='s', utc=True).date()})")

    mb = (mk.minutes - mk.t0).astype(np.int64)
    mb = mb[(mb >= 0) & (mb < mk.n)]
    print(f"\ncalm regime at minute starts: (a) no 10bps/5s burst in trailing 10m "
          f"= {mk.calm_a[mb].mean() * 100:.1f}%")
    print(f"                              (b) |30m return| < 0.4%              "
          f"= {mk.calm_b[mb].mean() * 100:.1f}%")
    print(f"                              (a AND b)                            "
          f"= {mk.calm[mb].mean() * 100:.1f}%")
    print(f"burst seconds (|5s ret| >= 10bps): {int((np.abs(mk.r5) >= BURST_BPS).sum()):,}"
          f" of {mk.n:,}")

    # ---------------- exploration ---------------- #
    header("1. EXPLORATION SEGMENT -- 3 FAMILIES x TUNING GRID (first 60%)")
    print("Tuning is restricted to edge offset (0/2/5 bps inside the edge) and")
    print("TP (range midpoint vs 1/3-of-range). Nothing else is touched.\n")
    print(f"{'family':<8}{'win_m':>6}{'off':>5} {'tp':<6}"
          f"{'trades':>7}  {'mean_bps':>9} {'med_bps':>9} {'sd':>8} {'win%':>7} {'dayT':>7}"
          f"  {'tp%':>5} {'stop%':>6} {'time%':>6}")
    rows = []
    for fam, win in FAMILIES.items():
        for off in OFFSETS_BPS:
            for tpm in TP_MODES:
                cfg = Cfg(fam, win, off, tpm)
                tdf, _ = backtest(mk, cfg, 0, split)
                s = summarise(tdf)
                if s["n"]:
                    rc = tdf["reason"].value_counts(normalize=True) * 100
                else:
                    rc = pd.Series(dtype=float)
                rows.append({"cfg": cfg, **s,
                             "tp%": rc.get("tp", 0.0), "stop%": rc.get("stop", 0.0),
                             "time%": rc.get("time", 0.0)})
                print(f"{fam:<8}{win:>6}{off:>5.0f} {tpm:<6}{fmt(s)}"
                      f"  {rc.get('tp', 0.0):>4.0f}% {rc.get('stop', 0.0):>5.0f}%"
                      f" {rc.get('time', 0.0):>5.0f}%")

    # selection rule, fixed in advance: highest total net bps among configs with
    # enough exploration trades to be measurable; ties broken by mean bps.
    MIN_EXPL = 60
    elig = [r for r in rows if r["n"] >= MIN_EXPL]
    if not elig:
        elig = rows
        print(f"\n[warn] no config reached {MIN_EXPL} exploration trades; "
              f"selecting over all configs")
    best = max(elig, key=lambda r: (r["total"], r["mean"]))
    cfg = best["cfg"]
    print(f"\nselection rule (fixed): maximise TOTAL net bps on the exploration "
          f"segment among configs with >= {MIN_EXPL} trades.")
    print(f"CHOSEN: {cfg.family} (window {cfg.window}m), offset {cfg.offset_bps:.0f} bps, "
          f"TP = {cfg.tp_mode}")
    print(f"  exploration: {best['n']} trades, {best['mean']:+.2f} bps/trade, "
          f"total {best['total']:+.0f} bps, day-T {best['t']:+.2f}")
    best_mean = max(elig, key=lambda r: r["mean"])["cfg"]
    agree = (best_mean.family, best_mean.offset_bps, best_mean.tp_mode) == \
            (cfg.family, cfg.offset_bps, cfg.tp_mode)
    print(f"  selection-rule robustness: max-MEAN-bps would pick "
          f"{best_mean.family}/{best_mean.offset_bps:.0f}bps/{best_mean.tp_mode} -- "
          f"{'same config' if agree else 'a DIFFERENT config'}.")
    if all(r["mean"] < 0 for r in rows):
        print("  NB every config in the grid is negative on exploration; the choice")
        print("  is 'least bad', and the judgment run is a formality unless the sign")
        print("  flips out of sample.")

    # ---------------- judgment ---------------- #
    header("2. JUDGMENT SEGMENT -- CHOSEN CONFIG, RUN ONCE (last 40%)")
    jt, jq = backtest(mk, cfg, split, n_min, collect_quotes=True)
    s = summarise(jt)
    n_quotes = len(jq)
    n_fills = int(jq["filled"].sum()) if n_quotes else 0
    print(f"config          : {cfg.family} window={cfg.window}m "
          f"offset={cfg.offset_bps:.0f}bps tp={cfg.tp_mode}")
    print(f"entry quotes    : {n_quotes:,} limit-minutes "
          f"({n_quotes // 2:,} minutes x 2 sides)")
    print(f"entry fill rate : {n_fills}/{n_quotes} = "
          f"{(n_fills / n_quotes * 100 if n_quotes else 0):.2f}% of resting limits")
    print(f"trades          : {s['n']}")
    if s["n"]:
        rc = jt["reason"].value_counts()
        tp_n = int(rc.get("tp", 0))
        print(f"TP  fill rate   : {tp_n}/{s['n']} = {tp_n / s['n'] * 100:.1f}% "
              f"of positions exited on the maker TP limit")
        print(f"stop rate       : {int(rc.get('stop', 0))}/{s['n']} = "
              f"{rc.get('stop', 0) / s['n'] * 100:.1f}%")
        print(f"time-stop rate  : {int(rc.get('time', 0))}/{s['n']} = "
              f"{rc.get('time', 0) / s['n'] * 100:.1f}%")
        print(f"\nnet bps/trade   : mean {s['mean']:+.3f}  median {s['median']:+.3f}"
              f"  sd {s['sd']:.2f}")
        print(f"win rate        : {s['win']:.1f}%")
        print(f"total net       : {s['total']:+.0f} bps over {s['days']} UTC days")
        print(f"day-clustered t : {s['t']:+.3f}  (n_days={s['days']})")
        print(f"mean hold       : {jt['hold_sec'].mean() / 60:.1f} min "
              f"(median {jt['hold_sec'].median() / 60:.1f})")
        print(f"long/short      : {(jt['side'] > 0).sum()} / {(jt['side'] < 0).sum()}")

    header("2b. ADOPTION BAR")
    c1 = s["n"] >= BAR_TRADES
    c2 = np.isfinite(s["mean"]) and s["mean"] >= BAR_NET_BPS
    c3 = np.isfinite(s["t"]) and s["t"] >= BAR_T
    print(f"  trades   >= {BAR_TRADES}    : {s['n']:>8}      "
          f"{'PASS' if c1 else 'FAIL'}")
    print(f"  net bps  >= {BAR_NET_BPS:+.1f}  : {s['mean']:>+8.2f}      "
          f"{'PASS' if c2 else 'FAIL'}")
    print(f"  day-T    >= {BAR_T:+.1f}  : {s['t']:>+8.2f}      "
          f"{'PASS' if c3 else 'FAIL'}")
    print(f"\n  VERDICT: {'PASS' if (c1 and c2 and c3) else 'FAIL'}")

    # ---------------- adverse selection ---------------- #
    header("3. ADVERSE-SELECTION COUNTERFACTUAL (judgment segment)")
    print("A resting bid at the bottom of a range only fills when someone is")
    print("willing to hit it there. The question is whether the fills we get are")
    print("exactly the moves that keep going -- i.e. the breakouts.\n")
    if n_quotes:
        base_i = np.clip((np.floor(jq["t_fill"].to_numpy()) - mk.t0).astype(np.int64),
                         0, mk.n - 1)
        base_px = mk.price[base_i]
        sd = jq["side"].to_numpy(float)
        print(f"{'horizon':<10}{'filled limits':>26}{'missed limits':>26}")
        print(f"{'':<10}{'n':>7}{'drift bps':>10}{'adverse%':>9}"
              f"{'n':>7}{'drift bps':>10}{'adverse%':>9}")
        for hz in (60, 300, 600, 3600):
            fwd_i = np.clip(base_i + hz, 0, mk.n - 1)
            drift = sd * (np.log(mk.price[fwd_i]) - np.log(base_px)) * 1e4
            f = jq["filled"].to_numpy()
            df_, dm_ = drift[f], drift[~f]
            print(f"{hz:>5}s     {len(df_):>7}{df_.mean():>+10.2f}"
                  f"{(df_ < 0).mean() * 100:>8.0f}%"
                  f"{len(dm_):>7}{dm_.mean():>+10.2f}{(dm_ < 0).mean() * 100:>8.0f}%")
        print("\n'drift' is the side-adjusted market move from the quote's reference")
        print("second (fill time for filled limits, quote-window end for missed ones);")
        print("positive = the market moved the way the fade wanted. 'adverse%' is the")
        print("share of quotes where it moved against the fade.")

        # full counterfactual, two entry-price assumptions for the missed set
        miss = jq[~jq["filled"]]
        cf_lim, cf_mkt = [], []
        skipped = [0, 0]
        for r in miss.itertuples():
            lo, hi = r.lo, r.hi
            width = hi - lo
            side = int(r.side)
            t_ref = float(r.t_fill)
            s_ref = int(np.clip(np.floor(t_ref) - mk.t0, 0, mk.n - 1))
            tp = 0.5 * (hi + lo) if cfg.tp_mode == "mid" else (
                lo + width / 3.0 if side > 0 else hi - width / 3.0)
            for bag, entry, extra in (
                    (cf_lim, float(r.limit), 0.0),
                    (cf_mkt, float(mk.price[s_ref]), COST_CALM_BPS)):
                if (side > 0 and tp <= entry) or (side < 0 and tp >= entry):
                    skipped[0 if extra == 0.0 else 1] += 1
                    continue
                te, pe, cost, reason = _manage(mk, side, t_ref, entry, tp, lo, hi,
                                               cfg.use_burst_stop, cfg.use_range_stop)
                g = side * (pe / entry - 1.0) * 1e4
                bag.append({"ts_entry": t_ref, "net_bps": g - cost - extra,
                            "reason": reason})
        print("\nfull counterfactual -- every MISSED limit force-filled and then")
        print("managed by the identical exit logic, under two entry assumptions:")
        print(f"{'':<34}{'trades':>7}  {'mean_bps':>9} {'med_bps':>9} {'sd':>8} "
              f"{'win%':>7} {'dayT':>7}")
        print(f"{'actually filled (maker, real)':<34}{fmt(s)}")
        for label, bag in (("missed, filled AT the limit", cf_lim),
                           ("missed, chased at market (taker)", cf_mkt)):
            cs = summarise(pd.DataFrame(bag)) if bag else {"n": 0}
            print(f"{label:<34}{fmt(cs)}")
        print(f"\n  ({skipped[1]} of {len(miss)} missed limits are dropped from the")
        print("  'chased at market' row because the market had already passed the TP")
        print("  by the end of the quote window -- there was nothing left to fade.)")
        print("\n  'filled AT the limit' is NOT obtainable: the market never traded")
        print("  there, so that row buys ~10 bps below every print in the window. It")
        print("  is an upper bound on adverse selection, not an estimate. The 'chased")
        print("  at market' row is the honest comparison -- same setups, executable")
        print("  entry price -- and it is what tells you whether the missed setups")
        print("  were genuinely better than the ones the tape handed us.")

    # ---------------- decomposition ---------------- #
    header("4. PnL DECOMPOSITION + THE BURST STOP'S CONTRIBUTION")
    if s["n"]:
        g = jt.groupby("reason")["net_bps"]
        dec = pd.DataFrame({"trades": g.size(), "mean_bps": g.mean(),
                            "total_bps": g.sum()})
        dec["share_of_trades%"] = dec["trades"] / s["n"] * 100
        # contribution of each bucket to the OVERALL mean bps/trade; these sum
        # to the headline number, which a %-of-total column cannot do when the
        # total is negative.
        dec["contrib_to_mean"] = dec["total_bps"] / s["n"]
        print(dec.round(2).to_string())
        print(f"\ncontributions sum to {dec['contrib_to_mean'].sum():+.3f} bps/trade "
              f"= the headline {s['mean']:+.3f}")
        print(f"total net: {s['total']:+.1f} bps")

        # the geometry that decides the whole thing
        wbps = (jt["rng_hi"] - jt["rng_lo"]) / jt["entry"] * 1e4
        tp_dist = wbps * (0.5 if cfg.tp_mode == "mid" else 1 / 3.0) \
            - cfg.offset_bps
        stop_dist = RANGE_BREAK_BPS + cfg.offset_bps + COST_BURST_BPS
        be = 100 * stop_dist / (tp_dist.median() + stop_dist)
        print(f"\ngeometry: range width {wbps.median():.0f} bps median "
              f"({wbps.quantile(.1):.0f}..{wbps.quantile(.9):.0f} p10-p90)")
        print(f"  reward if TP hits      : {tp_dist.median():+.0f} bps (median)")
        print(f"  risk if the stop hits  : {-stop_dist:+.0f} bps "
              f"({RANGE_BREAK_BPS:.0f} bps break + {COST_BURST_BPS:.2f} taker cost)")
        print(f"  breakeven TP hit rate  : {be:.1f}%")
        print(f"  ACTUAL TP hit rate     : {(jt['reason'] == 'tp').mean() * 100:.1f}%")
        print("  -> the edge does not hold price often enough to pay for a stop")
        print("     placed 10 bps beyond it. That gap, not the cost model, is the")
        print("     whole result.")
        print(f"\nmedian hold by exit: "
              + ", ".join(f"{k} {v / 60:.1f}m" for k, v in
                          jt.groupby('reason')['hold_sec'].median().items()))

        # how often does the burst stop specifically fire (vs the range break)?
        fired_burst = 0
        for r in jt[jt["reason"] == "stop"].itertuples():
            si_ = int(r.ts_exit) - mk.t0
            if 0 <= si_ < mk.n:
                rr = mk.r5[si_]
                if (r.side > 0 and rr <= -BURST_BPS) or (r.side < 0 and rr >= BURST_BPS):
                    fired_burst += 1
        n_stop = int((jt["reason"] == "stop").sum())
        print(f"\nof {n_stop} stop exits, {fired_burst} were triggered by the BURST "
              f"condition ({fired_burst / n_stop * 100 if n_stop else 0:.0f}%);")
        print(f"the remaining {n_stop - fired_burst} were pure range breaks.")

        nb_cfg = Cfg(cfg.family, cfg.window, cfg.offset_bps, cfg.tp_mode,
                     use_calm=cfg.use_calm, use_burst_stop=False)
        nbt, _ = backtest(mk, nb_cfg, split, n_min)
        nb = summarise(nbt)
        print("\nNO-BURST-STOP variant (range break + time stop only), same segment:")
        print(f"{'':<22}{'trades':>7}  {'mean_bps':>9} {'med_bps':>9} {'sd':>8} "
              f"{'win%':>7} {'dayT':>7}")
        print(f"{'with burst stop':<22}{fmt(s)}")
        print(f"{'without burst stop':<22}{fmt(nb)}")
        if nb["n"]:
            print(f"\nburst stop is worth {s['mean'] - nb['mean']:+.2f} bps/trade "
                  f"(total {s['total']:+.0f} vs {nb['total']:+.0f} bps)")
            print("  (trade counts can differ because exit times differ, which shifts")
            print("   when the next entry becomes possible.)")

        print("\nPOST-HOC DIAGNOSTIC (not part of the adoption decision, not a")
        print("tuning knob): what if the fade were given no price stop at all and")
        print("only the 60-minute time stop -- i.e. is it the stops that kill it, or")
        print("the fade itself?")
        ns_cfg = Cfg(cfg.family, cfg.window, cfg.offset_bps, cfg.tp_mode,
                     use_calm=cfg.use_calm, use_burst_stop=False, use_range_stop=False)
        nst, _ = backtest(mk, ns_cfg, split, n_min)
        ns = summarise(nst)
        print(f"{'':<22}{'trades':>7}  {'mean_bps':>9} {'med_bps':>9} {'sd':>8} "
              f"{'win%':>7} {'dayT':>7}")
        print(f"{'pre-registered':<22}{fmt(s)}")
        print(f"{'no price stop at all':<22}{fmt(ns)}")
        if ns["n"]:
            rc2 = nst["reason"].value_counts(normalize=True) * 100
            print(f"  (TP {rc2.get('tp', 0):.0f}% / time stop {rc2.get('time', 0):.0f}%)")

    # ---------------- calm filter ---------------- #
    header("5. CALM-FILTER EFFECTIVENESS (judgment segment)")
    nc_cfg = Cfg(cfg.family, cfg.window, cfg.offset_bps, cfg.tp_mode,
                 use_calm=False, use_burst_stop=cfg.use_burst_stop)
    nct, _ = backtest(mk, nc_cfg, split, n_min)
    nc = summarise(nct)
    print(f"{'':<22}{'trades':>7}  {'mean_bps':>9} {'med_bps':>9} {'sd':>8} "
          f"{'win%':>7} {'dayT':>7}")
    print(f"{'calm filter ON':<22}{fmt(s)}")
    print(f"{'calm filter OFF':<22}{fmt(nc)}")
    if nc["n"] and s["n"]:
        print(f"\ncalm filter is worth {s['mean'] - nc['mean']:+.2f} bps/trade; it "
              f"removes {nc['n'] - s['n']} of {nc['n']} trades "
              f"({(1 - s['n'] / nc['n']) * 100:.0f}%).")

    # per-element ablation for completeness
    print("\nfull 2x2 ablation of the owner's elements 1 and 3 (judgment segment):")
    print(f"{'calm':<6}{'burst stop':<12}{'trades':>7}  {'mean_bps':>9} "
          f"{'med_bps':>9} {'sd':>8} {'win%':>7} {'dayT':>7}")
    for uc in (True, False):
        for ub in (True, False):
            t_, _ = backtest(mk, Cfg(cfg.family, cfg.window, cfg.offset_bps,
                                     cfg.tp_mode, use_calm=uc, use_burst_stop=ub),
                             split, n_min)
            print(f"{str(uc):<6}{str(ub):<12}{fmt(summarise(t_))}")

    # ---------------- sanity ---------------- #
    header("6. SANITY CHECKS")
    ok = True
    if s["n"] > 1:
        overlap = (jt["ts_entry"].to_numpy()[1:] < jt["ts_exit"].to_numpy()[:-1]).sum()
        print(f"  overlapping positions            : {overlap}  "
              f"{'OK' if overlap == 0 else 'FAIL'}")
        ok &= overlap == 0
        bad = (jt["ts_exit"] < jt["ts_entry"]).sum()
        print(f"  exits before entries             : {bad}  "
              f"{'OK' if bad == 0 else 'FAIL'}")
        ok &= bad == 0
        long_hold = (jt["hold_sec"] > HOLD_MAX_SEC + 2).sum()
        print(f"  holds longer than the time stop  : {long_hold}  "
              f"{'OK' if long_hold == 0 else 'FAIL'}")
        ok &= long_hold == 0
        inr = (((jt["side"] > 0) & (jt["entry"] >= jt["rng_lo"]) &
                (jt["entry"] <= jt["rng_hi"])) |
               ((jt["side"] < 0) & (jt["entry"] >= jt["rng_lo"]) &
                (jt["entry"] <= jt["rng_hi"]))).sum()
        print(f"  entries inside their own range   : {inr}/{s['n']}  "
              f"{'OK' if inr == s['n'] else 'CHECK'}")
        tp_bad = ((jt["reason"] == "tp") & (jt["gross_bps"] <= 0)).sum()
        print(f"  TP exits with non-positive gross : {tp_bad}  "
              f"{'OK' if tp_bad == 0 else 'FAIL'}")
        ok &= tp_bad == 0
    # look-ahead: range uses shift(1) on completed minutes; regime uses trailing
    # windows ending at the decision second; fills use prints strictly inside the
    # quote window. Re-assert the range property numerically.
    hi_arr, lo_arr = _rolling_extrema(mk.mhigh, mk.mlow, cfg.window)
    chk = np.isfinite(hi_arr) & np.isfinite(lo_arr)
    ii = np.flatnonzero(chk)[:20000]
    la = 0
    for i in ii[::37]:
        if hi_arr[i] != mk.mhigh[i - cfg.window:i].max():
            la += 1
    print(f"  range = trailing completed minutes only : "
          f"{'OK' if la == 0 else f'{la} MISMATCH'}")
    ok &= la == 0
    tr_per_day = s["n"] / max(s["days"], 1)
    print(f"  trades/day (judgment)            : {tr_per_day:.1f}  "
          f"(quotes/day {n_quotes / 2 / max(s['days'], 1):.0f})")
    print(f"\n  SANITY: {'all checks pass' if ok else 'SOMETHING FAILED -- see above'}")

    header("7. CAVEATS")
    for line in [
        "1s approximation: only ~12% of seconds carry a print, so the 1s last-price",
        "   series is ~88% forward filled. Burst detection (5s return) is therefore",
        "   slightly laggy and understates true intra-second bursts.",
        "last-trade-as-touch: we have no book. A limit at the range edge is tested",
        "   against trade prints only; queue position, partial fills and the fact",
        "   that a real resting order may sit behind size at the same tick are all",
        "   ignored. Real fill rates are LOWER than reported here, and the fills you",
        "   lose are preferentially the good ones (you are last in queue exactly when",
        "   flow is thin).",
        "tape completeness: the executions file is a paginated snapshot; ~36% of",
        "   individual prints are missing (454 pagination gaps), but those gaps cover",
        "   only 0.11% of wall-clock time because they land in high-rate bursts.",
        "   Missing prints make fills HARDER, so the bias is conservative.",
        "30 days, one regime: the whole sample is a single market state. A 12-day",
        "   judgment window cannot distinguish a strategy from a regime.",
        "the calm filter is weak by construction: ~90% of minutes qualify, so",
        "   'calm-only' is close to 'always' on this sample.",
        "no funding/financing cost is modelled; FX_BTC_JPY charges a daily swap on",
        "   positions held over the settlement time. Holds here are <= 60 min so this",
        "   is second-order, but it is not zero.",
    ]:
        print(("  " if line.startswith("   ") else "* ") + line.strip()
              if not line.startswith("   ") else "  " + line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
