"""ETF measurement STATE_UNKNOWN reconciliation. READ-ONLY, run by a human.

Not scheduled: STATE_UNKNOWN blocks every order for BOTH symbols until it is
resolved, and resolving it is an operator action (CLAUDE.md §1, PREREG §6 S2).
The executor is handed a `QueryOnlyKabu`, which exposes /orders and /positions
and nothing else, so this path structurally cannot place an order.

Positive evidence only: when the account does not prove what happened, the state
stays STATE_UNKNOWN and a human decides.

The same read-only view is used to finalise any round trip whose fills have
become visible, so running this after an incident also brings the ledger up to
date without sending anything.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from bot.jpx.etf_auction_executor import (                       # noqa: E402
    STATE_DIRNAME, build_etf_executor,
)
from bot.jpx.kabu_client import QueryOnlyKabu                    # noqa: E402
from bot.jpx.run_lock import LockBusy, RunLock                   # noqa: E402


def main() -> int:
    try:
        with RunLock(ROOT / STATE_DIRNAME / "reconcile.lock"):
            executor = build_etf_executor(ROOT)
            query = QueryOnlyKabu(executor.client)
            outcomes = executor.reconcile(query)
            rows = executor.finalize_pending(query)
    except LockBusy as exc:
        print(f"run_etf_measure_reconcile: another run holds the lock ({exc}); "
              "doing nothing")
        return 0
    print(f"run_etf_measure_reconcile: {outcomes}")
    print(f"run_etf_measure_reconcile: {len(rows)} round trip(s) finalised into "
          f"{executor.ledger_path}")
    if any(v == "unresolved" for v in outcomes.values()):
        print("run_etf_measure_reconcile: STATE_UNKNOWN stands. Check the account "
              "by hand, then edit data/etf_measure/state_<symbol>.json deliberately.")
    if executor.pause.is_paused():
        print(f"run_etf_measure_reconcile: PAUSED -- {executor.pause.reason()}. "
              "This does not auto-resume; clear data/etf_measure/paused.json only "
              "after the cause is understood and the owner agrees.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
