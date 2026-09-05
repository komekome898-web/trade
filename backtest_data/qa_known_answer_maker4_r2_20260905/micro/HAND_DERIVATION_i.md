# Hand derivation -- micro-tape (i): touch-move rejoin must RESET cumulative
# progress to zero (this is the round-2 planted-defect exposure tape)

own_size=0.05 throughout.

Entry order at bid=1000, displayed bid size=0.30 (entry order: no
minus-own) -> queue_ahead=0.30, threshold=0.35.
- t=1 SELL 1000 0.20 -> cum=0.20 (<=0.35, no fill; not even own_size
  worth has printed yet).

t=2: ticker row moves bid from 1000 to 1010 (ask stays 1020 throughout,
so this is a valid, uncrossed row). Per RULE_DECISIONS decision 1/8, this
is a touch-move: the resting order at 1000 is CANCELLED and a NEW order
joins at 1010, and **the new order starts at zero** -- the cum=0.20
progress made at the old price is forfeited. New displayed bid size at
1010 = 0.10 -> queue_ahead=0.10, threshold=0.10+0.05=0.15.

- t=3 SELL 1010 0.02 -> CORRECT (reset) cum=0.02 (<=0.15, no fill).
  A simulator that wrongly carried over the old cum=0.20 would compute
  cum=0.20+0.02=0.22, which EXCEEDS 0.15 -- and would erroneously
  complete the entry right here, one execution after the rejoin, having
  never actually seen 0.15 units of real post-rejoin volume.
- t=4 SELL 1010 0.10 -> correct cum=0.12 (<=0.15, still no fill).
- t=5 SELL 1010 0.10 -> correct cum=0.22 (>0.15) -> ENTRY COMPLETES at
  t=5, price=1010 (long).

Exit created at t=5 on ask side: ask=1020 (unchanged since t=0), raw
displayed ask size=0.5; EXIT order at the current touch, so
queue_ahead = 0.5 - own_size(0.05) = 0.45, threshold=0.50.
- t=6 BUY 1020 0.30 -> cum=0.30 (<=0.50, no fill).
- t=7 BUY 1020 0.30 -> cum=0.60 (>0.50) -> EXIT COMPLETES at t=7,
  price=1020.

Expected (CORRECT simulator): long, entry 1010@t=5, exit 1020@t=7,
forced=False, net_bps = (1020-1010)/1010*1e4 = 99.00990099009901.
Touch after t=2 is constant (1010/1020) through t=10+, so mid at entry
(t=5, mid=1015) equals mid at t=10 (entry_ts+5s) -> markout_5s_bps=0.0.

## Why this is the round-2 exposing tape

scripts/qa/maker_fill_ref_packet_r2.py's planted defect: on a touch-move
rejoin, `refresh()` builds a fresh `_Slot` (correctly using the NEW
queue_ahead for the new price) but then copies the OLD slot's `cum`
counter into it instead of leaving it at zero. Running both simulators on
this tape:

| | entry_ts | entry_price | exit_ts | exit_price | net_bps |
|---|---|---|---|---|---|
| clean (scripts/qa/maker_fill_ref.py) | 00:00:05 | 1010 | 00:00:07 | 1020 | 99.0099 |
| defective (scripts/qa/maker_fill_ref_packet_r2.py) | **00:00:03** | 1010 | 00:00:07 | 1020 | 99.0099 |

The defective copy carries the pre-rejoin cum=0.20 forward, so at t=3 its
cum is 0.20+0.02=0.22 > 0.15 and it completes the entry two prints (and
two seconds) too early -- "re-joined orders fill too early", exactly as
RULE_DECISIONS' own (correct) text says they must not: decision 1 states
"the new order starts at zero." The RULE_DECISIONS text in the defective
copy is unchanged and still states the correct rule; only the code
contradicts it.

Confirmed: none of micro-tapes (a)-(h) discriminate this defect (checked
by running both simulators on all nine tapes -- see
test_packet_r2_diverges_only_on_tape_i in tests/test_qa_maker_fill_ref.py);
tape (c), the packet's only other touch-move-rejoin tape, does not expose
it because its pre-rejoin cum (0.08) is too small to push either
simulator's completion earlier than the same execution print (both clean
and defective complete tape (c) at the same t=5 -- verified by running
both simulators on tape (c) unchanged from round 1).
