You are an independent reviewer of a research design. You will NOT see any results; none exist yet. Answer only from the purpose and the candidate lists. Do not read any file in the repository; answer from this text only.

For the unit below, answer:
(Q1) Rank the candidate observables by how directly they measure the stated purpose. For each, give one label: direct / proxy / unrelated, and one short reason.
(Q2) The comparison is "gated form minus ungated form, per day, same days". For each candidate covariate say match / report / ignore, with one short reason. Say whether comparing profit averaged over all days is fair when the gate sets the profit of excluded days to zero.
(Q3) Name one thing the design below does not measure that you would expect to change the conclusion, if any.

Answer in English, as a numbered list. Keep each reason under 20 words.

## Unit: intraday mean reversion (card 8), a previous-day volatility gate checked on another market
Strategy: every minute, hold short if the 1-minute close is above the running mean of today's closes (session = Tokyo calendar day), long if below; flat at the session's last minute. Fill at the next bar's open. No costs.
Where the gate came from: on bitFlyer FX_BTC_JPY 2017-2023, days whose previous day was calm (bottom third of previous-day mean absolute 1-minute log return, thirds cut on the previous calendar year) lost money in both halves of the period; days after a volatile day were positive in point but not significant.
Purpose (owner-approved, translated): "Measure the previous-day volatility gate on Binance BTCUSDT 1-minute bars 2018-01-01 to 2023-12-17 (data not used to find the gate). Gate form A = trade only after a volatile day (top third); gate form B = do not trade after a calm day (bottom third). Measure both." What this can show: whether the same mechanism appears on another market, not whether it works on bitFlyer.
Runs: one run of the ungated strategy on Binance; A and B are made by setting the daily profit of excluded days to zero. Classes use the same definition on Binance's own bars (Binance's 2017 has fewer than 300 days, so classification starts in 2019).
Candidate observables: (a) A minus ungated, per day, averaged over all classified days; (b) B minus ungated, same; (c) A's profit per traded day; (d) B's profit per traded day; (e) ungated profit per day on days after a calm day, by first and second half; (f) the same for middle and volatile days; (g) the sign of (a) and (b) under a midpoint fill (average of high and low) instead of the next open; (h) year-by-year sign of (a) and (b); (i) number of traded days per form.
Candidate covariates: fill assumption (next open vs midpoint); year; first vs second half; the market (Binance USDT spot vs bitFlyer JPY margin); number of traded days; positions carried across the session boundary when the last minute has no bar.
