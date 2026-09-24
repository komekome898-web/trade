"""Self-checks of the item-0 scene set (scene keeper's tests, rule 7).

They check the battery itself, not any engine: the definitions document is
in sync with scenes.py, every viewpoint has a value scene, the runner grades
by the expected result, the canary changes exactly the stated behaviour of
the new core, and the candidate pool is reproducible from its script.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "adapters"))

import gen_definitions  # noqa: E402
import run_battery  # noqa: E402
import scenes  # noqa: E402
from adapters.protocol import SceneResult  # noqa: E402


def test_definitions_in_sync_with_scenes():
    assert (HERE / "DEFINITIONS.md").read_text(encoding="utf-8") == gen_definitions.render()


def test_every_viewpoint_has_a_value_scene_and_every_scene_an_expected():
    for vp in scenes.VIEWPOINTS:
        assert any(s.viewpoint == vp and s.kind == "value" for s in scenes.SCENES)
    for s in scenes.SCENES:
        assert s.expected is not None and s.derivation and s.measures


def test_grading_uses_expected_not_the_adapters_word():
    exp = {"a": 1}
    assert run_battery.correctness(SceneResult("ok", {"a": 1, "extra": 2}), exp) == "正解と一致"
    assert run_battery.correctness(SceneResult("ok", {"a": 2}), exp) == "不一致"
    assert run_battery.correctness(SceneResult("ok", None), exp) == "不一致"
    assert run_battery.correctness(SceneResult("not_supported"), exp) == "対応なし"
    assert run_battery.correctness(SceneResult("error"), exp) == "結果なし"


def test_current_impl_runs_every_scene_twice_identically():
    rows = run_battery.run_target("current_impl")
    assert len(rows) == len(scenes.SCENES)
    assert all(r["reproducibility"] == "2 回の実行で同じ" for r in rows)
    assert all(r["status_1"] != "error" for r in rows), [r["detail_1"] for r in rows if r["status_1"] == "error"]


def test_mutant_core_delivers_early_and_nothing_else():
    core = pytest.importorskip("bot.bt.core")
    import mutant

    def delivered(ns):
        seen = []

        class S(ns.Strategy):
            def on_event(self, event, ctx):
                seen.append((type(event).__name__, int(ctx.now_ns)))

        evs = [ns.TradeEvent(exchange_time_ns=10, received_time_ns=30, price=1.0, size=1.0, side="buy"),
               ns.TradeEvent(exchange_time_ns=20, received_time_ns=20, price=1.0, size=1.0, side="buy")]
        ns.CoreEngine(S(), evs).run()
        return seen

    real = delivered(core)
    mut = delivered(mutant.mutant_core())
    assert real == [("TradeEvent", 20), ("TradeEvent", 30)]
    assert mut == [("TradeEvent", 10), ("TradeEvent", 20)]


def test_pool_reproducible(tmp_path):
    out = tmp_path / "pool.tsv"
    subprocess.run([sys.executable, str(HERE / "gen_pool.py"), "--out", str(out)], check=True, capture_output=True)
    assert out.read_text(encoding="utf-8") == (HERE / "pool.tsv").read_text(encoding="utf-8")


def test_considered_table_passes_the_checker():
    """Rule 9: the review table of unrunnable candidates passes the checker
    (form, the reason words, and an aggregate block that matches the rows)."""
    repo = HERE.parents[3]
    r = subprocess.run([sys.executable, str(repo / "scripts" / "check_bt_considered.py"),
                        str(HERE / "opponents" / "CONSIDERED.md")], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_every_reproduction_named_in_the_table_runs_every_scene():
    """A candidate the table marks 再現した is run through all scenes by the runner."""
    import re
    text = (HERE / "opponents" / "CONSIDERED.md").read_text(encoding="utf-8")
    for path in set(re.findall(r"opponents/(repro_[\w]+)\.py", text)):
        rows = run_battery.run_target(path)
        assert len(rows) == len(scenes.SCENES)


def test_considered_table_covers_the_pool_exactly():
    """Every pool candidate of a viewpoint is either named runnable or has a row
    in the review table, and nothing outside the pool appears."""
    import csv
    import collections
    import re
    pool = collections.defaultdict(set)
    with (HERE / "pool.tsv").open(encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            if r["viewpoint"].startswith("P0-"):
                pool[r["viewpoint"]].add(int(r["cand"]))
    text = (HERE / "opponents" / "CONSIDERED.md").read_text(encoding="utf-8")
    secs = re.split(r"^### 観点 ", text, flags=re.M)[1:]
    assert sorted(s[:4] for s in secs) == sorted(pool)
    for s in secs:
        vp = s[:4]
        line = re.search(r"動かせた候補: \d+ 件\((.*)\)", s).group(1)
        run = {int(x) for x in re.findall(r"(?:^|, )(\d+) ", line)}
        rows = {int(m) for m in re.findall(r"^\| (\d+) ", s, flags=re.M)}
        assert not run & rows, vp
        assert run | rows == pool[vp], vp


# ---------------------------------------------------------------- round r4-1
def _scene(scene_id):
    return next(s for s in scenes.SCENES if s.id == scene_id)


def test_graders_are_exactly_the_scenes_that_say_graded_from():
    assert set(run_battery.GRADERS) == {s.id for s in scenes.SCENES if s.graded_from}


def test_no_expected_is_met_by_a_target_that_reports_nothing_or_zeros():
    """A value/capability scene whose expected result a target can produce
    without the capability (all zeros, empty lists, False, None) measures
    nothing (i0-r3-03's kind; p7-cost-zero was one: fee 0.0)."""
    def zero(v):
        if isinstance(v, bool):
            return False
        if isinstance(v, (int, float)):
            return 0
        if isinstance(v, list):
            return []
        return None

    for s in scenes.SCENES:
        exp = s.expected
        degenerate = [None, {}, []]
        if isinstance(exp, dict):
            degenerate.append({k: zero(v) for k, v in exp.items()})
        for out in degenerate:
            res = SceneResult("ok", out)
            assert run_battery.correctness(res, exp, s) != "正解と一致", (s.id, out)


def _p4(*attempts):
    return SceneResult("ok", {"attempts": [dict(means=m, form=f, raised=r, returned=v) for m, f, r, v in attempts]})


def test_p4_only_an_error_on_every_named_read_is_correct():
    sc = _scene("p4-future-read-attempt")
    grade = lambda res: run_battery.correctness(res, sc.expected, sc)  # noqa: E731
    assert grade(_p4(("by time", "time", "LookAheadError", None), ("by index", "position", "IndexError", None))) == "正解と一致"
    # silently truncated, empty, NaN: passed through, not stopped (REQUIREMENTS.md P0-4)
    assert grade(_p4(("by time", "time", None, [100.0, 101.0, 102.0, 103.0]))) == "不一致"
    assert grade(_p4(("by time", "time", None, []))) == "不一致"
    assert grade(_p4(("by index", "position", None, float("nan")))) == "不一致"
    # the future value through any read, named or not
    assert grade(_p4(("by time", "time", "KeyError", None), ("whole array", "other", None, [103.0, 104.0]))) == "不一致"
    # no named read at all is not a pass
    assert grade(_p4(("latest", "other", None, 103.0))) == "不一致"


def test_p5_same_time_needs_every_event_and_the_rule_fixed_in_the_scene_set():
    """The order is graded against the target's rule in stated_rules.py,
    applied by the runner; an order the adapter writes is ignored (i0-r4-05)."""
    sc = _scene("p5-same-time-twice")
    t = scenes.T0 + scenes.DAY
    four = [["liquidation", t], ["funding", t], ["trade", t], ["bar", t]]
    grade = lambda out, target: run_battery.correctness(SceneResult("ok", out), sc.expected, sc, target)  # noqa: E731
    assert grade({"order": four}, "new_impl") == "正解と一致"
    assert grade({"order": list(reversed(four))}, "new_impl") == "不一致"       # not the target's rule
    assert grade({"order": four}, None) == "不一致"                               # no rule for the target
    assert grade({"order": four}, "opp_no_rule_written") == "不一致"
    assert grade({"order": [["trade", t]]}, "new_impl") == "不一致"               # three events dropped
    wrong = list(reversed(four))                                                  # an adapter's own "rule" is not read
    assert grade({"order": wrong, "stated_rule": {"source": "s", "quote": "q", "predicted": wrong}}, "new_impl") == "不一致"


def test_p5_hand_over_single_input_keeping_its_order_is_correct_and_multi_input_must_not_move(monkeypatch):
    import stated_rules as R
    monkeypatch.setitem(R.STATED_RULES, "t_single", R.StatedRule("s", "q", "single_input", "stable_by_time"))
    sc = _scene("p5-hand-over-order")
    grade = lambda out, target: run_battery.correctness(SceneResult("ok", out), sc.expected, sc, target)  # noqa: E731
    orders = sc.input["hand_over_orders"]

    def concat(o):
        return [[e["kind"], e["ts_ns"]] for name in o for e in sc.input["streams"][name]]

    single = {"form": "single_input", "runs": [{"hand_over": o, "order": concat(o)} for o in orders]}
    assert grade(single, "t_single") == "正解と一致"
    assert grade(single, "new_impl") == "不一致"                   # the rule is written for separate streams
    moving = {"form": "multi_input", "runs": [{"hand_over": o, "order": concat(o)} for o in orders]}
    assert grade(moving, "new_impl") == "不一致"
    fixed = R.FIXED_PREDICTED["new_impl"]
    steady = {"form": "multi_input", "runs": [{"hand_over": o, "order": fixed} for o in orders]}
    assert grade(steady, "new_impl") == "正解と一致"
    dropped = {"form": "multi_input", "runs": [{"hand_over": o, "order": fixed[:1]} for o in orders]}
    assert grade(dropped, "new_impl") == "不一致"
    # runs must be the scene's own 24 hand-over orders, in the scene's order
    shuffled = {"form": "multi_input", "runs": [{"hand_over": o, "order": fixed} for o in reversed(orders)]}
    assert grade(shuffled, "new_impl") == "不一致"


def test_stated_rule_recipes_reproduce_the_hand_written_orders():
    """Two derivations of the correct order must agree: the one written by hand
    from each quote (FIXED_PREDICTED) and the recipe the runner applies."""
    import stated_rules as R
    sc = _scene("p5-same-time-twice")
    assert set(R.FIXED_PREDICTED) == set(R.STATED_RULES)
    for target, rule in R.STATED_RULES.items():
        assert R.predicted(rule, sc.input["streams"], sc.input["hand_over_order"]) == R.FIXED_PREDICTED[target], target
        assert sorted(R.FIXED_PREDICTED[target]) == sorted(run_battery._all_tie_events(sc)), target
        assert rule.form in ("multi_input", "single_input") and rule.source and rule.quote
        assert not __import__("re").search(r"\d+\s*[-〜]\s*\d+\s*行|:\d+", rule.source), (
            f"{target}: cite the rule by a name, not by line numbers (i0-r4-05)")


def test_new_impl_rule_copy_matches_the_core_by_name():
    core = pytest.importorskip("bot.bt.core")
    import stated_rules as R
    live = core.ORDERING_RULE["source_merge"]
    for k, v in R.NEW_IMPL_SOURCE_MERGE.items():
        assert live[k] == v, (k, live[k], v)
    assert R.STATED_RULES["new_impl"].params["type_order"] == [t.lower() for t in live["type_order"]]


def test_no_adapter_reports_a_rule_or_a_predicted_order():
    import re
    bad = []
    for p in sorted([*(HERE / "adapters").glob("*.py"), *(HERE / "opponents").glob("*.py")]):
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            code = line.split("#", 1)[0]
            if re.search(r"[\"']predicted[\"']|[\"']stated_rule[\"']|stated_rule\(", code):
                bad.append(f"{p.name}:{i}: {line.strip()}")
    assert not bad, bad
    rows = {r["scene_id"]: r for r in run_battery.run_target("current_impl")}
    for sid in ("p5-same-time-twice", "p5-hand-over-order"):
        assert "stated_rule" not in rows[sid]["output_1"] and "predicted" not in rows[sid]["output_1"]


def test_p5_same_stream_input_is_not_in_price_order():
    prices = [e["price"] for e in _scene("p5-same-stream-order").input["events"]]
    assert prices not in (sorted(prices), sorted(prices, reverse=True))
    assert _scene("p5-same-stream-order").expected == {"prices": prices}


def test_no_survey_adapter_switches_off_a_protective_default():
    import re
    bad = []
    for p in sorted((HERE / "opponents").glob("*.py")):
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            code = line.split("#", 1)[0]
            if re.search(r"\benabled\s*=\s*False|set_risk_limits\s*\(", code):
                bad.append(f"{p.name}:{i}: {line.strip()}")
    assert not bad, bad


def test_every_unmapped_line_is_reviewed_in_the_table():
    """Every grep hit gen_pool.py could not map to a candidate has a row in
    CONSIDERED.md's section for those lines (critic i0-r1-17 / i0-r3-07)."""
    import re
    text = (HERE / "opponents" / "CONSIDERED.md").read_text(encoding="utf-8")
    sec = text.split("## grep で当たって候補に写せなかった行", 1)
    assert len(sec) == 2, "the section is missing"
    reviewed = set(re.findall(r"^\| (P0-\d) \| (\d+) \|", sec[1], flags=re.M))
    unmapped = set()
    for ln in (HERE / "pool.tsv").read_text(encoding="utf-8").splitlines():
        if ln.startswith("# P0-"):
            vp, n, _ = ln[2:].split("\t", 2)
            unmapped.add((vp, n))
    assert unmapped == reviewed, (sorted(unmapped - reviewed)[:10], sorted(reviewed - unmapped)[:10])


def test_single_input_form_is_graded_correct_for_the_core_keeping_one_input_in_order(monkeypatch):
    """The single-input form of p5-hand-over-order through the grader, with the
    real core fed one concatenated input per hand-over order (the case of
    critic test i0-r2-07), graded by a rule written for one input (stable by
    time, like the single-input rule in stated_rules.py): keeping that
    input's own order is 正解と一致."""
    core = pytest.importorskip("bot.bt.core")
    import stated_rules as R
    monkeypatch.setitem(R.STATED_RULES, "t_single", R.StatedRule("s", "q", "single_input", "stable_by_time"))
    sc = _scene("p5-hand-over-order")
    kinds = {"trade": core.TradeEvent, "bar": core.BarEvent, "funding": core.FundingEvent,
             "liquidation": core.LiquidationEvent}

    def ev(d):
        t = d["ts_ns"]
        if d["kind"] == "bar":
            return core.BarEvent(received_time_ns=t, open=d["open"], high=d["high"], low=d["low"], close=d["close"],
                                 volume=d["volume"])
        if d["kind"] == "funding":
            return core.FundingEvent(received_time_ns=t, rate=d["rate"])
        return kinds[d["kind"]](received_time_ns=t, price=d["price"], size=d["qty"], side=d["side"])

    runs = []
    for order in sc.input["hand_over_orders"]:
        dicts = [e for name in order for e in sc.input["streams"][name]]
        got = []

        class Rec(core.Strategy):
            def on_event(self, event, ctx):
                got.append([event.EVENT_TYPE.value.lower(), int(event.exchange_time_ns)])

        core.CoreEngine(Rec(), [ev(d) for d in dicts]).run()
        runs.append({"hand_over": order, "order": got})
    out = {"form": "single_input", "runs": runs}
    assert len({json.dumps(r["order"]) for r in runs}) == 24
    assert run_battery.correctness(SceneResult("ok", out), sc.expected, sc, "t_single") == "正解と一致"
