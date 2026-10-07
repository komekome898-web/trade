"""マチルダ(v37)の 1 回の走らせの後の置き場の検査 check_outputs を cProfile で測る(直し A の読んだ事実)。使い方: PYTHONPATH=src python3 <このファイル> <本数>。合成の乱歩の 1 分足(σ 3,000 円、seed 0)を tmp の根に書き、市場のデータは読まない。"""
import os, sys, random, pathlib, tempfile, time, cProfile, pstats
sys.path.insert(0, "tests/road")
import test_matilda_v37_spec as T
from bot.strategy import matilda_v37 as M
from bot.bt.road import check_outputs
n = int(sys.argv[1])
def walk(n, seed, sig):
    rng = random.Random(seed); px = 7_000_000; bars = []
    for i in range(n):
        o = px; c = o + round(rng.gauss(0, sig)); h = max(o, c) + abs(round(rng.gauss(0, sig/2))); l = min(o, c) - abs(round(rng.gauss(0, sig/2)))
        bars.append((i, o, h, l, c, rng.randint(1, 10))); px = c
    return bars
t0 = time.time()
res = T.run(pathlib.Path(tempfile.mkdtemp()), walk(n, 0, 3000), dict(M.V37_ORIGINAL), rules={"market_ref": "next_bar_open", "self_trade": "cancel_both"})
print("run", round(time.time()-t0, 1), flush=True)
pr = cProfile.Profile(); t0 = time.time(); pr.enable()
f = check_outputs(res["store"], res["bars"]).failures
pr.disable(); print("check", round(time.time()-t0, 1), len(f), flush=True)
pstats.Stats(pr).sort_stats("cumulative").print_stats(18)
