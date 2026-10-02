"""手で作った小さな入力で XborderMomRewrite を確かめる。k=3(min_history=5)、thr 0.8%、exit 0.05%。"""
from __future__ import annotations

import math
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot.bt.core import BarEvent, LookAheadError  # noqa: E402
from bot.bt.data.reference import reference_series  # noqa: E402
from bot.research.cards.card import SeriesSpec  # noqa: E402
from bot.research.cards.run import run_card  # noqa: E402
from rewrite_card import MIN_NS, REF_NAME, XborderMomRewrite, decide  # noqa: E402

T0 = 28_333_333 * 60 * 1_000_000_000  # 分の始まりにそろえた時刻(ns)
DECL = {REF_NAME: {"lag_ns": MIN_NS, "source": "W4 委任文(リードの決め): open_time + 60 秒"}}
P = {"k": 3, "thr_pct": 0.8, "exit_pct": 0.05}


def m(i: int) -> int:
    """分 i の始まり(ns)。足 i は [m(i), m(i+1))。"""
    return T0 + i * MIN_NS


def bars(idx, empty=()):
    out = []
    for i in idx:
        out.append(BarEvent(received_time_ns=m(i + 1), exchange_time_ns=m(i + 1), open=100.0, high=100.0,
                            low=100.0, close=100.0, volume=0.0 if i in empty else 1.0, start_time_ns=m(i)))
    return out


def refs(values: dict):
    """values: 分 i -> Binance の close。キーが無い分は行が無い。"""
    rows = [(m(i), float(v)) for i, v in sorted(values.items())]
    return {REF_NAME: reference_series(REF_NAME, rows, declarations=DECL)}


def run(bar_idx, values, empty=(), card=None):
    card = card or XborderMomRewrite(P)
    r = run_card(card, bars(bar_idx, empty), references=refs(values), declarations=DECL,
                 venue="bitflyer", symbol="FX_BTC_JPY")
    return r


def series(lo, hi, f):
    return {i: f(i) for i in range(lo, hi)}


def test_buy_then_close():
    v = series(-10, 12, lambda i: 101.0 if i >= 6 else 100.0)
    r = run(range(10), v)
    assert list(r.exposure) == [0, 0, 0, 0, 0, 0, 1, 1, 1, 0]


def test_sell_then_close():
    v = series(-10, 12, lambda i: 99.0 if i >= 6 else 100.0)
    r = run(range(10), v)
    assert list(r.exposure) == [0, 0, 0, 0, 0, 0, -1, -1, -1, 0]


def test_hold_keeps_previous():
    v = series(-10, 12, lambda i: 100.0)
    v.update({6: 101.0, 7: 100.5, 8: 100.5, 9: 100.5, 10: 100.5})
    r = run(range(11), v)
    # 6: BUY / 7: log(100.5/100)=0.499% HOLD / 8: 同じ / 9: log(100.5/101)=-0.496% HOLD / 10: 0 -> CLOSE
    assert list(r.exposure) == [0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 0]


def test_hold_keeps_previous_short():
    v = series(-10, 12, lambda i: 100.0)
    v.update({6: 99.0, 7: 99.5, 8: 99.5, 9: 99.5, 10: 99.5})
    r = run(range(11), v)
    assert list(r.exposure) == [0, 0, 0, 0, 0, 0, -1, -1, -1, -1, 0]


def test_insufficient_history_is_hold_from_zero():
    # 分 2 から 102。足 2,3 は Binance だけ見れば BUY だが、足が k+2=5 本そろうまでは様子見(持ち高 0)。
    v = series(-10, 12, lambda i: 102.0 if i >= 2 else 100.0)
    r = run(range(7), v)
    assert list(r.exposure) == [0, 0, 0, 0, 1, 0, 0]


def test_empty_bar_counts_for_history_but_is_not_decided():
    v = series(-10, 12, lambda i: 102.0 if i >= 2 else 100.0)
    r = run(range(7), v, empty={1})
    assert not r.decided[1] and math.isnan(r.exposure[1])
    assert list(r.exposure[[0, 2, 3, 4, 5, 6]]) == [0, 0, 0, 1, 0, 0]


def test_k_back_is_counted_in_time_at_a_bitflyer_gap():
    # bitFlyer の足 5 が無い。足 8 の k 本前は「時刻で 3 分前の分 5」(行で数えれば足 4)。
    v = series(-10, 12, lambda i: 100.0)
    v[5] = 99.0
    r = run([0, 1, 2, 3, 4, 6, 7, 8], v)
    # 足 6: 分6=100/分3=100 CLOSE、足 7: 分7/分4 CLOSE、足 8: log(100/99)=1.005% BUY
    assert list(r.exposure) == [0, 0, 0, 0, 0, 0, 0, 1]


def test_fallback_up_to_two_minutes_and_none_after_three():
    v = series(-10, 12, lambda i: 101.0 if i >= 4 else 100.0)
    for i in (5, 6, 7):
        del v[i]
    r = run(range(10), v)
    # 足 4: 101/100 BUY。足 5: 分5 無し -> 分4=101 BUY。足 6: 分6,5 無し -> 分4 BUY。
    # 足 7: 分7,6,5 無し -> None -> 様子見で 1 のまま(3 分遡れば 101/101 で CLOSE になるので見分けられる)。
    # 足 8: 今 101、過去 分5 無し -> 分4=101 -> CLOSE 0(遡りが過去の側にも効く)。
    assert list(r.exposure) == [0, 0, 0, 0, 1, 1, 1, 1, 0, 0]


def test_no_reference_at_all_is_hold():
    r = run(range(8), {})
    assert list(r.exposure) == [0] * 8


def test_future_rows_do_not_change_the_past():
    v = series(-10, 30, lambda i: 100.0 * (1.003 ** i))
    full = run(range(25), v)
    cut = {i: x for i, x in v.items() if i <= 15}
    part = run(range(25), cut)
    assert list(full.exposure[:17]) == list(part.exposure[:17])


def test_reading_the_row_of_t_is_lookahead():
    class Peek(XborderMomRewrite):
        def exposure(self, view):
            view.ref_at(REF_NAME, int(view.now_ns))  # t で始まる分は t+60s まで使えない
            return 0.0

    with pytest.raises(LookAheadError):
        run(range(3), series(-10, 12, lambda i: 100.0), card=Peek(P))


def test_same_instance_twice_gives_same_answer():
    v = series(-10, 12, lambda i: 101.0 if i >= 6 else 100.0)
    c = XborderMomRewrite(P)
    a = run(range(10), v, card=c)
    b = run(range(10), v, card=c)
    assert list(a.exposure) == list(b.exposure)


def test_card_mouth():
    c = XborderMomRewrite()
    assert c.k == 30 and c.thr == 0.8 / 100 and c.exit_band == 0.05 / 100
    assert c.requires == [SeriesSpec(REF_NAME, 60 * 1_000_000_000)]


def test_decide_boundaries():
    a, b = 101.0, 100.0
    mom = float(np.log(a / b))
    assert decide(a, b, thr=mom, exit_band=0.0) == "HOLD"  # mom > thr は厳密
    assert decide(a, b, thr=np.nextafter(mom, 0.0), exit_band=0.0) == "BUY"
    neg = float(np.log(b / a))
    assert decide(b, a, thr=-neg, exit_band=0.0) == "HOLD"  # mom < -thr も厳密
    assert decide(b, a, thr=np.nextafter(-neg, 0.0), exit_band=0.0) == "SELL"
    assert decide(a, b, thr=1.0, exit_band=mom) == "CLOSE"  # |mom| <= exit は等号を含む
    assert decide(a, b, thr=1.0, exit_band=np.nextafter(mom, 0.0)) == "HOLD"
    assert decide(a, 0.0, thr=0.01, exit_band=0.0) == "HOLD"  # leader_past <= 0
    assert decide(a, -1.0, thr=0.01, exit_band=0.0) == "HOLD"
    assert decide(float("nan"), b, thr=0.01, exit_band=0.0) == "HOLD"
    assert decide(None, b, thr=0.01, exit_band=0.0) == "HOLD"


def _synthetic_root(tmp_path, seal_cut=None):
    """合成の置き場(本物の backtest_data ではない)。足は 2023-03-01 00:00 から 90 分、分 10 は約定なし。
    Binance は 分 40 から 102、それより前は 100。seal_cut を渡すと、足のファイルをその時刻で封印する。"""
    import gzip
    from datetime import datetime, timedelta, timezone

    import compare

    t0 = datetime(2023, 3, 1, tzinfo=timezone.utc)
    bd = tmp_path / compare.BARS_DIR
    rd = tmp_path / compare.REF_DIR
    bd.mkdir(parents=True)
    rd.mkdir(parents=True)
    with gzip.open(bd / "candles_1m_2023.csv.gz", "wt") as f:
        f.write("ts,open,high,low,close,volume\n")
        for i in range(90):
            ts = (t0 + timedelta(minutes=i)).strftime("%Y-%m-%d %H:%M:%S+00:00")
            f.write(f"{ts},,,,,0\n" if i == 10 else f"{ts},100,100,100,100,1\n")
    with gzip.open(rd / "binance_BTCUSDT_1m_2023.csv.gz", "wt") as f:
        f.write("open_time,open,high,low,close,volume\n")
        for i in range(-70, 90):
            ts = (t0 + timedelta(minutes=i)).strftime("%Y-%m-%d %H:%M:%S+00:00")
            f.write(f"{ts},1,1,1,{102.0 if i >= 40 else 100.0},1\n")
    if seal_cut is not None:
        sd = tmp_path / "backtest_data" / "phase2_sealed" / "U"
        sd.mkdir(parents=True)
        (sd / "SEALED.json").write_text(json_dumps({
            "unit": "U", "forward_start": seal_cut,
            "files": [{"path": f"{compare.BARS_DIR}/candles_1m_2023.csv.gz", "time_column": "ts",
                       "seal_from_ts": seal_cut}]}))
    other = tmp_path / "zero_card.py"
    other.write_text(
        "from bot.research.cards.card import SeriesSpec\n"
        "class Zero:\n"
        "    name = 'zero'\n"
        "    def __init__(self):\n"
        "        self.requires = [SeriesSpec('binance_btcusdt_close', 60 * 1_000_000_000)]\n"
        "    def exposure(self, view):\n"
        "        return 0.0\n")
    return t0, other


def json_dumps(x):
    import json
    return json.dumps(x)


def test_compare_script_on_a_synthetic_root(tmp_path):
    """compare.py を合成の置き場で通す。相手 = いつも 0 のカード。"""
    import json
    from datetime import timedelta

    import compare

    t0, other = _synthetic_root(tmp_path)
    out = tmp_path / "r.json"
    rc = compare.main(["--root", str(tmp_path), "--start", "2023-03-01T00:00:00Z", "--end", "2023-03-01T01:00:00Z",
                       "--other-module", str(other), "--other-class", "Zero", "--out", str(out)])
    assert rc == 0
    res = json.loads(out.read_text())
    # 足 59 本(分 10 は約定なしで門が落とす)。持ち高 1 は足 40..59 の 20 本(今 102 / 30 分前 100)
    assert res["bars"] == 59 and res["decided"] == 59 and res["mismatch"] == 20
    assert res["mismatches"][0]["bar_end"] == (t0 + timedelta(minutes=41)).strftime("%Y-%m-%dT%H:%M:%SZ")
    # 最初の食い違い(足の終わり 00:41)の窓 [00:10, 00:41) に約定なしの分 10 が入る -> bitFlyer の抜け。以降は持ち越し
    assert res["counts"]["bitFlyer の抜け"] == 1 and res["counts"]["持ち越し"] == 19
    assert compare.main(["--root", str(tmp_path), "--end", "2023-12-19", "--other-module", str(other),
                         "--other-class", "Zero"]) == 2


def test_compare_goes_through_the_seal_door(tmp_path, capsys):
    """足のファイルを 00:30 で封印した合成の置き場: 終わりが 00:30 なら読め、01:00 なら門が拒む。"""
    import compare

    _, other = _synthetic_root(tmp_path, seal_cut="2023-03-01T00:30:00+00:00")
    base = ["--root", str(tmp_path), "--start", "2023-03-01T00:00:00Z", "--other-module", str(other),
            "--other-class", "Zero"]
    assert compare.main(base + ["--end", "2023-03-01T00:30:00Z"]) == 0
    capsys.readouterr()
    assert compare.main(base + ["--end", "2023-03-01T01:00:00Z"]) == 3
    assert "SealedRangeError" in capsys.readouterr().out
