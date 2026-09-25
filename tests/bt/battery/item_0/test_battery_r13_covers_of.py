"""Round r13-1 (critic i0-r11-02, the scene keeper's positive definition of ROOTCAUSE_r13-1.md section 3, passed by
the definitions auditor): a cell (e, v, x) is "場面にした" for a scene s only when s declares the cell AND the type e
comes out of s's input by machine. Written BEFORE scenes.covers_of was changed (the delegation's scrutiny (6)).

The oracle below is written from the definition's sentences alone, not from scenes.py's code:
  * market event types (約定・板の写真・板の差分・足・資金調達・清算) = the type field of each event scenes.py puts in the
    input (`events` and the contents of `streams`), one type field one type; for a `type_plan` scene the input of
    `for_target_types(s, TYPE_ORDER)` (a target with all six types); an event without a type field and a scene without
    events give no type;
  * 時計 / 注文の受付・拒否・約定の通知 / 取消の通知 come only from the strategy's requests the input holds as a field
    (`requests`): the clock request gives 時計, the order request gives the three order notices together, the cancel
    request gives 取消の通知; the input's text (`strategy` etc.) is not read;
  * a declared cell whose e does not come out of the input is not counted, and such a declaration makes a test fail
    (never dropped silently): `covers_problems` names it and test_every_scene_declares_only_cells_its_input_gives fails.

The grid (built from the input space, not from scenes.py's branches): every scene of the set x every input mutation
(as is / type fields removed / no events at all / empty events / every event set to each of the six market types /
an event with a type outside the six / a strategy text naming orders, cancels and a clock without the field) x every
request field (absent / empty / each single kind / order+cancel / all three / an unknown kind / not a list) x two
declarations (the full range of the scene's viewpoint plus the out-of-axis cancel cell, and nothing); for a
`type_plan` scene the mutations are of the plan (slots 1 to the scene's own slots x cycled or not x the fewest
types 1, 2, 6, 7).

Not in the grid (left to the critic's reading, LEAD_DESIGN.md section 8.5 item 24, and why):
  * whether a declared (v, x) fits what the scene measures, and whether the input really calls that path -- meaning,
    not machine;
  * which of the three order notices a scene counts: the order request gives all three, so the machine decides only
    that a scene without the order request counts none of them; swapping a declared notice for another of the three
    on a copy is NOT refused (test_swapping_one_order_notice_for_another_is_left_to_the_declaration shows it);
  * a `type_plan` with more slots than the scene's own builder lays out (the builder has no slot for it, so it is
    not a scene of this set; the builder raises);
  * the records of the runner (`types_in`, `requests`) -- never used for the table (test_battery_item0.py checks them);
  * values of an adapter, the target's output, "the expected result names the event" -- not used by the definition.
"""
from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import grid_c  # noqa: E402
import scenes  # noqa: E402

# written here from the definition's words (REQUIREMENTS.md section 1's order of the market types)
MARKET = {"trade": "約定", "book_snapshot": "板の写真", "book_delta": "板の差分", "bar": "足",
          "funding": "資金調達", "liquidation": "清算"}
CANCEL = "取消の通知(要件 §1 の事象の型の外)"
FROM_REQUEST = {"timer": {"時計"}, "place": {"注文の受付の通知", "注文の拒否の通知", "注文の約定の通知"},
                "cancel": {CANCEL}}
ALL_SIX = list(MARKET)


class Refused(Exception):
    pass


def _oracle_types(s) -> set:
    src = scenes.for_target_types(s, ALL_SIX) if s.type_plan is not None else s
    inp = src.input if src is not None and isinstance(src.input, dict) else {}
    evs = list(inp.get("events") or [])
    for stream in (inp.get("streams") or {}).values():
        evs += list(stream)
    out = set()
    for e in evs:
        if isinstance(e, dict) and "kind" in e:
            if e["kind"] not in MARKET:
                raise Refused(e["kind"])
            out.add(MARKET[e["kind"]])
    own = s.input if isinstance(s.input, dict) else {}
    if "requests" in own:
        req = own["requests"]
        if not isinstance(req, list) or any(r not in FROM_REQUEST for r in req):
            raise Refused(req)
        for r in req:
            out |= FROM_REQUEST[r]
    return out


def _oracle(s):
    """(counted cells in declaration order, declared cells not counted)."""
    types = _oracle_types(s)
    return (tuple(c for c in s.declares if c[0] in types), [c for c in s.declares if c[0] not in types])


def _full_declaration(vp: str) -> tuple:
    return tuple(grid_c.cells(vp)) + ((CANCEL, "戦略の呼び出しに届く物", ""),)


def _input_mutations(inp: dict):
    yield "as_is", dict(inp)
    def each_event(fn):
        out = dict(inp)
        if "events" in out:
            out["events"] = [fn(dict(e)) for e in out["events"]]
        if "streams" in out:
            out["streams"] = {k: [fn(dict(e)) for e in v] for k, v in out["streams"].items()}
        return out
    yield "no_type_field", each_event(lambda e: {k: v for k, v in e.items() if k != "kind"})
    yield "no_events", {k: v for k, v in inp.items() if k not in ("events", "streams")}
    yield "empty_events", {**inp, **({"events": []} if "events" in inp else {}), **({"streams": {}} if "streams" in inp else {})}
    for k in ALL_SIX:
        yield f"all_{k}", each_event(lambda e, k=k: {**e, "kind": k})
    yield "outside_type", each_event(lambda e: {**e, "kind": "clock"})
    yield "strategy_text_only", {**inp, "strategy": "発注して取り消す。時計で起こして", "note": "取消の通知を受ける"}


def _plan_mutations(plan: dict):
    for slots in range(1, plan["slots"] + 1):
        for cycle in (False, True):
            for fewest in (1, 2, 6, 7):
                yield f"plan_{slots}_{cycle}_{fewest}", {"slots": slots, "min_types": fewest, "cycle": cycle}


REQUESTS = [("absent", None), ("empty", []), ("timer", ["timer"]), ("place", ["place"]), ("cancel", ["cancel"]),
            ("place_cancel", ["place", "cancel"]), ("all", ["timer", "place", "cancel"]), ("unknown", ["read"]),
            ("not_a_list", "place")]


def _copies(s):
    base = {k: v for k, v in s.input.items() if k != "requests"}
    for rname, req in REQUESTS:
        inp0 = dict(base) if req is None else {**base, "requests": req}
        for dname, decl in (("full", _full_declaration(s.viewpoint)), ("none", ())):
            if s.type_plan is None:
                for mname, inp in _input_mutations(inp0):
                    yield f"{mname}/{rname}/{dname}", replace(s, input=inp, declares=decl)
            else:
                for mname, plan in _plan_mutations(s.type_plan):
                    yield f"{mname}/{rname}/{dname}", replace(s, input=inp0, declares=decl, type_plan=plan)


@pytest.mark.parametrize("s", scenes.SCENES, ids=[s.id for s in scenes.SCENES])
def test_covers_follow_the_definition_on_every_copy(s):
    runs = 0
    for name, c in _copies(s):
        try:
            want = _oracle(c)
        except Refused:
            with pytest.raises(ValueError):
                scenes.covers_of(c)
            with pytest.raises(ValueError):
                scenes.covers_problems(c)
            runs += 1
            continue
        assert scenes.covers_of(c) == want[0], (s.id, name)
        assert c.covers == want[0], (s.id, name)
        assert scenes.covers_problems(c) == want[1], (s.id, name)
        runs += 1
    assert runs == len(list(_copies(s)))


@pytest.mark.parametrize("s", scenes.SCENES, ids=[s.id for s in scenes.SCENES])
def test_every_scene_declares_only_cells_its_input_gives(s):
    counted, dropped = _oracle(s)
    assert not dropped, (s.id, dropped)
    assert s.covers == counted == tuple(s.declares) == tuple(scenes.COVERS[s.id])


def test_a_declaration_the_input_does_not_give_is_named_not_dropped_silently():
    """Every scene x every cell of its viewpoint's range not given by its input: declared on a copy, it is named by
    covers_problems and left out of covers."""
    checked = 0
    for s in scenes.SCENES:
        types = _oracle_types(s)
        for cell in _full_declaration(s.viewpoint):
            if cell[0] in types:
                continue
            c = replace(s, declares=tuple(s.declares) + (cell,))
            assert scenes.covers_problems(c) == [cell], (s.id, cell)
            assert cell not in c.covers
            checked += 1
    assert checked > 0


def test_swapping_one_order_notice_for_another_is_left_to_the_declaration():
    """Not machine (section 3): on a copy of every scene holding the order request, a declared order notice swapped for
    another of the three is still counted -- which of the three a scene measures is the critic's reading."""
    notices = ["注文の受付の通知", "注文の拒否の通知", "注文の約定の通知"]
    seen = 0
    for s in scenes.SCENES:
        for i, cell in enumerate(s.declares):
            if cell[0] not in notices:
                continue
            for other in notices:
                decl = list(s.declares)
                decl[i] = (other,) + tuple(cell[1:])
                c = replace(s, declares=tuple(decl))
                assert (other,) + tuple(cell[1:]) in c.covers and not scenes.covers_problems(c)
                seen += 1
    assert seen > 0


def test_the_cancel_notice_stays_outside_the_event_axis():
    ev, _, _ = grid_c.axes()
    assert CANCEL not in ev
    rows = grid_c.table(scenes.SCENES)
    assert not [r for r in rows if r["event"] == CANCEL]
    assert CANCEL in scenes.OUTSIDE_AXES
    assert [s.id for s in scenes.SCENES if any(c[0] == CANCEL for c in s.covers)] == ["p6-cancel-notice"]
    text = (HERE / "DEFINITIONS.md").read_text(encoding="utf-8")
    assert f"- 軸の外の升目を覆う場面がある: {CANCEL}" in text


def test_the_table_is_made_from_covers_of_not_from_a_field_written_by_hand():
    """grid_c reads the counted cells; a scene whose declaration the input does not give is not "場面にした" there."""
    s = next(x for x in scenes.SCENES if x.id == "p2-event-time-exact")
    bad = replace(s, declares=(("約定", "戦略の呼び出しに届く物", "int64 ナノ秒"),))
    rows = grid_c.table([bad])
    hit = [r for r in rows if r["viewpoint"] == "P0-2" and r["event"] == "約定"
           and r["see"] == "戦略の呼び出しに届く物" and r["extra"] == "int64 ナノ秒"]
    assert hit and hit[0]["verdict"] == grid_c.VERDICTS[1]
