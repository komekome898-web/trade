"""Purge, embargo and combinatorial purged cross-validation (item 3, old
item 7: 「purge と embargo つきの walk-forward と CPCV」).

Rows are observations whose LABEL spans [time_i, label_end_i] (the label of
a row at time t is decided by data up to label_end). Training on a row whose
label interval overlaps a test window leaks the test outcome into training;
the rule below removes exactly those rows (Lopez de Prado, AFML ch. 7, the
PurgedKFold form), per maximal run ("block") of consecutive test rows:

  left   a row i before the block is dropped when label_end_i > time of the
         block's first row (its label reaches into the block);
  right  let e0 = the largest label end in the block and f = the first row
         AFTER the block whose time >= e0 ("free"; when the labels end at
         the block's last row, f is the next row, so the embargo still
         starts right after the block). Rows after the block and before f
         start inside the block's labels and are dropped (purge);
  embargo  from f on, `embargo_rows` rows, or the rows with time in
         [time_f, time_f + embargo_ns), are dropped too.

Exactly one embargo form must be given (0 is allowed and means none).

    purged_train(times, label_end, test_idx, embargo_rows=|embargo_ns=) -> Purged
    cpcv(times, label_end, n_groups=, n_test_groups=, embargo_rows=|embargo_ns=) -> CPCV
"""
from __future__ import annotations

import itertools
import math
from dataclasses import dataclass
from typing import Optional, Sequence

from ._args import as_int, as_times
from .errors import ValidationError


@dataclass(frozen=True)
class Purged:
    train: tuple[int, ...]
    test: tuple[int, ...]
    purged: tuple[int, ...]  # dropped by the left / right rule
    embargoed: tuple[int, ...]  # dropped by the embargo only


def _labels(times: Sequence[int], label_end: Sequence[int]) -> tuple[list[int], list[int]]:
    t = as_times("times", times)
    le = [as_int(f"label_end[{i}]", x) for i, x in enumerate(label_end)]
    if len(le) != len(t):
        raise ValidationError(f"label_end has {len(le)} values for {len(t)} rows")
    for i in range(len(t)):
        if le[i] < t[i]:
            raise ValidationError(f"label_end[{i}] = {le[i]} is before its row time {t[i]}")
    return t, le


def _embargo(embargo_rows: Optional[int], embargo_ns: Optional[int]) -> tuple[str, int]:
    if (embargo_rows is None) == (embargo_ns is None):
        raise ValidationError("give exactly one of embargo_rows / embargo_ns (0 for no embargo)")
    if embargo_rows is not None:
        return "rows", as_int("embargo_rows", embargo_rows, lo=0)
    return "ns", as_int("embargo_ns", embargo_ns, lo=0)


def _blocks(test: Sequence[int]) -> list[list[int]]:
    out: list[list[int]] = []
    for i in test:
        if out and i == out[-1][-1] + 1:
            out[-1].append(i)
        else:
            out.append([i])
    return out


def _purge(t: list[int], le: list[int], test: Sequence[int], emb: tuple[str, int]) -> Purged:
    n = len(t)
    test_set = set(test)
    purged: set[int] = set()
    embargoed: set[int] = set()
    for blk in _blocks(sorted(test_set)):
        a, b = blk[0], blk[-1]
        s0 = t[a]
        e0 = max(le[i] for i in blk)
        for i in range(a):
            if le[i] > s0:
                purged.add(i)
        f = next((i for i in range(b + 1, n) if t[i] >= e0), n)
        purged.update(range(b + 1, f))
        if f < n:
            if emb[0] == "rows":
                embargoed.update(range(f, min(n, f + emb[1])))
            else:
                embargoed.update(i for i in range(f, n) if t[i] < t[f] + emb[1])
    purged -= test_set
    embargoed -= test_set | purged
    train = tuple(i for i in range(n) if i not in test_set and i not in purged and i not in embargoed)
    return Purged(train, tuple(sorted(test_set)), tuple(sorted(purged)), tuple(sorted(embargoed)))


def purged_train(times: Sequence[int], label_end: Sequence[int], test_idx: Sequence[int], *,
                 embargo_rows: Optional[int] = None, embargo_ns: Optional[int] = None) -> Purged:
    t, le = _labels(times, label_end)
    idx = [as_int(f"test_idx[{k}]", i, lo=0, hi=len(t) - 1) for k, i in enumerate(test_idx)]
    if not idx:
        raise ValidationError("test_idx is empty")
    if len(set(idx)) != len(idx):
        raise ValidationError("test_idx has repeated rows")
    return _purge(t, le, idx, _embargo(embargo_rows, embargo_ns))


def group_bounds(n: int, n_groups: int) -> list[range]:
    """Contiguous groups of rows in time order: the first n % n_groups groups
    have one row more (numpy.array_split's layout)."""
    q, r = divmod(n, n_groups)
    out, s = [], 0
    for g in range(n_groups):
        e = s + q + (1 if g < r else 0)
        out.append(range(s, e))
        s = e
    return out


@dataclass(frozen=True)
class CPCVSplit:
    test_groups: tuple[int, ...]
    purged: Purged


@dataclass(frozen=True)
class CPCV:
    n_groups: int
    n_test_groups: int
    groups: tuple[range, ...]
    splits: tuple[CPCVSplit, ...]  # every combination of test groups, lexicographic

    @property
    def n_splits(self) -> int:
        return len(self.splits)

    @property
    def n_paths(self) -> int:
        return self.n_splits * self.n_test_groups // self.n_groups

    def split_for(self, test_groups: Sequence[int]) -> CPCVSplit:
        key = tuple(sorted(test_groups))
        for s in self.splits:
            if s.test_groups == key:
                return s
        raise ValidationError(f"no split has test groups {key} (n_groups {self.n_groups}, "
                              f"n_test_groups {self.n_test_groups})")

    def paths(self) -> list[list[tuple[tuple[int, ...], int]]]:
        """n_paths backtest paths. Path p takes, for every group g, the p-th
        split (in lexicographic order) that tests g; each (split, group) pair
        appears in exactly one path, and each path tests every group once."""
        per_group = {g: [s.test_groups for s in self.splits if g in s.test_groups] for g in range(self.n_groups)}
        return [[(per_group[g][p], g) for g in range(self.n_groups)] for p in range(self.n_paths)]


def cpcv(times: Sequence[int], label_end: Sequence[int], *, n_groups: int, n_test_groups: int,
         embargo_rows: Optional[int] = None, embargo_ns: Optional[int] = None) -> CPCV:
    t, le = _labels(times, label_end)
    N = as_int("n_groups", n_groups, lo=2)
    k = as_int("n_test_groups", n_test_groups, lo=1, hi=N - 1)
    if len(t) < N:
        raise ValidationError(f"{len(t)} rows cannot make {N} non-empty groups")
    emb = _embargo(embargo_rows, embargo_ns)
    groups = group_bounds(len(t), N)
    splits = []
    for comb in itertools.combinations(range(N), k):
        test = [i for g in comb for i in groups[g]]
        splits.append(CPCVSplit(comb, _purge(t, le, test, emb)))
    assert len(splits) == math.comb(N, k)
    return CPCV(N, k, tuple(groups), tuple(splits))
