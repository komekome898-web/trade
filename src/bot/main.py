"""Bot entry point: wires all modules and runs the trading loop.

Startup safety sequence:
1. Load settings (mode resolution refuses ambiguous/half-armed LIVE).
2. Register secrets for log redaction.
3. Kill switch state check — a tripped switch from a previous run blocks trading.
4. In LIVE mode only: verify API permissions contain no withdrawal access.

The loop is fail-closed: any unhandled exception out of the loop body trips the
persisted kill switch before the process dies, so a supervisor restart lands on
the refusal in `main()` instead of resuming trading in an unknown state. The
FIRST reason recorded wins (`_trip_once`) — a failure while shutting down must
not overwrite the diagnosis of what actually went wrong.
"""
from __future__ import annotations

import logging
import time

from bot.exchange.bitflyer_client import BitflyerClient, BitflyerError, NetworkError
from bot.execution.paper import PaperExecutor
from bot.logging_setup import log_decision, redact, register_secret, setup_logging
from bot.market_data.feed import CandleBuilder, MarketDataAnomaly, MarketDataFeed
from bot.monitoring.notifier import DiscordNotifier, Notifier, NullNotifier
from bot.monitoring.status import StatusWriter
from bot.order_management.manager import OrderManager
from bot.order_management.order import DuplicateOrderError, OrderStore
from bot.portfolio.portfolio import Portfolio
from bot.risk.kill_switch import KillReason, KillSwitch
from bot.risk.pre_trade_checks import AccountState, OrderRequest, PreTradeChecker
from bot.settings import Mode, Settings, load_settings
from bot.strategy import STRATEGIES
from bot.strategy.base import SignalType
from bot.strategy.composite import DEFAULT_CONFIG_PATH as COMPOSITE_CONFIG_PATH
from bot.strategy.composite import ModuleContext, OverlayState

import pandas as pd

logger = logging.getLogger("bot.main")


def build_app(settings: Settings, *, client: BitflyerClient | None = None,
              notifier: Notifier | None = None) -> "TradingApp":
    client = client or BitflyerClient(settings.api_key, settings.api_secret)
    if notifier is None:
        notifier = (DiscordNotifier(settings.discord_webhook_url)
                    if settings.discord_webhook_url else NullNotifier())
    return TradingApp(settings, client, notifier)


class TradingApp:
    def __init__(self, settings: Settings, client: BitflyerClient, notifier: Notifier):
        self.settings = settings
        self.client = client
        self.notifier = notifier
        cfg = settings.config
        md = cfg.get("market_data", {})
        self.feed = MarketDataFeed(
            client, settings.product_code,
            max_staleness_sec=float(md.get("max_staleness_sec", 60)),
            max_price_jump_pct=float(md.get("max_price_jump_pct", 5.0)),
            max_spread_pct=float(md.get("max_spread_pct", 1.0)),
        )
        self.candles = CandleBuilder(int(cfg.get("candle_interval_sec", 60)))
        strat_cfg = cfg.get("strategy", {})
        strat_name = strat_cfg.get("name", "ema_cross")
        # Repo-anchored absolute path (bot.strategy.composite): the guard must
        # test the SAME file the strategy will read, whatever the process cwd.
        if strat_name == "composite" and not COMPOSITE_CONFIG_PATH.exists():
            # Refuse rather than silently running the composite with an empty
            # module set: a missing file must not look like a validated config.
            raise FileNotFoundError(
                f"strategy.name is 'composite' but {COMPOSITE_CONFIG_PATH} is "
                "missing; restore it (module gates live there) before starting."
            )
        strategy_cls = STRATEGIES[strat_name]
        self.strategy = strategy_cls(strat_cfg.get("params", {}))
        leader_cfg = cfg.get("leader", {})
        self.leader_feed = None
        if leader_cfg.get("symbol"):
            from bot.market_data.external_feed import BinanceFeed
            self.leader_feed = BinanceFeed(
                symbol=str(leader_cfg["symbol"]),
                interval_sec=int(cfg.get("candle_interval_sec", 60)),
            )
        from bot.products import load_products
        products = load_products(".")  # bot always runs from the repo root
        self.product = products.get(settings.product_code)
        if self.product is None:
            raise ValueError(f"unknown product {settings.product_code}; add it to config/products.yaml")
        self.sfd_guard_pct = float(cfg.get("sfd_guard_pct", 4.5))
        self.stop_loss_pct = float(cfg.get("stop_loss_pct", 0.5))
        self.use_flow_candles = bool(cfg.get("use_flow_candles", False))
        self._sfd_divergence: float | None = None

        self.kill_switch = KillSwitch()
        self.checker = PreTradeChecker(settings.risk_limits, self.kill_switch,
                                       product=self.product)
        self.store = OrderStore()
        costs = cfg.get("costs", {})

        if settings.mode is Mode.LIVE:
            # Imported here so paper runs never even load the live module.
            from bot.execution.live import LiveExecutor
            self._verify_live_preconditions()
            gateway = LiveExecutor(settings, client)
            initial_equity = self._fetch_jpy_balance()
        else:
            initial_equity = float(cfg.get("paper_equity_jpy", 6000.0))
            gateway = PaperExecutor(
                quote_fn=self._quote,
                balance_jpy=initial_equity,
                taker_fee_pct=self.product.taker_fee_pct,
                slippage_pct=float(costs.get("slippage_pct", 0.05)),
                allow_short=self.product.shortable,
                leverage=self.product.leverage,
            )

        self.orders = OrderManager(self.store, gateway, self.kill_switch)
        self.portfolio = Portfolio(initial_equity_jpy=initial_equity)
        # Risk-overlay brake state survives a restart: a crash mid-losing-streak
        # must not hand the next process a clean slate and full size.
        #
        # It is kept HERE, never copied into the portfolio. The portfolio's
        # consecutive_losses / equity_peak_jpy feed the hard pre-trade risk
        # checks, which trip the kill switch; they must stay facts about what
        # THIS process traded. Seeding them from disk would trip the switch on
        # inherited history — and again on the next boot after an operator
        # reset, a deadlock no reset can clear. Sizing may inherit the brake;
        # the kill switch may not. (bot/strategy/composite.py module docstring.)
        self.overlay_state = OverlayState.load(boot_equity_jpy=initial_equity)
        self._overlay_suppressed_day: int | None = None
        self.status = StatusWriter()
        self.status.status.mode = settings.mode.value
        self._api_errors_in_row = 0
        from bot.market_data.feed import SpreadRecorder
        self.spread_recorder = SpreadRecorder(f"data/spread_{settings.product_code}.csv")

    # ---- helpers ----------------------------------------------------------
    def _quote(self, symbol: str) -> tuple[float, float]:
        tick = self.feed.last_tick
        if tick is None:
            raise MarketDataAnomaly("no quote available")
        return tick.best_bid, tick.best_ask

    def _fetch_jpy_balance(self) -> float:
        balances = self.client.get_balance()
        jpy = next((b for b in balances if b.get("currency_code") == "JPY"), None)
        return float(jpy["available"]) if jpy else 0.0

    def _verify_live_preconditions(self) -> None:
        perms = self.client.get_permissions()
        bad = [p for p in perms if any(k in p.lower() for k in ("withdraw", "sendcoin", "sendmoney"))]
        if bad:
            raise PermissionError(
                f"API key has withdrawal-related permissions {bad}; refusing LIVE mode."
            )

    # ---- one iteration of the trading loop --------------------------------
    def step(self) -> None:
        if self.kill_switch.is_tripped:
            return
        try:
            tick = self.feed.poll_ticker()
            self._api_errors_in_row = 0
            self.status.status.api_connected = True
            self.spread_recorder.record(tick)
        except MarketDataAnomaly as e:
            self.kill_switch.trip(KillReason.MARKET_DATA_ANOMALY, str(e))
            self._on_kill(str(e))
            return
        except (BitflyerError, NetworkError) as e:
            self._api_errors_in_row += 1
            self.status.status.error_count += 1
            self.status.status.consecutive_api_errors = self._api_errors_in_row
            self.status.status.api_connected = False
            if self._api_errors_in_row >= self.settings.risk_limits.max_api_errors_in_row:
                self.kill_switch.trip(KillReason.API_ERRORS, f"{self._api_errors_in_row} in a row: {e}")
                self._on_kill(str(e))
            return

        if self.leader_feed is not None:
            self.leader_feed.poll()  # failure -> stale leader -> strategy holds

        if self.use_flow_candles:
            # candles from real executions (volume + taker sides) for
            # order-flow strategies; a failed poll just delays the candle
            try:
                completed = self.feed.poll_executions(self.candles)
            except (BitflyerError, NetworkError):
                completed = []
            finished = completed[-1] if completed else None
        else:
            finished = self.candles.add_trade(tick.timestamp, tick.price, 0.0)
        self._update_status(tick.price)
        if finished is None:
            return  # decide only on completed candles

        candles_df = pd.DataFrame([c.__dict__ for c in self.candles.completed])
        if self.leader_feed is not None:
            candles_df["leader_close"] = pd.Series(
                [self.leader_feed.close_for(c.start) for c in self.candles.completed],
                dtype="float64",
            )
        # protective stop-loss overrides the strategy
        pos = self.portfolio.position_size
        if pos != 0.0:
            loss_pct = -self.portfolio.unrealized_pnl_jpy(tick.price) / \
                self.portfolio.position_notional_jpy(tick.price) * 100
            if loss_pct >= self.stop_loss_pct:
                side = "SELL" if pos > 0 else "BUY"
                order = self._try_order(side, tick, size=abs(pos))
                log_decision(
                    logger, symbol=self.settings.product_code, price=tick.price,
                    strategy_signal="STOP_LOSS", indicator_values={"loss_pct": loss_pct},
                    decision="ORDER_SENT" if order else "REJECTED",
                    reason=f"protective stop: unrealized -{loss_pct:.2f}%",
                    order_id=order.local_id if order else None,
                    pnl=self.portfolio.realized_pnl_jpy,
                )
                self._update_status(tick.price)
                return

        signal = self.strategy.on_candles(candles_df)
        # Optional module gate (CompositeStrategy). Duck-typed: strategies
        # without the hook are untouched. Position-aware so a module can never
        # veto a signal that closes an open position.
        gate = getattr(self.strategy, "gate_entry", None)
        if callable(gate):
            signal = gate(signal, ModuleContext(candles=candles_df,
                                                timestamp=tick.timestamp,
                                                position_size=pos,
                                                signal_ts=time.time()))
        decision, order = "HOLD", None

        if signal.type is SignalType.BUY:
            if pos < 0:      # close short
                order = self._try_order("BUY", tick, size=abs(pos))
                decision = "ORDER_SENT" if order else "REJECTED"
            elif pos == 0.0 and not self._sfd_blocked():
                order = self._try_order("BUY", tick)
                decision = "ORDER_SENT" if order else "REJECTED"
        elif signal.type is SignalType.SELL:
            if pos > 0:      # close long
                order = self._try_order("SELL", tick, size=pos)
                decision = "ORDER_SENT" if order else "REJECTED"
            elif pos == 0.0 and self.product.shortable and not self._sfd_blocked():
                order = self._try_order("SELL", tick)
                decision = "ORDER_SENT" if order else "REJECTED"
        elif signal.type is SignalType.CLOSE and pos != 0.0:
            side = "SELL" if pos > 0 else "BUY"
            order = self._try_order(side, tick, size=abs(pos))
            decision = "ORDER_SENT" if order else "REJECTED"

        log_decision(
            logger, symbol=self.settings.product_code, price=tick.price,
            strategy_signal=signal.type.value, indicator_values=signal.indicators,
            decision=decision, reason=signal.reason,
            order_id=order.local_id if order else None,
            order_size=order.size if order else None,
            order_price=order.price if order else None,
            execution_status=order.state.value if order else None,
            pnl=self.portfolio.realized_pnl_jpy,
        )
        self._update_status(tick.price)

    def _sfd_blocked(self) -> bool:
        """For FX products, refuse NEW entries when the FX/spot divergence is
        close to the SFD band (5%). Closing positions is always allowed."""
        if self.product.market_type != "FX":
            return False
        try:
            spot = float(self.client.ticker("BTC_JPY")["ltp"])
            fx = self.feed.last_tick.price if self.feed.last_tick else spot
            self._sfd_divergence = (fx - spot) / spot * 100
        except Exception:
            return True  # cannot verify divergence -> stay out (safe side)
        if abs(self._sfd_divergence) >= self.sfd_guard_pct:
            logger.warning("SFD guard active", extra={"data": {
                "event": "sfd_guard", "divergence_pct": self._sfd_divergence}})
            return True
        return False

    def _entry_size_factor(self, mark_price: float) -> float:
        """Risk-overlay multiplier for a NEW entry, when the active strategy
        exposes one (duck-typed).

        Reads the OVERLAY's own peak and loss streak (self.overlay_state), not
        the portfolio's: the portfolio's counters belong to the hard risk
        checks and must not be re-pointed at persisted state. Current equity is
        a live fact and comes from the portfolio.
        """
        factor_fn = getattr(self.strategy, "size_factor", None)
        if not callable(factor_fn):
            return 1.0
        equity = self.portfolio.equity_jpy(mark_price)
        peak = max(self.overlay_state.equity_peak_jpy, equity)
        return float(factor_fn(peak, equity, self.overlay_state.consecutive_losses))

    def _quantize(self, budget_jpy: float, price: float) -> float:
        """Round an order budget DOWN to the product's size granularity.

        Plain truncation, bit-identical to the pre-composite champion's sizing
        expression. An epsilon was briefly added here; it is an undocumented
        change to the sizing of the strategy under paper validation (it can
        round one step UP), and the composite is a carrier, not a rewrite.
        """
        steps = int(budget_jpy / price / self.product.min_size)
        return round(steps * self.product.min_size, 8)

    def _scale_size(self, size: float, factor: float) -> float:
        """Apply the overlay factor to an already-approved SIZE, re-quantized.

        Directly on the size, not `_quantize(size * factor * price, price)`:
        multiplying by the price and dividing it straight back out is not the
        identity in binary floating point, and at some prices the round trip
        lands one ulp off a step boundary and moves the result a whole
        min_size step — in either direction, including UP, above the size the
        risk checks approved times the factor. The scaled size is a function
        of (size, factor) alone, so the price must not appear in it. This is
        the form scripts/validate_composite.py G1b asserts.
        """
        return round(int(size * factor / self.product.min_size)
                     * self.product.min_size, 8)

    def _warn_overlay_suppressed(self, factor: float, price: float, full_size: float) -> None:
        """One notifier warning per UTC day; the log line is per occurrence.

        A suppressed entry means the overlay has shrunk sizing below what the
        product can trade — worth telling the operator once, not once a tick.
        """
        logger.warning("entry suppressed: overlay size below product minimum", extra={"data": {
            "event": "size_below_min", "reason": "risk_overlay",
            "size_factor": factor, "full_size": full_size,
            "min_notional_jpy": self.product.min_size * price}})
        day = int(time.time() // 86400)
        if self._overlay_suppressed_day == day:
            return
        self._overlay_suppressed_day = day
        self.notifier.send(
            "OVERLAY SUPPRESSING ENTRIES",
            f"risk overlay factor {factor:.2f} scales the entry below "
            f"{self.product.min_size} {self.settings.product_code}; entries are "
            "being skipped until the drawdown / loss-streak brake releases.")

    def _try_order(self, side: str, tick, size: float | None = None):
        price = tick.best_ask if side == "BUY" else tick.best_bid
        opening = size is None
        if opening:
            # margin products size off equity x leverage; spot off half equity
            equity = self.portfolio.equity_jpy(tick.price)
            if self.product.is_margin:
                budget = min(self.settings.risk_limits.max_order_size_jpy,
                             equity * self.product.leverage * 0.9)
            else:
                budget = min(self.settings.risk_limits.max_order_size_jpy, equity / 2)
            # FULL (unscaled) size: the risk checks below judge this one, so the
            # overlay can only narrow an approved order, never rescue a rejected
            # one. Retrying a refused entry at half size would quietly widen the
            # champion's permission boundary (e.g. the daily-loss brake).
            size = self._quantize(budget, price)
            if size < self.product.min_size:
                logger.warning("order skipped: budget below product minimum", extra={"data": {
                    "event": "size_below_min", "reason": "budget_below_min",
                    "budget_jpy": budget,
                    "min_notional_jpy": self.product.min_size * price}})
                return None
        # entry orders risk stop_loss_pct of price; closing orders reduce risk
        if opening:
            stop = price * (1 - self.stop_loss_pct / 100) if side == "BUY" \
                else price * (1 + self.stop_loss_pct / 100)
        else:
            stop = price
        request = OrderRequest(self.settings.product_code, side, size, price,
                               stop_price=stop)
        account = AccountState(
            balance_jpy=self.portfolio.equity_jpy(tick.price) - (
                0.0 if self.product.is_margin else self.portfolio.position_notional_jpy(tick.price)),
            position_notional_jpy=self.portfolio.position_notional_jpy(tick.price),
            open_orders=len(self.store.active_orders(self.settings.product_code)),
            daily_pnl_jpy=self.portfolio.daily_pnl_jpy(tick.price),
            drawdown_pct=self.portfolio.drawdown_pct(tick.price),
            consecutive_losses=self.portfolio.consecutive_losses,
            position_size=self.portfolio.position_size,
        )
        decision = self.checker.check(request, account)
        if not decision.approved:
            logger.warning("order rejected by risk checks", extra={"data": {
                "event": "risk_reject", "reasons": decision.reasons}})
            if self.kill_switch.is_tripped:
                self._on_kill("; ".join(decision.reasons))
            return None
        if opening:
            # Approved at full size -> the overlay may now shrink it. Only ever
            # downward, and re-quantized to the product's granularity.
            factor = self._entry_size_factor(tick.price)
            if factor < 1.0:
                scaled = self._scale_size(size, factor)
                if scaled < self.product.min_size:
                    self._warn_overlay_suppressed(factor, price, size)
                    return None
                # All three numbers, so the line can be checked by hand: the
                # approved full size, the factor, and what was actually sent.
                logger.info("entry scaled by risk overlay", extra={"data": {
                    "event": "overlay_scaled_entry", "reason": "risk_overlay",
                    "full_size": size, "size_factor": factor,
                    "scaled_size": scaled,
                    "consecutive_losses": self.overlay_state.consecutive_losses}})
                size = scaled
        try:
            order = self.orders.submit(symbol=self.settings.product_code, side=side, size=size)
        except (DuplicateOrderError, RuntimeError) as e:
            logger.error("submit refused", extra={"data": {"event": "submit_refused", "error": str(e)}})
            return None
        # Refresh once for immediate (market/paper) fills and book them.
        order = self.orders.refresh(order)
        if order.state.value in ("FILLED", "PARTIALLY_FILLED") and order.filled_size > 0:
            fill_price = order.avg_fill_price or price
            fee = fill_price * order.filled_size * self.product.taker_fee_pct / 100
            realized = self.portfolio.on_fill(symbol=order.symbol, side=side,
                                              size=order.filled_size, price=fill_price,
                                              fee_jpy=fee)
            if not opening:
                # A CLOSING fill, decided by what was ordered rather than by
                # its P&L: a close that happened to break exactly even
                # (realized + fee == 0) still moved the equity path and still
                # has to checkpoint the brake. Opening fills change no
                # overlay state, so they are not written.
                self._persist_overlay_state(tick.price, realized)
            self.status.status.last_execution = f"{side} {order.filled_size} @ {fill_price}"
        self.status.status.last_order = f"{side} {size} ({order.state.value})"
        return order

    def _persist_overlay_state(self, mark_price: float,
                               realized_pnl_jpy: float) -> None:
        """Advance and checkpoint the overlay brake after every closed trade.

        The overlay keeps its OWN streak and peak (see __init__); the portfolio
        keeps the ones the risk checks read.
        """
        self.overlay_state.on_closed_trade(realized_pnl_jpy,
                                           self.portfolio.equity_jpy(mark_price))
        self.overlay_state.save()

    def _on_kill(self, detail: str) -> None:
        """Shut trading down cleanly. Every step is independently guarded: a
        failure in one must not skip the others."""
        try:
            self.orders.cancel_all_active(self.settings.product_code)
        except Exception:
            logger.exception("cancel_all_active failed during kill switch")
        self.status.status.kill_switch = self.kill_switch.state
        self.status.write()
        try:
            self.notifier.send("KILL SWITCH", detail, urgent=True)
        except Exception:
            # A dead webhook must not become an exception that propagates back
            # into run_forever and overwrites the kill reason we just recorded.
            logger.exception("kill switch notification failed")
        logger.critical("kill switch tripped", extra={"data": {
            "event": "kill_switch", "detail": detail, "state": self.kill_switch.state}})

    def _update_status(self, price: float) -> None:
        equity = self.portfolio.equity_jpy(price)
        # Fold the equity the bot is looking at RIGHT NOW into the overlay's
        # running peak. The peak is a property of the equity curve, not of the
        # trade log: a run-up handed back inside one open position is a real
        # drawdown, and a peak that only moved on closes would engage the brake
        # a trade late. Persisting still happens on the closing fill only.
        self.overlay_state.observe_equity(equity)
        s = self.status.status
        s.running = not self.kill_switch.is_tripped
        s.last_price = price
        s.balance_jpy = equity
        s.position_size = self.portfolio.position_size
        s.daily_pnl_jpy = self.portfolio.daily_pnl_jpy(price)
        s.total_pnl_jpy = self.portfolio.realized_pnl_jpy + self.portfolio.unrealized_pnl_jpy(price)
        s.max_drawdown_pct = max(s.max_drawdown_pct, self.portfolio.drawdown_pct(price))
        s.last_data_time = self.feed.last_update
        s.kill_switch = self.kill_switch.state
        s.overlay = self._overlay_status(price)
        s.active_modules = self._active_module_names()
        self.status.write()

    def _overlay_status(self, price: float) -> dict | None:
        """Overlay brake, for status.json — None when the strategy has no
        overlay (xborder_momentum), so an operator can tell "not applicable"
        from "applicable and currently at full size".

        `dd_pct` is measured live against the OVERLAY's peak (the same peak
        `_entry_size_factor` uses), not the portfolio's: the portfolio's
        drawdown is already reported as `max_drawdown_pct` and belongs to the
        hard risk checks.
        """
        if not callable(getattr(self.strategy, "size_factor", None)):
            return None
        equity = self.portfolio.equity_jpy(price)
        peak = max(self.overlay_state.equity_peak_jpy, equity)
        return {
            "factor": self._entry_size_factor(price),
            "consecutive_losses": self.overlay_state.consecutive_losses,
            "dd_pct": round((1.0 - equity / peak) * 100, 3) if peak > 0 else 0.0,
        }

    def _active_module_names(self) -> list[str] | None:
        """Enabled composite modules, for status.json. None when the strategy
        has no module framework at all — an empty list means "framework
        present, nothing enabled", which is a different fact."""
        modules = getattr(self.strategy, "active_modules", None)
        if modules is None:
            return None
        return [m.name for m in modules]

    def run_forever(self) -> None:
        poll = float(self.settings.config.get("poll", {}).get("ticker_sec", 5))
        report_every = float(self.settings.config.get("notifications", {})
                             .get("status_report_interval_sec", 3600))
        last_report = time.time()
        self.notifier.send("BOT START", f"mode={self.settings.mode.value} "
                                        f"product={self.settings.product_code}")
        while not self.kill_switch.is_tripped:
            # The WHOLE body is guarded, not just step(): a failure in the
            # freshness check, the status report or the notifier is just as
            # much an unknown state as a failure in step(). KeyboardInterrupt
            # and SystemExit are BaseExceptions and deliberately pass straight
            # through — an operator stopping the bot must not leave a tripped
            # switch behind for the next start to refuse.
            try:
                self.step()
                self.feed.check_freshness()
                if time.time() - last_report >= report_every:
                    self.notifier.send("STATUS", self.status.format_report())
                    last_report = time.time()
                time.sleep(poll)
            except MarketDataAnomaly as e:
                self._trip_once(KillReason.MARKET_DATA_ANOMALY, str(e))
                self._on_kill(str(e))
                break
            except Exception as e:
                # An unexpected exception is an unknown state, not a hiccup: a
                # bare crash would let systemd/the watchdog restart the process
                # straight back into trading. Trip the (persisted) kill switch
                # first, so the restarted process refuses to trade until a human
                # has investigated and reset it (see main()).
                detail = redact(f"unhandled exception in loop: {e!r}")
                self._trip_once(KillReason.UNHANDLED_EXCEPTION, detail)
                logger.exception("unhandled exception in loop; kill switch tripped")
                self._on_kill(detail)
                raise
        self.notifier.send("BOT STOPPED", str(self.kill_switch.state), urgent=True)

    def _trip_once(self, reason: KillReason, detail: str) -> None:
        """Trip the kill switch only if it is not already tripped.

        The FIRST reason is the diagnosis. An exception raised while handling a
        kill (a dead Discord webhook, a locked status file) surfaces here as a
        second trip; re-tripping would overwrite 'market_data_anomaly: stale
        feed' with 'unhandled exception in the notifier' and send the operator
        after the wrong fault.
        """
        if self.kill_switch.is_tripped:
            logger.warning("kill switch already tripped; keeping the original reason",
                           extra={"data": {"event": "kill_switch_secondary",
                                           "ignored_reason": reason.value,
                                           "ignored_detail": detail,
                                           "state": self.kill_switch.state}})
            return
        self.kill_switch.trip(reason, detail)


def main() -> int:
    settings = load_settings(".")
    setup_logging()
    for secret in (settings.api_key, settings.api_secret, settings.discord_webhook_url):
        register_secret(secret.reveal())
    app = build_app(settings)
    if app.kill_switch.is_tripped:
        print(f"kill switch is tripped, refusing to start: {app.kill_switch.state}")
        print("After investigating, reset with: python -c \"from bot.risk.kill_switch import "
              "KillSwitch; KillSwitch().reset(operator_confirm=True)\"")
        return 1
    app.run_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
