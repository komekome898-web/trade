"""Helpers shared by adapters. Pure data handling of the scene inputs; no
grading, no knowledge of any target. Standard library only (reproductions
and venv adapters import this under plain interpreters)."""
from __future__ import annotations

from typing import Any


def events(scene) -> list[dict]:
    """The scene's single event list (scenes with `streams` use `streams_*`)."""
    return [dict(e) for e in scene.input["events"]]


def as_bar(e: dict) -> dict:
    """The `any_type` substitution: a trade becomes a bar at the same time with
    open = high = low = close = its price (receive time kept)."""
    if e.get("kind", "trade") != "trade":
        return dict(e)
    out = {"kind": "bar", "ts_ns": e["ts_ns"], "open": e["price"], "high": e["price"],
           "low": e["price"], "close": e["price"], "volume": e.get("qty", 1.0), "substituted_from": "trade"}
    if "recv_ns" in e:
        out["recv_ns"] = e["recv_ns"]
    return out


def recv(e: dict) -> int:
    return int(e.get("recv_ns", e["ts_ns"]))


def streams_in_order(scene, order: list[str] | None = None) -> list[tuple[str, list[dict]]]:
    order = order or scene.input["hand_over_order"]
    return [(name, [dict(e) for e in scene.input["streams"][name]]) for name in order]


def concatenated(scene, order: list[str] | None = None) -> list[dict]:
    """Streams joined in hand-over order, NOT sorted (for single-input targets)."""
    out: list[dict] = []
    for _, evs in streams_in_order(scene, order):
        out.extend(evs)
    return out


def fields_of(e: dict) -> dict[str, Any]:
    return {k: v for k, v in e.items() if k not in ("kind", "ts_ns", "recv_ns", "substituted_from")}


_EPOCH = None


def ns_to_dt(ns: int):
    """int ns -> timezone-aware UTC datetime (the type some targets require).
    datetime holds microseconds; the sub-microsecond part is dropped by floor
    division -- that loss belongs to the target's time type, and scenes see it."""
    import datetime as _dt
    return _dt.datetime(1970, 1, 1, tzinfo=_dt.timezone.utc) + _dt.timedelta(microseconds=int(ns) // 1000)


def dt_to_ns(d) -> int:
    """aware datetime -> int ns with integer arithmetic (no float rounding)."""
    import datetime as _dt
    delta = d - _dt.datetime(1970, 1, 1, tzinfo=_dt.timezone.utc)
    return (delta.days * 86_400 + delta.seconds) * 1_000_000_000 + delta.microseconds * 1_000


# ---------------------------------------------------------------- P0-4 reads
def plain(v, depth: int = 0):
    """A JSON-able copy of what a read returned, so the runner can look for the
    future value in it (numbers stay numbers; objects with a `close` give it;
    anything else becomes its repr). Standard library only."""
    if depth > 6:
        return repr(v)[:120]
    if v is None or isinstance(v, (bool, str)):
        return v
    if isinstance(v, (int, float)):
        return v
    try:
        from decimal import Decimal
        if isinstance(v, Decimal):
            return float(v)
    except Exception:  # noqa: BLE001
        pass
    if hasattr(v, "isoformat") and callable(v.isoformat):
        try:
            return v.isoformat()
        except Exception:  # noqa: BLE001
            return repr(v)[:120]
    if hasattr(v, "item") and callable(getattr(v, "item")) and getattr(v, "shape", None) == ():
        return plain(v.item(), depth + 1)  # numpy scalar
    if isinstance(v, dict):
        return {str(k): plain(u, depth + 1) for k, u in list(v.items())[:200]}
    if hasattr(v, "to_dict") and hasattr(v, "columns"):  # a DataFrame: its columns as lists
        return {str(c): plain(list(v[c]), depth + 1) for c in list(v.columns)[:20]}
    if hasattr(v, "tolist") and callable(v.tolist):
        return plain(v.tolist(), depth + 1)
    if isinstance(v, (list, tuple, set, frozenset)):
        return [plain(u, depth + 1) for u in list(v)[:500]]
    for attr in ("close", "close_price"):
        if hasattr(v, attr):
            try:
                return {attr: plain(getattr(v, attr), depth + 1), "repr": repr(v)[:120]}
            except Exception:  # noqa: BLE001
                break
    import re
    return re.sub(r"0x[0-9a-fA-F]+", "0x…", repr(v))[:120]


class Attempts:
    """Records the P0-4 reads one by one (scene p4-future-read-attempt): the
    means, the form (`time` / `position` name the future bar; `other` reads
    that do not name it), the exception's name or the value returned. The
    runner grades; this class only records.

    Round r6-1 (critic i0-r5-03): every attempt also carries `shape` and
    `naming`. Which namings a read gets is NOT the adapter's choice: the
    position and time namings are applied as a whole by
    `try_position_namings` / `try_time_namings` from the list fixed in
    scenes.py (`NAMING_SHAPES`), and run_battery.py refuses to grade a means
    whose namings are not the whole list. `shape` is one of:
      position     a read that takes an index / a slice (all POSITION_NAMINGS)
      time_at / time_until / time_since / time_range
                   a read that takes one time / only an end / only a start /
                   both ends (all TIME_NAMINGS[shape])
      next_call    a call that returns the next item (peek / next), once
      no_means     the target hands the strategy no read of this form (none
                   that takes a time, for form `time`; none that takes a
                   position, for form `position`): the call a strategy would
                   write, written and called as it is; graded like any named
                   read (a value returned is a read that was not stopped)
      other        a read that does not name the future bar
    """

    def __init__(self) -> None:
        self.items: list[dict] = []

    @staticmethod
    def _shape(form: str, shape):
        if shape is not None:
            return shape
        return "other" if form == "other" else None  # a named read without a shape is refused by the runner

    def _record(self, means, form, shape, naming, exc, v, touched, via) -> None:
        import re
        item = Record({"means": means, "form": form, "shape": shape, "naming": naming, "touched": touched,
                "via": via if via is None or (isinstance(via, (Record, Made)) and made_here(via)) else carrier(via)})
        if exc is not None:
            # memory addresses in messages differ between runs and would read as "2 回で違う"
            item.update({"raised": type(exc).__name__, "message": re.sub(r"0x[0-9a-fA-F]+", "0x…", str(exc))[:160],
                         "returned": None, **_raise_site(exc)})
        else:
            item.update({"raised": None, "returned": plain(v)})
        self.items.append(_register(item))

    def run(self, means: str, form: str, fn, shape=None, naming=None, via=None) -> None:
        """One attempt. `via` = the target object the attempt reads through
        (for a written call that fails before any target code runs, e.g. a
        wrong signature: the target's bound method / the target's object)."""
        shape = self._shape(form, shape)
        naming = naming if naming is not None else ("other" if shape == "other" else None)
        exc, v, touched = _profiled(fn)
        self._record(means, form, shape, naming, exc, v, touched, via)

    def compiled(self, means: str, form: str, shape, naming, via: str, raised=None, message: str = "", returned=None,
                 expressible: bool = True) -> None:
        """One attempt a compiled tool's driver made and printed (the Python side
        only copies it): `via` = the tool's function / type name the driver
        called (a `compiled` name, checked against the target's namespace)."""
        item = Record({"means": means, "form": form, "shape": shape, "naming": naming, "touched": [], "via": compiled(via),
                       "raised": raised, "message": message, "returned": returned})
        if not expressible:
            item["expressible"] = False
        self.items.append(_register(item))

    async def run_async(self, means: str, form: str, make_coro, shape=None, naming=None, via=None) -> None:
        shape = self._shape(form, shape)
        naming = naming if naming is not None else ("other" if shape == "other" else None)
        files: set = set()
        exc, v = None, None
        try:
            # a coroutine suspends; the profile of creating it is what the call touched synchronously,
            # and the awaited body is profiled below through the running loop's frames
            prev = _sys.getprofile()

            def prof(frame, event, arg):
                if event == "call":
                    files.add(frame.f_code.co_filename)
                elif event == "c_call":
                    files.add(code_file(arg) or "")
            _sys.setprofile(prof)
            try:
                v = await make_coro()
            finally:
                _sys.setprofile(prev)
        except Exception as e:  # noqa: BLE001
            exc = e
        touched = sorted({p for p in (_real(f) for f in files) if p and not in_scene_set(p)})
        self._record(means, form, shape, naming, exc, v, touched, via)

    def output(self) -> dict:
        return {"attempts": list(self.items)}

    def summary(self) -> str:
        out = []
        for a in self.items:
            got = f"{a['raised']}: {a['message']}" if a["raised"] else f"-> {str(a['returned'])[:120]}"
            out.append(f"[{a['shape']} {a['naming']}] {a['means']} {got}")
        return " ; ".join(out)


def _namings():
    import scenes  # the fixed list (scenes.py); standard library only
    return scenes.POSITION_NAMINGS, scenes.TIME_NAMINGS, scenes.DAY


def _position_key(naming: str, n: int):
    return {"[n]": n, "[n:]": slice(n, None), "[n:n+1]": slice(n, n + 1), "[n-1:n+1]": slice(n - 1, n + 1),
            "[n::2]": slice(n, None, 2), "[n:n]": slice(n, n), "[n::-1]": slice(n, None, -1),
            "[:n:-1]": slice(None, n, -1)}[naming]


def values_of(v, get=None):
    """What a read returned, as plain values: `get` (e.g. the close of an
    event object) applied to one item, or to each item of a slice."""
    if get is None:
        return v
    if isinstance(v, (str, bytes)) or not hasattr(v, "__iter__"):
        return get(v)
    return [get(x) for x in v]


class KeyCall:
    """For a target's read that takes the position as an argument (`f(k)`):
    `KeyCall(f)[key]` is `f(key)` -- the naming's key (an int or a slice)
    handed to the target's own function as it is, nothing else."""

    def __init__(self, fn) -> None:
        self.fn = fn

    def __getitem__(self, key):
        return self.fn(key)


def try_position_namings(att: Attempts, means: str, seq_fn, n: int, get=None, via=None) -> None:
    """Every position naming of scenes.POSITION_NAMINGS on the read `seq_fn()`
    (re-read for each naming), with `n` = the position right after the newest
    delivered event in the target's own way of counting; `get` turns an
    item of the read into its close (for the runner's look for 104). `via` =
    the target object read, when the read runs no target code (Attempts.run)."""
    for naming in _namings()[0]:
        key = _position_key(naming, n)
        att.run(means, "position", lambda key=key: values_of(seq_fn()[key], get), shape="position", naming=naming, via=via)


def _time_args(shape: str, naming: str, sc, to_t):
    _, times, day = _namings()
    first = int(sc.input["events"][0]["ts_ns"])
    fut = int(sc.input["future_ts_ns"])
    now = int(sc.input["probe_at_ns"])
    return {"at(fut)": (fut,), "until(fut)": (fut,), "until(fut+1d)": (fut + day,),
            "since(fut)": (fut,), "since(now+1ns)": (now + 1,),
            "range(first,fut)": (first, fut), "range(fut,fut)": (fut, fut),
            "range(now+1ns,fut+1d)": (now + 1, fut + day)}[naming]


def try_time_namings(att: Attempts, means: str, shape: str, read, sc, to_t=lambda ns: ns, via=None) -> None:
    """Every time naming of scenes.TIME_NAMINGS[shape] through `read(*times)`,
    each time converted by `to_t` (the target's time type)."""
    for naming in _namings()[1][shape]:
        args = tuple(to_t(t) for t in _time_args(shape, naming, sc, to_t))
        att.run(means, "time", lambda args=args: read(*args), shape=shape, naming=naming, via=via)


async def try_time_namings_async(att: Attempts, means: str, shape: str, read, sc, to_t=lambda ns: ns, via=None) -> None:
    for naming in _namings()[1][shape]:
        args = tuple(to_t(t) for t in _time_args(shape, naming, sc, to_t))
        await att.run_async(means, "time", lambda args=args: read(*args), shape=shape, naming=naming, via=via)


# ---------------------------------------------------------------- provenance
# Round r6-2 (critic br6-1-1 / br6-1-2). Where a measured thing came from is
# written here FROM THE OBJECTS (never typed by an adapter) as facts: files.
# Which files belong to the target is not known here; run_battery.py decides
# with its own table of the target's distribution (`TARGET_DISTS`) and
# accepts only records made here (`Record` / `Made`), so a string or a dict
# an adapter writes by hand is refused.
#
# Facts recorded for an object the strategy received (`carrier`):
#   type / type_file   its class and the file of the module that defines it
#                      (a numba jitclass box: the class the target wrote);
#   code_file          for a function: the file of its code;
#   passed_by          the files of the frames outside the scene set that
#                      called the strategy's callback, when the object is an
#                      argument of that call (alpha);
#   returned_by        the file of the target function that returned it,
#                      when the strategy read it through `read(fn, ...)` (beta);
#   held_by            where a scene-set frame outside the strategy's call
#                      holds the same object (an input the adapter handed in
#                      and the target forwarded), or None;
#   tag / dtype        the target's tag object (enum member, named constant)
#                      and a numpy record's dtype, each with its own file.
import os as _os
import sys as _sys
from pathlib import Path as _Path

BATTERY_DIR = _os.path.realpath(str(_Path(__file__).resolve().parent.parent))
_HERE_FILE = _os.path.realpath(__file__)


class Record(dict):
    """A provenance record made by this module from an object."""


class Made(str):
    """A name made by this module from an object (`qualname`) or a compiled
    driver's type name (`compiled`). `file` is the defining file, if any."""

    file: str | None = None
    compiled: bool = False


def _real(path):
    if not path or not isinstance(path, str):
        return None
    if not _os.path.isabs(path):
        return None  # exec'd / generated code with a pseudo name: belongs to no one
    return _os.path.realpath(path)


_GENERATED: set = set()  # code files an adapter wrote outside the scene set (a strategy file a tool loads by path)


def scene_set_file(path) -> None:
    """Declare a code file an adapter generated (e.g. a strategy module the
    tool imports from a directory) as the scene set's own code."""
    _GENERATED.add(_os.path.realpath(str(path)))


def in_scene_set(path) -> bool:
    """A frame of the scene set (adapters, runner, scenes, opponents, and the
    code files adapters generated). A frame with a pseudo file name
    ('<string>', an exec'd copy) counts as the scene set's: code nobody can
    place is never credited to the target."""
    if not path:
        return True
    if path.startswith("<frozen "):
        return False  # the interpreter's own frozen modules (importlib): the standard library
    if not _os.path.isabs(path):
        return True
    rp = _os.path.realpath(path)
    return rp == BATTERY_DIR or rp.startswith(BATTERY_DIR + _os.sep) or rp in _GENERATED


def _module_file(modname):
    m = _sys.modules.get(modname or "")
    return _real(getattr(m, "__file__", None))


def _numba_class_type(t):
    nt = getattr(t, "_numba_type_", None)
    return getattr(nt, "class_type", None) if nt is not None else None


def type_file(t):
    """The file of the module that defines class `t`. A numba jitclass box
    (its class lives in numba's module) is placed by the Python code of the
    class the target wrote: `_numba_type_.class_type.methods` are the target's
    own functions."""
    ct = _numba_class_type(t)
    if ct is not None:
        cd = getattr(ct, "class_def", None)
        if isinstance(cd, type):
            return _module_file(cd.__module__)
        files = sorted({_real(f.__code__.co_filename) for f in (getattr(ct, "methods", None) or {}).values()
                        if hasattr(f, "__code__")} - {None})
        if len(files) == 1:
            return files[0]
    return _module_file(getattr(t, "__module__", None))


def code_file(fn):
    """The file of the code of a function / method / numba dispatcher, or of
    the module / class a C function belongs to."""
    s = getattr(fn, "__self__", None)
    if s is not None and _numba_class_type(type(s)) is not None:
        disp = (getattr(_numba_class_type(type(s)), "jit_methods", None) or {}).get(getattr(fn, "__name__", ""))
        py = getattr(disp, "py_func", None)
        return _real(py.__code__.co_filename) if py is not None else type_file(type(s))
    name = getattr(fn, "__name__", None)
    if s is not None and not isinstance(s, type(_sys)) and name and not hasattr(fn, "__func__"):
        # a bound C method (pybind11 / builtin): placed by the class in the MRO that defines it
        for k in type(s).__mro__:
            if name in vars(k):
                return type_file(k)
    f = getattr(fn, "__func__", fn)
    py = getattr(f, "py_func", None)  # a numba dispatcher: the Python function it compiled
    if py is not None:
        f = py
    code = getattr(f, "__code__", None)
    if code is not None:
        return _real(code.co_filename)
    mod = getattr(f, "__module__", None)
    if mod:
        got = _module_file(mod)
        if got:
            return got
    if s is not None and not isinstance(s, type(_sys)):
        return type_file(type(s))
    if isinstance(s, type(_sys)):
        return _real(getattr(s, "__file__", None))
    return None


def _args_of(fr) -> list:
    code = fr.f_code
    n = code.co_argcount + code.co_kwonlyargcount
    names = list(code.co_varnames[:n])
    if code.co_flags & 0x04:
        names.append(code.co_varnames[n])
        n += 1
    if code.co_flags & 0x08:
        names.append(code.co_varnames[n])
    loc = fr.f_locals
    out = []
    for nm in names:
        if nm not in loc:
            continue
        v = loc[nm]
        out.append(v)
        if isinstance(v, tuple) and code.co_flags & 0x04:
            out.extend(v)
        if isinstance(v, dict) and code.co_flags & 0x08:
            out.extend(v.values())
    return out


def _is_scene_set_instance(v) -> bool:
    t = type(v)
    if isinstance(v, type):
        return False
    return in_scene_set(_module_file(getattr(t, "__module__", None))) and getattr(t, "__module__", "") not in ("builtins",)


def _held(obj, frames, handed=()) -> str | None:
    """Whether a scene-set frame outside the strategy's call holds `obj`, or
    the scene set handed it to the target as (part of) an argument of the
    target function it called (`handed`): depth 4 through lists, tuples,
    sets, dict values and the attributes of scene-set objects."""
    seen: set[int] = set()
    stack = [(v, "対象に渡した引数", 0) for v in handed]
    for fr in frames:
        where = f"{_os.path.basename(fr.f_code.co_filename)}:{fr.f_code.co_name}"
        for k, v in list(fr.f_locals.items()):
            stack.append((v, f"{where}:{k}", 0))
    budget = 50_000
    while stack and budget:
        budget -= 1
        v, where, d = stack.pop()
        if v is obj:
            return where
        if d >= 4 or id(v) in seen:
            continue
        seen.add(id(v))
        if isinstance(v, (list, tuple, set, frozenset)):
            kids = list(v)[:5000]
        elif isinstance(v, dict):
            kids = list(v.values())[:5000]
        elif _is_scene_set_instance(v) and hasattr(v, "__dict__"):
            kids = list(vars(v).values())
        else:
            continue
        stack.extend((c, where, d + 1) for c in kids)
    return None


_FIRST: list = []  # (object, stack facts) at the first time the strategy recorded the object
_SCALARS = (int, float, complex, str, bytes, bool, type(None))


def _stack_facts(obj) -> dict:
    """alpha and held_by as they were the FIRST time the strategy recorded
    this object (a later record of the same object -- `of=` / `via=` after the
    strategy kept it in its own list -- reuses them: what the strategy keeps
    after receiving is not an input the adapter handed in)."""
    if isinstance(obj, _SCALARS):
        # a value has no identity to follow (small ints are shared): only who passed it, now; never "held"
        return {**_stack_facts_now(obj), "held_by": None}
    for o, f in _FIRST:
        if o is obj:
            return dict(f)
    f = _stack_facts_now(obj)
    _FIRST.append((obj, f))
    return dict(f)


def _stack_facts_now(obj) -> dict:
    """alpha (who passed `obj` into the strategy's call) and held_by, from the
    live stack at the moment the strategy recorded the object."""
    fr = _sys._getframe(1)
    while fr is not None and _real(fr.f_code.co_filename) == _HERE_FILE:
        fr = fr.f_back
    chain = []
    while fr is not None and in_scene_set(fr.f_code.co_filename):
        chain.append(fr)
        fr = fr.f_back
    segment = []
    while fr is not None and not in_scene_set(fr.f_code.co_filename):
        segment.append(fr)
        fr = fr.f_back
    outer = []
    while fr is not None:
        if in_scene_set(fr.f_code.co_filename):
            outer.append(fr)
        fr = fr.f_back
    passed = None
    called = sorted({p for p in (_real(f.f_code.co_filename) for f in segment) if p}) if chain and segment else None
    args = _args_of(chain[-1]) if chain else []
    if called and any(a is obj for a in args):
        passed = called
    # the arguments of the target function the scene set called (the outermost frame of the segment)
    handed = _args_of(segment[-1]) if segment else []
    return {"passed_by": passed, "called_by": called, "in_args": bool(called) and _reachable(obj, args),
            "held_by": _held(obj, outer, handed)}


def _reachable(obj, roots_, depth: int = 3) -> bool:
    """`obj` is one of `roots_` or inside them (items and attributes, `depth` steps)."""
    seen: set[int] = set()
    level = list(roots_)
    for _ in range(depth + 1):
        nxt = []
        for v in level:
            if v is obj:
                return True
            if id(v) in seen or isinstance(v, (str, bytes, int, float, type)):
                continue
            seen.add(id(v))
            if isinstance(v, (list, tuple, set, frozenset)):
                nxt.extend(list(v)[:2000])
            elif isinstance(v, dict):
                nxt.extend(list(v.values())[:2000])
            d = getattr(v, "__dict__", None)
            if isinstance(d, dict):
                nxt.extend(list(d.values())[:2000])
        level = nxt
    return False


_MADE: list = []  # every record made here, kept alive (identity is what run_battery checks)
_READ: list = []  # (object returned by a target function, file of that function), for `returned_by`


def _register(x):
    _MADE.append(x)
    return x


def made_here(x) -> bool:
    return any(x is m for m in _MADE)


def _object_facts(obj) -> dict:
    t = type(obj)
    out = {"type": f"{t.__module__}.{t.__qualname__}", "type_file": type_file(t)}
    if callable(obj) and not isinstance(obj, type) and (hasattr(obj, "__code__") or hasattr(obj, "__func__")):
        out["code_file"] = code_file(obj)
    base = getattr(obj, "base", None) if type(obj).__module__ == "numpy" else None  # a row of an array a read returned
    rets = [f for o, f in _READ if o is obj or (base is not None and o is base)]
    out["returned_by"] = rets[-1] if rets else None
    return out


def carrier(obj) -> Record:
    """The provenance of what the strategy received, from the object itself
    (call it at the moment the strategy receives the object)."""
    rec = Record(_object_facts(obj))
    rec.update(_stack_facts(obj))
    return _register(rec)


def carrier_tag(obj, tag) -> Record:
    """For a target that marks the type with its own tag object (an enum
    member): the object's record and the tag's class, each with its file."""
    rec = Record(_object_facts(obj))
    rec.update(_stack_facts(obj))
    tt = type(tag)
    rec["tag"] = {"type": f"{tt.__module__}.{tt.__qualname__}", "name": getattr(tag, "name", None) or repr(tag),
                  "type_file": type_file(tt)}
    return _register(rec)


def carrier_const(obj, module, name: str, value) -> Record:
    """For a target that marks the type with a plain constant (an int code):
    the constant is named by the target's module that defines it; this
    checks the module's value is the one the object carries."""
    if getattr(module, name, object()) != value:
        raise ValueError(f"{getattr(module, '__name__', module)}.{name} != {value!r}")
    rec = Record(_object_facts(obj))
    rec.update(_stack_facts(obj))
    rec["tag"] = {"const": f"{module.__name__}.{name}", "name": name, "type_file": _real(getattr(module, "__file__", None))}
    return _register(rec)


def carrier_record(obj, module, name: str, const=None) -> Record:
    """A numpy record (row) whose type is the target's record dtype `module.name`;
    `const` = (module, name, value) of the target's constant that marks the
    row's kind (checked like `carrier_const`)."""
    want = getattr(module, name)
    if getattr(obj, "dtype", None) != want:
        raise ValueError(f"dtype {getattr(obj, 'dtype', None)!r} is not {module.__name__}.{name}")
    rec = Record(_object_facts(obj))
    rec.update(_stack_facts(obj))
    rec["dtype"] = {"name": f"{module.__name__}.{name}", "type_file": _real(getattr(module, "__file__", None))}
    if const is not None:
        cm, cn, cv = const
        if getattr(cm, cn, object()) != cv:
            raise ValueError(f"{getattr(cm, '__name__', cm)}.{cn} != {cv!r}")
        rec["tag"] = {"const": f"{cm.__name__}.{cn}", "name": cn, "type_file": _real(getattr(cm, "__file__", None))}
    return _register(rec)


def compiled(name: str) -> Made:
    """A compiled tool's type / function name, as its driver's match arm or
    `%T` printed it (e.g. "go:*gobacktest.Bar"). run_battery.py checks the
    head against the target's own namespace."""
    m = Made(name)
    m.compiled = True
    return _register(m)


def carrier_tag_compiled(name: str) -> Made:  # kept name for clarity at call sites
    return compiled(name)


def qualname(fn) -> Made:
    """Module and name of the function / class that did the work (p2-iso-*:
    the target's own reader), from the object itself, with its file."""
    f = getattr(fn, "__func__", fn)
    mod = getattr(f, "__module__", None) or type(f).__module__
    name = getattr(f, "__qualname__", None) or getattr(f, "__name__", None) or type(f).__qualname__
    m = Made(f"{mod}.{name}")
    m.file = type_file(fn) if isinstance(fn, type) else code_file(fn)
    return _register(m)


def _profiled(fn):
    """Run `fn()` and return (raised exception or None, value, files of the code that ran)."""
    files: set = set()

    def prof(frame, event, arg):
        if event == "call":
            files.add(frame.f_code.co_filename)
            if "jitclass" in frame.f_code.co_filename:  # numba's box wrapper: placed by the jitclass it wraps
                for v in list(frame.f_locals.values()):
                    for x in (v if isinstance(v, tuple) else (v,)):
                        if _numba_class_type(type(x)) is not None:
                            files.add(type_file(type(x)) or "")
        elif event == "c_call":
            files.add(code_file(arg) or "")

    prev = _sys.getprofile()
    _sys.setprofile(prof)
    try:
        v = fn()
        exc = None
    except Exception as e:  # noqa: BLE001 - returned to the caller
        v, exc = None, e
    finally:
        _sys.setprofile(prev)
    touched = sorted({p for p in (_real(f) for f in files) if p and not in_scene_set(p)})
    return exc, v, touched


def read(fn, *args, **kwargs):
    """A read the strategy makes through a target function `fn`: the object it
    returns (and the items of a returned tuple / list) are recorded, so a
    `carrier` of them shows `returned_by` = the file of `fn`."""
    exc, v, _ = _profiled(lambda: fn(*args, **kwargs))
    if exc is not None:
        raise exc
    f = code_file(fn)
    _READ.append((v, f))
    if isinstance(v, (tuple, list)) and len(v) <= 16:
        for x in v:
            _READ.append((x, f))
    return v


def _raise_site(exc) -> dict:
    """Where the exception was raised: the innermost frame's file and whether
    it was a `raise` statement of the scene set (an adapter stopping itself)."""
    tb = exc.__traceback__
    if tb is None:
        return {"raised_file": None, "raised_by_scene_set_raise": False}
    while tb.tb_next is not None:
        tb = tb.tb_next
    code = tb.tb_frame.f_code
    op = None
    try:
        import dis
        for ins in dis.get_instructions(code):
            if ins.offset == tb.tb_lasti:
                op = ins.opname
                break
    except Exception:  # noqa: BLE001
        op = None
    f = code.co_filename
    return {"raised_file": _real(f) or f,
            "raised_by_scene_set_raise": bool(in_scene_set(f) and op in ("RAISE_VARARGS", "RERAISE"))}


class Reads:
    """p4-visible-at-step (round r6-1): each read the strategy makes at the
    probe call through a public means of the target, with the closes it
    returned. The output's count and maximum are made from these reads (the
    runner checks they agree); a list the strategy kept itself is not a read
    of the target.

    Round r6-2: each read also records the files of the code that ran while
    it was made (`touched`), and `of` = the provenance of the target object
    it reads from (a `carrier` record, or a compiled driver's `compiled`
    name). run_battery.py grades a read only when one of them belongs to the
    target."""

    def __init__(self) -> None:
        self.items: list[dict] = []

    def read(self, means: str, fn, of=None) -> None:
        exc, raw, touched = _profiled(fn)
        if exc is not None:
            raise exc
        vals = [float(x) for x in raw]
        if of is not None and not (isinstance(of, (Record, Made)) and made_here(of)):
            of = carrier(of)
        self.items.append(_register(Record({"means": means, "returned": vals, "touched": touched, "of": of})))

    def output(self) -> dict:
        counts = sorted({len(r["returned"]) for r in self.items})
        closes = [x for r in self.items for x in r["returned"]]
        return {"visible_count": counts[0] if len(counts) == 1 else counts,
                "max_visible_close": max(closes) if closes else None}

    def provenance(self) -> dict:
        return {"reads": list(self.items)}
