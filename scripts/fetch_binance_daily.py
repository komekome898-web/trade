"""Daily Binance USDT-M futures metrics + USDJPY reference rate.

Feeds the dashboard's データ蓄積 table (G6特徴量・レジーム監視 / 円換算) — no
trading signal, collection only.

data/binance_daily/metrics.csv: one row per UTC day, the 5-minute rows of
Binance's public daily metrics dump (data.binance.vision, no API key, no
geo-block — unlike api.binance.com) averaged down to a daily mean. Columns:
date, sum_open_interest, sum_open_interest_value,
count_toptrader_long_short_ratio, sum_toptrader_long_short_ratio,
count_long_short_ratio, sum_taker_long_short_vol_ratio.
First run backfills the most recent METRICS_BACKFILL_DAYS days; later runs
re-check the same recent window and fetch only the days still missing, so a
day that failed on an earlier run (network blip, not-yet-published file)
self-heals on the next one instead of leaving a permanent hole.

data/binance_daily/usdjpy.csv: date, usdjpy — the ECB reference rate via
frankfurter.app (free, no key). First run backfills full history since
FRANKFURTER_START; later runs top up the last USDJPY_TOPUP_DAYS days.

Both fetches retry FETCH_TRIES times with exponential backoff and print (not
swallow) a failure before moving on to the next day/source.
"""

from __future__ import annotations

import csv
import io
import sys
import time
import zipfile
from datetime import date, timedelta
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "binance_daily"
METRICS_OUT = OUT_DIR / "metrics.csv"
USDJPY_OUT = OUT_DIR / "usdjpy.csv"

METRICS_FIELDS = ["date", "sum_open_interest", "sum_open_interest_value",
                  "count_toptrader_long_short_ratio", "sum_toptrader_long_short_ratio",
                  "count_long_short_ratio", "sum_taker_long_short_vol_ratio"]
METRICS_COLS = METRICS_FIELDS[1:]

METRICS_URL = ("https://data.binance.vision/data/futures/um/daily/metrics/"
              "BTCUSDT/BTCUSDT-metrics-{day}.zip")
METRICS_BACKFILL_DAYS = 30   # first run; later runs re-scan the same window
                              # for gaps, so it doubles as the self-heal window

FRANKFURTER_START = "2015-01-01"
FRANKFURTER_URL = "https://api.frankfurter.app/{start}..?from=USD&to=JPY"
USDJPY_TOPUP_DAYS = 14

UA = {"User-Agent": "trade-research-collector/1.0"}
FETCH_TRIES = 3


def _get(url: str, timeout: int = 60, tries: int = FETCH_TRIES) -> bytes:
    """GET with exponential backoff. Prints (never swallows) the final
    failure, then re-raises so the caller decides whether to skip or abort."""
    last: Exception | None = None
    for attempt in range(tries):
        try:
            resp = requests.get(url, headers=UA, timeout=timeout)
            resp.raise_for_status()
            return resp.content
        except requests.RequestException as exc:
            last = exc
            if attempt + 1 < tries:
                time.sleep(2 ** attempt)
    print(f"fetch_binance_daily: GET failed after {tries} tries: {url} ({last})")
    raise last  # type: ignore[misc]


# ---- Binance daily metrics -------------------------------------------------
def parse_metrics_zip(content: bytes) -> list[dict[str, str]]:
    """The 5-minute rows inside one daily metrics zip."""
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        name = zf.namelist()[0]
        text = zf.read(name).decode("utf-8")
    return list(csv.DictReader(io.StringIO(text)))


def aggregate_daily(rows: list[dict[str, str]]) -> dict[str, float | None]:
    """Daily mean of each metrics column. A column with no parseable values
    on the day (e.g. a field Binance had not started publishing yet) is None,
    not zero -- the CSV writer below emits an empty cell for it."""
    out: dict[str, float | None] = {}
    for col in METRICS_COLS:
        vals: list[float] = []
        for r in rows:
            v = r.get(col)
            if v in (None, ""):
                continue
            try:
                vals.append(float(v))
            except ValueError:
                continue
        out[col] = round(sum(vals) / len(vals), 6) if vals else None
    return out


def fetch_metrics_day(day: date) -> dict[str, float | None] | None:
    content = _get(METRICS_URL.format(day=day.strftime("%Y-%m-%d")))
    rows = parse_metrics_zip(content)
    if not rows:
        return None
    return aggregate_daily(rows)


def load_metrics_csv(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8") as f:
        return {r["date"]: r for r in csv.DictReader(f)}


def write_metrics_csv(path: Path, rows: dict[str, dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=METRICS_FIELDS)
        w.writeheader()
        for day in sorted(rows):
            w.writerow({k: rows[day].get(k, "") for k in METRICS_FIELDS})


def update_metrics(today: date | None = None) -> int:
    """Backfill/self-heal data/binance_daily/metrics.csv. Returns rows fetched."""
    today = today or date.today()
    existing = load_metrics_csv(METRICS_OUT)
    # Binance publishes a day's file only after that UTC day has closed, so
    # the newest day this run can ever fetch is yesterday.
    latest = today - timedelta(days=1)
    window = [latest - timedelta(days=i) for i in range(METRICS_BACKFILL_DAYS)]
    missing = [d for d in window if d.strftime("%Y%m%d") not in existing]
    fetched = 0
    for day in missing:
        key = day.strftime("%Y%m%d")
        try:
            agg = fetch_metrics_day(day)
        except requests.RequestException:
            continue          # already printed inside _get; try the next day
        except (zipfile.BadZipFile, KeyError, IndexError, UnicodeDecodeError) as exc:
            print(f"fetch_binance_daily: metrics {key} parse failed: {exc}")
            continue
        if agg is None:
            continue
        existing[key] = {"date": key, **{k: ("" if v is None else v) for k, v in agg.items()}}
        fetched += 1
    write_metrics_csv(METRICS_OUT, existing)
    print(f"binance metrics: {len(existing)} rows ({fetched} fetched), "
          f"latest {max(existing) if existing else '-'}")
    return fetched


# ---- USDJPY -----------------------------------------------------------------
def fetch_usdjpy(start: str) -> dict[str, float]:
    """{YYYYMMDD: rate} from frankfurter.app's open-ended range endpoint."""
    import json

    content = _get(FRANKFURTER_URL.format(start=start))
    data = json.loads(content)
    out: dict[str, float] = {}
    for day, rates in (data.get("rates") or {}).items():
        if "JPY" in rates:
            out[day.replace("-", "")] = float(rates["JPY"])
    return out


def load_usdjpy_csv(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8") as f:
        return {r["date"]: r["usdjpy"] for r in csv.DictReader(f)}


def write_usdjpy_csv(path: Path, rows: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "usdjpy"])
        for day in sorted(rows):
            w.writerow([day, rows[day]])


def update_usdjpy(today: date | None = None) -> int:
    """Backfill (first run) or 14-day top-up data/binance_daily/usdjpy.csv."""
    today = today or date.today()
    existing = load_usdjpy_csv(USDJPY_OUT)
    start = (FRANKFURTER_START if not existing
             else (today - timedelta(days=USDJPY_TOPUP_DAYS)).isoformat())
    try:
        fetched = fetch_usdjpy(start)
    except (requests.RequestException, ValueError) as exc:
        print(f"fetch_binance_daily: usdjpy fetch failed: {exc}")
        fetched = {}
    updated = sum(1 for d, v in fetched.items()
                 if existing.get(d) != f"{v:.4f}")
    for day, rate in fetched.items():
        existing[day] = f"{rate:.4f}"
    write_usdjpy_csv(USDJPY_OUT, existing)
    print(f"usdjpy: {len(existing)} rows ({updated} updated), "
          f"latest {max(existing) if existing else '-'}")
    return updated


def main() -> int:
    update_metrics()
    update_usdjpy()
    return 0


if __name__ == "__main__":
    sys.exit(main())
