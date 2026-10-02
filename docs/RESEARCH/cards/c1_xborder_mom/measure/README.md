# c1_xborder_mom の測定(W4)

W4 の仕様(`docs/DISCUSSIONS/2026-10-02_W4_spec.md` §3)と W1 の測定器(`src/bot/research/cards/`)で測った記録。
言葉の判定はしない(区間の両端と MDE を並べるだけ。計画 段 2 の訂正)。各数値の意味は `src/bot/research/cards/measure.py` の冒頭の説明のとおり。

## 何をどう走らせたか

- カード: `src/bot/research/cards/library/c1_xborder_mom.py` の `XborderMom()`(引数なし、既定値)。リードの追加の 1 回。
- 出力: `default/`(measure.json・week_block.json・daily.csv・daily_stats.json。診断の項目は無い)。
- 入力の読み方は `scratchpad/w4/c1_rewrite/compare.py` と同じ(区切りごとに新しいカードを作り、慣らしの分を渡し、区切りの中の足だけを使う)。最初の区切りは足を測る期間の始まり(2017-08-17T15:00Z)から、Binance の行をその 1 日前(2017-08-16T15:00Z)から読んだ。つまり測る期間の始まりより前の Binance の行を 1 日分読んでいる。2 つ目以降の区切りは、足を区切りの 1 日前から、Binance の行を区切りの 2 日前から読んだ(どれも測る期間の中)。封印(2023-12-18 00:00Z 以降)には触れていない(読む範囲の終わりは 2023-12-17T15:00Z)。
- 測定: `measure_card(CARD.md, run, seed=20261002, control_seed=20261003, regimes=[(開始, "SFD")], daily_path=…/daily.csv)`。vr_q_bars・day_zone・参照の宣言は CARD.md の測定の設定から測定器が読む。制度の変数は 1 値(W4 の仕様 §3: 期間は全部 SFD の時代)。
- 種: ブートストラップ 20261002、対照のずらし 20261003。1 週のブロックの区間も 20261002。
- 1 週のブロックの区間(week_block.json): 同じ P_t の系列に `bot.bt.validation.bootstrap.block_bootstrap_ci`(circular)を L_w = max(ceil(Politis–White b), 10,080 本)・1,000 回・同じ種で当て、全体の平均の 95% 区間・se・MDE(`bot.bt.validation.power.mde`、5% 両側・検出力 80%・sd = se × √n)を出した。照合のため、同じ関数で L = 測定器の L(1 日)でも計算し(`day_recomputed`)、measure.json の区間と並べた。測定器のコードは変えていない。
- 走らせ方: 区切り(暦年)ごとに、その区切りの分だけを封印の門(`bot.bt.data` の load / load_reference)から読んで `run_card` に通し、区切りの記録をつないだ全期間の CardRun に測定器を 1 回当てた(ブートストラップは全期間の系列に 1 回。区切って測定していない)。つなぎ方は台本 `run_v2.py` の冒頭の説明。区切りの一覧は各 measure.json の `w4.chunks`。理由: run_card は核の履歴に届いた事象の写しを全部持つため、全期間を 1 回で走らせるとカード 2 でこの環境の記憶の上限(cgroup の memory.limit_in_bytes = 14,345,035,776 バイト)を超えて止まった(exit 137)。
- 区切って読んだ結果と全期間を一度に読んだ結果の同一性: 下の「照合」。
- 1 変種 = 1 起動。最大 3 本を並列に走らせた(リードの指示 2026-10-02。3 枚共通)。

## コマンド

リポジトリの直下で(台本は `scratchpad/w4/measure/` に置き、リポジトリには置いていない):

```
PYTHONPATH=src python <scratchpad>/run_v2.py --card c1
PYTHONPATH=src python <scratchpad>/add_daily.py c1_xborder_mom default <scratchpad>/runs/c1_xborder_mom/default.npz
```

並列(3 枚共通): 同時は最大 3 本。カード 2 を 3 本同時に measure_card に入れたところで a_5m が記憶の上限(cgroup 14,345,035,776 バイト)で止められ(exit 137、12:25Z)、その後は 1 本の最大 RSS の見積もり(カード 2 = 4.3GB・カード 3 = 3.5GB・カード 1 = 3.0GB)の合計 + 2GB が 14.3GB を超えるなら待つ形(`sched3.sh`・`sched4.sh`)にした。
このカード: default は `sched3.sh` で 13:53Z に始まり 14:33Z に終わった(カード 3 の回と同時に走った)。

## 照合(区切って読む = 全期間を一度に読む)

範囲: default の 1 変種だけ、2018-01-01〜2019-01-01 の 1 年だけ、月の境の区切り 11 か所だけで比べた。本番の走らせの暦年の境の区切りそのもの、ほかの年の同一性はこの照合では確かめていない。
- `check_v2.py c1`: 2018-01-01T00:00:00Z〜2019-01-01T00:00:00Z(1 年)、月の区切り 11 か所、足 521307 本・決定 520293。持ち高の食い違い 0 本(完全一致 True)。 所要 486.7 秒、最大 RSS 1.35GB。

## 各回の要約

損益は bp・持ち高 1 単位あたり・経費前。区間は 95%(百分位)。MDE は 5% 両側・検出力 80%。
「1 分ごと」= 1 分ごとの P_t の系列の circular block bootstrap(L = 1,440 本は measure_card、L = 10,080 本は台本の week_block)。「日ごと」= 日ごとの損益の系列(日本時間の日)を日の塊(1 日・5 日)で circular block bootstrap し、1 分あたりに直したもの(daily_stats.json。式はそのファイルの formula)。この表の回は全部 measure_card を打った。対照の百分位 = 持ち高を L 以上ずらした 200 通りの中の位置(measure_card の C5 d)。

| 変種 | 期間 | n(決定) | 日の数 | 平均(1 分あたり) | 平均(1 日あたり) | 1 分ごと L=1440 | 1 分ごと L=10080 | 日ごと 1 日塊 | 日ごと 5 日塊 | MDE(1 分ごと L=1440 / 日ごと 1 日塊) | 持ち高が 0 でない割合 | 変わった回数 | sum\|Δe\| | mean\|Δe\| | 対照の百分位 | 所要(秒) | 最大 RSS(GB) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| default | 2017-08-17〜2023-12-17 | 3251350 | 2313 | 0.0177 | 24.84 | [0.0079, 0.0279] | [0.0062, 0.0297] | [0.0077, 0.0271] | [0.0063, 0.0290] | 0.0145 / 0.0143 | 0.2232 | 41902 | 46212.0 | 0.01421 | 100.0 | 区切りの run 1154 + 測定 1195 + 1 週 55 + 診断 0 | 2.09 |

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
| binance_btcusdt_close | `backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_2017.csv.gz` | `590178034c6e31b32e63e531804cbb5b2301253bc36eb904e4b45c21829b06a6` |
| binance_btcusdt_close | `backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_2018.csv.gz` | `f66cc2228c3b3b4c78ed418014f323f00690050b7319c57fba83a9e3d2389347` |
| binance_btcusdt_close | `backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_2019.csv.gz` | `ffb1fde499ae1c47f39e1df341d31d9db3cbb138a46bef36e9ed433c5135bb12` |
| binance_btcusdt_close | `backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_2020.csv.gz` | `655ab3497125c7a5bbd1f11cd23c655c29b2788a7916a3f8e6bd2048d98dda34` |
| binance_btcusdt_close | `backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_2021.csv.gz` | `56d016ad19008cb7c56bbe9754a74c32b1b7ce2061b6ae9133dccecb2a7dc859` |
| binance_btcusdt_close | `backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_2022.csv.gz` | `cdc318ee448879f567812cd2bdc4a60964e9e9f3806cf7adaba6e295b52b5ca4` |
| binance_btcusdt_close | `backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_2023.csv.gz` | `1a83012af9283a4dd6952c30c3daf7aa82a31f0ccbf1af46ccfd11a358ac282e` |

## 出力のファイルと sha256

| ファイル | sha256 |
|---|---|
| `default/daily.csv` | `6f25e2cec7c87fdd74b23de4776b7e626a7a51cc018f8b2426ff18d42c97e2a5` |
| `default/daily_stats.json` | `a7a5044cf3e30af915747b5c37dc73f9786aa05d9ba6b048cb9e3d82ccc2a904` |
| `default/measure.json` | `f78710853600664586a69cc63745552b98101707e33aedba35688a7dff1ca860` |
| `default/week_block.json` | `f7ab2fc18dc17fc6e62170d337f97667f87ff47279d94ff9b4300192b45c3cbd` |
