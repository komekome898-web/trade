"""Round r15-1 (critic i0-r14-06, repeat_of i0-r11-02; ROOTCAUSE_r15-1.md section 4, families 8, 1' and 9).
Written BEFORE grid_c.unplaced / grid_c.request_recording existed (the delegation's scrutiny (6)).

Family 8: every scene of a viewpoint shows in the cell table (a counted cell, or the out-of-axis line) or in the
viewpoint's list of scenes the table does not place. The rule, from ROOTCAUSE_r15-1.md section 3 item 2 (the oracle
below is written from these words, not from grid_c's code): with the input's events = the items of `events` and of
every stream (a `type_plan` scene: the input built for a target with all six types), the input's types = F's types
(test_battery_r13_covers_of._oracle_types) and the counted cells = F's (test_battery_r13_covers_of._oracle):
  * no counted cell, no event and no type                      -> 事象を持たない
  * no counted cell, events but no type                        -> 事象の型を入力が決めない
  * no counted cell, the input gives a type                    -> 入力から型は出るが、その型の升目を宣言していない
  * counted cells, and an event without a type field           -> 升目に当たるが、型の欄の無い事象を含む
  * counted cells, every event with a type field               -> not listed
An input F refuses (a type outside the six, a request field that is not a list of known kinds) is refused here too.
The cell verdicts are not changed by the list (F and LEAD_DESIGN.md section 8.2 item 1: two values).

The grid (from the input space, not from grid_c's branches): every scene x every copy of
test_battery_r13_covers_of._copies (input mutations x request fields x two declarations) plus, for scenes with
events, the copies below (one event's type field removed / a non-dict item added, x every request field x the scene's
own declaration, the full range, and nothing).

Family 9 (br13-1-2): which adapters record the strategy's requests (`records_requests = True` in the adapter's class)
and how many configured targets each has, by group (ours and the planted mutant / the opponents / the reproductions),
read here from the adapter files' text by a regular expression, not by grid_c's syntax-tree reader.

Not in the grids (and why):
  * whether an empty declaration is right (the scene reads something no cell names) -- the critic's reading
    (LEAD_DESIGN.md section 8.5 item 24);
  * a `type_plan` with more slots than the scene's own builder lays out (the builder raises; not a scene of this set);
  * event items inside a stream that is not a list (scenes.py never builds one; F's reader iterates it as given);
  * whether an adapter that says it records requests really calls `common.request` where its strategy asks -- the
    reference strategy's checks of test_battery_r13_claims.py (new_impl, current_impl).
"""
from __future__ import annotations

import re
import sys
from dataclasses import replace
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "adapters"))

import grid_c  # noqa: E402
import scenes  # noqa: E402
import test_battery_r13_covers_of as CO  # noqa: E402

C1, C2, C3, C4 = ("事象を持たない", "事象の型を入力が決めない", "入力から型は出るが、その型の升目を宣言していない",
                  "升目に当たるが、型の欄の無い事象を含む")
UNPLACED = (C1, C2, C3)


def _events(s) -> list:
    src = scenes.for_target_types(s, CO.ALL_SIX) if s.type_plan is not None else s
    inp = src.input if src is not None and isinstance(src.input, dict) else {}
    evs = list(inp.get("events") or [])
    for stream in (inp.get("streams") or {}).values():
        evs += list(stream)
    return evs


def oracle_class(s):
    """The class of one scene by the rule's words (raises CO.Refused where F refuses)."""
    counted, _ = CO._oracle(s)
    types = CO._oracle_types(s)
    evs = _events(s)
    untyped = [e for e in evs if not (isinstance(e, dict) and "kind" in e)]
    if not counted:
        if not evs and not types:
            return C1
        if not types:
            return C2
        return C3
    return C4 if untyped else None


def oracle_list(scs) -> list[dict]:
    out = []
    for s in scs:
        c = oracle_class(s)
        if c is not None:
            out.append({"viewpoint": s.viewpoint, "scene": s.id, "class": c})
    return out


def _extra_copies(s):
    if s.type_plan is not None:
        return
    inp = {k: v for k, v in s.input.items() if k != "requests"}
    variants = []
    if inp.get("events"):
        first = dict(inp["events"][0])
        first.pop("kind", None)
        variants.append(("first_untyped", {**inp, "events": [first] + [dict(e) for e in inp["events"][1:]]}))
        variants.append(("non_dict_item", {**inp, "events": [dict(e) for e in inp["events"]] + [7]}))
    if inp.get("streams"):
        k0 = next(iter(inp["streams"]))
        st = {k: [dict(e) for e in v] for k, v in inp["streams"].items()}
        st[k0][0].pop("kind", None)
        variants.append(("stream_first_untyped", {**inp, "streams": st}))
    for mname, minp in variants:
        for rname, req in CO.REQUESTS:
            i2 = dict(minp) if req is None else {**minp, "requests": req}
            for dname, decl in (("own", tuple(s.declares)), ("full", CO._full_declaration(s.viewpoint)), ("none", ())):
                yield f"{mname}/{rname}/{dname}", replace(s, input=i2, declares=decl)


def copies(s):
    yield from CO._copies(s)
    yield from _extra_copies(s)


def mismatches(scs=None) -> int:
    """Cases of the grid where grid_c.unplaced differs from the oracle (a refusal must be a ValueError)."""
    bad = 0
    for s in scs or scenes.SCENES:
        for _, c in copies(s):
            try:
                want = oracle_list([c])
            except CO.Refused:
                try:
                    grid_c.unplaced([c])
                    bad += 1
                except ValueError:
                    pass
                continue
            try:
                if grid_c.unplaced([c]) != want:
                    bad += 1
            except ValueError:
                bad += 1
    return bad


# ---------------------------------------------------------------- family 8 (c)
@pytest.mark.parametrize("s", scenes.SCENES, ids=[s.id for s in scenes.SCENES])
def test_unplaced_follows_the_rule_on_every_copy(s):
    n = 0
    classes = set()
    for name, c in copies(s):
        try:
            want = oracle_list([c])
        except CO.Refused:
            with pytest.raises(ValueError):
                grid_c.unplaced([c])
            n += 1
            continue
        assert grid_c.unplaced([c]) == want, (s.id, name)
        classes |= {w["class"] for w in want}
        n += 1
    assert n == len(list(copies(s)))


def test_the_grid_reaches_every_class():
    """The grid is not narrower than the rule: each class and the not-listed case occur in it."""
    seen = set()
    for s in scenes.SCENES:
        for _, c in copies(s):
            try:
                seen.add(oracle_class(c))
            except CO.Refused:
                seen.add("refused")
    assert seen == {C1, C2, C3, C4, None, "refused"}, seen


def test_the_list_of_the_scene_set_is_the_oracles():
    assert grid_c.unplaced(scenes.SCENES) == oracle_list(scenes.SCENES)


def test_every_scene_is_in_the_table_or_in_the_list():
    rows = grid_c.table(scenes.SCENES)
    in_table = {i for r in rows for i in r["scenes"]}
    in_table |= {s.id for s in scenes.SCENES if any(c[0] in scenes.OUTSIDE_AXES for c in s.covers)}
    listed = {x["scene"]: x["class"] for x in grid_c.unplaced(scenes.SCENES)}
    for s in scenes.SCENES:
        placed = s.id in in_table
        cls = listed.get(s.id)
        assert placed != (cls in UNPLACED), (s.id, placed, cls)       # exactly one of the two
        assert cls != C4 or placed, s.id


# ---------------------------------------------------------------- family 8 and 1' (c): what DEFINITIONS.md shows
KIND_JP = {"value": "値の場面", "capability": "能力の場面"}


def expected_section_lines(vp: str) -> list[str]:
    """The heading and the list lines of one viewpoint, from the oracle (the cells' count from F's oracle)."""
    mine = [s for s in scenes.SCENES if s.viewpoint == vp]
    cells = grid_c.cells(vp)
    counted = {c for s in mine for c in CO._oracle(s)[0]}
    n_done = sum(1 for c in cells if c in counted)
    lst = oracle_list(mine)
    n_un = sum(1 for x in lst if x["class"] in UNPLACED)
    head = (f"### {vp}(升目 {len(cells)}: {grid_c.VERDICTS[0]} {n_done} / {grid_c.VERDICTS[1]} {len(cells) - n_done}"
            f" / 升目に当たらない場面 {n_un})")
    by = {s.id: s for s in mine}
    items = [f"- `{x['scene']}`({KIND_JP[by[x['scene']].kind]}): {x['class']}" for x in lst]
    return [head] + (items or ["- 無し"])


def definitions_problems(text: str) -> list:
    out = []
    lines = text.split("\n")
    for vp in grid_c.VIEWPOINTS:
        want = expected_section_lines(vp)
        heads = [i for i, ln in enumerate(lines) if ln.startswith(f"### {vp}(升目 ")]
        if len(heads) != 1 or lines[heads[0]] != want[0]:
            out.append(("見出し", vp, [lines[i] for i in heads], want[0]))
            continue
        i = heads[0] + 1
        body = []
        # round r16-1: the list ends where the next list of the section (the values the viewpoint's text names,
        # test_battery_r16_units.py) or the table begins
        while i < len(lines) and not lines[i].startswith("| 事象 |") and not lines[i].startswith("観点の文が名指す値ごとの場面"):
            body.append(lines[i])
            i += 1
        got = [ln for ln in body if ln.startswith("- ")]
        if got != want[1:]:
            out.append(("一覧", vp, got, want[1:]))
    return out


def test_the_definitions_show_the_list_the_rule_gives():
    text = (HERE / "DEFINITIONS.md").read_text(encoding="utf-8")
    assert definitions_problems(text) == []


# ---------------------------------------------------------------- family 8 (d): mutants

def _mutants():
    import grid_c as G
    orig = G.unplaced
    orig_events = scenes.input_events

    def untyped_as_typed(scs):
        out = []
        for s in scs:
            inp = s.input if isinstance(s.input, dict) else {}
            if inp.get("events") and s.type_plan is None:
                s = replace(s, input={**inp, "events": [dict(e, kind=e.get("kind", "trade")) if isinstance(e, dict)
                                                        else e for e in inp["events"]]})
            out += orig([s])
        return out

    def drop_no_event(scs):
        return [x for x in orig(scs) if x["class"] != C1]

    def list_placed_too(scs):
        got = orig(scs)
        have = {x["scene"] for x in got}
        return got + [{"viewpoint": s.viewpoint, "scene": s.id, "class": C3} for s in scs
                      if s.id not in have and scenes.covers_of(s)]

    def swap_c1_c2(scs):
        sw = {C1: C2, C2: C1}
        return [{**x, "class": sw.get(x["class"], x["class"])} for x in orig(scs)]

    def drop_c4(scs):
        return [x for x in orig(scs) if x["class"] != C4]

    def events_no_streams(scene):
        built = scenes.for_target_types(scene, scenes.TYPE_ORDER) if scene.type_plan is not None else scene
        inp = built.input if built is not None and isinstance(built.input, dict) else {}
        return list(inp.get("events") or [])

    def events_no_type_plan(scene):
        return orig_events(replace(scene, type_plan=None))

    return ({"型の欄の無い事象を型の有る事象と数える": ("unplaced", untyped_as_typed),
             "事象を持たない場面を落とす": ("unplaced", drop_no_event),
             "升目に当たる場面も列べる": ("unplaced", list_placed_too),
             "区分を取り違える": ("unplaced", swap_c1_c2),
             "型の欄の無い事象を含む場面を落とす": ("unplaced", drop_c4)},
            {"streams を読まない": events_no_streams, "type_plan を読まない": events_no_type_plan})


def test_the_machine_itself_agrees_with_the_oracle():
    assert mismatches() == 0


@pytest.mark.parametrize("name", sorted(_mutants()[0]))
def test_mutants_of_unplaced_are_caught(monkeypatch, name):
    _, fn = _mutants()[0][name]
    monkeypatch.setattr(grid_c, "unplaced", fn)
    assert mismatches() > 0, name


@pytest.mark.parametrize("name", sorted(_mutants()[1]))
def test_mutants_of_input_events_are_caught(monkeypatch, name):
    monkeypatch.setattr(scenes, "input_events", _mutants()[1][name])
    assert mismatches() > 0, name


def test_a_mutant_section_without_the_list_is_caught(monkeypatch):
    import gen_definitions
    assert definitions_problems(gen_definitions.render()) == []
    monkeypatch.setattr(grid_c, "unplaced", lambda scs: [])
    assert definitions_problems(gen_definitions.render())


# ---------------------------------------------------------------- family 9 (br13-1-2): who records requests
def oracle_recording() -> dict:
    import run_battery as R
    groups = {"新実装・当方の現状・試金石": ["new_impl", "current_impl", "mutant"], "相手": list(R.OPPONENTS),
              "再現": list(R._repro_targets())}
    out = {}
    for g, bases in groups.items():
        rec, non = [], []
        for b in bases:
            text = R._module_path(b).read_text(encoding="utf-8")
            n = len(R.configured_targets(b))
            (rec if re.search(r"^[ \t]+records_requests[ \t]*=[ \t]*True\b", text, re.M) else non).append((b, n))
        out[g] = {"records": rec, "not": non}
    return out


def recording_sentence(counts: dict) -> str:
    parts = []
    for g, v in counts.items():
        parts.append(f"{g}: 記録する {len(v['records'])}(設定つき対象 {sum(n for _, n in v['records'])})/ "
                     f"記録しない {len(v['not'])}(設定つき対象 {sum(n for _, n in v['not'])})")
    return "。".join(parts)


def test_request_recording_counts_are_the_adapters():
    assert grid_c.request_recording() == oracle_recording()
    text = (HERE / "DEFINITIONS.md").read_text(encoding="utf-8")
    assert recording_sentence(oracle_recording()) in text


def test_mutants_of_request_recording_are_caught(monkeypatch):
    orig = grid_c.request_recording
    want = oracle_recording()
    assert orig() == want

    def all_record():
        return {g: {"records": v["records"] + v["not"], "not": []} for g, v in orig().items()}

    def adapters_not_targets():
        return {g: {k: [(b, 1) for b, _ in v[k]] for k in v} for g, v in orig().items()}

    def no_repro():
        return {g: v for g, v in orig().items() if g != "再現"}
    for name, m in {"全部を記録すると数える": all_record, "設定つき対象でなく adapter を数える": adapters_not_targets,
                    "再現の対象を落とす": no_repro}.items():
        monkeypatch.setattr(grid_c, "request_recording", m)
        assert grid_c.request_recording() != want, name
