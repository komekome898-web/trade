# QAM3 blind audit (maker fill model, known-answer packet)

Files read: `docs/AUDIT_2026-09/PROTOCOL.md`; `docs/AUDIT_2026-09/00_packets.md` (grepped for "QAM3"/"maker3" —
no row found, packet not yet listed there, proceeded from the task's own claim text and data path per protocol
"data files and their manifest"); `backtest_data/qa_known_answer_maker3_20260907/manifest.md` + both `.csv.gz`
files. No file under `docs/QA/`, `scripts/qa/*`, `docs/AUDIT_2026-09/QAM3_*.md`, or `KNOWLEDGE*.md` was opened.
Own script: `scratchpad/audit_QAM3.py` (independent re-implementation, two structural variants — see QA3-1).

Data: 5 days (2026-08-03..08), 200,747 ticker rows, 37,223 executions. Tick=10, fee=0, own size=0.05 (from
manifest, matches claim). Validity check: 0 duplicate exec ids, no gaps >60s (no maintenance-window artifact —
data is synthetic per manifest), all prices exact multiples of 10; 185/200,747 (0.09%) ticker rows have
best_bid>=best_ask (crossed/locked touch) — a minor synthetic-data artifact, not filtered out below.

Model: continuous two-sided maker quoting, queue-priority fill (queue_ahead = displayed size at insertion,
fills once cumulative same-price executions exceed queue_ahead+own size, weighted-avg price over partials),
re-quote on touch-price change. Two position-pairing variants tested for robustness: (B) shared always-on
bid/ask resting orders, a position closes on the first opposite-side fill (flip-flop netting); (D) single
inventory {0,±1}, entry side suspended while in position, dedicated fresh exit order queued at position-open
time. Both variants tested because the shared "common fill rule" text under-specifies whether the closing
order inherits stale queue state or resets — see 前提の誤り.

## QA3-1
Claim: S1 (symmetric best-quote, 300s cap), net = -1.47bps/RT, t=-8.97.
Recomputed (variant B): n=1149, mean=+1.2374bps, t=17.17. Breakdown: natural closes n=642 mean=+2.4202bps;
forced/cap closes n=507 mean=-0.2602bps. By direction: long n=605 mean=+1.14bps; short n=544 mean=+1.35bps.
Robustness (variant D, single-inventory/dedicated exit): n=1051, mean=+1.2729bps, t=16.12 — same sign/order
of magnitude. Split-half consistency: first half n=573 mean=+1.33bps t=13.6; second half n=576 mean=+1.15bps
t=10.8 — sign stable across time and across both pairing conventions.
MDE at n=1149: se=0.072bps, ~0.20bps (2.8·se) — the claimed -1.47bps is >7x this MDE, so the disagreement is
not a power/small-n artifact; it is a genuine sign flip, robust to two reasonable fill/pairing implementations
and to a temporal split.
Verdict: 結論変更

## QA3-2
Claim: same population, "naive first-print-after-insertion = unconditional fill" rule, net=+1.92bps, t=217.
Recomputed: n=5437, mean=+2.2829bps, t=128.48, forced_frac=0.15% (queue-blind fills happen almost immediately,
long before any 300s cap). |2.28-1.92|/1.92=18.9% (outside the 10% band) but conclusion (ignoring queue
priority manufactures a large, highly significant positive edge out of the same tape that is flat/negative
under the queue-real rule) holds and is in fact the qualitative point of this claim (illustrating a naive-fill
bias). MDE≈0.05bps — no power issue.
Verdict: 数値差異(結論維持)

## QA3-3
Claim: S2 (improve 1 tick when spread≥2 ticks, else at-touch), same fill rule, net=-0.02bps, t=-0.75 (≈0).
Recomputed: n=1477, mean=+1.0642bps, t=19.40, forced_frac=25.5%. This is not a near-zero, insignificant number
— it is positive and highly significant, disagreeing in both sign and significance. MDE at n=1477 ≈0.15bps,
far smaller than the observed +1.06bps, so this is a real disagreement, not underpower on my side; conversely,
if the true effect really were ≈0 as claimed, my pipeline would have had ample power (se=0.055bps) to see that
and did not.
Verdict: 結論変更

## QA3-4
Claim: S1 entries only, sign-adjusted mid-move at +5s (adverse selection) is statistically indistinguishable
from zero.
Recomputed: n=1150 entries, mean_adverse=+0.083bps (positive = price moves against the new position, my sign
convention), t=7.11 (p≪0.001). MDE at this n ≈0.033bps, well below the observed 0.083bps — so this is a
real, detectable, if economically tiny, adverse-selection signal, not a null. The claim's literal statistical
assertion ("cannot be distinguished from zero") does not hold under my measurement, even though the magnitude
is small enough to be practically immaterial for sizing.
Verdict: 結論変更

## QA3-5
Claim: S1 completed positions excluding forced/cap exits, mean=+2.08bps, "the correct expected-value estimate"
of the strategy.
Recomputed: subset (natural closes only) n=642, mean=+2.4202bps, t=35.09. |2.42-2.08|/2.08=16.3%, just outside
the 10% band. But the substantive claim under audit is the second half of the sentence: that this conditional
mean is "the correct" unconditional expectancy estimate. It is not — forced/cap exits are the loss-making tail
in my recomputation (mean -0.26bps vs +2.42bps for natural closes, 44% of the population by count); dropping
them is conditioning on a mediator of the outcome (whether the market ran against the position hard enough to
still be open at 300s), a textbook survivorship/selection-bias construction, not a valid EV estimator for the
strategy as actually run. Per the boundary rule, a reproduced number with an unsound conclusion is 結論変更.
Verdict: 結論変更

## QA3-6
Claim: proportion of S1 completed positions that hit the 300s cap and exit as taker = 23.8%.
Recomputed (variant B): 507/1149 = 44.13% (95% CI 41.3%–47.0%, se=1.46pp). Robustness (variant D): 47.00%.
Both variants land far above the claimed figure and outside any plausible CI overlap (~20pp gap, ~14x the
binomial se). This directly undercuts QA3-1's and QA3-5's framing of forced exits as a minority tail.
Verdict: 結論変更

## Claimed vs recomputed (headline numbers)
| Claim | Claimed | Recomputed | Rel. diff | Verdict |
|---|---|---|---|---|
| QA3-1 | -1.47bps, t=-8.97 | +1.237bps, t=17.17 | sign flip | 結論変更 |
| QA3-2 | +1.92bps, t=217 | +2.283bps, t=128 | 18.9% | 数値差異(結論維持) |
| QA3-3 | -0.02bps, t=-0.75 | +1.064bps, t=19.40 | sign flip | 結論変更 |
| QA3-4 | ≈0, n.s. | +0.083bps, t=7.11 | n.s.→sig. | 結論変更 |
| QA3-5 | +2.08bps (="correct EV") | +2.420bps | 16.3%, bad inference | 結論変更 |
| QA3-6 | 23.8% forced | 44.1% forced | ~85% rel. | 結論変更 |

Overall packet class (worst sub-figure across the 6 claims): 結論変更.

Money translation (Q3): fee=0bps (manifest), tick=10 (price units), own size=0.05/leg. At the recomputed
QA3-1 mean (+1.237bps) on a notional of, say, 100,000 price units per side, expected pnl ≈ +1.237bps ×
100,000 × 0.05 ≈ ~0.62 price-units/round-trip before any real-world fee — i.e. this synthetic tape shows the
literal fill rule as stated produces a positive-EV maker strategy, not the claimed negative one; this is a
statement about the synthetic tape/rule combination only, not a real-market claim.

Controls (Q2): sign-shuffle placebo on QA3-1 trade bps gives mean≈-0.08bps (≈0, as expected for a placebo);
sign-reversed control trivially flips to -1.237bps/t=-17.17 (mechanical, not informative on its own). State-
conditional control (forced vs natural, above) is the most informative: it shows the two claimed-mixed
sub-populations have opposite sign, so the reported pooled mean is highly sensitive to their relative
weight — exactly where my recomputed weight (44%) disagrees sharply with the claimed weight (23.8%).

Consistency (Q9): QA3-1 sign/magnitude is stable across a first/second half split of the 5-day tape (+1.33 /
+1.15bps) and across two structurally different position-pairing implementations (+1.24 / +1.27bps) — the
disagreement with the claim is not a fragile artifact of one modeling choice.

Selection contamination (Q7): S1 and the fill rule have no tunable parameters; S2 has one (2-tick/1-tick
threshold) not swept here for budget reasons — flagged as unexamined, not as a finding.

## 前提の誤り

1. premise: S1's net expectancy under the stated queue-priority fill rule is negative (-1.47bps) | source:
   QA3-1 | data shows: robustly positive (+1.24 to +1.27bps across two pairing implementations and a time
   split) | bias direction: reverses the conclusion from "costly to run" to "profitable" | inherited by:
   QA3-5 (builds its "corrected" estimate on this same population) and QA3-6 (forced-ratio computed on this
   same population); any claim citing "S1 loses money by construction" as a baseline.

2. premise: forced/cap exits are a minority (~23.8%) of completed S1 positions | source: QA3-1, QA3-6 | data
   shows: ~44-47% under two implementations, i.e. roughly double | bias direction: understates how often the
   strategy is run over and forced to cross at cap; understates tail/model risk | inherited by: QA3-5's
   exclusion-based "correct EV" (excludes a far larger, and disproportionately loss-making, slice than assumed).

3. premise: the mean of completed positions after excluding forced/cap exits is a valid estimate of the
   strategy's true expected value | source: QA3-5 | data shows: forced exits are the loss-making tail (mean
   -0.26bps vs +2.42bps for natural closes in my recomputation) so excluding them is conditioning on the
   outcome (whether the position survived to be closed naturally), not a legitimate unconditional estimator |
   bias direction: overstates true expectancy | inherited by: any go/no-go reasoning elsewhere in this study
   family that estimates a maker strategy's edge by dropping its cap/stop-out exits (same exclude-the-tail
   mechanism).

4. premise: entry-fill adverse selection at +5s is statistically indistinguishable from zero | source: QA3-4 |
   data shows: small but statistically significant (t=7.11, n=1150) positive adverse-selection effect
   (~0.08bps) | bias direction: understates real information leakage immediately after a maker fill, though
   the economic size is small | inherited by: any claim in this family that treats S1 maker fills as
   information-free/exogenous.

5. premise (data quality, not in the claims but material to all of them): every ticker row has best_bid <
   best_ask | source: implicit in the fill-rule text ("best 気配") | data shows: 185/200,747 rows (0.09%) have
   best_bid ≥ best_ask (crossed/locked); not specially handled in this recomputation | bias direction: small,
   uncharacterized (affects a fraction of a percent of quote updates only) | inherited by: any claim in this
   packet, minimally.

6. premise: the common fill rule fully determines how a position's closing order inherits queue state |
   source: task's shared "fill rule" paragraph | data/finding: under-specified — I built two structurally
   different, individually reasonable resolutions (variant B, D) that agree with each other but both disagree
   with the claims, so this gap does not explain the QA3-1/3/6 mismatches, but it is a genuine spec gap worth
   closing before this packet is used to certify any real maker-fill engine | inherited by: QA3-1, QA3-3, QA3-6
   (anything whose headline number depends on exact position-close bookkeeping).
