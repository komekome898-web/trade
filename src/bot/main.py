"""Bot entry point: wires all modules and runs the trading loop.

Startup safety sequence:
1. Load settings (mode resolution refuses ambiguous/half-armed LIVE).
2. Register secrets for log redaction.
3. Kill switch state check — a tripped switch from a previous run blocks trading.
4. In LIVE mode only: verify API permissions contain no withdrawal access.
"""
from __future__ import annotations

import logging
import time

from bot.exchange.bitflyer_client import BitflyerClient, BitflyerError, NetworkError
from bot.execution.paper import PaperExecutor
from bot.logging_setup import log_decision, register_secret, setup_logging
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
        strategy_cls = STRATEGIES[strat_cfg.get("name", "ema_cross")]
        self.strategy = strategy_cls(strat_cfg.get("params", {}))
        self.kill_switch = KillSwitch()
        self.checker = PreTradeChecker(settings.risk_limits, self.kill_switch)
        self.store = OrderStore()
        costs = cfg.get("costs", {})

        if settings.mode is Mode.LIVE:
            # Imported here so paper runs never even load the live module.
            from bot.execution.live import LiveExecutor
            self._verify_live_preconditions()
            gateway = LiveExecutor(settings, client)
            initial_equity = self._fetch_jpy_balance()
        else:
            gateway = PaperExecutor(
                quote_fn=self._quote,
                balance_jpy=6000.0,
                taker_fee_pct=float(costs.get("taker_fee_pct", 0.15)),
                slippage_pct=float(costs.get("slippage_pct", 0.05)),
            )
            initial_equity = 6000.0

        self.orders = OrderManager(self.store, gateway, self.kill_switch)
        self.portfolio = Portfolio(initial_equity_jpy=initial_equity)
        self.status = StatusWriter()
        self.status.status.mode = settings.mode.value
        self._api_errors_in_row = 0

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

        finished = self.candles.add_trade(tick.timestamp, tick.price, 0.0)
        self._update_status(tick.price)
        if finished is None:
            return  # decide only on completed candles

        candles_df = pd.DataFrame([c.__dict__ for c in self.candles.completed])
        signal = self.strategy.on_candles(candles_df)
        decision, reject_reasons, order = "HOLD", [], None

        if signal.type is SignalType.BUY and self.portfolio.position_size == 0.0:
            order = self._try_order("BUY", tick)
            decision = "ORDER_SENT" if order else "REJECTED"
        elif signal.type is SignalType.SELL and self.portfolio.position_size > 0.0:
            order = self._try_order("SELL", tick, size=self.portfolio.position_size)
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

    def _try_order(self, side: str, tick, size: float | None = None):
        price = tick.best_ask if side == "BUY" else tick.best_bid
        if size is None:
            notional = min(self.settings.risk_limits.max_order_size_jpy,
                           self.portfolio.initial_equity_jpy / 2)
            size = round(notional / price, 6)
        request = OrderRequest(self.settings.product_code, side, size, price)
        account = AccountState(
            balance_jpy=self.portfolio.equity_jpy(tick.price) - self.portfolio.position_notional_jpy(tick.price),
            position_notional_jpy=self.portfolio.position_notional_jpy(tick.price),
            open_orders=len(self.store.active_orders(self.settings.product_code)),
            daily_pnl_jpy=self.portfolio.daily_pnl_jpy(tick.price),
            drawdown_pct=self.portfolio.drawdown_pct(tick.price),
            consecutive_losses=self.portfolio.consecutive_losses,
        )
        decision = self.checker.check(request, account)
        if not decision.approved:
            logger.warning("order rejected by risk checks", extra={"data": {
                "event": "risk_reject", "reasons": decision.reasons}})
            if self.kill_switch.is_tripped:
                self._on_kill("; ".join(decision.reasons))
            return None
        try:
            order = self.orders.submit(symbol=self.settings.product_code, side=side, size=size)
        except (DuplicateOrderError, RuntimeError) as e:
            logger.error("submit refused", extra={"data": {"event": "submit_refused", "error": str(e)}})
            return None
        # Refresh once for immediate (market/paper) fills and book them.
        order = self.orders.refresh(order)
        if order.state.value in ("FILLED", "PARTIALLY_FILLED") and order.filled_size > 0:
            fill_price = order.avg_fill_price or price
            fee = fill_price * order.filled_size * float(
                self.settings.config.get("costs", {}).get("taker_fee_pct", 0.15)) / 100
            self.portfolio.on_fill(symbol=order.symbol, side=side,
                                   size=order.filled_size, price=fill_price, fee_jpy=fee)
            self.status.status.last_execution = f"{side} {order.filled_size} @ {fill_price}"
        self.status.status.last_order = f"{side} {size} ({order.state.value})"
        return order

    def _on_kill(self, detail: str) -> None:
        try:
            self.orders.cancel_all_active(self.settings.product_code)
        except Exception:
            logger.exception("cancel_all_active failed during kill switch")
        self.status.status.kill_switch = self.kill_switch.state
        self.status.write()
        self.notifier.send("KILL SWITCH", detail, urgent=True)
        logger.critical("kill switch tripped", extra={"data": {
            "event": "kill_switch", "detail": detail, "state": self.kill_switch.state}})

    def _update_status(self, price: float) -> None:
        s = self.status.status
        s.running = not self.kill_switch.is_tripped
        s.last_price = price
        s.balance_jpy = self.portfolio.equity_jpy(price)
        s.position_size = self.portfolio.position_size
        s.daily_pnl_jpy = self.portfolio.daily_pnl_jpy(price)
        s.total_pnl_jpy = self.portfolio.realized_pnl_jpy + self.portfolio.unrealized_pnl_jpy(price)
        s.max_drawdown_pct = max(s.max_drawdown_pct, self.portfolio.drawdown_pct(price))
        s.last_data_time = self.feed.last_update
        s.kill_switch = self.kill_switch.state
        self.status.write()

    def run_forever(self) -> None:
        poll = float(self.settings.config.get("poll", {}).get("ticker_sec", 5))
        report_every = float(self.settings.config.get("notifications", {})
                             .get("status_report_interval_sec", 3600))
        last_report = time.time()
        self.notifier.send("BOT START", f"mode={self.settings.mode.value} "
                                        f"product={self.settings.product_code}")
        while not self.kill_switch.is_tripped:
            self.step()
            try:
                self.feed.check_freshness()
            except MarketDataAnomaly as e:
                self.kill_switch.trip(KillReason.MARKET_DATA_ANOMALY, str(e))
                self._on_kill(str(e))
                break
            if time.time() - last_report >= report_every:
                self.notifier.send("STATUS", self.status.format_report())
                last_report = time.time()
            time.sleep(poll)
        self.notifier.send("BOT STOPPED", str(self.kill_switch.state), urgent=True)


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
