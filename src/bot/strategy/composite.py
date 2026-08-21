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
docs/KNOWLEDGE.md §4. None has passed its judgment, so none may trade. The
framework is fail-closed at CONSTRUCTION, not at call time:

* `enabled: true` with an empty `gate_evidence` raises,
* `gate_evidence` that does not name an existing docs/RESEARCH_REPORT_*.md
  raises (a made-up reference cannot unlock a module),
* a module entry in YAML that omits `gate`, or whose `gate` text differs from
  the one pre-registered in code, raises, and
* `enabled: true` on a module that has no `veto_entry` implementation raises.
  The base hook is an unimplemented stub, so an enabled-but-unbuilt module can
  never construct — it cannot fail open at decision time because it cannot
  exist.

Risk overlay: convention, NOT a fitted parameter
------------------------------------------------
`size_factor()` halves new exposure while equity sits below 95% of its running
peak, and halves it again after 3 consecutive losses (floor 0.25). 95% / 3 /
0.5 are conventional risk-of-ruin brakes fixed a priori; no backtest was
searched to choose them and none may be — tuning them on this repo's data
would turn a convention into an unregistered parameter search. Sizing cannot
change per-trade % expectancy; it only reshapes the equity path.

The overlay NARROWS exposure, it never widens the champion's permission set:
the pre-trade risk checks are evaluated against the FULL unscaled size, and
the factor is applied only to an already-approved order (bot/main.py
`_try_order`). A size the champion would have been refused is never retried
smaller.

The overlay's own state (consecutive losses, relative drawdown) is persisted by
`OverlayState` so a process restart cannot reset the brake — the same reason
the kill switch persists.

The overlay's counters are the OVERLAY'S OWN and are deliberately kept out of
`Portfolio`. The portfolio's `consecutive_losses` / `equity_peak_jpy` feed the
HARD risk checks in bot/risk/pre_trade_checks.py, which trip the kill switch;
they are process-local facts about trades this process actually made and must
stay that way. Writing persisted overlay numbers into them would make a
restart trip the kill switch on history it did not live through — and after an
operator reset, trip it again on the very next boot (an unresettable deadlock).
The overlay reads its own state; the risk checks read the portfolio's.

data/overlay_state.json
-----------------------
The persisted brake. Two fields:

* `consecutive_losses` — losing closes in a row, as counted by the overlay.
* `dd_frac` — equity / running-peak equity at the moment of the write (<= 1.0),
  i.e. the RELATIVE drawdown. The absolute peak is deliberately NOT stored:
  restoring an absolute JPY peak against a different boot equity (a changed
  `paper_equity_jpy`, a different account) would manufacture a drawdown that
  never happened. On boot the peak is reconstructed as
  `boot_equity / dd_frac`, which preserves the relative drawdown exactly and
  degrades to "no drawdown" when the file is missing.

Written after every closed trade. Deleting it clears the SIZING brake only —
it never unblocks trading (that is the kill switch) and it is never required
for the bot to start: a missing or unreadable file degrades to the safe
defaults (no drawdown, zero losses). Delete it when the account is
re-baselined (paper equity reset, fresh account) and the accumulated brake no
longer describes anything real. Operator steps: docs/OPERATIONS.md §3.

The overlay applies to NEW exposure only. Closing/exit orders are never
scaled and never blocked, the same invariant `increases_exposure` enforces in
bot/risk/pre_trade_checks.py: a position opened at a cap must stay exitable.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from fnmatch import fnmatchcase
from pathlib import Path

import pandas as pd
import yaml

from bot.strategy.base import Signal, SignalType, Strategy
from bot.strategy.xborder_momentum import XborderMomentumStrategy

CORE_PARAM_KEYS = ("k", "thr_pct", "exit_pct")

# Anchored to the repo, not to the process cwd: a bot started from anywhere
# must read the same gates and the same core params as the tests do.
REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG_PATH = REPO_ROOT / "config" / "composite.yaml"

# gate_evidence must name a report that actually exists in the repo.
EVIDENCE_DIR = REPO_ROOT / "docs"
EVIDENCE_PATTERN = "RESEARCH_REPORT_*.md"

# Risk-overlay conventions (see module docstring — fixed a priori, not fitted)
DRAWDOWN_TRIGGER = 0.95      # scale down while equity < 95% of running peak
LOSS_STREAK_TRIGGER = 3      # scale down after this many losses in a row
SCALE_STEP = 0.5             # each trigger halves new exposure
MIN_SIZE_FACTOR = 0.25       # floor, however many triggers are active

OVERLAY_STATE_PATH = Path("data") / "overlay_state.json"


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
    it. An ENABLED module must carry judged evidence AND a real `veto_entry`
    implementation — both are checked here, at construction, so there is no
    code path in which an unbuilt module gets asked about a live trade.
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
        if self.gate_evidence:
            _check_evidence(self.name, self.gate, self.gate_evidence)
        if self.enabled and type(self).veto_entry is CompositeModule.veto_entry:
            # Fail closed at construction: an enabled module with no rule would
            # otherwise raise (or worse, be skipped) in the middle of a decision.
            raise ModuleGateError(
                f"module '{self.name}' is enabled but has no veto_entry "
                f"implementation. Gate: {self.gate}. Build and register the "
                "rule before enabling; config alone cannot switch it on."
            )

    # ---- hooks (entry side only; exits are never consulted) ---------------
    def veto_entry(self, signal: Signal, context: ModuleContext) -> bool:
        """True = refuse this NEW entry. Never called for a close.

        The base implementation is a stub and is never reached: an enabled
        module that has not overridden it fails to construct (see __init__).
        """
        raise NotImplementedError(
            f"module '{self.name}' has no veto rule yet; gate: {self.gate}")

    def describe(self) -> dict:
        return {"name": self.name, "enabled": self.enabled, "gate": self.gate,
                "gate_evidence": self.gate_evidence}


def _check_evidence(name: str, gate: str, evidence: str) -> None:
    """gate_evidence must be the BARE FILENAME of an existing report in docs/.

    Free text ("passed", "see chat") is refused: the unlock reference has to
    be a report that can be read and audited afterwards. Any path separator or
    `..` is refused too — taking the basename of a path would have let
    `../../elsewhere/RESEARCH_REPORT_x.md` (or a same-named file dropped into
    another directory) read as a docs/ report. The match is case-SENSITIVE
    (fnmatchcase): on Windows `fnmatch` would accept `research_report_x.MD`
    for a file the repo does not have under that name.
    """
    if any(sep in evidence for sep in ("/", "\\", os.sep)) or ".." in evidence:
        raise ModuleGateError(
            f"module '{name}' gate_evidence {evidence!r} must be a bare "
            f"filename under docs/ (no path separators, no '..'). Gate: {gate}."
        )
    if not fnmatchcase(evidence, EVIDENCE_PATTERN):
        raise ModuleGateError(
            f"module '{name}' gate_evidence {evidence!r} is not a "
            f"docs/{EVIDENCE_PATTERN} reference. Gate: {gate}."
        )
    if not (EVIDENCE_DIR / evidence).exists():
        raise ModuleGateError(
            f"module '{name}' gate_evidence {evidence!r} names a report that "
            f"does not exist under {EVIDENCE_DIR}. Gate: {gate}."
        )


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
    """Would veto entries by open-interest condition.

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

    Fail-closed: an unknown module name is an error; a configured module that
    omits `gate` is an error (the criterion must be spelled out where it is
    being configured, not inherited silently); a `gate` text that does not
    match the one pre-registered in code is an error (the gate cannot be
    weakened by editing YAML); enabled-without-judged-evidence and
    enabled-without-implementation raise in CompositeModule.__init__.

    A module absent from the config entirely is simply built disabled.
    """
    raw = dict(raw or {})
    unknown = sorted(set(raw) - set(MODULE_CLASSES))
    if unknown:
        raise ValueError(f"unknown composite module(s): {unknown}; "
                         f"known: {sorted(MODULE_CLASSES)}")
    modules = []
    for name, cls in MODULE_CLASSES.items():
        configured = name in raw
        cfg = dict(raw.get(name) or {})
        if configured and "gate" not in cfg:
            raise ModuleGateError(
                f"module '{name}' is configured without a 'gate' key. The "
                f"pre-registered gate must be stated in config: {cls.GATE!r}"
            )
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
    modules off — the safe state); a path given explicitly must exist.

    The default path is absolute (repo-anchored), so this fallback is reached
    only when the file has genuinely been removed from the repo — not merely
    because the process was started from another directory. Selecting
    `strategy.name: composite` while the file is missing is refused at startup
    by bot/main.py, and CompositeStrategy itself refuses to construct without
    core params, so this fallback can never be how the live bot ends up running
    an unconfigured composite.
    """
    explicit = path is not None
    path = Path(path) if explicit else DEFAULT_CONFIG_PATH
    if not path.exists():
        if explicit:
            raise FileNotFoundError(f"composite config not found: {path}")
        return {}
    with open(path, encoding="utf-8") as f:   # cp932 default on Windows breaks UTF-8
        return yaml.safe_load(f) or {}


@dataclass
class OverlayState:
    """Risk-overlay brake state; persisted so it survives a restart.

    A crash-and-restart in the middle of a losing streak would otherwise hand
    the bot a clean slate and full size — exactly the moment sizing should be
    smallest. Written on every closed trade, reloaded on boot.

    On disk it is `consecutive_losses` + `dd_frac` (equity / peak at the time
    of the write). The RELATIVE drawdown is what carries over; the absolute
    peak does not, because it is only meaningful against the equity it was
    measured on. See the module docstring for why.

    In memory the same state is carried as the reconstructed absolute peak
    (`equity_peak_jpy`) alongside the last known equity, because that is the
    form `CompositeStrategy.size_factor` takes.

    A missing or unreadable file degrades to safe defaults (no drawdown, zero
    losses) rather than crashing: this is a brake, not an authorisation, so
    losing it must not stop the bot from running.
    """

    consecutive_losses: int = 0
    equity_peak_jpy: float = 0.0
    equity_jpy: float = 0.0

    @property
    def dd_frac(self) -> float:
        """Equity as a fraction of the running peak, clamped to (0, 1]."""
        if self.equity_peak_jpy <= 0 or self.equity_jpy <= 0:
            return 1.0
        return min(1.0, self.equity_jpy / self.equity_peak_jpy)

    def on_closed_trade(self, realized_pnl_jpy: float, equity_jpy: float) -> None:
        """Fold one closed trade into the brake (the overlay's own counters).

        Mirrors Portfolio's streak rule — a loss increments, a win resets, a
        flat close does neither — but on state of its own, because the
        portfolio's counter feeds the kill-switch checks (module docstring).
        """
        if realized_pnl_jpy < 0:
            self.consecutive_losses += 1
        elif realized_pnl_jpy > 0:
            self.consecutive_losses = 0
        self.equity_jpy = float(equity_jpy)
        self.equity_peak_jpy = max(self.equity_peak_jpy, self.equity_jpy)

    @classmethod
    def load(cls, path: str | Path = OVERLAY_STATE_PATH, *,
             boot_equity_jpy: float = 0.0) -> "OverlayState":
        """Rebuild the brake against THIS boot's equity.

        peak := boot_equity / dd_frac, so a saved 10% drawdown is still a 10%
        drawdown after a restart — whatever the account is now worth, and
        whatever `paper_equity_jpy` was changed to in between.
        """
        path = Path(path)
        boot = float(boot_equity_jpy)
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            losses = max(0, int(raw["consecutive_losses"]))
            dd_frac = float(raw["dd_frac"])
            if not 0.0 < dd_frac <= 1.0:
                raise ValueError(f"dd_frac out of range: {dd_frac}")
            return cls(consecutive_losses=losses,
                       equity_peak_jpy=boot / dd_frac, equity_jpy=boot)
        except (OSError, ValueError, TypeError, KeyError, ZeroDivisionError):
            return cls(consecutive_losses=0, equity_peak_jpy=boot, equity_jpy=boot)

    def save(self, path: str | Path = OVERLAY_STATE_PATH) -> None:
        """Best-effort atomic-ish write (same pattern as StatusWriter): a
        state write must never take down trading.

        On Windows os.replace fails with PermissionError while another process
        briefly holds the destination open; retry, then fall back to a direct
        write, and swallow any remaining OSError. A temp file left behind by a
        failed replace is cleaned up — otherwise every failure leaks one.
        """
        path = Path(path)
        payload = json.dumps({"consecutive_losses": int(self.consecutive_losses),
                              "dd_frac": self.dd_frac}, ensure_ascii=False)
        tmp = path.with_suffix(".tmp")
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(payload, encoding="utf-8")
            for _ in range(5):
                try:
                    os.replace(tmp, path)
                    return
                except PermissionError:
                    time.sleep(0.05)
            path.write_text(payload, encoding="utf-8")
        except OSError:
            pass
        finally:
            try:
                if tmp.exists():
                    tmp.unlink()
            except OSError:
                pass


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
        if not core:
            # Fail closed rather than falling through to XborderMomentumStrategy's
            # own defaults: a composite silently trading k=10 because its config
            # went missing is a different strategy wearing the validated name.
            raise FileNotFoundError(
                "composite core params unavailable: no core params were given "
                f"and {DEFAULT_CONFIG_PATH} supplied none (missing or empty "
                "'core:'). Restore the file or pass k/thr_pct/exit_pct."
            )
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

    def gate_entry(self, signal: Signal, context: ModuleContext) -> Signal:
        """Run enabled modules against a signal that would OPEN exposure.

        Returns the signal unchanged, or HOLD when a module vetoes. CLOSE,
        HOLD and any signal that reduces an existing position are returned
        untouched — a module can never block an exit. With no enabled module
        this is the identity function and touches nothing (E0 equivalence).

        `context` is required: the position is what separates an entry from an
        exit, and defaulting it would silently treat every close as an entry.
        """
        if not self._active:
            return signal
        if signal.type not in (SignalType.BUY, SignalType.SELL):
            return signal
        pos = context.position_size
        closing = (signal.type is SignalType.BUY and pos < 0) or \
                  (signal.type is SignalType.SELL and pos > 0)
        if closing:
            return signal
        for module in self._active:
            if module.veto_entry(signal, context):
                return Signal(SignalType.HOLD,
                              f"entry vetoed by module {module.name}",
                              dict(signal.indicators))
        return signal

    @staticmethod
    def size_factor(equity_peak: float, equity_now: float,
                    consecutive_losses: int) -> float:
        """Size multiplier for NEW exposure only (see module docstring).

        1.0 normally; x0.5 while equity is below 95% of its running peak;
        x0.5 after 3+ consecutive losses (`OverlayState`'s counter, which
        resets on a win); factors multiply, floored at 0.25. Never applied to a
        closing order — the caller must not consult this when reducing
        exposure, and never before the full-size risk checks have approved the
        order.
        """
        factor = 1.0
        if equity_peak > 0 and equity_now < DRAWDOWN_TRIGGER * equity_peak:
            factor *= SCALE_STEP
        if consecutive_losses >= LOSS_STREAK_TRIGGER:
            factor *= SCALE_STEP
        return max(factor, MIN_SIZE_FACTOR)
