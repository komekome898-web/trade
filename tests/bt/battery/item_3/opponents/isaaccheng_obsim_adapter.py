"""Survey candidate 103 for the item 3 battery: every request is tried and none has a mouth.

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
    name = "opp_isaaccheng_obsim"
    WHAT = "候補 103 は注文の板の模擬器(照合・配信・Streamlit の画面)。"
    NO: dict = {
        'walk_forward': '当たりは注文の数の転がる窓(market_simulator_stats.py 8-16 行)で、学習と評価の窓ではない',
        'block_bootstrap': '当たりは Kafka の bootstrap servers(接続先の設定)',
        'auto_repro': '当たりは README の文だけ',
        'trade_metrics': '当たりは WebSocket の性能の測り(benchmarks/unit/websocket_benchmark.py)',
        'fill_metrics': '当たりは配信の取りこぼしの回復(gateway/routers/ws_router.py 21-31 行)',
        'dashboard': '画面は ui/streamlit_app.py の板と約定の表示(市場の模擬の監視)で、バックテストの実行の一覧・項目別タブを持たない。起こすには Kafka・DB の配信の系が要る',
    }


TARGET = T()
