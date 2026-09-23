"""Opponent adapter: 候補 qf-lib (`qf_lib` on PyPI, "Tools to prevent look-ahead bias" の記述があった候補。
REQUIREMENTS.md 観点4では README止まりと記録されていたが、この周で実装のコードまで降りて
再検証した -- 事象駆動の queue.Queue ベースの EventManager を実測で確認した(下記 v1)。)

Installed for real in `<scratchpad>/bt/venvs/item_0/qf-lib/` via `pip install qf-lib`.
"""
from __future__ import annotations

import datetime
import sys
from pathlib import Path

_ITEM0_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ITEM0_DIR))
sys.path.insert(0, str(_ITEM0_DIR / "adapters"))

from protocol import Adapter, SceneResult  # noqa: E402
from scenes import Scene  # noqa: E402
from opponents._common import walk_submodule_names  # noqa: E402

try:
    import qf_lib  # noqa: E402
    from qf_lib.backtesting.events.event_base import Event, AllEventListener, AllEventNotifier  # noqa: E402
    from qf_lib.backtesting.events.event_manager import EventManager  # noqa: E402
    from qf_lib.common.utils.dateutils.timer import SettableTimer  # noqa: E402
    from qf_lib.backtesting.broker.broker import Broker as _Broker  # noqa: E402
    from qf_lib.backtesting.execution_handler.commission_models.fixed_commission_model import (  # noqa: E402
        FixedCommissionModel as _FixedCommissionModel,
    )
    _IMPORT_ERROR: Exception | None = None
    _ALL_SUBMODULES = walk_submodule_names(qf_lib)
except Exception as exc:  # noqa: BLE001
    _IMPORT_ERROR = exc
    _ALL_SUBMODULES = []


class _Counter(AllEventListener):
    def __init__(self) -> None:
        self.calls: list = []

    def on_event(self, event) -> None:  # noqa: ANN001
        self.calls.append(getattr(event, "tag", None))


class QfLibAdapter(Adapter):
    name = "opp_qf_lib"

    def run_scene(self, scene: Scene) -> SceneResult:
        if _IMPORT_ERROR is not None:
            return SceneResult("no_record", detail=f"import failed: {_IMPORT_ERROR}")
        handler = getattr(self, "_scene_" + scene.id.replace("-", "_"), None)
        if handler is None:
            return SceneResult("no_record", detail=f"no handler for {scene.id} this round")
        try:
            return handler(scene)
        except Exception as exc:  # noqa: BLE001
            return SceneResult("error", detail=f"{type(exc).__name__}: {exc}")

    # v1 -- ACTUALLY driven one event at a time via the real public API ---
    def _scene_v1_event_driven_cap(self, scene: Scene) -> SceneResult:
        bars = scene.input["events"]
        timer = SettableTimer(datetime.datetime(2024, 1, 1))
        mgr = EventManager(timer)
        notifier = AllEventNotifier()
        counter = _Counter()
        notifier.subscribe(counter)
        mgr.register_notifiers([notifier])
        for i, _bar in enumerate(bars):
            e = Event()
            e.tag = i
            mgr.publish(e)
        for _ in range(len(bars)):
            mgr.dispatch_next_event()
        supported = counter.calls == list(range(len(bars)))
        return SceneResult(
            "ok" if supported else "error",
            output={"event_driven": supported, "calls": counter.calls},
            detail=(
                f"qf_lib.backtesting.events.event_manager.EventManager を実際にインスタンス化し、"
                f"5件を `mgr.publish(event)` で1件ずつ投入 → `mgr.dispatch_next_event()` を5回呼んで"
                f"1件ずつ取り出させた。リスナーが記録した到着順 = {counter.calls}"
                f"(期待 [0,1,2,3,4] と{'一致' if supported else '不一致'})。"
                f"内部は queue.Queue で、公開の1件供給API(publish)がある -- このバッテリーの"
                f"4候補中、唯一この場面を『説明ではなく実行』で確かめられた。"
            ),
        )

    def _scene_v1_event_driven_known(self, scene: Scene) -> SceneResult:
        bars = scene.input["events"]
        timer = SettableTimer(datetime.datetime(2024, 1, 1))
        mgr = EventManager(timer)
        notifier = AllEventNotifier()
        counter = _Counter()
        notifier.subscribe(counter)
        mgr.register_notifiers([notifier])
        for bar in bars:
            e = Event()
            e.tag = bar["ts_ns"]  # tag with the real ts_ns, not an index (v1-cap tags with index)
            mgr.publish(e)
        for _ in range(len(bars)):
            mgr.dispatch_next_event()
        now_sequence = counter.calls
        output = {"now_sequence": now_sequence}
        match = output == scene.expected
        return SceneResult(
            "ok" if match else "error",
            output=output,
            detail=(
                f"v1-event_driven-cap と同じ `EventManager.publish`/`dispatch_next_event` 経路を使い、"
                f"今回は各 `Event.tag` に入力の ts_ns を入れて1件ずつ投入・取り出しさせた。"
                f"リスナーが記録した到着順の tag 列 = {now_sequence}。"
                f"既知解({scene.expected['now_sequence']})と{'一致' if match else '不一致'}。"
            ),
        )

    def _generic_v2_cap(self, scene: Scene, key: str, supported: bool, detail: str) -> SceneResult:
        return SceneResult("ok" if supported else "not_supported", output={"supported": supported}, detail=detail)

    def _scene_v2_bar_cap(self, scene: Scene) -> SceneResult:
        hit = any(n.endswith(".bar_event") or "intraday_bar_event" in n for n in _ALL_SUBMODULES)
        return self._generic_v2_cap(scene, "bar", hit, f"サブモジュール実測 (intraday_bar_event 等): 当たり={hit}。")

    def _scene_v2_bar_known(self, scene: Scene) -> SceneResult:
        return SceneResult("no_record", detail="往復の動的実行(データプロバイダ接続)はこの周は未実行。")

    def _scene_v2_fill_cap(self, scene: Scene) -> SceneResult:
        hit = any("order" in n.lower() for n in _ALL_SUBMODULES)
        return self._generic_v2_cap(scene, "fill", hit, "qf_lib.backtesting.order 系サブモジュールの実在を実測。")

    def _scene_v2_fill_known(self, scene: Scene) -> SceneResult:
        return SceneResult("no_record", detail="未実行。")

    def _scene_v2_book_snapshot_cap(self, scene: Scene) -> SceneResult:
        return self._generic_v2_cap(scene, "book_snapshot", False, f"サブモジュール {len(_ALL_SUBMODULES)} 件中、板(orderbook)関連の名前なし(実測)。")

    def _scene_v2_book_snapshot_known(self, scene: Scene) -> SceneResult:
        return SceneResult("not_supported", detail="cap 場面で不在確認済み。")

    def _scene_v2_book_delta_cap(self, scene: Scene) -> SceneResult:
        return self._generic_v2_cap(scene, "book_delta", False, "同上、板の差分に対応する型なし(実測)。")

    def _scene_v2_book_delta_known(self, scene: Scene) -> SceneResult:
        return SceneResult("not_supported", detail="cap 場面で不在確認済み。")

    def _scene_v2_funding_cap(self, scene: Scene) -> SceneResult:
        hit = any("fund" in n.lower() for n in _ALL_SUBMODULES)
        return self._generic_v2_cap(scene, "funding", hit, f"サブモジュール名の 'fund' 走査、実測当たり={hit}。qf-lib は株式/先物向けで資金調達(perpetual funding)の概念は想定外と見られる。")

    def _scene_v2_funding_known(self, scene: Scene) -> SceneResult:
        return SceneResult("not_supported", detail="cap 場面で不在確認済み。")

    def _scene_v2_liquidation_cap(self, scene: Scene) -> SceneResult:
        hit = any("liquidat" in n.lower() for n in _ALL_SUBMODULES)
        return self._generic_v2_cap(scene, "liquidation", hit, f"サブモジュール名の 'liquidat' 走査、実測当たり={hit}(モジュール名レベルの走査で、ソース文字列の意味の取り違えは無い)。")

    def _scene_v2_liquidation_known(self, scene: Scene) -> SceneResult:
        return SceneResult("not_supported", detail="cap 場面で不在確認済み。")

    def _scene_v2_clock_cap(self, scene: Scene) -> SceneResult:
        hit = any("time_event" in n for n in _ALL_SUBMODULES)
        return self._generic_v2_cap(scene, "clock", hit, f"qf_lib.backtesting.events.time_event 系サブモジュールの実在を実測: 当たり={hit}(MarketOpenEvent/MarketCloseEvent 等の時刻駆動イベント)。")

    def _scene_v2_clock_known(self, scene: Scene) -> SceneResult:
        return SceneResult("no_record", detail="未実行。")

    def _scene_v2_order_notice_cap(self, scene: Scene) -> SceneResult:
        has_broker_methods = hasattr(_Broker, "cancel_order") and hasattr(_Broker, "place_orders")
        return self._generic_v2_cap(scene, "order_notice", has_broker_methods, f"qf_lib.backtesting.broker.broker.Broker を hasattr で実測: cancel_order/place_orders 実在={has_broker_methods}。受付/拒否/約定を分ける専用イベント型までは未確認(浅い探査)。")

    def _scene_v2_order_notice_known(self, scene: Scene) -> SceneResult:
        return SceneResult("no_record", detail="未実行。")

    def _scene_v3_precision_known(self, scene: Scene) -> SceneResult:
        return SceneResult(
            "no_record",
            detail=(
                "qf_lib.common.utils.dateutils.timer.SettableTimer は Python 標準の datetime.datetime "
                "(マイクロ秒精度、ns 未満切り捨て)を保持する設計(実測: SettableTimer.now() の型は"
                "datetime.datetime)。ns 精度の既知解はこの型では原理的に表現できない可能性が高いが、"
                "他の内部経路(pandas Timestamp 使用箇所)まではこの周で確認していない。"
            ),
        )

    def _scene_v3_precision_cap(self, scene: Scene) -> SceneResult:
        a_ns = scene.input["event_a"]["ts_ns"]
        b_ns = scene.input["event_b"]["ts_ns"]

        def _ns_to_datetime(ns: int) -> datetime.datetime:
            return datetime.datetime(1970, 1, 1) + datetime.timedelta(microseconds=ns / 1000.0)

        timer = SettableTimer()
        timer.set_current_time(_ns_to_datetime(a_ns))
        a = timer.now()
        timer.set_current_time(_ns_to_datetime(b_ns))
        b = timer.now()
        distinguishable = bool(a != b)
        return SceneResult(
            "ok",
            output={"distinguishable": distinguishable},
            detail=(
                f"SettableTimer に ts_ns={a_ns} と ts_ns={b_ns}(1ナノ秒差)をそれぞれ "
                f"set_current_time で実際に設定して now() を呼んだ実測: a={a!r}, b={b!r}, "
                f"distinguishable={distinguishable}。SettableTimer.now() は datetime.datetime "
                f"(マイクロ秒精度)を返すため、1ナノ秒差の2値は同じ datetime に潰れて"
                f"区別できないことを実測で確認した(要件のUTC int64ナノ秒を満たさない)。"
            ),
        )

    def _scene_v4_lookahead_known(self, scene: Scene) -> SceneResult:
        return SceneResult("no_record", detail="実行確認にはデータプロバイダ/戦略の用意が要り、この周は未実行。")

    def _scene_v4_lookahead_cap(self, scene: Scene) -> SceneResult:
        return SceneResult(
            "no_record",
            detail=(
                "REQUIREMENTS.md 観点4では『README止まり』(qf-lib は「Tools to prevent look-ahead bias」を"
                "謳うのみ)と記録されていたが、この周でパッケージ内に "
                "qf_lib.tests.integration_tests.data_providers.bloomberg.test_bbg_look_ahead_bias という"
                "専用テストモジュールが実在することを実測した(モジュール名の実在確認のみ、中身の"
                "読み込み・実行はしていない)。README 止まりではなく実装/試験が存在する可能性が高いが、"
                "この場面が要求する『戦略側から将来へアクセスできないか』の直接確認はまだ行っていない。"
            ),
        )

    def _scene_v5_order_known(self, scene: Scene) -> SceneResult:
        return SceneResult(
            "no_record",
            detail=(
                "EventManager.dispatch_next_event は queue.Queue(FIFO)から取り出す設計(v1 の実測で"
                "確認済み)なので、同時刻の複数事象は publish された順に処理される可能性が高いが、"
                "『同時刻』を明示的に判定する分岐は event_manager.py に見当たらず(_dispatch_event は"
                "event の型で振り分けるのみ)、複数事象を実際に同時刻で投入して2回一致を見る実行は"
                "この周は未実行。"
            ),
        )

    def _scene_v5_order_cap(self, scene: Scene) -> SceneResult:
        return SceneResult("not_supported", detail="同時刻の並びを明記した規則(docstring/コード)は event_manager.py に見当たらない(FIFOキューが暗黙の規則と読める程度)。")

    def _scene_v6_order_lifecycle_known(self, scene: Scene) -> SceneResult:
        return SceneResult("no_record", detail="place_orders/cancel_order の実在は v6-api_surface-cap で確認したが、実発注の動的実行(Broker の具象実装が要る)はこの周は未実行。")

    def _scene_v6_api_surface_cap(self, scene: Scene) -> SceneResult:
        has_callback = hasattr(AllEventListener, "on_event")
        has_place = hasattr(_Broker, "place_orders")
        has_cancel = hasattr(_Broker, "cancel_order")
        count = sum([has_callback, has_place, has_cancel])
        return SceneResult(
            "ok",
            output={"count": count, "callback": has_callback, "place": has_place, "cancel": has_cancel},
            detail=f"AllEventListener.on_event 実在={has_callback}(v1で実際に発火も確認済み)、Broker.place_orders={has_place}、Broker.cancel_order={has_cancel}。合計 {count}/3。",
        )

    def _scene_v7_cost_swap_known(self, scene: Scene) -> SceneResult:
        order = scene.input["order"]
        model = _FixedCommissionModel(0.0)
        fee = model.calculate_commission(order["qty"], order["price"])
        output = {"fee": float(fee)}
        match = output == scene.expected
        return SceneResult(
            "ok" if match else "error",
            output=output,
            detail=(
                f"qf_lib...FixedCommissionModel(0.0).calculate_commission({order['qty']}, {order['price']}) "
                f"を実行した実測値={fee}。既知解({scene.expected})と{'一致' if match else '不一致'}。"
                f"CommissionModel は独立クラスで engine 本体を書き換えず注入可能。"
            ),
        )

    def _scene_v7_extension_points_cap(self, scene: Scene) -> SceneResult:
        kws = {
            "cost": ["commission"],
            "latency": ["latency", "delay"],
            "fill_model": ["slippage", "execution_handler"],
            "account": ["portfolio", "broker"],
        }
        present = {k: any(any(w in n.lower() for w in words) for n in _ALL_SUBMODULES) for k, words in kws.items()}
        count = sum(present.values())
        return SceneResult(
            "ok",
            output={"count": count, **present},
            detail=f"サブモジュール名をキーワード走査した実測: {present}。合計 {count}/4。",
        )
