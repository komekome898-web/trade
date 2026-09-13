# データ登録簿(単一の台帳)

`research-squad` skill(`.claude/skills/research-squad/SKILL.md`)の `procure` モードが
書き込む先。**「私たちが何を持っているか / どこにあるか」の台帳**であり、
「何を見て何を選んだか」は `docs/DATA_CONSUMPTION_LOG.md`(別文書、削除禁止)が別に持つ。
両方確認してから新しい研究単位を始めること。

作成 2026-09-11(L-107/L-108、`research-squad` skill の一部として)。

## 0. 守る仕組み(自動スナップショット・バイト完全一致の検証・取り込み台帳)

データ QA 完了 2026-09-06(11 項目)。

| 部品 | 役割 | 所在 |
|---|---|---|
| 保持期間の定数 | 各ソースの上限を `measured` + `verified_on` つきで一元管理。ここが唯一の真実 | `config/constants.yaml: data_retention.*` |
| 自動スナップショット | 各ソースを**上限の半分以下の間隔**で `backtest_data/auto_<source>_<YYYYMMDD>/` へコピー。定数と間隔の整合を起動時に検証し、緩すぎる設定は失敗させる | `scripts/retention_snapshot.py`(宣言的な `SOURCES` 表) |
| 実行 | オーナー PC のタスクスケジューラ → `fetch_all.bat` で毎日実行 | `deploy/fetch_all.bat` |
| 共有 | `share_logs.bat` が `backtest_data/auto_*` を commit | `deploy/share_logs.bat` |
| 受領台帳(intake ledger) | オーナーが送るログ・外部取得・スナップショットは全て 1 行(時刻・経路・ファイル・行数・期間・MD5・送付者)で記録。`share_logs.bat` と `fetch_*` が自動追記 | `data/INTAKE.jsonl`、`scripts/intake_ledger.py` |
| 単一の真実 | 研究側は必ず `paper_logs/`(共有)を読む。`shared_or_local`/`shared_or_local_dir` を全読み手に強制し、ローカルが新しい場合のみローカルを使う | `src/bot/monitoring/gates.py: shared_or_local` / `shared_or_local_dir` |
| スナップショット義務 | 判定・報告に使ったデータは `backtest_data/<name>_<date>/` に MD5 付きで保存してからでなければ結論を書けない(消失は「未検証」への格下げ規則) | `backtest_data/` |
| 品質ゲート | 取り込み時の自動チェック(重複・欠測・交差板・メンテ窓・極端リターン・列の型と意味の宣言) | `scripts/data_quality.py`、`schema/*.json` |
| 出所ファイル | 定数は値・単位・`source_type`(primary_document/measured/assumed)・一次資料 URL・確認日を併記する。値だけの定数を禁止。`assumed`/`deprecated` な定数を判定文脈で使おうとすると例外 | `config/constants.yaml`、`src/bot/constants.py: require_source()` |
| バイト完全一致の検証 | `backtest_data/` の MD5 不一致を検査する。git の autocrlf による改行コード変換は LF/CRLF 正規化後の再判定で `line_ending_only`(実質的な内容変更ではない)として分離し、それでも一致しないものだけ `mismatch` として残す。`.gitattributes` で `backtest_data/**`・`paper_logs/**` を `-text` 指定し、以後どの OS でチェックアウトしても改行変換が起きないようにした | `scripts/verify_snapshots.py`、`.gitattributes` |
| 点検 | 取込台帳と品質チェックの完了確認(2026-09-06、11 項目) | `data/INTAKE_latest.json` |

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
| **WS 生ログ(オーナー PC、未共有)** | オーナー PC `data\ws\FX_BTC_JPY_*.jsonl.gz`(板・ticker・約定の生 WS。共有されるのは抽出後の `data\tape\*` のみ) | **2026-08-20 06:13 UTC 〜 2026-09-11(23 日分。オーナー確認 2026-09-12、L-120。最古 9.2 MB、最新は書き込み中 24.5 MB)** | **PC に未共有の可能性** | 2026-09-11 | 手順 P11(板 10 段への抽出 → `share_logs.bat` で共有。生ログ自体は共有しない) | ④-1 経費の床の再実行(`docs/PHASE2/EXEC/RESULT.md` §1.6、L-098) |
| 約定 31日ロングテープ(us、tardis形式) | `backtest_data/bitflyer_executions_us_20260723_20260906/` | 2026-07-23〜09-06 | 取得済 | 2026-09-11 | — | 未使用 |
| tardis 形式 約定(**標本日 = 各月 1 日**) | `data/tardis/bitflyer_FX_BTC_JPY_trades/` | **2019-09-01〜2026-09-01、85 標本日。全日 00:00〜23:59 のフルカバー、1 日 1.0 万〜290 万件。列 = exchange/symbol/timestamp/local_timestamp/id/side/price/amount(**約定の向きが付いている**)。`_fetch_summary.json` に取得時の遅延分布、`MD5SUMS` あり** | 取得済 | **中身を実際に開いて確認 2026-09-13**(それまで「詳細未確認」のまま 2 日放置していた) | — | **O-3c の経費実測(2023-06〜2024-10 に 17 標本日が入る。板は無いが約定の向きがあるので実効スプレッドが測れる)** |
| 約定 31日スナップショット(2本) | `backtest_data/candles_FX_BTC_JPY_31d_20260823.csv.gz`, `backtest_data/executions_FX_BTC_JPY_31d_20260823.csv.gz` | 〜2026-08-23 | 取得済 | 2026-09-11 | — | 未使用 |
| 約定 31日スナップショット(2026-09-08) | `backtest_data/executions_FX_BTC_JPY_31d_20260908/` | 〜2026-09-08 | 取得済 | 2026-09-11 | — | 未使用(31日制限の前倒し回避のみ) |
| 継続ローリング(生、日次更新) | `data/candles_FX_BTC_JPY.csv`, `data/executions_FX_BTC_JPY.csv`, `data/flow_FX_BTC_JPY.csv`, `data/spread_FX_BTC_JPY.csv` | 最新は 2026-09-08 更新(`spread_FX_BTC_JPY.csv` 既知の欠測: 2026-08-28T04:19:17Z までの約10.3h、2026-08-26頃の約10.7h(未確認)。`schema/spread_fx_btc_jpy.json` 記載) | 取得済 | 2026-09-11 | — | 執行校正・マチルダ系構成選択(重度消費、`DATA_CONSUMPTION_LOG.md` §1) |
| 1分足 30日/継続結合 | `backtest_data/candles_FX_BTC_JPY_30d_20260820.csv`, `backtest_data/fx_btc_jpy_1m_continuous_20260906/` | 〜2026-08-20 / 2026-09-06 時点結合 | 取得済 | 2026-09-11 | — | 面探索(重度消費) |
| 清算・強制決済(losscut) 履歴 | `https://api.bitflyer.com/v1/executions`, `getticker`, `getboardstate`(公開API)、`https://lightning.bitflyer.com/docs`(公式APIリファレンス) | 該当なし(清算を識別するフィールド・専用エンドポイントいずれも無し) | **試行して不可(bitFlyer Lightning の公開 API リファレンスと実測スキーマ(`/v1/executions`・`getticker`・`getboardstate`)の両方で、約定に清算を識別するフィールドが存在しないことを確認。清算履歴の専用エンドポイントも見つからない)** | 2026-09-12 | `docs/DATA/probes/20260912_o3c_supp_a_bitflyer_bitmex.log` | O-3c(調達、2026-09-12) |
| 板の深さの履歴(ヒストリカル) | — | 現在の板スナップショットのみ `https://api.bitflyer.com/v1/board` で取得可(履歴保存 API は無い) | **試行して不可(板の履歴配信APIが存在しない。現在値のみ HTTP 200 で確認。方法: GET、この環境から実測)** | 2026-09-11 | `docs/DATA/probes/20260911_crypto_cfd_board_liq_funding_basis.log` | 未使用(自前スナップショット化が必要) |
| bitFlyer SFD・証拠金維持率・ロスカット閾値の一次資料(公式FAQ) | SFD: `https://bitflyer.com/ja-jp/faq/7-33`; 証拠金維持率・ロスカット: `https://bitflyer.com/ja-jp/faq/7-23`, `7-11`, `7-9` | この環境から GET(curl HTTP/1.1・HTTP/2・WebFetch の3通り)を試し、HTTP 403(WAF)で本文が読めない。同じ実行で `lightning.bitflyer.com/docs` は 200 で読めているので、ホスト固有の遮断 | **試行して不可(範囲・方法)** | 2026-09-12 | `docs/DATA/probes/20260912_o3c_supp_a_bitflyer_bitmex.log` | 未使用(オーナー PC の通常のブラウザなら読める可能性があり、未確認) |

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
| OKX 建玉(OI)・L/S比 スナップショット(自前記録) | `backtest_data/auto_okx_open_interest_5m_20260905/`(同 09-06〜09-08 も同様)、`backtest_data/auto_okx_long_short_ratio_20260905/`、`data/okx_btc_oi_*.csv`、`data/okx_btc_lsratio_*.csv` | 2026-08-23 以降、5分/1時間粒度で継続記録(既知の欠測: 2026-08-27夜〜08-28朝 約10.3h、2026-08-31 09:07:42Z〜12:03:50Z 約2.9h。`schema/oi_snapshots.json` 記載) | 取得済 | 2026-09-11 | — | 未使用(自前構築中の履歴、判定はまだ) |
| Coinalyze(清算・OIの集計値、鍵必須) | `https://api.coinalyze.net/v1/*` | — | **試行して不可(HTTP 401、API キー必須。方法: GET、この環境から実測)** | 2026-09-11 | `docs/DATA/probes/20260911_crypto_cfd_board_liq_funding_basis.log` | 未使用 |
| Gate.io 個別清算約定(90日、鍵不要) | `backtest_data/gate_liquidations_20260908/BTC_USDT.jsonl.gz` | 2026-06-10〜09-08(2,160時間、79,183件、欠測167時間) | 取得済 | 2026-09-11 | `docs/DATA/probes/20260911_crypto_cfd_board_liq_funding_basis.log`(再確認、既存台帳は L-030) | P8(清算研究、進行中) |
| BitMEX 保険基金 日次残高(全通貨) | `backtest_data/bitmex_insurance_20260912/`(`insurance.jsonl.gz` / `insurance_daily.csv`) | 2016-02-28〜2026-09-11、通貨 XBt/USDt/Gwei/USD/USDe/USDc、9,804 レコード、欠測日 0、重複 0 | 取得済(BitMEX 2026-09-23 閉鎖前の退避) | 2026-09-12 | `docs/DATA/probes/20260912_bitmex_insurance_fetch.log` | O-3c(未使用。清算強度の長期代理の候補。**注: ウォレット残高であり清算イベントの代理ではない**) |
| Binance/BitMEX/Bybit/OKX 清算 WS ストリーム(自前記録) | `data/liquidations/*.jsonl.gz`, `paper_logs/liquidations/*.jsonl.gz` | 常駐記録(取引所により履歴無し、詳細 `scripts/record_liquidations.py`) | 取得済。うち **10 ファイルは破損・回収待ち**(旧 Writer のハードキルによる gzip メンバ境界破損、2026-09-11 発見、L-121。回収手順 `docs/OWNER_PROCEDURES.md` P14) | 2026-09-11 | — | 未使用 |
| BitMEX XBTUSD 1秒足(取引所閉鎖前の保全) | `backtest_data/bitmex_trade_1s_XBTUSD/` | 2017〜2021(1,826 日、7,874 万本) | 取得済。**2017〜2019 は K1 の探索区間として全読(第 1〜14 部)、2020〜2021 は封印として 2026-09-10 に一度だけ開封(L-085、第 15 部)。この設計での再利用は不可** | 2026-09-11 | `docs/DATA_CONSUMPTION_LOG.md` | K1 全部(第 1〜15 部) |
| Kraken XBTUSD 1分足 | `data/kraken_XBTUSD_1m.csv` | 単一ファイル | 取得済 | 2026-09-11 | — | 未使用 |
| Deribit DVOL(ボラ指数) | `data/deribit_dvol_1h.csv`, `data/deribit_dvol_1m_7d.csv` | 1時間粒度(全期間)/1分粒度(直近7日) | 取得済 | 2026-09-11 | — | 未使用 |
| 現物 BTC/ETH 日足(Bitstamp/Coinbase/Yahoo、複数取引所横断) | `backtest_data/daily_btcusd_*.csv.gz`, `backtest_data/daily_ethusd_*.csv.gz` | 〜2026-08-28 | 取得済 | 2026-09-11 | — | 未使用 |
| 資金調達率・基差(自前結合、粒度不明) | `data/funding_rate_history.csv`, `data/basis_1m.csv` | 単一ファイル、範囲未確認 | 取得済(ファイル存在のみ確認。列・範囲は未検査) | 2026-09-11 | — | 未使用 |
| Tardis.dev(第三者・有料、メタデータのみ確認) | `https://api.tardis.dev/v1/exchanges/binance-futures` | 取引所メタデータ(1件)のみ取得。実データは未取得・鍵要 | 未試行(メタデータ到達のみ確認、本体データは有料) | 2026-09-11 | `docs/DATA/probes/20260911_crypto_cfd_board_liq_funding_basis.log` | 未使用 |
| CryptoDataDownload(第三者・無料、OHLCVのみ想定) | `https://www.cryptodatadownload.com/data/binance/` | トップページのみ確認(板深さ・清算・資金調達率の提供は未確認) | 未試行(トップページ到達のみ確認、板・清算・資金調達率の有無は個別ページ未確認) | 2026-09-11 | `docs/DATA/probes/20260911_crypto_cfd_board_liq_funding_basis.log` | 未使用 |
| ベニュー横断調査(サーベイ文書) | `backtest_data/venue_survey_20260827/` | — | 取得済 | 2026-09-11 | — | 未使用 |
| Binance COIN-M BTCUSD_PERP liquidationSnapshot(強制決済イベント、公開アーカイブ) | `backtest_data/binance_cm_o3c_20260913/liquidationSnapshot/BTCUSD_PERP/`(日次zip、472/478日) | 2023-06-25〜2024-10-14、欠測6日(`2023-09-09/23/25`, `2024-06-01/11/12`) | 取得済(配信停止前の退避) | 2026-09-13 | `docs/DATA/probes/20260913_binance_cm_o3c_fetch.log` | O-3c(未使用) |
| Binance COIN-M BTCUSD_PERP metrics(建玉`sum_open_interest`・L/S比、5分粒度) | `backtest_data/binance_cm_o3c_20260913/metrics/BTCUSD_PERP/`(日次zip、379/478日) | 2023-06-25〜2024-10-14、欠測99日(単発2日+`2024-03-04`〜`2024-06-08`の連続97日) | 取得済(配信停止前の退避) | 2026-09-13 | `docs/DATA/probes/20260913_binance_cm_o3c_fetch.log` | O-3c(未使用) |
| Binance USD-M liquidationSnapshot アーカイブ(全シンボル) | `https://data.binance.vision/data/futures/um/daily/liquidationSnapshot/` | 該当なし | **試行して不可(全シンボル・全期間で S3 list-objects が KeyCount=0。方法: GET S3 list-objects、実測 2026-09-12)** | 2026-09-12 | `docs/DATA/probes/20260912_o3c_liquidation_history.log` | O-3c(未使用) |
| BitMEX 公開バルクアーカイブの清算専用フォルダ | `https://public.bitmex.com/`(S3 REST) | 該当なし | **試行して不可(ディレクトリ一覧に「清算」名のフォルダが存在しない。方法: GET、実測 2026-09-12)** | 2026-09-12 | `docs/DATA/probes/20260912_o3c_liquidation_history.log` | O-3c(未使用) |
| CoinGlass 個別イベント清算(`/api/futures/liquidation/order`) | `https://open-api-v4.coinglass.com/api/futures/liquidation/order` | 不明(鍵必須) | **試行して不可(HTTP 200 だが本文 JSON が `{"code":"401","msg":"API key missing."}`。方法: GET、実測 2026-09-12)** | 2026-09-12 | `docs/DATA/probes/20260912_o3c_liquidation_history.log` | O-3c(未使用) |
| OKX 1分足(無期限、history-candles) | `https://www.okx.com/api/v5/market/history-candles?instId=BTC-USDT-SWAP&bar=1m` | 2020-01-01〜現在(2019-10-01は空、境界未特定) | 未試行(到達性・範囲のみ確認、本体未取得) | 2026-09-12 | `docs/DATA/probes/20260912_o3c_liquidation_history.log` | O-3c(未使用) |
| Gate 1分足(candlesticks、真の OHLC) | `https://api.gateio.ws/api/v4/futures/usdt/candlesticks?contract=BTC_USDT&interval=1m` | 直近 約5〜8日のみ(それ以前は "too long ago" で HTTP 400) | **試行して不可(APIの遡及上限。方法: GET、from/toを5/8/10/15/30日前で実測、実測 2026-09-12)** | 2026-09-12 | `docs/DATA/probes/20260912_o3c_liquidation_history.log` | O-3c(未使用) |
| ccxt `fetchLiquidations`(bitmex)実装 | `ccxt/python/ccxt/bitmex.py`(GitHub) | 該当なし(公開`/liquidation`の薄いラッパーで過去分は返らない) | **試行して不可(ソース確認済み。timestampを自らnullにしている)** | 2026-09-12 | `docs/DATA/probes/20260912_o3c_supp_a_bitflyer_bitmex.log` | O-3c(未使用) |
| Tardis.dev BitMEX `liquidation`チャネル(第三者・有料) | `https://docs.tardis.dev/historical-data-details/bitmex` | 未確認(チャネル存在は確認、範囲・料金は未取得) | 未試行(到達性のみ確認、深さ・料金は次回調査が必要) | 2026-09-12 | `docs/DATA/probes/20260912_o3c_supp_a_bitflyer_bitmex.log` | O-3c(未使用) |
| archive.org(public.bitmex.com 過去スナップショット確認経路) | `web.archive.org` | 該当なし | **試行して不可(この環境から WebFetch・curl 双方で到達不能。方法: WebFetch(ツール側ブロック)、curl HTTPS(接続リセット)。実測 2026-09-12)** | 2026-09-12 | `docs/DATA/probes/20260912_o3c_supp_a_bitflyer_bitmex.log` | O-3c(未使用)。オーナー PC での到達確認が必要 |
| `deploy/mirror_bitmex.bat` の保全対象範囲 | `scripts/mirror_bitmex_archive.py`(PREFIXES定義) | trade/quote/porl の3種のみ、liquidation は対象外 | 取得済(コード確認、ダウンロードそのものではない) | 2026-09-12 | `docs/DATA/probes/20260912_o3c_supp_a_bitflyer_bitmex.log`(コード確認、プローブではない) | O-3c(未使用) |
| Binance USD-M BTCUSDT metrics(建玉・L/S比、5分粒度、公開アーカイブ) | `https://data.binance.vision/data/futures/um/daily/metrics/BTCUSDT/` | 2020-09-01〜(2026-09-01時点存在、継続は推定) | 未試行(到達性・1件サンプルDLのみ確認、本体一括取得は未実施) | 2026-09-12 | `docs/DATA/probes/20260912_o3c_supp_b_oi_vap_gate1m.log` | O-3c(未使用) |
| Binance COIN-M BTCUSD_PERP aggTrades/trades(個別約定、公開アーカイブ) | `https://data.binance.vision/data/futures/cm/daily/{aggTrades,trades}/BTCUSD_PERP/` | 2020-08-11〜(2023-06-25・2024-10-14の存在を個別確認、清算窓と一致) | 未試行(到達性のみ確認、本体未取得。478日換算の容量見積り約1.48GBはサンプル13日の外挿、実測ではない) | 2026-09-12 | `docs/DATA/probes/20260912_o3c_supp_b_oi_vap_gate1m.log` | O-3c(未使用) |
| OKX rubik open-interest-history(REST、保持期間の実測) | `https://www.okx.com/api/v5/rubik/stat/contracts/open-interest-history` | 5m=約3〜6日、1H=約30〜59日(自前記録の欠測と符合) | 未試行(REST到達性・境界のみ実測、本体保存は自前記録`auto_okx_open_interest_5m_*`で別途継続中) | 2026-09-12 | `docs/DATA/probes/20260912_o3c_supp_b_oi_vap_gate1m.log` | O-3c(未使用) |
| OKX rubik long-short-account-ratio(REST、保持期間の実測) | `https://www.okx.com/api/v5/rubik/stat/contracts/long-short-account-ratio` | 5m=約1〜2日のみ、1D=少なくとも90日(上限未特定) | 未試行(境界のみ実測) | 2026-09-12 | `docs/DATA/probes/20260912_o3c_supp_b_oi_vap_gate1m.log` | O-3c(未使用) |
| Gate contract_stats(建玉・L/S比・mark_price、1分粒度) | `https://api.gateio.ws/api/v4/futures/usdt/contract_stats?contract=BTC_USDT&interval=1m` | 直近〜179日前(180日が保持上限、一次資料的に確定) | 未試行(到達性・境界・サンプルのみ確認、179日分の一括取得(約65リクエスト)は未実施) | 2026-09-12 | `docs/DATA/probes/20260912_o3c_supp_b_oi_vap_gate1m.log` | O-3c(未使用) |
| BitMEX instrument 建玉(openInterest、現在値のみ) | `https://www.bitmex.com/api/v1/instrument` | 該当なし(現在値1点のみ、過去日指定手段が構造上無い) | **試行して不可(API構造上、過去日を指定する手段が無い。方法: GET、実測 2026-09-12)** | 2026-09-12 | `docs/DATA/probes/20260912_o3c_supp_b_oi_vap_gate1m.log` | O-3c(未使用) |
| CryptoCompare(CoinDesk Data) histominute(gate.io、第三者) | `https://min-api.cryptocompare.com/data/v2/histominute?e=gateio` | 該当なし | **試行して不可(HTTP 401、鍵必須。無料匿名アクセスは廃止。方法: GET、実測 2026-09-12)** | 2026-09-12 | `docs/DATA/probes/20260912_o3c_supp_b_oi_vap_gate1m.log` | O-3c(未使用) |
| Hyperliquid BTC無期限 `userFills`/`userFillsByTime`(清算識別可、`liquidation`フィールド) | `https://api.hyperliquid.xyz/info`(POST、type=userFills/userFillsByTime) | 直近2000件(userFills)/直近10000件(userFillsByTime、一次資料記載の上限) | 未試行(到達性のみ確認、実際の清算含有アドレスでの検証は未実施) | 2026-09-12 | `docs/DATA/probes/20260912_o3c_supp_c_hyperliquid.log` | O-3c(未使用) |
| Hyperliquid BTC無期限 `candleSnapshot`(1分足) | 同上(type=candleSnapshot) | 直近5000本(1分足で約3.47日、一次資料+実測で確認) | **試行して不可(それより古い1分足はこのAPI経由では不可。方法: POST、実測 2026-09-12)** | 2026-09-12 | `docs/DATA/probes/20260912_o3c_supp_c_hyperliquid.log` | O-3c(未使用) |
| Hyperliquid BTC無期限 `metaAndAssetCtxs`(建玉・資金調達率、現在値のみ) | 同上(type=metaAndAssetCtxs) | 現在のスナップショットのみ(履歴機能なし) | 取得済(現在値、2026-09-12T06:43:15Z: OI 35904.57 BTC, dayNtlVlm $3.58B) | 2026-09-12 | `docs/DATA/probes/20260912_o3c_supp_c_hyperliquid.log` | O-3c(未使用) |
| Hyperliquid S3アーカイブ(板 L2Book想定、`hyperliquid-archive`) | `s3://hyperliquid-archive/market_data/[date]/[hour]/[datatype]/[coin].lz4`等(一次資料記載パス) | 月次アップロード目安、欠測許容(一次資料明記)。中身は未確認 | **試行して不可(匿名アクセスは403、Requester Pays。方法: GET S3 ListObjectsV2、実測 2026-09-12)** | 2026-09-12 | `docs/DATA/probes/20260912_o3c_supp_c_hyperliquid.log` | O-3c(未使用) |

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

## 8. 損失・欠損(事象単位、追記専用)

既知のデータ損失・欠損を一覧にする。「損失」= 元データが物理的に消えて再取得不能なもの、「欠損」=
そもそも十分な範囲/形式で保存されなかった(短時間・単発・列不足)ため実質的に再計算不能なもの、の両方を含む。
台帳自体は追記専用(行の削除・書き換えは「記録日」を追加した新規行で行う。既存行は消さない)。
行の単位は「事象」であり、§1〜§7(資産単位)の行には混ぜない。

| # | 何が | 期間 | 原因 | 復旧可否 | 記録日 |
|---|---|---|---|---|---|
| 1 | OKX 5m 建玉(open interest)のギャップ | 2026-08-23〜2026-09-03 | `fetch_okx.py` が `fetch_all.bat` に組み込まれていなかった(未スケジュール) | 不可(OKX の 5m OI は保持期間 2〜3 日、既に取得元からロールオフ済み) | 2026-09-05 |
| 2 | 板記録(WS)の切断ファイル 34 本 | 各ファイルの最終メンバー書き込み中(旧レコーダ運用期間全体、日付は個別ファイルにより異なる) | 旧レコーダ(`src/bot/market_data/realtime.py`)が単一 gzip メンバーをセッション中ずっと開いたまま書き続け、`stop_all.bat` の強制終了(`taskkill /F`)がファイルを閉じる機会を与えずに切っていた | 部分可(`scripts/repair_gz_listing.py` で末尾未完メンバー手前までの行は読み出し可能。以後は列 `truncated` で判定。レコーダは修正済みで新規記録は完結する) | 2026-09-05 |
| 3 | bitFlyer 生約定履歴(`FX_BTC_JPY`)、31 日 API 保持期間を超えて遡る分 | 恒久テープ抽出開始(`data/tape/executions_20260820.csv.gz`、先頭 2026-08-20T06:13:26Z、`paper_logs/INTAKE_latest.json` 記載)より前 | bitFlyer の約定履歴 API は 31 日でロールオフする(`config/constants.yaml: data_retention.bitflyer_executions_days=31`)。`extract_tape.py` による恒久保存が始まったのは 2026-08-20 で、それ以前は取得のたびに 31 日窓から外へロールオフし続けていた | 不可(上流 API 自体が既に保持していない。2026-08-20 以前の生約定は永久に再取得不能) | 2026-09-05 |
| 4 | J-REIT スナップショット作成時の kabutan 生 HTML(10 ページ)・Yahoo 生 JSON | 2026-09-04 | リードが「CSV があれば十分」と判断してコミット前に削除((削除済み文書) §0 の自己申告)。データ管理原則「全保管・削除禁止」への違反 | 不可(コミット前削除のため git 履歴にも残らない。CSV への変換後の派生データのみ現存) | 2026-09-05 |
| 5 | パケット H(JPX overnight premium)監査が最初に使った Yahoo Finance 日足 JSON(15 銘柄、`range=15y`) | 監査時点(H_jpx_cross_market_overnight.md 記載、2026-09 上旬) | 「fetched live」と記載されているのみで、取得した 15 本の JSON レスポンス自体はスナップショットとして保存されなかった。後日 JPR6/JPR7 向けの追加確認 4 本のみ `backtest_data/audit_fetch_H_20260905/` として保存(2026-09-05 に再取得) | 部分可(Yahoo から同じ範囲を再取得すれば同種のデータは得られるが、原監査が実際に読んだバイト列そのものは再現不能。特に bad-print 15 件などの一時的な異常値は再取得時に同じ値が返る保証がない) | 2026-09-05 |
| 6 | 長期モメンタム研究(2 年 4h/日足トレンドフォロー、R3)の原データ | 研究実施時点(2 年分、粒度 4h/日足) | 一度もスナップショットされておらず、210 日 1 分足での代替検証しかできない((削除済み文書) row 3、(削除済み文書) R3 行) | 不可(元の粒度・期間のデータは存在しない。代替の 210 日 1 分足では非再現) | 2026-09-05 |
| 7 | スキャルパー武装閾値の引き下げ検証の母集団 | R14 検証時点 | 「限界トレードが低質」という数値は、実際にはライブ取引ではなく別母集団(オフライン再生)由来だったと判明。オフライン再生時の元データ・分割ラベルが記録されておらず再構成不能 | 不可(再計算不能・未検証に格下げ。再実測には新規データ収集が必要) | 2026-09-05 |
| 8 | TP のボラ連動(適応型 TP、R19)ログの必要列 | ライブ前方 n=77 の記録期間 | ボラ列・TP 割当・train/val/OOS の分割ラベルがログ(`bot.jsonl` 等)に記録されておらず、傾き消滅の再構成ができない((削除済み文書) R19/R16 行) | 不可(記録不備。今後の同種検証は分割ラベル・ボラ列を先に設計してログに残す必要あり) | 2026-09-05 |
| 9 | WS メッセージ配信レイテンシ(`data/latency/ws_vm.csv`) | 2026-08-28T00:13:06Z〜00:22:40Z(9.6 分間、単一セッション) | レイテンシ計測がこの 1 回・9.6 分間しか記録されておらず、`data/latency/` 配下に他のファイルが無い。edge×latency 曲線や頻度(0.84/日)の主張を検証するには全く不十分((削除済み文書)) | 不可(過去分は存在しない。今後複数セッション・長時間の計測を新規に取得する必要あり) | 2026-09-05 |
| 10 | 板の全深度(フルデプス)データ(壁板の生存・吸収の検証、AR-78) | 4 時間分(単日)のみ | 真の全深度データがこの 1 セッションしか記録されておらず、16 日分ある top-of-book 代理データとは順位が逆転する(方向不一致)ため検証不能 | 不可(過去分は存在しない。複数日の全深度記録が別途必要 — データ管理 #40) | 2026-09-05 |
| 11 | maker 両建て(逆選択検証、P3)の発注イベント記録 | P3 検証対象期間全体 | maker の両建て発注イベントがそもそもログに記録されておらず、再構成不能((削除済み文書) P3 行、AR-61 の注記) | 不可(記録が存在しない。将来同種の検証をするなら発注イベントのログ設計が先に必要) | 2026-09-05 |
| 12 | Binance の秒足(1 秒粒度)データ(L3、1 分足 lag1 相関の秒遅れ検証) | L3 検証対象期間 | リポジトリ内に Binance の 1 秒粒度データが一度も存在せず、秒単位の遅れの直接検証が再計算不能((削除済み文書) L3 行) | 不可(未収集。今後必要なら新規に秒足を収集・保存する必要あり) | 2026-09-05 |
| 13 | maker の逆選択を測った元テープ | 第 i・j 報作成時点(日付不明) | 元テープが消失し、再検証は別テープでの近似にとどまった(当時の主張は数倍〜10 倍の過大だったと判明) | 不可(元テープは既に無く、法則の大きさの直接再検証はできない。閉鎖の結論自体は E2 で別テープにより再現) | 2026-09-05 |
| 14 | `backtest_data/candles_FX_BTC_JPY_30d_20260820.csv`(凍結・旧)の open/close 値、重複区間の一部(3,405〜6,655/40,094分) | 2026-07-23 12:09〜2026-08-20 08:22(31d/30dスナップショット重複区間) | 凍結スナップショットが2本あり値が食い違う件を`backtest_data/executions_FX_BTC_JPY_31d_20260823.csv.gz`から`build_candles`で再構築して裁定。high/lowはほぼ一致(2件/0件)、open/close(順序依存のfirst/last)が多数不一致(3,836件/3,405件)なので、30dスナップショット構築時に約定を時刻順ソートせずresampleした可能性が高い(`schema/candles_fx_btc_jpy.json` known_defects 参照)。実損失ではない(正しい方の`..._31d_20260823.csv.gz`と生約定から随時再現可能、どちらのファイルも書き換えていない)が、単純concatで結合すると誤ったopen/closeが混入するため記録 | 不要(正しい方のスナップショットが現存し随時再現可能。30dスナップショットのopen/closeを継続窓へ使わないことが復旧策) | 2026-09-06 |
| 15 | なし(予防的記録)。P2-08b の Binance スナップショット 4 系統(現物 aggTrades 45 日 994MB、1 秒足 167MB、無期限 aggTrades 1.2GB、診断用 標本日 aggTrades 85 日 3.1GB)の**本体データを git に入れていない** | 2026-07-23〜09-05(取引窓)、2019-09-01〜2026-09-01(標本日) | オーナー PC が毎日 pull するリポジトリに 5.5GB を載せられないため。各ディレクトリの `README.md`・`MD5SUMS`・索引は commit 済みで、Binance Vision は保持期限なしの公開アーカイブ(CHECKSUM 付き)なので `scripts/fetch_binance_vision.py --kind aggTrades` で同一ファイルを再取得し MD5 で突合できる。研究コンテナが再生成されたら再取得が必要(所要 1〜2 時間) | 不要(再現可能)。封印台帳 `SEALED.json` にはパスと MD5 を登録し、改変検知は効く | 2026-09-07 |


(以下 2 節は旧 `DATA_LOSS_REGISTER.md` の「分類の出所」「この台帳に載せない判断」を原文のまま移したもの。2026-09-12、監査役の指摘)

#### 分類の出所

- 行 1・2・3・6: `docs/DATA_QA_CHECKLIST.md`・CLAUDE.md §2 に記載の既知事象。
- 行 4・5: (削除済み文書) §0(自己申告)、(削除済み文書)、
  `backtest_data/audit_fetch_H_20260905/README.md`。
- 行 7・8・11・12・13: (削除済み文書)(AR-19, AR-26, AR-40, AR-61)・
  (削除済み文書) §5.2「未検証(再計算不能)33件」の分類 (i) 元データ消失
  (L5, L3, R3の2年粒度)・(iii) ログに必要列が無い(R19, R16の分割, P3)・(iv) 数値が別母集団由来(R14, R20)
  から、データの物理的な損失・欠損に該当する行のみを転記した(定義未文書化 (ii) や外部一次資料未取得 (v) は
  データ損失ではないため対象外)。
- 行 9・10: (削除済み文書)(latency)、(削除済み文書) AR-78(venue depth)。

#### この台帳に載せない判断

`99_master.md` §5.2 の 33 件「未検証(再計算不能)」のうち、以下は物理的なデータ損失/欠損ではないため
本台帳の対象外とした(データ品質ではなく仮説・監査スコープの問題):

- 分類 (ii) 定義がコード・文書のどこにも無い: R39, L21, L23, R32, FXR4 — 実装・文書の欠落であり、データは
  存在するか、そもそも定義が無いだけ。
- 分類 (v) 外部一次資料未取得: FXC1/2/4/7, JPC1〜5 系 — 一次資料を取得していないだけで、リポジトリ内のデータが
  消えたわけではない。
- R9, R20, P4, P6, JPP1, JPP2, PR7 — 監査スコープ外・進行中フォワード計測・母集団解釈の相違であり、データの
  物理的損失ではない。
- I-002(`docs/INCIDENTS.md`、2026-09-06): `backtest_data/auto_*` 保持期限スナップショットが
  `share_logs.bat` 経由で研究環境へ push されていなかった件。オーナー PC 上には作成済みで現存しており、
  **消失していない**(単に共有ステップが未実装だっただけ)。`share_logs.bat` 修正後は commit・push されるため
  本台帳への計上対象外。

## 9. 保持期間(資産単位)

作成 2026-09-08。**「取り逃すと二度と手に入らない」データを一箇所に集めた表**(§0 の「守る仕組み」とは別に、
個別ソースごとの保持期限をここにまとめる)。印: 事実 = 実測、推定 = 推論。判定日を必ず入れる(賞味期限つき)。

### 9.1 硬い保持期間(上流が消す)

| ソース | 上限 | 仕組みでの扱い | 状態 |
|---|---|---|---|
| bitFlyer 公開約定 `/v1/getexecutions` | **31 日**(サーバが明示エラー) | `bitflyer_executions` 15 日間隔 | 保護済み。2026-09-08 の到達最古 = 2026-08-08T05:26【事実】 |
| OKX 建玉 1H | 30 日 | `okx_open_interest_1h` 14 日間隔 | 保護済み |
| OKX 建玉 5m | **2〜3 日** | `okx_open_interest_5m` **毎日** | 保護済み |
| OKX 買い持ち比率 | 60〜90 日 | `okx_long_short_ratio` 28 日間隔 | 保護済み |
| **JPX デリバティブ日報の月次索引** | **暦年**(2026-01〜は 200、2025-10 以前は 404) | **2026-09-08 に発見・登録**。`jpx_daily_report_months` を新設し、収集器が生 zip を `data/jpx_daily/raw/` に保存するよう変更 | **新規。次の消失は 2027-01-01** |

#### JPX 日報について(新発見の詳細)
`scripts/fetch_jpx_daily.py` は日次の OSE 報告 zip を取得 → **日経の行だけ**を抜いて `nk225_sessions.csv` に追記し、
**zip を捨てていた**。zip には全商品(TOPIX 先物・建玉・出来高を含む)が入っており、索引ごと暦年で消える。
P2-06(NT 倍率)を始める直前にこれを捨てているのは筋が悪い。→ 生 zip を保存するよう変更(追記のみ・失敗しても収集は継続)。
索引 9 か月分(2026-01〜09)は `backtest_data/jpx_daily_report_json_20260908/` に退避済み。【事実】
**残作業**: 生 zip から全商品を抽出する CSV を作る。zip 自体は 1 年で ~500MB になり git に載せられないため、
抽出した CSV を共有する設計にする。

### 9.2 **ベニューそのものが消える**(2026-09-09 に新設。この軸が台帳に無かった)

保持期間の話とは別に、**取引所が閉じるとその過去データも一緒に消えうる**。
この軸を本台帳は持っておらず、**オーナーの指摘で初めて登録した**。
リードは学習データ(2026-05 まで)に無い出来事を検知できないので、
**ベニューの存廃は記憶で答えず、必ずその取引所自身の告知を GET で読む。**

| ベニュー | 状態【事実・一次情報】 | 期限 | 対応 |
|---|---|---|---|
| **BitMEX** | **閉鎖を告知**(`api/v1/announcement`、2026-09-01 付)。11 銘柄は 09-02 に廃止済み | **XBTUSD 等は 2026-09-16 12:00 UTC に上場廃止・清算 / 取引所閉鎖 2026-09-23** | 公開約定アーカイブ(2014-11〜**2025-02-22**、3,747 日 / 47.9 GB)を**閉鎖前に確保**。1 秒バーに落として `backtest_data/bitmex_trade_1s_XBTUSD/`(1 日 0.8MB)。**2017-2021 = 完了**(1,826 日 / 秒バー **7,874 万** / 元の約定 **7.18 億**、約 900MB)。**生のまま丸ごと(trade 47.9GB + quote 197.8GB)はオーナー PC に保全中**(手順 P10、L-039) |
| その他(Binance / Bybit / OKX / Gate / bitFlyer) | 未確認 | — | 同じ検査を定期的に行う(告知 API か公式ブログを GET) |

**波及**: BitMEX の**ライブ清算記録は、上場廃止に向かう期間のもの**になる。建玉整理・
reduce only・薄い板の下で起きる清算は通常時と別物なので、**この期間を機構の検定に使わない**。
記録自体は害が無いので続けるが、`schema/liquidations.json` と本台帳に線を引いておく。
