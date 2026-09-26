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
REPO = HERE.parents[3]
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
    # the scene as listed = a target with all six types: trade, book_snapshot, book_delta, bar (round r7-1)
    four = [["book_snapshot", t], ["book_delta", t], ["trade", t], ["bar", t]]
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
    fixed = R.FIXED_PREDICTED["new_impl"][1]
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
    base = _scene("p5-same-time-twice")
    # round r7-1: each hand-written order is for the input built from that target's own types;
    # a target left out has fewer than two types and never gets this scene
    assert {t.partition('@')[0] for t in R.FIXED_PREDICTED} <= set(R.STATED_RULES)  # round r8-1: configured targets
    for target, (types, fixed) in R.FIXED_PREDICTED.items():
        sc = scenes.for_target_types(base, types)
        assert sc is not None, target
        if fixed is None:  # the rule leaves a tie
            with pytest.raises(R.RuleDoesNotDecide):
                R.predicted(R.rule_for(target), sc.input["streams"], sc.input["hand_over_order"])
            continue
        assert R.predicted(R.rule_for(target), sc.input["streams"], sc.input["hand_over_order"]) == fixed, target
        assert sorted(fixed) == sorted(run_battery._all_tie_events(sc)), target
    for target, rule in R.STATED_RULES.items():
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
    # the input of a target with the four types trade, bar, funding, liquidation (round r7-1: the
    # types come from the target; this core has all six, so any four of them are a valid input)
    sc = scenes.for_target_types(_scene("p5-hand-over-order"), ["trade", "bar", "funding", "liquidation"])
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


# ---------------------------------------------------------------- round r5-1
# The runnability ledger opponents/RUNNABILITY.tsv and the ability-by-ability
# form of the review table (ROOTCAUSE_r5-1.md, critic i0-r4-03 / i0-r4-04).
DANGER_11 = {44, 74, 120, 41, 58, 19, 112, 111, 97, 51, 118}   # delegation: tool catalogue §3


def _ledger() -> list[dict]:
    import csv
    with (HERE / "opponents" / "RUNNABILITY.tsv").open(encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def _pool() -> dict[str, set[int]]:
    import collections
    import csv
    pool = collections.defaultdict(set)
    with (HERE / "pool.tsv").open(encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            if r["viewpoint"].startswith("P0-"):
                pool[r["viewpoint"]].add(int(r["cand"]))
    return pool


def test_ledger_has_one_row_per_pool_candidate():                                    # (a)
    cands = [int(r["cand"]) for r in _ledger()]
    assert len(cands) == len(set(cands))
    assert set(cands) == set().union(*_pool().values())
    assert all(r["result"] in ("走った", "走らなかった") for r in _ledger())


def test_every_ran_candidate_has_all_scenes_from_its_own_adapter():                   # (b)
    import csv
    for r in _ledger():
        if r["result"] != "走った":
            continue
        assert r["target"] in run_battery.OPPONENTS, r["cand"]
        for t in run_battery.configured_targets(r["target"]):  # round r8-1: every configured target of the candidate
            p = HERE / "survey_results" / f"{t}.tsv"
            with p.open(encoding="utf-8") as f:
                ids = [row["scene_id"] for row in csv.DictReader(f, delimiter="\t")]
            assert sorted(ids) == sorted(s.id for s in scenes.SCENES), (r["cand"], t)


def test_every_unrun_candidate_has_an_attempt_record_or_a_stated_danger():            # (c)
    import re
    for r in _ledger():
        if r["result"] != "走らなかった":
            continue
        log = HERE / r["log"] if r["log"] != "-" else None
        if log is not None:
            assert log.is_file() and log.stat().st_size > 0, r["cand"]
            assert re.search(r"20\d\d-\d\d-\d\dT\d\d:\d\d:\d\dZ", log.read_text(encoding="utf-8")), r["cand"]
        else:
            assert int(r["cand"]) in DANGER_11 and r["reason_kind"].startswith("危険(台帳 §3"), r["cand"]
        if r["reason_kind"].startswith("危険(§6-1)"):
            assert re.search(r"SCAN \d+ 行", r["reason"]), r["cand"]


def test_a_size_or_space_reason_carries_the_disk_reading():                          # (d)
    for r in _ledger():
        if any(w in r["reason_kind"] + r["reason"] for w in ("容量", "一括の取得", "数百 MB")):
            assert r["log"] != "-", r["cand"]
            text = (HERE / r["log"]).read_text(encoding="utf-8")
            assert "/dev/" in text and "%" in text, r["cand"]   # a `df -m /` line


def test_no_record_says_it_was_not_tried():                                          # (e)
    for p in (HERE / "opponents" / "RUNNABILITY.tsv", HERE / "opponents" / "CONSIDERED.md"):
        assert "試していない" not in p.read_text(encoding="utf-8"), p.name


def test_runnable_lines_equal_the_pool_candidates_that_ran():                         # (f)
    import re
    ran = {int(r["cand"]) for r in _ledger() if r["result"] == "走った"}
    pool = _pool()
    text = (HERE / "opponents" / "CONSIDERED.md").read_text(encoding="utf-8")
    for sec in re.split(r"^### 観点 ", text, flags=re.M)[1:]:
        vp = sec[:4]
        line = re.search(r"動かせた候補: (\d+) 件(?:\((.*)\))?", sec)
        named = {int(x) for x in re.findall(r"(?:^|, )(\d+) ", line.group(2) or "")}
        rows = {int(m) for m in re.findall(r"^\| (\d+) ", sec, flags=re.M)}
        assert named == pool[vp] & ran, vp
        assert int(line.group(1)) == len(named), vp
        assert rows == pool[vp] - ran, vp


def _table_rows(sec: str):
    lines = sec.splitlines()
    for i, ln in enumerate(lines):
        if ln.startswith("| 候補 |"):
            head = [c.strip() for c in ln.strip().strip("|").split("|")]
            for row in lines[i + 2:]:
                if not row.startswith("|"):
                    break
                yield dict(zip(head, [c.strip() for c in row.strip().strip("|").split("|")]))


def test_superset_and_absent_rows_answer_every_ability_with_a_source():
    """i0-r4-03: a 上位互換 or 持たないと確認した row answers each ability of the
    viewpoint as 在る or 無い with its source; 在る names the containing ran
    candidate after 含む:; the hedging words are not used; 持たない is all 無い."""
    import re
    ran = set(_cand_targets())  # run candidates and (round r6-3) reproduced ones: 委任文 §3「動かせた候補か再現した候補の機構」
    text = (HERE / "opponents" / "CONSIDERED.md").read_text(encoding="utf-8")
    checked = 0
    for sec in re.split(r"^### 観点 ", text, flags=re.M)[1:]:
        abilities = sorted({int(n) for n in re.findall(r"\(能 (\d+)\)", sec)})
        for row in _table_rows(sec):
            verdict, why = row["判断"], row["理由"]
            if not (verdict.startswith("スキップ") or verdict.startswith("持たないと確認した")):
                continue
            checked += 1
            whole = " ".join(row.values())
            for w in ("在るとしても", "在るかは", "未確認"):
                assert w not in whole, (row["候補"], w)
            assert re.search(r"SCAN \d+ 行|https?://", whole), row["候補"]
            parts = re.split(r"能 (\d+): (在る|無い)", why)
            found = {int(parts[k]): (parts[k + 1], parts[k + 2]) for k in range(1, len(parts) - 1, 3)}
            assert sorted(found) == abilities, (row["候補"], sorted(found), abilities)
            for n, (have, seg) in found.items():
                assert re.search(r"SCAN \d+ 行|https?://|\d+(?:-\d+)? 行|grep", seg), (row["候補"], n)
                if have == "在る":
                    m = re.search(r"含む: (\d+) ", seg)
                    assert m and int(m.group(1)) in ran, (row["候補"], n)
            if verdict.startswith("持たないと確認した"):
                assert all(h == "無い" for h, _ in found.values()), row["候補"]
    assert checked > 0


# ---------------------------------------------------------------- round r6-1
# i0-r5-02 / i0-r5-03 / i0-r5-04: what a scene measures counts only when the
# target's own code produced it; the runner checks the provenance before it
# grades, and the review table's containments must hold in the records.
def _records() -> dict[str, list[dict]]:
    import csv
    csv.field_size_limit(10**9)
    out = {}
    for p in sorted((HERE / "survey_results").glob("*.tsv")):
        with p.open(encoding="utf-8") as f:
            out[p.stem] = list(csv.DictReader(f, delimiter="\t"))
    return out


def _raw(row: dict):
    out = json.loads(row["output_1"])
    return out.get("raw", out) if isinstance(out, dict) else out


def test_no_recorded_result_was_refused_by_the_provenance_check():
    """Every recorded survey result passed the runner's provenance check (an
    adapter-made carrier, a foreign reader, a value the strategy kept itself,
    an incomplete list of namings would show as provenance_error)."""
    bad = [(t, r["scene_id"], r["detail_1"][:160]) for t, rows in _records().items() for r in rows
           if ("provenance_error" in r["output_1"] or "出所の検めで採点しない" in r["detail_1"])
           and "まだ届いていない入力" not in r["detail_1"]]
    assert not bad, bad
    # round r8-1: the only refusals left are settings the adapter itself recorded as decided from input not yet
    # delivered (positive definition A); each such row names the refused setting
    for t, rows in _records().items():
        for r in rows:
            if "まだ届いていない入力" in r["detail_1"] and "出所の検めで採点しない" in r["detail_1"]:
                assert r["status_1"] == "error" and r["correctness"] == "結果なし", (t, r["scene_id"])
                assert any("まだ届いていない入力" in x["decided_from"] for x in json.loads(r["settings_1"])), (t, r["scene_id"])


def test_one_carrier_carries_one_kind_across_all_scenes_of_a_target():
    """A class of the target carries ONE event kind over the whole record: the
    same base class carried as 'trade' in one scene and 'funding' in another
    is the adapter deciding the type (i0-r5-02)."""
    for target, rows in _records().items():
        by: dict[str, set] = {}
        for r in rows:
            if r["scene_id"] not in run_battery.CARRIER_SCENES or r["status_1"] != "ok":
                continue
            key, with_kinds = run_battery.CARRIER_SCENES[r["scene_id"]]
            if not with_kinds:
                continue
            raw, prov = _raw(r), json.loads(r["provenance_1"])
            if r["scene_id"] == "p5-hand-over-order":
                pairs = [(k, c) for run, cs in zip(raw["runs"], prov["carriers"])
                         for k, c in zip(run_battery._kinds(run, "order", True), cs)]
            else:
                pairs = list(zip(run_battery._kinds(raw, key, True), prov["carriers"]))
            for k, c in pairs:
                by.setdefault(run_battery._key(c), set()).add(str(k))
        many = {c: sorted(ks) for c, ks in by.items() if len(ks) > 1}
        assert not many, (target, many)


# ---------------------------------------------------------------- round r6-2
# br6-1-1 / br6-1-2: the provenance check is positive. A fake tool is written
# to a temporary directory OUTSIDE the scene set; its directory is the only
# place of the target. Every hole of round r6-1's name check is fed to the
# runner: an adapter-built dict, an adapter-written function, a tag class of
# the scene set, a string written by hand, a shared reader, a strategy-kept
# list, an adapter's own raise -- all must be refused; the same things made
# by the fake tool must pass.
_FAKE_TOOL = """
import enum, datetime


class Kind(enum.Enum):
    TRADE = 1


class Event:
    def __init__(self, kind, ts):
        self.kind, self.ts = kind, ts


def run_dicts(strategy, rows):
    for r in rows:
        d = {"price": r[0], "timestamp": r[1]}   # the tool builds the dict it hands over
        strategy.on(d)


def forward(strategy, items):
    for d in items:                               # the tool hands over what it was given
        strategy.on(d)


def call_back(strategy):
    strategy.on(pick)                             # hands over one of its own functions


def pick(xs, i):
    return xs[i]


def parse(s):
    return datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))


def history():
    return [100.0, 101.0, 102.0, 103.0]


def event(ts):
    return Event(Kind.TRADE, ts)


def emit(strategy, ts):
    strategy.on(Event(Kind.TRADE, ts))            # the tool builds its own event and hands it over


def call_each(fn, items):
    for x in items:                               # the tool calls the strategy with each item
        fn(x)
"""


@pytest.fixture()
def fake_tool(tmp_path, monkeypatch):
    pkg = tmp_path / "faketool_r62"
    pkg.mkdir()
    (pkg / "__init__.py").write_text(_FAKE_TOOL, encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    import importlib
    mod = importlib.import_module("faketool_r62")
    roots = run_battery.Roots([str(pkg.resolve())], ["go:*faketool."], [])
    yield mod, roots
    sys.modules.pop("faketool_r62", None)


def _check(sid, out, prov, roots):
    return run_battery.checked(SceneResult("ok", out, provenance=prov), _scene(sid), roots=roots)


class _Strat:
    def __init__(self):
        self.car = []

    def on(self, obj):
        import common as C
        self.car.append(C.carrier(obj))


def test_shared_type_carriers_are_placed_by_how_they_reached_the_strategy(fake_tool):
    """br6-1-1: builtins.dict / a function are the target's only when the
    target's code passed them into the strategy's call (or returned them),
    and not when the scene-set side made or handed them in."""
    import common as C
    tool, roots = fake_tool
    out = {"observed_ts_ns": [1]}
    s = _Strat()
    tool.run_dicts(s, [(100.0, 1)])  # the tool made the dict and passed it
    assert _check("p2-event-time-exact", out, {"carriers": s.car}, roots).status == "ok"
    s = _Strat()
    tool.forward(s, [{"price": 100.0, "timestamp": 1}])  # the adapter's dict, only forwarded by the tool
    got = _check("p2-event-time-exact", out, {"carriers": s.car}, roots)
    assert got.status == "error" and "場面集の側が持つ物" in got.output["provenance_error"], got.output

    def cb(e, now):  # the scene-set side builds the dict inside its own callback
        return C.carrier({"price": e, "timestamp": now})
    got = _check("p2-event-time-exact", out, {"carriers": [cb(100.0, 1)]}, roots)
    assert got.status == "error" and "共有の型" in got.output["provenance_error"], got.output
    got = _check("p5-same-stream-order", {"prices": [1.0]}, {"carriers": [C.carrier(lambda: None)]}, roots)  # an adapter lambda
    assert got.status == "error", got.output
    s = _Strat()
    tool.call_back(s)  # the tool's own function handed over
    assert _check("p5-same-stream-order", {"prices": [1.0]}, {"carriers": s.car}, roots).status == "ok"


def test_hand_written_carriers_and_names_are_refused(fake_tool):
    """A carrier / reader that common.py did not make from an object is not
    graded, whatever it says (round r6-1's `_row_carrier` strings)."""
    import common as C
    tool, roots = fake_tool
    for c in ("faketool_r62.Event", {"type": "faketool_r62.Event", "type_file": str(roots.dirs[0]) + "/__init__.py"}):
        got = _check("p3-trade", {"sequence": [["trade", 1]]}, {"carriers": [c]}, roots)
        assert got.status == "error" and "手で書いた" in got.output["provenance_error"], (c, got.output)
    s = _Strat()
    tool.emit(s, 1)  # round r6-3: an object of the tool's class counts only once the tool delivered it
    assert _check("p3-trade", {"sequence": [["trade", 1]]}, {"carriers": s.car}, roots).status == "ok"
    assert _check("p3-trade", {"sequence": [["trade", 1]]}, {"carriers": [C.compiled("go:*faketool.Trade")]}, roots).status == "ok"
    got = _check("p3-trade", {"sequence": [["trade", 1]]}, {"carriers": [C.compiled("go:*othertool.Trade")]}, roots)
    assert got.status == "error", got.output


def test_a_tag_is_checked_as_well_as_the_object(fake_tool):
    """br6-1-2: the tag of `carrier_tag` / `carrier_const` is placed on its own."""
    import enum

    import common as C
    tool, roots = fake_tool

    class MyKind(enum.Enum):  # a tag class of the scene-set side
        TRADE = 1
    got_ev = []
    tool.call_each(lambda _: got_ev.append(C.read(tool.event, 1)), [0])  # read inside a strategy call the tool made
    ev = got_ev[0]  # round r6-3: returned by the tool's function (returned_by), so delivered
    assert _check("p3-trade", {"sequence": [["trade", 1]]}, {"carriers": [C.carrier_tag(ev, tool.Kind.TRADE)]}, roots).status == "ok"
    after = C.read(tool.event, 2)  # round r8-1 (positive definition A (3)): a read made outside any strategy call
    got = _check("p3-trade", {"sequence": [["trade", 1]]}, {"carriers": [C.carrier_tag(after, tool.Kind.TRADE)]}, roots)
    assert got.status == "error" and "戦略の呼び出しの中の読みに限る" in got.output["provenance_error"], got.output
    got = _check("p3-trade", {"sequence": [["trade", 1]]}, {"carriers": [C.carrier_tag(ev, MyKind.TRADE)]}, roots)
    assert got.status == "error" and "札" in got.output["provenance_error"], got.output
    import types
    here = types.ModuleType("scene_side_consts")
    here.__file__ = str(HERE / "scene_side_consts.py")
    here.TRADE = 2
    got = _check("p3-trade", {"sequence": [["trade", 1]]}, {"carriers": [C.carrier_const(ev, here, "TRADE", 2)]}, roots)
    assert got.status == "error" and "札" in got.output["provenance_error"], got.output
    with pytest.raises(ValueError):
        C.carrier_const(ev, tool, "history", 2)  # the named constant must carry the value


def test_readers_reads_and_attempts_must_run_the_targets_code(fake_tool):
    """The same positive check for p2-iso's reader, p4-visible-at-step's reads
    and p4-future-read-attempt's attempts."""
    import datetime

    import common as C
    tool, roots = fake_tool
    iso = 1704067200123456789
    assert _check("p2-iso-utc", iso, {"reader": C.qualname(tool.parse)}, roots).status == "ok"
    for reader in (C.qualname(datetime.datetime.fromisoformat), "faketool_r62.parse", C.qualname(_check)):
        assert _check("p2-iso-utc", iso, {"reader": reader}, roots).status == "error", reader
    out = {"visible_count": 4, "max_visible_close": 103.0}
    r = C.Reads()
    tool.call_each(lambda _: r.read("tool.history()", tool.history), [0])  # inside a strategy call the tool made
    assert _check("p4-visible-at-step", out, r.provenance(), roots).status == "ok"
    r = C.Reads()
    r.read("tool.history()", tool.history)  # round r8-1 (positive definition A (3)): outside any strategy call
    got = _check("p4-visible-at-step", out, r.provenance(), roots)
    assert got.status == "error" and "戦略の呼び出しの中で行った物と示せない" in got.output["provenance_error"], got.output
    r = C.Reads()
    with C.user_loop_call():  # a target the user drives with his own loop: the loop body is the strategy call
        r.read("tool.history()", tool.history)
    assert _check("p4-visible-at-step", out, r.provenance(), roots).status == "ok"
    kept = [100.0, 101.0, 102.0, 103.0]
    r = C.Reads()
    with C.user_loop_call():
        r.read("a list the strategy kept", lambda: list(kept))
    got = _check("p4-visible-at-step", out, r.provenance(), roots)
    assert got.status == "error" and "1 行も走らず" in got.output["provenance_error"], got.output
    by_hand = {"reads": [{"means": "tool.history()", "returned": [100.0, 101.0, 102.0, 103.0], "touched": [roots.dirs[0] + "/__init__.py"]}]}
    got = _check("p4-visible-at-step", out, by_hand, roots)
    assert got.status == "error" and "手で書いた" in got.output["provenance_error"], got.output
    r = C.Reads()
    with C.user_loop_call():
        r.read("tool.history()", tool.history)
    assert _check("p4-visible-at-step", {"visible_count": 5, "max_visible_close": 104.0}, r.provenance(), roots).status == "error"

    def attempts(fn):
        att = C.Attempts()
        with C.user_loop_call():  # round r8-1: the attempts are made inside a strategy call
            C.try_position_namings(att, "seq", fn, 4)
        return att.output()
    stopped = attempts(lambda: C.KeyCall(lambda k: tool.pick([100.0, 101.0, 102.0, 103.0], k)))
    assert _check("p4-future-read-attempt", stopped, None, roots).status == "ok"
    own = attempts(lambda: [100.0, 101.0, 102.0, 103.0])  # the strategy's own list: no tool code runs
    got = _check("p4-future-read-attempt", own, None, roots)
    assert got.status == "error" and "1 行も走らず" in got.output["provenance_error"], got.output

    def raiser(k):
        tool.history()
        raise IndexError("the adapter stops itself")
    self_stopped = attempts(lambda: C.KeyCall(raiser))
    got = _check("p4-future-read-attempt", self_stopped, None, roots)
    assert got.status == "error" and "raise 文" in got.output["provenance_error"], got.output


def test_p4_attempts_must_cover_the_fixed_namings_and_only_compiled_means_may_skip_one(fake_tool):
    """i0-r5-03: a means is graded only with the whole fixed list of namings
    of its shape; `expressible: False` is allowed only for a compiled driver."""
    tool, roots = fake_tool
    sc = _scene("p4-future-read-attempt")
    f = roots.dirs[0] + "/__init__.py"

    def res(atts):
        return run_battery.checked(SceneResult("ok", {"attempts": atts}), sc, roots=roots)

    import common as C

    def made(d):  # an attempt record as common.Attempts makes it (the provenance itself is tested above)
        return C._register(C.Record(d))
    whole = [made({"means": "seq", "form": "position", "shape": "position", "naming": n, "raised": "IndexError", "returned": None,
                   "touched": [f]}) for n in scenes.POSITION_NAMINGS]
    assert res(whole).status == "ok"
    assert res(whole[:1]).status == "error"  # only [n]: the open slices were not tried
    skipped = [made(dict(a, expressible=False)) if a["naming"] == "[n::2]" else a for a in whole]
    assert res(skipped).status == "error"  # a Python means cannot declare a naming unwritable
    compiled = [made(dict(a, means="go:" + a["means"])) for a in skipped]
    assert res(compiled).status == "ok"
    untouched = [made(dict(a, touched=[])) for a in whole]
    assert res(untouched).status == "error"  # nothing of the target ran
    assert res([dict(a) for a in whole]).status == "error"  # records not made by common.Attempts


def test_every_target_has_its_distribution_in_the_runner():
    """The places of each target are the runner's table, not the adapter's."""
    names = {"new_impl", "mutant", *run_battery.OPPONENTS}
    assert names <= set(run_battery.TARGET_DISTS), sorted(names - set(run_battery.TARGET_DISTS))
    for t, spec in run_battery.TARGET_DISTS.items():
        assert spec.get("py") or spec.get("compiled"), t
        assert all(h.startswith(run_battery.COMPILED) for h in spec.get("compiled", [])), t


def test_the_scene_set_is_never_a_place_of_a_target():
    """A target whose table entry resolves into the scene set is refused."""
    run_battery._ROOTS.pop("__probe__", None)
    run_battery.TARGET_DISTS["__probe__"] = {"py": ["run_battery"]}
    try:
        with pytest.raises(SystemExit):
            run_battery.roots_of("__probe__")
    finally:
        run_battery.TARGET_DISTS.pop("__probe__", None)
        run_battery._ROOTS.pop("__probe__", None)


def test_generated_code_files_are_declared_as_the_scene_sets():
    """An adapter that writes a Python file for a tool to load (a strategy
    module) declares it with common.scene_set_file, so frames of that code are
    not taken for the tool's."""
    import re
    for p in sorted((HERE / "opponents").glob("*.py")):
        src = p.read_text(encoding="utf-8")
        if re.search(r"\.py[\"']\)\.write_text|\.py[\"']\)\s*,\s*[\"']w", src):
            assert "C.scene_set_file(" in src, p.name


def test_no_adapter_composes_a_carrier_string():
    """Carriers are made by common.py from objects: no adapter adds to or
    formats a carrier (round r6-1's `C.carrier(hbt) + ".wait_next_feed"`,
    `f"hftbacktest.{name}"`)."""
    import re
    for p in sorted([*(HERE / "opponents").glob("*.py"), *(HERE / "adapters").glob("*.py")]):
        if p.name == "common.py":
            continue
        src = p.read_text(encoding="utf-8")
        assert not re.search(r"C\.carrier(?:_tag)?\([^)]*\)\s*\+", src), p.name
        assert not re.search(r"carrier\(lambda", src), p.name


def test_every_python_adapter_names_the_future_through_the_common_helpers():
    """The namings a Python adapter tries are not its own choice: a p4 attempt
    with form time / position goes through common.try_position_namings /
    try_time_namings, or is a written call of shape no_means, or the one
    naming of shape next_call (a call that returns the next item)."""
    import re
    for p in sorted([*(HERE / "opponents").glob("*.py"), *(HERE / "adapters").glob("*.py")]):
        if p.name == "common.py":  # the helpers themselves
            continue
        src = p.read_text(encoding="utf-8")
        for m in re.finditer(r"att\.run(?:_async)?\((.{0,400}?)\)\s*$", src, flags=re.M | re.S):
            call = m.group(1)
            if re.search(r"[\"'](time|position)[\"']", call.split(",")[1] if "," in call else ""):
                assert re.search(r"shape=[\"'](no_means|next_call)[\"']", call), (p.name, call[:160])


def _cand_targets() -> dict[int, str]:
    """Candidate number -> recorded target: run candidates (ledger) and, round
    r6-3, reproductions (the review table's 再現した rows)."""
    import survey_counts
    out = {int(r["cand"]): r["target"] for r in _ledger() if r["result"] == "走った"}
    out.update({n: t for t, n in survey_counts.repro_numbers().items()})
    return out


def _containing_segments():
    """(row, ability number, text after 含む:) for every 在る ability of a 上位互換 row."""
    import re
    text = (HERE / "opponents" / "CONSIDERED.md").read_text(encoding="utf-8")
    for sec in re.split(r"^### 観点 ", text, flags=re.M)[1:]:
        for row in _table_rows(sec):
            if not row["判断"].startswith("スキップ"):
                continue
            parts = re.split(r"能 (\d+): (在る|無い)", row["理由"])
            for k in range(1, len(parts) - 1, 3):
                if parts[k + 1] == "在る" and "含む:" in parts[k + 2]:
                    yield sec[:4], row["候補"], int(parts[k]), parts[k + 2].split("含む:", 1)[1]


def test_every_scene_a_containment_cites_as_correct_is_correct_in_the_records():
    """i0-r5-04: a 上位互換 row's evidence is checked against the records, not
    believed: each scene the containing text cites as 正解と一致 is 正解と一致
    in the survey result of a run candidate the same text names, and a cited
    probe log exists."""
    import re
    recs = {t: {r["scene_id"]: r for r in rows} for t, rows in _records().items()}
    targets = _cand_targets()
    checked = 0
    for vp, cand, n, seg in _containing_segments():
        named = [targets[int(c)] for c in re.findall(r"(?:^|[\s(、。/])(\d+) [A-Za-z]", seg) if int(c) in targets]
        assert named, (vp, cand, n, seg[:120])
        # round r8-1: a candidate's records are those of every configured target of it (<target>[@<label>])
        named_files = [t for t in recs if t.partition("@")[0] in named]
        for group in re.findall(r"((?:p\d-[\w-]+(?:(?:の[^・、。 ]{1,8})?・)?)+) ?が正解と一致", seg):
            for sid in re.findall(r"p\d-[\w-]+", group):
                checked += 1
                ok_ = [t for t in named_files if recs.get(t, {}).get(sid, {}).get("correctness") == "正解と一致"]
                assert ok_, f"{vp} {cand} 能 {n}: {sid} is cited as 正解と一致 but none of {named} has it in survey_results"
        for log in re.findall(r"survey_results/attempts/[\w.-]+", seg):
            assert (HERE / log).exists(), (vp, cand, n, log)
    assert checked > 0


def test_no_containment_rests_on_what_a_user_could_add():
    """i0-r5-04: the containing side is a mechanism the run candidate itself
    has; a base class users can subclass, 'no limit on types', 'can be written
    in the handler' contain every ability of every candidate without reading it.
    P0-7 is left out on purpose: its abilities ARE the places a user's own
    implementation is handed in (the table's reading section, 「P0-7 の口」), so
    a class the user writes against a published socket is the mechanism itself."""
    for vp, cand, n, seg in _containing_segments():
        if vp == "P0-7":
            continue
        for w in ("の子", "上限が無い", "上限の無い", "で書ける", "で運べる", "書き足せ"):
            assert w not in seg, (vp, cand, n, w, seg[:160])


# ---------------------------------------------------------------- round r6-3
# br6-2-1: an object of the target's own class counts as the target's delivery
# only when the target's code (Python or compiled) passed it -- or an object
# holding it -- into the strategy's call, or a target function returned it. The
# type alone says only that the target HAS the class.
class _OwnStrat:
    """A strategy of the scene-set side (this file is inside the scene set)."""

    def __init__(self, tool=None):
        self.car, self.tool, self.kept = [], tool, None

    def on(self, obj):
        import common as C
        self.car.append(C.carrier(obj))

    def on_build(self, ts):  # the scene-set side builds the tool's class inside the call
        import common as C
        self.car.append(C.carrier(self.tool.Event(self.tool.Kind.TRADE, ts)))

    def on_kept(self, _obj):  # records what the adapter hung on the strategy, not what it received
        import common as C
        self.car.append(C.carrier(self.kept))

    def on_box(self, box):  # the event arrives inside another object the tool hands over
        import common as C
        self.car.append(C.carrier(box["event"]))


def test_own_class_carriers_must_have_been_delivered_by_the_target(fake_tool):
    import common as C
    tool, roots = fake_tool
    out = {"sequence": [["trade", 1]]}

    def grade(car):
        return _check("p3-trade", out, {"carriers": car}, roots)

    s = _OwnStrat(tool)
    tool.emit(s, 1)  # the tool built its own event and passed it
    assert grade(s.car).status == "ok"
    s = _OwnStrat(tool)
    tool.call_each(s.on_build, [1])  # the tool calls the strategy, but the strategy builds the tool's class itself
    got = grade(s.car)
    assert got.status == "error" and "届けたことを示せない" in got.output["provenance_error"], got.output
    held = tool.Event(tool.Kind.TRADE, 1)  # the adapter's object of the tool's class, never handed over
    got = grade([C.carrier(held)])
    assert got.status == "error" and "届けたことを示せない" in got.output["provenance_error"], got.output
    s = _OwnStrat(tool)
    s.kept = tool.Event(tool.Kind.TRADE, 1)  # hung on the strategy by the adapter; the tool passes something else
    tool.call_each(s.on_kept, [0])
    got = grade(s.car)
    assert got.status == "error" and "届けたことを示せない" in got.output["provenance_error"], got.output
    s = _OwnStrat(tool)
    tool.call_each(s.on_box, [{"event": tool.Event(tool.Kind.TRADE, 1)}])  # inside an argument the tool passed
    assert grade(s.car).status == "ok"
    s = _OwnStrat(tool)
    tool.forward(s, [tool.Event(tool.Kind.TRADE, 1)])  # input the adapter built in the tool's class, delivered by the tool
    assert grade(s.car).status == "ok"
    rec = run_battery.compact({"carriers": s.car}, roots)["carriers"][0]
    assert rec.get("input") and rec.get("held_by"), rec  # the record says it was the adapter's input
    got_ev = []
    tool.call_each(lambda _: got_ev.append(C.read(tool.event, 1)), [0])  # returned by the tool's function, in a call
    assert grade([C.carrier(got_ev[0])]).status == "ok"
    got = grade([C.carrier(C.read(tool.event, 2))])  # round r8-1: the same read after the run
    assert got.status == "error" and "届けたことを示せない" in got.output["provenance_error"], got.output


def test_a_strategy_called_from_compiled_code_shows_the_compiled_caller():
    """34 QuantCore's shape: compiled code calls the strategy, so no Python frame
    of the target is on the stack. `contextvars.Context.run` is a compiled
    function (lib-dynload/_contextvars) that calls a Python callable with an
    argument; a Context object is its own module's class."""
    import contextvars
    import os

    import _contextvars

    import common as C
    so = os.path.realpath(_contextvars.__file__)
    roots = run_battery.Roots([so], [], [])
    out = {"sequence": [["trade", 1]]}
    ctx = contextvars.Context()
    s = _OwnStrat()
    with C.native_tracker():
        ctx.run(s.on, ctx)
    assert s.car[0]["native_by"] == [so], s.car[0]
    assert _check("p3-trade", out, {"carriers": s.car}, roots).status == "ok"
    s = _OwnStrat()
    ctx2 = contextvars.Context()
    ctx2.run(s.on, ctx2)  # without the tracker the compiled caller is not seen: not graded
    assert _check("p3-trade", out, {"carriers": s.car}, roots).status == "error"

    class Build(_OwnStrat):
        def on(self, _obj):
            import common as C
            self.car.append(C.carrier(contextvars.Context()))  # built inside the call by the scene set
    s = Build()
    with C.native_tracker():
        contextvars.Context().run(s.on, 0)
    assert _check("p3-trade", out, {"carriers": s.car}, roots).status == "error"


def test_every_recorded_carrier_shows_how_the_target_delivered_it():
    """br6-2-1 on the records: every carrier, `of` and `via` of every recorded
    target carries a delivery fact the runner accepted (or is the target's code
    as a means); the facts the check does not read are not in the records."""
    checked = 0
    for target, rows in _records().items():
        for r in rows:
            prov = json.loads(r["provenance_1"])
            recs = []

            def walk(x, path=""):
                if isinstance(x, dict):
                    if "type_file" in x and "type" in x and not path.endswith("/tag"):
                        recs.append((path, x))
                    for k, v in x.items():
                        walk(v, path + "/" + k)
                elif isinstance(x, list):
                    for v in x:
                        walk(v, path)
            walk(prov)
            for path, rec in recs:
                assert "in_args" not in rec and "called_by" not in rec, (target, r["scene_id"], path)
                if r["status_1"] != "ok":
                    continue
                checked += 1
                shown = any(rec.get(k) for k in ("passed_by", "reached_by", "native_by", "returned_by"))
                assert shown or (path.endswith(("/via", "/of")) and rec.get("code_file")), (target, r["scene_id"], path, rec)
    assert checked > 0


def test_quantcore_is_placed_by_its_compiled_caller():
    rows = _records().get("opp_quantcore", [])
    natives = {tuple(c.get("native_by") or ()) for r in rows if r["status_1"] == "ok"
               for c in (json.loads(r["provenance_1"]) or {}).get("carriers", []) if isinstance(c, dict)}
    assert natives and all(n and n[0].endswith(".so") and "/quantcore/" in n[0] for n in natives), natives


def _best_by_scene() -> dict[str, str]:
    """Scene -> best correctness over every recorded survey target (run
    candidates and reproductions), by the order of rule 5."""
    order = {"正解と一致": 0, "対応なし": 1, "不一致": 2, "結果なし": 3}
    best: dict[str, str] = {}
    for t, rows in _records().items():
        if not t.startswith(("opp_", "repro_")):
            continue
        for r in rows:
            c = r["correctness"]
            if r["scene_id"] not in best or order[c] < order[best[r["scene_id"]]]:
                best[r["scene_id"]] = c
    return best


def test_every_skip_names_what_it_lacks_for_each_scene_the_survey_side_misses():
    """br6-2-2: a skip is allowed only for a candidate that is clearly weaker,
    and the survey side's strength is the best result per scene. For each
    scene of the row's viewpoint whose best is not 正解と一致, a skip row names
    the type or ability the candidate lacks for it, with the line it read;
    otherwise the candidate could raise that best and must be reproduced."""
    import re
    best = _best_by_scene()
    assert set(best) == {sc.id for sc in scenes.SCENES}
    text = (HERE / "opponents" / "CONSIDERED.md").read_text(encoding="utf-8")
    checked = 0
    for sec in re.split(r"^### 観点 ", text, flags=re.M)[1:]:
        vp = sec[:4]
        missed = [sc.id for sc in scenes.SCENES if sc.viewpoint == vp and best[sc.id] != "正解と一致"]
        for row in _table_rows(sec):
            if not row["判断"].startswith("スキップ"):
                continue
            for sid in missed:
                m = re.search(rf"最良が正解と一致でない場面 {re.escape(sid)}: (.*?)(?= / |$)", row["理由"])
                assert m and "無い" in m.group(1) and ("行" in m.group(1) or "http" in m.group(1)), (vp, row["候補"], sid)
                checked += 1
    assert checked > 0


def test_the_reproduction_is_run_for_every_configured_target_and_placed_in_its_engine():
    """Round r8-1 (i0-r7-03): the reproduction of 52 LEAN is run once per configured target (the resolutions its
    Initialize passes to AddCryptoFuture), each with its own record; its engine is the target's only place."""
    recs = _records()
    for t in run_battery.configured_targets("repro_lean52"):
        assert t in recs, t
        choose = {r["choose"] for r in recs[t]}
        assert len(choose) == 1, t  # one set of chosen values for every scene of a configured target
    assert _best_by_scene()["p1-merge-by-time"] == "正解と一致"
    roots = run_battery.roots_of("repro_lean52@tick")
    assert [Path(d).name for d in roots.dirs] == ["lean52.py"] and "repro_engines" in roots.dirs[0]
    import common as C
    assert C.in_scene_set(str(HERE / "opponents" / "repro_lean52.py"))
    assert not C.in_scene_set(roots.dirs[0])


# ---------------------------------------------------------------- round r7-1
# i0-r6-02: a scene of another viewpoint than P0-3 must not have its result
# decided by which event types a target has (that is what P0-3 measures).
# i0-r6-04: the reproduction rewrites every condition of the source that
# encloses a rewritten statement (IsInternalFeed, the subscription sort).
TYPED = set(scenes.L438_2_SCENES)


def _kinds_in(inp) -> set:
    evs = list(inp.get("events") or []) + [e for evs in (inp.get("streams") or {}).values() for e in evs]
    return {e["kind"] for e in evs if "kind" in e}


def test_no_scene_outside_p0_3_fixes_its_event_types():
    """Every scene of P0-1, P0-2, P0-4 .. P0-7 is one of: (A) its types come
    from the target's own (type_plan, built by the runner); (B) the target
    picks one of its own types and no type name is graded; (C) any_type:
    trades that may be bars; (D) bars that may be trades."""
    kind_names = set(scenes.TYPE_ORDER)
    for sc in scenes.SCENES:
        if sc.viewpoint == "P0-3":
            continue
        kinds = _kinds_in(sc.input)
        exp = json.dumps(sc.expected, ensure_ascii=False)
        if sc.type_plan is not None:
            assert sc.id in TYPED and "type_rule" in sc.input, sc.id
        elif not kinds or "型は対象が受ける型" in json.dumps(sc.input, ensure_ascii=False):
            assert not any(f'"{k}"' in exp for k in kind_names), (sc.id, "the target picks the type, so no type may be graded")
        elif sc.input.get("any_type"):
            assert kinds == {"trade"}, sc.id
        else:
            assert kinds == {"bar"} and "約定で代えてよい" in sc.input.get("note", ""), sc.id
    assert {sc.id for sc in scenes.SCENES if sc.type_plan} == TYPED


def test_typed_scenes_are_built_by_their_rule_for_any_set_of_types():
    base = {sc.id: sc for sc in scenes.SCENES if sc.type_plan}
    for sid, sc in base.items():
        full = scenes.for_target_types(sc, scenes.TYPE_ORDER)
        assert (full.input, full.expected) == (sc.input, sc.expected), sid  # the listed scene = all six types
        assert scenes.for_target_types(sc, ["bar"]) is None, sid           # every typed scene needs two types
        assert scenes.for_target_types(sc, []) is None, sid
    two = scenes.for_target_types(base["p1-merge-by-time"], ["bar", "trade"])
    assert two.input["types"] == {"A": "trade", "B": "bar", "C": "trade"}  # TYPE_ORDER, cycled over A, B, C
    evs = [e for s in two.input["streams"].values() for e in s]
    assert two.expected["sequence"] == [[e["kind"], e["ts_ns"]] for e in sorted(evs, key=lambda e: e["ts_ns"])]
    assert [e["ts_ns"] for e in two.input["streams"]["A"]] == [scenes.T0 + 2 * scenes.DAY, scenes.T0 + 5 * scenes.DAY]
    for e in evs:
        assert {k: v for k, v in e.items() if k != "ts_ns"} == {k: v for k, v in scenes.SAMPLES[e["kind"]].items() if k != "ts_ns"}
    three = scenes.for_target_types(base["p5-hand-over-order"], ["funding", "bar", "trade"])
    assert three.input["types"] == {"A": "trade", "B": "bar", "C": "funding"}
    assert len(three.input["hand_over_orders"]) == 6 and len({tuple(o) for o in three.input["hand_over_orders"]}) == 6
    twice = scenes.for_target_types(base["p5-same-time-twice"], ["book_delta", "trade"])
    assert twice.expected["delivered_as_multiset"] == sorted([["book_delta", scenes.T0 + scenes.DAY], ["trade", scenes.T0 + scenes.DAY]])
    typed = scenes.for_target_types(base["p1-typed-events"], ["liquidation", "book_snapshot", "bar"])
    assert typed.expected == {"sequence": [["book_snapshot", scenes.T0 + scenes.DAY], ["bar", scenes.T0 + 2 * scenes.DAY]]}


def test_the_runner_takes_the_types_from_the_p3_grades_and_never_asks_the_adapter():
    """Round r8-1 (positive definition A, L-438 (2)): a type of the configured target is one whose p3-<type>
    scene of the same run was graded 正解と一致; 不一致, 対応なし and 結果なし are not had."""
    grades = {"p3-trade": "正解と一致", "p3-bar": "正解と一致", "p3-book_snapshot": "不一致",
              "p3-book_delta": "対応なし", "p3-funding": "結果なし"}  # p3-liquidation: no grade at all
    assert run_battery.target_types(grades) == ["trade", "bar"]

    class Never:
        def run_scene(self, sc):
            raise AssertionError("the adapter must not be asked when the target has too few types")

    sc = _scene("p5-same-time-twice")
    _, res, settings = run_battery.run_for_types(Never(), sc, {"p3-bar": "正解と一致", "p3-trade": "不一致"})
    assert res.status == "not_supported" and "最低 2 種" in res.detail and "p3-trade: 不一致" in res.detail and settings == []

    seen = []

    class Rec:
        def run_scene(self, s):
            seen.append(s)
            return SceneResult("not_supported", detail="rec")

    conc, res, _ = run_battery.run_for_types(Rec(), sc, grades)
    assert seen and seen[0].input["types"] == {"A": "trade", "B": "bar"} and conc is seen[0]
    assert res.detail.startswith("型の選び方(runner")


def test_every_record_of_a_typed_scene_used_the_types_of_its_own_p3_grades():
    """The survey records were made by the runner of this round: the typed scenes' types are the ones the same
    record's p3 rows were graded 正解と一致 for, and the chosen type combination is in `types_1`."""
    for target, rows in _records().items():
        by = {r["scene_id"]: r for r in rows}
        types = run_battery.target_types({f"p3-{k}": by[f"p3-{k}"]["correctness"] for k in scenes.TYPE_ORDER})
        for sid in scenes.L438_2_SCENES:
            assert by[sid]["detail_1"].startswith(f"型の選び方(runner、第 r8-1 回): 設定つき対象の持つ型 {types}"), (target, sid)
            built = scenes.for_target_types(_scene(sid), types)
            assert json.loads(by[sid]["types_1"]) == (built.input["types"] if built else None), (target, sid)


def test_every_target_with_a_type_has_a_trade_or_a_bar():
    """The any_type scenes and the two P0-4 bar scenes let a target use a trade
    or a bar; every recorded target that delivers any market type in its p3 scenes delivers one of them."""
    for target, rows in _records().items():
        by = {r["scene_id"]: r for r in rows}
        delivered = [k for k in scenes.TYPE_ORDER if by[f"p3-{k}"]["status_1"] == "ok"]
        assert not delivered or {"trade", "bar"} & set(delivered), (target, delivered)


def test_one_call_per_event_grades_the_times_of_the_calls_not_the_type():
    sc = _scene("p1-one-call-per-event")
    ts = [e["ts_ns"] for e in sc.input["events"]]
    grade = lambda out: run_battery.correctness(SceneResult("ok", out), sc.expected, sc)  # noqa: E731
    assert grade({"sequence": [["data", t] for t in ts]}) == "正解と一致"
    assert grade({"sequence": [["bar", t] for t in ts[:4]]}) == "不一致"          # a call missing
    assert grade({"sequence": [["bar", t] for t in ts + ts[-1:]]}) == "不一致"    # a call too many
    assert grade({"sequence": [["bar", t + 1] for t in ts]}) == "不一致"          # the time moved


def test_no_stale_best_claim_in_the_review_table():
    """A 'best is not 正解と一致' claim in the review table names only scenes
    whose best over the records is still not 正解と一致."""
    import re
    best = _best_by_scene()
    text = (HERE / "opponents" / "CONSIDERED.md").read_text(encoding="utf-8")
    for sid in re.findall(r"最良が正解と一致でない場面 (p\d-[a-z_\-]+)", text):
        assert best[sid] != "正解と一致", sid


def test_lean_reproduction_keeps_internal_feeds_out_of_the_slice():
    from opponents.repro_engines import lean52 as L
    got = []

    class A(L.QCAlgorithm):
        def OnData(self, s):  # noqa: N802
            got.append([(type(d).__name__, d.EndTime) for d in s.AllData] + [("rates", sorted(s.MarginInterestRates)),
                                                                           ("ticks", sorted(s.Ticks))])

    t = 10 * L.TICKS_PER_SECOND
    tick = L.Tick(t, "X", "", "", 1.0, 100.0)
    rate = L.MarginInterestRate()
    rate.Time, rate.Symbol, rate.InterestRate = t, "X", 0.1
    dm = L.DataManager()
    internal = dm.Add("X", L.SecurityType.CryptoFuture, L.Resolution.Tick, False, is_internal_feed=True,
                      subscription_data_types=[(L.Tick, L.TickType.Trade), (L.MarginInterestRate, L.TickType.Quote)])
    for s_ in L.sync([L.Subscription([tick], internal[0]), L.Subscription([rate], internal[1])], 0):
        if s_.HasData:
            A().OnData(s_)
    assert got == []  # TimeSliceFactory.cs 181 / 194 / 329: nothing of an internal feed reaches OnData (HasData false, 389)
    user = L.DataManager().Add("X", L.SecurityType.CryptoFuture, L.Resolution.Tick, False)
    assert [c.IsInternalFeed for c in user] == [False, False, False]  # DataManager.cs 720-721 with AddSecurity's defaults
    oi = L.DataManager().Add("X", L.SecurityType.CryptoFuture, L.Resolution.Tick, False,
                             subscription_data_types=[(L.Tick, "OpenInterest")])
    assert oi[0].IsInternalFeed is False  # 720: internal by OpenInterest only when the data types were NOT given
    by_type = {(c.Type, c.TickType): c for c in user}
    for s_ in L.sync([L.Subscription([tick], by_type[(L.Tick, L.TickType.Trade)]),
                      L.Subscription([rate], by_type[(L.MarginInterestRate, L.TickType.Quote)])], 0):
        if s_.HasData:
            A().OnData(s_)
    assert got == [[("Tick", t), ("MarginInterestRate", t), ("rates", ["X"]), ("ticks", ["X"])]]


def test_lean_reproduction_sorts_the_subscriptions_by_their_key():
    """SubscriptionCollection.cs 213-227: SecurityType, then TickType (Trade <
    Quote), then Symbol; the same key keeps the order handed over."""
    from opponents.repro_engines import lean52 as L
    t = 10 * L.TICKS_PER_SECOND

    def sub(kind, sym):
        cfgs = {(c.Type, c.TickType): c for c in L.DataManager().Add(sym, L.SecurityType.CryptoFuture, L.Resolution.Tick, False)}
        if kind == "rate":
            d = L.MarginInterestRate()
            d.Time, d.Symbol = t, sym
            return L.Subscription([d], cfgs[(L.MarginInterestRate, L.TickType.Quote)])
        return L.Subscription([L.Tick(t, sym, "", "", 1.0, 1.0)], cfgs[(L.Tick, L.TickType.Trade)])

    subs = [sub("rate", "A"), sub("tick", "B"), sub("tick", "A")]
    assert [(s.Configuration.TickType, s.Configuration.Symbol) for s in L.sort_subscriptions(subs)] == \
        [(L.TickType.Trade, "A"), (L.TickType.Trade, "B"), (L.TickType.Quote, "A")]


# ---------------------------------------------------------------- round r8-1
# i0-r7-03 / positive definition A: settings, configured targets, the types of a configured target.
# i0-r7-05 / positive definition C: the table of every viewpoint's cells.
# L-438 (2) / LEAD_DESIGN.md section 7.2 item 10: the four scenes named by id.

def test_l438_2_names_four_scenes_by_id_and_only_they_take_types_from_the_target():
    assert scenes.L438_2_SCENES == ("p1-merge-by-time", "p1-typed-events", "p5-same-time-twice", "p5-hand-over-order")
    assert {s.id for s in scenes.SCENES if s.type_plan is not None} == set(scenes.L438_2_SCENES)
    assert all(_scene(sid).viewpoint in ("P0-1", "P0-5") for sid in scenes.L438_2_SCENES)
    text = (HERE / "DEFINITIONS.md").read_text(encoding="utf-8")
    assert "・".join(scenes.L438_2_SCENES) in text


def _setting_rec(fn=None, **kw):
    import common as C
    C.settings_begin()
    kw.setdefault("what", "x")
    C.configure(fn or run_battery.split_target, "a@b", **kw)
    return C.settings_taken()


def test_a_setting_counts_only_when_made_through_the_targets_code_from_knowable_values():
    import common as C
    roots_target = run_battery.Roots([str(HERE / "run_battery.py")], [], [])  # a stand-in place of a target
    good = _setting_rec(decided_from=("選ぶ値",))
    assert run_battery.settings_problem(good, roots_target) is None
    assert "対象の配布物に無い" in run_battery.settings_problem(good, run_battery.Roots(["/nonexistent"], [], []))
    unseen = _setting_rec(decided_from=("場面の入力", "まだ届いていない入力"))
    assert "まだ届いていない入力" in run_battery.settings_problem(unseen, roots_target)
    forged = [C.Record({"fn": "run_battery.split_target", "fn_file": str(HERE / "run_battery.py"), "when": "開始前",
                        "decided_from": ["選ぶ値"]})]  # a record not made by common.configure
    assert "手で書いた値" in run_battery.settings_problem(forged, roots_target)
    with pytest.raises(ValueError):
        _setting_rec(decided_from=("思いついた値",))
    with pytest.raises(ValueError):
        _setting_rec(when="いつか")
    # an ok result made under a refused setting is not graded
    res = run_battery.checked(SceneResult("ok", {"x": 1}), _scene("p6-place-then-cancel"), roots=roots_target, settings=unseen)
    assert res.status == "error" and "まだ届いていない入力" in res.detail


def test_every_ok_survey_row_records_the_settings_of_its_run():
    """Round r8-1: each survey row the runner graded from an engine's run carries the settings of that run
    (`settings_1`, made by common.configure*). The scenes whose value is a time a reader made (the ISO scenes and,
    round r16-1, the unit scenes: run_battery.READER_SCENES) may make no setting; a setting they make is checked."""
    for t, rows in _records().items():
        for r in rows:
            if r["status_1"] != "ok":
                continue
            if r["scene_id"] in run_battery.READER_SCENES and json.loads(r["settings_1"]) == []:
                continue
            st = json.loads(r["settings_1"])
            assert isinstance(st, list) and st, (t, r["scene_id"])
            for x in st:
                assert x["when"] in ("開始前", "戦略の呼び出しの中") or x["when"].startswith("その他: "), (t, x)
                assert x["decided_from"] and set(x["decided_from"]) <= {"場面の入力", "選ぶ値", "公開の既定", "戦略が受けた物"}, (t, x)


def test_a_configured_target_runs_every_scene_with_one_set_of_chosen_values():
    for t, rows in _records().items():
        assert len({r["choose"] for r in rows}) == 1, t
        assert all(r["target"] == t for r in rows), t


def test_the_configured_targets_listed_are_the_adapters_configs():
    import ast
    for base in ["new_impl", *run_battery.OPPONENTS, *run_battery._repro_targets()]:
        ts = run_battery.configured_targets(base)
        assert ts and len(ts) == len(set(ts)), base
        assert all(run_battery.split_target(t)[0] == base for t in ts), base
    # Basana's chosen priority is the one its stated same-time rule is written for
    tree = ast.parse((HERE / "opponents" / "basana_adapter.py").read_text(encoding="utf-8"))
    cfg = next(ast.literal_eval(st.value) for n in ast.walk(tree) if isinstance(n, ast.ClassDef) and n.name == "BasanaAdapter"
               for st in n.body if isinstance(st, ast.Assign) and any(getattr(x, "id", "") == "CONFIGS" for x in st.targets))
    import stated_rules
    assert cfg[""]["priority"] == stated_rules.TYPE_PRIORITY


def test_lean_subscriptions_come_from_the_resolution_through_the_public_entry():
    """i0-r7-03: the reproduction's subscriptions are what LEAN's own lookup makes of the resolution the
    algorithm passes to AddCryptoFuture (LeanData.GetDataType); the scene set never builds a config itself."""
    from opponents.repro_engines import lean52 as L
    want = {"Tick": {("Tick", "Trade"), ("Tick", "Quote"), ("MarginInterestRate", "Quote")}}
    for r in ("Second", "Minute", "Hour", "Daily"):
        want[r] = {("TradeBar", "Trade"), ("QuoteBar", "Quote"), ("MarginInterestRate", "Quote")}
    for r, types in want.items():
        a = L.QCAlgorithm()
        a.AddCryptoFuture("X", r, None, False)
        a.OnEndOfTimeStep()
        got = {(c.Type.__name__, c.TickType) for c in a._universe_selection()}
        assert got == types, r
    two = L.QCAlgorithm()
    two.AddCryptoFuture("X", "Tick", None, False)
    two.AddCryptoFuture("X", "Minute", None, False)
    two.OnEndOfTimeStep()
    assert len(two._universe_selection()) == 6  # both calls' configs, the two MarginInterestRate configs differ by resolution
    src = (HERE / "opponents" / "repro_lean52.py").read_text(encoding="utf-8")
    assert "data_manager_add" not in src and "SubscriptionDataConfig(" not in src and "DataManager(" not in src
    assert "C.configure(self.AddCryptoFuture" in src


def _grid_axes_from_the_requirements():
    """The axes rebuilt here from the requirements' text and the judgments (not from grid_c's output)."""
    import csv
    import re
    lines = (run_battery.REPO / "docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/REQUIREMENTS.md").read_text(
        encoding="utf-8").split("\n")
    segs = []
    # round r16-1: the rows are found by their first cell (the lead's L-445 edit moved them; fixed line numbers broke)
    rows = [[x.strip() for x in ln.strip().strip("|").split("|")] for ln in lines if ln.startswith("|")]
    picked = [(r, 4) for r in rows if r[0] == "0"] + [(r, c) for i in range(1, 8) for r in rows if r[0] == f"P0-{i}"
                                                      for c in (2, 3)]
    assert len(picked) == 1 + 14, len(picked)
    for r, c in picked:
        cell = r[c - 1]
        segs += [x.strip() for x in re.split(r"[・、。()（）/「」:]|\*\*|\+", cell) if x.strip()]
    with (HERE / "grid_c_judgments.tsv").open(encoding="utf-8") as f:
        judged = [r for r in csv.reader(f, delimiter="\t") if r and not r[0].startswith("#")]
    return segs, judged


def test_grid_every_requirement_segment_has_one_judgment():                            # (d)
    segs, judged = _grid_axes_from_the_requirements()
    assert [int(r[0]) for r in judged] == list(range(1, len(segs) + 1))
    assert [r[1] for r in judged] == segs
    for r in judged:
        assert r[2][:2] in ("E:", "V:", "X:", "N:") and len(r[2]) > 2, r


# ------------------------------------------------------------------ round r11-1: the cells' verdicts, two values
# The rule (LEAD_DESIGN.md section 8.2 items 1-2): a cell is "場面にした" (with the ids of the scenes) when a scene
# of the same viewpoint has the cell in `covers`, and "測っていない" otherwise; nothing else (round r16-1: the value's name;
# its reason is test_battery_r16_units.py's).
# The oracle below is written from that sentence alone (not from grid_c's code); the axes are rebuilt here from
# the requirements' text and the judgments.
GRID_DONE, GRID_NOT_MEASURED = "場面にした", "測っていない"
GRID_MEANING = ("この表は測っていない範囲の記録である。要件を広げるかはオーナーの判断で、項目 0 の通過のあとに"
                "『欠けているもの』の批評家の経路で上げる。")


def _grid_cells_from_the_requirements():
    import itertools
    _, judged = _grid_axes_from_the_requirements()
    ev = list(dict.fromkeys(r[2][2:] for r in judged if r[2].startswith("E:")))
    see = list(dict.fromkeys(r[2][2:] for r in judged if r[2].startswith("V:")))
    extra: dict = {}
    for r in judged:
        if r[2].startswith("X:"):
            _, vp, ax, val = r[2].split(":", 3)
            extra.setdefault(vp, [])
            if val not in extra[vp]:
                extra[vp].append(val)
    return [(vp, e, s_, x) for vp in [f"P0-{i}" for i in range(1, 8)]
            for e, s_, x in itertools.product(ev, see, extra.get(vp, [""]))], ev


def _grid_oracle(cell, scene_list):
    ids = [s_.id for s_ in scene_list if s_.viewpoint == cell[0] and tuple(cell[1:]) in {tuple(c) for c in s_.covers}]
    return (GRID_DONE, ids) if ids else (GRID_NOT_MEASURED, [])


def _fake(i, vp, *cells):
    """A scene of the set's own class (round r13-1: grid_c takes only scenes.Scene) whose declaration is `cells` and
    whose input gives every event type the cells name: an event with that type field for a market type, the
    `requests` field for the clock and the order notices (ROOTCAUSE_r13-1.md section 3)."""
    kinds = {v: k for k, v in scenes.JP.items() if k in scenes.TYPE_ORDER}
    inp: dict = {"events": [], "requests": []}
    for c in cells:
        if c[0] in kinds:
            inp["events"].append({"kind": kinds[c[0]], "ts_ns": scenes.T0})
        elif c[0] == "時計":
            inp["requests"].append("timer")
        else:
            inp["requests"].append("place")
    return scenes.Scene(id=i, viewpoint=vp, kind="value", title="", input=inp, expected=None, derivation="",
                        measures="", declares=tuple(cells))


def test_grid_verdicts_follow_covers_on_every_cell_and_every_cover_state():
    """Adversarial grid (round r11-1, the delegation's scrutiny (6)): every cell of every viewpoint (all of them,
    from the requirements' text) x every state of the scenes covering it -- none / a scene of the same viewpoint /
    only a scene of another viewpoint with the same (event, see-path, extra) / both -- and on each run every row
    of the table is compared with the oracle. Not in the grid (left out, and why): cells outside the axes (their
    scenes are listed apart and checked by test_grid_table_lists_every_cell_of_every_viewpoint_once), objects that are
    not a scenes.Scene (grid_c refuses them since round r13-1: test_grid_refuses_an_object_that_is_not_a_scene), a
    declaration the input does not give (test_battery_r13_covers_of.py). Round r13-1: the fake scenes are
    scenes.Scene objects whose input gives the declared cells' types (`_fake`), so the table reads covers_of."""
    import grid_c
    cells, _ = _grid_cells_from_the_requirements()
    others = {vp: next(v for v in [f"P0-{i}" for i in range(1, 8)] if v != vp) for vp in {c[0] for c in cells}}
    runs = 0
    for cell in cells:
        vp, key = cell[0], cell[1:]
        for state in (
            [],
            [_fake("same", vp, key)],
            [_fake("other", others[vp], key)],
            [_fake("same", vp, key), _fake("other", others[vp], key), _fake("same2", vp, key)],
        ):
            rows = grid_c.table(state)
            got = {(r["viewpoint"], r["event"], r["see"], r["extra"]): (r["verdict"], list(r["scenes"])) for r in rows}
            assert sorted(got) == sorted(cells) and len(rows) == len(cells), (cell, len(rows))
            for c in cells:
                assert got[c] == _grid_oracle(c, state), (cell, [s_.id for s_ in state], c, got[c])
            assert not grid_c.problems(state, rows), (cell, grid_c.problems(state, rows)[:3])
            runs += 1
    assert runs == 4 * len(cells)


def test_grid_refuses_an_object_that_is_not_a_scene():
    """Round r13-1: the table is made from scenes.covers_of only; an object with a hand-written `covers` is refused."""
    import grid_c
    from types import SimpleNamespace
    cell = ("約定", "戦略の呼び出しに届く物", "")
    with pytest.raises(TypeError):
        grid_c.table([SimpleNamespace(id="x", viewpoint="P0-1", covers=(cell,))])


def test_grid_check_refuses_every_verdict_but_the_one_covers_gives():
    """Adversarial grid for the check (grid_c.problems): every row of the table of the scene set x every candidate
    verdict (the two values, the words the three-valued table used, an empty verdict, "場面にした" without ids, the
    right verdict with a scene id that does not cover the cell); the check passes iff the candidate is the oracle's.
    Not in the grid: other strings (a verdict is refused unless it is one of the two values, so any other string is
    the same case as the ones listed), rows added or removed (test_grid_table_lists_every_cell_of_every_viewpoint_once)."""
    import grid_c
    rows = grid_c.table(scenes.SCENES)
    assert not grid_c.problems(scenes.SCENES, rows)
    checked = 0
    for n, r in enumerate(rows):
        cell = (r["viewpoint"], r["event"], r["see"], r["extra"])
        want = _grid_oracle(cell, scenes.SCENES)
        candidates = [(GRID_DONE, want[1] or ["p1-merge-by-time"]), (GRID_NOT_MEASURED, []), ("未決", []),
                      ("場面にしない", []), ("", []), (GRID_DONE, []), (want[0], want[1] + ["p7-account-swap"])]
        for verdict, ids in candidates:
            bad = [dict(x) for x in rows]
            bad[n]["verdict"], bad[n]["scenes"] = verdict, list(ids)
            ok = not grid_c.problems(scenes.SCENES, bad)
            assert ok == ((verdict, list(ids)) == want), (cell, verdict, ids, want)
            checked += 1
    assert checked == 7 * len(rows)


# The two phrases of positive definition A that named the withdrawn target (委任文 docs/DATA/delegations/
# 20260926_backtest_env_item4_close.md, L-470 / L-474): the record ROOTCAUSE_r8-1.md keeps them, the frozen text does not.
WITHDRAWN_FROM_A = (("新実装・当方の現状・試金石の比較の表の行は", "新実装・試金石の比較の表の行は"),
                    ("この正の定義は新実装・当方の現状・調査結果の側・再現・試金石のすべてに同じく当てる", "この正の定義は新実装・調査結果の側・再現・試金石のすべてに同じく当てる"))


def test_the_six_positive_definitions_are_frozen_in_the_definitions_one_paragraph_each():
    """LEAD_DESIGN.md section 8.2 item 5: definitions 0-E sit in DEFINITIONS.md, one paragraph each. 0, A, B, D, E are
    ROOTCAUSE_r8-1.md's paragraphs character for character; C keeps every sentence but the four section 8.2 item 1
    withdrew (the 9th to 12th: the three-valued verdicts and how they were decided), which it replaces."""
    import def_grids
    old = (HERE / "ROOTCAUSE_r8-1.md").read_text(encoding="utf-8").split("\n")
    text = (HERE / "DEFINITIONS.md").read_text(encoding="utf-8").split("\n")
    for k, head in def_grids.HEADS.items():
        mine = gen_definitions.FROZEN_DEFINITIONS[k]
        assert [ln for ln in text if ln == f"正の定義 {k}: " + mine], k            # one line, one paragraph
        before = [ln for ln in old if ln.startswith(head)]
        assert len(before) == 1, k
        if k == "A":  # L-470 / L-474 (2026-09-26): the axis value 「当方の現状」 was withdrawn from A; nothing else changed
            for old_phrase, new_phrase in WITHDRAWN_FROM_A:
                assert before[0].count(old_phrase) == 1, old_phrase
                before[0] = before[0].replace(old_phrase, new_phrase)
        if k != "C":
            assert mine == before[0], k
            continue
        a, b = before[0].split("。"), mine.split("。")
        assert a[:8] == b[:8] and a[12:] == b[-len(a[12:]):], "C: only the 9th to 12th sentences change"
        replaced = "。".join(b[8:len(b) - len(a[12:])])
        assert "未決" not in replaced and "場面にしない" not in replaced and "covers" in replaced
        assert "この表は測っていない範囲の記録である。要件を広げるかはオーナーの判断で" in replaced


def test_grid_table_lists_every_cell_of_every_viewpoint_once():                        # (a) (b)
    import grid_c
    cells, ev = _grid_cells_from_the_requirements()
    rows = grid_c.table(scenes.SCENES)
    got = [(r["viewpoint"], r["event"], r["see"], r["extra"]) for r in rows]
    assert sorted(got) == sorted(cells) and len(got) == len(set(got))              # (a) every cell, once
    assert {r["verdict"] for r in rows} <= {GRID_DONE, GRID_NOT_MEASURED}             # (b) two values only
    for r in rows:
        assert (r["verdict"], r["scenes"]) == _grid_oracle((r["viewpoint"], r["event"], r["see"], r["extra"]),
                                                           scenes.SCENES), r
    outside = {c[0] for s_ in scenes.SCENES for c in s_.covers} - set(ev)
    assert outside == set(scenes.OUTSIDE_AXES)
    text = (HERE / "DEFINITIONS.md").read_text(encoding="utf-8")
    frozen = text[text.index("## 正の定義 0〜E"):text.index("## 数える物の選択肢")]  # definition C's own words
    rest = text.replace(frozen, "")
    assert "升目を列べない" not in rest and "観点: なし" not in rest  # no statement that skips listing the cells
    section = text[text.index("## 場面にしていない観点・側面"):text.index("\n## ", text.index("## 場面にしていない観点・側面") + 5)]
    assert GRID_MEANING in section                                                    # section 8.2 item 2
    assert "未決" not in section and "場面にしない" not in section and "理由1" not in section


def test_every_line_the_scene_keeper_writes_is_listed_and_every_marked_line_judged():
    """Round r8-1 (positive definition B): every line of every file the scene keeper writes is in the output of
    line_marks.py; a line naming a scene (id, family, Scene field, a count of scenes) has a judgment in
    line_judgments.tsv of a known category, and the categories that rest on a machine stay where the machine is."""
    import line_marks as M
    lines = M.all_lines()
    judged = M.judgments()
    marked = [x for x in lines if x[3]]
    missing = [(f, i, t[:100]) for f, i, t, _ in marked if M.key(f, t) not in judged]
    assert not missing, missing[:10]
    assert len(marked) + sum(1 for x in lines if not x[3]) == len(lines)
    for f, i, t, _ in marked:
        cat = judged[M.key(f, t)][0]
        assert cat in M.CATEGORIES, (f, i, cat)
        if cat == "生成物":
            assert f == "DEFINITIONS.md", (f, i)
        if cat == "照合元":
            assert f == "scenes.py", (f, i)
        if cat == "試験が照らす":
            assert f in ("opponents/CONSIDERED.md", "mutant.py"), (f, i)
    files = set(M.files())
    assert {"opponents/CONSIDERED.md", "DEFINITIONS.md", "scenes.py", "ROOTCAUSE_r8-1.md"} <= files
    assert not any(f.startswith("survey_results/") for f in files)


def test_the_handoff_to_the_materials_role_is_in_the_definitions_and_the_columns_exist():
    """Round r8-1 (positive definition A, handoff): DEFINITIONS.md carries the handoff to the materials role with the
    table's one note sentence, and every runner output has the columns the handoff names."""
    text = (HERE / "DEFINITIONS.md").read_text(encoding="utf-8")
    assert "## 資料係への申し送り" in text
    assert "「型の組は対象の持つ型から規則で決めた」" in text
    for t, rows in _records().items():
        for col in ("choose", "settings_1", "types_1"):
            assert rows and col in rows[0], (t, col)


def test_every_use_of_the_scene_keepers_terms_is_judged():
    """Round r8-1 (positive definition D): every occurrence (term, line) of the terms ROOTCAUSE_r8-1.md's term
    table gives a meaning of the scene keeper's own is listed by term_marks.py and has one judgment in
    term_judgments.tsv; no judgment is 「別の意味」 (a term of the table has one meaning), and no judgment is left
    for a line that no longer holds the term (a changed line is read again)."""
    import term_marks as T
    ts = T.terms()
    assert "設定つき対象" in ts and "升目" in ts and "照合元" in ts  # the table is read (a smoke check of the reader)
    assert not T.problems(), T.problems()[:20]
