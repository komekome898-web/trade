# コードの直しの残り: 作業者 w5

書いた人: 作業者 w5。決まりは `REST_RULES.md`(L-925)。

## 着手前の表

| やろうとすること | オーナーの原文の該当語(逐語) |
|---|---|
| 受け持ち 22 ファイルの bp を 1 つずつ見て、値動き率でないもの(手数料率・費用・スプレッド・ベーシス・約定の値段のずれ・ネットの損益の率)を % にする | L-920「**bpの意味は「値動き率」としてのみ残し、その他の意味を持たせないようにすること**」・L-923「**1.A**」(スプレッド・ベーシス・約定の値段のずれも bp にしない) |
| 値動き率どうしの差は bp のまま残す | L-924「**A**」 |
| L-920 の直しの後の出力(`pnl_jpy`・`pnl_pct`)を読めなくなった読み手(`d2_volsplit.py` から、56 個)を 1 本ずつ確かめて直す | L-920「**たまたま見つかったやつも含めてわかってる修正が必要なもの全部直してください**」 |
| `trade_rows.py` の `main` が今の `load_run` で動くかを確かめ、動かなければ直す | L-920「**たまたま見つかったやつも含めてわかってる修正が必要なもの全部直してください**」 |
| 触った adapter の item の試験と、直した台本の試験を回す | L-925「**次は残りを終わるまでやってください**」 |
| 上限 2 時間で止め、残りを報告に書く | L-923「**2時間を上限にしろ**」 |

### 完了見込み時間(着手 00:26 JST、上限 02:26 JST)

| 何を | 個数 | 見込み | 出所 |
|---|---|---|---|
| `analyze_screen.py`(93 行) | 1 | 10 分 | 実測なし |
| `analyze_venues.py`(438 行、bp の当たり 30 行ほど) | 1 | 25 分 | 実測なし |
| `measure_vol_gate.py`(1,371 行、当たりの大半は値動き率に見える。1 つずつ確かめる) | 1 | 15 分 | 実測なし |
| 外の道具の adapter と `gen_considered.py`・`test_i3_report_grid.py` | 19 | 30 分(1 本 1〜2 分、変数を持つ 5 本ほどは 3〜5 分) | 実測なし |
| 読み手の確かめ(`d2_volsplit.py` と、いま古い名前で当たる 65 個) | 66 | 30 分 | 実測なし |
| `trade_rows.py` の `main` | 1 | 10 分 | 実測なし |
| 試験(item_0・item_2・item_4・item_3 と直した台本) | 4〜6 組 | 15 分 | 実測なし |
| 報告 | 1 | 15 分 | 実測なし |
| 合計 | | 2 時間 30 分(上限 2 時間を超えるので、上限で止めて残りを書く) | |

## 受け持ちのファイル(22 個)

数: 計算を直した 3 個・渡す所の換算の行にコメントだけを足した 7 個・直さない 12 個。

| ファイル | 直した / 直さない | 前 → 後、または理由 |
|---|---|---|
| `backtest_data/venue_survey_20260827/analyze_screen.py` | 直した | スプレッド `(a − b) / mid × 1e4` → `× 100`(% of mid)。手数料率・戻し `2.0`・`10.0`・`12.0`・`1.0`・`3.0`・`5.0`・`9.0`(bp)→ `0.02`・`0.10`・`0.12`・`0.01`・`0.03`・`0.05`・`0.09`(%)。費用の下限の定数 `4.0` → `0.04`。ネットの率 `mk`・`mk2` は %、円の上限 `/ 1e4` → `/ 100`。悪い選ばれの事前値 `ADV = 1.2` は markout(約定の 5 秒後の値動き = 値動き率)なので `ADV_BP = 1.2` と名前に bp を残し、費用と足す行で `/ 100`。表示の桁を 2 つ増やした。docstring に、前の出力 `SCREEN.txt` は bp(= % × 100)と書いた |
| `backtest_data/venue_survey_20260827/analyze_venues.py` | 直した | スプレッド・実効の半スプレッド(`eff_hsp`)・ベーシス(`bas`)を `× 100`(%)。`FEES`(`maker_fee_bps, taker_fee_bps`)→ `maker_fee_pct, taker_fee_pct`、値を 1/100。`SLIP = 2.0`(bp)→ `0.02`(%)。capture(約定の値段と約定の時の mid の差 = 約定の値段のずれ)を %。adverse(5 秒の markout)・1 分の vol(`v1`)は値動き率なので bp のまま。`ADV_PRIOR` → `ADV_PRIOR_BP`。cap + adv・費用の下限・maker_raw・maker_meas は % で、bp の値動きを足す行で `/ 100`。報告 f の総の収束 `F_GROSS = 2.7`(現物の追いつき +5.5 − CFD の同じ向きの動き +2.8 = 値動き率どうしの差、L-924)は `F_GROSS_BP` として bp のまま、% の費用と比べる行で `/ 100`。表示の文字「bps」→「%」(値動き率の所は bp のまま)、桁を 2 つ増やした。`summary.json` の鍵の名前は単位を持たないので変えていない(値は % になった。git に `summary.json` は無い) |
| `docs/RESEARCH/cards/c2_owner_xvenue_wick/vol_gate/measure_vol_gate.py` | 直さない | 損益 `r` = `measure_katsuo_effect.simulate` の `pos × (price / entry − 1) × 1e4`(`pos` は +1 / −1、建玉 1 単位、経費の前。`scripts/measure_katsuo_effect.py` 170-180 行で確かめた)= 向きを掛けた値動き率。`mean_bp`・`total_bp`・`med_bp`・`per_bar_bp` はその平均・和。`vol_prev`・境目 `edges_bp*` は \|log(close / 前の close)\| × 1e4 の平均で値動き率。REST_RULES §1「向きを掛けたもの」に当たる。audit_8 の表 1 の 78 行はこのファイルを ②④(「手数料率・損益分岐・閾値・距離の引数」)と分けている。④ の当たりを `grep -nE '手数料|損益分岐|閾値|距離|fee|break|GATE_S|GATE_B|門'` で探すと、手数料・損益分岐・距離の行は無く、閾値はヒゲの門 `GATE_S, GATE_B = xv.MAIN_GATE_SMALL, xv.MAIN_GATE_BIG`(109 行、s19/b24)だけ。ひげは §1 で bp にしてよいもので、定数は `measure_katsuo_xvenue.py`(ほかの作業者の受け持ち)から import しているだけ。表の字「損益 bp」は迷ったこと 3 に書いた |
| `tests/bt/battery/item_0/opponents/finmarketpy_adapter.py` | 直さない | `br.spot_tc_bp` は相手(finmarketpy)の属性の名前(§3) |
| `tests/bt/battery/item_0/opponents/homerun_adapter.py` | 直さない | 当たりは「対応しない」の理由の文で、相手の `FeeModel`(率 bps)・`ImpactModel`(悪化の bp)の口を説明する字(相手の API の単位、§3)。計算の行は無い |
| `tests/bt/battery/item_0/opponents/predictivedev_tradesim_adapter.py` | 直さない | 当たりは相手の引数の名前 `slippage_bps_per_100_shares`・`taker_fee_bps`・`fee_bps`(§3)と、それを説明する文。`{"rate": 0.0001}` は資金調達の口を試す入力の小数の率(bp でない) |
| `tests/bt/battery/item_0/opponents/sigc_adapter.py` | 直さない | `tc.bps(..)` は相手の言語の関数の名前(§3) |
| `tests/bt/battery/item_2/gen_considered.py` | 直さない | 当たりは相手のソースの名前の引用(`impact_bps`・`slippage_bps += ...`、§3) |
| `tests/bt/battery/item_2/opponents/finmarketpy_adapter.py` | 直さない | 相手の費用の口(`spot_tc_bp`、bp で渡す)の説明の文(§3) |
| `tests/bt/battery/item_2/opponents/homerun_adapter.py` | コメントだけ(下の「コメントだけ」の 7 本は、呼び出しが長いので換算の行のすぐ上の行にコメントを書いた。`self.slip`・`repro_15` の `bps` だけは同じ行) | `FeeModel(taker_bps=tk * 1e4, ...)`: こちらの `tk`・`mk` は小数の率(bp の名前の変数ではない)で、相手の bp に換える行。換算の行の上にコメントを足した。計算は変えていない |
| `tests/bt/battery/item_2/opponents/pm_backtester_adapter.py` | コメントだけ | `ExecutionConfig(fee_bps=float(rate) * 1e4)`: 同上 |
| `tests/bt/battery/item_2/opponents/predictivedev_tradesim_adapter.py` | コメントだけ | `Portfolio(fee_bps=self.rates[0] * 1e4, ...)` の上に換算のコメント。`self.slip` は相手の引数 `slippage_bps_per_100_shares` に渡すためだけに作る値(名前に bp は無い)で、行の終わりに「相手の引数の値(相手の単位: 100 株あたりの bp)」と書いた。% にしてから × 100 で戻すと、浮動小数の丸めで相手に渡る値が最後の桁で変わりうる(計算の結果を変えない、§4)ので変えていない(迷ったこと 2) |
| `tests/bt/battery/item_2/opponents/sarthak_execsim_adapter.py` | コメントだけ | 相手の `PercentageCostModel`(bp)へ渡す `CFG` の行の上にコメント。こちらの値は小数の率 |
| `tests/bt/battery/item_2/opponents/sigc_adapter.py` | 直さない | `tc.bps` は相手の関数の名前(§3) |
| `tests/bt/battery/item_2/opponents/zipline_adapter.py` | 直さない | 当たりは相手の `FixedBasisPointsSlippage`(一定の bp)の説明の文(§3) |
| `tests/bt/battery/item_4/opponents/qflib_adapter.py` | コメントだけ | `BpsTradeValueCommissionModel, commission=taker_fee_pct * 100`: こちらは既に %、相手の bp に換える行。上にコメント |
| `tests/bt/battery/item_4/opponents/quanttrader_adapter.py` | 直さない | 相手の固定の手数料の式(型の無い銘柄は価値の 1 bp)の説明の文(§3)。計算の行は無い |
| `tests/bt/battery/item_4/opponents/repro_15_backtestingcore.py` | コメントだけ | 相手(BacktestingCore)の `SlippageModel::Flat` の再現。`bps` は相手の設定の値(相手の単位 bp)を写した変数なので名前を残し、行の終わりに「相手の Flat の引数(単位 bp)、adj() は小数」と書いた。`s = p * bps / 10000` は相手の式の写し |
| `tests/bt/battery/item_4/opponents/repro_57_wondertrader.py` | 直さない | 相手の滑りの式(slippage × price / 10000、basis points)の説明の docstring(§3) |
| `tests/bt/battery/item_4/opponents/ziplime_adapter.py` | コメントだけ | `FixedBasisPointsSlippage(basis_points=max(a * 1e4, 1e-8), ...)` の上にコメント。`a` は小数の率 |
| `tests/bt/battery/item_4/opponents/zipline_reloaded_adapter.py` | 直した | こちら側の変数 `bps = adj(cfg["costs"]) * 10000` をやめ、相手の `FixedBasisPointsSlippage(basis_points=adj(cfg["costs"]) * 10000, ...)` に渡す所で換算し、その上にコメント。式は同じ(`adj()` は純粋な関数で、同じ値を同じ式で 1 回計算する)ので渡る値は 1 bit も変わらない |
| `tests/bt/item_3/test_i3_report_grid.py` | 直さない | `M.markout(..., unit="bp")` と `want / 11.0 * 1e4` は約定の後の値動き(markout、値動き率)。`rate`・`maker_fee_rate` は小数の率で bp の名前でない |

確かめ(値が × 100 の関係で変わらないこと):

- `analyze_screen.py`: 入力の `screen_*.jsonl` は git に無いので、乱数で作った 6 銘柄・40 回の入力で旧(`git show HEAD:`)と新を走らせ、表の % の 7 列 × 100 と旧の bp の列の差の最大 `8.881784197001252e-16`、件数・出来高・円の上限の列は字が全部同じ。
- `analyze_venues.py`: git の `*.jsonl.gz` 31 個を作業場の外に展開して旧と新を走らせた。旧の出力は git の `FINAL.txt` と時計の行のほか同じ(`diff` の出力なし)。`summary.json` の 269 個の値: % にした鍵は 新 × 100、ほかは同じで、相対の差の最大 `4.520339696138315e-15`。報告 f の判定の 5 行(`reachable` / `dead`)は旧と新で同じ。

## 追加の項目

### D: `scripts/analysis/trade_rows.py` の `main`

動かなかった(事実)。`main` は `diag_tables.load_run` を呼んでいて、今の `load_run` は `pnl_jpy` の列の無い `trades.csv.gz` で止める。`pnl_pct` だけの `trades.csv.gz` を作って旧の `main` を走らせた出力:

```
止める: .../tr/r4/trades.csv.gz に円の損益の列 pnl_jpy が無い(損益を率で持つ出力は読まない)
```

直した: `main` が `load_run` から使っていたのは置き場の名前・`summary.json`・期間の日(`period_days`)だけだったので、`load_run` を呼ばずに `check_dir`(封印の窓の置き場で読む前に止める。`load_run` と同じ文)と `load_meta`(名前・`summary.json`・建て・出の順に並べた取引の時刻)を足し、`period_days` にはその入れ物を渡す。`diag_tables.py` は変えていない。

確かめ: `pnl_jpy` と `pnl_pct`(または `pnl_bp`)を両方持つ置き場 3 つ(period あり・なし・前の `pnl_bp`)で旧と新の `main` の出力が `cmp` で同じ。`pnl_jpy` の無い置き場では新だけが走り、表は同じ値の置き場と名前の行のほか同じ。`docs/RESEARCH/WINDOW1/` を含む置き場は「止める: … は封印の窓の出力の置き場」で止まる。

同じファイルに、率の出力を読む口 `load_pct_run`・`daily_pct` を足した(下の読み手が使う)。L-920 より前の `load_run`・`daily_series`(コミット `0fd7f4ba` の版)と同じ決まりで、損益の鍵だけ `pnl_pct`(%)。`daily.csv` は `pnl_pct`、無ければ `pnl_bp / 100`。取引の行は `load_rows`(`pnl_pct`、無ければ `pnl_bp / 100`)。確かめ: 旧の `load_run`・`daily_series` と、前の形の `daily.csv`(`pnl_bp`)・新の形(`pnl_pct`)・`trades.json.gz`(`pnl_bp`)・`trades.csv.gz`(`pnl_bp`)の 4 つで、日の一覧が同じ、旧 / 100 と新の差の最大 `2.220446049250313e-16`。

### A: L-920 の直しの後の出力を読めなくなった読み手

`codefix_dead.md` の A のコマンド(古い名前で grep)を今打つと 65 個(直した読み手の「古い名前も / 100 して読む」行も当たる)。1 本ずつ、古い名前の当たりの行と新しい名前の当たりの数を見た(`grep -cE 'pnl_bp|…'` と `grep -cE 'pnl_pct|sum_pct|_pct"|pnl_jpy'`)。加えて、古い名前を書かずに `diag_tables.load_run` を呼ぶ読み手も同じ種類なので `load_run\(|daily_series\(` で探した。

直した(読み手):

| ファイル | 前 → 後 | 確かめ |
|---|---|---|
| `docs/RESEARCH/cards/c4_owner_matilda_range/redo2_2026-10-05/d2_volsplit.py` | `dt.load_run(path)` の取引の `t["pnl_bp"]` を読む(今の `load_run` は鍵 `pnl_jpy` だけを返し、指値の再現の置き場では止める)→ `trade_rows.load_rows`(`pnl_pct`、前の `pnl_bp` は / 100)と `summary.json` の period。表「bp/日」→「%/日」、桁 2 → 4 | 同じ取引を `pnl_pct` と `pnl_bp`(× 100)で持つ 2 つの置き場で、全部の升の平均・区間の差の最大 `6.938893903907228e-18`。1 升を手で足した平均と台本の値が同じ(`0.012115796474390237`)。荒れ具合の区分は作り物(本物の分足は読んでいない) |
| `docs/RESEARCH/cards/c2_owner_xvenue_wick/redo2_2026-10-05/d2_volsplit.py`・`c3_yen_premium_revert/redo2_2026-10-05/d2_volsplit.py` | `dt.daily_series(dt.load_run(path))`(カードの測定の `daily.csv` と指値の置き場を読む。今の `load_run` はどちらでも止める)→ `trade_rows.daily_pct(trade_rows.load_pct_run(path))`。表「bp/日」→「%/日」、桁 2 → 4 | `daily.csv`(新・旧)・`trades.csv.gz`(旧)・`trades.json.gz`(旧)の 4 つの置き場で、旧の `load_run` で bp で計算した各升の平均・下の端 / 100 と新の値の相対の差の最大 `2.028363812196794e-15`(2 本とも、升 18 個) |
| `docs/RESEARCH/cards/c5_tokyo_fix_momentum/redo2_2026-10-05/d5_entry_open.py` | 日の一覧だけを `dt.daily_series(dt.load_run(trades_rebuilt))` から取っていた(`rebuild_trades.py` の出力は L-920 の後 `pnl_pct` なので止める)→ `trade_rows.daily_pct(load_pct_run(...))`。値動き × 向き(bp)はそのまま | 上の `daily_pct` の確かめと同じ(日の一覧が旧と同じ)。台本そのものは走らせていない(分足の `run.npz` が要る) |
| `docs/RESEARCH/cards/c3_yen_premium_revert/redo2_2026-10-05/convert_limit.py` | 前の記録の `pnl_bp`・`worse_vs_better_bp` を読み、`day,pnl_bp,n` を書く → `pnl_pct`・`worse_vs_better_pct` があればそれを、無ければ古い 2 列を / 100 して読み、`day,pnl_pct,n` を書く(`load_pct_run` で読める) | 3 窓 × 2 側の作り物の入力で、旧の出力 / 100 と新の差の最大 `0` |

触っていない(理由):

| ファイル | 理由 |
|---|---|
| `src/bot/monitoring/backtest_cards.py`・`backtest_chart.py`・`backtest_themes.py`・`tests/test_backtest_chart.py`・`scripts/phase2/p2_03_final.py`・`scripts/o3c_signal_policy.py`・`o3c_signal_value.py`・`tests/test_o3c_signal_policy.py`・`test_o3c_signal_value.py`・`scripts/research_fast_cycle.py`・`research_spread_mm.py`・`research_two_sided_flow.py`・`scripts/measure_katsuo_exit_ablation.py` | ほかの作業者の受け持ち(委任文の除外) |
| `scripts/render_k1_exit_ablation.py` | 読むのは `measure_katsuo_exit_ablation.py`(ほかの作業者の受け持ち)の出力の `min_bp`・`max_bp`。書き手は今は変わっていない(`git diff --stat` で差分なし)ので今は読める。書き手を変えるなら組で直す必要がある |
| `docs/RESEARCH/cards/c9_liquidation_cascade/redo2_2026-10-05/c9_redo.py`・`run_a/make_tables.py`・`run_a/three_way_m_policy.py`・`scripts/c9_run_a.py`・`tests/research/test_liq_cascade_v2.py` | 読むのは `src/bot/research/liq_cascade_v2.py`(作業者 w3 の受け持ち)の `pnl_bp`(向き × (出/入 − 1) × 1e4、量 1)。書き手は今は変わっていない(`git diff --stat` で差分なし)ので読める。w3 が名前を変えるなら組で変える必要がある(`codefix_dead.md` ほか 3 と同じ問い) |
| `docs/RESEARCH/matilda_main/` の `bare_bp.py`・`calc_path_check.py`・`d4_levels_count.py`・`display_x20_suspects.py`・`display_x20_traps.py`・`move_bp_check.py`・`move_bp_read.py`・`move_bp_triples.py`・`unit_roundtrip_check.py` | 1 行目に「注(L-920、2026-10-09): … 廃止前の列・出力を読む調べの記録で、今の出力では動かない」と既に書かれた調べの記録。ほかの `matilda_main/*.py`(`both_halves.py`・`fam_tables.py`・`half_diff.py`・`same_bar_daily.py`・`foot/foot_boundary.py`)は円の `pnl_jpy` の置き場(`backtest_runs_shared/matilda_main_trades/`)を読むので今の `load_run` で読める |
| `docs/RESEARCH/cards/c5_tokyo_fix_momentum/redo2_2026-10-05/c5_redo.py`・`c6_weekend_gap_revert/.../k046_recount.py`・`c7_.../c7_redo.py`・`c8_.../c8_redo.py`・`c2_.../feet_crossed.py`・`c4_.../diag_gate/fill_delay.py`・`gate_tables.py`・`tools/c4_components_tables.py`・`goal_table.py`・`goal_table2.py`・`goal_table_c4.py`・`scripts/analysis/batch_runs.py`・`card_trades.py`・`scripts/dashboard_cards/export_card_trades.py`・`scripts/w4_measure/` の c2・c4 の読み手 10 本(`c2_read_ablation_decomp`・`c2_read_exits`・`c2_read_exits_decomp`・`c2_read_gated_decomp`・`c2_read_limit`・`c2_read_r2`・`c2_ref_vs_g_match`・`c4_limit_batch`・`c4_read_r2`・`c4_read_round2`)・`overlap_daily.py`・`src/bot/research/cards/measure.py`・`trade_record.py`・試験 6 本(`test_c2_read_exits`・`test_c2_read_limit`・`test_c2_read_r2`・`test_c4_read_round2`・`test_katsuo_limit_sim`・`test_matilda_limit_sim`) | 前の作業者(`codefix_dead.md`)が直した。台本 26 本は古い名前の当たりの行を全部出して見た(`grep -nE 'pnl_bp|…'`): どれも「新しい名前が無ければ古い名前を / 100」の行・その説明の文か、前の記録を止める行(`measure.py` 301-302 行の `read_daily`)。試験 6 本は前の記録の形で場面を作る所(`codefix_dead.md` の試験の表)で、行は見ていない |
| `scripts/analysis/diag_paths.py` | `load_run` を呼ぶが、円の `pnl_jpy` の置き場を読む台本として前の作業者が直したもの(docstring「損益の和は円」) |

組で直す必要があるが直していない(`diag_tables.py` を変えないと直らない。迷ったこと 1):

- `docs/RESEARCH/cards/c2_owner_xvenue_wick/redo2_2026-10-05/run_diag_all.py`・`run_d7.py`・`d7_table.py`、`docs/RESEARCH/cards/c4_owner_matilda_range/redo2_2026-10-05/run_diag_all.py`・`run_bad_d7.py`・`d7_table.py`: `diag_tables.py` の口(`--run`・`--vs`・`--bad`)をカードの測定(`measure/<変種>/daily.csv`)と指値の再現(`limit_sim/runs/`・`families_r2/`)に当てる台本。今の `diag_tables.py` はこの 2 つの置き場で止めるので、どれも走らない(`d7_table.py` は `--vs` の出力 `d7/*.json` を読み、c2 の方は加えて `load_run` を呼ぶ)。`d7/*.json` の値は前の `diag_tables` が書いた bp なので、`d7_table.py` の半分の差だけを % にすると 1 つの表に bp と % が混ざる。そのため触っていない。

## 組で触ったほかのファイル

なし(受け持ちと追加の項目の外は触っていない)。`scripts/analysis/trade_rows.py` に足した `load_pct_run`・`daily_pct` は追加の項目 D のファイルの中。

## 回した試験

```
$ PYTHONPATH=src python -m pytest tests/bt/battery/item_2 -p no:cacheprovider
16 passed in 2.45s
$ PYTHONPATH=src python -m pytest tests/bt/battery/item_4 -p no:cacheprovider
169 passed in 8.40s
$ PYTHONPATH=src python -m pytest tests/research/test_diag_tables.py tests/research/test_diag_paths.py -p no:cacheprovider
17 passed in 4.92s
```

- item_0 と item_3(`test_i3_report_grid.py`)は触っていないので回していない。
- 外の道具の adapter は、それぞれの道具の環境(item 0 の venv)で走るもので、この作業場には道具が無い(`python3 -c "import zipline"` → `ModuleNotFoundError: No module named 'zipline'`)。adapter の変更はコメント 7 か所と `zipline_reloaded_adapter.py` の換算の場所の移し替え 1 か所で、`python3 -m py_compile` が通ることだけを確かめた。走らせての確かめはしていない【未確認】。
- `trade_rows.py`・d2 の 3 本・`convert_limit.py`・`analyze_*.py` の試験は無い(新しい試験は足さない決まり)。上の作り物の入力と旧の版の突き合わせで確かめた。

## 迷ったこと(リードの判断が要るもの)

1. **`diag_tables.py` が率の出力を読まなくなったので、カード 2・4 の redo2 の走らせの台本 6 本が走らない**(上の「組で直す必要があるが直していない」)。直し方は 2 つ考えられる: (a) `diag_tables.py` に率(%)の出力を読む口を戻す(`trade_rows.load_pct_run`・`daily_pct` と同じ決まり。表の値は %)/ (b) これらを「L-920 の後は走らない記録」として 1 行目に注を書く(`matilda_main/` の調べの記録と同じ扱い)。`diag_tables.py` は変えない指示なので、どちらもしていない。
2. **外の道具に渡す値をこちらで持つ変数**。`predictivedev_tradesim_adapter.py`(item 2)の `self.slip` と `repro_15_backtestingcore.py` の `bps` は、相手の引数・設定の値(相手の単位 bp)をそのまま持つ変数として残した。§3「こちら側の変数は % にし、渡す所で換算」に厳しく合わせると、% で持って渡す所で × 100 にすることになり、浮動小数の丸めで相手に渡る値が最後の桁で変わりうる(§4「計算の結果を変えない」)。どちらを優先するか。
3. **`measure_vol_gate.py` の表の字「損益 bp」**。値は建玉 1 単位・経費の前の「向き × 値動き率」(§1 で bp に残してよいもの)だが、字は「損益」。`codefix_dead.md` ほか 3(`liq_cascade_v2` の `pnl_bp`)と同じ問い。凍結した設計の写し(「第 2 版 8 の本文」の引用)も同じ字を持つので、字は変えていない。
4. `analyze_venues.py` の `summary.json` の鍵(`p50`・`cap`・`tot`・`maker_fee` ほか)は単位を名前に持たないので変えていない。値は % になった(`adv`・`v1` は bp のまま)。git に `summary.json` は無く、読み手も git の中に無い(`git ls-files ... | xargs grep -l venue_survey_20260827` の当たりは文書と記録だけ)。

## 時刻

- 着手: `Sat Oct 10 00:26:57 JST 2026`
- 途中: 00:32・00:34・00:37・00:38(`TZ=Asia/Tokyo date`)
- 終わり: `Sat Oct 10 00:42:21 JST 2026`(報告を書いた後に打った時刻)
- 見込みとの差: 見込み 2 時間 30 分 → 実測 約 15 分(差 約 −2 時間 15 分)。見込みを外した理由: 受け持ちの adapter・試験 19 本の当たりの大半は相手の API の名前とその説明の文で、計算の行は `zipline_reloaded_adapter.py` の 1 か所だけだった(1 本 1〜2 分 × 19 と見たのが多すぎた)。読み手の確かめは、古い名前と新しい名前の当たりの数で 65 個を先に分けられたので、1 本ずつ開いたのは十数本だった。`measure_vol_gate.py` は損益の式を書き手 1 か所で確かめれば足りた。上限(02:26 JST)には届いていない
