"""data/paper_state.json: the paper book survives a restart (PAPER ONLY).

The safety-relevant half is first: a restart must not hand back a spent
MAX_DAILY_LOSS_JPY budget, must not forget an open position (the protective
stop is the thing that closes it), and must change nothing about the kill
switch, the overlay brake or LIVE mode.
"""
from __future__ import annotations

import json
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pytest

import bot.main
from bot.market_data.feed import Tick
from bot.monitoring.notifier import NullNotifier
from bot.portfolio.persistence import PaperPosition, PaperState, utc_date
from bot.portfolio.portfolio import Portfolio
from bot.risk.kill_switch import KillReason, KillSwitch
from bot.risk.pre_trade_checks import AccountState, OrderRequest
from bot.settings import Mode, RiskLimits, Secret, Settings
from tests.conftest import FakeResponse, FakeSession
from tests.test_app_fx_integration import drive
from tests.test_composite import LEADER, TICKS, app_config, build_test_app

REPO = Path(__file__).resolve().parents[1]
STATE = Path("data") / "paper_state.json"
SYMBOL = "FX_BTC_JPY"
PRICE = 1e7

DAY0 = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc).timestamp()
DAY1 = DAY0 + 86400


@pytest.fixture
def workdir(tmp_path, monkeypatch):
    shutil.copytree(REPO / "config", tmp_path / "config")
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def clock(monkeypatch):
    """Freeze the PORTFOLIO's clock — the one clock the daily window uses, so
    every restart in a test lands on a UTC day the test chose."""
    holder = {"now": DAY0}
    real = Portfolio

    def make_portfolio(*args, **kwargs):
        kwargs.setdefault("clock", lambda: holder["now"])
        return real(*args, **kwargs)

    monkeypatch.setattr(bot.main, "Portfolio", make_portfolio)
    return holder


def boot(monkeypatch, **kwargs):
    """A paper TradingApp on the champion strategy = one process start."""
    kwargs.setdefault("strategy_name", "xborder_momentum")
    return build_test_app(monkeypatch, **kwargs)


def write_state(**fields) -> None:
    fields.setdefault("product_code", SYMBOL)
    Path("data").mkdir(exist_ok=True)
    STATE.write_text(json.dumps(fields), encoding="utf-8")


def spend_daily(app, jpy: float) -> None:
    """Book `jpy` of REALIZED P&L into today, the way a losing day would."""
    p = app.portfolio
    p.seed_daily_realized(jpy, day=p.daily_day_index)


def read_state() -> dict:
    return json.loads(STATE.read_text(encoding="utf-8"))


def account_of(app, price: float = PRICE) -> AccountState:
    """The AccountState the app assembles in `_try_order` for a margin product."""
    p = app.portfolio
    return AccountState(balance_jpy=p.equity_jpy(price),
                        position_notional_jpy=p.position_notional_jpy(price),
                        open_orders=0, daily_pnl_jpy=p.daily_pnl_jpy(price),
                        drawdown_pct=p.drawdown_pct(price),
                        consecutive_losses=p.consecutive_losses,
                        position_size=p.position_size)


# An entry whose estimated loss (2,400 JPY) fits the full 6,000 daily budget
# but not what is left of it after a 5,000 JPY losing day.
def wide_stop_entry() -> OrderRequest:
    return OrderRequest(SYMBOL, "SELL", 0.012, PRICE, stop_price=PRICE * 1.02)


# ---- the daily-loss brake keeps its memory across a restart ----------------
def test_daily_loss_brake_survives_a_restart_on_the_same_day(workdir, monkeypatch, clock):
    """The bug this file exists for: a watchdog restart used to hand the rest
    of the day a full MAX_DAILY_LOSS_JPY budget."""
    app = boot(monkeypatch)
    app.portfolio.realized_pnl_jpy = -5000.0
    spend_daily(app, -5000.0)
    app._save_paper_state()
    assert read_state()["daily_date"] == "2026-08-20"

    restarted = boot(monkeypatch)
    assert restarted.portfolio.daily_pnl_jpy(PRICE) == pytest.approx(-5000.0)
    assert restarted.portfolio.realized_pnl_jpy == pytest.approx(-5000.0)
    # the pre-trade check outcome, not just the number it reads
    decision = restarted.checker.check(wide_stop_entry(), account_of(restarted))
    assert not decision.approved
    assert any("daily risk budget" in r for r in decision.reasons)
    assert not restarted.kill_switch.is_tripped        # rejected, not killed


def test_the_same_entry_is_approved_on_a_fresh_book(workdir, monkeypatch, clock):
    """Directionality: the order above is refused BECAUSE of the carried-over
    daily loss, not because it is a bad order."""
    app = boot(monkeypatch)
    assert app.checker.check(wide_stop_entry(), account_of(app)).approved


def test_daily_loss_resets_on_the_next_utc_day(workdir, monkeypatch, clock):
    """The carried brake expires — that is what makes carrying it safe."""
    app = boot(monkeypatch)
    app.portfolio.realized_pnl_jpy = -5000.0
    spend_daily(app, -5000.0)
    app._save_paper_state()

    clock["now"] = DAY1
    restarted = boot(monkeypatch)
    assert restarted.portfolio.daily_pnl_jpy(PRICE) == 0.0
    assert restarted.portfolio.realized_pnl_jpy == pytest.approx(-5000.0)   # cumulative stays
    assert restarted.checker.check(wide_stop_entry(), account_of(restarted)).approved


def test_daily_loss_limit_still_trips_the_kill_switch_after_a_restart(
        workdir, monkeypatch, clock):
    app = boot(monkeypatch)
    app.portfolio.realized_pnl_jpy = -6000.0
    spend_daily(app, -6000.0)
    app._save_paper_state()

    restarted = boot(monkeypatch)
    restarted.checker.check(wide_stop_entry(), account_of(restarted))
    assert restarted.kill_switch.is_tripped
    assert restarted.kill_switch.state["reason"] == KillReason.DAILY_LOSS_LIMIT.value


def test_day_rollover_while_running_resets_and_persists(workdir, monkeypatch, clock):
    app = boot(monkeypatch)
    app.portfolio.realized_pnl_jpy = -1000.0
    spend_daily(app, -1000.0)
    app._save_paper_state()

    saves = []
    real_save = app._save_paper_state
    monkeypatch.setattr(app, "_save_paper_state",
                        lambda: (saves.append(1), real_save())[1])
    clock["now"] = DAY1
    app._update_status(PRICE)
    app._update_status(PRICE)                     # same day: no second write
    assert len(saves) == 1
    assert app.portfolio.daily_pnl_jpy(PRICE) == 0.0
    saved = read_state()
    assert saved["daily_date"] == "2026-08-21" and saved["daily_pnl_jpy"] == 0.0
    assert saved["realized_pnl_jpy"] == pytest.approx(-1000.0)


# ---- a restored loss is not TODAY's loss, and not an instant drawdown ------
# N1: the reviewer's deadlock. A position restored 5% underwater used to (a)
# spend the whole of TODAY's MAX_DAILY_LOSS_JPY budget on a move that happened
# on an earlier day and (b) be measured against an equity peak that pretended
# the open loss was not there. Either trips the kill switch on the FIRST order
# the bot tries — which is the protective stop closing that very position — so
# the position can never be closed, and the next boot after an operator reset
# trips again: a reset-proof loop.
GAP = PRICE * 0.95              # the adverse move while the process was down


def yesterdays_long(**overrides) -> None:
    fields = dict(realized_pnl_jpy=0.0, trade_count=1, daily_pnl_jpy=-400.0,
                  daily_date=utc_date(DAY0 - 86400),      # expired: another day
                  position={"side": "LONG", "size": 0.013, "entry_price": PRICE,
                            "opened_ts": DAY0 - 86400})
    fields.update(overrides)
    write_state(**fields)


def test_a_restored_underwater_position_is_not_charged_to_today(workdir, monkeypatch,
                                                                clock):
    yesterdays_long()
    app = boot(monkeypatch)
    p = app.portfolio
    # the loss is fully visible in equity — it is only the two BRAKES that
    # measure from this boot rather than from an entry price days old
    assert p.unrealized_pnl_jpy(GAP) == pytest.approx(-6500.0)
    assert p.equity_jpy(GAP) == pytest.approx(193500.0)
    assert p.daily_pnl_jpy(GAP) == pytest.approx(0.0)     # not today's -6500
    assert p.drawdown_pct(GAP) == 0.0
    assert p.equity_peak_jpy == pytest.approx(193500.0)   # anchored at boot, marked


def test_the_protective_stop_on_a_restored_underwater_position_executes(
        workdir, monkeypatch, clock):
    """The whole point of not charging it to today: the exit must be allowed
    through. It used to be rejected by the brake that the position itself had
    filled up."""
    yesterdays_long()
    app = boot(monkeypatch)
    close = OrderRequest(SYMBOL, "SELL", 0.013, GAP, stop_price=GAP)
    assert app.checker.check(close, account_of(app, GAP)).approved

    drive(app, [(30, GAP), (90, GAP)], LEADER)      # 5% below entry -> the stop
    assert app.portfolio.position_size == 0.0
    assert app.portfolio.realized_pnl_jpy < -6000.0         # the loss was booked
    assert not app.kill_switch.is_tripped
    assert read_state()["position"] is None
    # REALIZED accounting is unchanged: once booked it is today's loss like any
    # other, so the day's budget is spent (and expires with the day). What the
    # anchors changed is that the exit happened at all.
    assert app.portfolio.daily_pnl_jpy(GAP) < -6000.0


def test_an_adverse_move_after_boot_still_counts_toward_the_daily_brake(
        workdir, monkeypatch, clock):
    """Directionality of N1: only the move made BEFORE this boot is exempt. A
    5% drop after the anchor is spent out of today's budget exactly as before,
    and trips the daily-loss kill switch."""
    yesterdays_long()
    app = boot(monkeypatch)
    assert app.portfolio.daily_pnl_jpy(PRICE) == pytest.approx(0.0)   # the anchor
    assert app.portfolio.daily_pnl_jpy(GAP) == pytest.approx(-6500.0)  # since it
    app.checker.check(wide_stop_entry(), account_of(app, GAP))
    assert app.kill_switch.is_tripped
    assert app.kill_switch.state["reason"] == KillReason.DAILY_LOSS_LIMIT.value


def test_an_operator_reset_and_restart_lets_the_bot_trade_again(workdir, monkeypatch,
                                                                clock):
    """The loop the anchors break, end to end: a book already 90% down with an
    underwater position used to re-trip MAX_DRAWDOWN on every boot, so the
    operator's reset was undone before the stop could fire."""
    yesterdays_long(realized_pnl_jpy=-180000.0, trade_count=8,
                    position={"side": "LONG", "size": 0.005, "entry_price": PRICE,
                              "opened_ts": DAY0 - 86400})
    KillSwitch().trip(KillReason.MAX_DRAWDOWN, "the boot that started the loop")
    KillSwitch().reset(operator_confirm=True)     # human, after investigating

    app = boot(monkeypatch)
    assert app.portfolio.drawdown_pct(GAP) == 0.0
    drive(app, [(30, GAP), (90, GAP)], LEADER)    # the stop gets the position out
    assert app.portfolio.position_size == 0.0
    assert not app.kill_switch.is_tripped

    restarted = boot(monkeypatch)                 # and the next boot trades
    assert not restarted.kill_switch.is_tripped
    drive(restarted, TICKS, LEADER)
    assert restarted.portfolio.position_size == pytest.approx(-0.003)
    assert not restarted.kill_switch.is_tripped


# ---- one clock read decides the day, on the way out and on the way in ------
def rolling_clock(reads: list):
    """A clock that turns midnight immediately after its FIRST read: the race
    a second `clock()` call for the date used to lose."""
    def clock() -> float:
        reads.append(1)
        return DAY0 if len(reads) == 1 else DAY1
    return clock


def test_the_saved_daily_figure_and_its_date_come_from_one_read(workdir, monkeypatch,
                                                                clock):
    """Two reads could straddle the rollover and write yesterday's spent budget
    under TODAY's date — a fresh day starting with its brake already spent."""
    app = boot(monkeypatch)
    spend_daily(app, -5000.0)
    app.portfolio.clock = rolling_clock([])

    state = app._capture_paper_state()
    assert (state.daily_pnl_jpy, state.daily_date) == (-5000.0, "2026-08-20")
    # and once the day HAS turned, the pair moves together
    later = app._capture_paper_state()
    assert (later.daily_pnl_jpy, later.daily_date) == (0.0, "2026-08-21")


def test_a_rollover_during_the_restore_drops_the_daily_figure(workdir, monkeypatch):
    """The mirror image on the way in: the date check and the seed read the
    same day index, so a rollover between them can only drop the figure (the
    new day genuinely starts at 0), never book it into the wrong day."""
    write_state(realized_pnl_jpy=-5900.0, trade_count=2, daily_pnl_jpy=-5900.0,
                daily_date=utc_date(DAY0), position=None)
    real = Portfolio
    monkeypatch.setattr(bot.main, "Portfolio",
                        lambda *a, **k: real(*a, **{**k, "clock": rolling_clock([])}))
    app = boot(monkeypatch)
    assert app.portfolio.realized_pnl_jpy == pytest.approx(-5900.0)   # ledger kept
    assert app.portfolio.daily_pnl_jpy(PRICE) == 0.0                  # brake reset
    assert app.checker.check(wide_stop_entry(), account_of(app)).approved


# ---- a restored position is a position the bot can still get out of --------
def test_restored_long_is_closed_by_the_protective_stop(workdir, monkeypatch, clock):
    write_state(realized_pnl_jpy=-120.0, trade_count=1, daily_pnl_jpy=-120.0,
                daily_date=utc_date(DAY0),
                position={"side": "LONG", "size": 0.013, "entry_price": PRICE,
                          "opened_ts": DAY0 - 600})
    app = boot(monkeypatch)
    assert app.portfolio.position_size == pytest.approx(0.013)
    assert app.portfolio.avg_entry_price == pytest.approx(PRICE)
    assert app.trade_count == 1

    # a completed candle at 1% below entry -> the 0.5% protective stop fires
    drive(app, [(30, PRICE), (90, PRICE * 0.99)], LEADER)
    assert app.portfolio.position_size == 0.0
    assert app.portfolio.realized_pnl_jpy < -120.0          # the loss was booked
    assert app.trade_count == 2                             # restored entry + exit
    saved = read_state()
    assert saved["position"] is None and saved["trade_count"] == 2


def test_restored_position_is_mirrored_into_the_paper_executor(workdir, monkeypatch, clock):
    """Without this the executor is flat while the portfolio is long, and the
    exit OPENS a phantom short in the executor instead of closing anything."""
    write_state(realized_pnl_jpy=0.0, trade_count=1, daily_pnl_jpy=0.0,
                daily_date=utc_date(DAY0),
                position={"side": "SHORT", "size": 0.013, "entry_price": PRICE,
                          "opened_ts": DAY0})
    app = boot(monkeypatch)
    gateway = app.orders._gateway
    assert gateway.positions[SYMBOL] == pytest.approx(-0.013)
    assert gateway.entry_prices[SYMBOL] == pytest.approx(PRICE)

    drive(app, TICKS + [(390, PRICE), (430, PRICE), (490, PRICE)], LEADER)
    assert app.portfolio.position_size == 0.0
    assert gateway.positions[SYMBOL] == pytest.approx(0.0)   # closed, not flipped


def test_pre_trade_checks_see_the_restored_position(workdir, monkeypatch, clock):
    write_state(realized_pnl_jpy=0.0, trade_count=1, daily_pnl_jpy=0.0,
                daily_date=utc_date(DAY0),
                position={"side": "LONG", "size": 0.012, "entry_price": PRICE,
                          "opened_ts": DAY0})
    app = boot(monkeypatch)
    seen = []
    real_check = app.checker.check
    monkeypatch.setattr(app.checker, "check",
                        lambda order, account: (seen.append(account),
                                                real_check(order, account))[1])
    tick = Tick(timestamp=30.0, price=PRICE, best_bid=PRICE - 1000, best_ask=PRICE + 1000)
    app.feed.last_tick = tick
    app._try_order("SELL", tick, size=0.012)      # a close
    assert seen[0].position_size == pytest.approx(0.012)
    assert seen[0].position_notional_jpy == pytest.approx(0.012 * PRICE)


def spot_app() -> bot.main.TradingApp:
    """A paper app on BTC_JPY (spot, not shortable) = the same bot started on
    another product."""
    settings = Settings(mode=Mode.PAPER, product_code="BTC_JPY",
                        config=app_config("xborder_momentum"),
                        risk_limits=RiskLimits.from_dict({
                            "MAX_ORDER_SIZE_JPY": 130000, "MAX_POSITION_SIZE_JPY": 130000,
                            "MAX_DAILY_LOSS_JPY": 6000, "MAX_DRAWDOWN_PCT": 10.0,
                            "MAX_OPEN_ORDERS": 1, "MAX_CONSECUTIVE_LOSSES": 5,
                            "MAX_API_ERRORS_IN_ROW": 5}))
    session = FakeSession()
    session.set("GET", "/v1/ticker", FakeResponse(200, {
        "ltp": PRICE, "best_bid": PRICE - 1000, "best_ask": PRICE + 1000}))
    from bot.exchange.bitflyer_client import BitflyerClient
    return bot.main.TradingApp(settings, BitflyerClient(session=session,
                                                        sleep=lambda s: None),
                               NullNotifier())


def test_short_in_state_is_dropped_on_a_non_shortable_product(workdir, monkeypatch,
                                                              clock, caplog):
    """The PRODUCT SPEC changed under the file (same product, shortable flipped
    off); start flat rather than restore a position the executor could never
    have opened."""
    write_state(realized_pnl_jpy=0.0, trade_count=2, daily_pnl_jpy=0.0,
                daily_date=utc_date(DAY0), product_code="BTC_JPY",
                position={"side": "SHORT", "size": 0.01, "entry_price": PRICE,
                          "opened_ts": DAY0})
    with caplog.at_level(logging.WARNING):
        app = spot_app()
    assert app.portfolio.position_size == 0.0
    assert app.trade_count == 2                    # the ledger is still inherited
    assert "non-shortable" in caplog.text


# ---- the book belongs to ONE product ---------------------------------------
def test_a_book_from_another_product_is_not_transplanted(workdir, monkeypatch,
                                                         clock, caplog):
    """N2: sizes, entry prices and a margin balance mean nothing on another
    product. An FX_BTC_JPY book must not become a BTC_JPY spot book — the
    restored long would have its notional subtracted from a cash balance that
    never paid it (a negative paper balance), and the ledger would attribute
    another experiment's P&L to this one."""
    write_state(realized_pnl_jpy=-30000.0, trade_count=9, daily_pnl_jpy=-500.0,
                daily_date=utc_date(DAY0), product_code=SYMBOL,
                position={"side": "LONG", "size": 0.013, "entry_price": PRICE,
                          "opened_ts": DAY0})
    with caplog.at_level(logging.WARNING):
        app = spot_app()
    assert app.portfolio.realized_pnl_jpy == 0.0        # nothing transplanted
    assert app.portfolio.position_size == 0.0
    assert app.trade_count == 0
    assert app.portfolio.daily_pnl_jpy(PRICE) == 0.0
    assert app.orders._gateway.balance_jpy == pytest.approx(200000.0)
    assert caplog.text.count("belongs to another product") == 1
    assert not app.kill_switch.is_tripped
    # the other product's book is kept, not overwritten: it is the only record
    # of that paper experiment
    kept = json.loads((workdir / "data" / f"paper_state.{SYMBOL}.bak")
                      .read_text(encoding="utf-8"))
    assert kept["realized_pnl_jpy"] == pytest.approx(-30000.0)
    app._save_paper_state()
    assert read_state()["product_code"] == "BTC_JPY"


def test_the_same_product_is_restored_normally(workdir, monkeypatch, clock):
    """Directionality for the test above: it is the MISMATCH that drops the
    book, not the product-code field itself."""
    write_state(realized_pnl_jpy=-30000.0, trade_count=9, daily_pnl_jpy=0.0,
                daily_date="2000-01-01", product_code=SYMBOL)
    app = boot(monkeypatch)
    assert app.portfolio.realized_pnl_jpy == pytest.approx(-30000.0)
    assert app.trade_count == 9


def test_a_book_written_before_the_product_field_is_adopted(workdir, monkeypatch,
                                                            clock, caplog):
    """A file with no product recorded predates the field; it is the running
    product's book by construction (there was only ever one)."""
    Path("data").mkdir(exist_ok=True)
    STATE.write_text(json.dumps({"realized_pnl_jpy": -900.0, "trade_count": 3,
                                 "daily_pnl_jpy": 0.0, "daily_date": "2000-01-01",
                                 "position": None}), encoding="utf-8")
    with caplog.at_level(logging.WARNING):
        app = boot(monkeypatch)
    assert app.portfolio.realized_pnl_jpy == pytest.approx(-900.0)
    assert app.trade_count == 3
    assert caplog.text == ""
    app._save_paper_state()
    assert read_state()["product_code"] == SYMBOL      # and it is stamped now


# ---- continuity of the console numbers -------------------------------------
def test_restart_carries_equity_trades_and_daily_through_real_fills(
        workdir, monkeypatch, clock):
    app = boot(monkeypatch)
    drive(app, TICKS, LEADER)                       # opens a short
    assert app.portfolio.position_size == pytest.approx(-0.013)
    entry_price = app.portfolio.avg_entry_price

    restarted = boot(monkeypatch)                   # simulated process restart
    assert restarted.portfolio.position_size == pytest.approx(-0.013)
    assert restarted.portfolio.avg_entry_price == pytest.approx(entry_price)
    assert restarted.trade_count == 1

    drive(restarted, TICKS + [(390, PRICE), (430, PRICE), (490, PRICE)], LEADER)
    assert restarted.portfolio.position_size == 0.0
    fills = len(restarted.portfolio.trades)         # what THIS process filled
    assert fills >= 1
    assert restarted.trade_count == 1 + fills       # plus the entry it inherited
    s = restarted.status.status
    assert s.trade_count == restarted.trade_count
    # 残高 = initial + cumulative realized (flat, so no unrealized term)
    assert s.balance_jpy == pytest.approx(200000.0 + restarted.portfolio.realized_pnl_jpy)
    assert s.total_pnl_jpy == pytest.approx(restarted.portfolio.realized_pnl_jpy)

    third = boot(monkeypatch)                       # and it keeps carrying
    assert third.trade_count == restarted.trade_count
    assert third.portfolio.realized_pnl_jpy == pytest.approx(
        restarted.portfolio.realized_pnl_jpy)
    assert third.portfolio.position_size == 0.0


def test_restored_loss_does_not_read_as_an_instant_max_drawdown(workdir, monkeypatch, clock):
    """The portfolio's peak is anchored at BOOT equity: the hard drawdown check
    measures what this process lived through, so a book already 15% down does
    not trip MAX_DRAWDOWN_PCT the moment it starts."""
    write_state(realized_pnl_jpy=-30000.0, trade_count=4, daily_pnl_jpy=0.0,
                daily_date="2000-01-01", position=None)
    app = boot(monkeypatch)
    assert app.portfolio.equity_jpy(PRICE) == pytest.approx(170000.0)
    assert app.portfolio.drawdown_pct(PRICE) == 0.0
    assert app.checker.check(wide_stop_entry(), account_of(app)).approved
    assert not app.kill_switch.is_tripped


def test_consecutive_losses_are_not_inherited(workdir, monkeypatch, clock):
    """N1 again: the portfolio's streak feeds the kill switch and stays a fact
    about this process. Nothing in paper_state.json can seed it."""
    app = boot(monkeypatch)
    app.portfolio.consecutive_losses = 4
    app.portfolio.realized_pnl_jpy = -900.0
    app._save_paper_state()
    assert "consecutive_losses" not in read_state()
    assert boot(monkeypatch).portfolio.consecutive_losses == 0


# ---- the other persisted state is untouched --------------------------------
def test_overlay_state_is_neither_read_nor_written_here(workdir, monkeypatch, clock):
    app = boot(monkeypatch)
    app.portfolio.realized_pnl_jpy = -700.0
    app._save_paper_state()
    assert "equity_peak" not in read_state()
    assert not (workdir / "data" / "overlay_state.json").exists()


def test_overlay_peak_is_rebuilt_against_the_restored_equity(workdir, monkeypatch, clock):
    """The overlay reconstructs peak = boot_equity / dd_frac, so boot equity has
    to be the equity the book actually restarts at (initial + realized)."""
    write_state(realized_pnl_jpy=-20000.0, trade_count=3, daily_pnl_jpy=0.0,
                daily_date="2000-01-01", position=None)
    (workdir / "data" / "overlay_state.json").write_text(
        json.dumps({"consecutive_losses": 0, "dd_frac": 0.9}), encoding="utf-8")
    app = boot(monkeypatch, strategy_name="composite")
    assert app.overlay_state.equity_jpy == pytest.approx(180000.0)
    assert app.overlay_state.equity_peak_jpy == pytest.approx(200000.0)
    assert app._entry_size_factor(PRICE) == 0.5      # the 10% drawdown still bites


def test_tripped_kill_switch_still_refuses_trading_with_a_restored_book(
        workdir, monkeypatch, clock):
    write_state(realized_pnl_jpy=5000.0, trade_count=6, daily_pnl_jpy=5000.0,
                daily_date=utc_date(DAY0), position=None)
    KillSwitch().trip(KillReason.MANUAL, "operator")
    app = boot(monkeypatch)
    assert app.kill_switch.is_tripped
    assert app.trade_count == 6                       # the book is still restored
    tick = Tick(timestamp=30.0, price=PRICE, best_bid=PRICE - 1000, best_ask=PRICE + 1000)
    assert app._try_order("SELL", tick) is None
    app.step()
    assert app.portfolio.position_size == 0.0

    KillSwitch().reset(operator_confirm=True)         # human, after investigating
    after = boot(monkeypatch)
    assert not after.kill_switch.is_tripped
    assert after.trade_count == 6
    drive(after, TICKS, LEADER)
    assert after.portfolio.position_size == pytest.approx(-0.013)


# ---- LIVE mode is untouched ------------------------------------------------
def live_app(session) -> bot.main.TradingApp:
    settings = Settings(mode=Mode.LIVE, product_code=SYMBOL,
                        api_key=Secret("key"), api_secret=Secret("secret"),
                        config=app_config("xborder_momentum"),
                        risk_limits=RiskLimits.from_dict({
                            "MAX_ORDER_SIZE_JPY": 130000, "MAX_POSITION_SIZE_JPY": 130000,
                            "MAX_DAILY_LOSS_JPY": 6000, "MAX_DRAWDOWN_PCT": 10.0,
                            "MAX_OPEN_ORDERS": 1, "MAX_CONSECUTIVE_LOSSES": 5,
                            "MAX_API_ERRORS_IN_ROW": 5}))
    from bot.exchange.bitflyer_client import BitflyerClient
    client = BitflyerClient(settings.api_key, settings.api_secret,
                            session=session, sleep=lambda s: None)
    return bot.main.TradingApp(settings, client, NullNotifier())


def test_live_mode_neither_reads_nor_writes_paper_state(workdir, monkeypatch, clock):
    write_state(realized_pnl_jpy=999999.0, trade_count=42, daily_pnl_jpy=-5000.0,
                daily_date=utc_date(DAY0),
                position={"side": "LONG", "size": 5.0, "entry_price": PRICE,
                          "opened_ts": DAY0})
    before = STATE.read_text(encoding="utf-8")
    session = FakeSession()
    session.set("GET", "/v1/ticker", FakeResponse(200, {
        "ltp": PRICE, "best_bid": PRICE - 1000, "best_ask": PRICE + 1000}))
    session.set("GET", "/v1/me/getpermissions", FakeResponse(200, [
        "/v1/me/getbalance", "/v1/me/sendchildorder"]))
    session.set("GET", "/v1/me/getbalance", FakeResponse(200, [
        {"currency_code": "JPY", "available": 50000}]))
    # LIVE boots by ASKING the venue what it holds (bot/main.py
    # `_adopt_venue_position`); here it holds nothing.
    session.set("GET", "/v1/me/getpositions", FakeResponse(200, []))

    app = live_app(session)
    assert app.paper_state is None
    assert not app.kill_switch.is_tripped
    assert app.portfolio.initial_equity_jpy == pytest.approx(50000.0)
    assert app.portfolio.realized_pnl_jpy == 0.0
    assert app.portfolio.position_size == 0.0
    assert app.trade_count == 0
    app._save_paper_state()                       # no-op in LIVE
    app._roll_paper_day()
    app._update_status(PRICE)
    assert STATE.read_text(encoding="utf-8") == before


# ---- the file itself -------------------------------------------------------
def test_state_roundtrip_is_utf8_json(tmp_path):
    path = tmp_path / "nested" / "paper_state.json"
    state = PaperState(realized_pnl_jpy=-1234.5, trade_count=7,
                       daily_pnl_jpy=-200.0, daily_date="2026-08-20",
                       position=PaperPosition("SHORT", 0.013, 9_999_000.0, DAY0))
    state.save(path)
    assert json.loads(path.read_text(encoding="utf-8"))["position"]["side"] == "SHORT"
    reloaded = PaperState.load(path)
    assert reloaded == state
    assert reloaded.position.signed_size == pytest.approx(-0.013)
    assert reloaded.daily_pnl_on("2026-08-20") == pytest.approx(-200.0)
    assert reloaded.daily_pnl_on("2026-08-21") == 0.0


def test_missing_state_is_a_silent_fresh_book(tmp_path, caplog):
    with caplog.at_level(logging.WARNING):
        state = PaperState.load(tmp_path / "paper_state.json")
    assert state == PaperState()
    assert caplog.text == ""                      # a first start is not a fault


@pytest.mark.parametrize("content", [
    "", "{not json", "[]", '{"realized_pnl_jpy": 1.0}',
    '{"realized_pnl_jpy": "x", "trade_count": 1, "daily_pnl_jpy": 0, "daily_date": "d"}',
    '{"realized_pnl_jpy": NaN, "trade_count": 1, "daily_pnl_jpy": 0, "daily_date": "d"}',
    '{"realized_pnl_jpy": 0, "trade_count": -1, "daily_pnl_jpy": 0, "daily_date": "d"}',
])
def test_corrupt_state_degrades_to_a_fresh_book_with_one_warning(tmp_path, caplog, content):
    path = tmp_path / "paper_state.json"
    path.write_text(content, encoding="utf-8")
    with caplog.at_level(logging.WARNING):
        state = PaperState.load(path)
    assert state == PaperState()
    assert caplog.text.count("paper state unreadable") == 1


# The ledger and the position are parsed independently: dropping the whole book
# because the position is unreadable would ALSO hand back the spent daily
# budget — the safety brake this file exists to carry.
LEDGER = ('"realized_pnl_jpy": -12000, "trade_count": 4, '
          '"daily_pnl_jpy": -5900, "daily_date": "2026-08-20"')


@pytest.mark.parametrize("position", [
    '{"side": "FLAT", "size": 1, "entry_price": 1}',
    '{"side": "LONG", "size": 0, "entry_price": 1}',
    '{"side": "LONG", "size": 0.01, "entry_price": 1, "opened_ts": "yesterday"}',
    '{"size": 0.01, "entry_price": 1}',
    'true',
])
def test_a_corrupt_position_drops_only_the_position(tmp_path, caplog, position):
    path = tmp_path / "paper_state.json"
    path.write_text('{%s, "position": %s}' % (LEDGER, position), encoding="utf-8")
    with caplog.at_level(logging.WARNING):
        state = PaperState.load(path)
    assert state.position is None                      # started flat
    assert state.realized_pnl_jpy == pytest.approx(-12000.0)
    assert state.trade_count == 4
    assert state.daily_pnl_on("2026-08-20") == pytest.approx(-5900.0)
    assert caplog.text.count("position unreadable") == 1
    assert "paper state unreadable" not in caplog.text  # the book is readable


def test_app_boots_on_a_corrupt_state_file(workdir, monkeypatch, clock):
    write_state(realized_pnl_jpy="nonsense")
    app = boot(monkeypatch)                       # must not raise
    assert app.portfolio.realized_pnl_jpy == 0.0
    assert app.portfolio.position_size == 0.0
    assert app.trade_count == 0
    drive(app, TICKS, LEADER)                     # and trades normally
    assert app.portfolio.position_size == pytest.approx(-0.013)


def test_save_survives_a_locked_destination(tmp_path, monkeypatch):
    """os.replace fails with PermissionError on Windows while the dashboard
    holds the file open: retry, write directly, leak no temp file. The write
    itself is bot/atomic_file.py, shared with the other two state files."""
    import bot.atomic_file as atomic

    path = tmp_path / "paper_state.json"
    monkeypatch.setattr(atomic.time, "sleep", lambda s: None)
    calls = []

    def always_locked(src, dst):
        calls.append((src, dst))
        raise PermissionError("a reader holds the file open")

    monkeypatch.setattr(atomic.os, "replace", always_locked)
    PaperState(realized_pnl_jpy=-5.0, trade_count=3).save(path)

    assert len(calls) == 5
    assert json.loads(path.read_text(encoding="utf-8"))["trade_count"] == 3
    assert not path.with_suffix(".tmp").exists()


def test_save_never_raises(tmp_path):
    """A bookkeeping checkpoint must not be able to take trading down."""
    blocked = tmp_path / "blocked"
    blocked.write_text("a file where a directory would have to be", encoding="utf-8")
    PaperState(trade_count=1).save(blocked / "paper_state.json")


def test_shutdown_checkpoints_the_book(workdir, monkeypatch, clock):
    """run_forever saves on every way out, Ctrl-C included."""
    app = boot(monkeypatch)
    app.portfolio.realized_pnl_jpy = -42.0
    monkeypatch.setattr(app, "step", lambda: (_ for _ in ()).throw(KeyboardInterrupt()))
    with pytest.raises(KeyboardInterrupt):
        app.run_forever()
    assert read_state()["realized_pnl_jpy"] == pytest.approx(-42.0)


def test_kill_checkpoints_the_book(workdir, monkeypatch, clock):
    app = boot(monkeypatch)
    app.portfolio.realized_pnl_jpy = -77.0
    app.kill_switch.trip(KillReason.MANUAL, "operator")
    app._on_kill("operator")
    assert read_state()["realized_pnl_jpy"] == pytest.approx(-77.0)
