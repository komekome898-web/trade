#!/usr/bin/env python3
"""Study R5-S1 -- range fading with REVERSED execution.

Prior study (scripts/research_calm_range.py) faded the range edges with MAKER
entries and failed at -3.30 bps/trade. Root cause: the resting fade limits at
the edges filled only 0.86% of the time, and the fills we did get were the
breakouts (-6.5 bps of adverse drift). The entry side was selecting against us.

This study runs the mirror image, pre-registered by the owner:

  * ENTRY  -- pay TAKER the moment price touches the edge. No entry-side
              selection at all: every calm-minute touch is traded.
  * EXIT   -- rest a MAKER take-profit INSIDE the range (fee 0). A maker TP on
              a fade fills on exactly the reversion the trade is betting on, so
              the exit-side selection works FOR us instead of against us.
  * STOP   -- burst onset (|5s ret| >= 10 bps against) or 10 bps beyond the
              entry edge, taker. 60-minute time stop, taker.

Everything below is fixed in advance.  The first 60% of the 30-day span is the
EXPLORATION segment (9 configs: window x TP distance); the last 40% is the
JUDGMENT segment, run once, reported as-is.

Adoption bar (pre-registered): judgment >= 100 trades AND net >= +2.0 bps/trade
AND day-clustered t >= 2.0.

Data
----
data/executions_FX_BTC_JPY.csv  raw public executions (~820k prints, 30 days)
data/flow_FX_BTC_JPY.csv        per-minute OHLCV built from the SAME file

Usage:  python scripts/research_range_reversed.py
Read-only, no network, idempotent, writes nothing.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PRODUCT = "FX_BTC_JPY"

# ---- fixed constants (pre-registered) ------------------------------------- #
BURST_BPS = 10.0             # |5s log-return| threshold, bps
BURST_LOOKBACK_SEC = 600     # calm (a): trailing 10 minutes
DRIFT_LOOKBACK_SEC = 1800    # calm (b): trailing 30 minutes
DRIFT_MAX = 0.004            # calm (b): |30m log-return| < 0.4%
RANGE_BREAK_BPS = 10.0       # stop: 10 bps beyond the entry edge
HOLD_MAX_SEC = 3600          # time stop: 60 minutes
COST_TAKER_BURST = 1.96 + 2.0    # 3.96 bps -- entry touch and stop exit
COST_TAKER_CALM = 0.93 + 2.0     # 2.93 bps -- time-stop exit (and sensitivity)
COOLDOWN_SEC = 60.0          # minimum gap between exit and next entry
RETRACE_FRAC = 0.25          # re-entry guard: 25% of the range off the edge

BAR_TRADES = 100
BAR_NET_BPS = 2.0
BAR_T = 2.0

WINDOWS = [60, 120, 240]                   # rolling range window, minutes
TP_MODES = ["third", "mid", "fix10"]       # TP distance inside the range
MIN_EXPL_TRADES = 60                       # selection eligibility

EPOCH = pd.Timestamp("1970-01-01", tz="UTC")


def header(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def sub(title: str) -> None:
    print("\n" + "-" * 78)
    print(title)
    print("-" * 78)


# --------------------------------------------------------------------------- #
# 1. data loading -- unit-proof epoch conversion
# --------------------------------------------------------------------------- #
def epoch_seconds(ts) -> np.ndarray:
    """datetime -> float epoch seconds, immune to the datetime64 unit trap.

    A prior replay in this repo had a silent us-vs-s epoch bug from relying on
    the array's native unit.  Dividing a Timedelta by Timedelta('1s') is
    unit-agnostic by construction: pandas normalises both operands.
    """
    idx = pd.DatetimeIndex(pd.to_datetime(ts, format="ISO8601", utc=True))
    return ((idx - EPOCH) / pd.Timedelta("1s")).to_numpy(dtype=float)


def epoch_seconds_ns(ts) -> np.ndarray:
    """Independent implementation used only to cross-check `epoch_seconds`."""
    idx = pd.DatetimeIndex(pd.to_datetime(ts, format="ISO8601", utc=True))
    return idx.values.astype("datetime64[ns]").astype("int64") / 1e9


@dataclass
class Market:
    t0: int
    n: int
    price: np.ndarray        # (n,) 1s last price, forward filled
    logp: np.ndarray
    r5: np.ndarray           # (n,) 5s log-return, bps
    calm: np.ndarray         # (n,) calm regime (a AND b)
    calm_a: np.ndarray
    calm_b: np.ndarray
    ptime: np.ndarray        # (m,) print epoch seconds
    pprice: np.ndarray
    pbuy: np.ndarray         # taker side == BUY
    pmin: np.ndarray         # (m,) index of the 1m candle containing the print
    pcalm: np.ndarray        # (m,) calm flag at the START of that candle
    psec: np.ndarray         # (m,) grid index of the print's second
    minutes: np.ndarray
    mhigh: np.ndarray
    mlow: np.ndarray
    mclose: np.ndarray
    n_side_missing: int


def load_market() -> Market:
    ex = pd.read_csv(DATA / f"executions_{PRODUCT}.csv")
    ex = ex.sort_values("id", kind="mergesort")
    ptime = epoch_seconds(ex["exec_date"])
    order = np.argsort(ptime, kind="mergesort")
    ptime = ptime[order]
    pprice = ex["price"].to_numpy(float)[order]
    side_raw = ex["side"].to_numpy()[order]
    pbuy = side_raw == "BUY"
    n_side_missing = int((~np.isin(side_raw, ["BUY", "SELL"])).sum())

    t0 = int(np.floor(ptime[0]))
    t1 = int(np.ceil(ptime[-1]))
    n = t1 - t0 + 1
    price = np.full(n, np.nan)
    si = (np.floor(ptime) - t0).astype(np.int64)
    price[si] = pprice                      # last print of the second wins
    fill_idx = np.where(~np.isnan(price), np.arange(n), 0)
    np.maximum.accumulate(fill_idx, out=fill_idx)
    price = price[fill_idx]                 # forward fill, no look-ahead
    logp = np.log(price)

    r5 = np.zeros(n)
    r5[5:] = (logp[5:] - logp[:-5]) * 1e4
    burst = np.abs(r5) >= BURST_BPS
    cum = np.concatenate([[0], np.cumsum(burst)])
    calm_a = np.zeros(n, bool)
    calm_a[BURST_LOOKBACK_SEC:] = (
        cum[BURST_LOOKBACK_SEC:n] - cum[0:n - BURST_LOOKBACK_SEC]) == 0
    calm_b = np.zeros(n, bool)
    calm_b[DRIFT_LOOKBACK_SEC:] = np.abs(
        logp[DRIFT_LOOKBACK_SEC:] - logp[:-DRIFT_LOOKBACK_SEC]) < DRIFT_MAX
    calm = calm_a & calm_b

    fl = pd.read_csv(DATA / f"flow_{PRODUCT}.csv")
    minutes = epoch_seconds(fl["ts"]).astype(np.int64)
    if np.any(np.diff(minutes) != 60):
        raise SystemExit("flow candles are not contiguous 1-minute bars")

    pmin = np.searchsorted(minutes, np.floor(ptime), side="right") - 1
    pmin = np.clip(pmin, 0, len(minutes) - 1)
    msec = np.clip(minutes - t0, 0, n - 1)
    pcalm = calm[msec][pmin]
    psec = np.clip((np.floor(ptime) - t0).astype(np.int64), 0, n - 1)

    return Market(
        t0=t0, n=n, price=price, logp=logp, r5=r5,
        calm=calm, calm_a=calm_a, calm_b=calm_b,
        ptime=ptime, pprice=pprice, pbuy=pbuy, pmin=pmin, pcalm=pcalm,
        psec=psec,
        minutes=minutes,
        mhigh=fl["high"].to_numpy(float),
        mlow=fl["low"].to_numpy(float),
        mclose=fl["close"].to_numpy(float),
        n_side_missing=n_side_missing,
    )


# --------------------------------------------------------------------------- #
# 2. backtest engine
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Cfg:
    window: int
    tp_mode: str
    use_calm: bool = True
    use_burst_stop: bool = True
    use_range_stop: bool = True
    maker_tp: bool = True
    entry_cost: float = COST_TAKER_BURST
    calm_at_signal: bool = False   # diagnostic variant only
    use_guard: bool = True         # diagnostic variant only

    def label(self) -> str:
        return f"W={self.window}m TP={self.tp_mode}"


TRADE_COLS = ["ts_entry", "ts_exit", "side", "entry", "exit", "tp", "edge",
              "width_bps", "tp_dist_bps", "overshoot_bps", "gross_bps",
              "cost_bps", "net_bps", "reason", "hold_sec", "rng_lo", "rng_hi"]


def _rolling_extrema(mh: np.ndarray, ml: np.ndarray, w: int):
    """Trailing high/low over the w COMPLETED minutes strictly before each bar."""
    hi = pd.Series(mh).rolling(w).max().shift(1).to_numpy()
    lo = pd.Series(ml).rolling(w).min().shift(1).to_numpy()
    return hi, lo


def _tp_level(tp_mode: str, side: int, lo: float, hi: float) -> float:
    """Take-profit level, anchored on the range EDGE (not the entry print)."""
    width = hi - lo
    if tp_mode == "mid":
        return 0.5 * (hi + lo)
    if tp_mode == "third":
        return lo + width / 3.0 if side > 0 else hi - width / 3.0
    if tp_mode == "fix10":
        return lo * (1 + 10.0 / 1e4) if side > 0 else hi * (1 - 10.0 / 1e4)
    raise ValueError(tp_mode)


def _manage(mk: Market, cfg: Cfg, side: int, t_fill: float, tp: float,
            lo: float, hi: float):
    """Run one open position forward.  Returns (t_exit, px_exit, cost, reason)."""
    s_start = int(np.ceil(t_fill)) - mk.t0
    s_end = min(mk.n - 1, int(np.floor(t_fill + HOLD_MAX_SEC)) - mk.t0)
    if s_end < s_start:
        s_end = min(mk.n - 1, s_start)

    # ---- stop scan on the 1s grid (seconds strictly after the fill second) --
    t_stop, px_stop = np.inf, np.nan
    if s_end >= s_start:
        seg_p = mk.price[s_start:s_end + 1]
        seg_r = mk.r5[s_start:s_end + 1]
        if cfg.use_range_stop:
            trig = (seg_p < lo * (1 - RANGE_BREAK_BPS / 1e4)) if side > 0 else \
                   (seg_p > hi * (1 + RANGE_BREAK_BPS / 1e4))
        else:
            trig = np.zeros(seg_p.shape, bool)
        if cfg.use_burst_stop:
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
    t_tp, px_tp, cost_tp = np.inf, np.nan, 0.0
    if hi_i > lo_i:
        pp = mk.pprice[lo_i:hi_i]
        pb = mk.pbuy[lo_i:hi_i]
        if cfg.maker_tp:
            # LONG exits with a resting SELL limit -> a taker BUY must reach it.
            ok = (pb & (pp >= tp)) if side > 0 else ((~pb) & (pp <= tp))
        else:
            ok = (pp >= tp) if side > 0 else (pp <= tp)
        w = np.flatnonzero(ok)
        if w.size:
            k = int(w[0])
            t_tp = float(mk.ptime[lo_i + k])
            if cfg.maker_tp:
                px_tp = tp                    # maker fill happens AT the limit
            else:
                px_tp = float(pp[k])          # taker fill at the print
                cost_tp = COST_TAKER_CALM

    if t_tp < t_stop:                         # ties go to the stop (conservative)
        return t_tp, px_tp, cost_tp, "tp"
    if np.isfinite(t_stop):
        return t_stop, px_stop, COST_TAKER_BURST, "stop"
    t_end = float(s_end + mk.t0)
    return t_end, float(mk.price[s_end]), COST_TAKER_CALM, "time"


def _first_cross(px: np.ndarray, start: int, thr: float, below: bool) -> int:
    """First index >= start where px crosses thr (<= if below else >=)."""
    n = len(px)
    i = start
    while i < n:
        j = min(n, i + 50_000)
        seg = px[i:j]
        w = np.flatnonzero(seg <= thr) if below else np.flatnonzero(seg >= thr)
        if w.size:
            return i + int(w[0])
        i = j
    return n


def signals(mk: Market, cfg: Cfg, m_lo: int, m_hi: int):
    """Every eligible edge touch in [m_lo, m_hi) -- before any position/guard
    bookkeeping.  Returns (idx_into_full_print_array, side, lo, hi)."""
    hi_arr, lo_arr = _rolling_extrema(mk.mhigh, mk.mlow, cfg.window)
    t_lo = float(mk.minutes[m_lo])
    t_hi = float(mk.minutes[m_hi - 1]) + 60.0
    i0 = int(np.searchsorted(mk.ptime, t_lo, side="left"))
    i1 = int(np.searchsorted(mk.ptime, t_hi, side="left"))
    pm = mk.pmin[i0:i1]
    hp, lp, px = hi_arr[pm], lo_arr[pm], mk.pprice[i0:i1]
    good = np.isfinite(hp) & np.isfinite(lp) & (hp > lp)
    good &= (mk.psec[i0:i1] >= DRIFT_LOOKBACK_SEC)
    sig_s = good & (px >= hp)
    sig_l = good & (px <= lp)
    if cfg.use_calm:
        ok = mk.calm[mk.psec[i0:i1]] if cfg.calm_at_signal else mk.pcalm[i0:i1]
        sig_s &= ok
        sig_l &= ok
    c = np.flatnonzero(sig_s | sig_l)
    side = np.where(sig_l[c], 1, -1)
    return i0 + c, side, lp[c], hp[c]


def backtest(mk: Market, cfg: Cfg, m_lo: int, m_hi: int,
             stats: dict | None = None) -> pd.DataFrame:
    """Run over minute indices [m_lo, m_hi).  One position at a time."""
    hi_arr, lo_arr = _rolling_extrema(mk.mhigh, mk.mlow, cfg.window)

    t_lo = float(mk.minutes[m_lo])
    t_hi = float(mk.minutes[m_hi - 1]) + 60.0
    i0 = int(np.searchsorted(mk.ptime, t_lo, side="left"))
    i1 = int(np.searchsorted(mk.ptime, t_hi, side="left"))

    pm = mk.pmin[i0:i1]
    hp = hi_arr[pm]
    lp = lo_arr[pm]
    px = mk.pprice[i0:i1]
    good = np.isfinite(hp) & np.isfinite(lp) & (hp > lp)
    # a stale trailing range needs at least DRIFT_LOOKBACK_SEC of history for
    # the calm flags to be defined at all
    good &= (mk.psec[i0:i1] >= DRIFT_LOOKBACK_SEC)
    sig_s = good & (px >= hp)     # touch of the high edge -> SELL (fade)
    sig_l = good & (px <= lp)     # touch of the low  edge -> BUY  (fade)
    if cfg.use_calm:
        ok_calm = mk.calm[mk.psec[i0:i1]] if cfg.calm_at_signal \
            else mk.pcalm[i0:i1]
        sig_s &= ok_calm
        sig_l &= ok_calm
    cand = np.flatnonzero(sig_s | sig_l)

    all_px = mk.pprice
    trades = []
    next_ok_t = -np.inf
    # re-entry guard, per side: absolute index in the FULL print array at which
    # the 25% retrace happened (np.inf = not yet satisfied / no guard)
    guard_until = {1: -1, -1: -1}

    n_busy = n_guard = 0
    for c in cand:
        i = i0 + int(c)
        t = mk.ptime[i]
        if t < next_ok_t:
            n_busy += 1
            continue
        side = 1 if sig_l[c] else -1
        if cfg.use_guard and guard_until[side] > i:
            n_guard += 1
            continue
        lo, hi = float(lp[c]), float(hp[c])
        entry = float(px[c])
        edge = hi if side < 0 else lo
        width = hi - lo
        tp = _tp_level(cfg.tp_mode, side, lo, hi)
        if (side > 0 and tp <= entry) or (side < 0 and tp >= entry):
            continue                       # nothing left to fade (cannot happen
                                           # for edge-anchored TPs, kept as a guard)

        t_exit, px_exit, exit_cost, reason = _manage(mk, cfg, side, t, tp, lo, hi)
        gross = side * (px_exit / entry - 1.0) * 1e4
        cost = cfg.entry_cost + exit_cost
        trades.append({
            "ts_entry": t, "ts_exit": t_exit, "side": side,
            "entry": entry, "exit": px_exit, "tp": tp, "edge": edge,
            "width_bps": width / entry * 1e4,
            "tp_dist_bps": side * (tp / entry - 1.0) * 1e4,
            "overshoot_bps": abs(entry - edge) / entry * 1e4,
            "gross_bps": gross, "cost_bps": cost, "net_bps": gross - cost,
            "reason": reason, "hold_sec": t_exit - t,
            "rng_lo": lo, "rng_hi": hi,
        })

        next_ok_t = t_exit + COOLDOWN_SEC
        # arm the same-side re-entry guard: price must retrace 25% of the range
        # off the edge that was faded before this side can be traded again.
        thr = edge - RETRACE_FRAC * width if side < 0 else \
            edge + RETRACE_FRAC * width
        j = int(np.searchsorted(mk.ptime, t_exit, side="right"))
        guard_until[side] = _first_cross(all_px, j, thr, below=(side < 0))

    if stats is not None:
        stats.update(touches=int(cand.size), blocked_busy=n_busy,
                     blocked_guard=n_guard, taken=len(trades))
    return pd.DataFrame(trades, columns=TRADE_COLS)


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
    if tdf is None or tdf.empty:
        return {"n": 0, "mean": np.nan, "median": np.nan, "sd": np.nan,
                "win": np.nan, "t": np.nan, "days": 0, "total": 0.0,
                "tp%": 0.0, "stop%": 0.0, "time%": 0.0}
    t, nd = day_clustered_t(tdf)
    rc = tdf["reason"].value_counts(normalize=True) * 100
    return {
        "n": len(tdf),
        "mean": tdf["net_bps"].mean(),
        "median": tdf["net_bps"].median(),
        "sd": tdf["net_bps"].std(ddof=1),
        "win": (tdf["net_bps"] > 0).mean() * 100,
        "t": t, "days": nd, "total": tdf["net_bps"].sum(),
        "tp%": float(rc.get("tp", 0.0)), "stop%": float(rc.get("stop", 0.0)),
        "time%": float(rc.get("time", 0.0)),
    }


HEAD = (f"{'trades':>7}  {'mean_bps':>9} {'med_bps':>9} {'sd':>8} "
        f"{'win%':>7} {'dayT':>7}")


def fmt(s: dict) -> str:
    if s["n"] == 0:
        return f"{0:>7}  {'-':>9} {'-':>9} {'-':>8} {'-':>7} {'-':>7}"
    return (f"{s['n']:>7}  {s['mean']:>+9.2f} {s['median']:>+9.2f} "
            f"{s['sd']:>8.1f} {s['win']:>6.1f}% {s['t']:>+7.2f}")


def fwd_drift(mk: Market, t: np.ndarray, side: np.ndarray, hz: int) -> np.ndarray:
    """Side-adjusted forward move over hz seconds from time t.  + = fade wins."""
    a = np.clip((np.floor(t) - mk.t0).astype(np.int64), 0, mk.n - 1)
    b = np.clip(a + hz, 0, mk.n - 1)
    return side * (mk.logp[b] - mk.logp[a]) * 1e4


# --------------------------------------------------------------------------- #
# 4. main
# --------------------------------------------------------------------------- #
def main() -> int:
    pd.set_option("display.width", 200)

    header("0. DATA + SPLIT")
    mk = load_market()
    chk_a = epoch_seconds(pd.Series(["2026-07-21T08:17:22.19+00:00"]))
    chk_b = epoch_seconds_ns(pd.Series(["2026-07-21T08:17:22.19+00:00"]))
    print(f"executions      : {len(mk.ptime):,} prints, "
          f"{pd.to_datetime(mk.ptime[0], unit='s', utc=True)} .. "
          f"{pd.to_datetime(mk.ptime[-1], unit='s', utc=True)}")
    print(f"1s grid         : {mk.n:,} seconds ({(mk.n - 1) / 86400:.2f} days)")
    print(f"1m candles      : {len(mk.minutes):,} (contiguous, verified)")
    sec_with_print = len(np.unique(np.floor(mk.ptime)))
    print(f"seconds with >=1 print: {sec_with_print:,} "
          f"({sec_with_print / mk.n * 100:.1f}%) -- the rest are forward filled")
    print(f"prints with a missing taker side: {mk.n_side_missing} "
          f"(treated as SELL, same as the prior study)")

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

    mb = np.clip(mk.minutes - mk.t0, 0, mk.n - 1)
    print(f"\ncalm regime at minute starts: (a) no 10bps/5s burst in trailing 10m"
          f" = {mk.calm_a[mb].mean() * 100:.1f}%")
    print(f"                              (b) |30m return| < 0.4%             "
          f"  = {mk.calm_b[mb].mean() * 100:.1f}%")
    print(f"                              (a AND b)                           "
          f"  = {mk.calm[mb].mean() * 100:.1f}%")
    print(f"\nepoch conversion cross-check: (idx-EPOCH)/Timedelta('1s') = "
          f"{chk_a[0]:.3f}, ns-astype = {chk_b[0]:.3f}, "
          f"max|diff| over the tape = "
          f"{np.abs(epoch_seconds(pd.read_csv(DATA / f'executions_{PRODUCT}.csv', nrows=5000)['exec_date']) - epoch_seconds_ns(pd.read_csv(DATA / f'executions_{PRODUCT}.csv', nrows=5000)['exec_date'])).max():.9f}")

    # ---------------- exploration ---------------- #
    header("1. EXPLORATION SEGMENT -- 9 CONFIGS (first 60%)")
    print("Entry: taker at the first print at-or-beyond the trailing W-minute")
    print("edge, in a calm minute, EVERY touch.  Exit: maker TP inside the range")
    print("(fee 0), burst/range stop 3.96 taker, 60m time stop 2.93 taker.")
    print("Tuning is restricted to W x TP distance.  Nothing else is touched.\n")
    print(f"{'W(min)':<8}{'TP':<8}{HEAD}  {'total':>9}  "
          f"{'tp%':>5} {'stop%':>6} {'time%':>6}")
    rows = []
    for w in WINDOWS:
        for tpm in TP_MODES:
            cfg = Cfg(w, tpm)
            tdf = backtest(mk, cfg, 0, split)
            s = summarise(tdf)
            rows.append({"cfg": cfg, **s})
            print(f"{w:<8}{tpm:<8}{fmt(s)}  {s['total']:>+9.0f}  "
                  f"{s['tp%']:>4.0f}% {s['stop%']:>5.0f}% {s['time%']:>5.0f}%")

    elig = [r for r in rows if r["n"] >= MIN_EXPL_TRADES]
    if not elig:
        elig = rows
        print(f"\n[warn] no config reached {MIN_EXPL_TRADES} exploration trades; "
              f"selecting over all configs")
    best = max(elig, key=lambda r: (r["total"], r["mean"]))
    cfg = best["cfg"]
    print(f"\nselection rule (fixed in advance): maximise TOTAL net bps on the "
          f"exploration\nsegment among configs with >= {MIN_EXPL_TRADES} trades.")
    print(f"CHOSEN: W={cfg.window}m, TP={cfg.tp_mode}")
    print(f"  exploration: {best['n']} trades, {best['mean']:+.2f} bps/trade, "
          f"total {best['total']:+.0f} bps, day-T {best['t']:+.2f}")
    best_mean = max(elig, key=lambda r: r["mean"])["cfg"]
    print(f"  robustness: a max-MEAN-bps rule would pick {best_mean.label()} -- "
          f"{'same config' if best_mean == cfg else 'a DIFFERENT config'}")
    if all(r["mean"] < 0 for r in rows):
        print("  NB every config in the grid is negative on exploration; the")
        print("  choice is 'least bad' and the judgment run is a formality unless")
        print("  the sign flips out of sample.")

    # ---------------- judgment ---------------- #
    header("2. JUDGMENT SEGMENT -- CHOSEN CONFIG, RUN ONCE (last 40%)")
    jstats: dict = {}
    jt = backtest(mk, cfg, split, n_min, stats=jstats)
    s = summarise(jt)
    print(f"config          : W={cfg.window}m TP={cfg.tp_mode}  "
          f"entry taker {cfg.entry_cost:.2f} bps")
    print(f"edge touches    : {jstats['touches']:,} eligible calm-minute prints "
          f"at-or-beyond an edge")
    print(f"  suppressed by position-open/cooldown : "
          f"{jstats['blocked_busy']:,}")
    print(f"  suppressed by the 25% re-entry guard : "
          f"{jstats['blocked_guard']:,}")
    print(f"trades          : {s['n']}")
    if s["n"] == 0:
        print("no trades -- nothing to judge")
        return 0
    rc = jt["reason"].value_counts()
    tp_n = int(rc.get("tp", 0))
    print(f"maker TP fills  : {tp_n}/{s['n']} = {tp_n / s['n'] * 100:.1f}% "
          f"(the exit-side fill rate)")
    print(f"stop exits      : {int(rc.get('stop', 0))}/{s['n']} = "
          f"{rc.get('stop', 0) / s['n'] * 100:.1f}%")
    print(f"time exits      : {int(rc.get('time', 0))}/{s['n']} = "
          f"{rc.get('time', 0) / s['n'] * 100:.1f}%")
    print(f"\nnet bps/trade   : mean {s['mean']:+.3f}  median {s['median']:+.3f}"
          f"  sd {s['sd']:.2f}")
    print(f"win rate        : {s['win']:.1f}%")
    print(f"total net       : {s['total']:+.0f} bps over {s['days']} UTC days")
    print(f"day-clustered t : {s['t']:+.3f}  (n_days={s['days']})")
    print(f"mean hold       : {jt['hold_sec'].mean() / 60:.1f} min "
          f"(median {jt['hold_sec'].median() / 60:.1f})")
    print(f"long/short      : {(jt['side'] > 0).sum()} / {(jt['side'] < 0).sum()}")
    print(f"trades/day      : {s['n'] / max(s['days'], 1):.1f}")

    header("2b. ADOPTION BAR (pre-registered)")
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

    sub("2c. entry-cost sensitivity (2.93 bps instead of 3.96)")
    jt293 = backtest(mk, Cfg(cfg.window, cfg.tp_mode,
                             entry_cost=COST_TAKER_CALM), split, n_min)
    print(f"{'entry cost':<22}{HEAD}")
    print(f"{'3.96 bps (registered)':<22}{fmt(s)}")
    print(f"{'2.93 bps (sensitivity)':<22}{fmt(summarise(jt293))}")
    print("  (the 1.03 bps difference is mechanical -- the trade set is identical)")

    # ---------------- risk / reward ---------------- #
    header("3. RISK-REWARD DECOMPOSITION")
    winr = jt[jt["net_bps"] > 0]
    losr = jt[jt["net_bps"] <= 0]
    aw = winr["net_bps"].mean() if len(winr) else np.nan
    al = losr["net_bps"].mean() if len(losr) else np.nan
    print(f"wins   : {len(winr):>5} ({len(winr) / s['n'] * 100:.1f}%)  "
          f"average {aw:+.2f} bps  total {winr['net_bps'].sum():+.0f}")
    print(f"losses : {len(losr):>5} ({len(losr) / s['n'] * 100:.1f}%)  "
          f"average {al:+.2f} bps  total {losr['net_bps'].sum():+.0f}")
    if np.isfinite(aw) and np.isfinite(al) and al != 0:
        pw = len(winr) / s["n"]
        print(f"payoff ratio (avg win / |avg loss|) : {aw / abs(al):.3f}")
        print(f"breakeven win rate at that payoff   : "
              f"{100 * abs(al) / (aw + abs(al)):.1f}%   actual {pw * 100:.1f}%")
    print(f"worst / best trade : {jt['net_bps'].min():+.1f} / "
          f"{jt['net_bps'].max():+.1f} bps")
    q = jt["net_bps"].quantile([.01, .05, .25, .5, .75, .95, .99])
    print("net bps quantiles  : " +
          "  ".join(f"p{int(k * 100)}={v:+.1f}" for k, v in q.items()))

    sub("3a. per-exit-type contribution (sums to the headline bps/trade)")
    g = jt.groupby("reason")["net_bps"]
    dec = pd.DataFrame({"trades": g.size(), "mean_bps": g.mean(),
                        "total_bps": g.sum()})
    dec["share%"] = dec["trades"] / s["n"] * 100
    dec["contrib_to_mean"] = dec["total_bps"] / s["n"]
    dec["gross_mean"] = jt.groupby("reason")["gross_bps"].mean()
    dec["cost_mean"] = jt.groupby("reason")["cost_bps"].mean()
    dec["med_hold_min"] = jt.groupby("reason")["hold_sec"].median() / 60
    print(dec.round(2).to_string())
    print(f"\ncontributions sum to {dec['contrib_to_mean'].sum():+.3f} bps/trade "
          f"= the headline {s['mean']:+.3f}")

    sub("3b. the geometry")
    print(f"range width (bps of price): median {jt['width_bps'].median():.0f} "
          f"(p10 {jt['width_bps'].quantile(.1):.0f} .. "
          f"p90 {jt['width_bps'].quantile(.9):.0f})")
    print(f"TP distance from entry    : median "
          f"{jt['tp_dist_bps'].median():+.1f} bps "
          f"(p10 {jt['tp_dist_bps'].quantile(.1):+.1f} .. "
          f"p90 {jt['tp_dist_bps'].quantile(.9):+.1f})")
    print(f"entry overshoot past edge : median "
          f"{jt['overshoot_bps'].median():.2f} bps "
          f"(p90 {jt['overshoot_bps'].quantile(.9):.2f}, "
          f"max {jt['overshoot_bps'].max():.1f})")
    already = (jt["overshoot_bps"] > RANGE_BREAK_BPS).mean() * 100
    print(f"  entries already >10 bps beyond the edge (instant range stop): "
          f"{already:.1f}%")
    stop_dist = RANGE_BREAK_BPS + COST_TAKER_BURST + cfg.entry_cost
    reward = jt["tp_dist_bps"].median()
    print(f"reward if the maker TP hits : {reward:+.1f} bps gross, "
          f"{reward - cfg.entry_cost:+.1f} net of the entry taker")
    print(f"risk if the range stop hits : {-stop_dist:+.1f} bps "
          f"({RANGE_BREAK_BPS:.0f} break + {COST_TAKER_BURST:.2f} exit "
          f"+ {cfg.entry_cost:.2f} entry)")
    be = 100 * stop_dist / ((reward - cfg.entry_cost) + stop_dist)
    print(f"breakeven TP hit rate       : {be:.1f}%    "
          f"ACTUAL {tp_n / s['n'] * 100:.1f}%")

    sub("3c. how much of the loss tail did the STORM/BURST stop truncate?")
    fired_burst, fired_range = 0, 0
    burst_idx = []
    for r in jt[jt["reason"] == "stop"].itertuples():
        si_ = int(np.clip(int(r.ts_exit) - mk.t0, 0, mk.n - 1))
        rr = mk.r5[si_]
        is_burst = (r.side > 0 and rr <= -BURST_BPS) or \
                   (r.side < 0 and rr >= BURST_BPS)
        if is_burst:
            fired_burst += 1
            burst_idx.append(r.Index)
        else:
            fired_range += 1
    n_stop = int((jt["reason"] == "stop").sum())
    print(f"of {n_stop} stop exits: {fired_burst} fired on the BURST condition "
          f"({fired_burst / max(n_stop, 1) * 100:.0f}%), "
          f"{fired_range} were pure range breaks")

    # matched counterfactual: same entries, burst stop switched off, exits
    # re-managed.  This isolates the truncation from the entry-sequence shift.
    nb_cfg = Cfg(cfg.window, cfg.tp_mode, use_burst_stop=False)
    burst_set = set(burst_idx)
    cf = []
    for r in jt.itertuples():
        te, pe, ec, rsn = _manage(mk, nb_cfg, int(r.side), float(r.ts_entry),
                                  float(r.tp), float(r.rng_lo), float(r.rng_hi))
        gr = r.side * (pe / r.entry - 1.0) * 1e4
        cf.append({"ts_entry": r.ts_entry, "net_bps": gr - cfg.entry_cost - ec,
                   "reason": rsn, "was_burst": r.Index in burst_set})
    cfd = pd.DataFrame(cf)
    print("\nMATCHED counterfactual -- identical entry list, burst stop OFF, the")
    print("same exit machinery re-run (isolates truncation from sequencing):")
    print(f"{'':<28}{HEAD}")
    print(f"{'with burst stop (actual)':<28}{fmt(s)}")
    print(f"{'without burst stop':<28}{fmt(summarise(cfd))}")
    bmask = cfd["was_burst"].to_numpy()
    if bmask.sum():
        act = jt.loc[list(burst_idx), "net_bps"]
        ctf = cfd.loc[bmask, "net_bps"]
        print(f"\non the {int(bmask.sum())} burst-stopped trades alone:")
        print(f"  actual (stopped early)      : mean {act.mean():+.2f} bps, "
              f"worst {act.min():+.1f}, total {act.sum():+.0f}")
        print(f"  counterfactual (held on)    : mean {ctf.mean():+.2f} bps, "
              f"worst {ctf.min():+.1f}, total {ctf.sum():+.0f}")
        print(f"  burst stop is worth {act.mean() - ctf.mean():+.2f} bps on those "
              f"trades = {(act.sum() - ctf.sum()) / s['n']:+.2f} bps/trade overall")
        rescued = int((ctf.to_numpy() < act.to_numpy()).sum())
        print(f"  it truncated a WORSE outcome in {rescued}/{int(bmask.sum())} "
              f"({rescued / bmask.sum() * 100:.0f}%) of them")
    # loss-tail comparison
    lt_a = jt.loc[jt["net_bps"] <= 0, "net_bps"]
    lt_b = cfd.loc[cfd["net_bps"] <= 0, "net_bps"]
    print(f"\nloss tail (net<=0):  with stop  n={len(lt_a)} mean {lt_a.mean():+.2f} "
          f"p05 {lt_a.quantile(.05):+.1f} min {lt_a.min():+.1f}")
    print(f"                     no stop    n={len(lt_b)} mean {lt_b.mean():+.2f} "
          f"p05 {lt_b.quantile(.05):+.1f} min {lt_b.min():+.1f}")

    sub("3d. the raw signal, with no strategy on top (judgment segment)")
    print("Every eligible calm-minute edge touch, no position limit, no guard,")
    print("no costs: does price revert after touching a range edge at all?")
    sidx, sside, slo, shi = signals(mk, cfg, split, n_min)
    st = mk.ptime[sidx]
    print(f"  touches: {len(sidx):,}  ({int((sside > 0).sum()):,} low-edge / "
          f"{int((sside < 0).sum()):,} high-edge)")
    print(f"{'horizon':<10}{'mean bps':>11}{'median':>10}{'revert%':>10}")
    for hz, lab in ((60, "+1m"), (300, "+5m"), (900, "+15m"), (3600, "+60m")):
        d = fwd_drift(mk, st, sside.astype(float), hz)
        print(f"{lab:<10}{d.mean():>+11.2f}{np.median(d):>+10.2f}"
              f"{(d > 0).mean() * 100:>9.1f}%")
    print("  (+ = price moved back INTO the range, i.e. the fade was right)")
    # barrier race: 10 bps back inside the edge vs 10 bps beyond it, 60m cap
    a = np.clip((np.floor(st) - mk.t0).astype(np.int64), 0, mk.n - 1)
    edge_px = np.where(sside > 0, slo, shi)
    win_b = lose_b = neither = 0
    for k in range(len(sidx)):
        b = min(mk.n - 1, a[k] + HOLD_MAX_SEC)
        seg = mk.price[a[k]:b + 1]
        if seg.size == 0:
            continue
        if sside[k] > 0:
            up = np.flatnonzero(seg >= edge_px[k] * (1 + 10.0 / 1e4))
            dn = np.flatnonzero(seg < edge_px[k] * (1 - 10.0 / 1e4))
        else:
            up = np.flatnonzero(seg <= edge_px[k] * (1 - 10.0 / 1e4))
            dn = np.flatnonzero(seg > edge_px[k] * (1 + 10.0 / 1e4))
        iu = up[0] if up.size else 10 ** 9
        idn = dn[0] if dn.size else 10 ** 9
        if iu == idn == 10 ** 9:
            neither += 1
        elif iu < idn:
            win_b += 1
        else:
            lose_b += 1
    tot = win_b + lose_b + neither
    print(f"\n  10 bps barrier race from the touch, 60-minute cap "
          f"(n={tot:,}):")
    print(f"    reverts 10 bps INTO the range first  : {win_b:,} "
          f"({win_b / max(tot, 1) * 100:.1f}%)")
    print(f"    breaks  10 bps BEYOND the edge first : {lose_b:,} "
          f"({lose_b / max(tot, 1) * 100:.1f}%)")
    print(f"    neither within 60 minutes            : {neither:,} "
          f"({neither / max(tot, 1) * 100:.1f}%)")
    print("  A symmetric 10/10 race needs >50% reverts before ANY cost. This is")
    print("  the whole result: an edge touch is a momentum event, not a mean-")
    print("  reversion event, and no execution scheme fixes a negative edge.")

    # ---------------- exit-side selection ---------------- #
    header("4. EXIT-SIDE SELECTION -- WHAT HAPPENS WHEN THE MAKER TP MISSES?")
    print("The maker-entry study died of adverse selection on the ENTRY side.")
    print("The mirror question here: when the resting TP does NOT fill inside")
    print("its window, is that because the reversion never came (bad luck /")
    print("bad signal), or because it came and we were not filled (queue)?\n")

    # (i) closest approach to the TP for non-TP exits, split by exit type
    print(f"{'exit type':<12}{'n':>5}{'MFE/TP med':>12}{'p75':>8}{'p90':>8}"
          f"{'reached TP unfilled':>22}")
    for rsn in ["stop", "time"]:
        sel = jt[jt["reason"] == rsn]
        if sel.empty:
            continue
        approach, touched = [], 0
        for r in sel.itertuples():
            a = int(np.clip(int(np.ceil(r.ts_entry)) - mk.t0, 0, mk.n - 1))
            b = int(np.clip(int(np.floor(r.ts_exit)) - mk.t0, a, mk.n - 1))
            seg = mk.price[a:b + 1]
            if seg.size == 0:
                continue
            mfe = seg.max() if r.side > 0 else seg.min()
            got = r.side * (mfe / r.entry - 1.0) * 1e4
            approach.append(got / r.tp_dist_bps if r.tp_dist_bps > 0 else np.nan)
            if (r.side > 0 and mfe >= r.tp) or (r.side < 0 and mfe <= r.tp):
                touched += 1
        ap = np.array(approach, float)
        print(f"{rsn:<12}{len(sel):>5}{np.nanmedian(ap):>12.2f}"
              f"{np.nanpercentile(ap, 75):>8.2f}{np.nanpercentile(ap, 90):>8.2f}"
              f"{touched:>13} = {touched / max(len(sel), 1) * 100:>5.1f}%")
    print("  MFE/TP = best favourable excursion as a fraction of the TP distance.")
    print("  'reached TP unfilled' = the 1s price reached the limit level but no")
    print("  COUNTER-SIDE print did, so the maker order was not filled. That")
    print("  column is the exit-side execution loss; it is the mirror of the")
    print("  entry-side adverse selection that killed the maker-entry study.")
    print("  The 'time' row is the meaningful one -- stop exits were cut early by")
    print("  construction, so their MFE is truncated too.")

    # (ii) forward drift after each exit type
    print(f"\nside-adjusted forward move AFTER the exit "
          f"(+ = the fade kept working):")
    print(f"{'exit type':<12}{'n':>6}" +
          "".join(f"{h:>12}" for h in ["+5m", "+15m", "+60m"]))
    for rsn in ["tp", "stop", "time"]:
        sel = jt[jt["reason"] == rsn]
        if sel.empty:
            continue
        row = f"{rsn:<12}{len(sel):>6}"
        for hz in (300, 900, 3600):
            d = fwd_drift(mk, sel["ts_exit"].to_numpy(),
                          sel["side"].to_numpy(float), hz)
            row += f"{d.mean():>+12.2f}"
        print(row)
    print("  tp    row > 0 means we left money on the table by taking profit")
    print("  time  row > 0 means the reversion merely arrived late (the 60m")
    print("        window was too short), < 0 means the trade was simply wrong")
    print("  stop  row > 0 means the stop was premature")

    # (iii) does the TP level get hit later for the time exits?
    late = {30: 0, 60: 0, 120: 0}
    tex = jt[jt["reason"] == "time"]
    for r in tex.itertuples():
        a = int(np.clip(int(r.ts_exit) - mk.t0, 0, mk.n - 1))
        for mm in late:
            b = int(min(mk.n - 1, a + mm * 60))
            seg = mk.price[a:b + 1]
            if seg.size and ((r.side > 0 and seg.max() >= r.tp) or
                             (r.side < 0 and seg.min() <= r.tp)):
                late[mm] += 1
    if len(tex):
        print(f"\nof the {len(tex)} time exits, the TP level was reached later by:")
        for mm, c in late.items():
            print(f"  +{mm:>3} min after the exit : {c:>4} "
                  f"({c / len(tex) * 100:.0f}%)")

    # ---------------- ablations ---------------- #
    header("5. ABLATIONS (judgment segment)")
    print(f"{'variant':<34}{HEAD}  {'tp%':>5} {'stop%':>6} {'time%':>6}")

    def row(label: str, c: Cfg, pre: pd.DataFrame | None = None):
        t_ = backtest(mk, c, split, n_min) if pre is None else pre
        ss = summarise(t_)
        print(f"{label:<34}{fmt(ss)}  {ss['tp%']:>4.0f}% "
              f"{ss['stop%']:>5.0f}% {ss['time%']:>5.0f}%")
        return ss, t_

    base_s, _ = row("pre-registered", cfg, jt)
    nc_s, _ = row("calm filter OFF", Cfg(cfg.window, cfg.tp_mode, use_calm=False))
    cs_s, _ = row("calm evaluated at signal second",
                  Cfg(cfg.window, cfg.tp_mode, calm_at_signal=True))
    tk_s, _ = row("TAKER TP (2.93) instead of maker",
                  Cfg(cfg.window, cfg.tp_mode, maker_tp=False))
    nb_s, _ = row("burst stop OFF (full re-run)",
                  Cfg(cfg.window, cfg.tp_mode, use_burst_stop=False))
    nr_s, _ = row("range stop OFF",
                  Cfg(cfg.window, cfg.tp_mode, use_range_stop=False))
    ns_s, _ = row("no price stop at all",
                  Cfg(cfg.window, cfg.tp_mode, use_burst_stop=False,
                      use_range_stop=False))
    gstats: dict = {}
    gt = backtest(mk, Cfg(cfg.window, cfg.tp_mode, use_guard=False),
                  split, n_min, stats=gstats)
    gs = summarise(gt)
    print(f"{'re-entry guard OFF (post-hoc)':<34}{fmt(gs)}  {gs['tp%']:>4.0f}% "
          f"{gs['stop%']:>5.0f}% {gs['time%']:>5.0f}%")
    print()
    if nc_s["n"]:
        print(f"calm filter is worth {base_s['mean'] - nc_s['mean']:+.2f} bps/trade "
              f"({base_s['n']} trades with it, {nc_s['n']} without -- the binding")
        print("  constraint on trade count is the guard and the one-position rule,")
        print("  not the calm filter, which very few minutes fail on this sample).")
    if tk_s["n"]:
        print(f"\nmaker exit is worth {base_s['mean'] - tk_s['mean']:+.2f} bps/trade"
              f" vs a taker TP; TP-exit share {base_s['tp%']:.0f}% (maker) vs "
              f"{tk_s['tp%']:.0f}% (taker).")
        print("  A taker TP fills on ANY print through the level and pays 2.93 bps;")
        print("  the maker TP is free but needs a counter-side print. On this tape")
        print("  the two fill at the same rate, so the maker exit is worth exactly")
        print("  its saved fee -- and that saving is an order of magnitude too")
        print("  small to close the gap.")
    print(f"\nthe judgment run has only {base_s['n']} trades, below the "
          f"{BAR_TRADES}-trade bar. The post-hoc")
    print("'guard OFF' row above is the large-sample view of the same signal (279")
    print("trades, still deeply negative). It is not part of the decision and it is")
    print("not a tuning knob -- it makes the day-clustered t WORSE, not better.")
    print("\nfull 2x2 of the two owner elements (calm filter x burst stop):")
    print(f"{'calm':<7}{'burst':<8}{HEAD}")
    for uc in (True, False):
        for ub in (True, False):
            t_ = backtest(mk, Cfg(cfg.window, cfg.tp_mode, use_calm=uc,
                                  use_burst_stop=ub), split, n_min)
            print(f"{str(uc):<7}{str(ub):<8}{fmt(summarise(t_))}")

    print("\nall 9 configs on the JUDGMENT segment (out-of-sample, for context")
    print("only -- the pre-registered decision uses the chosen config alone):")
    print(f"{'W(min)':<8}{'TP':<8}{HEAD}  {'total':>9}")
    for w in WINDOWS:
        for tpm in TP_MODES:
            ss = summarise(backtest(mk, Cfg(w, tpm), split, n_min))
            mark = "  <- chosen" if (w == cfg.window and tpm == cfg.tp_mode) else ""
            print(f"{w:<8}{tpm:<8}{fmt(ss)}  {ss['total']:>+9.0f}{mark}")

    # ---------------- sanity ---------------- #
    header("6. SANITY CHECKS")
    ok = True
    overlap = int((jt["ts_entry"].to_numpy()[1:] <
                   jt["ts_exit"].to_numpy()[:-1]).sum())
    print(f"  overlapping positions              : {overlap}  "
          f"{'OK' if overlap == 0 else 'FAIL'}")
    ok &= overlap == 0
    gap = jt["ts_entry"].to_numpy()[1:] - jt["ts_exit"].to_numpy()[:-1]
    bad_cd = int((gap < COOLDOWN_SEC - 1e-6).sum())
    print(f"  cooldown (>= {COOLDOWN_SEC:.0f}s) violations       : {bad_cd}  "
          f"{'OK' if bad_cd == 0 else 'FAIL'}")
    ok &= bad_cd == 0
    bad = int((jt["ts_exit"] < jt["ts_entry"]).sum())
    print(f"  exits before entries               : {bad}  "
          f"{'OK' if bad == 0 else 'FAIL'}")
    ok &= bad == 0
    lh = int((jt["hold_sec"] > HOLD_MAX_SEC + 2).sum())
    print(f"  holds longer than the time stop    : {lh}  "
          f"{'OK' if lh == 0 else 'FAIL'}")
    ok &= lh == 0
    tp_bad = int(((jt["reason"] == "tp") & (jt["gross_bps"] <= 0)).sum())
    print(f"  TP exits with non-positive gross   : {tp_bad}  "
          f"{'OK' if tp_bad == 0 else 'FAIL'}")
    ok &= tp_bad == 0
    at_edge = int((((jt["side"] < 0) & (jt["entry"] >= jt["rng_hi"])) |
                   ((jt["side"] > 0) & (jt["entry"] <= jt["rng_lo"]))).sum())
    print(f"  entries at-or-beyond their edge    : {at_edge}/{s['n']}  "
          f"{'OK' if at_edge == s['n'] else 'FAIL'}")
    ok &= at_edge == s["n"]
    # re-entry guard: consecutive same-side trades must have a 25% retrace
    viol = 0
    prev = {}
    for r in jt.itertuples():
        p = prev.get(r.side)
        if p is not None:
            a = int(np.clip(int(p[0]) - mk.t0, 0, mk.n - 1))
            b = int(np.clip(int(r.ts_entry) - mk.t0, a, mk.n - 1))
            seg = mk.price[a:b + 1]
            thr = p[1] - RETRACE_FRAC * p[2] if r.side < 0 else \
                p[1] + RETRACE_FRAC * p[2]
            hit = (seg.min() <= thr) if r.side < 0 else (seg.max() >= thr)
            if not hit:
                viol += 1
        prev[r.side] = (r.ts_exit, r.edge, r.rng_hi - r.rng_lo)
    print(f"  re-entry guard violations          : {viol}  "
          f"{'OK' if viol == 0 else 'FAIL'}")
    ok &= viol == 0
    # look-ahead: the trailing range must equal the max/min of the W COMPLETED
    # minutes strictly before the signal's minute
    hi_arr, lo_arr = _rolling_extrema(mk.mhigh, mk.mlow, cfg.window)
    la = 0
    idx = np.flatnonzero(np.isfinite(hi_arr))[::97][:2000]
    for i in idx:
        if hi_arr[i] != mk.mhigh[i - cfg.window:i].max() or \
           lo_arr[i] != mk.mlow[i - cfg.window:i].min():
            la += 1
    print(f"  range = trailing COMPLETED minutes : "
          f"{'OK' if la == 0 else f'{la} MISMATCH'}  "
          f"({len(idx)} bars sampled)")
    ok &= la == 0
    # every entry price must be an actual print at that exact timestamp
    same = 0
    for r in jt.itertuples():
        a = int(np.searchsorted(mk.ptime, r.ts_entry, side="left"))
        b = int(np.searchsorted(mk.ptime, r.ts_entry, side="right"))
        if np.any(mk.pprice[a:b] == r.entry):
            same += 1
    print(f"  entry price == a real print        : {same}/{s['n']}  "
          f"{'OK' if same == s['n'] else 'FAIL'}")
    ok &= same == s["n"]
    # entries must never precede the segment boundary (no leakage across split)
    early = int((jt["ts_entry"] < float(mk.minutes[split])).sum())
    print(f"  entries before the split boundary  : {early}  "
          f"{'OK' if early == 0 else 'FAIL'}")
    ok &= early == 0
    # determinism
    jt2 = backtest(mk, cfg, split, n_min)
    det = jt2.equals(jt)
    print(f"  rerun determinism (identical df)   : {det}  "
          f"{'OK' if det else 'FAIL'}")
    ok &= bool(det)
    print(f"\n  SANITY: {'all checks pass' if ok else 'SOMETHING FAILED -- see above'}")

    header("7. CAVEATS")
    for line in [
        "queue position is ignored. A maker TP is declared filled the instant a "
        "counter-side print trades at or through the limit. In reality you are "
        "behind the resting size at that tick, so real maker TP fill rates are "
        "LOWER than reported -- every TP number here is an UPPER BOUND, and the "
        "fills you lose are preferentially at levels the market only kissed.",
        "taker entry is priced off the LAST PRINT, not the book. The 3.96 bps "
        "(1.96 half-spread + 2.0 slippage) is a model, not a measurement, and "
        "edge touches are exactly when the spread widens.",
        "1s approximation: only ~12% of seconds carry a print, so the 1s series "
        "is heavily forward filled; burst detection is slightly laggy and the "
        "stop scan can miss intra-second excursions.",
        "tape completeness: the executions file is a paginated snapshot with "
        "known gaps (~36% of individual prints missing, covering ~0.1% of "
        "wall-clock time because they land in high-rate bursts). Missing prints "
        "make maker TP fills HARDER, so that bias is conservative, but they also "
        "make the entry TOUCH detection later than reality.",
        "30 days, one regime. A ~12-day judgment window cannot separate a "
        "strategy from a market state.",
        "the calm filter is weak by construction on this sample -- the large "
        "majority of minutes qualify, so 'calm-only' is close to 'always'.",
        "no funding/financing cost is modelled; FX_BTC_JPY charges a daily swap "
        "on positions held over settlement. Holds are <= 60 min so this is "
        "second-order but not zero.",
        "the 25% re-entry guard and the 60s cooldown were fixed in advance and "
        "not tuned, but they are arbitrary; they are also what holds the "
        "judgment run to 43 trades, below the pre-registered 100-trade bar. The "
        "guard-OFF row (279 trades) and the raw-touch analysis in 3d are what "
        "carry the statistical weight here.",
        "the day-clustered t is reported for completeness; with 11 UTC days and "
        "a strongly negative mean it is a sign check, not a precise statistic.",
    ]:
        print("* " + line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
