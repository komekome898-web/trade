"""約定の関数(SPEC.md §3): 1 本の足について、出ている注文と足から約定を返す。"""
from __future__ import annotations

from decimal import Decimal

from .common import floor_tick

# 1 本の足の中で約定させ記す順(SPEC.md §3): ⓪ 前からの建玉を閉じる注文のうち始値で約定するもの ① 成行
# ② 前からの建玉を閉じる注文のうち範囲の内で約定するもの ③ 指値(close の印の無いもの) ④ 段 ⑤ 親がこの足で約定した利確
# 前からの建玉を閉じる注文 = 親が前の足までに約定した利確と、close の印の付いた指値
RANK_CLOSE_OPEN, RANK_MARKET, RANK_CLOSE_RANGE, RANK_LIMIT, RANK_LEVEL, RANK_EXIT_SAME_BAR = range(6)


class Order:
    """出ている注文 1 つの状態。raw は戦略が出した中身(同じ番号の比べに使う)。"""

    def __init__(self, seq: int, oid: str, raw: dict):
        self.seq, self.id = seq, oid
        self.form, self.side, self.qty = raw["form"], raw["side"], float(raw["qty"])
        self.px_calc = float(raw["px"]) if "px" in raw and self.form in ("limit", "exit") else None
        self.root = raw.get("root") if self.form == "level" else None
        self.offset = float(raw["offset"]) if self.form == "level" else None
        self.parent = raw.get("parent") if self.form == "exit" else None
        self.close = self.form == "limit" and raw.get("close") is True  # 建玉を閉じる指値の印(run が形を検めてから作る)
        self.px: float | None = None  # 切り捨てた値段(level は根が約定した時に決まる)
        self.state = "live"  # live / filled / gone
        self.fill_ts: str | None = None
        self.fill_px: float | None = None
        self.first_ts: str | None = None  # 約定しうる最初の足
        self.last_ts: str | None = None  # 約定しうる最後の足(今までに出ていた最後の足)
        self.case: str | None = None  # 約定の行の case
        self.root_order: "Order | None" = None  # level の根(run が結ぶ)
        self.parent_order: "Order | None" = None  # exit の親(run が結ぶ)

    def key(self) -> tuple:
        """同じ番号の比べ: 形・売買・量・戦略が出した値段そのもの・根・距離・親・close の印。"""
        return (self.form, self.side, self.qty, self.px_calc, self.root, self.offset, self.parent, self.close)


def _limit_rule(o: Order, px: float, bar):
    """limit と同じ決まり: 範囲の内なら値段で(range)、約定する向きに範囲の外なら始値で(open)。"""
    _, op, hi, lo, _, _ = bar
    if lo <= px <= hi:
        return px, "range"
    if (o.side == "buy" and px > hi) or (o.side == "sell" and px < lo):
        return op, "open"
    return None


def _close_rank(o: Order, bar) -> int:
    """前からの建玉を閉じる注文の組: 約定値段が始値(始値で約定、または切り捨てた後の値段が始値ちょうど)なら ⓪、範囲の内なら ②。"""
    res = _limit_rule(o, o.px, bar)
    return RANK_CLOSE_OPEN if res is not None and res[0] == bar[1] else RANK_CLOSE_RANGE


def _rank(o: Order, bar) -> int:
    """足に入る時点の状態と足から決める組の番号(足の中で約定した注文の状態では決めない)。"""
    if o.form == "market":
        return RANK_MARKET
    if o.form == "limit":
        return _close_rank(o, bar) if o.close else RANK_LIMIT
    if o.form == "level":
        return RANK_LEVEL
    return _close_rank(o, bar) if o.parent_order.state == "filled" else RANK_EXIT_SAME_BAR


def fill_bar(live: list, bar, side: str, tick: float) -> list:
    """live(出ている注文)を bar で約定させ、約定した注文を約定させた順に返す(注文の状態も更新する)。

    side: optimistic(親が約定した足で付けた利確を試す)/ pessimistic(試さない)。
    """
    ts, op, hi, lo, _, _ = bar
    filled = []
    for o in sorted(live, key=lambda x: (_rank(x, bar), x.seq)):  # sorted は全部の鍵を先に作るので、組は足に入る時点の状態で決まる
        res = None
        if o.form == "market":
            res = (op, "market")
        elif o.form == "limit":
            res = _limit_rule(o, o.px, bar)
        elif o.form == "level":
            root = o.root_order
            if root.state == "filled" and o.px is not None:
                if root.fill_ts == ts:  # 根が約定した足: 段の値段が範囲の内なら段の値段で
                    res = (o.px, "anchor_bar") if lo <= o.px <= hi else None
                else:
                    res = _limit_rule(o, o.px, bar)
        else:  # exit
            par = o.parent_order
            if par.state == "filled":
                if par.fill_ts == ts:  # 親が約定した足: 良い側だけ、値段が範囲の内なら値段で。始値では約定しない
                    res = (o.px, "entry_bar") if side == "optimistic" and lo <= o.px <= hi else None
                else:
                    res = _limit_rule(o, o.px, bar)
        if res is None:
            continue
        o.state, o.fill_ts, o.fill_px = "filled", ts, res[0]
        o.case = res[1]
        if o.form == "limit":
            for lv in live:  # この根を持つ段の値段が決まる(戦略の値段ではなく約定値段 F から。L-816「1.a」)
                if lv.form == "level" and lv.root_order is o and lv.state == "live":
                    lv.px = floor_tick(Decimal(repr(res[0])) + Decimal(repr(lv.offset)), tick)
        filled.append(o)
    return filled
