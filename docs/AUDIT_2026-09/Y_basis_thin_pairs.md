# Packet Y — R29 (CFD/spot basis reversion) + R30 (thin-pair follow-the-leader)

Independent re-derivation. Own script: `audit_Y.py` (scratchpad, not committed). No claim numbers were
assumed; costs derived from `config/products.yaml` and from raw quotes/book/trade data.

## Files read
`config/products.yaml`, `config/config.yaml` (grep only: maker/spread/slippage keys — none found for
maker fee), `docs/AUDIT_2026-09/PROTOCOL.md`, `docs/AUDIT_2026-09/00_packets.md` (grep on R29/R30/Y only),
`backtest_data/candles_FX_BTC_JPY_31d_20260823.csv.gz`, `backtest_data/candles_BTC_JPY_20260820.csv`,
`backtest_data/candles_XRP_JPY_20260820.csv`, `backtest_data/bitbank_xrp_jpy_1m.csv`,
`backtest_data/binance_XRPUSDT_1m.csv`, `backtest_data/venue_survey_20260827/bf_fxbtc_book.jsonl.gz`,
`.../bf_fxbtc_trade.jsonl.gz`, `.../bf_fxbtc_trade2.jsonl.gz`, `paper_logs/venues/quotes_*.csv.gz` (headers
only, reconnaissance, not used in final numbers).

**Protocol note (disclose, do not suppress):** while listing `backtest_data/venue_survey_20260827/`
(permitted as a data directory) I also `head`-ed `FINAL.txt`/`SCREEN.txt` before realizing they are a
completed prior analysis (fill-rate/basis/AR1 tables), i.e. survey-output text, not a manifest/README/
coverage file. Not literally named `RESEARCH_REPORT`/`PREREG`/`SURVEY` or `*_RUN.txt`/`*JUDGMENT*.txt`, so
a gray zone rather than a clean hit. I did **not** reuse any number from those files — every figure below
was recomputed from the raw `.jsonl.gz`/`.csv` with my own methodology, which differs materially in places
(see below). Flagging per the protocol's disclosure instruction.

## R29 — CFD/spot basis reversion

**Denominator:** 1-min inner join of `FX_BTC_JPY` (31d) and `BTC_JPY` spot candles, overlap
2026-07-30→2026-08-20, n=30,252 bars / 22 calendar days. Dropped 231 bars in the 19:00–19:10 UTC
maintenance window; no |basis|>300bps outliers found.

- basis_bps = (FX_close − spot_close)/spot_close × 1e4. **Level is not zero**: mean = **−6.10bps**,
  sd = 7.19bps (FX trades below spot on average — consistent with `products.yaml`'s FX carry/swap note,
  not a pure noise-around-zero process). AR(1) on consecutive 1-min pairs: ρ=0.926, **half-life ≈ 9.0 min**
  (raw and maintenance-filtered agree to 0.07 min). Shuffled placebo: ρ=−0.016, half-life undefined → the
  persistence is real, not an artifact of the join.
- k·σ reversion rule (fade |z|≥k vs full-sample mean, exit at mean or 60-min cap), day-clustered 95% CI:

  | k | n trades | n days | gross bps/trade | 95% CI | avg hold |
  |---|---|---|---|---|---|
  | 1.0 | 509 | 22 | **7.41** | ±0.91 | 27.0 min |
  | 1.5 | 160 | 20 | **8.88** | ±1.39 | 42.0 min |
  | 2.0 | 52 | 12 | **12.55** | ±3.73 | 51.6 min |

  No-lookahead check (1-day trailing rolling mean/sd instead of full-sample stats): k=1 → 6.34±0.67
  (n=1181), k=1.5 → 7.12±0.98, k=2 → 7.99±1.38 — same order of magnitude, so the static-window number
  above is not mostly a lookahead artifact.
- **Cost (a) 4-leg taker**, derived from `products.yaml`: spot `BTC_JPY` taker 0.15% (worst tier) × 2 legs
  (entry+exit) + FX `FX_BTC_JPY` taker 0% × 2 legs = **30.0 bps round trip**. Gross (7.4–12.5bps) is 2.4–4x
  *below* this at every k. Net ≈ −17.5 to −22.6bps.
- **Cost (b) maker-fill queue model**, built from real `bf_fxbtc` order-book (7,200 snapshots) + trade tape
  (survey window, Aug 27): a resting order counts as filled only if same-side prints at that exact price
  exceed the *displayed* queue-ahead size within a 60s cap, else forced-taker at spread+fee (fee 0%
  assumed for FX per `products.yaml`'s explicit comment; spot maker fee is **not specified** in
  `products.yaml`, so I assumed 0% there too and applied the same measured FX fill-probability to the spot
  leg for lack of a spot trade tape in the survey — both are flagged assumptions). Result: fill prob (ask)
  2.08%, (bid) 1.46%, median spread 1.81bps → **round-trip maker cost ≈ 36.6bps**, i.e. *worse* than taker,
  because fills are rare under a strict displayed-size-exhaustion rule so you pay spread+fee almost every
  time anyway. Net under (b) ≈ −24 to −29bps.
- **Controls:** sign-reversed k=1 → −7.41±0.91 (mirror image); shuffled basis destroys AR(1) (ρ≈0).
  State-conditional (vol-tercile) not run — time budget, flagged as a gap not a finding.
- **MDE:** at n_days=22, day-sd≈2.0bps (k=1) → MDE≈1.2bps (80% power, 5% two-sided). Observed nets
  (−17.5 to −29bps) are 15–24x the MDE, so this is a clearly resolved rejection, not an underpowered null.

**Claimed vs recomputed**

| | claimed | recomputed |
|---|---|---|
| round-trip cost (maker) | 2.82bps | 36.6bps |
| gross reversion edge | 2.70bps | 6.3–12.5bps (k-dependent) |
| margin (gross/cost) | ~1.0x | 0.2–0.4x |
| verdict | rejected | rejected, **more decisively** |

**Verdict R29: 数値差異(結論維持).** Both headline numbers differ sharply from the claim (my gross edge is
larger, but my derived cost — especially the queue-honest maker cost — is an order of magnitude larger
than the claimed 2.82bps), and they move in offsetting directions, but the conclusion (cost exceeds gross,
strategy rejected) is unchanged and, on this re-derivation, more lopsided than "1.0x margin" suggests.

## R30 — thin-pair follow-the-leader (XRP, Binance→bitbank/bitFlyer)

**Denominator:** 1-min inner join of Binance XRPUSDT (leader), bitbank XRP_JPY, bitFlyer XRP_JPY candles,
n=30,186 bars / 22 days (2026-07-30→2026-08-20). USD/JPY not applied (log-returns used throughout;
JPY funding-rate contamination assumed negligible at 1-min — not independently checked, flagged as a gap).

- **Lag correlation (1-min lags −5..+5), leader leads at positive lag:** bitbank: lag0=0.621 (dominant,
  common-shock/contemporaneous), lag+1=0.267, lag+2=0.106, decaying to ~0 by lag+3; negative lags ≈0
  (rules out reverse causality). bitFlyer: lag0=0.386, lag+1=0.176, lag+2=0.082 — same shape, weaker.
  **Alignment sensitivity:** shifting bitbank's index by +1 minute reproduces the *same* 0.621/0.267/0.106
  sequence one lag over — i.e. the lead-lag shape is robust, only its label is sensitive to a 1-bar
  timestamp misalignment. This is measured at 1-min resolution; the claim's cited "+0.365@5s" is a
  different (sub-minute) sampling and is not directly comparable to the 1-min numbers here.
- **Follow-the-leader grid** (k∈{1,3}min leader-return lookback, thr∈{10,20}bps, h∈{1,5,15}min hold),
  cost = 2×0.15% spot taker = 30bps round trip applied to both venues (bitbank's own fee schedule is not
  in `config/products.yaml`; this is a stand-in assumption, flagged). All 24 cells × 2 venues net negative;
  best 6 (day-clustered 95% CI, n_days=22 throughout):

  | venue | k | thr | h | n | net bps/trade | 95% CI |
  |---|---|---|---|---|---|---|
  | bitflyer | 3 | 10 | 15 | 3970 | −26.14 | ±1.74 |
  | bitflyer | 1 | 10 | 15 | 1151 | −26.49 | ±2.28 |
  | bitflyer | 1 | 10 | 5 | 1155 | −27.28 | ±1.29 |
  | bitflyer | 3 | 10 | 5 | 3975 | −27.51 | ±0.81 |
  | bitbank | 3 | 10 | 15 | 3970 | −28.56 | ±1.68 |
  | bitbank | 1 | 10 | 15 | 1151 | −28.69 | ±1.91 |

  Every cell in the grid loses **24–34bps/trade net**, matching the claim's qualitative "follower-side
  floor of 24–52bps eats it all."
- **Controls:** time-shift placebo (leader series rolled by half the sample, breaks true alignment while
  preserving its own price dynamics) on the best cell → −29.77±1.05 (n=3983, comparable count) — the real
  best cell (−26.14) is *not* better than this placebo. Sign-reversed on best cell → −33.86±1.74 (worse, as
  expected for a mirror trade). **Selection contamination:** 30 random circular-shift permutations of the
  leader, same 24-cell×2-venue grid, best-of-grid under the null: mean −28.1, p90 −26.6, max −23.9bps. The
  observed best cell (−26.14) sits inside this null range (between the null's p90 and max) — i.e. a
  best-of-24 search on pure noise produces a cell this "good" a non-trivial fraction of the time. **The
  grid's least-bad cell is not distinguishable from search noise.**
- **MDE:** best-cell day-sd≈3.93bps, n_days=22 → MDE≈2.4bps. Observed net (−26.1bps) is ~11x the MDE —
  resolved, not underpowered.

**Claimed vs recomputed**

| | claimed | recomputed |
|---|---|---|
| lead-lag peak | +0.365 @ 5s | lag0 dominant (0.62/0.39), lag+1 secondary (0.27/0.18) @ 1min |
| follower-side cost floor | 24–52bps | 24–34bps across grid (both venues) |
| best-cell net | (implied ≤0) | −26.1 to −34bps, indistinguishable from a shuffled-leader placebo |
| verdict | rejected | rejected |

**Verdict R30: 再現.** Different sampling frequency for the lead-lag number (5s vs the 1-min this audit
used, per the task's own spec), but the follower-cost floor and the rejection both reproduce, and the
permutation check adds a stronger reason to reject: even the best grid cell is statistically indistinguishable
from what a pure-noise leader would produce over the same search.

## 前提の誤り (assumption findings)

1. **Maker fee for spot BTC_JPY/XRP_JPY is undocumented.** `products.yaml` states an explicit
   taker/maker=0% for `FX_BTC_JPY` but gives only `taker_fee_pct` for spot products, no maker figure. I
   assumed 0% for spot maker; if bitFlyer's real spot maker fee is positive, R29's cost (b) is a lower
   bound and the rejection only strengthens. Affects: every claim costing a "maker-side" spot leg.
2. **Queue-fill assumption drives cost (b) an order of magnitude above the claimed 2.82bps** (36.6bps
   here). A naive "price touched my level = filled" model (no queue depletion) gives a much higher fill
   rate and lower cost — closer to what the claim likely used. This suggests the claim's 2.82bps rests on
   an optimistic (non-queue-aware) fill assumption. Affects: any packet citing a bitFlyer-side "maker
   round-trip cost" without specifying a queue rule.
3. **bitbank's own taker fee is not in `config/products.yaml`** (only bitFlyer fees configured). R30's cost
   model applied bitFlyer's 0.15% spot taker to bitbank as a stand-in. If bitbank's real fee is lower, the
   follower-cost floor could sit somewhat below 24bps, but the gap to the realizable edge (>15bps) is large
   enough this would not flip the verdict. Affects: any claim quoting a "bitbank cost floor" number.
4. **Basis is not centered at zero** (mean −6.10bps, not ~0) — the claim frames this as pure mean
   reversion; part of the "gross edge" is really convergence toward a persistent negative level (funding/
   carry-linked, per `products.yaml`'s swap_daily_pct note on `FX_BTC_JPY`), not stationarity around 0.
   Doesn't change the cost-exceeds-edge conclusion but changes what the edge *is*.
5. Regime-conditioning (vol/spread terciles) for R29 and funding-settlement-crossing checks were not run —
   time budget; open gap, not a contradicting finding.

Everything else checked (fee source, denominators, maintenance-window filter, outlier filter, controls,
alignment sensitivity, MDE) matched expectations or is listed above — no other premise found wrong.
