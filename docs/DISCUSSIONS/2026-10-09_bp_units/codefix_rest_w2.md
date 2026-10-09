# bp の残りの直し(作業者 w2)

書いた人: 作業者 w2。決まりは `REST_RULES.md`(L-925)。コミットはしていない(決まり §4)。

## 着手前の表

| やろうとすること | オーナーの原文の該当語(逐語) |
|---|---|
| 受け持ちの 29 ファイルで、値動き率でない bp(費用・スプレッド・ネットの損益の率・板の深さ ÷ 仲値・クオートと仲値の距離)を % / `_pct` にする | 「**方針はbpの意味は「値動き率」としてのみ残し、その他の意味を持たせないようにすること**」(L-920)/「**1.A**」(L-923: スプレッド・ベーシス・約定の値段のずれも bp にしない) |
| 値動き率(markout・前方の動き・事象の動き・値動き率どうしの差)は bp のまま残す | 「**bpの意味は「値動き率」としてのみ残し**」(L-920)/「**A**」(L-924) |
| `config/constants.yaml` の費用・スプレッドの `*_bps` の鍵を `_pct` にし値を 1/100 にする。読む台本と試験を合わせる | 「**わかってる修正が必要なもの全部直してください**」(L-920)/「**1.A**」(L-923) |
| `schema/board_round_series_5s.json` の `spread_bps` 列を合わせる | 「**わかってる修正が必要なもの全部直してください**」(L-920) |
| `backtest_tab.js:507` の `minMove`、`backtest_chart.py`・`backtest_themes.py` の古いコメントを確かめて直す | 「**わかってる修正が必要なもの全部直してください**」(L-920) |
| `test_every_ledger_group_exists_and_every_shared_run_is_placed` の落ちの原因を確かめる | 「**たまたま見つかったやつも含めて**」(L-920) |
| 2 時間で止め、残りを持ち越しとして書く | 「**2時間を上限にしろ**」(L-923) |

右が空の行は無い。

完了見込み時間(実測なし、見積もり): 約 120 分(上限)。内訳: constants.yaml と読む台本・試験 5 本 20 分 / 板(run_board_round・schema・試験・judge_board_round・research_board_calibration・research_imbalance・measure_exec_floor)40 分 / qa の既知の答え 7 本と試験 25 分 / research_overnight_onr・research_wall_front と試験 15 分 / ダッシュボード 3 件と落ちる試験の調べ 10 分 / 試験の実行と報告 10 分。

## 受け持ちのファイル 1 つずつ

印: 【直した】/【直さない】。「値動き率」= REST_RULES §1 の bp にしてよいもの。

### 台本

| ファイル | 結果 | 前 → 後 |
|---|---|---|
| `scripts/constants_inventory.py` | 【直した】 | 計測計画の鍵 `taker_round_trip_floor_bps_OLD` → `_pct_OLD`、`etf_spread_bps` → `etf_spread_pct`、文の「2.0〜2.6bps」→「0.020〜0.026%」、「板スプレッド(bps)」→「(仲値に対する %)」 |
| `scripts/judge_board_round.py` | 【直した】 | `TAKER_COST_BPS = 5.8` → `TAKER_COST_PCT = 0.058`、`QC_SPREAD_MAX_BPS = 50` → `QC_SPREAD_MAX_PCT = 0.5`。`gross_and_t(x_bp, cost_pct)` は gross・net を %(x / 100)で返す(t は単位に依らない)。列 `spread_bps`・`bid/ask_depth_5bps`・`imb_5bps` → `spread_pct`・`bid/ask_depth_0p05pct`・`imb_0p05pct`、QC の理由名 `spread_gt_50bps` → `spread_gt_0p5pct` ほか。TP の特徴 `avg_spread_bps` → `avg_spread_pct`。GMO の capture(クオートと仲値の距離)を %、判定 `capture×2 − |drift| ≥ 1.0bps` → `capture(%)×2 − |drift(bp)|/100 ≥ 0.01`。前方の動き・30 秒の変位・バースト 20bps・adverse(5s)・drift は値動き率なので bp のまま。凍結した PREREG の docstring は書き換えず、直後に「(L-920 の後の単位: …)」の段を足した。`load_series` は L-920 より前の系列(`spread_bps` 列)を `/ 100` で、`*_5bps` 列を名前の付け替えだけで読む(コメントに書いた) |
| `scripts/measure_exec_floor.py` | 【直した】 | 統計の関数に `unit`("bp" / "pct")を足し、鍵の接尾辞と桁(bp 4 桁 / pct 6 桁)を切り替える。E-a 気配スプレッド・分単位のスプレッド・E-b 板を歩く費用・E-c 実現スプレッド・E-f の e_a/e_b_001・E-i の往復費用 → %(`*_pct`、`roundtrip_taker_cost_001btc_bp` → `_pct`)。`walk_cost_bp` の換算の shim を消し `walk_cost_pct` を直接使う。E-d(約定 H 秒後の mid の動き)・E-e のドリフト・K1 の経費前の値は値動き率なので bp のまま。docstring に単位の段を足した |
| `scripts/qa/make_known_answer.py` | 【直した】 | `QUOTE_SPREAD_BPS 2.0 / TAKER_SLIPPAGE_BPS 0.8 / TAKER_FEE_BPS 0.0` → `_PCT 0.02 / 0.008 / 0.0`、答えの鍵 `quoted_spread_bps`・`realized_spread_bps_ex_crossed`・`taker_slippage_bps_per_side`・`realized_slippage_bps_per_side`・`taker_fee_bps`・`true_taker_roundtrip_floor_bps` → `_pct`(6 桁)、`costs_qa.yaml` の `taker_fee_bps` → `taker_fee_pct`、主張 QA-5・QA-6 の文を %。夜間プレミアム・ボラ・配当落ちは値動き率なので bp のまま |
| `scripts/qa/make_known_answer_maker.py` | 【直した】 | `HALF_SPREAD_BPS 0.9 / QUOTE_IMPROVE_BPS 0.3 / TAKER_SLIPPAGE_BPS 0.3` → `_PCT 0.009 / 0.003 / 0.003`、`TICK_BPS` → `TICK_PCT`、往復の `net_bps`・`capture_*_bps` → `_pct`、要約の鍵 `net_pct_mean`・`net_pct_t_stat`・`capture_pct_per_leg_mean`・`biased_net_pct_mean_if_unclosed_positions_dropped`、罠の鍵、答えの `quoted_spread_pct`・`tick_pct`・`half_spread_pct`・`taker_slippage_pct`、マニフェストの「Fee: 0 % … Tick = 0.003 %」、主張の文。再値付けの線 `REPRICE_TICK_BPS`・衝撃 `IMPACT_BPS_PER_UNIT_SIZE`・5 秒 markout・`mean_abs_bias_bps`(クオート時と約定時の 2 つの mid の差 = 時間を挟んだ動き)は bp のまま |
| `scripts/qa/make_known_answer_maker3.py` | 【直した】 | 建玉ごとの `net_bps`(pnl / 建値 × 1e4)→ `net_pct`(× 100)、要約の鍵 `net_pct_mean`・`net_pct_t_stat`・`survivorship_biased_net_pct_if_forced_dropped`(6 桁)、`TICK_BPS` → `TICK_PCT`(0.01 %)、素朴モデルとの差の線 `gap ≥ 0.5` → `≥ 0.005`(%)、自己検査 `|net| p95 ≤ 8` → `≤ 0.08`、公開だけの再現との一致の許し 1e-6 → 1e-8、主張・印字の文を %。`SEEDS_TRIED`(2026-09-07〜11 の掃引の記録)と、逐語で残すと書かれたリードの決定 `NAIVE_GAP_CRITERION_REVISION`・`SEED_SELECTION_NOTE` は書き換えず、記録の前に「L-920 より前の記録、net は × 1e4」のコメントを足した。adverse(5s)・mid の動きの p99 は値動き率なので bp のまま |
| `scripts/qa/make_known_answer_steer.py` | 【直した】 | 主張 QS-5 の `planted_numbers` の鍵と文を `make_known_answer.py` の新しい鍵(`_pct`)に合わせた。夜間プレミアムは bp のまま |
| `scripts/qa/pipeline_known_answer_daily.py` | 【直さない】 | 中身は夜間リターン(植えたプレミアム Y・回収した平均・SE・MDE)だけで、費用もネットも無い。値動き率なので bp のまま(`grep -n -i 'cost\|fee\|spread\|net_'` の出力は 609 行の英語の文 1 行だけ) |
| `scripts/qa/pipeline_known_answer_taker.py` | 【直した】 | 費用 `realized_round_trip_bps` → `realized_round_trip_pct`(`used_pct`)、`trade_net_bps` → `trade_net_pct`(× 100)、出力の鍵 `cost_pct_used`・`planted_net_pct`・`recovered_net_pct_mean/se/ci95`・`recovered_gross_pct_mean`・`mde_pct`(6 桁)、RESULTS.md の表の見出し。事象の動き・検出の線・継続の X は値動き率なので bp のまま。封印の済んだ `planted_values_sealed.json` は書き換えず、docstring に「古い *_bps の費用・ネット・グロス・MDE は / 100 で今の % と同じ」と書いた(読む台本は無い: 下の §5) |
| `scripts/research_board_calibration.py` | 【直した】 | `load` のスプレッド → `spread_pct`(× 100)、capture(クオートと仲値の距離)→ %、`capture + adverse` → `capture(%) + adverse(bp)/100`(%)、`REVIVAL_BAR 0.38` → `0.0038`(%)、`EDGES (0.38, 0.76)` → `(0.0038, 0.0076)`、検出力の式の sd は 5 秒の mid の変化の sd(bp)/ 100、表示の桁。adverse(τ)・5 秒の mid の変化・不均衡の前方ドリフト・g は bp のまま。事前登録の docstring は書き換えず「(L-920 の後の単位: …)」の段を足した |
| `scripts/research_imbalance.py` | 【直した】 | `--depth-bps 5` → `--depth-pct 0.05`(呼び手は無い: `git ls-files … \| xargs grep -ln 'depth-bps'` は docs 2 本と本体だけ)、スプレッド → `spread_pct`(× 100)と表示。前方リターンは bp のまま |
| `scripts/research_overnight_onr.py` | 【直した】 | `COST_CONSERVATIVE_BPS 1.0 / COST_STRESS_BPS 2.6` → `_PCT 0.01 / 0.026`、`net_mean_t(x, cost_bps)` → `net_mean_t(x, cost_pct)`、ネットの表示を %。夜間・日中の動きの表は bp のまま。凍結した PREREG の docstring は書き換えず「(L-920 の後の単位: …)」の段を足した |
| `scripts/research_wall_front.py` | 【直した】 | `BAR_BPS 2.0` → `BAR_PCT 0.02`、capture → %、`net = cap + adv / 100`(%、7 か所)、壁の距離・オフセット(2 JPY・24 JPY・1 tick を仲値で割ったもの)→ %、表示の桁と単位の行。adverse(5s・30s)は bp のまま。凍結した事前登録の docstring は書き換えず「(L-920 の後の単位: …)」の段を足した |
| `scripts/run_board_round.py` | 【直した】 | `DEPTH_BPS 5.0` → `DEPTH_PCT 0.05`、書く列 `spread_bps`(× 1e4)→ `spread_pct`(× 100)、`bid/ask_depth_5bps`・`imb_5bps` → `bid/ask_depth_0p05pct`・`imb_0p05pct`(値は同じ)。docstring の PREREG の列の逐語は残し、直後に「(L-920 の後の単位: …)」を足した |

### 試験

| ファイル | 結果 | 前 → 後 |
|---|---|---|
| `tests/test_backtest_chart.py` | 【直した】(文だけ) | 前の書き出しの形(`pnl_bp`)で場面を作る所は、古い記録を / 100 で読む口の試験なので残した。古くなった説明 3 か所(「the exporter's column」「as scripts/dashboard_cards writes it」「compact(x, 4)」)を「L-920 より前の書き出しの形」「今は pnl_pct を 6 桁で書く」に直した。落ちる 1 本は下の §5 |
| `tests/test_board.py` | 【直さない】 | bp の語がもう無い(`grep -niE 'bp' tests/test_board.py` の出力なし)。前の回に直っている |
| `tests/test_board_round.py` | 【直した】 | 列名を `spread_pct`・`*_0p05pct` に、場面のスプレッドの値を 1/100(2.0 → 0.02、−1.0 → −0.01、999 → 9.99、一様 1〜3 → 0.01〜0.03)、`spread_gt_50bps` → `spread_gt_0p5pct`、`200/1e6 × 1e4` → `× 100`。バーストの 20bps・25bps は値動き率なので残した |
| `tests/test_board_walk.py` | 【直さない】 | bp の語がもう無い(同上) |
| `tests/test_clock_burst.py` | 【直さない】 | 60 秒 20bps の発火・+30bps などは値動き率。212・264 行の "bps" は出力に出てはいけない語の一覧 |
| `tests/test_constants.py` | 【直した】 | 鍵を `_pct` に、`unit == "bps"` → `"percent_of_mid"`、`"2bps" in reason` → `"0.02%" in reason`(`or "slippage"` は前のまま)、作り物の yaml の `unit: bps` → `unit: percent` |
| `tests/test_constants_inventory.py` | 【直した】 | 作り物の定数(手数料・古い床・スプレッド・未測定)の鍵を `*_pct`、値を 1/100、`unit: percent` |
| `tests/test_data_quality.py` | 【直した】 | 情報扱いの検査の場面の列 `spread_bps`(1.0 / −1.0)→ `spread_pct`(0.01 / −0.01)。交差板の数え方は変わらない |
| `tests/test_etf_measure.py` | 【直さない】 | 残る bp は、L-920 より前の台帳(`c_bps` 列)を読む口の試験と、表示に「6.1bps」が出ないことの試験。前の回に直っている |
| `tests/test_market_view.py` | 【直さない】 | `thr_bps` は scalp の発火の線(値動き率)の事象の記録。台本 `run_scalp_paper.py` は w3 の受け持ち |
| `tests/test_onr.py` | 【直した】 | `net_mean_t(x, cost_bps=1.0)` → `net_mean_t(x, cost_pct=0.01)`、試験名 `…_in_bps` → `…_in_pct`(期待値 0.001 − 1e-4 は同じ) |
| `tests/test_qa_make_known_answer.py` | 【直した】 | 答えの鍵を `_pct` に、期待値と許しを 1/100(2.0 → 0.02、0.8 → 0.008、3.6 → 0.036、0.05 → 0.0005、0.1 → 0.001)、マニフェストに漏れてはいけない文字列を新しい書き方(「0.020%」ほか)に。夜間プレミアムは bp のまま |
| `tests/test_qa_make_known_answer_maker.py` | 【直した】 | 鍵を `_pct` に、`HALF_SPREAD_BPS` → `HALF_SPREAD_PCT`(許し 1e-6 → 1e-8)、`|inside net| < 1.5` → `< 0.015`、罠の差 `+ 1.0` → `+ 0.01`、漏れの文字列を 6 桁に。adverse・mean_abs_bias は bp のまま |
| `tests/test_qa_make_known_answer_maker3.py` | 【直した】 | 鍵を `_pct` に、`p95 ≤ 8` → `≤ 0.08`、`gap ≥ 0.5` → `≥ 0.005`、`|net| < 10` → `< 0.1`、一致の許し 1e-6 → 1e-8、主張の文の書式 `:+.2f` → `:+.4f`、漏れの文字列を 6 桁に。「0.5 bps」が逐語の決定文に入っていることの試験はそのまま |
| `tests/test_record_funding_basis.py` | 【直さない】 | 残る bp は L-920 より前のベーシスの記録(`basis_bp`)を読み替える口の試験。前の回に直っている |

### 追加の項目

| 項目 | 結果 | 中身 |
|---|---|---|
| `config/constants.yaml` | 【直した】 | `quoted_spread_median_bps` 1.9 → `quoted_spread_median_pct` 0.019、`realized_taker_one_way_bps` [1.0, 1.3] → `_pct` [0.010, 0.013]、`realized_round_trip_bps` [2.0, 2.6] → `_pct` [0.020, 0.026]、`taker_round_trip_floor_bps_OLD` [5.8, 7.9] → `taker_round_trip_floor_pct_OLD` [0.058, 0.079]、`etf_spread_bps` null → `etf_spread_pct` null。`unit: bps` → `unit: percent_of_mid`。`notes` と `reason` の数字も %(「2bps/leg」→「0.02%/leg」、マイクロ先物の手数料の「0.331bps」→「0.00331%」も費用なので直した)。`status`・`measured_by`・`verified_on`・`source_url` はそのまま(下の §5 の 3)。`realized_round_trip_pct` の notes に「L-920 で名前と値を変えた、measured_by の bps は × 1e4」の文を足した |
| `scripts/phase2/p2_08_run.py`(w1 の受け持ち) | 触っていない | 要る直しは 121 行のコメントの鍵名だけで、見たときには w1 がもう `realized_taker_one_way_pct` に直していた(`grep -n 'realized_taker_one_way' scripts/phase2/p2_08_run.py` → `121:# constants.yaml realized_taker_one_way_pct upper / lower …`)。値は台本の中の定数で、yaml を読んでいない |
| 封印の済んだ `backtest_data/qa_pipeline_taker_20260905/planted_values_sealed.json` | 書き換えていない | 読む台本は無い(`git ls-files … \| xargs grep -ln 'planted_values_sealed\|qa_pipeline_taker'` は MD5SUMS・paper_logs の記録・schema の説明・書く台本 2 本だけ)。直した台本を同じ種と日数で回し、% × 100 が封印の bp と全部一致することを確かめた(§4) |
| `schema/board_round_series_5s.json` | 【直した】 | 新しい列 `spread_pct`(percent of mid、交差板の線 0.5)・`bid/ask_depth_0p05pct`・`imb_0p05pct` を足し、古い列 `spread_bps`・`*_5bps` は「2026-10-10 より前の系列だけ、/ 100 で読む」の説明に変えて残した。git にある古い系列(`backtest_data/board_round_20260904/`)も新しい系列も「書いてない列・無い列」にならないよう、8 列とも `"optional": true` |
| `backtest_tab.js:507` の `minMove: 0.01` | 【直した】 | % のときの表示は `num(v, 3)`(小数 3 桁)なのに `minMove` が 0.01 で、目盛り・十字線の丸めが表示より粗かった(コードを読んだだけ。画面では見ていない)。`minMove: k === 2 ? 0.001 : 0.01`(% は 3 桁、お金は前のまま)にし、理由をコメントに書いた |
| `backtest_chart.py:377` 付近・`backtest_themes.py:648` 付近のコメント | 【直した】 | 「card exports still write pnl_bp」「The card exports write it x 1e4 as pnl_bp」は今のコードと合わない(`export_card_trades.py` 123・136・249 行は `pnl_pct` を 6 桁で書く)。「L-920 から pnl_pct を書く。前の書き出しは pnl_bp(× 1e4)で、/ 100 で読む」に直した。K1 のひげの門「19 bp」「24 bp」は値動き率なので触っていない |
| `test_every_ledger_group_exists_and_every_shared_run_is_placed` の落ち | 【直さない】(リードの判断) | 下の §5 の 1 |

## 3. 組で触ったほかのファイル

| ファイル | 何を | なぜ組か |
|---|---|---|
| `tests/test_qa_pipeline_known_answer.py` | taker の試験の鍵(`recovered_net_pct_mean`・`mde_pct`・`planted_net_pct`・`realized_round_trip_pct`・`taker_round_trip_floor_pct_OLD`)。daily の試験は触っていない | `pipeline_known_answer_taker.py` と constants.yaml の鍵を名前で呼ぶ |
| `tests/test_qa_make_known_answer_steer.py` | `taker_fee_pct`・`true_taker_roundtrip_floor_pct`・`quoted_spread_pct`・`taker_slippage_pct_per_side`、漏れの文字列 | `make_known_answer.py` の答えの鍵を名前で呼ぶ |
| `scripts/render_exec_floor.py` | `pct_of(st, key)`(`*_pct` が無ければ `*_bp / 100`)を足し、E-a・E-b・E-c・E-f の e_a/e_b_001・E-i の往復費用を % で 5 桁で出す。見出しの「bp」→「%」。E-d・ドリフト・K1 は bp のまま | `measure_exec_floor.py` の出力 `exec_floor.json` を読む。git にある古い json(bp)も読めるようにした |

ほかの作業者の受け持ちで、組の相手として見たが触っていないもの:
- `scripts/tp_operating_curve.py`(w3): `judge_board_round.load_series` の出力の `spread_pct` を読み、無ければ `spread_bps / 100` を読む形に w3 が直していた。私の `load_series` は古い系列でも `spread_pct` を作るので、どちらの系列でも動く(推定: 回していない)。
- `scripts/research_matilda_modern.py`・`research_matilda_taro.py`・`research_spread_mm.py`(受け持ちは私でない): `research_board_calibration.load` の 7 番目の戻り値を `spread_bps` という名前で受ける。値はいま % になった。3 本とも計算には使っていない(事実: `grep -n spread_bps` で、taro・spread_mm は受け取る行だけ、modern は `m.spread = …` に入れるが `m.spread` を読む行が無い)。名前だけ持ち主が `spread_pct` に直す必要がある。
- `src/bot/monitoring/backtest_cards.py`(私の受け持ちでない): 7-8・360・376 行の説明が「書き出しは pnl_bp(4 桁)」のまま。読み方(`pnl_pct` を先に読み、無ければ `pnl_bp / 100`)は合っている。

## 4. 回した試験と確かめ

試験(すべて `PYTHONPATH=src python -m pytest <試験>`)。受け持ちの試験 16 本と、組で触った試験 2 本を 1 回で回した:

```
$ PYTHONPATH=src python -m pytest tests/test_backtest_chart.py tests/test_board.py tests/test_board_round.py tests/test_board_walk.py tests/test_clock_burst.py tests/test_constants.py tests/test_constants_inventory.py tests/test_data_quality.py tests/test_etf_measure.py tests/test_market_view.py tests/test_onr.py tests/test_qa_make_known_answer.py tests/test_qa_make_known_answer_maker.py tests/test_qa_make_known_answer_maker3.py tests/test_qa_make_known_answer_steer.py tests/test_record_funding_basis.py tests/test_qa_pipeline_known_answer.py
FAILED tests/test_backtest_chart.py::test_every_ledger_group_exists_and_every_shared_run_is_placed
1 failed, 459 passed, 4 skipped in 227.76s (0:03:47)
```

落ちた 1 本は直す前から落ちる(事実: 着手直後、`tests/test_backtest_chart.py` に手を付ける前に回して `1 failed, 55 passed, 4 skipped`、同じ 1 本。原因は §5 の 1)。`git stash` は使っていない。ほかに途中で単独でも回した: `tests/test_board_round.py`(15 passed)、`tests/test_onr.py`(10 passed)、`tests/test_data_quality.py tests/test_jev_schemas.py`(26 passed、schema を変えた後)、`tests/test_constants.py tests/test_constants_inventory.py tests/test_qa_pipeline_known_answer.py -k "taker or constants"`(33 passed)。

換算の確かめ(% × 100 = 前の bp):
- `pipeline_known_answer_taker.py`: 同じ種 20260905・60 日で回し、封印の bp と比べた。3 つの X で net・se・gross・mde・planted が全部一致、t と within_mde も一致。
  ```
  0.0 net -0.048 -0.048 se 2.4949 2.4949 gross 2.252 2.252 mde 6.9858 6.9858 planted -2.3 -2.3 t 0.9026 0.9026 True True
  3.0 net 2.9517 2.9517 se 2.495 2.495 gross 5.2517 5.2517 mde 6.986 6.986 planted 0.7 0.7 t 2.1049 2.1049 True True
  8.0 net 7.9513 7.9513 se 2.4951 2.4951 gross 10.2513 10.2513 mde 6.9863 6.9863 planted 5.7 5.7 t 4.1086 4.1086 True True
  ```
- `judge_board_round.py`: git にある古い系列(`spread_bps` 列)で走らせ直し、`backtest_data/board_round_20260904/JUDGE_RUN_qc.txt` と比べた。QC の数(264 / 71 / 357 / 357 / 0 / 0 / 0、無効 621、除外 2,023)は一致。BI・VR の gross・net は前の bp の 1/100(例 `0.191 −5.609` → `0.00191 −0.05609`)、t・判定・TP の AUC と判定は同じ。違うのは名前と単位の行だけ。
- `render_exec_floor.py`: git にある古い `exec_floor.json` を新しい読み方で書き出し(出力先は作業用の場所。`EXEC_FLOOR_TABLES.md` は書き換えていない)、前の表と比べた。E-a〜E-c の値は前の / 100(例 `0.892 | 1.770 | 3.009` → `0.00892 | 0.01770 | 0.03009`)、E-d は同じ。
- `make_known_answer.py`: 前の版(`git show HEAD:…`)と今の版の `make_tape` を同じ種で回し、約定の値段の最大差 0.0(32,595 行)、`quoted_spread`・`realized_spread`・`realized_slippage`・`floor` の % × 100 が前の bp と一致。
- `make_known_answer_maker.py`: 前の版と今の版を同じ種で回し、3 つの場面で net・capture の % × 100、adverse・t が一致。
- `make_known_answer_maker3.py`: 前の版と今の版を既定の種 20260910・既定の日数で回し、3 つの場面で net の % × 100・t・生き残りだけの net が一致(S1 `0.3046 0.3046 2.795 2.795 1.264 1.264`、S2 `-0.9825 -0.9825 …`、naive `0.8357 0.8357 …`)。S1 の 0.3046 は台本の中の記録 `SEEDS_TRIED[20260910]` の `S1_net_bps_mean` とも同じ。
- 回していないもの: `measure_exec_floor.py`・`research_board_calibration.py`・`research_wall_front.py`・`research_imbalance.py`・`research_overnight_onr.py` の本体(データが重い、または手元に無い)。どれも `py_compile` は通る。換算は線形(× 100 と / 100)で、確かめは読んだだけ【推定】。

## 5. 迷ったこと(リードの判断が要るもの)

1. **`test_every_ledger_group_exists_and_every_shared_run_is_placed` の落ち**: 原因は、台帳 `src/bot/monitoring/backtest_themes.py` の `THEMES` が組 `k1_newenv_a`・`k1_newenv_g`・`k1_env_fixes/pipeline`・`k1_env_fixes/pipeline_r2`・`k1_newenv_g_close` を指すのに、その置き場 `backtest_runs_shared/…` がコミット a705e9ed で消えたこと(事実: `catalog()` の `missing_groups` がこの 5 つ。a705e9ed のメッセージ「Delete per L-764 3.A-3.D … 3.A: backtest_runs_shared/k1_newenv_a, k1_newenv_g, k1_env_fixes, k1_newenv_g_close」)。消したのはオーナーの決定 L-764「**3.A 消す。損益の計算が今と違うから**」によるもので、消したこと自体は正しい。台帳の側は消し忘れか、回し直しのために残したのかを私は決められない(L-764 は「損益の計算が今と違うから」消すとあり、回し直せばこの組の説明がまた要る)。台帳から 2 つのテーマ(K1 のヒゲ・環境の確かめ)を消すと試験 112 行の「env_check に k1_newenv_g_close がある」も変える必要がある。直していない。案: (a) 台帳から 5 組を消し、試験の 2 行を合わせる / (b) 回し直すまで台帳を残し、試験の `missing_groups == []` を「L-764 で消した 5 組だけは無くてよい」にする。
2. **板の深さの列名 `*_0p05pct`**: 決まり §1 の「板の深さ ÷ 仲値・同じ時刻の 2 つの値段の距離」に当たるので帯の名前を % にしたが、書き方(`0p05pct`)は私が決めた。凍結した PREREG(`docs/PREREG_board_round.md` §0)の列名とずれる。系列の書き手(`run_board_round.py`)はオーナーの PC で動くので、次に回すと新しい列名の系列ができる。読み手(`judge_board_round.py`・`tp_operating_curve.py`・`data_quality.py`)は新旧どちらも読む。
3. **constants.yaml の `measured_by` の中の「quoted_spread_median_bps」と bps の数字**: 委任文の「出所の欄はそのまま」に従い書き換えていないので、`realized_taker_one_way_pct` の `measured_by` が古い鍵名 `quoted_spread_median_bps` を指したままになっている。`realized_round_trip_pct` の `notes` に「measured_by の bps は × 1e4」と書いた。鍵名だけでも直すかはリードの判断。
4. **capture + adverse の足し算**(`judge_board_round.py` の GMO、`research_board_calibration.py`、`research_wall_front.py`): capture(クオートと仲値の距離 → %)と adverse(約定後の mid の動き → bp)を足した maker のネットを % にした(`capture + adverse / 100`)。表には capture と net を %、adverse を bp で並べ、単位の行を足した。1 つの表で単位が混ざる。
5. **`research_board_calibration.py` の検出力の式の sd**: 事前登録は「sd = round trip の bps の sd、5 秒の mid の変化の sd で代用」。代用の sd(値動き、bp)を / 100 して % の edge で割った。sd の印字は bp のまま、式の中だけ %。
6. **`make_known_answer_maker.py` の `mean_abs_bias_bps`**: クオート時の mid と約定時の mid の差(時間を挟んだ 2 つの mid)なので値動き率と読み bp のまま残した。「同じ時刻の 2 つの値段の距離」ではないと読んだ。
7. **qa の既知の答えの git にある古い置き場**(`backtest_data/qa_known_answer_*`・`qa_pipeline_*`): 書き換えていない(決まり §2)。今の台本で作り直すと鍵名が `_pct` になり、古い置き場の答えと鍵名が違う。監査の試し(人や別のモデルに渡す包み)で古い置き場を使う手順があれば、読み方を足す必要がある【推定: そういう読み手の台本は git に無い】。

## 6. 時刻

- 着手: `Sat Oct 10 00:26:58 JST 2026`(`TZ=Asia/Tokyo date` の出力)
- 終わり: `Sat Oct 10 00:52:48 JST 2026`(同)
- 見込みとの差: 見込み 120 分に対し、`date` の差は 26 分。途中の `date` も 00:38・00:40・00:42・00:43・00:45・00:47・00:49 と進み、試験 1 回(3 分 47 秒)を含む作業の量に比べて短く見える。時計の出力をそのまま書いた(どちらが正しいかは確かめていない)。上限(2 時間)には達しておらず、受け持ちの全ファイルと追加の項目は「直した / 直さない」のどちらかになった。持ち越しは §5 の判断待ちだけ。

## 数え(受け持ち 29 ファイル + 追加 7 項目)

- 受け持ち 29 ファイル(台本 14・試験 15): 直した 22(台本 13・試験 9。うち `test_backtest_chart.py` は説明文だけ)/ 直さない 7(`pipeline_known_answer_daily.py`・`test_board.py`・`test_board_walk.py`・`test_clock_burst.py`・`test_etf_measure.py`・`test_market_view.py`・`test_record_funding_basis.py`。値動き率か、前の回に直っている)。`test_every_ledger…` の落ちは §5 の 1。
- 追加 7 項目: 直した 5(constants.yaml・schema・minMove・コメント 2 本)/ 触っていない 2(`p2_08_run.py` は w1 が直し済み、封印の答えは書き換えない決まり)/ 落ちる試験は直さずリードへ。
- 組で触ったほかのファイル 3(§3)。
