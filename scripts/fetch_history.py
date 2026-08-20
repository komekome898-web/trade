#!/usr/bin/env python3
"""Accumulate bitFlyer public executions into data/executions_<product>.csv and
build 1-minute candles into data/candles_<product>.csv.

Run repeatedly (cron/systemd timer) from a network-enabled machine; it pages
backwards from the newest stored id and forwards for new trades.
"""
from __future__ import annotations

import csv
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd  # noqa: E402

from bot.exchange.bitflyer_client import BitflyerClient  # noqa: E402
from bot.settings import load_settings  # noqa: E402


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    settings = load_settings(root)
    product = settings.product_code
    client = BitflyerClient()
    data_dir = root / "data"
    data_dir.mkdir(exist_ok=True)
    exec_file = data_dir / f"executions_{product}.csv"

    existing_ids: set[int] = set()
    if exec_file.exists():
        existing_ids = set(pd.read_csv(exec_file, usecols=["id"])["id"].astype(int))
        print(f"loaded {len(existing_ids)} stored executions")

    new_rows: list[dict] = []
    before: int | None = None
    for page in range(50):  # up to ~25k trades per run
        batch = client.executions(product, count=500, before=before)
        if not batch:
            break
        fresh = [t for t in batch if int(t["id"]) not in existing_ids]
        new_rows.extend(fresh)
        before = int(batch[-1]["id"])
        if len(fresh) < len(batch):   # reached already-stored region
            break
        time.sleep(0.6)

    if new_rows:
        write_header = not exec_file.exists()
        with open(exec_file, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["id", "exec_date", "price", "size", "side"])
            if write_header:
                w.writeheader()
            for t in new_rows:
                w.writerow({k: t.get(k) for k in ("id", "exec_date", "price", "size", "side")})
    print(f"appended {len(new_rows)} new executions")

    # Rebuild candles
    df = pd.read_csv(exec_file)
    df["ts"] = pd.to_datetime(df["exec_date"], format="mixed", utc=True)
    df = df.sort_values("ts")
    o = df.set_index("ts")["price"].resample("1min").ohlc()
    v = df.set_index("ts")["size"].resample("1min").sum().rename("volume")
    candles = o.join(v).dropna(subset=["open"])
    out = data_dir / f"candles_{product}.csv"
    candles.to_csv(out)
    print(f"wrote {len(candles)} candles -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
