"""Round r17-1 (critic i0-r16-04 [stop]; ROOTCAUSE_r17-1.md section 4, families 15-18).
Written BEFORE the machines existed (the delegation's scrutiny (6)); every oracle below is written from the rule's
sentences in ROOTCAUSE_r17-1.md section 3, not from the code it checks.

Family 15 -- a refusal is credited to the target's entry (`run_battery.refusal_problem` is None) exactly when ALL hold:
  * the result's status is not_supported;
  * `provenance["refusal"]` is a record common.py made from the exception object (`common.refusal`), not a dict or a
    `Record` written by hand;
  * the entry that refused (`provenance["reader"]`) is the target's (a function / class whose file is in the target's
    distribution, or a compiled name under the target's heads);
  * what was handed to the entry is the scene input's field the record names, of the same type and the same value;
  * a Python entry: (i) a frame of the target's distribution is on the exception's traceback, (ii) no frame of a real
    file of the scene set lies inside the outermost target frame (the target did not call back into the scene set's
    code that then failed), (iii) the innermost frame is a real file (a pseudo-named frame -- exec'd code -- cannot
    be placed), and the exception is not a `CompiledRefusal`;
  * a compiled entry: the exception is a `common.CompiledRefusal` (the driver's printed refusal of the tool; the
    driver's code is read by the critic).
  `common.unit_time` makes the record only when an entry of the scene's unit and form was called and raised; the record
  holds the input's object itself.
Family 16 -- the scenes whose answer is a refusal are exactly the unit scenes whose input value (a text: its decimal;
  an int: itself; a float: the binary value it holds) times the unit's factor is not a whole number of ns.
Family 17 -- the grade: error -> 結果なし; not_supported -> 正解と一致 when the scene's answer is a refusal and the refusal
  is credited, else 対応なし; ok -> for a scene whose answer is a refusal 不一致 (the target made a time), otherwise
  正解と一致 when the graded value matches, else 不一致. Every scene has a behavior graded as its answer.
Family 18 -- the texts that state the refusal grade say what the machine gives: each refusal scene's section of
  DEFINITIONS.md carries the fixed phrase of scenes.REFUSAL_PHRASE; the old sentences that graded a refusal of a
  NO_INT scene as 対応なし are in no file the scene keeper writes (the ROOTCAUSE files of earlier rounds keep their
  history).

Not in the grids (and why):
  * whether a compiled driver's printed error is the tool's own refusal: Python sees no frame of the tool (critic);
  * why the entry refused (sub-ns digits or any decimal): reading the exception's text is reading prose, which the
    finding forbids ("文の読みでなく機械の欄で"); the paired scenes with an int answer show whether the entry reads
    the unit at all (ROOTCAUSE_r17-1.md section 5.2 item 3);
  * a target frame reached only through a C extension without a Python frame (numba, Rust bindings): no Python frame
    of the target is on the traceback, so the refusal is not credited (the grid's chain without a target frame);
  * which entry of a tool reads which unit and form: the tool's code or documents, read by the critic.
"""
from __future__ import annotations

import importlib.util
import sys
from dataclasses import replace
from fractions import Fraction
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "adapters"))
sys.path.insert(0, str(HERE.parents[3] / "src"))

import scenes  # noqa: E402

FACTOR = {"s": 10 ** 9, "ms": 10 ** 6, "us": 10 ** 3}
SC = {s.id: s for s in scenes.SCENES}


def _held(v) -> Fraction:
    if type(v) is float:
        n, d = v.as_integer_ratio()
        return Fraction(n, d)
    return Fraction(v)


def oracle_answer_is_refusal(s) -> bool:
    if not (isinstance(s.input, dict) and "unit" in s.input and "time" in s.input):
        return False
    return (_held(s.input["time"]) * FACTOR[s.input["unit"]]).denominator != 1


# ---------------------------------------------------------------- the target / third-party / scene-set code of the grid
TARGET_SRC = '''
import third


def refuse(v, cls):
    raise cls("target refuses " + repr(v))


def c_level(v, cls):
    return int("x" + str(v))


def via_third(v, cls):
    return third.boom(v, cls)


def call_back(v, cb):
    return cb(v)


def fine(v):
    return 7
'''
THIRD_SRC = '''
def boom(v, cls):
    raise cls("third party refuses")
'''


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    import common as C
    import run_battery as R
    base = tmp_path_factory.mktemp("r17_refusal_world")
    (base / "tgt").mkdir()
    (base / "lib").mkdir()
    (base / "tgt" / "r17_target_entry.py").write_text(TARGET_SRC, encoding="utf-8")
    (base / "lib" / "third.py").write_text(THIRD_SRC, encoding="utf-8")
    sys.path.insert(0, str(base / "lib"))
    spec = importlib.util.spec_from_file_location("r17_target_entry", base / "tgt" / "r17_target_entry.py")
    tgt = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tgt)
    import third
    roots = R.Roots([str((base / "tgt").resolve())], ["rust:tool::"], [])
    R._ROOTS["t_r17_grid"] = roots  # the grid's target: its places (roots_of reads this cache first)
    return {"tgt": tgt, "third": third, "roots": roots, "C": C, "R": R}


def _ss_raise(v, cls):  # the scene set's own raise statement
    raise cls("scene set")


def _ss_c(v):  # the scene set's code failing in C
    return int("x" + str(v))


def _pseudo(src: str, **glb):
    ns = dict(glb)
    exec(src, ns)  # noqa: S102 - a pseudo-named frame ('<string>')
    return ns["p"]


# chain -> (how the exception comes about, credited on the Python path by the rule (i)-(iii))
def chains(w):
    tgt, third = w["tgt"], w["third"]

    def k(fn):
        return fn
    return {
        "K1 target raises": (lambda v, cls: tgt.refuse(v, cls), True),
        "K2 target fails in C": (lambda v, cls: tgt.c_level(v, cls), True),
        "K3 target -> third party raises": (lambda v, cls: tgt.via_third(v, cls), True),
        "K4 target -> scene-set raise": (lambda v, cls: tgt.call_back(v, lambda x: _ss_raise(x, cls)), False),
        "K5 target -> scene-set C failure": (lambda v, cls: tgt.call_back(v, _ss_c), False),
        "K6 target -> scene set -> third party": (lambda v, cls: tgt.call_back(v, lambda x: third.boom(x, cls)), False),
        "K7 scene-set raise only": (lambda v, cls: _ss_raise(v, cls), False),
        "K8 third party called by the scene set": (lambda v, cls: third.boom(v, cls), False),
        "K9 target returned, then the scene set raised": (lambda v, cls: (tgt.fine(v), _ss_raise(v, cls)), False),
        "K10 target -> exec'd code -> target raises": (
            lambda v, cls: tgt.call_back(v, _pseudo("def p(x):\n    return refuse(x, cls)\n", refuse=tgt.refuse, cls=cls)),
            True),
        "K11 target -> exec'd code raises": (
            lambda v, cls: tgt.call_back(v, _pseudo("def p(x):\n    raise cls('exec')\n", cls=cls)), False),
        "K12 wrong call, no target frame": (lambda v, cls: tgt.refuse(v), False),
    }


def _raise(run, v, cls):
    try:
        run(v, cls)
    except Exception as exc:  # noqa: BLE001
        return exc
    raise AssertionError("the chain did not raise")


INPUT = 1704067200  # an int input: the type axis needs a value equal across types (1704067200 == 1704067200.0)


def handed_values():
    return {"same object": (lambda: INPUT, "time", True),
            "equal int": (lambda: int("1704067200"), "time", True),
            "equal float": (lambda: float(INPUT), "time", False),
            "other int": (lambda: INPUT + 1, "time", False),
            "field not in the input": (lambda: INPUT, "stamp", False)}


def readers(w):
    C = w["C"]
    return {"target function": (C.qualname(w["tgt"].refuse), "py"),
            "scene-set function": (C.qualname(_ss_raise), None),
            "hand-written name": ("r17_target_entry.refuse", None),
            "compiled, target's head": (C.compiled("rust:tool::de_refuse"), "compiled"),
            "compiled, other head": (C.compiled("rust:other::de_refuse"), None),
            "no reader": (None, None)}


def records(C, exc, field, handed):
    made = C.refusal(exc, field, handed)
    return {"made by common": (made, True), "Record by hand": (C.Record(dict(made)), False),
            "plain dict": (dict(made), False), "None": (None, False), "text": ("refused", False), "absent": ("ABSENT", False)}


def grid_scene():
    return replace(SC["p2-s-text-subns"], input={"time": INPUT, "unit": "s", "note": ""})


def refusal_cases(w):
    """Every cell of: chain x exception class x handed x reader x record origin x status; with the oracle."""
    C = w["C"]
    sc = grid_scene()
    out = []
    for cname, (run, py_ok) in chains(w).items():
        for cls in (ValueError, C.CompiledRefusal):
            for hname, (mk, field, h_ok) in handed_values().items():
                handed = mk()
                exc = _raise(run, handed, cls)
                compiled_exc = isinstance(exc, C.CompiledRefusal)
                for rname, (rec, r_ok) in records(C, exc, field, handed).items():
                    for dname, (reader, path) in readers(w).items():
                        for status in ("not_supported", "ok", "error"):
                            prov = {"reader": reader}
                            if rec != "ABSENT":
                                prov["refusal"] = rec
                            from protocol import SceneResult
                            res = SceneResult(status, output=None, detail="", provenance=prov)
                            if path == "py":
                                chain_ok = py_ok and not compiled_exc
                            elif path == "compiled":
                                chain_ok = compiled_exc
                            else:
                                chain_ok = False
                            want = status == "not_supported" and r_ok and h_ok and chain_ok
                            out.append(((cname, cls.__name__, hname, rname, dname, status), sc, res, want))
    return out


def refusal_problems(w, fn) -> list:
    bad = []
    for key, sc, res, want in refusal_cases(w):
        got = fn(res, sc, "t_r17_grid", w["roots"]) is None
        if got != want:
            bad.append(key + (want, got))
    return bad


def test_refusal_rule_on_every_cell_of_the_grid(world):
    R = world["R"]
    cases = refusal_cases(world)
    assert len(cases) == 12 * 2 * 5 * 6 * 6 * 3
    assert sum(1 for *_, want in cases if want) > 0
    assert refusal_problems(world, R.refusal_problem) == []


def test_mutants_of_the_refusal_rule_are_caught(world, monkeypatch):
    R, C = world["R"], world["C"]
    orig_made, orig_reader = R._made, R._reader_problem
    mutants = {
        "記録の出所を見ない": ("_made", lambda x: isinstance(x, dict) or orig_made(x)),
        "入口の出所を見ない": ("_reader_problem", lambda reader, roots: None),
        "道筋に対象の枠を求めない / 内側の場面集の枠を見ない / 最も内の枠を見ない": ("_refusal_chain_problem", lambda rec, roots: None),
        "渡した物を見ない": ("_handed_problem", lambda rec, scene: None),
    }
    for name, (attr, fn) in mutants.items():
        with monkeypatch.context() as m:
            m.setattr(R, attr, fn)
            assert refusal_problems(world, R.refusal_problem), name
    assert R._made is orig_made and R._reader_problem is orig_reader

    def chain_target_frame_only(rec, roots):  # (i) only: a target frame somewhere
        fr = rec.get("frames") or []
        return None if any(roots.has_file(f) for f in fr) else "no target frame"

    def chain_no_innermost(rec, roots):  # (i) and (ii), not (iii)
        fr = rec.get("frames") or []
        first = next((i for i, f in enumerate(fr) if roots.has_file(f)), None)
        if first is None:
            return "no target frame"
        if any(C.in_scene_set(f) and f.startswith("/") for f in fr[first + 1:]):
            return "scene set inside"
        return None
    for name, fn in {"内側の場面集の枠を見ない": chain_target_frame_only, "最も内の枠を見ない": chain_no_innermost}.items():
        with monkeypatch.context() as m:
            m.setattr(R, "_refusal_chain_problem", fn)
            assert refusal_problems(world, R.refusal_problem), name

    def ignore_compiled_mark(res, scene, target=None, roots=None):
        why = orig(res, scene, target, roots)
        if why and "CompiledRefusal" in why:
            return None
        return why
    orig = R.refusal_problem
    assert refusal_problems(world, ignore_compiled_mark), "翻訳した道具の印を見ない"


# ---------------------------------------------------------------- common.unit_time makes the record
class _Rec:
    def __init__(self, result):
        self.result, self.args = result, []

    def __call__(self, v):
        self.args.append(v)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def _entry_reader(v):
    return v


ENTRY_SETS = {"none": [], "s str": [("s", ("str",))], "s int+float": [("s", ("int", "float"))],
              "ms all": [("ms", ("str", "int", "float"))], "every unit": [(u, ("str", "int", "float")) for u in FACTOR]}
INPUTS = [("s", "1.5"), ("s", 2), ("s", 2.5), ("ms", "3"), ("ms", 4), ("us", 5.25)]
OUTCOMES = [7, None, ValueError("refused"), KeyError("k")]


def unit_time_refusal_problems(unit_time) -> list:
    import common as C
    base = SC["p2-s-text-subns"]
    out = []
    for ename, spec in ENTRY_SETS.items():
        for u, v in INPUTS:
            for r in OUTCOMES:
                recs = [_Rec(r) for _ in spec]
                entries = [{"unit": eu, "forms": ef, "how": f"entry {i}", "reader": _entry_reader, "call": rec}
                           for i, ((eu, ef), rec) in enumerate(zip(spec, recs))]
                sc = replace(base, input={"time": v, "unit": u, "note": ""})
                res = unit_time(sc, entries, tried="")
                form = {str: "str", int: "int", float: "float"}[type(v)]
                called = any(eu == u and form in ef for eu, ef in spec)
                prov = res.provenance if isinstance(res.provenance, dict) else {}
                rec = prov.get("refusal")
                key = (ename, u, repr(v), repr(r))
                if called and isinstance(r, Exception):
                    if res.status != "not_supported" or rec is None or not C.made_here(rec) \
                            or rec.get("handed") is not v or rec.get("field") != "time" \
                            or rec.get("raised") != type(r).__name__:
                        out.append(key + ("want a refusal record of the handed object", res.status, rec))
                elif rec is not None:
                    out.append(key + ("want no refusal record", res.status, rec))
    return out


def test_unit_time_records_a_refusal_only_when_an_entry_raised():
    import common as C
    assert unit_time_refusal_problems(C.unit_time) == []


def test_mutants_of_unit_time_refusal_are_caught():
    import common as C
    from protocol import SceneResult
    orig = C.unit_time

    def record_always(sc, entries, tried=""):
        res = orig(sc, entries, tried)
        if res.status == "not_supported" and not (isinstance(res.provenance, dict) and res.provenance.get("refusal")):
            return SceneResult(res.status, res.output, res.detail,
                               {"reader": None, "refusal": C.refusal(ValueError("x"), "time", sc.input["time"])})
        return res

    def no_record(sc, entries, tried=""):
        res = orig(sc, entries, tried)
        return SceneResult(res.status, res.output, res.detail, None) if res.status == "not_supported" else res

    def other_handed(sc, entries, tried=""):
        res = orig(sc, entries, tried)
        if isinstance(res.provenance, dict) and res.provenance.get("refusal") is not None:
            v = sc.input["time"]
            copy = type(v)(str(v)) if not isinstance(v, str) else "".join(list(v))
            return SceneResult(res.status, res.output, res.detail,
                               {**res.provenance, "refusal": C.refusal(ValueError("x"), "time", copy)})
        return res
    for name, m in {"入口が無くても記録を作る": record_always, "断りに記録を付けない": no_record,
                    "別の物を渡した物として記録する": other_handed}.items():
        assert unit_time_refusal_problems(m), name


# ---------------------------------------------------------------- family 16: which scenes answer "refuse"
def answer_set_problems(scs, is_refusal=oracle_answer_is_refusal) -> list:
    import run_battery as R
    out = []
    for s in scs:
        if R.expects_refusal(s.expected) != is_refusal(s):
            out.append((s.id, s.expected))
        if is_refusal(s) and not (isinstance(s.expected, dict) and s.expected.get("int64_ns") == scenes.NO_INT):
            out.append((s.id, "a refusal scene keeps int64_ns = NO_INT (no int is right)"))
    return out


def test_refusal_is_the_answer_exactly_where_no_int_is():
    assert answer_set_problems(scenes.SCENES) == []
    assert sum(1 for s in scenes.SCENES if oracle_answer_is_refusal(s)) == 5
    assert scenes.REFUSED == "refused_by_entry"


def test_mutants_of_the_refusal_answer_set_are_caught():
    def shortest(s):
        if not (isinstance(s.input, dict) and "unit" in s.input):
            return False
        v = s.input["time"]
        return (Fraction(repr(v) if type(v) is float else v) * FACTOR[s.input["unit"]]).denominator != 1

    def every_unit_scene(s):
        return isinstance(s.input, dict) and "unit" in s.input
    assert answer_set_problems(scenes.SCENES, shortest), "float を最短の表記で読む"
    assert answer_set_problems(scenes.SCENES, every_unit_scene), "整数の場面にも断りを求める"
    unmarked = [replace(s, expected={k: v for k, v in s.expected.items() if k != scenes.REFUSED})
                if isinstance(s.expected, dict) else s for s in scenes.SCENES]
    assert answer_set_problems(unmarked), "断りの印を外す"


# ---------------------------------------------------------------- family 17: the grade
def _credited(w, sc, field):
    C = w["C"]
    handed = sc.input[field]
    exc = _raise(lambda v, cls: w["tgt"].refuse(v, cls), handed, ValueError)
    return {"reader": C.qualname(w["tgt"].refuse), "refusal": C.refusal(exc, field, handed)}


def _uncredited(w, sc, field):
    C = w["C"]
    handed = sc.input[field]
    exc = _raise(lambda v, cls: _ss_raise(v, cls), handed, ValueError)
    return {"reader": C.qualname(w["tgt"].refuse), "refusal": C.refusal(exc, field, handed)}


GRADE_SCENES = ["p2-s-text-subns", "p2-ms-float-subns", "p2-s-int", "p2-us-float-held", "p2-iso-utc", "p5-same-stream-order"]


def grade_cases(w):
    from protocol import SceneResult
    out = []
    for sid in GRADE_SCENES:
        sc = SC[sid]
        field = "time" if "time" in sc.input else next(iter(sc.input))
        refusal_answer = oracle_answer_is_refusal(sc)
        unit = "unit" in sc.input
        if unit:
            right = None if refusal_answer else sc.expected["int64_ns"]
            oks = {"right int": ({"ns": right}, not refusal_answer),
                   "other int": ({"ns": 7}, False), "float": ({"ns": float(right or 7)}, False), "empty": ({}, False)}
        else:
            oks = {"right": (sc.expected, True), "wrong": ({"other": 1} if isinstance(sc.expected, dict) else 7, False)}
        for oname, (o, right_ok) in oks.items():
            out.append(((sid, "ok", oname), sc, SceneResult("ok", output=o), "正解と一致" if right_ok else "不一致"))
        out.append(((sid, "error"), sc, SceneResult("error"), "結果なし"))
        out.append(((sid, "not_supported", "no record"), sc, SceneResult("not_supported"), "対応なし"))
        out.append(((sid, "not_supported", "credited"), sc,
                    SceneResult("not_supported", provenance=_credited(w, sc, field)),
                    "正解と一致" if refusal_answer else "対応なし"))
        out.append(((sid, "not_supported", "not credited"), sc,
                    SceneResult("not_supported", provenance=_uncredited(w, sc, field)), "対応なし"))
    return out


def grade_problems(w, correctness) -> list:
    return [key + (want, got) for key, sc, res, want in grade_cases(w)
            if (got := correctness(res, sc.expected, sc, "t_r17_grid")) != want]


def test_grades_on_every_cell_of_the_grid(world):
    R = world["R"]
    assert grade_problems(world, R.correctness) == []
    for key, sc, res, want in grade_cases(world):  # the output column shows the machine's reading of a refusal
        if res.status == "not_supported" and isinstance(res.provenance, dict) and "refusal" in res.provenance:
            g = R.graded_output(res, sc, "t_r17_grid")
            assert g[scenes.REFUSED] is (key[-1] == "credited"), key


def test_mutants_of_the_grade_are_caught(world, monkeypatch):
    R = world["R"]
    orig = R.correctness
    for name, attr, fn in [("期待を見ない", "expects_refusal", lambda e: True),
                           ("帰属を見ない", "refusal_problem", lambda *a, **k: None)]:
        with monkeypatch.context() as m:
            m.setattr(R, attr, fn)
            assert grade_problems(world, R.correctness), name

    def refusal_mismatch(res, expected, scene=None, target=None):
        g = orig(res, expected, scene, target)
        return "不一致" if g == "正解と一致" and res.status == "not_supported" else g

    def ok_by_mark(res, expected, scene=None, target=None):
        g = orig(res, expected, scene, target)
        return "正解と一致" if res.status == "ok" and R.expects_refusal(expected) else g

    def any_record(res, expected, scene=None, target=None):
        if res.status == "not_supported" and isinstance(res.provenance, dict) and res.provenance.get("refusal"):
            return "正解と一致"
        return orig(res, expected, scene, target)
    for name, m in {"断りを不一致にする": refusal_mismatch, "ok でも断りの印で一致にする": ok_by_mark,
                    "断りの記録があれば全部一致にする": any_record}.items():
        assert grade_problems(world, m), name


def test_every_scene_has_a_behavior_graded_as_its_answer(world):
    """Rule 1: for every scene some behavior is graded 正解と一致 -- a refusal credited to the target's entry for a
    refusal scene; the expected output itself for a scene graded on its raw output; the time as an int for a unit
    scene; and, for the four scenes whose graded values the runner computes from observations (not writable from the
    expected alone), the new implementation's run through the runner's full path."""
    R = world["R"]
    from protocol import SceneResult
    unreached = []
    witnessed = {}
    new = None
    for s in scenes.SCENES:
        if R.expects_refusal(s.expected):
            res, target = SceneResult("not_supported", provenance=_credited(world, s, "time")), "t_r17_grid"
        elif s.id in scenes.UNIT_SCENES:
            res, target = SceneResult("ok", output={"ns": s.expected["int64_ns"]}), None
        elif not s.graded_from:
            res, target = SceneResult("ok", output=s.expected), None
        else:
            if new is None:
                new, p3 = R.load_adapter("new_impl"), {}
                for tid in R.TYPE_SCENES:  # the runner's own order: the type scenes decide the types of type_plan scenes
                    t_run, t_raw, t_set, *_ = R.run_for_types_records(new, SC[tid], p3)
                    p3[tid] = R.correctness(R.checked(t_raw, t_run, "new_impl", settings=t_set), t_run.expected, t_run,
                                            "new_impl")
            sc_run, raw, settings, *_ = R.run_for_types_records(new, s, p3)
            res, target = R.checked(raw, sc_run, "new_impl", settings=settings), "new_impl"
            s = sc_run
        witnessed[s.id] = R.correctness(res, s.expected, s, target)
        if witnessed[s.id] != "正解と一致":
            unreached.append((s.id, witnessed[s.id], res.status))
    assert len(witnessed) == len(scenes.SCENES)
    assert unreached == []


# ---------------------------------------------------------------- family 18: the texts
OLD_SENTENCES = ["対象が断れば「対応なし」", "入口が断れば「対応なし」(出た例外を書く)"]


def text_problems(definitions: str, files: dict) -> list:
    out = []
    for s in scenes.SCENES:
        if not oracle_answer_is_refusal(s):
            continue
        block = definitions[definitions.index(f"### `{s.id}`"):]
        block = block[:block.index("\n### ", 1)] if "\n### " in block[1:] else block
        if scenes.REFUSAL_PHRASE not in block:
            out.append((s.id, "no refusal phrase"))
    grade_line = [ln for ln in definitions.split("\n") if ln.startswith("- **正しさ**")]
    if len(grade_line) != 1 or "断りの記録" not in grade_line[0]:
        out.append(("正しさ", "the grade line does not name the refusal record"))
    for f, text in files.items():
        for old in OLD_SENTENCES:
            if old in text:
                out.append((f, old))
    return out


def _files() -> dict:
    import line_marks
    out = {}
    for f in line_marks.files():
        if f.startswith("ROOTCAUSE") or f == Path(__file__).name:
            continue  # the rounds' records keep their history (this round's quotes the old sentences); this file names them
        try:
            out[f] = (HERE / f).read_text(encoding="utf-8")
        except (UnicodeDecodeError, FileNotFoundError):
            continue
    return out


def test_texts_state_the_grade_the_machine_gives():
    import gen_definitions
    text = (HERE / "DEFINITIONS.md").read_text(encoding="utf-8")
    assert text == gen_definitions.render()
    assert scenes.REFUSAL_PHRASE and "正解と一致" in scenes.REFUSAL_PHRASE
    assert text_problems(text, _files()) == []


def test_a_stale_refusal_text_is_caught():
    import gen_definitions
    text = gen_definitions.render()
    assert text_problems(text.replace(scenes.REFUSAL_PHRASE, "対象が断れば「対応なし」"), {}), "古い文を戻す"
    assert text_problems(text, {"scenes.py": "x" + OLD_SENTENCES[1]}), "古い文がファイルに残る"
