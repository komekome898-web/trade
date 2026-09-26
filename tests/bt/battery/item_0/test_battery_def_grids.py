"""Adversarial tests of the six positive definitions of round r8-1 (0, A, B, C, D, E; C as replaced by
LEAD_DESIGN.md section 8.2 item 1 in round r11-1), written from the definitions' own text (def_grids.py), not from the implementation's cases.

For each definition: every segment of its paragraph is judged; its input space (all axes x all values,
'どれにも当たらない' included) is written out and counted; the cells run follow the lead's rule
(LEAD_DESIGN.md section 7.2 item 12): all cells when there are at most 100,000, otherwise a deterministic cover
of every pair of values of two axes. The full grid of every one of the six has more than 100,000 cells, so no
full grid was run here: the counts and the choice are `SELECTED` below and are checked against def_grids.py.

For each cell run, the expectation comes from the definition's table only (a cell passes iff every value's
expectation is 通る and every condition between two axes holds). The implementation is asked through PROBES:
an axis value that the scene set's machine decides (the runner's checks of settings and types, the scene
set's L-438 (2) check, the line marks of positive definition B, the grid table of positive definition C) has
a probe that builds that input and returns the machine's verdict. The machine's verdict on a cell (every probed
value's verdict, and the conditions among probed axes) must equal the table's expectation restricted to the
probed axes.

Not probed (left out of the comparison, and why) -- what the machine does not decide, read by the critic and
the auditor:
  * positive definitions 0 and E: rules for the scene keeper's own documents (what may be claimed, what the
    scrutiny record holds); the machine for them is the scene keeper's self-check of ROOTCAUSE_r8-1.md (outputs
    named in its section 10), not code of the scene set;
  * definition D: every axis not in PROBES["D"] (the term table's cells and the uses inside ROOTCAUSE_r8-1.md are
    the self-check's; term_marks.py decides only the uses in the other files);
  * definition A: every axis not in PROBES["A"] (e.g. 寄せ集め of settings no run can make, a work done by
    code the primary source does not have, the materials' records, the table's rows): the runner does not see
    them; the adapters' and reproductions' code is read;
  * definition B: every axis not in PROBES["B"] (whether a sentence's truth depends on the sources of truth is
    not decided by a machine; line_marks.py lists every line and makes every marked line need a judgment);
  * definition C: every axis not in PROBES["C"] (the judgments of the requirement segments are read; the machine
    checks their form, test (d) in test_battery_item0.py; whether a scene's `covers` matches what it measures is
    read by the critic, LEAD_DESIGN.md section 8.2 item 1). 升目を覆う場面 is not probed on its own: its
    conditions with 升目の判断 need both values in one input, which the table's own tests in test_battery_item0.py
    run on every cell (test_grid_verdicts_follow_covers_on_every_cell_and_every_cover_state).
"""
from __future__ import annotations

import itertools
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "adapters"))
sys.path.insert(0, str(HERE.parents[3] / "src"))

import def_grids as G  # noqa: E402
import run_battery  # noqa: E402
import scenes  # noqa: E402
import common as C  # noqa: E402

# (full grid, cells run, how) per definition -- written here, checked against def_grids.py
SELECTED = {
    "0": (30958682112000, 92, "2 軸の全組(pairwise)"),
    "A": (2080423437926400000, 71, "2 軸の全組(pairwise)"),  # 2026-09-26: the axis value 「当方の現状」 withdrawn (L-470 / L-474)
    "B": (497664, 59, "2 軸の全組(pairwise)"),
    "C": (10510663680, 59, "2 軸の全組(pairwise)"),
    "D": (68812800, 42, "2 軸の全組(pairwise)"),
    "E": (103680, 24, "2 軸の全組(pairwise)"),
}

_TARGET_ROOTS = run_battery.Roots([str(HERE / "run_battery.py")], [], [])  # a stand-in place of a target


def _verdict(fn) -> str:
    try:
        return "通る" if fn() else "落ちる"
    except (ValueError, AssertionError):
        return "落ちる"


def _setting(decided_from=("選ぶ値",), when="開始前", fn=None, roots=_TARGET_ROOTS, arg="a@b") -> bool:
    C.settings_begin()
    C.configure(fn or run_battery.split_target, arg, what="x", when=when, decided_from=decided_from)
    return run_battery.settings_problem(C.settings_taken(), roots) is None


def _forged(**extra) -> bool:
    rec = C.Record({"fn": "run_battery.split_target", "fn_file": str(HERE / "run_battery.py"), "decided_from": ["選ぶ値"], **extra})
    return run_battery.settings_problem([rec], _TARGET_ROOTS) is None


def _types_has_trade(grade: str) -> bool:
    return run_battery.target_types({"p3-trade": grade}) == ["trade"]


def _repro_setting() -> bool:
    from opponents.repro_engines import lean52 as L
    return _setting(fn=L.resolution_to_timespan, roots=run_battery.roots_of("repro_lean52@tick"), arg=L.Resolution.Tick)


# A stand-in target outside the scene set (round r8-1, definition A (3)): a module in a temporary directory whose
# functions call the strategy (plain and awaited) and return a fresh object
import tempfile as _tempfile  # noqa: E402

_TGT_DIR = Path(_tempfile.mkdtemp(prefix="bt_item0_standin_"))
(_TGT_DIR / "standin_target.py").write_text(
    "def value():\n    return object()\n\n"
    "def drive(cb):\n    return cb()\n\n"
    "async def adrive(cb):\n    return await cb()\n", encoding="utf-8")
sys.path.insert(0, str(_TGT_DIR))
import standin_target as _T  # noqa: E402

_STANDIN_ROOTS = run_battery.Roots([str(_TGT_DIR)], [], [])


def _received(rec) -> bool:
    return run_battery.origin_problem(rec, _STANDIN_ROOTS, "carrier") is None


def _in_plain_call() -> bool:
    return _T.drive(lambda: _received(C.carrier(C.read(_T.value))))


def _in_user_loop() -> bool:
    with C.user_loop_call():
        return _received(C.carrier(C.read(_T.value)))


def _in_coroutine() -> bool:
    import asyncio

    async def strategy():
        return _received(C.carrier(C.read(_T.value)))
    return asyncio.run(_T.adrive(strategy))


def _after_the_run() -> bool:
    got = _T.drive(lambda: None) or C.read(_T.value)  # the target's run is over; the adapter reads afterwards
    return _received(C.carrier(got))


def _called_by_scene_set() -> bool:
    return (lambda cb: cb())(lambda: _received(C.carrier(C.read(_T.value))))  # the scene set calls the "strategy"


N = G.NONE
PROBES: dict[str, dict[str, dict[str, object]]] = {
    "A": {
        "設定の操作を決めた物": {
            "場面が名指す銘柄と事象の型": lambda: _setting(("場面の入力",)),
            "その設定つき対象の選ぶ値": lambda: _setting(("選ぶ値",)),
            "対象の公開の既定": lambda: _setting(("公開の既定",)),
            "その操作までに戦略が (3) の届き方で受けた物": lambda: _setting(("戦略が受けた物",)),
            "まだ届いていない入力の時刻・順・件数": lambda: _setting(("まだ届いていない入力",)),
            N: lambda: _setting(("思いついた値",)),
        },
        "設定の操作の時点": {
            "実行の開始前": lambda: _setting(when="開始前"),
            "実行の途中の公開の API の操作": lambda: _setting(when="その他: 実行の途中の公開の API の操作"),
            "戦略の呼び出しの中": lambda: _setting(when="戦略の呼び出しの中"),
            N + "(ほかの時点)": lambda: _setting(when="その他: ほかの時点"),
        },
        "設定の操作の示し方": {
            "対象の配布物のコードのファイルの行": lambda: _setting(),
            "再現なら一次資料の行": _repro_setting,
            N: lambda: _forged(when="開始前"),
        },
        "設定の操作の時点の書き残し": {
            "書き残す": lambda: _setting(),
            N: lambda: _forged(),
        },
        "p3 の場面の正しさ": {
            "正解と一致": lambda: _types_has_trade("正解と一致"),
            "届いたが値が違う(不一致)": lambda: _types_has_trade("不一致"),
            "対応なし": lambda: _types_has_trade("対応なし"),
            "結果なし": lambda: _types_has_trade("結果なし"),
            N: lambda: _types_has_trade("?"),
        },
        "型の組を設定つき対象の持つ型から決める場面": {
            "L-438 (2) が名指す P0-1・P0-5 の 4 場面": lambda: all(
                scenes.for_target_types(next(s for s in scenes.SCENES if s.id == i), ["trade", "bar"]).input.get("types")
                for i in scenes.L438_2_SCENES),
            "4 場面の外の場面": lambda: any(
                scenes.for_target_types(s, ["trade", "bar"]) is not s for s in scenes.SCENES if s.id not in scenes.L438_2_SCENES),
            N + "(型の組を対象から決めない場面(場面の定義に書いた型の組))": lambda: all(
                scenes.for_target_types(s, []) is s for s in scenes.SCENES if s.id not in scenes.L438_2_SCENES),
        },
        "書き出した場面の数": {
            "L-438 (2) の 4": lambda: scenes.l438_2_ok(scenes.L438_2_SCENES),
            N: lambda: scenes.l438_2_ok(list(scenes.L438_2_SCENES) + ["p1-one-call-per-event"]),
        },
        "書き出した場面の観点": {
            "全部 P0-1 か P0-5": lambda: scenes.l438_2_ok(scenes.L438_2_SCENES),
            N: lambda: scenes.l438_2_ok(["p1-merge-by-time", "p1-typed-events", "p5-same-time-twice", "p3-trade"]),
        },
        "戦略が受けた時": {
            "戦略の 1 回の呼び出しが始まってから戻るまで": lambda: _in_plain_call() and _in_user_loop(),
            "コルーチンの最初に入ってから終わるまで": _in_coroutine,
            "戦略の呼び出しの外で対象の関数を呼んで得た": _after_the_run,
            N: _called_by_scene_set,
        },
        "1 つの設定つき対象の場面の選ぶ値": {
            "全部同じ": lambda: run_battery.one_choose([{"choose": "{}"}, {"choose": "{}"}]),
            N: lambda: run_battery.one_choose([{"choose": "{}"}, {"choose": '{"x": 1}'}]),
        },
    },
    "B": {
        "検査の判断": {
            "当てる範囲の全部のファイルの行をファイルの行ごとの判断で覆う": lambda: _lines_cover_everything(),
            "探す語の一覧で当てる範囲を狭める": lambda: _lines_cover_everything(narrow=True),
            N: lambda: _lines_cover_everything(narrow=True),
        },
        "当てる範囲から除いた物": {
            "ファイルの種類で除いた": lambda: _files_complete(lambda f: f.endswith(".tsv")),
            "名前で除いた": lambda: _files_complete(lambda f: f.endswith("CONSIDERED.md")),
            "書いた周で除いた": lambda: _files_complete(lambda f: f.startswith("ROOTCAUSE_r7")),
            N + "(除かない(14-16 の「除かない」))": lambda: _files_complete(None),
        },
    },
    "D": {
        "示した結果": {
            "意味は 1 つ(全部の出現に判断)": lambda: _terms_ok(),
            "一部の出現の判断で「意味は 1 つ」": lambda: _terms_ok(drop=True),
        },
        "2 つ以上の意味の語の使い方": {
            "裸で使う": lambda: _terms_ok(other=True),
        },
    },
    "C": {
        "升目の表での出方": {
            "観点ごとに観点の範囲の全部の升目が表にある": lambda: _grid_complete(),
            "観点の範囲の升目が 1 つでも表に無い": lambda: _grid_complete(drop_one=True),
        },
        "升目の判断": {
            "場面にした": lambda: _grid_verdict_accepted("場面にした"),
            "測っていない": lambda: _grid_verdict_accepted("測っていない"),  # round r16-1: the value's name (ROOTCAUSE_r16-1.md section 5.1)
            N: lambda: _grid_verdict_accepted("未決"),
        },
        "升目の判断の決め方": {
            "`covers` から機械で決める": lambda: _grid_rule_accepted(None),
            "要件の文を切片に切って名指しを決める機械": lambda: _grid_rule_accepted("words"),
            N: lambda: _grid_rule_accepted("all_not_measured"),
        },
    },
}


def _terms_ok(drop: bool = False, other: bool = False) -> bool:
    """Definition D's machine (term_marks.py) on the judgments as they are, with one judgment dropped, or with one
    judgment turned into another meaning."""
    import term_marks
    j = dict(term_marks.judgments())
    k = sorted(j)[0]
    if drop:
        del j[k]
    if other:
        j[k] = "別の意味: 試し"
    return not term_marks.problems(j)


def _files_complete(exclude) -> bool:
    """Definition B's machine lists every file the scene keeper writes (all of `git ls-files` and the untracked
    files there, but the runner's output); `exclude` = a checker that leaves some out, which must not match."""
    import subprocess
    import line_marks
    every = {f for f in subprocess.run(["git", "ls-files", "--others", "--cached", "--exclude-standard", "."], cwd=HERE,
                                       capture_output=True, text=True).stdout.split()
             if not f.startswith("survey_results/") and "__pycache__" not in f and not f.endswith(".pyc")}
    listed = [f for f in line_marks.files() if not (exclude and exclude(f))]
    return set(listed) == every


def _lines_cover_everything(narrow: bool = False) -> bool:
    """The machine of definition B: every line listed, every marked line judged. `narrow` = a checker that only
    lists the marked lines (a word list), which the definition refuses: its count of lines is not the files'."""
    import line_marks
    lines = line_marks.all_lines()
    listed = [x for x in lines if x[3]] if narrow else lines
    total = sum((HERE / f).read_text(encoding="utf-8").count("\n") + 1 for f in line_marks.files())
    return len(listed) == total


def _grid_complete(drop_one: bool = False) -> bool:
    import grid_c
    rows = grid_c.table(scenes.SCENES)
    if drop_one:
        rows = rows[1:]
    want = sum(len(grid_c.cells(vp)) for vp in grid_c.VIEWPOINTS)
    return len({(r["viewpoint"], r["event"], r["see"], r["extra"]) for r in rows}) == want


def _grid_verdict_accepted(verdict: str) -> bool:
    """Definition C's machine (grid_c.problems) on the table of the scene set with one row given `verdict`: the row
    is the first whose verdict is `verdict` when there is one, else the first row (a verdict no row can have)."""
    import grid_c
    rows = [dict(r) for r in grid_c.table(scenes.SCENES)]
    n = next((i for i, r in enumerate(rows) if r["verdict"] == verdict), 0)
    rows[n]["verdict"] = verdict
    return not grid_c.problems(scenes.SCENES, rows)


def _grid_rule_accepted(other) -> bool:
    """Definition C's machine on a table made by covers (None), by a reading of the requirements' words that puts a
    covered cell outside because its see-path is not the one the measuring text names ("words": P0-7's cells that
    reach the strategy's call are made 測っていない), or by no rule (every cell 測っていない)."""
    import grid_c
    rows = [dict(r) for r in grid_c.table(scenes.SCENES)]
    for r in rows:
        if other == "all_not_measured" or (other == "words" and r["viewpoint"] == "P0-7" and r["see"] == "戦略の呼び出しに届く物"):
            r["verdict"], r["scenes"] = "測っていない", []
    return not grid_c.problems(scenes.SCENES, rows)


def test_every_paragraph_segment_is_judged_once_and_every_axis_can_pass():
    for k in "0ABCDE":
        axes, pairs, problems = G.derive(k)
        assert not problems, (k, problems[:3])
        assert all(any(e == "通る" for _, e in vals) for vals in axes.values()), k
        for a, av, b, bv in pairs:
            assert a in axes and b in axes, (k, a, b)


def test_the_full_grids_are_counted_and_the_cells_run_follow_the_leads_rule():
    for k, (full, n, how) in SELECTED.items():
        axes, _, _ = G.derive(k)
        cells, got_how = G.selected_cells(axes)
        assert G.full_grid_size(axes) == full, k
        assert (len(cells), got_how) == (n, how), k
        assert (full <= G.FULL_GRID_LIMIT) == (how == "全格子"), k
        # the cover, checked here on its own: every pair of values of two axes is in some cell run
        names = list(axes)
        seen = {(a, x, b, y) for c in cells for a, b in itertools.combinations(names, 2) for x, y in [(c[a], c[b])]}
        for a, b in itertools.combinations(names, 2):
            for x, _ in axes[a]:
                for y, _ in axes[b]:
                    assert (a, x, b, y) in seen, (k, a, x, b, y)


@pytest.mark.parametrize("k", ["A", "B", "C", "D"])
def test_the_machine_agrees_with_the_definition_on_every_cell_run(k):
    axes, pairs, _ = G.derive(k)
    probes = PROBES[k]
    for ax, vals in probes.items():
        assert ax in axes, (k, ax)
        assert set(vals) <= {v for v, _ in axes[ax]}, (k, ax, set(vals) - {v for v, _ in axes[ax]})
    cache = {(ax, v): _verdict(fn) for ax, vals in probes.items() for v, fn in vals.items()}
    table = {ax: dict(vals) for ax, vals in axes.items()}
    for ax, v in cache:  # every probed value: the machine says what the definition's table says
        assert cache[(ax, v)] == table[ax][v], (k, ax, v, cache[(ax, v)], table[ax][v])
    cells, _ = G.selected_cells(axes)
    compared = 0
    for cell in cells:
        sub = {ax: cell[ax] for ax in probes if cell[ax] in probes[ax]}
        if len(sub) != len(probes):
            continue  # a value of a probed axis has no probe: left out (the NOT list in the module docstring)
        want = G.expectation(sub, {ax: axes[ax] for ax in sub},
                             [p for p in pairs if p[0] in sub and p[2] in sub])
        got = "通る" if all(cache[(ax, v)] == "通る" for ax, v in sub.items()) else "落ちる"
        assert got == want, (k, sub)
        compared += 1
    assert compared > 0, k
