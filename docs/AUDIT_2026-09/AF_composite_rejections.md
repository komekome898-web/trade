# Packet AF — blind audit of R37 (C3 long-only) and R39 (S11 signal-reversal fade)

Budget used: ~28 tool calls. Script: `scratchpad/audit_AF.py` (not committed).

## Files read
`docs/AUDIT_2026-09/PROTOCOL.md`; `docs/AUDIT_2026-09/00_packets.md` (grep on `R37`/`R39` only, section 1.3-1.4
rows); `paper_logs/bot.jsonl`; `paper_logs/spread_FX_BTC_JPY.csv`; `paper_logs/status.json`,
`s12_status.json`, `overlay_state.json` (existence-check only); `paper_logs/scalp_paper.jsonl` (head, ruled
out as unrelated); `config/composite.yaml`; `config/products.yaml`; `config/config.yaml` (grep: strategy
name, slippage_pct); `src/bot/strategy/composite.py` (grep, lines 439/696-710 only); `src/bot/execution/paper.py`
(fill-model logic, lines 1-40); directory listing (not content) of `src/bot/strategy/`. `paper_logs/tape/*.csv.gz`
was listed but not opened — the spread CSV and the decision log's own price series were sufficient.

## How C3 and S11 trades were identified
**C3**: `config/composite.yaml`'s `modules.long_only` block states the gate gate is judged against "the
long-only subset of champion paper trades." `bot.jsonl` carries no module/strategy tag field at all — every
FX_BTC_JPY `"decision":"ORDER_SENT"` row belongs to the single active strategy (`config.yaml: strategy.name:
xborder_momentum`; composite's modules are all `enabled: false`, so composite ≡ xborder_momentum signal-for-
signal). I reconstructed round trips from `strategy_signal` ∈ {BUY,SELL,CLOSE,STOP_LOSS} (a same-direction
signal while already positioned is a same-direction size-add and was excluded from re-anchoring; a signal
opposite the open position is a reversal that closes-then-reopens in one row — confirmed at
`composite.py:709-710`). Filtering to `direction=='long'` (BUY entries) **and** taking the cumulative-count
window where total trades = 30 reproduces **both** R36's n=30 and R37's n=17 simultaneously (trade #30 by exit
time is the 17th long trade, closing 2026-08-25T02:54 UTC) — strong confirmation the reconstruction matches
whatever produced the original claim.

**S11**: not recoverable. `signal_reversal`/`fade`/`S11` appear nowhere in `composite.py`, `composite.yaml`,
or any field/value in `bot.jsonl` (checked all `reason` prefixes and all `indicator_values` keys — none
reference a reversal-fade rule). It is not one of composite.yaml's four gated modules. Two filenames in
`src/bot/strategy/` (`wick_reversal.py`, `range_fade.py`) look topically adjacent but their content is outside
this packet's read list (not `composite.py`) and reading it was skipped to stay in scope. **This claim's
trade-level attribution cannot be reconstructed from the sources this audit is permitted to open.**

## R37 — C3 long-only (n=17)

Population: the first 30 champion (xborder_momentum) round trips by exit time, 2026-08-20T13:43–
2026-08-25T02:54 UTC (5 trading days), long subset n=17 (13 shorts in the same window).

Cost derivation (not trusting the claim's number): `config/products.yaml` FX_BTC_JPY `taker_fee_pct: 0.0`;
`config/config.yaml execution.slippage_pct: 0.05` (→10bps RT, "PAPER"); `paper_logs/spread_FX_BTC_JPY.csv`
(237,674 quotes) mean round-trip spread 1.94bps / median 1.78bps — close to, not identical to, the given
"≈2.6bps realized" premise; I used the given 2.6bps for the "realistic" column below since it's the one the
task asks to re-judge under, and note my own spread-only estimate is somewhat lower.

| | claimed | recomputed: gross (no cost) | net @ PAPER 10bps RT | net @ realistic 2.6bps RT |
|---|---|---|---|---|
| mean %/trade | −0.013 | −0.025 | −0.125 | −0.051 |
| 95% CI (day-clustered, 5 days) | [−0.194, +0.196] | [−0.212, +0.161] (i.i.d. boot) | **[−0.338, −0.038]** | [−0.264, +0.036] |

The day-clustered CI has only 5 day-clusters (block bootstrap over 5 blocks) — treat its width as indicative,
not exact. Under **both** cost regimes the mean stays negative and well short of the module's own pre-
registered bar (net ≥ +0.15%/trade, n≥15, CI excludes 0): **even the friendlier realistic-cost re-judgment does
not clear the bar** — the qualitative rejection is unchanged by the slippage-premise correction. Point estimate
differs from the quoted −0.013% (my gross figure is the closest match, −0.025%, suggesting the original "net"
figure may not have the PAPER 10bps cost applied — see 前提の誤り).

**Controls**: random 17-of-30 draws from the same 30 trades average −0.178%/trade (20,000 draws); the actual
long subset (−0.025%) sits at the 94th percentile — longs really were the better half of this window, but the
short-only complement (n=13) averages −0.38%/trade and BTC rose ~11% (¥11.28M→¥12.5-12.6M) over the neighboring
weeks — the simplest explanation is directional drift in the window, not a durable long-side edge (protocol
Q8). Consistency check: over the **full** current log (62 round trips through 2026-09-04, 35 longs) the long
subset mean is +0.0094%/trade — near zero, same sign as the original small-negative/near-zero reading, not the
opposite sign. No maintenance-window (19:00–19:10 UTC) overlap in any of the 17 trades.

**Definition sensitivity**: one of the 17 trades is a STOP_LOSS whose naive entry-price-anchored return is
+1.78% — physically impossible for a protective stop — because the position was pyramided (2 same-direction
size-adds visible only as `ORDER_SENT` rows with no distinct exit) and the anchor price is stale. Using the
strategy's own logged `indicator_values.loss_pct` (−0.78%) for STOP_LOSS exits instead of naive price-diff
swaps that single trade from +1.78% to −0.78% and moves the 17-trade mean from **+0.137%** to **−0.025%/trade**
— a sign flip on the headline number from a single-trade bookkeeping choice. This is the biggest source of
disagreement with the claimed −0.013% and should be treated as a fragility, not just noise.

**MDE at n=17**: pooled sd (first-30 window) = 0.585%/trade → MDE ≈ **0.40%/trade** at 80% power, α=0.05 — over
2.5× the module's own 0.15% gate bar. **The rejection at n=17 is a power-limited non-detection**: this sample
could not have reliably detected the exact effect size (0.15%/trade) the gate was set to require, let alone
anything smaller.

## R39 — S11 signal-reversal fade (n=4)

No trades could be attributed (see above). What can still be said without the specific data, generically, at
n=4: an exact two-sided sign test with all 4 outcomes the same sign gives p = 2×0.5⁴ = **0.125** — not
significant even in the best case a sign test at this n can produce, so "4セル全負" is not distinguishable from
chance by a sign test alone. Using this bot's own observed per-trade dispersion (sd≈0.585%/trade, comparable
population) as a stand-in, MDE at n=4, 80% power ≈ **0.82%/trade** — more than 5× the 0.15% gate bar. **Any
rejection at n=4 is necessarily power-limited**: no CI or exact test at this n can exclude or confirm an effect
of the size this project's own bars require. This is a structural fact about n=4, independent of what S11's
actual rule is — it does not validate or invalidate the specific −0.35 to −12.8bps-type numbers quoted for
other n=4-scale claims in this packet family, only says none of them could have been powered to detect
0.15%/trade.

## Verdict
- **R37 (C3 long-only)**: 数値差異(結論維持) — recomputed mean/CI differ from the quoted figures (see
  fragility above), but under both the PAPER and the realistic-cost premise the module stays below its own
  gate and the CI cannot exclude zero with any reliability at n=17; conclusion (rejected/stays off) holds.
- **R39 (S11 signal-reversal fade)**: 再計算不能 → **未検証**. The module/trade definition is not present in
  any file this audit may open; the headline "4セル全負" cannot be independently re-derived. The generic n=4
  power argument above applies regardless and supports treating any n=4 verdict here as provisional.

## 前提の誤り (assumption findings)
1. **PAPER cost not applied to the "net" headline** | source: R37's quoted "net −0.013%/trade" | data shows my
   closest-matching reconstruction is the **gross, no-cost** figure (−0.025%), while net-of-PAPER's-own-modeled
   10bps slippage is materially worse (−0.125%, CI negative and excluding zero under day-clustering) | bias:
   makes the module look closer to break-even than PAPER's own cost model implies | inherits to: any other
   composite-module rejection whose quoted "net" was produced the same way (radar_window's pending gate uses
   the identical "subset of champion paper trades" phrasing and would need the same check).
2. **Realized RT cost premise (2.6bps) vs directly-measured spread** | source: task premise | my own spread-only
   measurement from `spread_FX_BTC_JPY.csv` gives mean 1.94bps / median 1.78bps RT, somewhat below 2.6bps | bias:
   using 2.6bps is conservative (understates the improvement from the true 10bps→~1.8-1.9bps cost correction) |
   inherits to: every claim in this packet family re-judged under "realized ≈2.6bps."
3. **Pyramided (same-direction add) positions break naive price-diff P&L** | source: reconstruction method,
   not the claim text itself, but the claim's underlying trade-level P&L would face the same issue | data shows
   2 same-direction size-adds in the audit window that make the following STOP_LOSS's price-anchored return
   sign-wrong unless the strategy's own `loss_pct` is used | bias: could inflate OR deflate any per-trade P&L
   recomputation that anchors to first-entry price during a pyramided hold | inherits to: R36 (champion 30-trade
   headline) and any other subset gate computed from `bot.jsonl` price-diff rather than fill-level PnL.
4. **S11 has no discoverable definition in the reviewable codebase** | source: R39 | data shows zero references
   to S11/signal-reversal-fade in `composite.py`, `composite.yaml`, or any `bot.jsonl` field | bias: unknown —
   cannot be signed without the rule | inherits to: any other claim in 00_packets.md whose module also has no
   composite.yaml entry (would need the same "not recoverable" flag before trusting its n).
