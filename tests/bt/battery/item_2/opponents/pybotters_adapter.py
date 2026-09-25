"""Survey candidate 12 `pybotters` (PyPI 1.11.2, venv item_0/pybotters; install record: item 0
survey_results/attempts/12.log) for the item 2 battery.

What the tool is: an exchange API client (signed HTTP / websocket) with DataStores that apply websocket messages.  It
has no backtest engine: no simulated time, no order matching, no fills, no latency model, no account simulation.
Sending orders needs an exchange account and keys, which this battery never uses (委任文 §4).  No scene of this
battery can be handed to it; each scene reads the tool's public names as what was tried.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from probe_base import ProbeAdapter  # noqa: E402

import pybotters  # noqa: E402  (the tool, in its venv)


class Adapter(ProbeAdapter):
    name = "opp_pybotters"
    tool = "pybotters 1.11.2"
    what = "取引所の API の client(署名つきの HTTP・websocket と DataStore)で、模擬の時刻・照合・約定・遅延・口座の模擬が無い"

    def probe(self):
        return f"pybotters の公開の名前: {[n for n in dir(pybotters) if not n.startswith('_')][:40]}"

    def why_not(self, inp):
        return "検証の機関が無い(注文は取引所の口座と鍵で本物の取引所へ送る口だけで、この場面集は鍵を使わない)"


TARGET = Adapter()
