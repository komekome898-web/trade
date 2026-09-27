#!/usr/bin/env python3
"""K1 stage A (2026-09-27, L-479): fold the BitMEX XBTUSD 1-second bars of
2017-2019 to `foot` minutes THROUGH THE DATA LAYER of the new environment.

Every day file is read by `bot.bt.data.load` under an allow-list whose only
roots are backtest_data/bitmex_trade_1s_XBTUSD/2017, /2018, /2019 (2020 and
2021, the sealed judgement window of K1, and every other folder are refused
by the allow-list before a byte is read; the refusal is also proven at start
by trying one 2020 file). The fold is `bot.bt.vector.bars_from_bars` (K1
RESULT.md 1.2: UTC wall clock, open = first, high = max, low = min, close =
last, an interval with no 1-second bar has no bar).

Outputs (under backtest_data/k1_newenv_a_20260927/):
  xbtusd_{foot}m_2017_2019.csv.gz  start_ts,o,h,l,c,vol (start_ts = ISO UTC, bar start)
  FOLD_MANIFEST.json               every input file (path, size, sha256, rows), the
                                   allow-list, the spec, anomalies, the fold source
                                   sha256, the outputs' sha256 / rows, wall time and
                                   max RSS per year

Usage: PYTHONPATH=src python3 scripts/k1_newenv_fold.py [--years 2017 2018 2019] [--feet 1 3 5 15 30 60]
       [--days-limit N] (N days per year, for a quick check)
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import inspect
import json
import os
import resource
import sys
import time
from datetime import datetime, timezone
from multiprocessing import Pool

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from bot.bt.data import AllowList, PathRefused, load  # noqa: E402
from bot.bt.vector import bars as VB  # noqa: E402

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SRC_DIR = "backtest_data/bitmex_trade_1s_XBTUSD"
OUT_DIR = "backtest_data/k1_newenv_a_20260927"
YEARS = (2017, 2018, 2019)
FEET = (1, 3, 5, 15, 30, 60)
NS = 1_000_000_000
SPEC = {"format": "csv", "header": True, "delimiter": ",", "compression": "gzip", "kind": "bar",
        "symbol": "XBTUSD", "asset": "crypto",
        "time": {"columns": ["ts"], "unit": "iso", "tz": "UTC"},
        "fields": {"open": "o", "high": "h", "low": "l", "close": "c", "volume": "vol"},
        "bar": {"interval_s": 1, "label": "start"}, "key": "start"}


def allowlist(years) -> AllowList:
    roots = tuple(f"{SRC_DIR}/{y}" for y in years)
    deny = tuple((f"{y}*", f"K1 sealed judgement window / not stage A ({y})") for y in (2020, 2021))
    return AllowList(roots=roots, extra_deny=deny)


def iso(ns: int) -> str:
    return datetime.fromtimestamp(ns // NS, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def fold_year(args):
    year, feet, days_limit = args
    al = allowlist(YEARS)
    ydir = os.path.join(REPO, SRC_DIR, str(year))
    names = sorted(n for n in os.listdir(ydir) if n.endswith(".csv.gz"))
    if days_limit:
        names = names[:days_limit]
    files, anomalies, out = [], {}, {f: [] for f in feet}
    t0 = time.time()
    rows_total = 0
    for name in names:
        rel = f"{SRC_DIR}/{year}/{name}"
        r = load(REPO, [{"name": "d", "paths": [rel], "spec": SPEC}], allowlist=al)
        an = r.anomalies("d")
        if an:
            anomalies[rel] = an[:20]
            raise SystemExit(f"{rel}: {len(an)} anomalies ({an[0]}); the fold does not resolve them silently")
        ev = r.events("d")
        rows_total += len(ev)
        st = [e.start_time_ns for e in ev]
        o = [e.open for e in ev]
        h = [e.high for e in ev]
        lo = [e.low for e in ev]
        c = [e.close for e in ev]
        v = [e.volume for e in ev]
        for f in feet:
            out[f].extend(VB.bars_from_bars(st, o, h, lo, c, v, f * 60))
        for fr in r.files():
            d = fr.__dict__.copy()
            d.pop("real", None)
            files.append(d)
    wall = time.time() - t0
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    return {"year": year, "files": files, "rows": rows_total, "wall_s": round(wall, 1), "max_rss_mb": round(rss, 1),
            "bars": {f: out[f] for f in feet}}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--years", type=int, nargs="+", default=list(YEARS))
    ap.add_argument("--feet", type=int, nargs="+", default=list(FEET))
    ap.add_argument("--days-limit", type=int, default=0)
    ap.add_argument("--out-dir", default=OUT_DIR)
    a = ap.parse_args()
    for y in a.years:
        if y not in YEARS:
            raise SystemExit(f"year {y} is outside stage A (2017-2019)")
    al = allowlist(YEARS)
    # the refusal of the sealed window is proven, not assumed
    refused = {}
    for probe in (f"{SRC_DIR}/2020/20200101.csv.gz", f"{SRC_DIR}/2021/20211231.csv.gz",
                  "backtest_data/binance_BTCUSDT_1m.csv"):
        try:
            load(REPO, [{"name": "d", "paths": [probe], "spec": SPEC}], allowlist=al)
            raise SystemExit(f"{probe} was NOT refused by the allow-list")
        except PathRefused as exc:
            refused[probe] = str(exc)[:200]
    t0 = time.time()
    with Pool(len(a.years)) as pool:
        results = pool.map(fold_year, [(y, tuple(a.feet), a.days_limit) for y in a.years])
    wall = time.time() - t0
    out_dir = os.path.join(REPO, a.out_dir)
    os.makedirs(out_dir, exist_ok=True)
    outputs = {}
    for f in a.feet:
        path = os.path.join(out_dir, f"xbtusd_{f}m_{a.years[0]}_{a.years[-1]}.csv.gz")
        n = 0
        last = None
        with gzip.open(path, "wt", encoding="utf-8", newline="\n", compresslevel=6) as fh:
            fh.write("start_ts,o,h,l,c,vol\n")
            for res in results:
                for b in res["bars"][f]:
                    if last is not None and b["start_ns"] <= last:
                        raise SystemExit(f"foot {f}: bar start {b['start_ns']} not after {last}")
                    last = b["start_ns"]
                    fh.write(f"{iso(b['start_ns'])},{b['open']!r},{b['high']!r},{b['low']!r},{b['close']!r},{b['volume']!r}\n")
                    n += 1
        with open(path, "rb") as fh:
            sha = hashlib.sha256(fh.read()).hexdigest()
        outputs[os.path.relpath(path, REPO)] = {"foot_min": f, "rows": n, "sha256": sha}
    src = inspect.getsource(VB.bars_from_bars)
    manifest = {
        "made_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "purpose": "K1 stage A (L-479): 1-second bars -> foot-minute bars through the data layer",
        "allowlist": {"roots": ["/".join(r) for r in al.roots], "deny": [p for p, _ in al.deny]},
        "refusals_proven": refused,
        "spec_1s": SPEC,
        "fold": {"function": "bot.bt.vector.bars.bars_from_bars", "source_sha256": hashlib.sha256(src.encode()).hexdigest()},
        "years": [{k: v for k, v in res.items() if k != "bars"} | {"n_files": len(res["files"])} for res in results],
        "inputs": [f for res in results for f in res["files"]],
        "rows_1s_total": sum(res["rows"] for res in results),
        "outputs": outputs,
        "wall_s_total": round(wall, 1),
        "max_rss_mb_parent": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
        "max_rss_mb_children": round(resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1024, 1),
    }
    with open(os.path.join(out_dir, "FOLD_MANIFEST.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in manifest.items() if k != "inputs"}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
