"""Survey candidate 20 VnPy in its BAR backtesting mode (see vnpy_common.py)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import vnpy_common as V  # noqa: E402


class Adapter:
    name = "opp_vnpy@bar"

    def run(self, inp):
        return V.run(inp, "BAR", "VnPy 4.4.0 / vnpy_ctastrategy 1.4.1(BAR の型)")


TARGET = Adapter()
