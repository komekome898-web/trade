#!/usr/bin/env python3
"""K1 env fixes (2026-09-27, delegation 20260927_k1_env_fixes §2-3, D-2): fold the BitMEX XBTUSD
1-second bars 2017-2019 to 60-minute bars with ONE call of the data layer's streaming door
(`bot.bt.data.stream`: the 1,095 day files as one dataset, read file by file), and compare the
result byte for byte with stage A's 60-minute file (backtest_data/k1_newenv_a_20260927/
xbtusd_60m_2017_2019.csv.gz, made by scripts/k1_newenv_fold.py with one load() per day file).

Same allow-list as stage A (roots = the 2017 / 2018 / 2019 folders; 2020* and 2021* refused).
Same fold (`bot.bt.vector.bars_from_bars`, per file; a bar that would span two files is merged:
open of the first, max / min, close of the last, volume summed in file order). Same writer
(start_ts ISO UTC, repr of the floats). The gzip header's mtime is set to stage A's, so the
compressed bytes are comparable too.

Output: <out-dir>/xbtusd_60m_2017_2019.csv.gz and <out-dir>/STREAM_FOLD.json (wall time, max RSS,
rows, sha256 of both files compressed and uncompressed, the comparison).

Usage: PYTHONPATH=src python3 scripts/k1_newenv_fix_stream_fold.py [--days-limit N] [--out-dir DIR]
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import resource
import struct
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from bot.bt.data import stream  # noqa: E402
from bot.bt.vector import bars as VB  # noqa: E402
from k1_newenv_fold import SPEC, SRC_DIR, YEARS, allowlist, iso  # noqa: E402

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
STAGE_A = os.path.join(REPO, "backtest_data", "k1_newenv_a_20260927", "xbtusd_60m_2017_2019.csv.gz")
FOOT_S = 3600


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--days-limit", type=int, default=0, help="first N files only (a quick check; no comparison)")
    ap.add_argument("--out-dir", default=os.path.join("backtest_runs", "k1_env_fixes", "stream_fold"))
    a = ap.parse_args()
    paths = []
    for y in YEARS:
        ydir = os.path.join(REPO, SRC_DIR, str(y))
        paths += [f"{SRC_DIR}/{y}/{n}" for n in sorted(os.listdir(ydir)) if n.endswith(".csv.gz")]
    if a.days_limit:
        paths = paths[:a.days_limit]
    t0 = time.time()
    s = stream(REPO, {"name": "xbtusd_1s", "paths": paths, "spec": SPEC}, allowlist=allowlist(YEARS))
    bars: list[dict] = []
    rows = 0
    anomalies = 0
    for ch in s:  # one call: the whole dataset, file by file
        anomalies += len(ch.anomalies)
        if ch.anomalies:
            raise SystemExit(f"{ch.file.given}: {len(ch.anomalies)} anomalies; the fold does not resolve them silently")
        ev = ch.events
        rows += len(ev)
        got = VB.bars_from_bars([e.start_time_ns for e in ev], [e.open for e in ev], [e.high for e in ev],
                                [e.low for e in ev], [e.close for e in ev], [e.volume for e in ev], FOOT_S)
        if got and bars and got[0]["start_ns"] == bars[-1]["start_ns"]:
            b, g = bars[-1], got.pop(0)
            b.update(high=max(b["high"], g["high"]), low=min(b["low"], g["low"]), close=g["close"],
                     volume=b["volume"] + g["volume"])
        bars.extend(got)
        del ev, got, ch
    wall = time.time() - t0
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    out_dir = os.path.join(REPO, a.out_dir)
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "xbtusd_60m_2017_2019.csv.gz")
    with open(STAGE_A, "rb") as fh:
        a_gz = fh.read()
    mtime = struct.unpack("<I", a_gz[4:8])[0]
    text = "start_ts,o,h,l,c,vol\n" + "".join(
        f"{iso(b['start_ns'])},{b['open']!r},{b['high']!r},{b['low']!r},{b['close']!r},{b['volume']!r}\n" for b in bars)
    with open(out, "wb") as raw, gzip.GzipFile(filename="xbtusd_60m_2017_2019.csv", mode="wb", compresslevel=6,
                                               fileobj=raw, mtime=mtime) as fo:
        fo.write(text.encode("utf-8"))
    with open(out, "rb") as fh:
        b_gz = fh.read()
    a_txt = gzip.decompress(a_gz)
    b_txt = gzip.decompress(b_gz)
    sha = lambda x: hashlib.sha256(x).hexdigest()  # noqa: E731
    first_diff = None
    if a_txt != b_txt:
        al, bl = a_txt.split(b"\n"), b_txt.split(b"\n")
        for i, (x, y) in enumerate(zip(al, bl)):
            if x != y:
                first_diff = {"line": i + 1, "stage_a": x.decode(), "stream": y.decode()}
                break
        else:
            first_diff = {"line": min(len(al), len(bl)) + 1, "lines_stage_a": len(al), "lines_stream": len(bl)}
    rep = {
        "made_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "call": "bot.bt.data.stream(REPO, {name, paths: 1,095 day files, spec}, allowlist=stage A's) -- one call",
        "files": len(s.files()), "rows_1s": rows, "anomalies": anomalies, "bars_60m": len(bars),
        "wall_s": round(wall, 1), "max_rss_mb": round(rss, 1),
        "stage_a": {"path": os.path.relpath(STAGE_A, REPO), "sha256_gz": sha(a_gz), "sha256_csv": sha(a_txt),
                    "gz_mtime": mtime},
        "stream": {"path": os.path.relpath(out, REPO), "sha256_gz": sha(b_gz), "sha256_csv": sha(b_txt)},
        "identical_csv_bytes": a_txt == b_txt, "identical_gz_bytes": a_gz == b_gz, "first_difference": first_diff,
        "days_limit": a.days_limit,
    }
    with open(os.path.join(out_dir, "STREAM_FOLD.json"), "w", encoding="utf-8") as fh:
        json.dump(rep, fh, ensure_ascii=False, indent=1)
    print(json.dumps(rep, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
