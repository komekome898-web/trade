"""Critic, item 0, round 13 (i0-r13-01): the core decides what a static (C)
number IS by asking the numbers ABCs (values.py `_settle`: `issubclass(t,
numbers.Integral)` / `numbers.Real` / `numbers.Complex`), and whether a value
is a numpy bool by reading `sys.modules['numpy'].bool_` (values.py
`_numpy_bool`). Both answers are process-global state that any party can
change from inside its own call -- `numbers.Integral.register(numpy.float32)`
is a public runtime API, not a change of the core's code -- and the ABC
caches keep the change for the rest of the process.

Contract (core-14) scope: "the strategy changing ANY state object it can
reach, by any means ... reaches only what the strategy itself reads";
"what the core does with what the party handed over ... is decided only by
objects the core made and no one else reaches, or by static (C) classes";
"no code the party wrote runs there and a refusal is always the entry's own
error". Its "Not covered" list names classes WITH a __subclasshook__ or a
metaclass hook ("defining classes changes the program"); a plain
registration carries no hook and is not in that list.

Grid: change {register numpy.float32 with numbers.Integral (no hook), a
numbers.Integral subclass whose ABCMeta metaclass answers True} x site {the
cost model's fee (take_float), the latency model's delay (take_int)}; the
same clean run before and after another run's strategy made the change, in
one process; numpy.bool_ replaced by a class of the strategy's (a settled
outbox timer value). Oracle: a fee of numpy.float32(0.75) reaches the
account as 0.75 (or the run is refused with CostModelError), never 0.0; a
delay of numpy.float32(1.5) is refused with LatencyModelError; the same run
gives the same result in one process; no code of the strategy runs outside
on_event and the refusal is the entry's own error.

Every case runs in a FRESH interpreter (subprocess): an ABC registration
cannot be undone and would change every later test of this session.

Not in the grid: numbers.Real / numbers.Complex registrations (same code
path, the loop in `_settle` asks Integral first); a class defined by an
imported library rather than the strategy (same state, other owner).
"""
from __future__ import annotations

import os
import subprocess
import sys
import textwrap

import pytest

SRC = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "src")

PRELUDE = textwrap.dedent('''
    import abc, numbers
    import numpy as np
    from bot.bt.core import BarEvent, CoreEngine
    from bot.bt.core.api import OrderRequest
    from bot.bt.core.testing import ImmediateFillModel, RecordingAccount

    T0 = 1_700_000_000_000_000_000
    INSIDE = [0]
    OUTSIDE = []
    KEEP = []

    def change(how):
        if how == "register":
            numbers.Integral.register(np.float32)
        elif how == "hook":
            class M(abc.ABCMeta):
                def __subclasscheck__(cls, sub):
                    if INSIDE[0] <= 0:
                        OUTSIDE.append("hook")
                    return True
            class Evil(numbers.Integral, metaclass=M):
                pass
            KEEP.append(Evil)  # the strategy keeps its class (else gc timing decides)
            # any registration with any ABC bumps the one global invalidation counter, so the
            # negative cache of an earlier run no longer hides the hook (registering Evil itself
            # does not: it is already a subclass)
            import collections.abc
            collections.abc.Sized.register(type("Other", (), {}))  # not yet a Sized: a real registration

    class NpCost:
        def cost(self, fill):
            return np.float32(0.75)

    class HalfDelay:
        def feed_delay_ns(self, event):
            return 0
        def order_delay_ns(self, order, t):
            return np.float32(1.5)
        def cancel_delay_ns(self, req, t):
            return 0
        def notice_delay_ns(self, report, t):
            return 0

    class S:
        def __init__(self, how=None):
            self.how, self.done = how, False
        def on_event(self, ev, ctx):
            INSIDE[0] += 1
            try:
                if self.done:
                    return
                self.done = True
                change(self.how)
                ctx.place_order(OrderRequest(side="buy", order_type="market", size=1.0, client_order_id="o1"))
            finally:
                INSIDE[0] -= 1

    def bar(t):
        return BarEvent(received_time_ns=t, open=100.0, high=100.0, low=100.0, close=100.0, volume=1.0)

    def run(how=None, latency=None):
        acct = RecordingAccount()
        eng = CoreEngine(S(how), [bar(T0), bar(T0 + 10)], fill_model=ImmediateFillModel(100.0),
                         cost_model=NpCost(), account=acct, latency_model=latency)
        try:
            eng.run()
        except BaseException as exc:
            return ("raised", type(exc).__name__)
        return ("ok", [c[1].fee for c in acct.calls if c[0] == "fill"])
''')


def _run(body: str) -> str:
    env = dict(os.environ, PYTHONPATH=os.path.abspath(SRC))
    out = subprocess.run([sys.executable, "-c", PRELUDE + textwrap.dedent(body)], env=env,
                         capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr[-2000:]
    return out.stdout.strip()


@pytest.mark.parametrize("how", ["register", "hook"])
def test_a_fee_is_not_changed_by_what_a_strategy_did_to_the_numbers_abcs(how):
    got = _run(f"print(run({how!r}), OUTSIDE)")
    assert got in ("('ok', [0.75]) []", "('raised', 'CostModelError') []"), got


@pytest.mark.parametrize("how", ["register", "hook"])
def test_a_fractional_delay_is_refused_whatever_a_strategy_did_to_the_numbers_abcs(how):
    got = _run(f"run({how!r}); print(run(latency=HalfDelay()), OUTSIDE)")
    assert got == "('raised', 'LatencyModelError') []", got


@pytest.mark.parametrize("how", ["register", "hook"])
def test_the_same_run_gives_the_same_result_in_one_process(how):
    got = _run(f"a = run(); run({how!r}); b = run(); print(a == b, a, b)")
    assert got.startswith("True"), got


def test_numpy_bool_replaced_by_the_strategy_runs_no_strategy_code_and_keeps_the_refusal():
    body = '''
    class Foo:
        def __bool__(self):
            if INSIDE[0] <= 0:
                OUTSIDE.append("Foo.__bool__")
            return False

    def outbox(ctx):
        return object.__getattribute__(ctx, "_StrategyContext__place_order_cb").__self__[2]

    class P:
        def __init__(self, patch):
            self.patch, self.done = patch, False
        def on_event(self, ev, ctx):
            INSIDE[0] += 1
            try:
                if not self.done:
                    self.done = True
                    if self.patch:
                        np.bool_ = Foo
                    list.append(outbox(ctx), ("timer", Foo(), "tag"))
            finally:
                INSIDE[0] -= 1

    res = []
    for patch in (False, True):
        OUTSIDE.clear()
        try:
            CoreEngine(P(patch), [bar(T0)]).run()
            res.append(("ok", list(OUTSIDE)))
        except BaseException as exc:
            res.append((type(exc).__name__, list(OUTSIDE)))
    print(res)
    '''
    got = _run(body)
    assert got == "[('OrderApiError', []), ('OrderApiError', [])]", got
