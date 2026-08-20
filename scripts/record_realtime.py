#!/usr/bin/env python3
"""Record bitFlyer Realtime API streams (board/executions/ticker) to
data/ws/*.jsonl.gz. Read-only, no auth, no orders.

Usage: python scripts/record_realtime.py [PRODUCT] [--minutes N]
Default: FX_BTC_JPY, run until stopped (Ctrl+C).
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from bot.market_data.realtime import RealtimeRecorder  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("product", nargs="?", default="FX_BTC_JPY")
    ap.add_argument("--minutes", type=float, default=None)
    args = ap.parse_args()
    recorder = RealtimeRecorder(args.product)
    duration = args.minutes * 60 if args.minutes else None
    try:
        asyncio.run(recorder.run(duration))
    except KeyboardInterrupt:
        pass
    print(f"recorded {recorder.messages_written} messages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
