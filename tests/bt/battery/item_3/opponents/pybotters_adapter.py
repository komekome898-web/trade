"""Survey candidate 12 for the item 3 battery: every request is tried and none has a mouth.

The venv is the one named in i3_targets.py (installed by an earlier item's scene-keeper;
its record is in that item's RUNNABILITY.tsv / logs).  For every request the adapter
raises NotExpressible with the fixed grep of opponents/gen_search.py over the tool's own
code (SEARCH.tsv) and, where that grep hits, why the hit is not a mouth (NO).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _i3_base import Base  # noqa: E402


class T(Base):
    name = "opp_pybotters"
    WHAT = "pybotters は取引所の HTTP / WebSocket の接続と DataStore。"
    NO: dict = {
        'cpcv': '当たりは同梱の sympy(_static_dependencies)',
        'block_bootstrap': '当たりは同梱の parsimonious',
        'run': '当たりは取引所の署名と同梱の構文解析器',
        'auto_repro': '当たりは署名の決定的な乱数(RFC 6979)と同梱の部品',
        'cost_breakdown': '当たりは取引所ごとの DataStore の資金調達の欄(models/*.py)で、与えた約定から費用の内訳を出す口ではない',
        'purpose': '当たりは同梱の構文解析器の地の文',
    }


TARGET = T()
