"""Survey candidate 20 VnPy in its TICK backtesting mode (see vnpy_common.py)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import vnpy_common as V  # noqa: E402


class Adapter:
    name = "opp_vnpy@tick"

    def run(self, inp):
        return V.run(inp, "TICK", "VnPy 4.4.0 / vnpy_ctastrategy 1.4.1(TICK の型)")


TARGET = Adapter()
