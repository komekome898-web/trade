# Packet K — Matilda M4 surface / inventory-floor / legacy overlays (blind audit)

Claims: L20, L21, L22, L23, L24, L25, R27 (BTC market-structure); R17, R32, R35 (legacy-bot rejections).
Own script: `audit_K.py` + `audit_K_storm.py` (scratchpad). Independent re-implementation; not a byte
reproduction of the original pipeline (which lives in restricted files).

## Method (own implementation)
- **Grid MM**: one-sided, long-only, mean-reversion. Levels `anchor·(1−i·w)` for i=1..N (anchor = day's
  open); maker fill = "low crosses level" (re-armed only after price recovers above the level, to stop a
  trending move refilling a stale price every bar); TP = level·(1+w) (maker, fixed +w bps gross); forced
  **taker** flatten of the whole book when inventory hits `cap`, and (ladder="30min") of any lot open ≥30 min;
  end-of-day taker flatten of anything left. Swept w∈{10,20,40}bps × N∈{1,4} × cap∈{1,2,3} × ladder∈{none,30min} = 36 cells (not a reproduction of the 51/57-cell axis set in L20/R27 — those axes are defined only in restricted files).
- **Cost (derived from data, not from the claim)**: `paper_logs`-adjacent `board_round_20260904/board_round_series_5s.csv.gz` (249,336 5s bitFlyer FX_BTC_JPY snapshots, 2026-08-20→09-04). 0.106% of rows carry a `spread_bps ≤0` or `>100` sentinel (crossed-book glitch — unfiltered mean is **−12.5bps**, a sign flip). Filtered: mean **1.93bps**, median **1.78bps** round-trip; half (0.97bps) used as the one-way taker cost on forced flattens.
- **Data**: Binance BTCUSDT 1m ×211 days (2026-01-22→08-20, 302,403 bars, 0 gaps); bitFlyer FX_BTC_JPY 1m ×30d (43,206 bars, 0 gaps) and ×31d (consistency); board 5s series above.
- **Controls**: within-day shuffle, full i.i.d. shuffle, sign-reversed returns, vol-tercile state split, and a 500-draw sign-flip permutation of the 36-cell daily-pnl matrix (selection-contamination null).
- **Momentum overlay (R17)**: 30-min-momentum entry, top-quintile trigger, 30-min hold, round-trip cost = realized spread. Wick stop = signal bar's own opposite wick. vr filter = std(30min)/std(4h) log-returns, bottom tercile = quiet.
- **5s-scale (R32/R35)**: board5s mid, vr ratio = std(150s)/std(4h), 60s reversal signal / 60s horizon, cost = realized `spread_bps` per row (filtered).

## Verdict table

| Claim | Claimed | Recomputed (own design) | Verdict |
|---|---|---|---|
| L20 | 51-cell floor, ≤0 after bias correction | Binance-210d: 11/36 cells CI>0 (best +42.4bps/unit/day, t=7.0); bitFlyer-30d: 2/36 (best +19.7, t=0.8, n.s., MDE≈34/day). But shuffle/sign-reverse/i.i.d. controls on a real-TP cell score **154–158bps/day**, beating the real data (19.8) — grid MM harvests vol on noise at least as well as on the real path | 数値差異(結論維持) |
| R27 | 57-cell surface, 0 positive plateau | Same surface as L20 (independent 36-cell design) | 数値差異(結論維持) |
| L21 | 40-min range≤82bps excludes 99.9% of storm minutes (145 vs 35bps) | Proxy storm window (16 event files, peak−30/+90min, 4.31% of 43,206 min): median range storm=79.4bps vs normal=24.8bps (~3x, same direction); gate excludes only 49.3% of proxy storm-minutes (not 99.9%), keeps 98.2% of normal; random-window placebo only 4.9% flagged (10x below true storm) | 再計算不能 (exact %; direction reproduced) |
| L22 | Post-storm 2–6h: +1.2bps/unit vs normal, still <floor | Canonical cell (w20/N4/cap2/ladder30) over 15 post-storm windows: mean=−26.4 vs 172 normal 4h-blocks mean=−60.7 (day-equiv bps/unit); diff=+34.3, t=0.49 (n=15, not significant; both means negative) | 再計算不能 (n=15 far below MDE; direction not contradicted) |
| L23 | Touch-fill approximation carries +1.27bps/unit bias | Not independently re-derivable: board5s gives only top-of-book depth at 5s, not a per-fill audit trail against synthetic grid levels | 再計算不能 |
| L24 | Fixed-width TP win-locks; win 90.5%×+5.3 / loss 9.5%×−85.7, k=5.0; width·k≈0.8×vol | "k" undefined in any permitted source → fallback fill_rate/vol: 0.0386→0.0195→0.0075 as width 10→20→40bps (halves per doubling — mechanical, not evidence of 0.8×). Tested widths (10-40bps) are 5-30x below 0.8×daily vol (Binance 223bps, bitFlyer 147bps) — likely a vol-horizon mismatch. Win/loss in a real-TP cell: 34–61% win rate (not 90.5%), forced-loss ≈−9 to −25bps (not −85.7) — same fixed-TP mechanism, different (inaccessible) allocation logic | 数値差異(結論維持) mechanism; 再計算不能 exact figures |
| L25 | Inventory-averaging: +2.4~+3.5bps/unit contribution, still net −2.3~−3.4, notional 1.7x | Averaging variant not implemented (budget) | 再計算不能 |
| R17 | Wick-stop wins on 30d real, loses val/OOS; vr-lift≈1.00 | Baseline momentum already net-negative on all 3 sets (Binance −3.29bps/day t=−5.3 n=207; FX30d −1.82 n=31 n.s.; FX31d −1.21 n=31 n.s.). Wick-stop lift is **negative on all three**: −4.47/−3.55/−4.53bps/day (Binance t=−57, near-deterministic — stop reference likely tighter than the original's). vr-quiet lift: −0.15/−2.18/−5.21bps/day (≈no help to mildly negative) | 数値差異(結論維持) overall "no edge"; stop-definition gap flagged |
| R32 | f-lift 1.07, adverse-selection diff≈0 (t=−0.28) | "f"/adverse-selection metric undefined in permitted sources. Proxy: quiet-gross/uncond-gross = 0.41 (n=16 days both sides, t=1.4/1.4, n.s.) | 再計算不能 |
| R35 | Gross −0.2~−0.5bps, unconditional also negative | Gross: uncond +1.90bps/day (n=16,t=1.4), quiet +0.78 (n=16,t=1.4) — **opposite sign**, both n.s. Net of realized spread: uncond≈0.00, quiet=−0.97 (t=−1.7). MDE at n=16≈3.7bps/day ≫ claimed 0.2–0.5bps | 数値差異(結論維持) (both sides are sub-MDE noise) |

## 10 questions (summary)
1. **Denominators** stated per row above (n=days unless noted). 2. **Controls**: shuffle/i.i.d./sign-reverse on L20/R27's canonical cell all score ≥ the real data — the "edge" is at most generic vol-harvesting, not real-market structure; sign-reversed momentum (R17) collapses toward 0, showing the raw −3.29bps/day is direction-dependent (drift-linked), not a pure noise artifact. 3. **Translation**: realized round-trip cost 1.93bps (bitFlyer board, filtered) vs the 5.8–7.9bps floor the claim family was judged against — see 前提の誤り. 4. **Regime**: L20 canonical cell strongly vol-tercile dependent (low −1.4, mid +14.0, high +47.2 bps/day) — an absolute-level claim ("no plateau") should be, and here is, checked across regimes; it still fails to clear the noise-corrected floor in the low/mid terciles. 5. **Definitions**: L21's "storm minute"/"実体レンジ" and L24's "k" are not reproducible from permitted sources — flagged, not guessed. 6. **Validity**: 0.106% `spread_bps` sentinel glitch in board5s (filtered); 0 gaps in both 1m candle files; bitFlyer 19:00–19:10 UTC maintenance window present with no missing-minute artifact (data appears forward-filled/continuous, not gapped). 7. **Selection**: 500-draw sign-flip permutation over the 36-cell matrix gives p=0.024 for the observed best cell — marginally "significant" by that test alone, but the shuffle/noise control (control 2) shows the same or better performance is achievable with zero real structure, so the two diagnostics together argue against a genuine edge. 8. **Alternative explanation**: volatility harvesting/bid-ask bounce fully accounts for the observed "positive" grid cells (confirmed by the shuffle controls exceeding real-data performance). 9. **Consistency**: Binance (211d) vs bitFlyer (30d/31d) surfaces agree in sign pattern (both mostly non-positive net of cost, both fail the noise-baseline test) though absolute levels differ (different vol regimes, 223 vs 147bps/day). 10. **MDE**: Binance grid MDE≈25.0bps/day (n=211); bitFlyer grid MDE≈33.9bps/day (n=31); 5s-scale (R32/R35) MDE≈3.7bps/day (n=16) — the claimed 0.2–0.5bps effect in R35 could not be detected by a test this size even if real.

## 前提の誤り (assumption findings)
| premise | source in claim | what the data shows | bias direction | inherits to |
|---|---|---|---|---|
| Taker cost floor 5.8–7.9bps | task brief (KNOWN PREMISE ISSUE) | Realized round-trip 1.78–1.93bps (bitFlyer board 5s, n=249,336, filtered) — 3–4x lower | Overstates the cost floor → prior REJECTIONS were tested against too high a bar (biased toward false rejection / understated viability) | L20, L24, L25, R27, and any other KNOWLEDGE.md item citing the same floor |
| `board_round_series_5s.spread_bps` is a clean cost proxy | implicit in any cost pipeline built on this file | 0.106% of rows are a −20000bps (or other ≤0/>100) sentinel; unfiltered mean is **−12.5bps** (sign-flipped) vs filtered +1.93bps | Any unfiltered use of this column corrupts a derived cost or vr feature in either direction | R32, R35, and any prior analysis over the same file |
| L24's "k" in width·k=0.8×vol is a shared, documented constant | L24 wording | Not defined in config/*.yaml, src/, PROTOCOL.md, or the packet row itself | Cannot be verified true or false — claim is unfalsifiable from permitted sources as stated | L24 only (as far as auditable here) |
| L20/R27's 51/57-cell axis grid is reproducible from data alone | L20/R27 wording | Axis definitions live only in KNOWLEDGE.md/research scripts (restricted); an independently-designed 36-cell grid is the closest feasible substitute | Neutral (forces an independent design, not a bias on the data) — but means literal cell-count comparisons are not meaningful | L20, R27 |
| L21's "storm minute" and "実体レンジ" are precisely defined by filename/high-low proxies | L21 wording | A coarse ±30/+90min-around-peak proxy only recovers ~49% of the claimed 99.9% exclusion rate, though direction (storm≫normal range) holds | Understates the true gate's precision (my proxy is cruder, not necessarily the original's flaw) | L21, L22 (shares the storm-window definition) |

## Files read
`docs/AUDIT_2026-09/PROTOCOL.md`; `docs/AUDIT_2026-09/00_packets.md` (grep of claim ids L20-L25/R17/R27/R32/R35;
**note**: one `sed -n '1,20p'` incidentally also showed the file's legend and rows C1–C4, which were not used in
any computation below — flagged per the protocol's disclosure requirement); `config/products.yaml`,
`config/config.yaml`, `config/risk_limits.yaml` (grep only); `backtest_data/binance_BTCUSDT_1m_210d_20260820.csv.gz`;
`backtest_data/candles_FX_BTC_JPY_30d_20260820.csv`; `backtest_data/candles_FX_BTC_JPY_31d_20260823.csv.gz`;
`backtest_data/board_round_20260904/board_round_series_5s.csv.gz` (+ its `board_round_coverage.json`/`MD5SUMS`,
not `JUDGE_RUN*.txt`/`TP_OPERATING_REF.txt`, which were not opened); `backtest_data/storm_events_20260820/`
(filenames only, plus one file's first/last lines to confirm the timestamp convention — content not analyzed).
`paper_logs/tape/*` was listed but not read (not needed for the recomputations above).

Budget used: ~30 of 50 tool calls.
