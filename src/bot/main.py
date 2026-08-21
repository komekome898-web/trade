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
from bot.exchange.resilience import (
    ApiHealthRecorder, ApiObserver, ConditionMonitor, EndpointClass,
    ExchangeCondition, FailureClass, RetryPolicy, Timeouts,
    condition_multiplier, load_resilience_config,
)
from bot.execution.paper import PaperExecutor
from bot.logging_setup import log_decision, redact, register_secret, setup_logging
from bot.market_data.feed import CandleBuilder, MarketDataAnomaly, MarketDataFeed
from bot.monitoring.notifier import DiscordNotifier, Notifier, NullNotifier
from bot.monitoring.status import StatusWriter
from bot.order_management.manager import OrderManager
from bot.order_management.order import DuplicateOrderError, OrderStore
from bot.order_management.reconciler import AutoReconciler, QueryOnlyExchange
from bot.portfolio.persistence import PaperPosition, PaperState, utc_date_of_day
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

# How often the loop re-reads the state of every non-terminal LIVE order. The
# book must not be allowed to believe an order is resting when the venue has
# already filled, cancelled or expired it: a stale non-terminal record is what
# makes `OrderStore.create` refuse the next order — including a protective
# close. Cheap and bounded (one diagnostic GET per open order, at most this
# often), and best effort: a failed sweep changes nothing.
ORDER_SWEEP_SEC = 30.0

# Below this, a "fill" is float noise on a size the venue already reported.
FILL_EPSILON = 1e-12


def _num(value) -> float:
    """Venue numbers arrive as strings, None or junk. Unusable -> 0.0."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _net_position(rows) -> tuple[float, float]:
    """(signed size, average entry price) from getpositions rows.

    bitFlyer answers with one row per open lot, normally all on the same side.
    The signed sum is the position; the price is weighted over the rows on the
    NET side only, so even a mixed listing yields the entry price of what is
    actually held rather than a blend of both directions.
    """
    signed = 0.0
    for row in rows or ():
        size = _num(row.get("size"))
        signed += size if str(row.get("side") or "").upper() == "BUY" else -size
    if abs(signed) <= FILL_EPSILON:
        return 0.0, 0.0
    wanted = "BUY" if signed > 0 else "SELL"
    notional = quantity = 0.0
    for row in rows or ():
        if str(row.get("side") or "").upper() != wanted:
            continue
        size, price = _num(row.get("size")), _num(row.get("price"))
        if size <= 0 or price <= 0:
            continue
        notional += size * price
        quantity += size
    return signed, (notional / quantity if quantity > 0 else 0.0)


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

        # ---- execution resilience (bot/exchange/resilience.py) -------------
        # Wired BEFORE the gateway so the very first API call the bot makes is
        # already instrumented: the paper bot's job right now is to accrue real
        # degradation telemetry from the home PC.
        self.res_cfg = load_resilience_config(cfg.get("resilience"))
        res_cfg = self.res_cfg
        self._base_timeouts = Timeouts(connect_sec=res_cfg.connect_timeout_sec,
                                       read_sec=res_cfg.read_timeout_sec)
        self.condition_monitor = ConditionMonitor(
            window_sec=res_cfg.condition_window_sec,
            degraded_latency_ms=res_cfg.degraded_latency_ms,
            critical_latency_ms=res_cfg.critical_latency_ms,
            health_ttl_sec=res_cfg.health_ttl_sec,
        )
        self.api_recorder = ApiHealthRecorder(res_cfg.api_health_csv)
        client.attach_observer(ApiObserver(self.condition_monitor, self.api_recorder))
        client.configure(
            timeouts=self._base_timeouts,
            retry_policy=RetryPolicy(max_tries=res_cfg.retry_max_tries,
                                     total_budget_sec=res_cfg.retry_budget_sec))
        self.condition = ExchangeCondition.NORMAL
        self._health_poll_sec = res_cfg.health_poll_sec
        self._last_health_poll = 0.0
        self._last_order_sweep = 0.0
        self._degraded_entry_seq = 0
        # UNREGISTERED behavior change, default OFF: throttling entries under
        # DEGRADED/CRITICAL alters what the champion trades and would
        # contaminate the running paper sample. gethealth=STOP suppression is
        # not behind the flag (see `_entry_allowed_under_condition`).
        self._entry_gating = res_cfg.entry_gating
        # The staleness watchdog scales with the same multiplier as the read
        # timeout: at CRITICAL a single read may legitimately take 30s, and a
        # fixed 60s threshold would trip the kill switch on our OWN widened
        # timeouts rather than on a real loss of data.
        self._base_staleness_sec = self.feed.max_staleness_sec

        self.kill_switch = KillSwitch()
        self.checker = PreTradeChecker(settings.risk_limits, self.kill_switch,
                                       product=self.product)
        self.store = OrderStore()
        costs = cfg.get("costs", {})

        reconciler = None
        if settings.mode is Mode.LIVE:
            # Imported here so paper runs never even load the live module.
            from bot.execution.live import LiveExecutor
            self._verify_live_preconditions()
            gateway = LiveExecutor(settings, client)
            initial_equity = self._fetch_jpy_balance()
            # LIVE only: PAPER's executor is local, so an ambiguous send cannot
            # happen there and a reconciler would have nothing to reconcile.
            reconciler = AutoReconciler(QueryOnlyExchange(client),
                                        budget_sec=res_cfg.reconcile_budget_sec)
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

        # Fills the portfolio has been told about but whose watermark could not
        # be persisted. See `_book_fill_delta` / `_mark_booked`.
        self._applied_bookings: set[tuple[str, float]] = set()
        self.orders = OrderManager(self.store, gateway, self.kill_switch,
                                   reconciler=reconciler, notifier=notifier,
                                   # A self-cancel is a fill discovery path
                                   # like any other: an order the venue partly
                                   # filled before the cancel landed is booked
                                   # through the same idempotent path.
                                   on_canceled_fill=self._book_fill_delta)
        self.portfolio = Portfolio(initial_equity_jpy=initial_equity)
        # PAPER only: reload the paper book (cumulative P&L, fill count, today's
        # daily P&L, the open position). LIVE never touches the file — there the
        # exchange holds the book and is reconciled against, and a JSON file
        # pretending to know a real position would be worse than no file at all.
        self.paper_state: PaperState | None = None
        self._restored_trade_count = 0
        self._position_opened_ts: float | None = None
        if settings.mode is Mode.LIVE:
            self._adopt_venue_position()
        else:
            self._restore_paper_state(gateway)
        self._paper_day = self.portfolio.daily_day_index
        # Boot equity for the overlay INCLUDES the restored realized P&L: the
        # overlay rebuilds its peak as boot_equity / dd_frac, so it has to be
        # handed the equity the book actually starts at. The unrealized term
        # needs a mark price this early boot does not have; the overlay folds
        # the real equity in on the first `_update_status`, and its peak only
        # ever moves UP, so an open loss shrinks SIZE (the overlay's whole job)
        # rather than being missed. The portfolio's own peak cannot wait like
        # that — it feeds the kill switch — and is anchored mark-to-market in
        # `_restore_paper_state`. Realized is 0 on a fresh/live book, so this
        # is the previous value unchanged there.
        boot_equity = initial_equity + self.portfolio.realized_pnl_jpy
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
        self.overlay_state = OverlayState.load(boot_equity_jpy=boot_equity)
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

    # ---- LIVE boot reconciliation (LIVE ONLY) -----------------------------
    def _adopt_venue_position(self) -> None:
        """Seed the portfolio from what the EXCHANGE says we hold.

        LIVE keeps no local book on purpose (see `_restore_paper_state`): the
        venue owns the position. But "no local book" was implemented as "start
        flat", so every LIVE restart booted a portfolio that believed it held
        nothing while bitFlyer held a real position. Nothing would have
        corrected it either — the sweep only re-reads orders THIS book knows,
        and a position opened before the restart has no such order. The
        consequences are the two the whole booking path exists to prevent: the
        protective stop never arms (there is nothing, as far as the portfolio
        knows, to protect), and the next entry signal opens on top of the live
        position instead of being refused by MAX_POSITION_SIZE.

        So the boot ASKS, on the diagnostic timeouts, and adopts the venue's
        net position — size, side and average entry price — loudly, in the log
        and to the operator, because silently inheriting a position is exactly
        the kind of thing an operator must be able to see happening.

        A failure to ask is NOT "assume flat". It is refusal: the kill switch
        is tripped (`system_error`, 'live boot reconciliation failed') so
        `main()` refuses to start and no order can be placed, and a human
        decides. Assuming flat is the phantom-flat state again, this time
        chosen deliberately.
        """
        try:
            with self.client.diagnostic_call():
                rows = self.client.get_positions(self.settings.product_code)
        except Exception as e:
            self._refuse_live_boot(
                "could not read the venue's positions",
                f"getpositions for {self.settings.product_code} could not be "
                f"read ({type(e).__name__}), so the bot does not know whether "
                f"a position is open.",
                error=type(e).__name__)
            return
        size, entry_price = _net_position(rows)
        if size == 0.0:
            logger.info("LIVE boot: the venue reports no open position",
                        extra={"data": {"event": "live_boot_flat",
                                        "symbol": self.settings.product_code}})
            return
        if entry_price <= 0:
            # A position with no usable entry price cannot be protected: the
            # stop, the daily brake and the drawdown are all computed from it.
            # Knowing a position exists and nothing else is not a state to
            # trade from either.
            self._refuse_live_boot(
                "the venue reports a position with no usable entry price",
                f"getpositions reports {size} {self.settings.product_code} "
                f"with no usable entry price, so the position cannot be "
                f"protected.",
                position_size=size)
            return
        p = self.portfolio
        p.position_size = size
        p.avg_entry_price = entry_price
        # Same anchoring as a restored paper book: the drawdown peak and the
        # daily mark are taken at THIS boot's first price, so a position that
        # was already underwater does not trip the brakes before the stop can
        # close it (bot/portfolio/portfolio.py module docstring).
        p.anchor_boot_equity()
        side = "LONG" if size > 0 else "SHORT"
        logger.warning("LIVE boot: adopted venue position", extra={"data": {
            "event": "live_boot_position_adopted",
            "symbol": self.settings.product_code, "side": side,
            "position_size": size, "avg_entry_price": entry_price,
            "rows": len(rows or [])}})
        self._notify("LIVE BOOT: POSITION ADOPTED",
                     f"LIVE boot: adopted venue position {side} {abs(size)} "
                     f"{self.settings.product_code} @ {entry_price}. The bot "
                     f"starts holding it — the protective stop is armed "
                     f"against this position and new entries are sized on top "
                     f"of it.")

    def _refuse_live_boot(self, reason: str, message: str, **data) -> None:
        """Trip the kill switch so the LIVE boot cannot trade, and say why.

        ONE detail string for every way boot reconciliation can fail — the
        operator's next step is the same in all of them (look at bitFlyer,
        then reset), and the specifics are in the log line and the alert.
        """
        logger.critical(f"LIVE boot: {reason}; refusing to trade",
                        extra={"data": {
                            "event": "live_boot_reconcile_failed",
                            "symbol": self.settings.product_code,
                            "reason": reason, **data}})
        self.kill_switch.trip(KillReason.SYSTEM_ERROR,
                              "live boot reconciliation failed")
        self._notify("LIVE BOOT RECONCILIATION FAILED",
                     f"{message} Trading is stopped and NO order can be "
                     f"placed. Check the position on bitFlyer, then reset the "
                     f"kill switch (KillSwitch().reset(operator_confirm=True)).",
                     urgent=True)

    def _notify(self, title: str, message: str, *, urgent: bool = False) -> None:
        """Operator line that must never raise into the caller — the boot path
        included, where a dead webhook would otherwise abort startup."""
        try:
            self.notifier.send(title, message, urgent=urgent)
        except Exception:
            logger.exception("operator notification failed")

    # ---- paper book persistence (PAPER ONLY) ------------------------------
    @property
    def trade_count(self) -> int:
        """Fills booked by this paper book, not by this process.

        A restart used to show 0 here — the console tile, and every reading of
        the paper experiment taken from it, restarted with the process."""
        return self._restored_trade_count + len(self.portfolio.trades)

    def _restore_paper_state(self, gateway: PaperExecutor) -> None:
        """Reload data/paper_state.json into the portfolio and the paper gateway.

        Restored: cumulative realized P&L, the fill count, the open position,
        and today's realized daily P&L — the last one ONLY when the saved date
        is still today (UTC), which `PaperState.daily_pnl_on` decides, and only
        when the file belongs to the product this process is running (a book
        from another product is renamed aside and not read at all; see
        bot/portfolio/persistence.py).

        NOT restored, deliberately: `consecutive_losses` and `equity_peak_jpy`.
        Those feed the HARD pre-trade checks, which trip the kill switch, so
        seeding them from disk would trip it on history this process never
        traded — and again on the next boot after an operator reset, a deadlock
        no reset can clear (bot/strategy/composite.py module docstring). The
        daily P&L is a different kind of fact: it EXPIRES at the UTC rollover,
        so inheriting a spent budget for the rest of the same day is bounded,
        while dropping it let a watchdog restart hand back the whole
        MAX_DAILY_LOSS_JPY allowance mid-day.

        The peak is instead anchored at the MARK-TO-MARKET boot equity
        (`Portfolio.anchor_boot_equity`), and a restored position's unrealized
        P&L is counted into the daily brake only from the first mark this
        process sees. Both brakes therefore measure what happened SINCE this
        boot: a book restored 5% underwater neither reads as an instant
        max-drawdown breach nor spends today's MAX_DAILY_LOSS_JPY budget on a
        loss incurred days ago — either would trip the kill switch before the
        protective stop could close the position, and trip again on the boot
        after every operator reset.
        """
        state = PaperState.load(product_code=self.settings.product_code)
        self.paper_state = state
        p = self.portfolio
        p.realized_pnl_jpy = state.realized_pnl_jpy
        self._restored_trade_count = state.trade_count
        # ONE clock read decides both the day and the date the file's daily
        # figure is judged against (see Portfolio.seed_daily_realized).
        day = p.daily_day_index
        today = utc_date_of_day(day)
        daily = state.daily_pnl_on(today)
        p.seed_daily_realized(daily, day=day)
        position = state.position
        if position is not None and position.side == "SHORT" and not gateway.allow_short:
            # The product is not shortable now; whatever wrote that short is not
            # this configuration. Start flat rather than restore a position the
            # executor could never have opened.
            logger.warning("paper state holds a short on a non-shortable product; "
                           "starting flat", extra={"data": {
                               "event": "paper_state_position_dropped",
                               "symbol": self.settings.product_code}})
            position = None
        if position is not None:
            p.position_size = position.signed_size
            p.avg_entry_price = position.entry_price
            self._position_opened_ts = position.opened_ts
        p.anchor_boot_equity()      # after the position: it is marked to market
        self._restore_gateway(gateway, position, state.realized_pnl_jpy)
        logger.info("paper state restored", extra={"data": {
            "event": "paper_state_restored",
            "realized_pnl_jpy": state.realized_pnl_jpy,
            "trade_count": state.trade_count,
            "daily_pnl_jpy": daily, "daily_date": today,
            "position_size": p.position_size}})

    def _restore_gateway(self, gateway: PaperExecutor,
                         position: PaperPosition | None,
                         realized_pnl_jpy: float) -> None:
        """Put the paper executor back where the portfolio is.

        The executor keeps its own book, and a restart left it flat and at the
        starting balance while the portfolio was long: the exit would then OPEN
        a phantom short in the executor (margin) or be refused for want of
        inventory (spot), and every later fill would be priced off a balance
        that never happened.

        Balance: margin moves by realized P&L and fees only, both already inside
        the portfolio's realized figure. Spot additionally paid the position's
        notional out of cash when it was opened.
        """
        symbol = self.settings.product_code
        gateway.balance_jpy += realized_pnl_jpy
        if position is None:
            return
        gateway.positions[symbol] = position.signed_size
        gateway.entry_prices[symbol] = position.entry_price
        if not gateway.allow_short:
            gateway.balance_jpy -= position.size * position.entry_price

    def _capture_paper_state(self) -> PaperState:
        """Snapshot the paper book.

        The daily figure and the date labelling it come from ONE read of the
        portfolio's clock (`daily_snapshot`): asking the clock a second time
        for the date could straddle a UTC rollover and persist yesterday's
        spent budget under today's date, wedging a fresh day's brake."""
        p = self.portfolio
        day, daily_realized = p.daily_snapshot()
        pos = p.position_size
        if pos == 0.0:
            self._position_opened_ts = None
            position = None
        else:
            if self._position_opened_ts is None:
                self._position_opened_ts = p.clock()
            position = PaperPosition.from_signed(pos, p.avg_entry_price,
                                                 self._position_opened_ts)
        return PaperState(realized_pnl_jpy=p.realized_pnl_jpy,
                          trade_count=self.trade_count,
                          daily_pnl_jpy=daily_realized,
                          daily_date=utc_date_of_day(day),
                          position=position,
                          product_code=self.settings.product_code)

    def _save_paper_state(self) -> None:
        """Checkpoint the paper book. No-op in LIVE mode; best-effort and
        silent otherwise (`PaperState.save` swallows OSError) — bookkeeping must
        never raise into trading."""
        if self.paper_state is None:
            return
        self.paper_state = self._capture_paper_state()
        self.paper_state.save()

    # ---- one iteration of the trading loop --------------------------------
    def step(self) -> None:
        if self.kill_switch.is_tripped:
            return
        # Before the polls, not after: a widened read timeout has to apply to
        # the very call that is struggling, not to the one after it.
        self._refresh_condition()
        self._sweep_open_orders()
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
            self.status.status.error_count += 1
            self.status.status.api_connected = False
            if self._counts_towards_api_errors(e):
                self._api_errors_in_row += 1
                self.status.status.consecutive_api_errors = self._api_errors_in_row
                if self._api_errors_in_row >= self.settings.risk_limits.max_api_errors_in_row:
                    self.kill_switch.trip(KillReason.API_ERRORS,
                                          f"{self._api_errors_in_row} in a row: {e}")
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

    def _sweep_open_orders(self) -> None:
        """Re-read every non-terminal LIVE order, at most once per sweep window.

        Without this the book only learns about an order when something asks
        about it, and a LIMIT order the venue filled, cancelled or expired can
        sit as SUBMITTED forever. That stale record is not merely untidy: the
        duplicate-order guard counts it, so the next order for the symbol is
        refused — and the next order may be the protective stop. `OrderManager`
        can force its way past that wedge, but a book that is simply CURRENT
        never gets into it.

        Whatever it discovers is BOOKED, through the same idempotent path the
        submit path uses (`_book_fill_delta`). A sweep that only tidied the
        record was the worse half of the bug: it moved a filled LIMIT order to
        FILLED and told the portfolio nothing, so the bot read its own flat
        book and opened a second position on top of a real one.

        LIVE only (PAPER fills synchronously, so its records are never stale),
        on the DIAGNOSTIC timeouts, and best effort in the strongest sense: a
        failed refresh leaves the record exactly as it was.

        COST BOUND: one diagnostic GET per non-terminal order, at most once per
        ORDER_SWEEP_SEC. That is bounded at one call per window because
        `OrderStore.create` refuses a new order while ANY non-terminal order
        exists for the symbol — the same invariant `_make_room_for_close` is
        built around. The check below is the cheap statement of it: it is
        LOGGED, never raised, because a surprising book is a reason to look, not
        a reason to kill trading from inside a best-effort sweep.
        """
        if self.settings.mode is not Mode.LIVE:
            return
        now = time.time()
        if now - self._last_order_sweep < ORDER_SWEEP_SEC:
            return
        self._last_order_sweep = now
        try:
            open_orders = self.store.active_orders(self.settings.product_code)
        except Exception:
            logger.exception("order sweep could not read the book")
            return
        if len(open_orders) > 1:
            logger.error("order sweep: more than one non-terminal order",
                         extra={"data": {
                             "event": "sweep_invariant_broken",
                             "symbol": self.settings.product_code,
                             "count": len(open_orders),
                             "local_ids": [o.local_id for o in open_orders]}})
        for order in open_orders:
            try:
                with self.client.diagnostic_call():
                    refreshed = self.orders.refresh(order)
            except Exception as e:
                logger.warning("order sweep refresh failed", extra={"data": {
                    "event": "order_sweep_failed", "local_id": order.local_id,
                    "error": type(e).__name__}})
                continue
            try:
                self._book_fill_delta(refreshed)
            except Exception:
                # Booking is the whole point of the sweep, so a failure here is
                # loud — but it still must not take the trading loop down: the
                # watermark is untouched, so the next sweep books the same
                # delta again.
                logger.exception("order sweep could not book a discovered fill",
                                 extra={"data": {
                                     "event": "sweep_booking_failed",
                                     "local_id": refreshed.local_id}})

    def _counts_towards_api_errors(self, error: Exception) -> bool:
        """Should this failure move MAX_API_ERRORS_IN_ROW towards a kill?

        The counter exists for "the API is answering us with a definite no we
        cannot handle" — a revoked key, a rejected signature. It is NOT the
        degradation detector, and it must not become one: tripping the kill
        switch is a FULL freeze, closes included (see `_on_kill`), so a slow
        venue tripping it would recreate the 2019 trap the resilience layer was
        built to avoid.

        Not counted:
        - anything classified SAFE_RETRY (transport failure, 429, 5xx on a read
          endpoint). It has already been retried under a widened timeout, and
          the thing it endangers — a stale price — is owned by the market-data
          staleness watchdog, whose threshold scales with the same multiplier.
        - any PUBLIC-endpoint failure while the venue is DEGRADED or worse.
          That failure IS the degradation; it is already reflected in the
          condition, the timeouts and (when enabled) the entry gate.

        A failure carrying NO classification at all counts. Every exemption
        above is granted on positive evidence about what went wrong; "we do not
        know what this was" is not evidence, and treating it as one turned an
        unclassified error into an error the counter could never see.
        """
        failure = getattr(error, "failure", None)
        if failure is None:
            return True
        if failure.failure_class is FailureClass.SAFE_RETRY:
            return False
        if self.condition is not ExchangeCondition.NORMAL \
                and failure.endpoint_class is EndpointClass.PUBLIC:
            # The ticker poll is a public endpoint; a failure there while
            # degraded says nothing new.
            return False
        return True

    # ---- exchange condition ------------------------------------------------
    def _refresh_condition(self) -> None:
        """Fold /v1/gethealth into the monitor and apply the resulting level.

        Best effort throughout, and OFF the hot path in the sense that matters:
        the poll runs on the short fixed DIAGNOSTIC timeouts (connect 3s / read
        5s, one attempt), never on the widened trading ones, so a CRITICAL
        venue cannot make this call stall a whole trading step. A failed poll is
        telemetry we did not get, not a reason to stop trading — it is skipped
        silently and the reading expires on its own
        (`ConditionMonitor.health_ttl_sec`), so a stale health string can no
        longer hold the bot at a level forever.
        """
        now = time.time()
        if now - self._last_health_poll >= self._health_poll_sec:
            self._last_health_poll = now
            try:
                with self.client.diagnostic_call():
                    status = self.client.health(self.settings.product_code)
                self.condition_monitor.observe_health((status or {}).get("status"))
            except Exception:
                pass
        condition = self.condition_monitor.condition
        if condition is not self.condition:
            previous = self.condition
            self.condition = condition
            # DEGRADED/CRITICAL widen the READ timeout only: a slow venue
            # answers late, it does not refuse the connection.
            self.client.apply_condition(condition)
            self._apply_staleness_budget(condition)
            logger.warning("exchange condition changed", extra={"data": {
                "event": "exchange_condition",
                "from": previous.value, "to": condition.value,
                "max_staleness_sec": self.feed.max_staleness_sec,
                **self.condition_monitor.snapshot()}})

    def _apply_staleness_budget(self, condition: ExchangeCondition) -> None:
        """Scale the market-data staleness threshold with the read timeout.

        Same multiplier, one definition (`resilience.condition_multiplier`): a
        widened read timeout must never race the watchdog that is supposed to
        catch a genuinely dead feed. At NORMAL this restores the configured
        value exactly.
        """
        self.feed.max_staleness_sec = (self._base_staleness_sec
                                       * condition_multiplier(condition))

    def _entry_allowed_under_condition(self) -> bool:
        """Gate for NEW entries ONLY.

        Closing orders are never routed through here (see `_try_order`: the
        gate sits inside `if opening:`), which is the whole point. The 2019
        trap was a position that could not be exited while bitFlyer was
        degraded — degradation must only ever REDUCE exposure, exactly like
        pre_trade_checks' `increases_exposure`.

        Two different rules, deliberately:

        - gethealth = STOP is ALWAYS honoured. The venue is halted; a new order
          cannot succeed, so refusing it is not a strategy change.
        - DEGRADED/CRITICAL throttling is behind `resilience.entry_gating`,
          DEFAULT FALSE. Skipping entries because latency is high changes what
          the champion trades, and that is a strategy change which has to be
          pre-registered and measured (.claude/skills/research-protocol) before
          it may touch the running paper sample.
        """
        if self.condition_monitor.exchange_stopped:
            logger.warning("entry suppressed: exchange halted", extra={"data": {
                "event": "entry_suppressed", "reason": "exchange_stopped",
                **self.condition_monitor.snapshot()}})
            return False
        if not self._entry_gating:
            return True
        condition = self.condition
        if condition is ExchangeCondition.NORMAL:
            return True
        if condition is ExchangeCondition.CRITICAL:
            logger.warning("entry suppressed: exchange condition", extra={"data": {
                "event": "entry_suppressed", "reason": "exchange_condition",
                **self.condition_monitor.snapshot()}})
            return False
        # DEGRADED: halve the entry frequency — take one opportunity, skip the
        # next. Closing and the protective stop are untouched.
        self._degraded_entry_seq += 1
        if self._degraded_entry_seq % 2 == 1:
            return True
        logger.warning("entry skipped: exchange DEGRADED (frequency halved)",
                       extra={"data": {
                           "event": "entry_skipped", "reason": "exchange_degraded",
                           **self.condition_monitor.snapshot()}})
        return False

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
            # Degradation gate, first thing and inside `opening` only: a
            # CLOSING order can never reach it.
            if not self._entry_allowed_under_condition():
                return None
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
            order = self.orders.submit(symbol=self.settings.product_code,
                                       side=side, size=size, opening=opening)
        except (DuplicateOrderError, RuntimeError) as e:
            # `opening` travels with the order because the manager treats a
            # refused CLOSE as an emergency (cancel the resting order, retry
            # once, then alert + kill switch) rather than as a skipped tick.
            # By the time one surfaces here the operator has already been told.
            logger.error("submit refused", extra={"data": {
                "event": "submit_refused", "opening": opening,
                "side": side, "size": size, "error": str(e)}})
            return None
        # Refresh once for immediate (market/paper) fills. GUARDED, like the
        # sweep's: this refresh is a diagnostic, and a failure inside it — a
        # dead read, an InvalidTransition on a record another path already
        # moved — must not propagate out of the order path and become an
        # unhandled exception that trips the kill switch on a placed order.
        try:
            order = self.orders.refresh(order)
        except Exception as e:
            logger.warning("post-submit refresh failed", extra={"data": {
                "event": "submit_refresh_failed", "local_id": order.local_id,
                "error": type(e).__name__}})
            order = self.store.get(order.local_id) or order
        # Booking runs on the record UNCONDITIONALLY, refresh or no refresh:
        # `submit` itself may already have resolved the order to FILLED or
        # PARTIALLY_FILLED through auto-reconciliation, in which case there was
        # nothing for `refresh` to do. `_book_fill_delta` is the single
        # idempotent path and books only what is not booked yet.
        order = self._book_fill_delta(order, fallback_price=price)
        self.status.status.last_order = f"{side} {size} ({order.state.value})"
        return order

    # ---- THE fill-booking path --------------------------------------------
    def _book_fill_delta(self, order, *, fallback_price: float | None = None):
        """Book everything this order has filled but not yet been booked for.

        ONE path, called from EVERY place a fill can be discovered — the
        submit-path refresh, the periodic sweep (`_sweep_open_orders`), and
        auto-reconciliation (whose resolution `_try_order` books off the record
        it returns), plus the cancel path (`OrderManager.cancel_orders`, whose
        refreshed records arrive here through `on_canceled_fill`). A watermark
        is what makes that safe: the delta is `filled_size` minus what the
        portfolio already holds for this order, so the same fill seen by three
        paths is booked once and a fill seen only by one of them is booked at
        all.

        Before this existed, booking lived inside `_try_order` alone. A LIMIT
        order that filled later was discovered by the sweep, which moved the
        record to FILLED and told nobody — the portfolio stayed flat while the
        venue held a real position. The bot then read its own flat book, took
        the next entry signal, and doubled a live position; the protective stop
        never armed, because as far as the portfolio was concerned there was
        nothing to protect.

        Fees come from the product spec, the price from the exchange's own
        record (`avg_fill_price`); `fallback_price` is the caller's
        decision-time quote and is used only when the venue reported no average
        price at all. Which of the four sources was used is logged as
        `price_source`, because "the position moved" and "the position moved at
        a price the venue never confirmed" are different facts.

        TWO watermarks, not one. `booked_size` is persisted with the order and
        survives a restart; `_applied_bookings` is this process's memory of
        what it has already handed to the portfolio. They differ only when
        `mark_booked` FAILED after the portfolio had already moved — and
        without the second one the next discovery would read the stale
        persisted watermark and book the same fill again, doubling a real
        position to fix a bookkeeping error.

        RESIDUAL, LIVE ONLY: a process that dies between the portfolio move and
        a successful `mark_booked` loses the in-session set. The restarted
        process re-discovers the order through the sweep and books it a second
        time — LIVE has no local book to compare against (the venue is the
        book), so nothing can tell the two apart. It is bounded to the orders
        that were open at the crash and is why the LIVE boot reconciles against
        getpositions (`_adopt_venue_position`), which re-seats the portfolio on
        the venue's own answer. PAPER is safe by ordering: `paper_state` is
        written BEFORE the watermark, and a restored PAPER book never revisits
        a terminal order (there is no sweep in PAPER).
        """
        applied = self._applied_watermark(order)
        delta = float(order.filled_size) - applied
        if delta <= FILL_EPSILON:
            # Nothing new for the portfolio. The persisted watermark may still
            # be behind it, though — retrying that write is the only thing left
            # to do, and it is what clears the in-session record.
            if order.unbooked_size > FILL_EPSILON:
                return self._mark_booked(order, applied)
            return order
        fill_price, price_source = self._fill_price_of(order, fallback_price)
        if not fill_price or fill_price <= 0:
            # No usable price means no honest booking. Leave the watermark
            # alone so the next discovery books it, and say so loudly — a
            # position the portfolio does not know about is the phantom-flat
            # state this whole path exists to prevent.
            logger.error("fill observed with no usable price; NOT booked",
                         extra={"data": {
                             "event": "fill_unpriced", "local_id": order.local_id,
                             "symbol": order.symbol, "side": order.side,
                             "unbooked_size": delta}})
            return order
        # Closing is decided by the position the fill lands on, not by what the
        # caller intended: the sweep discovers fills with no intent attached.
        pos_before = self.portfolio.position_size
        closing = pos_before != 0.0 and ((pos_before > 0) != (order.side == "BUY"))
        fee = fill_price * delta * self.product.taker_fee_pct / 100
        target = float(order.filled_size)
        realized = self.portfolio.on_fill(symbol=order.symbol, side=order.side,
                                          size=delta, price=fill_price,
                                          fee_jpy=fee)
        # The portfolio has moved. Record that in-session BEFORE anything that
        # can fail, so a failed watermark write cannot make the next discovery
        # replay this same fill.
        self._applied_bookings.add((order.local_id, target))
        tick = self.feed.last_tick
        mark_price = tick.price if tick is not None else fill_price
        if closing:
            # A CLOSING fill, decided by what it did to the position rather
            # than by its P&L: a close that happened to break exactly even
            # still moved the equity path and still has to checkpoint the
            # brake. Opening fills change no overlay state.
            self._persist_overlay_state(mark_price, realized)
        # Every fill, opening included: an unsaved entry is a position the next
        # process does not know it holds.
        #
        # BEFORE `mark_booked`, deliberately. In PAPER the two writes are the
        # crash window, and this order closes it: `paper_state` carries the
        # position itself, and a PAPER restart restores the book and never
        # looks at a terminal order again (there is no sweep in PAPER), so a
        # crash in between loses only the watermark — never the position, and
        # never by doubling it. In LIVE this call is a no-op.
        self._save_paper_state()
        booked = self._mark_booked(order, target)
        self.status.status.last_execution = f"{order.side} {delta} @ {fill_price}"
        logger.info("fill booked", extra={"data": {
            "event": "fill_booked", "local_id": order.local_id,
            "symbol": order.symbol, "side": order.side, "size": delta,
            "price": fill_price, "price_source": price_source,
            "fee_jpy": fee, "realized_pnl_jpy": realized,
            "state": order.state.value, "position_size": self.portfolio.position_size}})
        return booked

    def _fill_price_of(self, order,
                       fallback_price: float | None) -> tuple[float | None, str]:
        """(price, source) for a fill, best evidence first.

        `venue_avg` is the exchange's own average for the order and is the only
        one that is a FACT about the fill; the rest are approximations, in
        descending order of how close they are to the moment it happened.
        """
        if order.avg_fill_price:
            return float(order.avg_fill_price), "venue_avg"
        if fallback_price:
            return float(fallback_price), "decision_quote"
        if order.price:
            return float(order.price), "order_price"
        tick = self.feed.last_tick
        if tick is not None and tick.price:
            return float(tick.price), "last_tick"
        return None, "none"

    def _applied_watermark(self, order) -> float:
        """How much of this order the PORTFOLIO already holds.

        The persisted watermark, raised by anything this process applied but
        could not persist (`_mark_booked`). Persisted-only would replay a fill
        whose watermark write failed; in-session-only would forget every fill
        booked before a restart.
        """
        applied = float(order.booked_size)
        for local_id, booked_to in self._applied_bookings:
            if local_id == order.local_id:
                applied = max(applied, booked_to)
        return applied

    def _mark_booked(self, order, booked_to: float):
        """Persist the watermark; on failure keep the in-session record.

        A failure here is CRITICAL and not retried in place: the portfolio is
        already correct, the store is behind, and the only harm is that the
        next discovery of this order sees an unbooked delta. `_applied_bookings`
        is what stops it from acting on that, and the next discovery retries
        this write.
        """
        try:
            booked = self.store.mark_booked(order.local_id, booked_to)
        except Exception:
            logger.critical("fill booked into the portfolio but the watermark "
                            "could not be persisted; it will NOT be re-applied",
                            extra={"data": {
                                "event": "mark_booked_failed",
                                "local_id": order.local_id,
                                "symbol": order.symbol,
                                "booked_to": booked_to}})
            self._applied_bookings.add((order.local_id, float(booked_to)))
            return order
        # Persisted: the in-session record has done its job for this order.
        self._applied_bookings = {
            entry for entry in self._applied_bookings
            if entry[0] != order.local_id or entry[1] > float(booked.booked_size)}
        return booked

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
            # FIRST, and before the message is built: cancelling a resting
            # order finalizes whatever it filled on the way out, and that fill
            # is booked from inside this call (`on_canceled_fill`). The OPEN
            # POSITION line below is then the position the operator will
            # actually find on bitFlyer, not the one from before the cancel.
            self.orders.cancel_all_active(self.settings.product_code)
        except Exception:
            logger.exception("cancel_all_active failed during kill switch")
        self._save_paper_state()
        self.status.status.kill_switch = self.kill_switch.state
        self.status.write()
        try:
            self.notifier.send("KILL SWITCH", self._kill_message(detail), urgent=True)
        except Exception:
            # A dead webhook must not become an exception that propagates back
            # into run_forever and overwrites the kill reason we just recorded.
            logger.exception("kill switch notification failed")
        logger.critical("kill switch tripped", extra={"data": {
            "event": "kill_switch", "detail": detail,
            "position_size": self.portfolio.position_size,
            "state": self.kill_switch.state}})

    def _kill_message(self, detail: str) -> str:
        """A tripped kill switch is a FULL freeze — the pre-trade checks refuse
        every order while it is tripped, closing orders included. That is the
        deliberate contract (a bot in an unknown state must not keep trading),
        but it means an OPEN POSITION is now the operator's to manage. Say so,
        with the position, instead of leaving them to infer it.
        """
        position = self.portfolio.position_size
        if position == 0.0:
            return detail
        side = "LONG" if position > 0 else "SHORT"
        return (f"{detail}\n\nOPEN POSITION: {side} {abs(position)} "
                f"{self.settings.product_code}. The bot will NOT close it — a "
                f"tripped kill switch blocks every order, exits included. Close "
                f"it by hand on bitFlyer if you want it flat, then investigate "
                f"and reset the switch "
                f"(KillSwitch().reset(operator_confirm=True)).")

    def _roll_paper_day(self) -> None:
        """Persist the daily-P&L reset when the UTC day turns under a running
        process. Portfolio owns the rollover itself (`_roll_day`); this only
        notices that it happened, off the SAME clock, and checkpoints it — once
        a day, so an idle process does not rewrite the file every tick."""
        if self.paper_state is None:
            return
        day = self.portfolio.daily_day_index
        if day != self._paper_day:
            self._paper_day = day
            self._save_paper_state()

    def _update_status(self, price: float) -> None:
        equity = self.portfolio.equity_jpy(price)
        # Fold the equity the bot is looking at RIGHT NOW into the overlay's
        # running peak. The peak is a property of the equity curve, not of the
        # trade log: a run-up handed back inside one open position is a real
        # drawdown, and a peak that only moved on closes would engage the brake
        # a trade late. Persisting still happens on the closing fill only.
        self.overlay_state.observe_equity(equity)
        self._roll_paper_day()
        s = self.status.status
        s.running = not self.kill_switch.is_tripped
        s.last_price = price
        s.balance_jpy = equity
        s.position_size = self.portfolio.position_size
        s.trade_count = self.trade_count
        s.daily_pnl_jpy = self.portfolio.daily_pnl_jpy(price)
        s.total_pnl_jpy = self.portfolio.realized_pnl_jpy + self.portfolio.unrealized_pnl_jpy(price)
        s.max_drawdown_pct = max(s.max_drawdown_pct, self.portfolio.drawdown_pct(price))
        s.last_data_time = self.feed.last_update
        s.kill_switch = self.kill_switch.state
        s.overlay = self._overlay_status(price)
        s.active_modules = self._active_module_names()
        snap = self.condition_monitor.snapshot()
        s.api_condition = snap["condition"]
        s.api_health_status = snap["health"]
        s.api_health_age_sec = snap["health_age_sec"]
        s.api_latency_ms = snap["latency_ms"]
        s.api_error_rate = snap["error_rate"]
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
        try:
            self._run_loop(poll, report_every, last_report)
        finally:
            # Every exit checkpoints the paper book: a clean stop, a kill, a
            # crash on its way out, and Ctrl-C (a BaseException that passes
            # straight through the loop's guards). Fills are saved as they
            # happen, so this only ever tops up the day/rollover fields — but it
            # is the difference between a stop being continuous and being a
            # silent partial reset.
            self._save_paper_state()
        self.notifier.send("BOT STOPPED", str(self.kill_switch.state), urgent=True)

    def _run_loop(self, poll: float, report_every: float, last_report: float) -> None:
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
