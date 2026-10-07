"""What fill model a run selects: the tier (tool catalogue section 2.1), the
stance on cancels ahead in the queue (section 2.2) and the market-impact
function. Nothing is chosen for the run: `FillSpec.tier` has no default, a
queue tier (5) needs its stance, an impact tier (6) needs its function.

Tiers (docs/DATA/TOOLS_CATALOG.md section 2.1, one line each there; the
concrete rule this model applies is written next to each):

  0  always fills -- a resting limit order fills in full when it rests, at
     its limit price.
  1  fills when the price crosses -- the first trade strictly through the
     limit (a buy: a trade below it) fills the whole remainder at the limit.
  2  compares with the next bar and leaves unfilled -- only bars decide: the
     first bar that starts at or after the order began resting and whose
     low (a buy) / high (a sell) reaches the limit fills the remainder at the
     limit, at the bar's close time (the bar is known then).
  3  the fill-deciding arrival is an event -- the first trade that reaches
     the limit (touches it) fills the whole remainder.
  4  reads the volume -- each trade that reaches the limit fills up to its
     own size (our orders at better prices first, then by arrival).
  5  tracks our place in the queue -- at rest, the external size displayed
     at our price is ahead of us (reduced by the cancel stance); a trade AT
     our price whose aggressor hits our side (or is unknown) first consumes
     what is ahead, then fills us; a trade strictly through our price fills
     the whole remainder.
  6  has a market-impact function -- as 5 for resting orders, and every
     aggressive execution (market, marketable limit, triggered stop) is
     priced by the impact function instead of walking the book.

Without a tier, aggressive executions walk the displayed book (best level
first, each level up to its size); a run with no book prices them from the
last trade and the declared spread (rule `market_ref`).

A tier-2 run may select a second rule for resting limit orders on bars
(`bar_rule`, None = the rule of tier 2 above, unchanged), and with it when an
exit attached to an entry starts to fill (`attached_exit`). The owner's
scenario (L-769, L-770; docs/DISCUSSIONS/2026-10-06_held_batches/
DELEGATION_fill_scenario_L769.md):

  bar_rule "range_open" -- a limit order resting at time T (a bar's close)
     is tried from the bar that STARTS at T (start >= the time it rested):
     low <= limit <= high fills it at the limit; a limit beyond the range in
     the direction that fills (a buy above the high, a sell below the low)
     fills it at the bar's open (L-770 a); beyond the range the other way it
     does not fill on that bar. The limit is the price the venue holds (after
     rounding to the tick by rule off_tick). Every such fill is the maker (the
     open fill too: the owner's decision L-783 「maker」). A stop
     order is refused (FillSpecError, the run stops): how a stop is tried
     under this rule is not decided.
     "Resting at a bar's close" is the order's arrival at the venue: the rule
     needs the order delay to be 0 (bot.bt.pipeline refuses a run that
     selects bar_rule with an order latency that can be other than 0; with a
     delay the order would meet the bar after the signal's next one).
  attached_exit -- an exit limit sent with its entry (extra key
     `attached_to` = the entry's client_order_id; venue.ATTACHED_KEY) lives
     only after the entry fills, for the size the entry filled (L-770 b):
     "same_bar" (the optimistic side): on the bar that filled the entry, the
     exit fills at its limit when low <= limit <= high; otherwise, and on
     later bars, as bar_rule. "next_bar" (the pessimistic side): from the
     bar after the one that filled the entry, as bar_rule.
  The two go together (both set or both None) and need tier 2.

The tier's number is kept on the model (`SimVenue.tier`); the model has no
default tier, so its "tier by default" is none: the run must choose
(`TIER_BY_DEFAULT = None`), and every tier 0-6 can be chosen
(`TIER_MECHANISM = 6`).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from bot.bt.orders.errors import ExecutionModelError

TIERS: dict[int, str] = {
    0: "always fills: a resting limit fills in full at its limit when it rests",
    1: "price crosses: the first trade strictly through the limit fills the remainder",
    2: "next bar: the first bar starting at/after rest whose low/high reaches the limit fills it at the close",
    3: "touch is an event: the first trade reaching the limit fills the remainder",
    4: "volume: each trade reaching the limit fills up to its size",
    5: "queue position: displayed size ahead at rest, consumed by trades at our price",
    6: "market impact: tier 5 for resting orders, the impact function prices aggressive executions",
}
TIER_MECHANISM = 6
TIER_BY_DEFAULT = None

# stance on cancels ahead of us (catalogue section 2.2) -> the candidate whose
# stance it is (catalogue number) and the rule applied
CANCEL_STANCES: dict[str, tuple[str, str]] = {
    "none": ("95", "cancels ahead are invisible: the size ahead only falls when trades consume it"),
    "discount_at_entry": ("57", "once, at rest: ahead *= (1 - cancel_rate); nothing afterwards"),
    "l3_advance": ("104", "per-order feed: a cancelled order ahead leaves the queue at once"),
    "l3_mark": ("98", "per-order feed: a cancelled order ahead is marked and skipped when reached"),
    "snapshot_cap": ("90", "each book update: ahead = min(ahead, displayed size at our price)"),
    "prob": ("probabilistic queue model",
             "a fall of the displayed size by d: the part in front of us is d * f(front)/(f(front)+f(back)), "
             "ahead = min(front - (1-p) d + min(back - p d, 0), new size), p = f(back)/(f(back)+f(front))"),
}
PROB_FUNCTIONS = ("power", "log")

# the second rule for resting limit orders on bars (tier 2) and when an attached exit starts (see the docstring)
BAR_RULES: dict[str, str] = {
    "range_open": "from the bar starting when the limit rested: in [low, high] at the limit, beyond it in the "
                  "filling direction at the open, else no fill (L-769, L-770 a)",
}
ATTACHED_EXITS: dict[str, str] = {
    "same_bar": "an exit sent with its entry may fill on the bar that filled the entry, at its limit when the limit "
                "is in [low, high] (the optimistic side, L-769 / L-770 b)",
    "next_bar": "an exit sent with its entry is tried from the bar after the one that filled the entry "
                "(the pessimistic side, L-769)",
}

IMPACT_KINDS = ("linear_temporary", "sqrt_temporary", "linear_permanent")
IMPACT_BASES = ("best_ask", "best_bid", "opposite_best", "mid")


class FillSpecError(ExecutionModelError):
    pass


def _num(name: str, v, *, positive: bool = False, fraction: bool = False) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0:
        raise FillSpecError(f"{name} must be a finite number >= 0, got {v!r}")
    if positive and v <= 0:
        raise FillSpecError(f"{name} must be > 0, got {v!r}")
    if fraction and v > 1:
        raise FillSpecError(f"{name} must be in [0, 1], got {v!r}")
    return float(v)


@dataclass(frozen=True)
class ImpactSpec:
    """The price of an aggressive execution of size q (sign s = +1 buy, -1 sell):

    linear_temporary: basis + s * k * q
    sqrt_temporary:   basis * (1 + s * eta * sqrt(q / adv))
    linear_permanent: basis + s * k * q, then every later price moves by
                      s * gamma * q (the permanent part; k is the temporary
                      part, 0 for none)

    `basis`: best_ask / best_bid / mid of the displayed book, or opposite_best
    (the best ask for a buy, the best bid for a sell), plus the permanent
    shift accumulated so far."""

    kind: str
    basis: str
    k: Optional[float] = None
    eta: Optional[float] = None
    adv: Optional[float] = None
    gamma: Optional[float] = None

    def __post_init__(self) -> None:
        if self.kind not in IMPACT_KINDS:
            raise FillSpecError(f"impact kind {self.kind!r}: one of {IMPACT_KINDS}")
        if self.basis not in IMPACT_BASES:
            raise FillSpecError(f"impact basis {self.basis!r}: one of {IMPACT_BASES}")
        needed = {"linear_temporary": ("k",), "sqrt_temporary": ("eta", "adv"),
                  "linear_permanent": ("k", "gamma")}[self.kind]
        for name in ("k", "eta", "adv", "gamma"):
            v = getattr(self, name)
            if name in needed:
                if v is None:
                    raise FillSpecError(f"impact {self.kind} needs {name}")
                object.__setattr__(self, name, _num(f"impact.{name}", v, positive=(name == "adv")))
            elif v is not None:
                raise FillSpecError(f"impact {self.kind} takes no {name}")

    def price(self, sign: int, q: float, basis: float) -> float:
        if self.kind == "sqrt_temporary":
            return basis * (1.0 + sign * self.eta * math.sqrt(q / self.adv))  # type: ignore[operator]
        return basis + sign * self.k * q  # type: ignore[operator]

    def permanent_shift(self, sign: int, q: float) -> float:
        return sign * self.gamma * q if self.kind == "linear_permanent" else 0.0  # type: ignore[operator]


@dataclass(frozen=True)
class FillSpec:
    tier: int
    cancel_stance: Optional[str] = None
    cancel_rate: Optional[float] = None
    prob_f: Optional[str] = None
    prob_n: Optional[float] = None
    impact: Optional[ImpactSpec] = None
    bar_ns: Optional[int] = None
    bar_rule: Optional[str] = None
    attached_exit: Optional[str] = None

    def __post_init__(self) -> None:
        if type(self.tier) is not int or self.tier not in TIERS:
            raise FillSpecError(f"tier must be one of {sorted(TIERS)}, got {self.tier!r}")
        st = self.cancel_stance
        if st is not None:
            if st not in CANCEL_STANCES:
                raise FillSpecError(f"cancel_stance {st!r}: one of {tuple(CANCEL_STANCES)}")
            if self.tier < 5 and st != "none":
                # "none" claims no handling of cancels, which is what tiers 0-4 do;
                # any other stance would claim an effect these tiers do not have
                raise FillSpecError(f"cancel_stance {st!r} acts in a queue tier (5, 6), not tier {self.tier}")
        elif self.tier == 5:
            raise FillSpecError("tier 5 (queue position) needs its cancel_stance")
        if (st == "discount_at_entry") != (self.cancel_rate is not None):
            raise FillSpecError("cancel_rate goes with cancel_stance 'discount_at_entry' (and only with it)")
        if self.cancel_rate is not None:
            object.__setattr__(self, "cancel_rate", _num("cancel_rate", self.cancel_rate, fraction=True))
        if st == "prob":
            if self.prob_f not in PROB_FUNCTIONS:
                raise FillSpecError(f"cancel_stance 'prob' needs prob_f in {PROB_FUNCTIONS}")
            if (self.prob_f == "power") != (self.prob_n is not None):
                raise FillSpecError("prob_n goes with prob_f 'power' (and only with it)")
            if self.prob_n is not None:
                object.__setattr__(self, "prob_n", _num("prob_n", self.prob_n, positive=True))
        elif self.prob_f is not None or self.prob_n is not None:
            raise FillSpecError("prob_f / prob_n go with cancel_stance 'prob'")
        if (self.tier == 6) != (self.impact is not None):
            raise FillSpecError("tier 6 needs an impact function; other tiers take none")
        if self.impact is not None and type(self.impact) is not ImpactSpec:
            raise FillSpecError("impact must be an ImpactSpec")
        if self.bar_ns is not None and (type(self.bar_ns) is not int or self.bar_ns <= 0):
            raise FillSpecError(f"bar_ns must be an int > 0, got {self.bar_ns!r}")
        if self.bar_rule is not None and self.bar_rule not in BAR_RULES:
            raise FillSpecError(f"bar_rule {self.bar_rule!r}: one of {tuple(BAR_RULES)} (or None)")
        if self.attached_exit is not None and self.attached_exit not in ATTACHED_EXITS:
            raise FillSpecError(f"attached_exit {self.attached_exit!r}: one of {tuple(ATTACHED_EXITS)} (or None)")
        if (self.bar_rule is None) != (self.attached_exit is None):
            raise FillSpecError("bar_rule and attached_exit go together (both set or both None)")
        if self.bar_rule is not None and self.tier != 2:
            raise FillSpecError(f"bar_rule {self.bar_rule!r} is a rule of tier 2 (bars), not tier {self.tier}")

    def prob_weight(self, x: float) -> float:
        x = max(x, 0.0)
        if self.prob_f == "log":
            return math.log1p(x)
        return x ** self.prob_n  # type: ignore[operator]
