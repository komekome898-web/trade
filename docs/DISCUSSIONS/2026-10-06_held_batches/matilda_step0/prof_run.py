"""マチルダ(v37)の 1 回の走らせを cProfile で測り、自分の時間の多い順に 15 行出す(直し A の読んだ事実)。使い方: PYTHONPATH=src python3 <このファイル> <本数>。合成の乱歩の 1 分足(σ 3,000 円、seed 0)を tmp の根に書き、市場のデータは読まない。"""
import os, sys, random, pathlib, tempfile, time, cProfile, pstats
sys.path.insert(0, "tests/road")
import test_matilda_v37_spec as T
from bot.strategy import matilda_v37 as M
n = int(sys.argv[1])
rng = random.Random(0); px = 7_000_000; bars = []
for i in range(n):
    o = px; c = o + round(rng.gauss(0, 3000)); h = max(o, c) + abs(round(rng.gauss(0, 1500))); l = min(o, c) - abs(round(rng.gauss(0, 1500)))
    bars.append((i, o, h, l, c, rng.randint(1, 10))); px = c
pr = cProfile.Profile(); t0 = time.time(); pr.enable()
res = T.run(pathlib.Path(tempfile.mkdtemp()), bars, dict(M.V37_ORIGINAL), rules={"market_ref": "next_bar_open", "self_trade": "cancel_both"})
pr.disable(); print("run", round(time.time()-t0, 1), flush=True)
pstats.Stats(pr).sort_stats("tottime").print_stats(15)
