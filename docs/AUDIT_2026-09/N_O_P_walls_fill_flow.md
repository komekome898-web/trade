# Packets N, O, P — walls, fill rate, two-sided flow (blind audit)

Claims: L26, R31 (N) / L27, L28 (O) / L29 (P). Own implementation, ≤50 tool calls.

## Files read
`docs/AUDIT_2026-09/PROTOCOL.md`; `docs/AUDIT_2026-09/00_packets.md` lines 25–107 only (grep/sed, claim rows for
L1–L30, R1–R43); `paper_logs/tape/ticker_20260820..20260904.csv.gz` (16 files, best bid/ask+size);
`paper_logs/tape/executions_20260820..20260904.csv.gz` (16 files, trade prints); `backtest_data/board_round_20260904/
board_round_series_5s.csv.gz` (header + row count only — confirms no per-level breakdown, see below),
`board_round_coverage.json`, `MD5SUMS`; `backtest_data/venue_survey_20260827/` directory listing +
`bf_fxbtc_book.jsonl.gz` (fully loaded, 5-level depth, 1 day/4hr), `bf_fxbtc_trade.jsonl.gz`/`trade2` (head only);
`config/config.yaml`, `config/products.yaml`, `config/risk_limits.yaml` (grep). **Not opened**: `FINAL.txt`,
`SCREEN.txt`, `analyze_*.py` in venue_survey (survey-report-shaped text, avoided out of caution though not literally
named in the exclusion list), `JUDGE_RUN*.txt` in board_round_20260904 (excluded by `*_RUN.txt` rule). Audit not void.

## Data-availability finding (untestable parts)
Only `bf_fxbtc_book.jsonl.gz` (venue_survey, **1 day, 4-hour window**, 5 levels/side, ~2s cadence) has genuine
multi-level depth. `board_round_series_5s.csv.gz` has only `best_bid_size`/`best_ask_size` (top) plus an aggregated
`bid_depth_5bps`/`ask_depth_5bps` sum — **no individual level sizes**, so it cannot support a "wall at a specific
level" test at all. `ticker_*.csv.gz` (16 days) has top-of-book size only. Consequence: a literal, long-sample,
per-level wall-survival test (as L26/R31 imply) is **not reproducible** from the data provided; we used two
proxies instead (below), one long-but-shallow (top-of-book, 16 days) and one deep-but-short (5-level, 1 day).

## N — L26 (walls are not absorbers) / R31 (quoting in front of a wall)
Wall def. (own choice, matches the "M24" label in L26): displayed size at a level ≥ 10× the trailing 24-tick
median size at that same side (excludes bitFlyer 19:00–19:10 UTC maintenance).

**Top-of-book, 16 days** (n=1,589,458 ticks): wall events n=122,508 (bid+ask); control (size ≤2×M24) n=2,380,169
(subsampled 48,000, day-stratified). 10s outcome = does the exact best price survive unchanged / get eaten through
(price crosses it) / get "reversed" (a better price appears first)?
| | SURVIVE | day-CI | EATEN | REVERSED |
|---|---|---|---|---|
|wall|6.01%|[4.30,7.35]%|43.9%|50.1%|
|control|3.29%|[1.76,5.35]%|46.3%|50.4%|

Walls survive ~2× longer than non-wall levels here, but both rates are tiny because *any* best-price tick change
(which happens almost every second in this book) counts as "not surviving" — this is a much stricter test than
"the resting order is gone."

**Depth-based, 1 day/4h cross-check** (bf_fxbtc_book, ranks 0–4 pooled, tracks whether the exact price still
appears anywhere in the visible top-5 book after 10s): bid n=1,072 (GONE 91.3%, SURVIVE_FULL≥70%size 6.7%,
SURVIVE_PARTIAL 2.0%); ask n=1,749 (GONE 87.9%, SURVIVE_FULL 9.8%, SURVIVE_PARTIAL 2.2%).

Same qualitative story as L26 (large displayed size is not durable) but our number is *more* extreme (88–91%
disappear vs claimed 63–65%; survival 7–10% vs claimed 13%) — and only testable on one day, 5 visible levels
(a level can "vanish" from view merely by price drifting past the 5th level, inflating GONE — flagged, not
correctable with this data). n=1 day means no cross-day CI is possible for this cut.

**R31** — quote 1 tick in front of a detected wall (front-run for queue priority), fill = an opposite-side print
crosses the quote within 30s (uses executions file), edge = mid move 30s after fill net of the tick paid:
fill rate 61.2% (n=122,509 attempts, 74,913 filled), mean edge **−0.41bps** (median −0.29bps) vs a data-derived
bar = median half-spread **0.956bps** (16-day, all ticks; spread=1.91bps median) → edge/bar = **−0.43**.

**Verdict L26: 数値差異(結論維持)** — walls vanish fast and are not reliable absorbers, direction confirmed on the
one testable day; magnitude not pinned down (63–65%→88–91% here), and the 16-day top-of-book proxy actually shows
the *opposite* ranking (walls more sticky than control) under a stricter definition — flag both.
**Verdict R31: 数値差異(結論維持)** — strategy fails to clear the bar in our reproduction too (edge/bar<1), but our
raw edge is *negative*, not the claimed small positive (+0.32~0.70bps); sign differs even though the pass/fail
conclusion does not.

## O — L27 (fill rate) / L28 (capture)
Queue-realistic quote: every 15s (both sides, 16 days), join queue at current best behind `ahead_size` = displayed
size there; fill when cumulative opposite-side prints *at that exact price* reach `ahead_size`; cancel when the
top-of-book price moves ("cancel_on_move"); 30s lifetime. n=165,734 attempts.

**f(30s) = 9.15%**, day-clustered 95% CI **[8.77%, 9.63%]** (n_days=16) — about **half** the claimed 18.1%.
Day-clustered SE implies an MDE of ≈0.6 percentage points at this n; the 9pp gap to the claim is far outside noise,
so this is a genuine level discrepancy, not a sampling artifact — likely driven by our 15s refresh cadence and/or
exact-price-match fill rule differing from whatever produced "実板7日."

One-at-a-time sensitivity (|Δf| from baseline, or range across a 3-way split):
| axis | measurement | Δ/range |
|---|---|---|
|spread tercile|tight 14.8% / mid 6.9% / wide 5.8%|0.090|
|fill model (naive vs queue)|naive 13.6%|0.045|
|cancel policy (hold vs cancel_on_move)|hold 13.6%|0.044|
|regime (vol tercile)|8.6%/8.6%/10.3%|0.017|
|lifetime (10s/60s vs 30s)|8.6%/9.2%|0.006|
|vr tercile|9.0%/9.2%/9.2%|0.002|

Our order: **spread > fill_model ≈ cancel_policy > regime > lifetime > vr**. Claimed order: cancel_policy(4.33x)
> spread(2.04x) > lifetime(1.63x) > regime > fill_model > vr. Only agreement: **vr is the weakest driver in both.**
Cancel policy vs spread swap rank #1/#2; lifetime drops from 3rd to next-to-last in ours.

**L28 capture** (30s-lifetime fills, n=15,157): nominal (mid *at quote time* − fill price) mean **0.79bps**
(81% of the nominal half-spread, 0.97bps) — not "about half." Effective (mid *at actual fill time* − fill price,
the economically meaningful one) mean **0.033bps** — almost fully eroded, because fills disproportionately occur
exactly when price has already moved to meet the quote. Adding 5s post-fill adverse drift (mean **+0.36bps**
against the position) gives net **−0.33bps** for this cohort (claim: filled-quote capture ≈ **+0.60bps**, positive).
Single-shot, 5s-lifetime quote, unconditional over all n=165,734 attempts (0 if unfilled): mean **−0.02bps**
— same sign and order of magnitude as claimed −0.09~−0.86bps, at the small end of that range.

**Verdict L27: 数値差異(結論維持)** for "f is small, single digits/low teens %", but the specific 18.1% does not
reproduce (9.15%, ~2× off, day-clustered CI excludes 18.1%).
**Verdict dominance order: 結論変更** — only the "vr weakest" ranking survives; the ordering of the other 5 axes
does not reproduce.
**Verdict L28: 数値差異(結論維持)** — capture is thin and largely consumed by adverse selection (net negative to
near-zero in our reproduction, which if anything is a *more* pessimistic finding than the claimed +0.60bps); the
single-quote 5s figure reproduces in sign/order of magnitude.

## P — L29 (two-sided flow)
30s windows, 16 days, n=41,685 (executions-only; maintenance window not separately filtered here — negligible,
<10min/day of near-zero volume). Two-sided = both buy and sell prints present with
`min(buy_vol,sell_vol)/max(...)` ≥ threshold (own choice; swept):
| balance threshold | duty cycle |
|---|---|
|≥0.3 (any imbalance)|40.2%|
|≥0.5|25.5%|
|≥0.7|13.6%|
|≥0.7, min 0.01 BTC/side|13.1%|
|≥0.8, min 0.01 BTC/side|8.3%|

The claimed **11.5%** sits inside a narrow band around threshold≈0.7–0.75 — reproducible only with a fairly
strict, undisclosed balance definition; the headline swings **~5×** (8%→40%) across a plausible parameter range —
a real selection-contamination risk (protocol Q7), not resolved by this audit.

Idealized maker P&L (bal≥0.3 windows; both legs fill at 100%, capture the window's own spread_bps; outside
windows get forced-taker-completion netting to ≈0 by construction — single reference, no fee since FX_BTC_JPY
taker_fee=0% per `config/products.yaml`): net_inside mean **+2.02bps** [day-CI 1.83, 2.09], n=16,724 windows;
net_outside ≈ **0bps** (by construction of the idealization, not an independent measurement). Sign (inside>outside)
holds across every balance threshold we tried (0.3–0.8) — this part is comparatively robust even though the duty
level is not. Claimed net_inside range +0.38~0.76bps is **3–5× smaller** than ours — our idealization (full
spread captured, zero cost) is evidently more optimistic than whatever produced the claim.

Money translation (own assumption, undocumented in the claim): 0.01 BTC unit (~115,000 JPY notional at
~11.5M JPY/BTC) × duty(0.3)=40.25% × 2,880 windows/day → ≈1,159 two-sided windows/day → **≈27,000 JPY/day** at
f=100%. Same order of magnitude as the claimed 80,000–130,000 JPY/day but **3–5× smaller**; both the unit size and
the duty-cycle threshold are free parameters not pinned down by the claim text, so this gap is not resolvable here.

**Verdict L29: 数値差異(結論維持)** — two-sided windows are the only regime where the idealized model is reliably
positive (sign robust to the balance threshold), but neither the 11.5% duty cycle nor the +0.38~0.76bps / 8–13万
円/day figures are independently pinned down; our own numbers move several-fold with defensible parameter choices.

## Controls / consistency (protocol Q2, Q9)
Two independent wall-survival measurements (top-of-book/16d vs depth/1d) agree in *direction* (both show most
large displayed sizes are transient) but disagree sharply in magnitude and even in the wall-vs-control ranking —
a genuine inconsistency (Q9), most likely because they measure different things (best-price persistence vs level
presence anywhere in the visible 5-level book).

## 前提の誤り (assumption findings)
| premise | source in claim | what the data shows | bias direction | inherits to |
|---|---|---|---|---|
|A continuous, multi-day, full-depth order book exists to test "wall survival" literally|L26/R31 (implied by n and 10s-survival framing)|Only 1 day/4h of 5-level depth is available (`bf_fxbtc_book.jsonl.gz`); everything else is top-of-book only or a level-blind 5bps aggregate|Unknown; shrinks effective n for the literal test from "whatever produced 63–65%" to n≈1,072–1,749 on 1 day — confidence should be downgraded regardless of point-estimate agreement|R21, L19, L28 (same venue_survey machinery), any claim citing "10 seconds" wall/level persistence|
|f=18.1% used "実板7日" (7 days)|L27|Our permitted long sample is 16 days of ticker/executions; no 7-day-labeled subset was identified, and our reproduction (9.15%) is ~half the claim regardless of which sub-window|Unknown direction; the quote-refresh cadence and exact-match fill rule are also unstated in the claim and materially move f (this audit's own sensitivity: fill_model alone moves f by 4.5pp)|L28 (capture is fill-model-dependent), the dominance-order ranking itself|
|"Balanced" two-sided flow (L29) has one implicit threshold|L29|Duty cycle ranges 8%→40% for balance thresholds 0.8→0.3; claimed 11.5% only matches ≈0.7–0.75|Could inflate or deflate the reported edge-per-day depending on which threshold was used upstream|The JPY/day translation, and any capacity/sizing claim built on "how often" two-sided flow occurs|
|FX_BTC_JPY has a nonzero taker fee used as a cost floor|not stated numerically in any of L26–L29, but "コスト" language throughout the packet implies one|`config/products.yaml`: FX_BTC_JPY `taker_fee_pct: 0.0` (Lightning FX); `config/config.yaml`'s generic `costs.taker_fee_pct: 0.15%` is a spot-product paper-fill fallback, not this product's live fee|If any upstream "bar" used 0.15% instead of 0%, rejections against that bar look more decisive than the true (spread-only) cost floor warrants — direction: conservative (harder to pass) bar inflates false rejections|R31's bar, any other claim on this product citing a taker-fee cost floor|

Every rate above states its own n/date-range denominator (16 days ticker+executions 20260820–20260904 unless
marked as the 1-day venue_survey depth cross-check).
