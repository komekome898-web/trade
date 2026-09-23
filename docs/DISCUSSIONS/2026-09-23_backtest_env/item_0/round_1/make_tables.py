#!/usr/bin/env python3
"""Build the six blinded comparison tables of item 0, round 1, from the
battery runs (delegation doc §3 "比較の表", battery rules 3-5).

Input: `runs/<target>.tsv`, written by
`tests/bt/battery/item_0/run_battery.py --target <target> --out ...`
(each target run twice by the runner; correctness / reproducibility are
graded there, never here).

Output: six files `表_<6 random chars>.md` in this directory, and on stdout
the mapping file name -> table id (current_1 .. mutant_2). The mapping is
not written to any file here. Rows are "A" and "B"; columns are scenes,
grouped by viewpoint; each cell has two fields, correctness and
reproducibility. The survey side is one row: per scene, the best result of
every survey target that ran (order below), without saying which target.

Best order (battery rule 5): correctness 正解と一致 > 対応なし > 不一致 >
結果なし; equal correctness -> 2 回の実行で同じ above 2 回で違う above
結果なし; still equal -> the first target name in sorted order (a fixed
rule so the output is deterministic).

    python3 make_tables.py [--survey-note TEXT] [--seed N]
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import string
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
sys.path.insert(0, str(REPO / "tests" / "bt" / "battery" / "item_0"))
from scenes import SCENES, VIEWPOINTS  # noqa: E402

RUNS = HERE / "runs"
C_RANK = {"正解と一致": 0, "対応なし": 1, "不一致": 2, "結果なし": 3}
R_RANK = {"2 回の実行で同じ": 0, "2 回で違う": 1, "結果なし": 2}
SURVEY_PREFIXES = ("opp_", "repro_")


def load(target: str) -> dict[str, dict]:
    with (RUNS / f"{target}.tsv").open(encoding="utf-8") as f:
        rows = {r["scene_id"]: r for r in csv.DictReader(f, delimiter="\t")}
    missing = [s.id for s in SCENES if s.id not in rows]
    if missing:
        raise SystemExit(f"{target}: scenes missing from the run: {missing}")
    return rows


def best(rows_by_target: dict[str, dict[str, dict]]) -> dict[str, dict]:
    out = {}
    for sc in SCENES:
        cands = sorted(rows_by_target.items(), key=lambda kv: (
            C_RANK[kv[1][sc.id]["correctness"]], R_RANK[kv[1][sc.id]["reproducibility"]], kv[0]))
        out[sc.id] = cands[0][1][sc.id]
    return out


def _graded_part(output_json: str, expected_json: str) -> str:
    """The value that was graded: for a dict expectation, only its keys."""
    out = json.loads(output_json)
    exp = json.loads(expected_json)
    if isinstance(exp, dict) and isinstance(out, dict):
        out = {k: out.get(k) for k in exp}
    return json.dumps(out, ensure_ascii=False, sort_keys=True)


def cell(r: dict) -> str:
    c = r["correctness"]
    if c == "不一致":
        c = f"不一致({_graded_part(r['output_1'], r['expected'])})"
    rep = r["reproducibility"]
    if rep == "2 回で違う":
        rep = (f"2 回で違う(1 回目 {r['status_1']} {_graded_part(r['output_1'], r['expected'])} / "
               f"2 回目 {r['status_2']} {_graded_part(r['output_2'], r['expected'])})")
    return f"正しさ: {c}<br>再現: {rep}"


def esc(s: str) -> str:
    return s.replace("|", "\\|")


def render(a: dict[str, dict], b: dict[str, dict], note: str) -> str:
    lines = ["# 比較の表(項目 0、第 1 周)", "",
             "A と B は名前を伏せた 2 つの対象。場面の定義は `tests/bt/battery/item_0/DEFINITIONS.md`。",
             "各セルは 2 つの欄: 正しさ(正解と一致 / 対応なし / 不一致(値)/ 結果なし)と、"
             "再現(2 回の実行で同じ / 2 回で違う(値)/ 結果なし)。",
             "良い順: 正解と一致 > 対応なし > 不一致 > 結果なし。正しさが同じなら「2 回の実行で同じ」が上。", ""]
    if note:
        lines += [f"注記: {note}", ""]
    lines += ["## 観点ごとの「正解と一致」の数", "",
              "| 対象 | " + " | ".join(VIEWPOINTS) + " | 計 |",
              "|---" * (len(VIEWPOINTS) + 2) + "|"]
    for label, rows in (("A", a), ("B", b)):
        cells, tot_hit, tot_n = [], 0, 0
        for vp in VIEWPOINTS:
            ids = [s.id for s in SCENES if s.viewpoint == vp]
            hit = sum(rows[i]["correctness"] == "正解と一致" for i in ids)
            cells.append(f"{hit} / {len(ids)}")
            tot_hit, tot_n = tot_hit + hit, tot_n + len(ids)
        lines.append(f"| {label} | " + " | ".join(cells) + f" | {tot_hit} / {tot_n} |")
    lines.append("")
    lines += ["## 観点ごとの「2 回の実行で同じ」の数", "",
              "| 対象 | " + " | ".join(VIEWPOINTS) + " | 計 |",
              "|---" * (len(VIEWPOINTS) + 2) + "|"]
    for label, rows in (("A", a), ("B", b)):
        cells, tot_hit, tot_n = [], 0, 0
        for vp in VIEWPOINTS:
            ids = [s.id for s in SCENES if s.viewpoint == vp]
            hit = sum(rows[i]["reproducibility"] == "2 回の実行で同じ" for i in ids)
            cells.append(f"{hit} / {len(ids)}")
            tot_hit, tot_n = tot_hit + hit, tot_n + len(ids)
        lines.append(f"| {label} | " + " | ".join(cells) + f" | {tot_hit} / {tot_n} |")
    lines.append("")
    for vp, title in VIEWPOINTS.items():
        scs = [s for s in SCENES if s.viewpoint == vp]
        kinds = "・".join(f"{s.id}({'値' if s.kind == 'value' else '能力'})" for s in scs)
        lines += [f"## {vp} {title}", "", f"場面 {len(scs)} 件: {kinds}", "",
                  "| 対象 | " + " | ".join(s.id for s in scs) + " |",
                  "|---" * (len(scs) + 1) + "|"]
        for label, rows in (("A", a), ("B", b)):
            lines.append(f"| {label} | " + " | ".join(esc(cell(rows[s.id])) for s in scs) + " |")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--survey-note", default="", help="note printed on the two survey tables")
    ap.add_argument("--seed", type=int, default=None, help="seed for the file names (default: system entropy)")
    a = ap.parse_args()

    targets = sorted(p.stem for p in RUNS.glob("*.tsv"))
    survey_targets = [t for t in targets if t.startswith(SURVEY_PREFIXES)]
    if not survey_targets:
        raise SystemExit("no survey runs under runs/")
    new, cur, mut = load("new_impl"), load("current_impl"), load("mutant")
    survey = best({t: load(t) for t in survey_targets})

    pairs = {
        "current_1": (new, cur, ""), "current_2": (cur, new, ""),
        "survey_1": (new, survey, a.survey_note), "survey_2": (survey, new, a.survey_note),
        "mutant_1": (new, mut, ""), "mutant_2": (mut, new, ""),
    }
    rng = random.Random(a.seed) if a.seed is not None else random.SystemRandom()
    taken = {p.name for p in HERE.glob("表_*.md")}
    mapping = {}
    for table_id in rng.sample(list(pairs), len(pairs)):  # write order random too
        while True:
            name = "表_" + "".join(rng.choice(string.ascii_lowercase + string.digits) for _ in range(6)) + ".md"
            if name not in taken:
                taken.add(name)
                break
        left, right, note = pairs[table_id]
        (HERE / name).write_text(render(left, right, note) + "\n", encoding="utf-8")
        mapping[table_id] = name
    print("survey targets merged:", ", ".join(survey_targets))
    for table_id in pairs:
        print(f"{table_id}\t{mapping[table_id]}")


if __name__ == "__main__":
    main()
