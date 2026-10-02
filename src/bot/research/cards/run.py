"""Running one card over one instrument's bars (W1 spec C2), through the
core's event flow.

    run = run_card(card, bars, references={name: ReferenceSeries, ...}, venue=..., symbol=...)

The card is called inside `bot.bt.core.Strategy.on_event`, so the core's
rules hold for it (an event reaches the strategy at its received time; a
read of the history after now raises `LookAheadError`; a context kept past
its callback raises `StaleContextError`). Streams handed to `CoreEngine`:
"bars" (the instrument's bars) and "ref:<name>" per reference series (the
data layer's events, delivered at available_at, bot.bt.data.reference).

When the card is called: at the end t of every bar that is not empty
(volume > 0). The call is made from a timer the strategy sets for t when the
bar is delivered: the core delivers timers after every input event of the
same instant (ordering.py, phase 4), so every reference row whose
available_at is <= t has been delivered when the card runs, whatever the
merge order of the event types (a lag-0 row stamped at a bar's close merges
after the bar). An empty bar (volume 0) present in the input is delivered
(the card sees it in `bars`) but no exposure is taken at it: an exposure at
an empty bar would be filled at the same open as the one taken at the
non-empty bar before it (spec C2: the fill skips empty bars), so it is not
a decision of its own. Missing bars (the data layer drops no-trade rows) are
simply absent.

What is recorded per bar: whether the card was called, its exposure, and,
per reference series, the newest row available at t (time and value) -- the
same rows the card could read, used later as scene variables. The profit
and loss is computed afterwards from the record (pnl.py); the spec allows
that ("持ち高の系列を記録したあとの損益の計算は、まとめて行ってよい").

Bars: `BarEvent`s with `start_time_ns` (the open), whose received time is
their close (a bar received later than its close is outside W1 and refused),
strictly increasing closes, and no overlap (start >= the previous close).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Optional, Sequence

import numpy as np

from bot.bt.core import BarEvent, CoreEngine, EventType, Strategy
from bot.bt.data.reference import ReferenceSeries, parse_decl, reference_value

from .card import Card, CardError, CardView, SeriesSpec, check_exposure

BARS_STREAM = "bars"
REF_PREFIX = "ref:"
_TAG = "card"


@dataclass(frozen=True)
class CardRun:
    """The record of one run. Arrays are per bar of the input, in order."""
    card: str
    venue: str
    symbol: str
    start_ns: np.ndarray  # int64, bar open
    end_ns: np.ndarray  # int64, bar close = decision time t
    open: np.ndarray
    high: np.ndarray
    low: np.ndarray
    close: np.ndarray
    volume: np.ndarray
    decided: np.ndarray  # bool: the card was called at this bar's end
    exposure: np.ndarray  # float, NaN where not decided
    ref_time: dict = field(default_factory=dict)  # name -> int64 array: newest available row's time (-1: none yet)
    ref_value: dict = field(default_factory=dict)  # name -> float array (NaN: none yet)
    ref_lag_ns: dict = field(default_factory=dict)  # name -> lag ns, or None (per-row available_at)
    ref_decl: dict = field(default_factory=dict)  # name -> the declaration (plain dict) the run was checked against
    delivery_digest: str = ""


class _CardStrategy(Strategy):
    def __init__(self, card: Card, bars: Sequence[BarEvent], lags: Mapping[str, int], allowed: frozenset) -> None:
        self._card = card
        self._n = len(bars)
        self._ends = [int(b.exchange_time_ns) for b in bars]
        self._nonempty = [b.volume > 0 for b in bars]
        self._next_bar = 0
        self._allowed = allowed
        self._refs = {name: ([], [], lag) for name, lag in lags.items()}
        self.exposure = np.full(self._n, np.nan)
        self.decided = np.zeros(self._n, dtype=bool)
        self.ref_time = {name: np.full(self._n, -1, dtype=np.int64) for name in lags}
        self.ref_value = {name: np.full(self._n, np.nan) for name in lags}

    def on_event(self, event, ctx) -> None:
        et = event.EVENT_TYPE
        if et is EventType.BAR:
            if event.stream != BARS_STREAM:  # pragma: no cover - only one bar stream is handed over
                raise CardError(f"unexpected bar stream {event.stream!r}")
            i = self._next_bar
            if i >= self._n or int(event.exchange_time_ns) != self._ends[i]:
                raise CardError(f"bar delivered out of order at {event.exchange_time_ns}")  # pragma: no cover
            self._next_bar += 1
            if self._nonempty[i]:
                ctx.set_timer(ctx.now_ns, f"{_TAG}{i}")
            return
        if et is EventType.CLOCK:
            if event.stream.startswith(REF_PREFIX):
                times, values, _lag = self._refs[event.stream[len(REF_PREFIX):]]
                times.append(int(event.exchange_time_ns))
                values.append(reference_value(event))
                return
            if event.stream == "" and event.tag.startswith(_TAG):
                self._decide(int(event.tag[len(_TAG):]), ctx)
                return
        raise CardError(f"unexpected event {et.value} from stream {event.stream!r}")  # pragma: no cover

    def _decide(self, i: int, ctx) -> None:
        t = self._ends[i]
        if ctx.now_ns != t:  # pragma: no cover - the timer is set for t
            raise CardError(f"decision for bar {i} called at {ctx.now_ns}, not at its end {t}")
        view = CardView(ctx, t, self._refs, self._allowed)
        try:
            x = self._card.exposure(view)
        finally:
            view._kill()
        self.exposure[i] = check_exposure(x, self._card.name, t)
        self.decided[i] = True
        for name, (times, values, _lag) in self._refs.items():
            if times:
                self.ref_time[name][i] = times[-1]
                self.ref_value[name][i] = values[-1]


def _check_bars(bars: Sequence[BarEvent]) -> None:
    if len(bars) < 1:
        raise CardError("a run needs at least one bar")
    prev_end = None
    for k, b in enumerate(bars):
        if type(b) is not BarEvent:
            raise CardError(f"bars[{k}] is a {type(b).__name__}, not a BarEvent")
        if b.start_time_ns is None:
            raise CardError(f"bars[{k}] has no start_time_ns (the open is needed for the fill)")
        if b.received_time_ns != b.exchange_time_ns:
            raise CardError(f"bars[{k}] is received at {b.received_time_ns}, after its close {b.exchange_time_ns}; "
                            f"a bar received later than its close is outside W1")
        if prev_end is not None:
            if b.exchange_time_ns <= prev_end:
                raise CardError(f"bars[{k}] closes at {b.exchange_time_ns}, not after the previous close {prev_end}")
            if b.start_time_ns < prev_end:
                raise CardError(f"bars[{k}] opens at {b.start_time_ns}, before the previous close {prev_end}")
        prev_end = b.exchange_time_ns


def check_declared(refs: Mapping[str, ReferenceSeries], declarations: Mapping) -> None:
    """Every reference series a run receives -- those the card reads and those
    used only as scenes -- must carry exactly the declaration the run was
    given for its name (bot.bt.data.reference): a series built with another
    lag (0 where the publication takes 3 days, say) is refused."""
    if not isinstance(declarations, Mapping):
        raise CardError("declarations must be a mapping of series name -> declaration")
    for name, s in refs.items():
        if type(s) is not ReferenceSeries or s.name != name:
            raise CardError(f"references[{name!r}] must be the ReferenceSeries named {name!r} (bot.bt.data.reference)")
        if name not in declarations:
            raise CardError(f"reference {name!r} has no declaration in this run's declarations")
        want = parse_decl(name, declarations[name])
        if s.decl != want:
            raise CardError(f"reference {name!r} was made with {s.decl.as_dict()}, but this run declares "
                            f"{want.as_dict()}")


def run_card(card: Card, bars: Sequence[BarEvent], *, references: Optional[Mapping[str, ReferenceSeries]] = None,
             declarations: Mapping, venue: str, symbol: str) -> CardRun:
    """Run `card` over `bars` (one instrument), with the reference series it
    requires and any others the measurement uses as scenes (all are
    recorded per bar). `declarations` (name -> declaration, the card's
    measurement settings) is checked against every series received."""
    if not isinstance(card, Card):
        raise CardError(f"{card!r} does not have the card mouth (name, requires, exposure)")
    if type(card.name) is not str or not card.name:
        raise CardError("card.name must be a non-empty str")
    for v, what in ((venue, "venue"), (symbol, "symbol")):
        if type(v) is not str or not v:
            raise CardError(f"{what} must be a non-empty str")
    bars = list(bars)
    _check_bars(bars)
    refs = dict(references or {})
    check_declared(refs, declarations)
    names = []
    for spec in card.requires:
        if type(spec) is not SeriesSpec:
            raise CardError(f"card {card.name!r}: requires must list SeriesSpec, got {type(spec).__name__}")
        if spec.name in names:
            raise CardError(f"card {card.name!r} lists {spec.name!r} twice in requires")
        names.append(spec.name)
        if spec.name not in refs:
            raise CardError(f"card {card.name!r} requires reference {spec.name!r}, which the run was not given")
        if refs[spec.name].lag_ns != spec.lag_ns:
            raise CardError(f"card {card.name!r} states lag {spec.lag_ns} for {spec.name!r}, but the series is "
                            f"declared with lag {refs[spec.name].lag_ns} (None: per-row available_at)")
    allowed = frozenset(s.name for s in card.requires)
    lags = {name: s.lag_ns for name, s in refs.items()}
    strategy = _CardStrategy(card, bars, lags, allowed)
    streams = {BARS_STREAM: iter(bars)}
    times = [int(bars[0].exchange_time_ns), int(bars[-1].exchange_time_ns)]
    for name, s in refs.items():
        streams[REF_PREFIX + name] = s.events()
        if len(s):
            times += [s.times_ns[0], s.available_at(len(s) - 1)]
    result = CoreEngine(strategy, streams, time_span_ns=(min(times), max(times))).run()
    n_called = int(strategy.decided.sum())
    n_nonempty = sum(1 for b in bars if b.volume > 0)
    if n_called != n_nonempty:  # pragma: no cover - every non-empty bar sets a timer that fires
        raise CardError(f"the card was called {n_called} times for {n_nonempty} non-empty bars")
    f = np.array
    return CardRun(
        card=card.name, venue=venue, symbol=symbol,
        start_ns=f([b.start_time_ns for b in bars], dtype=np.int64),
        end_ns=f([b.exchange_time_ns for b in bars], dtype=np.int64),
        open=f([b.open for b in bars], dtype=float), high=f([b.high for b in bars], dtype=float),
        low=f([b.low for b in bars], dtype=float), close=f([b.close for b in bars], dtype=float),
        volume=f([b.volume for b in bars], dtype=float),
        decided=strategy.decided, exposure=strategy.exposure,
        ref_time=strategy.ref_time, ref_value=strategy.ref_value, ref_lag_ns=lags,
        ref_decl={name: s.decl.as_dict() for name, s in refs.items()},
        delivery_digest=result.delivery_digest,
    )


__all__ = ["BARS_STREAM", "CardRun", "REF_PREFIX", "run_card"]
