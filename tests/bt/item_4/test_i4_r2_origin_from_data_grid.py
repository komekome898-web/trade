"""Adversarial grid (委任文 §3「提出前の吟味」(6); round 2 i4-r1-04, rewritten in the finishing stage for i4-r2-03):
whether a dataset is market data is decided from the data, not from the caller's word.

The rule (finishing delegation §1 i4-r2-03, verbatim): 「出所は宣言でもファイルの中身の同一性でもなく、行の中身で
決める」「合成は種つきの生成器からだけ作れる口にし、その種と生成器の版を実行記録に残す」 + 委任文 §4 「実データを通す
ときの戦略は、時刻だけで決まる機械的な手順か種つきの乱数に限る」. Read as a rule of bot.bt.pipeline: a FILE dataset is
real market data (a file cannot be declared synthetic: refused); its evidence is its rows compared with the rows of
this environment's market files through the data layer; a GENERATED dataset (seeded generator) is synthetic.
`expected` below is written from that rule text.

Round 2 of the k1 env fixes (2026-09-27, delegation 20260927_k1_env_fixes §4 (d)2 / (d)3): the environment's
market files are SYNTHETIC files written by `make_env` into a temporary "environment" (pipeline.MARKET_BASE points
at it for these tests), in the formats of the files the grid used before (the FX event ticks of
fx_event_ticks_2015_2026 and the TOPIX futures 1-minute bars of topixf_225labo_20260907, which are unconsumed data
after 2026-08-28 and are no longer read). And the evidence is looked for ONLY in the files handed to the run and
the market files declared as their "source": a copy declares the market file it copies (`source`), and
test_a_copy_without_a_declared_source_is_unmatched / test_the_evidence_opens_nothing_else pin the rest.

Grid (the rule's input space): source {the market file itself (root = the environment), a symbolic link under a
temporary root pointing at the market file, a byte copy under a temporary root in a market-folder name
(backtest_data/...), a byte copy under a temporary root in another allowed folder name (data/...), a seeded
generator} x the market file {FX event ticks (quotes), TOPIX futures 1-minute bars} (the generator makes the same
kind) x declared origin {real, synthetic} (the generator declares none: one column) x strategy {schedule,
seeded_random, price_rule} x purpose {動作確認, 研究 with a pre-registration FILE}
= (4 x 2 x 2 + 2) x 3 x 2 = 108 cells, all planned (the rule is checked at planning; nothing is executed). The
rows are read through the data layer at planning, so the symbolic link out of the temporary data root is refused
there by the data layer (PathRefused: outside the data root), whatever the declaration.
The re-encodings (recompressed, decompressed, cut, one byte edited, every row edited) are the grid of
test_i4_r3_origin_by_rows_grid.py. Not in the grid: market data that exists only outside this environment (the
owner's PC: a file, so real by the rule, with evidence "unmatched").
"""
from __future__ import annotations

import gzip
import itertools
import os
import shutil
import tempfile
from pathlib import Path

import pytest

from bot.bt.pipeline import PipelineError, plan_pipeline

import i4w_decl as D

REPO = Path(__file__).resolve().parents[3]
NS = 1_000_000_000
GZ = {"compression": "gzip", "format": "csv", "header": True, "delimiter": ","}
MARKET = {
    "fx_ticks": ("backtest_data/syn_fx_event_ticks/NFP_like.csv.gz",
                 {**GZ, "kind": "quote", "symbol": "USDJPY", "asset": "fx",
                  "time": {"columns": ["ts_utc"], "unit": "ms", "tz": "UTC"},
                  "fields": {"bid": "bid", "ask": "ask", "bid_qty": "bidvol", "ask_qty": "askvol"}}),
    "jpx_1m": ("backtest_data/syn_topixf_1min/bars_1min.csv.gz",
               {**GZ, "kind": "bar", "symbol": "TOPIXF", "asset": "jpx",
                "time": {"columns": ["date", "time"], "join": " ", "unit": "iso", "tz": "Asia/Tokyo"},
                "fields": {"open": "open", "high": "high", "low": "low", "close": "close", "volume": "volume"},
                "bar": {"interval_s": 60, "label": "start"}, "key": "start"}),
}
DECOY = "backtest_data/syn_other/ticks_other.csv.gz"  # a market file of the environment no run names
QA_FILE = "backtest_data/qa_known_answer_syn/daily_qa_alpha.csv.gz"


def _fx_rows(seed: int, n: int = 900) -> bytes:
    """Synthetic FX event ticks (ts_utc in ms from 2026-01-05 00:00 UTC, 1 s apart; bid / ask 0.005 apart)."""
    import random
    rnd = random.Random(seed)
    t0, mid, out = 1767571200 * 1000, 150.0, ["ts_utc,bid,ask,bidvol,askvol"]
    for k in range(n):
        mid = round(mid + rnd.choice((-0.003, 0.0, 0.003)), 3)
        out.append(f"{t0 + k * 1000},{mid - 0.0025:.4f},{mid + 0.0025:.4f},{rnd.randint(1, 9)},{rnd.randint(1, 9)}")
    return ("\n".join(out) + "\n").encode()


def _jpx_rows(seed: int, n: int = 240) -> bytes:
    """Synthetic TOPIX-futures-like 1-minute bars: date, time (JST, the bar's start), open, high, low, close, volume;
    7 columns, prices 0.5 apart, lines ended with CRLF (as the file the grid used before)."""
    import random
    rnd = random.Random(seed)
    out, px = ["date,time,open,high,low,close,volume"], 3000.0
    for k in range(n):
        h, m = divmod(8 * 60 + 45 + k, 60)  # from 08:45 JST
        o = px
        c = o + rnd.choice((-1.0, -0.5, 0.0, 0.5, 1.0))
        hi, lo = max(o, c) + 0.5, min(o, c) - 0.5
        out.append(f"2026-01-05,{h:02d}:{m:02d},{o:.1f},{hi:.1f},{lo:.1f},{c:.1f},{rnd.randint(10, 99)}")
        px = c
    return ("\r\n".join(out) + "\r\n").encode()


def make_env(env: str) -> str:
    """A synthetic environment: the two market files of MARKET, a decoy market file with the FX header, and a qa_*
    file (named as not market data by the data layer). Returns env."""
    files = {MARKET["fx_ticks"][0]: _fx_rows(1), MARKET["jpx_1m"][0]: _jpx_rows(2), DECOY: _fx_rows(3),
             QA_FILE: _fx_rows(1)}
    for rel, body in files.items():
        dst = os.path.join(env, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "wb") as fh:
            fh.write(gzip.compress(body, mtime=0))
    return env


@pytest.fixture(scope="module")
def env():
    """The synthetic environment, with bot.bt.pipeline.MARKET_BASE pointed at it for the module."""
    from bot.bt import pipeline as P
    tmp = tempfile.mkdtemp(prefix="i4w_env_")
    make_env(tmp)
    mp = pytest.MonkeyPatch()
    mp.setattr(P, "MARKET_BASE", tmp)
    yield tmp
    mp.undo()
    shutil.rmtree(tmp, ignore_errors=True)


SYN_SPEC = {**GZ, "kind": "bar", "symbol": "SYN", "asset": "crypto",
            "time": {"columns": ["timestamp"], "unit": "iso", "tz": "UTC"},
            "fields": {"open": "open", "high": "high", "low": "low", "close": "close", "volume": "volume"},
            "bar": {"interval_s": 60, "label": "start"}, "key": "start"}
PLACEMENTS = ("in_market_folder", "symlink_to_market", "copy_backtest_data", "copy_data")
GEN = {"fx_ticks": {"kind": "quote", "start_ns": 1767571200 * NS, "step_ns": 1 * NS, "n": 600, "price0": 150.0,
                    "step_pct": 0.01, "qty": 1.0, "spread_pct": 0.002},
       "jpx_1m": {"kind": "bar", "start_ns": 1767571200 * NS, "step_ns": 60 * NS, "n": 60, "price0": 3000.0,
                  "step_pct": 0.1, "qty": 1.0}}
T0 = 1767571200 * NS
STRATS = {"schedule": {"kind": "schedule", "orders": [{"t_ns": T0, "side": "buy", "qty": 1.0},
                                                      {"t_ns": T0 + 300 * NS, "side": "sell", "qty": 1.0}]},
          "seeded_random": {"kind": "seeded_random", "seed": 7, "times": [T0, T0 + 300 * NS], "qty": 1.0},
          "price_rule": {"kind": "price_rule", "buy_below": 1e12, "sell_above": 0.0, "qty": 1.0}}
PURPOSES = ("動作確認", "研究")
PREREG = "prereg/PREREG.md"
FILL = D.FILL
ZERO = D.COSTS0

CELLS = ([(pl, f, o, s, p) for pl, f, o, s, p in itertools.product(PLACEMENTS, MARKET, ("real", "synthetic"), STRATS,
                                                                    PURPOSES)]
         + [("generator", f, "-", s, p) for f, s, p in itertools.product(MARKET, STRATS, PURPOSES)])


def expected(placement: str, origin: str, strat: str, purpose: str):
    """The rule text above -> "refuse" or the origin the run records."""
    if placement == "generator":
        return "synthetic"
    if placement == "symlink_to_market":
        return "refuse"  # the rows are read at planning; the data layer refuses a link out of the data root
    if origin == "synthetic":
        return "refuse"  # a file cannot be synthetic
    if purpose == "動作確認" and strat == "price_rule":
        return "refuse"  # 委任文 §4
    return "real"


@pytest.fixture(scope="module")
def roots(env):
    tmp = tempfile.mkdtemp(prefix="i4w_origin_")
    out = {"in_market_folder": env}
    r = os.path.join(tmp, "symlink_to_market")
    for name, (rel, _) in MARKET.items():
        dst = os.path.join(r, "backtest_data", "linked", f"{name}_link.csv.gz")
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        os.symlink(os.path.join(env, rel), dst)
    out["symlink_to_market"] = r
    for pl, folder in (("copy_backtest_data", "backtest_data"), ("copy_data", "data")):
        r = os.path.join(tmp, pl)
        for name, (rel, _) in MARKET.items():
            dst = os.path.join(r, folder, "copied", f"{name}_renamed.csv.gz")
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(os.path.join(env, rel), dst)
        out[pl] = r
    r = os.path.join(tmp, "generator")
    os.makedirs(r)
    out["generator"] = r
    for root in set(out.values()):
        os.makedirs(os.path.join(root, "prereg"), exist_ok=True)
        with open(os.path.join(root, PREREG), "w", encoding="utf-8") as fh:
            fh.write("test pre-registration (the file's sha256 goes into the record)\n")
    yield out
    shutil.rmtree(tmp, ignore_errors=True)


def _dataset(placement: str, f: str, origin: str) -> dict:
    if placement == "generator":
        return {"name": f, "generator": {"name": "random_walk", "seed": 11, "params": GEN[f]}}
    rel, spec = MARKET[f]
    if placement == "in_market_folder":
        path = rel
    elif placement == "symlink_to_market":
        path = f"backtest_data/linked/{f}_link.csv.gz"
    else:  # a copy declares the market file it copies (round 2: the only other place the evidence is looked for)
        path = f"{'backtest_data' if placement == 'copy_backtest_data' else 'data'}/copied/{f}_renamed.csv.gz"
        return {"name": f, "paths": [path], "spec": spec, "origin": origin, "source": [rel]}
    return {"name": f, "paths": [path], "spec": spec, "origin": origin}


def test_the_grid_is_the_full_space():
    assert len(CELLS) == 108
    assert {expected(*c[:1], *c[2:]) for c in CELLS} == {"refuse", "real", "synthetic"}


@pytest.mark.parametrize("cell", CELLS, ids=["-".join(c) for c in CELLS])
def test_origin_is_decided_from_the_data(cell, roots):
    placement, f, origin, strat, purpose = cell
    want = expected(placement, origin, strat, purpose)
    root = roots[placement]
    prereg = PREREG if purpose == "研究" else None
    kind = "bar" if f == "jpx_1m" else "quote"
    try:
        plan = plan_pipeline(root=root, datasets=[_dataset(placement, f, origin)],
                             instruments=[D.instrument(f, f, kind)], strategy=STRATS[strat], purpose=purpose,
                             prereg=prereg, **D.kw())
    except PipelineError as exc:
        assert want == "refuse", (cell, str(exc))
        return
    assert want != "refuse", (cell, "accepted")
    d = plan.datasets[0]
    assert d["origin"] == want, (cell, d["origin"])
    ev = d["origin_evidence"]
    if placement == "generator":
        assert ev == {"by": "generator", "generator": "random_walk", "version": ev["version"], "seed": 11}, ev
    else:
        assert ev["by"] == "rows" and ev["rows_matched"] == ev["rows_read"] > 0, ev
        assert ev["market_path"] == MARKET[f][0], ev
    assert plan.identity["datasets"][0]["origin"] == want


def test_a_file_the_data_layer_names_as_not_market_data_is_not_evidence(env):
    """The data layer's mandatory refusals name qa_* (synthetic known-answer packets) as not market data: a qa_* file
    is never a candidate, even when it is handed to the run or declared as a source (its rows are those of the FX
    market file here, so only the exclusion keeps it out)."""
    from bot.bt.pipeline import _market_candidates
    spec = MARKET["fx_ticks"][1]
    got = _market_candidates(spec, [os.path.join(env, QA_FILE), os.path.join(env, MARKET["fx_ticks"][0])])
    assert [rel for _, rel, _, _ in got] == [MARKET["fx_ticks"][0]]


def _plan_copy(root: str, source):
    rel, spec = MARKET["fx_ticks"]
    ds = {"name": "fx", "paths": ["backtest_data/copied/fx_ticks_renamed.csv.gz"], "spec": spec, "origin": "real",
          **({"source": source} if source is not None else {})}
    return plan_pipeline(root=root, datasets=[ds], instruments=[D.instrument("fx", "fx", "quote")],
                         strategy=STRATS["schedule"], purpose="動作確認", **D.kw())


def test_a_copy_without_a_declared_source_is_unmatched(env, roots):
    """Round 2 (d)2: the evidence is looked for only in the files handed to the run and the declared sources. A copy
    outside the environment's market folders with no declared source is still real (a file), with evidence
    "unmatched"; declaring the market file as its source gives "rows"."""
    root = roots["copy_backtest_data"]
    ev = _plan_copy(root, None).datasets[0]["origin_evidence"]
    assert ev["by"] == "unmatched" and ev["rows_matched"] == 0 and ev["searched"] == [
        os.path.relpath(os.path.realpath(os.path.join(root, "backtest_data/copied/fx_ticks_renamed.csv.gz")),
                        os.path.realpath(env))], ev
    ev = _plan_copy(root, [MARKET["fx_ticks"][0]]).datasets[0]["origin_evidence"]
    assert ev["by"] == "rows" and ev["market_path"] == MARKET["fx_ticks"][0] and ev["rows_matched"] == ev["rows_read"]


def test_a_declared_source_must_be_a_market_file_of_the_environment(env, roots):
    for bad in (["../outside.csv.gz"], [QA_FILE], ["backtest_data/no_such_file.csv.gz"], "not a list"):
        with pytest.raises(PipelineError):
            _plan_copy(roots["copy_backtest_data"], bad)


def test_the_evidence_opens_nothing_else(env, roots):
    """Round 2 (d)2: planning opens, under the environment, only the declared source (the decoy -- a market file
    with the same header and rows of the same span -- and every other file stay unopened). Before round 2 the
    evidence walk opened every file of the market folders."""
    import sys
    opened = []
    env_real = os.path.realpath(env)

    def hook(event, args):
        if event == "open" and args and isinstance(args[0], (str, bytes, os.PathLike)):
            p = os.path.realpath(os.fsdecode(args[0]))
            if p.startswith(env_real + os.sep):
                opened.append(os.path.relpath(p, env_real))

    sys.addaudithook(hook)  # an audit hook cannot be removed: it only records while `opened` is this list
    try:
        _plan_copy(roots["copy_backtest_data"], [MARKET["fx_ticks"][0]])
        seen = sorted(set(opened))
    finally:
        opened = None  # noqa: F841 -- the hook's list is no longer read
    assert seen == [MARKET["fx_ticks"][0]], seen
