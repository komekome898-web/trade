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

Cell shape (delegation doc Sec.3 "比較の表", exactly as specified): each
cell carries TWO independent readings, joined by "・":
    正しさ = 一致 / 対応なし / 不一致(値) / 結果なし   (one of these 4)
    再現   = 2回の実行で同じ / 2回で違う(値) / 結果なし (one of these 3)
e.g. "不一致(値)・2回で同じ" = "同じ誤りを2回返した" (the delegation doc's
own worked example).

2026-09-23 fix: this file's round-1 build gave known_answer rows only 正しさ
and capability rows only 再現, i.e. it silently dropped 正しさ for every
capability scene and graded them purely by whether two runs agreed with
EACH OTHER (not with any correct answer) -- exactly the self-report problem
場面集の規則1 was written to close, reintroduced at the table-generation
step even after `run_battery.py`'s own `_grade` was fixed to compute a real
正しさ for both kinds. Both axes are independent and orthogonal for BOTH
kinds now: 正しさ always comes from `run_battery.py`'s `verdict` column
(which itself independently checks `output` against `scenes.py`'s
`expected` -- see that module's docstring), 再現 always comes from its
`match_across_runs` column.
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


def _correctness(row: dict) -> str:
    """正しさ axis -- identical rule for known_answer AND capability rows
    (both are graded by run_battery.py's `_grade` against `scenes.py`'s
    `expected`; `verdict` is never derived from `status`/`match` alone
    here -- see this module's docstring)."""
    return row["verdict"]


def _reproducibility(row: dict) -> str:
    """再現 axis -- independent of 正しさ. `結果なし` when the target could
    not even be invoked this scene (no basis to compare two runs)."""
    if row["status"] == "no_record":
        return "結果なし"
    return "2回の実行で同じ" if row["match_across_runs"] == "True" else "2回で違う(値)"


def _cell(row: dict | None) -> str:
    """One TSV row -> "正しさ・再現" (delegation doc Sec.3 "比較の表")."""
    if row is None:
        return "結果なし・結果なし"
    return f"{_correctness(row)}・{_reproducibility(row)}"


_RANK = {  # higher = "better showing" for whichever side is being judged;
    # keyed by 正しさ alone (再現 breaks ties within a rank via a second
    # pass below), per 場面集の規則5's ordering: 一致 > 対応なし > 不一致(値) > 結果なし
    "一致": 3,
    "対応なし": 2,
    "不一致(値)": 1,
    "結果なし": 0,
}


def _rank(row: dict) -> tuple[int, int]:
    correctness_rank = _RANK[_correctness(row)]
    reproducible_rank = 1 if _reproducibility(row) == "2回の実行で同じ" else 0
    return (correctness_rank, reproducible_rank)


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
    candidates.sort(key=_rank, reverse=True)
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
