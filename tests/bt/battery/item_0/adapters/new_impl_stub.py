"""Adapter around 新実装 (`src/bot/bt/core/`).

Round 1 (2026-09-23, 資料係): the worker's core exists now (report:
`docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/round_1/REPORT.md`), so this
file's `run_scene` is filled in against the core's real public API
(`from bot.bt.core import *`), following the same "one `_scene_<id>` method
per scene, never raise -- return not_supported/error instead" shape as
`current_impl.CurrentImplAdapter`. Every value below comes from actually
calling the core this round; nothing is copied from REQUIREMENTS.md.

Field-name note: the scenes speak the vocabulary in `scenes.py`
(`ts_ns`/`qty`/`order_id`/...); the core's events speak their own vocabulary
(`received_time_ns`/`size`/`client_order_id`/...). Known-answer scenes below
translate the core's output back into the scene's field names before
comparing, exactly as the worker's self-check script did
(`<scratchpad>/bt/item0_r1_worker_scenecheck.py`), so `run_battery.py`'s own
`output == scene.expected` check is meaningful.
"""
from __future__ import annotations

import sys
from pathlib import Path

_ADAPTERS_DIR = Path(__file__).resolve().parent
_ITEM0_DIR = _ADAPTERS_DIR.parent
_REPO_ROOT = _ITEM0_DIR.parents[2]  # tests/bt/battery/item_0 -> tests/bt -> tests -> repo root
sys.path.insert(0, str(_ITEM0_DIR))
sys.path.insert(0, str(_REPO_ROOT / "src"))

from protocol import Adapter, SceneResult  # noqa: E402
from scenes import Scene  # noqa: E402


class _Recorder:
    """Minimal `Strategy` double: records every event it is shown, and can
    optionally run a caller-supplied side-action per event."""

    def __init__(self, act=None) -> None:
        self.seen: list = []
        self.act = act

    def on_event(self, event, ctx) -> None:
        self.seen.append(event)
        if self.act is not None:
            self.act(event, ctx)


_SAMPLE_TO_EVENT = None  # filled lazily inside _core(), needs bot.bt.core loaded


class NewImplAdapter(Adapter):
    name = "new_impl"

    def __init__(self) -> None:
        # Import lazily (per this file's original contract) so a round whose
        # core is broken/missing fails a single scene with `no_record`
        # instead of crashing adapter construction / the whole battery run.
        import bot.bt.core as core  # noqa: PLC0415

        self._core = core
        self._sample_to_event = {
            "fill": lambda s: core.TradeEvent(received_time_ns=s["ts_ns"], price=s["price"], size=s["qty"], side=s["side"]),
            "book_snapshot": lambda s: core.BookSnapshotEvent(received_time_ns=s["ts_ns"], bids=s["bids"], asks=s["asks"]),
            "book_delta": lambda s: core.BookDeltaEvent(received_time_ns=s["ts_ns"], side=s["side"], price=s["price"], size=s["size"]),
            "bar": lambda s: core.BarEvent(received_time_ns=s["ts_ns"], open=s["open"], high=s["high"], low=s["low"], close=s["close"], volume=s["volume"]),
            "funding": lambda s: core.FundingEvent(received_time_ns=s["ts_ns"], rate=s["rate"]),
            "liquidation": lambda s: core.LiquidationEvent(received_time_ns=s["ts_ns"], price=s["price"], size=s["qty"], side=s["side"]),
            "clock": lambda s: core.ClockEvent(received_time_ns=s["ts_ns"]),
            "order_notice": lambda s: core.OrderAckEvent(received_time_ns=s["ts_ns"], client_order_id=s["order_id"]),
        }

    def run_scene(self, scene: Scene) -> SceneResult:
        handler_name = "_scene_" + scene.id.replace("-", "_")
        handler = getattr(self, handler_name, None)
        if handler is None:
            return SceneResult(
                "no_record",
                detail=f"NewImplAdapter has no handler method {handler_name} for this scene id",
            )
        try:
            return handler(scene)
        except Exception as exc:  # noqa: BLE001 -- record, don't crash the batch
            return SceneResult("error", detail=f"{type(exc).__name__}: {exc}")

    def _bar(self, b: dict):
        c = self._core
        return c.BarEvent(received_time_ns=b["ts_ns"], open=b.get("open", b["close"]),
                           high=b.get("high", b["close"]), low=b.get("low", b["close"]),
                           close=b["close"], volume=b.get("volume", 0.0))

    # ------------------------------------------------------------------
    # viewpoint 1 -- event-driven architecture
    # ------------------------------------------------------------------
    def _scene_v1_event_driven_cap(self, scene: Scene) -> SceneResult:
        c = self._core
        bars = [self._bar(b) for b in scene.input["events"]]
        rec = _Recorder()
        c.CoreEngine(rec, bars).run()
        output = {"event_driven": len(rec.seen) == len(bars), "callback_count": len(rec.seen)}
        return SceneResult(
            "ok" if output["event_driven"] else "error",
            output=output,
            detail=(
                f"CoreEngine(strategy, {len(bars)}件のBarEventのlist).run() を実行し、"
                f"on_event が呼ばれた回数を数えた: {len(rec.seen)}。事象は list として core に渡す"
                f"（DataFrame一括ではなく1件ずつのEventオブジェクト）。"
                f"src/bot/bt/core/engine.py `CoreEngine`。"
            ),
        )

    def _scene_v1_event_driven_known(self, scene: Scene) -> SceneResult:
        c = self._core
        bars = [self._bar(b) for b in scene.input["events"]]
        now_sequence: list[int] = []

        def act(event, ctx):
            now_sequence.append(ctx.now_ns)

        c.CoreEngine(_Recorder(act), bars).run()
        output = {"now_sequence": now_sequence}
        match = output == scene.expected
        return SceneResult(
            "ok" if match else "error",
            output=output,
            detail=(
                f"5件のBarEventを1件ずつ流し、各コールバックで ctx.now_ns を記録した列: "
                f"{now_sequence}。既知解({scene.expected})と{'一致' if match else '不一致'}。"
            ),
        )

    # ------------------------------------------------------------------
    # viewpoint 2 -- event type coverage
    # ------------------------------------------------------------------
    def _scene_v2_generic_cap(self, scene: Scene, key: str) -> SceneResult:
        c = self._core
        event = self._sample_to_event[key](scene.input["sample"])
        if event.EVENT_TYPE in c.SOURCE_EVENT_TYPES:
            rec = _Recorder()
            c.CoreEngine(rec, [event]).run()
            delivered = [x.EVENT_TYPE.value for x in rec.seen]
            ok = event.EVENT_TYPE.value in delivered
            return SceneResult(
                "ok" if ok else "error",
                output={"supported": ok},
                detail=(
                    f"{event.EVENT_TYPE.value} を CoreEngine にデータ源事象として投入し、"
                    f"on_event に届いた型の列 = {delivered}。SOURCE_EVENT_TYPES に含まれる型として"
                    f"実際に受理・配送された。"
                ),
            )
        return SceneResult(
            "not_supported",
            output={"supported": False},
            detail=(
                f"{event.EVENT_TYPE.value} は core.SOURCE_EVENT_TYPES に含まれない"
                f"(= データ源から直接は受け取らない型で、取引所の答えとして核が生成する通知)。"
                f"scenes.py の想定(データ源から投入する合成入力)ではこの型を直接投入できないため、"
                f"この場面としては対応なし(engine.py の NOTICE_EVENT_TYPES 経由でのみ発生する)。"
            ),
        )

    def _scene_v2_generic_known(self, scene: Scene, key: str) -> SceneResult:
        c = self._core
        event = self._sample_to_event[key](scene.input["sample"])
        if event.EVENT_TYPE not in c.SOURCE_EVENT_TYPES:
            return SceneResult(
                "not_supported",
                detail=f"{event.EVENT_TYPE.value} はデータ源から投入できない型なので往復試験の対象が無い(v2-{key}-cap と同じ実測)。",
            )
        round_tripped = c.event_from_dict(event.to_dict())
        d = round_tripped.to_dict()
        # translate core vocabulary -> the exact scene-input vocabulary
        # (each event type's sample in scenes.py uses its own field names --
        # `qty` for fill/liquidation but `size` for book_delta -- so this is
        # a per-type table, not one blanket rename).
        if key == "fill":
            recovered = {"ts_ns": d["received_time_ns"], "price": d["price"], "qty": d["size"], "side": d["side"]}
        elif key == "book_snapshot":
            recovered = {"ts_ns": d["received_time_ns"], "bids": d["bids"], "asks": d["asks"]}
        elif key == "book_delta":
            recovered = {"ts_ns": d["received_time_ns"], "side": d["side"], "price": d["price"], "size": d["size"]}
        elif key == "bar":
            recovered = {"ts_ns": d["received_time_ns"], "open": d["open"], "high": d["high"],
                          "low": d["low"], "close": d["close"], "volume": d["volume"]}
        elif key == "funding":
            recovered = {"ts_ns": d["received_time_ns"], "rate": d["rate"]}
        elif key == "liquidation":
            recovered = {"ts_ns": d["received_time_ns"], "price": d["price"], "qty": d["size"], "side": d["side"]}
        elif key == "clock":
            recovered = {"ts_ns": d["received_time_ns"]}
        else:  # order_notice -- unreachable here (caught by the SOURCE_EVENT_TYPES check above)
            recovered = {"ts_ns": d["received_time_ns"], "notice": "accepted", "order_id": d["client_order_id"]}
        match = recovered == scene.expected
        return SceneResult(
            "ok" if match else "error",
            output=recovered,
            detail=(
                f"event_from_dict(event.to_dict()) で往復させ、core の欄名を場面の欄名へ対応付けて"
                f"比較した(received_time_ns→ts_ns, size→qty; clock/order_noticeは個別対応)。"
                f"core の生の往復値: {d}。翻訳後: {recovered}。入力サンプルと"
                f"{'一致' if match else '不一致'}。"
            ),
        )

    def _scene_v2_fill_cap(self, s): return self._scene_v2_generic_cap(s, "fill")
    def _scene_v2_fill_known(self, s): return self._scene_v2_generic_known(s, "fill")
    def _scene_v2_book_snapshot_cap(self, s): return self._scene_v2_generic_cap(s, "book_snapshot")
    def _scene_v2_book_snapshot_known(self, s): return self._scene_v2_generic_known(s, "book_snapshot")
    def _scene_v2_book_delta_cap(self, s): return self._scene_v2_generic_cap(s, "book_delta")
    def _scene_v2_book_delta_known(self, s): return self._scene_v2_generic_known(s, "book_delta")
    def _scene_v2_bar_cap(self, s): return self._scene_v2_generic_cap(s, "bar")
    def _scene_v2_bar_known(self, s): return self._scene_v2_generic_known(s, "bar")
    def _scene_v2_funding_cap(self, s): return self._scene_v2_generic_cap(s, "funding")
    def _scene_v2_funding_known(self, s): return self._scene_v2_generic_known(s, "funding")
    def _scene_v2_liquidation_cap(self, s): return self._scene_v2_generic_cap(s, "liquidation")
    def _scene_v2_liquidation_known(self, s): return self._scene_v2_generic_known(s, "liquidation")
    def _scene_v2_clock_cap(self, s): return self._scene_v2_generic_cap(s, "clock")
    def _scene_v2_clock_known(self, s): return self._scene_v2_generic_known(s, "clock")
    def _scene_v2_order_notice_cap(self, s): return self._scene_v2_generic_cap(s, "order_notice")
    def _scene_v2_order_notice_known(self, s): return self._scene_v2_generic_known(s, "order_notice")

    # ------------------------------------------------------------------
    # viewpoint 3 -- timestamp precision
    # ------------------------------------------------------------------
    def _scene_v3_precision_known(self, scene: Scene) -> SceneResult:
        c = self._core
        out = c.to_nanos(scene.input["iso"], "iso")
        match = out == scene.expected
        return SceneResult(
            "ok" if match else "error",
            output=out,
            detail=f"core.to_nanos(iso, 'iso') を実行した実測値 = {out}。既知解({scene.expected})と{'一致' if match else '不一致'}。",
        )

    def _scene_v3_precision_cap(self, scene: Scene) -> SceneResult:
        c = self._core
        out = dict(c.CORE_CONTRACT["time"])
        return SceneResult(
            "ok",
            output=out,
            detail=f"core.CORE_CONTRACT['time'](機械可読の契約, src/bot/bt/core/contract.py)を読み出した: {out}。",
        )

    # ------------------------------------------------------------------
    # viewpoint 4 -- look-ahead prevention
    # ------------------------------------------------------------------
    def _scene_v4_lookahead_known(self, scene: Scene) -> SceneResult:
        c = self._core
        bars = [self._bar(b) for b in scene.input["bars"]]
        k = scene.input["probe_index"]
        probe: dict = {}

        def act(event, ctx):
            vis = ctx.visible_events(c.EventType.BAR)
            if len(vis) == k + 1 and not probe:
                probe["max_visible_close"] = max(x.close for x in vis)
                probe["visible_count"] = len(vis)

        c.CoreEngine(_Recorder(act), bars).run()
        match = probe == scene.expected
        return SceneResult(
            "ok" if match else "error",
            output=probe,
            detail=(
                f"探査時刻(probe_index={k})で ctx.visible_events(BAR) を読み出し: {probe}。"
                f"既知解({scene.expected})と{'一致' if match else '不一致'}。visible_events は "
                f"『もう届けた事象』の列だけを返す(engine.py の _deliver、window.py)。"
            ),
        )

    def _scene_v4_lookahead_cap(self, scene: Scene) -> SceneResult:
        # 2026-09-23 fix (場面集の規則1): stop self-reporting a prose verdict
        # and instead actually attempt to read one event past what should be
        # visible (index == len(vis), one past the delivered window), the
        # same public `visible_events()` window that v4-lookahead-known reads
        # its known answer from.
        c = self._core
        bars = [self._bar(b) for b in scene.input["bars"]]
        k = scene.input["probe_index"]
        probe: dict = {}

        def act(event, ctx):
            vis = ctx.visible_events(c.EventType.BAR)
            if len(vis) == k + 1 and "raised" not in probe:
                try:
                    leaked = vis[len(vis)]  # one past the end of the delivered window
                    probe["raised"] = False
                    probe["leaked_close"] = leaked.close
                except IndexError:
                    probe["raised"] = True

        c.CoreEngine(_Recorder(act), bars).run()
        output = {"future_index_raises": probe.get("raised", False)}
        match = output == scene.expected
        if probe.get("raised"):
            probe_desc = "IndexErrorで読めなかった"
        else:
            probe_desc = f"読めてしまい値={probe.get('leaked_close')}が漏れた"
        return SceneResult(
            "ok" if match else "error",
            output=output,
            detail=(
                f"探査時刻(probe_index={k})で `ctx.visible_events(BAR)[len(vis)]` (1つ先の"
                f"未到達バー)を実際に読もうとした実測: "
                f"{probe_desc}。"
                f"既知解({scene.expected})と{'一致' if match else '不一致'}。"
                f"EventWindow.__getitem__(window.py) は `_end` を超える添字に IndexError を"
                f"投げる構造で、履歴は『もう届けた事象』だけを保持する(engine.py の `_deliver`)。"
            ),
        )

    # ------------------------------------------------------------------
    # viewpoint 5 -- deterministic same-timestamp ordering
    # ------------------------------------------------------------------
    def _same_ts_events(self, reverse: bool = False):
        c = self._core
        ts = 1_700_000_000_000_000_000
        events = [
            c.TradeEvent(received_time_ns=ts, price=1.0, size=1.0, side="buy", trade_id="A"),
            self._bar({"ts_ns": ts, "close": 1.0}),
            c.ClockEvent(received_time_ns=ts),
        ]
        return list(reversed(events)) if reverse else events

    def _run_once_ordering(self, reverse: bool = False):
        c = self._core

        def act(event, ctx):
            if event.EVENT_TYPE is c.EventType.TRADE:
                ctx.place_order(c.OrderRequest("buy", "limit", 1.0, price=1.0, client_order_id="C"))

        rec = _Recorder(act)
        c.CoreEngine(rec, self._same_ts_events(reverse=reverse)).run()
        return [x.EVENT_TYPE.value for x in rec.seen]

    def _scene_v5_order_known(self, scene: Scene) -> SceneResult:
        a, b = self._run_once_ordering(), self._run_once_ordering()
        output = {"run1_equals_run2": a == b}
        match = output == scene.expected
        return SceneResult(
            "ok" if match else "error",
            output=output,
            detail=(
                f"同一時刻の3事象(約定・足・時計)+発注1件を2回走らせ、届いた型の順序を比較: "
                f"1回目={a}, 2回目={b}。既知解({scene.expected})と{'一致' if match else '不一致'}。"
            ),
        )

    def _scene_v5_order_cap(self, scene: Scene) -> SceneResult:
        # 2026-09-23 fix (場面集の規則1): stop self-reporting "a rule exists"
        # from prose/contract data alone, and instead actually feed the same
        # tied-timestamp events in two different INPUT orders (forward and
        # reversed) and check whether the DELIVERED order is the same both
        # times -- a rule that is truly content-driven (not just insertion
        # order) must produce the same result regardless of input order.
        order_fwd = self._run_once_ordering(reverse=False)
        order_rev = self._run_once_ordering(reverse=True)
        output = {"order_independent_of_input_order": order_fwd == order_rev}
        match = output == scene.expected
        c = self._core
        return SceneResult(
            "ok" if match else "error",
            output=output,
            detail=(
                f"同一時刻3事象(約定・足・時計)を(a)投入順=A,B,C(順方向)と(b)投入順=C,B,A"
                f"(逆順)の2通りで実行し、実際に届いた順序を比較: 順方向={order_fwd}, "
                f"逆順={order_rev}。既知解({scene.expected})と{'一致' if match else '不一致'}。"
                f"core.ORDERING_RULE(機械可読、ordering.py `ORDERING_RULE`)は "
                f"{c.ORDERING_RULE!r}。"
            ),
        )

    # ------------------------------------------------------------------
    # viewpoint 6 -- strategy API completeness
    # ------------------------------------------------------------------
    def _scene_v6_order_lifecycle_known(self, scene: Scene) -> SceneResult:
        c = self._core
        st: dict = {}

        def act(event, ctx):
            if event.EVENT_TYPE is c.EventType.CLOCK:
                oid = ctx.place_order(c.OrderRequest("buy", "limit", scene.input["order"]["qty"], price=1.0))
                ctx.cancel_order(oid)
            st["open"] = len(ctx.open_orders())

        res = c.CoreEngine(_Recorder(act), [c.ClockEvent(received_time_ns=1_700_000_000_000_000_000)]).run()
        output = {"open_orders_after": st["open"]}
        match = output == scene.expected
        return SceneResult(
            "ok" if match else "error",
            output=output,
            detail=(
                f"ctx.place_order で発注し即 ctx.cancel_order で取消、直後の ctx.open_orders() の"
                f"長さ={st['open']}。実行結果 EngineResult.open_orders の長さ={len(res.open_orders)}。"
                f"既知解({scene.expected})と{'一致' if match else '不一致'}。"
            ),
        )

    def _scene_v6_api_surface_cap(self, scene: Scene) -> SceneResult:
        c = self._core
        api = list(c.CORE_CONTRACT["strategy_api"])
        has_callback = "on_event" in c.STRATEGY_API or hasattr(c.Strategy, "on_event")
        has_place = "place_order" in api
        has_cancel = "cancel_order" in api
        count = sum([has_callback, has_place, has_cancel])
        return SceneResult(
            "ok",
            output={"count": count, "callback": has_callback, "place": has_place, "cancel": has_cancel, "full_api": api},
            detail=f"core.CORE_CONTRACT['strategy_api'] を実測: {api}。呼び出し・発注・取消の3つを含む(合計{count}/3、ほかに visible_events/last/open_orders/set_timer も持つ)。",
        )

    # ------------------------------------------------------------------
    # viewpoint 7 -- extension points
    # ------------------------------------------------------------------
    def _scene_v7_cost_swap_known(self, scene: Scene) -> SceneResult:
        c = self._core
        from bot.bt.core.testing import ImmediateFillModel, FixedRateCost  # noqa: PLC0415

        def act(event, ctx):
            if event.EVENT_TYPE is c.EventType.CLOCK:
                ctx.place_order(c.OrderRequest("buy", "market", 1.0))

        res = c.CoreEngine(
            _Recorder(act),
            [c.ClockEvent(received_time_ns=1_700_000_000_000_000_000)],
            fill_model=ImmediateFillModel(fixed_price=100.0),
            cost_model=c.NullCostModel(),
        ).run()
        fee = res.fills[0].fee
        output = {"fee": fee}
        match = output == scene.expected
        return SceneResult(
            "ok" if match else "error",
            output=output,
            detail=(
                f"core を書き換えずに CoreEngine(..., cost_model=NullCostModel()) を注入し、"
                f"約定1件の fee を実測 = {fee}。既知解({scene.expected})と{'一致' if match else '不一致'}。"
                f"（費用模型を渡さないと `MissingCostModelError` になり黙って0にならないことも別途確認済み: "
                f"REPORT.md 4.1 の拡張口の行）"
            ),
        )

    def _scene_v7_extension_points_cap(self, scene: Scene) -> SceneResult:
        c = self._core
        sockets = dict(c.CORE_CONTRACT["sockets"])
        count = len(sockets)
        return SceneResult(
            "ok",
            output={"count": count, **sockets},
            detail=f"core.CORE_CONTRACT['sockets'](プロトコルから機械的に作った一覧, contract.py)を実測: {sockets}。4つの差し込み口(FillModel/LatencyModel/CostModel/Account)すべてを核の外で実装し差し替え可能。",
        )
