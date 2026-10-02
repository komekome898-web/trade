# c2_owner_xvenue_wick の測定(W4)

W4 の仕様(`docs/DISCUSSIONS/2026-10-02_W4_spec.md` §3)と W1 の測定器(`src/bot/research/cards/`)で測った記録。
言葉の判定はしない(区間の両端と MDE を並べるだけ。計画 段 2 の訂正)。各数値の意味は `src/bot/research/cards/measure.py` の冒頭の説明のとおり。

## 何をどう走らせたか

- カード: `src/bot/research/cards/library/c2_owner_xvenue_wick.py` の `C2OwnerXvenueWick(series=…, foot_min=…)`。変種 (a) = `SERIES_SPOT`(Binance BTCUSDT 現物)、(b) = `SERIES_UM`(Binance USD-M 先物)、(c) = `SERIES_BITMEX`(BitMEX XBTUSD)。足の長さ 1・3・5・15・30・60 分。
- 出力: `<変種>_<足の長さ>m/`(measure.json・daily.csv・diagnostics.json・week_block.json)。
- 参照 4 系列(始値・高値・安値・終値)は同じファイルから値の列を変えて `load_reference` で読んだ(行の時刻 = `open_time` のまま、lag_ns 60 秒。宣言は CARD.md の測定の設定)。読む範囲は各変種の測る期間 [開始, 終了) の中だけ(開始より前の行は渡していない)。
- 診断(diagnostics.json、INTENT_MAP §7。検定の数に入れない): 枝(19 だけ・24 だけ・両方)ごとのシグナルの数と、決定 t の P_t を「足の終わりが t 以下の最新のシグナル」に帰属させた平均損益。式は各 diagnostics.json の `formula`。
- 測定: `measure_card(CARD.md, run, seed=20261002, control_seed=20261003, regimes=[(開始, "SFD")], daily_path=…/daily.csv)`。vr_q_bars・day_zone・参照の宣言は CARD.md の測定の設定から測定器が読む。制度の変数は 1 値(W4 の仕様 §3: 期間は全部 SFD の時代)。
- 種: ブートストラップ 20261002、対照のずらし 20261003。1 週のブロックの区間も 20261002。
- 1 週のブロックの区間(week_block.json): 同じ P_t の系列に `bot.bt.validation.bootstrap.block_bootstrap_ci`(circular)を L_w = max(ceil(Politis–White b), 10,080 本)・1,000 回・同じ種で当て、全体の平均の 95% 区間・se・MDE(`bot.bt.validation.power.mde`、5% 両側・検出力 80%・sd = se × √n)を出した。照合のため、同じ関数で L = 測定器の L(1 日)でも計算し(`day_recomputed`)、measure.json の区間と並べた。測定器のコードは変えていない。
- 走らせ方: 区切り(暦年)ごとに、その区切りの分だけを封印の門(`bot.bt.data` の load / load_reference)から読んで `run_card` に通し、区切りの記録をつないだ全期間の CardRun に測定器を 1 回当てた(ブートストラップは全期間の系列に 1 回。区切って測定していない)。つなぎ方は台本 `run_v2.py` の冒頭の説明。区切りの一覧は各 measure.json の `w4.chunks`。理由: run_card は核の履歴に届いた事象の写しを全部持つため、全期間を 1 回で走らせるとカード 2 で 15GB を超えて止まった(exit 137)。
- 区切って読んだ結果と全期間を一度に読んだ結果の同一性: 下の「照合」。
- 1 変種 = 1 起動。最大 3 本を並列に走らせた(リードの指示 2026-10-02)。

- 例外 `a_1m`: リードの変更の前に走らせた回で、全期間の足と参照を一度に読み(最大 RSS 7.00GB)、`run_card` だけを暦年で区切って同じカードの物でつないだ(台本 `run_c2_a_as_run.py`・`chunked.py`)。同じ区切りのつなぎ方の 2 週間の照合(`check_chunked.py`、6 つの足の長さ、区切り 3 か所)で持ち高・signal_log・参照の記録がビット一致。所要: 読み込み 502 秒、run_card 1,079 秒、measure_card 1,148 秒、1 週 51 秒(`c2_full.log`)。

## コマンド

リポジトリの直下で(台本は `scratchpad/w4/measure/` に置き、リポジトリには置いていない):

```
PYTHONPATH=src python <scratchpad>/run_v2.py --card c2 --variant <a|b|c> --foot <1|3|5|15|30|60>
```

並列: 最初の 3 本(c2 の a_3m・a_5m・a_15m)は `queue.sh 3`(`jobs.txt` の各行を `job.sh` で 3 本ずつ)。3 本が同時に測定器に入ったところで a_5m が記憶の上限(この環境の cgroup の上限 14,345,035,776 バイト)で止められた(exit 137、2026-10-02T12:25Z)。a_5m は最初からやり直した。その後は `sched3.sh`(`jobs2.txt` を上から順に、同時 3 本まで、1 本の最大 RSS の見積もり カード 2 = 4.3GB・カード 3 = 3.5GB・カード 1 = 3.0GB の合計 + 2GB が 14.3GB を超えるなら待つ)。

## 照合(区切って読む = 全期間を一度に読む)

- `check_v2.py c2`: 2018-01-01T00:00:00Z〜2019-01-01T00:00:00Z(1 年)、月の区切り 11 か所、足 521307 本・決定 520293。持ち高の食い違い 0 本(完全一致 True)。 足 60 分、signal_log 一致 True。 所要 907.2 秒、最大 RSS 2.52GB。
- `check_v2.py c3`: 2018-01-01T00:00:00Z〜2019-01-01T00:00:00Z(1 年)、月の区切り 11 か所、足 521307 本・決定 520293。持ち高の食い違い 0 本(完全一致 True)。 窓 1w、参照の記録の一致 True。 所要 565.2 秒、最大 RSS 1.76GB。
- `check_v2.py c1`: 2018-01-01T00:00:00Z〜2019-01-01T00:00:00Z(1 年)、月の区切り 11 か所、足 521307 本・決定 520293。持ち高の食い違い 0 本(完全一致 True)。 所要 486.7 秒、最大 RSS 1.35GB。

## 各回の要約

損益は bp・持ち高 1 単位あたり・経費前。区間は 95%(百分位)。MDE は 5% 両側・検出力 80%。
「1 分ごと」= 1 分ごとの P_t の系列の circular block bootstrap(L = 1,440 本は measure_card、L = 10,080 本は台本の week_block)。「日ごと」= 日ごとの損益の系列(日本時間の日)を日の塊(1 日・5 日)で circular block bootstrap し、1 分あたりに直したもの(daily_stats.json。式はそのファイルの formula)。リードの測り方の変更(2026-10-02)の後の回は measure_card を打っていない(1 分ごとの欄は —)。対照の百分位 = 持ち高を L 以上ずらした 200 通りの中の位置(measure_card の C5 d)。

| 変種 | 期間 | n(決定) | 日の数 | 平均(1 分あたり) | 平均(1 日あたり) | 1 分ごと L=1440 | 1 分ごと L=10080 | 日ごと 1 日塊 | 日ごと 5 日塊 | MDE(1 分ごと L=1440 / 日ごと 1 日塊) | 持ち高が 0 でない割合 | 変わった回数 | 対照の百分位 | 所要(秒) | 最大 RSS(GB) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| a_1m | 2017-08-17〜2023-12-17 | 3251350 | 2313 | 0.0345 | 48.51 | [0.0227, 0.0473] | [0.0219, 0.0471] | [0.0238, 0.0457] | [0.0218, 0.0474] | 0.0173 / 0.0161 | 0.4347 | 86615 | 100.0 | 読み込み 502 + run 1079 + 測定 1148 + 1 週 51 | 7.00 |
| a_3m | 2017-08-17〜2023-12-17 | 3251350 | 2313 | 0.0268 | 37.66 | [0.0169, 0.0380] | [0.0162, 0.0371] | [0.0163, 0.0375] | [0.0161, 0.0372] | 0.0152 / 0.0154 | 0.5476 | 82958 | 100.0 | 区切りの run 1879 + 測定 1183 + 1 週 52 + 診断 0 | 3.95 |
| a_5m | 2017-08-17〜2023-12-17 | 3251350 | 2313 | 0.0068 | 9.61 | [-0.0040, 0.0185] | [-0.0044, 0.0174] | [-0.0047, 0.0174] | [-0.0054, 0.0179] | 0.0162 / 0.0161 | 0.5947 | 75670 | 84.0 | 区切りの run 1814 + 測定 1135 + 1 週 50 + 診断 0 | 4.01 |
| a_15m | 2017-08-17〜2023-12-17 | 3251350 | 2313 | -0.0140 | -19.70 | [-0.0245, -0.0042] | [-0.0251, -0.0021] | [-0.0252, -0.0038] | [-0.0249, -0.0031] | 0.0144 / 0.0148 | 0.6781 | 54772 | 0.5 | 区切りの run 1872 + 測定 1186 + 1 週 51 + 診断 0 | 3.96 |
| a_30m | 2017-08-17〜2023-12-17 | 3251350 | 2313 | -0.0106 | -14.86 | [-0.0207, 0.0003] | [-0.0207, -0.0011] | [-0.0206, -0.0005] | [-0.0197, 0.0003] | 0.0147 / 0.0147 | 0.7150 | 38356 | 0.0 | 区切りの run 1861 + 測定 1099 + 1 週 55 + 診断 0 | 4.04 |
| a_60m | 2017-08-17〜2023-12-17 | 3251350 | 2313 | -0.0117 | -16.44 | [-0.0221, -0.0016] | [-0.0228, -0.0015] | [-0.0223, -0.0023] | [-0.0219, -0.0018] | 0.0151 / 0.0145 | 0.7473 | 24345 | 0.0 | 区切りの run 1888 + 測定 1150 + 1 週 54 + 診断 0 | 4.02 |

## 入力のファイルと sha256

sha256 は封印の門が読んだときに計算した値(門の manifest。走らせた記録 `runs/<card>/summary_<変種>.json` から写した)。

| 役 | ファイル | sha256 |
|---|---|---|
| 持つ足 | `backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_2017.csv.gz` | `6d84ad5319ae0038401db20d92331838e8f8bef2fcaf749383f6cf7d7dc789f8` |
| 持つ足 | `backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_2018.csv.gz` | `1385d1ebf85b5da0b096957043c2680011854e1265ee0d7558ef9a37959a95df` |
| 持つ足 | `backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_2019.csv.gz` | `07b74645997c6e66c23ba06213261ff6abdf4ca5ebb14cdb5c49689883d6e8a3` |
| 持つ足 | `backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_2020.csv.gz` | `8da834bd5acd192d937ea1293a7ac6d352a09790b1af313dd4142b5aace67a23` |
| 持つ足 | `backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_2021.csv.gz` | `79de9fd56e06d5eb22cc6e3fd719c12eae62b4042619ea304a38b7d447ed3d76` |
| 持つ足 | `backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_2022.csv.gz` | `62b691086660b660dcfcc3906d0293a76e1ecd927f19662380ad8f863291cf56` |
| 持つ足 | `backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_2023.csv.gz` | `d0e7bb576a161059dc0844032bd19ec85f9ab9e082dbfbab538fc70ae84b6a15` |
| binance_close | `backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_2017.csv.gz` | `590178034c6e31b32e63e531804cbb5b2301253bc36eb904e4b45c21829b06a6` |
| binance_close | `backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_2018.csv.gz` | `f66cc2228c3b3b4c78ed418014f323f00690050b7319c57fba83a9e3d2389347` |
| binance_close | `backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_2019.csv.gz` | `ffb1fde499ae1c47f39e1df341d31d9db3cbb138a46bef36e9ed433c5135bb12` |
| binance_close | `backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_2020.csv.gz` | `655ab3497125c7a5bbd1f11cd23c655c29b2788a7916a3f8e6bd2048d98dda34` |
| binance_close | `backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_2021.csv.gz` | `56d016ad19008cb7c56bbe9754a74c32b1b7ce2061b6ae9133dccecb2a7dc859` |
| binance_close | `backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_2022.csv.gz` | `cdc318ee448879f567812cd2bdc4a60964e9e9f3806cf7adaba6e295b52b5ca4` |
| binance_close | `backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_2023.csv.gz` | `1a83012af9283a4dd6952c30c3daf7aa82a31f0ccbf1af46ccfd11a358ac282e` |
| binance_high | `backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_2017.csv.gz` | `590178034c6e31b32e63e531804cbb5b2301253bc36eb904e4b45c21829b06a6` |
| binance_high | `backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_2018.csv.gz` | `f66cc2228c3b3b4c78ed418014f323f00690050b7319c57fba83a9e3d2389347` |
| binance_high | `backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_2019.csv.gz` | `ffb1fde499ae1c47f39e1df341d31d9db3cbb138a46bef36e9ed433c5135bb12` |
| binance_high | `backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_2020.csv.gz` | `655ab3497125c7a5bbd1f11cd23c655c29b2788a7916a3f8e6bd2048d98dda34` |
| binance_high | `backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_2021.csv.gz` | `56d016ad19008cb7c56bbe9754a74c32b1b7ce2061b6ae9133dccecb2a7dc859` |
| binance_high | `backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_2022.csv.gz` | `cdc318ee448879f567812cd2bdc4a60964e9e9f3806cf7adaba6e295b52b5ca4` |
| binance_high | `backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_2023.csv.gz` | `1a83012af9283a4dd6952c30c3daf7aa82a31f0ccbf1af46ccfd11a358ac282e` |
| binance_low | `backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_2017.csv.gz` | `590178034c6e31b32e63e531804cbb5b2301253bc36eb904e4b45c21829b06a6` |
| binance_low | `backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_2018.csv.gz` | `f66cc2228c3b3b4c78ed418014f323f00690050b7319c57fba83a9e3d2389347` |
| binance_low | `backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_2019.csv.gz` | `ffb1fde499ae1c47f39e1df341d31d9db3cbb138a46bef36e9ed433c5135bb12` |
| binance_low | `backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_2020.csv.gz` | `655ab3497125c7a5bbd1f11cd23c655c29b2788a7916a3f8e6bd2048d98dda34` |
| binance_low | `backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_2021.csv.gz` | `56d016ad19008cb7c56bbe9754a74c32b1b7ce2061b6ae9133dccecb2a7dc859` |
| binance_low | `backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_2022.csv.gz` | `cdc318ee448879f567812cd2bdc4a60964e9e9f3806cf7adaba6e295b52b5ca4` |
| binance_low | `backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_2023.csv.gz` | `1a83012af9283a4dd6952c30c3daf7aa82a31f0ccbf1af46ccfd11a358ac282e` |
| binance_open | `backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_2017.csv.gz` | `590178034c6e31b32e63e531804cbb5b2301253bc36eb904e4b45c21829b06a6` |
| binance_open | `backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_2018.csv.gz` | `f66cc2228c3b3b4c78ed418014f323f00690050b7319c57fba83a9e3d2389347` |
| binance_open | `backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_2019.csv.gz` | `ffb1fde499ae1c47f39e1df341d31d9db3cbb138a46bef36e9ed433c5135bb12` |
| binance_open | `backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_2020.csv.gz` | `655ab3497125c7a5bbd1f11cd23c655c29b2788a7916a3f8e6bd2048d98dda34` |
| binance_open | `backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_2021.csv.gz` | `56d016ad19008cb7c56bbe9754a74c32b1b7ce2061b6ae9133dccecb2a7dc859` |
| binance_open | `backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_2022.csv.gz` | `cdc318ee448879f567812cd2bdc4a60964e9e9f3806cf7adaba6e295b52b5ca4` |
| binance_open | `backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_2023.csv.gz` | `1a83012af9283a4dd6952c30c3daf7aa82a31f0ccbf1af46ccfd11a358ac282e` |

## 出力のファイルと sha256

| ファイル | sha256 |
|---|---|
| `a_1m/daily.csv` | `7e9c8e1cc23d097b7ef63b3efec08e5bf1ab675348aa2018646d5862cd22de0d` |
| `a_1m/daily_stats.json` | `165df0ad517931254da66032d32fcdd52176a4799bf7eef48ebb71a1d6bbcec0` |
| `a_1m/diagnostics.json` | `b68686d15ce3b4083fe2e49df1d066a7f8b3f5a75aa972b9e34cc2637966cd67` |
| `a_1m/measure.json` | `6a78dedea673554ede7fa3e59319c973510342c6c37b9b087f4d4d0575e0cd86` |
| `a_1m/week_block.json` | `cb44bf37674afea93a97446d45b48d3545d413372827ec11b10fb4446977dbda` |
| `a_3m/daily.csv` | `4843c3b50c8db35c09a82f230650020a01b11f54035ab82bf317180c312f021f` |
| `a_3m/daily_stats.json` | `ff422791323e9112c1cef7fe14360d58a8b5f6815459f766daf6bccbc4604911` |
| `a_3m/diagnostics.json` | `1e74311c6fee47d29328052eaf2363fa1136d341640d2f8cfc20bf7f1f49bf2f` |
| `a_3m/measure.json` | `61397c7473c926d3ac9547b2f0efaa93cfe31f5fccff330b6c606a1f3cdfa5a9` |
| `a_3m/week_block.json` | `8d8646b92eec60cebc69f1b5184834226f94c20b61c888027cd2f8ff2cea3776` |
| `a_5m/daily.csv` | `612e93a9ac5ba6279af966c617ab98d578f17abc9fa5422ddc23dd7fb7a55934` |
| `a_5m/daily_stats.json` | `a83decf3c8cfcf1c1f89c2df2257ad2ed992866f66bdd59d35a5196eb2e777bf` |
| `a_5m/diagnostics.json` | `aa896f3a10a0d619ac38ea2fcc1463dce1e0bd7404e86447979e034058cdab7d` |
| `a_5m/measure.json` | `44351c550d97a2f36c17359baab49ab9830b6d1a69738921c47eed5ef1be6024` |
| `a_5m/week_block.json` | `de2c9ead979bec18a674bfb9e1e1c506f0fa5e12b6e5ff5b410506a56e5b9e93` |
| `a_15m/daily.csv` | `57137662207445e20b281b7805d2b5d4ad4ad94920fd5f51085449263c613360` |
| `a_15m/daily_stats.json` | `03b39987008e01258f2c35a327119cfa79f8d13528770868a3502ac6a5d7c2f8` |
| `a_15m/diagnostics.json` | `7fae37b0ba6cf3ec515630de67a4a92db730b51fc3dad860524d9101f3a32e7e` |
| `a_15m/measure.json` | `8109a968d434dbef85c204d5e645ef44298dc386d85ad6a9f2748b4eb1ded022` |
| `a_15m/week_block.json` | `2501bcb6735b733be059a761994a1d755070919d51fad200f652d7d46b3c30ac` |
| `a_30m/daily.csv` | `51d5fd2edc767c9a37c11325ba479038fdc7e3f0c4473494ee89f6eb94a5ccef` |
| `a_30m/daily_stats.json` | `4c02a6dc8e952e4bfe575072f6456f905b56f78c7cf5ca21ce96aa237108f62a` |
| `a_30m/diagnostics.json` | `b6b4cecdcbb313c6e98526a404436be4c66de62e73b8c982850eade90cb5848e` |
| `a_30m/measure.json` | `ab12ab7357b2635a101808f0e0cabb6528e2d050992dd1a544736a659fa5e9fa` |
| `a_30m/week_block.json` | `91e07aed3555379f74a5d1dc889f4b26d2ad0f0416a384d2aeadc874f98bb07e` |
| `a_60m/daily.csv` | `3f6ce7c8f6a0a4d750c911e7afd972a071f92f66d1aa91bfe583250225451e01` |
| `a_60m/daily_stats.json` | `10cf9d56c8af9f8280ec161b9a0523eaeaa0399b36d02d7c99c3631dd5ca1ea1` |
| `a_60m/diagnostics.json` | `1da58641f6cc0202a75592bcfccbb0c7390e8d5f063f45d96bac6556081504cc` |
| `a_60m/measure.json` | `27f91ea03cd103ab7382d9a803eef568bc09ccb144b5411bb71f36e987301075` |
| `a_60m/week_block.json` | `1f9f0f574d7a5f507b57c38fccf5856a0cd59181e97217793bd10932a62eac94` |
