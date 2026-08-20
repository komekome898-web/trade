#!/usr/bin/env bash
# Setup for home PC / Raspberry Pi (Linux). Creates a venv, installs the bot,
# prepares .env, and runs the test suite. Sends NO orders and needs no API key.
set -euo pipefail

cd "$(dirname "$0")/.."

echo "== Python check =="
PYTHON="${PYTHON:-python3}"
if ! "$PYTHON" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'; then
    echo "ERROR: Python 3.11+ required (found: $("$PYTHON" --version 2>&1))" >&2
    echo "On Raspberry Pi OS / Debian: sudo apt install python3.11 python3.11-venv" >&2
    exit 1
fi
"$PYTHON" --version

echo "== Virtualenv =="
if [ ! -d .venv ]; then
    "$PYTHON" -m venv .venv
fi
. .venv/bin/activate

echo "== Install =="
pip install --upgrade pip -q
pip install -e ".[dev]" -q

echo "== .env =="
if [ ! -f .env ]; then
    cp .env.example .env
    chmod 600 .env
    echo "Created .env from template. Edit it to add your bitFlyer API key"
    echo "(read + trade permissions only, NO withdrawal permission)."
else
    echo ".env already exists, leaving it untouched."
fi

echo "== Tests =="
python -m pytest

echo ""
echo "Setup complete. Next steps:"
echo "  1. Edit .env (API key, optional DISCORD_WEBHOOK_URL)"
echo "  2. .venv/bin/python scripts/check_api.py     # read-only API check"
echo "  3. .venv/bin/python scripts/fetch_history.py # start accumulating data"
echo "  4. See docs/OPERATIONS.md for systemd installation (24h operation)"
