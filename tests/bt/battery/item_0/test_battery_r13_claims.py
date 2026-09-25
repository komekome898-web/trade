"""Round r13-1 (critic i0-r11-02, L-443): the (c) tests of the claim table of ROOTCAUSE_r13-1.md section 4 for the
claims the table's families 2, 5, 6 and 7 name -- written BEFORE the machine was changed (the delegation's scrutiny
(6)). Family 1, 3 and 4 have their tests in test_battery_r13_covers_of.py and the critic's
tests/bt/critic/item_0/test_i0r11_covers_within_scene_input.py.

  family 2  the `requests` field of a scene is what the scene's strategy asks: the reference strategy (the scene
            set's own adapter for the new implementation, adapters/new_impl.py) is run on every scene and the request
            kinds it records must equal the field (a field written by hand that is wrong fails here);
  family 5  the records `types_in` / `types_added` (LEAD_DESIGN.md section 9.2 item 33): every row of
            survey_results/ holds them and `types_in` is within the market types of the input the runner handed; the
            record function follows its rule on the whole grid of its inputs; no adapter changes a scene event's type
            outside the shared parts of adapters/common.py (read from the syntax tree of every adapter file);
  family 6  the record `requests`: within the field, in every row of survey_results/ and for our two targets;
  family 7  `grid_c.not_entered` on the whole grid of its inputs.

Oracles are written here from the claim table's words, not from the code under test. Not in the grids (and why):
  * a target's own API call that turns a trade into a bar without a dict (a target object built straight from the
    event's fields): the syntax tree cannot tell a substitution from a use; the records then rely on the configured
    target's own types (L-438 (2)), which limit `types_in` for the scenes without a delivered list;
  * whether the adapters of the survey tools call `request` (they do not record requests; ROOTCAUSE_r13-1.md
    section 8 item 5 asks the lead);
  * which of the three order notices a scene measures (family 3: left to the declaration and the critic);
  * the record function's grid (test_records_of_on_every_case) takes one scene per shape of what reached the
    strategy (a list with kinds, per-run lists with kinds, a list without kinds, no list), not every scene; the real
    rows of every scene are checked by test_records_types_in_within_the_input_handed.
"""
from __future__ import annotations

import ast
import csv
import itertools
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "adapters"))

import scenes  # noqa: E402

MARKET_JP = {"trade": "約定", "book_snapshot": "板の写真", "book_delta": "板の差分", "bar": "足",
             "funding": "資金調達", "liquidation": "清算"}
MARKET_JP_INV = {v: k for k, v in MARKET_JP.items()}
REQUEST_KINDS = ("timer", "place", "cancel")
csv.field_size_limit(1 << 30)


def _field(s) -> list:
    inp = s.input if isinstance(s.input, dict) else {}
    return list(inp.get("requests") or [])


def _built(s):
    return scenes.for_target_types(s, list(MARKET_JP)) if s.type_plan is not None else s


def _market_kinds(inp) -> set:
    inp = inp if isinstance(inp, dict) else {}
    evs = list(inp.get("events") or [])
    for stream in (inp.get("streams") or {}).values():
        evs += list(stream)
    return {MARKET_JP[e["kind"]] for e in evs if isinstance(e, dict) and e.get("kind") in MARKET_JP}


# ---------------------------------------------------------------- family 2: the field against the reference strategy
_REF: dict = {}


def reference_requests(target: str = "new_impl") -> dict:
    """{scene id: request kinds the target's adapter strategy recorded} for every scene (built for all six types)."""
    if target not in _REF:
        import run_battery
        import common as C
        adapter = run_battery.load_adapter(target)
        out = {}
        for s in scenes.SCENES:
            run_battery._run_one(adapter, _built(s))
            out[s.id] = list(C.requests_taken())
        _REF[target] = out
    return _REF[target]


def field_problems(field_of, recorded: dict, equal: bool) -> list:
    """Scenes whose field is not the recorded requests (equal) or does not hold them (subset)."""
    out = []
    for s in scenes.SCENES:
        f, r = set(field_of(s)), set(recorded[s.id])
        if (f != r) if equal else not (r <= f):
            out.append((s.id, sorted(f), sorted(r)))
    return out


def test_the_requests_field_is_what_the_reference_strategy_asks():
    import run_battery
    assert getattr(run_battery.load_adapter("new_impl"), "records_requests", False)
    assert not field_problems(_field, reference_requests("new_impl"), equal=True)


def test_the_current_implementations_requests_are_within_the_field():
    import run_battery
    assert getattr(run_battery.load_adapter("current_impl"), "records_requests", False)
    assert not field_problems(_field, reference_requests("current_impl"), equal=False)


def test_every_request_kind_is_asked_by_some_scene():
    """The field's kinds are all used (a kind no scene asks would be a machine path never measured)."""
    assert {k for s in scenes.SCENES for k in _field(s)} == set(REQUEST_KINDS)


# ---------------------------------------------------------------- families 5 and 6: the records in survey_results/
def survey_rows() -> list[tuple[str, dict]]:
    out = []
    for p in sorted((HERE / "survey_results").glob("*.tsv")):
        with p.open(encoding="utf-8") as f:
            out += [(p.name, r) for r in csv.DictReader(f, delimiter="\t")]
    return out


def handed_types(row: dict) -> set:
    """The market types of the input the runner handed the configured target (a `type_plan` scene: the types it
    built for that target, the column types_1)."""
    s = next(x for x in scenes.SCENES if x.id == row["scene_id"])
    if s.type_plan is None:
        return _market_kinds(s.input)
    types = json.loads(row["types_1"]) if row.get("types_1") not in (None, "") else None
    if isinstance(types, dict):  # slot -> type (the streams of a type_plan scene)
        types = list(types.values())
    return {MARKET_JP[k] for k in (types or []) if k in MARKET_JP}


def records_problems(rows) -> list:
    out = []
    for name, r in rows:
        for col in ("types_in", "types_added", "requests"):
            if col not in r or r[col] in (None, ""):
                out.append((name, r.get("scene_id"), f"列 {col} が無い"))
        if any(p[0] == name and p[1] == r.get("scene_id") for p in out):
            continue
        tin = json.loads(r["types_in"])
        if not set(tin) <= handed_types(r):
            out.append((name, r["scene_id"], "types_in が渡した入力の型の外", tin, sorted(handed_types(r))))
        req = json.loads(r["requests"])
        s = next(x for x in scenes.SCENES if x.id == r["scene_id"])
        if req is not None and not set(req) <= set(_field(s)):
            out.append((name, r["scene_id"], "requests が欄の外", req, _field(s)))
    return out


def test_records_types_in_within_the_input_handed():
    rows = survey_rows()
    assert rows
    assert not records_problems(rows)


def test_records_requests_within_the_field():
    rows = survey_rows()
    assert rows and all("requests" in r for _, r in rows)
    assert not [p for p in records_problems(rows) if "requests" in str(p[2])]


# ---------------------------------------------------------------- family 5: no substitution outside common
ADAPTER_FILES = sorted([*(HERE / "adapters").glob("*.py"), *(HERE / "opponents").glob("*.py"),
                        *(HERE / "opponents" / "repro_engines").glob("*.py")])
SHARED = {HERE / "adapters" / "common.py"}


def _event_fields() -> set:
    out: set = set()
    for s in scenes.SCENES:
        for x in (s, _built(s)):
            inp = x.input if isinstance(x.input, dict) else {}
            evs = list(inp.get("events") or [])
            for stream in (inp.get("streams") or {}).values():
                evs += list(stream)
            for e in evs:
                if isinstance(e, dict):
                    out |= set(e) - {"kind"}
    return out


def _reads_event_field(node, fields) -> bool:
    for n in ast.walk(node):
        if isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Constant) and n.slice.value in fields:
            return True
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in ("get", "recv")
                and n.args and (isinstance(n.args[0], ast.Name) or
                                (isinstance(n.args[0], ast.Constant) and n.args[0].value in fields))):
            return True
    return False


def substitution_sites(tree, fields) -> list[int]:
    """Lines where a dict holding a type field of a market type (or of an unknown value) is built from a scene
    event's fields: a dict display with a "kind" key and a value reading an event field or unpacking a mapping, or
    dict(<event>, kind=...)."""
    sites = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Dict):
            kinds = [v for k, v in zip(n.keys, n.values) if isinstance(k, ast.Constant) and k.value == "kind"]
            # a type field of a market type, or one whose value is not a constant; a target's own form ("tick") is not
            # a scene type
            if not any(not isinstance(v, ast.Constant) or v.value in MARKET_JP for v in kinds):
                continue
            others = [v for k, v in zip(n.keys, n.values) if not (isinstance(k, ast.Constant) and k.value == "kind")]
            unpack = any(k is None for k in n.keys)
            if unpack or any(_reads_event_field(v, fields) for v in others):
                sites.append(n.lineno)
        elif (isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "dict"
              and any(kw.arg == "kind" for kw in n.keywords) and n.args):
            sites.append(n.lineno)
    return sites


def test_no_adapter_builds_a_substitute_event_outside_common():
    fields = _event_fields()
    assert {"ts_ns", "price"} <= fields
    found = []
    for p in ADAPTER_FILES:
        if p in SHARED:
            continue
        for line in substitution_sites(ast.parse(p.read_text(encoding="utf-8")), fields):
            found.append(f"{p.relative_to(HERE)}:{line}")
    assert not found, found


def test_the_substitution_finder_sees_every_form():
    """The finder's own grid: each form of building a typed event from a scene event is found; a probe built from
    constants and a dict without a type field are not."""
    fields = {"ts_ns", "price", "qty", "recv_ns", "close"}
    found = ['{"kind": "bar", "ts_ns": e["ts_ns"], "close": 1.0}', '{"kind": k, "ts_ns": e["ts_ns"]}',
             '{**e, "kind": "bar"}', 'dict(e, kind="bar")', '{"kind": "bar", "close": e.get("price")}',
             '{"kind": "bar", "ts_ns": C.recv(e)}']
    not_found = ['{"kind": "bar", "ts_ns": 1_700_000_000, "close": 1.0}', '{"ts_ns": e["ts_ns"], "close": 1.0}',
                 'dict(e, price=1.0)', '{"kind": "tick", "ts_ns": e["ts_ns"], "bid": e["price"]}']
    for src in found:
        assert substitution_sites(ast.parse(src), fields), src
    for src in not_found:
        assert not substitution_sites(ast.parse(src), fields), src


# ---------------------------------------------------------------- family 5 and 6: the record function's grid
def _oracle_records(handed, delivered, called, substituted, requests, records_requests, own):
    """From the claim table's words (family 5, 6)."""
    if not called:
        return {"types_in": [], "types_added": [], "requests": [] if records_requests else None}
    if delivered is not None:
        tin = [k for k in handed if k in delivered]
        added = sorted(set(delivered) - set(handed))
    else:
        tin = [k for k in handed if k not in substituted and k in own]
        added = []
    return {"types_in": [MARKET_JP[k] for k in tin], "types_added": [MARKET_JP.get(k, k) for k in added],
            "requests": list(requests) if records_requests else None}


def _cases():
    import adapters.protocol as P
    carrier = next(s for s in scenes.SCENES if s.id == "p3-mixed-one-run")          # a list of delivered kinds
    runs = _built(next(s for s in scenes.SCENES if s.id == "p5-hand-over-order"))  # per-run lists with kinds
    no_kinds = next(s for s in scenes.SCENES if s.id == "p2-event-time-exact")       # a list without kinds
    plain = next(s for s in scenes.SCENES if s.id == "p4-received-time")             # no delivered list
    for s, status, delivered, called, subst, req, rr, own in itertools.product(
            (carrier, runs, no_kinds, plain), ("ok", "not_supported", "error"),
            # round r15-1 (the lead's answer to br13-1-3): a target's own form ("tick", as the gobacktest adapter
            # builds from a trade) reaching the strategy is not the handed trade
            (None, ["trade"], ["trade", "bar"], ["bar"], ["tick"], ["tick", "bar"]), (True, False), ([], ["trade"]),
            ([], ["place"], ["timer", "place", "cancel"]), (True, False),
            ([], ["trade"], list(MARKET_JP))):
        if delivered is None:
            out = {}
        elif s is runs:  # two runs, the kinds split between them
            out = {"runs": [{"order": [[k, 0] for k in delivered[:1]]}, {"order": [[k, 0] for k in delivered[1:]]}]}
        else:
            out = {"sequence": [[k, 0] for k in delivered]}
        res = P.SceneResult(status, output=out if status == "ok" else None)
        got_delivered = delivered if (s in (carrier, runs) and status == "ok" and delivered is not None) else None
        handed = [MK for MK in MARKET_JP if MK in {MARKET_JP_INV[t] for t in _market_kinds(s.input)}]
        yield (s, res, called, subst, req, rr, own), (handed, got_delivered, called, subst, req, rr, own)


def test_records_of_on_every_case():
    import run_battery
    n = 0
    for args, oracle_args in _cases():
        assert run_battery.records_of(*args) == _oracle_records(*oracle_args), (args[0].id, args[1:], oracle_args)
        n += 1
    assert n == 4 * 3 * 6 * 2 * 2 * 3 * 2 * 3


# ---------------------------------------------------------------- family 7: not_entered
def _oracle_not_entered(rows, records):
    """Cells the table counts whose event type entered no covering scene's run (market types from types_in, the
    clock and the notices from requests); cells whose covering scenes all have no request record are apart."""
    gives = {"時計": "timer", "注文の受付の通知": "place", "注文の拒否の通知": "place", "注文の約定の通知": "place"}
    miss, unknown = [], []
    for r in rows:
        if r["verdict"] != "場面にした":
            continue
        cell = (r["viewpoint"], r["event"], r["see"], r["extra"])
        recs = [records.get(i) for i in r["scenes"]]
        if r["event"] in gives:
            known = [x for x in recs if x is not None and x.get("requests") is not None]
            if not known:
                unknown.append(cell)
            elif not any(gives[r["event"]] in x["requests"] for x in known):
                miss.append(cell)
        elif not any(x is not None and r["event"] in x.get("types_in", []) for x in recs):
            miss.append(cell)
    return {"入らなかった": miss, "記録なし": unknown}


def test_not_entered_on_every_case():
    import grid_c
    rows = [{"viewpoint": "P0-3", "event": e, "see": "戦略の呼び出しに届く物", "extra": "", "verdict": v, "scenes": ids}
            for e, v, ids in (("約定", "場面にした", ["a", "b"]), ("足", "場面にした", ["a"]),
                              ("時計", "場面にした", ["c"]), ("注文の受付の通知", "場面にした", ["c", "d"]),
                              ("清算", "測っていない(固定した測り方の外)", []))]
    rec_values = [None, {"types_in": [], "requests": None}, {"types_in": ["約定"], "requests": []},
                  {"types_in": ["足"], "requests": ["timer"]}, {"types_in": ["約定", "足"], "requests": ["place"]}]
    n = 0
    for combo in itertools.product(rec_values, repeat=4):
        records = {k: v for k, v in zip("abcd", combo) if v is not None}
        assert grid_c.not_entered(rows, records) == _oracle_not_entered(rows, records), combo
        n += 1
    assert n == 5 ** 4


# ---------------------------------------------------------------- the texts DEFINITIONS.md shows for family 1-4
def test_the_rule_texts_are_the_sources_character_for_character():
    """DEFINITIONS.md says F is verbatim LEAD_DESIGN.md section 9.2 item 32 and the round r13-1 definition is
    ROOTCAUSE_r13-1.md section 3 unchanged; both claims are checked here."""
    import gen_definitions as G
    lead = (HERE.parents[3] / "docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/round_7/LEAD_DESIGN.md").read_text(
        encoding="utf-8")
    assert G.LEAD_F in [ln.strip() for ln in lead.split("\n")]
    rc = (HERE / "ROOTCAUSE_r13-1.md").read_text(encoding="utf-8").split("\n")
    i = next(n for n, ln in enumerate(rc) if ln.startswith("## 3. "))
    para = [ln for ln in rc[i + 1:next(n for n in range(i + 1, len(rc)) if rc[n].startswith("## "))]
            if ln.startswith("**升目を「場面にした」と数える物**")]
    assert para == [G.R13_DEFINITION]
    text = (HERE / "DEFINITIONS.md").read_text(encoding="utf-8")
    assert G.LEAD_F in text and G.R13_DEFINITION in text
