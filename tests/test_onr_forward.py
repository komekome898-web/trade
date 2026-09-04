"""ONR forward tracking: paper ledger construction, guard percentiles, idempotency."""

import csv
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


paper = _load("paper_onr")


def _etf_row(date, open_, close, div=""):
    return {"date": date, "open": str(open_), "close": str(close), "div_yen": str(div)}


def _idx_row(date, open_, close):
    return {"date": date, "open": str(open_), "close": str(close)}


def test_kabutan_row_regex_parses_real_row():
    html = (
        '<table class="stock_kabuka_dwm">'
        '<thead><tr><th>a</th></tr></thead><tbody>'
        '<tr><th scope="row"><time datetime="2026-09-03">26/09/03</time></th>'
        '<td>1,784.97</td><td>1,789.42</td><td>1,773.07</td><td>1,773.07</td>'
        '<td><span class="down">-6.81</span></td><td><span class="down">-0.38</span></td>'
        '<td>-</td></tr></tbody></table>'
    )
    import re
    m = re.search(r'<table class="stock_kabuka_dwm">(.*?)</table>', html, re.S)
    rows = paper.KABUTAN_ROW_RE.findall(m.group(1))
    assert rows == [("2026-09-03", "1,784.97", "1,789.42", "1,773.07", "1,773.07")]


def test_ledger_basic_trade_and_no_backfill_before_freeze():
    # a trade entirely before LEDGER_START must not appear in the ledger
    etf = {r["date"]: r for r in [
        _etf_row("2026-09-01", 1900, 1905),
        _etf_row("2026-09-02", 1905, 1908),  # entry->exit both before freeze: excluded
        _etf_row("2026-09-04", 1930, 1935),  # entry date == freeze date: included
        _etf_row("2026-09-07", 1940, 1945),
    ]}
    ledger = paper.build_ledger(etf, {})
    dates = [(r["date_entry"], r["date_exit"]) for r in ledger]
    assert ("2026-09-01", "2026-09-02") not in dates
    assert ("2026-09-02", "2026-09-04") not in dates
    assert dates == [("2026-09-04", "2026-09-07")]
    t = ledger[0]
    # close_entry = entry day's close (1935); open_exit = exit day's open (1940)
    assert t["close_entry"] == "1935.00" and t["open_exit"] == "1940.00"
    assert t["qty"] == 10
    assert float(t["pnl_yen"]) == (1940 - 1935) * 10
    assert t["cum_pnl_yen"] == t["pnl_yen"]


def test_ledger_ex_dividend_day_credits_dividend_to_exit_leg():
    etf = {r["date"]: r for r in [
        _etf_row("2026-09-04", 1900, 1910),          # close_entry = 1910
        _etf_row("2026-09-07", 1905, 1900, div=20.6),  # open_exit = 1905, ex-div here
    ]}
    ledger = paper.build_ledger(etf, {})
    assert len(ledger) == 1
    t = ledger[0]
    assert t["dividend_yen"] == "206.0"  # 20.6 * qty(10)
    expected_pnl = (1905 - 1910) * 10 + 206.0
    assert float(t["pnl_yen"]) == expected_pnl


def test_ledger_missing_index_day_leaves_gap_blank_but_keeps_etf_trade():
    etf = {r["date"]: r for r in [
        _etf_row("2026-09-04", 1900, 1910),
        _etf_row("2026-09-07", 1910, 1920),
        _etf_row("2026-09-08", 1920, 1915),
    ]}
    # index has a row for 09-04 and 09-08 but is missing 09-07 entirely
    index = {r["date"]: r for r in [
        _idx_row("2026-09-04", 1780, 1790),
        _idx_row("2026-09-08", 1790, 1785),
    ]}
    ledger = paper.build_ledger(etf, index)
    assert len(ledger) == 2
    trade1 = next(r for r in ledger if r["date_entry"] == "2026-09-04")
    trade2 = next(r for r in ledger if r["date_entry"] == "2026-09-07")
    # trade1: exit leg (09-07) has no index row -> blank
    assert trade1["index_on_bps"] == "" and trade1["gap_bps"] == ""
    # trade2: entry leg (09-07) has no index row -> blank
    assert trade2["index_on_bps"] == "" and trade2["gap_bps"] == ""
    # ETF pnl/bps must still be computed for both despite missing index
    assert trade1["etf_on_bps"] != "" and trade2["etf_on_bps"] != ""
    # cumulative pnl carries across both trades in order
    assert float(trade2["cum_pnl_yen"]) == float(trade1["pnl_yen"]) + float(trade2["pnl_yen"])


def test_ledger_zero_price_glitch_is_skipped():
    etf = {r["date"]: r for r in [
        _etf_row("2026-09-04", 1900, 1910),
        _etf_row("2026-09-07", 0, 0),  # bad print, whole day (open=close=0)
        _etf_row("2026-09-08", 1920, 1915),
    ]}
    ledger = paper.build_ledger(etf, {})
    # the 09-04->09-07 leg is dropped (open_exit<=0); 09-07->09-08 is dropped too
    # (close_entry<=0 on that leg)
    assert ledger == []


def test_guard_percentiles_ok_caution_stop():
    # 63 daily bps values summing under p05 (-6.78%) but not under p01 (-12.39%)
    # -> caution.  -6.78% over 63 trades = -10.76 bps/trade average.
    caution_bps = -11.0
    ledger = [{"etf_on_bps": str(caution_bps)} for _ in range(63)]
    assert paper.evaluate_guard(ledger) == "caution"

    stop_bps = -25.0  # 63 * -25bps = -15.75% < p01 -12.39%
    ledger_stop = [{"etf_on_bps": str(stop_bps)} for _ in range(63)]
    assert paper.evaluate_guard(ledger_stop) == "stop"

    ok_bps = 1.0
    ledger_ok = [{"etf_on_bps": str(ok_bps)} for _ in range(300)]
    assert paper.evaluate_guard(ledger_ok) == "ok"

    # fewer trades than the smallest window -> always ok (no window evaluated)
    assert paper.evaluate_guard([{"etf_on_bps": "-1000.0"}]) == "ok"


def test_write_status_shape(tmp_path, monkeypatch):
    monkeypatch.setattr(paper, "OUT_DIR", tmp_path)
    monkeypatch.setattr(paper, "STATUS_JSON", tmp_path / "status.json")
    etf = {r["date"]: r for r in [
        _etf_row("2026-09-04", 1900, 1910),
        _etf_row("2026-09-07", 1910, 1920),
    ]}
    ledger = paper.build_ledger(etf, {})
    status = paper.write_status(ledger)
    assert status["n_trades"] == 1
    assert status["guard"] == "ok"
    assert status["last_date"] == "2026-09-07"
    on_disk = json.loads((tmp_path / "status.json").read_text())
    assert on_disk == status

    # empty ledger still produces a well-shaped status
    empty_status = paper.write_status([])
    assert empty_status["n_trades"] == 0 and empty_status["guard"] == "ok"
    assert empty_status["last_date"] is None


def test_self_heal_never_drops_history_and_is_idempotent(tmp_path):
    path = tmp_path / "etf.csv"
    first = [_etf_row("2026-08-01", 1000, 1010), _etf_row("2026-08-02", 1010, 1005)]
    changed1 = paper.self_heal_csv(path, paper.ETF_FIELDS, first)
    assert changed1 == 2
    rows_after_first = paper.load_csv(path)
    assert set(rows_after_first) == {"2026-08-01", "2026-08-02"}

    # a later "fetch" only covers a recent window (self-heal, no network) --
    # earlier history must survive untouched, and re-running with identical
    # rows for the covered dates must report zero changes (idempotent).
    second = [_etf_row("2026-08-02", 1010, 1005), _etf_row("2026-09-04", 1900, 1910)]
    changed2 = paper.self_heal_csv(path, paper.ETF_FIELDS, second)
    assert changed2 == 1  # only the new 09-04 row is new; 08-02 unchanged
    rows_after_second = paper.load_csv(path)
    assert set(rows_after_second) == {"2026-08-01", "2026-08-02", "2026-09-04"}
    assert rows_after_second["2026-08-01"]["close"] == "1010"

    # re-running with the exact same `second` batch changes nothing
    changed3 = paper.self_heal_csv(path, paper.ETF_FIELDS, second)
    assert changed3 == 0


def test_full_pipeline_idempotent_rebuild(tmp_path, monkeypatch):
    etf_path = tmp_path / "etf.csv"
    idx_path = tmp_path / "idx.csv"
    monkeypatch.setattr(paper, "ETF_CSV", etf_path)
    monkeypatch.setattr(paper, "INDEX_CSV", idx_path)
    monkeypatch.setattr(paper, "LEDGER_CSV", tmp_path / "ledger.csv")
    monkeypatch.setattr(paper, "STATUS_JSON", tmp_path / "status.json")
    monkeypatch.setattr(paper, "OUT_DIR", tmp_path)

    paper.self_heal_csv(etf_path, paper.ETF_FIELDS, [
        _etf_row("2026-09-04", 1900, 1910), _etf_row("2026-09-07", 1910, 1920),
    ])
    paper.self_heal_csv(idx_path, paper.INDEX_FIELDS, [
        _idx_row("2026-09-04", 1780, 1790), _idx_row("2026-09-07", 1790, 1795),
    ])

    def rebuild():
        etf_rows = paper.load_csv(etf_path)
        idx_rows = paper.load_csv(idx_path)
        ledger = paper.build_ledger(etf_rows, idx_rows)
        with paper.LEDGER_CSV.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=paper.LEDGER_FIELDS)
            w.writeheader()
            w.writerows(ledger)
        return paper.write_status(ledger)

    s1 = rebuild()
    ledger_bytes_1 = paper.LEDGER_CSV.read_bytes()
    s2 = rebuild()
    ledger_bytes_2 = paper.LEDGER_CSV.read_bytes()
    assert s1 == s2
    assert ledger_bytes_1 == ledger_bytes_2


def test_aggregate_onr_reads_status_and_shared_or_local(tmp_path):
    from bot.monitoring.aggregate import _onr_paper, collect_status

    assert _onr_paper(tmp_path, 0.0) is None
    d = collect_status(tmp_path, now=1_000_000.0)
    assert "onr" in d and d["onr"] is None

    # local copy only
    local_dir = tmp_path / "data" / "paper_onr"
    local_dir.mkdir(parents=True)
    (local_dir / "status.json").write_text(json.dumps({
        "n_trades": 2, "cum_pnl_yen": 150.0, "mean_bps": 5.0,
        "gap_mean_bps": 1.2, "guard": "ok", "last_date": "2026-09-07",
    }))
    (local_dir / "ledger.csv").write_text("date_entry,date_exit\n2026-09-04,2026-09-05\n2026-09-06,2026-09-07\n")
    out = _onr_paper(tmp_path, 1_000_000.0)
    assert out["n_trades"] == 2 and out["guard"] == "ok" and out["n_ledger_rows"] == 2

    # a newer shared copy (paper_logs/onr_status.json) takes precedence
    import os
    import time as _time
    shared_dir = tmp_path / "paper_logs"
    shared_dir.mkdir()
    shared_status = shared_dir / "onr_status.json"
    shared_status.write_text(json.dumps({
        "n_trades": 9, "cum_pnl_yen": 999.0, "mean_bps": 9.0,
        "gap_mean_bps": None, "guard": "stop", "last_date": "2026-09-10",
    }))
    future = _time.time() + 10
    os.utime(shared_status, (future, future))
    out2 = _onr_paper(tmp_path, 1_000_000.0)
    assert out2["n_trades"] == 9 and out2["guard"] == "stop"


def test_dashboard_page_renders_onr_tiles():
    page = (ROOT / "scripts" / "dashboard.py").read_text(encoding="utf-8")
    assert "onrTiles(d.onr)" in page
    for field in ("cum_pnl_yen", "mean_bps", "guard", "gap_mean_bps", "last_date", "n_trades"):
        assert f"o.{field}" in page
