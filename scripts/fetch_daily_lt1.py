"""LT1 データ取得 — BTCUSD / ETHUSD 日足を「取得可能な最長」で複数ソースから収集する。

docs/PREREG_trend_lt1.md §3 のためのフェーズ1スクリプト。取得のみを行い、分析は
scripts/research_trend_lt1.py が担当する(取得と分析の分離)。

ソース(公開・無認証):
  - bitstamp   : REST /api/v2/ohlc/<pair>/?step=86400&limit=1000&start=<unix>
                 BTC/USD は 2011-08 起点。ページング。
  - yahoo      : query1.finance.yahoo.com /v8/finance/chart/BTC-USD (2014-09 起点)
  - coinbase   : api.exchange.coinbase.com /products/BTC-USD/candles (2015 起点、300本/req)

出力: backtest_data/daily_<sym>_<source>_20260828.csv.gz
      列 = date(UTC, YYYY-MM-DD), open, high, low, close, volume

到達不可のソースはログに事実を記録して次へ進む(PREREG 指示)。
冪等: 既存ファイルがあり --force がなければ再取得しない。
"""

from __future__ import annotations

import argparse
import gzip
import io
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "backtest_data"
STAMP = "20260828"
UA = "Mozilla/5.0 (research; daily OHLC snapshot)"
DAY = 86400


def log(msg: str) -> None:
    print(f"[fetch_daily_lt1] {msg}", flush=True)


def http_get(url: str, timeout: int = 60, retries: int = 4) -> bytes:
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"GET failed after {retries}: {url}: {last}")


def ts_to_date(ts: int) -> str:
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d")


# ----------------------------------------------------------------- bitstamp
def fetch_bitstamp(pair: str, start_unix: int) -> dict[str, tuple]:
    rows: dict[str, tuple] = {}
    cur = start_unix
    now = int(time.time())
    stall = 0
    while cur < now:
        url = (
            f"https://www.bitstamp.net/api/v2/ohlc/{pair}/"
            f"?step={DAY}&limit=1000&start={cur}"
        )
        payload = json.loads(http_get(url))
        ohlc = payload.get("data", {}).get("ohlc", [])
        if not ohlc:
            stall += 1
            if stall >= 2:
                break
            cur += 1000 * DAY
            continue
        stall = 0
        maxts = cur
        for c in ohlc:
            ts = int(c["timestamp"])
            maxts = max(maxts, ts)
            rows[ts_to_date(ts)] = (
                float(c["open"]),
                float(c["high"]),
                float(c["low"]),
                float(c["close"]),
                float(c["volume"]),
            )
        log(f"  bitstamp {pair}: +{len(ohlc)} rows, cursor {ts_to_date(maxts)}, total {len(rows)}")
        if maxts <= cur:
            break
        cur = maxts + DAY
        time.sleep(0.35)
    return rows


# -------------------------------------------------------------------- yahoo
def fetch_yahoo(symbol: str) -> dict[str, tuple]:
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        f"?period1=1000000000&period2={int(time.time())}&interval=1d"
    )
    payload = json.loads(http_get(url))
    res = payload["chart"]["result"][0]
    stamps = res["timestamp"]
    q = res["indicators"]["quote"][0]
    rows: dict[str, tuple] = {}
    for i, ts in enumerate(stamps):
        o, h, l, c, v = q["open"][i], q["high"][i], q["low"][i], q["close"][i], q["volume"][i]
        if c is None:
            continue
        rows[ts_to_date(ts)] = (
            float(o) if o is not None else float(c),
            float(h) if h is not None else float(c),
            float(l) if l is not None else float(c),
            float(c),
            float(v) if v is not None else 0.0,
        )
    return rows


# ----------------------------------------------------------------- coinbase
def fetch_coinbase(product: str, start_unix: int) -> dict[str, tuple]:
    rows: dict[str, tuple] = {}
    cur = start_unix
    now = int(time.time())
    while cur < now:
        end = min(cur + 295 * DAY, now)
        url = (
            f"https://api.exchange.coinbase.com/products/{product}/candles"
            f"?granularity={DAY}"
            f"&start={datetime.fromtimestamp(cur, tz=timezone.utc).isoformat()}"
            f"&end={datetime.fromtimestamp(end, tz=timezone.utc).isoformat()}"
        )
        try:
            data = json.loads(http_get(url, retries=3))
        except Exception as exc:  # noqa: BLE001
            log(f"  coinbase {product}: window {ts_to_date(cur)} failed: {exc}")
            cur = end + DAY
            continue
        for c in data:
            ts, lo, hi, op, cl, vol = c[0], c[1], c[2], c[3], c[4], c[5]
            rows[ts_to_date(int(ts))] = (
                float(op), float(hi), float(lo), float(cl), float(vol)
            )
        log(f"  coinbase {product}: window {ts_to_date(cur)} +{len(data)}, total {len(rows)}")
        cur = end + DAY
        time.sleep(0.4)
    return rows


def write_csv_gz(rows: dict[str, tuple], path: Path) -> None:
    buf = io.StringIO()
    buf.write("date,open,high,low,close,volume\n")
    for d in sorted(rows):
        o, h, l, c, v = rows[d]
        buf.write(f"{d},{o},{h},{l},{c},{v}\n")
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        fh.write(buf.getvalue())
    ds = sorted(rows)
    log(f"WROTE {path.name}: n={len(rows)} {ds[0]}..{ds[-1]}")


JOBS = [
    ("btcusd", "bitstamp", lambda: fetch_bitstamp("btcusd", 1313971200)),   # 2011-08-22
    ("btcusd", "yahoo", lambda: fetch_yahoo("BTC-USD")),
    ("btcusd", "coinbase", lambda: fetch_coinbase("BTC-USD", 1420070400)),  # 2015-01-01
    ("ethusd", "bitstamp", lambda: fetch_bitstamp("ethusd", 1451606400)),   # 2016-01-01
    ("ethusd", "yahoo", lambda: fetch_yahoo("ETH-USD")),
    ("ethusd", "coinbase", lambda: fetch_coinbase("ETH-USD", 1451606400)),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--only", default="")
    args = ap.parse_args()

    failures = []
    for sym, src, fn in JOBS:
        if args.only and args.only not in f"{sym}_{src}":
            continue
        path = OUT / f"daily_{sym}_{src}_{STAMP}.csv.gz"
        if path.exists() and not args.force:
            log(f"SKIP existing {path.name}")
            continue
        log(f"FETCH {sym} from {src}")
        try:
            rows = fn()
        except Exception as exc:  # noqa: BLE001
            log(f"UNREACHABLE {sym}/{src}: {exc}")
            failures.append((sym, src, str(exc)))
            continue
        if not rows:
            log(f"EMPTY {sym}/{src}")
            failures.append((sym, src, "empty"))
            continue
        write_csv_gz(rows, path)

    if failures:
        log("FAILURES: " + json.dumps(failures))
    return 0


if __name__ == "__main__":
    sys.exit(main())
