"""Round r13-1 (L-443): the (d) column of ROOTCAUSE_r13-1.md section 4 -- mutants of the machines that make the claims,
each of which the (c) checks must catch. A mutant that no check catches means the check does not guard the claim.

Each mutant replaces one machine function (monkeypatch) by a wrong version that a hand-written claim or a slip could
produce; the test runs the family's oracle over its grid (the same grids as the (c) tests) and asserts that at least
one case differs. What is not a mutant here (and why):
  * family 3 (which of the three order notices a scene measures) has no machine, so no mutant;
  * the adapters' own code (a substitution a target's API does without a dict) is read by the critic.
"""
from __future__ import annotations

import itertools
import sys
from dataclasses import replace
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "adapters"))

import grid_c  # noqa: E402
import scenes  # noqa: E402
import test_battery_r13_claims as CL  # noqa: E402
import test_battery_r13_covers_of as CO  # noqa: E402

_ORIG_INPUT_TYPES = scenes.input_types
MARKET = {scenes.JP[k] for k in scenes.TYPE_ORDER}


def _market_mismatches() -> int:
    """Cases of the covers grid (every scene x every copy) where covers_of / covers_problems differ from the oracle."""
    bad = 0
    for s in scenes.SCENES:
        for _, c in CO._copies(s):
            try:
                want = CO._oracle(c)
            except CO.Refused:
                try:
                    scenes.covers_of(c)
                    bad += 1
                except ValueError:
                    pass
                continue
            try:
                if scenes.covers_of(c) != want[0] or scenes.covers_problems(c) != want[1]:
                    bad += 1
            except ValueError:
                bad += 1
    return bad


def _no_kind_as_trade(scene):
    inp = scene.input if isinstance(scene.input, dict) else {}
    if inp.get("events") and any(isinstance(e, dict) and "kind" not in e for e in inp["events"]):
        scene = replace(scene, input={**inp, "events": [dict(e, kind=e.get("kind", "trade")) for e in inp["events"]]})
    return _ORIG_INPUT_TYPES(scene)


def _ignore_type_plan(scene):
    return _ORIG_INPUT_TYPES(replace(scene, type_plan=None)) if scene.type_plan is not None else _ORIG_INPUT_TYPES(scene)


def _all_six_when_any(scene):
    out = _ORIG_INPUT_TYPES(scene)
    return out | MARKET if out & MARKET else out


def _no_streams(scene):
    built = scenes.for_target_types(scene, scenes.TYPE_ORDER) if scene.type_plan is not None else scene
    inp = dict(built.input) if built is not None and isinstance(built.input, dict) else {}
    inp.pop("streams", None)
    own = scene.input if isinstance(scene.input, dict) else {}
    if "requests" in own:
        inp["requests"] = own["requests"]
    return _ORIG_INPUT_TYPES(replace(scene, type_plan=None, input=inp))


def _ignore_requests(scene):
    inp = scene.input
    if isinstance(inp, dict):
        inp = {k: v for k, v in inp.items() if k != "requests"}
    return _ORIG_INPUT_TYPES(replace(scene, input=inp))


MARKET_MUTANTS = {"事象の型の欄が無い事象を約定と数える": _no_kind_as_trade, "type_plan を読まない": _ignore_type_plan,
                  "市場の型が 1 つでもあれば 6 型を全部足す": _all_six_when_any, "streams を読まない": _no_streams}


def test_the_machine_itself_agrees_with_the_oracle():
    assert _market_mismatches() == 0
    assert _records_mismatches() == 0


@pytest.mark.parametrize("name", sorted(MARKET_MUTANTS))
def test_mutants_of_the_market_type_machine_are_caught(monkeypatch, name):
    monkeypatch.setattr(scenes, "input_types", MARKET_MUTANTS[name])
    assert _market_mismatches() > 0, name


def test_a_mutant_covers_of_that_returns_the_declaration_is_caught(monkeypatch):
    monkeypatch.setattr(scenes, "covers_of", lambda s: tuple(tuple(c) for c in s.declares))
    assert _market_mismatches() > 0


def test_a_mutant_verdict_that_reads_the_declaration_is_caught(monkeypatch):
    """The (c) test test_the_table_is_made_from_covers_of_not_from_a_field_written_by_hand asserts 測っていない for
    this cell; under the mutant the table says 場面にした."""
    s = next(x for x in scenes.SCENES if x.id == "p2-event-time-exact")
    bad = replace(s, declares=(("約定", "戦略の呼び出しに届く物", "int64 ナノ秒"),))

    def wrong(vp, cell, scs):
        ids = [sc.id for sc in scs if sc.viewpoint == vp and tuple(cell) in {tuple(c) for c in sc.declares}]
        return (grid_c.VERDICTS[0], ids) if ids else (grid_c.VERDICTS[1], [])
    monkeypatch.setattr(grid_c, "verdict", wrong)
    hit = [r for r in grid_c.table([bad]) if r["viewpoint"] == "P0-2" and r["event"] == "約定"
           and r["see"] == "戦略の呼び出しに届く物" and r["extra"] == "int64 ナノ秒"]
    assert hit[0]["verdict"] == grid_c.VERDICTS[0]


def test_a_mutant_that_does_not_read_the_requests_field_is_caught(monkeypatch):
    monkeypatch.setattr(scenes, "input_types", _ignore_requests)
    assert _market_mismatches() > 0


def test_a_mutant_request_mapping_is_caught(monkeypatch):
    swapped = dict(scenes.REQUEST_TYPES)
    swapped["timer"], swapped["place"] = swapped["place"], swapped["timer"]
    monkeypatch.setattr(scenes, "REQUEST_TYPES", swapped)
    assert _market_mismatches() > 0


def test_mutants_of_the_requests_field_are_caught():
    """Each scene's field with one kind dropped or one kind added (a hand-written field that is wrong) is caught by
    the reference strategy's check (test_the_requests_field_is_what_the_reference_strategy_asks)."""
    ref = CL.reference_requests("new_impl")
    n = 0
    for s in scenes.SCENES:
        f = CL._field(s)
        variants = [[k for k in f if k != d] for d in f] + [f + [a] for a in CL.REQUEST_KINDS if a not in f]
        for v in variants:
            probs = CL.field_problems(lambda x, s=s, v=v: v if x.id == s.id else CL._field(x), ref, equal=True)
            assert [p for p in probs if p[0] == s.id], (s.id, v)
            n += 1
    assert n >= len(scenes.SCENES)


def test_a_mutant_that_puts_the_cancel_notice_on_the_event_axis_is_caught(monkeypatch):
    orig = grid_c.axes

    def wrong():
        ev, see, extra = orig()
        return ev + [CO.CANCEL], see, extra
    monkeypatch.setattr(grid_c, "axes", wrong)
    ev, _, _ = grid_c.axes()
    assert CO.CANCEL in ev  # test_the_cancel_notice_stays_outside_the_event_axis asserts the opposite
    assert [r for r in grid_c.table(scenes.SCENES) if r["event"] == CO.CANCEL]


def _records_mismatches() -> int:
    import run_battery
    return sum(1 for args, oargs in CL._cases() if run_battery.records_of(*args) != CL._oracle_records(*oargs))


def test_mutants_of_the_records_machine_are_caught(monkeypatch):
    import run_battery
    orig = run_battery.records_of
    mutants = {
        "代えた型を除かない": lambda sr, res, called, subst, req, rr, own: orig(sr, res, called, [], req, rr, own),
        "設定つき対象の持つ型に限らない": lambda sr, res, called, subst, req, rr, own: orig(sr, res, called, subst, req, rr,
                                                                             list(scenes.TYPE_ORDER)),
        "申告しない adapter の欄を [] にする": lambda sr, res, called, subst, req, rr, own: {
            **orig(sr, res, called, subst, req, rr, own), "requests": list(req)},
        "届いた列を読まない": lambda sr, res, called, subst, req, rr, own: orig(
            sr, type(res)("not_supported"), called, subst, req, rr, own),
    }
    for name, m in mutants.items():
        monkeypatch.setattr(run_battery, "records_of", m)
        assert _records_mismatches() > 0, name


def test_mutants_of_not_entered_are_caught(monkeypatch):
    orig = grid_c.not_entered
    rows = [{"viewpoint": "P0-3", "event": e, "see": "戦略の呼び出しに届く物", "extra": "", "verdict": "場面にした",
             "scenes": ids} for e, ids in (("約定", ["a", "b"]), ("時計", ["c"]), ("注文の受付の通知", ["c", "d"]))]
    recs = [None, {"types_in": [], "requests": None}, {"types_in": ["約定"], "requests": ["place"]},
            {"types_in": [], "requests": ["timer"]}]

    def bad() -> int:
        n = 0
        for combo in itertools.product(recs, repeat=4):
            r = {k: v for k, v in zip("abcd", combo) if v is not None}
            n += grid_c.not_entered(rows, r) != CL._oracle_not_entered(rows, r)
        return n
    assert bad() == 0

    def no_unknown(rows_, records):
        return orig(rows_, {k: {**v, "requests": v.get("requests") or []} for k, v in records.items()})

    def first_scene_only(rows_, records):
        return orig([{**r, "scenes": r["scenes"][:1]} for r in rows_], records)

    def ignore_requests(rows_, records):
        return orig(rows_, {k: {**v, "requests": []} for k, v in records.items()})
    for name, m in {"記録なしを入らなかったにする": no_unknown, "覆う場面の最初だけを見る": first_scene_only,
                    "頼みを見ない": ignore_requests}.items():
        monkeypatch.setattr(grid_c, "not_entered", m)
        assert bad() > 0, name
