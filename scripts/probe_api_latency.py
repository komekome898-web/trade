#!/usr/bin/env python3
"""Read-only API round-trip-time probe (EXEC_FLOOR_PREREG.md sec7 row 3 -> E-h).

Every --interval-sec (default 30) this calls exactly ONE authenticated
read-only endpoint -- /v1/me/getpermissions, the same call
scripts/check_api.py already uses to verify key permissions/read access;
NEVER an order endpoint -- and one public endpoint (/v1/getticker,
FX_BTC_JPY), and appends the timing of each to data/latency/api_probe.csv.

This is a PROXY for order-acknowledgement latency, not a measurement of
it: EXEC_FLOOR_PREREG.md sec1/E-h is explicit that no order-response delay
is recorded anywhere in this repo, and sending a real order just to time it
would violate rule 12 (no capital risk for measurement) and the PAPER/LIVE
safety invariant. What this DOES measure: the network+auth+server RTT of a
same-class private read (closest legal proxy for an order-ack's own
network+auth+server hop) and of a public read, sampled continuously over a
window, so E-h can at least bound "delay" by something better than nothing
while flagging the gap plainly rather than pretending it is closed.

Refuses to run under LIVE_MODE outright (checked via
bot.settings.resolve_mode/load_settings) -- this diagnostic has no
business needing live money armed, and confirming it work is meant to be
done with PAPER credentials (an API key with read permissions only; the
private call here is read-only regardless of what the key can do -- see
check_api.py's own withdrawal-permission check for the key-level guard).
Sends NO order under any credential.

WS lag (optional, best-effort): if a WS recorder (src/bot/market_data/
realtime.py, run via scripts/record_realtime.py) is writing to data/ws/,
each cycle also reports how stale its most recently received ticker
message is AT THE SAME WALL-CLOCK INSTANT as the probe call (probe_time -
message rts), so a REST RTT sample and the concurrent WS feed staleness can
be read on the same axis. This never re-decompresses a whole (potentially
hours-long) growing recording: it reads only the bytes appended since the
last successful read (state in data/latency/ws_probe_state.json), which
works because realtime.py always flushes a COMPLETE gzip member per write
(FLUSH_INTERVAL_SEC) -- the appended range is either a run of complete
members (decompresses cleanly) or ends mid-member because the recorder is
flushing RIGHT NOW, in which case this cycle reports "mid_flush" and does
NOT advance its stored offset, so nothing is lost, just retried next cycle.

Rate: 2 requests every interval-sec (default 30s) = ~0.033 req/s each,
far under bitFlyer's published 500-per-5-minutes (~1.7 req/s) limits.

Resumable: output is a plain append-only CSV opened in "a" mode and the WS
tail state is checkpointed to disk every cycle, so killing and restarting
this script loses at most the in-flight cycle.

Usage:
    python scripts/probe_api_latency.py                  # 168h, 30s interval
    python scripts/probe_api_latency.py --hours 1 --interval-sec 5
    python scripts/probe_api_latency.py --no-ws           # skip the WS leg
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import sys
import time
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bot.exchange.bitflyer_client import BitflyerClient, BitflyerError, NetworkError  # noqa: E402
from bot.settings import ModeConfigError, load_settings  # noqa: E402

DEFAULT_OUT = ROOT / "data" / "latency" / "api_probe.csv"
DEFAULT_WS_DIR = ROOT / "data" / "ws"
DEFAULT_WS_STATE = ROOT / "data" / "latency" / "ws_probe_state.json"

FIELDS = ["t_send", "t_recv", "rtt_ms", "endpoint", "http_status", "ws_lag_ms", "ws_note"]

DEFAULT_INTERVAL_SEC = 30.0
DEFAULT_HOURS = 168.0
TICKER_CHANNEL_PREFIX = "lightning_ticker_"

# Raised by gzip/zlib when a compressed stream stops short (recorder writing
# right now). gzip.BadGzipFile is an OSError.
_TRUNCATED_GZ_ERRORS = (EOFError, OSError, zlib.error, UnicodeDecodeError)


# ---- one timed call ---------------------------------------------------------
def timed_call(client: BitflyerClient, fn) -> tuple[float, float, str]:
    """Run fn() as a single-attempt, fixed-short-timeout diagnostic call.
    Returns (t_send, t_recv, http_status) where http_status is "200" on
    success, the numeric status on a definite API error, or "" on a
    transport-level failure (timeout, connection error)."""
    with client.diagnostic_call():
        t_send = time.time()
        try:
            fn()
            status = "200"
        except BitflyerError as e:
            status = str(e.status_code)
        except NetworkError:
            status = ""
        t_recv = time.time()
    return t_send, t_recv, status


# ---- WS tail lag (best-effort, see module docstring) ------------------------
def _pick_ws_file(ws_dir: Path) -> Path | None:
    try:
        files = sorted(ws_dir.glob("*.jsonl.gz"), key=lambda p: p.stat().st_mtime)
    except OSError:
        return None
    return files[-1] if files else None


def _load_ws_state(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save_ws_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state), encoding="utf-8")
    tmp.replace(path)


def _ticker_rts(obj: dict) -> float | None:
    """Local receive timestamp (rts) of a line, if it is a ticker message."""
    if not isinstance(obj, dict):
        return None
    rts = obj.get("rts")
    if not isinstance(rts, (int, float)) or isinstance(rts, bool):
        return None
    m = obj.get("m")
    params = m.get("params") if isinstance(m, dict) else None
    channel = params.get("channel") if isinstance(params, dict) else None
    if isinstance(channel, str) and channel.startswith(TICKER_CHANNEL_PREFIX):
        return float(rts)
    return None


def ws_ticker_lag(ws_dir: Path, state_path: Path, probe_time: float
                  ) -> tuple[float | None, str]:
    """(lag_sec, note). lag_sec = probe_time - rts of the latest ticker
    message seen so far (None if never seen / unavailable)."""
    if not ws_dir.is_dir():
        return None, "no_ws_dir"
    ws_file = _pick_ws_file(ws_dir)
    if ws_file is None:
        return None, "no_ws_file"
    state = _load_ws_state(state_path)
    entry = state.get(ws_file.name, {})
    offset = entry.get("offset", 0)
    try:
        size = ws_file.stat().st_size
    except OSError:
        return None, "stat_failed"
    if size < offset:
        offset = 0  # rotated/truncated -- restart this file from 0
    last_rts = entry.get("last_rts")
    if size == offset:
        return (probe_time - last_rts if last_rts is not None else None), "unchanged"
    try:
        with ws_file.open("rb") as f:
            f.seek(offset)
            chunk = f.read()
        text = gzip.decompress(chunk).decode("utf-8")
    except _TRUNCATED_GZ_ERRORS:
        # Recorder is flushing right now -- do NOT advance the offset;
        # retry from the same point next cycle.
        return (probe_time - last_rts if last_rts is not None else None), "mid_flush"
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        rts = _ticker_rts(obj)
        if rts is not None:
            last_rts = rts
    state[ws_file.name] = {"offset": size, "last_rts": last_rts}
    _save_ws_state(state_path, state)
    if last_rts is None:
        return None, "no_ticker_seen"
    return probe_time - last_rts, "ok"


# ---- one probe cycle ---------------------------------------------------------
def run_cycle(client: BitflyerClient, has_credentials: bool, out_path: Path,
             ws_dir: Path | None, ws_state_path: Path) -> list[dict]:
    rows: list[dict] = []

    t_send, t_recv, status = timed_call(client, lambda: client.ticker("FX_BTC_JPY"))
    rows.append({"t_send": t_send, "t_recv": t_recv,
                "rtt_ms": (t_recv - t_send) * 1000.0,
                "endpoint": "public:getticker", "http_status": status})

    if has_credentials:
        t_send, t_recv, status = timed_call(client, client.get_permissions)
        rows.append({"t_send": t_send, "t_recv": t_recv,
                    "rtt_ms": (t_recv - t_send) * 1000.0,
                    "endpoint": "private:getpermissions", "http_status": status})
    else:
        now = time.time()
        rows.append({"t_send": now, "t_recv": now, "rtt_ms": "",
                    "endpoint": "private:getpermissions", "http_status": "no_credentials"})

    if ws_dir is not None:
        lag_sec, note = ws_ticker_lag(ws_dir, ws_state_path, time.time())
        ws_lag_ms = "" if lag_sec is None else lag_sec * 1000.0
    else:
        ws_lag_ms, note = "", "disabled"
    for row in rows:
        row["ws_lag_ms"] = ws_lag_ms
        row["ws_note"] = note

    _append_rows(out_path, rows)
    return rows


def _append_rows(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not path.exists() or path.stat().st_size == 0
    with path.open("a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if write_header:
            w.writeheader()
        for row in rows:
            w.writerow(row)


# ---- run loop ----------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--interval-sec", type=float, default=DEFAULT_INTERVAL_SEC)
    ap.add_argument("--hours", type=float, default=DEFAULT_HOURS,
                    help="total run duration; the process exits after this "
                         "many hours (default 168 = 1 week)")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--ws-dir", default=str(DEFAULT_WS_DIR))
    ap.add_argument("--ws-state", default=str(DEFAULT_WS_STATE))
    ap.add_argument("--no-ws", action="store_true", help="skip the WS lag leg entirely")
    ap.add_argument("--max-cycles", type=int, default=None,
                    help="stop after this many cycles regardless of --hours "
                         "(mainly for smoke-testing)")
    ap.add_argument("--root", default=str(ROOT), help="repo root, for settings/.env")
    args = ap.parse_args(argv)

    try:
        settings = load_settings(args.root)
    except ModeConfigError as e:
        print(f"probe_api_latency: refusing to start -- {e}", file=sys.stderr)
        return 1
    if settings.is_live:
        print("probe_api_latency: refusing to start -- LIVE_MODE is active. "
              "This diagnostic is PAPER-only by design; do not arm LIVE for it.",
              file=sys.stderr)
        return 1

    has_credentials = bool(settings.api_key)
    client = BitflyerClient(settings.api_key, settings.api_secret)
    out_path = Path(args.out)
    ws_dir = None if args.no_ws else Path(args.ws_dir)
    ws_state_path = Path(args.ws_state)

    print(f"probe_api_latency: mode={settings.mode.value} "
          f"credentials={'yes' if has_credentials else 'no'} "
          f"interval={args.interval_sec:.0f}s hours={args.hours:.1f} "
          f"-> {out_path}", flush=True)

    deadline = time.monotonic() + args.hours * 3600.0
    cycles = 0
    try:
        while time.monotonic() < deadline:
            if args.max_cycles is not None and cycles >= args.max_cycles:
                break
            t0 = time.monotonic()
            try:
                rows = run_cycle(client, has_credentials, out_path, ws_dir, ws_state_path)
                statuses = ", ".join(f"{r['endpoint']}={r['http_status']}"
                                     f"({r['rtt_ms'] if r['rtt_ms'] != '' else '-'}"
                                     f"{'ms' if r['rtt_ms'] != '' else ''})"
                                     for r in rows)
                print(f"probe_api_latency: {statuses}", flush=True)
            except Exception as e:  # noqa: BLE001 - resident: never die on one bad cycle
                print(f"probe_api_latency: cycle FAILED: {type(e).__name__}: {e}",
                      file=sys.stderr, flush=True)
            cycles += 1
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            sleep_for = max(0.0, min(args.interval_sec - (time.monotonic() - t0), remaining))
            time.sleep(sleep_for)
    except KeyboardInterrupt:
        pass
    print(f"probe_api_latency: stopped after {cycles} cycle(s)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
