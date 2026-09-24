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
        p = HERE / "survey_results" / f"{r['target']}.tsv"
        with p.open(encoding="utf-8") as f:
            ids = [row["scene_id"] for row in csv.DictReader(f, delimiter="\t")]
        assert sorted(ids) == sorted(s.id for s in scenes.SCENES), r["cand"]


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
    ran = {int(r["cand"]) for r in _ledger() if r["result"] == "走った"}
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
           if "provenance_error" in r["output_1"] or "出所の検めで採点しない" in r["detail_1"]]
    assert not bad, bad


def test_current_impl_passes_the_provenance_check():
    rows = run_battery.run_target("current_impl")
    bad = [(r["scene_id"], r["detail_1"][:160]) for r in rows if "出所の検めで採点しない" in r["detail_1"]]
    assert not bad, bad


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
    assert _check("p3-trade", {"sequence": [["trade", 1]]}, {"carriers": [C.carrier(tool.event(1))]}, roots).status == "ok"
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
    ev = tool.event(1)
    assert _check("p3-trade", {"sequence": [["trade", 1]]}, {"carriers": [C.carrier_tag(ev, tool.Kind.TRADE)]}, roots).status == "ok"
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
    r.read("tool.history()", tool.history)
    assert _check("p4-visible-at-step", out, r.provenance(), roots).status == "ok"
    kept = [100.0, 101.0, 102.0, 103.0]
    r = C.Reads()
    r.read("a list the strategy kept", lambda: list(kept))
    got = _check("p4-visible-at-step", out, r.provenance(), roots)
    assert got.status == "error" and "1 行も走らず" in got.output["provenance_error"], got.output
    by_hand = {"reads": [{"means": "tool.history()", "returned": [100.0, 101.0, 102.0, 103.0], "touched": [roots.dirs[0] + "/__init__.py"]}]}
    got = _check("p4-visible-at-step", out, by_hand, roots)
    assert got.status == "error" and "手で書いた" in got.output["provenance_error"], got.output
    r = C.Reads()
    r.read("tool.history()", tool.history)
    assert _check("p4-visible-at-step", {"visible_count": 5, "max_visible_close": 104.0}, r.provenance(), roots).status == "error"

    def attempts(fn):
        att = C.Attempts()
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
    names = {"current_impl", "new_impl", "mutant", *run_battery.OPPONENTS}
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
    return {int(r["cand"]): r["target"] for r in _ledger() if r["result"] == "走った"}


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
        for group in re.findall(r"((?:p\d-[\w-]+(?:(?:の[^・、。 ]{1,8})?・)?)+) ?が正解と一致", seg):
            for sid in re.findall(r"p\d-[\w-]+", group):
                checked += 1
                ok_ = [t for t in named if recs.get(t, {}).get(sid, {}).get("correctness") == "正解と一致"]
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
