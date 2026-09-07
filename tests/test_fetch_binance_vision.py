"""Test for scripts/fetch_binance_vision.py's --kind aggTrades addition
(P2-08b, docs/PHASE2/P2-08b/PREREG.md). No network: exercises the pure
zip-parsing / normalization / daily-csv-writing path only. The pre-existing
--kind klines path is left untouched by that change and is not re-tested
here."""
from __future__ import annotations

import gzip
import io
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import fetch_binance_vision as m  # noqa: E402


def _make_zip(tmp_path: Path, name: str, csv_text: str) -> Path:
    zp = tmp_path / name
    with zipfile.ZipFile(zp, "w") as zf:
        zf.writestr(name.replace(".zip", ".csv"), csv_text)
    return zp


def test_parse_and_write_aggtrades_day_normalizes_ts_and_maker_flag(tmp_path):
    # spot-style row: 8 columns, is_best_match trailing, ts already microseconds (2026)
    spot_csv = (
        "1,66114.5,0.0001,10,10,1784764800092008,False,True\n"
        "2,66114.6,0.0002,11,12,1784764800164949,True,True\n"
    )
    # futures/um-style row: 7 columns (no is_best_match), header present, ts milliseconds
    fut_csv = (
        "agg_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker\n"
        "3,66082.0,0.168,20,20,1784764800435,false\n"
    )

    spot_zip = _make_zip(tmp_path, "BTCUSDT-aggTrades-2026-07-23.zip", spot_csv)
    fut_zip = _make_zip(tmp_path, "BTCUSDT-aggTrades-2026-07-24.zip", fut_csv)

    spot_rows = m.parse_aggtrades_zip(spot_zip)
    assert len(spot_rows) == 2  # header-less spot file: both data rows kept
    fut_rows = m.parse_aggtrades_zip(fut_zip)
    assert len(fut_rows) == 1  # header row skipped (non-numeric first field)

    out_csv = tmp_path / "out.csv.gz"
    n = m.write_aggtrades_day_csv(spot_rows + fut_rows, out_csv)
    assert n == 3

    with gzip.open(out_csv, "rt") as f:
        lines = f.read().splitlines()
    assert lines[0] == "agg_id,price,qty,first_id,last_id,ts_us,is_buyer_maker"
    # sorted by agg_id ascending
    assert [l.split(",")[0] for l in lines[1:]] == ["1", "2", "3"]
    # spot ts already microseconds -> passed through unchanged
    assert lines[1].split(",")[5] == "1784764800092008"
    # futures ts in milliseconds -> normalized to microseconds (*1000)
    assert lines[3].split(",")[5] == "1784764800435000"
    # is_buyer_maker lowercased regardless of source casing ("False"/"true")
    assert lines[1].split(",")[6] == "false"
    assert lines[3].split(",")[6] == "false"
    assert lines[2].split(",")[6] == "true"


def test_normalize_to_us_detects_ms_vs_us_by_magnitude():
    assert m.normalize_to_us(1784764800435) == 1784764800435000  # ms -> us
    assert m.normalize_to_us(1784764800092008) == 1784764800092008  # already us


def test_day_range_is_inclusive_both_ends():
    days = list(m.day_range("2026-07-23", "2026-07-25"))
    assert days == ["2026-07-23", "2026-07-24", "2026-07-25"]
