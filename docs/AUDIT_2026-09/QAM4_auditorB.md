# QAM4 blind audit (auditor B) -- maker fill model, CODE-AS-CLAIM

Population for every number below: the synthetic v3 tape `qa_known_answer_maker3_v3_20260905/` --
340,617 ticker rows (330 crossed, skipped), 36,904 executions, 2026-08-03T00:00:00.787Z ..
2026-08-07T23:59:55.201Z (5 days), mid mean 101,028, mean spread 2.3335 bps (median 1.9922),
own_size 0.05, cap 300 s, tick 10.0. Fee used: **0 bps maker and taker** (manifest.md; consistent
with `config/products.yaml FX_BTC_JPY taker_fee_pct: 0.0`); carry `swap_daily_pct: 0.06` is
unmodelled (0.0160 bps/trip at the measured 231.1 s mean hold).

## Code review

`scripts/qa/maker_fill_ref_packet.py` vs the rule text in its docstring / in
`docs/QA/claims_for_auditors_maker4.md`, and vs its own `RULE_DECISIONS`.

**Contradictions (code disagrees with the text it claims to implement):**
1. **Forced exit does not cross.** Text: "forced exits at the 300 s cap **cross** exactly at the
   displayed public touch". `check_caps` sets `exit_price = touch[opposite[side]]` -- for a long
   (entered on the bid) that is the **ask**: the long is sold at the offer, while a taker sell hits
   the bid. `RULE_DECISION 9` ("touch price of the exit's side") encodes this, but the exit's side
   is the *resting* side, so the forced exit is priced as a maker fill and handed the full spread.
   Measured: forced trips earn **+1.2334 bps** vs **+1.0435** for genuine maker exits (n=507/414) --
   a forced taker exit out-earning a passive fill is the signature. Fixing only this line (exit at
   the entry side's touch): S1 **+1.1481 -> +0.0733 bps, t 9.05 -> 0.57**. It carries QA4-1, QA4-3.
2. **Queue-ahead ignores the "minus own size" clause.** Text: "queue-ahead = displayed size at
   insertion, **minus own size**, since [it] already includes our own just-joined clip" (the tape
   manifest repeats that the displayed sizes always include our clip). Code (`refresh`,
   `RULE_DECISION 6`) uses the raw displayed size. Effect on S1: n 921 -> 1070, forced share
   55.05% -> 46.07%, mean 1.1481 -> 1.1385 bps (t 9.05 -> 10.60).
3. **`>=` where the rule says "exceed".** `apply_execution` uses `if s.cum >= threshold`, while
   `RULE_DECISION 7` requires cumulative volume **strictly greater** than queue-ahead + own_size.
   The packet's own micro-tape **d** is built to detect exactly this and the code **fails it**.
   Immaterial for S1 (identical output), material for S2, where improved quotes have queue-ahead 0
   so the threshold is exactly own_size 0.05 and print sizes are quantized: S2 mean 0.7738 ->
   0.8637 bps, t 4.15 -> 4.72, n 361 -> 369.
4. **"or partially per FIFO"** is not implemented: a position is all-or-nothing at own_size, only
   cumulative progress toward one threshold (`RULE_DECISION 1` admits this).

**Decisions the code makes that neither the text nor RULE_DECISIONS state:**
5. `check_caps` fires only when the next event arrives: `exit_ts` is stamped at the exact deadline
   but `exit_price` is the touch at that *later* event, and a cap falling after the last tape event
   never fires -- the position is dropped. After a forced exit it clears `slot[exit_side]` without
   calling `refresh()`, so that side holds no order until the next ticker row (`complete()` does).
6. Exit queue-ahead and `entry_mid` come from the last ticker row *before* the filling execution
   (executions go first at equal timestamps), i.e. pre-trade, though the manifest defines ticker rows
   as post-trade: 0.1462 bps of the 0.6099 bps markout (24%, t=-13.67) is that asymmetry alone, and
   "displayed size at insertion" is stale by one row where it matters most.
7. Any `side` string not literally "SELL" is silently treated as a buy; `_entry_price` uses
   `round((ask-bid)/TICK) >= 2` so a 1.5-tick spread would count as improvable; `refresh` compares
   float prices with `==`. The column is named `net_bps` though no cost term is ever applied.

Micro-tapes (packet / my independent implementation vs `expected_*.json`; I derived a-h by hand from the text + RULE_DECISIONS before running any code):

| tape | a | b | c | d | e | f | g | h(naive) | h(true) |
|---|---|---|---|---|---|---|---|---|---|
| packet code | OK | OK | OK | **FAIL** | OK | OK | OK | OK | OK |
| my independent impl | OK | OK | OK | OK | OK | OK | OK | OK | OK |

Tape d: expected `entry_ts=00:00:04` (cum 0.16 > 0.15); the packet code completes at `00:00:03`
(cum 0.15 == threshold). My hand derivation agrees with `expected_d.json` -- text and decision 7
both say "exceed", so **the expected file is right and the code is wrong**; my implementation
reproduces all eight expected files exactly. Tape e's expected file itself enshrines the
non-crossing forced exit of item 1 (long entered 1000, "forced" exit 1010, +100 bps), so the
micro-tape suite cannot detect that defect by construction.

## QA4-1

S1, completed round trips, n=921 over 5 days (184.2/day; 495 long / 426 short).

| figure | claimed | packet code | my impl (rule text: crossing forced exit) |
|---|---|---|---|
| net bps/round trip | +1.15 | +1.1481 | +0.0733 |
| t | 9.05 | 9.05 | 0.57 |

Packet code reproduces the claim (0.2% off). Mixture identity holds: 0.5505x1.2334 +
0.4495x1.0435 = 1.1481. Money: 0.05 x 101,028 = 5,051 JPY/clip -> 0.58 JPY/trip, 107 JPY/day, ~39k
JPY/year at 0 bps fee, before 0.0160 bps/trip carry. Controls (all n=921): sign-reversed -1.1481
(t=-9.05); random-time mid-to-mid 300 s -0.0541 bps (t=-0.39, no drift in the tape); random-time
taker-in/taker-out 300 s -2.1770 bps (t=-15.40) ~ one spread. So +1.15 is spread capture, not
drift -- but 55.05% of trips capture it on the leg that should *pay* it; fixing only the forced-exit
side leaves +0.073 bps (t=0.57; MDE sd 3.94, 80% power ~0.36 bps). "Positive and significant" is an
artifact of an impossible fill price. By hour: [0,8) 0.872 (n=305, t=3.93), [8,16) 1.608 (n=310,
t=7.43), [16,24) 0.958 (n=306, t=4.37).
Verdict: 結論変更

## QA4-2

Naive (queue-blind) replay, same tape/strategy: claimed +0.84 bps, t=76.59; recomputed **+0.8418
bps, t=76.59, n=11,936** (packet code and my implementation identical) -- both numbers 再現. But the
claim's population statement is false: this is **not** "the same set of positions as S1" -- 11,936
vs 921 round trips (13.0x), 0.00% forced vs 55.05%. Comparing per-trip means across different
populations is not like-for-like, and the derived conclusion ("neither optimistic, and rather more
pessimistic than the true rule") fails on the economically meaningful axis: gross edge over the
same 5 days is 11,936 x 0.8418 = 10,048 bps naive vs 921 x 1.1481 = 1,057 bps -- **9.5x more
optimistic**. A lower mean per trip with 13x the trips is the classic queue-blind failure.
Verdict: 結論変更

## QA4-3

S2 (improve 1 tick when spread >= 2 ticks), completed round trips.

| figure | claimed | packet code (the declared claim) | my impl, strict ">" | my impl + crossing forced exit |
|---|---|---|---|---|
| n | -- | 369 | 361 | 361 |
| net bps | +0.77 | +0.8637 (+12.2%) | +0.7738 | -0.2493 |
| t | 4.15 | 4.72 (+13.7%) | 4.15 | -1.30 |

Two failures. (i) The claim's numbers are **not** produced by the code the packet declares to be
the claim: `>=` inflates the mean 12.2% and t 13.7%, both outside the 10% band, while my
implementation of the written rule reproduces 0.7738 / 4.15 -- so the claimed figures came from a
strictly-greater simulator and the shipped code is the defective one. (ii) With the forced exit
crossing, S2 is -0.2493 bps (t=-1.30, n=361, 53.19% forced). (i) leaves the conclusion, (ii) kills it.
Verdict: 結論変更

## QA4-4

S1 entry legs that completed a round trip, n=921. Claimed -0.61 bps (t=-21.36); recomputed
**-0.6099 bps, t=-21.36** -- exact; sign convention confirmed (positive = favorable). Alternative
explanation tested: 0.1462 bps (t=-13.67) is the pre/post-trade baseline asymmetry of code-review
item 6; rebasing on the post-trade mid at entry still gives -0.4637 bps (t=-16.82, same n). Same
sign and magnitude in S2 (-0.5337, t=-15.01, n=361) and the naive replay (-0.5458, t=-73.11,
n=11,936). Unlike QA4-1/3 it does not depend on the forced-exit price (fills unchanged). Caveat:
entries open at tape end are dropped, so the denominator is completers, not all entry fills
(immaterial at n=921).
Verdict: 再現

## QA4-5

Claimed 55.0% of completed S1 round trips are forced; recomputed **55.05% (507/921)** -- 再現 under
the packet code. Under the rule text's queue-ahead ("minus own size", item 2) the same tape gives
**46.07% (493/1070)**: 16% relative below the claim and no longer a majority (S2: 53.19%, 192/361).
So it reproduces only conditional on decision 6 overriding the written rule.
Verdict: 数値差異(結論維持)

## 前提の誤り

| premise | source in claim | what the data shows | bias direction | inherited by |
|---|---|---|---|---|
| forced 300 s exits "cross ... at the displayed public touch" | 約定規則, RULE_DECISION 9 | exit is priced at the *resting* side's touch; forced trips earn +1.2334 vs +1.0435 for real maker exits; crossing gives S1 +0.0733 (t=0.57), S2 -0.2493 (t=-1.30) | inflates every quoted net by ~ (forced share x spread) = 0.55 x 2.33 ~ 1.28 bps | QA4-1, QA4-3, and any claim quoting a cap-limited maker P&L; micro-tape e's expected file bakes it in |
| queue-ahead = displayed size **minus own size** | 約定規則 + manifest ("sizes ALWAYS include our own clip") | code uses raw displayed size (RULE_DECISION 6); raw -> n=921/55.05% forced, minus-own -> n=1070/46.07% | too few fills, forced share overstated by ~9 pts | QA4-1 (n, t), QA4-5 (the headline ratio) |
| completion requires volume to **exceed** queue-ahead+own | 約定規則, RULE_DECISION 7 | code uses `>=`; fails the packet's own micro-tape d; S2 +0.8637/t4.72 vs correct +0.7738/t4.15 | optimistic wherever queue-ahead is 0 (all improved quotes) | QA4-3; any S2/inside-quote claim |
| "母集団=S1と同じ建玉群" for the naive replay | QA4-2 | 11,936 vs 921 round trips, 0% vs 55.05% forced | makes a 9.5x more optimistic model look conservative | QA4-2 |
| `net_bps` is a net (after-cost) figure | "ネット" in QA4-1/2/3 | no fee, carry or slippage term exists in the code; fee is 0 bps on this tape (manifest, `products.yaml`), carry 0.0160 bps/trip unmodelled | negligible here (~1.4% of 1.15 bps), but the label is unearned | all net-bps claims |
| markout baseline = mid at the entry fill | QA4-4, RULE_DECISION 11 | baseline is the *pre*-trade mid while the +5 s mid is post-trade; 0.1462 of 0.6099 bps is that asymmetry | overstates adverse selection by 24%; conclusion survives (-0.4637, t=-16.82) | QA4-4 |
| "positions = completed entry fills" | 約定規則 | positions open at tape end, and caps expiring after the last event, are dropped silently | tiny at n=921; matters on short tapes | QA4-1, QA4-4, QA4-5 |

Files read: `docs/AUDIT_2026-09/PROTOCOL.md`; `docs/QA/claims_for_auditors_maker4.md`;
`scripts/qa/maker_fill_ref_packet.py`; `qa_known_answer_maker4_20260905/micro/*` (ticker/exec/
expected/HAND_DERIVATION a-h); `qa_known_answer_maker3_v3_20260905/` (manifest.md + both tapes);
`config/config.yaml`; `config/products.yaml`. No forbidden file opened (no sealed answers, no
tests, no other docs/QA file, no git history). Script: scratchpad `audit_QAM4_B.py`. Not committed.
