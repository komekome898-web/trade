"""Scene set, item 0, round f2 (i0-r17-03): a `de_error` is credited as the tool's refusal only when the tool
received the call. Whether the tool received it is read from the driver's own source (survey_results/attempts/61.log,
the `match which` arms that call `bde::...`), not from the adapter's constant.

Grid: every name the driver dispatches, every name an entry of `_units` calls, and names the driver does not have
{"no_such_deserializer", ""} x every row the driver can print {tool Err, the driver's own "unknown deserializer",
de_ns, nothing}. Oracle: CompiledRefusal iff the name is a driver arm AND the row is a `de_error` the tool printed.
Not in the grid: rows with several keys (the driver prints one key per call: 61.log 377-382), a driver that is not
the configured one (the critic's test runs the real binary).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

B = Path(__file__).resolve().parent
for p in (B, B / "adapters", B / "opponents"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import common as C  # noqa: E402
import barter_adapter as BA  # noqa: E402

LOG = B / "survey_results" / "attempts" / "61.log"
ARMS = set(re.findall(r'"(de_[a-z0-9_]+)"\s*=>\s*bde::', LOG.read_text(encoding="utf-8")))
CALLED = set(re.findall(r'self\._de\("([a-z0-9_]+)"', (B / "opponents" / "barter_adapter.py").read_text(encoding="utf-8")))
NAMES = sorted(ARMS | CALLED | {"no_such_deserializer", ""})
ROWS = {"tool_err": {"de_error": "invalid digit found in string"},
        "driver_unknown": {"de_error": "unknown deserializer x"},
        "ns": {"de_ns": 5},
        "none": None}


def test_the_driver_arms_are_read_and_every_entry_calls_one():
    assert len(ARMS) == 4
    assert CALLED and CALLED <= ARMS


@pytest.mark.parametrize("row", sorted(ROWS))
@pytest.mark.parametrize("name", NAMES)
def test_only_a_received_call_is_credited(name, row, monkeypatch):
    printed = ROWS[row]
    monkeypatch.setattr(BA, "drv", lambda payload: [printed] if printed is not None else [])
    received = name in ARMS
    credited = received and row == "tool_err"
    try:
        BA.BarterAdapter._de(name, "1")
    except C.CompiledRefusal:
        assert credited, (name, row)
        return
    except Exception:
        assert not credited, (name, row)
        return
    assert received and row == "ns", (name, row)
