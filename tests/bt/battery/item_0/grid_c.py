"""The cells of every viewpoint's range (round r8-1, positive definition C).

The axes are written out by machine from the fixed requirements' text, never
kept by hand: the text is the section 1 row (column 4) and every section 2
row (columns 2 and 3) of REQUIREMENTS.md, cut into segments at the delimiter
characters below; each segment has exactly one judgment in
`grid_c_judgments.tsv` (an event-axis value, a see-path value, a value of a
viewpoint's own extra axis, or "not an axis" with its reason). The axes and
their values come only from those judgments.

A viewpoint's cells are every combination of the event axis, the see-path
axis and the viewpoint's own extra axes (a viewpoint's text limits no axis).
Each cell is either "場面にした" (the scenes whose `Scene.covers` holds the
cell), "場面にしない" (a reason that quotes the words of that viewpoint's fixed
way of measuring -- REQUIREMENTS.md section 2, column 3 -- the cell falls
outside, or a lead's decision that names the cell), or "未決" (the words do
not decide it; raised to the lead). `DEFINITIONS.md` shows the table made
here ("場面にしていない観点・側面"); `test_battery_item0.py` rebuilds the
axes from the requirements' text on its own and checks the table.
"""
from __future__ import annotations

import csv
import re
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


def judgments() -> list[tuple[int, str, str]]:
    rows = []
    with JUDGMENTS.open(encoding="utf-8") as f:
        for r in csv.reader(f, delimiter="\t"):
            if not r or r[0].startswith("#"):
                continue
            rows.append((int(r[0]), r[1], r[2]))
    return rows


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


# ------------------------------------------------------------------ what the words decide
# Names used in the rules below (the axis values, as the judgments write them).
MARKET = ["約定", "板の写真", "板の差分", "足", "資金調達", "清算"]
CLOCK = "時計"
NOTICES = ["注文の受付の通知", "注文の拒否の通知", "注文の約定の通知"]
RECV, PLACE_RET, CANCEL_RET, READ = ("戦略の呼び出しに届く物", "発注の呼び出しがその場で返す物",
                                     "取消の呼び出しがその場で返す物", "戦略が対象の公開の手段で読む物")

# A lead's decision that names cells: LEAD_DESIGN.md section 7, item 2 (the words quoted), and the cells its
# segments name (ROOTCAUSE_r8-1.md section 9 item 2: the notices and the clock of P0-4).
LEAD_7_2 = ("docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/round_7/LEAD_DESIGN.md §7 の 2(57 のファイルの行。切片 5「定義 C を当てたときの通知・時計の組(i0-r7-05)」・"
            "切片 6「場面にしない」・切片 8「固定した測り方(要件 P0-4 の文)の外」)",
            "固定した測り方(要件 P0-4 の文)の外。要件は 1 周目の前に固定したもので、周の途中で広げない(委任文 §3「要件と判定の固定」)")

PENDING_SCENE = ("測り方の語では中(引いた語)。場面を足すかは ROOTCAUSE_r8-1.md §9 の 8(升目の場面の事象の型の扱い)の答えを待つ"
                 "(正の定義 C: その扱いに依る升目の場面は答えまで足さない)")
UNDECIDED_SEE = ("測り方の文が見る道を名指さない(ROOTCAUSE_r8-1.md §9 の 3)")
UNDECIDED_INPUT = ("測り方の語「{w}」が、核が作る事象(時計・注文の通知)を入れるかを決めない(ROOTCAUSE_r8-1.md §9 の 2)")


def rule(vp: str, event: str, see: str, extra: str) -> tuple[str, str, str]:
    """(verdict for a cell no scene covers, the words quoted, the reason). The verdict is 場面にしない or 未決;
    a quoted word is a substring of the viewpoint's measuring text, or the lead's decision is named."""
    m = measure_text(vp)
    if vp == "P0-1":
        w = "事象を型で投入し"
        if event not in MARKET:
            return "未決", w, UNDECIDED_INPUT.format(w=w)
        if see in (PLACE_RET, CANCEL_RET):
            return "場面にしない", w, "発注・取消の呼び出しがその場で返す物は、投入した事象ではない"
        return "未決", "時刻順に処理されるかを見る", UNDECIDED_SEE
    if vp == "P0-2":
        if extra in ("秒", "ミリ"):
            return "未決", "既知の時刻", "測り方の語「既知の時刻(例 …)を投入し」が、秒・ミリの時刻を入れるかを決めない(例はナノ秒の ISO 文字列)"
        if event not in MARKET:
            return "未決", "既知の時刻", UNDECIDED_INPUT.format(w="既知の時刻")
        return "未決", "核が保持する値", UNDECIDED_SEE
    if vp == "P0-3":
        return "未決", "型ごとに 1 件ずつ投入し", UNDECIDED_SEE
    if vp == "P0-4":
        if event == CLOCK or event in NOTICES:
            return "場面にしない", LEAD_7_2[0], LEAD_7_2[1]
        w = "未来時刻の事象を読もうとするコード"
        if see in (PLACE_RET, CANCEL_RET):
            return "場面にしない", w, "発注・取消の呼び出しがその場で返す物は、事象を読むコードの読み出しではない"
        if see == READ:
            return "未決", w, PENDING_SCENE.replace("引いた語", w)
        return "未決", "戦略側から未来時刻の事象を読もうとする", UNDECIDED_SEE
    if vp == "P0-5":
        w = "同時刻に複数型の事象を仕込んだ入力を作り"
        if event not in MARKET:
            return "未決", w, UNDECIDED_INPUT.format(w=w)
        if see in (PLACE_RET, CANCEL_RET):
            return "場面にしない", w, "発注・取消の呼び出しがその場で返す物は、入力に仕込んだ事象ではない"
        return "未決", "規則どおりの順で処理されるか", UNDECIDED_SEE
    if vp == "P0-6":
        w = "注文の受付"
        if event not in NOTICES:
            return "場面にしない", w, "測り方は核が返す物を「注文の受付/拒否/約定の通知の事象」に限る。市場の事象と時計は通知ではない"
        return "未決", "通知の事象として返すか", PENDING_SCENE.replace("引いた語", "通知の事象として返すか")
    if vp == "P0-7":
        return "未決", "各口にダミー実装を差し込み", UNDECIDED_SEE
    raise ValueError(vp)  # pragma: no cover


def table(scenes) -> list[dict]:
    """Every cell of every viewpoint, once, with its verdict (made from the scenes' `covers` and `rule`)."""
    by_cell: dict[tuple, list[str]] = {}
    for sc in scenes:
        for cov in sc.covers:
            by_cell.setdefault((sc.viewpoint, *cov), []).append(sc.id)
    rows = []
    for vp in VIEWPOINTS:
        for e, s, x in cells(vp):
            ids = by_cell.get((vp, e, s, x), [])
            if ids:
                rows.append({"viewpoint": vp, "event": e, "see": s, "extra": x, "verdict": "場面にした",
                             "scenes": ids, "quote": "", "reason": ""})
            else:
                v, q, r = rule(vp, e, s, x)
                rows.append({"viewpoint": vp, "event": e, "see": s, "extra": x, "verdict": v, "scenes": [],
                             "quote": q, "reason": r})
    return rows
