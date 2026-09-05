# Hand derivation -- micro-tape (f): exit order queue-ahead at insertion

bid=1000 size=0.05 constant -> queue_ahead=0.05, threshold=0.10.
ask=1010, size=0.10 at t=0..1, then size CHANGES (price unchanged) to
0.40 from t=2 onward. This size-only change does NOT move the touch
price, so it does not cancel/rejoin the pre-existing ask-side entry order
that formed at t=0 with queue_ahead=0.10 (fixed at ITS insertion time,
decision 6) -- that stale order's queue_ahead stays 0.10 even though the
displayed size later grows to 0.40.

- t=3 SELL 1000 0.20 -> cum=0.20 (>0.10) -> bid ENTRY COMPLETES at t=3,
  price=1000.

Per decision 3, the exit is created AT THAT MOMENT (t=3) on the ask side,
using the CURRENT (last known, i.e. updated) displayed ask size = 0.40,
NOT the stale 0.10 the pre-existing ask entry order was using. So
queue_ahead(exit) = 0.40, threshold = 0.45. This evicts the stale
ask-entry order (which had made zero progress, so nothing is lost).

- t=4 BUY 1010 0.20 -> cum=0.20. Discriminating check: if the
  implementation wrongly reused the stale queue_ahead=0.10 (threshold
  0.15), this print (0.20>0.15) would incorrectly complete the exit here.
  Under the correct queue_ahead=0.40 (threshold 0.45), 0.20<=0.45, so the
  exit does NOT complete yet.
- t=5 BUY 1010 0.30 -> cum=0.50 (>0.45) -> EXIT COMPLETES at t=5,
  price=1010.

Expected: long, entry 1000@t=3, exit 1010@t=5, forced=False, net_bps=100.0.
Touch constant throughout -> markout_5s_bps = 0.0.
