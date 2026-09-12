"""ETF measurement exit job: 寄成 (FrontOrderType 13) SELL of the one long.

Scheduled at 08:40 on weekdays (docs/OPERATIONS_JPX.md §5.2), before the 9:00
opening auction and deliberately 5 minutes after the ON1 exit job so two jobs
never hit the same kabuステーション at the same minute.

Cash sell only: the payload is built with `CashMargin: 1`, `DelivType: 0` and
`FundType` = two half-width spaces, and it is only ever built as the close of
the single long this executor opened.  If the account does not hold exactly
that one long, the job records an alert and orders NOTHING (fail-close).

DRY RUN unless all three of `config/etf_measure.yaml: enabled` + `live_ack` and
env `ETF_EXEC_LIVE` are set: the payload that WOULD be sent is printed here and
written to data/etf_measure/events.jsonl, and nothing reaches kabuステーション.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from bot.jpx.etf_auction_executor import (                       # noqa: E402
    EXIT, STATE_DIRNAME, build_etf_executor,
)
from bot.jpx.run_lock import LockBusy, RunLock                   # noqa: E402


def main() -> int:
    try:
        with RunLock(ROOT / STATE_DIRNAME / f"{EXIT}.lock"):
            executor = build_etf_executor(ROOT)
            outcomes = executor.run_exit_all()
    except LockBusy as exc:
        print(f"run_etf_measure_exit: another run holds the lock ({exc}); "
              "doing nothing")
        return 0
    print(f"run_etf_measure_exit: {outcomes} "
          f"(live={executor.live}: {executor.live_reason})")
    if not executor.live:
        for record in [r for r in executor.emitted
                       if r.get("event") == "dry_run_order" and r.get("job") == EXIT]:
            print(f"run_etf_measure_exit: WOULD send {record['symbol']}: "
                  f"{json.dumps(record['payload'], ensure_ascii=False)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
