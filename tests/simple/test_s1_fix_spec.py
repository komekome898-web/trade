"""単純な測りの道 S1 の直し(作り終えた後の批評家 1 回目の [直す] と L-824)の受け入れの試験。

リードが書いた(批評家の答え docs/AUDITOR/VERDICTS/2026-10-08_simple_s1_critic1.md、応答は
docs/DISCUSSIONS/2026-10-08_simple_road/CRITIC1_RESPONSE.md、決まりの正本は同じ置き場の SPEC.md)。
作業者は試験を変えずに通す(変えたいときは問いとして返す)。test_s1_spec.py も変えずに通す。

オーナーの逐語: L-824「**(a)**」(同じ足で、前からの建玉を閉じる利確と新しい 1 段目が両方約定したら、利確を先に記す)/
L-754「**私がしてほしいの決まりを足すんじゃなくて、この計算が確実にできるツールを作ることと、そのツールが必ず使われる仕組みです。**」/
L-819「**測定方法も残し方も検査もシンプルにできるはず**」
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

simple = pytest.importorskip("bot.bt.simple")
run, read_bars, check_numbers, SimpleRoadError = simple.run, simple.read_bars, simple.check_numbers, simple.SimpleRoadError

SIDES = ("optimistic", "pessimistic")
SEAL = "2023-12-17T15:00:00+00:00"
META = {"strategy": "試験", "params": {}, "seal": SEAL, "bar_files": []}


def ts(k):
    """足 k(0 から)の始まり。2023-11-14T22:10 から 1 分ずつ。"""
    return f"2023-11-14T22:{10 + k:02d}:00+00:00"


def bars(rows):
    return [(ts(k),) + tuple(float(x) for x in r) + (1.0,) for k, r in enumerate(rows)]


class Script:
    """足 k の判定で plan[k] の注文を返す。約定し終えた番号は返さない(raw なら返す)。"""

    def __init__(self, plan, raw=False):
        self.plan, self.raw, self.k, self.done = plan, raw, -1, set()

    def decide(self, bar, fills):
        self.k += 1
        self.done |= {f["id"] for f in fills}
        return {i: o for i, o in self.plan.get(self.k, {}).items() if self.raw or i not in self.done}, []


def go(tmp_path, rows, plan, side, raw=False):
    out = tmp_path / side
    run(bars(rows), Script(plan, raw), side=side, out_dir=str(out), tick=1.0, meta=META)
    return out


def table(out, name, side):
    with open(os.path.join(out, f"{name}_{side}.csv"), newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def fills(out, side):
    return [(r["ts"], r["id"], r["px"], r["case"]) for r in table(out, "fills", side)]


def summary(out, side):
    with open(os.path.join(out, f"summary_{side}.json"), encoding="utf-8") as fh:
        return json.load(fh)


FLAT = (7000000, 7000000, 7000000, 7000000)
A1 = (7000000, 7000050, 6999950, 7000000)  # 足 1: 7,000,000 の買いが範囲の内で約定する
A2 = (7000000, 7000150, 6999850, 7000000)  # 足 2: 7,000,100 の売りと 6,999,900 の買いが両方とも範囲の内
R1 = {"form": "limit", "side": "buy", "qty": 0.009, "px": 7000000.0}
X1 = {"form": "exit", "side": "sell", "qty": 0.009, "parent": "r1", "px": 7000100.0}
R2 = {"form": "limit", "side": "buy", "qty": 0.009, "px": 6999900.0}


# ================================================================ F1 足の中の記す順(L-824 の (a))
@pytest.mark.parametrize("side", SIDES)
@pytest.mark.parametrize("exit_at", (0, 1), ids=("利確を根と一緒に出す", "利確を根の約定の後に出す"))
def test_f1_exit_of_earlier_parent_before_new_limit(tmp_path, side, exit_at):
    # 足 1 で r1(買い 7,000,000)が range で約定。利確 x1(売り 7,000,100)は足 1 の高値 7,000,050 より上なので足 1 では約定しない
    #   (良い側でも範囲の外)。足 2 で x1(7,000,100)と新しい根 r2(買い 6,999,900)が両方とも範囲の内で約定する。
    #   x1 の親 r1 は前の足で約定したので、x1 を r2 より先に記す(L-824 の (a))。r2 の seq が x1 より小さくても同じ。
    plan = {0: {"r1": R1}, 1: {"r2": R2, "x1": X1}} if exit_at == 1 else {0: {"r1": R1, "x1": X1}, 1: {"r2": R2, "x1": X1}}
    out = go(tmp_path, [FLAT, A1, A2], plan, side)
    assert fills(out, side) == [(ts(1), "r1", "7000000.0", "range"), (ts(2), "x1", "7000100.0", "range"),
                                (ts(2), "r2", "6999900.0", "range")]
    # 帳簿: r1 → x1 で取引 1 回が閉じ(0.009 × 100 = +0.9 円)、r2 は途中の取引
    s = summary(out, side)
    assert (s["fill_count"], s["closed_trades"], s["open_trades"]) == (3, 1, 1)
    assert check_numbers(str(out), side) == []


@pytest.mark.parametrize("side", SIDES)
def test_f1_exit_of_same_bar_parent_stays_after(tmp_path, side):
    # 親がこの足で約定した利確は、今までどおり親の後(limit → level → この足で親が約定した利確)。
    #   足 1(安値 6,999,950・高値 7,000,050): r1 7,000,000 が range、利確 7,000,040 は良い側だけ同じ足で entry_bar。
    #   前の足で親が約定した利確は無いので、記す順は r1 → x1。悪い側は x1 が足 2(高値 7,000,150)で range。
    x = dict(X1, px=7000040.0)
    out = go(tmp_path, [FLAT, A1, A2], {0: {"r1": R1, "x1": x}, 1: {"x1": x}}, side)
    want = [(ts(1), "r1", "7000000.0", "range")]
    want += [(ts(1), "x1", "7000040.0", "entry_bar")] if side == "optimistic" else [(ts(2), "x1", "7000040.0", "range")]
    assert fills(out, side) == want


@pytest.mark.parametrize("side", SIDES)
def test_f1_market_before_exit_of_earlier_parent(tmp_path, side):
    # 成行は足の始値で約定し、足の中で最初に起きる(リードの決め。SPEC.md §3)。足 1 で r1 が約定し、足 2 で
    #   成行の買い m1(始値 7,000,000)と r1 の利確 x1(売り 7,000,100、範囲の内)が両方約定する。記す順は m1 → x1
    m1 = {"form": "market", "side": "buy", "qty": 0.009}
    out = go(tmp_path, [FLAT, A1, A2], {0: {"r1": R1, "x1": X1}, 1: {"x1": X1, "m1": m1}}, side)
    assert fills(out, side) == [(ts(1), "r1", "7000000.0", "range"), (ts(2), "m1", "7000000.0", "market"),
                                (ts(2), "x1", "7000100.0", "range")]


# ================================================================ F2 封印の境の行より先は読まない
def _bar_file(tmp_path, lines):
    p = tmp_path / "candles_1m_2023.csv.gz"
    with gzip.open(p, "wt", encoding="utf-8") as fh:
        fh.write("ts,open,high,low,close,volume,col7_inferred_long_oi,col8_inferred_short_oi,buy_volume,sell_volume\n")
        for line in lines:
            fh.write(line + "\n")
    return str(p)


def test_f2_read_bars_does_not_read_past_seal_row(tmp_path):
    # 境の行の次の行は、時刻も読めない壊れた行。境の行で読むのをやめれば落ちない(読み続ければ時刻を読めずに落ちる)
    p = _bar_file(tmp_path, ["2023-12-17T14:59:00+00:00,100.0,101.0,99.0,100.5,1.5,,,,",
                             "2023-12-17T15:00:00+00:00,100.0,100.0,100.0,100.0,1.0,,,,",
                             "時刻でない,壊れた,行,,,,,,,"])
    assert list(read_bars([p], SEAL)) == [("2023-12-17T14:59:00+00:00", 100.0, 101.0, 99.0, 100.5, 1.5)]


# ================================================================ F3 安値 > 高値の足で止める
def test_f3_run_stops_on_low_above_high(tmp_path):
    with pytest.raises(SimpleRoadError):
        go(tmp_path, [FLAT, (7000000, 6999000, 7001000, 7000000)], {}, "optimistic")


def test_f3_read_bars_stops_on_low_above_high(tmp_path):
    p = _bar_file(tmp_path, ["2023-12-17T14:58:00+00:00,100.0,99.0,101.0,100.0,1.5,,,,"])
    with pytest.raises(SimpleRoadError):
        list(read_bars([p], SEAL))


# ================================================================ F4 数の作り直しは壊した記録を通さない(例外にもしない)
def _write(path, data: bytes):
    with open(path, "wb") as fh:
        fh.write(data)


def _ok_run(tmp_path):
    out = go(tmp_path, [FLAT, A1, A2], {0: {"r1": R1}, 1: {"r2": R2, "x1": X1}}, "optimistic")
    assert check_numbers(str(out), "optimistic") == []
    return str(out)


def _p(out, name, ext="csv"):
    return os.path.join(out, f"{name}_optimistic.{ext}")


ZERO = json.dumps({"fill_count": 0, "closed_trades": 0, "pnl_jpy": "0", "open_trades": 0}).encode()
TRADES_HEAD = b"first_t_ns,last_t_ns,levels,max_position,hold_ns,pnl_jpy,status\n"
FILLS_HEAD = b"ts,id,side,qty,px,case\n"


def _t_zero_bytes(out):
    _write(_p(out, "fills"), b"")
    _write(_p(out, "trades"), b"")
    _write(_p(out, "summary", "json"), ZERO)


def _t_garbage_fills_head(out):
    _write(_p(out, "fills"), b"garbage\n")
    _write(_p(out, "trades"), TRADES_HEAD)
    _write(_p(out, "summary", "json"), ZERO)


def _t_fills_head_extra_col(out):
    with open(_p(out, "fills"), "rb") as fh:
        lines = fh.read().split(b"\n")
    lines[0] += b",extra"
    _write(_p(out, "fills"), b"\n".join(lines))


def _t_trades_head_extra_col(out):
    with open(_p(out, "trades"), "rb") as fh:
        lines = fh.read().split(b"\n")
    lines[0] += b",extra"
    _write(_p(out, "trades"), b"\n".join(lines))


def _t_summary_list(out):
    _write(_p(out, "summary", "json"), b"[]")


def _t_summary_null(out):
    _write(_p(out, "summary", "json"), b"null")


def _t_summary_values_as_text(out):
    with open(_p(out, "summary", "json"), encoding="utf-8") as fh:
        s = json.load(fh)
    _write(_p(out, "summary", "json"), json.dumps({k: str(v) for k, v in s.items()}).encode())


def _t_summary_extra_key(out):
    with open(_p(out, "summary", "json"), encoding="utf-8") as fh:
        s = json.load(fh)
    s["extra"] = 1
    _write(_p(out, "summary", "json"), json.dumps(s).encode())


def _t_trades_not_utf8(out):
    _write(_p(out, "trades"), b"\xff\xfe\x00garbage")


def _t_fills_not_utf8(out):
    _write(_p(out, "fills"), b"\xff\xfe\x00garbage")


def _t_trades_row_added(out):
    with open(_p(out, "trades"), "rb") as fh:
        data = fh.read()
    last = data.rstrip(b"\n").split(b"\n")[-1]
    _write(_p(out, "trades"), data + last + b"\n")


def _t_trades_row_removed(out):
    with open(_p(out, "trades"), "rb") as fh:
        lines = fh.read().rstrip(b"\n").split(b"\n")
    _write(_p(out, "trades"), b"\n".join(lines[:-1]) + b"\n")


def _t_summary_value_bool(out):
    with open(_p(out, "summary", "json"), encoding="utf-8") as fh:
        s = json.load(fh)
    s["closed_trades"] = bool(s["closed_trades"])  # 1 → true(Python では True == 1)
    _write(_p(out, "summary", "json"), json.dumps(s).encode())


def _t_summary_value_float(out):
    with open(_p(out, "summary", "json"), encoding="utf-8") as fh:
        s = json.load(fh)
    s["fill_count"] = float(s["fill_count"])  # 3 → 3.0(Python では 3.0 == 3)
    _write(_p(out, "summary", "json"), json.dumps(s).encode())


def _t_fills_row_short(out):
    with open(_p(out, "fills"), "rb") as fh:
        lines = fh.read().rstrip(b"\n").split(b"\n")
    lines[-1] = b",".join(lines[-1].split(b",")[:2])
    _write(_p(out, "fills"), b"\n".join(lines) + b"\n")


def _t_trades_row_extra_cell(out):
    with open(_p(out, "trades"), "rb") as fh:
        lines = fh.read().rstrip(b"\n").split(b"\n")
    lines[1] += b",extra"
    _write(_p(out, "trades"), b"\n".join(lines) + b"\n")


def _t_trades_crlf(out):
    with open(_p(out, "trades"), "rb") as fh:
        data = fh.read()
    _write(_p(out, "trades"), data.replace(b"\n", b"\r\n"))


TAMPERS = [
    ("fills と trades が 0 バイト・summary が 0", _t_zero_bytes),
    ("fills の見出しがでたらめ・行なし・summary が 0", _t_garbage_fills_head),
    ("fills の見出しに余計な列", _t_fills_head_extra_col),
    ("trades の見出しに余計な列", _t_trades_head_extra_col),
    ("summary が []", _t_summary_list),
    ("summary が null", _t_summary_null),
    ("summary の値を全部文字に", _t_summary_values_as_text),
    ("summary に余計な鍵", _t_summary_extra_key),
    ("trades が UTF-8 でない", _t_trades_not_utf8),
    ("fills が UTF-8 でない", _t_fills_not_utf8),
    ("trades の行を 1 つ足す", _t_trades_row_added),
    ("trades の行を 1 つ消す", _t_trades_row_removed),
    ("summary の値を真偽値に", _t_summary_value_bool),
    ("summary の値を小数に", _t_summary_value_float),
    ("約定の行の欄が足りない", _t_fills_row_short),
    ("trades の中身の行の末尾に余計な欄", _t_trades_row_extra_cell),
    ("trades の改行を CRLF に", _t_trades_crlf),
]


@pytest.mark.parametrize("name,tamper", TAMPERS, ids=[t[0] for t in TAMPERS])
def test_f4_check_numbers_refuses_broken_records(tmp_path, name, tamper):
    out = _ok_run(tmp_path)
    tamper(out)
    got = check_numbers(out, "optimistic")  # 例外を出さない
    assert isinstance(got, list) and got != [] and all(isinstance(x, str) for x in got)


def test_f4_check_numbers_passes_true_zero_fill_run(tmp_path):
    # 約定が 0 本の走らせ(見出しだけの fills・trades と 0 の summary)は、そのまま合格する
    out = go(tmp_path, [FLAT, FLAT], {}, "optimistic")
    with open(_p(str(out), "fills"), "rb") as fh:
        assert fh.read() == FILLS_HEAD
    with open(_p(str(out), "trades"), "rb") as fh:
        assert fh.read() == TRADES_HEAD
    assert check_numbers(str(out), "optimistic") == []


# ================================================================ F5 取り下げた根・親の段・利確は止める(報告の Q7)
L = {"form": "level", "side": "buy", "qty": 0.009, "root": "r1", "offset": -100.0}


@pytest.mark.parametrize("name,plan", [
    ("根を約定の前に取り下げ段だけ残す", {0: {"r1": R1, "l1": L}, 1: {"l1": L}}),
    ("親を約定の前に取り下げ利確だけ残す", {0: {"r1": R1, "x1": X1}, 1: {"x1": X1}}),
], ids=["段", "利確"])
def test_f5_withdrawn_reference_stops(tmp_path, name, plan):
    # 足 1 = 平らな足 7,000,100(r1 の買い 7,000,000 は範囲の外で、約定する向きでもないので約定しない)
    with pytest.raises(SimpleRoadError):
        go(tmp_path, [FLAT, (7000100, 7000100, 7000100, 7000100), FLAT], plan, "optimistic", raw=True)


# ================================================================ F6 消えた注文を記憶に持ち続けない
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


def test_f6_gone_orders_are_not_kept():
    # 消えた注文 1 つあたりの記憶の増え方が 200 バイト未満(番号の集合だけを持つ形で約 100 バイト、
    #   注文の中身を全部持つ形で約 450 バイトだった。リードが捨てる実装で測った値)
    a, b = _peak(2000), _peak(12000)
    assert (b - a) / 10000 < 200, (a, b)


def test_f7_seq_is_unique_and_counts_up(tmp_path):
    # 消えた注文を記憶から外しても、注文の記録の seq は 0 から重ならずに並ぶ(注文を初めて受けた順の通し番号。SPEC.md §4)
    t0 = datetime(2020, 1, 1, tzinfo=timezone.utc)
    rows = [((t0 + timedelta(minutes=k)).isoformat(), 7e6, 7e6, 7e6, 7e6, 1.0) for k in range(30)]
    out = tmp_path / "seq"
    run(rows, _Churn(), side="optimistic", out_dir=str(out), tick=1.0, meta=META)
    got = {(r["id"], int(r["seq"])) for r in table(out, "orders", "optimistic")}
    assert sorted(s for _, s in got) == list(range(len(got)))
    assert sorted(got, key=lambda x: x[1]) == sorted(got, key=lambda x: x[0])  # 番号 o000000001… を出した順 = seq の順
