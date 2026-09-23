"""Survey candidate 12 `pybotters` (PyPI `pybotters` 1.11.2), run in its own venv.

pybotters is an exchange API client with DataStores that apply websocket
messages; it has no backtest engine (no simulated time, orders or fills).
What can be run offline is its bitFlyer DataStore: messages are handed to
`bitFlyerDataStore.onmessage(msg)` and a consumer receives typed changes
through `store.<name>.watch()` (StoreStream of StoreChange). That path is
used for the event-type scenes; every other scene is answered by a real call
showing the missing part.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "adapters"))

import datetime as D  # noqa: E402

from _vector_base import VectorBase  # noqa: E402
from protocol import not_supported, ok  # noqa: E402
import common as C  # noqa: E402

import pybotters  # noqa: E402

CH = "FX_BTC_JPY"


def _exec_date(ns: int) -> str:
    d = C.ns_to_dt(ns)
    frac = (int(ns) % 1_000_000_000) // 100  # bitFlyer exec_date carries 7 fractional digits (100 ns)
    return d.strftime("%Y-%m-%dT%H:%M:%S") + f".{frac:07d}Z"


def _parse_exec_date(s: str) -> int:
    base, frac = s.rstrip("Z").split(".")
    d = D.datetime.strptime(base, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=D.timezone.utc)
    return C.dt_to_ns(d) + int(frac.ljust(9, "0")[:9])


def _msg(channel: str, message):
    return {"jsonrpc": "2.0", "method": "channelMessage", "params": {"channel": channel, "message": message}}


def _feed(msgs, store_names):
    s = pybotters.bitFlyerDataStore()
    got = []

    async def main():
        async def consume(name):
            with getattr(s, name).watch() as stream:
                async for ch in stream:
                    got.append((name, ch.operation, dict(ch.data)))

        tasks = [asyncio.create_task(consume(n)) for n in store_names]
        await asyncio.sleep(0)
        for m in msgs:
            s.onmessage(m, None)
            await asyncio.sleep(0)
        await asyncio.sleep(0.01)
        for t in tasks:
            t.cancel()

    asyncio.run(main())
    return s, got


class PybottersAdapter(VectorBase):
    name = "opp_pybotters"
    what = "pybotters は取引所の API の窓口と、websocket の文を当てる DataStore で、模擬の時刻・注文・約定を持つバックテストの機関が無い"

    def attempt(self, scene_id: str) -> str:
        names = [n for n in dir(pybotters) if "back" in n.lower() or "sim" in n.lower() or "engine" in n.lower()]
        try:
            pybotters.Backtest  # type: ignore[attr-defined]  # noqa: B018
            r = "見つかった"
        except AttributeError as exc:
            r = f"AttributeError: {exc}"
        return f"pybotters.Backtest -> {r}。公開の名前で backtest/sim/engine を含むもの: {names}"

    def scene_p3_trade(self, sc):
        e = C.events(sc)[0]
        m = _msg(f"lightning_executions_{CH}", [{"id": 1, "side": e["side"].upper(), "price": e["price"], "size": e["qty"],
                                                 "exec_date": _exec_date(e["ts_ns"]), "buy_child_order_acceptance_id": "a",
                                                 "sell_child_order_acceptance_id": "b"}])
        _, got = _feed([m], ["executions"])
        seq = [["trade", _parse_exec_date(g[2]["exec_date"])] for g in got]
        f = {"price": got[0][2]["price"], "qty": got[0][2]["size"], "side": got[0][2]["side"].lower()} if got else {}
        return ok({"sequence": seq, "fields": f}, "bitFlyer の約定の文を bitFlyerDataStore.onmessage に渡し、executions.watch() で受けた変化。"
                  f"時刻は文の exec_date(小数 7 桁、100 ns 刻み)を ns に直した。受けた変化: {got}")

    def _board(self, sc, snapshot: bool):
        e = C.events(sc)[0]
        if snapshot:
            m = _msg(f"lightning_board_snapshot_{CH}", {"mid_price": 5012250.0,
                     "bids": [{"price": p, "size": q} for p, q in e["bids"]], "asks": [{"price": p, "size": q} for p, q in e["asks"]]})
        else:
            m = _msg(f"lightning_board_{CH}", {"mid_price": 5012250.0,
                     "bids": [{"price": e["price"], "size": e["qty"]}] if e["side"] == "bid" else [],
                     "asks": [{"price": e["price"], "size": e["qty"]}] if e["side"] == "ask" else []})
        s, got = _feed([m], ["board"])
        return not_supported("板の文は、websocket の接続(ClientWebSocketResponse)から来たときだけ写真として受け、差分は写真のあとだけ当てる"
                             "(models/bitflyer.py 69-87)。接続なしで渡すと板に何も入らない。"
                             f"試したこと: onmessage(板の{'写真' if snapshot else '差分'}の文, None) -> board.watch() の変化 {got}、board.sorted() {s.board.sorted()}")

    def scene_p3_book_snapshot(self, sc):
        return self._board(sc, True)

    def scene_p3_book_delta(self, sc):
        return self._board(sc, False)
