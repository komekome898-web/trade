"""The old engine's 8 test files, unchanged, run against the new engine's
compatibility mouth (item 4, old item 14: 「使う 12 本と試験 8 本は 1 行も変えずに新エンジンで
動き、旧の試験 8 本が全部そのまま通ることを「完全上位互換」の確認にする」).

Before the last stage replaces src/bot/backtest/, this is the dry run of it:
a child process binds the names bot.backtest.engine / metrics / walk_forward
to bot.bt.compat.engine / metrics / walk_forward (sys.modules) and runs
pytest on the 8 files as they are. After the last stage the 8 files import
the replaced modules directly and the same child run still applies.
The 12 scripts that import the old names are checked for importability the
same way (import only; they are research scripts, not run here).
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OLD_TESTS = ["tests/test_backtest.py", "tests/test_engine_maker_exit.py", "tests/test_maker_execution.py",
             "tests/test_max_hold.py", "tests/test_qa_pipeline_known_answer.py", "tests/test_short_margin.py",
             "tests/test_tp_sl.py", "tests/test_wick_stop.py"]
IMPORTERS = ["scripts/research_basis.py", "scripts/research_anchor.py", "scripts/research_fx.py", "scripts/run_backtest.py",
             "scripts/research_tournament.py", "scripts/qa/pipeline_known_answer_taker.py",
             "scripts/research_legacy_elements.py", "scripts/research_mainbot_exits.py",
             "scripts/research_user_strategies.py", "scripts/research_anchor_v2.py", "scripts/validate_composite.py",
             "scripts/research_signals.py"]
BIND = """
import sys
import bot.backtest
import bot.bt.compat.engine as E, bot.bt.compat.metrics as M, bot.bt.compat.walk_forward as W
sys.modules["bot.backtest.engine"], sys.modules["bot.backtest.metrics"], sys.modules["bot.backtest.walk_forward"] = E, M, W
bot.backtest.engine, bot.backtest.metrics, bot.backtest.walk_forward = E, M, W
"""


def _env():
    return {**os.environ, "PYTHONPATH": str(REPO / "src")}


def test_the_eight_old_test_files_exist_and_are_the_ones_named():
    for t in OLD_TESTS:
        assert (REPO / t).is_file(), t


def test_the_eight_old_test_files_pass_unchanged_against_the_mouth():
    code = BIND + f"import pytest\nsys.exit(pytest.main(['-p', 'no:cacheprovider', *{OLD_TESTS!r}]))\n"
    r = subprocess.run([sys.executable, "-c", code], cwd=REPO, env=_env(), capture_output=True, text=True, timeout=1800)
    tail = (r.stdout + r.stderr)[-3000:]
    assert r.returncode == 0, tail
    assert " passed" in tail and "failed" not in tail, tail


def test_the_twelve_importers_import_against_the_mouth():
    code = BIND + (
        "import importlib.util, os\n"
        f"for p in {IMPORTERS!r}:\n"
        "    spec = importlib.util.spec_from_file_location('m_' + os.path.basename(p)[:-3], p)\n"
        "    mod = importlib.util.module_from_spec(spec)\n"
        "    sys.modules[spec.name] = mod\n"
        "    sys.argv = [p, '--help']\n"
        "    # import only: the module body runs, its __main__ block does not\n"
        "    spec.loader.exec_module(mod)\n"
        "    for name in ('run_backtest', 'CostModel', 'split_data', 'evaluate_on_splits'):\n"
        "        if hasattr(mod, name):\n"
        "            assert getattr(mod, name).__module__.startswith('bot.bt.compat'), (p, name)\n"
        "print('ok', len(" + repr(IMPORTERS) + "))\n")
    r = subprocess.run([sys.executable, "-c", code], cwd=REPO, env=_env(), capture_output=True, text=True, timeout=600)
    assert r.returncode == 0 and "ok 12" in r.stdout, (r.stdout + r.stderr)[-3000:]
