"""単純な測りの道の共通の部品(止める場面の型・時刻・数の書き方・刻みへの切り捨て)。決まりの正本は SPEC.md。"""
from __future__ import annotations

import math
import re
from datetime import datetime, timedelta, timezone
from decimal import ROUND_FLOOR, Decimal

_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
STEP_QTY = Decimal("0.001")  # 量の刻み(L-756「3. 0.001」)
SIDES = ("buy", "sell")


class SimpleRoadError(Exception):
    """単純な測りの道が先へ進めない場面(文は日本語)。"""


def parse_ts(s: str) -> datetime:
    """足のファイルの ts(ISO 8601)を UTC の時刻に。"""
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00") if isinstance(s, str) else s)
    except (TypeError, ValueError):
        raise SimpleRoadError(f"時刻を読めない: {s!r}") from None
    if d.tzinfo is None:
        raise SimpleRoadError(f"時刻に UTC の印が無い: {s!r}")
    return d.astimezone(timezone.utc)


def to_ns(s: str) -> int:
    """足の始まりの時刻の文字列を UTC の ns(整数)に。"""
    return ((parse_ts(s) - _EPOCH) // timedelta(microseconds=1)) * 1000


def num(x) -> str:
    """数の書き方: repr(float(x))(SPEC.md §4)。"""
    return repr(float(x))


def cell(v) -> str:
    """表の欄の文字列(None は空)。書くときも比べるときも同じ関数を使う。"""
    return "" if v is None else str(v)


def is_number(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def floor_tick(v: float | Decimal, tick: float) -> float:
    """刻みに切り捨てる(SPEC.md §3: Decimal(repr(値段)) / Decimal(repr(刻み)) を ROUND_FLOOR で整数にして刻みを掛ける)。"""
    d = v if isinstance(v, Decimal) else Decimal(repr(float(v)))
    t = Decimal(repr(float(tick)))
    return float(((d / t).to_integral_value(rounding=ROUND_FLOOR)) * t)


def step_ok(qty: float) -> bool:
    return qty > 0 and Decimal(repr(float(qty))) % STEP_QTY == 0


_YEAR = re.compile(r"_(\d{4})\.csv\.gz$")


def file_year(path: str) -> int | None:
    m = _YEAR.search(str(path))
    return int(m.group(1)) if m else None
