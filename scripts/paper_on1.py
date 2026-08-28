"""ON1 forward paper ledger builder (docs/PREREG_on1_forward.md, frozen 2026-08-28).

Paper rule (verbatim from the PREREG):
  - Instrument: Nikkei 225 MICRO futures, always long, 1 contract (x10 multiplier).
  - Contract month: the micro month with the LARGEST day-session volume that day
    (central month; entry and exit use the SAME month).
  - Entry price: that day's day-session close (closing auction print).
    Exit price: next trading day's day-session open (opening auction print).
  - Cost: fee 11 yen/contract/side (22 yen round trip).  No slippage charge;
    instead the micro-vs-large print deviation is recorded daily as a diagnostic.
  - A day with a missing central-month print is SKIPPED with a reason
    (never back-filled).

Input:  data/jpx_daily/nk225_sessions.csv (built by scripts/fetch_jpx_daily.py)
Output: data/paper_on1/ledger.csv  (fully rebuilt from the input on every run --
        deterministic, no hidden state)

Warning / stop lines (PREREG sec.3) are evaluated on the ledger and printed.
"""

from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IN_CSV = ROOT / "data" / "jpx_daily" / "nk225_sessions.csv"
OUT_DIR = ROOT / "data" / "paper_on1"
OUT_CSV = OUT_DIR / "ledger.csv"

MULTIPLIER = 10
FEE_SIDE = 11.0
GUARDS = {  # window (trading days) -> (p05 warn, p01 stop), from PREREG sec.3
    63: (-11.1, -22.4),
    126: (-14.2, -42.5),
    245: (-20.4, -51.1),
}

FIELDS = [
    "entry_date", "exit_date", "month",
    "entry_px", "exit_px", "gross_bps", "fee_yen", "net_yen", "net_bps",
    "large_entry_px", "large_exit_px", "micro_minus_large_entry", "micro_minus_large_exit",
    "note",
]


def load_sessions() -> dict[str, dict[str, dict]]:
    """date -> product -> {month -> row}"""
    out: dict[str, dict[str, dict]] = {}
    with IN_CSV.open() as f:
        for r in csv.DictReader(f):
            out.setdefault(r["date"], {}).setdefault(r["product"], {})[r["month"]] = r
    return out


def central_micro_month(products: dict[str, dict]) -> str | None:
    micro = products.get("micro", {})
    best, best_vol = None, -1.0
    for month, row in micro.items():
        vol = float(row["day_volume"]) if row["day_volume"] else 0.0
        if vol > best_vol:
            best, best_vol = month, vol
    return best


def build_ledger() -> list[dict]:
    sessions = load_sessions()
    dates = sorted(sessions)
    ledger: list[dict] = []
    for d0, d1 in zip(dates, dates[1:]):
        p0, p1 = sessions[d0], sessions[d1]
        month = central_micro_month(p0)
        rec = {k: "" for k in FIELDS}
        rec.update({"entry_date": d0, "exit_date": d1, "month": month or ""})
        if month is None:
            rec["note"] = "skip: no micro rows on entry day"
            ledger.append(rec)
            continue
        entry_row = p0["micro"][month]
        exit_row = p1.get("micro", {}).get(month)
        if not entry_row["day_close"]:
            rec["note"] = "skip: entry print missing"
            ledger.append(rec)
            continue
        if exit_row is None or not exit_row["day_open"]:
            rec["note"] = "skip: exit print missing"
            ledger.append(rec)
            continue
        e = float(entry_row["day_close"])
        x = float(exit_row["day_open"])
        gross_bps = math.log(x / e) * 1e4
        net_yen = (x - e) * MULTIPLIER - 2 * FEE_SIDE
        net_bps = gross_bps - (2 * FEE_SIDE) / (e * MULTIPLIER) * 1e4
        rec.update({
            "entry_px": f"{e:.0f}", "exit_px": f"{x:.0f}",
            "gross_bps": f"{gross_bps:+.3f}", "fee_yen": f"{2*FEE_SIDE:.0f}",
            "net_yen": f"{net_yen:+.0f}", "net_bps": f"{net_bps:+.3f}",
        })
        for leg, day, key in (("entry", d0, "day_close"), ("exit", d1, "day_open")):
            large = sessions[day].get("large", {}).get(month, {})
            px = large.get(key, "")
            if px:
                rec[f"large_{leg}_px"] = px
                micro_px = e if leg == "entry" else x
                rec[f"micro_minus_large_{leg}"] = f"{micro_px - float(px):+.0f}"
        ledger.append(rec)
    return ledger


def check_guards(ledger: list[dict]) -> None:
    rets = [float(r["net_bps"]) / 1e4 for r in ledger if r["net_bps"]]
    if not rets:
        return
    for win, (warn, stop) in GUARDS.items():
        if len(rets) < win:
            continue
        cum = sum(rets[-win:]) * 100
        if cum < stop:
            print(f"paper_on1: STOP line breached: {win}d cum {cum:+.2f}% < p01 {stop}% -- halt and investigate (PREREG sec.3)")
        elif cum < warn:
            print(f"paper_on1: WARN: {win}d cum {cum:+.2f}% < p05 {warn}% -- review required (PREREG sec.3)")
    # auction-friction stop line (PREREG sec.3 as amended 2026-08-28): the cost of
    # executing on micro prints instead of large prints is the SIGNED round-trip
    # difference exit_dev - entry_dev (deviations are symmetric noise otherwise).
    recent = [r for r in ledger[-21:] if r["micro_minus_large_entry"] and r["micro_minus_large_exit"]]
    if len(recent) >= 15:
        rt_cost = sum(float(r["micro_minus_large_exit"]) - float(r["micro_minus_large_entry"]) for r in recent) / len(recent)
        mean_abs = sum(abs(float(r["micro_minus_large_entry"])) for r in recent) / len(recent)
        print(f"paper_on1: micro-vs-large friction: signed RT cost {rt_cost:+.1f} yen/trade, "
              f"|entry dev| mean {mean_abs:.1f} yen (n={len(recent)})")
        if rt_cost < -10.0:
            print("paper_on1: STOP line breached: mean signed friction cost < -10 yen (2 micro ticks) -- "
                  "auction friction exceeds the conservative cost premise (PREREG sec.3)")


def main() -> int:
    if not IN_CSV.exists():
        print("paper_on1: no input (run scripts/fetch_jpx_daily.py first)")
        return 0
    ledger = build_ledger()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(ledger)
    traded = [r for r in ledger if r["net_bps"]]
    skipped = len(ledger) - len(traded)
    total_yen = sum(float(r["net_yen"]) for r in traded)
    print(f"paper_on1: {len(traded)} paper trades ({skipped} skipped), cumulative net {total_yen:+.0f} yen")
    if traded:
        mean_bps = sum(float(r["net_bps"]) for r in traded) / len(traded)
        print(f"paper_on1: mean net {mean_bps:+.2f} bps/day over {len(traded)} days")
    check_guards(ledger)
    return 0


if __name__ == "__main__":
    sys.exit(main())
