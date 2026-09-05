# Hand derivation -- micro-tape (b): fill blocked by queue-ahead

Bid displayed size = 1.00 throughout, own_size=0.05 -> queue_ahead=1.00,
threshold=1.05 (must be strictly exceeded).

Executions on bid (SELL hits bid): 0.20+0.20+0.20+0.20+0.10 = 0.90 total
cumulative across t=1..5. 0.90 <= 1.05 at every step -> the resting bid
order NEVER reaches even a full partial fill of its own_size, let alone
completes. No entry ever completes, so no exit is ever created either
(ask side never gets past its own huge queue_ahead=1.00 either, and no
BUY executions exist in this tape at all).

Expected: zero completed positions (the still-open bid entry, sitting at
0.90 - 1.00(qa) = -0.10 filled i.e. still fully queued behind, is dropped
per "still open at end of tape" rule).
