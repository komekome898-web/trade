#!/usr/bin/env python3
"""K1 段階 G の戦略(src/bot/strategy/k1_xvenue.py)の自前の試験。データの門の下で回す(ファイルは読まない)。

乱数の足 2 本の流れ(海外 = d0、bitFlyer = d1、同じ窓)を核(CoreEngine)に通し、約定の列から作った往復を、
規則の文(RESULT.md 1.3・10.1・11.1・12.1、XVENUE_PREREG.md §1)をこの試験の中で書き直した素の
ループと 1 往復ずつ比べる(向き・建値・決済値・建てた時刻・閉じた時刻・決済理由)。素のループは
k1_wick / k1_xvenue のコードを使わない。モード design / sameclose / single、門 13 × 強さ 3。

使い方: PYTHONPATH=scripts:src python3 scripts/k1_newenv_g_selftest.py [--trials 6]
"""
from __future__ import annotations

import argparse
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import k1_newenv_g_datagate  # noqa: E402,F401

from bot.bt.core import BarEvent  # noqa: E402
from bot.bt.core.engine import CoreEngine  # noqa: E402
from bot.bt.report.trades import round_trips  # noqa: E402
from bot.strategy.k1_xvenue import K1XSetup  # noqa: E402

NS = 1_000_000_000
SMALL = ("off", "-", "10", "19", "30")
BIG = ("-", "24", "40")


def all_gates():
    out = []
    for s in SMALL:
        for b in BIG:
            if (s, b) == ("off", "-"):
                continue
            if s not in ("off", "-") and b != "-" and float(s) > float(b):
                continue
            out.append((s, b))
    return out


def ref_signal(o, h, l, c, s, b):
    """RESULT.md 1.3 + H1 を書き直したもの。(sig, strength)。"""
    d = c - o
    if d == 0:
        return 0, ""
    cs = 1 if d > 0 else -1
    top = h - max(o, c)
    under = min(o, c) - l
    if int(top) > int(under):
        sig, w = -1, top
    elif int(under) > int(top):
        sig, w = 1, under
    else:
        return 0, ""
    wbp = w / c * 10000.0
    small = s != "off" and (s == "-" or wbp >= float(s)) and w > abs(d)
    big = b != "-" and wbp >= float(b)
    if not (small or big):
        return 0, ""
    if abs(d) >= w:
        sig = -cs
    return sig, ("strong" if sig == cs else "weak")


def ref_trades(sig_bars, px, times, s, b, keep, delay):
    sigs = [ref_signal(*x, s, b) for x in sig_bars]
    acts = ([(0, "")] + sigs[:-1]) if delay else sigs
    pos, out, entry = 0, [], None
    for j, (sg, st) in enumerate(acts):
        if sg == 0 or not (keep == "both" or st == keep) or pos == sg:
            continue
        if pos == -sg:
            out.append((pos, entry[0], px[j], entry[1], times[j], "reversed" if st == "strong" else "opposite_weak"))
            pos = 0
            if st != "strong":
                continue
        pos, entry = sg, (px[j], times[j])
    return out


def bars(rng, n, base, scale):
    out, p = [], base
    for _ in range(n):
        o = p
        c = max(1.0, o + rng.gauss(0, scale))
        h = max(o, c) + abs(rng.gauss(0, scale)) * (3 if rng.random() < 0.3 else 0.5)
        l = max(0.5, min(o, c) - abs(rng.gauss(0, scale)) * (3 if rng.random() < 0.3 else 0.5))
        out.append((o, h, l, c))
        p = c
    return out


def ev(t0, i, foot, x):
    o, h, l, c = x
    return BarEvent(received_time_ns=t0 + (i + 1) * foot * NS, exchange_time_ns=t0 + (i + 1) * foot * NS,
                    open=o, high=h, low=l, close=c, volume=1.0, start_time_ns=t0 + i * foot * NS)


def run_engine(mode, s, b, keep, sb, pb, t0, foot):
    cfg = {"instrument": "BTCUSDT" if mode == "single" else "FX_BTC_JPY", "foot_min": 1, "gate": {"s": s, "b": b},
           "strength": keep, "mode": mode, "fill": "last_bar_close",
           "costs": {"maker_fee_rate": 0, "taker_fee_rate": 0, "source": "test"}}
    parts = K1XSetup().build(cfg, 0)
    streams = {"d0": [ev(t0, i, foot, x) for i, x in enumerate(sb)]}
    if mode != "single":
        streams["d1"] = [ev(t0, i, foot, x) for i, x in enumerate(pb)]
    eng = CoreEngine(parts.strategy, streams, parts.fill_model, parts.latency_model, parts.cost_model, parts.account)
    res = eng.run()
    sides = {o.client_order_id: o.request.side for o in res.orders.values()}
    fills = [{"order_id": f.client_order_id, "t_ns": f.venue_time_ns, "side": f.side or sides[f.client_order_id],
              "px": f.price, "qty": f.size, "fee": f.fee} for f in res.fills]
    tr = round_trips(fills, parts.exit_reasons)
    return [(1 if t["side"] == "buy" else -1, t["entry_px"], t["exit_px"], t["entry_t_ns"], t["exit_t_ns"], t["reason"])
            for t in tr]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=6)
    a = ap.parse_args()
    rng = random.Random(20261001)
    n_cases = n_trades = fails = 0
    for trial in range(a.trials):
        n = 400
        sb = bars(rng, n, 9000.0, 25.0)
        pb = bars(rng, n, 1_000_000.0, 2500.0)
        t0, foot = 1_600_000_000 * NS, 60
        times = [t0 + (i + 1) * foot * NS for i in range(n)]
        for s, b in all_gates():
            for keep in ("strong", "weak", "both"):
                for mode in ("design", "sameclose", "single"):
                    px = [x[3] for x in (sb if mode == "single" else pb)]
                    want = ref_trades(sb, px, times, s, b, keep, delay=(mode != "sameclose"))
                    got = run_engine(mode, s, b, keep, sb, pb, t0, foot)
                    n_cases += 1
                    n_trades += len(want)
                    if got != want:
                        fails += 1
                        if fails <= 3:
                            print("MISMATCH", trial, s, b, keep, mode, len(got), len(want),
                                  next((x for x in zip(got, want) if x[0] != x[1]), None))
    print(f"cases {n_cases} trades compared {n_trades} mismatched cases {fails}")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
