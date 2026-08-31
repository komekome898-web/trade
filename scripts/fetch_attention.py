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
from datetime import date, timedelta
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "attention" / "attention.csv"
FIELDS = ["date", "wp_en", "wp_ja", "gdelt_vol", "fng"]
UA = {"User-Agent": "trade-research-gauge/1.0"}
WP_START = "20150701"
GDELT_START = "20170101000000"


def _get(url: str, timeout: int = 120) -> bytes:
    resp = requests.get(url, headers=UA, timeout=timeout)
    resp.raise_for_status()
    return resp.content


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
    for attempt in (1, 2):  # long windows get reset occasionally; one retry
        try:
            text = _get(url).decode("utf-8", "replace")
            break
        except requests.RequestException:
            if attempt == 2:
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


def fetch_gdelt(start: str, end: str) -> dict[str, float]:
    """Yearly chunks: the full 2017- span in one request is reset-prone."""
    out: dict[str, float] = {}
    y0, y1 = int(start[:4]), int(end[:4])
    for year in range(y0, y1 + 1):
        s = max(start, f"{year}0101000000")
        e = min(end, f"{year}1231235959")
        out.update(_fetch_gdelt_window(s, e))
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
    # Full backfill when empty; otherwise a 14-day top-up window (covers the
    # D-2 Wikipedia lag plus a week of missed runs).
    if existing:
        start = (today - timedelta(days=14)).strftime("%Y%m%d")
        g_start = start + "000000"
    else:
        start, g_start = WP_START, GDELT_START

    wp_en = fetch_wikipedia("en.wikipedia", "Bitcoin", start, end)
    wp_ja = fetch_wikipedia("ja.wikipedia",
                            "%E3%83%93%E3%83%83%E3%83%88%E3%82%B3%E3%82%A4%E3%83%B3",
                            start, end)
    gdelt = fetch_gdelt(g_start, end + "000000")
    fng = fetch_fng()

    days = set(existing) | set(wp_en) | set(wp_ja) | set(gdelt)
    updated = 0
    for day in days:
        row = existing.get(day) or {k: "" for k in FIELDS}
        row["date"] = day
        before = dict(row)
        for key, src in (("wp_en", wp_en), ("wp_ja", wp_ja),
                         ("gdelt_vol", gdelt), ("fng", fng)):
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
