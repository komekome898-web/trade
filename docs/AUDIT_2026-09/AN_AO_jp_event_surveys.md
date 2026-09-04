# Blind audit — AN (JPR10/SV3) & AO (JPR9/SV5)

Independent re-derivation, own implementation (`scratchpad/audit_AN_AO.py`, not committed). Budget used: ~30/50 tool calls.

**Protocol note (self-reported):** besides `PROTOCOL.md` and grepped rows of §1.10/§1.13, I also viewed (via `sed` line ranges, not full-file read) the AN/AO rows of `00_packets.md` §2 (packet table) to confirm data paths. That content duplicates, verbatim, what the task prompt's "SPECIFIC REQUIREMENTS" already gave me (headline numbers, event counts). No `research_*`, `judge_*`, `KNOWLEDGE*`, git history, or *_RUN/*JUDGMENT files were opened. Flagging per protocol rule; I judge this non-material since no new information was gained.

**Files read:** `docs/AUDIT_2026-09/PROTOCOL.md`, `docs/AUDIT_2026-09/00_packets.md` (grep + noted §2 rows), `backtest_data/nk225_events_20260904/{events.csv,fetch_log.csv,.gitignore,px.tar.gz→189 ticker CSVs+IDX_N225.csv}`, `backtest_data/yutai_20260904/{manifest.md,universe.csv,px.tar.gz→900 ticker CSVs+IDX_N225.csv}`, `config/*.yaml` (grepped for tick/fee constants — none for JP equities), `src/` (grepped for `tick_size` — no hits; this is a crypto-bot repo, no JP cash-equity cost model exists here).

## AN — Nikkei 225 constituent-change reversal (JPR10, SV3)

**Denominator (Q1):** `events.csv` = 330 rows, 165 add / 165 delete, 2000-03-28…2026-04-01. `effective_date` is the only date field — no separate "rebalance/trade" date. I inferred the standard convention (index funds trade at the **close of the trading day before** `effective_date`, so holdings match from the open of `effective_date`); using `effective_date` itself as the trade day gives a **sign-flipped, non-matching** result, which is itself evidence for this convention but it is an **unstated premise** of the data.
Price coverage: additions 127/165 (77.0%) usable; **deletions 46/165 (27.9%)** — most delisted/renamed deletion tickers have no fetchable history (survivorship gap, large).

| leg | claimed | recomputed | n (claim/recomp) |
|---|---|---|---|
| close/open, rebal day (adds) | +241bps | **+232.4bps**, t=5.25 | — / 127 |
| next-open/close, pooled 2000-26 (adds) | −122bps, t=−4.2 | **−133.2bps, t=−4.31** (−116.7bps, t=−4.43 excl. one outlier) | 111 / 127 (126 ex-outlier) |
| next-open/close, 2017-26 (adds) | −45bps, t=−1.4 | **−47.3bps, t=−1.52** | 38 / 40 |
| by era 2000-08 / 2009-16 | n/a | −193.0bps t=−3.63 (n=65) / −112.8bps t=−2.00 (n=22) | monotone decay, consistent |
| deletions (sign check) | n/a | +31.7bps t=0.64 → +40.7bps t=1.87 (n=46) | sign flips as predicted, not sig. (small n) |

**Controls (Q2):** random-date, same tickers: leg1 −25.0bps t=−1.70 (n=173), leg2 +22.4bps t=2.35 (n=171) — both far smaller than the ±130-230bps event effect, and leg2's sign is opposite the addition effect. Sign-reversed (deletions) direction matches the mean-reversion story but is underpowered.

**Translation (Q3):** additions avg rebal-close price ¥3,932 → TSE standard tick ¥10 (25.4bps/tick — no JP-equity fee/tick config exists in this repo; TSE public schedule used as external premise). −133bps edge ≈ ¥52/share ≈ 5.2 ticks. Commission=0 (SOR) is a **task premise, not repo-verifiable**. Execution occurs at the same auction cross index funds use, so no separate slippage model is derivable; capturing the edge needs auction-priority access, not modeled here.

**Data validity (Q6):** one outlier, ticker 8316 (2002-12-03, holding-company conversion) at −22.1%/day — a corporate-action artifact, not an index-reversal signal; excluding it **tightens** the estimate (see table), so it is not driving the effect.

**MDE (Q10):** at n=111, sd=348bps → MDE=65.5bps (claimed −122bps ≈ 1.9× MDE, detectable). At n=38, sd=197bps → MDE=64.7bps — the claimed −45bps effect is **below its own detection floor**, consistent with the claim's own non-significant t=−1.4 (a correctly-reported null, not a hidden effect).

**Verdict AN: 再現** for the addition-side headline (pooled and 2017-26), under the inferred T−1 execution-day convention — both magnitude and t-stat reproduce within ~10bps / ~0.1t. Deletion side: directionally consistent but **未検証** (72% data loss).

## AO — Perk / dividend ex-date seasonality (JPR9, SV5)

**Denominator (Q1):** universe.csv 900 tickers (600 perk / 300 control), all had usable px. Ex-div events extracted (any `dividend>0` row): perk 8,571 / nonperk 5,027 = 13,598 (claim: 8,159/4,781=12,940 — same order, +5-8%, likely a stricter per-ticker event/threshold filter in the original).

| metric | claimed | recomputed |
|---|---|---|
| final cum-day open→close, pooled | −3.8bps, t=−2.1 | **−4.7bps, t=−3.27** (n=13,598) |
| D-10 run-up 2015-19 | +74bps | **+31.6bps, t=4.36** (n=5,540) — undershoots >50% |
| D-5 run-up 2015-19 | — | +34.1bps, t=6.64 (n=5,538) |
| D-10 run-up 2020-26 | — | +7.5bps, t=1.10 (n=8,055, n.s.) |
| D-5 leg 2020-26 | −38bps, t=−7.6 | **−30.5bps, t=−6.47** (n=8,055) — close match |

**Controls (Q2), critical finding:** a same-universe random-date control (5 draws/ticker, n=4,375) gives open→close = **−5.2bps, t=−1.94** — statistically indistinguishable from the claimed "final cum-day" −3.8/−4.7bps effect. This same stock universe already drifts ~−5bps/day market-adjusted on an arbitrary day, most plausibly because these are small/mid-cap names benchmarked against the large-cap N225 (a benchmark-mismatch confound), not an ex-date-specific behavior. The D-5/2020-26 leg (−30.5bps) remains ~6× the control and clearly separable; the **final-day headline number does not clear this bar**.

**Ex-drop, perk vs nonperk (excess):** perk −157.9bps (t=−57.6) vs nonperk −94.3bps (t=−33.0); excess = **−63.6bps** (Welch t=−16.1, n=8,570/5,026). ≈2.05 ticks at avg price ¥1,614 (tick ¥5, 31.0bps/tick).

**D+10 "recovery":** −115.3bps, t=−21.8 (n=13,581) — prices **do not recover**, they keep drifting down net of index for 10 more days. This contradicts a recovery framing; it is either a real post-event drift or a benchmark/composition artifact (see below) — flagged as an open finding, not a reproduction of any specific claimed number.

**Translation (Q3):** no JP cash-equity fee config exists in this repo; commission=0 (SOR) is a task premise. At avg price ¥1,614/tick ¥5 (31.0bps/tick), the claimed final-day effect (−3.8bps) is **smaller than one tick** — even if real, it is below the minimum executable price increment via ordinary limit orders.

**MDE (Q10):** pooled n=13,598, sd=169bps → MDE=2.8bps — at this n, essentially any nonzero effect is "significant," so statistical significance here does not imply the effect is behaviorally real or exceeds the control-noise floor above.

**Verdict AO: 数値差異(結論維持)**, with a carve-out: the D-5-into-ex-date reversal (era 2020-26) reproduces well in sign, magnitude and significance and clears the random-date control. The 2015-19 D-10 run-up magnitude is materially overstated in the claim (31.6 vs 74bps). The "final cum-day −3.8bps" headline number **fails the control test** (indistinguishable from generic universe drift) and should not be treated as an established ex-date effect on its own.

## 前提の誤り (assumption findings)

| premise | source | data shows | bias direction | inherits to |
|---|---|---|---|---|
| Perk flag applied today's (2026-09) status back over 2015-2026 | yutai manifest, self-disclosed | no time-varying perk-status source available | unknown sign, dilutes/contaminates era splits (JPR9's own 2015-19 vs 2020-26 comparison) | any AO era-split number, esp. the D-10 2015-19 undershoot found above |
| Perk universe = top-600 **by combined yield** (not random) | yutai manifest | ex-day drop scales mechanically with distributed dividend/perk value | inflates the "excess ex-drop perk−nonperk" (−63.6bps) via a **mechanical**, not behavioral, channel | the excess-ex-drop finding above; any causal "perk stocks behave differently" claim |
| Non-perk control filtered to price range + ≥4 ex-div events 2015-2026 | yutai manifest | control is dividend-stable survivors, not a neutral random sample | shrinks true perk-vs-control gap (control is itself somewhat cherry-picked) | same as above |
| `effective_date` in nk225 events = single field, no explicit "rebalance/trade date" | events.csv schema | T−1 convention had to be inferred to match claimed signs/magnitudes at all | none once inferred correctly, but unverifiable from data alone | any future reuse of `events.csv` that assumes `effective_date` = trade day |
| Deletion-side price coverage 27.9% | fetch_log.csv / px files | 72% of deletions untraceable (delisted/renamed) | direction unknown; likely non-random (extreme-event tickers more likely delisted, e.g. the one deletion outlier found even among the 28% that *do* have data) | any deletion-side number, including any future extension of JPR10 to the sell side |
| "SOR commission=0" cost premise | task instruction | no JP cash-equity fee/tick config exists anywhere in this repo | can't independently verify; treated as given | AN/AO money translations above, and any other JP-equity packet using the same premise |
| AO final cum-day effect vs random-date control | this audit | −4.7bps event vs −5.2bps control, same universe | overstates the ex-date-specificity of JPR9's headline number | JPR9 headline; SV5; any strategy design keying off "the final cum-day" alone |

No other premise categories from the checklist (spreads, contract multipliers, time-zone/lag, maintenance windows) apply materially to these two daily-bar, cash-equity claims.
