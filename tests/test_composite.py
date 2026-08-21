"""CompositeStrategy: baseline equivalence, fail-closed modules, risk overlay."""
from __future__ import annotations

import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from bot.main import TradingApp
from bot.monitoring.notifier import NullNotifier
from bot.portfolio.portfolio import Portfolio
from bot.settings import Mode, RiskLimits, Settings
from bot.strategy import STRATEGIES
from bot.strategy.base import Signal, SignalType
from bot.strategy.composite import (
    CompositeModule,
    CompositeStrategy,
    ModuleContext,
    ModuleGateError,
    build_modules,
    load_composite_config,
)
from bot.strategy.xborder_momentum import XborderMomentumStrategy
from tests.conftest import FakeResponse, FakeSession
from tests.test_app_fx_integration import drive

REPO = Path(__file__).resolve().parents[1]
PARAMS = {"k": 10, "thr_pct": 0.8, "exit_pct": 0.1}


def make_candles(n=400, seed=7):
    """Random walk with a leader series that crosses the threshold both ways."""
    rng = np.random.default_rng(seed)
    p = 100 + rng.normal(0, 0.3, n).cumsum()
    leader = 1.0 + rng.normal(0, 0.003, n).cumsum()
    return pd.DataFrame({"open": p, "high": p * 1.001, "low": p * 0.999,
                         "close": p, "volume": np.ones(n),
                         "leader_close": leader})


# ---- E0 gate: composite(all modules off) == xborder_momentum ---------------
def test_registry_lookup():
    assert STRATEGIES["composite"] is CompositeStrategy
    assert isinstance(STRATEGIES["composite"](dict(PARAMS)), CompositeStrategy)


def test_equivalence_signal_for_signal():
    candles = make_candles()
    comp = CompositeStrategy(dict(PARAMS), config_path=REPO / "config" / "composite.yaml")
    base = XborderMomentumStrategy(dict(PARAMS))
    assert comp.min_history == base.min_history
    seen = set()
    for i in range(comp.min_history, len(candles)):
        window = candles.iloc[: i + 1]
        a, b = comp.on_candles(window), base.on_candles(window)
        assert a.type is b.type and a.reason == b.reason and a.indicators == b.indicators
        # gate_entry is the identity function while every module is disabled
        assert comp.gate_entry(a, ModuleContext(position_size=0.0)) is a
        seen.add(a.type)
    assert {SignalType.BUY, SignalType.SELL, SignalType.CLOSE} <= seen  # not a trivial pass


def test_core_params_from_yaml_when_config_params_absent():
    comp = CompositeStrategy({}, config_path=REPO / "config" / "composite.yaml")
    assert comp.params == {"k": 30, "thr_pct": 0.8, "exit_pct": 0.05}
    assert comp.min_history == 32


def test_config_params_override_yaml_core():
    comp = CompositeStrategy({"k": 5}, config_path=REPO / "config" / "composite.yaml")
    assert comp.params["k"] == 5 and comp.params["thr_pct"] == 0.8


# ---- module framework: fail-closed ----------------------------------------
def test_shipped_yaml_has_three_disabled_ungated_modules():
    cfg = load_composite_config(REPO / "config" / "composite.yaml")
    modules = build_modules(cfg["modules"])
    assert [m.name for m in modules] == ["imbalance_filter", "funding_window", "oi_regime"]
    for m in modules:
        assert m.enabled is False
        assert m.gate                      # pre-registered unlock criterion
        assert m.gate_evidence == ""       # nothing has passed judgment yet
    assert CompositeStrategy({}, config_path=REPO / "config" / "composite.yaml").active_modules == []


def test_enabled_without_gate_evidence_raises():
    raw = {"imbalance_filter": {"enabled": True, "gate_evidence": ""}}
    with pytest.raises(ModuleGateError, match="gate_evidence"):
        build_modules(raw)


def test_enabled_without_gate_evidence_raises_via_strategy_config(tmp_path):
    path = tmp_path / "composite.yaml"
    path.write_text(
        "core: {k: 10}\n"
        "modules:\n"
        "  imbalance_filter:\n"
        "    enabled: true\n"
        "    gate_evidence: \"\"\n", encoding="utf-8")
    with pytest.raises(ModuleGateError):
        CompositeStrategy({}, config_path=path)


def test_gate_text_cannot_be_weakened_by_config():
    raw = {"oi_regime": {"enabled": False, "gate": "vibes"}}
    with pytest.raises(ModuleGateError, match="pre-registered gate"):
        build_modules(raw)


def test_unknown_module_rejected():
    with pytest.raises(ValueError, match="unknown composite module"):
        build_modules({"moon_phase": {"enabled": False}})


def test_enabled_module_stub_raises_when_invoked():
    raw = {"funding_window": {"enabled": True, "gate_evidence": "docs/RESEARCH_REPORT_x.md",
                              "params": {"window_minutes": 30}}}
    module = next(m for m in build_modules(raw) if m.name == "funding_window")
    assert module.enabled and module.params["window_minutes"] == 30
    with pytest.raises(NotImplementedError):
        module.veto_entry(Signal(SignalType.BUY), ModuleContext())
    with pytest.raises(NotImplementedError):
        module.scale_entry(Signal(SignalType.BUY), ModuleContext())


def test_disabled_module_is_never_consulted():
    class Exploding(CompositeModule):
        NAME, GATE = "imbalance_filter", CompositeModule.GATE

        def veto_entry(self, signal, context):
            raise AssertionError("a disabled module must never be consulted")

    comp = CompositeStrategy(dict(PARAMS), modules=[Exploding(enabled=False)])
    sig = Signal(SignalType.BUY, "core")
    assert comp.gate_entry(sig, ModuleContext(position_size=0.0)) is sig


# ---- module gate never blocks an exit --------------------------------------
class AlwaysVeto(CompositeModule):
    NAME = "oi_regime"
    GATE = "oi_snapshots.csv 30-day phase-C judgment"

    def veto_entry(self, signal, context):
        return True


def _vetoing_composite():
    return CompositeStrategy(dict(PARAMS),
                             modules=[AlwaysVeto(enabled=True, gate_evidence="test-only")])


def test_module_vetoes_new_entry():
    out = _vetoing_composite().gate_entry(Signal(SignalType.BUY, "core", {"x": 1.0}),
                                          ModuleContext(position_size=0.0))
    assert out.type is SignalType.HOLD and "oi_regime" in out.reason
    assert out.indicators == {"x": 1.0}


@pytest.mark.parametrize("sig_type,pos", [
    (SignalType.CLOSE, 0.5),     # explicit flatten
    (SignalType.CLOSE, -0.5),
    (SignalType.BUY, -0.5),      # BUY that closes a short
    (SignalType.SELL, 0.5),      # SELL that closes a long
    (SignalType.HOLD, 0.0),
])
def test_module_never_blocks_a_close(sig_type, pos):
    sig = Signal(sig_type, "core")
    assert _vetoing_composite().gate_entry(sig, ModuleContext(position_size=pos)) is sig


# ---- risk overlay ----------------------------------------------------------
@pytest.mark.parametrize("peak,now,losses,expected", [
    (200000.0, 200000.0, 0, 1.0),     # at the peak, no streak
    (200000.0, 195000.0, 0, 1.0),     # 2.5% below peak -> still above the 95% line
    (200000.0, 189000.0, 0, 0.5),     # 5.5% below peak
    (200000.0, 200000.0, 3, 0.5),     # loss streak only
    (200000.0, 200000.0, 2, 1.0),     # streak below the trigger
    (200000.0, 180000.0, 4, 0.25),    # both triggers -> floor
    (0.0, 0.0, 0, 1.0),               # no equity history -> no drawdown brake
])
def test_size_factor(peak, now, losses, expected):
    assert CompositeStrategy.size_factor(peak, now, losses) == pytest.approx(expected)


def test_size_factor_boundaries():
    assert CompositeStrategy.size_factor(200000.0, 190000.0, 0) == 1.0  # exactly 95%
    assert CompositeStrategy.size_factor(200000.0, 189999.0, 0) == 0.5


def test_size_factor_floor_is_quarter():
    assert min(CompositeStrategy.size_factor(1e6, e, n)
               for e in (1e6, 5e5, 0.0) for n in (0, 3, 50)) == 0.25


def test_overlay_resets_after_a_win():
    """The consecutive-loss counter the overlay reads is the portfolio's, and
    it resets on any winning close."""
    p = Portfolio(initial_equity_jpy=200000.0, clock=lambda: 0.0)
    for _ in range(3):
        p.on_fill(symbol="FX_BTC_JPY", side="BUY", size=0.01, price=100.0)
        p.on_fill(symbol="FX_BTC_JPY", side="SELL", size=0.01, price=90.0)
    assert p.consecutive_losses == 3
    assert CompositeStrategy.size_factor(200000.0, 200000.0, p.consecutive_losses) == 0.5
    p.on_fill(symbol="FX_BTC_JPY", side="BUY", size=0.01, price=100.0)
    p.on_fill(symbol="FX_BTC_JPY", side="SELL", size=0.01, price=110.0)
    assert p.consecutive_losses == 0
    assert CompositeStrategy.size_factor(200000.0, 200000.0, p.consecutive_losses) == 1.0


# ---- app wiring ------------------------------------------------------------
@pytest.fixture
def app(tmp_path, monkeypatch):
    """Paper TradingApp on FX_BTC_JPY running the composite strategy."""
    shutil.copytree(REPO / "config", tmp_path / "config")
    monkeypatch.chdir(tmp_path)

    config = {
        "product_code": "FX_BTC_JPY",
        "candle_interval_sec": 60,
        "paper_equity_jpy": 200000,
        "sfd_guard_pct": 4.5,
        "stop_loss_pct": 0.5,
        "strategy": {"name": "composite",
                     "params": {"k": 2, "thr_pct": 0.15, "exit_pct": 0.03}},
        "leader": {"exchange": "binance", "symbol": "BTCUSDT"},
        "costs": {"slippage_pct": 0.0},
        "market_data": {"max_staleness_sec": 3600, "max_price_jump_pct": 50,
                        "max_spread_pct": 5.0},
    }
    limits = RiskLimits.from_dict({
        "MAX_ORDER_SIZE_JPY": 130000, "MAX_POSITION_SIZE_JPY": 130000,
        "MAX_DAILY_LOSS_JPY": 6000, "MAX_DRAWDOWN_PCT": 10.0,
        "MAX_OPEN_ORDERS": 1, "MAX_CONSECUTIVE_LOSSES": 5,
        "MAX_API_ERRORS_IN_ROW": 5,
    })
    settings = Settings(mode=Mode.PAPER, product_code="FX_BTC_JPY",
                        config=config, risk_limits=limits)
    session = FakeSession()
    session.set("GET", "/v1/ticker", FakeResponse(200, {
        "ltp": 10_000_000, "best_bid": 9_999_000, "best_ask": 10_001_000}))
    from bot.exchange.bitflyer_client import BitflyerClient
    client = BitflyerClient(session=session, sleep=lambda s: None)
    app = TradingApp(settings, client, NullNotifier())
    monkeypatch.setattr(app.leader_feed, "poll", lambda: None)
    return app


LEADER = {0: 100000.0, 60: 100000.0, 120: 100000.0, 180: 100000.0,
          240: 99600.0, 300: 99600.0, 360: 99610.0}
TICKS = [(30, 1e7), (90, 1e7), (150, 1e7), (210, 1e7), (270, 1e7), (330, 1e7)]


def test_app_runs_composite_at_full_size(app):
    assert isinstance(app.strategy, CompositeStrategy)
    drive(app, TICKS, LEADER)
    assert app.portfolio.position_size == pytest.approx(-0.013)  # same as xborder


def test_app_halves_new_entry_after_loss_streak(app):
    app.portfolio.consecutive_losses = 3
    drive(app, TICKS, LEADER)
    assert app.portfolio.position_size == pytest.approx(-0.006)  # 130k x 0.5


def test_app_quarters_new_entry_in_drawdown_and_streak(app):
    app.portfolio.consecutive_losses = 3
    # 7% below peak: inside MAX_DRAWDOWN_PCT (10) so the kill switch stays
    # untripped, but below the overlay's 95% line.
    app.portfolio.equity_peak_jpy = 215000.0
    drive(app, TICKS, LEADER)
    assert app.portfolio.position_size == pytest.approx(-0.003)  # 130k x 0.25


def test_overlay_never_shrinks_a_closing_order(app):
    drive(app, TICKS, LEADER)
    assert app.portfolio.position_size == pytest.approx(-0.013)
    # drawdown + loss streak while a position is open: the exit must still
    # close the FULL position, never a scaled fraction of it.
    app.portfolio.consecutive_losses = 4
    app.portfolio.equity_peak_jpy = 215000.0
    drive(app, [(390, 1e7), (430, 1e7), (490, 1e7)], LEADER)
    assert app.portfolio.position_size == 0.0
