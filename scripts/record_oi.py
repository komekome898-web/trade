#!/usr/bin/env python3
"""Append ONE derivatives snapshot row to data/oi_snapshots.csv.

Why this exists: the OKX rubik endpoints return a fixed ~30-day window and
cannot be paged back, and Deribit's DVOL history is hourly-only. Phase B of
the storm study (scripts/research_storm_b.py) could therefore not evaluate
the OI / long-short hypotheses (G4/G5/G6) on the fresh segment at all — they
were ruled INSUFFICIENT rather than tested. The only way to get a long,
dense, aligned history of those series is to record it forward ourselves,
one row per collector run, starting now.

Columns (data/oi_snapshots.csv, header written on create):
    ts_utc         ISO-8601 UTC timestamp of this run
    okx_usdt_oi    OKX BTC-USDT-SWAP open interest   (public/open-interest)
    okx_usd_oi     OKX BTC-USD-SWAP open interest    (public/open-interest)
    okx_ls_ratio   OKX BTC long/short ACCOUNT ratio, newest 5m value
                   (rubik/stat/contracts/long-short-account-ratio)
    dvol           Deribit BTC DVOL, newest 1m close
                   (public/get_volatility_index_data, resolution=60)
    deribit_oi     Deribit BTC-PERPETUAL open interest (public/ticker)

Every field is fetched independently and best-effort: a venue that errors,
times out or answers in an unexpected shape leaves its cell EMPTY and never
aborts the row, so one flaky endpoint cannot punch a hole in the series.
Read-only public endpoints, no auth, 10s timeout per call.

Usage:
    python scripts/record_oi.py            # append one row, print it
"""
from __future__ import annotations

import csv
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
OUT = DATA_DIR / "oi_snapshots.csv"

OKX = "https://www.okx.com"
DERIBIT = "https://www.deribit.com/api/v2/public"
TIMEOUT = 10.0

FIELDS = ["ts_utc", "okx_usdt_oi", "okx_usd_oi", "okx_ls_ratio", "dvol", "deribit_oi"]

session = requests.Session()


def _warn(what: str, exc: object) -> None:
    print(f"[record_oi] {what} FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)


def okx_open_interest(inst_id: str) -> float | None:
    """Newest open interest for one OKX swap, or None on any failure."""
    try:
        r = session.get(f"{OKX}/api/v5/public/open-interest",
                        params={"instType": "SWAP", "instId": inst_id},
                        timeout=TIMEOUT)
        r.raise_for_status()
        body = r.json()
        if body.get("code") != "0":
            raise RuntimeError(f"code={body.get('code')} msg={body.get('msg')!r}")
        return float(body["data"][0]["oi"])
    except Exception as exc:  # noqa: BLE001 - best effort by design
        _warn(f"okx open-interest {inst_id}", exc)
        return None


def okx_ls_ratio(ccy: str = "BTC", period: str = "5m") -> float | None:
    """Latest long/short account ratio. The endpoint returns newest-first
    rows of [ts, ratio]; we take the row with the largest timestamp so the
    ordering is not assumed."""
    try:
        r = session.get(f"{OKX}/api/v5/rubik/stat/contracts/long-short-account-ratio",
                        params={"ccy": ccy, "period": period}, timeout=TIMEOUT)
        r.raise_for_status()
        body = r.json()
        if body.get("code") != "0":
            raise RuntimeError(f"code={body.get('code')} msg={body.get('msg')!r}")
        rows = [row for row in body.get("data") or [] if len(row) >= 2]
        if not rows:
            raise RuntimeError("empty data")
        newest = max(rows, key=lambda row: int(row[0]))
        return float(newest[1])
    except Exception as exc:  # noqa: BLE001
        _warn("okx long-short-account-ratio", exc)
        return None


def deribit_dvol(currency: str = "BTC") -> float | None:
    """Latest DVOL close: last point of a short resolution=60 (1m) window."""
    try:
        now_ms = int(time.time() * 1000)
        r = session.get(f"{DERIBIT}/get_volatility_index_data",
                        params={"currency": currency, "resolution": 60,
                                "start_timestamp": now_ms - 6 * 3600 * 1000,
                                "end_timestamp": now_ms},
                        timeout=TIMEOUT)
        r.raise_for_status()
        rows = (r.json().get("result") or {}).get("data") or []
        if not rows:
            raise RuntimeError("empty data")
        newest = max(rows, key=lambda row: row[0])   # [ts, open, high, low, close]
        return float(newest[4])
    except Exception as exc:  # noqa: BLE001
        _warn("deribit get_volatility_index_data", exc)
        return None


def deribit_perp_oi(instrument: str = "BTC-PERPETUAL") -> float | None:
    """Open interest from the BTC-PERPETUAL ticker."""
    try:
        r = session.get(f"{DERIBIT}/ticker",
                        params={"instrument_name": instrument}, timeout=TIMEOUT)
        r.raise_for_status()
        result = r.json().get("result") or {}
        if "open_interest" not in result:
            raise RuntimeError("no open_interest in ticker")
        return float(result["open_interest"])
    except Exception as exc:  # noqa: BLE001
        _warn(f"deribit ticker {instrument}", exc)
        return None


def snapshot() -> dict[str, object]:
    """One row. Each cell is independent; failures become empty strings."""
    row = {"ts_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    row["okx_usdt_oi"] = okx_open_interest("BTC-USDT-SWAP")
    row["okx_usd_oi"] = okx_open_interest("BTC-USD-SWAP")
    row["okx_ls_ratio"] = okx_ls_ratio()
    row["dvol"] = deribit_dvol()
    row["deribit_oi"] = deribit_perp_oi()
    return {k: ("" if v is None else v) for k, v in row.items()}


def append_row(row: dict[str, object], out: Path = OUT) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    new_file = not out.exists() or out.stat().st_size == 0
    with open(out, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
            w.writeheader()
        w.writerow(row)


def main() -> int:
    row = snapshot()
    append_row(row)
    filled = sum(1 for k in FIELDS[1:] if row[k] != "")
    print(f"[record_oi] {OUT} += 1 row ({filled}/{len(FIELDS) - 1} fields): "
          + "  ".join(f"{k}={row[k]}" for k in FIELDS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
