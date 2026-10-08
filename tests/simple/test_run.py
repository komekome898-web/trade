"""単純な測りの道 2 版目の走らせ(bot.bt.simple)の受け入れの試験。

決まりの正本は docs/DISCUSSIONS/2026-10-08_simple_road/SPEC.md(2 版目)、場面の表は simple_scenes.py。2 版目の作業者が
1 版目の試験を書き換えた(L-831 の方針: やらなくてもいい試験は消す・重複は消す・分ける必要のないものはまとめる)。

オーナーの逐語: L-819「**測定方法も残し方も検査もシンプルにできるはず**」/ L-821「**1.よい 2.よい**」/
L-882「**口の案はそれでよい**」/ L-851「**注文の履歴いらないわ、約定の履歴だけでいい**」

口(この試験が決める):
- `from bot.bt.simple import run, read_bars, SimpleRoadError`
- `run(bars, strategy, out_dir, tick, meta)`: bars は (足の始まりの時刻の文字列, 始値, 高値, 安値, 終値, 出来高) の並び。
  out_dir に SPEC §4 のファイル(fills.csv・signals.csv・summary.json・run.json)を書く。
- 戦略は `decide(ev)` を持ち、(注文の辞書 {番号: 注文}, 合図の出来事の並び, 見張る値段の並び) を返す。止める場面は `SimpleRoadError`。
- `read_bars(paths, seal_iso)`: 1 分足のファイル(CSV.gz)を読み、値段の空の足を飛ばし、封印の境の行で終わる。
"""
from __future__ import annotations

import gzip
import json
import os
import tempfile
import tracemalloc
from datetime import datetime, timedelta, timezone

import pytest

from bot.bt.road.ledger import book
from bot.bt.simple import SimpleRoadError, read_bars, run
from simple_scenes import BULL, META, SCENES, SEAL, Z0, Script, check_all, make_bars, od, table, ts


# ================================================================ 場面の表(simple_scenes.py)の呼び出しと約定(U1・U2・U3)
def test_scenes(tmp_path):
    def one(sc):
        raws = {i: o for p in sc["plan"].values() for i, o in p.get("o", {}).items()}
        out = str(tmp_path / f"{SCENES.index(sc)}")
        st = Script(sc["plan"])
        run(make_bars(sc["rows"]), st, out_dir=out, tick=1.0, meta=META)
        assert st.bad == [], ("ev の形", st.bad)  # "stop" の ev に bar(足の高値・安値・終値)が無い。約定の鍵は SPEC §2.2 のまま
        assert st.calls == sc["calls"], st.calls
        # 約定のファイルは戦略に届いた約定と同じ順・同じ値段・case で、kind は tag(無ければ形の名前)
        got = [(t, i, px, c) for _, t, _, fills, _ in st.calls for i, px, c in fills]
        assert [(r["ts"], r["kind"], float(r["px"]), r["case"]) for r in table(out, "fills")] == [
            (t, raws[i].get("tag", raws[i]["form"]), px, c) for t, i, px, c in got]
    check_all(SCENES, one)


# ================================================================ 止める場面(SimpleRoadError。U3・U4)。場面 = 名前・足・計画・止まる理由の文の一部
Z1, Z2, Z3 = (1002, 1003, 1001, 1003), (1004, 1005, 1003, 1005), (1006, 1007, 1005, 1007)  # どれも約定も到達も起きない足
L900 = od("limit", "buy", 900.0)


def _markets(n):
    """足 1 の 998(見張る値段)で止まり、呼ぶたびに新しい成行を返す(すぐ約定して同じ点で呼び直す)。同じ点で n + 1 回呼ぶ。"""
    plan = {0: {"w": [998]}}
    for k in range(1, n + 1):
        plan[k] = {"o": {f"m{k}": od("market", "buy")}}
    plan[n + 1] = {}
    return plan


STOPS = [
    ("知らない形", [Z0, Z1], {0: {"o": {"r": od("foo", "buy", 900.0)}}}, "知らない形"),
    ("level の形", [Z0, Z1], {0: {"o": {"r": od("level", "buy", 900.0)}}}, "知らない形"),
    ("exit の形", [Z0, Z1], {0: {"o": {"r": od("exit", "sell", 900.0)}}}, "知らない形"),
    ("close の印", [Z0, Z1], {0: {"o": {"r": dict(L900, close=True)}}}, "知らない鍵"),
    ("知らない鍵", [Z0, Z1], {0: {"o": {"r": dict(L900, root="x")}}}, "知らない鍵"),
    ("値段の無い limit", [Z0, Z1], {0: {"o": {"r": od("limit", "buy")}}}, "値段は 0 より大きい数"),
    ("値段の無い stop", [Z0, Z1], {0: {"o": {"r": od("stop", "buy")}}}, "値段は 0 より大きい数"),
    ("値段のある market", [Z0, Z1], {0: {"o": {"r": dict(od("market", "buy"), px=900.0)}}}, "に値段がある"),
    ("量が刻みの外", [Z0, Z1], {0: {"o": {"r": dict(L900, qty=0.0095)}}}, "量は 0 より大きく"),
    ("量が 0", [Z0, Z1], {0: {"o": {"r": dict(L900, qty=0.0)}}}, "量は 0 より大きく"),
    ("tag が文字でない", [Z0, Z1], {0: {"o": {"r": dict(L900, tag=1)}}}, "tag は文字"),
    ("同じ番号で値段が違う", [Z0, Z1, Z2], {0: {"o": {"r": L900}}, 1: {"o": {"r": dict(L900, px=901.0)}}}, "中身が前と違う"),
    ("同じ番号で tag が違う", [Z0, Z1, Z2], {0: {"o": {"r": dict(L900, tag="a")}}, 1: {"o": {"r": dict(L900, tag="b")}}},
     "中身が前と違う"),
    # 足 1 の 999 で約定した r を、その点の呼び出しでまた返す
    ("約定し終えた番号をまた返す", [Z0, BULL], {0: {"o": {"r": od("limit", "buy", 999.0)}}}, "もう一度返した"),
    ("消えた番号をまた返す", [Z0, Z1, Z2, Z3], {0: {"o": {"r": L900}}, 1: {}, 2: {"o": {"r": L900}}}, "もう一度返した"),
    ("同じ点で 101 回目の呼び出し", [Z0, BULL], _markets(100), "回を超えて呼んだ"),
    ("安値が高値より上の足", [Z0, (1000, 999, 1001, 1000)], {}, "安値が高値より高い"),
    ("始値が安値〜高値の外の足", [Z0, (1003, 1002, 1000, 1001)], {}, "安値〜高値の外"),
    ("終値が安値〜高値の外の足", [Z0, (1001, 1002, 1000, 1003)], {}, "安値〜高値の外"),
    # 封印の境の検めは飛ばす足の判定より先(どちらの足も 始値 = 終値 でデータの頭なので、検めが後なら止まらない)
    ("封印の境以後に始まる足", None, {}, "封印の境"),
]


def test_stops(tmp_path):
    def one(case):
        name, rows, plan, why = case
        bars = make_bars(rows) if rows else [("2023-12-17T14:59:00+00:00", 7e6, 7e6, 7e6, 7e6, 1.0),
                                             (SEAL, 7e6, 7e6, 7e6, 7e6, 1.0)]
        with pytest.raises(SimpleRoadError, match=why):  # ねらいの理由で止まったか(ほかの理由で止まって通るのを避ける)
            run(bars, Script(plan, raw=True), out_dir=str(tmp_path / name), tick=1.0, meta=META)
    check_all(STOPS, one)
    # 同じ点で 100 回までは止めない(上の 101 回目の場面と 1 回だけ違う)
    st = Script(_markets(99))
    run(make_bars([Z0, BULL]), st, out_dir=str(tmp_path / "100"), tick=1.0, meta=META)
    assert sum(1 for c in st.calls if c[:3] == ("stop", ts(1), 998.0)) == 100


# ================================================================ 足のファイルの読み(封印の境・値段の空の足。U3・U5)
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
    # 安値 > 高値の行、始値か終値が安値〜高値の外の行で止める
    for k, line in enumerate(["100.0,99.0,101.0,100.0", "102.0,101.0,99.0,100.0", "100.0,101.0,99.0,98.0"]):
        (tmp_path / f"bad{k}").mkdir()
        b = _bar_file(tmp_path / f"bad{k}" / "candles_1m_2023.csv.gz", [f"2023-12-17T14:58:00+00:00,{line},1.5,,,,"])
        with pytest.raises(SimpleRoadError):
            list(read_bars([b], SEAL))


# ================================================================ 残すファイル(SPEC.md §4。U5)
def test_files(tmp_path):
    # 足 0 の終値で合図 s1 を始め、買いの limit a(0.002、tag entry)999・売りの limit x(0.001、tag close)1006・
    #   売りの limit y(0.001、tag なし)1009 を出す。足 1(1002 → 995 → 1010 → 1008)で a は 999、x は 1006、y は 1009(path)。
    #   y の点の呼び出し(3)で s1 を終える。足 1 の終値(呼び出し 4)で成行の買い m 0.003 → 足 2 の始値 1010(market)。
    #   取引: 0.002 を 999 で買い、1006 と 1009 で 0.001 ずつ売って閉じる(1 回)。m で建てた玉は途中(1 回)。
    #   x は tag close だが建玉は 0 に戻らない(塊を kind で切ると数が変わる)
    plan = {0: {"o": {"a": od("limit", "buy", 999.0, qty=0.002, tag="entry"), "x": od("limit", "sell", 1006.0, qty=0.001, tag="close"),
                      "y": od("limit", "sell", 1009.0, qty=0.001)}},
            4: {"o": {"m": od("market", "buy", qty=0.003)}}, 5: {}}
    sig = {0: [{"op": "start", "id": "s1", "kind": "試験", "direction": "long", "value": {"a": 1}}],
           3: [{"op": "end", "id": "s1", "reason": "試験の終わり"}]}
    out = str(tmp_path / "f")
    run(make_bars([Z0, BULL, (1010, 1012, 1009, 1011)]), Script(plan, sig), out_dir=out, tick=1.0, meta=META)
    assert sorted(os.listdir(out)) == ["fills.csv", "run.json", "signals.csv", "summary.json"]
    with open(os.path.join(out, "fills.csv"), encoding="utf-8") as fh:
        assert fh.read() == ("ts,kind,side,qty,px,case\n" f"{ts(1)},entry,buy,0.002,999,path\n"
                             f"{ts(1)},close,sell,0.001,1006,path\n" f"{ts(1)},limit,sell,0.001,1009,path\n"
                             f"{ts(2)},market,buy,0.003,1010,market\n")
    assert [(r["id"], r["kind"], r["direction"], r["start_ts"], r["end_ts"], r["end_reason"]) for r in table(out, "signals")] == [
        ("s1", "試験", "long", ts(0), ts(1), "試験の終わり")]
    with open(os.path.join(out, "run.json"), encoding="utf-8") as fh:
        rec = json.load(fh)
    assert {"strategy", "params", "seal", "bar_files", "tick", "git"} == set(rec)
    # まとめは、建玉が 0 に戻るまでの塊に分けて数えた数が、全部を帳簿のツールに 1 回で渡した数と同じ
    fills = [{"t_ns": int(datetime.fromisoformat(r["ts"]).timestamp()) * 10**9, "side": r["side"], "qty": float(r["qty"]),
              "px": float(r["px"]), "ccy": "JPY"} for r in table(out, "fills")]
    whole = {k: v for k, v in book(fills).summary.items() if k != "trades"}
    with open(os.path.join(out, "summary.json"), encoding="utf-8") as fh:
        assert json.load(fh) == whole and whole["closed_trades"] == 1 and whole["open_trades"] == 1
    # 同じディレクトリで走らせ直すと前の中身を残さない(約定の無い走らせ)
    run(make_bars([Z0, BULL]), Script({}), out_dir=out, tick=1.0, meta=META)
    assert table(out, "fills") == [] and table(out, "signals") == []
    with open(os.path.join(out, "summary.json"), encoding="utf-8") as fh:
        assert json.load(fh)["fill_count"] == 0


# ================================================================ 消えた注文を記憶に持ち続けない(SPEC.md §4。U5)
class _Churn:
    """呼ぶたびに新しい番号で約定しない買い指値(1 円)を 1 つ出す。前の注文は返さないので消える。"""

    def __init__(self):
        self.k = 0

    def decide(self, ev):
        self.k += 1
        return {f"o{self.k:09d}": {"form": "limit", "side": "buy", "qty": 0.001, "px": 1.0}}, [], []


def _peak(n):
    # 足は全部 始値 7,000,000・終値 7,000,001 の陽線(飛ばさない足)
    t0 = datetime(2020, 1, 1, tzinfo=timezone.utc)
    rows = (((t0 + timedelta(minutes=k)).isoformat(), 7e6, 7e6 + 1, 7e6, 7e6 + 1, 1.0) for k in range(n))
    with tempfile.TemporaryDirectory() as d:
        tracemalloc.start()
        try:
            st = _Churn()
            run(rows, st, out_dir=d, tick=1.0, meta=META)
            assert st.k == n  # 足ごとに 1 回(終値)呼ばれた = 飛ばさずに回した
            return tracemalloc.get_traced_memory()[1]
        finally:
            tracemalloc.stop()


def test_gone_orders_are_not_kept():
    # 消えた注文 1 つあたりの記憶の増え方が 200 バイト未満(番号の集合だけを持つ形で約 100 バイト、
    #   注文の中身を全部持つ形で約 450 バイトだった。1 版目でリードが捨てる実装で測った値)
    a, b = _peak(2000), _peak(12000)
    assert (b - a) / 10000 < 200, (a, b)
