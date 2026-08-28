"""ON1 entry job: 15:40 引成 buy, 1 Nikkei 225 micro contract.

Scheduled at 15:35 on weekdays (docs/OPERATIONS.md §5.1).  Everything that
decides whether an order is actually sent lives in bot/jpx/on1_executor.py; this
file is only the process wrapper + double-start guard.

Exit code is always 0 unless the wrapper itself failed: a skipped or refused
order is a normal, recorded outcome, not a scheduler failure.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from bot.jpx.on1_executor import ENTRY, build_executor          # noqa: E402
from bot.jpx.run_lock import RunLock, LockBusy                   # noqa: E402


def main() -> int:
    try:
        with RunLock(ROOT / "data" / "on1_live" / f"{ENTRY}.lock"):
            executor = build_executor(ROOT)
            outcome = executor.run_entry()
    except LockBusy as exc:
        print(f"run_on1_entry: another run holds the lock ({exc}); doing nothing")
        return 0
    print(f"run_on1_entry: {outcome} (live={executor.live}: {executor.live_reason})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
