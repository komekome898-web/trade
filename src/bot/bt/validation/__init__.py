"""Item 3 (old item 7): validation and statistics for backtests.

Fixed requirements: docs/DISCUSSIONS/2026-09-23_backtest_env/item_3/REQUIREMENTS.md
(C3-1 .. C3-6). Tests: tests/bt/item_3/.

  splits         calendar Train / Val / OOS and walk-forward on calendar days of a zone
  purge          purge and embargo, CPCV (splits and paths)
  bootstrap      block bootstrap intervals (circular / moving / stationary)
  power          MDE and the verdict 陰性 / 不明 / 陽性 (no MDE -> never 陰性)
  overfit        deflated Sharpe, PBO (CSCV)
  ledger         the iteration ledger ITER (append-only, hash-chained)
  sealed_access  the sealed window only through load_sealed's four gates;
                 the ordinary read refuses sealed rows

Numbers come from numpy, pandas and the standard library only (no scipy).
"""
from .bootstrap import METHODS as BOOTSTRAP_METHODS
from .bootstrap import BootstrapCI, block_bootstrap_ci, circular_block_se_of_mean
from .errors import LedgerError, SealedRefused, ValidationError
from .ledger import IterLedger, deflated_sharpe_from_ledger
from .overfit import DSR, PBO, deflated_sharpe, deflated_sharpe_of_returns, expected_max_sr, pbo, sample_moments
from .power import NEGATIVE, POSITIVE, UNKNOWN, Verdict, mde, verdict
from .purge import CPCV, CPCVSplit, Purged, cpcv, group_bounds, purged_train
from .sealed_access import read_sealed, read_table
from .splits import (WF_MODES, CalendarSplit, Fold, FoldEval, Part, calendar_split, day_start_ns, walk_forward,
                     walk_forward_eval)

__all__ = ["BOOTSTRAP_METHODS", "BootstrapCI", "CPCV", "CPCVSplit", "CalendarSplit", "DSR", "Fold", "FoldEval",
           "IterLedger", "LedgerError", "NEGATIVE", "PBO", "POSITIVE", "Part", "Purged", "SealedRefused", "UNKNOWN",
           "ValidationError", "Verdict", "WF_MODES", "block_bootstrap_ci", "calendar_split", "circular_block_se_of_mean",
           "cpcv", "day_start_ns", "deflated_sharpe", "deflated_sharpe_from_ledger", "deflated_sharpe_of_returns",
           "expected_max_sr", "group_bounds", "mde", "pbo", "purged_train", "read_sealed", "read_table",
           "sample_moments", "verdict", "walk_forward", "walk_forward_eval"]
