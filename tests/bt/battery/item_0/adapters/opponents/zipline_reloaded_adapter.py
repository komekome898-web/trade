"""Opponent adapter: 候補18 zipline-reloaded (SCAN 9857行, viewpoint1 段(機構)最大値, 台帳イベント駆動=○)。

Installed for real in `<scratchpad>/bt/venvs/item_0/zipline-reloaded/` via
`pip install zipline-reloaded`. Same rules as `ziplime_adapter.py`: every
check imports and calls the actually-installed package.
"""
from __future__ import annotations

import sys
from pathlib import Path

_ADAPTERS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ADAPTERS_DIR))

from protocol import Adapter, SceneResult  # noqa: E402
from scenes import Scene  # noqa: E402
from opponents._common import class_methods_present, walk_submodule_names  # noqa: E402

try:
    import zipline  # noqa: E402
    import zipline.algorithm as _alg  # noqa: E402
    import zipline.finance.commission as _comm  # noqa: E402
    import zipline.gens.sim_engine as _sim_engine  # noqa: E402
    import zipline.gens.tradesimulation as _tradesim  # noqa: E402
    import zipline.finance.order as _order  # noqa: E402
    import inspect as _inspect
    _IMPORT_ERROR: Exception | None = None
    _ALL_SUBMODULES = walk_submodule_names(zipline)
    _TRADESIM_SRC = _inspect.getsource(_tradesim)
    _ORDER_SRC = _inspect.getsource(_order)
except Exception as exc:  # noqa: BLE001
    _IMPORT_ERROR = exc
    _ALL_SUBMODULES = []
    _TRADESIM_SRC = ""
    _ORDER_SRC = ""

_EVENT_KEYWORDS = {
    "fill": ["order", "transaction"],
    "book_snapshot": ["orderbook", "order_book", "book"],
    "book_delta": ["orderbook", "order_book", "book"],
    "bar": ["bar", "ohlcv"],
    "funding": ["funding"],
    "liquidation": ["liquidat"],
    "clock": ["clock", "sim_engine"],
    "order_notice": ["order"],
}


class ZiplineReloadedAdapter(Adapter):
    name = "opp_zipline_reloaded"

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

    def _scene_v1_event_driven_cap(self, scene: Scene) -> SceneResult:
        has_clock_class = hasattr(_sim_engine, "MinuteSimulationClock")
        has_yield = "yield" in _TRADESIM_SRC
        return SceneResult(
            "ok" if (has_clock_class and has_yield) else "not_supported",
            output={"event_driven": has_clock_class and has_yield},
            detail=(
                f"zipline.gens.sim_engine.MinuteSimulationClock の実在 hasattr={has_clock_class}。"
                f"zipline.gens.tradesimulation のソースに 'yield' あり={has_yield}"
                f"(bar 単位の生成器で駆動する構造)。"
            ),
        )

    def _generic_v2_cap(self, scene: Scene, key: str) -> SceneResult:
        kws = _EVENT_KEYWORDS[key]
        hits = [n for n in _ALL_SUBMODULES if any(k in n.lower() for k in kws)]
        supported = len(hits) > 0
        return SceneResult(
            "ok" if supported else "not_supported",
            output={"supported": supported},
            detail=f"サブモジュール {len(_ALL_SUBMODULES)} 件をキーワード {kws} で実測フィルタ。当たり {len(hits)} 件: {hits[:4]}。",
        )

    def _generic_v2_known(self, scene: Scene, key: str) -> SceneResult:
        return SceneResult(
            "no_record",
            detail=f"{key} のモジュール存在は cap 場面で確認済みだが、往復の動的実行(取引カレンダー/バンドル要)はこの周は未実行。",
        )

    def _scene_v2_fill_cap(self, s): return self._generic_v2_cap(s, "fill")
    def _scene_v2_fill_known(self, s): return self._generic_v2_known(s, "fill")
    def _scene_v2_book_snapshot_cap(self, s): return self._generic_v2_cap(s, "book_snapshot")
    def _scene_v2_book_snapshot_known(self, s): return self._generic_v2_known(s, "book_snapshot")
    def _scene_v2_book_delta_cap(self, s): return self._generic_v2_cap(s, "book_delta")
    def _scene_v2_book_delta_known(self, s): return self._generic_v2_known(s, "book_delta")
    def _scene_v2_bar_cap(self, s): return self._generic_v2_cap(s, "bar")
    def _scene_v2_bar_known(self, s): return self._generic_v2_known(s, "bar")
    def _scene_v2_funding_cap(self, s): return self._generic_v2_cap(s, "funding")
    def _scene_v2_funding_known(self, s): return self._generic_v2_known(s, "funding")
    def _scene_v2_liquidation_cap(self, s): return self._generic_v2_cap(s, "liquidation")
    def _scene_v2_liquidation_known(self, s): return self._generic_v2_known(s, "liquidation")

    def _scene_v2_clock_cap(self, scene: Scene) -> SceneResult:
        has_clock = hasattr(_sim_engine, "MinuteSimulationClock")
        return SceneResult(
            "ok" if has_clock else "not_supported",
            output={"supported": has_clock},
            detail=f"zipline.gens.sim_engine.MinuteSimulationClock 実在 hasattr={has_clock}。",
        )

    def _scene_v2_clock_known(self, s): return self._generic_v2_known(s, "clock")

    def _scene_v2_order_notice_cap(self, scene: Scene) -> SceneResult:
        has_status = "ORDER_STATUS" in _ORDER_SRC
        has_rejected = "REJECTED" in _ORDER_SRC
        has_cancelled = "CANCELLED" in _ORDER_SRC
        supported = has_status and has_rejected
        return SceneResult(
            "ok" if supported else "not_supported",
            output={"supported": supported},
            detail=(
                f"zipline.finance.order のソースを実測: ORDER_STATUS 定義あり={has_status}, "
                f"REJECTED あり={has_rejected}, CANCELLED あり={has_cancelled}。"
            ),
        )

    def _scene_v2_order_notice_known(self, s): return self._generic_v2_known(s, "order_notice")

    def _scene_v3_precision_known(self, scene: Scene) -> SceneResult:
        import pandas as pd
        iso = scene.input["iso"]
        ts = pd.Timestamp(iso)
        if ts.tzinfo is None:
            ts = ts.tz_localize("UTC")
        else:
            ts = ts.tz_convert("UTC")
        output = int(ts.value)
        match = output == scene.expected
        return SceneResult(
            "ok" if match else "error",
            output=output,
            detail=(
                f"pandas.Timestamp({iso!r}).tz_convert('UTC').value を実行した実測値={output}。"
                f"既知解({scene.expected})と{'一致' if match else '不一致'}。"
                f"ただし zipline 自身のイベントオブジェクトがこの精度のまま値を保持して"
                f"往復することまでは確認していない(pandas の基盤機能の確認に留まる)。"
            ),
        )

    def _scene_v3_precision_cap(self, scene: Scene) -> SceneResult:
        return SceneResult(
            "ok",
            output={"dtype": "pandas.Timestamp (int64 ns, tz-aware)"},
            detail="zipline はカレンダー・セッションに pandas の DatetimeIndex/Timestamp を用いる(zipline.utils.calendar_utils 依存)。ns 精度は pandas の基盤機能として申告可能。",
        )

    def _scene_v4_lookahead_known(self, scene: Scene) -> SceneResult:
        return SceneResult("no_record", detail="実行確認には取引カレンダー/バンドルが要り、この周は未実行。")

    def _scene_v4_lookahead_cap(self, scene: Scene) -> SceneResult:
        return SceneResult("no_record", detail="同上(未実行)。")

    def _scene_v5_order_known(self, scene: Scene) -> SceneResult:
        return SceneResult("no_record", detail="未実行。")

    def _scene_v5_order_cap(self, scene: Scene) -> SceneResult:
        return SceneResult("no_record", detail="未実行。")

    def _scene_v6_order_lifecycle_known(self, scene: Scene) -> SceneResult:
        return SceneResult("no_record", detail="order()/cancel_order() の実在は v6-api_surface-cap で確認したが、実発注の動的実行はこの周は未実行。")

    def _scene_v6_api_surface_cap(self, scene: Scene) -> SceneResult:
        present = class_methods_present(_alg.TradingAlgorithm, ["handle_data", "order", "cancel_order"])
        count = sum(present.values())
        return SceneResult(
            "ok",
            output={"count": count, **present},
            detail=f"zipline.algorithm.TradingAlgorithm を hasattr で実測: {present}。合計 {count}/3。",
        )

    def _scene_v7_cost_swap_known(self, scene: Scene) -> SceneResult:
        fee = _comm.NoCommission.calculate(None, None)
        output = {"fee": float(fee)}
        match = output == scene.expected
        return SceneResult(
            "ok" if match else "error",
            output=output,
            detail=f"zipline.finance.commission.NoCommission.calculate(None, None) を実行した実測値={fee}。既知解と{'一致' if match else '不一致'}。",
        )

    def _scene_v7_extension_points_cap(self, scene: Scene) -> SceneResult:
        kws = {
            "cost": ["commission"],
            "latency": ["latency", "delay"],
            "fill_model": ["slippage", "execution"],
            "account": ["account", "portfolio", "ledger"],
        }
        present = {k: any(any(w in n.lower() for w in words) for n in _ALL_SUBMODULES) for k, words in kws.items()}
        count = sum(present.values())
        return SceneResult(
            "ok",
            output={"count": count, **present},
            detail=f"サブモジュール名をキーワード走査した実測: {present}。合計 {count}/4。",
        )
