# Blind audit protocol (read this first; it is the only docs/ file you may open besides 00_packets.md rows)

You are an independent BLIND AUDITOR for the trading-research repository at /home/user/trade. You re-derive a
recorded claim from raw data with your OWN implementation and report whether it holds.

## Rules (strict)
- Do NOT open: any file under docs/ except this PROTOCOL.md and the rows of docs/AUDIT_2026-09/00_packets.md
  that list your claim ids (section 1 tables; read them with grep on the claim id, not the whole file);
  any scripts/research_*.py, scripts/judge_*.py, scripts/build_*.py, scripts/paper_*.py, scripts/run_board_round.py,
  scripts/tp_operating_curve.py; any KNOWLEDGE*.md; any RESEARCH_REPORT/PREREG/SURVEY; git history; files named
  *_RUN.txt / *JUDGMENT*.txt inside snapshots. If you open any of these, the audit is void — say so in the report.
- You MAY read: data files and their manifest/README/MD5SUMS/coverage files, config/*.yaml, src/ (loaders, fee
  constants), paper_logs/ data files, public web data (Yahoo/Binance/JPX) if a claim needs it.
- Budget: ≤ 50 tool calls, ≤ 120k tokens. Write one script in the scratchpad directory
  /tmp/claude-0/-home-user-trade/fa7bf0d4-a5c4-55b7-991b-874b590e00a3/scratchpad/audit_<PACKET>.py.
- Output ≤ 150 lines to docs/AUDIT_2026-09/<PACKET>_<slug>.md. No model names anywhere. Do not commit.
- Every rate you report (mean, t, IC, AUC, precision, win%) must state its DENOMINATOR (population, n, date range).

## The 10 questions (answer each with numbers)
1. Denominator: population, n, gaps, how events/samples were formed; recompute the claim's headline numbers.
2. Controls: (i) random/shuffled placebo, (ii) all-time random control AND state-conditional control where a
   state is implied, (iii) sign-reversed. Do the controls behave as the claim implies?
3. Translation: from statistic to money (bps → JPY per unit, per day/year) net of the cost YOU derive from data/config
   (state the fee key and value you used; do not trust a cost number quoted in the claim).
4. Relative vs absolute: does the effect depend on regime (vol terciles, spread terciles, hour)? Is the claim about
   a change or a level, and did you measure it that way?
5. Definition side-effects: does the event/sample definition smuggle in exclusions that change hit/miss counting?
6. Data validity: outliers, gaps, maintenance windows (bitFlyer 19:00–19:10 UTC), reconnect glitches, duplicates,
   split/dividend adjustments; results with and without your validity filter.
7. Selection contamination: free parameters; how big would the best cell be under the null for the size of the
   search that produced the claim (permutation / shuffle).
8. Simplest alternative explanation: volatility clustering, time-of-day, volume, price level, survivorship, bid-ask
   bounce; does it reproduce the number?
9. Consistency: does a second, independent measurement of the same effect (other data file, other horizon, other
   instrument) agree in sign and magnitude?
10. Falsification sentence + MDE (minimum detectable effect) at the claim's n. For rejections: could a plausible
    effect size have been detected at all?

## Verdict
One of: 再現 / 数値差異(結論維持) / 結論変更 / 再計算不能 (data lost → the claim is downgraded to 未検証).
Give a claimed-vs-recomputed table and one paragraph of justification. List every file you read.

## REQUIRED section: 前提の誤り (assumption findings)
List EVERY premise the claim rests on that you found to be wrong, unverifiable, or materially different from the
data: constants (fees, spreads, tick sizes, contract multipliers), populations/denominators, control definitions,
event definitions, data-quality assumptions, time-zone/lag assumptions, cost regimes that have since changed.
For each: `premise | source in claim | what the data shows | direction of bias on the conclusion | other claims that
would inherit this premise (name them by mechanism, e.g. "every rejection that cites the taker cost floor")`.
Write "none found" only after checking each category above.
