"""Critic, item 0, round 14 (i0-r14-01, i0-r14-02): contract core-15
`process_state` says "what the core accepts, refuses or computes is decided by
the value and by objects bound when the core was loaded -- never by
process-wide state read at run time ... no ABC is asked about a class ...
sys.modules or a module's attributes are never read to decide ... So a
registration, a subclass hook, ... -- made by any party, in any earlier run of
the process -- changes no value, refusal or result of the core, and runs no
code of that party."

The worker's grid (tests/bt/item_0/test_bt0_r14_process_state.py) proves the
core's OWN SOURCE asks no ABC (it reads the isinstance / issubclass / is_a in
the core's files). Two routes it does not see:

(i0-r14-01) The core rebuilds sets and dicts from settled values
(values.py `_settle` / `_freeze`), which compares elements whose hashes
collide. Equality of a Fraction with a Decimal (or a float, a complex) is
library code that asks the numbers ABCs: `Fraction.__eq__` does
`isinstance(b, numbers.Rational)` (and the C decimal asks
`isinstance(w, Rational)`). Fraction(1) and Decimal(2**61) hash alike
(1 mod 2**61-1) and are not equal.

(i0-r14-02) values.py `_make_copier` / `_make_rebuilder` run
`import dataclasses` INSIDE the function (a read of sys.modules at run time)
the first time a carrier class is copied / taken, and keep the result in the
module-level caches `_COPIERS` / `_REBUILDERS` for the rest of the process.

Grid: route {extra of the strategy's own order; extra of the account's forced
order} x change {none; register Decimal with numbers.Rational; a Rational
subclass whose metaclass hook answers (logs where it ran)} for (i0-r14-01);
{sys.modules['dataclasses'] replaced by a module of the strategy's for ONE
callback, then put back} for (i0-r14-02). Oracle: the same run gives the same
result in one process as in a fresh one, and no code of the strategy runs
outside its own on_event.

Every case runs in a FRESH interpreter (subprocess): a registration and a
filled module cache cannot be undone.

Not in the grid: rebinding a function the core calls (dataclasses.fields,
heapq.heappush), which the contract names "not covered"; this grid only
swaps a MODULE in sys.modules, which the contract says is never read.
"""
from __future__ import annotations

import os
import subprocess
import sys
import textwrap

SRC = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "src")


def _run(code: str) -> str:
    env = dict(os.environ, PYTHONPATH=os.path.abspath(SRC))
    out = subprocess.run([sys.executable, "-c", textwrap.dedent(code)], capture_output=True, text=True,
                         env=env, timeout=120)
    assert out.returncode == 0, out.stderr[-2000:]
    return out.stdout.strip()


EQ_PRELUDE = '''
    import abc, collections.abc, numbers
    from decimal import Decimal
    from fractions import Fraction
    from bot.bt.core import BarEvent, CoreEngine
    from bot.bt.core.api import OrderRequest
    from bot.bt.core.interfaces import NullCostModel
    from bot.bt.core.testing import ImmediateFillModel, RecordingAccount

    T0 = 1_700_000_000_000_000_000
    INSIDE = [False]
    OUTSIDE = []
    KEEP = []
    assert hash(Fraction(1)) == hash(Decimal(2**61)) and Fraction(1) != Decimal(2**61)
    EXTRA = (("k", {Fraction(1): "a", Decimal(2**61): "b"}),)

    class HookMeta(abc.ABCMeta):
        def __subclasscheck__(cls, sub):
            if not INSIDE[0]:
                OUTSIDE.append(getattr(sub, "__name__", "?"))
            return False

    def bump():
        class Fresh:
            pass
        KEEP.append(Fresh)
        collections.abc.Sized.register(Fresh)  # clears every ABC's negative cache

    class S:
        def __init__(self, change):
            self.change, self.n = change, 0
        def on_event(self, ev, ctx):
            INSIDE[0] = True
            try:
                self.n += 1
                if self.n != 1:
                    return
                if self.change == "register":
                    numbers.Rational.register(Decimal)
                elif self.change == "hook":
                    class Evil(numbers.Rational, metaclass=HookMeta):
                        pass
                    KEEP.append(Evil)
                    bump()
                if self.change != "quiet":
                    ctx.place_order(OrderRequest(side="buy", order_type="market", size=1.0,
                                                 client_order_id="o1", extra=EXTRA))
                if self.change == "hook":
                    bump()
            finally:
                INSIDE[0] = False

    class ForcingAccount(RecordingAccount):
        def on_market_event(self, event, t):
            super().on_market_event(event, t)
            if event.received_time_ns == T0 + 10:
                return [OrderRequest(side="sell", order_type="market", size=1.0,
                                     client_order_id="forced-1", extra=EXTRA)]
            return []

    def run(change, account=False):
        bars = [BarEvent(received_time_ns=T0 + k, open=100.0, high=100.0, low=100.0, close=100.0, volume=1.0)
                for k in (0, 10, 20)]
        eng = CoreEngine(S(change), bars, fill_model=ImmediateFillModel(100.0),
                         account=ForcingAccount() if account else RecordingAccount(),
                         cost_model=NullCostModel())
        try:
            eng.run()
            return "ok"
        except BaseException as exc:
            return type(exc).__name__
'''


def test_another_runs_registration_does_not_change_the_same_run():
    out = _run(EQ_PRELUDE + '''
    a1 = run("none")
    b = run("register")
    a2 = run("none")
    print(a1, b, a2)
    ''')
    a1, b, a2 = out.split()
    assert a1 == "ok"
    assert a2 == a1, f"the same run in one process: {a1} before, {a2} after another run's registration ({b})"


def test_the_strategys_registration_does_not_change_the_accounts_forced_order():
    out = _run(EQ_PRELUDE + '''
    print(run("quiet", account=True))
    ''')
    clean = out
    out2 = _run(EQ_PRELUDE + '''
    class Q(S):
        def on_event(self, ev, ctx):
            if ev.received_time_ns == T0:
                numbers.Rational.register(Decimal)
    bars = [BarEvent(received_time_ns=T0 + k, open=100.0, high=100.0, low=100.0, close=100.0, volume=1.0)
            for k in (0, 10, 20)]
    try:
        CoreEngine(Q("quiet"), bars, fill_model=ImmediateFillModel(100.0), account=ForcingAccount(),
                   cost_model=NullCostModel()).run()
        print("ok")
    except BaseException as exc:
        print(type(exc).__name__)
    ''')
    assert clean == "ok"
    assert out2 == clean, f"the account's forced order: {clean} without, {out2} after the strategy's registration"


def test_no_hook_of_the_strategy_runs_outside_its_call_through_numeric_equality():
    out = _run(EQ_PRELUDE + '''
    r = run("hook")
    print(r, "|", OUTSIDE)
    ''')
    assert out == "ok | []", out


LAZY_PRELUDE = '''
    import dataclasses as _real_dc
    import sys, types
    from bot.bt.core import BarEvent, CoreEngine
    from bot.bt.core.api import OrderRequest
    from bot.bt.core.interfaces import Ack, Fill, NullCostModel
    from bot.bt.core.testing import RecordingAccount

    T0 = 1_700_000_000_000_000_000
    INSIDE = [False]
    OUTSIDE = []

    def fake_fields(cls):
        if not INSIDE[0]:
            OUTSIDE.append(cls.__name__)
        return tuple(f for f in _real_dc.fields(cls) if not (cls is Fill and f.name == "liquidity"))

    FAKE = types.ModuleType("dataclasses")
    FAKE.__dict__.update({k: v for k, v in _real_dc.__dict__.items() if not k.startswith("__")})
    FAKE.fields = fake_fields

    class MakerVenue:
        def on_market_event(self, event, t):
            return ()
        def on_order(self, order, t):
            return (Ack(order.client_order_id, "v1"), Fill(order.client_order_id, 100.0, 1.0, "maker"))
        def on_cancel(self, req, t):
            return ()

    class Strategy:
        def __init__(self, swap):
            self.swap, self.n = swap, 0
        def on_event(self, ev, ctx):
            INSIDE[0] = True
            try:
                self.n += 1
                if self.n == 1:
                    if self.swap:
                        sys.modules["dataclasses"] = FAKE
                    ctx.place_order(OrderRequest(side="buy", order_type="limit", price=100.0, size=1.0,
                                                 client_order_id="o1"))
                elif self.swap:
                    sys.modules["dataclasses"] = _real_dc
            finally:
                INSIDE[0] = False

    def run(swap):
        acct = RecordingAccount()
        bars = [BarEvent(received_time_ns=T0 + k, open=100.0, high=100.0, low=100.0, close=100.0, volume=1.0)
                for k in (0, 10, 20)]
        CoreEngine(Strategy(swap), bars, fill_model=MakerVenue(), account=acct, cost_model=NullCostModel()).run()
        return ",".join(c[1].liquidity for c in acct.calls if c[0] == "fill")
'''


def test_a_module_swapped_in_sys_modules_for_one_callback_changes_nothing_in_this_or_a_later_run():
    fresh = _run(LAZY_PRELUDE + '''
    print(run(False))
    ''')
    out = _run(LAZY_PRELUDE + '''
    a = run(True)
    back = sys.modules["dataclasses"] is _real_dc
    b = run(False)
    print(a, b, back, "|", OUTSIDE)
    ''')
    a, b, back, _bar, *outside = out.split(" ", 4) + [""]
    assert fresh == "maker"
    assert back == "True"
    assert a == fresh, f"run A (its strategy swapped sys.modules['dataclasses'] for one callback): {a}"
    assert b == fresh, f"run B, a clean strategy after run A in one process: {b} (a fresh process: {fresh})"
    assert out.endswith("| []"), f"the strategy's code ran outside its call: {out}"
