#!/usr/bin/env python3
"""Deep historical fetch of bitFlyer public executions (read-only).

Pages backwards through /v1/executions until TARGET_DAYS of history or
MAX_PAGES is reached, then writes executions and 1-minute candles CSVs.

Usage:
    python scripts/fetch_deep.py [PRODUCT ...] [--days N] [--max-pages N]
Defaults: XRP_JPY, 21 days, 1700 pages (500 trades/page).
"""
from __future__ import annotations

import argparse
import csv
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd  # noqa: E402

from bot.exchange.bitflyer_client import BitflyerClient  # noqa: E402


def fetch_product(client: BitflyerClient, product: str, days: int, max_pages: int,
                  data_dir: Path, sleep_sec: float = 1.05) -> None:
    from bot.exchange.bitflyer_client import BitflyerError

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    rows: list[dict] = []
    before: int | None = None
    for page in range(max_pages):
        try:
            batch = client.executions(product, count=500, before=before)
        except BitflyerError as e:
            # the public executions API only serves the most recent ~31 days;
            # keep what we have instead of dying mid-product
            print(f"[{product}] history limit reached at page {page}: {e}", flush=True)
            break
        if not batch:
            break
        rows.extend(batch)
        before = int(batch[-1]["id"])
        oldest = datetime.fromisoformat(batch[-1]["exec_date"]).replace(tzinfo=timezone.utc)
        if page % 100 == 0:
            print(f"[{product}] page {page}: oldest={oldest.isoformat()} rows={len(rows)}",
                  flush=True)
        if oldest < cutoff:
            break
        time.sleep(sleep_sec)

    out = data_dir / f"executions_{product}.csv"
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "exec_date", "price", "size", "side"])
        w.writeheader()
        for t in sorted(rows, key=lambda r: int(r["id"])):
            w.writerow({k: t.get(k) for k in ("id", "exec_date", "price", "size", "side")})
    print(f"[{product}] wrote {len(rows)} executions -> {out}", flush=True)

    df = pd.read_csv(out)
    df["ts"] = pd.to_datetime(df["exec_date"], format="mixed", utc=True)
    df = df.sort_values("ts")
    o = df.set_index("ts")["price"].resample("1min").ohlc()
    v = df.set_index("ts")["size"].resample("1min").sum().rename("volume")
    candles = o.join(v)
    candles[["open", "high", "low", "close"]] = candles[["open", "high", "low", "close"]].ffill()
    candles["volume"] = candles["volume"].fillna(0.0)
    candles = candles.dropna(subset=["open"])
    cout = data_dir / f"candles_{product}.csv"
    candles.to_csv(cout)
    print(f"[{product}] wrote {len(candles)} 1-min candles "
          f"({candles.index[0]} .. {candles.index[-1]}) -> {cout}", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("products", nargs="*", default=["XRP_JPY"])
    ap.add_argument("--days", type=int, default=21)
    ap.add_argument("--max-pages", type=int, default=1700)
    args = ap.parse_args()
    products = args.products or ["XRP_JPY"]

    data_dir = Path(__file__).resolve().parents[1] / "data"
    data_dir.mkdir(exist_ok=True)
    client = BitflyerClient()
    for product in products:
        fetch_product(client, product, args.days, args.max_pages, data_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
