#!/usr/bin/env bash
# Periodic multi-source data collection (systemd timer target).
# bitFlyer executions + external leader markets, incremental and read-only.
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PY:-.venv/bin/python}"

"$PY" scripts/fetch_history.py
"$PY" scripts/fetch_external.py --days 2 --swing-days 30
