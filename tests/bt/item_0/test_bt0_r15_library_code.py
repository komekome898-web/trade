"""Round 15 (i0-r14-01..05): what the core accepts, refuses or computes is
decided by the value alone -- also through the LIBRARY code the core runs
(the equality of the values it builds, a table it fills late, a module it
imports at run time) and whatever the stack depth of the call.

Round 14 proved "the core asks no ABC" by reading the core's own source.
These grids list what RUNS instead (the root cause of i0-r14-01/02/05):

Grid A (`test_the_library_code_the_core_runs_is_the_reviewed_table`): the
  workload (_r15_workload.py: every entry where the core takes, copies,
  compares or hashes a value, with keys whose hashes collide across every
  pair of types) runs under sys.setprofile; every Python function outside
  the core entered while the nearest non-library frame is the core's is
  listed. Oracle: the list is inside REVIEWED (each entry with the reason it
  reads no process-wide state); no ABC, import machinery, `fractions`,
  `numbers` or `decimal` code is in it. The C functions the core calls
  include no ABC check, no decimal context and no recursion limit.

Grid B (`test_a_change_of_process_state_changes_nothing_through_library_code`):
  changes = the child's CHANGES (_r15_state_child.py, read from the modules
  and the core's source): every ABC of `numbers` and `collections.abc` x
  {register every type the workload hands over and the core's own classes;
  a subclass whose metaclass answers True, after a registration that clears
  every negative cache}; the thread's decimal context (precision 1; floor at
  precision 3; no traps; every trap, FloatOperation included; lower-case
  exponent; Emax 5); every module the core imports swapped in sys.modules
  for ONE callback of the strategy's and put back in the next (i0-r14-02);
  warnings made errors; numpy's errors raised -- each made by the strategy
  inside its own on_event. Sites = the whole workload (the strategy's extra,
  the account's forced order, the outbox, every hand-over, extra_dict() in
  the fill model's and the account's calls, the colliding keys). Oracle: the
  run that made the change and a clean run after it in the same process
  equal a run in a fresh process, value for value; no code of the changer's
  runs with the core as its nearest non-library caller. Every child runs
  with PYTHONHASHSEED=0 (str hashes, and so the colliding keys, are the
  same in every child).

Grid B' (`test_no_import_…`, `test_the_state_of_the_core_modules_…`,
  `test_the_core_writes_no_decimal_flag`): no import, __import__,
  importlib or sys.modules in any function of the core (AST of every file);
  the globals of every core module and the dicts of the core's classes --
  and the contents of the containers they hold -- are the same after the
  workload ran twice as right after the core was loaded (a fresh process);
  the thread's decimal flags are clear after a run.

Grid C (`test_*_number_*`, `test_to_nanos_*`, `test_validate_nanos_*`,
  `test_a_delay_*`, `test_a_duration_*`): value classes = every numpy scalar
  class (numpy's own table np.sctypeDict) and int, float, Fraction,
  Decimal, str, with values exactly representable and not; entries =
  freeze, settle, to_nanos in every unit, validate_nanos, a latency model's
  delay. Oracle (from the value, not from the core): plain data is EQUAL to
  the value handed over (exact rationals compared), or refused; a time is
  the int of ns the value states (a binary float by its shortest repr, as
  documented; a value a float cannot hold exactly is refused), or refused
  when it states none; numpy timedelta64 / datetime64 (a count in a unit)
  are refused everywhere.

Grid D (`test_an_entry_takes_a_value_alike_at_every_stack_depth`): headroom
  left below the interpreter's recursion limit {CALL_FRAMES, +5, 60, 200} x
  nesting {1, 10, 50, MAX_NESTING-2, MAX_NESTING, MAX_NESTING+1} x
  container {list, tuple, dict, a set of a nested tuple, FrozenDicts nested
  in a dict key} x entry {freeze, settle, renew, thaw, place_order inside
  on_event, ctx.order() and extra_dict() inside on_event}. Oracle: the same
  outcome as with the whole stack free. The interpreter's OWN recursion
  when it compares two distinct nested values with equal hashes in one set
  (`test_colliding_nested_values_…`): refused with the entry's error, never
  RecursionError, and taken with CALL_FRAMES + the nesting of headroom.

Equality oracle (`test_the_cores_number_equality_…`): the core's equality
  of the Fraction / Decimal it builds equals Python's `==` in a clean
  process for every pair of number types and values (0, -0.0, 1, 2**70,
  0.5, 1e300, +-inf, nan, 1+2j, 1/3, Decimal 1E+999999 ...), and its hash
  equals the library's.

NOT in the grids (A-10): rebinding a name the core calls (a builtin, a
library's function, the core's globals: the contract's "not covered");
interpreter hooks (settrace / setprofile -- grid A itself uses one --,
audit hooks, gc callbacks, signals, threads); a recursion limit set below
what the core needs; a signaling-NaN Decimal compared by Python (Python
raises depending on the context's traps; the core answers "not equal");
ABCs of modules other than numbers / collections.abc (no ABC is asked:
grid A shows no ABC code runs at all); an interpreter started with -b
(bytes_warning), under which comparing bytes with str warns: an
interpreter option like -O, not state a party changes at run time.
"""
from __future__ import annotations

import ast
import concurrent.futures
import glob
import json
import math
import os
import subprocess
import sys
from decimal import Decimal
from fractions import Fraction

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import _r15_workload as W  # noqa: E402
from bot.bt.core import BarEvent, CoreEngine, TimestampUnitError  # noqa: E402
from bot.bt.core import values as V  # noqa: E402
from bot.bt.core.api import OrderRequest  # noqa: E402
from bot.bt.core.errors import LatencyModelError, OrderApiError  # noqa: E402
from bot.bt.core.interfaces import NullCostModel  # noqa: E402
from bot.bt.core.testing import ImmediateFillModel, RecordingAccount  # noqa: E402
from bot.bt.core.time import to_nanos, validate_nanos  # noqa: E402

CORE_DIR = os.path.dirname(os.path.abspath(V.__file__)) + os.sep
CHILD = os.path.join(HERE, "_r15_state_child.py")
SRC = os.path.abspath(os.path.join(HERE, "..", "..", "..", "src"))
T0 = W.T0


# ---- grid A: the library code the core runs ------------------------------------------

# (file, qualname) -> why running it on the core's behalf reads no process-wide state
REVIEWED = {
    ("dataclasses.py", "replace"): "copies the fields of one of the core's carriers into a new one of its "
                                   "class: reads the class's own __dataclass_fields__ and the object's slots",
    ("dataclasses.py", "fields"): "the class's own __dataclass_fields__ (a core class)",
    ("dataclasses.py", "fields.<locals>.<genexpr>"): "the same",
    ("dataclasses.py", "_is_dataclass_instance"): "hasattr of the core class's __dataclass_fields__",
    ("dataclasses.py", "_recursive_repr.<locals>.wrapper"): "the generated __repr__ of a core event for the "
                                                            "delivery digest: its fields are the core's "
                                                            "scalars; the guard set is per repr call",
    ("enum.py", "Enum.__hash__"): "hash of the member's own name (the core's EventType / OrderState)",
    ("enum.py", "EnumType.__iter__"): "the members of the core's own Enum class",
    ("enum.py", "EnumType.__iter__.<locals>.<genexpr>"): "the same",
    # code compiled from a string: keyed with its first argument's name, so another piece of code
    # of the same qualname is not taken for it
    ("<string>", "__create_fn__.<locals>.__init__(self)"): "the __init__ dataclasses wrote, when the core was "
                                                           "loaded, for a core carrier / view class",
    ("<string>", "__create_fn__.<locals>.__repr__(self)"): "the __repr__ dataclasses wrote for a core event "
                                                           "(the delivery digest)",
    ("<string>", "<lambda>(_cls)"): "the __new__ collections.namedtuple wrote for the core's NamedTuple "
                                    "(window.AnswerPlace): tuple.__new__ of its fields",
}
FORBIDDEN_FILES = ("abc.py", "<frozen abc>", "numbers.py", "fractions.py", "_pydecimal.py", "importlib",
                   "<frozen importlib", "codecs.py", "warnings.py", "_collections_abc.py")
FORBIDDEN_C = {("_abc", "_abc_instancecheck"), ("_abc", "_abc_subclasscheck"), ("builtins", "__import__"),
               ("sys", "getrecursionlimit"), ("decimal", "getcontext"), ("_decimal", "getcontext"),
               ("sys", "get_int_max_str_digits"), ("sys", "_getframe")}


def _library_calls():
    parties = {os.path.abspath(W.__file__), os.path.abspath(__file__)}
    py, c = {}, {}

    def owner(f):
        while f is not None:
            fn = f.f_code.co_filename
            if fn.startswith(CORE_DIR) or fn.startswith("<bot.bt.core"):
                return "core"
            if os.path.abspath(fn) in parties:
                return "party"
            f = f.f_back
        return None

    def prof(frame, event, arg):
        if event == "call":
            fn = frame.f_code.co_filename
            if fn.startswith(CORE_DIR) or fn.startswith("<bot.bt.core") or os.path.abspath(fn) in parties:
                return
            if owner(frame.f_back) == "core":
                code = frame.f_code
                if fn.startswith("<"):
                    key = (fn, f"{code.co_qualname}({code.co_varnames[0] if code.co_varnames else ''})")
                else:
                    key = (os.path.basename(fn), code.co_qualname)
                py[key] = py.get(key, 0) + 1
        elif event == "c_call" and owner(frame) == "core":
            mod = getattr(arg, "__module__", None) or type(getattr(arg, "__self__", None)).__name__
            key = (str(mod), getattr(arg, "__name__", repr(arg)))
            c[key] = c.get(key, 0) + 1

    old = sys.getprofile()
    sys.setprofile(prof)
    try:
        out = W.run()
    finally:
        sys.setprofile(old)
    assert out["outcome"] == "ok", out
    return py, c


def test_the_library_code_the_core_runs_is_the_reviewed_table():
    py, _c = _library_calls()
    forbidden = sorted(k for k in py if any(k[0].startswith(f) or f in k[0] for f in FORBIDDEN_FILES))
    assert forbidden == [], f"the core ran library code that reads process-wide state: {forbidden}"
    unreviewed = sorted(set(py) - set(REVIEWED))
    assert unreviewed == [], f"library code the core runs, not reviewed: {unreviewed}"


def test_the_c_functions_the_core_calls_ask_no_abc_context_or_limit():
    _py, c = _library_calls()
    assert sorted(set(c) & FORBIDDEN_C) == []


# ---- grid B: process state x library code ----------------------------------------------

def _child(mode: str) -> dict:
    env = dict(os.environ, PYTHONPATH=SRC, PYTHONHASHSEED="0")
    out = subprocess.run([sys.executable, CHILD, mode], capture_output=True, text=True, env=env, timeout=300)
    assert out.returncode == 0, (mode, out.stderr[-3000:])
    return json.loads(out.stdout)


def _changes() -> list:
    env = dict(os.environ, PYTHONPATH=SRC, PYTHONHASHSEED="0")
    out = subprocess.run([sys.executable, CHILD, "--list"], capture_output=True, text=True, env=env, timeout=120)
    assert out.returncode == 0, out.stderr[-3000:]
    return json.loads(out.stdout)


CHANGES = _changes()


@pytest.fixture(scope="module")
def grid_b():
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(2, (os.cpu_count() or 2))) as pool:
        futures = {m: pool.submit(_child, m) for m in ["fresh"] + CHANGES}
        return {m: f.result() for m, f in futures.items()}


def test_the_grid_lists_every_abc_decimal_setting_and_core_module():
    kinds = {c.partition(":")[0] for c in CHANGES}
    assert kinds == {"register", "hook", "decimal", "sys_modules", "warnings", "numpy_seterr"}
    modules = {c.partition(":")[2] for c in CHANGES if c.startswith("sys_modules:")}
    assert {"dataclasses", "fractions", "decimal", "numbers", "numpy", "heapq", "hashlib"} <= modules
    assert "register:numbers.Rational" in CHANGES and "hook:collections.abc.Mapping" in CHANGES


def test_the_fresh_run_is_the_workload_taken_whole(grid_b):
    """The oracle of grid B is a run that took the whole workload: the
    extras of the strategy's order and of the account's forced order reached
    the result with every colliding key (none merged, none refused)."""
    fresh = grid_b["fresh"]
    assert fresh["run"]["outcome"] == "ok"
    for coid, extra in fresh["run"]["orders"] + fresh["run"]["forced"]:
        if coid not in ("m1", "forced-1"):
            continue
        fields = {k[1]: v for k, v in extra[1]}
        # as many keys as the sender's own dict / frozenset holds (the sender's containers already
        # hold equal keys once), and more than one key of each colliding hash
        assert len(fields["'colliding_dict'"][1]) == fresh["sent"]["colliding_dict"], coid
        assert len(fields["'colliding_frozenset'"][1]) == fresh["sent"]["colliding_frozenset"], coid


@pytest.mark.parametrize("change", CHANGES)
def test_a_change_of_process_state_changes_nothing_through_library_code(grid_b, change):
    fresh = grid_b["fresh"]["run"]
    got = grid_b[change]
    assert got["run_a"] == fresh, f"{change}: the run whose strategy made the change differs from a fresh process"
    assert got["run_b"] == fresh, f"{change}: a clean run after it, in the same process, differs from a fresh one"
    assert got["in_core"] == [], f"{change}: the changer's code ran with the core as its caller: {got['in_core'][:5]}"


def test_the_core_writes_no_decimal_flag(grid_b):
    assert grid_b["fresh"]["flags"] == [], "the core's comparisons set flags in the thread's decimal context"


# ---- grid B': no late import, no table filled at run time -----------------------------------

def test_no_import_or_module_lookup_inside_a_function_of_the_core():
    found = []
    for path in sorted(glob.glob(os.path.join(CORE_DIR, "*.py"))):
        tree = ast.parse(open(path, encoding="utf-8").read())
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                continue
            for sub in ast.walk(node):
                text = ast.unparse(sub) if isinstance(sub, (ast.Attribute, ast.Call)) else ""
                if isinstance(sub, (ast.Import, ast.ImportFrom)):
                    found.append((os.path.basename(path), sub.lineno, ast.unparse(sub)))
                elif isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name) and sub.func.id == "__import__":
                    found.append((os.path.basename(path), sub.lineno, text[:60]))
                elif isinstance(sub, ast.Attribute) and text in ("sys.modules", "importlib.import_module"):
                    found.append((os.path.basename(path), sub.lineno, text))
    assert found == []


SNAPSHOT = r'''
import json, sys, types
sys.path.insert(0, HERE)
import bot.bt.core as core
from bot.bt.core import values, api, engine, events, history, interfaces, ordering, time, window, contract, errors, testing, strategy

def shape(v, depth=0):
    """What a module-level object holds, by identity: containers by the ids of their contents."""
    t = type(v)
    if isinstance(v, dict) or isinstance(v, types.MappingProxyType):
        return ["map", len(v), sorted((repr(k), id(x)) for k, x in v.items())] if depth < 2 else ["map", len(v)]
    if isinstance(v, (list, set, frozenset, tuple)):
        return ["seq", len(v), sorted(id(x) for x in v)]
    if isinstance(v, values.IdTable):
        d = object.__getattribute__(v, "_by_id")
        return ["idtable", len(d), sorted(d)]
    return ["obj", id(v)]

def snapshot():
    out = {}
    for name, mod in sorted(sys.modules.items()):
        if not name.startswith("bot.bt.core"):
            continue
        for k, v in sorted(vars(mod).items()):
            out[f"{name}.{k}"] = shape(v)
            if isinstance(v, type) and v.__module__ == name:
                for ck, cv in sorted(vars(v).items()):
                    if ck not in ("__doc__", "__weakref__"):
                        out[f"{name}.{k}.{ck}"] = shape(cv, 1)
    return out

before = snapshot()
import _r15_workload as W
before_w = snapshot()
W.run(); W.run()
after = snapshot()
changed = sorted(k for k in set(before_w) | set(after) if before_w.get(k) != after.get(k))
print(json.dumps(changed))
'''


def test_the_state_of_the_core_modules_is_the_same_after_runs_as_after_loading():
    env = dict(os.environ, PYTHONPATH=SRC, PYTHONHASHSEED="0")
    code = f"HERE = {HERE!r}\n" + SNAPSHOT
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, timeout=300)
    assert out.returncode == 0, out.stderr[-3000:]
    changed = json.loads(out.stdout)
    assert changed == [], f"module-level state of the core filled or changed by running: {changed}"


# ---- the core's equality of the numbers it builds -------------------------------------------

NUMBERS = [0, 1, -1, 2**70, True, 0.5, -0.0, 1e300, float("inf"), float("-inf"), float("nan"), 1 + 0j, 1 + 2j,
           complex(0.5, 0), Fraction(1, 2), Fraction(1, 3), Fraction(2**70), Fraction(-7, 4), Decimal("0.5"),
           Decimal("-0"), Decimal("1E+2"), Decimal("100"), Decimal("Infinity"), Decimal("-Infinity"),
           Decimal("NaN"), Decimal("1E+999999"), Decimal("1E-999999"), Decimal("0.3333"), Decimal(2**70),
           "a", b"a", None, (1,), frozenset(), np.float32(0.5), np.int64(100)]


def _built(x):
    return V.freeze(x)


@pytest.mark.parametrize("a", [x for x in NUMBERS if isinstance(x, (Fraction, Decimal))], ids=repr)
def test_the_cores_number_equality_is_pythons_in_a_clean_process(a):
    built = _built(a)
    assert isinstance(built, Fraction if isinstance(a, Fraction) else Decimal)
    for b in NUMBERS:
        for other in (b, _built(b) if not isinstance(b, (tuple, frozenset)) else b):
            try:
                want = bool(a == other)  # numpy answers with its own bool
            except TypeError:
                # the library itself fails here (the C decimal takes a numpy integer for a Rational
                # and cannot read its numerator); the core answers by the value
                assert type(built == other) is bool and type(built != other) is bool, (a, other)
                continue
            assert bool(built == other) is want, (a, other, want)
            assert bool(other == built) is want, (other, a, want)
            assert bool(built != other) is (not want), (a, other)
    if not (isinstance(a, Decimal) and a.is_nan()):
        assert hash(built) == hash(a)


def test_a_signaling_nan_is_not_equal_to_anything_whatever_the_context():
    import decimal

    s = V.freeze(Decimal("sNaN"))
    for other in (s, Decimal("sNaN"), 1, 1.0, Decimal(1), Fraction(1)):
        assert (s == other) is False and (s != other) is True
    ctx = decimal.getcontext()
    saved = ctx.traps[decimal.InvalidOperation]
    try:
        ctx.traps[decimal.InvalidOperation] = False
        assert (s == Decimal(1)) is False
    finally:
        ctx.traps[decimal.InvalidOperation] = saved


def test_fractions_and_decimals_read_back_as_the_cores_own_subclasses():
    req = OrderRequest(side="buy", order_type="market", size=1.0, client_order_id="o",
                       extra=(("f", Fraction(1, 3)), ("d", Decimal("2.5")), ("s", {Fraction(1, 2), Decimal(3)})))
    got = req.extra_dict()
    assert type(got["f"]) is V.PlainFraction and got["f"] == Fraction(1, 3) and isinstance(got["f"], Fraction)
    assert type(got["d"]) is V.PlainDecimal and got["d"] == Decimal("2.5") and isinstance(got["d"], Decimal)
    assert {type(x) for x in got["s"]} == {V.PlainFraction, V.PlainDecimal}
    # arithmetic is the library's, on the values
    assert got["f"] + 1 == Fraction(4, 3) and got["d"] * 2 == Decimal("5.0")


# ---- grid C: numbers and times keep their value or are refused -----------------------------

EXACT = 1_700_000_000_123_456_789
UNITS = {"s": 10**9, "ms": 10**6, "us": 10**3, "ns": 1}
TD_UNITS = ["Y", "M", "W", "D", "h", "m", "s", "ms", "us", "ns", "ps", "fs", "as"]


def _numpy_classes():
    return sorted(set(np.sctypeDict.values()), key=lambda c: c.__name__)


def _values_of(t):
    if issubclass(t, np.timedelta64):
        return [np.timedelta64(5, u) for u in TD_UNITS] + [np.timedelta64(5000, "ps")]
    if issubclass(t, np.datetime64):
        return [np.datetime64(5, u) for u in TD_UNITS]
    if issubclass(t, np.bool_):
        return [t(True)]
    if issubclass(t, np.integer):
        info = np.iinfo(t)
        return [t(0), t(5), t(info.max), t(info.min)]
    if issubclass(t, np.floating):
        return [t(0), t(1.5), t(-0.0), t(np.inf), t(np.nan), t("0.1"), t(1) / t(3),
                t("1700000000.123456789"), t("1700000000.5")]
    if issubclass(t, np.complexfloating):
        return [t(1 + 2j), t(1.5), t(np.longdouble(1) / 3) if t is np.clongdouble else t(0.5)]
    return []


NUMPY_VALUES = [v for t in _numpy_classes() for v in _values_of(t)]
PY_VALUES = [0, 5, 2**70, -3, True, 1.5, 0.1, -0.0, float("inf"), float("nan"), 1 + 2j, Fraction(3, 2),
             Fraction(1, 3), Fraction(EXACT, 10**9), Fraction(EXACT), Decimal("1.5"), Decimal("1E+3"),
             Decimal("1700000000.123456789")]


def _is_unit(v):
    return isinstance(v, (np.timedelta64, np.datetime64))


def _exact(v):
    """The test's own reading of a number: ('r', Fraction) / ('c', re, im) /
    ('nan',) / ('inf', sign) -- by the library, in this clean process."""
    if isinstance(v, (complex, np.complexfloating)):
        re, im = _exact(v.real), _exact(v.imag)
        return re if im == ("r", Fraction(0)) else ("c", re, im)
    if isinstance(v, (bool, np.bool_)):
        return ("r", Fraction(int(bool(v))))
    if isinstance(v, (int, np.integer)):
        return ("r", Fraction(int(v)))
    if isinstance(v, Decimal):
        if v.is_nan():
            return ("nan",)
        if v.is_infinite():
            return ("inf", -1 if v < 0 else 1)
        return ("r", Fraction(v))
    if isinstance(v, Fraction):
        return ("r", v)
    if isinstance(v, (float, np.floating)):
        if v != v:
            return ("nan",)
        if v in (np.inf, -np.inf):
            return ("inf", -1 if v < 0 else 1)
        n, d = v.as_integer_ratio()
        return ("r", Fraction(int(n), int(d)))
    raise TypeError(type(v))


@pytest.mark.parametrize("v", NUMPY_VALUES + PY_VALUES, ids=lambda v: f"{type(v).__name__}({v!r})")
@pytest.mark.parametrize("entry", ["freeze", "settle"])
def test_a_number_in_plain_data_keeps_its_value_or_is_refused(entry, v):
    fn = V.freeze if entry == "freeze" else V.settle
    try:
        got = fn(v)
    except ValueError:
        return
    assert not _is_unit(v), f"{entry}({v!r}): a count in a unit taken as the number {got!r}"
    assert _exact(got) == _exact(v), f"{entry}({type(v).__name__} {v!r}) gave {got!r}: not the same value"


def _stated_ns(v, unit):
    """The int of ns the value states in `unit`, or None when it states none
    (sub-ns digits, not a real number, a unit of its own, a value its
    conversion cannot hold) -- decided from the value by the documented rule."""
    f = UNITS[unit]
    if _is_unit(v) or isinstance(v, (bool, np.bool_, complex, np.complexfloating)):
        return None
    if isinstance(v, (int, np.integer)):
        q = Fraction(int(v) * f)
    elif isinstance(v, (float, np.floating)):
        fl = float(v)
        if fl != fl or fl in (math.inf, -math.inf):
            return None
        if _exact(np.float64(fl)) != _exact(v):  # the value is not a float: nothing exact to take
            return None
        q = Fraction(Decimal(float.__repr__(fl))) * f  # the documented shortest-repr reading
    elif isinstance(v, (Fraction, Decimal)):
        if isinstance(v, Decimal) and not v.is_finite():
            return None
        q = Fraction(v) * f
    else:
        return None
    return int(q) if q.denominator == 1 and -(2**63) <= q <= 2**63 - 1 else None


@pytest.mark.parametrize("v", NUMPY_VALUES + PY_VALUES, ids=lambda v: f"{type(v).__name__}({v!r})")
@pytest.mark.parametrize("unit", list(UNITS))
def test_to_nanos_gives_the_ns_the_value_states_or_refuses(unit, v):
    want = _stated_ns(v, unit)
    try:
        got = to_nanos(v, unit, plausible=(-(2**63), 2**63 - 1))
    except TimestampUnitError:
        got = None
    assert got == want, f"to_nanos({type(v).__name__} {v!r}, {unit!r}) = {got}; the value states {want}"


@pytest.mark.parametrize("v", NUMPY_VALUES + PY_VALUES, ids=lambda v: f"{type(v).__name__}({v!r})")
def test_validate_nanos_takes_an_int_as_itself_and_nothing_else(v):
    want = (int(v) if isinstance(v, (int, np.integer)) and not isinstance(v, (bool, np.bool_))
            and not _is_unit(v) and -(2**63) <= int(v) <= 2**63 - 1 else None)
    try:
        got = validate_nanos(v)
    except TimestampUnitError:
        got = None
    assert got == want and (got is None or type(got) is int), (v, got, want)


def _delay_run(delay):
    class Lat:
        def feed_delay_ns(self, event, *a):
            return 0

        def order_delay_ns(self, order, *a):
            return delay

        def cancel_delay_ns(self, cancel, *a):
            return 0

        def notice_delay_ns(self, report, *a):
            return 0

    class S:
        acks: list = []

        def on_event(self, ev, ctx):
            if type(ev).__name__ == "OrderAckEvent":
                S.acks.append(ev.received_time_ns - T0)
            if ev.received_time_ns == T0 and type(ev).__name__ == "BarEvent":
                ctx.place_order(OrderRequest(side="buy", order_type="market", size=1.0, client_order_id="o1"))

    S.acks = []
    bars = [BarEvent(received_time_ns=T0 + k, open=1.0, high=1.0, low=1.0, close=1.0, volume=1.0)
            for k in (0, 1, 5, 10, 5000, 10**12)]
    try:
        CoreEngine(S(), bars, fill_model=ImmediateFillModel(1.0), latency_model=Lat(), account=RecordingAccount(),
                   cost_model=NullCostModel()).run()
    except LatencyModelError:
        return None
    return S.acks[0] if S.acks else "no ack"


@pytest.mark.parametrize("v", [t(5) for t in _numpy_classes() if issubclass(t, (np.number, np.bool_))
                               and not issubclass(t, np.timedelta64)]
                         + [np.timedelta64(5, u) for u in TD_UNITS] + [np.timedelta64(5000, "ps"), 5, 5.0,
                                                                       Fraction(5), Decimal(5), True],
                         ids=lambda v: f"{type(v).__name__}({v!r})")
def test_a_delay_is_the_int_the_answer_states_or_refused(v):
    want = (int(v) if isinstance(v, (int, np.integer)) and not isinstance(v, (bool, np.bool_))
            and not _is_unit(v) else None)
    assert _delay_run(v) == want, v


# ---- grid D: the stack depth of the call -----------------------------------------------

def _frames() -> int:
    n, f = 0, sys._getframe()
    while f is not None:
        n += 1
        f = f.f_back
    return n


def _down(k, fn):
    return fn() if k <= 0 else _down(k - 1, fn)


def _with_headroom(h, fn):
    """Call `fn` with `h` frames left below the interpreter's recursion limit."""
    return _down(sys.getrecursionlimit() - h - _frames(), fn)


def _outcome(fn):
    try:
        r = fn()
        return ("ok", repr(type(r).__name__))
    except RecursionError:
        return ("RecursionError",)
    except Exception as exc:  # noqa: BLE001 - the kind of refusal is what is compared
        return ("raised", type(exc).__name__)


def _nest(kind, n):
    if kind == "set_of_tuple":
        v = 1
        for _ in range(max(0, n - 1)):
            v = (v,)
        return {v}
    if kind == "frozendict_key":
        v = 1
        for _ in range(max(0, n - 1)):
            v = V.FrozenDict({"k": v})
        return {v: 1}
    v = 1
    for _ in range(n):
        v = [v] if kind == "list" else (v,) if kind == "tuple" else {"k": v}
    return v


KINDS = ["list", "tuple", "dict", "set_of_tuple", "frozendict_key"]
NESTS = [1, 10, 50, V.MAX_NESTING - 2, V.MAX_NESTING, V.MAX_NESTING + 1]
HEADROOMS = [getattr(V, "CALL_FRAMES", 40), getattr(V, "CALL_FRAMES", 40) + 5, 60, 200]


def _entry_outcome(entry, value, headroom):
    frozen = None
    try:
        frozen = V.freeze(value)
    except ValueError:
        pass
    if entry == "freeze":
        fn = lambda: V.freeze(value)  # noqa: E731
    elif entry == "settle":
        fn = lambda: V.settle(value)  # noqa: E731
    elif entry == "renew":
        if frozen is None:
            return ("not built",)
        fn = lambda: V.renew(frozen)  # noqa: E731
    elif entry == "thaw":
        if frozen is None:
            return ("not built",)
        fn = lambda: V.thaw(frozen)  # noqa: E731
    else:
        return _engine_outcome(entry, value, headroom)
    return _outcome(fn) if headroom is None else _with_headroom(headroom, lambda: _outcome(fn))


def _engine_outcome(entry, value, headroom):
    out = []

    class S:
        n = 0

        def on_event(self, ev, ctx):
            if type(ev).__name__ != "BarEvent":
                return
            S.n += 1

            def act():
                if entry == "place_order":
                    return _outcome(lambda: ctx.place_order(OrderRequest(
                        side="buy", order_type="limit", price=1.0, size=1.0, client_order_id="o1",
                        extra=(("k", value),))))
                view = ctx.order("o1")
                if view is None:
                    return ("no order",)
                return _outcome(lambda: view.request.extra_dict())

            if entry == "place_order" and S.n == 1:
                out.append(act() if headroom is None else _with_headroom(headroom, act))
            elif entry == "order_view" and S.n == 1:
                try:
                    ctx.place_order(OrderRequest(side="buy", order_type="limit", price=1.0, size=1.0,
                                                 client_order_id="o1", extra=(("k", value),)))
                except OrderApiError:
                    out.append(("raised", "OrderApiError"))
            elif entry == "order_view" and S.n == 2 and not out:
                out.append(act() if headroom is None else _with_headroom(headroom, act))

    bars = [BarEvent(received_time_ns=T0 + k, open=1.0, high=1.0, low=1.0, close=1.0, volume=1.0) for k in (0, 10)]
    CoreEngine(S(), bars, fill_model=ImmediateFillModel(1.0), account=RecordingAccount(),
               cost_model=NullCostModel()).run()
    return out[0] if out else ("nothing",)


@pytest.mark.parametrize("entry", ["freeze", "settle", "renew", "thaw", "place_order", "order_view"])
@pytest.mark.parametrize("kind", KINDS)
def test_an_entry_takes_a_value_alike_at_every_stack_depth(entry, kind):
    for n in NESTS:
        value = _nest(kind, n)
        top = _entry_outcome(entry, value, None)
        assert top[0] != "RecursionError", (entry, kind, n, top)
        for h in HEADROOMS:
            here = _entry_outcome(entry, value, h)
            assert here == top, f"{entry} {kind} nesting {n}: {here} with {h} frames of headroom, {top} with all"


def _colliding_nested(n):
    a, b = -1, -2  # hash(-1) == hash(-2)
    for _ in range(n):
        a, b = (a,), (b,)
    assert hash(a) == hash(b) and a != b
    return frozenset([a, b])


@pytest.mark.parametrize("entry", ["freeze", "settle", "renew", "thaw", "place_order"])
@pytest.mark.parametrize("n", [10, 50, V.MAX_NESTING - 2])
def test_colliding_nested_values_are_refused_by_the_entry_never_recursion_error(entry, n):
    value = _colliding_nested(n)
    top = _entry_outcome(entry, value, None)
    k = getattr(V, "CALL_FRAMES", 40)
    for h in (k, k + 5, 60):
        here = _entry_outcome(entry, value, h)
        assert here[0] != "RecursionError", (entry, n, h, here)
        assert here == top or here[0] == "raised", (entry, n, h, here, top)
    assert _entry_outcome(entry, value, k + n + 30) == top, (entry, n)
