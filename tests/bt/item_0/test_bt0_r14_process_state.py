"""Round 14 (i0-r13-01): what the core accepts, refuses or computes is
decided by the value and by objects bound when the core was loaded -- never
by process-wide state read at run time (ABC registries and caches,
sys.modules and a library's attributes, a thread's decimal context, the
int <-> str digit limit, the recursion limit and the depth of the stack).

Every case runs in a FRESH interpreter (`_r14_state_child.py`): the changes
cannot be undone and would change every later test of the session. The
children of grid 1 run in parallel.

Grid 1 (`test_a_change_of_process_state_changes_nothing_the_core_decides`):
  changes = the child's CHANGES, read from the modules, not from the core:
  every ABC of `numbers` and `collections.abc` x {register every type the
  battery uses; a subclass whose metaclass answers True to
  __subclasscheck__ / __instancecheck__, after a registration that clears
  every negative cache}; the decimal context (precision 1; floor rounding
  at precision 3; no traps; a lower-case exponent; Emax 5); the digit limit
  640; numpy's names bool_, integer, floating, inexact, number, generic,
  float32, int64, float64, complexfloating set to a class of the
  strategy's; sys.modules['numpy'] replaced by a module of the strategy's;
  warnings turned into errors; numpy's floating-point errors raised; a codec
  error handler registered under "surrogatepass" and under "strict" -- each
  made by a strategy inside its own on_event.
  sites = every place the core decides a value: a plug-in's answer taken
  after its call (the fee, a delay), a fill's price made inside the fill
  model's call, the strategy's order fields (size, post_only), a timer from
  the outbox and from set_timer, an event's number and time, to_nanos
  (numbers, and texts / Decimals in every unit), validate_nanos, a FAILED
  engine's text of a strategy's exception, the shape of the engine's input
  (list, tuple, dict, mappingproxy, OrderedDict, generator), keys whose
  hashes collide (a FrozenDict and the frozenset of its items, in a dict both
  orders, in a frozenset, in a list) at freeze / settle / extra / the outbox,
  and texts with a lone surrogate (an order id, a timer tag, freeze).
  values = every numpy scalar type (numpy's own table), int, float, complex,
  bool, str, Fraction, Decimal, a Python class deriving numbers.Real, a
  Python class that converts but is not a number, a class of the
  strategy's, an object.
  Oracle: the same outcomes after the change as before it, and no code of
  the changer runs with a core frame on the stack outside its own call.

Grid 2 (`test_in_a_clean_process_...`): every class in a clean process
  (numpy, pandas and the core loaded): the core's number kind equals the
  numbers ABCs' answer for every static class, and its mapping decision the
  Mapping ABC's for every class.

Grid 3 (`test_an_int_too_long_to_print_...`): every entry that takes an int
  (validate_nanos, to_nanos in 4 units, an event's two times, the engine's
  history_limit / end_time_ns / time_span_ns, set_timer, the history read's
  n / since_ns / until_ns, a timer in the outbox, the 4 delays, the
  arguments of a strategy's exception) x {+-10**5000, 2**2000, +-2**2001}
  x digit limit {the default, 640}. Oracle: the same outcome kind and type
  as an int just outside int64 of the same sign (2**63, -2**63-1), never an
  error of the digit limit.

Grid 4 (`test_plain_data_nesting_...`): containers (tuple, list, dict,
  frozenset, a set outermost) x depth 0..MAX_NESTING+3 x entry (freeze,
  settle, OrderRequest.extra inside place_order, a request put in the outbox
  whose extra was set behind the class's back, a timer tag in the outbox) x
  frames the strategy used first {0, 300}. Oracle: a value of `depth`
  containers is taken iff depth <= MAX_NESTING, counted from the field that
  holds it (extra's own tuple and its pair are 2), refused otherwise by the
  entry's error; the same for both stack depths.

NOT in the grids (A-10): rebinding a name the core CALLS -- a builtin
(`len`, `type`), a library's function (`heapq.heappush`), the core's own
module globals -- which changes the program's code (the contract's
`process_state`); interpreter hooks (sys.settrace / setprofile, audit
hooks, gc callbacks, signal handlers, threads the strategy starts); a
recursion limit set below what the core needs; ABCs of other modules (io,
os.PathLike, contextlib) -- the core's source asks no ABC at all
(`test_the_core_asks_no_abc_...` reads every isinstance / issubclass / is_a
in it), so which ABC changes is not an axis once no ABC is asked.
"""
from __future__ import annotations

import ast
import concurrent.futures
import json
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.abspath(os.path.join(HERE, "..", "..", "..", "src"))
CHILD = os.path.join(HERE, "_r14_state_child.py")
CORE = os.path.join(SRC, "bot", "bt", "core")


def _child(*args: str, timeout: int = 300):
    env = dict(os.environ, PYTHONPATH=SRC)
    out = subprocess.run([sys.executable, CHILD, *args], env=env, capture_output=True, text=True,
                         timeout=timeout)
    assert out.returncode == 0, f"{args}: {out.stderr[-3000:]}"
    return json.loads(out.stdout)


CHANGES = _child("changes")


@pytest.fixture(scope="module")
def state_results():
    workers = max(2, min(8, os.cpu_count() or 2))
    with concurrent.futures.ThreadPoolExecutor(workers) as pool:
        futures = {c: pool.submit(_child, "state", c) for c in CHANGES}
        return {c: f.result() for c, f in futures.items()}


def _diff(before: dict, after: dict) -> list:
    out = []
    for site, cells in before.items():
        for label, got in cells.items():
            if after[site][label] != got:
                out.append((site, label, got, after[site][label]))
    return out


def test_the_grid_holds_every_abc_and_every_setting():
    assert any(c.startswith("register:numbers.") for c in CHANGES)
    assert "register:collections.abc.Mapping" in CHANGES and "hook:numbers.Integral" in CHANGES
    assert len([c for c in CHANGES if c.startswith("hook:")]) == len([c for c in CHANGES if c.startswith("register:")]) >= 25


@pytest.mark.parametrize("change", CHANGES)
def test_a_change_of_process_state_changes_nothing_the_core_decides(state_results, change):
    got = state_results[change]
    assert got["applied"], "the strategy did not make the change"
    assert _diff(got["before"], got["after"]) == []
    assert got["hooks_in_core"] == []


def test_the_battery_itself_decides_the_values_by_the_rule(state_results):
    """The clean battery states the rule (not only its invariance): a class
    that converts but is not a number (not derived from a numbers ABC) is
    refused everywhere; a Python class deriving numbers.Real is converted
    inside its sender's call and refused after it; numpy's numbers are
    converted by their own C code; a float32 fee reaches the account as the
    float it holds."""
    b = state_results["digits:640"]["before"]
    for site in ("fee", "delay", "fill_price", "size", "bar_open", "to_nanos_s", "timer_outbox"):
        assert b[site]["RegOnly"][0] == "raised", (site, b[site]["RegOnly"])
    assert b["size"]["Inherits"][0] == "ok" and b["bar_open"]["Inherits"] == ["ok", ["float", "0.75"]]
    assert b["fee"]["Inherits"] == ["raised", "CostModelError"]
    assert b["delay"]["Inherits"] == ["raised", "LatencyModelError"]
    assert b["fee"]["numpy.float32"][1][2] == [["float", "0.75"]]
    assert b["delay"]["numpy.float32"] == ["raised", "LatencyModelError"]
    fills = [e for e in b["fill_price"]["numpy.float32"][1][0] if e[0] == "ORDER_FILL"]
    assert [e[2] for e in fills] == [["float", "0.75"]], b["fill_price"]["numpy.float32"]
    assert b["timer_outbox"]["Foo"] == ["raised", "OrderApiError"]
    for shape in ("list", "tuple", "dict", "mappingproxy", "OrderedDict", "generator"):
        assert b["events_shape"][shape][0] == "ok", (shape, b["events_shape"][shape])


def test_in_a_clean_process_the_core_decides_numbers_and_mappings_as_the_abcs_do():
    got = _child("equivalence")
    assert got["numbers_diff"] == [] and got["mapping_diff"] == []
    # round 15 (i0-r14-04): the one difference, by rule: numpy's counts in a unit (the ABCs call a
    # timedelta64 an Integral; the core refuses it; a datetime64 is no number for either)
    assert sorted(got["units"]) == [["numpy.datetime64", None, None], ["numpy.timedelta64", "int", None]]
    assert got["static"] > 50 and got["classes"] > 1000


@pytest.mark.parametrize("limit", ["default", "640"])
def test_an_int_too_long_to_print_is_refused_by_the_entrys_own_error(limit):
    got = _child("bigint", limit)
    bad = []
    for entry, cells in got.items():
        for label, out in cells.items():
            if out[0] == "raised" and out[2] == "digit limit":
                bad.append((entry, label, out))
            ref = cells["+ref"] if not label.startswith("-") else cells["-ref"]
            if out[:2] != ref[:2]:
                bad.append((entry, label, out, "ref", ref))
    assert bad == []


@pytest.fixture(scope="module")
def nesting_results():
    with concurrent.futures.ThreadPoolExecutor(2) as pool:
        a, b = pool.submit(_child, "nesting", "0", timeout=600), pool.submit(_child, "nesting", "300", timeout=600)
        return a.result(), b.result()


def test_plain_data_nesting_is_decided_by_the_value_alone(nesting_results):
    shallow, deep = nesting_results
    limit = shallow["MAX_NESTING"]
    assert deep["MAX_NESTING"] == limit and shallow["cells"] == deep["cells"]
    bad = []
    for key, cell in shallow["cells"].items():
        depth = int(key.split(":")[1])
        want = {
            "freeze": ["ok"] if depth <= limit else ["raised", "ValueError", ""],
            "settle": ["ok"] if depth <= limit else ["raised", "Unsettled", ""],
            "extra": ["ok"] if depth + 2 <= limit else ["raised", "OrderApiError", ""],
            "extra_run": ["ok"],
            "outbox_extra": ["ok"] if depth + 2 <= limit else ["raised", "OrderApiError", ""],
            "timer_tag": ["raised", "OrderApiError", ""],
        }
        for entry, w in want.items():
            if cell[entry] != w:
                bad.append((key, entry, cell[entry], w))
    assert bad == []


# ---- the source: the core asks no ABC and reads no module registry ---------------------

def _core_modules():
    import importlib

    for name in sorted(os.listdir(CORE)):
        if name.endswith(".py"):
            mod = importlib.import_module(f"bot.bt.core.{name[:-3]}") if name != "__init__.py" else None
            with open(os.path.join(CORE, name), encoding="utf-8") as fh:
                yield name, mod, ast.parse(fh.read())


def _classes_named(node, mod):
    """The objects a type-check's second argument names (a name, an attribute
    chain or a tuple of them), looked up in the module."""
    if isinstance(node, ast.Tuple):
        out = []
        for e in node.elts:
            out.extend(_classes_named(e, mod))
        return out
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if not isinstance(node, ast.Name):
        return [("<expr>", None)]
    import builtins

    obj = getattr(mod, node.id, getattr(builtins, node.id, None))
    for p in reversed(parts):
        obj = getattr(obj, p, None)
    return [(ast.unparse(node) + "".join("." + p for p in reversed(parts)), obj)]


def test_the_core_asks_no_abc_about_a_value():
    """Every isinstance / issubclass / is_a in the core names classes whose
    metaclass is `type` itself (the check walks the MRO; no ABC registry,
    cache or hook is asked). A check whose class is an expression (a
    parameter) is listed for reading."""
    asks, unresolved = [], []
    for name, mod, tree in _core_modules():
        if mod is None:
            continue
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id in ("isinstance", "issubclass", "is_a") and len(node.args) == 2):
                continue
            for text, obj in _classes_named(node.args[1], mod):
                if obj is None:
                    unresolved.append((name, node.lineno, text))
                elif type(obj) is not type:
                    asks.append((name, node.lineno, text, type(obj).__name__))
    assert asks == []
    # the helpers that take the class as a parameter: `is_a` itself (values.py) and the
    # checks inside the core's own generic helpers
    assert {(n, t) for n, _, t in unresolved} <= {("values.py", "cls"), ("values.py", "convert"),
                                                  ("values.py", "c")}, unresolved


def test_the_core_reads_no_module_registry_at_run_time():
    hits = []
    for name, _mod, tree in _core_modules():
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr == "modules" and isinstance(node.value, ast.Name) \
                    and node.value.id == "sys":
                hits.append((name, node.lineno))
    assert hits == []


def test_the_contract_states_the_rule_from_the_code():
    from bot.bt.core import values as V
    from bot.bt.core.contract import CORE_CONTRACT

    vis = CORE_CONTRACT["visibility"]
    text = vis["process_state"]
    # core-16 (round 15): the rule of process_state reaches the library code the core runs;
    # core-17 (round 16): one reading of a value (a float time, a float field, a key without a hash,
    # colliding nested FrozenDicts compared iteratively);
    # core-18 (round 17): each container taken once per object, a key read back with a hash,
    # several colliding candidates compared on one stack
    # core-19 (item 4 round 1): a key's hash bounded by the objects it visits, the walk memo holds its
    # containers, freeze's places made only when named
    assert CORE_CONTRACT["version"] == "core-19"
    assert str(V.MAX_NESTING) in text and str(V.INT_TEXT_BITS) in text and "NUMBER_BASES" in text
    assert "registered with the numbers ABCs" not in vis["scope"] and "process_state" in vis["scope"]
    assert [k.__name__ for _, k in V.NUMBER_BASES] == ["int", "int", "float", "float", "complex", "complex"]
    assert "MAX_NESTING" in V.PLAIN_DATA_RULE and "NUMBER_BASES" in V.PLAIN_DATA_RULE


@pytest.mark.parametrize("name", ["bool_", "integer", "floating", "inexact"])
def test_the_core_refuses_to_load_with_a_numpy_changed_before_it(name):
    """The numpy classes the core decides by are bound at load and must be
    numpy's own C classes; a numpy whose name was set to a class written in
    Python before the core was loaded is refused (ImportError), never used."""
    code = (f"import numpy\nnumpy.{name} = type('Planted', (), {{}})\n"
            "try:\n    import bot.bt.core\nexcept ImportError as exc:\n    print('ImportError', 'numpy.' in str(exc))\n"
            "else:\n    print('loaded')\n")
    env = dict(os.environ, PYTHONPATH=SRC)
    out = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, timeout=120)
    assert out.stdout.strip() == "ImportError True", out.stdout + out.stderr[-2000:]
