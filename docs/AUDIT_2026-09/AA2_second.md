# AA (second/blind) audit — L18, R25

Files read: `docs/AUDIT_2026-09/PROTOCOL.md`; grep rows `AA`,`L18`,`R25` of `docs/AUDIT_2026-09/00_packets.md`;
`data/latency/ws_vm.csv` (only file under `data/latency/`); `config/config.yaml`; grep of `src/`,`config/` for
latency/VPS cost constants. Script: `audit_AA2.py` in the scratchpad path named in PROTOCOL. No forbidden files
opened.

L18 and R25 both restate the same underlying claim (KNOWLEDGE §2 "law" and §3 "rejection ledger" entries citing the
same source `ah`): an edge×latency curve concentrated in the first 0.2s, an opportunity frequency of 0.84/day at
0.02BTC book depth, a best economic case of +27 JPY/day, against a WS-hosting server cost of 33–50 JPY/day → the
line is hardware-reachable but economically closed. Packet table marks both `partial: data/latency/` with the note
"session ended, at risk of loss, only summary values survive in the report."

## L18

1. **Denominator**: The only surviving raw file is `data/latency/ws_vm.csv`, 379 rows, 204 unique after removing
   exact duplicate rows (`rts`,`exec_date`,`delay_s` identical) — 175/379 = 46% of rows are exact duplicates.
   `exec_date` spans 2026-08-28T00:13:06Z to 2026-08-28T00:22:40Z, i.e. **9.6 minutes of one session**, 191 distinct
   `rts` receive-timestamps. There is no "edge" column, no PnL/opportunity column, no board-depth column, and no
   per-opportunity frequency column anywhere in the file — only `rts` (receive time), `exec_date` (exchange
   timestamp), `delay_s` (= rts − exec_date, a pure network/WS message-delay measurement).
2. **Controls**: Cannot be built. A placebo/shuffle or sign-reversed control requires an edge metric to shuffle;
   none exists in this file. Not answerable from available data.
3. **Translation**: Cannot be recomputed. Neither the +27 JPY/day edge figure nor the 33–50 JPY/day server-cost
   figure has any source in `config/*.yaml` or `src/` (grepped for `latency`, `vps`, `サーバ費`, `レイテンシ` — the
   only hits are unrelated health-check thresholds `degraded_latency_ms`/`critical_latency_ms` in
   `config/config.yaml`, and monitoring/exchange-client latency instrumentation in `src/bot/monitoring/`,
   `src/bot/exchange/`, none of which carries a JPY cost constant). No fee/cost key exists to net a server-hosting
   cost against.
4. **Relative vs absolute**: The file's `delay_s` distribution (unique rows): min 0.038s, mean 0.067s, median
   0.059s, p90 0.081s, p99 0.174s, max 0.593s; 99.0% of samples are < 0.2s. This shows message-delivery latency is
   almost always sub-0.2s in this single 9.6-minute session — but that is a statement about **network delay**, not
   about **edge decay by latency bucket**, which is what the claim needs. No edge-vs-latency-bucket table can be
   built.
5. **Definition side-effects**: Unknown — the "0.84回/日" frequency and "0.02BTC" depth figures cannot be checked
   for exclusions since no event/opportunity definition or log survives in this file.
6. **Data validity**: 46% exact-duplicate rows in the raw CSV is itself a data-quality problem (likely duplicate
   WS callback registrations); after dedup, n drops from 379 to 204, and the sample is a single 9.6-minute window,
   nowhere near a full day, let alone enough days to support a 0.84/day frequency estimate.
7. **Selection contamination**: Cannot assess — no sweep grid or parameter list survives with the data.
8. **Simplest alternative explanation**: Not testable — no edge series exists to test against volatility/
   time-of-day/volume confounds.
9. **Consistency**: No second latency file exists under `data/latency/` (directory contains only `ws_vm.csv`) to
   cross-check against.
10. **Falsification/MDE**: With only 204 unique network-delay samples spanning 9.6 minutes and zero paired edge
    observations, no MDE for a JPY/day economic claim can be computed — the sample cannot even estimate a daily
    opportunity rate, since it does not span a day.

Claimed vs recomputed:

| quantity | claimed | recomputed | note |
|---|---|---|---|
| edge concentration window | first 0.2s | n/a (no edge data) | only network delay available, 99% < 0.2s |
| frequency | 0.84/day | not derivable | 9.6 min of data, no event log |
| best case | +27 JPY/day | not derivable | no cost/edge source found |
| server cost | 33–50 JPY/day | not derivable | no cost constant found in config or src |

Verdict: 再計算不能

## R25

Same source data and same finding as L18 (R25 is the rejection-ledger phrasing of the identical +27 vs 33–50
JPY/day economic-closure result, citing the same evaluation id `ah`). All ten questions above apply unchanged:
the only surviving artifact is a 9.6-minute, 204-unique-row WS message-delay log with no edge, frequency, depth,
or cost columns, and no cost constant exists elsewhere in the repo to reconstruct the 33–50 JPY/day server-cost
side of the comparison. The "hardware reachable / economically closed" conclusion cannot be independently
re-derived from any data available to this auditor; it is currently only reported as a summary value, consistent
with the packet table's own "partial … at risk of loss" annotation.

Claimed vs recomputed: identical table to L18 above (same underlying summary figures, same absence of raw
opportunity data).

Verdict: 再計算不能

## 前提の誤り

- premise: an edge×latency curve and a per-day opportunity frequency (0.84/day) exist and were measured | source:
  L18/R25 text | what the data shows: only a 9.6-minute, single-session WS message-delay log (`delay_s` = network
  receive delay, not economic edge) survives; no edge, opportunity-count, or board-depth column exists anywhere
  under `data/latency/` | direction of bias: the claim cannot currently be verified in either direction — its
  numeric content (0.2s, 0.84/day, 27円, 33–50円) is unsupported by any recoverable data, so confidence in the
  precise figures should be lowered even though the qualitative conclusion ("economically closed") may still be
  correct | inherits: any other claim in KNOWLEDGE that cites source `ah` or reuses this 27円/33–50円 comparison.
- premise: a server-hosting cost of 33–50 JPY/day is a known constant | source: L18/R25 text | what the data shows:
  no such constant exists in `config/*.yaml` or `src/` (only unrelated latency *threshold* configs, in
  milliseconds, for health monitoring) | direction of bias: unverifiable — the comparison's cost side is currently
  asserted, not derived from data in this repo | inherits: any claim reusing this same server-cost figure as a
  fixed input.
- premise: the raw latency log is clean | source: implicit in "partial: data/latency/" | what the data shows: 46%
  of raw rows in `ws_vm.csv` are exact duplicates (175/379); after dedup only 204 rows / 9.6 minutes remain |
  direction of bias: makes any frequency/percentile statistic drawn from the raw file (without dedup) look roughly
  2x denser than reality | inherits: any future recomputation attempt from this same file that does not dedup
  first.
