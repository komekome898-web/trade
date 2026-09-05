# audit_fetch_H_20260905

Mandatory-fetch attempt (PROTOCOL.md public-source rule) for JPR6 (RB1: leveraged-ETF
pre-close rebalancing flow) and JPR7 (UO1: intraday decomposition), whose packet-H row
marks individual-ETF minute bars as not snapshotted in the repo.

## Fetches (all via Yahoo Finance chart API, through the session's proxy, User-Agent: Mozilla/5.0)

| file | URL | HTTP | rows | first | last |
|---|---|---|---|---|---|
| 1570.T_5d_1m.json | https://query1.finance.yahoo.com/v8/finance/chart/1570.T?range=5d&interval=1m | 200 | 1942 | 2026-08-31 | 2026-09-04 |
| 1570.T_1mo_5m.json | https://query1.finance.yahoo.com/v8/finance/chart/1570.T?range=1mo&interval=5m | 200 | 1716 | 2026-08-05 | 2026-09-04 |
| 1557.T_1mo_5m.json | https://query1.finance.yahoo.com/v8/finance/chart/1557.T?range=1mo&interval=5m | 200 | 1717 | 2026-08-05 | 2026-09-04 |
| 1570.T_1y_1h.json | https://query1.finance.yahoo.com/v8/finance/chart/1570.T?range=1y&interval=1h | 200 | 1702 | 2025-09-05 | 2026-09-04 |

Fetch time: 2026-09-05 (this audit session). No errors -- all four requests returned HTTP 200.

## Finding

Yahoo's free chart API caps 1-minute bars at ~5 trading days and 5-minute bars at ~1 month for
these Tokyo tickers. JPL... JPR6's stated methodology (1-minute bars over 170 days) cannot be
reproduced from this or any other free source found in this session -- no historical intraday
(sub-daily) JPX data provider was found that serves 170 days of 1-minute bars for free. The 1h/1y
series for 1570.T is the coarsest usable substitute and was used only as a non-equivalent,
lower-resolution supplementary check (see H3_third.md), not as a basis for reproducing the claim.

Raw files here are unmodified Yahoo chart API responses. Never delete.
