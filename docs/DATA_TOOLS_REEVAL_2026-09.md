# 外部ツール再評価 — データ取得・保持基盤としてのみ(2026-09-05)

`DATA_GOVERNANCE_PLAN.md` §2 item 8 に基づく再評価。**戦略性能ではなく**、
「今失っているデータ(bitFlyer 31日約定、OKX OI/L-S比の保持期限、板スナップショット)を
取得・保持できるか」だけを一次資料で判定する。一次資料以外(ブログ等の意見)は根拠に採らない。

## 1. 位置分布チェッカー(Hyperliquid型)

| 項目 | 内容 |
|---|---|
| 前回の棄却理由 | 戦略側では未評価(KNOWLEDGE.md は自前の推定建値台帳 `scripts/research_position_ladder.py` を「Hyperliquid型チェッカーのCEX推定版」と記すのみ。棄却理由は記録なし) |
| データ基盤としての価値 | Hyperliquid 公式 S3 (`hyperliquid-archive`) に **板スナップショット(`market_data/.../l2Book`、1時間・銘柄別)** と **建玉等の資産コンテキスト(`asset_ctxs`、日次csv)** が**約月1回**アップロードされ、期限の記載なし(=無期限アーカイブ)。ただし公式に「更新の遅延・欠落は保証しない」と明記、取得はAWS転送費用が要求者負担。API側 `openInterest` は現在値のみ(履歴なし)、`candleSnapshot`・`clearinghouseState` にも独自の長期保持保証はない。**Hyperliquid 自身の板・建玉であり、当プロジェクトが実際に取引する bitFlyer/OKX とは別の取引所**。bitFlyer 31日問題・OKX OI/L-S 保持問題・自前板消失のいずれも直接には解決しない(代替ではなく別ベニューの参考系列止まり) |
| 判定 | **保留**(採用も棄却もしない。将来クロスベニュー建玉シグナルを研究する場合のみ、research-protocol の事前登録付きで再検討) |
| 根拠URL | https://hyperliquid.gitbook.io/hyperliquid-docs/historical-data (板・asset_ctxsのS3仕様、更新保証なしの明記)/ https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/rate-limits-and-user-limits (レート制限、`openInterest`系エンドポイントの重み) |

## 2. Freqtrade のデータ層

| 項目 | 内容 |
|---|---|
| 前回の棄却理由(2026-09-01) | 公式対応取引所に bitFlyer・GMO・JPX がいずれも無い。hyperopt/FreqAI は研究規律が排除する手法で、自前資産(コストモデル・嵐法則・ON1)は移植不能 |
| データ基盤としての価値 | `freqtrade download-data` は OHLCV・約定(trades)・funding_rate/mark/index/premiumIndex を json/jsongz/**feather/parquet** で保存。**保持期限は無し**(ローカルディスクに無期限、既存データは自動で差分更新のみ・削除しない)。ただし **建玉(open interest)の時系列取得コマンドは存在せず**、板(L2)履歴の取得機能も無い。取引所対応は前回確認のとおり bitFlyer・GMO・JPX いずれも非対応(2026-09-04 に生ドキュメントで再確認済み、`docs/AUDIT_2026-09/AQ_AR_due_diligence_infra.md`)。従って bitFlyer 31日問題は原理的に対象外、OKX を使っても OI/L-S 保持問題は解決しない(そのコマンド自体が無い)、板スナップショットも非対応。Binance 等の候補足データを取るだけなら当プロジェクトの `fetch_*`/`backtest_data/` 恒久スナップショット + `schema/*.json`(列意味・既知欠陥の宣言)の方が本プロジェクトの品質ゲートに適合し、二重管理コストが増えるだけ |
| 判定 | **棄却**(データ基盤としても不採用。理由が戦略性能から実装範囲外(OI・板・bitFlyer非対応)に変わっただけで結論は変わらず) |
| 根拠URL | https://www.freqtrade.io/en/stable/data-download/ (`--data-format-ohlcv/trades`、`--candle-types`、更新は差分のみで削除しない仕様)/ https://raw.githubusercontent.com/freqtrade/freqtrade/develop/docs/index.md (対応取引所一覧、bitFlyer/GMO/JPX 不在) |

## 3. 暗号資産 MCP・データツール群(オーナーのツイート調査)

前回(2026-09-04)全不採用、理由は個別。データ基盤の観点で再確認。AQ監査(`AQ_AR_due_diligence_infra.md`)は
「暗号通貨MCP 10選」自体の一次資料URLが特定不能と結論済みのため、個別ツールの一次資料相当(公式ドキュメントのナビゲーション・料金体系の公開情報)で再確認した。

| ツール | 前回の棄却理由 | データ基盤としての価値 | 判定 |
|---|---|---|---|
| CoinGecko / CoinMarketCap / CryptoPanic / LunarCrush | 既存の無料一次資料と重複、社会的センチメントは方向性として閉鎖済み | 汎用マルチ取引所の価格・出来高・ニュース集約であり、**bitFlyer個別約定・OKXのOI/L-S固有の保持期限・板情報は対象外**(いずれも上場銘柄の集計指標のみ)。データ取得基盤としても3つの消失問題を一切埋めない | **棄却**(変更なし) |
| altFINS(150指標) | 履歴最適化の温床 | 加工済み指標配信であり生データ保持ではない。指標のバックフィル年数は非公開ページの会員限定情報で一次資料から確認不能 | **棄却**(変更なし) |
| GOAT SDK / DeFi Portfolio / TradingView非公式ラッパー | 鍵・資格情報を第三者コードに渡す構造で秘密不変条件(CLAUDE.md §1)に抵触 | データ取得目的で使っても、読み取り専用キーであっても第三者コードへの資格情報引き渡しという構造自体は変わらず、TradingView非公式は利用規約違反のスクレイピング構造 | **棄却**(データ基盤としても不変条件抵触のため不可、変更なし) |
| Dune(オンチェーン取引所フロー) | 将来G6規模ゲート用に再検討可、と留保付きで実質棚上げ | オンチェーンのウォレット・取引所フローが対象で、**bitFlyer/OKXの中央集権型の約定・OI・板とは別種のデータ**。3つの消失問題(bitFlyer 31日・OKX OI/L-S・板)はいずれも対象外。無料枠の詳細(レート制限・保持期間)は公式ドキュメントがクライアント側描画のため本再評価では確認不能だった(ナビゲーション構造のみ取得) | **保留**(変更なし。G6規模ゲート用途のみ将来再検討、データ基盤としての優先度は上げない) |

根拠URL: https://docs.dune.com/api-reference/overview/introduction(取得できたのはページ構成のみ、本文はクライアント側描画で不読)/
KNOWLEDGE.md §7(個別ツールの前回判定の原文)

## 4. 結論と推奨

- 3カテゴリとも、**当プロジェクトが今失っている3種のデータ(bitFlyer 31日約定・OKX OI/L-S保持期限・板スナップショット)を
  埋めるものは一つもない**。理由は個別に異なる: Freqtradeは対象取引所非対応+OI/板コマンド自体が無い、
  MCP/データツール群は対象データの種類が違う(集計指標・オンチェーン)、Hyperliquid型は取引所自体が違う。
- 唯一新知見は Hyperliquid の S3 板・建玉アーカイブが無期限保持である点だが、更新保証なし・転送費用負担・別ベニューという
  制約から、今回は**保留**に留め、採用のための実装コストは払わない。
- 現行の `scripts/intake_ledger.py`・`scripts/retention_snapshot.py`・`schema/*.json`・`config/constants.yaml`
  (`data_retention`)による自前の先回りスナップショット体制が、3つの消失問題への対応として引き続き最適。
  外部ツール導入によるデータ基盤の置き換え・追加は**不要**と判定する。
- 次アクションなし(全て前回同様の棄却・保留を維持)。将来 Dune や Hyperliquid を使う場合は、
  データ基盤の判断ではなく research-protocol の事前登録を要する戦略仮説として扱う。
