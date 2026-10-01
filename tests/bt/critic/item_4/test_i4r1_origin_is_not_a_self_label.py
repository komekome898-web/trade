"""Item 4 critic, round 1 (i4-r1-03): the real-data rule of the delegation §4 must not rest on the caller's label.

§4: 「実データを通すときの戦略は、時刻だけで決まる機械的な手順か種つきの乱数に限る。信号・条件付け・最適化を入れない」.
bot.bt.pipeline enforces it only for datasets the CALLER declares `origin: "real"`. The same market-data file of
this environment, declared `origin: "synthetic"`, lets a price-conditioned strategy run under the purpose
動作確認 -- the rule is then a self-declaration, not a structure.

Grid: the environment's market-data files the real-data smoke run uses (tests/bt/item_4/test_i4_real_data_smoke.py)
x purpose {動作確認} x strategy {price_rule} x label {synthetic}. Expected: refused (a ValueError subclass)
before anything runs. Not in the grid: the same bytes copied under another root (whether the engine should
recognise market data by content is the lead's / worker's design; the test only pins that a file under
the repository's market-data folders is not made synthetic by a word).

Round 2 of the k1 env fixes (2026-09-30, delegation 20260927_k1_env_fixes §4 (d)3): the smoke run's FX / JPX files
are now SYNTHETIC files in the same formats (test_i4_real_data_smoke._synthetic_files; the files read before are
unconsumed data after 2026-08-28), written into a temporary environment that is the run's root and
pipeline.MARKET_BASE (its market-data folder). Until round 2 this test only checked that the repository's file
existed (os.stat) and skipped otherwise; with the smoke run's paths now naming synthetic files, that check skipped
every case (3 skips in the round-2 worker's run), so the test builds its environment itself. The refusal is pinned
to the origin rule (`match="origin"`). Nothing is skipped.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest

ITEM4 = Path(__file__).resolve().parents[2] / "item_4"
if str(ITEM4) not in sys.path:
    sys.path.insert(0, str(ITEM4))

import test_i4_real_data_smoke as R  # noqa: E402

FILL = {"price": "first_observed_at_or_after", "trade": "px", "quote": {"buy": "ask", "sell": "bid"}, "bar": "open",
        "latency_ns": 0}
ZERO = {"taker_fee_pct": 0.0, "maker_fee_pct": 0.0, "slippage_pct": 0.0, "spread_pct": 0.0}
PRICE_RULE = {"kind": "price_rule", "buy_below": 1e12, "sell_above": 0.0, "qty": 1.0}


@pytest.fixture(scope="module")
def env():
    import gzip
    import os
    import shutil
    from bot.bt import pipeline as P
    tmp = tempfile.mkdtemp(prefix="i4r1crit_env_")
    for rel, body in R._synthetic_files().items():
        dst = os.path.join(tmp, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "wb") as fh:
            fh.write(gzip.compress(body.encode(), mtime=0))
    mp = pytest.MonkeyPatch()
    mp.setattr(P, "MARKET_BASE", tmp)
    yield tmp
    mp.undo()
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.mark.parametrize("name", ["fx_1m", "jpx_1m", "fx_ticks"])
def test_a_market_data_file_labelled_synthetic_does_not_admit_a_price_rule(env, name):
    from bot.bt.pipeline import plan_pipeline, run_pipeline
    ds = [dict(d) for d in R.datasets() if d["name"] == name]
    assert (Path(env) / ds[0]["paths"][0]).is_file()
    ds[0]["origin"] = "synthetic"
    with pytest.raises(ValueError, match="origin"):
        plan = plan_pipeline(root=env, datasets=ds, instruments=[{"name": name, "price": name, "with": []}],
                             strategy=PRICE_RULE, fill=FILL, costs=ZERO, purpose="動作確認")
        run_pipeline(plan, runs_dir=tempfile.mkdtemp(prefix="i4r1crit_"))
