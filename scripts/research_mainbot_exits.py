#!/usr/bin/env python3
"""R5-S3: exit-structure audit of the main paper bot (xborder_momentum).

The main paper bot trades `xborder_momentum` (src/bot/strategy/xborder_momentum.py)
with ENTRY frozen at the researched values (config/config.yaml): k=30 bars,
thr_pct=0.8%, leader=Binance BTCUSDT. Entry got research attention; the EXIT
side (exit_pct band-close, stop_loss_pct, and the unused take_profit_pct /
max_hold_bars engine features) never did. This script audits exits only.

Methodology
-----------
(a) 210-day PROXY: data/binance_BTCUSDT_1m_full.csv used as BOTH the traded
    instrument and its own leader signal (leader_close == close), under the
    FX_BTC_JPY Crypto CFD cost model (0% fee, spread+slippage ~3.2bps/side,
    swap 0.06%/day). This is a proxy for "what if bitFlyer had 210 days of
    history" -- it is NOT bitFlyer data. Chronological 60/20/20 train/val/OOS
    (bot.backtest.walk_forward.split_data, same split used by every other
    research script in this repo).
(b) 30-day REAL: data/candles_FX_BTC_JPY.csv (actual bitFlyer FX_BTC_JPY
    trade candles) joined with the real Binance BTCUSDT leader over the
    overlapping ~30 days, same cost model. Confirmation only, no parameter
    selection happens here.

Exit grid (entry frozen): exit_pct x stop_loss_pct x take_profit_pct x
max_hold_bars, full grid on (a)-train, ranked by net expectancy/trade among
configs with >=30 trades, confirmed on (a)-val, OOS run exactly once.
CURRENT config (0.05 / 0.5 / none / none) is always reported alongside as
baseline on every split.

Adoption rule (fixed, not tuned): propose the winner to the lead ONLY if it
beats CURRENT on BOTH val and OOS net expectancy AND its OOS net expectancy
is > 0. Otherwise: keep current. The point is to know, not to churn.

Run: python scripts/research_mainbot_exits.py
"""
from __future__ import annotations

import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import pandas as pd

from bot.backtest.engine import CostModel, run_backtest
from bot.backtest.walk_forward import split_data
from bot.strategy.xborder_momentum import XborderMomentumStrategy

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

# ---------------------------------------------------------------------------
# Frozen entry (config/config.yaml: strategy.params) -- NOT part of this audit
K = 30
THR_PCT = 0.8

# FX_BTC_JPY Crypto CFD cost model (config/products.yaml + config/config.yaml
# comments): taker/maker fee 0%, spread measured live ~0.0235%, slippage
# 0.02% conservative => per-side extra ~(0.0235/2 + 0.02) = 0.03175% ~= 3.2bps,
# round-trip taker ~6.35bps, matching the task brief exactly. Swap
# 0.06%/day (products.yaml FX_BTC_JPY.swap_daily_pct) accrues on carried
# positions, which matters directly for max_hold_bars=240 (4h holds).
FX_COSTS = CostModel(taker_fee_pct=0.0, maker_fee_pct=0.0,
                      slippage_pct=0.02, spread_pct=0.0235)
SWAP_DAILY_PCT = 0.06
NOTIONAL = 110000.0        # ~0.01 BTC-CFD, matches min FX order size
INITIAL_EQUITY = 200000.0  # config.yaml paper_equity_jpy

CURRENT = {"exit_pct": 0.05, "stop_loss_pct": 0.5, "take_profit_pct": None, "max_hold_bars": None}

GRID_EXIT_PCT = [0.05, 0.2, 0.4]
GRID_SL = [0.3, 0.5, 1.0]
GRID_TP = [None, 1.0, 2.0]
GRID_HOLD = [None, 240]

MIN_TRADES = 30


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
def _load(name: str) -> pd.DataFrame:
    df = pd.read_csv(DATA / name, index_col=0, parse_dates=True)
    df.index = pd.to_datetime(df.index, utc=True)
    return df


def make_proxy_frame() -> pd.DataFrame:
    """210d Binance BTCUSDT as both traded instrument and leader signal."""
    df = _load("binance_BTCUSDT_1m_full.csv")[["open", "high", "low", "close", "volume"]].dropna()
    df = df.copy()
    df["leader_close"] = df["close"]
    return df.reset_index(drop=True)


def make_real_frame() -> pd.DataFrame:
    """30d bitFlyer FX_BTC_JPY traded, real Binance BTCUSDT leader (inner join)."""
    fx = _load("candles_FX_BTC_JPY.csv")
    leader = _load("binance_BTCUSDT_1m_full.csv")["close"]
    merged = fx.join(leader.rename("leader_close"), how="inner").dropna()
    return merged.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Backtest wrapper
# ---------------------------------------------------------------------------
def run(exit_cfg: dict, data: pd.DataFrame, *, notional: float = NOTIONAL,
        initial_equity: float = INITIAL_EQUITY):
    strat_params = {"k": K, "thr_pct": THR_PCT, "exit_pct": exit_cfg["exit_pct"]}
    return run_backtest(
        XborderMomentumStrategy(strat_params), data,
        costs=FX_COSTS, execution="taker", allow_short=True,
        swap_daily_pct=SWAP_DAILY_PCT, order_notional_jpy=notional,
        initial_equity_jpy=initial_equity,
        stop_loss_pct=exit_cfg["stop_loss_pct"],
        take_profit_pct=exit_cfg["take_profit_pct"],
        max_hold_bars=exit_cfg["max_hold_bars"],
    )


def cfg_str(c: dict) -> str:
    tp = "none" if c["take_profit_pct"] is None else f"{c['take_profit_pct']:.1f}"
    mh = "none" if c["max_hold_bars"] is None else str(c["max_hold_bars"])
    return f"exit={c['exit_pct']:.2f} sl={c['stop_loss_pct']:.1f} tp={tp} hold={mh}"


def fmt(r) -> str:
    m = r.metrics
    exp_pct = m.expectancy_per_trade_jpy / NOTIONAL * 100 if m.num_trades else 0.0
    return (f"trades={m.num_trades:4d} win={m.win_rate_pct:5.1f}% PF={m.profit_factor:5.2f} "
            f"exp={m.expectancy_per_trade_jpy:+8.1f}JPY/t ({exp_pct:+.4f}%/t) "
            f"maxDD={m.max_drawdown_pct:5.2f}% totPnL={m.total_pnl_jpy:+10.0f} "
            f"fees={m.total_fees_jpy:8.0f} miss={r.missed_fills}")


def exit_mix(r) -> dict:
    closes = [t for t in r.trade_log if t["side"].startswith("CLOSE_")]
    n = len(closes)
    counts = {"signal": 0, "stop_loss": 0, "take_profit": 0, "time_exit": 0}
    for t in closes:
        counts[t.get("reason", "signal")] += 1
    assert n == len(r.trade_pnls), \
        f"trade_log close count ({n}) != trade_pnls length ({len(r.trade_pnls)})"
    return {"n": n, "counts": counts,
            "pct": {k: (v / n * 100 if n else 0.0) for k, v in counts.items()}}


def print_exit_mix(label: str, r) -> None:
    mix = exit_mix(r)
    print(f"  {label}: n={mix['n']} closed trades")
    for reason in ("signal", "stop_loss", "take_profit", "time_exit"):
        c, p = mix["counts"][reason], mix["pct"][reason]
        print(f"    {reason:12s} {c:5d}  ({p:5.1f}%)")


# ---------------------------------------------------------------------------
# Sanity checks
# ---------------------------------------------------------------------------
def hand_check_one_trade(data: pd.DataFrame, r, label: str) -> None:
    """Independently recompute the strategy signal + fill price for the
    FIRST executed entry in the trade log and verify the engine's causal,
    next-bar-open execution against it by hand."""
    opens_ = data["open"].to_numpy()
    leader = data["leader_close"].to_numpy()
    open_entry = next((t for t in r.trade_log if t["side"].startswith("OPEN_")), None)
    if open_entry is None:
        print(f"  [{label}] no trades to hand-check")
        return
    b = open_entry["bar"]
    side = open_entry["side"]
    fill_price = open_entry["price"]
    signal_bar = b - 1  # engine fills bar b's signal at bar b+1's open -> decision was at b-1
    assert signal_bar - K >= 0, "hand-check trade too close to warmup, pick another run"
    mom = float(np.log(leader[signal_bar] / leader[signal_bar - K]))
    thr = THR_PCT / 100
    expect_side = "OPEN_LONG" if mom > thr else "OPEN_SHORT" if mom < -thr else None
    assert expect_side == side, (
        f"hand-check FAILED: recomputed mom={mom*100:.4f}% at bar {signal_bar} "
        f"implies {expect_side}, engine opened {side}")
    ref = opens_[b]
    expect_price = (FX_COSTS.buy_price(ref) if side == "OPEN_LONG" else FX_COSTS.sell_price(ref))
    assert abs(expect_price - fill_price) < 1e-6, (
        f"hand-check FAILED: recomputed fill price {expect_price:.4f} != "
        f"engine fill price {fill_price:.4f}")
    print(f"  [{label}] PASS -- signal bar {signal_bar} (leader mom {mom*100:+.3f}% over "
          f"{K} bars) -> {side} fills at bar {b} open={ref:.2f}, "
          f"cost-adjusted price={fill_price:.4f} (engine matched exactly). "
          f"Confirms next-bar-open causal execution, no look-ahead.")


def determinism_check(exit_cfg: dict, data: pd.DataFrame, label: str) -> None:
    r1 = run(exit_cfg, data)
    r2 = run(exit_cfg, data)
    ok = (r1.metrics.as_dict() == r2.metrics.as_dict() and r1.trade_pnls == r2.trade_pnls)
    print(f"  [{label}] determinism: {'PASS (bit-identical rerun)' if ok else 'FAIL'}")
    assert ok


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    print("=" * 100)
    print("R5-S3: EXIT-STRUCTURE AUDIT -- xborder_momentum (main paper bot)")
    print("=" * 100)
    print(f"Entry FROZEN: k={K}  thr_pct={THR_PCT}  leader=Binance BTCUSDT")
    print(f"CURRENT exits: {cfg_str(CURRENT)}")
    print(f"Cost model (FX_BTC_JPY Crypto CFD): taker/maker fee=0%, spread=0.0235%, "
          f"slippage=0.02% -> per-side ~{(0.0235/2+0.02):.3f}% (~3.2bps), "
          f"round-trip taker ~{2*(0.0235/2+0.02):.2f}% (~6.35bps). Swap {SWAP_DAILY_PCT}%/day.")
    print(f"Order size: notional={NOTIONAL:.0f} JPY (~0.01 BTC), "
          f"paper equity={INITIAL_EQUITY:.0f} JPY. Execution=taker (matches production "
          f"MARKET-order default, src/bot/order_management/manager.py).")

    # ---- (a) 210d Binance proxy, train/val/OOS ---------------------------
    proxy = make_proxy_frame()
    splits = split_data(proxy)  # 60/20/20 chronological, same as every other research script
    print(f"\n[data] 210d Binance proxy: {len(proxy)} bars "
          f"({proxy.index[0]}..{proxy.index[-1]} by row count; timestamps dropped on reset_index)")
    print(f"       train={len(splits.training)}  val={len(splits.validation)}  "
          f"oos={len(splits.out_of_sample)}")

    print("\n--- CURRENT config baseline on every split (210d proxy) ---")
    cur_train = run(CURRENT, splits.training)
    cur_val = run(CURRENT, splits.validation)
    cur_oos = run(CURRENT, splits.out_of_sample)
    print(f"  train : {fmt(cur_train)}")
    print(f"  val   : {fmt(cur_val)}")
    print(f"  oos   : {fmt(cur_oos)}")

    # ---- Grid search on train ---------------------------------------------
    grid = [{"exit_pct": e, "stop_loss_pct": sl, "take_profit_pct": tp, "max_hold_bars": mh}
            for e, sl, tp, mh in itertools.product(GRID_EXIT_PCT, GRID_SL, GRID_TP, GRID_HOLD)]
    print(f"\n--- Exit grid on TRAIN ({len(grid)} combos, entry frozen k={K} thr={THR_PCT}) ---")
    grid_results = []
    for cfg in grid:
        r = run(cfg, splits.training)
        grid_results.append((cfg, r))
        tag = " <= CURRENT" if cfg == CURRENT else ""
        print(f"  {cfg_str(cfg):40s} {fmt(r)}{tag}")

    viable = [(c, r) for c, r in grid_results if r.metrics.num_trades >= MIN_TRADES]
    print(f"\n  {len(viable)}/{len(grid_results)} combos have >= {MIN_TRADES} trades on train")
    if not viable:
        print("  -> NO viable configuration; audit cannot select a winner. Keep current.")
        chosen = dict(CURRENT)
        chosen_train = cur_train
    else:
        viable_sorted = sorted(viable, key=lambda cr: cr[1].metrics.expectancy_per_trade_jpy,
                               reverse=True)
        print("\n  Top 5 viable by train net expectancy/trade:")
        for c, r in viable_sorted[:5]:
            print(f"    {cfg_str(c):40s} {fmt(r)}")
        chosen, chosen_train = viable_sorted[0]
        print(f"\n  SELECTED (train winner): {cfg_str(chosen)}")
        print(f"    train: {fmt(chosen_train)}")

    # ---- Confirm on val, report OOS once -----------------------------------
    print("\n--- VALIDATION confirmation (210d proxy) ---")
    chosen_val = run(chosen, splits.validation)
    print(f"  CURRENT: {fmt(cur_val)}")
    print(f"  CHOSEN : {fmt(chosen_val)}   [{cfg_str(chosen)}]")

    print("\n--- OUT-OF-SAMPLE verdict, run ONCE (210d proxy) ---")
    chosen_oos = run(chosen, splits.out_of_sample)
    print(f"  CURRENT: {fmt(cur_oos)}")
    print(f"  CHOSEN : {fmt(chosen_oos)}   [{cfg_str(chosen)}]")

    # ---- Adoption rule (fixed) ---------------------------------------------
    beats_val = chosen_val.metrics.expectancy_per_trade_jpy > cur_val.metrics.expectancy_per_trade_jpy
    beats_oos = chosen_oos.metrics.expectancy_per_trade_jpy > cur_oos.metrics.expectancy_per_trade_jpy
    oos_positive = chosen_oos.metrics.expectancy_per_trade_jpy > 0
    propose = beats_val and beats_oos and oos_positive and cfg_str(chosen) != cfg_str(CURRENT)
    print("\n--- ADOPTION RULE (fixed, pre-registered) ---")
    print(f"  chosen beats current on val net expectancy : {beats_val} "
          f"({chosen_val.metrics.expectancy_per_trade_jpy:+.1f} vs "
          f"{cur_val.metrics.expectancy_per_trade_jpy:+.1f} JPY/trade)")
    print(f"  chosen beats current on oos net expectancy : {beats_oos} "
          f"({chosen_oos.metrics.expectancy_per_trade_jpy:+.1f} vs "
          f"{cur_oos.metrics.expectancy_per_trade_jpy:+.1f} JPY/trade)")
    print(f"  chosen oos net expectancy > 0               : {oos_positive} "
          f"({chosen_oos.metrics.expectancy_per_trade_jpy:+.1f} JPY/trade)")
    if propose:
        print(f"  VERDICT: PROPOSE CHANGE to {cfg_str(chosen)} (all three conditions met)")
    else:
        print("  VERDICT: KEEP CURRENT CONFIG (0.05 / 0.5 / none / none) "
              "-- adoption conditions not all met")

    # ---- 30d bitFlyer REAL data: current vs chosen -------------------------
    print("\n" + "=" * 100)
    print("(b) 30d bitFlyer FX_BTC_JPY REAL DATA: current vs chosen")
    print("=" * 100)
    real = make_real_frame()
    print(f"[data] real bitFlyer/Binance overlap: {len(real)} bars "
          f"(~{len(real)/60/24:.1f} days)")
    real_cur = run(CURRENT, real)
    real_chosen = run(chosen, real)
    print(f"  CURRENT: {fmt(real_cur)}")
    print(f"  CHOSEN : {fmt(real_chosen)}   [{cfg_str(chosen)}]")

    # ---- Exit mix: how trades actually end ----------------------------------
    print("\n" + "=" * 100)
    print("EXIT MIX -- how trades actually end (the owner's actual question)")
    print("=" * 100)
    print(f"\n210d proxy, FULL period, CURRENT {cfg_str(CURRENT)}:")
    proxy_cur_full = run(CURRENT, proxy)
    print_exit_mix("current/proxy-full", proxy_cur_full)
    print(f"\n210d proxy, FULL period, CHOSEN {cfg_str(chosen)}:")
    proxy_chosen_full = run(chosen, proxy)
    print_exit_mix("chosen/proxy-full", proxy_chosen_full)
    print(f"\n30d bitFlyer REAL, CURRENT {cfg_str(CURRENT)}:")
    print_exit_mix("current/real30d", real_cur)
    print(f"\n30d bitFlyer REAL, CHOSEN {cfg_str(chosen)}:")
    print_exit_mix("chosen/real30d", real_chosen)

    # ---- Sanity: no look-ahead (hand-check) + determinism -------------------
    print("\n" + "=" * 100)
    print("SANITY CHECKS")
    print("=" * 100)
    print("Look-ahead (hand-checked trade, next-bar-open causal execution):")
    hand_check_one_trade(real, real_cur, "real30d/current")
    hand_check_one_trade(proxy, proxy_chosen_full, "proxy-full/chosen")
    print("\nDeterminism (identical config + data -> bit-identical result):")
    determinism_check(CURRENT, real, "real30d/current")
    determinism_check(chosen, splits.training, "proxy-train/chosen")

    # ---- Caveats --------------------------------------------------------------
    print("\n" + "=" * 100)
    print("CAVEATS")
    print("=" * 100)
    print("""\
  1. The 210d "proxy" backtest uses Binance BTCUSDT as BOTH the traded
     instrument and its own leader signal (leader_close == close). This is
     NOT a cross-exchange-lag test -- it degenerates to plain momentum-on-
     itself under an FX-shaped cost model. It exists only to get 210 days of
     history for exit-parameter selection; treat its absolute PnL as
     indicative of exit-parameter RANKING, not of live bitFlyer performance.
  2. The 30d bitFlyer REAL run is real traded-market data but covers only
     ~30 days -- one regime, small trade counts especially once the exit
     grid thins out entries via SL/TP/hold interactions. Treat it as a
     confirmation sanity check, not a second independent OOS test.
  3. Real bitFlyer costs (spread/slippage) were estimated once (see
     scripts/research_fx.py) and are reused here unchanged; they were not
     re-measured for this study. Funding-rate carry is modeled as a constant
     0.06%/day swap (products.yaml), which is conservative but not identical
     to the real 8h funding schedule.
  4. Regime dependence: cross-exchange/leader-momentum edges are known to be
     unstable across volatility regimes (see docs/RESEARCH_REPORT_2026-08-20*
     .md). A config that wins on this train/val/OOS split is not guaranteed
     to keep winning if the market regime shifts after this audit.
  5. take_profit_pct uses the engine's maker-fill assumption (limit at the
     TP level, maker fee) even though execution=taker elsewhere in this
     script -- this matches engine.py's design (TP is a resting order) and
     is NOT swept as its own maker/taker execution variable here.
  6. Entry (k, thr_pct) was intentionally frozen per the pre-registered
     grid; this audit says nothing about whether entry itself is still
     optimal.
""")
    print("Done. Nothing committed by this script.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
