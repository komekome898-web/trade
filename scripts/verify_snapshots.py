#!/usr/bin/env python3
"""Verify the integrity of everything under backtest_data/ (DATA_QA_CHECKLIST
item 5).

For every "unit" under backtest_data/ -- each immediate subdirectory
(recursively, so nested files like ``raw/foo.csv`` are covered) plus the
top-level loose files directly inside backtest_data/ itself (treated as one
more unit) -- this script:

  - if the unit already has an ``MD5SUMS`` file: recomputes the md5 of every
    file it lists and compares. Mismatches and files listed but missing on
    disk are reported. Files present in the unit but NOT listed in MD5SUMS
    are reported separately (``extra``) -- not a failure by itself, just
    visibility.
  - if the unit has no ``MD5SUMS`` file: computes one from the files
    present right now and WRITES it (new file only). Reported as
    "newly_sealed". This never reads, moves, or modifies any existing data
    file -- only ever hashes (read-only) and writes a brand-new MD5SUMS.

It then cross-checks, where a path resolves, the md5 recorded in the intake
ledger (``data/INTAKE_latest.json``, preferring the operator's shared copy
``paper_logs/INTAKE_latest.json`` when newer, via
``bot.monitoring.gates.shared_or_local`` -- same rule the dashboard uses)
against the md5 this script just computed for that same file.

Output: ``data/SNAPSHOT_VERIFY.json`` (full detail) + a console summary.
Exit code: 1 if any listed file is missing, any md5 mismatches (against its
own MD5SUMS or against the ledger); 0 otherwise (newly-sealed units and
"extra" untracked files do not fail the run).

Safety (CLAUDE.md): every file under backtest_data/ is only ever opened for
reading. The only write this script performs is creating a brand-new
MD5SUMS file in a unit that does not already have one (mkdir/open with
exist_ok=False-equivalent guard -- never overwrites an existing MD5SUMS,
never touches any other file).

Usage:
    python scripts/verify_snapshots.py                # verify + seal + report
    python scripts/verify_snapshots.py --root /path    # different repo root
    python scripts/verify_snapshots.py --no-write      # dry run: report
                                                        # missing seals but
                                                        # do not create them
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
import intake_ledger as il  # noqa: E402 -- reuse md5_of

SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
from bot.monitoring.gates import shared_or_local  # noqa: E402

MD5SUMS_NAME = "MD5SUMS"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _iter_unit_files(unit_dir: Path) -> list[Path]:
    """Files inside unit_dir, recursively, excluding MD5SUMS itself."""
    out = []
    for p in sorted(unit_dir.rglob("*")):
        if p.is_file() and p.name != MD5SUMS_NAME:
            out.append(p)
    return out


def _top_level_loose_files(root: Path) -> list[Path]:
    """Files directly inside backtest_data/ (not in any subdirectory)."""
    return sorted(p for p in root.iterdir() if p.is_file() and p.name != MD5SUMS_NAME)


def _parse_md5sums(path: Path) -> dict[str, str]:
    """rel path (posix, relative to the unit dir) -> expected md5."""
    entries: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.rstrip("\n")
        if not line.strip():
            continue
        # standard md5sum format: "<hex>  <path>" (two spaces, or one +
        # optional '*' for binary mode)
        parts = line.split(None, 1)
        if len(parts) != 2:
            continue
        digest, rel = parts
        rel = rel.lstrip("*").strip()
        entries[rel] = digest.strip().lower()
    return entries


def _write_md5sums(unit_dir: Path, rel_to_md5: dict[str, str]) -> None:
    lines = [f"{md5}  {rel}\n" for rel, md5 in sorted(rel_to_md5.items())]
    (unit_dir / MD5SUMS_NAME).write_text("".join(lines), encoding="utf-8")


def verify_unit(unit_dir: Path, unit_label: str, files: list[Path],
                 write_seal: bool) -> dict[str, Any]:
    """files: the file paths that belong to this unit (already resolved,
    excluding MD5SUMS). Returns a result dict; never mutates any file other
    than possibly creating a brand-new MD5SUMS."""
    md5sums_path = unit_dir / MD5SUMS_NAME
    rel_of = {f: f.relative_to(unit_dir).as_posix() for f in files}
    actual_md5: dict[str, str] = {rel_of[f]: il.md5_of(f) for f in files}

    result: dict[str, Any] = {
        "unit": unit_label,
        "md5sums_path": str(md5sums_path.relative_to(REPO_ROOT)) if _is_under(md5sums_path, REPO_ROOT) else str(md5sums_path),
        "file_count": len(files),
    }

    if md5sums_path.exists():
        expected = _parse_md5sums(md5sums_path)
        mismatches = []
        missing = []
        matched = 0
        seen_rel = set(actual_md5.keys())
        for rel, exp_md5 in expected.items():
            if rel not in seen_rel:
                missing.append(rel)
                continue
            act = actual_md5[rel]
            if act != exp_md5:
                mismatches.append({"file": rel, "expected": exp_md5, "actual": act})
            else:
                matched += 1
        extra = sorted(seen_rel - set(expected.keys()))
        result.update({
            "status": "verified" if not mismatches and not missing else "mismatch",
            "checked": len(expected),
            "matched": matched,
            "mismatches": mismatches,
            "missing": missing,
            "extra": extra,
        })
    elif not files:
        result.update({
            "status": "empty",
            "checked": 0, "matched": 0,
            "mismatches": [], "missing": [], "extra": [],
            "sealed_file_count": 0,
        })
    else:
        result.update({
            "status": "newly_sealed" if write_seal else "unsealed_dry_run",
            "checked": 0,
            "matched": 0,
            "mismatches": [],
            "missing": [],
            "extra": [],
            "sealed_file_count": len(files),
        })
        if write_seal:
            _write_md5sums(md5sums_path.parent, actual_md5)

    result["_actual_md5"] = actual_md5  # for ledger cross-check; stripped before dump if caller wants
    return result


def _is_under(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def discover_units(bt_root: Path) -> list[tuple[Path, str, list[Path]]]:
    """Returns (unit_dir_for_md5sums_placement, label, files) tuples.

    The top-level loose-files unit uses bt_root itself as the MD5SUMS
    placement dir but only its direct files (no recursion into
    subdirectories, which are their own units).
    """
    units: list[tuple[Path, str, list[Path]]] = []
    loose = _top_level_loose_files(bt_root)
    units.append((bt_root, "backtest_data (top-level files)", loose))
    for sub in sorted(p for p in bt_root.iterdir() if p.is_dir()):
        files = _iter_unit_files(sub)
        units.append((sub, str(sub.relative_to(bt_root)), files))
    return units


def cross_check_ledger(root: Path, unit_results: list[dict[str, Any]]) -> dict[str, Any]:
    """Compare each verified file's freshly-computed md5 against the intake
    ledger's recorded md5 for that same repo-relative path, where present."""
    ledger_rel = "data/INTAKE_latest.json"
    ledger_path = shared_or_local(root, ledger_rel)
    out: dict[str, Any] = {
        "ledger_path": str(ledger_path.relative_to(root)) if _is_under(ledger_path, root) else str(ledger_path),
        "checked": 0,
        "mismatches": [],
    }
    if not ledger_path.exists():
        out["note"] = "ledger not found; cross-check skipped"
        return out
    try:
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        out["note"] = f"ledger unreadable: {type(exc).__name__}: {exc}"
        return out

    checked = 0
    mismatches = []
    for res in unit_results:
        unit_dir_rel = res["_unit_dir_rel"]  # posix, relative to backtest_data
        actual_md5 = res.pop("_actual_md5", {})
        for rel, md5 in actual_md5.items():
            if unit_dir_rel:
                full_rel = f"backtest_data/{unit_dir_rel}/{rel}"
            else:
                full_rel = f"backtest_data/{rel}"
            entry = ledger.get(full_rel)
            if not entry:
                continue
            ledger_md5 = entry.get("md5")
            if not ledger_md5:
                continue
            checked += 1
            if ledger_md5 != md5:
                mismatches.append({
                    "file": full_rel, "snapshot_md5": md5, "ledger_md5": ledger_md5,
                })
    out["checked"] = checked
    out["mismatches"] = mismatches
    return out


def run(root: Path, write_seal: bool) -> dict[str, Any]:
    bt_root = root / "backtest_data"
    unit_results = []
    if bt_root.is_dir():
        for unit_dir, label, files in discover_units(bt_root):
            res = verify_unit(unit_dir, label, files, write_seal)
            res["_unit_dir_rel"] = "" if unit_dir == bt_root else unit_dir.relative_to(bt_root).as_posix()
            unit_results.append(res)

    ledger_check = cross_check_ledger(root, unit_results)

    for res in unit_results:
        res.pop("_unit_dir_rel", None)
        res.pop("_actual_md5", None)

    total_mismatches = sum(len(r["mismatches"]) for r in unit_results)
    total_missing = sum(len(r["missing"]) for r in unit_results)
    total_extra = sum(len(r["extra"]) for r in unit_results)
    newly_sealed = sum(1 for r in unit_results if r["status"] == "newly_sealed")
    verified = sum(1 for r in unit_results if r["status"] == "verified")

    report = {
        "generated_at": _now_iso(),
        "backtest_data_root": "backtest_data",
        "units": unit_results,
        "ledger_cross_check": ledger_check,
        "summary": {
            "unit_count": len(unit_results),
            "verified": verified,
            "newly_sealed": newly_sealed,
            "mismatch_units": sum(1 for r in unit_results if r["status"] == "mismatch"),
            "total_mismatches": total_mismatches,
            "total_missing": total_missing,
            "total_extra_untracked": total_extra,
            "ledger_mismatches": len(ledger_check["mismatches"]),
        },
    }
    ok = (total_mismatches == 0 and total_missing == 0
          and len(ledger_check["mismatches"]) == 0)
    report["ok"] = ok
    return report


def print_summary(report: dict[str, Any]) -> None:
    s = report["summary"]
    print(f"verify_snapshots: {s['unit_count']} units "
          f"({s['verified']} verified, {s['newly_sealed']} newly_sealed, "
          f"{s['mismatch_units']} with mismatches)")
    for r in report["units"]:
        if r["status"] == "newly_sealed":
            print(f"  [newly_sealed] {r['unit']}: sealed {r['sealed_file_count']} files -> {r['md5sums_path']}")
        elif r["status"] == "unsealed_dry_run":
            print(f"  [dry_run] {r['unit']}: {r['sealed_file_count']} files, no MD5SUMS -- would seal (--no-write)")
        elif r["status"] == "empty":
            print(f"  [empty] {r['unit']}: no files, no MD5SUMS")
        elif r["status"] == "mismatch":
            print(f"  [MISMATCH] {r['unit']}: {len(r['mismatches'])} mismatched, "
                  f"{len(r['missing'])} missing, {len(r['extra'])} extra-untracked")
            for m in r["mismatches"]:
                print(f"      mismatch: {m['file']} expected={m['expected']} actual={m['actual']}")
            for miss in r["missing"]:
                print(f"      missing: {miss}")
        else:
            extra_note = f" ({len(r['extra'])} extra-untracked)" if r["extra"] else ""
            print(f"  [ok] {r['unit']}: {r['matched']}/{r['checked']} matched{extra_note}")
    lc = report["ledger_cross_check"]
    print(f"ledger cross-check ({lc['ledger_path']}): {lc['checked']} files checked, "
          f"{len(lc['mismatches'])} mismatches")
    for m in lc["mismatches"]:
        print(f"      ledger mismatch: {m['file']} snapshot={m['snapshot_md5']} ledger={m['ledger_md5']}")
    print(f"overall: {'OK' if report['ok'] else 'FAIL'}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=str(REPO_ROOT), help="repo root (default: this repo)")
    ap.add_argument("--out", default=None, help="output json path (default: <root>/data/SNAPSHOT_VERIFY.json)")
    ap.add_argument("--no-write", action="store_true",
                     help="dry run: report missing seals but do not create MD5SUMS files")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    report = run(root, write_seal=not args.no_write)

    out_path = Path(args.out) if args.out else root / "data" / "SNAPSHOT_VERIFY.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print_summary(report)
    print(f"wrote {out_path}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
