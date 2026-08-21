"""Composite strategy — the vehicle the validated pieces get bolted onto.

What this is
------------
A CARRIER, not a new edge. The core signal is `xborder_momentum` verbatim
(the only strategy currently under paper validation), and CompositeStrategy
adds two things around it:

1. a fail-closed MODULE framework, so a pending hypothesis can be wired in
   only after its pre-registered gate has actually been judged, and
2. a convention-based RISK OVERLAY that scales new exposure.

Baseline equivalence (E0 gate)
------------------------------
With every module disabled, CompositeStrategy is signal-for-signal identical
to XborderMomentumStrategy with the same params — no reason string, no
indicator value differs. That is the reproduction gate demanded by the
research protocol (a new vehicle must reproduce the existing baseline
trade-for-trade before any difference may be discussed). It is enforced by
tests/test_composite.py and scripts/validate_composite.py.

Why every module ships disabled
-------------------------------
Each module corresponds to a hypothesis listed as PENDING in
docs/KNOWLEDGE.md §4. None has passed its judgment, so none may trade.
`enabled: true` with an empty `gate_evidence` raises at construction: editing
config alone can never switch on an unvalidated module. The hooks are stubs —
invoking one while enabled raises NotImplementedError rather than inventing a
rule that was never measured.

Risk overlay: convention, NOT a fitted parameter
------------------------------------------------
`size_factor()` halves new exposure while equity sits below 95% of its running
peak, and halves it again after 3 consecutive losses (floor 0.25). 95% / 3 /
0.5 are conventional risk-of-ruin brakes fixed a priori; no backtest was
searched to choose them and none may be — tuning them on this repo's data
would turn a convention into an unregistered parameter search. Sizing cannot
change per-trade % expectancy; it only reshapes the equity path.

The overlay applies to NEW exposure only. Closing/exit orders are never
scaled and never blocked, the same invariant `increases_exposure` enforces in
bot/risk/pre_trade_checks.py: a position opened at a cap must stay exitable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
import yaml

from bot.strategy.base import Signal, SignalType, Strategy
from bot.strategy.xborder_momentum import XborderMomentumStrategy

DEFAULT_CONFIG_PATH = Path("config") / "composite.yaml"
CORE_PARAM_KEYS = ("k", "thr_pct", "exit_pct")

# Risk-overlay conventions (see module docstring — fixed a priori, not fitted)
DRAWDOWN_TRIGGER = 0.95      # scale down while equity < 95% of running peak
LOSS_STREAK_TRIGGER = 3      # scale down after this many losses in a row
SCALE_STEP = 0.5             # each trigger halves new exposure
MIN_SIZE_FACTOR = 0.25       # floor, however many triggers are active


class ModuleGateError(RuntimeError):
    """A module would act without its pre-registered gate being satisfied."""


@dataclass
class ModuleContext:
    """What a module needs beyond the candles.

    The Strategy interface is position-blind by design (bot/strategy/base.py),
    but a veto must never touch a closing order — so the position-aware caller
    passes `position_size` in here.
    """

    candles: pd.DataFrame | None = None
    timestamp: float | None = None
    position_size: float = 0.0
    extra: dict = field(default_factory=dict)


class CompositeModule:
    """Base class for an optional module.

    Subclasses declare NAME and GATE (the pre-registered unlock criterion).
    A module is inert while disabled: CompositeStrategy never calls a hook on
    it. While enabled the hooks below must be implemented — the stubs raise so
    an unbuilt module can never silently pass judgement on a trade.
    """

    NAME = ""
    GATE = ""

    def __init__(self, *, enabled: bool = False, gate_evidence: str = "",
                 params: dict | None = None):
        self.name = self.NAME
        self.gate = self.GATE
        self.enabled = bool(enabled)
        self.gate_evidence = str(gate_evidence or "").strip()
        self.params = dict(params or {})
        if self.enabled and not self.gate_evidence:
            raise ModuleGateError(
                f"module '{self.name}' is enabled but has no gate_evidence. "
                f"Gate: {self.gate}. Record the report reference that satisfies "
                "the gate (owner approval required) before enabling."
            )

    # ---- hooks (entry side only; exits are never consulted) ---------------
    def veto_entry(self, signal: Signal, context: ModuleContext) -> bool:
        """True = refuse this NEW entry. Never called for a close."""
        raise NotImplementedError(
            f"module '{self.name}' has no veto rule yet; gate: {self.gate}")

    def scale_entry(self, signal: Signal, context: ModuleContext) -> float:
        """Multiplicative size factor for this NEW entry (1.0 = untouched)."""
        raise NotImplementedError(
            f"module '{self.name}' has no sizing rule yet; gate: {self.gate}")

    def describe(self) -> dict:
        return {"name": self.name, "enabled": self.enabled, "gate": self.gate,
                "gate_evidence": self.gate_evidence}


class ImbalanceFilterModule(CompositeModule):
    """Would veto entries whose order-book imbalance opposes the signal.

    Effect and sign are real but measured at 0.29-1.35bps against a 2.22bps
    spread (KNOWLEDGE §3): unusable as a standalone taker signal, plausible
    only as a filter on top of an existing signal. Pending §4.
    """

    NAME = "imbalance_filter"
    GATE = "board-data judgment >= 1-2 weeks recording, per KNOWLEDGE.md §4"


class FundingWindowModule(CompositeModule):
    """Would veto entries inside a configurable post-settlement window.

    Params: `window_start_utc` ("HH:MM") and `window_minutes`. Motivated by a
    -8.2bps drift after the 13:00 UTC funding settlement on n=21 (t~1.8) —
    under-powered, hence the 3x-sample gate. Pending §4.
    """

    NAME = "funding_window"
    GATE = "13:00 UTC post-settlement drift re-test at 3x sample"


class OiRegimeModule(CompositeModule):
    """Would veto or scale entries by open-interest condition.

    OKX history is ~30 days and non-pageable, so the judgment waits on the
    self-recorded data/oi_snapshots.csv reaching 30 days. Pending §4.
    """

    NAME = "oi_regime"
    GATE = "oi_snapshots.csv 30-day phase-C judgment"


MODULE_CLASSES: dict[str, type[CompositeModule]] = {
    cls.NAME: cls for cls in (ImbalanceFilterModule, FundingWindowModule, OiRegimeModule)
}


def build_modules(raw: dict | None) -> list[CompositeModule]:
    """Instantiate every registered module from config (all default: off).

    Fail-closed in three ways: an unknown module name is an error, a `gate`
    text that does not match the one pre-registered in code is an error (the
    gate cannot be weakened by editing YAML), and enabled-without-evidence
    raises in CompositeModule.__init__.
    """
    raw = dict(raw or {})
    unknown = sorted(set(raw) - set(MODULE_CLASSES))
    if unknown:
        raise ValueError(f"unknown composite module(s): {unknown}; "
                         f"known: {sorted(MODULE_CLASSES)}")
    modules = []
    for name, cls in MODULE_CLASSES.items():
        cfg = dict(raw.get(name) or {})
        gate = str(cfg.get("gate", cls.GATE)).strip()
        if gate != cls.GATE:
            raise ModuleGateError(
                f"module '{name}' gate text in config does not match the "
                f"pre-registered gate. config: {gate!r}; registered: {cls.GATE!r}"
            )
        modules.append(cls(enabled=bool(cfg.get("enabled", False)),
                           gate_evidence=cfg.get("gate_evidence", ""),
                           params=cfg.get("params")))
    return modules


def load_composite_config(path: str | Path | None = None) -> dict:
    """Read config/composite.yaml. A missing DEFAULT path yields {} (all
    modules off — the safe state); a path given explicitly must exist."""
    explicit = path is not None
    path = Path(path) if explicit else DEFAULT_CONFIG_PATH
    if not path.exists():
        if explicit:
            raise FileNotFoundError(f"composite config not found: {path}")
        return {}
    with open(path, encoding="utf-8") as f:   # cp932 default on Windows breaks UTF-8
        return yaml.safe_load(f) or {}


class CompositeStrategy(Strategy):
    """xborder_momentum core + (disabled) modules + risk overlay."""

    def __init__(self, params: dict | None = None, *,
                 modules: list[CompositeModule] | None = None,
                 config_path: str | Path | None = None):
        params = dict(params or {})
        file_cfg = load_composite_config(
            config_path if config_path is not None else params.get("config_path"))
        core = dict(file_cfg.get("core") or {})
        for key in CORE_PARAM_KEYS:      # config.yaml strategy.params wins
            if key in params:
                core[key] = params[key]
        super().__init__(core)
        self.core = XborderMomentumStrategy(core)
        self.modules = list(modules) if modules is not None \
            else build_modules(file_cfg.get("modules"))
        self._active = [m for m in self.modules if m.enabled]

    @property
    def min_history(self) -> int:
        return self.core.min_history

    @property
    def active_modules(self) -> list[CompositeModule]:
        return list(self._active)

    def on_candles(self, candles: pd.DataFrame) -> Signal:
        """Core signal, untouched. Modules act in `gate_entry`, which needs
        the position and therefore only the position-aware caller can run."""
        return self.core.on_candles(candles)

    def gate_entry(self, signal: Signal, context: ModuleContext | None = None) -> Signal:
        """Run enabled modules against a signal that would OPEN exposure.

        Returns the signal unchanged, or HOLD when a module vetoes. CLOSE,
        HOLD and any signal that reduces an existing position are returned
        untouched — a module can never block an exit. With no enabled module
        this is the identity function and touches nothing (E0 equivalence).
        """
        if not self._active:
            return signal
        if signal.type not in (SignalType.BUY, SignalType.SELL):
            return signal
        pos = context.position_size if context is not None else 0.0
        closing = (signal.type is SignalType.BUY and pos < 0) or \
                  (signal.type is SignalType.SELL and pos > 0)
        if closing:
            return signal
        ctx = context if context is not None else ModuleContext()
        for module in self._active:
            if module.veto_entry(signal, ctx):
                return Signal(SignalType.HOLD,
                              f"entry vetoed by module {module.name}",
                              dict(signal.indicators))
        return signal

    @staticmethod
    def size_factor(equity_peak: float, equity_now: float,
                    consecutive_losses: int) -> float:
        """Size multiplier for NEW exposure only (see module docstring).

        1.0 normally; x0.5 while equity is below 95% of its running peak;
        x0.5 after 3+ consecutive losses (the caller's counter resets on a
        win); factors multiply, floored at 0.25. Never applied to a closing
        order — the caller must not consult this when reducing exposure.
        """
        factor = 1.0
        if equity_peak > 0 and equity_now < DRAWDOWN_TRIGGER * equity_peak:
            factor *= SCALE_STEP
        if consecutive_losses >= LOSS_STREAK_TRIGGER:
            factor *= SCALE_STEP
        return max(factor, MIN_SIZE_FACTOR)
