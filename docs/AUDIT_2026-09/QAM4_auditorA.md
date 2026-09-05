# QAM4 — blind audit report (auditor A)

Files read: `docs/QA/claims_for_auditors_maker4.md`, `scripts/qa/maker_fill_ref_packet.py`,
`backtest_data/qa_known_answer_maker4_20260905/micro/*` (all 8 tapes + hand derivations +
expected json), `backtest_data/qa_known_answer_maker3_v3_20260905/{manifest.md, ticker_*.csv.gz,
executions_*.csv.gz}`. No other `docs/`, `scripts/qa/`, or `tests/` file opened. Script:
scratchpad `audit_QAM4_A.py` (ran the packet's own `simulate()` on all 8 micro-tapes + full v3
tape, plus an independent from-scratch re-implementation of the rule text on the 8 micro-tapes).

## Code review

**Confirmed defect — code contradicts its own `RULE_DECISIONS`.** Line 197:
`if s.cum >= threshold: complete(...)`. But `RULE_DECISIONS[6]` (the file's own stated resolution)
says completion requires cumulative volume to **strictly exceed** `queue_ahead+own_size`
("STRICTLY GREATER THAN ... NOT yet 'completed'"), matching the rule text's "exceed". The code
uses `>=`, not `>`. This is exactly the boundary micro-tape `d` is built to expose. Verified: the
packet's `simulate()` completes the entry on tape `d` at `t=3` (cum==0.15==threshold); both the
hand derivation and my independent strict-`>` re-implementation say the entry completes one print
later, at `t=4` (cum=0.16>0.15). This is not a hypothetical — it reproducibly diverges from the
sealed expected answer on tape `d` only (7/8 micro-tapes match exactly).

**Undocumented feature — `naive` mode is not in `RULE_DECISIONS` at all.** QA4-2 depends entirely
on `naive=True` (complete on the first qualifying same-price print, ignoring queue-ahead and size),
yet none of the 12 `RULE_DECISIONS` entries describe this branch or its semantics. It is only
documented in the micro-tape `h` hand-derivation, not in the file's own claimed decision list.

**Other places the code decides something the rule text/RULE_DECISIONS does not say:**
- `check_caps()` unconditionally discards (`slot[exit_side] = None`) any partial progress on a
  resting exit order when its position is forced-closed at the cap. Decision 9 only specifies the
  forced exit's own price/timing, not the fate of a competing in-progress exit order.
- After a cap-triggered forced exit frees a side (`position[side] = None`), `check_caps()` does
  **not** call `refresh()`. The freed side only gets a new entry slot on the *next* `apply_ticker`
  call. An execution at the exact same or an intervening timestamp on that side/price cannot fill
  a fresh entry until a ticker row arrives. Not stated anywhere.
- Float equality (`cur.price == price`) is used to decide whether a resting order is "the same"
  order across refreshes (decision 1/6 boundary); with tick-quantized prices this is safe here but
  is an implicit, unstated assumption.

Net: the code review finds one direct contradiction of the file's own rule (the `>=`/`>` defect)
and one entirely undocumented decision (naive mode) that a headline claim (QA4-2) rests on. Per
PROTOCOL.md, maker-fill claims stay **provisional** until the known-answer test passes cleanly;
it does not (7/8, tape `d` fails).

## QA4-1

S1, completed positions, net bps/round-trip. Denominator: n=921 completed round trips (full v3
tape, 340,617 ticker rows / 36,904 executions, 5 trading days).
Recomputed by running `simulate(strategy="S1", cap_s=300, own_size=0.05)` on the full tape:
mean=+1.1481 bps, t=9.05 (df=920). Claimed: +1.15 bps, t=9.05.
Relative diff on mean: 0.17%; t matches to 2 dp. Both inside the 10% band; conclusion (positive,
significant) holds.
Caveat: this number is produced by the code containing the `>=` defect above, so it is a faithful
reproduction of the *packet* (code-as-claim), not an independent confirmation that the *literal*
queue rule gives +1.15bps — the clean/strict-`>` rule was not run on the full tape (budget did not
allow a second full pass materially changing the verdict given the very close match already found,
and RULE_DECISIONS itself asks the auditor to treat only the micro-tapes as this generation's
correctness check for the fill-rule details).
Verdict: 再現

## QA4-2

Same S1 strategy, but replay with the naive (queue-ignorant) fill: population claimed as "S1と同じ
建玉群" (the same cohort as S1). Recomputed: naive n=**11,936** vs S1(true) n=**921** — a 13x
larger, categorically different set of round trips, not the same cohort re-scored. Headline stats:
mean=+0.8418 bps, t=76.59, vs claimed +0.84 bps, t=76.59 (diff <0.3%, t matches to 2dp) — inside
band, and the directional conclusion ("naive is pessimistic vs. the true rule here", 0.84<1.15)
holds numerically. The population-identity phrasing is false (see 前提の誤り); it does not change
the reproduced statistic or its sign, but it means the comparison is between two differently-sized,
differently-composed samples, not a matched-pair comparison.
Verdict: 再現

## QA4-3

S2 (spread≥2 ticks → improve 1 tick inside best, else at touch), completed positions.
Denominator: n=369 completed round trips (same tape/window as QA4-1).
Recomputed: mean=+0.8637 bps, t=4.72. Claimed: +0.77 bps, t=4.15.
Relative diff: mean 12.2%, t 13.7% — both **outside** the 10% band. Direction and significance
(positive, t>2) still hold, so the conclusion is not overturned, but the headline numbers are off
by more than tolerance.
Verdict: 数値差異(結論維持)

## QA4-4

S1 entries only, 5s markout, sign convention = positive means favorable-to-position.
Denominator: n=921 (same completed-position set as QA4-1; every completed round trip has exactly
one entry, per RULE_DECISIONS #12 — a position still open at tape-end is dropped in full,
entry included, so n cannot exceed the QA4-1 count and here equals it).
Recomputed: mean=-0.6099 bps, t=-21.36. Claimed: -0.61 bps, t=-21.36. Diff <0.02%, t exact match.
Adverse selection against the maker fill is confirmed, clearly distinguishable from zero.
Verdict: 再現

## QA4-5

S1 completed positions, share exiting via forced (300s cap) exit.
Denominator: n=921 completed positions; forced count=507.
Recomputed ratio: 507/921 = 55.05%. Claimed: 55.0%. Diff 0.09%.
Verdict: 再現

## 前提の誤り

- premise: the reference simulator implements the literal fill rule ("... EXCEED queue-ahead + own
  size") exactly, i.e. strict `>` | source: rule text + the file's own RULE_DECISIONS[6] | what the
  data shows: code uses `>=` (line 197); reproducibly diverges from the hand-derived/independently
  re-implemented correct answer on micro-tape `d` (entry completes one print early) | direction of
  bias: makes completions fire slightly earlier at the rare exact-equality boundary; net effect on
  the full tape appears small (QA4-1/4/5 reproduce within <0.2%) but is unaudited in magnitude
  beyond the 8 micro-tapes | inherited by: every claim run through `simulate(naive=False)` on the
  full tape — QA4-1, QA4-3, QA4-4, QA4-5 (not QA4-2, which uses `naive=True` and never touches this
  branch).
- premise: QA4-2's population is "the same cohort of positions as S1" (母集団=S1と同じ建玉群) |
  source: QA4-2 claim text | what the data shows: the naive replay produces n=11,936 completed
  round trips vs S1's n=921 — a completely different, ~13x larger sample, not the same trades
  scored under a different fill assumption | direction of bias: none on the sign/magnitude of the
  two bps numbers reported (both reproduce), but it invalidates any implicit "apples-to-apples,
  same-trades" reading of "true rule is more pessimistic per-trade than naive" — the two samples
  are not comparable trade-for-trade, only in aggregate | inherits: any other claim in this or
  future packets that describes a fill-rule-swap replay as "the same population/cohort".
- premise: the `naive` fill mode used by QA4-2 is part of the audited/declared rule set | source:
  RULE_DECISIONS (12 items) | what the data shows: `naive` is implemented in code but appears in
  none of the 12 RULE_DECISIONS entries, only in the micro-tape `h` hand derivation | direction of
  bias: none on the numbers (code review issue only) | inherits: any claim relying on `naive=True`
  semantics without a written decision to audit against.
- premise (implicit in "code-as-claim" framing): passing the known-answer test on all micro-tapes
  is a precondition already satisfied | source: PROTOCOL.md "Maker fill-model claims" | what the
  data shows: 7/8 micro-tapes match; tape `d` fails due to the `>=`/`>` defect above | direction of
  bias: keeps the whole packet at PROVISIONAL per the Standard configuration section, regardless of
  how closely full-tape numbers reproduce | inherits: QA4-1, QA4-3, QA4-4, QA4-5 (all run the
  defective completion branch).
