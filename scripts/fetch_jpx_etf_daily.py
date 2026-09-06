#!/usr/bin/env python3
"""Fetch daily OHLCV for JPX-listed symbols from the Yahoo Finance chart API
and write a permanent, MD5-stamped snapshot directory.

This generalizes the ad-hoc method used to build the first snapshot of this
dataset, `backtest_data/jpx_etf_daily_20260905/` (see that directory's
README.md -- it was fetched live via plain Python `requests` and never
checked in as a reusable script, which is what this file now is). Re-run
this for a fresh dated/labeled directory rather than editing an existing
snapshot -- raw JSON files under backtest_data/jpx_etf_daily_*/ are never
modified once written (see schema/jpx_etf_daily.json retention note).

Source (one GET per symbol, no auth):
    https://query1.finance.yahoo.com/v8/finance/chart/<SYM>?range=15y&interval=1d&events=div,splits

Output directory layout (matches jpx_etf_daily_20260905/):
    <SYM>.json        -- raw response body, byte-for-byte, never modified
    <SYM>.csv         -- derived: date,open,high,low,close,adjclose,volume
    _fetch_results.json -- per-symbol fetch metadata (url, fetched_at_utc,
                           http_status, error, row_count, first_date, last_date)
    manifest.json     -- _fetch_results.json entries + raw_json_md5/csv_md5
    MD5SUMS           -- md5sum of every *.json/*.csv/README.md in the dir
                         (run after README.md is written by hand)

`date` in the CSV is the UTC calendar date of the bar's raw Unix timestamp
(datetime.fromtimestamp(ts, tz=UTC).date()) -- see jpx_etf_daily_20260905's
README "Time basis" section for the JST-equivalence caveat.

Usage:
    python scripts/fetch_jpx_etf_daily.py --symbols 1348.T,1305.T \\
        --out-dir backtest_data/jpx_etf_daily_20260906_topix_alt

Does not write MD5SUMS or README.md by itself for the prose parts (row-count
table, notes) -- those still need a human/agent to write README.md, after
which MD5SUMS should be regenerated (`md5sum *.json *.csv README.md > MD5SUMS`
from inside the output directory) so it also covers README.md.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

REPO = Path(__file__).resolve().parents[1]
URL_TMPL = "https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=15y&interval=1d&events=div,splits"


def utc_date(ts: int) -> str:
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d")


def now_iso() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def md5_of(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch_one(symbol: str, session: requests.Session) -> dict:
    url = URL_TMPL.format(sym=symbol)
    fetched_at = now_iso()
    result = {
        "symbol": symbol,
        "url": url,
        "fetched_at_utc": fetched_at,
        "http_status": None,
        "error": None,
        "row_count": 0,
        "first_date": None,
        "last_date": None,
    }
    try:
        resp = session.get(url, timeout=30)
        result["http_status"] = resp.status_code
        resp.raise_for_status()
        raw_bytes = resp.content
    except requests.RequestException as exc:
        result["error"] = str(exc)
        return result, None

    try:
        payload = json.loads(raw_bytes)
        res = payload["chart"]["result"][0]
        stamps = res.get("timestamp", []) or []
        if stamps:
            result["row_count"] = len(stamps)
            result["first_date"] = utc_date(stamps[0])
            result["last_date"] = utc_date(stamps[-1])
    except (KeyError, IndexError, ValueError, json.JSONDecodeError) as exc:
        result["error"] = f"parse error: {exc}"

    return result, raw_bytes


def raw_to_csv_rows(raw_bytes: bytes) -> list[str]:
    payload = json.loads(raw_bytes)
    res = payload["chart"]["result"][0]
    stamps = res.get("timestamp", []) or []
    quote = (res.get("indicators", {}).get("quote") or [{}])[0]
    adj = (res.get("indicators", {}).get("adjclose") or [{}])
    adjclose = adj[0].get("adjclose") if adj and adj[0] else None

    def cell(arr, i):
        if arr is None:
            return ""
        v = arr[i] if i < len(arr) else None
        return "" if v is None else v

    rows = ["date,open,high,low,close,adjclose,volume"]
    for i, ts in enumerate(stamps):
        d = utc_date(ts)
        o = cell(quote.get("open"), i)
        h = cell(quote.get("high"), i)
        l = cell(quote.get("low"), i)
        c = cell(quote.get("close"), i)
        ac = cell(adjclose, i)
        v = cell(quote.get("volume"), i)
        rows.append(f"{d},{o},{h},{l},{c},{ac},{v}")
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", required=True, help="comma-separated, e.g. 1348.T,1305.T")
    ap.add_argument("--out-dir", required=True, help="repo-relative or absolute output directory")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = REPO / out_dir
    out_dir.mkdir(parents=True, exist_ok=False if not out_dir.exists() else True)

    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    session = requests.Session()
    session.headers["User-Agent"] = "trade-bot-research/1.0"

    fetch_results: dict[str, dict] = {}
    manifest_symbols: list[dict] = []

    for sym in symbols:
        print(f"fetch_jpx_etf_daily: fetching {sym} ...", flush=True)
        result, raw_bytes = fetch_one(sym, session)
        fetch_results[sym] = result

        if raw_bytes is None:
            print(f"fetch_jpx_etf_daily: {sym} FAILED: {result['error']}", flush=True)
            manifest_symbols.append({**result, "raw_json_file": None, "raw_json_md5": None,
                                      "csv_file": None, "csv_md5": None})
            continue

        json_path = out_dir / f"{sym}.json"
        json_path.write_bytes(raw_bytes)

        csv_path = out_dir / f"{sym}.csv"
        try:
            csv_rows = raw_to_csv_rows(raw_bytes)
            csv_path.write_text("\n".join(csv_rows) + "\n", encoding="utf-8")
            csv_md5 = md5_of(csv_path)
        except Exception as exc:  # noqa: BLE001
            print(f"fetch_jpx_etf_daily: {sym} CSV derivation failed: {exc}", flush=True)
            csv_md5 = None

        manifest_symbols.append({
            **result,
            "raw_json_file": json_path.name,
            "raw_json_md5": md5_of(json_path),
            "csv_file": csv_path.name if csv_md5 else None,
            "csv_md5": csv_md5,
        })
        print(f"fetch_jpx_etf_daily: {sym} OK rows={result['row_count']} "
              f"{result['first_date']}..{result['last_date']}", flush=True)

    (out_dir / "_fetch_results.json").write_text(
        json.dumps(fetch_results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    manifest = {
        "dataset": out_dir.name,
        "purpose": "Snapshot of JPX-listed Yahoo Finance daily series (see README.md in this directory for why).",
        "source_url_template": URL_TMPL,
        "fetch_method": "Python requests via preconfigured HTTPS proxy",
        "symbols": manifest_symbols,
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"fetch_jpx_etf_daily: wrote _fetch_results.json and manifest.json to {out_dir}")
    print("fetch_jpx_etf_daily: NOTE -- write README.md by hand, then regenerate MD5SUMS "
          "(md5sum *.json *.csv README.md > MD5SUMS) to also cover it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
