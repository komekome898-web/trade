# Blind audit — packet QAM3 (maker fill model, known-answer tape)
Independent re-implementation. Script: scratchpad `audit_QAM3c.py` (+ `audit_QAM3c_var.py`, `diag.py`, `var2.py`
variants). No sealed answers, no generator, no other audit report opened.

## Method and denominator (question 1)

Data: `qa_known_answer_maker3_20260907/ticker_qa_maker3_tape.csv.gz` (200,747 quotes) and
`executions_qa_maker3_tape.csv.gz` (37,223 prints), 2026-08-03T00:00:00.802Z – 2026-08-07T23:59:52.570Z (5 days,
synthetic). Tick 10.0, own size 0.05, fee 0 (manifest); price ~100,000 → 1 tick = 1 bps, 5,000 JPY notional/side.
Fill engine as stated: on insertion queue-ahead = displayed size at that price; a resting bid is consumed by
executions at its price whose taker side is SELL (a resting ask by BUY takers); fill when cumulative consumption
− queue-ahead ≥ 0.05; cancel and re-join at the back of the new best when the touch moves. Side mapping verified
against the tape: at 00:00:02.883Z a BUY print of 0.0191515 at 100010 reduces `best_ask_size` by exactly 0.0191515,
so BUY takers consume asks and the quote row is post-trade (executions processed before the quote at equal ts).
The opposite mapping (taker label = own side) is degenerate here — it yields **n = 1** round trip. Positions =
completed entry fills, both sides quoted continuously. Exit = maker order on the opposite side at the touch under
the same rule; if unfilled at 300 s, taker exit at the touch (the only reading under which QA3-5 and QA3-6 are
non-vacuous; a literal "always taker at 300 s" makes forced = 100 %).

**Recomputed headline table (denominator in every row):**

| # | claim | claimed | recomputed | n (denominator) |
|---|---|---|---|---|
| QA3-1 | S1 net /round trip | −1.47 bps, t=−8.97 | **+0.745 bps, t=+15.45** (sd 2.397) | 2,471 completed S1 round trips, 5 days |
| QA3-2 | S1, naive first-print fill | +1.92 bps, t=217 | **+1.872 bps, t=383.0** | 31,412 round trips (same rule change) |
| QA3-3 | S2 net /round trip | −0.02 bps, t=−0.75 | **−0.354 bps, t=−4.52** | 775 completed S2 round trips |
| QA3-4 | S1 entry 5 s adverse selection | ≈0, n.s. | **−0.1378 bps, t=−16.11** | 2,471 entry fills |
| QA3-5 | S1 excl. forced exits | +2.08 bps | **+1.889 bps, t=+41.7** | 1,306 maker-exited round trips |
| QA3-6 | S1 forced-exit share | 23.8 % | **47.15 %** | 1,165 / 2,471 |

Specification sensitivity (S1 net, forced %): stated rule +0.745 / 47.2 %; exit pinned at the entry-moment opposite
touch +0.204 / 76.6 %; inventory limited to one position +0.825 / 46.2 %; pure taker exit at 300 s, no maker exit
leg −0.265 / 100 %. **No specification produces −1.47 bps with a 23.8 % forced share.**

## QA3-1

S1 net is **positive and significant**: +0.745 bps/round trip, t = +15.45, n = 2,471 (5 days, 494/day). The
claimed −1.47 bps is not merely outside the 10 % band, it is the opposite sign, and t reverses (+15.45 vs −8.97).
Every one of the five days is independently positive (+0.48 to +1.12 bps, t = 4.6…11.5), so this is not one
outlier session. Controls behave as they should: sign-reversed gives exactly −0.745 (t = −15.45); a random-entry
control at the touch with the identical exit rule gives +1.097 (t = 24.5, n = 2,471), i.e. the timing of the queue
fills *costs* about 0.35 bps relative to random entry — real adverse selection is present but is far smaller than
the half-spread earned. Shuffling the taker-side labels (placebo) collapses fills to n = 1,060 and the mean to
+0.244 (t = 3.11), confirming the result depends on the real side labels and not on an accounting artefact.
Removing 19:00–19:10 UTC changes nothing (n = 2,450, +0.739, t = 15.27). MDE at this n (sd 2.397, SE 0.0482) is
0.135 bps at 80 % power, so a true −1.47 bps would have been detected with |t| ≈ 30; this is not a power failure.
Money: +0.745 bps on 5,000 JPY notional = +0.372 JPY/round trip, ≈ +184 JPY/day at fee 0 (fee key: `config/
products.yaml` FX_BTC_JPY `taker_fee_pct = 0.0`, consistent with the packet's 0 bps; **not** `config/config.yaml
costs.taker_fee_pct: 0.15`, which `config/constants.yaml` marks as not applicable to this product).
Verdict: 結論変更

## QA3-2

The number reproduces: +1.872 bps vs claimed +1.92 (−2.5 %, inside the band). The t does not (383 vs 217; the
claim's n is unstated, mine is 31,412). But the conclusion does not follow from the number. Replacing the queue
rule with "the first print at your price and side fills you" multiplies fills by 12.7× (31,412 vs 2,471) and drives
the forced-exit share from 47.2 % to 0.01 % — the naive rule fills orders that never reach the front of the queue
and therefore exits every position at the far touch inside the cap. The +1.87 bps it prints is simply the round
number of the round-trip spread (modal spread 20 = 2 bps) minus a sliver, i.e. the mechanical spread capture of an
order book that can never miss. It is a property of the fill rule, not of the tape: the same tape and the same
population under the stated rule pays +0.745 bps, and under a pinned-exit specification +0.204 bps. A number that
survives only because queue position was deleted is not evidence of a tradable edge; it is the standard
queue-position illusion, and it would be the same number on a shuffled tape.
Verdict: 結論変更

## QA3-3

S2 (improve 1 tick inside when the spread ≥ 2 ticks, else quote at the touch) recomputes to **−0.354 bps,
t = −4.52, n = 775**, i.e. 17.7× the claimed magnitude and significantly negative rather than indistinguishable
from zero. MDE at this n (sd 2.177, SE 0.0782) is 0.219 bps, so the claimed −0.02 would indeed have been
undetectable — but the measured value is 4.5 SE below zero, well above the MDE, so "no significant difference from
0" is a statement the data contradicts, not one it fails to resolve. Mechanism: the tape's modal spread is 20
(2 ticks, 133,796 of 200,747 quotes; 88 % of quotes are ≥ 2 ticks), so S2 improves almost always, quoting into a
price with zero displayed queue-ahead, halving the spread it can capture while raising the forced-exit share to
77.6 %. The non-forced subset earns only +0.132 bps. Improving is a losing trade on this tape, not a neutral one.
Verdict: 結論変更

## QA3-4

Sign-adjusted mid change 5 s after an entry fill is **−0.1378 bps with t = −16.11 over 2,471 entry fills** —
adverse selection is present and one of the most significant quantities in the packet. The term structure is
monotone and consistently negative: −0.060 bps at 1 s (t = −11.1), −0.138 at 5 s (t = −16.1), −0.145 at 30 s
(t = −9.1), −0.161 at 60 s (t = −7.4), −0.172 at 300 s (t = −3.6). MDE at n = 2,471 (SE 0.00856) is 0.024 bps at
80 % power, so the measurement is 5.7× the MDE: the claim is not rescuable as a power problem. Note the direction
of the error is against the claim's own narrative — QA3-1 argues the strategy loses, which requires adverse
selection, while QA3-4 argues adverse selection is zero. The two cannot both hold. What the data shows is small
but unambiguous adverse selection (−0.14 bps) that is simply much smaller than the ~2 bps round-trip spread.
Verdict: 結論変更

## QA3-5

The number is inside the band: +1.889 bps vs claimed +2.08 (−9.2 %; a pinned-exit specification gives +2.093).
The conclusion is a selection artefact and is wrong. "Forced exit" is not an independent covariate — it is decided
by whether the position went the right way, so excluding it conditions on the outcome. The complementary subset is
not noise: forced exits are 47.15 % of the population and average −0.538 bps (t = −7.46). The correct expectation
is the mean over the whole population an operator is committed to at entry time, +0.745 bps; +1.889 is the mean of
the winners. The same construction applied to S2 turns −0.354 into +0.132, and applied to the pure-taker-exit
specification is undefined (100 % forced) — a statistic whose value depends on how many losers you are allowed to
delete is not an expected value.
Verdict: 結論変更

## QA3-6

Recomputed forced-exit share is **47.15 % (1,165 of 2,471)**, not 23.8 % — 98 % relative error, and the
substantive statement (about a quarter of positions run to the cap) fails; nearly half do. The variants bracket
the truth on the same side: pinned exit 76.6 %, inventory-limited 46.2 %, S2 77.6 %; only the naive fill rule of
QA3-2 gets below a quarter, and it gets to 0.01 %. There is no specification on this tape in which 23.8 % is a
neighbourhood of the answer.

**Arithmetic impossibility of the claim set (specification-independent).** QA3-1, QA3-5 and QA3-6 are asserted of
the same population, so −1.47 = 0.762 × 2.08 + 0.238 × X forces the forced-exit leg to average **X = −12.84 bps**.
A forced exit is a taker exit at the touch 300 s after entry, so its loss is bounded by the 300 s price move plus
the spread: the sign-adjusted 300 s mid move has mean −0.172, sd 2.37, 1st percentile −6.00 and **minimum −9.00
bps** on this tape, and the worst single round trip I observe is −9.99 bps. The most negative mean any 23.8 %
subset of my S1 P&L can take is **−2.56 bps**. −12.84 is unreachable on this tape under any fill model, so at
least one of the three claimed numbers is wrong independently of how the fills are simulated.
Verdict: 結論変更

## Data validity, regimes, contamination (questions 4, 6, 7, 8, 9)

Validity: 3 duplicate execution rows (id-distinct, identical ts/price/size/side); **117 crossed quote rows**
(ask − bid = −20) plus a 1-tick spread in 23,628 rows; largest quote gap 33.3 s; excluding 19:00–19:10 UTC moves S1
from +0.745/t15.45 to +0.739/t15.27. Regime: spread terciles degenerate because spread is discrete — narrow (≤ 20)
n = 1,899, +0.678, t = 12.4; wide (> 20) n = 572, +0.967, t = 9.51; both positive, so the sign is not a spread
artefact, and all 24 UTC hours are positive (+0.09 to +1.16). Consistency: all 5 days positive; the effect is a
level (spread capture) and was measured as a level. Definition side-effects: partial fills cancelled when the touch
moves are discarded, as the rule requires; counting them would add fills at worse queue position. Selection
contamination: free parameters are the 300 s cap, improve threshold and own size; the placebo (shuffled taker
sides) still returns +0.244 (t = 3.11), which is the scale a best-cell-under-the-null bound must clear — −1.47 bps
is nowhere in that null. No alternative explanation is needed for the claimed sign: it does not appear.
Falsification: *if the stated rule produced a negative S1 expectancy, the mean of 2,471 round trips would sit at or
below −0.135 bps (80 %-power MDE); it sits at +0.745, t = +15.45, and at +0.204 under the worst specification.*

## 前提の誤り

| premise | source in claim | what the data shows | direction of bias | other claims inheriting it |
|---|---|---|---|---|
| S1 maker quoting is net loss-making under queue-aware fills | QA3-1 | +0.745 bps, t=+15.45, positive on all 5 days and in both spread terciles | makes maker quoting look unviable when the tape says the half-spread dominates | any rejection resting on "maker edge disappears once queue position is modelled" |
| forced (cap) exits are a minority (23.8 %) | QA3-6 | 47.15 %; 76.6 % / 46.2 % / 77.6 % under other specifications | understates cap exposure, so understates the taker cost and holding risk of the design | QA3-1 and QA3-5, whose decomposition uses this weight |
| the three S1 figures (−1.47, +2.08, 23.8 %) describe one population | QA3-1/5/6 jointly | requires forced legs to average −12.84 bps; tape minimum round trip is −9.99, 300 s move minimum −9.00 | at least one figure is mis-transcribed or from a different run | any downstream ledger that sums these three |
| entry fills carry no measurable adverse selection | QA3-4 | −0.1378 bps at 5 s, t=−16.11; monotone −0.06→−0.17 bps out to 300 s | hides the one real cost the fill model does exist to measure | any claim that treats maker fills as information-free |
| excluding forced exits estimates the strategy's expectation | QA3-5 | conditions on outcome; the excluded 47 % average −0.538 bps (t=−7.46) | inflates expectancy by ~1.14 bps/round trip | every "excluding stopped-out trades" statistic elsewhere |
| improving 1 tick inside is expectation-neutral | QA3-3 | −0.354 bps, t=−4.52; 88 % of quotes trigger the improve branch, forced share 77.6 % | makes price improvement look free when it costs ~0.35 bps/round trip | any quoting-policy comparison that treats improve as a neutral variant |
| "executions on its side" is unambiguous | fill rule as stated | the taker-label reading yields n=1 round trip; only the book-consumption reading is usable, and it had to be inferred from a size-decrement check on the tape | a wrong reading silently changes n by 3 orders of magnitude | every claim in this packet |
| fee 0 both sides is the operative cost | manifest, all claims | matches `config/products.yaml` FX_BTC_JPY `taker_fee_pct=0.0`, but `config/constants.yaml` carries an unmeasured 2 bps/leg taker slippage assumption that the tape cannot see; `config/config.yaml costs.taker_fee_pct: 0.15` is stale for this product | zero-cost forced exits are optimistic in live terms; at 2 bps/leg slippage the 47 % forced share alone costs ~0.94 bps/round trip and flips S1 negative | every maker claim quoting a bps figure without a slippage term |
| the tape is clean | implicit in all claims | 117 crossed quotes, 3 duplicate prints, 33.3 s quote gaps | small; excluding the maintenance-hour analogue changes S1 by 0.006 bps | none material |

Files read: `docs/AUDIT_2026-09/PROTOCOL.md`; `backtest_data/qa_known_answer_maker3_20260907/manifest.md`,
`ticker_qa_maker3_tape.csv.gz`, `executions_qa_maker3_tape.csv.gz`; `config/config.yaml`, `config/constants.yaml`
(fee-constant grep only). `00_packets.md` has no QA3 rows. No forbidden file opened. Not committed.
