# データ品質点検 台帳 (2026-09-05)

入力: `paper_logs/QUALITY.json`(オーナーPC 2026-09-05 14:03 UTC 生成、20データセット)+ `paper_logs/INTAKE_latest.json`。
件数 > 0 の全フラグを判定。根拠はローカル(VM)の `paper_logs/`・`backtest_data/` 実ファイルを開いて確認、または `scripts/data_quality.py` を直接呼んで再現。データは一切変更していない。

判断: **仕様どおり**(設計上の挙動)/ **既知欠陥**(schemaのknown_defectsに記載済み・今回追記)/ **収集側の修正**(ツール/schemaのバグを本コミットで修正)/ **未解決**(追加調査が必要)。

## 台帳

| dataset | flag | count | 判断 | 根拠(要約) | 対応 |
|---|---|---|---|---|---|
| bitflyer_tape | duplicate_keys | 30351 | 仕様どおり | executions の複合キー(ts,price,size,side)でも同一マイクロ秒に複数約定が印字される仕様。schema記載済み | 対応不要 |
| bitflyer_tape | gaps | 243465 | 仕様どおり | paper_logs/tape 再現で内訳: executions が大半(取引閑散=自然な間隔)、ticker/board_top5 は既存known_defectsのdedup/再接続直後の記載どおり | 対応不要 |
| bitflyer_tape | missing_columns | 504 | 収集側の修正 | board_top5の`bid_px_1..5`等の範囲省略記法をチェッカーが展開せず、実ヘッダーの20列全てを誤検知(504=21ファイル×24)。実ヘッダーは正しい | 修正済み: `scripts/data_quality.py`に`_expand_range_columns`追加。VM再実行でbitflyer_tape分は0に |
| board_round_series_5s | crossed_book | 1005 | 既知欠陥 | 最大外れ値(spread_bps=-20000, row9025等)はextreme_returnと同一行に集中し、既存known_defects「WS再接続直後は書籍状態が一時的に誤る」と一致 | schema記載済み(既存) |
| board_round_series_5s | extreme_return | 102 | 既知欠陥 | 同上。価格が半値→倍返しするパターンが3箇所、再接続直後の book 再構成アーチファクトと一致 | schema記載済み(既存) |
| board_round_series_5s | gaps | 135 | 既知欠陥 | 最大ギャップ(10.3h, 2026-08-27夜〜08-28朝)は venues・oi_snapshots の最大ギャップと同時刻に終了、かつ data/ws の WS セッション一覧にも同じ穴。オーナーPC本体のダウン/スリープと推定 | schema追記済み(3データセット) |
| candles_fx_btc_jpy | gaps | 163 | 仕様どおり | 例示は夜間・週末の低頻度期間(約定なし=行なし)。既存known_defects記載どおり | 対応不要 |
| candles_fx_btc_jpy | maintenance_window | 610 | 仕様どおり | 19:00-19:10 UTCの平坦OHLC carried-forward行。チェッカー自身がbitFlyer保守時間として検出する設計 | 対応不要 |
| candles_fx_btc_jpy | zero_volume | 56649 | 未解決 | 価格が実際に動いているのにvolume=0の行が多数。`scripts/fetch_history.py`のresampleロジックを検証(pandas再現テスト)した結果、単発実行ではopen非NaN行がvolume=0になるのは数学的に不可能と確認。VM上の`data/candles_*.csv`と`data/executions_*.csv`が非同時点のコピーである可能性が濃厚だが未確認(VMはbotを稼働させていない) | schema追記(検証手順を記録)。オーナーPCで新鮮な組を再生成し再検証が必要 |
| fx_event_ticks | duplicate_keys | 23 | 仕様どおり | CPIとFOMCが同日開催の実例(2008-09-16など7日)。`date`列単独をキーにした結果の誤判定 | 修正済み: schemaにcalendar.csvの`unique_key: [date,type]`追加 |
| fx_event_ticks | gaps | 367871 | 仕様どおり | イベントtickは発表直前のみ密、それ以外は疎という設計上の性質(median_gap 0.157〜5.5秒、単発の疎ギャップ) | 対応不要 |
| jpx_etf_daily | extreme_return | 98 | 既知欠陥 | 一部は既存known_defects「ISOLATED BAD-PRINT DAYS」記載(1557/1306/1655/2558)。1311/1321/1343/1547のrow~3182は2024-08-05/06のNikkei暴落(実相場、複数ETFで整合的に確認) | schema追記済み(暴落の件) |
| jpx_etf_daily | gaps | 14 | 既知欠陥 | 全14件が2019-05-07、令和改元10連休(Golden Week)。n225fの既存known_defectsと同種の実休場 | 対応不要 |
| jpx_etf_daily | split_candidate | 5 | 既知欠陥 | 既存known_defects「1306.T 2015-01-05の実10:1分割」「1655.Tの分割」を検出する設計どおりの発火 | 対応不要 |
| jpx_etf_daily | zero_volume | 351 | 仕様どおり | 大半は祝日の平坦OHLC+ゼロ出来高(2017-08-11山の日等、5銘柄で日付・値が一致=祝日判定)。Yahoo側の仕様 | schema追記済み(祝日パターン) |
| n225f_225labo | duplicate_keys | 171 | 収集側の修正 | bars_1min.csv.gzに`unique_key`未宣言のため、チェッカーが`date`列単独をキー化(1トレーディング日=約1200行が全て「重複」、171=実トレーディング日数)。(date,time)複合では重複0件を確認済み | 修正済み: schemaに`quality.unique_key: [date,time]`追加 |
| n225f_225labo | extreme_return | 16 | 仕様どおり | Golden Week前後・実相場変動の範囲内(既存known_defects) | 対応不要 |
| n225f_225labo | gaps | 5 | 既知欠陥 | 既存known_defects「2019-04-26..05-07 Golden Week」と一致 | 対応不要 |
| n225f_225labo | zero_volume | 14893 | 仕様どおり | 1分足の薄商い分(夜間セッション中心)。1分粒度では無出来高分が生じるのは構造上当然 | 対応不要 |
| oi_snapshots | gaps | 6 | 既知欠陥(2件×3コピー) | 実ギャップは2件(data/・paper_logs/・backtest_dataの3コピーで6)。最大(10.4h, 08-28 04:22終了)はboard_round/venuesと同時、オーナーPCダウンと推定。2件目(2.9h, 08-31)は対応するventues/board_roundの穴が無く未説明 | schema追記済み(1件)。2件目は未解決 |
| qa_synthetic | duplicate_keys | 60679 | 仕様どおり | 全ファイルが既存known_defects「SYNTHETIC DATA WARNING」明記の人工既知解フィクスチャで実データではない | 対応不要 |
| qa_synthetic | extreme_return | 70 | 仕様どおり | 同上 | 対応不要 |
| qa_synthetic | gaps | 55593 | 仕様どおり | 同上 | 対応不要 |
| qa_synthetic | maintenance_window | 4200 | 仕様どおり | 同上 | 対応不要 |
| qa_synthetic | split_candidate | 3 | 仕様どおり | 同上 | 対応不要 |
| qa_synthetic | zero_volume | 4200 | 仕様どおり | 同上 | 対応不要 |
| reit_onr | extreme_return | 8 | 仕様どおり | 既存known_defects(open==0 erratum等)の範囲内。件数小さく個別全件検証はしていない | 対応不要 |
| reit_onr | gaps | 2 | 既知欠陥 | n225f/jpx_etf_dailyと同じ2019-05-07 Golden Week | 対応不要 |
| reit_onr | missing_columns | 6 | 収集側の修正 | schemaのfile_groupsキーがディレクトリ階層にプレースホルダを含み、旧ロジック(basenameのみで照合)ではbacktest_data版が誤って`data/onr/`版(列が少ない)のcolumnsに一致し、実列を「undocumented」と誤検知 | 修正済み: `_file_group_prefix_match`をrel_path込みのfnmatchに変更。VM再実行で6→0 |
| reit_onr | zero_volume | 124 | 仕様どおり | 1321.T/1343.Tの上場初期(2008-2009年)の薄商い日。REIT系ETFの立ち上げ初期に典型的なパターン | 対応不要 |
| schema_undefined | schema_undefined_count(top) | 134 | 収集側の修正(131件)/未解決(3件) | 17新規+3修正schemaのpush後、path_globをローカルで照合した結果131/134は正しいdatasetへ解決(VMのフルスキャンでも`schema_undefined_count=0`)。残り3件はさらにpath_glob不足だった: `backtest_data/auto_bitflyer_executions_*/candles_FX_BTC_JPY.csv`・`candles_XRP_JPY.csv`(candles_fx_btc_jpyのpath_glob対象外)、`data/api_health.csv`(schema自体が無い) | 修正済み: candles_fx_btc_jpy.jsonにpath_glob追加、新規`schema/api_health.json`作成(`src/bot/exchange/resilience.py`のApiHealthRecorderを読んで作成。VM上に実ファイルが無くコード読解のみ、オーナーPCでの再確認が望ましい=未解決の余地あり) |
| schema_undefined | gaps(バケツ集計) | 109400 | 収集側の修正(結果的に解消) | schema未定義バケツの構造チェック(structural-only)の合算値。schema追加後は各データセット固有のチェックへ正しく分解される(VM再実行でexternal_crypto_klines/fx_macro_fundamentals/daily_crypto_usd_multisource/regime_composite等へ分解確認済み) | 対応不要(schema追加で自然消滅) |
| venues | duplicate_keys | 399 | 仕様どおり | quotes_YYYYMMDD.csv.gzの複合unique_key(ts_utc,venue,pair)前提でも、GMOの複数シンボル一括返却などで残る想定内の重複(既存known_defects記載の範囲) | 対応不要 |
| venues | extreme_return | 15 | 未解決 | 個別行までは検証していない。件数は小さく既存known_defectsの範囲内と推定されるが未確認 | 必要なら個別に確認 |
| venues | gaps | 211876 | 仕様どおり | ローカル再現(paper_logs/venues 50ファイル)で99%超がtrades_*.csv.gz(個々の約定の到着間隔=自然な閑散)。最大ギャップ(2.17h、GMOのBTC/BTC_JPYが同時、2026-08-29 02:10 UTC)は既存known_defects「ベニューごとの独立バックオフ」どおり。quotes側の残りは19:00-19:10 UTC保守で説明可 | schema追記済み(outage window) |

## 収集側の修正 一覧(本コミットで適用)

1. `scripts/data_quality.py`: `schema_columns_for`に`_expand_range_columns`を追加し、schemaの`prefix_N..M`省略記法(例: `bid_px_1..5`)を実列名へ展開してから比較。bitflyer_tapeのmissing_columns誤検知(504件)を解消。
2. `scripts/data_quality.py`: `_file_group_prefix_match`をrel_path込みのfnmatchベースに変更(旧: basenameのみのプレフィックス比較)。reit_onrのようにfile_groupsキーがディレクトリ階層にプレースホルダを持つschemaで、同名ファイルの列セットが別ディレクトリの別file_groupに誤って一致する問題を解消(missing_columns 6→0)。
3. `schema/n225f_225labo.json`: bars_1min.csv.gzに`quality.unique_key: [date, time]`を追加。`date`列単独の重複判定(171件の偽陽性)を解消。
4. `schema/fx_event_ticks.json`: calendar.csvに`quality.unique_key: [date, type]`を追加。CPI/FOMC同日開催による重複判定(23件のうち大半)を解消。
5. `schema/candles_fx_btc_jpy.json`: path_globに`backtest_data/auto_bitflyer_executions_*/candles_FX_BTC_JPY.csv`・`candles_XRP_JPY.csv`を追加(schema_undefined 134件のうち2件を解消)。
6. `schema/api_health.json`(新規): `data/api_health.csv`のスキーマ未定義(schema_undefined 134件のうち1件)を、`src/bot/exchange/resilience.py`のApiHealthRecorderを読んで追加。

## known_defects 追記(既知欠陥として記載)

`schema/board_round_series_5s.json` / `schema/venues.json` / `schema/oi_snapshots.json`: 2026-08-27夜〜08-28朝の約10.3時間の同時ギャップ(オーナーPCダウン推定)を追記。
`schema/jpx_etf_daily.json`: 2024-08-05/06 Nikkei暴落による本物のextreme_return、および日本の祝日による平坦ゼロ出来高行のパターンを追記。
`schema/bitflyer_tape.json`: missing_columnsの原因説明とgapsの内訳(executions優位)を追記。
`schema/candles_fx_btc_jpy.json`: zero_volumeの再現不能性の検証結果(未解決の根拠)を追記。

## 未解決として残るもの

- candles_fx_btc_jpy zero_volume(56649): アルゴリズム上再現不能と確認済みだが、原因(VM上の非同時点コピー vs 実際の履歴書き換え)はオーナーPCでの再実行でのみ確定できる。
- oi_snapshots gapsの2件目(2.9h, 2026-08-31 12:03 UTC終了): venues/board_roundに対応するギャップが見当たらず未説明。
- venues extreme_return(15件)・reit_onr extreme_return(一部): 件数が小さく既存known_defectsの範囲内と推定されるが、1件ずつは未検証。
- schema/api_health.json: VM上に実ファイルが無く、コード読解のみで作成。オーナーPCの実データで列内容の確認が望ましい。

## 検証

`PYTHONPATH=src python -m pytest -q tests/test_data_quality.py` および全体テスト(976件)を実行し、全て通過(スキーマ・チェッカー変更後も既存の期待値に影響なし)。`scripts/data_quality.py`をVMのローカルコピーに対して再実行し、上記の修正が実際に該当フラグを解消することを確認(例: missing_columns 347→5、schema_undefined_count 0 を維持)。データファイルは変更していない。
