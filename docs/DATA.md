# データ登録簿(単一の台帳)

`research-squad` skill(`.claude/skills/research-squad/SKILL.md`)の `procure` モードが
書き込む先。**「私たちが何を持っているか / どこにあるか」の台帳**であり、
「何を見て何を選んだか」は `docs/DATA_CONSUMPTION_LOG.md`(別文書、削除禁止)が別に持つ。
両方確認してから新しい研究単位を始めること。

作成 2026-09-11(L-107/L-108、`research-squad` skill の一部として)。

## 列の意味

| 列 | 意味 |
|---|---|
| 資産 | データの内容(商品・粒度・種別) |
| 所在 | 実体のパス、または外部の URL・API |
| 範囲 | 期間・行数など、実際にディスク上で確認できる範囲 |
| 状態 | 下表 |
| 最終確認日 | この行の内容を最後に実測で確認した日(YYYY-MM-DD) |
| プローブのログ | 到達性を確認した生ログのパス(無ければ「—」。ただし「試行して不可」では必須) |
| 使った単位 | この資産を実際に読んだ研究単位の名(`docs/DATA_CONSUMPTION_LOG.md` の行と対応)。未使用なら「未使用」 |

## 状態の値

| 値 | 意味 |
|---|---|
| **取得済** | この環境のディスク上に実体があることを `ls`(または同等の列挙)で確認した |
| **PC に未共有の可能性** | オーナー PC 側で取得された記録があるが、この環境のディスクには実体が見当たらない(`docs/OWNER_STATUS.md` 参照。share_logs 待ちの可能性) |
| **未試行** | 入手経路はあるが、まだ到達確認(プローブ)も取得もしていない |
| **試行して不可(範囲・方法)** | 到達を試みて失敗した。**この値は「範囲・方法」のセル(範囲列 or 資産列に方法込みで明記)とプローブのログへのパスが無ければ使ってはならない**(CLAUDE.md §5.2、「取れない」の書き方) |
| **未確認** | 文書中に言及はあるが、本台帳作成時点でディスクの実体確認(`ls`)を行っていない。取得済への昇格には再確認が要る |

**「取れない」は、範囲・方法のセルとプローブのログパスが埋まっていない限り書いてはならない。**

---

## 1. bitFlyer FX_BTC_JPY(標的商品・自市場)

| 資産 | 所在 | 範囲 | 状態 | 最終確認日 | プローブのログ | 使った単位 |
|---|---|---|---|---|---|---|
| FX_BTC_JPY 1分足チャート(lightchart) | `backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/` | 2015-11〜2026-09 | 取得済 | 2026-09-11 | — | K1 フレッシュ確認(L-090)、K1 取引所横断 段階1/2(L-093/L-095) |
| BTC_JPY 1分足チャート(lightchart、現物) | `backtest_data/bitflyer_lightchart_BTC_JPY_1m_20260906/` | 2026-09-06 時点スナップショット | 取得済 | 2026-09-11 | — | 未使用 |
| 板・ticker・約定(1分粒度、監査用) | `backtest_data/auto_bitflyer_executions_20260905/` | 2026-08-20〜09-05 | 取得済 | 2026-09-11 | — | ④-1 経費の床(L-098、`EXEC_FLOOR_PREREG.md`) |
| 板 top5(高頻度) | `data/tape/board_top5_*.csv.gz`, `paper_logs/tape/board_top5_*.csv.gz` | 2026-08-20〜08-27 | 取得済 | 2026-09-11 | — | 嵐予兆・秒スケール研究 |
| 約定・ticker(高頻度テープ) | `data/tape/executions_*.csv.gz`, `data/tape/ticker_*.csv.gz` | 2026-08-20〜08-27 | 取得済 | 2026-09-11 | — | 同上 |
| WS 生ログ(jsonl) | `data/ws/FX_BTC_JPY_*.jsonl.gz` | 2026-08-20 の複数スロット | 取得済 | 2026-09-11 | — | 未使用 |
| **WS 生ログ(オーナー PC、未共有)** | オーナー PC `data\ws\FX_BTC_JPY_*.jsonl.gz`(板・ticker・約定の生 WS。共有されるのは抽出後の `data\tape\*` のみ) | 2026-08-20 頃〜現在。**保持日数はこの環境から未確認**(P11 手順 1 の `dir data\ws` で判明) | **PC に未共有の可能性** | 2026-09-11 | 手順 P11(板 10 段への抽出 → `share_logs.bat` で共有。生ログ自体は共有しない) | ④-1 経費の床の再実行(`docs/PHASE2/EXEC/RESULT.md` §1.6、L-098) |
| 約定 31日ロングテープ(us、tardis形式) | `backtest_data/bitflyer_executions_us_20260723_20260906/` | 2026-07-23〜09-06 | 取得済 | 2026-09-11 | — | 未使用 |
| tardis 形式 約定 | `data/tardis/bitflyer_FX_BTC_JPY_trades/` | 詳細未確認(ディレクトリ存在のみ確認) | 取得済 | 2026-09-11 | — | 未使用 |
| 約定 31日スナップショット(2本) | `backtest_data/candles_FX_BTC_JPY_31d_20260823.csv.gz`, `backtest_data/executions_FX_BTC_JPY_31d_20260823.csv.gz` | 〜2026-08-23 | 取得済 | 2026-09-11 | — | 未使用 |
| 約定 31日スナップショット(2026-09-08) | `backtest_data/executions_FX_BTC_JPY_31d_20260908/` | 〜2026-09-08 | 取得済 | 2026-09-11 | — | 未使用(31日制限の前倒し回避のみ) |
| 継続ローリング(生、日次更新) | `data/candles_FX_BTC_JPY.csv`, `data/executions_FX_BTC_JPY.csv`, `data/flow_FX_BTC_JPY.csv`, `data/spread_FX_BTC_JPY.csv` | 最新は 2026-09-08 更新 | 取得済 | 2026-09-11 | — | 執行校正・マチルダ系構成選択(重度消費、`DATA_CONSUMPTION_LOG.md` §1) |
| 1分足 30日/継続結合 | `backtest_data/candles_FX_BTC_JPY_30d_20260820.csv`, `backtest_data/fx_btc_jpy_1m_continuous_20260906/` | 〜2026-08-20 / 2026-09-06 時点結合 | 取得済 | 2026-09-11 | — | 面探索(重度消費) |
| 清算・強制決済(losscut) 履歴 | — | — | **試行して不可(bitFlyer は個別losscutの公開履歴APIを提供しない。方法: 本 pilot では未探索。JPX §4 の一次資料確認が必要)** | 2026-09-11 | `docs/DATA/probes/20260911_crypto_cfd_board_liq_funding_basis.log` | 未使用 |
| 板の深さの履歴(ヒストリカル) | — | 現在の板スナップショットのみ `https://api.bitflyer.com/v1/board` で取得可(履歴保存 API は無い) | **試行して不可(板の履歴配信APIが存在しない。現在値のみ HTTP 200 で確認。方法: GET、この環境から実測)** | 2026-09-11 | `docs/DATA/probes/20260911_crypto_cfd_board_liq_funding_basis.log` | 未使用(自前スナップショット化が必要) |

## 2. 海外暗号資産(無期限・先物)

| 資産 | 所在 | 範囲 | 状態 | 最終確認日 | プローブのログ | 使った単位 |
|---|---|---|---|---|---|---|
| Binance BTCUSDT 現物 1分足(積み上げ) | `data/binance_BTCUSDT_1m.csv`, `data/binance_BTCUSDT_1m_full.csv`, `backtest_data/binance_BTCUSDT_1m_210d_20260820.csv.gz`, `backtest_data/binance_BTCUSDT_1m_20170801_20231231/`, `backtest_data/binance_BTCUSDT_1m_20240101_20260831/` | 2017-08〜2026-08 | 取得済 | 2026-09-11 | — | K1 取引所横断 段階1(L-093)、面探索多数(重度消費) |
| Binance BTCUSDT 1秒足 / aggTrades | `backtest_data/binance_BTCUSDT_1s_20260723_20260906/`, `backtest_data/binance_BTCUSDT_aggTrades_20260723_20260906/`, `backtest_data/binance_um_BTCUSDT_aggTrades_20260723_20260906/`, `backtest_data/binance_BTCUSDT_aggTrades_tardis_days/` | 2026-07-23〜09-06 | 取得済 | 2026-09-11 | — | P2-08b 用(未読み) |
| Binance BTCUSDT 1秒足(高頻度サンプル) | `data/binance_BTCUSDT_1s_hi1.csv` 等 4 本 + `_today.csv` | 個別サンプル日 | 取得済 | 2026-09-11 | — | 未使用 |
| Binance XRPUSDT 1分/1日/4時間足 | `data/binance_XRPUSDT_*.csv`, `backtest_data/binance_XRPUSDT_*.csv` | 複数粒度 | 取得済 | 2026-09-11 | — | 未使用 |
| Binance 資金調達率・板深さ・清算(このデータセンターから) | `https://fapi.binance.com/fapi/v1/*` | — | **試行して不可(この環境から HTTP 451: "restricted location", 現物 `api.binance.com` も同様。方法: GET、この環境の egress IP から実測)** | 2026-09-11 | `docs/DATA/probes/20260911_crypto_cfd_board_liq_funding_basis.log` | 未使用 |
| Bybit BTCUSDT 無期限 1分足 | `backtest_data/bybit_BTCUSDT_1m_20260910/` | 2022-01-01〜2026-08-31 | 取得済 | 2026-09-11 | — | K1 取引所横断 段階2(L-095) |
| Bybit 現物/無期限 到達確認サンプル(2日分) | `backtest_data/bybit_reachability_check_20260906/` | 2026-08-01〜08-02(現物) | 取得済 | 2026-09-11 | — | 到達確認のみ(P2-08b 対照候補) |
| Bybit REST API(資金調達率・板・清算) | `https://api.bybit.com/v5/*` | — | **試行して不可(この環境から HTTP 403: CloudFront の国別ブロック。方法: GET、この環境の egress IP から実測)** | 2026-09-11 | `docs/DATA/probes/20260911_crypto_cfd_board_liq_funding_basis.log` | 未使用 |
| Bybit 静的アーカイブ(`public.bybit.com`、約定のみ) | `https://public.bybit.com/trading/BTCUSDT/`, `https://public.bybit.com/spot/BTCUSDT/` | ディレクトリ一覧まで到達確認(ダウンロードは未実施) | 未試行(到達性のみ確認) | 2026-09-11 | `docs/DATA/probes/20260911_crypto_cfd_board_liq_funding_basis.log` | 未使用。**api.bybit.com とは別ホストで地域ブロックを受けない**(板・清算・資金調達率は無く約定のみ) |
| OKX 資金調達率(現在値・履歴) | `https://www.okx.com/api/v5/public/funding-rate*` | 直近数件を実測(全履歴はページングで別途取得が必要) | 未試行(到達性は確認済み、全量取得は未実施) | 2026-09-11 | `docs/DATA/probes/20260911_crypto_cfd_board_liq_funding_basis.log` | 未使用 |
| OKX 基差(mark/index の履歴、basisの代理) | `https://www.okx.com/api/v5/market/{mark-price-candles,index-candles}` | 直近数件を実測(1H足。遡れる期間の上限は未確認) | 未試行(到達性は確認済み、遡及可能範囲は未確認) | 2026-09-11 | `docs/DATA/probes/20260911_crypto_cfd_board_liq_funding_basis.log` | 未使用 |
| OKX 板の深さ(現在値のみ) | `https://www.okx.com/api/v5/market/books` | 現在のスナップショットのみ(履歴API無し) | **試行して不可(履歴配信APIが存在しない。現在値は HTTP 200 で到達確認済み。方法: GET、この環境から実測)** | 2026-09-11 | `docs/DATA/probes/20260911_crypto_cfd_board_liq_funding_basis.log` | 未使用(自前スナップショット化が必要) |
| OKX 建玉(OI)・L/S比 スナップショット(自前記録) | `backtest_data/auto_okx_open_interest_5m_20260905/`(同 09-06〜09-08 も同様)、`backtest_data/auto_okx_long_short_ratio_20260905/`、`data/okx_btc_oi_*.csv`、`data/okx_btc_lsratio_*.csv` | 2026-08-23 以降、5分/1時間粒度で継続記録 | 取得済 | 2026-09-11 | — | 未使用(自前構築中の履歴、判定はまだ) |
| Coinalyze(清算・OIの集計値、鍵必須) | `https://api.coinalyze.net/v1/*` | — | **試行して不可(HTTP 401、API キー必須。方法: GET、この環境から実測)** | 2026-09-11 | `docs/DATA/probes/20260911_crypto_cfd_board_liq_funding_basis.log` | 未使用 |
| Gate.io 個別清算約定(90日、鍵不要) | `backtest_data/gate_liquidations_20260908/BTC_USDT.jsonl.gz` | 2026-06-10〜09-08(2,160時間、79,183件、欠測167時間) | 取得済 | 2026-09-11 | `docs/DATA/probes/20260911_crypto_cfd_board_liq_funding_basis.log`(再確認、既存台帳は L-030) | P8(清算研究、進行中) |
| BitMEX XBTUSD 1秒足(取引所閉鎖前の保全) | `backtest_data/bitmex_trade_1s_XBTUSD/` | 2017〜2021(1,826 日、7,874 万本) | 取得済。**2017〜2019 は K1 の探索区間として全読(第 1〜14 部)、2020〜2021 は封印として 2026-09-10 に一度だけ開封(L-085、第 15 部)。この設計での再利用は不可** | 2026-09-11 | `docs/DATA_CONSUMPTION_LOG.md` | K1 全部(第 1〜15 部) |
| Kraken XBTUSD 1分足 | `data/kraken_XBTUSD_1m.csv` | 単一ファイル | 取得済 | 2026-09-11 | — | 未使用 |
| Deribit DVOL(ボラ指数) | `data/deribit_dvol_1h.csv`, `data/deribit_dvol_1m_7d.csv` | 1時間粒度(全期間)/1分粒度(直近7日) | 取得済 | 2026-09-11 | — | 未使用 |
| 現物 BTC/ETH 日足(Bitstamp/Coinbase/Yahoo、複数取引所横断) | `backtest_data/daily_btcusd_*.csv.gz`, `backtest_data/daily_ethusd_*.csv.gz` | 〜2026-08-28 | 取得済 | 2026-09-11 | — | 未使用 |
| 資金調達率・基差(自前結合、粒度不明) | `data/funding_rate_history.csv`, `data/basis_1m.csv` | 単一ファイル、範囲未確認 | 取得済(ファイル存在のみ確認。列・範囲は未検査) | 2026-09-11 | — | 未使用 |
| Tardis.dev(第三者・有料、メタデータのみ確認) | `https://api.tardis.dev/v1/exchanges/binance-futures` | 取引所メタデータ(1件)のみ取得。実データは未取得・鍵要 | 未試行(メタデータ到達のみ確認、本体データは有料) | 2026-09-11 | `docs/DATA/probes/20260911_crypto_cfd_board_liq_funding_basis.log` | 未使用 |
| CryptoDataDownload(第三者・無料、OHLCVのみ想定) | `https://www.cryptodatadownload.com/data/binance/` | トップページのみ確認(板深さ・清算・資金調達率の提供は未確認) | 未試行(トップページ到達のみ確認、板・清算・資金調達率の有無は個別ページ未確認) | 2026-09-11 | `docs/DATA/probes/20260911_crypto_cfd_board_liq_funding_basis.log` | 未使用 |
| ベニュー横断調査(サーベイ文書) | `backtest_data/venue_survey_20260827/` | — | 取得済 | 2026-09-11 | — | 未使用 |

## 3. 国内暗号資産(bitFlyer 以外)

| 資産 | 所在 | 範囲 | 状態 | 最終確認日 | プローブのログ | 使った単位 |
|---|---|---|---|---|---|---|
| bitFlyer BTC_JPY / ETH_JPY / XRP_JPY(candles/executions/flow) | `data/candles_{BTC,ETH,XRP}_JPY.csv` ほか | 〜2026-08-20 | 取得済 | 2026-09-11 | — | 未使用 |
| bitbank BTC/XRP JPY | `backtest_data/bitbank_btc_jpy_transactions_monthly_first_days/`, `data/bitbank_xrp_jpy_1m.csv`, `backtest_data/bitbank_xrp_jpy_1m.csv` | 各種 | 取得済 | 2026-09-11 | — | 未使用 |
| GMO・bitbank 横断(quotes/trades) | `backtest_data/auto_venues_20260905/` | 2026-08-27〜09-05 | 取得済 | 2026-09-11 | — | 未使用 |

## 4. FX(USD/JPY)

| 資産 | 所在 | 範囲 | 状態 | 最終確認日 | プローブのログ | 使った単位 |
|---|---|---|---|---|---|---|
| USD/JPY 1分足(3.5年) | `backtest_data/fx_usdjpy_1m_20260822.csv.gz` | 〜2026-08-22、約3.5年 | 取得済 | 2026-09-11 | — | FX系の全研究(重度消費) |
| USD/JPY 1分足(拡張、2017-2022) | `backtest_data/fx_usdjpy_1m_20170801_20221231/` | 2017-08〜2022-12 | 取得済 | 2026-09-11 | — | 未使用 |
| FX イベントティック(2005-2014 / 2015-2026) | `backtest_data/fx_event_ticks_2005_2014/`, `backtest_data/fx_event_ticks_2015_2026/` | 各期間 | 取得済 | 2026-09-11 | — | 未使用 |
| FX ファンダメンタルズ・カレンダー | `backtest_data/fx_fundamentals_20260822/`, `data/fx/calendar.csv`, `data/fx/calendar_cache*`, `data/fx/events/` | 各種 | 取得済 | 2026-09-11 | — | 未使用 |
| FRED 系列(政策金利・スワップ) | `backtest_data/fred_*.csv` | 各系列 | 取得済 | 2026-09-11 | — | 未使用 |
| GMO USD/JPY スワップ | `backtest_data/gmo_swap_usdjpy.csv` | 単一ファイル | 取得済 | 2026-09-11 | — | 未使用 |

## 5. JPX / 国内証券

| 資産 | 所在 | 範囲 | 状態 | 最終確認日 | プローブのログ | 使った単位 |
|---|---|---|---|---|---|---|
| 日経225先物 225Labo 日足 | `backtest_data/n225f_225labo_20260828/` | 2020-12-21〜(2026-08-28版) | 取得済 | 2026-09-11 | — | オーバーナイト系(重度消費) |
| TOPIX先物/miniTOPIX先物 225Labo | `backtest_data/topixf_225labo_20260907/`, `backtest_data/mini_topixf_225labo_20260907/` | 日足2001-01-04〜/2008-06-16〜、1分足2025-12-30〜 | 取得済 | 2026-09-11 | — | 未使用 |
| ETF 日足(1343/1321/1348 等) | `backtest_data/audit_fetch_etf_units_20260906/`, `backtest_data/jpx_etf_daily_20260905/`, `backtest_data/jpx_etf_daily_20260906_topix_alt/` | 1343: 2021-04-13〜 / 1321・1348: 2022-03-05〜 | 取得済 | 2026-09-11 | — | 消費済み(§3) |
| ETF 代替候補調査 | `backtest_data/audit_fetch_etf_alternatives_20260906/` | — | 取得済 | 2026-09-11 | — | 未使用 |
| REIT / ONR(オーバーナイトリターン) | `backtest_data/reit_onr_20260904/`, `data/onr/`, `data/paper_onr/` | manifest記載範囲 | 取得済 | 2026-09-11 | — | ONR研究 |
| 優待(yutai)ユニバース | `backtest_data/yutai_20260904/` | 900銘柄、2026-09-04時点 | 取得済 | 2026-09-11 | — | サーベイのみ(判定なし) |
| 日本ファクター | `backtest_data/jp_factors_20260905/` | — | 取得済 | 2026-09-11 | — | 未使用 |
| 日経225イベント | `backtest_data/nk225_events_20260904/` | — | 取得済 | 2026-09-11 | — | 未使用 |
| JPX デリバティブ日報(生 zip) | `backtest_data/jpx_daily_report_json_20260908/` | 2026-01〜 | 取得済 | 2026-09-11 | — | 未使用(保存開始のみ) |
| JPX 日次セッション | `data/jpx_daily/nk225_sessions.csv` | — | 取得済 | 2026-09-11 | — | 未使用 |
| JPX Tick 調査(監査) | `backtest_data/audit_fetch_JPX_tick_20260906/`, `backtest_data/audit_fetch_JPX_n225f_months_20260906/`, `backtest_data/audit_fetch_1306_split_20260906/`, `backtest_data/audit_fetch_H_20260905/`, `backtest_data/audit_fetch_micro_fee_20260906/` | — | 取得済 | 2026-09-11 | — | 監査記録のみ |
| kabuステーション API(実口座・実発注) | オーナーPC(未接続) | — | **PC に未共有の可能性**(前提: 先物OP口座の承認・入金待ち) | 2026-09-11 | — | 未使用(`docs/OWNER_STATUS.md` 参照) |

## 6. 研究基盤(合成データ・監査用フィクスチャ)

**以下は実データではない。** 固定シードで生成した QA 用の既知解パケット(`scripts/qa/make_known_answer*.py`)。
盲検監査の較正専用で、相場についての主張には使えない。

| 資産 | 所在 | 状態 | 最終確認日 | 使った単位 |
|---|---|---|---|---|
| QA既知解パケット群(通常・maker・maker3各世代・steer) | `backtest_data/qa_known_answer*_2026090[5-7]*/` | 取得済(合成) | 2026-09-11 | 盲検監査の較正 |
| QAパイプライン日次/taker | `backtest_data/qa_pipeline_daily_2026090[5-6]/`, `backtest_data/qa_pipeline_taker_20260905/` | 取得済(合成) | 2026-09-11 | 同上 |
| 板往復イベント(round trip) | `backtest_data/board_round_20260904/` | 取得済 | 2026-09-11 | 未使用 |
| ストーム/バーストイベント抽出 | `backtest_data/storm_events_20260820/`, `backtest_data/burst_events_20260820/`, `data/storm_events/`, `data/burst_events/` | 取得済 | 2026-09-11 | 嵐予兆研究(重度消費) |
| レジーム複合特徴 | `backtest_data/regime_composite_20260901/` | 取得済 | 2026-09-11 | 未使用 |
| フェーズ2 走行結果・封印台帳 | `backtest_data/phase2_runs/`, `backtest_data/phase2_sealed/` | 取得済(結果物、生データではない) | 2026-09-11 | K1 各段(`DATA_CONSUMPTION_LOG.md` §4) |
| PC 時計・レイテンシ | `data/latency/ws_vm.csv` | 取得済 | 2026-09-11 | 未使用 |
| アテンション指標 | `data/attention/attention.csv` | 取得済 | 2026-09-11 | 未使用 |
| ON1/ONR ペーパー台帳 | `data/paper_on1/ledger.csv`, `data/paper_onr/ledger.csv`, `data/paper_onr/status.json` | 取得済 | 2026-09-11 | 実行記録(研究データではない) |

## 7. pilot procure の結果(2026-09-11、この skill の初回実行)

需要: 「日本の暗号資産CFD(bitFlyer FX_BTC_JPY)と海外無期限(Bybit/Binance/OKX)の公開データ:
板の深さ・清算・資金調達率・基差 の履歴」。行は上の §1・§2 に統合済み(**試行して不可**および
**未試行**の行を参照)。プローブの生ログ: `docs/DATA/probes/20260911_crypto_cfd_board_liq_funding_basis.log`
(17件、方法・HTTPコード・バイト数・先頭200文字・タイムスタンプ付き)。

**総括(推定)**: 板の深さ・清算の**履歴**を無料公開APIから直接取れる経路は今回確認した範囲では無い
(bitFlyer・OKX とも現在値スナップショットのみ)。資金調達率・基差は OKX が鍵無しで履歴付きで取れる
(遡及可能な期間は未確認)。Binance は API 全体がこの環境からは地域制限(HTTP 451)、Bybit の REST API も
地域制限(HTTP 403、ただし静的アーカイブ `public.bybit.com` は別ホストで到達可能・約定のみ)。
**この推定はこの環境の egress からの到達性であり、オーナー PC からの到達性は別に確認が要る**
(`procure` の第2経路)。
