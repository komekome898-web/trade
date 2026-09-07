# Binance BTCUSDT USDT無期限(futures/um)aggTrades, 2026-07-23 .. 2026-09-06(P2-08b 対照系列)

`docs/PHASE2/P2-08b/PREREG.md` 対照(反事実)5「信号源の置換: Binance USDT 無期限」用。
**主指標・選択には使わない**(現物 aggTrades — `backtest_data/binance_BTCUSDT_aggTrades_20260723_20260906/`
— が主系列)。「Binance 現物固有の先行か、Binance(無期限含む)全般の現象か」を見分ける対照。

## 出典
`https://data.binance.vision/data/futures/um/daily/aggTrades/BTCUSDT/BTCUSDT-aggTrades-YYYY-MM-DD.zip`
(公開・無認証)。取得: `scripts/fetch_binance_vision.py --kind aggTrades --market um --start-day 2026-07-23 --end-day 2026-09-06`。

## 取得結果(2026-09-06 実測)
- **45/46 日 成功**。欠け: 2026-09-06(本日分、未公開。現物 aggTrades と同じ理由)。
- 合計行数: **50,201,080 行**(現物の 35,372,025 行より **約 1.42 倍**多い — 無期限のほうが
  現物より出来高が多いことを反映、実測)。
- ディレクトリ容量: 1.2GB

## 列(現物と同一スキーマ、`is_best_match` 列は futures/um には元々存在しない)
`agg_id, price, qty, first_id, last_id, ts_us, is_buyer_maker`

## 既知の限界
- 現物とは別の agg_id 体系(市場が異なる)— `agg_id` を現物側と比較しないこと。
- 09-06 分は未公開(現物と同じ)。
- **対照専用**: この系列を使って発火させた取引可能性の探索は、P2-08b の主検定・選択には数えない。
