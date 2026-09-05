# Blind audit — packet QAM4R2 (maker fill model, round 2)

Files read: docs/AUDIT_2026-09/PROTOCOL.md; docs/QA/claims_for_auditors_maker4_r2.md;
scripts/qa/maker_fill_ref_packet_r2.py; backtest_data/qa_known_answer_maker4_r2_20260905/micro/
{HAND_DERIVATION,ticker,exec,expected}_{a..i}.*; backtest_data/qa_known_answer_maker3_v3_20260905/
{manifest.md, ticker_qa_maker3_v3_tape.csv.gz, executions_qa_maker3_v3_tape.csv.gz}. No forbidden
file opened.

## Code review

`maker_fill_ref_packet_r2.py`'s own RULE_DECISIONS list is a faithful, explicit resolution of every
ambiguity in the prose (partial-fill accumulation, shared per-side slot, exit-insertion timing/price,
same-timestamp tie-break, crossed-row skip, queue-ahead formula incl. the exit "minus own_size" case,
strict `>` completion boundary, uniform touch-move eviction, forced-exit **own-side** taker pricing,
naive mode, timestamp/markout conventions, open-at-end drop). None of these are hidden — each is
declared as text before the code that implements it. Two findings:

1. **Confirmed defect, contradicts the file's own decision 1.** `refresh()`'s touch-move-rejoin branch
   (`if cur is not None and cur.role == role: new_slot.cum = cur.cum`) carries the OLD slot's
   cumulative fill progress into the newly-joined order at the new price. RULE_DECISIONS decision 1
   says explicitly "the new order starts at zero," and the rule text in the claims doc says
   "cumulative progress reset to zero on rejoin." The code does the opposite of what its own adjacent
   comment and decision text say. Confirmed on micro-tape (i) (below) and shown to materially move
   every S1/S2 headline number on the full tape.
2. **Stale/contradictory module docstring.** Lines 1–20 describe "the v3 fill rule stated... in
   claims_for_auditors_maker3_v3.md" and say forced exits "cross EXACTLY at the displayed public touch
   at exit time" with no side specified — copied verbatim from the superseded v3 packet. This
   contradicts the file's own (correct) RULE_DECISIONS "Forced exit at the cap," which specifies the
   position's own **unfavourable** side. The actual code (`exit_price=touch[side]`, `side`=entry side)
   implements the RULE_DECISIONS version correctly (verified on tape e) — the docstring is just wrong/
   misleading documentation, not a behavioral bug.

## QA4R2-1 — S1 net, n=952

Denominator: completed S1 round trips (own_size=0.05, symmetric best-quote, 300s cap), 5-day public
tape. Micro-tapes a–h all match expected exactly (packet code and my independent re-implementation
agree with HAND_DERIVATION on every case except (i), see below — (i) does not affect the S1
population's *shape* for a-h). Running `simulate(strategy="S1")` from the packet file, unmodified, on
the full public tape gives **n=2052, mean=0.7327bps, t=12.07** — not n=952/0.17bps/t=1.42 as claimed.
My independent (rejoin-reset) re-implementation, run on the same tape, gives **n=952, mean=0.1738bps,
t=1.42**, exactly reproducing the claim. The defect (finding 1) inflates completions 2.16× and turns a
statistically indistinguishable-from-zero result into a highly significant one — this is not a rounding
difference, it is the opposite conclusion.
Verdict: 結論変更

## QA4R2-2 — naive vs S1, n=11,936 (naive)

Denominator: completed round trips under the naive (queue-ignoring) rule replayed on the same public
tape — a different population from S1 by construction (per the claim text itself). Naive mode never
touches `cum`/`queue_ahead` (`if naive: complete(...); return`), so it is immune to finding 1. Packet
code on the full tape: **n=11936, mean=0.8418bps, t=76.59** — matches the claim exactly. The claim's own
n=952 (12.5× naive/S1) is off relative to the code's actual S1 n=2052 (11936/2052=5.8×), and the "≈61×
aggregate edge" figure is computed against the claimed n=952, not the code's actual 2052-row output —
but taken on its own terms (naive population only) this sub-figure reproduces.
Verdict: 再現

## QA4R2-3 — S2 net, n=370

Denominator: completed S2 round trips (spread≥2tick → 1-tick improve, else best-quote), same tape.
Packet code as shipped: **n=620, mean=+0.4412bps, t=4.38** — positive and significant. My
rejoin-reset re-implementation: **n=370, mean=-0.1608bps, t=-0.87** — exactly the claim (negative,
not significant). The defect flips both the sign and the significance verdict here, worse than
QA4R2-1's case.
Verdict: 結論変更

## QA4R2-4 — S1 entry markout_5s, n=952

Denominator: S1 entry fills only (n=952 per claim). Packet code on the actual (defective, n=2052)
S1 population: markout n=2052, mean=-0.5368bps, t=-29.50. My rejoin-reset re-implementation on the
correct n=952 population: mean=-0.6146bps, t=-21.93 — exact match to the claim. Sign and significance
(adverse, p≪.01) agree between the buggy code's output and the claim, but n differs by >100% and mean
by ~14% relative — both outside the 10% reproduction band, conclusion (adverse selection, significant)
still holds.
Verdict: 数値差異(結論維持)

## QA4R2-5 — forced-exit fraction, 46.6% (444/952)

Denominator: S1 completed round trips, n=952 (claim's own count). Packet code as shipped: forced
100/2052 = **4.9%**. My rejoin-reset re-implementation: forced 46.6% exactly (444/952). This is the
starkest divergence: the shipped code says the vast majority of S1 round trips fill passively before
the 300s cap; the correct rule says under half do and the rest are taken-exit at the cap — opposite
qualitative pictures of how the strategy actually behaves.
Verdict: 結論変更

## Micro-tape summary (all 9, own re-implementation vs packet code vs expected)

a,b,c,d,e,f,g,h: packet code == my independent build == expected JSON, exactly, on every field
(entry/exit ts & price, forced, net_bps, markout_5s_bps; (h) checked in both naive=True/False).
(i) (the round-2 planted-defect tape, touch-move rejoin with prior partial progress): expected/my
build = entry_ts 00:00:05; packet code = entry_ts **00:00:03** (two prints early), all other fields
identical — this is exactly finding 1, and it is the only tape among the nine that discriminates it
(consistent with HAND_DERIVATION_i.md's own note that a–h and even tape c's smaller pre-rejoin cum do
not expose it).

## Overall verdict: 結論変更

(worst of the five sub-claims: 結論変更 for QA4R2-1, -3, -5; 再現 for -2; 数値差異(結論維持) for -4).
The packet instructs auditors to treat `maker_fill_ref_packet_r2.py` itself as the claim and to run it
to reproduce the headline numbers; running it, unmodified, on the full tape reproduces only the
naive-mode claim. The other four numbers in the claims doc were produced by a rule that resets queue
progress to zero on rejoin — which is what the shipped file's own RULE_DECISIONS says it does, but not
what its code does.

## 前提の誤り

- premise: "running `scripts/qa/maker_fill_ref_packet_r2.py` reproduces the numbers in QA4R2-1/3/4/5"
  (claims doc line 8, "code-as-claim" framing) | source: claims_for_auditors_maker4_r2.md intro | data
  shows: the shipped code's touch-move-rejoin path carries over `cum` instead of resetting it (contra
  its own RULE_DECISIONS decision 1), producing S1 n=2052 not 952, S2 sign-flipped, forced-fraction
  4.9% not 46.6% | bias: makes S1/S2 look like they fill far more often, more profitably, and time out
  far less than the correct rule implies — optimistic on completion rate and directionally wrong on S2
  and on cap-timeout risk | inherits: any claim in this or a later packet computed via
  `maker_fill_ref_packet_r2.py` (or an uncorrected copy of it) for a queue-respecting (non-naive)
  population — i.e. every completed-round-trip count, net-bps figure, or forced/cap-timeout rate that
  cites this file for S1 or S2, not just these five.
- premise: none found regarding tick size, own_size, cap_s, fee (0bps stated in the v3 manifest and
  consistent with the packet header) — these check out against the data files.
