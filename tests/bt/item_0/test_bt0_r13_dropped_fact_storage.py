"""Round 13 (lead design round_7/LEAD_DESIGN.md s9.3 38): the contract's
`visibility.history_limit` states how the facts of dropped events are
stored -- 16 bytes per dropped event in two array('q'), one chunk per drop
(an array('q') of that drop's facts; a drop removes history_limit + 1
events of one type) until the strategy's next read folds the chunks in --
and why (a list of int, which exports no buffer, measured 88.2 bytes per
fact against 16.9). These tests hold the implementation to those words, so
the numbers in the contract cannot drift from the code.

The input space: every history_limit in 1..6 x every number of deliveries
of one type in 0..(6 * limit + 3) (so every phase of the N..2N cycle is
crossed several times), with the strategy's read done (a) never until the
end, (b) after every delivery, (c) while the strategy holds a memoryview of
the arrays it read before. Oracle: the dropped facts computed from the
inputs alone (the oldest deliveries, in order, whenever 2 * limit events of
the type are held before a delivery).

NOT covered (A-10): absolute sizes (sys.getsizeof of an empty array is
CPython's own; only the growth per fact is held, which is the item size);
several event types at once (each type has its own facts and chunks, the
code path is per type: tests/bt/item_0/test_bt0_history_limit.py and the
round 10 read oracle cover mixed types); the tracemalloc figures themselves
(measurements of the interpreter, not of the core: recorded in the
contract with their method).
"""
from __future__ import annotations

import sys
from array import array

import pytest

from bot.bt.core import EventType
from bot.bt.core.contract import CORE_CONTRACT
from bot.bt.core.history import DeliveredHistory, HistoryLists, read_dropped

from bt0_util import MS, T0, trade

_POS = tuple(EventType).index(EventType.TRADE)
_EMPTY = sys.getsizeof(array("q"))


def _expected_dropped(limit: int, n: int) -> list[int]:
    """Delivery numbers dropped after `n` deliveries of one type, from the
    contract's words alone: before a delivery, when 2 * limit are held, the
    oldest history_limit + 1 go."""
    held, gone = [], []
    for seq in range(1, n + 1):
        if len(held) >= 2 * limit:
            cut = limit + 1
            gone += held[:cut]
            held = held[cut:]
        held.append(seq)
    return gone


def _run(limit: int, n: int, read_each: bool, pin: bool):
    hist, lists = DeliveredHistory(limit), HistoryLists()
    facts = lists.dropped_facts()[_POS]
    views = []
    last = None
    for seq in range(1, n + 1):
        hist.append(trade(T0 + seq * MS), seq, T0 + seq * MS, EventType.TRADE, lists)
        if read_each:
            last = read_dropped(facts)
            if pin:
                views += [memoryview(last[0]), memoryview(last[1])]
    return hist, lists, facts, views, last


def test_the_contract_states_the_stored_form_and_the_measurement():
    text = CORE_CONTRACT["visibility"]["history_limit"]
    for words in ("16 bytes per dropped event", "a drop removes history_limit + 1 events",
                  "80 bytes plus 16 per dropped event", "16.9 bytes per fact", "88.2 bytes per fact"):
        assert words in text


@pytest.mark.parametrize("limit", range(1, 7))
def test_each_drop_appends_one_chunk_of_that_drop_s_facts(limit):
    n = 6 * limit + 3
    hist, lists, facts, _views, _last = _run(limit, n, read_each=False, pin=False)
    expected = _expected_dropped(limit, n)
    chunks = list(facts.pending)
    assert len(chunks) == len(expected) // (limit + 1)
    for i, chunk in enumerate(chunks):
        assert type(chunk) is array and chunk.typecode == "q" and chunk.itemsize == 8
        seqs = expected[i * (limit + 1):(i + 1) * (limit + 1)]
        assert list(chunk) == [x for s in seqs for x in (s, T0 + s * MS)]
        # the growth per dropped event is two int64: 16 bytes
        assert sys.getsizeof(chunk) - _EMPTY == 16 * (limit + 1)
    assert hist.dropped_count.get(EventType.TRADE, 0) == len(expected)


@pytest.mark.parametrize("limit", range(1, 7))
@pytest.mark.parametrize("mode", ["read_at_end", "read_each", "read_each_pinned"])
def test_the_strategy_s_read_folds_the_chunks_into_16_bytes_per_fact(limit, mode):
    for n in range(0, 6 * limit + 4):
        _hist, _lists, facts, views, last = _run(limit, n, read_each=mode != "read_at_end",
                                                  pin=mode == "read_each_pinned")
        seqs, recvs = read_dropped(facts)
        expected = _expected_dropped(limit, n)
        assert list(seqs) == expected
        assert list(recvs) == [T0 + s * MS for s in expected]
        assert len(facts.pending) == 0
        for a in (seqs, recvs):
            assert type(a) is array and a.typecode == "q" and a.itemsize == 8
            # what the array holds beyond its header: 8 bytes per fact plus
            # array's own over-allocation (at most 1/16 + 7 items)
            assert sys.getsizeof(a) - _EMPTY <= 8 * (len(a) + len(a) // 16 + 8)
        if mode == "read_each_pinned" and last is not None:
            # a view the strategy holds keeps what it held; the read is whole
            assert list(last[0]) == expected
        del views
