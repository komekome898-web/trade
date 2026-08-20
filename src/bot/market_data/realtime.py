"""bitFlyer Realtime API (JSON-RPC 2.0 over WebSocket) recorder.

Subscribes to public channels and appends every message as one JSON line
(with local receive timestamp) to a gzip file — the raw dataset for
market-making / scalping research that REST polling cannot provide:
board snapshots + diffs, executions and tickers at millisecond cadence.

Read-only: no authentication, no orders. Reconnects with backoff on any
failure; a session writes to its own file so crashes never corrupt data.
"""
from __future__ import annotations

import asyncio
import gzip
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import websockets

ENDPOINT = "wss://ws.lightstream.bitflyer.com/json-rpc"

DEFAULT_CHANNELS = (
    "lightning_ticker_{p}",
    "lightning_executions_{p}",
    "lightning_board_snapshot_{p}",
    "lightning_board_{p}",
)


class RealtimeRecorder:
    def __init__(self, product_code: str = "FX_BTC_JPY",
                 out_dir: str | Path = "data/ws",
                 channels: tuple[str, ...] = DEFAULT_CHANNELS,
                 endpoint: str = ENDPOINT):
        self.product_code = product_code
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.channels = [c.format(p=product_code) for c in channels]
        self.endpoint = endpoint
        self.messages_written = 0

    def _open_file(self):
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        path = self.out_dir / f"{self.product_code}_{stamp}.jsonl.gz"
        return gzip.open(path, "at", encoding="utf-8"), path

    async def run(self, duration_sec: float | None = None) -> None:
        deadline = time.monotonic() + duration_sec if duration_sec else None
        backoff = 1.0
        while deadline is None or time.monotonic() < deadline:
            try:
                await self._session(deadline)
                backoff = 1.0
            except asyncio.CancelledError:
                raise
            except Exception as e:  # reconnect on anything (network, server)
                print(f"[recorder] reconnect after error: {type(e).__name__}: {e}",
                      flush=True)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60.0)

    async def _session(self, deadline: float | None) -> None:
        f, path = self._open_file()
        print(f"[recorder] connecting; writing {path}", flush=True)
        try:
            async with websockets.connect(self.endpoint, ping_interval=20,
                                          ping_timeout=20, max_size=2 ** 24) as ws:
                for i, channel in enumerate(self.channels):
                    await ws.send(json.dumps({
                        "jsonrpc": "2.0", "id": i + 1, "method": "subscribe",
                        "params": {"channel": channel},
                    }))
                while deadline is None or time.monotonic() < deadline:
                    timeout = None if deadline is None else max(
                        0.1, deadline - time.monotonic())
                    raw = await asyncio.wait_for(ws.recv(), timeout=min(60.0, timeout or 60.0))
                    f.write(json.dumps({"rts": time.time(), "m": json.loads(raw)},
                                       ensure_ascii=False, separators=(",", ":")) + "\n")
                    self.messages_written += 1
        except asyncio.TimeoutError:
            if deadline is not None and time.monotonic() >= deadline:
                return  # duration reached while waiting — normal shutdown
            raise ConnectionError("no message for 60s — reconnecting")
        finally:
            f.close()
            print(f"[recorder] closed {path} ({self.messages_written} msgs total)",
                  flush=True)
