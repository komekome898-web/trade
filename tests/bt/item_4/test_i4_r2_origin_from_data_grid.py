"""Adversarial grid (委任文 §3「提出前の吟味」(6); round 2 i4-r1-04, rewritten in the finishing stage for i4-r2-03):
whether a dataset is market data is decided from the data, not from the caller's word.

The rule (finishing delegation §1 i4-r2-03, verbatim): 「出所は宣言でもファイルの中身の同一性でもなく、行の中身で
決める」「合成は種つきの生成器からだけ作れる口にし、その種と生成器の版を実行記録に残す」 + 委任文 §4 「実データを通す
ときの戦略は、時刻だけで決まる機械的な手順か種つきの乱数に限る」. Read as a rule of bot.bt.pipeline: a FILE dataset is
real market data (a file cannot be declared synthetic: refused); its evidence is its rows compared with the rows of
this environment's market files through the data layer; a GENERATED dataset (seeded generator) is synthetic.
`expected` below is written from that rule text.

Grid (the rule's input space): source {the market file itself (root = the repository), a symbolic link under a
temporary root pointing at the market file, a byte copy under a temporary root in a market-folder name
(backtest_data/...), a byte copy under a temporary root in another allowed folder name (data/...), a seeded
generator} x the market file {FX event ticks (quotes), TOPIX futures 1-minute bars} (the generator makes the same
kind) x declared origin {real, synthetic} (the generator declares none: one column) x strategy {schedule,
seeded_random, price_rule} x purpose {動作確認, 研究 with a pre-registration FILE}
= (4 x 2 x 2 + 2) x 3 x 2 = 108 cells, all planned (the rule is checked at planning; nothing is executed).
The re-encodings (recompressed, decompressed, cut, one byte edited, every row edited) are the grid of
test_i4_r3_origin_by_rows_grid.py. Not in the grid: market data that exists only outside this environment (the
owner's PC: a file, so real by the rule, with evidence "unmatched").
Skipped only when a market file is not in this environment.
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
    "fx_ticks": ("backtest_data/fx_event_ticks_2015_2026/NFP_20260807.csv.gz",
                 {**GZ, "kind": "quote", "symbol": "USDJPY", "asset": "fx",
                  "time": {"columns": ["ts_utc"], "unit": "ms", "tz": "UTC"},
                  "fields": {"bid": "bid", "ask": "ask", "bid_qty": "bidvol", "ask_qty": "askvol"}}),
    "jpx_1m": ("backtest_data/topixf_225labo_20260907/bars_1min.csv.gz",
               {**GZ, "kind": "bar", "symbol": "TOPIXF", "asset": "jpx",
                "time": {"columns": ["date", "time"], "join": " ", "unit": "iso", "tz": "Asia/Tokyo"},
                "fields": {"open": "open", "high": "high", "low": "low", "close": "close", "volume": "volume"},
                "bar": {"interval_s": 60, "label": "start"}, "key": "start"}),
}
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
         + [("synthetic_file", "syn", o, s, p) for o, s, p in itertools.product(("real", "synthetic"), STRATS, PURPOSES)])


def expected(placement: str, origin: str, strat: str, purpose: str):
    """The rule text above -> "refuse" or the origin the run records."""
    if placement == "generator":
        return "synthetic"
    if origin == "synthetic":
        return "refuse"  # a file cannot be synthetic
    if purpose == "動作確認" and strat == "price_rule":
        return "refuse"  # 委任文 §4
    return "real"


@pytest.fixture(scope="module")
def roots():
    for rel, _ in MARKET.values():
        if not (REPO / rel).is_file():
            pytest.skip(f"{rel} is not in this environment")
    tmp = tempfile.mkdtemp(prefix="i4w_origin_")
    out = {"in_market_folder": str(REPO)}
    r = os.path.join(tmp, "symlink_to_market")
    for name, (rel, _) in MARKET.items():
        dst = os.path.join(r, "backtest_data", "linked", f"{name}_link.csv.gz")
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        os.symlink(REPO / rel, dst)
    out["symlink_to_market"] = r
    for pl, folder in (("copy_backtest_data", "backtest_data"), ("copy_data", "data")):
        r = os.path.join(tmp, pl)
        for name, (rel, _) in MARKET.items():
            dst = os.path.join(r, folder, "copied", f"{name}_renamed.csv.gz")
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(REPO / rel, dst)
        out[pl] = r
    r = os.path.join(tmp, "generator")
    os.makedirs(r)
    out["generator"] = r
    for root in set(out.values()) - {str(REPO)}:
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
    else:
        path = f"{'backtest_data' if placement == 'copy_backtest_data' else 'data'}/copied/{f}_renamed.csv.gz"
    return {"name": f, "paths": [path], "spec": spec, "origin": origin}


def test_the_grid_is_the_full_space():
    assert len(CELLS) == 108
    assert {expected(*c[:1], *c[2:]) for c in CELLS} == {"refuse", "real", "synthetic"}


@pytest.mark.parametrize("cell", CELLS, ids=["-".join(c) for c in CELLS])
def test_origin_is_decided_from_the_data(cell, roots):
    placement, f, origin, strat, purpose = cell
    want = expected(placement, origin, strat, purpose)
    root = roots[placement]
    prereg = None
    if purpose == "研究":
        prereg = PREREG if root != str(REPO) else os.path.relpath(__file__, REPO)  # a file of the repository
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
        assert ev["market_path"] is not None and not ev["market_path"].startswith(".."), ev
    assert plan.identity["datasets"][0]["origin"] == want


QA_FILE = "backtest_data/qa_known_answer_20260905/daily_qa_alpha.csv.gz"


def test_a_file_the_data_layer_names_as_not_market_data_is_not_evidence():
    """The data layer's mandatory refusals name qa_* (synthetic known-answer packets) as not market data: a copy of
    such a file is still a FILE (real by the rule), but its rows are never matched against the qa_* file itself
    (the qa_* folder is not a candidate), so its evidence is not "rows" from a qa_* path."""
    from bot.bt.pipeline import _market_candidates
    src = REPO / QA_FILE
    if not src.is_file():
        pytest.skip(f"{QA_FILE} is not in this environment")
    spec = {**GZ, "kind": "bar", "symbol": "QA", "asset": "crypto",
            "time": {"columns": ["timestamp"], "unit": "iso", "tz": "UTC"},
            "fields": {"open": "open", "high": "high", "low": "low", "close": "close", "volume": "volume"},
            "bar": {"interval_s": 60, "label": "start"}, "key": "start"}
    assert not any("qa_" in rel for _, rel, _, _ in _market_candidates(spec))
