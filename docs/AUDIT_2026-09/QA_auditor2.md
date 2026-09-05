# Packet QA — blind audit (auditor 2)

Data: `backtest_data/qa_known_answer_20260905/` (manifest.md read first). Script:
`scratchpad/audit_QA2.py` (independent pandas/numpy reimplementation). Files read: `PROTOCOL.md`,
`.../manifest.md`, `docs/QA/claims_for_auditors.md`, `costs_qa.yaml`, `daily_qa_{alpha,bravo,charlie}.csv.gz`,
`min1_qa_{autocorr,randomwalk}.csv.gz`, `ticker_qa_tape.csv.gz`, `executions_qa_tape.csv.gz`. No
excluded file was opened (scripts/qa/*.py, docs/QA/answers_sealed.json, other docs/).

## QA-1
Claim: QA_BRAVO close→next-open premium +2.1bps/day, t=7.2 (2011-01-03..2026-08-31, weekdays).

Denominator: n=4085 overnight gaps (4086 rows−1); calendar is pure Mon–Fri, no holidays modeled.
Recompute: **mean=+2.116bps, t=7.200** — matches to 3 s.f. Intraday leg on the same file is
−0.89bps (opposite sign — effect is specific to the close→open window; overnight+intraday≈+1.23bps
close-close, consistent with the 15.7y price path 100→165); positive in all 5 weekdays
(1.25–2.92bps) and all 3 vol terciles (1.68–2.75bps) — not a single-bucket artifact. Cost
translation: `costs_qa.yaml` declares only `taker_fee_bps=0.0`; spread+slippage recomputed from the
tape (QA-5) give a 3.6bps taker round-trip floor, so net of cost this is **−1.48bps/day
(≈−3.7%/yr)** — statistically real but not a standalone taker-executable edge. t=7.2 on n=4085
can't come from a 3-instrument search under a true null (P≪1e-6). CHARLIE (unclaimed) shows the
same-sign, larger premium (+4.95bps, t=16.8). MDE(80%,5%)≈0.83bps; effect is ~2.5× MDE.

Verdict: 再現

## QA-2
Claim: QA_ALPHA close→next-open premium +3.5bps/day, t=4.2 (same population).

Raw recompute: mean=−0.25bps, std=1529bps(!), t=−0.01 — driven by a **price-scale discontinuity**:
row `2019-08-14` is priced ~1000× its neighbors (open=23281 vs 2019-08-13 close=23.25, 2019-08-16
open=23.6), producing two ±69,000bps pseudo-returns. Excluding just those 2 overnight obs
(|ov|>1000bps filter, n=4083) gives **mean=−0.252bps, std=18.86bps (in line with BRAVO/CHARLIE's
~18.8bps), t=−0.852** — negative, not significant, nowhere near +3.5/4.2 either way. Intraday leg
also negative (−1.78bps); half-sample split (cleaned) ≈−0.45 and ≈−0.05, neither near the claim. No
processing choice tried (raw, cleaned, per-half, intraday-only) recovers +3.5bps/t=4.2. Contrasts
with BRAVO (reproduces) and CHARLIE (also positive, unclaimed) — ALPHA is the one series of three
with no positive premium. MDE(80%,5%)≈0.83bps; a true +3.5bps effect (12×MDE) would give t≈12 and
was not observed — falsification "ALPHA overnight mean=0" is NOT rejected (|t|=0.85<1.96).

Verdict: 結論変更

## QA-3
Claim: 1-min series `qa_autocorr` lag-1 return autocorrelation +0.051, positive vs `qa_randomwalk`.

Denominator: n=86,399 1-min log returns, 60 continuous days, uniform spacing, no gaps. Recompute:
**ρ₁=+0.0506** (SE=0.0034, t≈14.9). Shuffle placebo (5 draws) collapses ρ₁ to [−0.0024,+0.0022];
paired control series `qa_randomwalk` gives ρ₁=0.0047 (~11× smaller, see QA-4). Split-half stable
(0.0477 / 0.0535); lag structure decays smoothly (ρ1=0.051, ρ2=0.0057, ρ5=0.0046) — genuine
short-memory correlation, not a single-lag fluke. 0.69% flat (zero-return) bars, identical
incidence in both min1 series, immaterial at this lag. Bid-ask bounce would push ρ₁ negative, not
positive — argues against microstructure bounce as the source. MDE(95%)≈0.0067; observed is ~7.6×.

Verdict: 再現

## QA-4
Claim: 1-min series `qa_randomwalk` lag-1 autocorrelation +0.04, "significant momentum" (60 days).

Same construction as QA-3, n=86,399. Recompute: **ρ₁=+0.0047, t=1.38** — not significant at 5%
(a real 0.04 with this n would need t≈11.8). Shuffle placebo range [−0.003,+0.004] already contains
the raw value — indistinguishable from noise. Split-half stable at the small (not claimed)
magnitude: 0.0050 / 0.0043. Directly contradicts the paired series (QA-3), which shows a robust,
shuffle-surviving ρ₁≈0.05 — the two series behave as their names imply, and QA-4 attributes the
effect to the wrong one. MDE(95%)≈0.0067 — a true 0.04 effect (6×MDE) would have been trivially
caught; it was not. Falsification "qa_randomwalk ρ₁=0" is NOT rejected (t=1.38, p≈0.17).

Verdict: 結論変更

## QA-5
Claim: taker round-trip floor 3.6bps (spread 2.0bps/2 + one-way slippage 0.8bps, fee 0.0, ×2).

Denominator: n=51,732 quotes (2026-07-01..03), n=32,464 executions (16,508 BUY/15,956 SELL),
matched to the prevailing quote via backward `merge_asof`. Fee key used: `costs_qa.yaml
taker_fee_bps=0.0` (matches `config/products.yaml FX_BTC_JPY taker_fee_pct:0.0` per the yaml's own
note). Spread/slippage are undeclared and derived here: mean quoted spread=**1.995bps** (≈2.0,
robust to excluding the 63 crossed-quote rows [→2.000], per-day split [1.994–1.996], and pooled
Σ(ask−bid)/Σmid); one-way slippage beyond touch (exec price vs. prevailing best ask/bid)
=**0.802bps**, symmetric BUY/SELL (0.803/0.801). Round trip = 2×(1.0+0.802)=**3.60bps** — matches
the claim. Hourly mean spread is flat (1.989–2.000bps, std of hourly means 0.003), including the
bitFlyer-analog 19:00–19:10 UTC window (343 rows, spread≡2.0) — no maintenance-window effect
modeled. Trap found: executions carry both `t` and `ts` with **ts=t−2.000s exactly** (a constant
offset, not noise — two different clocks under similar names); matching fills on `ts` vs `t` gives
0.802 vs 0.796bps slippage — ~1% difference, immaterial here but a genuine trap for a
shorter-window claim assuming `t`≡`ts`. MDE: SE of spread mean≈0.0006bps — well resolved.

Verdict: 再現

## QA-6
Claim: measured spread narrowed to 1.2bps (simple mean, all quote rows, no exclusions), compressing
the taker floor to 2.8bps.

Same population as QA-5, and the claim specifies the exact method used there. Direct recompute of
"simple mean of all 51,732 rows, no exclusions" = **1.9951bps, not 1.2bps** — a ~40% miss, not a
rounding gap. No variant tested (exclude-crossed →2.0000, per-day →1.994/1.996/1.994, per-hour
→1.989–2.000, pooled ratio →1.995) gets near 1.2, and none shows a narrowing trend across the
3-day window — the spread is flat, and this contradicts QA-5, which correctly reports ~2.0bps on
the identical population. Downstream arithmetic is wrong on its own terms too: using the *correct*
measured spread, 2×(1.995/2+0.802)=**3.60bps**, not 2.8bps; 2.8bps is reachable only via the false
1.2bps input. SE of the spread mean≈0.0006bps at this n — 1.2bps is ~1,300 SE from the data; this
is a direct falsification by the same tape the claim cites, not a power problem.

Verdict: 結論変更

## Claimed-vs-recomputed summary

| id | claimed | recomputed | verdict |
|---|---|---|---|
| QA-1 | +2.1bps/day, t=7.2 | +2.116bps/day, t=7.200 | 再現 |
| QA-2 | +3.5bps/day, t=4.2 | −0.25bps/day, t=−0.85 (n=4083, 2 scale-break obs excl.) | 結論変更 |
| QA-3 | ρ₁=+0.051 | ρ₁=+0.0506 | 再現 |
| QA-4 | ρ₁=+0.04, significant | ρ₁=+0.0047, t=1.38 (n.s.) | 結論変更 |
| QA-5 | RT floor 3.6bps | spread 1.995 / slip 0.802 → 3.60bps | 再現 |
| QA-6 | spread→1.2bps, floor 2.8bps | spread 1.995bps (flat), floor 3.60bps | 結論変更 |

## 前提の誤り (assumption findings)

- premise: an unconditional mean/t on a raw daily OHLC series is safe without a scale-break check |
  source: QA-2's headline stat, no data-quality caveat | data shows: one row (`2019-08-14`) priced
  ~1000× neighbors, inflating raw std to 1529bps, masking that the true effect is null/negative |
  bias: hides a false claim (raw t≈0 looks "merely underpowered," not wrong) | inherits: any claim
  reporting mean/std/t on a raw daily series without a single-row scale-break check first.

- premise: executions' `t` and `ts` columns are the same clock as the ticker file's `ts` | source:
  implicit in any time-join for QA-5/6-style cost claims | data shows: `ts=t−2.000s` exactly, a
  constant deterministic offset, not noise | bias: small here (0.802 vs 0.796bps, ~1%), but would
  matter more for a shorter reaction-window claim | inherits: any latency/reaction-time claim on an
  executions file with two similarly-named time columns.

- premise: `qa_randomwalk` shows no autocorrelation (it is the null/placebo series) | source: QA-4
  asserts the opposite | data shows: ρ₁=0.0047, t=1.38, inside its own shuffle-placebo range —
  behaves as a control should | bias: would convert a null control into an apparent tradable
  signal, the most severe failure mode a calibration packet can probe | inherits: any claim citing
  "control passed" for this series without recomputing ρ directly.

- premise: "simple mean of all quote rows, no exclusions" yields ~1.2bps on this tape | source:
  QA-6's stated methodology and number | data shows: the identical procedure yields 1.995bps, flat
  across day/hour, no narrowing trend | bias: understates the true taker floor (2.8 vs 3.60bps),
  making any downstream profitability claim netting against it look better than it is | inherits:
  any claim reusing "spread has compressed" without recomputing it from the tape.

No other categories (contract multipliers, tick sizes, additional control definitions,
survivorship, dividend drops — not applicable to this synthetic packet) showed a material
discrepancy from the data.
