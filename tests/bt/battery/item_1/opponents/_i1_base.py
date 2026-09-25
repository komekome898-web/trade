"""Shared shape of the item 1 survey adapters whose tool has no public way to
take (some) scenes: each op names what was looked for and where (the tool is
imported at module load, so a broken install shows as 「結果なし」 with the
import error rather than as a reason)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from i1_protocol import NotExpressible  # noqa: E402,F401


class ReasonTarget:
    name = "opp"
    reasons: dict = {}

    def run(self, inp: dict) -> dict:
        op = inp["op"]
        handler = getattr(self, "op_" + op, None)
        if handler is not None:
            return handler(inp)
        raise NotExpressible(self.reasons.get(op, f"未知の op {op}"))
