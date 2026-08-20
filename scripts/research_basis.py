#!/usr/bin/env python3
"""FX/spot basis mean-reversion research (pre-registered hypothesis).

Hypothesis: the basis between bitFlyer's BTC CFD (FX_BTC_JPY) and spot
BTC_JPY mean-reverts (arbitrage plus the 8-hourly funding rate push it back),
so an extreme basis should predict the CFD's OWN forward returns:
rich basis (CFD >> spot) -> CFD underperforms; cheap basis -> outperforms.

Method:
  1. Inner-join 1m candles; basis_pct = (fx_close/spot_close - 1) * 100.
  2. Descriptives + AR(1) half-life of basis deviations.
  3. Causal predictive check: rolling z-score of basis (window 1440m, the
     window ends at bar t so only data through t is used), then mean forward
     CFD log return over 30/60/120m conditional on z beyond +/-{1.5,2.0,2.5}.
  4. Walk-forward backtest of a BasisReversion rule under the FX cost model.
     Parameters are selected on Training+Validation ONLY (>=30 trades
     required); the single selected config is then judged on Out-of-Sample.

Screening rule (fixed in advance): the hypothesis passes only if the selected
config has POSITIVE train+val pnl with >=30 trades AND positive OOS pnl.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from bot.backtest.engine import CostModel, run_backtest  # noqa: E402
from bot.backtest.walk_forward import split_data  # noqa: E402
from bot.strategy.base import Signal, SignalType, Strategy  # noqa: E402

DATA = Path(__file__).resolve().parents[1] / "data"

# FX_BTC_JPY: 0% fees, measured spread 0.0235%, conservative slippage,
# 0.06%/day swap carry on any position held overnight-equivalent.
FX_COSTS = CostModel(taker_fee_pct=0.0, maker_fee_pct=0.0,
                     slippage_pct=0.02, spread_pct=0.0235)
SWAP_DAILY_PCT = 0.06
NOTIONAL = 110000.0        # ~0.01 BTC
INITIAL_EQUITY = 200000.0
Z_WINDOW = 1440            # 24h of 1-minute bars
STOP_LOSS_PCT = 0.5


# --------------------------------------------------------------------------
# strategy under test (kept local until the hypothesis clears screening)
# --------------------------------------------------------------------------
class BasisReversionStrategy(Strategy):
    """Fade an extreme FX-vs-spot basis, expecting it to revert.

    Requires a `spot_close` column alongside the CFD candles. z is the
    rolling z-score of basis_pct over `window` bars ending at the current
    (completed) bar - strictly causal.
    """

    @property
    def min_history(self) -> int:
        return int(self.params.get("window", Z_WINDOW)) + 1

    def on_candles(self, candles: pd.DataFrame) -> Signal:
        window = int(self.params.get("window", Z_WINDOW))
        z_entry = float(self.params.get("z_entry", 2.0))
        z_exit = float(self.params.get("z_exit", 0.5))

        if "spot_close" not in candles.columns:
            return Signal(SignalType.HOLD, "no spot_close column")
        if len(candles) < self.min_history:
            return Signal(SignalType.HOLD, "insufficient history")

        fx = candles["close"].iloc[-window:].to_numpy(dtype=float)
        spot = candles["spot_close"].iloc[-window:].to_numpy(dtype=float)
        if np.isnan(fx[-1]) or np.isnan(spot[-1]) or spot[-1] <= 0:
            return Signal(SignalType.HOLD, "price data gap")
        basis = (fx / spot - 1.0) * 100.0
        basis = basis[np.isfinite(basis)]
        if len(basis) < window // 2:
            return Signal(SignalType.HOLD, "basis data gap")

        mu = float(basis.mean())
        sd = float(basis.std(ddof=0))
        if sd <= 0:
            return Signal(SignalType.HOLD, "degenerate basis dispersion")
        b = float(basis[-1])
        z = (b - mu) / sd
        ind = {"basis_pct": b, "basis_z": z, "basis_mean_pct": mu, "basis_sd_pct": sd}

        if z > z_entry:
            return Signal(SignalType.SELL, f"basis rich z={z:+.2f}", ind)
        if z < -z_entry:
            return Signal(SignalType.BUY, f"basis cheap z={z:+.2f}", ind)
        if abs(z) < z_exit:
            return Signal(SignalType.CLOSE, f"basis reverted z={z:+.2f}", ind)
        return Signal(SignalType.HOLD, f"basis z={z:+.2f} between bands", ind)


# --------------------------------------------------------------------------
# data
# --------------------------------------------------------------------------
def load(name: str) -> pd.DataFrame:
    df = pd.read_csv(DATA / name, index_col=0, parse_dates=True)
    df.index = pd.to_datetime(df.index, utc=True)
    return df


def build_frame() -> pd.DataFrame:
    fx = load("candles_FX_BTC_JPY.csv")
    spot = load("candles_BTC_JPY.csv")[["close"]].rename(columns={"close": "spot_close"})
    merged = fx.join(spot, how="inner").dropna()
    merged["basis_pct"] = (merged["close"] / merged["spot_close"] - 1.0) * 100.0
    return merged


def causal_z(basis: pd.Series, window: int = Z_WINDOW) -> pd.Series:
    """Rolling z-score whose window ENDS at bar t (uses data through t only)."""
    roll = basis.rolling(window, min_periods=window)
    return (basis - roll.mean()) / roll.std(ddof=0)


# --------------------------------------------------------------------------
# reporting helpers
# --------------------------------------------------------------------------
def fmt(r) -> str:
    m = r.metrics
    exp = m.expectancy_per_trade_jpy / NOTIONAL * 100 if m.num_trades else 0.0
    pf = "inf " if m.profit_factor == float("inf") else f"{m.profit_factor:4.2f}"
    return (f"pnl={m.total_pnl_jpy:+9.0f} trades={m.num_trades:4d} "
            f"win={m.win_rate_pct:3.0f}% PF={pf} exp={exp:+.4f}%/t "
            f"maxDD={m.max_drawdown_pct:4.1f}% miss={r.missed_fills}")


def run(params: dict, data: pd.DataFrame, execution: str):
    return run_backtest(
        BasisReversionStrategy(params), data.reset_index(drop=True),
        costs=FX_COSTS, execution=execution, allow_short=True,
        swap_daily_pct=SWAP_DAILY_PCT, order_notional_jpy=NOTIONAL,
        initial_equity_jpy=INITIAL_EQUITY, stop_loss_pct=STOP_LOSS_PCT,
    )


def descriptives(df: pd.DataFrame) -> None:
    b = df["basis_pct"]
    print(f"\naligned bars: {len(df)}  span: {df.index[0]} .. {df.index[-1]}")
    print("\n--- basis_pct descriptive stats (FX over spot, %) ---")
    print(f"  mean={b.mean():+.4f}  std={b.std():.4f}  min={b.min():+.4f}  max={b.max():+.4f}")
    qs = [1, 5, 25, 50, 75, 95, 99]
    print("  percentiles: " + "  ".join(f"p{q}={b.quantile(q/100):+.4f}" for q in qs))
    print(f"  share of bars with basis > 0: {(b > 0).mean()*100:.1f}%")

    # AR(1): basis_t = a + rho * basis_{t-1};  half-life = -ln2 / ln(rho)
    x = b.shift(1).to_numpy()
    y = b.to_numpy()
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = x[ok], y[ok]
    rho, a = np.polyfit(x, y, 1)
    hl = -np.log(2) / np.log(rho) if 0 < rho < 1 else float("nan")
    resid = y - (a + rho * x)
    print(f"\n--- AR(1) on 1m basis ---  rho={rho:.6f}  intercept={a:+.6f}  "
          f"resid_sd={resid.std():.4f}")
    print(f"  half-life of a basis deviation: {hl:.1f} minutes ({hl/60:.2f} hours)")


def predictive_check(df: pd.DataFrame) -> None:
    z = causal_z(df["basis_pct"], Z_WINDOW)
    logc = np.log(df["close"])
    print(f"\n--- causal predictive check (z window={Z_WINDOW}m, "
          f"{int(z.notna().sum())} usable bars) ---")
    print("  forward CFD log return in bps, mean [t-stat] (n events)")
    header = "  {:<10}".format("cond") + "".join(f"{'h=' + str(h) + 'm':>26}"
                                                 for h in (30, 60, 120))
    print(header)
    for thr in (1.5, 2.0, 2.5):
        for label, mask in (("z>+%.1f" % thr, z > thr), ("z<-%.1f" % thr, z < -thr)):
            cells = []
            for h in (30, 60, 120):
                fwd = (logc.shift(-h) - logc) * 10000.0
                sel = fwd[mask & fwd.notna()]
                if len(sel) < 2:
                    cells.append(f"{'n/a':>26}")
                    continue
                t = sel.mean() / (sel.std(ddof=1) / np.sqrt(len(sel)))
                cells.append(f"{sel.mean():+9.2f} [{t:+6.2f}] (n={len(sel):5d})")
            print("  {:<10}".format(label) + "".join(cells))
    print("  (expect NEGATIVE on z>thr rows and POSITIVE on z<-thr rows if the "
          "hypothesis holds)")
    print("  note: overlapping horizons -> t-stats are optimistic, sign is the "
          "thing to read")

    # Which leg closes the gap? Decompose the forward basis change into the
    # CFD leg and the spot leg. Only the CFD leg is tradable by this bot.
    logs = np.log(df["spot_close"])
    print("\n--- mechanism: which leg closes the basis gap? (mean, bps) ---")
    print("  {:<9}{:>5}{:>14}{:>13}{:>14}{:>8}".format(
        "cond", "h", "d_basis", "fx_ret", "spot_ret", "n"))
    for thr in (2.0, 2.5):
        for label, mask in (("z>+%.1f" % thr, z > thr), ("z<-%.1f" % thr, z < -thr)):
            for h in (30, 120):
                db = (df["basis_pct"].shift(-h) - df["basis_pct"]) * 100.0
                rf = (logc.shift(-h) - logc) * 10000.0
                rs = (logs.shift(-h) - logs) * 10000.0
                m = mask & db.notna()
                if not m.any():
                    continue
                print("  {:<9}{:>5}{:>14.2f}{:>13.2f}{:>14.2f}{:>8d}".format(
                    label, h, db[m].mean(), rf[m].mean(), rs[m].mean(), int(m.sum())))


def main() -> int:
    df = build_frame()
    descriptives(df)
    predictive_check(df)

    s = split_data(df)
    train_val = pd.concat([s.training, s.validation])
    print(f"\n--- walk-forward splits ---")
    print(f"  train={len(s.training)} val={len(s.validation)} "
          f"train+val={len(train_val)} OOS={len(s.out_of_sample)} bars")
    print(f"  costs: fee 0% | spread {FX_COSTS.spread_pct}% | slip "
          f"{FX_COSTS.slippage_pct}% | swap {SWAP_DAILY_PCT}%/day | "
          f"notional {NOTIONAL:.0f} JPY | SL {STOP_LOSS_PCT}%")
    print(f"  round-trip taker cost ~"
          f"{2*(FX_COSTS.spread_pct/2 + FX_COSTS.slippage_pct):.3f}%")

    grid = [{"window": Z_WINDOW, "z_entry": ze, "z_exit": zx}
            for ze in (1.5, 2.0, 2.5) for zx in (0.5,)]

    verdicts = {}
    for execution in ("taker", "maker"):
        print(f"\n=== execution={execution} (selection on train+val ONLY) ===")
        results = []
        for params in grid:
            r = run(params, train_val, execution)
            results.append((r.metrics.total_pnl_jpy, r.metrics.num_trades, params, r))
            print(f"  z_entry={params['z_entry']:.1f} z_exit={params['z_exit']:.1f} "
                  f"{fmt(r)}")
        viable = [x for x in results if x[1] >= 30]
        if not viable:
            print("  -> no configuration with >=30 trades; nothing to take to OOS")
            verdicts[execution] = (None, None, None)
            continue
        best = max(viable, key=lambda x: x[0])
        print(f"  SELECTED: z_entry={best[2]['z_entry']} z_exit={best[2]['z_exit']} "
              f"(train+val pnl {best[0]:+.0f}, {best[1]} trades)")
        oos = run(best[2], s.out_of_sample, execution)
        print(f"  OOS VERDICT: {fmt(oos)}")
        verdicts[execution] = (best, oos, best[2])

    print("\n=== SCREENING RULE ===")
    print("  pass iff selected config has train+val pnl > 0 with >=30 trades "
          "AND OOS pnl > 0")
    overall = False
    for execution, (best, oos, params) in verdicts.items():
        if best is None:
            print(f"  {execution:6s}: FAIL (no config with >=30 trades)")
            continue
        tv_pnl, tv_n = best[0], best[1]
        oos_pnl = oos.metrics.total_pnl_jpy
        ok = tv_pnl > 0 and tv_n >= 30 and oos_pnl > 0
        overall = overall or ok
        print(f"  {execution:6s}: train+val pnl={tv_pnl:+.0f} ({tv_n} trades), "
              f"OOS pnl={oos_pnl:+.0f}  -> {'PASS' if ok else 'FAIL'}")
    print(f"\n  HYPOTHESIS SCREENING: {'PASS' if overall else 'FAIL'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
