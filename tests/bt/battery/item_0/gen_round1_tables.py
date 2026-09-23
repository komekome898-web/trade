#!/usr/bin/env python3
"""Round-1 comparison tables for item 0 (核), 資料係.

Reads the raw `run_battery.py --out` TSVs already produced for this round
(current_impl / new_impl / the 4 opponents / mutant, each run with
`--repeat 2`) and writes 6 blind two-row Markdown tables under
`docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/round_1/`:

    current_1 (A=new_impl,    B=current_impl)
    current_2 (A=current_impl,B=new_impl)      -- swapped
    survey_1  (A=new_impl,    B=survey side)
    survey_2  (A=survey side, B=new_impl)      -- swapped
    mutant_1  (A=new_impl,    B=mutant)
    mutant_2  (A=mutant,      B=new_impl)      -- swapped

This script writes ONLY the table (script output); no prose goes into the
Markdown files (delegation doc Sec.3 "比較の表" + this round's instruction
"文章を書かない。表はスクリプトの出力だけ"). Which file is which pairing is
returned by this script on stdout, not written into any file, so the judges
stay blind.

Cell vocabulary (delegation doc Sec.3, exactly these five):
    一致 / 不一致(値) / 対応なし / 実行の記録なし / 2回の一致
`known_answer` scenes use the first four (taken straight from run_battery.py's
own `verdict` column). `capability` scenes have no known answer, so the only
meaningful measurement left is run-to-run reproducibility: "2回の一致" (both
runs agreed) or "2回不一致" (they didn't) when the target could actually run
the scene (status=="ok"); "対応なし"/"実行の記録なし" carry over unchanged.
`status=="error"` (an uncaught exception) is folded into 不一致(値) for both
kinds -- run_battery.py's own `_classify_known_answer` already does this for
known_answer rows.
"""
from __future__ import annotations

import csv
import random
import string
import sys
from pathlib import Path

_ITEM0_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _ITEM0_DIR.parents[3]
sys.path.insert(0, str(_ITEM0_DIR))
from scenes import SCENES  # noqa: E402

_SCRATCH = Path(
    "/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/item_0"
)
_OUT_DIR = _REPO_ROOT / "docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/round_1"

_OPP_TARGETS = ["opp_ziplime", "opp_zipline_reloaded", "opp_lib_pybroker", "opp_qf_lib"]

FIELDNAMES = ["target", "scene_id", "viewpoint", "kind", "status", "output", "expected",
              "verdict", "match_across_runs", "detail"]


def _load(target: str) -> dict[str, dict]:
    path = _SCRATCH / f"round1_{target}.tsv"
    rows: dict[str, dict] = {}
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            rows[row["scene_id"]] = row
    return rows


def _cell(row: dict | None) -> str:
    """One TSV row -> one of the 5 delegation-doc cell values."""
    if row is None:
        return "実行の記録なし"
    kind = row["kind"]
    status = row["status"]
    match = row["match_across_runs"] == "True"
    if kind == "known_answer":
        v = row["verdict"]
        # run_battery.py already emits exactly one of the 4 known_answer words
        return v
    # capability
    if status == "not_supported":
        return "対応なし"
    if status == "no_record":
        return "実行の記録なし"
    if status == "error":
        return "不一致(値)"
    # status == "ok" -- the only axis left to report is run-to-run agreement
    return "2回の一致" if match else "2回不一致"


_RANK = {  # higher = "better showing" for whichever side is being judged
    "一致": 3,
    "2回の一致": 3,
    "対応なし": 2,
    "2回不一致": 1,
    "不一致(値)": 1,
    "実行の記録なし": 0,
}


def _best_survey_row(scene_id: str, opp_rows: dict[str, dict[str, dict]]) -> dict | None:
    """Among the 4 opponents' rows for this scene, keep the one 資料係ing the
    strongest showing (delegation doc Sec.3: "場面ごとに動かせた道具のうち
    最も良い結果を1行に寄せる" -- picking the toughest available opponent
    per scene is the direction that makes 新実装 harder to win against, not
    easier)."""
    candidates = []
    for target in _OPP_TARGETS:
        row = opp_rows[target].get(scene_id)
        if row is None or row["status"] == "no_record":
            continue  # "動かせた道具のうち" excludes 実行の記録なし entirely
        candidates.append(row)
    if not candidates:
        return None
    candidates.sort(key=lambda r: _RANK[_cell(r)], reverse=True)
    return candidates[0]


def _rand_suffix() -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=6))


def _write_table(filename_stem: str, a_rows_by_scene: dict, b_rows_by_scene: dict) -> Path:
    header = "| # | 場面 | A | B |\n|---|---|---|---|\n"
    lines = [header]
    for i, scene in enumerate(SCENES, start=1):
        a = _cell(a_rows_by_scene.get(scene.id))
        b = _cell(b_rows_by_scene.get(scene.id))
        lines.append(f"| {i} | {scene.id} | {a} | {b} |\n")
    _OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = _OUT_DIR / f"{filename_stem}.md"
    path.write_text("".join(lines), encoding="utf-8")
    return path


def main() -> None:
    current_rows = _load("current_impl")
    new_rows = _load("new_impl")
    mutant_rows = _load("mutant")
    opp_rows = {t: _load(t) for t in _OPP_TARGETS}
    survey_rows = {
        scene.id: _best_survey_row(scene.id, opp_rows) for scene in SCENES
    }

    pairs = {
        "current_1": (new_rows, current_rows),   # A=new_impl, B=current_impl
        "current_2": (current_rows, new_rows),   # swapped
        "survey_1": (new_rows, survey_rows),     # A=new_impl, B=survey side
        "survey_2": (survey_rows, new_rows),     # swapped
        "mutant_1": (new_rows, mutant_rows),     # A=new_impl, B=mutant
        "mutant_2": (mutant_rows, new_rows),     # swapped
    }

    tables: dict[str, str] = {}
    for key, (a_rows, b_rows) in pairs.items():
        suffix = _rand_suffix()
        stem = f"表_{suffix}"
        path = _write_table(stem, a_rows, b_rows)
        tables[key] = str(path.relative_to(_REPO_ROOT))

    for key, rel_path in tables.items():
        print(f"{key}\t{rel_path}")


if __name__ == "__main__":
    main()
