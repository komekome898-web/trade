"""マチルダ(v37)の 1 回の走らせの時間を合成の乱歩の 1 分足で測る(L-805・L-813)。使い方: PYTHONPATH=src python3 <このファイル> <本数> <seed> <σ>。tmp の根に書き、市場のデータは読まない。原典の値(V37_ORIGINAL)、self_trade = cancel_both、execute_once(1 回だけ、良い側・悪い側の両方)。"""
import os, sys, time, random, importlib
sys.path.insert(0, "tests/road")
import test_matilda_v37_spec as T
from bot.bt import pipeline as P
from bot.strategy import matilda_v37 as M
n = int(sys.argv[1]); seed = int(sys.argv[2]); sig = float(sys.argv[3])
rng = random.Random(seed); px = 7_000_000; bars = []
for i in range(n):
    o = px; c = o + round(rng.gauss(0, sig)); h = max(o, c) + abs(round(rng.gauss(0, sig/2))); l = min(o, c) - abs(round(rng.gauss(0, sig/2)))
    bars.append((i, o, h, l, c, rng.randint(1, 10))); px = c
import tempfile
root = tempfile.mkdtemp(); T._write_bars(root, bars)
plan = T._plan(root, "bot.strategy.matilda_v37", dict(M.V37_ORIGINAL), rules={"market_ref": "next_bar_open", "self_trade": "cancel_both"})
out = os.path.join(root, "out"); os.makedirs(out)
t0 = time.time(); res = P.execute_once(plan, out); dt = time.time() - t0
nf = {s: sum(len(r.fills) for r in res["range"][s].values()) for s in P.SIDES}
print(f"bars {n} seed {seed} sigma {sig} execute_once {dt:.1f}s fills {nf}")
