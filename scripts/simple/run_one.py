"""マチルダの測りを 1 本(1 つの引数の組)走らせ、書き終えた約定と合図を圧縮する(L-852・L-854)。

L-845「**では再開しマチルダの測定を1本、今の仕組みの確かめとして回してください。**」。
使い方: PYTHONPATH=src python3 scripts/simple/run_one.py <出力の置き場> <側 optimistic|pessimistic|both> [足の本数の上限]
側ごとに別のプロセスで回すと記憶が側ごとに戻る。
引数の組は基準 1 本(原典の値 V37_ORIGINAL。FAMILIES_TO_MEASURE.md §3)。足は bitFlyer Lightning FX の 1 分足、封印の境まで。
"""
from __future__ import annotations

import glob
import gzip
import shutil
import hashlib
import itertools
import json
import os
import resource
import sys
import time

from bot.bt.simple import read_bars, run
from bot.strategy.matilda_simple import MatildaSimple
from bot.strategy.matilda_v37 import V37_ORIGINAL

SEAL = "2023-12-17T15:00:00+00:00"
FILES = sorted(glob.glob("backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_20[12][0-9].csv.gz"))
FILES = [f for f in FILES if int(f[-11:-7]) <= 2023]


def _bars(limit):
    it = read_bars(FILES, SEAL)
    return itertools.islice(it, limit) if limit else it


def _sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    out = sys.argv[1]
    which = sys.argv[2]
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    sides = ("optimistic", "pessimistic") if which == "both" else (which,)
    params = dict(V37_ORIGINAL)
    meta = {"strategy": "matilda_simple", "params": params, "seal": SEAL,
            "bar_files": [{"path": f, "sha256": _sha(f)} for f in FILES], "bar_limit": limit}
    rep = {"params": params, "bar_limit": limit, "sides": {}}
    for side in sides:
        r = {}
        t = time.time()
        run(_bars(limit), MatildaSimple(params), side=side, out_dir=out, tick=1.0, meta=meta)
        r["run_sec"] = round(time.time() - t, 1)
        with open(os.path.join(out, f"summary_{side}.json"), encoding="utf-8") as fh:
            r["summary"] = json.load(fh)
        for name in ("fills", "signals"):  # 書き終えてから圧縮する(L-852)
            p = os.path.join(out, f"{name}_{side}.csv")
            r[f"{name}_mb_raw"] = round(os.path.getsize(p) / 1e6, 1)
            with open(p, "rb") as src, gzip.open(p + ".gz", "wb") as dst:
                shutil.copyfileobj(src, dst)
            os.remove(p)
            r[f"{name}_mb_gz"] = round(os.path.getsize(p + ".gz") / 1e6, 1)
        rep["sides"][side] = r
        print(side, json.dumps(r, ensure_ascii=False), flush=True)
    rep["max_rss_mb"] = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024)
    with open(os.path.join(out, f"report_{which}.json"), "w", encoding="utf-8") as fh:
        json.dump(rep, fh, ensure_ascii=False, indent=1)
    print("max_rss_mb", rep["max_rss_mb"])


if __name__ == "__main__":
    main()
