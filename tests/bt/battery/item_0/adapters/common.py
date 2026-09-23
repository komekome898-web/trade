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
