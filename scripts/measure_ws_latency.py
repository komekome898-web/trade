#!/usr/bin/env python3
"""Round 24 Step 2 -- LIVE, READ-ONLY latency measurement from this machine.

WHAT THIS IS (and is not)
    A diagnostic.  It measures how late this machine learns about a trade
    that already happened on bitFlyer, and how long a public REST round trip
    takes from here.  It places NO order, touches NO private endpoint, and
    needs NO API key.  Public channels / public REST only.

MEASUREMENTS
    (a) WS receive delay: subscribe to lightning_executions_FX_BTC_JPY for
        --minutes minutes and record, for every execution carried by every
        message, delay = local_receive_time - exchange exec_date.
        Output: one CSV row per print (rts, exec_date, delay_s) plus a
        printed p50/p90/p99 summary.
    (c) Public REST RTT: --rest-n timed GETs of /v1/getticker (no order
        endpoint is ever contacted).  Reports min/p50/p90/max.

CLOCK CAVEAT (stated, not hidden)
    delay = local_clock - exchange_clock, so it contains this host's clock
    offset.  The offset is reported separately (HTTP Date header comparison)
    and the raw distribution is published so the reader can subtract it.

Usage:
    python scripts/measure_ws_latency.py --minutes 10 --out data/latency/ws_vm.csv
    python scripts/measure_ws_latency.py --rest-only --rest-n 20
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import email.utils
import json
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
import websockets

ENDPOINT = "wss://ws.lightstream.bitflyer.com/json-rpc"
REST_TICKER = "https://api.bitflyer.com/v1/getticker?product_code=FX_BTC_JPY"
PRODUCT = "FX_BTC_JPY"


def parse_iso(s: str) -> float:
    """bitFlyer exec_date -> epoch seconds (7-digit fractional seconds)."""
    s = s.rstrip("Z")
    if "." in s:
        head, frac = s.split(".", 1)
        frac = (frac + "000000")[:6]
        s = f"{head}.{frac}"
    dt = datetime.fromisoformat(s).replace(tzinfo=timezone.utc)
    return dt.timestamp()


def pct(xs, q):
    if not xs:
        return float("nan")
    xs = sorted(xs)
    i = min(len(xs) - 1, max(0, int(round(q / 100.0 * (len(xs) - 1)))))
    return xs[i]


def rest_rtt(n: int) -> list[float]:
    rtts = []
    sess = requests.Session()
    for i in range(n):
        t0 = time.perf_counter()
        try:
            r = sess.get(REST_TICKER, timeout=10)
            r.raise_for_status()
        except Exception as e:  # noqa: BLE001
            print(f"  rest[{i}] failed: {type(e).__name__}: {e}", flush=True)
            time.sleep(0.5)
            continue
        rtts.append(time.perf_counter() - t0)
        time.sleep(0.5)
    return rtts


def clock_offset_probe(n: int = 30) -> tuple[float, float, int]:
    """Bound the host clock offset (local - exchange) with HTTP Date headers.

    The Date header is the server time FLOORED to the second, stamped at some
    instant between our send (t0) and our receive (t1), both on the local
    clock.  So for every sample:
        offset >= t0 - (srv + 1)   and   offset <= t1 - srv
    Intersecting the intervals over n samples brackets the offset far more
    tightly than any single 1 s-resolution reading.
    """
    lo, hi, k = -1e9, 1e9, 0
    sess = requests.Session()
    for _ in range(n):
        t0 = time.time()
        try:
            r = sess.get(REST_TICKER, timeout=10)
        except Exception:  # noqa: BLE001
            continue
        t1 = time.time()
        d = r.headers.get("Date")
        if not d:
            continue
        srv = email.utils.parsedate_to_datetime(d).timestamp()
        lo = max(lo, t0 - (srv + 1.0))
        hi = min(hi, t1 - srv)
        k += 1
        time.sleep(0.35)
    return lo, hi, k


async def ws_probe(minutes: float, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + minutes * 60.0
    rows: list[tuple[float, str, float]] = []
    msg_delays: list[float] = []
    n_msg = 0
    print(f"[ws] connecting to {ENDPOINT} (executions only, read-only)", flush=True)
    async with websockets.connect(ENDPOINT, ping_interval=20, ping_timeout=20,
                                  max_size=2 ** 24) as ws:
        await ws.send(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "subscribe",
                                  "params": {"channel": f"lightning_executions_{PRODUCT}"}}))
        print("[ws] subscribed", flush=True)
        while time.monotonic() < deadline:
            try:
                raw = await asyncio.wait_for(ws.recv(),
                                             timeout=max(1.0, deadline - time.monotonic()))
            except asyncio.TimeoutError:
                break
            rts = time.time()
            n_msg += 1
            obj = json.loads(raw)
            params = obj.get("params") or {}
            msg = params.get("message")
            if not isinstance(msg, list):
                continue
            first = None
            for ex in msg:
                ed = ex.get("exec_date")
                if not ed:
                    continue
                t_ex = parse_iso(ed)
                d = rts - t_ex
                rows.append((rts, ed, d))
                if first is None:
                    first = d
            if first is not None:
                msg_delays.append(first)
    with out_path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["rts", "exec_date", "delay_s"])
        w.writerows(rows)
    ds = [r[2] for r in rows]
    print(f"[ws] messages={n_msg}  prints={len(ds)}  file={out_path}", flush=True)
    if ds:
        print(f"[ws] per-print delay s: p10={pct(ds,10):.3f} p50={pct(ds,50):.3f} "
              f"p90={pct(ds,90):.3f} p99={pct(ds,99):.3f} "
              f"min={min(ds):.3f} max={max(ds):.3f} mean={statistics.fmean(ds):.3f}",
              flush=True)
        print(f"[ws] first-print-of-message delay s: n={len(msg_delays)} "
              f"p50={pct(msg_delays,50):.3f} p90={pct(msg_delays,90):.3f} "
              f"p99={pct(msg_delays,99):.3f}", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=float, default=10.0)
    ap.add_argument("--rest-n", type=int, default=20)
    ap.add_argument("--rest-only", action="store_true")
    ap.add_argument("--out", default="data/latency/ws_vm.csv")
    a = ap.parse_args()

    print("=" * 70)
    print("READ-ONLY latency probe -- public channels / public REST only")
    print("=" * 70)

    lo, hi, k = clock_offset_probe()
    if k:
        print(f"[clock] host clock offset (local - exchange) bracketed by "
              f"n={k} Date headers: [{lo:+.3f}, {hi:+.3f}] s "
              f"(midpoint {0.5*(lo+hi):+.3f})", flush=True)

    if not a.rest_only:
        asyncio.run(ws_probe(a.minutes, Path(a.out)))

    print(f"[rest] timing {a.rest_n} GETs of /v1/getticker (no order endpoint)",
          flush=True)
    rtts = rest_rtt(a.rest_n)
    if rtts:
        print(f"[rest] RTT s: n={len(rtts)} min={min(rtts):.3f} p50={pct(rtts,50):.3f} "
              f"p90={pct(rtts,90):.3f} max={max(rtts):.3f}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
