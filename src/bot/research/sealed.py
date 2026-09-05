"""Phase-2 data sealing (docs/PHASE2_SPEC.md §3).

Each phase-2 research unit gets an evaluation set sealed away BEFORE any
iteration begins, so that "iterating without overfitting" can be enforced by
code instead of trusted on the researcher's word:

  * the historical HOLD-OUT window: the last 30% of each input file's time
    span, split by CALENDAR date (not row count) — a dense cluster of rows
    near one end must not shift the boundary;
  * the FORWARD window: everything timestamped at/after the day the unit was
    sealed (``forward_start``), since that data did not exist yet when the
    unit's design was frozen.

``scripts/phase2_seal.py`` computes the boundaries and writes the seal record
(``backtest_data/phase2_sealed/<unit>/SEALED.json``) — it never copies, moves,
or rewrites the underlying data files, so the helpers below always read the
data from wherever it already lives.

This module is the ENFORCED path for phase-2 research code:

  * ``load_unsealed`` — the dev set. Always available; sealed rows removed.
  * ``load_sealed``   — the held-out eval set. Refuses unless the environment
    says a final evaluation is deliberately happening (``PHASE2_FINAL_EVAL``)
    AND the owner has dropped an approval file AND the caller passes the
    explicit confirmation token — the same "three independent guards" shape
    as the LIVE_MODE ack (CLAUDE.md §1), because an accidental read here is
    exactly the failure this whole mechanism exists to prevent. Every call
    that gets past the guards is appended to an audit log.
  * ``assert_not_sealed`` — a defensive check for code that loads data by
    some other means (not through ``load_unsealed``) and wants to fail loudly
    rather than silently train on held-out rows.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[3]
SEALED_SUBDIR = Path("backtest_data") / "phase2_sealed"

# Same candidate list / tolerant parsing as scripts/intake_ledger.py — kept in
# sync deliberately (a schema's declared time column should always be one of
# these; see schema/*.json). Order matters: the first candidate present wins.
TS_CANDIDATES = ["ts", "ts_utc", "timestamp", "date", "entry_date",
                  "open_time", "exec_date"]

HASH_CHUNK = 1024 * 1024

UNSEAL_TOKEN = "I_UNDERSTAND_THIS_IS_FINAL_EVAL"


class SealedDataError(Exception):
    """Raised when phase-2 sealed data is requested without the required
    unseal guards, or when a caller's own data crosses a sealed boundary."""


# ---------------------------------------------------------------------------
# timestamp parsing (tolerant; mirrors scripts/intake_ledger.py's parse_ts so
# a seal computed here and a column read there never disagree about what a
# given cell means)
# ---------------------------------------------------------------------------

_YYYYMMDD_RE = re.compile(r"^\d{8}$")


def parse_ts(raw: Any) -> datetime | None:
    """Best-effort tolerant timestamp parse. Returns None, never raises."""
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw if raw.tzinfo else raw.replace(tzinfo=timezone.utc)
    s = str(raw).strip()
    if not s or s.lower() in ("nan", "none", "null", ""):
        return None

    if _YYYYMMDD_RE.match(s):
        try:
            return datetime.strptime(s, "%Y%m%d").replace(tzinfo=timezone.utc)
        except ValueError:
            pass

    try:
        f: float | None = float(s)
    except ValueError:
        f = None
    if f is not None:
        try:
            if abs(f) >= 1e12:  # epoch millis
                return datetime.fromtimestamp(f / 1000.0, tz=timezone.utc)
            if abs(f) >= 1e8:  # epoch seconds
                return datetime.fromtimestamp(f, tz=timezone.utc)
        except (ValueError, OSError, OverflowError):
            return None
        return None

    iso = s[:-1] + "+00:00" if s.endswith("Z") else s
    try:
        dt = datetime.fromisoformat(iso)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def find_ts_column(header: Iterable[str], explicit: str | None = None
                   ) -> int | None:
    lower = [h.strip().lower() for h in header]
    if explicit is not None:
        needle = explicit.strip().lower()
        return lower.index(needle) if needle in lower else None
    for cand in TS_CANDIDATES:
        if cand in lower:
            return lower.index(cand)
    return None


def md5_of(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(HASH_CHUNK)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def is_gz(path: Path) -> bool:
    return path.name.lower().endswith(".gz")


def open_text(path: Path):
    if is_gz(path):
        return gzip.open(path, "rt", encoding="utf-8", errors="replace", newline="")
    return open(path, "rt", encoding="utf-8", errors="replace", newline="")


def read_timestamps(path: Path, time_column: str | None = None
                    ) -> tuple[str, list[datetime]]:
    """(column name used, every parseable timestamp) in a CSV/CSV.GZ file.

    Reads the whole file — sealing is a one-time, per-unit setup cost, not a
    per-dashboard-poll one, so there is no row cap here (unlike
    scripts/intake_ledger.py's default 2000-row cap).
    """
    with open_text(path) as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            raise SealedDataError(f"{path}: empty file, no header row")
        idx = find_ts_column(header, time_column)
        if idx is None:
            wanted = time_column or "/".join(TS_CANDIDATES)
            raise SealedDataError(
                f"{path}: no time column found (looked for {wanted!r} in "
                f"header {header!r})")
        col_name = header[idx]
        out: list[datetime] = []
        for row in reader:
            if idx >= len(row):
                continue
            dt = parse_ts(row[idx])
            if dt is not None:
                out.append(dt)
    if not out:
        raise SealedDataError(f"{path}: no parseable timestamps in column {col_name!r}")
    return col_name, out


def calendar_seal_boundary(timestamps: Iterable[datetime]) -> datetime:
    """The calendar date (00:00:00 UTC) at which 70% of [first, last] date
    span has elapsed, i.e. the start of the sealed last-30% window.

    Deliberately date-granular and row-count-blind: the span is measured in
    whole UTC calendar days between the first and last timestamp's dates, and
    the boundary is ``first_date + floor(span_days * 0.7)`` days — floor
    (not round) so a fractional day always rounds the boundary EARLIER,
    i.e. the sealed window is never smaller than 30% of the calendar span.
    A dense cluster of rows near either end does not move the boundary at
    all, since only the two calendar dates at the ends of the range matter.
    """
    ts_list = sorted(t.astimezone(timezone.utc) for t in timestamps)
    if not ts_list:
        raise SealedDataError("no timestamps to compute a seal boundary from")
    first_date = ts_list[0].date()
    last_date = ts_list[-1].date()
    span_days = (last_date - first_date).days
    boundary_days = (span_days * 7) // 10  # floor(span_days * 0.7), integer-exact
    from datetime import timedelta
    boundary_date = first_date + timedelta(days=boundary_days)
    return datetime(boundary_date.year, boundary_date.month, boundary_date.day,
                     tzinfo=timezone.utc)


def resolve_dataset_files(dataset: str, root: Path | str = REPO_ROOT
                          ) -> list[Path]:
    """Existing files under ``root`` matching schema/<dataset>.json's
    ``path_glob`` patterns, sorted, deduplicated. Read-only: globs, never
    opens for writing."""
    root = Path(root)
    schema_path = root / "schema" / f"{dataset}.json"
    if not schema_path.is_file():
        raise SealedDataError(f"no schema/{dataset}.json for dataset {dataset!r}")
    spec = json.loads(schema_path.read_text(encoding="utf-8"))
    patterns = spec.get("path_glob") or []
    found: list[Path] = []
    seen: set[Path] = set()
    for pattern in patterns:
        for p in sorted(root.glob(pattern)):
            if p.is_file() and p not in seen:
                seen.add(p)
                found.append(p)
    return found


# ---------------------------------------------------------------------------
# seal record I/O (read side; scripts/phase2_seal.py is the write side)
# ---------------------------------------------------------------------------

def seal_dir(unit: str, root: Path | str = REPO_ROOT) -> Path:
    return Path(root) / SEALED_SUBDIR / unit


def seal_path(unit: str, root: Path | str = REPO_ROOT) -> Path:
    return seal_dir(unit, root) / "SEALED.json"


def _rel_str(path: Path, root: Path) -> str:
    path = Path(path)
    root = Path(root)
    abs_path = path if path.is_absolute() else (root / path)
    try:
        return str(abs_path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(abs_path)


def load_seal_record(unit: str, root: Path | str = REPO_ROOT) -> dict:
    p = seal_path(unit, root)
    if not p.is_file():
        raise SealedDataError(f"no seal record for unit {unit!r} at {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def _find_file_entry(seal: dict, path: Path, root: Path) -> dict:
    rel = _rel_str(path, root)
    for entry in seal.get("files", []):
        if entry["path"] == rel:
            return entry
    raise SealedDataError(
        f"{rel} is not one of unit {seal.get('unit')!r}'s sealed files "
        f"({[e['path'] for e in seal.get('files', [])]})")


def _read_table(path: Path) -> pd.DataFrame:
    # pandas infers gzip from the .gz suffix automatically.
    return pd.read_csv(path)


def is_dataset_sealed_file(dataset_path: str, unit: str,
                           root: Path | str = REPO_ROOT) -> bool:
    """True if ``dataset_path`` (relative to ``root``) is one of unit's
    sealed files, per its SEALED.json. False (never raises) if the unit has
    no seal record at all — used by gates.shared_or_local's warning-only
    check, which must not blow up plain non-phase-2 reads."""
    try:
        seal = load_seal_record(unit, root)
    except SealedDataError:
        return False
    root = Path(root)
    rel = _rel_str(Path(dataset_path), root)
    return any(e["path"] == rel for e in seal.get("files", []))


# ---------------------------------------------------------------------------
# the enforced loaders
# ---------------------------------------------------------------------------

def load_unsealed(path: Path | str, unit: str, root: Path | str = REPO_ROOT
                  ) -> pd.DataFrame:
    """The dev-set rows of ``path``: sealed rows REMOVED.

    Drops both (a) the file's own historical last-30%-by-calendar-date window
    (``seal_from_ts`` recorded for this exact path in the unit's SEALED.json)
    and (b) every row at/after the unit's ``forward_start``. Always available
    — this is the path iteration is meant to use.
    """
    root = Path(root)
    abs_path = Path(path) if Path(path).is_absolute() else root / path
    seal = load_seal_record(unit, root)
    entry = _find_file_entry(seal, abs_path, root)
    df = _read_table(abs_path)
    col = entry["time_column"]
    if col not in df.columns:
        raise SealedDataError(
            f"{abs_path}: sealed time_column {col!r} not present (columns: "
            f"{list(df.columns)})")
    seal_from = datetime.fromisoformat(entry["seal_from_ts"])
    forward_start = datetime.fromisoformat(seal["forward_start"])
    cutoff = min(seal_from, forward_start)
    ts = df[col].map(parse_ts)
    keep = ts.map(lambda d: d is not None and d < cutoff)
    return df.loc[keep].reset_index(drop=True)


def load_sealed(path: Path | str, unit: str, token: str,
                root: Path | str = REPO_ROOT) -> pd.DataFrame:
    """The held-out eval-set rows of ``path`` — refuses unless ALL THREE
    guards are satisfied, mirroring CLAUDE.md §1's LIVE_MODE shape:

      1. env ``PHASE2_FINAL_EVAL`` equals exactly this ``unit``,
      2. ``backtest_data/phase2_sealed/<unit>/UNSEAL_APPROVED`` exists
         (owner-created; this code never creates it),
      3. the caller passes the explicit confirmation token.

    Any call that gets past the guards is appended to
    ``backtest_data/phase2_sealed/<unit>/UNSEAL_LOG.jsonl`` (audit trail,
    written even though this is a read of already-existing data).
    """
    import os

    root = Path(root)
    env_unit = os.environ.get("PHASE2_FINAL_EVAL")
    approved = seal_dir(unit, root) / "UNSEAL_APPROVED"
    reasons = []
    if env_unit != unit:
        reasons.append(f"PHASE2_FINAL_EVAL={env_unit!r} does not equal unit {unit!r}")
    if not approved.is_file():
        reasons.append(f"missing owner approval file {approved}")
    if token != UNSEAL_TOKEN:
        reasons.append("wrong confirmation token")
    if reasons:
        raise SealedDataError(
            f"refusing to unseal {unit!r}: " + "; ".join(reasons))

    abs_path = Path(path) if Path(path).is_absolute() else root / path
    seal = load_seal_record(unit, root)
    entry = _find_file_entry(seal, abs_path, root)
    df = _read_table(abs_path)
    col = entry["time_column"]
    seal_from = datetime.fromisoformat(entry["seal_from_ts"])
    ts = df[col].map(parse_ts)
    keep = ts.map(lambda d: d is not None and d >= seal_from)
    result = df.loc[keep].reset_index(drop=True)

    log_path = seal_dir(unit, root) / "UNSEAL_LOG.jsonl"
    record = {
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "unit": unit,
        "path": _rel_str(abs_path, root),
        "rows_returned": int(len(result)),
    }
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return result


def assert_not_sealed(df: pd.DataFrame, unit: str, root: Path | str = REPO_ROOT
                      ) -> None:
    """Raise ``SealedDataError`` if any row of ``df`` falls into a sealed
    window for ``unit``, for code that loaded data by some means other than
    ``load_unsealed``.

    ``df`` carries no file identity, so this cannot know which file's
    historical seal_from_ts specifically applies — it checks the
    UNIVERSALLY sealed forward window (``forward_start``, applies to every
    file in the unit) plus, conservatively, EVERY file's own historical
    window recorded in the unit's SEALED.json. A false positive (flagging a
    row that only coincides in time with an unrelated file's sealed window)
    is the safe direction to err in here; a false negative is not.
    """
    seal = load_seal_record(unit, root)
    forward_start = datetime.fromisoformat(seal["forward_start"])
    seal_froms = [datetime.fromisoformat(e["seal_from_ts"])
                 for e in seal.get("files", [])]
    earliest_seal_from = min(seal_froms) if seal_froms else forward_start

    col = None
    lower_cols = {str(c).strip().lower(): c for c in df.columns}
    for cand in TS_CANDIDATES:
        if cand in lower_cols:
            col = lower_cols[cand]
            break
    if col is None:
        raise SealedDataError(
            f"assert_not_sealed: no recognizable time column in {list(df.columns)}")

    for raw in df[col]:
        dt = parse_ts(raw)
        if dt is None:
            continue
        if dt >= earliest_seal_from:
            raise SealedDataError(
                f"row at {dt.isoformat()} falls in a sealed window for unit "
                f"{unit!r} (forward_start={forward_start.isoformat()})")
