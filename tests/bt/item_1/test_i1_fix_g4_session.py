"""G-4 of K1 stage G (delegation docs/DATA/delegations/20261001_k1_stage_g_close.md §2-4): before the fix the gap and
off_grid checks ran only when a bar spec wrote `bar.session` (anomalies.py: `spec.bar.session in ("24x7", "24x5")`),
and the key was optional: leaving it out turned the checks off silently (Binance 2018 read without it gave only
`synthetic` anomalies). Rule after the fix (spec.py): `bar.session` is required for asset crypto and fx (refused
before any file is opened); for asset jpx (no exchange calendar in the layer) it may be left out, and the result says
which checks did not run and why (`LoadResult.checks_not_run`, manifest `checks_not_run`).
"""
from __future__ import annotations

import pytest

from bot.bt.data import SpecError, load

NS = 1_000_000_000
BASE = {"format": "csv", "header": True, "delimiter": ",", "kind": "bar", "symbol": "X",
        "time": {"columns": ["ts"], "unit": "iso", "tz": "UTC"},
        "fields": {"open": "o", "high": "h", "low": "l", "close": "c", "volume": "v"}, "key": "start"}
BODY = ("ts,o,h,l,c,v\n2018-01-01T00:00:00,1,2,0.5,1.5,1\n2018-01-01T00:01:30,1,2,0.5,1.5,1\n"
        "2018-01-01T00:04:00,1,2,0.5,1.5,1\n")
P = "backtest_data/x/bars.csv"


@pytest.fixture
def root(tmp_path):
    (tmp_path / "backtest_data" / "x").mkdir(parents=True)
    (tmp_path / P).write_text(BODY)
    return str(tmp_path)


def spec(asset, session=None):
    bar = {"interval_s": 60, "label": "start"}
    if session:
        bar["session"] = session
    return {**BASE, "asset": asset, "bar": bar}


@pytest.mark.parametrize("asset", ["crypto", "fx"])
def test_an_omitted_session_is_refused_for_crypto_and_fx(root, asset):
    with pytest.raises(SpecError, match="session is required for asset"):
        load(root, [{"name": "d", "paths": [P], "spec": spec(asset)}])


def test_crypto_24x7_runs_gap_and_off_grid(root):
    r = load(root, [{"name": "d", "paths": [P], "spec": spec("crypto", "24x7")}])
    kinds = sorted(a["kind"] for a in r.anomalies("d"))
    assert kinds == ["gap", "gap", "gap", "off_grid"] and r.checks_not_run("d") == {}


def test_fx_24x5_runs_off_grid_and_says_gap_did_not_run(root):
    r = load(root, [{"name": "d", "paths": [P], "spec": spec("fx", "24x5")}])
    assert sorted(a["kind"] for a in r.anomalies("d")) == ["off_grid"]
    assert set(r.checks_not_run("d")) == {"gap"}
    assert r.manifest()["datasets"]["d"]["checks_not_run"] == r.checks_not_run("d")


def test_jpx_may_leave_it_out_and_the_result_says_the_calendar_checks_did_not_run(root):
    r = load(root, [{"name": "d", "paths": [P], "spec": spec("jpx")}])
    assert r.anomalies("d") == [] and "gap" not in r.checks("d")
    nr = r.checks_not_run("d")
    assert set(nr) == {"gap", "off_grid"} and "asset 'jpx'" in nr["gap"]
    assert r.manifest()["datasets"]["d"]["checks_not_run"] == nr
