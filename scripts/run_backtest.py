#!/usr/bin/env python3
"""Run all strategies over stored candles with Training/Validation/OOS splits.

Usage: python scripts/run_backtest.py [candles_csv]
Defaults to data/candles_<product>.csv produced by fetch_history.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd  # noqa: E402

from bot.backtest.engine import CostModel  # noqa: E402
from bot.backtest.walk_forward import evaluate_on_splits  # noqa: E402
from bot.settings import load_settings  # noqa: E402
from bot.strategy import STRATEGIES  # noqa: E402


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    settings = load_settings(root)
    csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else (
        root / "data" / f"candles_{settings.product_code}.csv")
    if not csv_path.exists():
        print(f"no candle data at {csv_path}; run scripts/fetch_history.py first")
        return 1
    candles = pd.read_csv(csv_path)
    print(f"{len(candles)} candles from {csv_path}")
    if len(candles) < 500:
        print("WARNING: fewer than 500 candles — results are not statistically meaningful")

    costs_cfg = settings.config.get("costs", {})
    costs = CostModel(
        taker_fee_pct=float(costs_cfg.get("taker_fee_pct", 0.15)),
        slippage_pct=float(costs_cfg.get("slippage_pct", 0.05)),
    )
    strat_params = settings.config.get("strategy", {}).get("params", {})

    for name, cls in STRATEGIES.items():
        params = strat_params if settings.config.get("strategy", {}).get("name") == name else {}
        print(f"\n=== {name} ===")
        results = evaluate_on_splits(cls, params, candles, costs=costs)
        for split, res in results.items():
            m = res.metrics
            print(f"  [{split}] pnl={m.total_pnl_jpy:+.0f} trades={m.num_trades} "
                  f"win={m.win_rate_pct:.0f}% PF={m.profit_factor:.2f} "
                  f"sharpe={m.sharpe_ratio:.2f} maxDD={m.max_drawdown_pct:.1f}% "
                  f"expectancy={m.expectancy_per_trade_jpy:+.1f}/trade fees={m.total_fees_jpy:.0f}")
    print("\nReminder: only OOS results count. Suspect overfitting when training >> OOS.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
