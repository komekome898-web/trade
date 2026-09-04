# Packet G — ONR (J-REIT overnight) — blind audit

Claim ids: JPL6, JPL7, JPP3, PR8, PR10, JPR8 (verbatim texts from `00_packets.md` §1.9/1.10/1.11, read via grep only).
Script: `scratchpad/audit_G.py` (independent re-implementation, no code from `scripts/research_*` opened).

## Claimed vs recomputed

| # | claim (paraphrase, id) | claimed | recomputed | verdict |
|---|---|---|---|---|
|1| JPP3: 298-day overlap, ETF overnight vs index overnight | ETF +9.2bps, index ≈0 | n=297 overlap dates: ETF onr mean=+9.19bps (t=4.13), index onr mean=−0.00bps (t=−0.00), gap=+9.19bps (t=4.48) | **再現** (n off by 1, immaterial) |
|2| PR10: overall judgment → 仮通過 via JPP3; 2011+ ETF level excluded as "汚染" | not usable for judgment | era table below shows a genuinely negative era (2016-2019, −1.48bps, t=−1.13) inside 2011+; instability is real, not just a labelling choice | **数値差異(結論維持)** — caution was warranted, exact "汚染" mechanism unverifiable here |
|3| PR8: forward paper ledger, n=1, frozen 2026-09-04 | n=1 | `paper_logs/onr_ledger.csv` has header row only (0 data rows); `onr_status.json`: `n_trades: 0, last_date: null` | **数値差異(結論維持 as "not yet started")** — but the specific "n=1" figure is wrong; see 前提の誤り |
|4| JPL7/JPR8: thin-ETF auction artifact inflates overnight (example 1311 Core30, ADV ¥0.3億/day) | thin → inflated overnight | 1311 not fetchable in this packet (not in the allowed fetch list); across 5 REIT-family ETFs actually tested (ADV ¥1.3×10⁸–1.7×10⁹, all ≫ 1311's ¥3×10⁷), corr(log ADV, mean_bps)=−0.11, n=5, non-monotonic (see table) | **再計算不能** for the cited instrument (1311); the general liquidity-scaling mechanism is **not confirmed** on the proxy set tested |
|5| JPL6: overnight premium positive market-wide (N225/TOPIX/JPX400/Growth250/REIT ETFs) | all positive | tested 7 of these: 1343,1345,1476,1488,1597 (REIT), 1321 (N225 proxy), 1306 (TOPIX) — **all 7 positive**, t = 3.16–9.89 | **再現 (partial)** — JPX400/Growth250 still untested (as claim itself flags) |

### Recomputed headline numbers (1343, denominator = trading days with valid open&close, |ln r|≤0.10)
- Full history 2008‑09‑17..2026‑09‑03: overnight n=4399, mean=+4.77bps/day, t=3.69, Sharpe(ann)=0.88. Day session (open→close) n=4402, mean=**−2.98bps**, t=−2.20 (opposite sign — see Q8).
- By era (n / mean bps / t): 2008‑11 792/+4.94/0.92 · 2012‑15 980/+3.85/1.79 · **2016‑19 999/−1.48/−1.13** · 2020‑23 977/+9.75/3.55 · 2024‑26 651/+8.10/5.09.
- Dividend-inclusive (36/55 ex-dates matched to a next-open row): n=4399, mean=+5.49bps, t=4.22 (vs +4.77bps raw, same n) — direction unchanged.

### Liquidity-artifact table (JPL7/JPR8 proxy test; 1311 itself unavailable)
| sym | mean_bps | t | n | ADV (¥, last 252d) |
|---|---|---|---|---|
|1343|4.77|3.69|4399|1.69e9|
|1345|4.52|4.58|3684|1.34e8|
|1476|11.99|9.89|2675|3.70e8|
|1488|10.03|8.30|2429|3.33e8|
|1597|7.06|7.41|3079|2.97e8|

corr(log ADV, mean_bps) across these 5 = **−0.11** (weak, wrong-signed-strength for a clean "thinner→bigger" story, n=5 too small for real inference; not monotonic: thinnest here, 1345, shows the *smallest* premium).

## Stale-open diagnostic (Q4/Q8, the core mechanism check)
- REIT: corr(1343 overnight, REIT-index overnight) = **0.580**; corr(1343 day, REIT-index day) = **0.847** (n=297 overlap). Overnight corr well below day corr.
- N225 control pair: corr(1321 overnight, ^N225 overnight) = **0.922**; corr(1321 day, ^N225 day) = **0.881** (n=3666/3665, full history). Overnight corr ≥ day corr — opposite pattern.
This asymmetry is specific to the REIT index pair, matches the manifest's own caveat ("index open is computed from constituents' first prints and may be stale"), and is the simplest alternative explanation for JPP3's "+9.2bps ETF vs ≈0 index" gap: part of it can be a REIT-index-construction artifact, not a pure ETF-specific premium.

## Controls (Q2)
- **Placebo** (close(t) paired with a *random* other day's open, not t+1): n=1454 survives the |r|≤0.10 filter (random pairing across years mostly produces >10% jumps, correctly dropped as non-comparable), mean=+7.37bps, **t=0.51 (not significant)** — vs the true date-adjacent pairing's t=3.69. Consistent with a real, date-specific structure rather than generic price-level noise.
- **State-conditional** (prior-day session direction): prior-day-up n=2297 mean=+6.19bps t=3.09; prior-day-down n=2102 mean=+3.22bps t=2.03. Sign unchanged in both states — not purely a momentum artifact.
- **Sign-reversed**: day-session return is −2.98bps (opposite sign, own t=−2.20) — i.e. this is *not* explained by a simple upward price drift bleeding into both sessions; overnight and day sessions move in opposite average directions, a genuine time-of-day split.

## Translation to money / cost (Q3)
- Fee assumption per task: commission ¥0 under SOR (not verified here, per instruction).
- Tick = ¥1 (verified: JPX product page, 1343 is a 1-unit-lot ETF, ¥1 tick at the ¥1,000–3,000 band). At the recent average 1343 price (¥2,067, last 252 sessions): **one-side tick ≈ 4.84bps; worst-case round-trip (both legs mis-rounded by a full tick) ≈ 9.68bps; expected round-trip under a half-tick average ≈ 4.8bps.**
- This is the **same order of magnitude as the full-history edge (4.77bps)** and **roughly half of the recent overlap-window edge (9.19bps)**. None of the six claim texts mention tick cost. A genuinely zero-commission SOR path still leaves the edge thin-to-negative once realistic auction rounding is priced in.
- JPY/unit: overlap-window edge ≈ ¥1.90/unit/event gross; full-history edge ≈ ¥0.99/unit/event gross — both comparable to or smaller than the tick-cost band above.

## MDE (Q10) and falsification
- Full sample: n=4399, daily sd=85.8bps → MDE (5% two-sided, 80% power) ≈ **3.62bps/day**. Observed 4.77bps clears this.
- Overlap gap: n=297, daily sd=35.4bps → MDE ≈ **5.75bps/day**. Observed gap 9.19bps clears this.
- Falsification: the claim is falsified if a fresh, date-adjacent close→open sample of comparable size (n≈300+) shows mean overnight ≤0 or the ETF−index gap ≤0; that has not happened in the tested windows, but it *did* happen for a multi-year era (2016‑2019, −1.48bps) inside the pre-2025 history, so absence-of-effect is a real, previously-observed outcome for this instrument, not a hypothetical.

## Consistency (Q9)
- Independent small dataset `data/onr/*.csv` (production/forward-tracking snapshot, most recent window, n=21 overlap days, 2026‑07‑24..2026‑09‑04): gap mean = **+7.58bps**, same sign and same order of magnitude as the 297-day backtest-snapshot gap (+9.19bps). Agrees in sign and rough magnitude — passes a basic consistency check, though both windows are the *same* recent regime (not an independent era).

## Data validity (Q6) / definition side-effects (Q5)
- 1343: 4 of 4409 rows dropped (open/close ≤0, listing-week no-trade prints); 5 more overnight obs dropped by the |ln r|>0.10 glitch filter. <0.2% of sample — immaterial.
- 1321: 255 of 4338 rows dropped (open=0 placeholder rows, concentrated in the earliest ~2009 period before Yahoo reports intraday open for this symbol) — 5.9% of history excluded; if those early days had systematically different true overnight behavior this is unrecoverable from this data source, and is a real (if modest) gap, not examined further here.
- Dividend matching only hit 36 of 55 ex-dates (index/date alignment gaps) — treated as a minor caveat, does not change sign or significance of the div-adjusted result.
- Zero-volume glitches, exchange maintenance windows, and reconnect issues are not applicable to daily OHLC snapshot data (no intraday feed used in this packet).

## Selection contamination (Q7)
- No free parameter was tuned by this audit (glitch threshold 0.10, era boundaries, and instrument list were fixed by the task/manifest, not chosen post-hoc from the results). The liquidity-scaling test (5 ETFs) is too small (n=5) to run a meaningful permutation search; flagged as underpowered rather than as evidence either way.

## Verdict
**再現** for JPP3's headline overlap gap (+9.2bps ETF vs ≈0 index, 297≈298 days) and for JPL6's cross-market positive-sign pattern on the 7 instruments testable here. **数値差異(結論維持)** for PR10's "2011+ excluded as contaminated" framing — the instability is real but the specific contamination mechanism is unverifiable from this packet's data alone; the stale REIT-index-open diagnostic is a strong alternative/contributing explanation for the ETF-vs-index gap itself. **再計算不能** for JPL7/JPR8's specific 1311 claim (no 1311 data available in this packet) — the liquidity-scaling mechanism is not confirmed on the 5-ETF proxy set tested and should be downgraded to **未検証** for the 1311-specific number until that instrument's data is fetched. PR8's "n=1" is simply wrong; the ledger is empty (n=0).

## 前提の誤り (assumption findings)
1. `paper_logs/onr_ledger.csv` has **0** data rows, `onr_status.json.n_trades=0`, not the "n=1" PR8/JPP3 assert | source: PR8, JPP3 | data: paper_logs/onr_ledger.csv, onr_status.json | bias: overstates forward-tracking progress (implies a first fill has already occurred; it has not) | inherits: any future claim that cites "the forward ledger shows a first data point."
2. TSE REIT Index full-window (2003→) daily data was never obtained (manifest, self-disclosed); all index-side numbers here rest on a 297-299-day 2025-06→2026-09 window only | source: JPP3, PR10 | data: manifest.md §"Judgment data ①" | bias: any claim implying the +9.2bps/≈0 pattern holds across the full 2008-2026 ETF history is unsupported — the ETF's own era table shows a negative era (2016-2019) that a full-window index comparison could not corroborate or refute | inherits: JPL6 (era-stability implied by "confirmed law"), PR10's own "2011+ excluded" caveat (can't be checked against index-level ground truth either).
3. The REIT index's overnight-vs-day correlation asymmetry (0.58 vs 0.85, vs 0.92/0.88 for the N225 control pair) indicates the index open used for the "index≈0" comparator may itself be stale, not a clean settlement price | source: JPP3, PR10, JPR8 (anything using this REIT index as "the" no-artifact benchmark) | data: recomputed here | bias: inflates confidence that the +9.2bps gap is a genuine ETF-specific/auction-capturable premium rather than partly a REIT-index-construction artifact | inherits: every claim that treats "ETF vs index gap" as clean evidence of an ETF-side effect (JPL6, JPP3, PR10).
4. Tick-rounding cost (~4.8-9.7bps round-trip at current price) is never stated in any of the six claim texts, and is the same order of magnitude as the measured edge | source: JPL7/JPR8 (cost discussion absent), JPP3/PR10 (仮通過 without this cost line) | data: recomputed from JPX tick table + recent 1343 price | bias: overstates net profitability of any live/forward implementation | inherits: PR8 forward-tracking (if its cost model omits ticks), any future LIVE go-decision citing JPP3's 仮通過.
5. JPL7/JPR8's specific example (1311, ADV ¥0.3億/day) has no data in this packet's fetch scope; the 5 REIT-family ETFs substituted here are all 4-56× more liquid than 1311 and show a weak, non-monotonic liquidity/premium relationship (corr=-0.11, n=5) | source: JPL7, JPR8 | data: this packet's Yahoo fetches | bias: neither confirms nor refutes the artifact claim; citing this packet as support for the 1311 number specifically would be an unverified extrapolation | inherits: any packet-H style cross-market artifact table that reuses this proxy set for the 1311 cell.

## Files read
docs/AUDIT_2026-09/PROTOCOL.md; docs/AUDIT_2026-09/00_packets.md (grep on claim ids only); backtest_data/reit_onr_20260904/{manifest.md,MD5SUMS,etf_1343_daily.csv,etf_1343_dividends.csv,etf_1321_daily.csv,reit_index_daily.csv} (directory listing only for ONR_RUN.txt — not opened, excluded per protocol); data/onr/{etf_1343_daily.csv,reit_index_daily.csv}; paper_logs/onr_ledger.csv; paper_logs/onr_status.json; config/*.yaml (grepped, no REIT/1343 hits); src/ (grepped for onr/1343/reit, no usable fee constants found); public Yahoo Finance chart API for 1345.T, 1476.T, 1488.T, 1597.T, 1306.T, ^N225 (fetched fresh, this session).
