# Hand derivation -- micro-tape (d): partial fill then completion
# (this tape is the one that EXPOSES the >= vs > planted defect)

bid=1000 size=0.10 constant, own_size=0.05 -> queue_ahead=0.10,
threshold=queue_ahead+own_size=0.15, and per decision 7 completion
requires cumulative execution volume to be STRICTLY GREATER than 0.15.

- t=1 SELL 1000 0.05 -> cum=0.05 (<=0.10, no partial fill of own_size yet)
- t=2 SELL 1000 0.05 -> cum=0.10 (==queue_ahead exactly, still 0 of our
  own_size filled, no completion -- this is a different boundary than the
  one being tested)
- t=3 SELL 1000 0.05 -> cum=0.15 -- EXACTLY EQUAL to the completion
  threshold (0.15). Per the LITERAL rule text ("... EXCEED queue-ahead +
  own size") this is NOT yet a completion under the correct (clean)
  simulator: 0.15 does not exceed 0.15. The planted defect (`>=` instead
  of `>` in scripts/qa/maker_fill_ref_packet.py) DOES complete here.
  -> CLEAN: no completion yet. DEFECTIVE: entry completes at t=3, price=1000.
- t=4 SELL 1000 0.01 -> cum=0.16 (>0.15) -- CLEAN: entry completes NOW, at
  t=4, price=1000 (same price, one execution later than the defective sim).
  DEFECTIVE: this execution has no resting bid order to match anymore
  (the bid slot was already freed and is blocked from re-entering because
  a position is open there), so it is ignored.

Ask side (exit) is identical for both simulators from here: ask=1010
size=0.50 constant -> queue_ahead=0.50, threshold=0.55, and the only BUY
execution is t=5 BUY 1010 0.60 -> cum=0.60 (>0.55) -> exit completes at
t=5 for BOTH simulators, price=1010.

CLEAN expected output: long, entry 1000@t=4, exit 1010@t=5, net_bps=100.0.
DEFECTIVE output: long, entry 1000@t=3 (one second earlier), exit
1010@t=5, net_bps=100.0 (same price, so only entry_ts differs).

This is exactly the discriminating case: the entry_ts field differs
between the clean and defective simulators on this tape and on no other
micro-tape in this packet (see test_maker_fill_ref.py
test_packet_copy_diverges_only_on_tape_d).
