# QAM4R2 — blind audit (auditor B)

Packet QAM4R2 (CODE-AS-CLAIM, maker fill model, round 2). Method per PROTOCOL.md "Maker fill-model claims":
(a) code review, (b) micro-tapes hand-first, (c) full-tape re-run of the packet code, (d) own implementation.

**Headline: the packet's own reference code fails the packet's own known-answer test (micro-tape i) and does
NOT produce the numbers in claims 1, 3, 4, 5. An implementation faithful to the file's RULE_DECISIONS — which
the claims doc designates as 規則の確定版 — reproduces every claimed number exactly.** The claims' arithmetic
is right; the shipped artifact is wrong. (I also ran my implementation on the full tape, beyond PROTOCOL's
micro-tape-only role for it, solely to attribute the divergence; verdicts rest on that attribution.)

## Code review

Contradictions between `scripts/qa/maker_fill_ref_packet_r2.py` and the rule text / its own RULE_DECISIONS:

1. **DECISIVE — cumulative progress is carried across a cancel/rejoin.** In `refresh()`:
   `if cur is not None and cur.role == role: new_slot.cum = cur.cum`. The claims' rule text says
   "with cumulative progress reset to zero on rejoin"; RULE_DECISIONS 1 says "the new order starts at
   zero" and decision 8 repeats it. The code copies the old counter into the new slot while correctly
   taking the new queue-ahead, so a rejoined order fills on volume it never queued behind. Exposed by
   micro-tape (i) (entry at 00:00:03 instead of 00:00:05); on the full tape it is worth
   n=952→2052, +0.17→+0.73 bps, t=1.42→12.07, forced 46.6%→4.9% for S1.
2. **One shared slot per side contradicts the text.** RULE_DECISIONS 2 gives each side one slot and lets
   an exit evict a resting entry. The rule text says "at most one open position **per side** … a new
   entry quote on a side is placed only when that side has no open position" — under the text, a long
   (bid side) leaves the ask side free to keep quoting an entry. In the code the ask slot is taken by the
   long's exit, so **at most one position exists overall, ever**, never one per side. This roughly halves
   the population and serialises the two directions. Declared in RULE_DECISIONS, but not derivable from —
   and in conflict with — the prose the claims present as "上記の約定規則".
3. **Exit-only "minus own_size" is asymmetric and unsupported at the moment it is used.**
   `qa = max(0, disp[side] - own_size)` for `role=='exit'`, raw `disp` for entries. The justification
   (the displayed size already contains our just-joined clip) is a property of the *tape-generating* bot,
   not of the order being simulated: at the instant the exit qa is computed our exit order has not joined
   yet, and the last valid ticker predates its creation. Meanwhile the v3 manifest states displayed sizes
   "ALWAYS include our own resting clip while it is on the book", which if true would demand the same
   subtraction for entries. Both branches cannot be right on one tape.
4. **The micro-tape suite does not test finding 3 at all, and the hand answers disagree with themselves
   about it.** HAND_DERIVATION a/c/d/f compute the exit queue-ahead as the RAW displayed size
   (0.50 / 0.30 / 0.50 / 0.40); e/i subtract own_size (4.95 / 0.45). I re-ran both variants: on every one
   of the nine tapes the exit completes on the same print either way, so no expected_*.json discriminates
   them. The packet certifies neither branch of its most consequential contested decision.
5. **Stale docstring.** The module docstring still quotes the v3 clause "forced exits … cross EXACTLY at
   the displayed public touch at exit time", which is what round 1's defect implemented. The code and
   RULE_DECISIONS 9 follow the r2 text (cross into the position's own unfavourable side); the docstring
   was not updated and now contradicts the code it documents.

Decisions the code takes that no rule text states (each changes numbers):

6. Queue-ahead is frozen at insertion and never updated when the displayed size changes at the same price
   (`refresh` returns early on unchanged role+price). Micro-tape (f) depends on this and it is nowhere stated.
7. `check_caps` fires only at event timestamps and *before* the triggering row is applied: `exit_ts` is the
   exact deadline but `exit_price` is the touch from the last valid ticker at/before the triggering event,
   which can be stale relative to the deadline.
8. After a forced exit, `check_caps` nulls `slot[exit_side]` but never calls `refresh()`, so that side is
   unquoted until the next ticker row.
9. No cap sweep after the final event: a position whose deadline falls after the last tape row is dropped
   rather than force-closed (RULE_DECISIONS 13 covers only "cap not yet reached"). 1 S1 entry on the full tape.
10. `check_caps` still runs on a crossed ticker row that decision 5 says is "skipped entirely".
11. `_entry_price` under S2 with a spread of exactly 2 ticks puts BOTH sides' quotes at the same price
    (bid+tick == ask−tick); the text says nothing about this self-crossing case.
12. `markout_5s_bps` baselines on `entry_mid` captured from the **post-trade** ticker state at the fill
    instant, i.e. after the very print that filled us has moved the book — a definitional negative bias
    that is part of claim 4's −0.61 bps. RULE_DECISIONS 12 does not disclose this.
13. Naive mode is never forced-exited (0 of 11,936) because it always exits on the next opposite-side print;
    claim 2 compares populations that differ in exit mechanism, not only in fill threshold.

Micro-tapes: I derived all nine by hand before opening HAND_DERIVATION_*.md and agreed with every
expected_*.json. Packet code matches expected on a,b,c,d,e(cap=5 s),f,g,h(naive T and F); my independent
implementation matches on all nine. **Only tape (i) diverges: packet entry_ts 00:00:03 vs expected 00:00:05.**
Re-derived (i) by hand: bid qa 0.30→thr 0.35, cum 0.20 at t=1; touch moves 1000→1010 at t=2, new qa
0.10→thr 0.15, cum must restart at 0; 0.02 / 0.12 / 0.22 at t=3/4/5 → entry completes t=5. **The expected
file is right and the packet code is wrong**; the code reaches 0.22 at t=3 only by re-using pre-rejoin volume.

## QA4R2-1

Population: S1 completed round trips, 5-day synthetic tape 2026-08-03T00:00:00Z–2026-08-07T23:59:55Z
(340,617 ticker rows, 36,904 executions; no gaps or maintenance windows — synthetic), own_size 0.05,
cap 300 s, tick 10.0, fee 0 (manifest; consistent with `config/products.yaml FX_BTC_JPY.taker_fee_pct=0.0`
as recorded in `config/constants.yaml`). Rule-faithful re-run: n=952, mean net +0.1738 bps/round trip,
t=+1.42 (sd 3.78 bps, se 0.122). Claimed +0.17 / t 1.42 → exact. Mixture identity holds:
444/952 × (−0.892) + 508/952 × (+1.106) = +0.174 ✓ (forced legs lose, passive legs earn ~1 tick-share).
MDE at n=952, 80% power, α=0.05 two-sided ≈ 0.34 bps — an edge of ⅓ bp/round trip could not have been
detected, so "sign positive, not distinguishable from zero" is the correct reading, not a null result.
**Running the shipped packet code instead gives n=2052, +0.7327 bps, t=12.07 — which would flip the claim's
conclusion.** The claim's numbers, not the code's, follow the rule the claims doc declares definitive.
Verdict: 再現

## QA4R2-2

Population: naive (queue-blind) completed round trips on the same PUBLIC tape. Both the packet code and my
independent implementation give the identical answer here (the naive branch never touches the defective
`cum` carry): n=11,936, mean +0.8418 bps, t=+76.59. Claimed 11,936 / +0.84 / 76.59 → exact.
Sub-figures: population ratio 11,936/952 = 12.54× (claimed 12.5×) ✓; aggregate 5-day edge
10,048.3 bps vs 165.5 bps = **60.7×** (claimed ≈61×) ✓. Direction of the claim (queue-blind is optimistic,
not pessimistic or neutral) holds on both the per-round-trip mean and the aggregate. Caveat that belongs in
the claim: part of the 61× is that naive positions never reach the 300 s cap (0% forced vs 46.6%), so the
two populations differ in exit mechanism as well as fill threshold. Note also that the 61× ratio is computed
against the S1 aggregate the shipped code does **not** reproduce (its S1 sum gives 6.7×).
Verdict: 再現

## QA4R2-3

Population: S2 (improve 1 tick inside when spread ≥ 2 ticks, else at best) completed round trips, same tape.
Rule-faithful re-run: n=370, mean −0.1608 bps, t=−0.87 (se 0.185; MDE ≈ 0.52 bps at n=370). Claimed
−0.16 / t −0.87 / n 370 → exact, and the conclusion (negative sign, indistinguishable from zero) holds.
The shipped packet code gives n=620, **+0.4412 bps, t=+4.38 — the sign of the claim reverses.**
Verdict: 再現

## QA4R2-4

Population: entry legs of the S1 completed round trips, n=952. Markout at +5 s, sign-adjusted (positive =
favourable), mid from the last valid ticker at/before each timestamp. Re-run: mean −0.6146 bps, t=−21.93
(se 0.0280; MDE ≈ 0.08 bps, so this one is comfortably detectable). Claimed −0.61 / −21.93 → exact.
Definition side-effect: "エントリー約定 n=952" is really *entries that later completed a round trip* — I
counted exactly 1 entry fill still open at tape end, so the exclusion is immaterial here (952 of 953).
Larger caveat, from code finding 12: the baseline mid is the post-trade book at the fill instant, so a part
of the −0.61 bps is definitional rather than subsequent adverse drift. Packet code: −0.5368, t=−29.50, n=2052.
Verdict: 再現

## QA4R2-5

Population: S1 completed round trips, n=952. Forced (300 s cap, taker cross into the position's own side)
= 444 → 46.64%. Claimed 46.6% (444/952) → exact, and the count/rate identity checks out.
Forced exits average −0.892 bps vs +1.106 bps for passive exits, i.e. this 46.6% is where the strategy's
edge goes. Packet code: 100/2052 = 4.9%.
Verdict: 再現

## 前提の誤り

| premise | source in claim | what the data shows | direction of bias | inherits |
|---|---|---|---|---|
| The packet's reference code implements the stated rule | claims doc: "約定規則の実装は maker_fill_ref_packet_r2.py … RULE_DECISIONS が確定版" | The code contradicts RULE_DECISIONS 1/8 (cum carried across rejoin); fails micro-tape (i) | Optimistic: +0.17→+0.73 bps, t 1.42→12.07, S2 sign flips −0.16→+0.44, forced 46.6%→4.9% | every QAM4R2 claim, and any later claim generated with this file |
| "at most one open position per side" | rule text, all claims | Code allows at most one position overall (exit evicts the opposite side's entry quote, RULE_DECISIONS 2) | Halves n; serialises long/short; unknown sign on the mean | claims 1, 3, 4, 5 and any n-based power statement |
| Exit queue-ahead = displayed size − own_size (entries not adjusted) | rule text + v3 manifest; RULE_DECISIONS 6 | Justification is a property of the tape's generating bot, not of the simulated order; manifest's "always includes our clip" would require the same subtraction for entries | Exits fill slightly too easily and/or entries too rarely | any reused-tape maker claim |
| The micro-tapes verify the rule's decisions | packet framing ("each exercises one decision") | Decision 6 is untested — hand derivations a/c/d/f use raw size, e/i subtract own_size, and no tape's outcome discriminates | Overstates the known-answer test's coverage | the "known-answer test passed" gate in PROTOCOL |
| Forced exit costs nothing beyond the crossing ("no additional slippage") | rule text, claim 5 | The crossing itself is a full spread (1 tick ≈ 99 bps on this tape) and is what drives forced legs to −0.89 bps | Correctly modelled, but the phrasing hides that this is the dominant cost term | claim 1 |
| markout measures post-fill adverse drift | claim 4 | Baseline is the post-trade mid at the fill instant, so the filling print's own impact is inside the −0.61 bps | Overstates adverse selection | claim 4, any markout-based maker claim |
| Fee = 0 maker and taker | v3 manifest | Consistent with the repo constant for this product (`FX_BTC_JPY.taker_fee_pct = 0.0`); no error found, but the +0.17 bps S1 edge is smaller than any non-zero taker fee applied to 46.6% forced exits | Would turn claim 1 negative under a fee regime change | claim 1, claim 3 |

Data-validity check: synthetic tape, no maintenance-window or reconnect issues apply; 340,617 ticker rows
contain crossed rows, which both implementations skip identically (micro-tape g confirms); results above are
with that filter, and no duplicates or gaps were found affecting the counts.

Files read: `docs/AUDIT_2026-09/PROTOCOL.md`; `docs/QA/claims_for_auditors_maker4_r2.md`;
`scripts/qa/maker_fill_ref_packet_r2.py`;
`backtest_data/qa_known_answer_maker4_r2_20260905/micro/{ticker,exec,expected,HAND_DERIVATION}_{a..i}`;
`backtest_data/qa_known_answer_maker3_v3_20260905/{manifest.md, ticker_qa_maker3_v3_tape.csv.gz,
executions_qa_maker3_v3_tape.csv.gz}`; `config/{config,constants,products}.yaml` (grep for fee keys).
No forbidden file was opened. Script:
`/tmp/claude-0/-home-user-trade/fa7bf0d4-a5c4-55b7-991b-874b590e00a3/scratchpad/audit_QAM4R2_B.py`. Not committed.
