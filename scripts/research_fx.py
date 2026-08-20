#!/usr/bin/env python3
"""FX_BTC_JPY research: cross-exchange momentum (long AND short) under the
real FX cost structure (0% fee, measured spread, swap carry).

Methodology: parameter selection on Training+Validation only; the single
selected configuration per execution model is then judged on Out-of-Sample.
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

DATA = Path(__file__).resolve().parents[1] / "data"

# FX_BTC_JPY: taker/maker fee 0%. Spread measured live at 0.0235%; slippage
# conservative for a deep book. Swap 0.04%/day accrues on carried positions.
FX_COSTS = CostModel(taker_fee_pct=0.0, maker_fee_pct=0.0,
                     slippage_pct=0.02, spread_pct=0.0235)
SWAP_DAILY_PCT = 0.04
NOTIONAL = 110000.0     # ~0.01 BTC


def load(name: str) -> pd.DataFrame:
    df = pd.read_csv(DATA / name, index_col=0, parse_dates=True)
    df.index = pd.to_datetime(df.index, utc=True)
    return df


def leadlag(target: pd.Series, predictor: pd.Series, max_lag: int = 5) -> str:
    joined = pd.DataFrame({"t": target, "p": predictor}).dropna()
    rt, rp = np.log(joined["t"]).diff(), np.log(joined["p"]).diff()
    return "  ".join(f"k={k}:{rt.corr(rp.shift(k)):+.3f}" for k in range(max_lag + 1))


def run(params, data, execution):
    return run_backtest(
        XborderMomentumStrategy(params), data.reset_index(drop=True),
        costs=FX_COSTS, execution=execution, allow_short=True,
        swap_daily_pct=SWAP_DAILY_PCT, order_notional_jpy=NOTIONAL,
        initial_equity_jpy=200000.0,
    )


def fmt(r):
    m = r.metrics
    exp = m.expectancy_per_trade_jpy / NOTIONAL * 100 if m.num_trades else 0.0
    return (f"pnl={m.total_pnl_jpy:+8.0f} trades={m.num_trades:4d} win={m.win_rate_pct:3.0f}% "
            f"PF={m.profit_factor:4.2f} exp={exp:+.4f}%/t maxDD={m.max_drawdown_pct:4.1f}% "
            f"miss={r.missed_fills}")


def main() -> int:
    fx = load("candles_FX_BTC_JPY.csv")
    leader = load("binance_BTCUSDT_1m.csv")["close"]
    merged = fx.join(leader.rename("leader_close"), how="inner").dropna()
    print(f"aligned bars: {len(merged)}  span: {merged.index[0]} .. {merged.index[-1]}")
    print(f"round-trip cost estimate: taker ~{2*(0.0235/2+0.02):.3f}% | maker ~0% + fill risk")
    print("\nlead-lag Binance BTCUSDT -> bitFlyer FX_BTC_JPY (1m returns):")
    print("  " + leadlag(fx["close"], leader))

    s = split_data(merged)
    train_val = pd.concat([s.training, s.validation])
    print(f"\nsplits: train+val={len(train_val)} bars, OOS={len(s.out_of_sample)} bars")

    grid = [{"k": k, "thr_pct": thr, "exit_pct": ex}
            for k, thr, ex in itertools.product([3, 5, 10], [0.05, 0.10, 0.15, 0.25], [0.03])]

    for execution in ("taker", "maker"):
        print(f"\n=== execution={execution} (selection on train+val only) ===")
        results = []
        for params in grid:
            r = run(params, train_val, execution)
            results.append((r.metrics.total_pnl_jpy, r.metrics.num_trades, params, r))
            print(f"  k={params['k']:2d} thr={params['thr_pct']:.2f} {fmt(r)}")
        viable = [x for x in results if x[1] >= 30]   # enough trades to mean anything
        if not viable:
            print("  -> no configuration with >=30 trades; nothing to take to OOS")
            continue
        best = max(viable, key=lambda x: x[0])
        print(f"  SELECTED: {best[2]} (train+val pnl {best[0]:+.0f}, {best[1]} trades)")
        oos = run(best[2], s.out_of_sample, execution)
        print(f"  OOS VERDICT: {fmt(oos)}")

    print("\nCAVEAT: trade-based candles + next-bar execution; a live paper run against")
    print("real quotes remains the deciding test before any live-money discussion.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
