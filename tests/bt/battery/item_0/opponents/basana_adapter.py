"""Opponent adapter: 候補1 Basana (PyPI `basana`, SCAN 6836/1680/1823/7176/7666行)。

**この周に新規で導入した**(2026-09-23、場面係)。旧版の `opponents/CONSIDERED.md` は
「言語がPythonでない(Go)」として未導入にしていたが、これは誤りだった -- `basana` は
PyPI配布のPython(asyncio)パッケージで(`pip show basana` の実測: Summary
"A Python async and event driven framework for algorithmic trading..."、
Home-page/Author は `gbeced/basana`)、`<scratchpad>/bt/venvs/item_0/basana/` へ
`pip install basana` で実際に導入できた(このファイルの `_scene_v1_*`/`_scene_v2_bar_*`
は、その実インストール済みパッケージを `basana.backtesting_dispatcher()` /
`FifoQueueEventSource` / `BarEvent` で実際に動かした結果)。
"""
from __future__ import annotations

import sys
from pathlib import Path

_ITEM0_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ITEM0_DIR))
sys.path.insert(0, str(_ITEM0_DIR / "adapters"))

from protocol import Adapter, SceneResult  # noqa: E402
from scenes import Scene  # noqa: E402
from opponents._common import walk_submodule_names  # noqa: E402

try:
    import asyncio
    import datetime
    from decimal import Decimal
    import inspect as _inspect
    import basana as _bs  # noqa: E402
    from basana.backtesting import exchange as _exchange  # noqa: E402
    _IMPORT_ERROR: Exception | None = None
    _ALL_SUBMODULES = walk_submodule_names(_bs)
    _EXCHANGE_SRC = _inspect.getsource(_exchange.Exchange)
except Exception as exc:  # noqa: BLE001
    _IMPORT_ERROR = exc
    _ALL_SUBMODULES = []
    _EXCHANGE_SRC = ""


_EVENT_KEYWORDS = {
    "fill": ["order", "fill"],
    "book_snapshot": ["orderbook", "order_book", "book"],
    "book_delta": ["orderbook", "order_book", "book"],
    "funding": ["funding"],
    "liquidation": ["liquidat"],
    "clock": ["clock"],
    "order_notice": ["order_mgr", "orders", "errors"],
}


def _run_bar_events(ts_ns_list: list[int]) -> list[datetime.datetime]:
    """Actually drive `ts_ns_list.len()` real `basana.BarEvent`s through a real
    `basana.backtesting_dispatcher()` + `FifoQueueEventSource`, and return the
    delivery-order sequence of `event.when` the subscribed handler observed
    (real asyncio run, not a static/source-only check -- see module docstring).
    """
    pair = _bs.Pair("BTC", "JPY")
    events = []
    for ts_ns in ts_ns_list:
        when = datetime.datetime.fromtimestamp(ts_ns / 1e9, tz=datetime.timezone.utc)
        bar = _bs.Bar(
            when, pair, Decimal("100.0"), Decimal("101.0"), Decimal("99.0"),
            Decimal("100.5"), Decimal("12.0"), datetime.timedelta(minutes=1),
        )
        events.append(_bs.BarEvent(when, bar))
    src = _bs.FifoQueueEventSource(events=events)
    dispatcher = _bs.backtesting_dispatcher()
    seen: list[datetime.datetime] = []

    async def handler(ev):
        seen.append(ev.when)

    dispatcher.subscribe(src, handler)
    asyncio.run(dispatcher.run())
    return seen


class BasanaAdapter(Adapter):
    name = "opp_basana"

    def run_scene(self, scene: Scene) -> SceneResult:
        if _IMPORT_ERROR is not None:
            return SceneResult("no_record", detail=f"import failed in this venv: {_IMPORT_ERROR}")
        handler = getattr(self, "_scene_" + scene.id.replace("-", "_"), None)
        if handler is None:
            return SceneResult("no_record", detail=f"no handler written for {scene.id} this round")
        try:
            return handler(scene)
        except Exception as exc:  # noqa: BLE001
            return SceneResult("error", detail=f"{type(exc).__name__}: {exc}")

    # v1 -----------------------------------------------------------------
    def _scene_v1_event_driven_cap(self, scene: Scene) -> SceneResult:
        bars = scene.input["events"]
        seen = _run_bar_events([b["ts_ns"] for b in bars])
        supported = len(seen) == len(bars)
        return SceneResult(
            "ok" if supported else "error",
            output={"event_driven": supported},
            detail=(
                f"実際に `basana.backtesting_dispatcher()` を作り、5件の `basana.BarEvent` を "
                f"`FifoQueueEventSource` に積んで `dispatcher.subscribe(src, handler); "
                f"asyncio.run(dispatcher.run())` を実行した(pip install basana した実物のvenv)。"
                f"async ハンドラが呼ばれた回数 = {len(seen)}(5件と一致={supported})。"
                f"型(BarEvent)を持つ事象をイベントディスパッチャで流す構造そのものを、"
                f"ソース読みではなく実行で確認した。"
            ),
        )

    def _scene_v1_event_driven_known(self, scene: Scene) -> SceneResult:
        bars = scene.input["events"]
        seen = _run_bar_events([b["ts_ns"] for b in bars])
        now_sequence = [round(dt.timestamp() * 1e9) for dt in seen]
        output = {"now_sequence": now_sequence}
        match = output == scene.expected
        return SceneResult(
            "ok" if match else "error",
            output=output,
            detail=(
                f"v1-event_driven-cap と同じ実行で、各 `BarEvent.when` を到着順に記録し "
                f"`round(dt.timestamp()*1e9)` で ts_ns に戻した列 = {now_sequence}。"
                f"既知解({scene.expected['now_sequence']})と{'一致' if match else '不一致'}。"
            ),
        )

    # v2 -------------------------------------------------------------
    def _scene_v2_bar_cap(self, scene: Scene) -> SceneResult:
        sample = scene.input["sample"]
        seen = _run_bar_events([sample["ts_ns"]])
        supported = len(seen) == 1
        return SceneResult(
            "ok" if supported else "not_supported",
            output={"supported": supported},
            detail=f"合成1件の足を実際に `BarEvent` で投入・配送できた(実行、supported={supported})。",
        )

    def _scene_v2_bar_known(self, scene: Scene) -> SceneResult:
        sample = scene.input["sample"]
        pair = _bs.Pair("BTC", "JPY")
        when = datetime.datetime.fromtimestamp(sample["ts_ns"] / 1e9, tz=datetime.timezone.utc)
        bar = _bs.Bar(
            when, pair, Decimal(str(sample["open"])), Decimal(str(sample["high"])),
            Decimal(str(sample["low"])), Decimal(str(sample["close"])),
            Decimal(str(sample["volume"])), datetime.timedelta(minutes=1),
        )
        src = _bs.FifoQueueEventSource(events=[_bs.BarEvent(when, bar)])
        dispatcher = _bs.backtesting_dispatcher()
        received = {}

        async def h(ev):
            received["ts_ns"] = round(ev.when.timestamp() * 1e9)
            received["open"] = float(ev.bar.open)
            received["high"] = float(ev.bar.high)
            received["low"] = float(ev.bar.low)
            received["close"] = float(ev.bar.close)
            received["volume"] = float(ev.bar.volume)

        dispatcher.subscribe(src, h)
        asyncio.run(dispatcher.run())
        match = received == scene.expected
        return SceneResult(
            "ok" if match else "error",
            output=received,
            detail=(
                f"実際に `basana.Bar`(open/high/low/close/volume を Decimal で保持)を1件投入し、"
                f"ハンドラが受け取った `event.bar` から読み戻した値 = {received}。"
                f"既知解({scene.expected})と{'一致' if match else '不一致'}。"
            ),
        )

    def _generic_v2_cap(self, scene: Scene, key: str) -> SceneResult:
        kws = _EVENT_KEYWORDS[key]
        hits = [n for n in _ALL_SUBMODULES if any(k in n.lower() for k in kws)]
        supported = len(hits) > 0
        return SceneResult(
            "ok" if supported else "not_supported",
            output={"supported": supported},
            detail=(
                f"pkgutil.walk_packages(basana) で得た {len(_ALL_SUBMODULES)} サブモジュールを"
                f"キーワード {kws} で実測フィルタ。当たり {len(hits)} 件: {hits[:5]}"
                f"{'...' if len(hits) > 5 else ''}。"
            ),
        )

    def _generic_v2_known(self, scene: Scene, key: str) -> SceneResult:
        return SceneResult(
            "no_record",
            detail=(
                f"{key} 型のモジュール存在は v2-{key}-cap で確認したが、合成1件を実際に投入して"
                f"往復させるには(v2-bar と異なり)取引所(`backtesting.exchange.Exchange`)の"
                f"ブートストラップが要り、この周では未実行(範囲: モジュール構造の走査のみ)。"
            ),
        )

    def _scene_v2_fill_cap(self, s): return self._generic_v2_cap(s, "fill")
    def _scene_v2_fill_known(self, s): return self._generic_v2_known(s, "fill")
    def _scene_v2_book_snapshot_cap(self, s): return self._generic_v2_cap(s, "book_snapshot")
    def _scene_v2_book_snapshot_known(self, s): return self._generic_v2_known(s, "book_snapshot")
    def _scene_v2_book_delta_cap(self, s): return self._generic_v2_cap(s, "book_delta")
    def _scene_v2_book_delta_known(self, s): return self._generic_v2_known(s, "book_delta")
    def _scene_v2_funding_cap(self, s): return self._generic_v2_cap(s, "funding")
    def _scene_v2_funding_known(self, s): return self._generic_v2_known(s, "funding")
    def _scene_v2_liquidation_cap(self, s): return self._generic_v2_cap(s, "liquidation")
    def _scene_v2_liquidation_known(self, s): return self._generic_v2_known(s, "liquidation")
    def _scene_v2_clock_cap(self, s): return self._generic_v2_cap(s, "clock")
    def _scene_v2_clock_known(self, s): return self._generic_v2_known(s, "clock")

    def _scene_v2_order_notice_cap(self, scene: Scene) -> SceneResult:
        has_rejected = "OrderRejected" in _EXCHANGE_SRC or "subscribe_to_order_events" in _EXCHANGE_SRC
        return SceneResult(
            "ok" if has_rejected else "not_supported",
            output={"supported": has_rejected},
            detail=(
                f"basana.backtesting.exchange.Exchange のソースを実測: "
                f"'subscribe_to_order_events' あり={'subscribe_to_order_events' in _EXCHANGE_SRC}。"
                f"合成1件の投入・配送はこの周は未実行(取引所のブートストラップが要る)。"
            ),
        )

    def _scene_v2_order_notice_known(self, scene: Scene) -> SceneResult:
        return self._generic_v2_known(scene, "order_notice")

    # v3 -------------------------------------------------------------
    def _scene_v3_precision_known(self, scene: Scene) -> SceneResult:
        return SceneResult(
            "no_record",
            detail=(
                "basana の `Bar.begin`/`BarEvent.when` は `datetime.datetime` で、Python の "
                "datetime はマイクロ秒止まり(basana自身のソースにナノ秒/int64の保持は無い、"
                "walk_submodule_names の実測でも 'nanosecond' 系の当たり無し)。既知解の"
                "ナノ秒精度往復はこの周は未実行(datetimeの型的な精度上限が既にv3-precision-capの"
                "答えを示唆するため優先度を下げた)。"
            ),
        )

    def _scene_v3_precision_cap(self, scene: Scene) -> SceneResult:
        a_ns = scene.input["event_a"]["ts_ns"]
        b_ns = scene.input["event_b"]["ts_ns"]
        a = datetime.datetime.fromtimestamp(a_ns / 1e9, tz=datetime.timezone.utc)
        b = datetime.datetime.fromtimestamp(b_ns / 1e9, tz=datetime.timezone.utc)
        distinguishable = a != b
        return SceneResult(
            "ok",
            output={"distinguishable": distinguishable},
            detail=(
                f"basana が事象の時刻に使う `datetime.datetime`(`BarEvent.when` の型)で "
                f"{a_ns} ns と {b_ns} ns(差 1ns)を構築し比較した実測: a={a!r}, b={b!r}, "
                f"distinguishable={distinguishable}(datetimeはマイクロ秒止まりのため、"
                f"1ナノ秒差は区別できない)。"
            ),
        )

    # v4 / v5 -- not attempted dynamically this round -----------------
    def _scene_v4_lookahead_known(self, scene: Scene) -> SceneResult:
        return SceneResult("no_record", detail="実行での確認には戦略側APIの組み立てが要り、この周では未実行。")

    def _scene_v4_lookahead_cap(self, scene: Scene) -> SceneResult:
        return SceneResult("no_record", detail="同上(未実行)。")

    def _scene_v5_order_known(self, scene: Scene) -> SceneResult:
        return SceneResult("no_record", detail="未実行(複数事象型の同時刻投入は取引所ブートストラップが要る)。")

    def _scene_v5_order_cap(self, scene: Scene) -> SceneResult:
        return SceneResult("no_record", detail="未実行。")

    # v6 -------------------------------------------------------------
    def _scene_v6_order_lifecycle_known(self, scene: Scene) -> SceneResult:
        return SceneResult(
            "no_record",
            detail="create_market_order/cancel_order の存在は v6-api_surface-cap で確認したが、実発注→取消の操作列はこの周では未実行(取引所のブートストラップが要る)。",
        )

    def _scene_v6_api_surface_cap(self, scene: Scene) -> SceneResult:
        names = ["create_market_order", "create_limit_order", "cancel_order"]
        present = {n: hasattr(_exchange.Exchange, n) for n in names}
        count = sum(present.values())
        return SceneResult(
            "ok",
            output={"count": count, **present},
            detail=f"basana.backtesting.exchange.Exchange を hasattr で実測: {present}。合計 {count}/3。",
        )

    # v7 -------------------------------------------------------------
    def _scene_v7_cost_swap_known(self, scene: Scene) -> SceneResult:
        return SceneResult(
            "no_record",
            detail=(
                "basana の手数料モデルは `basana.backtesting.fees` にあり(walk_submodule_names で"
                "実測確認済み)、取引所を構築せず単体で呼べる無手数料モデルの有無はこの周は未確認。"
            ),
        )

    def _scene_v7_extension_points_cap(self, scene: Scene) -> SceneResult:
        kws = {
            "cost": ["fees"],
            "latency": ["latency", "delay"],
            "fill_model": ["liquidity", "slippage"],
            "account": ["account_balances", "loan_mgr", "lending"],
        }
        present = {k: any(any(w in n.lower() for w in words) for n in _ALL_SUBMODULES) for k, words in kws.items()}
        count = sum(present.values())
        return SceneResult(
            "ok",
            output={"count": count, **present},
            detail=(
                f"サブモジュール名をキーワード走査した実測: {present}。合計 {count}/4。"
                f"うち fill_model(liquidity) は SCAN 7176/7666行で実行経路まで確認済み"
                f"(`order_mgr.py` の `liquidity_strategy.on_bar(...)`/`order.try_fill(bar, liquidity_strategy)`、"
                f"既定は「影響あり」側)。"
            ),
        )
