#!/usr/bin/env python3
"""Validation harness for CompositeStrategy (src/bot/strategy/composite.py).

This is NOT a research script: no hypothesis is tested, no parameter is
selected, nothing here may become an adoption argument. It is the
reproduction gate the research protocol requires of any new vehicle (§6: a new
script's baseline must reproduce the existing result trade-for-trade before
any difference is discussed), plus two mechanical checks on the safety
framework. Idempotent, deterministic, no network, writes nothing.

G1 EQUIVALENCE — xborder_momentum vs composite with every module disabled,
   same params, same candles: identical trade logs (count, bar timestamps,
   sides, pnl to 1e-9), identical metrics, and gate_entry as the identity
   function. This is the E0 gate of the build.

G2 OVERLAY — replay G1's trade sequence with size_factor() applied to each
   ENTRY (equity peak and loss streak evolve from the scaled PnL). Engine PnL
   is linear in notional, so scaling cannot change per-trade % expectancy:
   that is asserted to 1e-9, and any drift would mean the overlay had leaked
   into the signal. Max drawdown JPY must come out <= baseline. Also reported:
   how many entries round below FX_BTC_JPY min_size and would be skipped.
   Reported for the record only — sizing conventions are not an edge and
   nothing here is evidence for adopting anything.

G3 FAIL-CLOSED — a composite built with imbalance_filter enabled and empty
   gate_evidence must raise ModuleGateError.

Data: data/candles_FX_BTC_JPY.csv joined to the Binance BTCUSDT leader
(data/binance_BTCUSDT_1m_full.csv); falls back to the permanent
backtest_data/ snapshots, since the public bitFlyer history expires after
31 days (KNOWLEDGE.md §6). Cost model = this repo's measured Crypto CFD
constants (taker/maker fee 0%, spread 0.0235%, slippage 0.02%, swap
0.06%/day) — same constants as scripts/research_mainbot_exits.py.

Run: PYTHONPATH=src python scripts/validate_composite.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd  # noqa: E402

from bot.backtest.engine import CostModel, run_backtest  # noqa: E402
from bot.products import load_products  # noqa: E402
from bot.strategy.base import Signal, SignalType  # noqa: E402
from bot.strategy.composite import (  # noqa: E402
    CompositeStrategy,
    ModuleContext,
    ModuleGateError,
    build_modules,
)
from bot.strategy.xborder_momentum import XborderMomentumStrategy  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "composite.yaml"

FX_COSTS = CostModel(taker_fee_pct=0.0, maker_fee_pct=0.0,
                     slippage_pct=0.02, spread_pct=0.0235)
SWAP_DAILY_PCT = 0.06
NOTIONAL = 110000.0         # ~0.01 BTC-CFD
INITIAL_EQUITY = 200000.0   # config.yaml paper_equity_jpy
PRODUCT = "FX_BTC_JPY"

# Frozen entry/exit params (config/config.yaml strategy.params, mirrored in
# config/composite.yaml core). Nothing in this script may change them.
PARAMS = {"k": 30, "thr_pct": 0.8, "exit_pct": 0.05}
STOP_LOSS_PCT = 0.5

CANDLE_SOURCES = [
    (ROOT / "data" / "candles_FX_BTC_JPY.csv",
     ROOT / "data" / "binance_BTCUSDT_1m_full.csv"),
    (ROOT / "backtest_data" / "candles_FX_BTC_JPY_30d_20260820.csv",
     ROOT / "backtest_data" / "binance_BTCUSDT_1m.csv"),
    (ROOT / "backtest_data" / "candles_FX_BTC_JPY_20260820.csv",
     ROOT / "backtest_data" / "binance_BTCUSDT_1m.csv"),
]


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
def _load(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    df.index = pd.to_datetime(df.index, utc=True)
    return df


def load_frame() -> tuple[pd.DataFrame, pd.Index, str]:
    """First available (candles, leader) pair, inner-joined on timestamp."""
    for candles_path, leader_path in CANDLE_SOURCES:
        if not (candles_path.exists() and leader_path.exists()):
            continue
        fx = _load(candles_path)[["open", "high", "low", "close", "volume"]]
        leader = _load(leader_path)["close"].rename("leader_close")
        merged = fx.join(leader, how="inner").dropna()
        if len(merged) < 500:
            continue
        label = f"{candles_path.relative_to(ROOT)} + {leader_path.relative_to(ROOT)}"
        return merged.reset_index(drop=True), merged.index, label
    raise SystemExit(
        "no usable candle+leader pair found; run scripts/fetch_history.py and "
        "scripts/fetch_external.py, or restore the backtest_data/ snapshots")


# ---------------------------------------------------------------------------
# Runs
# ---------------------------------------------------------------------------
def run(strategy, data: pd.DataFrame):
    return run_backtest(
        strategy, data, costs=FX_COSTS, execution="taker", allow_short=True,
        swap_daily_pct=SWAP_DAILY_PCT, order_notional_jpy=NOTIONAL,
        initial_equity_jpy=INITIAL_EQUITY, stop_loss_pct=STOP_LOSS_PCT,
    )


def stamped_log(result, index: pd.Index) -> list[tuple]:
    """Trade log reduced to the comparable fields, bar -> UTC timestamp."""
    return [(str(index[e["bar"]]), e["side"], round(e["price"], 9),
             round(e.get("pnl", 0.0), 9), e.get("reason", ""))
            for e in result.trade_log]


# ---------------------------------------------------------------------------
# G1 equivalence
# ---------------------------------------------------------------------------
def gate_equivalence(data: pd.DataFrame, index: pd.Index) -> tuple[bool, object, object]:
    base = run(XborderMomentumStrategy(dict(PARAMS)), data)
    comp_strategy = CompositeStrategy(dict(PARAMS), config_path=CONFIG_PATH)
    comp = run(comp_strategy, data)

    active = comp_strategy.active_modules
    log_base, log_comp = stamped_log(base, index), stamped_log(comp, index)
    pnl_ok = len(base.trade_pnls) == len(comp.trade_pnls) and all(
        abs(a - b) <= 1e-9 for a, b in zip(base.trade_pnls, comp.trade_pnls))
    # gate_entry must be the identity function while every module is disabled
    probe = [Signal(t, "probe", {"x": 1.0}) for t in SignalType]
    gate_ok = all(comp_strategy.gate_entry(s, ModuleContext(position_size=p)) is s
                  for s in probe for p in (-1.0, 0.0, 1.0))

    ok = (not active and log_base == log_comp and pnl_ok
          and base.metrics.as_dict() == comp.metrics.as_dict())
    print("G1 EQUIVALENCE (composite with all modules off == xborder_momentum)")
    print(f"  active modules            : {[m.name for m in active] or 'none'}")
    print(f"  trades  xborder/composite : {base.metrics.num_trades} / {comp.metrics.num_trades}")
    print(f"  log entries               : {len(log_base)} / {len(log_comp)} "
          f"({'identical' if log_base == log_comp else 'DIFFERENT'})")
    print(f"  per-trade pnl within 1e-9 : {pnl_ok}")
    print(f"  metrics identical         : {base.metrics.as_dict() == comp.metrics.as_dict()}")
    print(f"  gate_entry is identity    : {gate_ok}")
    print(f"  net pnl                   : {base.metrics.total_pnl_jpy:+.2f} JPY "
          f"(expectancy {base.metrics.expectancy_per_trade_jpy:+.2f} JPY/trade)")
    print(f"  -> {'PASS' if ok and gate_ok else 'FAIL'}\n")
    return ok and gate_ok, base, comp


# ---------------------------------------------------------------------------
# G2 overlay simulation
# ---------------------------------------------------------------------------
def _paired_trades(result) -> list[dict]:
    opens = [e for e in result.trade_log if e["side"].startswith("OPEN_")]
    closes = [e for e in result.trade_log if e["side"].startswith("CLOSE_")]
    if len(opens) != len(closes):
        opens = opens[:len(closes)]        # a position still open at the end
    return [{"entry_price": o["price"], "pnl": c["pnl"]} for o, c in zip(opens, closes)]


def _max_dd_jpy(path: list[float]) -> float:
    peak, dd = path[0], 0.0
    for equity in path:
        peak = max(peak, equity)
        dd = max(dd, peak - equity)
    return dd


def simulate(trades: list[dict], *, overlay: bool, min_size: float):
    """Replay the closed trades, optionally scaling each ENTRY by size_factor.

    Engine PnL is linear in notional (size = notional/price, and every cost
    term scales with size), so a factor f on the entry scales that trade's PnL
    by exactly f. Exits are never scaled.
    """
    equity = INITIAL_EQUITY
    peak = equity
    losses = 0
    path = [equity]
    scaled_pnls: list[float] = []
    factors: list[float] = []
    skipped = 0
    for t in trades:
        factor = CompositeStrategy.size_factor(peak, equity, losses) if overlay else 1.0
        steps = int(factor * NOTIONAL / t["entry_price"] / min_size)
        if steps * min_size < min_size:    # scaled entry below the product minimum
            skipped += 1
        factors.append(factor)
        pnl = t["pnl"] * factor
        scaled_pnls.append(pnl)
        equity += pnl
        peak = max(peak, equity)
        if pnl < 0:
            losses += 1
        elif pnl > 0:
            losses = 0
        path.append(equity)
    n = len(scaled_pnls)
    exp_pct = sum(p / (f * NOTIONAL) for p, f in zip(scaled_pnls, factors)) / n * 100 if n else 0.0
    return {"n": n, "expectancy_pct": exp_pct, "max_dd_jpy": _max_dd_jpy(path),
            "total_pnl": sum(scaled_pnls), "skipped": skipped,
            "min_factor": min(factors) if factors else 1.0,
            "scaled_trades": sum(1 for f in factors if f < 1.0)}


def linearity_check(data: pd.DataFrame, base) -> bool:
    """The overlay simulation assumes engine PnL is linear in notional. Verify
    it on the real run rather than asserting it: half the notional must halve
    every single trade's PnL exactly."""
    half = run_backtest(
        CompositeStrategy(dict(PARAMS), config_path=CONFIG_PATH), data,
        costs=FX_COSTS, execution="taker", allow_short=True,
        swap_daily_pct=SWAP_DAILY_PCT, order_notional_jpy=NOTIONAL / 2,
        initial_equity_jpy=INITIAL_EQUITY, stop_loss_pct=STOP_LOSS_PCT,
    )
    return len(half.trade_pnls) == len(base.trade_pnls) and all(
        abs(h * 2 - f) <= 1e-9 * max(1.0, abs(f))
        for h, f in zip(half.trade_pnls, base.trade_pnls))


def gate_overlay(data: pd.DataFrame, base) -> bool:
    trades = _paired_trades(base)
    min_size = load_products(ROOT)[PRODUCT].min_size
    flat = simulate(trades, overlay=False, min_size=min_size)
    over = simulate(trades, overlay=True, min_size=min_size)
    linear = linearity_check(data, base)
    exp_same = abs(flat["expectancy_pct"] - over["expectancy_pct"]) <= 1e-9
    dd_ok = over["max_dd_jpy"] <= flat["max_dd_jpy"] + 1e-9
    ok = exp_same and dd_ok and linear
    print("G2 OVERLAY (size_factor applied to entries; exits untouched)")
    print(f"  closed trades             : {flat['n']}")
    print(f"  pnl linear in notional    : {linear} (half notional halves every trade)")
    print(f"  expectancy %/trade  flat  : {flat['expectancy_pct']:+.6f}%")
    print(f"                      overlay: {over['expectancy_pct']:+.6f}% "
          f"({'unchanged' if exp_same else 'CHANGED'})")
    print(f"  max drawdown JPY    flat  : {flat['max_dd_jpy']:,.0f}")
    print(f"                      overlay: {over['max_dd_jpy']:,.0f} "
          f"({'reduced or equal' if dd_ok else 'INCREASED'})")
    print(f"  total pnl JPY  flat/overlay: {flat['total_pnl']:+,.0f} / {over['total_pnl']:+,.0f}")
    print(f"  entries scaled below 1.0  : {over['scaled_trades']} "
          f"(smallest factor {over['min_factor']:.2f})")
    print(f"  entries skipped < min_size: {over['skipped']} "
          f"(min_size {min_size} {PRODUCT})")
    print("  note: any total-pnl difference is path arithmetic on ONE sample, "
          "not an edge.")
    print(f"  -> {'PASS' if ok else 'FAIL'}\n")
    return ok


# ---------------------------------------------------------------------------
# G3 fail-closed modules
# ---------------------------------------------------------------------------
def gate_fail_closed() -> bool:
    cases = [
        ("imbalance_filter enabled without evidence",
         {"imbalance_filter": {"enabled": True, "gate_evidence": ""}}),
        ("gate text rewritten in config",
         {"oi_regime": {"enabled": False, "gate": "trust me"}}),
    ]
    checks = []
    for label, raw in cases:
        try:
            build_modules(raw)
        except ModuleGateError as e:
            checks.append((label, True, type(e).__name__))
        else:
            checks.append((label, False, "no error raised"))
    ok = all(passed for _, passed, _ in checks)
    print("G3 FAIL-CLOSED MODULES")
    for label, passed, detail in checks:
        print(f"  {label:42s}: {'refused' if passed else 'ACCEPTED'} ({detail})")
    print(f"  -> {'PASS' if ok else 'FAIL'}\n")
    return ok


def main() -> int:
    data, index, label = load_frame()
    print(f"data: {label}")
    print(f"      {len(data)} bars, {index[0]} .. {index[-1]}")
    print(f"params: {PARAMS} stop_loss_pct={STOP_LOSS_PCT} notional={NOTIONAL:,.0f} JPY\n")
    g1, base, _ = gate_equivalence(data, index)
    g2 = gate_overlay(data, base)
    g3 = gate_fail_closed()
    print(f"RESULT: {'ALL GATES PASS' if all((g1, g2, g3)) else 'FAILED'}")
    return 0 if all((g1, g2, g3)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
