"""Survey candidate 107 `sigc` (Skelf-Research/sigc, commit aa5f616f, built with cargo in item 0's venv c107;
install record: tests/bt/battery/item_0/survey_results/attempts/107.log) for the item 3 battery.

What the tool is: a compiler and runner for a signal language over a DAILY price panel
(`sigc run <file.sig> [--trials N] [-o report]`; `sigc diff` compares two runs' reports).
It takes a .sig program and a parquet price panel; no request of this battery (row lists,
stated moments, trades, fills, a trade tape with market orders, a dashboard) can be handed
to it.  Every request makes a real call of the binary's help text as what was tried, and
names the nearest mouth the help shows.  The source clone was removed for disk by the lead
(the binary remains), so the grep of gen_search.py cannot be run on it.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _i3_base import NotExpressible  # noqa: E402

BIN = "/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/venvs/item_0/c107/bin/sigc"
NEAR = {
    "dsr": "`sigc run --trials N` が自分のバックテストの Sharpe を試行の数で縮める(help の逐語「Used to deflate the Sharpe ratio for multiple testing」)。"
           "述べた積率(SR・T・歪度・尖度・V)を渡す口は無い",
    "iter_dsr": "試行の数は --trials の引数で人が渡す。累積する台帳の口は無い",
    "auto_repro": "`sigc diff` は 2 つの実行の報告の差を示す(help「Show differences between two runs」)が、この要求の実行(約定の列への成行の往復)を sigc に渡せない",
    "walk_forward": "SCAN 6689・6918 行が名を挙げた walk_forward.rs は日足の表の上の信号の枠で、この要求の毎時の行を渡せない",
}


HELP_LOG = Path(__file__).resolve().parent / "attempts" / "i3_r1_scenekeeper_sigc_help.log"


class Sigc:
    name = "opp_sigc"

    def run(self, inp: dict) -> dict:
        op = inp["op"]
        if Path(BIN).exists():
            r = subprocess.run([BIN, "run", "--help"], capture_output=True, text=True, timeout=30)
            tried = f"sigc run --help → rc={r.returncode}、{r.stdout.strip().splitlines()[0] if r.stdout.strip() else r.stderr[:80]}"
        else:
            tried = ("実行ファイルは 2026-09-25 18:28 UTC のリードの容量の片付け(commit 08aaad4)で消えた。消える前に打った sigc --help と"
                     f" sigc run --help の出力(opponents/attempts/{HELP_LOG.name})で判断した")
        raise NotExpressible(f"{op}: {NEAR.get(op, '口が無い')}。sigc は .sig の信号の言語と日足の価格の表(parquet)だけを受け取る。試したこと: {tried}")


TARGET = Sigc()
