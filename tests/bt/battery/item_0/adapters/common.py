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
      no_means     the target hands the strategy no read that takes a time
                   or a position: the call a strategy would write, written
                   and called as it is; graded like any named read (a value
                   returned is a read that was not stopped)
      other        a read that does not name the future bar
    """

    def __init__(self) -> None:
        self.items: list[dict] = []

    def _raised(self, means: str, form: str, exc: BaseException, shape, naming) -> None:
        import re
        # memory addresses in messages differ between runs and would read as "2 回で違う"
        msg = re.sub(r"0x[0-9a-fA-F]+", "0x…", str(exc))[:160]
        self.items.append({"means": means, "form": form, "shape": shape, "naming": naming,
                           "raised": type(exc).__name__, "message": msg, "returned": None})

    @staticmethod
    def _shape(form: str, shape):
        if shape is not None:
            return shape
        return "other" if form == "other" else None  # a named read without a shape is refused by the runner

    def run(self, means: str, form: str, fn, shape=None, naming=None) -> None:
        shape = self._shape(form, shape)
        naming = naming if naming is not None else ("other" if shape == "other" else None)
        try:
            v = fn()
        except Exception as exc:  # noqa: BLE001 - the exception IS the observation
            self._raised(means, form, exc, shape, naming)
            return
        self.items.append({"means": means, "form": form, "shape": shape, "naming": naming,
                           "raised": None, "returned": plain(v)})

    async def run_async(self, means: str, form: str, make_coro, shape=None, naming=None) -> None:
        shape = self._shape(form, shape)
        naming = naming if naming is not None else ("other" if shape == "other" else None)
        try:
            v = await make_coro()
        except Exception as exc:  # noqa: BLE001
            self._raised(means, form, exc, shape, naming)
            return
        self.items.append({"means": means, "form": form, "shape": shape, "naming": naming,
                           "raised": None, "returned": plain(v)})

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


def try_position_namings(att: Attempts, means: str, seq_fn, n: int, get=None) -> None:
    """Every position naming of scenes.POSITION_NAMINGS on the read `seq_fn()`
    (re-read for each naming), with `n` = the position right after the newest
    delivered event in the target's own way of counting; `get` turns an
    item of the read into its close (for the runner's look for 104)."""
    for naming in _namings()[0]:
        key = _position_key(naming, n)
        att.run(means, "position", lambda key=key: values_of(seq_fn()[key], get), shape="position", naming=naming)


def _time_args(shape: str, naming: str, sc, to_t):
    _, times, day = _namings()
    first = int(sc.input["events"][0]["ts_ns"])
    fut = int(sc.input["future_ts_ns"])
    now = int(sc.input["probe_at_ns"])
    return {"at(fut)": (fut,), "until(fut)": (fut,), "until(fut+1d)": (fut + day,),
            "since(fut)": (fut,), "since(now+1ns)": (now + 1,),
            "range(first,fut)": (first, fut), "range(fut,fut)": (fut, fut),
            "range(now+1ns,fut+1d)": (now + 1, fut + day)}[naming]


def try_time_namings(att: Attempts, means: str, shape: str, read, sc, to_t=lambda ns: ns) -> None:
    """Every time naming of scenes.TIME_NAMINGS[shape] through `read(*times)`,
    each time converted by `to_t` (the target's time type)."""
    for naming in _namings()[1][shape]:
        args = tuple(to_t(t) for t in _time_args(shape, naming, sc, to_t))
        att.run(means, "time", lambda args=args: read(*args), shape=shape, naming=naming)


async def try_time_namings_async(att: Attempts, means: str, shape: str, read, sc, to_t=lambda ns: ns) -> None:
    for naming in _namings()[1][shape]:
        args = tuple(to_t(t) for t in _time_args(shape, naming, sc, to_t))
        await att.run_async(means, "time", lambda args=args: read(*args), shape=shape, naming=naming)


# ---------------------------------------------------------------- provenance
def carrier(obj) -> str:
    """The class of what the strategy received, from the object itself."""
    t = type(obj)
    return f"{t.__module__}.{t.__qualname__}"


def carrier_tag(obj, tag) -> str:
    """For a target that marks the type with its own tag object (an enum
    member, a flag constant): the object's class and the tag's own class and
    name, both read from the objects."""
    tt = type(tag)
    name = getattr(tag, "name", None) or repr(tag)
    return f"{carrier(obj)}[{tt.__module__}.{tt.__qualname__}.{name}]"


def qualname(fn) -> str:
    """Module and name of the function / class that did the work (p2-iso-*: the
    target's own reader), from the object itself."""
    f = getattr(fn, "__func__", fn)
    mod = getattr(f, "__module__", None) or type(f).__module__
    name = getattr(f, "__qualname__", None) or getattr(f, "__name__", None) or type(f).__qualname__
    return f"{mod}.{name}"


class Reads:
    """p4-visible-at-step (round r6-1): each read the strategy makes at the
    probe call through a public means of the target, with the closes it
    returned. The output's count and maximum are made from these reads (the
    runner checks they agree); a list the strategy kept itself is not a read
    of the target."""

    def __init__(self) -> None:
        self.items: list[dict] = []

    def read(self, means: str, fn) -> None:
        vals = [float(x) for x in fn()]
        self.items.append({"means": means, "returned": vals})

    def output(self) -> dict:
        counts = sorted({len(r["returned"]) for r in self.items})
        closes = [x for r in self.items for x in r["returned"]]
        return {"visible_count": counts[0] if len(counts) == 1 else counts,
                "max_visible_close": max(closes) if closes else None}

    def provenance(self) -> dict:
        return {"reads": list(self.items)}
