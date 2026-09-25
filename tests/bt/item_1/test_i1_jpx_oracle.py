"""V6 adversary: JPX corporate actions and the point-in-time universe
against an oracle that walks each company's days with plain loops and
fractions (the factor of day d is the product of the company's splits with
d < ex_date <= as_of, collected walking back from as_of).

Drawn from 600 seeds: 1..4 companies, a listing each (some delisted inside
the window, some listed inside it), 0..2 code changes, 0..3 splits /
reverse splits with ratios {2, 3, 5, 3/2, 1/4}, a bar every day of the
listing under the code of that day, prices that are not multiples of the
ratios (so the float rounding of the exact value is what is compared),
as_of anywhere in the window (so some actions are after it). Not drawn:
several companies sharing a code at different times (refused as
ambiguous by the implementation only when simultaneous; the oracle does not
model code reuse -- listed as a gap), bars on non-trading days (the module
has no calendar; any date is a day).
"""
from __future__ import annotations

import datetime as dt
import random
from fractions import Fraction

import pytest

from bot.bt.data import CorporateActionError, Universe, adjust_daily, universe

D0 = dt.date(2026, 1, 1)
DAYS = [(D0 + dt.timedelta(days=k)).isoformat() for k in range(20)]


def draw(rng):
    comps = []
    for c in range(rng.randint(1, 4)):
        li = rng.randrange(0, 10) if rng.random() < 0.4 else None
        de = rng.randrange((li or 0) + 2, 21) if rng.random() < 0.4 else None
        listed = DAYS[li] if li is not None else "2000-01-04"
        delisted = DAYS[de] if (de is not None and de < 20) else None
        live = [d for d in DAYS if d >= listed and (delisted is None or d < delisted)]
        codes = [(None, f"{1000 + c}")]
        for k, ex in enumerate(sorted(rng.sample(live[1:], min(len(live) - 1, rng.randint(0, 2))))):
            codes.append((ex, f"{2000 + 10 * c + k}"))
        splits = []
        for ex in sorted(rng.sample(live[1:], min(len(live) - 1, rng.randint(0, 3)))):
            splits.append((ex, rng.choice(["split", "reverse_split"]), rng.choice([2, 3, 5, Fraction(3, 2), Fraction(1, 4)])))
        comps.append({"listed": listed, "delisted": delisted, "live": live, "codes": codes, "splits": splits})
    return comps


def code_on(comp, day):
    code = comp["codes"][0][1]
    for ex, new in comp["codes"][1:]:
        if ex <= day:
            code = new
    return code


def inputs(rng, comps):
    bars, actions, listings = [], [], []
    for comp in comps:
        listings.append({"code": comp["codes"][0][1], "listed": comp["listed"], "delisted": comp["delisted"]})
        prev = comp["codes"][0][1]
        for ex, new in comp["codes"][1:]:
            actions.append({"code": prev, "type": "code_change", "ex_date": ex, "new_code": new})
            prev = new
        for ex, typ, r in comp["splits"]:
            ratio = r if isinstance(r, int) else str(float(r))
            actions.append({"code": code_on(comp, ex), "type": typ, "ex_date": ex, "ratio": ratio})
        for d in comp["live"]:
            base = rng.randrange(101, 997)
            bars.append({"code": code_on(comp, d), "date": d, "open": base, "high": base + 7, "low": base - 3,
                         "close": str(base + 1) + ".3", "volume": rng.randrange(1, 10**6)})
    rng.shuffle(actions)
    return bars, actions, listings


def oracle_adjust(comps, bars, as_of):
    out = {}
    for comp in comps:
        mine = [b for b in bars if b["date"] <= as_of and b["date"] in comp["live"] and b["code"] == code_on(comp, b["date"])]
        if not mine:
            continue
        name = code_on(comp, as_of) if (comp["delisted"] is None or as_of < comp["delisted"]) else code_on(comp, comp["live"][-1])
        rows = []
        for b in sorted(mine, key=lambda x: x["date"]):
            pf = vf = Fraction(1)
            walk = as_of
            for ex, typ, r in sorted(comp["splits"], reverse=True):
                if b["date"] < ex <= walk:
                    r = Fraction(r)
                    pf, vf = (pf / r, vf * r) if typ == "split" else (pf * r, vf / r)
            rows.append({"date": b["date"], **{k: float(Fraction(str(b[k])) * pf) for k in ("open", "high", "low", "close")},
                         "volume": float(Fraction(b["volume"]) * vf)})
        out[name] = rows
    return out


def oracle_universe(comps, day):
    return sorted(code_on(c, day) for c in comps if c["listed"] <= day and (c["delisted"] is None or day < c["delisted"]))


SEEDS = list(range(600))


@pytest.mark.parametrize("seed", SEEDS)
def test_adjust_and_universe_match_the_oracle(seed):
    rng = random.Random(seed)
    comps = draw(rng)
    bars, actions, listings = inputs(rng, comps)
    as_of = rng.choice(DAYS)
    got = adjust_daily(bars, actions, listings, as_of)
    assert got == oracle_adjust(comps, bars, as_of)
    u = universe(listings, actions, DAYS)
    assert u == {d: oracle_universe(comps, d) for d in DAYS}


def test_the_seeds_exercise_every_action_and_the_as_of_cut():
    n = {"split": 0, "reverse_split": 0, "code_change": 0, "after_as_of": 0, "delisted": 0}
    for seed in SEEDS:
        rng = random.Random(seed)
        comps = draw(rng)
        bars, actions, listings = inputs(rng, comps)
        as_of = rng.choice(DAYS)
        for a in actions:
            n[a["type"]] += 1
            n["after_as_of"] += a["ex_date"] > as_of
        n["delisted"] += sum(c["delisted"] is not None for c in comps)
    assert all(v >= 100 for v in n.values()), n


BASE_BARS = [{"code": "1", "date": "2026-01-05", "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1}]
LIST1 = [{"code": "1", "listed": "2000-01-04", "delisted": None}]


@pytest.mark.parametrize("bars,actions,listings,as_of", [
    (BASE_BARS * 2, [], LIST1, "2026-01-09"),  # two bars for one code and day
    ([dict(BASE_BARS[0], code="9")], [], LIST1, "2026-01-09"),  # bar under a code with no listing is its own company;
    (BASE_BARS, [{"code": "7", "type": "split", "ex_date": "2026-01-06", "ratio": 2}], LIST1, "2026-01-09"),
    (BASE_BARS, [{"code": "1", "type": "split", "ex_date": "2026-01-06", "ratio": 0}], LIST1, "2026-01-09"),
    (BASE_BARS, [{"code": "1", "type": "split", "ex_date": "2026-1-6", "ratio": 2}], LIST1, "2026-01-09"),
    (BASE_BARS, [{"code": "1", "type": "dividend", "ex_date": "2026-01-06"}], LIST1, "2026-01-09"),
    (BASE_BARS, [{"code": "1", "type": "code_change", "ex_date": "2026-01-06", "new_code": "2"},
                 {"code": "1", "type": "code_change", "ex_date": "2026-01-06", "new_code": "3"}], LIST1, "2026-01-09"),
    ([dict(BASE_BARS[0], date="2026-01-07")], [{"code": "1", "type": "code_change", "ex_date": "2026-01-06", "new_code": "2"}],
     LIST1, "2026-01-09"),  # a bar under the old code after the change
    (BASE_BARS, [], [{"code": "1", "listed": "2026-01-06", "delisted": None}], "2026-01-09"),  # bar before its listing
    (BASE_BARS, [], LIST1, "2026-13-01"),
])
def test_inconsistent_inputs_are_refused(bars, actions, listings, as_of):
    if bars and bars[0]["code"] == "9":
        # a code with no listing and no action is a company of its own: accepted, not refused
        assert adjust_daily(bars, actions, listings, as_of) == {"9": [{"date": "2026-01-05", "open": 1.0, "high": 1.0,
                                                                        "low": 1.0, "close": 1.0, "volume": 1.0}]}
        return
    with pytest.raises(CorporateActionError):
        adjust_daily(bars, actions, listings, as_of)


def test_universe_object_is_point_in_time():
    u = Universe([{"code": "A", "listed": "2026-01-02", "delisted": "2026-01-04"}],
                 [{"code": "A", "type": "code_change", "ex_date": "2026-01-03", "new_code": "B"}])
    assert [u.on(d) for d in ("2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04")] == [[], ["A"], ["B"], []]
