#!/usr/bin/env python3
"""Multi-angle signal research: cross-exchange lead-lag, cross-asset,
volume-spike drift, and long-horizon swing.

All predictive claims are evaluated causally (predictor at t-1 and earlier,
target from t onward) and strategies use Training/Validation/OOS splits.

IMPORTANT CAVEAT printed with results: bitFlyer XRP_JPY candles are built from
TRADES in a thin market. A lead-lag edge measured against last-trade prices can
overstate what is capturable against live QUOTES; any promising signal must be
confirmed in paper trading against the real board before it counts.
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
COSTS = CostModel(taker_fee_pct=0.15, maker_fee_pct=0.15, slippage_pct=0.05, spread_pct=0.15)


def load(name: str) -> pd.DataFrame:
    df = pd.read_csv(DATA / name, index_col=0, parse_dates=True)
    df.index = pd.to_datetime(df.index, utc=True)
    return df


# ---------------------------------------------------------------- section A/B
def leadlag_table(target: pd.Series, predictor: pd.Series, max_lag: int = 10) -> pd.DataFrame:
    """corr( target_ret[t], predictor_ret[t-k] ) for k = 0..max_lag."""
    joined = pd.DataFrame({"t": target, "p": predictor}).dropna()
    rt = np.log(joined["t"]).diff()
    rp = np.log(joined["p"]).diff()
    rows = []
    for k in range(max_lag + 1):
        c = rt.corr(rp.shift(k))
        rows.append({"lag_min": k, "corr": c})
    return pd.DataFrame(rows)


def conditional_drift(target: pd.Series, predictor: pd.Series, k: int, m: int,
                      thresholds: list[float]) -> pd.DataFrame:
    """E[ target fwd m-min return | predictor past k-min return > thr ], causal:
    predictor window ends at t, target return measured from t to t+m."""
    joined = pd.DataFrame({"t": target, "p": predictor}).dropna()
    past = np.log(joined["p"]).diff(k)                      # (t-k, t]
    fwd = np.log(joined["t"]).shift(-m) - np.log(joined["t"])  # (t, t+m]
    rows = []
    for thr in thresholds:
        mask = past > thr
        n = int(mask.sum())
        rows.append({
            "thr_pct": thr * 100, "events": n,
            "mean_fwd_pct": float(fwd[mask].mean() * 100) if n else np.nan,
            "median_fwd_pct": float(fwd[mask].median() * 100) if n else np.nan,
            "hit_rate_pct": float((fwd[mask] > 0).mean() * 100) if n else np.nan,
        })
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ section C
class XborderMomentum(Strategy):
    """BUY when the external (leader) market's past-k-bar return exceeds a
    threshold; SELL when it turns negative. Reads leader prices from an extra
    'leader_close' column carried in the candles frame (causal: same-bar close,
    decisions execute next bar via the engine)."""

    @property
    def min_history(self) -> int:
        return int(self.params.get("k", 5)) + 2

    def on_candles(self, candles: pd.DataFrame) -> Signal:
        k = int(self.params.get("k", 5))
        thr = float(self.params.get("thr_pct", 0.3)) / 100
        if len(candles) < self.min_history:
            return Signal(SignalType.HOLD, "warmup")
        leader = candles["leader_close"]
        mom = float(np.log(leader.iloc[-1] / leader.iloc[-1 - k]))
        ind = {"leader_mom_pct": mom * 100}
        if np.isnan(mom):
            return Signal(SignalType.HOLD, "leader data gap", ind)
        if mom > thr:
            return Signal(SignalType.BUY, f"leader +{mom*100:.2f}% over {k}m", ind)
        if mom < 0:
            return Signal(SignalType.SELL, f"leader momentum negative", ind)
        return Signal(SignalType.HOLD, "no edge", ind)


class TsMomentum(Strategy):
    """Time-series momentum for swing horizons: long above N-bar SMA with a
    buffer, exit below."""

    @property
    def min_history(self) -> int:
        return int(self.params.get("period", 50)) + 2

    def on_candles(self, candles: pd.DataFrame) -> Signal:
        period = int(self.params.get("period", 50))
        buf = float(self.params.get("buffer_pct", 0.5)) / 100
        close = candles["close"]
        if len(candles) < self.min_history:
            return Signal(SignalType.HOLD, "warmup")
        sma = float(close.iloc[-period:].mean())
        c = float(close.iloc[-1])
        ind = {"sma": sma, "close": c}
        if c > sma * (1 + buf):
            return Signal(SignalType.BUY, "above SMA", ind)
        if c < sma * (1 - buf):
            return Signal(SignalType.SELL, "below SMA", ind)
        return Signal(SignalType.HOLD, "in buffer", ind)


def eval_strategy(strategy_cls, params, candles, execution="taker", label="",
                  order_notional=3000.0):
    s = split_data(candles.reset_index(drop=True))
    out = []
    for split_name, data in (("train", s.training), ("valid", s.validation),
                             ("OOS", s.out_of_sample)):
        r = run_backtest(strategy_cls(params), data.reset_index(drop=True),
                         costs=COSTS, execution=execution,
                         order_notional_jpy=order_notional)
        m = r.metrics
        exp_pct = (m.expectancy_per_trade_jpy / order_notional * 100) if m.num_trades else 0.0
        out.append(f"{split_name}: {m.total_pnl_jpy:+7.0f} JPY {m.num_trades:4d}t "
                   f"exp={exp_pct:+.3f}%/t miss={r.missed_fills}")
    print(f"  {label:42s} " + " | ".join(out))


def main() -> int:
    print("=" * 100)
    print("SECTION A/B: lead-lag correlations (1-minute log returns, 21 days)")
    print("=" * 100)
    bf_xrp = load("candles_XRP_JPY.csv")["close"]
    bb_xrp = load("bitbank_xrp_jpy_1m.csv")["close"]
    bn_xrp = load("binance_XRPUSDT_1m.csv")["close"]
    bn_btc = load("binance_BTCUSDT_1m.csv")["close"]

    for tgt_name, tgt in (("bitFlyer XRP_JPY", bf_xrp), ("bitbank XRP_JPY", bb_xrp)):
        for pred_name, pred in (("Binance XRPUSDT", bn_xrp), ("Binance BTCUSDT", bn_btc)):
            tbl = leadlag_table(tgt, pred, 5)
            cells = "  ".join(f"k={int(r.lag_min)}:{r.corr:+.3f}" for r in tbl.itertuples())
            print(f"{pred_name:16s} -> {tgt_name:18s} {cells}")

    print()
    print("Conditional forward drift of bitFlyer XRP_JPY after Binance XRP move")
    print("(round-trip costs: taker ~0.55%, maker ~0.30%)")
    for k, m in [(3, 5), (5, 10), (10, 15)]:
        tbl = conditional_drift(bf_xrp, bn_xrp, k, m, [0.001, 0.002, 0.003, 0.005])
        print(f"\n  predictor window k={k}min, target horizon m={m}min")
        print(tbl.to_string(index=False, float_format=lambda x: f"{x:.3f}"))

    print()
    print("=" * 100)
    print("SECTION C: cross-border momentum strategy (bitFlyer XRP_JPY, leader=Binance)")
    print("=" * 100)
    merged = load("candles_XRP_JPY.csv").join(
        bn_xrp.rename("leader_close"), how="inner").dropna()
    print(f"aligned bars: {len(merged)}")
    for execution in ("taker", "maker"):
        print(f"[execution={execution}]")
        for k, thr in [(3, 0.2), (3, 0.3), (5, 0.3), (5, 0.5), (10, 0.5)]:
            eval_strategy(XborderMomentum, {"k": k, "thr_pct": thr}, merged,
                          execution=execution, label=f"xborder k={k} thr={thr}%")

    print()
    print("=" * 100)
    print("SECTION D: volume-spike drift (bitFlyer XRP_JPY)")
    print("=" * 100)
    vol = load("candles_XRP_JPY.csv")
    v = vol["volume"]
    spike = v > v.rolling(60).mean() * 5
    fwd15 = np.log(vol["close"]).shift(-15) - np.log(vol["close"])
    up_bar = np.log(vol["close"]).diff() > 0
    for direction, mask in (("spike+up-bar", spike & up_bar), ("spike+down-bar", spike & ~up_bar)):
        n = int(mask.sum())
        print(f"  {direction:15s} events={n:5d} mean fwd15m={fwd15[mask].mean()*100:+.3f}% "
              f"hit={((fwd15[mask] > 0).mean()*100):.1f}%")

    print()
    print("=" * 100)
    print("SECTION E: swing horizons (Binance XRPUSDT, 2 years; notional-relative)")
    print("=" * 100)
    for tf in ("4h", "1d"):
        candles = load(f"binance_XRPUSDT_{tf}.csv")
        print(f"[{tf}] bars={len(candles)}")
        for execution in ("taker", "maker"):
            print(f"  [execution={execution}]")
            for params in ({"period": 20, "buffer_pct": 0.5}, {"period": 50, "buffer_pct": 0.5},
                           {"period": 100, "buffer_pct": 1.0}):
                eval_strategy(TsMomentum, params, candles, execution=execution,
                              label=f"tsmom {params}")
    print()
    print("CAVEAT: bitFlyer XRP_JPY candles are trade-based in a thin market; any")
    print("lead-lag result must be confirmed against live quotes in paper trading.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
