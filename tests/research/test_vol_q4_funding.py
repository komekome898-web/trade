"""問い 4(資金調達率)の読み方の決まり(`scripts/w4_measure/vol_q4_funding.py` の R1・R3・R4)を、表を見る前に固める。"""
from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "w4_measure"))
_spec = importlib.util.spec_from_file_location("vol_q4_funding", REPO / "scripts" / "w4_measure" / "vol_q4_funding.py")
q4 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(q4)


def _ms(y, m, d, h):
    return int(datetime(y, m, d, h, tzinfo=timezone.utc).timestamp() * 1000)


def test_daily_funding_is_jst_day_abs_and_signed_and_needs_two():
    rows = [(_ms(2021, 3, 1, 16), 0.0001),    # 日本時間 03-02 01:00
            (_ms(2021, 3, 2, 0), -0.0003),    # 03-02 09:00
            (_ms(2021, 3, 2, 8), 0.0002),     # 03-02 17:00
            (_ms(2021, 3, 2, 16), 0.0005)]    # 03-03 01:00(この日は 1 回だけ → 値なし)
    fa, fs = q4.daily_funding(rows)
    assert set(fa) == {"2021-03-02"}
    assert abs(fa["2021-03-02"] - 0.02) < 1e-11        # (0.01 + 0.03 + 0.02) / 3 %
    assert abs(fs["2021-03-02"] - 0.0) < 1e-11         # (0.01 − 0.03 + 0.02) / 3


def test_daily_funding_drops_after_last_day():
    rows = [(_ms(2023, 12, 17, 16), 0.0001), (_ms(2023, 12, 18, 0), 0.0001)]  # 日本時間 12-18
    fa, _ = q4.daily_funding(rows)
    assert fa == {}


def test_lagged_is_previous_day():
    assert q4.lagged({"2021-02-28": 1.0}) == {"2021-03-01": 1.0}


def test_spearman_and_residual():
    x = np.arange(10, dtype=float)
    assert abs(q4.spearman(x, x ** 3) - 1.0) < 1e-12
    assert abs(q4.spearman(x, -x) + 1.0) < 1e-12
    v1 = np.exp(np.arange(1, 11, dtype=float) / 5)
    v = v1 ** 2 * 3.0                                    # log v = log 3 + 2 log v1 → 残りは 0
    assert np.allclose(q4.residual_log(v, v1), 0.0, atol=1e-9)


def test_tercile_uses_previous_year_only():
    x = {f"2020-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}": float(i) for i in range(336)}
    x["2021-01-05"] = 1e9
    t = q4.tercile_by_prev_year(x)
    assert "2020-01-01" not in t                         # 2019 年が無いので 2020 年は分けない
    assert t["2021-01-05"] == "high"
