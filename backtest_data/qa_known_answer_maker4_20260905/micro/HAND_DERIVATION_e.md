# Hand derivation -- micro-tape (e): cap expiry -> forced exit at touch
# (simulate() called with cap_s=5)

bid=1000 size=0.05 -> queue_ahead=0.05, threshold=0.10.
- t=1 SELL 1000 0.20 -> cum=0.20 (>0.10) -> ENTRY COMPLETES at t=1,
  price=1000.

Exit created at t=1 on ask side: ask=1010, queue_ahead=last known ask
size=5.0 (deliberately huge so no realistic BUY volume in this tiny tape
can ever complete it), threshold=5.05.

Remaining executions (t=2..5) are all either at a different price
(1030, 990, 1020 -- irrelevant) or a tiny BUY 1010 0.02 at t=4 (cum=0.02,
nowhere near 5.05). None of them complete the exit naturally.

cap_s=5, entry_ts=t1 -> forced-exit deadline = entry_ts + 5s = t=6. The
tape's ticker rows continue (unchanged, 1000/1010) through t=9, so at the
ticker row t=6 the cap check fires (decision 9): the still-open long is
force-closed at exit_ts = deadline = t=6, exit_price = the ask touch
prevailing at that instant = 1010 (unchanged throughout the tape).

Expected: long, entry 1000@t=1, exit 1010@t=6, forced=True, net_bps=100.0.
Touch is constant throughout, so entry mid (t=1) == mid at t=6
(entry_ts+5s) -> markout_5s_bps = 0.0.
