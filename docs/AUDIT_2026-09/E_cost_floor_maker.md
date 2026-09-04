# Blind Audit E — Cost Floor & Maker Line (independent re-derivation)

Method: own script (`audit_E.py`, not checked in), own fill/pairing logic, no docs/ or scripts/research_*/judge_*/KNOWLEDGE* opened, no git history consulted. Data: all `paper_logs/tape/ticker_2026{0820..0904}.csv.gz` (n=1,589,458 quote-change rows) and matching `executions_2026{0820..0904}.csv.gz` (n=750,191 trades). `backtest_data/executions_FX_BTC_JPY_31d_20260823.csv.gz` was only schema-checked (id, exec_date, price, size, side) — it has no matching quote/ticker file, so it cannot support a spread/maker analysis and was **not** used in the numeric results below.

## Fee constants found (verbatim)
- `config/products.yaml`: `FX_BTC_JPY: {..., taker_fee_pct: 0.0, ...}` — this is the value actually consumed for the product (`src/bot/products.py:ProductSpec`, applied at `src/bot/main.py:231` via `self.product.taker_fee_pct`). No separate `maker_fee_pct` key exists in the schema at all — "maker/taker fee 0%" is only a comment (line 14), not an enforced config value.
- `config/config.yaml`: `costs.taker_fee_pct: 0.15` — a generic/spot-tier default (also the class default in `src/bot/execution/paper.py:36` and `src/bot/backtest/engine.py:100-101`), **not** the value applied to FX_BTC_JPY in the live order path.
- Neither figure, alone or doubled, reproduces 5.8–7.9bps together with the measured spread (see Q2).

## Q1 — Spread, three weightings (bps), whole sample
| weighting | median | mean | n |
|---|---|---|---|
| quote-change | 1.911 | 2.027 | 1,589,458 |
| time-weighted | 1.776 | 1.923 | 1,589,443 |
| trade-count-weighted | 1.849 | 2.052 | 750,191 |
| trade-size-weighted | 1.841 | 2.067 | 750,191 |
| ex-maintenance (19:00–19:15 UTC), quote-change | 1.911 | 2.026 | 1,586,167 |
| ex-maintenance, time-weighted | 1.773 | 1.878 | 1,586,163 |

Maintenance-window rows are only 0.207% of the tape — excluding them barely moves anything. By hour (quote-change median): low ~1.7–1.8bps at 03–07 UTC, rising to ~2.1–2.3bps at 13–16 UTC (Europe/US session), back down at night. **L3 (2.22bps median) does not reproduce exactly under any weighting on this window** (all three land 1.78–1.85bps median, i.e. ~15–20% below); the trade-vs-mid effective spread (Q9) is closer (median 2.071). Caveat: the tape starts 2026-08-20, so a clean "2026-08 only" cut isn't available — this run mixes 12 days of August with 4 days of September.

## Q2 — Cost floor = 2×fee + spread
Using the FX_BTC_JPY product fee actually wired into the code (0%): floor = spread alone = **1.78–2.07bps** across weightings — roughly a third of the claimed 5.8–7.9bps. Using the generic 0.15% default instead (which is *not* what the code applies to this product) gives floor ≈ **31.8–32.1bps**, wildly above the claim. Neither fee source in the repo reproduces 5.8–7.9bps. What "7.9" would require: with spread ≈1.9–2.6bps, `7.9 = 2·fee + spread` needs fee ≈ 2.65–3.0bps (≈0.0265–0.030%) per side — a rate that does not appear anywhere in `config/products.yaml` or `config/config.yaml` for this product.

## Q3 — Own maker simulation (virtual quote at best bid / best ask, epoch=30s, fill rule = at-or-through, queue position ignored)
- Fill rate within 30s: bid leg 58.4% (928,245/1,589,458), ask leg 59.9% (952,497/1,589,458).
- Time-to-fill: bid p50 5.88s / p90 21.8s; ask p50 5.61s / p90 21.6s. (Same order of magnitude as claimed p50 7–15s, somewhat faster.)
- Capture per filled leg: bid mean 1.007bps, ask mean 1.007bps (median 0.949bps both legs) — close to claimed "capture" implying capture×2 ≈ 2.0bps.
- Adverse selection (mid move 5s post-fill, signed against maker): bid mean 1.167bps, ask mean 1.142bps against the maker.
- Round trips (nearest opposite-leg fill within 30s of the first fill), n=704,722: capture1+capture2 mean **2.043bps** (vs claimed +2.2bps — close); leg-to-leg drift mean **−1.406bps** (median −0.666, std 4.309) — same sign as claimed but roughly a **third to a half** the claimed −3.2 to −3.6bps magnitude; **net round-trip mean = +0.637bps** (median +1.121), 66.6% of round trips net-positive, t=123.4 (n=704,722) — i.e. reliably **positive**, opposite sign to the claimed −1.02 to −1.42bps.

## Q4 — Regime breakdown (net_bps, epoch=30s at-or-through)
Every single bucket tested is **positive**: all 24 hours (range +0.39 to +0.96bps), all 3 spread terciles (low 0.487 / mid 0.635 / high 0.789bps), all 3 realized-vol terciles (0.542–0.685bps). No negative regime found anywhere in this reconstruction — the opposite of "no regime with positive net."

## Q5 — Fill-rule sensitivity (queue position ignored either way)
| rule | bid fill | ask fill | round trips | drift mean | capture sum | net mean |
|---|---|---|---|---|---|---|
| at-or-through (price ≤/≥ quote) | 58.40% | 59.93% | 704,722 | −1.406 | 2.043 | **+0.637** |
| strictly-through (price </>  quote) | 55.22% | 56.65% | 643,852 | −1.352 | 2.070 | **+0.718** |

Fill rate drops only ~3pp going from the optimistic to the conservative price rule — both are still far above a true queue-position model, since **neither rule consumes `best_bid_size`/`best_ask_size`** (the "queue-ahead = displayed size" variant asked for in the brief was not built here; budget did not allow it). This is the single biggest reason these results may overstate real fillability, and hence net edge, relative to L2's presumably queue-aware(?) methodology.

## Q6 — Data validity
Ticker median inter-row gap 0.59s; 62 gaps >60s totaling 22.2h, including two large single gaps (~8.4h and ~10.3h — recorder outages, not spread across many days). Executions: 707 gaps >60s totaling 38.5h, same two large outages. Per-day row counts are otherwise in a normal 79k–131k (ticker) / 17k–101k (exec) band with no all-zero days. Excluding the 19:00–19:15 UTC maintenance window changes nothing materially (Q1).

## Q7 — Selection / sensitivity grid (epoch × fill rule, step=3 subsample for speed)
| epoch | rule | bid fill | ask fill | n trips | net mean | drift mean | capture²mean |
|---|---|---|---|---|---|---|---|
|10s|at-or-through|38.1%|39.8%|111,124|+0.897|−1.151|2.048|
|10s|through|33.3%|34.7%|88,991|+1.024|−1.094|2.118|
|30s|at-or-through|58.4%|60.0%|234,376|+0.639|−1.405|2.043|
|30s|through|55.2%|56.7%|214,177|+0.722|−1.349|2.071|
|60s|at-or-through|70.0%|71.0%|317,653|+0.394|−1.640|2.034|
|60s|through|67.7%|68.7%|301,860|+0.458|−1.590|2.049|

Selection choices made: 30s primary epoch, nearest-opposite-leg greedy pairing, mid-price capture/drift convention `net = cap1+cap2+direction·(mid2−mid1)`. **Net is positive in all 6 cells** — this is not an artifact of one arbitrary epoch/rule choice; capture²mean is stable (~2.03–2.12bps) and drift grows more negative as epoch lengthens (more time to revert) but never approaches −3.2 to −3.6bps in this grid.

## Q8 — Tick floor alternative explanation
Tick size = 1 JPY (smallest observed |Δbest_bid| = 1.0). Median spread = 2368 JPY = **2368 ticks**; only 0.02% of quote-rows sit at a 1-tick spread, 0.07% at ≤2 ticks. **This rules out "spread ≈ tick floor, no capture to earn" as the explanation for any maker loss** — the book is nowhere near the tick floor on this product/period.

## Q9 — Consistency: quoted vs. trade-implied spread
Trade-vs-mid effective spread: median 2.071bps, mean 2.598bps (n=750,191) — noticeably above the quote-change-weighted median (1.911bps), consistent with trades clustering in higher-spread moments. Roll estimator (pooled, ignores day boundaries) gives an implied spread of only 0.976bps — much lower, and known to be biased/unstable when trade price series include bid/ask bounce mixed with genuine drift; treat as a weak cross-check only, not a primary estimate.

## Q10 — Falsification sentences
- **L1** is falsified as stated: no fee constant in this repo (0% FX taker, or 0.15% generic default) combines with the measured spread (1.8–2.6bps across weightings/definitions) to produce 5.8–7.9bps; the FX-appropriate floor measured here is 1.8–2.6bps, and the generic-fee floor is ~32bps — 5.8–7.9bps sits in neither regime.
- **L2** does not reproduce under a non-queue-aware maker-fill reconstruction: capture×2 (~2.0–2.1bps) matches the claim, but leg-to-leg drift here is −1.1 to −1.6bps (about a third to a half of the claimed −3.2 to −3.6bps) and **net is positive in every one of 6 epoch×rule cells and every hour/spread/vol regime tested** (+0.39 to +1.02bps), the opposite sign of the claimed −1.02 to −1.42bps. If a genuine queue-position (displayed-size) fill model were applied and still produced the claimed 99.8% close rate alongside a negative net, that would rescue L2; that variant was not built here (budget), so this audit **falsifies the specific magnitude and sign of L2's net result under the fill definitions tested, without ruling out that a queue-aware model could recover the claimed loss.**

## Verdict table
| Law | Claimed | Recomputed (this audit) | Verdict |
|---|---|---|---|
| L1 (taker floor 5.8–7.9bps) | 5.8–7.9bps | 1.8–2.6bps (FX 0% fee) or ~32bps (generic 0.15% fee) | **結論変更** — neither in-repo fee source reproduces the claimed range; true FX floor measured ~3x lower |
| L2 (maker closed, net −1.02〜−1.42bps, drift −3.2〜−3.6bps) | net −1.02〜−1.42bps, drift −3.2〜−3.6bps, fill 99.8% | net **+0.39 to +1.02bps** (positive, all 6 grid cells & all regimes), drift −1.09 to −1.64bps, fill 33–71% (30s epoch, not 99.8%) | **結論変更** (sign flip on net; magnitude gap on drift and fill rate), with an explicit caveat that no queue-position/displayed-size fill model was tested — this is the most plausible reconciling factor and was not ruled out |
| L3 (spread 2.22bps median, 2026-08) | 2.22bps | 1.78–1.85bps (quote/time/trade-count weighted) to 2.07bps (trade-vs-mid effective) | **数値差異(結論維持)** — same order of magnitude (~2bps), exact figure depends on weighting choice and on a date window (data starts 2026-08-20, includes 4 September days) that could not be restricted to August-only from available files |

## Files read
`config/config.yaml`, `config/products.yaml`, `src/bot/products.py`, `src/bot/main.py` (grep), `src/bot/execution/paper.py` (grep), `src/bot/backtest/engine.py` (grep), `src/bot/exchange/*.py` and `src/bot/settings.py` (grep, no fee/tick matches), all 16 `paper_logs/tape/ticker_2026*.csv.gz` and `paper_logs/tape/executions_2026*.csv.gz` (2026-08-20 through 2026-09-04), `backtest_data/executions_FX_BTC_JPY_31d_20260823.csv.gz` (header/schema only, not used numerically). No file under `docs/`, no `scripts/research_*.py` / `scripts/judge_*.py`, no `KNOWLEDGE*.md`, and no git history were opened — audit is not void.
