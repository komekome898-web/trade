#!/usr/bin/env python3
"""Anchor-reversion research: does bitFlyer FX_BTC_JPY mean-revert toward
Binance BTCUSDT after an IDIOSYNCRATIC local move?

Pre-registered hypothesis (lead): Binance BTCUSDT is the global price-discovery
anchor. When FX_BTC_JPY's own w-minute return departs from Binance's w-minute
return, that local deviation (stop runs, local liquidation flow) mean-reverts
toward the anchor. So FADE the deviation: SHORT the CFD when it has outrun
Binance to the upside, LONG when it has undershot. This is the opposite side of
the failed basis-fade, which anchored on laggy bitFlyer spot; here the anchor is
the LEADER, so the fade trades WITH the leader's information against local noise.

CAVEAT (stated up front): the deviation is measured JPY-vs-USD without a USDJPY
series, so USDJPY moves leak into it. At horizons <= 60 min USDJPY noise is
~2-6 bps, well under the deviation magnitudes of interest (>= 20 bps), but the
contamination is real and is NOT removed here.

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
from bot.strategy.base import Signal, SignalType, Strategy

DATA = Path(__file__).resolve().parents[1] / "data"

# FX_BTC_JPY: taker/maker fee 0%. Spread measured live at 0.0235%; slippage
# conservative for a deep book. Swap 0.06%/day accrues on carried positions.
FX_COSTS = CostModel(taker_fee_pct=0.0, maker_fee_pct=0.0,
                     slippage_pct=0.02, spread_pct=0.0235)
SWAP_DAILY_PCT = 0.06
NOTIONAL = 110000.0        # ~0.01 BTC
EQUITY = 200000.0
STOP_LOSS_PCT = 0.5
SD_WINDOW = 1440           # 24h of 1m bars for the causal deviation sd
WINDOWS = (15, 30, 60)
Z_ENTRIES = (1.5, 2.0, 2.5)
Z_EXIT = 0.5
HORIZONS = (15, 30, 60)
MIN_TRADES = 30


# --------------------------------------------------------------------------
# strategy under test (local to the research script until it earns promotion)
# --------------------------------------------------------------------------
class AnchorReversion(Strategy):
    """SHORT when the local CFD has outrun the anchor, LONG when it lags.

    z = deviation_w / rolling_sd(deviation_w, SD_WINDOW), all computed from the
    candle slice the engine hands us — no future data touched.
    """

    @property
    def min_history(self) -> int:
        return int(self.params.get("w", 30)) + int(self.params.get("sd_window", SD_WINDOW))

    def _z(self, candles: pd.DataFrame) -> float | None:
        w = int(self.params.get("w", 30))
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
        z_x = float(self.params.get("z_exit", Z_EXIT))
        z = self._z(candles)
        if z is None:
            return Signal(SignalType.HOLD, "insufficient/invalid leader data")
        ind = {"z": z}
        if z > z_e:
            return Signal(SignalType.SELL, f"local rich vs anchor (z={z:+.2f})", ind)
        if z < -z_e:
            return Signal(SignalType.BUY, f"local cheap vs anchor (z={z:+.2f})", ind)
        if abs(z) < z_x:
            return Signal(SignalType.CLOSE, f"deviation closed (z={z:+.2f})", ind)
        return Signal(SignalType.HOLD, f"between bands (z={z:+.2f})", ind)


# --------------------------------------------------------------------------
# data
# --------------------------------------------------------------------------
def load(name: str) -> pd.DataFrame:
    df = pd.read_csv(DATA / name, index_col=0, parse_dates=True)
    df.index = pd.to_datetime(df.index, utc=True)
    return df


def deviation(merged: pd.DataFrame, w: int) -> pd.Series:
    """deviation_w(t) = [log(FX_t/FX_{t-w}) - log(BN_t/BN_{t-w})] * 1e4 (bps)."""
    lf = np.log(merged["close"])
    lb = np.log(merged["leader_close"])
    return ((lf - lf.shift(w)) - (lb - lb.shift(w))) * 1e4


def ar1(s: pd.Series) -> float:
    x = s.dropna()
    return float(x.corr(x.shift(1)))


# --------------------------------------------------------------------------
# reporting helpers
# --------------------------------------------------------------------------
def fmt(r) -> str:
    m = r.metrics
    exp = m.expectancy_per_trade_jpy / NOTIONAL * 100 if m.num_trades else 0.0
    return (f"pnl={m.total_pnl_jpy:+8.0f} trades={m.num_trades:4d} win={m.win_rate_pct:3.0f}% "
            f"PF={m.profit_factor:4.2f} exp={exp:+.4f}%/t maxDD={m.max_drawdown_pct:4.1f}% "
            f"miss={r.missed_fills}")


def run(params: dict, data: pd.DataFrame, execution: str):
    return run_backtest(
        AnchorReversion(params), data.reset_index(drop=True),
        costs=FX_COSTS, execution=execution, allow_short=True,
        swap_daily_pct=SWAP_DAILY_PCT, order_notional_jpy=NOTIONAL,
        initial_equity_jpy=EQUITY, stop_loss_pct=STOP_LOSS_PCT,
    )


def main() -> int:
    fx = load("candles_FX_BTC_JPY.csv")
    leader = load("binance_BTCUSDT_1m.csv")["close"]
    merged = fx.join(leader.rename("leader_close"), how="inner").dropna()
    span_days = (merged.index[-1] - merged.index[0]).total_seconds() / 86400
    print("=" * 78)
    print("ANCHOR REVERSION RESEARCH — FX_BTC_JPY vs Binance BTCUSDT")
    print("=" * 78)
    print(f"aligned bars: {len(merged)}  span: {merged.index[0]} .. {merged.index[-1]}"
          f"  ({span_days:.2f} days)")
    print(f"costs: fee 0% | spread {FX_COSTS.spread_pct}% | slip {FX_COSTS.slippage_pct}% "
          f"| swap {SWAP_DAILY_PCT}%/day | stop {STOP_LOSS_PCT}%")
    print(f"round-trip taker cost ~{2*(FX_COSTS.spread_pct/2+FX_COSTS.slippage_pct):.3f}% "
          f"= {2*(FX_COSTS.spread_pct/2+FX_COSTS.slippage_pct)*100:.1f} bps")
    print("CAVEAT: deviation is JPY-vs-USD with no USDJPY series; at <=60m USDJPY")
    print("        noise is ~2-6 bps vs deviations of interest >=20 bps. Not removed.")

    devs = {w: deviation(merged, w) for w in WINDOWS}

    # ---------------- (a) descriptives ----------------
    print("\n" + "-" * 78)
    print("(a) DEVIATION DESCRIPTIVES  deviation_w = [logret_FX(w) - logret_BN(w)] * 1e4 bps")
    print("-" * 78)
    print(f"{'w':>4} {'n':>7} {'sd(bps)':>9} {'p1':>9} {'p99':>9} {'AR(1)':>8} {'mean':>8}")
    for w in WINDOWS:
        d = devs[w].dropna()
        print(f"{w:>4} {len(d):>7} {d.std():>9.2f} {d.quantile(0.01):>9.2f} "
              f"{d.quantile(0.99):>9.2f} {ar1(devs[w]):>8.4f} {d.mean():>8.2f}")
    print("note: AR(1) of the LEVEL is near 1 by construction (overlapping w-bar")
    print("      windows share w-1 increments); read it as persistence, not signal.")

    # ---------------- (b) causal event table ----------------
    print("\n" + "-" * 78)
    print("(b) CAUSAL EVENT TABLE — forward FX log-return (bps) after |z| > thr")
    print(f"    z = deviation_w / rolling_sd(deviation_w, {SD_WINDOW}m, data through t)")
    print("-" * 78)
    lfx = np.log(merged["close"])
    fwd = {h: ((lfx.shift(-h) - lfx) * 1e4) for h in HORIZONS}
    print(f"{'w':>4} {'thr':>5} {'side':>6} " +
          "".join(f"{'h='+str(h)+'m: n/mean/t':>26}" for h in HORIZONS))
    base_cells = []
    for h in HORIZONS:
        f = fwd[h].dropna()
        t = f.mean() / (f.std(ddof=1) / np.sqrt(len(f)))
        base_cells.append(f"{len(f):>8d} {f.mean():>+9.2f} {t:>+7.2f}")
    print(f"{'--':>4} {'--':>5} {'ALL':>6} " + "".join(base_cells) +
          "   <- unconditional baseline")
    for w in WINDOWS:
        z = devs[w] / devs[w].rolling(SD_WINDOW, min_periods=SD_WINDOW).std()
        for thr in Z_ENTRIES:
            for side, mask in (("z>+t", z > thr), ("z<-t", z < -thr)):
                cells = []
                for h in HORIZONS:
                    f = fwd[h][mask].dropna()
                    n = len(f)
                    if n < 2:
                        cells.append(f"{'n=0':>26}")
                        continue
                    mu = f.mean()
                    t = mu / (f.std(ddof=1) / np.sqrt(n)) if f.std(ddof=1) > 0 else 0.0
                    cells.append(f"{n:>8d} {mu:>+9.2f} {t:>+7.2f}")
                print(f"{w:>4} {thr:>5.1f} {side:>6} " + "".join(cells))
    print("hypothesis: mean forward return NEGATIVE after z>+thr, POSITIVE after z<-thr.")
    print("READ AGAINST THE BASELINE ROW: the sample has a non-zero unconditional")
    print("drift, so a positive conditional mean only supports the LONG leg if it")
    print("exceeds the baseline; the SHORT leg needs a mean below the baseline.")
    print("t-stats are OPTIMISTIC: events overlap heavily (consecutive 1m bars stay")
    print("above the threshold) and forward windows overlap, so the effective sample")
    print("is far smaller than n. Treat |t| < ~4 as noise.")

    # ---------------- (c) strategy grid ----------------
    s = split_data(merged)
    train_val = pd.concat([s.training, s.validation])
    print("\n" + "-" * 78)
    print("(c) STRATEGY GRID — AnchorReversion (SHORT z>z_e, LONG z<-z_e, "
          f"CLOSE |z|<{Z_EXIT})")
    print("-" * 78)
    print(f"splits: train={len(s.training)} val={len(s.validation)} "
          f"train+val={len(train_val)} bars ({len(train_val)/1440:.1f}d), "
          f"OOS={len(s.out_of_sample)} bars ({len(s.out_of_sample)/1440:.1f}d)")
    print(f"warm-up per config: w + {SD_WINDOW} bars before the first signal")

    grid = [{"w": w, "z_entry": ze, "z_exit": Z_EXIT, "sd_window": SD_WINDOW}
            for w, ze in itertools.product(WINDOWS, Z_ENTRIES)]

    verdicts = {}
    for execution in ("taker", "maker"):
        print(f"\n=== execution={execution} (selection on train+val ONLY) ===")
        results = []
        for params in grid:
            r = run(params, train_val, execution)
            results.append((r.metrics.total_pnl_jpy, r.metrics.num_trades, params, r))
            print(f"  w={params['w']:2d} z_e={params['z_entry']:.1f} {fmt(r)}")
        viable = [x for x in results if x[1] >= MIN_TRADES]
        if not viable:
            print(f"  -> no configuration with >={MIN_TRADES} trades; nothing to take to OOS")
            verdicts[execution] = (None, None, None)
            continue
        best = max(viable, key=lambda x: x[0])
        print(f"  SELECTED: w={best[2]['w']} z_e={best[2]['z_entry']} "
              f"(train+val pnl {best[0]:+.0f}, {best[1]} trades)")
        oos = run(best[2], s.out_of_sample, execution)
        print(f"  OOS VERDICT: {fmt(oos)}")
        verdicts[execution] = (best[2], best[3], oos)
        # diagnostic: how much of the loss is the 0.5% protective stop firing?
        stop_jpy = -STOP_LOSS_PCT / 100 * NOTIONAL * 0.9   # ~-495 JPY, incl. costs
        for label, res in (("T+V", best[3]), ("OOS", oos)):
            pnls = np.array(res.trade_pnls)
            if not len(pnls):
                continue
            stops = pnls[pnls <= stop_jpy]
            print(f"    diag {label}: {len(stops)}/{len(pnls)} trades hit the stop "
                  f"(<= {stop_jpy:.0f} JPY), contributing {stops.sum():+.0f} JPY of "
                  f"{pnls.sum():+.0f}; non-stopped trades sum {pnls[pnls > stop_jpy].sum():+.0f}")

    # ---------------- fixed decision rule ----------------
    print("\n" + "=" * 78)
    print("DECISION RULE: pass iff selected config has train+val pnl > 0 with "
          f">= {MIN_TRADES} trades AND OOS pnl > 0")
    print("=" * 78)
    any_pass = False
    for execution in ("taker", "maker"):
        params, tv, oos = verdicts[execution]
        if params is None:
            print(f"  {execution:>5}: FAIL — no config met the {MIN_TRADES}-trade floor")
            continue
        ok = (tv.metrics.total_pnl_jpy > 0 and tv.metrics.num_trades >= MIN_TRADES
              and oos.metrics.total_pnl_jpy > 0)
        any_pass = any_pass or ok
        print(f"  {execution:>5}: {'PASS' if ok else 'FAIL'} — "
              f"config w={params['w']} z_e={params['z_entry']}; "
              f"T+V pnl {tv.metrics.total_pnl_jpy:+.0f} ({tv.metrics.num_trades} trades), "
              f"OOS pnl {oos.metrics.total_pnl_jpy:+.0f} ({oos.metrics.num_trades} trades)")
    print(f"\nOVERALL: {'PASS' if any_pass else 'FAIL'} — "
          f"{'implement the strategy module' if any_pass else 'do NOT implement'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
