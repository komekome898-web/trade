"""Item 3 battery: the common base of the survey-side adapters.

An adapter subclasses ``Base``, sets ``name`` (the target name in i3_targets.py),
implements ``op_<op>(inp)`` for the requests its tool has a mouth for, and puts
in ``NO`` the reason for the requests it has none for (what was looked for and
where).  A request with neither falls back to the tool's line in SEARCH.tsv
(the fixed grep of opponents/gen_search.py over the tool's own code).
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from i3_protocol import NotExpressible, Refused  # noqa: E402,F401

# the request ops -> the key of the grep in SEARCH.tsv
SEARCH_KEY = {
    "calendar_split": "calendar_split", "walk_forward": "walk_forward", "walk_forward_eval": "walk_forward",
    "purged_split": "purged_split", "cpcv": "cpcv", "cpcv_paths": "cpcv", "block_bootstrap": "block_bootstrap",
    "mde": "mde", "verdict": "mde", "dsr": "dsr", "dsr_returns": "dsr", "pbo": "pbo", "iter_ledger": "iter_ledger",
    "iter_dsr": "iter_ledger", "sealed_read": "sealed_read", "data_read": "sealed_read", "run": "run",
    "run_ids": "run", "auto_repro": "auto_repro", "trade_metrics": "trade_metrics",
    "fill_metrics": "fill_metrics", "markout": "markout", "cost_breakdown": "cost_breakdown",
    "exit_reasons": "exit_reasons", "drawdown": "drawdown", "dashboard": "dashboard", "wiring_test": "dashboard",
}


def search_line(target: str, op: str) -> str:
    key = SEARCH_KEY.get(op, op)
    try:
        with open(HERE / "SEARCH.tsv", encoding="utf-8") as fh:
            for row in csv.DictReader(fh, delimiter="\t"):
                if row["target"] == target and row["op"] == key:
                    hits = f"{row['n_files']} ファイル" + (f"({row['first_files']})" if row["n_files"] not in ("0", "-") else "")
                    return f"grep -rliE '{row['regex']}' {row['dir']} → {hits}"
    except OSError:
        pass
    return "(SEARCH.tsv に行が無い)"


class Base:
    name = "base"
    WHAT = ""     # one line: what the tool is and what it takes as input
    NO: dict = {}  # op -> why there is no mouth (when the grep has hits that are not a mouth)

    def run(self, inp: dict) -> dict:
        op = inp["op"]
        fn = getattr(self, "op_" + op, None)
        if fn is None:
            why = self.NO.get(op) or self.NO.get(SEARCH_KEY.get(op, op))
            if not why:
                why = "口が無い"
            raise NotExpressible(f"{op}: {why}。{self.WHAT} 探した方法: {search_line(self.name, op)}")
        return fn(inp)
