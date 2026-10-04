"""dC − dT の区間の読み方の決まり(`scripts/w4_measure/c2_read_r2_ct.py` の CT1〜CT3)を表を見る前に固める。"""
from __future__ import annotations

import importlib.util
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "w4_measure"))
_spec = importlib.util.spec_from_file_location("c2_read_r2_ct", REPO / "scripts" / "w4_measure" / "c2_read_r2_ct.py")
ct = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ct)


def test_slice_from_drops_days_before_start():
    x = [1.0, 2.0, 3.0, 4.0]
    assert ct.slice_from(x, date(2018, 12, 30), date(2019, 1, 1)) == [3.0, 4.0]
    assert ct.slice_from(x, date(2019, 1, 2), date(2019, 1, 1)) == x


def test_late_from_is_2019():
    assert ct.LATE_FROM == date(2019, 1, 1)
