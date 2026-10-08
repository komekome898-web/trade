"""単純な測りの道の約定の作り直し(bot.bt.simple_refill = SPEC.md §5 の 1)の受け入れの試験。

リードが書いた(決まりの正本は docs/DISCUSSIONS/2026-10-08_simple_road/SPEC.md、場面の表は simple_scenes.py)。作業者は試験を変えずに
通す。作り直しは SPEC.md だけから約定の決まりを書き直したもの。走らせ(bot.bt.simple)のコードを読まず、import もしない。
L-831 で、場面を走らせの試験と同じ表にまとめ、重なる書き換えを消した。

オーナーの逐語: L-821「**1.よい 2.よい**」(検査は約定の作り直しと数の作り直しの 2 つ)/
L-819「**測定方法も残し方も検査もシンプルにできるはず**」

口(この試験が決める):
- `from bot.bt.simple_refill import refill`
- `refill(bars, out_dir, side)`: bars は走らせに渡したのと同じ足の並び(1 回だけ前から読む。生成器でもよい)。
  out_dir の `orders_<側>.csv`・`run_<側>.json`(刻み tick・側 side・封印の境 seal)と bars から約定を計算し直し、
  `fills_<側>.csv` と 1 字違わず(行の順も)同じか比べる。食い違いの文の並び(日本語)を返し、同じなら空。
  読めない・形の違う入力は例外にせず食い違いの文で返す。
"""
from __future__ import annotations

import csv
import json
import os
import random
import shutil
import tracemalloc
from datetime import datetime, timedelta, timezone

import pytest

from simple_scenes import (A1, A2, B1, B2, FLAT, META, R1, R2, ROOT, SCENES, SIDES, X1, Script, check_all, ex, lim, lv,
                           make_bars, ts)

simple = pytest.importorskip("bot.bt.simple")
refill_mod = pytest.importorskip("bot.bt.simple_refill")
run, refill = simple.run, refill_mod.refill


# ================================================================ 場面の表(simple_scenes.py)で、走らせの記録と作り直しが同じ
def test_scenes(tmp_path):
    def one(sc):
        for side in SIDES:
            out = str(tmp_path / f"{SCENES.index(sc)}" / side)
            bars = make_bars(sc["rows"], sc.get("minutes"))
            run(bars, Script(sc["plan"], sc.get("signals")), side=side, out_dir=out, tick=sc.get("tick", 1.0), meta=META)
            assert refill(bars, out, side) == [], side
    check_all(SCENES, one)


# ================================================================ 乱数の戦略で、走らせの記録と作り直しが同じ(足は生成器で渡す)
class Random:
    """乱数の戦略: 指値・段・段や指値に付けた利確・成行・取り下げ・親が約定した後に出す利確・close の印の指値。"""

    def __init__(self, seed):
        self.r, self.n, self.live, self.filled = random.Random(seed), 0, {}, {}

    def new(self):
        self.n += 1
        return f"o{self.n}"

    def decide(self, bar, fills):
        r, close = self.r, bar[4]
        for f in fills:
            o = self.live.pop(f["id"], None)
            if o is not None:
                self.filled[f["id"]] = o
        keep = {i: o for i, o in self.live.items() if r.random() < 0.8}
        # 根を外したら、その根の段も外す(残すと止まる)。親を外したら、その親の利確も外す
        keep = {i: o for i, o in keep.items()
                if not (o["form"] == "level" and o["root"] not in keep and o["root"] not in self.filled)
                and not (o["form"] == "exit" and o["parent"] not in keep and o["parent"] not in self.filled)}
        if r.random() < 0.3:
            side = r.choice(("buy", "sell"))
            sgn = 1 if side == "buy" else -1
            root = self.new()
            keep[root] = {"form": "limit", "side": side, "qty": 0.001 * r.randint(1, 3),
                          "px": close + sgn * r.choice((-300.0, -100.0, 0.0, 50.0, 200.0)) + r.choice((0.0, 0.4))}
            for _ in range(r.randint(0, 3)):
                keep[self.new()] = {"form": "level", "side": side, "qty": keep[root]["qty"], "root": root,
                                    "offset": -sgn * r.choice((0.0, 50.0, 100.5, 150.0))}
            if r.random() < 0.5:
                keep[self.new()] = {"form": "exit", "side": "sell" if side == "buy" else "buy", "qty": keep[root]["qty"],
                                    "parent": root, "px": close + sgn * r.choice((50.0, 100.0, 300.0))}
        if self.filled and r.random() < 0.2:
            pid = r.choice(sorted(self.filled))
            p = self.filled[pid]
            if p["form"] in ("limit", "level"):
                sgn = 1 if p["side"] == "buy" else -1
                keep[self.new()] = {"form": "exit", "side": "sell" if p["side"] == "buy" else "buy", "qty": p["qty"],
                                    "parent": pid, "px": close + sgn * r.choice((-50.0, 50.0, 150.0))}
        if r.random() < 0.05:
            keep[self.new()] = {"form": "market", "side": r.choice(("buy", "sell")), "qty": 0.001}
        if r.random() < 0.1:  # close の印の指値(印の正しさは戦略の仕事なので、ここでは建玉を見ない)
            sd = r.choice(("buy", "sell"))
            keep[self.new()] = {"form": "limit", "side": sd, "qty": 0.001, "close": True,
                                "px": close + (1 if sd == "buy" else -1) * r.choice((-300.0, -100.0, 0.0, 50.0, 200.0))}
        self.live = keep
        return dict(keep), []


def _walk(seed, n):
    r = random.Random(1000 + seed)
    px, rows = 7000000.0, []
    for m in range(n):
        if r.random() < 0.05:
            continue  # 欠けた分
        op = px
        hi = op + r.choice((0, 50, 100, 250))
        lo = op - r.choice((0, 50, 100, 250))
        cl = r.uniform(lo, hi)
        px = round(cl)
        rows.append((ts(m), float(op), float(hi), float(lo), float(cl), 1.0))
    return rows


def test_random_strategy(tmp_path):
    def one(seed):
        bars = _walk(seed, 600)
        for side in SIDES:
            out = str(tmp_path / f"{seed}" / side)
            run(bars, Random(seed), side=side, out_dir=out, tick=1.0, meta=META)
            with open(os.path.join(out, f"fills_{side}.csv"), encoding="utf-8") as fh:
                assert len(fh.read().splitlines()) > 20, side  # 約定が十分にある
            assert refill((b for b in bars), out, side) == [], side  # 足を並びにして持たず 1 回だけ前から読む形でも作り直せる
    check_all([(f"乱数の種 {s}", s) for s in range(6)], lambda c: one(c[1]))


# ================================================================ 書き換えた記録・違う足・違う側を通さない
def _base(tmp_path):
    rows = [FLAT, B1, B2, A1, A2, FLAT]
    plan = {0: {"r": ROOT, "l1": lv(-100.0), "l2": lv(-200.0), "x": ex("l1", 6999790.0)},
            1: {"l2": lv(-200.0), "x": ex("l1", 6999790.0)},
            2: {"r1": R1, "x1": X1}, 3: {"r2": R2, "x1": X1},
            4: {"m": {"form": "market", "side": "sell", "qty": 0.009},
                "far": lim("buy", 6000000.0)},  # 約定しない指値(データの終わりまで出たまま)
            # 最後の足の判定で出す根 far2・段 farl・利確 farx(約定しうる足が無く from_ts は空。止める注文の検めは
            #   約定を試す注文だけでなく、注文の記録の全部の行に効く)
            5: {"far": lim("buy", 6000000.0), "far2": lim("buy", 6000000.0), "farl": lv(-100.0, root="far2"),
                "farx": ex("far2", 6000100.0)}}
    bars = make_bars(rows)
    out = str(tmp_path / "base")
    run(bars, Script(plan), side="optimistic", out_dir=out, tick=1.0, meta=META)
    assert refill(bars, out, "optimistic") == []
    return out, bars


def _rw(out, name, fn):
    p = os.path.join(out, f"{name}_optimistic.csv")
    with open(p, newline="", encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    rows = fn(rows)
    with open(p, "w", newline="", encoding="utf-8") as fh:
        csv.writer(fh, lineterminator="\n").writerows(rows)


def _col(rows, name):
    return rows[0].index(name)


def _field(name, rid, col, value):
    """記録 name の番号 rid の行の列 col を value(関数なら今の値から)にする。"""
    def tamper(out, bars):
        def fn(rows):
            i, k = _col(rows, col), _col(rows, "id")
            for row in rows[1:]:
                if row[k] == rid:
                    row[i] = value(row[i]) if callable(value) else value
            return rows
        _rw(out, name, fn)
    return tamper


def _fills(fn):
    return lambda out, bars: _rw(out, "fills", lambda rows: fn(rows, [b[0] for b in bars]))


def _swap_same_bar(rows, _):
    i = _col(rows, "ts")
    k = next(k for k in range(1, len(rows) - 1) if rows[k][i] == rows[k + 1][i])
    rows[k], rows[k + 1] = rows[k + 1], rows[k]
    return rows


def _next_bar(rows, tss):
    rows[1][0] = tss[tss.index(rows[1][0]) + 1]
    return rows


def _run_json(**kw):
    def tamper(out, bars):
        p = os.path.join(out, "run_optimistic.json")
        with open(p, encoding="utf-8") as fh:
            rec = json.load(fh)
        rec.update({k: (v(bars) if callable(v) else v) for k, v in kw.items()})
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(rec, fh)
    return tamper


def _both(*ts_):
    def tamper(out, bars):
        for t in ts_:
            t(out, bars)
    return tamper


def _drop_close_col(out, bars):
    _rw(out, "orders", lambda rows: [r[:_col(rows, "close")] + r[_col(rows, "close") + 1:] for r in rows])


def _garbage_orders(out, bars):
    with open(os.path.join(out, "orders_optimistic.csv"), "w", encoding="utf-8") as fh:
        fh.write("garbage\n1,2,3\n")


def _other_bars(out, bars):
    t, op, hi, lo, cl, v = bars[2]
    bars[2] = (t, op, hi, lo + 200.0, cl, v)  # 安値を上げて、段 l2(6,999,600)が足 2 で約定しなくなる


def _as_pessimistic(out, bars):
    for name in ("orders_{}.csv", "fills_{}.csv", "run_{}.json"):
        os.rename(os.path.join(out, name.format("optimistic")), os.path.join(out, name.format("pessimistic")))


NOT_FILLED_TS = "2023-11-14T23:59:00+00:00"
TAMPERS = [
    # 約定の記録
    ("約定を次の足にずらす", _fills(_next_bar)),
    ("約定の記録の最後の行の値段だけを 1 円上げる", _fills(lambda rows, _: rows[:-1] + [rows[-1][:4] + [repr(float(rows[-1][4]) + 1.0)] + rows[-1][5:]])),
    ("case を変える", _fills(lambda rows, _: [rows[0], rows[1][:5] + ["range" if rows[1][5] != "range" else "open"]] + rows[2:])),
    ("約定の行を消す", _fills(lambda rows, _: rows[:-1])),
    ("約定の行を 2 重にする", _fills(lambda rows, _: rows + [rows[-1]])),
    ("同じ足の約定の順を入れ替える", _fills(_swap_same_bar)),
    ("値段の書き方だけを変える", _fills(lambda rows, _: [rows[0], rows[1][:4] + [rows[1][4] + "0"] + rows[1][5:]] + rows[2:])),
    # 注文の記録(作り直しは px 列を入力にしない。from_ts・to_ts は足に無い時刻なら食い違い)
    ("注文の戦略の値段を変える", _field("orders", "r1", "px_calc", lambda v: repr(float(v) - 1000.0))),
    ("利確の from_ts を親の約定の足より後にずらす", _field("orders", "x", "from_ts", ts(2))),
    ("約定しなかった注文の from_ts を足に無い時刻に", _field("orders", "far", "from_ts", NOT_FILLED_TS)),
    ("約定しなかった注文の to_ts を足に無い時刻に", _field("orders", "far", "to_ts", NOT_FILLED_TS)),
    ("約定しなかった根の行を消す(段と利確の根・親が無い)", lambda out, bars: _rw(out, "orders", lambda rows: [r for r in rows if r[1] != "far2"])),
    ("指値の px 列だけを書き換える", _field("orders", "r1", "px", lambda v: repr(float(v) + 1.0))),
    ("利確の px 列だけを書き換える", _field("orders", "x1", "px", lambda v: repr(float(v) + 1.0))),
    ("段の px 列だけを書き換える", _field("orders", "l2", "px", lambda v: repr(float(v) + 1.0))),
    # 走らせが切り捨てを忘れたかのように px 列と約定の値段をそろえる(px 列を入力にする作り直しは通してしまう)
    ("指値の px 列と約定の値段をそろえて書き換える", _both(_field("orders", "r1", "px", "7000000.5"), _field("fills", "r1", "px", "7000000.5"))),
    ("段の px 列と約定の値段をそろえて書き換える", _both(_field("orders", "l1", "px", "6999700.5"), _field("fills", "l1", "px", "6999700.5"))),
    # 止める注文(SPEC.md §3)を、約定の記録を変えない注文(約定しない根 far2 の段 farl・親 far2 の利確 farx)の上で破る。
    #   約定の計算し直しは変わらないので、止める注文の検めが無いと見えない
    ("約定しない根の段の売買を根と違えて書く", _field("orders", "farl", "side", "sell")),
    ("約定しない根の段の距離の向きを逆に書く", _field("orders", "farl", "offset", lambda v: repr(-float(v)))),
    ("約定しない親の利確の売買を親と同じに書く", _field("orders", "farx", "side", "buy")),
    ("約定しない親の利確の量を親と違えて書く", _field("orders", "farx", "qty", "0.018")),
    ("利確に close の印を書く", _field("orders", "x1", "close", "1")),
    ("成行に close の印を書く", _field("orders", "m", "close", "1")),
    ("close の欄に 0 を書く", _field("orders", "far", "close", "0")),
    ("注文の記録が close の列の無い 12 列", _drop_close_col),
    ("注文の記録がでたらめ", _garbage_orders),
    # run の記録・足・側
    ("run の刻みを変える", _run_json(tick=1000.0)),
    ("run の側だけを書き換える", _run_json(side="pessimistic")),
    ("足が run の封印の境に届いている", _run_json(seal=lambda bars: bars[-1][0])),
    ("走らせに渡したのと違う足", _other_bars),
    ("良い側の記録を悪い側として作り直す", _as_pessimistic),
]


def test_tampered_records_are_caught(tmp_path):
    out, bars = _base(tmp_path)

    def one(case):
        name, tamper = case
        d = str(tmp_path / f"t{TAMPERS.index(case)}")
        shutil.copytree(out, d)
        bs = list(bars)
        tamper(d, bs)
        side = "pessimistic" if os.path.exists(os.path.join(d, "run_pessimistic.json")) else "optimistic"
        got = refill(bs, d, side)  # 例外を出さない
        assert isinstance(got, list) and got != [] and all(isinstance(x, str) for x in got), got
    check_all(TAMPERS, one)


# ================================================================ 足を記憶に持たない
class _Idle:
    def decide(self, bar, fills):
        return {}, []


def _idle_bars(n):
    t0 = datetime(2020, 1, 1, tzinfo=timezone.utc)
    return (((t0 + timedelta(minutes=k)).isoformat(), 7e6, 7e6, 7e6, 7e6, 1.0) for k in range(n))


def _refill_peak(tmp_path, n):
    out = str(tmp_path / f"idle{n}")
    run(_idle_bars(n), _Idle(), side="optimistic", out_dir=out, tick=1.0, meta=META)
    tracemalloc.start()
    try:
        assert refill(_idle_bars(n), out, "optimistic") == []
        return tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()


def test_bars_are_not_kept(tmp_path):
    # 測る期間は約 423 万本。足 1 本あたりの記憶の増え方が 50 バイト未満(足を並びにして全部持つと 1 本あたり数百バイト)
    a, b = _refill_peak(tmp_path, 2000), _refill_peak(tmp_path, 12000)
    assert (b - a) / 10000 < 50, (a, b)
