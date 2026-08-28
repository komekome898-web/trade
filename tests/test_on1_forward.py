"""ON1 forward tracking: JPX daily-report row parsing and paper ledger rules."""

import csv
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


fetch_jpx = _load("fetch_jpx_daily")
paper = _load("paper_on1")

# Real lines captured from sif_dyr_20260827.pdf (large / micro; micro uses "…"
# for suppressed strategy columns on thin months).
LINE_LARGE = ("202609 09.10 161090018 66,260 66,410 65,750 66,120 67,000 67,180 65,770 66,150 "
              "- 260 21,848 210 1,448,141 13,861 66,150.00 154,609")
LINE_MICRO_THIN = ("202611 11.12 161110023 66,090 66,170 65,410 65,955 66,500 66,910 65,600 65,895 "
                   "- 230 390 … 257 … 65,910 369")


def test_row_regex_parses_real_lines():
    m = fetch_jpx.ROW_RE.match(LINE_LARGE)
    assert m and m.group("month") == "202609"
    assert m.group("do") == "67,000" and m.group("dc") == "66,150"
    m2 = fetch_jpx.ROW_RE.match(LINE_MICRO_THIN)
    assert m2 and m2.group("no") == "66,090" and m2.group("dc") == "65,895"


def _sessions_csv(tmp_path, rows):
    p = tmp_path / "nk225_sessions.csv"
    with p.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fetch_jpx.FIELDS)
        w.writeheader()
        w.writerows(rows)
    return p


def _row(date, product, month, day_open, day_close, vol):
    r = {k: "" for k in fetch_jpx.FIELDS}
    r.update({"date": date, "product": product, "month": month,
              "day_open": day_open, "day_close": day_close, "day_volume": vol})
    return r


def test_ledger_central_month_fee_and_deviation(tmp_path, monkeypatch):
    rows = [
        # day 1: two micro months; 202609 has larger volume -> central
        _row("20260101", "micro", "202609", "40000", "40100", "1000"),
        _row("20260101", "micro", "202612", "40200", "40300", "10"),
        _row("20260101", "large", "202609", "40010", "40110", "500"),
        # day 2: exit prints
        _row("20260102", "micro", "202609", "40200", "40250", "900"),
        _row("20260102", "large", "202609", "40190", "40240", "400"),
    ]
    monkeypatch.setattr(paper, "IN_CSV", _sessions_csv(tmp_path, rows))
    ledger = paper.build_ledger()
    assert len(ledger) == 1
    t = ledger[0]
    assert t["month"] == "202609"          # picked by volume, not by price
    assert t["entry_px"] == "40100" and t["exit_px"] == "40200"
    # net yen = (40200-40100)*10 - 22
    assert t["net_yen"] == "+978"
    assert t["micro_minus_large_entry"] == "-10"  # 40100 - 40110
    assert t["micro_minus_large_exit"] == "+10"   # 40200 - 40190


def test_ledger_skips_missing_exit_print(tmp_path, monkeypatch):
    rows = [
        _row("20260101", "micro", "202609", "40000", "40100", "1000"),
        _row("20260102", "micro", "202612", "40200", "40300", "900"),  # month rolled away
    ]
    monkeypatch.setattr(paper, "IN_CSV", _sessions_csv(tmp_path, rows))
    ledger = paper.build_ledger()
    assert len(ledger) == 1
    assert ledger[0]["note"].startswith("skip: exit print missing")
    assert ledger[0]["net_bps"] == ""
