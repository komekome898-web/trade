"""`load_diagnostic` is the only sanctioned path for封印外 diagnostic series."""
import gzip

import pytest

from bot.research.sealed import SealedDataError, load_diagnostic

ROWS = """ts_us,price
1750000000000000,100
1755000000000000,200
1756000000000000,300
"""


def _write(tmp_path):
    p = tmp_path / "diag.csv.gz"
    with gzip.open(p, "wt") as fh:
        fh.write(ROWS)
    return p


def test_drops_rows_at_or_after_cutoff(tmp_path):
    p = _write(tmp_path)
    # Rows are 2025-06-15T15:06:40Z, 2025-08-12T12:00:00Z, 2025-08-24T01:46:40Z.
    assert len(load_diagnostic(p, "2025-08-01")) == 1
    assert len(load_diagnostic(p, "2030-01-01")) == 3


def test_cutoff_is_exclusive_and_utc(tmp_path):
    p = _write(tmp_path)
    kept = load_diagnostic(p, "2025-08-12T12:00:00")
    assert list(kept["price"]) == [100]


def test_missing_time_column_raises(tmp_path):
    p = tmp_path / "no_ts.csv.gz"
    with gzip.open(p, "wt") as fh:
        fh.write("a,b\n1,2\n")
    with pytest.raises(SealedDataError):
        load_diagnostic(p, "2026-08-23")
