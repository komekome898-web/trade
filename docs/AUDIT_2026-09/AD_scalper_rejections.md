# Packet AD — Blind audit: burst scalper arming-threshold withdrawal (R14) and burst-scalper-body rejection (R18)

Independent re-derivation. Own script: `scratchpad/audit_AD.py` (not committed).
Budget used: 24 tool calls.

## Files read
`docs/AUDIT_2026-09/PROTOCOL.md`; `docs/AUDIT_2026-09/00_packets.md` (grep on `R14`,`R18`,`^| AD ` only,
§1.3/§7 rows); `paper_logs/scalp_paper.jsonl` (full, 510 lines); `paper_logs/bot.jsonl` (schema sample +
full scan for symbol/event counts); `paper_logs/tape/board_top5_20260820.csv.gz`,
`board_top5_20260821.csv.gz`, `executions_20260820.csv.gz`, `executions_20260821.csv.gz`;
`scripts/run_scalp_paper.py` (full — the paper runner that produces scalp_paper.jsonl; not on the
forbidden list); `config/config.yaml` (costs: block); `config/products.yaml` (FX_BTC_JPY row);
grep only on `src/bot/execution/paper.py`, `src/bot/backtest/engine.py` (slippage_pct usage).

## Denominator (Q1)
`scalp_paper.jsonl` spans **2026-08-20 06:13 → 2026-08-21 12:30 (≈30h, 2 calendar days only)**, 14
strategy restarts, several config eras. Reconstructing entry(fill)+exit pairs: 109 completed round
trips, 77 misses. Filtering to `exit_kind ∈ {tp_maker, fallback_taker}` (the current-production maker
entry / maker-TP-then-taker-fallback exit era) yields **n=86**, exactly matching R18's stated n. Mean
net = **-3.835 bps**, matching the claimed -3.83 bps almost exactly (regime a below) → the headline
mean **reproduces**.

## Execution model actually used (the "maker or taker" check)
`run_scalp_paper.py` is a **self-contained script that does not call `src/bot/execution/paper.py`**.
It has its own hardcoded cost model: entry is a resting limit filled by a same/better print
("permissive... optimistic bound", 0 spread, 0 slippage, 0 fee); the take-profit is the same maker
rule (0 cost); only the *fallback* exit crosses the spread and pays a hardcoded `SLIPPAGE_BPS = 2.0`
(one side only). `config/config.yaml: costs.slippage_pct = 0.05` (→10bps RT) is used only by
`src/bot/execution/paper.py` and `src/bot/backtest/engine.py`, i.e. the **main bot**'s paper engine
(confirmed against `paper_logs/bot.jsonl`, `fee_jpy: 0.0` fills on FX_BTC_JPY, `price_source:
venue_avg`) — **not** by the scalper. `config/products.yaml` confirms `FX_BTC_JPY taker_fee_pct: 0.0`.
Backing the embedded cost out of the 86 trades: implied average cost actually paid = **0.91 bps/trade**
(47/86 = 54.7% pay **zero** cost, being maker/maker; 39/86 = 45.3% pay ≈half-spread+2bps taker).

## Claimed-vs-recomputed (R18, n=86, bps)
| regime | mean | sd | 95% CI (bootstrap, B=20000) | win% |
|---|---|---|---|---|
| claimed | -3.83 | — | [-9.2, -2.8] | — |
| (a) as-logged (reproduced) | -3.835 | 18.17 | **[-7.81, -0.16]** | 54.7 |
| gross, cost stripped out entirely | -2.93 | 17.33 | [-6.72, +0.57] | 58.1 |
| (b) flat realized-taker 2.6bps RT | -5.53 | 17.33 | [-9.32, -2.03] | 54.7 |
| (c) queue-aware maker (tape-walked, n changes) | -4.41 (n=77) | 18.81 | — | — |

**The claimed "95% CI [-9.2, -2.8]" is not a confidence interval.** Split by calendar day: Aug-20
(n=14) mean = **-9.24 bps**, Aug-21 (n=72) mean = **-2.78 bps** — these two per-day means, not any
resampling procedure, are what the claim's bracket numbers equal to one decimal. This is a
mislabeling, not a computation error in the mean. The properly-computed pooled bootstrap 95% CI is
[-7.81, -0.16]; bootstrap P(mean ≥ 0) = 0.023.

## Regime (c): queue-aware maker fill (tape walk)
Tape-walked (`board_top5` displayed size at signal time as queue ahead, `executions` cumulative
same/through prints to clear it) instead of the script's touch-only rule: **9/86 entries (10.5%) and
1/47 TPs would not actually have filled** inside their timeout under a non-optimistic queue rule.
Dropping those 9 entries (n=77) leaves mean **-4.41 bps** — no improvement.

## Verdict per claim
- **R18 (burst scalper body, 86 events, net -3.83bps)** → **再現** (headline mean and n reproduce
  exactly). The 95% CI as stated is **数値差異(結論維持)**: it is mislabeled (day-split range, not a
  CI) but the correctly-computed CI [-7.81,-0.16] and bootstrap p=0.023 support the same conclusion
  (net negative, rejection holds). Under realized taker cost (2.6bps) the result gets **worse**
  (-5.53bps), under zero cost it is still negative (-2.93bps, CI barely straddles 0), and under a
  stricter tape-walked maker-fill rule it is also worse (-4.41bps, n=77). **The rejection does not
  flip under any tested regime; it is if anything strengthened.**
- **R14 (arming threshold 10→8bps, marginal trades "-4.14bps")** → **再計算不能** from the data this
  packet names. Only **4** `limit_placed` events ever ran at the lowered `thr_armed_bps=8` before the
  change reverted to 10; 2 missed, **2 completed** (+3.78bps, -7.08bps; mean -1.65bps, n=2). No trade
  in `scalp_paper.jsonl` shows `signal_bps` in [8,10) among the exit_kind-tagged (maker-TP-era)
  population either (n=0 there — different exit regime altogether: the thr=8 era predates the
  maker-TP exit and still used the legacy taker-hold exit). The "-4.14 bps / 68 fills" figure that
  motivated the withdrawal is attributed by `run_scalp_paper.py`'s own docstring to
  `scripts/replay_scalp_storm.py` (an offline replay of the storm library) — **not** to this live
  paper log; that population is outside the data this audit was given and cannot be checked here.
  Directionally the 2 live trades that did run do not contradict the withdrawal, but n=2 carries no
  statistical weight.

## The other 8 questions (condensed)
- **Controls (Q2):** radar-armed vs unarmed state-conditional control is **degenerate**: all 86 R18
  trades show `radar_armed=False` (the maker-TP era's bursts did not land inside the 12:30-15:00 UTC
  window in this 2-day sample) — no state split is possible from this data. Sign-reversed proxy
  (mirror the gross touch-to-touch price move): +2.93bps vs gross -2.93bps — mechanically symmetric,
  not independently informative.
- **Translation (Q3):** -3.83bps × 110,000 JPY notional ≈ **-42 JPY/trade**; at 86 trades/30h this
  paper strategy would lose money scaled to any trade frequency, before financing/funding.
- **Regime dependence (Q4):** hour-of-day (UTC) split is noisy at low n/bucket (e.g. h08 n=20
  mean+0.34, h09 n=19 mean-10.8, h15 n=7 mean-11.0); no clean regime signal recoverable at this n.
- **Definition side-effects (Q5):** filtering to `exit_kind∈{tp_maker,fallback_taker}` is the correct
  reconstruction of the claimed population (it reproduces n=86 exactly); it silently excludes the 23
  earlier-era exits and the thr=8 era, which is appropriate (different mechanics) but means R18 never
  actually pools across the arming-threshold experiment.
- **Data validity (Q6):** only 2 calendar days behind 86 "events"; 15 `ws_reconnect` events logged in
  the same window (reconnect risk during exactly the volatile bursts the strategy targets) — not
  screened out of the 86; no bitFlyer maintenance-window (19:00-19:10 UTC) overlap found in the trade
  timestamps.
- **Selection contamination (Q7):** entry/exit rule (thr, tp_bps, fallback_sec) is not tuned inside
  this packet's data — it's inherited from a prior study — so no additional search-driven overfitting
  visible in these two days, but the 2-day, 1-symbol, always-unarmed sample is itself a small,
  non-random slice.
- **Simplest alternative explanation (Q8):** the loss is fully attributable to the fallback-taker leg:
  tp_maker exits are a fixed **+10.00bps by construction** (47/86, 54.7%), fallback_taker exits average
  **-20.51bps** (39/86, 45.3%) — i.e. price continues adverse past entry often enough, and far enough,
  that the fixed +10bps TP is reached less than it "should" be for the strategy to break even; this is
  ordinary adverse-selection/momentum-continuation, not a cost artifact.
- **Consistency (Q9):** gross (cost-free) mean is already negative (-2.93bps); an edge cannot exist if
  even the zero-cost version is non-positive — cost regime choice is not what drives the rejection.
- **Falsification + MDE (Q10):** sd=18.17bps, n=86 → **MDE ≈ ±5.49bps** at 80% power / two-sided 5%.
  The claimed effect (-3.83bps) is *below* this MDE, i.e. this sample alone is somewhat underpowered
  to certify the point estimate, but the bootstrap one-sided P(mean≥0)=0.023 and the fact that raising
  cost to a realistic level (regime b) *increases* the loss to -5.53bps (above MDE) means: **a
  plausible positive edge is not what a cost correction would reveal here.**

## 前提の誤り (assumption findings)
1. **premise:** PAPER execution charges 0.05%/side (10bps RT) via `config/config.yaml
   costs.slippage_pct`. **source in claim:** task framing / general repo cost note. **what the data
   shows:** the scalper (`scalp_paper.jsonl`) never uses that config value — it's a standalone script
   with its own model (0 cost on maker legs, 2bps one-side on taker fallback, 0% fee), averaging
   0.91bps/trade actually paid. **direction of bias:** this premise, if applied to R14/R18, would
   *understate* the paper edge (implying correction should help); the opposite is true — realistic
   2.6bps RT cost makes R18 worse (-5.53 vs -3.83bps). **inherits:** any other rejection that assumes
   `config.yaml costs.slippage_pct` governs the scalper's paper log (it governs only the main
   `xborder_momentum` bot's `bot.jsonl`/backtest fills, confirmed via `fee_jpy:0.0` records there).
2. **premise:** R18's "95% CI[-9.2,-2.8]" is a statistical confidence interval. **source in claim:**
   packet R18 text. **what the data shows:** those two numbers equal the Aug-20 and Aug-21 per-day
   means to one decimal — a 2-day split range, not a resampling or parametric CI. **direction of
   bias:** overstates precision (a 2-cluster "CI" looks tighter/more certain than the true bootstrap
   CI [-7.81,-0.16], which is ~20% wider and reaches closer to zero). **inherits:** any other packet
   whose "95% CI" was produced by the same day-split convention should be re-checked for the same
   mislabeling.
3. **premise:** R14's "-4.14bps over marginal trades" is measurable from `paper_logs/scalp_paper.jsonl`
   (the source this packet names). **what the data shows:** only 2 completed live trades ever ran at
   `thr_armed_bps=8`; the -4.1bps/68-fill figure traces (per `run_scalp_paper.py`'s own comments) to an
   offline replay script, a different population entirely. **direction of bias:** the live number is
   unverifiable/not reproducible from the named source; not necessarily wrong, but the n=68 evidence
   for the withdrawal did not come from paper trading. **inherits:** any claim that cites
   `scalp_paper.jsonl` as the evidentiary base for the arming-threshold withdrawal specifically (vs.
   the storm-library replay) should cite the replay instead.
