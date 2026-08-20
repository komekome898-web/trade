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
  The exit style is selectable too (--exit):
    maker_tp (default) on the entry FILL, rest a take-profit limit
          --tp-bps beyond the fill in the profit direction (long -> sell
          above, short -> buy below), filled by the same at-or-through
          print rule as the entry; if it has not filled by fill +
          --fallback-sec the position is closed taker at market.
    taker legacy: hold --hold-sec from the FILL, then exit taker.
  One position at a time, cooldown between entries (measured from signal).
- Every trade and decision appended to data/scalp_paper.jsonl
- Safety: KILL file stops it; daily loss cap stops it; stale feeds pause it.

Defaults follow the quote-level study in scripts/research_scalp_opt.py:
maker entry beats taker entry per event, hold 60s sits at/near the peak of
the hold curve, and thr 10 bps keeps EV while raising trade count.

The exit default is E2 from the exit study in scripts/research_scalp_exits.py
(maker TP +10 bps, fallback taker at fill+120s). No exit variant cleared the
+5 bps/trade adoption bar there, so this is NOT an edge adoption: E2 is taken
as a VARIANCE decision (higher median, higher win rate, about half the sd,
bounded losses vs the legacy taker hold) and the call stays pending paper
evidence. The study ran on n = 16 storm events, under the 30-event bar; the
paper event count restarts at this change, so only fills logged from here on
count toward the 30.

Storm radar (src/bot/radar.py, from scripts/research_storm_b.py): storms are
2.23x more likely to begin during 12:30-15:00 UTC, the only pre-registered
precursor that qualified. Inside that window the radar is "armed"; while
armed the threshold is --thr-armed-bps. The armed default is 10 (same as
--thr-bps): the storm-library replay (scripts/replay_scalp_storm.py,
2026-08-20) found the marginal 8-10 bps bursts bought by a lower armed
threshold ran -4.1 bps/trade over 68 fills, so the sensitivity boost is
off until paper evidence says otherwise. Every arm/disarm flip is logged
as a "radar_state" event, and entry-side events carry radar_armed, so the
JSONL still separates armed vs unarmed performance at equal thresholds.

Usage:
  python scripts/run_scalp_paper.py [--thr-bps 10] [--thr-armed-bps 10]
      [--window-sec 5] [--hold-sec 60] [--entry maker]
      [--exit maker_tp] [--tp-bps 10] [--fallback-sec 120]
      [--fill-timeout-sec 10] [--notional 110000] [--daily-loss-cap 6000]
      [--radar-start 12:30] [--radar-end 15:00]
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

from bot.radar import StormRadar

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
        self.prints: deque[tuple[float, float, str, float | None]] = deque(maxlen=2000)
        self.position = None          # dict(side, size, entry, t_entry, tp)
        self.pending: RestingLimit | None = None
        self.last_entry_ts = 0.0
        self.daily_pnl = 0.0
        self.trades = 0
        self.misses = 0
        self.log_path = Path("data/scalp_paper.jsonl")
        self.log_path.parent.mkdir(exist_ok=True)
        self.session = requests.Session()
        self.radar = StormRadar(start=args.radar_start, end=args.radar_end)
        self.radar_armed: bool | None = None   # None until the first check

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
        ``size`` is appended after the fields RestingLimit reads (ts, price,
        side) so its ``rec[0]``/``rec[1]``/``rec[2]`` indexing is untouched;
        it feeds sigma60_bps/v60_btc below.
        """
        now = time.time()
        for ex in message or []:
            try:
                price = float(ex["price"])
            except (KeyError, TypeError, ValueError):
                continue
            try:
                size = float(ex["size"])
            except (KeyError, TypeError, ValueError):
                size = None
            self.prints.append((now, price, str(ex.get("side") or ""), size))

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

    def pre_signal_features(self, t_signal: float) -> tuple[float | None, float | None]:
        """sigma60_bps, v60_btc over the 60s strictly before ``t_signal``.

        Mirrors sigma_60/V60 in scripts/research_exit_surface.py (1s
        bitFlyer log-return std, and summed print volume, both looking only
        at seconds before the signal) so live entry-side events carry the
        features that study's TP30-vs-TP10 high-vol tercile tilt (+8 bps
        paired, n=9) will eventually be judged against. bf_price here is the
        last print in each whole second of ``self.prints``, since no
        resampled 1s series is kept.
        """
        window = [(ts, price, size) for ts, price, side, size in self.prints
                 if t_signal - 60.0 <= ts < t_signal]
        sizes = [size for _, _, size in window if size is not None]
        v60 = sum(sizes) if sizes else None
        bars: dict[int, float] = {}
        for ts, price, _ in window:
            bars[int(ts)] = price
        prices = [bars[s] for s in sorted(bars)]
        import math
        rets = [math.log(b / a) * 1e4 for a, b in zip(prices, prices[1:])
                if a > 0 and b > 0]
        if len(rets) < 10:
            return None, v60
        n = len(rets)
        mean = sum(rets) / n
        var = sum((r - mean) ** 2 for r in rets) / (n - 1)
        return math.sqrt(var), v60

    # ---- storm radar ------------------------------------------------------
    def update_radar(self, now: float) -> bool:
        """Refresh the armed flag, logging a "radar_state" event on each flip."""
        armed = self.radar.is_armed(now)
        if armed != self.radar_armed:
            self.radar_armed = armed
            state = self.radar.state(now)
            self.log("radar_state", radar_armed=armed, window=state["window"],
                     reason=state["reason"], thr_bps=self.threshold_bps())
        return armed

    def threshold_bps(self) -> float:
        """Entry threshold in force right now: armed -> --thr-armed-bps."""
        return self.args.thr_armed_bps if self.radar_armed else self.args.thr_bps

    # ---- trading loop -----------------------------------------------------
    async def engine(self):
        while True:
            await asyncio.sleep(0.25)
            now = time.time()
            # checked every tick so arm/disarm flips are logged even while a
            # position or a resting order is open
            self.update_radar(now)
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
                # every exit clock is measured from the FILL, which is t_entry
                self.check_exit(now, feeds_ok)
                continue
            if not feeds_ok:
                continue
            ret = self.leader_return_bps()
            if ret is None or abs(ret) < self.threshold_bps():
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
        self.position = {"side": side, "size": size, "entry": px, "t_entry": now,
                         "tp": self.make_tp(side, px, size, now)}
        sigma60_bps, v60_btc = self.pre_signal_features(now)
        self.log("entry", entry_mode="taker", side=side, price=px, size=size,
                 signal_bps=ret, radar_armed=bool(self.radar_armed),
                 thr_bps=self.threshold_bps(), bid=self.bid, ask=self.ask,
                 sigma60_bps=sigma60_bps, v60_btc=v60_btc)

    def place_limit(self, side: str, ret: float, now: float) -> None:
        """Rest a virtual limit at the near touch (bid for long, ask for short)."""
        limit = self.bid if side == "LONG" else self.ask
        self.pending = RestingLimit(
            side=side, limit=limit, t_signal=now,
            timeout_sec=self.args.fill_timeout_sec,
            size=self.args.notional / limit, signal_bps=ret)
        sigma60_bps, v60_btc = self.pre_signal_features(now)
        self.log("limit_placed", entry_mode="maker", side=side, limit=limit,
                 size=self.pending.size, signal_bps=ret,
                 radar_armed=bool(self.radar_armed),
                 thr_bps=self.threshold_bps(),
                 fill_timeout_sec=self.args.fill_timeout_sec,
                 bid=self.bid, ask=self.ask,
                 sigma60_bps=sigma60_bps, v60_btc=v60_btc)

    def check_pending(self, now: float) -> None:
        """Fill the resting order off the tape, or cancel it on timeout."""
        order = self.pending
        hit = order.first_fill(self.prints)
        if hit is not None:
            fill_ts, _ = hit
            self.pending = None
            # maker fill: at the limit price, no spread and no slippage
            self.position = {"side": order.side, "size": order.size,
                             "entry": order.limit, "t_entry": fill_ts,
                             "tp": self.make_tp(order.side, order.limit,
                                                order.size, fill_ts)}
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
            # features as of the original signal, not the miss (now)
            sigma60_bps, v60_btc = self.pre_signal_features(order.t_signal)
            self.log("missed", entry_mode="maker", side=order.side,
                     limit=order.limit, signal_bps=order.signal_bps,
                     taker_basis=basis, misses=self.misses,
                     waited_sec=round(now - order.t_signal, 3),
                     bid=self.bid, ask=self.ask,
                     sigma60_bps=sigma60_bps, v60_btc=v60_btc)

    def make_tp(self, side: str, entry: float, size: float, t_entry: float):
        """Take-profit limit --tp-bps beyond the fill, or None in taker mode.

        Exiting a LONG rests an ASK above the fill, which a taker BUY lifts —
        that is a RestingLimit whose *own* side is SHORT (fills at or through
        from below); exiting a SHORT is the mirror. Its window runs from the
        fill to the fallback deadline, so a print outside it cannot fill it.
        """
        if self.args.exit != "maker_tp":
            return None
        edge = 1 if side == "LONG" else -1
        limit = entry * (1 + edge * self.args.tp_bps / 1e4)
        return RestingLimit(side="SHORT" if side == "LONG" else "LONG",
                            limit=limit, t_signal=t_entry,
                            timeout_sec=self.args.fallback_sec, size=size)

    def check_exit(self, now: float, feeds_ok: bool) -> None:
        """Fill the take-profit off the tape, else exit taker on the deadline."""
        pos = self.position
        tp = pos["tp"]
        if tp is not None and tp.first_fill(self.prints) is not None:
            self.close_position("tp_maker", price=tp.limit)
            return
        deadline = self.args.fallback_sec if tp is not None else self.args.hold_sec
        if now - pos["t_entry"] >= deadline and feeds_ok:
            self.close_position("fallback_taker" if tp is not None else "taker")

    def close_position(self, exit_kind: str = "taker", price: float | None = None):
        pos = self.position
        # a maker TP passes its own fill price: AT the limit, no spread, no
        # slippage, no fee. Every other exit crosses and pays both.
        if price is None:
            price = self.bid if pos["side"] == "LONG" else self.ask
            price *= 1 - (SLIPPAGE_BPS / 1e4) * (1 if pos["side"] == "LONG" else -1)
        direction = 1 if pos["side"] == "LONG" else -1
        pnl = (price - pos["entry"]) * pos["size"] * direction
        self.daily_pnl += pnl
        self.trades += 1
        self.position = None
        self.log("exit", entry_mode=self.args.entry, exit_kind=exit_kind,
                 side=pos["side"], price=price,
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
    ap.add_argument("--thr-armed-bps", type=float, default=10.0,
                    help="entry threshold while the storm radar is armed "
                         "(12:30-15:00 UTC by default); replay evidence "
                         "says a lower armed bar hurts, so it matches "
                         "--thr-bps until paper data argues otherwise")
    ap.add_argument("--radar-start", default="12:30", help="radar window start, UTC HH:MM")
    ap.add_argument("--radar-end", default="15:00", help="radar window end, UTC HH:MM")
    ap.add_argument("--window-sec", type=float, default=5.0)
    ap.add_argument("--hold-sec", type=float, default=60.0)
    ap.add_argument("--cooldown-sec", type=float, default=30.0)
    ap.add_argument("--entry", choices=("maker", "taker"), default="maker")
    ap.add_argument("--exit", choices=("maker_tp", "taker"), default="maker_tp",
                    help="maker_tp: rest a take-profit --tp-bps beyond the "
                         "fill and fall back to a taker exit after "
                         "--fallback-sec (E2 of scripts/research_scalp_exits.py, "
                         "a variance decision pending paper evidence); "
                         "taker: legacy hold --hold-sec then exit taker")
    ap.add_argument("--tp-bps", type=float, default=10.0)
    ap.add_argument("--fallback-sec", type=float, default=120.0)
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
