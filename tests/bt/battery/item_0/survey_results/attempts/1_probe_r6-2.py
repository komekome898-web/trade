"""Probe (round r6-2, scene keeper; the r6-1 probe re-run under the positive provenance check): Basana's own merge-by-time and same-time
priority mechanisms on the scene set's P0-1 / P0-5 inputs with only the
types Basana's distribution has (trade, bar). The scenes themselves include
funding (and liquidation), for which Basana has no class, so the recorded
cells are "not supported"; this probe measures the mechanism the review
table cites as containing another candidate's ability.

Events are carried in Basana's own classes only (adapter's `_event`, checked
with the runner's provenance check). Nothing here changes the scene set.
Run with the Basana survey venv, cwd = tests/bt/battery/item_0.
"""
from __future__ import annotations

import dataclasses
import json
import sys
from itertools import permutations

sys.path[:0] = [".", "adapters", "opponents"]
import run_battery  # noqa: E402
import scenes  # noqa: E402
import stated_rules  # noqa: E402
import basana_adapter as B  # noqa: E402

KEEP = ("trades", "bars")


def reduced(scene_id: str):
    sc = next(s for s in scenes.SCENES if s.id == scene_id)
    streams = {k: v for k, v in sc.input["streams"].items() if k in KEEP}
    inp = {**sc.input, "streams": streams}
    if "hand_over_order" in inp:
        inp["hand_over_order"] = [k for k in inp["hand_over_order"] if k in KEEP]
    return dataclasses.replace(sc, input=inp)


# P0-1 ability 3: two typed inputs handed over trades first; Basana's multiplexer must deliver by time
sc = reduced("p1-merge-by-time")
res = run_battery.checked(B.BasanaAdapter().scene_p1_merge_by_time(sc), sc, "opp_basana")
out = res.output if isinstance(res.output, dict) else {}
want = sorted([[e["kind"], e["ts_ns"]] for evs in sc.input["streams"].values() for e in evs], key=lambda x: x[1])
handed = [[e["kind"], e["ts_ns"]] for k in sc.input["hand_over_order"] for e in sc.input["streams"][k]]
print("P1-MERGE hand_over", sc.input["hand_over_order"], "status", res.status, "provenance_error", out.get("provenance_error"))
print("P1-MERGE handed_over_order", json.dumps(handed))
print("P1-MERGE delivered", json.dumps(out.get("sequence")), "carriers", [c.get("type") for c in (res.provenance or {}).get("carriers") or []])
print("P1-MERGE time_order", json.dumps(want), "EQUAL", out.get("sequence") == want)

# P0-5 abilities 1-2: same-time trade and bar as two sources, both hand-over orders, the documented priority
rule = stated_rules.rule_for("opp_basana")
p5 = reduced("p5-same-time-twice")
orders = set()
for hand_over in permutations(KEEP):
    recs = B.run_streams([p5.input["streams"][k] for k in hand_over], priorities=True)
    got = [[r[0], r[2]] for r in recs]
    carriers = [r[4] for r in recs]
    pred = stated_rules.predicted(rule, p5.input["streams"], list(hand_over))
    why = run_battery._carrier_problem([g[0] for g in got], carriers, run_battery.roots_of("opp_basana"))
    orders.add(json.dumps(got))
    print("P5 hand_over", list(hand_over), "delivered", json.dumps(got), "carriers", [c.get("type") for c in carriers],
          "carrier_check", why, "stated_rule_order", json.dumps(pred), "FOLLOWS", got == pred)
print("P5 distinct_orders_over_hand_overs", len(orders))
