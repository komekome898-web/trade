#!/usr/bin/env python3
"""BitMEX XBTUSD の 1 秒足(backtest_data/bitmex_trade_1s_XBTUSD/)から 1 分足を作る。

    python3 scripts/build_bitmex_xbtusd_1m.py [--out backtest_data/bitmex_XBTUSD_1m_from1s_20261002]

- 入力: 日ごとの csv.gz(列 ts,o,h,l,c,vol,buy_vol,n,max_size,n_large)。`ts` は秒の始まり(UTC、オフセット無し。
  scripts/fetch_bitmex_archive.py の `row["timestamp"][:19]`)。
- 出力: 年ごとの bitmex_XBTUSD_1m_YYYY.csv.gz。列 open_time,open,high,low,close,volume。open_time は分の始まり
  (`2017-01-01 00:00:00+00:00` の形。backtest_data/binance_BTCUSDT_1m_20170801_20231231/ と同じ)。
- 1 分の中に 1 秒足が 1 本も無い分(取引の無かった分)は行を作らない(値を埋めない)。
- 1 分足: open = その分の最初の秒の o、high = 秒の h の最大、low = 秒の l の最小、close = 最後の秒の c、
  volume = 秒の vol の和(XBTUSD の vol は契約の枚数。README)。
- 日ごとに読み、年ごとに書く(記憶は 1 年分の 1 分足だけ)。gzip の mtime=0(同じ入力なら同じ md5)。
- 検め(年ごと・年の境をまたいで)と入力の数(progress.json の bars との照合)を MANIFEST.json に書く。
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import math
import os
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "backtest_data", "bitmex_trade_1s_XBTUSD")
DEFAULT_OUT = os.path.join(ROOT, "backtest_data", "bitmex_XBTUSD_1m_from1s_20261002")
YEARS = (2017, 2018, 2019, 2020, 2021)
COLUMNS = ["open_time", "open", "high", "low", "close", "volume"]
IN_COLUMNS = ["ts", "o", "h", "l", "c", "vol", "buy_vol", "n", "max_size", "n_large"]


def _epoch_min(key: str) -> int:
    """'YYYY-MM-DDTHH:MM' -> minutes since epoch (UTC)."""
    dt = datetime(int(key[0:4]), int(key[5:7]), int(key[8:10]), int(key[11:13]), int(key[14:16]),
                  tzinfo=timezone.utc)
    return int(dt.timestamp()) // 60


def _fmt(x: float) -> str:
    return repr(float(x))


def build_year(year: int, progress: dict) -> tuple[list, dict]:
    days = sorted(f for f in os.listdir(os.path.join(SRC, str(year))) if f.endswith(".csv.gz"))
    minutes: dict = {}  # 'YYYY-MM-DDTHH:MM' -> [o, h, l, c, vol]
    inp = {"day_files": len(days), "rows_1s": 0, "progress_bars": 0, "rows_1s_vs_progress_mismatch_days": [],
           "out_of_order_1s": 0, "dup_ts_1s": 0, "date_not_file_date": 0, "minute_key_seen_in_earlier_file": 0,
           "ohlc_violation_1s": 0, "price_le_0_1s": 0, "volume_lt_0_1s": 0, "header_unexpected": 0}
    for fn in days:
        day = fn[:4] + "-" + fn[4:6] + "-" + fn[6:8]
        with gzip.open(os.path.join(SRC, str(year), fn), "rt", encoding="utf-8", newline="") as fh:
            rd = csv.reader(fh)
            header = next(rd)
            if header != IN_COLUMNS:
                inp["header_unexpected"] += 1
                raise SystemExit(f"{fn}: header {header}")
            rows = [r for r in rd if r]
        n = len(rows)
        inp["rows_1s"] += n
        pb = progress.get(day, {}).get("bars")
        inp["progress_bars"] += pb or 0
        if pb != n:
            inp["rows_1s_vs_progress_mismatch_days"].append([day, n, pb])
        ts = [r[0] for r in rows]
        inp["out_of_order_1s"] += sum(1 for a, b in zip(ts, ts[1:]) if b < a)
        inp["dup_ts_1s"] += n - len(set(ts))
        rows.sort(key=lambda r: r[0])  # stable: same-second rows keep file order
        seen_here: set = set()
        for r in rows:
            t = r[0]
            if t[:10] != day:
                inp["date_not_file_date"] += 1
            o, h, lo, c, v = float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[5])
            if h < lo or h < max(o, c) or lo > min(o, c):
                inp["ohlc_violation_1s"] += 1
            if min(o, h, lo, c) <= 0:
                inp["price_le_0_1s"] += 1
            if v < 0:
                inp["volume_lt_0_1s"] += 1
            key = t[:16]
            m = minutes.get(key)
            if m is None:
                minutes[key] = [o, h, lo, c, v]
                seen_here.add(key)
            else:
                if key not in seen_here:
                    inp["minute_key_seen_in_earlier_file"] += 1
                    seen_here.add(key)
                m[1] = max(m[1], h)
                m[2] = min(m[2], lo)
                m[3] = c
                m[4] += v
    out = [(k, *minutes[k]) for k in sorted(minutes)]
    return out, inp


def checks(rows: list, prev_last_min: int | None) -> dict:
    mins = [_epoch_min(r[0]) for r in rows]
    steps = [b - a for a, b in zip(mins, mins[1:])]
    gaps = [(rows[i][0], rows[i + 1][0], s - 1) for i, s in enumerate(steps) if s > 1]
    cross = None
    if prev_last_min is not None and mins:
        cross = mins[0] - prev_last_min - 1  # missing minutes across the year boundary
    longest = max(gaps, key=lambda g: g[2]) if gaps else None
    return {
        "rows": len(rows),
        "dup_ts": sum(1 for s in steps if s == 0),
        "out_of_order": sum(1 for s in steps if s < 0),
        "steps_not_60s": sum(1 for s in steps if s != 1),
        "gaps": len(gaps),
        "missing_minutes": sum(g[2] for g in gaps),
        "longest_gap_minutes": longest[2] if longest else 0,
        "longest_gap_between": [longest[0], longest[1]] if longest else None,
        "missing_minutes_across_previous_year_boundary": cross,
        "high_lt_low": sum(1 for r in rows if r[2] < r[3]),
        "high_lt_max_open_close": sum(1 for r in rows if r[2] < max(r[1], r[4])),
        "low_gt_min_open_close": sum(1 for r in rows if r[3] > min(r[1], r[4])),
        "price_le_0": sum(1 for r in rows if min(r[1:5]) <= 0),
        "price_not_finite": sum(1 for r in rows if not all(math.isfinite(x) for x in r[1:5])),
        "volume_lt_0": sum(1 for r in rows if r[5] < 0),
        "volume_eq_0": sum(1 for r in rows if r[5] == 0),
    }, (mins[-1] if mins else prev_last_min)


def write_year(path: str, rows: list) -> tuple[str, int]:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(COLUMNS)
    for k, o, h, lo, c, v in rows:
        w.writerow([f"{k[:10]} {k[11:16]}:00+00:00", _fmt(o), _fmt(h), _fmt(lo), _fmt(c), _fmt(v)])
    data = buf.getvalue().encode("utf-8")
    with open(path, "wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz:
            gz.write(data)
    with open(path, "rb") as fh:
        blob = fh.read()
    return hashlib.md5(blob).hexdigest(), len(blob)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=DEFAULT_OUT)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(SRC, "progress.json"), encoding="utf-8") as fh:
        progress = json.load(fh)
    manifest = {
        "source_dir": "backtest_data/bitmex_trade_1s_XBTUSD",
        "source_note": "scripts/fetch_bitmex_archive.py が BitMEX の公開の約定アーカイブから作った 1 秒足。"
                       "ts = 秒の始まり、UTC、オフセット無し(row['timestamp'][:19])",
        "built_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "builder": "scripts/build_bitmex_xbtusd_1m.py",
        "time_column": "open_time",
        "columns": COLUMNS,
        "minute_without_trade": "行を作らない(値を埋めない)",
        "years": {},
    }
    prev = None
    total = 0
    for y in YEARS:
        rows, inp = build_year(y, progress)
        chk, prev = checks(rows, prev)
        name = f"bitmex_XBTUSD_1m_{y}.csv.gz"
        md5, size = write_year(os.path.join(a.out, name), rows)
        total += len(rows)
        manifest["years"][str(y)] = {"file": name, "rows": len(rows), "first": rows[0][0] + ":00Z",
                                     "last": rows[-1][0] + ":00Z", "md5": md5, "bytes": size, "checks": chk,
                                     "input": inp}
        print(y, len(rows), md5, size, json.dumps(chk, ensure_ascii=False), json.dumps(inp, ensure_ascii=False),
              flush=True)
        del rows
    manifest["rows_total"] = total
    with open(os.path.join(a.out, "MANIFEST.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
