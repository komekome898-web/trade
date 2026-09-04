# Packet W — Exit design cannot rescue a losing entry

Claims audited: L12, R15, R16, R19. Blind re-implementation, script at
`/tmp/claude-0/-home-user-trade/fa7bf0d4-a5c4-55b7-991b-874b590e00a3/scratchpad/audit_W.py`.
No claim-authoring script, KNOWLEDGE.md, PREREG or judgment file was opened.

## 1. Entry set (denominator) and method

- **Scalper** (`paper_logs/scalp_paper.jsonl`): 14 `start` sessions, 14 `entry` (taker) +
  95 `fill` (maker) events paired sequentially with the next `exit` event → **n=109** trades,
  **2 distinct UTC days** (2026-08-20/21 only — the file does not extend further).
- **Main bot** (`paper_logs/bot.jsonl`, `symbol=FX_BTC_JPY`, `decision=ORDER_SENT`): 65
  BUY/SELL entries, paired sequentially with the next CLOSE/STOP_LOSS → **n=61** matched
  round trips (4 entries have no logged close in file) across **14 distinct UTC days**
  (2026-08-20 .. 2026-09-03). Pooled n=170, 14 days (scalper's 2 days ⊂ bot's 14).
- Re-simulation: each entry's forward price path was rebuilt from `paper_logs/tape/executions_*.csv.gz`
  (tick trades) resampled to 1-second OHLC (max/min/last), 1800s (30min) forward, 0
  entries skipped for missing tape coverage (all fall inside the 2026-08-20..09-04 tape).
  Grid: TP∈{5,10,20,40}bps × SL∈{5,10,20}bps × max_hold∈{1,5,30}min = **36 cells**. Tie-break
  (SL and TP both crossed in the same second) resolves to **SL first**, matching
  `src/bot/backtest/engine.py` L294-329 ("STOP is assumed to fill first, conservative").
  Time-exit marks at the horizon's last tape price. This is a flat-bps-cost re-simulation
  (not maker/taker-differentiated like the engine) — a documented simplification.
- Costs: **paper** = `config/config.yaml costs.slippage_pct` 0.05%/side × 2 sides = **10bps RT**
  (`FX_BTC_JPY` `taker_fee_pct=0.0` in `config/products.yaml`, so no separate fee term).
  **realized** = **2.6bps RT** (given premise). Cross-check against data: mean/median bid-ask
  spread from `paper_logs/tape/ticker_*.csv.gz` (1,589,458 quotes, 16 days) = **2.03 / 1.91bps**
  — a taker RT (cross once each way) costs ≈ one spread-width, so the data-derived realized
  RT cost is **~2.0bps**, same order as the 2.6bps premise and confirms paper cost (10bps) is
  **~5×**, not ~4×, the data-derived figure (vs ~3.8× using the premise's own 2.6bps).

## 2. Surface (day-clustered, 36 cells, pooled n=170/14 days)

Marginal means (bps net, averaged over the other two axes) — flat, no ridge:

| axis | realized-cost mean_bps | paper-cost mean_bps |
|---|---|---|
| TP 5/10/20/40 | -1.22 / -0.47 / 0.66 / 2.07 | -8.62 / -7.87 / -6.74 / -5.33 |
| SL 5/10/20 | -0.50 / 0.42 / 0.86 | -7.90 / -6.98 / -6.54 |
| hold 1/5/30min | 0.23 / -0.19 / 0.74 | -7.17 / -7.59 / -6.66 |

Full-grid range: realized **-1.8 to +7.6bps**; paper **-9.2 to +0.2bps**. Monotonic drift
toward large TP/SL/hold, no interior peak ("ridge") — consistent with L12.

**Best cell** (both cost regimes): TP40/SL20/hold30min.
Pooled: mean_net = **+7.57bps** (realized) / **+0.17bps** (paper) vs **base** (actual logged
exit) mean_net = **-3.15bps** (realized, CI [-16.20, 9.90], 14-day cluster) / **-10.55bps**
(paper, CI [-23.60, 2.50]). Diff vs base = **+10.72bps**, paired day-clustered t-test
**p=0.032** (both cost regimes — cost cancels in the paired difference).

**Multiple-comparison correction** (Bonferroni, 36 cells, α=0.05/36=0.00139): **0 of 36
cells** beat the base exit significantly, in either cost regime, pooled or in either
source-split (scalper-only, bot-only). Source split for context:

| subset | n / days | best cell diff vs base | p | sig@bonf |
|---|---|---|---|---|
| scalper | 109 / 2 | +5.95bps (TP40/SL20/H30) | 0.287 | no |
| bot | 61 / 14 | +10.97bps (TP40/SL20/H30) | 0.030 | no |

**Required win ratio vs realized** (TP40/SL20 cell): breakeven win rate
`(SL+cost)/(TP+SL)` = (20+2.6)/60=**37.7%** (realized cost) / (20+10)/60=**50.0%** (paper
cost). Simulated win rate (TP hit first) at that cell = **35-39%** across subsets — below
even the *realized*-cost breakeven, i.e. the nominal "improvement" is a magnitude effect
(rare big wins), not a hit-rate edge, and does not clear the paper-cost bar at all.

**JPY translation** (avg notional ≈115,000 JPY/trade: scalper fixed 110,000; bot
≈0.011BTC×~11.3M): realized RT cost ≈30 JPY/trade, paper RT cost ≈115 JPY/trade. The
non-significant best-cell edge (+10.7bps pooled) ≈ +123 JPY/trade, ≈21,000 JPY summed over
170 trades — inside the day-clustered CI on zero.

## 3. MDE

At the corrected α (0.00139) and 80% power, illustrative cell TP10/SL10/hold5:
- bot/pooled (14-day cluster): **MDE ≈ 7.3-7.4bps** per cell.
- scalper (2-day cluster): **MDE ≈ 129bps** — with only 2 sampled days, the scalper subset
  cannot detect any plausible exit-design effect; its slice of L12/R15 is **underpowered by
  construction**, independent of the point estimate.

## 4. Side-check: E2 variance-reduction sub-claim (R15)

Comparing the pre-E2 scalper style (`event=entry`, taker, no `tp_bps`, n=14, gross std=17.4bps)
vs the E2-style (`event=fill`+`maker_tp`, n=95, gross std=17.8bps): Levene's test
stat=0.46, **p=0.50** — no detectable variance reduction in this data, but n=14 for the
"old" arm makes this comparison very underpowered; **inconclusive**, not a reproduction
either way.

## 5. Per-claim verdicts

| claim | claimed | recomputed | verdict |
|---|---|---|---|
| L12 (no ridge; adaptive TP ≈ const large-TP) | flat surface, no tuning wins | flat surface confirmed (marginal effects table §2), best cell +10.7bps pooled, p=0.032, **not** significant at 36-cell Bonferroni | **再現** (surface-flatness part). Adaptive-TP-vs-constant part: **再計算不能** — no adaptive-TP parameters are logged per-trade in either file, cannot be independently re-derived |
| R15 (24-cell fixed surface + 3 adaptive-TP: none beats E2) | no config significantly beats E2 | 36-cell grid: 0/36 beat the *actual logged* exit at Bonferroni-corrected significance, any cost regime | **再現** for "no significant winner"; E2-vs-others baseline and adaptive-TP arms **再計算不能** (not logged) |
| R16 (main-bot 54-config grid loses train→val/OOS) | best-in-train loses OOS | not independently testable as a train/val/OOS split (this audit used one pooled 36-cell in-sample surface, no held-out split); the **flat, non-significant surface itself reproduces** (bot-only: 0/36 sig, best diff +10.97bps p=0.030) | **数値差異(結論維持)** — same qualitative conclusion (no free-lunch exit win) via a different, coarser test; the specific train/val/OOS ranking is **未検証** here |
| R19 (TP-vol slope n=77 → -0.20bps, vanished) | live-forward regression slope ≈0 | no per-trade realized-volatility or per-trade-assigned-TP field exists in `scalp_paper.jsonl`/`bot.jsonl`; neither file yields an n=77 trade set under any entry-pairing rule tried (n=109, 95, 61, 65, 14) | **再計算不能 → 未検証** (data lost/not present in the allowed files) |

## 6. 前提の誤り (assumption findings)

- **paper cost ≈4× realized, premise=2.6bps RT | claim context | data-derived realized RT
  (mean bid-ask spread, 16 days, 1.59M quotes) = ~2.0bps, paper=10bps → ratio ~5×, not ~4× |
  biases claim's paper-vs-realized gap slightly downward (the real gap is larger) | every
  other rejection in this packet family that cites the 2.6bps realized-cost floor (R15, R16,
  R19 lineage) inherits a mildly conservative cost estimate**.
- **"24-cell" grid (L12/R15 wording) vs the 36-cell grid actually re-run here (task spec) |
  claim text says 24 | this audit used the specified 4×3×3=36-cell grid | direction: this
  audit is a *coarser superset* re-test, not a literal reproduction of the original 24-cell
  design | any claim citing "24 configs tested" should be read as a different (possibly
  TP×SL-only, no max_hold axis) grid than the one audited here**.
- **Entry/exit pairing assumes single-open-position, strictly serial trades | inferred from
  file structure, not stated in any claim | 4 of 65 main-bot entries have no matching
  close in `bot.jsonl` (dropped) — consistent with truncation at file end, not a data
  error, but reduces n from 65 to 61 | direction: mild reduction in power, does not
  change sign | any claim quoting "65 main-bot trades" from this file inherits the same
  4-trade truncation**.
- **R16's "54構成"/train-val-OOS split**: not reconstructable from the two flat log files
  alone (no split labels, no train/val/OOS date boundaries logged) | source: claim text |
  data shows only an undifferentiated 14-day trade stream | direction: cannot confirm or
  refute the specific ranking-reversal mechanism, only the weaker "no significant winner"
  finding | inherited by any claim citing R16's specific OOS-reversal number.
- **R19's n=77**: not present in either allowed log under any tested pairing rule | source:
  claim text | data: closest counts are 109 (scalper), 61-65 (bot) | direction: cannot
  attribute a cause, simply unverifiable from the given files | inherited by any claim
  citing the -0.20bps slope number.

## 7. Falsification

The exit-design-is-powerless conclusion (L12/R15/R16) would be **falsified** by: any grid
cell beating the actual logged exit by more than its MDE (≈7.3bps at n=61-170/14 days,
≈129bps at n=109/2 days) at Bonferroni-corrected significance, in **both** cost regimes,
on a fresh (not-yet-seen) entry sample. That did not happen here (0/36 cells, both regimes,
all subsets); the nominal best cell (TP40/SL20/H30) is directionally positive
(+5.95 to +10.97bps) but well inside its clustered CI on zero and outside the required
win-rate bar under paper cost. **R19 is not falsifiable from these files** — the claim's
population (n=77, TP-vs-vol) does not exist in `scalp_paper.jsonl` or `bot.jsonl`.

## Files read

`config/config.yaml`, `config/products.yaml`, `src/bot/backtest/engine.py` (TP/SL/max_hold
semantics only, L1-360), `paper_logs/scalp_paper.jsonl`, `paper_logs/bot.jsonl`,
`data/scalp_paper.jsonl` (checked identical to paper_logs copy, not used further),
`paper_logs/tape/executions_20260820..20260904.csv.gz` (16 files), `paper_logs/tape/ticker_20260820..20260904.csv.gz`
(16 files), `backtest_data/candles_FX_BTC_JPY_31d_20260823.csv.gz` (inspected, not used —
tape gave full-coverage 1s resolution across all entry days, candles stop 2026-08-23),
`docs/AUDIT_2026-09/PROTOCOL.md`, `docs/AUDIT_2026-09/00_packets.md` (grep on claim ids
L12/R15/R16/R19/W only).
