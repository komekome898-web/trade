"""All-JPY-pair rebate screen: does the maker rebate ever exceed the adverse-selection wall?

maker_raw = 0.5 * half_spread_p50 + rebate - ADV_PRIOR   (bps, per filled leg)
Capture rate 0.5 and the 1.2bps adverse prior are the repo's own measurements
(report aa: capture is ~half the nominal half-spread; adv(5s) = -1.32 at the touch).
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "run1")
ADV = 1.2
SHARE = 0.02  # generous: capture 2% of the venue pair's daily volume as a maker


def rebate_bitbank(pair):
    return 0.0 if pair == "btc_jpy" else 2.0  # -0.02% on every JPY pair except BTC


def taker_bitbank(pair):
    return 10.0 if pair == "btc_jpy" else 12.0


def rebate_gmo(sym):
    if "_JPY" in sym:
        return 0.0  # leverage products: 0 / 0
    return 1.0 if sym in ("BTC", "ETH", "XRP", "DAI") else 3.0


def taker_gmo(sym):
    if "_JPY" in sym:
        return 0.0
    return 5.0 if sym in ("BTC", "ETH", "XRP", "DAI") else 9.0


def load(name):
    p = os.path.join(OUT, f"screen_{name}.jsonl")
    if not os.path.exists(p):
        return {}
    acc = {}
    with open(p) as fh:
        for line in fh:
            try:
                r = json.loads(line)
            except Exception:
                continue
            for d in r["r"]:
                mid = (d["a"] + d["b"]) / 2.0
                if mid <= 0 or d["a"] < d["b"]:
                    continue
                acc.setdefault(d["p"], {"spr": [], "vol": d["vol"], "last": d["last"]})
                acc[d["p"]]["spr"].append((d["a"] - d["b"]) / mid * 1e4)
                acc[d["p"]]["vol"] = d["vol"]
                acc[d["p"]]["last"] = d["last"]
    return acc


def report(name, acc, reb, tak):
    print(f"\n## {name}  (n polls per pair shown; spread in bps of mid)")
    print(f"{'pair':>12s} | {'n':>5s} | {'p25':>8s} | {'p50':>8s} | {'p75':>8s} | "
          f"{'reb':>5s} | {'mk_flat':>9s} | {'mk_scaled':>10s} | {'costfloor':>9s} | "
          f"{'24h vol JPY':>13s} | {'ceilJPY/d':>10s}")
    out = []
    for p, d in acc.items():
        s = np.asarray(d["spr"], dtype=float)
        if len(s) < 20:
            continue
        p50 = float(np.percentile(s, 50))
        r = reb(p)
        hs = p50 / 2.0
        mk = 0.5 * hs + r - ADV               # flat 1.2bps adverse prior (naive)
        mk2 = r - 0.69 * hs                   # adverse scaled with the spread (K=1.19, report aa)
        cf = 2 * tak(p) + p50 + 4.0
        vj = d["vol"] * d["last"]
        ceil = max(mk2, 0.0) / 1e4 * vj * SHARE   # yen/day at SHARE of venue volume
        out.append((mk2, p, len(s), float(np.percentile(s, 25)), p50,
                    float(np.percentile(s, 75)), r, mk, cf, vj, ceil))
    out.sort(reverse=True)
    for mk2, p, n, a, b, c, r, mk, cf, vj, ceil in out:
        print(f"{p:>12s} | {n:>5d} | {a:>8.2f} | {b:>8.2f} | {c:>8.2f} | "
              f"{r:>5.1f} | {mk:>9.2f} | {mk2:>10.2f} | {cf:>9.2f} | {vj:>13,.0f} | {ceil:>10,.0f}")
    return out


if __name__ == "__main__":
    bb = load("bitbank")
    gm = load("gmo")
    report("bitbank JPY pairs (maker -0.02% except BTC)", bb, rebate_bitbank, taker_bitbank)
    report("GMO (spot maker -0.01%/-0.03%; *_JPY = leverage, 0/0)", gm, rebate_gmo, taker_gmo)
