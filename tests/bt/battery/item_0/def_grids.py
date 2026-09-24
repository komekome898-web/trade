"""The input spaces of the six positive definitions of round r8-1 (0, A, B, C, D, E), written out by machine.

Each definition's paragraph (frozen in DEFINITIONS.md by LEAD_DESIGN.md section 8.2 item 5; the text is
`gen_definitions.FROZEN_DEFINITIONS`, the one source DEFINITIONS.md is made from) is cut into segments at the delimiter characters below; every segment has exactly one judgment in
`def_axes/j<k>.tsv`:
  N|reason                       not an axis value
  T|axis|value|通る or 落ちる      an axis value and its expectation
  D|axis|通る or 落ちる|meaning    the expectation of the axis' 'どれにも当たらない' value
  K|axis=value (or axis∈v1,v2)|axis2=value2 (or axis2∈...)   a condition between two axes
(several parts of one judgment are joined with ' && '). Every axis gets a 'どれにも当たらない' value (default
落ちる) unless a T value already names it. A cell = one value per axis; a cell's expectation is 通る iff every
value's expectation is 通る and every condition holds.

Which cells are run (the lead's rule, LEAD_DESIGN.md section 7.2 item 12): the full grid is always written out
and counted; when it has at most 100,000 cells all are run; otherwise a deterministic selection that covers every
value of every axis together with every value of every other axis (all pairs) is run, and the test says how
many cells it ran and that it did not run the full grid.
"""
from __future__ import annotations

import itertools
import math
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
HEADS = {"0": "**当てる範囲**:", "A": "**対象の振る舞いと数える物**:", "B": "**場面集の文が場面について述べてよいこと**:",
         "C": "**観点の範囲と場面**:", "D": "**語の意味**:", "E": "**提出前の吟味の記録が持ってよい物**:"}
DELIMITERS = r"[・、。()（）/「」:]|\*\*|\+"
NONE = "どれにも当たらない"
FULL_GRID_LIMIT = 100_000


def segments(k: str) -> list[str]:
    import gen_definitions
    para = gen_definitions.FROZEN_DEFINITIONS[k]
    assert para.startswith(HEADS[k]) and "\n" not in para, k
    return [s.strip() for s in re.split(DELIMITERS, para) if s.strip()]


def judgments(k: str) -> dict[int, tuple[str, str]]:
    out = {}
    for row in (HERE / "def_axes" / f"j{k}.tsv").read_text(encoding="utf-8").splitlines():
        if not row or row.startswith("#"):
            continue
        d, i, seg, j = row.split("\t")
        assert d == k and int(i) not in out, (k, i)
        out[int(i)] = (seg, j)
    return out


def derive(k: str):
    """(axes {axis: [(value, expectation)]}, conditions [(axis, values, axis2, values2)], problems)."""
    segs, jud = segments(k), judgments(k)
    axes: dict[str, list[tuple[str, str]]] = {}
    dflt: dict[str, tuple[str, str]] = {}
    raw_pairs, problems = [], []
    if sorted(jud) != list(range(1, len(segs) + 1)):
        problems.append(("segments and judgments differ in number", len(segs), len(jud)))
    for i, s in enumerate(segs, 1):
        if i not in jud:
            continue
        if jud[i][0] != s:
            problems.append(("segment text differs", i, s, jud[i][0]))
        for part in jud[i][1].split(" && "):
            f = part.split("|")
            if f[0] == "T":
                _, ax, val, exp = f
                axes.setdefault(ax, [])
                if val not in [v for v, _ in axes[ax]]:
                    axes[ax].append((val, exp))
            elif f[0] == "D":
                dflt[f[1]] = (f[2], f[3])
            elif f[0] == "K":
                raw_pairs.append((f[1], f[2]))
            elif f[0] != "N":
                problems.append(("bad judgment", i, part))
    for ax, vals in axes.items():
        if not any(v.startswith(NONE) for v, _ in vals):
            exp, meaning = dflt.get(ax, ("落ちる", ""))
            vals.append((NONE + (f"({meaning})" if meaning else ""), exp))

    def parse(c):
        if "=" in c:
            ax, v = c.split("=", 1)
            return ax, [v]
        ax, v = c.split("∈", 1)
        return ax, v.split(",")
    pairs = []
    for cond, then in raw_pairs:
        a, av = parse(cond)
        b, bv = parse(then.replace("ならば ", ""))
        pairs.append((a, av, b, bv))
    return axes, pairs, problems


def full_grid_size(axes) -> int:
    return math.prod(len(v) for v in axes.values())


def expectation(cell: dict, axes, pairs) -> str:
    exp = dict((ax, dict(vals)) for ax, vals in axes.items())
    if any(exp[ax][v] != "通る" for ax, v in cell.items()):
        return "落ちる"
    for a, av, b, bv in pairs:
        if cell.get(a) in av and cell.get(b) not in bv:
            return "落ちる"
    return "通る"


def selected_cells(axes) -> tuple[list[dict], str]:
    """The cells that are run and how they were chosen (the lead's rule)."""
    names = list(axes)
    values = [[v for v, _ in axes[n]] for n in names]
    if full_grid_size(axes) <= FULL_GRID_LIMIT:
        return [dict(zip(names, c)) for c in itertools.product(*values)], "全格子"
    # deterministic all-pairs cover (greedy): every pair of values of two different axes is in some cell
    uncovered = {(i, a, j, b) for i, j in itertools.combinations(range(len(names)), 2)
                 for a in range(len(values[i])) for b in range(len(values[j]))}
    cells = []
    while uncovered:
        i, a, j, b = min(uncovered)
        cell = [None] * len(names)
        cell[i], cell[j] = a, b
        for k in range(len(names)):
            if cell[k] is not None:
                continue
            best, gain = 0, -1
            for v in range(len(values[k])):
                g = sum(1 for m in range(len(names)) if cell[m] is not None and
                        ((min(k, m), v if k < m else cell[m], max(k, m), cell[m] if k < m else v) in uncovered))
                if g > gain:
                    best, gain = v, g
            cell[k] = best
        for m, n in itertools.combinations(range(len(names)), 2):
            uncovered.discard((m, cell[m], n, cell[n]))
        cells.append(dict((names[k], values[k][cell[k]]) for k in range(len(names))))
    return cells, "2 軸の全組(pairwise)"
