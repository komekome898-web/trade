#!/usr/bin/env python3
"""Start the bot in PAPER mode regardless of environment (extra safety wrapper)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

os.environ["PAPER_MODE"] = "true"
os.environ["LIVE_MODE"] = "false"

from bot.main import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
