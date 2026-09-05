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


def _order_new_rows(new_rows: list[dict]) -> list[dict]:
    """Ascending-by-id order for a batch of freshly-fetched executions
    before it is appended to executions_<product>.csv.

    Why this exists: main()'s pagination fetches backward from the newest
    trade (before=None, then before=<oldest id seen>), so the raw list it
    accumulates is newest-first/descending -- appending it as-is to an
    otherwise-ascending file writes a strictly-decreasing run of ids/
    timestamps on every single run. See docs/DATA_QA_TRIAGE.md
    bitflyer_execution_flow/non_monotonic (538,325 flagged rows) and its
    downstream gaps miscount on data/executions_FX_BTC_JPY.csv and
    data/executions_XRP_JPY.csv."""
    return sorted(new_rows, key=lambda t: int(t["id"]))


def build_candles(executions: "pd.DataFrame") -> "pd.DataFrame":
    """1-minute OHLCV from an executions frame (columns: exec_date, price, size).

    A minute with zero executions is dropped entirely (dropna on open) --
    never written as a zero-volume row. `synthetic` is always 0 here since
    this builder never fabricates a bar; it exists so the column set matches
    fetch_deep.py's output (which does forward-fill gaps and needs the flag
    to mark them). See docs/DATA_QA_TRIAGE.md candles_fx_btc_jpy/zero_volume.
    """
    df = executions.copy()
    df["ts"] = pd.to_datetime(df["exec_date"], format="mixed", utc=True)
    df = df.sort_values("ts")
    o = df.set_index("ts")["price"].resample("1min").ohlc()
    v = df.set_index("ts")["size"].resample("1min").sum().rename("volume")
    candles = o.join(v).dropna(subset=["open"])
    candles["synthetic"] = 0
    return candles


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
        # DATA QA 2026-09-05 (docs/DATA_QA_TRIAGE.md bitflyer_execution_flow/
        # non_monotonic+gaps): the loop above pages BACKWARD from the newest
        # trade (before=None, then before=oldest id seen so far), so
        # new_rows arrives newest-first/descending. Appending it in that
        # order writes a strictly-decreasing run of ids/timestamps into an
        # otherwise-ascending file every single run -- exactly the huge
        # non_monotonic count found in data/executions_FX_BTC_JPY.csv and
        # data/executions_XRP_JPY.csv (and, downstream, gaps computed off
        # that same broken ordering). Sorting ascending by id before writing
        # fixes every future append; existing rows are NOT reordered/
        # rewritten (never modify data files).
        new_rows = _order_new_rows(new_rows)
        write_header = not exec_file.exists()
        with open(exec_file, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["id", "exec_date", "price", "size", "side"])
            if write_header:
                w.writeheader()
            for t in new_rows:
                w.writerow({k: t.get(k) for k in ("id", "exec_date", "price", "size", "side")})
    print(f"appended {len(new_rows)} new executions")

    # Rebuild candles
    candles = build_candles(pd.read_csv(exec_file))
    out = data_dir / f"candles_{product}.csv"
    candles.to_csv(out)
    print(f"wrote {len(candles)} candles -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
