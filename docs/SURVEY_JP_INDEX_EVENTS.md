# SURVEY — Nikkei 225 constituent-change closing-auction effect (2026-09-04)

Exploratory SURVEY, not a judgment. No PREREG; no strategy or parameters proposed here.
Script: `scripts/research_nk225_events.py` (deterministic, reads the frozen snapshot).
Snapshot: `backtest_data/nk225_events_20260904/` (`events.csv`, `px/*.csv`, `fetch_log.csv`).

## 1. Sources

- **Event list (effective/実施日 + code + name)**: official Nikkei Inc. PDF
  `indexes.nikkei.co.jp/nkave/archives/file/history_of_nikkei_stock_average_component_changes_jp.pdf`
  (as of 2026/4/1; covers every change since 1970). Reachable directly even though
  `indexes.nikkei.co.jp/nkave/archives/` (the listing page) and `/nkave/archives/news/`
  (the listing page) are Cloudflare-gated (403) — individual PDF file URLs under
  `/file/` and `/news/` are not. **This PDF has NO announcement dates**, only 実施日.
- **Methodology / lead-time context**: official FAQ PDF (`faq_nikkei_stock_average_en.pdf`).
  States periodic review is ~once/year (autumn, effective early Oct, announced early
  Sept — "time is taken... to ensure information is well acknowledged"); extraordinary
  replacements range from same-day-announced (bankruptcy, ~5 business days later) to
  ~2 weeks pre-announced (supervision-designated delisting candidates).
- **One real announcement date confirmed two ways** (press PDF + press coverage): the
  landmark 2000-04-24 30-stock rebalance was announced **2000-04-15** — only 9 calendar
  days (~6 trading days) of lead, much shorter than the modern ~4-week pattern (confirmed
  separately for 2023-10-02, announced 2023-09-04 = 28 days).
- ja.wikipedia "日経平均株価" §構成銘柄除外および採用の歴史 has a similar table but only
  by **year** pre-1990s and no ticker codes for older rows — checked, not used (official
  PDF is strictly better for 2000+).
- stooq.com: unreachable (proxy connection reset). Nikkei's own archives listing pages:
  Cloudflare 403. Both irrelevant once the PDF + Yahoo worked.
- **Prices**: Yahoo Finance chart API (`query1.finance.yahoo.com/v8/finance/chart/<code>.T`),
  daily OHLC, 2000-01-01..2026-09-04, incl. `^N225`. Works for new alphanumeric JPX codes
  (e.g. `285A.T`) issued since 2024.

## 2. Event list & coverage

330 raw events = **165 add/delete pairs**, effective dates 2000-03-28..2026-04-01 (all of
2000-01..2026-09 that has activity — nothing before 2000-03-28). One data-quality fix noted
in the script docstring: the table-extraction library mis-grouped the 2000-04-24 30-stock
special rebalance under the neighboring 2000-07-03 date (a page-break artifact); corrected
and cross-checked against the original 2000-04-15 Nikkei announcement PDF, which lists the
exact same 30+30 codes "適用 2000.4.24".

## 3. Survivorship (material — read before the tables)

| | usable | / total | reason breakdown when unusable |
|---|---|---|---|
| additions | 111 | /165 (67.3%) | no Yahoo series 33, insufficient calendar runway 18, code-reuse guard 3 |
| deletions | **45** | **/165 (27.3%)** | no Yahoo series 92, code-reuse guard 26, calendar runway 2 |
| by era | 2000-08: 106/194 (54.6%) usable · 2009-16: 29/54 (53.7%) · 2017-26: 70/82 (85.4%) | | |

**Deletions survive far less often — mechanically, not randomly**: a stock is deleted from
Nikkei 225 because it is illiquid, was acquired, delisted, or moved off Prime — the same
reasons Yahoo's daily series stops. The 45 deletions actually measured are the minority that
kept trading afterward (renamed/absorbed-but-still-listed, or simply demoted for liquidity
without delisting). **Read the deletion rows as biased toward the "survived the demotion"
subset**, not representative of all deletions historically. The code-reuse guard drops any
ticker whose fetched series starts *after* the event date (JPX code recycled by an unrelated
later listing) — 26 of those on the delete side alone.

## 4. Announcement-date caveat (run-up leg only)

No source gave per-event announcement dates cheaply (would need ~150 individual press-PDF
fetches, out of scope for a survey). The **run-up** leg below uses `announce_day :=
rebalance_day − 20 trading days` (~1 calendar month) as a **fixed, unobserved proxy** — not
sourced per event. This is known wrong in both directions (6 trading days for the 2000-04-24
event vs. ~19 for the 2023 example checked), and the 2000-04-24 event alone supplies 16 of
the 56 "add, 2000-2008" observations, landing its wrong 20-trading-day lookback squarely on
the March 2000 dot-com peak/crash — inflating that cell's run-up to +3370bps (n=16) vs. +1101bps
for the rest of the era's adds (n=40), neither of which should be trusted at face value.
**Treat run-up as directionally-illustrative context only.** The auction-pressure and
next-day-reversal legs below do **not** depend on this estimate and are the reliable numbers.

## 5. Results (market-adjusted log returns vs ^N225, same calendar day; bps)

Legs: run-up (announce~→rebalance close, caveated §4) · close-vs-open & close-vs-prevclose
(pressure into the rebalance-day close) · **next-open reversal** (close(rebal)→open(next) —
the tradeable cell: long for deletions, short for additions) · next-day full · +5 day.

```
[add    2000-2008] n=56   runup +1749bps t=5.57 | c-vs-o +444 t=5.47 | c-vs-pc +847 t=3.27 | reversal -189 t=-3.96 win21% | full -407 t=-6.68 | +5d -599 t=-4.92
[add    2009-2016] n=17   runup  +512bps t=1.86 | c-vs-o   -1 t=-0.01| c-vs-pc +474 t=1.02 | reversal  -74 t=-1.09 win29% | full -157 t=-1.16 | +5d -366 t=-1.78
[add    2017-2026] n=38   runup  +318bps t=2.10 | c-vs-o  +51 t=1.47 | c-vs-pc  +57 t=1.44 | reversal  -45 t=-1.41 win29% | full  -79 t=-1.64 | +5d  -89 t=-0.94
[add    pooled   ] n=111  runup +1070bps t=5.84 | c-vs-o +241 t=4.82 | c-vs-pc +520 t=3.42 | reversal -122 t=-4.23 win25% | full -256 t=-6.01 | +5d -389 t=-4.94

[delete 2000-2008] n=12   runup -1649bps t=-6.88| c-vs-o  -73 t=-0.87| c-vs-pc -311 t=-3.05| reversal  +32 t=0.78  win58% | full -153 t=-1.08 | +5d  -44 t=-0.24
[delete 2009-2016] n= 5   runup -1775bps t=-2.64| c-vs-o  +95 t=1.06 | c-vs-pc  +45 t=0.50 | reversal  +46 t=0.89  win60% | full  -17 t=-0.16 | +5d -139 t=-0.85
[delete 2017-2026] n=28   runup  -203bps t=-0.89| c-vs-o  +56 t=0.78 | c-vs-pc  -16 t=-0.20| reversal  +37 t=1.24  win54% | full  +61 t=1.45  | +5d  +48 t=0.43
[delete pooled   ] n=45   runup  -763bps t=-3.81| c-vs-o  +26 t=0.51 | c-vs-pc  -88 t=-1.41| reversal  +36 t=1.67  win56% | full   -5 t=-0.10 | +5d   +3 t=0.03
```

**Matched random control** (same tickers, 8 random non-event trading days each, ≥10-trading-day
buffer from any real event, same next-open-reversal cell, market-adjusted): n=1146, **+0.1bps
t=0.03 win 50.4%** — indistinguishable from zero, as a well-behaved control should be.

**Unit cost, deletions** (100 shares × close(rebalance day), JPY, n=45): min 11,000 · p25
71,800 · median 99,400 · p75 163,200 · max 527,700 · mean 132,433. Well inside single-unit
capital feasibility (contrast with the ¥20M cross-sectional floor in `KNOWLEDGE_JP.md`).

## 6. Read

The closing-auction print does carry visible one-day pressure — additions rise into the
rebalance-day close (close-vs-open pooled +241bps t=4.82, close-vs-prevclose +520bps t=3.42)
and that pressure **reverses at the next open** (pooled −122bps t=−4.23, win only 25%, vs. a
control that centers on zero) — consistent with passive buying pushing the close up and
liquidity providers/arb unwinding into the next session. Deletions are the mirror in sign but
much weaker and not era-stable: pooled next-open reversal is +36bps (t=1.67, win 56%),
driven mostly by 2017-2026 (+37bps, n=28) with 2000-2008 (n=12) and 2009-2016 (n=5) too thin
to read; deletion's close-day pressure itself is inconsistent in sign across eras, and the
27% usable rate (survivorship, §3) means the deletion result is the biased "survived" subset,
not the full population — the true deletion effect could be stronger or weaker. The addition
side is the more trustworthy half of this survey (67% coverage, consistent sign and
significance across all three eras for the pressure and reversal legs); its effect also
shrinks by era (2000-2008 reversal −189bps → 2017-2026 −45bps), which reads as the well-known
crowding/decay pattern for index-effect trades elsewhere, though n per era (56/17/38) is
modest for asserting a clean monotonic decline. Whether either side clears round-trip cost at
tradable size, and which exact entry/exit rule to use, is out of scope here — that is a
PREREG decision for the lead, and it should re-source real announcement dates and re-audit
the survivorship-affected deletion tickers by hand before any selection is made on this data.
