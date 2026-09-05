# PIPELINE known-answer test — taker execution

Generated 2026-09-05T07:38:43.235193+00:00. seed=20260905 days=60 cost_bps=2.3 (source: config/constants.yaml bitflyer_fx_btc_jpy.realized_round_trip_bps, measured, midpoint of [2.0, 2.6])

| X planted (bps) | planted net (X-cost) | recovered net mean | SE | 95% CI | MDE | within MDE | n trades | gross t-stat |
|---|---|---|---|---|---|---|---|---|
| 0.0 | -2.3 | -0.048 | 2.4949 | [-4.938, 4.842] | 6.9858 | YES | 52 | 0.9026 |
| 3.0 | 0.7 | 2.9517 | 2.495 | [-1.9384, 7.8419] | 6.986 | YES | 52 | 2.1049 |
| 8.0 | 5.7 | 7.9513 | 2.4951 | [3.0609, 12.8417] | 6.9863 | YES | 52 | 4.1086 |

X=0 null-as-null: gross t-stat = 0.9026 (non-significant, OK)

## パイプラインの欠陥 (findings)

- src/bot/backtest/engine.py:run_backtest consumes `candles` verbatim -- no maintenance-window or bad-print filtering exists anywhere in the taker path. All 600 synthetic maintenance flat-bars and all 6 isolated bad-print bars passed into the backtest unmodified and unflagged; they did not corrupt the measured trades here only because this generator deliberately placed them outside every event/hold window -- a real event window that happened to contain one would be silently traded on.
