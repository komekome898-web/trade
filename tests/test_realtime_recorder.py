"""Tests for src/bot/market_data/realtime.py — lazy output-file creation.

The recorder must not create any .jsonl.gz until the first message is
actually received: bitFlyer's daily maintenance window (19:00-19:10 JST)
makes every reconnect attempt fail, and an eagerly-opened file per attempt
used to litter data/ws with empty gzip stubs.
"""
from __future__ import annotations

import asyncio
import gzip
import json

import pytest

import bot.market_data.realtime as rt


class FakeWS:
    """Minimal websocket: records sends, replays queued messages, then
    fails recv (as a dropped connection would)."""

    def __init__(self, messages):
        self._messages = list(messages)
        self.sent = []

    async def send(self, data):
        self.sent.append(data)

    async def recv(self):
        if self._messages:
            return self._messages.pop(0)
        raise ConnectionError("connection lost")


class FakeConnect:
    """Stands in for websockets.connect: an async context manager that
    either raises on entry (connection refused) or yields a FakeWS."""

    def __init__(self, ws=None, connect_error=None):
        self._ws = ws
        self._error = connect_error

    def __call__(self, *args, **kwargs):
        return self

    async def __aenter__(self):
        if self._error is not None:
            raise self._error
        return self._ws

    async def __aexit__(self, *exc_info):
        return False


class FakeWebsockets:
    def __init__(self, connect):
        self.connect = connect


def test_connection_failure_creates_no_file(tmp_path, monkeypatch):
    monkeypatch.setattr(rt, "websockets", FakeWebsockets(
        FakeConnect(connect_error=OSError("connection refused"))))
    rec = rt.RealtimeRecorder(out_dir=tmp_path)

    with pytest.raises(OSError):
        asyncio.run(rec._session(None))

    assert list(tmp_path.iterdir()) == []  # no stub files


def test_connected_but_zero_messages_creates_no_file(tmp_path, monkeypatch):
    ws = FakeWS([])  # subscribed fine, but recv fails before any message
    monkeypatch.setattr(rt, "websockets", FakeWebsockets(FakeConnect(ws=ws)))
    rec = rt.RealtimeRecorder(out_dir=tmp_path)

    with pytest.raises(ConnectionError):
        asyncio.run(rec._session(None))

    assert len(ws.sent) == len(rec.channels)  # it did subscribe...
    assert list(tmp_path.iterdir()) == []     # ...but wrote no file


def test_file_appears_on_first_message_and_holds_all_messages(tmp_path, monkeypatch):
    msgs = [
        json.dumps({"jsonrpc": "2.0", "id": 1, "result": True}),
        json.dumps({"jsonrpc": "2.0", "method": "channelMessage",
                    "params": {"channel": "lightning_ticker_FX_BTC_JPY",
                               "message": {"ltp": 1}}}),
    ]
    ws = FakeWS(msgs)
    monkeypatch.setattr(rt, "websockets", FakeWebsockets(FakeConnect(ws=ws)))
    rec = rt.RealtimeRecorder(product_code="FX_BTC_JPY", out_dir=tmp_path)

    with pytest.raises(ConnectionError):  # session ends when recv fails
        asyncio.run(rec._session(None))

    files = list(tmp_path.iterdir())
    assert len(files) == 1  # exactly one file for the session
    name = files[0].name
    assert name.startswith("FX_BTC_JPY_") and name.endswith(".jsonl.gz")

    with gzip.open(files[0], "rt", encoding="utf-8") as f:
        lines = [json.loads(line) for line in f]
    assert len(lines) == 2
    assert all("rts" in ln and "m" in ln for ln in lines)
    assert lines[0]["m"] == {"jsonrpc": "2.0", "id": 1, "result": True}
    assert rec.messages_written == 2


# ---- buffered multi-member flush (no truncated members on a hard kill) ----


def test_row_count_flush_writes_a_complete_readable_member(tmp_path, monkeypatch):
    """A count-triggered flush mid-session must produce a fully valid gzip
    member on its own — a kill right after it leaves nothing truncated."""
    monkeypatch.setattr(rt, "FLUSH_MAX_ROWS", 2)
    msgs = [json.dumps({"i": i}) for i in range(5)]
    ws = FakeWS(msgs)
    monkeypatch.setattr(rt, "websockets", FakeWebsockets(FakeConnect(ws=ws)))
    rec = rt.RealtimeRecorder(out_dir=tmp_path)

    with pytest.raises(ConnectionError):
        asyncio.run(rec._session(None))

    files = list(tmp_path.iterdir())
    assert len(files) == 1
    # multiple gzip members were appended (>=2 flushes for 5 rows at max 2)
    with open(files[0], "rb") as raw:
        blob = raw.read()
    assert blob.count(b"\x1f\x8b") >= 2  # gzip magic bytes, one per member
    with gzip.open(files[0], "rt", encoding="utf-8") as f:
        lines = [json.loads(line) for line in f]
    assert [ln["m"]["i"] for ln in lines] == list(range(5))
    assert rec.messages_written == 5


def test_stop_requested_ends_session_without_reconnect_and_flushes(tmp_path, monkeypatch):
    """request_stop() (as a signal handler would call it) must end the recv
    loop within one poll interval, flush what's buffered, and — via run() —
    not attempt a reconnect."""
    monkeypatch.setattr(rt, "POLL_INTERVAL_SEC", 0.01)

    class StoppingWS(FakeWS):
        def __init__(self, messages, rec):
            super().__init__(messages)
            self._rec = rec

        async def recv(self):
            msg = await super().recv()
            if not self._messages:  # last queued message just returned
                self._rec.request_stop()
            return msg

    rec = rt.RealtimeRecorder(out_dir=tmp_path)
    ws = StoppingWS([json.dumps({"i": 0}), json.dumps({"i": 1})], rec)
    monkeypatch.setattr(rt, "websockets", FakeWebsockets(FakeConnect(ws=ws)))

    asyncio.run(rec.run(None))  # must return, not raise/hang despite FakeWS

    files = list(tmp_path.iterdir())
    assert len(files) == 1
    with gzip.open(files[0], "rt", encoding="utf-8") as f:
        lines = [json.loads(line) for line in f]
    assert [ln["m"]["i"] for ln in lines] == [0, 1]


def test_install_signal_handlers_registers_without_raising(tmp_path):
    import signal as signal_mod

    rec = rt.RealtimeRecorder(out_dir=tmp_path)
    prev = {name: signal_mod.getsignal(getattr(signal_mod, name))
            for name in ("SIGTERM", "SIGINT") if hasattr(signal_mod, name)}
    try:
        rec.install_signal_handlers()
        assert rec._stop_requested is False
        signal_mod.getsignal(signal_mod.SIGTERM)(signal_mod.SIGTERM, None)
        assert rec._stop_requested is True
    finally:
        for name, handler in prev.items():
            signal_mod.signal(getattr(signal_mod, name), handler)
