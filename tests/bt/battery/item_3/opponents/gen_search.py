#!/usr/bin/env python3
"""Item 3 battery: search every runnable survey tool's own code for the mouth of each request.

    python3 tests/bt/battery/item_3/opponents/gen_search.py > tests/bt/battery/item_3/opponents/SEARCH.tsv

For every (tool, op) it runs ``grep -rliE <regex>`` over the tool's own code
directory (not its dependencies) and records how many files hit and the first
few.  The adapters quote this table in their NotExpressible reasons; where a
hit exists but is not a usable mouth, the adapter says why in its own words.
The regexes are fixed here, before looking at any tool.
"""
from __future__ import annotations

import os
import subprocess
import sys

V = os.environ.get("I3_VENV_ROOT", "/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/venvs")
SP = "lib/python3.11/site-packages"
R = os.environ.get("I3_READ_ROOT", "/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/i3_r1_scenekeeper/read")

TOOLS = {  # target name -> (catalogue number, the tool's own code directory)
    "opp_homerun": ("91", f"{V}/item_2/src/c91/backend/services/backtest"),
    "opp_mlflow": ("-", f"{V}/item_3/mlflow/{SP}/mlflow"),
    "opp_freqtrade": ("75", f"{V}/item_3/freqtrade/{SP}/freqtrade"),
    "opp_pysystemtrade": ("3", f"{V}/item_1/_dl/c3"),
    "opp_luczinsritter": ("16", f"{V}/item_3/_dl/c16"),
    "opp_polymarket_fill": ("95", f"{V}/item_2/src/c95"),
    "opp_mihircoding_lob": ("98", f"{V}/item_2/src/c98"),
    "opp_isaaccheng_obsim": ("103", f"{V}/item_2/src/c103"),
    "opp_pybotters": ("12", f"{V}/item_0/pybotters/{SP}/pybotters"),
    # primary sources read without executing (委任文 §3 material (b)); shallow clones in the scratchpad
    "read_15": ("15", f"{R}/BacktestingCore"),
    "read_8": ("8", f"{R}/OpenTrader"),
    "read_88": ("88", f"{R}/tradesight"),
}

OPS_RE = {
    "calendar_split": r"train.?val|val_end|holdout|out.?of.?sample",
    "walk_forward": r"walk.?forward|rolling.?window|expanding.?window|fitting.?dates",
    "purged_split": r"purg(e|ing)|embargo",
    "cpcv": r"cpcv|combinatorial",
    "block_bootstrap": r"bootstrap",
    "mde": r"minimum.?detectable|\bmde\b|statistical.?power",
    "dsr": r"deflated",
    "pbo": r"\bpbo\b|backtest.?overfitting",
    "iter_ledger": r"n_trials|num_trials|trial.?count",
    "sealed_read": r"unseal|sealed",
    "run": r"run_id|sha256|git.?(sha|commit)|provenance",
    "auto_repro": r"reproducib|determinis",
    "trade_metrics": r"percentile|quantile|exposure|per.?hour",
    "fill_metrics": r"fill.?rate|fill.?ratio|missed",
    "markout": r"markout|mark.?out|adverse.?selection",
    "cost_breakdown": r"maker.?fee|taker.?fee|fee.?breakdown|funding",
    "exit_reasons": r"exit.?reason|close.?reason|sell.?reason",
    "drawdown": r"drawdown",
    "dashboard": r"dashboard|streamlit|http\.server|flask|fastapi",
    "purpose": r"dry.?run|paper|purpose",
    "prereg": r"pre.?regist|prereg",
    "cdn": r"cdn\.|<script src=.https?://",
}


def main() -> int:
    print("target\tcand\top\tregex\tdir\tn_files\tfirst_files")
    for name, (cand, d) in TOOLS.items():
        for op, rx in OPS_RE.items():
            if not os.path.isdir(d):
                print("\t".join([name, cand, op, rx, d, "-", "置き場が無い"]))
                continue
            r = subprocess.run(["grep", "-rliE", "--include=*.py", "--include=*.rs", "--include=*.ts",
                                "--include=*.tsx", "--include=*.md", "--include=*.html", rx, d], capture_output=True, text=True)
            files = [f[len(d) + 1:] for f in r.stdout.split()]
            files = [f for f in files if "/node_modules/" not in f and "/tests/" not in f and not f.startswith("tests/")]
            print("\t".join([name, cand, op, rx, d.replace(V, "<venvs>").replace(R, "<read>"), str(len(files)), " ".join(files[:4])]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
