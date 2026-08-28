"""Fetch OSE daily reports and extract Nikkei 225 futures session prints.

Source: JPX official daily report (free), published the next business day ~9:00 JST:
  https://www.jpx.co.jp/automation/markets/statistics-derivatives/daily/json/daily_report_YYYYMM.json
  -> Daily_Report_OSE_YYYYMMDD.zip -> sif_dyr_YYYYMMDD.pdf (stock index futures)

Extracted per trade date and contract month, for the three Nikkei 225 lines
(large / mini / micro): night-session OHLC, day-session OHLC, day volume,
settlement price.  Appended to data/jpx_daily/nk225_sessions.csv (idempotent:
a (date, product, month) row already present is never rewritten).

Used by the ON1 forward paper tracker (docs/PREREG_on1_forward.md).  Run daily
from deploy/fetch_all.bat; safe to run repeatedly, fetches only missing dates
within --days (default 7).
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
import zipfile
from datetime import date, timedelta
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "jpx_daily"
OUT_CSV = OUT_DIR / "nk225_sessions.csv"
BASE = "https://www.jpx.co.jp"
LIST_URL = BASE + "/automation/markets/statistics-derivatives/daily/json/daily_report_{yyyymm}.json"

FIELDS = [
    "date", "product", "month",
    "night_open", "night_high", "night_low", "night_close",
    "day_open", "day_high", "day_low", "day_close",
    "day_volume", "settlement",
]

# Page titles inside sif_dyr identifying the three Nikkei 225 futures tables.
PRODUCTS = {
    "日経225先物": "large",
    "日経225mini": "mini",
    "日経225マイクロ先物": "micro",
}

NUM = r"(?:\d{1,3}(?:,\d{3})*|-)"
# 202609 09.10 161090023 <night O H L C> <day O H L C> <netchg sign+num> ...
ROW_RE = re.compile(
    rf"^(?P<month>20\d{{4}}) \d{{2}}\.\d{{2}} \d+ "
    rf"(?P<no>{NUM}) (?P<nh>{NUM}) (?P<nl>{NUM}) (?P<nc>{NUM}) "
    rf"(?P<do>{NUM}) (?P<dh>{NUM}) (?P<dl>{NUM}) (?P<dc>{NUM}) "
    rf"(?P<rest>.*)$"
)


def _num(s: str) -> str:
    return "" if s == "-" else s.replace(",", "")


def parse_sif_pdf(pdf_bytes: bytes, trade_date: str) -> list[dict]:
    import pdfplumber  # heavy import kept local

    rows: list[dict] = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            lines = text.splitlines()
            product = None
            for line in lines[:8]:
                stripped = line.strip()
                if stripped in PRODUCTS:
                    product = PRODUCTS[stripped]
                    break
            if product is None:
                continue
            for line in lines:
                m = ROW_RE.match(line.strip())
                if not m:
                    continue
                # rest: netchange(± n or -) volume [strategy] value [strategy] settlement oi
                rest = m.group("rest").replace("… ", "").replace("…", "").split()
                # drop the net-change token(s): "- 270" (sign token + number) or "0"
                if rest and rest[0] in {"-", "+"}:
                    rest = rest[2:] if len(rest) > 1 else rest[1:]
                elif rest:
                    rest = rest[1:]
                day_volume = _num(rest[0]) if rest else ""
                settlement = ""
                # settlement is the second-to-last numeric token (last is open interest)
                nums = [t for t in rest if re.fullmatch(r"\d{1,3}(?:,\d{3})*(?:\.\d+)?", t)]
                if len(nums) >= 2:
                    settlement = nums[-2].replace(",", "")
                rows.append({
                    "date": trade_date,
                    "product": product,
                    "month": m.group("month"),
                    "night_open": _num(m.group("no")),
                    "night_high": _num(m.group("nh")),
                    "night_low": _num(m.group("nl")),
                    "night_close": _num(m.group("nc")),
                    "day_open": _num(m.group("do")),
                    "day_high": _num(m.group("dh")),
                    "day_low": _num(m.group("dl")),
                    "day_close": _num(m.group("dc")),
                    "day_volume": day_volume,
                    "settlement": settlement,
                })
    return rows


def existing_dates() -> set[str]:
    if not OUT_CSV.exists():
        return set()
    with OUT_CSV.open() as f:
        return {r["date"] for r in csv.DictReader(f)}


def append_rows(rows: list[dict]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    new_file = not OUT_CSV.exists()
    with OUT_CSV.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
            w.writeheader()
        for r in rows:
            w.writerow(r)


def fetch_zip_urls(days: int, session: requests.Session) -> dict[str, str]:
    """trade date (YYYYMMDD) -> OSE zip URL, newest first, within `days`."""
    urls: dict[str, str] = {}
    today = date.today()
    months = {today.strftime("%Y%m"), (today - timedelta(days=days)).strftime("%Y%m")}
    for yyyymm in sorted(months, reverse=True):
        try:
            resp = session.get(LIST_URL.format(yyyymm=yyyymm), timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except (requests.RequestException, json.JSONDecodeError):
            continue
        for row in data.get("TableDatas", []):
            td = row.get("TradeDate", "")
            ose = row.get("OseAll", "")
            if td and ose and ose != "-":
                urls[td] = BASE + ose
    cutoff = (today - timedelta(days=days)).strftime("%Y%m%d")
    return {d: u for d, u in urls.items() if d >= cutoff}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7, help="fetch back this many calendar days")
    args = ap.parse_args()

    have = existing_dates()
    session = requests.Session()
    session.headers["User-Agent"] = "trade-bot-research/1.0"
    targets = {d: u for d, u in fetch_zip_urls(args.days, session).items() if d not in have}
    if not targets:
        print("jpx_daily: up to date")
        return 0

    added = 0
    for td in sorted(targets):
        try:
            resp = session.get(targets[td], timeout=120)
            resp.raise_for_status()
            zf = zipfile.ZipFile(io.BytesIO(resp.content))
            name = next((n for n in zf.namelist() if n.startswith("sif_dyr_") and "flex" not in n), None)
            if name is None:
                print(f"jpx_daily: {td} no sif_dyr in zip, skipped")
                continue
            rows = parse_sif_pdf(zf.read(name), td)
            nk = [r for r in rows if r["product"] in {"large", "mini", "micro"}]
            if not nk:
                print(f"jpx_daily: {td} parsed 0 Nikkei rows, skipped (format change?)")
                continue
            append_rows(nk)
            added += 1
            print(f"jpx_daily: {td} +{len(nk)} rows")
        except requests.RequestException as e:
            print(f"jpx_daily: {td} fetch failed: {e}")
    print(f"jpx_daily: done, {added} new dates")
    return 0


if __name__ == "__main__":
    sys.exit(main())
