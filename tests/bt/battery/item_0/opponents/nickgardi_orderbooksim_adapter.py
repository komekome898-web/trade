"""Survey candidate 99 `NickGardi/orderbooksim`, run in its own venv.

Source: GitHub `NickGardi/orderbooksim`, commit
b767b0c4e86be0535f505e0d09d5407a849da074 (cloned 2026-09-24; not on PyPI).
The venv `c99` has sortedcontainers and a `.pth` pointing at the clone, so
`import matching_engine` / `models` are the tool's own modules (install
record `survey_results/attempts/99.log`; the Streamlit app `app.py` is not
used).

What the tool is: `MatchingEngine` (submit_order / cancel_order /
get_order / get_book_snapshot / all_trades) over `models.Order.create(
order_id, side, price, quantity, timestamp=None)` whose timestamp is float
seconds (`time.time()` when not given). There is no market data input, no
event loop, no strategy callback, no latency, fee or account object. Each
scene is answered by a real call into it.
"""
from __future__ import annotations

import sys
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "adapters"))

from _vector_base import VectorBase  # noqa: E402
from protocol import not_supported, ok  # noqa: E402
import common as C  # noqa: E402

from matching_engine import MatchingEngine  # noqa: E402  (the tool's modules, from the clone via a .pth)
from models import Order, Side  # noqa: E402


def _attempt() -> str:
    me = MatchingEngine()
    me.submit_order(Order.create(me.next_order_id(), Side.SELL, 100.0, 100.0, timestamp=1_700_006_400.0))
    trades = me.submit_order(Order.create(me.next_order_id(), Side.BUY, 100.0, 1.0, timestamp=1_700_006_400.0))
    return (f"MatchingEngine().submit_order(売り 100@100) のあと submit_order(買い 1@100) -> {[(t.price, t.quantity) for t in trades]}; "
            f"MatchingEngine の公開の名前 {[n for n in dir(MatchingEngine) if not n.startswith('_')]}")


def _attempt_kw(**kw) -> str:
    try:
        MatchingEngine(**kw)
    except Exception as exc:  # noqa: BLE001
        return f"MatchingEngine({', '.join(kw)}=...) -> {type(exc).__name__}: {str(exc)[:140]}"
    return f"MatchingEngine({', '.join(kw)}=...) は受け付けられた"


class NickgardiOrderbooksimAdapter(VectorBase):
    name = "opp_nickgardi_orderbooksim"
    what = ("この道具は注文の照合の機関(MatchingEngine)だけで、相場の事象を受ける口・事象ごとに戦略を呼ぶ口・通知・時計・"
            "遅延・費用・口座が無い")

    def attempt(self, scene_id: str) -> str:
        return _attempt()

    def _held_time(self, sc):
        me, seen = MatchingEngine(), []
        for e in C.events(sc):
            oid = me.next_order_id()
            me.submit_order(Order.create(oid, Side.BUY, 1.0, 1.0, timestamp=int(e["ts_ns"]) / 1e9))
            seen.append(round(Fraction(me.get_order(oid).timestamp) * 1_000_000_000))  # exact: the loss is the tool's float
        # round r6-1 (same root as critic i0-r5-02): the scene measures what a strategy RECEIVES; this tool has no strategy that events are delivered to, so the value the tool holds is reported as evidence, not graded
        return not_supported(f"{self.what}(戦略に事象を渡す口が無く、戦略が受け取った時刻が無い)。試したこと: 事象ごとに買い 1@1.0 の注文を "
                             f"timestamp=ns/1e9 で出し、get_order(id).timestamp(float 秒)を ns に戻した -> {seen}")

    scene_p2_event_time_exact = scene_p2_one_ns_apart = _held_time

    def _iso(self, sc):
        me = MatchingEngine()
        oid = me.next_order_id()
        me.submit_order(Order.create(oid, Side.BUY, 1.0, 1.0, timestamp=sc.input["iso"]))
        held = me.get_order(oid).timestamp
        return not_supported("日時の文字列を時刻に直す変換が無い(Order.timestamp は float 秒で、渡した値を検めずに持つ)。"
                             f"試したこと: Order.create(..., timestamp='{sc.input['iso']}') -> get_order(id).timestamp = {held!r}")

    scene_p2_iso_utc = scene_p2_iso_offset = _iso

    # ---------------- P0-2 unit scenes (round r16-1): no entry that reads a time in a unit
    def _units(self, sc):
        return C.unit_time(sc, [], tried='Order.timestamp は float の秒のまま持ち(渡した値を検めない)、int ナノ秒にする変換が無い' + '(r16-1 の場面係が道具の配布物を fromtimestamp・unit=・timestamp_to_datetime・datetime64[s/ms/us]・/1000・*1000・epoch で検索した範囲。記録 survey_results/attempts/r16-1_unit_entries.txt)' + "。" + C.iso_entry_tried(self._iso, sc))

    scene_p2_s_text = scene_p2_s_text_subns = scene_p2_s_int = scene_p2_s_float_held = scene_p2_s_float_subns = \
        scene_p2_ms_text = scene_p2_ms_text_subns = scene_p2_ms_int = scene_p2_ms_float_held = scene_p2_ms_float_subns = \
        scene_p2_us_text = scene_p2_us_text_subns = scene_p2_us_int = scene_p2_us_float_held = _units  # round r16-1

    def scene_p6_cancel_notice(self, sc):
        me = MatchingEngine()
        oid = me.next_order_id()
        me.submit_order(Order.create(oid, Side.BUY, 90.0, 1.0, timestamp=1_700_006_400.0))
        return not_supported(f"取消の成否は cancel_order の戻り値だけで、戦略に届く事象が無い。試したこと: 買い 1@90 -> cancel_order({oid}) -> {me.cancel_order(oid)}")

    def scene_p7_fill_model_swap(self, sc):
        return not_supported("照合を差し替える口が無い。試したこと: " + _attempt_kw(fill_model=object()))

    def scene_p7_latency_model_swap(self, sc):
        return not_supported("遅延の物が無い(注文は submit_order の時にそのまま照合される)。試したこと: " + _attempt_kw(latency_model=object()))

    def _fee(self, sc):
        return not_supported("費用の物が無い(Trade の欄は id・買いと売りの注文の id・価格・数量・時刻だけ)。試したこと: " + _attempt_kw(cost_model=object()))

    scene_p7_cost_model_swap = scene_p7_cost_per_unit = _fee

    def scene_p7_account_swap(self, sc):
        return not_supported("口座の物が無い。試したこと: " + _attempt_kw(account=object()))
