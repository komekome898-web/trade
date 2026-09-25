"""Tests of the item 3 battery itself (場面係の試験, 委任文 §3 場面集の規則 7).

What is checked: the scenes cover every viewpoint with a value scene (rule 3); the expected answers
agree with an independent derivation written here (not with any engine); the judge accepts a correct
observation and rejects a wrong one for every check; the runner runs a target twice and records the
reproducibility cell; the touchstone breaks exactly the scenes its MUTANT text declares; the wiring
breaker acts only when asked; the review table passes scripts/check_bt_considered.py; DEFINITIONS.md
names no tool.
"""
from __future__ import annotations

import copy
import csv
import hashlib
import importlib.util
import itertools
import json
import os
import socket
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(HERE))

import i3_judge as J  # noqa: E402
import i3_scenes as S  # noqa: E402


def test_every_viewpoint_has_a_value_scene_and_ids_are_unique():
    ids = [s["id"] for s in S.SCENES]
    assert len(ids) == len(set(ids))
    for vp in S.VIEWPOINTS:
        kinds = [s["kind"] for s in S.SCENES if s["viewpoint"] == vp]
        assert "値" in kinds, vp
    for s in S.SCENES:
        assert s["kind"] in ("値", "能力") and s["measures"] and s["how"] and s["input"]["op"] and s["expect"]["check"]
        assert ("variant" in s) == ("variant_expect" in s)


# --- independent derivations of the expected answers ---------------------------------------------------
def test_calendar_split_answers_by_zoneinfo():
    for sid, tz in (("v1-split-utc", "UTC"), ("v1-split-jst", "Asia/Tokyo")):
        z = ZoneInfo(tz)
        a = datetime(2026, 1, 7, tzinfo=z).timestamp() * 1e9
        b = datetime(2026, 1, 9, tzinfo=z).timestamp() * 1e9
        rows = S.by_id(sid)["input"]["rows"]
        want = {"train": [t for t in rows if t < a], "val": [t for t in rows if a <= t < b], "oos": [t for t in rows if t >= b]}
        assert S.by_id(sid)["expect"]["parts"] == want
    # the split is not a row-fraction split (the uneven density makes them differ)
    rows = S.SPLIT_ROWS
    assert len(S.by_id("v1-split-utc")["expect"]["parts"]["train"]) != int(len(rows) * 0.6)


def _afml_train(rows, label_end, blocks, embargo_ns):
    """Time form of the purge rule, written independently of i3_scenes (which counts rows):
    for each test block with first time s0 and largest label end e0, a non-test row at time t with label
    end e is dropped when (left) t < s0 < e, (right) its start falls inside the test labels, i.e.
    last test time < t < e0, or (embargo) it starts in [f, f + embargo) where f is the first row time >= e0."""
    keep = []
    for i, (t, e) in enumerate(zip(rows, label_end)):
        drop = any(i in blk for blk in blocks)
        for blk in blocks:
            s0, e0 = rows[blk[0]], max(label_end[j] for j in blk)
            f = min((x for x in rows if x >= e0), default=None)
            if t < s0 < e:
                drop = True
            if rows[blk[-1]] < t < e0:
                drop = True
            if f is not None and f <= t < f + embargo_ns:
                drop = True
        if not drop:
            keep.append(i)
    return keep


def test_purge_embargo_answers_by_interval_rule():
    H = S.H
    assert S.by_id("v2-purge-embargo")["expect"]["train"] == _afml_train(S.PE_ROWS, S.PE_LABEL_END, [list(range(12, 18))], 2 * H)
    assert S.by_id("v2-cpcv-split")["expect"]["train"] == _afml_train(S.PE_ROWS, S.PE_LABEL_END, [S.CPCV_GROUPS[1], S.CPCV_GROUPS[3]], 1 * H)
    e = S.by_id("v2-cpcv-split")["expect"]
    assert e["n_splits"] == len(list(itertools.combinations(range(6), 2))) and e["n_paths"] == 2 * 15 // 6


def test_closed_forms_against_published_constants():
    # z(0.975) = 1.959964, z(0.8) = 0.841621 (standard normal tables)
    assert S.by_id("v4-mde-two-sided")["expect"]["values"]["mde"] == pytest.approx((1.959964 + 0.841621) * 10 / 20, rel=1e-6)
    # z(0.99) = 2.326348, z(0.9) = 1.281552
    assert S.by_id("v4-mde-one-sided")["expect"]["values"]["mde"] == pytest.approx((2.326348 + 1.281552) * 5 / 10, rel=1e-6)
    assert S.PBO_VALUE == 0.5 and [x["oos_rank"] for x in S.PBO_LAMBDAS] == [3, 3, 2, 3, 1, 2]


def test_bootstrap_band_excludes_the_iid_answer():
    e = S.by_id("v3-block-bootstrap")["expect"]
    assert S.BOOT_SE_IID / e["se"] < e["width_band"][0]


def test_dsr_tolerance_excludes_a_dropped_variance_term():
    sr, sk, ku = S._moments(S.DSR_X)
    T = len(S.DSR_X)
    wrong = S.dsr(sr, T, sk, ku - 2.0, 10, 1 / T)  # (kurtosis - 3)/4 in place of (kurtosis - 1)/4
    assert abs(wrong - S.DSR_R_VALUE) > S.DSR_R_TOL


def test_fixed_run_answers():
    legs = S.LEGS
    bp = [(legs[i + 1][2] - legs[i][2]) / legs[i][2] * 1e4 for i in range(0, 6, 2)]
    assert bp == pytest.approx(S.RUN_BP, abs=1e-9)
    assert S.by_id("v7-data-sha256")["expect"]["value"] == {"data/tape.csv": hashlib.sha256(S.TAPE.encode()).hexdigest()}


# --- the judge -----------------------------------------------------------------------------------------
def _paths(G=6, K=2):
    splits = list(itertools.combinations(range(G), K))
    per_group = {g: [sp for sp in splits if g in sp] for g in range(G)}
    n = len(per_group[0])
    return [[{"split": list(per_group[g][p]), "group": g} for g in range(G)] for p in range(n)]


def oracle(scene, variant=False):
    """An observation that satisfies the scene's expected answer (built from the answer)."""
    if variant:
        ve = scene["variant_expect"]
        return ve.get("equal") or ve.get("refuse_or_equal")
    e = scene["expect"]
    c = e["check"]
    if c == "parts":
        return {"parts": copy.deepcopy(e["parts"])}
    if c == "folds":
        return {"folds": copy.deepcopy(e["folds"])}
    if c == "fold_evals":
        return {"folds": copy.deepcopy(e["folds"])}
    if c == "index_set":
        return {"train_idx": list(e["train"])}
    if c == "cpcv_split":
        return {"n_splits": e["n_splits"], "n_paths": e["n_paths"], "train_idx": list(e["train"])}
    if c == "cpcv_paths":
        return {"paths": _paths()}
    if c == "ci_band":
        return {"ci": [e["mean"] - 1.959963984540054 * e["se"], e["mean"] + 1.959963984540054 * e["se"]]}
    if c in ("close", "equal"):
        return copy.deepcopy(e["values"])
    if c == "record":
        v = J.git_head() if isinstance(e["value"], dict) and e["value"].get("oracle") == "git_head" else e["value"]
        return {"record": {e["field"]: copy.deepcopy(v)}}
    if c == "record_stable_hex":
        return {"records": [{e["field"]: "ab" * 16}, {e["field"]: "ab" * 16}]}
    if c == "record_nonempty":
        return {"record": {e["field"]: "1.0"}}
    if c == "id_relations":
        ids = [None] * 5
        for gi, grp in enumerate(e["groups"]):
            for i in grp:
                ids[i] = f"id{gi}"
        return {"ids": ids}
    if c == "exports_purpose":
        return {"exports": {"runs/x/metrics.json": e["value"]}}
    if c.startswith("dash_"):
        texts = {t: f"{t} {S.WARNING}" for t in S.TABS}
        return {"run_ids": {"A": "rA", "B": "rB"}, "top_tabs": ["Botコンソール", "バックテスト"], "run_list": ["rA", "rB"],
                "run_tabs": {"rA": list(S.TABS), "rB": list(S.TABS)},
                "tab_text": {"rA": texts, "rB": {t: t for t in S.TABS}},
                "values": {"rA": {"per_trade_bp": list(S.RUN_BP), "neg_frac": 1 / 3}}}
    raise AssertionError(c)


def corrupt(obs, check=""):
    """A silently wrong version of an observation (one value moved, in the part the check reads)."""
    o = copy.deepcopy(obs)
    if check == "record_nonempty":
        return {"record": {k: "" for k in o["record"]}}
    if check == "dash_run_tabs":
        o["run_tabs"]["rA"] = o["run_tabs"]["rA"][1:] + o["run_tabs"]["rA"][:1]
        return o
    if check == "dash_japanese":
        o["run_tabs"]["rA"][0] = "Overview"
        return o
    if check == "dash_values":
        o["values"]["rA"]["neg_frac"] = 0.5
        return o
    if check == "dash_warning":
        o["tab_text"]["rB"]["概要"] = "概要 " + S.WARNING
        return o
    s = json.dumps(o, ensure_ascii=False)
    for a, b in (('"バックテスト"', '"Backtest"'), ("動作確認の実行", "動作"), ('"陰性"', '"陽性"'), ("true", "false"), ('"id2"', '"id0"'),
                 ('"研究"', '"動作確認"'), ('"動作確認"', '"研究"')):
        if a in s:
            return json.loads(s.replace(a, b, 1))

    def bump(x):
        if isinstance(x, bool):
            return not x
        if isinstance(x, (int, float)):
            return x + 1
        if isinstance(x, str):
            return x + "x"
        if isinstance(x, list):
            return [bump(x[0])] + x[1:] if x else [1]
        if isinstance(x, dict):
            k = next(iter(x))
            return {**x, k: bump(x[k])}
        return x

    return bump(o)


@pytest.mark.parametrize("sid", [s["id"] for s in S.SCENES])
def test_judge_accepts_the_answer_and_rejects_a_wrong_value(sid):
    sc = S.by_id(sid)
    good = oracle(sc)
    assert J.compare(sc["expect"], good, sc) == ("正解と一致", ""), sid
    cls, _ = J.compare(sc["expect"], corrupt(good, sc["expect"]["check"]), sc)
    assert cls == "不一致", (sid, cls)
    if "variant" in sc:
        ve = sc["variant_expect"]
        if "refuse" in ve:
            assert J.variant_outcome(ve, "refused", "x")[0] == "正解と一致"
            assert J.variant_outcome(ve, "ok", {})[0] == "不一致"
        else:
            assert J.variant_outcome(ve, "ok", oracle(sc, variant=True))[0] == "正解と一致"
            assert J.variant_outcome(ve, "ok", corrupt(oracle(sc, variant=True)))[0] == "不一致"


def test_judge_missing_key_is_no_result_and_wrong_key_wins():
    sc = S.by_id("v14-cost-breakdown")
    assert J.compare(sc["expect"], {}, sc)[0] == "結果なし"
    sc = S.by_id("v2-cpcv-split")
    assert J.compare(sc["expect"], {"n_splits": 15, "train_idx": sc["expect"]["train"]}, sc)[0] == "結果なし"
    assert J.compare(sc["expect"], {"n_splits": 14, "train_idx": sc["expect"]["train"]}, sc)[0] == "不一致"


def test_stable_view_keeps_equality_of_run_ids():
    a = {"ids": ["x1", "x1", "x2"], "record": {"git_sha": "abc", "diff_hash": "d"}}
    b = {"ids": ["y9", "y9", "y7"], "record": {"git_sha": "def", "diff_hash": "e"}}
    c = {"ids": ["y9", "y7", "y7"], "record": {"git_sha": "def", "diff_hash": "e"}}
    assert J.digest(a) == J.digest(b) != J.digest(c)


# --- the runner ----------------------------------------------------------------------------------------
def test_runner_runs_twice_and_records_the_cells(tmp_path):
    out = tmp_path / "cur.tsv"
    r = subprocess.run([sys.executable, str(HERE / "run_battery.py"), "--target", "current_impl", "--out", str(out),
                        "--scenes", "v14-dd-pct,a6-sealed-token,v1-split-utc"], cwd=str(REPO), capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stderr[-800:]
    rows = {x["scene"]: x for x in csv.DictReader(open(out, encoding="utf-8"), delimiter="\t")}
    assert rows["v14-dd-pct"]["class_1"] == rows["v14-dd-pct"]["class_2"] == "正解と一致"
    assert rows["a6-sealed-token"]["class_1"] == "正解と一致"
    assert rows["v1-split-utc"]["class_1"] == "結果なし"
    assert all(x["repro"] in ("2 回の実行で同じ", "結果なし") for x in rows.values())


# --- the touchstone ------------------------------------------------------------------------------------
class _Oracle:
    """A correct engine for the ops the touchstone touches, written from the interval rule above."""
    name = "oracle"

    def run(self, inp):
        rows, le = inp["rows"], inp["label_end"]
        if inp["op"] == "purged_split":
            return {"train_idx": _afml_train(rows, le, [inp["test_rows"]], inp["embargo_ns"])}
        if inp["op"] == "cpcv":
            g = len(rows) // inp["n_groups"]
            blocks = [list(range(k * g, (k + 1) * g)) for k in sorted(inp["want_train_for"])]
            return {"n_splits": 15, "n_paths": 5, "train_idx": _afml_train(rows, le, blocks, inp["embargo_ns"])}
        if inp["op"] == "cpcv_paths":
            return {"paths": _paths()}
        raise AssertionError(inp["op"])


def test_mutant_breaks_exactly_the_declared_scenes(monkeypatch):
    spec = importlib.util.spec_from_file_location("i3_mutant_under_test", HERE / "mutant.py")
    mut = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mut)
    monkeypatch.setattr(mut._base, "TARGET", _Oracle())
    for sid in ("v2-purge-embargo", "v2-cpcv-split", "a2-cpcv-paths"):
        sc = S.by_id(sid)
        inp = dict(sc["input"], root="/nonexistent")
        good = J.compare(sc["expect"], _Oracle().run(inp), sc)[0]
        bad = J.compare(sc["expect"], mut.TARGET.run(inp), sc)[0]
        assert good == "正解と一致", sid
        assert bad == ("正解と一致" if sid == "a2-cpcv-paths" else "不一致"), sid
    # every other request passes through unchanged
    for s in S.SCENES:
        if s["input"]["op"] not in mut.AFFECTED_OPS:
            assert mut.plant(s["input"]) == s["input"]


# --- the wiring breaker --------------------------------------------------------------------------------
SERVER = r'''
import http.server, socketserver, sys
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = ("<nav><button>バックテスト</button></nav>" if self.path == "/" else '{"runs": []}').encode("utf-8")
        self.send_response(200); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def log_message(self, *a): pass
s = http.server.HTTPServer(("127.0.0.1", int(sys.argv[1])), H)
s.handle_request(); s.handle_request()
'''


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.mark.parametrize("mode", ["", "api_route", "tab_label"])
def test_wiring_breaker(mode, tmp_path):
    import urllib.error
    import urllib.request
    port = _free_port()
    env = dict(os.environ, PYTHONPATH=str(HERE / "wiring_break"))
    env.pop("I3_WIRING_BREAK", None)
    if mode:
        env["I3_WIRING_BREAK"] = mode
    p = subprocess.Popen([sys.executable, "-c", SERVER, str(port)], env=env)
    try:
        for _ in range(50):
            try:
                html = urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=2).read().decode("utf-8")
                break
            except OSError:
                time.sleep(0.1)
        try:
            api = urllib.request.urlopen(f"http://127.0.0.1:{port}/api/backtest/runs", timeout=2).status
        except urllib.error.HTTPError as exc:
            api = exc.code
    finally:
        p.wait(timeout=10)
    assert ("バックテスト" in html) == (mode != "tab_label")
    assert api == (404 if mode == "api_route" else 200)


# --- the review table and the definitions ---------------------------------------------------------------
def test_considered_table_passes_the_checker():
    r = subprocess.run([sys.executable, str(REPO / "scripts" / "check_bt_considered.py"), str(HERE / "opponents" / "CONSIDERED.md")],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout[-1500:]


def test_definitions_are_generated_and_name_no_tool():
    text = (HERE / "DEFINITIONS.md").read_text(encoding="utf-8")
    for s in S.SCENES:
        assert f"#### {s['id']}" in text
    for name in ("mlflow", "freqtrade", "homerun", "PySystemtrade", "BacktestingCore", "TradeSight", "OpenTrader", "sigc",
                 "pybotters", "polymarket", "limitOrderBook", "order-book-simulator", "Luczinsritter", "Jesse", "BacktestingMax"):
        assert name.lower() not in text.lower(), name
