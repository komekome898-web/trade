"""One best-effort atomic text write, shared by every state checkpoint.

Three files are rewritten while the bot trades — `logs/status.json`
(monitoring/status.py), `data/overlay_state.json` (strategy/composite.py) and
`data/paper_state.json` (portfolio/persistence.py). All three are telemetry or
bookkeeping, never an authorisation, so a failed write has to degrade quietly:
it must never raise into the trading loop, and it must never leave a truncated
file behind for the next boot (or the dashboard) to read.

The Windows detail this exists for: `os.replace` fails with PermissionError
while another process — the dashboard polls these files every few seconds —
briefly holds the destination open. Retry a few times, then fall back to
writing the destination directly (a rewrite that is not atomic beats no
checkpoint at all), and clean the temp file up so a failed replace does not
leak one per attempt.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

RETRIES = 5
RETRY_SLEEP_SEC = 0.05


def atomic_write_text(path: str | Path, text: str) -> bool:
    """Write `text` to `path` via a temp file + replace. Returns whether the
    bytes reached `path`; NEVER raises."""
    path = Path(path)
    tmp = path.with_suffix(".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(text, encoding="utf-8")
        for _ in range(RETRIES):
            try:
                os.replace(tmp, path)
                return True
            except PermissionError:
                time.sleep(RETRY_SLEEP_SEC)
        path.write_text(text, encoding="utf-8")
        return True
    except OSError:
        return False
    finally:
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass
