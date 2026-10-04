You are an independent reviewer of a research design. Do not read any file in the repository; answer from this text only. No results exist yet.

Context: two trading strategies were improved using data up to 2023-12-17. The owner said (translated): "For strategies still being improved, the gate must be re-applied after the improvement is finished. Testing on the unseen period comes after that." The unseen period to be opened now is 2023-12-18 to 2025-12-11 (an exploration window; a later period 2025-12-12 to 2026-09-06 stays sealed for final judgment). On 2024-03-28 the exchange changed the product (from a futures-like product to a CFD with different fees and funding).

Forms to test (decided before opening, each a single fixed configuration):
- Strategy K (wick reversal, 15-minute bars): K-A = time exit after 6 bars, no gate; K-A+D = K-A but skip days whose previous-day volatility tercile was "low"; K-B = volatility gate (top third of the previous 365 days) plus time exit after 9 bars; K-B+D = K-B but skip "low" and "mid" days. K-A and K-B were each the best of 7 settings in the old data. The day rule came from the old data.
- Strategy M (range mean-reversion, 1-minute bars, limit orders): M-A = ratio gate from the previous 365 days plus take-profit measured from the range center (4:3). Fills inside a 1-minute bar are simulated under an optimistic and a pessimistic order assumption; in old data these two differed by about 120-165 bp/day.
- Baselines: the unimproved version of each strategy.

(Q1) Rank candidate observables by how directly they answer "does the improvement carry over to unseen data"; label direct / proxy / unrelated, one reason each: (a) per-day profit of each form vs its baseline, with 95% interval and minimum detectable effect; (b) the same split by product period (before / after 2024-03-28); (c) the effect of the day rule (K-A+D minus K-A, K-B+D minus K-B) with interval; (d) sign agreement with the old data's effect; (e) per-trade profit and trades per day; (f) year-by-year results; (g) M-A under optimistic vs pessimistic fills reported separately.
(Q2) Which covariates must be matched or reported (match / report / ignore): product period; fill assumption (for M); the number of settings the forms were selected from (multiplicity); calendar year; volatility level of the window vs the old data.
(Q3) Name one thing this design does not measure that could change the conclusion.
Answer in English, numbered, each reason under 20 words.
