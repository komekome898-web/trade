"""走らせ(SPEC.md §1・§2・§4): 足を古い順に回し、足ごとに足の中の道筋をたどる。約定か見張る値段への到達が起きた
最初の点で止まって戦略を呼び、終値でもう一度呼ぶ。約定と合図を回しながら書き足し、終わった後に約定のファイルを
頭から読んで損益のまとめを数える(約定を記憶にためない。L-854)。"""
from __future__ import annotations

import csv
import json
import os
import subprocess
from bisect import bisect_left, bisect_right
from contextlib import ExitStack
from decimal import Decimal

from bot.bt.road.ledger import book

from .common import FILL_COLS, SUMMARY_COLS, SimpleRoadError, cell, floor_tick, is_number, num, parse_ts, to_ns
from .fills import Order, check_shape

SIGNAL_COLS = ("id", "kind", "direction", "start_ts", "end_ts", "end_reason")
MAX_CALLS_AT_POINT = 100  # 同じ点で呼ぶ回数の上限(SPEC.md §2.2 の 4)


class _Csv:
    """1 行ずつ書き足してすぐファイルに出す表。"""

    def __init__(self, stack: ExitStack, path: str, cols):
        self._fh = stack.enter_context(open(path, "w", newline="", encoding="utf-8"))
        self._w = csv.writer(self._fh, lineterminator="\n")
        self.row(cols)

    def row(self, vals):
        self._w.writerow([cell(v) for v in vals])


def _git_version() -> str:
    """コードの git の版。`src/` の下のどこかに未コミットの変更か git が追っていない新しいファイルがあれば印を付ける。"""
    here = os.path.dirname(os.path.abspath(__file__))
    try:
        top = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=here, capture_output=True, text=True,
                             check=True).stdout.strip()
        src = os.path.join(top, "src")
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=top, capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all", "--", src], cwd=top,
                               capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return head + ("+未コミットの変更あり" if dirty else "")


def run(bars, strategy, out_dir, tick, meta) -> None:
    """bars を古い順に回して SPEC.md §4 のファイルを out_dir に書く。止める場面は SimpleRoadError。"""
    if not is_number(tick) or tick <= 0:
        raise SimpleRoadError(f"刻みは 0 より大きい数: {tick!r}")
    if not isinstance(meta, dict) or "seal" not in meta:
        raise SimpleRoadError("meta に封印の境 seal が無い(境以後の足を止める検めができない)")
    seal = parse_ts(meta["seal"])
    os.makedirs(out_dir, exist_ok=True)
    path = lambda name: os.path.join(out_dir, name)  # noqa: E731
    if os.path.exists(path("summary.json")):
        os.remove(path("summary.json"))  # 前の走らせの数を残さない
    with open(path("run.json"), "w", encoding="utf-8") as fh:
        json.dump(dict(meta, tick=tick, git=_git_version()), fh, ensure_ascii=False, indent=1)

    with ExitStack() as stack:
        w = _Walk(strategy, tick, _Csv(stack, path("fills.csv"), FILL_COLS), _Csv(stack, path("signals.csv"), SIGNAL_COLS))
        prev = None  # 飛ばさずに回した直前の足の終値(データの頭では無い)
        last_t = None
        for bar in bars:
            t = _check_bar(bar, seal, meta["seal"], last_t)
            last_t = t
            ts, op, hi, lo, cl, _ = bar
            if op == cl and (prev is None or op == prev):
                continue  # 向きの決まらない足・データの頭の始値 = 終値 の足は無い足として飛ばす(SPEC.md §1)
            if cl > op or (cl == op and op < prev):
                pts = (op, lo, hi, cl)  # 陽線・下がって始まった始値 = 終値 の足
            else:
                pts = (op, hi, lo, cl)  # 陰線・上がって始まった始値 = 終値 の足
            w.bar(ts, prev, pts, tuple(bar))
            prev = cl
        # データの終わり
        for sid, (kind, direction, start_ts) in w.sig_open.items():
            w.sig_f.row([sid, kind, direction, start_ts, None, "データの終わり"])
    with open(path("summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summarize(path("fills.csv")), fh, ensure_ascii=False, indent=1)


def _check_bar(bar, seal, seal_iso, last_t):
    """足の検め(SPEC.md §1)。封印の境の検めは、向きの決まらない足を飛ばすより先にする。足の始まりの時刻を返す。"""
    ts = bar[0]
    t = parse_ts(ts)
    if t >= seal:
        raise SimpleRoadError(f"封印の境 {seal_iso} 以後に始まる足は渡せない: {ts}")
    if last_t is not None and t <= last_t:
        raise SimpleRoadError(f"足が古い順になっていない: {ts}")
    if len(bar) != 6 or not all(is_number(x) for x in bar[1:]):
        raise SimpleRoadError(f"足の値が数でない: {bar!r}")
    _, op, hi, lo, cl, _ = bar
    if lo > hi:
        raise SimpleRoadError(f"足の安値が高値より高い: {ts}")
    if not (lo <= op <= hi and lo <= cl <= hi):
        raise SimpleRoadError(f"足の始値か終値が安値〜高値の外: {ts}")
    return t


class _Walk:
    """出ている注文と見張る値段を持ち、1 本の足の道筋をたどって戦略を呼ぶ(SPEC.md §2.2)。

    保つこと: 戦略を呼び終えた点では、出ている注文のどれも今いる値段で約定する側にいない(すぐ約定するものは
    その点で約定させて呼び直すため)。だから道筋を a から b へ動くとき、届く注文は a より先にしか無い。
    """

    def __init__(self, strategy, tick, fills_f, sig_f):
        self.strategy, self.tick, self.fills_f, self.sig_f = strategy, tick, fills_f, sig_f
        self.live: dict[str, Order] = {}  # 出ている注文(番号を出した順 = seq の順)
        self.used: set[str] = set()  # 受けた注文の番号(使い回しの検め用。消えた注文の中身は持たない)
        self.n = 0  # 受けた注文の数(seq の元)
        self.watches: list = []  # 戦略が返した見張る値段そのもの
        self.wfloor: list = []  # 刻みに切り捨てた見張る値段(watches と同じ順)
        self.wsorted: list = []  # wfloor を小さい順に
        self.up: list = []  # 上へ動いて届く注文(売りの limit・買いの stop)を (値段, seq) の順に
        self.down: list = []  # 下へ動いて届く注文(買いの limit・売りの stop)を (値段の高い順, seq) に
        self.dirty = False  # 出ている注文が変わり、up・down を作り直す
        self.sig_open: dict[str, list] = {}
        self.sig_seen: set[str] = set()

    # ---------------------------------------------------------------- 1 本の足
    def bar(self, ts, prev, pts, bar) -> None:
        op = pts[0]
        if prev is not None:
            # 前の足の終値から始値へは飛ぶ。飛びの間の注文・見張る値段は始値で扱う(SPEC.md §2.1・§3)
            got = [o for o in self.live.values() if o.fills_at(op)]
            lo, hi = (prev, op) if op > prev else (op, prev)
            touched = [x for x, f in zip(self.watches, self.wfloor)
                       if op != prev and lo <= f <= hi and f != prev]
            if got or touched:
                fills = self._fill(ts, got, op, None)
                self._stop(ts, op, fills, touched)
        cur = op
        for nxt in pts[1:]:
            while cur != nxt:
                x = self._next(cur, nxt)
                if x is None:
                    cur = nxt
                    break
                side = self.up if x > cur else self.down
                got = sorted((o for o in side if o.px == x), key=lambda o: o.seq)
                touched = [v for v, f in zip(self.watches, self.wfloor) if f == x]
                fills = self._fill(ts, got, x, "path")
                self._stop(ts, x, fills, touched)
                cur = x
        self._call({"kind": "close", "ts": ts, "price": pts[3], "fills": [], "touched": [], "bar": bar}, ts)

    def _next(self, cur, nxt):
        """cur から nxt へ動くとき、最初に届く注文か見張る値段の値段(動き始めの点を除き、着いた点を含む)。無ければ None。"""
        if self.dirty:
            self._index()
        best = None
        if nxt > cur:
            if self.up and self.up[0].px <= nxt:
                best = self.up[0].px
            i = bisect_right(self.wsorted, cur)
            if i < len(self.wsorted) and self.wsorted[i] <= nxt and (best is None or self.wsorted[i] < best):
                best = self.wsorted[i]
        else:
            if self.down and self.down[0].px >= nxt:
                best = self.down[0].px
            i = bisect_left(self.wsorted, cur) - 1
            if i >= 0 and self.wsorted[i] >= nxt and (best is None or self.wsorted[i] > best):
                best = self.wsorted[i]
        return best

    def _index(self):
        orders = [o for o in self.live.values() if o.form != "market"]
        self.up = sorted((o for o in orders if o.up), key=lambda o: (o.px, o.seq))
        self.down = sorted((o for o in orders if not o.up), key=lambda o: (-o.px, o.seq))
        self.dirty = False

    # ---------------------------------------------------------------- 約定と呼び出し
    def _fill(self, ts, got, price, case) -> list:
        """got(seq の順)を price で約定させ、約定のファイルに書き、戦略に渡す約定の並びを返す。
        case が None なら始値への飛び: 成行は market、ほかは open。"""
        out = []
        for o in got:
            c = case or ("market" if o.form == "market" else "open")
            self.fills_f.row([ts, o.kind(), o.side, num(o.qty), num(price), c])
            out.append({"id": o.id, "side": o.side, "qty": o.qty, "px": price, "case": c})
            del self.live[o.id]
        if got:
            self.dirty = True
        return out

    def _stop(self, ts, price, fills, touched) -> None:
        """足の途中で止まった点で呼ぶ。返した注文のうち、この点ですぐ約定するものは約定させて同じ点でもう一度呼ぶ。"""
        calls = 0
        while True:
            calls += 1
            if calls > MAX_CALLS_AT_POINT:
                raise SimpleRoadError(f"同じ点({ts} の {price})で {MAX_CALLS_AT_POINT} 回を超えて呼んだ")
            self._call({"kind": "stop", "ts": ts, "price": price, "fills": fills, "touched": touched}, ts)
            got = [o for o in self.live.values() if o.fills_at(price)]
            if not got:
                return
            fills, touched = self._fill(ts, got, price, "now"), []

    def _call(self, ev, ts) -> None:
        res = self.strategy.decide(ev)
        try:
            orders, events, watches = res
        except (TypeError, ValueError):
            raise SimpleRoadError("decide は (注文の辞書, 合図の出来事の並び, 見張る値段の並び) を返す") from None
        if not isinstance(orders, dict):
            raise SimpleRoadError("decide が返す注文は辞書 {番号: 注文}")
        self._orders(orders)
        self._watches(watches)
        _signals(events, ts, self.sig_open, self.sig_seen, self.sig_f)

    def _orders(self, orders: dict) -> None:
        """返した注文の全部が出ている注文になる。返さなかった注文はここで消える(SPEC.md §2.2 の 3)。"""
        kept, new = [], []
        for oid, raw in orders.items():
            check_shape(oid, raw)
            old = self.live.get(oid)
            if old is None:
                if oid in self.used:
                    raise SimpleRoadError(f"約定し終えた・消えた注文の番号 {oid} をもう一度返した")
                new.append(Order(self.n, oid, raw, self.tick))
                self.n += 1
                self.used.add(oid)
            elif (raw["form"], raw["side"], float(raw["qty"]), raw.get("px"), raw.get("tag")) != old.key:
                raise SimpleRoadError(f"同じ番号 {oid} で中身が前と違う(値段を変えるときは新しい番号で出す)")
            else:
                kept.append(old)
        if new or len(kept) != len(self.live):
            kept.sort(key=lambda o: o.seq)
            self.live = {o.id: o for o in kept + new}
            self.dirty = True

    def _watches(self, watches) -> None:
        if not isinstance(watches, (list, tuple)) or not all(is_number(x) for x in watches):
            raise SimpleRoadError(f"見張る値段は数の並び: {watches!r}")
        if list(watches) != self.watches:
            self.watches = list(watches)
            self.wfloor = [floor_tick(x, self.tick) for x in self.watches]
            self.wsorted = sorted(self.wfloor)


def summarize(fills_path: str) -> dict:
    """約定のファイルを頭から読み、建玉が 0 に戻るまでを 1 つの塊として帳簿のツールに渡して、まとめを足し合わせる。
    記憶に持つのは今の塊(開いている取引 1 つ分)だけ。"""
    count = closed = open_tr = 0
    pnl = Decimal(0)
    chunk: list[dict] = []
    pos = Decimal(0)

    def flush():
        nonlocal closed, open_tr, pnl
        if chunk:
            s = book(chunk).summary
            closed += s["closed_trades"]
            open_tr += s["open_trades"]
            pnl += Decimal(s["pnl_jpy"])
            chunk.clear()

    with open(fills_path, newline="", encoding="utf-8") as fh:
        r = csv.reader(fh)
        head = next(r)
        ix = {c: head.index(c) for c in FILL_COLS}
        for row in r:
            q = Decimal(row[ix["qty"]])
            chunk.append({"t_ns": to_ns(row[ix["ts"]]), "side": row[ix["side"]], "qty": float(q),
                          "px": float(row[ix["px"]]), "ccy": "JPY"})
            count += 1
            pos += q if row[ix["side"]] == "buy" else -q
            if pos == 0:
                flush()
    flush()
    out = {"fill_count": count, "closed_trades": closed, "pnl_jpy": format(pnl.normalize(), "f") if pnl else "0",
           "open_trades": open_tr}
    assert set(out) == set(SUMMARY_COLS)
    return out


def _signals(events, ts, sig_open: dict, sig_seen: set, sig_f: _Csv) -> None:
    for ev in events or []:
        op, sid = ev.get("op"), ev.get("id")
        if op == "start":
            if sid in sig_seen:
                raise SimpleRoadError(f"合図 {sid} を二度始めた")
            sig_seen.add(sid)
            sig_open[sid] = [ev.get("kind"), ev.get("direction"), ts]
        elif op == "end":
            if sid not in sig_open:
                raise SimpleRoadError(f"出ていない合図 {sid} を終えた")
            kind, direction, start_ts = sig_open.pop(sid)
            sig_f.row([sid, kind, direction, start_ts, ts, ev.get("reason")])
        else:
            raise SimpleRoadError(f"合図の出来事の op が知らない: {op!r}")
