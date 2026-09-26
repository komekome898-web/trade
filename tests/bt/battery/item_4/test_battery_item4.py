"""Item 4 battery (統合と答え合わせ): tests of the scene set itself (the scene-keeper's tests, 規則 7).

- the scene set covers every viewpoint (a value scene each, or a stated reason why it cannot be a scene);
- the expected answers are internally consistent (the grid's invariants hold on its own answers, the pipeline files
  re-read with the csv module give the expected fills, the sha256 are the files' own);
- the judge tells a right answer from a perturbed one;
- the stated rules and the existing bar engine (src/bot/backtest/) agree on every bars / metrics / split scene except
  the listed deviations L-1..L-4 (this pins where the existing implementation departs from its own stated rules; the
  answers themselves are hand-calculated, never taken from the implementation);
- the touchstone plants exactly one defect and it breaks the scenes it says it breaks;
- the runner writes one row per scene with the reproducibility cell;
- the unrunnable-candidate table passes scripts/check_bt_considered.py.
"""
from __future__ import annotations

import copy
import csv
import hashlib
import importlib.util
import io
import json
import math
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(HERE))

import i4_judge as J  # noqa: E402
import i4_scenes as S  # noqa: E402

DEVIATIONS = {"i4-12-touch-decimal", "i4-13-tp-on-exit-bar", "i4-13-two-models", "i4-17-sharpe-bar-seconds",
              "i4-17-two-models", "i4-18-split-decimal", "i4-18-two-models",
              # L-5 (round r2-1, i4-r1-02): the pending signal after the range exits and the time exit
              "i4-10-signal-first", "i4-10-signal-first-short", "i4-10-signal-first-two-models", "i4-13-time-first",
              "i4-13-time-first-two-models", "i4-13-time-maker-tp-two-models",
              # L-5 (round r3-1, i4-r2-02): the range stop on the time-exit bar before the time exit at the open
              "i4-13-stop-on-time-bar", "i4-13-stop-on-time-bar-maker", "i4-13-stop-on-time-bar-two-models",
              # L-6 / L-7 (round r3-1, i4-r2-08): the maker path of a mask-False signal and of a same-side signal
              "i4-16-maker-mask-false-not-missed", "i4-16-maker-mask-false-two-models", "i4-16-same-side-keeps-limit",
              "i4-16-same-side-two-models"}


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_every_viewpoint_has_a_value_scene_or_a_reason():
    for vp in S.VIEWPOINTS:
        kinds = {s["kind"] for s in S.SCENES if s["viewpoint"] == vp}
        if vp in S.NOT_SCENES:
            assert not kinds, vp
            assert len(S.NOT_SCENES[vp]) > 40
        else:
            assert "値" in kinds, f"{vp} has no value scene"


def test_scene_fields_and_judged_keys_are_asked_for():
    for s in S.SCENES:
        for k in ("id", "viewpoint", "kind", "what", "how", "expect", "judge"):
            assert s.get(k) not in (None, ""), (s["id"], k)
        inps = s["cases"] if "cases" in s else [s["input"]]
        for inp in inps:
            if inp["op"] == "bars":
                assert set(inp["config"]) == set(S.cfg()), s["id"]  # every option explicit
                for sub in (s["judge"].values() if ("legacy" in s["judge"] or "engine" in s["judge"]) else [s["judge"]]):
                    for k in sub:
                        if k != "invariants":
                            assert k in inp["want"], (s["id"], k)


def test_grid_answers_satisfy_their_own_invariants():
    sc = S.by_id("i4-2-grid")
    for case, exp in zip(sc["cases"], sc["expect"]):
        assert J.invariants(case, exp) == []


def test_grid_has_shorts_closes_costs_and_a_last_bar_signal():
    sc = S.by_id("i4-2-grid")
    sides = {f["side"] for e in sc["expect"] for f in e["fills"]}
    assert {"OPEN_LONG", "OPEN_SHORT", "CLOSE_LONG", "CLOSE_SHORT"} <= sides
    assert any(sg["signal"] == "CLOSE" for c in sc["cases"] for sg in c["signals"])
    assert any(any(c["config"]["costs"].values()) for c in sc["cases"])


def _parse_pipeline_fills(files, sched):
    """Re-read the pipeline files with the csv module (not with the scene's own builders) and apply F-1."""
    import calendar
    import datetime as D
    by = {f["path"]: f["text"] for f in files}

    def iso_ns(txt, tz_h=0):
        txt = txt.replace("Z", "").replace("+00:00", "").replace("T", " ")
        head, _, frac = txt.partition(".")
        d = D.datetime.strptime(head, "%Y-%m-%d %H:%M:%S" if head.count(":") == 2 else "%Y-%m-%d %H:%M")
        ns = (calendar.timegm(d.timetuple()) - tz_h * 3600) * 10**9
        return ns + (int((frac + "000000000")[:9]) if frac else 0)

    ev = {}
    rows = list(csv.DictReader(io.StringIO(by["backtest_data/bf_exec_synth_20260105/executions_20260105.csv"])))
    ev["bf"] = [(iso_ns(r["exec_date"]), float(r["price"])) for r in rows]
    rows = list(csv.reader(io.StringIO(by["backtest_data/binance_BTCUSDT_aggTrades_synth/BTCUSDT-aggTrades-2026-01-05.csv"])))
    ev["binance"] = [(int(r[5]) * 10**6, float(r[1])) for r in rows]
    rows = list(csv.DictReader(io.StringIO(by["backtest_data/fx_event_ticks_synth/USDJPY_20260105.csv"])))
    fxq = [(iso_ns(r["ts_utc"]), float(r["bid"]), float(r["ask"])) for r in rows]
    rows = list(csv.DictReader(io.StringIO(by["backtest_data/n225f_synth_20260105/bars_1min.csv"])))
    ev["jpx"] = [(iso_ns(r["date"] + " " + r["time"], tz_h=9), float(r["open"])) for r in rows]
    rows = list(csv.DictReader(io.StringIO(by["backtest_data/fx_1m_synth/USDJPY_1m_20260105.csv"])))
    ev["fx_1m"] = [(iso_ns(r["ts"]), float(r["open"])) for r in rows]
    out = {}
    for name in ("bf", "binance", "jpx", "fx_1m"):
        out[name] = [next((t, p) for t, p in ev[name] if t >= o["t_ns"]) for o in sched]
    out["fx_tick"] = [next((t, a if o["side"] == "buy" else b) for t, b, a in fxq if t >= o["t_ns"]) for o in sched]
    return out


def test_pipeline_expected_fills_match_the_files():
    sc = S.by_id("i4-5-fills")
    got = _parse_pipeline_fills(sc["input"]["files"], S.SCHEDULE)
    for inst, fl in sc["expect"]["fills"].items():
        assert [(f["t_ns"], f["px"]) for f in fl] == [(t, pytest.approx(p)) for t, p in got[inst]], inst


def test_pipeline_sha256_are_the_files_own():
    sc = S.by_id("i4-5-outputs")
    for f in sc["input"]["files"]:
        assert sc["expect"]["run_record"]["data_sha256"][f["path"]] == hashlib.sha256(f["text"].encode()).hexdigest()


def test_judge_rejects_perturbations():
    sc = S.by_id("i4-3-e2e-taker")
    exp = S.expected(sc)
    assert J.compare(exp, copy.deepcopy(exp), sc)[0] == "正解と一致"
    for mutate in (lambda o: o["fills"][0].__setitem__("price", o["fills"][0]["price"] * (1 + 1e-7)),
                   lambda o: o["fills"][1].__setitem__("bar", o["fills"][1]["bar"] + 1),
                   lambda o: o["pnls"].pop(),
                   lambda o: o["metrics"].__setitem__("num_trades", 3),
                   lambda o: o["metrics"].pop("sharpe_ratio"),
                   lambda o: o.__setitem__("missed_fills", 1),
                   lambda o: o["equity"].__setitem__(5, o["equity"][5] + 0.01)):
        o = copy.deepcopy(exp)
        mutate(o)
        assert J.compare(exp, o, sc)[0] == "不一致"


def test_judge_invariants_catch_a_broken_identity():
    sc = S.by_id("i4-2-grid")
    k = next(i for i, e in enumerate(sc["expect"]) if e["pnls"])
    o = copy.deepcopy(sc["expect"][k])
    o["pnls"][0] += 1.0
    assert J.invariants(sc["cases"][k], o)


def test_judge_dashboard_rule():
    e = {"tabs": S.TABS, "banner": S.BANNER}
    tabs = [{"label": t + "(x)", "text": "..." + S.BANNER} for t in S.TABS]
    assert J._dashboard(e, {"tabs": tabs}) is None
    tabs[3]["text"] = "no banner"
    assert J._dashboard(e, {"tabs": tabs})
    tabs2 = [{"label": t, "text": S.BANNER} for t in S.TABS if t != "費用"]
    assert J._dashboard(e, {"tabs": tabs2})


def _current():
    sys.path.insert(0, str(REPO / "src"))
    return _load(HERE / "adapters" / "current_impl.py", "i4_test_current_impl").TARGET


def test_stated_rules_and_existing_engine_agree_except_the_listed_deviations():
    cur = _current()
    got = {}
    for s in S.SCENES:
        if "cases" in s:
            obs = [cur.run(c) for c in s["cases"]]
            got[s["id"]] = J.compare(s["expect"], obs, s)[0]
            continue
        if s["input"]["op"] == "pipeline" or s["input"].get("reference"):
            continue
        got[s["id"]] = J.compare(s["expect"], cur.run(s["input"]), s)[0]
    wrong = {k for k, v in got.items() if v != "正解と一致"}
    assert wrong == DEVIATIONS


def test_legacy_answers_of_two_model_scenes_are_the_existing_engine():
    cur = _current()
    for sid in [s["id"] for s in S.SCENES if "models" in (s.get("input") or {})]:
        s = S.by_id(sid)
        obs = cur.run(s["input"])
        assert J.judge_obs(s["expect"]["legacy"], obs["legacy"], s["judge"]["legacy"]) is None, sid
        assert J.judge_obs(s["expect"]["spec"], obs["spec"], s["judge"]["spec"]) is not None, sid


def test_mutant_plants_one_defect_and_breaks_its_scenes():
    mutant = _load(HERE / "mutant.py", "i4_test_mutant")
    inp = S.by_id("i4-16-missed")["input"]
    planted = mutant.plant(inp)
    diff = {k for k in inp if inp[k] != planted[k]}
    assert diff == {"config"}
    assert {k for k in inp["config"] if inp["config"][k] != planted["config"][k]} == {"maker_timeout_bars"}
    assert mutant.plant({"op": "metrics", "x": 1}) == {"op": "metrics", "x": 1}
    cur = _current()
    m = mutant.Mutant(cur)
    for sid in ("i4-16-missed", "i4-3-e2e-maker"):
        s = S.by_id(sid)
        assert J.compare(s["expect"], cur.run(s["input"]), s)[0] == "正解と一致"
        assert J.compare(s["expect"], m.run(s["input"]), s)[0] == "不一致", sid
    s = S.by_id("i4-8-next-open")
    assert J.compare(s["expect"], m.run(s["input"]), s)[0] == "正解と一致"


def test_runner_writes_a_row_per_scene_with_reproducibility(tmp_path):
    out = tmp_path / "cur.tsv"
    ids = "i4-4-plain,i4-9-strict,i4-18-refuse,i4-5-fills"
    r = subprocess.run([sys.executable, str(HERE / "run_battery.py"), "--target", "current_impl", "--out", str(out),
                        "--scenes", ids], capture_output=True, text=True, timeout=600, cwd=str(REPO))
    assert r.returncode == 0, r.stderr[-800:]
    rows = [ln.split("\t") for ln in out.read_text(encoding="utf-8").splitlines()[1:]]
    got = {x[0]: (x[3], x[9]) for x in rows}
    assert got["i4-4-plain"] == ("正解と一致", "2 回の実行で同じ")
    assert got["i4-9-strict"] == ("正解と一致", "2 回の実行で同じ")
    assert got["i4-18-refuse"] == ("正解と一致", "2 回の実行で同じ")
    assert got["i4-5-fills"] == ("結果なし", "結果なし")


def test_considered_table_passes_the_checker():
    path = HERE / "opponents" / "CONSIDERED.md"
    r = subprocess.run([sys.executable, str(REPO / "scripts" / "check_bt_considered.py"), str(path)],
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stdout[-1500:]


def test_definitions_are_generated_from_the_scenes():
    before = (HERE / "DEFINITIONS.md").read_text(encoding="utf-8")
    gen = _load(HERE / "gen_definitions.py", "i4_test_gen_definitions")
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        gen.OUT = Path(d) / "DEFINITIONS.md"
        gen.main()
        assert gen.OUT.read_text(encoding="utf-8") == before
