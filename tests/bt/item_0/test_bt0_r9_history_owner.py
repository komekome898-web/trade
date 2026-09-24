"""Round 9 (i0-r8-02, i0-r8-03): the core's history lists refuse every
change through their own behaviour, and the contract says how to read "the
last k events". Written in the same step as the fix (not before it, unlike
test_bt0_r9_reachable_state_adversary.py); run against the round-8 code it
fails (round_9 worker log item0_r9_worker_history_on_head.log).

The input space is taken from `list` itself, not from the class's refusal
list: every callable name of `dir(list)` is called on a plain list with
every argument shape of a small grid; the names that changed the plain
list's contents or raised no error on changing arguments are the changers.
Each is then called the same ways on the core's list, which must refuse it
(an exception) and keep its contents and `dropped`. Every attribute
assignment and deletion (the slot's own name, `dropped`, `__class__`, a new
name) and `__init__` on a made list are refused too.

NOT in the lists: `list`'s own methods called on the core's list
(`list.__init__(lst, ...)`, `object.__setattr__(lst, ...)`): outside the
contract, like `tuple.__getitem__` on an answer, and they reach only what
the strategy reads (the core never reads a list back: the reachable-state
adversary, test_bt0_r9_reachable_state_adversary.py, attacks the lists
with exactly those methods and checks the core).
"""
from __future__ import annotations

import pytest

from bot.bt.core import CORE_CONTRACT, CoreEngine, EventType, TradeEvent
from bot.bt.core.errors import BeforeFirstEventError, DroppedPositionError
from bot.bt.core.history import DeliveredList

T0 = 1_700_000_000_000_000_000
SEC = 1_000_000_000

_ARGS = [(), (0,), (1,), (-1,), ("x",), (0, "x"), (["x"],), (("x",),), (slice(0, 1),), (slice(0, 1), ["x"]),
         (2,), (0, 1), ([],)]


def _changers_of_plain_list() -> list[str]:
    """Every name of `list` that changes a plain list's contents for some
    argument shape of the grid (found by calling it, not by reading a
    list of names)."""
    out = []
    for name in sorted(dir(list)):
        if name in ("__class__", "__new__", "__init_subclass__", "__subclasshook__", "__class_getitem__"):
            continue
        attr = getattr(list, name)
        if not callable(attr):
            continue
        for args in _ARGS:
            plain = list(_ITEMS)
            try:
                getattr(plain, name)(*args)
            except Exception:  # noqa: BLE001 - that shape does not fit this method
                continue
            if plain != _ITEMS:
                out.append(name)
                break
    return out


_ITEMS = ["c", "x", "a"]  # unsorted, and holding the grid's "x": sort and remove change it


def _made():
    return DeliveredList._made(list(_ITEMS), 2)


def test_the_changers_are_found_from_list_itself():
    changers = _changers_of_plain_list()
    # the grid reaches every mutating method of list (a guard on the grid, not on the class)
    assert {"append", "extend", "insert", "pop", "remove", "clear", "sort", "reverse", "__setitem__",
            "__delitem__", "__iadd__", "__imul__", "__init__"} <= set(changers), changers


@pytest.mark.parametrize("name", _changers_of_plain_list())
def test_every_changer_of_list_is_refused_on_the_core_s_list(name):
    for args in _ARGS:
        lst = _made()
        try:
            getattr(lst, name)(*args)
        except Exception:  # noqa: BLE001 - refused (or that shape does not fit): the contents must hold
            pass
        else:
            pytest.fail(f"{name}{args!r} was accepted")
        assert list.__getitem__(lst, slice(None)) == _ITEMS and lst.dropped == 2, (name, args)


@pytest.mark.parametrize("name", ["dropped", "_dropped", "__class__", "x", "__dict__"])
def test_attributes_cannot_be_assigned_or_deleted(name):
    lst = _made()
    with pytest.raises((TypeError, AttributeError)):
        setattr(lst, name, 7)
    with pytest.raises((TypeError, AttributeError)):
        delattr(lst, name)
    assert type(lst) is DeliveredList and lst.dropped == 2 and list.__len__(lst) == 3


def test_it_is_made_by_the_core_only():
    with pytest.raises(TypeError):
        DeliveredList(["a"])
    with pytest.raises(TypeError):
        DeliveredList()


def test_the_critic_s_changes_are_refused_in_a_run_and_the_view_is_whole():
    """The critic's probe (i0-r8-02): `__init__` and `dropped =` through the
    list's own behaviour, from a callback; the next read shows every
    delivered event."""
    seen = {}

    class S:
        def __init__(self):
            self.k = 0

        def on_event(self, event, ctx):
            self.k += 1
            if self.k != 3:
                return
            lst = ctx._StrategyContext__visible_events._log
            for label, act in (("__init__", lambda: lst.__init__([lst[0]], 0)),
                               ("dropped =", lambda: setattr(lst, "dropped", 7)),
                               ("append", lambda: lst.append(1))):
                try:
                    act()
                    seen[label] = "accepted"
                except Exception as exc:  # noqa: BLE001
                    seen[label] = type(exc).__name__
            seen["after"] = len(ctx.visible_events())

    CoreEngine(S(), [TradeEvent(received_time_ns=T0 + i * SEC, price=100.0, size=1.0, side="buy")
                     for i in range(5)]).run()
    assert seen == {"__init__": "TypeError", "dropped =": "TypeError", "append": "TypeError", "after": 3}


# --- i0-r8-03: "the last k" -------------------------------------------------------

def test_the_contract_says_how_to_read_the_last_k_events():
    text = CORE_CONTRACT["visibility"]["position_rule"]["last_k"]
    assert "visible_events(n=k)" in text and "[-k:]" in text


def test_the_last_k_reads_as_the_contract_says():
    """[-k:] with fewer than k delivered raises BeforeFirstEventError;
    n=k returns all that were delivered (or the last k)."""
    got = []

    class S:
        def on_event(self, event, ctx):
            delivered = int(event.seq)
            for k in range(1, 7):
                ans = ctx.visible_events(n=k)
                assert len(ans) == min(k, delivered)
                if k > delivered:
                    with pytest.raises(BeforeFirstEventError):
                        ctx.visible_events()[-k:]
                else:
                    assert ctx.visible_events()[-k:] == ans
            got.append(delivered)

    CoreEngine(S(), [TradeEvent(received_time_ns=T0 + i * SEC, price=100.0, size=1.0, side="buy")
                     for i in range(5)]).run()
    assert got == [1, 2, 3, 4, 5]


def test_the_last_k_past_the_dropped_part_names_dropped_events():
    """Under history_limit, a window's [-k:] reaching before its oldest kept
    event names a dropped event (DroppedPositionError); n=k is the way."""
    seen = []

    class S:
        def on_event(self, event, ctx):
            win = ctx._StrategyContext__visible_events
            kept = len(win)
            if int(event.seq) > kept:
                with pytest.raises(DroppedPositionError):
                    win[-(kept + 1):]
                seen.append(kept)

    CoreEngine(S(), [TradeEvent(received_time_ns=T0 + i * SEC, price=100.0, size=1.0, side="buy")
                     for i in range(8)], history_limit=2).run()
    assert seen  # history_limit dropped some
