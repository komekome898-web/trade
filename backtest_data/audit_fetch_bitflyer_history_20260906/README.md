# bitFlyer FX_BTC_JPY multi-year history: source survey (2026-09-06)

Goal: find a source of multi-year 1-minute OHLCV for the CFD product
`FX_BTC_JPY` (our public-trade-history snapshot only covers 31 days,
2026-07-23..2026-08-23). Network: agent proxy, CA bundle
`/root/.ccr/ca-bundle.crt`, `REQUESTS_CA_BUNDLE`/`CURL_CA_BUNDLE` already set
in the environment.

## 1. bitFlyer lightchart (chart backend) — WORKS, goes back years

`https://lightchart.bitflyer.com/api/ohlc?symbol=FX_BTC_JPY&period=m` —
not Akamai-blocked, no auth. All requests below succeeded (HTTP 200 after
following a 301 redirect that normalizes the URL).

- `period=h` and `period=d` → **HTTP 501** (not implemented). Only
  `period=m` works. See `lightchart/headers_period_h.txt` / `_d.txt`.
- `period=m` with no `before` → returns the 2 most recent 1m bars only
  (`lightchart/resp_1.json`).
- `period=m&before=<epoch_ms>` → server floors `before` to a 12-hour UTC
  grid boundary (00:00/12:00) and 301-redirects to
  `...&before=<aligned>&type=full&grouping=1`; the canonical page returns
  up to 720 rows (12h of 1-minute bars), newest first. See
  `lightchart/headers_redirect_test.txt`, `lightchart/resp_redirect_test.json`.
- Paginating `before` = previous page's oldest timestamp walks arbitrarily
  far back. Probed `before` at 2024-01-01, 2022-01-01, 2020-01-01,
  2018-01-01, 2017-07-01, 2016-01-01 → all returned 720 (or near-720) rows
  of real data (`lightchart/resp_probe_*.json`).
- Binary-searched the start of history: `before`=2015-11-01 and earlier →
  0 rows; `before`=2015-12-01 → 719 rows ending 2015-11-30 23:41 UTC.
  **History starts ~2015-11-30** (not pinned to the exact minute).
- Row shape (10 fields) and OI-like extra columns are inferred/documented
  in `schema/bitflyer_lightchart_1m.json`. Fields 7-10 are null on bars
  before ~2017-07 (only OHLCV recorded that far back).
- Zero-execution minutes come back with **null OHLC** (not forward-filled),
  unlike our REST snapshot's known ffill defect.

Given this worked (not blocked), the actual pagination was run from this
container — see `backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/`
for the raw pages, combined CSV, gap list, and comparison against our
existing snapshots. `scripts/fetch_bitflyer_lightchart.py` is the resumable
fetcher (also runnable standalone by the owner, e.g. on a Windows PC,
with `--dry-run` to preview first).

## 2. ccxt — bitFlyer OHLCV not supported

Installed ccxt 4.5.77 into an isolated venv (not the project's Python,
to avoid the `cryptography` package conflict seen when installing into the
system env directly).

```
ex = ccxt.bitflyer()
ex.has['fetchOHLCV']  -> None   # not implemented
ex.has['fetchTrades']  -> True  # ccxt can only pull raw executions, not candles
```

ccxt's bitflyer adapter has no OHLCV endpoint at all (bitFlyer's official
REST API has no candle endpoint — only ticker/board/executions), so ccxt
cannot serve FX_BTC_JPY candles regardless of network reachability.

## 3. CryptoCompare histominute — blocked (needs paid API key), and it's spot anyway

```
GET https://min-api.cryptocompare.com/data/v2/histominute?fsym=BTC&tsym=JPY&e=bitflyer&limit=2000
-> HTTP 401 {"message":"API key required, please refer to the documentation at https://developers.coindesk.com/"}
```
See `cryptocompare/resp_histominute_bitflyer.json` and
`cryptocompare/headers_1.txt`. CryptoCompare (now under CoinDesk) no longer
serves this endpoint without a registered key — did not sign up for one
(out of scope / would need an owner decision). Even if it worked, `e=bitflyer`
there is bitFlyer's **spot** BTC_JPY order book, not the FX_BTC_JPY CFD —
not usable as a substitute in any case.

## 4. Public datasets (GitHub/Kaggle) — no FX_BTC_JPY 1m dataset found

Web search only, no bulk download (per instructions: sample only, and
none looked worth even a sample):

- `mczielinski/bitcoin-historical-data` (Kaggle) — well-known 1m BTC
  dataset, but sourced from Bitstamp/Coinbase-family exchanges, not
  bitFlyer.
- `bhadramohit/bitcoin-datasetintervals-of-1-minute` (Kaggle) — exchange
  unclear from listing, very unlikely to be bitFlyer FX.
- `pingu342/nodejs-bitflyer` (GitHub) — a *tool* that builds OHLC from
  bitFlyer executions itself, not a pre-built historical dataset (same
  approach as our own `scripts/fetch_history.py build_candles()`).
- Tardis.dev — commercial historical market data vendor, lists bitFlyer
  (incl. derivatives) back to **2019-08-30**, but paid/licensed; not
  fetched (no key, out of scope for a survey).

No candidate dataset was downloaded, sampled, or verified — search-result
listings only.

## Files here

- `lightchart/` — every raw probe response + headers for section 1
  (small exploratory requests; the full pagination run lives under
  `backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/`).
- `cryptocompare/` — the 401 response + headers for section 3.
- `MD5SUMS` — checksums of every file in this directory.
