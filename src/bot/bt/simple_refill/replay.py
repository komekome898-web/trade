"""約定の作り直し本体(検査 1)。

走らせの注文の記録(`orders_<側>.csv`)と、足を 1 回だけ前から読んで、約定を計算し直し、
`fills_<側>.csv` と 1 字違わず同じかを比べる。足は 1 本ごとに使い捨てる(足の全部を記憶に持たない)。
注文の記録と、作り直した約定は記憶に持つ。
"""
from __future__ import annotations

import csv
import io
import math
import os
from operator import attrgetter

from .loader import FILLS_COLS, SIDES, Issues, load_orders, load_run, parse_instant, read_text
from .rules import inside_fill, level_price, limit_fill, limit_price

_BY_SEQ = attrgetter("seq")


class _Stop(Exception):
    """これ以上続けても意味がない入力(足の形が違うなど)。文を持って作り直しを止める。"""


def refill(bars, out_dir, side):
    """約定を計算し直して `fills_<側>.csv` と比べる。食い違いの文(日本語)の並びを返し、同じなら空。

    bars: 走らせに渡したのと同じ足の並び(生成器でもよい)。1 本ずつ (足の始まりの時刻の文字列, 始値, 高値, 安値, 終値, 出来高)。
    読めない・形の違う入力は例外にせず、食い違いの文で返す。
    """
    issues = Issues()
    try:
        _refill(bars, out_dir, side, issues)
    except _Stop as e:
        issues.add(str(e))
    except Exception as e:  # どんな入力でも例外にせず、食い違いの文で返す
        issues.add(f"作り直しの途中で想定外の入力に当たった({type(e).__name__})。")
    return issues.result()


def _refill(bars, out_dir, side, issues: Issues) -> None:
    if side not in SIDES:
        issues.add(f"側 {side!r} は optimistic でも pessimistic でもない。")
        return
    out_dir = os.fspath(out_dir)
    run = load_run(out_dir, side, issues)
    orders = load_orders(out_dir, side, issues)
    fills_name = f"fills_{side}.csv"
    try:
        actual = read_text(os.path.join(out_dir, fills_name))
    except (OSError, ValueError) as e:
        issues.add(f"{fills_name} を読めない: {type(e).__name__}。")
        actual = None
    if run is None or orders is None or actual is None:
        return
    tick, seal = run
    optimistic = side == "optimistic"

    _link(orders, issues)
    pending_from: dict[str, list] = {}
    pending_to: dict[str, list] = {}
    for od in orders:
        if od.bad or od.from_ts == "":
            continue  # 約定しうる足が無い注文は、約定を試さない
        pending_from.setdefault(od.from_ts, []).append(od)
        pending_to.setdefault(od.to_ts, []).append(od)

    fills: list[list[str]] = []
    active: dict[int, object] = {}
    sealed_reported = False

    for bar in bars:
        ts, o, h, l = _read_bar(bar)
        if ts is None:
            continue  # 値段が空の足は、無い足として飛ばす
        if not sealed_reported:
            try:
                reached = parse_instant(ts) >= seal
            except ValueError:
                raise _Stop(f"足の始まりの時刻 {ts!r} が時刻として読めない。")
            if reached:
                issues.add(f"足の始まり {ts} が run の封印の境 {seal.isoformat()} に届いている。")
                sealed_reported = True

        for od in pending_from.pop(ts, ()):
            od.activated = True
            active[od.seq] = od

        if active:
            _step(ts, o, h, l, tick, optimistic, active, fills, issues)

        for od in pending_to.pop(ts, ()):
            if od.activated:
                od.ended = True
                active.pop(od.seq, None)

    for lst in pending_from.values():
        for od in lst:
            issues.add(f"注文 {od.id!r} の from_ts {od.from_ts} が足の並びに無い。")
    for od in orders:
        if od.activated and not od.ended and not od.bad:
            issues.add(f"注文 {od.id!r} の to_ts {od.to_ts} が、from_ts の後の足の並びに無い。")
    _check_px_column(orders, tick, issues)
    _compare_fills(fills_name, actual, fills, issues)


def _read_bar(bar):
    """足 1 本を (時刻の文字列, 始値, 高値, 安値) にする。値段が空なら (None, ...)。形が違えば止める。"""
    try:
        ts = bar[0]
        raw = (bar[1], bar[2], bar[3], bar[4])
    except (TypeError, IndexError, KeyError):
        raise _Stop("足の形が違う(時刻と 4 つの値段が要る)。")
    if not isinstance(ts, str):
        raise _Stop(f"足の始まりの時刻 {ts!r} が文字でない。")
    vals = []
    for v in raw:
        if v is None or v == "":
            return None, 0.0, 0.0, 0.0
        try:
            f = float(v)
        except (TypeError, ValueError):
            raise _Stop(f"足 {ts} の値段 {v!r} が数でない。")
        if math.isnan(f):
            return None, 0.0, 0.0, 0.0
        vals.append(f)
    o, h, l, _c = vals
    if l > h:
        raise _Stop(f"足 {ts} の安値 {l} が高値 {h} より高い。")
    return ts, o, h, l


def _link(orders, issues: Issues) -> None:
    """段の根・利確の親を注文の行からたどる。たどれない・種類が違うものは食い違いにして約定を試さない。"""
    by_id = {od.id: od for od in orders}
    for od in orders:
        if od.form == "level":
            root = by_id.get(od.root)
            if root is None:
                issues.add(f"段 {od.id!r} の根 {od.root!r} の行が注文の記録に無い。")
                od.bad = True
            elif root.form != "limit":
                issues.add(f"段 {od.id!r} の根 {od.root!r} が指値でない({root.form})。")
                od.bad = True
            else:
                od.root_order = root
        elif od.form == "exit":
            parent = by_id.get(od.parent)
            if parent is None:
                issues.add(f"利確 {od.id!r} の親 {od.parent!r} の行が注文の記録に無い。")
                od.bad = True
            elif parent.form not in ("limit", "level"):
                issues.add(f"利確 {od.id!r} の親 {od.parent!r} が指値でも段でもない({parent.form})。")
                od.bad = True
            else:
                od.parent_order = parent


def _step(ts, o, h, l, tick, optimistic, active, fills, issues: Issues) -> None:
    """1 本の足の約定(① 成行 → ② 前の足までに親が約定した利確 → ③ 指値 → ④ 段 → ⑤ この足で親が約定した利確)。"""
    acts = sorted(active.values(), key=_BY_SEQ)

    def fill(od, price, case):
        od.fill_ts, od.fill_px = ts, price
        active.pop(od.seq, None)
        fills.append([ts, od.id, od.side, repr(float(od.qty)), repr(float(price)), case])

    # ② に入る利確は、足の頭の時点で親が約定済みのもの(③④で親が約定しても、その足では ⑤)
    earlier_exits = [od for od in acts if od.form == "exit" and od.parent_order.fill_ts is not None]

    for od in acts:  # ① 成行は始値
        if od.form == "market":
            fill(od, o, "market")
    for od in earlier_exits:  # ② 利確はふつうの指値の決まり
        r = limit_fill(od.side, limit_price(od.px_calc, tick), o, h, l)
        if r:
            fill(od, *r)
    for od in acts:  # ③ 指値
        if od.form == "limit":
            r = limit_fill(od.side, limit_price(od.px_calc, tick), o, h, l)
            if r:
                fill(od, *r)
    for od in acts:  # ④ 段
        if od.form != "level":
            continue
        root = od.root_order
        if od.fixed_px is None:
            if root.fill_ts is None:
                continue  # 根が約定するまで効かない
            if root.fill_ts != ts:
                issues.add(f"段 {od.id!r} は、根 {root.id!r} が約定した足 {root.fill_ts} より後に初めて出ている。")
                od.bad = True
                active.pop(od.seq, None)
                continue
            od.fixed_px = level_price(root.fill_px, od.offset, tick)
            r = inside_fill(od.fixed_px, h, l, "anchor_bar")
        else:
            r = limit_fill(od.side, od.fixed_px, o, h, l)
        if r:
            fill(od, *r)
    for od in acts:  # ⑤ この足で親が約定した利確。良い側だけ、範囲の内なら値段で。悪い側は次の足から
        if od.form == "exit" and od.seq in active and od.parent_order.fill_ts == ts:
            if optimistic:
                r = inside_fill(limit_price(od.px_calc, tick), h, l, "entry_bar")
                if r:
                    fill(od, *r)


def _check_px_column(orders, tick, issues: Issues) -> None:
    """注文の記録の px 列を、戦略の値段(px_calc)・距離と作り直した根の約定値段から計算し直した値と突き合わせる。"""
    for od in orders:
        if od.bad or od.form == "market":
            continue
        if od.form == "level":
            expected = "" if od.fixed_px is None else repr(float(od.fixed_px))
        else:
            expected = repr(float(limit_price(od.px_calc, tick)))
        if od.px_text != expected:
            issues.add(f"注文 {od.id!r}({od.form})の px 列 {od.px_text!r} が、計算し直した値 {expected!r} と違う。")


def _compare_fills(name, actual, fills, issues: Issues) -> None:
    """作り直した約定を走らせと同じ書き方で書き、記録のファイルの中身と 1 字違わず比べる。"""
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(FILLS_COLS)
    w.writerows(fills)
    expected = buf.getvalue()
    if actual == expected:
        return
    a, e = actual.split("\n"), expected.split("\n")
    if a and a[-1] == "":
        a.pop()  # 最後の行の終わりの改行の後ろ
    e.pop()      # 作り直した中身は必ず改行で終わる
    if actual.count("\n") != expected.count("\n"):
        issues.add(f"{name} の改行の数が違う(走らせの記録 {actual.count(chr(10))}、作り直し {expected.count(chr(10))})。")
    shown = 0
    for i in range(max(len(a), len(e))):
        la = a[i] if i < len(a) else "(行が無い)"
        le = e[i] if i < len(e) else "(行が無い)"
        if la != le:
            issues.add(f"{name} の {i + 1} 行目が違う(走らせの記録 {la!r}、作り直し {le!r})。")
            shown += 1
            if shown >= 10:
                break
    if shown == 0:
        issues.add(f"{name} の行は同じだが、改行や末尾の書き方が作り直しと違う。")
