# Hand derivation -- micro-tape (a): simple queue consumption to fill

Rule: own_size=0.05. Resting order at bid=1000, queue-ahead = raw displayed
bid size at insertion = 0.10 (ticker rows are constant 1000/1010, 0.10/0.50
throughout). Threshold to COMPLETE = queue_ahead + own_size = 0.15,
strictly exceeded (decision 7).

Executions on bid (SELL hits bid):
- t=1 SELL 0.05 -> cum=0.05 (<=0.15, no fill)
- t=2 SELL 0.05 -> cum=0.10 (<=0.15, no fill)
- t=3 SELL 0.10 -> cum=0.20 (>0.15) -> ENTRY COMPLETES at t=3, price=1000.

At t=3 the exit is created immediately on the ask side (decision 3) at the
current ask touch (1010), queue-ahead = last known ask displayed size =
0.50 (unchanged since t=0), threshold = 0.55.

Executions on ask (BUY hits ask):
- t=4 BUY 0.30 -> cum=0.30 (<=0.55, no fill)
- t=5 BUY 0.30 -> cum=0.60 (>0.55) -> EXIT COMPLETES at t=5, price=1010.

Round trip: long, entry 1000@t=3, exit 1010@t=5, forced=False.
net_bps = (1010-1000)/1000 * 1e4 = 100.0.
Touch never moves (1000/1010 constant for all 10 rows) so mid at t=3 and
t=8 (entry_ts+5s) are both 1005 -> markout_5s_bps = 0.0.
