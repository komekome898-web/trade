#!/usr/bin/env python3
"""Event-driven burst-scalp PAPER runner (no real orders, read-only APIs).

Hypothesis under test (docs/RESEARCH_REPORT_2026-08-20e.md): when Binance
BTCUSDT moves >= thr bps within a few seconds, bitFlyer FX_BTC_JPY follows
over the next tens of seconds by more than the taker round-trip cost — but
only during violent regimes.

Mechanics:
- bitFlyer Realtime WS ticker -> live best bid/ask (no REST rate usage) and
  WS executions -> the print tape used to decide maker fills
- Binance REST price poll ~1/s (well inside Binance limits)
- On |Binance return over window_sec| >= thr_bps: paper-enter on bitFlyer
  FX_BTC_JPY. Entry style is selectable (--entry):
    maker (default) rest a virtual limit at the near touch and wait for a
          print to come to it (no spread, no slippage paid); if nothing
          fills inside --fill-timeout-sec the order is cancelled and the
          event is logged as a miss.
    taker cross the spread immediately, plus SLIPPAGE_BPS.
  The exit is always taker, hold_sec after the FILL (not after the signal).
  One position at a time, cooldown between entries (measured from signal).
- Every trade and decision appended to data/scalp_paper.jsonl
- Safety: KILL file stops it; daily loss cap stops it; stale feeds pause it.

Defaults follow the quote-level study in scripts/research_scalp_opt.py:
maker entry beats taker entry per event, hold 60s sits at/near the peak of
the hold curve, and thr 10 bps keeps EV while raising trade count.

Usage:
  python scripts/run_scalp_paper.py [--thr-bps 10] [--window-sec 5]
      [--hold-sec 60] [--entry maker] [--fill-timeout-sec 10]
      [--notional 110000] [--daily-loss-cap 6000]
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
TICKER_CHANNEL = "lightning_ticker_FX_BTC_JPY"
EXECUTIONS_CHANNEL = "lightning_executions_FX_BTC_JPY"
BINANCE_PRICE = "https://data-api.binance.vision/api/v3/ticker/price"
SLIPPAGE_BPS = 2.0


class RestingLimit:
    """A virtual maker order waiting for the tape to come to it.

    Pure logic (no clock, no I/O) so it can be unit tested — see
    tests/test_scalp_logic.py. The fill rule mirrors ``maker_sim`` in
    scripts/research_scalp_opt.py, the study this entry mode comes from:

      LONG  -> limit at the CURRENT best bid; filled when a print lands at
               or below that price (a taker SELL is what reaches a resting
               bid) within ``timeout_sec`` of the signal.
      SHORT -> limit at the CURRENT best ask; filled when a print lands at
               or above it (a taker BUY).

    Prints stamped before the order was placed can never fill it, and the
    permissive "at or through" touch rule is used, matching the optimistic
    bound reported by the study. Fills happen AT the limit price: no spread
    and no slippage are paid on a maker entry.
    """

    #: taker side of a print that can reach our resting order, by our side.
    _COUNTER_SIDE = {"LONG": "SELL", "SHORT": "BUY"}

    def __init__(self, side: str, limit: float, t_signal: float,
                 timeout_sec: float, size: float, signal_bps: float = 0.0):
        self.side = side
        self.limit = float(limit)
        self.t_signal = float(t_signal)
        self.timeout_sec = float(timeout_sec)
        self.size = float(size)
        self.signal_bps = float(signal_bps)

    def accepts(self, ts: float, price: float, taker_side: str | None = None) -> bool:
        """True if the print (ts, price, taker_side) fills this order."""
        if ts < self.t_signal or ts > self.t_signal + self.timeout_sec:
            return False
        if taker_side:
            if taker_side.upper() != self._COUNTER_SIDE[self.side]:
                return False
        if self.side == "LONG":
            return price <= self.limit
        return price >= self.limit

    def first_fill(self, prints) -> tuple[float, float] | None:
        """First (ts, price) in ``prints`` that fills this order, else None."""
        for rec in prints:
            ts, price = rec[0], rec[1]
            taker_side = rec[2] if len(rec) > 2 else None
            if self.accepts(ts, price, taker_side):
                return ts, price
        return None

    def expired(self, now: float) -> bool:
        return now > self.t_signal + self.timeout_sec


class ScalpPaper:
    def __init__(self, args):
        self.args = args
        self.bid: float | None = None
        self.ask: float | None = None
        self.quote_ts = 0.0
        self.leader: deque[tuple[float, float]] = deque(maxlen=600)
        self.prints: deque[tuple[float, float, str]] = deque(maxlen=2000)
        self.position = None          # dict(side, size, entry, t_entry)
        self.pending: RestingLimit | None = None
        self.last_entry_ts = 0.0
        self.daily_pnl = 0.0
        self.trades = 0
        self.misses = 0
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
                    for i, channel in enumerate((TICKER_CHANNEL, EXECUTIONS_CHANNEL)):
                        await ws.send(json.dumps({
                            "jsonrpc": "2.0", "id": i + 1, "method": "subscribe",
                            "params": {"channel": channel}}))
                    backoff = 1.0
                    while True:
                        msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=60))
                        params = msg.get("params", {})
                        channel = params.get("channel")
                        p = params.get("message")
                        if channel == EXECUTIONS_CHANNEL:
                            self.on_executions(p)
                        elif p and p.get("best_bid"):
                            self.bid = float(p["best_bid"])
                            self.ask = float(p["best_ask"])
                            self.quote_ts = time.time()
            except Exception as e:
                self.log("ws_reconnect", error=f"{type(e).__name__}")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30.0)

    def on_executions(self, message) -> None:
        """Append prints to the tape. ``side`` is the TAKER side of the print.

        Receive time is used as the timestamp: fills are judged against our
        own local placement clock, so exec_date parsing buys nothing here.
        """
        now = time.time()
        for ex in message or []:
            try:
                price = float(ex["price"])
            except (KeyError, TypeError, ValueError):
                continue
            self.prints.append((now, price, str(ex.get("side") or "")))

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
            if self.pending is not None:
                self.check_pending(now)
                continue
            if self.position is not None:
                # hold is measured from the FILL, which is t_entry
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
            # cooldown is measured from the SIGNAL in both entry modes
            self.last_entry_ts = now
            if self.args.entry == "maker":
                self.place_limit(side, ret, now)
            else:
                self.enter_taker(side, ret, now)

    def enter_taker(self, side: str, ret: float, now: float) -> None:
        px = self.ask if side == "LONG" else self.bid
        px *= 1 + (SLIPPAGE_BPS / 1e4) * (1 if side == "LONG" else -1)
        size = self.args.notional / px
        self.position = {"side": side, "size": size, "entry": px, "t_entry": now}
        self.log("entry", entry_mode="taker", side=side, price=px, size=size,
                 signal_bps=ret, bid=self.bid, ask=self.ask)

    def place_limit(self, side: str, ret: float, now: float) -> None:
        """Rest a virtual limit at the near touch (bid for long, ask for short)."""
        limit = self.bid if side == "LONG" else self.ask
        self.pending = RestingLimit(
            side=side, limit=limit, t_signal=now,
            timeout_sec=self.args.fill_timeout_sec,
            size=self.args.notional / limit, signal_bps=ret)
        self.log("limit_placed", entry_mode="maker", side=side, limit=limit,
                 size=self.pending.size, signal_bps=ret,
                 fill_timeout_sec=self.args.fill_timeout_sec,
                 bid=self.bid, ask=self.ask)

    def check_pending(self, now: float) -> None:
        """Fill the resting order off the tape, or cancel it on timeout."""
        order = self.pending
        hit = order.first_fill(self.prints)
        if hit is not None:
            fill_ts, _ = hit
            self.pending = None
            # maker fill: at the limit price, no spread and no slippage
            self.position = {"side": order.side, "size": order.size,
                             "entry": order.limit, "t_entry": fill_ts}
            self.log("fill", entry_mode="maker", side=order.side,
                     price=order.limit, size=order.size,
                     signal_bps=order.signal_bps,
                     fill_latency_sec=round(fill_ts - order.t_signal, 3),
                     bid=self.bid, ask=self.ask)
            return
        if order.expired(now):
            self.pending = None
            self.misses += 1
            # taker-basis price at miss time: what crossing now would have
            # cost, so live adverse-selection stats accumulate (the study's
            # miss analysis in scripts/research_scalp_opt.py, done live)
            basis = self.ask if order.side == "LONG" else self.bid
            if basis is not None:
                basis *= 1 + (SLIPPAGE_BPS / 1e4) * (1 if order.side == "LONG" else -1)
            self.log("missed", entry_mode="maker", side=order.side,
                     limit=order.limit, signal_bps=order.signal_bps,
                     taker_basis=basis, misses=self.misses,
                     waited_sec=round(now - order.t_signal, 3),
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
        self.log("exit", entry_mode=self.args.entry, side=pos["side"], price=px,
                 pnl_jpy=round(pnl, 1), daily_pnl=round(self.daily_pnl, 1),
                 trades=self.trades)

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
    ap.add_argument("--thr-bps", type=float, default=10.0)
    ap.add_argument("--window-sec", type=float, default=5.0)
    ap.add_argument("--hold-sec", type=float, default=60.0)
    ap.add_argument("--cooldown-sec", type=float, default=30.0)
    ap.add_argument("--entry", choices=("maker", "taker"), default="maker")
    ap.add_argument("--fill-timeout-sec", type=float, default=10.0)
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
