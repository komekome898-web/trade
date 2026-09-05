# Packet I — second (blind) audit

Files read: docs/AUDIT_2026-09/PROTOCOL.md; docs/AUDIT_2026-09/00_packets.md (rows `I`, `R22`, `PR5` only, via
grep); backtest_data/venue_survey_20260827/ (FINAL.txt, SCREEN.txt headers only; bf_fxbtc_book.jsonl.gz,
bf_fxbtc_trade.jsonl.gz, bf_fxbtc_trade2.jsonl.gz — full contents, own script); backtest_data/venue_survey_20260827/analyze_venues.py
(docstring + FEES/TICK/SLIP constant tables only, to source venue fee/tick constants — no analysis logic copied);
config/products.yaml; config/config.yaml. Own script: `audit_I2.py` (scratchpad, path per protocol).
No forbidden file was opened.

## R22

**Claim (verbatim from packet row):** "M2マチルダ現代化(8セル): 8セル全滅、56日次値すべて負(−516〜−7,141bps/日)". Packet I
names the sole data source as `backtest_data/venue_survey_20260827/`, and asks to reconstruct 8 cells
(N∈{1,4} × time-ladder{2} × gate{2}) and reproduce the sign of 56 daily values.

**Q1 Denominator.** 56 = 8 cells × 7 daily observations. The named directory contains exactly ONE continuous
recording: bf_fxbtc (bitFlyer FX_BTC_JPY) book n=7200, trades (trade+trade2, deduped by id) n=13,953, spanning
2026-08-27 07:48:09–11:48:07 UTC = 3.999h. No other `venue_survey_*` or date-stamped directory exists anywhere
under `backtest_data/` (checked: only this one). **There is no way to obtain 7 daily replicates, let alone 56
cell-day values, from the retained data** — only 1 replicate per cell (8 point estimates) is possible.

**Recompute attempted (own grid-MM implementation, see script header for full design):** grid levels at
best±(k-1)×trailing-60s-median-spread, N∈{1,4}; ladder = reprice every snapshot ("fast") vs every 30s ("slow");
gate = quote always vs quote only when trailing-60s realised vol ≤ session median; conservative "traded-through"
fill rule; cost = 0bps fee (products.yaml FX_BTC_JPY taker_fee_pct=0.0) + 2bps slippage (repo convention).

| cell (N/ladder/gate) | my daily_bps (single 4h window) | claimed range |
|---|---|---|
| 1/fast/open .. 4/slow/gated (8 cells) | **-2.6 to -2.9 bps** | -516 to -7,141 bps/day |
| sign | 8/8 negative | 8/8 negative (claimed) |

Sign matches (8/8 negative) but magnitude does not: even scaling my 4h figure to a 24h day (×6) gives only
≈ -16 to -17 bps/day, three orders of magnitude short of the claimed -516 (minimum) to -7,141 (maximum) bps/day.
No plausible re-scaling closes this gap.

**Q2 Controls.** Sign-reversed/placebo: shuffling trade aggressor side at random and rerunning cell
(N=1,fast,open) gives -3.0bps (1694 fills) vs the "real" -2.7bps (2130 fills) — **statistically indistinguishable**.
This means the negative result in my reconstruction is driven mainly by the fixed 2bps one-way cost assumption,
not by a demonstrated genuine adverse-selection/mean-reversion-failure mechanism. My sign match is therefore weak
evidence, not independent mechanistic confirmation.

**Q3 Translation.** Cost used: FEE=0bps (config/products.yaml: `FX_BTC_JPY taker_fee_pct: 0.0`) + SLIP=2bps
(this repo's stated half-spread+slippage convention). Note: `config/config.yaml` carries a SEPARATE, heavier
"paper fill model" cost (`costs.taker_fee_pct: 0.15`% = 15bps + `slippage_pct: 0.05`% = 5bps = 20bps total,
comment: "verify real account fee via check_api.py"). Which of these two the original 56-value study used is not
stated in the packet text; a 20bps-cost model would make the true edge threshold ~10x harder to clear than a
0bps-fee model, so this constant materially affects any bps→JPY translation and should be disclosed.

**Q4 Relative vs absolute (regime).** Within my single window, vol-gated cells were NOT less negative than
open-gate cells (differences of 0.1–0.3bps, within noise) — the gate did not visibly help, which is at least
consistent with (does not contradict) "8/8 still fail," but weakens any narrative that the gate module
specifically improves the strategy.

**Q5 Definition side-effects / Q7 selection contamination.** Cannot be assessed: reproducing whatever
multi-day/parameter search produced the original 56-value table requires data this snapshot does not contain.

**Q6 Data validity.** The single retained window itself is clean by my own check: 0 book gaps (verified from raw
timestamps, not trusted from FINAL.txt), and it does not straddle the bitFlyer 19:00–19:10 UTC maintenance
window (07:48–11:48 UTC). This says nothing about the missing 6 other days.

**Q8 Simplest alternative.** The placebo result above (Q2) IS the simplest alternative explanation for my own
reconstruction's sign: fixed transaction cost alone, not price dynamics, explains the sign I got.

**Q9 Consistency / Q10 Falsification+MDE.** No second day or independent instrument is available in the
retained data to cross-check sign/magnitude agreement, and with n=1 window per cell (not n=7 days), no
day-level variance or MDE can be computed for the "56 values" claim.

Verdict: 再計算不能

## PR5

**Claim (verbatim from packet row):** "PREREG_matilda_modern: M2 8セルフィージビリティ判定→棄却(R22)". PR5's
sole stated basis is R22.

Since R22's headline quantitative result (56 daily values, magnitude range -516 to -7,141 bps/day) could not be
recomputed — the retained snapshot supports only 1 of the needed 7 daily replicates per cell — PR5's reject
judgment cannot be independently verified either. What I CAN say: (a) my own from-scratch 8-cell reconstruction
on the one available window is also directionally negative in all 8 cells, so a "reject" outcome is not
implausible; (b) my controls (Q2 above) show that a negative result of similar sign is easy to obtain from cost
assumptions alone, so directional agreement here is weak corroboration, not confirmation that the reject
decision was correctly sized/derived from real 56-value evidence; (c) I cannot check whether PR5's registered
rejection threshold was cleared by a wide or a narrow margin, since the underlying value table is unavailable.

Verdict: 再計算不能

## 前提の誤り

- premise: the claim rests on a 7-day backtest yielding 56 daily samples (8 cells × 7 days) | source: packet I
  row text "56日次値" and R22 "56日次値すべて負" | what the data shows: `backtest_data/venue_survey_20260827/`
  contains exactly one continuous ~4.00h recording (2026-08-27 07:48–11:48 UTC UTC, bf_fxbtc n=7200 book /
  13,953 deduped trades) and no other dated `venue_survey_*`/similar directory exists under `backtest_data/` —
  only 1 of the needed 7 daily replicates per cell is retrievable | direction of bias: cannot be signed (this is
  a retention/traceability gap, not a proven numeric error), but it means the specific magnitude and the n used
  for PR5's reject decision are currently unauditable | other claims that would inherit this: any R-series or
  PR-series entry whose only retained evidence pointer is a single-date `backtest_data/*_survey_*/` snapshot
  while its text implies a multi-day/weekly backtest — each should be checked for whether the underlying daily
  candle/CSV files were archived separately from this intraday recording.
- premise: FX_BTC_JPY's fee is unambiguous for cost translation | source: my Q3 derivation, cross-checking
  `config/products.yaml` against `config/config.yaml` | what the data shows: two different stored fee
  assumptions — real product spec `taker_fee_pct: 0.0` (products.yaml) vs. a separate "paper fill model"
  `taker_fee_pct: 0.15`% + `slippage_pct: 0.05`% = 20bps total (config.yaml, explicitly flagged there as needing
  verification against the real account) | direction of bias: unknown which one the original 56-value study
  used; a 20bps model makes any positive edge ~10x harder to clear, so if R22 used the lighter 0bps+2bps model,
  the true case against M2 could be even stronger than stated, and vice versa | other claims that inherit this:
  any BTC-side cost/edge claim that quotes one fee number without naming its source (this applies to the whole
  C-series cost-model claims, not just I).
- premise: the "gate" component is expected to measurably reduce losses relative to no gate (implied by
  including it as one of the 3 design axes) | source: packet cell design "ゲート2" | what the data shows: in my
  reconstruction on the one available window, gated cells were not less negative than open-gate cells
  (difference ~0.1–0.3bps, within noise of the placebo control itself) | direction of bias: weakens any
  secondary narrative that the gate specifically helps, though it does not change the headline "8/8 fail" |
  other claims that inherit this: any claim crediting the gate module (rather than the core grid) for a
  partial improvement in the M2 family.
