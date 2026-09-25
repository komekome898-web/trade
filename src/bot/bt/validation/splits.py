"""Calendar splits and walk-forward (item 3, old item 7: 「暦日での Train / Val / OOS」、
「walk-forward」).

Days are CALENDAR days of a named time zone (IANA, `zoneinfo`): a day starts
at the first instant whose local date is that date (local midnight, or the
end of a DST gap when midnight does not exist there) and ends where the next
day starts, so a DST day is 23 or 25 hours long. Every part is a half-open
interval [start, end) of int64 UTC ns; a row belongs to the part whose
interval holds its time. Nothing is split by a fraction of the row count.

    calendar_split(times, tz=, train_end=, val_end=)      -> CalendarSplit
    walk_forward(times, tz=, train_days=, test_days=, step_days=, mode=,
                 label_end=None)                          -> list[Fold]
    walk_forward_eval(folds, columns, fit=, evaluate=)    -> list[FoldEval]

Rows must be in time order (non-decreasing); unsorted input is refused.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable, Mapping, Optional, Sequence
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from ._args import as_choice, as_int, as_times
from .errors import ValidationError

NS = 1_000_000_000
WF_MODES = ("rolling", "anchored")
_DATE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")


def zone(tz: Any) -> ZoneInfo:
    if type(tz) is not str or not tz:
        raise ValidationError(f"tz must be an IANA zone name (str), got {tz!r}")
    try:
        return ZoneInfo(tz)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValidationError(f"tz {tz!r} is not a known IANA zone: {exc}") from None


def parse_date(name: str, v: Any) -> date:
    m = _DATE.match(v) if type(v) is str else None
    if not m:
        raise ValidationError(f"{name} must be a calendar date 'YYYY-MM-DD', got {v!r}")
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError as exc:
        raise ValidationError(f"{name} {v!r}: {exc}") from None


def _local_date(sec: int, z: ZoneInfo) -> date:
    return datetime.fromtimestamp(sec, tz=timezone.utc).astimezone(z).date()


def day_start_ns(d: date, z: ZoneInfo) -> int:
    """The first instant (int ns UTC) whose local date in `z` is `d` or
    later (a date a zone skipped -- Pacific/Apia 2011-12-30 -- starts where
    the next one does). Found by a scan in 15-minute steps from 2 days
    before naive midnight (every UTC offset is within +-26 h, and zone
    transitions fall on quarter hours), then bisection on whole seconds
    inside the one step where the local date first reaches `d`; the scan
    makes the FIRST crossing the answer even where a DST fall-back re-enters
    the previous date."""
    naive = int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp())
    step = 900
    lo = naive - 2 * 86400
    if not _local_date(lo, z) < d:
        raise ValidationError(f"cannot place the start of {d} in {z.key}")
    hi = None
    for k in range(1, 4 * 86400 // step + 1):
        if _local_date(lo + k * step, z) >= d:
            lo, hi = lo + (k - 1) * step, lo + k * step
            break
    if hi is None:
        raise ValidationError(f"cannot place the start of {d} in {z.key}")
    while hi - lo > 1:  # invariant: local(lo) < d <= local(hi), within one step
        mid = (lo + hi) // 2
        if _local_date(mid, z) < d:
            lo = mid
        else:
            hi = mid
    return hi * NS


def local_date_of_ns(t_ns: int, z: ZoneInfo) -> date:
    return _local_date(t_ns // NS, z)  # floor: a time inside second s has the date of second s


@dataclass(frozen=True)
class Part:
    name: str
    start_ns: Optional[int]  # None = open (before the first row)
    end_ns: Optional[int]  # None = open (after the last row)
    idx: tuple[int, ...]

    @property
    def bounds(self) -> tuple[Optional[int], Optional[int]]:
        return (self.start_ns, self.end_ns)


@dataclass(frozen=True)
class CalendarSplit:
    tz: str
    train: Part
    val: Part
    oos: Part

    def parts(self) -> dict[str, Part]:
        return {"train": self.train, "val": self.val, "oos": self.oos}


def _select(times: Sequence[int], lo: Optional[int], hi: Optional[int]) -> tuple[int, ...]:
    return tuple(i for i, t in enumerate(times) if (lo is None or t >= lo) and (hi is None or t < hi))


def calendar_split(times: Sequence[int], *, tz: str, train_end: str, val_end: str) -> CalendarSplit:
    """Train = rows before the start of `train_end` (a date in `tz`), Val =
    rows from there to the start of `val_end`, OOS = the rest. Train and OOS
    are open towards the ends of the data; `train_end` < `val_end`."""
    t = as_times("times", times)
    z = zone(tz)
    a_d, b_d = parse_date("train_end", train_end), parse_date("val_end", val_end)
    if not a_d < b_d:
        raise ValidationError(f"train_end {train_end} must be before val_end {val_end}")
    a, b = day_start_ns(a_d, z), day_start_ns(b_d, z)
    return CalendarSplit(tz, Part("train", None, a, _select(t, None, a)), Part("val", a, b, _select(t, a, b)),
                         Part("oos", b, None, _select(t, b, None)))


@dataclass(frozen=True)
class Fold:
    k: int
    train: Part
    test: Part
    purged: tuple[int, ...] = ()  # train rows dropped because their label reaches the test window


def walk_forward(times: Sequence[int], *, tz: str, train_days: int, test_days: int, step_days: int, mode: str,
                 label_end: Optional[Sequence[int]] = None) -> list[Fold]:
    """Windows on calendar days of `tz`, anchored at the start of the first
    row's local date. Fold k: test = [D + k*step + train, D + k*step + train
    + test) days; train = [D + k*step, test start) ("rolling") or [D, test
    start) ("anchored"). A fold is made only when its whole test window ends
    at or before the end of the last row's local date (no partial window).
    `label_end` (optional, one int ns per row, >= the row's time): a train
    row whose label ends after the test start is purged (its label would
    overlap the test window). Rows after a test window are never trained on
    here, so no embargo applies (use `purge.cpcv` / `purge.purged_train`
    for folds with training data after the test)."""
    t = as_times("times", times)
    if not t:
        raise ValidationError("walk_forward needs at least one row")
    z = zone(tz)
    tr = as_int("train_days", train_days, lo=1)
    te = as_int("test_days", test_days, lo=1)
    st = as_int("step_days", step_days, lo=1)
    md = as_choice("mode", mode, WF_MODES)
    le = None
    if label_end is not None:
        le = [as_int(f"label_end[{i}]", x) for i, x in enumerate(label_end)]
        if len(le) != len(t):
            raise ValidationError(f"label_end has {len(le)} values for {len(t)} rows")
        bad = [i for i in range(len(t)) if le[i] < t[i]]
        if bad:
            raise ValidationError(f"label_end[{bad[0]}] ends before its row starts")
    d0 = local_date_of_ns(t[0], z)
    d_end = local_date_of_ns(t[-1], z) + timedelta(days=1)
    end_ns = day_start_ns(d_end, z)
    folds: list[Fold] = []
    k = 0
    while True:
        s_d = d0 + timedelta(days=k * st)
        ts_d = s_d + timedelta(days=tr)
        te_d = ts_d + timedelta(days=te)
        te_ns = day_start_ns(te_d, z)
        if te_ns > end_ns:
            break
        s_ns = day_start_ns(d0 if md == "anchored" else s_d, z)
        ts_ns = day_start_ns(ts_d, z)
        tr_idx = _select(t, s_ns, ts_ns)
        purged: tuple[int, ...] = ()
        if le is not None:
            purged = tuple(i for i in tr_idx if le[i] > ts_ns)
            tr_idx = tuple(i for i in tr_idx if le[i] <= ts_ns)
        folds.append(Fold(k, Part("train", s_ns, ts_ns, tr_idx), Part("test", ts_ns, te_ns, _select(t, ts_ns, te_ns)),
                          purged))
        k += 1
    return folds


@dataclass(frozen=True)
class FoldEval:
    k: int
    choice: Any
    score: Any


def _slice(columns: Mapping[str, Sequence[Any]], idx: Sequence[int]) -> dict[str, tuple]:
    return {name: tuple(col[i] for i in idx) for name, col in columns.items()}


def walk_forward_eval(folds: Sequence[Fold], columns: Mapping[str, Sequence[Any]], *,
                      fit: Callable[[dict], Any], evaluate: Callable[[Any, dict], Any]) -> list[FoldEval]:
    """For each fold: `choice = fit(train_columns)` sees ONLY the train rows
    of each column (a dict of tuples), then `score = evaluate(choice,
    test_columns)` sees only the test rows. Nothing of the test window
    reaches `fit` (the slices are built before it is called)."""
    if not isinstance(columns, Mapping) or not columns:
        raise ValidationError("columns must be a non-empty mapping name -> sequence")
    n = {len(v) for v in columns.values()}
    if len(n) != 1:
        raise ValidationError(f"columns have different lengths {sorted(n)}")
    size = n.pop()
    out = []
    for f in folds:
        if any(i >= size for i in f.train.idx + f.test.idx):
            raise ValidationError(f"fold {f.k} names rows beyond the columns' {size} rows")
        choice = fit(_slice(columns, f.train.idx))
        out.append(FoldEval(f.k, choice, evaluate(choice, _slice(columns, f.test.idx))))
    return out
