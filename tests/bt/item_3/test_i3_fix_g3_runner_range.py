"""G-3 of K1 stage G (delegation docs/DATA/delegations/20261001_k1_stage_g_close.md §2-3): before the fix the record
door `bot.bt.repro.runner` read every input without a range (runner.py: `seals.read_checked(..., None)  # the run
loads without a range`; `load(plan.root, datasets)` with no range_ns), so a file the seal ledger lists could not be an
input at all, and stage G fed the runner edited copies the ledger does not know. Rule after the fix: `DataInput`
has `range_ns`; a ledger-listed file is an input when its range ends at or before the seal's cutoff (the data layer
reads only that range), the range is in the run's identity and record.json; a range ending after the cutoff (or none)
is refused at planning, before the file is opened (RunSealedRangeError: a ReproError and a SealedRangeError).
Synthetic files only, under pytest's tmp_path.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

import pytest

from bot.bt.data import SealedRangeError
from bot.bt.repro.errors import ReproError, RunSealedRangeError
from bot.bt.repro.runner import DataInput, plan_run, run
from bot.strategy.k1_xvenue import K1XSetup

NS = 1_000_000_000
T2020 = 1577836800 * NS  # 2020-01-01T00:00:00Z
SPEC = {"format": "csv", "header": True, "delimiter": ",", "kind": "bar", "symbol": "X", "asset": "crypto",
        "time": {"columns": ["ts"], "unit": "iso", "tz": "UTC"},
        "fields": {"open": "o", "high": "h", "low": "l", "close": "c", "volume": "vol"},
        "bar": {"interval_s": 60, "label": "start", "session": "24x7"}, "key": "start"}
BODY = ("ts,o,h,l,c,vol\n"
        "2019-12-31T23:58:00,1,2,0.5,1.5,1\n"
        "2019-12-31T23:59:00,1.5,2,1,1.25,1\n"
        "2020-01-01T00:00:00,1.25,2,1,1.75,1\n")
SEALED = "backtest_data/x/sealed.csv"
CFG = {"instrument": "BTCUSDT", "foot_min": 1, "gate": {"s": "19", "b": "24"}, "strength": "weak", "mode": "single",
       "fill": "last_bar_close", "costs": {"maker_fee_rate": 0, "taker_fee_rate": 0, "source": "test"},
       "streams": {"signal": ["d0"], "price": ["d0"]}, "prepare": "none"}
LO = T2020 - 120 * NS
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))  # the git checkout

_OPENED: list = []
_WATCH: list = []


def _hook(event, args):
    if event == "open" and _WATCH and args and isinstance(args[0], (str, bytes, os.PathLike)):
        if os.path.realpath(os.fsdecode(args[0])) in _WATCH:
            _OPENED.append(args[0])


sys.addaudithook(_hook)


@pytest.fixture
def env(tmp_path):
    root = tmp_path
    (root / "backtest_data" / "x").mkdir(parents=True)
    (root / "backtest_data" / "phase2_sealed" / "U").mkdir(parents=True)
    (root / SEALED).write_bytes(BODY.encode())
    rec = {"unit": "U", "forward_start": "2020-01-01T00:00:00+00:00",
           "files": [{"path": SEALED, "time_column": "ts", "seal_from_ts": "2020-01-01T00:00:00+00:00",
                      "md5": hashlib.md5(BODY.encode()).hexdigest()}]}
    (root / "backtest_data" / "phase2_sealed" / "U" / "SEALED.json").write_text(json.dumps(rec))
    _OPENED.clear()
    _WATCH[:] = [os.path.realpath(root / SEALED)]
    yield root
    _WATCH.clear()


def _args(root, rng):
    return dict(root=str(root), data=[DataInput(SEALED, SPEC, {"gap": "accept"}, rng)], config=CFG, seed=0,
                setup=K1XSetup(), purpose="動作確認", repo=REPO)


def test_a_sealed_file_is_an_input_with_a_range_that_ends_at_the_cutoff(env, tmp_path):
    res = run(runs_dir=str(tmp_path / "runs"), **_args(env, (LO, T2020)))
    assert res.record["data"][0]["range_ns"] == [LO, T2020]  # the range stays in record.json
    with open(os.path.join(res.run_dir, "data_quality.json"), encoding="utf-8") as fh:
        man = json.load(fh)["data"]["manifest"]
    assert man["datasets"]["d0"]["range_ns"] == [LO, T2020] and man["datasets"]["d0"]["rows"] == 2
    assert [f["sealed_unit"] for f in man["files"]] == ["U"]
    assert res.record["engine"]["source_events"] == 2  # the 2020-01-01 row (sealed) never became an event


@pytest.mark.parametrize("rng", [None, (LO, T2020 + 60 * NS)])
def test_a_range_missing_or_ending_after_the_cutoff_stops_the_run_before_the_file_is_opened(env, rng):
    with pytest.raises(RunSealedRangeError) as ei:
        plan_run(**_args(env, rng))
    assert isinstance(ei.value, SealedRangeError) and isinstance(ei.value, ReproError)
    assert _OPENED == []


def test_the_range_is_part_of_the_identity_and_absent_when_not_given(env):
    a = plan_run(**_args(env, (LO, T2020)))
    b = plan_run(**_args(env, (LO - 60 * NS, T2020)))
    assert a.run_id != b.run_id and a.identity["data"][0]["range_ns"] == [LO, T2020]
    (env / "backtest_data" / "x" / "free.csv").write_text(BODY.replace("1.25,2,1,1.75", "1.25,2,1,1.5"))
    c = plan_run(**{**_args(env, None), "data": [DataInput("backtest_data/x/free.csv", SPEC, {"gap": "accept"})]})
    assert "range_ns" not in c.identity["data"][0]


@pytest.mark.parametrize("bad", [(T2020, LO), (LO,), [LO, 1.5], "x"])
def test_a_malformed_range_is_refused(env, bad):
    with pytest.raises(ReproError, match="range_ns"):
        plan_run(**_args(env, bad))
