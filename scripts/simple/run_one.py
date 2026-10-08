"""マチルダの測りを 1 本(1 つの引数の組)走らせ、書き終えた約定と合図を圧縮する(L-852・L-854)。

L-845「**では再開しマチルダの測定を1本、今の仕組みの確かめとして回してください。**」。
使い方: PYTHONPATH=src python3 scripts/simple/run_one.py <出力の置き場> [足の本数の上限] [--params '<JSON>']
走らせは足の中の道筋の 1 回だけ(L-876「**2.(a)**」。SPEC.md §3)。
引数の組は基準(BASE_PARAMS)に --params の鍵だけを上書きしたもの(本測定 PLAN.md、L-889)。足は bitFlyer Lightning FX の 1 分足、封印の境まで。
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
from bot.strategy.matilda_simple import BASE_PARAMS, MatildaSimple

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


def _args(argv):
    """<出力の置き場> [足の本数の上限] [--params '<JSON>'](L-889「**2 よい**」。基準の値のうち JSON の鍵だけ上書きする)。"""
    pos, over = [], {}
    it = iter(argv)
    for a in it:
        if a == "--params":
            over = json.loads(next(it))
        else:
            pos.append(a)
    unknown = sorted(set(over) - set(BASE_PARAMS))
    if unknown:
        raise SystemExit(f"知らない引数: {unknown}")
    return pos[0], (int(pos[1]) if len(pos) > 1 else 0), over


def main():
    out, limit, over = _args(sys.argv[1:])
    params = dict(BASE_PARAMS)
    params.update(over)
    meta = {"strategy": "matilda_simple", "params": params, "seal": SEAL,
            "bar_files": [{"path": f, "sha256": _sha(f)} for f in FILES], "bar_limit": limit}
    rep = {"params": params, "bar_limit": limit}
    t = time.time()
    run(_bars(limit), MatildaSimple(params), out_dir=out, tick=1.0, meta=meta)
    rep["run_sec"] = round(time.time() - t, 1)
    with open(os.path.join(out, "summary.json"), encoding="utf-8") as fh:
        rep["summary"] = json.load(fh)
    for name in ("fills", "signals"):  # 書き終えてから圧縮する(L-852)
        p = os.path.join(out, f"{name}.csv")
        rep[f"{name}_mb_raw"] = round(os.path.getsize(p) / 1e6, 1)
        with open(p, "rb") as src, gzip.open(p + ".gz", "wb") as dst:
            shutil.copyfileobj(src, dst)
        os.remove(p)
        rep[f"{name}_mb_gz"] = round(os.path.getsize(p + ".gz") / 1e6, 1)
    rep["max_rss_mb"] = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024)
    with open(os.path.join(out, "report.json"), "w", encoding="utf-8") as fh:
        json.dump(rep, fh, ensure_ascii=False, indent=1)
    print(json.dumps(rep, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
