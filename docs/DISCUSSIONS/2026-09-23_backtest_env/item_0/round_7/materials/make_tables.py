#!/usr/bin/env python3
"""Build the six blinded comparison tables of item 0, round 7 (materials
person), from the battery runs (delegation doc §3 "比較の表", battery rules
3-5).

Input: `materials/runs/<target>.tsv`, written by
`tests/bt/battery/item_0/run_battery.py --target <target> --out ...` via
`materials/run_all.sh` (each target run twice by the runner; correctness and
reproducibility are graded there, never here).

Output:
  * six files `round_7/表_<6 random chars>.md` (rows "A" / "B", columns =
    scenes grouped by viewpoint, each cell = correctness + reproducibility);
  * `materials/mapping.tsv`: table id -> file name -> which target is A / B
    (the only place that says what each table is);
  * `materials/survey_best.tsv`: per scene, which survey target gave the
    merged best result (kept out of the tables);
  * `materials/survey_failures.tsv`: per scene, every survey target whose
    result was 結果なし, with the runner's detail (kept out of the tables).

Survey side = one row: per scene, the best result of every survey target
that ran. Best order (battery rule 5): correctness 正解と一致 > 対応なし >
不一致 > 結果なし; equal correctness -> 2 回の実行で同じ > 2 回で違う >
結果なし; still equal -> first target name in sorted order (fixed rule, so
the output is deterministic).

Notes printed in a table name no tool and no clock time (§3 "比較の表"):
the per-scene failure note is generated from the runs; the candidate-level
note (a tool that could not be run at all this round) comes from
`--survey-note`.

    python3 make_tables.py [--survey-note TEXT] [--seed N]
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import random
import re
import string
import sys
from pathlib import Path

MAT = Path(__file__).resolve().parent
OUT = MAT.parent
REPO = MAT.parents[5]
sys.path.insert(0, str(REPO / "tests" / "bt" / "battery" / "item_0"))
from scenes import SCENES, VIEWPOINTS  # noqa: E402

RUNS = MAT / "runs"
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


def rank(r: dict) -> tuple[int, int]:
    return C_RANK[r["correctness"]], R_RANK[r["reproducibility"]]


def best(rows_by_target: dict[str, dict[str, dict]]) -> tuple[dict[str, dict], dict[str, str]]:
    out, who = {}, {}
    for sc in SCENES:
        name, rows = min(rows_by_target.items(), key=lambda kv: (rank(kv[1][sc.id]), kv[0]))
        out[sc.id], who[sc.id] = rows[sc.id], name
    return out, who


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


def _error_kind(detail: str) -> str:
    """What came out, in words that name no tool (round 7): a provenance
    refusal of the runner, a result that says the mechanism of the scene is
    not implemented, or the exception class names found in the detail. The
    rest of the detail can name the tool and stays in materials."""
    if detail.startswith("出所の検めで採点しない"):
        return "採点の前の出所の検めで退けられた結果(対象が届けたことを示せない。例外ではない)"
    if "再現の範囲外" in detail or "書き直していないので結果が無い" in detail:
        return "この場面の機構を実装していない旨を返し、採点できる結果が無い(例外ではない)"
    names = sorted(set(m.group(1) for m in re.finditer(r"\b([A-Z][A-Za-z]*(?:Error|Exception))\b", detail)))
    return "例外 " + "・".join(names) if names else "例外"


def _durations() -> dict[str, int]:
    """Seconds from start to end of each target's whole run (all scenes,
    twice), measured by run_all.sh (logs/run_all.log). Only the length goes
    into a table; the clock times stay in the log."""
    import datetime as dt
    out = {}
    log = MAT / "logs" / "run_all.log"
    if not log.exists():
        return out
    for line in log.read_text(encoding="utf-8").splitlines():
        m = re.match(r"(\S+) interpreter=\S+ start=(\S+) end=(\S+) ", line)
        if m:
            f = "%Y-%m-%dT%H:%M:%SZ"
            out[m.group(1)] = int((dt.datetime.strptime(m.group(3), f) - dt.datetime.strptime(m.group(2), f)).total_seconds())
    return out


def failure_notes(runs: dict[str, dict[str, dict]], merged: dict[str, dict]) -> list[str]:
    """Per scene: every merged survey target whose result was 結果なし, each
    with what came out and the measured seconds of its whole run (round 7:
    one (what, seconds) pair per target, so the two stay together)."""
    per_scene: dict[str, list[tuple[str, str]]] = collections.defaultdict(list)
    for name in sorted(runs):
        for sc in SCENES:
            r = runs[name][sc.id]
            if r["correctness"] == "結果なし" or r["reproducibility"] == "結果なし":
                per_scene[sc.id].append((name, _error_kind(r["detail_1"])))
    secs = _durations()
    notes = []
    for sc in SCENES:
        if sc.id in per_scene:
            items = "/".join(
                f"({i}) 出たもの: {k}。実測の時間: その対象を全場面に 2 回ずつ通した所要 "
                f"{str(secs[n]) + ' 秒' if n in secs else '未記録'}(時間の打ち切りではない)"
                for i, (n, k) in enumerate(per_scene[sc.id], 1))
            notes.append(
                f"場面 {sc.id}: この行に寄せた対象のうち {len(per_scene[sc.id])} 件は結果なし"
                f"(試したこと: 場面の定義どおりに対象の公開の口で走らせた。{items})。"
                f"この場面の行は残りの対象の最も良い結果 = {merged[sc.id]['correctness']}。")
    return notes


def candidate_notes(path, merged_targets: list[str]) -> list[str]:
    """Candidate-level gap (battery rule 4): how many survey candidates did
    not run at all, per reason kind of the scene keeper's RUNNABILITY.tsv.
    No names, no times (those stay in that file and in materials). Round 6:
    a target that rewrites a candidate that did not run (its number is the
    trailing digits of the target name) is counted as merged, without saying
    which rows or scenes it gave (the table does not tell it apart)."""
    if path is None:
        return []
    with Path(path).open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    ran = [r for r in rows if r["result"] == "走った"]
    not_ran = [r for r in rows if r["result"] != "走った"]
    if not not_ran:
        return []
    rewritten = {m.group(1) for t in merged_targets if t.startswith("repro_")
                 for m in [re.search(r"(\d+)$", t)] if m}
    rewritten = [r for r in not_ran if r["cand"] in rewritten]
    rest = [r for r in not_ran if r not in rewritten]
    kinds = collections.Counter(r["reason_kind"] for r in rest)
    parts = "、".join(f"{k} {n} 件" for k, n in sorted(kinds.items()))
    return [f"調査結果の側の候補 {len(rows)} 件のうち、この行に寄せたのは動かせた {len(ran)} 件と、"
            f"動かせなかった {len(not_ran)} 件のうちその機構を一次資料どおりに書き直して走らせた {len(rewritten)} 件の結果"
            f"(計 {len(merged_targets)} 対象)。残りの {len(rest)} 件(理由の内訳: {parts})はこの行に入っていない"
            f"(候補ごとの欠け。場面集の検討表で扱う)。"]


def render(a: dict[str, dict], b: dict[str, dict], notes: list[str]) -> str:
    lines = ["# 比較の表(項目 0、第 7 周)", "",
             "A と B は名前を伏せた 2 つの対象。場面の定義は `tests/bt/battery/item_0/DEFINITIONS.md`。",
             "各セルは 2 つの欄: 正しさ(正解と一致 / 対応なし / 不一致(値)/ 結果なし)と、"
             "再現(2 回の実行で同じ / 2 回で違う(値)/ 結果なし)。",
             "良い順: 正解と一致 > 対応なし > 不一致 > 結果なし。正しさが同じなら「2 回の実行で同じ」が上。", ""]
    for n in notes:
        lines += [f"注記: {n}", ""]
    for heading, field, good in (("「正解と一致」", "correctness", "正解と一致"),
                                 ("「2 回の実行で同じ」", "reproducibility", "2 回の実行で同じ")):
        lines += [f"## 観点ごとの{heading}の数", "",
                  "| 対象 | " + " | ".join(VIEWPOINTS) + " | 計 |",
                  "|---" * (len(VIEWPOINTS) + 2) + "|"]
        for label, rows in (("A", a), ("B", b)):
            cells, tot_hit, tot_n = [], 0, 0
            for vp in VIEWPOINTS:
                ids = [s.id for s in SCENES if s.viewpoint == vp]
                hit = sum(rows[i][field] == good for i in ids)
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
    ap.add_argument("--survey-note", action="append", default=[], help="candidate-level note on the survey tables")
    ap.add_argument("--runnability", type=Path, default=None,
                    help="the scene keeper's RUNNABILITY.tsv: candidates not run are counted in a note")
    ap.add_argument("--seed", type=int, default=None, help="seed for the file names (default: system entropy)")
    a = ap.parse_args()

    targets = sorted(p.stem for p in RUNS.glob("*.tsv"))
    survey_targets = [t for t in targets if t.startswith(SURVEY_PREFIXES)]
    if not survey_targets:
        raise SystemExit("no survey runs under materials/runs/")
    new, cur, mut = load("new_impl"), load("current_impl"), load("mutant")
    survey_runs = {t: load(t) for t in survey_targets}
    survey, who = best(survey_runs)
    survey_notes = list(a.survey_note) + candidate_notes(a.runnability, survey_targets) + failure_notes(survey_runs, survey)

    pairs = {
        "current_1": (new, cur, [], "new_impl", "current_impl"),
        "current_2": (cur, new, [], "current_impl", "new_impl"),
        "survey_1": (new, survey, survey_notes, "new_impl", "survey_best"),
        "survey_2": (survey, new, survey_notes, "survey_best", "new_impl"),
        "mutant_1": (new, mut, [], "new_impl", "mutant"),
        "mutant_2": (mut, new, [], "mutant", "new_impl"),
    }
    rng = random.Random(a.seed) if a.seed is not None else random.SystemRandom()
    taken = {p.name for p in OUT.glob("表_*.md")} | {p.name for p in (MAT / "stale").glob("表_*.md")}
    mapping = {}
    for table_id in rng.sample(list(pairs), len(pairs)):  # write order random too
        while True:
            name = "表_" + "".join(rng.choice(string.ascii_lowercase + string.digits) for _ in range(6)) + ".md"
            if name not in taken:
                taken.add(name)
                break
        left, right, notes, _, _ = pairs[table_id]
        (OUT / name).write_text(render(left, right, notes) + "\n", encoding="utf-8")
        mapping[table_id] = name

    with (MAT / "mapping.tsv").open("w", encoding="utf-8") as f:
        f.write("table_id\tfile\tA\tB\n")
        for table_id, (_, _, _, la, lb) in pairs.items():
            f.write(f"{table_id}\t{mapping[table_id]}\t{la}\t{lb}\n")
    with (MAT / "survey_best.tsv").open("w", encoding="utf-8") as f:
        f.write("scene_id\tviewpoint\tbest_target\tcorrectness\treproducibility\n")
        for sc in SCENES:
            r = survey[sc.id]
            f.write(f"{sc.id}\t{sc.viewpoint}\t{who[sc.id]}\t{r['correctness']}\t{r['reproducibility']}\n")
    with (MAT / "survey_failures.tsv").open("w", encoding="utf-8") as f:
        f.write("scene_id\ttarget\tcorrectness\treproducibility\tdetail_1\n")
        for t in survey_targets:
            for sc in SCENES:
                r = survey_runs[t][sc.id]
                if r["correctness"] == "結果なし" or r["reproducibility"] == "結果なし":
                    f.write(f"{sc.id}\t{t}\t{r['correctness']}\t{r['reproducibility']}\t{r['detail_1']}\n")
    print("survey targets merged:", ", ".join(survey_targets))
    for table_id in pairs:
        print(f"{table_id}\t{mapping[table_id]}")


if __name__ == "__main__":
    main()
