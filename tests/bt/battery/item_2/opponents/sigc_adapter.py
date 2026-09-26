"""Survey candidate 107 `sigc` (GitHub Skelf-Research/sigc, commit aa5f616f, built with cargo in item 0's venv c107;
install record: item 0 survey_results/attempts/107.log) for the item 2 battery.

What the tool is: a compiler and runner for a signal language over a daily price panel (`portfolio: weights = ...;
costs = tc.bps(..) + slippage.model(..); backtest from .. to ..`); the whole panel is computed at once from weights.
It takes no order (type, price, quantity, time), book, trade tape, latency, notice or account, so no scene of this
battery can be handed to it; each scene makes a real call of the binary (its help text) as what was tried.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from probe_base import ProbeAdapter  # noqa: E402

EXE = str(Path(sys.prefix) / "bin" / "sigc")


class Adapter(ProbeAdapter):
    name = "opp_sigc"
    tool = "sigc(aa5f616f)"
    what = "口は日足の価格の表の上の信号の言語(重み → 費用 tc.bps・slippage.model → 検証)で、注文・約定・遅延・口座の口が無い"

    def probe(self):
        r = subprocess.run([EXE, "--help"], capture_output=True, text=True, timeout=60)
        return f"sigc --help (rc={r.returncode}) -> " + " | ".join((r.stdout or r.stderr).split("\n"))[:400]

    def why_not(self, inp):
        return "注文(種類・値・数量・時刻)・板・約定の列を渡す口が無い(重みの表だけを受ける)"


TARGET = Adapter()
