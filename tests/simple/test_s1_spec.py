"""単純な測りの道 S1(走らせ・約定・残し方・数の作り直し)の受け入れの試験。

リードが書いた(委任文 docs/DISCUSSIONS/2026-10-08_simple_road/DELEGATION_s1.md、決まりの正本は同じ置き場の SPEC.md)。
作業者は試験を変えずに通す(変えたいときは問いとして返す)。期待の値は全部、足の値から手で計算した(各場面の注)。

オーナーの逐語: L-819「**測定方法も残し方も検査もシンプルにできるはず**」/ L-821「**1.よい 2.よい**」/
L-816「**1.a**」/ L-817「**問い 2(B-1) a**」/ L-783「**間違えそうやから小数点以下は切り捨ててください**」

口(この試験が決める):
- `from bot.bt.simple import run, read_bars, check_numbers, SimpleRoadError`
- `run(bars, strategy, side, out_dir, tick, meta)`: bars は (足の始まりの時刻の文字列, 始値, 高値, 安値, 終値, 出来高) の並び。
  side は "optimistic" か "pessimistic"。out_dir に SPEC §4 のファイルを書く。meta は run.json に写す辞書。
- 戦略は `decide(bar, fills)` を持つ。bar は渡した足の組、fills はこの足の約定の辞書の並び
  ({"ts", "id", "side", "qty", "px", "case"})。返すのは (注文の辞書 {番号: 注文}, 合図の出来事の並び)。
  注文 = {"form": "limit"|"level"|"exit"|"market", "side", "qty", "px"(limit・exit), "root", "offset"(level), "parent"(exit)}。
  合図の出来事 = {"op": "start", "id", "kind", "direction", "value"} か {"op": "end", "id", "reason"}。
- 止める場面は `SimpleRoadError`。
- `read_bars(paths, seal_iso)`: 1 分足のファイル(bitFlyer lightchart の CSV.gz の形)を読み、値段の空の足を飛ばし、
  封印の境以後の足で止める。
- `check_numbers(out_dir, side)`: 帳簿のツールで約定から計算し直した数と、書いた数の食い違いの並び(無ければ空)。
"""
from __future__ import annotations

import csv
import gzip
import json
import os

import pytest

simple = pytest.importorskip("bot.bt.simple")
run, read_bars, check_numbers, SimpleRoadError = simple.run, simple.read_bars, simple.check_numbers, simple.SimpleRoadError

SIDES = ("optimistic", "pessimistic")
SEAL = "2023-12-17T15:00:00+00:00"


def ts(k):
    """足 k(0 から)の始まり。2023-11-14T22:10 から 1 分ずつ。"""
    return f"2023-11-14T22:{10 + k:02d}:00+00:00"


def bars(rows):
    return [(ts(k),) + tuple(float(x) for x in r) + (1.0,) for k, r in enumerate(rows)]


class Script:
    """足 k の判定で plan[k] の注文を返す(無い k は何も出さない)。ただし約定し終えた番号は返さない(raw なら返す)。
    受けた約定を残す。"""

    def __init__(self, plan, signals=None, raw=False):
        self.plan, self.signals, self.raw, self.k, self.seen, self.done = plan, signals or {}, raw, -1, [], set()

    def decide(self, bar, fills):
        self.k += 1
        self.seen.append((bar[0], [dict(f) for f in fills]))
        self.done |= {f["id"] for f in fills}
        orders = {i: o for i, o in self.plan.get(self.k, {}).items() if self.raw or i not in self.done}
        return orders, list(self.signals.get(self.k, []))


def go(tmp_path, rows, plan, side, signals=None, tick=1.0, raw=False):
    out = tmp_path / side
    st = Script(plan, signals, raw)
    run(bars(rows), st, side=side, out_dir=str(out), tick=tick, meta={"strategy": "試験", "params": {}})
    return out, st


def table(out, name, side):
    with open(os.path.join(out, f"{name}_{side}.csv"), newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def fills(out, side):
    return [(r["ts"], r["id"], r["px"], r["case"]) for r in table(out, "fills", side)]


FLAT = (7000000, 7000000, 7000000, 7000000)
B1 = (6999800, 6999850, 6999700, 6999750)  # L-816 の例の足: 始値 6,999,800・高値 6,999,850・安値 6,999,700
B2 = (6999750, 6999800, 6999550, 6999600)
ROOT = {"form": "limit", "side": "buy", "qty": 0.009, "px": 7000050.0}


def lv(off, root="r"):
    return {"form": "level", "side": "buy", "qty": 0.009, "root": root, "offset": off}


# ================================================================ T1 段の約定(L-816 の例)
@pytest.mark.parametrize("side", SIDES)
def test_t1_levels_from_root_fill(tmp_path, side):
    # 足 0 の判定で 根 r = 買い 7,000,050、段 l1 = 根 −100、段 l2 = 根 −200。
    # 足 1: 根 > 高値 6,999,850 → 始値 6,999,800(open)。l1 = 6,999,700 = 安値 → 同じ足で 6,999,700(anchor_bar)。
    #   l2 = 6,999,600 < 安値 → 約定しない。足 1 の判定で l2 だけを返し続ける(r・l1 は約定し終えた)。
    # 足 2(安値 6,999,550): l2 6,999,600 は範囲の内 → 6,999,600(range)
    plan = {0: {"r": ROOT, "l1": lv(-100.0), "l2": lv(-200.0)}, 1: {"l2": lv(-200.0)}}
    out, st = go(tmp_path, [FLAT, B1, B2], plan, side)
    assert fills(out, side) == [(ts(1), "r", "6999800.0", "open"), (ts(1), "l1", "6999700.0", "anchor_bar"),
                                (ts(2), "l2", "6999600.0", "range")]
    # 戦略には足 1 の判定で r と l1 の約定、足 2 の判定で l2 の約定が届く
    assert [[f["id"] for f in fs] for _, fs in st.seen] == [[], ["r", "l1"], ["l2"]]
    rows = {r["id"]: r for r in table(out, "orders", side)}
    assert {k: (r["form"], r["px_calc"], r["px"], r["root"], r["offset"], r["from_ts"], r["to_ts"])
            for k, r in rows.items()} == {
        "r": ("limit", "7000050.0", "7000050.0", "", "", ts(1), ts(1)),
        "l1": ("level", "", "6999700.0", "r", "-100.0", ts(1), ts(1)),
        "l2": ("level", "", "6999600.0", "r", "-200.0", ts(1), ts(2))}


# ================================================================ T2 刻みの切り捨てと 10 進の和
@pytest.mark.parametrize("side", SIDES)
def test_t2_buy_level_floored(tmp_path, side):
    # 段 = 6,999,800 − 100.5 = 6,999,699.5 → 切り捨て 6,999,699 < 足 1 の安値 6,999,700 → 足 1 では約定しない
    #   (切り上げると約定する)。足 2(安値 6,999,550)で 6,999,699(range)
    plan = {0: {"r": ROOT, "l1": lv(-100.5)}, 1: {"l1": lv(-100.5)}}
    out, _ = go(tmp_path, [FLAT, B1, B2], plan, side)
    assert fills(out, side) == [(ts(1), "r", "6999800.0", "open"), (ts(2), "l1", "6999699.0", "range")]


@pytest.mark.parametrize("side", SIDES)
def test_t2_sell_level_floored(tmp_path, side):
    # 売り: 根 = 売り 6,999,950。足 1 = (7,000,200, 7,000,300, 7,000,150, 7,000,250): 根 < 安値 → 始値 7,000,200(open)。
    #   段 = 7,000,200 + 100.5 = 7,000,300.5 → 切り捨て 7,000,300 = 高値 → 同じ足で 7,000,300(anchor_bar)
    plan = {0: {"r": {"form": "limit", "side": "sell", "qty": 0.01, "px": 6999950.0},
                "l1": {"form": "level", "side": "sell", "qty": 0.01, "root": "r", "offset": 100.5}}}
    out, _ = go(tmp_path, [FLAT, (7000200, 7000300, 7000150, 7000250)], plan, side)
    assert fills(out, side) == [(ts(1), "r", "7000200.0", "open"), (ts(1), "l1", "7000300.0", "anchor_bar")]


@pytest.mark.parametrize("side", SIDES)
def test_t2_decimal_sum(tmp_path, side):
    # 距離 −1e-10: 浮動小数の和 6,999,800 − 1e-10 は 6,999,800.0(刻みの間隔より小さい差が消える)、10 進の和は
    #   6,999,799.9999999999 → 切り捨て 6,999,799。足 1 の範囲の内 → 6,999,799(anchor_bar)
    plan = {0: {"r": ROOT, "l1": lv(-1e-10)}}
    out, _ = go(tmp_path, [FLAT, B1], plan, side)
    assert fills(out, side)[1] == (ts(1), "l1", "6999799.0", "anchor_bar")


@pytest.mark.parametrize("side", SIDES)
def test_t2_limit_floored_and_calc_kept(tmp_path, side):
    # 戦略の出した値段 6,999,750.7 → 切り捨て 6,999,750(範囲の内)。注文の行に両方を残す
    plan = {0: {"a": {"form": "limit", "side": "buy", "qty": 0.009, "px": 6999750.7}}}
    out, _ = go(tmp_path, [FLAT, B1], plan, side)
    assert fills(out, side) == [(ts(1), "a", "6999750.0", "range")]
    assert [(r["px_calc"], r["px"]) for r in table(out, "orders", side)] == [("6999750.7", "6999750.0")]


# ================================================================ T3 指値・成行の決まり
@pytest.mark.parametrize("side", SIDES)
def test_t3_limit_cases_and_market(tmp_path, side):
    # 足 1 = B1(始 6,999,800・高 6,999,850・安 6,999,700):
    #   a 買い 6,999,000 < 安値 → 約定しない(足 1 の判定で返さない → 消える)。
    #   b 売り 6,999,900 > 高値 → 約定しない。
    #   c 売り 6,999,600 < 安値 → 約定する向きに外 → 始値 6,999,800(open)。
    #   m 成行の売り → 始値 6,999,800(market)
    plan = {0: {"a": {"form": "limit", "side": "buy", "qty": 0.009, "px": 6999000.0},
                "b": {"form": "limit", "side": "sell", "qty": 0.009, "px": 6999900.0},
                "c": {"form": "limit", "side": "sell", "qty": 0.009, "px": 6999600.0},
                "m": {"form": "market", "side": "sell", "qty": 0.009}}}
    out, _ = go(tmp_path, [FLAT, B1, B2], plan, side)
    assert fills(out, side) == [(ts(1), "m", "6999800.0", "market"), (ts(1), "c", "6999800.0", "open")]
    rows = {r["id"]: (r["from_ts"], r["to_ts"]) for r in table(out, "orders", side)}
    assert rows == {"a": (ts(1), ts(1)), "b": (ts(1), ts(1)), "c": (ts(1), ts(1)), "m": (ts(1), ts(1))}


# ================================================================ T4 付けた利確(良い側・悪い側)
def test_t4_exit_on_level(tmp_path):
    # 段 l1 = 根 −100(6,999,700)に利確 x = 売り 6,999,800。足 1: 根 6,999,800(open)→ l1 6,999,700(anchor_bar)。
    #   良い側: x は足 1 の範囲の内 → 足 1 で 6,999,800(entry_bar)。
    #   悪い側: 足 2 = (6,999,750, 6,999,850, 6,999,700, 6,999,800) の範囲の内 → 足 2 で 6,999,800(range)
    x = {"form": "exit", "side": "sell", "qty": 0.009, "parent": "l1", "px": 6999800.0}
    plan = {0: {"r": ROOT, "l1": lv(-100.0), "x": x}, 1: {"x": x}}
    rows = [FLAT, B1, (6999750, 6999850, 6999700, 6999800)]
    opt, _ = go(tmp_path, rows, plan, "optimistic")
    pes, _ = go(tmp_path, rows, plan, "pessimistic")
    assert fills(opt, "optimistic")[2] == (ts(1), "x", "6999800.0", "entry_bar")
    assert fills(pes, "pessimistic")[2] == (ts(2), "x", "6999800.0", "range")


def test_t4_exit_after_parent_filled_is_plain_limit(tmp_path):
    # 利確 x を、親 r が約定した後(足 1 の判定)に初めて出す。良い側でも足 1 では試さず、足 2 から limit の決まり。
    #   足 2 = B2(高値 6,999,800): x 売り 6,999,800 = 高値 → 範囲の内 → 6,999,800(range)
    x = {"form": "exit", "side": "sell", "qty": 0.009, "parent": "r", "px": 6999800.0}
    plan = {0: {"r": ROOT}, 1: {"x": x}}
    out, _ = go(tmp_path, [FLAT, B1, B2], plan, "optimistic")
    assert fills(out, "optimistic") == [(ts(1), "r", "6999800.0", "open"), (ts(2), "x", "6999800.0", "range")]


# ================================================================ T5 根を消す・段を消す
@pytest.mark.parametrize("side", SIDES)
def test_t5_root_and_level_withdrawn(tmp_path, side):
    # 足 1 = UP(7,000,200, 7,000,300, 7,000,100, 7,000,200): 根 7,000,050 < 安値 → 約定しない。
    #   足 1 の判定で何も返さない → r と l1 は消える。l1 の値段は決まらない(px 空)
    UP = (7000200, 7000300, 7000100, 7000200)
    plan = {0: {"r": ROOT, "l1": lv(-100.0)}}
    out, _ = go(tmp_path, [FLAT, UP, B1], plan, side)
    assert fills(out, side) == []
    rows = {r["id"]: (r["px"], r["from_ts"], r["to_ts"]) for r in table(out, "orders", side)}
    assert rows == {"r": ("7000050.0", ts(1), ts(1)), "l1": ("", ts(1), ts(1))}


# ================================================================ T6 欠けた足と値段の空の足
@pytest.mark.parametrize("side", SIDES)
def test_t6_next_bar_is_next_present_bar(tmp_path, side):
    # 足 0(22:10)の次の足は 22:13(22:11・22:12 はデータに無い)。注文は 22:13 の足で約定する
    rows = [(ts(0), 7e6, 7e6, 7e6, 7e6, 1.0), (ts(3),) + tuple(float(x) for x in B1) + (1.0,)]
    st = Script({0: {"r": ROOT}})
    out = tmp_path / side
    run(rows, st, side=side, out_dir=str(out), tick=1.0, meta={})
    assert fills(out, side) == [(ts(3), "r", "6999800.0", "open")]
    assert [(r["from_ts"], r["to_ts"]) for r in table(out, "orders", side)] == [(ts(3), ts(3))]


def _bar_file(tmp_path, lines):
    p = tmp_path / "candles_1m_2023.csv.gz"
    with gzip.open(p, "wt", encoding="utf-8") as fh:
        fh.write("ts,open,high,low,close,volume,col7_inferred_long_oi,col8_inferred_short_oi,buy_volume,sell_volume\n")
        for line in lines:
            fh.write(line + "\n")
    return str(p)


def test_t6_read_bars_skips_null_and_stops_at_seal(tmp_path):
    p = _bar_file(tmp_path, ["2023-12-17T14:58:00+00:00,100.0,101.0,99.0,100.5,1.5,,,,",
                             "2023-12-17T14:59:00+00:00,,,,,0.0,,,,",
                             "2023-12-17T15:00:00+00:00,100.0,100.0,100.0,100.0,1.0,,,,"])
    got = []
    with pytest.raises(SimpleRoadError):
        for b in read_bars([p], SEAL):
            got.append(b)
    assert got == [("2023-12-17T14:58:00+00:00", 100.0, 101.0, 99.0, 100.5, 1.5)]


def test_t6_read_bars_refuses_files_after_seal_year(tmp_path):
    # 封印の境より後の年のファイル(candles_1m_2024.csv.gz 以降)は開かずに止める(中身は封印の境より前でも)
    p = tmp_path / "candles_1m_2024.csv.gz"
    with gzip.open(p, "wt", encoding="utf-8") as fh:
        fh.write("ts,open,high,low,close,volume\n2023-01-01T00:00:00+00:00,1,1,1,1,1\n")
    with pytest.raises(SimpleRoadError):
        list(read_bars([str(p)], SEAL))


# ================================================================ T7 止める場面
X = {"form": "exit", "side": "sell", "qty": 0.009, "parent": "r", "px": 7000100.0}
STOPS = [
    ("同じ番号で中身が違う", {0: {"r": ROOT}, 1: {"r": dict(ROOT, px=7000040.0)}}, [FLAT, (7000200, 7000300, 7000100, 7000200), FLAT]),
    ("約定した番号をまた返す", {0: {"r": ROOT}, 1: {"r": ROOT}}, [FLAT, B1, B2]),
    ("根の無い段", {0: {"l1": lv(-100.0)}}, [FLAT, B1]),
    ("親の無い利確", {0: {"x": dict(X, parent="zz")}}, [FLAT, B1]),
    ("根が約定した後に初めて出た段", {0: {"r": ROOT}, 1: {"l1": lv(-100.0)}}, [FLAT, B1, B2]),
    ("段の距離の向きが違う", {0: {"r": ROOT, "l1": lv(100.0)}}, [FLAT, B1]),
    ("段の売買が根と違う", {0: {"r": ROOT, "l1": dict(lv(-100.0), side="sell")}}, [FLAT, B1]),
    ("量が刻みの外", {0: {"r": dict(ROOT, qty=0.0095)}}, [FLAT, B1]),
    ("量が 0", {0: {"r": dict(ROOT, qty=0.0)}}, [FLAT, B1]),
    ("知らない形", {0: {"r": dict(ROOT, form="stop")}}, [FLAT, B1]),
]


@pytest.mark.parametrize("name,plan,rows", STOPS, ids=[s[0] for s in STOPS])
def test_t7_stops(tmp_path, name, plan, rows):
    with pytest.raises(SimpleRoadError):
        go(tmp_path, rows, plan, "optimistic", raw=True)


# ================================================================ T8 残し方と数の作り直し(L-754)
def test_t8_files_signals_and_numbers(tmp_path):
    # 足 0 で合図 s1 を出し、買い 7,000,050(足 1 で始値 6,999,800)、足 1 で利確の売り 6,999,900(足 2 の範囲の外 = 高値 6,999,800
    #   より上で約定しない)、足 2 で成行の売り(足 3 の始値 7,000,000)。取引 1 回: 0.009 × (7,000,000 − 6,999,800) = +1.8 円
    plan = {0: {"r": ROOT}, 1: {"x": dict(X, px=6999900.0)}, 2: {"m": {"form": "market", "side": "sell", "qty": 0.009}}}
    sig = {0: [{"op": "start", "id": "s1", "kind": "試験", "direction": "long", "value": {"a": 1}}],
           2: [{"op": "end", "id": "s1", "reason": "試験の終わり"}]}
    out, _ = go(tmp_path, [FLAT, B1, B2, FLAT], plan, "optimistic", signals=sig)
    assert fills(out, "optimistic") == [(ts(1), "r", "6999800.0", "open"), (ts(3), "m", "7000000.0", "market")]
    s = table(out, "signals", "optimistic")
    assert [(r["id"], r["kind"], r["direction"], r["start_ts"], r["end_ts"], r["end_reason"]) for r in s] == [
        ("s1", "試験", "long", ts(0), ts(2), "試験の終わり")]
    assert json.loads(s[0]["value_json"]) == {"a": 1}
    with open(os.path.join(out, "run.json"), encoding="utf-8") as fh:
        rec = json.load(fh)
    for k in ("strategy", "params", "seal", "tick", "side", "git"):
        assert k in rec, k
    trades = table(out, "trades", "optimistic")
    assert len(trades) == 1
    assert check_numbers(str(out), "optimistic") == []
    # 書いた数を書き換えると食い違いが出る
    with open(os.path.join(out, "summary_optimistic.json"), encoding="utf-8") as fh:
        summ = json.load(fh)
    key = next(k for k, v in summ.items() if isinstance(v, (int, float, str)) and k != "side")
    summ[key] = "999"
    with open(os.path.join(out, "summary_optimistic.json"), "w", encoding="utf-8") as fh:
        json.dump(summ, fh)
    assert check_numbers(str(out), "optimistic") != []


def test_t8_records_are_written_while_running(tmp_path):
    # 注文の行は消えた時・約定した時に書く(走らせの終わりにまとめて持たない)。足 1 の判定の時点で、足 1 で約定した r の行が
    #   ファイルにある
    class Peek(Script):
        def decide(self, bar, fills):
            r = super().decide(bar, fills)
            if self.k == 1:
                p = os.path.join(self.out, "orders_optimistic.csv")
                with open(p, encoding="utf-8") as fh:
                    self.lines = fh.read()
            return r
    st = Peek({0: {"r": ROOT}})
    st.out = str(tmp_path / "o")
    run(bars([FLAT, B1, B2]), st, side="optimistic", out_dir=st.out, tick=1.0, meta={})
    assert "\nr," in st.lines
