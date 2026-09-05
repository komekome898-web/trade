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
| candles_fx_btc_jpy | zero_volume | 56649 | 収集側の修正 | 根本原因を確定: `data/candles_FX_BTC_JPY.csv`(=`backtest_data/candles_FX_BTC_JPY_31d_20260823.csv.gz`と同一)は`scripts/fetch_deep.py`で構築された区間を含み、同スクリプトは欠測分を`candles[["open","high","low","close"]].ffill()`(列ごとに独立転記)+`volume.fillna(0.0)`で埋めていた。これは単一フラットな点ではなく**前の実バーのopen/high/low/closeを列ごとにコピー**するため、前バーがフラットでなければ非フラットなOHLCがvolume=0で残る。実データで再現・確認済み: ts=2026-07-23 16:04:00Zの行(open=10624068 high=10625509 low=10623927 close=10624749 volume=0)は`data/executions_FX_BTC_JPY.csv`にその分の約定が0件である一方、直前16:03:00の実バー(open=10624068 high=10625509 low=10623927 close=10624749 volume=0.341750)とOHLCが完全一致——`fetch_history.py`側(dropna(subset=["open"])のみ、ffillなし)のロジックで同区間を再構築すると16:04の行自体が生成されないことも確認済み(数式再現テストは合成dfで実施、pandas resample().sum()は空バケットをNaNでなく0.0にする点が前回の「未解決」判断の誤り)。前回記載の「VM非同時点コピー」説は誤り(データ改変ではなく単発実行内のロジック起因、再現性あり) | 修正済み: `scripts/fetch_deep.py`(and `scripts/fetch_history.py`, 同一出力ファイルへの書き込み元として列を揃えるため)に`synthetic`列を追加(1=ffillで埋めた偽バー、0=実バー)。既存データファイルは書き換えない(過去分のzero_volume行はそのまま=既知欠陥として残る)。既存コンシューマは列名参照(`src/bot/monitoring/market_view.py:read_candles`はヘッダー由来の列名で辞書化、pandas読者は列名参照)のため追加列は無視され後方互換。テスト: `tests/test_fetch_history_candles.py`(合成executionsに欠測分を挟んで両ビルダーを比較) |
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
| oi_snapshots | gaps | 6 | 既知欠陥(2件×3コピー) | 実ギャップは2件(data/・paper_logs/・backtest_dataの3コピーで6)。最大(10.4h, 08-28 04:22終了)はboard_round/venuesと同時、オーナーPCダウンと推定。2件目(2.9h, 08-31 09:07:42Z→12:03:50Z終了)を本回で解明: venues(全ペア)・board_round_series_5s(5秒粒度、窓内2280行)・bot.jsonl(paperボット本体の判断ログ)は同じ窓で欠落なし、ws_listing.txtも窓内(11:17:22)に正常な再接続セッション開始があり穴なし→PC/回線/他コレクタは稼働中。`scripts/record_oi.py`は各API呼び出しを個別best-effortで捕捉し失敗時も空欄セルで必ず1行appendする設計(行自体を欠かすことは無い)ため、行が0件=OI用API個別の障害ではなく`record_oi.py`自体が実行されなかったことを意味する。同スクリプトは`deploy/fetch_all.bat`内でfetch_history.py/fetch_external.py/fetch_okx.pyの後に呼ばれる1行(15分毎のタスクスケジューラ`bitflyer-fetch`)なので、当該実行が前段のいずれかで2.9h滞留した(あるいはタスクスケジューラの「実行中は新規開始しない」既定によりその間の起動がスキップされた)ことが有力な説明——他プロセス(bot/venues/board_round/WS)は個別プロセスのため無関係で影響を受けない。オーナーPCの`logs\fetch.out.log`やタスクスケジューラ実行履歴が本リポジトリに無いため、前段のどのスクリプトが滞留したかの確定はできていないが、「PCダウン」「API側の一般的な不通」の2説は上記根拠で否定できる | schema追記済み(2件とも)。原因は`fetch_all.bat`バッチ(record_oi.py起動経路)の単発滞留に切り込み済みだが、滞留元スクリプトの確定は残課題(オーナーPCのfetch.out.log確認が必要) |
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
| venues | extreme_return | 15 | 既知欠陥 | 15件全行を列挙・個別検証(下記「venues extreme_return 15件の内訳」参照): 実体は5件の(ts,gmo,FCR)行が3コピー(data/・paper_logs/・backtest_data)に重複しているだけ。FCRはGMO専用の超薄商いマイナー銘柄(価格0.08〜0.12・刻み0.001)で1回の約定でlastが10〜20%動く。全行でbid<ask(クロスなし)・last∈[bid,ask]・bid/ask入替なしを確認済みで、recorder glitchやunit/pair mixではなく実際の薄商い挙動と判定 | schema追記済み |
| venues | gaps | 211876 | 仕様どおり | ローカル再現(paper_logs/venues 50ファイル)で99%超がtrades_*.csv.gz(個々の約定の到着間隔=自然な閑散)。最大ギャップ(2.17h、GMOのBTC/BTC_JPYが同時、2026-08-29 02:10 UTC)は既存known_defects「ベニューごとの独立バックオフ」どおり。quotes側の残りは19:00-19:10 UTC保守で説明可 | schema追記済み(outage window) |

## venues extreme_return 15件の内訳

`paper_logs/QUALITY.json`のvenues.extreme_return(count=15)を`scripts/data_quality.py`のロジック通りに手動列挙(row番号はヘッダー行を0とした生CSV行位置、`paper_logs/venues/quotes_*.csv.gz`で実測)。全15行は下記5件のユニーク事象が`path_glob`の3コピー(`data/venues/`・`paper_logs/venues/`・`backtest_data/auto_venues_*/`)に同一内容で重複しているだけ(5×3=15)。

| # | ts_utc | venue | pair | prev→value (last) | 変化率 | bid/ask文脈 | 判定 |
|---|---|---|---|---|---|---|---|
| 1 | 2026-08-27T13:00:46.471Z | gmo | FCR | 0.115→0.103 | -10.43% | bid 0.113→0.103と同時、ask 0.114で不変 | 実際の価格変動(薄商い) |
| 2 | 2026-08-27T13:18:06.081Z | gmo | FCR | 0.102→0.113 | +10.78% | bid 0.102/ask 0.113で不変、lastがaskへ収束 | 実際の価格変動(薄商い) |
| 3 | 2026-08-27T16:35:57.261Z | gmo | FCR | 0.102→0.113 | +10.78% | bid 0.102/ask 0.113で不変、lastがaskへ収束 | 実際の価格変動(薄商い) |
| 4 | 2026-08-31T03:36:43.256Z | gmo | FCR | 0.105→0.085 | -19.05% | bid 0.103→0.083と同時、ask 0.105で不変 | 実際の価格変動(薄商い) |
| 5 | 2026-08-31T04:10:23.944Z | gmo | FCR | 0.081→0.097 | +19.75% | bid 0.084で不変、ask 0.095→0.098、lastがaskへ収束 | 実際の価格変動(薄商い) |

各#×3コピー(data/・paper_logs/・backtest_data)= 15件。根拠: FCRはGMO専用のマイナー銘柄でbitbank/bitflyerに同一銘柄が無くベニュー間クロスチェック不能だが、各行でbid<ask(crossed_bookなし)・last∈[bid,ask]・bidとaskが同時に入れ替わっていない(swap無し)ことを窓±8行で確認。挙動は「約定が途切れる間lastが前回値のまま固まり、次の約定でbid/askの近い側へ飛ぶ」という薄商い銘柄特有のパターンで、閾値10%を刻み0.001の低価格銘柄で容易に超えるだけ。recorder glitch(bid/ask入替・stale row)・unit/pair mixのいずれにも当たらない。

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
`schema/candles_fx_btc_jpy.json`: zero_volumeの根本原因(`fetch_deep.py`のOHLC列別ffill+volume.fillna(0.0))を確定し、known_defectsに追記。
`schema/venues.json`: extreme_return 15件(実体は5件×3コピー、gmo/FCRの薄商いによる本物の価格変動)を追記。
`schema/oi_snapshots.json`: gapsの2件目(2.9h, 2026-08-31 09:07:42Z→12:03:50Z)について、venues/board_round/bot.jsonl/ws_listing全て欠落なし(PCダウンではない)、かつ`record_oi.py`は失敗時も空欄セルで必ず1行appendする設計(行自体が消えることは無い)ため単純なAPI不通でもない、と切り込んだ調査結果を追記(`deploy/fetch_all.bat`の当該実行がrecord_oi.py到達前の前段ステップで滞留した可能性が高い、ただし確定はオーナーPCのfetch.out.log待ち)。

## 未解決として残るもの

- oi_snapshots gapsの2件目: 「PCダウンではない」「API側の一般的な不通ではない」まで絞り込んだが、`fetch_all.bat`内でどのスクリプト(fetch_history.py/fetch_external.py/fetch_okx.pyのいずれか)が2.9h滞留したかの確定はできていない(オーナーPCの`logs\fetch.out.log`・タスクスケジューラ実行履歴がこのVM/リポジトリに無いため)。
- reit_onr extreme_return(8件): 件数が小さく既存known_defectsの範囲内と推定されるが、1件ずつは未検証(今回はvenues分のみ全件検証)。
- schema/api_health.json: VM上に実ファイルが無く、コード読解のみで作成。オーナーPCの実データで列内容の確認が望ましい。

## 検証

`PYTHONPATH=src python -m pytest -q tests/test_data_quality.py` および全体テスト(976件)を実行し、全て通過(スキーマ・チェッカー変更後も既存の期待値に影響なし)。`scripts/data_quality.py`をVMのローカルコピーに対して再実行し、上記の修正が実際に該当フラグを解消することを確認(例: missing_columns 347→5、schema_undefined_count 0 を維持)。データファイルは変更していない。

---

# 追記 (2026-09-05 続き): paper_logs/QUALITY.json (16:26 UTC, 32データセット) の残りフラグ

入力は本追記の見出しどおり `paper_logs/QUALITY.json`(2026-09-05 16:26 UTC生成、32データセット)+ `paper_logs/INTAKE_latest.json`。件数 > 0 で上表に未掲載の全フラグ(fx_event_ticks/gaps 367871、oi_snapshots/gaps 6 は既存行と完全一致するため対象外)を判定。手法は上表と同一(ローカル実ファイルを開く/`scripts/data_quality.py`のロジックを手動再現、または実際にVM上のローカルコピーに対して再実行)。データファイルは一切変更していない。

このラウンドでスキーマ形式に `quality.skip_checks`(その dataset/file_group にそのチェックを一切適用しない)と `quality.informational_checks`(チェックは発火させ続けるが結果には `informational: true` を付けて実データ問題としては扱わない)を追加し、`scripts/data_quality.py`(`_apply_check_switches`)に実装した。既存の `quality.group_by` / `quality.unique_key` と同じ場所(dataset直下または`file_groups`エントリ内、file_groups側が優先)で解決される。

## 台帳(追加分)

| dataset | flag | count | 判断 | 根拠(要約) | 対応 |
|---|---|---|---|---|---|
| bitflyer_execution_flow | non_monotonic | 538325 | 収集側の修正 | `data/executions_FX_BTC_JPY.csv`・`data/executions_XRP_JPY.csv`のみで発火(`backtest_data/executions_FX_BTC_JPY_31d_*.csv.gz`は0件=別の抽出経路で既にソート済み)。根本原因を`scripts/fetch_history.py`で特定: `before=None`から新しい順にページングして`before=batch[-1]["id"]`で遡る設計のため、`new_rows`は新しい順(降順)で溜まり、それをそのまま追記書き込みしていた。昇順の既存ファイルに対し**毎回の実行で降順の1ブロックを書き込む**ため、実行のたびに非単調な区間が生まれる(サンプル行のprev_ts→tsが連続して減少するパターンと一致) | 修正済み: `scripts/fetch_history.py`に`_order_new_rows`(id昇順ソート)を追加し、追記前に必ず昇順化。既存データファイルは書き換えない(「データは一切変更しない」原則により、過去に書き込まれた降順ブロックはそのまま残り、以後もnon_monotonic/gapsとして検出され続ける)。テスト: `tests/test_fetch_history_candles.py::test_order_new_rows_sorts_ascending_by_id` |
| bitflyer_execution_flow | gaps | 109005 | 収集側の修正(2ファイル)/仕様どおり(1ファイル) | 3ファイルの内訳: `backtest_data/executions_FX_BTC_JPY_31d_*.csv.gz`(median 0.734s、最大ギャップ約810s=閑散期、bitflyer_tapeと同じ「仕様どおり」の性質)/ `data/executions_FX_BTC_JPY.csv`・`data/executions_XRP_JPY.csv`(non_monotonic行と同一原因: 行順序が壊れているため、`_compute_gaps`が前行との差分から計算するgapsも同時に汚染されている実測値ではなく順序バグの副産物) | 上記non_monotonicの修正(`_order_new_rows`)で将来分は解消。既存データは非修正(既知の残存事象として記録) |
| bitflyer_execution_flow | maintenance_window | 80 | 収集側の修正 | `backtest_data/flow_FX_BTC_JPY_20260820.csv`(=`data/flow_FX_BTC_JPY.csv`と同一ビルダー)のみで発火。`scripts/build_flow.py`を確認したところ、`scripts/fetch_deep.py`と全く同じ`ffill(open/high/low/close)+fillna(volume,0.0)`パターンを独自実装しており(既存修正のcandles_fx_btc_jpy/zero_volumeと同根)、欠測分の1分足を前バーの値でOHLC埋めしていた。`synthetic`フラグが無いため実バーと区別不能だった | 修正済み: `scripts/build_flow.py`に`synthetic`列を追加(1=ffill埋め、0=実バー)。既存`schema/candles_fx_btc_jpy.json`の`synthetic`列と同じ設計・同じ「追加日より前の行には列自体が無い」の扱い。既存データファイルは書き換えない。テスト: `tests/test_build_flow.py` |
| bitflyer_execution_flow | zero_volume | 2527 | 収集側の修正 | 上記maintenance_windowと同一原因・同一ファイル(`build_flow.py`のffill+fillna(0.0))。ffillされた行は`volume`列が常に0.0になる | 同上(`synthetic`列で識別可能に) |
| bitflyer_execution_flow | (group_by適用性の確認) | - | 検討済み・不要 | 「複数銘柄が1ファイルに混在していないか」を`backtest_data/flow_FX_BTC_JPY_20260820.csv`・`backtest_data/executions_FX_BTC_JPY_31d_*.csv.gz`のヘッダーで確認したが、いずれも1ファイル1銘柄(製品名がファイル名に含まれ、`path_glob`も製品ごとに分離)で混在なし。gaps/non_monotonicの原因は上記の順序バグで説明済みのため`quality.group_by`は不要と判断 | schema known_defectsに追記済み(対応不要の根拠として記録) |
| daily_crypto_usd_multisource | extreme_return | 869 | 仕様どおり | 5ファイル全てで発火するが、いずれも各ソース(bitstamp 2011-08〜、coinbase/yahoo)の収集開始直後の年代に集中。BTC/ETHが1桁〜低2桁ドルだった時期の実相場変動(2011年のBTC乱高下等)で、隣接行との整合性も確認済み(単発の異常値ではない) | schema追記済み(早期年代の実変動の件) |
| daily_crypto_usd_multisource | zero_volume | 33 | 仕様どおり | 全件`backtest_data/daily_btcusd_bitstamp_20260828.csv.gz`の2011-08-23〜08-29(bitstampのBTC/USD取引開始直後の週)。新規上場直後の薄商いで実際に出来高ゼロの日が生じるのは自然(reit_onrの上場初期zero_volumeと同型) | schema追記済み(開始直後の週の件) |
| external_crypto_klines | extreme_return | 91 | 仕様どおり | 5ファイル(data/・backtest_dataのbinance_XRPUSDT_1d/4h、data/binance_BTCUSDT_1d)。XRP +13〜+26%、BTC +10〜-14%は両銘柄の既知の実ボラティリティ範囲内(前後行と整合、単発の桁ズレ等の兆候なし) | schema追記済み |
| external_crypto_klines | maintenance_window | 355 | 仕様どおり(チェック自体が不適用) | 全件`bitbank_xrp_jpy_1m.csv`(data/・backtest_data)。bitbank社はbitFlyerと無関係の別取引所であり、19:00-19:10 UTCという時間帯そのものに固有の意味はない(隣接行が同一値ではなく、単に該当分だけ値幅ゼロという薄商いの偶然の一致)。チェック名の前提(bitFlyerの保守時間)がそもそも当てはまらないデータセット | 修正済み: `schema/external_crypto_klines.json`にdataset-level `quality.skip_checks: ["maintenance_window"]`を追加(このデータセットの情報源はいずれもbitFlyer以外のため) |
| external_crypto_klines | missing_columns | 5 | 収集側の修正 | `backtest_data/binance_BTCUSDT_1m_210d_*.csv.gz`の実ヘッダーを確認したところ`open_time,open,high,low,close,volume,quote_volume,n_trades,taker_buy_base`(`scripts/fetch_binance_full.py`のフル精度出力と同一形状)だったが、schemaの該当file_groupsは`timestamp,open,high,low,close,volume`(簡易形状)を誤って宣言していた。この210日スナップショットは`fetch_binance_full.py`出力の凍結コピーであり、簡易版ではなかった | 修正済み: `schema/external_crypto_klines.json`の`binance_BTCUSDT_1m_210d_*.csv.gz`のcolumns/unique_keyを`binance_BTCUSDT_1m_full.csv`と同一形状に修正 |
| external_crypto_klines | zero_volume | 19435 | 仕様どおり | 全件`bitbank_xrp_jpy_1m.csv`(data/・backtest_data)。1分粒度のJPY建てマイナー銘柄(XRP/JPY)で無出来高分が多数生じるのは構造上当然(n225f_225labo・reit_onrの薄商いzero_volumeと同型) | 対応不要 |
| fx_usdjpy_reference | gaps | 189 | 仕様どおり | 最大例(172860s≈48h、2024-01-01始まり)は元日を挟むFX年末年始休場。他の反復例(86460s≈24h+60s、2023-01-08/15/22/29=いずれも日曜日)はFXの週末休場(金22:00UTC〜日22:00UTC)という市場構造そのもの。median_gap 60sは1分足として正常 | 対応不要 |
| fx_usdjpy_reference | maintenance_window | 1994 | 収集側の修正(チェック自体が不適用) | `backtest_data/fx_usdjpy_1m_20260822.csv.gz`のみで発火。DukascopyのFXフィードにbitFlyerの保守時間が影響する理由がなく、19:00-19:10UTCに固まって見えるのは単なる薄商いの平坦分足(既存known_defects「volumeはtick-volumeプロキシで頻繁に0」と同種の性質) | 修正済み: `schema/fx_usdjpy_reference.json`の`USDJPY_1m.csv`・`fx_usdjpy_1m_*.csv.gz`両file_groupsに`quality.skip_checks: ["zero_volume","maintenance_window"]`を追加 |
| fx_usdjpy_reference | zero_volume | 285071 | 収集側の修正(チェック自体が不適用) | 同上ファイル。既存known_defectsに「volumeはDukascopyのtick-volumeプロキシで真の約定高ではなく頻繁に0」と明記済み(新情報ではない)。FXに`volume`概念そのものが薄いため、このチェックはデータセットの性質上ほぼ常に大量発火する設計不一致だった | 同上(skip_checksで無効化) |
| regime_composite | extreme_return | 186 | 仕様どおり | `raw/price_daily.csv`と`features_daily.csv`(`close`列は前者の同日値をそのままコピー)の2ファイルで重複発火(93件×2)。該当日は2015-08(著名な2015年8月BTC暴落、約$280→$200)・2015-11(2015年11月BTC急騰、約$230→$464)・2016-01(その後の調整)で、いずれも実在する検証可能な相場変動 | schema追記済み |
| regime_composite | gaps | 1 | 既知欠陥 | `raw/gdelt_tone.csv`の単発ギャップ(2025-07-02、median 86400s=1日に対し約18日分の欠測)。既存known_defects「GDELTのレート制限により四半期単位で分割取得、過去のレート制限時期周辺に薄い欠測が生じるのは想定内」と完全一致 | 対応不要(既存記載どおり) |
| spread_fx_btc_jpy | gaps | 42 | 既知欠陥(大半)/未解決(一部) | 21件のユニーク事象×2コピー(data/・paper_logs/)。最大2件のうち1件(約10.3h、2026-08-28T04:19:17Z終了)は既存known_defects記載の2026-08-27夜〜08-28朝のオーナーPCダウンと同一時刻で完全一致。もう1件(約10.7h、2026-08-26T05:16:24Z終了、1日前)は同種のPCダウン/スリープの可能性が高いが、`paper_logs/venues/`がこのVMには2026-08-27分からしか無く独立したデータセットでの裏取りができず未確認のまま残す。残りの小さいギャップ(194s/約50分/約2.5h、いずれも2026-08-20)は収集初日の起動時の一時的な事象と推定 | schema追記済み(2件目は「未確認」と明記して残す)。08-25/26の件はオーナーPC側のログで確認できれば解消可能 |

## 収集側の修正 一覧(本追記で適用)

7. `scripts/fetch_history.py`: `_order_new_rows`を追加し、`before=`遡りページングで新しい順に溜まる`new_rows`を追記前にid昇順へソート。executions_<product>.csvのnon_monotonic(538,325件)と、それに連動するgapsの誤検出を将来分について解消。既存データは非変更。
8. `scripts/build_flow.py`: `scripts/fetch_deep.py`と同型のffill+fillna(0.0)によるギャップ埋めに`synthetic`列(1=埋めた行、0=実バー)を追加。flow_<product>.csvのmaintenance_window(80件)・zero_volume(2527件)を実バーと区別可能に。既存データは非変更。
9. `scripts/data_quality.py`: `quality.skip_checks`(該当チェックを結果から除外)・`quality.informational_checks`(チェックは発火させたまま`informational: true`を付与)をdataset-level/file_groups-levelで解決する`_apply_check_switches`を追加。`scan_file`の両returnパスに適用。
10. `schema/qa_synthetic.json`: `quality.informational_checks: "all"`を追加し、「SYNTHETIC DATA WARNING」を仕組みとして固定(以後QUALITY.jsonの当該チェックは`informational: true`付きで報告される)。
11. `schema/fx_usdjpy_reference.json`: `USDJPY_1m.csv`・`fx_usdjpy_1m_*.csv.gz`両file_groupsに`quality.skip_checks: ["zero_volume","maintenance_window"]`を追加。
12. `schema/external_crypto_klines.json`: dataset-levelに`quality.skip_checks: ["maintenance_window"]`を追加(全ソースがbitFlyer以外のため)。`binance_BTCUSDT_1m_210d_*.csv.gz`のcolumns誤り(簡易形状→フル精度形状)を修正。

## known_defects 追記(追加分)

`schema/bitflyer_execution_flow.json`: non_monotonic/gaps/maintenance_window/zero_volumeそれぞれの根本原因(fetch_history.pyの追記順序バグ、build_flow.pyの無フラグffill)と修正内容、group_by不要の確認結果を追記。
`schema/daily_crypto_usd_multisource.json`: extreme_returnが早期年代の実変動であること、zero_volumeがbitstamp取引開始直後の週であることを追記。
`schema/external_crypto_klines.json`: extreme_returnの実変動判定、maintenance_windowチェック不適用の理由、missing_columnsのschema修正内容、zero_volumeの薄商い判定を追記。
`schema/fx_usdjpy_reference.json`: zero_volume/maintenance_windowをskip_checksで無効化した理由を追記。
`schema/regime_composite.json`: extreme_returnが2015年のBTC暴落・急騰という実相場変動であることを追記。
`schema/spread_fx_btc_jpy.json`: gapsの内訳(既知の10.3h PCダウンと一致する1件、未確認の10.7h候補1件、起動日の小ギャップ)を追記。

## 未解決として残るもの(追加分)

- spread_fx_btc_jpyのgaps: 2026-08-25夜〜08-26朝と推定される約10.7時間のギャップが、独立したデータセット(venues等)でこのVM上では裏取りできない(paper_logs/venuesが2026-08-27分からしか無い)。オーナーPCの当該日ログで確認が望ましい。
- bitflyer_execution_flowのnon_monotonic/gaps: `fetch_history.py`の追記順序バグは将来分のみ修正済みで、既存の`data/executions_FX_BTC_JPY.csv`・`data/executions_XRP_JPY.csv`に残る過去の降順ブロックは「データは一切変更しない」原則により是正していない(検出され続ける)。一括再ソートするかどうかはオーナー判断待ち。

## 検証(追加分)

`PYTHONPATH=src python -m pytest -q tests/test_data_quality.py tests/test_fetch_history_candles.py tests/test_build_flow.py tests/test_verify_snapshots.py` を実行し全て通過(新規テスト`test_build_flow.py`、`test_data_quality.py`のskip_checks/informational_checksケース、`test_fetch_history_candles.py`の`_order_new_rows`ケース、`test_verify_snapshots.py`の`line_ending_only`ケースを含む)。`scripts/data_quality.py`をVMのローカルコピーに対して再実行し、`external_crypto_klines`のmissing_columns/maintenance_windowが解消、`fx_usdjpy_reference`のzero_volume/maintenance_windowが解消、`qa_synthetic`の全チェックに`informational: true`が付与されることを確認。データファイルは一切変更していない。
