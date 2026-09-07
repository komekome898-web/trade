# Binance BTCUSDT 現物 aggTrades — Tardis サンプル日と同じ85日分(2019-09-01〜2026-09-01)

`data/tardis/bitflyer_FX_BTC_JPY_trades/`(gitignore域、Tardis 無料サンプル)と**同じ暦日**の Binance 現物
aggTrades。こちらは公開データなので通常どおり `backtest_data/` にコミット対象として保存する。
`docs/PHASE2/P2-08b/PREREG.md` の診断 (iii)(伝播時間分布の長期変化)用、**診断専用・封印外**。

## 出典
`https://data.binance.vision/data/spot/daily/aggTrades/BTCUSDT/BTCUSDT-aggTrades-YYYY-MM-DD.zip`
(公開・無認証)。列・単位は `schema/binance_aggtrades_p2_08b.json` と同一
(`agg_id, price, qty, first_id, last_id, ts_us, is_buyer_maker`)。

## 取得結果(2026-09-07 実測)
- **85/85 日 成功**(2019-09-01〜2026-09-01 の毎月1日、`data/tardis/` と同じ日付リスト)
- 合計行数: **116,176,205 行**
- ディレクトリ容量: 3.1GB(raw/ の zip 85 本 + 日次 csv.gz 85 本)

## 出来高の傾向(実測)
2022年(LUNA崩壊 5月・FTX破綻 11月前後)と 2023年前半(SVB/USDC デペッグ 3月)の月初日は
特に出来高が多く、圧縮 zip で最大 106MB(2023-03-01)、csv.gz で最大 100MB超に達した。
2024年以降は概ね月 10〜30MB(zip)程度に落ち着いている。

## 取得方法の注記(実装メモ)
当初 `scripts/fetch_binance_vision.py --kind aggTrades`(純 Python の csv/gzip 逐次処理)で
取得を開始したが、2022年の大出来高月(特に 2022-11 FTX 破綻月、2023-02〜03 の SVB 危機月)で
1 ファイルの処理に数分を要したため、`pandas`(C 実装の CSV パーサ)を使う一時スクリプトに
切り替えて残りの日を取得した(`scripts/fetch_binance_vision.py` 本体は変更していない — 既存の
klines パスに対する非破壊の追加のみ)。出力スキーマ・列名は完全に同一。

## 既知の限界
- 月初1日のみのサンプリング(Tardis 側の制約に合わせたもの)。連続性は無い。
- **診断専用**: P2-08b の主指標・選択には使わない(長期の年別 R(τ) の記述統計のみに使用)。
