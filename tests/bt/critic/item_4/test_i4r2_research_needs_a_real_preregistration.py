"""Item 4 critic, round 2 (i4-r2-05): 「目的 `研究` の実行は事前登録のハッシュが無いと作れない」(委任文 §4) must not
be satisfied by 64 hex digits that name no pre-registration.

bot.bt.pipeline.plan_pipeline takes `prereg_sha256` as a bare string (checked only as 64 lowercase hex digits,
pipeline.py:288-292) and then admits, for the purpose 研究, a price-conditioned strategy on this environment's real
market data. Item 3's own runner (bot.bt.repro.runner.plan_run, runner.py:119-131) takes the pre-registration as a
FILE and hashes it; the integrated path is weaker than the part it integrates. A hash that is the sha256 of no file
in this environment is the caller's word, the same shape as the `origin` word of round 1 (i4-r1-04).

Grid: the real market file the worker's own origin grid uses (FX event ticks, in its market folder) x purpose
{研究} x strategy {price_rule} x prereg_sha256 {"00"*64/2, "cd"*32 (the worker's grid value), the sha256 of b"x"}
(none is the hash of a pre-registration file of this environment). Expected: refused at planning.

Round 2 of the k1 env fixes (2026-09-30, delegation 20260927_k1_env_fixes §4 (d)3): the market file is the
SYNTHETIC FX file of the worker's grid (test_i4_r2_origin_from_data_grid.make_env, same format; the file read before
is unconsumed data after 2026-08-28) in a temporary environment that is the run's root and pipeline.MARKET_BASE.
Until round 2 this test only checked that the repository's file existed (os.stat) and skipped otherwise; with the
grid's paths now naming synthetic files, that check skipped every case (3 skips in the round-2 worker's run), so the
test builds its environment itself. The refusal is pinned to the pre-registration rule (`match="prereg"`). Nothing
is skipped.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[4]
ITEM4 = REPO / "tests" / "bt" / "item_4"
if str(ITEM4) not in sys.path:
    sys.path.insert(0, str(ITEM4))

import test_i4_r2_origin_from_data_grid as G  # noqa: E402

PRICE_RULE = {"kind": "price_rule", "buy_below": 1e12, "sell_above": 0.0, "qty": 1.0}
FAKES = ["00" * 32, "cd" * 32, hashlib.sha256(b"x").hexdigest()]


@pytest.fixture(scope="module")
def env():
    import shutil
    import tempfile
    from bot.bt import pipeline as P
    tmp = G.make_env(tempfile.mkdtemp(prefix="i4r2crit_prereg_"))
    mp = pytest.MonkeyPatch()
    mp.setattr(P, "MARKET_BASE", tmp)
    yield tmp
    mp.undo()
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.mark.parametrize("fake", FAKES)
def test_a_made_up_hash_does_not_open_a_research_run_on_real_data(env, fake):
    from bot.bt.pipeline import plan_pipeline
    rel, spec = G.MARKET["fx_ticks"]
    assert (Path(env) / rel).is_file()
    ds = [{"name": "fx_ticks", "paths": [rel], "spec": spec, "origin": "real"}]
    with pytest.raises(ValueError, match="prereg"):
        plan_pipeline(root=env, datasets=ds, instruments=[{"name": "fx_ticks", "price": "fx_ticks", "with": []}],
                      strategy=PRICE_RULE, fill=G.FILL, costs=G.ZERO, purpose="研究", prereg_sha256=fake)
