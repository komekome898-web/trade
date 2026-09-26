"""Item 4 battery, round r2-1: the tests of the claims table (ROOTCAUSE_r2-1.md §4), the scene-keeper's tests (規則 7).

Families (the claim, the test that fails if a hand-written claim is left, the mutant of the machine):
  A  the order within one bar (R-O1 / L-5)      i4-r1-02
  B  what a scene asks for besides its viewpoint i4-r1-05
  C  the property grids and their invariants     i4-r1-06
  D  the granularity of I4-3                     i4-r1-07
  E  the controls of a variant                   i4-r1-09
  F  the compatibility mouth of new_impl         i4-r1-10
  G  the review table's judgement                i4-r1-05 / i4-r1-08
  H  the install attempts                        i4-r1-11

The adversarial grids (委任文 §3「提出前の吟味」(6)): the rule's input space, not any engine's branches.
  - test_exit_events_grid: every single exit event and every pair of exit events that can happen together
    (EXIT_EVENTS, less NEVER_TOGETHER / SAME_FILL), for a long and a short position, built from the rule text
    (levels 2 % / 3 % / 2.5 %, window 2, time exit N = 2); the detector must name exactly that set on bar 4 and
    nothing on bar 3.  Not in the grid (named): three or more events at once (the pairs fix the order; the winner
    of a larger set is the first of it in the order), a bar that OPENS beyond a level (a gap), exits on other bars
    than 4, costs other than 0, entry bars other than 2.
  - test_order_matches_the_rule_text: every pair's winner under ORDER_SPEC / ORDER_LEGACY against a table written
    from the text of R-O1 / L-5 (PROSE_SPEC / PROSE_LEGACY below), not from the lists.
  - test_invariants_catch_each_perturbation: every grid scene x every perturbation kind (value, size, bar, side,
    PnL, equity, nothing traded, look-ahead in a prefix, a kept position past its exit).  Not in the grid: a
    perturbation that keeps every identity (e.g. two fills swapped within the same bar and price).
"""
from __future__ import annotations

import copy
import csv
import importlib.util
import sys
import tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
for p in (HERE, HERE / "adapters", REPO / "src"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import i4_judge as J  # noqa: E402
import i4_scenes as S  # noqa: E402


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# =========================================================================== A  the order within one bar
def test_every_close_is_the_winner_of_its_bar():
    wrong, _ = S.order_findings(S.SCENES)
    assert wrong == []


def test_every_order_pair_is_pinned():
    _, pinned = S.order_findings(S.SCENES)
    missing = [p for p in S.order_pairs() if ("spec",) + S.first_of(p, S.ORDER_SPEC) not in pinned]
    assert missing == []
    differ = [p for p in S.order_pairs() if S.first_of(p, S.ORDER_SPEC) != S.first_of(p, S.ORDER_LEGACY)]
    assert differ, "L-1 / L-5 name pairs whose order differs"
    assert [p for p in differ if ("legacy",) + S.first_of(p, S.ORDER_LEGACY) not in pinned] == []


def _swapped(order, pair):
    o = list(order)
    a, b = pair
    ia, ib = o.index(a), o.index(b)
    o[ia], o[ib] = o[ib], o[ia]
    return o


@pytest.mark.parametrize("pair", S.order_pairs())
def test_swapping_any_pair_of_the_order_breaks_a_scene(pair):
    wrong, _ = S.order_findings(S.SCENES, order_override={"spec": _swapped(S.ORDER_SPEC, pair)})
    assert wrong, f"swapping {pair} in the spec order contradicts no scene"
    if S.first_of(pair, S.ORDER_SPEC) != S.first_of(pair, S.ORDER_LEGACY):
        wrong, _ = S.order_findings(S.SCENES, order_override={"legacy": _swapped(S.ORDER_LEGACY, pair)})
        assert wrong, f"swapping {pair} in the legacy order contradicts no scene"


# the winner of each pair, read from the rule text (DEFINITIONS.md R-O1 and L-5), not from the lists
PROSE_SPEC = {
    # R-O1: ① wick, ② on the time-exit bar: stop, else time, ③ signal, ④ stop, ⑤ tp, ⑥ mtp, ⑦ limit
    ("wick", "stop@time"): None, ("wick", "signal"): "wick", ("wick", "tp"): "wick", ("wick", "mtp"): "wick",
    ("wick", "limit"): "wick", ("stop@time", "time"): "stop@time", ("stop@time", "signal"): "stop@time",
    ("stop@time", "tp"): "stop@time", ("stop@time", "mtp"): "stop@time", ("stop@time", "limit"): "stop@time",
    ("time", "signal"): "time", ("time", "tp"): "time", ("time", "mtp"): "time", ("time", "limit"): "time",
    ("signal", "stop"): "signal", ("signal", "tp"): "signal", ("signal", "mtp"): "signal",
    ("stop", "tp"): "stop", ("stop", "mtp"): "stop", ("stop", "limit"): "stop", ("tp", "mtp"): "tp",
    ("tp", "limit"): "tp", ("mtp", "limit"): "mtp",
}
PROSE_LEGACY = dict(PROSE_SPEC)
PROSE_LEGACY.update({  # L-5: ① wick → ④ stop (also on the time-exit bar) → ⑤ tp → ⑥ mtp → ② time → ③ signal → ⑦ limit
    ("signal", "stop"): "stop", ("signal", "tp"): "tp", ("signal", "mtp"): "mtp", ("time", "tp"): "tp",
    ("time", "mtp"): "mtp"})


@pytest.mark.parametrize("pair", S.order_pairs())
def test_order_matches_the_rule_text(pair):
    key = pair if pair in PROSE_SPEC else pair[::-1]
    assert S.winner(set(pair), S.ORDER_SPEC) == PROSE_SPEC[key]
    assert S.winner(set(pair), S.ORDER_LEGACY) == PROSE_LEGACY[key]


def _mirror(rows):
    return [(200 - o, 200 - lo, 200 - h, 200 - c) for o, h, lo, c in rows]


def _grid_input(events, d):
    """A position opened at bar 2 (price 100) where exactly `events` can happen on bar 4 (the rule text's levels)."""
    ev = set(events)
    maker = "limit" in ev
    wick = "wick" in ev
    rows = [(100, 100.5, 99.5, 100), (100, 100.5, 99.5, 100), (100, 101.5, 99.5, 101),
            (101, 102, 99.2, 99.3) if wick else (101, 102, 100, 101)]
    o4 = 99.5 if wick else 101
    lo4 = 97 if ("stop" in ev or "stop@time" in ev) else min(o4, 100.5)
    hi4 = 104 if ev & {"tp", "mtp", "limit"} else 100.8
    if wick and not maker:
        hi4 = max(hi4, o4)
    rows += [(o4, hi4, lo4, (lo4 + hi4) / 2), (100, 100.5, 99.5, 100)]
    if d < 0:
        rows = _mirror(rows)
    over = {"allow_short": d < 0}
    if maker:
        over.update(execution="maker", maker_timeout_bars=3)
    if "stop" in ev or "stop@time" in ev:
        over["stop_loss_pct"] = 2.0
    if "time" in ev or "stop@time" in ev:
        over["max_hold_bars"] = 2
    if "tp" in ev:
        over["take_profit_pct"] = 3.0
    if "mtp" in ev:
        over.update(exit_execution="maker_tp", maker_tp_pct=2.5)
    if wick:
        over.update(stop_mode="wick_invalidation", stop_window_bars=2)
    entry, closer = ("BUY", "SELL") if d > 0 else ("SELL", "BUY")
    sigs = [(1, entry)] + ([(3, closer)] if ev & {"signal", "limit"} else [])
    return S.bars_input(S.mk_bars(rows), sigs, S.cfg(**over))


def _grid_sets():
    out = [{e} for e in S.EXIT_EVENTS if e != "stop@time"] + [{"stop@time", "time"}]
    for a, b in S.order_pairs():
        e = {a, b} | ({"time"} if "stop@time" in (a, b) else set())
        if e not in out:
            out.append(e)
    return out


@pytest.mark.parametrize("d", [1, -1])
@pytest.mark.parametrize("events", _grid_sets(), ids=lambda e: "+".join(sorted(e)))
def test_exit_events_grid(events, d):
    inp = _grid_input(events, d)
    assert S.exit_events(inp, 2, d, 100.0, 3) == set()
    assert S.exit_events(inp, 2, d, 100.0, 4) == set(events)


# =========================================================================== B  besides the viewpoint
BAR_VPS = [f"I4-{k}" for k in range(8, 18)]


def test_every_bar_viewpoint_has_a_barrier_free_value_scene():
    for vp in BAR_VPS:
        sc = [s for s in S.SCENES if s["viewpoint"] == vp and s["kind"] == "値" and s.get("input", {}).get("op") == "bars"]
        assert sc and any(not S.barriers(s) for s in sc), (vp, [(s["id"], S.barriers(s)) for s in sc])


def test_no_scene_sets_a_cost_its_judged_keys_cannot_see():
    bad = [(s["id"], b) for s in S.SCENES for b in S.barriers(s) if b.startswith("判定から見えない")]
    assert bad == []


def test_barriers_names_each_barrier():
    base = copy.deepcopy(S.by_id("i4-10-stop-first-plain"))
    assert S.barriers(base) == []
    s = copy.deepcopy(base)
    s["input"]["signals"] = [{"bar": 0, "signal": "BUY"}]
    assert "足 0 の合図" in S.barriers(s)
    s = copy.deepcopy(base)
    s["input"]["config"]["costs"]["taker_fee_pct"] = 0.1
    assert "0 でない費用" in S.barriers(s) and "違う 2 つの手数料の率" in S.barriers(s)
    s = copy.deepcopy(base)
    s["input"]["config"]["costs"].update(taker_fee_pct=0.1, maker_fee_pct=0.1)
    s["judge"] = S.J("fills")
    assert "判定から見えない taker の手数料" in S.barriers(s)
    s = copy.deepcopy(S.by_id("i4-8-no-short"))
    s["input"]["config"]["costs"]["maker_fee_pct"] = 0.05
    assert "判定から見えない maker の手数料" in S.barriers(s)
    s = copy.deepcopy(base)
    s["judge"] = S.J("fills", "pnls")
    assert "費用 0・持ち越し 0 の場面で損益・資産も判定する(約定から決まる)" in S.barriers(s)


# =========================================================================== C  the property grids
GRIDS = [s for s in S.SCENES if s["viewpoint"] == "I4-2"]


def test_property_grids_reach_every_path():
    first = GRIDS[0]
    assert set().union(*[S.paths_of(c["config"], c["bar_seconds"]) for c in first["cases"]]) == set(S.PATHS)
    for path in ("stop", "tp", "maker", "mtp", "swap", "hold", "wick"):
        g = S.by_id(f"i4-2-grid-{path}")
        assert all(S.paths_of(c["config"], c["bar_seconds"]) == {path} for c in g["cases"]), path
        assert not S.barriers(g), (path, S.barriers(g))
    for g in GRIDS:
        for k, e in enumerate(g["expect"]):
            if "prefix_of" in e:
                full, pre = g["cases"][e["prefix_of"]], g["cases"][k]
                assert pre["bars"] == full["bars"][:e["upto"]] and len(pre["bars"]) == e["upto"] < len(full["bars"])


def _current():
    return _load(HERE / "adapters" / "current_impl.py", "i4_claims_current").TARGET


@pytest.fixture(scope="module")
def grid_obs():
    cur = _current()
    return {g["id"]: [cur.run(c) for c in g["cases"]] for g in GRIDS}


def test_invariants_hold_on_the_existing_engine_and_the_hand_answers(grid_obs):
    for g in GRIDS:
        assert J.compare(g["expect"], grid_obs[g["id"]], g)[0] == "正解と一致", g["id"]
        for c, e in zip(g["cases"], g["expect"]):
            if "fills" in e:
                assert J.invariants(c, e) == []


def _perturbations(obs_list, g):
    """(name, perturbed observation list) -- one change each, at the first case where it applies."""
    out = []
    idx = next((k for k, o in enumerate(obs_list) if len(o["fills"]) >= 2), None)
    if idx is None:
        return out

    def one(name, f):
        o = copy.deepcopy(obs_list)
        f(o[idx])
        out.append((name, o))
    one("値", lambda o: o["fills"][0].__setitem__("price", o["fills"][0]["price"] * (1 + 1e-6)))
    one("決済の数量", lambda o: o["fills"][1].__setitem__("size", o["fills"][1]["size"] * 1.01))
    one("決済の足", lambda o: o["fills"][1].__setitem__("bar", o["fills"][1]["bar"] + 1))
    one("向き", lambda o: o["fills"][0].__setitem__("side", "OPEN_SHORT" if o["fills"][0]["side"] == "OPEN_LONG"
                                                   else "OPEN_LONG"))
    one("損益", lambda o: o["pnls"].__setitem__(0, o["pnls"][0] + 0.5))
    one("資産", lambda o: o["equity"].__setitem__(len(o["equity"]) - 1, o["equity"][-1] + 0.5))
    one("何もしない", lambda o: (o["fills"].clear(), o["pnls"].clear(),
                              o["equity"].__setitem__(slice(None), [g["cases"][idx]["config"]["initial_equity"]] * len(o["equity"]))))
    one("建玉を残す", lambda o: (o["fills"].__delitem__(slice(1, None)), o["pnls"].clear()))
    pre = next((k for k, e in enumerate(g["expect"]) if "prefix_of" in e and obs_list[k]["fills"]), None)
    if pre is not None:
        o = copy.deepcopy(obs_list)
        o[pre]["fills"][0]["price"] *= 1 + 1e-6
        out.append(("先読み(先頭の部分だけ違う)", o))
    return out


@pytest.mark.parametrize("gid", [g["id"] for g in GRIDS])
def test_invariants_catch_each_perturbation(gid, grid_obs):
    g = S.by_id(gid)
    obs = grid_obs[gid]
    kinds = _perturbations(obs, g)
    assert len(kinds) >= 8, gid
    for name, o in kinds:
        assert J.compare(g["expect"], o, g)[0] == "不一致", (gid, name)


# =========================================================================== D  granularity
def test_i4_3_has_a_value_scene_at_each_granularity():
    got = {S.granularity_of(s) for s in S.SCENES if s["viewpoint"] == "I4-3" and s["kind"] == "値"}
    assert got == set(S.GRANULARITY)


def test_granularity_of_names_each_op():
    s = copy.deepcopy(S.by_id("i4-3-core-delivery"))
    assert S.granularity_of(s) == "core"
    s["input"] = {"op": "bars", "reference": True}
    assert S.granularity_of(s) == "reference"
    s["input"] = {"op": "bars"}
    assert S.granularity_of(s) == "whole"


def test_delivery_answers_follow_c1():
    for sid in ("i4-3-core-delivery", "i4-3-core-delivery-gap"):
        s = S.by_id(sid)
        bars = s["input"]["bars"]
        assert [c["seen"] for c in s["expect"]["calls"]] == list(range(1, len(bars) + 1))
        assert [c["last_t_ns"] for c in s["expect"]["calls"]] == [b["t_ns"] for b in bars]
    gap = S.by_id("i4-3-core-delivery-gap")["input"]["bars"]
    assert any(b2["t_ns"] - b1["t_ns"] > 60 * S.NS for b1, b2 in zip(gap, gap[1:]))


# =========================================================================== E  the controls of a variant
def test_every_variant_feature_is_used_by_a_passing_control():
    for s in S.SCENES:
        if "variant" in s:
            assert S.features(s["variant"]) <= S.control_features(s), (s["id"], S.features(s["variant"]) - S.control_features(s))


class _Fake:
    """A target that answers every control input with its expected answer, and refuses the inputs in `refuse`."""

    def __init__(self, scene, refuse):
        self.s, self.refuse = scene, refuse
        self.name = "fake"

    def run(self, inp):
        from i4_protocol import Refused
        clean = {k: v for k, v in inp.items() if k != "root"}
        for r in self.refuse:
            if clean == r:
                raise Refused("fake refusal")
        if clean == self.s["input"]:
            return copy.deepcopy(self.s["expect"])
        for mc in self.s.get("more_controls", []):
            if clean == mc["input"]:
                return copy.deepcopy(mc["expect"])
        raise AssertionError("unexpected input")


@pytest.mark.parametrize("sid", [s["id"] for s in S.SCENES if s.get("more_controls")])
def test_runner_credits_a_refusal_only_after_all_controls(sid):
    import run_battery as R
    s = copy.deepcopy(S.by_id(sid))
    for mc in s["more_controls"]:
        for f in mc["input"].get("files", []):
            f.pop("text", None)
    for f in s["input"].get("files", []):
        f.pop("text", None)
    for f in s["variant"].get("files", []):
        f.pop("text", None)
    orig = S.by_id(sid)
    with tempfile.TemporaryDirectory() as base:
        good = _Fake(s, [s["variant"]])
        assert R.classify(orig, good, base)[0] == "正解と一致"
        lacking = _Fake(s, [s["variant"]] + [mc["input"] for mc in s["more_controls"]])
        assert R.classify(orig, lacking, base)[0] != "正解と一致"


# =========================================================================== F  the compatibility mouth
def test_new_impl_legacy_goes_through_the_old_mouths(monkeypatch):
    new = _load(HERE / "adapters" / "new_impl.py", "i4_claims_new_impl")
    seen = {"run_backtest": 0, "split_data": 0}
    for name in seen:
        real = getattr(new, name)

        def wrap(*a, _real=real, _name=name, **k):
            seen[_name] += 1
            return _real(*a, **k)
        monkeypatch.setattr(new, name, wrap)
    s = S.by_id("i4-13-two-models")
    assert J.compare(s["expect"], new.TARGET.run(s["input"]), s)[0] == "正解と一致"
    s = S.by_id("i4-18-two-models")
    assert J.compare(s["expect"], new.TARGET.run(s["input"]), s)[0] == "正解と一致"
    assert seen == {"run_backtest": 1, "split_data": 1}
    # the mutant: an old mouth that answers differently changes the legacy output (the adapter reads it)
    monkeypatch.setattr(new, "run_backtest", lambda *a, **k: (_ for _ in ()).throw(ValueError("mouth replaced")))
    from i4_protocol import Refused
    with pytest.raises(Refused):
        new.TARGET.run(S.by_id("i4-13-two-models")["input"])


# =========================================================================== G  the review table
def _gen():
    return _load(HERE / "gen_considered.py", "i4_claims_gen_considered")


def test_considered_rows_rest_on_verified_absence():
    text = (HERE / "opponents" / "CONSIDERED.md").read_text(encoding="utf-8")
    gen = _gen()
    bad = [ln[:120] for ln in text.splitlines() if "| 持たないと確認した |" in ln and any(w in ln for w in gen.UNVERIFIED)]
    assert bad == []


def test_judge_row_changes_with_unread_parts():
    gen = _gen()
    sid = "i4-10-stop-first-plain"
    row = {"scene": sid, "kind": "値", "detail_1": "adapter: T: stop_loss_pct: 逆指値の口が無い(broker.py 12 行)"}
    assert gen.judge_row([row])[0] == "持たないと確認した"
    row2 = dict(row, detail_1="adapter: T: stop_loss_pct: 逆指値の経路は読んでいない")
    assert gen.judge_row([row2])[0] == "再現できない"
    row3 = dict(row, detail_1="adapter: T: 足 0 の合図: 道具は最初の足で戦略を呼ばない(x.py 3 行)")
    assert gen.judge_row([row3])[0] == "再現できない"


# =========================================================================== H  install attempts
STOP_WORDS = ("attempts/", "資格情報", "導入前の検査", "消えている", "Python 2", "C# / .NET", "C++ の構築", "触手", "構築が失敗",
              "Node.js")


def test_runnability_records_an_attempt_for_every_reproduction():
    with open(HERE / "opponents" / "RUNNABILITY.tsv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    rep = [r for r in rows if r["result"] == "再現した"]
    assert rep
    for r in rep:
        assert any(w in r["tried"] for w in STOP_WORDS), (r["cand"], r["tried"][:120])
    for cand in ("56", "60", "67"):
        r = next(x for x in rows if x["cand"] == cand)
        assert "attempts/i4_r2-1_scenekeeper_dryrun_" in r["tried"] and "MiB" in r["tried"], cand
