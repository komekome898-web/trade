"""Backtest engine.

Since item 4 of the backtest-environment work (finishing condition 3,
2026-09-26) this module holds no engine of its own: every name below is the
compatibility mouth `bot.bt.compat` (the new engine's bar model on the core,
rule set "legacy"), through the layer `run_backtest_as_old` that gives the
old numbers for the inputs the core does not take (a malformed row, a
CostModel subclass with its own price or fee method). The names, the
arguments, the defaults and the promises below are the old module's and are
kept; the old implementation is kept, with its sha256, under
docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/round_3/materials/replace/
old_engine_snapshot/, and tests/bt/compat/ holds the proofs (the golden
file, the old tests, the grid against the snapshot).

Anti-look-ahead design:
- The strategy at bar i sees candles[0..i] only (an expanding slice).
- Taker execution: a signal at bar i executes at bar i+1's OPEN with
  spread + slippage + taker fee applied.
- Maker execution: a signal at bar i places a limit at bar i's CLOSE; it fills
  only when a LATER bar trades strictly through the limit (low < limit for BUY,
  high > limit for SELL), paying the maker fee only. Unfilled orders cancel
  after `maker_timeout_bars` and are counted as missed fills. Touching the
  level is not enough — a conservative fill model.

Position model: one net position at a time. BUY closes a short or opens a
long; SELL closes a long or opens a short (shorts only when allow_short, for
margin products such as FX_BTC_JPY). Margin carry cost accrues per bar via
`swap_daily_pct` and is charged against the open trade's PnL.

Time exit: `max_hold_bars` caps how long a position may stay open. A position
filled at bar b is force-closed at the OPEN of bar b + max_hold_bars — i.e.
after exactly max_hold_bars bars of holding — with taker costs, whatever the
strategy says. The forced close overrides any pending signal on that bar. An
intrabar stop/take-profit on an EARLIER bar naturally fires first; on the same
bar the stop is checked first (conservative).

Trade log: every CLOSE_* entry carries a "reason" in
{"signal", "stop_loss", "take_profit", "time_exit", "maker_tp", "wick_stop"} so
callers can break down how trades actually ended (exit-structure audits).
Additive field only — existing consumers keying off "bar"/"side"/"price"/"pnl"
are unaffected.

Additive options (all default to the historical behaviour; existing callers get
bit-identical results):

``exit_execution="maker_tp"`` + ``maker_tp_pct``
    Rests a maker take-profit limit at ``maker_tp_pct`` away from the entry
    price for the life of the position, while the strategy's own signal exit
    and the protective ``stop_loss_pct`` stay as taker fallbacks. The limit
    fills under the SAME conservative traded-through rule the maker entry
    path uses: the bar must trade strictly THROUGH the level
    (``high > level`` for a long TP, ``low < level`` for a short TP); merely
    touching it is not a fill. The fill is booked at the level itself with
    ``maker_fee`` and no spread/slippage, and is only ever checked on bars
    STRICTLY AFTER the entry bar, so there is no look-ahead.

    1m-bar approximation (optimistic, stated for the record): on a 1-minute
    bar we only know that the level traded through somewhere inside the
    minute, not that our specific resting order was reached in the queue, nor
    whether the stop level was touched EARLIER in the same minute. When the
    stop and the maker TP are both inside one bar's range the STOP is taken
    first (conservative), but within a single bar the true sequencing is
    unknown. Real fills also depend on queue position; this model grants the
    fill on any strict through-trade. Treat maker-TP results as an upper
    bound, not a promise.

``stop_mode="wick_invalidation"`` + ``stop_window_bars``
    Replaces the fixed-percentage protective stop with a STRUCTURAL one: the
    invalidation level is the extreme of the trailing ``stop_window_bars``
    COMPLETED bars' wicks as of the fill — ``min(low)`` over bars
    ``[b - N, b - 1]`` for a long, ``max(high)`` over the same bars for a
    short, where ``b`` is the fill bar. Bar ``b`` itself is excluded (its own
    range is not yet known when the position fills at its open), so under the
    taker path the window ends exactly on the SIGNAL bar — the bar whose wick
    the legacy bot froze.

    The level is FROZEN at entry and never trails. It is breached only by a
    CLOSE beyond it (``close < level`` long, ``close > level`` short); a wick
    poking through is explicitly not an exit, which is the whole point of the
    construction. A breach detected at bar ``i``'s close is executed at bar
    ``i + 1``'s OPEN with taker costs — the same next-bar-open causality the
    signal path uses — and is logged with ``reason="wick_stop"``. It overrides
    any pending signal for that bar and is checked BEFORE the intrabar
    stop/take-profit block, because it rests on strictly older information
    (the previous bar's close) than that bar's high/low.

    Requires ``stop_loss_pct=None``: the two protective stops are alternatives,
    never a stack.

``entry_mask`` / ``entry_sides``
    Restrict which decisions may OPEN a position; closes are never blocked.
    ``entry_mask`` is a per-bar boolean aligned to ``candles`` and is
    evaluated at the DECISION bar (the bar whose information produced the
    signal), not at the fill bar. ``entry_sides`` is one of
    ``"both"`` / ``"long"`` / ``"short"``. Both are entry-side filters only:
    an open position still exits by signal, stop, take-profit, maker TP and
    time exit exactly as before.
"""
from __future__ import annotations

from bot.backtest.metrics import Metrics, compute_metrics  # noqa: F401  (the old module imported these)
from bot.bt.compat.engine import BacktestResult, CostModel  # noqa: F401
from bot.bt.compat.engine import _PendingLimit  # noqa: F401  (a private name of the old module)
from bot.bt.compat.engine import run_backtest_as_old as run_backtest  # noqa: F401
from bot.strategy.base import SignalType, Strategy  # noqa: F401  (the old module imported these)

__all__ = ["BacktestResult", "CostModel", "run_backtest"]
