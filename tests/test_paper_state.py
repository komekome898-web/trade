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
    Path("data").mkdir(exist_ok=True)
    STATE.write_text(json.dumps(fields), encoding="utf-8")


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
    app.portfolio.seed_daily_realized(-5000.0)
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
    app.portfolio.seed_daily_realized(-5000.0)
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
    app.portfolio.seed_daily_realized(-6000.0)
    app._save_paper_state()

    restarted = boot(monkeypatch)
    restarted.checker.check(wide_stop_entry(), account_of(restarted))
    assert restarted.kill_switch.is_tripped
    assert restarted.kill_switch.state["reason"] == KillReason.DAILY_LOSS_LIMIT.value


def test_day_rollover_while_running_resets_and_persists(workdir, monkeypatch, clock):
    app = boot(monkeypatch)
    app.portfolio.realized_pnl_jpy = -1000.0
    app.portfolio.seed_daily_realized(-1000.0)
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


def test_short_in_state_is_dropped_on_a_non_shortable_product(workdir, monkeypatch,
                                                              clock, caplog):
    """The product config changed under the file; start flat rather than
    restore a position the executor could never have opened."""
    write_state(realized_pnl_jpy=0.0, trade_count=2, daily_pnl_jpy=0.0,
                daily_date=utc_date(DAY0),
                position={"side": "SHORT", "size": 0.01, "entry_price": PRICE,
                          "opened_ts": DAY0})
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
    with caplog.at_level(logging.WARNING):
        app = bot.main.TradingApp(settings, BitflyerClient(session=session,
                                                           sleep=lambda s: None),
                                  NullNotifier())
    assert app.portfolio.position_size == 0.0
    assert app.trade_count == 2                    # the ledger is still inherited
    assert "non-shortable" in caplog.text


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

    app = live_app(session)
    assert app.paper_state is None
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
    '{"realized_pnl_jpy": 0, "trade_count": 1, "daily_pnl_jpy": 0, "daily_date": "d",'
    ' "position": {"side": "FLAT", "size": 1, "entry_price": 1}}',
    '{"realized_pnl_jpy": 0, "trade_count": 1, "daily_pnl_jpy": 0, "daily_date": "d",'
    ' "position": {"side": "LONG", "size": 0, "entry_price": 1}}',
    '{"realized_pnl_jpy": 0, "trade_count": 1, "daily_pnl_jpy": 0, "daily_date": "d",'
    ' "position": true}',
])
def test_corrupt_state_degrades_to_a_fresh_book_with_one_warning(tmp_path, caplog, content):
    path = tmp_path / "paper_state.json"
    path.write_text(content, encoding="utf-8")
    with caplog.at_level(logging.WARNING):
        state = PaperState.load(path)
    assert state == PaperState()
    assert caplog.text.count("paper state unreadable") == 1


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
    holds the file open: retry, write directly, leak no temp file."""
    import bot.portfolio.persistence as persistence

    path = tmp_path / "paper_state.json"
    monkeypatch.setattr(persistence.time, "sleep", lambda s: None)
    calls = []

    def always_locked(src, dst):
        calls.append((src, dst))
        raise PermissionError("a reader holds the file open")

    monkeypatch.setattr(persistence.os, "replace", always_locked)
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
