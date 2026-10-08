"""単純な測りの道 S2(約定の作り直し = SPEC.md §5 の 1)の受け入れの試験。

リードが書いた(決まりの正本は docs/DISCUSSIONS/2026-10-08_simple_road/SPEC.md)。作業者は試験を変えずに通す。
作り直しは、SPEC.md だけから約定の決まりを書き直したもの。走らせ(bot.bt.simple)のコードを読まず、import もしない。

オーナーの逐語: L-821「**1.よい 2.よい**」(検査は約定の作り直しと数の作り直しの 2 つ)/
L-819「**測定方法も残し方も検査もシンプルにできるはず**」/ L-824「**(a)**」

口(この試験が決める):
- `from bot.bt.simple_refill import refill`
- `refill(bars, out_dir, side)`: bars は走らせに渡したのと同じ足の並び(足の始まりの時刻の文字列, 始値, 高値, 安値, 終値, 出来高)。
  out_dir の `orders_<側>.csv`・`run_<側>.json`(刻み tick・側 side)と bars から約定を計算し直し、
  `fills_<側>.csv` と 1 字違わず(行の順も)同じか比べる。食い違いの文の並び(日本語)を返し、同じなら空。
  読めない・形の違う入力は例外にせず食い違いの文で返す。
"""
from __future__ import annotations

import csv
import json
import os
import random

import pytest

simple = pytest.importorskip("bot.bt.simple")
refill_mod = pytest.importorskip("bot.bt.simple_refill")
run, refill = simple.run, refill_mod.refill

SIDES = ("optimistic", "pessimistic")
SEAL = "2023-12-17T15:00:00+00:00"
META = {"strategy": "試験", "params": {}, "seal": SEAL, "bar_files": []}


def ts(k):
    """足 k の始まり。2023-11-14T00:00 から 1 分ずつ(k の欠けは呼ぶ側が作る)。"""
    return f"2023-11-14T{k // 60:02d}:{k % 60:02d}:00+00:00"


class Script:
    def __init__(self, plan):
        self.plan, self.k, self.done = plan, -1, set()

    def decide(self, bar, fills):
        self.k += 1
        self.done |= {f["id"] for f in fills}
        return {i: o for i, o in self.plan.get(self.k, {}).items() if i not in self.done}, []


def go(tmp_path, rows, plan, side, tick=1.0, minutes=None):
    minutes = minutes or list(range(len(rows)))
    bars = [(ts(m),) + tuple(float(x) for x in r) + (1.0,) for m, r in zip(minutes, rows)]
    out = str(tmp_path / side)
    run(bars, Script(plan), side=side, out_dir=out, tick=tick, meta=META)
    return out, bars


FLAT = (7000000, 7000000, 7000000, 7000000)
B1 = (6999800, 6999850, 6999700, 6999750)
B2 = (6999750, 6999800, 6999550, 6999600)
A1 = (7000000, 7000050, 6999950, 7000000)
A2 = (7000000, 7000150, 6999850, 7000000)
ROOT = {"form": "limit", "side": "buy", "qty": 0.009, "px": 7000050.0}
R1 = {"form": "limit", "side": "buy", "qty": 0.009, "px": 7000000.0}
X1 = {"form": "exit", "side": "sell", "qty": 0.009, "parent": "r1", "px": 7000100.0}
R2 = {"form": "limit", "side": "buy", "qty": 0.009, "px": 6999900.0}
MKT = {"form": "market", "side": "sell", "qty": 0.009}


def lv(off, root="r", side="buy"):
    return {"form": "level", "side": side, "qty": 0.009, "root": root, "offset": off}


SELL_ROOT = {"form": "limit", "side": "sell", "qty": 0.009, "px": 6999950.0}

SCENES = [
    # (名前, 足, 計画, 刻み, 分)
    ("L-816 の例: 根は始値・段は根の足と次の足", [FLAT, B1, B2], {0: {"r": ROOT, "l1": lv(-100.0), "l2": lv(-200.0)},
                                                  1: {"l2": lv(-200.0)}}, 1.0, None),
    ("段の値段の切り捨てと 10 進の和(刻み 0.5)", [FLAT, B1, B2], {0: {"r": ROOT, "l1": lv(-100.3)}, 1: {"l1": lv(-100.3)}}, 0.5, None),
    ("売りの段", [FLAT, (7000200, 7000300, 7000100, 7000200), FLAT],
     {0: {"r": SELL_ROOT, "l1": lv(100.0, side="sell"), "l2": lv(101.0, side="sell")}, 1: {"l2": lv(101.0, side="sell")}}, 1.0, None),
    ("段に付けた利確(親の足と次の足)", [FLAT, B1, B2, FLAT],
     {0: {"r": ROOT, "l1": lv(-100.0), "x": {"form": "exit", "side": "sell", "qty": 0.009, "parent": "l1", "px": 6999790.0}},
      1: {"x": {"form": "exit", "side": "sell", "qty": 0.009, "parent": "l1", "px": 6999790.0}},
      2: {"x": {"form": "exit", "side": "sell", "qty": 0.009, "parent": "l1", "px": 6999790.0}}}, 1.0, None),
    ("前の足までに親が約定した利確が新しい指値より先(L-824)", [FLAT, A1, A2], {0: {"r1": R1, "x1": X1}, 1: {"r2": R2, "x1": X1}},
     1.0, None),
    ("親が約定した後に出た利確は次の足から", [FLAT, A1, A2], {0: {"r1": R1}, 1: {"x1": dict(X1, px=7000040.0)}}, 1.0, None),
    ("成行と指値の始値・範囲の外", [FLAT, B1, (7000500, 7000600, 7000400, 7000500)],
     {0: {"r": ROOT}, 1: {"m": MKT, "s": {"form": "limit", "side": "sell", "qty": 0.009, "px": 7000100.0}}}, 1.0, None),
    ("根が約定しないまま消える", [FLAT, (7000200, 7000300, 7000100, 7000200), FLAT], {0: {"r": ROOT, "l1": lv(-100.0)}}, 1.0, None),
    ("欠けた分の後の次の足", [FLAT, B1, B2], {0: {"r": ROOT, "l1": lv(-300.0)}, 1: {"l1": lv(-300.0)}}, 1.0, [0, 1, 5]),
    ("同じ足に同じ形が 2 本(出した順)", [FLAT, B1], {0: {"b": dict(ROOT, px=6999750.0), "a": dict(ROOT, px=6999760.0)}}, 1.0, None),
    ("データの終わりまで出ていた注文", [FLAT, FLAT], {0: {"r": dict(ROOT, px=6000000.0)}, 1: {"r": dict(ROOT, px=6000000.0)}}, 1.0, None),
]


# ================================================================ P1 走らせの記録と作り直しが同じ
@pytest.mark.parametrize("side", SIDES)
@pytest.mark.parametrize("name,rows,plan,tick,minutes", SCENES, ids=[s[0] for s in SCENES])
def test_p1_scenes_match(tmp_path, side, name, rows, plan, tick, minutes):
    out, bars = go(tmp_path, rows, plan, side, tick, minutes)
    assert refill(bars, out, side) == []


class Random:
    """乱数の戦略: 指値・段・段や指値に付けた利確・成行・取り下げ・親が約定した後に出す利確。"""

    def __init__(self, seed):
        self.r, self.k, self.n, self.live, self.filled, self.pos = random.Random(seed), -1, 0, {}, {}, 0

    def new(self):
        self.n += 1
        return f"o{self.n}"

    def decide(self, bar, fills):
        self.k += 1
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
        rows.append((ts(m) if m < 1440 else f"2023-11-15T{(m - 1440) // 60:02d}:{(m - 1440) % 60:02d}:00+00:00",
                     float(op), float(hi), float(lo), float(cl), 1.0))
    return rows


@pytest.mark.parametrize("side", SIDES)
@pytest.mark.parametrize("seed", range(6))
def test_p2_random_strategy_matches(tmp_path, side, seed):
    bars = _walk(seed, 600)
    out = str(tmp_path / side)
    run(bars, Random(seed), side=side, out_dir=out, tick=1.0, meta=META)
    with open(os.path.join(out, f"fills_{side}.csv"), encoding="utf-8") as fh:
        assert len(fh.read().splitlines()) > 20  # 約定が十分にある
    assert refill(bars, out, side) == []


# ================================================================ N 書き換えた記録を通さない
def _base(tmp_path, side="optimistic"):
    rows = [FLAT, B1, B2, A1, A2, FLAT]
    plan = {0: {"r": ROOT, "l1": lv(-100.0), "l2": lv(-200.0),
                "x": {"form": "exit", "side": "sell", "qty": 0.009, "parent": "l1", "px": 6999790.0}},
            1: {"l2": lv(-200.0), "x": {"form": "exit", "side": "sell", "qty": 0.009, "parent": "l1", "px": 6999790.0}},
            2: {"r1": R1, "x1": X1}, 3: {"r2": R2, "x1": X1}, 4: {"m": MKT}}
    out, bars = go(tmp_path, rows, plan, side)
    assert refill(bars, out, side) == []
    return out, bars


def _rw(out, name, fn, side="optimistic"):
    p = os.path.join(out, f"{name}_{side}.csv")
    with open(p, newline="", encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    rows = fn(rows)
    with open(p, "w", newline="", encoding="utf-8") as fh:
        csv.writer(fh, lineterminator="\n").writerows(rows)


def _col(rows, name):
    return rows[0].index(name)


def _fill_moved_to_next_bar(out, bars):
    def fn(rows):
        i = _col(rows, "ts")
        tss = [b[0] for b in bars]
        rows[1][i] = tss[tss.index(rows[1][i]) + 1]
        return rows
    _rw(out, "fills", fn)


def _fill_px_plus_one(out, bars):
    def fn(rows):
        i = _col(rows, "px")
        rows[2][i] = repr(float(rows[2][i]) + 1.0)
        return rows
    _rw(out, "fills", fn)


def _fill_case_changed(out, bars):
    def fn(rows):
        i = _col(rows, "case")
        rows[1][i] = "range" if rows[1][i] != "range" else "open"
        return rows
    _rw(out, "fills", fn)


def _fill_deleted(out, bars):
    _rw(out, "fills", lambda rows: rows[:-1])


def _fill_duplicated(out, bars):
    _rw(out, "fills", lambda rows: rows + [rows[-1]])


def _same_bar_fills_swapped(out, bars):
    def fn(rows):
        i = _col(rows, "ts")
        for k in range(1, len(rows) - 1):
            if rows[k][i] == rows[k + 1][i]:
                rows[k], rows[k + 1] = rows[k + 1], rows[k]
                return rows
        raise AssertionError("同じ足の約定が無い")
    _rw(out, "fills", fn)


def _px_text_changed(out, bars):
    def fn(rows):
        i = _col(rows, "px")
        rows[1][i] = rows[1][i] + "0"  # 6999800.0 → 6999800.00(値は同じ、書き方が違う)
        return rows
    _rw(out, "fills", fn)


def _order_px_calc_changed(out, bars):
    def fn(rows):
        i, f = _col(rows, "px_calc"), _col(rows, "form")
        for row in rows[1:]:
            if row[f] == "limit":
                row[i] = repr(float(row[i]) - 1000.0)
                return rows
        raise AssertionError("指値の行が無い")
    _rw(out, "orders", fn)


def _order_from_ts_later(out, bars):
    # 段に付けた利確の from_ts を親の約定の足より後にずらす(親の足の扱いが変わり、作り直しでは約定の足が変わる)
    def fn(rows):
        i, f, k = _col(rows, "from_ts"), _col(rows, "form"), _col(rows, "id")
        tss = [b[0] for b in bars]
        for row in rows[1:]:
            if row[f] == "exit" and row[k] == "x":
                row[i] = tss[tss.index(row[i]) + 1]
                return rows
        raise AssertionError("利確 x の行が無い")
    _rw(out, "orders", fn)


def _order_row_deleted(out, bars):
    def fn(rows):
        k = _col(rows, "id")
        return [r for r in rows if r[k] != "r"]
    _rw(out, "orders", fn)


def _run_json_tick_changed(out, bars):
    p = os.path.join(out, "run_optimistic.json")
    with open(p, encoding="utf-8") as fh:
        rec = json.load(fh)
    rec["tick"] = 1000.0
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(rec, fh)


def _run_json_missing(out, bars):
    os.remove(os.path.join(out, "run_optimistic.json"))


def _fills_not_utf8(out, bars):
    with open(os.path.join(out, "fills_optimistic.csv"), "wb") as fh:
        fh.write(b"\xff\xfe\x00garbage")


def _orders_garbage(out, bars):
    with open(os.path.join(out, "orders_optimistic.csv"), "w", encoding="utf-8") as fh:
        fh.write("garbage\n1,2,3\n")


TAMPERS = [
    ("約定を次の足にずらす", _fill_moved_to_next_bar),
    ("約定の値段を 1 円上げる", _fill_px_plus_one),
    ("case を変える", _fill_case_changed),
    ("約定の行を消す", _fill_deleted),
    ("約定の行を 2 重にする", _fill_duplicated),
    ("同じ足の約定の順を入れ替える", _same_bar_fills_swapped),
    ("値段の書き方だけを変える", _px_text_changed),
    ("注文の戦略の値段を変える", _order_px_calc_changed),
    ("利確の from_ts をずらす", _order_from_ts_later),
    ("注文の行を消す", _order_row_deleted),
    ("run の刻みを変える", _run_json_tick_changed),
    ("run の記録が無い", _run_json_missing),
    ("fills が UTF-8 でない", _fills_not_utf8),
    ("orders がでたらめ", _orders_garbage),
]


@pytest.mark.parametrize("name,tamper", TAMPERS, ids=[t[0] for t in TAMPERS])
def test_n1_tampered_records_are_caught(tmp_path, name, tamper):
    out, bars = _base(tmp_path)
    tamper(out, bars)
    got = refill(bars, out, "optimistic")  # 例外を出さない
    assert isinstance(got, list) and got != [] and all(isinstance(x, str) for x in got)


def test_n2_other_bars_are_caught(tmp_path):
    # 走らせに渡したのと違う足(1 本の高値を変えた足)では食い違う
    out, bars = _base(tmp_path)
    bad = list(bars)
    t, op, hi, lo, cl, v = bad[2]
    bad[2] = (t, op, hi, lo + 200.0, cl, v)  # 安値を上げて、段 l2(6,999,600)が足 2 で約定しなくなる
    assert refill(bad, out, "optimistic") != []


def test_n3_side_mismatch_is_caught(tmp_path):
    # 良い側の記録を悪い側として作り直すと食い違う(run_<側>.json の side と、ファイルの名前の側)
    out, bars = _base(tmp_path)
    for name in ("orders", "fills"):
        os.rename(os.path.join(out, f"{name}_optimistic.csv"), os.path.join(out, f"{name}_pessimistic.csv"))
    os.rename(os.path.join(out, "run_optimistic.json"), os.path.join(out, "run_pessimistic.json"))
    assert refill(bars, out, "pessimistic") != []


# ================================================================ P3 足は 1 回だけ前から読む(全部を記憶に持たない)
@pytest.mark.parametrize("side", SIDES)
def test_p3_bars_read_once_from_iterator(tmp_path, side):
    # 測る期間は約 423 万本。足を並びにして持たず、1 回だけ前から読む形でも作り直せる(生成器を渡す)
    bars = _walk(7, 400)
    out = str(tmp_path / side)
    run(bars, Random(7), side=side, out_dir=out, tick=1.0, meta=META)
    assert refill((b for b in bars), out, side) == []


class _Idle:
    def decide(self, bar, fills):
        return {}, []


def _idle_bars(n):
    from datetime import datetime, timedelta, timezone
    t0 = datetime(2020, 1, 1, tzinfo=timezone.utc)
    return (((t0 + timedelta(minutes=k)).isoformat(), 7e6, 7e6, 7e6, 7e6, 1.0) for k in range(n))


def _refill_peak(tmp_path, n):
    import tracemalloc
    out = str(tmp_path / f"idle{n}")
    run(_idle_bars(n), _Idle(), side="optimistic", out_dir=out, tick=1.0, meta=META)
    tracemalloc.start()
    try:
        assert refill(_idle_bars(n), out, "optimistic") == []
        return tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()


def test_p4_bars_are_not_kept(tmp_path):
    # 足 1 本あたりの記憶の増え方が 50 バイト未満(足を並びにして全部持つと 1 本あたり数百バイト)
    a, b = _refill_peak(tmp_path, 2000), _refill_peak(tmp_path, 12000)
    assert (b - a) / 10000 < 50, (a, b)
