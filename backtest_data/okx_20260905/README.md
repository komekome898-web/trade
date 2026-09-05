# OKX open interest / long-short ratio snapshot — 2026-09-05 13:46 UTC (fetched on the research VM)

Source: scripts/fetch_okx.py (OKX public API, BTC-USDT-SWAP / BTC-USD-SWAP). Taken because the owner PC's
fetch_all.bat did not include fetch_okx.py, so nothing had been collected since backtest_data/okx_*_20260823.csv.
- okx_btc_oi_1h.csv / okx_btc_lsratio_1h.csv: 720 rows, 2026-08-06 14:00 .. 2026-09-05 13:00 UTC (30-day API window;
  covers the 08-23..09-05 gap for the hourly series).
- okx_btc_oi_5m.csv / okx_btc_lsratio_5m.csv: 576 rows, 2026-09-03 13:50 .. 2026-09-05 13:45 UTC (2-day API window;
  the 5-minute series between 2026-08-23 and 2026-09-03 is LOST — not recoverable from the API).
fetch_okx.py was added to deploy/fetch_all.bat on 2026-09-05 so the owner PC collects it from now on.
