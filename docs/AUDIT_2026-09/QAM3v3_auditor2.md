# QAM3v3 blind audit (auditor 2)

Files read: `docs/AUDIT_2026-09/PROTOCOL.md`; `docs/QA/claims_for_auditors_maker3_v3.md` (only permitted docs/QA file);
`backtest_data/qa_known_answer_maker3_v3_20260905/manifest.md`, `ticker_qa_maker3_v3_tape.csv.gz`,
`executions_qa_maker3_v3_tape.csv.gz`. No other `docs/`, no `scripts/qa/*`, no sealed answers were opened.

Method: independent Python re-implementation of the stated fill rule (own script, not shown to the packet's
generator), event-merged over 340,617 ticker rows + 36,904 execution prints (5 trading days, tick=10, own
clip=0.05, fee=0bps per manifest). Two independent per-origin-side state machines (LONG from bid-entry, SHORT
from ask-entry), each: rest at touch -> cancel/rejoin on touch move -> fill when cumulative same-price/side
executions since (re)insertion reach queue-ahead(=display size at insertion minus 0.05)+0.05 -> opposite-side
exit (same queue logic, S1 non-improving; S2 improves 1 tick when spread>=2 ticks) -> forced exit at the public
touch if 300s elapse since entry fill. Script: `audit_QAM3v3_2.py` in the scratchpad.

Denominators (Q1): S1-correct completed round trips n=1263 (5 days, both LONG+SHORT); S1-naive n=17,924;
S2-correct n=388. Controls (Q2): sign-reversed net is the exact mirror (by construction, not informative on its
own); a placebo with randomized adverse-selection sign gives mean~0, t~1.4 (n=1250) — consistent with no built-in
bias in the estimator. Cost (Q3): manifest states fee=0bps maker/taker for this synthetic packet, so net=gross
here; this is NOT bitFlyer's real fee and the packet is not a claim about real economics. MDE at S1's n=1263,
std=4.65bps: ~0.37bps (two-sided, ~80% power) — the claimed +0.30bps (QA3-1) sits BELOW my own study's MDE, i.e.
even a true 0.30bps effect would be hard to detect at this n, which cuts against reading a low t as proof of "no
edge" but does not rescue a t=2.79 claim built on the same n. S2 (n=388, std=3.96bps): MDE~0.56bps — a true
-0.98bps effect (QA3-3) would have been detectable; I find +0.36bps instead (t=1.77), i.e. a sign flip, not
"can't tell."

## QA3-1
Claim: S1, 300s cap, net = +0.30bps/RT (t=2.79), positive and significant.
Recomputed: n=1263, mean = -0.0660bps, t = -0.50. Sign differs from claim and is not distinguishable from zero.
Neither the number (far outside 10% band) nor the "positive and significant" conclusion reproduces.
Verdict: 結論変更

## QA3-2
Claim: naive rule (ignore queue-ahead, first same-price/side print after insertion = fill) gives +0.84bps/RT
(t=74.63), so much more optimistic than the correct rule that a tradable edge is "obvious" even from the naive
calc alone.
Recomputed naive rule: n=17,924 (LONG 8989 mean 0.0118bps; SHORT 8935 mean 0.0005bps), pooled mean ~0.0062bps,
t=0.69 — indistinguishable from zero, not the large significant number claimed. Median holding time under naive
is 0.017s (near-instant), so the "naive is optimistic vs correct" DIRECTION is qualitatively right in my
reproduction (naive mean 0.006 > correct mean -0.066) but the magnitude/significance claimed (t=74.63) does not
reproduce, and the stated conclusion ("this alone proves a tradable edge exists") does not follow from what I
recompute — under my implementation the naive number itself is statistical noise.
Verdict: 結論変更

## QA3-3
Claim: S2 (improve 1 tick when spread>=2 ticks, else at touch), net = -0.98bps/RT (t=-26.19), negative and
significant.
Recomputed: n=388 (LONG 184 mean +0.53bps; SHORT 204 mean +0.19bps), pooled mean = +0.356bps, t=1.77. Sign is
opposite the claim and the effect is only marginally significant at best. Given the MDE at this n (~0.56bps) a
true -0.98bps effect should have been visible; instead I find a positive, weaker effect.
Verdict: 結論変更

## QA3-4
Claim: S1 entry fills only, 5s-ahead sign-adjusted adverse selection is statistically indistinguishable from
zero.
Recomputed: n=1250 entry fills, mean signed mid-move over the next 5s = +0.39 price units (~0.04bps), t=0.084 —
solidly indistinguishable from zero. This is the one claim whose qualitative conclusion reproduces cleanly under
my implementation (no explicit point estimate was given in the claim to band-check, only the "indistinguishable
from zero" conclusion, which holds).
Verdict: 再現

## QA3-5
Claim: S1 completed positions excluding 300s-cap forced exits, mean net = +1.26bps, "the correct expectation".
Recomputed: my S1-correct run produced 0 forced exits out of 1263 completed positions (see QA3-6), so the
"excluding forced exits" subset in my reproduction is identical to the full population, mean = -0.0660bps (same
as QA3-1), not +1.26bps. Sign differs and the magnitude is far outside the 10% band. Internally, the claim set
(QA3-1, QA3-5, QA3-6) is arithmetically self-consistent taken alone: 0.446*x_forced + 0.554*1.26 = 0.30 implies
the claimed forced-exit subset averages ~-0.89bps, which is a coherent mixture — but that internal consistency
does not rescue the claim once none of the three component numbers reproduces against the data.
Verdict: 結論変更

## QA3-6
Claim: 44.6% of S1 completed positions are forced (300s-cap) exits.
Recomputed: 0 of 1263 completed positions (0.0%) hit the 300s cap; maximum entry-to-exit holding time observed
was 2.43 seconds, three orders of magnitude below the 300s cap. This is the single largest and most structural
discrepancy in the packet: it is not a 10%-band miss, it is a different regime (my reproduction never approaches
the cap at all). Two admissible explanations: (a) the claim's generator produces materially slower exit fills
than my re-implementation of the stated rule (see 前提の誤り below for the specific ambiguity that could cause
this), or (b) the 44.6% figure is simply wrong for this population. I cannot fully rule out (a) within budget; I
flag this claim as needing the second (upper-tier) auditor's independent implementation to triangulate before
treating it as settled, but on the evidence I obtained, the claimed rate does not reproduce.
Verdict: 結論変更

## 前提の誤り

- premise: "at most one open position per side" | source: 上記の約定規則 (manifest fill rule) | data/model shows:
  the rule is read literally as a cap on OPEN POSITIONS COUNTED BY ORIGIN SIDE (bid-entries vs ask-entries), which
  permits our own LONG-exit order and our own SHORT-entry order to rest on the SAME book side (ask) at the same
  time, each independently computing queue-ahead from the same displayed size. An equally literal alternative
  reading treats each BOOK SIDE (not origin side) as a single shared slot, which would serialize those two orders
  and materially lengthen wait times. The manifest's "our own resting clip" is written in the singular, which is
  some evidence for the shared-slot reading. | direction of bias: if the shared-slot reading is correct, my
  reproduced exit times are too fast and my 0% forced-exit rate (QA3-6) and near-zero net (QA3-1/QA3-5) are biased
  toward faster/cheaper fills than the true rule would produce | inherits to: QA3-1, QA3-3, QA3-5, QA3-6 (every
  claim whose number depends on exit-side wait-time distribution); QA3-2 and QA3-4 are not materially affected
  since they don't depend on the shared-slot resolution (naive rule has no queue-ahead concept; adverse selection
  is measured at entry fills only).
- premise: none of the six claims states its own n (population size) | source: claims file, all six items | data
  shows: n must be back-derived; QA3-1's t=2.79 with a plausible per-trade std (I measure ~4.65bps under my model)
  implies a materially larger n than my reproduced 1263 if the claimed std is similar, which is inconsistent with
  the ~253 completed-positions/day rate I measure from the actual tape and my own entry-side wait times |
  direction of bias: obscures whether the discrepancy is a rate-of-fills problem or a per-trade-return problem |
  inherits to: QA3-1, QA3-2, QA3-3, QA3-5, QA3-6 (all give a bps+t pair with no n, no CI).
- premise: fee = 0bps maker and taker (manifest, explicit) | source: manifest, applies to every claim's "net" |
  data shows: this is confirmed and consistent (net=gross throughout this packet) | direction of bias: none for
  the packet's own arithmetic, but any reader translating these bps into a real bitFlyer P&L estimate would need
  to subtract real fees/costs not present here — flag so this synthetic packet's numbers are not reused as a real
  cost estimate | inherits to: any claim citing this packet's bps as a proxy for real strategy economics (none of
  the six do so explicitly, but the packet could be misused this way downstream).
- premise: S2's exit orders follow the same (non-improving) exit rule as S1 | source: inferred, since QA3-3's
  text only specifies the ENTRY-side improve logic and the shared fill-rule paragraph does not mention improving
  exits | data/model shows: this is a reasonable but unstated assumption; if S2's exits also improve, QA3-3's
  number would shift further, in a direction I did not test | direction of bias: unknown magnitude/sign |
  inherits to: QA3-3 only.
