#!/usr/bin/env python3
"""Daily funding-rate and FX/spot basis logger for bitFlyer FX_BTC_JPY
(EXEC_FLOOR_PREREG.md sec7, row 2: "funding rate and basis daily log" -> E-g).

PUBLIC endpoints only -- no API key/secret required, no order endpoints
touched. Two independent, idempotent appends per run:

1. Funding rate -> data/funding_rate_history.csv (columns: calculation_date,
   settlement_date, rate -- the schema already in that file, see
   schema/bitflyer_funding_rate.json; unique key = settlement_date).
       - GET /v1/getfundingrate (current/next-period rate): recorded with
         calculation_date = now (this call), settlement_date = whatever the
         payload names its upcoming-settlement time under.
       - GET /v1/getfundingratehistory (already-settled periods, most
         recent --history-count of them; default 6 covers ~48h so a run
         that was missed for a day still catches up).
       - Field names: bitFlyer's exact JSON keys for these two endpoints are
         not pinned down anywhere else in this repo (schema/bitflyer_funding_rate.json
         says the existing CSV's provenance is unconfirmed) -- this script
         tries the CSV's own column names first (calculation_date /
         settlement_date / rate), then a short list of plausible alternates
         (current_funding_rate / next_period_start_at / funding_rate /
         corresponding_time), and otherwise SKIPS the item with a one-line
         warning naming its raw keys (never its values -- public data, but
         no reason to spam) rather than guessing wrong or crashing.
       - Dedup: an item whose settlement_date already exists in the CSV is
         never re-appended (read once at the top of the run).

2. Basis (FX_BTC_JPY vs BTC_JPY) -> data/basis_log.csv (new file). Two
   independent measures per row:
       - mid-to-mid from the public tickers (/v1/getticker), taken at call
         time: fx_mid, spot_mid, basis_bp = (fx_mid/spot_mid - 1) * 1e4.
       - the latest 1-minute CLOSE basis from data/candles_FX_BTC_JPY.csv /
         data/candles_BTC_JPY.csv, IF those files are present (best-effort;
         candle_ts_fx/candle_ts_spot/fx_close_1m/spot_close_1m/
         basis_close_bp are left blank otherwise). These two candle files
         are not necessarily updated on the same cadence as this script, so
         their timestamps are recorded alongside the values rather than
         assumed to be "now".
   Appended unconditionally each run (a time series, not a dedup table) --
   safe to run every 15 minutes from fetch_all.bat; funding settles every
   8h and moves slowly, so near-duplicate basis rows across close-together
   runs cost a little disk, nothing more.

Usage:
    python scripts/record_funding_basis.py            # one run, append, exit
    python scripts/record_funding_basis.py --loop 3600 # resident: repeat hourly
"""
from __future__ import annotations

import argparse
import csv
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bot.exchange.bitflyer_client import BitflyerClient, BitflyerError, NetworkError  # noqa: E402

DEFAULT_FUNDING_CSV = ROOT / "data" / "funding_rate_history.csv"
DEFAULT_BASIS_CSV = ROOT / "data" / "basis_log.csv"
CANDLE_FX = ROOT / "data" / "candles_FX_BTC_JPY.csv"
CANDLE_SPOT = ROOT / "data" / "candles_BTC_JPY.csv"

FX_PRODUCT = "FX_BTC_JPY"
SPOT_PRODUCT = "BTC_JPY"

FUNDING_FIELDS = ["calculation_date", "settlement_date", "rate"]
BASIS_FIELDS = ["ts_utc", "fx_mid", "spot_mid", "basis_bp",
                "candle_ts_fx", "candle_ts_spot", "fx_close_1m", "spot_close_1m",
                "basis_close_bp"]

# Ordered candidate JSON keys, most-likely-first (see module docstring).
RATE_KEYS = ("rate", "funding_rate", "current_funding_rate")
SETTLE_KEYS = ("settlement_date", "next_period_start_at", "corresponding_time",
              "settlement_time", "date")
CALC_KEYS = ("calculation_date", "calculation_time", "calc_date", "date")

DEFAULT_HISTORY_COUNT = 6  # ~48h of 8h settlements -- catch-up margin


def _first(d: dict, keys: tuple[str, ...]):
    for k in keys:
        v = d.get(k)
        if v is not None:
            return v
    return None


def history_row(item: dict) -> dict | None:
    """Map one /v1/getfundingratehistory item to our CSV row shape, or None
    if it doesn't carry a recognizable rate/settlement pair."""
    if not isinstance(item, dict):
        return None
    rate = _first(item, RATE_KEYS)
    settlement = _first(item, SETTLE_KEYS)
    if rate is None or settlement is None:
        return None
    calc = _first(item, CALC_KEYS) or ""
    return {"calculation_date": calc, "settlement_date": settlement, "rate": rate}


def current_row(payload: dict, now_iso: str) -> dict | None:
    """Map the single /v1/getfundingrate payload to our CSV row shape, or
    None if it doesn't carry a recognizable rate/settlement pair."""
    if not isinstance(payload, dict):
        return None
    rate = _first(payload, RATE_KEYS)
    settlement = _first(payload, SETTLE_KEYS)
    if rate is None or settlement is None:
        return None
    return {"calculation_date": now_iso, "settlement_date": settlement, "rate": rate}


def _existing_settlements(path: Path) -> set[str]:
    if not path.exists():
        return set()
    seen: set[str] = set()
    try:
        with path.open("r", encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                s = row.get("settlement_date")
                if s:
                    seen.add(s)
    except (OSError, csv.Error):
        pass
    return seen


def _append_funding_rows(path: Path, rows: list[dict]) -> int:
    if not rows:
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not path.exists() or path.stat().st_size == 0
    with path.open("a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FUNDING_FIELDS)
        if write_header:
            w.writeheader()
        for r in rows:
            w.writerow(r)
    return len(rows)


def collect_funding(client: BitflyerClient, existing: set[str],
                    history_count: int = DEFAULT_HISTORY_COUNT
                    ) -> tuple[list[dict], list[str]]:
    """Returns (new_rows_to_append, warnings). `existing` is the set of
    settlement_date values already on disk; it is NOT mutated -- rows within
    this same call that share a settlement_date are also deduped against
    each other so a getfundingrate/getfundingratehistory overlap on the
    same still-open period does not write it twice in one run."""
    warnings: list[str] = []
    rows: list[dict] = []
    seen = set(existing)

    try:
        current = client.funding_rate(FX_PRODUCT)
        mapped = current_row(current, datetime.now(timezone.utc).isoformat())
        if mapped is None:
            warnings.append(
                f"getfundingrate: unrecognized shape, keys={sorted(current.keys()) if isinstance(current, dict) else type(current).__name__}")
        elif mapped["settlement_date"] not in seen:
            rows.append(mapped)
            seen.add(mapped["settlement_date"])
    except (BitflyerError, NetworkError) as e:
        warnings.append(f"getfundingrate failed: {e}")

    try:
        history = client.funding_rate_history(FX_PRODUCT, count=history_count)
        for item in history or []:
            mapped = history_row(item)
            if mapped is None:
                keys = sorted(item.keys()) if isinstance(item, dict) else type(item).__name__
                warnings.append(f"getfundingratehistory: unrecognized item shape, keys={keys}")
                continue
            if mapped["settlement_date"] in seen:
                continue
            rows.append(mapped)
            seen.add(mapped["settlement_date"])
    except (BitflyerError, NetworkError) as e:
        warnings.append(f"getfundingratehistory failed: {e}")

    return rows, warnings


def _mid(ticker: dict) -> float | None:
    try:
        return (float(ticker["best_bid"]) + float(ticker["best_ask"])) / 2.0
    except (KeyError, TypeError, ValueError):
        return None


def _last_candle_close(path: Path) -> tuple[str, float] | None:
    """(ts, close) of the last row of a candles_*.csv file, or None if the
    file is absent/empty/unparseable. Reads only the tail -- these files
    can be several MB, so this avoids loading the whole thing."""
    if not path.exists():
        return None
    try:
        with path.open("rb") as f:
            f.seek(0, 2)
            size = f.tell()
            chunk = min(size, 8192)
            f.seek(size - chunk)
            tail = f.read().decode("utf-8", errors="replace")
        lines = [ln for ln in tail.splitlines() if ln.strip()]
        if not lines:
            return None
        last = lines[-1]
        # A partial first line in the tail chunk (cut mid-row) is dropped by
        # requiring the header's column count; simplest robust check: needs
        # >= 5 comma-separated fields and a parseable float in position 4.
        parts = last.split(",")
        if len(parts) < 5:
            return None
        return parts[0], float(parts[4])
    except (OSError, ValueError, IndexError):
        return None


def collect_basis(client: BitflyerClient) -> tuple[dict, list[str]]:
    warnings: list[str] = []
    row = {f: "" for f in BASIS_FIELDS}
    row["ts_utc"] = datetime.now(timezone.utc).isoformat()

    try:
        fx_mid = _mid(client.ticker(FX_PRODUCT))
        spot_mid = _mid(client.ticker(SPOT_PRODUCT))
        if fx_mid is not None and spot_mid is not None and spot_mid != 0:
            row["fx_mid"] = fx_mid
            row["spot_mid"] = spot_mid
            row["basis_bp"] = (fx_mid / spot_mid - 1.0) * 1e4
        else:
            warnings.append("ticker: could not compute mid for fx and/or spot")
    except (BitflyerError, NetworkError) as e:
        warnings.append(f"ticker failed: {e}")

    fx_candle = _last_candle_close(CANDLE_FX)
    spot_candle = _last_candle_close(CANDLE_SPOT)
    if fx_candle is not None:
        row["candle_ts_fx"], row["fx_close_1m"] = fx_candle
    if spot_candle is not None:
        row["candle_ts_spot"], row["spot_close_1m"] = spot_candle
    if fx_candle is not None and spot_candle is not None and spot_candle[1]:
        row["basis_close_bp"] = (fx_candle[1] / spot_candle[1] - 1.0) * 1e4

    return row, warnings


def _append_basis_row(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not path.exists() or path.stat().st_size == 0
    with path.open("a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=BASIS_FIELDS)
        if write_header:
            w.writeheader()
        w.writerow(row)


def run_once(client: BitflyerClient, funding_csv: Path, basis_csv: Path,
            history_count: int = DEFAULT_HISTORY_COUNT) -> str:
    existing = _existing_settlements(funding_csv)
    funding_rows, fw = collect_funding(client, existing, history_count)
    n_funding = _append_funding_rows(funding_csv, funding_rows)

    basis_row, bw = collect_basis(client)
    _append_basis_row(basis_csv, basis_row)

    msg = f"record_funding_basis: +{n_funding} funding row(s), 1 basis row"
    for w in fw + bw:
        msg += f"\n  warning: {w}"
    return msg


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--funding-csv", default=str(DEFAULT_FUNDING_CSV))
    ap.add_argument("--basis-csv", default=str(DEFAULT_BASIS_CSV))
    ap.add_argument("--history-count", type=int, default=DEFAULT_HISTORY_COUNT)
    ap.add_argument("--loop", type=float, default=None, metavar="SECONDS",
                    help="resident mode: repeat every SECONDS until Ctrl+C "
                         "(default: run once and exit)")
    args = ap.parse_args(argv)

    # Public endpoints only -- no credentials needed or used.
    client = BitflyerClient()
    funding_csv, basis_csv = Path(args.funding_csv), Path(args.basis_csv)

    if args.loop is None:
        print(run_once(client, funding_csv, basis_csv, args.history_count))
        return 0

    print(f"record_funding_basis: looping every {args.loop:.0f}s (Ctrl+C to stop)",
          flush=True)
    try:
        while True:
            t0 = time.monotonic()
            try:
                print(run_once(client, funding_csv, basis_csv, args.history_count),
                      flush=True)
            except Exception as e:  # noqa: BLE001 - resident: never die on one bad cycle
                print(f"record_funding_basis: cycle FAILED: {type(e).__name__}: {e}",
                      file=sys.stderr, flush=True)
            time.sleep(max(1.0, args.loop - (time.monotonic() - t0)))
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
