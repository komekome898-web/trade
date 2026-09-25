"""Round r16-1 (critic i0-r15-05 [stop], i0-r15-06 [fix]; ROOTCAUSE_r16-1.md section 4, families 10-14 and 1'').
Written BEFORE the machines existed (the delegation's scrutiny (6)); every oracle below is written from the rule's
sentence in ROOTCAUSE_r16-1.md section 3, not from the code it checks.

Family 10 -- a viewpoint's text names values; the viewpoint's scenes' inputs give each of them:
  * the values a viewpoint names = the event-axis values ("E:") and extra-axis values ("X:") of the segments of the
    viewpoint's own row of REQUIREMENTS.md section 2 (columns 2 and 3), by the judgments of grid_c_judgments.tsv;
    see-path values ("V:") are the scenes' declarations and the critic's reading (LEAD_DESIGN.md section 8.5 item 24);
  * an event value is given by a scene when it is one of F's types of the scene's input (the r13-1 oracle);
  * an extra value is given by the input's fields: `iso` (a str) -> (時刻の単位, ISO 文字列); `unit` (one of s / ms /
    us, with a `time`) -> (時刻の単位, 秒 / ミリ / マイクロ秒); an event item (of `events` or a stream; a `type_plan`
    scene: the input built for all six types) whose `ts_ns` is an int (not a bool) -> (時刻の単位, int64 ナノ秒);
    `plug` (a str holding ":") -> (差し込む口, the text before the first ":", stripped). Anything else in those
    fields is refused (ValueError): an `iso` that is not a str, a `unit` outside the three, a `time` without `unit`
    or a `unit` without `time`, a `plug` that is not a str or has no ":".
Family 11 -- the P0-2 unit scenes: the answer is (the value the input holds) x (10^9 / 10^6 / 10^3): a str is its
  decimal, an int itself, a float the binary value it holds (float.as_integer_ratio); a whole number of ns is the
  answer, anything else answers "no int64 ns" (scenes.NO_INT). Every unit has every form (decimal text with a whole ns
  count, decimal text with sub-ns digits, int, float holding a whole ns count, float holding sub-ns digits) except a
  form no value can have at the scenes' time (the float spacing there is a whole number of ns).
Family 12 -- the unit scenes' grader: the target's value counts when it is an int (not a bool) or a numpy integer,
  inside int64; everything else grades as null.
Family 13 -- the unit scenes' provenance, and `common.unit_time`: an entry is used only when its unit is the scene's
  unit and its forms hold the input's form (the first such entry, in the adapter's order); none -> not supported; the
  entry raising -> not supported (the tool refused); otherwise the tool's time object read to int ns exactly (an int
  as it is, a numpy integer as int, a pandas Timestamp by .value, an aware datetime by its fields, a naive datetime as
  UTC, a numpy datetime64 at ns); anything else is reported as it is (the grader then gives null). The value handed to
  the entry is the input's object itself (the adapter converts nothing).
Family 14 -- a viewpoint's title is REQUIREMENTS.md section 2, column 2, character for character.
Family 1'' -- a cell no scene counts is "測っていない" with the reason: "宣言した場面はあるが、その事象の型が場面の入力から出ない"
  when a scene of the viewpoint declares it, else "この升目を宣言した場面が無い"; values stay two.

Not in the grids (and why):
  * see-path coverage (a viewpoint naming 発注 / 取消 / a read path): declarations and the critic's reading
    (LEAD_DESIGN.md section 8.5 item 24; the lead's answer 60 defers the P0-6 / P0-7 axes);
  * which entry of a tool reads which unit: the tool's code or documents, read by the critic (the adapter's comment
    names the line);
  * the exact decimal of floats outside the unit scenes' `time` (prices, quantities): what those scenes measure does
    not turn on the float's last binary digits;
  * numpy datetime64 finer than ns (ps / fs): no tool of the survey makes them.
"""
from __future__ import annotations

import datetime as dt
import math
import re
import sys
from dataclasses import replace
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "adapters"))
sys.path.insert(0, str(HERE.parents[3] / "src"))

import grid_c  # noqa: E402
import scenes  # noqa: E402
import test_battery_r13_covers_of as CO  # noqa: E402

REQ = HERE.parents[3] / "docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/REQUIREMENTS.md"
VPS = [f"P0-{i}" for i in range(1, 8)]
DELIMS = r"[・、。()（）/「」:]|\*\*|\+"  # the requirements' segment delimiters (grid_c.py's docstring)
UNIT_WORD = {"s": "秒", "ms": "ミリ", "us": "マイクロ秒"}
FACTOR = {"s": 10 ** 9, "ms": 10 ** 6, "us": 10 ** 3}
TIME_AXIS, PLUG_AXIS = "時刻の単位", "差し込む口"
K_NS = 1_704_067_200_123_456_789  # 2024-01-01T00:00:00.123456789Z, typed here by hand
WHY_NONE, WHY_NOT_INPUT = "この升目を宣言した場面が無い", "宣言した場面はあるが、その事象の型が場面の入力から出ない"


class Refused(Exception):
    pass


# ---------------------------------------------------------------- the requirements' rows, read here on their own
def _cells(ln: str) -> list[str]:
    return [x.strip() for x in ln.strip().strip("|").split("|")]


def _rows() -> list[tuple[int, int, str, str]]:
    """(line, column, first cell, text) of the source cells: section 1's item-0 row (column 4), section 2's rows
    (columns 2 and 3)."""
    out = []
    for n, ln in enumerate(REQ.read_text(encoding="utf-8").split("\n"), 1):
        if not ln.startswith("|"):
            continue
        c = _cells(ln)
        if c[0] == "0" and len(c) >= 4:
            out.append((n, 4, c[0], c[3]))
        elif re.fullmatch(r"P0-[1-7]", c[0]):
            out += [(n, 2, c[0], c[1]), (n, 3, c[0], c[2])]
    return out


def _judged() -> list[tuple[str, str, str]]:
    """(first cell of the row, segment, judgment) of every segment, in order."""
    segs = [(first, s.strip()) for _, _, first, text in _rows() for s in re.split(DELIMS, text) if s.strip()]
    js = []
    for ln in (HERE / "grid_c_judgments.tsv").read_text(encoding="utf-8").split("\n"):
        if ln and not ln.startswith("#"):
            p = ln.split("\t")
            js.append((p[1], p[2]))
    assert [s for _, s in segs] == [s for s, _ in js]
    return [(f, s, j) for (f, s), (_, j) in zip(segs, js)]


def oracle_named(vp: str) -> list[tuple[str, str]]:
    out: list = []
    for first, _, j in _judged():
        if first != vp:
            continue
        if j.startswith("E:"):
            item = ("事象", j[2:])
        elif j.startswith("X:"):
            _, v, ax, val = j.split(":", 3)
            assert v == vp
            item = (ax, val)
        else:
            continue
        if item not in out:
            out.append(item)
    return out


def _events(s) -> list:
    src = scenes.for_target_types(s, CO.ALL_SIX) if s.type_plan is not None else s
    inp = src.input if src is not None and isinstance(src.input, dict) else {}
    evs = list(inp.get("events") or [])
    for stream in (inp.get("streams") or {}).values():
        evs += list(stream)
    return evs


def oracle_extra(s) -> set:
    inp = s.input if isinstance(s.input, dict) else {}
    out = set()
    if "iso" in inp:
        if not isinstance(inp["iso"], str):
            raise Refused("iso")
        out.add((TIME_AXIS, "ISO 文字列"))
    if ("unit" in inp) != ("time" in inp):
        raise Refused("unit/time")
    if "unit" in inp:
        if inp["unit"] not in UNIT_WORD:
            raise Refused("unit")
        out.add((TIME_AXIS, UNIT_WORD[inp["unit"]]))
    if any(isinstance(e, dict) and type(e.get("ts_ns")) is int for e in _events(s)):
        out.add((TIME_AXIS, "int64 ナノ秒"))
    if "plug" in inp:
        p = inp["plug"]
        if not isinstance(p, str) or ":" not in p:
            raise Refused("plug")
        out.add((PLUG_AXIS, p.split(":", 1)[0].strip()))
    return out


def oracle_coverage(scs) -> list[dict]:
    rows = []
    for vp in VPS:
        for ax, val in oracle_named(vp):
            ids = [s.id for s in scs if s.viewpoint == vp
                   and (val in CO._oracle_types(s) if ax == "事象" else (ax, val) in oracle_extra(s))]
            rows.append({"viewpoint": vp, "axis": ax, "value": val, "scenes": ids})
    return rows


# ---------------------------------------------------------------- family 14: the viewpoints' titles
def title_problems(text: str) -> list:
    out = []
    by = {first: t for _, col, first, t in _rows() if col == 2}
    for vp in VPS:
        if scenes.VIEWPOINTS.get(vp) != by[vp]:
            out.append(("VIEWPOINTS", vp, scenes.VIEWPOINTS.get(vp)))
        if f"\n## {vp} {by[vp]}\n" not in text:
            out.append(("見出し", vp))
    return out


def test_viewpoint_titles_are_the_requirements_text():
    import gen_definitions
    assert title_problems(gen_definitions.render()) == []
    assert title_problems((HERE / "DEFINITIONS.md").read_text(encoding="utf-8")) == []


def test_mutants_of_viewpoint_titles_are_caught(monkeypatch):
    import gen_definitions
    by = {first: t for _, col, first, t in _rows() if col == 3}
    for name, m in {"要約を縮める": {**scenes.VIEWPOINTS, "P0-2": "時刻が UTC の int64 ナノ秒で表されること"},
                    "別の列を読む": dict(by)}.items():
        monkeypatch.setattr(scenes, "VIEWPOINTS", m)
        assert title_problems(gen_definitions.render()), name


# ---------------------------------------------------------------- family 10: named values and the inputs
def _copies(s):
    """Copies of a scene's input across the fields the rule reads (the input space, not the machine's branches)."""
    inp = dict(s.input) if isinstance(s.input, dict) else {}
    out = [("as is", inp)]
    for k in ("iso", "unit", "time", "plug", "events", "streams"):
        if k in inp:
            out.append((f"no {k}", {x: v for x, v in inp.items() if x != k}))
    out += [("iso str", {**inp, "iso": "2024-01-01T00:00:00Z"}), ("iso int", {**inp, "iso": 1})]
    for u in ("s", "ms", "us", "ns", "sec"):
        out += [(f"unit {u} with time", {**inp, "unit": u, "time": "1"}),
                (f"unit {u} without time", {x: v for x, v in {**inp, "unit": u}.items() if x != "time"})]
    out.append(("time without unit", {x: v for x, v in {**inp, "time": 1}.items() if x != "unit"}))
    for head in ("約定模型", "遅延模型", "費用", "口座", "未知の口"):
        out.append((f"plug {head}", {**inp, "plug": f" {head} : x"}))
    out += [("plug no colon", {**inp, "plug": "口座 だけ"}), ("plug not str", {**inp, "plug": 5})]
    evs = list(inp.get("events") or [])
    if evs and isinstance(evs[0], dict):
        for name, v in (("ts float", 1.0 * scenes.T0), ("ts bool", True), ("ts str", str(scenes.T0))):
            out.append((name, {**inp, "events": [{**evs[0], "ts_ns": v}] + evs[1:]}))
        out.append(("ts missing", {**inp, "events": [{k: v for k, v in evs[0].items() if k != "ts_ns"}] + evs[1:]}))
        out.append(("only non-int ts", {**inp, "events": [{**e, "ts_ns": 1.5} if isinstance(e, dict) else e for e in evs]}))
    return out


def test_extra_values_follow_the_rule_on_every_copy():
    seen = set()
    for s in scenes.SCENES:
        for name, inp in _copies(s):
            c = replace(s, input=inp)
            try:
                want = oracle_extra(c)
            except Refused:
                with pytest.raises(ValueError):
                    scenes.extra_values_of(c)
                seen.add("refused")
                continue
            assert scenes.extra_values_of(c) == want, (s.id, name)
            seen |= {v for _, v in want}
    assert {"refused", "ISO 文字列", "秒", "ミリ", "マイクロ秒", "int64 ナノ秒", "口座", "未知の口"} <= seen


def test_the_axis_names_are_the_judgments():
    _, _, extra = grid_c.axes()
    assert ("P0-2", TIME_AXIS) in extra and ("P0-7", PLUG_AXIS) in extra
    assert (scenes.TIME_AXIS, scenes.PLUG_AXIS) == (TIME_AXIS, PLUG_AXIS)
    assert scenes.UNIT_WORDS == UNIT_WORD


def coverage_problems(scs) -> list:
    got = grid_c.named_coverage(scs)
    want = oracle_coverage(scs)
    return [] if got == want else [("coverage", got, want)]


def test_every_value_a_viewpoint_names_is_given_by_an_input():
    assert coverage_problems(scenes.SCENES) == []
    empty = [(r["viewpoint"], r["axis"], r["value"]) for r in oracle_coverage(scenes.SCENES) if not r["scenes"]]
    assert empty == [], empty
    # dropping each scene in turn: the machine follows the oracle, and a value loses its scenes somewhere
    lost = 0
    for i in range(len(scenes.SCENES)):
        scs = scenes.SCENES[:i] + scenes.SCENES[i + 1:]
        assert coverage_problems(scs) == [], scenes.SCENES[i].id
        lost += sum(1 for r in oracle_coverage(scs) if not r["scenes"])
    assert lost > 0


def test_outside_values_have_a_reason():
    named = {vp: {v for ax, v in oracle_named(vp) if ax != "事象"} for vp in VPS}
    axis_of = {"P0-2": TIME_AXIS, "P0-7": PLUG_AXIS}
    for s in scenes.SCENES:
        ax = axis_of.get(s.viewpoint)
        for a, v in oracle_extra(s):
            if a == ax and v not in named[s.viewpoint]:
                assert v in scenes.OUTSIDE_EXTRA and scenes.OUTSIDE_EXTRA[v], (s.id, v)


def definitions_coverage_problems(text: str, scs) -> list:
    out = []
    for vp in VPS:
        rows = [r for r in oracle_coverage(scs) if r["viewpoint"] == vp]
        want = [f"- {r['axis']} {r['value']}: " + (", ".join(f"`{i}`" for i in r["scenes"]) or "無し(場面が無い)")
                for r in rows] or ["- 観点の文は事象・追加の軸の値を名指さない"]
        head = text.find(f"\n### {vp}(升目 ")
        body = text[head:text.find("\n### P0-", head + 5) if vp != "P0-7" else len(text)]
        for w in want:
            if f"\n{w}\n" not in body:
                out.append((vp, w))
    return out


def test_the_definitions_show_the_coverage_the_rule_gives():
    import gen_definitions
    assert definitions_coverage_problems(gen_definitions.render(), scenes.SCENES) == []
    assert definitions_coverage_problems((HERE / "DEFINITIONS.md").read_text(encoding="utf-8"), scenes.SCENES) == []


def _coverage_mutants():
    orig_extra, orig_named = scenes.extra_values_of, grid_c.named_values

    def no_unit(s):
        return {x for x in orig_extra(s) if x[1] not in ("秒", "ミリ", "マイクロ秒")}

    def no_iso(s):
        return {x for x in orig_extra(s) if x[1] != "ISO 文字列"}

    def no_event_time(s):
        return {x for x in orig_extra(s) if x[1] != "int64 ナノ秒"}

    def no_plug(s):
        return {x for x in orig_extra(s) if x[0] != PLUG_AXIS}

    def other_row(vp):
        return orig_named(VPS[(VPS.index(vp) + 1) % len(VPS)])
    return {"unit を読まない": ("extra_values_of", no_unit), "iso を読まない": ("extra_values_of", no_iso),
            "事象の時刻を読まない": ("extra_values_of", no_event_time), "plug を読まない": ("extra_values_of", no_plug),
            "別の行を読む": ("named_values", other_row)}


@pytest.mark.parametrize("name", sorted(_coverage_mutants()))
def test_mutants_of_the_coverage_machine_are_caught(monkeypatch, name):
    where, fn = _coverage_mutants()[name]
    monkeypatch.setattr(scenes if where == "extra_values_of" else grid_c, where, fn)
    assert coverage_problems(scenes.SCENES), name


def test_a_mutant_coverage_counting_another_viewpoint_is_caught(monkeypatch):
    orig = grid_c.named_coverage

    def other_vp(scs):
        return orig([replace(s, viewpoint="P0-2") if s.viewpoint == "P0-7" else s for s in scs])
    monkeypatch.setattr(grid_c, "named_coverage", other_vp)
    assert coverage_problems(scenes.SCENES)


# ---------------------------------------------------------------- family 11: the unit scenes' answers and forms
def unit_scenes(scs=None) -> list:
    return [s for s in (scs or scenes.SCENES) if isinstance(s.input, dict) and "unit" in s.input]


def _held(v) -> Fraction:
    if type(v) is str:
        return Fraction(v)
    if type(v) is int:
        return Fraction(v)
    if type(v) is float:
        n, d = v.as_integer_ratio()
        return Fraction(n, d)
    raise TypeError(type(v))


def oracle_answer(s, held=_held):
    q = held(s.input["time"]) * FACTOR[s.input["unit"]]
    return {"int64_ns": int(q) if q.denominator == 1 else scenes.NO_INT}


def answer_problems(scs, held=_held) -> list:
    out = []
    for s in unit_scenes(scs):
        if s.expected != oracle_answer(s, held):
            out.append((s.id, s.expected, oracle_answer(s, held)))
        if s.viewpoint != "P0-2" or s.kind != "value" or not s.graded_from:
            out.append((s.id, "not a P0-2 value scene graded by the runner"))
    return out


def test_unit_scene_answers_are_the_closed_form():
    assert unit_scenes(), "no unit scene"
    assert answer_problems(scenes.SCENES) == []
    assert isinstance(scenes.NO_INT, str) and scenes.NO_INT


def _form(v) -> tuple[str, bool]:
    return type(v).__name__, (_held(v) * 1).denominator == 1


def test_unit_scenes_cover_every_form_of_every_unit():
    for u, f in FACTOR.items():
        mine = [s for s in unit_scenes() if s.input["unit"] == u]
        forms = {(type(s.input["time"]).__name__, (_held(s.input["time"]) * f).denominator == 1) for s in mine}
        texts = [s for s in mine if type(s.input["time"]) is str and (_held(s.input["time"]) * f).denominator == 1]
        assert texts and all(_held(s.input["time"]) * f == K_NS for s in texts), u  # the known time, in every unit
        want = {("str", True), ("str", False), ("int", True), ("float", True), ("float", False)}
        x = float(texts[0].input["time"])
        if (Fraction(math.ulp(x)) * f).denominator == 1:  # every float of this binade holds a whole ns count
            want.discard(("float", False))
        assert forms == want, (u, sorted(forms), sorted(want))
        assert len(mine) == len(forms), u  # one scene per form


def test_float_inputs_show_their_exact_value():
    text = (HERE / "DEFINITIONS.md").read_text(encoding="utf-8")
    import gen_definitions
    rendered = gen_definitions.render()
    for s in unit_scenes():
        v = s.input["time"]
        if type(v) is float:
            exact = str(Decimal(v))
            assert exact in s.derivation, s.id
            for t in (text, rendered):
                block = t[t.index(f"### `{s.id}`"):]
                line = [ln for ln in block.split("\n") if ln.startswith("- **入力**")][0]
                assert f"time = {exact}" in line, (s.id, line)


def test_mutants_of_the_answer_oracle_are_caught():
    def shortest(v):
        return Fraction(repr(v)) if type(v) is float else _held(v)

    def floor_digits(v):
        q = _held(v)
        return Fraction(math.floor(q * 10 ** 6), 10 ** 6)
    assert answer_problems(scenes.SCENES, shortest), "a float read by its shortest repr"
    assert answer_problems(scenes.SCENES, floor_digits), "digits cut"
    swapped = [replace(s, input={**s.input, "unit": {"s": "ms", "ms": "us", "us": "s"}[s.input["unit"]]})
               for s in unit_scenes()]
    assert answer_problems(swapped), "factor swapped"


# ---------------------------------------------------------------- family 12: the grader
def oracle_grade(out) -> dict:
    v = out.get("ns") if isinstance(out, dict) else None
    ok = (type(v) is int) or isinstance(v, np.integer)
    if ok and -2 ** 63 <= int(v) < 2 ** 63:
        return {"int64_ns": int(v)}
    return {"int64_ns": None}


GRADE_VALUES = [K_NS, True, False, float(K_NS), 1704067200000000000.0, np.int64(K_NS), np.uint64(K_NS),
                np.int32(7), np.float64(1704067200000000000.0), Decimal(K_NS), Fraction(K_NS), str(K_NS), None,
                2 ** 63, 2 ** 63 - 1, -2 ** 63, -2 ** 63 - 1, [K_NS], {"v": K_NS}]


def grader_problems(grade) -> list:
    out = []
    cases = [{"ns": v} for v in GRADE_VALUES] + [{}, {"other": K_NS}, None, K_NS]
    for c in cases:
        got = grade(c)
        if got != oracle_grade(c) or type(got.get("int64_ns")) not in (int, type(None)):
            out.append((repr(c)[:60], got))
    return out


def test_unit_grader_on_every_value_type():
    import run_battery as R
    ids = [s.id for s in unit_scenes()]
    assert ids and all(R.GRADERS.get(i) is R._grade_unit_time for i in ids)
    sc = unit_scenes()[0]
    assert grader_problems(lambda o: R._grade_unit_time(sc, o if isinstance(o, dict) else {})) == []
    # through the runner's own path (a non-dict output grades as an empty dict there)
    from adapters.protocol import SceneResult
    for c in [{"ns": v} for v in GRADE_VALUES] + [K_NS]:
        g = R.graded_output(SceneResult("ok", output=c), sc)
        assert {"int64_ns": g["int64_ns"]} == oracle_grade(c if isinstance(c, dict) else {}), repr(c)[:60]


def test_mutants_of_the_unit_grader_are_caught():
    def float_equal(o):
        v = o.get("ns") if isinstance(o, dict) else None
        return {"int64_ns": int(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and v == int(v) else None}

    def with_bool(o):
        v = o.get("ns") if isinstance(o, dict) else None
        return {"int64_ns": int(v) if isinstance(v, (int, np.integer)) else None}

    def no_range(o):
        v = o.get("ns") if isinstance(o, dict) else None
        return {"int64_ns": int(v) if (type(v) is int or isinstance(v, np.integer)) else None}
    for name, m in {"float が整数に等しければ通す": float_equal, "bool を通す": with_bool, "範囲を見ない": no_range}.items():
        assert grader_problems(m), name


# ---------------------------------------------------------------- family 13: provenance and common.unit_time
def test_unit_scenes_are_provenance_checked():
    import run_battery as R
    import common as C
    from adapters.protocol import SceneResult
    from bot.bt.core import to_nanos

    def scene_set_reader(v):
        return v
    for s in unit_scenes():
        assert s.id in R.PROVENANCE_SCENES
        good = SceneResult("ok", output={"ns": K_NS}, provenance={"reader": C.qualname(to_nanos)})
        bad = SceneResult("ok", output={"ns": K_NS}, provenance={"reader": C.qualname(scene_set_reader)})
        none = SceneResult("ok", output={"ns": K_NS}, provenance={})
        assert R.provenance_problem(good, s, "new_impl") is None, s.id
        assert R.provenance_problem(bad, s, "new_impl") is not None, s.id
        assert R.provenance_problem(none, s, "new_impl") is not None, s.id
        assert R.checked(bad, s, "new_impl").status == "error"


class _Rec:
    def __init__(self, result):
        self.result, self.args = result, []

    def __call__(self, v):
        self.args.append(v)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def reader_fn(v):  # a named reader for the entries (its file is this test's; provenance is not checked here)
    return v


def oracle_ns(r):
    if isinstance(r, pd.Timestamp):
        return int(r.value)
    if isinstance(r, dt.datetime):
        d = r if r.tzinfo is not None else r.replace(tzinfo=dt.timezone.utc)
        delta = d - dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc)
        return (delta.days * 86_400 + delta.seconds) * 10 ** 9 + delta.microseconds * 1000
    if isinstance(r, np.datetime64):
        return int(r.astype("datetime64[ns]").astype(np.int64))
    if type(r) is int or isinstance(r, np.integer):
        return int(r) if isinstance(r, np.integer) else r
    return r


OUTCOMES = [7, True, 7.0, np.int64(7), dt.datetime(2024, 1, 1, 0, 0, 0, 123456, tzinfo=dt.timezone.utc),
            dt.datetime(2024, 1, 1, 9, 0, 0, 123456, tzinfo=dt.timezone(dt.timedelta(hours=9))),
            dt.datetime(2024, 1, 1, 0, 0, 0, 123456), pd.Timestamp(K_NS, unit="ns", tz="UTC"), pd.Timestamp(K_NS),
            np.datetime64(K_NS, "ns"), np.datetime64(1704067200123, "ms"), "2024", ValueError("refused")]
ENTRY_SETS = {
    "none": [],
    "s str": [("s", ("str",))],
    "s int+float": [("s", ("int", "float"))],
    "ms all": [("ms", ("str", "int", "float"))],
    "us float, then us all": [("us", ("float",)), ("us", ("str", "int", "float"))],
    "every unit": [(u, ("str", "int", "float")) for u in ("s", "ms", "us")],
}
INPUTS = [("s", "1.5"), ("s", 2), ("s", 2.5), ("ms", "3"), ("ms", 4), ("us", 5.25), ("us", "6"), ("s", True)]


def unit_time_problems(unit_time) -> list:
    import common as C
    base = unit_scenes()[0]
    out = []
    for ename, spec in ENTRY_SETS.items():
        for u, v in INPUTS:
            for r in OUTCOMES:
                recs = [_Rec(r) for _ in spec]
                entries = [{"unit": eu, "forms": ef, "how": f"entry {i}", "reader": reader_fn, "call": rec}
                           for i, ((eu, ef), rec) in enumerate(zip(spec, recs))]
                sc = replace(base, input={"time": v, "unit": u})
                try:
                    res = unit_time(sc, entries, tried="試したこと: なし")
                except Exception as exc:  # noqa: BLE001
                    out.append((ename, u, repr(v), repr(r)[:40], f"raised {type(exc).__name__}"))
                    continue
                form = {str: "str", int: "int", float: "float"}.get(type(v), type(v).__name__)
                pick = [i for i, (eu, ef) in enumerate(spec) if eu == u and form in ef]
                key = (ename, u, repr(v), repr(r)[:40])
                if not pick:
                    if res.status != "not_supported" or any(rec.args for rec in recs):
                        out.append(key + ("want not_supported, no call", res.status))
                    continue
                i = pick[0]
                if [len(rec.args) for rec in recs] != [1 if j == i else 0 for j in range(len(recs))] \
                        or recs[i].args[0] is not v:
                    out.append(key + ("entry call", [rec.args for rec in recs]))
                    continue
                if isinstance(r, Exception):
                    if res.status != "not_supported":
                        out.append(key + ("want not_supported on refusal", res.status))
                    continue
                want = oracle_ns(r)
                got = res.output.get("ns") if res.status == "ok" and isinstance(res.output, dict) else "no output"
                if res.status != "ok" or got != want or type(got) is not type(want) \
                        or str(res.provenance.get("reader")) != str(C.qualname(reader_fn)):
                    out.append(key + ("want", want, "got", res.status, got))
    return out


def test_unit_time_uses_only_an_entry_of_the_scenes_unit():
    import common as C
    assert unit_time_problems(C.unit_time) == []


def test_mutants_of_unit_time_are_caught(monkeypatch):
    import common as C
    orig = C.unit_time

    def any_unit(sc, entries, tried=""):
        return orig(replace(sc, input={**sc.input, "unit": entries[0]["unit"]}) if entries else sc, entries, tried)

    def refusal_raises(sc, entries, tried=""):
        wrapped = [{**e, "call": (lambda f: (lambda v: f(v)))(e["call"])} for e in entries]
        res = orig(sc, wrapped, tried)
        if res.status == "not_supported" and any(e["unit"] == sc.input["unit"] for e in entries):
            raise RuntimeError("refusal made an error")
        return res

    def converts(sc, entries, tried=""):
        v = sc.input["time"]
        conv = int(float(v)) if not isinstance(v, bool) else v
        return orig(replace(sc, input={**sc.input, "time": conv}), entries, tried)
    for name, m in {"別の単位の入口を使う": any_unit, "断りを結果なしにする": refusal_raises, "adapter が換算する": converts}.items():
        assert unit_time_problems(m), name


# ---------------------------------------------------------------- family 1'': the reason of a cell not counted
def oracle_why(vp, cell, scs) -> tuple[str, str]:
    mine = [s for s in scs if s.viewpoint == vp]
    if any(tuple(cell) in set(CO._oracle(s)[0]) for s in mine):
        return "場面にした", ""
    if any(tuple(cell) in {tuple(c) for c in s.declares} for s in mine):
        return "測っていない", WHY_NOT_INPUT
    return "測っていない", WHY_NONE


def why_problems(scs) -> list:
    out = []
    for r in grid_c.table(scs):
        cell = (r["event"], r["see"], r["extra"])
        if (r["verdict"], r.get("why")) != oracle_why(r["viewpoint"], cell, scs):
            out.append((r["viewpoint"], cell, r["verdict"], r.get("why")))
    return out


def _fake(i, vp, decl, give):
    inp = {"events": [{"kind": k, "ts_ns": scenes.T0} for k in give]}
    return scenes.Scene(id=i, viewpoint=vp, kind="value", title="", input=inp, expected=None, derivation="",
                        measures="", declares=tuple(decl))


def test_every_not_measured_cell_has_the_reason_the_rule_gives():
    assert grid_c.VERDICTS == ("場面にした", "測っていない")
    assert why_problems(scenes.SCENES) == []
    # the grid: a cell declared and given / declared and not given / not declared / declared in another viewpoint
    cell = ("約定", "戦略の呼び出しに届く物", "")
    x2 = ("約定", "戦略の呼び出しに届く物", "秒")
    grids = [
        [_fake("a", "P0-1", [cell], ["trade"])],
        [_fake("a", "P0-1", [cell], [])],
        [_fake("a", "P0-1", [], ["trade"])],
        [_fake("a", "P0-3", [cell], ["trade"])],
        [_fake("a", "P0-1", [cell], []), _fake("b", "P0-1", [cell], ["trade"])],
        [_fake("a", "P0-2", [x2], [])],
        [_fake("a", "P0-2", [x2], ["trade"])],
        [],
    ]
    kinds = set()
    for scs in grids:
        assert why_problems(scs) == [], [s.declares for s in scs]
        kinds |= {oracle_why(r["viewpoint"], (r["event"], r["see"], r["extra"]), scs) for r in grid_c.table(scs)}
    assert {("場面にした", ""), ("測っていない", WHY_NONE), ("測っていない", WHY_NOT_INPUT)} <= kinds
    # the table in DEFINITIONS.md shows the reason on every row
    text = (HERE / "DEFINITIONS.md").read_text(encoding="utf-8")
    rows = {(r["viewpoint"], r["event"], r["see"], r["extra"] or "—"): r for r in grid_c.table(scenes.SCENES)}
    vp = None
    n = 0
    for ln in text.split("\n"):
        m = re.match(r"### (P0-\d)(升目 ", ln)
        if m:
            vp = m.group(1)
        elif vp and ln.startswith("| ") and not ln.startswith("| 事象") and ln.count("|") == 6:
            e, s_, x, verdict, _ = _cells(ln)
            r = rows[(vp, e, s_, x)]
            assert verdict == (r["verdict"] if r["verdict"] == "場面にした" else f"測っていない({r['why']})"), ln
            n += 1
        elif ln.startswith("## "):
            vp = None
    assert n == len(rows)


def test_mutants_of_the_reason_are_caught(monkeypatch):
    orig = grid_c.table

    def constant(scs):
        return [{**r, "why": "固定した測り方の外"} if r["verdict"] != "場面にした" else r for r in orig(scs)]

    def no_declarations(scs):
        return [{**r, "why": WHY_NONE} if r["verdict"] != "場面にした" else r for r in orig(scs)]
    monkeypatch.setattr(grid_c, "table", constant)
    assert why_problems(scenes.SCENES)
    monkeypatch.setattr(grid_c, "table", no_declarations)
    assert why_problems([_fake("a", "P0-1", [("約定", "戦略の呼び出しに届く物", "")], [])])
