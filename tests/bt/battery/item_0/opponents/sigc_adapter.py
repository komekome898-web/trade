"""Survey candidate 107 `sigc` (GitHub `Skelf-Research/sigc`, commit aa5f616f),
built here with cargo (install record `survey_results/attempts/107.log`); the
`sigc` binary sits in the venv `c107`'s `bin/`.

What the tool is: a compiler and runner for a signal language over a daily
price panel (`data: prices: load csv from "..."`, `signal ...: emit ...`,
`portfolio ...: weights = ... ; costs = tc.bps(..) + slippage.model(..) ;
backtest from .. to ..`). The whole panel is computed at once; there is no
per-event strategy call, no event types other than the price panel, no
orders, cancels, notices, clock, latency or account to hand in. Each scene is
answered with a real run of the tool on a small synthetic panel written for
that scene (two assets, three days) and the tool's own output.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "adapters"))

from _vector_base import VectorBase  # noqa: E402
from protocol import not_supported  # noqa: E402

EXE = str(Path(sys.prefix) / "bin" / "sigc")
# the shape of the tool's own example examples/realdata.sig, on a synthetic two-asset panel
SIG = ('data:\n  prices: load csv from "p.csv"\n\nparams:\n  lookback = 1\n\nsignal momentum:\n  returns = ret(prices, lookback)\n'
       '  score = zscore(returns)\n  emit winsor(score, p=0.01)\n\nportfolio main:\n  weights = rank(momentum).long_short(top=0.5, bottom=0.5)\n'
       '{costs}  backtest from 2024-01-01 to 2024-12-31\n')


def run_sig(dates: list[str], costs: str = "") -> str:
    with tempfile.TemporaryDirectory(dir=os.environ.get("BT_SCRATCH") or None) as d:
        rows = ["date,X,Y"] + [f"{t},{100.0 + i:.1f},{100.0 - i:.1f}" for i, t in enumerate(dates)]
        Path(d, "p.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")
        Path(d, "s.sig").write_text(SIG.format(costs=costs), encoding="utf-8")
        r = subprocess.run([EXE, "run", "s.sig"], cwd=d, capture_output=True, text=True, timeout=120,
                           env={**os.environ, "NO_COLOR": "1", "RUST_LOG": "error"})
        text = (r.stdout + r.stderr).replace("\x1b", "")
        import re
        text = re.sub(r"\[[0-9;]*m", "", text)
        text = re.sub(r"\d{4}-\d\d-\d\dT[\d:.]+Z", "<ts>", text)  # the runner's own log time stamps
        lines = [ln.strip() for ln in text.splitlines() if ln.strip() and "INFO" not in ln]
        return f"sigc run(rc={r.returncode}) -> " + " | ".join(lines)[-500:]


class SigcAdapter(VectorBase):
    name = "opp_sigc"
    what = ("sigc は日次の価格の表(列 = 銘柄、行 = 日付)に信号の式を当てて重みを出し、表全体で損益を計算する形で、事象ごとに戦略を呼ぶ口・"
            "約定・板・資金調達・清算・時計・通知の型・発注と取消の口・約定と遅延の模型・口座を渡す口が無い"
            "(費用は portfolio の costs = tc.bps(..) + slippage.model(..) の率と模型の名前)")
    _out = None

    def attempt(self, scene_id: str) -> str:
        if self._out is None:
            type(self)._out = run_sig(["2024-01-02", "2024-01-03", "2024-01-04"])
        return self._out

    def _iso(self, sc):
        return not_supported("時刻は価格の表の日付の列だけで、戦略に時刻を渡す口も、読んだ時刻を返す出力も無い"
                             "(ナノ秒の ISO の日付も検めずに読んで走る)。試したこと: 日付の列の 1 行目に "
                             f"'{sc.input['iso']}' を入れた表 -> " + run_sig([sc.input["iso"], "2024-01-02", "2024-01-03"]))

    scene_p2_iso_utc = scene_p2_iso_offset = _iso

    def _cost(self, sc):
        return not_supported("費用は costs = tc.bps(率) + slippage.model(名前, coef) で、約定 1 件の定額や数量あたりの額を渡す口が無い"
                             "(注文と約定の数量を持たない)。試したこと: costs = tc.bps(5) を入れた走り -> "
                             + run_sig(["2024-01-02", "2024-01-03", "2024-01-04"], costs="  costs = tc.bps(5)\n"))

    scene_p7_cost_model_swap = scene_p7_cost_per_unit = _cost
