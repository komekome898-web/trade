"""Daily attention/heat series for the dashboard gauge (no trading signal).

Appends to data/attention/attention.csv: date, wp_en, wp_ja, gdelt_vol, fng.
First run backfills the full history (each source serves it in one request);
later runs top up the recent window.  Wikipedia publishes at D-2, so the last
two days are expected to be blank for wp_* — the gauge reads the newest
complete row, it does not wait for today's.

Sources (docs/SURVEY_ATTENTION_DATA.md):
- Wikimedia Pageviews API, per-article daily, user traffic only (bots excluded)
- GDELT doc API timelinevol: share of world news coverage mentioning bitcoin
- alternative.me Fear & Greed (kept for reference; ~60-70%% of its weight is
  price-derived per its own published composition — labeled as such in the UI)

Direction-prediction from these series is a recorded no-go (stage-0 + power
analysis + literature, see the survey); this file exists only so the owner can
see today's crowd heat as a number instead of a feeling.
"""

from __future__ import annotations

import csv
import io
import json
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "attention" / "attention.csv"
FIELDS = ["date", "wp_en", "wp_ja", "gdelt_vol", "fng", "btc_usd",
          "btc_open", "btc_high", "btc_low"]
UA = {"User-Agent": "trade-research-gauge/1.0"}
WP_START = "20150701"
GDELT_START = "20170101000000"


def _get(url: str, timeout: int = 120, tries: int = 3) -> bytes:
    last: Exception | None = None
    for attempt in range(tries):
        try:
            resp = requests.get(url, headers=UA, timeout=timeout)
            resp.raise_for_status()
            return resp.content
        except requests.RequestException as exc:  # read-only public data: retry
            last = exc
            time.sleep(2 ** attempt)
    raise last  # type: ignore[misc]


def fetch_wikipedia(project: str, article: str, start: str, end: str) -> dict[str, float]:
    url = (f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
           f"{project}/all-access/user/{article}/daily/{start}/{end}")
    try:
        items = json.loads(_get(url)).get("items", [])
    except (requests.RequestException, json.JSONDecodeError):
        return {}
    return {it["timestamp"][:8]: float(it["views"]) for it in items}


def _fetch_gdelt_window(start: str, end: str) -> dict[str, float]:
    url = ("https://api.gdeltproject.org/api/v2/doc/doc?query=bitcoin"
           f"&mode=timelinevol&STARTDATETIME={start}&ENDDATETIME={end}&format=CSV")
    try:
        text = _get(url).decode("utf-8", "replace")
    except requests.RequestException:
        return {}
    out: dict[str, float] = {}
    for row in csv.reader(io.StringIO(text)):
        if len(row) >= 2 and row[0][:4].isdigit():
            day = row[0][:10].replace("-", "")
            try:
                out[day] = out.get(day, 0.0) + float(row[-1])
            except ValueError:
                pass
    return out


def fetch_gdelt(years: list[int], end: str) -> dict[str, float]:
    """Yearly chunks (the full 2017- span in one request is reset-prone).
    The caller passes exactly the years that need (re)fetching, so a chunk that
    failed on an earlier run is retried on the next one."""
    out: dict[str, float] = {}
    for year in years:
        s = max(GDELT_START, f"{year}0101000000")
        e = min(end, f"{year}1231235959")
        if s <= e:
            out.update(_fetch_gdelt_window(s, e))
    return out


def fetch_btc_daily(start_day: str) -> dict[str, dict[str, float]]:
    """Bitstamp daily OHLC (public, full history, 1000 rows/page).
    Returns day -> {close, open, high, low} for the candle chart and the
    short-horizon heat-vs-range diagnostics."""
    from datetime import datetime, timezone
    out: dict[str, dict[str, float]] = {}
    start = int(datetime.strptime(start_day, "%Y%m%d")
                .replace(tzinfo=timezone.utc).timestamp())
    for _ in range(20):  # 20k days cap
        url = ("https://www.bitstamp.net/api/v2/ohlc/btcusd/"
               f"?step=86400&limit=1000&start={start}")
        try:
            data = json.loads(_get(url)).get("data", {}).get("ohlc", [])
        except (requests.RequestException, json.JSONDecodeError):
            break
        if not data:
            break
        for row in data:
            try:
                ts = int(row["timestamp"])
                day = date.fromtimestamp(ts).strftime("%Y%m%d")
                out[day] = {"close": float(row["close"]), "open": float(row["open"]),
                            "high": float(row["high"]), "low": float(row["low"])}
            except (KeyError, ValueError, TypeError, OSError):
                pass
        last = max(int(r["timestamp"]) for r in data)
        if len(data) < 1000:
            break
        start = last + 86400
    return out


def fetch_fng() -> dict[str, float]:
    try:
        data = json.loads(_get("https://api.alternative.me/fng/?limit=0&format=json"))
    except (requests.RequestException, json.JSONDecodeError):
        return {}
    out = {}
    for it in data.get("data", []):
        try:
            day = date.fromtimestamp(int(it["timestamp"])).strftime("%Y%m%d")
            out[day] = float(it["value"])
        except (KeyError, ValueError, TypeError, OSError):
            pass
    return out


def load_existing() -> dict[str, dict[str, str]]:
    if not OUT.exists():
        return {}
    with OUT.open(newline="", encoding="utf-8") as f:
        return {r["date"]: r for r in csv.DictReader(f)}


def main() -> int:
    existing = load_existing()
    today = date.today()
    end = today.strftime("%Y%m%d")
    topup = (today - timedelta(days=14)).strftime("%Y%m%d")

    def start_for(column: str, full_start: str) -> str:
        """14-day top-up when the column has real history; otherwise the full
        backfill start.  A source that failed silently on an earlier run (or a
        newly added column) heals itself on the next run instead of leaving a
        permanent hole behind the top-up window."""
        if any(r.get(column) for r in existing.values() if r["date"] < topup):
            return topup
        return full_start

    wp_en = fetch_wikipedia("en.wikipedia", "Bitcoin",
                            start_for("wp_en", WP_START), end)
    wp_ja = fetch_wikipedia("ja.wikipedia",
                            "%E3%83%93%E3%83%83%E3%83%88%E3%82%B3%E3%82%A4%E3%83%B3",
                            start_for("wp_ja", WP_START), end)
    # GDELT: refetch every year whose coverage is thin (<300 rows) plus the
    # current year, so an interior hole from a failed chunk heals itself.
    per_year: dict[int, int] = {}
    for r in existing.values():
        if r.get("gdelt_vol"):
            y = int(r["date"][:4])
            per_year[y] = per_year.get(y, 0) + 1
    gdelt_years = [y for y in range(int(GDELT_START[:4]), today.year + 1)
                   if per_year.get(y, 0) < 300 or y == today.year]
    gdelt = fetch_gdelt(gdelt_years, end + "000000")
    fng = fetch_fng()
    btc_rows = fetch_btc_daily(start_for("btc_low", WP_START))
    btc = {d: r["close"] for d, r in btc_rows.items()}
    btc_o = {d: r["open"] for d, r in btc_rows.items()}
    btc_h = {d: r["high"] for d, r in btc_rows.items()}
    btc_l = {d: r["low"] for d, r in btc_rows.items()}

    days = set(existing) | set(wp_en) | set(wp_ja) | set(gdelt) | set(btc)
    updated = 0
    for day in days:
        row = existing.get(day) or {k: "" for k in FIELDS}
        row["date"] = day
        before = dict(row)
        for key, src in (("wp_en", wp_en), ("wp_ja", wp_ja),
                         ("gdelt_vol", gdelt), ("fng", fng), ("btc_usd", btc),
                         ("btc_open", btc_o), ("btc_high", btc_h), ("btc_low", btc_l)):
            if day in src and not row.get(key):
                row[key] = f"{src[day]:.4f}".rstrip("0").rstrip(".")
        existing[day] = row
        if row != before:
            updated += 1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for day in sorted(existing):
            w.writerow({k: existing[day].get(k, "") for k in FIELDS})
    print(f"attention: {len(existing)} rows ({updated} updated), latest {max(existing) if existing else '-'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
