"""前の日の荒れ具合の門の当て直しの読み方の決まり(`scripts/w4_measure/volgate_improved.py` の V1〜V5)を、表を見る前に固める。"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "w4_measure"))
_spec = importlib.util.spec_from_file_location("volgate_improved", REPO / "scripts" / "w4_measure" / "volgate_improved.py")
vg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vg)


def test_gate_avoids_classes_with_upper_bound_at_or_below_zero():
    pnl = {"d1": -10.0, "d2": 5.0, "d3": -4.0, "d4": 3.0}
    cls = {"d1": "low", "d2": "mid", "d3": "high"}  # d4 は区分なし(いつも入る)
    ci = {"low": (-10.0, -12.0, -1.0), "mid": (5.0, 1.0, 9.0), "high": (-4.0, -8.0, 0.0)}
    g = vg.gate(pnl, cls, ci)
    assert g["avoid"] == ["low", "high"]  # 上端ちょうど 0 も避ける
    assert abs(g["take"] - (14.0 / 4)) < 1e-12  # 避ける日の損の和 −14 を、区分なしを含む全 4 日で割る
    assert vg.gate(pnl, cls, {"low": (1.0, -1.0, 3.0)})["avoid"] == []
    assert vg.gate(pnl, cls, {"low": (1.0, -1.0, 3.0)})["take"] is None


def test_series_paths_exist():
    for _, d in vg.SERIES:
        assert os.path.isfile(os.path.join(d, "trades.json.gz")), d
        assert os.path.isfile(os.path.join(d, "summary.json")), d
