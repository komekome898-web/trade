# Hand derivation -- micro-tape (e): cap expiry -> forced exit at touch
# ROUND 2: corrected for the round-1 forced-exit pricing bug
# (simulate() called with cap_s=5)

bid=1000 size=0.05 -> queue_ahead=0.05 (entry order: no minus-own, see
RULE_DECISIONS), threshold=0.10.
- t=1 SELL 1000 0.20 -> cum=0.20 (>0.10) -> ENTRY COMPLETES at t=1,
  price=1000 (long).

Exit created at t=1 on ask side: ask=1010, raw displayed ask size=5.0;
this is an EXIT order at the current touch, so per RULE_DECISIONS
queue_ahead = displayed size MINUS own_size = 5.0 - 0.05 = 4.95,
threshold = 5.00 (deliberately huge so no realistic BUY volume in this
tiny tape can ever complete it passively).

Remaining executions (t=2..5) are all either at a different price
(1030, 990, 1020 -- irrelevant) or a tiny BUY 1010 0.02 at t=4 (cum=0.02,
nowhere near 5.00). None of them complete the exit naturally.

cap_s=5, entry_ts=t1 -> forced-exit deadline = entry_ts + 5s = t=6. The
tape's ticker rows continue (unchanged, 1000/1010) through t=9, so at the
ticker row t=6 the cap check fires: the still-open long is force-closed
at exit_ts = deadline = t=6.

**Round-2 correction (the bug this tape's round-1 expected file baked
in):** a forced exit is a TAKER order that must CROSS the spread to
close out immediately -- it does not get the passive/favourable touch
the (now-cancelled) resting exit order was waiting at. For a LONG
(entered on the bid), closing means SELLING, and a taker sell crosses
into the BID, not the ask. So exit_price = touch["bid"] at the deadline
instant = 1000 (unchanged throughout the tape), NOT touch["ask"]=1010.

Round-1's expected file used exit_price=1010 (the ask, i.e. priced the
forced taker exit as if it were a passive maker sell earning the full
spread) -- that was the planted/discovered defect in
scripts/qa/maker_fill_ref.py's `check_caps`, confirmed by
docs/AUDIT_2026-09/QAM4_auditorB.md finding 1. It has been fixed in the
round-2 clean simulator (`exit_price=touch[side]` where `side` is the
position's own entry side, not `touch[opposite[side]]`).

Expected (round 2): long, entry 1000@t=1, exit 1000@t=6, forced=True,
net_bps = (1000-1000)/1000*1e4 = 0.0 (the forced exit earns nothing --
it crosses back to its own entry price, the worst case for a symmetric
book that never moved).
Touch is constant throughout, so entry mid (t=1) == mid at t=6
(entry_ts+5s) -> markout_5s_bps = 0.0 (unaffected by this fix; markout is
computed from mid, not from the exit fill price).
