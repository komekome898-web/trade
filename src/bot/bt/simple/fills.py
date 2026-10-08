"""注文の形と約定の決まり(SPEC.md §3): 注文 1 つの状態、形の検め、今いる値段で約定するかの判定。

道筋のたどり方(どの点で止まり、どの値段・case で約定させるか)は run.py。
"""
from __future__ import annotations

from .common import SIDES, SimpleRoadError, floor_tick, is_number, step_ok

FORMS = ("limit", "stop", "market")
KEYS = ("form", "side", "qty", "px", "tag")  # 注文の辞書に置ける鍵(SPEC.md §2.2。ほかの鍵は止める)


class Order:
    """出ている注文 1 つ。key は同じ番号の比べに使う中身(形・売買・量・戦略が出した値段そのもの・tag)。"""

    __slots__ = ("seq", "id", "form", "side", "qty", "px", "tag", "key", "up")

    def __init__(self, seq: int, oid: str, raw: dict, tick: float):
        self.seq, self.id = seq, oid
        self.form, self.side, self.qty = raw["form"], raw["side"], float(raw["qty"])
        self.tag = raw.get("tag")
        self.key = (self.form, self.side, self.qty, raw.get("px"), self.tag)
        self.px = None  # 刻みに切り捨てた値段(market は無し)
        if self.form != "market":
            self.px = floor_tick(raw["px"], tick)
            if self.px <= 0:
                raise SimpleRoadError(f"注文 {oid} の切り捨てた値段が 0 以下")
        # 道筋が上へ動いて届く注文(売りの limit・買いの stop)か、下へ動いて届く注文(買いの limit・売りの stop)か
        self.up = (self.form == "limit") == (self.side == "sell")

    def kind(self) -> str:
        """約定のファイルの kind(SPEC.md §4): tag、無ければ形の名前。"""
        return self.form if self.tag is None else self.tag

    def fills_at(self, price: float) -> bool:
        """今いる値段で約定する側にいるか(ちょうど同じ値段を含む。SPEC.md §3)。"""
        if self.form == "market":
            return True
        return price >= self.px if self.up else price <= self.px


def check_shape(oid, o) -> None:
    """注文 1 つの形の検め(SPEC.md §2.2・§3 の止める注文)。"""
    if not isinstance(oid, str) or not oid:
        raise SimpleRoadError(f"注文の番号は空でない文字: {oid!r}")
    if not isinstance(o, dict):
        raise SimpleRoadError(f"注文 {oid} は辞書で返す")
    extra = [k for k in o if k not in KEYS]
    if extra:
        raise SimpleRoadError(f"注文 {oid} に知らない鍵がある: {extra!r}")
    f = o.get("form")
    if f not in FORMS:
        raise SimpleRoadError(f"注文 {oid} の形が知らない形: {f!r}")
    if o.get("side") not in SIDES:
        raise SimpleRoadError(f"注文 {oid} の売買は buy / sell: {o.get('side')!r}")
    q = o.get("qty")
    if not is_number(q) or not step_ok(q):
        raise SimpleRoadError(f"注文 {oid} の量は 0 より大きく 0.001 の刻みの上: {q!r}")
    if f == "market":
        if "px" in o:
            raise SimpleRoadError(f"注文 {oid}(成行)に値段がある")
    elif not (is_number(o.get("px")) and o["px"] > 0):
        raise SimpleRoadError(f"注文 {oid}({f})の値段は 0 より大きい数: {o.get('px')!r}")
    if "tag" in o and not isinstance(o["tag"], str):
        raise SimpleRoadError(f"注文 {oid} の tag は文字: {o['tag']!r}")
