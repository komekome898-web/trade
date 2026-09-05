"""Generation-4 CODE-AS-CLAIM reference fill simulator (maker fill model).

Implements, verbatim, the v3 fill rule stated at the top of
docs/QA/claims_for_auditors_maker3_v3.md:

    resting order joins the back of the displayed queue at insertion; it
    fills when cumulative executions at its price on its side since
    insertion exceed queue-ahead + own size, or partially per FIFO;
    cancelled and re-joined at the new best when the touch moves away;
    after our own fill, the OPPOSITE-side exit order is a NEW order
    inserted at the back of the displayed queue AT THAT MOMENT
    (queue-ahead = displayed size at insertion, minus own size, since the
    displayed size at insertion already includes our own just-joined
    clip); each entry has its own exit order, there is no netting across
    positions, and at most one open position per side at a time (a new
    entry quote on a side is placed only when that side has no open
    position); ticker rows are written AFTER the execution(s) at that
    same timestamp are applied (post-trade); positions = completed entry
    fills; forced exits at the 300 s cap cross EXACTLY at the displayed
    public touch at exit time -- no additional slippage is modelled.

This module is the CLAIM, not merely a tool that produces one -- per
docs/AUDIT_2026-09/PROTOCOL.md "Maker fill-model claims", an auditor may
read this file directly. Every place where the prose above leaves a
decision open is resolved explicitly below in RULE_DECISIONS.
"""
from __future__ import annotations

import pandas as pd

TICK = 10.0  # this packet's instrument tick (docs/QA manifest: 10.0 price units)

RULE_DECISIONS = [
    "Partial fills accumulate cumulatively while an order rests at a fixed "
    "price; a position is 'completed' (appears in the output) only once "
    "cumulative same-price executions since insertion have fully filled "
    "own_size AND that cumulative volume strictly EXCEEDS queue-ahead + "
    "own_size (see decision 7). A cancel-and-rejoin (touch move) forfeits "
    "any partial progress; the new order starts at zero.",
    "Two directional machines per side vs one shared slot: this simulator "
    "gives each book side (bid, ask) exactly ONE shared resting-order "
    "slot. A side's slot holds at most one order: either that side's own "
    "entry order, or the exit order for a position that was entered via "
    "the OPPOSITE side (an exit always lands on the side opposite its "
    "entry). Exits always evict (cancel, no fill credit) any resting "
    "entry order occupying the slot they need -- closing existing "
    "exposure takes priority over opening a new one.",
    "Exit order insertion moment: the exit order is created at the exact "
    "instant (timestamp) its entry order completes, at the CURRENT touch "
    "of the opposite side (never improved, regardless of S1/S2), at the "
    "back of that side's displayed queue.",
    "Tie-breaking at equal timestamps: when an execution row and a ticker "
    "row share a timestamp, the execution is applied first (the ticker "
    "row is the post-trade state, per the rule text). Among execution "
    "rows sharing a timestamp, they are applied in file order (stable).",
    "Crossed ticker rows (best_bid >= best_ask) are skipped entirely: "
    "they do not update tracked touch price/size and cannot trigger a "
    "touch-move cancel/rejoin. Execution rows at the same timestamp are "
    "still applied normally, against whatever the last VALID touch state "
    "was.",
    "Queue-ahead at insertion = the raw displayed size (best_bid_size / "
    "best_ask_size) on that side from the most recent valid ticker row "
    "at or before insertion time -- MINUS own_size when, and only when, "
    "the inserted order is an EXIT order (role=='exit') priced at the "
    "current touch: the rule text and the v3 manifest both say the exit "
    "order's queue-ahead is 'displayed size at insertion, minus own "
    "size, since the displayed size at insertion already includes our "
    "own just-joined clip' -- true here because this reused tape was "
    "generated with an S1 bot's own clip already resting on the book, "
    "so its displayed sizes always include that clip once an order of "
    "ours occupies the side (manifest.md). This subtraction does NOT "
    "apply to ENTRY order insertion (initial, or after a touch-move "
    "rejoin, decision 8): at the moment a brand-new entry order is "
    "placed, no clip of ours is yet resting on that side, so the last "
    "known displayed size predates and does not include it -- the text "
    "makes no 'minus own size' claim for entries, only for the exit "
    "clause. Queue-ahead is clamped at 0 if own_size would exceed the "
    "displayed size (can happen if the baked-in footprint reflects a "
    "different own_size than 0.05). An order that improves the touch "
    "(S2 inside-quote) has queue-ahead = 0 regardless (nothing can be "
    "ahead of a brand-new best price). No attempt is made to purify a "
    "pre-existing own footprint baked into a reused tape's displayed "
    "sizes beyond this single documented subtraction -- this is why "
    "this simulator's numbers on a reused tape can differ from that "
    "tape's original packet's sealed values (expected; see "
    "docs/QA/answers_sealed_maker4.json).",
    "Fill/no-fill boundary at exact equality: per the literal rule text "
    "('... since insertion EXCEED queue-ahead + own size'), an order "
    "completes only when cumulative same-price executions since "
    "insertion are STRICTLY GREATER THAN queue-ahead + own_size. Volume "
    "exactly equal to that threshold is a full partial fill but NOT yet "
    "'completed' -- it waits for the next qualifying print, or the cap, "
    "to formally complete.",
    "Touch-move eviction applies uniformly to entry AND exit orders: if a "
    "resting order's side's target price changes (the touch itself "
    "moves, or, for S2, the improve/at-best regime flips because spread "
    "crossed the 2-tick boundary), the order cancels and rejoins at the "
    "new target price, forfeiting partial progress (decision 1).",
    "Forced exit at the cap: exit_ts = entry_ts + cap_s exactly. The "
    "forced exit is a TAKER order that crosses the spread immediately "
    "to close out, so exit_price = the touch price on the POSITION'S "
    "OWN (entry) side -- the UNFAVOURABLE side to cross into -- as last "
    "known at that instant: a long (entered on the bid) is force-sold "
    "into the bid, a short (entered on the ask) is force-bought into "
    "the ask. This is the opposite side from where the (now-cancelled) "
    "passive exit order had been resting -- that resting order priced "
    "at the favourable touch is exactly what a forced/taker exit does "
    "NOT get to use. No additional slippage beyond that crossing is "
    "modelled, per the rule text ('cross EXACTLY at the displayed "
    "public touch').",
    "Naive mode (naive=True; used only to build the queue-blind "
    "comparison population, never for S1/S2): identical order "
    "placement, eviction, and touch-move/rejoin logic to the true rule, "
    "but on the FIRST execution matching a resting order's book_side "
    "and price, that order completes UNCONDITIONALLY -- queue-ahead, "
    "own_size, and the incoming print's own size are all ignored (cum "
    "is never accumulated; the completion check is 'a matching print "
    "occurred', not 'cumulative volume exceeded a threshold'). This is "
    "queue position ignored entirely, not merely zeroed: even a matching "
    "print far smaller than own_size completes the order immediately.",
    "entry_ts/entry_price/exit_ts/exit_price record the moment an order "
    "COMPLETES (not the earlier moment it was inserted).",
    "markout_5s_bps sign convention: positive = price moved in the "
    "position's favor over [entry_ts, entry_ts+5s], using mid = "
    "(best_bid+best_ask)/2 at the last known valid ticker state at/before "
    "each timestamp.",
    "A position that is still open when the tape ends (no exit fill, cap "
    "not yet reached within the data) is dropped -- only completed "
    "round trips appear in the output.",
]


def _entry_price(side: str, bid: float, ask: float, strategy: str) -> float:
    spread_ticks = round((ask - bid) / TICK)
    improve = strategy == "S2" and spread_ticks >= 2
    if side == "bid":
        return bid + TICK if improve else bid
    return ask - TICK if improve else ask


class _Slot:
    __slots__ = ("role", "price", "queue_ahead", "cum")

    def __init__(self, role: str, price: float, queue_ahead: float):
        self.role, self.price, self.queue_ahead, self.cum = role, price, queue_ahead, 0.0


class _Position:
    __slots__ = ("direction", "entry_ts", "entry_price", "entry_mid")

    def __init__(self, direction, entry_ts, entry_price, entry_mid):
        self.direction, self.entry_ts = direction, entry_ts
        self.entry_price, self.entry_mid = entry_price, entry_mid


def simulate(ticker_df: pd.DataFrame, exec_df: pd.DataFrame, strategy: str = "S1",
             cap_s: float = 300.0, own_size: float = 0.05, naive: bool = False) -> pd.DataFrame:
    """Replay the public ticker+execution tapes under the v3 fill rule."""
    t = ticker_df.copy()
    t["ts"] = pd.to_datetime(t["ts"], utc=True)
    t = t.sort_values("ts", kind="mergesort").reset_index(drop=True)

    e = exec_df.copy()
    e["ts"] = pd.to_datetime(e["ts"], utc=True)
    e = e.sort_values("ts", kind="mergesort").reset_index(drop=True)

    touch = {"bid": None, "ask": None}
    disp = {"bid": None, "ask": None}
    slot: dict[str, _Slot | None] = {"bid": None, "ask": None}
    position: dict[str, _Position | None] = {"bid": None, "ask": None}
    rows_out: list[dict] = []
    opposite = {"bid": "ask", "ask": "bid"}

    def check_caps(now):
        for side in ("bid", "ask"):
            pos = position[side]
            if pos is not None and now >= pos.entry_ts + pd.Timedelta(seconds=cap_s):
                exit_side = opposite[side]
                deadline = pos.entry_ts + pd.Timedelta(seconds=cap_s)
                # Forced exit is a TAKER cross into the UNFAVOURABLE side --
                # the position's own entry side (bid for a long, ask for a
                # short), not the passive exit order's resting side
                # (exit_side). See RULE_DECISIONS "Forced exit at the cap".
                rows_out.append(dict(direction=("long" if side == "bid" else "short"),
                                      entry_ts=pos.entry_ts, entry_price=pos.entry_price,
                                      exit_ts=deadline, exit_price=touch[side], forced=True,
                                      entry_mid=pos.entry_mid))
                position[side] = None
                slot[exit_side] = None

    def refresh(side):
        opp = opposite[side]
        if touch[side] is None:
            return
        if position[opp] is not None:
            role, price = "exit", touch[side]
        elif position[side] is None:
            role, price = "entry", _entry_price(side, touch["bid"], touch["ask"], strategy)
        else:
            slot[side] = None
            return
        cur = slot[side]
        if cur is not None and cur.role == role and cur.price == price:
            return
        if price != touch[side]:
            qa = 0.0  # S2 inside-quote: nothing can be ahead of a brand-new best
        elif role == "exit":
            # Exit order's displayed size at insertion already includes our
            # own just-joined clip (rule text + manifest) -- subtract it.
            qa = max(0.0, (disp[side] or 0.0) - own_size)
        else:
            # Entry order (initial or post-rejoin): no clip of ours is yet
            # resting on this side, so the raw displayed size is used as-is.
            qa = disp[side] or 0.0
        new_slot = _Slot(role, price, qa)
        if cur is not None and cur.role == role:
            # touch-move rejoin (same role, price changed to the new best)
            new_slot.cum = cur.cum
        slot[side] = new_slot

    def complete(side, now):
        s = slot[side]
        if s.role == "entry":
            direction = "long" if side == "bid" else "short"
            mid = (touch["bid"] + touch["ask"]) / 2.0
            position[side] = _Position(direction, now, s.price, mid)
            slot[side] = None
        else:
            opp = opposite[side]
            pos = position[opp]
            rows_out.append(dict(direction=("long" if opp == "bid" else "short"),
                                  entry_ts=pos.entry_ts, entry_price=pos.entry_price,
                                  exit_ts=now, exit_price=s.price, forced=False,
                                  entry_mid=pos.entry_mid))
            position[opp] = None
            slot[side] = None
        refresh("bid")
        refresh("ask")

    def apply_execution(ts, price, size, taker_side):
        check_caps(ts)
        book_side = "bid" if taker_side == "SELL" else "ask"
        s = slot[book_side]
        if s is None or price != s.price:
            return
        if naive:
            complete(book_side, ts)
            return
        s.cum += size
        threshold = s.queue_ahead + own_size
        if s.cum > threshold:
            complete(book_side, ts)

    def apply_ticker(ts, bid, ask, bid_sz, ask_sz):
        check_caps(ts)
        if bid >= ask:
            return  # crossed row: skip entirely (decision 5)
        touch["bid"], touch["ask"] = bid, ask
        disp["bid"], disp["ask"] = bid_sz, ask_sz
        refresh("bid")
        refresh("ask")

    ti, ei = 0, 0
    n_t, n_e = len(t), len(e)
    while ti < n_t or ei < n_e:
        t_ts = t["ts"].iat[ti] if ti < n_t else None
        e_ts = e["ts"].iat[ei] if ei < n_e else None
        if e_ts is not None and (t_ts is None or e_ts <= t_ts):
            row = e.iloc[ei]
            apply_execution(row["ts"], row["price"], row["size"], row["side"])
            ei += 1
        else:
            row = t.iloc[ti]
            apply_ticker(row["ts"], row["best_bid"], row["best_ask"],
                         row["best_bid_size"], row["best_ask_size"])
            ti += 1

    out = pd.DataFrame(rows_out, columns=["direction", "entry_ts", "entry_price", "exit_ts",
                                           "exit_price", "forced", "entry_mid"])
    if out.empty:
        out["net_bps"] = []
        out["markout_5s_bps"] = []
        return out.drop(columns=["entry_mid"])[
            ["direction", "entry_ts", "entry_price", "exit_ts", "exit_price", "forced",
             "net_bps", "markout_5s_bps"]]

    sign = out["direction"].map({"long": 1.0, "short": -1.0})
    out["net_bps"] = sign * (out["exit_price"] - out["entry_price"]) / out["entry_price"] * 1e4

    valid = t[t["best_bid"] < t["best_ask"]].copy()
    valid["mid"] = (valid["best_bid"] + valid["best_ask"]) / 2.0
    valid_ts = valid["ts"].to_numpy()
    valid_mid = valid["mid"].to_numpy()

    def mid_at(ts):
        idx = valid_ts.searchsorted(ts, side="right") - 1
        return valid_mid[idx] if idx >= 0 else float("nan")

    later = out["entry_ts"] + pd.Timedelta(seconds=5.0)
    mid5 = later.map(mid_at)
    out["markout_5s_bps"] = sign * (mid5 - out["entry_mid"]) / out["entry_mid"] * 1e4
    return out.drop(columns=["entry_mid"])[
        ["direction", "entry_ts", "entry_price", "exit_ts", "exit_price", "forced",
         "net_bps", "markout_5s_bps"]]
