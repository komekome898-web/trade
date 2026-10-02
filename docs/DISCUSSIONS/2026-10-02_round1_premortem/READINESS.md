# 研究の第 1 周の準備の棚卸し(データ・経費・外部データ・測定器)

作成 2026-10-02 01:10〜02:20 UTC、この環境から。**リポジトリのファイルは 1 つも変更していない。封印されたデータの中身は開いていない**(台帳・文書・ファイル名・大きさ・日付の記述だけを見た。封印の台帳に載っていないファイルの時刻の列だけは読んだ箇所がある。その行には「時刻の列だけ読んだ」と書いた)。

印: **【事実】** = ファイルかコマンドの出力で確かめた(根拠を同じ行に書く)/ **【推定】** = 機構や文書からの推論で、確かめていない / **【未確認】** = 確かめていない、または確かめられなかった

## 0. 着手前の表(CLAUDE.md §0.1)

| やろうとすること | オーナーの原文の該当語(逐語) |
|---|---|
| 第 1 周に使うデータ・経費の材料・外部データ・測定器の状態を調べ、穴を一覧にする | 「2.については詳しく練ってからはじめたい」(L-535) |
| 「始める前に埋める穴」を列挙する | 「今のまま始めると必ず不備がおきてまた全捨てになります」(L-535) |
| 範囲を 2 区間から、手元の全期間・全取引所に広げる | 「戦略の特性(強み弱み)を理解するためなら短い封印期間を使わずに大量データから学習する方が理にかなってると思いませんか？」(L-536) |
| 封印の範囲を表にする(どのデータのどの期間が封印か) | 「短い封印期間を使わずに」(L-536) |
| 成果物を scratchpad の READINESS.md に書く(リポジトリは変更しない) | **(該当語なし)**(リードの委任文の指示) |
| bitFlyer などの公開 API を叩いて到達を確かめる | **(該当語なし)**(リードの委任文の指示) |

## 1. 第 3 版(`docs/DISCUSSIONS/2026-10-01_research_structure_intake_and_combiner.md`)の記述と食い違った事実

リードの計画を変えるので先に置く。

| # | 第 3 版の記述 | 今回確かめた事実 | 根拠 |
|---|---|---|---|
| C-1 | §5-1B・§7・§12「bitFlyer の資金調達率は B(1 回 500 件 = 2026-04-18〜。それより前は未確認)」 | **A。2024-03-28 21:00(制度の切れ目)から公開 API で遡れる**。公式文書に `from`(開始日時)・`to`・`count`(最大 500)の引数がある。`from=2024-03-28T00:00:00` で 500 件、計算 2024-03-28T21:00〜2024-09-11T05:00、決済 05/13/21 時、8 時間刻みの抜け 0 件【事実】 | 付録 R-1〜R-4 |
| C-2 | §7「#46 仲値は USDJPY の分足を使う。手元は 2017〜2022 と 2026 の一部【事実】」 | `backtest_data/fx_usdjpy_1m_20260822.csv.gz`(Dukascopy、bid の OHLC と ask_close)が **2023-01-01 00:00〜2026-08-21 23:59 を月ごとに埋めている**(2023-01 は 38,880 行 … 2026-08 は 25,920 行)。手元は 2017-08〜2026-08-21 で切れ目なし【事実】(時刻の列だけ読んだ。この系列は封印の台帳に無い) | 付録 R-20、`schema/fx_usdjpy_reference.json` |
| C-3 | §2 F3「経費の床 往復 p50 2.16 bp」(期間の記述なし) | 2.16 bp(E-b、0.01 BTC で板を歩く往復)は **板 5 段 2026-08-20〜08-26 の 7 日**、気配・約定は 2026-08-20〜09-05 の 16 日で測った。**どちらも予定の判定区間(2025-12-12〜2026-09-06)の中**で、探索区間(2023-12-18〜2025-12-12)の経費は 1 日も測っていない【事実】 | `docs/PHASE2/EXEC/RESULT.md` 5・14 行、`docs/DATA_CONSUMPTION_LOG.md` 25 行 |
| C-4 | §5-1B「Binance 1 分足 … CFD 期間」 | 手元の Binance 現物 1 分足は **2026-08-31 23:59 で終わる**。判定区間の終わり 2026-09-06 までの 6 日が無い(公開アーカイブには 2026-09-06 の日次がある: 200)【事実】 | `backtest_data/binance_BTCUSDT_1m_20240101_20260831/README.md`、付録 R-9 |
| C-5 | 付録 B-9「Farside 200」、DATA.md「tardis 標本日 取得済」 | 今日(2026-10-02 01:17〜01:21 UTC)はどちらも **Cloudflare の 403**(この環境の出口から)。10-01 は Farside 200、09-21 は tardis 200 だった = 間欠的。「取れない」ではない【事実】 | 付録 R-12・R-13 |

---

## A + A'. 価格・約定・足・気配のデータ(取引所 × 商品 × 粒度 × 期間 × 封印 × 所在)

列「封印」= 封印の台帳(`backtest_data/phase2_sealed/*/SEALED.json`)に載っているか。「消費」= `docs/DATA_CONSUMPTION_LOG.md` の記録。「容器」= この容器のディスクにあるか(`data/` は gitignore 域で、オーナーの PC か別の容器にしか無い)。

### A-1. bitFlyer

| 商品 | 粒度・列 | 期間 | 封印 | 消費 | 所在 / 容器 | 印・根拠 |
|---|---|---|---|---|---|---|
| FX_BTC_JPY | 1 分足(lightchart。OHLC、出来高、テイカー買い/売りの出来高(2017-07〜)、建玉らしき 2 列(推定・未確認))。約定 0 の分は OHLC 空。**気配(bid/ask)は無い** | 2015-11-28 04:54〜2026-09-06 00:00(年ファイル 12 本) | **P2-08: 2023-12-18 以降を封印**(2017〜2026 の 10 本が台帳。2015・2016 は台帳に無い = 封印外)。`raw_YYYY.tar` 12 本は台帳に無い | 2017-01-01〜2026-08-31 を K1 で選択に消費(L-090・L-093・L-095)。封印の作成(2026-09-06 17:12 UTC)の後、2026-09-10〜11 にオーナー承認(L-087〜L-090「一度だけ見る」)のもとで読まれた | `backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/` / 容器にある | 【事実】SEALED.json、README、git ls-files、消費台帳 24・36 行 |
| BTC_JPY(現物) | 1 分足(lightchart、同じ列) | 2015-08-02 02:07〜2026-09-06 12:00 | **P2-08: 2023-12-18 以降**(2015〜2026 の 12 本)。`raw_YYYY.tar` は台帳に無い | 未使用(DATA.md) | `backtest_data/bitflyer_lightchart_BTC_JPY_1m_20260906/` / ある | 【事実】同上 |
| FX_BTC_JPY | 1 分足(約定から作った継続結合) | 2026-07-23 12:09〜2026-09-05 13:47 | P2-08(全部が境より後) | 面探索(重度) | `backtest_data/fx_btc_jpy_1m_continuous_20260906/` / ある | 【事実】SEALED.json |
| FX_BTC_JPY | 約定 31 日 | 2026-07-23 12:09〜08-23 12:25 | P2-08・P2-08b | 選択に消費 | `backtest_data/executions_FX_BTC_JPY_31d_20260823.csv.gz` / ある | 【事実】SEALED.json |
| FX_BTC_JPY | 1 分足 30 日・31 日・20260820 版 | 2026-07-21〜08-20 / 07-23〜08-23 | **台帳に無い**(下の A''-2) | 選択に消費 | `backtest_data/candles_FX_BTC_JPY_{30d_20260820,31d_20260823,20260820}.csv*` / ある | 【事実】時刻の列だけ読んだ(付録 R-21) |
| FX_BTC_JPY | 約定(μs、tardis 形式) | 2026-07-23〜09-06 | P2-08b: 2026-08-23 以降 | 未使用 | `backtest_data/bitflyer_executions_us_20260723_20260906/` / ある | 【事実】SEALED.json |
| FX_BTC_JPY | 約定 31 日 | 2026-08-08〜09-08 | P2-08b: 2026-08-23 以降 | 未消費 | `backtest_data/executions_FX_BTC_JPY_31d_20260908/` / ある | 【事実】 |
| FX_BTC_JPY | 約定(向きつき)の**標本日 = 毎月 1 日** | DATA.md: 2019-09-01〜2026-09-01 の 85 日(別の容器にあったが、09-21 の追記ではその容器はもう無く 16 日だけ取り直した。85 日が今どこかに残っているかは未確認)。この容器: 2023-07-01〜2024-10-01 の 16 日 | 台帳に無い | O-3c の実効スプレッドに使用 | `data/tardis/bitflyer_FX_BTC_JPY_trades/`(gitignore。規約 9.2 で生は共有しない)/ 16 日だけある | 【事実】`ls`(付録 R-14)、DATA.md 69 行 |
| FX_BTC_JPY | 気配・約定・板 5 段(監査用) | 2026-08-20〜09-05(板は 08-20〜08-26) | 台帳に無い | ④-1 経費の床に消費 | `backtest_data/auto_bitflyer_executions_20260905/`・`_20260921/` / ある | 【事実】消費台帳 25 行 |
| FX_BTC_JPY | tape: 約定・ticker(気配の変化)・板 10 段(37 日分)・板 5 段(7 日分) | 2026-08-20〜2026-10-01(既定ブランチ) | P2-08b: 18 ファイル(08-20〜09-06)が台帳、境 2026-08-23。それ以降は台帳に無い | 一部消費 | `paper_logs/tape/`(既定ブランチ `claude/bitflyer-trading-bot-hhxxaf`)/ 作業ブランチは古い | 【事実】`git ls-tree`(付録 R-22) |
| FX_BTC_JPY | 気配(bot の REST、5 秒)+ 抜けの補い | 2026-08-20〜10-01 | 台帳に無い | — | `paper_logs/spread_FX_BTC_JPY.csv`、`backtest_data/spread_backfill_20261002/` / ある | 【事実】README |
| FX_BTC_JPY | 約定(API の取り直し) | 2026-09-18 07:24〜09-21 01:39 | 台帳に無い | — | `backtest_data/bitflyer_executions_backfill_20260921/` / ある | 【事実】DATA.md |
| FX_BTC_JPY | 板・ticker・約定の生 WS | 2026-08-20〜(オーナーの PC) | — | — | オーナーの PC `data\ws\` / 無い | 【事実】DATA.md 67 行 |
| BTC/ETH/XRP_JPY | 1 分足・約定・flow 30 日 | 〜2026-08-20 | 台帳に無い | 未使用 | `backtest_data/candles_*_JPY_20260820.csv` / ある | 【事実】 |
| FX_BTC_JPY の 1 分足のうち、手元の**旧制度(Lightning FX・SFD)**で封印の外 | — | **2015-11-28〜2023-12-17 = 2,942 日** | 封印外 | 2017〜 は K1 で消費 | 同上 | 【事実】python で計算(付録 R-23) |
| FX_BTC_JPY の**今の制度(Crypto CFD)** | — | 2024-03-28〜2026-09-06 = 892 日 | **全部が P2-08 の封印の中** | K1 第 16〜18 部で消費済み(封印の後、承認のもと) | 同上 | 【事実】同上 |

### A-2. 海外の暗号資産

| 取引所・商品 | 粒度 | 期間 | 封印 | 所在 / 容器 | 印・根拠 |
|---|---|---|---|---|---|
| Binance 現物 BTCUSDT | 1 分足(OHLCV・約定数・テイカー買い) | 2017-08-17 04:00〜2023-12-31(年 7 本)+ 2024-01-01〜2026-08-31(1 本、欠け 0) | **P2-08: 2023-12-18 以降**。`raw/BTCUSDT-1m-*.zip`(2024-01〜2026-08)62 本は台帳に無い | `backtest_data/binance_BTCUSDT_1m_20170801_20231231/`・`_20240101_20260831/` / ある | 【事実】SEALED.json、README |
| 同 | 1 分足 210 日 | 2026-01-22〜08-20 | **台帳に無い** | `backtest_data/binance_BTCUSDT_1m_210d_20260820.csv.gz` / ある | 【事実】DATA.md、消費台帳 31 行(選択に消費・重度) |
| 同 | 1 分足 | 2026-07-30〜08-20 | 台帳に無い | `backtest_data/binance_BTCUSDT_1m.csv` / ある | 【事実】時刻の列だけ読んだ(R-21) |
| 同 | 1 秒足・aggTrades | 2026-07-23〜09-05 | P2-08b: 2026-08-23 以降 | 本体は git に無い(README・MD5SUMS だけ。DATA.md §8 #15)/ 無い | 【事実】`ls` |
| Binance USD-M BTCUSDT 無期限 | aggTrades | 2026-07-23〜09-05 | P2-08b | 本体は git に無い / 無い | 【事実】 |
| 同 | 1 分足 | 公開アーカイブ: 2020-01 から(2019-12 は 404) | — | 取得していない | 【事実】R-15 |
| 同 | metrics(建玉・比率、5 分) | 公開アーカイブ 2020-09-01〜(比率の列は 2022-06〜)。手元は日次の平均だけ: `regime_composite_20260901/raw/binance_metrics.csv` 2021-01-01〜2026-08-31、`paper_logs/binance_daily/metrics.csv` 2026-08-04〜09-30 | 台帳に無い | ある(日次の平均だけ) | 【事実】時刻の列だけ読んだ、付録 B-6(第 3 版) |
| 同 | 資金調達率 | 公開アーカイブ 2020-01〜。手元は日次: `regime_composite_20260901/raw/binance_funding.csv` 2020-01-01〜2026-08-31 | 台帳に無い | ある(日次) | 【事実】同上 |
| 同 | bookTicker(気配) | 公開アーカイブ: 2024-03-30 は 200、2025-06-01 は 404(配信が途中で止まった【推定】) | — | 取得していない | 【事実】R-15 |
| Binance COIN-M BTCUSD_PERP | metrics(5 分、比率の列は空)/ 清算 / 資金調達率 / aggTrades | metrics・清算 2023-06-25〜2024-10-14(379 日・472 日)、資金調達 2023-05〜2024-11、1 分足は公開 2020-08〜。aggTrades 475 日は DATA.md に「取得済」だが**git に無い** | 台帳に無い | `backtest_data/binance_cm_o3c_20260913/` / aggTrades は無い | 【事実】git ls-files、DATA.md |
| Bybit BTCUSDT 無期限 | 1 分足 | DATA.md: 2022-01-01〜2026-08-31 | 台帳に無い | `backtest_data/bybit_BTCUSDT_1m_20260910/` は **MANIFEST.md だけ**(csv.gz は gitignore)/ 無い | 【事実】`ls`、`ENV_DEFECTS.md` G-5 |
| BitMEX XBTUSD | 1 秒足 | 2017-01-01〜2021-12-31(1,826 日) | 台帳に無い | `backtest_data/bitmex_trade_1s_XBTUSD/` / ある | 【事実】。2017〜2019 は K1 の探索で全読、2020〜2021 は一度だけ開封済み(DATA.md 100 行)。BitMEX は 2026-09-23 に閉鎖(DATA.md) |
| BitMEX | 保険基金 日次 | 2016-02-28〜2026-09-11 | 台帳に無い | `backtest_data/bitmex_insurance_20260912/` / ある | 【事実】DATA.md |
| Coinbase BTC-USD | 日足 / 1 分足 | 日足 2015-07-20〜2026-08-28(手元)。1 分足は公開 API で 2017-01-01 に 53 本(約定の無い分は返らない)、2015-01-15 は 0 本(始まりは未特定) | 台帳に無い | `backtest_data/daily_btcusd_coinbase_20260828.csv.gz` / 1 分足は手元に無い | 【事実】R-16、時刻の列だけ読んだ |
| Bitstamp・Yahoo BTCUSD | 日足 | 2011-08-22〜 / 2014-09-17〜(〜2026-08-28) | 台帳に無い | `backtest_data/daily_btcusd_{bitstamp,yahoo}_20260828.csv.gz` / ある | 【事実】 |
| Upbit KRW-BTC | 1 分足 | 公開 API で 2017-12-31T23:59 が返る(始まりは未特定) | — | 手元に無い | 【事実】R-17 |
| Kraken XBTUSD | 1 分足 | 不明 | — | `data/kraken_XBTUSD_1m.csv` / 無い | 【未確認】DATA.md にだけある |
| OKX BTC 無期限 | 建玉・比率(5 分・1 時間)の自前記録 | 2026-08-20〜10-01(PC で継続) | 台帳に無い | `backtest_data/auto_okx_*`、`paper_logs/oi_snapshots.csv` / ある | 【事実】 |
| OKX | 1 分足(history-candles) | 2020-01-01〜(DATA.md) | — | 取得していない | 【事実】DATA.md |
| Gate.io・Coinalyze | 清算 | Gate 2026-06-10〜09-08、Coinalyze 集計 | 台帳に無い | ある | 【事実】DATA.md |
| 4 取引所の清算の WS | 生 | 2026-09-09〜(PC で継続) | 台帳に無い | `paper_logs/liquidations/` / ある | 【事実】 |
| Binance XRPUSDT | 1 分・4 時間・日足 | 不明 | 台帳に無い | `backtest_data/binance_XRPUSDT_*.csv` / ある | 【未確認】期間は見ていない |

### A-3. 国内の他の取引所・FX・株

| 対象 | 粒度 | 期間 | 封印 | 所在 / 容器 | 印・根拠 |
|---|---|---|---|---|---|
| bitbank BTC/JPY | 約定の**標本日 = 毎月 1 日** | 2017-09-01〜2026-09-01(109 日) | 台帳に無い | `backtest_data/bitbank_btc_jpy_transactions_monthly_first_days/` / ある | 【事実】ファイル名 |
| GMO コイン・bitbank | 気配・約定 | 2026-08-27〜09-21(手元)、PC で継続 | 台帳に無い | `backtest_data/auto_venues_20260921/`、`paper_logs/venues/` / ある | 【事実】 |
| USDJPY | 1 分足(bid の OHLC + ask_close、Dukascopy) | 2017-08-01〜2022-12-30 / 2023-01-01〜2026-08-21 | 2017〜2022 のファイルは P2-08 の台帳にあるが境より前で実質封印なし。2023〜2026 のファイルは**台帳に無い** | `backtest_data/fx_usdjpy_1m_20170801_20221231/`、`fx_usdjpy_1m_20260822.csv.gz` / ある | 【事実】C-2 |
| USDJPY | イベントの前後のティック | 2005〜2014 / 2015〜2026(日銀などの日だけ) | 台帳に無い | `backtest_data/fx_event_ticks_*` / ある | 【事実】ファイル名 |
| USDJPY | 日次(ECB の参照値) | 2014-12-31〜2026-10-01 | 台帳に無い | `paper_logs/binance_daily/usdjpy.csv`(既定ブランチ) | 【事実】時刻の列だけ読んだ |
| FRED(金利・DEXJPUS)・GMO のスワップ | 日次 | 各系列 | 台帳に無い | `backtest_data/fred_*.csv`、`gmo_swap_usdjpy.csv` / ある | 【未確認】期間は見ていない |
| 日経 225 先物 | 日足(225Labo) | 1990-01-04〜2026-08-28 | P2-01(開封承認あり)・P2-04(境 2015-08-29) | `backtest_data/n225f_225labo_20260828/` / ある | 【事実】SEALED.json |
| TOPIX 先物・ミニ | 日足 2001-01-04〜 / 2008-06-16〜、1 分足 2025-12-30〜 | 台帳に無い | `backtest_data/{topixf,mini_topixf}_225labo_20260907/` / ある | 【事実】DATA.md |
| ETF 日足(1343・1321・1348 ほか) | 2011-09-05〜2026-09-04 | P2-02・P2-03(開封承認あり)、P2-03b(境 2022-03-05)、P2-04(境 2015-08-29) | `backtest_data/jpx_etf_daily_*` / ある | 【事実】SEALED.json |
| 日経 225 のイベント・個別の価格 | 2000-01-04〜2026-09-04 | P2-07(境 2018-06-12) | `backtest_data/nk225_events_20260904/` / ある | 【事実】 |
| REIT・ONR | 2008-09-16〜2026-09-03 | P2-02(開封承認あり) | `backtest_data/reit_onr_20260904/` / ある | 【事実】 |

### A-4. 台帳と実体の食い違い

| 種類 | 対象 | 印・根拠 |
|---|---|---|
| ファイルはあるが DATA.md に名前が無い(研究の中間物・合成を除く) | `audit_fetch_bitflyer_history_20260906`(95)、`auto_bitflyer_executions_20260921`、`auto_venues_20260921`、`auto_oi_snapshots_*`、`auto_okx_open_interest_*`(09-06 以降)、`binance_XRPUSDT_*.csv`、`candles_*_20260820.csv`、`daily_*_20260828.csv.gz`、`flow_FX_BTC_JPY_20260820.csv`、`fred_*.csv`、`liquidations_repaired_20260912`、`okx_20260905`、`okx_btc_*_20260823.csv`、`spread_backfill_20261002`、`k1_newenv_{a,g}` | 【事実】DATA.md を名前で grep(付録 R-24)。DATA.md は行の中で別名や `*` でまとめて書いている場合がある(例: `daily_btcusd_*`)ので、「台帳に無い」は名前の完全一致が無いという意味 |
| DATA.md にあるがこの容器に無い | `data/` の全部(Binance 1 秒の標本、Kraken 1 分、Deribit DVOL 1 時間、`funding_rate_history.csv`、`basis_1m.csv`、`attention.csv`、`data/tape/*`、`data/ws/*`、`data/liquidations/*` ほか)、Bybit 1 分足の本体、Binance COIN-M aggTrades、P2-08b の Binance の本体 | 【事実】`ls`(R-24)。`data/` は gitignore 域で、オーナーの PC にあるか、別の容器にあった【推定】 |

---

## A''. 封印の範囲

### A''-1. 封印の台帳(7 単位 + 開封済み 3 単位)

承認済みの規則(`src/bot/research/sealed.py` 1〜30 行): **各入力ファイルの時間の幅の最後の 30% を暦日で封印**し、さらに単位を封印した日(`forward_start`)以降を全部封印する。P2-08 だけは単位全体で境を明示(`--seal-from 2023-12-18`)し、ファイルごとの 70/30 の境は `seal_from_ts_per_file` に残した【事実】。

| 単位 | 対象 | 境(この日以降が封印) | forward_start | 開封承認 | 印・根拠 |
|---|---|---|---|---|---|
| P2-01 | 日経 225 先物 日足、paper_logs 2 本 | 2020-12-21 | 2026-09-06 | **あり**(`UNSEAL_APPROVED`、2026-09-06) | 【事実】 |
| P2-02 | REIT・ONR、ETF 日足 | 2021-04-13 | 2026-09-06 | **あり** | 【事実】 |
| P2-03 | ETF 日足 15 本 | 2022-03-05 | 2026-09-06 | **あり** | 【事実】 |
| P2-03b | ETF 日足(TOPIX 代替)2 本 | 2022-03-05 | 2026-09-06 | なし | 【事実】 |
| P2-04 | 日経 225 先物 日足 3 本、ETF 日足 2 本 | 2015-08-29 | 2026-09-06 | なし | 【事実】 |
| P2-07 | 日経 225 のイベント・個別 190 本 | 2018-06-12 | 2026-09-06 | なし | 【事実】 |
| **P2-08** | bitFlyer FX 1 分足 10 本(2017〜2026)、bitFlyer 現物 1 分足 12 本、Binance 現物 1 分足 8 本、FX 1 分足の継続結合、約定 31 日、USDJPY 1 分足 2017〜2022 | **2023-12-18**(明示。ファイルごとの 70/30 の境は例えば 2024 年のファイルで 2024-09-12) | 2026-09-06 | なし | 【事実】SEALED.json(付録 R-25) |
| P2-08b | bitFlyer の tape 18 本・約定(μs)46 本・約定 31 日、Binance 1 秒・aggTrades(現物・無期限) | 2026-08-23 | 2026-09-08 | なし | 【事実】 |

### A''-2. P2-08 の封印が各出所の全期間のどれだけを外しているか(L-536 の問いの材料)

| 出所 | 手元の全期間 | 封印(2023-12-18〜) | 割合 | 封印の外に残る期間の制度 | 印 |
|---|---|---|---|---|---|
| bitFlyer FX 1 分足 | 2015-11-28〜2026-09-06(3,935 日) | 993 日 | 25.2% | **全部が旧制度(Lightning FX・SFD)** | 【事実】R-23 |
| bitFlyer 現物 1 分足 | 2015-08-02〜2026-09-06(4,053 日) | 993 日 | 24.5% | 現物(制度変更なし) | 【事実】 |
| Binance 現物 1 分足 | 2017-08-17〜2026-08-31(3,302 日) | 988 日 | 29.9% | — | 【事実】 |

- **今の制度(CFD)の 892 日は全部が封印の中**にある。封印を開けずに使える bitFlyer FX の履歴は、全部 SFD があった頃のもの【事実】。
- P2-08 の境の期間は、封印を作った後の 2026-09-10〜11 に、オーナー承認のもとで **K1 第 16〜18 部が読んでいる**(消費台帳 24・36・38 行、第 3 版 F9、状態板 38 行)【事実】。封印は「誰も見ていない区間」ではなく、「これから先の読みを止める区間」になっている【推定】。

### A''-3. 封印の台帳に載っていないが、封印と同じ期間の値を持つファイル(封印の穴)

`src/bot/bt/data/allowlist.py` は「台帳に載ったパス、または同じ bytes のファイル」だけを封印として扱う(同 docstring)【事実】。下は**別のファイル**なので、新しい環境からも境を越えて読める【推定:docstring からの推論。実際に読ませて確かめてはいない】。

| ファイル | 封印と重なる期間 | 印・根拠 |
|---|---|---|
| `backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/raw_2023.tar`〜`raw_2026.tar` | P2-08 の境以降(生のページ) | 【事実】台帳に tar が無い(R-25) |
| `backtest_data/bitflyer_lightchart_BTC_JPY_1m_20260906/raw_2023.tar`〜`raw_2026.tar` | 同上 | 【事実】 |
| `backtest_data/binance_BTCUSDT_1m_20240101_20260831/raw/*.zip`(62 本) | 2024-01〜2026-08 | 【事実】 |
| `backtest_data/binance_BTCUSDT_1m_210d_20260820.csv.gz` | 2026-01-22〜08-20 | 【事実】R-21 |
| `backtest_data/binance_BTCUSDT_1m.csv` | 2026-07-30〜08-20 | 【事実】 |
| `backtest_data/candles_FX_BTC_JPY_{30d_20260820,31d_20260823,20260820}.csv*` | 2026-07-21〜08-23 | 【事実】 |
| `backtest_data/candles_BTC_JPY_20260820.csv` ほか JPY 現物 | 〜2026-08-20 の 30 日 | 【事実】 |
| `backtest_data/fx_usdjpy_1m_20260822.csv.gz` | 2023-12-18〜2026-08-21(USDJPY は P2-08 の出所に入っていたが、このファイルは台帳に無い) | 【事実】 |
| `backtest_data/regime_composite_20260901/raw/{binance_funding,binance_metrics,price_daily}.csv` | 〜2026-08-31(日次) | 【事実】 |
| `backtest_data/daily_btcusd_*_20260828.csv.gz` | 〜2026-08-28(日次) | 【事実】 |
| `backtest_data/binance_cm_o3c_20260913/`、`data/tardis/`(16 日)、`bitbank_*_monthly_first_days` | 2023-12-18 以降の部分 | 【事実】 |
| `paper_logs/tape/`(09-07 以降)・`spread_FX_BTC_JPY.csv`・`funding_rate_history.csv` | 判定区間の終わり(2026-09-06)より後 = 予定の「前向きのデータ」 | 【事実】 |

---

## B + B'. 経費の材料(取引所 × 制度 × 期間)

### B-1. bitFlyer FX_BTC_JPY

| 期間・制度 | 手数料 | スプレッド・板 | 資金調達 / SFD・スワップ | 経費を実データで当てられるか | 印・根拠 |
|---|---|---|---|---|---|
| 2015-11〜2024-03-27(Lightning FX) | 0%(`docs/OPERATIONS.md` 41 行「手数料0%・レバレッジ最大2倍は変更なし」。公式の料金表は bitflyer.com が WAF の 403 で原文未取得) | 1 分足に気配は無い。**向きつき約定の標本日**(tardis、毎月 1 日)が公開では 2019-09〜(この容器には 2023-07〜2024-03 の 9 日だけ)。テイカー買い/売りの出来高は 1 分足に 2017-07〜ある(推定器のコードは無い) | **SFD**(現物との乖離 5% 以上で 0.25〜2.00%、検索のスニペットだけ・原文未確認)。SFD を計算する道具は無い(`p2_08_run.py` 165 行は乖離 5% を診断で数えるだけ)。スワップ・建玉の手数料の有無は**未確認** | 標本日だけ(実効スプレッド)。SFD は FX と現物の 1 分足と料金表があれば計算できる【推定】が、料金表が未確認 | 【事実】/【未確認】DATA.md 75〜77 行、`docs/DATA/surveys/O3C_PROCUREMENT_SUPP_A_2026-09-12.md` 101 行 |
| 2024-03-28〜2026-08-19(Crypto CFD、封印の中) | 0%(同上、`config/constants.yaml` 34〜47 行。一次資料は未取得) | 標本日(tardis)の 2024-04〜2024-10 の 7 日はこの容器にある。その後は手元に無い。tardis には FX_BTC_JPY の quotes・板 5 段・25 段が 2019-08-30〜2026-10-02 まであるが、無料は毎月 1 日だけで、今日はこの環境から 403 | **資金調達: 公開 API で 2024-03-28 21:00 から全部取れる**(C-1)。手元には無い(`paper_logs/funding_rate_history.csv` は 2026-09-12〜) | 資金調達は取れる。スプレッドは毎月 1 日の標本日だけ(約定から推定)。最小発注は 2024-10-21 に 0.01 → 0.001 BTC | 【事実】R-1〜R-4・R-13・R-14 |
| 2026-08-20〜(tape・PC の記録) | 0% | 気配(ticker の変化・REST 5 秒)・約定・板 10 段(08-26〜)が連続 | 資金調達: PC の `record_funding_basis.py` が毎日追記(2026-09-12〜) | **実データで当てられる唯一の期間**。F3 の 2.16 bp はここの 08-20〜08-26 | 【事実】EXEC RESULT 5 行、R-22 |

- **既にある方法**: (a) `scripts/o3c_bitflyer_spread.py` = tardis の向きつき約定から「1 秒以内に隣り合う買いと売りの価格差」で実効スプレッドを測る(16 標本日 2023-07〜2024-10、清算直後の絶対値の中央値 2.004 bp)【事実】(同 docstring、`backtest_data/o3c_signal_value_20260921/spread/summary.json`)。(b) `scripts/measure_exec_floor.py` = 気配と板から床(E-a〜E-i)【事実】。(c) 1 分足の高値・安値からの推定器(Corwin–Schultz など)は**コードが無い**【事実】(src・scripts・docs を grep、R-26)。
- **API の約定は直近 31 日まで**(`getexecutions` の 400「limited to the most recent 31 days」、第 3 版 B-33)、**板の履歴の API は無い**(DATA.md 75 行)【事実】。

### B-2. 他の取引所(手元の材料)

| 取引所 | 手数料 | スプレッド・気配の履歴 | 資金調達 | 印・根拠 |
|---|---|---|---|---|
| bitFlyer 現物 | 0.15%(最低の段、`config/products.yaml` 4 行) | 1 分足のみ、PC で現物の ticker を 10 秒ごと(2026-08-27〜) | — | 【事実】 |
| GMO コイン・bitbank | `record_venues.py` docstring に「GMO ~5.3bps」「maker −0.02%」などの記述(出所は Round 22 の調査、一次資料は未確認) | 2026-08-27〜(PC) | — | 【未確認】 |
| Binance(現物・無期限) | リポジトリに手数料の定数の行は無い | 現物の気配の履歴は無い。無期限の bookTicker は公開アーカイブで 2024-03-30 はあり、2025-06-01 は無い | 無期限 2020-01〜(アーカイブ) | 【事実】`grep` で行なし、R-15 |
| BitMEX・Bybit・Coinbase・Upbit | リポジトリに手数料の行は無い | BitMEX の quote は公開アーカイブがあった(`mirror_bitmex.bat` は trade/quote/porl)が、手元の 1 秒足は約定から | — | 【未確認】 |
| USDJPY(GMO の FX) | 定数は `unverified`(`config/constants.yaml` 435〜454 行) | Dukascopy の 1 分足に ask_close があり、bid との差でスプレッドを出せる【推定】 | GMO のスワップの暦 `gmo_swap_usdjpy.csv` | 【事実】/【推定】 |

---

## D + D'. 場面の変数と外部データ(全期間)

列「判定区間」= 2025-12-12〜2026-09-06 を過去のアーカイブで覆えるか(今日叩いた結果)。「PC」= オーナーの PC で今記録しているか(既定ブランチの `deploy/start_all.bat`・`deploy/fetch_all.bat`・各台本の docstring)。「使える時刻」= その値をいつから使えるか(公表の遅れ)。

| 系列 | リポジトリに | 第 3 版 付録 B | 取れる全期間 | 判定区間 | PC で記録 | 使える時刻(公表の遅れ) | 印・根拠 |
|---|---|---|---|---|---|---|---|
| Binance USD-M 建玉・比率(metrics、5 分) | 日次の平均だけ(2021-01-01〜2026-08-31、`regime_composite`)+ 2026-08-04〜09-30(`paper_logs/binance_daily`) | B-6 | 2020-09-01〜(建玉の列 2022-01 で確認、比率 2022-06〜)。欠け 2023-11-19・2024-03-04・2024-04-15・2024-06-08 | **覆える**: 2025-12-12・2026-03-15・06-01・09-06 とも 200 | `fetch_binance_daily.py`(日次の平均、直近 30 日を毎日見直す) | 日 D の分は D+1 の 07:46 UTC に更新(2026-09-30 の分の Last-Modified = 2026-10-01 07:46:41 GMT)。10-01 の分は 01:19 UTC で 404 | 【事実】R-5〜R-7。API(`fapi`)はこの環境から 451、PC から**未確認** |
| Binance USD-M 資金調達率 | 日次(2020-01-01〜2026-08-31、`regime_composite`) | B-7 | 2020-01〜(月次) | **覆える**: 2025-12・2026-08・2026-09 とも 200 | 無し | 月次のアーカイブは月末の後【推定】(2026-09 の分は 10-02 に 200)。値そのものは決済の時刻に確定 | 【事実】R-8 |
| Coinbase BTC-USD 1 分足 | 日足だけ | B-14 | 2017-01-01 に返る(始まりは未特定) | **覆える**: 2026-03-01 00:00〜04:00 で 241 本 | 無し | 公開 API、その分の終わり | 【事実】R-10・R-16 |
| Upbit KRW-BTC 1 分足 | 無い | B-17 | 2017-12-31 に返る | **覆える**: to=2026-03-01 で 200 本 | 無し | 同上 | 【事実】R-11・R-17 |
| CFTC(CME BTC の建玉の内訳、週次) | 無い | B-8・B-29 | 2017-12-19〜 | **覆える**: 2025-12-02〜2026-09-22 の 43 回(BITCOIN - CME、MICRO、Coinbase の NANO PERP ほか) | 無し | 火曜の値を金曜に公表(約 3 日) | 【事実】R-11b |
| ETF のフロー(Farside、日次) | 無い | B-9(10-01 は 200、2024-01-11〜) | 2024-01-11〜 | 10-01 の取得では 2026-10-01 まであった。**今日は 403(Cloudflare の確認画面)** | 無し | 翌営業日【第 3 版の記述。未確認】 | 【事実】R-12 |
| DVOL(Deribit) | 無い(`data/deribit_dvol_1h.csv` は DATA.md にだけ) | B-4 | 2021-04 を確認(第 3 版 B-4。始まりは未特定)。1 時間足は全期間、1 分は直近 7 日(DATA.md) | **覆える**: 2026-03-01〜03-08 で 169 本(1 時間) | `record_oi.py` が実行ごとに最新の 1 分の値を 1 点(`oi_snapshots.csv`、2026-08-20〜) | その時間の終わり | 【事実】R-11c |
| ステーブルコインの供給(DefiLlama、USDT) | 無い | B-10 | 2017-11-29〜2026-10-02(3,230 日) | **覆える** | 無し | 日次。何時に確定するかは**未確認** | 【事実】R-11d |
| USDJPY | 1 分足 2017-08〜2026-08-21(C-2)、日次 ECB 2014-12〜 | B-16・B-31 | Dukascopy のティック: 2024-03 を確認(第 3 版)。今日は 2025-12-12・2026-02-16・2026-08-31 の時間ファイルが 200、2026-09-04 は 503(間欠。月は 0 始まり) | 1 分足は 2026-08-21 まで手元。残り 16 日は Dukascopy で**覆える**(間欠の 503 あり) | 日次 ECB(`fetch_binance_daily.py`)のみ。分足の記録は無い | ティックは即時。ECB は当日の参照値 | 【事実】R-18・R-20 |
| bitFlyer 資金調達率 | 2026-09-12〜(`paper_logs/funding_rate_history.csv`) | B-22(500 件) | **2024-03-28 21:00〜全部**(C-1) | **覆える** | `record_funding_basis.py`(毎日、直近 6 件) | 計算の時刻(calculation_date)に決まり、8 時間後に決済。何時に公開 API に出るかは**未確認** | 【事実】R-1〜R-4 |
| 局所ボラ・レンジ/トレンド・時刻・暦・制度 | 1 分足から計算 | — | 1 分足の全期間 | 1 分足が封印の中 | — | 過去の窓だけで計算 | 【事実】(場面表 §5-3 の定義) |
| 清算 | Binance COIN-M 2023-06-25〜2024-10-14、Gate 90 日、PC の 4 取引所 2026-09-09〜 | — | アーカイブは 2024-10-14 で配信停止 | **覆えない**(2026-09-09 より前は無い) | `record_liquidations.py`(常駐) | 受信の時刻 | 【事実】DATA.md、第 3 版 §5-1B |
| OKX 建玉・比率 | 2026-08-20〜(自前) | B-25 | API は 5 分 = 数日、1 日 = 180 日(2026-04-05〜) | 1 日の比率だけ 2026-04-05〜 | `record_oi.py`・`fetch_okx.py` | — | 【事実】 |

---

## E. 新しいバックテスト環境 `src/bot/bt/` の部品ごとの状態

| 部品 | 何があるか | 第 1 周の測定器の土台に使えるもの | 足りないもの | 印・根拠 |
|---|---|---|---|---|
| data(`data/`) | 唯一の読み口 `load`・流し読み `stream`。spec の厳格な宣言(未知の鍵は拒否)、時刻を int64 ns に、異常の報告と方針、全ファイルの sha256、許可リスト、封印の台帳の照合(パスと bytes)、`range_ns` で封印の境より前だけを読む(G-3・G-7 で直した) | bitFlyer・Binance の 1 分足、約定、気配、板、資金調達、清算を読む | (1) **事象の種類は trade/quote/bar/book/funding/liquidation の 6 つだけ**。建玉・比率・CFTC・ETF のフロー・DVOL・ステーブルコイン・USDJPY を載せる種類が無い。(2) **受け取れた時刻 = 行の時刻**(足は終わりの時刻)で、**公表の遅れ(available_at)を宣言する鍵は無い**。CFTC を行の日付で載せると約 3 日先を見る。(3) 読みが遅い(Binance 1 年 521,624 行で 47.6 秒、G-6 は一部だけ直した) | 【事実】`spec.py` docstring・`loader.py` 259〜314 行、`ENV_DEFECTS.md` 13・32 行 |
| core | 事象ごとに `received_time_ns`。戦略は受け取った事象しか見えない(`api.py` 8 行)。流れの名前 `Event.stream`(G-1) | 未来を見ない土台 | 外部の系列を「公表の時刻」で事象にする部品が data 側に無い | 【事実】`core/events.py` 18〜21 行 |
| fill | 段 0〜6(段 2 = 足で約定、段 5 = 待ち行列、段 6 = 衝撃)。段なしなら板を歩き、板が無ければ最後の約定 ± 宣言したスプレッド | 1 分足だけの履歴でも段 2 で回る | 時刻で変わるスプレッドを足に当てる段は無い | 【事実】`fill/spec.py` docstring |
| latency | 4 つの遅れ(feed・order・cancel・notice)を必須で宣言。定数・経験分布・一様 | 遅れを入れられる | 注文の応答遅延の実測は未(EXEC RESULT「P13 で記録中」) | 【事実】 |
| costs | `CostSchedule`: maker・taker の率と出所が必須。spread・funding・swap・fee_table は当たったら宣言が要る(既定値なし) | 手数料 0% を出所つきで宣言できる | (1) **spread は 1 つの定数**(期間・時刻・ボラで変えられない)。(2) **funding は FundingEvent の mark_price で払う**(`FundingRule.price = "event_mark"` だけ)。bitFlyer の履歴(`calculation_date, settlement_date, rate`)には mark_price が無いので、1 分足と結合して作る手間が要る。(3) SFD の模型は無い | 【事実】`costs/schedule.py` 136〜170 行 |
| orders | 商品・規則(既定なし)・故障の注入・Kill Switch(自動で戻らない)・発注の口 | 実際の bot と同じ規則を当てる | — | 【事実】 |
| portfolio | 円建ての証拠金口座。資金調達・スワップを別に計上、清算の規則、レバレッジ | CFD の 2 倍・円建てを扱える | — | 【事実】`account.py` docstring |
| validation | 暦日の分割と walk-forward、**パージとエンバーゴ、CPCV**、ブロック・ブートストラップ(UTC の日ごとなど)、MDE と 陰性/不明/陽性、deflated Sharpe・PBO(CSCV)、試行の台帳 ITER、封印の 4 門 | **L-536 の「大量データから学ぶ」の道具はそろっている**(CPCV・PBO・パージ) | 場面ごとの効果量と相関を出す道具(第 3 版 §5-2 の測定器)は無い | 【事実】`validation/__init__.py` |
| repro | 実行の記録、内容ハッシュの run id、2 回実行して一致を確かめる | 再現性 | — | 【事実】 |
| report | 1 取引あたり bp・分位・負の割合・markout・費用の内訳・DD | 経費前と経費後を並べられる | 場面ごとの表は無い | 【事実】 |
| vector | 足の高速経路。事象の経路とビット一致を試験で固定。規則は SMA の 2 本だけ | 速さ | 測定器としての規則は無い(第 3 版 §5-2 の指摘どおり) | 【事実】`vector/__init__.py` |
| pipeline | 宣言 → data → 銘柄ごとの core → 記録・指標・ダッシュボードを 1 回で | 実データの通し | 規模(数年 × 多系列)の速さは未測定【推定】 | 【事実】 |
| compat(項目 4 = 足の模型) | 場面集の規則(R-T・R-C・R-A・R-M・R-P・R-X・R-W・R-H・R-E・R-S・R-O・R-V)を core の上で。研究の台本の口(run_backtest など) | 旧の研究台本の口で回せる | 下の「項目 4」 | 【事実】`compat/barmodel.py` docstring |

**項目 4(足の模型)の状態**: 状態板では 2026-09-27 に「閉じた」(終わる条件 5 つを満たし、全試験 20598 passed、批評家 [止める] 0。`docs/OWNER_STATUS.md` 46 行)【事実】。閉じたあとに残っているもの:
- 閉じた報告の持ち越し(`item_4/round_3/REPORT_close_2026-09-27.md` §3): `rules`・`arithmetic` の引数と `model` の受け口を落とすこと(i4-c-04)、`entry_sides` と `allow_short=False` の同値の場面が無い(i4-c-06)、消した 12 場面の行の走らせ直し、PineForge(70)と比べていない【事実】。
- 閉じた後の段階 G(K1 の再現)で出た環境の欠陥 G-1〜G-7 のうち、**G-5(Bybit の 1 分足がディスクに無い)は直していない**、**G-6(読みが遅い)は一部だけ**直した。他は直した(`docs/PHASE2/K1/NEWENV_G/ENV_DEFECTS.md` 27〜33 行)【事実】。
- 状態板 39 行: 「これまでの全試験の実行は(封印・新鮮データの)ファイルを開いていた。どの実行で何行読んだかは未確認」【事実】。

---

## 第 1 周を始める前に必ず埋めるべき穴(全期間を使う前提、L-536)

前提: L-536 に従い、封印の短い区間ではなく手元の全期間で戦略の特性を学ぶ。そのとき「経費前の特性」は全期間で測れるが、**「経費後」は経費の材料がある期間でしか測れない**。これが全体の形である【推定:下の表からの帰結】。

| # | 穴 | なぜ全捨てになるか | 埋め方の候補(リードが決める) | 印 |
|---|---|---|---|---|
| H-1 | **bitFlyer の経費を全期間で当てる材料が無い**。気配の連続した履歴は 2026-08-20〜だけ。それより前は毎月 1 日の標本日だけ(この容器に 16 日。DATA.md の 85 日は別の容器にあったが、今どこかに残っているかは未確認)。1 分足の高値・安値からの推定器は無い | 経費の床を 2026-08 の 16 日の値で 10 年に当てると、制度・ボラ・出来高が違う時期の経費を誤る | (a) tardis の標本日 85 日を取り直す(今日は 403。PC から試す)、無料の quotes・板が標本日にあるかを確かめる、(b) 1 分足からの推定器を作り、標本日と 2026-08 以降の気配で較正する、(c) 経費を期間ごとの表にして costs に渡す | 【事実】B-1 |
| H-2 | **CFD 期間(892 日)が全部 P2-08 の封印の中**。封印の外の bitFlyer FX は全部 SFD の時代 | 今の制度の機構(資金調達 #39 など)を探索できない。旧制度で学んだものを今の制度に当てる | 封印の扱いはオーナーの判断(A-14)。L-536 の問いへの答えとして、P2-08 の封印を「全期間で学ぶ + 前向きで判定」に変えるかを決めてもらう | 【事実】A''-2 |
| H-3 | **SFD の模型が無く、料金表も未確認**(bitflyer.com が 403) | 旧制度の期間で、乖離が 5% を超えた時期の経費を落とす | 料金表を PC か検索で取る。FX と現物の 1 分足(どちらも手元)から乖離を計算する道具を作る | 【事実】/【未確認】 |
| H-4 | **封印の台帳に無い写し**(A''-3: lightchart の raw tar、Binance の raw zip・210 日、30・31 日の足、USDJPY 2023〜2026、regime_composite ほか) | 封印を残す決定をした場合、新しい環境の封印の門をすり抜けて境の先を読める【推定】。読んだ後では判定が汚れる | 封印を残すなら、台帳に足すか、許可リストの拒否に入れる。残さないなら不要 | 【事実】(すり抜けは【推定】) |
| H-5 | **データ層に外部の系列の入口が無い**(事象の種類 6 つ)、**公表の遅れ(available_at)を宣言する鍵が無い** | 場面表の変数(建玉・比率・CFTC・ETF・DVOL・ステーブルコイン・USDJPY)を載せられない。載せ方を手で書くと、CFTC の約 3 日・アーカイブの翌日を入れ忘れて未来を見る | 「参照の系列」の種類と、行ごとの使える時刻(行の時刻 + 宣言した遅れ、または記録した受信時刻)を data に足す。遅れの値は付録 R-6 のような実測で決める | 【事実】E |
| H-6 | costs の spread が 1 つの定数、funding が mark_price を要求 | H-1 の期間ごとの経費を渡せない。bitFlyer の資金調達を流すのに 1 分足との結合が要る | spread を時刻の表で渡せるようにする。funding の価格に「その時刻の足の終値」を選べるようにする | 【事実】E |
| H-7 | **bitFlyer の資金調達の履歴が手元に無い**(2026-09-12〜だけ) | 取れるのに無い | `from` で 6 ページ(見込み 2,752 件)を取って保存する。**判定区間を残す決定なら、取得した系列も境で切って台帳に載せるか、境より前の行だけを保存する**(そうしないと A''-3 と同じ穴を新しく作る) | 【事実】C-1 |
| H-8 | 場面表の外部データが手元に無い: Coinbase・Upbit の 1 分足、CFTC、ETF のフロー、DVOL、ステーブルコイン、Binance の 5 分の metrics(手元は日次の平均) | 第 3 版 §11 の「取得して場面表に入れる」が未着手 | 取得。ディスクの空きが 229 MB しか無いので、置き場の確保が先(下の H-12)。**判定区間を残す決定なら、取得した系列も境で切って台帳に載せるか、境より前の行だけを保存する**(H-7 と同じ) | 【事実】D |
| H-9 | Binance 現物 1 分足が 2026-08-31 で終わる(6 日足りない)。Bybit の 1 分足と Binance COIN-M aggTrades の本体がこの容器に無い | 取引所をまたぐ案(O-6・#28)が判定区間の終わりで欠ける | 公開アーカイブから取り足す(200 を確認済み) | 【事実】C-4、A-2 |
| H-10 | 旧制度の Lightning FX のスワップ・建玉の費用の有無が未確認 | 旧制度の保有の費用を落とす | 一次資料を PC から取る | 【未確認】 |
| H-11 | 測定器(場面ごとの効果量・頻度・相関・経費後)が無い。vector の規則は SMA 2 本 | 第 1 周の中身そのもの | 作る(第 3 版 §5-2)。validation の CPCV・パージ・ブロック・ブートストラップ・PBO を使う | 【事実】E |
| H-12 | **ディスクの空きが 229 MB**(`df -h`) | データを取れない。容器の作り直しで `data/`(gitignore)が消え、tardis の標本日などが失われる(09-21 に一度起きた、DATA.md 69 行) | 片付け、または置き場を決める | 【事実】`df -h`(冒頭) |
| H-13 | 試験の実行が封印・新鮮データのファイルを開いていた件(状態板 39 行「どの実行で何行読んだかは未確認」) | 封印を残す場合、汚れの範囲が分からない | 範囲を確かめる(封印を残す場合だけ) | 【事実】 |
| H-14 | DATA.md と実体の食い違い(A-4) | 台帳を真実として計画すると、無いデータ(Bybit・COIN-M aggTrades・Kraken・Deribit 1 時間)を前提にする | 台帳を実体に合わせる | 【事実】 |

---

## 付録: 外部への到達確認のコマンドと出力(この回、2026-10-02 UTC、この環境から)

UA は `trade-research/1.0 (research use)`。値(率・価格)は出していない。件数・日付の端・HTTP の結果だけ。

**R-1** `curl https://api.bitflyer.com/v1/getfundingrate?product_code=FX_BTC_JPY` → `HTTP 200 92B` `{"current_funding_rate":0.000100000000,"next_funding_rate_settledate":"2026-10-02T05:00:00"}`(判定区間より後の値)

**R-2** `.../v1/getfundingratehistory?product_code=FX_BTC_JPY&count=10000` → `HTTP 200 52673B`、`list 500`、鍵 `['calculation_date', 'settlement_date', 'rate']`、`min 2026-04-18T21:00:00 max 2026-10-02T05:00:00`

**R-3** 引数の試し(`count=10` に `before=` / `to_date=` / `end_date=` / `from_date=` / `offset=` / `page=` / `settlement_date=` / `date=`)→ 全部 `200 1054B n 10 min 2026-09-29T05:00:00 max 2026-10-02T05:00:00`(無視された)。公式文書 `https://lightning.bitflyer.com/docs?lang=en`(200、79,278 B)の記述: 「from : Start datetime. When specified, selects the oldest count records on or after this datetime … to : Upper bound for calculation_date … count : … Maximum 500」

**R-4** `from` と `to`:
```
200 52509B &count=500&from=2024-03-01T00:00:00 n 500 calc 2024-03-28T21:00:00 .. 2024-09-11T05:00:00 settle 2024-03-29T05:00:00 .. 2024-09-11T13:00:00
200 52509B &count=500&from=2024-03-28T00:00:00 n 500 calc 2024-03-28T21:00:00 .. 2024-09-11T05:00:00
200 52508B &count=500&to=2024-10-01T00:00:00 n 500 calc 2024-04-17T13:00:00 .. 2024-09-30T21:00:00
200 52509B &count=500&from=2023-01-01T00:00:00 n 500 calc 2024-03-28T21:00:00 .. 2024-09-11T05:00:00
200 52640B &count=500&from=2025-12-12T00:00:00 n 500 calc 2025-12-12T05:00:00 .. 2026-05-27T13:00:00
連続性: n 500 8時間刻みでない間隔 0 / settlement hours [5, 13, 21] / 予想件数(2024-03-29 05:00〜2026-10-02 05:00) 2752
```
取得したファイルは確認の後に消した。

**R-5** Binance USD-M metrics の日次 CHECKSUM: `2025-12-12 200 / 2026-03-15 200 / 2026-06-01 200 / 2026-09-06 200 / 2026-10-01 404`

**R-6** `2026-09-30 200`、`BTCUSDT-metrics-2026-09-30.zip` の `last-modified: Thu, 01 Oct 2026 07:46:41 GMT`

**R-7** R-5・R-6 の実行時刻 `Fri Oct 2 01:19:17 UTC 2026`

**R-8** Binance USD-M fundingRate 月次: `2025-12 200 / 2026-08 200 / 2026-09 200`

**R-9** Binance 現物 1 分足: `monthly 2026-08 200 / daily 2026-09-06 200`

**R-10** Coinbase `candles?granularity=60&start=2026-03-01T00:00:00Z&end=2026-03-01T04:00:00Z` → `200 本数 241 端 2026-03-01 00:00:00 2026-03-01 04:00:00`

**R-11** Upbit `candles/minutes/1?market=KRW-BTC&to=2026-03-01T00:00:00Z&count=200` → `200 本数 200 端 2026-02-28T20:40:00 2026-02-28T23:59:00`

**R-11b** CFTC `publicreporting.cftc.gov/resource/gpe5-46if.json`(BITCOIN を含む、2025-12-01 以降)→ `200 行 149`、`{'BITCOIN - CHICAGO MERCANTILE EXCHANGE': 43, 'MICRO BITCOIN - CHICAGO MERCANTILE EXCHANGE': 43, 'NANO BITCOIN PERP STYLE - COINBASE DERIVATIVES, LLC': 43, 'BITCOIN CASH PERP STYLE - COINBASE DERIVATIVES, LLC': 20}`、`日付 43 2025-12-02 2026-09-22`

**R-11c** Deribit `get_volatility_index_data?currency=BTC&start=2026-03-01&end=2026-03-08&resolution=3600` → `200 本数 169 2026-03-01 00:00:00 2026-03-08 00:00:00`

**R-11d** DefiLlama `stablecoincharts/all?stablecoin=1` → `200 日 3230 2017-11-29 2026-10-02`

**R-12** Farside `bitcoin-etf-flow-all-data/` → `403 5482B`、`server: cloudflare`、本文「Just a moment...」。UA を `Mozilla/5.0` にしても `403`。`/btc/` も `403`

**R-13** tardis `datasets.tardis.dev/v1/bitflyer/{trades,quotes,book_snapshot_5,book_snapshot_25,incremental_book_L2,derivative_ticker}/{2024/04/01,2025/06/01,2025/12/01}/FX_BTC_JPY.csv.gz` → 全部 `403`(`server: cloudflare`、「Attention Required! | Cloudflare」)。メタデータ `api.tardis.dev/v1/exchanges/bitflyer` → `200 88530B`、`{'id': 'FX_BTC_JPY', 'type': 'perpetual', 'dataTypes': ['trades', 'incremental_book_L2', 'quotes', 'book_snapshot_5', 'book_snapshot_25', 'book_ticker'], 'availableSince': '2019-08-30T00:00:00.000Z', 'availableTo': '2026-10-02T00:00:00.000Z'}`。プロキシの状態は `enabled: true`(プロキシ側の拒否ではない)

**R-14** `ls data/tardis/bitflyer_FX_BTC_JPY_trades/` → `FX_BTC_JPY_20230701 … FX_BTC_JPY_20241001`(16 本)+ `MD5SUMS`・`_fetch_summary.json`

**R-15** Binance: `um 1m klines 2019-12 404 / 2020-01 200`、`cm 1m klines BTCUSD_PERP 2020-08 200 / 2020-09 200`、`um bookTicker 2024-03-30 200 / 2025-06-01 404`

**R-16** Coinbase 1 分足: `2015-01-15 200 本数 0`、`2017-01-01 200 本数 53`

**R-17** Upbit 1 分足: `to=2018-01-01 200 本数 5 ['2017-12-31T23:59:00']`、`to=2019-06-01 200 本数 5`

**R-18** Dukascopy USDJPY(月は 0 始まり): 1 回目 `2026/01/16/10h 503 107B`・`2026/07/31/10h 503`・`2026/08/01/10h 503` → 第 3 版 B-16 と同じ `2024/03/01/00h 200 28339B` → 2 回目 `2026/01/16/10h 200 11556B`・`2026/07/31/10h 200 17080B`・`2025/11/12/10h 200 17662B`・`2026/08/04/10h 503 107B`(間欠)

**リポジトリの中のコマンド(抜粋)**

**R-20** `zcat backtest_data/fx_usdjpy_1m_20260822.csv.gz | cut -d, -f1 | cut -c1-7 | uniq -c` → `2023-01:38880 … 2026-07:38880 2026-08:25920`、端 `2023-01-01 00:00:00+00:00` / `2026-08-21 23:59:00+00:00`。列 `timestamp,open,high,low,close,volume,ask_close`

**R-21** 時刻の列だけ: `binance_BTCUSDT_1m.csv: 2026-07-30 02:26 〜 2026-08-20 02:25`、`candles_FX_BTC_JPY_31d_20260823.csv.gz: 2026-07-23 12:09 〜 2026-08-23 12:25`、`candles_FX_BTC_JPY_30d_20260820.csv: 2026-07-21 08:17 〜 2026-08-20 08:22`、`daily_btcusd_bitstamp 2011-08-22〜2026-08-28 / coinbase 2015-07-20〜 / yahoo 2014-09-17〜`、`regime_composite raw binance_funding 2020-01-01〜2026-08-31 / binance_metrics 2021-01-01〜2026-08-31`

**R-22** `git ls-tree --name-only origin/claude/bitflyer-trading-bot-hhxxaf paper_logs/tape/` → 日付 `20260820`〜`20261001`、`board_top10 37 / board_top5 7 / executions 43 / ticker 43`。`paper_logs/funding_rate_history.csv` の決済日の端: 作業ブランチ `2026-09-12T13:00:00`〜`2026-09-19T13:00:00`(25 行)、既定ブランチ `2026-09-12T13:00:00`〜`2026-10-02T05:00:00`(58 行)。封印の台帳を `grep -l 'funding_rate_history\|basis_log\|spread_FX_BTC_JPY'` → 該当なし(exit 1)

**R-23** python の日付計算: `bitFlyer FX 1分足 全 3935 日 / 封印 993 日 = 25.2 %`、`bitFlyer 現物 全 4053 / 993 = 24.5 %`、`Binance 現物 全 3302 / 988 = 29.9 %`、`CFD 期間 892`、`Lightning FX 期間(封印前) 2015-11-28〜2023-12-17 2942`、`封印内の旧制度 101`

**R-24** DATA.md と `git ls-files backtest_data` の突き合わせ(名前の grep)、DATA.md のパスの `ls`(本文 A-4 の一覧がその出力)

**R-25** 封印の台帳の要約(python で SEALED.json を読み、ディレクトリごとに件数・最初・最後・境)。P2-08: `bitflyer_lightchart_FX_BTC_JPY_1m_20260906 10 2017-01-01〜2026-09-06 ['2023-12-18']`、`binance_BTCUSDT_1m_20170801_20231231 7`、`binance_BTCUSDT_1m_20240101_20260831 1`、`fx_btc_jpy_1m_continuous_20260906 1`、`backtest_data(executions_FX_BTC_JPY_31d_20260823) 1`、`fx_usdjpy_1m_20170801_20221231 1`、`bitflyer_lightchart_BTC_JPY_1m_20260906 12`。台帳に無い: `binance_BTCUSDT_1m_210d_20260820.csv.gz`・`binance_BTCUSDT_1m.csv`・`candles_FX_BTC_JPY_{31d_20260823,30d_20260820,20260820}`・`candles_BTC_JPY_20260820.csv`・`fx_usdjpy_1m_20260822.csv.gz`・`regime_composite_20260901/raw/price_daily.csv`・`daily_btcusd_coinbase_20260828.csv.gz`

**R-26** `Grep "effective.?spread|実効スプレッド|corwin|abdi|roll_spread|roll estimator|spread_from_trades|tardis"`(src・scripts・docs の .py/.md)→ 43 ファイル。1 分足から推定する道具は無く、約定から測る `scripts/o3c_bitflyer_spread.py` だけ
