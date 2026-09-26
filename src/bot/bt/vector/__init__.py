"""Item 1 (old item 12): the vector shortcut for bar research, fixed by
tests to give the same bits as the event-driven path on the same bars.

  bars_from_trades(t_ns, px, qty, interval_s)   vector path      (bars.py)
  run_event_bars(trades, interval_s)            event path       (event_path.py)
  SmaLongFlat(...) / SmaCross(...).vector(close)  vector path  (rules.py)
  run_event_rule(bars, interval_s, rule)        event path       (event_path.py)
  run_vector_rule(bars, rule)                   the vector path on bar mappings
  bitwise_equal(a, b)                           the agreement the tests fix

Speed is measured and reported, not required as a number (the requirement
states none).
"""
from __future__ import annotations

import struct
from typing import Any, Iterable

from .bars import bars_from_trades, interval_ns
from .event_path import bar_events, run_event_bars, run_event_rule
from .rules import RULES, SmaCross, SmaLongFlat, equity_curve, rolling_mean, rule_from_mapping


def run_vector_rule(bars: Iterable[Any], rule: Any) -> dict:
    return rule.vector([b["close"] for b in bars])


def _bits(x: Any) -> Any:
    if type(x) is float:
        return struct.pack("<d", x).hex()
    if isinstance(x, (list, tuple)):
        return [_bits(v) for v in x]
    if isinstance(x, dict):
        return {k: _bits(v) for k, v in sorted(x.items())}
    return x


def bitwise_equal(a: Any, b: Any) -> bool:
    """True when both hold the same structure with the same float bits
    (0.0 and -0.0 differ; types matter)."""
    return _bits(a) == _bits(b) and type(a) is type(b)


__all__ = ["RULES", "SmaCross", "SmaLongFlat", "bar_events", "equity_curve", "rolling_mean", "bars_from_trades", "bitwise_equal",
           "interval_ns", "rule_from_mapping", "run_event_bars", "run_event_rule", "run_vector_rule"]
