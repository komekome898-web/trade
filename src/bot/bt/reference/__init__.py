"""Slow, independent reference implementation for item 4 (answer checking).

Written only from the item-4 row of the delegation and the fixed item-4
requirements file, without reading the new engine's core. Everything is
computed with exact rational arithmetic (fractions.Fraction) and plain loops;
speed is not a goal. See SPEC.md in this directory for every rule and for
which rules come from the requirement text and which are caller-selected
modes (required keyword arguments, no defaults).

Public entry points:
  - event_sim.Event / event_sim.simulate   (tick / book / funding events)
  - bar_sim.run_bars(bars, signals, options)   (bar backtest, written only
    from the scene book's bar rule text R-T..R-O; SPEC.md section 3)
"""
from bot.bt.reference.num import q, q_str  # noqa: F401
