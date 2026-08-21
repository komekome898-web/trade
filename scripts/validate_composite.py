#!/usr/bin/env python3
"""Validation harness for CompositeStrategy (src/bot/strategy/composite.py).

This is NOT a research script: no hypothesis is tested, no parameter is
selected, nothing here may become an adoption argument. It is the
reproduction gate the research protocol requires of any new vehicle (§6: a new
script's baseline must reproduce the existing result trade-for-trade before
any difference is discussed), plus mechanical checks on the safety framework.
Idempotent, deterministic, no network; all writes go to a scratch directory.

G1  CORE-SIGNAL EQUIVALENCE (ENGINE PATH) — xborder_momentum vs composite with
    every module disabled, same params, same candles, through the backtest
    engine: identical trade logs (count, bar timestamps, sides, pnl to 1e-9)
    and identical metrics. The engine never calls `gate_entry`, so this gate
    covers the CORE SIGNAL only; it says nothing about the live order path.
    A veto/closing-path probe on `gate_entry` (identity while disabled, and,
    with a test-double module enabled, entries vetoed while closes pass) is
    run alongside it.

G1b LIVE-PATH EQUIVALENCE — the same two strategies driven through a real
    paper TradingApp on identical synthetic feeds. Decisions (side, open vs
    close, order sequence) must be identical; order SIZES may differ only by
    the documented risk-overlay size_factor, re-quantized to the product's
    min_size. The divergence is printed explicitly rather than implied away.

G2  OVERLAY — replay G1's closed trades with size_factor() applied to each
    ENTRY, sized through the live quantization and truncated where the kill
    switch would have stopped trading (MAX_CONSECUTIVE_LOSSES). Reported for
    the record only: max-drawdown delta and how many entries were scaled or
    skipped. Sizing conventions are not an edge and nothing here is evidence
    for adopting anything; per-trade JPY totals on one sample are path
    arithmetic and are deliberately not reported.

G3  FAIL-CLOSED — configs that must be refused at construction: enabled with
    no gate_evidence, gate text rewritten in config, invented gate_evidence,
    and an enabled module with no veto_entry implementation.

Data: backtest_data/ permanent snapshots FIRST (deterministic; the public
bitFlyer history expires after 31 days, KNOWLEDGE.md §6), falling back to the
live-updated data/ collection. The source actually used is printed.
Cost model = this repo's measured Crypto CFD constants (taker/maker fee 0%,
spread 0.0235%, slippage 0.02%, swap 0.06%/day) — same constants as
scripts/research_mainbot_exits.py.

G1b reuses the paper-app helper in tests/test_composite.py, so this script
needs the dev extra (pytest) installed, like the test suite it stands beside.

Run: PYTHONPATH=src python scripts/validate_composite.py
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))     # tests/ helpers reused by G1b

import pandas as pd  # noqa: E402
import yaml  # noqa: E402

from bot.backtest.engine import CostModel, run_backtest  # noqa: E402
from bot.products import load_products  # noqa: E402
from bot.strategy.base import Signal, SignalType  # noqa: E402
from bot.strategy.composite import (  # noqa: E402
    MODULE_CLASSES,
    CompositeModule,
    CompositeStrategy,
    ModuleContext,
    ModuleGateError,
    build_modules,
)
from bot.strategy.xborder_momentum import XborderMomentumStrategy  # noqa: E402

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

# Kill-switch limit the overlay replay must respect (config/risk_limits.yaml).
MAX_CONSECUTIVE_LOSSES = int(
    yaml.safe_load((ROOT / "config" / "risk_limits.yaml").read_text(encoding="utf-8"))
    ["MAX_CONSECUTIVE_LOSSES"])

# gate_evidence for the throwaway test doubles below: a report that exists.
TEST_EVIDENCE = "docs/RESEARCH_REPORT_2026-08-20b.md"

# backtest_data/ snapshots are permanent and deterministic -> primary source.
CANDLE_SOURCES = [
    ("backtest_data snapshot (permanent, deterministic)",
     ROOT / "backtest_data" / "candles_FX_BTC_JPY_30d_20260820.csv",
     ROOT / "backtest_data" / "binance_BTCUSDT_1m.csv"),
    ("backtest_data snapshot (permanent, deterministic)",
     ROOT / "backtest_data" / "candles_FX_BTC_JPY_20260820.csv",
     ROOT / "backtest_data" / "binance_BTCUSDT_1m.csv"),
    ("data/ collection (live-updated, expires after 31 days)",
     ROOT / "data" / "candles_FX_BTC_JPY.csv",
     ROOT / "data" / "binance_BTCUSDT_1m_full.csv"),
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
    for kind, candles_path, leader_path in CANDLE_SOURCES:
        if not (candles_path.exists() and leader_path.exists()):
            continue
        fx = _load(candles_path)[["open", "high", "low", "close", "volume"]]
        leader = _load(leader_path)["close"].rename("leader_close")
        merged = fx.join(leader, how="inner").dropna()
        if len(merged) < 500:
            continue
        label = (f"{kind}\n      {candles_path.relative_to(ROOT)} + "
                 f"{leader_path.relative_to(ROOT)}")
        return merged.reset_index(drop=True), merged.index, label
    raise SystemExit(
        "no usable candle+leader pair found; restore the backtest_data/ "
        "snapshots, or run scripts/fetch_history.py and scripts/fetch_external.py")


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
# G1 core-signal equivalence (engine path)
# ---------------------------------------------------------------------------
class _AlwaysVeto(CompositeModule):
    """Throwaway test double: the only module in this repo with a real rule."""

    NAME = "oi_regime"
    GATE = "oi_snapshots.csv 30-day phase-C judgment"

    def veto_entry(self, signal, context):
        return True


def gate_probe(comp_strategy) -> tuple[bool, bool]:
    """(identity while disabled, closing path honoured with a module enabled).

    The engine never calls gate_entry, so the veto/exit logic has to be probed
    directly: with a module enabled, a NEW entry must become HOLD while every
    signal that closes or holds an existing position passes through untouched.
    """
    probe = [Signal(t, "probe", {"x": 1.0}) for t in SignalType]
    identity = all(comp_strategy.gate_entry(s, ModuleContext(position_size=p)) is s
                   for s in probe for p in (-1.0, 0.0, 1.0))

    vetoing = CompositeStrategy(
        dict(PARAMS), modules=[_AlwaysVeto(enabled=True, gate_evidence=TEST_EVIDENCE)])
    entries = [(SignalType.BUY, 0.0), (SignalType.SELL, 0.0)]
    closes = [(SignalType.BUY, -0.5), (SignalType.SELL, 0.5),
              (SignalType.CLOSE, 0.5), (SignalType.CLOSE, -0.5),
              (SignalType.HOLD, 0.0)]
    vetoed = all(
        vetoing.gate_entry(Signal(t, "core", {"x": 1.0}),
                           ModuleContext(position_size=p)).type is SignalType.HOLD
        for t, p in entries)
    passed = all(
        vetoing.gate_entry(sig, ModuleContext(position_size=p)) is sig
        for sig, p in ((Signal(t, "core"), p) for t, p in closes))
    return identity, (vetoed and passed)


def gate_equivalence(data: pd.DataFrame, index: pd.Index) -> tuple[bool, object]:
    base = run(XborderMomentumStrategy(dict(PARAMS)), data)
    comp_strategy = CompositeStrategy(dict(PARAMS), config_path=CONFIG_PATH)
    comp = run(comp_strategy, data)

    active = comp_strategy.active_modules
    log_base, log_comp = stamped_log(base, index), stamped_log(comp, index)
    pnl_ok = len(base.trade_pnls) == len(comp.trade_pnls) and all(
        abs(a - b) <= 1e-9 for a, b in zip(base.trade_pnls, comp.trade_pnls))
    identity, closing_ok = gate_probe(comp_strategy)

    ok = (not active and log_base == log_comp and pnl_ok
          and base.metrics.as_dict() == comp.metrics.as_dict()
          and identity and closing_ok)
    print("G1 CORE-SIGNAL EQUIVALENCE (ENGINE PATH)")
    print("  scope: the backtest engine never calls gate_entry — this compares")
    print("         the CORE SIGNAL only. Live-path equivalence is G1b.")
    print(f"  active modules            : {[m.name for m in active] or 'none'}")
    print(f"  trades  xborder/composite : {base.metrics.num_trades} / {comp.metrics.num_trades}")
    print(f"  log entries               : {len(log_base)} / {len(log_comp)} "
          f"({'identical' if log_base == log_comp else 'DIFFERENT'})")
    print(f"  per-trade pnl within 1e-9 : {pnl_ok}")
    print(f"  metrics identical         : {base.metrics.as_dict() == comp.metrics.as_dict()}")
    print(f"  gate_entry is identity    : {identity} (every module disabled)")
    print(f"  enabled-module probe      : {closing_ok} "
          "(entries vetoed, closes/holds pass untouched)")
    print(f"  net pnl                   : {base.metrics.total_pnl_jpy:+.2f} JPY "
          f"(expectancy {base.metrics.expectancy_per_trade_jpy:+.2f} JPY/trade)")
    print(f"  -> {'PASS' if ok else 'FAIL'}\n")
    return ok, base


# ---------------------------------------------------------------------------
# G1b live-path equivalence (real TradingApp, both strategies)
# ---------------------------------------------------------------------------
def _drive_app(workdir: Path, strategy_name: str, *, consecutive_losses: int,
               equity_peak_jpy: float | None):
    """Run one paper TradingApp on the shared synthetic feed; return its
    (decision, order-size) stream."""
    from tests.test_app_fx_integration import drive
    from tests.test_composite import LEADER, TICKS, build_test_app

    workdir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / "config", workdir / "config")
    cwd = Path.cwd()
    os.chdir(workdir)
    try:
        app = build_test_app(strategy_name=strategy_name)
        app.portfolio.consecutive_losses = consecutive_losses
        if equity_peak_jpy is not None:
            app.portfolio.equity_peak_jpy = equity_peak_jpy
        calls: list[tuple] = []
        original = app._try_order

        def recorded(side, tick, size=None):
            order = original(side, tick, size=size)
            calls.append(((side, "close" if size is not None else "open"),
                          round(order.size, 8) if order is not None else None))
            return order

        app._try_order = recorded
        drive(app, TICKS, LEADER)
        drive(app, [(390, 1e7), (430, 1e7), (490, 1e7)], LEADER)
        return calls
    finally:
        os.chdir(cwd)


def gate_live_path() -> bool:
    min_size = load_products(ROOT)[PRODUCT].min_size
    rows = []
    with tempfile.TemporaryDirectory(prefix="validate_composite_") as tmp:
        tmp = Path(tmp)
        scenarios = [
            ("flat portfolio (factor 1.00)", 0, None, 1.0),
            ("3 losses in a row (factor 0.50)", 3, None, 0.5),
        ]
        for i, (label, losses, peak, factor) in enumerate(scenarios):
            xb = _drive_app(tmp / f"xb{i}", "xborder_momentum",
                            consecutive_losses=losses, equity_peak_jpy=peak)
            cp = _drive_app(tmp / f"cp{i}", "composite",
                            consecutive_losses=losses, equity_peak_jpy=peak)
            rows.append((label, factor, xb, cp))

    ok = True
    print("G1b LIVE-PATH EQUIVALENCE (paper TradingApp, identical synthetic feed)")
    for label, factor, xb, cp in rows:
        decisions_same = [d for d, _ in xb] == [d for d, _ in cp]
        sizes_xb = [s for _, s in xb]
        sizes_cp = [s for _, s in cp]
        # Expected composite sizes: an OPEN is the xborder size scaled by the
        # overlay factor and re-quantized; a CLOSE flattens whatever THAT app
        # opened (exits are never scaled — they exit in full).
        expected, last_open = [], None
        for (side, kind), size in xb:
            if size is None:
                expected.append(None)
            elif kind == "open":
                last_open = round(int(size * factor / min_size + 1e-9) * min_size, 8)
                expected.append(last_open)
            else:
                expected.append(last_open)
        sizes_ok = sizes_cp == expected
        ok = ok and decisions_same and sizes_ok
        print(f"  {label}")
        print(f"    decisions xborder         : {[f'{s} {k}' for s, k in (d for d, _ in xb)]}")
        print(f"    decisions composite       : {[f'{s} {k}' for s, k in (d for d, _ in cp)]}")
        print(f"    decisions identical       : {decisions_same}")
        print(f"    order sizes xb/composite  : {sizes_xb} / {sizes_cp}")
        diverged = [(d, a, b) for (d, _), a, b in zip(xb, sizes_xb, sizes_cp) if a != b]
        if diverged:
            for (side, kind), a, b in diverged:
                note = ("size_factor %.2f, quantized to %s" % (factor, min_size)
                        if kind == "open" else "flattens the smaller position in full")
                print(f"    DIVERGENCE {side + ' ' + kind:11s}: {a} -> {b} ({note})")
        else:
            print("    DIVERGENCE                : none (sizes byte-identical)")
        print(f"    sizes = size_factor only  : {sizes_ok}")
    print(f"  -> {'PASS' if ok else 'FAIL'}\n")
    return ok


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

    Honest about the live path in three ways the first draft was not:
      * entries are sized through the SAME quantization the bot uses
        (int(budget/price/min_size) * min_size), so the PnL scales by the
        realised notional, not by the raw factor;
      * an entry that quantizes below min_size is SKIPPED — no trade, no
        equity change, no effect on the loss streak;
      * the replay STOPS at MAX_CONSECUTIVE_LOSSES, because the kill switch
        would have stopped the bot there and everything after it is fiction.
    Engine PnL is linear in notional (verified by linearity_check), which is
    what makes the rescaling legitimate at all.
    """
    equity = INITIAL_EQUITY
    peak = equity
    losses = 0
    path = [equity]
    factors: list[float] = []
    traded = skipped = 0
    truncated = False
    for t in trades:
        factor = CompositeStrategy.size_factor(peak, equity, losses) if overlay else 1.0
        budget = factor * NOTIONAL
        size = round(int(budget / t["entry_price"] / min_size + 1e-9) * min_size, 8)
        if size < min_size:                # scaled entry below the product minimum
            skipped += 1
            continue                       # no fill: the equity path does not move
        factors.append(factor)
        traded += 1
        pnl = t["pnl"] * (size * t["entry_price"]) / NOTIONAL
        equity += pnl
        peak = max(peak, equity)
        if pnl < 0:
            losses += 1
        elif pnl > 0:
            losses = 0
        path.append(equity)
        if losses >= MAX_CONSECUTIVE_LOSSES:
            truncated = True               # the kill switch would stop trading here
            break
    return {"n": traded, "max_dd_jpy": _max_dd_jpy(path), "skipped": skipped,
            "truncated": truncated,
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
    dd_delta = over["max_dd_jpy"] - flat["max_dd_jpy"]
    dd_ok = dd_delta <= 1e-9
    ok = dd_ok and linear
    print("G2 OVERLAY (size_factor applied to entries; exits untouched)")
    print(f"  closed trades in sample   : {len(trades)}")
    print(f"  pnl linear in notional    : {linear} (half notional halves every trade)")
    print(f"  entries filled flat/overlay: {flat['n']} / {over['n']}")
    print(f"  max drawdown JPY    flat  : {flat['max_dd_jpy']:,.0f}")
    print(f"                      overlay: {over['max_dd_jpy']:,.0f}")
    print(f"  max drawdown delta        : {dd_delta:+,.0f} JPY "
          f"({'reduced or equal' if dd_ok else 'INCREASED'})")
    print(f"  entries scaled below 1.0  : {over['scaled_trades']} "
          f"(smallest factor {over['min_factor']:.2f})")
    print(f"  entries skipped < min_size: flat {flat['skipped']} / overlay "
          f"{over['skipped']} (min_size {min_size} {PRODUCT})")
    print(f"  replay truncated at {MAX_CONSECUTIVE_LOSSES} losses: "
          f"flat {flat['truncated']} / overlay {over['truncated']}")
    if over["scaled_trades"] == 0:
        print("  note: neither brake engaged on this sample (no 5% drawdown, no "
              "3-loss streak), so the drawdown delta compares two identical "
              "runs and says nothing about the overlay.")
    print("  note: sizing conventions are not an edge; per-trade JPY totals on "
          "one sample are path arithmetic and are not reported here.")
    print(f"  -> {'PASS' if ok else 'FAIL'}\n")
    return ok


# ---------------------------------------------------------------------------
# G3 fail-closed modules
# ---------------------------------------------------------------------------
def gate_fail_closed() -> bool:
    gates = {name: cls.GATE for name, cls in MODULE_CLASSES.items()}
    cases = [
        ("enabled without evidence",
         {"imbalance_filter": {"enabled": True, "gate": gates["imbalance_filter"],
                               "gate_evidence": ""}}),
        ("gate text rewritten in config",
         {"oi_regime": {"enabled": False, "gate": "trust me"}}),
        ("gate key omitted in config",
         {"oi_regime": {"enabled": False}}),
        ("invented gate_evidence",
         {"funding_window": {"enabled": True, "gate": gates["funding_window"],
                             "gate_evidence": "docs/RESEARCH_REPORT_never_written.md"}}),
        ("free-text gate_evidence",
         {"funding_window": {"enabled": True, "gate": gates["funding_window"],
                             "gate_evidence": "the lead said it was fine"}}),
        ("enabled with no veto_entry implementation",
         {"funding_window": {"enabled": True, "gate": gates["funding_window"],
                             "gate_evidence": TEST_EVIDENCE}}),
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
    print("G3 FAIL-CLOSED MODULES (all must be refused at CONSTRUCTION)")
    for label, passed, detail in checks:
        print(f"  {label:42s}: {'refused' if passed else 'ACCEPTED'} ({detail})")
    print(f"  -> {'PASS' if ok else 'FAIL'}\n")
    return ok


def main() -> int:
    data, index, label = load_frame()
    print(f"data: {label}")
    print(f"      {len(data)} bars, {index[0]} .. {index[-1]}")
    print(f"params: {PARAMS} stop_loss_pct={STOP_LOSS_PCT} notional={NOTIONAL:,.0f} JPY\n")
    g1, base = gate_equivalence(data, index)
    g1b = gate_live_path()
    g2 = gate_overlay(data, base)
    g3 = gate_fail_closed()
    results = (g1, g1b, g2, g3)
    print(f"RESULT: {'ALL GATES PASS' if all(results) else 'FAILED'}")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
