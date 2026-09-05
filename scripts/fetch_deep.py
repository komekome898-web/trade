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


def build_candles(executions: "pd.DataFrame") -> "pd.DataFrame":
    """1-minute OHLCV from an executions frame (columns: exec_date, price, size).

    A minute with zero executions gets a forward-filled OHLC (each of
    open/high/low/close independently carries the *previous* real candle's
    value for that field -- not a single flat point) and volume=0, so it
    stays a gapless series for consumers that need one. `synthetic` marks
    exactly those rows (1) so they can be told apart from a real bar that
    legitimately traded; real rows are 0. Without this flag such a row is
    indistinguishable from a genuine moving-price bar with zero volume --
    see docs/DATA_QA_TRIAGE.md candles_fx_btc_jpy/zero_volume and
    schema/candles_fx_btc_jpy.json known_defects for how this was found.
    """
    df = executions.copy()
    df["ts"] = pd.to_datetime(df["exec_date"], format="mixed", utc=True)
    df = df.sort_values("ts")
    o = df.set_index("ts")["price"].resample("1min").ohlc()
    v = df.set_index("ts")["size"].resample("1min").sum().rename("volume")
    candles = o.join(v)
    # `open` is NaN here exactly on minutes with zero executions: ohlc() of
    # an empty bin has no price to report, unlike sum() which defaults an
    # empty bin's volume to 0.0 rather than NaN (resample().sum(min_count=0)
    # is the pandas default) -- so volume can NOT be used to detect the gap.
    # Capture the flag from `open` *before* ffill fills it in.
    synthetic = candles["open"].isna()
    candles[["open", "high", "low", "close"]] = candles[["open", "high", "low", "close"]].ffill()
    candles["volume"] = candles["volume"].fillna(0.0)
    candles["synthetic"] = synthetic.astype(int)
    candles = candles.dropna(subset=["open"])
    return candles


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

    candles = build_candles(pd.read_csv(out))
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
