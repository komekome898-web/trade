"""bitFlyer Realtime API (JSON-RPC 2.0 over WebSocket) recorder.

Subscribes to public channels and appends every message as one JSON line
(with local receive timestamp) to a gzip file — the raw dataset for
market-making / scalping research that REST polling cannot provide:
board snapshots + diffs, executions and tickers at millisecond cadence.

Read-only: no authentication, no orders. Reconnects with backoff on any
failure; a session writes to its own file so crashes never corrupt data.
The file is opened lazily on the first received message, so sessions that
never receive anything (e.g. reconnect attempts during bitFlyer's daily
maintenance window, 04:00-04:10 JST = 19:00-19:10 UTC) leave no empty
stub files behind.

Writing: messages are buffered in memory and flushed as a COMPLETE gzip
member (gzip.open(path, "ab") -> write -> close) every FLUSH_INTERVAL_SEC
seconds or every FLUSH_MAX_ROWS messages, whichever comes first — the same
multi-member-append pattern scripts/record_venues.py uses. The file is
never held open across messages, so a hard kill (taskkill /F, a plain
SIGKILL) can only lose the still-unflushed buffer; it can never leave a
truncated gzip member on disk (unlike the previous gzip.open(path, "at")
design, which kept one member open for the whole session).
SIGTERM/SIGINT (and, on Windows, SIGBREAK / CTRL_BREAK_EVENT) are handled
by run() to flush the buffer and stop cleanly instead of reconnecting; a
bare KeyboardInterrupt propagating through _session's try/finally is
flushed the same way before it reaches the caller.
"""
from __future__ import annotations

import asyncio
import gzip
import json
import signal
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

FLUSH_INTERVAL_SEC = 60.0
FLUSH_MAX_ROWS = 2000
# How often the recv loop wakes up even without a message, so a stop
# request (signal or duration deadline) is noticed promptly instead of
# waiting out the full 60s no-message reconnect timeout.
POLL_INTERVAL_SEC = 5.0
NO_MESSAGE_RECONNECT_SEC = 60.0


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
        self._stop_requested = False
        self._current_path: Path | None = None
        self._buf: list[bytes] = []
        self._last_flush = time.monotonic()

    def request_stop(self) -> None:
        """Ask the run loop to flush and exit instead of reconnecting.
        Safe to call from a signal handler or any thread — it only sets a
        flag the recv loop checks at least every POLL_INTERVAL_SEC."""
        self._stop_requested = True

    def install_signal_handlers(self) -> None:
        """Best-effort graceful shutdown: SIGTERM/SIGINT everywhere, plus
        SIGBREAK (Windows CTRL_BREAK_EVENT) where it exists. Must be called
        from the main thread; failures (e.g. not the main thread) are
        swallowed since this is a best-effort improvement over a hard kill,
        not a safety requirement — the periodic flush already bounds data
        loss to the current buffer regardless."""
        def _handler(signum, frame):  # noqa: ARG001 - signal handler signature
            self.request_stop()
        for name in ("SIGTERM", "SIGINT", "SIGBREAK"):
            sig = getattr(signal, name, None)
            if sig is None:
                continue
            try:
                signal.signal(sig, _handler)
            except (ValueError, OSError, RuntimeError):
                pass

    def _new_path(self) -> Path:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        return self.out_dir / f"{self.product_code}_{stamp}.jsonl.gz"

    def _buffer(self, record: dict) -> None:
        if self._current_path is None:
            self._current_path = self._new_path()
            print(f"[recorder] writing {self._current_path}", flush=True)
        line = json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
        self._buf.append(line.encode("utf-8"))

    def _should_flush(self) -> bool:
        if not self._buf:
            return False
        return (len(self._buf) >= FLUSH_MAX_ROWS or
                time.monotonic() - self._last_flush >= FLUSH_INTERVAL_SEC)

    def _flush(self) -> None:
        """Append the buffered rows as ONE complete gzip member (open,
        write, close) — never leaves a partial member on disk. A hard kill
        between flushes loses at most the buffer written since the last one."""
        if not self._buf or self._current_path is None:
            return
        data = b"".join(self._buf)
        n = len(self._buf)
        with gzip.open(self._current_path, "ab") as f:
            f.write(data)
        self._buf = []
        self._last_flush = time.monotonic()
        self.messages_written += n

    async def run(self, duration_sec: float | None = None) -> None:
        self.install_signal_handlers()
        deadline = time.monotonic() + duration_sec if duration_sec else None
        backoff = 1.0
        while not self._stop_requested and (deadline is None or time.monotonic() < deadline):
            try:
                await self._session(deadline)
                backoff = 1.0
            except asyncio.CancelledError:
                raise
            except Exception as e:  # reconnect on anything (network, server)
                if self._stop_requested:
                    break
                print(f"[recorder] reconnect after error: {type(e).__name__}: {e}",
                      flush=True)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60.0)

    async def _session(self, deadline: float | None) -> None:
        # Lazy open: the output file is created on the FIRST received message,
        # so a session that connects but receives nothing (or never connects)
        # leaves no empty stub file behind.
        self._current_path = None
        print("[recorder] connecting", flush=True)
        try:
            async with websockets.connect(self.endpoint, ping_interval=20,
                                          ping_timeout=20, max_size=2 ** 24) as ws:
                for i, channel in enumerate(self.channels):
                    await ws.send(json.dumps({
                        "jsonrpc": "2.0", "id": i + 1, "method": "subscribe",
                        "params": {"channel": channel},
                    }))
                last_msg = time.monotonic()
                while not self._stop_requested and (deadline is None or time.monotonic() < deadline):
                    poll_timeout = POLL_INTERVAL_SEC
                    if deadline is not None:
                        poll_timeout = min(poll_timeout, max(0.1, deadline - time.monotonic()))
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=poll_timeout)
                    except asyncio.TimeoutError:
                        if self._should_flush():
                            self._flush()
                        if self._stop_requested:
                            return
                        if deadline is not None and time.monotonic() >= deadline:
                            return  # duration reached while waiting — normal shutdown
                        if time.monotonic() - last_msg >= NO_MESSAGE_RECONNECT_SEC:
                            raise ConnectionError("no message for 60s — reconnecting")
                        continue
                    last_msg = time.monotonic()
                    self._buffer({"rts": time.time(), "m": json.loads(raw)})
                    if self._should_flush():
                        self._flush()
        finally:
            self._flush()
            if self._current_path is not None:
                print(f"[recorder] closed {self._current_path} "
                      f"({self.messages_written} msgs total)", flush=True)
