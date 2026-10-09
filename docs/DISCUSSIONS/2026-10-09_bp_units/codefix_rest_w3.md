# 残りの直し: 作業者 w3 の受け持ち(o3c・katsuo・scalp・liq_cascade_v2)

書いた人: 作業者 w3。決まりは `REST_RULES.md`。

## 着手前の表

| やろうとすること | オーナーの原文の該当語(逐語) |
|---|---|
| 受け持ちの 41 ファイルの bp を 1 つずつ読み、値動き率なら bp のまま、ほか(費用・ネット・スプレッド・距離・約定のずれ)は % に直す | L-920「**方針はbpの意味は「値動き率」としてのみ残し、その他の意味を持たせないようにすること**」 |
| スプレッド・約定の値段のずれも % にする | L-923「**1.A**」(1.A = スプレッド・ベーシス・約定の値段のずれも bp にしない) |
| 値動き率どうしの差は bp のまま | L-924「**A**」 |
| 組で変える必要のある読み手・書き手を一緒に直す(受け持ちの外は触らず報告に書く) | L-920「**わかってる修正が必要なもの全部直してください**」 |
| 着手から 2 時間で止め、残りを書く | L-923「**2時間を上限にしろ**」 |
| 新しい試験を足さない。今ある試験を名前と単位に合わせるだけ | L-923「**そうしないと意味不明な試験ばっかりで終わらなくなる**」 |
| 報告をこのファイルに書く | L-925「**次は残りを終わるまでやってください**」(書き場所は REST_RULES §5 のリードの決まり。オーナーの逐語は無い) |

### 完了見込み時間

- 分類(41 ファイルの bp の当たり 約 1,600 個を名前ごとに分ける): 20 分(実測なし)
- o3c の書き手 4 本(`o3c_price_level_table`・`o3c_price_level_ext`・`o3c_oi_distance`・`o3c_reaction`)と読み手 11 本の距離・費用の列: 50 分(実測なし)
- scalp の 5 本(`research_scalp_exits`・`research_scalp_opt`・`replay_scalp_storm`・`run_scalp_paper`・`tp_operating_curve`)の費用・ネット・滑り: 25 分(実測なし)
- katsuo 5 本・`liq_cascade_v2`・`build_burst_library`・`o3c_bitflyer_spread`: 15 分(実測なし)
- 試験 14 本を合わせて回す: 10 分(実測なし)
- 合計 約 2 時間(上限と同じ。上限に来たら止めて残りを下に書く)

## 着手前の試験(直す前に回した。`git stash` は使っていない)

| 試験 | 結果 |
|---|---|
| `tests/test_o3c_jev_state.py` | 39 passed |
| `tests/test_o3c_oi_distance.py` | 18 passed |
| `tests/test_o3c_price_level_table.py` | 16 passed |
| `tests/test_o3c_reaction.py` | 69 passed |
| `tests/test_o3c_reaction_judge.py` | 67 passed |
| `tests/test_o3c_reaction_r2.py` | 21 passed |
| `tests/test_o3c_signal_continue.py` | 13 passed |
| `tests/test_o3c_signal_continue_jev.py` | 7 passed |
| `tests/test_o3c_signal_explore.py` | 21 passed |
| `tests/test_o3c_signal_explore5.py` | 30 passed |
| `tests/test_o3c_signal_materials.py` | 13 passed, 1 warning |
| `tests/test_o3c_signal_stage2.py` | 9 passed |
| `tests/test_o3c_signal_value.py` | 86 passed |

(コマンドは 1 本ずつ `PYTHONPATH=src python -m pytest <試験>`。`tests/test_scalp_logic.py` だけは直した後に初めて回した(下)。)

## 受け持ちのファイル 1 つずつ

### scalp の組

| ファイル | 直した / 直さない | 中身(コードで確かめた行) |
|---|---|---|
| `scripts/run_scalp_paper.py` | 直した | `SLIPPAGE_BPS = 2.0` → `SLIPPAGE_PCT = 0.02`(%)、使う 3 か所 `/ 1e4` → `/ 100`(328・380・423 行)。約定の値段のずれ(L-923 1.A)。docstring の「+5 bps/trade adoption bar」「-4.1 bps/trade」(費用を引いたネット)→「+0.05 %/trade net」「-0.041 %/trade net」。`thr_bps`・`tp_bps`・`signal_bps`・`sigma60_bps`・`leader_return_bps` は値動き率(Binance の 5 秒の対数の値動き・入り値からの利確の距離・1 秒の対数リターンの標準偏差)なので bp のまま |
| `tests/test_scalp_logic.py` | 直した(組) | 滑りの期待値 `(1 - 2.0 / 1e4)` → `(1 - 0.02 / 100)`(269・313 行)。ほかの bp(`thr_bps`・`tp_bps`・`step_bps`・`sigma60_bps`)は値動き率 |
| `scripts/replay_scalp_storm.py` | 直した | 費用 `COST_BURST_BPS = 1.96 + 2.0`・`COST_CALM_BPS = 0.93 + 2.0` → `COST_BURST_PCT = 0.0196 + 0.02`・`COST_CALM_PCT = 0.0093 + 0.02`。採用の線 `ADOPTION_BAR_BPS = 5.0` → `ADOPTION_BAR_PCT = 0.05`(事前登録の逐語「>= +5 bps/trade net」は残し、直後に「L-920 の後の単位: >= +0.05 %/trade net」を足した)。`net_bps()`・`cf_net_bps()` → `net_pct()`・`cf_net_pct()`(= `gross_bps / 100 − 費用%`)。表示のネットは全部 %(桁は 2 つ増やした)。`gross_bps`・`cf_gross_bps`(量 1、向き × (出/入 − 1) × 1e4、費用なし: 263-266 行)・`ret_bps`・`thr_bps` は値動き率なので bp のまま。`stat_block` に `pct=` を足し、グロスは bp、ネットは % で出す |
| `scripts/research_scalp_exits.py` | 直した | `replay_scalp_storm` から読む費用・線を `_PCT` に。`Trade.cost_bps` → `cost_pct`、`Trade.net()` = `gross_bps / 100 − 費用%`。仮想の「120 秒持って出る」のネット `cf_hold_gross_bps − COST` → `cf_hold_gross_bps / 100 − COST_BURST_PCT`。E0 の再現の照合 `nets.append(gross − COST)` も同じ。表示のネット・採用の線・CI・和を % に(表示の中の過去の数「-2.13 bps」「-2.29 bps/trade」はネットなので「-0.0213 %」「-0.0229 %」と書き添え/書き換え)。`gross_bps`・`mfe_bps`・`mae_bps`・`tp_bps`・`trail_bps`・`rev_stop_bps`・`thr_bps` は値動き率(入り値からの距離・山からの戻り・5 秒の値動き)なので bp のまま |
| `scripts/research_scalp_opt.py` | 直した | `SLIP_BPS = 2.0` → `SLIP_PCT = 0.02`、`ASSUMED_RT_BPS = 6.35` → `ASSUMED_RT_PCT = 0.0635`。`taker_capture`(ask で買い bid で売り、滑り込みの約定値段どうしの対数比 = 費用込みのネット)と `maker_sim` の取り分(出口の滑り込み)を `× 1e4` → `× 100`(%)。入りの費用の分解(仲値からの約定のずれ)`× 1e4` → `× 100`、列 `cost vs mid bps` → `cost vs mid %`。スプレッドの文脈 `1e4 × (ask − bid) / mid` → `100 ×`。表の列 `bps/EVENT`・`bps/FILL`・`filled bps`・`missed-as-taker bps`・`mean bps`・`EV/h bps` → `%`。`gross_move`(仲値から仲値、費用前)の列 `gross bps` と `span drift`(期間の始めと終わりの値動き)は値動き率なので bp のまま |
| `scripts/tp_operating_curve.py` | 直した | スプレッドの特徴 `avg_spread_bps`・`rel_avg_spread_bps` → `avg_spread_pct`・`rel_avg_spread_pct`。入力の系列(`judge_board_round.load_series`、L-920 より前に書かれた `board_round_series_5s.csv.gz`)は `spread_bps`(= spread / mid × 1e4)しか持たないので、`spread_pct` が無ければ `spread_bps / 100` を読む(コメントを書いた)。閾値の表示の桁を `10.3f` → `10.5f`(% の値が 1/100 になるため)。`realized_move`・バーストの 20bps(60 秒の仲値の値動き)は値動き率なので bp のまま。走らせて確かめてはいない(入力の系列は 2026-09 の記録で、REST_RULES §4 の「2023-12-17T15:00Z より後のデータを読まない」に当たる) |

確かめ(% × 100 = 前の bp):

```
$ cd scripts && PYTHONPATH=../src python3 -c "import replay_scalp_storm as r; ... "
3.9599999999999995 3.96 2.93 2.93 5.0          # COST_BURST_PCT*100, 1.96+2.0, COST_CALM_PCT*100, 0.93+2.0, ADOPTION_BAR_PCT*100
8.540000000000001 8.54 -0.9199999999999986 -0.9199999999999999   # net_pct*100 と 12.5-(1.96+2.0)、cf_net_pct*100 と 7.0-2*(1.96+2.0)
$ ... research_scalp_exits.Trade(gross_bps=10.0, cost_pct=COST_BURST_PCT, exit_type='fallback').net()
net% 0.06040000000000001 x100 6.040000000000001 old bp 6.04
tp net% 10.0
$ python3 -c "print(0.02/100, 2.0/1e4, 0.02/100==2.0/1e4)"
0.0002 0.0002 True
```

(浮動小数の 1e-15 ほどの差は残る。値の意味は変わっていない。)

`tp_operating_curve.features()`(合成の 60 行。`spread_pct = spread_bps / 100` を入れて呼ぶ):

```
$ cd scripts && PYTHONPATH=../src python3 -c "... f = t.features(s); print(f['avg_spread_pct'].iloc[-1]*100, s['spread_bps'].rolling(t.WIN, min_periods=t.WIN).mean().iloc[-1])"
avg_spread_pct*100 = 3.1291132281525034  old avg_spread_bps = 3.1291132281525034
```

### katsuo の 5 本・`build_burst_library`(直さない)

| ファイル | 直さない理由(コードの行) |
|---|---|
| `scripts/measure_katsuo_body_wick.py` | ひげの長さ ÷ 終値 × 1e4(152 行 `wbp = w / close[i] * 1e4`)と、h 本後の終値までの向き付きのリターン(`mean_fwd_bp`・`buy_fwd_bp`・`sell_fwd_bp`)。どちらも REST_RULES §1 の値動き率(ひげ・向きを掛けた値動き) |
| `scripts/measure_katsuo_dispersion.py` | 門 `SMALL_GATES`・`BIG_GATES` はひげ ÷ 終値(129 行)。`sd_trade_bp`・`sd_sig2_bp`・`iqr_trade_bp` は 1 取引ずつの符号付きリターン(量 1、費用なし)の散らばり。値動き率 |
| `scripts/measure_katsuo_judgement_vol.py` | `ret_bp` は量 1 の符号付きリターン、境目 `edges_bp` は直前の値動きの大きさの三分位。値動き率。ただし `total_bp`(112 行 `round(sum(rs), 1)`)は取引ごとのリターンの和 → 下の「迷ったこと」1 |
| `scripts/measure_katsuo_vol_bitflyer.py` | 同上(`ret_bp`・`edges_bp_own`・`bitmex_fixed_edges_bp` は値動き率)。`total_bp`(95 行)は「迷ったこと」1 |
| `scripts/measure_katsuo_xvenue.py` | `mean_bp`・`ci95_bp`・`sd_bp`・`quantiles_bp`(1 取引の符号付きリターン)・`edges_bp_own` は値動き率。`total_bp`(346 行)は「迷ったこと」1 |
| `scripts/build_burst_library.py` | 当たりは docstring の「the scalper's 5s >= 10bps signals」(8 行、5 秒の値動き)だけ。値動き率 |

### o3c の費用・ネット・スプレッドの組

| ファイル | 直した / 直さない | 中身(コードで確かめた行) |
|---|---|---|
| `scripts/o3c_bitflyer_spread.py` | 直した | 実効スプレッド(同じ 1 秒の中で隣り合う買いと売りの約定の値段の差 ÷ 中値)= スプレッド(L-923 1.A)。`effective_spread_pairs` の `× 1e4` → `× 100`、表の列 `p25_bp`・`p50_bp`・`p75_bp`・`p90_bp`・`参考_符号付きp50_bp`・`参考_正の対だけp50_bp` → `_pct`、summary の鍵 `主のc_清算直後プールの絶対値の中央値_bp` ほか 4 つ → `_pct`、表示 `{c:.4f} bp` → `{c:.6f} %`、docstring の「× 1e4」「(bp)」→「× 100」「(%)」(実測の数「1.7869 / 1.9176 / 2.2574」は残し、直後に「L-920 の後の単位: 0.017869 / 0.019176 / 0.022574 %」を足した)。`read_cost` は新しい列 `p50_pct`・`p75_pct` があればそれを、無ければ(git の `backtest_data/o3c_signal_value_20260921/spread/spread_by_day.csv` は L-920 より前で `p50_bp`・`p75_bp` だけ)古い列を `/ 100` して % で返す(docstring とコメントに書いた) |
| `scripts/o3c_signal_value.py` | 直した | 費用 c とネット: `cost_bp` → `cost_pct`(引数・変数の全部)、`pnl_net_bp` → `pnl_net_pct` = `pnl_bp / 100 − c(%)× 建玉の回数`(883-885・998・1405-1428・1555・1921-1965・2137-2139 行の式。`v_bf − cost` の 1 分足の損益も `v_bf / 100 − cost`)。`apply_cost` は前は**費用を引いた値で `pnl_bp` 列を上書き**していた(名前は費用前の bp、中身はネット)。新しい列 `pnl_net_pct` に書き、`pnl_bp` は費用前のまま残す。`o3c_signal_policy` の分布の関数に `col="pnl_net_pct"` を渡す(下)。`tables_from_cascade_rows` も前は `sub["pnl_bp"] = sub["pnl_net_bp"]` で同じ上書きをしていたので同じに直した。列 `c_bp` → `c_pct`。表と summary の鍵: `総収支_bp`・`前半の前_総収支_bp`・`前半の後_総収支_bp`・`日ごとの総収支_bp`・`選んだ組との差_bp`・`保有1時間あたりの収支_bp/h`・`費用_bp`・`主のc_bp`・`p75_bp`(費用の dict)・`bitFlyer_bp`・`Binance_bp`(1 分足の費用を引いた損益)・`bitFlyerの合計_bp`・`Binanceの合計_bp`・`対差の中央値_bp`・`対差のp25_bp`・`対差のp75_bp`・`対差の平均_bp`・`対差の合計_bp`・`合計_bp`・`日の合計の中央値_bp`・`下位5日の合計_bp`・`上位5日の合計_bp`・`費用を引いた合計_bp` → `_pct`(どれも費用を引いた値かその和・差)。合成の道筋の列 `費用 c=… を引いた損益_bp` → `_pct`、既定 `cost_bp=2.0` → `cost_pct=0.02`。表示「主の c(bp)」→「(%)」。前の出力(git の `backtest_data/o3c_signal_value_20260921/**/cascades.csv.gz`)を読む口 `run_from_rows`・`tables_from_cascade_rows`・resume の summary は、新しい関数 `_with_pct_columns` で `pnl_net_pct`・`c_pct` が無ければ `pnl_net_bp`・`c_bp` を `/ 100` して読む。**直さないもの**: `pnl_bp`(費用前。1 本の連鎖の損益 = レグの損益の和、下の「迷ったこと」1)・`レグ損益_bp`(量 1、向き × (出/入 − 1) × 1e4)・`STOP_BP`(含み損 20/50bp = 入り値からの逆行)・`TP_BP`(入り値から 5bp)・`VALUE_CONT_BP`・`遅れ1秒の約定からの最大順行_bp`・`費用なしの中央値_bp` は値動き率。`費用なしの合計_bp`(2922 行、レグの損益の和)は「迷ったこと」1 |
| `scripts/o3c_signal_policy.py` | 直した(組) | `dist_stats`・`build_dist_table`・`build_position_breakdown` に引数 `col`(既定 `"pnl_bp"`)を足した。前は `pnl_bp` 列しか読めず、`o3c_signal_value` がネットを `pnl_bp` に上書きして渡していたため。既定は変えていないので、この台本の単独の走り(費用前)の値は変わらない。`pnl_bp`(633 行 `total_pnl` = 連鎖の中のレグの損益の和、`n_entries` ≥ 1)は「迷ったこと」1。`tp_bp`・`レグ損益_bp` は値動き率 |
| `tests/test_o3c_signal_value.py` | 直した | 試験する口に合わせた: 実効スプレッドの期待値 `× 1e4` → `× 100`、`_dist_row` の鍵 `p50_bp` ほか → `_pct`、費用 `c = 1.7869` → `0.017869`(%)と `apply_cost` の列 `pnl_net_pct`(= `pnl_bp / 100 − 2c`)、合成の道筋 `build_synthetic_traces_value(0.02)` と列 `費用 c=0.0200 を引いた損益_pct`、連鎖 1 本ごとの行の費用 `{0, 2.0, 4.0}` → `{0, 0.02, 0.04}` と `pnl_net_pct == 10.0 / 100 − 0.02 × 2`、`read_cost` は git の表の `p50_bp / 100` と比べる。ほかの鍵(`総収支_bp` ほか)の名前を `_pct` に。git の `spread_by_day.csv` の列の名前を確かめる試験(484-487 行)は前の表の名前のまま(コメントを足した)。試験の関数名 `..._bp_per_hour` → `..._pct_per_hour` |

確かめ(% × 100 = 前の bp):

```
$ cd scripts && PYTHONPATH=../src python3 -c "... vv.build_cascade_rows_file(pr, {'主': 1.9176/100}) ... vv.apply_cost(pr, 1.9176/100) ..."
new pct x100 = 6.5872  old bp = 6.5872          # pnl_bp 12.34、建玉 3 回、c = 1.9176bp(= 0.019176 %)
apply_cost x100 = 6.5872
```

### o3c の距離の列の族(直さない。下の「迷ったこと」2)と、族の外で直したもの

| ファイル | 直した / 直さない | 中身(コードで確かめた行) |
|---|---|---|
| `scripts/o3c_price_level_table.py` | 一部直した | docstring・コメントの「直前価格から ±35〜40bp ずれた帯」(21・47・416 行、指値と直前の約定の値段の距離)→「±0.35〜0.40%」。列 `dist_node_bp`・`dist_gap_bp`・`dist_vwap_bp`(189 行 `(centroid − p_liq) / p_liq × 1e4` = VWAP・節からの距離)は直していない(「迷ったこと」2) |
| `scripts/o3c_price_level_ext.py` | 一部直した | ローカル変数 `bp`(180 行。中身は `bin_pct`)→ `bin_pcts`。summary の文「offset の 56 / 70bp」(ノードからの距離)→「0.56 / 0.70 %」。`dist_*` の列は「迷ったこと」2 |
| `scripts/o3c_oi_distance.py` | 一部直した | `collect_side_spread`: 同じ桶の買い側 VWAP − 売り側 VWAP ÷ VWAP(537 行)= スプレッド。`× 1e4` → `× 100`、summary の鍵 `side_price_spread_bp` → `side_price_spread_pct`、分位の丸めを 4 → 6 桁。`dist_*`・`oi_dist_*`・`oi_side_dist_*`・`*_liqdir`・`implied_leverage` の `d/1e4` は「迷ったこと」2 |
| `tests/test_o3c_oi_distance.py` | 直した | `side_spread_block` の期待値 `2.0`(bp)→ `0.02`(%)。これが % × 100 = 前の bp の確かめにもなる(`(30003 − 29997) / 30000 × 100 = 0.02`、前は × 1e4 = 2)。ほかは「迷ったこと」2 |
| `scripts/o3c_reaction.py` | 一部直した | ローカル変数 `liq_bp`・`cand_bp`(1883-1901 行。中身は `bin_pct`、bp ではない)→ `liq_bin_pct`・`cand_bin_pct`。直さない: `anchor_price_diff_bp`(2082 行 `(anchor_price − before_price) / before_price`、同じ列の 2 つの時刻の値段 = 値動き率)・`bf_bp_{h}m`(1 分足の終値の変化)・`bp_h`・`emit_raw_bp`(h 秒の値動き)・`dist_*`・`node_up_bp`・`node_dn_bp`・`directional_node_bp`(節からの距離、「迷ったこと」2) |
| `scripts/o3c_signal_continue.py` | 一部直した(組) | 材料 8 の帯の量を `cascade_read`(作業者 w4 の受け持ちの `docs/DATA/probes/20260920_o3c_cascade_read.py`)の `oi_band_amounts` から読む鍵。w4 がこの回に鍵を `amt_5bp`・`amt_10bp`・`amt_20bp` → `amt_0.05pct`・`amt_0.1pct`・`amt_0.2pct` に変えたので、新しい鍵を読み、無ければ古い鍵を読むようにした(549-563 行)。直さない: `path_extreme_bp`・`range_bp_window`・`mat4_bounce_bp`・`price_path_bp_last_60s`(値動き率)、`dist_node_bp`・出力の列 `mat8_amt_5bp`・`mat8_amt_20bp`(「迷ったこと」2) |
| `src/bot/research/liq_cascade_v2.py` | 一部直した(組) | 同じく `oi_band_amounts` の鍵を新旧の両方で読むようにした(1085-1090 行)。**直す前、この鍵の変わりで `tests/research/test_liq_cascade_v2.py::test_no_lookahead_truncate_and_perturb` が `assert n_fin8 > 0` で落ちていた**(材料 8 が全部 NaN になる)。直した後は通る(下の試験)。直さない: `react_*`・`mfe_*`・`mae_*`・`giveback_*`(551-560 行、清算の向き × p₀ からの変化)・`s_curve_values` の fade の損益(610 行 `pos_dir × (px − pe) / pe × 1e4`、量 1・費用なし・1 回の建てから出まで = 値動き率)・`raw_m{T}`(385 行)・`mat4_bounce_bp`(1061-1064 行)・`range_bp_window`(1076 行)は値動き率。docstring の `pnl_bp`(48 行、状態機械の連鎖の損益)は「迷ったこと」1。1104 行の `profile_columns(...)["dist_node_bp"]` と出力の列 `mat8_amt_5bp`・`mat8_amt_20bp` は「迷ったこと」2 |
| `scripts/o3c_jev_state.py` | 直さない | `range_bp_window`・`price_path_bp_last_60s`・`_bp_moves`・`PULLBACK_EPS_BP`(戻り)・Jev に渡す文の「… bp」(60 秒・10 秒・5 秒の値動き、連鎖の始まりからの値動き)は値動き率。`mat8_amt_20bp`・`mat8_amt_5bp`・`oi_ahead_20bp`(帯 = 値段からの距離の名前)は「迷ったこと」2。`DAY_EXTREME_EPS_BP` と文「Price is X bp short of a fresh day extreme」(520 行、今の値段と日の極値の差)は「迷ったこと」3 |
| `scripts/o3c_reaction_r2.py` | 直さない | `bp_{h}m` 系は値動き率。`dist_*` は「迷ったこと」2 |
| `scripts/o3c_rows4.py` | 直さない | `internal_bp`(319 行 `(e[1] − s[1]) / s[1] × 10_000`、同じ足の中の始めと終わりの値段 = 値動き率)とその派生の列 |
| `scripts/o3c_signal_explore.py` | 直さない | `bp_{h}m`・`bp_{h}m_reactdir` は値動き率。`dist_*` は「迷ったこと」2 |
| `scripts/o3c_signal_explore2.py` | 直さない | `dist_*` だけ(「迷ったこと」2) |
| `scripts/o3c_signal_explore4.py` | 直さない | `sweep_bp`(231 行 `sign × (p_end − p_pre) / p_pre × 1e4`)・`den_bp_{T}`(261 行)・`r_end_{h}`・`m_{T}` は同じ列の 2 つの時刻の値段 = 値動き率。`dist_node_bp` 1 か所は「迷ったこと」2 |
| `scripts/o3c_signal_explore5.py` | 直さない | `dist_node_bp`・`dist_vwap_bp` だけ(「迷ったこと」2) |
| `tests/test_o3c_jev_state.py` | 直さない | 相手の台本の名前(`mat8_amt_*`・`oi_ahead_20bp`・`dist_node_bp`)を変えていないので試験も変えていない |
| `tests/test_o3c_price_level_table.py` | 直さない | `dist_*` だけ(「迷ったこと」2) |
| `tests/test_o3c_reaction.py` | 直さない | `bp_{h}m`・`emit_raw_bp`・`anchor_price_diff_bp` は値動き率。`directional_node_bp`・`dist_*` は「迷ったこと」2。`liq_bin_pct` の改名は関数の中のローカル変数なので試験に触れない |
| `tests/test_o3c_reaction_judge.py` | 直さない | 試験する相手 `scripts/o3c_reaction_judge.py` は受け持ちの外で、事前登録の軸(A2〜A5)を `dist_*_liqdir` の名前で持つ(「迷ったこと」2) |
| `tests/test_o3c_reaction_r2.py` | 直さない | `bp_{h}m` は値動き率、`dist_*` は「迷ったこと」2 |
| `tests/test_o3c_signal_continue.py` | 直さない | `dist_node_bp`(材料 5)は「迷ったこと」2、`price_path_bp_last_60s` は値動き率 |
| `tests/test_o3c_signal_continue_jev.py` | 直さない | `price_path_bp_last_60s` は値動き率、`dist_node_bp` は「迷ったこと」2(相手の `o3c_signal_continue_jev.py` は受け持ちの外) |
| `tests/test_o3c_signal_explore.py` | 直さない | 試験の中の関数 `liq_bp`・`ctl_bp`(63・67 行)は `bp_{h}m` の値動き率を返す。`dist_*` は「迷ったこと」2 |
| `tests/test_o3c_signal_explore5.py` | 直さない | `dist_node_bp` だけ(「迷ったこと」2) |
| `tests/test_o3c_signal_materials.py` | 直さない | 相手 `scripts/o3c_signal_materials.py`(受け持ちの外)の `node_ahead_bp_batch`(節までの距離)と `dist_node_bp`。「迷ったこと」2 |
| `tests/test_o3c_signal_stage2.py` | 直さない | `dist_node_bp`・`mat8_amt_*`・`oi_ahead_20bp` だけ(相手 `o3c_signal_stage2.py` は受け持ちの外)。「迷ったこと」2 |

## 組で触ったほかのファイル(受け持ちの一覧に無いもの)

- `scripts/o3c_signal_policy.py`: 一覧にはあるが、上の「組」の直し(`col` 引数)。その試験 `tests/test_o3c_signal_policy.py` は一覧に無い。触っていない(回しただけ)。
- 触っていないが組の相手で、直しが要るもの:
  - `scripts/research_exit_surface.py`(作業者 w4 の受け持ち)75-79 行が `from replay_scalp_storm import COST_BURST_BPS, COST_CALM_BPS, describe` をしている。私が `COST_BURST_PCT`・`COST_CALM_PCT` に変えたので、**この import は今は失敗する**(289 行 `cost = 0.0 if kind == "tp" else COST_BURST_BPS` もネットを bp で引く式)。w4 か リードが `_PCT` と `gross / 100 − 費用` に合わせる必要がある。
  - `tests/test_o3c_signal_policy.py`・`tests/research/test_liq_cascade_v2.py` は回した(下)。
- `scripts/run_scalp_paper.py` は動いている経路(`deploy/start_all.bat`)。変えたのは滑りの定数の名前と単位(`SLIPPAGE_PCT`)だけで、ログ(`data/scalp_paper.jsonl`)の欄の名前(`signal_bps`・`thr_bps`・`sigma60_bps`)は値動き率なので変えていない(`schema/scalp_paper_log.json`・`scripts/judge_gates.py` の読み口に影響しない)。

## 迷ったこと(リードの判断が要るもの)

1. **量 1 の損益を「足し合わせた」ものを bp のまま残した**。リードの決め(「量 1 で、向きを掛けた『建てから出までの値動き』(費用を引いていない)は値動き率なので bp のまま … 段数を足し合わせたものは bp にしない」)の「段数」が、**同時に持つ段(積み増し)だけ**を言うのか、**順に建て直したレグ(ドテン・取引)の和**も含むのかが、コードからは決められなかった。当たるもの:
   - `scripts/o3c_signal_policy.py` 633 行 `"pnl_bp": total_pnl`(= 1 本の連鎖の中のレグの損益の和。`n_entries` は 1 以上、型 B のドテンで 2 以上)。`scripts/o3c_signal_value.py` 713 行の `pnl_bp` は 1 回の建てから出まで(`建玉の回数` = 1)で値動き率だが、同じ列 `pnl_bp` に両方が入る。`src/bot/research/liq_cascade_v2.py` 48 行の docstring の `pnl_bp` は前者を指す。
   - `scripts/o3c_signal_value.py` 2922 行 `費用なしの合計_bp`(レグの損益の和)。
   - katsuo の `total_bp`(`measure_katsuo_judgement_vol.py` 112 行・`measure_katsuo_vol_bitflyer.py` 95 行・`measure_katsuo_xvenue.py` 346 行、取引ごとのリターンの和)。
   - 費用を引いたものは全部 % にした(上)。残したのは費用前の和だけ。「順のレグの和も bp にしない」なら、`pnl_bp`(連鎖)は `o3c_signal_policy`・`o3c_signal_value`・`liq_cascade_v2` と、その出力を読む `scripts/c9_run_a.py` ほか c9 の台本(受け持ちの外)と git の `backtest_data/o3c_signal_value_20260921/**` の読み口を組で変える必要がある。
   - `liq_cascade_v2` の `s_curve_values` の fade の損益(610 行)と `measure_katsuo_*` の `ret_bp`・`mean_bp` は 1 回の建てから出まで(量 1・費用なし)なので、決めのとおり値動き率として bp のまま残した(名前を `move_bp` などにするかは「読み手の数で決める」とあったが、`pnl_bp` の名前は c9 の台本ほか受け持ちの外の読み手が多いので変えていない)。

2. **o3c の距離の列の族(`dist_node_bp`・`dist_vwap_bp`・`dist_gap_bp`・`oi_dist_*`・`oi_side_dist_*`・`*_liqdir`・`node_up_bp`・`node_dn_bp`・`directional_node_bp`・`node_ahead_bp_batch`・`mat8_amt_5bp`・`mat8_amt_20bp`・`oi_ahead_20bp`)は直していない**。どれも同じ時刻の 2 つの値段の距離(VWAP・節・建玉の帯までの距離)で、REST_RULES §1 では bp にしないものに当たる。直さなかった理由: 列を読む判定の台本 `scripts/o3c_reaction_judge.py`(受け持ちの一覧に無い)が、**事前登録の軸 A2〜A5 をこの列の名前で持っている**(凍結した判定。リードの判断の場所):
   ```
   $ grep -nE 'read_csv|profile_columns|dist_(node|vwap|gap)_bp|_load\(|import' scripts/o3c_reaction_judge.py
   228:    "dist_vwap_bp_liqdir": "dist_vwap_bp",
   229:    "dist_node_bp_liqdir": "dist_node_bp",
   230:    "oi_dist_vwap_bp_liqdir": "oi_dist_vwap_bp",
   231:    "oi_dist_node_bp_liqdir": "oi_dist_node_bp",
   ...
   333:    ("A2", "dist_node_bp_liqdir"),
   334:    ("A3", "dist_vwap_bp_liqdir"),
   335:    ("A4", "oi_dist_node_bp_liqdir"),
   336:    ("A5", "oi_dist_vwap_bp_liqdir"),
   1666:    from _research_audit_gate import require_audit
   ```
   書き手だけを % にすると、この判定の台本は新しい出力を読めなくなる。半分だけの改名は混ぜるより悪いので、族ごと手を付けなかった。範囲(`.py` に切った。CSV・JSON・md は数えていない):
   ```
   $ P='dist_(node|vwap|gap)_bp|node_(up|dn)_bp|directional_node_bp|node_ahead_bp|mat8_amt_(5|20)bp|oi_ahead_20bp'
   $ git ls-files -z -- '*.py' ':!docs/RESEARCH/WINDOW1' ':!backtest_data/phase2_sealed' | xargs -0 grep -ohE "$P" | wc -l
   410
   ```
   ファイルごと(行数): 書き手 `o3c_oi_distance` 29・`o3c_price_level_table` 15・`o3c_price_level_ext` 8・`o3c_reaction` 25、受け持ちの読み手 `o3c_reaction_r2` 13・`o3c_signal_continue` 11・`o3c_signal_explore` 9・`o3c_signal_explore2` 3・`o3c_signal_explore4` 1・`o3c_signal_explore5` 13・`o3c_jev_state` 5・`liq_cascade_v2` 6、受け持ちの外の読み手 `o3c_reaction_judge` 17・`o3c_signal_materials` 2・調べの台本 8 本(`docs/DATA/probes/` の 20260919・20260920 の `.py`。うち 3 本(`20260919_o3c_reaction_bugcheck.py`・`_bugcheck2.py`・`_r1_bp_reactdir_standardized.py`)はこの回に作業者 w4 が `_dist_pct` で古い列を / 100 して読むように直している: `grep -l _dist_pct docs/DATA/probes/*.py` の出力。git diff で見た事実で、w4 の報告では確かめていない)、試験 13 本(118 行)。git に入った表(CSV・JSON)でこの列を持つものは 71 個(書き換えない)。`config/jev_design_examples/*.yaml` 8 本は Jev の共変量の説明文で、`.py` から読まれていない(`grep -l jev_design_examples` が 0 件)。直すなら: 書き手 4 本を `*_pct`(× 100)、読み手は新しい名前が無ければ古い名前を `/ 100`、判定の台本の軸の名前を変えるかをリードが決め、試験 13 本を合わせる。

3. `scripts/o3c_jev_state.py` の `DAY_EXTREME_EPS_BP` と Jev に渡す文「Price is X bp short of a fresh day extreme」(520 行): 今の値段と、その日のそれまでの極値(前の時刻の値段)の差。MFE・山からの戻りと同じく「前の値段から今の値段への動き」と読んで bp のまま残したが、「節からの距離」と同じく「水準からの距離」とも読める。

4. `scripts/tp_operating_curve.py` の入力の系列は `judge_board_round.load_series` が読む。`judge_board_round.py`(受け持ちの外。この回にほかの作業者が直している)は、古い列 `spread_bps` しか無い系列を `spread_pct = spread_bps / 100` にして `spread_bps` を落とす(246-248 行):
   ```
   $ grep -nE 'spread_bps|spread_pct' scripts/judge_board_round.py
   246:    if "spread_pct" not in df.columns and "spread_bps" in df.columns:
   247:        df["spread_pct"] = df["spread_bps"] / 100   # legacy column: x 1e4 -> %
   248:        df = df.drop(columns=["spread_bps"])
   ```
   なので `tp_operating_curve.py` 158-159 行の古い列の読み口は今は通らない(害は無い)。走らせての確かめはしていない(入力が 2026-09 の記録で、REST_RULES §4 の日付の決まりに当たる)。

## o3c_signal_value・o3c_oi_distance で変えた鍵の、受け持ちの外の読み手

```
$ git ls-files -z -- '*.py' ':!docs/RESEARCH/WINDOW1' ':!backtest_data/phase2_sealed' | xargs -0 grep -lE '費用_bp|収支_bp/h|対差の合計_bp|"合計_bp"|日の合計の中央値_bp|bitFlyerの合計_bp|side_price_spread_bp|対差の中央値_bp|下位5日の合計_bp|費用を引いた合計_bp' | grep -vE 'o3c_signal_value|test_o3c_signal_value|o3c_oi_distance'
(出力なし)
$ git ls-files -z -- '*.py' ... | xargs -0 grep -lE 'pnl_net_bp|総収支_bp|主のc_bp|c_bp"|bitFlyer_bp|p50_bp|apply_cost|read_cost|COST_BURST_BPS|SLIPPAGE_BPS|SLIP_BPS|avg_spread_bps'
(私の直したファイルのほかは scripts/research_exit_surface.py(上の import)と、別の意味の同じ字(c6 の g_btc_bp、render_exec_floor の p50_bp)だけ)
```

## 回した試験と結果(直した後)

```
$ PYTHONPATH=src python -m pytest tests/test_o3c_jev_state.py tests/test_o3c_oi_distance.py tests/test_o3c_price_level_table.py tests/test_o3c_reaction.py tests/test_o3c_reaction_judge.py tests/test_o3c_reaction_r2.py tests/test_o3c_signal_continue.py tests/test_o3c_signal_continue_jev.py tests/test_o3c_signal_explore.py tests/test_o3c_signal_explore5.py tests/test_o3c_signal_materials.py tests/test_o3c_signal_stage2.py tests/test_o3c_signal_value.py tests/test_scalp_logic.py tests/test_o3c_signal_policy.py tests/test_o3c_price_level_ext.py tests/research/test_liq_cascade_v2.py
...
520 passed, 1 warning in 264.17s (0:04:24)
```

(受け持ちの試験 14 本と、組の相手の試験 3 本(`test_o3c_signal_policy.py`・`test_o3c_price_level_ext.py`・`tests/research/test_liq_cascade_v2.py`)。warning は `o3c_signal_materials.py` 768 行の pandas の DtypeWarning で、着手前の回でも出ていた。)

途中で落ちたもの(どちらも直した):
- `tests/test_o3c_oi_distance.py::test_side_spread_block_counts_and_quantiles`: 私が `side_price_spread` を % にした直後に期待値 2.0(bp)で落ちた(`assert 0.02 == 2.0`)。試験を 0.02 に合わせた。
- `tests/research/test_liq_cascade_v2.py::test_no_lookahead_truncate_and_perturb`: `assert n_fin8 > 0` で落ちた。私の直しの前から(作業者 w4 が `docs/DATA/probes/20260920_o3c_cascade_read.py` の帯の鍵を `amt_*bp` → `amt_*pct` に変えたことで)落ちる状態だった(`git diff docs/DATA/probes/20260920_o3c_cascade_read.py` で確かめた。`git stash` は使っていない)。`liq_cascade_v2.py`・`o3c_signal_continue.py` の読み口を新旧の鍵の両方で読むようにして通った。

回していない: `scripts/research_exit_surface.py`(w4)の試験は無い。`tests/test_o3c_signal_explore2.py`(相手 `o3c_signal_explore2.py` は受け持ちだが中身は直していない)も回していない。

## 数

- 受け持ち 41 ファイル: 直した 17(一部だけ直したものを含む: `run_scalp_paper`・`test_scalp_logic`・`replay_scalp_storm`・`research_scalp_exits`・`research_scalp_opt`・`tp_operating_curve`・`o3c_bitflyer_spread`・`o3c_signal_value`・`o3c_signal_policy`・`test_o3c_signal_value`・`o3c_price_level_table`・`o3c_price_level_ext`・`o3c_oi_distance`・`test_o3c_oi_distance`・`o3c_reaction`・`o3c_signal_continue`・`liq_cascade_v2`)、直さない 24(理由は上の表)。
- 組で触った受け持ちの外のファイル: 0(`research_exit_surface.py` は触らず上に書いた)。

## 時刻

- 着手: `Sat Oct 10 00:26:57 JST 2026`
- 終わり: `Sat Oct 10 00:56:26 JST 2026`(報告の本文を書き終えた時刻)
- 見込み(約 2 時間)との差: 約 1 時間 30 分早く終わった。ただし見込みの 50 分を当てた o3c の距離の列の族(「迷ったこと」2)は手を付けずに残したので、その分が早い。上限(02:26 JST)には達していない。

## 続き(リードの決め 1〜4 を受けた直し)

着手: `Sat Oct 10 00:58:56 JST 2026`。上限は着手から 1 時間 30 分(02:28 JST)。コミット・stash・push はしていない。新しい試験は足していない。

### 着手前の表

| やろうとすること | 原文の該当語(逐語) |
|---|---|
| 複数のレグ・取引の損益の和を % にする(連鎖の `pnl_bp`・`費用なしの合計_bp`・katsuo の `total_bp` 3 本)。量 1・1 回の建てから出までは bp のまま | リード「複数のレグや取引の損益を足した和は、1 つの値段の動きではないので bp にしません(% にする)」/ L-920「**bpの意味は「値動き率」としてのみ残し**」 |
| o3c の距離の列の族を族ごと % にする。書き手・読み手・`o3c_reaction_judge.py` を組で直す | リード「o3c の距離の列の族は、族ごと % に直してください」/ L-923「**1.A**」 |
| git の前の表は書き換えず、読む口で古い列を / 100 | リード「読む口で、新しい列が無ければ古い列を /100 して読む形にしてください」 |
| 判定の働き(どの行がどの軸に入るか)を変えない。前と後で同じ判定かを確かめる | リード「判定の働き(どの行がどの軸に入るか)は変えないでください」「前の表で判定を回し直せるなら」 |
| `DAY_EXTREME_EPS_BP` は bp のまま | リード「DAY_EXTREME_EPS_BP は … bp のまま残します」 |
| `research_exit_surface.py`・probes(w4)は触らない | リード「触らないでください」「触らずに報告に書いてください」 |
| 1 時間 30 分で止める | リード「上限は着手から 1 時間 30 分です」 |

完了見込み時間(実測なし): 距離の族の改名(機械)10 分 + 書き手の × 1e4 → × 100 と丸め 15 分 + 読み口(前の表)20 分 + 試験の合わせ 20 分 + 連鎖の損益 15 分 + katsuo 5 分 + 試験を回す 10 分 + 報告 10 分 = 約 105 分。上限 90 分を超えるので、残ったものはここに書く。

### 1. 足し合わせた損益 → %

| ファイル | 前 → 後 |
|---|---|
| `scripts/o3c_signal_policy.py` | `simulate_cascade` の `"pnl_bp": total_pnl`(レグの和)→ `"pnl_pct": total_pnl / 100`。`simulate_baseline`(1 回の建てから出まで)は同じ列に入るので `"pnl_pct": pnl / 100` にそろえた(下の「迷ったこと」A)。行の鍵 `pnl_bp` → `pnl_pct`。分布の関数の既定の列 `col="pnl_bp"` → `"pnl_pct"`。合成の道筋の表示 `_fmt(res["pnl_bp"], 4)` → `_fmt(res["pnl_pct"], 6)`。`レグ損益_bp`(量 1 の 1 レグ)は bp のまま |
| `scripts/o3c_signal_value.py` | `simulate_reverse_entry` の `pnl_bp` → `pnl_pct`(= bp / 100。同じ列にそろえる)。連鎖 1 本ごとの行の列 `pnl_bp` → `pnl_pct`(`CASCADE_COLUMNS` も)。ネット `pnl_net_pct` = `pnl_pct − c × 建玉の回数`(前の回の `pnl_bp / 100 − …` を書き直した。値は同じ)。`費用なしの合計_bp`(2925 行、レグの和)→ `費用なしの合計_pct` = 和 / 100。合成の道筋の列 `費用なしの損益_bp` → `費用なしの損益_pct`(6 桁)。前の `cascades.csv.gz` を読む `_with_pct_columns` に `pnl_pct` が無ければ `pnl_bp / 100` を足した |
| `src/bot/research/liq_cascade_v2.py` | docstring の `pnl_bp` を `pnl_pct`(レグの和 / 100)と書き直した(この台本は状態機械の結果をそのまま返す) |
| `scripts/measure_katsuo_judgement_vol.py`・`_vol_bitflyer.py`・`_xvenue.py` | `"total_bp": round(sum(rs), 1)` → `"total_pct": round(sum(rs) / 100, 3)`(丸めは前の 1 桁と同じ細かさ) |
| `scripts/render_k1_judgement.py`・`render_k1_fresh_bitflyer.py`・`render_k1_xvenue.py`・`render_k1_xvenue2.py`(組の読み手) | 三分位ごとの総損益を `_total_pct_str(b)` で読む: `total_pct` があればそれを、無ければ(前の出力)`total_bp / 100` を % で出す |
| 試験 `tests/test_o3c_signal_policy.py`・`tests/test_o3c_signal_value.py`・`tests/research/test_liq_cascade_v2.py` | 鍵を `pnl_pct` に。レグの和との一致は `leg_sum / 100 == pnl_pct` に。場面の値 `pnl_bp: 10.0 / 4.0` → `pnl_pct: 0.10 / 0.04` |

確かめ(% × 100 = 前の bp。型 B のドテン 1 回、建玉 2 回):
```
$ cd scripts && PYTHONPATH=../src python3 -c "... sp.simulate_cascade(prints, [STOP, CONTINUE], -1.0, TYPE_B, 0, price_fn, end) ..."
pnl_pct x100 = -0.4499910001357256  sum of legs (bp) = -0.4499910001357257  n_entries = 2
```

### 2. o3c の距離の列の族 → %

- 名前(機械の置き換え、27 ファイル・281 行): `dist_(node|vwap|gap)_bp` → `dist_\1_pct`(`oi_`・`oi_side_`・`_liqdir`・`_median_by_side` も同じ規則でかかる)、`node_up_bp`・`node_dn_bp`・`directional_node_bp`・`_nearest_signed_bp` → `_pct`、`mat8_amt_5bp` → `mat8_amt_0p05pct`、`mat8_amt_20bp` → `mat8_amt_0p2pct`、`oi_ahead_20bp` → `oi_ahead_0p2pct`。対象: 書き手 `o3c_price_level_table`・`o3c_reaction`・`o3c_oi_distance`・`o3c_price_level_ext`、読み手 `o3c_reaction_r2`・`o3c_signal_continue`・`o3c_signal_explore`・`_explore2`・`_explore4`・`_explore5`・`o3c_jev_state`・`liq_cascade_v2`、判定 `o3c_reaction_judge`、試験 14 本(`test_o3c_signal_explore2.py`・`test_o3c_price_level_ext.py` を含む)。
- 単位(書き手): `o3c_price_level_table._nearest_signed_pct`・`profile_stats` の `dist_vwap` を `× 1e4` → `× 100`。`o3c_reaction.directional_node_pct` も同じ。到達の目標の値段 `p_liq × (1 + d / 1e4)` → `/ 100`。`o3c_oi_distance` の `implied_leverage = 1 / (d / 1e4 + mmr)` → `d / 100`。`o3c_price_level_ext` の帯の offset `-中央値 / 1e4` → `/ 100`。丸めは % で 6 桁(= 前の bp の 4 桁と同じ細かさ): 書き手 4 本の `round(…, 4)` と `_liqdir` の丸め、`o3c_signal_explore5` の `_num(…, 4)`、判定の `matched_partner_sign_axis` の丸め。
- 読み口(前の表): `o3c_price_level_table` に `legacy_pct_name`・`pct_dist_row`・`pct_dist_frame`・`legacy_usecols` を足した(新しい名前の列が無ければ古い列を読んで / 100。`mat8_amt_*` は帯の名前だけ変わり、値は建玉の量なので割らない)。使った所: `o3c_signal_continue`(`PrintsCSV`・`read_stage1_frame`・`load_rows`)、`o3c_jev_state`(`rows_continue` の読み。`config/o3c_jev_state_bands.yaml` の鍵 `oi_ahead_20bp` は `load_bands_yaml` で新しい鍵に写す。yaml は書き換えていない)、`o3c_signal_explore2`(`table.csv`・rows)、`_explore4`・`_explore5`(rows)。`o3c_reaction_r2._read_cols`(これを `o3c_signal_explore` も使う)と `o3c_reaction_judge.Run`(`_pct_dist_row`)は自前の小さな読み替えを足した(判定の台本は他の台本を import していないので)。
- 判定の台本 `o3c_reaction_judge.py` の軸 A2〜A5: 確かめたところ、**bp の値の閾値を持っていない**。軸は走行ごとの 3 分位(`tertile_cuts`)で切る(916-936 行)。なので、事前登録の逐語として残す bp の数も無かった。名前の対応(`LIQDIR_SOURCE`・`CONTROL_AXIS_KIND`・`AXES_W`)は `*_pct*` に変えた。MDE の単位の表(`UNIT_BP` = 価格変化・最大順行 / 逆行)は値動き率なので変えていない。
- 前と後で同じ判定か: **git の前の表(`backtest_data/o3c_reaction_20260918_full/*/table.csv`)で判定を回し直すことはしていない**。その `summary.json` の `params.days` が 2024-10-12 まで入っていて、REST_RULES §4「2023-12-17T15:00Z より後のデータを読まない」に当たるため。代わりに、試験の合成の走行(`tests/test_o3c_reaction_judge.py` の `make_run`)で、新しい列の表と、同じ値を古い名前・bp(× 100)に書き直した表を作り、判定の台本の群の所属(群ごとの実群・一様対照・合わせた対照の行の番号)と A2〜A5 の 3 分位の切り値、計 168 項目を比べた(作業用の置き場の使い捨ての台本。リポジトリに入れていない):
  ```
  $ PYTHONPATH=src python3 check_judge_legacy.py <tmp>
  groups: 168 identical membership: True
  differing: []
  ```
- probes(w4 の受け持ち、触っていない): `docs/DATA/probes/20260919_o3c_reaction_bugcheck.py`・`_bugcheck2.py`・`_r1_bp_reactdir_standardized.py` は w4 がこの回に古い列を / 100 して `dist_*_pct` で読むように直している。`20260919_jev_select_rank_probe.py` も `dist_vwap_pct` の説明文に変わっている。`20260920_o3c_cascade_read.py` は鍵を `amt_*pct` に変えている(前の回に読み手を合わせた)。`20260920_o3c_jev_state_proto.py`・`20260920_o3c_signal_continue_refuter.py`・`20260920_o3c_signal_explore5_refuter.py` は古い名前(`dist_node_bp`・`mat8_amt_*bp`)のままで、私の台本の**新しい**出力では止まる(前の表なら読める)。

### 3・4

- `DAY_EXTREME_EPS_BP` は bp のまま(変えていない)。
- `research_exit_surface.py` は触っていない。

### 試験(続きの直しの後)

```
$ PYTHONPATH=src python -m pytest tests/test_o3c_jev_state.py tests/test_o3c_oi_distance.py tests/test_o3c_price_level_table.py tests/test_o3c_reaction.py tests/test_o3c_reaction_judge.py tests/test_o3c_reaction_r2.py tests/test_o3c_signal_continue.py tests/test_o3c_signal_continue_jev.py tests/test_o3c_signal_explore.py tests/test_o3c_signal_explore2.py tests/test_o3c_signal_explore5.py tests/test_o3c_signal_materials.py tests/test_o3c_signal_stage2.py tests/test_o3c_signal_value.py tests/test_scalp_logic.py tests/test_o3c_signal_policy.py tests/test_o3c_price_level_ext.py tests/research/test_liq_cascade_v2.py tests/test_k1_xvenue.py
539 passed, 1 warning in 354.75s (0:05:54)
$ PYTHONPATH=src python -m pytest tests/test_o3c_price_level_ext.py     # 走らせた後に文だけ直したので回し直した
6 passed in 1.35s
```
途中で落ちて直したもの(どれも試験の期待値が bp のままだったもの。台本の値が 1/100 になったことの確かめでもある): `test_o3c_oi_distance::test_single_bucket_profile_matches_bin_center`(`assert -0.951128 == -95.1128`)、`test_o3c_price_level_table` の 2 件(`0.1000… == 10.0`・`-0.1997… == -20.0`)、`test_o3c_reaction::test_profile_columns_match_base_profile_stats_on_a_hand_window`(丸めの桁 4 → 6)。

### 迷ったこと・リードの判断が要るもの(続き)

A. **1 回の建てから出まで(量 1)の損益も、連鎖の損益と同じ列に入るものは % にそろえた**。`o3c_signal_policy.simulate_baseline` と `o3c_signal_value.simulate_reverse_entry` は量 1・1 回だが、`pnl_pct` の列(連鎖の和)に一緒に入るので、列の単位を 1 つにするために % にした。リードの決め(量 1・1 回は bp のまま)と 1 か所ずれている。
B. **受け持ちの外で、今は止まる読み手**(触っていない):
   - `scripts/c9_run_a.py` 175・182・494 行と `docs/RESEARCH/cards/c9_liquidation_cascade/run_a/three_way_m_policy.py` 95 行が `liq_cascade_v2.simulate_bundle` の結果を `res["pnl_bp"]` で読む → `KeyError`。`pnl_pct`(連鎖の和 / 100)に合わせる必要がある。175 行は基準の結果を `レグ損益_bp` に入れているので、`pnl_pct × 100` で入れる必要がある。`docs/RESEARCH/cards/c9_liquidation_cascade/run_a/make_tables.py` は保存した c9 の出力の `pnl_bp` を読む。
   - probes の 3 本(上の 2 の最後)。
C. **材料 5 `mat5_distance_to_liquidation_node` の値は、名前を変えずに bp から % になった**(`o3c_signal_continue` 517 行・`liq_cascade_v2` 1107 行が `dist_node_pct` を入れる)。名前に単位が無いので、前に書いた `rows_continue.csv.gz` ほか(bp)と新しい出力(%)を名前では区別できない。材料の分位は走りごとに切っているので判定は変わらないが、前と後の出力を混ぜて読むと 100 倍ずれる。名前を変える(`MAT_COL[5]` は `jev`・c9 の台本が読む)かはリードの判断。
D. `o3c_signal_value.append_csv_gz` で前の `cascades.csv.gz`(列 `pnl_bp`・`pnl_net_bp`)に新しい行(列 `pnl_pct`・`pnl_net_pct`)を継ぎ足すと、列がそろわない。前の回の段 2 の後半の利確の追加(`tp_append_summary.json`)をやり直すときに当たる。今は走らせない道筋なので直していない。
E. katsuo の描画の台本 4 本は、三分位ごとの総損益だけ % にした。各台本が自分で計算する年別の総損益(`total_of` = n × mean_bp、これも取引の和)は bp のまま(リードの決めの対象に挙がっていなかったので)。同じ表の中に bp の和と % の和が並ぶ。

### 時刻(続き)

- 着手: `Sat Oct 10 00:58:56 JST 2026`
- 終わり: `Sat Oct 10 01:15:17 JST 2026`(本文を書き終えた時刻)。見込み約 105 分に対し約 17 分。上限の 02:28 JST の前。

## 続き 2(リードの決め A〜E を受けた直し)

着手: `Sat Oct 10 01:15:56 JST 2026`。上限は着手から 1 時間(02:15 JST)。コミット・stash・push はしていない。新しい試験は足していない。w1 の受け持ち(phase2・xborder・overnight)には触っていない。

### 着手前の表

| やろうとすること | 原文の該当語(逐語) |
|---|---|
| 量 1 の損益を連鎖の和と同じ列で % にした件を、決めとずれる理由として書く | リード「1 つの列は 1 つの単位にします。報告に、決めとずれる理由として書いておいてください」 |
| c9 の 2 本と probes 3 本を、新しい名前を読み、無ければ古い名前を / 100 して読む形にする | リード「止まる読み手を直してください」「新しい名前を読み、無ければ古い名前を /100 して読む形にしてください」 |
| 材料 5 の列の名前に単位を入れ、読み手を組で直す | リード「名前で単位が分からない列を残さないでください」 |
| 前の cascades.csv.gz に継ぎ足す口で、見出しが違えば止める | リード「見出しが違えば止めるようにしてください」 |
| katsuo の描画の年別の総損益も % にする | リード「同じ表の中で単位を 1 つにしてください」 |
| 1 時間で止める | リード「上限は 1 時間です」 |

完了見込み時間(実測なし): D 5 分 + E 10 分 + C 15 分 + B(c9 2 本・probes 3 本)20 分 + 試験 10 分 + 報告 10 分 = 約 70 分。上限 60 分を超えるので、入らなかったものはここに書く。

### A. 決めとずれる所(理由)

`o3c_signal_policy.simulate_baseline` と `o3c_signal_value.simulate_reverse_entry` の損益は、量 1・1 回の建てから出まで(値動き率)。それでも `pnl_pct`(%)にした。理由は、連鎖の損益(レグの和)と同じ列 `pnl_pct` に入るからで、1 つの列を 1 つの単位にするため(リードの決め A)。同じ理由で、次の 3 か所の「1 レグ」も、連鎖と同じ表に並ぶので / 100 して % で出している(レグの断片のファイル `policy_legs*.csv.gz` の `pnl_bp` は、1 レグ = 値動き率なので bp のまま):
- `scripts/c9_run_a.py` の `dist_policy` の「1レグ」の行
- `make_tables.py` の t6a の「1 レグ」の行
- `c9_redo.py` の D4

### B. 止まる読み手の直し

| ファイル | 直したこと |
|---|---|
| `src/bot/research/liq_cascade_v2.py`(受け持ち) | 読み手のための関数を足した: `LEGACY_COLS`(前の列 → 今の列と掛ける数: 材料 5 は / 100、`mat8_amt_5bp`・`_20bp` は名前だけ、`pnl_bp` は / 100)、`legacy_usecols`、`with_legacy_columns`、`chain_pnl_pct(res)`(`pnl_pct` を読み、無ければ `pnl_bp / 100`) |
| `scripts/c9_run_a.py` | 175 行: 基準のレグの損益を `chain_pnl_pct(res) × 100`(1 レグなので bp)。182・494 行: 連鎖の行の列を `pnl_pct`(`chain_pnl_pct(res)`)。`read_chunks` が前の日の断片(`pnl_bp`・名前に単位の無い材料 5)を読むときは、今の名前が無ければ古い列を読み、/ 100 して今の名前で足す。集計は `rows["pnl_pct"]` を使う。1 レグの分布は / 100(上の A) |
| `docs/RESEARCH/cards/c9_liquidation_cascade/run_a/three_way_m_policy.py` | 95 行: 連鎖の行の列を `pnl_pct`(`chain_pnl_pct(res)`)。`anchors_prints.csv.gz` の読みで、材料 5 の今の名前が無ければ古い列を / 100 |
| `docs/RESEARCH/cards/c9_liquidation_cascade/run_a/three_way_m.py`(組) | `anchors_prints.csv.gz` の読みを同じ形に(前の出力の材料 5 で `KeyError` にならないように) |
| `docs/RESEARCH/cards/c9_liquidation_cascade/run_a/make_tables.py`(組。上の 2 本の出力 `policy_cascades*.csv.gz` を読む) | `CA`・`CA3`・`OC`・`RUNC` を `with_legacy_columns(keep={"pnl_pct"})` で読み、`pnl_bp` → `pnl_pct`(突き合わせの列 `pnl_bp_n/_r` も `pnl_pct_n/_r`)。t6a の 1 レグは / 100 |
| `docs/RESEARCH/cards/c9_liquidation_cascade/redo2_2026-10-05/c9_redo.py`(組。同じ出力を読む) | `policy_cascades.csv.gz` の `pnl_pct` が無ければ `pnl_bp / 100`。`policy_legs.csv.gz` の 1 レグは / 100 して、和を出す表(D4)にそろえた。損益の和・平均の表示の桁を増やし(和 `.0f` → `.3f`、平均 `f2(…, 2)` → 4・5 桁)、見出しの「bp/日」「1 連鎖あたり bp」「1 レグあたり bp」を % にした。値動き(D5・s 秒の曲線)は bp のまま |
| `docs/DATA/probes/20260920_o3c_jev_state_proto.py` | `rows_continue` に今の名前(`mat8_amt_0p05pct`・`mat8_amt_0p2pct`・`mat5_distance_to_liquidation_node_pct`)が無ければ古い列から作る(材料 5 は / 100)。帯の名前 `oi_ahead_20bp` → `oi_ahead_0p2pct`、文の「within 20 bp / 5 bp」→「0.2 % / 0.05 %」 |
| `docs/DATA/probes/20260920_o3c_signal_continue_refuter.py` | `MAT_VAR[5]` を `distance_to_liquidation_node_pct` に。`rows_continue` に今の名前が無ければ古い列を / 100。`PrintsCSV` に渡す合成の行の `dist_node_bp: -12.5` → `dist_node_pct: -0.125` |
| `docs/DATA/probes/20260920_o3c_signal_explore5_refuter.py` | rows に `dist_node_pct` が無ければ `dist_node_bp / 100`(2 か所の読み)。属性の名前 `|dist_node_bp|` → `|dist_node_pct|` |

### C. 材料 5 の名前

- `o3c_signal_continue.MAT_VAR[5]`: `distance_to_liquidation_node` → `distance_to_liquidation_node_pct`。列は `mat5_distance_to_liquidation_node_pct`。`liq_cascade_v2.MAT_COL[5]` も同じ名前にした。
- 前の出力の読み口: 前の列 `mat5_distance_to_liquidation_node`(名前に単位が無い bp)を / 100 して今の名前で足す。これを使う所は次のとおり。
  - 前の回に足した関数(`o3c_price_level_table` の `legacy_pct_name` の表に足した)を通す所: `o3c_signal_continue.load_rows` / `read_stage1_frame`、`o3c_jev_state` の `rows_continue` の読み、`o3c_signal_continue_jev.load_rows`(組の読み手。直す前は前の `rows_continue` を読むと材料 5 が黙って空になっていた)。
  - `liq_cascade_v2.LEGACY_COLS` を通す所: c9 の読み手(上の B)。
- `o3c_signal_materials` は材料 5 を読まない(`EXIST_NUMS` から 5 を外している。775 行のコメント)ので触っていない。
- Jev に渡す材料の鍵(`o3c_signal_continue_jev` の `materials[MAT_VAR[n]]`)も `distance_to_liquidation_node_pct` になる。Jev への入力の文字が変わる。
- 同じ所で、Jev の文の帯の幅「within 20 bp / 5 bp」を「within 0.2 % / 0.05 %」にした(`o3c_jev_state._sent11`。試験 `tests/test_o3c_jev_state.py` の期待の文字列も合わせた)。

### D. 継ぎ足しの口

`o3c_signal_value.append_csv_gz`: 前のファイルの見出しと、足す行の鍵が違えば止める。止める文は、見出しにあって行に無い列・行にあって見出しに無い列と、どうすればよいか(今の台本で作り直す / 別のファイルに書く)を書く。確かめ(作業用の置き場の一時ファイル):
```
[止め] cascades.csv.gz の見出しと足す行の列が違う。見出しにあって行に無い列: ['pnl_bp', 'pnl_net_bp'] / 行にあって見出しに無い列: ['pnl_net_pct', 'pnl_pct']。L-920 より前に書いたファイル(bp の列名)に、% の列名の行を継ぎ足そうとしている可能性がある。ファイルを今の台本で最初から作り直すか、継ぎ足さずに別のファイル(例: cascades_pct.csv.gz)に書くこと
```
既存の試験 `test_appending_rows_keeps_every_existing_byte` は同じ列どうしなので止まらない(下の試験で通った)。

### E. katsuo の描画の台本

`render_k1_judgement.py`・`render_k1_fresh_bitflyer.py`・`render_k1_xvenue.py`・`render_k1_xvenue2.py`:
- `total_of`(年別の総損益 = n × mean_bp)を `/ 100` して % にし、丸めは 1 桁 → 3 桁にした。
- 同じ形の式(`round(p["n"] * p["mean_bp"], 1)`)も同じに直した。4 本で 15 か所。
- 表示 `fmt0` を `+,.3f%` に、見出し「年別 n・総損益(bp)」を「(%)」にした。
- 前の回に直した三分位の総損益(`_total_pct_str`)と合わせて、同じ表の総損益の列は全部 % になった。
- 平均(`mean_bp`、1 取引の値動き率)は bp のまま。
- 走らせては確かめていない(入力の一部が 2022〜2026 の記録で、日付の決まりに当たる)。`py_compile` だけ通した。
- 同じ形の和を持つほかの描画の台本(`render_k1_h3.py`・`render_k1_yearly_pnl.py`)は、リードの対象に挙がっていないので触っていない。

### 試験(続き 2 の直しの後)

```
$ PYTHONPATH=src python -m pytest tests/test_o3c_jev_state.py tests/test_o3c_oi_distance.py tests/test_o3c_price_level_table.py tests/test_o3c_reaction.py tests/test_o3c_reaction_judge.py tests/test_o3c_reaction_r2.py tests/test_o3c_signal_continue.py tests/test_o3c_signal_continue_jev.py tests/test_o3c_signal_explore.py tests/test_o3c_signal_explore2.py tests/test_o3c_signal_explore5.py tests/test_o3c_signal_materials.py tests/test_o3c_signal_stage2.py tests/test_o3c_signal_value.py tests/test_scalp_logic.py tests/test_o3c_signal_policy.py tests/test_o3c_price_level_ext.py tests/research/test_liq_cascade_v2.py tests/test_k1_xvenue.py
539 passed, 1 warning in 328.84s (0:05:28)
```

試験の無いもの(c9 の 4 本・probes 3 本・描画の台本 4 本)は `python3 -m py_compile` だけ通した。走らせてはいない(入力の記録が 2023-12-17 より後の日を含むため)。読み口の関数は小さな入力で確かめた:
```
$ PYTHONPATH=src python3 -c "... v2.legacy_usecols(p, ['print_id', v2.MAT_COL[5]]) ... v2.chain_pnl_pct(...)"
['print_id', 'mat5_distance_to_liquidation_node'] [0.564]      # 前の列 56.4(bp)を読んで / 100
0.12 0.12                                                        # pnl_pct 0.12 と、前の pnl_bp 12.0 / 100
```

### 残り・リードの判断が要るもの(続き 2)

- `o3c_jev_state._sent11` の「Nearest liquidation level …: N bp away」の `cand_5p`(節までの距離)は、受け持ちの外の `o3c_signal_materials.node_ahead_bp_batch` が bp で作る列なので、bp のまま残した。同じ文の中で帯は %、節までの距離は bp になっている。`o3c_signal_materials`(`node_ahead_bp_batch`・`cand_5p`)を直すかはリードの判断。
- `render_k1_h3.py`・`render_k1_yearly_pnl.py` にも同じ形の年別の和(n × mean_bp)がある(触っていない)。

### 時刻(続き 2)

- 着手: `Sat Oct 10 01:15:56 JST 2026`
- 終わり: `Sat Oct 10 01:26:26 JST 2026`
- 見込み約 70 分に対して実際は約 11 分(c9_redo・make_tables の和の桁の直しは、見込みに無かった作業として足した)。上限(02:15 JST)の前。

## 続き 3(リードの決め 1・2 を受けた直し)

着手: `Sat Oct 10 01:26:51 JST 2026`。上限は着手から 40 分(02:06 JST)。コミット・stash・push はしていない。新しい試験は足していない。

### 着手前の表

| やろうとすること | 原文の該当語(逐語) |
|---|---|
| `node_ahead_bp_batch`(節までの距離)を %(関数名・出力の名前・作り手と読み手を組で)。Jev の文も帯と同じ % に。前の出力は / 100 して読む | リード「% に直してください(関数名と出力の名前、作り手と読み手を組で)」「帯と同じ % にそろえてください」「前の出力の古い名前は /100 して読んでください」 |
| `render_k1_h3.py`・`render_k1_yearly_pnl.py` の年別の和を % にする | リード「同じ表の中の単位を 1 つにしてください」 |
| 関係する試験を回し、報告に「続き 3」を足す | リード「関係する試験を回し、報告に節「続き 3」を足して返してください」 |
| 40 分で止める | リード「上限は 40 分です」 |

完了見込み時間(実測なし): 1 の作り手・読み手・試験 15 分 + 2 の 2 本 5 分 + 試験 5 分 + 報告 5 分 = 約 30 分。

### 1. 節までの距離(候補 5')

| ファイル | 前 → 後 |
|---|---|
| `scripts/o3c_signal_materials.py`(作り手) | 関数 `node_ahead_bp_batch` → `node_ahead_pct_batch`、`dist / p_ref × 1e4` → `× 100`(docstring も %)。候補の名前 `"5p"` → `"5p_pct"`、出力の列 `cand_5p` → `cand_5p_pct`(丸め 6 桁 → 8 桁 = 前の bp の 6 桁と同じ細かさ)。`--stage resummarize` で前の `rows_materials.csv.gz` を読む口は、`cand_5p_pct` が無ければ `cand_5p / 100`(`base.pct_dist_frame`) |
| `scripts/o3c_price_level_table.py` | 前の列 → 今の列の表(`legacy_pct_name`)に `cand_5p` → `cand_5p_pct`(/ 100)を足した |
| `scripts/o3c_jev_state.py`(読み手) | `rows_materials` を `pct_dist_frame` を通して読む(前の `cand_5p` は / 100)。Jev の文の節までの距離を `{d:.0f} bp away` → `{d:.2f} % away`(帯の「within 0.2 % / 0.05 %」と同じ %。.2f は前の bp の整数と同じ細かさ) |
| `docs/DATA/probes/20260920_o3c_jev_state_proto.py`(読み手) | `rows_materials` に `cand_5p_pct` が無ければ `cand_5p / 100`。文を `{abs(d):.2f} % away` に |
| 試験 `tests/test_o3c_signal_materials.py` | 関数名を合わせ、期待値 約 500(bp)・許し 15 / 60 → 約 5.0(%)・0.15 / 0.60 |
| 試験 `tests/test_o3c_jev_state.py`・`tests/test_o3c_signal_stage2.py` | 場面の鍵 `cand_5p` → `cand_5p_pct`、値 -14.2 → -0.142、-3.0 → -0.03。期待の文「14 bp away」→「0.14 % away」 |

残っている `cand_5p`・`node_ahead_bp` の字は、前の名前を読む口(読み替えの表とコメント)だけ:
```
$ git ls-files -z -- '*.py' ':!docs/RESEARCH/WINDOW1' ':!backtest_data/phase2_sealed' | xargs -0 grep -nE "cand_5p\b|node_ahead_bp"
(出力) docs/DATA/probes/20260920_o3c_jev_state_proto.py:4:# L-920: 前の rows_materials の cand_5p(先の節までの距離、bp)は / 100 して cand_5p_pct で読む
(出力) docs/DATA/probes/20260920_o3c_jev_state_proto.py:5:if 'cand_5p_pct' not in M.columns and 'cand_5p' in M.columns:
(出力) docs/DATA/probes/20260920_o3c_jev_state_proto.py:6:    M['cand_5p_pct'] = pd.to_numeric(M['cand_5p'], errors='coerce') / 100
(出力) scripts/o3c_jev_state.py:555:        # L-920: 前の rows_materials の cand_5p(節までの距離、bp)は / 100 して cand_5p_pct で読む
(出力) scripts/o3c_price_level_table.py:64:                 # o3c_signal_materials の候補 5'(先の節までの距離)。前は cand_5p(bp)→ / 100
(出力) scripts/o3c_price_level_table.py:65:                 "cand_5p": "cand_5p_pct"}
(出力) scripts/o3c_signal_materials.py:245:    前は node_ahead_bp_batch で × 1e4 の bp)。先に無ければ NaN。
(出力) scripts/o3c_signal_materials.py:813:    # L-920: 前の rows_materials の節までの距離は cand_5p(bp)。今の cand_5p_pct が無ければ / 100
```

% × 100 = 前の bp の確かめ: `test_o3c_signal_materials` の `node_ahead_pct_batch` の値が、前の期待値 約 500(bp)の 1/100(約 5.0)の許しの中で通った(下の試験)。

### 2. katsuo の描画の台本の残り 2 本

`scripts/render_k1_h3.py`・`scripts/render_k1_yearly_pnl.py`:
- `total`(年別の総損益 = n × mean_bp)を `/ 100` して % にした。
- 表示 `fmt0` / `fmt` を `+,.3f%` に、表の見出しと説明の文の「総損益 bp」を「%」にした。
- これで表の総損益(年別・全期間の合計)は全部 %。平均・分位(1 取引の値動き率)は bp のまま。
- 走らせてはいない。入力の Binance の JSON の期間が日付の決まりに当たるかを確かめていないため。`py_compile` だけ通した。

### 試験(続き 3 の直しの後)

```
$ PYTHONPATH=src python -m pytest tests/test_o3c_jev_state.py tests/test_o3c_signal_materials.py tests/test_o3c_signal_stage2.py tests/test_o3c_signal_continue_jev.py tests/test_o3c_signal_continue.py tests/test_o3c_price_level_table.py tests/test_k1_xvenue.py
102 passed, 1 warning in 11.98s
```
(warning は前と同じ `o3c_signal_materials.py` の pandas の DtypeWarning。)

### 時刻(続き 3)

- 着手: `Sat Oct 10 01:26:51 JST 2026`
- 終わり: `Sat Oct 10 01:28:51 JST 2026`(見込み約 30 分に対して実際は約 2 分。上限 02:06 JST の前)
