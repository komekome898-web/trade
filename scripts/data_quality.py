#!/usr/bin/env python3
"""Data quality checks over the intake ledger's inventory.

Why this exists: docs/DATA_GOVERNANCE_PLAN.md / docs/QA_PLAN_2026-09.md list
concrete quality failures found by hand during audits (crossed order books,
maintenance-window synthetic bars, a `t`/`ts` column mixup, zero-volume days,
extreme single-step returns) and ask for an automatic, repeatable check that
runs at intake time instead of being rediscovered by an auditor each round.

This script NEVER modifies, moves, or deletes anything under the scanned
data roots. It only reads:
  - data/INTAKE_latest.json (from scripts/intake_ledger.py) for the file
    inventory (paths, status, row counts) -- it does not re-walk the
    filesystem itself, so run intake_ledger.py first (or let the caller,
    e.g. deploy/fetch_all.bat, run it right before this script);
  - schema/*.json for column documentation (missing-column checks) and
    dataset identity (path_glob -> dataset name);
  - the data files themselves, streamed read-only.

Checks (per file, where the relevant column exists in the header):
  - duplicate_keys:     repeated timestamp-column value
  - non_monotonic:      timestamp column decreases somewhere in the file
  - gaps:               an inter-row time gap far larger than the file's own
                         median gap (no hardcoded cadence assumption --
                         see GAP_MULTIPLIER)
  - crossed_book:       a `spread_bps` column <= 0 or > 50
  - maintenance_window:  a flat (open==high==low==close) OHLC row inside
                         19:00-19:10 UTC (bitFlyer's documented maintenance
                         window) -- a candidate synthetic/carried-forward bar
  - extreme_return:     |pct change| > 10% between consecutive rows of a
                         price-like column (close/price/last/mid)
  - zero_volume:        a `volume` column equal to 0
  - missing_columns:    header columns undocumented in schema, or schema
                         columns absent from the header (per matched dataset)

Nothing is EXCLUDED for a flagged row -- this only marks, per the plan's
"除外はしない、印を付けるだけ" rule.

Usage:
    python scripts/data_quality.py               # run checks, write QUALITY.json
    python scripts/data_quality.py --summary     # + print a table of counts
    python scripts/data_quality.py --root /path  # different repo root
"""
from __future__ import annotations

import argparse
import csv
import fnmatch
import gzip
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import intake_ledger as il  # noqa: E402

REPO_ROOT = SCRIPT_DIR.parent

MAX_EXAMPLES = 5
GAP_MULTIPLIER = 8  # flag a gap this many times the file's own median gap
MAINT_START_H, MAINT_START_M = 19, 0
MAINT_END_H, MAINT_END_M = 19, 10
EXTREME_RETURN_FRAC = 0.10
CROSSED_SPREAD_MAX_BPS = 50.0

PRICE_COL_CANDIDATES = ["close", "price", "last", "mid"]


# --------------------------------------------------------------------------
# schema / dataset matching
# --------------------------------------------------------------------------


def load_schemas(root: Path) -> list[dict]:
    schema_dir = root / "schema"
    schemas = []
    if not schema_dir.exists():
        return schemas
    for p in sorted(schema_dir.glob("*.json")):
        try:
            with open(p, "r", encoding="utf-8") as f:
                schemas.append(json.load(f))
        except (OSError, json.JSONDecodeError):
            continue
    return schemas


def match_dataset(rel_path: str, schemas: list[dict]) -> Optional[dict]:
    for schema in schemas:
        globs = schema.get("path_glob") or []
        if isinstance(globs, str):
            globs = [globs]
        for g in globs:
            if fnmatch.fnmatch(rel_path, g):
                return schema
    return None


def schema_columns_for(schema: dict, filename: str) -> Optional[set]:
    """Flatten the documented column names relevant to this file: the
    dataset-level `columns` dict, plus any `file_groups` entry whose key
    (a filename pattern/example) appears as a substring of this filename."""
    cols: set = set()
    top = schema.get("columns")
    if isinstance(top, dict):
        cols.update(top.keys())
    groups = schema.get("file_groups")
    if isinstance(groups, dict):
        matched_any = False
        for group_key, group_val in groups.items():
            # group_key looks like "quotes_YYYYMMDD.csv.gz" or a bare
            # filename -- match on the stable literal prefix before any
            # placeholder/wildcard token.
            prefix = group_key.split("YYYYMMDD")[0].split("<")[0].split("*")[0]
            prefix = prefix.strip()
            if prefix and filename.startswith(prefix.split("/")[-1].split(" ")[0]):
                gcols = group_val.get("columns") if isinstance(group_val, dict) else None
                if isinstance(gcols, dict):
                    cols.update(gcols.keys())
                    matched_any = True
        if not matched_any and not cols:
            return None
    if not cols:
        return None
    return cols


# --------------------------------------------------------------------------
# per-file scan
# --------------------------------------------------------------------------


def _find_col(header_lower: list[str], candidates: list[str]) -> Optional[int]:
    for c in candidates:
        if c in header_lower:
            return header_lower.index(c)
    return None


def scan_file(root: Path, rel_path: str, schema: Optional[dict]) -> dict:
    """Run all applicable checks on one tabular file. Returns a dict of
    check_name -> {"count": int, "examples": [...]} for checks that fired
    at least once, plus (optionally) "missing_columns"."""
    result: dict[str, dict] = {}
    p = root / rel_path
    kind = il.tabular_kind(p.name)
    if kind is None or not p.exists():
        return result
    fmt, gz = kind
    if fmt != "csv":
        return result  # jsonl checks are out of scope for these column-based rules

    try:
        with il.open_text(p, gz) as f:
            reader = csv.reader(f)
            try:
                header = next(reader)
            except StopIteration:
                return result
            header_lower = [h.strip().lower() for h in header]

            if schema is not None:
                declared = schema_columns_for(schema, p.name)
                if declared is not None:
                    declared_lower = {c.lower() for c in declared}
                    have_lower = set(header_lower)
                    undocumented = [header[i] for i, h in enumerate(header_lower) if h not in declared_lower]
                    absent = sorted(declared_lower - have_lower)
                    if undocumented or absent:
                        result["missing_columns"] = {
                            "count": len(undocumented) + len(absent),
                            "examples": [
                                {"undocumented_in_schema": undocumented[:MAX_EXAMPLES],
                                 "declared_but_absent": absent[:MAX_EXAMPLES]}
                            ],
                        }

            ts_idx = il.find_ts_column(header)
            spread_idx = _find_col(header_lower, ["spread_bps"])
            volume_idx = _find_col(header_lower, ["volume"])
            price_idx = _find_col(header_lower, PRICE_COL_CANDIDATES)
            ohlc_idx = None
            if all(c in header_lower for c in ("open", "high", "low", "close")):
                ohlc_idx = {c: header_lower.index(c) for c in ("open", "high", "low", "close")}

            seen_ts: dict[str, int] = {}
            dup_examples: list = []
            non_monotonic_examples: list = []
            gap_examples: list = []
            crossed_examples: list = []
            maint_examples: list = []
            extreme_examples: list = []
            zero_vol_examples: list = []

            prev_dt = None
            prev_price = None
            deltas: list[float] = []
            rows_with_dt: list[tuple[float, list[str]]] = []

            row_i = 0
            for row in reader:
                row_i += 1
                # duplicate keys
                if ts_idx is not None and ts_idx < len(row):
                    raw_ts = row[ts_idx]
                    if raw_ts:
                        seen_ts[raw_ts] = seen_ts.get(raw_ts, 0) + 1
                        if seen_ts[raw_ts] == 2 and len(dup_examples) < MAX_EXAMPLES:
                            dup_examples.append({"row": row_i, "ts": raw_ts})

                    dt = il.parse_ts(raw_ts)
                    if dt is not None:
                        if prev_dt is not None:
                            if dt < prev_dt and len(non_monotonic_examples) < MAX_EXAMPLES:
                                non_monotonic_examples.append(
                                    {"row": row_i, "prev_ts": prev_dt.isoformat(), "ts": dt.isoformat()}
                                )
                            delta = (dt - prev_dt).total_seconds()
                            if delta > 0:
                                deltas.append(delta)
                                rows_with_dt.append((row_i, delta, dt.isoformat()))
                        prev_dt = dt

                # crossed book
                if spread_idx is not None and spread_idx < len(row):
                    try:
                        sv = float(row[spread_idx])
                    except (ValueError, TypeError):
                        sv = None
                    if sv is not None and (sv <= 0 or sv > CROSSED_SPREAD_MAX_BPS):
                        if len(crossed_examples) < MAX_EXAMPLES:
                            crossed_examples.append({"row": row_i, "spread_bps": sv})

                # maintenance window flat bar
                if ohlc_idx is not None and ts_idx is not None and ts_idx < len(row):
                    dt2 = il.parse_ts(row[ts_idx])
                    if dt2 is not None:
                        in_window = (
                            (dt2.hour, dt2.minute) >= (MAINT_START_H, MAINT_START_M)
                            and (dt2.hour, dt2.minute) < (MAINT_END_H, MAINT_END_M)
                        )
                        if in_window:
                            try:
                                o = float(row[ohlc_idx["open"]])
                                h = float(row[ohlc_idx["high"]])
                                l = float(row[ohlc_idx["low"]])
                                c = float(row[ohlc_idx["close"]])
                            except (ValueError, TypeError, IndexError):
                                o = h = l = c = None
                            if o is not None and o == h == l == c:
                                if len(maint_examples) < MAX_EXAMPLES:
                                    maint_examples.append({"row": row_i, "ts": dt2.isoformat(), "value": o})

                # extreme single-step return
                if price_idx is not None and price_idx < len(row):
                    try:
                        pv = float(row[price_idx])
                    except (ValueError, TypeError):
                        pv = None
                    if pv is not None:
                        if prev_price not in (None, 0) and pv != 0:
                            ret = (pv - prev_price) / prev_price
                            if abs(ret) > EXTREME_RETURN_FRAC:
                                if len(extreme_examples) < MAX_EXAMPLES:
                                    extreme_examples.append({"row": row_i, "prev": prev_price, "value": pv, "return": ret})
                        prev_price = pv

                # zero volume
                if volume_idx is not None and volume_idx < len(row):
                    try:
                        vv = float(row[volume_idx])
                    except (ValueError, TypeError):
                        vv = None
                    if vv == 0.0:
                        if len(zero_vol_examples) < MAX_EXAMPLES:
                            zero_vol_examples.append({"row": row_i, "ts": row[ts_idx] if ts_idx is not None and ts_idx < len(row) else None})

            dup_count = sum(1 for v in seen_ts.values() if v > 1)
            if dup_count:
                result["duplicate_keys"] = {"count": dup_count, "examples": dup_examples}
            if non_monotonic_examples:
                result["non_monotonic"] = {"count": len(non_monotonic_examples), "examples": non_monotonic_examples}
            if crossed_examples:
                result["crossed_book"] = {"count": len(crossed_examples), "examples": crossed_examples}
            if maint_examples:
                result["maintenance_window"] = {"count": len(maint_examples), "examples": maint_examples}
            if extreme_examples:
                result["extreme_return"] = {"count": len(extreme_examples), "examples": extreme_examples}
            if zero_vol_examples:
                result["zero_volume"] = {"count": len(zero_vol_examples), "examples": zero_vol_examples}

            if len(deltas) >= 4:
                sorted_deltas = sorted(deltas)
                median = sorted_deltas[len(sorted_deltas) // 2]
                if median > 0:
                    threshold = median * GAP_MULTIPLIER
                    gaps_found = [(ri, d, ts) for ri, d, ts in rows_with_dt if d > threshold]
                    if gaps_found:
                        gap_examples = [
                            {"row": ri, "gap_seconds": d, "ts": ts}
                            for ri, d, ts in sorted(gaps_found, key=lambda x: -x[1])[:MAX_EXAMPLES]
                        ]
                        result["gaps"] = {
                            "count": len(gaps_found),
                            "median_gap_seconds": median,
                            "examples": gap_examples,
                        }
    except (OSError, gzip.BadGzipFile, csv.Error) as exc:
        result["scan_error"] = {"count": 1, "examples": [{"error": f"{type(exc).__name__}: {exc}"}]}

    return result


# --------------------------------------------------------------------------
# driver
# --------------------------------------------------------------------------


def run(root: Path) -> dict:
    latest_path = root / "data" / "INTAKE_latest.json"
    index = il.load_latest(latest_path)
    schemas = load_schemas(root)

    datasets: dict[str, dict] = {}
    unmatched: list[str] = []

    for rel_path, rec in sorted(index.items()):
        if rec.get("status") != "present":
            continue
        if il.tabular_kind(Path(rel_path).name) is None:
            continue

        schema = match_dataset(rel_path, schemas)
        if schema is None:
            unmatched.append(rel_path)
            dataset_name = "_unmatched"
        else:
            dataset_name = schema.get("dataset", "_unmatched")

        d = datasets.setdefault(dataset_name, {"files_checked": 0, "files_flagged": 0, "checks": {}})
        d["files_checked"] += 1

        file_result = scan_file(root, rel_path, schema)
        if not file_result:
            continue
        d["files_flagged"] += 1
        for check_name, payload in file_result.items():
            agg = d["checks"].setdefault(check_name, {"count": 0, "files": 0, "examples": []})
            agg["count"] += payload.get("count", 0)
            agg["files"] += 1
            if len(agg["examples"]) < MAX_EXAMPLES:
                agg["examples"].append({"path": rel_path, **{k: v for k, v in payload.items() if k != "count"}})

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ledger_source": str(latest_path.relative_to(root)) if latest_path.exists() else None,
        "datasets": datasets,
        "unmatched_files": sorted(set(unmatched)),
    }
    return report


def write_report(root: Path, report: dict) -> Path:
    out_path = root / "data" / "QUALITY.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, sort_keys=True, indent=1)
    return out_path


def print_summary(report: dict) -> None:
    headers = ["dataset", "files", "flagged", "checks_fired", "total_hits"]
    rows_out = []
    for name in sorted(report["datasets"]):
        d = report["datasets"][name]
        checks = d.get("checks", {})
        total_hits = sum(c.get("count", 0) for c in checks.values())
        rows_out.append([name, str(d["files_checked"]), str(d["files_flagged"]), str(len(checks)), str(total_hits)])

    widths = [len(h) for h in headers]
    for row in rows_out:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    def fmt_row(cells):
        return "  ".join(c.ljust(widths[i]) for i, c in enumerate(cells))

    print(fmt_row(headers))
    print(fmt_row(["-" * w for w in widths]))
    for row in rows_out:
        print(fmt_row(row))

    if report["unmatched_files"]:
        print(f"\n{len(report['unmatched_files'])} tabular files not matched to any schema/*.json dataset (see unmatched_files in QUALITY.json)")

    print("\nchecks by type (across all datasets):")
    by_check: dict[str, int] = {}
    for d in report["datasets"].values():
        for check_name, payload in d.get("checks", {}).items():
            by_check[check_name] = by_check.get(check_name, 0) + payload.get("count", 0)
    for check_name in sorted(by_check):
        print(f"  {check_name}: {by_check[check_name]}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=str(REPO_ROOT), help="repo root (default: this repo)")
    ap.add_argument("--summary", action="store_true", help="print a per-dataset summary table")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    report = run(root)
    out_path = write_report(root, report)

    total_hits = sum(
        sum(c.get("count", 0) for c in d.get("checks", {}).values())
        for d in report["datasets"].values()
    )
    print(f"data_quality: {len(report['datasets'])} datasets, {total_hits} flagged rows total -> {out_path}")

    if args.summary:
        print()
        print_summary(report)

    return 0


if __name__ == "__main__":
    sys.exit(main())
