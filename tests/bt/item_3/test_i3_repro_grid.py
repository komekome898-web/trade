"""Adversarial grids for the reproducibility rules (item 3, old item 8) and
the purpose rule of the exports (old item 9, 委任文 §4).

Grids:
  identity      every key order of the config's top level (6! = 720) and
                of each nested mapping -> one id; each single change of an
                identity field (every config leaf, seed, data bytes, data
                declaration, setup, purpose, pre-registration bytes, git
                sha, diff hash, version) -> a new id, all pairwise distinct.
  purpose x prereg   {動作確認, 研究, None, "research", "", 1} x {none, a file,
                an empty file, a missing file} -> accepted exactly where the
                rule says.
  two runs      setup x seed: fixed and seeded setups reproduce; the unseeded
                one is caught (check says False, run refuses, nothing kept).
  place         the same run under two different roots -> same id, same bytes.
  code state    a scratch git repository: clean / edited tracked file /
                new untracked file / reverted -> the diff hash follows.
  config        every missing key, an unknown key, and bad values -> refused.

Not in the grids: a change of the repository's real HEAD (the tests do not
commit); the code state is replaced by a constant in the identity grid so
that the grid measures the id function and not git.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import i3_driver as D  # noqa: E402

from bot.bt import repro as RP  # noqa: E402
from bot.bt.repro import runner as RN  # noqa: E402
from bot.bt.report import ReportError, write_export  # noqa: E402

T0 = 1767225600000000000
S = 1_000_000_000


def _tape(shift=0.0):
    rows = []
    for h in (1, 2):
        for k in range(-12, 60):
            rows.append((T0 + h * 3600 * S + k * 5 * S, 10_000_000.0 + h * 1000 + shift))
    return "t_ns,px,qty\n" + "".join(f"{t},{p:.1f},1.0\n" for t, p in sorted(rows))


def _config():
    return {"instrument": "FX_BTC_JPY",
            "strategy": {"kind": "fixed_times", "legs": [{"t_ns": T0 + 3600 * S, "side": "buy", "qty": 0.01},
                                                         {"t_ns": T0 + 3600 * S + 120 * S, "side": "sell", "qty": 0.01},
                                                         {"t_ns": T0 + 7200 * S, "side": "sell", "qty": 0.02},
                                                         {"t_ns": T0 + 7200 * S + 120 * S, "side": "buy", "qty": 0.02}]},
            "order_type": "market", "fill": {"market": "next_trade_price"},
            "latency_ns": {"feed": 0, "order": 1000, "cancel": 0},
            "costs": {"maker_fee_rate": 0.0, "taker_fee_rate": 0.0005, "funding": "none", "source": "試験の宣言"}}


@pytest.fixture
def root(tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "tape.csv").write_text(_tape(), encoding="utf-8")
    (tmp_path / "data" / "tape2.csv").write_text(_tape(7.0), encoding="utf-8")
    (tmp_path / "prereg").mkdir()
    (tmp_path / "prereg" / "P.md").write_text("# 事前登録\n本文\n", encoding="utf-8")
    (tmp_path / "prereg" / "P2.md").write_text("# 事前登録\n本文 2\n", encoding="utf-8")
    (tmp_path / "prereg" / "E.md").write_text("  \n", encoding="utf-8")
    return tmp_path


def _args(root, **kw):
    a = dict(root=str(root), data=[RP.DataInput("data/tape.csv", D.TAPE_SPEC)], config=_config(), seed=5,
             setup=RP.FixedSetup("fixed_times"), purpose="動作確認", prereg=None)
    a.update(kw)
    return a


def _perm(d, order):
    return {k: d[k] for k in order}


def _leaves(d, path=()):
    if isinstance(d, dict):
        for k, v in d.items():
            yield from _leaves(v, path + (k,))
    elif isinstance(d, list):
        for i, v in enumerate(d):
            yield from _leaves(v, path + (i,))
    else:
        yield path, d


def _set(d, path, value):
    d = json.loads(json.dumps(d))
    cur = d
    for p in path[:-1]:
        cur = cur[p]
    cur[path[-1]] = value
    return d


def test_identity_grid(root, monkeypatch):
    state = {"git_sha": "a" * 40, "diff_hash": "b" * 64, "dirty": False, "untracked_files": 0, "code_scope": ["src"]}
    monkeypatch.setattr(RN, "code_state", lambda repo=None: dict(state))
    base = RP.plan_run(**_args(root)).run_id
    cfg = _config()
    perms = 0
    for order in itertools.permutations(cfg):
        assert RP.plan_run(**_args(root, config=_perm(cfg, order))).run_id == base
        perms += 1
    assert perms == 720
    nested = {k: (dict(reversed(list(v.items()))) if isinstance(v, dict) else v) for k, v in cfg.items()}
    assert RP.plan_run(**_args(root, config=nested)).run_id == base
    ids = {"base": base}
    for path, v in _leaves(cfg):
        new = v + 1 if type(v) is int else (v * 2 + 0.001 if type(v) is float else v + "x")
        ids[f"config:{path}"] = RP.plan_run(**_args(root, config=_set(cfg, path, new))).run_id
    ids["seed"] = RP.plan_run(**_args(root, seed=6)).run_id
    ids["data bytes"] = RP.plan_run(**_args(root, data=[RP.DataInput("data/tape2.csv", D.TAPE_SPEC)])).run_id
    ids["data spec"] = RP.plan_run(**_args(root, data=[RP.DataInput("data/tape.csv", dict(D.TAPE_SPEC, symbol="X"))])).run_id
    ids["setup"] = RP.plan_run(**_args(root, setup=RP.FixedSetup("seeded_random"))).run_id
    ids["purpose"] = RP.plan_run(**_args(root, purpose="研究", prereg="prereg/P.md")).run_id
    ids["prereg bytes"] = RP.plan_run(**_args(root, purpose="研究", prereg="prereg/P2.md")).run_id
    ids["prereg on smoke"] = RP.plan_run(**_args(root, prereg="prereg/P.md")).run_id
    for key in ("git_sha", "diff_hash"):
        old = state[key]
        state[key] = "c" * len(old)
        ids[key] = RP.plan_run(**_args(root)).run_id
        state[key] = old
    monkeypatch.setattr(RN, "version", lambda: "another version")
    ids["version"] = RP.plan_run(**_args(root)).run_id
    assert len(ids) == len(set(ids.values())) == 1 + len(list(_leaves(cfg))) + 10


PURPOSES = ["動作確認", "研究", None, "research", "", 1]
PREREGS = [None, "prereg/P.md", "prereg/E.md", "prereg/missing.md"]


def test_purpose_prereg_grid(root):
    n = 0
    for purpose, prereg in itertools.product(PURPOSES, PREREGS):
        ok = purpose in ("動作確認", "研究") and prereg in (None, "prereg/P.md") and not (purpose == "研究" and prereg is None)
        if ok:
            p = RP.plan_run(**_args(root, purpose=purpose, prereg=prereg))
            want = None if prereg is None else hashlib.sha256((root / prereg).read_bytes()).hexdigest()
            assert p.identity["prereg_sha256"] == want and p.identity["purpose"] == purpose
        else:
            with pytest.raises((RP.ReproError, ReportError)):
                RP.plan_run(**_args(root, purpose=purpose, prereg=prereg))
        n += 1
    assert n == 24


def test_two_runs_grid(root):
    for kind, seed in itertools.product(RP.SETUP_KINDS, (1, 2)):
        plan = RP.plan_run(**_args(root, setup=RP.FixedSetup(kind), seed=seed))
        chk = RP.check_reproducible(plan, work_dir=str(root / "work"))
        assert chk.runs == 2 and chk.reproduced == (kind != "unseeded_random"), (kind, seed)
        if kind == "unseeded_random":
            assert {"fills.json", "trades.json", "metrics.json", "orders.json"} <= set(chk.differing)
            with pytest.raises(RP.NotReproducibleError):
                RP.run(runs_dir=str(root / "runs"), **_args(root, setup=RP.FixedSetup(kind), seed=seed))
            assert not (root / "runs" / plan.run_id).exists()
        else:
            res = RP.run(runs_dir=str(root / "runs"), **_args(root, setup=RP.FixedSetup(kind), seed=seed))
            assert res.run_id == plan.run_id and res.repro["identical"] is True and res.repro["runs"] == 2
    assert sorted(os.listdir(root / "runs")) == sorted([".gitignore"] + [
        RP.plan_run(**_args(root, setup=RP.FixedSetup(k), seed=s)).run_id
        for k, s in itertools.product(("fixed_times", "seeded_random"), (1, 2))])
    assert not [x for x in os.listdir(root / "work")]


def test_seeded_quantities_follow_the_seed(root):
    import random
    res = RP.run(runs_dir=str(root / "runs"), **_args(root, setup=RP.FixedSetup("seeded_random"), seed=11))
    fills = json.loads((Path(res.run_dir) / "fills.json").read_text(encoding="utf-8"))["data"]
    rng = random.Random(11)
    mult = [1 + rng.randrange(256) / 256 for _ in range(2)]
    assert [f["qty"] for f in fills] == [0.01 * mult[0]] * 2 + [0.02 * mult[1]] * 2


def test_same_run_in_two_places_is_the_same_bytes(root, tmp_path_factory):
    other = tmp_path_factory.mktemp("elsewhere")
    for sub in ("data", "prereg"):
        (other / sub).mkdir()
    (other / "data" / "tape.csv").write_bytes((root / "data" / "tape.csv").read_bytes())
    a = RP.run(runs_dir=str(root / "runs"), **_args(root))
    b = RP.run(runs_dir=str(other / "runs"), **_args(other))
    assert a.run_id == b.run_id
    for name in sorted(os.listdir(a.run_dir)):
        assert (Path(a.run_dir) / name).read_bytes() == (Path(b.run_dir) / name).read_bytes(), name
    again = RP.run(runs_dir=str(root / "runs"), **_args(root))  # an existing identical run is kept
    assert again.run_id == a.run_id
    p = Path(a.run_dir) / "metrics.json"
    p.write_text(p.read_text(encoding="utf-8").replace('"n": 2', '"n": 3'), encoding="utf-8")
    with pytest.raises(RP.ReproError):
        RP.run(runs_dir=str(root / "runs"), **_args(root))


def test_record_fields_are_the_inputs(root):
    res = RP.run(runs_dir=str(root / "runs"), **_args(root, purpose="研究", prereg="prereg/P.md"))
    r = res.record
    head = subprocess.run(["git", "-C", str(RP.REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    assert r["git_sha"] == head and len(r["diff_hash"]) == 64
    assert r["config"] == _config() and r["seed"] == 5 and r["purpose"] == "研究"
    assert r["data_sha256"] == {"data/tape.csv": hashlib.sha256((root / "data" / "tape.csv").read_bytes()).hexdigest()}
    assert r["prereg_sha256"] == hashlib.sha256((root / "prereg" / "P.md").read_bytes()).hexdigest()
    assert r["version"] == RP.version() and r["run_id"] == res.run_id
    assert set(res.exports) == {"metrics.json", "trades.json", "fills.json", "orders.json", "data_quality.json"}
    assert set(res.exports.values()) == {"研究"}
    assert (root / "runs" / ".gitignore").read_text(encoding="utf-8").strip().endswith("*")


@pytest.mark.parametrize("purpose", [None, "", "research", "動作", 1, "研究 "])
def test_write_export_refuses_without_a_purpose(tmp_path, purpose):
    with pytest.raises(ReportError):
        write_export(str(tmp_path), "metrics", {"x": 1}, purpose=purpose, run_id="r")
    assert not list(tmp_path.iterdir())


def _git(repo, *a):
    subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True)


def test_diff_hash_follows_the_working_tree(tmp_path):
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "m.py").write_text("x = 1\n", encoding="utf-8")
    (repo / "notes.md").write_text("メモ\n", encoding="utf-8")
    _git(repo, "init", "-q")
    _git(repo, "add", ".")
    _git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init")
    clean = RP.code_state(str(repo))
    assert clean["dirty"] is False
    (repo / "src" / "m.py").write_text("x = 2\n", encoding="utf-8")
    edited = RP.code_state(str(repo))
    (repo / "src" / "new.py").write_text("y = 1\n", encoding="utf-8")
    untracked = RP.code_state(str(repo))
    (repo / "src" / "new.py").write_text("y = 2\n", encoding="utf-8")
    untracked2 = RP.code_state(str(repo))
    (repo / "notes.md").write_text("別のメモ\n", encoding="utf-8")  # outside the code scope
    doc = RP.code_state(str(repo))
    hashes = [clean["diff_hash"], edited["diff_hash"], untracked["diff_hash"], untracked2["diff_hash"]]
    assert len(set(hashes)) == 4 and doc["diff_hash"] == untracked2["diff_hash"]
    (repo / "src" / "new.py").unlink()
    (repo / "src" / "m.py").write_text("x = 1\n", encoding="utf-8")
    assert RP.code_state(str(repo))["diff_hash"] == clean["diff_hash"]
    assert all(s["git_sha"] == clean["git_sha"] for s in (edited, untracked, doc))
    with pytest.raises(RP.ReproError):
        RP.code_state(str(tmp_path / "nowhere"))


def test_config_refusal_grid():
    cfg = _config()
    bad = [{k: v for k, v in cfg.items() if k != drop} for drop in cfg] + [dict(cfg, extra=1)]
    bad += [_set(cfg, ("order_type",), "limit"), _set(cfg, ("fill", "market"), "mid"),
            _set(cfg, ("latency_ns", "feed"), -1), _set(cfg, ("latency_ns", "feed"), 1.0),
            _set(cfg, ("costs", "source"), " "), _set(cfg, ("costs", "funding"), "8h"),
            _set(cfg, ("costs", "taker_fee_rate"), "0.1"), _set(cfg, ("strategy", "kind"), "signal"),
            _set(cfg, ("strategy", "legs", 1, "side"), "buy"), _set(cfg, ("strategy", "legs", 1, "qty"), 0.02),
            _set(cfg, ("strategy", "legs", 1, "t_ns"), T0), _set(cfg, ("strategy", "legs"), [])]
    cost = dict(cfg["costs"])
    del cost["maker_fee_rate"]
    bad.append(dict(cfg, costs=cost))
    for b in bad:
        with pytest.raises(RP.ReproError):
            RP.parse_config(b)
    assert len(bad) == 6 + 1 + 12 + 1
    RP.parse_config(cfg)


def test_runs_dir_is_ignored_by_git(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    RN._ensure_runs_dir(str(repo / "backtest_runs"))
    (repo / "backtest_runs" / ("a" * 64)).mkdir()
    (repo / "backtest_runs" / ("a" * 64) / "record.json").write_text("{}", encoding="utf-8")
    out = subprocess.run(["git", "-C", str(repo), "status", "--porcelain", "--untracked-files=all"],
                         capture_output=True, text=True, check=True).stdout
    assert out == ""
    assert RP.DEFAULT_RUNS_DIR == os.path.join(RP.REPO, "backtest_runs")
