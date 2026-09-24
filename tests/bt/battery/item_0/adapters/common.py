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
    runner grades; this class only records."""

    def __init__(self) -> None:
        self.items: list[dict] = []

    def _raised(self, means: str, form: str, exc: BaseException) -> None:
        import re
        # memory addresses in messages differ between runs and would read as "2 回で違う"
        msg = re.sub(r"0x[0-9a-fA-F]+", "0x…", str(exc))[:160]
        self.items.append({"means": means, "form": form, "raised": type(exc).__name__,
                           "message": msg, "returned": None})

    def run(self, means: str, form: str, fn) -> None:
        try:
            v = fn()
        except Exception as exc:  # noqa: BLE001 - the exception IS the observation
            self._raised(means, form, exc)
            return
        self.items.append({"means": means, "form": form, "raised": None, "returned": plain(v)})

    async def run_async(self, means: str, form: str, make_coro) -> None:
        try:
            v = await make_coro()
        except Exception as exc:  # noqa: BLE001
            self._raised(means, form, exc)
            return
        self.items.append({"means": means, "form": form, "raised": None, "returned": plain(v)})

    def output(self) -> dict:
        return {"attempts": list(self.items)}

    def summary(self) -> str:
        out = []
        for a in self.items:
            got = f"{a['raised']}: {a['message']}" if a["raised"] else f"-> {str(a['returned'])[:120]}"
            out.append(f"[{a['form']}] {a['means']} {got}")
        return " ; ".join(out)


# ---------------------------------------------------------------- P0-5 rules
def stated_rule(source: str, quote: str, predicted: list) -> dict:
    """The target's own written rule for same-time order (P0-5), where it is
    written and its hand application to the scene's input. Written from the
    target's documents or public code, never from running it."""
    return {"source": source, "quote": quote, "predicted": [[str(k), int(t)] for k, t in predicted]}


def tie_events_in_hand_over(scene, order: list[str] | None = None) -> list[list]:
    """(kind, ts) of the P0-5 streams concatenated in hand-over order."""
    return [[e["kind"], int(e["ts_ns"])] for e in concatenated(scene, order)]
