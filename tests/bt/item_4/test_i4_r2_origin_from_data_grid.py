"""Adversarial grid (委任文 §3「提出前の吟味」(6), round 2, i4-r1-04): whether a dataset is market data is decided
from the data, not from the caller's word.

The rule (委任文 §4): 「実データを通すときの戦略は、時刻だけで決まる機械的な手順か種つきの乱数に限る」. Read as
a rule of the integrated run (bot.bt.pipeline): a dataset IS real market data when its file lies in this
environment's market-data folders (the repository's backtest_data / data / paper_logs/tape, the data layer's
allowed roots) or has the same bytes (size and sha256) as a file there; the caller's `origin` cannot make such a
file synthetic -- a "synthetic" declaration on it is refused as a false declaration, whatever the strategy and the
purpose. A declaration "real" is kept (it only restricts). `expected` below is written from that rule text.

Grid (the rule's input space): placement of the file {in the market folder itself (root = the repository), a
byte copy under a temporary root in a market-folder name (backtest_data/...), a byte copy under a temporary root
in another allowed folder name (data/...), a synthetic file under a temporary root} x the market file {FX event
ticks (quotes), TOPIX futures 1-minute bars} (the synthetic file is one) x declared origin {real, synthetic} x
strategy {schedule, seeded_random, price_rule} x purpose {動作確認, 研究 with a pre-registration hash}
= (3 x 2 + 1) x 2 x 3 x 2 = 84 cells, all planned (the rule is checked at planning; nothing is executed).

Not in the grid (named): a market file edited by even one byte (another file by content -- a limit of the rule,
written in bot.bt.pipeline); market data that exists only outside this environment (the owner's PC); the
synthetic battery files of the item-4 scene set (they declare themselves "real", which the rule keeps).
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
PLACEMENTS = ("in_market_folder", "copy_backtest_data", "copy_data")
T0 = 1767571200 * NS
STRATS = {"schedule": {"kind": "schedule", "orders": [{"t_ns": T0, "side": "buy", "qty": 1.0},
                                                      {"t_ns": T0 + 300 * NS, "side": "sell", "qty": 1.0}]},
          "seeded_random": {"kind": "seeded_random", "seed": 7, "times": [T0, T0 + 300 * NS], "qty": 1.0},
          "price_rule": {"kind": "price_rule", "buy_below": 1e12, "sell_above": 0.0, "qty": 1.0}}
PURPOSES = ("動作確認", "研究")
HASH = "cd" * 32
FILL = {"price": "first_observed_at_or_after", "trade": "px", "quote": {"buy": "ask", "sell": "bid"}, "bar": "open",
        "latency_ns": 0}
ZERO = {"taker_fee_pct": 0.0, "maker_fee_pct": 0.0, "slippage_pct": 0.0, "spread_pct": 0.0}

CELLS = ([(pl, f, o, s, p) for pl, f, o, s, p in itertools.product(PLACEMENTS, MARKET, ("real", "synthetic"), STRATS,
                                                                    PURPOSES)]
         + [("synthetic_file", "syn", o, s, p) for o, s, p in itertools.product(("real", "synthetic"), STRATS, PURPOSES)])


def expected(placement: str, origin: str, strat: str, purpose: str):
    """The rule text above -> "refuse" or the origin the run records."""
    market = placement != "synthetic_file"
    if market and origin == "synthetic":
        return "refuse"  # a false declaration
    real = market or origin == "real"
    if real and purpose == "動作確認" and strat == "price_rule":
        return "refuse"  # 委任文 §4
    return "real" if real else "synthetic"


def _synthetic_bytes() -> bytes:
    rows = ["timestamp,open,high,low,close,volume"]
    for i in range(20):
        p = 100 + (i % 5)
        rows.append(f"2026-01-05T00:{i:02d}:00Z,{p},{p + 1},{p - 1},{p + 0.5},1")
    return gzip.compress(("\n".join(rows) + "\n").encode(), mtime=0)


@pytest.fixture(scope="module")
def roots():
    for rel, _ in MARKET.values():
        if not (REPO / rel).is_file():
            pytest.skip(f"{rel} is not in this environment")
    tmp = tempfile.mkdtemp(prefix="i4w_origin_")
    out = {"in_market_folder": str(REPO)}
    for pl, folder in (("copy_backtest_data", "backtest_data"), ("copy_data", "data")):
        r = os.path.join(tmp, pl)
        for name, (rel, _) in MARKET.items():
            dst = os.path.join(r, folder, "copied", f"{name}_renamed.csv.gz")
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(REPO / rel, dst)
        out[pl] = r
    r = os.path.join(tmp, "synthetic_file")
    os.makedirs(os.path.join(r, "backtest_data"), exist_ok=True)
    with open(os.path.join(r, "backtest_data", "syn_bars.csv.gz"), "wb") as fh:
        fh.write(_synthetic_bytes())
    out["synthetic_file"] = r
    yield out
    shutil.rmtree(tmp, ignore_errors=True)


def _dataset(placement: str, f: str, origin: str) -> dict:
    if placement == "synthetic_file":
        return {"name": f, "paths": ["backtest_data/syn_bars.csv.gz"], "spec": SYN_SPEC, "origin": origin}
    rel, spec = MARKET[f]
    if placement == "in_market_folder":
        path = rel
    else:
        path = f"{'backtest_data' if placement == 'copy_backtest_data' else 'data'}/copied/{f}_renamed.csv.gz"
    return {"name": f, "paths": [path], "spec": spec, "origin": origin}


def test_the_grid_is_the_full_space():
    assert len(CELLS) == 84
    assert {expected(*c[:1], *c[2:]) for c in CELLS} == {"refuse", "real", "synthetic"}


@pytest.mark.parametrize("cell", CELLS, ids=["-".join(c) for c in CELLS])
def test_origin_is_decided_from_the_data(cell, roots):
    placement, f, origin, strat, purpose = cell
    want = expected(placement, origin, strat, purpose)
    try:
        plan = plan_pipeline(root=roots[placement], datasets=[_dataset(placement, f, origin)],
                             instruments=[{"name": f, "price": f, "with": []}], strategy=STRATS[strat], fill=FILL,
                             costs=ZERO, purpose=purpose, prereg_sha256=HASH if purpose == "研究" else None)
    except PipelineError as exc:
        assert want == "refuse", (cell, str(exc))
        return
    assert want != "refuse", (cell, "accepted")
    d = plan.datasets[0]
    assert d["origin"] == want, (cell, d["origin"])
    ev = d["origin_evidence"]
    if placement == "in_market_folder":
        assert ev["by"] == "position" and ev["market_path"] == MARKET[f][0], ev
    elif placement.startswith("copy_"):
        assert ev["by"] == "bytes" and ev["market_path"] == MARKET[f][0], ev
    else:
        assert ev["by"] is None and ev["market_path"] is None, ev
    assert plan.identity["datasets"][0]["origin"] == want
