# c2_owner_xvenue_wick の測定(W4)

W4 の仕様(`docs/DISCUSSIONS/2026-10-02_W4_spec.md` §3)と W1 の測定器(`src/bot/research/cards/`)で測った記録。
言葉の判定はしない(区間の両端と MDE を並べるだけ。計画 段 2 の訂正)。各数値の意味は `src/bot/research/cards/measure.py` の冒頭の説明のとおり。

## 何をどう走らせたか

- カード: `src/bot/research/cards/library/c2_owner_xvenue_wick.py` の `C2OwnerXvenueWick(series=…, foot_min=…)`。変種 (a) = `SERIES_SPOT`(Binance BTCUSDT 現物)、(b) = `SERIES_UM`(Binance USD-M 先物)、(c) = `SERIES_BITMEX`(BitMEX XBTUSD)。足の長さ 1・3・5・15・30・60 分。
- 出力: `<変種>_<足の長さ>m/`(measure.json・week_block.json・daily.csv・daily_stats.json・diagnostics.json)。(b)・(c) は measure_card を打っていないので、末尾の節「変種 (b)・(c)」のとおり daily.csv・daily_stats.json・diagnostics.json の 3 つだけ。
- 参照 4 系列(始値・高値・安値・終値)は同じファイルから値の列を変えて `load_reference` で読んだ(行の時刻 = `open_time` のまま、lag_ns 60 秒。宣言は CARD.md の測定の設定)。読む範囲は各変種の測る期間 [開始, 終了) の中だけ(開始より前の行は渡していない)。
- 診断(diagnostics.json、INTENT_MAP §7。検定の数に入れない): 枝(19 だけ・24 だけ・両方)ごとのシグナルの数と、決定 t の P_t を「足の終わりが t 以下の最新のシグナル」に帰属させた平均損益。式は各 diagnostics.json の `formula`。
- 測定: `measure_card(CARD.md, run, seed=20261002, control_seed=20261003, regimes=[(開始, "SFD")], daily_path=…/daily.csv)`。vr_q_bars・day_zone・参照の宣言は CARD.md の測定の設定から測定器が読む。制度の変数は 1 値(W4 の仕様 §3: 期間は全部 SFD の時代)。
- 種: ブートストラップ 20261002、対照のずらし 20261003。1 週のブロックの区間も 20261002。
- 1 週のブロックの区間(week_block.json): 同じ P_t の系列に `bot.bt.validation.bootstrap.block_bootstrap_ci`(circular)を L_w = max(ceil(Politis–White b), 10,080 本)・1,000 回・同じ種で当て、全体の平均の 95% 区間・se・MDE(`bot.bt.validation.power.mde`、5% 両側・検出力 80%・sd = se × √n)を出した。照合のため、同じ関数で L = 測定器の L(1 日)でも計算し(`day_recomputed`)、measure.json の区間と並べた。測定器のコードは変えていない。
- 走らせ方: 区切り(暦年)ごとに、その区切りの分だけを封印の門(`bot.bt.data` の load / load_reference)から読んで `run_card` に通し、区切りの記録をつないだ全期間の CardRun に測定器を 1 回当てた(ブートストラップは全期間の系列に 1 回。区切って測定していない)。つなぎ方は台本 `run_v2.py` の冒頭の説明。区切りの一覧は各 measure.json の `w4.chunks`。理由: run_card は核の履歴に届いた事象の写しを全部持つため、全期間を 1 回で走らせるとカード 2 でこの環境の記憶の上限(cgroup の memory.limit_in_bytes = 14,345,035,776 バイト)を超えて止まった(exit 137)。
- 区切って読んだ結果と全期間を一度に読んだ結果の同一性: 下の「照合」。
- 1 変種 = 1 起動。最大 3 本を並列に走らせた(リードの指示 2026-10-02。3 枚共通)。

- 例外 `a_1m`: リードの変更の前に走らせた回で、全期間の足と参照を一度に読み(最大 RSS 7.00GB)、`run_card` だけを暦年で区切って同じカードの物でつないだ(台本 `run_c2_a_as_run.py`・`chunked.py`)。同じ区切りのつなぎ方の 2 週間の照合(`check_chunked.py`、6 つの足の長さ、区切り 3 か所)で持ち高・signal_log・参照の記録がビット一致。所要: 読み込み 502 秒、run_card 1,079 秒、measure_card 1,148 秒、1 週 51 秒(`c2_full.log`)。

## コマンド

リポジトリの直下で(台本は `scratchpad/w4/measure/` に置き、リポジトリには置いていない):

```
PYTHONPATH=src python <scratchpad>/run_v2.py --card c2 --variant a --foot <3|5|15|30|60>
# a_1m(リードの変更の前): PYTHONPATH=src python <scratchpad>/run_c2_a_as_run.py(全期間を一度に読み、run_card を暦年で区切ってつなぐ)
# 済んだ回に日ごとの測定を足す
PYTHONPATH=src python <scratchpad>/add_daily.py c2_owner_xvenue_wick <変種> <scratchpad>/runs/c2_owner_xvenue_wick/<変種>.npz
```

並列(3 枚共通): 同時は最大 3 本。カード 2 を 3 本同時に measure_card に入れたところで a_5m が記憶の上限(cgroup 14,345,035,776 バイト)で止められ(exit 137、12:25Z)、その後は 1 本の最大 RSS の見積もり(カード 2 = 4.3GB・カード 3 = 3.5GB・カード 1 = 3.0GB)の合計 + 2GB が 14.3GB を超えるなら待つ形(`sched3.sh`・`sched4.sh`)にした。
このカード: a_1m はリードの変更の前に 1 本だけで走らせた。a_3m・a_5m・a_15m は `queue.sh 3` で同時に始め、a_5m は上の記憶の上限で止められて最初からやり直した(`sched.sh`)。a_30m は `queue.sh`、a_60m は `sched3.sh`。

## 照合(区切って読む = 全期間を一度に読む)

範囲: 足 60 分の 1 変種だけ、2018-01-01〜2019-01-01 の 1 年だけ、月の境の区切り 11 か所だけで比べた。ほかの足の長さ・ほかの年・本番の走らせの暦年の境の区切りそのものの同一性は、この照合では確かめていない。a_1m は別の経路(`chunked.py`、全期間を一度に読んで run_card だけを区切る)で、その確かめは `check_chunked.py` の 16 日(2017-12-25〜2018-01-10)・足の長さ 6 つ・区切り 3 か所だけ(持ち高・signal_log・参照の記録がビット一致)。
- `check_v2.py c2`: 2018-01-01T00:00:00Z〜2019-01-01T00:00:00Z(1 年)、月の区切り 11 か所、足 521307 本・決定 520293。持ち高の食い違い 0 本(完全一致 True)。 足 60 分、signal_log 一致 True。 所要 907.2 秒、最大 RSS 2.52GB。

## 各回の要約

損益は bp・持ち高 1 単位あたり・経費前。区間は 95%(百分位)。MDE は 5% 両側・検出力 80%。
「1 分ごと」= 1 分ごとの P_t の系列の circular block bootstrap(L = 1,440 本は measure_card、L = 10,080 本は台本の week_block)。「日ごと」= 日ごとの損益の系列(日本時間の日)を日の塊(1 日・5 日)で circular block bootstrap し、1 分あたりに直したもの(daily_stats.json。式はそのファイルの formula)。この表の回は全部 measure_card を打った。対照の百分位 = 持ち高を L 以上ずらした 200 通りの中の位置(measure_card の C5 d)。

| 変種 | 期間 | n(決定) | 日の数 | 平均(1 分あたり) | 平均(1 日あたり) | 1 分ごと L=1440 | 1 分ごと L=10080 | 日ごと 1 日塊 | 日ごと 5 日塊 | MDE(1 分ごと L=1440 / 日ごと 1 日塊) | 持ち高が 0 でない割合 | 変わった回数 | sum\|Δe\| | mean\|Δe\| | 対照の百分位 | 所要(秒) | 最大 RSS(GB) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| a_1m | 2017-08-17〜2023-12-17 | 3251350 | 2313 | 0.0345 | 48.51 | [0.0227, 0.0473] | [0.0219, 0.0471] | [0.0238, 0.0457] | [0.0218, 0.0474] | 0.0173 / 0.0161 | 0.4347 | 86615 | 96331.0 | 0.02963 | 100.0 | 読み込み 502 + run 1079 + 測定 1148 + 1 週 51 | 7.00 |
| a_3m | 2017-08-17〜2023-12-17 | 3251350 | 2313 | 0.0268 | 37.66 | [0.0169, 0.0380] | [0.0162, 0.0371] | [0.0163, 0.0375] | [0.0161, 0.0372] | 0.0152 / 0.0154 | 0.5476 | 82958 | 94869.0 | 0.02918 | 100.0 | 区切りの run 1879 + 測定 1183 + 1 週 52 + 診断 0 | 3.95 |
| a_5m | 2017-08-17〜2023-12-17 | 3251350 | 2313 | 0.0068 | 9.61 | [-0.0040, 0.0185] | [-0.0044, 0.0174] | [-0.0047, 0.0174] | [-0.0054, 0.0179] | 0.0162 / 0.0161 | 0.5947 | 75670 | 87877.0 | 0.02703 | 84.0 | 区切りの run 1814 + 測定 1135 + 1 週 50 + 診断 0 | 4.01 |
| a_15m | 2017-08-17〜2023-12-17 | 3251350 | 2313 | -0.0140 | -19.70 | [-0.0245, -0.0042] | [-0.0251, -0.0021] | [-0.0252, -0.0038] | [-0.0249, -0.0031] | 0.0144 / 0.0148 | 0.6781 | 54772 | 65975.0 | 0.02029 | 0.5 | 区切りの run 1872 + 測定 1186 + 1 週 51 + 診断 0 | 3.96 |
| a_30m | 2017-08-17〜2023-12-17 | 3251350 | 2313 | -0.0106 | -14.86 | [-0.0207, 0.0003] | [-0.0207, -0.0011] | [-0.0206, -0.0005] | [-0.0197, 0.0003] | 0.0147 / 0.0147 | 0.7150 | 38356 | 46809.0 | 0.01440 | 0.0 | 区切りの run 1861 + 測定 1099 + 1 週 55 + 診断 0 | 4.04 |
| a_60m | 2017-08-17〜2023-12-17 | 3251350 | 2313 | -0.0117 | -16.44 | [-0.0221, -0.0016] | [-0.0228, -0.0015] | [-0.0223, -0.0023] | [-0.0219, -0.0018] | 0.0151 / 0.0145 | 0.7473 | 24345 | 30415.0 | 0.00935 | 0.0 | 区切りの run 1888 + 測定 1150 + 1 週 54 + 診断 0 | 4.02 |

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

## 2026-10-02 リードの追記(関門 ② 2 回目の [直す])
- a_1m の経路の同一性の確かめ(`check_chunked.py`、16 日・足の長さ 6 つ・区切り 3 か所)は、**出力を保存していない(記録なし)**。期間と区切りの数は作業者の申告で、コマンドの引数と出力は残っていない。a_1m の同一性は、この記録の範囲では確かめられていないものとして扱う。

## 変種 (b)・(c)(軽い測り方。2026-10-02 リードの委任)

この節の 12 回は、上の (a) の表と測り方が違う。**measure_card を打っていない**(1 分ごとの系列のブートストラップ・持ち高をずらした 200 通りの対照・場面の回帰・1 週の塊の区間はどれも無い。L-556)。上の表の「1 分ごと L=1440」「1 分ごと L=10080」「対照の百分位」に当たる数は (b)(c) には無い。出力は `<回>/daily.csv`・`daily_stats.json`・`diagnostics.json` の 3 つだけ(measure.json・week_block.json は無い)。

### 何をどう走らせたか

- カード: `C2OwnerXvenueWick(series=SERIES_UM, foot_min=…)`(b)・`C2OwnerXvenueWick(series=SERIES_BITMEX, foot_min=…)`(c)。足の長さ 1・3・5・15・30・60 分。
- 期間: (b) 2020-01-01T15:00:00Z〜2023-12-17T15:00:00Z、(c) 2017-08-17T15:00:00Z〜2021-12-31T15:00:00Z(CARD.md の迷った点 9)。
- 参照 4 系列(始値・高値・安値・終値): (b) `backtest_data/binance_um_BTCUSDT_1m_20261002/`、(c) `backtest_data/bitmex_XBTUSD_1m_from1s_20261002/` を、同じファイルから値の列を変えて `load_reference` で読んだ(行の時刻 = `open_time` のまま、lag_ns 60 秒。宣言は CARD.md の測定の設定の binance_um_*・bitmex_* の行)。読む範囲は各変種の期間の中だけ。
- 走らせ方: (a) の a_3m〜a_60m と同じ区切りのつなぎ方(暦年ごとにその区切りの分だけを封印の門 `bot.bt.data` から読み、`run_card` に通して同じカードの物でつなぐ)。台本は `run_v2.py` の写し `run_v2_bc.py` の `--light` の経路。`run_v2.py` との違いは保存の npz に high・low を足した 1 行だけ(下の diff)。
- `--light` の経路が出すもの: 日ごとの損益の系列(日本時間の日)の circular block bootstrap(塊 1 日・5 日、1,000 回、種 20261002、95% 百分位、1 日あたりと 1 分あたり。式は daily_stats.json の formula)、年・曜日(日本時間)・時(日本時間)ごとの平均、持ち高が 0 でない割合と変わった回数(`frequency`)、診断(INTENT_MAP §7 の 19・24 の枝。diagnostics.json)。
- 後から足した数(台本 `post_bc.py`。`--light` が書いた数値は変えていない): sum|Δe| = Σ|e_k − e_{k−1}|、mean|Δe| = sum|Δe| ÷ (決定の数 − 1)(上の (a) の表と同じ式、`extra_nums.py`)、取引の回数/日 = 変わった回数 ÷ 日の数。照合として npz から `pnl.py` で P_t を計算し直した日ごとの合計が daily.csv と同じかを見た(下の表の「日の照合」)。
- 保存の npz(scratchpad の `runs/c2_owner_xvenue_wick/<回>.npz`。リポジトリには置いていない): end_ns・start_ns・open・high・low・close・volume・decided・exposure・signal_log。

### コマンド

リポジトリの直下で(台本は `scratchpad/w4/measure/` に置き、リポジトリには置いていない):

```
PYTHONPATH=src python <scratchpad>/run_v2_bc.py --card c2 --variant <b|c> --foot <1|3|5|15|30|60> --light
PYTHONPATH=src python <scratchpad>/post_bc.py
```

`diff run_v2.py run_v2_bc.py` の出力(全文):

```
332a333
>                             high=run.high, low=run.low,
```

### 並列と記憶

12 回は scratchpad の `run_bc.sh`(1 本目 b_15m)と `run_bc2.sh`(残りの 11 本)で始めた。同時は最大 2 本。1 本を始める前に毎回記憶を読み、「いまの使用量 + 4.3GB(カード 2 の 1 本の見積もり) + 2GB」が 14,345,035,776 バイトを超えるなら `sleep 120` を繰り返して待った。読んだ値と判断はすべて scratchpad の `run_bc.out` にある。

- `run_bc.sh` は使用量を `/sys/fs/cgroup/memory/memory.usage_in_bytes` で読んだ(委任文の `/sys/fs/cgroup/memory.usage_in_bytes` はこの容器に無く、cgroup v1 の同じ名前のファイルを読んだ)。この値はページキャッシュを含む【事実: 15:49:31Z に usage_in_bytes 11,246,530,560、memory.stat の total_cache 8,361,287,680・total_rss 2,885,545,984】。自分の測定が 1 本も走っていない 15:48:40Z の読みでも 9,934,733,312 + 4.3GB + 2GB が上限を超え、待ちが終わらない形になった。
- 15:50:00Z に `run_bc2.sh` に切り替え、委任文の代わりの読み `free -b` の used(buff/cache を含まない)で判定した。usage_in_bytes と total_rss も毎回読んで同じ行に書いた。b_15m が終わった 15:48:38Z から c_15m を始めた 15:50:01Z まで、測定が走っていない時間が 83 秒あった。
- `scratchpad/w4/measure/STOP`(14:33:53Z、リードの前の指示「(b)・(c) はこの回では測らない」で `kill_b.sh` が置いたもの)は消さず、`run_bc.sh`・`run_bc2.sh` は STOP を見ない。

### 照合(区切って読む = 全期間を一度に読む)の範囲

(b)・(c) のデータでは、区切って読んだ結果と全期間を一度に読んだ結果の同一性を**確かめていない**。上の「照合」の `check_v2.py c2` は (a)(SERIES_SPOT に固定)・足 60 分・2018 年の 1 年・月の区切り 11 か所だけである。(b)・(c) は (a) と同じ台本の同じつなぎ方を参照の名前と置き場だけ変えて使った(同じになると考える理由はそれだけで、【推定】)。(c) の 1 分足は約定の無い分に行が無い(CARD.md 迷った点 10)ので、行の抜けがある系列での区切りのつなぎは (a) の照合の範囲の外である。

### 各回の要約

損益は bp・持ち高 1 単位あたり・経費前。区間は 95%(百分位)。MDE は 5% 両側・検出力 80%。「日ごと」は daily_stats.json の `ci.block_1d`・`ci.block_5d`。

| 回 | 期間 | n(決定) | 日の数 | 平均(1 分あたり) | 平均(1 日あたり) | 日ごと 1 日塊(1 分あたり) | 日ごと 5 日塊(1 分あたり) | 日ごと 1 日塊(1 日あたり) | 日ごと 5 日塊(1 日あたり) | MDE(日ごと 1 日塊: 1 分あたり / 1 日あたり) | 持ち高が 0 でない割合 | 変わった回数 | 取引の回数/日 | sum\|Δe\| | mean\|Δe\| | 所要(秒) | 最大 RSS(GB) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| b_1m | 2020-01-01〜2023-12-17 | 2015993 | 1446 | 0.0180 | 25.11 | [0.0061, 0.0290] | [0.0053, 0.0318] | [8.44, 40.44] | [7.31, 44.35] | 0.0166 / 23.11 | 0.4588 | 34297 | 23.72 | 37747.0 | 0.01872 | 区切りの run 1103 + 日ごと 0 + 診断 0 | 2.71 |
| b_3m | 2020-01-01〜2023-12-17 | 2015993 | 1446 | 0.0066 | 9.15 | [-0.0032, 0.0169] | [-0.0035, 0.0159] | [-4.51, 23.61] | [-4.80, 22.21] | 0.0148 / 20.59 | 0.5521 | 40187 | 27.79 | 45807.0 | 0.02272 | 区切りの run 1106 + 日ごと 0 + 診断 0 | 2.88 |
| b_5m | 2020-01-01〜2023-12-17 | 2015993 | 1446 | 0.0024 | 3.31 | [-0.0092, 0.0139] | [-0.0108, 0.0153] | [-12.76, 19.48] | [-15.21, 21.36] | 0.0162 / 22.55 | 0.5965 | 39091 | 27.03 | 45447.0 | 0.02254 | 区切りの run 1106 + 日ごと 0 + 診断 0 | 2.92 |
| b_15m | 2020-01-01〜2023-12-17 | 2015993 | 1446 | -0.0134 | -18.71 | [-0.0253, -0.0015] | [-0.0261, 0.0004] | [-35.24, -2.15] | [-36.51, 0.55] | 0.0172 / 23.96 | 0.6796 | 31555 | 21.82 | 38137.0 | 0.01892 | 区切りの run 1010 + 日ごと 0 + 診断 0 | 2.97 |
| b_30m | 2020-01-01〜2023-12-17 | 2015993 | 1446 | -0.0197 | -27.53 | [-0.0310, -0.0080] | [-0.0320, -0.0075] | [-43.15, -11.19] | [-44.52, -10.39] | 0.0170 / 23.65 | 0.7152 | 22935 | 15.86 | 28114.0 | 0.01395 | 区切りの run 955 + 日ごと 0 + 診断 0 | 2.97 |
| b_60m | 2020-01-01〜2023-12-17 | 2015993 | 1446 | -0.0184 | -25.65 | [-0.0287, -0.0070] | [-0.0294, -0.0081] | [-40.04, -9.76] | [-41.03, -11.26] | 0.0157 / 21.93 | 0.7448 | 14822 | 10.25 | 18533.0 | 0.00919 | 区切りの run 999 + 日ごと 0 + 診断 0 | 2.98 |
| c_1m | 2017-08-17〜2021-12-31 | 2272523 | 1597 | 0.0484 | 68.91 | [0.0328, 0.0650] | [0.0288, 0.0700] | [46.68, 92.56] | [40.97, 99.67] | 0.0228 / 32.41 | 0.4246 | 46550 | 29.15 | 50925.0 | 0.02241 | 区切りの run 1214 + 日ごと 1 + 診断 0 | 2.83 |
| c_3m | 2017-08-17〜2021-12-31 | 2272523 | 1597 | 0.0292 | 41.57 | [0.0148, 0.0430] | [0.0136, 0.0451] | [21.05, 61.16] | [19.34, 64.28] | 0.0200 / 28.40 | 0.5369 | 51871 | 32.48 | 58459.0 | 0.02572 | 区切りの run 1272 + 日ごと 0 + 診断 0 | 2.85 |
| c_5m | 2017-08-17〜2021-12-31 | 2272523 | 1597 | 0.0125 | 17.79 | [-0.0028, 0.0271] | [-0.0046, 0.0295] | [-3.99, 38.60] | [-6.58, 41.86] | 0.0216 / 30.68 | 0.5930 | 48645 | 30.46 | 55655.0 | 0.02449 | 区切りの run 1100 + 日ごと 0 + 診断 0 | 2.90 |
| c_15m | 2017-08-17〜2021-12-31 | 2272523 | 1597 | -0.0240 | -34.15 | [-0.0369, -0.0107] | [-0.0377, -0.0124] | [-52.52, -15.13] | [-53.63, -17.65] | 0.0188 / 26.73 | 0.6709 | 36376 | 22.78 | 43209.0 | 0.01901 | 区切りの run 1250 + 日ごと 0 + 診断 0 | 2.87 |
| c_30m | 2017-08-17〜2021-12-31 | 2272523 | 1597 | -0.0220 | -31.32 | [-0.0367, -0.0086] | [-0.0368, -0.0071] | [-52.23, -12.18] | [-52.38, -10.08] | 0.0199 / 28.31 | 0.7038 | 26097 | 16.34 | 31405.0 | 0.01382 | 区切りの run 1104 + 日ごと 0 + 診断 0 | 2.88 |
| c_60m | 2017-08-17〜2021-12-31 | 2272523 | 1597 | -0.0190 | -27.07 | [-0.0329, -0.0060] | [-0.0334, -0.0065] | [-46.74, -8.58] | [-47.54, -9.27] | 0.0190 / 26.97 | 0.7345 | 16760 | 10.49 | 20713.0 | 0.00911 | 区切りの run 1075 + 日ごと 0 + 診断 0 | 2.87 |

日の照合(npz から計算し直した日ごとの合計と daily.csv)と、npz の high・low の欠け:

| 回 | 日の集合が同じ | 最大の差(bp) | high の NaN | low の NaN | (a) の同じ期間の日の集合と同じ |
|---|---|---|---|---|---|
| b_1m | True | 0.0 | 0 | 0 | True |
| b_3m | True | 0.0 | 0 | 0 | True |
| b_5m | True | 0.0 | 0 | 0 | True |
| b_15m | True | 0.0 | 0 | 0 | True |
| b_30m | True | 0.0 | 0 | 0 | True |
| b_60m | True | 0.0 | 0 | 0 | True |
| c_1m | True | 0.0 | 0 | 0 | True |
| c_3m | True | 0.0 | 0 | 0 | True |
| c_5m | True | 0.0 | 0 | 0 | True |
| c_15m | True | 0.0 | 0 | 0 | True |
| c_30m | True | 0.0 | 0 | 0 | True |
| c_60m | True | 0.0 | 0 | 0 | True |

### 年ごと(日本時間の日の年。1 日あたりの平均 bp / 日の数)

| 回 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 |
|---|---|---|---|---|---|---|---|
| b_1m |  |  |  | 35.14 / 365 | 63.91 / 365 | 6.97 / 365 | -6.82 / 351 |
| (a) 1m・b の期間 |  |  |  | 41.08 / 365 | 67.10 / 365 | 4.80 / 365 | -0.88 / 351 |
| b_3m |  |  |  | -6.59 / 365 | 50.36 / 365 | -8.81 / 365 | 1.34 / 351 |
| (a) 3m・b の期間 |  |  |  | -8.69 / 365 | 64.87 / 365 | 13.42 / 365 | -3.01 / 351 |
| b_5m |  |  |  | -14.52 / 365 | -2.52 / 365 | 19.30 / 365 | 11.28 / 351 |
| (a) 5m・b の期間 |  |  |  | -24.05 / 365 | -34.16 / 365 | 16.57 / 365 | 11.34 / 351 |
| b_15m |  |  |  | -15.87 / 365 | -49.39 / 365 | -19.04 / 365 | 10.57 / 351 |
| (a) 15m・b の期間 |  |  |  | -32.77 / 365 | -43.01 / 365 | -29.04 / 365 | 13.27 / 351 |
| b_30m |  |  |  | -43.66 / 365 | -84.08 / 365 | 14.81 / 365 | 4.01 / 351 |
| (a) 30m・b の期間 |  |  |  | -19.57 / 365 | -74.79 / 365 | 17.74 / 365 | 1.82 / 351 |
| b_60m |  |  |  | -61.10 / 365 | -45.28 / 365 | 0.98 / 365 | 3.93 / 351 |
| (a) 60m・b の期間 |  |  |  | -39.20 / 365 | -54.29 / 365 | -2.79 / 365 | 6.84 / 351 |
| c_1m | 297.41 / 136 | 106.51 / 365 | 30.63 / 365 | 14.86 / 366 | 38.66 / 365 |  |  |
| (a) 1m・c の期間 | 74.55 / 136 | 123.58 / 365 | 44.06 / 365 | 40.79 / 366 | 67.10 / 365 |  |  |
| c_3m | 164.45 / 136 | 96.13 / 365 | 4.68 / 365 | -15.19 / 366 | 35.03 / 365 |  |  |
| (a) 3m・c の期間 | 153.82 / 136 | 87.52 / 365 | 27.37 / 365 | -8.90 / 366 | 64.87 / 365 |  |  |
| c_5m | 204.67 / 136 | 24.59 / 365 | -12.83 / 365 | -0.36 / 366 | -9.83 / 365 |  |  |
| (a) 5m・c の期間 | 85.95 / 136 | 63.85 / 365 | -4.00 / 365 | -24.24 / 366 | -34.16 / 365 |  |  |
| c_15m | -37.36 / 136 | -8.99 / 365 | -16.78 / 365 | -49.29 / 366 | -60.29 / 365 |  |  |
| (a) 15m・c の期間 | 22.02 / 136 | -34.62 / 365 | -6.13 / 365 | -32.91 / 366 | -43.01 / 365 |  |  |
| c_30m | -5.27 / 136 | 11.57 / 365 | -2.34 / 365 | -55.26 / 366 | -88.90 / 365 |  |  |
| (a) 30m・c の期間 | -25.44 / 136 | -13.84 / 365 | 3.83 / 365 | -19.32 / 366 | -74.79 / 365 |  |  |
| c_60m | -61.50 / 136 | 55.68 / 365 | -38.29 / 365 | -60.17 / 366 | -52.57 / 365 |  |  |
| (a) 60m・c の期間 | -43.00 / 136 | 23.82 / 365 | -22.53 / 365 | -38.85 / 366 | -54.29 / 365 |  |  |

### (a) の同じ期間との比べ

(a) の数は `a_<足>/daily.csv`(measure_card が書いた日ごとの合計)の行のうち、日(日本時間)が (b) の期間の日 2020-01-02〜2023-12-17 のものだけから計算した(`post_bc.py`)。区間は daily_stats.py の `_boot` を同じ設定(1 日・5 日の塊、1,000 回、種 20261002)で当てた。持ち高の数(0 でない割合・変わった回数・取引の回数/日・sum|Δe|・mean|Δe|・n(決定))は daily.csv から出せないので、`a_<足>.npz` の決定のうち決定の時刻(足の終わり end_ns)が [2020-01-01T15:00:00Z, 2023-12-17T15:00:00Z) に入るものだけで数えた。(c) の期間(日 2017-08-18〜2021-12-31、[2017-08-17T15:00:00Z, 2021-12-31T15:00:00Z))でも同じものを出した(委任文に無い。並べて読めるように足した)。

| 回 | 期間 | n(決定) | 日の数 | 平均(1 分あたり) | 平均(1 日あたり) | 日ごと 1 日塊(1 分あたり) | 日ごと 5 日塊(1 分あたり) | 日ごと 1 日塊(1 日あたり) | 日ごと 5 日塊(1 日あたり) | MDE(日ごと 1 日塊: 1 分あたり / 1 日あたり) | 持ち高が 0 でない割合 | 変わった回数 | 取引の回数/日 | sum\|Δe\| | mean\|Δe\| | 所要(秒) | 最大 RSS(GB) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| b_1m | 2020-01-01〜2023-12-17 | 2015993 | 1446 | 0.0180 | 25.11 | [0.0061, 0.0290] | [0.0053, 0.0318] | [8.44, 40.44] | [7.31, 44.35] | 0.0166 / 23.11 | 0.4588 | 34297 | 23.72 | 37747.0 | 0.01872 | 区切りの run 1103 + 日ごと 0 + 診断 0 | 2.71 |
| (a) 1m | 2020-01-02〜2023-12-17(日) | 2015994 | 1446 | 0.0203 | 28.31 | [0.0087, 0.0321] | [0.0072, 0.0342] | [12.05, 44.80] | [10.01, 47.69] | 0.0167 / 23.30 | 0.4098 | 33100 | 22.89 | 36387.0 | 0.01805 | — | — |
| b_3m | 2020-01-01〜2023-12-17 | 2015993 | 1446 | 0.0066 | 9.15 | [-0.0032, 0.0169] | [-0.0035, 0.0159] | [-4.51, 23.61] | [-4.80, 22.21] | 0.0148 / 20.59 | 0.5521 | 40187 | 27.79 | 45807.0 | 0.02272 | 区切りの run 1106 + 日ごと 0 + 診断 0 | 2.88 |
| (a) 3m | 2020-01-02〜2023-12-17(日) | 2015994 | 1446 | 0.0121 | 16.84 | [0.0007, 0.0239] | [0.0013, 0.0228] | [1.04, 33.41] | [1.86, 31.83] | 0.0163 / 22.77 | 0.5326 | 38838 | 26.86 | 44189.0 | 0.02192 | — | — |
| b_5m | 2020-01-01〜2023-12-17 | 2015993 | 1446 | 0.0024 | 3.31 | [-0.0092, 0.0139] | [-0.0108, 0.0153] | [-12.76, 19.48] | [-15.21, 21.36] | 0.0162 / 22.55 | 0.5965 | 39091 | 27.03 | 45447.0 | 0.02254 | 区切りの run 1106 + 日ごと 0 + 診断 0 | 2.92 |
| (a) 5m | 2020-01-02〜2023-12-17(日) | 2015994 | 1446 | -0.0056 | -7.76 | [-0.0174, 0.0062] | [-0.0184, 0.0064] | [-24.23, 8.68] | [-25.77, 8.95] | 0.0173 / 24.12 | 0.5856 | 38227 | 26.44 | 44321.0 | 0.02198 | — | — |
| b_15m | 2020-01-01〜2023-12-17 | 2015993 | 1446 | -0.0134 | -18.71 | [-0.0253, -0.0015] | [-0.0261, 0.0004] | [-35.24, -2.15] | [-36.51, 0.55] | 0.0172 / 23.96 | 0.6796 | 31555 | 21.82 | 38137.0 | 0.01892 | 区切りの run 1010 + 日ごと 0 + 診断 0 | 2.97 |
| (a) 15m | 2020-01-02〜2023-12-17(日) | 2015994 | 1446 | -0.0167 | -23.24 | [-0.0271, -0.0053] | [-0.0281, -0.0056] | [-37.87, -7.43] | [-39.41, -7.87] | 0.0166 / 23.21 | 0.6721 | 30940 | 21.40 | 37468.0 | 0.01859 | — | — |
| b_30m | 2020-01-01〜2023-12-17 | 2015993 | 1446 | -0.0197 | -27.53 | [-0.0310, -0.0080] | [-0.0320, -0.0075] | [-43.15, -11.19] | [-44.52, -10.39] | 0.0170 / 23.65 | 0.7152 | 22935 | 15.86 | 28114.0 | 0.01395 | 区切りの run 955 + 日ごと 0 + 診断 0 | 2.97 |
| (a) 30m | 2020-01-02〜2023-12-17(日) | 2015994 | 1446 | -0.0136 | -18.90 | [-0.0241, -0.0015] | [-0.0249, -0.0025] | [-33.66, -2.11] | [-34.53, -3.48] | 0.0166 / 23.11 | 0.7100 | 22711 | 15.71 | 27832.0 | 0.01381 | — | — |
| b_60m | 2020-01-01〜2023-12-17 | 2015993 | 1446 | -0.0184 | -25.65 | [-0.0287, -0.0070] | [-0.0294, -0.0081] | [-40.04, -9.76] | [-41.03, -11.26] | 0.0157 / 21.93 | 0.7448 | 14822 | 10.25 | 18533.0 | 0.00919 | 区切りの run 999 + 日ごと 0 + 診断 0 | 2.98 |
| (a) 60m | 2020-01-02〜2023-12-17(日) | 2015994 | 1446 | -0.0162 | -22.64 | [-0.0277, -0.0052] | [-0.0274, -0.0054] | [-38.60, -7.17] | [-37.93, -7.55] | 0.0165 / 23.02 | 0.7500 | 14602 | 10.10 | 18354.0 | 0.00910 | — | — |
| c_1m | 2017-08-17〜2021-12-31 | 2272523 | 1597 | 0.0484 | 68.91 | [0.0328, 0.0650] | [0.0288, 0.0700] | [46.68, 92.56] | [40.97, 99.67] | 0.0228 / 32.41 | 0.4246 | 46550 | 29.15 | 50925.0 | 0.02241 | 区切りの run 1214 + 日ごと 1 + 診断 0 | 2.83 |
| (a) 1m | 2017-08-18〜2021-12-31(日) | 2272524 | 1597 | 0.0487 | 69.35 | [0.0345, 0.0661] | [0.0325, 0.0654] | [49.07, 94.03] | [46.20, 93.04] | 0.0226 / 32.15 | 0.4509 | 77617 | 48.60 | 86478.0 | 0.03805 | — | — |
| c_3m | 2017-08-17〜2021-12-31 | 2272523 | 1597 | 0.0292 | 41.57 | [0.0148, 0.0430] | [0.0136, 0.0451] | [21.05, 61.16] | [19.34, 64.28] | 0.0200 / 28.40 | 0.5369 | 51871 | 32.48 | 58459.0 | 0.02572 | 区切りの run 1272 + 日ごと 0 + 診断 0 | 2.85 |
| (a) 3m | 2017-08-18〜2021-12-31(日) | 2272524 | 1597 | 0.0366 | 52.14 | [0.0212, 0.0510] | [0.0224, 0.0514] | [30.14, 72.65] | [31.91, 73.27] | 0.0209 / 29.73 | 0.5589 | 71219 | 44.60 | 81724.0 | 0.03596 | — | — |
| c_5m | 2017-08-17〜2021-12-31 | 2272523 | 1597 | 0.0125 | 17.79 | [-0.0028, 0.0271] | [-0.0046, 0.0295] | [-3.99, 38.60] | [-6.58, 41.86] | 0.0216 / 30.68 | 0.5930 | 48645 | 30.46 | 55655.0 | 0.02449 | 区切りの run 1100 + 日ごと 0 + 診断 0 | 2.90 |
| (a) 5m | 2017-08-18〜2021-12-31(日) | 2272524 | 1597 | 0.0054 | 7.64 | [-0.0094, 0.0204] | [-0.0101, 0.0198] | [-13.45, 29.00] | [-14.41, 28.16] | 0.0215 / 30.65 | 0.6021 | 63617 | 39.84 | 74138.0 | 0.03262 | — | — |
| c_15m | 2017-08-17〜2021-12-31 | 2272523 | 1597 | -0.0240 | -34.15 | [-0.0369, -0.0107] | [-0.0377, -0.0124] | [-52.52, -15.13] | [-53.63, -17.65] | 0.0188 / 26.73 | 0.6709 | 36376 | 22.78 | 43209.0 | 0.01901 | 区切りの run 1250 + 日ごと 0 + 診断 0 | 2.87 |
| (a) 15m | 2017-08-18〜2021-12-31(日) | 2272524 | 1597 | -0.0174 | -24.81 | [-0.0310, -0.0029] | [-0.0307, -0.0028] | [-44.04, -4.09] | [-43.71, -3.95] | 0.0199 / 28.33 | 0.6861 | 43693 | 27.36 | 52749.0 | 0.02321 | — | — |
| c_30m | 2017-08-17〜2021-12-31 | 2272523 | 1597 | -0.0220 | -31.32 | [-0.0367, -0.0086] | [-0.0368, -0.0071] | [-52.23, -12.18] | [-52.38, -10.08] | 0.0199 / 28.31 | 0.7038 | 26097 | 16.34 | 31405.0 | 0.01382 | 区切りの run 1104 + 日ごと 0 + 診断 0 | 2.88 |
| (a) 30m | 2017-08-18〜2021-12-31(日) | 2272524 | 1597 | -0.0183 | -25.97 | [-0.0310, -0.0049] | [-0.0310, -0.0050] | [-44.04, -7.01] | [-44.14, -7.16] | 0.0193 / 27.51 | 0.7224 | 29545 | 18.50 | 36193.0 | 0.01593 | — | — |
| c_60m | 2017-08-17〜2021-12-31 | 2272523 | 1597 | -0.0190 | -27.07 | [-0.0329, -0.0060] | [-0.0334, -0.0065] | [-46.74, -8.58] | [-47.54, -9.27] | 0.0190 / 26.97 | 0.7345 | 16760 | 10.49 | 20713.0 | 0.00911 | 区切りの run 1075 + 日ごと 0 + 診断 0 | 2.87 |
| (a) 60m | 2017-08-18〜2021-12-31(日) | 2272524 | 1597 | -0.0173 | -24.68 | [-0.0306, -0.0042] | [-0.0304, -0.0052] | [-43.58, -5.95] | [-43.22, -7.38] | 0.0188 / 26.77 | 0.7539 | 18131 | 11.35 | 22807.0 | 0.01004 | — | — |

n(決定)の 1 の差は期間の端による【事実: 足 15 分で数えた】。(b) の期間では、(a) の daily.csv の 2020-01-02 の日に、決定の時刻 2020-01-01T15:00:00Z(期間の始まりちょうどに終わる足)の P_t が入っている。(b) の走らせはその時刻から始まるのでこの決定が無い。(c) の期間では、(c) の走らせの最後の 2 つの決定は P_t が無い(次の足の始値が無い)が、(a) は期間の後も続くので P_t がある。持ち高の数の n は決定の時刻で切ったので、この差の出方は日ごとの数と同じではない。

### 診断(INTENT_MAP §7。検定の数に入れない)

枝ごとのシグナルの数と、帰属させた決定の P_t の合計 ÷ シグナルの数(bp/シグナル)。式は各 diagnostics.json の formula。

| 回 | シグナルの総数 | 19 の枝だけ(19 bp 以上かつヒゲ > 実体、24 bp 未満): 数 / bp/シグナル | 24 の枝だけ(24 bp 以上、ヒゲ <= 実体): 数 / bp/シグナル | 両方の枝(24 bp 以上かつヒゲ > 実体): 数 / bp/シグナル |
|---|---|---|---|---|
| b_1m | 36003 | 13970 / 0.38 | 5191 / 1.23 | 16842 / 1.46 |
| b_3m | 46255 | 15460 / -0.28 | 7201 / 0.08 | 23594 / 0.72 |
| b_5m | 48005 | 14425 / 0.17 | 8341 / -0.75 | 25239 / 0.34 |
| b_15m | 42069 | 8721 / -0.70 | 9687 / 0.05 | 23661 / -0.91 |
| b_30m | 32302 | 4520 / -1.47 | 8833 / -2.61 | 18949 / -0.53 |
| b_60m | 22214 | 1778 / -3.68 | 7174 / -1.01 | 13262 / -1.76 |
| c_1m | 46285 | 14555 / 1.76 | 8307 / 1.48 | 23423 / 3.08 |
| c_3m | 58448 | 14649 / 0.96 | 11938 / 1.81 | 31861 / 0.97 |
| c_5m | 58904 | 12825 / -0.59 | 13685 / -0.61 | 32394 / 1.37 |
| c_15m | 48656 | 6996 / -0.39 | 13756 / -3.23 | 27904 / -0.26 |
| c_30m | 36900 | 3661 / -0.80 | 11833 / -2.49 | 21406 / -0.82 |
| c_60m | 25119 | 1492 / -1.23 | 8956 / -1.74 | 14671 / -1.76 |

曜日・時間帯(日本時間)ごとの平均は各 `daily_stats.json` の `weekday_jst`(月 = 0)・`hour_jst`。

### 入力のファイルと sha256((b)・(c))

sha256 は封印の門が読んだときに計算した値(門の manifest。走らせた記録 `runs/c2_owner_xvenue_wick/summary_<回>.json` から写した)。12 回で同じファイルの sha256 が食い違ったものは無い(食い違えば下の表に 2 行出る)。

| 役 | ファイル | sha256 |
|---|---|---|
| binance_um_close | `backtest_data/binance_um_BTCUSDT_1m_20261002/binance_um_BTCUSDT_1m_2020.csv.gz` | `2ea050f79edc34a8dd44ba31b024a7955a6e23499ed4ecdd77b5c56a848e4655` |
| binance_um_close | `backtest_data/binance_um_BTCUSDT_1m_20261002/binance_um_BTCUSDT_1m_2021.csv.gz` | `94076ccd75bd7bbc49ef5e623e7c8d7457ebd0c0a98bb3ebedfec642ef1d1ca3` |
| binance_um_close | `backtest_data/binance_um_BTCUSDT_1m_20261002/binance_um_BTCUSDT_1m_2022.csv.gz` | `ddae7954bacef08135500b92ee390394126ff8885f653d73b0f097941d4b750f` |
| binance_um_close | `backtest_data/binance_um_BTCUSDT_1m_20261002/binance_um_BTCUSDT_1m_2023.csv.gz` | `13cef357910e5d6c47528af4fdad18fa2ec6df7e29942ab680f4d797a8311282` |
| binance_um_high | `backtest_data/binance_um_BTCUSDT_1m_20261002/binance_um_BTCUSDT_1m_2020.csv.gz` | `2ea050f79edc34a8dd44ba31b024a7955a6e23499ed4ecdd77b5c56a848e4655` |
| binance_um_high | `backtest_data/binance_um_BTCUSDT_1m_20261002/binance_um_BTCUSDT_1m_2021.csv.gz` | `94076ccd75bd7bbc49ef5e623e7c8d7457ebd0c0a98bb3ebedfec642ef1d1ca3` |
| binance_um_high | `backtest_data/binance_um_BTCUSDT_1m_20261002/binance_um_BTCUSDT_1m_2022.csv.gz` | `ddae7954bacef08135500b92ee390394126ff8885f653d73b0f097941d4b750f` |
| binance_um_high | `backtest_data/binance_um_BTCUSDT_1m_20261002/binance_um_BTCUSDT_1m_2023.csv.gz` | `13cef357910e5d6c47528af4fdad18fa2ec6df7e29942ab680f4d797a8311282` |
| binance_um_low | `backtest_data/binance_um_BTCUSDT_1m_20261002/binance_um_BTCUSDT_1m_2020.csv.gz` | `2ea050f79edc34a8dd44ba31b024a7955a6e23499ed4ecdd77b5c56a848e4655` |
| binance_um_low | `backtest_data/binance_um_BTCUSDT_1m_20261002/binance_um_BTCUSDT_1m_2021.csv.gz` | `94076ccd75bd7bbc49ef5e623e7c8d7457ebd0c0a98bb3ebedfec642ef1d1ca3` |
| binance_um_low | `backtest_data/binance_um_BTCUSDT_1m_20261002/binance_um_BTCUSDT_1m_2022.csv.gz` | `ddae7954bacef08135500b92ee390394126ff8885f653d73b0f097941d4b750f` |
| binance_um_low | `backtest_data/binance_um_BTCUSDT_1m_20261002/binance_um_BTCUSDT_1m_2023.csv.gz` | `13cef357910e5d6c47528af4fdad18fa2ec6df7e29942ab680f4d797a8311282` |
| binance_um_open | `backtest_data/binance_um_BTCUSDT_1m_20261002/binance_um_BTCUSDT_1m_2020.csv.gz` | `2ea050f79edc34a8dd44ba31b024a7955a6e23499ed4ecdd77b5c56a848e4655` |
| binance_um_open | `backtest_data/binance_um_BTCUSDT_1m_20261002/binance_um_BTCUSDT_1m_2021.csv.gz` | `94076ccd75bd7bbc49ef5e623e7c8d7457ebd0c0a98bb3ebedfec642ef1d1ca3` |
| binance_um_open | `backtest_data/binance_um_BTCUSDT_1m_20261002/binance_um_BTCUSDT_1m_2022.csv.gz` | `ddae7954bacef08135500b92ee390394126ff8885f653d73b0f097941d4b750f` |
| binance_um_open | `backtest_data/binance_um_BTCUSDT_1m_20261002/binance_um_BTCUSDT_1m_2023.csv.gz` | `13cef357910e5d6c47528af4fdad18fa2ec6df7e29942ab680f4d797a8311282` |
| bitmex_close | `backtest_data/bitmex_XBTUSD_1m_from1s_20261002/bitmex_XBTUSD_1m_2017.csv.gz` | `ba97948a88dabe7172527f4bc4a8f6190ee379d31cd8078f236bbe920017cda7` |
| bitmex_close | `backtest_data/bitmex_XBTUSD_1m_from1s_20261002/bitmex_XBTUSD_1m_2018.csv.gz` | `9019ddb27bb482e6f12fdd721abd0ef442114c1f80f1b5c742896150ba3a2b96` |
| bitmex_close | `backtest_data/bitmex_XBTUSD_1m_from1s_20261002/bitmex_XBTUSD_1m_2019.csv.gz` | `fbe87867608a8131b336a9f6907424c0d4b1211eeb1709b20c36861b4465fc03` |
| bitmex_close | `backtest_data/bitmex_XBTUSD_1m_from1s_20261002/bitmex_XBTUSD_1m_2020.csv.gz` | `6d50714dabeccb73732098b09a082fff70249885229f725a5cbc52501e0023eb` |
| bitmex_close | `backtest_data/bitmex_XBTUSD_1m_from1s_20261002/bitmex_XBTUSD_1m_2021.csv.gz` | `7161314b54c4cd61ddba588ab2ee71bb6fc042c5552f63fdf801b1cce58d05e2` |
| bitmex_high | `backtest_data/bitmex_XBTUSD_1m_from1s_20261002/bitmex_XBTUSD_1m_2017.csv.gz` | `ba97948a88dabe7172527f4bc4a8f6190ee379d31cd8078f236bbe920017cda7` |
| bitmex_high | `backtest_data/bitmex_XBTUSD_1m_from1s_20261002/bitmex_XBTUSD_1m_2018.csv.gz` | `9019ddb27bb482e6f12fdd721abd0ef442114c1f80f1b5c742896150ba3a2b96` |
| bitmex_high | `backtest_data/bitmex_XBTUSD_1m_from1s_20261002/bitmex_XBTUSD_1m_2019.csv.gz` | `fbe87867608a8131b336a9f6907424c0d4b1211eeb1709b20c36861b4465fc03` |
| bitmex_high | `backtest_data/bitmex_XBTUSD_1m_from1s_20261002/bitmex_XBTUSD_1m_2020.csv.gz` | `6d50714dabeccb73732098b09a082fff70249885229f725a5cbc52501e0023eb` |
| bitmex_high | `backtest_data/bitmex_XBTUSD_1m_from1s_20261002/bitmex_XBTUSD_1m_2021.csv.gz` | `7161314b54c4cd61ddba588ab2ee71bb6fc042c5552f63fdf801b1cce58d05e2` |
| bitmex_low | `backtest_data/bitmex_XBTUSD_1m_from1s_20261002/bitmex_XBTUSD_1m_2017.csv.gz` | `ba97948a88dabe7172527f4bc4a8f6190ee379d31cd8078f236bbe920017cda7` |
| bitmex_low | `backtest_data/bitmex_XBTUSD_1m_from1s_20261002/bitmex_XBTUSD_1m_2018.csv.gz` | `9019ddb27bb482e6f12fdd721abd0ef442114c1f80f1b5c742896150ba3a2b96` |
| bitmex_low | `backtest_data/bitmex_XBTUSD_1m_from1s_20261002/bitmex_XBTUSD_1m_2019.csv.gz` | `fbe87867608a8131b336a9f6907424c0d4b1211eeb1709b20c36861b4465fc03` |
| bitmex_low | `backtest_data/bitmex_XBTUSD_1m_from1s_20261002/bitmex_XBTUSD_1m_2020.csv.gz` | `6d50714dabeccb73732098b09a082fff70249885229f725a5cbc52501e0023eb` |
| bitmex_low | `backtest_data/bitmex_XBTUSD_1m_from1s_20261002/bitmex_XBTUSD_1m_2021.csv.gz` | `7161314b54c4cd61ddba588ab2ee71bb6fc042c5552f63fdf801b1cce58d05e2` |
| bitmex_open | `backtest_data/bitmex_XBTUSD_1m_from1s_20261002/bitmex_XBTUSD_1m_2017.csv.gz` | `ba97948a88dabe7172527f4bc4a8f6190ee379d31cd8078f236bbe920017cda7` |
| bitmex_open | `backtest_data/bitmex_XBTUSD_1m_from1s_20261002/bitmex_XBTUSD_1m_2018.csv.gz` | `9019ddb27bb482e6f12fdd721abd0ef442114c1f80f1b5c742896150ba3a2b96` |
| bitmex_open | `backtest_data/bitmex_XBTUSD_1m_from1s_20261002/bitmex_XBTUSD_1m_2019.csv.gz` | `fbe87867608a8131b336a9f6907424c0d4b1211eeb1709b20c36861b4465fc03` |
| bitmex_open | `backtest_data/bitmex_XBTUSD_1m_from1s_20261002/bitmex_XBTUSD_1m_2020.csv.gz` | `6d50714dabeccb73732098b09a082fff70249885229f725a5cbc52501e0023eb` |
| bitmex_open | `backtest_data/bitmex_XBTUSD_1m_from1s_20261002/bitmex_XBTUSD_1m_2021.csv.gz` | `7161314b54c4cd61ddba588ab2ee71bb6fc042c5552f63fdf801b1cce58d05e2` |
| 持つ足 | `backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_2017.csv.gz` | `6d84ad5319ae0038401db20d92331838e8f8bef2fcaf749383f6cf7d7dc789f8` |
| 持つ足 | `backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_2018.csv.gz` | `1385d1ebf85b5da0b096957043c2680011854e1265ee0d7558ef9a37959a95df` |
| 持つ足 | `backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_2019.csv.gz` | `07b74645997c6e66c23ba06213261ff6abdf4ca5ebb14cdb5c49689883d6e8a3` |
| 持つ足 | `backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_2020.csv.gz` | `8da834bd5acd192d937ea1293a7ac6d352a09790b1af313dd4142b5aace67a23` |
| 持つ足 | `backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_2021.csv.gz` | `79de9fd56e06d5eb22cc6e3fd719c12eae62b4042619ea304a38b7d447ed3d76` |
| 持つ足 | `backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_2022.csv.gz` | `62b691086660b660dcfcc3906d0293a76e1ecd927f19662380ad8f863291cf56` |
| 持つ足 | `backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_2023.csv.gz` | `d0e7bb576a161059dc0844032bd19ec85f9ab9e082dbfbab538fc70ae84b6a15` |

### 出力のファイルと sha256((b)・(c))

| ファイル | sha256 |
|---|---|
| `b_1m/daily.csv` | `51f6b50acecc93a3d0ef989e412083fcdb75c63454a6d4d4df7f3a49ab814b57` |
| `b_1m/daily_stats.json` | `4e100d148605d4d3121c208f47295b7bb53814d0d9a89ea873418f8473d62ca3` |
| `b_1m/diagnostics.json` | `861639d2639d562f88907e6936ce695f9e9dde3a27418942c61c79ff910b4586` |
| `b_3m/daily.csv` | `d70d053348df8c320ffb8b159fd844819bfaa94f1554505f81151f81e543ee48` |
| `b_3m/daily_stats.json` | `fb367a74458ca0f60c5b1446c35b0b039dd42df5c25151e3d646851ad4359592` |
| `b_3m/diagnostics.json` | `0b495be8869167b8a3f2491c209fc21dfdd9fc055a31a7258ea844aa681922df` |
| `b_5m/daily.csv` | `706c3c2b98a43e86ba87d54e543946a379511ba25c52e7ce7b7a0cf275a7bf78` |
| `b_5m/daily_stats.json` | `8d9749921953ffe027fc947886c8f33b9adb1989ad444043a538aa16e50ddc89` |
| `b_5m/diagnostics.json` | `97950eb8ce5c8647702304d2039487868d60ec9a89deed655af6932b3598f0d3` |
| `b_15m/daily.csv` | `1de07323c9d1e2debb24b7fb733a321e325341687837b08503ee426890aa039b` |
| `b_15m/daily_stats.json` | `42cac4d27fd2b0b81ae307e7fb4b084b1a73dee182ecd1ae7b764da03c349fc0` |
| `b_15m/diagnostics.json` | `2a494375238e2b142da52bf3c383d12cad7fb235a8146439483486861ab34269` |
| `b_30m/daily.csv` | `91f4ceaa65ebba97758f7305798ed86f3fd688a10db4288678091b6d014f1f4a` |
| `b_30m/daily_stats.json` | `d6ddbeeb1e660137aa07916ea44c470484bf1f638cf6bd63f7590cbac006763c` |
| `b_30m/diagnostics.json` | `1cccfcc04bb8a2f01d2881a8d3935169b8af585f7d76906bff5967143a4300a9` |
| `b_60m/daily.csv` | `845acadba332e04797d34990f1875a4fc7d0e62d7245ad8ec3697c66439f130c` |
| `b_60m/daily_stats.json` | `3ff0619ab1dc3f0e393806696cebdcb87b2e2f67ea631785888f66d89f2aff6d` |
| `b_60m/diagnostics.json` | `dc631927fcf9252c1af1b58f31a786bbc80eb24c51ed5cad25f22bdab9604890` |
| `c_1m/daily.csv` | `b09f376ca4c942b7068e6303bb8aafa194a00f2c1445b8425ce2f23722562fd8` |
| `c_1m/daily_stats.json` | `7e52c9e0bf52d7ea976a8e3f98b6b553a146d36d99328f9b211654827056f8a6` |
| `c_1m/diagnostics.json` | `aeb39be60e9580e1d3cd07948c70a8094120dc7b93c6fd34cbb0d54dfe8a8db9` |
| `c_3m/daily.csv` | `92ed7e5ff4541c2d5721e3bba469aec52cd2dcf6960f49ec64a1449041c0ed82` |
| `c_3m/daily_stats.json` | `ea3417a0f18c9e33dadc98d4f995562d566abc34995c53ac879e7643f9e263b4` |
| `c_3m/diagnostics.json` | `2d2969073c6a35fc37813dd04febdc2a1685f1836e225bc0b448411a800ecb95` |
| `c_5m/daily.csv` | `53e7ce64b1e00ecd72aee0466ba8c04434b66c9c40836caa2c5628a93e6f399a` |
| `c_5m/daily_stats.json` | `46c751da5c9c1092f40f9a795b4a974fddb0f8f573bd236f9b24c01c65c0cb7c` |
| `c_5m/diagnostics.json` | `2dfbb66816eb40950b88a9f6fa1a655495f34417cef6eb72bd7b7ceecbf5a567` |
| `c_15m/daily.csv` | `32d6af860e012713103fced833e81539b28fd82c9332a40cb215805ca60d3474` |
| `c_15m/daily_stats.json` | `60d2722c76e8bede53f550cae3dc6a06cc9b48abe3318a9aeed5cf4f43528d48` |
| `c_15m/diagnostics.json` | `dead893c7acca376fa8de040493321bbf7d53585ba8a44195107faed7e0f3ec3` |
| `c_30m/daily.csv` | `bc547dbc4da5e757bc7e3bc266beff6a18020ad25b70d608ca2592450fb91e0b` |
| `c_30m/daily_stats.json` | `e76ad026a12afd5bba293eb266dd01868a690a74ae2bfaa04d1c9232557bb5c0` |
| `c_30m/diagnostics.json` | `57ec8ce6aaedb4758bab91109dcf2519b1e220037cd376ac8eb3046969c670b8` |
| `c_60m/daily.csv` | `03985f3160f3c308ae1bdad5d6aa3e0a1f1576532392fbe4cd0e9ce25de198bb` |
| `c_60m/daily_stats.json` | `05304582966499e17a4ee22f477a88ccee9f4edabbfc340f646739ba36221bf2` |
| `c_60m/diagnostics.json` | `1a1579821f09f0aa052ee20714536959f48aebbd8b20d08a19f51b4198e615fe` |

## 関門 ② の監査の後の追記(2026-10-03、数値は変えていない)

- (b) の最初の 2 回 `c2_b_1m`(14:29:43Z 開始)・`c2_b_3m`(14:33:43Z 開始)は途中で止めて捨てた(どちらも exit 143、14:33:53Z。`scratchpad/w4/measure/jobs/c2_b_1m.log`・`c2_b_3m.log`)。結果への混入は無い。(b) の最終出力はその後の `.bc.log` の回(`summary_b_1m.json` 16:13:32Z、`summary_b_3m.json` 16:37:39Z)。
- (b)(c) の区切りの同一性は確かめていない(上の「照合の範囲」)。オーナーへの報告では未確認として扱う。
