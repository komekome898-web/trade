"""Survey candidate 12 `pybotters 1.11.2` (venv item_0/pybotters) for the item 4 battery -- a tool that cannot take this battery's inputs.

The adapter loads the tool in its venv (so the runner records that it runs) and answers every input with what was
looked for and not found:
- op bars: 取引所の API の client と DataStore だけで、バックテスト(模擬の時刻・注文・約定)の口を探したが無い(項目 0・1 の記録)
- op pipeline: paper や dry-run の模擬は道具の側に無い(REQUIREMENTS.md §3.2、SCAN の否定の記述)。ファイルを宣言で読む口・目的つきの書き出し・ダッシュボードも無い
- op metrics / split / reference / models: see _i4_base (METRICS / SPLIT below).
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from _i4_base import Base, NotExpressible  # noqa: E402

import pybotters  # noqa: F401,E402


class Light(Base):
    name = "opp_pybotters"
    TOOL = "pybotters 1.11.2"
    PIPELINE = "paper や dry-run の模擬は道具の側に無い(REQUIREMENTS.md §3.2、SCAN の否定の記述)。ファイルを宣言で読む口・目的つきの書き出し・ダッシュボードも無い"
    METRICS = "外から与えた決済ごとの損益と資産の列から 12 の指標を出す口を探したが無い"
    SPLIT = "行の割合で学習・検証・検証外に分ける口を探したが無い"

    def gate(self, inp):
        raise NotExpressible(f"{self.TOOL}: 取引所の API の client と DataStore だけで、バックテスト(模擬の時刻・注文・約定)の口を探したが無い(項目 0・1 の記録)")


TARGET = Light()
