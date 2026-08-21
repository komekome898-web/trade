"""Risk limits and kill switch (items 13-17)."""
from __future__ import annotations

import pytest

from bot.risk.kill_switch import KillReason, KillSwitch
from bot.risk.pre_trade_checks import AccountState, OrderRequest, PreTradeChecker
from bot.settings import RiskLimits

LIMITS = RiskLimits(
    max_order_size_jpy=3000, max_position_size_jpy=6000, max_daily_loss_jpy=300,
    max_drawdown_pct=10.0, max_open_orders=1, max_consecutive_losses=4,
    max_api_errors_in_row=5,
)


@pytest.fixture
def kill_switch(tmp_path):
    return KillSwitch(state_dir=tmp_path, manual_file=tmp_path / "KILL")


@pytest.fixture
def checker(kill_switch):
    return PreTradeChecker(LIMITS, kill_switch)


def healthy_account(**overrides):
    base = dict(balance_jpy=6000, position_notional_jpy=0, open_orders=0,
                daily_pnl_jpy=0, drawdown_pct=0, consecutive_losses=0)
    base.update(overrides)
    return AccountState(**base)


def order(size=10.0, price=100.0, side="BUY", stop=98.0):
    return OrderRequest("XRP_JPY", side, size, price, stop_price=stop)


def test_healthy_order_approved(checker):
    assert checker.check(order(), healthy_account()).approved


def test_max_order_size_rejected(checker):
    d = checker.check(order(size=40.0, price=100.0), healthy_account())
    assert not d.approved and any("MAX_ORDER_SIZE" in r for r in d.reasons)


def test_max_position_size_rejected(checker):
    d = checker.check(order(size=20.0), healthy_account(position_notional_jpy=5000))
    assert not d.approved and any("MAX_POSITION_SIZE" in r for r in d.reasons)


def test_max_open_orders_rejected(checker):
    d = checker.check(order(), healthy_account(open_orders=1))
    assert not d.approved and any("MAX_OPEN_ORDERS" in r for r in d.reasons)


def test_max_open_orders_never_refuses_a_closing_order(checker):
    """(B1) The cap binds on exposure, like MAX_ORDER_SIZE and
    MAX_POSITION_SIZE beside it.

    A book at the cap is exactly the situation the closing-order priority path
    exists for — one resting order the venue never filled, and a position that
    now has to be exited. Refusing the exit HERE happens before the order
    manager runs, so `_make_room_for_close` never gets to cancel the blocker:
    the cap silently becomes 'this position cannot be closed'.
    """
    at_cap = healthy_account(open_orders=1, position_size=10.0,
                             position_notional_jpy=1000.0)
    closing = checker.check(order(side="SELL", stop=100.0), at_cap)
    assert closing.approved, closing.reasons

    opening = checker.check(order(side="BUY"), at_cap)
    assert not opening.approved
    assert any("MAX_OPEN_ORDERS" in r for r in opening.reasons)


def test_only_the_reducing_part_of_an_order_is_exempt_from_the_caps(checker):
    """(M1) The exemption exists so a stop can always be placed, and it is
    bounded by the position it closes.

    A SELL of 1.0 against a 0.001 long closes 0.001 and OPENS 0.999 short.
    Exempting the whole order because "it is a sell and we are long" let an
    order a thousand times MAX_ORDER_SIZE through as if it were protective —
    the caps applied to entries and to nothing else, reachable from any signal
    that oversizes a close.
    """
    long_at_the_cap = healthy_account(position_size=0.001,
                                      position_notional_jpy=10.0, open_orders=1)
    oversized = OrderRequest("XRP_JPY", "SELL", 1.0, 10_000.0, stop_price=10_000.0)

    d = checker.check(oversized, long_at_the_cap)

    assert not d.approved
    assert any("MAX_ORDER_SIZE" in r for r in d.reasons), d.reasons
    assert any("MAX_POSITION_SIZE" in r for r in d.reasons), d.reasons

    # ...and the actual close, of exactly what is open, is still exempt from
    # every one of them — including the open-order cap it sits at.
    exact = OrderRequest("XRP_JPY", "SELL", 0.001, 10_000.0, stop_price=10_000.0)
    assert checker.check(exact, long_at_the_cap).approved


def test_a_partial_close_is_exempt_and_an_oversized_one_is_judged_on_the_excess(
        checker):
    """The rule stated as a boundary: everything up to |position| is a close,
    and only what is left over is new exposure."""
    short = healthy_account(position_size=-20.0, position_notional_jpy=2000.0)

    # closing half of a 20-unit short: entirely reducing
    assert checker.check(order(size=10.0, side="BUY", stop=100.0), short).approved
    # exactly flat: still entirely reducing
    assert checker.check(order(size=20.0, side="BUY", stop=100.0), short).approved
    # 20 closes the short and 25 more open a long, so the caps see the 2500 JPY
    # EXCESS — not the 4500 the whole order is worth, which would have been
    # refused by MAX_ORDER_SIZE for exposure it does not add.
    assert checker.check(order(size=45.0, side="BUY", stop=100.0), short).approved
    # ...and once the excess itself is over the cap, it is refused.
    too_far = checker.check(order(size=90.0, side="BUY", stop=100.0), short)
    assert not too_far.approved
    assert any("MAX_ORDER_SIZE" in r for r in too_far.reasons), too_far.reasons


def test_insufficient_balance_rejected(checker):
    d = checker.check(order(size=25.0), healthy_account(balance_jpy=1000))
    assert not d.approved and any("insufficient balance" in r for r in d.reasons)


def test_estimated_loss_exceeding_daily_budget_rejected(checker):
    d = checker.check(order(size=10.0, price=100.0, stop=50.0),  # 500 JPY risk > 300
                      healthy_account())
    assert not d.approved and any("daily risk budget" in r for r in d.reasons)


def test_daily_loss_limit_trips_kill_switch(checker, kill_switch):
    d = checker.check(order(), healthy_account(daily_pnl_jpy=-300))
    assert not d.approved
    assert kill_switch.is_tripped
    assert kill_switch.state["reason"] == KillReason.DAILY_LOSS_LIMIT.value


def test_max_drawdown_trips_kill_switch(checker, kill_switch):
    d = checker.check(order(), healthy_account(drawdown_pct=12.0))
    assert not d.approved and kill_switch.is_tripped
    assert kill_switch.state["reason"] == KillReason.MAX_DRAWDOWN.value


def test_consecutive_losses_trip_kill_switch(checker, kill_switch):
    d = checker.check(order(), healthy_account(consecutive_losses=4))
    assert not d.approved and kill_switch.is_tripped


def test_tripped_kill_switch_blocks_all_orders(checker, kill_switch):
    kill_switch.trip(KillReason.MANUAL, "test")
    d = checker.check(order(), healthy_account())
    assert not d.approved and any("kill switch" in r for r in d.reasons)


def test_kill_switch_persists_across_restart(tmp_path):
    ks = KillSwitch(state_dir=tmp_path, manual_file=tmp_path / "KILL")
    ks.trip(KillReason.API_ERRORS, "5 in a row")
    ks2 = KillSwitch(state_dir=tmp_path, manual_file=tmp_path / "KILL")  # "restart"
    assert ks2.is_tripped
    assert ks2.state["reason"] == KillReason.API_ERRORS.value


def test_kill_switch_manual_file(tmp_path):
    manual = tmp_path / "KILL"
    ks = KillSwitch(state_dir=tmp_path, manual_file=manual)
    assert not ks.is_tripped
    manual.write_text("")
    assert ks.is_tripped
    assert ks.state["reason"] == KillReason.MANUAL.value


def test_kill_switch_reset_requires_confirmation(tmp_path):
    ks = KillSwitch(state_dir=tmp_path, manual_file=tmp_path / "KILL")
    ks.trip(KillReason.MANUAL, "test")
    with pytest.raises(PermissionError):
        ks.reset()
    ks.reset(operator_confirm=True)
    assert not ks.is_tripped
