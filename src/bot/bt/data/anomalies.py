"""The checks of the data layer: what is wrong with a dataset's rows, found
and reported, never repaired silently.

Kinds (each anomaly: {"kind", "t_ns", "row", "file", "line"}; `t_ns` is the
row's time -- a bar's start):

  duplicate        the row has the key of an earlier row and is the same row
                   (every declared field equal as normalised, every other
                   column equal as written)
  conflict         the row has the key of an earlier row and differs from it
  backward         the row's time is before the latest time of the earlier
                   rows OF THE SAME FILE (the files of one dataset are
                   generations / pieces; where they overlap, the key checks
                   and the generation checks speak)
  gap              (bars with session 24x7) a start on the interval grid,
                   from the first bar to the last, that no row has -- one per
                   missing start (t_ns = the missing start)
  off_grid         (bars with session 24x7) a bar whose start is not on the
                   grid anchored at the first bar
  generation_gap   (two or more files, with a key) a keyed row of one file
                   whose time lies inside another file's span, while that
                   other file has no row with its key: the generations
                   disagree on what exists
  unkeyed_overlap  (two or more files) a row without a key (no key declared,
                   or an empty id) inside another file's span: a repeat of it
                   there could not be told from a new row
  synthetic        (spec.synthetic declared) a row its flag column marks as
                   synthetic

A check that cannot run for a dataset (no key declared, no 24x7 session,
one file) does not run and is not listed in its `checks`.

Resolution (`resolve`): events are made only after every kind present has a
policy the caller named:

  duplicate        "drop"                       drop the repeats
  conflict         "keep_first" | "keep_last"   of each conflicting key, keep
                                                its first / last row
  backward         "drop" | "sort"              drop the late rows / sort by time
  gap              "accept"
  off_grid         "accept" | "drop"
  generation_gap   "accept"
  unkeyed_overlap  "accept"
  synthetic        "drop" | "accept"

After the policies, rows are ordered by time (a stable sort: rows of one
time keep their delivered order), which is the order the core's streams
require.
"""
from __future__ import annotations

from collections import Counter
from typing import Mapping, Optional

from .errors import SpecError, UnresolvedAnomalyError

KINDS = ("duplicate", "conflict", "backward", "gap", "off_grid", "generation_gap", "unkeyed_overlap", "synthetic")
POLICIES: dict[str, tuple[str, ...]] = {
    "duplicate": ("drop",),
    "conflict": ("keep_first", "keep_last"),
    "backward": ("drop", "sort"),
    "gap": ("accept",),
    "off_grid": ("accept", "drop"),
    "generation_gap": ("accept",),
    "unkeyed_overlap": ("accept",),
    "synthetic": ("drop", "accept"),
}


def _a(kind: str, t: int, idx: Optional[int], rows) -> dict:
    if idx is None:
        return {"kind": kind, "t_ns": t, "row": None, "file": None, "line": None}
    r = rows[idx]
    return {"kind": kind, "t_ns": t, "row": idx, "file": r.file_index, "line": r.line}


def detect(spec, rows: list, n_files: int) -> tuple[tuple, tuple]:
    out: list[dict] = []
    checks = ["backward"]
    last_max: dict[int, int] = {}
    for i, r in enumerate(rows):
        m = last_max.get(r.file_index)
        if m is not None and r.time_ns < m:
            out.append(_a("backward", r.time_ns, i, rows))
        last_max[r.file_index] = r.time_ns if m is None else max(m, r.time_ns)

    spans: dict[int, tuple[int, int]] = {}
    for r in rows:
        lo, hi = spans.get(r.file_index, (r.time_ns, r.time_ns))
        spans[r.file_index] = (min(lo, r.time_ns), max(hi, r.time_ns))

    def inside_other(r) -> list[int]:
        return [j for j, (lo, hi) in spans.items() if j != r.file_index and lo <= r.time_ns <= hi]

    if spec.key is not None:
        checks += ["duplicate", "conflict"]
        first: dict = {}
        for i, r in enumerate(rows):
            if r.key is None:
                continue
            j = first.get(r.key)
            if j is None:
                first[r.key] = i
            elif rows[j].identity == r.identity:
                out.append(_a("duplicate", r.time_ns, i, rows))
            else:
                out.append(_a("conflict", r.time_ns, i, rows))
        if n_files > 1:
            checks.append("generation_gap")
            keys_by_file: dict[int, set] = {}
            for r in rows:
                if r.key is not None:
                    keys_by_file.setdefault(r.file_index, set()).add(r.key)
            for i, r in enumerate(rows):
                if r.key is None:
                    continue
                if any(r.key not in keys_by_file.get(j, set()) for j in inside_other(r)):
                    out.append(_a("generation_gap", r.time_ns, i, rows))
    if n_files > 1:
        checks.append("unkeyed_overlap")
        for i, r in enumerate(rows):
            if r.key is None and inside_other(r):
                out.append(_a("unkeyed_overlap", r.time_ns, i, rows))

    if spec.synthetic is not None:
        checks.append("synthetic")
        out.extend(_a("synthetic", r.time_ns, i, rows) for i, r in enumerate(rows) if r.synthetic)

    if spec.kind == "bar" and spec.bar.session == "24x7" and rows:
        checks += ["gap", "off_grid"]
        iv = spec.bar.interval_ns
        starts = sorted({r.time_ns for r in rows})
        s0, s1 = starts[0], starts[-1]
        for i, r in enumerate(rows):
            if (r.time_ns - s0) % iv:
                out.append(_a("off_grid", r.time_ns, i, rows))
        have = set(starts)
        for s in range(s0, s1 + 1, iv):
            if s not in have:
                out.append(_a("gap", s, None, rows))
    return tuple(out), tuple(checks)


def count(anoms) -> dict[str, int]:
    return dict(sorted(Counter(a["kind"] for a in anoms).items()))


def resolve(name: str, rows: list, anoms, policies: Mapping[str, str]) -> tuple[list, dict]:
    if not isinstance(policies, Mapping):
        raise SpecError("resolve must be a mapping kind -> policy")
    for kind, pol in policies.items():
        if kind not in POLICIES:
            raise SpecError(f"resolve: unknown anomaly kind {kind!r} (kinds: {list(KINDS)})")
        if pol not in POLICIES[kind]:
            raise SpecError(f"resolve[{kind!r}] must be one of {list(POLICIES[kind])}, got {pol!r}")
    present = count(anoms)
    missing = {k: n for k, n in present.items() if k not in policies}
    if missing:
        raise UnresolvedAnomalyError(
            f"dataset {name!r} has anomalies with no named resolution: {missing}; name one policy per "
            f"kind in resolve (choices: { {k: list(POLICIES[k]) for k in missing} })")
    applied = {k: policies[k] for k in present}
    drop: set[int] = set()
    by = {k: [a for a in anoms if a["kind"] == k] for k in present}
    drop.update(a["row"] for a in by.get("duplicate", ()))
    if "conflict" in present:
        conflicting = {rows[a["row"]].key for a in by["conflict"]}
        groups: dict = {}
        for i, r in enumerate(rows):
            if r.key in conflicting:
                groups.setdefault(r.key, []).append(i)
        for idxs in groups.values():
            keep = idxs[0] if policies["conflict"] == "keep_first" else idxs[-1]
            drop.update(i for i in idxs if i != keep)
    if policies.get("backward") == "drop" and "backward" in present:
        drop.update(a["row"] for a in by["backward"])
    if policies.get("synthetic") == "drop" and "synthetic" in present:
        drop.update(a["row"] for a in by["synthetic"])
    if policies.get("off_grid") == "drop" and "off_grid" in present:
        drop.update(a["row"] for a in by["off_grid"])
    kept = [r for i, r in enumerate(rows) if i not in drop]
    kept.sort(key=lambda r: int(r.event.exchange_time_ns))
    return kept, applied
