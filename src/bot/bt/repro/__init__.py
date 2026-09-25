"""Item 3 (old item 8): reproducibility -- run records, content-hash run
ids, the automatic two-execution check, `backtest_runs/<id>/`.

Fixed requirements: docs/DISCUSSIONS/2026-09-23_backtest_env/item_3/REQUIREMENTS.md
(C3-7 .. C3-10, C3-15). Tests: tests/bt/item_3/.

  runner      plan_run / run / check_reproducible (see its docstring)
  code_state  git HEAD and the diff hash of the code scope; the version string
  fixed       the fixed procedures for 動作確認 runs (time-only legs, seeded
              random, and an unseeded one that the check must catch)
"""
from .code_state import CODE_SCOPE, REPO, code_state, version
from .errors import NotReproducibleError, ReproError
from .fixed import SETUP_KINDS, FixedSetup, parse_config
from .runner import DEFAULT_RUNS_DIR, DataInput, ReproCheck, RunPlan, RunResult, canonical, check_reproducible, plan_run, run

__all__ = ["CODE_SCOPE", "DEFAULT_RUNS_DIR", "DataInput", "FixedSetup", "NotReproducibleError", "REPO", "ReproCheck", "ReproError",
           "RunPlan", "RunResult", "SETUP_KINDS", "canonical", "check_reproducible", "code_state", "parse_config",
           "plan_run", "run", "version"]
