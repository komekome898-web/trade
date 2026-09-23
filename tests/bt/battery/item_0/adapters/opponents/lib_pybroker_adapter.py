"""Opponent adapter: 候補4 PyBroker (`lib-pybroker` on PyPI) (SCAN 6845行, 足 段(機構)最大値6)。

Installed for real in `<scratchpad>/bt/venvs/item_0/lib-pybroker/` via
`pip install lib-pybroker` (PyPI project name differs from the import name
`pybroker` -- both confirmed live in this venv).
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

_ADAPTERS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ADAPTERS_DIR))

from protocol import Adapter, SceneResult  # noqa: E402
from scenes import Scene  # noqa: E402
from opponents._common import walk_submodule_names  # noqa: E402

try:
    import pybroker as _pb  # noqa: E402
    import pybroker.strategy as _st  # noqa: E402
    import inspect as _inspect
    import dataclasses as _dc
    _IMPORT_ERROR: Exception | None = None
    _ALL_SUBMODULES = walk_submodule_names(_pb)
    _EXECCTX_SRC = _inspect.getsource(_pb.ExecContext)
    _CONFIG_FIELDS = [f.name for f in _dc.fields(_pb.StrategyConfig)]
except Exception as exc:  # noqa: BLE001
    _IMPORT_ERROR = exc
    _ALL_SUBMODULES = []
    _EXECCTX_SRC = ""
    _CONFIG_FIELDS = []


class LibPybrokerAdapter(Adapter):
    name = "opp_lib_pybroker"

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
        sig = inspect.signature(_st.Strategy.backtest)
        return SceneResult(
            "not_supported",
            output={"event_driven": False},
            detail=(
                f"pybroker.strategy.Strategy.backtest{sig} を実測: start_date/end_date で範囲を"
                f"指定して丸ごと実行する形で、1件ずつ事象を外部から供給する公開APIは無い。"
                f"ExecContext はシンボルごとに足単位で呼ばれるコールバックだが、当方の現状"
                f"(engine.py)と同型 -- 「足単位のコールバックはあるが事前に全区間のデータが要る」。"
            ),
        )

    def _generic_v2_cap(self, scene: Scene, key: str, supported: bool, detail: str) -> SceneResult:
        return SceneResult("ok" if supported else "not_supported", output={"supported": supported}, detail=detail)

    def _scene_v2_bar_cap(self, scene: Scene) -> SceneResult:
        return self._generic_v2_cap(scene, "bar", True, "pybroker.BarData が公開型として存在(実測 hasattr(pybroker,'BarData')=True)。足そのものを表す事象型を持つ。")

    def _scene_v2_bar_known(self, scene: Scene) -> SceneResult:
        return SceneResult("no_record", detail="BarData の往復には Strategy.backtest の実行(データソース接続)が要り、この周は未実行。")

    def _scene_v2_fill_cap(self, scene: Scene) -> SceneResult:
        has_order = hasattr(_pb, "Order")
        has_trade = hasattr(_pb, "Trade")
        return self._generic_v2_cap(scene, "fill", has_order and has_trade, f"pybroker.Order 実在={has_order}, pybroker.Trade 実在={has_trade}(hasattr 実測)。約定は Trade 型で表現。")

    def _scene_v2_fill_known(self, scene: Scene) -> SceneResult:
        return SceneResult("no_record", detail="Trade の往復には実行が要り、この周は未実行。")

    def _scene_v2_book_snapshot_cap(self, scene: Scene) -> SceneResult:
        return self._generic_v2_cap(scene, "book_snapshot", False, f"サブモジュール {_ALL_SUBMODULES} に板(orderbook)関連の名前なし(実測)。")

    def _scene_v2_book_snapshot_known(self, scene: Scene) -> SceneResult:
        return SceneResult("not_supported", detail="cap 場面で不在確認済み。")

    def _scene_v2_book_delta_cap(self, scene: Scene) -> SceneResult:
        return self._generic_v2_cap(scene, "book_delta", False, "同上、板の差分に対応する型なし(実測)。")

    def _scene_v2_book_delta_known(self, scene: Scene) -> SceneResult:
        return SceneResult("not_supported", detail="cap 場面で不在確認済み。")

    def _scene_v2_funding_cap(self, scene: Scene) -> SceneResult:
        hit = any("fund" in n.lower() for n in _ALL_SUBMODULES) or "funding" in _EXECCTX_SRC.lower()
        return self._generic_v2_cap(scene, "funding", hit, f"サブモジュール走査 + ExecContext ソース中の 'funding' 検索、実測当たり={hit}。")

    def _scene_v2_funding_known(self, scene: Scene) -> SceneResult:
        return SceneResult("not_supported", detail="cap 場面で不在確認済み。")

    def _scene_v2_liquidation_cap(self, scene: Scene) -> SceneResult:
        # NOTE: a naive 'liquidat' keyword grep DOES hit ExecContext's source (実測),
        # but reading those 3 lines shows they all mean "close our own open
        # position" (a portfolio action), never a market-wide forced-liquidation
        # event as traded/reported by the venue (the 事象型「清算」this scene
        # asks about). Recorded as not_supported to avoid a false positive.
        hit_raw = "liquidat" in _EXECCTX_SRC.lower()
        return self._generic_v2_cap(
            scene, "liquidation", False,
            f"ExecContext ソース中の 'liquidat' 検索は当たり(hit_raw={hit_raw})だが、"
            f"実際の3件はいずれも『自分の建玉を手仕舞う』という意味(例: "
            f"'which the position is automatically liquidated' -- ポジションの自動決済)で、"
            f"取引所発の強制清算イベント(市場の事象としての清算)を表す型ではない。"
            f"キーワード一致と概念一致を混同しないため not_supported とした。",
        )

    def _scene_v2_liquidation_known(self, scene: Scene) -> SceneResult:
        return SceneResult("not_supported", detail="cap 場面で不在確認済み。")

    def _scene_v2_clock_cap(self, scene: Scene) -> SceneResult:
        return self._generic_v2_cap(scene, "clock", False, f"サブモジュール {_ALL_SUBMODULES} に clock 相当の名前なし(実測)。")

    def _scene_v2_clock_known(self, scene: Scene) -> SceneResult:
        return SceneResult("not_supported", detail="cap 場面で不在確認済み。")

    def _scene_v2_order_notice_cap(self, scene: Scene) -> SceneResult:
        has_order_type = hasattr(_pb, "OrderType")
        return self._generic_v2_cap(scene, "order_notice", has_order_type, f"pybroker.OrderType 実在 hasattr={has_order_type}。受付/拒否/約定を分ける明示の通知イベント型は同ソース内には確認できず(浅い探査)。")

    def _scene_v2_order_notice_known(self, scene: Scene) -> SceneResult:
        return SceneResult("no_record", detail="未実行。")

    def _scene_v3_precision_known(self, scene: Scene) -> SceneResult:
        return SceneResult("no_record", detail="pybroker は pandas ベースだが、内部の時刻表現を往復させる実行はこの周は未実行。")

    def _scene_v3_precision_cap(self, scene: Scene) -> SceneResult:
        return SceneResult("not_supported", detail="内部時刻表現の型を申告する公開の定数・関数は、実測した範囲には見当たらない。")

    def _scene_v4_lookahead_known(self, scene: Scene) -> SceneResult:
        return SceneResult("no_record", detail="実行にはデータソース接続が要り、この周は未実行。")

    def _scene_v4_lookahead_cap(self, scene: Scene) -> SceneResult:
        return SceneResult("no_record", detail="同上。")

    def _scene_v5_order_known(self, scene: Scene) -> SceneResult:
        return SceneResult("no_record", detail="未実行。")

    def _scene_v5_order_cap(self, scene: Scene) -> SceneResult:
        return SceneResult("no_record", detail="未実行。")

    def _scene_v6_order_lifecycle_known(self, scene: Scene) -> SceneResult:
        return SceneResult("no_record", detail="buy_shares/cancel_pending_order の実在は v6-api_surface-cap で確認したが、実発注の動的実行はこの周は未実行。")

    def _scene_v6_api_surface_cap(self, scene: Scene) -> SceneResult:
        has_callback = True  # ExecContext is invoked per bar per symbol by the framework
        has_place = "buy_shares" in _EXECCTX_SRC or "sell_shares" in _EXECCTX_SRC
        has_cancel = "cancel_pending_order" in _EXECCTX_SRC
        count = sum([has_callback, has_place, has_cancel])
        return SceneResult(
            "ok",
            output={"count": count, "callback": has_callback, "place": has_place, "cancel": has_cancel},
            detail=(
                f"ExecContext のソース文字列を実測: 'buy_shares'/'sell_shares' あり={has_place}, "
                f"'cancel_pending_order' あり={has_cancel}。callback は Strategy が各足でシンボルごとに"
                f"ExecContext を呼ぶ設計(pybroker.strategy 全体構造から)。合計 {count}/3。"
            ),
        )

    def _scene_v7_cost_swap_known(self, scene: Scene) -> SceneResult:
        return SceneResult(
            "no_record",
            detail=(
                "StrategyConfig(fee_mode=None, fee_amount=0) がゼロ手数料に相当することは"
                "フィールド定義(fee_mode, fee_amount)から読めるが、手数料は Strategy.backtest の"
                "実行内部でのみ計算され、孤立した呼び出しで確かめる経路が無い。この周は未実行。"
            ),
        )

    def _scene_v7_extension_points_cap(self, scene: Scene) -> SceneResult:
        has_cost = "fee_mode" in _CONFIG_FIELDS and "fee_amount" in _CONFIG_FIELDS
        has_latency = "buy_delay" in _CONFIG_FIELDS and "sell_delay" in _CONFIG_FIELDS
        has_fill_model = any("slippage" in n.lower() for n in _ALL_SUBMODULES)
        has_account = "initial_cash" in _CONFIG_FIELDS or "leverage" in _CONFIG_FIELDS
        count = sum([has_cost, has_latency, has_fill_model, has_account])
        return SceneResult(
            "ok",
            output={"count": count, "cost": has_cost, "latency": has_latency, "fill_model": has_fill_model, "account": has_account},
            detail=(
                f"pybroker.StrategyConfig のフィールド {_CONFIG_FIELDS} を実測。費用(fee_mode/"
                f"fee_amount)={has_cost}, 遅延(buy_delay/sell_delay)={has_latency}, "
                f"約定/滑り(pybroker.slippage サブモジュール)={has_fill_model}, "
                f"口座(initial_cash/leverage)={has_account}。合計 {count}/4。"
            ),
        )
