"""The data layer's bar session "24x5" (FX: closed at the weekend), added for
the integrated run (item 4): accepted by the declaration; the off_grid check
runs; the gap check does not (the layer has no weekly-close calendar), so it
is not listed in the dataset's checks. The grid: session {24x7, 24x5, none}
x rows {on the grid, one off the grid, one missing start} (9 cells)."""
from __future__ import annotations

import os
import tempfile

import pytest

from bot.bt.data import load
from bot.bt.data.errors import SpecError

ROWS = {"clean": [0, 60, 120, 180], "off_grid": [0, 60, 150, 180], "gap": [0, 60, 180, 240]}


def _load(session, rows):
    root = tempfile.mkdtemp()
    p = "backtest_data/fx_1m_synth/x.csv"
    os.makedirs(os.path.join(root, os.path.dirname(p)))
    with open(os.path.join(root, p), "w") as fh:
        fh.write("ts,open,high,low,close,volume\n")
        for s in rows:
            fh.write(f"{1767571200 + s},157.0,157.1,156.9,157.0,1\n")
    bar = {"interval_s": 60, "label": "start"}
    if session:
        bar["session"] = session
    spec = {"format": "csv", "header": True, "delimiter": ",", "kind": "bar", "symbol": "USDJPY", "asset": "fx",
            "time": {"columns": ["ts"], "unit": "s", "tz": "UTC"},
            "fields": {"open": "open", "high": "high", "low": "low", "close": "close", "volume": "volume"},
            "bar": bar, "key": "start"}
    r = load(root, [{"name": "d", "paths": [p], "spec": spec}])
    return r.checks("d"), sorted({a["kind"] for a in r.anomalies("d")})


EXPECT = {
    ("24x7", "clean"): (True, True, []), ("24x7", "off_grid"): (True, True, ["gap", "off_grid"]),
    ("24x7", "gap"): (True, True, ["gap"]),
    ("24x5", "clean"): (False, True, []), ("24x5", "off_grid"): (False, True, ["off_grid"]),
    ("24x5", "gap"): (False, True, []),
    (None, "clean"): (False, False, []), (None, "off_grid"): (False, False, []), (None, "gap"): (False, False, []),
}


@pytest.mark.parametrize("session,rows", list(EXPECT))
def test_session_checks(session, rows):
    checks, kinds = _load(session, ROWS[rows])
    gap_runs, off_runs, want = EXPECT[(session, rows)]
    assert ("gap" in checks) == gap_runs and ("off_grid" in checks) == off_runs
    assert kinds == want


def test_an_unknown_session_is_refused():
    with pytest.raises(SpecError, match="session"):
        _load("24x6", ROWS["clean"])
