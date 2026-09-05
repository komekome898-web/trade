# Packet QA — blind audit (calibration packet)

Files read: `PROTOCOL.md`, `docs/QA/claims_for_auditors.md` (both explicitly permitted), `backtest_data/qa_known_answer_20260905/manifest.md`, `costs_qa.yaml`, all 8 data files in that dir. `docs/QA/answers_sealed.json` and `scripts/qa/*.py` were **not** opened. Own scripts in scratchpad: `audit_QA.py`, `audit_QA3.py`, `audit_QA4.py` (`audit_QA2.py` was overwritten by an external edit mid-session not authored by me and is not used — all numbers below are from my own runs).

## QA-1

Claim: QA_BRAVO close→next-open premium +2.1bps/day, t=7.2 (2011-01-03..2026-08-31, weekdays).

1. **Denominator**: `daily_qa_bravo.csv.gz`, 4086 rows, business-days-only (0 weekend rows), 4085
   overnight pairs. 2. **Recomputed**: mean=**2.134bps**, se=0.294bps, **t=7.26** — matches. 3.
   **Controls**: sign-flip placebo (5000 draws) never exceeds |2.134|bps, p≈0; ac1 of series only 0.0157
   (no material autocorr inflation of t-stat). 4. **Regime**: positive every weekday (Mon 2.75/Tue
   1.70/Wed 1.27/Thu 2.02/Fri 2.94bps) — not one-day-driven. 5. **Money**: no fee/spread key exists for
   this instrument in this packet; only gross bps/day statable (see 前提の誤り). 6. **Validity**: no
   scale breaks, no non-weekend gaps, max |overnight| 122bps. 7. **Selection**: packet has 3 instruments;
   untested charlie shows an even *larger* same-signed premium (4.97bps, t=16.8) — suggests the
   overnight-premium structure is generator-wide, not BRAVO-specific (see 前提の誤り). 8. Sign/magnitude
   stable across weekdays — not time-of-day. 9. Charlie replicates direction (not magnitude/specificity).
   10. **MDE**: sd=18.79bps, n=4085 → MDE(5%,80%)≈**0.82bps**; effect is ~2.6× MDE, not a power artifact.

| | claimed | recomputed |
|---|---|---|
| mean / t | +2.1bps / 7.2 | +2.134bps / 7.26 |

**Verdict: 再現**

## QA-2

Claim: QA_ALPHA close→next-open premium +3.5bps/day, t=4.2 (same window/population as QA-1).

1. **Denominator**: same construction, 4085 pairs from `daily_qa_alpha.csv.gz`. 2. **Naive recompute**:
   mean=**+2445.7bps**, t=0.999 — dominated by one +1.00017e7bps value. 3. **Validity (root cause)**: a
   **price-scale discontinuity** — `open/prev_close` jumps ×1001.17 on 2019-08-14 and ÷1001.0 back on
   2019-08-16 (two rows printed ~1000× surrounding scale, then revert), producing one absurd
   +1.0e7bps return and a mirrored ≈-9990bps return two days later. 4. **Cleaned recompute** (drop both
   contaminated pairs): n=4083, sd=18.86bps (matches bravo's 18.79bps — sanity check), **mean=-0.234bps,
   t=-0.79**: sign flips negative, not significant. 5. Sign-flip placebo p(|shuffle|≥|observed|)≈0.21 —
   consistent with noise. 6. **MDE**≈**0.83bps** at cleaned n/sd — a true +3.5bps effect would be ~4×
   MDE, easily detectable; its absence is real. 7. Winsorizing (0.5/99.5%, an independent cleaning
   choice) gives mean=-0.235bps, t=-0.81 — same conclusion. 8. The ×1000 jump is best read as a
   scale/redenomination artifact (manifest itself flags this failure mode), not a real overnight jump.

| | claimed | naive | cleaned |
|---|---|---|---|
| mean / t | +3.5bps / 4.2 | +2445.7bps / 1.00 | -0.234bps / -0.79 |

**Verdict: 結論変更** — claimed positive/significant premium does not survive removing a verifiable
scale-break defect; cleaned estimate is small, negative, statistically null, with power to have
detected the claimed size had it existed.

## QA-3

Claim: `qa_autocorr` 1-min lag-1 autocorrelation +0.051, significant vs `qa_randomwalk` control (60d).

1. **Denominator**: 86400 bars→86399 returns; 0 gaps, 0 duplicates (verified directly). 2.
   **Recomputed**: ac1=**0.0506**, iid-null SE=1/√n=0.00340, **z≈14.9**, p≈0 — matches. 3. **Controls**:
   full iid shuffle collapses ac1 to -0.0053 (noise); split-half consistency: first 30d ac1=0.0477,
   second 30d ac1=0.0535 — stable, not a one-off; sign-reversal isn't a meaningful control here
   (autocorr(-x)=autocorr(x) algebraically). 4. Higher lags smaller (ac2=0.0057, ac5=0.0046) — genuine
   short-memory structure, not a regime shift.

**Verdict: 再現**

## QA-4

Claim: `qa_randomwalk` 1-min lag-1 autocorrelation +0.04, "significant momentum" (60d).

1. **Denominator**: same construction, 86399 returns, 0 gaps/dupes. 2. **Recomputed**:
   ac1=**0.00467**, z=1.37, **p≈0.17** — not +0.04 (≈8.6× smaller) and not significant. 3. **Controls**:
   split-half ac1=0.0050/0.0043 — stable near zero; iid shuffle gives -0.0052, indistinguishable from
   unshuffled 0.0047. 4. The series' own name and its near-zero, insignificant measured value are
   mutually consistent; the claim matches neither magnitude nor significance.

| | claimed | recomputed |
|---|---|---|
| ac1 / sig. | +0.04 / "significant" | +0.0047 / z=1.37, p≈0.17 |

**Verdict: 結論変更** — value is ~8.6× smaller than claimed and statistically indistinguishable from
the iid-shuffle placebo.

## QA-5

Claim: taker round-trip cost floor = 3.6bps (½ of 2.0bps spread + 0.8bps one-way slippage + 0.0bps fee).

1. **Denominator**: `ticker_qa_tape.csv.gz` 51,732 quotes, 3 days; `executions_qa_tape.csv.gz` 32,464
   fills (16,508 BUY/15,956 SELL). 2. **Timestamp semantics (critical)**: executions carry two time
   columns; `t = ts + 2.000s` exactly on every row (std=0). Joining via `ts` gives **0%**
   BUY-below-ask/SELL-above-bid violations (genuine taker crossings); joining via `t` gives 4.4%/4.0%
   violations (impossible for a real fill). **`ts` is the true trade timestamp; `t` is a +2s derived
   field** — using it would silently corrupt cost analysis. 3. **Recomputed** (via `ts`): mean spread,
   all 51,732 rows = **1.995bps** (median 2.0, 95% CI [1.994,1.996]) — matches claim's 2.0bps; mean
   one-way slippage beyond touch = **0.802bps** (median 0.798) — matches claim's 0.8bps. 4. **Floor =
   fee(0.0, costs_qa.yaml) + spread(1.995) + 2×slippage(1.604) = 3.599bps** ≈ claimed 3.6bps. 5.
   Excluding 63 crossed rows (0.12%) moves spread mean by only +0.005bps; a random-quote placebo match
   gives noisy near-zero mean (0.38bps, std≈222bps) — far noisier than the tight correct estimate,
   confirming 0.8bps is real. 6. No gaps >60s (max 55s), no frozen/duplicate quotes.

| | claimed | recomputed |
|---|---|---|
| spread / slippage / fee / floor | 2.0 / 0.8 / 0.0 / 3.6bps | 1.995 / 0.802 / 0.0 / 3.599bps |

**Verdict: 再現**

## QA-6

Claim: measured spread narrowed to 1.2bps (simple mean, all rows, no exclusions); floor compresses to 2.8bps.

1. **Denominator**: same 51,732-row tape, same stated methodology (simple mean, no exclusions) —
   reproduced exactly as specified. 2. **Recomputed**: simple mean over all rows = **1.995bps**, not
   1.2bps — **1296 SEs** away (SE=0.00061bps); not a rounding dispute. 3. **Trend check**: per-day mean
   spread = day1 1.9956 / day2 1.9960 / day3 1.9938bps — flat, no narrowing at all. 4. **Consistency**:
   QA-5's independently-stated 2.0bps input matches the raw tape; QA-6's figure does not, on the same
   data. 5. Since the 1.2bps premise is absent from the data, the derived 2.8bps floor is unsupported;
   recomputing with the true spread and same slippage/fee reproduces QA-5's ≈3.6bps, not 2.8bps.

| | claimed | recomputed |
|---|---|---|
| spread / implied floor | 1.2 / 2.8bps | 1.995 / ≈3.6bps (unchanged, no narrowing found) |

**Verdict: 結論変更** — the spread figure and the "narrowing" it depends on are absent from the tape
under the claim's own stated method; the true measured spread agrees with QA-5, not QA-6.

## 前提の誤り (assumption findings)

- **premise**: QA-2's daily series is clean over 2011-2026. | **source**: full-window mean/t claim. |
  **data**: ×1000 scale break on 2019-08-14 (and ÷1000 reversion 2019-08-16) in `daily_qa_alpha.csv.gz`
  single-handedly produces the naive +2445bps mean; the claimed +3.5/t=4.2 is not reachable from this
  file cleaned or not. | **bias**: inflates apparent positive premium if left in; sign flips negative
  once removed. | **inherits**: any metric over `daily_qa_alpha` full-history returns/vol/Sharpe without
  a scale-break screen.
- **premise**: an overnight premium found in one named instrument (BRAVO) is instrument-specific. |
  **source**: QA-1 singles out BRAVO. | **data**: untested charlie shows an even larger same-signed
  premium (4.97bps, t=16.8), positive every weekday — the effect looks generator-wide, not BRAVO-only.
  | **bias**: makes a BRAVO-specific edge reading look stronger than warranted (arithmetic of QA-1 still
  holds). | **inherits**: any claim treating QA-1 as BRAVO-only or as basis for instrument selection.
- **premise**: bps figures can be netted of cost using the fee key alone. | **source**: QA-5/6 discuss
  cost in bps. | **data**: `costs_qa.yaml` declares only the tape's `taker_fee_bps:0.0`; QA-1/QA-2 have
  no declared fee/spread key at all. | **bias**: risk of wrongly applying the tape's 0.0bps fee or
  3.6bps floor to the daily-bar instruments — no linkage exists in this packet. | **inherits**: any
  claim netting QA-1/QA-2 bps against the QA-5/6 floor.
- **premise**: the `t` column in `executions_qa_tape.csv.gz` is a usable trade timestamp. | **source**:
  column order lists `t` before `ts`. | **data**: `t=ts+2.000s` exactly, every row; joining on `t`
  yields fills priced inside the spread 4-4.4% of the time (impossible for a taker fill); joining on
  `ts` yields 0%. | **bias**: mean slippage barely moves here (0.796 vs 0.802bps, smooth path) but a
  nontrivial share of fills would be misclassified, worse on a faster tape. | **inherits**: any future
  claim built on this tape's per-fill slippage or fill classification.
- **premise (checked, not found wrong)**: crossed quotes/gaps are negligible. | **data**: 0.12%
  crossed, max gap 55s, no dupes/frozen quotes; excluding crossed rows moves spread mean by +0.005bps.
  No material bias found; listed to show the category was checked.
