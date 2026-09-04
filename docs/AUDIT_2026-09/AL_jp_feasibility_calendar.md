# Packet AL — JP株式・先物の実現可能性(資本床/暦アノマリー/日銀ETF/2脚/NT) — blind audit

Claim IDs: JPL1, JPL2, JPR1, JPR2, JPR3, JPR5, SV2 (as listed in `00_packets.md` §1.9/1.10/1.13, packet-AL row).
**ID-mapping note:** the task brief's prose for "JPR5" ("US-style two-leg, intraday≈0") does not match
`00_packets.md`'s verbatim JPR5 (NT-ratio mean reversion, held/pending) — that two-leg text is verbatim **JPR4**
in §1.10. JPR5 is audited below as actually written; the two-leg claim is separately audited under its correct
ID (JPR4) since the packet's own "specific requirements" ask for it.

Files read: `PROTOCOL.md`; `00_packets.md` (grep + lines 180-231, §1.9-1.13 tables only); `n225f_225labo_20260828/
manifest.json`, `day_session_daily.csv.gz` (heads of `night_session_daily.csv.gz`/`full_day_daily.csv.gz` only);
`yutai_20260904/manifest.md`, `universe.csv`, `px.tar.gz` (900 per-ticker CSVs); Yahoo chart API JSON for `^N225`,
`1321.T`, `9983.T`, `6861.T`, `8035.T`; `config/products.yaml` (no JPX fee constant — repo config is BTC/JPY-CFD only).

## 1. Capital floor — JPL1 / JPR1 / SV2 (same underlying claim, 3 angles)

**Denominator:** 900 TSE Prime/Standard tickers in `yutai_20260904/universe.csv` (600 perk + 300 non-perk control),
last available close per ticker (≈2026-09-03), lot = close×100 shares (単元株). All 900 had price data.

| Statistic | Recomputed |
|---|---|
| Lot-cost percentiles (JPY) | p10 ¥42,990 / p25 ¥84,050 / **p50 ¥163,750** / **p75 ¥287,850** / p90 ¥435,650 / p99 ¥1.27M / max ¥3.31M |
| 30-name **random** equal-unit basket (5,000 draws) | p10 ¥5.19M / **p50 ¥6.58M** / **p75 ¥7.64M** / p90 ¥8.91M |
| 27-random + 3 known high-price anchors (Fast Retailing 9983 ¥6.80M/lot, Keyence 6861 ¥7.80M/lot, Tokyo Electron 8035 ¥5.33M/lot) | p10 ¥24.5M / **p50 ¥25.85M** / p75 ¥26.79M |

**Verdict: 数値差異(結論維持).** The claimed ¥20M floor is **not reproducible from the permitted dataset alone**
— a 30-name basket drawn from `yutai_20260904` costs ¥6.6-7.6M at the median/p75, less than half the claim. But
that dataset is *not* a representative TSE population: its manifest states the 300-name control group was
explicitly filtered to the perk sample's price band (¥161-4,759/share), and perk-program issuers self-select for
low unit price to attract small retail holders — max lot cost in the whole 900-name file is ¥3.31M, whereas
ordinary, un-excluded Nikkei 225 constituents (Fast Retailing, Keyence, Tokyo Electron, and others) run ¥5-8M/lot.
Forcing in just 3 such names lifts the 30-name basket to ¥24.5-26.8M — *above* the claimed floor. A genuinely
sector-diversified 30-name basket (not a retail-affordable-biased sample) plausibly sits in the ¥20-28M range, so
the claim's order of magnitude survives, but the exact ¥20M figure could not be independently pinned down here —
it is highly sensitive to which 30 names are chosen, and no unbiased full-market price file was available under
the audit's data restrictions. "Odd-lot routes don't help" is a structural/execution-mechanics claim (mini-kabu
odd-lot orders in Japan execute only at specific windows, not continuously) that cannot be tested from price data;
flagged as **未検証** here, plausible but not independently confirmed.

**MDE/falsification:** n=900 is enough to place the lot-cost median to within a few thousand yen; the floor
number's uncertainty is *population selection*, not sample size — no amount of additional draws from the biased
900-name file fixes this.

## 2. Calendar anomalies dead — JPL2 / JPR2

**Denominator:** `^N225` daily closes, Yahoo, 1990-01-05..2026-08-31, n=8,995 trading days (JST calendar dates),
8,994 log-returns. 567 business-day gaps identified as holidays; 434 pre-holiday days; SQ = 2nd Friday of month,
matched to an actual trading day in 432/440 months.

| Anomaly | n | mean (bps) | Newey-West t | shuffle p |
|---|---|---|---|---|
| Turn-of-month window (day −1..+3 around month-end) | 2,197 | +2.67 | 0.83 | 0.92 |
| — worst single offset (day +2) | 439 | +11.45 | 1.69 | 0.35 |
| SQ day | 432 | +0.20 | 0.03 | 0.97 |
| SQ+1 | 432 | −2.53 | −0.31 | 0.52 |
| Monday | 1,684 | −6.04 | −1.49 | 0.96 |
| Tuesday..Friday | 1,824-1,831 | −3.4..+5.3 | 0.67..1.56 | 0.29-0.99 |
| Pre-holiday | 434 | −0.71 | −0.12 | 0.81 |

All full-sample |t| < 2, matching JPR2's headline. **By decade** (24 cells: 4 anomalies × 4 decades), 23/24 stayed
|t|<2; the one exception is **1990s Monday, t=−2.32 (n=478, mean −18.3bps)** — a real, if isolated, deviation from
"all |t|<2 at every horizon" that the full-sample number (t=−1.49) dilutes away. Shuffled-return controls give
p>0.15 almost everywhere, consistent with no genuine structural anomaly. Sign-reversed check: none of the point
estimates flip conclusion (already straddling zero).

**Simplest alternative explanation:** none needed — the effects are statistically indistinguishable from the
shuffled-return null, so there is nothing to explain away.

**MDE / falsification:** daily σ = 149bps. At n=8,995 (full sample) the t=2 MDE is 3.2bps; for the 5-day TOM
window (n≈2,197/26yr-equivalent) it is 6.4bps; for a once-a-month SQ day (n=432) it is 14.3bps. Reproducing JPR2's
own claim that "t=2 needs ~265 years": at n=265yr×245d≈64,925, MDE=1.17bps — i.e. only an anomaly smaller than
~1bps would need that much data, which matches the near-zero point estimates here (SQ day: 0.20bps). **Verdict:
再現**, with one flagged sub-period exception (1990s Monday) noted below.

## 3. BOJ ETF flow structurally ended — JPR3

Public web search (BOJ's own `boj.or.jp` ETF page path 404'd; a general reference page fetch was egress-blocked)
corroborates via news summaries (dated 2025-09) that BOJ announced/began **selling** ETF holdings in Sept 2025,
which presupposes purchases had already stopped — consistent with a 2024-03 purchase-program end. The claimed
**0.05%-of-proceeds sale pace** could not be confirmed from a primary source within budget: **未検証**.

Attempted price-mechanism test: "sharp morning decline (low ≤ open −1%) → afternoon recovery into close," pre- vs
post-2024-03-19, on day-session futures OHLC (n=2,216 pre, 169 post). Recovery ≈67bps (t=27.9) pre vs ≈80bps
(t=10.8) post — **not discriminating**: "close ≥ low" holds by construction every day (unconditional mean ≈74bps
too), so this proxy can't isolate a BOJ-specific afternoon-buying signature. Needs intraday timestamps, only in
`bars_1min.csv.gz` (2025-12-30 on, entirely post-cutoff — no pre/post contrast possible).
**Verdict: 数値差異(結論維持)** for the structural claim (corroborated); mechanism and 0.05% figure: **未検証**.

## 4. JPR5 as actually defined (NT倍率平均回帰, held/pending — NOT the "US two-leg" text in the task brief)

`00_packets.md` §1.10: "NT倍率平均回帰: 最小構成¥8M相当で粒度不足+定量報告なし。保留(棄却ではない)". This is a
feasibility/status statement, not a performance number, so there is no backtest headline to re-derive. I checked
only the capital-granularity premise: `1321.T` (N225 ETF, Yahoo daily 2009-01-05..2026-09-03, n=4,338) last close
¥66,480 → 1-unit lot ¥6.65M. A two-leg N225-vs-TOPIX ratio trade needs at least one lot on each side, each several
¥M — same order of magnitude as the claimed "¥8M-equivalent" floor. **Verdict: 再現** (the held/pending status and
its stated capital-granularity reasoning are consistent with the data; nothing here promotes it out of "pending").

## 5. Two-leg overnight-long / intraday-short (verbatim = JPR4; the content the task brief mislabeled JPR5)

**Denominator:** `day_session_daily.csv.gz`, 1990-01-05..2026-08-27, n=9,037 (open→close = intraday leg; prior
close→open = overnight leg).

| Era | overnight mean(bps)/t | intraday mean(bps)/t |
|---|---|---|
| 1990s (n=2,458) | +4.86 / 2.86 | **−7.83 / −3.53** |
| 2000s (n=2,457) | +1.30 / 0.60 | −3.66 / −1.78 |
| 2010s (n=2,449) | +4.00 / 2.12 | −0.70 / −0.44 |
| 2020-26 (n=1,673) | +5.64 / 2.24 | +0.51 / 0.25 |
| **Full 1990-2026** | +3.80 / 3.73 | **−3.22 / −3.22** |
| **2016-2026 recent** (n=2,651) | +4.73 / 2.54 | **−0.02 / −0.01** |

Combined two-leg (overnight−intraday), full sample: +7.02bps/day, t=5.08 — driven almost entirely by the
**historical** intraday shortside (1990s/2000s), not a currently exploitable pattern: shuffle control on the
intraday leg alone gives p=0.19 despite |t|=3.22 (tension between parametric NW-t and permutation check). Recent
era (2016-2026) intraday leg is genuinely ≈0 (t=−0.01), matching "近年ゼロ化" qualitatively. **My exact
recomputed headline does not match the claimed −1.84%/year, t=−0.38** — the exact sub-window is unrecoverable
without the forbidden PREREG/report file; flagged as a numeric miss, not directional. No cost translation given
(Q3): **no JPX/N225-futures fee constant exists in this repo's `config/`** (BTC/JPY-CFD only) — gross bps only.
**MDE:** intraday σ→ t=2 MDE = 2.3bps at n=9,037, 4.2bps at n=2,651 (2016-2026) — a modern-era intraday edge
smaller than ~4bps would be undetectable at today's sample size; the observed −0.02bps is far inside that.
**Verdict: 数値差異(結論維持)** — direction (intraday leg decayed to statistical zero in the modern era, so the
"US-style" two-leg construction fails to add anything the overnight-only leg doesn't already give) reproduces;
the specific reported statistic does not.

## 前提の誤り (assumption findings)

- **Capital-floor population bias** | source: JPL1/JPR1/SV2 implicitly assume a "typical diversified 30-name"
  population | data shows: the only permitted price file (`yutai_20260904`) is deliberately capped to a
  retail-affordable price band (manifest: control group filtered to ¥161-4,759/share) and its max lot cost
  (¥3.31M) is below several ordinary large-cap lot costs (¥5-8M) | bias: makes a naive recompute from this file
  **understate** the true floor by ~3-4x | inherits to: any other claim in this packet or elsewhere that cites a
  ¥/name capital number derived from the yutai universe (e.g. JPR9's yutai-based seasonality sizing).
- **No JPX fee constant in repo** | source: JPR4's/AL's cost translation implicitly assumes a known fee | data
  shows: `config/*.yaml` only defines BTC/JPY CFD costs, nothing for N225 futures | bias: any "net of cost" number
  quoted for JP-futures claims elsewhere in this repo is **not independently derivable from config** and must be
  sourced from wherever it actually came from (not this audit) | inherits to: every JP-futures claim (JPL4/JPL5/
  JPR4/PR9/ON1) that states a net-of-cost bps or %/year figure.
- **BOJ-ETF mechanism untestable with available data** | source: JPR3's "structurally ended" implies a testable
  price mechanism | data shows: only daily OHLC is available for the pre-2024 period (`bars_1min.csv.gz` starts
  2025-12-30, entirely post-cutoff) so no pre/post intraday contrast is possible; the daily-OHLC proxy tried here
  is definitionally non-discriminating (close≥low every day) | bias: none on the structural/factual conclusion
  (independently corroborated via public reporting), but the *0.05%* figure and any causal mechanism claim stay
  **未検証** | inherits to: any claim that treats JPR3's mechanism (not just its endpoint) as established.
- **Claim-ID/content mismatch in this audit's own tasking** | source: task brief's prose for "JPR5" | data shows:
  `00_packets.md` §1.10 JPR5 is NT-ratio mean reversion (held/pending); the "US two-leg, intraday≈0" text is
  verbatim JPR4 | bias: none on the underlying numbers (both were audited above under their correct IDs), but a
  reader matching this report against `00_packets.md` by ID alone would be confused without this note |
  inherits to: nothing else in this packet; noted here for traceability only.
- Calendar-anomaly "all |t|<2, every era" (JPL2) has one exception: 1990s Monday, t=−2.32, n=478 — a real,
  isolated deviation the full-sample average papers over. Direction of bias: makes the blanket claim marginally
  overstated for that one decade/anomaly cell; does not change the modern-era (post-2000) conclusion.
