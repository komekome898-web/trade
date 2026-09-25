"""Tests of the item 2 battery itself (場面集の規則 1-9 that a machine can check)."""
from __future__ import annotations

import copy
import csv
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(HERE))

import i2_judge as J  # noqa: E402
import i2_scenes as S  # noqa: E402

VIEWPOINTS = [f"C2-{i}" for i in range(1, 13)]


def test_scene_ids_unique_and_well_formed():
    ids = [s["id"] for s in S.SCENES]
    assert len(ids) == len(set(ids))
    for s in S.SCENES:
        assert s["viewpoint"] in VIEWPOINTS
        assert s["kind"] in ("値", "能力")
        assert s["measures"] and s["derivation"] and s["title"]


def test_every_viewpoint_has_a_value_scene():
    """場面集の規則 3: each viewpoint has at least one value scene."""
    for vp in VIEWPOINTS:
        kinds = [s["kind"] for s in S.SCENES if s["viewpoint"] == vp]
        assert "値" in kinds, vp


def test_nouns_point_to_existing_scenes_and_cover_all_scenes():
    ids = {s["id"] for s in S.SCENES}
    covered = set()
    for vp in VIEWPOINTS:
        assert vp in S.NOUNS, vp
        for noun, scenes in S.NOUNS[vp].items():
            assert scenes, noun
            for sid in scenes:
                assert sid in ids, (noun, sid)
                covered.add(sid)
    assert covered == ids, ids - covered


def test_oracles_are_deterministic_and_do_not_touch_any_engine():
    src = (HERE / "i2_scenes.py").read_text(encoding="utf-8")
    assert not re.search(r"^\s*(import|from)\s+(bot|src|backtrader|zipline|hftbacktest)", src, re.M)
    for s in S.SCENES:
        a = S.expected(s)
        b = S.expected(copy.deepcopy(s))
        assert a == b and a, s["id"]


def test_expected_keys_are_known_to_the_judge():
    heads = {"status", "filled", "avg_px", "first_fill_t", "cum", "fee", "lat_in", "sent", "notice", "seen",
             "account", "costs", "range"}
    for s in S.SCENES:
        for k in S.expected(s):
            assert k.split(".")[0] in heads, (s["id"], k)


def test_variant_scenes_differ_from_control():
    for s in S.SCENES:
        if "variant" in s:
            assert s["variant"] != s["input"], s["id"]


def test_value_scenes_hand_checks():
    """A few closed forms re-derived here independently of the oracle functions."""
    e = S.expected(S.by_id("c2-7-walk"))
    assert e["avg_px.o1"] == pytest.approx((0.5 * 10001 + 0.7 * 10002 + 0.3 * 10005) / 1.5)
    e = S.expected(S.by_id("c2-6-prob-power2"))
    front = 5 - (25 / 34) * 4 + min(3 - (9 / 34) * 4, 0)
    assert e["filled.o1"] == pytest.approx(min(3, 4.5 - front))
    e = S.expected(S.by_id("c2-5-queue-value"))
    assert (e["cum.o1@c1"], e["cum.o1@c2"], e["cum.o1@c3"]) == pytest.approx((0.0, 0.2, 0.6))
    e = S.expected(S.by_id("c2-11-liquidation"))
    assert e["account.realized"] == pytest.approx((6000 - 10001) * 0.19)
    e = S.expected(S.by_id("c2-10-taker"))
    assert e["fee.o1"] == pytest.approx(0.0005 * 10001)
    e = S.expected(S.by_id("c2-10-spread"))
    assert e["avg_px.o1"] == 10001.0


def _obs_from_expected(scene):
    """An observation that a correct engine would give for the simple keys of `scene` (test helper)."""
    exp = S.expected(scene)
    orders, fills = {}, []
    refs = {k.split(".", 1)[1] for k in exp if k.split(".")[0] in ("status", "filled", "avg_px", "fee")}
    for ref in refs:
        st = exp.get(f"status.{ref}", "filled")
        orders[ref] = {"status": st if isinstance(st, str) else st["v"][0]}
        q = exp.get(f"filled.{ref}", 1.0)
        if q:
            act = S.action(scene["input"], ref)
            fills.append({"ref": ref, "t": act["t"], "px": exp.get(f"avg_px.{ref}", 1.0), "qty": q,
                          "fee": exp.get(f"fee.{ref}", 0.0), "liq": "taker" if act["type"] == "market" else "maker"})
    return {"orders": orders, "fills": fills}


def test_judge_accepts_a_faithful_observation_and_rejects_a_perturbed_one():
    s = S.by_id("c2-10-taker")
    obs = _obs_from_expected(s)
    assert J.compare(S.expected(s), obs, s["input"])[0] == "正解と一致"
    bad = copy.deepcopy(obs)
    bad["fills"][0]["px"] += 1.0
    assert J.compare(S.expected(s), bad, s["input"])[0] == "不一致"
    missing = {"orders": obs["orders"], "fills": []}
    assert J.compare(S.expected(s), missing, s["input"])[0] == "不一致"


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_mutant_breaks_taker_fee_scenes_and_leaves_others():
    """The touchstone's planted defect must turn a correct taker-fee answer into 不一致 and leave a
    scene without a taker fill unchanged (its correctness differs from the new implementation only there)."""
    M = _load(HERE / "mutant.py", "i2_mutant_test")
    for sid in ("c2-10-taker", "c2-11-legs"):
        s = S.by_id(sid)
        obs = _obs_from_expected(s)
        assert J.compare(S.expected(s), obs, s["input"])[0] == "正解と一致", sid
        bad = M.plant(s["input"], copy.deepcopy(obs))
        assert J.compare(S.expected(s), bad, s["input"])[0] == "不一致", sid
    s = S.by_id("c2-10-maker")
    obs = _obs_from_expected(s)
    assert M.plant(s["input"], copy.deepcopy(obs)) == obs
    assert M.MUTANT


def test_definitions_is_generated_and_names_no_tool():
    r = subprocess.run([sys.executable, str(HERE / "gen_definitions.py"), "--check"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    text = (HERE / "DEFINITIONS.md").read_text(encoding="utf-8")
    body = text[: text.index("## 提出前の吟味")] if "## 提出前の吟味" in text else text
    with open(REPO / "docs/DATA/tools_catalog.tsv", encoding="utf-8") as fh:
        names = [r[1] for r in csv.reader(fh, delimiter="\t")][1:]
    words = set()
    for n in names:
        for w in re.split(r"[ /()（）]", n):
            if len(w) >= 5 and not re.fullmatch(r"[\d.:]+", w):
                words.add(w.lower())
    # generic words inside repository names are not names of a tool
    words -= {"python3", "info.license", "backtest", "backtesting", "trading", "market", "engine", "simulator",
              "order", "orderbook", "limit", "matching", "automated", "financial", "system", "optimal", "execution",
              "impact", "model", "slippage", "event_driven_backtesting_engine", "awesome", "quant", "systematic"}
    low = body.lower()
    hits = sorted(w for w in words if w in low)
    assert not hits, hits


def test_adapters_do_not_read_the_answer():
    for p in list((HERE / "adapters").glob("*.py")) + list((HERE / "opponents").glob("*.py")):
        src = p.read_text(encoding="utf-8")
        assert "expected(" not in src and "i2_scenes" not in src.split('"""', 2)[-1], p.name
        assert not re.search(r"['\"]c2-\d+-", src), p.name  # no scene id special-casing


def test_runner_repro_cell():
    R = _load(HERE / "run_battery.py", "i2_runner_test")
    a = {"class": "正解と一致", "digest": "x"}
    assert R.repro_cell(a, dict(a)) == "2 回の実行で同じ"
    assert R.repro_cell(a, {"class": "正解と一致", "digest": "y"}).startswith("2 回で違う")
    assert R.repro_cell({"class": "結果なし", "digest": "-"}, {"class": "結果なし", "digest": "-"}) == "結果なし"


def test_pool_is_machine_extracted_and_current():
    r = subprocess.run([sys.executable, str(HERE / "gen_pool.py")], capture_output=True, text=True, cwd=str(REPO))
    assert r.returncode == 0, r.stderr
    rows = list(csv.DictReader(open(HERE / "pool.tsv", encoding="utf-8"), delimiter="\t"))
    assert rows and all(row["rule"] for row in rows)
