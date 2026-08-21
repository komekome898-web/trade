#!/usr/bin/env python3
"""R9-L1: two elements from the owner's legacy bots, tested as pre-registered.

PRE-REGISTRATION
================
Fixed in docs/KNOWLEDGE.md sec.4 on 2026-08-21 (entries "wick-tip invalidation
line exit" and "vr regime indicator", both sourced from docs/legacy/). This
script transcribes those bars; it does not invent new ones and does not relax
them. Nothing here is adopted -- the deliverable is a verdict.

-----------------------------------------------------------------------------
H2  WICK-EXTREME INVALIDATION STOP  (from docs/legacy/katsuo_v03.py)
-----------------------------------------------------------------------------
Replace the champion's fixed 0.5% protective stop with a STRUCTURAL one.

  invalidation level = the extreme of the trailing N COMPLETED bars' wicks as
  of the fill: min(low) over bars [b-N, b-1] for a LONG, max(high) over the
  same bars for a SHORT, where b is the fill bar.
  exit = a bar CLOSES beyond the level (close < level long, close > level
  short); a wick poking through is NOT an exit.
  the level is FROZEN at entry and never trails.

KATSUO SEMANTICS, DOCUMENTED. katsuo_v03.py sets `lcprice = High[-1]` or
`Low[-1]` at the moment the signal fires -- the wick of the SIGNAL bar, i.e.
the single last completed 15m bar -- and then exits on `Close[-1]` crossing it
(lines 171/174/182/185 and 507/529). It tracks the signal bar only and freezes
it. This study generalises the count to N trailing completed bars and keeps the
freeze. Under the engine's taker path the decision is made on bar b-1 and the
fill happens at bar b's open, so the window [b-N, b-1] ENDS EXACTLY ON THE
SIGNAL BAR: at N=1 this study is katsuo's rule verbatim. Bar b itself is
excluded because its range is unknown when the position fills at its open.

  Family (exhaustive, nothing added later):  N in {3, 6, 12} on 1m bars.
  Everything else frozen: xborder_momentum k=30, thr_pct=0.8, exit_pct=0.05,
  taker both ways, allow_short=True, no take-profit, no max_hold.

  Engine: additive extension stop_mode="wick_invalidation" / stop_window_bars,
  mirroring how exit_execution="maker_tp" was added (src/bot/backtest/engine.py,
  new tests in tests/test_wick_stop.py; the default path stays bit-identical,
  which that file's last two tests pin down).

  Data / splits
    (a) 210d PROXY  data/binance_BTCUSDT_1m_full.csv as BOTH traded instrument
        and its own leader (leader_close == close), FX_BTC_JPY cost model.
        Chronological 60/20/20 train/val/OOS via bot.backtest.walk_forward.
        SELECTION HAPPENS ON TRAIN ONLY: highest net expectancy per trade among
        family members with >= 30 trades; ties broken by lower maxDD.
    (b) 30d REAL    data/candles_FX_BTC_JPY.csv inner-joined with the real
        Binance BTCUSDT leader, exactly as scripts/research_mainbot_exits.py
        wires it. Confirmation only; no selection happens there.
  The CURRENT config (fixed 0.5% stop) is reported as the baseline on every
  split that any candidate is reported on.

  ADOPTION RULE (fixed, KNOWLEDGE.md sec.4 / report k's rule): propose the
  change ONLY if the winner beats CURRENT on BOTH val and OOS net expectancy
  AND its OOS net expectancy is > 0. Otherwise: keep the fixed 0.5% stop.
  Also reported either way: exit mix (how often the structural stop fires vs
  the signal exit, against CURRENT's ~1-in-5 stop rate measured in report k)
  and maxDD.

-----------------------------------------------------------------------------
H3  vr REGIME INDICATOR  (from docs/legacy/matilda_v52.py)
-----------------------------------------------------------------------------
  vr = (rolling 60m high-low range) / (mean |1m close-open| over 60m)

matilda computes `vola = mean(candlelen)` over vola_count bars with
`candlelen = |Close - Open|`, `range_width = max(High) - min(Low)` over
range_count bars, and `vr = range_width / vola` (lines 1103-1114). Large vr =
one-sided trend, small vr = range. Transcribed here onto 1m bars with both
windows set to 60 minutes. Both rolling windows END ON THE REFERENCE BAR and
use completed bars only; the forward-looking storm flag is strictly (t, t+H],
so no window used to decide ever extends past the decision point.

H3(a) STORM-PRECURSOR TEST  (bars from report h: lift >= 2.0 AND recall >= 0.10
      AND >= 30 storms on the evaluation segment)
  Framework: scripts/research_storm.py machinery imported verbatim through
  scripts/research_storm_b.py's pattern -- storm minute |30m log-return| >=
  0.8%, event = first storm minute after >= 2h clean, horizons 2h / 6h, the
  same eval_feature() metric code.

  Conditions (exhaustive, exactly three):
    V1  vr in its TOP quintile      vr >= q80(TRAIN)
    V2  vr in its BOTTOM quintile   vr <= q20(TRAIN)
    V3  vr RISING                   vr[t] > vr[t-60]      (no threshold)
  q20/q80 are estimated on the TRAIN segment and on nothing else.

  EVALUATION-WINDOW DISCIPLINE (report h). The 210d anchor spans 2026-01-22 ..
  2026-08-20 and divides into two very different provenances:
    * 2026-05-22 .. 2026-08-20 (the 90d file) is the segment phase A
      (scripts/research_storm.py) SELECTED on -- its section 7 scans storm rate
      by UTC hour-of-day, and the clock window 12:30-15:00 that later became
      bot.radar.StormRadar was read off exactly that scan. This segment is
      BURNED for anything clock- or regime-shaped and cannot carry a verdict.
    * 2026-01-24 .. 2026-05-22 is report h's PRIMARY window. Report h EVALUATED
      pre-registered features there but SELECTED nothing there -- every G1..G7
      threshold was transcribed from the brief before the run. No study has
      ever chosen a configuration on it.
  So this study splits report h's PRIMARY window chronologically:
    TRAIN 2026-01-24 .. 2026-03-24  (thresholds q20/q80 only; then burned)
    EVAL  2026-03-24 .. 2026-05-22  (judgment, run ONCE, reported as it comes)
  TRAIN precedes EVAL, so the thresholds are causal as well as pre-registered.
  The burned 90d segment is printed as a SUPPLEMENTARY read only, flagged, and
  cannot change the verdict.

H3(b) CHAMPION-TRADE FILTER
  Backtest the champion on 30d real + 210d proxy, bucket its trades by the vr
  quartile at entry (quartile cutoffs estimated on the EXPLORATION segment and
  on nothing else), report expectancy and maxDD per bucket.

  Family (exactly two members, both registered before looking at judgment):
    Q4-only  entries restricted to the TOP vr quartile     (trend regime)
    Q1-only  entries restricted to the BOTTOM vr quartile  (calm-range regime)
  SELECTION happens ONCE, on the PRIMARY (30d real) exploration segment: higher
  net expectancy per trade among members with >= 5 trades, ties broken by lower
  maxDD (tournament rule, scripts/research_tournament.py). Fallback to the 210d
  exploration segment only if neither member reaches 5 trades on the primary
  exploration segment.

  JUDGMENT (run once, primary judgment segment): the filter becomes a CANDIDATE
  only if the selected subset beats the FULL set on BOTH net expectancy per
  trade AND maxDD, with subset n >= 20 (tournament match rule). The 210d proxy's
  judgment segment is run with the SAME selected member and printed as ranking
  support; per the tournament precedent the degenerate self-proxy never decides
  a verdict. Per-bucket tables for all four quartiles are printed on both sets
  and on both segments, so a bucket that was not the selected member is still
  visible as a diagnostic (a diagnostic stays a diagnostic --
  research-protocol sec.8.2).

-----------------------------------------------------------------------------
Costs (repo-measured constants, research-protocol sec.3)
  taker per side 3.2bps = spread 0.0235%/2 + slippage 0.02%; fees 0% both
  sides; swap 0.06%/day on carried positions; notional 110,000 JPY.

Sanity gates (all must pass before any number is read)
  * REPRODUCTION: the champion's full-30d row must reproduce
    scripts/research_mainbot_exits.py's CURRENT 30d row trade-for-trade
    (28 trades, +108.4977478769954 JPY/trade).
  * NO LOOK-AHEAD: one entry hand-recomputed from raw arrays; one wick level
    hand-recomputed from raw arrays and proved to use only bars strictly before
    the fill; the vr feature proved to be shift-invariant under a 31-minute lag
    guard (report i's tautology test).
  * DETERMINISM: identical config + data -> bit-identical result.
  * EPOCH UNITS: the datetime64 -> seconds conversion cross-checked (the trap
    in research-protocol sec.6).
  * NO OVERLAPPING POSITIONS.

Run: PYTHONPATH=src python scripts/research_legacy_elements.py
Idempotent. Writes nothing. Commits nothing. Adopts nothing.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import numpy as np                                          # noqa: E402
import pandas as pd                                         # noqa: E402

import research_storm as A                                  # noqa: E402
from bot.backtest.engine import CostModel, run_backtest     # noqa: E402
from bot.backtest.walk_forward import split_data            # noqa: E402
from bot.strategy.xborder_momentum import XborderMomentumStrategy  # noqa: E402

DATA = ROOT / "data"

# --- frozen entry + cost model (identical to research_mainbot_exits.py) ------
K = 30
THR_PCT = 0.8
EXIT_PCT = 0.05
CURRENT_SL_PCT = 0.5
FX_COSTS = CostModel(taker_fee_pct=0.0, maker_fee_pct=0.0,
                     slippage_pct=0.02, spread_pct=0.0235)
TAKER_SIDE = (FX_COSTS.spread_pct / 2 + FX_COSTS.slippage_pct) / 100
SWAP_DAILY_PCT = 0.06
NOTIONAL = 110000.0
INITIAL_EQUITY = 200000.0

# --- H2 family --------------------------------------------------------------
WICK_N = (3, 6, 12)
H2_MIN_TRADES_TRAIN = 30

# --- H3 constants -----------------------------------------------------------
VR_WINDOW = 60                 # minutes, both numerator and denominator
VR_RISE_LAG = 60               # "rising" = above its own 60m-ago value
TAUTOLOGY_LAG = A.STORM_WINDOW_MIN + 1     # 31m: pushes the whole vr window
                                           # outside any forward event's window
VR_TRAIN = (pd.Timestamp("2026-01-24", tz="UTC"), pd.Timestamp("2026-03-24", tz="UTC"))
VR_EVAL = (pd.Timestamp("2026-03-24", tz="UTC"), pd.Timestamp("2026-05-22", tz="UTC"))
VR_SUPP = (pd.Timestamp("2026-05-22", tz="UTC"), pd.Timestamp("2026-08-21", tz="UTC"))

EXPLORE_FRAC = 0.60
H3B_MIN_TRADES_SELECT = 5
H3B_MIN_TRADES_JUDGMENT = 20

EXIT_REASONS = ("signal", "stop_loss", "take_profit", "time_exit", "maker_tp", "wick_stop")

# reproduction gate, read off scripts/research_mainbot_exits.py (CURRENT, 30d real)
GATE_TRADES = 28
GATE_EXPECTANCY_JPY = 108.4977478769954


def line(c: str = "-", n: int = 104) -> None:
    print(c * n)


def header(t: str) -> None:
    print()
    line("=", 104)
    print(t)
    line("=", 104)


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
def _load(name: str) -> pd.DataFrame:
    df = pd.read_csv(DATA / name, index_col=0, parse_dates=True)
    df.index = pd.to_datetime(df.index, utc=True)
    return df


def make_real() -> pd.DataFrame:
    """30d real bitFlyer FX_BTC_JPY traded, real Binance BTCUSDT leader.

    Same inner join as research_mainbot_exits.make_real_frame(); the UTC index
    is kept (that script drops it) and the reproduction gate proves the engine
    result is unchanged by keeping it.
    """
    fx = _load("candles_FX_BTC_JPY.csv")
    leader = _load("binance_BTCUSDT_1m_full.csv")["close"]
    return fx.join(leader.rename("leader_close"), how="inner").dropna()


def make_proxy() -> pd.DataFrame:
    """210d Binance BTCUSDT as both traded instrument and its own leader."""
    df = _load("binance_BTCUSDT_1m_full.csv")[
        ["open", "high", "low", "close", "volume"]].dropna().copy()
    df["leader_close"] = df["close"]
    return df


def load_anchor() -> pd.DataFrame:
    """210d Binance 1m on a strict clock grid (research_storm_b.load_anchor)."""
    df = pd.read_csv(DATA / "binance_BTCUSDT_1m_full.csv",
                     parse_dates=["open_time"]).set_index("open_time").sort_index()
    df = df[~df.index.duplicated(keep="first")]
    full = pd.date_range(df.index[0], df.index[-1], freq="1min", tz="UTC")
    gaps = len(full) - len(df)
    df = df.reindex(full)
    for c in ("volume", "quote_volume", "n_trades", "taker_buy_base"):
        if c in df.columns:
            df[c] = df[c].fillna(0.0)
    df[["open", "high", "low", "close"]] = df[["open", "high", "low", "close"]].ffill()
    df.index.name = "ts"
    span = (df.index[-1] - df.index[0]).total_seconds() / 86400.0
    print(f"  binance 1m anchor: {df.index[0]} .. {df.index[-1]}  rows={len(df)}  "
          f"span={span:.1f}d  filled_gaps={gaps}")
    return df


def epoch_seconds(idx: pd.DatetimeIndex) -> np.ndarray:
    """research-protocol sec.6: the only safe datetime64 -> seconds conversion."""
    epoch = pd.Timestamp("1970-01-01", tz="UTC")
    return ((idx - epoch) / pd.Timedelta("1s")).to_numpy(dtype=float)


def split_60_40(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    cut = int(len(df) * EXPLORE_FRAC)
    return df.iloc[:cut], df.iloc[cut:]


# ---------------------------------------------------------------------------
# vr
# ---------------------------------------------------------------------------
def compute_vr(df: pd.DataFrame, window: int = VR_WINDOW) -> pd.Series:
    """vr = (rolling high-low range) / (mean |close - open|), both over `window`
    bars ENDING ON the reference bar. Completed bars only: the reference bar is
    the one whose close the decision is taken on, and nothing later enters."""
    hh = df["high"].rolling(window, min_periods=window).max()
    ll = df["low"].rolling(window, min_periods=window).min()
    body = (df["close"] - df["open"]).abs()
    vola = body.rolling(window, min_periods=window).mean()
    return (hh - ll) / vola.replace(0.0, np.nan)


# ---------------------------------------------------------------------------
# Backtest runner
# ---------------------------------------------------------------------------
def run_champion(data: pd.DataFrame, *, wick_n: int | None = None,
                 entry_mask=None):
    """The champion, optionally with the structural stop and/or an entry mask.

    wick_n=None -> CURRENT config (fixed 0.5% protective stop).
    """
    kw: dict = {}
    if wick_n is None:
        kw["stop_loss_pct"] = CURRENT_SL_PCT
    else:
        kw["stop_mode"] = "wick_invalidation"
        kw["stop_window_bars"] = wick_n
    if entry_mask is not None:
        kw["entry_mask"] = entry_mask
    return run_backtest(
        XborderMomentumStrategy({"k": K, "thr_pct": THR_PCT, "exit_pct": EXIT_PCT}),
        data, costs=FX_COSTS, execution="taker", allow_short=True,
        swap_daily_pct=SWAP_DAILY_PCT, order_notional_jpy=NOTIONAL,
        initial_equity_jpy=INITIAL_EQUITY, **kw)


def cfg_name(wick_n: int | None) -> str:
    return "CURRENT sl=0.5% fixed" if wick_n is None else f"wick N={wick_n:<2d} (no fixed sl)"


# ---------------------------------------------------------------------------
# Trade-level analytics
# ---------------------------------------------------------------------------
def round_trips(res, data: pd.DataFrame) -> list[dict]:
    """Pair each OPEN_* with its CLOSE_*; attach timestamps and the decision bar."""
    trips, pending = [], None
    for ev in res.trade_log:
        if ev["side"].startswith("OPEN_"):
            pending = ev
        elif ev["side"].startswith("CLOSE_"):
            assert pending is not None, "CLOSE without a matching OPEN"
            long = pending["side"] == "OPEN_LONG"
            trips.append({
                "entry_bar": pending["bar"], "exit_bar": ev["bar"],
                # taker path: the signal that opened at bar b was decided at b-1
                "decision_bar": pending["bar"] - 1,
                "side": "LONG" if long else "SHORT",
                "reason": ev.get("reason", "signal"),
                "pnl": ev["pnl"], "pct": ev["pnl"] / NOTIONAL * 100,
                "entry_ts": data.index[pending["bar"]],
                "exit_ts": data.index[ev["bar"]],
                "hold_bars": ev["bar"] - pending["bar"],
            })
            pending = None
    assert len(trips) == len(res.trade_pnls), "round-trip pairing lost a trade"
    return trips


def subset_dd_pct(pnls) -> float:
    """maxDD of a SUBSET of trades: drawdown of realised equity, trade by trade,
    from the same starting equity the engine uses. Comparable across subsets,
    and comparable to the full set computed the same way -- it is NOT the
    engine's bar-level maxDD (which also carries unrealised PnL)."""
    eq = np.concatenate([[INITIAL_EQUITY], INITIAL_EQUITY + np.cumsum(np.asarray(pnls, float))])
    peak = np.maximum.accumulate(eq)
    return float(np.max((peak - eq) / peak) * 100) if len(eq) else 0.0


def day_cluster_t(trips: list[dict]) -> tuple[float, int]:
    """t over UTC-day clusters of per-trade net % (research-protocol sec.4)."""
    if not trips:
        return float("nan"), 0
    df = pd.DataFrame({"day": [t["entry_ts"].normalize() for t in trips],
                       "pct": [t["pct"] for t in trips]})
    daily = df.groupby("day")["pct"].mean().to_numpy()
    d = len(daily)
    if d < 2 or daily.std(ddof=1) == 0:
        return float("nan"), d
    return float(daily.mean() / (daily.std(ddof=1) / np.sqrt(d))), d


HDR = (f"{'config':<26} {'n':>4s} {'net%/t':>9s} {'JPY/t':>9s} {'win%':>6s} {'PF':>6s} "
       f"{'maxDD%':>7s} {'totPnL':>9s} {'clust t':>8s} {'days':>5s}")


def row(label: str, res, data: pd.DataFrame) -> dict:
    m = res.metrics
    trips = round_trips(res, data)
    t, ndays = day_cluster_t(trips)
    n = m.num_trades
    return {"label": label, "n": n,
            "pct": m.expectancy_per_trade_jpy / NOTIONAL * 100 if n else 0.0,
            "jpy": m.expectancy_per_trade_jpy, "win": m.win_rate_pct,
            "pf": m.profit_factor, "dd": m.max_drawdown_pct,
            "total": m.total_pnl_jpy, "t": t, "ndays": ndays,
            "mix": {r: sum(1 for x in trips if x["reason"] == r) for r in EXIT_REASONS},
            "trips": trips}


def fmt_row(r: dict) -> str:
    t = f"{r['t']:+.2f}" if np.isfinite(r["t"]) else "  n/a"
    return (f"{r['label']:<26} {r['n']:4d} {r['pct']:+9.4f} {r['jpy']:+9.1f} "
            f"{r['win']:6.1f} {r['pf']:6.2f} {r['dd']:7.2f} {r['total']:+9.0f} "
            f"{t:>8s} {r['ndays']:5d}")


def mix_line(r: dict) -> str:
    n = max(r["n"], 1)
    parts = [f"{k}={r['mix'][k]}({r['mix'][k] / n * 100:.0f}%)"
             for k in EXIT_REASONS if r["mix"][k]]
    return "      exit mix: " + (", ".join(parts) if parts else "(no closed trades)")


# ---------------------------------------------------------------------------
# SANITY GATES
# ---------------------------------------------------------------------------
def sanity_gates(real: pd.DataFrame, anchor: pd.DataFrame, vr_anchor: pd.Series) -> None:
    header("SANITY GATES  (all must pass before any result below is read)")

    # (1) reproduction gate ---------------------------------------------------
    res = run_champion(real)
    m = res.metrics
    print(f"  [gate 1] REPRODUCTION -- champion on the FULL 30d real set: "
          f"trades={m.num_trades}  expectancy={m.expectancy_per_trade_jpy:.10f} JPY/trade")
    print(f"           research_mainbot_exits.py CURRENT 30d row:           "
          f"trades={GATE_TRADES}  expectancy={GATE_EXPECTANCY_JPY:.10f} JPY/trade")
    assert m.num_trades == GATE_TRADES, "REPRODUCTION GATE FAILED (trade count)"
    assert abs(m.expectancy_per_trade_jpy - GATE_EXPECTANCY_JPY) < 1e-9, \
        "REPRODUCTION GATE FAILED (expectancy)"
    print("           PASS -- trade-for-trade identical baseline.")

    # (2) no look-ahead: hand-recompute the first entry -----------------------
    opens_, leader = real["open"].to_numpy(), real["leader_close"].to_numpy()
    lows_, highs_, closes_ = (real["low"].to_numpy(), real["high"].to_numpy(),
                              real["close"].to_numpy())
    ev = next(t for t in res.trade_log if t["side"].startswith("OPEN_"))
    b, sig = ev["bar"], ev["bar"] - 1
    mom = float(np.log(leader[sig] / leader[sig - K]))
    want = "OPEN_LONG" if mom > THR_PCT / 100 else "OPEN_SHORT"
    px = FX_COSTS.buy_price(opens_[b]) if want == "OPEN_LONG" else FX_COSTS.sell_price(opens_[b])
    assert want == ev["side"] and abs(px - ev["price"]) < 1e-9, "look-ahead check FAILED"
    print(f"  [gate 2] NO LOOK-AHEAD (entry) -- leader mom {mom * 100:+.3f}% over {K} bars "
          f"decided at bar {sig}\n"
          f"           -> {ev['side']} filled at bar {b} open {opens_[b]:.1f} "
          f"(cost-adjusted {ev['price']:.4f}). PASS -- decision strictly precedes fill.")

    # (2b) hand-recompute one wick level --------------------------------------
    N = 6
    wres = run_champion(real, wick_n=N)
    wtrips = round_trips(wres, real)
    stopped = next((t for t in wtrips if t["reason"] == "wick_stop"), None)
    assert stopped is not None, "no wick_stop fired on the 30d set -- cannot hand-check"
    b = stopped["entry_bar"]
    lvl = (float(lows_[b - N:b].min()) if stopped["side"] == "LONG"
           else float(highs_[b - N:b].max()))
    # the level must sit strictly before the fill bar, and the exit bar's
    # PREVIOUS close must be the first close beyond it
    x = stopped["exit_bar"]
    beyond = (closes_[x - 1] < lvl) if stopped["side"] == "LONG" else (closes_[x - 1] > lvl)
    assert beyond, "hand-check FAILED: the bar before the exit did not close beyond the level"
    inner = closes_[b:x - 1]
    early = ((inner < lvl) if stopped["side"] == "LONG" else (inner > lvl))
    assert not early.any(), "hand-check FAILED: an earlier close was already beyond the level"
    print(f"  [gate 2b] NO LOOK-AHEAD (wick level) -- {stopped['side']} filled at bar {b}; "
          f"level = {'min(low)' if stopped['side'] == 'LONG' else 'max(high)'} over bars "
          f"[{b - N}, {b - 1}] = {lvl:.1f}\n"
          f"           first close beyond it is bar {x - 1} (close {closes_[x - 1]:.1f}); "
          f"exit fills at bar {x} open. PASS -- window ends strictly before the fill bar, "
          f"exit strictly after the breach.")

    # (2c) vr tautology guard --------------------------------------------------
    v = vr_anchor.to_numpy()
    ok = np.isfinite(v)
    print(f"  [gate 2c] vr FEATURE -- defined on {int(ok.sum())}/{len(v)} anchor minutes, "
          f"first at {anchor.index[int(np.argmax(ok))]},\n"
          f"           median {np.nanmedian(v):.2f}, p05 {np.nanpercentile(v, 5):.2f}, "
          f"p95 {np.nanpercentile(v, 95):.2f}. Window = {VR_WINDOW} completed bars ending on "
          f"the reference bar;\n"
          f"           section H3(a) additionally re-measures every condition with a "
          f"{TAUTOLOGY_LAG}m lag so the whole vr window falls outside any forward "
          f"event's 30m definition window (report i's test).\n"
          f"           In H3(b) vr is read at the DECISION bar and the position fills at "
          f"the NEXT bar's open, so\n           every bar in the window closed strictly "
          f"before the action it conditions.")

    # (3) determinism ----------------------------------------------------------
    a1, a2 = run_champion(real, wick_n=12), run_champion(real, wick_n=12)
    assert a1.metrics.as_dict() == a2.metrics.as_dict() and a1.trade_pnls == a2.trade_pnls
    v1 = compute_vr(real)
    v2 = compute_vr(real)
    assert v1.equals(v2)
    print("  [gate 3] DETERMINISM -- identical config + data -> bit-identical rerun "
          "(engine and vr). PASS")

    # (4) epoch units ----------------------------------------------------------
    secs = epoch_seconds(real.index[:3])
    print(f"  [gate 4] EPOCH UNITS -- {real.index[0]} -> {secs[0]:.0f}s -> "
          f"{pd.Timestamp(secs[0], unit='s', tz='UTC')} (step {secs[1] - secs[0]:.0f}s "
          f"= 1m bars). PASS")

    # (5) no overlapping positions --------------------------------------------
    for t1, t2 in zip(wtrips, wtrips[1:]):
        assert t2["entry_bar"] >= t1["exit_bar"], "overlapping positions"
    assert all(t["hold_bars"] >= 1 for t in wtrips), "zero-length trade"
    print(f"  [gate 5] POSITION OVERLAP -- none across {len(wtrips)} wick-mode trades "
          f"(entries never precede the prior exit; min hold "
          f"{min(t['hold_bars'] for t in wtrips)} bars). PASS")


# ---------------------------------------------------------------------------
# H2
# ---------------------------------------------------------------------------
def study_h2(real: pd.DataFrame, proxy: pd.DataFrame) -> None:
    header("H2  WICK-EXTREME INVALIDATION STOP (katsuo)  --  family N in {3, 6, 12}")
    print(f"  entry FROZEN: k={K} thr={THR_PCT}% exit_pct={EXIT_PCT}%, taker both ways, "
          f"shorts allowed")
    print(f"  CURRENT baseline: fixed {CURRENT_SL_PCT}% protective stop, no TP, no max_hold")
    print(f"  costs: taker {TAKER_SIDE * 100:.4f}%/side (~3.2bps), round trip ~6.35bps, "
          f"swap {SWAP_DAILY_PCT}%/day, notional {NOTIONAL:.0f} JPY")

    splits = split_data(proxy)
    print(f"\n  [data] 210d proxy: {len(proxy)} bars {proxy.index[0]} .. {proxy.index[-1]}")
    print(f"         train={len(splits.training)}  val={len(splits.validation)}  "
          f"oos={len(splits.out_of_sample)}  (60/20/20 chronological)")
    print(f"  [data] 30d real  : {len(real)} bars {real.index[0]} .. {real.index[-1]} "
          f"({len(real) / 1440:.1f}d)")

    # ---- baseline on every split -------------------------------------------
    print("\n--- CURRENT baseline on every 210d-proxy split ---")
    print("  " + HDR)
    cur = {}
    for name, seg in (("train", splits.training), ("val", splits.validation),
                      ("oos", splits.out_of_sample)):
        cur[name] = row(f"CURRENT / {name}", run_champion(seg), seg)
        print("  " + fmt_row(cur[name]))
        print(mix_line(cur[name]))

    # ---- family on TRAIN: selection happens here and only here --------------
    print(f"\n--- FAMILY on TRAIN (selection segment; rule = highest net expectancy/trade "
          f"among members with >= {H2_MIN_TRADES_TRAIN} trades, ties by lower maxDD) ---")
    print("  " + HDR)
    print("  " + fmt_row(cur["train"]) + "   <= CURRENT")
    train_rows = {}
    for n_bars in WICK_N:
        r = row(f"wick N={n_bars} / train", run_champion(splits.training, wick_n=n_bars),
                splits.training)
        train_rows[n_bars] = r
        print("  " + fmt_row(r))
        print(mix_line(r))

    elig = [n for n in WICK_N if train_rows[n]["n"] >= H2_MIN_TRADES_TRAIN]
    print(f"\n  eligible (>= {H2_MIN_TRADES_TRAIN} train trades): "
          f"{elig if elig else '(none)'}")
    if not elig:
        elig = list(WICK_N)
        print("  rule exhausted -> all members eligible (stated, not silently relaxed)")
    chosen = sorted(elig, key=lambda n: (-train_rows[n]["pct"], train_rows[n]["dd"]))[0]
    print(f"  SELECTED: N={chosen}  "
          f"(train net {train_rows[chosen]['pct']:+.4f}%/trade, "
          f"maxDD {train_rows[chosen]['dd']:.2f}%)")

    # ---- plateau diagnostic (research-protocol sec.4.4) ---------------------
    order = list(WICK_N)
    i = order.index(chosen)
    nb = [order[j] for j in (i - 1, i + 1) if 0 <= j < len(order)]
    print(f"  plateau check (neighbours {nb} on train): " + ", ".join(
        f"N={n}: {train_rows[n]['pct']:+.4f}%/t "
        f"({(train_rows[n]['pct'] - train_rows[chosen]['pct']) * 100:+.1f}bps vs winner)"
        for n in nb))
    print("  NOTE: the family has 3 members by pre-registration, so 'plateau' here is a "
          "1-step read, not the 24-cell surface report l used. Reported, not weighted.")

    # ---- val, then OOS once -------------------------------------------------
    print("\n--- VALIDATION (210d proxy) ---")
    print("  " + HDR)
    val_chosen = row(f"wick N={chosen} / val", run_champion(splits.validation, wick_n=chosen),
                     splits.validation)
    print("  " + fmt_row(cur["val"]) + "   <= CURRENT")
    print("  " + fmt_row(val_chosen))
    print(mix_line(val_chosen))

    print("\n--- OUT-OF-SAMPLE, run ONCE (210d proxy) ---")
    print("  " + HDR)
    oos_chosen = row(f"wick N={chosen} / oos", run_champion(splits.out_of_sample, wick_n=chosen),
                     splits.out_of_sample)
    print("  " + fmt_row(cur["oos"]) + "   <= CURRENT")
    print("  " + fmt_row(oos_chosen))
    print(mix_line(oos_chosen))

    # ---- adoption rule ------------------------------------------------------
    beats_val = val_chosen["jpy"] > cur["val"]["jpy"]
    beats_oos = oos_chosen["jpy"] > cur["oos"]["jpy"]
    oos_pos = oos_chosen["jpy"] > 0
    print("\n--- ADOPTION RULE (fixed, KNOWLEDGE.md sec.4) ---")
    print(f"  beats CURRENT on VAL net expectancy : {beats_val}  "
          f"({val_chosen['jpy']:+.1f} vs {cur['val']['jpy']:+.1f} JPY/trade)")
    print(f"  beats CURRENT on OOS net expectancy : {beats_oos}  "
          f"({oos_chosen['jpy']:+.1f} vs {cur['oos']['jpy']:+.1f} JPY/trade)")
    print(f"  OOS net expectancy > 0              : {oos_pos}  "
          f"({oos_chosen['jpy']:+.1f} JPY/trade)")
    h2_pass = beats_val and beats_oos and oos_pos
    print(f"  H2 VERDICT: {'PASS -- propose to the lead' if h2_pass else 'FAIL'} "
          f"-- {'all three conditions met' if h2_pass else 'keep the fixed 0.5% stop'}")

    # ---- 30d real confirmation ---------------------------------------------
    print("\n--- 30d REAL bitFlyer confirmation (no selection happens here) ---")
    print("  " + HDR)
    real_cur = row("CURRENT / real30d", run_champion(real), real)
    print("  " + fmt_row(real_cur) + "   <= CURRENT")
    print(mix_line(real_cur))
    real_rows = {}
    for n_bars in WICK_N:
        r = row(f"wick N={n_bars} / real30d", run_champion(real, wick_n=n_bars), real)
        real_rows[n_bars] = r
        print("  " + fmt_row(r) + ("   <= SELECTED" if n_bars == chosen else ""))
        print(mix_line(r))

    # ---- exit mix vs report k's ~1-in-5 stop rate ---------------------------
    print("\n--- EXIT MIX: how often does the protective stop actually fire? ---")
    print("  report k measured the CURRENT config ending ~20% of real trades on the "
          "0.5% stop; the\n  structural stop replaces exactly that leg.")
    print(f"  {'dataset / config':<34}{'n':>5}{'stop-type exits':>18}{'signal exits':>15}"
          f"{'stop share':>12}{'maxDD%':>9}")
    line()

    def mix_report(tag: str, r: dict) -> None:
        n = max(r["n"], 1)
        stop = r["mix"]["stop_loss"] + r["mix"]["wick_stop"]
        print(f"  {tag:<34}{r['n']:>5}{stop:>18}{r['mix']['signal']:>15}"
              f"{stop / n * 100:>11.1f}%{r['dd']:>9.2f}")

    mix_report("30d real  / CURRENT", real_cur)
    for n_bars in WICK_N:
        mix_report(f"30d real  / wick N={n_bars}", real_rows[n_bars])
    proxy_cur_full = row("CURRENT / proxy-full", run_champion(proxy), proxy)
    proxy_chosen_full = row(f"wick N={chosen} / proxy-full",
                            run_champion(proxy, wick_n=chosen), proxy)
    mix_report("210d proxy/ CURRENT", proxy_cur_full)
    mix_report(f"210d proxy/ wick N={chosen}", proxy_chosen_full)

    # ---- mechanism ----------------------------------------------------------
    print("\n--- MECHANISM: what the structural stop changes about a trade ---")
    print("  Both legs are reported separately, because a change in where the stop sits "
          "moves BOTH:\n  it changes the average of the trades it cuts, and it changes "
          "which trades survive to be\n  exited by the signal. A row that improves one leg "
          "at the other's expense is a different\n  object from one that improves both, and "
          "only the second is evidence about the level.")

    def mech(tag: str, r: dict, stop_reason: str) -> None:
        trips = r["trips"]
        if not trips:
            return
        st = [t["pct"] for t in trips if t["reason"] == stop_reason]
        sg = [t["pct"] for t in trips if t["reason"] == "signal"]
        hold = float(np.mean([t["hold_bars"] for t in trips]))
        print(f"  {tag:<22} mean hold {hold:5.1f} bars | stop leg n={len(st):3d} "
              f"mean {(np.mean(st) if st else float('nan')):+.4f}% | signal leg "
              f"n={len(sg):3d} mean {(np.mean(sg) if sg else float('nan')):+.4f}%")

    mech("30d real / CURRENT", real_cur, "stop_loss")
    for n_bars in WICK_N:
        mech(f"30d real / wick N={n_bars}", real_rows[n_bars], "wick_stop")


# ---------------------------------------------------------------------------
# H3(a)
# ---------------------------------------------------------------------------
def study_h3a(anchor: pd.DataFrame, vr: pd.Series) -> None:
    header("H3(a)  vr AS A STORM PRECURSOR (matilda)  --  conditions V1 / V2 / V3")
    idx = anchor.index

    storm_min, events = A.build_storms(anchor["close"])
    n_days = (idx[-1] - idx[0]).total_seconds() / 86400.0
    print(f"  storm minute : |{A.STORM_WINDOW_MIN}m log-return| >= "
          f"{A.STORM_THRESHOLD * 100:.1f}%   (imported verbatim from research_storm.py)")
    print(f"  dedup        : first storm minute after >= {A.STORM_DEDUP_MIN}m clean")
    print(f"  storm minutes: {int(storm_min.sum())} of {len(idx)} "
          f"({100 * storm_min.mean():.2f}%)")
    print(f"  storm EVENTS : {len(events)} over {n_days:.1f} days "
          f"({len(events) / n_days * 7:.1f}/week)")
    print(f"  bars         : lift >= {A.ADOPT_LIFT}, recall >= {A.ADOPT_RECALL}, "
          f">= {A.ADOPT_MIN_EVENTS} storms, horizons "
          f"{'/'.join(f'{h // 60}h' for h in A.HORIZONS)}")

    train = (idx >= VR_TRAIN[0]) & (idx < VR_TRAIN[1])
    ev_seg = (idx >= VR_EVAL[0]) & (idx < VR_EVAL[1])
    supp = (idx >= VR_SUPP[0]) & (idx < VR_SUPP[1])

    v = vr.to_numpy()
    defined = np.isfinite(v)

    # ---- thresholds from TRAIN only ----------------------------------------
    tv = v[train & defined]
    q20, q80 = float(np.percentile(tv, 20)), float(np.percentile(tv, 80))
    print(f"\n--- THRESHOLDS, estimated on TRAIN and on nothing else ---")
    print(f"  TRAIN {VR_TRAIN[0].date()} .. {VR_TRAIN[1].date()}  "
          f"({int((train & defined).sum())} defined minutes)")
    print(f"    vr q20 = {q20:.3f}   vr median = {np.median(tv):.3f}   vr q80 = {q80:.3f}")
    print(f"  EVAL  {VR_EVAL[0].date()} .. {VR_EVAL[1].date()}   -- judgment, run ONCE")
    print(f"  SUPP  {VR_SUPP[0].date()} .. {VR_SUPP[1].date()}   -- the segment phase A "
          f"selected the clock window on; SUPPLEMENTARY ONLY, cannot carry a verdict")
    print("  NOTE (report h sec.2b's threshold semantics): the cutoffs are FROZEN from TRAIN, "
          "so the\n  realized duty on EVAL is only ~20% if vr is stationary across the two "
          "segments. The duty%\n  column below is the honest realized figure, not the nominal "
          "one; read lift against it.")

    rise = np.zeros(len(v), dtype=bool)
    rise[VR_RISE_LAG:] = (v[VR_RISE_LAG:] > v[:-VR_RISE_LAG])
    rise &= defined
    rise[:VR_RISE_LAG] = False
    conds = {
        "V1 vr top quintile": (v >= q80) & defined,
        "V2 vr bottom quintile": (v <= q20) & defined,
        "V3 vr rising (vs 60m ago)": rise,
    }
    avail = {"V1 vr top quintile": defined, "V2 vr bottom quintile": defined,
             "V3 vr rising (vs 60m ago)": defined & np.r_[np.zeros(VR_RISE_LAG, bool),
                                                          defined[:-VR_RISE_LAG]]}

    def guard(sig: np.ndarray) -> np.ndarray:
        """report i's tautology test: read the condition TAUTOLOGY_LAG minutes
        earlier, so its whole vr window sits outside every forward event's own
        30m definition window."""
        out = np.zeros(len(sig), dtype=bool)
        out[TAUTOLOGY_LAG:] = sig[:-TAUTOLOGY_LAG]
        return out

    def evaluate(seg: np.ndarray, seg_name: str, lag: bool = False) -> dict:
        print(f"\n[{seg_name}{'  (+' + str(TAUTOLOGY_LAG) + 'm tautology guard)' if lag else ''}]"
              f"  {int(seg.sum())} minutes")
        out = {}
        for H in A.HORIZONS:
            fwd = A.event_flag_forward(idx, events, H)
            print(f"  horizon {H // 60}h")
            print(f"    {'condition':<28}{'duty%':>8}{'P(storm|ON)':>13}{'base':>9}"
                  f"{'lift':>8}{'recall':>9}{'caught/ev':>12}{'med_lead':>10}{'ON min':>9}"
                  f"{'episodes':>10}")
            line("-", 104)
            for name, sig in conds.items():
                s = guard(sig) if lag else sig
                mask = seg & avail[name]
                if lag:
                    mask = mask & guard(avail[name])
                m = A.eval_feature(s, fwd, mask, idx, events, H)
                run = s & mask
                eps = int(np.flatnonzero(run & ~np.r_[False, run[:-1]]).size)
                out[(name, H)] = m
                p_on = "-" if not np.isfinite(m["p_on"]) else f"{m['p_on'] * 100:.2f}%"
                lift = "-" if not np.isfinite(m["lift"]) else f"{m['lift']:.2f}"
                lead = "-" if not np.isfinite(m["med_lead"]) else f"{m['med_lead']:.0f}m"
                print(f"    {name:<28}{m['duty']:>8.2f}{p_on:>13}{m['base'] * 100:>8.2f}%"
                      f"{lift:>8}{m['recall']:>9.3f}"
                      f"{str(m['caught']) + '/' + str(m['n_events']):>12}{lead:>10}"
                      f"{m['n_on']:>9}{eps:>10}")
        return out

    print("\n--- TRAIN segment (construction sanity only; no verdict is taken here) ---")
    evaluate(train, "TRAIN")

    print("\n--- EVAL segment: JUDGMENT, run ONCE, reported as it came out ---")
    res_eval = evaluate(ev_seg, "EVAL")

    print("\n--- EVAL segment under the tautology guard (sanity, not the verdict) ---")
    res_guard = evaluate(ev_seg, "EVAL", lag=True)

    print("\n--- SUPPLEMENTARY: the burned 90d segment (phase A selected the clock there) ---")
    evaluate(supp, "SUPP-90d")

    # ---- verdict ------------------------------------------------------------
    print("\n--- H3(a) ADOPTION RULE (report h bars, EVAL segment) ---")
    print(f"  {'condition':<28}{'lift2h':>8}{'lift6h':>8}{'rec2h':>8}{'rec6h':>8}"
          f"{'events':>8}   verdict")
    line()
    passed = []
    for name in conds:
        m2, m6 = res_eval[(name, 120)], res_eval[(name, 360)]
        lift_ok = (m2["lift"] >= A.ADOPT_LIFT) or (m6["lift"] >= A.ADOPT_LIFT)
        rec_ok = ((m2["lift"] >= A.ADOPT_LIFT and m2["recall"] >= A.ADOPT_RECALL)
                  or (m6["lift"] >= A.ADOPT_LIFT and m6["recall"] >= A.ADOPT_RECALL))
        ev_ok = m2["n_events"] >= A.ADOPT_MIN_EVENTS
        ok = bool(lift_ok and rec_ok and ev_ok)
        why = []
        if not lift_ok:
            why.append(f"lift < {A.ADOPT_LIFT} at both horizons")
        if lift_ok and not rec_ok:
            why.append(f"recall < {A.ADOPT_RECALL} on the qualifying horizon")
        if not ev_ok:
            why.append(f"only {m2['n_events']} storms in mask (< {A.ADOPT_MIN_EVENTS})")
        if ok:
            passed.append(name)
        l2 = f"{m2['lift']:.2f}" if np.isfinite(m2["lift"]) else "-"
        l6 = f"{m6['lift']:.2f}" if np.isfinite(m6["lift"]) else "-"
        print(f"  {name:<28}{l2:>8}{l6:>8}{m2['recall']:>8.3f}{m6['recall']:>8.3f}"
              f"{m2['n_events']:>8}   {'PASS' if ok else 'FAIL -- ' + ', '.join(why)}")
    print(f"\n  qualifying conditions: {', '.join(passed) if passed else '(none)'}")
    tail = ("candidate(s) generated" if passed else
            "vr does not predict storm onset on the evaluation segment "
            "under the pre-registered bars")
    print(f"  H3(a) VERDICT: {'PASS' if passed else 'FAIL'} -- {tail}")

    print("\n  tautology cross-check (same conditions read "
          f"{TAUTOLOGY_LAG}m earlier, 2h horizon):")
    for name in conds:
        a2 = res_eval[(name, 120)]["lift"]
        g2 = res_guard[(name, 120)]["lift"]
        a_s = f"{a2:.2f}" if np.isfinite(a2) else "-"
        g_s = f"{g2:.2f}" if np.isfinite(g2) else "-"
        print(f"    {name:<28} lift as-registered {a_s:>6}  ->  lift with guard {g_s:>6}")
    print("    A large drop here would mean the condition was reading inside the storm's own\n"
          "    30m definition window (report i's failure mode) rather than ahead of it.")


# ---------------------------------------------------------------------------
# H3(b)
# ---------------------------------------------------------------------------
def bucket_table(trips: list[dict], vr_vals: np.ndarray, cuts: np.ndarray,
                 label: str) -> dict[int, list[dict]]:
    """Partition a champion run's OWN trades by the vr quartile at the decision
    bar. This is the 'subset' the tournament rule talks about: same trades, just
    split -- no re-run, no interaction with which entries survive."""
    buckets: dict[int, list[dict]] = {q: [] for q in (1, 2, 3, 4)}
    undefined = 0
    for t in trips:
        x = vr_vals[t["decision_bar"]]
        if not np.isfinite(x):
            undefined += 1
            continue
        q = int(np.searchsorted(cuts, x, side="right")) + 1   # cuts = [q25,q50,q75]
        buckets[min(q, 4)].append(t)
    allt = [t for b in buckets.values() for t in b]
    print(f"\n  [{label}] {len(allt)} trades bucketed "
          f"({undefined} dropped for undefined vr)")
    print(f"    {'bucket':<22}{'n':>5}{'net%/t':>10}{'JPY/t':>10}{'win%':>7}"
          f"{'subset maxDD%':>15}{'total%':>9}{'mean vr':>9}")
    line("-", 104)
    for q, name in ((1, "Q1 lowest vr"), (2, "Q2"), (3, "Q3"), (4, "Q4 highest vr")):
        tr = buckets[q]
        if not tr:
            print(f"    {name:<22}{0:>5}{'-':>10}{'-':>10}{'-':>7}{'-':>15}{'-':>9}{'-':>9}")
            continue
        p = np.array([t["pct"] for t in tr])
        pn = [t["pnl"] for t in tr]
        mvr = np.mean([vr_vals[t["decision_bar"]] for t in tr])
        print(f"    {name:<22}{len(tr):>5}{p.mean():>+10.4f}{np.mean(pn):>+10.1f}"
              f"{100 * (p > 0).mean():>7.1f}{subset_dd_pct(pn):>15.2f}"
              f"{p.sum():>+9.3f}{mvr:>9.2f}")
    if allt:
        p = np.array([t["pct"] for t in allt])
        pn = [t["pnl"] for t in allt]
        print(f"    {'FULL SET':<22}{len(allt):>5}{p.mean():>+10.4f}{np.mean(pn):>+10.1f}"
              f"{100 * (p > 0).mean():>7.1f}{subset_dd_pct(pn):>15.2f}{p.sum():>+9.3f}"
              f"{np.mean([vr_vals[t['decision_bar']] for t in allt]):>9.2f}")
    return buckets


MEMBERS = {"Q4-only (top vr)": 4, "Q1-only (bottom vr)": 1}


def prep_h3b(tag: str, frame: pd.DataFrame) -> dict:
    """Everything about one dataset that does not depend on which family member
    wins: split, frozen quartile cutoffs, champion runs, bucketed trades."""
    vr_full = compute_vr(frame).to_numpy()
    exp_df, jud_df = split_60_40(frame)
    cut = len(exp_df)
    vr_exp, vr_jud = vr_full[:cut], vr_full[cut:]
    cuts = np.percentile(vr_exp[np.isfinite(vr_exp)], [25, 50, 75])
    exp_res, jud_res = run_champion(exp_df), run_champion(jud_df)
    return {"tag": tag, "frame": frame, "exp_df": exp_df, "jud_df": jud_df,
            "vr_exp": vr_exp, "vr_jud": vr_jud, "cuts": cuts,
            "exp_res": exp_res, "jud_res": jud_res,
            "exp_trips": round_trips(exp_res, exp_df),
            "jud_trips": round_trips(jud_res, jud_df)}


def print_h3b_header(d: dict) -> None:
    frame, exp_df, jud_df, cuts = d["frame"], d["exp_df"], d["jud_df"], d["cuts"]
    print()
    line("=", 104)
    print(f"{d['tag']}: {len(frame)} bars {frame.index[0]} .. {frame.index[-1]} "
          f"({len(frame) / 1440:.1f}d)")
    print(f"  exploration {len(exp_df)} bars {exp_df.index[0]} .. {exp_df.index[-1]}")
    print(f"  judgment    {len(jud_df)} bars {jud_df.index[0]} .. {jud_df.index[-1]}")
    print(f"  vr quartile cutoffs from the EXPLORATION segment only: "
          f"q25={cuts[0]:.2f}  q50={cuts[1]:.2f}  q75={cuts[2]:.2f}")
    line("=", 104)


def member_stats(buckets: dict[int, list[dict]]) -> dict[str, tuple[int, float, float]]:
    out = {}
    for name, q in MEMBERS.items():
        tr = buckets[q]
        pct = float(np.mean([t["pct"] for t in tr])) if tr else float("nan")
        dd = subset_dd_pct([t["pnl"] for t in tr]) if tr else float("nan")
        out[name] = (len(tr), pct, dd)
    return out


def print_member_stats(label: str, stats: dict) -> None:
    print(f"    [{label}]")
    for name, (n, pct, dd) in stats.items():
        p = f"{pct:+.4f}%/t" if n else "n/a (no trades)"
        d = f"{dd:.2f}%" if n else "n/a"
        print(f"      {name:<24} n={n:>4}  net {p:<16}  maxDD {d}")


def judge_h3b(d: dict, pick: str, decisive: bool) -> None:
    b_jud = bucket_table(d["jud_trips"], d["vr_jud"], d["cuts"],
                         f"{d['tag']} / JUDGMENT (run once)")
    sub = b_jud[MEMBERS[pick]]
    full = [t for b in b_jud.values() for t in b]
    sub_pct = float(np.mean([t["pct"] for t in sub])) if sub else float("nan")
    full_pct = float(np.mean([t["pct"] for t in full])) if full else float("nan")
    sub_dd = subset_dd_pct([t["pnl"] for t in sub]) if sub else float("nan")
    full_dd = subset_dd_pct([t["pnl"] for t in full]) if full else float("nan")
    beats_exp = bool(np.isfinite(sub_pct) and np.isfinite(full_pct) and sub_pct > full_pct)
    beats_dd = bool(np.isfinite(sub_dd) and np.isfinite(full_dd) and sub_dd < full_dd)
    enough = len(sub) >= H3B_MIN_TRADES_JUDGMENT
    win = bool(beats_exp and beats_dd and enough)
    print(f"\n  MATCH RULE ({d['tag']}) -- selected subset {pick} vs the FULL set:")
    print(f"    net expectancy beats full set : {beats_exp}  "
          f"({sub_pct:+.4f}% vs {full_pct:+.4f}%)")
    print(f"    maxDD beats full set          : {beats_dd}  "
          f"({sub_dd:.2f}% vs {full_dd:.2f}%)")
    print(f"    subset n >= {H3B_MIN_TRADES_JUDGMENT}                : {enough}  "
          f"(n={len(sub)})")
    if decisive:
        print(f"    H3(b) VERDICT: {'CANDIDATE' if win else 'FAIL'} "
              f"-- {'all three conditions met' if win else 'no vr filter is a candidate'}")
    else:
        print("    (SECONDARY: ranking support only -- the degenerate self-proxy never "
              "decides a verdict)")

    # the same filter as an executable entry mask
    print("\n  CONSISTENCY CHECK -- the same quartile applied as a real entry_mask (engine "
          "re-run, so\n  blocked entries can let a later signal open instead; this is the "
          "EXECUTABLE form of the\n  filter, while the partition above is the pre-registered "
          "'subset'):")
    print("  " + HDR)
    print("  " + fmt_row(row("full set / judgment", d["jud_res"], d["jud_df"])) + "   <= FULL")
    vr_jud, cuts = d["vr_jud"], d["cuts"]
    qidx = np.searchsorted(cuts, np.nan_to_num(vr_jud, nan=-1.0), side="right") + 1
    for name, qq in MEMBERS.items():
        mask = np.isfinite(vr_jud) & (qidx == qq)
        r = run_champion(d["jud_df"], entry_mask=mask)
        print("  " + fmt_row(row(f"Q{qq} only / judgment", r, d["jud_df"]))
              + ("   <= SELECTED" if name == pick else ""))


def study_h3b(real: pd.DataFrame, proxy: pd.DataFrame) -> None:
    header("H3(b)  vr AS A CHAMPION-TRADE FILTER  --  family {Q4-only, Q1-only}")
    print("  Both quartile extremes were registered as a 2-member family BEFORE any"
          "\n  judgment number was produced; the exploration segment picks ONE member, and "
          "that one\n  member is then judged once on the primary judgment segment.")
    print("  Bucketing is a PARTITION of the champion's own trades by the vr quartile at "
          "the\n  DECISION bar (entry_bar - 1) -- the same information set the signal used.")
    print("  'subset maxDD%' = drawdown of realised equity trade-by-trade from the same "
          "starting\n  equity, computed identically for every subset and for the full set.")

    prim = prep_h3b("PRIMARY 30d real bitFlyer", real)
    sec = prep_h3b("SECONDARY 210d proxy", proxy)

    # ---- exploration on both sets; selection uses the primary, falling back --
    print_h3b_header(prim)
    b_prim_exp = bucket_table(prim["exp_trips"], prim["vr_exp"], prim["cuts"],
                              f"{prim['tag']} / EXPLORATION")
    print_h3b_header(sec)
    b_sec_exp = bucket_table(sec["exp_trips"], sec["vr_exp"], sec["cuts"],
                             f"{sec['tag']} / EXPLORATION")

    s_prim, s_sec = member_stats(b_prim_exp), member_stats(b_sec_exp)
    print(f"\n  SELECTION (>= {H3B_MIN_TRADES_SELECT} exploration trades, highest net "
          f"expectancy/trade, ties by lower maxDD):")
    print_member_stats("PRIMARY exploration", s_prim)
    print_member_stats("SECONDARY exploration (fallback source only)", s_sec)
    stats, src = s_prim, "PRIMARY exploration"
    elig = [n for n in MEMBERS if s_prim[n][0] >= H3B_MIN_TRADES_SELECT]
    if not elig:
        stats, src = s_sec, ("SECONDARY exploration -- no member reached "
                             f"{H3B_MIN_TRADES_SELECT} primary trades")
        elig = [n for n in MEMBERS if s_sec[n][0] >= H3B_MIN_TRADES_SELECT]
    if not elig:
        elig, src = list(MEMBERS), "rule exhausted on both sets (stated, not relaxed)"

    def key(n: str):
        pct, dd = stats[n][1], stats[n][2]
        return (-(pct if np.isfinite(pct) else -np.inf),
                dd if np.isfinite(dd) else np.inf)

    pick = sorted(elig, key=key)[0]
    print(f"    SELECTED: {pick}   (source: {src}; eligible: {elig})")

    # ---- judgment: primary decides, secondary is ranking support ------------
    judge_h3b(prim, pick, decisive=True)
    judge_h3b(sec, pick, decisive=False)


# ---------------------------------------------------------------------------
def main() -> int:
    header("R9-L1  LEGACY ELEMENTS  --  H2 wick-invalidation stop (katsuo) + "
           "H3 vr regime indicator (matilda)")
    print("  Pre-registered in docs/KNOWLEDGE.md sec.4 (2026-08-21). Verdicts only; "
          "nothing is adopted,\n  nothing is written, nothing is committed.")

    print("\n[data]")
    real = make_real()
    proxy = make_proxy()
    anchor = load_anchor()
    vr_anchor = compute_vr(anchor)
    print(f"  30d real (bitFlyer x Binance leader): {len(real)} bars "
          f"{real.index[0]} .. {real.index[-1]}")
    print(f"  210d proxy (Binance self-leader)    : {len(proxy)} bars "
          f"{proxy.index[0]} .. {proxy.index[-1]}")

    sanity_gates(real, anchor, vr_anchor)
    study_h2(real, proxy)
    study_h3a(anchor, vr_anchor)
    study_h3b(real, proxy)

    header("CAVEATS (research-protocol sec.7)")
    print("""\
  1. SINGLE REGIME on the real data. The 30d bitFlyer set is one contiguous
     regime and turns ~28 champion trades in total. Every 30d row here -- and
     especially any quartile subset of it -- describes a handful of trades.
     KNOWLEDGE.md sec.2 records repeated cases where a 21-30d winner collapsed
     on fresh data (the wick-fade family itself is one of them).
  2. PROXY DEGENERACY. The 210d set uses Binance BTCUSDT as BOTH the traded
     instrument and its own leader (leader_close == close), so it measures
     momentum-on-itself under an FX-shaped cost model. It is NOT a cross-
     exchange lag test and NOT bitFlyer data. It exists to give the exit/filter
     RANKING more than one regime and to supply enough trades for a 60/20/20
     split; it never decides the real bot's behaviour.
  3. H2's FAMILY IS SMALL BY DESIGN. Three values of N, one axis, no other
     knob. That is deliberate -- report l showed the exit surface is noise, so
     a wide grid would only manufacture a winner. The cost is that the plateau
     condition (research-protocol sec.4.4) is a one-step read here, not the
     24-cell surface report l used. It is reported, not leaned on.
  4. THE CLOSE-BEYOND STOP IS MODELLED CONSERVATIVELY, ONCE. A breach is
     detected at a bar's CLOSE and filled at the NEXT bar's open with taker
     costs -- the same next-bar-open causality the signal path uses. On 1m bars
     that is one minute of slippage the legacy 15m bot did not pay in the same
     proportion; katsuo also used a 4-stage reduce-only/stop/market exit ladder
     that this study does NOT reproduce. Only the invalidation LINE is tested.
  5. vr's WINDOW OVERLAPS NOTHING FORWARD, BUT ITS SEGMENT WAS READ ONCE.
     H3(a)'s EVAL segment is the second half of report h's PRIMARY window. No
     study ever SELECTED a configuration there, which is the property the
     pre-registration requires, but report h did evaluate G1..G7 on it -- and
     two of those (G5, G7) carried a quiet-1h-range component that is loosely
     related to vr's numerator. Those failed, so the prior read, if anything,
     biases against vr; it is still a caveat and not a clean first look.
  6. THE 90d SUPPLEMENTARY SEGMENT IS BURNED. Phase A read storm rate by UTC
     hour-of-day over exactly that stretch and the clock window came out of it.
     Its vr numbers are printed for shape only and cannot qualify anything.
  7. STORM MINUTES ARE NOT INDEPENDENT. Duty%, ON-episode counts and
     caught/events must be read together: a condition that is ON for long
     contiguous runs can post a large lift off very few independent episodes.
     Episode counts are printed next to every lift for that reason.
  8. H3(b) IS UNDERPOWERED ON THE REAL SET BY CONSTRUCTION. A 40% judgment
     segment of 30 days carries roughly a dozen champion trades, so a quartile
     subset cannot reach the 20-trade bar. That is the pre-registered rule
     working as intended (it refuses to certify a 3-trade subset), not a
     measurement failure -- but it does mean the real-data answer is "not
     shown", not "shown false".
  9. COSTS ARE THE REPO'S STANDING MEASURED CONSTANTS, not re-measured here;
     funding is modelled as a flat 0.06%/day swap rather than the real 8h
     schedule.
 10. NO ADOPTION. This script produces verdicts and, at most, candidates.
     Adoption still requires the standing pre-registered paper bars
     (KNOWLEDGE.md sec.5: main bot >= 30 paper trades, >= +0.15%/trade net,
     max DD < 10%) plus owner approval.""")

    print()
    line("=", 104)
    print("done. Nothing written, nothing committed, nothing adopted.")
    line("=", 104)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
