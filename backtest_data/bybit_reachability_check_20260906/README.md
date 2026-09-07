# Bybit 公開約定履歴 — 到達確認・2日分サンプル・スキーマ記録(全窓は取得しない)

`docs/PHASE2/P2-08b/PREREG.md` 対照(反事実)5「信号源の置換: Binance USDT 無期限、Bybit(海外先行一般かBinance固有か)」の
到達確認用。**本ディレクトリは 2 日分のスキーマ確認のみ**であり、P2-08b の対象窓(2026-07-23〜09-06)全体は取得していない。

## 到達確認(2026-09-06 実測)

| 候補パス | 内容 | 到達 | 頻度 |
|---|---|---|---|
| `https://public.bybit.com/spot/BTCUSDT/` | **現物**(BTCUSDT spot)、`BTCUSDT-YYYY-MM.csv.gz` | HTTP 200 | **月次**(日次ではない) |
| `https://public.bybit.com/trading/BTCUSDT/` | USDT 無期限(perpetual、旧来の trading エンドポイント)、`BTCUSDT{YYYY-MM-DD}.csv.gz` | HTTP 200 | 日次 |

タスクの指定どおり「現物 BTCUSDT」を優先し `/spot/` を使用。`/spot/` は **月次アーカイブのみ**(日次ファイルは無い)ため、
2026-08 の月次ファイルをダウンロードし、その中から 2026-08-01・2026-08-02 の 2 日分を抜き出して本ディレクトリに保存した。

## スキーマ(`/spot/BTCUSDT/BTCUSDT-2026-08.csv.gz` 実測)

列: `id, timestamp, price, volume, side`(ヘッダ有り)
- `id`: 連番(bybit 内部 ID)
- `timestamp`: 取引所刻印、**ミリ秒**(実測: `1785542401142` → 2026-08-01T00:00:01.142Z)
- `price`: USDT
- `volume`: BTC
- `side`: `buy` / `sell`

本ディレクトリのファイルは列名を `id, timestamp_ms, price, volume, side` に変更(単位を明示)、値は無加工。

## 参考: `/trading/` (USDT 無期限、未取得・スキーマのみ記録)

列: `timestamp, symbol, side, size, price, tickDirection, trdMatchID, grossValue, homeNotional, foreignNotional, RPI`
(`timestamp` は秒未満の小数を含む UNIX 秒、例 `1788480000.1185`)。日次ファイルで最新は 2026-09-05。
P2-08b では「海外先行一般か Binance 固有か」の対照シグナル源として使う場合の候補だが、**本単位では未取得**
(タスクの指示どおり到達確認のみ)。

## ファイル
- `bybit_spot_BTCUSDT_20260801.csv.gz`(221,151 行)
- `bybit_spot_BTCUSDT_20260802.csv.gz`(298,072 行)

## 既知の限界
- `/spot/` は月次のみのため、日次 gap 分析やこの単位の主系列とは直接突合しない(対照専用)。
- 全窓(2026-07-23〜09-06)は取得していない — 必要になった場合は 2026-07・2026-08・2026-09 の月次ファイル
  3 本(合計 ~110MB×3 圧縮)をダウンロードし、日付でスライスすれば良い。
