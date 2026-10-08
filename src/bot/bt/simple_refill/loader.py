"""走らせが書いた記録(`run_<側>.json`・`orders_<側>.csv`)を読む。

読めない・形の違うものは例外にせず、食い違いの文を `issues`(文の並び)に足して None を返す。
"""
from __future__ import annotations

import csv
import io
import json
import math
import os
from datetime import datetime, timezone

SIDES = ("optimistic", "pessimistic")
FORMS = ("limit", "level", "exit", "market")
ORDER_COLS = ["seq", "id", "form", "side", "qty", "px_calc", "px", "root", "offset", "parent", "from_ts", "to_ts"]
FILLS_COLS = ["ts", "id", "side", "qty", "px", "case"]


class Issues:
    """食い違いの文の入れ物。多すぎるときは先頭の `limit` 件だけ持ち、残りは数だけ数える。"""

    def __init__(self, limit: int = 100):
        self.items: list[str] = []
        self.omitted = 0
        self.limit = limit

    def add(self, text: str) -> None:
        if len(self.items) < self.limit:
            self.items.append(text)
        else:
            self.omitted += 1

    def result(self) -> list[str]:
        out = list(self.items)
        if self.omitted:
            out.append(f"食い違いの文が多いため、先頭の {self.limit} 件より後の {self.omitted} 件は省いた。")
        return out


class Order:
    """注文の記録の 1 行と、作り直しの途中の状態。"""

    __slots__ = ("seq", "id", "form", "side", "qty", "px_calc", "px_text", "root", "offset", "parent",
                 "from_ts", "to_ts", "root_order", "parent_order",
                 "fixed_px", "fill_ts", "fill_px", "activated", "ended", "bad")

    def __init__(self):
        self.root_order = self.parent_order = None
        self.fixed_px = None      # 段: 根が約定した足で決まった段の値段
        self.fill_ts = None       # 作り直しで約定した足の始まり
        self.fill_px = None       # 作り直しで約定した値段
        self.activated = False    # from_ts の足に来たか
        self.ended = False        # activated になった後に to_ts の足に来たか
        self.bad = False          # 記録の形が違い、約定を試さない注文


def read_text(path: str) -> str:
    """UTF-8 として厳密に読む(行の終わりは変えない)。"""
    with open(path, "rb") as fh:
        return fh.read().decode("utf-8")


def parse_instant(text: str) -> datetime:
    """足の始まり・封印の境の時刻の文字列を、時刻(タイムゾーン付き)にする。付いていなければ UTC とみなす。"""
    dt = datetime.fromisoformat(text)
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def _finite(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def load_run(out_dir: str, side: str, issues: Issues):
    """`run_<側>.json` から (刻み tick, 封印の境 seal の時刻) を取り出す。側が違えば食い違い。"""
    path = os.path.join(out_dir, f"run_{side}.json")
    try:
        rec = json.loads(read_text(path))
    except (OSError, ValueError) as e:  # 見つからない・UTF-8 でない・JSON でない(UnicodeDecodeError は ValueError の一種)
        issues.add(f"{os.path.basename(path)} を読めない: {type(e).__name__}。")
        return None
    if not isinstance(rec, dict):
        issues.add(f"{os.path.basename(path)} の中身が辞書でない。")
        return None
    ok = True
    if rec.get("side") != side:
        issues.add(f"{os.path.basename(path)} の側 side が {rec.get('side')!r} で、呼んだ側 {side!r} と違う。")
        ok = False
    tick = rec.get("tick")
    if not _finite(tick) or tick <= 0:
        issues.add(f"{os.path.basename(path)} の刻み tick が正の数でない: {tick!r}。")
        ok = False
    seal = rec.get("seal")
    seal_dt = None
    if not isinstance(seal, str):
        issues.add(f"{os.path.basename(path)} の封印の境 seal が文字でない: {seal!r}。")
        ok = False
    else:
        try:
            seal_dt = parse_instant(seal)
        except ValueError:
            issues.add(f"{os.path.basename(path)} の封印の境 seal が時刻として読めない: {seal!r}。")
            ok = False
    return (float(tick), seal_dt) if ok else None


def _opt_float(text: str):
    """空なら None、数なら float。数でなければ ValueError。"""
    if text == "":
        return None
    v = float(text)
    if not math.isfinite(v):
        raise ValueError(text)
    return v


def load_orders(out_dir: str, side: str, issues: Issues):
    """`orders_<側>.csv` を読み、seq の順の注文の並びを返す。形が違えば食い違いを足して None。"""
    name = f"orders_{side}.csv"
    try:
        text = read_text(os.path.join(out_dir, name))
        rows = list(csv.reader(io.StringIO(text, newline="")))
    except (OSError, ValueError, csv.Error) as e:
        issues.add(f"{name} を読めない: {type(e).__name__}。")
        return None
    if not rows or rows[0] != ORDER_COLS:
        issues.add(f"{name} の見出しの行が決まった列 {','.join(ORDER_COLS)} と違う。")
        return None
    orders: list[Order] = []
    seen_ids, seen_seq = set(), set()
    for n, row in enumerate(rows[1:], start=2):
        if len(row) != len(ORDER_COLS):
            issues.add(f"{name} の {n} 行目の欄の数が {len(row)} で、見出しの {len(ORDER_COLS)} と違う。")
            continue
        r = dict(zip(ORDER_COLS, row))
        od = Order()
        col = "seq"
        try:
            if not (r["seq"].isascii() and r["seq"].isdigit()):
                raise ValueError
            od.seq = int(r["seq"])
            col = "form"
            od.id, od.form, od.side = r["id"], r["form"], r["side"]
            if od.form not in FORMS:
                raise ValueError
            col = "side"
            if od.side not in ("buy", "sell"):
                raise ValueError
            col = "qty"
            od.qty = float(r["qty"])
            if not (math.isfinite(od.qty) and od.qty > 0):
                raise ValueError
            col = "px_calc"
            od.px_calc = _opt_float(r["px_calc"])
            od.px_text = r["px"]
            col = "offset"
            od.offset = _opt_float(r["offset"])
            od.root, od.parent = r["root"], r["parent"]
            od.from_ts, od.to_ts = r["from_ts"], r["to_ts"]
            col = "px_calc"
            if od.form in ("limit", "exit") and od.px_calc is None:
                raise ValueError
            col = "root/offset"
            if od.form == "level" and (od.offset is None or od.root == ""):
                raise ValueError
            col = "parent"
            if od.form == "exit" and od.parent == "":
                raise ValueError
            col = "from_ts/to_ts"
            if (od.from_ts == "") != (od.to_ts == ""):
                raise ValueError
        except ValueError:
            issues.add(f"{name} の {n} 行目(id {r['id']!r})の欄 {col} の形が違う。")
            continue
        if od.id in seen_ids:
            issues.add(f"{name} の {n} 行目: id {od.id!r} が重なっている。")
            continue
        if od.seq in seen_seq:
            issues.add(f"{name} の {n} 行目: seq {od.seq} が重なっている。")
            continue
        seen_ids.add(od.id)
        seen_seq.add(od.seq)
        orders.append(od)
    if len(orders) != len(rows) - 1:
        return None  # 形の違う行がある。食い違いは文にしてある
    orders.sort(key=lambda o: o.seq)
    return orders
