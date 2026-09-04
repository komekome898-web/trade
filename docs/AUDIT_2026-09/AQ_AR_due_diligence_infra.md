# AQ / AR — due diligence & infra fact-check (live, 2026-09-04)

Non-statistical fact packets per PROTOCOL.md. Source: 00_packets.md §2 rows AQ (line 291),
AR (line 292), and §3 context (lines 301-311). No other docs/ files opened.

## AR — data-lifespan / infra facts (live access, 2026-09-04 UTC)

| # | Claim (repo) | Live check | URL | Verdict |
|---|---|---|---|---|
| 1 | bitFlyer public `/v1/executions` retention = 31 days | Queried `FX_BTC_JPY` with `before=` at id offsets. At ~28 days back: data returned normally. At ~2M id (~28-35d) back: API itself returns `{"status":-156,"error_message":"Execution history is limited to the most recent 31 days."}` — exact wording, live today. | `https://api.bitflyer.com/v1/executions?product_code=FX_BTC_JPY&count=1&before=<id>` | **確認** — exact match, server-stated, not inferred |
| 2 | OKX open-interest history "~30 days fixed" | `open-interest-volume` endpoint, `period=1H`, `begin`/`end`: returns data through 30 days ago, errors `{"code":"50030","msg":"Illegal time range"}` at 31 days ago and beyond (binary-searched boundary sits between day 30 and day 31). | `https://www.okx.com/api/v5/rubik/stat/contracts/open-interest-volume?ccy=BTC&period=1H&begin=..&end=..` | **確認** for OI (1H granularity) |
| 3 | OKX L-S ratio same "~30 days" limit, no paging | `long-short-account-ratio-contract` (instId=BTC-USDT-SWAP, period=1H) does **not** hard-error at 30/31/32/60 days — returns data (code 0) at 60 days back, only goes empty (still code 0, not an error) somewhere between 60-90 days. Behaves differently from the OI endpoint: soft/empty-data limit further out, not a hard 30-day wall. Also, no `after`/cursor param exists on either endpoint — confirmed no true pagination; only the `begin`/`end` window, which for the 5m granularity actually errors at only ~2-3 days back (tighter than 30d), while 1H reaches ~30d. | same host, `long-short-account-ratio-contract` | **数値差異** — repo's "OKX ≈30日固定" is accurate for OI but not for L-S ratio, and the exact ceiling is period-dependent (5m ≠ 1H) |
| 4 | Binance `data.binance.vision` archive: monthly klines/fundingRate/metrics | S3 listing (`list-type=2`) direct to bucket. Monthly **klines** BTCUSDT: 2017-08 → 2026-07 (216 keys, available). Monthly **fundingRate** BTCUSDT (futures/um): 2020-01 → 2026-08 (160 keys, available). Monthly **metrics** folder: 0 keys — **metrics does not exist as a monthly product**; it exists only under `data/futures/um/daily/metrics/BTCUSDT/`, 2020-09-01 onward (≥1000 daily files, truncated listing). | `https://s3-ap-northeast-1.amazonaws.com/data.binance.vision?list-type=2&prefix=...` | **数値差異** — klines/fundingRate confirmed monthly & long-lived; "metrics" monthly does not exist, only daily |
| 5 | VM ephemerality (deploy/session storage is not durable) | Not independently checkable via live external access — this is a claim about this repo's own compute environment, not a third-party API. Per task instruction, recorded as **procedural**, not an empirical/statistical claim to re-derive. | n/a | **procedural (not checked)** |

## AQ — external-tool due-diligence facts (primary source only)

| Claim | Live check | URL | Verdict |
|---|---|---|---|
| Freqtrade supported-exchange list (used to argue against/for adopting it) | Fetched `docs/index.md` from the `develop` branch directly. Live official list: Spot = Binance, BingX, Bitget, Bybit EU, Bybit, Gate EU, Gate, HTX, Hyperliquid, Kraken, MyOKX, OKX, + "potentially many others via ccxt, not guaranteed". Futures = Binance, Bitget, Bybit, Gate, Hyperliquid, Kraken, OKX. Community-tested = Bitvavo, Kucoin. **bitFlyer appears nowhere** in any tier. | `https://raw.githubusercontent.com/freqtrade/freqtrade/develop/docs/index.md` | **確認** — bitFlyer absent from Freqtrade's official/community exchange support, as of 2026-09-04 |
| "crypto MCP list" (external MCP tool survey) | No stable, named primary source is identifiable from the packet row text alone (row 291 says only "外部ツール評価…crypto MCP" with no URL, and the underlying evaluation doc is off-limits under PROTOCOL.md). There is no single canonical "crypto MCP list" to fetch and diff against. | — | **未確認 — 到達不能**(一次資料URL不明、対象ドキュメントは監査規則で開示禁止) |

## 前提の誤り (assumption findings)

1. **premise**: OKX OI and L-S-ratio history share one "~30-day fixed" ceiling (as stated together in P2/AR row).
   **source in claim**: 00_packets.md line 113 (P2) / line 292 (AR), bundles both series under one number.
   **what the data shows**: OI (`open-interest-volume`, 1H) hard-errors (`Illegal time range`) beyond 30 days; L-S ratio (`long-short-account-ratio-contract`, 1H) still returns real (non-error) data at 60 days and only goes empty later. The two endpoints are not governed by the same limit.
   **direction of bias**: P2's OI-side "30-day wall → lost" framing is correct; but any statement that treats the **L-S ratio series** as similarly capped at exactly 30 days understates how much L-S history could still be pulled live today (understates recoverable data / overstates "lost").
   **inherits**: P2 (OI・L-S極値の一部)、L14 の OI 関連 lift 値、PR1 の GMO-cal 時系列 — anywhere the repo cites "OKX 30日" as a blanket ceiling for both series should specify OI vs L-S separately.

2. **premise**: implied granularity-independence — that "30 days" is a single number regardless of bar size (1H vs 5m).
   **source in claim**: same AR/P2 rows, no granularity qualifier given.
   **what the data shows**: for `open-interest-volume`, `period=5m` with explicit `begin`/`end` errors at only ~3 days back (`Illegal time range`), far tighter than the 30-day ceiling measured at `period=1H`. The "~30 days" figure only holds at the coarser (1H/1D) granularity actually likely used for daily bucketed features; a 5m-level reconstruction would already be far more history-starved than "30 days" suggests.
   **direction of bias**: understates how much of the *high-frequency* OI signal is actually unrecoverable — the real ceiling for fine-grained OI history is much shorter than 30 days.
   **inherits**: any composite/backtest column built from sub-hourly OKX OI bars.

3. **premise**: `data.binance.vision`'s monthly archive covers klines, fundingRate, **and** metrics symmetrically (as the AR row title implies by listing them together).
   **source in claim**: 00_packets.md line 292 parenthetical "Binanceアーカイブ".
   **what the data shows**: klines and fundingRate exist as monthly zips; **metrics (open interest / top-trader long-short ratio hourly snapshots) is daily-only**, never published as monthly bundles.
   **direction of bias**: minor operational risk — any pipeline that assumes a monthly `metrics` key exists (mirroring klines/fundingRate) will silently get zero files; must fetch ~daily-file-count-many objects instead of one monthly zip per month.
   **inherits**: any BTC-cross-venue OI feature that sources Binance OI/L-S history from `data.binance.vision` rather than the live 30-day REST window.

4. **premise (AQ)**: none found for the Freqtrade fact itself — the live list matches what a "bitFlyer not supported" due-diligence conclusion would need.

5. **premise (AQ, crypto MCP)**: the claim is unverifiable **as an audit input**, not necessarily wrong — but the packet's "n/a, due-diligence only" framing (line 291) should not be read as "verified"; it is currently un-sourced from this vantage point. **inherits**: AQ's own due-diligence conclusion on the MCP-list, until a primary URL is added to the underlying evaluation doc.

## Files/URLs accessed
`api.bitflyer.com/v1/executions` (live), `www.okx.com/api/v5/rubik/stat/contracts/open-interest-volume` (live),
`www.okx.com/api/v5/rubik/stat/contracts/long-short-account-ratio-contract` (live),
`s3-ap-northeast-1.amazonaws.com/data.binance.vision` (S3 listing API, live),
`raw.githubusercontent.com/freqtrade/freqtrade/develop/docs/index.md` (live).
Repo files read: `docs/AUDIT_2026-09/PROTOCOL.md`, `docs/AUDIT_2026-09/00_packets.md` (grep only, lines cited above).
All checks performed 2026-09-04 (UTC), against live/current endpoint state — figures reflect today, not necessarily
the state when the original claims were written.
