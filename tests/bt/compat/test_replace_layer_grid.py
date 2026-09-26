"""Finishing condition 3 (the old engine replaced): src/bot/backtest/ now
delegates to bot.bt.compat, and `run_backtest` is the layer
`bot.bt.compat.engine.run_backtest_as_old` in front of the compatibility
mouth (「例外は作らない」 L-407: the inputs the core does not take give the old
numbers, the core's contract unchanged).

The reference is the old engine itself: the files of src/bot/backtest/ before
the replacement, kept verbatim with their sha256 under
docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/round_3/materials/replace/
old_engine_snapshot/ (the same sha256 the golden file records). They are
loaded here as private modules, so the comparison is against the old code,
not against a description of it. Outputs are compared as JSON text (a float's
repr), i.e. bit for bit; a ValueError is compared by its text (the mouth
raises a ValueError subclass with the old text), any other exception by its
class name and text.

The lattice (built from the row's fields and the old options, not from the
layer's branches):
  malformed-row shape (27): each of open/high/low/close set to NaN, +inf,
      -inf, 0, a negative price (20); high below low; open above high; open
      below low; close above high; close below low (5); volume NaN; volume
      negative (2)
  x position (4): first bar, a middle bar (by seed), last bar, every bar
  x option cell: the golden grid (execution x allow_short x protective exit
      x max_hold_bars x entry_sides x entry_mask x swap sign = 1008 cells,
      tests/bt/compat/golden/compat_golden_scenes.py) with the position
      cycling by cell, and every position on the 28 cells execution x
      allow_short x protective exit
  odd options on valid rows: order_notional 0 / negative / NaN / huge /
      numpy scalars, initial equity 0 / negative / NaN / inf, bar_seconds 0 /
      negative / NaN, swap NaN / huge, maker_timeout 0 / negative / 2.5,
      stop_loss / take_profit / maker_tp 0 / negative / >= 100 / NaN,
      max_hold / stop_window 2.5, costs that make a taker price <= 0, a
      negative fee, a negative slippage, allow_short 1 / "yes"
  CostModel subclasses overriding each of buy_price / sell_price / fee /
      maker_fee
  evaluate_on_splits on valid and malformed rows
Not in the lattice (named here, per the adversarial-test rule): non-numeric
columns (strings, objects), missing columns, candles that are not a
DataFrame, an unsorted or duplicate index, a strategy that raises, bar counts
other than the golden N_BARS (0, 1 and min_history beyond the bars are in the
golden edge scenes and run through the layer below).
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import inspect
import json
import random
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SNAP = REPO / "docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/round_3/materials/replace/old_engine_snapshot"
sys.path.insert(0, str(HERE / "golden"))

import compat_golden_scenes as S  # noqa: E402
from compat_golden_run import Script, run  # noqa: E402

import bot.backtest.engine as NEW_E  # noqa: E402
import bot.backtest.metrics as NEW_M  # noqa: E402
import bot.backtest.walk_forward as NEW_W  # noqa: E402
import bot.bt.compat.engine as C  # noqa: E402

GOLDEN = json.loads((HERE / "golden" / "old_engine_golden.json").read_text(encoding="utf-8"))


def _load(name: str, modname: str, bind: dict):
    """Exec a snapshot file as the private module `modname`, with the old
    package names it imports bound to other snapshot modules while it runs."""
    spec = importlib.util.spec_from_file_location(modname, SNAP / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[modname] = mod
    saved = {k: sys.modules.get(k) for k in bind}
    sys.modules.update(bind)
    try:
        spec.loader.exec_module(mod)
    finally:
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v
    return mod


OLD_M = _load("metrics", "_old_snapshot_metrics", {})
OLD_E = _load("engine", "_old_snapshot_engine", {"bot.backtest.metrics": OLD_M})
OLD_W = _load("walk_forward", "_old_snapshot_walk_forward", {"bot.backtest.engine": OLD_E})


def _frame(bars):
    idx = pd.date_range("2026-01-05", periods=len(bars), freq="min", tz="UTC")
    return pd.DataFrame({"open": [b[0] for b in bars], "high": [b[1] for b in bars], "low": [b[2] for b in bars],
                         "close": [b[3] for b in bars],
                         "volume": [b[4] if len(b) > 4 else 1.0 for b in bars]}, index=idx)


def _run(engine, scene: dict) -> dict:
    opts = dict(scene["options"])
    if isinstance(opts.get("costs"), dict):
        opts["costs"] = engine.CostModel(**opts["costs"])
    res = engine.run_backtest(Script(scene["signals"], scene["min_history"]), _frame(scene["bars"]), **opts)
    return {"trade_log": [dict(e) for e in res.trade_log], "trade_pnls": [float(p) for p in res.trade_pnls],
            "equity": [float(x) for x in res.equity_curve.tolist()],
            "index": [str(t) for t in res.equity_curve.index],
            "metrics": dict(res.metrics.as_dict()), "missed_fills": int(res.missed_fills)}


def _out(engine, scene: dict) -> str:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            return json.dumps(_run(engine, scene), sort_keys=True)
        except ValueError as exc:
            return f"ValueError: {exc}"
        except Exception as exc:  # noqa: BLE001 -- the old engine's own exception is part of its behaviour
            return f"{type(exc).__name__}: {exc}"


# --------------------------------------------------------------------------- the snapshot is the old engine
def test_the_snapshot_is_the_old_engine_the_golden_file_was_made_from():
    rec = GOLDEN["made_with"]["old_source_sha256"]
    sums = dict(reversed(line.split()) for line in (SNAP / "SHA256SUMS").read_text().splitlines() if line.strip())
    for name, sha in rec.items():
        assert hashlib.sha256((SNAP / name).read_bytes()).hexdigest() == sha == sums[name], name


def test_the_old_modules_now_delegate_to_the_compat_package():
    assert NEW_E.run_backtest is C.run_backtest_as_old
    assert NEW_E.CostModel is C.CostModel and NEW_E.BacktestResult is C.BacktestResult
    assert NEW_W.evaluate_on_splits is C.evaluate_on_splits_as_old
    for mod in (NEW_E, NEW_M, NEW_W):
        src = Path(mod.__file__).read_text(encoding="utf-8")
        assert "for i in range(len(candles))" not in src and "def " not in src, mod.__name__



def test_the_old_arithmetic_in_the_layer_is_the_snapshot_text_line_for_line():
    """A value lattice cannot reach every boundary (a low exactly on the stop
    level, say), so the copy is also held to the snapshot's text: the same
    lines, only the function's name changed."""
    old = inspect.getsource(OLD_E.run_backtest).replace("def run_backtest(", "def _old_arithmetic(", 1)
    assert inspect.getsource(C._old_arithmetic) == old
    assert inspect.getsource(C._PendingLimit) == inspect.getsource(OLD_E._PendingLimit)
    for name in ("CostModel", "BacktestResult"):
        assert inspect.getsource(getattr(C, name)) == inspect.getsource(getattr(OLD_E, name)), name

def _public(mod):
    return {n: v for n, v in vars(mod).items() if not n.startswith("_") and getattr(v, "__module__", None) == mod.__name__}


@pytest.mark.parametrize("pair", ["engine", "metrics", "walk_forward"])
def test_every_public_name_of_the_old_module_is_there_with_the_same_signature(pair):
    old = {"engine": OLD_E, "metrics": OLD_M, "walk_forward": OLD_W}[pair]
    new = {"engine": NEW_E, "metrics": NEW_M, "walk_forward": NEW_W}[pair]
    names = _public(old)
    assert names, pair
    for n, v in names.items():
        assert hasattr(new, n), n
        if callable(v) and not isinstance(v, type):
            assert str(inspect.signature(getattr(new, n))) == str(inspect.signature(v)), n
        if isinstance(v, type) and hasattr(v, "__dataclass_fields__"):
            assert list(v.__dataclass_fields__) == list(getattr(new, n).__dataclass_fields__), n
            assert str(inspect.signature(getattr(new, n))) == str(inspect.signature(v)), n
        if isinstance(v, type):
            for m in ("buy_price", "sell_price", "fee", "maker_fee", "as_dict"):
                if hasattr(v, m):
                    assert str(inspect.signature(getattr(getattr(new, n), m))) == str(inspect.signature(getattr(v, m)))


# --------------------------------------------------------------------------- malformed rows x options
NAN, INF = float("nan"), float("inf")
FIELDS = ("open", "high", "low", "close")


def _set(field: int, value: float):
    def f(r):
        r = list(r)
        r[field] = value
        return r
    return f


def _rel(kind: str):
    def f(r):
        o, h, lo, c, v = r
        if kind == "high_below_low":
            h, lo = min(o, c, lo) - 1.0, max(o, c, h) + 1.0
        elif kind == "open_above_high":
            o = h + 1.5
        elif kind == "open_below_low":
            o = max(0.5, lo - 1.5) if lo > 1.0 else lo / 2
        elif kind == "close_above_high":
            c = h + 1.5
        elif kind == "close_below_low":
            c = max(0.5, lo - 1.5) if lo > 1.0 else lo / 2
        return [o, h, lo, c, v]
    return f


SHAPES = {}
for _k, _name in enumerate(FIELDS):
    for _label, _val in (("nan", NAN), ("pinf", INF), ("ninf", -INF), ("zero", 0.0), ("negative", -5.0)):
        SHAPES[f"{_name}_{_label}"] = _set(_k, _val)
for _kind in ("high_below_low", "open_above_high", "open_below_low", "close_above_high", "close_below_low"):
    SHAPES[_kind] = _rel(_kind)
SHAPES["volume_nan"] = _set(4, NAN)
SHAPES["volume_negative"] = _set(4, -3.0)
assert len(SHAPES) == 27
POSITIONS = ("first", "middle", "last", "all")


def _malformed(scene: dict, shape: str, pos: str, seed: int) -> dict:
    sc = copy.deepcopy(scene)
    rows = [list(b) + [1.0] for b in sc["bars"]]
    n = len(rows)
    at = {"first": [0], "middle": [random.Random(seed).randrange(1, n - 1)], "last": [n - 1],
          "all": list(range(n))}[pos]
    for i in at:
        rows[i] = SHAPES[shape](rows[i])
    sc["bars"] = rows
    return sc


def test_every_shape_is_a_row_the_core_refuses_or_a_volume_shape():
    """The shapes are the malformed rows of the lattice: every price shape is
    one the core refuses (so the layer, not the mouth, answers it)."""
    base = S.make_scene(1, S.grid()[0])
    for shape in SHAPES:
        for pos in POSITIONS:
            sc = _malformed(base, shape, pos, 7)
            route, _ = C.route_of(_frame(sc["bars"]))
            if not shape.startswith("volume"):
                assert route == "old", (shape, pos)
                with pytest.raises(ValueError, match="cannot be a bar event"):
                    C.run_backtest(Script(sc["signals"], 0), _frame(sc["bars"]))


@pytest.mark.parametrize("shape", sorted(SHAPES))
def test_malformed_rows_on_every_option_cell_give_the_old_numbers(shape):
    for k, cell in enumerate(S.grid()):
        sc = _malformed(S.make_scene(610_000 + k, cell), shape, POSITIONS[k % 4], 610_000 + k)
        assert _out(NEW_E, sc) == _out(OLD_E, sc), (shape, POSITIONS[k % 4], cell)


SMALL_CELLS = [c for c in S.grid() if c[3] is None and c[4] == "both" and c[5] == "none" and c[6] == 0.5]
assert len(SMALL_CELLS) == 28


@pytest.mark.parametrize("shape", sorted(SHAPES))
def test_malformed_rows_at_every_position_give_the_old_numbers(shape):
    for pos in POSITIONS:
        for k, cell in enumerate(SMALL_CELLS):
            sc = _malformed(S.make_scene(620_000 + k, cell), shape, pos, 620_000 + k)
            assert _out(NEW_E, sc) == _out(OLD_E, sc), (shape, pos, cell)


# --------------------------------------------------------------------------- valid rows: the core, and the old numbers
def _decimal_bars(rng: random.Random, n: int):
    rows, c = [], 1234.5
    for _ in range(n):
        o = round(c + rng.choice((0, 0, 0.1, -0.1, 0.7, -0.7, 3.3)), 1)
        cl = round(o + rng.uniform(-2, 2), 1)
        rows.append([o, round(max(o, cl) + rng.uniform(0, 1.3), 1), round(min(o, cl) - rng.uniform(0, 1.3), 1), cl])
        c = cl
    return rows


@pytest.fixture
def no_old_route(monkeypatch):
    def refuse(*a, **k):
        raise AssertionError("a valid input took the old-arithmetic route")
    monkeypatch.setattr(C, "_old_arithmetic", refuse)


CHUNK = 144


@pytest.mark.parametrize("start", range(0, len(S.grid()), CHUNK))
def test_fresh_valid_cells_run_on_the_core_and_match_the_old_engine(start, no_old_route):
    cells = S.grid()
    for k in range(start, min(start + CHUNK, len(cells))):
        sc = S.make_scene(777_000 + k, cells[k])
        if k % 2:
            sc["bars"] = _decimal_bars(random.Random(k), S.N_BARS)
        assert _out(NEW_E, sc) == _out(OLD_E, sc), cells[k]



def _critic_decimal_module():
    """The critic's decimal-price cells (tests/bt/critic/item_4/
    test_i4r1_compat_decimal_prices.py) compare the mouth with the LIVE old
    engine and skip once it is replaced; their scenes are read from that file
    (not copied) and compared here with the snapshot instead."""
    path = REPO / "tests/bt/critic/item_4/test_i4r1_compat_decimal_prices.py"
    spec = importlib.util.spec_from_file_location("_critic_i4r1_decimal", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


_CRITIC_DEC = _critic_decimal_module()


@pytest.mark.parametrize("start", range(0, len(_CRITIC_DEC.CELLS), _CRITIC_DEC.CHUNK))
def test_the_critic_decimal_price_cells_match_the_old_engine_snapshot(start, no_old_route):
    cells = _CRITIC_DEC.CELLS
    for k in range(start, min(start + _CRITIC_DEC.CHUNK, len(cells))):
        sc = _CRITIC_DEC._scene(k, cells[k])
        assert _out(NEW_E, sc) == _out(OLD_E, sc), cells[k]

@pytest.mark.parametrize("start", range(0, len(GOLDEN["bars"]), 128))
def test_the_golden_scenes_through_the_replaced_module_on_the_core(start, no_old_route):
    for rec in GOLDEN["bars"][start:start + 128]:
        try:
            got = run(NEW_E, rec["scene"])
        except ValueError as exc:
            got = {"refused": str(exc)}
        assert json.dumps(got, sort_keys=True) == json.dumps(rec["old"], sort_keys=True), rec["scene"]["cell"]


ODD = {"order_notional_jpy": [0.0, -3000.0, NAN, 1e308, np.float64(2500.0), np.int64(3000)],
       "initial_equity_jpy": [0.0, -1.0, NAN, INF],
       "bar_seconds": [0.0, -60.0, NAN], "swap_daily_pct": [NAN, 1e6], "maker_timeout_bars": [0, -2, 2.5],
       "stop_loss_pct": [0.0, -1.0, 150.0, NAN, np.float64(1.0)], "take_profit_pct": [0.0, -1.0, 150.0, NAN],
       "max_hold_bars": [2.5], "stop_window_bars": [2.5],
       "costs": [{"taker_fee_pct": 0.1, "maker_fee_pct": 0.1, "slippage_pct": 60.0, "spread_pct": 100.0},
                 {"taker_fee_pct": 0.1, "maker_fee_pct": 0.1, "slippage_pct": -150.0, "spread_pct": 0.0},
                 {"taker_fee_pct": -200.0, "maker_fee_pct": 0.1, "slippage_pct": 0.0, "spread_pct": 0.0},
                 {"taker_fee_pct": 0.1, "maker_fee_pct": 0.1, "slippage_pct": -0.2, "spread_pct": 0.0},
                 {"taker_fee_pct": NAN, "maker_fee_pct": 0.1, "slippage_pct": 0.0, "spread_pct": 0.0}],
       "allow_short": [1, "yes"], "maker_tp_pct": [NAN, -1.0, 150.0], "exit_execution": ["maker_tp"]}


@pytest.mark.parametrize("key", sorted(ODD))
def test_odd_option_values_give_the_old_numbers(key):
    cells = S.grid()
    for v in ODD[key]:
        for k in range(0, len(cells), 7):
            sc = copy.deepcopy(S.make_scene(900_000 + k, cells[k]))
            sc["options"][key] = v
            assert _out(NEW_E, sc) == _out(OLD_E, sc), (key, v, cells[k])


# --------------------------------------------------------------------------- CostModel subclasses
def _subclass(base, method: str):
    def buy_price(self, ref_price):
        return ref_price * 1.003 + 0.25

    def sell_price(self, ref_price):
        return ref_price * 0.997 - 0.25

    def fee(self, notional):
        return 0.5 + notional * 0.0001

    def maker_fee(self, notional):
        return -0.1

    return type(f"Custom_{method}", (base,), {method: locals()[method]})


@pytest.mark.parametrize("method", ["buy_price", "sell_price", "fee", "maker_fee"])
def test_a_cost_model_subclass_with_its_own_method_gives_the_old_numbers(method):
    for k, cell in enumerate(SMALL_CELLS + [c for c in S.grid() if c[1] and c[4] == "short"][:28]):
        sc = S.make_scene(630_000 + k, cell)
        cdict = sc["options"]["costs"]
        outs = []
        for eng in (NEW_E, OLD_E):
            s2 = copy.deepcopy(sc)
            s2["options"]["costs"] = _subclass(eng.CostModel, method)(**cdict)
            outs.append(_out(eng, s2))
        assert outs[0] == outs[1], (method, cell)
        assert C.route_of(_frame(sc["bars"]), _subclass(C.CostModel, method)(**cdict))[0] == "old"


# --------------------------------------------------------------------------- the strategy is called as the old engine calls it
class _Counting(Script):
    calls = 0

    def on_candles(self, candles):
        type(self).calls += 1
        return super().on_candles(candles)


@pytest.mark.parametrize("malformed", [False, True])
def test_the_strategy_is_called_as_often_as_the_old_engine_calls_it(malformed):
    """The route is chosen before the strategy is called: no second pass."""
    for k, cell in enumerate(SMALL_CELLS):
        sc = S.make_scene(640_000 + k, cell)
        if malformed:
            sc = _malformed(sc, "high_below_low", POSITIONS[k % 4], k)
        counts = []
        for eng in (NEW_E, OLD_E):
            _Counting.calls = 0
            opts = dict(sc["options"], costs=eng.CostModel(**sc["options"]["costs"]))
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                try:
                    eng.run_backtest(_Counting(sc["signals"], sc["min_history"]), _frame(sc["bars"]), **opts)
                except ValueError:
                    pass
            counts.append(_Counting.calls)
        assert counts[0] == counts[1], cell


# --------------------------------------------------------------------------- evaluate_on_splits
class _ParamScript(Script):
    def __init__(self, params: dict):
        super().__init__(params["signals"], params["min_history"])


def _splits_out(W, params, bars) -> str:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            res = W.evaluate_on_splits(_ParamScript, params, _frame(bars), costs=W.CostModel(0.1, 0.05, 0.02, 0.04))
        except ValueError as exc:
            return f"ValueError: {exc}"
    return json.dumps({k: {"log": r.trade_log, "eq": [float(x) for x in r.equity_curve.tolist()],
                           "m": r.metrics.as_dict(), "miss": r.missed_fills} for k, r in res.items()}, sort_keys=True)


@pytest.mark.parametrize("shape", [None, "high_below_low", "close_nan", "open_zero", "low_negative"])
def test_evaluate_on_splits_gives_the_old_numbers(shape):
    for k in range(12):
        sc = S.make_scene(650_000 + k, S.grid()[k * 83])
        if shape:
            sc = _malformed(sc, shape, POSITIONS[k % 4], k)
        params = {"signals": sc["signals"], "min_history": sc["min_history"]}
        assert _splits_out(NEW_W, params, sc["bars"]) == _splits_out(OLD_W, params, sc["bars"]), (shape, k)
