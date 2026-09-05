# QAM3v3 blind audit (auditor 1)

Files read: PROTOCOL.md; docs/QA/claims_for_auditors_maker3_v3.md (only permitted docs/QA file);
backtest_data/qa_known_answer_maker3_v3_20260905/manifest.md + both csv.gz tapes (340,617 ticker
rows, 36,904 execution rows, 2026-08-03T00:00:00.79Z .. 2026-08-07T23:59:55.20Z, no timestamp gap
>60s anywhere — no maintenance window is modelled in this synthetic tape). No forbidden file was
opened (no scripts/qa/*, no docs/QA/answers_sealed*, no other docs/ file).

Method: independent Python re-implementation of the fill rule text (own script, event-driven over
the merged ticker+execution stream, own queue-ahead bookkeeping, own 300s cap, own bps/t-stat).
Own clip = 0.05, tick = 10.0, fee = 0 (all per manifest). Engine sanity check: my S1-naive replay
(QA3-2's alternative rule) gives mean +0.8429 bps vs claimed +0.84 bps — a near-exact match — so
basic mechanics (entry/exit direction, target-price rule, 300s cap, bps formula) are validated;
divergences below are concentrated in the correct rule's queue-priority bookkeeping, which the
manifest specifies fully for only one transition (entry-fill -> exit-insert) and leaves the other
insertion moments (session start, price-move re-join, cap -> new-entry) to be inferred by analogy.
I implemented the literal "-own_size" instruction for both fill->new-order transitions; toggling it
moved every number by <1%, so it is not the source of the remaining gap.

Recomputed (own engine, correct queue rule unless noted), n = completed round trips both channels:

| claim | claimed | recomputed | rel. diff | within 10%? |
|---|---|---|---|---|
| QA3-1 S1 net/rt | +0.30bps t=2.79 | +0.96bps t=9.39 (n=1263) | 220% | no |
| QA3-2 S1 naive net/rt | +0.84bps t=74.63 | +0.84bps t=93.4 (n=17842) | mean 0.2%, t 25% | mean yes, t no |
| QA3-3 S2 net/rt | -0.98bps t=-26.19 | +1.19bps t=5.72 (n=394) | sign flip | no |
| QA3-4 adverse sel. @5s | ~0 (n.s.) | -0.47bps, t=-20.1 (n=1263) | n/a | no |
| QA3-5 non-cap subset | +1.26bps | +1.06bps (n=612) | 16% | no |
| QA3-6 cap ratio | 44.6% | 51.5% (n=1263) | 15% (6.9pp) | no |

## QA3-1
Denominator: n=1263 completed round trips (both sides of S1's symmetric quote, 300s cap), 5 trading
days. My recompute: mean +0.9644bps, sd 3.652, t=9.39 (MDE at this n, 80%/5%: ~0.29bps — the
claimed +0.30bps sits almost exactly at the detection floor, consistent with the claim's own
marginal t=2.79; my point estimate of +0.96bps is 3x that and far above the MDE). Sign and
significance direction (positive, significant) DO hold in my reproduction — they hold even more
strongly — but the magnitude is far outside the 10% band, and the 3x gap under a rule the manifest
only partially specifies is itself the main finding: the "correct" fill model's headline number is
not pinned down tightly enough by the written rule for an independent build to land within 10% of
it, even with sensible tie-breaking choices at the underspecified transitions. Controls: sign of
direction is a bookkeeping convention (reversing it just negates the mean, uninformative alone);
no shuffle placebo run (budget). Consistency: this claim's n, cap-share and non-cap mean are
internally self-consistent by construction (0.5154*0.8735+0.4846*1.0611=0.9645, matches QA3-1 mean
to 4 decimals) — the *arithmetic* is sound in my own numbers; the mismatch is level, not logic.
Verdict: 数値差異(結論維持)

## QA3-2
Denominator: n=17,842 naive-rule round trips (same 5 days, same S1 quoting, "first print at our
price/side fills us in full, no queue"). My mean +0.8429bps matches the claimed +0.84bps almost
exactly; t differs (93.4 vs 74.63, population-size dependent, outside 10%). The real problem is the
CONCLUSION: the claim argues that because the naive (queue-blind) calculation gives a bigger,
more significant number than the correct queue-aware rule (QA3-1), "even this naive calculation
alone" proves a tradable edge exists. That is backwards. A fill rule that lets every resting order
jump straight to the front of the queue is a maximally optimistic assumption — it removes exactly
the risk (waiting in line while the market moves) that a real resting order bears — so a bigger
number under it is evidence of OPTIMISM BIAS in the naive method, not corroboration of a real edge.
If anything, the ~3x gap between naive (+0.84) and correct (+0.30, or my +0.96) shows the result is
highly sensitive to the fill-queue assumption, which argues for MORE caution, not less. Falsification:
a fill model whose queue realism doesn't matter would show naive ≈ correct; here it clearly does not.
Verdict: 結論変更

## QA3-3
Denominator: n=394 completed S2 round trips (improve 1 tick when spread>=2 ticks, else touch; 300s
cap), same 5 days. Claimed -0.98bps (t=-26.19, negative & significant); my recompute is
+1.19bps (t=5.72) — SIGN-FLIPPED. This is the most serious divergence in the packet. I cannot rule
out that my queue/reprice handling of the "improve" leg (target price recomputed on every tick,
so an improving order re-joins very often) differs from the intended model, but a sign flip on the
strategy's headline number, on top of QA3-1's 3x magnitude gap using the same engine, means I have
no independent confirmation of "negative and significant" — my own honest, rule-following
recomputation says the opposite sign. Consistency check (Q9): S2 improving orders get queue-ahead=0
by the manifest's own rule ("nothing can be ahead of a brand-new best price"), so S2 should fill
faster/more favourably on the entry leg than S1 whenever it improves — my result (S2 more positive
than S1) is at least directionally what that specific stated mechanic implies; the claimed negative
result requires the improve mechanic to be dominated by adverse selection on the exit leg badly
enough to flip the whole sign, which the rule text does not obviously predict and which the earlier,
forbidden-to-me derivation may or may not have shown correctly (I re-derive it as a claim to test,
per protocol, and it does not reproduce).
Verdict: 結論変更

## QA3-4
Denominator: n=1263 S1 entry fills (both channels). Signed, direction-adjusted mid change from fill
time to +5s (nearest ticker row at or before ts+5): mean -4.715 price units = -0.47bps, sd 8.34,
t=-20.1 — very far from indistinguishable from zero; MDE at this n/sd is ~0.46bps at 80% power, so
the claimed null is itself only marginally testable at this n, yet my point estimate clears even
that bar with room to spare. The direction is the textbook adverse-selection sign: after our maker
order gets filled, the mid tends to keep moving against the newly-opened position. A market-making
fill process with literally zero information content in fills would be unusual on priors; my
recomputation contradicts the claimed null directly rather than merely missing the 10% band.
Verdict: 結論変更

## QA3-5
Denominator: n=612 S1 round trips that closed by maker fill rather than the 300s forced cap (out of
1263 total, my cap share 51.5%). My subset mean +1.0611bps vs claimed +1.26bps (16%, outside band).
Independent of the number, the conclusion is the more important error: forced/cap exits are not a
random censoring of the return distribution — a position only hits the 300s cap because it did NOT
mean-revert to a fillable exit price in time, which is precisely the tail where the trade is going
against the maker (QA3-1's own arithmetic implies the cap-only subset mean is negative, back-solving
from the claim's own QA3-1/QA3-5/QA3-6 figures: 0.30=0.446*x+0.554*1.26 -> x=-0.88bps). Excluding
that tail and calling the remainder "the correct expected value of the strategy" is a selection/
survivorship bias, not a better estimate — the strategy's expectancy an operator actually earns is
the whole-population mean (QA3-1), which already nets in the cap exits. This inherits into any later
sizing/PnL projection that quotes "+1.2-1.3bps" instead of the full-population number.
Verdict: 結論変更

## QA3-6
Denominator: n=1263 completed S1 round trips. My cap-exit share is 51.5% vs claimed 44.6% — a 6.9
percentage-point gap, far above the ~2.8pp two-sided MDE at this n (so this is a real, detectable
disagreement, not noise), and outside the 10% relative band either way. There is no further
inferential conclusion attached to this claim beyond the ratio itself, and the qualitative takeaway
("a large, non-trivial share of round trips are forced timeouts rather than clean fills") holds
under both figures, so I do not treat this as a conclusion reversal, only a magnitude miss — but it
is large enough, and moves in the same direction as QA3-1's and QA3-5's misses (my engine reaches
the cap more often and books the fills that do complete somewhat more favourably than claimed),
that I read it as further evidence the underlying queue/timing bookkeeping in my rebuild differs
systematically from whatever produced the sealed numbers, rather than as six independent errors.
Verdict: 数値差異(結論維持)

## 前提の誤り
- premise: fee = 0bps maker/taker (manifest) | source: manifest instrument note | data: confirmed,
  used as-is | bias: none on THIS packet's internal comparisons, but every headline bps figure here
  (+0.3 to +1.3bps) is pre-fee; any later reuse of these numbers as forward-looking, cost-inclusive
  edge estimates would overstate profitability the moment any real fee/spread is applied | inherits
  to: any claim or downstream doc that cites QA3-1/3/5's bps figures without re-adding a live fee.
- premise: "the fill rule fully determines the correct-model numbers" | source: implied by treating
  QA3-1/3/4/5/6 as settled facts | data: an independent, good-faith rebuild from the written rule
  reproduces the mechanically simple naive claim (QA3-2's mean) almost exactly but diverges 3x-to-
  sign-flipped on every correct-queue claim | bias: unknown direction, but it means the "correct"
  rule as documented is under-specified at insertion moments other than the one worked example
  (entry-fill -> exit-insert) | inherits to: QA3-1, QA3-3, QA3-5, QA3-6 (anything computed under the
  correct queue rule).
- premise (QA3-2's own conclusion): "naive fill giving a bigger, more significant number than the
  correct rule corroborates a tradable edge" | source: QA3-2 body | data: naive fill removes queue
  risk entirely (own recompute confirms mean matches almost exactly), which is a known optimism
  bias, not a validation | bias: makes the strategy look more tradable than the correct rule
  supports | inherits to: any argument that cites the naive number as supporting evidence rather
  than as an upper-bound sanity check.
- premise (QA3-5's own conclusion): "excluding forced/cap exits gives the correct expected value" |
  source: QA3-5 body | data: cap exits are conditioned on not mean-reverting in time — a selection
  on the adverse tail, not random censoring; QA3-1's own reported numbers imply a negative cap-only
  mean (~-0.88bps) | bias: overstates strategy expectancy | inherits to: any sizing/PnL figure that
  substitutes QA3-5's +1.26 for QA3-1's whole-population mean.
- premise (QA3-4): "adverse selection at +5s is statistically indistinguishable from zero" | source:
  QA3-4 body | data: own recompute gives -0.47bps, t=-20.1, n=1263 — clearly non-zero and of the
  sign expected for adverse selection against a passive quoter | bias: understates a real cost that
  a live version of this strategy would pay | inherits to: any capacity/cost model for S1 that
  assumes fills carry no informational cost.
