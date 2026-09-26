"""Item 4 critic, round 2 (i4-r2-03): the real-data rule of the delegation §4 must not be undone by an ordinary
re-encoding of a market-data file.

§4: 「実データを通すときの戦略は、時刻だけで決まる機械的な手順か種つきの乱数に限る。信号・条件付け・最適化を入れない」
+ requirement I4-6 (「実データを通す実行の戦略が…に限られ」). Round 2 decides the origin from the file's position
or its exact bytes (bot.bt.pipeline.market_evidence). The same market rows written out again -- gunzip then gzip
(the gzip header carries a time stamp), decompressed, or the first rows cut out of the day -- are other bytes, so
declaring them `origin: "synthetic"` lets a price-conditioned strategy run on real market data under 動作確認.
These are not adversarial edits: they are what a researcher does to a day of data before a quick run.

Grid: the FX event-tick file and the TOPIX futures 1-minute bars (the files the worker's own origin grid uses)
x the re-encoding {regzip with another header time, decompressed, first 200 data rows cut out (regzipped)}
x declared origin {synthetic} x strategy {price_rule} x purpose {動作確認}. Expected: refused (a ValueError
subclass) at planning (where the worker's grid checks the origin rule). Skipped only when a market file is not in this environment.
"""
from __future__ import annotations

import gzip
import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[4]
ITEM4 = REPO / "tests" / "bt" / "item_4"
if str(ITEM4) not in sys.path:
    sys.path.insert(0, str(ITEM4))

import test_i4_r2_origin_from_data_grid as G  # noqa: E402

PRICE_RULE = {"kind": "price_rule", "buy_below": 1e12, "sell_above": 0.0, "qty": 1.0}
WAYS = ("regzip", "decompressed", "first_rows")


def _rewrite(src: Path, dst: str, way: str) -> dict:
    raw = gzip.decompress(src.read_bytes())
    if way == "first_rows":
        lines = raw.split(b"\n")
        raw = b"\n".join(lines[:201]) + b"\n"
    if way == "decompressed":
        with open(dst, "wb") as fh:
            fh.write(raw)
        return {"compression": "none"}
    with open(dst, "wb") as fh:
        fh.write(gzip.compress(raw, mtime=12345))
    return {}


@pytest.mark.parametrize("way", WAYS)
@pytest.mark.parametrize("name", sorted(G.MARKET))
def test_reencoded_market_rows_declared_synthetic_do_not_admit_a_price_rule(name, way):
    from bot.bt.pipeline import plan_pipeline
    rel, spec = G.MARKET[name]
    if not (REPO / rel).is_file():
        pytest.skip(f"{rel} is not in this environment")
    tmp = tempfile.mkdtemp(prefix="i4r2crit_origin_")
    try:
        os.makedirs(os.path.join(tmp, "data"), exist_ok=True)
        dst = os.path.join(tmp, "data", f"{name}_{way}.csv" + ("" if way == "decompressed" else ".gz"))
        spec = {**spec, **_rewrite(REPO / rel, dst, way)}
        if spec.get("compression") == "none":
            spec.pop("compression")
        ds = [{"name": name, "paths": [os.path.relpath(dst, tmp)], "spec": spec, "origin": "synthetic"}]
        # the origin rule is checked at planning (the worker's own grid plans only, its docstring); a later refusal
        # for another reason (a data anomaly without a named resolution) would not be this rule
        with pytest.raises(ValueError):
            plan_pipeline(root=tmp, datasets=ds, instruments=[{"name": name, "price": name, "with": []}],
                          strategy=PRICE_RULE, fill=G.FILL, costs=G.ZERO, purpose="動作確認")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
