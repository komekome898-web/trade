"""Survey candidate 103 `IsaacCheng9/order-book-simulator` (commit a72e6258), run in
its own venv `c103` made with a Python 3.14 interpreter installed into the
scratchpad by uv (the package requires Python >= 3.14; install record
`survey_results/attempts/103.log`).

What the tool is: an exchange simulation service (FastAPI gateway, Kafka,
PostgreSQL, multicast of book deltas, a Streamlit UI) around a price-time
matching book `order_book_simulator.matching.order_book.OrderBook`
(`add_order(order) -> trades`, `cancel_order(id)`, `get_full_snapshot()`,
`DeltaBuffer` of incremental book deltas). It has no backtest loop: no
historical market events are replayed into it and no strategy is called per
event; orders come from clients (HTTP) or its random order generator. The
adapter calls the book directly (no network, no Kafka / database started).
"""
from __future__ import annotations

import sys
from pathlib import Path
from uuid import UUID

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "adapters"))

from _vector_base import VectorBase  # noqa: E402


def _run() -> str:
    try:
        import datetime as D
        from order_book_simulator.matching.order_book import OrderBook
        book = OrderBook(UUID(int=1), "X")
        t0 = D.datetime(2023, 11, 16, tzinfo=D.timezone.utc)
        t1 = book.add_order({"id": UUID(int=11), "side": "SELL", "order_type": "LIMIT", "price": 100.0, "quantity": 1, "created_at": t0})
        t2 = book.add_order({"id": UUID(int=12), "side": "BUY", "order_type": "MARKET", "price": None, "quantity": 1,
                             "created_at": t0 + D.timedelta(days=1)})
        snap = book.get_full_snapshot()
        return (f"OrderBook(stock_id, 'X').add_order(売り 指値 100 × 1) -> 約定 {len(t1)} 件; add_order(買い 成行 1) -> 約定 {len(t2)} 件"
                f"(値 {[str(t.get('price')) for t in t2]}、created_at は注文を受けた時刻で、板の中の時間優先に使う); get_full_snapshot() の鍵 {sorted(snap)[:6]}")
    except Exception as exc:  # noqa: BLE001 - the failure is the observation
        return f"OrderBook の呼び出し: {type(exc).__name__}: {str(exc)[:200]}"


class IsaaccengObsimAdapter(VectorBase):
    name = "opp_isaaccheng_obsim"
    what = ("order-book-simulator は取引所を模す仕事(利用者の注文を HTTP で受けて値段と時刻の優先で照合し、板の差分を配る)で、過去の相場の事象を流して"
            "戦略を事象ごとに呼ぶ検証の機関が無い(戦略が無いので、事象の型・時刻・時計・通知を戦略に渡す口も、約定・遅延・費用・口座を差し込む口も無い。"
            "板と約定は自分の照合の結果として持つ)")
    _out = None

    def attempt(self, scene_id: str) -> str:
        if self._out is None:
            type(self)._out = _run()
        return self._out
