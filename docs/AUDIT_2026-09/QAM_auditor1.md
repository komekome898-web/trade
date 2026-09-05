# QAM blind audit (packet: qa_known_answer_maker_20260905)

Files read: `docs/AUDIT_2026-09/PROTOCOL.md`; `backtest_data/qa_known_answer_maker_20260905/manifest.md`,
`ticker_qa_maker_tape.csv.gz` (51517 rows), `executions_qa_maker_tape.csv.gz` (32247 rows). Grepped
`docs/AUDIT_2026-09/00_packets.md` for "QAM"/"QA-M" — no matching rows exist in that file, so no packet
row content was read. No other `docs/` file, no `scripts/qa/*`, no `docs/QA/` opened. Script:
`/tmp/claude-0/-home-user-trade/fa7bf0d4-a5c4-55b7-991b-874b590e00a3/scratchpad/audit_QAM.py` (own
implementation, event-driven simulator over the merged tick+execution stream). Fee used: 0 bps
maker/taker (per manifest — trusted here only because the manifest is data documentation, not a claim
document). Tick = 0.3 bps of price (relative, so tick size itself is ~30 JPY at ~1,000,000 price and
drifts with price — not a fixed grid). Own size 0.85 units throughout.

Fill model (mine, independent of any generator code I did not read): a resting maker order joins the
queue with `queue_ahead` = displayed size at post time; it is repriced (queue reset) only when the
market moves **away** from it (best rises above a resting bid, or falls below a resting ask) — the
"always quote the best" discipline; when the market moves **toward/through** it, the order is not
auto-filled — instead every qualifying same/better-priced print's size accumulates, and the order fills
once cumulative volume ≥ `queue_ahead + 0.85`. "Naive" (QA-M2) sets `queue_ahead=0` in that same
accumulation (ignore other traders' queue, still respect own size) — the literal reading of "displayed
queue size in front of you is ignored." "Improve" (QA-M3) posts 1 tick inside best with `queue_ahead=0`
always (a fresh price level). Round trips: flat quotes both sides; first fill opens a position; the
opposite side is then quoted (300s cap); on cap, forced-cross at the prevailing opposite best (0 bps
fee, so cost = the crossed spread only). Diagnostics: exact float equality between an execution price and
the immediately preceding tick's touch holds for only ~3% of prints (backward), confirming prices are
continuous, not levels — so an "exact price, no crossing" convention gave n=1 fill in 3 days (unusable)
and was rejected as unrealistically strict; the reported numbers use the accumulation model above.

## QA-M1
Recomputed (best-quote, queue-correct, all round trips incl. forced timeouts, n=942, denominator = every
completed cycle from a flat quote to next flat quote over the full 3-day tape): mean **-21.13 bps**/trip,
sd 13.55, t=-47.9. Timeouts: 181/942 (19%). Controls: sign-reversed flips sign as expected (sanity pass);
random-sign placebo on the same trips gives mean -1.13bps, t=-1.38 (not significant) — the un-shuffled
effect is not a fluke of the test, but its **size** is far from the claim. Regime: long vs short entries
agree in sign/magnitude (-21.55 vs -20.72bps, n=461/481) — not a directional artifact; 3 UTC hour-tercile
buckets all -19 to -23bps — no regime concentration. Money: -21.13bps × 0.85 units × ~1,000,000 JPY
notional ≈ -1,796 JPY/trip; n/day≈314. MDE at this n,sd ≈ 1.24bps (80%/α=.05) — my sample could easily
have detected the claimed -0.84bps, so the gap is not a power problem. Median holding time 156s (p90
303s, i.e. most trips ride close to the 300s cap), which is the mechanical driver: the "chase on adverse,
hold on favorable" repricing bakes in the full adverse excursion whenever price moves against the open
side before it fills. Claimed: -0.84bps, t=-1.50. My number reproduces the **sign** (net negative,
doesn't clear a 0-bps cost floor) but not the **magnitude or significance class** (25x larger, t an order
of magnitude bigger). I cannot rule out that my repricing/accumulation convention is more punishing than
whatever produced -0.84bps, and without the generator I cannot pin down which convention is "the" answer.
Verdict: 判定不能

## QA-M2
Recomputed (naive: `queue_ahead=0`, same accumulation/repricing/cap machinery, n=1007, denominator as
above): mean **-20.43 bps**/trip, sd 13.30, t=-48.8, 146/1007 timeouts. This differs from QA-M1 by only
~0.7bps (942→1007 trips, -21.13→-20.43) — under my implementation, dropping other traders' queue barely
moves the number, because displayed sizes here (0.001-0.25 units) are a small fraction of the 0.85-unit
own order, so `queue_ahead` was never the dominant term in the fill threshold. I also tried a much looser
"any single qualifying print instantly fills the whole order" reading of "naive" (no accumulation at
all): that gave -3.41bps (n=5873) — still negative, never positive, under either reading of "naive." I
could not reproduce a positive naive edge under any fill convention I built, nor the claimed mechanism
(that ignoring queue position specifically is what flips the sign) — in my reconstruction queue-ignoring
is a minor effect, not a sign-flipping one. Denominator: n=1007 (naive) vs 942 (queue-correct) — same
population, different fill counts because the threshold differs slightly.
Verdict: 結論変更

## QA-M3
Recomputed (best+1 tick improve, `queue_ahead=0` fresh each reprice, n=1007, same 3-day denominator):
mean **-20.99 bps**/trip, sd 13.25, t=-50.3, 146/1007 timeouts — essentially identical to QA-M1/QA-M2 in
my reconstruction, not the claimed near-zero (-0.43bps, t=-0.89, "not distinguishable from 0"). Sign
agrees (still negative) but the claimed near-zero/insignificant result does not reproduce at all — mine
is as significant as QA-M1. Since improving the quote should, if anything, reduce time-to-fill and
therefore adverse drift relative to best-quote, and it did not move the number here, this is more
evidence that whatever dominates my simulated loss (the cap-chasing mechanic, holding-time ≈150s median)
swamps the specific quoting-price choice — a mechanism the claim's framing (which treats M1/M2/M3 as
differing mainly by fill-assumption realism) does not mention.
Verdict: 判定不能

## QA-M4
Recomputed on every maker fill from the QA-M1 sim (entries + resolved maker exits, n=1704, 5-second
forward mid move, signed so positive = adverse to the filled side; denominator = all such fills across
the 3-day tape, looked up via as-of merge against the ticker stream): mean adverse-selection cost
**+3.36 bps**, sd 5.04, t=27.5 — overwhelmingly different from zero, not "indistinguishable from 0" as
claimed. This held up (positive, large-t) under a second, looser fill convention too (+1.27bps, t=53.0
under the "any print at/through price = instant fill" variant), so the qualitative finding (real,
economically meaningful adverse selection exists on maker fills here) is robust to my modeling choices,
even though the point estimate moves with the convention. The claim's logical step — "if adverse
selection ≈0, a correct queue model should flip the round trip to net-positive" — is a non sequitur even
on its own terms: QA-M1's loss is concentrated in trips that ride out toward the 300s cap (chasing cost),
not in the instant-post-fill drift window QA-M4 measures; these are different loss channels. My data
reject the premise (adverse selection is not ≈0) and separately show the conclusion doesn't follow from
the premise.
Verdict: 結論変更

## QA-M5
Recomputed on QA-M1's resolved-only trips (n=761, excludes 181/942 timeouts): plain price-diff mean
-17.78bps (vs -21.13bps for the full sample — excluding timeouts does help, +3.35bps, consistent
direction with the claim's mechanism). Then switching to "mid at the ticker quote immediately before
each fill" as the capture basis (entry_edge + exit_edge relative to local mid) moves it further, to
**-10.25bps**, t=-57.7 — a further +7.53bps improvement from the benchmark change. Both adjustments push
in the claimed direction, but combined they leave the number substantially negative, not positive:
neither the exclusion nor the mid-basis redefinition, alone or together, gets me to the claimed
net-positive result in my reconstruction. Separately, both adjustments are look-ahead / selection
choices: excluding trades that "wouldn't have closed via maker" throws out exactly the trades most
likely to be adverse-drift trades (survivorship on the worst outcomes), and pricing capture against the
mid "just before" each leg's own fill (rather than one consistent entry-to-exit reference) credits
spread-capture per leg independent of the price path between legs — it cannot be traded on on a
walk-forward basis since it uses information (that this specific fill would happen at this specific
time) that isn't known when the position is opened. Even granting the flawed method's numbers, the
implied conclusion ("a real tradable edge exists once you avoid stuck positions") does not follow.
Verdict: 結論変更

## 前提の誤り
- **premise**: "コスト" in QA-M1's framing implies a fee floor being exceeded. | source: claim text
  ("コストを上回らない"). | data: manifest fee = 0bps maker AND taker for this packet — there is no fee
  cost here at all; every claimed net number in this packet is 100% spread-crossing/drift cost, not fee.
  | bias: none on THIS packet's sign, but any downstream reasoning that attributes QA-M1-style losses to
  "the fee floor" would be wrong for this data and should be checked against whatever fee assumption the
  real (non-QA) audits used. | inherits: any claim that cites "the cost floor" as if it were fee-driven.
- **premise**: queue position (displayed size ahead of you) is the dominant lever between QA-M1 and
  QA-M2. | source: QA-M2's stated dependency ("キュー位置...を無視した約定仮定に依存する"). | data: in
  this tape, displayed touch sizes (0.001-0.25 units) are small next to the 0.85-unit test order, so
  zeroing them out changed my recomputed mean by <1bps out of ~-21bps — queue position is a second-order
  effect here, not the primary driver of the naive-vs-correct gap the claim implies. | bias: unclear
  direction without the generator's own fill logic, but it undermines the claimed causal story. |
  inherits: QA-M2, and any claim in this area attributing sign flips to queue-ahead modeling specifically.
- **premise**: a single, unambiguous "correct" fill convention exists that any competent implementation
  would converge on. | source: implicit in all five claims quoting one number apiece. | data: I built
  three defensible conventions (exact-price-only: n=1, unusable; instant-through-clears: n≈5872,
  mean≈-3.4bps; sticky-accumulate-until-threshold: n≈942-1007, mean≈-20 to -21bps) and got answers that
  differ by more than an order of magnitude from each other and from the claims. This packet's own
  manifest names this exact area ("MAKER FILL-MODEL claims — the area where the real blind audits
  actually disagreed") as unsettled. | bias: makes every claim in this packet's magnitude
  (not just sign) essentially unverifiable without the sealed generator. | inherits: QA-M1, QA-M3, QA-M5
  numerically; QA-M2's sign claim is contradicted more directly (see above).
- **premise** (QA-M4): adverse selection at 5s is ≈0. | source: claim text. | data: t=27.5-53 across two
  conventions, mean +1.3 to +3.4bps — robustly, significantly positive, not zero. | bias: this premise
  being false undermines the QA-M4 conclusion independent of the separate logic error already noted. |
  inherits: any claim assuming "no informed-flow selection on maker fills" in this instrument/venue.
