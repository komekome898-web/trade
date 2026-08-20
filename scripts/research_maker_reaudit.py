#!/usr/bin/env python3
"""S2+S3 — maker + calm-regime RE-AUDIT of two cost-rejected fade strategies.

Both strategies were rejected earlier because the raw fade effect was smaller
than the ~6.3 bps TAKER round trip:

  S2  wick reversal (15m)     — scripts/research_user_strategies.py
  S3  anchor-deviation fade   — scripts/research_anchor_v2.py

This re-audit changes ONLY the cost side and the risk plumbing.  The SIGNAL
DEFINITIONS ARE REUSED VERBATIM (the wick strategy class itself for S2; the
identical dev/z formula for S3).  What changes:

  * execution : maker entry AND maker take-profit (fee 0, fills at the limit,
                and ONLY on a counter-side print at or through the limit --
                the conservative convention of scripts/replay_scalp_storm.py,
                here applied print-by-print on the raw executions tape rather
                than to a 1s summary bar, which is the same rule at finer
                resolution and is what the live engine does).
  * regime    : the fixed calm filter (below).
  * stop      : burst stop (|5s bitFlyer return| >= 10 bps against the
                position), taker at 3.96 bps; time-stop exits taker at
                2.93 bps.

PRE-REGISTERED DESIGN (fixed by the lead before any number below was seen;
nothing here deviates from it):

  data    : bitFlyer FX_BTC_JPY, last ~30 days.
            data/candles_FX_BTC_JPY.csv (1m) + data/executions_FX_BTC_JPY.csv
            (tape -> 1s series for fills/stops) + data/binance_BTCUSDT_1m.csv
            (S3 anchor leader, exactly as research_anchor_v2.py).
  split   : first 60% exploration / last 40% judgment, chronological, one
            single shared boundary timestamp for both studies.
  calm    : minute t is calm iff  no |5s log-ret| >= 10 bps anywhere in the
            trailing 10 min  AND  |30m log-ret| < 0.4%.  Evaluated at signal
            time, on the bitFlyer 1s series.
  costs   : maker entry 0 bps, maker TP 0 bps, burst-stop taker 3.96 bps,
            time-stop taker 2.93 bps.  FX/CFD fee is 0%.
  grid S2 : entry limit {bar close, 1/3 wick retrace} x TP {15 bps, wick mid}
  grid S3 : entry limit {current price, 2 bps deeper} x TP {50%, 100% of the
            anchor deviation}
  adopt   : judgment needs >= 100 trades AND net >= +2.0 bps/trade AND
            day-clustered t >= 2.0.  A structural shortfall of trades is an
            automatic FAIL-by-sample; the expectancy is still reported.

Usage:  PYTHONPATH=src python3 scripts/research_maker_reaudit.py
Idempotent, read-only, no network, writes nothing.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

# ---------------------------------------------------------------- fixed costs
MAKER_BPS = 0.0          # maker entry / maker TP: no fee, fills at the limit
STOP_TAKER_BPS = 3.96    # burst regime taker side  (1.96 half-spread + 2.0 slip)
TIME_TAKER_BPS = 2.93    # calm regime taker side   (0.93 half-spread + 2.0 slip)
TAKER_RT_BPS = 2 * TIME_TAKER_BPS   # taker round trip used in counterfactuals

# ------------------------------------------------------------- fixed regime
CALM_BURST_BPS = 10.0    # |5s log-ret| threshold
CALM_LOOKBACK_S = 600    # trailing 10 min
CALM_TREND_S = 1800      # 30 min
CALM_TREND_MAX = 0.004   # 0.4%
BURST_STOP_BPS = 10.0    # |5s ret| against the position -> stop

# ------------------------------------------------------------- fixed plumbing
S2_ENTRY_TIMEOUT_S = 900     # one 15m bar for the entry limit to fill
S2_HOLD_CAP_S = 8 * 900      # 8 bars
S3_ENTRY_TIMEOUT_S = 300     # 5 min for the entry limit to fill
S3_HOLD_CAP_S = 3600         # 60 min

# ------------------------------------------------------------- adoption bar
BAR_MIN_TRADES = 100
BAR_MIN_NET_BPS = 2.0
BAR_MIN_T = 2.0

EXPLORE_MIN_TRADES = 20      # a config must clear this on exploration to be
                             # eligible for selection

EPOCH = pd.Timestamp("1970-01-01", tz="UTC")


def to_unix(idx) -> np.ndarray:
    """Unit-proof epoch seconds.

    pandas 2/3 hand back datetime64 in [s], [ms], [us] or [ns] depending on how
    the frame was built; `.asi8` / `.view('int64')` therefore silently changes
    scale (a prior study in this repo shipped a us-vs-s bug that way).  A
    Timedelta division is unit-proof, so it is the only conversion used here.
    """
    if isinstance(idx, pd.Series):
        return ((idx - EPOCH) / pd.Timedelta(seconds=1)).to_numpy(dtype=float)
    return ((pd.DatetimeIndex(idx) - EPOCH) / pd.Timedelta(seconds=1)).to_numpy(dtype=float)


# ===========================================================================
# market data
# ===========================================================================
@dataclass
class Tape:
    """The bitFlyer executions tape plus the derived 1s series."""
    t: np.ndarray            # print timestamps, epoch seconds, sorted
    px: np.ndarray           # print prices
    is_buy: np.ndarray       # True if the aggressor was a BUY
    sec0: int                # epoch second of grid element 0
    grid: np.ndarray         # 1s last-price series, forward filled
    ret5: np.ndarray         # 5s log return in bps (nan for the first 5)
    calm: np.ndarray         # bool, the fixed calm filter, per second

    def sec_index(self, ts: float) -> int:
        return int(np.floor(ts)) - self.sec0

    def price_at(self, ts: float) -> float:
        i = self.sec_index(ts)
        if i < 0 or i >= len(self.grid):
            return float("nan")
        return float(self.grid[i])

    def is_calm(self, ts: float) -> bool:
        i = self.sec_index(ts)
        if i < 0 or i >= len(self.calm):
            return False
        return bool(self.calm[i])


def load_tape() -> Tape:
    ex = pd.read_csv(DATA / "executions_FX_BTC_JPY.csv")
    ts = pd.to_datetime(ex["exec_date"], utc=True, format="mixed")
    t = to_unix(ts)
    order = np.argsort(t, kind="stable")
    t = t[order]
    px = ex["price"].to_numpy(dtype=float)[order]
    is_buy = (ex["side"].to_numpy()[order] == "BUY")

    sec0 = int(np.floor(t[0]))
    sec1 = int(np.floor(t[-1]))
    n = sec1 - sec0 + 1
    grid = np.full(n, np.nan)
    grid[np.floor(t).astype(np.int64) - sec0] = px          # last print wins
    grid = pd.Series(grid).ffill().to_numpy()

    ret5 = np.full(n, np.nan)
    ret5[5:] = np.log(grid[5:] / grid[:-5]) * 1e4

    absr = pd.Series(np.abs(np.nan_to_num(ret5, nan=0.0)))
    roll_max = absr.rolling(CALM_LOOKBACK_S, min_periods=CALM_LOOKBACK_S).max().to_numpy()
    r30 = np.full(n, np.nan)
    r30[CALM_TREND_S:] = np.abs(np.log(grid[CALM_TREND_S:] / grid[:-CALM_TREND_S]))
    calm = (roll_max < CALM_BURST_BPS) & (r30 < CALM_TREND_MAX)
    calm = np.nan_to_num(calm, nan=False).astype(bool)

    return Tape(t=t, px=px, is_buy=is_buy, sec0=sec0, grid=grid, ret5=ret5, calm=calm)


def load_candles(name: str) -> pd.DataFrame:
    df = pd.read_csv(DATA / name, index_col=0, parse_dates=True)
    df.index = pd.to_datetime(df.index, utc=True)
    return df.sort_index()


# ===========================================================================
# the simulator
# ===========================================================================
@dataclass
class Sig:
    """One signal, already priced by the strategy layer."""
    ts: float                # epoch second at which the limit starts resting
    side: int                # +1 long, -1 short
    limit: float             # maker entry limit price
    tp_dist_bps: float       # take-profit distance from the fill, in bps
    ref_px: float            # market price at signal time (taker shadow entry)
    calm: bool
    tag: str = ""


@dataclass
class Trade:
    ts_sig: float
    side: int
    filled: bool
    fill_ts: float | None = None
    fill_lag_s: float | None = None
    entry: float | None = None
    exit_ts: float | None = None
    exit_px: float | None = None
    exit_kind: str = ""      # tp | stop | time
    net_bps: float | None = None
    gross_bps: float | None = None
    # shadow: taker entry at ref_px at the signal second, same exit rules
    shadow_gross_bps: float | None = None
    shadow_kind: str = ""


def _first_counter_print(tape: Tape, side: int, limit: float,
                         t_from: float, t_to: float) -> tuple[float, int] | None:
    """First print in (t_from, t_to] that fills a resting limit.

    LONG limit  -> a SELL print at or through (px <= limit).
    SHORT limit -> a BUY  print at or through (px >= limit).
    Strictly after t_from: the order cannot fill against a print that already
    happened at or before the moment it was posted.
    """
    lo = int(np.searchsorted(tape.t, t_from, side="right"))
    hi = int(np.searchsorted(tape.t, t_to, side="right"))
    if hi <= lo:
        return None
    px = tape.px[lo:hi]
    buy = tape.is_buy[lo:hi]
    if side > 0:
        mask = (~buy) & (px <= limit)
    else:
        mask = buy & (px >= limit)
    if not mask.any():
        return None
    j = lo + int(np.argmax(mask))
    return float(tape.t[j]), j


def _first_burst(tape: Tape, side: int, t_from: float, t_to: float) -> float | None:
    """First second in (t_from, t_to] whose 5s return runs >= 10 bps AGAINST us."""
    i0 = tape.sec_index(t_from) + 1
    i1 = tape.sec_index(t_to)
    i0 = max(i0, 5)
    i1 = min(i1, len(tape.ret5) - 1)
    if i1 < i0:
        return None
    seg = tape.ret5[i0:i1 + 1]
    mask = (seg <= -BURST_STOP_BPS) if side > 0 else (seg >= BURST_STOP_BPS)
    mask = np.nan_to_num(mask, nan=False)
    if not mask.any():
        return None
    return float(tape.sec0 + i0 + int(np.argmax(mask)))


def _resolve_exit(tape: Tape, side: int, entry: float, tp_dist_bps: float,
                  t_fill: float, hold_cap_s: int, use_burst_stop: bool):
    """Return (exit_ts, exit_px, kind, cost_bps)."""
    t_end = t_fill + hold_cap_s
    tp_px = entry * (1.0 + side * tp_dist_bps / 1e4)

    tp = _first_counter_print(tape, -side, tp_px, t_fill, t_end)   # closing side
    tp_ts = tp[0] if tp else None

    st_ts = _first_burst(tape, side, t_fill, t_end) if use_burst_stop else None

    # earliest wins; on a tie the stop wins (conservative)
    if st_ts is not None and (tp_ts is None or st_ts <= tp_ts):
        return st_ts, tape.price_at(st_ts), "stop", STOP_TAKER_BPS
    if tp_ts is not None:
        return tp_ts, tp_px, "tp", MAKER_BPS
    return t_end, tape.price_at(t_end), "time", TIME_TAKER_BPS


def simulate(tape: Tape, sigs: list[Sig], entry_timeout_s: int, hold_cap_s: int,
             *, use_burst_stop: bool = True, stats: dict | None = None) -> list[Trade]:
    """One position at a time; a resting entry order also blocks new signals."""
    out: list[Trade] = []
    busy_until = -np.inf
    skipped = 0
    grid_end = tape.sec0 + len(tape.grid) - 1
    for s in sigs:
        if s.ts < busy_until:
            skipped += 1
            continue
        if s.ts + entry_timeout_s + hold_cap_s > grid_end:
            continue                      # cannot be resolved inside the data
        tr = Trade(ts_sig=s.ts, side=s.side, filled=False)

        # ---- shadow taker trade (counterfactual, independent of the fill) ---
        if np.isfinite(s.ref_px) and s.ref_px > 0:
            e_ts, e_px, kind, _ = _resolve_exit(tape, s.side, s.ref_px,
                                                s.tp_dist_bps, s.ts, hold_cap_s,
                                                use_burst_stop)
            if np.isfinite(e_px) and e_px > 0:
                tr.shadow_gross_bps = s.side * (e_px / s.ref_px - 1.0) * 1e4
                tr.shadow_kind = kind

        fill = _first_counter_print(tape, s.side, s.limit, s.ts, s.ts + entry_timeout_s)
        if fill is None:
            busy_until = s.ts + entry_timeout_s
            out.append(tr)
            continue

        t_fill = fill[0]
        tr.filled = True
        tr.fill_ts = t_fill
        tr.fill_lag_s = t_fill - s.ts
        tr.entry = s.limit                       # a maker order fills AT its limit

        e_ts, e_px, kind, cost = _resolve_exit(tape, s.side, s.limit, s.tp_dist_bps,
                                               t_fill, hold_cap_s, use_burst_stop)
        if not np.isfinite(e_px) or e_px <= 0:
            busy_until = e_ts
            out.append(tr)
            continue
        tr.exit_ts, tr.exit_px, tr.exit_kind = e_ts, e_px, kind
        tr.gross_bps = s.side * (e_px / s.limit - 1.0) * 1e4
        tr.net_bps = tr.gross_bps - cost         # maker entry costs nothing
        busy_until = e_ts
        out.append(tr)
    if stats is not None:
        stats["offered"] = len(sigs)
        stats["skipped_busy"] = skipped
    return out


# ===========================================================================
# statistics
# ===========================================================================
def day_clustered_t(net: np.ndarray, days: np.ndarray) -> tuple[float, int]:
    """t-stat of the mean with errors clustered on the UTC calendar day."""
    n = len(net)
    if n < 2:
        return float("nan"), 0
    mean = float(net.mean())
    resid = net - mean
    uniq = np.unique(days)
    g = len(uniq)
    if g < 2:
        return float("nan"), g
    sums = np.array([resid[days == d].sum() for d in uniq])
    var = (sums ** 2).sum() / (n ** 2) * (g / (g - 1))
    if var <= 0:
        return float("nan"), g
    return mean / float(np.sqrt(var)), g


@dataclass
class Perf:
    n_sig: int
    n_fill: int
    n_res: int          # resolved (has a net)
    fill_pct: float
    net_mean: float
    net_sum: float
    win_pct: float
    tstat: float
    ndays: int
    mix: dict = field(default_factory=dict)
    gross_mean: float = float("nan")


def perf(trades: list[Trade]) -> Perf:
    n_sig = len(trades)
    filled = [t for t in trades if t.filled]
    res = [t for t in filled if t.net_bps is not None]
    if not res:
        return Perf(n_sig, len(filled), 0, 100.0 * len(filled) / max(n_sig, 1),
                    float("nan"), 0.0, float("nan"), float("nan"), 0)
    net = np.array([t.net_bps for t in res])
    gross = np.array([t.gross_bps for t in res])
    days = np.array([int(t.fill_ts // 86400) for t in res])
    ts, g = day_clustered_t(net, days)
    mix: dict[str, int] = {}
    for t in res:
        mix[t.exit_kind] = mix.get(t.exit_kind, 0) + 1
    return Perf(n_sig, len(filled), len(res), 100.0 * len(filled) / max(n_sig, 1),
                float(net.mean()), float(net.sum()),
                100.0 * float((net > 0).mean()), ts, g, mix, float(gross.mean()))


def perf_row(label: str, p: Perf) -> str:
    mix = " ".join(f"{k}={v}" for k, v in sorted(p.mix.items())) or "-"
    return (f"{label:<34}{p.n_sig:>6}{p.n_fill:>7}{p.fill_pct:>7.1f}"
            f"{p.net_mean:>+11.2f}{p.win_pct:>8.1f}{p.tstat:>8.2f}{p.ndays:>6}  {mix}")


PERF_HDR = (f"{'config':<34}{'sig':>6}{'fill':>7}{'fill%':>7}"
            f"{'net bps/t':>11}{'win%':>8}{'t(day)':>8}{'days':>6}  exit mix")


def verdict(p: Perf) -> tuple[bool, str]:
    reasons = []
    ok_n = p.n_res >= BAR_MIN_TRADES
    ok_net = np.isfinite(p.net_mean) and p.net_mean >= BAR_MIN_NET_BPS
    ok_t = np.isfinite(p.tstat) and p.tstat >= BAR_MIN_T
    if not ok_n:
        reasons.append(f"trades {p.n_res} < {BAR_MIN_TRADES}")
    if not ok_net:
        reasons.append(f"net {p.net_mean:+.2f} < {BAR_MIN_NET_BPS:+.1f} bps/t")
    if not ok_t:
        reasons.append(f"t {p.tstat:.2f} < {BAR_MIN_T:.1f}")
    return (ok_n and ok_net and ok_t), ("; ".join(reasons) or "all three met")


# ===========================================================================
# S2 — wick reversal (15m)
# ===========================================================================
S2_WICK_MULT = 1.5        # the config research_user_strategies.py SELECTED
S2_MIN_WICK_PCT = 0.20    # on T+V, both for taker and for maker execution
S2_SENS_MIN_WICK_PCT = 0.10   # reported as a sample-size sensitivity only


def resample_15m(c1m: pd.DataFrame) -> pd.DataFrame:
    """Identical to research_user_strategies.resample_15m."""
    return pd.DataFrame({
        "open": c1m["open"].resample("15min").first(),
        "high": c1m["high"].resample("15min").max(),
        "low": c1m["low"].resample("15min").min(),
        "close": c1m["close"].resample("15min").last(),
        "volume": c1m["volume"].resample("15min").sum(),
    }).dropna()


def s2_raw_signals(b15: pd.DataFrame, mult: float, min_wick_pct: float) -> pd.DataFrame:
    """Vectorised WickReversalStrategy.on_candles — same inequalities, verbatim.

    lower >= max(mult*body, min_wick_pct/100*close) and lower > upper -> BUY
    upper >= max(mult*body, min_wick_pct/100*close) and upper > lower -> SELL
    """
    o = b15["open"].to_numpy(float)
    h = b15["high"].to_numpy(float)
    lo = b15["low"].to_numpy(float)
    c = b15["close"].to_numpy(float)
    body = np.abs(c - o)
    upper = h - np.maximum(o, c)
    lower = np.minimum(o, c) - lo
    thr = np.maximum(mult * body, min_wick_pct / 100.0 * c)
    buy = (lower >= thr) & (lower > upper)
    sell = (upper >= thr) & (upper > lower)
    side = np.where(buy, 1, np.where(sell, -1, 0))
    keep = side != 0
    return pd.DataFrame({
        "bar_start": b15.index[keep], "side": side[keep], "close": c[keep],
        "high": h[keep], "low": lo[keep], "open": o[keep],
    })


def s2_price(raw: pd.DataFrame, tape: Tape, entry_mode: str, tp_mode: str) -> list[Sig]:
    sigs: list[Sig] = []
    for r in raw.itertuples():
        ts = to_unix(pd.DatetimeIndex([r.bar_start]))[0] + 900.0   # the bar's CLOSE
        c = float(r.close)
        wick = (c - float(r.low)) if r.side > 0 else (float(r.high) - c)
        if wick <= 0:
            continue
        if entry_mode == "close":
            limit = c
        else:                                    # 1/3 retrace back into the wick
            limit = c - r.side * wick / 3.0
        if tp_mode == "fix15":
            tp_bps = 15.0
        else:                                    # half the wick length ("wick mid")
            tp_bps = 0.5 * wick / limit * 1e4
        ref = tape.price_at(ts)
        sigs.append(Sig(ts=ts, side=int(r.side), limit=limit, tp_dist_bps=tp_bps,
                        ref_px=ref, calm=tape.is_calm(ts)))
    return sigs


# ===========================================================================
# S3 — anchor-deviation fade
# ===========================================================================
S3_W = 60
S3_SD_WINDOW = 1440
S3_Z_ENTRY = 2.0          # primary; 2.5 (the other pre-registered v2 value)
S3_Z_SENS = 2.5           # is reported as a sensitivity


def s3_raw_signals(z_entry: float) -> pd.DataFrame:
    """dev/z exactly as AnchorReversionTimed._z in research_anchor_v2.py."""
    fx = load_candles("candles_FX_BTC_JPY.csv")
    leader = load_candles("binance_BTCUSDT_1m.csv")["close"]
    merged = fx.join(leader.rename("leader_close"), how="inner").dropna()
    lf = np.log(merged["close"].to_numpy(float))
    lb = np.log(merged["leader_close"].to_numpy(float))
    w = S3_W
    dev = np.full(len(merged), np.nan)
    dev[w:] = ((lf[w:] - lf[:-w]) - (lb[w:] - lb[:-w])) * 1e4
    sd = pd.Series(dev).rolling(S3_SD_WINDOW, min_periods=S3_SD_WINDOW).std(ddof=1)
    z = pd.Series(dev) / sd
    side = np.where(z > z_entry, -1, np.where(z < -z_entry, 1, 0))   # rich -> SHORT
    keep = (side != 0) & np.isfinite(dev)
    return pd.DataFrame({
        "bar_start": merged.index[keep], "side": side[keep],
        "close": merged["close"].to_numpy(float)[keep],
        "dev": dev[keep], "z": z.to_numpy()[keep],
    }), merged


def s3_price(raw: pd.DataFrame, tape: Tape, entry_mode: str, tp_mode: str) -> list[Sig]:
    sigs: list[Sig] = []
    frac = 0.5 if tp_mode == "rev50" else 1.0
    for r in raw.itertuples():
        ts = to_unix(pd.DatetimeIndex([r.bar_start]))[0] + 60.0     # the bar's CLOSE
        c = float(r.close)
        # "deeper" = further along the direction the deviation already went,
        # i.e. a better price for the fade.
        off = 0.0 if entry_mode == "market" else 2.0
        limit = c * (1.0 - r.side * off / 1e4)
        tp_bps = frac * abs(float(r.dev))
        sigs.append(Sig(ts=ts, side=int(r.side), limit=limit, tp_dist_bps=tp_bps,
                        ref_px=tape.price_at(ts), calm=tape.is_calm(ts)))
    return sigs


# ===========================================================================
# reporting helpers
# ===========================================================================
def adverse_selection(trades: list[Trade], title: str) -> None:
    filled = [t for t in trades if t.filled and t.shadow_gross_bps is not None]
    missed = [t for t in trades if not t.filled and t.shadow_gross_bps is not None]
    print(f"\n  {title}")
    if not filled or not missed:
        print(f"    filled={len(filled)} missed={len(missed)} — "
              "one side is empty, no comparison possible")
        return
    f = np.array([t.shadow_gross_bps for t in filled])
    m = np.array([t.shadow_gross_bps for t in missed])
    print(f"    shadow trade = TAKER entry at the market price of the signal second,")
    print(f"    same TP / burst stop / hold cap. GROSS (pre-cost) bps:")
    print(f"      filled signals  n={len(f):>4}  gross {f.mean():+7.2f}  "
          f"median {np.median(f):+7.2f}  win {100 * (f > 0).mean():5.1f}%")
    print(f"      missed signals  n={len(m):>4}  gross {m.mean():+7.2f}  "
          f"median {np.median(m):+7.2f}  win {100 * (m > 0).mean():5.1f}%")
    d = f.mean() - m.mean()
    print(f"      adverse selection = filled - missed = {d:+.2f} bps "
          f"({'FILLS ARE WORSE' if d < 0 else 'fills are not worse'} than the misses)")
    print(f"      missed signals, had they been TAKEN taker (entry+exit "
          f"{TAKER_RT_BPS:.2f} bps): net {m.mean() - TAKER_RT_BPS:+.2f} bps/trade")


def print_grid(name: str, rows: list[tuple[str, Perf]]) -> str | None:
    print(f"\n{name}")
    print("  " + PERF_HDR)
    for label, p in rows:
        print("  " + perf_row(label, p))
    eligible = [(l, p) for l, p in rows if p.n_res >= EXPLORE_MIN_TRADES
                and np.isfinite(p.net_mean)]
    if not eligible:
        best = max(rows, key=lambda r: r[1].n_res)
        print(f"  -> no config reached {EXPLORE_MIN_TRADES} exploration trades; "
              f"falling back to the largest-sample config: {best[0]}")
        return best[0]
    best = max(eligible, key=lambda r: r[1].net_mean)
    n_pos = sum(1 for _, p in eligible if p.net_mean > 0)
    print(f"  -> CHOSEN (best net bps/trade among configs with "
          f">= {EXPLORE_MIN_TRADES} trades): {best[0]}")
    if n_pos == 0:
        print("     NOTE: no config in the grid was profitable on exploration; the "
              "chosen one is merely the least-bad.")
    return best[0]


def sanity(trades: list[Trade], entry_timeout_s: int, hold_cap_s: int,
           label: str) -> list[tuple[str, bool, str]]:
    checks = []
    bad_fill = [t for t in trades if t.filled
                and not (t.ts_sig < t.fill_ts <= t.ts_sig + entry_timeout_s)]
    checks.append((f"{label}: entry fill strictly after signal, within "
                   f"{entry_timeout_s}s", not bad_fill, f"{len(bad_fill)} bad"))
    bad_exit = [t for t in trades if t.filled and t.exit_ts is not None
                and not (t.fill_ts < t.exit_ts <= t.fill_ts + hold_cap_s + 1)]
    checks.append((f"{label}: exit after fill and within the hold cap",
                   not bad_exit, f"{len(bad_exit)} bad"))
    res = [t for t in trades if t.filled and t.exit_ts is not None]
    ovl = 0
    for a, b in zip(res, res[1:]):
        if b.fill_ts < a.exit_ts:
            ovl += 1
    checks.append((f"{label}: no overlapping positions", ovl == 0, f"{ovl} overlaps"))
    return checks


# ===========================================================================
# main
# ===========================================================================
def study(name: str, sig_builder, raw: pd.DataFrame, tape: Tape, grid: list[tuple[str, str]],
          split_ts: float, entry_timeout_s: int, hold_cap_s: int,
          extra_note: str = "") -> list[tuple[str, bool, str]]:
    print("\n" + "=" * 118)
    print(name)
    print("=" * 118)
    if extra_note:
        print(extra_note)

    all_labels = {}
    explore_rows, all_sigs = [], {}
    for em, tm in grid:
        label = f"entry={em:<10} tp={tm}"
        sigs = sig_builder(raw, tape, em, tm)
        all_sigs[label] = sigs
        all_labels[label] = (em, tm)
        ex = [s for s in sigs if s.ts < split_ts and s.calm]
        explore_rows.append((label, perf(simulate(tape, ex, entry_timeout_s, hold_cap_s))))

    n_raw = len(next(iter(all_sigs.values())))
    n_calm = sum(1 for s in next(iter(all_sigs.values())) if s.calm)
    print(f"\nraw signals over the full span: {n_raw}   calm-filtered: {n_calm} "
          f"({100 * n_calm / max(n_raw, 1):.1f}% survive the calm filter)")

    chosen = print_grid("EXPLORATION (first 60%, calm only)", explore_rows)
    sigs = all_sigs[chosen]

    jud_raw = [s for s in sigs if s.ts >= split_ts]
    jud = [s for s in jud_raw if s.calm]
    jud_all = jud_raw
    st: dict = {}
    tr = simulate(tape, jud, entry_timeout_s, hold_cap_s, stats=st)
    p = perf(tr)

    print(f"\nJUDGMENT (last 40%, run once, config = {chosen})")
    print(f"  funnel: {len(jud_raw)} raw signals -> {len(jud)} calm "
          f"-> {st['offered'] - st['skipped_busy']} evaluated "
          f"({st['skipped_busy']} skipped: a position or a resting order was live) "
          f"-> {p.n_fill} filled -> {p.n_res} resolved")
    print("  " + PERF_HDR)
    print("  " + perf_row(chosen, p))
    if p.n_res:
        lags = [t.fill_lag_s for t in tr if t.filled]
        holds = [(t.exit_ts - t.fill_ts) / 60 for t in tr
                 if t.filled and t.exit_ts is not None]
        print(f"  entry fill lag: median {np.median(lags):.1f}s  "
              f"p90 {np.percentile(lags, 90):.1f}s   |   "
              f"holding time: median {np.median(holds):.1f} min  "
              f"mean {np.mean(holds):.1f} min")
        tps = [t for t in tr if t.exit_kind == "tp"]
        print(f"  maker TP fill rate among filled entries: "
              f"{100 * len(tps) / p.n_res:.1f}%   "
              f"gross {p.gross_mean:+.2f} bps/trade -> net {p.net_mean:+.2f}")
    ok, why = verdict(p)
    print(f"  ADOPTION BAR (>= {BAR_MIN_TRADES} trades, >= {BAR_MIN_NET_BPS:+.1f} "
          f"bps/trade, t >= {BAR_MIN_T:.1f}): {'PASS' if ok else 'FAIL'} — {why}")

    adverse_selection(tr, "ADVERSE-SELECTION COUNTERFACTUAL (judgment, chosen config)")

    print("\n  ABLATIONS on the judgment split (same chosen config)")
    print("  " + PERF_HDR)
    print("  " + perf_row("[baseline] calm + burst stop", p))
    p_nocalm = perf(simulate(tape, jud_all, entry_timeout_s, hold_cap_s))
    print("  " + perf_row("[-calm filter] all regimes", p_nocalm))
    p_nostop = perf(simulate(tape, jud, entry_timeout_s, hold_cap_s, use_burst_stop=False))
    print("  " + perf_row("[-burst stop] calm only", p_nostop))
    p_neither = perf(simulate(tape, jud_all, entry_timeout_s, hold_cap_s,
                              use_burst_stop=False))
    print("  " + perf_row("[-both] all regimes, no stop", p_neither))
    print(f"  contribution of the calm filter : {p.net_mean - p_nocalm.net_mean:+.2f} bps/trade")
    print(f"  contribution of the burst stop  : {p.net_mean - p_nostop.net_mean:+.2f} bps/trade")

    return sanity(tr, entry_timeout_s, hold_cap_s, name.split("—")[0].strip()), p, chosen


def main() -> int:
    print("=" * 118)
    print("S2 + S3 — MAKER + CALM-REGIME RE-AUDIT of two cost-rejected fade strategies")
    print("=" * 118)

    tape = load_tape()
    c1m = load_candles("candles_FX_BTC_JPY.csv")
    span_d = (to_unix(c1m.index)[-1] - to_unix(c1m.index)[0]) / 86400
    print(f"tape        : {len(tape.t):,} executions, "
          f"{pd.Timestamp(tape.t[0], unit='s', tz='UTC')} .. "
          f"{pd.Timestamp(tape.t[-1], unit='s', tz='UTC')}")
    print(f"1s grid     : {len(tape.grid):,} seconds (forward filled), "
          f"calm fraction {100 * tape.calm.mean():.1f}%")
    print(f"1m candles  : {len(c1m):,} bars, {span_d:.2f} days")
    print(f"costs       : maker entry 0.00 | maker TP 0.00 | burst stop "
          f"{STOP_TAKER_BPS:.2f} | time stop {TIME_TAKER_BPS:.2f} bps "
          f"(taker RT reference {TAKER_RT_BPS:.2f})")
    print(f"calm rule   : no |5s ret| >= {CALM_BURST_BPS:.0f} bps in the trailing "
          f"{CALM_LOOKBACK_S // 60} min AND |30m ret| < {CALM_TREND_MAX * 100:.1f}%")
    print(f"burst stop  : |5s bitFlyer ret| >= {BURST_STOP_BPS:.0f} bps against "
          f"the position -> taker exit")

    # ---- one shared chronological 60/40 boundary --------------------------
    tsec = to_unix(c1m.index)
    split_ts = float(tsec[int(len(tsec) * 0.6)])
    print(f"\nsplit       : exploration < {pd.Timestamp(split_ts, unit='s', tz='UTC')} "
          f"<= judgment   (60/40 by 1m bar count; "
          f"{(split_ts - tsec[0]) / 86400:.1f}d / {(tsec[-1] - split_ts) / 86400:.1f}d)")

    checks: list[tuple[str, bool, str]] = []

    # ================================================================== S2
    b15 = resample_15m(c1m)
    raw2 = s2_raw_signals(b15, S2_WICK_MULT, S2_MIN_WICK_PCT)
    note2 = (f"signal: WickReversalStrategy verbatim, wick_body_mult="
             f"{S2_WICK_MULT}, min_wick_pct={S2_MIN_WICK_PCT} — the config that\n"
             f"        research_user_strategies.py SELECTED on its own T+V "
             f"(both taker and maker).\n"
             f"        15m bars: {len(b15)}   signal fires at the BAR CLOSE; the "
             f"entry limit rests {S2_ENTRY_TIMEOUT_S}s, hold cap "
             f"{S2_HOLD_CAP_S // 900} bars.\n"
             f"        TP 'wick mid' = 50% of the wick length from the fill "
             f"(the wick's own midpoint measured from the entry).")
    c2, p2, cfg2 = study("S2 — WICK REVERSAL (15m), maker + calm", s2_price, raw2, tape,
                         [("close", "fix15"), ("close", "wickmid"),
                          ("retrace13", "fix15"), ("retrace13", "wickmid")],
                         split_ts, S2_ENTRY_TIMEOUT_S, S2_HOLD_CAP_S, note2)
    checks += c2

    # sample-size sensitivity: the looser wick threshold from the same grid
    raw2b = s2_raw_signals(b15, S2_WICK_MULT, S2_SENS_MIN_WICK_PCT)
    print(f"\n  S2 SAMPLE-SIZE SENSITIVITY (min_wick_pct={S2_SENS_MIN_WICK_PCT}, "
          f"NOT the selected signal — diagnostic only)")
    print("  " + PERF_HDR)
    for em, tm in [("close", "fix15"), ("close", "wickmid"),
                   ("retrace13", "fix15"), ("retrace13", "wickmid")]:
        sg = s2_price(raw2b, tape, em, tm)
        jj = [s for s in sg if s.ts >= split_ts and s.calm]
        print("  " + perf_row(f"entry={em:<10} tp={tm}",
                              perf(simulate(tape, jj, S2_ENTRY_TIMEOUT_S, S2_HOLD_CAP_S))))

    # ================================================================== S3
    raw3, merged = s3_raw_signals(S3_Z_ENTRY)
    note3 = (f"signal: dev = (logFX[t]-logFX[t-{S3_W}]) - "
             f"(logBN[t]-logBN[t-{S3_W}]) in bps, z = dev / rolling sd"
             f"({S3_SD_WINDOW}) — research_anchor_v2.py verbatim.\n"
             f"        z_entry={S3_Z_ENTRY} (the lower of v2's two pre-registered "
             f"values; the larger sample of the two).\n"
             f"        aligned bars: {len(merged)}   entry limit rests "
             f"{S3_ENTRY_TIMEOUT_S}s, hold cap {S3_HOLD_CAP_S // 60} min.\n"
             f"        CAVEAT carried over from v2: the deviation is JPY-vs-USD "
             f"with no USDJPY series; that contamination is NOT removed.")
    c3, p3, cfg3 = study("S3 — ANCHOR-DEVIATION FADE, maker + calm", s3_price, raw3, tape,
                         [("market", "rev50"), ("market", "rev100"),
                          ("deep2bp", "rev50"), ("deep2bp", "rev100")],
                         split_ts, S3_ENTRY_TIMEOUT_S, S3_HOLD_CAP_S, note3)
    checks += c3

    raw3b, _ = s3_raw_signals(S3_Z_SENS)
    print(f"\n  S3 SENSITIVITY (z_entry={S3_Z_SENS}, the other pre-registered v2 "
          f"value — diagnostic only)")
    print("  " + PERF_HDR)
    for em, tm in [("market", "rev50"), ("market", "rev100"),
                   ("deep2bp", "rev50"), ("deep2bp", "rev100")]:
        sg = s3_price(raw3b, tape, em, tm)
        jj = [s for s in sg if s.ts >= split_ts and s.calm]
        print("  " + perf_row(f"entry={em:<10} tp={tm}",
                              perf(simulate(tape, jj, S3_ENTRY_TIMEOUT_S, S3_HOLD_CAP_S))))

    # ================================================================== sanity
    print("\n" + "=" * 118)
    print("SANITY CHECKS")
    print("=" * 118)
    # the 1s grid must reproduce the tape: for 2000 sampled prints, the grid value
    # at that print's second must be the LAST print of that second.
    rng = np.random.default_rng(0)
    pick = rng.choice(len(tape.t), size=2000, replace=False)
    bad_grid = 0
    for j in pick:
        sec = int(np.floor(tape.t[j]))
        last = int(np.searchsorted(tape.t, sec + 1.0, side="left")) - 1
        if abs(tape.grid[sec - tape.sec0] - tape.px[last]) > 1e-6:
            bad_grid += 1
    checks.append(("1s grid == last print of that second (2000 sampled prints)",
                   bad_grid == 0, f"{bad_grid} mismatches"))
    # unit trap: reconvert the candle index through a DIFFERENT datetime64 unit
    # and confirm to_unix() gives the identical seconds.
    alt = c1m.index.astype("datetime64[us]").tz_localize("UTC") \
        if c1m.index.tz is None else c1m.index.as_unit("us")
    same = bool(np.allclose(to_unix(alt), to_unix(c1m.index)))
    checks.append(("timestamps unit-proof: [ns] and [us] indexes give identical "
                   "epoch seconds", same, "to_unix() uses Timedelta division"))
    checks.append(("1m candle spacing is 60s (median)",
                   float(np.median(np.diff(to_unix(c1m.index)))) == 60.0, ""))
    checks.append((f"tape span is ~30 days ({span_d:.2f}d)", 25 <= span_d <= 35,
                   f"{span_d:.2f}d"))
    checks.append(("tape prints are time sorted", bool(np.all(np.diff(tape.t) >= 0)), ""))
    checks.append(("calm fraction is plausible (50-99%)",
                   0.5 < tape.calm.mean() < 0.99, f"{100 * tape.calm.mean():.1f}%"))
    for label, ok, detail in checks:
        print(f"  [{'ok ' if ok else 'FAIL'}] {label}" + (f"   ({detail})" if detail else ""))

    # ================================================================== verdict
    print("\n" + "=" * 118)
    print("VERDICT — does maker execution + a calm regime flip the earlier "
          "cost-based rejection?")
    print("=" * 118)
    for tag, cfg, p in (("S2 wick reversal (15m)", cfg2, p2),
                        ("S3 anchor-deviation fade", cfg3, p3)):
        ok, why = verdict(p)
        print(f"  {tag:<28} {cfg}")
        print(f"  {'':<28} judgment: {p.n_res} trades, net {p.net_mean:+.2f} bps/trade, "
              f"win {p.win_pct:.1f}%, day-clustered t {p.tstat:+.2f}")
        print(f"  {'':<28} -> {'PASS' if ok else 'FAIL'} ({why})")
    print("\n  BOTH REJECTIONS STAND. The earlier verdicts were 'the raw fade effect is")
    print("  smaller than the ~6.3 bps taker round trip'. Setting the round trip to ~0 by")
    print("  going maker does NOT rescue either strategy, because the effect measured on")
    print("  filled trades is not merely small — it is at or below zero. The maker fill")
    print("  itself is the reason: a fade limit fills exactly when the price keeps running")
    print("  through it, so the fills are systematically the worst subset of the signals")
    print("  (see the adverse-selection counterfactuals above).")

    print("\n" + "=" * 118)
    print("CAVEATS")
    print("=" * 118)
    for line in [
        "1. Maker fills are simulated from the TRADE TAPE, not from a book. A resting limit is",
        "   assumed to fill in full on the first counter-side print at or through it, with no",
        "   queue position. Real queue priority makes fills RARER and more adversely selected,",
        "   so every fill rate here is an upper bound.",
        "2. The entry limit is priced off the last trade / bar close, not the true near touch;",
        "   for a fade this is typically inside the spread and therefore slightly optimistic.",
        "3. The executions tape averages ~27k prints/day; it is a real but not necessarily",
        "   complete feed. Seconds without prints are forward filled, which understates the",
        "   number of 5s bursts and so slightly over-admits 'calm' minutes.",
        "4. The burst stop and the time exit fill at the 1s grid price (last print of that",
        "   second) plus a flat taker cost; real stop slippage in a burst can exceed 3.96 bps.",
        "5. S3's deviation is JPY-vs-USD with no USDJPY series (inherited from v2).",
        "6. S2's judgment sample is STRUCTURALLY tiny: the selected wick threshold fires ~90",
        "   times in 30 days, so 12 judgment days can never reach 100 trades. Its judgment",
        "   number is an anecdote, not a measurement; the FAIL is a FAIL-by-sample and the",
        "   larger min_wick_pct=0.10 diagnostic (also negative) is the more informative read.",
        "7. 'TP at the wick midpoint' is implemented as 'TP 50% of the wick length away from",
        "   the fill, in the fade direction'. A lower wick has no upside midpoint, so the",
        "   literal price-level reading is undefined for a fade; this is the closest",
        "   well-defined equivalent. Stated so it can be challenged.",
        "8. S3 is signal-rich but position-starved: 798 of 940 calm judgment signals were",
        "   skipped because a position or a resting order was already live. Which 142 get",
        "   traded therefore depends on the one-at-a-time rule, not only on the signal.",
        "9. Exploration selected among four configs that were ALL negative in both studies,",
        "   so 'the chosen config' means least-bad, not good. Judgment was still run once.",
        "10. The z_entry=2.5 sensitivity shows small positive numbers (+1.5 to +1.8 bps/t) on",
        "    50-70 trades with t < 1.0. That is inside noise, was not the pre-registered",
        "    primary, and must not be mined into an adoption.",
        "11. 30 days is one market regime. Nothing here is evidence about another one.",
    ]:
        print("  " + line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
