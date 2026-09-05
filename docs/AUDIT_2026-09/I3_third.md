# Packet I — blind audit (third pass)

Files read: docs/AUDIT_2026-09/PROTOCOL.md; docs/AUDIT_2026-09/00_packets.md (grep rows `I`, `R22`, `PR5` only);
config/config.yaml; config/products.yaml; schema/bitflyer_tape.json; paper_logs/tape/ticker_20260820..20260904.csv.gz
(16 files, coverage scan + simulation); paper_logs/tape/executions_20260820.csv.gz (header/structure spot-check only,
not used in the fill model — see 前提の誤り); backtest_data/binance_BTCUSDT_1m_210d_20260820.csv.gz (head/tail/wc,
coverage check); backtest_data/venue_survey_20260827/FINAL.txt (pre-computed touch-fill economics, used for Q9);
backtest_data/venue_survey_20260827/bf_fxbtc_book.jsonl.gz (head/count, structure spot-check only).
Script: scratchpad/audit_I3.py (own implementation; no forbidden file was opened).

No PREREG/report text for R22/PR5 was available to me, so "8 cells (N∈{1,4} × time-ladder(2) × gate(2))" was
re-interpreted from the packet row's own words into an independently-designed inventory-grid MM: N = max concurrent
resting clips per side; time-ladder = anchor (grid-center) rolling-mean window, 30s ("fast") vs 300s ("slow"); gate =
new clips allowed only when quoted spread ≤3bps ("on") vs unrestricted ("off"). Grid step = 8bps (own choice, ~4x the
measured touch spread, claim C4's 1.56–2.22bps). Unit = 0.001 BTC (products.yaml min_size). Fee: FX_BTC_JPY
`taker_fee_pct: 0.0` (both maker/taker), so modeled fee = 0; limit fills assumed to execute exactly at the resting
price when touched (generous — no queue/slippage cost, biases toward LESS negative PnL than a real book would give).
Funding (`swap_daily_pct: 0.06`/day) is NOT modeled (see 前提の誤り).

## R22

**1. Denominator.** 16 days of bitFlyer FX_BTC_JPY public ticker (paper_logs/tape/ticker_20260820..20260904.csv.gz),
resampled to 5s bars. 6/16 days are partial captures (<24h): 20260820 (17.8h), 20260825 (18.5h), 20260826 (21.1h,
starts 02:54), 20260827 (18.0h), 20260828 (19.7h, starts 04:18), 20260904 (12.5h) — a known extract_tape.py defect
(truncated WS recording), not noise I introduced. 8 self-defined cells × 16 days = 128 daily cell-values (not the
claimed 56 — I could not find a 7-day subset rule anywhere in the permitted files, so I used all 16 days and also
report a 10-full-day-only subset).

**Recomputed headline:** all 8 cell MEANS are negative (JPY/day, 0.001 BTC unit, no fee):
fast30s/N1/off=-162, fast30s/N1/on=-132, fast30s/N4/off=-565, fast30s/N4/on=-435, slow300s/N1/off=-155,
slow300s/N1/on=-157, slow300s/N4/off=-712, slow300s/N4/on=-719. Pooled 128 obs: mean=-380 JPY/day, sd=641,
t=-6.70 (df=127, p≪.001). But **95/128 (74%) of individual daily values are negative, not 128/128** — the literal
"56 of 56 all negative" (zero exceptions) does not reproduce; every cell has 3–6/16 positive days.
10-full-day subset (drops the 6 partial days): same sign pattern, e.g. fast30s/N1/off 8/10 neg (mean -164),
slow300s/N4/on 9/10 neg (mean -828).

**2. Controls.** (i) Sign-reversed (momentum: buy breakouts instead of dips) → strongly POSITIVE, mean +8,032 to
+23,719 JPY/day, 0/16 negative — confirms no sign bug and that the loss is specific to the mean-reversion logic in a
trending tape. (ii) All-time random control: shuffling each day's 5s log-returns (same cell, 8 reps/day) — note this
*preserves the day's total start-to-end drift* (sum of returns is order-invariant) — gives mean -120 JPY/day, 13/16
negative, close to real (-162). (ii) State-conditional / detrended control: demeaning returns to zero out each day's
net drift before shuffling collapses the loss to mean -32 JPY/day (11/16 negative) — an order of magnitude smaller.
Together these show the loss is driven mostly by each day's net trend (drift), with a smaller residual (~-32 of -162,
≈20%) from pure touch/spread mechanics even with zero drift — consistent with the venue-survey's own finding (below).

**3. Translation.** Fee key used: `config/products.yaml FX_BTC_JPY.taker_fee_pct = 0.0` (maker/taker both 0%); no
half-spread/slippage line item applies to a resting-maker design, so modeled cost = 0 beyond adverse selection.
Per-notional bps/day: N=1 cells ≈ -162 JPY / (0.001×~11.0M JPY notional) ≈ -147bps/day per active clip-slot; N=4
cells ≈ -565 to -719 JPY over up to 4 slots/side ≈ -13 to -16bps/day per unit of capacity. **This is 1–2 orders of
magnitude smaller than the claimed -516..-7,141bps/day range** — I cannot tell what denominator (margin at 2x
leverage? per-trade instead of per-day? a single grid slot's committed capital?) produces numbers that large from the
data or config files available to me; see 前提の誤り.

**4. Relative vs absolute.** Volatility-tercile split (fast30s/N1/off): low-vol tercile mean -45 JPY/day, mid -111,
high -354 — losses scale with realized volatility. corr(|day net drift bps|, daily PnL) = -0.64 across the 16 days —
bigger trend days → bigger losses, matching a mean-reversion-in-a-trend failure mode.

**5. Definition side-effects.** My clip-count cap (N) and gate both only restrict OPENING new clips, never closing —
this is a design choice that could not be verified against the original; a design that also throttles closes could
change the exception count (item 1) without changing the sign.

**6. Data validity.** 6/16 days truncated (see item 1); no bitFlyer 19:00–19:10 UTC maintenance gap was visible as a
literal gap in the ticker files I checked (ticker rows just stop updating during flat quotes, per schema's dedup
note) — I did not specifically isolate that window. No duplicate timestamps survived the resample.

**7. Selection contamination.** 8 cells is a genuinely small grid (3 free binary/binary/2-valued knobs); under my own
construction all 8 cell means still land negative, so a shuffle-based permutation test on the cell selection was not
run (out of budget) — flagged as unverified, not as passing.

**8. Simplest alternative explanation.** Trend/net-drift (item 2/4) explains most, not all, of the loss; residual
~-32 JPY/day even at zero net drift agrees directionally with the venue-survey's own bf_fxbtc "virtual touch quote"
measurement (next item) — i.e., touch-based maker fills lose money on this venue even absent trend.

**9. Consistency.** backtest_data/venue_survey_20260827/FINAL.txt (pre-computed by the survey, not by my script)
reports, for bf_fxbtc touch quotes over its 4h window: placed=14,400, fills=6,260 (43.5%), captured spread
+0.413bps, 5s-adverse-move -1.078bps, net **-0.665bps [CI95 -0.773,-0.568]** — independently negative and
significant, agreeing in sign with both my main result and my zero-drift control. The Binance file
(backtest_data/binance_BTCUSDT_1m_210d_20260820.csv.gz) does **not** actually cover the 16-day tape window: it ends
2026-08-20 11:36 UTC, ~11.6h into day 1 of 16 — I could not use it for a same-window cross-instrument check (data-path
problem, not a result).

**10. Falsification / MDE.** Pooled n=128, t=-6.70 → highly powered to reject "no effect" at this n. Per-cell (n=16,
df=15, t_crit≈2.13, 80%-power MDE≈2.97·SE): N=1 cells SE≈51 JPY → MDE≈151 JPY/day (observed -132..-162, at the edge
of individual-cell significance); N=4 cells SE≈205 JPY → MDE≈609 JPY/day (observed -435..-719, individually
significant). Falsification sentence: if the true daily edge were ≥0, we should see ≥50% of daily values positive and
a pooled t not reliably negative — neither holds here.

**Claimed vs recomputed:**
| | claimed | recomputed (own cells) |
|---|---|---|
| cells negative | 8/8 | 8/8 (means) |
| daily values negative | 56/56 (100%) | 95/128 (74%); 8-9/10 on full-day subset |
| magnitude | -516..-7,141 bps/day | -13..-147 bps/day (per unit of capacity) |

Verdict: 数値差異(結論維持)

## PR5

PR5 is the PREREG gate decision citing R22 as its basis for rejecting the M2 8-cell design. Since R22's directional
conclusion (all 8 self-defined cells net-negative, statistically significant, corroborated by the independent
venue-survey touch-fill measurement) reproduces even though the literal 100%-negative claim and the bps magnitude do
not, a rejection decision built on R22 is not overturned by this audit — I find no basis to call the feasibility
verdict wrong, only to note that the rejection's supporting numbers are less extreme under an independent
implementation. I did not have access to PR5's own text/thresholds (PREREG files are forbidden), so I can only judge
it through R22's inherited numbers, not re-derive its gate logic itself.

Verdict: 数値差異(結論維持)

## 前提の誤り

- premise: claimed magnitude -516..-7,141 bps/day | source: R22 row | data shows: my own per-notional accounting
  gives -13..-147 bps/day, 1-2 orders of magnitude smaller | direction of bias: unknown without the original capital
  denominator — could indicate a much smaller capital base (e.g. per-slot margin) was used, which would inflate bps
  figures without changing JPY reality | inherits to: PR5 and any other claim quoting this bps range verbatim.
- premise: "56 daily values all negative, 0 exceptions" | source: R22 row | data shows: 74% negative (95/128) under
  my construction, with 3-6/16 positive days per cell | direction of bias: the claim reads as stronger/more uniform
  than what a differently-specified but reasonable grid MM produces | inherits to: PR5's feasibility rejection
  (weakens the "every cell every day" framing but not the mean-negative conclusion).
- premise: funding/swap cost | source: config/products.yaml swap_daily_pct=0.06%/day | data shows: not modeled in
  either my sim or (unverifiably) in R22's own figure | direction of bias: omission would make BOTH my numbers and
  a comparable original figure slightly LESS negative than reality if clips are held across 05/13/21 UTC funding
  times | inherits to: any bps/day figure for inventory-holding strategies on FX_BTC_JPY.
- premise: 16-day tape is a clean daily panel | source: packet I row ("16 日") | data shows: 6/16 days are partial
  (truncated WS capture, a documented extract_tape.py defect) | direction of bias: reduces effective sample and could
  skew which days are represented (e.g. day cut off before a reversal) | inherits to: any packet-I-adjacent claim
  using a "16-day" or "56 = 8×7" framing without stating which 7 days.
- premise: binance_BTCUSDT_1m_210d file is usable as a same-window cross-check for this packet | source: packet I
  row lists it alongside the 16-day tape | data shows: the file ends 2026-08-20 11:36 UTC, covering ~11.6h of the
  16-day window, not the full period | direction of bias: none on R22 itself, but any claim relying on this file for
  a 16-day cross-instrument consistency check cannot actually do so | inherits to: any other packet citing this same
  binance file for period-matched comparison to the paper_logs/tape window.
