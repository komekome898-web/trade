"""Survey candidate 98 for the item 3 battery: every request is tried and none has a mouth.

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
    name = "opp_mihircoding_lob"
    WHAT = "候補 98 は価格・時間優先の照合の板(src/orderbook.py)と遅延の模擬(src/latency.py)とゼロ知能の注文流。"
    NO: dict = {
        'auto_repro': '当たりは INTERVIEW.md の文だけ。2 回回して比べる口が無い(遅延の模型の種で決定的に回せる = SCAN 9011・9148 行、というだけ)',
        'trade_metrics': '当たりは処理の時間の分位(benchmark.py 170 行 latency_percentiles)と文書で、往復の bp の分布・露出あたりの口ではない',
        'fill_metrics': '当たりは RESULTS.md の文だけ',
        'markout': 'latency_study.py の run(102 行)は自分の模擬の中で公正価格との差を数える研究の台本(121-151 行)で、与えた約定と仲値の列を渡す口が無い',
        'cost_breakdown': 'src/fees.py は 1 株あたりの maker / taker の額(36-43 行)で、率・スプレッド・資金調達の内訳を出す口が無い',
        'purpose': '当たりは simulator.py 95 行の「on purpose」など地の文',
    }


TARGET = T()
