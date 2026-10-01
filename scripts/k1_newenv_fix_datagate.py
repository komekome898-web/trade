"""Private pytest plugin / import hook of the k1 env-fixes worker (2026-09-27).

Refuses, by a Python audit hook, every open() of a file under the repository's
data roots (backtest_data, data, paper_logs) except the data the delegation
allows: BitMEX 1-second bars 2017-2019, the stage-A folded bars, two consumed
bitFlyer files of 2026-08-21 (ALLOW_FILES, round 2), and the seal
ledger (backtest_data/phase2_sealed/*, not market data; the data layer reads it
on every load). A refused open raises PermissionError (an OSError) and is
logged to $K1FIX_DATAGATE_LOG, so a test that needs other data fails visibly
and nothing forbidden is read.

Usage (tests): PYTHONPATH=scripts:src K1FIX_DATAGATE_LOG=<file> python -m pytest ... -p k1_newenv_fix_datagate
Usage (a script): import k1_newenv_fix_datagate first (the hook is installed at import).
The worker ran the same file from its scratch folder under the name k1fix_datagate.
"""
import os
import sys

REPO = os.path.realpath(os.environ.get("K1FIX_REPO", "/home/user/trade"))
ROOTS = tuple(os.path.join(REPO, r) + os.sep for r in ("backtest_data", "data", "paper_logs"))
ALLOW = tuple(os.path.join(REPO, r) + os.sep for r in (
    "backtest_data/bitmex_trade_1s_XBTUSD/2017", "backtest_data/bitmex_trade_1s_XBTUSD/2018",
    "backtest_data/bitmex_trade_1s_XBTUSD/2019", "backtest_data/k1_newenv_a_20260927",
    "backtest_data/phase2_sealed"))
# single files allowed in round 2 of the env fixes (2026-09-30) as the real-data input of the tests that ran on
# unconsumed data before (tests/bt/item_2/test_i2_real_data_check.py, tests/bt/item_4/test_i4_real_data_smoke.py):
# consumed (docs/DATA_CONSUMPTION_LOG.md §1: 2026-08-20..08-27 board / executions, 選択に消費(重度), and the
# auto_bitflyer_executions_20260905 row, ④-1 経費の床), rows of 2026-08-21 (before 2026-08-28), in no SEALED.json.
# The reason is written in docs/PHASE2/K1/NEWENV_A/FIXES.md §11.
ALLOW_FILES = frozenset(os.path.join(REPO, r) for r in (
    "backtest_data/auto_bitflyer_executions_20260905/board_top5_20260821.csv.gz",
    "backtest_data/auto_bitflyer_executions_20260905/executions_20260821.csv.gz"))
LOG = os.environ.get("K1FIX_DATAGATE_LOG")
_busy = [False]


def _hook(event, args):
    if event != "open" or _busy[0]:
        return
    path = args[0]
    if isinstance(path, int) or path is None:
        return
    try:
        p = os.fsdecode(path)
    except Exception:
        return
    _busy[0] = True
    try:
        real = os.path.realpath(p)
    finally:
        _busy[0] = False
    if not real.startswith(ROOTS):
        return
    if real.startswith(ALLOW) or real in ALLOW_FILES:
        return
    if LOG:
        _busy[0] = True
        try:
            with open(LOG, "a", encoding="utf-8") as fh:
                fh.write(real + "\n")
        finally:
            _busy[0] = False
    raise PermissionError(f"k1fix datagate: {real} is outside the data the delegation allows")


sys.addaudithook(_hook)


def pytest_configure(config):  # noqa: D401 - pytest plugin entry (the hook is installed at import)
    pass
