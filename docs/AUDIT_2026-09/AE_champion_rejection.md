# AE — champion (xborder_momentum) rejection, R36

Blind audit per `docs/AUDIT_2026-09/PROTOCOL.md`. Analysis script kept at
`/tmp/.../scratchpad/audit_AE.py` (not committed to `scripts/`, per budget).
Claim (R36, grep'd from `00_packets.md` §1.3 only): champion 30取引 net
−0.148%/取引, CI[−0.243,+0.063].
## Method (trade reconstruction)
`paper_logs/bot.jsonl` has 20,709 `decision` events for `FX_BTC_JPY` (+117
for an unrelated `XRP_JPY` HOLD-only stream), 126 of them `ORDER_SENT`. Each
flat-to-entry (`BUY`/`SELL`) opens a round trip; it closes on the next
`CLOSE`, `STOP_LOSS`, or an opposite-sign entry (`main.py` closes an
opposite position under the *same* signal label — a SELL closing a long is
logged as `strategy_signal:"BUY"`, not `"CLOSE"` — so side-tracking, not
label-matching, is required). This reconstructs **62** round trips
end-to-end (08-20→09-04). The cumulative `PnL` field was **not** used — it
resets to 0 mid-stream ≥3 times with no matching restart/flat event nearby,
so all P&L below is recomputed from entry/exit prices instead.

A sliding 30-trade window search over the 62 reproduces the claimed
−0.148%/trade to 4 decimals at exactly one location: index 26–55, entry
2026-08-24T16:27 → exit 2026-09-02T13:58 UTC — this claim's population, a
snapshot near 2026-09-02, not "all history" (26 earlier + 6 later trades
sit outside it, §1). Two reconstruction anomalies (one signal-flip exit;
one same-direction re-entry consistent with async fill-booking lag between
the paper gateway and `portfolio.position_size`) both fall in the excluded
pre-window 26, not in the claimed 30 — they don't affect this claim.
## 1. Denominator
30 round trips, FX_BTC_JPY, PAPER, 2026-08-24T16:27–09-02T13:58 UTC, of 62
recoverable in the full log. Pre-window 26 trades: mean −0.293%/trade.
Post-window 6 trades (closed since this claim was judged): mean
−0.009%/trade — the trailing record has moved toward breakeven since.
## Claimed vs. recomputed
| cost regime | mean net%/trade | trade-level 95% CI | day-clustered 95% CI (n_days=9) |
|---|---|---|---|
| claimed (paper, as judged) | −0.148 | [−0.243, +0.063] | — |
| (a) paper-as-logged (fee 0% + 0.05%/side slippage = 10bps RT) | **−0.1476** | [−0.274, −0.008] | [−0.209, −0.093] |
| (b) realized cost floor (fee 0% + measured spread/slippage ≈2.6bps RT) | **−0.0736** | [−0.200, +0.067] | [−0.136, −0.018] |
| (c) gross (0 cost) | **−0.0476** | [−0.175, +0.092] | [−0.110, +0.009] |

(a) reproduces the claim almost exactly. Under realistic cost (b) the mean
halves and the trade-level CI straddles zero; only the day-clustered CI
still (barely) excludes it.
## 2. Controls
Sign-reversed mirrors trivially (+0.148% under a). Shuffled-exit placebo
(5,000 resamples, entries re-paired with a random other trade's exit,
regime a): mean of shuffled means −0.384%, 5–95% band [−0.743, −0.027].
Observed −0.148% sits inside this band, not in either tail — the true
chronological pairing isn't statistically distinguishable from a random
pairing at this n. State-conditional: no explicit regime is claimed;
§4/§9 substitute exit-type and horizon splits.
## 3. Translation / cost derivation
`config/products.yaml`: `FX_BTC_JPY taker_fee_pct: 0.0`. `paper.py`'s
`PaperExecutor` is wired in `main.py` with `taker_fee_pct=self.product.taker_fee_pct`
(→0.0), `slippage_pct=costs.slippage_pct` (0.05%, `config.yaml`) per side →
**10bps RT**, confirming the premise's paper-cost number by tracing the
code, not quoting it. Realized cost: mean quoted spread over all 16 days of
`ticker_*.csv.gz` (1,589,458 ticks) = **2.03bps RT** (premise quoted
≈1.9bps — same order). With fee 0% this supports the premise's ≈2.6bps
realized floor (spread ~2bps + ~0.6bps slippage beyond quotes; slippage not
independently re-measured from `executions_*.csv.gz` under budget). On
0.01 BTC/trade, 30 trades: (a)≈−4,428 JPY, (b)≈−2,208 JPY, (c)≈−1,428 JPY.
## 4. Regime dependence — exit-type attribution
| exit type | n | share | mean net% (a) | mean net% (b) | mean net% (c) |
|---|---|---|---|---|---|
| STOP_LOSS (0.5% protective stop) | 6 | 20% | −0.572 | −0.498 | −0.472 |
| CLOSE (signal fade) | 24 | 80% | −0.042 | **+0.033** | **+0.059** |

Under realistic-cost and gross regimes the 24 signal-exit trades are net
**positive**; the entire realized loss comes from the 6 stop-outs (~14x
larger per trade). The champion's apparent failure is a cost-and-stop
artifact, not a broad signal failure.
## 5/6/8. Definition side-effects, validity, alternative explanation
0/30 trades touch the 19:00–19:10 UTC maintenance window; no other
gap/duplicate found beyond the out-of-window PnL-field resets (§method).
Simplest alternative explanation for the stop-dominated loss: the fixed
0.5% stop is close in magnitude to ordinary short-horizon volatility here
(§9: 30–60min moves average 0.37–0.43%) — a tight stop on a plain
momentum-follow gets clipped by normal noise often, regardless of signal
quality; this reproduces the STOP_LOSS loss share without a broken signal.
## 7. Selection contamination
Not assessable from allowed files: `config.yaml` carries one active
parameter set (k=30, thr=0.8%, exit=0.05%), no visible sweep here
(prereg/research docs off-limits to this audit).
## 9. Consistency — "entries precede movement"
Mean |tape-mid move| after the 30 entries vs. 2,000 random times, same
period (`ticker` tape):

| horizon | champion entries | random control | ratio |
|---|---|---|---|
| 5 min | 0.151% | 0.113% | 1.33x |
| 30 min | 0.367% | 0.234% | 1.57x |
| 60 min | 0.430% | 0.319% | 1.35x |

Confirms the qualitative premise across 3 independent horizons — but the
movement isn't reliably directional at the champion's stop tightness (§4),
which is why it doesn't convert to positive expectancy under paper cost.
## 10. Falsification + MDE
Falsification: if realized-cost mean net%/trade on a fresh 30-trade OOS
block is ≤ −0.20%/trade (day-clustered CI excluding 0), the "cost artifact"
reading here is wrong and the signal itself is lossy. SD/trade = 0.381%
(same across cost regimes — cost is a constant shift). MDE at n=30, α=.05
two-sided, 80% power ≈ **0.195%/trade** — larger than the claimed/recomputed
effect (−0.148%): n=30 could not reliably detect an effect this size even
if real; the CI's borderline exclusion of zero under (a) is closer to luck
than power.
## Verdict: 再現 (headline number reproduces)
Recomputed mean (a) = −0.1476%, matching claimed −0.148% almost exactly
from an independently reconstructed trade list and a traced (not quoted)
cost model; the CI reproduces in shape though not to the digit (bootstrap
detail differs). **But** the rejection's evidentiary weight is much thinner
than the headline suggests once the premises below are corrected.
## 前提の誤り (assumption findings)
- **Cost regime (10bps paper vs. ≈2.6bps realized)** | source: PAPER
  judgment's cost model | data: both numbers are real (paper path traced;
  realized floor supported by 2.03bps measured spread) | bias: paper model
  overstates RT cost ~4x — the single largest lever here, turning a
  marginally-profitable signal-exit population (+0.033–0.059%/trade, §4)
  into a net-negative headline | inherits to: every PAPER-judged claim using
  `costs.slippage_pct` as ground truth rather than a ceiling.
- **"Stop bundle of 7 stops"** | source: packet framing | data: only ONE
  mechanism produced any of the 30 exits — the fixed 0.5% `stop_loss_pct`
  (6/30). The other ~6 configured guards (`MAX_DAILY_LOSS_JPY`,
  `MAX_DRAWDOWN_PCT`, `MAX_CONSECUTIVE_LOSSES`, `MAX_API_ERRORS_IN_ROW`,
  `sfd_guard_pct`, market-data staleness/spread — `risk_limits.yaml`,
  `config.yaml`) never fired here; the log's only 2 `kill_switch` events
  (market-data staleness) occurred at `position_size:0.0`, unrelated |
  bias: a single fixed-threshold stop is described as a multiply-
  corroborated "bundle," overstating independence | inherits to: any
  packet citing "stop bundle" for this or other strategies sharing
  `stop_loss_pct`.
- **"30 trades" as a complete/final record** | source: claim's n | data: a
  fixed historical window (index 26–55 of 62 recoverable), not the full or
  most-recent record; 6 later trades (mean −0.009%) and 26 earlier
  (mean −0.293%) sit outside it | bias: none in the number itself, but
  stale as of 2026-09-04 | inherits to: any gate/packet treating this
  verdict as current without re-pulling the log.
- Cumulative `PnL` field resets to 0 at several points with no matching
  flat/restart event nearby — unusable for P&L reconstruction (price-based
  method used instead; none of the resets fall inside the claimed window).
## Files read
`docs/AUDIT_2026-09/PROTOCOL.md`; `00_packets.md` (grep `R36` only);
`paper_logs/bot.jsonl`; `paper_logs/status.json`; `paper_logs/tape/ticker_*.csv.gz`
(all 16); `paper_logs/tape/executions_20260820.csv.gz`, `board_top5_20260820.csv.gz`
(structure sample); `src/bot/strategy/xborder_momentum.py`;
`src/bot/execution/paper.py`; `src/bot/main.py` (order/signal/stop logic);
`config/config.yaml`; `config/products.yaml`; `config/composite.yaml`;
`config/risk_limits.yaml`.
