# Hand derivation -- micro-tape (g): crossed row skipped

t=0: bid=1000/0.05, ask=1010/0.10 (valid). Own bid entry: price=1000,
queue_ahead=0.05, threshold=0.10.

t=1: ticker row is CROSSED (bid=1015 >= ask=1005). Per decision 5 this
row must be skipped entirely: it must NOT move our resting order to 1015,
must NOT change queue_ahead, and the tracked touch state must remain
1000/1010 (last VALID state).

- t=1 SELL 1000 0.20 (same timestamp as the crossed ticker row; per
  decision 4 the execution is applied BEFORE the ticker row) -> cum=0.20
  (>0.10) -> ENTRY COMPLETES at t=1, price=1000. This is only possible if
  the crossed row was correctly ignored -- if a buggy implementation had
  already cancelled/rejoined the order to price 1015 before applying this
  execution, an execution AT PRICE 1000 would not match and this fill
  would not happen.

t=2: ticker row restores 1000/1010 (0.05/0.10) -- identical to the
pre-crossed state, confirming nothing was ever actually altered by the
crossed row.

Exit created at t=1 on ask side: price=1010 (last known valid, from t=0),
queue_ahead=0.10, threshold=0.15.
- t=3 BUY 1010 0.20 -> cum=0.20 (>0.15) -> EXIT COMPLETES at t=3,
  price=1010.

Expected: long, entry 1000@t=1, exit 1010@t=3, forced=False, net_bps=100.0.
Touch constant (ignoring the skipped crossed row) -> markout_5s_bps = 0.0.
