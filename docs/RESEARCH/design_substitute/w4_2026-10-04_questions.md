You are an independent reviewer of a research design. You will NOT see any results. Answer only from the purpose and the candidate lists. Do not read any file under docs/RESEARCH or scripts; answer from this text only.

For each of the 6 units below, answer two questions:
(Q1) Rank the candidate observables by how directly they measure the stated purpose. For each, give one label: direct / proxy / unrelated, and one short reason.
(Q2) The comparison is "variant minus baseline, per day, same data". List which of the candidate covariates must be held equal or reported alongside (match / report / ignore), with one short reason each. In particular say whether comparing per-day profit is fair when the variant changes the number of trades per day.

Answer in English, as a numbered list per unit. Keep each reason under 20 words.

## Unit 1: range strategy (Matilda), combining two improvements
Purpose (owner's words, translated): "Optimize from both viewpoints: amplifying small wins, and avoiding big losses."
Candidate observables: (a) total profit per day; (b) sum of winning trades per day; (c) sum of trades losing more than 10 bp per day; (d) sum of profit of trades closed by a breakout per day; (e) number of trades per day; (f) win rate; (g) average win size; (h) interaction term = combined effect minus the sum of single effects.
Candidate covariates: number of trades per day; fill assumption inside a 1-minute bar (optimistic vs pessimistic); year; share of trades touching an ambiguous bar.

## Unit 2: range strategy (Matilda), reducing breakout losses directly
Purpose (owner's words, translated): "Reduce the losses at breakouts directly: close the losing position earlier / same / later; do not enter when the range is too wide relative to candle bodies."
Candidate observables: (a) sum of profit of trades closed at a breakout or by the new close rule, per day; (b) sum of trades losing more than 10 bp per day; (c) total profit per day; (d) number of trades per day; (e) sum of winning trades per day; (f) loss per breakout-closed trade.
Candidate covariates: number of trades per day; fill assumption inside a 1-minute bar; year; the threshold chosen from the same data (in-sample).

## Unit 3: wick-reversal strategy (Katsuo), why limit orders do worse than the bar-close reference
Purpose: "Split the gap between limit-order fills and the bar-close reference into the part due to entry and the part due to exit."
Candidate observables: (a) per-day profit difference for entry-only limit runs; (b) per-day profit difference for exit-only limit runs; (c) interaction term; (d) per-day difference in number of trades; (e) profit of reference trades that the limit version missed; (f) per-trade profit difference on trades present in both.
Candidate covariates: fill assumption inside a 1-minute bar; number of trades; bar length; entry style.

## Unit 4: wick-reversal strategy (Katsuo), exits for long holds
Purpose (owner-approved plan, translated): "The strategy earns on trades closed early and loses on trades held long. Try two exits for long holds: exit on price (k times volatility against entry) and exit on time (N bars)."
Candidate observables: (a) per-day profit difference vs no-exit; (b) per-day difference of winning sums and losing sums; (c) profit by holding-time band; (d) profit of trades closed by the new exit; (e) number of trades per day; (f) profit of trades re-entered after a price exit; (g) per-trade profit difference on trades present in both runs.
Candidate covariates: number of trades per day; year; bar length.

## Unit 5: wick-reversal strategy (Katsuo), volatility gate with a rolling threshold
Purpose (owner's words, translated): "The gate's threshold should not be a fixed value; re-measure with the threshold taken from the past year."
Candidate observables: (a) per-day profit difference gated minus ungated; (b) same, restricted to years not used to set any threshold; (c) number of trades per day; (d) per-trade profit difference; (e) year-by-year sign agreement; (f) profit of trades removed by the gate.
Candidate covariates: number of trades per day; year; volatility level of the year.

## Unit 6: data-handling difference between two simulators (cause investigation)
Purpose (owner's words, translated): "Investigate the cause based on how the data handling differs."
Candidate observables: (a) number of trades present in only one simulator, attributed to each handling difference; (b) yearly profit difference; (c) profit difference after switching one handling to match the other; (d) per-trade profit difference on common trades.
Candidate covariates: year; bar length.
