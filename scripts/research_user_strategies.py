#!/usr/bin/env python3
"""Evaluate the owner's playbook strategies on FX_BTC_JPY flow data:
① いなご volume-surge follow  ② ヒゲ wick reversal (15m)  ④ レンジ range fade.
(③ spread trade needs board history that does not exist yet — recording starts
separately; it cannot be backtested from trade data.)

Methodology: selection on Training+Validation only (>=30 trades), single
selected config judged on OOS. FX cost model: 0% fee, measured spread,
slippage, swap carry.
"""
from __future__ import annotations

import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

from bot.backtest.engine import CostModel, run_backtest
from bot.backtest.walk_forward import split_data
from bot.strategy import STRATEGIES

DATA = Path(__file__).resolve().parents[1] / "data"
FX_COSTS = CostModel(taker_fee_pct=0.0, maker_fee_pct=0.0,
                     slippage_pct=0.02, spread_pct=0.0235)
NOTIONAL = 110000.0


def load_flow(product: str) -> pd.DataFrame:
    df = pd.read_csv(DATA / f"flow_{product}.csv", index_col=0, parse_dates=True)
    df.index = pd.to_datetime(df.index, utc=True)
    return df


def resample_15m(flow: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame({
        "open": flow["open"].resample("15min").first(),
        "high": flow["high"].resample("15min").max(),
        "low": flow["low"].resample("15min").min(),
        "close": flow["close"].resample("15min").last(),
        "volume": flow["volume"].resample("15min").sum(),
    }).dropna()
    return out


def run(strategy_name, params, data, execution, *, sl=None, tp=None, bar_seconds=60.0):
    return run_backtest(
        STRATEGIES[strategy_name](params), data.reset_index(drop=True),
        costs=FX_COSTS, execution=execution, allow_short=True,
        swap_daily_pct=0.04, order_notional_jpy=NOTIONAL,
        initial_equity_jpy=200000.0, stop_loss_pct=sl, take_profit_pct=tp,
        bar_seconds=bar_seconds,
    )


def fmt(r):
    m = r.metrics
    exp = m.expectancy_per_trade_jpy / NOTIONAL * 100 if m.num_trades else 0.0
    return (f"pnl={m.total_pnl_jpy:+8.0f} t={m.num_trades:4d} win={m.win_rate_pct:3.0f}% "
            f"PF={m.profit_factor:4.2f} exp={exp:+.4f}%/t DD={m.max_drawdown_pct:4.1f}%")


def evaluate(title, strategy_name, grid, data, *, bar_seconds=60.0, min_trades=30):
    s = split_data(data)
    train_val = pd.concat([s.training, s.validation])
    print(f"\n{'=' * 90}\n{title}  (bars: T+V={len(train_val)}, OOS={len(s.out_of_sample)})\n{'=' * 90}")
    for execution in ("taker", "maker"):
        print(f"[{execution}]")
        results = []
        for params, sl, tp in grid:
            r = run(strategy_name, params, train_val, execution, sl=sl, tp=tp,
                    bar_seconds=bar_seconds)
            results.append((r.metrics.total_pnl_jpy, r.metrics.num_trades,
                            params, sl, tp))
            print(f"  {params} sl={sl} tp={tp}  {fmt(r)}")
        viable = [x for x in results if x[1] >= min_trades]
        if not viable:
            print(f"  -> no config with >= {min_trades} trades on T+V")
            continue
        best = max(viable, key=lambda x: x[0])
        _, _, params, sl, tp = best
        oos = run(strategy_name, params, s.out_of_sample, execution, sl=sl, tp=tp,
                  bar_seconds=bar_seconds)
        verdict = "T+V POSITIVE" if best[0] > 0 else "T+V negative"
        print(f"  SELECTED ({verdict}): {params} sl={sl} tp={tp}")
        print(f"  OOS: {fmt(oos)}")


def main() -> int:
    flow = load_flow("FX_BTC_JPY")

    inago_grid = [({"baseline_window": w, "spike_mult": m, "dir_ratio": d}, 0.4, None)
                  for w, m, d in itertools.product([60], [3, 5, 8], [0.65, 0.75])]
    evaluate("① いなご volume-surge follow (1m, SL 0.4%)", "inago", inago_grid, flow)

    flow15 = resample_15m(flow)
    wick_grid = [({"wick_body_mult": mult, "min_wick_pct": mw}, sl, tp)
                 for mult, mw, (sl, tp) in itertools.product(
                     [1.5, 2.0, 3.0], [0.10, 0.20], [(0.3, 0.3), (0.5, 0.5)])]
    evaluate("② ヒゲ wick reversal (15m)", "wick_reversal", wick_grid, flow15,
             bar_seconds=900.0, min_trades=20)

    range_grid = [({"window": w, "max_width_pct": mw, "edge_frac": 0.15}, 0.3, None)
                  for w, mw in itertools.product([60, 120], [0.3, 0.5])]
    evaluate("④ レンジ range fade (1m, SL 0.3%)", "range_fade", range_grid, flow)

    print("\n③ スプレッドトレード: 過去の板情報が存在しないため今回は検証不可。")
    print("   スプレッド記録を開始し、データが貯まり次第検証する。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
