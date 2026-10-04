You are an independent reviewer of a research design. You will NOT see any results; none exist yet. Answer only from the purpose and the candidate lists. Do not read any file in the repository; answer from this text only.

For each of the 2 units below, answer:
(Q1) Rank the candidate observables by how directly they measure the stated purpose. For each, give one label: direct / proxy / unrelated, and one short reason.
(Q2) The comparison is "variant minus baseline, per day, same data". For each candidate covariate say match / report / ignore, with one short reason. Say whether comparing per-day profit is fair when the variant changes the number of trades per day.
(Q3) Name one thing the design below does not measure that you would expect to change the conclusion, if any.

Answer in English, as a numbered list per unit. Keep each reason under 20 words.

## Unit A: wick-reversal strategy (Katsuo), second improvement round = combining the first-round improvements
Purpose (owner-approved plan, translated): "Combine the improved form (enter at bar close, 15-minute bars, exit on time after N bars, volatility gate with a threshold from the previous 365 days) into one and measure it. Also: N between 6 and 12; and the handling of minutes where the Japanese venue has no bar." Hypothesis to test: the time exit and the gate act on different trades (the time exit cuts long losing holds; the gate removes trades in calm conditions), so their effects add up when combined.
Runs: baseline (no exit, no gate); time exit only (N = 6..12); gate only; gate + time exit (N = 6..12); the same with an inner join that drops signal minutes where the Japanese venue has no bar (for N = 6 and 12 only).
Candidate observables: (a) per-day profit difference vs baseline for the combined form; (b) interaction = combined effect minus (time-only effect + gate-only effect); (c) per-day profit difference combined minus the better single improvement; (d) year-by-year sign agreement of the combined-vs-baseline difference; (e) profit by holding-time band, combined vs baseline; (f) number of trades per day; (g) per-trade profit difference; (h) the shape of the effect across N = 6..12 (neighbours of the best N); (i) the combined-vs-baseline difference under the inner join compared with the same difference without it.
Candidate covariates: number of trades per day; year; bar length; how missing Japanese-venue minutes are handled; the first year in which the 365-day gate has less than a full year of history.

## Unit B: range strategy (Matilda), second improvement round
Purpose (owner-approved plan, translated): "Stack the width-to-body ratio gate with the take-profit measured from the range center (4:3) and see whether they compete for the same big losses. Re-derive the ratio gate threshold using only the period before each point in time." Hypothesis to test: the ratio gate removes big losses at breakouts that the take-profit change does not touch, so stacking keeps both effects.
Runs (each under an optimistic and a pessimistic fill assumption inside a 1-minute bar): baseline v37; take-profit 4:3 only; fixed ratio gate (threshold chosen from the whole period, in-sample) only; fixed gate + take-profit 4:3; rolling gate (70th percentile of the previous 365 days) only; rolling gate + take-profit 4:3.
Candidate observables: (a) per-day total profit difference vs baseline; (b) per-day sum of trades losing more than 10 bp; (c) per-day sum of winning trades; (d) interaction = stacked effect minus the sum of single effects; (e) profit of trades closed at a breakout per day; (f) number of trades per day; (g) rolling-gate effect compared with the fixed-gate effect; (h) year-by-year sign agreement.
Candidate covariates: number of trades per day; fill assumption inside a 1-minute bar; year; whether the threshold was chosen in-sample; days on which the rolling gate had less than 180 days of history (gate off).
