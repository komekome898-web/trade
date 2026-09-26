"""Adversarial grid: trading hours and the price band (C2-3 JPX hours and
price limit, FX weekend).

1. `Sessions` (JST 09:00-11:30 / 12:30-15:30, Mon-Fri): every 7 minutes over
   9 days plus every window edge -1 / 0 / +1 ns on each of those days;
   is_open and next_open against an oracle built with `datetime` in a fixed
   +09:00 zone (weekday and wall clock from `datetime`, not from the
   implementation's day arithmetic).
2. `ClosedWindows` + `VenueRules.next_open`: FX weekend windows over the
   same span.
3. The venue at the edges: an order arriving at an edge -1 / 0 / +1 ns x
   outside_session in {reject, queue_to_next_open} x order type {market,
   limit} -> rejected, filled at the session's first book, or acted on at once.
4. The price band: limit prices around low / high (-1 tick, edge, +1 tick) x
   side -> accepted iff low <= price <= high.

Not enumerated: holidays (a holiday is a ClosedWindows entry, the same code
path as 2), sessions crossing midnight (a window is refused unless start <
end), daylight-saving zones (a fixed offset is declared).
"""
from __future__ import annotations

import itertools
from datetime import datetime, timedelta, timezone

import pytest

from bot.bt.orders import ClosedWindows, PriceLimit, Sessions, VenueRules
from i2_gridkit import MS, SEC, book, filled, first_t, inp, place, run, trade

JST = timezone(timedelta(hours=9))
WINDOWS = (("09:00", "11:30"), ("12:30", "15:30"))
SESS = Sessions(WINDOWS, 540, (0, 1, 2, 3, 4), "grid: TSE hours")
START = int(datetime(2026, 1, 3, 0, 0, tzinfo=JST).timestamp()) * SEC  # Saturday, JST
DAY = 86_400 * SEC


def _edges() -> list[int]:
    out = []
    for d in range(9):
        base = datetime(2026, 1, 3, tzinfo=JST) + timedelta(days=d)
        for a, b in WINDOWS:
            for hm in (a, b):
                h, m = map(int, hm.split(":"))
                t = int(base.replace(hour=h, minute=m).timestamp()) * SEC
                out += [t - 1, t, t + 1]
    return out


TIMES = sorted(set(list(range(START, START + 9 * DAY, 7 * 60 * SEC)) + _edges()))


def oracle_open(t: int) -> bool:
    dt = datetime.fromtimestamp(t // SEC, JST)
    if dt.weekday() > 4:
        return False
    sub = t % SEC
    for a, b in WINDOWS:
        ha, ma = map(int, a.split(":"))
        hb, mb = map(int, b.split(":"))
        lo = int(dt.replace(hour=ha, minute=ma, second=0).timestamp()) * SEC
        hi = int(dt.replace(hour=hb, minute=mb, second=0).timestamp()) * SEC
        if lo <= (t - sub) + sub < hi:
            return True
    return False


def oracle_next_open(t: int) -> int:
    if oracle_open(t):
        return t
    day0 = datetime.fromtimestamp(t // SEC, JST).replace(hour=0, minute=0, second=0)
    cands = []
    for d in range(0, 12):
        day = day0 + timedelta(days=d)
        if day.weekday() > 4:
            continue
        for a, _b in WINDOWS:
            h, m = map(int, a.split(":"))
            s = int(day.replace(hour=h, minute=m).timestamp()) * SEC
            if s > t:
                cands.append(s)
    return min(cands)


def test_grid_sizes():
    assert len(TIMES) > 1800  # every 7 min over 9 days + 108 edge instants


@pytest.mark.parametrize("chunk", range(10))
def test_sessions_open_and_next_open(chunk):
    for t in TIMES[chunk::10]:
        assert SESS.is_open(t) == oracle_open(t), t
        assert SESS.next_open(t) == oracle_next_open(t), t


FRI_CLOSE = int(datetime(2026, 1, 9, 22, 0, tzinfo=timezone.utc).timestamp()) * SEC
SUN_OPEN = int(datetime(2026, 1, 11, 22, 0, tzinfo=timezone.utc).timestamp()) * SEC


def test_closed_windows_next_open():
    rules = VenueRules(closed=ClosedWindows(((FRI_CLOSE, SUN_OPEN),), "grid: FX weekend"),
                       outside_session="queue_to_next_open")
    for t in range(FRI_CLOSE - 2 * DAY, SUN_OPEN + 2 * DAY, 11 * 60 * SEC):
        inside = FRI_CLOSE <= t < SUN_OPEN
        assert rules.is_open(t) == (not inside)
        assert rules.next_open(t) == (SUN_OPEN if inside else t)
    for t in (FRI_CLOSE - 1, FRI_CLOSE, FRI_CLOSE + 1, SUN_OPEN - 1, SUN_OPEN, SUN_OPEN + 1):
        inside = FRI_CLOSE <= t < SUN_OPEN
        assert rules.is_open(t) == (not inside)


def test_hours_without_a_policy_are_refused():
    from bot.bt.orders import RuleNotDeclaredError
    with pytest.raises(RuleNotDeclaredError):
        VenueRules(sessions=SESS)


JPX = {"symbol": "JPX_A", "venue": "jpx_equity", "tick": 1.0, "min_qty": 100.0, "qty_step": 100.0,
       "quote_ccy": "JPY", "margin": False}
MORNING_CLOSE = int(datetime(2026, 1, 6, 11, 30, tzinfo=JST).timestamp()) * SEC
AFTERNOON_OPEN = int(datetime(2026, 1, 6, 12, 30, tzinfo=JST).timestamp()) * SEC
EDGE_GRID = list(itertools.product(
    [MORNING_CLOSE - 1, MORNING_CLOSE, MORNING_CLOSE + 1, AFTERNOON_OPEN - 1, AFTERNOON_OPEN, AFTERNOON_OPEN + 1],
    ["reject", "queue_to_next_open"], ["market", "limit"]))


@pytest.mark.parametrize("combo", EDGE_GRID, ids=[f"{c[0] % 10**12}-{c[1]}-{c[2]}" for c in EDGE_GRID])
def test_venue_at_session_edges(combo):
    t_order, policy, typ = combo
    rules = {"off_tick": "reject", "below_min_qty": "reject", "market_remainder": "cancel", "mark": "last_trade",
             "sessions_jst": [list(w) for w in WINDOWS], "outside_session": policy, "source": "grid: TSE hours"}
    t_first = MORNING_CLOSE - 60 * SEC
    market = [book(t_first, [(1499, 5000)], [(1501, 5000)]), trade(t_first, 1500, 100, "buy"),
              book(AFTERNOON_OPEN, [(1509, 5000)], [(1510, 5000)]), trade(AFTERNOON_OPEN, 1510, 100, "buy"),
              trade(AFTERNOON_OPEN + 60 * SEC, 1495, 1000, "sell")]
    px = 1500.0 if typ == "limit" else None
    obs, refused = run(inp(market, [place(t_order, "o1", "buy", typ, 100.0, px=px)], product=JPX, rules=rules,
                           account={"currency": "JPY", "cash": 1e8, "leverage": 1.0},
                           end_t=AFTERNOON_OPEN + 3600 * SEC))
    assert refused is None, refused
    is_open = oracle_open(t_order)
    if not is_open and policy == "reject":
        assert obs["orders"]["o1"]["status"] == "rejected"
        return
    assert obs["orders"]["o1"]["status"] == "filled"
    if is_open:
        # acted on at arrival: a market order takes the morning book's ask; a
        # limit 1500 rests and the 1495 print fills it
        exp_t = t_order if typ == "market" else AFTERNOON_OPEN + 60 * SEC
    else:
        # held until the afternoon's first book: a market order takes its ask
        # 1510; a limit 1500 is not marketable then and the 1495 print fills it
        exp_t = AFTERNOON_OPEN if typ == "market" else AFTERNOON_OPEN + 60 * SEC
    assert first_t(obs, "o1") == exp_t
    assert filled(obs, "o1") == 100.0


BAND = PriceLimit(1000.0, 300.0, "grid: band")
BAND_GRID = list(itertools.product(("buy", "sell"), (699.0, 700.0, 1000.0, 1300.0, 1301.0)))


@pytest.mark.parametrize("combo", BAND_GRID, ids=[f"{s}-{p}" for s, p in BAND_GRID])
def test_price_band(combo):
    side, px = combo
    rules = {"off_tick": "reject", "below_min_qty": "reject", "market_remainder": "cancel", "mark": "last_trade",
             "price_limit": {"base": 1000.0, "width": 300.0, "source": "grid: band"}}
    t = int(datetime(2026, 1, 6, 10, 0, tzinfo=JST).timestamp()) * SEC
    market = [book(t, [(650, 1)], [(1350, 1)])]
    margin_jpx = dict(JPX, margin=True)  # a margin account, so a sell is read by the band, not by a cash rule
    obs, refused = run(inp(market, [place(t + MS, "o1", side, "limit", 100.0, px=px)], product=margin_jpx,
                           rules=rules, account={"currency": "JPY", "cash": 1e9, "leverage": 1.0},
                           end_t=t + 60 * SEC))
    assert refused is None, refused
    inside = BAND.low <= px <= BAND.high
    assert obs["orders"]["o1"]["status"] == ("open" if inside else "rejected")
