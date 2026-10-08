"""単純な測りの道の走らせ(bot.bt.simple)の受け入れの試験。

リードが書いた(決まりの正本は docs/DISCUSSIONS/2026-10-08_simple_road/SPEC.md、場面の表は simple_scenes.py)。作業者は試験を変えずに通す。
L-831 で、S1・S1 の直し・直し 2 の 3 つの試験のファイルを、表を回す試験にまとめ、重なる場面を消した。

オーナーの逐語: L-819「**測定方法も残し方も検査もシンプルにできるはず**」/ L-821「**1.よい 2.よい**」/
L-754「**私がしてほしいの決まりを足すんじゃなくて、この計算が確実にできるツールを作ることと、そのツールが必ず使われる仕組みです。**」

口(この試験が決める):
- `from bot.bt.simple import run, read_bars, SimpleRoadError`
- `run(bars, strategy, side, out_dir, tick, meta)`: bars は (足の始まりの時刻の文字列, 始値, 高値, 安値, 終値, 出来高) の並び。
  side は "optimistic" か "pessimistic"。out_dir に SPEC §4 のファイル(約定・合図・まとめ・走らせの記録)を書く。
  meta は run_<側>.json に写す辞書。注文の記録は書かない(L-851)。
- 戦略は `decide(bar, fills)` を持ち、(注文の辞書 {番号: 注文}, 合図の出来事の並び) を返す。止める場面は `SimpleRoadError`。
- `read_bars(paths, seal_iso)`: 1 分足のファイル(CSV.gz)を読み、値段の空の足を飛ばし、封印の境の行で終わる。
"""
from __future__ import annotations

import csv
import gzip
import json
import os
import tempfile
import tracemalloc
from datetime import datetime, timedelta, timezone

import pytest

from bot.bt.road.ledger import book
from simple_scenes import (A1, A2, B1, B2, C1, FLAT, M1, META, R1, R2, ROOT, SCENES, SEAL, SIDES, X1, Script, check_all, ex,
                           lim, lv, make_bars, table, ts)

simple = pytest.importorskip("bot.bt.simple")
run, read_bars, SimpleRoadError = simple.run, simple.read_bars, simple.SimpleRoadError


def _kind(raw):
    return "close" if raw.get("close") else ("entry" if raw["form"] == "limit" else raw["form"])


# ================================================================ 場面の表(simple_scenes.py)の約定・合図
def test_scenes(tmp_path):
    def one(sc):
        raws = {i: o for plan in sc["plan"].values() for i, o in plan.items()}
        for side in SIDES:
            out = str(tmp_path / f"{SCENES.index(sc)}" / side)
            st = Script(sc["plan"], sc.get("signals"))
            run(make_bars(sc["rows"], sc.get("minutes")), st, side=side, out_dir=out, tick=sc.get("tick", 1.0), meta=META)
            want = sc["fills"][side] if isinstance(sc["fills"], dict) else sc["fills"]
            assert st.got == [(ts(k), i, float(px), c) for k, i, px, c in want], (side, st.got)
            # 約定のファイルは戦略に届いた約定と同じ順・同じ値段で、番号の代わりに注文の種類を書く
            rows = table(out, "fills", side)
            assert [(r["ts"], r["kind"], float(r["px"]), r["case"]) for r in rows] == [
                (t, _kind(raws[i]), px, c) for t, i, px, c in st.got], (side, rows)
            if "seen" in sc:
                assert st.seen == sc["seen"], (side, st.seen)
            for want_row, r in zip(sc.get("signal_rows", []), table(out, "signals", side)):
                assert {c: r[c] for c in want_row} == want_row, (side, r)
    check_all(SCENES, one)


# ================================================================ 止める場面(SimpleRoadError)
UP5 = (7000200, 7000300, 7000100, 7000200)
X = ex("r", 7000100.0)
STOPS = [
    ("同じ番号で中身が違う", [FLAT, UP5, FLAT], {0: {"r": ROOT}, 1: {"r": dict(ROOT, px=7000040.0)}}),
    ("約定した番号をまた返す", [FLAT, B1, B2], {0: {"r": ROOT}, 1: {"r": ROOT}}),
    ("消えた番号をまた返す", [FLAT, UP5, FLAT, FLAT], {0: {"r": ROOT}, 2: {"r": ROOT}}),
    ("根の無い段", [FLAT, B1], {0: {"l1": lv(-100.0)}}),
    ("親の無い利確", [FLAT, B1], {0: {"x": dict(X, parent="zz")}}),
    ("根が約定した後に初めて出た段", [FLAT, B1, B2], {0: {"r": ROOT}, 1: {"l1": lv(-100.0)}}),
    ("根を約定の前に取り下げ段だけ残す", [FLAT, (7000100,) * 4, FLAT], {0: {"r1": R1, "l1": lv(-100.0, root="r1")}, 1: {"l1": lv(-100.0, root="r1")}}),
    ("親を約定の前に取り下げ利確だけ残す", [FLAT, (7000100,) * 4, FLAT], {0: {"r1": R1, "x1": X1}, 1: {"x1": X1}}),
    ("段の距離の向きが違う", [FLAT, B1], {0: {"r": ROOT, "l1": lv(100.0)}}),
    ("段の売買が根と違う", [FLAT, B1], {0: {"r": ROOT, "l1": lv(100.0, side="sell")}}),
    ("根が段の段", [FLAT, B1], {0: {"r": ROOT, "l1": lv(-100.0), "l2": lv(-100.0, root="l1")}}),
    ("親が成行の利確", [FLAT, B1], {0: {"m": M1, "x": dict(X, parent="m")}}),
    ("売買が親と同じ利確", [FLAT, B1], {0: {"r": ROOT, "x": dict(X, side="buy")}}),
    ("量が親と違う利確", [FLAT, B1], {0: {"r": ROOT, "x": dict(X, qty=0.018)}}),
    ("量が刻みの外", [FLAT, B1], {0: {"r": dict(ROOT, qty=0.0095)}}),
    ("量が 0", [FLAT, B1], {0: {"r": dict(ROOT, qty=0.0)}}),
    ("知らない形", [FLAT, B1], {0: {"r": dict(ROOT, form="stop")}}),
    ("利確に close の印", [FLAT, FLAT], {0: {"r1": R1, "x1": dict(X1, close=True)}}),
    ("成行に close の印", [FLAT, FLAT], {0: {"m1": dict(M1, close=True)}}),
    ("close の印が false", [FLAT, FLAT], {0: {"c1": dict(C1, close=False)}}),
    ("close の印が 1", [FLAT, FLAT], {0: {"c1": dict(C1, close=1)}}),
    ("同じ番号で close の印を外す", [FLAT, FLAT, FLAT],
     {0: {"c1": dict(C1, px=7000500.0)}, 1: {"c1": lim("sell", 7000500.0)}}),
    ("安値が高値より上の足", [FLAT, (7000000, 6999000, 7001000, 7000000)], {}),
    ("封印の境以後に始まる足", None, {}),
]


def test_stops(tmp_path):
    def one(case):
        name, rows, plan = case
        bars = make_bars(rows) if rows else [("2023-12-17T14:59:00+00:00", 7e6, 7e6, 7e6, 7e6, 1.0),
                                             (SEAL, 7e6, 7e6, 7e6, 7e6, 1.0)]
        with pytest.raises(SimpleRoadError):
            run(bars, Script(plan, raw=True), side="optimistic", out_dir=str(tmp_path / name), tick=1.0, meta=META)
    check_all(STOPS, one)


# ================================================================ 足のファイルの読み(封印の境)
def _bar_file(path, lines):
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        fh.write("ts,open,high,low,close,volume,col7_inferred_long_oi,col8_inferred_short_oi,buy_volume,sell_volume\n")
        for line in lines:
            fh.write(line + "\n")
    return str(path)


def test_read_bars(tmp_path):
    # 値段の空の 14:59 を飛ばし、封印の境 15:00 の行で終わる。境の行の次は時刻も読めない壊れた行(読み続ければ落ちる)
    p = _bar_file(tmp_path / "candles_1m_2023.csv.gz", ["2023-12-17T14:58:00+00:00,100.0,101.0,99.0,100.5,1.5,,,,",
                                                         "2023-12-17T14:59:00+00:00,,,,,0.0,,,,",
                                                         "2023-12-17T15:00:00+00:00,100.0,100.0,100.0,100.0,1.0,,,,",
                                                         "時刻でない,壊れた,行,,,,,,,"])
    assert list(read_bars([p], SEAL)) == [("2023-12-17T14:58:00+00:00", 100.0, 101.0, 99.0, 100.5, 1.5)]
    # 封印の境より後の年のファイルは、中身が境より前でも開かずに止める
    q = _bar_file(tmp_path / "candles_1m_2024.csv.gz", ["2023-01-01T00:00:00+00:00,1,1,1,1,1,,,,"])
    with pytest.raises(SimpleRoadError):
        list(read_bars([q], SEAL))
    # 安値 > 高値の行で止める
    (tmp_path / "bad").mkdir()
    b = _bar_file(tmp_path / "bad" / "candles_1m_2023.csv.gz", ["2023-12-17T14:58:00+00:00,100.0,99.0,101.0,100.0,1.5,,,,"])
    with pytest.raises(SimpleRoadError):
        list(read_bars([b], SEAL))


# ================================================================ 残すファイル(SPEC.md §4)
def test_files(tmp_path):
    # 足 0 で合図 s1 を出し、買い 7,000,050(足 1 で始値 6,999,800)、足 2 で成行の売り(足 3 の始値 7,000,000)。取引 1 回
    plan = {0: {"r": ROOT}, 2: {"m": {"form": "market", "side": "sell", "qty": 0.009}}}
    sig = {0: [{"op": "start", "id": "s1", "kind": "試験", "direction": "long", "value": {"a": 1}}],
           2: [{"op": "end", "id": "s1", "reason": "試験の終わり"}]}
    out = str(tmp_path / "f")
    run(make_bars([FLAT, B1, B2, FLAT]), Script(plan, sig), side="optimistic", out_dir=out, tick=1.0, meta=META)
    s = table(out, "signals", "optimistic")
    assert [(r["id"], r["kind"], r["direction"], r["start_ts"], r["end_ts"], r["end_reason"]) for r in s] == [
        ("s1", "試験", "long", ts(0), ts(2), "試験の終わり")]
    with open(os.path.join(out, "run_optimistic.json"), encoding="utf-8") as fh:
        rec = json.load(fh)
    assert {"strategy", "params", "seal", "tick", "side", "git"} <= set(rec)
    assert sorted(os.listdir(out)) == ["fills_optimistic.csv", "run_optimistic.json", "signals_optimistic.csv",
                                       "summary_optimistic.json"]
    with open(os.path.join(out, "fills_optimistic.csv"), encoding="utf-8") as fh:
        assert fh.read() == ("ts,kind,side,qty,px,case\n" f"{ts(1)},entry,buy,0.009,6999800,open\n"
                             f"{ts(3)},market,sell,0.009,7000000,market\n")
    # まとめは、約定のファイルを建玉が 0 に戻るまでの塊に分けて数えた数が、全部を帳簿のツールに 1 回で渡した数と同じ
    #   (取引 1 回が閉じ 1 回が途中)
    base = str(tmp_path / "base")
    run(make_bars([FLAT, A1, A2]), Script({0: {"r1": R1}, 1: {"r2": R2, "x1": X1}}), side="optimistic", out_dir=base,
        tick=1.0, meta=META)
    fills = [{"t_ns": int(datetime.fromisoformat(r["ts"]).timestamp()) * 10**9, "side": r["side"], "qty": float(r["qty"]),
              "px": float(r["px"]), "ccy": "JPY"} for r in table(base, "fills", "optimistic")]
    whole = {k: v for k, v in book(fills).summary.items() if k != "trades"}
    with open(os.path.join(base, "summary_optimistic.json"), encoding="utf-8") as fh:
        assert json.load(fh) == whole and whole["closed_trades"] == 1 and whole["open_trades"] == 1
    # 同じディレクトリで走らせ直しても前の中身を残さない。良い側と悪い側は同じディレクトリに別々に残る
    same = str(tmp_path / "same")
    for side in ("optimistic", "optimistic", "pessimistic"):
        run(make_bars([FLAT, B1]), Script({0: {"r": ROOT}}), side=side, out_dir=same, tick=1.0, meta=META)
    for side in SIDES:
        assert [r["kind"] for r in table(same, "fills", side)] == ["entry"]
        with open(os.path.join(same, f"run_{side}.json"), encoding="utf-8") as fh:
            assert json.load(fh)["side"] == side


# ================================================================ 消えた注文を記憶に持ち続けない
class _Churn:
    """足ごとに新しい番号で約定しない買い指値(1 円)を 1 つ出す。前の足の注文は返さないので消える。"""

    def __init__(self):
        self.k = 0

    def decide(self, bar, fills):
        self.k += 1
        return {f"o{self.k:09d}": {"form": "limit", "side": "buy", "qty": 0.001, "px": 1.0}}, []


def _peak(n):
    t0 = datetime(2020, 1, 1, tzinfo=timezone.utc)
    rows = (((t0 + timedelta(minutes=k)).isoformat(), 7e6, 7e6, 7e6, 7e6, 1.0) for k in range(n))
    with tempfile.TemporaryDirectory() as d:
        tracemalloc.start()
        try:
            run(rows, _Churn(), side="optimistic", out_dir=d, tick=1.0, meta=META)
            return tracemalloc.get_traced_memory()[1]
        finally:
            tracemalloc.stop()


def test_gone_orders_are_not_kept():
    # 消えた注文 1 つあたりの記憶の増え方が 200 バイト未満(番号の集合だけを持つ形で約 100 バイト、
    #   注文の中身を全部持つ形で約 450 バイトだった。リードが捨てる実装で測った値)
    a, b = _peak(2000), _peak(12000)
    assert (b - a) / 10000 < 200, (a, b)
