"""G-1 of K1 stage G (delegation docs/DATA/delegations/20261001_k1_stage_g_close.md §2-1), the strategy side: before
the fix `bot.strategy.k1_xvenue` took "the first bar of an instant" as the overseas bar (d0) and "the second" as the
bitFlyer bar (d1): a proxy that leaned on the core's merge order (INTENT_MAP X-9 = △). Rule after the fix: the
strategy tells the two streams apart by the names its config gives (`streams`), acts when both bars of a window have
arrived, and the venue prices by the price stream only (SimVenue(streams=...)). So the trades are the same whichever
stream the merge rule delivers first; and the prepare step `join_fold` (XVENUE_PREREG.md §2) joins on the UTC minute
and folds both sides on the same windows.
"""
from __future__ import annotations

import random

import pytest

from bot.bt.core import BarEvent, CoreEngine
from bot.bt.report.trades import round_trips
from bot.strategy.k1_xvenue import K1XError, K1XSetup, join_fold

NS = 1_000_000_000
T0 = 1_600_000_000 * NS


def bars(rng, n, base, scale):
    out, p = [], base
    for _ in range(n):
        o = p
        c = max(1.0, o + rng.gauss(0, scale))
        h = max(o, c) + abs(rng.gauss(0, scale)) * (3 if rng.random() < 0.3 else 0.5)
        lo = max(0.5, min(o, c) - abs(rng.gauss(0, scale)) * (3 if rng.random() < 0.3 else 0.5))
        out.append((o, h, lo, c))
        p = c
    return out


def ev(i, x, foot=60):
    o, h, lo, c = x
    return BarEvent(received_time_ns=T0 + (i + 1) * foot * NS, start_time_ns=T0 + i * foot * NS,
                    open=o, high=h, low=lo, close=c, volume=1.0)


def cfg(mode, signal, price, prepare="none", foot=1):
    return {"instrument": "FX_BTC_JPY", "foot_min": foot, "gate": {"s": "19", "b": "24"},
            "strength": "both", "mode": mode, "fill": "last_bar_close",
            "costs": {"maker_fee_rate": 0, "taker_fee_rate": 0, "source": "test"},
            "streams": {"signal": signal, "price": price}, "prepare": prepare}


def run(mode, sn, pn, sb, pb):
    parts = K1XSetup().build(cfg(mode, [sn], [pn]), 0)
    streams = {sn: [ev(i, x) for i, x in enumerate(sb)], pn: [ev(i, x) for i, x in enumerate(pb)]}
    res = CoreEngine(parts.strategy, streams, parts.fill_model, parts.latency_model, parts.cost_model,
                     parts.account).run()
    sides = {o.client_order_id: o.request.side for o in res.orders.values()}
    fills = [{"order_id": f.client_order_id, "t_ns": f.venue_time_ns, "side": f.side or sides[f.client_order_id],
              "px": f.price, "qty": f.size, "fee": f.fee} for f in res.fills]
    return round_trips(fills, parts.exit_reasons), fills


@pytest.mark.parametrize("mode", ["design", "sameclose"])
def test_the_trades_do_not_depend_on_which_stream_the_merge_delivers_first(mode):
    rng = random.Random(7)
    sb, pb = bars(rng, 600, 9000.0, 25.0), bars(rng, 600, 1_000_000.0, 2500.0)
    a, fa = run(mode, "d0", "d1", sb, pb)  # the signal stream sorts first
    b, fb = run(mode, "z", "a", sb, pb)    # the price stream sorts first
    assert len(a) > 20 and a == b
    closes = {T0 + (i + 1) * 60 * NS: x[3] for i, x in enumerate(pb)}
    assert all(f["px"] == closes[f["t_ns"]] for f in fa + fb)  # every fill at the price stream's close of that time


def test_out_of_step_windows_and_unnamed_streams_stop_the_run():
    rng = random.Random(1)
    sb, pb = bars(rng, 5, 9000.0, 25.0), bars(rng, 5, 1e6, 2500.0)
    parts = K1XSetup().build(cfg("design", ["s"], ["p"]), 0)
    streams = {"s": [ev(i, x) for i, x in enumerate(sb)], "p": [ev(i + 1, x) for i, x in enumerate(pb)]}
    with pytest.raises(K1XError, match="out of step"):
        CoreEngine(parts.strategy, streams, parts.fill_model, parts.latency_model, parts.cost_model,
                   parts.account).run()
    parts = K1XSetup().build(cfg("design", ["s"], ["p"]), 0)
    streams = {"s": [ev(0, sb[0])], "q": [ev(0, pb[0])]}
    with pytest.raises(K1XError, match="stream 'q'"):
        CoreEngine(parts.strategy, streams, parts.fill_model, parts.latency_model, parts.cost_model,
                   parts.account).run()


def test_config_names_the_streams():
    for bad in ({"signal": ["d0"], "price": ["d0"]}, {"signal": [], "price": ["d1"]}, {"signal": ["d0"]},
                {"signal": ["d0", "d2"], "price": ["d1"]}):
        c = cfg("design", ["d0"], ["d1"])
        c["streams"] = bad
        with pytest.raises(K1XError):
            K1XSetup().build(c, 0)


TJ = 1_599_998_400 * NS  # on the 3-minute epoch grid (bars_from_bars folds on the UTC epoch grid)


def _m(minute, px, sec=0):
    return BarEvent(received_time_ns=TJ + minute * 60 * NS + sec * NS + 60 * NS, start_time_ns=TJ + minute * 60 * NS + sec * NS,
                    open=px, high=px + 1, low=px - 1, close=px + 0.5, volume=1.0)


def test_join_fold_joins_on_the_utc_minute_and_folds_both_sides_on_the_same_windows():
    # signal: minutes 0,1,2(off grid by 30 s),4,5 ; price: minutes 0,1,2,3,5 -> joined minutes 0,1,2,5
    sig = {"a": [_m(0, 10), _m(1, 11)], "b": [_m(2, 12, sec=30), _m(4, 14), _m(5, 15)]}
    px = {"c": [_m(0, 100), _m(1, 101), _m(2, 102), _m(3, 103), _m(5, 105)]}
    out = join_fold({**sig, **px}, ("a", "b"), ("c",), 3, True)
    starts = [int(e.start_time_ns) for e in out["signal"]]
    assert starts == [int(e.start_time_ns) for e in out["price"]] == [TJ, TJ + 180 * NS]
    s0, s1 = out["signal"]
    p0, p1 = out["price"]
    assert (s0.open, s0.close, s0.high, s0.low, s0.volume) == (10, 12.5, 13, 9, 3.0)
    assert (p0.open, p0.close, p0.volume) == (100, 102.5, 3.0)
    assert (s1.open, s1.close, s1.volume) == (15, 15.5, 1.0) and (p1.open, p1.close, p1.volume) == (105, 105.5, 1.0)
    assert int(s1.received_time_ns) == TJ + 360 * NS  # a 3-minute window is delivered at its end


def test_join_fold_refuses_streams_out_of_order():
    with pytest.raises(K1XError, match="does not start after"):
        join_fold({"a": [_m(5, 10)], "b": [_m(1, 10)], "c": [_m(1, 10)]}, ("a", "b"), ("c",), 3, True)
