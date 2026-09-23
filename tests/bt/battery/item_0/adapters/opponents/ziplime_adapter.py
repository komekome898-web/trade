"""Opponent adapter: 候補6 ziplime (SCAN 9650行, viewpoint1/7 段(機構) 4・6, 台帳イベント駆動=○)。

Installed for real in `<scratchpad>/bt/venvs/item_0/ziplime/` via
`pip install ziplime` (needs Python >=3.12; see `opponents/CONSIDERED.md` for
the install log path). Every check below imports the ACTUALLY installed
package and inspects/calls it live -- see each `detail` string for the exact
module/class/call used, so a reader can redo it with
`<venv>/bin/python3 -c "..."`.
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
    import ziplime  # noqa: E402
    import ziplime.trading.trading_algorithm as _ta  # noqa: E402
    import ziplime.trading.trading_algorithm_executor as _executor  # noqa: E402
    import ziplime.finance.commission.no_commission as _no_commission  # noqa: E402
    import ziplime.finance.domain.order_status as _order_status  # noqa: E402
    import inspect as _inspect
    _IMPORT_ERROR: Exception | None = None
    _ALL_SUBMODULES = walk_submodule_names(ziplime)
    _EXECUTOR_SRC = _inspect.getsource(_executor)
except Exception as exc:  # noqa: BLE001
    _IMPORT_ERROR = exc
    _ALL_SUBMODULES = []
    _EXECUTOR_SRC = ""


_EVENT_KEYWORDS = {
    "fill": ["order", "transaction", "fill"],
    "book_snapshot": ["orderbook", "order_book", "book"],
    "book_delta": ["orderbook", "order_book", "book"],
    "bar": ["bar", "ohlcv", "candle"],
    "funding": ["funding"],
    "liquidation": ["liquidat"],
    "clock": ["clock"],
    "order_notice": ["order_status", "orders"],
}


class ZiplimeAdapter(Adapter):
    name = "opp_ziplime"

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
        has_yield = "yield" in _EXECUTOR_SRC
        has_async_iter = "AsyncIterator" in _EXECUTOR_SRC
        return SceneResult(
            "ok" if (has_yield or has_async_iter) else "not_supported",
            output={"event_driven": has_yield or has_async_iter},
            detail=(
                f"ziplime.trading.trading_algorithm_executor のソースを実測: "
                f"'yield' あり={has_yield}, 'AsyncIterator' あり={has_async_iter}。"
                f"1件ずつ供給する具体的な公開APIまでは呼んでいない(モジュールの構造上の"
                f"根拠のみ)。"
            ),
        )

    # v2 -------------------------------------------------------------
    def _generic_v2_cap(self, scene: Scene, key: str) -> SceneResult:
        kws = _EVENT_KEYWORDS[key]
        hits = [n for n in _ALL_SUBMODULES if any(k in n.lower() for k in kws)]
        supported = len(hits) > 0
        return SceneResult(
            "ok" if supported else "not_supported",
            output={"supported": supported},
            detail=(
                f"pkgutil.walk_packages(ziplime) で得た {len(_ALL_SUBMODULES)} サブモジュールを"
                f"キーワード {kws} で実測フィルタ。当たり {len(hits)} 件: {hits[:5]}"
                f"{'...' if len(hits) > 5 else ''}。"
            ),
        )

    def _generic_v2_known(self, scene: Scene, key: str) -> SceneResult:
        return SceneResult(
            "no_record",
            detail=(
                f"{key} 型のモジュール存在は v2-{key}-cap で確認したが、合成1件を実際に投入して"
                f"往復させるには取引カレンダー/バンドル等のブートストラップが要り、この周では"
                f"未実行(範囲: モジュール構造の走査のみ)。"
            ),
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
    def _scene_v2_clock_cap(self, s): return self._generic_v2_cap(s, "clock")
    def _scene_v2_clock_known(self, s): return self._generic_v2_known(s, "clock")

    def _scene_v2_order_notice_cap(self, scene: Scene) -> SceneResult:
        members = [m.name for m in _order_status.OrderStatus]
        supported = "FILLED" in members and "REJECTED" in members
        return SceneResult(
            "ok" if supported else "not_supported",
            output={"supported": supported, "members": members},
            detail=f"ziplime.finance.domain.order_status.OrderStatus を実測: {members}。",
        )

    def _scene_v2_order_notice_known(self, scene: Scene) -> SceneResult:
        return self._generic_v2_known(scene, "order_notice")

    # v3 -------------------------------------------------------------
    def _scene_v3_precision_known(self, scene: Scene) -> SceneResult:
        return SceneResult(
            "no_record",
            detail=(
                "ziplime は内部で pandas を使っており pandas.Timestamp は tz 付きなら int64 ns を"
                "保持できることは一般に確認できるが(このバッテリーの別候補 zipline-reloaded の"
                "v3-precision-known 実測: pd.Timestamp(...).value と既知解が一致)、ziplime 自身の"
                "事象オブジェクトがその精度を保ったまま入出力することは、この周では未実行"
                "(取引カレンダー/バンドルのブートストラップが要る)。"
            ),
        )

    def _scene_v3_precision_cap(self, scene: Scene) -> SceneResult:
        return SceneResult(
            "not_supported",
            detail="内部時刻表現の型を申告する公開の関数・定数は、実測した範囲(walk_submodule_names)には見当たらない。",
        )

    # v4 / v5 -- not attempted dynamically this round -----------------
    def _scene_v4_lookahead_known(self, scene: Scene) -> SceneResult:
        return SceneResult(
            "no_record",
            detail="実行での確認には取引カレンダー/バンドルの用意が要り、この周では未実行。",
        )

    def _scene_v4_lookahead_cap(self, scene: Scene) -> SceneResult:
        return SceneResult(
            "no_record",
            detail="同上(未実行)。",
        )

    def _scene_v5_order_known(self, scene: Scene) -> SceneResult:
        return SceneResult("no_record", detail="未実行(取引カレンダー/バンドルの用意が要る)。")

    def _scene_v5_order_cap(self, scene: Scene) -> SceneResult:
        return SceneResult("no_record", detail="未実行。")

    # v6 -------------------------------------------------------------
    def _scene_v6_order_lifecycle_known(self, scene: Scene) -> SceneResult:
        return SceneResult(
            "no_record",
            detail=(
                "order()/cancel_order() の存在は v6-api_surface-cap で確認したが、実発注→取消の"
                "操作列には取引カレンダー・アセット登録が要り、この周では未実行。"
            ),
        )

    def _scene_v6_api_surface_cap(self, scene: Scene) -> SceneResult:
        present = class_methods_present(_ta.TradingAlgorithm, ["handle_data", "order", "cancel_order"])
        count = sum(present.values())
        return SceneResult(
            "ok",
            output={"count": count, **present},
            detail=f"ziplime.trading.trading_algorithm.TradingAlgorithm を hasattr で実測: {present}。合計 {count}/3。",
        )

    # v7 -------------------------------------------------------------
    def _scene_v7_cost_swap_known(self, scene: Scene) -> SceneResult:
        order = scene.input["order"]
        model = _no_commission.NoCommission()
        fee = model.calculate_for_asset(None, order["qty"], order["price"] * order["qty"])
        output = {"fee": float(fee)}
        match = output == scene.expected
        return SceneResult(
            "ok" if match else "error",
            output=output,
            detail=(
                f"ziplime.finance.commission.no_commission.NoCommission().calculate_for_asset"
                f"(None, {order['qty']}, {order['price']*order['qty']}) を実行した実測値 = {fee}。"
                f"既知解({scene.expected})と{'一致' if match else '不一致'}。"
                f"NoCommission は engine 本体を書き換えず注入できる独立クラス。"
            ),
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
