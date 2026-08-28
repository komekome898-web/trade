"""ON1 STATE_UNKNOWN reconciliation. READ-ONLY, run by a human.

Not scheduled: STATE_UNKNOWN blocks every ON1 order until it is resolved, and
resolving it is an operator action (CLAUDE.md §1).  The executor is handed a
`QueryOnlyKabu`, which exposes /orders and /positions and nothing else, so this
path structurally cannot place an order.

Positive evidence only: when the account does not prove what happened, the state
stays STATE_UNKNOWN and a human decides.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from bot.jpx.kabu_client import QueryOnlyKabu                    # noqa: E402
from bot.jpx.on1_executor import build_executor                  # noqa: E402
from bot.jpx.run_lock import RunLock, LockBusy                   # noqa: E402


def main() -> int:
    try:
        with RunLock(ROOT / "data" / "on1_live" / "reconcile.lock"):
            executor = build_executor(ROOT)
            outcome = executor.reconcile(QueryOnlyKabu(executor.client))
    except LockBusy as exc:
        print(f"run_on1_reconcile: another run holds the lock ({exc}); doing nothing")
        return 0
    print(f"run_on1_reconcile: {outcome}")
    if outcome == "unresolved":
        print("run_on1_reconcile: STATE_UNKNOWN stands. Check the account by hand, "
              "then edit data/on1_live/state.json deliberately.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
