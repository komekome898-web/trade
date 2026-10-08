"""走らせ(SPEC.md §2・§4): 足を古い順に回し、足ごとに 約定 → 戦略に知らせる → 判定。残すファイルは回しながら書き足す。"""
from __future__ import annotations

import csv
import json
import os
import subprocess
from contextlib import ExitStack

from bot.bt.road.ledger import book

from .common import (FILL_COLS, SIDES, SimpleRoadError, cell, floor_tick, is_number, num, parse_ts,
                     step_ok, to_ns, trades_text)
from .fills import Order, fill_bar

SIDE_NAMES = ("optimistic", "pessimistic")
ORDER_COLS = ("seq", "id", "form", "side", "qty", "px_calc", "px", "root", "offset", "parent", "from_ts", "to_ts")
SIGNAL_COLS = ("id", "kind", "direction", "start_ts", "end_ts", "end_reason", "value_json")
FORMS = ("limit", "level", "exit", "market")


class _Csv:
    """1 行ずつ書き足してすぐファイルに出す表。"""

    def __init__(self, stack: ExitStack, path: str, cols):
        self._fh = stack.enter_context(open(path, "w", newline="", encoding="utf-8"))
        self._w = csv.writer(self._fh, lineterminator="\n")
        self.row(cols)

    def row(self, vals):
        self._w.writerow([cell(v) for v in vals])
        self._fh.flush()


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


def _shape(oid, o) -> None:
    """注文の形の検め(1 つずつ。他の注文との関係は _links)。"""
    if not isinstance(oid, str) or not oid:
        raise SimpleRoadError(f"注文の番号は空でない文字: {oid!r}")
    if not isinstance(o, dict):
        raise SimpleRoadError(f"注文 {oid} は辞書で返す")
    if o.get("form") not in FORMS:
        raise SimpleRoadError(f"注文 {oid} の形が知らない形: {o.get('form')!r}")
    if o.get("side") not in SIDES:
        raise SimpleRoadError(f"注文 {oid} の売買は buy / sell: {o.get('side')!r}")
    q = o.get("qty")
    if not is_number(q) or not step_ok(q):
        raise SimpleRoadError(f"注文 {oid} の量は 0 より大きく 0.001 の刻みの上: {q!r}")
    f = o["form"]
    if f in ("limit", "exit") and not (is_number(o.get("px")) and o["px"] > 0):
        raise SimpleRoadError(f"注文 {oid} の値段は 0 より大きい数: {o.get('px')!r}")
    if f == "level":
        if not isinstance(o.get("root"), str) or not is_number(o.get("offset")):
            raise SimpleRoadError(f"注文 {oid}(段)は根の番号と距離の数が要る")
        if (o["side"] == "buy" and o["offset"] > 0) or (o["side"] == "sell" and o["offset"] < 0):
            raise SimpleRoadError(f"注文 {oid}(段)の距離の向きが違う(買いは負、売りは正): {o['offset']!r}")
    if f == "exit" and not isinstance(o.get("parent"), str):
        raise SimpleRoadError(f"注文 {oid}(利確)は親の番号が要る")


def run(bars, strategy, side, out_dir, tick, meta) -> None:
    """bars を古い順に回して SPEC.md §4 のファイルを out_dir に書く。止める場面は SimpleRoadError。"""
    if side not in SIDE_NAMES:
        raise SimpleRoadError(f"側は optimistic か pessimistic: {side!r}")
    if not is_number(tick) or tick <= 0:
        raise SimpleRoadError(f"刻みは 0 より大きい数: {tick!r}")
    if not isinstance(meta, dict) or "seal" not in meta:
        raise SimpleRoadError("meta に封印の境 seal が無い(境以後の足を止める検めができない)")
    seal = parse_ts(meta["seal"])
    os.makedirs(out_dir, exist_ok=True)
    path = lambda name, ext="csv": os.path.join(out_dir, f"{name}_{side}.{ext}")  # noqa: E731
    for stale in (path("trades"), path("summary", "json")):
        if os.path.exists(stale):
            os.remove(stale)  # 前の走らせの数を残さない
    with open(path("run", "json"), "w", encoding="utf-8") as fh:
        json.dump(dict(meta, tick=tick, side=side, git=_git_version()), fh, ensure_ascii=False, indent=1)

    seen: set[str] = set()  # 受けた注文の番号(使い回しの検め用。消えた注文は番号だけをここに残す)
    n_seen = 0  # 受けた注文の数(seq の元。記憶に持つ注文の数からは出さない)
    filled: dict[str, Order] = {}  # 約定した注文(段・利確の検めに要る中身を持つ)
    live: list[Order] = []
    sig_open: dict[str, list] = {}  # 出ている合図 id → [kind, direction, start_ts, value_json]
    sig_seen: set[str] = set()
    fill_rows: list[dict] = []
    last_ts = None
    with ExitStack() as stack:
        orders_f = _Csv(stack, path("orders"), ORDER_COLS)
        fills_f = _Csv(stack, path("fills"), FILL_COLS)
        sig_f = _Csv(stack, path("signals"), SIGNAL_COLS)

        def write_order(o: Order) -> None:
            orders_f.row([o.seq, o.id, o.form, o.side, num(o.qty),
                          None if o.px_calc is None else num(o.px_calc), None if o.px is None else num(o.px),
                          o.root, None if o.offset is None else num(o.offset), o.parent, o.first_ts, o.last_ts])

        for bar in bars:
            ts = bar[0]
            t = parse_ts(ts)
            if t >= seal:
                raise SimpleRoadError(f"封印の境 {meta['seal']} 以後に始まる足は渡せない: {ts}")
            if last_ts is not None and t <= parse_ts(last_ts):
                raise SimpleRoadError(f"足が古い順になっていない: {last_ts} の次に {ts}")
            if len(bar) != 6 or not all(is_number(x) for x in bar[1:]):
                raise SimpleRoadError(f"足の値が数でない: {bar!r}")
            if bar[3] > bar[2]:
                raise SimpleRoadError(f"足の安値が高値より高い: {ts}")
            last_ts = ts
            # 1. 約定
            for o in live:
                if o.first_ts is None:
                    o.first_ts = ts
                o.last_ts = ts
            got = fill_bar(live, bar, side, tick)
            out = []
            for o in got:
                fills_f.row([ts, o.id, o.side, num(o.qty), num(o.fill_px), o.case])
                write_order(o)
                fill_rows.append({"t_ns": to_ns(ts), "side": o.side, "qty": float(o.qty), "px": float(o.fill_px), "ccy": "JPY"})
                out.append({"ts": ts, "id": o.id, "side": o.side, "qty": o.qty, "px": o.fill_px, "case": o.case})
            live = [o for o in live if o.state == "live"]
            for o in got:
                filled[o.id] = o
            # 2. 知らせ 3. 判定
            res = strategy.decide(bar, out)
            try:
                orders, events = res
                orders = dict(orders)
            except (TypeError, ValueError):
                raise SimpleRoadError("decide は (注文の辞書, 合図の出来事の並び) を返す") from None
            new: dict[str, Order] = {}
            by_id = {o.id: o for o in live}
            for oid, raw in orders.items():
                _shape(oid, raw)
                if oid in filled:
                    raise SimpleRoadError(f"約定し終えた注文の番号 {oid} をもう一度返した")
                old = by_id.get(oid)
                if old is None:
                    if oid in seen:
                        raise SimpleRoadError(f"消えた注文の番号 {oid} をもう一度返した")
                    new[oid] = Order(n_seen, oid, raw)
                    n_seen += 1
                    seen.add(oid)
                elif Order(old.seq, oid, raw).key() != old.key():
                    raise SimpleRoadError(f"同じ番号 {oid} で中身が前と違う(値段を変えるときは新しい番号で出す)")
            _links(lambda i: new.get(i) or by_id.get(i) or filled.get(i), orders, new)
            for o in live:
                if o.id not in orders:  # 返さなかった注文はここで消える
                    o.state = "gone"
                    write_order(o)
            live = [o for o in live if o.state == "live"]
            for oid, o in new.items():
                if o.form in ("limit", "exit"):
                    o.px = floor_tick(o.px_calc, tick)
                    if o.px <= 0:
                        raise SimpleRoadError(f"注文 {oid} の切り捨てた値段が 0 以下")
                live.append(o)
            _signals(events, ts, sig_open, sig_seen, sig_f)
        # データの終わり
        for o in sorted(live, key=lambda x: x.seq):
            write_order(o)
        for sid, (kind, direction, start_ts, vj) in sig_open.items():
            sig_f.row([sid, kind, direction, start_ts, None, "データの終わり", vj])

    ledger = book(fill_rows)
    with open(path("trades"), "w", newline="", encoding="utf-8") as fh:
        fh.write(trades_text(ledger.trades))
    summary = {k: v for k, v in ledger.summary.items() if k != "trades"}
    with open(path("summary", "json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=1)


def _links(find, returned: dict, new: dict) -> None:
    """根・親の参照を結び、止める場面(根の無い段・親の無い利確ほか)を検める。find は番号から出ている・約定した注文を引く。"""
    for oid in returned:
        o = find(oid)
        if o.form not in ("level", "exit"):
            continue
        ref_id = o.root if o.form == "level" else o.parent
        ref = find(ref_id)
        what = "根" if o.form == "level" else "親"
        if ref is None or (ref.state != "filled" and ref_id not in returned):
            raise SimpleRoadError(f"注文 {oid} の{what} {ref_id} が出ていなくて約定もしていない")
        if o.form == "level":
            if ref.form != "limit":
                raise SimpleRoadError(f"段 {oid} の根 {ref_id} が limit でない")
            if ref.side != o.side:
                raise SimpleRoadError(f"段 {oid} の売買が根 {ref_id} と違う")
            if oid in new and ref.state == "filled":
                raise SimpleRoadError(f"段 {oid} は根 {ref_id} が約定した後に初めて出た")
            o.root_order = ref
        else:
            if ref.form not in ("limit", "level"):
                raise SimpleRoadError(f"利確 {oid} の親 {ref_id} が limit でも level でもない")
            if ref.side == o.side:
                raise SimpleRoadError(f"利確 {oid} の売買が親 {ref_id} と同じ")
            if ref.qty != o.qty:
                raise SimpleRoadError(f"利確 {oid} の量が親 {ref_id} と違う")
            o.parent_order = ref


def _signals(events, ts, sig_open: dict, sig_seen: set, sig_f: _Csv) -> None:
    for ev in events or []:
        op, sid = ev.get("op"), ev.get("id")
        if op == "start":
            if sid in sig_seen:
                raise SimpleRoadError(f"合図 {sid} を二度始めた")
            try:
                vj = json.dumps(ev.get("value"), ensure_ascii=False, sort_keys=True)
            except TypeError:
                raise SimpleRoadError(f"合図 {sid} の value を JSON にできない") from None
            sig_seen.add(sid)
            sig_open[sid] = [ev.get("kind"), ev.get("direction"), ts, vj]
        elif op == "end":
            if sid not in sig_open:
                raise SimpleRoadError(f"出ていない合図 {sid} を終えた")
            kind, direction, start_ts, vj = sig_open.pop(sid)
            sig_f.row([sid, kind, direction, start_ts, ts, ev.get("reason"), vj])
        else:
            raise SimpleRoadError(f"合図の出来事の op が知らない: {op!r}")
