"""ETF measurement entry job: 引成 (FrontOrderType 16) BUY of 1 trading unit.

Scheduled at 15:20 on weekdays (docs/OPERATIONS_JPX.md §5.2), before the 15:30
closing auction.  Everything that decides whether an order is actually sent
lives in bot/jpx/etf_auction_executor.py; this file is only the process wrapper
+ double-start guard.

DRY RUN unless all three of `config/etf_measure.yaml: enabled` + `live_ack` and
env `ETF_EXEC_LIVE` are set: in a dry run the payload that WOULD be sent is
printed here and written to data/etf_measure/events.jsonl, and nothing reaches
kabuステーション — not even the 検証 port 18081.

The run also finalises any round trip from a previous night whose fills have
become visible.  That step is READ ONLY (it is handed a `QueryOnlyKabu`) and
its failures can neither block nor permit an order.

Exit code is always 0 unless the wrapper itself failed: a skipped or refused
order is a normal, recorded outcome, not a scheduler failure.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from bot.jpx.etf_auction_executor import (                       # noqa: E402
    ENTRY, STATE_DIRNAME, build_etf_executor,
)
from bot.jpx.kabu_client import QueryOnlyKabu                    # noqa: E402
from bot.jpx.run_lock import LockBusy, RunLock                   # noqa: E402


def _finalize(executor) -> None:
    """Read-only ledger catch-up.  Never allowed to affect the trading path."""
    try:
        rows = executor.finalize_pending(QueryOnlyKabu(executor.client))
    except Exception as exc:                     # noqa: BLE001 - never fatal
        print(f"run_etf_measure_entry: ledger finalisation skipped ({exc})")
        return
    if rows:
        print(f"run_etf_measure_entry: {len(rows)} round trip(s) finalised")


def main() -> int:
    try:
        with RunLock(ROOT / STATE_DIRNAME / f"{ENTRY}.lock"):
            executor = build_etf_executor(ROOT)
            if executor.live:
                _finalize(executor)
            outcomes = executor.run_entry_all()
    except LockBusy as exc:
        print(f"run_etf_measure_entry: another run holds the lock ({exc}); "
              "doing nothing")
        return 0
    print(f"run_etf_measure_entry: {outcomes} "
          f"(live={executor.live}: {executor.live_reason})")
    if not executor.live:
        for record in _dry_run_payloads(executor):
            print(f"run_etf_measure_entry: WOULD send {record['symbol']}: "
                  f"{json.dumps(record['payload'], ensure_ascii=False)}")
    return 0


def _dry_run_payloads(executor) -> list[dict]:
    """What this run WOULD have sent, straight off the run's own event list."""
    return [r for r in executor.emitted
            if r.get("event") == "dry_run_order" and r.get("job") == ENTRY]


if __name__ == "__main__":
    sys.exit(main())
