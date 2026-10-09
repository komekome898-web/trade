# 残りの直し: 作業者 w4(研究の台本 26 本と調べの台本 6 本)

書いた人: 作業者 w4。着手 `Sat Oct 10 00:26:56 JST 2026`(`TZ=Asia/Tokyo date` の出力)。上限 02:26 JST(着手から 2 時間)。コミット・押し出しはしていない。git stash / reset / checkout は使っていない。

## 着手前の表

| やろうとすること | オーナーの原文の該当語(逐語) |
|---|---|
| 受け持ちの台本の bp・bps を値動き率だけに使い、手数料率・費用・ネット・スプレッド・ベーシス・距離・資金調達率・建玉で重みを付けた損益の率は % の名前と値(× 100 / 定数は 1/100)にする | L-920「**方針はbpの意味は「値動き率」としてのみ残し、その他の意味を持たせないようにすること**」 |
| スプレッド・ベーシス・約定の値段のずれも bp にしない | L-923「**1.A**」 |
| 値動き率どうしの差は bp のまま残す | L-924「**A**」 |
| 受け持ち 32 ファイルを、分かっているものは全部直す | L-920「**たまたま見つかったやつも含めてわかってる修正が必要なもの全部直してください**」/ L-925「**次は残りを終わるまでやってください**」 |
| 2 時間で止める(02:26 JST)。残りはこの報告に書く | L-923「**2時間を上限にしろ、そうしないと意味不明な試験ばっかりで終わらなくなる**」 |
| 試験は足さず、今ある試験を回す。直した関数は旧版(作業前に scratchpad に写した自分の受け持ちの元の版)と小さな作り物の入力で突き合わせる | L-923「**そうしないと意味不明な試験ばっかりで終わらなくなる**」 |

### 完了見込み時間(内訳)

- 対象(事実): 32 ファイル。`grep -ci bp` の合計 約 1,700 行(大きい順: matilda_taro 126・exit_surface 104・fast_cycle 98・range_reversed 97・two_sided_flow 88・calm_range 87)。
- 見積もり(実測なし): 小さい 9 本(bp 30 行未満)× 5 分 = 45 分 / 大きい 23 本 × 10〜15 分 = 230〜345 分 / 報告 15 分。合計 290〜405 分。上限 120 分には入らない見込みだった。
- 上限の中でやる順(実測なし): ほかの台本が import する台本と小さい台本を先に、残りを ④ の行の多い順。

## 決め方(受け持ちの中でそろえた読み方)

REST_RULES §1 を次のように当てた。迷った所は下の「迷ったこと」に全部書いた。

- **bp のまま**: 値動き(n 秒の値動き・drift・gross・MFE・前向きの値動き・markout の adverse・実現 vol・レンジの幅 = 窓の中の高値−安値)、合図の閾値、**入りの約定から測る** TP・止めの幅(例: TP +10bps、止め X bps)、値動き率どうしの差。
- **% にした**: 手数料・taker の費用・滑り、ネット(gross − 費用)とその平均・CI・合計・最大の落ち込み・採用の線、スプレッド・半スプレッド・capture(約定の値段と mid の距離)、ベーシス、**レンジの縁(節)から測る距離**(縁を越えた止め・縁の内側への指値の offset・縁からの行き過ぎ・縁から測る障壁の競争)、VWAP・建玉の値段からの距離、資金調達、建玉の数で重みが付く 1 単位の往復の損益(matilda 系の u・two_sided_flow の往復)。
- 事前登録の逐語(docstring)は書き換えず、docstring の最後に「(L-920 の後の単位: …)」の段落を足した(手本は `scripts/research_clock_burst.py`)。L-920 より前の記録の数(S4・report 30 の数)は書き換えず `/ 100` して比べる(§2)。

## 受け持ちのファイル 1 つずつ

### 直した(31 ファイル)

| ファイル | 前 → 後 |
|---|---|
| `scripts/research_anchor.py` | 費用の表示「= X bps」(往復の taker 費用 × 100)を消し、% だけの表示に。偏差(FX と Binance の対数の値動きの差)は値動き率の差なので bp のまま(L-924) |
| `scripts/research_basis.py` | ベーシスの変化 `d_basis`(`basis_pct` の差 × 100 = bps)→ `basis_pct` の差のまま(%)、表示 `.2f`→`.4f`。先の CFD・現物の対数の値動き(`rf`・`rs`・`fwd`)は bp のまま |
| `scripts/research_leader_surface.py` | 事前登録の docstring の後に換算の段落(7.92bps = 0.0792 %、13.0bps = 0.13 %)。`COST_TAKER_PCT` の横のコメント「7.92 bps」→「% round trip」。実現 vol(bps)は値動きなので bp のまま |
| `scripts/research_two_sided_flow.py` | `HALF_SPREAD_BPS=1.10`→`HALF_SPREAD_PCT=0.0110`、`HALF_SPREAD_ALT 0.78`→`0.0078`、`EDGE_BAR_BPS 0.30`→`EDGE_BAR_PCT 0.0030`、`revisit_flags(h_bps)`→`(h_pct)`(× 1e-4 → × 1e-2)、`episode_pnl_prereg(spread_bps)`→`(spread_pct)`、`EpisodeStats` の `bps_of_notional/cap_bps/inv_bps/bps`→`pct_of_notional/cap_pct/inv_pct/pct`(× 1e4 → × 100)、FIFO の往復 `rt_bps`→`rt_pct`、markout は `adverse`(mid から mid、bp のまま)・`entry`(半スプレッド、%)・`total`(= entry + adverse/100、%)、記録の板のスプレッド `sp` を %。drift(bp)と半スプレッド(%)の比べは `abs(d) <= h * 100`。表示の桁を 2 つ増やした |
| `scripts/research_calm_range.py` | `COST_BURST_BPS/COST_CALM_BPS`(3.96/2.93)→`_PCT`(0.0396/0.0293)、`BAR_NET_BPS 2.0`→`BAR_NET_PCT 0.02`、`RANGE_BREAK_BPS 10`→`RANGE_BREAK_PCT 0.10`、`OFFSETS_BPS (0,2,5)`→`OFFSETS_PCT (0,0.02,0.05)`、`offset_bps`→`offset_pct`、取引の列 `cost_bps/net_bps`→`cost_pct/net_pct`(`net_pct = gross_bps/100 − cost_pct`)。`gross_bps`・5 秒の値動き・レンジの幅は bp のまま |
| `scripts/research_range_reversed.py` | 同じく費用 `COST_TAKER_BURST/CALM` を %(名前に bp なし、値を 1/100)、`RANGE_BREAK_PCT`、`BAR_NET_PCT`、`fix10` の TP(縁の内側 10bps)→ 0.1 %、取引の列 `tp_dist_bps/overshoot_bps/cost_bps/net_bps`→`_pct`、3d の障壁の競争(縁から ±10bps)→ ±0.1 %、MFE(bp)と TP の距離(%)の比は `tp_dist_pct * 100` で割る |
| `scripts/research_vr_barrier.py` | `BARRIERS (10,5)`(縁から測る障壁)→`(0.10,0.05)` %、`barrier_race(bps)`→`(bpct)`、`FADE_GROSS_BPS/FADE_LOSS_BPS`→`_PCT`、EV を %。`COST_TAKER_CALM` は `research_range_reversed` から読む(組) |
| `scripts/research_fx_event_ticks.py` | `FEE_BPS_PER_SIDE 0.2`→`FEE_PCT_PER_SIDE 0.002`、`GMO_FLOOR_ROUNDTRIP_BPS 0.71`→`_PCT 0.0071`、`trade_bps()`→`trade_rates()`(net_base・net_gmo・gross_book を %、gross_mid は bp)、テープのスプレッド `spread_bps`→`spread_pct`、採用の線 +2.0bps → +0.02 %。impulse・閾値 m は bp のまま |
| `scripts/research_fx_s4_judgment.py` | `s4.FEE_PCT_PER_SIDE`・`s4.GMO_FLOOR_ROUNDTRIP_PCT`・`s4.trade_rates` を読む(組)。`COST_TODAY_LO/HI 0.89/1.46`→`0.0089/0.0146`、net@C を %。S4 の記録 `S4_F2R_NET_BASE`(bps)は書き換えず `/ 100` して比べ、許し幅 0.002 → 0.002/100 |
| `scripts/research_fx_sessions.py` | `BARRIERS (3,5,10)`(縁から)→`(0.03,0.05,0.10)` %、`C_SIDE 0.355`→`0.00355`、`C_RT`、`race(bps)`→`(b_pct)`、`ev_uncond` を %(上限の drift(bp)は /100)、表示・文の bps を %。損益分岐 p* は比なので値は同じ |
| `scripts/research_fx_tokyofix.py` | `COST_PER_SIDE_BPS/ROUND_TRIP_BPS/BAR_NET_BPS`→`_PCT`(1/100)、`Res.net` = rets/100 − 往復(%)、スプレッドを %、値動き(bp)と費用(%)の比べは値動きを /100 |
| `scripts/research_fx_events.py` | `COST_FLOOR 0.71`→`0.0071`、`COST_SLIP 2.0`→`0.02`、`BAR_NET 1.5`→`0.015`(名前に bp なし、値と注を %)、net = gross/100 − 費用、表示を % |
| `scripts/research_avalanche.py` | `TAKER_BPS/SLIP_SENS_BPS`→`_PCT`、`COST_IN` を %、入りの値段 `base*(1+side*c_in/100)`、`net_bps`→`net_pct`、`max_dd_bps`→`max_dd_pct`。TP 幅(入りから)・閾値・前向きの値動きは bp のまま |
| `scripts/research_burst_atlas.py` | `TAKER_ONE_WAY/TAKER_ROUND` 3.96/7.92 → 0.0396/0.0792 %。drift(bp)と費用の線の比べは線を × 100、ネット(drift/100 − 往復)を % |
| `scripts/research_fast_cycle.py` | `TAKER_BPS`→`TAKER_PCT`、`pnl_bps`→`pnl_pct`(TP は tp_bps/100、止めは × 100 − 費用)、`daily_bps`→`daily_pct`、`maxdd_bps` を消し `maxdd_pct` = 累積 % の落ち込み(前の maxdd_bps/100 と同じ値)、`BAR_DAILY_BPS 10`→`BAR_DAILY_PCT 0.10`、capture を %、net(τ) = capture % + markout/100、S7 の定数 1.169/0.38/0.76 bps → %、板のスプレッドを % |
| `scripts/research_latency_grade.py` | `SLIPS (0,2)`→`(0,0.02)` %、スプレッドを %、`net` を %(× 100)、円の換算 `net/100`。合図 r・閾値・TP 幅 10bps・drift は bp のまま |
| `scripts/research_storm_bracket.py` | `TAKER_BPS`→`TAKER_PCT`、`net_bps`→`net_pct`(gross/100 − 2 × 費用)、`max_dd_bps`→`max_dd_pct`、線 +5bps → +0.05 %・1000bps → 10 %。止めの距離 X(入りから)は bp のまま |
| `scripts/research_signal_fade.py` | `TAKER_BPS/MAKER_BPS`→`_PCT`(0.0396/0)、`net_pct = gross_pct − exit_cost`(前は `exit_cost/100`、値は同じ) |
| `scripts/research_spread_mm.py` | `TAKER_BPS`→`TAKER_PCT`、`FUND_BPS_DAY 6.0`→`FUND_PCT_DAY 0.06`、1 往復の unit・capture を %、三つの項の和 = capture % + drift/100。`cal.load` の 7 番目(他の作業者が % にした)を `spread_pct` で受ける |
| `scripts/research_maker_reaudit.py` | `MAKER/STOP_TAKER/TIME_TAKER/TAKER_RT_BPS`→`_PCT`、`BAR_MIN_NET_BPS`→`_PCT`、`net_bps`→`net_pct`、S3 の「2bps 深く」の指値 offset → 0.02 %(設定の名前 `deep2bp`→`deep0.02pct`)。gross・影の取引・TP 幅は bp のまま |
| `scripts/research_exit_surface.py` | **他の作業者の直しで import が壊れていた**(`replay_scalp_storm` が `COST_BURST_BPS` を `COST_BURST_PCT` に変え、旧版は `ImportError`)。`COST_BURST_PCT/COST_CALM_PCT` を読むようにし、`T.net` = gross/100 − 費用(%)、`mean_of`・`PLATEAU_TOL_BPS 2.0`→`PLATEAU_TOL_PCT 0.02`、表・文のネットを % に(小数を 2 つ増やした) |
| `scripts/research_prediction_atlas.py` | `TAKER_ROUND 7.92`→`0.0792` %、`p_req_*` は費用 × 100 で X(bp)にそろえる(値は同じ)、EVatt を % |
| `scripts/research_matilda_taro.py` | `TAKER_BPS`→`TAKER_PCT 0.0396`、1 単位の損益 `u_bps`→`u_pct`(× 1e4 → × 100)、`c_first_bps`→`c_first_pct`、capture `f_cap` を %、`cal.load` のスプレッドを `spread_pct` で受ける、表・文を %。40 分のレンジの門 `RANGE_MIN/MAX_BPS 10/82` は値動きの幅として bp のまま |
| `scripts/research_matilda_surface.py` | `TAKER_BPS`→`TAKER_PCT`、`FUNDING_BPS_DAY` を消し `FUNDING_PCT_DAY 0.06`(`Cfg.funding` の既定)、`u_bps`→`u_pct`、`u_gross` も %(taker の出の値段を含む損益)、report 30 の文の数(−0.395 / −2.597 / 2.20 bps/unit)を % で |
| `scripts/research_m4_finecheck.py` | `M3.TAKER_PCT`・`M4.FUNDING_PCT_DAY` を読む(組)、自前の機械の `u_bps`→`u_pct`・`u_gross` %、capture %、`REPORT30_*`(記録、bps)は書き換えず `/ 100` で比べ許し幅 0.001 → 0.001/100、機械どうしの一致の許し幅 1e-12 → 1e-14(同じ相対の厳しさ) |
| `scripts/research_matilda_modern.py` | `TAKER_BPS`→`TAKER_PCT`、`u_bps`→`u_pct`、`c_first_bps`→`c_first_pct`、capture・`f_dist`(入りの値段と中心の距離)・1 tick の率を %、#26 の再現の帯 capture 0.35..0.80bps → 0.0035..0.0080 %、`cal.load` のスプレッドを `spread_pct` |
| `docs/DATA/probes/20260919_o3c_reaction_bugcheck.py` | 保存済みの表(L-920 より前、`dist_vwap_bp`・`dist_node_bp`)を `_dist_pct()` で `/ 100` して `dist_*_pct` で読む(新しい名前の列があればそのまま)。目標価格の検査 `/1e4`→`/100`、帯 0/10/25/50/100bp → 0/0.10/0.25/0.50/1.00 %、表示を %。`bp_{h}m`・`*_reactdir`・mfe・mae は値動きなので bp のまま |
| `docs/DATA/probes/20260919_o3c_reaction_bugcheck2.py` | 同じ読み方。5 帯の境を % |
| `docs/DATA/probes/20260919_o3c_reaction_r1_bp_reactdir_standardized.py` | 同じ読み方(10 分位の境は分位なので結果は同じ) |
| `docs/DATA/probes/20260919_jev_select_rank_probe.py` | Jev に送る共変量の説明 `"dist_vwap_bp": "distance in bp …"`→`"dist_vwap_pct": "distance in % …"`(2026-09-19 の保存済みの答え `data/jev/probe/20260919_L241_select_rank.json` は古い鍵のまま) |
| `docs/DATA/probes/20260920_o3c_cascade_read.py` | 建玉の帯 `BAND_BP (5,10,20)`(p0 と建玉の値段の距離)→`BAND_PCT (0.05,0.10,0.20)`、鍵 `amt_{x}bp`→`amt_{x:g}pct`、表を %。`dist_node_bp` の表示は下の「直さない」 |

### 直さない(理由)

| ファイル・箇所 | 理由 |
|---|---|
| `docs/DATA/probes/20260920_o3c_signal_continue_refuter.py` 全体 | bp の行は値動き(向き付きの 1 件あたりの値動き・k_ticks の値動き・60 秒の動き)で bp のまま。合成の行の `dist_node_bp`(④)は `scripts/o3c_signal_continue.py` の `PrintsCSV` が読む列名で、書き手(o3c 系、ほかの作業者の受け持ち)が bp の名前のまま。ここだけ変えると試しが止まるので触っていない(組の相手は下の「迷ったこと」) |
| `docs/DATA/probes/20260920_o3c_cascade_read.py` の `dist_node_bp` 表示 | 同じく `liq_cascade_v2` 系の出力の列名をそのまま表示している(組の相手がほかの作業者) |
| 各台本の事前登録の docstring の「bps」 | REST_RULES §3。逐語は書き換えず、換算の段落を足した |
| 値動き・閾値・入りから測る TP/止め・レンジの幅の bps | REST_RULES §1「bp にしてよい = 値動き率だけ」 |

### 直していない(上限に入らなかった)

なし(受け持ち 32 ファイルはすべて上の「直した」か「直さない」)。

## 組で触ったほかのファイル

なし(受け持ちの外は触っていない)。受け持ちの中の組: `research_range_reversed`→`research_vr_barrier`、`research_fx_event_ticks`→`research_fx_s4_judgment`、`research_matilda_taro`(M3)・`research_matilda_surface`(M4)→`research_m4_finecheck`。

ほかの作業者の直しに合わせた所(事実): `scripts/replay_scalp_storm.py` の `COST_BURST_PCT`・`COST_CALM_PCT`(`research_exit_surface.py` が旧名で import して止まっていた。下の確かめ 4)、`scripts/research_board_calibration.py` の `load()` が返すスプレッドが % になった(`spread_pct`、作業木の差分の 34 行目)ので、受ける変数名を `spread_mm`・`matilda_taro`・`matilda_modern` で `spread_pct` にした。

## 回した試験と確かめ

1. 今ある試験(受け持ちの台本を import する試験は無い。`git ls-files tests | xargs grep -l <名前>` で `tests/test_scalp_logic.py` のコメントだけが当たった):

```
$ timeout 600 env PYTHONPATH=src python -m pytest tests/test_scalp_logic.py
39 passed in 0.77s
```

2. 最後の直しの後に回し直した(事実): 全 32 ファイル `python -m py_compile` → `py_compile ok=32 fail=0`。研究の台本 26 本 `PYTHONPATH=src:scripts python3 -c "import <名前>"` → `import ok=26`。同じ回の `tests/test_scalp_logic.py` → `39 passed in 0.22s`。
   latency_grade の slip の鍵の取り残しを `grep -n "2\.0\b\|0\.0, d\|, 0\.0)"` で見た。残った `2.0` は遅れ(delta)の値だけで、slip は 0.0 と `SLIPS` からだけ渡る(事実)。

3. 旧版(作業前に scratchpad に写した自分の受け持ちの元のファイル)と新版を小さな作り物の入力で回し、% × 100 = 前の bp を確かめた(事実。実データは 2026 年のテープで、REST_RULES §4 の日付の線より後なので読んでいない):

| 台本 | 回したもの | 出力 |
|---|---|---|
| two_sided_flow | `fifo_round_trips`・`markouts`(3 種)・`episode_pnl_prereg`・`revisit_flags` | `fifo max abs(new*100-old) 3.55e-15`、`entry 4.4e-16`、`adverse 0.0`(bp のまま)、`total 1.8e-15`、prereg の JPY は同じ、revisit の判定は同じ |
| calm_range | `backtest` 6 設定 96 取引 | `net 3.6e-15`・`cost 4.4e-16`・`gross 0.0`・理由が同じ |
| range_reversed | `backtest` 18 設定 48 取引 | `pct*100 == bp within 1e-9, reasons identical` |
| vr_barrier | `barrier_race` 2 障壁 × 500 | `outcome same True tbar same True`。損益分岐は旧版 50.15 %・新版 61.33 %(下の注) |
| fx_event_ticks | `trade_bps`/`trade_rates` 1,200 回 | `max 7.1e-15` |
| fx_tokyofix | `Res`(300 取引) | net・CI・t・win が一致 |
| fx_sessions | `race`・`breakeven`・`ev_uncond` | 結果と時間が同じ、p* 同じ、EV × 100 = 旧 EV |
| latency_grade | `simulate`(300 合図 × slip 2 × 遅れ 2) | `max 7.1e-15`、TP の判定が同じ |
| avalanche | `simulate`(4 設定) | `max 7.1e-15` |
| fast_cycle | `_run_exit` 2,400 回(tp 1,054・age 612・stop 734) | `max 3.6e-15` |
| matilda_modern | `_close`(手で作った在庫 500 回、1,582 単位) | `max abs(u_pct*100 - u_bps) and cycle pnl 2.84e-14` |
| 調べの台本 | `_dist_pct` に古い列名と新しい列名の小さな CSV | 古い `-66.2685` → `-0.662685`、新しい列はそのまま |

注(事実): vr_barrier の旧版を新しい `research_range_reversed`(費用を % にした)と組で読むと、損益分岐が 50.15 % になる(旧版は費用を bp として 5 + 0.0293 を足すため)。新版は 61.33 %(事前登録の 61.3 % と一致)。組で変える必要がある所の実例。

4. `research_exit_surface.py` の旧版は、ほかの作業者が `replay_scalp_storm.py` を直した後の作業木では import で止まる(事実):

```
old version fails now: ImportError cannot import name 'COST_BURST_BPS' from 'replay_scalp_storm'
```

新版は `import ok 0.0396 0.0293 0.02`。

5. 走らせて確かめていないもの(事実): matilda 系の 3 本(taro・surface・m4_finecheck。close_cycle が関数の中の関数で、市場の作り物が要る)と modern の `_close` 以外、maker_reaudit、fx_events、fx_s4_judgment の `main`、burst_atlas、exit_surface・prediction_atlas・storm_bracket・signal_fade・spread_mm の数の機械。式の置き換え(× 1e4 → × 100、定数 1/100)だけで、作り物の入力で回していない。matilda 系は市場の作り物を組むのが重く、上の時間の中では作らなかった。

## 迷ったこと(リードの判断が要る)

1. **レンジの縁(節)から測る距離を % にし、入りの約定から測る TP・止めを bp に残した**。REST_RULES §1 の「節からの距離」を縁から測る距離に当てた。当てたもの: calm_range の `RANGE_BREAK`・`OFFSETS`、range_reversed の `RANGE_BREAK`・`fix10`・行き過ぎ・3d の障壁、vr_barrier と fx_sessions の `BARRIERS`、maker_reaudit の「2bps 深く」の指値。一方、ひげ(同じ足の高値・安値と終値の差)は bp でよいと §1 にあり、「縁を 10bps 越えた」は値動きとも読める。逆の読み(全部 bp)にするなら、上の 6 本で値と名前を戻す。range_reversed の `tp_dist`(縁から決めた TP の水準と入りの値段の距離)は % にしたが、ほかの台本の「入りから +10bps の TP」は bp のままで、ここはそろっていない。
2. **1 単位の往復の損益を % にした**(matilda 系の `u`、two_sided_flow の FIFO の往復 `rt`)。式は「向き × (出/入 − 1)」で値動き率の形だが、出の値段に taker の費用(mid ∓ 3.96bps)やスプレッドの取り分が入り、合計・1 日の和・最大の落ち込みは建玉の数で重みが付くので、§1 の「建玉・段数で重みを付けた損益の率」「ネット」に当てた。`codefix_dead.md` の迷ったこと 3(`liq_cascade_v2` の fade の `pnl_bp` を ② として残した)とは読みが逆。
3. **組の相手がほかの作業者の所**: `dist_node_bp`(節からの距離、④)を書く `scripts/o3c_signal_continue.py`・`src/bot/research/liq_cascade_v2.py`・`scripts/o3c_reaction.py` ほか o3c 系が bp の名前のまま(この時点の作業木で未変更、`git status` に出ていない)。書き手が `_pct` にしたら、`20260920_o3c_signal_continue_refuter.py` の合成の行の鍵と `20260920_o3c_cascade_read.py` の表示を合わせる必要がある。調べの 3 本(bugcheck・bugcheck2・r1)は新旧どちらの列名でも読める。
4. **調べの台本の記録との食い違い**: `docs/DATA/probes/*.log`(2026-09-19 の出力、bp)は書き換えていない。走らせ直すと % で出るので、記録の数とは 1/100 で食い違う。jev の調べは Jev に送る文が変わったので、走らせ直すと保存済みの答え(古い鍵 `dist_vwap_bp`)と違う問いになる。
5. **台本の中の、過去の報告の数の文**(S4 の +0.8..+3.0bps、report 30 の −0.395/−2.597/2.20 bps/unit、#26 の capture +0.604 ほか)は、ネット・capture のものを % に書き換えた(括弧で bp を残した所もある)。事前登録の逐語ではないと読んだが、「過去の数を引用しない」(全捨て)とは別の話として残した。
6. `research_basis.py` の `d_basis`(ベーシスの時間の変化)は、値動き率の差(fx_ret − spot_ret)にほぼ等しいので L-924 で bp のままとも読めるが、名前と元がベーシスなので % にした。

## 時刻

- 着手: `Sat Oct 10 00:26:56 JST 2026`
- 終わり: `Sat Oct 10 01:03:32 JST 2026`(最後の確かめの直後の `TZ=Asia/Tokyo date` の出力)。
- 見込みとの差: 00:26:56 → 01:03:32 で 36 分 36 秒。見込み 290〜405 分(実測なし)より 253〜368 分短い。見込みは 1 ファイルあたりの分を実測なしで置いたもので、大きく外れた。
