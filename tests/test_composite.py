"""CompositeStrategy: baseline equivalence, fail-closed modules, risk overlay."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from bot.main import TradingApp
from bot.monitoring.notifier import Notifier, NullNotifier
from bot.portfolio.portfolio import Portfolio
from bot.risk.kill_switch import KillReason, KillSwitch
from bot.settings import Mode, RiskLimits, Settings
from bot.strategy import STRATEGIES
from bot.strategy.base import Signal, SignalType
from bot.strategy.composite import (
    CompositeModule,
    CompositeStrategy,
    ModuleContext,
    ModuleGateError,
    OverlayState,
    build_modules,
    load_composite_config,
)
from bot.strategy.xborder_momentum import XborderMomentumStrategy
from tests.conftest import FakeResponse, FakeSession
from tests.test_app_fx_integration import drive

REPO = Path(__file__).resolve().parents[1]
PARAMS = {"k": 10, "thr_pct": 0.8, "exit_pct": 0.1}
# A real report in docs/: gate_evidence must reference one that exists.
EVIDENCE = "docs/RESEARCH_REPORT_2026-08-20b.md"


class RecordingNotifier(Notifier):
    def __init__(self):
        self.sent: list[tuple[str, str, bool]] = []

    def send(self, title, message, *, urgent=False):
        self.sent.append((title, message, urgent))
        return True


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


def _raw(name: str, **overrides) -> dict:
    """A single-module config carrying the registered gate text."""
    from bot.strategy.composite import MODULE_CLASSES
    cfg = {"enabled": False, "gate": MODULE_CLASSES[name].GATE}
    cfg.update(overrides)
    return {name: cfg}


def test_enabled_without_gate_evidence_raises():
    with pytest.raises(ModuleGateError, match="gate_evidence"):
        build_modules(_raw("imbalance_filter", enabled=True, gate_evidence=""))


def test_enabled_without_gate_evidence_raises_via_strategy_config(tmp_path):
    path = tmp_path / "composite.yaml"
    path.write_text(
        "core: {k: 10}\n"
        "modules:\n"
        "  imbalance_filter:\n"
        "    enabled: true\n"
        "    gate: \"board-data judgment >= 1-2 weeks recording, per KNOWLEDGE.md §4\"\n"
        "    gate_evidence: \"\"\n", encoding="utf-8")
    with pytest.raises(ModuleGateError):
        CompositeStrategy({}, config_path=path)


def test_gate_text_cannot_be_weakened_by_config():
    with pytest.raises(ModuleGateError, match="pre-registered gate"):
        build_modules({"oi_regime": {"enabled": False, "gate": "vibes"}})


def test_missing_gate_key_is_refused():
    """The criterion must be spelled out where the module is configured;
    inheriting it silently would make the gate-match check vacuous."""
    with pytest.raises(ModuleGateError, match="without a 'gate' key"):
        build_modules({"oi_regime": {"enabled": False}})


def test_module_absent_from_config_is_simply_off():
    modules = build_modules(_raw("oi_regime"))
    assert all(m.enabled is False for m in modules)
    assert [m.name for m in modules] == ["imbalance_filter", "funding_window", "oi_regime"]


def test_unknown_module_rejected():
    with pytest.raises(ValueError, match="unknown composite module"):
        build_modules({"moon_phase": {"enabled": False}})


@pytest.mark.parametrize("evidence", ["trust me", "docs/RESEARCH_REPORT_x.md",
                                      "docs/KNOWLEDGE.md", "RESEARCH_REPORT_9999-99-99z.md"])
def test_gate_evidence_must_name_an_existing_report(evidence):
    """Invented evidence cannot unlock a module: the reference must resolve to
    a docs/RESEARCH_REPORT_*.md that actually exists and can be audited."""
    with pytest.raises(ModuleGateError, match="gate_evidence"):
        build_modules(_raw("funding_window", enabled=True, gate_evidence=evidence))


def test_evidence_is_checked_even_while_disabled():
    with pytest.raises(ModuleGateError, match="gate_evidence"):
        build_modules(_raw("funding_window", enabled=False, gate_evidence="trust me"))


def test_enabled_module_without_implementation_cannot_be_constructed():
    """B1: an enabled module whose veto rule is a stub must fail AT
    CONSTRUCTION — never at decision time, where 'no rule' could fail open."""
    raw = _raw("funding_window", enabled=True, gate_evidence=EVIDENCE,
               params={"window_minutes": 30})
    with pytest.raises(ModuleGateError, match="no veto_entry implementation"):
        build_modules(raw)


def test_stub_veto_entry_still_raises_if_called_directly():
    module = next(m for m in build_modules(_raw("funding_window")) if m.name == "funding_window")
    with pytest.raises(NotImplementedError):
        module.veto_entry(Signal(SignalType.BUY), ModuleContext())


def test_scale_entry_hook_is_gone():
    """M6: the sizing hook was dead code — only the risk overlay sizes."""
    assert not hasattr(CompositeModule, "scale_entry")


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
                             modules=[AlwaysVeto(enabled=True, gate_evidence=EVIDENCE)])


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
def app_config(strategy_name: str = "composite") -> dict:
    return {
        "product_code": "FX_BTC_JPY",
        "candle_interval_sec": 60,
        "paper_equity_jpy": 200000,
        "sfd_guard_pct": 4.5,
        "stop_loss_pct": 0.5,
        "strategy": {"name": strategy_name,
                     "params": {"k": 2, "thr_pct": 0.15, "exit_pct": 0.03}},
        "leader": {"exchange": "binance", "symbol": "BTCUSDT"},
        "costs": {"slippage_pct": 0.0},
        "market_data": {"max_staleness_sec": 3600, "max_price_jump_pct": 50,
                        "max_spread_pct": 5.0},
    }


APP_LIMITS = {
    "MAX_ORDER_SIZE_JPY": 130000, "MAX_POSITION_SIZE_JPY": 130000,
    "MAX_DAILY_LOSS_JPY": 6000, "MAX_DRAWDOWN_PCT": 10.0,
    "MAX_OPEN_ORDERS": 1, "MAX_CONSECUTIVE_LOSSES": 5,
    "MAX_API_ERRORS_IN_ROW": 5,
}


def build_test_app(monkeypatch=None, *, strategy_name="composite", notifier=None):
    """Paper TradingApp on FX_BTC_JPY. The caller must already be chdir'd into
    a writable working directory holding a config/ copy.

    Also used by scripts/validate_composite.py (gate G1b), hence the optional
    monkeypatch: outside pytest the leader feed is silenced directly."""
    settings = Settings(mode=Mode.PAPER, product_code="FX_BTC_JPY",
                        config=app_config(strategy_name),
                        risk_limits=RiskLimits.from_dict(dict(APP_LIMITS)))
    session = FakeSession()
    session.set("GET", "/v1/ticker", FakeResponse(200, {
        "ltp": 10_000_000, "best_bid": 9_999_000, "best_ask": 10_001_000}))
    from bot.exchange.bitflyer_client import BitflyerClient
    client = BitflyerClient(session=session, sleep=lambda s: None)
    app = TradingApp(settings, client, notifier or NullNotifier())
    if monkeypatch is not None:
        monkeypatch.setattr(app.leader_feed, "poll", lambda: None)
    else:
        app.leader_feed.poll = lambda: None
    return app


@pytest.fixture
def workdir(tmp_path, monkeypatch):
    shutil.copytree(REPO / "config", tmp_path / "config")
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def app(workdir, monkeypatch):
    """Paper TradingApp on FX_BTC_JPY running the composite strategy."""
    return build_test_app(monkeypatch)


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


# ---- B2: the overlay may narrow an approved order, never rescue a rejected one
def _set_daily_pnl(portfolio, jpy: float) -> None:
    portfolio.daily_pnl_jpy(0.0)            # anchor today's bucket
    portfolio._daily_realized = jpy


def test_full_size_rejection_is_not_retried_at_overlay_size(app):
    """MAX_DAILY_LOSS_JPY=6000 with daily_pnl=-5500 leaves a 500 JPY risk
    budget. Full size (0.013 BTC, ~650 JPY of stop risk) is refused; the
    halved size (~300 JPY) would pass — entering it anyway would move the
    champion's rejection boundary, so there must be NO entry at all."""
    _set_daily_pnl(app.portfolio, -5500.0)
    app.portfolio.consecutive_losses = 3     # overlay factor 0.5
    drive(app, TICKS, LEADER)
    assert app.portfolio.position_size == 0.0
    assert app.portfolio.trades == []
    assert not app.kill_switch.is_tripped    # -5500 > -6000: reject, not kill


def test_same_scenario_without_the_daily_brake_does_enter_scaled(app):
    """Control for the test above: the only thing stopping the scaled entry is
    the full-size rejection, not the overlay itself."""
    app.portfolio.consecutive_losses = 3
    drive(app, TICKS, LEADER)
    assert app.portfolio.position_size == pytest.approx(-0.006)


# ---- M14: overlay suppression is announced once per UTC day ----------------
def test_overlay_suppression_notifies_once_per_day(workdir, monkeypatch):
    notifier = RecordingNotifier()
    app = build_test_app(monkeypatch, notifier=notifier)
    # min_size 0.001 at ~1e7 JPY = 10,000 JPY; a 0.25 factor on a budget that
    # only ever buys one step rounds the entry away entirely.
    monkeypatch.setattr(app.settings.risk_limits, "max_order_size_jpy", 12000.0)
    app.portfolio.consecutive_losses = 3
    app.portfolio.equity_peak_jpy = 215000.0
    drive(app, TICKS, LEADER)
    assert app.portfolio.position_size == 0.0
    suppressed = [s for s in notifier.sent if s[0] == "OVERLAY SUPPRESSING ENTRIES"]
    assert len(suppressed) == 1
    app._try_order("SELL", app.feed.last_tick)     # same UTC day: no second alert
    app._try_order("SELL", app.feed.last_tick)
    assert len([s for s in notifier.sent if s[0] == "OVERLAY SUPPRESSING ENTRIES"]) == 1
    app._overlay_suppressed_day -= 1               # next UTC day
    app._try_order("SELL", app.feed.last_tick)
    assert len([s for s in notifier.sent if s[0] == "OVERLAY SUPPRESSING ENTRIES"]) == 2


# ---- M5: the overlay brake survives a restart ------------------------------
def test_overlay_state_persists_across_restart(workdir, monkeypatch):
    app = build_test_app(monkeypatch)
    app.portfolio.consecutive_losses = 4
    app.portfolio.equity_peak_jpy = 215000.0
    app._persist_overlay_state(1e7)
    assert (workdir / "data" / "overlay_state.json").exists()

    restarted = build_test_app(monkeypatch)      # simulated process restart
    assert restarted.portfolio.consecutive_losses == 4
    assert restarted.portfolio.equity_peak_jpy == pytest.approx(215000.0)
    # and the brake is actually in force after the restart
    drive(restarted, TICKS, LEADER)
    assert restarted.portfolio.position_size == pytest.approx(-0.003)


def test_closing_trade_checkpoints_overlay_state(app, workdir):
    drive(app, TICKS, LEADER)
    assert not (workdir / "data" / "overlay_state.json").exists()   # entry only
    drive(app, [(390, 1e7), (430, 1e7), (490, 1e7)], LEADER)
    assert app.portfolio.position_size == 0.0
    saved = json.loads((workdir / "data" / "overlay_state.json").read_text(encoding="utf-8"))
    assert saved["consecutive_losses"] == app.portfolio.consecutive_losses
    assert saved["equity_peak_jpy"] == pytest.approx(app.portfolio.equity_peak_jpy)


@pytest.mark.parametrize("content", ["", "{not json", '{"consecutive_losses": 3}',
                                     '{"consecutive_losses": "x", "equity_peak_jpy": 1}'])
def test_corrupt_overlay_state_degrades_to_safe_defaults(workdir, monkeypatch, content):
    (workdir / "data").mkdir(exist_ok=True)
    (workdir / "data" / "overlay_state.json").write_text(content, encoding="utf-8")
    app = build_test_app(monkeypatch)            # must not raise
    assert app.portfolio.consecutive_losses == 0
    assert app.portfolio.equity_peak_jpy == pytest.approx(200000.0)


def test_missing_overlay_state_degrades_to_safe_defaults(workdir, monkeypatch):
    assert not (workdir / "data" / "overlay_state.json").exists()
    app = build_test_app(monkeypatch)
    assert app.portfolio.consecutive_losses == 0
    assert app.portfolio.equity_peak_jpy == pytest.approx(200000.0)


def test_overlay_state_roundtrip_is_utf8_json(tmp_path):
    path = tmp_path / "nested" / "overlay_state.json"
    OverlayState(consecutive_losses=2, equity_peak_jpy=123.5).save(path)
    assert OverlayState.load(path) == OverlayState(2, 123.5)


# ---- B1(b): an unhandled exception must trip the persisted kill switch -----
def test_unhandled_step_exception_trips_kill_switch(workdir, monkeypatch):
    notifier = RecordingNotifier()
    app = build_test_app(monkeypatch, notifier=notifier)

    def boom():
        raise ZeroDivisionError("bad math in a strategy")
    monkeypatch.setattr(app, "step", boom)

    with pytest.raises(ZeroDivisionError):
        app.run_forever()

    state = app.kill_switch.state
    assert state["reason"] == "unhandled_exception"
    assert "ZeroDivisionError" in state["detail"]
    assert any(t == "KILL SWITCH" for t, _, _ in notifier.sent)
    # persisted: a supervisor restart must find it tripped and refuse to trade
    assert json.loads((workdir / "data" / "kill_switch.json")
                      .read_text(encoding="utf-8"))["reason"] == "unhandled_exception"
    assert KillSwitch().is_tripped


def test_restarted_app_refuses_to_trade_after_a_tripped_switch(workdir, monkeypatch):
    app = build_test_app(monkeypatch)
    app.kill_switch.trip(KillReason.UNHANDLED_EXCEPTION, "repr(Exception())")
    restarted = build_test_app(monkeypatch)
    assert restarted.kill_switch.is_tripped
    drive(restarted, TICKS, LEADER)
    assert restarted.portfolio.position_size == 0.0
    assert restarted.portfolio.trades == []


# ---- M8: one source of truth for the core params ---------------------------
def test_config_yaml_params_match_composite_yaml_core():
    cfg = yaml.safe_load((REPO / "config" / "config.yaml").read_text(encoding="utf-8"))
    strat = cfg.get("strategy", {})
    if strat.get("name") not in ("xborder_momentum", "composite"):
        pytest.skip(f"strategy.name is {strat.get('name')!r}; core params not comparable")
    core = load_composite_config(REPO / "config" / "composite.yaml")["core"]
    assert {k: strat["params"][k] for k in core} == core


def test_composite_selected_without_its_config_refuses_to_start(workdir, monkeypatch):
    (workdir / "config" / "composite.yaml").unlink()
    with pytest.raises(FileNotFoundError, match="composite.yaml"):
        build_test_app(monkeypatch)


def test_other_strategies_do_not_need_composite_yaml(workdir, monkeypatch):
    (workdir / "config" / "composite.yaml").unlink()
    app = build_test_app(monkeypatch, strategy_name="xborder_momentum")
    assert isinstance(app.strategy, XborderMomentumStrategy)
