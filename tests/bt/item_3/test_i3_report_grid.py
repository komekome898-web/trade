"""Adversarial grids for the metrics (item 3, old item 9), each against an
oracle written from the definition in bot/bt/report/metrics.py's docstring.

Grids: 400 seeded trades (side x fee x price); list lengths 1..30 x 9
probabilities for the quantiles; 200 seeded overlapping intervals against a
minute bitmap for the union; every (order state x fill time vs end) for
the fill rate; every (fill time x horizon) placement against a mid path
(on a sample, between samples, before the first, after the last) x side;
seeded fills with a fill AT a funding instant for the costs; 300 seeded
equity paths (and non-positive peaks) for the drawdown; 200 seeded fill
sequences that end flat (with position flips) for the round trips, checked
against the cash flow; every missing field / bad value for the refusals.

Not in the grids: quantile methods other than type 7 (the only one the
module offers); markout on quotes with a bid/ask (the module takes a mid
path; which mid is the caller's input).
"""
from __future__ import annotations

import itertools
import math
import random

import pytest

from bot.bt import report as RP
from bot.bt.report import ReportError, metrics as M

H = 3_600_000_000_000
S = 1_000_000_000


def _trades(n, seed):
    r = random.Random(seed)
    out = []
    for i in range(n):
        e = r.choice((100.0, 9999.5, 1e7))
        x = e * (1 + r.uniform(-0.02, 0.02))
        a = r.randrange(0, 1000) * 60 * S
        out.append({"id": f"t{i}", "side": r.choice(("buy", "sell")), "qty": r.choice((0.01, 1.0, 3.5)),
                    "entry_px": e, "exit_px": x, "entry_t_ns": a, "exit_t_ns": a + r.randrange(0, 300) * 60 * S,
                    "fees": r.choice((0.0, 0.5, 12.0))})
    return out


def test_per_trade_bp_grid():
    tr = _trades(400, 1)
    got = M.per_trade_bp(tr)
    for t, g in zip(tr, got):
        s = 1 if t["side"] == "buy" else -1
        want = (s * (t["exit_px"] - t["entry_px"]) * t["qty"] - t["fees"]) / (t["entry_px"] * t["qty"]) * 1e4
        assert g == pytest.approx(want, rel=1e-9, abs=1e-9)
    d = M.trade_distribution(tr)
    assert d["neg_frac"] == sum(1 for x in got if x < 0) / len(got)
    assert d["bp_per_hour"] == pytest.approx(sum(got) / (sum(t["exit_t_ns"] - t["entry_t_ns"] for t in tr) / H))


def _q7(xs, p):
    s = sorted(xs)
    h = (len(s) - 1) * p
    lo = math.floor(h)
    return s[lo] + (h - lo) * (s[min(lo + 1, len(s) - 1)] - s[lo])


def test_quantile_grid():
    r = random.Random(2)
    n = 0
    for length in range(1, 31):
        xs = [r.choice((-5, -1, 0, 0, 2, 7.5, 30)) + r.random() for _ in range(length)]
        probs = [0, 0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99, 1]
        got = M.quantiles(xs, probs)
        for p in probs:
            assert got[str(p)] == pytest.approx(_q7(xs, p), abs=1e-12)
            n += 1
    assert n == 30 * 9
    assert M.neg_frac([0.0, -0.0, 1.0, -1e-12]) == 0.25


def test_union_hours_grid():
    r = random.Random(3)
    tr = [{"entry_t_ns": a * 60 * S, "exit_t_ns": (a + d) * 60 * S}
          for a, d in ((r.randrange(0, 2000), r.randrange(0, 180)) for _ in range(200))]
    minutes = set()
    for t in tr:
        minutes.update(range(t["entry_t_ns"] // (60 * S), t["exit_t_ns"] // (60 * S)))
    ex = M.exposure(tr)
    assert ex["union_hours"] == pytest.approx(len(minutes) / 60)
    assert ex["trade_hours"] == pytest.approx(sum(t["exit_t_ns"] - t["entry_t_ns"] for t in tr) / H)


def test_fill_rate_grid():
    end = 1000 * S
    states = ["none", "full_before", "full_after", "partial_before", "two_parts", "part_before_rest_after"]
    count = 0
    for combo in itertools.product(states, repeat=3):
        orders, fills = [], []
        for i, st in enumerate(combo):
            oid = f"o{i}"
            orders.append({"id": oid, "qty": 2.0})
            if st == "full_before":
                fills.append({"order_id": oid, "t_ns": 10 * S, "qty": 2.0})
            elif st == "full_after":
                fills.append({"order_id": oid, "t_ns": end + 1, "qty": 2.0})
            elif st == "partial_before":
                fills.append({"order_id": oid, "t_ns": end, "qty": 0.5})
            elif st == "two_parts":
                fills += [{"order_id": oid, "t_ns": 1, "qty": 1.0}, {"order_id": oid, "t_ns": 2, "qty": 1.0}]
            elif st == "part_before_rest_after":
                fills += [{"order_id": oid, "t_ns": 1, "qty": 1.0}, {"order_id": oid, "t_ns": end + 5, "qty": 1.0}]
        filled = [st in ("full_before", "partial_before", "two_parts", "part_before_rest_after") for st in combo]
        partial = [st in ("partial_before", "part_before_rest_after") for st in combo]
        r = M.fill_metrics(orders, fills, end)
        assert r["fill_rate"] == sum(filled) / 3 and r["missed"] == 3 - sum(filled) and r["partial"] == sum(partial)
        count += 1
    assert count == 216
    with pytest.raises(ReportError):
        M.fill_metrics([{"id": "o", "qty": 1.0}], [{"order_id": "o", "t_ns": 0, "qty": 1.5}], end)
    with pytest.raises(ReportError):
        M.fill_metrics([{"id": "o", "qty": 1.0}], [{"order_id": "x", "t_ns": 0, "qty": 1.0}], end)


def test_markout_placement_grid():
    path = [(100 * S, 10.0), (160 * S, 12.0), (400 * S, 9.0), (700 * S, 15.0)]

    def asof(t):
        if t < path[0][0] or t > path[-1][0]:
            return None
        return [v for tt, v in path if tt <= t][-1]

    n = 0
    for ft, h, side in itertools.product((50, 100, 130, 160, 399, 400, 650, 700, 701), (0, 30, 60, 300, 600), ("buy", "sell")):
        fill = {"t_ns": ft * S, "px": 11.0, "side": side, "qty": 1.0}
        got = M.markout([fill], path, [h], unit="price")[str(h)][0]
        m = asof((ft + h) * S)
        want = None if m is None else (1 if side == "buy" else -1) * (m - 11.0)
        assert got == want, (ft, h, side)
        gb = M.markout([fill], path, [h], unit="bp")[str(h)][0]
        assert gb == (None if want is None else pytest.approx(want / 11.0 * 1e4))
        n += 1
    assert n == 9 * 5 * 2
    with pytest.raises(ReportError):
        M.markout([], [(2, 1.0), (1, 1.0)], [60], unit="price")
    with pytest.raises(ReportError):
        M.markout([], path, [60], unit="ticks")


def test_cost_breakdown_grid():
    r = random.Random(4)
    for _ in range(50):
        fills = []
        for i in range(8):
            px = 1000 + r.randrange(-50, 50)
            fills.append({"t_ns": r.choice((0, 10, 20, 30)) * S, "side": r.choice(("buy", "sell")),
                          "qty": r.choice((0.5, 1.0, 2.0)), "px": float(px), "liquidity": r.choice(("maker", "taker")),
                          "mid": float(px + r.choice((-2, -1, 0, 1, 2)))})
        funding = [{"t_ns": t * S, "rate": r.choice((-0.001, 0.0001, 0.0005)), "mark": 1000.0 + t} for t in (10, 20, 35)]
        rates = {"maker_fee_rate": -0.0001, "taker_fee_rate": 0.0006}
        got = M.cost_breakdown(fills, funding, rates)
        want = {"maker_fee": 0.0, "taker_fee": 0.0, "spread": 0.0, "funding": 0.0}
        for f in fills:
            want[f["liquidity"] + "_fee"] += f["px"] * f["qty"] * rates[f["liquidity"] + "_fee_rate"]
            want["spread"] += (1 if f["side"] == "buy" else -1) * (f["px"] - f["mid"]) * f["qty"]
        for ev in funding:  # position strictly before the event (the core applies funding before fills)
            pos = sum((1 if f["side"] == "buy" else -1) * f["qty"] for f in fills if f["t_ns"] < ev["t_ns"])
            want["funding"] += pos * ev["mark"] * ev["rate"]
        for k in want:
            assert got[k] == pytest.approx(want[k], abs=1e-9)
    nomid = [dict(fills[0], mid=None)]
    assert M.cost_breakdown(nomid, [], rates)["spread"] is None
    with pytest.raises(ReportError):
        M.cost_breakdown(fills, funding, {"maker_fee_rate": 0.0})


def test_drawdown_grid():
    r = random.Random(5)
    for _ in range(300):
        eq = [r.choice((50.0, 100.0)) + r.uniform(-40, 40) for _ in range(r.randrange(1, 25))]
        want_abs = max(max(eq[:j + 1]) - eq[j] for j in range(len(eq)))
        want_pct = max((max(eq[:j + 1]) - eq[j]) / max(eq[:j + 1]) * 100 for j in range(len(eq)))
        got = M.drawdown(eq)
        assert got["max_dd_abs"] == pytest.approx(want_abs) and got["max_dd_pct"] == pytest.approx(want_pct)
    assert M.drawdown([0.0, -5.0, 3.0])["max_dd_pct"] is None
    assert M.drawdown([0.0, -5.0, 3.0])["max_dd_abs"] == 5.0


def test_round_trips_match_the_cash_flow():
    r = random.Random(6)
    for _ in range(200):
        pos, fills, reasons = 0.0, [], {}
        for i in range(r.randrange(1, 8)):
            side = r.choice(("buy", "sell"))
            q = float(r.choice((1, 2, 3)))
            fills.append({"order_id": f"o{i}", "t_ns": i * S, "side": side, "qty": q, "px": float(100 + r.randrange(20)),
                          "fee": r.choice((0.0, 0.3))})
            reasons[f"o{i}"] = r.choice(("tp", "sl"))
            pos += q if side == "buy" else -q
        if pos:
            fills.append({"order_id": "close", "t_ns": 99 * S, "side": "sell" if pos > 0 else "buy", "qty": abs(pos),
                          "px": 110.0, "fee": 0.1})
            reasons["close"] = "time_exit"
        trades = RP.round_trips(fills, reasons)
        cash = sum((-1 if f["side"] == "buy" else 1) * f["px"] * f["qty"] - f["fee"] for f in fills)
        assert sum(t["pnl"] for t in trades) == pytest.approx(cash, abs=1e-9)
        assert RP.open_lots(fills) == pytest.approx(0.0)
        by = M.exit_reasons(trades)
        assert sum(v["n"] for v in by.values()) == len(trades)
    with pytest.raises(ReportError):
        RP.round_trips([{"order_id": "a", "t_ns": 0, "side": "buy", "qty": 1.0, "px": 1.0, "fee": 0.0},
                        {"order_id": "b", "t_ns": 1, "side": "sell", "qty": 1.0, "px": 1.0, "fee": 0.0}], {})


BASE = {"id": "t", "side": "buy", "qty": 1.0, "entry_px": 100.0, "exit_px": 101.0, "entry_t_ns": 0, "exit_t_ns": H,
        "fees": 0.0}


@pytest.mark.parametrize("change", [{"fees": None}, {"side": "long"}, {"qty": 0.0}, {"entry_px": -1.0},
                                    {"exit_px": float("nan")}, {"qty": True}, {"exit_t_ns": -1}, {"entry_t_ns": 1.5}])
def test_trade_refusals(change):
    t = dict(BASE, **change)
    if change.get("fees", 0) is None:
        del t["fees"]
    with pytest.raises(ReportError):
        M.trade_distribution([t])
