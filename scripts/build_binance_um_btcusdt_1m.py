"""Binance USD-M BTCUSDT 1m: monthly 2020-01..2023-11 + daily 2023-12-01..17 -> yearly csv.gz + MANIFEST + MD5SUMS."""
import csv, gzip, hashlib, json, sys, time
from datetime import datetime, timezone
from pathlib import Path
import requests

sys.path.insert(0, "/home/user/trade/scripts")
from fetch_binance_vision import fetch_one, iter_zip_rows, normalize_epoch, verify_checksum, OUT_COLUMNS

ROOT = Path("/home/user/trade/backtest_data/binance_um_BTCUSDT_1m_20261002")
RAW = ROOT / "raw"
B = "https://data.binance.vision/data/futures/um"
MONTHS = [f"{y}-{m:02d}" for y in range(2020, 2024) for m in range(1, 13) if (y, m) <= (2023, 11)]
DAYS = [f"2023-12-{d:02d}" for d in range(1, 18)]
mode = sys.argv[1] if len(sys.argv) > 1 else "all"

if mode in ("fetch", "all"):
    s = requests.Session(); s.headers.update({"User-Agent": "trade-bot-research/1.0 (+backtest data)"})
    missing = []
    for m in MONTHS:
        ok = fetch_one(s, f"{B}/monthly/klines/BTCUSDT/1m/BTCUSDT-1m-{m}.zip", RAW / f"BTCUSDT-1m-{m}.zip", 0.2)
        if not ok: missing.append(m)
    for d in DAYS:
        ok = fetch_one(s, f"{B}/daily/klines/BTCUSDT/1m/BTCUSDT-1m-{d}.zip", RAW / "daily_2023_12" / f"BTCUSDT-1m-{d}.zip", 0.2)
        if not ok: missing.append(d)
    print("fetch missing(404):", missing)

if mode in ("build", "all"):
    zips = [RAW / f"BTCUSDT-1m-{m}.zip" for m in MONTHS] + [RAW / "daily_2023_12" / f"BTCUSDT-1m-{d}.zip" for d in DAYS]
    # 1) re-verify every zip from disk against its .CHECKSUM
    ck_ok = sum(verify_checksum(z.read_bytes(), Path(str(z) + ".CHECKSUM").read_text()) for z in zips)
    print(f"checksum {ck_ok}/{len(zips)} OK")
    if ck_ok != len(zips):
        sys.exit("checksum failure")
    # 2) read rows, keep every row (no dedup), note unit
    by_year = {}
    units = {"ms": 0, "us": 0}
    raw_rows = 0
    for z in zips:
        for r in iter_zip_rows(z):
            raw_rows += 1
            t0 = int(r[0]); units["us" if t0 >= 1e14 else "ms"] += 1
            ts = normalize_epoch(t0)
            y = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).year
            by_year.setdefault(y, []).append((ts, r[1], r[2], r[3], r[4], r[5], r[7], r[8], r[9]))
    years = {}
    tot = {"rows": 0, "dup_ts": 0, "dup_ts_differing_content": 0, "steps_not_60s": 0, "missing_minutes": 0,
           "high_lt_low": 0, "high_lt_max_open_close": 0, "low_gt_min_open_close": 0, "price_le_0": 0,
           "volume_lt_0": 0, "n_trades_0": 0, "out_of_order": 0}
    longest = None
    prev_last = None
    for y in sorted(by_year):
        rows = by_year[y]
        st = {k: 0 for k in tot}
        st["rows"] = len(rows)
        # duplicates & order (before any sort)
        seen = {}
        for i, row in enumerate(rows):
            if i and row[0] < rows[i - 1][0]: st["out_of_order"] += 1
            if row[0] in seen:
                st["dup_ts"] += 1
                if seen[row[0]] != row: st["dup_ts_differing_content"] += 1
            else:
                seen[row[0]] = row
        if st["dup_ts_differing_content"]:
            sys.exit(f"{y}: duplicates with differing content: {st['dup_ts_differing_content']}")
        if st["dup_ts"] or st["out_of_order"]:
            sys.exit(f"{y}: dup={st['dup_ts']} out_of_order={st['out_of_order']} -- stop and report")
        ts_list = [r[0] for r in rows]
        if prev_last is not None:
            ts_list_chk = [prev_last] + ts_list  # step across year boundary counted in the later year
        else:
            ts_list_chk = ts_list
        ylong = None
        for a, b in zip(ts_list_chk, ts_list_chk[1:]):
            if b - a != 60000:
                st["steps_not_60s"] += 1
                miss = (b - a) // 60000 - 1
                st["missing_minutes"] += miss
                if ylong is None or b - a > ylong[0]: ylong = (b - a, a, b)
        for row in rows:
            o, h, l, c = (float(row[k]) for k in (1, 2, 3, 4))
            if h < l: st["high_lt_low"] += 1
            if h < max(o, c): st["high_lt_max_open_close"] += 1
            if l > min(o, c): st["low_gt_min_open_close"] += 1
            if min(o, h, l, c) <= 0: st["price_le_0"] += 1
            if float(row[5]) < 0: st["volume_lt_0"] += 1
            if row[7].strip() == "0": st["n_trades_0"] += 1
        iso = lambda ms: datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S+00:00")
        if ylong:
            st["longest_step"] = {"minutes": ylong[0] // 60000, "from": iso(ylong[1]), "to": iso(ylong[2])}
            if longest is None or ylong[0] > longest[0]: longest = ylong
        out = ROOT / f"binance_um_BTCUSDT_1m_{y}.csv.gz"
        with gzip.open(out, "wt", newline="") as f:
            w = csv.writer(f); w.writerow(OUT_COLUMNS)
            for r in rows:
                w.writerow([iso(r[0])] + list(r[1:]))
        data = out.read_bytes()
        years[str(y)] = {"rows": len(rows), "first": iso(rows[0][0]), "last": iso(rows[-1][0]),
                         "md5": hashlib.md5(data).hexdigest(), "bytes": len(data), "checks": st}
        for k in tot: tot[k] += st[k]
        prev_last = rows[-1][0]
    iso = lambda ms: datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S+00:00")
    tot["longest_step"] = {"minutes": longest[0] // 60000, "from": iso(longest[1]), "to": iso(longest[2])} if longest else None
    manifest = {
        "source": {"monthly": f"{B}/monthly/klines/BTCUSDT/1m/BTCUSDT-1m-YYYY-MM.zip (2020-01..2023-11)",
                   "daily": f"{B}/daily/klines/BTCUSDT/1m/BTCUSDT-1m-2023-12-DD.zip (2023-12-01..2023-12-17)",
                   "fetched_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                   "monthly_404": ["2019-09", "2019-10", "2019-11", "2019-12"]},
        "time_column": "open_time", "columns": OUT_COLUMNS,
        "raw_zip_count": len(zips), "raw_zip_checksum_sha256_ok": f"{ck_ok}/{len(zips)}",
        "raw_rows_read": raw_rows, "raw_time_unit_rows": units,
        "years": years, "checks_total": tot,
        "notes": "steps_not_60s: consecutive rows whose open_time step != 60 s (step across a year boundary is counted "
                 "in the later year); missing_minutes: sum of (step/60s - 1); OHLC counters are separate (a row can "
                 "hit more than one); n_trades_0 = rows with n_trades == 0 (informational).",
    }
    (ROOT / "MANIFEST.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({k: manifest[k] for k in ("raw_zip_checksum_sha256_ok", "raw_rows_read", "raw_time_unit_rows",
                                               "checks_total")}, ensure_ascii=False))
    for y, v in years.items():
        print(y, json.dumps(v, ensure_ascii=False))
