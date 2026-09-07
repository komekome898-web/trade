# Binance BTCUSDT 現物 1秒足klines, 2026-07-23 .. 2026-09-06(P2-08b)

## 出典
`https://data.binance.vision/data/spot/daily/klines/BTCUSDT/1s/BTCUSDT-1s-YYYY-MM-DD.zip`
(公開・無認証)。`scripts/fetch_binance_vision.py --interval 1s --start-day 2026-07-23 --end-day 2026-09-06`
(日単位の厳密窓モード。月次アーカイブは使わず、指定した日だけを取得 — 月境界にまたがる部分月の
無駄な取得を避けるため、本単位でスクリプトに追加した機能)。

## 取得結果(2026-09-06 実測)
- **45/46 日成功**。欠け: **2026-09-06**(本日分、未公開。理由は aggTrades README と同じ)。
- **3,888,000 行**(45 日 × 86,400 秒)、**1 秒刻みの欠けはゼロ**(実測: 全行の連続差分が厳密に 1.000 秒、
  最大ギャップ 0 秒)。取引の無い秒も `n_trades=0` の行として存在する(価格継承ではなく「観測なし」として扱う —
  PREREG.md 既知欠陥(4)と整合)。
- 1ファイルに結合(このリポジトリの `binance_BTCUSDT_1m_*` 系と同じ慣例)。容量 167MB。

## 列
`open_time(ISO-8601 UTC), open, high, low, close, volume(BTC), quote_volume(USDT), n_trades, taker_buy_base(BTC)`
(`close_time, taker_buy_quote, ignore` は既存スクリプトの慣例どおり削除)。

## 既知の限界
- `scripts/fetch_binance_vision.py` の `consolidate()` が出す `non-60s-gaps` 統計は 1 分足専用の
  ハードコード(60000ms 刻み前提)で、1 秒足に適用すると無意味な値(ほぼ全行が「ギャップ」)になる
  — 上記の「1 秒刻みの欠けはゼロ」は本 README 作成時に別途 Python で実測した値で、こちらが正しい。
  スクリプト自体の当該チェックは変更していない(既存挙動维持)。
