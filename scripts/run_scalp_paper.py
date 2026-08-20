#!/usr/bin/env python3
"""Event-driven burst-scalp PAPER runner (no real orders, read-only APIs).

Hypothesis under test (docs/RESEARCH_REPORT_2026-08-20e.md): when Binance
BTCUSDT moves >= thr bps within a few seconds, bitFlyer FX_BTC_JPY follows
over the next tens of seconds by more than the taker round-trip cost — but
only during violent regimes.

Mechanics:
- bitFlyer Realtime WS ticker -> live best bid/ask (no REST rate usage)
- Binance REST price poll ~1/s (well inside Binance limits)
- On |Binance return over window_sec| >= thr_bps: paper-enter at the live
  bitFlyer quote (crossing the spread, plus slippage), hold hold_sec, exit at
  the quote again. One position at a time, cooldown between entries.
- Every trade and decision appended to data/scalp_paper.jsonl
- Safety: KILL file stops it; daily loss cap stops it; stale feeds pause it.

Usage:
  python scripts/run_scalp_paper.py [--thr-bps 12] [--window-sec 5]
      [--hold-sec 30] [--notional 110000] [--daily-loss-cap 6000]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import requests
import websockets

WS_ENDPOINT = "wss://ws.lightstream.bitflyer.com/json-rpc"
BINANCE_PRICE = "https://data-api.binance.vision/api/v3/ticker/price"
SLIPPAGE_BPS = 2.0


class ScalpPaper:
    def __init__(self, args):
        self.args = args
        self.bid: float | None = None
        self.ask: float | None = None
        self.quote_ts = 0.0
        self.leader: deque[tuple[float, float]] = deque(maxlen=600)
        self.position = None          # dict(side, size, entry, t_entry)
        self.last_entry_ts = 0.0
        self.daily_pnl = 0.0
        self.trades = 0
        self.log_path = Path("data/scalp_paper.jsonl")
        self.log_path.parent.mkdir(exist_ok=True)
        self.session = requests.Session()

    def log(self, event: str, **kw):
        rec = {"ts": time.time(), "event": event, **kw}
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(json.dumps(rec, ensure_ascii=False), flush=True)

    # ---- feeds ------------------------------------------------------------
    async def bitflyer_ws(self):
        backoff = 1.0
        while True:
            try:
                async with websockets.connect(WS_ENDPOINT, ping_interval=20) as ws:
                    await ws.send(json.dumps({
                        "jsonrpc": "2.0", "id": 1, "method": "subscribe",
                        "params": {"channel": "lightning_ticker_FX_BTC_JPY"}}))
                    backoff = 1.0
                    while True:
                        msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=60))
                        p = msg.get("params", {}).get("message")
                        if p and p.get("best_bid"):
                            self.bid = float(p["best_bid"])
                            self.ask = float(p["best_ask"])
                            self.quote_ts = time.time()
            except Exception as e:
                self.log("ws_reconnect", error=f"{type(e).__name__}")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30.0)

    async def binance_poll(self):
        while True:
            try:
                r = await asyncio.to_thread(
                    self.session.get, BINANCE_PRICE,
                    params={"symbol": "BTCUSDT"}, timeout=5)
                if r.status_code == 200:
                    self.leader.append((time.time(), float(r.json()["price"])))
            except requests.exceptions.RequestException:
                pass
            await asyncio.sleep(1.0)

    def leader_return_bps(self) -> float | None:
        if len(self.leader) < 3:
            return None
        now_ts, now_px = self.leader[-1]
        cutoff = now_ts - self.args.window_sec
        past = None
        for ts, px in self.leader:
            if ts >= cutoff:
                past = px
                break
        if past is None or now_ts - self.leader[0][0] < self.args.window_sec / 2:
            return None
        import math
        return math.log(now_px / past) * 1e4

    # ---- trading loop -----------------------------------------------------
    async def engine(self):
        while True:
            await asyncio.sleep(0.25)
            now = time.time()
            if Path("KILL").exists():
                self.log("kill_file_stop", daily_pnl=self.daily_pnl)
                return
            if self.daily_pnl <= -self.args.daily_loss_cap:
                # marker prevents a watchdog restart from resuming the same day
                self.stop_marker().touch()
                self.log("daily_loss_stop", daily_pnl=self.daily_pnl)
                return
            feeds_ok = (self.bid is not None and now - self.quote_ts < 10
                        and self.leader and now - self.leader[-1][0] < 5)
            if self.position is not None:
                if now - self.position["t_entry"] >= self.args.hold_sec and feeds_ok:
                    self.close_position()
                continue
            if not feeds_ok:
                continue
            ret = self.leader_return_bps()
            if ret is None or abs(ret) < self.args.thr_bps:
                continue
            if now - self.last_entry_ts < self.args.cooldown_sec:
                continue
            side = "LONG" if ret > 0 else "SHORT"
            px = self.ask if side == "LONG" else self.bid
            px *= 1 + (SLIPPAGE_BPS / 1e4) * (1 if side == "LONG" else -1)
            size = self.args.notional / px
            self.position = {"side": side, "size": size, "entry": px, "t_entry": now}
            self.last_entry_ts = now
            self.log("entry", side=side, price=px, size=size, signal_bps=ret,
                     bid=self.bid, ask=self.ask)

    def close_position(self):
        pos = self.position
        px = self.bid if pos["side"] == "LONG" else self.ask
        px *= 1 - (SLIPPAGE_BPS / 1e4) * (1 if pos["side"] == "LONG" else -1)
        direction = 1 if pos["side"] == "LONG" else -1
        pnl = (px - pos["entry"]) * pos["size"] * direction
        self.daily_pnl += pnl
        self.trades += 1
        self.position = None
        self.log("exit", side=pos["side"], price=px, pnl_jpy=round(pnl, 1),
                 daily_pnl=round(self.daily_pnl, 1), trades=self.trades)

    def stop_marker(self) -> Path:
        import datetime
        day = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d")
        return Path(f"data/scalp_stopped_{day}")

    async def run(self):
        if self.stop_marker().exists():
            self.log("refused_start", reason="daily loss cap already hit today "
                     f"({self.stop_marker()}); delete the marker to override")
            return
        self.log("start", **vars(self.args))
        await asyncio.gather(self.bitflyer_ws(), self.binance_poll(), self.engine())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--thr-bps", type=float, default=12.0)
    ap.add_argument("--window-sec", type=float, default=5.0)
    ap.add_argument("--hold-sec", type=float, default=30.0)
    ap.add_argument("--cooldown-sec", type=float, default=30.0)
    ap.add_argument("--notional", type=float, default=110000.0)
    ap.add_argument("--daily-loss-cap", type=float, default=6000.0)
    args = ap.parse_args()
    try:
        asyncio.run(ScalpPaper(args).run())
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
