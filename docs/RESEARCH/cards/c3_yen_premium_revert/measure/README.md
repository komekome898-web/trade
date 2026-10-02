# c3_yen_premium_revert の測定(W4)

W4 の仕様(`docs/DISCUSSIONS/2026-10-02_W4_spec.md` §3)と W1 の測定器(`src/bot/research/cards/`)で測った記録。
言葉の判定はしない(区間の両端と MDE を並べるだけ。計画 段 2 の訂正)。各数値の意味は `src/bot/research/cards/measure.py` の冒頭の説明のとおり。

## 何をどう走らせたか

- カード: `src/bot/research/cards/library/c3_yen_premium_revert.py` の `YenPremiumRevert(window)`(窓 1h・1d・1w)。
- 出力: `1h/`・`1d/`(measure.json・week_block.json・daily.csv・daily_stats.json・diagnostics.json)、`1w/`(daily.csv・daily_stats.json・diagnostics.json の 3 つ)。1w に measure.json と week_block.json が無い理由: 1w の測定に入る前に、リードの測り方の変更(2026-10-02「1 分ごとの系列に掛ける重い measure_card は打たない」)が届いたため、measure_card と 1 週のブロックの区間を打たず、日ごとの系列からの測定(daily_stats.json)だけを出した。1h・1d と並べられる数は daily_stats.json の日ごとの区間・年ごと・曜日・時間帯と、diagnostics.json。
- 参照: `binance_btcusdt_close`(Binance BTCUSDT の close、行の時刻 = `open_time`)と `usdjpy_close`(USDJPY の BID の close、行の時刻 = `timestamp`)。どちらも置き場の時刻のまま、lag_ns 60 秒(CARD.md の測定の設定)。
- 診断(diagnostics.json、INTENT_MAP §4 の 4-1(4)・4-2・4-3・4-4・4-6・4-7。検定の数に入れない): カードと同じ手順を台本で書き直し(`run_c3.py` の `premiums`・`positions`)、全決定でカードの持ち高とビット一致することを確かめてから計算した(`check.reimplementation_equals_card_exposure`)。式は各 diagnostics.json の `formula`。
- **4-1(4)(現物で作った上乗せ)は出していない**: bitFlyer 現物 BTC_JPY の 1 分足を封印の門(`bot.bt.data.load`、kind bar)が拒んだため(各 diagnostics.json の `4-1(4).not_computed`、`gate_error`: `backtest_data/bitflyer_lightchart_BTC_JPY_1m_20260906/candles_1m_2018.csv.gz` line 47222: bar invariant violated、open=high=low=912511.0 close=912515.0)。現物の足は測定にも診断にも使っていない(下の入力表にも載せない)。
- 4-3 の注: Δp は close_t → close_{次の決定} の対数の動き、P_t は open_{t+1} → open_{t+2} の動きで、区間がずれる。そのずれの一部 mean(e_t × (open_{t+1} / close_t − 1)) × 10,000 は 1h 0.1085bp・1d 0.0467bp・1w 0.0270bp(scratchpad の extra_nums.py、保存した npz から計算)。このため 4-3 の「mean(e×Δp) − P_t」をそのまま「海外の側で寄った分」と読まない。
- 1h・1d は測り直した回: 最初の起動(1h は 13:16Z 開始、診断の現物の足の読み込みで門に拒まれて止まった。1d は 13:24Z 開始、測定の途中で止めた)が、区切りの run_card の後・測定の前に保存した npz(scratchpad の `runs/c3_yen_premium_revert/1h.npz` 13:34Z・`1d.npz` 13:42Z 保存)から、測定と診断をやり直した(`--from-npz`)。npz を作ったときの区切りの記録は `jobs/c3_1h.gatefail.log`・`jobs/c3_1d.killed.log` の 3〜9 行(区切りごとの足と参照の行の数)。1w は区切りの run_card の起動(`jobs/c3_1w.runonly.log`、1,087 秒)が保存した npz(14:34Z)から、日ごとの測定と診断だけを出した(measure_card は打っていない)。
- 測定: `measure_card(CARD.md, run, seed=20261002, control_seed=20261003, regimes=[(開始, "SFD")], daily_path=…/daily.csv)`。vr_q_bars・day_zone・参照の宣言は CARD.md の測定の設定から測定器が読む。制度の変数は 1 値(W4 の仕様 §3: 期間は全部 SFD の時代)。
- measure_card と 1 週のブロックの区間は 1h・1d だけ。1w は打っていない(リードの測り方の変更 2026-10-02 の後の回)。
- 種: ブートストラップ 20261002、対照のずらし 20261003。1 週のブロックの区間も 20261002。
- 1 週のブロックの区間(week_block.json): 同じ P_t の系列に `bot.bt.validation.bootstrap.block_bootstrap_ci`(circular)を L_w = max(ceil(Politis–White b), 10,080 本)・1,000 回・同じ種で当て、全体の平均の 95% 区間・se・MDE(`bot.bt.validation.power.mde`、5% 両側・検出力 80%・sd = se × √n)を出した。照合のため、同じ関数で L = 測定器の L(1 日)でも計算し(`day_recomputed`)、measure.json の区間と並べた。測定器のコードは変えていない。
- 走らせ方: 区切り(暦年)ごとに、その区切りの分だけを封印の門(`bot.bt.data` の load / load_reference)から読んで `run_card` に通し、区切りの記録をつないだ全期間の CardRun に測定器を 1 回当てた(ブートストラップは全期間の系列に 1 回。区切って測定していない)。つなぎ方は台本 `run_v2.py` の冒頭の説明。区切りの一覧は各 measure.json の `w4.chunks`。理由: run_card は核の履歴に届いた事象の写しを全部持つため、全期間を 1 回で走らせるとカード 2 でこの環境の記憶の上限(cgroup の memory.limit_in_bytes = 14,345,035,776 バイト)を超えて止まった(exit 137)。
- 区切って読んだ結果と全期間を一度に読んだ結果の同一性: 下の「照合」。
- 1 変種 = 1 起動。最大 3 本を並列に走らせた(リードの指示 2026-10-02。3 枚共通)。

## コマンド

リポジトリの直下で(台本は `scratchpad/w4/measure/` に置き、リポジトリには置いていない):

```
PYTHONPATH=src python <scratchpad>/run_v2.py --card c3 --window <1h|1d|1w>
# 1h・1d: 区切りの run の起動が保存した npz から測定と診断をやり直した
PYTHONPATH=src python <scratchpad>/run_v2.py --card c3 --window <1h|1d> --from-npz <scratchpad>/runs/c3_yen_premium_revert/<1h|1d>.npz
# 1w: リードの測り方の変更の後。measure_card を打たず、日ごとの測定と診断だけ
PYTHONPATH=src python <scratchpad>/run_v2.py --card c3 --window 1w --from-npz <scratchpad>/runs/c3_yen_premium_revert/1w.npz --light
# 済んだ回に日ごとの測定を足す
PYTHONPATH=src python <scratchpad>/add_daily.py c3_yen_premium_revert <1h|1d> <npz>
```

並列(3 枚共通): 同時は最大 3 本。カード 2 を 3 本同時に measure_card に入れたところで a_5m が記憶の上限(cgroup 14,345,035,776 バイト)で止められ(exit 137、12:25Z)、その後は 1 本の最大 RSS の見積もり(カード 2 = 4.3GB・カード 3 = 3.5GB・カード 1 = 3.0GB)の合計 + 2GB が 14.3GB を超えるなら待つ形(`sched3.sh`・`sched4.sh`)にした。
このカード: 1h・1d・1w の区切りの run は `sched3.sh` で始めた。測り直し(1h・1d の `--from-npz`、1w の `--light`)は `sched4.sh` と `c3_1w_switch.sh` と手で打った 1 回。

## 照合(区切って読む = 全期間を一度に読む)

範囲: 窓 1w の 1 変種だけ、2018-01-01〜2019-01-01 の 1 年だけ、月の境の区切り 11 か所だけで比べた。ほかの窓・ほかの年・本番の走らせの暦年の境の区切りそのものの同一性は、この照合では確かめていない。
- `check_v2.py c3`: 2018-01-01T00:00:00Z〜2019-01-01T00:00:00Z(1 年)、月の区切り 11 か所、足 521307 本・決定 520293。持ち高の食い違い 0 本(完全一致 True)。 窓 1w、参照の記録の一致 True。 所要 565.2 秒、最大 RSS 1.76GB。

## 各回の要約

損益は bp・持ち高 1 単位あたり・経費前。区間は 95%(百分位)。MDE は 5% 両側・検出力 80%。
「1 分ごと」= 1 分ごとの P_t の系列の circular block bootstrap(L = 1,440 本は measure_card、L = 10,080 本は台本の week_block)。「日ごと」= 日ごとの損益の系列(日本時間の日)を日の塊(1 日・5 日)で circular block bootstrap し、1 分あたりに直したもの(daily_stats.json。式はそのファイルの formula)。1h・1d は measure_card を打った。1w は打っていない(リードの測り方の変更の後の回。1 分ごとの欄は —)。対照の百分位 = 持ち高を L 以上ずらした 200 通りの中の位置(measure_card の C5 d)。

| 変種 | 期間 | n(決定) | 日の数 | 平均(1 分あたり) | 平均(1 日あたり) | 1 分ごと L=1440 | 1 分ごと L=10080 | 日ごと 1 日塊 | 日ごと 5 日塊 | MDE(1 分ごと L=1440 / 日ごと 1 日塊) | 持ち高が 0 でない割合 | 変わった回数 | sum\|Δe\| | mean\|Δe\| | 対照の百分位 | 所要(秒) | 最大 RSS(GB) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1h | 2017-08-17〜2022-12-31 | 2793408 | 1962 | 0.2403 | 342.12 | [0.2231, 0.2581] | [0.2099, 0.2760] | [0.2240, 0.2580] | [0.2109, 0.2698] | 0.0254 / 0.0249 | 0.9886 | 2573476 | 808915.0 | 0.28958 | 100.0 | 区切りの run 62 + 測定 958 + 1 週 42 + 診断 190(1 回目の起動は区切りの run 1,084 秒・測定 約 1,000 秒の後、診断の現物の足の読み込みで門に拒まれて止まった。保存した npz から測定と診断をやり直した時間) | 2.08 |
| 1d | 2017-08-17〜2022-12-31 | 2793408 | 1962 | 0.1316 | 187.34 | [0.1193, 0.1449] | [0.1129, 0.1537] | [0.1194, 0.1448] | [0.1125, 0.1517] | 0.0183 / 0.0187 | 0.9884 | 2722685 | 282027.0 | 0.10096 | 100.0 | 区切りの run 60 + 測定 997 + 1 週 41 + 診断 192(1 回目の起動は区切りの run 1,073 秒(npz を保存)。そのあと止め、npz から測定と診断をやり直した時間) | 2.09 |
| 1w | 2017-08-17〜2022-12-31 | 2793408 | 1962 | 0.0890 | 126.66 | — | — | [0.0772, 0.1009] | [0.0758, 0.1022] | — / 0.0168 | 0.9857 | 2739904 | 145868.8 | 0.05222 | — | 区切りの run 61 + 日ごと 1 + 診断 192(区切りの run は 1 回目の起動(npz を保存)。そのあと npz から日ごとの測定をした) | 1.96 |

注: このカードの回は区切りの run の起動の記録(入力の sha256)を残す前に止めて測り直したため、持つ足と Binance のファイルの sha256 は、同じファイルをほかのカードの起動で封印の門が読んだときの値を写した。

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
| binance_btcusdt_close | `backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_2017.csv.gz` | `590178034c6e31b32e63e531804cbb5b2301253bc36eb904e4b45c21829b06a6` |
| binance_btcusdt_close | `backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_2018.csv.gz` | `f66cc2228c3b3b4c78ed418014f323f00690050b7319c57fba83a9e3d2389347` |
| binance_btcusdt_close | `backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_2019.csv.gz` | `ffb1fde499ae1c47f39e1df341d31d9db3cbb138a46bef36e9ed433c5135bb12` |
| binance_btcusdt_close | `backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_2020.csv.gz` | `655ab3497125c7a5bbd1f11cd23c655c29b2788a7916a3f8e6bd2048d98dda34` |
| binance_btcusdt_close | `backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_2021.csv.gz` | `56d016ad19008cb7c56bbe9754a74c32b1b7ce2061b6ae9133dccecb2a7dc859` |
| binance_btcusdt_close | `backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_2022.csv.gz` | `cdc318ee448879f567812cd2bdc4a60964e9e9f3806cf7adaba6e295b52b5ca4` |
| usdjpy_close | `backtest_data/fx_usdjpy_1m_20170801_20221231/usdjpy_1m.csv.gz` | `755670f47b6c99ea7fc1cc33479afe1f7cc9044bdb525ef2b14b37b09c76ccce` |

## 出力のファイルと sha256

| ファイル | sha256 |
|---|---|
| `1h/daily.csv` | `31786686ebc5175c0da413648edcca60e07cb1506d2a41544b5ef68163ae5f62` |
| `1h/daily_stats.json` | `bc6374c567ffa05817e5bb3d1b4831613b5c2355295a9ab7d7a54480db2fd16b` |
| `1h/diagnostics.json` | `20b5d6edb3095fbb2ba2e47d9eeec4ce1dda80ad41563cd230061fc1a5687a74` |
| `1h/measure.json` | `45e821edb6cb4d4c216306930ab031c368ac1d77dc22ba97706fb52bead4c2cc` |
| `1h/week_block.json` | `3dfb8d6b750acb00833b30174788796431624a92e0663f4984523c6917137706` |
| `1d/daily.csv` | `7830610c22f28ec4c0e1d2810423ded28554a81052af2e92407524ae6cbc4daa` |
| `1d/daily_stats.json` | `44b9a5fc6f61cd8f131bba80a016ac2244aabf52df0c999dc47c30fbcaf537dc` |
| `1d/diagnostics.json` | `7921d050aae6e53675bf158ed90f5d9a4aca91ba6a6ab7ac752bdbbec6d2aaf1` |
| `1d/measure.json` | `ca9f06a03ff29cb97ced0f9f739ab910b5415b02fd4386e191b6c60fb019fe36` |
| `1d/week_block.json` | `78e54e6e20b594b228f58d59594fdec30952464772f693940cdf0bb890f51a1f` |
| `1w/daily.csv` | `38c944a0dca7af82a2a1e51cf96a2e651065dbbc456813aae72fad4da6839e95` |
| `1w/daily_stats.json` | `279386a0528f8994c2e18cc167801c5fdf2df677d19df687c5c64ceeb9eb07fe` |
| `1w/diagnostics.json` | `b750052267a14458e67845ef1724895c6471a3750b9149553f9ffcfc8aad6e92` |

## 2026-10-02 リードの追記(関門 ② 2 回目の [直す])
- `1w/daily_stats.json` の `w4.chunks[0].note` にある「1 回目の起動は測定の後の診断(現物の足の読み込み)で止まった」は、1h の注の文面の写しで、**1w には当てはまらない(誤り)**。1w の npz は、区切りの run_card だけの起動(`jobs/c3_1w.runonly.log`、14:34Z 保存)から作った。出力ファイルは sha256 を載せているので書き換えず、ここで訂正する。
