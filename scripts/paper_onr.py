"""ONR forward paper ledger builder (docs/PREREG_onr_forward.md, frozen 2026-09-04).

Paper rule (verbatim from the PREREG sec.1):
  - Instrument: J-REIT ETF 1343 (TSE REIT index-tracking). Always long, fixed
    10 units, every business day, unconditional (no exclusions for SQ,
    ex-dividend, or pre-holiday sessions).
  - Entry: closing-auction print (15:30) that day. Exit: opening-auction print
    (9:00) the next trading day.
  - pnl_yen = (open_exit - close_entry) * 10 + dividend_yen (dividend credited
    only when the exit date is the ex-dividend date -- the overnight holder is
    entitled).  Fee = 0 (auction print, no slippage charge in the paper model).
  - gap_bps = ETF overnight bps - TSE REIT index overnight bps, recorded daily
    for attribution (sec.2). Blank when the index row for either leg is
    missing -- tolerated, never blocks the ETF-only trade.
  - Ledger starts at the first trade with date_entry >= 2026-09-04 (freeze
    date). Earlier history is never backfilled into the ledger (sec.1).

Data maintained (append/self-heal; existing dates are refreshed with fresh
values but never dropped from history):
  data/onr/etf_1343_daily.csv    date,open,close,div_yen   (Yahoo chart API)
  data/onr/reit_index_daily.csv  date,open,close           (kabutan code=0105)

Output: data/paper_onr/ledger.csv (fully rebuilt from the two CSVs above on
every run -- deterministic, no hidden state, same convention as paper_on1.py)
        data/paper_onr/status.json ({n_trades, cum_pnl_yen, mean_bps,
        gap_mean_bps, guard, last_date})

Guard percentiles (PREREG sec.3, computed once from the full 1343 history
backtest_data/reit_onr_20260904/etf_1343_daily.csv 2008-09-16..2026-09-03,
n=4399 overnight returns after dropping open<=0/close<=0 rows and the
|log r|>0.10 glitch filter -- see docs/PREREG_onr_forward.md 付録A) are
duplicated here deliberately, same rationale as paper_on1.py: the dashboard
and this script must render the frozen lines even if either changes
independently, and a mismatch is itself a bug worth seeing.
"""

from __future__ import annotations

import csv
import json
import math
import re
import sys
import time
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "onr"
ETF_CSV = DATA_DIR / "etf_1343_daily.csv"
INDEX_CSV = DATA_DIR / "reit_index_daily.csv"
OUT_DIR = ROOT / "data" / "paper_onr"
LEDGER_CSV = OUT_DIR / "ledger.csv"
STATUS_JSON = OUT_DIR / "status.json"

QTY = 10
LEDGER_START = "2026-09-04"  # freeze date; no backfill before this (PREREG sec.1)

UA = {"User-Agent": "Mozilla/5.0"}
YAHOO_URL = "https://query1.finance.yahoo.com/v8/finance/chart/1343.T?range=1mo&interval=1d&events=div"
KABUTAN_URL = "https://kabutan.jp/stock/kabuka?code=0105&ashi=day&page=1"

# (p05 pct, p01 pct) of the rolling window cumulative overnight log-return
# distribution, PREREG sec.3. See docs/PREREG_onr_forward.md 付録A.
GUARDS = {
    63: (-6.78, -12.39),
    126: (-8.31, -13.32),
    252: (-9.11, -12.74),
}

ETF_FIELDS = ["date", "open", "close", "div_yen"]
INDEX_FIELDS = ["date", "open", "close"]
LEDGER_FIELDS = [
    "date_entry", "date_exit", "close_entry", "open_exit", "qty",
    "dividend_yen", "pnl_yen", "etf_on_bps", "index_on_bps", "gap_bps",
    "cum_pnl_yen",
]

KABUTAN_ROW_RE = re.compile(
    r'<time datetime="(?P<date>\d{4}-\d{2}-\d{2})">.*?</th>\s*'
    r'<td>(?P<open>[\d,.]+)</td>\s*'
    r'<td>(?P<high>[\d,.]+)</td>\s*'
    r'<td>(?P<low>[\d,.]+)</td>\s*'
    r'<td>(?P<close>[\d,.]+)</td>',
    re.S,
)


def _get(url: str, timeout: int = 30, tries: int = 3) -> bytes:
    last: Exception | None = None
    for attempt in range(tries):
        try:
            resp = requests.get(url, headers=UA, timeout=timeout)
            resp.raise_for_status()
            return resp.content
        except requests.RequestException as exc:  # read-only public data: retry
            last = exc
            if attempt < tries - 1:
                time.sleep(2 ** attempt)
    raise last  # type: ignore[misc]


# ------------------------------------------------------------------ fetch -- #

def fetch_etf_bars() -> list[dict[str, str]]:
    """1343.T daily bars (open/close = auction prints) + ex-dividend amounts."""
    payload = json.loads(_get(YAHOO_URL))
    result = payload["chart"]["result"][0]
    ts = result["timestamp"]
    q = result["indicators"]["quote"][0]
    div_by_date: dict[str, float] = {}
    for ev in (result.get("events") or {}).get("dividends", {}).values():
        d = time.strftime("%Y-%m-%d", time.gmtime(ev["date"]))
        div_by_date[d] = float(ev["amount"])
    rows: list[dict[str, str]] = []
    for i, t in enumerate(ts):
        o, c = q["open"][i], q["close"][i]
        if o is None or c is None:
            continue
        d = time.strftime("%Y-%m-%d", time.gmtime(t))
        rows.append({
            "date": d, "open": f"{o:.2f}", "close": f"{c:.2f}",
            "div_yen": f"{div_by_date[d]:.2f}" if d in div_by_date else "",
        })
    return rows


def fetch_index_page() -> list[dict[str, str]]:
    """Latest ~30 trading days of the TSE REIT index (code=0105) from kabutan."""
    html = _get(KABUTAN_URL).decode("utf-8", errors="replace")
    m = re.search(r'<table class="stock_kabuka_dwm">(.*?)</table>', html, re.S)
    if not m:
        return []
    rows = []
    for d, o, _h, _l, c in KABUTAN_ROW_RE.findall(m.group(1)):
        rows.append({"date": d, "open": o.replace(",", ""), "close": c.replace(",", "")})
    return rows


# --------------------------------------------------------------- self-heal -- #

def self_heal_csv(path: Path, fields: list[str], new_rows: list[dict[str, str]]) -> int:
    """Merge new_rows into path keyed by date. Existing dates not covered by
    new_rows are kept untouched (never dropped); dates present in both are
    refreshed with the fresh values. Returns the row count added or changed."""
    existing: dict[str, dict[str, str]] = {}
    if path.exists():
        with path.open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                existing[r["date"]] = r
    changed = 0
    for r in new_rows:
        if existing.get(r["date"]) != r:
            changed += 1
        existing[r["date"]] = r
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for d in sorted(existing):
            w.writerow({k: existing[d].get(k, "") for k in fields})
    return changed


def load_csv(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8") as f:
        return {r["date"]: r for r in csv.DictReader(f)}


# ---------------------------------------------------------------- ledger -- #

def build_ledger(etf_rows: dict[str, dict[str, str]],
                  index_rows: dict[str, dict[str, str]]) -> list[dict[str, Any]]:
    """Rebuild the full ledger from the accumulated ETF/index history, then
    the caller filters to date_entry >= LEDGER_START. Pure function -- no I/O,
    no network -- so tests can drive it with synthetic in-memory rows."""
    dates = sorted(etf_rows)
    ledger: list[dict[str, Any]] = []
    for d0, d1 in zip(dates, dates[1:]):
        r0, r1 = etf_rows[d0], etf_rows[d1]
        try:
            close_entry = float(r0["close"])
            open_exit = float(r1["open"])
        except (KeyError, ValueError):
            continue
        if close_entry <= 0 or open_exit <= 0:
            continue  # data glitch (missing print) -- self-heals on a later fetch
        div = 0.0
        if r1.get("div_yen"):
            try:
                div = float(r1["div_yen"])
            except ValueError:
                div = 0.0
        dividend_yen = div * QTY
        pnl_yen = (open_exit - close_entry) * QTY + dividend_yen
        etf_on_bps = math.log(open_exit / close_entry) * 1e4

        index_on_bps = ""
        gap_bps = ""
        i0, i1 = index_rows.get(d0), index_rows.get(d1)
        if i0 and i1:
            try:
                idx_close = float(i0["close"])
                idx_open = float(i1["open"])
                if idx_close > 0 and idx_open > 0:
                    idx_bps = math.log(idx_open / idx_close) * 1e4
                    index_on_bps = f"{idx_bps:.3f}"
                    gap_bps = f"{etf_on_bps - idx_bps:.3f}"
            except (KeyError, ValueError):
                pass

        ledger.append({
            "date_entry": d0, "date_exit": d1,
            "close_entry": f"{close_entry:.2f}", "open_exit": f"{open_exit:.2f}",
            "qty": QTY, "dividend_yen": f"{dividend_yen:.1f}",
            "pnl_yen": f"{pnl_yen:.1f}", "etf_on_bps": f"{etf_on_bps:.3f}",
            "index_on_bps": index_on_bps, "gap_bps": gap_bps,
        })

    cum = 0.0
    out: list[dict[str, Any]] = []
    for r in ledger:
        if r["date_entry"] < LEDGER_START:
            continue  # PREREG sec.1: no backfill before the freeze date
        cum += float(r["pnl_yen"])
        r["cum_pnl_yen"] = f"{cum:.1f}"
        out.append(r)
    return out


def evaluate_guard(ledger: list[dict[str, Any]]) -> str:
    """PREREG sec.3: p05 -> caution, p01 -> stop, checked over trailing
    63/126/252-trade windows of etf_on_bps (the same quantity the historical
    baseline in GUARDS was computed on -- see docs/PREREG_onr_forward.md 付録A)."""
    bps = [float(r["etf_on_bps"]) for r in ledger]
    state = "ok"
    for win, (p05, p01) in GUARDS.items():
        if len(bps) < win:
            continue
        cum_pct = sum(bps[-win:]) / 1e4 * 100
        if cum_pct < p01:
            return "stop"
        if cum_pct < p05:
            state = "caution"
    return state


def write_status(ledger: list[dict[str, Any]]) -> dict[str, Any]:
    if not ledger:
        status = {"n_trades": 0, "cum_pnl_yen": 0.0, "mean_bps": None,
                   "gap_mean_bps": None, "guard": "ok", "last_date": None}
    else:
        bps = [float(r["etf_on_bps"]) for r in ledger]
        gaps = [float(r["gap_bps"]) for r in ledger if r["gap_bps"]]
        status = {
            "n_trades": len(ledger),
            "cum_pnl_yen": round(float(ledger[-1]["cum_pnl_yen"]), 1),
            "mean_bps": round(sum(bps) / len(bps), 3),
            "gap_mean_bps": round(sum(gaps) / len(gaps), 3) if gaps else None,
            "guard": evaluate_guard(ledger),
            "last_date": ledger[-1]["date_exit"],
        }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with STATUS_JSON.open("w") as f:
        json.dump(status, f, indent=2)
        f.write("\n")
    return status


def main() -> int:
    try:
        etf_new = fetch_etf_bars()
        self_heal_csv(ETF_CSV, ETF_FIELDS, etf_new)
    except requests.RequestException as e:
        print(f"paper_onr: ETF fetch failed ({e}), using existing data/onr/etf_1343_daily.csv")

    try:
        idx_new = fetch_index_page()
        if idx_new:
            self_heal_csv(INDEX_CSV, INDEX_FIELDS, idx_new)
        else:
            print("paper_onr: kabutan page parsed 0 rows (format change?)")
    except requests.RequestException as e:
        print(f"paper_onr: index fetch failed ({e}), using existing data/onr/reit_index_daily.csv")

    etf_rows = load_csv(ETF_CSV)
    index_rows = load_csv(INDEX_CSV)
    if not etf_rows:
        print("paper_onr: no ETF data available, nothing to build")
        return 0

    ledger = build_ledger(etf_rows, index_rows)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with LEDGER_CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=LEDGER_FIELDS)
        w.writeheader()
        w.writerows(ledger)

    status = write_status(ledger)
    print(f"paper_onr: {status['n_trades']} paper trades, cumulative {status['cum_pnl_yen']:+.0f} yen, "
          f"guard={status['guard']}")
    if status["guard"] == "caution":
        print("paper_onr: CAUTION -- rolling overnight cum return below historical p05 (PREREG sec.3)")
    elif status["guard"] == "stop":
        print("paper_onr: STOP line breached -- below historical p01, halt and investigate (PREREG sec.3)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
