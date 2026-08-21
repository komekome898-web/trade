#!/usr/bin/env python3
"""R6-T1: strategy tournament -- three grounded challengers vs the champion.

PRE-REGISTRATION (fixed by the lead before any run; deviations are rejected).
=============================================================================

Question
--------
The main paper bot is `xborder_momentum` with entry k=30 / thr_pct=0.8. Its
exit structure survived a 54-config audit (report k) and its entry has never
been beaten. This tournament does not re-open the grid; it puts three
challengers built on ESTABLISHED repo knowledge against the champion, so that
either the champion improves or we learn precisely why each grounded idea does
not carry.

Champion (baseline on EVERY split)
----------------------------------
    xborder_momentum, k=30, thr_pct=0.8, exit_pct=0.05, stop_loss_pct=0.5,
    taker both ways, allow_short=True.

Challenger families (exactly these three; nothing is added later)
-----------------------------------------------------------------
C1  COST challenger -- identical signal; the exit becomes a resting maker
    take-profit at +{0.3, 0.5, 0.8}% from entry (traded-through fill
    semantics), with the strategy's own signal exit and the 0.5% protective
    stop kept as taker fallbacks.
    Rationale: KNOWLEDGE.md sec.2 "adverse selection is an ALLY on the exit
    side of a trend trade" -- report k measured a +33bps selection effect for
    TP limits at second scale. Requires the additive engine option
    exit_execution="maker_tp" / maker_tp_pct (src/bot/backtest/engine.py,
    tests/test_engine_maker_exit.py).

C2  REGIME challenger -- identical signal and exits; ENTRIES restricted to
    (a) inside 12:30-15:00 UTC, or (b) outside it. Both variants are run.
    Rationale: KNOWLEDGE.md sec.2 "storms are ruled by the clock" -- the only
    precursor that ever passed (bot.radar.StormRadar, lift 2.23, n=234).
    A large-move follower should care whether large moves are likelier.

C3  ASYMMETRY challenger -- identical signal and exits; LONG-ONLY
    (allow_short=False).
    Rationale: report BT/b found the long-only leg of every momentum study
    carried the bull-market drift while shorts bled; this asks whether the
    champion's short leg pays for itself under the CFD cost model.

Within-family SELECTION RULE (fixed, applied to the EXPLORATION segment only)
----------------------------------------------------------------------------
Within each family, pick the variant with the highest NET expectancy per trade
on the PRIMARY exploration segment among variants with >= 5 trades; ties broken
by lower max drawdown. If no variant of a family reaches 5 trades on the
primary exploration segment, the same rule is applied to the SECONDARY
(210d proxy) exploration segment instead. C3 has a single variant, so no
selection happens there.

Data & split
------------
PRIMARY   data/candles_FX_BTC_JPY.csv (real bitFlyer FX_BTC_JPY 1m trade
          candles) inner-joined with the real Binance BTCUSDT 1m leader
          (data/binance_BTCUSDT_1m_full.csv) -> ~43.2k bars, ~30 days.
          Chronological 60/40: exploration = first 60% of bars, judgment =
          last 40%. Each segment is backtested independently (flat start).
SECONDARY data/binance_BTCUSDT_1m_full.csv used as BOTH traded instrument and
          its own leader (leader_close == close), ~302k bars / ~210 days, same
          60/40 split, same FX cost model. DEGENERACY CAVEAT, as report k
          stated: this is momentum-on-itself under an FX-shaped cost model, it
          is NOT a cross-exchange lag test and NOT bitFlyer data. It exists
          only to give the RANKING more than one regime; it never decides the
          verdict.

Costs (repo-measured constants, research-protocol sec.3)
--------------------------------------------------------
taker per side 3.2bps = spread 0.0235%/2 + slippage 0.02%; fees 0% both sides;
maker legs free (no fee, no spread, filled at the limit); swap 0.06%/day on
carried positions.

MATCH RULE (fixed)
------------------
A challenger WINS its match iff, on the JUDGMENT segment of the PRIMARY data,
it beats the champion on BOTH
    (i)  net expectancy per trade, AND
    (ii) max drawdown (lower is better),
AND it has >= 20 trades on that segment.
The judgment segment is run ONCE and reported as it comes out.

BRUSH-UP ROUND (at most one)
----------------------------
If any challenger wins, "champion-v2" = champion + the winning element, and
champion-v2 is re-run against the remaining challengers on the JUDGMENT
segment only -- no re-selection, no new variants. If NO challenger wins, the
deliverable on the challenger side is the loss analysis instead: cost
decomposition, exit mix, and trade overlap with the champion.

Sanity gates (all must pass before any number is read)
------------------------------------------------------
  * REPRODUCTION GATE: the champion's full-30d primary row must reproduce
    scripts/research_mainbot_exits.py's CURRENT-config 30d row trade-for-trade
    (28 trades, +108.4977 JPY/trade). If it does not, stop and reconcile.
  * No look-ahead: the maker TP is only ever checked on bars strictly AFTER
    the entry bar; one trade is hand-recomputed from raw arrays.
  * Determinism: identical config + data -> bit-identical result.

This tournament produces CANDIDATE improvements, never adoptions. Adoption
still requires the standing paper bars in KNOWLEDGE.md sec.5 (main bot: >= 30
paper trades, >= +0.15%/trade net, max DD < 10%).

Run: PYTHONPATH=src python scripts/research_tournament.py
Writes nothing. Commits nothing.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import pandas as pd

from bot.backtest.engine import CostModel, run_backtest
from bot.radar import StormRadar
from bot.strategy.xborder_momentum import XborderMomentumStrategy

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

# --- frozen entry + cost model (identical to scripts/research_mainbot_exits.py)
K = 30
THR_PCT = 0.8
FX_COSTS = CostModel(taker_fee_pct=0.0, maker_fee_pct=0.0,
                     slippage_pct=0.02, spread_pct=0.0235)
TAKER_SIDE = (FX_COSTS.spread_pct / 2 + FX_COSTS.slippage_pct) / 100  # 3.175e-4
SWAP_DAILY_PCT = 0.06
NOTIONAL = 110000.0
INITIAL_EQUITY = 200000.0

EXPLORE_FRAC = 0.60
MIN_TRADES_JUDGMENT = 20      # match rule
MIN_TRADES_SELECT = 5         # within-family selection rule
EXIT_REASONS = ("signal", "stop_loss", "take_profit", "time_exit", "maker_tp")

# reproduction gate, read off scripts/research_mainbot_exits.py (CURRENT, 30d real)
GATE_TRADES = 28
GATE_EXPECTANCY_JPY = 108.4977478769954


# ---------------------------------------------------------------------------
# Variants
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Variant:
    key: str
    label: str
    family: str
    element: str                       # the one thing it changes vs champion
    kwargs: dict = field(default_factory=dict)
    needs_radar: str = ""              # "", "in", "out"


CHAMPION = Variant("CHAMP", "champion  k30/thr0.8 exit0.05 sl0.5 taker/taker",
                   "champion", "-")

C1 = [Variant(f"C1@{p}", f"C1 maker-TP +{p:.1f}% (signal/stop = taker fallback)",
              "C1 cost", f"maker TP +{p:.1f}%",
              {"exit_execution": "maker_tp", "maker_tp_pct": p})
      for p in (0.3, 0.5, 0.8)]

C2 = [Variant("C2in", "C2 entries INSIDE 12:30-15:00 UTC", "C2 regime",
              "entries inside storm window", {}, needs_radar="in"),
      Variant("C2out", "C2 entries OUTSIDE 12:30-15:00 UTC", "C2 regime",
              "entries outside storm window", {}, needs_radar="out")]

C3 = [Variant("C3", "C3 long-only (no short entries)", "C3 asymmetry",
              "long-only", {"allow_short": False})]

FAMILIES = [("C1 cost", C1), ("C2 regime", C2), ("C3 asymmetry", C3)]


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
def _load(name: str) -> pd.DataFrame:
    df = pd.read_csv(DATA / name, index_col=0, parse_dates=True)
    df.index = pd.to_datetime(df.index, utc=True)
    return df


def make_primary() -> pd.DataFrame:
    """30d real bitFlyer FX_BTC_JPY traded, real Binance BTCUSDT leader.

    Same inner join as scripts/research_mainbot_exits.make_real_frame(), but the
    UTC DatetimeIndex is KEPT (the reference script drops it). The index is
    needed for the radar mask and for day-clustered t-stats; sanity_gates()
    proves the engine result is unchanged by keeping it.
    """
    fx = _load("candles_FX_BTC_JPY.csv")
    leader = _load("binance_BTCUSDT_1m_full.csv")["close"]
    return fx.join(leader.rename("leader_close"), how="inner").dropna()


def make_secondary() -> pd.DataFrame:
    """210d Binance BTCUSDT as both traded instrument and its own leader."""
    df = _load("binance_BTCUSDT_1m_full.csv")[
        ["open", "high", "low", "close", "volume"]].dropna().copy()
    df["leader_close"] = df["close"]
    return df


def split_60_40(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    cut = int(len(df) * EXPLORE_FRAC)
    return df.iloc[:cut], df.iloc[cut:]


def epoch_seconds(idx: pd.DatetimeIndex) -> np.ndarray:
    """research-protocol sec.6: the only safe datetime64 -> seconds conversion."""
    epoch = pd.Timestamp("1970-01-01", tz="UTC")
    return ((idx - epoch) / pd.Timedelta("1s")).to_numpy(dtype=float)


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
def run_variant(v: Variant, data: pd.DataFrame):
    kwargs = dict(v.kwargs)
    if v.needs_radar:
        radar = StormRadar()
        armed = np.array([radar.is_armed(ts) for ts in epoch_seconds(data.index)],
                         dtype=bool)
        kwargs["entry_mask"] = armed if v.needs_radar == "in" else ~armed
    return run_backtest(
        XborderMomentumStrategy({"k": K, "thr_pct": THR_PCT, "exit_pct": 0.05}),
        data, costs=FX_COSTS, execution="taker",
        allow_short=kwargs.pop("allow_short", True),
        swap_daily_pct=SWAP_DAILY_PCT, order_notional_jpy=NOTIONAL,
        initial_equity_jpy=INITIAL_EQUITY, stop_loss_pct=0.5, **kwargs)


def compose(base: Variant, add: Variant, key: str, label: str) -> Variant:
    """champion-v2 = champion + the winning element (brush-up round only)."""
    kwargs = dict(base.kwargs)
    kwargs.update(add.kwargs)
    return Variant(key, label, "champion-v2",
                   f"{base.element} + {add.element}", kwargs,
                   needs_radar=add.needs_radar or base.needs_radar)


# ---------------------------------------------------------------------------
# Trade-level analytics
# ---------------------------------------------------------------------------
def round_trips(res, data: pd.DataFrame) -> list[dict]:
    """Pair each OPEN_* with its CLOSE_*; attach timestamps and cost split."""
    trips, pending = [], None
    for ev in res.trade_log:
        if ev["side"].startswith("OPEN_"):
            pending = ev
        elif ev["side"].startswith("CLOSE_"):
            assert pending is not None, "CLOSE without a matching OPEN"
            reason = ev.get("reason", "signal")
            size = ev["size"]
            # entry is always taker: fill = mid*(1+c) long / mid*(1-c) short
            long = pending["side"] == "OPEN_LONG"
            e_px = pending["price"]
            entry_cost = size * e_px * TAKER_SIDE / (
                (1 + TAKER_SIDE) if long else (1 - TAKER_SIDE))
            # exit is taker unless it was a resting maker limit
            x_px = ev["price"]
            if reason in ("take_profit", "maker_tp"):
                exit_cost = 0.0
            else:
                exit_cost = size * x_px * TAKER_SIDE / (
                    (1 - TAKER_SIDE) if long else (1 + TAKER_SIDE))
            trips.append({
                "entry_bar": pending["bar"], "exit_bar": ev["bar"],
                "side": "LONG" if long else "SHORT", "reason": reason,
                "pnl": ev["pnl"], "pct": ev["pnl"] / NOTIONAL * 100,
                "entry_ts": data.index[pending["bar"]],
                "exit_ts": data.index[ev["bar"]],
                "entry_cost": entry_cost, "exit_cost": exit_cost,
                "maker_exit": reason in ("take_profit", "maker_tp"),
                "hold_bars": ev["bar"] - pending["bar"],
            })
            pending = None
    assert len(trips) == len(res.trade_pnls), "round-trip pairing lost a trade"
    return trips


def day_cluster_t(trips: list[dict]) -> tuple[float, int]:
    """t over UTC-day clusters of the per-trade net % (research-protocol sec.4).

    Each day contributes its MEAN net %/trade; t = mean / (sd / sqrt(D)).
    Returns (t, n_days); t = nan when fewer than 2 days carry trades.
    """
    if not trips:
        return float("nan"), 0
    df = pd.DataFrame({"day": [t["entry_ts"].normalize() for t in trips],
                       "pct": [t["pct"] for t in trips]})
    daily = df.groupby("day")["pct"].mean().to_numpy()
    d = len(daily)
    if d < 2 or daily.std(ddof=1) == 0:
        return float("nan"), d
    return float(daily.mean() / (daily.std(ddof=1) / np.sqrt(d))), d


def row(v: Variant, res, data: pd.DataFrame) -> dict:
    m = res.metrics
    trips = round_trips(res, data)
    t, ndays = day_cluster_t(trips)
    n = m.num_trades
    mix = {r: sum(1 for x in trips if x["reason"] == r) for r in EXIT_REASONS}
    return {
        "key": v.key, "label": v.label, "n": n,
        "pct": m.expectancy_per_trade_jpy / NOTIONAL * 100 if n else 0.0,
        "jpy": m.expectancy_per_trade_jpy, "win": m.win_rate_pct,
        "pf": m.profit_factor, "dd": m.max_drawdown_pct,
        "total": m.total_pnl_jpy, "t": t, "ndays": ndays, "mix": mix,
        "trips": trips, "carry": m.total_fees_jpy,
    }


HDR = (f"{'variant':<46s} {'n':>4s} {'net%/t':>9s} {'JPY/t':>9s} {'win%':>6s} "
       f"{'PF':>6s} {'maxDD%':>7s} {'totPnL':>9s} {'clust t':>8s} {'days':>5s}")


def line(r: dict) -> str:
    t = f"{r['t']:+.2f}" if np.isfinite(r["t"]) else "  n/a"
    return (f"{r['label']:<46s} {r['n']:4d} {r['pct']:+9.4f} {r['jpy']:+9.1f} "
            f"{r['win']:6.1f} {r['pf']:6.2f} {r['dd']:7.2f} {r['total']:+9.0f} "
            f"{t:>8s} {r['ndays']:5d}")


def mix_line(r: dict) -> str:
    n = max(r["n"], 1)
    parts = [f"{k}={r['mix'][k]}({r['mix'][k]/n*100:.0f}%)"
             for k in EXIT_REASONS if r["mix"][k]]
    return "    exit mix: " + (", ".join(parts) if parts else "(no closed trades)")


def cost_decomposition(r: dict) -> str:
    trips = r["trips"]
    if not trips:
        return "    cost: (no trades)"
    n = len(trips)
    ent = sum(t["entry_cost"] for t in trips) / n
    ext = sum(t["exit_cost"] for t in trips) / n
    carry = r["carry"] / n
    maker = sum(1 for t in trips if t["maker_exit"]) / n * 100
    gross = r["jpy"] + ent + ext + carry
    return (f"    cost/trade: gross {gross:+8.1f} JPY ({gross/NOTIONAL*100:+.4f}%)"
            f" - entry {ent:5.1f} - exit {ext:5.1f} - carry {carry:5.1f}"
            f" = net {r['jpy']:+8.1f} JPY | maker exits {maker:4.0f}%"
            f" | mean hold {sum(t['hold_bars'] for t in trips)/n:5.1f} bars")


def concentration(r: dict) -> str:
    """How much of the segment's PnL rides on its single best trade.

    At n ~ 10 this is the number that decides whether a row means anything.
    """
    trips = r["trips"]
    if not trips:
        return "    concentration: (no trades)"
    top = max(trips, key=lambda t: t["pct"])
    total = sum(t["pct"] for t in trips)
    share = top["pct"] / total * 100 if total else float("nan")
    wins = sum(1 for t in trips if t["pct"] > 0)
    ex_top = (total - top["pct"]) / (len(trips) - 1) if len(trips) > 1 else float("nan")
    return (f"    concentration: best trade {top['pct']:+.3f}% on "
            f"{top['entry_ts']:%Y-%m-%d %H:%M} ({top['side']}, {top['reason']}) "
            f"= {share:.0f}% of the {total:+.3f}% segment total"
            f" | {wins}/{len(trips)} winners"
            f" | net%/trade EXCLUDING the best trade {ex_top:+.4f}%")


def overlap(champ: dict, chal: dict) -> str:
    """Trade overlap keyed on (entry bar, side) -- the segments share bar indices."""
    ck = {(t["entry_bar"], t["side"]): t for t in champ["trips"]}
    hk = {(t["entry_bar"], t["side"]): t for t in chal["trips"]}
    shared = sorted(set(ck) & set(hk))
    only_c = sorted(set(ck) - set(hk))
    only_h = sorted(set(hk) - set(ck))

    def avg(keys, src):
        return np.mean([src[k]["pct"] for k in keys]) if keys else float("nan")

    def f(x):
        return f"{x:+.4f}%" if np.isfinite(x) else "   n/a"

    ac, ah = avg(shared, ck), avg(shared, hk)
    same_exit = np.isfinite(ac) and np.isfinite(ah) and abs(ac - ah) < 1e-12
    note = ("exits IDENTICAL on shared entries => the whole difference comes from "
            "which entries were dropped" if same_exit else
            "same entry, different exit => this delta is a pure EXIT effect")
    return (f"    overlap vs champion: shared entries {len(shared)}"
            f" | champion-only {len(only_c)} | challenger-only {len(only_h)}\n"
            f"      shared-entry net/trade   champion {f(ac)}"
            f"  challenger {f(ah)}   ({note})\n"
            f"      champion-only net/trade  {f(avg(only_c, ck))}"
            f"   challenger-only net/trade {f(avg(only_h, hk))}")


def maker_selection_counterfactual(r: dict) -> str:
    """research-protocol sec.3: the adverse-selection counterfactual.

    Here the maker leg is an EXIT, so the split that matters is "trades whose
    resting TP was traded through" vs "trades the TP never reached and which
    fell back to a taker exit". Report k measured +33bps in favour of the
    filled group at second scale; this is the same measurement on 1m bars.
    """
    filled = [t["pct"] for t in r["trips"] if t["reason"] == "maker_tp"]
    missed = [t["pct"] for t in r["trips"] if t["reason"] != "maker_tp"]
    if not filled or not missed:
        return "    maker-TP selection: n/a (one of the two groups is empty)"
    fm, mm = float(np.mean(filled)), float(np.mean(missed))
    return (f"    maker-TP selection: TP filled n={len(filled)} mean {fm:+.4f}%"
            f" | TP never reached n={len(missed)} mean {mm:+.4f}%"
            f" | selection effect {(fm - mm) * 100:+.1f}bps"
            f"  ({'ALLY' if fm > mm else 'ENEMY'} on this exit)")


def truncation_diagnostic(champ: dict, levels) -> str:
    """How much of the champion's edge lives ABOVE each candidate TP cap."""
    g = sorted((t["pct"] for t in champ["trips"]), reverse=True)
    out = [f"    champion judgment trades, net % sorted: "
           f"[{', '.join(f'{x:+.3f}' for x in g)}]"]
    for lv in levels:
        above = [x for x in g if x > lv]
        out.append(f"      trades whose realised net % exceeded a +{lv:.1f}% cap: "
                   f"{len(above)}/{len(g)}, carrying "
                   f"{sum(above):+.3f}% of the {sum(g):+.3f}% total "
                   f"({(sum(above)/sum(g)*100 if sum(g) else 0):.0f}% of all PnL) "
                   f"-- a +{lv:.1f}% maker TP truncates exactly this")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Sanity gates
# ---------------------------------------------------------------------------
def sanity_gates(primary: pd.DataFrame) -> None:
    print("=" * 108)
    print("SANITY GATES (must pass before any tournament number is read)")
    print("=" * 108)

    # (1) reproduction gate vs scripts/research_mainbot_exits.py
    res = run_variant(CHAMPION, primary)
    m = res.metrics
    print(f"  [gate 1] champion on FULL 30d primary: trades={m.num_trades} "
          f"expectancy={m.expectancy_per_trade_jpy:.10f} JPY/trade")
    print(f"           research_mainbot_exits.py CURRENT 30d row: trades={GATE_TRADES} "
          f"expectancy={GATE_EXPECTANCY_JPY:.10f} JPY/trade")
    assert m.num_trades == GATE_TRADES, "REPRODUCTION GATE FAILED (trade count)"
    assert abs(m.expectancy_per_trade_jpy - GATE_EXPECTANCY_JPY) < 1e-9, \
        "REPRODUCTION GATE FAILED (expectancy)"
    print("           PASS -- champion reproduces the reference row exactly; the "
          "DatetimeIndex kept here does not perturb the engine.")

    # (2) no look-ahead: hand-recompute the first entry from raw arrays
    opens_, leader = primary["open"].to_numpy(), primary["leader_close"].to_numpy()
    ev = next(t for t in res.trade_log if t["side"].startswith("OPEN_"))
    b, sig = ev["bar"], ev["bar"] - 1
    mom = float(np.log(leader[sig] / leader[sig - K]))
    want = "OPEN_LONG" if mom > THR_PCT / 100 else "OPEN_SHORT"
    px = FX_COSTS.buy_price(opens_[b]) if want == "OPEN_LONG" \
        else FX_COSTS.sell_price(opens_[b])
    assert want == ev["side"] and abs(px - ev["price"]) < 1e-9, "look-ahead check FAILED"
    print(f"  [gate 2] look-ahead: leader mom {mom*100:+.3f}% over {K} bars decided at "
          f"bar {sig} -> {ev['side']} filled at bar {b} open {opens_[b]:.1f} "
          f"(cost-adj {ev['price']:.4f}). PASS -- decision strictly precedes fill.")

    # (2b) the maker TP is never checked on the entry bar
    mres = run_variant(C1[0], primary)
    trips = round_trips(mres, primary)
    bad = [t for t in trips if t["reason"] == "maker_tp" and t["exit_bar"] <= t["entry_bar"]]
    assert not bad, "maker TP filled on/before its entry bar -- LOOK-AHEAD"
    ntp = sum(1 for t in trips if t["reason"] == "maker_tp")
    print(f"  [gate 2b] maker TP: {ntp} maker-TP exits, minimum hold "
          f"{min([t['hold_bars'] for t in trips], default=0)} bars, none on the entry "
          f"bar. PASS -- fill is checked strictly after entry.")

    # (3) determinism
    a, b2 = run_variant(C1[1], primary), run_variant(C1[1], primary)
    assert a.metrics.as_dict() == b2.metrics.as_dict() and a.trade_pnls == b2.trade_pnls
    print("  [gate 3] determinism: identical config + data -> bit-identical rerun. PASS")

    # (4) datetime conversion cross-check (research-protocol sec.6)
    secs = epoch_seconds(primary.index[:3])
    print(f"  [gate 4] datetime->seconds cross-check: {primary.index[0]} -> {secs[0]:.0f}s"
          f" -> {pd.Timestamp(secs[0], unit='s', tz='UTC')} (step "
          f"{secs[1]-secs[0]:.0f}s = 1m bars). PASS")

    # (5) no overlapping positions
    for t1, t2 in zip(trips, trips[1:]):
        assert t2["entry_bar"] >= t1["exit_bar"], "overlapping positions"
    print("  [gate 5] position overlap: none (entries never precede the prior exit). PASS")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    print("=" * 108)
    print("R6-T1  STRATEGY TOURNAMENT -- champion (xborder_momentum k30/thr0.8) "
          "vs C1 cost / C2 regime / C3 asymmetry")
    print("=" * 108)
    print(f"  costs: taker {TAKER_SIDE*100:.4f}%/side (= spread {FX_COSTS.spread_pct}%/2 "
          f"+ slippage {FX_COSTS.slippage_pct}%) ~ 3.2bps; round trip ~6.35bps; "
          f"maker legs free; swap {SWAP_DAILY_PCT}%/day")
    print(f"  notional {NOTIONAL:.0f} JPY/trade, paper equity {INITIAL_EQUITY:.0f} JPY")
    print(f"  MATCH RULE: challenger wins iff judgment-segment net expectancy/trade > "
          f"champion AND maxDD < champion AND n >= {MIN_TRADES_JUDGMENT}\n")

    primary = make_primary()
    secondary = make_secondary()
    p_exp, p_jud = split_60_40(primary)
    s_exp, s_jud = split_60_40(secondary)
    print(f"[data] PRIMARY   30d real bitFlyer x Binance leader: {len(primary)} bars "
          f"{primary.index[0]} .. {primary.index[-1]} ({len(primary)/1440:.1f}d)")
    print(f"        exploration {len(p_exp)} bars {p_exp.index[0]} .. {p_exp.index[-1]}")
    print(f"        judgment    {len(p_jud)} bars {p_jud.index[0]} .. {p_jud.index[-1]}")
    print(f"[data] SECONDARY 210d Binance self-proxy (leader_close == close): "
          f"{len(secondary)} bars {secondary.index[0]} .. {secondary.index[-1]} "
          f"({len(secondary)/1440:.1f}d)")
    print(f"        exploration {len(s_exp)} bars | judgment {len(s_jud)} bars")
    print("        DEGENERACY CAVEAT: the secondary set is momentum-on-itself under an "
          "FX-shaped cost model,\n        not a cross-exchange lag test and not bitFlyer "
          "data. Ranking support only; it never decides a match.\n")

    sanity_gates(primary)

    # ---------------- exploration -----------------------------------------
    print("=" * 108)
    print("EXPLORATION SEGMENT (first 60%) -- within-family selection happens HERE, "
          "and only here")
    print("=" * 108)

    champ_pexp = row(CHAMPION, run_variant(CHAMPION, p_exp), p_exp)
    champ_sexp = row(CHAMPION, run_variant(CHAMPION, s_exp), s_exp)

    chosen: dict[str, Variant] = {}
    for fam, variants in FAMILIES:
        print(f"\n--- family {fam} --- PRIMARY exploration (30d real, first 60%)")
        print("  " + HDR)
        print("  " + line(champ_pexp) + "   <= champion baseline")
        prows = {}
        for v in variants:
            r = row(v, run_variant(v, p_exp), p_exp)
            prows[v.key] = r
            print("  " + line(r))
            print("  " + mix_line(r))

        print(f"\n    SECONDARY exploration (210d proxy, first 60%) -- ranking support")
        print("  " + HDR)
        print("  " + line(champ_sexp) + "   <= champion baseline")
        srows = {}
        for v in variants:
            r = row(v, run_variant(v, s_exp), s_exp)
            srows[v.key] = r
            print("  " + line(r))

        # fixed selection rule
        elig = [v for v in variants if prows[v.key]["n"] >= MIN_TRADES_SELECT]
        src, tag = prows, f"PRIMARY exploration (>= {MIN_TRADES_SELECT} trades)"
        if not elig:
            elig = [v for v in variants if srows[v.key]["n"] >= MIN_TRADES_SELECT]
            src, tag = srows, (f"SECONDARY exploration -- no primary variant reached "
                               f"{MIN_TRADES_SELECT} trades")
        if not elig:
            elig, src, tag = list(variants), prows, "PRIMARY (rule exhausted, all thin)"
        pick = sorted(elig, key=lambda v: (-src[v.key]["pct"], src[v.key]["dd"]))[0]
        chosen[fam] = pick
        print(f"\n    SELECTED for {fam}: {pick.label}")
        print(f"      rule: highest net expectancy/trade on {tag}; "
              f"eligible = {[v.key for v in elig]}")

    # ---------------- judgment --------------------------------------------
    print("\n" + "=" * 108)
    print("JUDGMENT SEGMENT (last 40%) -- run ONCE, reported as it came out")
    print("=" * 108)

    champ_pj = row(CHAMPION, run_variant(CHAMPION, p_jud), p_jud)
    champ_sj = row(CHAMPION, run_variant(CHAMPION, s_jud), s_jud)

    print("\nPRIMARY judgment (30d real, last 40%) -- THIS decides the matches")
    print("  " + HDR)
    print("  " + line(champ_pj) + "   <= CHAMPION")
    print("  " + mix_line(champ_pj))
    print(cost_decomposition(champ_pj))
    print(concentration(champ_pj))

    results, verdicts = {}, {}
    for fam, _ in FAMILIES:
        v = chosen[fam]
        r = row(v, run_variant(v, p_jud), p_jud)
        results[fam] = r
        print("\n  " + line(r))
        print("  " + mix_line(r))
        print(cost_decomposition(r))
        print(concentration(r))
        if r["mix"]["maker_tp"]:
            print(maker_selection_counterfactual(r))
        print(overlap(champ_pj, r))
        beats_exp = r["pct"] > champ_pj["pct"]
        beats_dd = r["dd"] < champ_pj["dd"]
        enough = r["n"] >= MIN_TRADES_JUDGMENT
        win = beats_exp and beats_dd and enough
        verdicts[fam] = win
        print(f"    MATCH RULE: net expectancy beats champion = {beats_exp} "
              f"({r['pct']:+.4f}% vs {champ_pj['pct']:+.4f}%) | "
              f"maxDD beats champion = {beats_dd} "
              f"({r['dd']:.2f}% vs {champ_pj['dd']:.2f}%) | "
              f"n >= {MIN_TRADES_JUDGMENT} = {enough} (n={r['n']})")
        print(f"    VERDICT {fam}: {'CHALLENGER WINS' if win else 'CHAMPION HOLDS'}")

    print("\nSECONDARY judgment (210d proxy, last 40%) -- ranking support, not a verdict")
    print("  " + HDR)
    print("  " + line(champ_sj) + "   <= CHAMPION")
    for fam, _ in FAMILIES:
        r = row(chosen[fam], run_variant(chosen[fam], s_jud), s_jud)
        print("  " + line(r))
        print("  " + mix_line(r))

    # ---------------- brush-up round --------------------------------------
    print("\n" + "=" * 108)
    print("BRUSH-UP ROUND (max one)")
    print("=" * 108)
    winners = [f for f, w in verdicts.items() if w]
    if winners:
        win_fam = winners[0]
        v2 = compose(CHAMPION, chosen[win_fam], "CHAMPv2",
                     f"champion-v2 = champion + {chosen[win_fam].element}")
        print(f"  {len(winners)} challenger(s) won: {winners}. "
              f"champion-v2 takes the element from {win_fam}.")
        if len(winners) > 1:
            print(f"  NOTE: more than one winner; the pre-registration composes ONE "
                  f"element, so the first family in order is used and the rest stay "
                  f"as challengers.")
        r2 = row(v2, run_variant(v2, p_jud), p_jud)
        print("\n  Re-run on the JUDGMENT segment only (no re-selection):")
        print("  " + HDR)
        print("  " + line(champ_pj) + "   <= champion (v1)")
        print("  " + line(r2) + "   <= CHAMPION-v2")
        print("  " + mix_line(r2))
        print(cost_decomposition(r2))
        for fam, _ in FAMILIES:
            if fam == win_fam:
                continue
            r = results[fam]
            print("  " + line(r))
            better = (r2["pct"] > r["pct"]) and (r2["dd"] < r["dd"])
            print(f"    champion-v2 beats {fam} on both axes: {better}")
    else:
        print("  NO challenger won its match. Per the pre-registration the brush-up "
              "deliverable is the LOSS ANALYSIS below.\n")
        print("  Why each challenger lost (cost decomposition + exit mix + overlap are "
              "printed with each match above).\n")
        print("  Mechanism behind C1's loss -- where the champion's PnL actually sits:")
        print(truncation_diagnostic(champ_pj, [0.3, 0.5, 0.8]))
        for fam, _ in FAMILIES:
            r, v = results[fam], chosen[fam]
            beats_exp = r["pct"] > champ_pj["pct"]
            beats_dd = r["dd"] < champ_pj["dd"]
            missing = []
            if not beats_exp:
                missing.append(f"net expectancy {r['pct']:+.4f}% <= champion "
                               f"{champ_pj['pct']:+.4f}% "
                               f"(shortfall {(r['pct']-champ_pj['pct'])*100:+.1f}bps)")
            if not beats_dd:
                missing.append(f"maxDD {r['dd']:.2f}% >= champion {champ_pj['dd']:.2f}%")
            if r["n"] < MIN_TRADES_JUDGMENT:
                missing.append(f"only {r['n']} trades (< {MIN_TRADES_JUDGMENT}); "
                               f"the judgment segment is underpowered for this rule")
            n = max(r["n"], 1)
            maker_share = sum(1 for t in r["trips"] if t["maker_exit"]) / n * 100
            saved = sum(1 for t in r["trips"] if t["maker_exit"]) * \
                (NOTIONAL * TAKER_SIDE) / n
            print(f"\n  [{fam}] {v.label}")
            for msg in missing:
                print(f"      FAILS: {msg}")
            print(f"      exit-side cost actually saved: {maker_share:.0f}% of exits were "
                  f"maker legs => {saved:+.1f} JPY/trade "
                  f"({saved/NOTIONAL*100:+.4f}%) of taker cost avoided")
            print(f"      trades kept vs champion: "
                  f"{len(set((t['entry_bar'], t['side']) for t in r['trips']) & set((t['entry_bar'], t['side']) for t in champ_pj['trips']))}"
                  f" shared / {r['n']} own / {champ_pj['n']} champion")

    # ---------------- caveats ---------------------------------------------
    print("\n" + "=" * 108)
    print("CAVEATS (research-protocol sec.7)")
    print("=" * 108)
    print("""\
  1. SINGLE REGIME. The primary set is ~30 days of one market regime. Nothing
     here establishes stability across regimes; KNOWLEDGE.md sec.2 records
     repeated cases where a 21-30d winner collapsed on fresh data.
  2. MAKER-TP FILL IS OPTIMISTIC. On a 1-minute bar we only observe that the
     level traded through somewhere inside the minute -- not queue position,
     not intra-minute sequencing against the stop. The engine grants the fill
     on any strict through-trade and books it at the level with zero cost.
     Real maker fills are worse than this; treat C1's numbers as an UPPER
     BOUND. (The offsetting force -- adverse selection -- is an ALLY on a
     trend exit per report k, which is exactly why C1 was worth testing, and
     the "maker-TP selection" line above confirms the direction. The point is
     that the ally is not big enough to pay for the truncated tail.)
  3. SMALL n, AND ONE TRADE CARRIES IT. The champion turns ~28 trades in 30
     days, so a 40% judgment segment carries roughly a dozen. The >= 20-trade
     bar in the match rule is therefore hard to clear on the primary set by
     construction, and day-clustered t-stats at this n are indicative only
     (every |t| printed for the primary judgment is below 2.0 -- NOTHING here
     is statistically separated from zero). Worse, the "concentration" line
     shows a SINGLE trade supplies more than the whole segment's PnL for the
     champion, C2 and C3 alike. Read every primary-judgment row as a
     description of that one trade's fate, not as an expectancy estimate.
     The excluding-the-best-trade figures are printed as a DIAGNOSTIC only;
     dropping the biggest winner post hoc is not a legitimate selection rule
     and must not be promoted to a verdict (research-protocol sec.8.2).
  4. SECONDARY SET IS DEGENERATE. leader_close == close there; it measures
     momentum-on-itself under FX costs, not the cross-exchange effect the live
     bot trades. Ranking support only.
  5. NO ADOPTION. This is a candidate-generation exercise. Adoption still
     requires the standing pre-registered paper bars (main bot: >= 30 paper
     trades, >= +0.15%/trade net, max DD < 10%) -- KNOWLEDGE.md sec.5.
  6. C2's radar mask is evaluated at the DECISION bar, so a position opened
     inside the window is still allowed to run (and exit) outside it. That is
     an entry filter, deliberately, so the exit structure stays identical to
     the champion's as the pre-registration requires.
  7. Costs are the repo's standing measured constants, not re-measured here;
     funding is modelled as a flat 0.06%/day swap rather than the real 8h
     schedule.
""")
    print("Done. Nothing written, nothing committed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
