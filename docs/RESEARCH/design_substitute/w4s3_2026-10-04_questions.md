You are an independent reviewer of a research design. Do not read any file in the repository; answer from this text only. You will not see results.

Purpose (owner's words, translated): "Looking at the table, it seems that by using how volatile the previous day was, we can clearly avoid trades that lose or barely gain. But for strategies still being improved, this must be re-applied after the improvement is finished."
Design: for each improved strategy form, split days into three classes by the previous day's volatility (terciles with thresholds from the previous calendar year; no look-ahead). Decision rule for a "gate": avoid a class if the upper end of the 95% interval of its mean daily profit is at or below zero.

(Q1) Rank these candidate observables by how directly they measure the purpose; label each direct / proxy / unrelated, one short reason each: (a) per-class mean daily profit with 95% interval; (b) high-minus-low difference with interval; (c) the gate's take (profit avoided per day) under the rule above; (d) minimum detectable effect per class; (e) per-class number of days; (f) per-class share of total profit; (g) the same split applied to the pre-improvement version.
(Q2) Is the decision rule ("upper end at or below zero") a fair translation of "avoid trades that lose or barely gain"? What would a fairer rule be, in one or two sentences?
(Q3) Which covariates must be matched or reported (match / report / ignore): fill assumption inside a 1-minute bar (optimistic vs pessimistic); calendar year; days without a class (first year); whether the class thresholds were chosen in-sample.
Answer in English, numbered, each reason under 20 words.
