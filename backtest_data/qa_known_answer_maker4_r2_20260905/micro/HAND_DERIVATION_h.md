# Hand derivation -- micro-tape (h): naive fills on first print, true rule does not

bid=1000, size=1.00 (deliberately large) -> queue_ahead=1.00, own_size=0.05,
threshold=1.05.

naive=True (decision: ignore queue-ahead entirely, complete on the very
FIRST qualifying print regardless of its size):
- t=1 SELL 1000 0.10 -> first print at our price/side -> ENTRY COMPLETES
  IMMEDIATELY at t=1, price=1000, regardless of the tiny size (0.10).
  Exit created on ask side (ask=1010); naive mode applies uniformly to the
  exit too.
- t=2 BUY 1010 0.01 -> first qualifying print on the exit -> EXIT
  COMPLETES at t=2, price=1010, regardless of its tiny size.
Expected (naive=True): long, entry 1000@t=1, exit 1010@t=2, net_bps=100.0.

naive=False (true rule, queue-ahead respected):
- t=1 SELL 1000 0.10 -> cum=0.10 (<<1.05) -> no completion.
- t=5 SELL 1000 0.05 (the only other same-price/side print in this tape)
  -> cum=0.15 (still <<1.05) -> no completion.
The bid entry never gets remotely close to its threshold, so it never
completes; the exit is therefore never even created.
Expected (naive=False): zero completed positions.

This is exactly the QA3-2 phenomenon (docs/QA/claims_for_auditors_maker3_v3.md):
the naive, queue-blind rule reports a filled round trip where the correct,
queue-aware rule reports nothing at all.
