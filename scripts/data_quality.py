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
  - split_candidate:    (daily OHLC files only, i.e. header's timestamp
                         column is literally `date`) flag-only check: a day
                         whose close/prev_close ratio (or its inverse) is
                         within SPLIT_TOLERANCE of a round factor in
                         SPLIT_FACTORS *and* the next day's close stays
                         within PERSIST_TOLERANCE of the new level (so it is
                         not a one-day round trip) is a probable unadjusted
                         corporate action rather than a bad print. Reported
                         alongside extreme_return when both fire on the same
                         row -- it does not replace or suppress it.

Nothing is EXCLUDED for a flagged row -- this only marks, per the plan's
"除外はしない、印を付けるだけ" rule.

A file that matches no schema/*.json `path_glob` at all lands in the
"schema_undefined" dataset bucket (report["schema_undefined_files"] lists
the paths) and gets ONLY the two structural checks that don't need
documented column meaning: duplicate_keys (on an auto-detected key -- the
full row, not just its timestamp column, since we don't know which columns
actually identify a row) and gaps. The value-based checks (extreme_return,
non_monotonic, crossed_book, maintenance_window, zero_volume,
split_candidate, missing_columns) are skipped there rather than guessed at.

A schema can additionally declare a `quality` block (dataset-level, and/or
per file_groups entry -- the file_groups one wins, same lookup as
`columns`):
  - quality.group_by: [col, ...] -- for a file that interleaves several
    independent time series (e.g. venues' quotes_*.csv.gz holds every
    (venue, pair) ticker in one file), extreme_return / non_monotonic /
    gaps are computed per group instead of over the raw row order.
  - quality.unique_key: [col, ...] -- duplicate_keys uses these columns
    instead of the timestamp column alone (e.g. bitFlyer executions can
    print several distinct trades within one shared microsecond).
  - quality.skip_checks: [check_name, ...] -- the named check(s) do not
    apply to this dataset at all and are dropped from the result entirely
    (e.g. an FX 1-minute feed has no real `volume` concept, so zero_volume
    is meaningless there; bitFlyer's maintenance window has no bearing on
    an FX reference feed either). See _apply_check_switches.
  - quality.informational_checks: [check_name, ...] or "all"/true -- the
    named check(s) (or every check that fires on the file) are real and
    should keep firing, but are not data problems to chase down (e.g.
    qa_synthetic's planted-defect fixtures exist specifically to trip these
    checks). Marked `"informational": true` on the result rather than
    dropped, at both the per-file and dataset-aggregate level.

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
import re
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

SPLIT_FACTORS = [2, 3, 4, 5, 10, 100]
SPLIT_TOLERANCE = 0.02   # ratio (or its inverse) must be within 2% of a round factor
PERSIST_TOLERANCE = 0.05  # next day's close must stay within 5% of the new level


def _matches_round_factor(x: float) -> bool:
    for f in SPLIT_FACTORS:
        if abs(x - f) / f <= SPLIT_TOLERANCE:
            return True
    return False


def _is_split_ratio(ratio: float) -> bool:
    """True if `ratio` (close / prev_close) or its inverse sits within
    SPLIT_TOLERANCE of one of SPLIT_FACTORS -- e.g. a 10:1 split drops the
    close to ~1/10th of the prior close (ratio ~= 0.1, inverse ~= 10)."""
    if ratio is None or ratio <= 0:
        return False
    return _matches_round_factor(ratio) or _matches_round_factor(1.0 / ratio)


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


_PLACEHOLDER_RE = re.compile(r"<[^>]*>|\{[^}]*\}|YYYYMMDD")


def _file_group_prefix_match(group_key: str, filename: str, rel_path: Optional[str] = None) -> bool:
    """True if `filename` plausibly belongs to a `file_groups` entry keyed
    by `group_key` (e.g. "quotes_YYYYMMDD.csv.gz", "executions_<date>.csv",
    "trades_{venue}_{pair}_YYYYMMDD.csv.gz"), matched on the stable literal
    prefix before any placeholder/wildcard token -- "{", "<", "*", or the
    literal "YYYYMMDD" example token, whichever comes first.

    When `group_key` itself spans a directory (e.g.
    "backtest_data/reit_onr_<date>/etf_1343_daily.csv", as opposed to a bare
    "quotes_YYYYMMDD.csv.gz" filename pattern) and `rel_path` is given, EVERY
    placeholder token ("<...>", "{...}", the literal "YYYYMMDD") is turned
    into a glob "*" and matched against the full path with fnmatch, not just
    a literal prefix -- a directory-qualified prefix alone is not enough to
    tell apart two group_keys that share the same placeholder-bearing
    directory but differ only in their basename (e.g. reit_onr's
    "backtest_data/reit_onr_<date>/etf_1343_daily.csv" vs.
    ".../etf_1343_dividends.csv": both reduce to the identical directory
    prefix "backtest_data/reit_onr_", so a prefix-only path check could not
    distinguish them and matched a file against the wrong file_group's
    (narrower) columns, misreporting real columns as
    'undocumented_in_schema')."""
    if "/" in group_key and rel_path is not None:
        pattern = _PLACEHOLDER_RE.sub("*", group_key)
        return fnmatch.fnmatch(rel_path.replace("\\", "/"), pattern)
    prefix = group_key.split("YYYYMMDD")[0].split("<")[0].split("*")[0].split("{")[0]
    prefix = prefix.strip()
    if not prefix:
        return False
    return filename.startswith(prefix.split("/")[-1].split(" ")[0])


_RANGE_COL_RE = re.compile(r"^(.*?)(\d+)\.\.(\d+)$")


def _expand_range_columns(names) -> set:
    """Expand a schema column key using the "prefix_N..M" shorthand (e.g.
    "bid_px_1..5") into the individual numbered column names it documents
    (bid_px_1, bid_px_2, ..., bid_px_5). Schemas use this shorthand purely
    for readability (see schema/bitflyer_tape.json's board_top5 columns);
    comparing it literally against a real CSV header -- which has no column
    actually named "bid_px_1..5" -- made every board_top5_*.csv.gz file
    misreport all 20 of its real level columns as undocumented, every time,
    while also claiming the 4 literal shorthand strings as "missing"."""
    out: set = set()
    for name in names:
        m = _RANGE_COL_RE.match(name)
        if m:
            base, lo, hi = m.group(1), int(m.group(2)), int(m.group(3))
            out.update(f"{base}{i}" for i in range(lo, hi + 1))
        else:
            out.add(name)
    return out


def schema_columns_for(schema: dict, filename: str, rel_path: Optional[str] = None) -> Optional[set]:
    """Flatten the documented column names relevant to this file: the
    dataset-level `columns` dict, plus any `file_groups` entry whose key
    (a filename pattern/example) appears as a substring of this filename.
    `rel_path` (the full path relative to the repo root) disambiguates
    file_groups keyed by a directory-qualified pattern -- see
    _file_group_prefix_match. Column keys using the "prefix_N..M" shorthand
    are expanded to individual column names -- see _expand_range_columns."""
    cols: set = set()
    top = schema.get("columns")
    if isinstance(top, dict):
        cols.update(top.keys())
    groups = schema.get("file_groups")
    if isinstance(groups, dict):
        matched_any = False
        for group_key, group_val in groups.items():
            if _file_group_prefix_match(group_key, filename, rel_path):
                gcols = group_val.get("columns") if isinstance(group_val, dict) else None
                if isinstance(gcols, dict):
                    cols.update(gcols.keys())
                    matched_any = True
        if not matched_any and not cols:
            return None
    if not cols:
        return None
    return _expand_range_columns(cols)


def schema_quality_for(schema: Optional[dict], filename: str, rel_path: Optional[str] = None) -> dict:
    """Merge dataset-level `quality` (group_by / unique_key) with any
    matched `file_groups` entry's own `quality` (file-group keys win,
    since bitflyer_tape/venues declare different keys per file shape
    within one schema). Returns {} if schema is None or nothing declared.
    `rel_path` disambiguates directory-qualified file_groups keys -- see
    _file_group_prefix_match."""
    if schema is None:
        return {}
    quality: dict = dict(schema.get("quality") or {})
    groups = schema.get("file_groups")
    if isinstance(groups, dict):
        for group_key, group_val in groups.items():
            if _file_group_prefix_match(group_key, filename, rel_path) and isinstance(group_val, dict):
                gq = group_val.get("quality")
                if isinstance(gq, dict):
                    quality.update(gq)
    return quality


# --------------------------------------------------------------------------
# per-file scan
# --------------------------------------------------------------------------


def _apply_check_switches(result: dict, quality: dict) -> dict:
    """Apply a schema's per-dataset (or per-file_group) quality-check
    switches to one file's already-computed check results:

      - quality.skip_checks: [check_name, ...] -- the named check does not
        apply to this dataset at all (e.g. an FX 1-minute file has no real
        `volume` concept, so zero_volume is structurally meaningless there;
        bitFlyer's 19:00-19:10 UTC maintenance window has no bearing on an
        FX reference feed). The check still runs (cheap, and keeps the code
        simple), but its result is dropped before it ever reaches
        QUALITY.json or a dashboard count -- it is not merely hidden, it
        never happened as far as any consumer of this report is concerned.
      - quality.informational_checks: [check_name, ...], or the literal
        string "all" (or boolean True) for every check that fires on this
        file -- the check is real and SHOULD keep firing (e.g. qa_synthetic
        is planted-defect fixtures whose entire purpose is to exercise
        these checks; a real dataset's genuinely-expected-but-still-worth-
        seeing pattern could use this too), but it is not a data problem to
        chase down. Marked with `"informational": true` on that check's
        result rather than removed, so counts/examples stay visible.

    Both keys are read from the SAME `quality` dict schema_quality_for()
    already resolves (dataset-level merged with any matching file_groups
    entry), so a file_group can, e.g., skip a check the dataset applies
    everywhere else.
    """
    skip = {c for c in (quality.get("skip_checks") or []) if isinstance(c, str)}
    for name in skip:
        result.pop(name, None)

    info = quality.get("informational_checks")
    if info is True or info == "all":
        info_names = set(result.keys())
    else:
        info_names = {c for c in (info or []) if isinstance(c, str)}
    for name in info_names:
        if name in result:
            result[name]["informational"] = True

    return result


def _compute_gaps(groups: dict) -> tuple[int, Optional[float], list]:
    """Per-group median-gap detection (see scan_file's `groups` state):
    a group's own median inter-row delta sets its threshold, so one group's
    cadence never contaminates another's (this is what quality.group_by
    exists to isolate). Returns (total_count, smallest per-group median
    seen, capped examples)."""
    gap_count = 0
    gap_median: Optional[float] = None
    gap_examples: list = []
    for gs in groups.values():
        deltas = gs["deltas"]
        if len(deltas) < 4:
            continue
        sorted_deltas = sorted(deltas)
        median = sorted_deltas[len(sorted_deltas) // 2]
        if median <= 0:
            continue
        gap_median = median if gap_median is None else min(gap_median, median)
        threshold = median * GAP_MULTIPLIER
        gaps_found = [(ri, d, ts) for ri, d, ts in gs["rows_with_dt"] if d > threshold]
        gap_count += len(gaps_found)
        if gaps_found and len(gap_examples) < MAX_EXAMPLES:
            gap_examples.extend(
                {"row": ri, "gap_seconds": d, "ts": ts}
                for ri, d, ts in sorted(gaps_found, key=lambda x: -x[1])[:MAX_EXAMPLES - len(gap_examples)]
            )
    return gap_count, gap_median, gap_examples


def _find_col(header_lower: list[str], candidates: list[str]) -> Optional[int]:
    for c in candidates:
        if c in header_lower:
            return header_lower.index(c)
    return None


def scan_file(root: Path, rel_path: str, schema: Optional[dict]) -> dict:
    """Run all applicable checks on one tabular file. Returns a dict of
    check_name -> {"count": int, "examples": [...]} for checks that fired
    at least once, plus (optionally) "missing_columns".

    schema is None for a file with no schema/*.json match at all ("schema
    _undefined" in run()'s report): in that case only the two STRUCTURAL
    checks (duplicate_keys, gaps) run -- the value-based checks below
    (extreme_return, non_monotonic, crossed_book, maintenance_window,
    zero_volume, split_candidate) need documented column meaning to avoid
    misfiring on a dataset we haven't actually looked at, so they are
    skipped rather than guessed at.

    A schema's `quality.group_by` (dataset- or file_group-level, see
    schema_quality_for) names columns that split one file into several
    independent time series (e.g. venues' quotes_*.csv.gz interleaves many
    (venue, pair) tickers) -- extreme_return / non_monotonic / gaps are
    then computed per group instead of over the raw row order, which would
    otherwise manufacture bogus "extreme returns" out of jumping between
    series. `quality.unique_key` names the columns that actually identify a
    row (e.g. bitflyer executions: several prints can share a timestamp) --
    duplicate_keys uses it instead of the timestamp column alone when set.
    """
    result: dict[str, dict] = {}
    quality: dict = {}  # overwritten below once the schema is resolved; stays {} on an early return/error
    p = root / rel_path
    kind = il.tabular_kind(p.name)
    if kind is None or not p.exists():
        return result
    fmt, gz = kind
    if fmt != "csv":
        return result  # jsonl checks are out of scope for these column-based rules

    structural_only = schema is None

    try:
        with il.open_text(p, gz) as f:
            reader = csv.reader(f)
            try:
                header = next(reader)
            except StopIteration:
                return result
            header_lower = [h.strip().lower() for h in header]

            if schema is not None:
                declared = schema_columns_for(schema, p.name, rel_path)
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

            quality = schema_quality_for(schema, p.name, rel_path)

            ts_idx = il.find_ts_column(header)
            spread_idx = _find_col(header_lower, ["spread_bps"])
            volume_idx = _find_col(header_lower, ["volume"])
            price_idx = _find_col(header_lower, PRICE_COL_CANDIDATES)
            ohlc_idx = None
            if all(c in header_lower for c in ("open", "high", "low", "close")):
                ohlc_idx = {c: header_lower.index(c) for c in ("open", "high", "low", "close")}
            is_daily_ohlc = ohlc_idx is not None and ts_idx is not None and header_lower[ts_idx] == "date"

            # -- grouping (quality.group_by): only used to split extreme_return /
            # non_monotonic / gaps into independent per-series tracking; falls
            # back to a single implicit group ("_all") when undeclared or the
            # named columns aren't actually in this file's header.
            group_by_cols = [c for c in (quality.get("group_by") or []) if isinstance(c, str)]
            group_idxs = (
                [header_lower.index(c.lower()) for c in group_by_cols]
                if group_by_cols and all(c.lower() in header_lower for c in group_by_cols)
                else []
            )

            def _group_key(row: list[str]):
                if not group_idxs:
                    return "_all"
                return tuple(row[i] if i < len(row) else "" for i in group_idxs)

            # -- duplicate key (quality.unique_key): declared columns win;
            # otherwise a schema_undefined file auto-detects the full row
            # (an exact repeated row, not merely a repeated timestamp);
            # otherwise fall back to the timestamp column alone (unchanged
            # legacy behaviour for schemas that never opted in).
            unique_key_cols = [c for c in (quality.get("unique_key") or []) if isinstance(c, str)]
            key_idxs = (
                [header_lower.index(c.lower()) for c in unique_key_cols]
                if unique_key_cols and all(c.lower() in header_lower for c in unique_key_cols)
                else []
            )
            if key_idxs:
                dup_key_mode = "declared"
            elif structural_only:
                dup_key_mode = "auto_full_row"
            elif ts_idx is not None:
                dup_key_mode = "ts"
            else:
                dup_key_mode = None

            def _dup_key(row: list[str]):
                if dup_key_mode == "declared":
                    return tuple(row[i] if i < len(row) else "" for i in key_idxs)
                if dup_key_mode == "auto_full_row":
                    return tuple(row)
                if dup_key_mode == "ts":
                    return row[ts_idx] if ts_idx < len(row) else None
                return None

            seen_keys: dict = {}
            dup_examples: list = []
            crossed_examples: list = []
            crossed_count = 0
            maint_examples: list = []
            maint_count = 0
            zero_vol_examples: list = []
            zero_vol_count = 0
            daily_rows: list[tuple[int, Optional[str], Optional[float]]] = []

            # per-group state for non_monotonic / extreme_return / gaps
            groups: dict = {}

            def _g(gkey):
                return groups.setdefault(gkey, {
                    "prev_dt": None, "prev_price": None,
                    "deltas": [], "rows_with_dt": [],
                })

            non_monotonic_examples: list = []
            non_monotonic_count = 0
            extreme_examples: list = []
            extreme_count = 0

            row_i = 0
            for row in reader:
                row_i += 1
                gkey = _group_key(row)
                gs = _g(gkey)
                group_tag = {} if not group_idxs else {"group": dict(zip(group_by_cols, gkey))}

                # duplicate keys (structural -- ungrouped, whole-file)
                if dup_key_mode is not None:
                    kv = _dup_key(row)
                    non_empty = kv not in (None, "") if not isinstance(kv, tuple) else any(v not in (None, "") for v in kv)
                    if non_empty:
                        seen_keys[kv] = seen_keys.get(kv, 0) + 1
                        if seen_keys[kv] == 2 and len(dup_examples) < MAX_EXAMPLES:
                            ex = {"row": row_i}
                            if dup_key_mode == "ts":
                                ex["ts"] = kv
                            else:
                                ex["key"] = list(kv)
                            dup_examples.append(ex)

                if ts_idx is not None and ts_idx < len(row):
                    raw_ts = row[ts_idx]
                    dt = il.parse_ts(raw_ts)
                    if dt is not None:
                        if not structural_only and gs["prev_dt"] is not None:
                            if dt < gs["prev_dt"]:
                                non_monotonic_count += 1
                                if len(non_monotonic_examples) < MAX_EXAMPLES:
                                    non_monotonic_examples.append(
                                        {"row": row_i, "prev_ts": gs["prev_dt"].isoformat(), "ts": dt.isoformat(), **group_tag}
                                    )
                        if gs["prev_dt"] is not None:
                            delta = (dt - gs["prev_dt"]).total_seconds()
                            if delta > 0:
                                gs["deltas"].append(delta)
                                gs["rows_with_dt"].append((row_i, delta, dt.isoformat()))
                        gs["prev_dt"] = dt

                if structural_only:
                    continue  # everything below is a value-based check needing a documented schema

                # crossed book
                if spread_idx is not None and spread_idx < len(row):
                    try:
                        sv = float(row[spread_idx])
                    except (ValueError, TypeError):
                        sv = None
                    if sv is not None and (sv <= 0 or sv > CROSSED_SPREAD_MAX_BPS):
                        crossed_count += 1
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
                                maint_count += 1
                                if len(maint_examples) < MAX_EXAMPLES:
                                    maint_examples.append({"row": row_i, "ts": dt2.isoformat(), "value": o})

                        if is_daily_ohlc:
                            try:
                                daily_close = float(row[ohlc_idx["close"]])
                            except (ValueError, TypeError, IndexError):
                                daily_close = None
                            daily_rows.append((row_i, dt2.isoformat(), daily_close))

                # extreme single-step return (per group)
                if price_idx is not None and price_idx < len(row):
                    try:
                        pv = float(row[price_idx])
                    except (ValueError, TypeError):
                        pv = None
                    if pv is not None:
                        if gs["prev_price"] not in (None, 0) and pv != 0:
                            ret = (pv - gs["prev_price"]) / gs["prev_price"]
                            if abs(ret) > EXTREME_RETURN_FRAC:
                                extreme_count += 1
                                if len(extreme_examples) < MAX_EXAMPLES:
                                    extreme_examples.append(
                                        {"row": row_i, "prev": gs["prev_price"], "value": pv, "return": ret, **group_tag}
                                    )
                        gs["prev_price"] = pv

                # zero volume
                if volume_idx is not None and volume_idx < len(row):
                    try:
                        vv = float(row[volume_idx])
                    except (ValueError, TypeError):
                        vv = None
                    if vv == 0.0:
                        zero_vol_count += 1
                        if len(zero_vol_examples) < MAX_EXAMPLES:
                            zero_vol_examples.append({"row": row_i, "ts": row[ts_idx] if ts_idx is not None and ts_idx < len(row) else None})

            dup_count = sum(1 for v in seen_keys.values() if v > 1)
            if dup_count:
                result["duplicate_keys"] = {"count": dup_count, "examples": dup_examples}

            if structural_only:
                gap_count, gap_median, gap_examples = _compute_gaps(groups)
                if gap_count:
                    result["gaps"] = {"count": gap_count, "median_gap_seconds": gap_median, "examples": gap_examples}
                return _apply_check_switches(result, quality)

            if non_monotonic_count:
                result["non_monotonic"] = {"count": non_monotonic_count, "examples": non_monotonic_examples}
            if crossed_count:
                result["crossed_book"] = {"count": crossed_count, "examples": crossed_examples}
            if maint_count:
                result["maintenance_window"] = {"count": maint_count, "examples": maint_examples}
            if extreme_count:
                result["extreme_return"] = {"count": extreme_count, "examples": extreme_examples}
            if zero_vol_count:
                result["zero_volume"] = {"count": zero_vol_count, "examples": zero_vol_examples}

            if is_daily_ohlc and len(daily_rows) >= 3:
                split_examples: list = []
                split_count = 0
                for i in range(1, len(daily_rows) - 1):
                    prev_i, _prev_ts, prev_close = daily_rows[i - 1]
                    cur_i, cur_ts, cur_close = daily_rows[i]
                    _next_i, _next_ts, next_close = daily_rows[i + 1]
                    if prev_close in (None, 0) or cur_close in (None, 0) or next_close is None:
                        continue
                    ratio = cur_close / prev_close
                    if not _is_split_ratio(ratio):
                        continue
                    if abs(next_close / cur_close - 1.0) > PERSIST_TOLERANCE:
                        continue  # reverts back next day -- a one-day round trip, not a split
                    if i - 2 >= 0:
                        prev2_close = daily_rows[i - 2][2]
                        # the pre-jump level must itself have been established
                        # (not merely a single-day glitch bar reverting on this
                        # very transition) -- otherwise the "revert" leg of a
                        # one-day bad print would also look like a persistent
                        # split from this side.
                        if prev2_close not in (None, 0) and abs(prev_close / prev2_close - 1.0) > PERSIST_TOLERANCE:
                            continue
                    split_count += 1
                    if len(split_examples) < MAX_EXAMPLES:
                        split_examples.append(
                            {"row": cur_i, "ts": cur_ts, "prev_close": prev_close, "close": cur_close, "ratio": ratio}
                        )
                if split_count:
                    result["split_candidate"] = {"count": split_count, "examples": split_examples}

            gap_count, gap_median, gap_examples = _compute_gaps(groups)
            if gap_count:
                result["gaps"] = {
                    "count": gap_count,
                    "median_gap_seconds": gap_median,
                    "examples": gap_examples,
                }
    except (OSError, gzip.BadGzipFile, csv.Error) as exc:
        result["scan_error"] = {"count": 1, "examples": [{"error": f"{type(exc).__name__}: {exc}"}]}

    return _apply_check_switches(result, quality)


# --------------------------------------------------------------------------
# driver
# --------------------------------------------------------------------------


def run(root: Path) -> dict:
    latest_path = root / "data" / "INTAKE_latest.json"
    index = il.load_latest(latest_path)
    schemas = load_schemas(root)

    datasets: dict[str, dict] = {}
    schema_undefined: list[str] = []

    for rel_path, rec in sorted(index.items()):
        if rec.get("status") != "present":
            continue
        if il.tabular_kind(Path(rel_path).name) is None:
            continue

        schema = match_dataset(rel_path, schemas)
        if schema is None:
            schema_undefined.append(rel_path)
            dataset_name = "schema_undefined"
        else:
            dataset_name = schema.get("dataset", "schema_undefined")

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
            if payload.get("informational"):
                # quality.informational_checks (see _apply_check_switches):
                # surfaced at the aggregate level too, not just buried in
                # per-file examples, so a consumer can tell "this whole
                # check is expected-by-design for this dataset" without
                # inspecting individual examples.
                agg["informational"] = True
            if len(agg["examples"]) < MAX_EXAMPLES:
                agg["examples"].append({"path": rel_path, **{k: v for k, v in payload.items() if k != "count"}})

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ledger_source": str(latest_path.relative_to(root)) if latest_path.exists() else None,
        "datasets": datasets,
        "schema_undefined_files": sorted(set(schema_undefined)),
        "schema_undefined_count": len(set(schema_undefined)),
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

    if report["schema_undefined_files"]:
        print(f"\n{len(report['schema_undefined_files'])} tabular files not matched to any schema/*.json dataset "
              f"(structural checks only -- see schema_undefined_files in QUALITY.json)")

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
