# AJ2 — second blind auditor report (packet AJ)

Files read: docs/AUDIT_2026-09/PROTOCOL.md; docs/AUDIT_2026-09/00_packets.md (grep rows for AJ, FXL9-14, FXR5/6/10, PR4, FXP1 only);
backtest_data/fx_event_ticks_2005_2014/{calendar.csv,manifest.json,MISSING.txt,*.csv.gz}; backtest_data/fx_event_ticks_2015_2026/{calendar.csv,manifest.json,*.csv.gz};
config/constants.yaml (gmo_fx_usdjpy.spread_sen / fee_yen only). Script: scratchpad/audit_AJ2.py (+ inline follow-ups, same methodology). No forbidden files opened (no *_RUN.txt/*JUDGMENT*.txt, no research_*/judge_*/build_*/paper_* scripts, no KNOWLEDGE/RESEARCH_REPORT/PREREG, no git history, no first auditor's report).

Data: USDJPY bid/ask tick files, ts_utc/bid/ask/bidvol/askvol. 2005-2014: CPI 119 files (+1 documented empty, CPI_20090617), FOMC 80, NFP 120 (calendar n=320). 2015-2026: BOJ 100, CPI 139, FOMC 99(97 usable), NFP 139 (calendar n=477, matches packet header n).

## FXL9 (median 1.7-1.9bps / p90 5-6bps at E+1s, ~35s recovery)
Denominator: US indicators only (NFP+CPI+FOMC), 2015-2026, n=375 (BOJ excluded — see FXL11/FXL12). Floor = median spread in [E-300s,E-60s).
Recomputed: s1(E+1s) median=1.71bps, p90=5.45bps — inside claimed ranges. Control: pre-window [-60,0) median=0.77bps (~2x floor, mild anticipatory widening) vs post peak [0,2s] median=3.87bps — the spike is genuinely concentrated post-E, not pre-event drift.
Recovery to ≤1.5×floor is highly sensitive to the "sustained" dwell time (undocumented in the claim): 3-tick sustain→median 17.4s; 1s sustain→45.7s; 2s→67.6s; 3s→87.4s; 5s→113.7s; 10s→185.8s. No single reasonable choice lands exactly on 35s (closest is ~0.5-1s dwell). Denominator for recovery: same n=375 in every variant.
Claimed vs recomputed: median 1.7-1.9 vs 1.71 (match); p90 5-6 vs 5.45 (match); recovery ~35s vs 17-186s across defs (definition-dependent, plausible but not pinned).
Verdict: 数値差異(結論維持)

## FXL10 (round-trip cost median 0.89-1.46bps = 1.3-2x floor)
Population unspecified ("S4"); tested both datasets and two cost definitions. (a) window-median spread over [E+5,E+300]: 2015-2026 US n=375 → 0.459bps, floor 0.359, ratio 1.28x; 2005-2014 all n=319 → 1.110bps, floor 0.935, ratio 1.19x. (b) endpoint half-spread-in/half-spread-out at E+5 & E+300: 2015-2026 (incl. BOJ) n=467 → 0.78bps, ratio 2.19x; 2005-2014 n=291 → 1.99bps, ratio 2.08x.
No combination simultaneously reproduces both the absolute 0.89-1.46bps band and the 1.3-2x ratio band; each definition matches one axis but not both. Direction (round-trip cost elevated above the pre-event floor for minutes after the event, order of magnitude sub-2bps) holds in all four re-derivations.
Verdict: 数値差異(結論維持)

## FXL11 (BOJ has no spread event; E+1s narrower than pre-announcement)
n=95 BOJ events with valid pre/post windows (2015-2026). Recomputed: median s1(nominal E+1s)=0.360bps vs median pre[-60,0)=0.338bps — s1 is very slightly *wider*, not narrower; only 38/95 (40%) individual events show narrowing.
BUT: calendar.csv documents, for every BOJ row, "RELEASE TIME DRIFTS -- time_utc is the nominal 11:30 JST anchor" — the timestamp used as E is admittedly not the true release time. Testing "narrower at E+1s" against a documented-drifting nominal anchor cannot validly confirm or refute the underlying claim (the nominal E+1s tick may fall before, at, or well after the true release).
Verdict: 再計算不能

## FXL12 (initial |E→E+5s| median: NFP17.7/CPI12.9/FOMC3.0/BOJ2.4bps)
Denominator 2015-2026: NFP n=139, CPI n=139, FOMC n=97, BOJ n=98(100 events, 98 with valid windows).
Recomputed: NFP 17.47 (match), CPI 12.91 (match), FOMC 3.59 (~20% high, same order), BOJ 0.23bps — an order of magnitude below the claimed 2.4bps. Extending the BOJ horizon out to E+600s only reaches a median of 1.88bps, still short of 2.4bps at just +5s. This tracks directly from FXL11's finding: BOJ's calendar timestamp is a documented nominal/drifting anchor, so a fixed "+5s" measured from it understates the true immediate reaction.
Verdict: 再現 (NFP/CPI), 数値差異(結論維持) (FOMC), 結論変更 (BOJ sub-figure — order-of-magnitude mismatch attributable to the nominal-time premise, see 前提の誤り)

## FXL13 (CPI "12日近傍" 20.9%; NFP first-Friday 81.3%; t(477件))
Denominators: CPI n=139, NFP n=139 (both subsets of the 477-event 2015-2026 calendar named in the row).
NFP: exact-first-Friday-of-month match = 113/139 = 81.3% — exact reproduction.
CPI: tried day==12 (26/139=18.7%), |day-12|≤1 (48.2%), |day-12|≤2 (77.0%). None hits 20.9% exactly; closest is exact-day-12 (18.7%, ~2pp / 3 events below the claimed 29/139). Direction and rough magnitude (~19-21% vs NFP's ~81%) confirmed; exact rule/cutoff not recoverable from data alone.
Verdict: 再現 (NFP), 数値差異(結論維持) (CPI)

## FXL14 (FOMC statement time irregular 2019-20: 6 events; BOJ time column nominal)
Denominator: FOMC 2019-2020 rows in 2015-2026 calendar, n=21.
Recomputed: exactly 6 rows flagged "[OFF-SCHEDULE TIME -- unscheduled/emergency statement]" (2019-10-11, 2020-03-03, 2020-03-15, 2020-03-23, 2020-03-31, 2020-08-27) — exact match. Every BOJ row (n=100) carries a "RELEASE TIME DRIFTS -- time_utc is the nominal ... anchor" note — exact match to the "時刻列は名目値" claim.
Verdict: 再現

## FXR5 (29/29 mechanism real, direction unreadable, 1-min bars)
Could not identify what constitutes the "29" cells/sub-tests from any file I am permitted to open (no such partition documented in config/*.yaml or the data manifests). As an independent, non-equivalent proxy, overall sign-continuation win rate (initial E→E+5s direction vs E+60→E+300s continuation, non-BOJ, 2015-2026, n=375) = 54.9% (206/375); 2005-2014 n=284 = 53.2% (151/284) — both close to chance, qualitatively consistent with "direction not reliably readable," but this does not verify the specific 29-cell figure.
Verdict: 再計算不能 (denominator/cell structure for "29" not recoverable from available data)

## FXR6 (zero-cost, all 12 configs ≈0 or below, config keeps flipping)
Reconstructed a plausible 3(entry: 1/5/10s)×4(exit: 60/180/300/600s)=12-configuration grid on the same continuation-direction logic, zero-cost, 2015-2026 non-BOJ (n≈360-376 per cell): means range -1.15 to +0.80bps, medians -0.93 to +0.72bps — mixed sign, clustered near zero, no config with a large or consistently positive edge; the two mildly positive cells (~0.7-0.8bps mean) are within one floor-spread's cost of the very transaction cost this test explicitly excludes. This is an independent reconstruction, not the original 12 configurations, so it corroborates the qualitative message without confirming the exact reported cell values.
Verdict: 数値差異(結論維持)

## FXR10 / PR4 (initial-direction continuation E+60→300s, S4, backward-fresh 2005-14 n=317, rejected, 2 main cells sign-reversed)
Recomputed on 2005-2014 (CPI+FOMC+NFP), requiring valid E, E+5s, E+60s, E+300s ticks and nonzero initial move: n=284 (claim states 317 — I could not recover the extra ~33 events without the original's exact validity filter; likely a looser tick-availability tolerance). Overall win rate (same-sign initial-move vs continuation) = 53.2% (151/284), z≈1.07 vs 50% (not significant) — consistent with the claimed rejection (no usable edge).
By type: NFP 55.7% (n=106), CPI 58.5% (n=106), FOMC 41.7% (n=72, i.e. *below* 50%, a sign reversal). Only one clearly-reversed cell was reproducible this way, not the claimed two, but the qualitative picture (weak/no continuation, at least one cell flipped sign) matches. As a cross-check, the same test on 2015-2026 (the presumed "front"/development sample) gives 54.9% (n=375, z≈1.91) — itself only borderline, supporting that the underlying effect was never robust even where it was found, which is consistent with an out-of-sample rejection.
Falsification/MDE: at n=284, SE≈2.97pp; an 80%-power two-sided MDE is roughly ±8-9pp around 50%. The observed edge (3.2pp) is well under this MDE, so this test could not have reliably detected even a moderate (5-8pp) true edge — the rejection is defensible but the population (n≈284-317) was not large enough to rule out a small residual effect.
Verdict: 再現 (rejection direction and near-chance magnitude confirmed); n and "2 cells" not exactly reproduced — 数値差異(結論維持) on those specifics.

## FXP1 (GBP/JPY robustness check frozen — target strategy vanished per prior report)
Packet marks data as n/a; this is a procedural/status claim (a decision to freeze work), not a numeric one, and no GBP/JPY tick data exists in the directories this packet cites to test anything empirically. My own FXR10/PR4 recomputation independently supports that the underlying S4 signal did not survive an out-of-sample test, which is at least consistent with a decision to freeze downstream robustness work, but I cannot verify the freeze decision itself from data.
Verdict: 判定不能

## 前提の誤り

1. **BOJ timestamp is a documented nominal anchor, not the true release time** | source: calendar.csv note "RELEASE TIME DRIFTS -- time_utc is the nominal 11:30 JST anchor" (every BOJ row, 2015-2026) | data shows: using this nominal time, BOJ shows no clean E+1s spread explosion (FXL11) and a 10x-undersized initial move at E+5s (FXL12: 0.23 vs claimed 2.4bps, still only 1.88bps even out to +600s) | bias: any BOJ-timed statistic computed against the nominal anchor is biased toward "no effect" / understated magnitude, i.e. FXL12's BOJ figure and FXL11's comparison cannot be taken at face value from this calendar alone | inherits: every claim in this packet (and any future one) that times an effect off the BOJ nominal anchor in this calendar file, e.g. any "BOJ reaction speed/size" statistic.

2. **Retail cost constant used for JPY translation is explicitly unverified** | source: config/constants.yaml `gmo_fx_usdjpy.spread_sen` (0.2 sen, source_type: assumed, "unverified — egress blocked") | data shows: the tick-data-derived pre-event floor spread is ~0.35-0.36bps (2015-2026) to ~0.9-1.0bps (2005-2014) at typical USDJPY levels — a different order of magnitude / basis than the assumed 0.2-sen retail constant, and the two are not on record as reconciled | bias: any bps→JPY cost translation that reaches for `spread_sen` instead of the data-derived floor will misstate real trading cost by roughly 2-5x in an unknown direction (venue-dependent) | inherits: any claim in this or other packets that translates an FX-event bps figure into JPY cost/profit using the constants.yaml retail-spread assumption.

3. **"Recovery time" and "round-trip real cost" are free-parameter-sensitive constructs not pinned down in the claim text** | source: FXL9 ("~35秒"), FXL10 (0.89-1.46bps / 1.3-2x) | data shows: my own reasonable re-implementations span 17-186s for recovery and 0.46-1.99bps for round-trip cost depending only on an unstated dwell/window choice | bias: unknown/neutral — but it means the headline numbers are not independently reproducible without the exact operational definition, which should be pre-registered explicitly | inherits: any claim citing "recovery time" or "round-trip cost" for this event-tick family without stating the sustain window / cost formula.

4. **"29 cells" (FXR5) and the exact "12 configurations" (FXR6) are not documented in any file available to a blind auditor** | source: FXR5, FXR6 row text | data shows: no partition matching "29" is discoverable in config/*.yaml or the data manifests; I could only approximate FXR6's 12 with a self-chosen 3×4 grid | bias: unknown — these claims cannot be independently checked at the stated resolution, only proxied | inherits: any claim that cites "all N configurations/cells" without the grid being recorded in an auditor-readable location.

No other categories (populations, event definitions, tick-quality/gaps, timezone beyond the BOJ item above) showed a material discrepancy: NFP-first-Friday and FOMC-2019/20-irregularity reproduced exactly, and the one documented data gap (CPI_20090617, empty) is disclosed in MISSING.txt and excluded consistently.
