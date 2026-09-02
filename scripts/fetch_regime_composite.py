"""Phase-1 data collection for PREREG RC1 (docs/PREREG_regime_composite.md).

Collects the six free, key-less public sources named in the pre-registration and
writes a permanent snapshot to backtest_data/regime_composite_20260901/:

  raw/binance_funding.csv     Binance USD-M monthly fundingRate  (2020-01 .. 2026-08)
  raw/binance_premium.csv     Binance USD-M premiumIndexKlines 1d (2020-01 .. 2026-08)
  raw/binance_metrics.csv     Binance USD-M daily metrics, 5-min rows averaged to
                              one row per day (2021-01-01 .. 2026-08-31)
  raw/gdelt_tone.csv          GDELT doc API timelinetone "bitcoin" (2017-01 .. 2026-08)
  raw/price_daily.csv         Bitstamp BTC/USD daily from data/attention/attention.csv
  features_daily.csv          date, funding_3d_mean, premium_1d, ls_ratio,
                              toptrader_ls, tone_7d_mean, ret_28d, close
  manifest.json               source URLs, row counts, coverage, missing days
  MD5SUMS

api.binance.com REST is geo-blocked (451) and is not used; every byte here comes
from data.binance.vision or api.gdeltproject.org.  All requests retry with
exponential backoff.  Timestamps in the Binance archives are epoch milliseconds
but a few files ship microseconds -- the unit is decided per value by digit count.

The script is resumable: whatever already sits in raw/*.csv is reused, and only
the still-missing periods are requested.  GDELT rate-limits (429) and resets
connections on year-sized queries, so its gaps are refilled in quarter-sized
chunks, spaced out.  Binance publishes the CURRENT month's premiumIndexKlines
only as daily files, so a monthly 404 falls back to per-day files.
"""

from __future__ import annotations

import concurrent.futures as cf
import csv
import hashlib
import io
import json
import sys
import time
import zipfile
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "backtest_data" / "regime_composite_20260901"
RAW = OUT / "raw"
ATTENTION = ROOT / "data" / "attention" / "attention.csv"

VISION = "https://data.binance.vision/data/futures/um"
GDELT = "https://api.gdeltproject.org/api/v2/doc/doc"
UA = {"User-Agent": "trade-research-rc1/1.0"}

FUND_START, FUND_END = (2020, 1), (2026, 8)
PREM_START, PREM_END = (2020, 1), (2026, 8)
PREM_LAST_DAY = date(2026, 8, 31)
METRICS_START = date(2021, 1, 1)
METRICS_END = date(2026, 8, 31)
GDELT_START_YEAR, GDELT_END = 2017, date(2026, 8, 31)

MISSING: dict[str, list[str]] = defaultdict(list)
URLS: dict[str, list[str]] = defaultdict(list)


def _get(url: str, timeout: int = 120, tries: int = 3, base: float = 2.0) -> bytes | None:
    """GET with retries / exponential backoff.  None on a hard 404."""
    last: Exception | None = None
    for attempt in range(tries):
        try:
            resp = requests.get(url, headers=UA, timeout=timeout)
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.content
        except requests.RequestException as exc:
            last = exc
            time.sleep(base ** (attempt + 1))
    print(f"  ! give up after {tries} tries: {url} ({last})", file=sys.stderr)
    return None


def read_existing(path: Path) -> list[dict]:
    """Rows already collected in a previous run (resume support)."""
    if not path.exists():
        return []
    with path.open() as fh:
        return list(csv.DictReader(fh))


def _unzip_rows(blob: bytes) -> list[list[str]]:
    z = zipfile.ZipFile(io.BytesIO(blob))
    text = z.read(z.namelist()[0]).decode("utf-8", "replace")
    return [r for r in csv.reader(io.StringIO(text)) if r]


def _epoch_to_utcdate(raw: str) -> date:
    """Binance ships ms, but some files ship us -- decide by digit count."""
    v = int(float(raw))
    digits = len(str(abs(v)))
    if digits >= 16:
        v //= 1_000_000          # microseconds
    elif digits >= 13:
        v //= 1_000              # milliseconds
    return datetime.fromtimestamp(v, tz=timezone.utc).date()


def _months(start: tuple[int, int], end: tuple[int, int]):
    y, m = start
    while (y, m) <= end:
        yield y, m
        m += 1
        if m == 13:
            y, m = y + 1, 1


# --------------------------------------------------------------------------- funding
def fetch_funding() -> list[dict]:
    """8-hourly funding rate -> daily mean of last_funding_rate."""
    prev = read_existing(RAW / "binance_funding.csv")
    have = {r["date"][:7] for r in prev}
    if prev:
        print(f"  resume: {len(prev)} funding days already on disk")
    per_day: dict[date, list[float]] = defaultdict(list)
    for y, m in _months(FUND_START, FUND_END):
        if f"{y}-{m:02d}" in have:
            continue
        url = f"{VISION}/monthly/fundingRate/BTCUSDT/BTCUSDT-fundingRate-{y}-{m:02d}.zip"
        blob = _get(url)
        if blob is None:
            MISSING["funding"].append(f"{y}-{m:02d}")
            continue
        URLS["funding"].append(url)
        rows = _unzip_rows(blob)
        header = [c.strip() for c in rows[0]]
        if not header[0].replace("-", "").isdigit():   # header line present
            rows = rows[1:]
        else:
            header = ["calc_time", "funding_interval_hours", "last_funding_rate"]
        i_t, i_r = header.index("calc_time"), header.index("last_funding_rate")
        for r in rows:
            per_day[_epoch_to_utcdate(r[i_t])].append(float(r[i_r]))
        print(f"  funding {y}-{m:02d}: {len(rows)} rows")
    out = {r["date"]: {"date": r["date"], "funding_rate": float(r["funding_rate"]),
                       "n": int(r["n"])}
           for r in read_existing(RAW / "binance_funding.csv")}
    for d, v in per_day.items():
        out[d.isoformat()] = {"date": d.isoformat(),
                              "funding_rate": sum(v) / len(v), "n": len(v)}
    return [out[k] for k in sorted(out)]


# --------------------------------------------------------------------------- premium
def fetch_premium() -> list[dict]:
    """Daily premium index klines -> close."""
    out: dict[date, float] = {date.fromisoformat(r["date"]): float(r["premium_close"])
                              for r in read_existing(RAW / "binance_premium.csv")}
    have = {d.isoformat()[:7] for d in out}
    if out:
        print(f"  resume: {len(out)} premium days already on disk")
    for y, m in _months(PREM_START, PREM_END):
        if f"{y}-{m:02d}" in have:
            continue
        url = (f"{VISION}/monthly/premiumIndexKlines/BTCUSDT/1d/"
               f"BTCUSDT-1d-{y}-{m:02d}.zip")
        blob = _get(url)
        if blob is None:
            # Binance publishes the current month only as daily files
            n_day = 0
            d = date(y, m, 1)
            while d.month == m and d <= PREM_LAST_DAY:
                b = _get(f"{VISION}/daily/premiumIndexKlines/BTCUSDT/1d/"
                         f"BTCUSDT-1d-{d.isoformat()}.zip")
                if b is not None:
                    rr = _unzip_rows(b)
                    if not rr[0][0].strip().replace("-", "").isdigit():
                        rr = rr[1:]
                    for r in rr:
                        out[_epoch_to_utcdate(r[0])] = float(r[4])
                    n_day += 1
                d += timedelta(days=1)
            if n_day:
                print(f"  premium {y}-{m:02d}: {n_day} days via daily fallback")
                URLS["premium"].append(f"{VISION}/daily/premiumIndexKlines/BTCUSDT/1d/"
                                       f"BTCUSDT-1d-{y}-{m:02d}-DD.zip")
            else:
                MISSING["premium"].append(f"{y}-{m:02d}")
            continue
        URLS["premium"].append(url)
        rows = _unzip_rows(blob)
        if not rows[0][0].strip().replace("-", "").isdigit():
            rows = rows[1:]
        for r in rows:
            out[_epoch_to_utcdate(r[0])] = float(r[4])   # close
        print(f"  premium {y}-{m:02d}: {len(rows)} rows")
    return [{"date": d.isoformat(), "premium_close": v} for d, v in sorted(out.items())]


# --------------------------------------------------------------------------- metrics
METRIC_COLS = ["sum_open_interest", "sum_open_interest_value",
               "count_toptrader_long_short_ratio", "sum_toptrader_long_short_ratio",
               "count_long_short_ratio", "sum_taker_long_short_vol_ratio"]


def _one_metrics_day(d: date) -> tuple[date, dict | None, str]:
    url = f"{VISION}/daily/metrics/BTCUSDT/BTCUSDT-metrics-{d.isoformat()}.zip"
    blob = _get(url)
    if blob is None:
        return d, None, url
    rows = _unzip_rows(blob)
    header = [c.strip() for c in rows[0]]
    body = rows[1:]
    idx = {c: header.index(c) for c in METRIC_COLS if c in header}
    acc: dict[str, list[float]] = defaultdict(list)
    for r in body:
        for c, i in idx.items():
            try:
                acc[c].append(float(r[i]))
            except (ValueError, IndexError):
                pass
    if not acc:
        return d, None, url
    rec = {"date": d.isoformat(), "n_5min": len(body)}
    for c in METRIC_COLS:
        rec[c] = (sum(acc[c]) / len(acc[c])) if acc.get(c) else ""
    return d, rec, url


def fetch_metrics() -> list[dict]:
    """~2,070 daily zips of 5-min rows, averaged to one row per day (size)."""
    out: dict[date, dict] = {date.fromisoformat(r["date"]): r
                             for r in read_existing(RAW / "binance_metrics.csv")}
    if out:
        print(f"  resume: {len(out)} metric days already on disk")
    days = []
    d = METRICS_START
    while d <= METRICS_END:
        if d not in out:
            days.append(d)
        d += timedelta(days=1)
    if not days:
        return [out[k] for k in sorted(out)]
    done = 0
    with cf.ThreadPoolExecutor(max_workers=4) as pool:      # polite concurrency
        for dd, rec, url in pool.map(_one_metrics_day, days):
            done += 1
            if rec is None:
                MISSING["metrics"].append(dd.isoformat())
            else:
                out[dd] = rec
                URLS["metrics"].append(url)
            if done % 200 == 0:
                print(f"  metrics {done}/{len(days)} (missing {len(MISSING['metrics'])})")
    return [out[k] for k in sorted(out)]


# --------------------------------------------------------------------------- gdelt
def _gdelt_chunk(start: date, end: date, out: dict[date, float],
                 tries: int, pause: float) -> int:
    url = (f"{GDELT}?query=bitcoin&mode=timelinetone"
           f"&STARTDATETIME={start:%Y%m%d}000000"
           f"&ENDDATETIME={end:%Y%m%d}235959&format=CSV")
    blob = _get(url, timeout=150, tries=tries, base=2.0)
    time.sleep(pause)                      # the public API rate-limits (429)
    if blob is None:
        return 0
    URLS["gdelt"].append(url)
    n = 0
    for row in csv.DictReader(io.StringIO(blob.decode("utf-8-sig", "replace"))):
        ds = (row.get("Date") or "").strip()
        if not ds or (row.get("Series") or "").strip() != "Average Tone":
            continue
        try:
            out[date.fromisoformat(ds[:10])] = float(row["Value"])
            n += 1
        except (ValueError, TypeError, KeyError):
            continue
    return n


def fetch_gdelt() -> list[dict]:
    """timelinetone 'bitcoin': a year per request, gaps refilled by quarter."""
    out: dict[date, float] = {date.fromisoformat(r["date"]): float(r["tone"])
                              for r in read_existing(RAW / "gdelt_tone.csv")}
    if out:
        print(f"  resume: {len(out)} tone days already on disk")
    for year in range(GDELT_START_YEAR, GDELT_END.year + 1):
        start, end = date(year, 1, 1), min(date(year, 12, 31), GDELT_END)
        span_days = (end - start).days + 1
        have = sum(1 for d in out if start <= d <= end)
        if have >= span_days - 30:          # already dense enough
            continue
        # a year-sized query is what GDELT resets / 429s on, so fill by quarter
        got = 0
        for q0 in (1, 4, 7, 10):
            qs = date(year, q0, 1)
            qe = min(date(year + (q0 == 10), (q0 + 3 - 1) % 12 + 1, 1)
                     - timedelta(days=1), GDELT_END)
            if qs > GDELT_END:
                break
            got += _gdelt_chunk(qs, qe, out, tries=3, pause=5.0)
        if got:
            print(f"  gdelt {year}: {got} rows (quarter chunks)")
        else:
            MISSING["gdelt"].append(str(year))
    return [{"date": d.isoformat(), "tone": v} for d, v in sorted(out.items())]


# --------------------------------------------------------------------------- price
def load_price() -> list[dict]:
    if not ATTENTION.exists():
        raise SystemExit(f"missing {ATTENTION}; run scripts/fetch_attention.py first")
    out = []
    with ATTENTION.open() as fh:
        for row in csv.DictReader(fh):
            ds, close = row["date"].strip(), (row.get("btc_usd") or "").strip()
            if len(ds) != 8 or not close:
                continue
            out.append({
                "date": f"{ds[:4]}-{ds[4:6]}-{ds[6:]}",
                "open": (row.get("btc_open") or "").strip(),
                "high": (row.get("btc_high") or "").strip(),
                "low": (row.get("btc_low") or "").strip(),
                "close": close,
            })
    URLS["price"].append(str(ATTENTION.relative_to(ROOT)) +
                         " (Bitstamp daily via scripts/fetch_attention.py)")
    return out


# --------------------------------------------------------------------------- features
def build_features(funding, premium, metrics, tone, price) -> list[dict]:
    f = {r["date"]: r["funding_rate"] for r in funding}
    p = {r["date"]: r["premium_close"] for r in premium}
    ls = {r["date"]: r["count_long_short_ratio"] for r in metrics
          if r.get("count_long_short_ratio") != ""}
    tt = {r["date"]: r["sum_toptrader_long_short_ratio"] for r in metrics
          if r.get("sum_toptrader_long_short_ratio") != ""}
    tn = {r["date"]: r["tone"] for r in tone}
    px = {r["date"]: float(r["close"]) for r in price}

    all_days = sorted(set(f) | set(p) | set(ls) | set(tt) | set(tn) | set(px))
    start, end = date.fromisoformat(all_days[0]), date.fromisoformat(all_days[-1])
    grid, d = [], start
    while d <= end:
        grid.append(d.isoformat())
        d += timedelta(days=1)

    rows = []
    for i, ds in enumerate(grid):
        # 3-day mean of funding over the trailing calendar window (>=1 obs)
        win = [f[k] for k in grid[max(0, i - 2):i + 1] if k in f]
        fund3 = sum(win) / len(win) if win else ""
        win7 = [tn[k] for k in grid[max(0, i - 6):i + 1] if k in tn]
        tone7 = sum(win7) / len(win7) if len(win7) >= 4 else ""
        # 28-day log return needs both endpoints on the price calendar
        ret28 = ""
        if ds in px and i >= 28 and grid[i - 28] in px:
            import math
            ret28 = math.log(px[ds] / px[grid[i - 28]])
        rows.append({
            "date": ds,
            "funding_3d_mean": fund3,
            "premium_1d": p.get(ds, ""),
            "ls_ratio": ls.get(ds, ""),
            "toptrader_ls": tt.get(ds, ""),
            "tone_7d_mean": tone7,
            "ret_28d": ret28,
            "close": px.get(ds, ""),
        })
    return rows


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"  wrote {path.relative_to(ROOT)} ({len(rows)} rows)")


def span(rows: list[dict]) -> dict:
    if not rows:
        return {"rows": 0}
    return {"rows": len(rows), "first": rows[0]["date"], "last": rows[-1]["date"]}


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    print("[1/5] funding rate")
    funding = fetch_funding()
    print("[2/5] premium index")
    premium = fetch_premium()
    print("[3/5] daily metrics (2,070 files, 4 workers)")
    metrics = fetch_metrics()
    print("[4/5] gdelt tone")
    tone = fetch_gdelt()
    print("[5/5] price")
    price = load_price()

    write_csv(RAW / "binance_funding.csv", funding, ["date", "funding_rate", "n"])
    write_csv(RAW / "binance_premium.csv", premium, ["date", "premium_close"])
    write_csv(RAW / "binance_metrics.csv", metrics, ["date", "n_5min"] + METRIC_COLS)
    write_csv(RAW / "gdelt_tone.csv", tone, ["date", "tone"])
    write_csv(RAW / "price_daily.csv", price, ["date", "open", "high", "low", "close"])

    feats = build_features(funding, premium, metrics, tone, price)
    fields = ["date", "funding_3d_mean", "premium_1d", "ls_ratio",
              "toptrader_ls", "tone_7d_mean", "ret_28d", "close"]
    write_csv(OUT / "features_daily.csv", feats, fields)

    nonnull = {c: sum(1 for r in feats if r[c] != "") for c in fields[1:]}
    manifest = {
        "prereg": "docs/PREREG_regime_composite.md (frozen 2026-09-01)",
        "collected_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sources": {
            "funding": {"url_pattern": f"{VISION}/monthly/fundingRate/BTCUSDT/"
                                       "BTCUSDT-fundingRate-YYYY-MM.zip",
                        "files": len(URLS["funding"]), **span(funding)},
            "premium": {"url_pattern": f"{VISION}/monthly/premiumIndexKlines/BTCUSDT/1d/"
                                       "BTCUSDT-1d-YYYY-MM.zip",
                        "files": len(URLS["premium"]), **span(premium)},
            "metrics": {"url_pattern": f"{VISION}/daily/metrics/BTCUSDT/"
                                       "BTCUSDT-metrics-YYYY-MM-DD.zip",
                        "files": len(URLS["metrics"]),
                        "note": "5-min rows averaged to one row per UTC day",
                        **span(metrics)},
            "gdelt": {"url_pattern": f"{GDELT}?query=bitcoin&mode=timelinetone"
                                     "&STARTDATETIME=...&ENDDATETIME=...&format=CSV",
                      "chunks": len(URLS["gdelt"]), **span(tone)},
            "price": {"source": URLS["price"][0], **span(price)},
        },
        "missing": {k: v for k, v in MISSING.items()},
        "missing_counts": {k: len(v) for k, v in MISSING.items()},
        "features_daily": {"rows": len(feats), "first": feats[0]["date"],
                           "last": feats[-1]["date"], "non_null": nonnull},
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("  wrote manifest.json")

    lines = []
    for p in sorted(OUT.rglob("*")):
        if p.is_file() and p.name != "MD5SUMS":
            lines.append(f"{hashlib.md5(p.read_bytes()).hexdigest()}  "
                         f"{p.relative_to(OUT)}")
    (OUT / "MD5SUMS").write_text("\n".join(lines) + "\n")
    print("  wrote MD5SUMS")
    print(json.dumps(manifest["missing_counts"], indent=2))


if __name__ == "__main__":
    main()
