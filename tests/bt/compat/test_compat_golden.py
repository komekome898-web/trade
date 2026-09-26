"""The new engine's compatibility mouth against the OLD engine's outputs
(item 4, old item 14: 「確認 = 旧の試験 8 本の全場面 + 種つきの乱数の場面での旧と新の突き合わせ
(一致しなければ通過にしない)」「以後は新がそれと一致することを試験で見る」).

golden/old_engine_golden.json was made by golden/make_golden.py with the old
engine (src/bot/backtest/, before any replacement): 1008 grid scenes (every
combination of the old options, golden/compat_golden_scenes.py) + 3 edge scenes, 400 metric
cases, 400 split cases. Every output is compared as JSON text (a float's
repr), i.e. bit for bit, not within a tolerance.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE / "golden"))

import compat_golden_scenes as S  # noqa: E402
from compat_golden_run import frame, run  # noqa: E402

import bot.bt.compat.engine as NEW  # noqa: E402
from bot.bt.compat import metrics as NEW_M  # noqa: E402
from bot.bt.compat import walk_forward as NEW_W  # noqa: E402

GOLDEN = json.loads((HERE / "golden" / "old_engine_golden.json").read_text(encoding="utf-8"))


def _old_engine_present() -> bool:
    import bot.backtest.engine as E
    return E.run_backtest.__module__ == "bot.backtest.engine"


def _j(x) -> str:
    return json.dumps(x, sort_keys=True)


def test_the_golden_file_says_what_made_it():
    m = GOLDEN["made_with"]
    assert m["grid_cells"] == len(S.grid()) == 2 * 2 * 7 * 2 * 3 * 2 * 3
    assert len(GOLDEN["bars"]) == len(S.grid()) + len(S.EDGE_SCENES)
    assert len(m["old_source_sha256"]) == 3
    if _old_engine_present():  # while the old engine is still there, the golden is of THIS old engine
        for name, sha in m["old_source_sha256"].items():
            assert hashlib.sha256((REPO / "src" / "bot" / "backtest" / name).read_bytes()).hexdigest() == sha, name


def test_the_generator_still_makes_the_recorded_inputs():
    made = S.scenes() + S.EDGE_SCENES
    for rec, sc in zip(GOLDEN["bars"], made):
        assert _j(rec["scene"]) == _j(sc)


def test_the_golden_scenes_are_not_vacuous():
    """Every exit reason and the missed-fill count occur, so the comparison sees each path."""
    reasons, missed = set(), 0
    for rec in GOLDEN["bars"]:
        out = rec["old"]
        assert "refused" not in out
        reasons |= {e.get("reason") for e in out["trade_log"] if e["side"].startswith("CLOSE")}
        missed += out["missed_fills"]
    assert reasons == {"signal", "stop_loss", "take_profit", "maker_tp", "time_exit", "wick_stop"}
    assert missed > 0


CHUNK = 64


@pytest.mark.parametrize("start", range(0, len(GOLDEN["bars"]), CHUNK))
def test_bar_scenes_match_the_old_engine_bit_for_bit(start):
    for rec in GOLDEN["bars"][start:start + CHUNK]:
        try:
            got = run(NEW, rec["scene"])
        except ValueError as exc:
            got = {"refused": str(exc)}
        assert _j(got) == _j(rec["old"]), rec["scene"]["cell"]


def test_the_equity_curve_keeps_the_candles_index():
    sc = GOLDEN["bars"][5]["scene"]
    fr = frame(sc["bars"])
    from compat_golden_run import Script
    res = NEW.run_backtest(Script(sc["signals"], sc["min_history"]), fr,
                           **{**sc["options"], "costs": NEW.CostModel(**sc["options"]["costs"])})
    assert res.equity_curve.index.equals(fr.index)


@pytest.mark.parametrize("start", range(0, 400, 100))
def test_metric_cases_match_the_old_module(start):
    for rec in GOLDEN["metrics"][start:start + 100]:
        c = rec["input"]
        m = NEW_M.compute_metrics(c["trade_pnls"], pd.Series(c["equity"], dtype=float), c["total_fees"],
                                  periods_per_year=c["periods_per_year"])
        assert _j(m.as_dict()) == _j(rec["old"])


def test_split_cases_match_the_old_module():
    for rec in GOLDEN["splits"]:
        c = rec["input"]
        df = pd.DataFrame({"close": [float(i) for i in range(c["rows"])]})
        try:
            sp = NEW_W.split_data(df, train_frac=c["train_frac"], val_frac=c["val_frac"])
            got = {k: [int(x) for x in getattr(sp, k)["close"].tolist()] for k in ("training", "validation", "out_of_sample")}
        except ValueError as exc:
            got = {"refused": str(exc)}
        assert got == rec["old"], c


@pytest.mark.skipif(not _old_engine_present(), reason="the old engine has been replaced; the golden file is the record")
def test_fresh_seeded_scenes_match_the_live_old_engine():
    """Seeds the golden file does not hold (another base), every grid cell, against the old engine itself."""
    import bot.backtest.engine as OLD
    for k, cell in enumerate(S.grid()):
        sc = S.make_scene(777_000 + k, cell)
        outs = []
        for eng in (OLD, NEW):
            try:
                outs.append(_j(run(eng, sc)))
            except ValueError as exc:
                outs.append(_j({"refused": str(exc)}))
        assert outs[0] == outs[1], cell


def _public(mod):
    return {n: v for n, v in vars(mod).items() if not n.startswith("_") and getattr(v, "__module__", None) == mod.__name__}


@pytest.mark.skipif(not _old_engine_present(), reason="the old engine has been replaced")
@pytest.mark.parametrize("name", ["engine", "metrics", "walk_forward"])
def test_every_public_name_of_the_old_module_is_in_the_mouth_with_the_same_signature(name):
    import importlib
    old = importlib.import_module(f"bot.backtest.{name}")
    new = importlib.import_module(f"bot.bt.compat.{name}")
    for n, v in _public(old).items():
        assert hasattr(new, n), n
        if callable(v) and not isinstance(v, type):
            assert str(inspect.signature(getattr(new, n))) == str(inspect.signature(v)), n
        if isinstance(v, type) and hasattr(v, "__dataclass_fields__"):
            assert list(v.__dataclass_fields__) == list(getattr(new, n).__dataclass_fields__), n
            assert str(inspect.signature(getattr(new, n))) == str(inspect.signature(v)), n


@pytest.mark.parametrize("kwargs", [
    {"execution": "vwap"}, {"max_hold_bars": 0}, {"stop_mode": "trail"},
    {"stop_mode": "wick_invalidation"}, {"stop_mode": "wick_invalidation", "stop_window_bars": 2, "stop_loss_pct": 1.0},
    {"stop_window_bars": 2}, {"exit_execution": "limit"}, {"exit_execution": "maker_tp"},
    {"exit_execution": "maker_tp", "maker_tp_pct": 0.0}, {"maker_tp_pct": 1.0}, {"entry_sides": "up"},
    {"entry_mask": [True] * 3},
])
def test_refusals_match_the_old_engine(kwargs):
    """Every refusal of an option (the old engine's ValueError, the same text)."""
    sc = GOLDEN["bars"][0]["scene"]
    msgs = []
    engines = [NEW]
    if _old_engine_present():
        import bot.backtest.engine as OLD
        engines.append(OLD)
    from compat_golden_run import Script
    for eng in engines:
        with pytest.raises(ValueError) as ei:
            eng.run_backtest(Script(sc["signals"], 0), frame(sc["bars"]), **kwargs)
        msgs.append(str(ei.value))
    assert len(set(msgs)) == 1, msgs


def test_a_row_the_core_cannot_take_as_a_bar_is_refused_not_computed():
    """The one intended difference from the old engine (engine.py docstring)."""
    from compat_golden_run import Script
    fr = frame([[100.0, 101.0, 99.0, 100.0], [100.0, 99.0, 101.0, 100.0]])  # high < low
    with pytest.raises(ValueError, match="cannot be a bar event"):
        NEW.run_backtest(Script("..", 0), fr)
    fr = frame([[100.0, 101.0, 99.0, 100.0], [float("nan"), 101.0, 99.0, 100.0]])
    with pytest.raises(ValueError, match="cannot be a bar event"):
        NEW.run_backtest(Script("..", 0), fr)
