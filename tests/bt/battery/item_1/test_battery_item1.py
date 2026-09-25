"""Item 1 battery (データと時刻): tests of the battery itself (scene-keeper's tests).

- the scenes cover every viewpoint of REQUIREMENTS.md §2 with a value scene;
- the expected answers are what an independent reading of the written text gives
  (decimal epochs through Fraction, ISO texts through a regex on the digits, the
  V7 rule on the exact binary values), and the fractional V7 scene has no near-tie;
- the judge accepts an observation equal to the expected answer and rejects each
  single perturbation (1 ns, one field missing, one path differing in one bit,
  a slower vector path, a variant not refused);
- the touchstone plants its defect in exactly the scenes it names, and nowhere else;
- the runner runs the current state and records both runs;
- the review table of the unrunnable candidates passes scripts/check_bt_considered.py.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import re
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(HERE))

import i1_judge as J  # noqa: E402
import i1_scenes as S  # noqa: E402

NS = 1_000_000_000


def perfect(scene: dict) -> dict:
    """An observation equal to the expected answer (records carry exactly the expected keys)."""
    exp = S.expected(scene)
    obs: dict = {}
    for k, v in exp.items():
        if k == "paths":
            obs["paths"] = {"event": copy.deepcopy(v), "vector": copy.deepcopy(v)}
        elif k == "speed":
            obs["timing"] = {"event_s": 2.0, "vector_s": 1.0}
        else:
            obs[k] = copy.deepcopy(v)
    return obs


# ---------------------------------------------------------------- coverage (rule 3)
def test_every_viewpoint_has_a_value_scene_and_ids_are_unique():
    ids = [s["id"] for s in S.SCENES]
    assert len(ids) == len(set(ids))
    for vp in S.VIEWPOINTS:
        kinds = {s["kind"] for s in S.SCENES if s["viewpoint"] == vp}
        assert "値" in kinds, vp
    for s in S.SCENES:
        assert s["id"].startswith(s["viewpoint"].lower() + "-")
        assert s["what"] and s["how"] and "expect" in s and "input" in s


def test_capability_scenes_are_judged_by_results_too():
    """Rule 1: a capability scene has an expected RESULT (not just 'ran')."""
    for s in S.SCENES:
        if s["kind"] == "能力":
            exp = S.expected(s)
            assert exp and all(v not in (None, {}, []) for v in exp.values()), s["id"]


# ---------------------------------------------------------------- oracle, read independently
_ISO = re.compile(r"^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})(?::(\d{2})(?:\.(\d+))?)?(Z|[+-]\d{2}:?\d{2})?$")


def _iso_ns(text: str, naive_offset_h: int = 0) -> int:
    m = _ISO.match(text)
    assert m, text
    y, mo, d, h, mi, s, frac, off = m.groups()
    ns = S.ns(int(y), int(mo), int(d), int(h), int(mi), int(s or 0), int((frac or "0").ljust(9, "0")[:9]))
    if off in (None, ""):
        return ns - naive_offset_h * 3600 * NS
    if off == "Z":
        return ns
    sign = 1 if off[0] == "+" else -1
    hh, mm = int(off[1:3]), int(off[-2:])
    return ns - sign * (hh * 3600 + mm * 60) * NS


def _cells(scene, ds_name):
    ds = next(d for d in scene["input"]["datasets"] if d["name"] == ds_name)
    f = next(f for f in scene["input"]["files"] if f["path"] == ds["paths"][0])
    sp = ds["spec"]
    lines = f["text"].strip("\n").split("\n")
    names = lines[0].split(sp["delimiter"]) if sp.get("header", True) else sp["names"]
    body = lines[1:] if sp.get("header", True) else lines
    return sp, [dict(zip(names, ln.split(sp["delimiter"]))) for ln in body]


def test_v2_decimal_and_iso_texts_read_back_to_the_expected_ns():
    sc = next(s for s in S.SCENES if s["id"] == "v2-same-instant-4-units")
    per = {"s": NS, "ms": 10**6, "us": 10**3, "ns": 1}
    for ds in sc["input"]["datasets"]:
        sp, rows = _cells(sc, ds["name"])
        unit = sp["time"]["unit"]
        got = [int(Fraction(r["t"]) * per[unit]) if unit != "iso" else _iso_ns(r["t"]) for r in rows]
        assert got == [e["t_ns"] for e in sc["expect"]["events"][ds["name"]]], ds["name"]
    sc = next(s for s in S.SCENES if s["id"] == "v2-iso-offsets")
    _, rows = _cells(sc, "iso_forms")
    assert {_iso_ns(r["t"]) for r in rows} == {sc["expect"]["events"]["iso_forms"][0]["t_ns"]}
    assert len({r["t"] for r in rows}) == len(rows)  # six different spellings


def test_local_zone_scenes_are_nine_hours_behind_the_wall_clock():
    sc = next(s for s in S.SCENES if s["id"] == "v2-naive-local-tz")
    _, rows = _cells(sc, "jst_trades")
    assert [_iso_ns(r["t"], 9) for r in rows] == [e["t_ns"] for e in sc["expect"]["events"]["jst_trades"]]
    _, rows = _cells(sc, "jst_bars")
    assert [_iso_ns(r["date"] + " " + r["time"], 9) for r in rows] == [e["start_ns"] for e in sc["expect"]["events"]["jst_bars"]]


def test_v1_generic_shapes_read_back_by_their_own_spec():
    sc = next(s for s in S.SCENES if s["id"] == "v1-generic-shape")
    per = {"s": NS, "ms": 10**6, "us": 10**3, "ns": 1}
    delims, units = set(), set()
    for ds in sc["input"]["datasets"]:
        sp, rows = _cells(sc, ds["name"])
        f = sp["fields"]
        unit, tcol = sp["time"]["unit"], sp["time"]["columns"][0]
        delims.add(sp["delimiter"])
        units.add(unit)
        got = [{"t_ns": _iso_ns(r[tcol]) if unit == "iso" else int(Fraction(r[tcol]) * per[unit]),
                "px": float(r[f["px"]]), "qty": float(r[f["qty"]]), "side": r[f["side"]].lower(), "id": r[f["id"]]} for r in rows]
        assert got == sc["expect"]["events"][ds["name"]]
    assert units == {"s", "ms", "us", "ns", "iso"}


def test_v7_rule_on_the_exact_binary_values_and_no_near_tie():
    sc = next(s for s in S.SCENES if s["id"] == "v7-rule-fractional")
    closes = [Fraction(b["close"]) for b in sc["input"]["bars"]]
    for t in range(2, len(closes)):
        assert abs(closes[t] - sum(closes[t - 2:t + 1]) / 3) >= Fraction(33, 1000)
    exp = sc["expect"]["paths"]
    pos, eq = [], [Fraction(1_000_000)]
    for t, c in enumerate(closes):
        m = sum(closes[t - 2:t + 1]) / 3 if t >= 2 else None
        pos.append(1 if m is not None and c > m else 0)
        if t:
            eq.append(eq[-1] + pos[t - 1] * (c - closes[t - 1]))
    assert exp["position"] == pos and exp["equity"] == [float(x) for x in eq]


def test_v7_bars_follow_the_bucket_definition_at_the_edges():
    sc = next(s for s in S.SCENES if s["id"] == "v7-bars-from-trades")
    starts = [b["start_ns"] for b in sc["expect"]["paths"]["bars"]]
    assert starts == [S.T0 + k * 60 * NS for k in (0, 1, 3, 4)]  # the empty minute 2 makes no bar
    b4 = sc["expect"]["paths"]["bars"][-1]
    assert (b4["open"], b4["close"], b4["volume"]) == (104.0, 106.0, 1.25)


def test_v6_expected_values_are_exact_ratios():
    sc = next(s for s in S.SCENES if s["id"] == "v6-split")
    raw = [b for b in sc["input"]["bars"] if b["date"] < "2026-01-08"]
    adj = sc["expect"]["adjusted"]["1001"][:len(raw)]
    assert [a["close"] * 2 for a in adj] == [float(b["close"]) for b in raw]
    assert [a["volume"] / 2 for a in adj] == [float(b["volume"]) for b in raw]


def test_v4_expected_hash_is_of_the_written_bytes():
    import gzip
    import hashlib
    sc = next(s for s in S.SCENES if s["id"] == "v4-sha256-values")
    h = S.expected(sc)["hashes"]
    for f in sc["input"]["files"]:
        data = f["text"].encode()
        data = gzip.compress(data, mtime=0) if f.get("gzip") else data
        assert h[f["path"]] == hashlib.sha256(data).hexdigest()
    sc = next(s for s in S.SCENES if s["id"] == "v4-sha256-distinguishes")
    h = list(S.expected(sc)["hashes"].values())
    assert h[0] == h[1] != h[2]


def test_every_scene_materializes_and_every_dataset_path_exists(tmp_path):
    import os
    sys.path.insert(0, str(HERE))
    import run_battery as R
    for sc in S.SCENES:
        for inp in [sc["input"]] + ([sc["variant"]] if "variant" in sc else []):
            if not inp.get("files"):
                continue
            root = R.materialize(inp, str(tmp_path))
            for ds in inp["datasets"]:
                for p in ds["paths"]:
                    assert os.path.isfile(os.path.join(root, p)), (sc["id"], p)
    link = next(s for s in S.SCENES if s["id"] == "v5-reject-symlink")
    root = R.materialize(link["variant"], str(tmp_path))
    assert os.path.islink(os.path.join(root, "backtest_data", "bf_exec_link_synth"))
    assert "qa_" in os.path.realpath(os.path.join(root, link["variant"]["datasets"][0]["paths"][0]))


def test_board_blank_levels_are_absent_not_zero():
    sc = next(s for s in S.SCENES if s["id"] == "v1-bitflyer-board-top10")
    recs = sc["expect"]["events"]["board"]
    assert [len(r["bids"]) for r in recs] == [10, 3] and [len(r["asks"]) for r in recs] == [10, 2]
    obs = perfect(sc)
    obs["events"]["board"][1]["bids"].append([0.0, 0.0])
    assert J.compare(S.expected(sc), obs, sc)[0] == "不一致"


# ---------------------------------------------------------------- judge
@pytest.mark.parametrize("scene", S.SCENES, ids=[s["id"] for s in S.SCENES])
def test_judge_accepts_the_expected_answer(scene):
    assert J.compare(S.expected(scene), perfect(scene), scene) == ("正解と一致", "")


def _first_time_record(obs):
    for key in ("events",):
        for recs in (obs.get(key) or {}).values():
            for r in recs:
                for k in ("t_ns", "start_ns"):
                    if k in r:
                        return r, k
    return None, None


@pytest.mark.parametrize("scene", [s for s in S.SCENES if "events" in s["expect"]], ids=lambda s: s["id"])
def test_judge_rejects_one_nanosecond_off(scene):
    obs = perfect(scene)
    rec, k = _first_time_record(obs)
    rec[k] += 1
    assert J.compare(S.expected(scene), obs, scene)[0] == "不一致"


@pytest.mark.parametrize("scene", [s for s in S.SCENES if "paths" in s["expect"]], ids=lambda s: s["id"])
def test_judge_rejects_paths_that_differ_in_one_bit(scene):
    import struct
    obs = perfect(scene)
    nudge = lambda x: struct.unpack("<d", (struct.unpack("<q", struct.pack("<d", x))[0] + 1).to_bytes(8, "little", signed=True))[0]  # noqa: E731
    vec = obs["paths"]["vector"]
    key = next((k for k in vec if k != "bars"), "bars")
    if key == "bars":
        vec["bars"][-1]["close"] = nudge(vec["bars"][-1]["close"])
    else:
        seq = vec[key]
        i = next(i for i, x in enumerate(seq) if isinstance(x, float))
        seq[i] = nudge(seq[i])
    assert J.compare(S.expected(scene), obs, scene)[0] == "不一致"


def test_judge_rejects_a_slower_vector_path_and_missing_anomalies():
    sc = next(s for s in S.SCENES if s["id"] == "v7-speed")
    obs = perfect(sc)
    obs["timing"] = {"event_s": 1.0, "vector_s": 1.0}
    assert J.compare(S.expected(sc), obs, sc)[0] == "不一致"
    sc = next(s for s in S.SCENES if s["id"] == "v3-gap-bars")
    assert J.compare(S.expected(sc), {"events": {}}, sc)[0] == "不一致"
    obs = perfect(sc)
    obs["anomalies"]["gap"].pop()
    assert J.compare(S.expected(sc), obs, sc)[0] == "不一致"


def test_judge_rejects_a_missing_field_and_a_wrong_type():
    sc = next(s for s in S.SCENES if s["id"] == "v1-bitflyer-rest")
    obs = perfect(sc)
    del obs["events"]["bf_rest"][0]["px"]
    assert J.compare(S.expected(sc), obs, sc)[0] == "不一致"
    obs = perfect(sc)
    obs["events"]["bf_rest"][0]["t_ns"] = float(obs["events"]["bf_rest"][0]["t_ns"])
    assert J.compare(S.expected(sc), obs, sc)[0] == "不一致"
    obs = perfect(sc)
    obs["events"]["bf_rest"][0]["id"] = int(obs["events"]["bf_rest"][0]["id"])
    assert J.compare(S.expected(sc), obs, sc)[0] == "不一致"


def test_digest_ignores_timings_only():
    a = {"paths": {"event": {"sma": [1.0]}}, "timing": {"event_s": 1.0}}
    b = {"paths": {"event": {"sma": [1.0]}}, "timing": {"event_s": 9.0}}
    c = {"paths": {"event": {"sma": [1.0000000000000002]}}, "timing": {"event_s": 1.0}}
    assert J.digest(a) == J.digest(b) != J.digest(c)


# ---------------------------------------------------------------- touchstone
def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_mutant_breaks_exactly_the_scenes_it_names():
    M = _load(HERE / "mutant.py", "i1_mutant_under_test")
    named = set(re.findall(r"(v\d-[a-z0-9-]+)", M.__doc__.split("Scenes whose answer this must break", 1)[1].split("All other")[0]))
    broken = set()
    for sc in S.SCENES:
        obs = M.plant(sc["input"], perfect(sc))
        if J.compare(S.expected(sc), obs, sc)[0] != "正解と一致":
            broken.add(sc["id"])
    assert broken == named and broken


def test_new_impl_is_the_mouth_only():
    N = _load(HERE / "adapters" / "new_impl.py", "i1_new_impl_under_test")
    from i1_protocol import NotExpressible
    with pytest.raises(NotExpressible):
        N.TARGET.run(S.SCENES[0]["input"])


# ---------------------------------------------------------------- runner and review table
def test_runner_runs_twice_and_records_both(tmp_path):
    out = tmp_path / "cur.tsv"
    r = subprocess.run([sys.executable, str(HERE / "run_battery.py"), "--target", "current_impl", "--out", str(out),
                        "--scenes", "v5-sealed-window,v2-iso-offsets,v6-split"], capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stderr[-800:]
    rows = {ln.split("\t")[0]: ln.split("\t") for ln in out.read_text(encoding="utf-8").splitlines()[1:]}
    assert rows["v5-sealed-window"][3] == rows["v5-sealed-window"][6] == "正解と一致"
    assert rows["v5-sealed-window"][9] == "2 回の実行で同じ"
    assert rows["v6-split"][3] == "結果なし" and rows["v6-split"][9] == "結果なし"
    assert len(out.with_suffix(".obs.jsonl").read_text(encoding="utf-8").splitlines()) == 3


def test_reproductions_refuse_what_their_source_refuses():
    from i1_protocol import Refused
    sys.path.insert(0, str(HERE / "opponents"))
    r105 = _load(HERE / "opponents" / "repro_105_duplicate_bars.py", "i1_r105")
    r23 = _load(HERE / "opponents" / "repro_23_event_order.py", "i1_r23")
    import tempfile
    import os
    for mod, sid in ((r105, "v3-generations"), (r23, "v3-backward")):
        sc = next(s for s in S.SCENES if s["id"] == sid)
        inp = copy.deepcopy(sc["input"])
        root = tempfile.mkdtemp()
        for f in inp["files"]:
            p = os.path.join(root, f["path"])
            os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, "wb").write(S.file_bytes(f))
        inp["root"] = root
        with pytest.raises(Refused):
            mod.TARGET.run(inp)


def test_considered_table_passes_the_checker():
    r = subprocess.run([sys.executable, str(REPO / "scripts" / "check_bt_considered.py"), str(HERE / "opponents" / "CONSIDERED.md")],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout[-1500:]


def test_definitions_are_generated_from_the_scenes():
    """DEFINITIONS.md lists every scene id (it is written by gen_definitions.py from i1_scenes)."""
    text = (HERE / "DEFINITIONS.md").read_text(encoding="utf-8")
    for s in S.SCENES:
        assert f"`{s['id']}`" in text, s["id"]
    r = subprocess.run([sys.executable, str(HERE / "gen_definitions.py"), "--check"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout[-800:] + r.stderr[-800:]
