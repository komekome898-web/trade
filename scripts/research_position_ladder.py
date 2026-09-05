"""Estimated entry-price ladder (建値分布の推定) from our own OI snapshots.

Why an estimate: the tweet-style "クソポジチェッカー" (per-entry-price position
map with unrealized P&L) is exact ONLY on Hyperliquid, whose API exposes every
wallet's positions. CEX perps (OKX/Binance/bitFlyer) publish aggregate open
interest only, so any per-price map there is an inference. This is the standard
one — the same family Coinglass-style liquidation maps use:

  every snapshot interval (15 min), dOI = OI_t - OI_{t-1}
    dOI > 0  -> new positions opened; allocate them to the price bucket of P_t
    dOI < 0  -> positions closed; retire them PRO-RATA across the existing ladder
               (no information on which entries closed, so no side/vintage bias)

The ladder is symmetric in side: every contract opened at P has a long AND a
short counterparty, so the map says WHERE open positions were struck relative
to the current price, not who is long. Read it as pain geometry:
  mass ABOVE current price = longs underwater / shorts in profit
  mass BELOW current price = shorts underwater / longs in profit

Inputs: data/oi_snapshots.csv (scripts/record_oi.py). Rows recorded before
2026-08-31 have no btc_usd cell; they are back-joined from OKX 15m candles
(public history endpoint) at run time, and persisted with --write-prices.
Output: ladder table + overhead/underfoot mass summary. Exploration/monitoring
only: no signal is adopted from this (KNOWLEDGE §4, G6 phase-C study pending).
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from bot.monitoring.gates import shared_or_local  # noqa: E402

LOCAL_CSV = ROOT / "data" / "oi_snapshots.csv"
BUCKET = 500.0                       # USD per rung
OKX = "https://www.okx.com/api/v5/market/history-candles"
FIELDS = ["ts_utc", "okx_usdt_oi", "okx_usd_oi", "okx_ls_ratio", "dvol", "deribit_oi",
          "btc_usd"]


def load(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as f:
        return [r for r in csv.DictReader(f) if r.get("okx_usdt_oi")]


def okx_15m_closes(t0: datetime, t1: datetime) -> dict[int, float]:
    """15-minute closes keyed by bucket-start epoch seconds (public, paginated)."""
    out: dict[int, float] = {}
    after = int(t1.timestamp() * 1000)
    floor = int(t0.timestamp() * 1000)
    for _ in range(200):
        try:
            r = requests.get(OKX, params={"instId": "BTC-USDT-SWAP", "bar": "15m",
                                          "after": after, "limit": 100}, timeout=20)
            r.raise_for_status()
            data = r.json().get("data") or []
        except requests.RequestException:
            break
        if not data:
            break
        for row in data:
            ts = int(row[0])
            out[ts // 1000] = float(row[4])
        after = min(int(row[0]) for row in data)
        if after <= floor:
            break
    return out


def backfill_prices(rows: list[dict]) -> int:
    missing = [r for r in rows if not r.get("btc_usd")]
    if not missing:
        return 0
    stamps = [datetime.fromisoformat(r["ts_utc"]) for r in missing]
    closes = okx_15m_closes(min(stamps), max(stamps))
    filled = 0
    for r, ts in zip(missing, stamps):
        key = int(ts.timestamp()) // 900 * 900
        px = closes.get(key) or closes.get(key - 900)
        if px:
            r["btc_usd"] = f"{px:.2f}"
            filled += 1
    return filled


def build_ladder(rows: list[dict], oi_key: str = "okx_usdt_oi") -> tuple[dict[float, float], float | None]:
    ladder: dict[float, float] = {}
    prev_oi: float | None = None
    last_px: float | None = None
    for r in rows:
        if not r.get("btc_usd") or not r.get(oi_key):
            continue
        oi = float(r[oi_key])
        px = float(r["btc_usd"])
        last_px = px
        if prev_oi is not None:
            d = oi - prev_oi
            if d > 0:
                b = round(px / BUCKET) * BUCKET
                ladder[b] = ladder.get(b, 0.0) + d
            elif d < 0:
                total = sum(ladder.values())
                if total > 0:
                    f = max(0.0, 1 - (-d) / total)
                    for b in list(ladder):
                        ladder[b] *= f
        prev_oi = oi
    return {b: v for b, v in ladder.items() if v > 0}, last_px


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=Path, default=None,
                    help="override the input CSV; default is the freshest "
                         "of paper_logs/oi_snapshots.csv or data/oi_snapshots.csv "
                         "(single source of truth, docs/DATA_QA_CHECKLIST.md #10)")
    ap.add_argument("--write-prices", action="store_true",
                    help="persist back-joined btc_usd cells into the CSV "
                         "(always writes the LOCAL copy, never paper_logs/, "
                         "so the shared/committed file is never mutated here)")
    args = ap.parse_args()
    read_path = args.csv or shared_or_local(ROOT, "data/oi_snapshots.csv")
    print(f"[data] oi_snapshots.csv read from: {read_path}")
    rows = load(read_path)
    if not rows:
        print("no OI rows")
        return 0
    filled = backfill_prices(rows)
    if args.write_prices and filled:
        write_path = args.csv or LOCAL_CSV
        with write_path.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            w.writeheader()
            for r in rows:
                w.writerow({k: r.get(k, "") for k in FIELDS})
    ladder, px = build_ladder(rows)
    priced = sum(1 for r in rows if r.get("btc_usd"))
    print(f"rows {len(rows)} (priced {priced}, back-filled {filled}), "
          f"span {rows[0]['ts_utc'][:16]} .. {rows[-1]['ts_utc'][:16]}, last px {px}")
    if not ladder or px is None:
        print("ladder empty")
        return 0
    total = sum(ladder.values())
    above = sum(v for b, v in ladder.items() if b > px)
    below = sum(v for b, v in ladder.items() if b < px)
    print(f"\nestimated open-position ladder (${BUCKET:.0f} rungs, pro-rata retirement)")
    print(f"  overhead mass (entries above px: longs underwater / shorts winning): {above/total:5.1%}")
    print(f"  underfoot mass (entries below px: shorts underwater / longs winning): {below/total:5.1%}")
    print("\n  rung      share   bar")
    for b in sorted(ladder, reverse=True):
        share = ladder[b] / total
        mark = "<" if abs(b - round(px / BUCKET) * BUCKET) < 1e-9 else " "
        print(f"  ${b:>8,.0f} {share:6.1%}  {'#' * int(share * 200)} {mark}")
    print("\nCAVEATS: aggregate-OI inference (no per-account data, unlike Hyperliquid);"
          " pro-rata retirement assumes closes are vintage-neutral; ladder only knows"
          " positions opened since recording began (2026-08-20).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
