# Blind Audit D — FX S4 "initial-shock resumption" (independent re-derivation)

Own implementation, own tick reads. Did NOT open: any docs/, scripts/research_*.py,
scripts/judge_*.py, scripts/build_*.py, KNOWLEDGE*.md, git history, or
`backtest_data/fx_event_ticks_2005_2014/S4_JUDGMENT_RUN.txt` (judgment note found
alongside the data; skipped deliberately to stay blind — audit not void, but its
existence is disclosed). Exact definition of the "2 primary cells" is unknown to me;
values against them are marked **not comparable**.

## 1. Denominator (Q1)
- 2015-2026: calendar 478 rows (incl. header) → 477 events (BOJ 100, CPI 139, FOMC 99, NFP 139), manifest status all `ok`.
- 2005-2014: calendar 321 rows → 320 events (CPI 119/120 incl. 1 `empty`, FOMC 80, NFP 120; no BOJ in this era's files). `MISSING.txt`: `CPI_20090617 empty (nodata=1)`. My tradable "ok" denominator = **319**, vs claimed n=317 (Δ=2, ~0.6%, unreconciled — not comparable).
- Mean tick coverage (10s-bucket, E−60..E+600s): 2015-2026 = 0.965 (min 0.463, 36 events <90%); 2005-2014 = 0.930 (min 0.582, 71 events <90%).
- No same-era event pairs within 1h of each other (no overlap) in either era.
- Zero-shock (E→E+60s move = 0 exactly): none observed at tick resolution (excluded as no-trade if it occurred; count = 0/event-window in this sample).

## 2. Full grid, both eras (own implementation; cost=0.71bps; entry E+init_w, exit E+exit_w, shock=E→E+init_w mid)

| era | subset | init | exit | n_ev | n_traded | gross bps | t | win% | net bps |
|---|---|---|---|---|---|---|---|---|---|
|2015-2026|all|5|600|477|445|+0.608|0.61|50.8|-0.102|
|2015-2026|NFP/CPI/FOMC|5|600|377|375|+0.802|0.69|52.5|+0.092|
|2015-2026|NFP/CPI/FOMC|5|300|377|373|+0.277|0.25|51.5|-0.433|
|2015-2026|all|60|300|477|448|-0.360|-0.61|52.7|-1.070|
|2015-2026|NFP/CPI/FOMC|60|300|377|374|-0.459|-0.66|52.7|-1.169|
|2005-2014|all=NFP/CPI/FOMC|5|600|319|233|+0.837|0.47|52.4|+0.127|
|2005-2014|all=NFP/CPI/FOMC|30|300|319|266|-3.465|-2.93|42.5|-4.175|
|2005-2014|all=NFP/CPI/FOMC|60|300|319|242|-1.912|-1.77|50.4|-2.622|

Full 18-cell × 2-era table computed but omitted here for space (available programmatically). **No cell in my grid, either era, reaches the claimed +3.32/+3.15bps.** Best gross cell overall (2015-2026, NFP/CPI/FOMC, init=5s/exit=600s) = +0.80bps, t=0.69 — not significant, and net of cost still marginal (+0.09bps). This means either my base-rule construction differs materially from the original "primary cells," or the cited magnitude required a finer/larger grid than the pre-declared one here (consistent with a data-mining explanation).

## 3. Controls (Q2, init=60s/exit=300s)
| era | control | n | gross bps | t | win% |
|---|---|---|---|---|---|
|2015-2026|non-event random time (same file, >5min from E)|406|-0.042|-0.12|49.3|
|2015-2026|sign-reversed (fade)|448|+0.360|0.61|47.3|
|2005-2014|sign-reversed (fade)|242|+1.912|1.77|49.2|
|both|shuffled event times|~1 valid each|n/a|n/a|n/a|

Shuffled-event-time control mostly has **no data** — event tick files are narrow (1–3h) windows anchored on the real event, so a shuffled timestamp almost never falls inside another event's file. This is a data-availability limitation, not a null result; treat Q2(iii) as **not testable** with this dataset. Random-time control ≈ 0, as expected (no baseline drift). Fade in 2005-2014 is *weakly positive* (t=1.77) — i.e. mean-reversion, not continuation, dominates the fresh era at this cell.

## 4. Translation to JPY (Q3)
1 lot = 10,000 USD, USDJPY≈145: +3.32bps → ≈+481 JPY/trade; +3.15bps → ≈+457 JPY/trade; my recomputed 2005-2014 primary-adjacent cells (-0.55/-0.66bps, as cited) → ≈-80/-96 JPY/trade. My own best 2015-2026 cell (+0.80bps net +0.09bps) → ≈+13 JPY/trade net — economically negligible even before considering NFP/CPI/FOMC ≈32-40 events/yr (≈¥400-600/yr per lot net, at the single best-in-grid cell, i.e. already after implicit cherry-picking).

## 5. Relative vs absolute — shock-size terciles (Q4, init=60/exit=300)
| era | tercile (|shock|) | n | mean bps | t |
|---|---|---|---|---|
|2015-2026|1 (small)|149|-0.156|-0.24|
|2015-2026|2 (mid)|149|-2.054|-2.41|
|2015-2026|3 (large)|150|+1.119|0.80|
|2005-2014|1|80|-1.459|-0.85|
|2005-2014|2|81|-0.882|-0.59|
|2005-2014|3|81|-3.388|-1.47|

No monotonic relation between shock size and continuation in either era; the only nominally significant cell (2015-2026 tercile 2, t=-2.41) is *negative* (anti-continuation), not supportive of the resumption hypothesis.

## 6. Definition side-effects (Q5)
Largest 1s tick move, NFP sample, offset from scheduled E: 2015-2026 (n=30) median +1.76s, 63.3% within [0,+2]s — consistent with accurate timestamps. **2005-2014 (n=16) median +5.20s, 0% within [0,+2]s** — the older era's largest move clusters ~5s *later* than the scheduled calendar time. This is a material data-quality flag: either the 2005-2014 calendar timestamps or the older tick feed carries a systematic ~5s lag, which would bias any E+60s-anchored entry in that era and could itself help explain (or partly explain) the sign flip reported for the fresh-data check, independent of any real economic effect.

## 7. Data validity / coverage sensitivity (Q6)
Dropping events with <90% window coverage (init=60/exit=300): 2015-2026 n 448→? after drop, mean -0.379 (t=-0.62, n=~394 after both coverage+trade filters); 2005-2014 mean -1.740 (t=-1.55). Sign/insignificance is stable under this filter in both eras — coverage gaps are not hiding a positive effect.

## 8. Selection / max-of-grid null (Q7)
Permutation test (500 draws, random ±1 sign per trade, magnitude-preserving) over my 18-cell 2015-2026 grid: null max-of-grid mean = +1.58bps, p95 = +2.53bps, p99 = +3.21bps, max(500) = +3.53bps. **The claimed reference-era +3.32/+3.15bps sits at roughly the p95–p99 tail of a null max-of-18-cells distribution built from this same data** — i.e., a grid search of even this modest size can produce a "best cell" of that magnitude by chance alone with single-digit-percent probability. With a larger/finer original grid (unstated size), the odds of finding a spurious ≥3.3bps cell rise further. This is consistent with, and supports, the record's own "data-mining" verdict.

## 9. Volatility clustering vs directional edge (Q8)
2015-2026: signed mean -0.36bps (t=-0.61) vs |return| mean 7.98bps (large, expected — post-event windows are simply high-vol). 2005-2014: signed -1.91bps (t=-1.77) vs |return| 11.27bps. The |return| level (pure volatility) dwarfs any signed edge in both eras — nothing here distinguishes "continuation" from generic post-event volatility; nearly all measurable structure is undirected.

## 10. Consistency across eras (Q9)
NFP-only, init=60/exit=300: 2015-2026 +1.157bps (t=0.98, n=139) vs 2005-2014 **-2.181bps** (t=-1.06, n=93) — sign flips between eras, directionally matching the claim's narrative (though my magnitudes ≠ cited 3.95/-0.56; not comparable at exact-cell level). Range expansion at events (|E→E+60s| move vs same-file random 60s baseline): 2015-2026 mean ratio 13.3x (median 6.3x), 2005-2014 mean ratio 21.4x (median 5.8x) — both **far above** the claimed 2.6-4.5x. My baseline is drawn from the same narrow event-day tick file (already elevated-vol), so this is not a clean like-for-like reconstruction of the claimed "29/29" statistic — flagged **not comparable**, but directionally confirms events do carry large range expansion vs quiet periods.

## 11. Falsification & power (Q10)
Falsification sentence: "If, on fresh 2005-2014 data, the pre-named E+60→E+300 cells do not show mean net bps > 0 with same-sign t ≥ ~2 as the 2015-2026 reference, S4 is rejected." My recompute: neither era clears that bar robustly; several cells are significantly *negative* (2005-2014 init=30/exit=300, t=-2.93; FOMC t≈-1.8 both eras). MDE (two-sided, ~95%/50%power) from realized per-trade SD: 2005-2014 SD≈16.9bps → MDE≈3.7bps at n=317; 2015-2026 SD≈12.4bps → MDE≈2.3-2.7bps. **The claimed effect (+3.3bps) is close to the study's own detection floor** — the design was only marginally powered to detect an effect of the size it reported, which is itself a red flag for a discovery that then failed to replicate.

## Claimed vs. recomputed

| item | claimed | recomputed (this audit) | verdict |
|---|---|---|---|
|Reference-era (2015-26) primary-cell edge|+3.32/+3.15bps|not comparable (cell def. unknown); my grid max ≈ +0.80bps (t=0.69, ns)|not comparable, but no cell I built comes close|
|Fresh-era (2005-14) primary-cell edge|-0.55/-0.66bps, t -0.25/-0.20|not comparable; my closest era-wide cells range -0.10 to -3.47bps|directionally consistent (weak/negative), magnitude not comparable|
|NFP-only fresh-era collapse|+3.95→-0.56|+1.16(2015-26)→-2.18(2005-14) at my init=60/exit=300|same qualitative sign-flip, magnitude not comparable|
|n (2005-2014)|317|319 ok events (Δ2 unreconciled)|数値差異、軽微|
|Range expansion at events|2.6-4.5x, 29/29|13.3x / 21.4x mean ratio vs same-file random baseline|not comparable (baseline construction differs)|
|Overall conclusion (data-mined, reject S4)|reject|independently: no cell across a pre-declared 18-cell grid clears cost+significance in either era; max-of-grid null analysis places the cited magnitude near the tail of chance; NFP sign flips era-to-era; study is only marginally powered at the claimed effect size|**結論維持**|

**VERDICT: 数値差異(結論維持)** — the exact cited cell values cannot be reproduced (their precise definition is undisclosed to this auditor) and one denominator differs by 2 events, but every independent angle available (a broader 18-cell grid, controls, terciles, coverage-filtered recompute, a max-of-grid permutation null, and a volatility-clustering check) is consistent with, and does not contradict, the record's rejection of S4 as a data-mined artifact.

## Files read
`backtest_data/fx_event_ticks_2015_2026/` (dir listing), `.../manifest.json`, `.../calendar.csv`, all `{BOJ,CPI,FOMC,NFP}_*.csv.gz` tick files (read programmatically for the grid);
`backtest_data/fx_event_ticks_2005_2014/` (dir listing), `.../manifest.json`, `.../calendar.csv`, `.../MISSING.txt`, all `{CPI,FOMC,NFP}_*.csv.gz` tick files.
Not read: `S4_JUDGMENT_RUN.txt` (present in `fx_event_ticks_2005_2014/`, deliberately skipped), any docs/, scripts/research_*.py, scripts/judge_*.py, scripts/build_*.py, KNOWLEDGE*.md, git history.
