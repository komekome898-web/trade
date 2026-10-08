"""捨てる前提の試作(L-821): 単純な測りの道で、時間とメモリを測るだけのもの。測りには使わない。

使い方: PYTHONPATH=src python3 <このファイル> <本数> [出力のディレクトリ]
合成の乱歩の 1 分足(σ 3,000 円、seed 0。timing_probe.py と同じ作り方)を記憶の中で作り、市場のデータは読まない。

- 走らせ: 足を 1 本ずつ回し、足ごとに「約定 → 戦略に知らせる → 判定(次の足に出しておく注文の全部)」。
- 約定の決まり: 指値は範囲の内なら指値・約定する向きに外なら始値。段は根の最初の約定値段 + 距離(10 進で足して刻みに
  切り捨て)、根の足でも範囲の内なら約定。利確は良い側は建ての足から、悪い側は次の足から。成行は足の始値。
- 戦略: マチルダの代わりの小さな段の戦略(中心・ボラで 7 段の買い・売り、段ごとの利確、20 本で成行の決済)。
  マチルダそのものではない。注文と約定の数がマチルダの今の走らせと同じくらいになるかを出力で比べる。
- 残し方: 注文(消えたときに 1 行)と約定を、足を回しながらファイルに書き足す。
- 環境変数 CHURN=1 で、玉なしの間は足ごとに段を全部出し直す(注文の数を多めにした重い側の見積もり)。
"""
from __future__ import annotations

import csv
import math
import os
import random
import resource
import sys
import tempfile
import time
from collections import deque
from decimal import ROUND_FLOOR, Decimal

TICK = Decimal(1)
CHURN = os.environ.get("CHURN") == "1"  # 1 なら玉なしの間は足ごとに段を全部出し直す(注文の数の上限を見るため)


def floor_tick(x: Decimal) -> float:
    return float((x / TICK).to_integral_value(rounding=ROUND_FLOOR) * TICK)


def walk(n, seed=0, sig=3000.0):
    rng = random.Random(seed)
    px = 7_000_000
    for i in range(n):
        o = px
        c = o + round(rng.gauss(0, sig))
        h = max(o, c) + abs(round(rng.gauss(0, sig / 2)))
        lo = min(o, c) - abs(round(rng.gauss(0, sig / 2)))
        yield i, float(o), float(h), float(lo), float(c)
        px = c


# ---- 約定の関数(注文の一覧と足 1 本 → 約定) --------------------------------------------
def fill_bar(active: dict, state: dict, bar, side_rule: str) -> list:
    """active: 番号 → 注文。state: 番号 → {"fill_px": 約定値段, "fill_bar": 足, "px": 決まった値段}。
    返すのは [(番号, 値段, 量, 当たり方)]。"""
    k, o, h, lo, c = bar
    out = []

    def try_range_open(oid, side, px):
        if lo <= px <= h:
            return px, "range"
        if (px > h) if side == "buy" else (px < lo):
            return o, "open"
        return None

    def done(oid, px, qty, case):
        state[oid] = {**state.get(oid, {}), "fill_px": px, "fill_bar": k}
        out.append((oid, px, qty, case))

    # 成行・指値(根)
    for oid, od in active.items():
        if oid in state and "fill_px" in state[oid]:
            continue
        if od["form"] == "market":
            done(oid, o, od["qty"], "market")
        elif od["form"] == "limit":
            r = try_range_open(oid, od["side"], od["px"])
            if r:
                done(oid, r[0], od["qty"], r[1])
    # 段
    for oid, od in active.items():
        if od["form"] != "level" or (oid in state and "fill_px" in state[oid]):
            continue
        root = state.get(od["root"])
        if not root or "fill_px" not in root:
            continue
        px = state.get(oid, {}).get("px")
        if px is None:
            px = floor_tick(Decimal(repr(root["fill_px"])) + Decimal(repr(od["off"])))
            state[oid] = {"px": px, "since": k}
        if state[oid]["since"] == k:  # 根の足: 範囲の内だけ
            if lo <= px <= h:
                done(oid, px, od["qty"], "anchor_bar")
        else:
            r = try_range_open(oid, od["side"], px)
            if r:
                done(oid, r[0], od["qty"], r[1])
    # 利確
    for oid, od in active.items():
        if od["form"] != "exit" or (oid in state and "fill_px" in state[oid]):
            continue
        parent = state.get(od["parent"])
        if not parent or "fill_px" not in parent:
            continue
        if parent["fill_bar"] == k:
            if side_rule == "optimistic" and lo <= od["px"] <= h:
                done(oid, od["px"], od["qty"], "entry_bar")
        else:
            r = try_range_open(oid, od["side"], od["px"])
            if r:
                done(oid, r[0], od["qty"], r[1])
    return out


# ---- 代わりの戦略 ---------------------------------------------------------------------
class Ladder:
    def __init__(self, levels=7, n=40, entry=0.7, exit_=0.3, hold=20):
        self.levels, self.n, self.entry, self.exit_, self.hold = levels, n, entry, exit_, hold
        self.win = deque(maxlen=n)
        self.pos = 0.0
        self.since = None
        self.orders: dict = {}  # 出しておく注文(番号 → 注文)
        self.seq = 0
        self.dir = 0

    def nid(self):
        self.seq += 1
        return f"o{self.seq}"

    def on_fill(self, od, qty, k):
        s = 1 if od["side"] == "buy" else -1
        self.pos = round(self.pos + s * qty, 3)
        if self.since is None and self.pos != 0:
            self.since = k
        if self.pos == 0:
            self.since = None

    def decide(self, bar, filled: set) -> dict:
        k, o, h, lo, c = bar
        self.win.append((o, h, lo, c))
        keep = {oid: od for oid, od in self.orders.items() if oid not in filled}
        if len(self.win) < self.n:
            self.orders = keep
            return self.orders
        hi = max(x[1] for x in self.win)
        low = min(x[2] for x in self.win)
        center = round((hi + low) / 2)
        vola = sum(abs(x[3] - x[0]) for x in list(self.win)[:-1]) / (self.n - 1)
        if self.pos != 0 and self.since is not None and k - self.since > self.hold:
            self.orders = {self.nid(): {"form": "market", "side": "sell" if self.pos > 0 else "buy", "qty": abs(self.pos)}}
            return self.orders
        d = 1 if c < center - self.entry * vola else (-1 if c > center + self.entry * vola else 0)
        if d == 0 and self.pos == 0:
            self.orders, self.dir = {}, 0
            return self.orders
        if d != 0 and (d != self.dir or CHURN) and self.pos == 0:
            side = "buy" if d == 1 else "sell"
            xside = "sell" if d == 1 else "buy"
            p1 = center - d * self.entry * vola
            xp = float(round(center - d * self.exit_ * vola))
            qty = 0.009
            new = {}
            root = self.nid()
            new[root] = {"form": "limit", "side": side, "px": float(math.floor(p1)), "qty": qty}
            new[self.nid()] = {"form": "exit", "side": xside, "px": xp, "qty": qty, "parent": root}
            for j in range(1, self.levels):
                lv = self.nid()
                new[lv] = {"form": "level", "side": side, "root": root, "off": -d * j * round(vola), "qty": qty}
                new[self.nid()] = {"form": "exit", "side": xside, "px": xp, "qty": qty, "parent": lv}
            self.orders, self.dir = new, d
            return self.orders
        self.orders = keep
        return self.orders


def run(n, side_rule, out_dir):
    st = Ladder()
    active: dict = {}
    state: dict = {}
    placed: dict = {}
    nf = no = 0
    with open(os.path.join(out_dir, f"fills_{side_rule}.csv"), "w", newline="") as ff, \
            open(os.path.join(out_dir, f"orders_{side_rule}.csv"), "w", newline="") as fo:
        wf, wo = csv.writer(ff), csv.writer(fo)
        for bar in walk(n):
            fills = fill_bar(active, state, bar, side_rule)
            filled = set()
            for oid, px, qty, case in fills:
                wf.writerow((bar[0], oid, active[oid]["side"], qty, px, case))
                st.on_fill(active[oid], qty, bar[0])
                filled.add(oid)
                nf += 1
            new = st.decide(bar, filled)
            for oid in list(active):
                if oid not in new or oid in filled:
                    od = active.pop(oid)
                    s = state.pop(oid, {})
                    wo.writerow((oid, placed.pop(oid), bar[0], od["form"], od["side"], od.get("px", ""),
                                 od.get("root", od.get("parent", "")), od.get("off", ""), s.get("px", ""), od["qty"]))
                    no += 1
            for oid, od in new.items():
                if oid not in active and oid not in filled:
                    active[oid] = od
                    placed[oid] = bar[0]
            # 約定した注文の根・親の値段は、まだ出ている段・利確が使うので残す(使い終わったら消す)
            live = {od.get("root") for od in active.values()} | {od.get("parent") for od in active.values()}
            for oid in [x for x in state if x not in active and x not in live]:
                del state[oid]
    return nf, no


def main():
    n = int(sys.argv[1])
    out_dir = sys.argv[2] if len(sys.argv) > 2 else tempfile.mkdtemp()
    t0 = time.perf_counter()
    res = {s: run(n, s, out_dir) for s in ("optimistic", "pessimistic")}
    dt = time.perf_counter() - t0
    mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    print(f"bars {n} secs {dt:.2f} per_bar_us {dt / n * 1e6:.1f} maxrss_mb {mb:.0f} fills/orders {res}")


if __name__ == "__main__":
    main()
