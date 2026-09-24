"""Survey candidates 101, 102 and 104: C++ limit-order-book libraries, built
in this environment (install records `survey_results/attempts/101.log`,
`102.log`, `104.log`). Each runs under the python of its own venv
(`c101` / `c102` / `c104`): 101 and 104 are driven through a small C++
driver compiled against the library and put in that venv's `bin/`
(`c101_driver`, `c104_driver`; the driver sources are in the install
records), 102 through its own pybind11 module `lob_cpp` (built with the
repository's `LOB_BUILD_PYTHON` option).

  * 101 `akurkar07/OrderBook` (commit 5673f66a): `OrderBook::place_limit_order /
    place_market_order / cancel_order` returning `Fills`; `Order.timestamp` is
    `std::chrono::steady_clock::now()` at construction.
  * 102 `3yit/Limit-Order-Book-Simulator` (commit 8e5e9d24): `MatchingEngine::process /
    cancel / modify`, `OrderBook::add_order / cancel_order / snapshot`;
    `Order.timestamp` is a `high_resolution_clock::time_point` (a Python
    `datetime` through the binding); `Simulator` replays a CSV of order
    commands and its `simulate_latency` option sleeps in real time per event
    (`std::this_thread::sleep_for`, src/simulator.cpp) -- it is not bound to Python.
  * 104 `jxm35/LimitOrderBook-MatchingEngine` (commit b5984aac): only the price
    level queue (`Limit`, `OrderBookEntry`, `Order`) builds here; the matching
    core `OrderBook.cpp` needs spdlog, which this environment does not have
    (install record). Two substitute headers from the survey (SCAN run 17:
    `boost::optional` = `std::optional`, `fmt::format` = `std::format`) are used.

None of the three takes market data (trades, bars, book, funding,
liquidation) or calls a strategy per event; each scene is answered by a
real call into the library (the driver's output), except the time scenes of
102 where the library's own time type is used.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "adapters"))

from _vector_base import VectorBase  # noqa: E402
from protocol import not_supported, ok  # noqa: E402
import common as C  # noqa: E402


def _driver(name: str) -> str:
    exe = Path(sys.prefix) / "bin" / name
    try:
        r = subprocess.run([str(exe)], capture_output=True, text=True, timeout=60)
    except Exception as exc:  # noqa: BLE001
        return f"{exe.name} -> {type(exc).__name__}: {exc}"
    return f"{exe.name}(rc={r.returncode}) -> " + " | ".join(ln.strip() for ln in r.stdout.splitlines())[:600]


class Akurkar07OrderbookAdapter(VectorBase):
    name = "opp_akurkar07_orderbook"
    what = ("この道具は C++ の照合の機関(OrderBook の place_limit_order / place_market_order / cancel_order)だけで、相場の事象を受ける口・"
            "事象ごとに戦略を呼ぶ口・通知・時計・遅延・費用・口座が無く、注文の時刻は構築の瞬間の steady_clock")
    _out = None

    def attempt(self, scene_id: str) -> str:
        if self._out is None:
            type(self)._out = _driver("c101_driver")
        return self._out


class Jxm35LobAdapter(VectorBase):
    name = "opp_jxm35_lob"
    what = ("この道具のうちこの環境で構築できたのは価格の段の待ち行列(Limit・OrderBookEntry・Order)だけで、照合の核 OrderBook.cpp は "
            "spdlog が無く構築できない(導入の記録)。構築できた部分にも、相場の事象を受ける口・事象ごとに戦略を呼ぶ口・通知・時計・遅延・費用・口座が無い")
    _out = None

    def attempt(self, scene_id: str) -> str:
        if self._out is None:
            type(self)._out = _driver("c104_driver")
        return self._out


class ThreeyitLobAdapter(VectorBase):
    name = "opp_3yit_lob"
    what = ("この道具は C++ の照合の機関(MatchingEngine の process / cancel / modify)と、注文の命令の CSV を再生する Simulator で、"
            "相場の事象を受ける口・事象ごとに戦略を呼ぶ口・通知・時計・費用・口座が無い(Simulator の simulate_latency は "
            "実時間で sleep する設定で、Python に出ていない)")

    def attempt(self, scene_id: str) -> str:
        import lob_cpp as L
        me = L.MatchingEngine()
        sell = L.Order()
        sell.id, sell.side, sell.type, sell.price, sell.quantity = 1, L.Side.SELL, L.OrderType.LIMIT, 10000, 100
        r1 = me.process(sell)
        buy = L.Order()
        buy.id, buy.side, buy.type, buy.price, buy.quantity = 2, L.Side.BUY, L.OrderType.MARKET, 0, 1
        r2 = me.process(buy)
        return (f"MatchingEngine().process(売りの指値 100@10000) -> 約定 {len(r1.trades)}; process(買いの成行 1) -> "
                f"{[(t.price, t.quantity) for t in r2.trades]}; lob_cpp の公開の名前 {[n for n in dir(L) if not n.startswith('_')]}")

    def _obs(self, sc):
        import lob_cpp as L
        seen = []
        for e in C.events(sc):
            o = L.Order()
            o.timestamp = C.ns_to_dt(e["ts_ns"]).replace(tzinfo=None)
            back = o.timestamp
            seen.append(C.dt_to_ns(back.replace(tzinfo=C.ns_to_dt(0).tzinfo)))
        return ok({"observed_ts_ns": seen}, "Order.timestamp(C++ の high_resolution_clock::time_point。binding では datetime)に事象の時刻を入れて読み戻し、"
                  "ns にした(datetime はマイクロ秒まで。戦略に渡す口は無いので、道具が持つ値を読んだ)")

    scene_p2_event_time_exact = scene_p2_one_ns_apart = _obs
