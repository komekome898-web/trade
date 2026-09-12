# G2 データ在庫棚卸し(bitFlyer FX_BTC_JPY, 分足)

出典: `data/INTAKE_latest.json`(棚卸し台帳)/ `data/QUALITY.json` / `backtest_data/` 一覧 / `schema/*.json`。作成 2026-09-06。

## 0. 追記(2026-09-06、P2-08 補助データ 2 件、前任エージェントの中断分を完了)

| 種別 | パス | span (UTC) | rows | 品質検査 | 台帳 |
|---|---|---|---|---|---|
| USDJPY 1分足(Dukascopy BID) | `backtest_data/fx_usdjpy_1m_20170801_20221231/usdjpy_1m.csv.gz` | 2017-08-01 00:00 〜 2022-12-30 23:59(既存スナップショット2023-01-01〜と重複なし・列/時刻形式一致) | 2,422,080 | 重複0・負値0・週末外60分超欠損10件(年別内訳・詳細はREADME/QUALITY.json)。`schema/fx_usdjpy_reference.json`のpath_glob/file_groupsキーを実ファイル名に修正済み(前任が誤った glob を残していた) | `data/INTAKE_latest.json`に登録済み(`scripts/intake_ledger.py`実行、2026-09-06) |
| 現物 BTC_JPY 1分足(lightchart) | `backtest_data/bitflyer_lightchart_BTC_JPY_1m_20260906/candles_1m_<year>.csv.gz`(12ファイル、`raw_<year>.tar`12本、`candles_1m_index.json`) | 2015-08-02 02:07 〜 2026-09-06 12:00 | 5,828,554(null-OHLC 493,858) | gap>5min 16,590件(年別内訳README)。FX_BTC_JPYとの重なり期間close相関: 年別最低0.9944、全期間プール0.99969(P2-08 BLINDSPOT_AUDIT診断(d)のCPU軽量版) | 同上 |

詳細・出典URL・ライセンス注記・検査結果全文は各ディレクトリの README.md / QUALITY.json を参照。既存の (削除済み文書) 調達票(USDJPY対照5・現物ベーシス診断(d)の2行)は取得完了として更新要(未実施、リード側作業)。

## 0.1 追記(2026-09-11、Bybit BTCUSDT 無期限 1分足、K1 段階 2、L-095)

| 種別 | パス | span (UTC) | rows | 品質検査 | 台帳 |
|---|---|---|---|---|---|
| Bybit BTCUSDT 無期限 1分足 | `backtest_data/bybit_BTCUSDT_1m_20260910/bybit_BTCUSDT_1m_<year>.csv.gz`(5ファイル、2022〜2026、`MANIFEST.md`にファイルサイズ・sha256・出典URL・取得日・タイムスタンプ基準を記録) | 2022-01-01 00:00 〜 2026-08-31 23:59 | 2,453,760(欠測 0 件。全区間で分の欠落なしを確認済み) | 欠測 0.00%(全年)・古い終値 1.1〜8.6%(閾値10%未達、除外年なし)・OHLC不整合0・`|1分r|>1000bp` 0(`docs/PHASE2/K1/xvenue/bybit_data_check.json`) | `docs/DATA_CONSUMPTION_LOG.md` §2 に登録済み(2026-09-11) |

出典: 2022〜2024は`kline_for_metatrader4`月次アーカイブ(タイムスタンプはブローカー時間UTC+3、-3h補正。オフセットは2024-12-31の約定畳み込みとの突き合わせで実測: 補正後1239/1261分一致、補正無し0/1440)。2025-01〜2026-08は`trading/BTCUSDT/`日次約定ファイルをUTCの分に畳んだもの。2022-2024側で見つかった実データの欠落(2023年12月の大部分、2024年1〜3月の大部分、いずれも`kline_for_metatrader4`アーカイブ自体の欠落。取得側のバグではないことを直接確認)は同じ日次約定ファイルの畳み込みで補完済み(詳細は`MANIFEST.md`)。

## 1. スナップショット一覧

| 種別 | パス | span (UTC) | rows | gap>5min | 既知の欠陥 |
|---|---|---|---|---|---|
| 1分足 | `data/candles_FX_BTC_JPY.csv` | 07-23 12:09 〜 08-23 12:25 (31d) | 44,657 | 0(実測、5分超gapなし) | 19:00 UTC前後にフラット行(bitFlyerメンテ窓)1,150件超(`QUALITY.json` maintenance_window)。ゼロ出来高行がffillで前足コピーになる既知バグ(`schema/candles_fx_btc_jpy.json`) |
| 1分足(凍結) | `backtest_data/candles_FX_BTC_JPY_31d_20260823.csv.gz` | 同上(上記の永久コピー) | 44,657 | 同上 | 同上 |
| 1分足(凍結・旧) | `backtest_data/candles_FX_BTC_JPY_30d_20260820.csv` | 07-21 08:17 〜 08-20 08:22 (30d) | 43,206 | 未走査 | 同上想定 |
| 1分足(凍結・旧小) | `backtest_data/candles_FX_BTC_JPY_20260820.csv` | 07-30 03:28 〜 08-20 03:38 | 30,251 | 未走査 | 上記30dスナップショットの部分集合とみられる |
| 約定履歴 | `data/executions_FX_BTC_JPY.csv` | 07-23 12:09 〜 08-23 12:25 (31d) | 982,000 | — | mtime 08-23 のまま**更新停止中**(今日から13日停滞) |
| 約定履歴(凍結) | `backtest_data/executions_FX_BTC_JPY_31d_20260823.csv.gz` | 同上 | 982,000 | — | 同上。これ以外の約定スナップショットは存在しない |
| WS生キャプチャ(板・気配) | `data/ws/FX_BTC_JPY_2026082*.jsonl.gz` ×4 | 08-20 05:07〜10:42のみ(単日・断片) | 523/71,357/14,669/58,267 | — | `QUALITY.json` flag無し(4ファイルのみ、長期録画なし) |
| 板再構成(5s) | `backtest_data/board_round_20260904/board_round_series_5s.csv.gz` | 08-20 06:13 〜 09-04 12:50 (15d) | 249,336 | 未走査 | crossed_book 670件・extreme_return 68件(スパイク、`QUALITY.json`) |
| WS抽出tape(ticker/executions/board_top5) | `paper_logs/tape/*_2026*.csv.gz`(41ファイル) | 08-20 06:13 〜 **09-05 13:47**(直近まで継続) | — | — | executions側 duplicate_keys 15,041件(同一μ秒の複数約定、想定内) |
| Binance BTCUSDT 1分足(高精度) | `data/binance_BTCUSDT_1m_full.csv` / `backtest_data/binance_BTCUSDT_1m_210d_20260820.csv.gz` | 2026-01-22 11:34 〜 08-20 11:36 (210d) | 302,403 | 未走査 | 不整合なし(このパイプラインが唯一のBinance長期ソース) |

## 2. 三点(bitFlyer分足 ∧ Binance分足 ∧ bitFlyer約定)最長連続窓

**約定履歴が律速**(唯一のスナップショットが07-23〜08-23のみ)。Binanceは08-20 11:36までしかなく、これが上限。
→ **最長連続窓 = 2026-07-23 12:09 〜 2026-08-20 11:36(約28日)**。

**31d候足の延伸可否**: `backtest_data/candles_FX_BTC_JPY_30d_20260820.csv`(07-21〜08-20)と`data/candles_FX_BTC_JPY.csv`(07-23〜08-23)は列は同一(ts/open/high/low/close/volume)だが、**重複区間4万行中3,405行でclose等の値が食い違う**(fetch_history.py/fetch_deep.pyの再構築差と推測、`known_defects`参照)。単純concatは不可。値の優劣を決めてから結合する追加作業が要る。

## 3. storm_events / board_round の span

- `storm_events_20260820`: 16イベント、各2時間・1秒足(7,201行)。全体span **2026-07-21 13:40 〜 2026-08-20 09:37**。
- `board_round_20260904`: 5秒足連続シリーズ、**2026-08-20 06:13 〜 2026-09-04 12:50(15日)**。

## 4. コスト定数(`config/constants.yaml` bitflyer_fx_btc_jpy)

| 項目 | 値 | source_type |
|---|---|---|
| taker_fee_pct | 0.0% | primary_document(egress不可のため二次確認: API docs+実コード) |
| quoted_spread_median_bps | **失効(2026-09-08 の全捨て)** — 単位ごとに測り直す | discarded |
| realized_taker_one_way_bps | **失効(2026-09-08 の全捨て)** — 単位ごとに測り直す | discarded |
| realized_round_trip_bps | **失効(2026-09-08 の全捨て)** — 単位ごとに測り直す | discarded |
| funding_swap_daily_pct | 0.06%/日 | measured(3日サンプル) |
| taker_round_trip_floor_bps_OLD | **失効(2026-09-08 の全捨て)** — 単位ごとに測り直す | discarded |

## 5. 60日分足シールに向けて不足しているもの・入手法

- **不足**: 08-24〜09-05(約13日)の bitFlyer 分足/約定REST欠落(収集停止中)。ただし同期間は `paper_logs/tape/executions_2026{0824..0905}.csv.gz`(WS由来)でカバー可能——分足への再構築が未実施。
- **不足**: 約定REST収集の再開そのもの(今日時点でbitFlyer API保持31日=08-06以降のみ再取得可)。
- **入手コマンド(実行しない・名称のみ)**:
  - 直近31日の再取得: `PYTHONPATH=src python scripts/fetch_deep.py FX_BTC_JPY --days 31`
  - 継続収集(cron/systemd): `PYTHONPATH=src python scripts/fetch_history.py`(config.yaml product_code=FX_BTC_JPY)
  - 板WS録画の継続: `PYTHONPATH=src python scripts/record_realtime.py FX_BTC_JPY`
- 上記を直ちに開始し、旧凍結分(07-21〜08-23、重複区間の値差解消要)とWS-tape再構成分を繋いでも約45日程度。**60日到達には本日から更に2週間程度の継続収集が必要**。
