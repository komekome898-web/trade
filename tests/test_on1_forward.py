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


def test_aggregate_on1_reads_ledger_and_guard(tmp_path):
    from bot.monitoring.aggregate import _on1_paper, collect_status
    # no ledger -> None, and collect_status still publishes the key
    assert _on1_paper(tmp_path / "ledger.csv", 0.0) is None
    d = collect_status(tmp_path, now=1_000_000.0)
    assert "on1" in d and d["on1"] is None
    # small real-shaped ledger
    p = tmp_path / "ledger.csv"
    with p.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=paper.FIELDS)
        w.writeheader()
        w.writerow({**{k: "" for k in paper.FIELDS},
                    "entry_date": "20260101", "exit_date": "20260102",
                    "net_yen": "+978", "net_bps": "+24.700",
                    "micro_minus_large_entry": "-10", "micro_minus_large_exit": "+10"})
        w.writerow({**{k: "" for k in paper.FIELDS},
                    "entry_date": "20260102", "exit_date": "20260103",
                    "note": "skip: exit print missing"})
    o = _on1_paper(p, 1_000_000.0)
    assert o["trades"] == 1 and o["skipped"] == 1
    assert o["cum_net_yen"] == 978 and o["guard"] == "OK"
    assert o["friction_yen"] is None  # n<15 -> friction line not evaluated


def test_dashboard_page_renders_on1_tiles():
    page = (ROOT / "scripts" / "dashboard.py").read_text(encoding="utf-8")
    assert "on1Tiles(d.on1)" in page
    for field in ("cum_net_yen", "mean_net_bps", "guard", "friction_yen", "last_exit_date"):
        assert f"o.{field}" in page


def test_attention_gauge_z_and_missing(tmp_path):
    from bot.monitoring.aggregate import _attention_gauge
    assert _attention_gauge(tmp_path / "attention.csv", 0.0) is None
    p = tmp_path / "attention.csv"
    import math
    with p.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "wp_en", "wp_ja", "gdelt_vol", "fng"])
        # 450 mildly-noisy days then a spike on the last day -> large positive z
        for i in range(450):
            base = 1000 + (i % 7) * 10
            w.writerow([f"2025{i:04d}", str(base), str(base), "", "50"])
        w.writerow(["20260101", "8000", "8000", "", "77"])
    o = _attention_gauge(p, 0.0)
    assert o is not None and o["z_wp_ja"] is not None
    assert o["z_wp_ja"] > 3          # log spike vs flat window
    assert o["fng"] == 77
    # too-short history -> gauge withholds z rather than fake one
    p2 = tmp_path / "short.csv"
    with p2.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "wp_en", "wp_ja", "gdelt_vol", "fng"])
        for i in range(100):
            w.writerow([f"2026{i:04d}", "1000", "1000", "", ""])
    o2 = _attention_gauge(p2, 0.0)
    assert o2 is None or o2.get("z_wp_ja") is None


def test_dashboard_page_renders_attention_tile():
    page = (ROOT / "scripts" / "dashboard.py").read_text(encoding="utf-8")
    assert "attentionTile(d.attention)" in page
    for field in ("z_wp_ja", "z_wp_en", "z_gdelt", "fng"):
        assert f"a.{field}" in page


def test_attention_chart_monthly_series(tmp_path):
    from bot.monitoring.aggregate import _attention_chart
    from bot.monitoring.gates import clear_cache
    clear_cache()
    p = tmp_path / "attention.csv"
    with p.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "wp_en", "wp_ja", "gdelt_vol", "fng", "btc_usd",
                    "btc_open", "btc_high", "btc_low"])
        for i in range(500):
            m, d = divmod(i, 28)
            base = 1000 + (i % 7) * 10
            px = 50000 + i
            w.writerow([f"2024{m+1:02d}{d+1:02d}" if m < 12 else f"2025{m-11:02d}{d+1:02d}",
                        str(base), str(base), "", "", str(px),
                        str(px - 5), str(px + 10), str(px - 10)])
    series = _attention_chart(p)
    assert series, "monthly series should not be empty"
    assert all(set(r) == {"m", "o", "h", "l", "c", "ja", "en", "gd"} for r in series)
    # last close / first open / max high / min low of each month; sorted months
    assert [r["m"] for r in series] == sorted(r["m"] for r in series)
    last = series[-1]
    assert last["c"] == 50000 + 499 and last["h"] == 50000 + 499 + 10
    first = series[0]
    assert first["o"] == 50000 - 5 and first["l"] == 50000 - 10
    clear_cache()


def test_dashboard_page_renders_attention_chart():
    page = (ROOT / "scripts" / "dashboard.py").read_text(encoding="utf-8")
    assert 'id="a-chart"' in page and "drawAttentionChart" in page
    assert "attention_chart" in page
    # validated palette, fixed stacking order, no dual axis
    for hex_ in ("#c08a20", "#4a86d1", "#d16a9e"):
        assert hex_ in page
