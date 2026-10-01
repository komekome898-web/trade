"""Round 2 of the k1 env fixes, (d)1 (delegation docs/DATA/delegations/20260927_k1_env_fixes.md §4): the data layer
read a ledger-sealed file's bytes (open + read + sha256) BEFORE it refused it (loader._read_file before round 2:
open, read, then SealRegistry.match, then check_range). Rule after the fix (bot.bt.data.allowlist docstring):

- a file the seal record names by its real path, read without a range ending at or before its cutoff, is refused
  BEFORE it is opened (0 opens of the file);
- the same file read with a range ending at or before its cutoff is read (only rows before the cutoff are kept);
- a byte copy under another name is refused before its bytes are decoded, and the sealed file itself is not opened
  (the copy's md5 is compared with the md5 the seal record wrote);
- a copy of a sealed file whose bytes changed after the record was written (the recorded md5 is stale) is still
  refused (same size as the sealed file now: the sealed file's current bytes are hashed, never decoded);
- a file of the same size that is not a copy is read.

The same door serves the stream loader (bot.bt.data.stream), the repro runner's planning (it hashed every data
file with open() before round 2), the integrated run's planning (bot.bt.pipeline) and
bot.bt.validation.sealed_access.read_table. Synthetic files only, under pytest's tmp_path.
"""
from __future__ import annotations

import json
import os
import sys

import pytest

import bot.bt.data.loader as L
from bot.bt.data import SealedRangeError, load
from bot.bt.data.stream import stream
from bot.bt.repro.errors import ReproError
from bot.bt.repro.runner import DataInput, plan_run
from bot.bt.validation import sealed_access

NS = 1_000_000_000
T2020 = 1577836800 * NS  # 2020-01-01T00:00:00Z
SPEC = {"format": "csv", "header": True, "delimiter": ",", "kind": "bar", "symbol": "X", "asset": "crypto",
        "time": {"columns": ["ts"], "unit": "iso", "tz": "UTC"},
        "fields": {"open": "o", "high": "h", "low": "l", "close": "c", "volume": "vol"},
        "bar": {"interval_s": 60, "label": "start"}, "key": "start"}
BODY = ("ts,o,h,l,c,vol\n"
        "2019-12-31T23:58:00,1,2,0.5,1.5,1\n"
        "2019-12-31T23:59:00,1.5,2,1,1.25,1\n"
        "2020-01-01T00:00:00,1.25,2,1,1.75,1\n")
SEALED = "backtest_data/x/sealed.csv"

RULES = {"off_tick": "reject", "below_min_qty": "reject", "off_step": "reject", "market_remainder": "cancel",
         "market_ref": "next_bar_open"}  # the item-4 tests' bar rules (tests/bt/item_4/i4w_decl.py)

_OPENED: list = []
_WATCH: list = []  # real paths whose opens are recorded (an audit hook cannot be removed: it records only these)


def _hook(event, args):
    if event == "open" and _WATCH and args and isinstance(args[0], (str, bytes, os.PathLike)):
        p = os.path.realpath(os.fsdecode(args[0]))
        if p in _WATCH:
            _OPENED.append(p)


sys.addaudithook(_hook)


def _md5(b: bytes) -> str:
    import hashlib
    return hashlib.md5(b).hexdigest()


@pytest.fixture
def env(tmp_path):
    """A data root with one sealed file (sealed from 2020-01-01; its record carries the md5 of its bytes)."""
    root = tmp_path
    (root / "backtest_data" / "x").mkdir(parents=True)
    (root / "backtest_data" / "y").mkdir(parents=True)
    (root / "backtest_data" / "phase2_sealed" / "U").mkdir(parents=True)
    (root / SEALED).write_bytes(BODY.encode())
    rec = {"unit": "U", "forward_start": "2020-01-01T00:00:00+00:00",
           "files": [{"path": SEALED, "time_column": "ts", "seal_from_ts": "2020-01-01T00:00:00+00:00",
                      "md5": _md5(BODY.encode())}]}
    (root / "backtest_data" / "phase2_sealed" / "U" / "SEALED.json").write_text(json.dumps(rec))
    _OPENED.clear()
    _WATCH[:] = [os.path.realpath(root / SEALED)]
    yield root
    _WATCH.clear()
    _OPENED.clear()


@pytest.fixture
def no_decode(monkeypatch):
    """Records every decode of a file's bytes by the data layer."""
    seen = []
    orig = L._decode

    def spy(raw, spec, given):
        seen.append(given)
        return orig(raw, spec, given)

    monkeypatch.setattr(L, "_decode", spy)
    return seen


def _ds(path, **kw):
    return {"name": "d", "paths": [path], "spec": SPEC, **kw}


@pytest.mark.parametrize("range_ns", [None, [0, T2020 + 60 * NS]], ids=["no_range", "range_past_cutoff"])
def test_sealed_by_path_is_refused_unopened(env, no_decode, range_ns):
    with pytest.raises(SealedRangeError):
        load(str(env), [_ds(SEALED, **({"range_ns": range_ns} if range_ns else {}))])
    assert _OPENED == [] and no_decode == []


def test_sealed_by_path_with_a_range_before_the_cutoff_is_read(env):
    got = load(str(env), [_ds(SEALED, range_ns=[0, T2020])]).records("d")
    assert len(got) == 2 and _OPENED  # read: the two rows before the cutoff


def test_a_byte_copy_is_refused_undecoded_without_opening_the_sealed_file(env, no_decode):
    (env / "backtest_data" / "y" / "copy.csv").write_bytes(BODY.encode())
    with pytest.raises(SealedRangeError):
        load(str(env), [_ds("backtest_data/y/copy.csv")])
    assert _OPENED == [] and no_decode == []


def test_a_copy_of_a_sealed_file_changed_after_its_record_is_refused(env, no_decode):
    changed = BODY.replace("1.75", "1.85").encode()  # same size, other bytes than the record's md5
    (env / SEALED).write_bytes(changed)
    (env / "backtest_data" / "y" / "copy.csv").write_bytes(changed)
    with pytest.raises(SealedRangeError):
        load(str(env), [_ds("backtest_data/y/copy.csv")])
    assert no_decode == []  # the sealed file was hashed (opened), never decoded


def test_a_same_size_file_that_is_not_a_copy_is_read(env):
    other = BODY.replace("1.75", "1.95").encode()
    (env / "backtest_data" / "y" / "other.csv").write_bytes(other)
    assert len(load(str(env), [_ds("backtest_data/y/other.csv")]).records("d")) == 3


def test_the_stream_loader_uses_the_same_door(env, no_decode):
    with pytest.raises(SealedRangeError):
        for _ in stream(str(env), _ds(SEALED)):
            pass
    assert _OPENED == [] and no_decode == []


def test_the_repro_runner_does_not_read_a_sealed_file_to_hash_it(env):
    with pytest.raises(ReproError, match="SealedRangeError"):
        plan_run(root=str(env), data=[DataInput(SEALED, SPEC)], config={}, seed=1, setup=None, purpose="動作確認")
    assert _OPENED == []


def test_the_integrated_run_does_not_read_a_sealed_file_to_hash_it(env):
    from bot.bt.pipeline import PipelineError, plan_pipeline
    with pytest.raises(PipelineError, match="SealedRangeError"):
        plan_pipeline(root=str(env), datasets=[{**_ds(SEALED), "origin": "real"}],
                      instruments=[{"name": "i", "price": "d", "with": [], "rules": RULES,
                                    "product": {"symbol": "X", "venue": "test", "tick": 1e-9, "min_qty": 1e-8,
                                                "qty_step": 1e-8, "quote_ccy": "JPY", "margin": True}}],
                      strategy={"kind": "schedule", "orders": [{"t_ns": T2020, "side": "buy", "qty": 1.0,
                                                                "instrument": "i"}]},
                      fill={"optimistic": {"tier": 3}, "pessimistic": {"tier": 1}},
                      latency={ch: {"kind": "constant", "ns": 0} for ch in ("feed", "order", "cancel", "notice")},
                      costs={"maker_rate": 0.0, "taker_rate": 0.0, "spread": 0.0, "source": "動作確認: 費用 0 を宣言"},
                      account={"currency": "JPY", "cash": 1e12, "leverage": 1.0, "mark": "last_trade",
                               "liquidation": None, "margin_check": "open_orders"},
                      purpose="動作確認")
    assert _OPENED == []


def test_read_table_uses_the_same_door(env):
    with pytest.raises(sealed_access.SealedRefused):
        sealed_access.read_table(str(env), SEALED, time_column="ts")
    assert _OPENED == []
