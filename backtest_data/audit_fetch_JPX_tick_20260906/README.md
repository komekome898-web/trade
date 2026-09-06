# Audit fetch: JPX 呼値の単位 (tick size) — 2026-09-06

Raw HTML snapshots fetched for the primary-source verification behind
`config/constants.yaml: jpx_cash_equity.etf_tick_size_yen_by_price_band`
(and the check on whether to add `closing_auction_time_before_2024_11_05`).

## Files

- `jpx_07.html`
  - URL: https://www.jpx.co.jp/equities/trading/domestic/07.html
  - Fetched: 2026-09-06T00:35:02Z (UTC), via `curl -sS` through the configured
    egress proxy (WebFetch was blocked with `EGRESS_BLOCKED` for
    www.jpx.co.jp; curl through `HTTPS_PROXY=http://127.0.0.1:32843` with
    `--cacert /root/.ccr/ca-bundle.crt` returned HTTP 200).
  - Page's own "更新" (updated) date shown in the HTML: 2026/08/06.
  - Contains the full 呼値の単位 table (値段の水準 x
    TOPIX500構成銘柄 / 売買単位が１口のETF等(ETF、ETN及びレバレッジ商品) /
    その他の銘柄) used to build the new constants entry.

- `jpx_closing_auction_press_release.html`
  - URL: https://www.jpx.co.jp/corporate/news/news-releases/1030/20241105-01.html
  - Fetched: 2026-09-06T00:35:xx UTC (same session, same method as above).
  - Same press release already cited by
    `jpx_cash_equity.closing_auction_time_since_2024_11_05` in
    config/constants.yaml. Checked for an explicit statement of the
    *previous* (pre-2024-11-05) closing-auction time. The release states
    only "現物市場の取引時間の30分延伸" (30-minute extension) and the
    introduction of the closing auction; it does **not** state "15:00"
    or any other explicit previous close time anywhere in the page text.
    Per task instructions, `closing_auction_time_before_2024_11_05` was
    therefore **not** added to constants.yaml (no primary-document
    statement of the prior time in this same press release).

## Verification method

```
export HTTPS_PROXY=http://127.0.0.1:32843
curl -sS --cacert /root/.ccr/ca-bundle.crt -o <file> "<url>"
```

Both fetches returned HTTP 200. See `MD5SUMS` for content hashes of the
files as saved.
