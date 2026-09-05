#!/usr/bin/env python3
"""Pre-empt retention-limited source expiry with automatic snapshots.

docs/QA_PLAN_2026-09.md §1-2 item 5 / docs/DATA_GOVERNANCE_PLAN.md §2.7:
several upstream sources this project reads enforce a hard (or empirically
observed) retention window -- bitFlyer's own execution history API caps at
31 days, OKX's rubik endpoints cap open interest at 30 days (1H) or 2-3 days
(5m) and the long/short ratio at 60-90 days (config/constants.yaml
`data_retention.*`, sourced via src/bot/constants.py). If nobody snapshots a
source before it rolls off the upstream window, that data is gone forever
(see docs/QA_PLAN_2026-09.md's Binance-1m "210日窓に対し21日しか残っていな
かった" incident this plan exists to prevent).

This script takes a **copy-only** snapshot of each configured source into
`backtest_data/auto_<source>_<YYYYMMDD>/` -- one snapshot at (at most) half
the source's retention window, so a missed run or two still leaves margin
before the upstream data actually expires:

    bitFlyer executions   31d  -> every <=15 days  (data/tape/*.csv.gz,
                                  data/candles_*.csv -- the extract_tape.py /
                                  fetch_history.py outputs already used for
                                  long-term storage, see CLAUDE.md §2)
    OKX open interest 1H  30d  -> every <=14 days  (data/okx_btc_oi_1h.csv)
    OKX open interest 5m  2-3d -> daily            (data/okx_btc_oi_5m.csv)
    OKX long/short ratio  60d  -> every <=28 days  (data/okx_btc_lsratio_1h.csv,
                                  data/okx_btc_lsratio_5m.csv)
    OI snapshots csv      rolling, no upstream expiry, but this project's own
                           append-only ledger -> every <=14 days as a safety
                           copy (paper_logs/oi_snapshots.csv, falling back to
                           data/oi_snapshots.csv via the same shared_or_local
                           rule the dashboard uses)
    venues                rolling -> every <=14 days
                           (paper_logs/venues/*.csv.gz, preferring the shared
                           copy over data/venues/*.csv.gz by basename)

Each configured cadence is checked against config/constants.yaml at run time
(``interval_days <= min(retention_days) / 2``) so a future edit to the
retention constant that invalidates the cadence fails loudly instead of
silently snapshotting too late.

Safety (CLAUDE.md: never delete or modify data files):
  - every source file is only ever *read* (shutil.copy2 into the snapshot
    dir); nothing under data/ or paper_logs/ is opened for writing.
  - a snapshot directory is created with mkdir(exist_ok=False) -- an existing
    snapshot for that source+date is NEVER overwritten; the run just skips.
  - a source with no retention-driven snapshot due yet (latest snapshot
    younger than its interval) is skipped -- no directory, no copy, no cost.

Each snapshot carries `MD5SUMS` (standard md5sum-format checksums of every
copied file) and `manifest.json` (source, window={retention_days,
interval_days}, rows, first_ts, last_ts, per-file detail, created_at).

Usage:
    python scripts/retention_snapshot.py                 # run all sources
    python scripts/retention_snapshot.py --summary        # + print actions
    python scripts/retention_snapshot.py --root /path     # different repo root
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
import intake_ledger as il  # noqa: E402 -- reuse row/timestamp/md5 scanning

SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
from bot.constants import load_constants  # noqa: E402
from bot.monitoring.gates import shared_or_local  # noqa: E402


# --------------------------------------------------------------------------
# source definitions
# --------------------------------------------------------------------------


def _glob_files(root: Path, *patterns: str) -> list[Path]:
    out: list[Path] = []
    for pat in patterns:
        out.extend(sorted(p for p in root.glob(pat) if p.is_file()))
    return out


def _bitflyer_executions_files(root: Path) -> list[Path]:
    return _glob_files(root, "data/tape/*.csv.gz", "data/candles_*.csv")


def _okx_oi_1h_files(root: Path) -> list[Path]:
    return _glob_files(root, "data/okx_btc_oi_1h.csv")


def _okx_oi_5m_files(root: Path) -> list[Path]:
    return _glob_files(root, "data/okx_btc_oi_5m.csv")


def _okx_ls_ratio_files(root: Path) -> list[Path]:
    return _glob_files(root, "data/okx_btc_lsratio_1h.csv", "data/okx_btc_lsratio_5m.csv")


def _oi_snapshots_files(root: Path) -> list[Path]:
    path = shared_or_local(root, "data/oi_snapshots.csv")
    return [path] if path.exists() else []


def _venues_files(root: Path) -> list[Path]:
    # paper_logs/venues is the shared/canonical copy (per shared_or_local's
    # own "operator PC is newest by construction" rule); data/venues is the
    # local scratch fallback. Prefer the shared file by basename when both
    # exist, same precedence dashboard reads already use elsewhere.
    by_name: dict[str, Path] = {}
    for d in (root / "data" / "venues", root / "paper_logs" / "venues"):
        if not d.is_dir():
            continue
        for p in sorted(d.glob("*.csv.gz")):
            by_name[p.name] = p
    return sorted(by_name.values())


@dataclass(frozen=True)
class SourceSpec:
    name: str
    interval_days: int
    resolve_files: Callable[[Path], list[Path]]
    constant_key: Optional[str] = None  # config/constants.yaml data_retention.<key>
    notes: str = ""


SOURCES: list[SourceSpec] = [
    SourceSpec(
        "bitflyer_executions", 15, _bitflyer_executions_files,
        constant_key="data_retention.bitflyer_executions_days",
        notes="bitFlyer public execution history API: 31-day hard limit.",
    ),
    SourceSpec(
        "okx_open_interest_1h", 14, _okx_oi_1h_files,
        constant_key="data_retention.okx_open_interest_1h_days",
        notes="OKX rubik open-interest-volume, period=1H: 30-day hard wall.",
    ),
    SourceSpec(
        "okx_open_interest_5m", 1, _okx_oi_5m_files,
        constant_key="data_retention.okx_open_interest_5m_days",
        notes="OKX rubik open-interest-volume, period=5m: 2-3 day wall.",
    ),
    SourceSpec(
        "okx_long_short_ratio", 28, _okx_ls_ratio_files,
        constant_key="data_retention.okx_long_short_ratio_days",
        notes="OKX rubik long-short-account-ratio: empirically 60-90 days.",
    ),
    SourceSpec(
        "oi_snapshots", 14, _oi_snapshots_files,
        notes="Rolling project ledger, no upstream expiry; safety copy only.",
    ),
    SourceSpec(
        "venues", 14, _venues_files,
        notes="Rolling venue tape shards, no upstream expiry; safety copy only.",
    ),
]


class RetentionCadenceError(Exception):
    """A configured snapshot interval no longer satisfies half the
    retention window recorded in config/constants.yaml."""


def _min_retention_days(value: Any) -> float:
    if isinstance(value, (list, tuple)):
        return float(min(value))
    return float(value)


def _validate_cadence(spec: SourceSpec, constants: dict[str, Any]) -> Any:
    """Returns the raw retention value (for the manifest) after checking the
    configured interval is still <= half the retention window. Sources with
    no constant_key (rolling, no upstream expiry) are exempt."""
    if spec.constant_key is None:
        return "rolling"
    c = constants.get(spec.constant_key)
    if c is None:
        raise RetentionCadenceError(
            f"{spec.name}: constant {spec.constant_key!r} not found in "
            "config/constants.yaml -- refusing to guess a retention window"
        )
    min_days = _min_retention_days(c.value)
    if spec.interval_days > min_days / 2:
        raise RetentionCadenceError(
            f"{spec.name}: configured interval {spec.interval_days}d exceeds "
            f"half of {spec.constant_key}={c.value} ({min_days / 2:.1f}d) -- "
            "the source may already have expired data before this runs; fix "
            "the interval in scripts/retention_snapshot.py"
        )
    return c.value


# --------------------------------------------------------------------------
# snapshot dir discovery
# --------------------------------------------------------------------------

_DIR_RE_PREFIX = "auto_"


def _snapshot_dirs(backtest_dir: Path, source: str) -> list[tuple[str, Path]]:
    """[(YYYYMMDD, path), ...] for existing auto_<source>_<date> dirs."""
    out = []
    prefix = f"{_DIR_RE_PREFIX}{source}_"
    if not backtest_dir.is_dir():
        return out
    for p in backtest_dir.iterdir():
        if not p.is_dir() or not p.name.startswith(prefix):
            continue
        date_part = p.name[len(prefix):]
        if len(date_part) == 8 and date_part.isdigit():
            out.append((date_part, p))
    return sorted(out)


def _latest_snapshot_age_days(dirs: list[tuple[str, Path]], now: datetime) -> Optional[float]:
    if not dirs:
        return None
    latest_date_str = dirs[-1][0]
    latest_date = datetime.strptime(latest_date_str, "%Y%m%d").replace(tzinfo=timezone.utc)
    return (now - latest_date).total_seconds() / 86400.0


# --------------------------------------------------------------------------
# snapshot execution
# --------------------------------------------------------------------------


def _scan_file(path: Path) -> dict[str, Any]:
    rec: dict[str, Any] = {
        "name": path.name, "bytes": path.stat().st_size,
        "md5": il.md5_of(path), "row_count": None,
        "first_ts": None, "last_ts": None,
    }
    kind = il.tabular_kind(path.name)
    if kind is not None:
        fmt, gz = kind
        try:
            if fmt == "csv":
                rows, first_ts, last_ts = il.scan_csv(path, gz, il.DEFAULT_TS_CAP)
            else:
                rows, first_ts, last_ts = il.scan_jsonl(path, gz, il.DEFAULT_TS_CAP)
            rec["row_count"], rec["first_ts"], rec["last_ts"] = rows, first_ts, last_ts
        except (OSError, gzip.BadGzipFile) as exc:
            rec["scan_error"] = f"{type(exc).__name__}: {exc}"
    return rec


def _write_md5sums(dest_dir: Path, file_recs: list[dict[str, Any]]) -> None:
    lines = [f"{r['md5']}  {r['name']}\n" for r in sorted(file_recs, key=lambda r: r["name"])]
    (dest_dir / "MD5SUMS").write_text("".join(lines), encoding="utf-8")


def snapshot_source(root: Path, spec: SourceSpec, constants: dict[str, Any],
                    now: datetime) -> dict[str, Any]:
    """Take (or skip) one source's snapshot. Never raises for ordinary
    skip conditions; raises RetentionCadenceError only for a misconfigured
    cadence (a real bug worth stopping the batch job for)."""
    retention_value = _validate_cadence(spec, constants)
    backtest_dir = root / "backtest_data"
    existing = _snapshot_dirs(backtest_dir, spec.name)
    age_days = _latest_snapshot_age_days(existing, now)

    if age_days is not None and age_days < spec.interval_days:
        return {"source": spec.name, "action": "skip",
                "reason": f"latest snapshot is {age_days:.1f}d old (< {spec.interval_days}d)"}

    files = spec.resolve_files(root)
    if not files:
        return {"source": spec.name, "action": "skip",
                "reason": "no source files present"}

    dest_dir = backtest_dir / f"{_DIR_RE_PREFIX}{spec.name}_{now.strftime('%Y%m%d')}"
    try:
        dest_dir.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        return {"source": spec.name, "action": "skip",
                "reason": f"{dest_dir.name} already exists (never overwrite)"}

    file_recs: list[dict[str, Any]] = []
    for src in files:
        dest = dest_dir / src.name
        shutil.copy2(src, dest)  # read-only over src; never touches originals
        file_recs.append(_scan_file(dest))

    rows = [r["row_count"] for r in file_recs if r["row_count"] is not None]
    first_tss = [r["first_ts"] for r in file_recs if r["first_ts"]]
    last_tss = [r["last_ts"] for r in file_recs if r["last_ts"]]
    manifest = {
        "source": spec.name,
        "created_at": now.isoformat(),
        "window": {"retention_days": retention_value, "interval_days": spec.interval_days},
        "rows": sum(rows) if rows else None,
        "first_ts": min(first_tss) if first_tss else None,
        "last_ts": max(last_tss) if last_tss else None,
        "files": file_recs,
        "notes": spec.notes,
    }
    (dest_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=1), encoding="utf-8"
    )
    _write_md5sums(dest_dir, file_recs)

    return {"source": spec.name, "action": "created", "dir": str(dest_dir),
            "files": len(file_recs), "rows": manifest["rows"]}


def run(root: Path, now: Optional[datetime] = None) -> list[dict[str, Any]]:
    now = now or datetime.now(timezone.utc)
    constants = load_constants(root)
    return [snapshot_source(root, spec, constants, now) for spec in SOURCES]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=str(REPO_ROOT), help="repo root (default: this repo)")
    ap.add_argument("--summary", action="store_true", help="print per-source actions")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    results = run(root)

    created = sum(1 for r in results if r["action"] == "created")
    skipped = sum(1 for r in results if r["action"] == "skip")
    print(f"retention_snapshot: {created} created, {skipped} skipped")
    if args.summary:
        for r in results:
            print(f"  {r['source']}: {r['action']}"
                  f" ({r.get('reason') or r.get('dir')})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
