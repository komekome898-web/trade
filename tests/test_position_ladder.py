"""OI-delta entry-price ladder estimator + record_oi header migration."""

import csv
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


ladder = _load("research_position_ladder")
record_oi = _load("record_oi")


def _row(ts, oi, px):
    return {"ts_utc": ts, "okx_usdt_oi": str(oi), "btc_usd": str(px)}


def test_ladder_allocates_adds_and_retires_pro_rata():
    rows = [
        _row("2026-08-20T00:00:00+00:00", 1000, 70000),
        _row("2026-08-20T00:15:00+00:00", 1100, 70000),   # +100 at $70,000
        _row("2026-08-20T00:30:00+00:00", 1300, 72000),   # +200 at $72,000
        _row("2026-08-20T00:45:00+00:00", 1150, 71000),   # -150 pro-rata (x0.5)
    ]
    lad, px = ladder.build_ladder(rows)
    assert px == 71000
    assert abs(lad[70000.0] - 50) < 1e-9 and abs(lad[72000.0] - 100) < 1e-9
    assert sum(lad.values()) == 150


def test_ladder_skips_rows_without_price():
    rows = [_row("t0", 1000, 70000), {"ts_utc": "t1", "okx_usdt_oi": "1200", "btc_usd": ""},
            _row("t2", 1300, 71000)]
    lad, _ = ladder.build_ladder(rows)
    # the unpriced +200 step is skipped; only t0->t2 (+300 at 71,000) is booked
    assert lad == {71000.0: 300.0}


def test_record_oi_header_migration_keeps_old_rows(tmp_path):
    out = tmp_path / "oi.csv"
    old_fields = record_oi.FIELDS[:-1]
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=old_fields)
        w.writeheader()
        w.writerow({k: ("2026-08-20T00:00:00+00:00" if k == "ts_utc" else "1") for k in old_fields})
    record_oi.append_row({k: "2" for k in record_oi.FIELDS} | {"ts_utc": "2026-08-21T00:00:00+00:00"}, out)
    rows = list(csv.DictReader(out.open()))
    assert list(rows[0].keys()) == record_oi.FIELDS
    assert rows[0]["btc_usd"] == "" and rows[1]["btc_usd"] == "2"
    assert len(rows) == 2
