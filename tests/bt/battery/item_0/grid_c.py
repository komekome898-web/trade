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
and "測っていない" otherwise (round r16-1: with the reason made per cell from the declarations and F's counted cells,
`why`). Since round r13-1 (critic
i0-r11-02, ROOTCAUSE_r13-1.md section 3) `Scene.covers` is not written by
hand: it is `scenes.covers_of`, the declared cells whose event type comes out
of the scene's input by machine. No reading of the requirements' words decides
a verdict. `DEFINITIONS.md` shows the table made
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
DELIMITERS = r"[・、。()（）/「」:]|\*\*|\+"
JUDGMENTS = HERE / "grid_c_judgments.tsv"
VIEWPOINTS = [f"P0-{i}" for i in range(1, 8)]


def requirement_lines() -> list[str]:
    return (REPO / REQUIREMENTS).read_text(encoding="utf-8").split("\n")


def _row_lines() -> dict[str, int]:
    """The line of each table row the axes are written from, found by the row's first cell (round r16-1: the lead's
    L-445 edit added a section 0 and moved every row; fixed line numbers had pointed at other lines): the section 1
    row of item 0 (first cell "0") and the section 2 rows P0-1 .. P0-7. Each must occur exactly once."""
    found: dict[str, list[int]] = {}
    for n, ln in enumerate(requirement_lines(), 1):
        if ln.startswith("|"):
            first = ln.strip().strip("|").split("|")[0].strip()
            if first in ("0", *VIEWPOINTS):
                found.setdefault(first, []).append(n)
    bad = {k: v for k, v in found.items() if len(v) != 1}
    missing = [k for k in ("0", *VIEWPOINTS) if k not in found]
    if bad or missing:
        raise ValueError(f"REQUIREMENTS.md rows: repeated {bad}, missing {missing}")
    return {k: v[0] for k, v in found.items()}


_ROWS = _row_lines()
# (line, column) of the text written out: section 1's row, column 4; section 2's rows, columns 2 and 3
SOURCE_CELLS = [(_ROWS["0"], 4)] + [(_ROWS[vp], c) for vp in VIEWPOINTS for c in (2, 3)]
MEASURE_LINE = {vp: _ROWS[vp] for vp in VIEWPOINTS}  # the section 2 row of each viewpoint


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


VERDICTS = ("場面にした", "測っていない")  # the only two values (LEAD_DESIGN.md section 8.2 item 1; the name, round r16-1)
# Round r16-1 (critic i0-r15-06; ROOTCAUSE_r16-1.md section 2, root 4): the second value's name carried the reason of
# the criterion section 8.2 item 1 withdrew ("固定した測り方の外"), which no machine checked. The reason is now made per
# cell from what the machine does check: the scenes' declarations and F's counted cells (`why`).
WHY_NO_DECLARATION = "この升目を宣言した場面が無い"
WHY_TYPE_NOT_FROM_INPUT = "宣言した場面はあるが、その事象の型が場面の入力から出ない"
MEANING = ("この表は測っていない範囲の記録である。要件を広げるかはオーナーの判断で、項目 0 の通過のあとに"
           "『欠けているもの』の批評家の経路で上げる。")  # section 8.2 item 2, verbatim


def verdict(vp: str, cell: tuple[str, str, str], scenes) -> tuple[str, list[str]]:
    """(verdict, scene ids) of one cell: the scenes of the same viewpoint whose covers (scenes.covers_of: declared and
    given by the input, round r13-1) hold the cell."""
    import scenes as _scenes
    for sc in scenes:
        if not isinstance(sc, _scenes.Scene):  # round r13-1: only a scene's own declaration and input decide
            raise TypeError(f"not a scenes.Scene: {type(sc).__name__}")
    ids = [sc.id for sc in scenes if sc.viewpoint == vp and tuple(cell) in set(_scenes.covers_of(sc))]
    return (VERDICTS[0], ids) if ids else (VERDICTS[1], [])


def why(vp: str, cell: tuple[str, str, str], scenes) -> str:
    """The reason of a cell no scene counts (round r16-1): a scene of the viewpoint declares it but F does not count
    it -> WHY_TYPE_NOT_FROM_INPUT; no scene of the viewpoint declares it -> WHY_NO_DECLARATION; "" for a counted cell."""
    if verdict(vp, cell, scenes)[0] == VERDICTS[0]:
        return ""
    declared = any(sc.viewpoint == vp and tuple(cell) in {tuple(c) for c in sc.declares} for sc in scenes)
    return WHY_TYPE_NOT_FROM_INPUT if declared else WHY_NO_DECLARATION


def shown(row: dict) -> str:
    """The verdict as the table shows it: 場面にした, or 測っていない(<why>)."""
    return row["verdict"] if row["verdict"] == VERDICTS[0] else f"{row['verdict']}({row['why']})"


def table(scenes) -> list[dict]:
    """Every cell of every viewpoint, once, with its verdict made from the scenes' `covers` only (and, round r16-1,
    the reason of a cell not counted)."""
    rows = []
    for vp in VIEWPOINTS:
        for e, s, x in cells(vp):
            v, ids = verdict(vp, (e, s, x), scenes)
            rows.append({"viewpoint": vp, "event": e, "see": s, "extra": x, "verdict": v, "scenes": ids,
                         "why": why(vp, (e, s, x), scenes)})
    return rows


def problems(scenes, rows) -> list[tuple]:
    """What differs between a table and the one the scenes' covers make: a missing, repeated or foreign cell, or a
    verdict / scene list that is not the covers' (the check the generator, the tests and the probes share)."""
    want = {(r["viewpoint"], r["event"], r["see"], r["extra"]): (r["verdict"], r["scenes"], r["why"]) for r in table(scenes)}
    got = [((r["viewpoint"], r["event"], r["see"], r["extra"]), (r["verdict"], list(r["scenes"]), r.get("why")))
           for r in rows]
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


# ---------------------------------------------------------------- round r16-1: the values a viewpoint names
# Critic i0-r15-05 (ROOTCAUSE_r16-1.md section 2, root 1): nothing checked that a viewpoint's scenes give every value
# its text names (P0-2 names 秒 and ミリ; no scene gave them). `named_values` reads them from the judgments of the
# segments of the viewpoint's own section 2 row (event-axis and extra-axis values; see-path values are the scenes'
# declarations, read by the critic -- LEAD_DESIGN.md section 8.5 item 24); `named_coverage` lists, for each, the
# scenes of the viewpoint whose input gives it (an event value: F's types, scenes.input_types; an extra value:
# scenes.extra_values_of). A value no input gives shows with no scene, and a test fails.
def named_values(vp: str) -> list[tuple[str, str]]:
    """[(axis, value)] named by the viewpoint's own section 2 row, in order: ("事象", event) and (extra axis, value)."""
    out: list = []
    for (n, _, _), (_, _, j) in zip(segments(), judgments()):
        if n != MEASURE_LINE[vp]:
            continue
        if j.startswith("E:"):
            item = ("事象", j[2:])
        elif j.startswith("X:"):
            _, v, ax, val = j.split(":", 3)
            if v != vp:
                raise ValueError(f"line {n} names an extra value of {v}, not of {vp}: {j}")
            item = (ax, val)
        else:
            continue
        if item not in out:
            out.append(item)
    return out


def named_coverage(scenes) -> list[dict]:
    """[{"viewpoint", "axis", "value", "scenes"}] for every value every viewpoint names, with the ids of the scenes of
    that viewpoint whose input gives it."""
    import scenes as _scenes
    rows = []
    for vp in VIEWPOINTS:
        for ax, val in named_values(vp):
            ids = [sc.id for sc in scenes if sc.viewpoint == vp and (
                val in _scenes.input_types(sc) if ax == "事象" else (ax, val) in _scenes.extra_values_of(sc))]
            rows.append({"viewpoint": vp, "axis": ax, "value": val, "scenes": ids})
    return rows


# ---------------------------------------------------------------- round r15-1: the scenes the cells do not place
# Critic i0-r14-06 (repeat_of i0-r11-02; ROOTCAUSE_r15-1.md sections 2-4): the table shows a scene only where it
# counts a cell, so a scene that measures its viewpoint but counts no cell under F vanished from it (P0-2's four,
# p6-place-then-cancel, p7-account-swap). `unplaced` lists them per viewpoint, with the class the scene's input gives by
# machine; it never changes a cell's verdict (F and LEAD_DESIGN.md section 8.2 item 1: two values).
NO_EVENT = "事象を持たない"
TYPE_NOT_IN_INPUT = "事象の型を入力が決めない"
NO_CELL_DECLARED = "入力から型は出るが、その型の升目を宣言していない"
HAS_UNTYPED = "升目に当たるが、型の欄の無い事象を含む"
UNPLACED_CLASSES = (NO_EVENT, TYPE_NOT_IN_INPUT, NO_CELL_DECLARED)  # the classes of scenes no cell places


def unplaced(scenes) -> list[dict]:
    """[{"viewpoint", "scene", "class"}] in the scenes' order: every scene whose counted cells (scenes.covers_of) are
    none -- 事象を持たない (no event item and no type), 事象の型を入力が決めない (event items, no type),
    入力から型は出るが、その型の升目を宣言していない (the input gives a type) -- and every scene that counts cells but
    holds an event item without a type field (升目に当たるが、型の欄の無い事象を含む). An input F refuses raises
    ValueError (scenes.input_types)."""
    import scenes as _scenes
    out = []
    for sc in scenes:
        if not isinstance(sc, _scenes.Scene):
            raise TypeError(f"not a scenes.Scene: {type(sc).__name__}")
        types = _scenes.input_types(sc)
        counted = _scenes.covers_of(sc)
        evs = _scenes.input_events(sc)
        untyped = [e for e in evs if not (isinstance(e, dict) and "kind" in e)]
        if not counted:
            cls = NO_EVENT if not evs and not types else TYPE_NOT_IN_INPUT if not types else NO_CELL_DECLARED
        elif untyped:
            cls = HAS_UNTYPED
        else:
            continue
        out.append({"viewpoint": sc.viewpoint, "scene": sc.id, "class": cls})
    return out


# ---------------------------------------------------------------- round r15-1: who records the strategy's requests
# The lead's answer to br13-1-2 (VERDICTS run11): the note of the cell table says, with the numbers, which adapters
# do not record the strategy's requests (their clock and order-notice cells are "記録なし" in the materials role's
# note, never "entered"). Read from run_battery.py's target tables and each adapter file's syntax tree (an opponent
# adapter imports only in its own venv, so it is not imported here).
RECORDING_GROUPS = ("新実装・試金石", "相手", "再現")


def request_recording() -> dict:
    """{group: {"records": [(target, configured targets)], "not": [...]}} for the three groups of targets."""
    import ast
    import run_battery as R
    bases = {RECORDING_GROUPS[0]: ["new_impl", "mutant"], RECORDING_GROUPS[1]: list(R.OPPONENTS),
             RECORDING_GROUPS[2]: list(R._repro_targets())}
    table = {**R.OPPONENTS, **R._repro_targets()}
    out = {}
    for g, bs in bases.items():
        rec, non = [], []
        for b in bs:
            cls = table.get(b, (None, None))[1]
            says = False
            for node in ast.walk(ast.parse(R._module_path(b).read_text(encoding="utf-8"))):
                if isinstance(node, ast.ClassDef) and (cls is None or node.name == cls):
                    for st in node.body:
                        if (isinstance(st, ast.Assign) and isinstance(st.value, ast.Constant) and st.value.value is True
                                and any(isinstance(x, ast.Name) and x.id == "records_requests" for x in st.targets)):
                            says = True
            (rec if says else non).append((b, len(R.configured_targets(b))))
        out[g] = {"records": rec, "not": non}
    return out


def request_recording_sentence(counts: dict) -> str:
    return "。".join(f"{g}: 記録する {len(v['records'])}(設定つき対象 {sum(n for _, n in v['records'])})/ "
                    f"記録しない {len(v['not'])}(設定つき対象 {sum(n for _, n in v['not'])})" for g, v in counts.items())


# ---------------------------------------------------------------- round r13-1: the materials role's note
# LEAD_DESIGN.md section 9.2 item 33: per configured target, the cells the table counts ("場面にした") whose event type
# entered none of the covering scenes' runs for that target. Made from the table and the runner's records only; it
# never changes a verdict. A market type entered when it is in a covering scene's `types_in`; the clock and the three
# order notices when the request that gives them (scenes.REQUEST_TYPES) is in a covering scene's `requests`. A cell
# whose covering scenes all have no request record (`requests` null: an adapter that does not record requests) is
# listed apart ("記録なし"), never as entered.
def not_entered(rows, records: dict) -> dict:
    """{"入らなかった": [cell, ...], "記録なし": [cell, ...]}; cell = (viewpoint, event, see-path, extra).
    `records` = {scene id: {"types_in": [event type, ...], "requests": [kind, ...] or None}} of one configured target."""
    import scenes as _scenes
    gives = {e: k for k, es in _scenes.REQUEST_TYPES.items() for e in es}
    miss, unknown = [], []
    for r in rows:
        if r["verdict"] != VERDICTS[0]:
            continue
        cell = (r["viewpoint"], r["event"], r["see"], r["extra"])
        recs = [records[i] for i in r["scenes"] if records.get(i) is not None]
        if r["event"] in gives:
            known = [x for x in recs if x.get("requests") is not None]
            if not known:
                unknown.append(cell)
            elif not any(gives[r["event"]] in x["requests"] for x in known):
                miss.append(cell)
        elif not any(r["event"] in (x.get("types_in") or []) for x in recs):
            miss.append(cell)
    return {"入らなかった": miss, "記録なし": unknown}


def records_from_tsv(path) -> dict:
    """{scene id: {"types_in", "requests"}} from one runner output (run_battery.py's columns, round r13-1)."""
    import json
    csv.field_size_limit(1 << 30)
    out = {}
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            out[row["scene_id"]] = {"types_in": json.loads(row["types_in"]), "requests": json.loads(row["requests"])}
    return out


def not_entered_note(path, scenes) -> str:
    """The note line of one configured target for the materials role's table (the cells named, no target name)."""
    got = not_entered(table(scenes), records_from_tsv(path))
    fmt = lambda cs: "、".join(f"{v} {e}/{s}{'/' + x if x else ''}" for v, e, s, x in cs) or "無し"
    return (f"場面にしたが、この対象には型が入らなかった升目: {fmt(got['入らなかった'])}。"
            f"頼みの記録が無く入ったかを決められない升目: {fmt(got['記録なし'])}。")


if __name__ == "__main__":
    import sys
    import scenes as _s
    for p in sys.argv[1:]:
        print(f"{p}\t{not_entered_note(p, _s.SCENES)}")
