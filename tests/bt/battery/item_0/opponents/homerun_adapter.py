"""Survey candidate 91 `braedonsaunders/homerun` (commit 6cb8ea56), its backtester
package `backend/services/backtest` run in the venv `c91` (a `.pth` to
`backend/`; the package's transitive imports needed httpx, pydantic and
fastapi, nothing of the app's database or web server is started; install
record `survey_results/attempts/91.log`).

What the backtester is (engine.py docstring and `BacktestEngine.run`): a
prediction-market book replay. Inputs are `BookSnapshot`s (an L2 book at
`observed_at`, a `datetime`) from a book source with `iter_snapshots()` /
`snapshot_at()` (e.g. `InMemoryBookReplay`) and a list of `TradeIntent`s --
entries computed BEFORE the run by an upstream pipeline, drained by their
`emitted_at`. A strategy object is called only for positions it holds
(`should_exit`) and on fills / cancels (`on_fill`, `on_cancel`); it is not
called per event and cannot place entries during the run. Plug points in
`BacktestConfig`: `latency` (LatencyModel), `fees` (FeeModel), `impact`
(ImpactModel), `venue` (Venue: price rules; the default PolymarketVenue has
prices 0.01 .. 0.99), `fill_model_snapshot`, `portfolio` (PortfolioConfig).
"""
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "adapters"))

from _vector_base import VectorBase  # noqa: E402
from protocol import not_supported, ok  # noqa: E402
import common as C  # noqa: E402

from services.backtest.book_replay import BookSnapshot, InMemoryBookReplay, PriceLevel  # noqa: E402
from services.backtest.engine import BacktestConfig, BacktestEngine, TradeIntent  # noqa: E402
from services.backtest.latency_model import LatencyModel  # noqa: E402
from services.backtest.matching_engine import FeeModel  # noqa: E402

logging.disable(logging.CRITICAL)
TOK = "X"


def snap(ts_ns: int, price: float, qty: float) -> BookSnapshot:
    """A market trade (price, qty) as the book the tool reads: an ask of qty at price."""
    return BookSnapshot(TOK, C.ns_to_dt(ts_ns), bids=(PriceLevel(price - 1.0, qty),), asks=(PriceLevel(price, qty),),
                        trade_price=price, trade_size=qty)


class Recorder:
    def __init__(self):
        self.calls = []

    def should_exit(self, position, market_state):
        self.calls.append("should_exit")
        return None

    def on_fill(self, order, **kw):
        self.calls.append("on_fill")

    def on_cancel(self, order, **kw):
        self.calls.append("on_cancel")


def run(snaps, intents, **cfg):
    rec = Recorder()
    eng = BacktestEngine(config=BacktestConfig(**cfg), strategy=rec)
    res = asyncio.run(eng.run(book_source=InMemoryBookReplay(snaps), trade_intents=intents))
    return res, rec


def _attempt() -> str:
    t0 = 1_700_092_800_000_000_000
    res, rec = run([snap(t0 + k * 86_400_000_000_000, 100.0, 100.0) for k in range(3)], [])
    return (f"BacktestEngine(strategy=<記録する戦略>).run(book_source=InMemoryBookReplay(3 枚), trade_intents=[]) -> "
            f"戦略が呼ばれた回数 {len(rec.calls)}、約定 {res.total_fills}(建玉の無い戦略は事象ごとに呼ばれず、入りは走る前に作った TradeIntent だけ)")


def buy_intent(ts_ns: int, size: float, price: float = 100.0, tif: str = "IOC") -> TradeIntent:
    return TradeIntent(intent_id="mine", emitted_at=C.ns_to_dt(ts_ns), token_id=TOK, side="BUY", size=size, limit_price=price, tif=tif)


class HomerunAdapter(VectorBase):
    name = "opp_homerun"
    what = ("homerun の検証は板の写真(BookSnapshot)の列を再生し、入りの注文は走る前に作った TradeIntent の列から出す形で、戦略は建玉があるときの "
            "should_exit と約定・取消の知らせにしか呼ばれない。事象ごとに戦略を呼ぶ口・走っている間に戦略が発注する口・約定・足・資金調達・清算・時計の型が無い")
    _out = None

    def attempt(self, scene_id: str) -> str:
        if self._out is None:
            type(self)._out = _attempt()
        return self._out

    # ---------------- P0-2: the time type is datetime (microseconds)
    def _obs(self, sc):
        replay = InMemoryBookReplay([snap(int(e["ts_ns"]), 100.0, 1.0) for e in C.events(sc)])

        async def read():
            return [s.observed_at async for s in replay.iter_snapshots()]

        return ok({"observed_ts_ns": [C.dt_to_ns(t) for t in asyncio.run(read())]},
                  "BookSnapshot の observed_at は datetime(マイクロ秒まで)。事象の時刻を datetime にして InMemoryBookReplay に入れ、iter_snapshots が返した "
                  "observed_at を ns に(戦略に渡す口は無いので、再生の出す値を読んだ)")

    scene_p2_event_time_exact = scene_p2_one_ns_apart = _obs

    # ---------------- P0-3: the book snapshot type
    def scene_p3_book_snapshot(self, sc):
        e = C.events(sc)[0]
        s = BookSnapshot(TOK, C.ns_to_dt(e["ts_ns"]), bids=tuple(PriceLevel(p, q) for p, q in e["bids"]),
                         asks=tuple(PriceLevel(p, q) for p, q in e["asks"]))
        replay = InMemoryBookReplay([s])

        async def read():
            return [x async for x in replay.iter_snapshots()]

        got = asyncio.run(read())
        return ok({"sequence": [["book_snapshot", C.dt_to_ns(x.observed_at)] for x in got],
                   "fields": {"bids": [[lv.price, lv.size] for lv in got[0].bids], "asks": [[lv.price, lv.size] for lv in got[0].asks]} if got else {}},
                  "BookSnapshot を InMemoryBookReplay に入れ、iter_snapshots が返した写真(戦略に渡す口は無いので、再生の出す値を読んだ)")

    # ---------------- P0-7: the engine's plug points, the entry as a TradeIntent at the first event
    def _fill_run(self, sc, size: float = 1.0, **cfg):
        evs = C.events(sc)
        snaps = [snap(int(e["ts_ns"]), float(e["price"]), float(e["qty"])) for e in evs]
        res, rec = run(snaps, [buy_intent(int(evs[0]["ts_ns"]), size)], **cfg)
        return [f for f in res.fills if f.order_id == "mine"], res

    def scene_p7_latency_model_swap(self, sc):
        mine, res = self._fill_run(sc, latency=LatencyModel.deterministic(submit_ms=7.0, cancel_ms=0.001))
        if not mine and res.rejected_orders:
            return not_supported("場(Venue)が値 100 の注文を拒否した(既定の PolymarketVenue は値 0.01..0.99。場の規則は既定の守りなので外さない)。"
                                 f"試したこと: BacktestConfig(latency=LatencyModel.deterministic(submit_ms=7))、T0 に買い 1 の TradeIntent(IOC、指値 100) -> "
                                 f"約定 0、拒否 {res.rejected_orders}")
        return ok({"fill_time_ns": C.dt_to_ns(mine[0].occurred_at) if mine else None},
                  "BacktestConfig(latency=LatencyModel.deterministic(submit_ms=7))、T0 に買い 1 の TradeIntent(IOC、指値 100)。約定の occurred_at。"
                  f"約定 {[(f.price, f.size, str(f.occurred_at)) for f in mine]}、拒否 {res.rejected_orders}、取消 {res.cancelled_orders}(既定の場は値 0.01..0.99)")

    def _fee(self, sc, fees: FeeModel, size: float, what: str):
        mine, res = self._fill_run(sc, size=size, fees=fees)
        if not mine and res.rejected_orders:
            return not_supported("場(Venue)が値 100 の注文を拒否した(既定の PolymarketVenue は値 0.01..0.99。場の規則は既定の守りなので外さない)。"
                                 f"試したこと: BacktestConfig(fees={what})、T0 に買い {size} の TradeIntent(IOC、指値 100) -> 約定 0、拒否 {res.rejected_orders}")
        return ok({"fee": sum(f.fee_usd for f in mine) if mine else None},
                  f"BacktestConfig(fees={what})、T0 に買い {size} の TradeIntent(IOC、指値 100)。約定の fee_usd の合計。"
                  f"約定 {[(f.price, f.size, f.fee_usd) for f in mine]}、拒否 {res.rejected_orders}、取消 {res.cancelled_orders}(既定の場は値 0.01..0.99)")

    def scene_p7_cost_model_swap(self, sc):
        return self._fee(sc, FeeModel(per_fill_gas_usd=0.5), 1.0, "FeeModel(per_fill_gas_usd=0.5)(約定 1 件の定額の口)")

    def scene_p7_cost_per_unit(self, sc):
        return not_supported("数量あたりの額を渡す口が無い(FeeModel は率(bps)・約定 1 件の gas・Polymarket の取り手の曲線の設定で、fill_fee(price, size, ...) を"
                             "差し替える口は BacktestConfig に無い)。試したこと: "
                             + self._fee(sc, FeeModel(per_fill_gas_usd=0.0), 2.0, "FeeModel(per_fill_gas_usd=0)").detail)

    def scene_p7_fill_model_swap(self, sc):
        mine, res = self._fill_run(sc)
        return not_supported("埋まる値を決める模型を渡す口が無い(fill_model_snapshot は約定する確率の模型、ImpactModel は板の深さに応じた悪化の bp、"
                             f"値は板の値)。試したこと: 既定の設定で T0 に買い 1 -> 約定 {[(f.price, f.size) for f in mine]}、拒否 {res.rejected_orders}")

    def scene_p7_account_swap(self, sc):
        return not_supported("口座(Portfolio)は BacktestEngine が PortfolioConfig から作り、差し替える口が無い(BacktestConfig.portfolio は設定の値)")
