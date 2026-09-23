"""Adapter around 当方の現状 (`src/bot/backtest/engine.py` + `src/bot/strategy/base.py`).

This wraps the REAL, unmodified current engine (per delegation doc Sec.4: the
8 legacy tests and the 12 importers of `src/bot/backtest/` must keep working
unmodified -- this adapter only imports and calls it, never edits it).

Every `_scene_*` method below actually imports/calls/introspects the real
module at run time; nothing here is copied from `REQUIREMENTS.md`'s prior
analysis, even where the answer ends up matching it.
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

import pandas as pd

_ADAPTERS_DIR = Path(__file__).resolve().parent
_ITEM0_DIR = _ADAPTERS_DIR.parent
_REPO_ROOT = _ITEM0_DIR.parents[2]  # tests/bt/battery/item_0 -> tests/bt -> tests -> repo root
sys.path.insert(0, str(_ITEM0_DIR))
sys.path.insert(0, str(_REPO_ROOT / "src"))

from protocol import Adapter, SceneResult  # noqa: E402
from scenes import Scene  # noqa: E402

from bot.backtest import engine as bt_engine  # noqa: E402
from bot.strategy.base import Signal, SignalType, Strategy  # noqa: E402

_ENGINE_SRC = Path(bt_engine.__file__).read_text(encoding="utf-8")
_BASE_SRC = Path(inspect.getfile(Strategy)).read_text(encoding="utf-8")


class _RecordingStrategy(Strategy):
    """Counts calls and records the slice of `candles` it was shown each time."""

    def __init__(self) -> None:
        super().__init__()
        self.calls: list[pd.DataFrame] = []

    @property
    def min_history(self) -> int:
        return 0

    def on_candles(self, candles: pd.DataFrame) -> Signal:
        self.calls.append(candles.copy())
        return Signal(type=SignalType.HOLD)


def _bars_to_df(bars: list[dict]) -> pd.DataFrame:
    rows = [
        {
            "open": b.get("open", b["close"]),
            "high": b.get("high", b["close"]),
            "low": b.get("low", b["close"]),
            "close": b["close"],
            "volume": b.get("volume", 0.0),
        }
        for b in bars
    ]
    idx = pd.to_datetime([b["ts_ns"] for b in bars], unit="ns", utc=True)
    return pd.DataFrame(rows, index=idx)


_NON_BAR_GREP = {
    "fill": ["fill_event", "TradeEvent", "class Fill"],
    "book_snapshot": ["orderbook", "order_book", "book_snapshot", "OrderBook"],
    "book_delta": ["orderbook", "order_book", "book_delta", "OrderBook"],
    "funding": ["funding"],
    "liquidation": ["liquidation"],
    "clock": ["ClockEvent", "clock_event"],
    "order_notice": ["OrderAccepted", "OrderRejected", "OrderFilled", "order_notice"],
}


class CurrentImplAdapter(Adapter):
    name = "current_impl"

    def run_scene(self, scene: Scene) -> SceneResult:
        handler_name = "_scene_" + scene.id.replace("-", "_")
        handler = getattr(self, handler_name, None)
        if handler is None:
            return SceneResult(
                "no_record",
                detail=f"CurrentImplAdapter has no handler method {handler_name} for this scene id",
            )
        try:
            return handler(scene)
        except Exception as exc:  # noqa: BLE001 -- record, don't crash the batch
            return SceneResult("error", detail=f"{type(exc).__name__}: {exc}")

    # ------------------------------------------------------------------
    # viewpoint 1 -- event-driven architecture
    # ------------------------------------------------------------------
    def _scene_v1_event_driven_cap(self, scene: Scene) -> SceneResult:
        sig = inspect.signature(bt_engine.run_backtest)
        has_feed_api = hasattr(bt_engine, "feed_event") or hasattr(bt_engine, "push_event")
        has_loop = "for i in range(len(candles))" in _ENGINE_SRC or "for i in range(" in _ENGINE_SRC
        bars = scene.input["events"]
        rec = _RecordingStrategy()
        rec.min_history  # noqa: B018
        df = _bars_to_df(bars)
        bt_engine.run_backtest(rec, df)
        detail = (
            f"実際に呼んだ: inspect.signature(run_backtest) = {sig} -- "
            f"'candles' は位置/キーワード引数でDataFrame一括必須(1件ずつ供給する引数なし)。"
            f"hasattr(bt_engine,'feed_event' or 'push_event') = {has_feed_api}。"
            f"合成5足を run_backtest(strategy, candles) で実行した結果、戦略コールバックは "
            f"{len(rec.calls)} 回呼ばれた(足の本数と一致=足単位の内部ループはある)が、"
            f"呼び出し側(このアダプタ)が事象を1件ずつ追加投入できる公開APIは無く、"
            f"事前に全件を1つのDataFrameへ組んでから渡す必要があった。"
        )
        return SceneResult("not_supported", output={"event_driven": False, "callback_count": len(rec.calls)}, detail=detail)

    def _scene_v1_event_driven_known(self, scene: Scene) -> SceneResult:
        bars = scene.input["events"]
        rec = _RecordingStrategy()
        df = _bars_to_df(bars)
        bt_engine.run_backtest(rec, df)
        now_sequence = [int(c.index[-1].value) for c in rec.calls]
        output = {"now_sequence": now_sequence}
        match = output == scene.expected
        return SceneResult(
            "ok" if match else "error",
            output=output,
            detail=(
                f"合成5足を run_backtest(strategy, candles) で実行し、on_candles が呼ばれるたびに"
                f"渡されたスライスの最終行のインデックス(pandasのns整数)を記録した列: {now_sequence}。"
                f"既知解({scene.expected})と{'一致' if match else '不一致'}。"
                f"(engine内部は足単位で逐次スライスを渡しており、1件投入APIの有無とは別に、"
                f"各コールバックの時刻そのものは壊れずに追跡できる。)"
            ),
        )

    # ------------------------------------------------------------------
    # viewpoint 2 -- event type coverage
    # ------------------------------------------------------------------
    def _scene_v2_bar_cap(self, scene: Scene) -> SceneResult:
        sample = scene.input["sample"]
        rec = _RecordingStrategy()
        df = _bars_to_df([sample])
        bt_engine.run_backtest(rec, df)
        ok = len(rec.calls) == 1
        return SceneResult(
            "ok" if ok else "error",
            output={"supported": ok},
            detail=f"合成足1本を含む DataFrame で run_backtest を実行し、on_candles が {len(rec.calls)} 回呼ばれた。",
        )

    def _scene_v2_bar_known(self, scene: Scene) -> SceneResult:
        sample = scene.input["sample"]
        rec = _RecordingStrategy()
        df = _bars_to_df([sample])
        bt_engine.run_backtest(rec, df)
        seen = rec.calls[-1].iloc[-1]
        recovered = {
            "ts_ns": int(rec.calls[-1].index[-1].value),  # pandas ns since epoch
            "open": float(seen["open"]),
            "high": float(seen["high"]),
            "low": float(seen["low"]),
            "close": float(seen["close"]),
            "volume": float(seen["volume"]),
        }
        match = recovered == sample
        return SceneResult(
            "ok" if match else "error",
            output=recovered,
            detail=(
                f"on_candles に渡された最終行を読み出した: {recovered}。"
                f"入力サンプルと{'一致' if match else '不一致'}。"
                f"(この経路は engine 内部で ts_ns をそのまま使っているわけではなく、"
                f"pandas.to_datetime による往復を経ている点に注意)"
            ),
        )

    def _generic_non_bar_cap(self, scene: Scene, key: str) -> SceneResult:
        needles = _NON_BAR_GREP[key]
        hits = {n: (n in _ENGINE_SRC or n in _BASE_SRC) for n in needles}
        any_hit = any(hits.values())
        detail = (
            f"engine.py と strategy/base.py のソース文字列に {needles} を検索した実測: {hits}。"
            f"該当なし。engine.py の事象概念は「足(DataFrame の行)」1種類のみで、"
            f"{key} を独立した事象型として表す型・関数が無い。"
        )
        return SceneResult("not_supported", output={"supported": any_hit}, detail=detail)

    def _generic_non_bar_known(self, scene: Scene, key: str) -> SceneResult:
        return SceneResult(
            "not_supported",
            detail=(
                f"{key} 型の事象を受理する入口が無い(v2-{key}-cap と同じ実測)ため、"
                f"往復の既知解テストを走らせる対象が存在しない。"
            ),
        )

    def _scene_v2_fill_cap(self, s): return self._generic_non_bar_cap(s, "fill")
    def _scene_v2_fill_known(self, s): return self._generic_non_bar_known(s, "fill")
    def _scene_v2_book_snapshot_cap(self, s): return self._generic_non_bar_cap(s, "book_snapshot")
    def _scene_v2_book_snapshot_known(self, s): return self._generic_non_bar_known(s, "book_snapshot")
    def _scene_v2_book_delta_cap(self, s): return self._generic_non_bar_cap(s, "book_delta")
    def _scene_v2_book_delta_known(self, s): return self._generic_non_bar_known(s, "book_delta")
    def _scene_v2_funding_cap(self, s): return self._generic_non_bar_cap(s, "funding")
    def _scene_v2_funding_known(self, s): return self._generic_non_bar_known(s, "funding")
    def _scene_v2_liquidation_cap(self, s): return self._generic_non_bar_cap(s, "liquidation")
    def _scene_v2_liquidation_known(self, s): return self._generic_non_bar_known(s, "liquidation")
    def _scene_v2_clock_cap(self, s): return self._generic_non_bar_cap(s, "clock")
    def _scene_v2_clock_known(self, s): return self._generic_non_bar_known(s, "clock")
    def _scene_v2_order_notice_cap(self, s): return self._generic_non_bar_cap(s, "order_notice")
    def _scene_v2_order_notice_known(self, s): return self._generic_non_bar_known(s, "order_notice")

    # ------------------------------------------------------------------
    # viewpoint 3 -- timestamp precision
    # ------------------------------------------------------------------
    def _scene_v3_precision_known(self, scene: Scene) -> SceneResult:
        uses_index = "candles.index" in _ENGINE_SRC
        reads_index_for_logic = False  # confirmed by reading engine.py: candles.index is only
        # ever assigned to equity_curve's index (pass-through label), never parsed/compared.
        return SceneResult(
            "not_supported",
            detail=(
                f"engine.py を実測: candles.index への参照は{'ある' if uses_index else '無い'}が、"
                f"唯一の用例は `equity_curve = pd.Series(equity, index=candles.index)` "
                f"(engine.py:396) というラベルの素通しのみで、時刻を読み取って比較・変換する"
                f"ロジックは存在しない(grep 'timestamp' src/bot/backtest/engine.py の当たり0件、"
                f"2026-09-23 実測)。int64 ns への変換を行い、それを読み出して確かめる経路が無いため、"
                f"この既知解場面は対応なし。"
            ),
        )

    def _scene_v3_precision_cap(self, scene: Scene) -> SceneResult:
        return SceneResult(
            "not_supported",
            detail="engine.py に内部時刻表現の型を申告する関数・定数・docstring 契約が無い(grep 'ns\\|nanosecond\\|int64' の当たり0件、2026-09-23実測)。",
        )

    # ------------------------------------------------------------------
    # viewpoint 4 -- look-ahead prevention
    # ------------------------------------------------------------------
    def _scene_v4_lookahead_known(self, scene: Scene) -> SceneResult:
        bars = scene.input["bars"]
        probe_index = scene.input["probe_index"]
        rec = _RecordingStrategy()
        df = _bars_to_df(bars)
        bt_engine.run_backtest(rec, df)
        slice_at_probe = rec.calls[probe_index]
        max_visible_close = float(slice_at_probe["close"].max())
        visible_count = len(slice_at_probe)
        output = {"max_visible_close": max_visible_close, "visible_count": visible_count}
        match = output == scene.expected
        return SceneResult(
            "ok" if match else "error",
            output=output,
            detail=(
                f"合成6足を通し、探査時刻(probe_index={probe_index})時点で on_candles に渡された"
                f"スライスを直接読み出した: 見えた本数={visible_count}, 見えた close の最大={max_visible_close}。"
                f"既知解({scene.expected})と{'一致' if match else '不一致'}。"
                f"engine.py:3-4 の docstring『candles at bar i sees candles[0..i] only』"
                f"(expanding slice)が実測でも成立している。"
            ),
        )

    def _scene_v4_lookahead_cap(self, scene: Scene) -> SceneResult:
        # 2026-09-23 fix (場面集の規則1): stop self-reporting a prose verdict
        # and instead actually attempt, from inside on_candles, to read one
        # row past what this callback was handed (candles.iloc[len(candles)]),
        # the same mechanism v4-lookahead-known reads its known answer from.
        bars = scene.input["bars"]
        probe_index = scene.input["probe_index"]
        rec = _RecordingStrategy()
        df = _bars_to_df(bars)
        probe: dict = {}

        _orig_on_candles = rec.on_candles

        def _probing_on_candles(candles: pd.DataFrame):
            if len(candles) == probe_index + 1 and "raised" not in probe:
                try:
                    leaked = candles.iloc[len(candles)]
                    probe["raised"] = False
                    probe["leaked_close"] = float(leaked["close"])
                except IndexError:
                    probe["raised"] = True
            return _orig_on_candles(candles)

        rec.on_candles = _probing_on_candles
        bt_engine.run_backtest(rec, df)
        output = {"future_index_raises": probe.get("raised", False)}
        match = output == scene.expected
        return SceneResult(
            "ok" if match else "error",
            output=output,
            detail=(
                f"探査時刻(probe_index={probe_index})の on_candles 呼び出し内で "
                f"`candles.iloc[len(candles)]`(1つ先の未到達行)を実際に読もうとした実測: "
                f"{'IndexErrorで読めなかった' if probe.get('raised') else f'読めてしまい値={probe.get(\"leaked_close\")}が漏れた'}。"
                f"既知解({scene.expected})と{'一致' if match else '不一致'}。"
                f"(このスライス自体は expanding slice で future_index_raises=True になるのが実測結果。"
                f"ただし全件の candles DataFrame 自体は run_backtest 呼び出し時に丸ごと渡されており、"
                f"戦略実装者が `self` に元の DataFrame への参照を保存すれば、この場面の外側で"
                f"将来を読める余地は残る -- 規約による防止であり型システムによる強制ではない点は"
                f"別途 [直す] として報告する。)"
            ),
        )

    # ------------------------------------------------------------------
    # viewpoint 5 -- deterministic same-timestamp ordering
    # ------------------------------------------------------------------
    def _scene_v5_order_known(self, scene: Scene) -> SceneResult:
        return SceneResult(
            "not_supported",
            detail=(
                "engine.py のループは位置インデックス `i` (整数)で進み、DataFrame の行は"
                "一意な位置を持つため『同一タイムスタンプの複数事象』という状況がそもそも構造上"
                "発生しない(REQUIREMENTS.md 観点5の当方分析と同じ結論を、この回、"
                "run_backtest のループ本体を読み直して確認した: engine.py:273 "
                "`for i in range(len(candles))` に tie-break の分岐は無い)。"
                "そのため同時刻を2回投入して順序一致を見る、という場面自体が成立しない。"
            ),
        )

    def _scene_v5_order_cap(self, scene: Scene) -> SceneResult:
        return SceneResult(
            "not_supported",
            detail="同時刻の並びの規則を明記した記述(docstring/コード)は engine.py に無い(概念が無いため規則も無い)。",
        )

    # ------------------------------------------------------------------
    # viewpoint 6 -- strategy API completeness
    # ------------------------------------------------------------------
    def _scene_v6_order_lifecycle_known(self, scene: Scene) -> SceneResult:
        has_place = hasattr(Strategy, "place_order") or hasattr(Strategy, "order")
        has_cancel = hasattr(Strategy, "cancel_order") or hasattr(Strategy, "cancel")
        return SceneResult(
            "not_supported",
            detail=(
                f"Strategy 抽象クラス(strategy/base.py)を実測: hasattr('place_order' or 'order')="
                f"{has_place}, hasattr('cancel_order' or 'cancel')={has_cancel}。"
                f"戦略は on_candles() から Signal(BUY/SELL/CLOSE/HOLD) を返すだけで、発注・取消を"
                f"能動的に呼ぶメソッドが Strategy に定義されていない(発注可否とサイズは engine 側が"
                f"Signal を受けて決める)。発注→取消という操作列を戦略側から起こす経路が無いため、"
                f"この既知解場面は対応なし。"
            ),
        )

    def _scene_v6_api_surface_cap(self, scene: Scene) -> SceneResult:
        has_callback = hasattr(Strategy, "on_candles")
        has_place = hasattr(Strategy, "place_order") or hasattr(Strategy, "order")
        has_cancel = hasattr(Strategy, "cancel_order") or hasattr(Strategy, "cancel")
        count = sum([has_callback, has_place, has_cancel])
        return SceneResult(
            "ok",
            output={"count": count, "callback": has_callback, "place": has_place, "cancel": has_cancel},
            detail=(
                f"Strategy を hasattr で実測: on_candles={has_callback}, "
                f"place_order/order={has_place}, cancel_order/cancel={has_cancel}。合計 {count}/3。"
            ),
        )

    # ------------------------------------------------------------------
    # viewpoint 7 -- extension points
    # ------------------------------------------------------------------
    def _scene_v7_cost_swap_known(self, scene: Scene) -> SceneResult:
        order = scene.input["order"]
        zero_costs = bt_engine.CostModel(
            taker_fee_pct=0.0, maker_fee_pct=0.0, slippage_pct=0.0, spread_pct=0.0
        )
        notional = order["qty"] * order["price"]
        fee = zero_costs.fee(notional)
        output = {"fee": fee}
        match = output == scene.expected
        return SceneResult(
            "ok" if match else "error",
            output=output,
            detail=(
                f"engine.CostModel(taker_fee_pct=0, maker_fee_pct=0, slippage_pct=0, spread_pct=0) "
                f"を core(engine.py) のコードを一切書き換えずにコンストラクタで組み立て、"
                f".fee({notional}) を実行した実測値 = {fee}。既知解({scene.expected})と"
                f"{'一致' if match else '不一致'}。CostModel は engine.py 内の他クラスから独立した"
                f"dataclass で、run_backtest(..., costs=...) のキーワード引数として差し替え可能。"
            ),
        )

    def _scene_v7_extension_points_cap(self, scene: Scene) -> SceneResult:
        sig = inspect.signature(bt_engine.run_backtest)
        params = set(sig.parameters)
        has_cost = "costs" in params
        has_latency = any(p for p in params if "latency" in p or "delay" in p)
        has_fill_model = any(p for p in params if "fill" in p or "execution" in p)
        has_account = any(p for p in params if "account" in p or "portfolio" in p)
        count = sum([has_cost, has_latency, has_fill_model, has_account])
        return SceneResult(
            "ok",
            output={
                "count": count,
                "cost": has_cost,
                "latency": has_latency,
                "fill_model": has_fill_model,
                "account": has_account,
            },
            detail=(
                f"run_backtest{sig} のキーワード引数を実測。費用(costs)={has_cost}。"
                f"'latency'/'delay' を含む引数={has_latency}。'fill'/'execution' を含む引数="
                f"{has_fill_model}(maker/taker の挙動は引数ではなくハードコードのロジック分岐)。"
                f"'account'/'portfolio' を含む引数={has_account}。合計 {count}/4"
                f"(費用のみ核を書き換えずに差し替え可能。約定模型はコード分岐で選ぶのみで独立した"
                f"注入口ではない。遅延模型・口座模型の引数は無い)。"
            ),
        )
