#!/usr/bin/env python3
"""Anchor-reversion v2 — the PRE-REGISTERED follow-up.

v1 (scripts/research_anchor.py, 21 days) found the reversion in the CAUSAL
EVENT STUDY at w=60 only, yet every backtest configuration lost money. Two
design errors were identified as the likely cause, and BOTH are fixed here —
nothing else is changed, and the test set below was fixed by the lead BEFORE
this (30-day) dataset was looked at:

  1. The 0.5% protective stop was ~10x the size of the measured edge (a few
     bps), so it converted the edge into stop-out noise.  ->  NO STOP AT ALL.
  2. The exit was a z-band (|z| < 0.5), which has no relation to the 60-minute
     horizon at which the effect was measured. -> FIXED 60-MINUTE TIME EXIT,
     implemented by the engine's new `max_hold_bars`. z_exit is not used.

Pre-registered test — EXACTLY this, no grid widening:
    w = 60 (only), z_entry in {2.0, 2.5}, exit = max_hold_bars=60,
    stop_loss_pct = None.
Data: data/candles_FX_BTC_JPY.csv extended to 30 days (2026-07-21..2026-08-20);
the July portion is fresh and was never used in any prior selection. Leader:
data/binance_BTCUSDT_1m.csv, inner-joined on the minute as in v1.

PASS RULE (fixed in advance, judged separately for taker and maker): take the
BETTER of the two z_entry values ON TRAIN+VAL; it passes iff
    T+V pnl > 0 with >= 30 trades  AND  its OOS pnl > 0 with >= 15 trades.

CAVEAT (unchanged from v1): the deviation is measured JPY-vs-USD with no USDJPY
series, so USDJPY moves leak into it. At <= 60 min that noise is ~2-6 bps
against deviations of interest >= 20 bps, but it is real and is NOT removed.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import pandas as pd

from bot.backtest.engine import CostModel, run_backtest
from bot.backtest.walk_forward import split_data
from bot.strategy.base import Signal, SignalType, Strategy

DATA = Path(__file__).resolve().parents[1] / "data"

# FX_BTC_JPY: taker/maker fee 0%. Spread measured live at 0.0235%; slippage
# conservative for a deep book. Swap 0.06%/day accrues on carried positions.
FX_COSTS = CostModel(taker_fee_pct=0.0, maker_fee_pct=0.0,
                     slippage_pct=0.02, spread_pct=0.0235)
SWAP_DAILY_PCT = 0.06
NOTIONAL = 110000.0        # ~0.01 BTC
EQUITY = 200000.0
SD_WINDOW = 1440           # 24h of 1m bars for the causal deviation sd
W = 60                     # the ONLY deviation window under test
Z_ENTRIES = (2.0, 2.5)
MAX_HOLD_BARS = 60         # the fixed 60-minute time exit
MIN_TRADES_TV = 30
MIN_TRADES_OOS = 15


# --------------------------------------------------------------------------
# strategy under test (entries only; the engine owns the exit)
# --------------------------------------------------------------------------
class AnchorReversionTimed(Strategy):
    """SHORT when the local CFD has outrun the anchor, LONG when it lags.

    Entries only — it NEVER emits CLOSE. Positions are flattened solely by the
    engine's `max_hold_bars` time exit. z = deviation_w / rolling_sd(dev, 1440),
    all of it computed from the candle slice the engine hands us, so no future
    data is touched.
    """

    @property
    def min_history(self) -> int:
        return int(self.params.get("w", W)) + int(self.params.get("sd_window", SD_WINDOW))

    def _z(self, candles: pd.DataFrame) -> float | None:
        w = int(self.params.get("w", W))
        sd_window = int(self.params.get("sd_window", SD_WINDOW))
        need = w + sd_window
        if "leader_close" not in candles.columns or len(candles) < need:
            return None
        fx = candles["close"].to_numpy()[-need:]
        bn = candles["leader_close"].to_numpy()[-need:]
        if not (np.all(np.isfinite(fx)) and np.all(np.isfinite(bn))):
            return None
        if fx.min() <= 0 or bn.min() <= 0:
            return None
        lf, lb = np.log(fx), np.log(bn)
        dev = ((lf[w:] - lf[:-w]) - (lb[w:] - lb[:-w])) * 1e4
        sd = float(dev.std(ddof=1))
        if not np.isfinite(sd) or sd <= 0:
            return None
        return float(dev[-1]) / sd

    def on_candles(self, candles: pd.DataFrame) -> Signal:
        z_e = float(self.params.get("z_entry", 2.0))
        z = self._z(candles)
        if z is None:
            return Signal(SignalType.HOLD, "insufficient/invalid leader data")
        ind = {"z": z}
        if z > z_e:
            return Signal(SignalType.SELL, f"local rich vs anchor (z={z:+.2f})", ind)
        if z < -z_e:
            return Signal(SignalType.BUY, f"local cheap vs anchor (z={z:+.2f})", ind)
        return Signal(SignalType.HOLD, f"inside band (z={z:+.2f})", ind)


# --------------------------------------------------------------------------
# data / plumbing
# --------------------------------------------------------------------------
def load(name: str) -> pd.DataFrame:
    df = pd.read_csv(DATA / name, index_col=0, parse_dates=True)
    df.index = pd.to_datetime(df.index, utc=True)
    return df


def run(params: dict, data: pd.DataFrame, execution: str):
    return run_backtest(
        AnchorReversionTimed(params), data.reset_index(drop=True),
        costs=FX_COSTS, execution=execution, allow_short=True,
        swap_daily_pct=SWAP_DAILY_PCT, order_notional_jpy=NOTIONAL,
        initial_equity_jpy=EQUITY, stop_loss_pct=None,
        max_hold_bars=MAX_HOLD_BARS,
    )


def row(label: str, r) -> str:
    m = r.metrics
    exp = m.expectancy_per_trade_jpy / NOTIONAL * 100 if m.num_trades else 0.0
    pf = f"{m.profit_factor:5.2f}" if np.isfinite(m.profit_factor) else "  inf"
    return (f"{label:>5} {m.total_pnl_jpy:>+9.0f} {m.num_trades:>7d} "
            f"{m.win_rate_pct:>6.1f} {pf} {exp:>+11.4f} {m.max_drawdown_pct:>7.2f} "
            f"{r.missed_fills:>6d}")


def exit_mix(r) -> tuple[int, int]:
    """(time exits, exits caused by an opposite-side signal).

    The strategy emits no CLOSE, but a z-flip through the far band while a
    position is open still closes it early through the engine's net-position
    model. Count both so the 'pure time exit' claim is auditable.
    """
    opens = [t["bar"] for t in r.trade_log if t["side"].startswith("OPEN")]
    closes = [t["bar"] for t in r.trade_log if t["side"].startswith("CLOSE")]
    timed = sum(1 for o, c in zip(opens, closes) if c - o >= MAX_HOLD_BARS)
    return timed, len(closes) - timed


HEADER = (f"{'set':>5} {'pnl':>9} {'trades':>7} {'win%':>6} {'PF':>5} "
          f"{'exp%/trade':>11} {'maxDD%':>7} {'miss':>6}")


def main() -> int:
    fx = load("candles_FX_BTC_JPY.csv")
    leader = load("binance_BTCUSDT_1m.csv")["close"]
    merged = fx.join(leader.rename("leader_close"), how="inner").dropna()
    span_days = (merged.index[-1] - merged.index[0]).total_seconds() / 86400
    rt_cost = 2 * (FX_COSTS.spread_pct / 2 + FX_COSTS.slippage_pct)

    print("=" * 78)
    print("ANCHOR REVERSION v2 — pre-registered: w=60, NO stop, 60-minute time exit")
    print("=" * 78)
    print(f"aligned bars: {len(merged)}  span: {merged.index[0]} .. {merged.index[-1]}"
          f"  ({span_days:.2f} days)")
    print(f"costs: fee 0% | spread {FX_COSTS.spread_pct}% | slip {FX_COSTS.slippage_pct}% "
          f"| swap {SWAP_DAILY_PCT}%/day | stop NONE | exit {MAX_HOLD_BARS} bars")
    print(f"round-trip taker cost ~{rt_cost:.3f}% = {rt_cost * 100:.1f} bps; "
          f"60m carry ~{SWAP_DAILY_PCT / 24 * 100:.2f} bps")
    print("CAVEAT: deviation is JPY-vs-USD with no USDJPY series; contamination not removed.")

    s = split_data(merged)
    train_val = pd.concat([s.training, s.validation])
    warm = W + SD_WINDOW
    print(f"\nsplits: train={len(s.training)} val={len(s.validation)} "
          f"T+V={len(train_val)} bars ({len(train_val) / 1440:.1f}d), "
          f"OOS={len(s.out_of_sample)} bars ({len(s.out_of_sample) / 1440:.1f}d)")
    print(f"warm-up per split: {warm} bars ({warm / 1440:.1f}d) before the first signal")

    verdicts = {}
    for execution in ("taker", "maker"):
        print("\n" + "-" * 78)
        print(f"execution={execution}  (selection on T+V ONLY; OOS run once, after)")
        print("-" * 78)
        print(HEADER)
        runs = {}
        for z_e in Z_ENTRIES:
            params = {"w": W, "z_entry": z_e, "sd_window": SD_WINDOW}
            tv = run(params, train_val, execution)
            oos = run(params, s.out_of_sample, execution)
            runs[z_e] = (params, tv, oos)
            print(f"  z_e={z_e:.1f}")
            print("  " + row("T+V", tv))
            print("  " + row("OOS", oos))
            for label, r in (("T+V", tv), ("OOS", oos)):
                timed, flipped = exit_mix(r)
                print(f"        exits {label}: {timed} by time, {flipped} by an "
                      f"opposite-side signal before {MAX_HOLD_BARS} bars")

        # pre-registered selection: better of the two z_entry values on T+V
        best_z = max(Z_ENTRIES, key=lambda z: runs[z][1].metrics.total_pnl_jpy)
        params, tv, oos = runs[best_z]
        print(f"  SELECTED on T+V: z_e={best_z} "
              f"(T+V pnl {tv.metrics.total_pnl_jpy:+.0f}, {tv.metrics.num_trades} trades)")
        verdicts[execution] = (best_z, tv, oos)

    print("\n" + "=" * 78)
    print("PASS RULE (fixed in advance): better-of-two z_entry ON T+V needs "
          f"T+V pnl>0 with >={MIN_TRADES_TV} trades")
    print(f"                             AND OOS pnl>0 with >={MIN_TRADES_OOS} trades")
    print("=" * 78)
    any_pass = False
    for execution in ("taker", "maker"):
        z_e, tv, oos = verdicts[execution]
        tvm, om = tv.metrics, oos.metrics
        ok = (tvm.total_pnl_jpy > 0 and tvm.num_trades >= MIN_TRADES_TV
              and om.total_pnl_jpy > 0 and om.num_trades >= MIN_TRADES_OOS)
        any_pass = any_pass or ok
        print(f"  {execution:>5}: {'PASS' if ok else 'FAIL'} — z_e={z_e}; "
              f"T+V pnl {tvm.total_pnl_jpy:+.0f} ({tvm.num_trades} trades), "
              f"OOS pnl {om.total_pnl_jpy:+.0f} ({om.num_trades} trades)")
    print(f"\nOVERALL: {'PASS' if any_pass else 'FAIL'} — "
          f"{'implement the strategy module' if any_pass else 'do NOT implement'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
