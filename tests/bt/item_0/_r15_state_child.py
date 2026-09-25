"""Child program of test_bt0_r15_library_code.py (round 15): ONE change of
process-wide state, made by a strategy inside its own call, then the
workload (_r15_workload.py) run again in the same process. Prints JSON.

    python _r15_state_child.py fresh
    python _r15_state_child.py <change>

`fresh` -> {"run": summary, "flags": [decimal flags the run set]}.
`<change>` -> {"run_a": the run whose strategy makes the change in its first
on_event (and, for a module swapped in sys.modules, puts it back in its
second), "run_b": a clean run after it in the same process, "in_core": code
of the changer's that ran with the core as the nearest non-library caller}.

The parent runs every child with PYTHONHASHSEED=0 so the str hashes -- and
with them the colliding keys of the workload -- are the same in every child.
"""
from __future__ import annotations

import abc
import ast
import collections.abc
import decimal
import glob
import json
import numbers
import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import numpy as np  # noqa: E402

import _r15_workload as W  # noqa: E402
from bot.bt.core import values as V  # noqa: E402

CORE_DIR = os.path.dirname(os.path.abspath(V.__file__)) + os.sep
PARTIES = {os.path.abspath(W.__file__), os.path.abspath(__file__)}
IN_CORE: list = []
KEEP: list = []


def _caller_is_core(frame) -> bool:
    """Is the nearest frame below `frame` that is not library code the
    core's (not a party's)?"""
    f = frame
    while f is not None:
        fn = os.path.abspath(f.f_code.co_filename) if not f.f_code.co_filename.startswith("<") else f.f_code.co_filename
        if fn.startswith(CORE_DIR) or fn.startswith("<bot.bt.core"):
            return True
        if fn in PARTIES:
            return False
        f = f.f_back
    return False


def _note(what: str) -> None:
    if _caller_is_core(sys._getframe(2)):
        IN_CORE.append(what)


# ---- the changes ----------------------------------------------------------------------

def abcs() -> list:
    """Every ABC of `numbers` and `collections.abc` (read from the modules)."""
    out = []
    for mod in (numbers, collections.abc):
        for name in sorted(getattr(mod, "__all__", dir(mod))):
            if isinstance(getattr(mod, name, None), abc.ABCMeta):
                out.append(f"{mod.__name__}.{name}")
    return out


def core_modules() -> list:
    """Every module the core's files import (read from their source)."""
    names = set()
    for path in glob.glob(os.path.join(CORE_DIR, "*.py")):
        for node in ast.walk(ast.parse(open(path, encoding="utf-8").read())):
            if isinstance(node, ast.Import):
                names.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module != "__future__":
                names.add(node.module)
    return sorted(names)


DECIMAL = ["prec1", "floor3", "notraps", "alltraps", "capitals0", "emax"]
CHANGES = ([f"register:{a}" for a in abcs()] + [f"hook:{a}" for a in abcs()]
           + [f"decimal:{d}" for d in DECIMAL]
           + [f"sys_modules:{m}" for m in core_modules()]
           + ["warnings:error", "numpy_seterr:raise"])


def _every_type() -> list:
    """Every type the workload hands over (read from its values) and the
    core's own classes."""
    seen: dict = {}

    def walk(v):
        seen[id(type(v))] = type(v)
        if isinstance(v, dict):
            for k, x in v.items():
                walk(k)
                walk(x)
        elif isinstance(v, (list, tuple, set, frozenset)):
            for x in v:
                walk(x)

    walk(W.EXTRA)
    for _label, a, b in W.colliding_pairs():
        walk(a)
        walk(b)
    for name in ("PlainFraction", "PlainDecimal", "FrozenList", "FrozenDict", "FrozenSet"):
        if hasattr(V, name):
            seen[id(getattr(V, name))] = getattr(V, name)
    return sorted(seen.values(), key=lambda t: (t.__module__, t.__qualname__))


def _resolve(dotted: str):
    mod, _, name = dotted.rpartition(".")
    return getattr(sys.modules[mod], name)


def _swap_module(name: str):
    """A module of the changer's in sys.modules[name]: the real module's
    names, every callable wrapped to note a call whose nearest non-library
    caller is the core."""
    real = sys.modules.get(name)
    if real is None:
        __import__(name)
        real = sys.modules[name]
    fake = types.ModuleType(name)
    for k, v in vars(real).items():
        if callable(v) and not isinstance(v, type):
            def wrapped(*a, _v=v, _k=k, **kw):
                _note(f"sys.modules[{name!r}].{_k}")
                return _v(*a, **kw)
            setattr(fake, k, wrapped)
        else:
            setattr(fake, k, v)

    def change():
        sys.modules[name] = fake

    def restore():
        sys.modules[name] = real

    return change, restore


def make(change: str):
    """(change, restore) callables for a strategy's first and second on_event."""
    kind, _, arg = change.partition(":")
    if kind == "sys_modules":
        return _swap_module(arg)

    def do():
        if kind == "register":
            a = _resolve(arg)
            for t in _every_type():
                try:
                    a.register(t)
                except (TypeError, RuntimeError):  # a cycle, or a class the ABC refuses
                    pass
        elif kind == "hook":
            a = _resolve(arg)

            def sub(cls, other):
                _note(f"__subclasscheck__({arg})")
                return True

            def inst(cls, obj):
                _note(f"__instancecheck__({arg})")
                return True

            meta = type("M", (type(a),), {"__subclasscheck__": sub, "__instancecheck__": inst})
            KEEP.append(meta("Evil", (a,), {}))
            # clear every ABC's negative cache with a registration outside every hierarchy
            KEEP.append(abc.ABCMeta("Bump", (), {}))
            KEEP[-1].register(type("Fresh", (), {}))
        elif kind == "decimal":
            ctx = decimal.getcontext()
            if arg == "prec1":
                ctx.prec = 1
            elif arg == "floor3":
                ctx.prec, ctx.rounding = 3, decimal.ROUND_FLOOR
            elif arg == "notraps":
                for s in list(ctx.traps):
                    ctx.traps[s] = False
            elif arg == "alltraps":
                for s in list(ctx.traps):
                    ctx.traps[s] = True
            elif arg == "capitals0":
                ctx.capitals = 0
            elif arg == "emax":
                ctx.Emax, ctx.Emin = 5, -5
        elif kind == "warnings":
            import warnings

            warnings.simplefilter(arg)
        elif kind == "numpy_seterr":
            np.seterr(all=arg)
        else:
            raise SystemExit(f"unknown change {change}")

    return do, None


def _flags() -> list:
    return sorted(s.__name__ for s, on in decimal.getcontext().flags.items() if on)


def main(mode: str) -> dict:
    if mode == "fresh":
        decimal.getcontext().clear_flags()
        run = W.run()
        sent = dict(W.EXTRA)
        return {"run": run, "flags": _flags(),
                "sent": {"colliding_dict": len(sent["colliding_dict"]),
                         "colliding_frozenset": len(sent["colliding_frozenset"])}}
    change, restore = make(mode)
    run_a = W.run(change, restore)
    run_b = W.run()
    return {"run_a": run_a, "run_b": run_b, "in_core": IN_CORE}


if __name__ == "__main__":
    if sys.argv[1] == "--list":
        print(json.dumps(CHANGES))
    else:
        print(json.dumps(main(sys.argv[1]), default=repr))
