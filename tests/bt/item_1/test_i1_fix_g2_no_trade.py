"""G-2 of K1 stage G (delegation docs/DATA/delegations/20261001_k1_stage_g_close.md §2-2): before the fix the data
layer could not read a bitFlyer lightchart 1-minute file: a minute with no trade is written with open/high/low/close
empty, and `loader._build` refused every blank field (ParseError ... is blank) -- `spec.synthetic` did not help (the
fields were read as numbers before the flag was looked at). Stage G worked around it by writing a copy without those
rows (scripts/k1_newenv_g_fold.py: filter_bitflyer). Rule after the fix (spec.py `no_trade`, anomalies.py): a bar spec
may DECLARE which price fields, all blank, mark a minute with no trade; such rows are reported (anomaly "no_trade",
one per row, counted in the manifest / data_quality) and dropped only by the named policy "drop". Partial blanks and
undeclared blanks are still refused. Synthetic files only, under pytest's tmp_path.
"""
from __future__ import annotations

import pytest

from bot.bt.data import ParseError, SpecError, UnresolvedAnomalyError, load
from bot.bt.data.stream import stream

NS = 1_000_000_000
T0 = 1514764800 * NS  # 2018-01-01T00:00:00Z
SPEC = {"format": "csv", "header": True, "delimiter": ",", "kind": "bar", "symbol": "FX_BTC_JPY", "asset": "crypto",
        "time": {"columns": ["ts"], "unit": "iso", "tz": "UTC"},
        "fields": {"open": "open", "high": "high", "low": "low", "close": "close", "volume": "volume"},
        "bar": {"interval_s": 60, "label": "start", "session": "24x7"}, "key": "start"}
NT = {**SPEC, "no_trade": {"fields": ["open", "high", "low", "close"]}}
# the shape of backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906 (header and a no-trade row as written there)
BODY = ("ts,open,high,low,close,volume,col7_inferred_long_oi\n"
        "2018-01-01T00:00:00+00:00,100,101,99,100.5,2.0,5.0\n"
        "2018-01-01T00:01:00+00:00,,,,,0.0,5.0\n"
        "2018-01-01T00:02:00+00:00,,,,,0.0,5.0\n"
        "2018-01-01T00:03:00+00:00,100.5,102,100,101,1.0,5.0\n")
P = "backtest_data/bf/candles_1m_2018.csv"


@pytest.fixture
def root(tmp_path):
    (tmp_path / "backtest_data" / "bf").mkdir(parents=True)
    (tmp_path / P).write_text(BODY)
    return str(tmp_path)


def ds(spec, body_path=P):
    return [{"name": "d", "paths": [body_path], "spec": spec}]


def test_without_the_declaration_a_blank_price_is_refused_as_before(root):
    with pytest.raises(ParseError, match="line 3: field 'open'.*is blank"):
        load(root, ds(SPEC))


def test_declared_no_trade_rows_are_reported_and_dropped_by_the_named_policy(root):
    r = load(root, ds(NT))
    assert [(a["kind"], a["line"]) for a in r.anomalies("d")] == [("no_trade", 3), ("no_trade", 4)]
    assert "no_trade" in r.checks("d") and "gap" in r.checks("d")  # the no-trade minutes are rows: not gaps
    with pytest.raises(UnresolvedAnomalyError, match="no_trade"):
        r.events("d")
    ev = r.events("d", {"no_trade": "drop"})
    assert [(int(e.start_time_ns) - T0) // (60 * NS) for e in ev] == [0, 3]
    m = r.manifest()["datasets"]["d"]
    assert m["anomalies"] == {"no_trade": 2} and m["resolution"] == {"no_trade": "drop"} and m["rows"] == 4
    assert r.records("d")[1] == {"start_ns": T0 + 60 * NS, "open": None, "high": None, "low": None, "close": None,
                                 "volume": 0.0}


def test_the_only_policy_is_drop(root):
    r = load(root, ds(NT))
    with pytest.raises(SpecError, match="no_trade"):
        r.events("d", {"no_trade": "accept"})


@pytest.mark.parametrize("row", ["2018-01-01T00:01:00+00:00,,,99,,0.0,5.0",        # only some of the declared fields
                                 "2018-01-01T00:01:00+00:00,100,101,99,100,,5.0"])  # a blank field not declared
def test_partial_or_undeclared_blanks_are_still_refused(tmp_path, row):
    (tmp_path / "backtest_data" / "bf").mkdir(parents=True)
    (tmp_path / P).write_text(BODY.splitlines()[0] + "\n" + row + "\n")
    with pytest.raises(ParseError, match="is blank"):
        load(str(tmp_path), ds(NT))


@pytest.mark.parametrize("bad", [{"fields": []}, {"fields": ["open", "open"]}, {"fields": ["px"]}, {}, {"fields": ["open"], "x": 1}])
def test_the_declaration_is_read_strictly(root, bad):
    with pytest.raises(SpecError, match="no_trade"):
        load(root, ds({**SPEC, "no_trade": bad}))


def test_no_trade_is_for_bars_only(root):
    trade = {"format": "csv", "header": True, "delimiter": ",", "kind": "trade", "symbol": "X", "asset": "crypto",
             "time": {"columns": ["ts"], "unit": "iso", "tz": "UTC"}, "fields": {"px": "open", "qty": "volume"},
             "no_trade": {"fields": ["open"]}}
    with pytest.raises(SpecError, match="kind 'bar' only"):
        load(root, ds(trade))


def test_the_stream_door_reads_the_same_declaration(root):
    s = stream(root, {"name": "d", "paths": [P], "spec": NT}, resolve={"no_trade": "drop"})
    chunks = list(s)
    assert [(int(e.start_time_ns) - T0) // (60 * NS) for e in chunks[0].events] == [0, 3]
    assert s.manifest()["dataset"]["anomalies"] == {"no_trade": 2}
