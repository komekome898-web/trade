#!/usr/bin/env bash
# Periodic multi-source data collection (systemd timer target).
# bitFlyer executions + external leader markets, incremental and read-only.
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PY:-.venv/bin/python}"

"$PY" scripts/fetch_history.py
"$PY" scripts/fetch_external.py --days 2 --swing-days 30
"$PY" scripts/record_oi.py
# Board top-10 daily extraction (EXEC_FLOOR_PREREG.md sec7 row 1, owner
# L-098) + funding-rate/basis daily log (row 2). See docs/OWNER_PROCEDURES.md
# P11/P12. Both incremental/idempotent; public data only.
"$PY" scripts/extract_tape.py --board-top 10
"$PY" scripts/record_funding_basis.py
