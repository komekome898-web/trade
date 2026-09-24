"""The cells of every viewpoint's range (positive definition C) and their verdicts.

The axes are written out by machine from the fixed requirements' text, never
kept by hand: the text is the section 1 row (column 4) and every section 2
row (columns 2 and 3) of REQUIREMENTS.md, cut into segments at the delimiter
characters below; each segment has exactly one judgment in
`grid_c_judgments.tsv` (an event-axis value, a see-path value, a value of a
viewpoint's own extra axis, or "not an axis" with its reason). The axes and
their values come only from those judgments.

A viewpoint's cells are every combination of the event axis, the see-path
axis and the viewpoint's own extra axes (a viewpoint's text limits no axis).
Each cell's verdict has two values only and is made from the scenes' `covers`
alone (round r11-1, LEAD_DESIGN.md section 8.2 item 1): "場面にした" with the
ids of the scenes of the same viewpoint whose `Scene.covers` holds the cell,
and "測っていない(固定した測り方の外)" otherwise. No reading of the
requirements' words decides a verdict. `DEFINITIONS.md` shows the table made
here ("場面にしていない観点・側面"); `test_battery_item0.py` rebuilds the axes
from the requirements' text on its own and checks the table against an oracle
written from the rule's sentence.
"""
from __future__ import annotations

import csv
import re
from collections import Counter
from functools import lru_cache
from itertools import product
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
REQUIREMENTS = "docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/REQUIREMENTS.md"
# (line, column) of the text written out: section 1's row, column 4; section 2's rows, columns 2 and 3
SOURCE_CELLS = [(9, 4)] + [(n, c) for n in range(17, 24) for c in (2, 3)]
DELIMITERS = r"[・、。()（）/「」:]|\*\*|\+"
JUDGMENTS = HERE / "grid_c_judgments.tsv"
VIEWPOINTS = [f"P0-{i}" for i in range(1, 8)]
MEASURE_LINE = {f"P0-{i}": 16 + i for i in range(1, 8)}  # the section 2 row of each viewpoint


def requirement_lines() -> list[str]:
    return (REPO / REQUIREMENTS).read_text(encoding="utf-8").split("\n")


def table_cell(line: int, column: int) -> str:
    cells = [x.strip() for x in requirement_lines()[line - 1].strip().strip("|").split("|")]
    return cells[column - 1]


def segments() -> list[tuple[int, int, str]]:
    """(line, column, segment) of every segment of the source cells, in order."""
    out = []
    for n, c in SOURCE_CELLS:
        for s in re.split(DELIMITERS, table_cell(n, c)):
            s = s.strip()
            if s:
                out.append((n, c, s))
    return out


@lru_cache(maxsize=None)
def judgments() -> tuple[tuple[int, str, str], ...]:
    rows = []
    with JUDGMENTS.open(encoding="utf-8") as f:
        for r in csv.reader(f, delimiter="\t"):
            if not r or r[0].startswith("#"):
                continue
            rows.append((int(r[0]), r[1], r[2]))
    return tuple(rows)


def axes() -> tuple[list[str], list[str], dict[tuple[str, str], list[str]]]:
    """(event values, see-path values, {(viewpoint, axis name): values}) from the judgments only."""
    ev, see, extra = [], [], {}
    for _, _, j in judgments():
        if j.startswith("E:") and j[2:] not in ev:
            ev.append(j[2:])
        elif j.startswith("V:") and j[2:] not in see:
            see.append(j[2:])
        elif j.startswith("X:"):
            _, vp, ax, val = j.split(":", 3)
            vals = extra.setdefault((vp, ax), [])
            if val not in vals:
                vals.append(val)
    return ev, see, extra


def measure_text(vp: str) -> str:
    """The viewpoint's fixed way of measuring (section 2, column 3)."""
    return table_cell(MEASURE_LINE[vp], 3)


def cells(vp: str) -> list[tuple[str, str, str]]:
    """Every (event, see-path, extra) cell of a viewpoint; extra is "" when the viewpoint has no extra axis."""
    ev, see, extra = axes()
    ex = [vals for (v, _), vals in extra.items() if v == vp]
    assert len(ex) <= 1, "one extra axis per viewpoint in the fixed requirements"
    return [(e, s, x) for e, s, x in product(ev, see, ex[0] if ex else [""])]


VERDICTS = ("場面にした", "測っていない(固定した測り方の外)")  # the only two values (LEAD_DESIGN.md section 8.2 item 1)
MEANING = ("この表は測っていない範囲の記録である。要件を広げるかはオーナーの判断で、項目 0 の通過のあとに"
           "『欠けているもの』の批評家の経路で上げる。")  # section 8.2 item 2, verbatim


def verdict(vp: str, cell: tuple[str, str, str], scenes) -> tuple[str, list[str]]:
    """(verdict, scene ids) of one cell: the scenes of the same viewpoint whose covers hold the cell."""
    ids = [sc.id for sc in scenes if sc.viewpoint == vp and tuple(cell) in {tuple(c) for c in sc.covers}]
    return (VERDICTS[0], ids) if ids else (VERDICTS[1], [])


def table(scenes) -> list[dict]:
    """Every cell of every viewpoint, once, with its verdict made from the scenes' `covers` only."""
    rows = []
    for vp in VIEWPOINTS:
        for e, s, x in cells(vp):
            v, ids = verdict(vp, (e, s, x), scenes)
            rows.append({"viewpoint": vp, "event": e, "see": s, "extra": x, "verdict": v, "scenes": ids})
    return rows


def problems(scenes, rows) -> list[tuple]:
    """What differs between a table and the one the scenes' covers make: a missing, repeated or foreign cell, or a
    verdict / scene list that is not the covers' (the check the generator, the tests and the probes share)."""
    want = {(r["viewpoint"], r["event"], r["see"], r["extra"]): (r["verdict"], r["scenes"]) for r in table(scenes)}
    got = [((r["viewpoint"], r["event"], r["see"], r["extra"]), (r["verdict"], list(r["scenes"]))) for r in rows]
    out: list[tuple] = []
    seen = Counter(k for k, _ in got)
    out += [("升目が無い", k) for k in want if k not in seen]
    out += [("升目が 2 回", k) for k, n in sorted(seen.items()) if n > 1]
    for k, v in got:
        if k not in want:
            out.append(("範囲の外の升目", k))
        elif v[0] not in VERDICTS or v != want[k]:
            out.append(("判断が covers と違う", k, v, want[k]))
    return out
