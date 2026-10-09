# 残りの直し: 作業者 w1(phase2 の台本・xborder_p2・overnight・judge_gates)

書いた人: 作業者 w1。決まりは `REST_RULES.md`(L-925)。コミットはしていない(決まり §4)。

## 着手前の表

| やろうとすること | オーナーの原文の該当語(逐語) |
|---|---|
| 受け持ちのファイルの bp のうち、値動き率でないもの(費用・ネット・資金調達・損益の率・スプレッド)の名前を `_pct` にし、`× 1e4` を `× 100` にする | 「**bpの意味は「値動き率」としてのみ残し、その他の意味を持たせないようにすること**」L-920 |
| 値動き率(グロス・脚・夜間−日中の差・ボラ・閾値)は bp のまま残す | 「**bpの意味は「値動き率」としてのみ残し**」L-920 /「**A**」L-924 |
| 組で変える必要のある読み手・書き手と、今ある試験を名前・単位に合わせる(新しい試験は足さない) | 「**たまたま見つかったやつも含めてわかってる修正が必要なもの全部直してください**」L-920 |
| 2 時間で止め、残りを書く | 「**2時間を上限にしろ**」L-923 |
| この報告を書く | 「**次は残りを終わるまでやってください**」L-925 |

### 完了見込み時間(実測なし。着手時の見積もり)

- 着手前の試験(受け持ち 8 本): 2 分
- xborder_p2 の組(本体 2・試験 2・_fx/_state/p2_08_data の確かめ): 20 分
- p2_08_run(233 か所): 25 分
- overnight(state_split・edge_trend)と呼び手: 15 分
- p2_01_run・p2_01_final・p2_01b_history・試験: 20 分
- p2_02_run・p2_02_final・試験 2 本: 15 分
- p2_03_*・p2_04_run・g1_state_analysis: 25 分
- judge_gates・試験・test_jev_design: 15 分
- 試験と報告: 15 分
- 合計 約 150 分。上限 120 分を超えるので上の順で進め、01:50 JST ごろに手を止める予定だった。

## 1. 受け持ちのファイル(全部)

直した 23・直さない 3。直さない 3 本はどれも bp の当たりが 0 件(`grep -ciE 'bps?\b|_bps?|bps?_|1e4|10000|10_000'` の結果 0)。

### 本体

| ファイル | 直した / 直さない | 前 → 後 |
|---|---|---|
| `src/bot/research/xborder_p2.py` | 直した | 帳簿の列 `cost_bps`/`funding_bps`/`net_bps` → `cost_pct`/`funding_pct`/`net_pct`(%)。`gross_bps` は値動き率なので bp のまま。`net_pct = gross_bps / 100 − cost_pct − funding_pct`。引数 `cost_one_way_bps` → `cost_one_way_pct`(%)。`funding_pct_per_settlement` は前から % なので × 100 をやめただけ。`pnl_jpy = net_pct / 100 × entry_px × size`。`daily_pnl` の既定 `value="net_bps"` → `"net_pct"`。docstring |
| `src/bot/research/xborder_p2_fast.py` | 直した | 上と同じ列・引数。`simulate_arrays` の返す鍵 `funding_bps` → `funding_pct` |
| `src/bot/research/xborder_p2_fx.py` | 直さない | bp の当たり 0 件(帳簿の列を使っていない) |
| `src/bot/research/xborder_p2_state.py` | 直さない | bp の当たり 0 件 |
| `scripts/phase2/p2_08_data.py` | 直さない | bp の当たり 0 件 |
| `scripts/phase2/p2_08_run.py` | 直した | `COST_CONS_1W` 1.3 → 0.013・`COST_OPT_1W` 1.0 → 0.010(%。事前登録の 1.3 / 1.0 bps と constants.yaml の新しい名前 `realized_taker_one_way_pct` をコメントに残した)。`MDE_REGISTERED` 1.54 → 0.0154・`SIGMA_REGISTERED` 86.5 → 0.865(%、ネットの値。事前登録の bps 値を横に書いた)。`net_of`・`full_stats`・対照 1/2・`net_bps_opt` をすべて % に。鍵 `mean_net_bps`/`sd_net_bps`/`max_dd_bps`/`mean_funding_bps`/`mean_cost_bps`/`mde_bps`/`mde_cluster_bps`/`sigma_bps`/`sd_bps`/`one_way_bps`/`val_improvement_*_bps`/`max_mean_net_bps_<期間>`/`obs_mean_net_bps` → `_pct`。半スプレッド `eff_bps`/`quoted_bps`(× 1e4)→ `eff_pct`/`quoted_pct`(× 100)。エッジ推移の 3 脚(グロス・費用・ネット)はすべて % にそろえ `slope_bps_per_week` → `slope_pct_per_week`(`value_unit="%"`)。前の反復の CSV を読む口 7 か所を `read_prev_csv` に通した(下の §2)。ボラ三分位の境界(σ × 1e4)と `mean_abs_diff_bps`(m の差 = 値動き率の差)は bp のまま |
| `src/bot/research/overnight.py` | 直した | `edge_trend` の `value_unit` の既定 `"bps"` を外して必須にした(呼び手が単位を名乗る)。`state_split` の引数 `cost_bps` → `cost_pct`。cost を渡すときは values も % にする、と docstring に書いた |
| `scripts/phase2/g1_state_analysis.py` | 直した | 費用の列を `cost_pct_cons`/`cost_conservative_pct`/`cost_cons_pct` で読み、無ければ古い `*_bps` ÷ 100(§2)。費用を渡すので values(グロス bp)÷ 100 して % で `state_split(cost_pct=…)`。出力の鍵 `null_p95_bps`・`uncond_*_bps` → `_pct`、本文の bps → %、表示の桁を 2 → 4 |
| `scripts/phase2/p2_04_run.py` | 直した | `cost_bps_cons`/`cost_bps_opt`/`cost_bps_cons_fullday_base`(× 1e4)→ `cost_pct_*`(× 100)。`r_net_bps_cons/opt` → `r_net_pct_*`(= `r_bps / 100 − cost`)。ネットの統計の鍵(`net_mean_cons_bps`・`sd_bps`・`mde_bps`・`null_*_bps`・`observed_*_bps`・`val_*_bps`・`iter0_unconditional_val_mean_bps` ほか)→ `_pct`。グロスの差(`diff_gross_bps`・`gross_mean_bps`・`sd_gross_bps`・`mde_diff_bps`)は bp のまま。`state_split` は `r_bps / 100` と `cost_pct=` で呼ぶ。`edge_trend` は脚ごとに `value_unit`(グロス "bps"、費用・ネット "%")。表の % の列は桁を 2 増やした |
| `scripts/phase2/p2_01_run.py` | 直した | `cost_bps_cons/opt` → `cost_pct_*`、`r_net_bps_*` → `r_net_pct_*`(= `r_night_bps / 100 − cost`)。`MDE_PCT = MDE_BPS / 100`(ネットと比べる所だけ。`MDE_BPS`・`MDE_DIFF_BPS`・`GROSS_GATE_BPS` は事前登録の値なので残し、グロス・差と比べる)。`describe` の行に `unit` を付ける `_u` を足し、表に「単位」列(ネット %、グロス・差 bps)。`mde.csv`・RUN.json の鍵を単位なしの名前 + `unit` に。RUN.json の `mean_r_net_bps_conservative` → `mean_r_net_pct_conservative`。反復 0 の RUN.json を読む口は §2 |
| `scripts/phase2/p2_01_final.py` | 直した | p2_01_run と同じ形。ON1 台帳の読み口は `net_pct` を読み、無ければ `net_bps` ÷ 100(`ledger_net_pct_mean`)。PREREG 原文の引用「cost_bps(t)」は書き換えず、直後に「(L-920 の後の単位: …)」の 1 行を足した |
| `scripts/phase2/p2_01b_history.py` | 直した | 費用・ネットを %、`REF_DEV`/`REF_SEALED`(PREREG §2 の bps 値)は残し、費用・ネットと比べる所で ÷ 100。一致の許容 ±0.01bp は % の列で ±0.0001。H1 恒等式 `cost_pct × close × 10 / 100 == 122`。`edge_trend` に脚ごとの `value_unit` |
| `scripts/phase2/p2_02_run.py` | 直した | `conservative_cost_bps` → `conservative_cost_pct`(× 100)、旧手数料の `fee_bps` → `fee_pct`。列 `cost_conservative_bps`/`cost_optimistic_bps`/`net_*_raw_bps`/`net_*_adj_bps` → `_pct`(ネット = グロス bp ÷ 100 − 費用)。`mde_bps(sigma_bps, n)` → `mde_from_sigma(sigma, n)`(単位は sigma の単位)。`sign_reversal_stats` は % を返す。要約・対照・train/val の鍵を `_pct`、本文を %。`gap_bps`・`r_night_*_bps`・`r_day_bps`・配当の確かめの中央値は値動き率なので bp のまま |
| `scripts/phase2/p2_02_final.py` | 直した | p2_02_run と同じ。`main_indicators.csv` は鍵を `mean`/`ci_lo`/`ci_hi` + `unit` 列に。**`check_guards`(123〜166 行)は触っていない**(`git diff -U0` の当たりは 89 行の import と 404 行より後だけ。門の中に bp の当たりは 0 件) |
| `scripts/phase2/p2_03_run.py` | 直した | `cost_cons_bps` → `cost_cons_pct`(× 100)、`net_opt_bps`/`net_cons_bps` → `_pct`(グロス bp ÷ 100 − 費用)。`mean_ci` の鍵 `mean_bps` → `mean`(グロスにもネットにも使うので単位なし)。`MDE_PCT = MDE_BPS / 100` を足し、保守ネット平均との比べは %。対照 3(売り)を %。反復 0 の CSV を読む口は §2 |
| `scripts/phase2/p2_03_final.py` | 直した | 上の列名に合わせ、費用・ネットの鍵と表を %。符号一致は楽観ネット(= グロス ÷ 100)の `mean_opt_pct` で比べる(符号は単位で変わらない) |
| `scripts/phase2/p2_03_iter2.py` | 直した | 上の列名・`mean_ci` の鍵に合わせた。反復 1 の要約を読む口は §2。`mde_bps`(σ(r_night) からの MDE、グロス)は bp のまま |
| `scripts/judge_gates.py` | 直した | 売りスキャルパーの損益率 `ScalpTrade.bps`(pnl ÷ 元本 × 1e4)→ `pnl_pct`(× 100)。`SCALP_NET_BPS_BAR = 5.0` → `SCALP_NET_PCT_BAR = 0.05`(§5 の「+5 bps/trade」は docstring にそのまま残し、直後に L-920 の 1 行)。G2/G3/G5 の鍵 `net_bps`/`median_bps`/`armed_bps`/`unarmed_bps`/`diff_bps`/`buckets.*.net_bps` → `_pct`。既存の `_pct_stats`(G1 用)と名前が重なるので、スキャルパー用は `_scalp_pct_stats`。`thr_bps`・`thr_armed_bps`・`sigma60_bps`・`cuts_bps`・`thr_ref_bps`(値動きの閾値・ボラ)は bp のまま |

### 試験

| ファイル | 直した / 直さない | 前 → 後 |
|---|---|---|
| `tests/test_xborder_p2_known_answer.py` | 直した | `COST_1W` 1.3 → 0.013、期待値の費用・資金調達・ネットを ÷ 100(0.026・0.02・0.374・−1.526・0.254・0.974・−0.026、日次 −2.424・−1.45・−1.476)。許容は `TOL_PCT = 1e-9 / 100`(前の 1e-9 bp と同じ細かさ)。`pnl_jpy == net_pct × 100` |
| `tests/test_xborder_p2_fast.py` | 直した | 列名、% の列の許容を 1e-11 |
| `tests/test_bot_research_overnight.py` | 直した | `_run_edge_trend` に `value_unit="bps"` を明示、`cost_bps=` → `cost_pct=`(数値は単位なしの合成なので変えず、コメントで % と読むと書いた) |
| `tests/test_jev_design.py` | 直した | 合成の共変量名 `dist_vwap_bp`(同じ時刻の 2 つの値段の距離)→ `dist_vwap_pct`、説明文を % に。`bp_reactdir`(値動き)はそのまま |
| `tests/test_judge_gates.py` | 直した | `scalp_event`/`scalp_log` の損益の引数を %(6.0 → 0.06 など 16 か所)、鍵を `_pct` |
| `tests/test_phase2_p2_01.py` | 直した | 費用 × 100、ネット = planted ÷ 100 − 費用 |
| `tests/test_phase2_p2_02.py` | 直した | `conservative_cost_pct`、期待値 × 100 |
| `tests/test_phase2_p2_02_final.py` | 直した | 列・鍵を `_pct`、ネット = グロス ÷ 100 − 費用(許容 1e-6 bp → 1e-8 %) |

## 2. 前の記録を読む口(REST_RULES §2)

どれも「新しい名前があればそれ、無ければ古い名前 ÷ 100」。コメントに列と割る数を書いた。

- `p2_08_run.read_prev_csv`: 反復 0/1 の `configs.csv`・`null_best_of_*.csv`・`sensitivity_val_2022_only.csv`。`*_bps` の 8 列と `max_mean_net_bps_<期間>` を `_pct` にして ÷ 100、古い形のときだけ名前に単位の無い `ci_lo`/`ci_hi`/`se_cluster` も ÷ 100。`mean_gross_bps` はそのまま。
- `p2_01_run`: 反復 0 の RUN.json の `mean_r_net_bps_conservative` と `ci95`。
- `p2_01_final`: ON1 台帳の `net_bps`。
- `p2_03_run`: 反復 0 の `summary_by_series.csv`(`mean_net_cons_bps`・`cons_ci_lo/hi`)と `pairs_1306T.csv`(`cost_cons_bps`)。
- `p2_03_iter2`: 反復 1 の `summary_by_series.csv`(同上。登録 MDE は bp のまま、新しい形なら `mde_pct × 100`)。
- `g1_state_analysis`: P2-01/02/03 のペア CSV の費用の列。
- 試験 `test_phase2_p2_04.py` の反復 0 の `train_val.csv` との突き合わせ(`net_mean_cons_bps`・`ci_lo/hi` ÷ 100)。

## 3. 組で触ったほかのファイル

- `tests/test_phase2_p2_04.py`: p2_04_run の名前に合わせ、反復 0 の記録を ÷ 100 で読む形に(上)。
- `tests/test_phase2_p2_03_final.py`: 楽観ネットが % になったので、植えたドリフト(bp)を ÷ 100 して比べる(許容 5bp → 0.05%)。
- 触っていないが回した: `test_phase2_p2_01_final.py`・`test_phase2_p2_03.py`・`test_phase2_p2_03_iter2.py`・`test_xborder_p2_fx.py`・`test_xborder_p2_state.py`・`test_audit_gates_wired.py`・`test_composite.py`・`test_market_view.py`。

## 4. 回した試験と結果

着手前(00:27 JST、何も直す前):

```
$ PYTHONPATH=src python -m pytest tests/test_bot_research_overnight.py tests/test_jev_design.py tests/test_judge_gates.py tests/test_phase2_p2_01.py tests/test_phase2_p2_02.py tests/test_phase2_p2_02_final.py tests/test_xborder_p2_fast.py tests/test_xborder_p2_known_answer.py
187 passed in 106.12s (0:01:46)
```

直した後(01:03 JST):

```
$ PYTHONPATH=src python -m pytest tests/test_bot_research_overnight.py tests/test_jev_design.py tests/test_judge_gates.py tests/test_phase2_p2_01.py tests/test_phase2_p2_02.py tests/test_phase2_p2_02_final.py tests/test_xborder_p2_fast.py tests/test_xborder_p2_known_answer.py
187 passed in 76.59s (0:01:16)

$ PYTHONPATH=src python -m pytest tests/test_phase2_p2_01_final.py tests/test_phase2_p2_03.py tests/test_phase2_p2_03_final.py tests/test_phase2_p2_03_iter2.py tests/test_xborder_p2_fx.py tests/test_xborder_p2_state.py tests/test_audit_gates_wired.py tests/test_composite.py tests/test_market_view.py
339 passed in 13.44s

$ PYTHONPATH=src python -m pytest tests/test_phase2_p2_04.py
FAILED tests/test_phase2_p2_04.py::test_iteration1_output_is_still_byte_identical_after_adding_iteration2
FAILED tests/test_phase2_p2_04.py::test_iteration0_output_is_byte_identical_to_the_committed_reference
2 failed, 32 passed in 75.69s
```

落ちた 2 本について(事実): どちらも p2_04 を開発セットで走らせ直し、git に入った反復 0 / 反復 1 の CSV と**バイト単位で一致**することを求める試験。列名と単位を変えたので一致しない。私の変更の前にこの 2 本が通っていたかは確かめていない(着手前の試験の一覧に入れていなかった。`git stash` は使わない決まり)。私の `overnight.state_split` の引数の名前替えの直後に回したときは `TypeError` で落ちた(00:40 ごろ)。

**% × 100 = 前の bp の確かめ**(事実。実行したもの):

- xborder の帳簿: 既知解の期待値を ÷ 100 したものに 1e-11 % で一致(上の試験)。
- p2_08_run: 直す前の `xborder_p2`/`_fast`/`p2_08_run` を `git show HEAD:` で作業場の外(scratchpad)に取り出し、新旧を同じ入力で比べた。既知解の 5 取引と、乱数で作った 12 日・889 取引の系列で、`full_stats` の平均・CI・SE・最大 DD・資金調達・σ・費用の `|% × 100 − bp| / max(1, |bp|)` の最大 3.9e-16、Sharpe・勝率・グロス・円損益の差の最大 1.8e-12、対照 1(無作為時刻)と対照 2(符号シャッフル)の平均の差の最大 2.7e-15。`read_prev_csv` を実物の反復 1 `configs.csv` に当て、`|mean_net_pct × 100 − mean_net_bps|` の最大 3.6e-15。
- p2_04_run: 開発セット(ペアの日付 1990-01-05〜2015-08-28)で走らせ直し、git の反復 0・反復 1 の CSV と列ごとに比べた。全列が「同じ」か「新しい値 × 100 = 古い値」(相対 1e-9 以内)のどちらか。違ったのは (a) `condition_summary_3lines.csv` の列名「同時置換帰無95点(最大差, bps)」が「%」になった所、(b) `joint_permutation_null.csv` の p50/p95/p99 が帰無 A の行(ネット)だけ 1/100、帰無 B の行(グロスの差)は同じ — の 2 つで、どちらも意図どおり。
- p2_01/p2_02/p2_03 の本体・final・g1・p2_01b: 実データでは走らせていない(final と g1・p2_01b は封印期間の出力を読み、2023-12-17 より後のデータを含むため)。合成データの試験と `py_compile` だけ。

## 5. 迷ったこと(リードの判断が要るもの)

1. **p2_04 のバイト一致の試験 2 本**(上)。直す道は (a) 反復 0・1 の参照の CSV を作り直す(前の記録を書き換えない決まり §2 に当たる)、(b) 試験を「古い列 ÷ 100 で読んで数値で比べる」形に変える(試験の意味が変わる。凍結した PREREG の「反復 0 の既定の挙動を変えない」に関わる)。私はどちらもしていない。
2. **`edge_trend` の `value_unit` を必須にした**。既定を "%" にする手もあった。必須にしたので、ほかの作業者の受け持ちに単位を渡さずに呼ぶ所があれば止まる。追跡されている `.py` の呼び手は p2_01b・p2_04・p2_08 と試験だけだった(`git ls-files -z -- '*.py' … | xargs -0 grep -nE 'edge_trend\(|state_split\(|value_unit|cost_bps='`)。
3. **p2_08 のエッジ推移でグロスの脚も % にした**(3 脚の表の列 `slope_pct_per_week` を 1 つの単位にするため)。p2_04・p2_01b は脚ごとに単位を持たせ、グロスは bps のまま。そろっていない。
4. **表示の桁**: p2_01/02/03/04・g1 では % の列の桁を 2 増やしたが、p2_08_run の本文の表は 3 桁のまま(% の 3 桁 = 0.1 bp 刻み)。混ざった表(帰無の要約など)があり、機械的に増やせなかった。
5. **事前登録の値の持ち方**: `MDE_BPS`(P2-01・P2-03)・`GROSS_GATE_BPS`・`MDE_DIFF_BPS`・`REF_DEV`/`REF_SEALED` は bp のまま残し、ネットと比べる所で ÷ 100(`MDE_PCT`)。p2_08 の `MDE_REGISTERED`/`SIGMA_REGISTERED` と judge_gates の `SCALP_NET_*_BAR` は値ごと % に置き換えた(ネットとしか比べないため)。持ち方が 2 通りある。
6. **judge_gates G8 の出所の文「report f: n=21, -8.2 bps」**は書き換えていない。資金調達の時刻窓の値動き(値動き率)かネットか、文からは分からない。
7. **p2_03_run の「他の系列は補正の影響を受けていない」の突き合わせ**は、反復 0 と今の pairs CSV の共通の列だけを比べる。名前を変えた列(費用・ネット)は比べる対象から外れた。
8. **p2_02 の `sensitivity_median_close_1343_bps_denominator`**(中身は円の終値)を `…_yen_denominator` にした。名前の bp は値動き率でも費用でもなかった。
9. **合成の試験の数値の読み方**: `test_bot_research_overnight.py` の費用つき `state_split` の場面は、数値を変えずに「% と読む」とコメントした(ほかの場面のコメントは bps のまま)。
10. **`codefix_live.md` の「直さなかったもの」の 2 行**(`overnight.state_split` の `cost_bps`・`edge_trend` の `value_unit` の既定 "bps")は、この直しで閉じた(呼び手 g1・p2_01b・p2_04・p2_08 も直した)。
11. 上の 1 の (b) には同じ試験ファイルの中に手本がある: `test_iteration1_unconditional_rows_reproduce_iteration0_train_val` は、この直しで「反復 0 の記録 ÷ 100 を数値で比べる」形にした(新しい試験ではなく、今ある試験を名前と単位に合わせたもの)。

## 6. 作業中に起きたこと

- 新旧の突き合わせのため、直す前の `p2_08_run.py` を `git show` で `scripts/phase2/_w1_tmp_p2_08_run_old.py` に一度書き、数秒後に scratchpad へ移した(作業木には残っていない)。
- p2_04 の試験と私の突き合わせの台本は `p2_04_run.main` を走らせる。`main` は RUN.json に書くため `backtest_data/phase2_sealed/P2-04/SEALED.json` の md5 を取り、`load_unsealed` は封印の記録を読んで開発セットだけに切る(どちらも元からある台本の動き)。私がその置き場を開いて読んだり grep したりはしていない。読んだデータの日付は 2015-08-28 まで。
- 着手前の追加の試験(`test_phase2_seal.py` を含む 6 本)を一度回した。`test_phase2_seal.py` は tmp に合成の置き場を作る試験。
- `config/constants.yaml` の `realized_taker_one_way_bps` は、ほかの作業者がすでに `realized_taker_one_way_pct`(値 0.010・0.013 %)にしていた。p2_08_run のコメントはその新しい名前を指す。

## 7. 時刻

- 着手: `Sat Oct 10 00:26:56 JST 2026`
- 試験の最後の実行: `Sat Oct 10 01:04:04 JST 2026`
- 終わり(この報告を書き終えた時刻): 下の最終行
- 見込み 150 分に対し、実際は約 45 分。差の理由は推定(実測なし): 置き換えの多くを台本でまとめて当てたため。
- 終わり: `Sat Oct 10 01:08:15 JST 2026`

## 続き(リードの決め 1〜5 を受けて。01:09〜01:16 JST)

### 着手前の表

| やろうとすること | 原文の該当語(逐語。リードの決めはオーナーの L-920・L-923〜L-925 の委任の中の判断) |
|---|---|
| p2_04 のバイト一致の試験 2 本を、参照の古い列 ÷ 100 で読んで数値で比べる形に直す | 「**たまたま見つかったやつも含めてわかってる修正が必要なもの全部直してください**」L-920 |
| p2_08 のエッジ推移のグロスの脚を bp に戻す | 「**bpの意味は「値動き率」としてのみ残し**」L-920 |
| `edge_trend` の呼び手を grep で確かめる・G8 の「-8.2 bps」の出所をたどる | 「**bpの意味は「値動き率」としてのみ残し、その他の意味を持たせないようにすること**」L-920 |
| 1 時間で止める | (リードの上限。オーナーの「**2時間を上限にしろ**」L-923 の内側) |

完了見込み(実測なし): 試験 2 本の直し 25 分・p2_08 10 分・grep と G8 10 分・試験と追記 15 分、計 60 分。

### 1. p2_04 のバイト一致の試験 2 本(直した)

`tests/test_phase2_p2_04.py` に `_assert_matches_reference_l920` と、ファイルごとの列の対応表 `_L920_PCT_COLUMNS` を足した(新しい試験ではなく、2 本の試験の比べ方の部品)。`test_iteration0_output_is_byte_identical_to_the_committed_reference` と `test_iteration1_output_is_still_byte_identical_after_adding_iteration2` はこれで比べる。試験の名前はそのまま残し、docstring に L-920 の後の比べ方を書いた。

- 列の対応(試験の中に全部書いた): 参照の `*_bps` の列(ネット・費用)→ 走らせ直しの `*_pct` の列、参照の値 ÷ 100。名前に単位の無いネットの列(`ci_lo`/`ci_hi`/`mean`/`diff`/`se`/`mde`/`null_p95`/`net_mean_<年代>`/`null_A_*`/`control1_draws.csv` の全列 など)も、ファイルごとに名指しして ÷ 100。`joint_permutation_null.csv`・`iter1_joint_permutation_null.csv` は帰無 A の行(ネット)だけ p50/p95/p99 を ÷ 100、帰無 B の行(グロスの差)はそのまま。`pairs_1306.csv`・`pairs_1321.csv`・`pairs_futures.csv` の費用・ネットの列も名前を対応させた。
- それ以外の列(グロス・値動き率の bp、件数、ラベル、Sharpe、勝率)は参照のまま比べる。列の並びは「参照の列を対応表で読み替えた並び」と完全一致を求める。
- 許す差: 数値の列は相対 1e-9(と、ゼロの値のための絶対 1e-12)。文字・真偽の列は完全一致。前のバイト一致から緩めた理由は、% への換算(× 1/100)と、% の系列で計算し直した Sharpe(尺度によらない量)で末尾の桁が変わるため。
- 参照の CSV は作り直していない。

### 2. `edge_trend` の呼び手(確かめた)

```
$ git ls-files -z -- '*.py' ':!docs/RESEARCH/WINDOW1' ':!backtest_data/phase2_sealed' | xargs -0 grep -nE '\bedge_trend\('
scripts/phase2/p2_01b_history.py:266:        res = edge_trend(dates, values, regime_dates=REGIME_DATES, value_unit=unit,
scripts/phase2/p2_04_run.py:1142:                res = edge_trend(frame["date"], frame[col].to_numpy(dtype=float),
scripts/phase2/p2_08_run.py:724:        res = edge_trend(dates, vals, window=EDGE_WINDOW, block=EDGE_BLOCK, time_unit="week",
src/bot/research/overnight.py:324:def edge_trend(
tests/test_bot_research_overnight.py:369:    return edge_trend(dates, x, **kwargs)
```

呼び手は 4 か所で、全部が `value_unit` を渡している(p2_04_run.py 1146 行 `value_unit=unit`、p2_08_run.py 726 行 `value_unit=unit`、試験は 367 行の `kwargs` に `value_unit="bps"`)。git に載っていない `.py` は無かった(`git ls-files --others --exclude-standard -- '*.py'` の出力が空)。

### 3. p2_08 のグロスの脚を bp に戻した

- `edge_trend_for`: グロスの脚 `a["gross_bps"]`(bp、`value_unit="bps"`)、費用・ネットは %(`value_unit="%"`)。p2_04・p2_01b とそろった。
- 要約の列 `slope_pct_per_week` → `slope_per_week` と `slope_unit`(脚ごとの単位。`"bps/week"` か `"%/week"`)。本文の表に「単位」の列を足し、説明を「傾きの単位は脚ごと(グロス bps/週、費用・ネット %/週)」に。
- 年別表の列: `gross_mean` → `gross_mean_bps`、`cost_mean` → `cost_mean_pct`(3 か所)。本文の表の見出しに「net 平均(%)」「グロス平均(bps)」「費用平均(%)」。
- 確かめ(事実): 直す前の版(scratchpad の写し)と新しい版の `edge_trend_for` を、乱数で作った 40 日の系列に当てた。グロスの傾きは前と同じ値(−0.8476186163553375)、費用・ネットの傾きは × 100 で前と一致(差は最大 1e-15 程度)、判定文は 3 脚とも同じ。
- §1 の表の p2_08_run の行にある「エッジ推移の 3 脚はすべて % にそろえ」は、この直しで置き換わった。

### 4. 表示の桁

決めのとおり変えていない。

### 5. judge_gates G8 の「-8.2 bps」(値動き率と決め、bp のまま)

たどった道筋:
1. `scripts/judge_gates.py` の G8 の `source` は「KNOWLEDGE.md §4 (report f: n=21, -8.2 bps, t~1.8)」。KNOWLEDGE.md は全捨て(L-019)で今の作業木に無い。git 履歴は掘っていない(A-5)。
2. 今の作業木で同じ数を grep した(`git ls-files -z … | xargs -0 grep -nE '8\.2 ?bps|-8\.2|−8\.2'` で資金調達・13:00 に関わる行を探した)。当たりは `src/bot/strategy/composite.py:344` の `FundingWindowModule` の docstring「**-8.2bps drift after the 13:00 UTC funding settlement on n=21 (t~1.8)**」。
3. G8 が数えているのは `candles_FX_BTC_JPY*.csv`(足の値段)の 13:00 UTC の窓を含む日数で、取引の損益ではない(`gate_funding` の本文、`src/bot/monitoring/gates.py` の `FUNDING_HOUR_UTC = 13`・`FUNDING_WINDOW_MIN = 30`)。

結論: 決済の後の「値段の流れ(drift)」の率なので、値動き率。文は書き換えず、直前にコメント 3 行(値動き率なので bp のまま、の理由と出所)を足した。

### 回した試験(01:12〜01:16 JST)

```
$ PYTHONPATH=src python -m pytest tests/test_phase2_p2_04.py
34 passed in 81.21s (0:01:21)

$ PYTHONPATH=src python -m pytest tests/test_bot_research_overnight.py tests/test_jev_design.py tests/test_judge_gates.py tests/test_phase2_p2_01.py tests/test_phase2_p2_02.py tests/test_phase2_p2_02_final.py tests/test_xborder_p2_fast.py tests/test_xborder_p2_known_answer.py
187 passed in 84.20s (0:01:24)

$ PYTHONPATH=src python -m pytest tests/test_phase2_p2_01_final.py tests/test_phase2_p2_03.py tests/test_phase2_p2_03_final.py tests/test_phase2_p2_03_iter2.py tests/test_xborder_p2_fx.py tests/test_xborder_p2_state.py tests/test_audit_gates_wired.py tests/test_composite.py tests/test_market_view.py
339 passed in 14.17s
```

p2_04 の試験は前と同じく `p2_04_run.main` を開発セット(2015-08-28 まで)で走らせ、その中で台本が `phase2_sealed/P2-04/SEALED.json` の md5 を取る(元からある動き。私がその置き場を開いて読んではいない)。

### 時刻

- 着手: `Sat Oct 10 01:09:12 JST 2026`
- 試験の最後: `Sat Oct 10 01:15:50 JST 2026`
- 見込み 60 分に対し約 10 分(差の理由は推定: 対応表は前回の列ごとの突き合わせの結果をそのまま使えたため)。
- 終わり: `Sat Oct 10 01:16:22 JST 2026`
