"""Survey candidate 105 `DaniyalMlk/slippage` (distribution `slippage-tca`
0.1.0, built from the GitHub clone; the PyPI name `slippage` is another
project, SCAN 5218 行), run in its own venv.

Source: GitHub `DaniyalMlk/slippage`, commit
6985edb124b737b0979e3f4fd49fb65ffb2bfaf3 (cloned 2026-09-24), installed with
`pip install <clone>` (pyproject: setuptools build, dependency numpy only;
install record `survey_results/attempts/105.log`).

What the tool is: transaction-cost analysis and optimal execution
(Almgren-Chriss): impact models (`LinearImpact`, `PowerLawImpact`,
`SquareRootLaw`), `simulate_costs(impact, trades, tau=, volatility=)`
(Monte Carlo cost of a fixed schedule), and CSV loaders
(`slippage.io.load_bars` / `load_orders`) whose timestamps are ISO 8601 read
with `datetime.fromisoformat`. There is no event loop, strategy callback,
order placement, fill, notice, clock, latency or account. The bar loader is
the tool's only way in for market data and its only time conversion, so the
time and bar scenes use it; every other scene is answered by a real call.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "adapters"))

from _vector_base import VectorBase  # noqa: E402
from protocol import not_supported, ok  # noqa: E402
import common as C  # noqa: E402

from slippage import io as sio  # noqa: E402
from slippage.impact import LinearImpact  # noqa: E402
from slippage.simulate import simulate_costs  # noqa: E402


def _iso_of(ns: int) -> str:
    d = C.ns_to_dt(ns)
    return d.strftime("%Y-%m-%dT%H:%M:%S") + f".{int(ns) % 1_000_000_000:09d}+00:00"


def load(rows: list[tuple[str, dict]]):
    """Write rows (timestamp text, bar fields) as the tool's bars.csv and read it with load_bars."""
    with tempfile.TemporaryDirectory(dir=os.environ.get("BT_SCRATCH") or None) as d:
        p = Path(d) / "bars.csv"
        lines = ["symbol,timestamp,open,high,low,close,volume"]
        lines += [f"X,{ts},{b['open']},{b['high']},{b['low']},{b['close']},{b.get('volume', 1.0)}" for ts, b in rows]
        p.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return sio.load_bars(p)


def _bar(price: float = 100.0) -> dict:
    return {"open": price, "high": price, "low": price, "close": price, "volume": 1.0}


def _attempt() -> str:
    try:
        dist = simulate_costs(LinearImpact(0.0, 0.0), [1.0], tau=1.0, volatility=0.0, paths=4)
        r = f"平均 {dist.mean}"
    except Exception as exc:  # noqa: BLE001
        r = f"{type(exc).__name__}: {str(exc)[:120]}"
    import slippage
    return (f"simulate_costs(LinearImpact(0, 0), [1.0], tau=1, volatility=0, paths=4) -> {r}; "
            f"slippage の公開の名前 {[n for n in dir(slippage) if not n.startswith('_')][:40]}")


class DaniyalmlkSlippageAdapter(VectorBase):
    name = "opp_daniyalmlk_slippage"
    what = ("この道具は執行の費用の分析(影響の模型・費用の分布・CSV の読み込み)で、事象を流して戦略を呼ぶ機関・注文・約定・通知・時計・"
            "遅延・口座が無い")

    def attempt(self, scene_id: str) -> str:
        return _attempt()

    def _iso(self, sc):
        try:
            s = load([(sc.input["iso"], _bar())])
        except Exception as exc:  # noqa: BLE001
            return not_supported(f"load_bars(timestamp='{sc.input['iso']}') -> {type(exc).__name__}: {str(exc)[:160]}")
        return ok(C.dt_to_ns(s["X"][0].timestamp), "bars.csv の timestamp に ISO を書き、slippage.io.load_bars(datetime.fromisoformat で読む)の "
                  "Bar.timestamp を ns にした", {"reader": C.qualname(sio.load_bars)})

    scene_p2_iso_utc = scene_p2_iso_offset = _iso

    # ---------------- P0-2 unit scenes (round r16-1): no entry that reads a time in a unit
    def _units(self, sc):
        return C.unit_time(sc, [], tried='時刻を読む入口は CSV の timestamp の欄だけで、datetime.fromisoformat で読む(slippage/io.py 86・133 行)。数の時刻を読む変換は無い' + '(r16-1 の場面係が道具の配布物を fromtimestamp・unit=・timestamp_to_datetime・datetime64[s/ms/us]・/1000・*1000・epoch で検索した範囲。記録 survey_results/attempts/r16-1_unit_entries.txt)' + "。" + C.iso_entry_tried(self._iso, sc))

    scene_p2_s_text = scene_p2_s_text_subns = scene_p2_s_int = scene_p2_s_float_held = scene_p2_s_float_subns = \
        scene_p2_ms_text = scene_p2_ms_text_subns = scene_p2_ms_int = scene_p2_ms_float_held = scene_p2_ms_float_subns = \
        scene_p2_us_text = scene_p2_us_text_subns = scene_p2_us_int = scene_p2_us_float_held = _units  # round r16-1

    def _obs(self, sc):
        rows = [(_iso_of(e["ts_ns"]), _bar()) for e in C.events(sc)]
        try:
            s = load(rows)
        except Exception as exc:  # noqa: BLE001
            return not_supported(f"load_bars(timestamp={[r[0] for r in rows]}) -> {type(exc).__name__}: {str(exc)[:160]}")
        # round r6-1 (same root as critic i0-r5-02): the scene measures what a strategy RECEIVES; this tool has no strategy that events are delivered to, so the value the tool holds is reported as evidence, not graded
        return not_supported(f"{self.what}(戦略に事象を渡す口が無く、戦略が受け取った時刻が無い)。試したこと: 事象の時刻を 9 桁の小数の ISO にして "
                             f"bars.csv に書き({[r[0] for r in rows]})、load_bars が持った Bar.timestamp は {[C.dt_to_ns(b.timestamp) for b in s['X']]}")

    scene_p2_event_time_exact = scene_p2_one_ns_apart = _obs

    def scene_p3_bar(self, sc):
        e = C.events(sc)[0]
        s = load([(_iso_of(e["ts_ns"]), e)])
        b = s["X"][0]
        # round r6-1 (same root as critic i0-r5-02): the scene measures what a strategy RECEIVES; this tool has no strategy that events are delivered to, so the value the tool holds is reported as evidence, not graded
        return not_supported(f"{self.what}(足を事象として戦略に届ける口が無い)。試したこと: bars.csv 1 行を load_bars で読んだ -> 道具が持つ Bar "
                             f"{(C.dt_to_ns(b.timestamp), b.open, b.high, b.low, b.close, b.volume)}(足の型 Bar は在るが、戦略に渡らない)")

    def scene_p5_same_stream_order(self, sc):
        rows = [(_iso_of(e["ts_ns"]), _bar(float(e["price"]))) for e in C.events(sc)]
        try:
            s = load(rows)
        except Exception as exc:  # noqa: BLE001
            return not_supported(f"同じ時刻の 3 行を bars.csv にして load_bars -> {type(exc).__name__}: {str(exc)[:160]}")
        # round r6-1 (same root as critic i0-r5-02): the scene measures what a strategy RECEIVES; this tool has no strategy that events are delivered to, so the value the tool holds is reported as evidence, not graded
        return not_supported(f"{self.what}(戦略に事象を渡す口が無い)。試したこと: 同じ時刻の 3 行を load_bars で読んだ BarSeries の順 {[b.close for b in s['X']]}")
