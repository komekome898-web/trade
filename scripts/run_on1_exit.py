"""ON1 exit job: 8:40 成行 sell (返済) of the single micro long.

Scheduled at 8:35 on weekdays (docs/OPERATIONS.md §5.1).  See
bot/jpx/on1_executor.py for why this is a plain 成行 and not 寄成 — 寄成 does not
exist in the kabusapi futures FrontOrderType table.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from bot.jpx.on1_executor import EXIT, build_executor           # noqa: E402
from bot.jpx.run_lock import RunLock, LockBusy                   # noqa: E402


def main() -> int:
    try:
        with RunLock(ROOT / "data" / "on1_live" / f"{EXIT}.lock"):
            executor = build_executor(ROOT)
            outcome = executor.run_exit()
    except LockBusy as exc:
        print(f"run_on1_exit: another run holds the lock ({exc}); doing nothing")
        return 0
    print(f"run_on1_exit: {outcome} (live={executor.live}: {executor.live_reason})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
