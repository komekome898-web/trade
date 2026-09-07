# bitbank BTC/JPY 約定履歴 — 毎月1日、2017-09-01〜2026-09-01(109日分)

## 出典
- エンドポイント: `GET https://public.bitbank.cc/btc_jpy/transactions/YYYYMMDD`(Public API、キー不要)
- 一次資料: `bitbankinc/bitbank-api-docs` (`public-api_JP.md` §約定履歴) —
  「指定された日付の全約定履歴を取得。YYYYMMDDを省略した場合、最新60件が取得可能」。
  レスポンス列: `transaction_id`(取引ID)、`side`(buy/sell)、`price`、`amount`、
  `executed_at`(約定日時、UnixTimeのミリ秒)。
- 利用条件: bitbank の Public API はキー不要・利用規約上の明示的な再配布禁止条項は
  API ドキュメント上には見当たらない(2026-09-06 確認、`bitbank.cc/docs/terms/` は
  JS レンダリングのため本環境からは本文を取得できず、規約全文の確認はできていない
  = **仮定**: Public API の性質上、他取引所(Binance Vision 等)と同様に再配布前提の
  公開データと扱うが、規約全文の未確認は既知の限界として明記する)。

## 取得方法
- `scripts/fetch_bitbank_daily.py --start 2017-09 --end 2026-09 --day-of-month 1 --out <this dir>`
- 実測 2026-09-06(HTTPS プロキシ経由)。全 109 日で HTTP 200・`success: 1`。

## ファイル
- `btc_jpy_transactions_YYYYMMDD.csv.gz`(1 ファイル/日、109 ファイル)。列:
  `transaction_id, side, price, amount, ts_us`
  - `transaction_id`: bitbank の取引ID(int)
  - `side`: `buy` / `sell`
  - `price`: JPY(文字列のまま、桁落ち回避)
  - `amount`: BTC(文字列のまま)
  - `ts_us`: 取引所刻印 `executed_at`(ms)を UTC μs に正規化(`×1000`)
- `MD5SUMS`: 全 csv.gz の MD5
- `_fetch_summary.json`: 取得時の生ログ(日付・HTTPステータス・行数)

## 用途と位置づけ(P2-08b)
`docs/PHASE2/P2-08b/PREREG.md` の**診断専用・封印外**系列。円市場(bitbank)側の
「Binance → 円建て市場」伝播時間の**長期変化**(2017〜2026、9年)を年別に測る計測器。
bitFlyer CFD の執行検証には使わない(bitbank は価格発見で bitFlyer に追随する側、
床 24bps・`docs/KNOWLEDGE.md` (ac))。選択・判定には使わない。

## 既知の限界
- 月初1日のみのサンプリング(月末ロール・資金調達イベント等の偏りは未補正、**仮定**として明記)。
- 2017-09-01 は上場直後のため行数が少ない可能性がある(実測値は各日の `_fetch_summary.json` を参照)。
- 利用規約全文は本環境から未確認(上記「出典」参照)。

## 実測サマリ
- 取得日数: 109/109(全て HTTP 200)
- 合計行数: 2,149,650 行(詳細は `_fetch_summary.json` の `n_rows` を参照)
