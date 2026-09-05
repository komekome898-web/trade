# QAM blind audit (packet: QAM, known-answer maker-fill-model set)

Files read: `docs/AUDIT_2026-09/PROTOCOL.md`; `backtest_data/qa_known_answer_maker_20260905/manifest.md`;
`.../ticker_qa_maker_tape.csv.gz` (51,517 rows); `.../executions_qa_maker_tape.csv.gz` (32,247 rows).
Nothing else under `docs/` opened; `scripts/qa/*` and `docs/QA/answers_sealed_maker.json` NOT opened.
Script: scratchpad `audit_QAM2.py`. Tool calls used: 15/50.

**Method (applies to all 5 claims).** Entries sampled on a non-overlapping 300s grid over the full
3-day tape (863 grid points, 862 with a valid crossed-free two-sided quote at t0 — denominator for
every stat below unless stated otherwise). At each entry both a bid0 (=best_bid) and ask0 (=best_ask)
maker order (size 0.85, per manifest) are posted simultaneously ("対称的"). **Queue-correct fill**:
own order joins the back of the displayed queue (queue_ahead = best_bid_size0 / best_ask_size0 at
t0, or 0 when quoting inside the touch for QA-M3); it fills only once cumulative same-price,
opposite-taker-side execution volume exceeds queue_ahead, at OUR quoted price. Whichever side fills
first is the "entry"; the surviving order is then re-pegged to the then-current opposite touch as
the exit leg (re-running the same queue logic), capped at t0+300s total; if the exit never fills it
is forced closed at the cap by crossing the spread (fee = 0 both sides per manifest, so crossing
costs exactly the quoted spread at that instant, not an extra fee). This is the most literal reading
of "queue position based correct fill model" I could construct from best-of-book snapshots + a
timestamped print tape; I stress-tested it against a second variant (independent legs, static
counter-quote, no re-peg) and a "fresh 300s cap per leg" variant — all three cluster tightly
(see below), so the qualitative result is not an artifact of this particular round-trip mechanic.
Tick = 0.3bps of price (manifest). No fee anywhere (manifest: 0bps maker/taker) — translation to
JPY therefore reflects pure capture/adverse-selection, not a fee floor.

## QA-M1
Recomputed (queue-correct, re-pegged exit, n=862): **mean = -4.31bps/RT, sd=12.12, t=-10.44**.
Robustness: independent-leg/static-counter-quote variant -4.28bps (t=-10.09); fresh-cap-per-leg
variant -4.39bps (t=-10.53). All three land in -3.9..-4.4bps, t in -9.9..-10.5 — an order of
magnitude larger effect, and far more significant, than the claimed -0.84bps (t=-1.50).
Denominator: 862/863 valid grid windows, virtually none dropped as "no trade" (entry established in
862/862). Decomposition: ~23% of round trips never get a maker exit within cap and are forced to
cross (average loss on those ≈ -22bps); the maker-completed 77% alone average +1.2bps (matches
QA-M5 below) — the loss is concentrated in the legged/forced-close tail, not spread evenly.
Translation: notional per RT ≈ 0.85 × mid(≈1,000,000 synthetic JPY/unit) ≈ 850,000 JPY;
-4.31bps → ≈ -366 JPY/RT; at 288 attempts/day (continuous 300s cadence) ≈ -105,000 JPY/day —
economically large, not a rounding-level effect. Controls: sign-reversal mirrors exactly (sanity
only); shuffling which window's exit price attaches to which entry collapses the effect to
+14.5bps, t=1.55 (not significant) — i.e., the *pairing* of a specific entry with its own
subsequent exit carries the signal, so this is a real within-trip leg-risk effect, not a sample-wide
drift artifact. MDE at this n (SE≈0.41bps) ≈0.8bps — my effect is ~5x the MDE (highly powered
rejection); the claim's own reported SE (≈0.56bps from t=-1.50) implies a similarly sized sample,
so the discrepancy is in the point estimate, not the power.
Verdict: 数値差異(結論維持)

## QA-M2
"Naive, ignore queue position" was tested two ways. (a) Price-respecting naive: first print at our
exact quoted price fills us in full — mean = **-3.96bps, t=-9.90** (n=862), still strongly negative,
contradicting the claimed +0.3bps opportunity; ignoring queue depth alone (while still requiring the
print to reach our price) does not flip the sign here. (b) A more extreme "any print anywhere,
price irrelevant, instant fill" naive rule (both legs treated as filling on the very first
tick after t0, no wait) gives a deterministic **+1.80bps** (=the entry spread every time, sd=0,
forced-close rate 0%) — same sign as claimed but ~6x the claimed magnitude, and it requires
discarding price-level relevance entirely, not merely queue position. I could not reproduce +0.3bps
from "ignore queue position" as stated; reproducing a *positive* number at all required an
additional, unstated relaxation (zero latency + price-blind fills). The claim's causal attribution
("driven by ignoring queue position") is therefore not what makes the number positive in my
reimplementation — it is ignoring price-of-print and wait time that does it.
Verdict: 結論変更

## QA-M3
Recomputed (1-tick inside touch, queue-correct, own queue=0, n=862): **mean=-3.93bps, sd=11.14,
t=-10.37** (fresh-cap variant: -4.00bps, t=-10.39). Direction (negative, cost not cleared) agrees
with the claim, but the claim's own headline — "not significantly different from 0" (t=-0.89) — is
directly contradicted: my recompute rejects the zero-edge null with very high confidence at the
same n. Forced-close rate is lower than QA-M1 (20.2% vs 23.5%, consistent with faster fills at the
front of a fresh price level), but the smaller entry spread from improving 1 tick each side does not
compensate. This changes the decision-relevant conclusion from "can't tell, maybe neutral" to
"can affirmatively reject profitability."
Verdict: 結論変更

## QA-M4
Adverse selection measured as mid-move against the position, from the entry-fill timestamp, using
the queue-correct QA-M1 sample (n=862, denominator = every established entry, buy or sell pooled).
AS@5s: **mean=+1.48bps, t=16.9**; AS@60s: +2.59bps, t=9.0; AS@300s: +2.56bps, t=3.6. An all-time
random-time/random-side control (same n, no conditioning on a fill) gives AS@5s mean=-0.03bps,
t=-0.39 — i.e., unconditionally there is no drift, but *conditional on being the side that got
filled*, price keeps moving against the new position with overwhelming significance. This directly
falsifies premise (1) of the claim (AS@5s is emphatically NOT indistinguishable from 0 here). Premise
(2), the inference that "therefore queue-correct modeling should flip the round trip positive," is
independently falsified by QA-M1 above: modeling queue position correctly makes the net *more*
negative than the naive fill, not positive — the loss is dominated by legged trades riding the same
adverse drift for up to 300s before a forced cross, which a single 5s snapshot does not capture.
Verdict: 結論変更

## QA-M5
Restricting to the 659/862 (76.5%) round trips whose exit filled via maker (dropping every forced
cross) reproduces a positive number easily: raw capture (exit_price - entry_price convention) mean
= +1.19bps (sd=1.88, t=16.3); switching the reference to "mid at the ticker quote immediately
before each fill" (per-leg edge vs. contemporaneous mid, summed) pushes it further positive to
+3.20bps (t=24.5). Both reproduce the claimed direction and then some. But this is a textbook
double bias, not a real edge: (i) it survivorship-excludes precisely the ~23.5% of attempts that
QA-M1 shows carry the large adverse losses (-22bps average on the excluded group) — dropping the
losers before averaging; (ii) benchmarking each leg's price against the mid *at the moment that leg
prints* is close to tautological for a maker fill (a resting order almost always executes at a price
better than the mid prevailing at the instant it trades — that is the definition of providing
liquidity), so it manufactures a positive number regardless of what happens to the position between
legs. Excluding exactly the outcome you are trying to measure (whether the exit leg fills) and then
declaring the survivors profitable is not evidence the strategy is viable stand-alone.
Verdict: 結論変更

## 前提の誤り

| premise | source in claim | what the data shows | bias direction | claims that inherit it |
|---|---|---|---|---|
| "queue position based correct fill" alone accounts for the gap between M1 and M2 | QA-M1/M2 framing | queue-correct (-4.3bps) is *more* negative than a price-respecting naive fill (-4.0bps); only an additional price-blind, zero-latency assumption produces a positive number | overstates how much of the naive-model's optimism comes from queue depth specifically | QA-M2, and any future claim citing "ignore queue → false profit" as a single mechanism |
| AS at a fixed 5s horizon proxies the round trip's real risk | QA-M4 | AS is significant and *growing* from 5s (1.48bps) to 60s (2.59bps) to 300s (2.56bps); the round trip's loss is concentrated in the ~23% of trades that never close within the full 300s cap, not in the first 5s | makes the strategy look safer than it is by checking too short a horizon | QA-M4, and any maker round-trip claim that reports only a short-horizon AS check |
| a round trip's cost is well summarized by its average capture across all *completed* legs | QA-M5 | 76.5% of attempts complete via maker and average a small *positive* capture; the entire negative headline comes from the 23.5% that get legged and forced-closed — excluding them removes exactly the tail that decides viability | manufactures profitability by conditioning on the outcome being measured | QA-M5, and any "maker net" number computed only over maker-closed exits |
| the claimed -0.84bps/t=-1.50 (M1) and -0.43bps/t=-0.89 (M3) reflect the true magnitude/significance obtainable from this tape | QA-M1, QA-M3 | three independent round-trip mechanics all reproduce for me a 5-10x larger, far more significant effect (-3.9..-4.4bps, t≈-10) on the same tape and same 862-window denominator | the claimed numbers understate both the loss and its statistical certainty; a reader could wrongly treat this as a "close to breakeven, needs more data" result when it is not | any downstream judgement that treats M1/M3 as marginal/inconclusive rather than a clear rejection |
| fee/tick constants (0bps, 0.3bps tick) | manifest | confirmed as stated for this synthetic packet only — not bitFlyer's real fee schedule | none (synthetic, self-consistent) | any claim that imports this 0-fee assumption into a real-market context |

Overall: none of the five headline numbers reproduced within a small tolerance under my
implementation; direction agreed for M1/M3 (still negative) but magnitude/significance did not,
and M2/M4/M5's stated causal mechanisms and conclusions did not survive a queue-correct,
re-peg-aware recomputation with the specified size/tick constants.
