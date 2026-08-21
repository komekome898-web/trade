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
    run alongside it. The identity holds for ANY ModuleContext — the fields it
    carries (position, timestamps such as `signal_ts`) are only ever read by an
    ENABLED module, so extending the context additively cannot move G1 or G1b.

G1b LIVE-PATH EQUIVALENCE — the same two strategies driven through a real
    paper TradingApp on identical synthetic feeds. Decisions (side, open vs
    close, order sequence) must be identical; order SIZES may differ only by
    the documented risk-overlay size_factor, re-quantized to the product's
    min_size. The divergence is printed explicitly rather than implied away.

G2  OVERLAY — replay G1's closed trades with size_factor() applied to each
    ENTRY, sized through the live quantization and truncated where the kill
    switch would have stopped trading (MAX_CONSECUTIVE_LOSSES). PASS/FAIL rests
    on ONE thing: that engine PnL is linear in notional, which is what makes
    rescaling a replay legitimate at all. The max-drawdown delta and the
    scaled/skipped counts are printed as INFORMATION and gate nothing — one
    path on one sample cannot show a sizing convention works. Sizing
    conventions are not an edge; per-trade JPY totals are path arithmetic and
    are deliberately not reported.

G3  FAIL-CLOSED — configs that must be refused at construction: enabled with
    no gate_evidence, gate text rewritten in config, invented gate_evidence,
    gate_evidence naming a file outside docs/, gate_evidence naming a REAL
    report that never mentions the module, and an enabled module with no
    veto_entry implementation. The section is not a list of everything that
    fails: the one ACCEPTED construction is printed beside them, because a
    framework that refused everything would be useless and the honest claim is
    about WHICH edit unlocks a module, not that none does.

G4  MODULE EFFECT ON THE LIVE PATH — the engine never calls gate_entry, so no
    backtest can show what a module does. G4 drives a real paper TradingApp
    whose strategy carries a temporarily ENABLED RadarWindowModule and checks
    the three things that matter: an entry whose signal time is outside the
    window is suppressed, an entry inside it goes through at full size, and a
    CLOSE goes through even after the window has moved away. This is a
    behaviour check only — whether the module HELPS is judged from subsets of
    the champion's own paper trades (KNOWLEDGE.md §5), never from here.

Data: backtest_data/ permanent snapshots FIRST (deterministic; the public
bitFlyer history expires after 31 days, KNOWLEDGE.md §6), falling back to the
live-updated data/ collection. The source actually used is printed.
Cost model = this repo's measured Crypto CFD constants (taker/maker fee 0%,
spread 0.0235%, slippage 0.02%, swap 0.06%/day) — same constants as
scripts/research_mainbot_exits.py.

G1b and G4 reuse the paper-app helper in tests/test_composite.py, so this
script needs the dev extra (pytest) installed, like the suite it stands beside.

Run: PYTHONPATH=src python scripts/validate_composite.py
"""
from __future__ import annotations

import contextlib
import os
import shutil
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))     # tests/ helpers reused by G1b

import pandas as pd  # noqa: E402
import yaml  # noqa: E402

from bot.backtest.engine import CostModel, run_backtest  # noqa: E402
from bot.products import load_products  # noqa: E402
from bot.strategy.base import Signal, SignalType  # noqa: E402
import bot.strategy.composite as composite_mod  # noqa: E402
from bot.strategy.composite import (  # noqa: E402
    MODULE_CLASSES,
    CompositeModule,
    CompositeStrategy,
    ModuleContext,
    ModuleGateError,
    RadarWindowModule,
    build_modules,
)
from bot.strategy.xborder_momentum import XborderMomentumStrategy  # noqa: E402

# The composite reads this itself (bot.strategy.composite.DEFAULT_CONFIG_PATH);
# kept here only to assert the script and the strategy mean the same file.
CONFIG_PATH = ROOT / "config" / "composite.yaml"
assert CONFIG_PATH == composite_mod.DEFAULT_CONFIG_PATH

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

# gate_evidence for the throwaway test doubles below. It resolves under the
# scratch docs/ that harness_evidence() installs, never under the repo's own.
TEST_EVIDENCE = "RESEARCH_REPORT_2026-08-20b.md"

# A real report in the repo's docs/ that discusses none of the modules — G3
# uses it to show that an existing report cannot be borrowed to unlock a module
# it never mentions.
UNRELATED_REPORT = "RESEARCH_REPORT_2026-08-20k.md"


@contextlib.contextmanager
def harness_evidence():
    """HARNESS ONLY: point the evidence check at a scratch docs/ that names
    every module.

    gate_evidence must name a report whose text mentions the module it
    unlocks. No such report exists — nothing has been judged — so a probe that
    needs an ENABLED module cannot get one against the real docs/. This
    installs a stub for the duration of the probe and puts the real directory
    back afterwards. It unlocks nothing in the repo: the shipped config carries
    no gate_evidence at all, and G3's refusal cases run against the REAL
    docs/.
    """
    original = composite_mod.EVIDENCE_DIR
    with tempfile.TemporaryDirectory(prefix="composite_evidence_") as tmp:
        docs = Path(tmp)
        (docs / TEST_EVIDENCE).write_text(
            "validation harness stub, not a research report. Modules named so "
            "the evidence-content check resolves: "
            + ", ".join(sorted(MODULE_CLASSES)) + "\n", encoding="utf-8")
        composite_mod.EVIDENCE_DIR = docs
        try:
            yield docs
        finally:
            composite_mod.EVIDENCE_DIR = original


def utc_window(start_offset_min: int, end_offset_min: int) -> dict:
    """A radar window placed relative to the wall clock the live path reads
    (bot/main.py passes time.time() as the signal's `signal_ts`)."""
    now = datetime.now(timezone.utc)
    return {
        "window_start_utc": (now + timedelta(minutes=start_offset_min)).strftime("%H:%M"),
        "window_end_utc": (now + timedelta(minutes=end_offset_min)).strftime("%H:%M"),
    }

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

    with harness_evidence():     # an enabled module needs evidence that names it
        vetoing = CompositeStrategy(
            dict(PARAMS),
            modules=[_AlwaysVeto(enabled=True, gate_evidence=TEST_EVIDENCE)])
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
    comp_strategy = CompositeStrategy(dict(PARAMS))   # reads CONFIG_PATH itself
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
    if active:
        print("    FAIL: an enabled module makes this comparison meaningless, not")
        print("          merely different. The ENGINE calls on_candles and never")
        print("          gate_entry, so a module cannot act here at all: the run")
        print("          would silently reproduce the core signal and 'pass' while")
        print("          saying nothing about the module. Module behaviour is")
        print("          checked on the live path (G4); module VALUE is judged from")
        print("          champion paper subsets (KNOWLEDGE.md §5).")
    print(f"  trades  xborder/composite : {base.metrics.num_trades} / {comp.metrics.num_trades}")
    print(f"  log entries               : {len(log_base)} / {len(log_comp)} "
          f"({'identical' if log_base == log_comp else 'DIFFERENT'})")
    print(f"  per-trade pnl within 1e-9 : {pnl_ok}")
    print(f"  metrics identical         : {base.metrics.as_dict() == comp.metrics.as_dict()}")
    print(f"  gate_entry is identity    : {identity} (every module disabled)")
    print(f"  enabled-module probe      : {closing_ok} "
          "(entries vetoed, closes/holds pass untouched)")
    # No net-pnl / expectancy line: this gate is a trade-log IDENTITY check.
    # Printing the baseline's profitability beside it invites reading a
    # reproduction gate as a performance result, which it is not.
    print(f"  -> {'PASS' if ok else 'FAIL'}\n")
    return ok, base


# ---------------------------------------------------------------------------
# G1b live-path equivalence (real TradingApp, both strategies)
# ---------------------------------------------------------------------------
def _drive_app(workdir: Path, strategy_name: str, *, consecutive_losses: int,
               equity_peak_jpy: float | None):
    """Run one paper TradingApp on the shared synthetic feed; return its
    (decision, order-size) stream.

    The brake is set on the OVERLAY's state, never on the portfolio's: the
    portfolio's counters drive the hard risk checks and injecting into them
    would be testing the kill switch, not the overlay.
    """
    from tests.test_app_fx_integration import drive
    from tests.test_composite import LEADER, TICKS, build_test_app

    workdir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / "config", workdir / "config")
    cwd = Path.cwd()
    os.chdir(workdir)
    try:
        app = build_test_app(strategy_name=strategy_name)
        app.overlay_state.consecutive_losses = consecutive_losses
        if equity_peak_jpy is not None:
            app.overlay_state.equity_peak_jpy = equity_peak_jpy
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
                last_open = round(int(size * factor / min_size) * min_size, 8)
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
        size = round(int(budget / t["entry_price"] / min_size) * min_size, 8)
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
        CompositeStrategy(dict(PARAMS)), data,
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
    # PASS/FAIL rests on LINEARITY alone — the one thing this replay actually
    # verifies. The drawdown delta is a single path on a single sample: a
    # smaller number is not evidence the overlay works, and a larger one is not
    # evidence it is broken, so gating on it would manufacture a result.
    ok = linear
    print("G2 OVERLAY (size_factor applied to entries; exits untouched)")
    print(f"  closed trades in sample   : {len(trades)}")
    print(f"  pnl linear in notional    : {linear} (half notional halves every trade)")
    print(f"  entries filled flat/overlay: {flat['n']} / {over['n']}")
    print(f"  max drawdown JPY    flat  : {flat['max_dd_jpy']:,.0f}")
    print(f"                      overlay: {over['max_dd_jpy']:,.0f}")
    print(f"  max drawdown delta        : {dd_delta:+,.0f} JPY "
          "(INFORMATIONAL - one path, one sample; not a pass/fail criterion)")
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
    # (label, config, harness) — harness=True runs the case against the scratch
    # docs/ of harness_evidence(), so it is refused for ITS OWN reason instead
    # of tripping the evidence-content check first.
    cases = [
        ("enabled without evidence",
         {"imbalance_filter": {"enabled": True, "gate": gates["imbalance_filter"],
                               "gate_evidence": ""}}, False),
        ("gate text rewritten in config",
         {"oi_regime": {"enabled": False, "gate": "trust me"}}, False),
        ("gate key omitted in config",
         {"oi_regime": {"enabled": False}}, False),
        ("invented gate_evidence",
         {"funding_window": {"enabled": True, "gate": gates["funding_window"],
                             "gate_evidence": "RESEARCH_REPORT_never_written.md"}},
         False),
        ("gate_evidence pointing outside docs/",
         {"funding_window": {"enabled": True, "gate": gates["funding_window"],
                             "gate_evidence": "../elsewhere/" + TEST_EVIDENCE}},
         False),
        ("free-text gate_evidence",
         {"funding_window": {"enabled": True, "gate": gates["funding_window"],
                             "gate_evidence": "the lead said it was fine"}}, False),
        # Real report, right shape, right module implementation — refused only
        # because that report is about something else. radar_window has a veto
        # rule, so nothing else could refuse it.
        ("real report that never names the module",
         {"radar_window": {"enabled": True, "gate": gates["radar_window"],
                           "gate_evidence": UNRELATED_REPORT}}, False),
        ("enabled with no veto_entry implementation",
         {"funding_window": {"enabled": True, "gate": gates["funding_window"],
                             "gate_evidence": TEST_EVIDENCE}}, True),
    ]
    checks = []
    for label, raw, harness in cases:
        ctx = harness_evidence() if harness else contextlib.nullcontext()
        try:
            with ctx:
                build_modules(raw)
        except ModuleGateError as e:
            # first sentence, minus the "module 'x'" prefix the label already
            # carries, so the printed reason is the reason
            detail = str(e).split(". ")[0]
            _, _, tail = detail.partition("' ")
            detail = tail or detail
            if len(detail) > 72:                 # cut on a word, not mid-word
                detail = detail[:72].rsplit(" ", 1)[0] + " ..."
            checks.append((label, True, detail))
        else:
            checks.append((label, False, "no error raised"))

    # The ONE construction that is meant to succeed. Printing only refusals
    # would read as "nothing can enable a module", which is false: this edit
    # can, and what stops it in practice is owner approval of the report.
    with harness_evidence():
        accepted = next(
            m for m in build_modules(
                {"radar_window": {"enabled": True, "gate": gates["radar_window"],
                                  "gate_evidence": TEST_EVIDENCE}})
            if m.name == "radar_window")
    unlocked = accepted.enabled and accepted.gate_evidence == TEST_EVIDENCE

    ok = all(passed for _, passed, _ in checks) and unlocked
    print("G3 FAIL-CLOSED MODULES (construction-time gate)")
    print("  refused:")
    for label, passed, detail in checks:
        print(f"    {label:42s}: {'refused' if passed else 'ACCEPTED'} ({detail})")
    print("  accepted: enabled + evidence naming a report that mentions the module")
    print(f"    radar_window enabled                      : {unlocked} "
          f"(evidence {TEST_EVIDENCE})")
    print("    -> this IS the unlock path. The code cannot read a verdict out of")
    print("       a report; owner approval of it is the remaining gate.")
    print(f"  -> {'PASS' if ok else 'FAIL'}\n")
    return ok


# ---------------------------------------------------------------------------
# G4 module effect on the live path
# ---------------------------------------------------------------------------
def _drive_module_app(workdir: Path, window: dict, *,
                      close_window: dict | None = None) -> dict:
    """Paper TradingApp running the composite with ONE enabled RadarWindowModule.

    `close_window` (optional) is swapped in after the entry ticks, to prove an
    exit is still executed once the window has moved away from it.
    """
    from tests.test_app_fx_integration import drive
    from tests.test_composite import LEADER, TICKS, build_test_app

    workdir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / "config", workdir / "config")
    cwd = Path.cwd()
    os.chdir(workdir)
    try:
        app = build_test_app(strategy_name="composite")
        params = dict(app.settings.config["strategy"]["params"])

        def with_window(win: dict):
            return CompositeStrategy(dict(params), modules=[RadarWindowModule(
                enabled=True, gate_evidence=TEST_EVIDENCE, params=win)])

        app.strategy = with_window(window)
        drive(app, TICKS, LEADER)
        entered = app.portfolio.position_size
        closed = None
        if close_window is not None:
            app.strategy = with_window(close_window)
            drive(app, [(390, 1e7), (430, 1e7), (490, 1e7)], LEADER)
            closed = app.portfolio.position_size
        return {"position": entered, "trades": len(app.portfolio.trades),
                "after_close": closed}
    finally:
        os.chdir(cwd)


def gate_module_live_path() -> bool:
    """The only place a module's behaviour can be observed: the live path."""
    outside = utc_window(60, 120)      # window opens an hour from now
    inside = utc_window(-30, 30)       # window is open right now
    with tempfile.TemporaryDirectory(prefix="validate_composite_g4_") as tmp:
        tmp = Path(tmp)
        with harness_evidence():       # an enabled module needs naming evidence
            out = _drive_module_app(tmp / "outside", outside)
            ins = _drive_module_app(tmp / "inside", inside)
            exit_ = _drive_module_app(tmp / "exit", inside, close_window=outside)

    suppressed = out["position"] == 0.0 and out["trades"] == 0
    entered = ins["position"] != 0.0
    closes = exit_["position"] != 0.0 and exit_["after_close"] == 0.0
    ok = suppressed and entered and closes

    print("G4 MODULE EFFECT ON THE LIVE PATH (radar_window on a paper TradingApp)")
    print("  scope: the ENGINE cannot show this — it never calls gate_entry. What")
    print("         a module DOES is checked here; whether it HELPS is judged from")
    print("         champion paper subsets (KNOWLEDGE.md §5), never from this run.")
    print(f"  module              : radar_window (enabled for this probe only, "
          f"evidence {TEST_EVIDENCE})")
    print(f"  outside window {outside['window_start_utc']}-{outside['window_end_utc']}"
          f"  : position {out['position']}, trades {out['trades']} "
          f"-> entries suppressed: {suppressed}")
    print(f"  inside window  {inside['window_start_utc']}-{inside['window_end_utc']}"
          f"  : position {ins['position']} -> entry passed: {entered}")
    print(f"  close after window moved   : {exit_['position']} -> "
          f"{exit_['after_close']} (exit never blocked: {closes})")
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
    g4 = gate_module_live_path()
    results = (g1, g1b, g2, g3, g4)
    print(f"RESULT: {'ALL GATES PASS' if all(results) else 'FAILED'}")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
