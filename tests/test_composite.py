"""CompositeStrategy: baseline equivalence, fail-closed modules, risk overlay."""
from __future__ import annotations

import json
import logging
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
from bot.risk.pre_trade_checks import AccountState, OrderRequest, PreTradeChecker
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
# A report filename in the shape gate_evidence demands (bare, docs/-relative).
# It resolves under the STUB docs directory installed by stub_evidence_dir
# below, not under the repo's own docs/.
EVIDENCE = "RESEARCH_REPORT_2026-08-20b.md"
ALL_MODULES = ["imbalance_filter", "funding_window", "oi_regime",
               "radar_window", "long_only"]


@pytest.fixture(autouse=True)
def stub_evidence_dir(tmp_path, monkeypatch):
    """HARNESS ONLY: a scratch docs/ holding one report that names every module.

    gate_evidence must resolve to a report whose text MENTIONS the module
    (bot.strategy.composite._check_evidence). No such report exists in the real
    docs/ — no module has been judged — so every test that enables a module
    would otherwise be testing the content check instead of the behaviour it is
    about. Pointing EVIDENCE_DIR at a stub keeps that check honest: the repo's
    shipped config still carries no gate_evidence at all, and the refusal cases
    below are checked against this same stub, so they fail for their own reason
    rather than because the directory is empty.
    """
    import bot.strategy.composite as composite_mod

    docs = tmp_path / "stub_docs"
    docs.mkdir()
    (docs / EVIDENCE).write_text(
        "test harness stub, not a research report. Modules named so the "
        "evidence-content check resolves: " + ", ".join(ALL_MODULES) + "\n",
        encoding="utf-8")
    monkeypatch.setattr(composite_mod, "EVIDENCE_DIR", docs)
    return docs


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
    comp = CompositeStrategy(dict(PARAMS))
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
    comp = CompositeStrategy({})
    assert comp.params == {"k": 30, "thr_pct": 0.8, "exit_pct": 0.05}
    assert comp.min_history == 32


def test_config_params_override_yaml_core():
    comp = CompositeStrategy({"k": 5})
    assert comp.params["k"] == 5 and comp.params["thr_pct"] == 0.8


def test_config_path_cannot_be_injected():
    """M3: there is exactly ONE config path (DEFAULT_CONFIG_PATH). Neither a
    constructor kwarg nor a `config_path` smuggled through strategy.params may
    repoint the composite at another set of gates."""
    with pytest.raises(TypeError):
        CompositeStrategy(dict(PARAMS), config_path=REPO / "config" / "composite.yaml")
    comp = CompositeStrategy({"config_path": "/nowhere/else.yaml"})
    assert comp.params["k"] == 30            # still the repo's core params
    assert comp.active_modules == []


# ---- module framework: fail-closed ----------------------------------------
def test_shipped_yaml_modules_are_all_disabled_and_ungated():
    cfg = load_composite_config()
    modules = build_modules(cfg["modules"])
    assert [m.name for m in modules] == ALL_MODULES
    for m in modules:
        assert m.enabled is False
        assert m.gate                      # pre-registered unlock criterion
        assert m.gate_evidence == ""       # nothing has passed judgment yet
    assert CompositeStrategy({}).active_modules == []


def _raw(name: str, **overrides) -> dict:
    """A single-module config carrying the registered gate text."""
    from bot.strategy.composite import MODULE_CLASSES
    cfg = {"enabled": False, "gate": MODULE_CLASSES[name].GATE}
    cfg.update(overrides)
    return {name: cfg}


def test_enabled_without_gate_evidence_raises():
    with pytest.raises(ModuleGateError, match="gate_evidence"):
        build_modules(_raw("imbalance_filter", enabled=True, gate_evidence=""))


def test_enabled_without_gate_evidence_raises_via_strategy_config(tmp_path, monkeypatch):
    path = tmp_path / "composite.yaml"
    path.write_text(
        "core: {k: 10}\n"
        "modules:\n"
        "  imbalance_filter:\n"
        "    enabled: true\n"
        "    gate: \"board-data judgment >= 1-2 weeks recording, per KNOWLEDGE.md §4\"\n"
        "    gate_evidence: \"\"\n", encoding="utf-8")
    monkeypatch.setattr("bot.strategy.composite.DEFAULT_CONFIG_PATH", path)
    with pytest.raises(ModuleGateError):
        CompositeStrategy({})


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
    assert [m.name for m in modules] == ALL_MODULES


def test_unknown_module_rejected():
    with pytest.raises(ValueError, match="unknown composite module"):
        build_modules({"moon_phase": {"enabled": False}})


@pytest.mark.parametrize("enabled", ["false", "no", "off", "true", 1, 0, 0.0, None, []])
def test_enabled_must_be_a_yaml_bool(enabled):
    """`enabled` is read STRICTLY, not through bool(): every non-empty string is
    truthy, so a quoted "false" — the typo YAML invites — would have switched
    the module ON. Anything that is not a bare bool is refused in either
    direction rather than guessed at."""
    with pytest.raises(ModuleGateError, match="non-boolean 'enabled'") as exc:
        build_modules(_raw("oi_regime", enabled=enabled))
    assert "oi_regime" in str(exc.value)          # names the module
    assert repr(enabled) in str(exc.value)        # and the offending value


@pytest.mark.parametrize("enabled", [True, False])
def test_bare_yaml_bools_still_work(enabled):
    evidence = EVIDENCE if enabled else ""
    module = next(m for m in build_modules(
        _raw("radar_window", enabled=enabled, gate_evidence=evidence))
        if m.name == "radar_window")
    assert module.enabled is enabled


def test_enabled_read_from_yaml_is_a_bool_not_a_string():
    """End to end through the YAML reader: the quoted form is what a config
    edit actually produces, and it must be refused there too."""
    from bot.strategy.composite import MODULE_CLASSES

    raw = yaml.safe_load(
        "oi_regime:\n"
        "  enabled: \"false\"\n"
        f"  gate: {json.dumps(MODULE_CLASSES['oi_regime'].GATE)}\n")
    with pytest.raises(ModuleGateError, match="non-boolean 'enabled'"):
        build_modules(raw)


@pytest.mark.parametrize("entry", [True, False, "true", 3, ["enabled"]])
def test_non_mapping_module_entry_is_refused(entry):
    """`radar_window: true` is a plausible typo for the mapping form. It must
    be refused with a message that says so, not a raw TypeError out of dict()."""
    with pytest.raises(ModuleGateError, match="must be configured as a mapping"):
        build_modules({"radar_window": entry})


@pytest.mark.parametrize("evidence", ["trust me", "RESEARCH_REPORT_x.md",
                                      "KNOWLEDGE.md", "RESEARCH_REPORT_9999-99-99z.md"])
def test_gate_evidence_must_name_an_existing_report(evidence):
    """Invented evidence cannot unlock a module: the reference must resolve to
    a docs/RESEARCH_REPORT_*.md that actually exists and can be audited."""
    with pytest.raises(ModuleGateError, match="gate_evidence"):
        build_modules(_raw("funding_window", enabled=True, gate_evidence=evidence))


@pytest.mark.parametrize("evidence", [
    "docs/" + EVIDENCE,                       # the old path form
    "../docs/" + EVIDENCE,
    "..\\docs\\" + EVIDENCE,
    "/etc/" + EVIDENCE,
    "elsewhere/" + EVIDENCE,                  # same basename, another directory
])
def test_gate_evidence_must_be_a_bare_filename(evidence):
    """N8: taking the basename of a path let anything named like a report —
    anywhere on disk — read as a docs/ report. Only a bare filename is
    accepted, and it is resolved under docs/."""
    with pytest.raises(ModuleGateError, match="bare filename"):
        build_modules(_raw("funding_window", enabled=True, gate_evidence=evidence))


def test_gate_evidence_match_is_case_sensitive():
    """fnmatchcase, not fnmatch: on Windows the latter would accept a name the
    repo does not actually have."""
    with pytest.raises(ModuleGateError, match="gate_evidence"):
        build_modules(_raw("funding_window", enabled=True,
                           gate_evidence=EVIDENCE.replace("RESEARCH", "research")))


def test_evidence_is_checked_even_while_disabled():
    with pytest.raises(ModuleGateError, match="gate_evidence"):
        build_modules(_raw("funding_window", enabled=False, gate_evidence="trust me"))


# ---- M2: the evidence must be about THIS module ----------------------------
def test_evidence_report_must_mention_the_module(stub_evidence_dir):
    """A report that exists and is named correctly but never mentions the
    module cannot unlock it — otherwise any of the dozen reports already in
    docs/ would unlock anything. radar_window HAS a veto rule, so the content
    check is the only thing that can refuse this construction."""
    other = "RESEARCH_REPORT_2026-08-20z.md"
    (stub_evidence_dir / other).write_text(
        "a report about something else entirely\n", encoding="utf-8")
    with pytest.raises(ModuleGateError, match="never mentions"):
        build_modules(_raw("radar_window", enabled=True, gate_evidence=other))


def test_evidence_content_match_is_case_sensitive(stub_evidence_dir):
    other = "RESEARCH_REPORT_2026-08-20y.md"
    (stub_evidence_dir / other).write_text("RADAR_WINDOW passed\n", encoding="utf-8")
    with pytest.raises(ModuleGateError, match="never mentions"):
        build_modules(_raw("radar_window", enabled=True, gate_evidence=other))


def test_unreadable_evidence_report_is_refused(stub_evidence_dir):
    """A report saved in cp932 (the Windows default this repo keeps meeting)
    cannot be decoded as UTF-8. That is a refusal — an unreadable report is not
    evidence — not a raw UnicodeDecodeError escaping into startup."""
    other = "RESEARCH_REPORT_2026-08-20w.md"
    (stub_evidence_dir / other).write_bytes(
        "radar_window は窓内部分集合で判定済み\n".encode("cp932"))
    with pytest.raises(ModuleGateError, match="unreadable report is not evidence"):
        build_modules(_raw("radar_window", enabled=True, gate_evidence=other))


def test_evidence_naming_the_module_is_accepted(stub_evidence_dir):
    """The one ACCEPTED construction: an implemented module, enabled, with
    evidence that names a readable report mentioning it. Owner approval of
    that report is the remaining gate and lives outside the code."""
    module = next(m for m in build_modules(
        _raw("radar_window", enabled=True, gate_evidence=EVIDENCE))
        if m.name == "radar_window")
    assert module.enabled is True and module.gate_evidence == EVIDENCE


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


@pytest.mark.parametrize("sig_type", [SignalType.BUY, SignalType.SELL])
def test_veto_reason_names_the_suppressed_side(sig_type):
    """Several modules are one-sided; a reason that does not say WHICH entry
    was suppressed cannot be read back from the decision log."""
    out = _vetoing_composite().gate_entry(Signal(sig_type, "core"),
                                          ModuleContext(position_size=0.0))
    assert out.reason == f"{sig_type.value} entry vetoed by module oi_regime"


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


# ---- tournament candidates (C2 radar_window / C3 long_only) ----------------
# Both are CANDIDATES, not adoptions: they beat the champion on the tournament's
# judgment split but on n=2 / n=6 trades and with the sign flipped on the 210d
# proxy. They ship disabled; these tests check the wiring, not the hypothesis.
def _ts(hh: int, mm: int) -> float:
    """Unix seconds for a UTC wall-clock time on an arbitrary date."""
    from datetime import datetime, timezone
    return datetime(2026, 8, 20, hh, mm, tzinfo=timezone.utc).timestamp()


INSIDE, OUTSIDE = _ts(13, 0), _ts(3, 0)      # storm window is 12:30-15:00 UTC


def _enabled_module(name: str, **params):
    """The real module, enabled with evidence that exists — the fail-closed
    construction check only passes because the rule is actually implemented."""
    module = next(m for m in build_modules(
        _raw(name, enabled=True, gate_evidence=EVIDENCE, params=params or None))
        if m.name == name)
    assert module.enabled is True
    return module


def _composite_with(name: str, **params) -> CompositeStrategy:
    return CompositeStrategy(dict(PARAMS), modules=[_enabled_module(name, **params)])


@pytest.mark.parametrize("name,subset", [("radar_window", "inside-window"),
                                         ("long_only", "long-only")])
def test_candidate_modules_ship_disabled(name, subset):
    modules = build_modules(load_composite_config()["modules"])
    module = next(m for m in modules if m.name == name)
    assert module.enabled is False and module.gate_evidence == ""
    # B1: the gate is the STANDING bars on a paper subset plus owner approval,
    # not a re-reading of the tournament that generated the candidate.
    assert "Owner approval" in module.gate
    assert f"{subset} subset of champion paper trades" in module.gate
    assert "+0.15%/trade" in module.gate and "maxDD < 10%" in module.gate
    assert "the KNOWLEDGE.md §5 bars" in module.gate
    assert "candidate-generation only" in module.gate


@pytest.mark.parametrize("name", ["radar_window", "long_only"])
def test_candidate_gate_states_the_subset_n_as_a_deviation(name):
    """B1: subset n >= 15 is NOT §5's number — §5's bar is 30 trades on the
    full set. The gate must carry the reduced n as an explicit deviation the
    owner approves along with the report, never dressed up as §5 saying 15."""
    module = next(m for m in build_modules(load_composite_config()["modules"])
                  if m.name == name)
    assert "subset n >= 15" in module.gate
    assert "§5's full-set bar is 30 trades" in module.gate
    assert "deliberate deviation that the owner approves" in module.gate
    # the §5 attribution covers the two BARS only, not the sample size
    assert "n >= 15 (KNOWLEDGE" not in module.gate


@pytest.mark.parametrize("name", ["radar_window", "long_only"])
def test_candidate_modules_construct_when_enabled_with_valid_evidence(name):
    """Unlike the pending §4 modules, these two have real veto rules, so the
    B1 construction check passes instead of refusing them."""
    assert _enabled_module(name).gate_evidence == EVIDENCE


def test_radar_window_vetoes_an_entry_outside_the_window():
    out = _composite_with("radar_window").gate_entry(
        Signal(SignalType.BUY, "core", {"x": 1.0}),
        ModuleContext(position_size=0.0, signal_ts=OUTSIDE))
    assert out.type is SignalType.HOLD and "radar_window" in out.reason
    assert out.indicators == {"x": 1.0}


@pytest.mark.parametrize("sig_type", [SignalType.BUY, SignalType.SELL])
def test_radar_window_passes_an_entry_inside_the_window(sig_type):
    sig = Signal(sig_type, "core")
    comp = _composite_with("radar_window")
    assert comp.gate_entry(sig, ModuleContext(position_size=0.0, signal_ts=INSIDE)) is sig


def test_radar_window_reuses_the_radar_window_bounds():
    module = _enabled_module("radar_window")
    assert module.radar.window == "12:30-15:00 UTC"
    assert module.radar.is_armed(INSIDE) and not module.radar.is_armed(OUTSIDE)


def test_radar_window_bounds_come_from_params():
    comp = _composite_with("radar_window", window_start_utc="02:00", window_end_utc="04:00")
    sig = Signal(SignalType.BUY, "core")
    assert comp.gate_entry(sig, ModuleContext(position_size=0.0, signal_ts=OUTSIDE)) is sig
    assert comp.gate_entry(sig, ModuleContext(position_size=0.0, signal_ts=INSIDE)
                           ).type is SignalType.HOLD


@pytest.mark.parametrize("start,end", [
    ("12:30", "12:30"),      # identical strings
    ("0:00", "00:00"),       # M1: same MINUTE, different spelling
    ("1:05", "01:05"),
])
def test_radar_window_rejects_an_empty_window(start, end):
    """A start == end window is never armed, so the module would veto EVERY
    entry — a silent trading halt wearing the clothes of a configured window.
    Refuse it where it is written, on the PARSED minutes: "0:00" and "00:00"
    are the same minute to StormRadar, and a string comparison let that
    spelling through into a permanent veto."""
    with pytest.raises(ValueError, match="empty window"):
        _enabled_module("radar_window", window_start_utc=start,
                        window_end_utc=end)


def test_radar_window_accepts_an_unpadded_real_window():
    """The parsed-minutes guard must not refuse a legitimate window written
    without a leading zero."""
    module = _enabled_module("radar_window", window_start_utc="1:05",
                             window_end_utc="02:05")
    assert module.radar.is_armed(_ts(1, 30))
    assert not module.radar.is_armed(_ts(3, 0))


def test_radar_window_vetoes_when_no_signal_time_is_supplied():
    """Fail closed: an entry that cannot be shown to be inside the window is
    refused rather than being timed by the process clock."""
    out = _composite_with("radar_window").gate_entry(
        Signal(SignalType.BUY, "core"), ModuleContext(position_size=0.0))
    assert out.type is SignalType.HOLD


def test_long_only_vetoes_a_short_entry():
    out = _composite_with("long_only").gate_entry(
        Signal(SignalType.SELL, "core", {"x": 1.0}), ModuleContext(position_size=0.0))
    assert out.type is SignalType.HOLD and "long_only" in out.reason
    assert out.indicators == {"x": 1.0}


@pytest.mark.parametrize("pos", [0.0, -0.5])      # opening and extending a short
def test_long_only_vetoes_any_short_exposure(pos):
    assert _composite_with("long_only").gate_entry(
        Signal(SignalType.SELL, "core"), ModuleContext(position_size=pos)
    ).type is SignalType.HOLD


@pytest.mark.parametrize("pos", [0.0, 0.5])       # opening and extending a long
def test_long_only_passes_long_entries(pos):
    sig = Signal(SignalType.BUY, "core")
    assert _composite_with("long_only").gate_entry(
        sig, ModuleContext(position_size=pos)) is sig


@pytest.mark.parametrize("sig_type,pos", [
    (SignalType.CLOSE, 0.5), (SignalType.CLOSE, -0.5),
    (SignalType.BUY, -0.5),        # BUY closing a short
    (SignalType.SELL, 0.5),        # SELL closing a long — the one to watch
    (SignalType.HOLD, 0.0),
])
def test_long_only_never_blocks_a_close(sig_type, pos):
    """The framework's closing guard covers this, but a long-only rule that
    ever blocked a SELL out of a long would strand a position."""
    sig = Signal(sig_type, "core")
    assert _composite_with("long_only").gate_entry(
        sig, ModuleContext(position_size=pos)) is sig


@pytest.mark.parametrize("signal_ts", [None, INSIDE, OUTSIDE])
def test_disabled_candidates_leave_every_signal_untouched(signal_ts):
    """E0: the shipped (all-disabled) module set is the identity function for
    every signal type, every position and any signal_ts."""
    comp = CompositeStrategy({})
    assert comp.active_modules == []
    for sig_type in SignalType:
        for pos in (-0.5, 0.0, 0.5):
            sig = Signal(sig_type, "core", {"x": 1.0})
            assert comp.gate_entry(sig, ModuleContext(
                position_size=pos, signal_ts=signal_ts)) is sig


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
    """The overlay's own loss counter resets on any winning close."""
    state = OverlayState(equity_peak_jpy=200000.0, equity_jpy=200000.0)
    for _ in range(3):
        state.on_closed_trade(-100.0, 200000.0)
    assert state.consecutive_losses == 3
    assert CompositeStrategy.size_factor(200000.0, 200000.0, state.consecutive_losses) == 0.5
    state.on_closed_trade(+100.0, 200000.0)
    assert state.consecutive_losses == 0
    assert CompositeStrategy.size_factor(200000.0, 200000.0, state.consecutive_losses) == 1.0


def test_dd_frac_of_a_wiped_out_book_is_the_deepest_drawdown():
    """A book at (or below) zero is the DEEPEST drawdown, not the absence of
    one. Reporting 1.0 there let a wiped-out account restart at full size."""
    from bot.strategy.composite import DD_FLOOR, DRAWDOWN_TRIGGER

    state = OverlayState(equity_peak_jpy=200000.0, equity_jpy=0.0)
    assert state.dd_frac == DD_FLOOR
    assert 0.0 < DD_FLOOR < DRAWDOWN_TRIGGER          # engages the brake
    assert OverlayState(equity_peak_jpy=200000.0, equity_jpy=-5.0).dd_frac == DD_FLOOR
    # no peak recorded yet is a different case: nothing measured, no drawdown
    assert OverlayState().dd_frac == 1.0


def test_wiped_out_state_reloads_as_a_drawdown(tmp_path):
    """DD_FLOOR must survive the round trip: a value load() rejected would
    degrade to 'no drawdown' — the exact reading it exists to prevent."""
    path = tmp_path / "overlay_state.json"
    OverlayState(equity_peak_jpy=200000.0, equity_jpy=0.0).save(path)
    reloaded = OverlayState.load(path, boot_equity_jpy=100000.0)
    assert reloaded.equity_peak_jpy > reloaded.equity_jpy
    assert CompositeStrategy.size_factor(reloaded.equity_peak_jpy,
                                         reloaded.equity_jpy, 0) == 0.5


def test_observe_equity_raises_the_peak_without_touching_the_streak():
    """The peak is a fact about the equity CURVE, not the trade log: equity
    seen between closes counts. The loss streak is a closed-trade fact and must
    not move here."""
    state = OverlayState(consecutive_losses=2, equity_peak_jpy=200000.0,
                         equity_jpy=200000.0)
    state.observe_equity(220000.0)
    assert state.equity_peak_jpy == pytest.approx(220000.0)
    state.observe_equity(205000.0)                  # a give-back is a drawdown
    assert state.equity_peak_jpy == pytest.approx(220000.0)
    assert state.equity_jpy == pytest.approx(205000.0)
    assert state.consecutive_losses == 2


def test_overlay_counter_is_not_the_portfolios():
    """N1: the portfolio's counter feeds the HARD risk checks (kill switch);
    the overlay must never write into it, in either direction."""
    p = Portfolio(initial_equity_jpy=200000.0, clock=lambda: 0.0)
    state = OverlayState(consecutive_losses=9, equity_peak_jpy=400000.0,
                         equity_jpy=200000.0)
    state.on_closed_trade(-50.0, 199950.0)
    assert p.consecutive_losses == 0
    assert p.equity_peak_jpy == pytest.approx(200000.0)
    assert state.consecutive_losses == 10


# ---- app wiring ------------------------------------------------------------
def app_config(strategy_name: str = "composite", paper_equity_jpy: float = 200000) -> dict:
    return {
        "product_code": "FX_BTC_JPY",
        "candle_interval_sec": 60,
        "paper_equity_jpy": paper_equity_jpy,
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


def build_test_app(monkeypatch=None, *, strategy_name="composite", notifier=None,
                   paper_equity_jpy=200000):
    """Paper TradingApp on FX_BTC_JPY. The caller must already be chdir'd into
    a writable working directory holding a config/ copy.

    Also used by scripts/validate_composite.py (gate G1b), hence the optional
    monkeypatch: outside pytest the leader feed is silenced directly."""
    settings = Settings(mode=Mode.PAPER, product_code="FX_BTC_JPY",
                        config=app_config(strategy_name, paper_equity_jpy),
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


def test_quantize_truncates_like_the_pre_composite_champion(app):
    """M2: sizing is the champion's own expression, int(budget/price/min_size).
    An epsilon there rounds a budget one step UP at the boundary — an
    undocumented change to the sizing of the strategy under paper validation,
    which the composite (a carrier) must not make."""
    assert app.product.min_size == 0.001
    # 11.9999999999 steps: truncation buys 11, an epsilon-nudged floor could not
    assert app._quantize(119999.999999, 1e7) == pytest.approx(0.011)
    assert app._quantize(130000.0, 1e7) == pytest.approx(0.013)
    assert app._quantize(9999.0, 1e7) == 0.0        # below one step


def test_overlay_scales_the_size_directly_not_through_the_price(app):
    """The scaled size is a function of (size, factor) only.

    The old form, `_quantize(size * factor * price, price)`, multiplied by the
    price and divided it straight back out — not the identity in binary
    floating point. At this price the round trip lands one ulp off the step
    boundary and loses a whole min_size step; at others it GAINS one, sending
    more than the approved size times the factor. `_scale_size` is the direct
    form, which is also what validate_composite.py G1b asserts.
    """
    size, factor, price = 0.012, 0.5, 6525609.457968516
    assert app._scale_size(size, factor) == pytest.approx(0.006)
    assert app._quantize(size * factor * price, price) == pytest.approx(0.005)
    # and the sizes the bot actually meets are unchanged by the switch
    assert app._scale_size(0.013, 0.5) == pytest.approx(0.006)
    assert app._scale_size(0.013, 0.25) == pytest.approx(0.003)
    assert app._scale_size(0.001, 0.5) == 0.0        # below one step -> suppressed


def test_app_halves_new_entry_after_loss_streak(app):
    app.overlay_state.consecutive_losses = 3
    drive(app, TICKS, LEADER)
    assert app.portfolio.position_size == pytest.approx(-0.006)  # 130k x 0.5


def test_app_quarters_new_entry_in_drawdown_and_streak(app):
    app.overlay_state.consecutive_losses = 3
    # 7% below the OVERLAY's peak. The portfolio's own peak is untouched, so
    # the hard drawdown check still sees 0% and the kill switch stays out of
    # it — this exercises the overlay alone.
    app.overlay_state.equity_peak_jpy = 215000.0
    drive(app, TICKS, LEADER)
    assert app.portfolio.position_size == pytest.approx(-0.003)  # 130k x 0.25
    assert not app.kill_switch.is_tripped
    assert app.portfolio.consecutive_losses == 0


def test_scaled_entry_logs_all_three_sizes(app, caplog):
    """M4(4): the log line has to be checkable by hand — approved full size,
    the factor, and what was actually sent."""
    app.overlay_state.consecutive_losses = 3
    with caplog.at_level(logging.INFO, logger="bot.main"):
        drive(app, TICKS, LEADER)
    rec = next(r for r in caplog.records
               if getattr(r, "data", {}).get("event") == "overlay_scaled_entry")
    assert rec.data["full_size"] == pytest.approx(0.013)
    assert rec.data["size_factor"] == pytest.approx(0.5)
    assert rec.data["scaled_size"] == pytest.approx(0.006)


def test_overlay_never_shrinks_a_closing_order(app):
    drive(app, TICKS, LEADER)
    assert app.portfolio.position_size == pytest.approx(-0.013)
    # drawdown + loss streak while a position is open: the exit must still
    # close the FULL position, never a scaled fraction of it.
    app.overlay_state.consecutive_losses = 4
    app.overlay_state.equity_peak_jpy = 215000.0
    drive(app, [(390, 1e7), (430, 1e7), (490, 1e7)], LEADER)
    assert app.portfolio.position_size == 0.0


# ---- M4: module effects are visible on the LIVE path, never in a backtest --
def _utc_window(start_offset_min: int, end_offset_min: int) -> dict:
    """A radar window placed relative to the wall clock the live path reads
    (bot/main.py passes time.time() as signal_ts)."""
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    return {"window_start_utc": (now + timedelta(minutes=start_offset_min)).strftime("%H:%M"),
            "window_end_utc": (now + timedelta(minutes=end_offset_min)).strftime("%H:%M")}


def _run_with_module(app, name: str, **params):
    """HARNESS ONLY: put a real, ENABLED module on the running app's strategy.

    The backtest engine never calls gate_entry, so a module's effect can only
    be seen on the live order path. Nothing in the repo ships enabled; this
    swaps in the same class the config would build, with the same core params.
    """
    app.strategy = CompositeStrategy(dict(app.settings.config["strategy"]["params"]),
                                     modules=[_enabled_module(name, **params)])
    return app


def test_live_path_module_suppresses_out_of_window_entries(app):
    _run_with_module(app, "radar_window", **_utc_window(60, 120))
    drive(app, TICKS, LEADER)
    assert app.portfolio.position_size == 0.0
    assert app.portfolio.trades == []


def test_live_path_module_passes_in_window_entries_and_never_blocks_a_close(app):
    _run_with_module(app, "radar_window", **_utc_window(-30, 30))
    drive(app, TICKS, LEADER)
    assert app.portfolio.position_size == pytest.approx(-0.013)   # full size
    # the window moves away while the position is open: the EXIT must still go
    _run_with_module(app, "radar_window", **_utc_window(60, 120))
    drive(app, [(390, 1e7), (430, 1e7), (490, 1e7)], LEADER)
    assert app.portfolio.position_size == 0.0


# ---- M13: overlay + active modules are visible in status.json --------------
def test_status_json_carries_overlay_and_active_modules(app, workdir):
    app.overlay_state.consecutive_losses = 3
    app.overlay_state.equity_peak_jpy = 215000.0
    drive(app, TICKS, LEADER)
    saved = json.loads((workdir / "logs" / "status.json").read_text(encoding="utf-8"))
    assert saved["overlay"]["consecutive_losses"] == 3
    assert saved["overlay"]["factor"] == pytest.approx(0.25)
    assert saved["overlay"]["dd_pct"] > 0.0
    assert saved["active_modules"] == []     # framework present, none enabled


def test_status_json_lists_enabled_modules(app, workdir):
    _run_with_module(app, "radar_window", **_utc_window(-30, 30))
    drive(app, TICKS, LEADER)
    saved = json.loads((workdir / "logs" / "status.json").read_text(encoding="utf-8"))
    assert saved["active_modules"] == ["radar_window"]


def test_status_json_omits_overlay_for_a_strategy_without_one(workdir, monkeypatch):
    """None, not 0/[]: 'this strategy has no overlay and no module framework'
    is a different fact from 'the overlay is at full size'."""
    app = build_test_app(monkeypatch, strategy_name="xborder_momentum")
    drive(app, TICKS, LEADER)
    saved = json.loads((workdir / "logs" / "status.json").read_text(encoding="utf-8"))
    assert saved["overlay"] is None
    assert saved["active_modules"] is None


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
    app.overlay_state.consecutive_losses = 3     # overlay factor 0.5
    drive(app, TICKS, LEADER)
    assert app.portfolio.position_size == 0.0
    assert app.portfolio.trades == []
    assert not app.kill_switch.is_tripped    # -5500 > -6000: reject, not kill


@pytest.mark.parametrize("label,full_size,daily_pnl,position_notional,position_size", [
    ("flat book", 0.013, 0.0, 0.0, 0.0),
    ("most of the daily risk budget spent", 0.013, -5300.0, 0.0, 0.0),
    ("a position already open", 0.010, 0.0, 30000.0, -0.003),
    ("unrealized loss on the day", 0.013, -1200.0, 0.0, 0.0),
])
def test_a_smaller_size_never_turns_an_approval_into_a_rejection(
        workdir, label, full_size, daily_pnl, position_notional, position_size):
    """The invariant that makes "check at full size, then scale" sound.

    bot/main.py runs the pre-trade checks on the FULL size and lets the overlay
    shrink an order those checks already approved — it never re-checks the
    smaller one. That is only safe because every size-bearing check is monotone
    in size: the order-notional cap, the position cap, the margin and balance
    checks and the remaining daily risk budget all get LOOSER as the size
    falls, so a smaller order cannot be refused where the full one passed.
    Sizes below the product minimum are out of scope by construction — there
    the overlay suppresses the entry instead of submitting it (bot/main.py
    `_warn_overlay_suppressed`).

    The inputs are the ones the composite tests above already exercise
    (daily-loss budget, open position, flat book).
    """
    from bot.products import load_products

    product = load_products(str(REPO))["FX_BTC_JPY"]
    checker = PreTradeChecker(RiskLimits.from_dict(dict(APP_LIMITS)),
                              KillSwitch(), product=product)
    price = 1e7
    account = AccountState(
        balance_jpy=200000.0, position_notional_jpy=position_notional,
        open_orders=0, daily_pnl_jpy=daily_pnl, drawdown_pct=0.0,
        consecutive_losses=0, position_size=position_size)

    def approved(size: float) -> bool:
        request = OrderRequest("FX_BTC_JPY", "SELL", size, price,
                               stop_price=price * 1.005)
        return checker.check(request, account).approved

    assert approved(full_size), f"{label}: full size must be approved first"
    steps = int(round(full_size / product.min_size))
    for step in range(1, steps + 1):
        size = round(step * product.min_size, 8)
        assert approved(size), f"{label}: {size} refused while {full_size} passed"


def test_same_scenario_without_the_daily_brake_does_enter_scaled(app):
    """Control for the test above: the only thing stopping the scaled entry is
    the full-size rejection, not the overlay itself."""
    app.overlay_state.consecutive_losses = 3
    drive(app, TICKS, LEADER)
    assert app.portfolio.position_size == pytest.approx(-0.006)


# ---- M14: overlay suppression is announced once per UTC day ----------------
def test_overlay_suppression_notifies_once_per_day(workdir, monkeypatch):
    notifier = RecordingNotifier()
    app = build_test_app(monkeypatch, notifier=notifier)
    # min_size 0.001 at ~1e7 JPY = 10,000 JPY; a 0.25 factor on a budget that
    # only ever buys one step rounds the entry away entirely.
    monkeypatch.setattr(app.settings.risk_limits, "max_order_size_jpy", 12000.0)
    app.overlay_state.consecutive_losses = 3
    app.overlay_state.equity_peak_jpy = 215000.0
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


# ---- M5 / N2: the overlay brake survives a restart, as a RELATIVE drawdown --
def _write_state(workdir: Path, **fields) -> None:
    (workdir / "data").mkdir(exist_ok=True)
    (workdir / "data" / "overlay_state.json").write_text(
        json.dumps(fields), encoding="utf-8")


def test_overlay_state_persists_across_restart(workdir, monkeypatch):
    app = build_test_app(monkeypatch)
    app.overlay_state.consecutive_losses = 4
    app.overlay_state.equity_peak_jpy = 215000.0
    app._persist_overlay_state(1e7, -1.0)        # a losing close -> 5 in a row
    assert (workdir / "data" / "overlay_state.json").exists()

    restarted = build_test_app(monkeypatch)      # simulated process restart
    assert restarted.overlay_state.consecutive_losses == 5
    # the RELATIVE drawdown carried over (200000 / 215000 of the peak)
    assert restarted.overlay_state.equity_peak_jpy == pytest.approx(215000.0)
    # the portfolio — which feeds the hard risk checks — is untouched by it
    assert restarted.portfolio.consecutive_losses == 0
    assert restarted.portfolio.equity_peak_jpy == pytest.approx(200000.0)
    # and the brake is actually in force after the restart
    drive(restarted, TICKS, LEADER)
    assert restarted.portfolio.position_size == pytest.approx(-0.003)


def test_restart_after_operator_reset_trades_scaled_instead_of_deadlocking(
        workdir, monkeypatch):
    """N1: the persisted brake must not re-trip the kill switch on boot.

    5 losses (= MAX_CONSECUTIVE_LOSSES) trip the switch. The operator
    investigates and resets. If the restarted process seeded the PORTFOLIO's
    counter from disk, the very first pre-trade check would trip the switch
    again on history it did not live through — a deadlock no reset can clear.
    The overlay may still shrink the entry; the kill switch may not fire.
    """
    _write_state(workdir, consecutive_losses=5, dd_frac=1.0)
    KillSwitch().trip(KillReason.CONSECUTIVE_LOSSES, "5 consecutive losses")
    KillSwitch().reset(operator_confirm=True)    # human, after investigating

    app = build_test_app(monkeypatch)
    assert app.overlay_state.consecutive_losses == 5   # brake inherited
    assert app.portfolio.consecutive_losses == 0       # risk checks start clean
    drive(app, TICKS, LEADER)
    assert not app.kill_switch.is_tripped
    assert app.portfolio.position_size == pytest.approx(-0.006)   # 130k x 0.5


def test_restart_with_lower_paper_equity_does_not_scale_by_itself(workdir, monkeypatch):
    """N2: an absolute JPY peak restored against a smaller boot equity would
    manufacture a drawdown that never happened. dd_frac cannot."""
    # saved at no drawdown on a 200,000 JPY book; restarted on a 100,000 one
    _write_state(workdir, consecutive_losses=0, dd_frac=1.0)
    restarted = build_test_app(monkeypatch, paper_equity_jpy=100000)
    # peak follows the boot equity; an absolute 200,000 peak would have read
    # as a 50% drawdown and halved every entry for nothing
    assert restarted.overlay_state.equity_peak_jpy == pytest.approx(100000.0)
    assert restarted._entry_size_factor(1e7) == 1.0
    drive(restarted, TICKS, LEADER)
    assert restarted.portfolio.position_size == pytest.approx(-0.013)   # full size


def test_relative_drawdown_survives_a_restart(workdir, monkeypatch):
    """A 10% drawdown at save time is still a 10% drawdown after a restart,
    so the factor-0.5 brake is still in force."""
    _write_state(workdir, consecutive_losses=0, dd_frac=0.9)
    app = build_test_app(monkeypatch)
    assert app.overlay_state.equity_peak_jpy == pytest.approx(200000.0 / 0.9)
    assert app._entry_size_factor(1e7) == 0.5
    drive(app, TICKS, LEADER)
    assert app.portfolio.position_size == pytest.approx(-0.006)   # 130k x 0.5


def test_closing_trade_checkpoints_overlay_state(app, workdir):
    drive(app, TICKS, LEADER)
    assert not (workdir / "data" / "overlay_state.json").exists()   # entry only
    drive(app, [(390, 1e7), (430, 1e7), (490, 1e7)], LEADER)
    assert app.portfolio.position_size == 0.0
    saved = json.loads((workdir / "data" / "overlay_state.json").read_text(encoding="utf-8"))
    assert saved["consecutive_losses"] == app.overlay_state.consecutive_losses
    assert saved["dd_frac"] == pytest.approx(app.overlay_state.dd_frac)
    assert 0.0 < saved["dd_frac"] <= 1.0
    assert "equity_peak_jpy" not in saved        # absolute peaks are not stored


def test_flat_close_still_checkpoints_the_overlay(app, workdir, monkeypatch):
    """A close that breaks exactly even (realized + fee == 0) still moved the
    equity path, so the brake must be checkpointed. Keying the write on the
    P&L skipped exactly that case."""
    drive(app, TICKS, LEADER)                       # opens a position
    assert not (workdir / "data" / "overlay_state.json").exists()
    real_on_fill = app.portfolio.on_fill
    monkeypatch.setattr(app.portfolio, "on_fill",
                        lambda **kw: (real_on_fill(**kw), 0.0)[1])
    drive(app, [(390, 1e7), (430, 1e7), (490, 1e7)], LEADER)
    assert app.portfolio.position_size == 0.0
    assert (workdir / "data" / "overlay_state.json").exists()


def test_equity_high_between_closes_engages_the_brake_earlier(app, monkeypatch):
    """The overlay peak follows equity the app OBSERVES, not only equity at a
    close. A run-up handed back inside one open position is a real drawdown; a
    peak that moved only on closes would engage the brake a trade late."""
    monkeypatch.setattr(app.portfolio, "equity_jpy", lambda price: 220000.0)
    app._update_status(1e7)
    assert app.overlay_state.equity_peak_jpy == pytest.approx(220000.0)
    # 205,000 is 6.8% below that high -> the drawdown brake is in force, where
    # a close-only peak would still read 205,000 as its own peak (factor 1.0)
    monkeypatch.setattr(app.portfolio, "equity_jpy", lambda price: 205000.0)
    app._update_status(1e7)
    assert app._entry_size_factor(1e7) == 0.5
    assert app.status.status.overlay["dd_pct"] > 0.0
    assert app.overlay_state.consecutive_losses == 0     # not a closed trade


@pytest.mark.parametrize("content", [
    "", "{not json", '{"consecutive_losses": 3}',
    '{"consecutive_losses": "x", "dd_frac": 1}',
    '{"consecutive_losses": 3, "dd_frac": 0}',      # out of range
    '{"consecutive_losses": 3, "dd_frac": 1.5}',    # equity above its own peak
    '{"consecutive_losses": 3, "dd_frac": -0.5}',
    '{"consecutive_losses": 3, "equity_peak_jpy": 400000}',   # old format
])
def test_corrupt_overlay_state_degrades_to_safe_defaults(workdir, monkeypatch, content):
    (workdir / "data").mkdir(exist_ok=True)
    (workdir / "data" / "overlay_state.json").write_text(content, encoding="utf-8")
    app = build_test_app(monkeypatch)            # must not raise
    assert app.overlay_state.consecutive_losses == 0
    assert app.overlay_state.equity_peak_jpy == pytest.approx(200000.0)
    assert app._entry_size_factor(1e7) == 1.0


def test_missing_overlay_state_degrades_to_safe_defaults(workdir, monkeypatch):
    assert not (workdir / "data" / "overlay_state.json").exists()
    app = build_test_app(monkeypatch)
    assert app.overlay_state.consecutive_losses == 0
    assert app.overlay_state.equity_peak_jpy == pytest.approx(200000.0)
    assert app.portfolio.consecutive_losses == 0
    assert app.portfolio.equity_peak_jpy == pytest.approx(200000.0)


def test_overlay_state_roundtrip_is_utf8_json(tmp_path):
    path = tmp_path / "nested" / "overlay_state.json"
    OverlayState(consecutive_losses=2, equity_peak_jpy=200.0, equity_jpy=150.0).save(path)
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved == {"consecutive_losses": 2, "dd_frac": pytest.approx(0.75)}
    # reloaded against a different boot equity: the RATIO is what survives
    reloaded = OverlayState.load(path, boot_equity_jpy=300.0)
    assert reloaded.consecutive_losses == 2
    assert reloaded.equity_peak_jpy == pytest.approx(400.0)
    assert reloaded.dd_frac == pytest.approx(0.75)


def test_overlay_state_save_survives_a_locked_destination(tmp_path, monkeypatch):
    """N7: os.replace fails with PermissionError on Windows while a reader
    holds the file. Retry, then write directly — and never leak the temp
    file. The write itself is bot/atomic_file.py, shared with StatusWriter
    and the paper book."""
    import bot.atomic_file as atomic

    path = tmp_path / "overlay_state.json"
    monkeypatch.setattr(atomic.time, "sleep", lambda s: None)

    calls = []

    def always_locked(src, dst):
        calls.append((src, dst))
        raise PermissionError("dashboard holds the file open")

    monkeypatch.setattr(atomic.os, "replace", always_locked)
    OverlayState(consecutive_losses=3, equity_peak_jpy=100.0, equity_jpy=50.0).save(path)

    assert len(calls) == 5                       # retried before falling back
    assert json.loads(path.read_text(encoding="utf-8"))["consecutive_losses"] == 3
    assert not path.with_suffix(".tmp").exists()  # no temp file left behind


def test_overlay_state_save_never_raises(tmp_path):
    """A brake checkpoint must not be able to take trading down."""
    blocked = tmp_path / "blocked"
    blocked.write_text("a file where a directory would have to be", encoding="utf-8")
    OverlayState(consecutive_losses=1).save(blocked / "overlay_state.json")


# ---- B1(b): an unhandled exception must trip the persisted kill switch -----
def _interrupt_on_sleep(monkeypatch, after: int = 3) -> list[float]:
    """The loop carries on in data-only mode after a fault (L-532), so a test
    ends it with Ctrl-C on the `after`-th sleep."""
    import bot.main as bot_main
    sleeps: list[float] = []

    def fake_sleep(sec):
        sleeps.append(sec)
        if len(sleeps) >= after:
            raise KeyboardInterrupt()
    monkeypatch.setattr(bot_main.time, "sleep", fake_sleep)
    return sleeps


def test_unhandled_step_exception_trips_kill_switch(workdir, monkeypatch):
    notifier = RecordingNotifier()
    app = build_test_app(monkeypatch, notifier=notifier)

    def boom():
        raise ZeroDivisionError("bad math in a strategy")
    monkeypatch.setattr(app, "step", boom)
    _interrupt_on_sleep(monkeypatch)

    with pytest.raises(KeyboardInterrupt):
        app.run_forever()

    state = app.kill_switch.state
    assert state["reason"] == "unhandled_exception"
    assert "ZeroDivisionError" in state["detail"]
    assert any(t == "KILL SWITCH" for t, _, _ in notifier.sent)
    # persisted: a supervisor restart must find it tripped and refuse to trade
    assert json.loads((workdir / "data" / "kill_switch.json")
                      .read_text(encoding="utf-8"))["reason"] == "unhandled_exception"
    assert KillSwitch().is_tripped


# ---- N3: a failure while shutting down must not destroy the kill reason ----
class ExplodingNotifier(Notifier):
    """A webhook that dies exactly when it is needed most."""

    def __init__(self):
        self.attempts: list[str] = []

    def send(self, title, message, *, urgent=False):
        self.attempts.append(title)
        if title == "KILL SWITCH":
            raise ConnectionError("discord webhook is gone")
        return True


def test_kill_reason_survives_a_failing_notifier(workdir, monkeypatch):
    """The FIRST reason is the diagnosis. A notifier that raises while the
    switch is being tripped must not overwrite it with 'unhandled exception'."""
    notifier = ExplodingNotifier()
    app = build_test_app(monkeypatch, notifier=notifier)

    def trip_then_raise():
        # Trip ONCE: re-tripping every cycle would restore the reason and hide
        # an overwrite by `_trip_once`.
        if not app.kill_switch.is_tripped:
            app.kill_switch.trip(KillReason.MARKET_DATA_ANOMALY, "ticker stale for 900s")
            raise RuntimeError("a second fault while shutting down")
    monkeypatch.setattr(app, "step", trip_then_raise)
    _interrupt_on_sleep(monkeypatch)

    with pytest.raises(KeyboardInterrupt):
        app.run_forever()

    state = app.kill_switch.state
    assert state["reason"] == "market_data_anomaly"
    assert state["detail"] == "ticker stale for 900s"
    assert json.loads((workdir / "data" / "kill_switch.json")
                      .read_text(encoding="utf-8"))["reason"] == "market_data_anomaly"
    assert "KILL SWITCH" in notifier.attempts        # it did try


def test_failing_notifier_does_not_prevent_cancel_all(workdir, monkeypatch):
    notifier = ExplodingNotifier()
    app = build_test_app(monkeypatch, notifier=notifier)
    cancelled: list[str] = []
    monkeypatch.setattr(app.orders, "cancel_all_active",
                        lambda symbol: cancelled.append(symbol))

    app._on_kill("market data anomaly")          # must not raise

    assert cancelled == ["FX_BTC_JPY"]
    assert "KILL SWITCH" in notifier.attempts
    assert (workdir / "logs" / "status.json").exists()   # status still flushed


def test_exception_outside_step_trips_the_switch(workdir, monkeypatch):
    """N3: the whole loop body is guarded — a freshness check that blows up is
    just as much an unknown state as a failing step()."""
    app = build_test_app(monkeypatch, notifier=RecordingNotifier())
    monkeypatch.setattr(app, "step", lambda: None)
    monkeypatch.setattr(app.feed, "check_freshness",
                        lambda: (_ for _ in ()).throw(ValueError("clock went backwards")))
    _interrupt_on_sleep(monkeypatch)

    with pytest.raises(KeyboardInterrupt):
        app.run_forever()

    assert app.kill_switch.state["reason"] == "unhandled_exception"
    assert "clock went backwards" in app.kill_switch.state["detail"]


def test_keyboard_interrupt_leaves_the_switch_untripped(workdir, monkeypatch):
    """An operator stopping the bot is not a fault; the next start must not
    find a tripped switch it has to reset."""
    app = build_test_app(monkeypatch, notifier=RecordingNotifier())
    monkeypatch.setattr(app, "step",
                        lambda: (_ for _ in ()).throw(KeyboardInterrupt()))

    with pytest.raises(KeyboardInterrupt):
        app.run_forever()

    assert not app.kill_switch.is_tripped


def test_kill_switch_detail_is_redacted(workdir, monkeypatch):
    """N6: the exception repr goes to a file on disk and to Discord; a secret
    caught up in it must be masked first, exactly as in the logs."""
    from bot.logging_setup import _SECRET_PATTERNS, register_secret

    before = list(_SECRET_PATTERNS)
    register_secret("super-secret-api-key")
    try:
        app = build_test_app(monkeypatch, notifier=RecordingNotifier())
        monkeypatch.setattr(app, "step", lambda: (_ for _ in ()).throw(
            ValueError("auth failed for super-secret-api-key")))
        _interrupt_on_sleep(monkeypatch)
        with pytest.raises(KeyboardInterrupt):
            app.run_forever()
    finally:
        _SECRET_PATTERNS[:] = before

    detail = app.kill_switch.state["detail"]
    assert "super-secret-api-key" not in detail
    assert "REDACTED" in detail
    persisted = (workdir / "data" / "kill_switch.json").read_text(encoding="utf-8")
    assert "super-secret-api-key" not in persisted


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
    core = load_composite_config()["core"]
    assert {k: strat["params"][k] for k in core} == core


def test_composite_selected_without_its_config_refuses_to_start(workdir, monkeypatch, tmp_path):
    """The startup guard tests the same absolute path the strategy reads."""
    monkeypatch.setattr("bot.main.COMPOSITE_CONFIG_PATH", tmp_path / "gone.yaml")
    with pytest.raises(FileNotFoundError, match="gone.yaml"):
        build_test_app(monkeypatch)


def test_other_strategies_do_not_need_composite_yaml(workdir, monkeypatch, tmp_path):
    monkeypatch.setattr("bot.main.COMPOSITE_CONFIG_PATH", tmp_path / "gone.yaml")
    app = build_test_app(monkeypatch, strategy_name="xborder_momentum")
    assert isinstance(app.strategy, XborderMomentumStrategy)


# ---- N4: params must not depend on the process working directory -----------
def test_default_config_path_is_absolute_and_repo_anchored():
    from bot.strategy.composite import DEFAULT_CONFIG_PATH
    assert DEFAULT_CONFIG_PATH.is_absolute()
    assert DEFAULT_CONFIG_PATH == REPO / "config" / "composite.yaml"


def test_core_params_do_not_depend_on_cwd(tmp_path, monkeypatch):
    """Started from anywhere, the composite must load the repo's core params —
    not fall through to XborderMomentumStrategy's own k=10 defaults."""
    monkeypatch.chdir(tmp_path)
    comp = CompositeStrategy({})
    assert comp.params == {"k": 30, "thr_pct": 0.8, "exit_pct": 0.05}
    assert comp.active_modules == []


def test_missing_default_config_and_no_params_raises(tmp_path, monkeypatch):
    """Fail closed: silently trading k=10 under the validated name is a
    different strategy, not a degraded one."""
    monkeypatch.setattr("bot.strategy.composite.DEFAULT_CONFIG_PATH",
                        tmp_path / "gone.yaml")
    with pytest.raises(FileNotFoundError, match="core params"):
        CompositeStrategy({})
    # explicit core params are still enough to construct without the file
    assert CompositeStrategy(dict(PARAMS)).params["k"] == 10


# ---- L-532: a tripped kill switch stops TRADING, not market data ----------
def _record_trading_calls(app, monkeypatch) -> list[str]:
    """Wrap (not replace) every trading entry point so a test can see whether
    it was reached; the originals still run."""
    calls: list[str] = []

    def spy(name, fn):
        def wrapped(*a, **k):
            calls.append(name)
            return fn(*a, **k)
        return wrapped

    monkeypatch.setattr(app, "_sweep_open_orders",
                        spy("sweep", app._sweep_open_orders))
    monkeypatch.setattr(app, "_try_order", spy("try_order", app._try_order))
    monkeypatch.setattr(app.strategy, "on_candles",
                        spy("strategy", app.strategy.on_candles))
    monkeypatch.setattr(app.orders, "cancel_all_active",
                        spy("cancel_all", app.orders.cancel_all_active))
    return calls


def _spread_rows(workdir) -> list[str]:
    return (workdir / "data" / "spread_FX_BTC_JPY.csv").read_text(
        encoding="utf-8").splitlines()[1:]


def test_tripped_step_still_polls_records_and_updates_status(workdir, monkeypatch):
    """(1) The ticker is still polled, the spread still recorded, the leader
    still polled and status.json still written — with the kill state in it."""
    app = build_test_app(monkeypatch)
    leader_polls: list[int] = []
    monkeypatch.setattr(app.leader_feed, "poll", lambda: leader_polls.append(1))
    app.kill_switch.trip(KillReason.MARKET_DATA_ANOMALY, "market data stale: 900s > 60s")

    app.step()
    app.step()

    rows = _spread_rows(workdir)
    assert len(rows) == 2
    assert rows[0].endswith(",9999000.0,10001000.0,10000000.0")
    assert app.feed.last_tick.price == 10_000_000
    assert leader_polls == [1, 1]
    status = json.loads((workdir / "logs" / "status.json").read_text(encoding="utf-8"))
    assert status["running"] is False
    assert status["last_price"] == 10_000_000
    assert status["kill_switch"]["reason"] == "market_data_anomaly"


def test_tripped_step_builds_candles_but_never_trades(workdir, monkeypatch):
    """(2) Candles complete while tripped, yet the sweep, the strategy, the
    order path and the cancel path are never reached and the book is unmoved."""
    app = build_test_app(monkeypatch)
    calls = _record_trading_calls(app, monkeypatch)
    app.kill_switch.trip(KillReason.MANUAL, "operator")

    drive(app, TICKS, LEADER)            # the same ticks that open a short below

    assert len(app.candles.completed) >= 4
    assert len(_spread_rows(workdir)) == len(TICKS)
    assert calls == []
    assert app.portfolio.position_size == 0.0
    assert app.store.active_orders("FX_BTC_JPY") == []
    assert app.kill_switch.state["reason"] == "manual"


def test_untripped_step_still_trades_as_before(workdir, monkeypatch):
    """(4) Not tripped: sweep and strategy run every completed candle and the
    same ticks open the same short as before the change."""
    app = build_test_app(monkeypatch)
    calls = _record_trading_calls(app, monkeypatch)

    drive(app, TICKS, LEADER)

    assert calls.count("sweep") == len(TICKS)
    assert "strategy" in calls and "try_order" in calls
    assert "cancel_all" not in calls
    assert app.portfolio.position_size == pytest.approx(-0.013)
    assert len(_spread_rows(workdir)) == len(TICKS)
    assert not app.kill_switch.is_tripped


def test_untripped_anomaly_still_trips_and_alerts_once(workdir, monkeypatch):
    """(4) First anomaly while trading: trip, cancel, alert — unchanged."""
    from bot.market_data.feed import MarketDataAnomaly
    notifier = RecordingNotifier()
    app = build_test_app(monkeypatch, notifier=notifier)
    cancels: list[str] = []
    monkeypatch.setattr(app.orders, "cancel_all_active", lambda s: cancels.append(s))
    monkeypatch.setattr(app.feed, "poll_ticker", lambda: (_ for _ in ()).throw(
        MarketDataAnomaly("crossed book")))

    app.step()

    assert app.kill_switch.state["reason"] == "market_data_anomaly"
    assert [t for t, _, _ in notifier.sent] == ["KILL SWITCH"]
    assert cancels == ["FX_BTC_JPY"]


def test_data_failures_while_tripped_neither_retrip_nor_realert(workdir, monkeypatch):
    """(3) After the first trip, more anomalies and more API errors (enough to
    trip API_ERRORS twice over) change nothing: same state, one alert, one
    cancel, no counter — and recording resumes when the data comes back."""
    from bot.exchange.bitflyer_client import BitflyerError, NetworkError
    from bot.market_data.feed import MarketDataAnomaly
    notifier = RecordingNotifier()
    app = build_test_app(monkeypatch, notifier=notifier)
    cancels: list[str] = []
    monkeypatch.setattr(app.orders, "cancel_all_active", lambda s: cancels.append(s))
    real_poll = app.feed.poll_ticker
    errors = ([MarketDataAnomaly("crossed book")]
              + [MarketDataAnomaly("abnormal spread")] * 3
              + [BitflyerError(400, "nope")] * 10
              + [NetworkError("connection reset")] * 3)

    def failing_poll():
        raise errors.pop(0)
    monkeypatch.setattr(app.feed, "poll_ticker", failing_poll)

    app.step()                                   # the real first trip
    first_state = dict(app.kill_switch.state)
    for _ in range(len(errors)):                 # bounded: a regression fails, not hangs
        app.step()

    assert not errors
    assert app.kill_switch.state == first_state
    assert json.loads((workdir / "data" / "kill_switch.json")
                      .read_text(encoding="utf-8")) == first_state
    assert [t for t, _, _ in notifier.sent] == ["KILL SWITCH"]
    assert cancels == ["FX_BTC_JPY"]
    assert app._api_errors_in_row == 0
    assert app.status.status.consecutive_api_errors == 0

    monkeypatch.setattr(app.feed, "poll_ticker", real_poll)
    app.step()
    assert len(_spread_rows(workdir)) == 1


def test_run_loop_keeps_recording_after_a_trip_and_alerts_once(workdir, monkeypatch):
    """(3) The loop no longer ends on a trip: a feed that stays stale trips the
    switch once, alerts once, and every later cycle still polls and records."""
    import bot.main as bot_main
    from bot.market_data.feed import MarketDataAnomaly
    notifier = RecordingNotifier()
    app = build_test_app(monkeypatch, notifier=notifier)
    calls = _record_trading_calls(app, monkeypatch)
    monkeypatch.setattr(app.feed, "check_freshness", lambda: (_ for _ in ()).throw(
        MarketDataAnomaly("market data stale: 900s > 60s")))
    sleeps: list[float] = []

    def fake_sleep(sec):
        sleeps.append(sec)
        if len(sleeps) >= 5:
            raise KeyboardInterrupt()
    monkeypatch.setattr(bot_main.time, "sleep", fake_sleep)

    with pytest.raises(KeyboardInterrupt):
        app.run_forever()

    titles = [t for t, _, _ in notifier.sent]
    assert titles == ["BOT START", "KILL SWITCH"]
    assert app.kill_switch.state["reason"] == "market_data_anomaly"
    assert len(_spread_rows(workdir)) == 5       # one per cycle, trip or not
    assert calls.count("sweep") == 1             # the cycle before the trip only
    assert calls.count("cancel_all") == 1        # from the one _on_kill


def test_run_loop_survives_faults_while_tripped_and_alerts_a_manual_kill_once(
        workdir, monkeypatch):
    """(3) A KILL file dropped mid-run is alerted ONCE (it never goes through
    _on_kill); after that an unexpected fault in a data cycle neither ends the
    loop nor re-trips nor re-alerts."""
    import bot.main as bot_main
    notifier = RecordingNotifier()
    app = build_test_app(monkeypatch, notifier=notifier)
    monkeypatch.setattr(app.feed, "check_freshness", lambda: None)
    real_step = app.step
    cycles: list[int] = []

    def step():
        cycles.append(1)
        if len(cycles) == 4:
            raise ValueError("bad row in a data cycle")
        real_step()
    monkeypatch.setattr(app, "step", step)
    sleeps: list[float] = []

    def fake_sleep(sec):
        sleeps.append(sec)
        if len(sleeps) == 2:
            (workdir / "KILL").write_text("", encoding="utf-8")
        if len(sleeps) >= 6:
            raise KeyboardInterrupt()
    monkeypatch.setattr(bot_main.time, "sleep", fake_sleep)

    with pytest.raises(KeyboardInterrupt):
        app.run_forever()

    titles = [t for t, _, _ in notifier.sent]
    assert titles == ["BOT START", "KILL SWITCH"]
    assert app.kill_switch.state["reason"] == "manual"
    assert len(cycles) == 6
    assert len(_spread_rows(workdir)) == 5       # every cycle but the faulty one


def test_main_starts_data_only_when_tripped(workdir, monkeypatch, capsys):
    """A restart while tripped no longer exits: it records data, trades
    nothing, and says why on stdout."""
    import bot.main as bot_main
    KillSwitch().trip(KillReason.MARKET_DATA_ANOMALY, "market data stale")
    app = build_test_app(monkeypatch, notifier=RecordingNotifier())
    ran: list[bool] = []
    monkeypatch.setattr(bot_main, "load_settings", lambda root: app.settings)
    monkeypatch.setattr(bot_main, "setup_logging", lambda: None)
    monkeypatch.setattr(bot_main, "register_secret", lambda value: None)
    monkeypatch.setattr(bot_main, "build_app", lambda settings: app)
    monkeypatch.setattr(app, "run_forever", lambda: ran.append(app.kill_switch.is_tripped))

    assert bot_main.main() == 0
    assert ran == [True]
    assert "refusing to trade" in capsys.readouterr().out


def test_a_feed_that_stays_down_while_tripped_logs_each_kind_once(
        workdir, monkeypatch, caplog):
    """(3) A down venue fails the poll AND the freshness check every cycle; the
    log gets one line per kind for the outage, not two lines per cycle."""
    import bot.main as bot_main
    from bot.exchange.bitflyer_client import NetworkError
    from bot.market_data.feed import MarketDataAnomaly
    KillSwitch().trip(KillReason.MARKET_DATA_ANOMALY, "market data stale")
    notifier = RecordingNotifier()
    app = build_test_app(monkeypatch, notifier=notifier)   # boots tripped
    real_poll = app.feed.poll_ticker
    down = {"on": True}

    def poll():
        if down["on"]:
            raise NetworkError("connection reset")
        return real_poll()
    monkeypatch.setattr(app.feed, "poll_ticker", poll)
    monkeypatch.setattr(app.feed, "check_freshness", lambda: (_ for _ in ()).throw(
        MarketDataAnomaly("market data stale: 900s > 60s")) if down["on"] else None)
    sleeps: list[float] = []

    def fake_sleep(sec):
        sleeps.append(sec)
        if len(sleeps) == 10:
            down["on"] = False
        if len(sleeps) >= 12:
            raise KeyboardInterrupt()
    monkeypatch.setattr(bot_main.time, "sleep", fake_sleep)

    with caplog.at_level(logging.INFO, logger="bot.main"):
        with pytest.raises(KeyboardInterrupt):
            app.run_forever()

    events = [getattr(r, "data", {}).get("event") for r in caplog.records]
    assert events.count("data_only_failure") == 2        # NetworkError + anomaly
    assert events.count("data_only_recovered") == 1
    assert events.count("kill_switch_data_only") == 1
    assert [t for t, _, _ in notifier.sent] == ["BOT START"]   # tripped at boot
    assert len(_spread_rows(workdir)) == 2               # the two cycles after recovery


def test_a_trip_inside_step_is_not_alerted_again_by_the_freshness_check(
        workdir, monkeypatch):
    """(3) step() trips API_ERRORS and alerts; the freshness check that fails
    in the SAME cycle must not trip, cancel or alert a second time."""
    import bot.main as bot_main
    from bot.exchange.bitflyer_client import BitflyerError
    from bot.market_data.feed import MarketDataAnomaly
    notifier = RecordingNotifier()
    app = build_test_app(monkeypatch, notifier=notifier)
    cancels: list[str] = []
    monkeypatch.setattr(app.orders, "cancel_all_active", lambda s: cancels.append(s))
    monkeypatch.setattr(app.feed, "poll_ticker", lambda: (_ for _ in ()).throw(
        BitflyerError(400, "nope")))
    monkeypatch.setattr(app.feed, "check_freshness", lambda: (_ for _ in ()).throw(
        MarketDataAnomaly("market data stale")) if app.kill_switch.is_tripped else None)
    sleeps: list[float] = []

    def fake_sleep(sec):
        sleeps.append(sec)
        if len(sleeps) >= 8:
            raise KeyboardInterrupt()
    monkeypatch.setattr(bot_main.time, "sleep", fake_sleep)

    with pytest.raises(KeyboardInterrupt):
        app.run_forever()

    assert app.kill_switch.state["reason"] == "api_errors"
    assert [t for t, _, _ in notifier.sent] == ["BOT START", "KILL SWITCH"]
    assert cancels == ["FX_BTC_JPY"]


# ---- critic fixes to L-532: jump freeze (A), reset exit (B), fault (C) -----
def _quotes(monkeypatch, app) -> dict:
    """Mutable ticker answer for `app`, with the production jump limit (5%)."""
    app.feed.max_price_jump_pct = 5.0
    quotes = {"ltp": 10_000_000, "best_bid": 9_999_000, "best_ask": 10_001_000}
    monkeypatch.setattr(app.feed._client, "ticker", lambda product: dict(quotes))
    return quotes


def test_tripped_feed_takes_a_price_jump_as_the_new_reference(workdir, monkeypatch):
    """(A) At the production 5% limit, a +6% move while tripped is recorded and
    becomes the reference, so the record does not freeze; a crossed book is
    still rejected and nothing re-trips."""
    app = build_test_app(monkeypatch)
    quotes = _quotes(monkeypatch, app)
    app.kill_switch.trip(KillReason.MANUAL, "operator")
    app.step()
    quotes.update(ltp=10_600_000, best_bid=10_599_000, best_ask=10_601_000)

    for _ in range(50):
        app.step()

    rows = _spread_rows(workdir)
    assert len(rows) == 51
    assert rows[-1].endswith(",10599000.0,10601000.0,10600000.0")
    assert app.feed.last_tick.price == 10_600_000
    assert app.status.status.last_price == 10_600_000
    quotes.update(best_bid=10_602_000)                   # crossed book
    app.step()
    assert len(_spread_rows(workdir)) == 51
    assert app.kill_switch.state["reason"] == "manual"


def test_untripped_price_jump_still_trips_and_is_not_recorded(workdir, monkeypatch):
    """(A) Not tripped: the same +6% move trips the switch exactly as before."""
    notifier = RecordingNotifier()
    app = build_test_app(monkeypatch, notifier=notifier)
    quotes = _quotes(monkeypatch, app)
    app.step()
    quotes.update(ltp=10_600_000, best_bid=10_599_000, best_ask=10_601_000)

    app.step()

    assert app.kill_switch.state["reason"] == "market_data_anomaly"
    assert "abnormal price jump" in app.kill_switch.state["detail"]
    assert [t for t, _, _ in notifier.sent] == ["KILL SWITCH"]
    assert len(_spread_rows(workdir)) == 1
    assert app.feed.last_tick.price == 10_000_000


class _LoopDidNotEnd(BaseException):
    """Backstop for a loop that should have ended by itself: not an Exception,
    so the loop's guards do not swallow it, and not KeyboardInterrupt."""


def test_an_operator_reset_ends_the_data_only_process_without_trading(
        workdir, monkeypatch):
    """(B) A reset by another KillSwitch (state file and KILL file removed)
    ends the loop: no order on the way, the files are not written back, the
    in-memory switch stays tripped (no auto-resume), one BOT STOPPED."""
    import bot.main as bot_main
    (workdir / "KILL").write_text("", encoding="utf-8")
    notifier = RecordingNotifier()
    app = build_test_app(monkeypatch, notifier=notifier)      # boots tripped
    calls = _record_trading_calls(app, monkeypatch)
    monkeypatch.setattr(app.feed, "check_freshness", lambda: None)
    assert (workdir / "data" / "kill_switch.json").exists()
    sleeps: list[float] = []

    def fake_sleep(sec):
        sleeps.append(sec)
        if len(sleeps) == 3:
            KillSwitch().reset(operator_confirm=True)
        if len(sleeps) >= 10:
            raise _LoopDidNotEnd()
    monkeypatch.setattr(bot_main.time, "sleep", fake_sleep)

    app.run_forever()                                    # returns: normal exit

    assert len(sleeps) == 3
    assert calls == []
    assert app.portfolio.trades == []
    assert app.store.active_orders("FX_BTC_JPY") == []
    assert not (workdir / "data" / "kill_switch.json").exists()
    assert not (workdir / "KILL").exists()
    assert app.kill_switch.is_tripped
    assert [t for t, _, _ in notifier.sent] == ["BOT START", "BOT STOPPED"]
    assert len(_spread_rows(workdir)) == 3


def test_an_unexpected_fault_while_trading_trips_once_and_keeps_recording(
        workdir, monkeypatch):
    """(C) A fault in a trading cycle trips (persisted) and alerts once, and
    the process goes on recording in data-only mode instead of exiting."""
    notifier = RecordingNotifier()
    app = build_test_app(monkeypatch, notifier=notifier)
    cancels: list[str] = []
    monkeypatch.setattr(app.orders, "cancel_all_active", lambda s: cancels.append(s))
    monkeypatch.setattr(app.feed, "check_freshness", lambda: None)
    real_step = app.step
    cycles: list[int] = []

    def step():
        cycles.append(1)
        if len(cycles) == 2:
            raise ValueError("bad row in a trading cycle")
        real_step()
    monkeypatch.setattr(app, "step", step)
    _interrupt_on_sleep(monkeypatch, after=6)

    with pytest.raises(KeyboardInterrupt):
        app.run_forever()

    assert app.kill_switch.state["reason"] == "unhandled_exception"
    assert "bad row" in app.kill_switch.state["detail"]
    assert json.loads((workdir / "data" / "kill_switch.json")
                      .read_text(encoding="utf-8"))["reason"] == "unhandled_exception"
    assert [t for t, _, _ in notifier.sent] == ["BOT START", "KILL SWITCH"]
    assert cancels == ["FX_BTC_JPY"]
    assert len(cycles) == 6
    assert len(_spread_rows(workdir)) == 5               # every cycle but the faulty one


def test_a_fault_after_a_kill_in_the_same_cycle_is_not_alerted_twice(
        workdir, monkeypatch):
    """(C) step() trips and runs _on_kill, then a fault in the same cycle: the
    first reason stays, and there is no second cancel or alert."""
    notifier = RecordingNotifier()
    app = build_test_app(monkeypatch, notifier=notifier)
    cancels: list[str] = []
    monkeypatch.setattr(app.orders, "cancel_all_active", lambda s: cancels.append(s))
    monkeypatch.setattr(app.feed, "check_freshness", lambda: None)

    def kill_then_fault():
        if not app.kill_switch.is_tripped:
            app.kill_switch.trip(KillReason.API_ERRORS, "5 in a row")
            app._on_kill("5 in a row")
            raise RuntimeError("a fault after the kill")
    monkeypatch.setattr(app, "step", kill_then_fault)
    _interrupt_on_sleep(monkeypatch, after=4)

    with pytest.raises(KeyboardInterrupt):
        app.run_forever()

    assert app.kill_switch.state["reason"] == "api_errors"
    assert [t for t, _, _ in notifier.sent] == ["BOT START", "KILL SWITCH"]
    assert cancels == ["FX_BTC_JPY"]


def test_a_trip_never_seen_on_disk_is_not_taken_for_a_reset(workdir, monkeypatch):
    """(B) An in-memory trip whose state file is missing (as if the write had
    failed) is not a reset: the process stays data-only, it does not exit."""
    app = build_test_app(monkeypatch, notifier=RecordingNotifier())
    monkeypatch.setattr(app.feed, "check_freshness", lambda: None)
    app.kill_switch.trip(KillReason.MANUAL, "operator")
    (workdir / "data" / "kill_switch.json").unlink()
    _interrupt_on_sleep(monkeypatch, after=5)

    with pytest.raises(KeyboardInterrupt):
        app.run_forever()

    assert app.kill_switch.is_tripped
    assert len(_spread_rows(workdir)) == 5


# ---- L-544: stale market data PAUSES a paper bot (no kill switch) ----------
STALE_SEC = 60.0
PAUSE_TITLE = "データ停滞: 取引を一時停止"
RESUME_TITLE = "データ回復: 取引を再開"


def _safe_retry_error():
    """What a 503 on the ticker really raises: classified SAFE_RETRY, so it
    never counts towards API_ERRORS — staleness is all it causes."""
    from bot.exchange.bitflyer_client import BitflyerClient
    session = FakeSession()
    session.set("GET", "/v1/ticker", FakeResponse(503, {"error_message": "busy"}))
    try:
        BitflyerClient(session=session, sleep=lambda s: None).ticker("FX_BTC_JPY")
    except Exception as e:                         # noqa: BLE001 - captured
        return e
    raise AssertionError("a 503 did not raise")


class _StaleRig:
    """Drives `run_forever` on a virtual clock: the feed reads `now`, every
    loop sleep advances it by the poll interval, and the ticker is down
    (`error`) while down_at <= now < up_at. `log` holds (now, paused,
    tripped) at the end of each cycle; `hooks[t]` runs at the end of the
    cycle at clock t."""

    def __init__(self, app, monkeypatch, *, start, down_at=None, up_at=None,
                 until):
        import bot.main as bot_main
        self.app, self.now, self.until = app, float(start), float(until)
        self.down_at, self.up_at = down_at, up_at
        self.error = _safe_retry_error()
        self.quotes = {"ltp": 10_000_000, "best_bid": 9_999_000,
                       "best_ask": 10_001_000}
        self.log: list[tuple[float, bool, bool]] = []
        self.hooks: dict[float, object] = {}
        self.calls: list[tuple[float, str, object]] = []
        app.feed.max_staleness_sec = STALE_SEC
        app._base_staleness_sec = STALE_SEC
        app.feed._clock = lambda: self.now
        monkeypatch.setattr(app.feed._client, "ticker", self._ticker)
        real_try, real_strategy = app._try_order, app.strategy.on_candles

        def try_order(*a, **k):
            self.calls.append((self.now, "try_order", a[0]))
            return real_try(*a, **k)

        def on_candles(df):
            self.calls.append((self.now, "strategy", list(df["start"])))
            return real_strategy(df)
        monkeypatch.setattr(app, "_try_order", try_order)
        monkeypatch.setattr(app.strategy, "on_candles", on_candles)

        def fake_sleep(sec):
            self.log.append((self.now, getattr(app, "_stale_pause", None) is not None,
                             app.kill_switch.is_tripped))
            hook = self.hooks.get(self.now)
            if hook is not None:
                hook()
            if self.now >= self.until:
                raise KeyboardInterrupt()
            self.now += sec
        monkeypatch.setattr(bot_main.time, "sleep", fake_sleep)

    def _ticker(self, product):
        if self.down_at is not None and self.down_at <= self.now \
                and (self.up_at is None or self.now < self.up_at):
            raise self.error
        return dict(self.quotes)

    def run(self):
        with pytest.raises(KeyboardInterrupt):
            self.app.run_forever()

    def paused_at(self, t: float) -> bool:
        return next(p for now, p, _ in self.log if now == t)

    def first(self, *, paused: bool, after: float = float("-inf")) -> float:
        return next(now for now, p, _ in self.log if p is paused and now > after)


# Timeline (candle_interval_sec = 60, poll 5s): the leader falls 0.2% a
# candle, so k=2 momentum is -0.4% and the strategy opens a short early on.
# The ticker is down from 10_040; the last fresh tick is 10_035, so the data
# is stale (> 60s) at 10_100. It is back at 10_180 — mid-candle — so the
# first candle built only from fresh data starts at 10_200 and completes
# with the first tick at or after 10_260.
START, DOWN, UP, BOUNDARY = 9_630.0, 10_040.0, 10_180.0, 10_200
GAP_LEADER = {s: 100000.0 * float(np.exp(-0.002 * ((s - 9_600) // 60)))
              for s in range(9_600, BOUNDARY, 60)}
# After the gap the leader sits far lower and flat: a window that reaches
# back across the gap reads a huge drop (a SELL), a window of fresh candles
# reads no momentum at all.
GAP_LEADER.update({s: 90000.0 for s in range(BOUNDARY, 11_000, 60)})


def _gap_app(monkeypatch, notifier=None, *, until, up_at=UP, strategy_name="composite"):
    app = build_test_app(monkeypatch, notifier=notifier or RecordingNotifier(),
                         strategy_name=strategy_name)
    app.leader_feed._closes.update(GAP_LEADER)
    rig = _StaleRig(app, monkeypatch, start=START, down_at=DOWN, up_at=up_at,
                    until=until)
    return app, rig


def _status_json(workdir) -> dict:
    return json.loads((workdir / "logs" / "status.json").read_text(encoding="utf-8"))


def test_stale_paper_data_pauses_closes_and_alerts_once(workdir, monkeypatch):
    """(1) PAPER + stale: paused, not tripped — no kill-switch file — the
    short is closed at the LAST RECEIVED quote, no order or strategy call
    after that, one alert across many stale cycles, status.json says so."""
    notifier = RecordingNotifier()
    app, rig = _gap_app(monkeypatch, notifier, until=UP - 5)
    rig.run()

    pause_t = rig.first(paused=True)
    assert pause_t == 10_100.0                    # first cycle older than 60s
    assert all(p for t, p, _ in rig.log if t >= pause_t)
    assert not app.kill_switch.is_tripped
    assert not (workdir / "data" / "kill_switch.json").exists()
    opened = [c for c in rig.calls if c[1] == "try_order" and c[0] < pause_t]
    assert opened and opened[0][2] == "SELL"      # the short opened before
    assert app.portfolio.position_size == 0.0
    close = app.portfolio.trades[-1]
    assert (close.side, close.price) == ("BUY", 10_001_000)   # last ask seen
    assert [c for c in rig.calls if c[0] > pause_t] == []
    assert [(t, n, s) for t, n, s in rig.calls if t == pause_t] == [
        (pause_t, "try_order", "BUY")]
    assert [t for t, _, _ in notifier.sent] == ["BOT START", PAUSE_TITLE]
    assert "キルスイッチは発動していません" in notifier.sent[-1][1]
    pause = _status_json(workdir)["data_stale_pause"]
    assert "market data stale" in pause["detail"]
    assert pause["fresh_since"] is None
    assert _status_json(workdir)["kill_switch"] is None


def test_paused_bot_resumes_after_one_fresh_candle_and_alerts_once(
        workdir, monkeypatch):
    """(2) Data back at 10_180: the first all-fresh candle (10_200) completes
    at 10_260 and trading resumes there, with one alert. The quote moved
    when the data came back, and the close is still at the old price."""
    notifier = RecordingNotifier()
    app, rig = _gap_app(monkeypatch, notifier, until=10_400)
    rig.hooks[UP - 5] = lambda: rig.quotes.update(
        ltp=10_050_000, best_bid=10_049_000, best_ask=10_051_000)
    rig.run()

    assert rig.first(paused=False, after=10_100.0) == 10_260.0
    assert all(not p for t, p, _ in rig.log if t >= 10_260.0)
    assert [t for t, _, _ in notifier.sent] == ["BOT START", PAUSE_TITLE,
                                                RESUME_TITLE]
    assert not app.kill_switch.is_tripped
    assert not (workdir / "data" / "kill_switch.json").exists()
    assert app.portfolio.trades[-1].price == 10_001_000      # no future price
    assert _status_json(workdir)["data_stale_pause"] is None
    assert any(n == "strategy" for t, n, _ in rig.calls if t >= 10_260.0)


def test_pause_does_not_resume_before_a_fresh_candle_completes(workdir, monkeypatch):
    """(3) Fresh ticks from 10_180 on, and the part-fresh candle 10_140
    completes at 10_200 — still paused. Only 10_260 (10_200 + one
    candle_interval_sec) resumes."""
    app, rig = _gap_app(monkeypatch, until=10_260)
    rig.run()

    for t in (10_180.0, 10_200.0, 10_230.0, 10_255.0):
        assert rig.paused_at(t), t
    assert not rig.paused_at(10_260.0)
    assert [c for c in rig.calls if 10_100.0 < c[0] < 10_260.0] == []


def test_live_stale_data_still_trips_the_kill_switch(workdir, monkeypatch):
    """(4) LIVE is unchanged: stale data trips the persisted kill switch,
    alerts KILL SWITCH, and never pauses."""
    from bot.exchange.bitflyer_client import BitflyerClient
    from bot.settings import Secret
    session = FakeSession()
    session.set("GET", "/v1/me/getpermissions", FakeResponse(200, [
        "/v1/me/getbalance", "/v1/me/sendchildorder"]))
    session.set("GET", "/v1/me/getbalance", FakeResponse(200, [
        {"currency_code": "JPY", "available": 200000}]))
    session.set("GET", "/v1/me/getpositions", FakeResponse(200, []))
    settings = Settings(mode=Mode.LIVE, product_code="FX_BTC_JPY",
                        api_key=Secret("key"), api_secret=Secret("secret"),
                        config=app_config("xborder_momentum"),
                        risk_limits=RiskLimits.from_dict(dict(APP_LIMITS)))
    client = BitflyerClient(settings.api_key, settings.api_secret,
                            session=session, sleep=lambda s: None)
    notifier = RecordingNotifier()
    app = TradingApp(settings, client, notifier)
    monkeypatch.setattr(app.leader_feed, "poll", lambda: None)
    rig = _StaleRig(app, monkeypatch, start=START, down_at=DOWN, until=10_200)
    rig.run()

    assert app.kill_switch.state["reason"] == "market_data_anomaly"
    assert "market data stale" in app.kill_switch.state["detail"]
    assert json.loads((workdir / "data" / "kill_switch.json").read_text(
        encoding="utf-8"))["reason"] == "market_data_anomaly"
    assert [t for t, _, _ in notifier.sent] == ["BOT START", "KILL SWITCH"]
    assert not any(p for _, p, _ in rig.log)
    assert _status_json(workdir)["data_stale_pause"] is None


def _boom(*a, **k):
    raise ValueError("bad row")


# (name, what to break, expected kill reason). Each is injected at the end of
# the cycle at clock `at`, so the next cycle meets it.
NON_STALE_FAULTS = [
    ("crossed_book", lambda rig: rig.quotes.update(best_bid=10_002_000),
     "market_data_anomaly"),
    ("abnormal_spread", lambda rig: rig.quotes.update(best_bid=9_000_000),
     "market_data_anomaly"),
    ("non_positive_price", lambda rig: rig.quotes.update(ltp=0),
     "market_data_anomaly"),
    ("price_jump", lambda rig: (setattr(rig.app.feed, "max_price_jump_pct", 5.0),
                                rig.quotes.update(ltp=10_600_000,
                                                  best_bid=10_599_000,
                                                  best_ask=10_601_000)),
     "market_data_anomaly"),
    ("api_errors", lambda rig: setattr(rig, "error", __import__(
        "bot.exchange.bitflyer_client", fromlist=["BitflyerError"]
    ).BitflyerError(400, "nope")), "api_errors"),
    ("kill_file", lambda rig: (Path("KILL").write_text("", encoding="utf-8")),
     "manual"),
    ("unexpected_exception",
     lambda rig: setattr(rig.app.spread_recorder, "record", _boom),
     "unhandled_exception"),
]


@pytest.mark.parametrize("name,inject,reason", NON_STALE_FAULTS,
                         ids=[f[0] for f in NON_STALE_FAULTS])
def test_paper_non_stale_faults_still_trip(workdir, monkeypatch, name, inject,
                                           reason):
    """(5) PAPER, data fresh, any anomaly but staleness: the kill switch trips
    (persisted) exactly as before — no pause. API errors are injected by
    taking the ticker down with a COUNTED error, five polls before it could
    go stale."""
    notifier = RecordingNotifier()
    app = build_test_app(monkeypatch, notifier=notifier)
    rig = _StaleRig(app, monkeypatch, start=START, until=START + 120)
    rig.hooks[START + 20] = lambda: inject(rig)
    if name == "api_errors":
        rig.down_at = START + 25
    rig.run()

    assert app.kill_switch.state["reason"] == reason
    assert (workdir / "data" / "kill_switch.json").exists()
    assert not any(p for _, p, _ in rig.log)
    titles = [t for t, _, _ in notifier.sent]
    assert "KILL SWITCH" in titles and PAUSE_TITLE not in titles
    assert _status_json(workdir)["data_stale_pause"] is None


def test_paper_no_data_ever_still_trips(workdir, monkeypatch):
    """(5) 'no market data received yet' is not staleness — there is no
    fresh data to go back to — and still trips, as before."""
    notifier = RecordingNotifier()
    app = build_test_app(monkeypatch, notifier=notifier)
    rig = _StaleRig(app, monkeypatch, start=START, down_at=START, until=START + 30)
    rig.run()

    assert app.kill_switch.state["reason"] == "market_data_anomaly"
    assert app.kill_switch.state["detail"] == "no market data received yet"
    assert not any(p for _, p, _ in rig.log)
    assert _status_json(workdir)["data_stale_pause"] is None


# A price jump is not among them: while paused no order can be sent, so a
# move larger than the jump limit across the outage is taken as the new
# reference (see the test after this one), not a trip.
DURING_PAUSE_FAULTS = [f for f in NON_STALE_FAULTS if f[0] != "price_jump"]


@pytest.mark.parametrize("name,inject,reason", DURING_PAUSE_FAULTS,
                         ids=[f[0] for f in DURING_PAUSE_FAULTS])
def test_non_stale_fault_during_the_pause_trips(workdir, monkeypatch, name,
                                                inject, reason):
    """(6) Paused at 10_100; the fault is armed while paused and data comes
    back at 10_180 (API errors: the outage turns into counted errors
    instead). The kill switch trips as it always has, and the pause ends."""
    notifier = RecordingNotifier()
    app, rig = _gap_app(monkeypatch, notifier, until=10_250)
    rig.hooks[10_150.0] = lambda: inject(rig)
    rig.run()

    assert rig.paused_at(10_150.0)
    assert app.kill_switch.state["reason"] == reason
    assert (workdir / "data" / "kill_switch.json").exists()
    titles = [t for t, _, _ in notifier.sent]
    assert titles == ["BOT START", PAUSE_TITLE, "KILL SWITCH"]
    assert app._stale_pause is None
    assert _status_json(workdir)["data_stale_pause"] is None
    assert not any(p for t, p, _ in rig.log if t > 10_185.0)


def test_candles_from_before_the_resume_never_reach_the_strategy(
        workdir, monkeypatch):
    """(7) A window reaching back across the gap reads the leader's drop
    (100000 -> 90000) as a SELL. After the resume the strategy only ever
    sees candles from 10_200 on, and fresh candles hold no momentum: no
    order, the book stays flat."""
    app, rig = _gap_app(monkeypatch, until=10_500)
    rig.run()

    after = [s for t, n, s in rig.calls if n == "strategy" and t >= 10_260.0]
    assert len(after) >= 5
    assert all(min(starts) >= BOUNDARY for starts in after)
    assert [c for c in rig.calls if c[1] == "try_order" and c[0] > 10_100.0] == []
    assert app.portfolio.position_size == 0.0
    assert [c.start for c in app.candles.completed][0] == BOUNDARY


def test_a_restart_does_not_carry_the_pause(workdir, monkeypatch):
    """(8) The pause lives in the process: a restart after one finds nothing
    tripped and nothing paused, and trades normally."""
    app, rig = _gap_app(monkeypatch, until=10_150)
    rig.run()
    assert rig.paused_at(10_150.0)

    restarted = build_test_app(monkeypatch)
    assert restarted._stale_pause is None
    assert not restarted.kill_switch.is_tripped
    drive(restarted, TICKS, LEADER)
    assert restarted.portfolio.position_size == pytest.approx(-0.013)


def test_a_price_jump_across_the_outage_resumes_instead_of_tripping(
        workdir, monkeypatch):
    """(L-544, lead decision) The price moved +6% while the data was gone
    (jump limit 5%): the first fresh tick becomes the new reference, the
    pause ends after one fresh candle as usual, nothing trips. After the
    resume the jump check is back: a second +6% move trips."""
    notifier = RecordingNotifier()
    app, rig = _gap_app(monkeypatch, notifier, until=10_400)
    app.feed.max_price_jump_pct = 5.0
    rig.hooks[UP - 5] = lambda: rig.quotes.update(
        ltp=10_600_000, best_bid=10_599_000, best_ask=10_601_000)
    rig.hooks[10_300.0] = lambda: rig.quotes.update(
        ltp=11_236_000, best_bid=11_235_000, best_ask=11_237_000)
    rig.run()

    assert rig.first(paused=False, after=10_100.0) == 10_260.0
    assert [t for t, _, _ in notifier.sent][:3] == ["BOT START", PAUSE_TITLE,
                                                    RESUME_TITLE]
    assert app.kill_switch.state["reason"] == "market_data_anomaly"
    assert "abnormal price jump" in app.kill_switch.state["detail"]


def test_a_price_jump_after_the_first_fresh_tick_still_trips(workdir, monkeypatch):
    """(critic 1c37399b #1) Only the FIRST fresh tick may jump. A +6% print
    at 10_255 — the data has been back since 10_180 — is checked as in
    normal running: it trips, it does not become the reference the resume
    is built on (before the fix it resumed at 10_260 on that price)."""
    app, rig = _gap_app(monkeypatch, until=10_400)
    app.feed.max_price_jump_pct = 5.0
    rig.hooks[10_250.0] = lambda: rig.quotes.update(
        ltp=10_600_000, best_bid=10_599_000, best_ask=10_601_000)
    rig.run()

    assert app.kill_switch.is_tripped
    assert app.kill_switch.state["reason"] == "market_data_anomaly"
    assert "abnormal price jump" in app.kill_switch.state["detail"]
    assert next(t for t, _, k in rig.log if k) == 10_255.0   # on that tick
    assert not any(n == "strategy" for t, n, _ in rig.calls if t >= 10_180.0)


def test_stale_again_before_the_resume_restarts_the_resume_clock(
        workdir, monkeypatch):
    """(critic 1c37399b #4) Data back at 10_180, down again 10_230-10_330,
    stale again at 10_290: the candle 10_200 is no longer all fresh, so no
    resume at 10_260. The clock restarts at the next fresh tick (10_330),
    the first all-fresh candle is 10_380, resume at 10_440. No second pause
    alert."""
    notifier = RecordingNotifier()
    app, rig = _gap_app(monkeypatch, notifier, until=10_500)
    real = rig._ticker

    def ticker(product):
        if 10_230 <= rig.now < 10_330:
            raise rig.error
        return real(product)
    monkeypatch.setattr(app.feed._client, "ticker", ticker)
    rig.run()

    for t in (10_260.0, 10_290.0, 10_330.0, 10_435.0):
        assert rig.paused_at(t), t
    assert rig.first(paused=False, after=10_100.0) == 10_440.0
    assert [c.start for c in app.candles.completed][0] == 10_380
    assert [t for t, _, _ in notifier.sent] == ["BOT START", PAUSE_TITLE,
                                                RESUME_TITLE]
    assert not app.kill_switch.is_tripped


def test_pause_and_resume_alerts_are_japanese_and_the_resume_repeats_the_close(
        workdir, monkeypatch):
    """(critic 1c37399b #3, #9) The pause alert may be lost when the PC's
    own network is what went down, so the resume alert carries the reason
    and the close as well. Neither carries the English log detail (O-1)."""
    notifier = RecordingNotifier()
    app, rig = _gap_app(monkeypatch, notifier, until=10_300)
    rig.run()

    (_, pause_body, _), (_, resume_body, _) = notifier.sent[1], notifier.sent[2]
    for body in (pause_body, resume_body):
        assert "market data stale" not in body
        assert "最後に市場データを受け取ってから" in body
    assert "売り建玉 0.013 を最後に受け取った値段" in resume_body


def test_a_refused_stale_pause_close_trips_as_before(workdir, monkeypatch):
    """Owner L-547 "2.(a)": when the close at the pause is refused the
    position is not left open through the pause with no stop-loss — the
    kill switch trips, as it did before the pause existed."""
    notifier = RecordingNotifier()
    app, rig = _gap_app(monkeypatch, notifier, until=10_200)
    real = app._try_order

    def refuse_when_stale(*a, **k):
        if rig.now >= 10_100.0:
            return None
        return real(*a, **k)
    monkeypatch.setattr(app, "_try_order", refuse_when_stale)
    rig.run()

    assert app.kill_switch.is_tripped
    assert app.kill_switch.state["reason"] == "market_data_anomaly"
    assert "could not be closed" in app.kill_switch.state["detail"]
    assert app._stale_pause is None
    assert app.portfolio.position_size == pytest.approx(-0.013)
    assert PAUSE_TITLE not in [t for t, _, _ in notifier.sent]


def test_status_report_shows_the_pause_in_japanese_with_jst_times():
    """(second critic, finding on status.py) The STATUS report goes to the
    owner: the pause line is Japanese and the times are JST clock times,
    not Unix seconds."""
    from bot.monitoring.status import _stale_pause_line
    line = _stale_pause_line({"since": 0.0, "fresh_since": 3600.0})
    assert "開始 09:00:00 JST" in line and "データ回復 10:00:00 JST" in line
    assert "since" not in line and "3600" not in line
    assert "データ回復 -" in _stale_pause_line({"since": 0.0, "fresh_since": None})
