# QAM3 blind audit (independent reproduction, second auditor)

Files read: `docs/AUDIT_2026-09/PROTOCOL.md`; data files
`backtest_data/qa_known_answer_maker3_20260907/{manifest.md,ticker_qa_maker3_tape.csv.gz,executions_qa_maker3_tape.csv.gz}`.
Did not open `docs/QA/*`, any packet row (QAM3 has none in `00_packets.md` — it is not
in the master table), any other `docs/AUDIT_2026-09/*` file, or any forbidden script.
Own script: scratchpad `audit_QAM3b.py` (own implementation, no scripts/qa code read).

## Method (my own, stated explicitly — this is the crux of every verdict below)
Merged the two streams in timestamp order. Each side (bid=resting BUY, ask=resting
BUY... resting SELL) keeps a queue-ahead size fixed at (re)join, accumulates same-price
opposite-taker-side execution volume, and fills once cumulative ≥ queue-ahead+0.05;
re-joins at the new touch (new queue-ahead = displayed size) whenever price or my own
fill changes it. Completed positions are built as event-driven FIFO pairing: each fill
either closes the oldest opposite open lot (maker exit, captures whatever the two prices
happen to be) or opens a new lot; a 300 s watchdog force-closes taker-side (at the touch)
before any later fill can pair with it. This is a faithful but not unique reading of the
prose — see 前提の誤り. n(ticker)=200,747, n(exec)=37,223, 5 days, no gaps/dupes (see Q6).

## Claimed vs recomputed
| claim | claimed | recomputed | n |
|---|---|---|---|
| QA3-1 | -1.47bps, t=-8.97 | **+0.972bps, t=+15.90** | 1758 |
| QA3-2 | +1.92bps, t=217 | +1.744bps, t=107.7 | 17282 |
| QA3-3 | -0.02bps, t=-0.75 | **+0.617bps, t=+11.22** | 1977 |
| QA3-4 | markout≈0, n.s. | +0.082bps (0.82 price-u), t=+10.96 | 2555 |
| QA3-5 | +2.08bps | +2.448bps | 796 |
| QA3-6 | 23.8% taker | **54.7%** taker | 1758 |

## QA3-1
1. Denominator: all S1 completed round trips over the 5-day tape, n=1758 (342–372/day, stable — Q9).
2. Controls: sign-shuffle placebo (200 draws) gives mean≈0.001bps, sd≈0.07bps — the observed
   +0.97bps is ~14 placebo-sd away, i.e. not noise under my model. Sign-reversed = -0.97bps.
   State-conditional (hour-of-day tercile) control: +1.18/+0.90/+0.86bps, same sign all three — level effect, not a regime artifact.
3. Translation: fee=0 per manifest (overrides live config's 0.15% taker — see 前提の誤り). 0.05 BTC @ ~100,000 JPY: 1bps/RT = 0.5 JPY. At the observed rate (~352 RT/day) ≈ +171 JPY/day, +0.97bps mean net — this is my sign, not the claim's.
4. Regime: positive in every day and every 8h bucket (Q9 data above) — a level effect, consistently signed, not a transient window.
5. Definition side-effect: FIFO pairing means a long that hasn't found its mirror-fill by the time a later long opens does not block that later long (inventory not capped at ±1) — this differs from an inventory-capped implementation and is a free choice I had to make (see 前提の誤り).
6. Data validity: no ticker gaps >60s (no synthetic maintenance window), 0 duplicate exec ids, 4541 duplicate ticker timestamps (near-simultaneous quote prints, harmless to the model). Result unaffected.
7. Selection: no free parameter swept for QA3-1 itself (rule fully specified); the FIFO-pairing convention is the only latitude and it is fixed once, not tuned to a target.
8. Alternative explanation: because ask>bid by definition, any maker–maker paired trip nets at least the realized (exit−entry) which is spread-shaped-positive unless price moves down/up against the position in the interim — my maker-only subset is indeed positive (+2.45bps, QA3-5), and my taker-only subset is only mildly negative (-0.25bps); the claim's implied taker-only figure would have to be much more negative (~-12.8bps, back-solved from its own QA3-1/QA3-5 numbers) to reach -1.47bps overall. That is a large, specific quantitative disagreement about how bad forced exits are, not just a rounding difference.
9. Consistency: same sign and similar magnitude across all 5 days independently (Q4 data) — internally consistent, but this is *my* model; I have no second independent dataset to cross-check the claim's exact pairing convention against.
10. Falsification: MDE at n=1758, sd=2.56bps, α=.05/80% power ≈ 0.17bps. Both -1.47 and my +0.97 are far above this MDE — the discrepancy is not a power problem, it is a genuine sign flip between two defensible implementations of the same prose.

Verdict: 結論変更

## QA3-2
1–2. Denominator: same S1 legs, alt "first qualifying print after (re)join fills unconditionally" rule → far more (and much faster) fills, n=17282. Placebo/sign-reversed not separately re-run (dominant sign is unambiguous at t=108).
3. Translation: +1.744bps × 0.5 JPY/bps/unit × ~3456 RT/day ≈ +3013 JPY/day nominal, again fee=0 per manifest.
4. Regime: not separately re-split (budget); QA3-1's flat-across-regime pattern makes a regime-driven artifact unlikely here too.
5–8. **This is the decisive point.** "Ignore queue-ahead, take the first print unconditionally" is not a fill model any real resting order can achieve — it fills you *ahead of* every unit of currently-displayed size at the touch, which is strictly better than what queue priority allows. It is a look-ahead/optimistic-fill artifact (Q8), not tradable liquidity. My number is close to the claim's (+1.744 vs +1.92, -9.2%, inside the 10% band) and the *sign* reproduces, but the claim's inference — "therefore a tradable edge exists" — does not follow, because the rule that produced the number describes fills that cannot be obtained in the real queue (this is exactly what QA3-1's queue-respecting rule is for, and it disagrees in sign).
9. Consistency: contradicts QA3-1 under the honest rule — that internal contradiction is itself the finding.
10. Falsification: the number is easily significant (t=108); the *inference* is what fails, not statistical power.

Verdict: 結論変更 (number inside the 10% band; conclusion "tradable edge exists" does not follow from an unrealizable fill assumption)

## QA3-3
1. Denominator: S2 (improve 1 tick inside when spread≥2 ticks, else touch), same queue fill rule as QA3-1, n=1977 completed round trips.
2. Sign-reversed = -0.617bps. Not separately placebo'd (budget); QA3-1's placebo scale (~0.07bps sd of means) makes t=11.2 far from a noise explanation here too.
3. Translation: +0.617bps × 0.5 JPY × ~395/day ≈ +122 JPY/day, fee=0 per manifest.
4. Regime: improve-quotes only trigger when spread≥2 ticks — this makes S2 itself a state-conditional strategy; not further split by hour (budget).
5. Definition side-effect: at an improved (non-touch) price I set queue-ahead=0 (no visible depth existed there before I joined) — this is a modeling choice the manifest does not resolve (touch-only sizes given), and it mechanically makes improve-quotes fill faster/first, likely raising my mean versus a stricter "somebody could already be there" assumption.
6. Data validity: same as QA3-1, no issue found.
7. Selection: none swept.
8. Alternative explanation: same maker-vs-taker decomposition as QA3-1 (taker_frac=48.8% here vs my 54.7% for S1) — again a milder, positive-leaning outcome under my convention.
9. Consistency: disagrees with the claim in both sign and significance, in the same direction as QA3-1's disagreement — consistent with a systematic convention difference rather than an S2-specific error.
10. MDE at n=1977 is well under 0.617bps; not a power issue.

Verdict: 結論変更

## QA3-4
1. Denominator: 2555 S1 entry fills (both legs), markout = direction-signed mid change at entry+5s, sign-flipped to read as "adverse selection" (positive = moved against the maker).
2. Sign-reversed = -0.082bps, trivially so.
3. Translation: 0.082bps × 0.5 JPY × 2555 entries/5d ≈ 21 JPY/day of adverse markout, fee=0.
4. Not regime-split (budget).
5. Definition: mid = (bid+ask)/2 from the ticker asof lookup; this mixes true informed flow with mechanical bid-ask bounce (Q8) — likely most of this effect.
6. No validity issues found beyond QA3-1's checks.
7. No parameter swept.
8. Alternative explanation: 0.82 price-units is under 1 tick; plausibly bid-ask bounce / quote-staleness rather than genuine informed order flow — economically negligible even though statistically non-zero at this n.
9. Consistent in sign with QA3-1's overall positive tilt (my convention systematically favors the maker slightly).
10. MDE at n=2555 is far below 0.082bps, so this is not a power failure — the claim's literal statement ("indistinguishable from zero") is rejected by my recompute, even though the magnitude is economically tiny.

Verdict: 結論変更 (statistically significant, though economically small — the claim's specific statistical statement does not hold under my recompute)

## QA3-5
1. Denominator: the 796/1758 (45.3%) of QA3-1's population that closed via maker fill before 300s.
2. This is by construction not a random subset (Q2 state-conditional): it excludes precisely the lots for which the market moved enough, or stayed too thin, for 300s — a survivorship exclusion.
3. Translation: +2.448bps × 0.5 JPY × ~159/day ≈ +195 JPY/day, fee=0.
4. n/a (this sub-figure is defined as one regime already — "not forced-exited").
5. **Definition side-effect is the whole claim.** Excluding the forced-exit lots removes the tail that is realized precisely when the position has been running against the maker for the full 300s (see QA3-1 Q8: the back-solved taker-only mean implied by the claim's own QA3-1/QA3-5 figures is ≈-12.8bps, i.e. very negative) — dropping them and calling the remainder "the correct expected value" is the standard survivorship error: a completed round trip that hits the cap is still a completed, realized trade of the strategy, not a data artifact.
6. No validity issue.
7. No parameter search.
8. Alternative explanation: this is exactly the mechanism, not an alternative to it.
9. Consistent with QA3-1: under my model the same subset shows the same qualitative pattern (maker-only positive, full-population smaller), even though my full population is net positive rather than negative.
10. Not a power question — a definitional one.

Verdict: 結論変更 (numbers are in the same ballpark — +2.45 vs +2.08bps, 17.7% off, single-sign — but "this is the correct expected-value estimate" does not follow: it is a post-hoc exclusion of the loss-carrying tail)

## QA3-6
1. Denominator: same 1758 S1 completed round trips as QA3-1; 962 closed by the 300s taker cap.
2. n/a (single proportion).
3. n/a.
4. Not split by regime (budget); day-level taker fraction not separately tabulated but QA3-1's per-day n and mean stability suggest no single-day driver.
5. This fraction is mechanically a function of the same FIFO-pairing convention flagged in QA3-1 — a stricter/looser convention on "does an opposite fill during the window always count as this lot's exit" changes it directly.
6. No data-validity issue found.
7. No parameter swept for this figure itself.
8. n/a.
9. Consistency: 54.7% (mine) vs 23.8% (claim) flips which side is the majority mechanism (taker-forced vs maker-natural) — this materially changes how QA3-5's exclusion should be read (excluding a majority of trades is a much larger and more suspicious cut than excluding a minority).
10. MDE at n=1758 for a proportion is a few percentage points at most — 54.7% vs 23.8% (30.9 pp apart) is far outside any plausible sampling/power explanation; this is a model-convention difference.

Verdict: 結論変更

## 前提の誤り
- premise: the stated fill/pairing rule fully determines "completed positions" | source: claim text (shared across QA3-1..6) | what the data/rebuild shows: the rule under-specifies (a) whether re-quoting after your own fill starts a queue-ahead of 0 or of the currently-displayed size, and (b) whether an opposite-side fill closes the *oldest* open lot (FIFO, inventory-shared) or is scoped per-entry independently; my one reasonable reading flips the sign of the population mean (QA3-1: +0.97 vs -1.47bps) and roughly doubles the taker-exit share (54.7% vs 23.8%) relative to the claim | direction of bias: unknown without the generator — could go either way | other claims inheriting this: QA3-1, QA3-3 (same pairing rule under S2), QA3-5 (its "true EV" argument depends on exactly which lots the pairing rule assigns to the forced-exit bucket), QA3-6 (the proportion itself).
- premise: fee = 0bps maker/taker (manifest) | source: QAM3 manifest.md | what the data shows: consistent with manifest, but this is far from the repository's real product cost (config/config.yaml costs.taker_fee_pct=0.15%, plus slippage_pct=0.05%) | direction of bias: any of these bps-scale synthetic edges (QA3-1 ±1–2bps, QA3-3 ±0.6bps) would be erased or reversed by the real taker cost floor if ever force-exited at 15bps+5bps taker cost | other claims inheriting this: QA3-1, QA3-3, QA3-5's "true EV" (a forced exit under real fees costs ~20bps, not ~0, which would make the excluded tail even more decisive against QA3-5's conclusion).
- premise: QA3-2's fill rule ("ignore queue-ahead") describes an achievable trading strategy | source: claim text ("したがって取引可能なエッジが存在する") | what the data shows: the rule fills strictly ahead of the full displayed queue at the touch, which no resting order can obtain in a real book | direction of bias: inflates the apparent edge into a materially wrong economic conclusion | other claims inheriting this: none else directly, but any future claim reusing this "first-print" convenience shortcut for a maker fill model should be treated the same way.
- premise: excluding forced-exit ("cap-out") trades yields the strategy's expected value | source: QA3-5 | what the data shows: forced exits are ~45–55% of completed trades under either convention (mine 54.7%, claim's 23.8%) — a non-trivial, systematically loss-leaning population, not a rare tail | direction of bias: overstates true EV | other claims inheriting this: none currently in this packet, but the same fallacy would infect any future "ex-cap-out" performance claim for a time-boxed strategy.
