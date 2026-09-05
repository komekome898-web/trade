# Hand derivation -- micro-tape (c): touch moves away -> cancel and re-join

t=0..1: bid=1000 (size 0.10), ask=1020 (size 0.30, constant throughout).
own_size=0.05.

Original bid-side entry: price=1000, queue_ahead=0.10, threshold=0.15.
- t=1 SELL 1000 0.08 -> cum=0.08 (<=0.10, not even a partial fill of our
  own_size yet).

t=2: ticker row changes bid from 1000 to 1010 (touch moved away). Per
decision 8, the resting order at 1000 is CANCELLED (its cum=0.08 progress
is forfeited) and a NEW order joins at the new touch 1010, queue_ahead =
displayed size there at that moment = 0.20, threshold=0.25, cum resets to
0.

- t=3 SELL 1000 0.50 -- this print is at the OLD, abandoned price (1000);
  our resting order is now at 1010, so this execution has no effect
  (confirms the cancelled order does not "come back to life").
- t=4 SELL 1010 0.10 -> cum=0.10 (<=0.25, no fill).
- t=5 SELL 1010 0.20 -> cum=0.30 (>0.25) -> ENTRY COMPLETES at t=5,
  price=1010.

Exit created at t=5 on ask side: price=1020 (unchanged touch), queue_ahead
= last known ask size = 0.30, threshold=0.35.
- t=6 BUY 1020 0.40 -> cum=0.40 (>0.35) -> EXIT COMPLETES at t=6,
  price=1020.

Round trip: long, entry 1010@t=5, exit 1020@t=6, forced=False.
net_bps = (1020-1010)/1010 * 1e4 = 10/1010*1e4 = 99.00990099...
Touch is constant (1010/1020) from t=5 onward through t=10+, so mid at
entry (1015) equals mid at t=10 (entry_ts+5s) -> markout_5s_bps = 0.0.
