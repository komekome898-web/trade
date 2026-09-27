"""The streaming door of the data layer (D-2 of K1 stage A, 2026-09-27).

    s = stream(root, dataset, allowlist=None, resolve=None)
    for chunk in s:            # one chunk per file, in the given order
        chunk.file             # FileRecord (path, real path, size, sha256, seal unit, rows read / kept)
        chunk.events           # the core's events of that file (resolved)
        chunk.anomalies        # what the checks found in that file (and at its border with the previous one)
    s.files(), s.manifest()    # the record of what was read so far

Why: `load` keeps every row of every file as Python objects so that the
checks across files can see them all at once; three years of 1-second bars
(49 million rows) do not fit (ENV_DEFECTS E-2). `stream` reads the SAME way
as `load` -- the same allow-list, the same seal records, the same parsing and
row validation (`loader._read_file`), the same checks (`anomalies.detect`) --
but holds one file at a time: a chunk's rows are dropped once it is handed
out.

What it gives up, and how it refuses instead of guessing:
  * the checks that need two files at once (duplicate / conflict across
    files, generation_gap, unkeyed_overlap) are replaced by one rule: every
    file's rows must come strictly after the previous file's rows (by the
    row time: t_ns, or a bar's start). A file that breaks it is refused
    (`StreamOrderError`); such data goes through `load`.
  * a bar dataset declared "24x7" / "24x5" is checked across files as
    `load` checks it: off_grid against the FIRST bar of the whole stream,
    and (24x7) a gap between two files is reported on the later chunk.
  * `resolve` names a policy per anomaly kind, as `LoadResult.events` does;
    a chunk with an anomaly kind it does not name is refused
    (`UnresolvedAnomalyError`), never passed on silently.

Every path is checked (allow-list, then the seal records by path) when
`stream` is called, before any file is opened -- as `load` does.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterator, Mapping, Optional

from ..core.events import Event
from . import anomalies as A
from .allowlist import DEFAULT_ALLOWLIST, AllowList, SealRegistry
from .errors import SpecError, StreamOrderError
from .loader import FileRecord, _check_paths, _parse_datasets, _read_file


@dataclass(frozen=True)
class StreamChunk:
    index: int  # the file's position in the dataset's paths
    file: FileRecord
    events: tuple[Event, ...]
    anomalies: tuple[dict, ...]
    checks: tuple[str, ...]
    resolution: dict


class Stream:
    """An iterator of StreamChunk (one per file). Iterate it once."""

    def __init__(self, root: str, dataset: Mapping, allowlist: AllowList, resolve: Mapping[str, str]) -> None:
        parsed = _parse_datasets([dataset])
        self._d = parsed[0]
        self.root = root
        self._allow = allowlist
        self._seals = SealRegistry(root)
        self._resolve = dict(resolve)
        # every path is checked before any file is opened (allow-list, then seals by path)
        self._checked = _check_paths(root, parsed, allowlist, self._seals)[0]
        self._files: list[FileRecord] = []
        self._counts: dict[str, int] = {}
        self._started = False

    @property
    def name(self) -> str:
        return self._d.name

    def __iter__(self) -> Iterator[StreamChunk]:
        if self._started:
            raise SpecError("a stream is iterated once (make another stream to read the files again)")
        self._started = True
        return self._chunks()

    def _chunks(self) -> Iterator[StreamChunk]:
        d = self._d
        spec = d.spec
        reader = spec.time.reader()
        prev_max: Optional[int] = None
        prev_given: Optional[str] = None
        grid = spec.kind == "bar" and spec.bar.session in ("24x7", "24x5")
        s0: Optional[int] = None
        last_start: Optional[int] = None
        for fi, cp in enumerate(self._checked):
            rows, rec = _read_file(d, fi, cp, self._seals, reader)
            self._files.append(rec)
            if rows:
                lo = min(r.time_ns for r in rows)
                if prev_max is not None and lo <= prev_max:
                    raise StreamOrderError(
                        f"{cp.given!r}: its first row time {lo} ns is not after the last row time {prev_max} ns of "
                        f"{prev_given!r}; rows across files are checked only by load()")
            anoms, checks = A.detect(spec, rows, 1)
            anoms = list(anoms)
            if grid and rows:
                iv = spec.bar.interval_ns
                if s0 is None:
                    s0 = min(r.time_ns for r in rows)
                # off_grid against the stream's first bar (load checks the whole dataset against its first bar)
                anoms = [a for a in anoms if a["kind"] != "off_grid"]
                anoms += [A._a("off_grid", r.time_ns, i, rows) for i, r in enumerate(rows) if (r.time_ns - s0) % iv]
                first = min(r.time_ns for r in rows)
                if spec.bar.session == "24x7" and last_start is not None:
                    anoms += [A._a("gap", s, None, rows) for s in range(last_start + iv, first, iv)]
                last_start = max(r.time_ns for r in rows)
            if rows:
                prev_max, prev_given = max(r.time_ns for r in rows), cp.given
            for a in anoms:
                self._counts[a["kind"]] = self._counts.get(a["kind"], 0) + 1
            kept, applied = A.resolve(d.name, rows, anoms, self._resolve)
            events = tuple(r.event for r in kept)
            del rows, kept
            yield StreamChunk(fi, rec, events, tuple(anoms), tuple(checks), applied)

    def files(self) -> list[FileRecord]:
        return list(self._files)

    def manifest(self) -> dict:
        return {
            "files": [f.__dict__.copy() for f in self._files],
            "seal_records": dict(self._seals.records_read),
            "allowlist": {"roots": ["/".join(r) for r in self._allow.roots],
                          "deny": [p for p, _ in self._allow.deny]},
            "dataset": {"name": self._d.name, "spec": self._d.spec.source,
                        "range_ns": list(self._d.range_ns) if self._d.range_ns else None,
                        "files_read": len(self._files), "files_declared": len(self._checked),
                        "anomalies": dict(sorted(self._counts.items())), "resolve": dict(self._resolve)},
        }


def stream(root: str, dataset: Any, *, allowlist: Optional[AllowList] = None,
           resolve: Optional[Mapping[str, str]] = None) -> Stream:
    """One dataset ({name, paths, spec[, range_ns]}), read file by file. See the module docstring."""
    if type(root) is not str or not root:
        raise SpecError("root must be a non-empty str (the data root)")
    allow = DEFAULT_ALLOWLIST if allowlist is None else allowlist
    if not isinstance(allow, AllowList):
        raise SpecError("allowlist must be an AllowList")
    if resolve is not None and not isinstance(resolve, Mapping):
        raise SpecError("resolve must be a mapping kind -> policy")
    return Stream(root, dataset, allow, resolve or {})
