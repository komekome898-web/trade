#!/usr/bin/env python3
"""Item 4, round 1, table-maker: build the six blind comparison tables from
materials/runs/<target>.tsv (the first execution of the battery per target).

    python3 make_tables.py            # writes ../表_<6 chars>.md x6, mapping.tsv,
                                      # survey_breakdown.tsv, table_counts.tsv

Rows are hidden as A / B.  Columns are the scenes, grouped by viewpoint
(VIEWPOINTS below: i4_scenes.VIEWPOINTS minus i4_scenes.NOT_SCENES).  Every cell has two fields: correctness (class_1 of
the first pass) and reproducibility (the runner's repro cell).  The survey
side is folded into one row: per scene, the best result of every survey
target by the order 正解と一致 > 対応なし > 不一致 > 結果なし, then
「2 回の実行で同じ」 above anything else.  Which target gave it is written
only to survey_breakdown.tsv (materials), never to a table.
"""
from __future__ import annotations

import csv
import os
import random
import shutil
import string
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent            # .../round_1/materials
ROUND = HERE.parent                               # .../round_1
REPO = Path("/home/user/trade")
BATTERY = REPO / "tests/bt/battery/item_4"
sys.path.insert(0, str(BATTERY))

import i4_scenes as S  # noqa: E402
import i4_targets as TG  # noqa: E402

VIEWPOINTS: dict = {}
CLASSES = ("正解と一致", "対応なし", "不一致", "結果なし")
SAME = "2 回の実行で同じ"
RUNS = HERE / "runs"

PAIRS = [
    ("current_1", "new_impl", "current_impl"),
    ("current_2", "current_impl", "new_impl"),
    ("survey_1", "new_impl", "survey_best"),
    ("survey_2", "survey_best", "new_impl"),
    ("mutant_1", "new_impl", "mutant"),
    ("mutant_2", "mutant", "new_impl"),
]


def read_run(name: str) -> dict:
    with open(RUNS / f"{name}.tsv", encoding="utf-8") as fh:
        rows = {r["scene"]: r for r in csv.DictReader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)}
    ids = [s["id"] for s in S.SCENES]
    missing = [i for i in ids if i not in rows]
    if missing:
        raise SystemExit(f"{name}: scenes missing from runs/{name}.tsv: {missing}")
    return rows


def why_none(detail: str) -> str:
    """Category of a 「結果なし」 (no tool name, no clock time)."""
    d = detail or ""
    if d.startswith("adapter:") or d.startswith("対照: adapter:") or d.startswith("変形: adapter:"):
        return "対象の公開の口に、この場面を渡す手段が見つからなかった(探した場所は資料係の記録)"
    if d.startswith("対象を読み込めない"):
        return "対象を読み込めなかった(例外)"
    if "時間の上限" in d:
        return "時間の上限で打ち切った"
    if d.startswith("実行が行を残さなかった"):
        return "実行が結果の行を残さなかった"
    return "対象の呼び出しが例外で終わった(対象が拒んだのではない)"


def cell_of(r: dict) -> dict:
    cls = r["class_1"]
    rank = (CLASSES.index(cls), 0 if r["repro"] == SAME else 1)
    return {"class": cls, "detail": r["detail_1"], "repro": r["repro"], "rank": rank,
            "secs": max(float(r["secs_1"] or 0), float(r["secs_2"] or 0)),
            "class_2": r["class_2"], "detail_2": r["detail_2"]}


def build_rows():
    rows = {n: {sid: cell_of(r) for sid, r in read_run(n).items()} for n in ("new_impl", "current_impl", "mutant")}
    survey_names = list(TG.SURVEY) + list(TG.REPRO)
    survey = {n: {sid: cell_of(r) for sid, r in read_run(n).items()} for n in survey_names}
    best, breakdown = {}, []
    for s in S.SCENES:
        sid = s["id"]
        cands = sorted(((survey[n][sid]["rank"], i, n) for i, n in enumerate(survey_names)))
        _, _, pick = cands[0]
        c = dict(survey[pick][sid])
        c["folded"] = {n: survey[n][sid] for n in survey_names}
        best[sid] = c
        for n in survey_names:
            x = survey[n][sid]
            breakdown.append([sid, n, str(TG.TARGETS[n].get("cand", "-")), x["class"], x["repro"],
                              "選んだ" if n == pick else "", str(x["secs"]), x["detail"][:300]])
    rows["survey_best"] = best
    return rows, survey_names, breakdown


def esc(t: str) -> str:
    return str(t).replace("|", "/").replace("\n", " ").replace("\t", " ")


def cell_text(c: dict) -> str:
    cls = c["class"]
    if cls == "不一致":
        cls = f"不一致({esc(c['detail'])[:160]})"
    return f"正しさ: {cls}<br>再現: {esc(c['repro'])}"


def notes_for(label: str, name: str, row: dict, n_survey: int) -> list[str]:
    out = []
    if name == "survey_best":
        n_venv = len(TG.SURVEY)
        n_rep = len(TG.REPRO)
        out.append(f"注記: 行 {label} は {n_survey} 対象(道具 {n_venv} 件と、一次資料どおりに最小限で書き直した機構 {n_rep} 件)の"
                   f"結果を場面ごとに寄せた行。場面ごとに、この {n_survey} 対象のうち最も良い結果を 1 つ置いた(どの対象かは伏せる)。")
    for s in S.SCENES:
        c = row[s["id"]]
        if c["class"] != "結果なし":
            continue
        if name == "survey_best":
            cats: dict[str, int] = {}
            for x in c["folded"].values():
                k = why_none(x["detail"]) if x["class"] == "結果なし" else x["class"]
                cats[k] = cats.get(k, 0) + 1
            secs = max(x["secs"] for x in c["folded"].values())
            parts = "、".join(f"{k} {v} 件" for k, v in sorted(cats.items(), key=lambda kv: (-kv[1], kv[0])))
            out.append(f"注記: 場面 {s['id']}: 行 {label} に寄せた {n_survey} 対象の全部が結果なし。試したこと: 場面の定義どおりに、"
                       f"各対象を別々のプロセスで 2 回ずつ、各対象の公開の口で走らせた。出たもの: {parts}。"
                       f"実測の時間: 1 回の実行でこの場面にかかった時間の最長 {secs:.3f} 秒(時間の上限は 1 場面 300 秒)。")
        else:
            secs = c["secs"]
            out.append(f"注記: 場面 {s['id']}: 行 {label} は結果なし。試したこと: 場面の定義どおりに、別々のプロセスで 2 回、"
                       f"対象の公開の口で走らせた。出たもの: {why_none(c['detail'])}。"
                       f"実測の時間: 1 回の実行でこの場面にかかった時間の最長 {secs:.3f} 秒(時間の上限は 1 場面 300 秒)。")
    return out


def counts(row: dict):
    by_vp = {vp: [0, 0, 0] for vp in VIEWPOINTS}  # correct, same, total
    for s in S.SCENES:
        c = row[s["id"]]
        v = by_vp[s["viewpoint"]]
        v[0] += c["class"] == "正解と一致"
        v[1] += c["repro"] == SAME
        v[2] += 1
    return by_vp


def render(a_name: str, b_name: str, rows: dict, n_survey: int) -> str:
    vps = list(VIEWPOINTS)
    L = ["# 比較の表(項目 4「統合と答え合わせ」、第 1 周)", "",
         "A と B は名前を伏せた 2 つの対象。場面の定義は `tests/bt/battery/item_4/DEFINITIONS.md`。",
         "各セルは 2 つの欄: 正しさ(正解と一致 / 対応なし / 不一致(値)/ 結果なし)と、再現(2 回の実行で同じ / 2 回で違う(値)/ 結果なし)。",
         "良い順: 正解と一致 > 対応なし > 不一致 > 結果なし。正しさが同じなら「2 回の実行で同じ」が上。",
         "正しさの欄は 1 回目の実行の結果。2 回目の実行が違えば、再現の欄に「2 回で違う」と両方の値が出る。",
         "場面の無い観点(" + "、".join(S.NOT_SCENES) + ")は列が無い(理由は場面の定義の各観点の節)。", ""]
    for label, name in (("A", a_name), ("B", b_name)):
        for n in notes_for(label, name, rows[name], n_survey):
            L += [n, ""]
    for title, idx in (("観点ごとの「正解と一致」の数", 0), ("観点ごとの「2 回の実行で同じ」の数", 1)):
        L += [f"## {title}", "", "| 対象 | " + " | ".join(vps) + " | 計 |", "|" + "---|" * (len(vps) + 2)]
        for label, name in (("A", a_name), ("B", b_name)):
            cv = counts(rows[name])
            tot = sum(cv[v][idx] for v in vps)
            den = sum(cv[v][2] for v in vps)
            L.append(f"| {label} | " + " | ".join(f"{cv[v][idx]} / {cv[v][2]}" for v in vps) + f" | {tot} / {den} |")
        L.append("")
    for vp, title in VIEWPOINTS.items():
        scenes = [s for s in S.SCENES if s["viewpoint"] == vp]
        L += [f"## {vp} {title}", "", "場面: " + "、".join(f"{s['id']}({s['kind']}の場面)" for s in scenes), "",
              "| 対象 | " + " | ".join(s["id"] for s in scenes) + " |", "|" + "---|" * (len(scenes) + 1)]
        for label, name in (("A", a_name), ("B", b_name)):
            L.append(f"| {label} | " + " | ".join(cell_text(rows[name][s["id"]]) for s in scenes) + " |")
        L.append("")
    return "\n".join(L)


def load_viewpoints() -> None:
    """Viewpoint id -> title: i4_scenes.VIEWPOINTS without the viewpoints that have no scene (i4_scenes.NOT_SCENES)."""
    for vp, title in S.VIEWPOINTS.items():
        if vp not in S.NOT_SCENES:
            VIEWPOINTS[vp] = title
    seen = {s["viewpoint"] for s in S.SCENES}
    if set(VIEWPOINTS) != seen:
        raise SystemExit(f"viewpoints differ: {sorted(VIEWPOINTS)} vs {sorted(seen)}")


def main() -> int:
    load_viewpoints()
    rows, survey_names, breakdown = build_rows()
    mapping_path = HERE / "mapping.tsv"
    names = {}
    if mapping_path.exists():
        for r in csv.DictReader(open(mapping_path, encoding="utf-8"), delimiter="\t"):
            names[r["table_id"]] = r["file"]
    rng = random.SystemRandom()
    for tid, _, _ in PAIRS:
        while tid not in names or list(names.values()).count(names[tid]) > 1:
            names[tid] = "表_" + "".join(rng.choice(string.ascii_lowercase + string.digits) for _ in range(6)) + ".md"
    # tables of an earlier start: anything named 表_*.md here that is not one of this round's six
    stale = [p for p in ROUND.glob("表_*.md") if p.name not in names.values()]
    if stale:
        (HERE / "stale").mkdir(exist_ok=True)
        with open(HERE / "stale" / "MOVED.tsv", "a", encoding="utf-8") as fh:
            for p in stale:
                shutil.move(str(p), str(HERE / "stale" / p.name))
                fh.write(f"{p.name}\tmoved by make_tables.py\n")
    with open(mapping_path, "w", encoding="utf-8") as fh:
        fh.write("table_id\tfile\tA\tB\n")
        for tid, a, b in PAIRS:
            fh.write(f"{tid}\t{names[tid]}\t{a}\t{b}\n")
    for tid, a, b in PAIRS:
        (ROUND / names[tid]).write_text(render(a, b, rows, len(survey_names)) + "\n", encoding="utf-8")
    with open(HERE / "survey_breakdown.tsv", "w", encoding="utf-8") as fh:
        fh.write("scene\ttarget\tcand\tclass_1\trepro\tpicked\tmax_secs\tdetail_1\n")
        for r in breakdown:
            fh.write("\t".join(esc(x) for x in r) + "\n")
    with open(HERE / "table_counts.tsv", "w", encoding="utf-8") as fh:
        fh.write("row\tviewpoint\tcorrect\tsame\ttotal\n")
        for name in ("new_impl", "current_impl", "survey_best", "mutant"):
            cv = counts(rows[name])
            for vp, (c, s_, t) in cv.items():
                fh.write(f"{name}\t{vp}\t{c}\t{s_}\t{t}\n")
            fh.write(f"{name}\t計\t{sum(v[0] for v in cv.values())}\t{sum(v[1] for v in cv.values())}\t"
                     f"{sum(v[2] for v in cv.values())}\n")
    for tid, _, _ in PAIRS:
        print(tid, names[tid])
    return 0


if __name__ == "__main__":
    sys.exit(main())
