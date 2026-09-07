# Binance BTCUSDT 現物 aggTrades, 2026-07-23 .. 2026-09-06(P2-08b 主系列窓)

`docs/PHASE2/P2-08b/PREREG.md` の主系列(bitFlyer 約定)と同じ暦窓の Binance 現物 aggTrades。
第1層(伝播計測)・第2層(取引可能性)の信号源。

## 出典
`https://data.binance.vision/data/spot/daily/aggTrades/BTCUSDT/BTCUSDT-aggTrades-YYYY-MM-DD.zip`
(公開・無認証、S3 静的配信、Binance 公式)。取得は本単位のために拡張した
`scripts/fetch_binance_vision.py --kind aggTrades --market spot --start-day 2026-07-23 --end-day 2026-09-06`。
各 zip は自身の `.CHECKSUM`(SHA-256)で照合してから使用(スクリプトの `fetch_one()`、全ファイル一致)。

## 取得結果(2026-09-06 実測)
- **45/46 日 成功**。欠け: **2026-09-06**(本日、当日分はまだ data.binance.vision に未公開 — HTTP 404。
  日次ファイルは通常「翌 UTC 日」に確定するため、経過中の当日は取得不能。翌日以降に再実行すれば埋まる)。
- 合計行数: **35,372,025 行**(2026-07-23〜09-05)
- ディレクトリ容量: 994MB(raw/ の zip + 日次 csv.gz、両方保持)

## 刻印の確認
2026 年のデータは取引所刻印がすでに **マイクロ秒**(16桁、例 `1784764800092008`)。
`github.com/binance/binance-public-data` README 「timestamp for SPOT Data from January 1st 2025
onwards will be in microseconds」と一致。`normalize_to_us()` は 1e14 未満(ミリ秒)を ×1000 して
統一するが、本窓はそもそも変換不要(素通し)。

## ファイル
- `raw/BTCUSDT-aggTrades-YYYY-MM-DD.zip[.CHECKSUM]` — 45 日分、Binance からのダウンロード原本
- `BTCUSDT-aggTrades-YYYY-MM-DD.csv.gz` — 日次(月次への結合はしない。P2-08b の日次 gap/overlap 分析のため
  日境界を保持)。列: `agg_id, price, qty, first_id, last_id, ts_us, is_buyer_maker`
  (`is_best_match` 列は現物のみに存在し、登録スキーマ外のため削除)
- `MD5SUMS` — 全ファイルの MD5(135 行 = raw zip 45 + .CHECKSUM 45 + csv.gz 45)

## 既知の限界
- 09-06 分は本日時点で未公開(上記)。
- 出来高が日によって最大 5 倍程度変動する(2026-07-25 の 5.1MB 圧縮 〜 2026-07-30 の 21.0MB 圧縮)。
  行数が少ない日は取得失敗ではなく、その日の実出来高を反映している(1s klines の volume 列と突合可能)。
