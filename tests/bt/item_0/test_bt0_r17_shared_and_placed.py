"""Round 17 (i0-r16-01..03): the core's work on a value is decided by the
OBJECTS the sender handed over and by WHERE each sits -- not by the tree
the value unfolds to, and not by the class alone.

The root cause of the round-16 findings (round_17/ROOTCAUSE.md §1): the
core rebuilt, hashed and compared plain data once per PATH (a container two
fields point to was rebuilt twice, and so on down: 2**n for n objects), a
comparison that met several candidates of one hash nested a Python call per
level, and `thaw` chose the form it hands back by the class alone -- so a
container that was a dict KEY came back as a dict / list / set, which has no
hash. The inputs below are made from what a sender can write with the
public constructors (FrozenDict / FrozenSet / FrozenList) and tuple / list /
dict / set / frozenset / int; the oracles come from the construction, from
the library in this clean process, or from the contract's own bounds --
never from the core's cases.

Grid K (`test_k_*`): hashable values (seed 17: scalars, tuple, frozenset,
  FrozenList, FrozenSet, FrozenDict of hashables, nested up to 3) x position
  {dict key, set element, frozenset element, FrozenSet element, FrozenDict
  key, a dict key inside a list, a set element inside a dict value, inside
  a key tuple, a set inside a tuple} x reader {values.thaw, values.renew,
  OrderRequest.extra_dict() (the strategy's), the fill model's
  order.extra_dict() in a run}. Oracle: freeze takes it (the sender's own
  dict / set held it), the reader raises nothing, and what it gives equals
  the value given (Python's ==). Plus a wider grammar (lists / dicts / sets
  anywhere, core containers anywhere): freeze(thaw(freeze(x))) == freeze(x)
  and every key and element of what thaw gives has a hash.

Grid S (`test_s_*`): shape of sharing {tuple, list, dict, FrozenList,
  FrozenDict value, FrozenDict key, frozenset element, the kinds mixed by
  level} x entry {freeze, settle, renew, thaw, the core's == of two such
  values built apart, hash of a FrozenDict key, place_order and the fill
  model's extra_dict(), the outbox the engine settles, the account's forced
  order} x nesting {8: the answer equals the library's; deep (unfolds to
  2**45 .. 2**90): a child process must finish within its time limit}. A
  shared object is rebuilt once and stays shared in what comes out, exactly
  where the sender shared it (two equal objects the sender did NOT share
  stay two). MAX_NESTING holds for a shared object whatever path reaches it
  first (grid D: shallow-then-deep and deep-then-shallow, depths 95..101,
  against an unshared copy of the same value). Plus random values whose
  containers reuse earlier ones and whose leaves collide in hash across
  types (seed 170): the core's == (and `_plain_equal`) equals the library's
  == on a copy made of library types with the same sharing.

Grid C (`test_c_*`): chains whose keys collide in hash at every level: c
  deep colliding keys a level (1 deep + {1, 2, 3} ints; or 2 / 3 deep) x
  levels {1, 10, 20, 40, 90} x container {FrozenDict key, FrozenDict key and
  FrozenSet element alternating by level, FrozenDict value side} x answer {equal, differs at
  the bottom, differs in the middle}. Oracle: the answer the construction
  fixes (built from the same parameters = equal), and freeze of a dict with
  both as keys needs at most CALL_FRAMES + levels frames of headroom (the
  contract's bound, the critic's i0-r16-01). The all-deep chains run in a
  child process with a time limit (unmemoized they are c**2 per level).

NOT in the grids (A-10): a TUPLE key that is itself a shared DAG (to build
the sender's dict the interpreter hashes and compares it, unfolded: the
sender cannot make it without the same 2**n work, and the core's copy keeps
the same sharing, so the interpreter's work on it equals the sender's);
hashing a value that holds a shared tuple (the interpreter's own tuple
hash, not cached in Python 3.11, unfolds it for anyone who hashes it -- the
core hashes a value only as a key or an element, which the sender's dict /
set hashed already); frozensets compared by the interpreter above the
topmost FrozenDict of a colliding chain (C code; the sender's own dict made
the same comparison); classes the sender writes (L-445: outside the core's
promise); threads.
"""
from __future__ import annotations

import os
import random
import subprocess
import sys
import textwrap
from decimal import Decimal
from fractions import Fraction

import pytest

from bot.bt.core import BarEvent, CoreEngine, values as V
from bot.bt.core.api import OrderRequest
from bot.bt.core.interfaces import NullCostModel
from bot.bt.core.testing import ImmediateFillModel, RecordingAccount

T0 = 1_700_000_000_000_000_000
M = (1 << 61) - 1  # sys.hash_info.modulus on 64-bit builds: n and n + M hash alike
# the child processes import the same `bot` package this process imported
SRC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(V.__file__)))))


# ---- grid K: where a container sits decides the form it reads back in ---------------------

_LEAVES = [1, -2, 0.5, "a", b"b", None, True, Fraction(1, 3), Decimal("1.5"), 2 + 1j, (), frozenset()]


def _key(rng: random.Random, depth: int):
    """A hashable value a sender can write: scalars and the hashable containers."""
    if depth == 0 or rng.random() < 0.25:
        return rng.choice(_LEAVES)
    kind = rng.choice(["tuple", "frozenset", "FrozenList", "FrozenSet", "FrozenDict"])
    items = [_key(rng, depth - 1) for _ in range(rng.randrange(0, 3))]
    if kind == "tuple":
        return tuple(items)
    if kind == "frozenset":
        return frozenset(items)
    if kind == "FrozenList":
        return V.FrozenList(items)
    if kind == "FrozenSet":
        return V.FrozenSet(items)
    return V.FrozenDict({k: _key(rng, depth - 1) for k in items})


POSITIONS = {
    "dict-key": lambda k: {k: 1},
    "set-element": lambda k: {k},
    "frozenset-element": lambda k: frozenset({k}),
    "FrozenSet-element": lambda k: V.FrozenSet({k}),
    "FrozenDict-key": lambda k: V.FrozenDict({k: 1}),
    "dict-key-in-list": lambda k: [{k: 1}, 2],
    "set-in-dict-value": lambda k: {"v": {k}},
    "in-a-key-tuple": lambda k: {(k, 1): 2},
    "set-in-tuple": lambda k: ({k},),
}

_RNG = random.Random(17)
KEYS = [_key(_RNG, 3) for _ in range(40)] + [
    V.FrozenDict({"a": 1}), V.FrozenSet({1}), (V.FrozenList([1]),), V.FrozenList([V.FrozenSet({2})]),
    V.FrozenDict({(V.FrozenList([1]),): V.FrozenSet({V.FrozenDict({})})}), frozenset({V.FrozenList([3])}),
]
K_CASES = [(p, i) for p in POSITIONS for i in range(len(KEYS))]


def _thawed_type(given):
    t = type(given)
    return {V.FrozenDict: dict, V.FrozenSet: set}.get(t, t)


@pytest.mark.parametrize("position,i", K_CASES, ids=[f"{p}-{i}" for p, i in K_CASES])
def test_k_what_freeze_takes_at_a_key_position_reads_back_equal(position, i):
    given = POSITIONS[position](KEYS[i])
    frozen = V.freeze(given)  # the sender's own dict / set held it: taken
    back = V.thaw(frozen)
    assert back == given, (position, KEYS[i], back)
    assert type(back) is _thawed_type(given)
    assert V.renew(frozen) == frozen and V.thaw(V.renew(frozen)) == given
    req = OrderRequest(side="buy", order_type="market", size=1.0, client_order_id="o", extra=(("k", given),))
    assert req.extra_dict() == {"k": given}


def test_k_the_fill_model_reads_every_accepted_extra():
    seen: list = []

    class Reader(ImmediateFillModel):
        def on_order(self, order, venue_time_ns):
            seen.append(order.extra_dict())
            return super().on_order(order, venue_time_ns)

    givens = [POSITIONS[p](KEYS[i]) for p, i in K_CASES]

    class S:
        n = 0

        def on_event(self, ev, ctx):
            S.n += 1
            if S.n == 1:
                for j, g in enumerate(givens):
                    ctx.place_order(OrderRequest(side="buy", order_type="market", size=1.0,
                                                 client_order_id=f"o{j}", extra=(("k", g),)))

    bars = [BarEvent(received_time_ns=T0 + k, open=100.0, high=100.0, low=100.0, close=100.0, volume=1.0)
            for k in (0, 10, 20)]
    CoreEngine(S(), bars, fill_model=Reader(100.0), account=RecordingAccount(), cost_model=NullCostModel()).run()
    assert len(seen) == len(givens)
    for g, got in zip(givens, seen):
        assert got == {"k": g}


def _any(rng: random.Random, depth: int):
    """Plain data with every container anywhere (keys and elements hashable)."""
    if depth == 0 or rng.random() < 0.2:
        return rng.choice(_LEAVES)
    kind = rng.choice(["list", "dict", "set", "tuple", "frozenset", "FrozenList", "FrozenSet", "FrozenDict"])
    n = rng.randrange(0, 3)
    if kind in ("set", "frozenset", "FrozenSet"):
        items = [_key(rng, depth - 1) for _ in range(n)]
        return {"set": set, "frozenset": frozenset, "FrozenSet": V.FrozenSet}[kind](items)
    if kind in ("dict", "FrozenDict"):
        d = {_key(rng, depth - 1): _any(rng, depth - 1) for _ in range(n)}
        return d if kind == "dict" else V.FrozenDict(d)
    items = [_any(rng, depth - 1) for _ in range(n)]
    return {"list": list, "tuple": tuple, "FrozenList": V.FrozenList}[kind](items)


def _keys_hashable(x, seen=None):
    """Every dict key and set element anywhere in x has a hash."""
    stack = [x]
    while stack:
        y = stack.pop()
        if isinstance(y, dict):
            for k, v in y.items():
                hash(k)
                stack += [k, v]
        elif isinstance(y, (set, frozenset)):
            for e in y:
                hash(e)
                stack.append(e)
        elif isinstance(y, (list, tuple)):
            stack.extend(y)
        elif type(y) is V.FrozenDict:
            for k, v in y.items():
                hash(k)
                stack += [k, v]


def test_k_any_frozen_value_thaws_to_keys_with_a_hash_and_back():
    rng = random.Random(1717)
    taken = 0
    for _ in range(600):
        x = _any(rng, 4)
        f = V.freeze(x)
        back = V.thaw(f)
        _keys_hashable(back)
        assert V.freeze(back) == f
        assert V.renew(f) == f
        taken += 1
    assert taken == 600


# ---- grid S: a shared object is taken once --------------------------------------------------

def _mk(kind, x, level):
    if kind == "mixed":
        kind = ["tuple", "list", "dict", "FrozenList", "FrozenDict"][level % 5]
    if kind == "tuple":
        return (x, x)
    if kind == "list":
        return [x, x]
    if kind == "dict":
        return {"a": x, "b": x}
    if kind == "FrozenList":
        return V.FrozenList([x, x])
    if kind == "FrozenDict":
        return V.FrozenDict({"a": x, "b": x})
    if kind == "FrozenDict-key":
        return V.FrozenDict({x: 0, "b": x})
    if kind == "frozenset":
        return frozenset({x, (x,)})
    raise AssertionError(kind)


SHARE_KINDS = ["tuple", "list", "dict", "FrozenList", "FrozenDict", "FrozenDict-key", "frozenset", "mixed"]
# the nesting a shape reaches per level (frozenset holds (x,): 2 containers a level on that path)
DEEP = {"frozenset": 45}


def _shared(kind, n):
    x = V.FrozenDict({}) if kind == "FrozenDict-key" else ()
    for level in range(n):
        x = _mk(kind, x, level)
    return x


def _children(x):
    if isinstance(x, (tuple, list)):
        return list(x)
    if isinstance(x, (dict, V.FrozenDict)):
        return [v for kv in x.items() for v in kv]
    if isinstance(x, (set, frozenset)):
        return list(x)
    return []


def _identity_pattern(x):
    """The sharing of a value: the containers met depth first (children in
    their order), each as the index of the first one it is the same object
    as; a container is entered on its first meeting only."""
    first, out, stack = {}, [], [x]
    while stack:
        y = stack.pop()
        if not isinstance(y, (tuple, list, dict, set, frozenset, V.FrozenDict)):
            continue
        new = id(y) not in first
        out.append(first.setdefault(id(y), len(first)))
        if new:
            stack.extend(reversed(_children(y)))
    return out


# thaw gives list / dict / set where the sender gave those (a FrozenList it gave comes back a list)
_THAW_EQUALS_GIVEN = ("tuple", "list", "dict", "FrozenDict", "FrozenDict-key", "frozenset")


@pytest.mark.parametrize("kind", SHARE_KINDS)
def test_s_a_shared_value_is_taken_equal_and_keeps_its_sharing(kind):
    x = _shared(kind, 8)
    f = V.freeze(x)
    back = V.thaw(f)
    assert V.freeze(back) == f
    if kind in _THAW_EQUALS_GIVEN:
        assert back == x
    assert V.settle(x) == x and V.renew(f) == f
    # the same pattern of shared objects as the sender's value, in each form
    pattern = _identity_pattern(x)
    assert _identity_pattern(f) == pattern
    assert _identity_pattern(V.renew(f)) == pattern
    assert _identity_pattern(V.settle(x)) == pattern
    if kind != "FrozenDict-key":  # one object as a key and as a value thaws to two forms (grid K)
        assert _identity_pattern(back) == pattern
    # nothing of what comes out is the sender's object (but the one empty tuple the interpreter keeps)
    ids = {id(c) for c in _containers(x) if not (type(c) is tuple and len(c) == 0)}
    for out in (f, back, V.settle(x), V.renew(f)):
        assert not ({id(c) for c in _containers(out)} & ids)


def _containers(x):
    out, seen, stack = [], set(), [x]
    while stack:
        y = stack.pop()
        if isinstance(y, (tuple, list, dict, set, frozenset, V.FrozenDict)) and id(y) not in seen:
            seen.add(id(y))
            out.append(y)
            stack.extend(_children(y))
    return out


def test_s_equal_objects_the_sender_did_not_share_stay_apart():
    a, b = [1], [1]
    for f in (V.freeze([a, b]), V.settle([a, b])):
        assert f[0] is not f[1] and f[0] == f[1]
    back = V.thaw(V.freeze([a, b]))
    back[0].append(2)
    assert back == [[1, 2], [1]]
    s = [1]
    back = V.thaw(V.freeze([s, s]))
    assert back[0] is back[1]  # the sender shared it: so does the copy (as copy.deepcopy does)
    t = V.freeze([s, s])
    assert V.thaw(t) is not V.thaw(t) and V.thaw(t)[0] is not V.thaw(t)[0]  # each thaw is fresh


CHILD_S = textwrap.dedent("""
    import sys, time
    from bot.bt.core import BarEvent, CoreEngine, values as V
    from bot.bt.core.api import OrderRequest
    from bot.bt.core.interfaces import NullCostModel
    from bot.bt.core.testing import ImmediateFillModel, RecordingAccount
    T0 = 1_700_000_000_000_000_000
    MK = {mk}
    exec(MK)
    def bars():
        return [BarEvent(received_time_ns=T0 + k, open=100.0, high=100.0, low=100.0, close=100.0, volume=1.0)
                for k in (0, 10, 20)]
    def outbox(ctx):
        return object.__getattribute__(ctx, "_StrategyContext__place_order_cb").__self__[2]
    def via(how, value):
        seen = []
        class Reader(ImmediateFillModel):
            def on_order(self, order, t):
                seen.append(order.extra_dict())
                return super().on_order(order, t)
        class S:
            n = 0
            def on_event(self, ev, ctx):
                S.n += 1
                if S.n != 1 or how == "account":
                    return
                if how == "place_order":
                    ctx.place_order(OrderRequest(side="buy", order_type="market", size=1.0, client_order_id="o1",
                                                 extra=(("k", value),)))
                else:
                    req = OrderRequest(side="buy", order_type="market", size=1.0, client_order_id="o1")
                    object.__setattr__(req, "extra", (("k", value),))
                    list.append(outbox(ctx), ("new", req, ev.received_time_ns))
        class Forcing(RecordingAccount):
            def on_market_event(self, event, t):
                super().on_market_event(event, t)
                if how == "account" and event.received_time_ns == T0 + 10:
                    req = OrderRequest(side="sell", order_type="market", size=1.0, client_order_id="forced-f1")
                    object.__setattr__(req, "extra", (("k", value),))
                    return [req]
                return []
        CoreEngine(S(), bars(), fill_model=Reader(100.0), account=Forcing(), cost_model=NullCostModel()).run()
        assert len(seen) == 1, seen
    assert V.__file__.startswith(sys.argv[2]), (V.__file__, sys.argv[2])
    entry = sys.argv[1]
    for kind in ({keykinds} if entry == "key" else {kinds}):
        n = {deep}.get(kind, 90)
        if entry in ("place_order", "outbox", "account"):
            n -= 2  # extra's tuple and pair hold the value
        x = shared(kind, n)
        t = time.perf_counter()
        try:
            if entry == "freeze":
                V.freeze(x)
            elif entry == "settle":
                V.settle(x)
            elif entry == "renew":
                V.renew(V.freeze(x))
            elif entry == "thaw":
                V.thaw(V.freeze(x))
            elif entry == "equal":
                a, b = V.freeze(V.FrozenDict({{"r": x}})), V.freeze(V.FrozenDict({{"r": shared(kind, n)}}))
                assert a == b and not (a != b)
            elif entry == "key":
                d = {{V.FrozenDict({{"r": V.freeze(x)}}): 1}}  # the sender's dict hashes its key
                V.freeze(d)
            else:
                via(entry, x)
            r = "taken"
        except ValueError:
            r = "refused"
        print(f"{{kind}} {{r}} {{time.perf_counter() - t:.3f}}", flush=True)
""")

MK_SRC = "\n".join([
    "import random",
    "from bot.bt.core import values as V",
    "def _mk(kind, x, level):",
    "    if kind == 'mixed':",
    "        kind = ['tuple', 'list', 'dict', 'FrozenList', 'FrozenDict'][level % 5]",
    "    if kind == 'tuple': return (x, x)",
    "    if kind == 'list': return [x, x]",
    "    if kind == 'dict': return {'a': x, 'b': x}",
    "    if kind == 'FrozenList': return V.FrozenList([x, x])",
    "    if kind == 'FrozenDict': return V.FrozenDict({'a': x, 'b': x})",
    "    if kind == 'FrozenDict-key': return V.FrozenDict({x: 0, 'b': x})",
    "    if kind == 'frozenset': return frozenset({x, (x,)})",
    "def shared(kind, n):",
    "    x = V.FrozenDict({}) if kind == 'FrozenDict-key' else ()",
    "    for level in range(n):",
    "        x = _mk(kind, x, level)",
    "    return x",
])

# the shapes whose frozen form holds no shared TUPLE (hashing one unfolds it in the interpreter's
# own tuple hash: not the core's, see NOT in the grids)
KEY_KINDS = ["dict", "FrozenDict", "FrozenDict-key", "frozenset"]
S_ENTRIES = ["freeze", "settle", "renew", "thaw", "equal", "key", "place_order", "outbox", "account"]


def _child(code: str, args: list, limit: float):
    env = {**os.environ, "PYTHONPATH": SRC}  # before the installed path: the parent's own `bot`
    try:
        out = subprocess.run([sys.executable, "-c", code, *args], capture_output=True, text=True,
                             timeout=limit, env=env)
        return out.stdout, out.stderr, out.returncode
    except subprocess.TimeoutExpired as exc:
        return (exc.stdout or b"").decode() if isinstance(exc.stdout, bytes) else (exc.stdout or ""), "timeout", None


@pytest.mark.parametrize("entry", S_ENTRIES)
def test_s_a_deeply_shared_value_is_taken_in_bounded_time(entry):
    code = CHILD_S.format(mk=repr(MK_SRC), kinds=repr(SHARE_KINDS), keykinds=repr(KEY_KINDS), deep=repr(DEEP))
    out, err, rc = _child(code, [entry, SRC], 60)
    done = {row.split()[0]: row.split()[1] for row in out.splitlines() if row.strip()}
    want = set(KEY_KINDS) if entry == "key" else set(SHARE_KINDS)
    assert rc == 0 and set(done) == want, (entry, out, err[-2000:])
    # nesting within MAX_NESTING: every shape is taken, none is refused
    assert set(done.values()) == {"taken"}, (entry, done)


# ---- grid D: the nesting bound holds whichever path reaches a shared object first ----------

def _deepen(x, levels):
    for _ in range(levels):
        x = [x]
    return x


def _chain(h):
    x = 1
    for _ in range(h):
        x = [x]
    return x


def _copy(x):
    return [_copy(v) for v in x] if isinstance(x, list) else x


@pytest.mark.parametrize("depth", list(range(95, 102)))
@pytest.mark.parametrize("order", ["shallow-first", "deep-first"])
def test_d_the_nesting_bound_holds_for_a_shared_object(depth, order):
    s = _chain(10)  # 10 lists
    deep = _deepen(s, depth - 11)  # s reached under depth - 11 more lists + the root below
    x = [s, deep] if order == "shallow-first" else [deep, s]
    unshared = [_copy(s), _deepen(_copy(s), depth - 11)] if order == "shallow-first" else \
        [_deepen(_copy(s), depth - 11), _copy(s)]
    for fn, err in ((V.freeze, ValueError), (V.settle, V.Unsettled)):
        outcomes = []
        for value in (x, unshared):
            try:
                fn(value)
                outcomes.append("taken")
            except err:
                outcomes.append("refused")
        assert outcomes[0] == outcomes[1], (fn.__name__, depth, order, outcomes)
        assert outcomes[0] == ("taken" if depth <= V.MAX_NESTING else "refused"), (fn.__name__, depth, outcomes)


# ---- grid C: chains whose keys collide at every level ---------------------------------------

def _ints_of_hash(h, count, start):
    """`count` distinct ints whose hash is h, unequal to anything else built here."""
    base = (h % M) + start * M
    return [base + i * M for i in range(count)]


def _collide_chain(levels, ints, deep, container, differ_at=None):
    """A chain: level 0 is `deep` distinct ints of hash 5; each level k is
    `deep` containers, all of one hash, each holding every container of
    level k - 1 plus `ints` ints of that hash plus one int of that hash
    naming it. Two chains built with the same arguments are equal (and
    share no object); `differ_at` changes the ints of that level."""
    level = [5 + (i + (97 if differ_at == 0 else 0)) * M for i in range(deep)]
    for k in range(1, levels + 1):
        h = hash(V.freeze(level[0]))
        extra = _ints_of_hash(h, ints, 3)
        names = _ints_of_hash(h, deep, 50 + (7 if differ_at == k else 0))
        new = []
        for i in range(deep):
            members = list(level) + extra + [names[i]]
            if container == "FrozenDict-key":
                new.append(V.FrozenDict({m: 0 for m in members}))
            elif container == "FrozenDict-key/FrozenSet-element":  # one container a level, alternating
                new.append(V.FrozenDict({m: 0 for m in members}) if k % 2 else V.FrozenSet(members))
            else:  # FrozenDict-value: the keys are 0, 1, ...; the values carry the chain
                new.append(V.FrozenDict({j: m for j, m in enumerate(members)}))
        level = new
    return level[0]


C_SHAPES = [(1, 1), (2, 1), (3, 1)]  # (ints, deep): the critic's chain and more ints a level
C_CONTAINERS = ["FrozenDict-key", "FrozenDict-key/FrozenSet-element", "FrozenDict-value"]


def _depth():
    f, n = sys._getframe(1), 0
    while f is not None:
        n += 1
        f = f.f_back
    return n


def _ok(headroom, fn):
    old = sys.getrecursionlimit()
    sys.setrecursionlimit(_depth() + headroom)
    try:
        fn()
        return True
    except (RecursionError, ValueError):
        return False
    finally:
        sys.setrecursionlimit(old)


def _least(fn):
    lo, hi = 1, 3000
    assert _ok(hi, fn)
    while lo < hi:
        mid = (lo + hi) // 2
        if _ok(mid, fn):
            hi = mid
        else:
            lo = mid + 1
    return lo


@pytest.mark.parametrize("levels", [1, 10, 20, 40, 90])
@pytest.mark.parametrize("container", C_CONTAINERS)
@pytest.mark.parametrize("ints,deep", C_SHAPES)
def test_c_colliding_chains_compare_as_built_within_the_contracts_frames(ints, deep, container, levels):
    a = _collide_chain(levels, ints, deep, container)
    same = _collide_chain(levels, ints, deep, container)
    bottom = _collide_chain(levels, ints, deep, container, differ_at=0)
    middle = _collide_chain(levels, ints, deep, container, differ_at=max(1, levels // 2))
    fa, fs, fb, fm = (V.freeze(v) for v in (a, same, bottom, middle))
    assert fa == fs and not (fa != fs)
    assert not (fa == fb) and fa != fb
    assert not (fa == fm) and fa != fm
    assert hash(fa) == hash(fb) == hash(fm)  # they collide: the core must compare them
    need = max(_least(lambda: V.freeze({a: 1, bottom: 2})), _least(lambda: V.freeze({a: 1, middle: 2})))
    bound = V.CALL_FRAMES + levels
    assert need <= bound, f"{container} ints={ints} x {levels}: needs {need} frames; the contract says {bound}"


CHILD_C = textwrap.dedent("""
    import sys, time
    exec({src})
    assert V.__file__.startswith(sys.argv[2]), (V.__file__, sys.argv[2])
    deep = int(sys.argv[1])
    for container in {containers}:
        for levels in (10, 20, 40, 90):
            t = time.perf_counter()
            a = _collide_chain(levels, 1, deep, container)
            b = _collide_chain(levels, 1, deep, container)
            m = _collide_chain(levels, 1, deep, container, differ_at=levels // 2)
            fa, fb, fm = V.freeze(a), V.freeze(b), V.freeze(m)
            assert fa == fb and fa != fm
            V.freeze({{a: 1, m: 2}})
            print(container, levels, f"{{time.perf_counter() - t:.3f}}", flush=True)
""")


def _chain_src() -> str:
    import inspect
    return "\n".join(["from bot.bt.core import values as V", "M = (1 << 61) - 1",
                      inspect.getsource(_ints_of_hash), inspect.getsource(_collide_chain)])


@pytest.mark.parametrize("deep", [2, 3])
def test_c_chains_with_several_deep_colliding_keys_finish(deep):
    code = CHILD_C.format(src=repr(_chain_src()), containers=repr(C_CONTAINERS))
    out, err, rc = _child(code, [str(deep), SRC], 60)
    rows = [line.split() for line in out.splitlines() if line.strip()]
    assert rc == 0 and len(rows) == len(C_CONTAINERS) * 4, (deep, out, err[-2000:])


# ---- the core's equality over shared values equals the library's --------------------------

class _D:
    """The oracle's FrozenDict: equal to another _D with the same items."""

    def __init__(self, items):
        self.items = frozenset(items)

    def __eq__(self, other):
        return type(other) is _D and self.items == other.items

    def __hash__(self):
        return hash(self.items)


def _library(x, memo):
    """The oracle's copy of a core value: library types only, one copy per
    object (so sharing -- and the interpreter's identity shortcut -- is kept)."""
    got = memo.get(id(x))
    if got is not None:
        return got[1]
    t = type(x)
    if t is V.FrozenDict:
        out = _D((_library(k, memo), _library(v, memo)) for k, v in x.items())
    elif t in (tuple, V.FrozenList):
        out = tuple(_library(v, memo) for v in x)
    elif t in (frozenset, V.FrozenSet):
        out = frozenset(_library(v, memo) for v in x)
    elif t is V.PlainFraction:
        out = Fraction(*V.fraction_parts(x))
    elif t is V.PlainDecimal:
        out = Decimal(str(x))
    else:
        out = x
    memo[id(x)] = (x, out)
    return out


def _random_shared(rng, pool, depth):
    """A value whose containers reuse earlier ones (`pool`) and whose leaves
    collide in hash across types (-1 / -2, 1 / 1.0 / True / Fraction(1))."""
    leaves = [-1, -2, 1, 1.0, True, Fraction(1), Decimal(1), 0.5, "a", None, 5, 5 + M]
    if pool and rng.random() < 0.35:
        return rng.choice(pool)
    if depth == 0 or rng.random() < 0.25:
        return rng.choice(leaves)
    kind = rng.choice(["tuple", "FrozenList", "frozenset", "FrozenSet", "FrozenDict"])
    items = [_random_shared(rng, pool, depth - 1) for _ in range(rng.randrange(0, 4))]
    if kind == "tuple":
        out = tuple(items)
    elif kind == "FrozenList":
        out = V.FrozenList(items)
    elif kind == "frozenset":
        out = frozenset(items)
    elif kind == "FrozenSet":
        out = V.FrozenSet(items)
    else:
        out = V.FrozenDict({k: _random_shared(rng, pool, depth - 1) for k in items})
    pool.append(out)
    return out


def test_s_the_cores_equality_of_shared_values_is_the_librarys():
    rng = random.Random(170)
    checked = equal = 0
    for _ in range(300):
        pool: list = []
        vals = [V.freeze(_random_shared(rng, pool, 4)) for _ in range(6)]
        vals += [V.renew(v) for v in vals[:3]]  # equal by construction, no object shared with the first
        for a in vals:
            for b in vals:
                memo: dict = {}
                want = _library(a, memo) == _library(b, memo)
                assert (a == b) == want, (a, b)
                if type(a) is V.FrozenDict and type(b) is V.FrozenDict:
                    assert V._plain_equal(a, b) == want
                checked += 1
                equal += want
    assert checked > 20000 and equal > 3000, (checked, equal)
