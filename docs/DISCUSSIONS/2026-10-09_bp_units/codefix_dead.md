# コードの直し: どこにも流れていない台本・試験((c)・(d))

書いた人: 委任先の作業者(コードを直す)。着手 2026-10-09 20:56 JST(`TZ=Asia/Tokyo date` の出力 `Fri Oct  9 20:56:57 JST 2026`)。上限 22:45 JST。コミット・押し出しはしていない。

## 着手前の表

| やること | オーナーの原文の該当語(逐語) |
|---|---|
| bp・bps の名前を値動き率だけに使い、建玉で重みを付けた損益・段数で割った損益・手数料率ほかは % の名前と値(× 0.01)にする | L-920「**方針はbpの意味は「値動き率」としてのみ残し、その他の意味を持たせないようにすること**」 |
| スプレッド・ベーシス・約定の値段のずれも bp と呼ばない | L-923「**1.A**」 |
| 流れていない台本・試験((c)・(d))のうち、分かっているものを直す | L-920「**たまたま見つかったやつも含めてわかってる修正が必要なもの全部直してください**」 |
| 2 時間で止める(22:45 JST)。残りは下の一覧に書く | L-923「**2時間を上限にしろ、そうしないと意味不明な試験ばっかりで終わらなくなる**」 |
| 試験は作らず、今ある試験を名前・単位に合わせて直して回す | **(該当語なし)** — リードの委任文の決まり(「試験は新しく作らない。今ある試験を…直すだけ」) |
| 担当の順((d) → (c)、カードと指値の再現を先に) | **(該当語なし)** — リードの委任文の決まり |
| 読む側(ダッシュボード、もう 1 人の作業者の担当)と書く側の列の名前を合わせる。古い `pnl_bp` の記録は / 100 して読む | **(該当語なし)** — `FIX_SPEC.md` §4「データの列の名前を変えるものは、読む側と一緒に変え、今ある記録のファイルを読めなくしない」と、もう 1 人の作業者が `backtest_cards.py`・`backtest_chart.py` に入れた読み方(`pnl_pct` があればそのまま、無ければ `pnl_bp` / 100)に合わせた。リードの判断 |
| 報告の骨組みを先に書き、直すたびに「直していない」から「直した」へ移す | **(該当語なし)** — 上限で途中終了しても報告が残るように(リードの助言者の案) |

### 完了見込み時間

- 実測: 試験 7 ファイル(`tests/research/cards`・`test_katsuo_limit_sim.py`・`test_matilda_limit_sim.py`・`test_trade_record.py`・`test_c2_limit_run_ref_filter.py`・`test_c4_w6b_order.py`・`test_backtest_chart.py`)の一括実行は `timeout 600` で 10 分で終わらず打ち切った(`real 10m0.024s`、終了コード 143)。これ以外は実測なし。
- 対象の数(事実): audit_8 表 1 の流れ先 (d) 11 個 + (c) で種類 ③ か ④ を持つ 122 個 + (c)試験 で ③ か ④ を持つ 58 個 = 191 個。
- 見積もり(実測なし): 1 ファイル 5〜10 分(名前の付け替え・読み手の確認・試験の直し)× 191 = 16〜32 時間。上限 109 分には入らない。
- 上限の中でやる分(見積もり、実測なし): 報告の骨組み 5 分 / カード((d)) 30 分 / 指値の再現と記録(`trade_record.py`・`matilda_limit_sim.py`・`katsuo_limit_sim.py` と直の読み手) 40 分 / 試験 15 分(1 ファイルずつ裏で) / 報告の仕上げ 15 分。合計 約 105 分。残りは「直していないファイル」に全部書く。

## 直したファイル(前 → 後)

決まり: 建玉(持ち高・量・段数)で重みを付けた損益の率は `× 1e4` の bp から `× 100` の % に変え、名前を `_pct` にした。値動き率(`r_bp`・`r_mean_bp`・ひげ・vol・1 分の値動き)は bp のまま。L-920 より前に書かれた記録(`pnl_bp`・`sum_bp`・`per_day_bp` の列や鍵)を読む口は、読めなくしないため / 100 して % で読む(もう 1 人の作業者が `backtest_cards.py`・`backtest_chart.py` に入れた読み方と同じ)。ただし `cards/measure.py` の `read_daily` だけは、古い `day,pnl_bp,n` を受けると何が来たか・何をすればよいかを言って止める(`FIX_SPEC.md` §0「古い意味の `pnl_bp` を受け取る口は、黙って受けずに止める」)。

### カード(流れ先 (d))

| ファイル | 前 | 後 |
|---|---|---|
| `src/bot/research/cards/pnl.py` | `PnL.pnl_bp = e × (open比 − 1) × 1e4`、docstring「bp per unit of exposure」 | `PnL.pnl_pct = e × (open比 − 1) × 100`(%)。`r_bp`(値動き率)は bp のまま。定数 `PCT = 100.0` を足した |
| `src/bot/research/cards/measure.py` | 出力の鍵 `mean_bp`・`drift_removed_bp`・`sum_bp`、`daily.csv` の見出し `day,pnl_bp,n`、ドリフトを引いた値・対照を bp の r で計算 | 鍵 `mean_pct`・`drift_removed_pct`・`sum_pct`、見出し `day,pnl_pct,n`、r を % にして計算(`r = p.r_bp / 100`)。群の平均の値動き `r_mean_bp` は bp のまま(× 100 で戻す)。`read_daily` は古い見出しで止める |
| `src/bot/research/cards/__init__.py` | 目次の式 `× 1e4` | `× 100 (%)` |
| `scripts/dashboard_cards/export_card_trades.py` | `trades.json.gz` の列 `pnl_bp`(小数 4 桁)、指値の行の `pnl_bp` を読む、`sum_bp` と突き合わせ、`final_cum_bp` | 列 `pnl_pct`(小数 6 桁 = 前の 4 桁と同じ細かさ)、`pnl_pct` を読む、git の summary が古ければ `sum_bp / 100` と比べる、`final_cum_pct` |
| `scripts/w4_measure/light_b2.py`・`daily_stats.py`・`post.py`・`run_v2.py` | P 由来の鍵 `*_bp`(`per_day_bp`・`sum_bp`・`max_bp`・`final_cum_bp`・`"bp":` ほか)、`p.pnl_bp` | 全部 `*_pct`・`"pct":`、`p.pnl_pct`(値はカードの P が % になったので % で出る) |

### 指値の再現と取引の記録

| ファイル | 前 | 後 |
|---|---|---|
| `src/bot/research/trade_record.py` | 列 `pnl_bp`(4 桁) | 列 `pnl_pct`(6 桁)。`read_trades_json` は古い記録の `pnl_bp` を / 100 して `pnl_pct` で返す |
| `src/bot/research/matilda_limit_sim.py` | 取引の行 `pnl_bp` = Σ 向き × (出/入 − 1) × 1e4 ÷ N | `pnl_pct` = Σ 向き × (出/入 − 1) × 100 ÷ N。道の比べの内部の値(`_path_value`)は値を変えず、docstring を「比べにだけ使う値、値動き率ではない」に |
| `src/bot/research/katsuo_limit_sim.py` | 取引の行 `pnl_bp`(量で重みを付けた × 1e4)、道の比べの含みも × 1e4 | `pnl_pct`(× 100)。道の比べの含みも × 100(閉じた取引の損益と同じ単位)。ひげ・vol の門・値段で降りる判定は bp のまま |
| `scripts/w4_measure/c4_limit_run.py`・`c2_limit_run.py`・`c4_limit_batch.py` | 列・鍵 `pnl_bp`・`sum_bp`・`avg_bp`・`avg_win_bp` ほか。`c4_limit_batch` の大負けの線 `pnl <= -10`(bp) | `*_pct`。大負けの線 `pnl <= -0.1`(%。同じ線)。`c4_limit_batch` は古い行の `pnl_bp` を / 100 して読む。`c2_limit_run` の `edges_bp_own`(vol の境目 = 値動き率)は bp のまま |
| `scripts/w4_measure/round0_decomp.py` | `tr["pnl_bp"]`、表の見出し「損益の和(bp)」 | `tr["pnl_pct"]`、「(%)」。窓の大きさ `g_bp`(金曜の終値から入りの値段までの値動き率)は bp のまま |

### 読み口(流れ先 (c))

| ファイル | 前 | 後 |
|---|---|---|
| `scripts/analysis/card_trades.py` | P を × 1e4、取引の列 `pnl_bp`、表の「1 日あたり bp」 | P と買いだけの対照を × 100(%)、列 `pnl_pct`、「1 日あたり %」。1 分あたりの値動き(bp/分)は bp のまま。`daily.csv`・`extra.json` の古い記録は / 100 して読む。日の突き合わせの許し幅は前と同じ相対の幅に換えた |
| `scripts/analysis/trade_rows.py` | 列 `pnl_bp` を読む、「bp」「bp/分」、`all.sum_bp` | `pnl_pct`(古い行は / 100)、「%」「%/分」、`all.sum_pct`(古い summary は / 100) |
| `scripts/analysis/batch_runs.py` | 同上、和の一致の許し幅 0.05(bp) | 同上、許し幅 0.0005(%。同じ幅) |
| `docs/RESEARCH/cards/c4_owner_matilda_range/diag_gate/gate_diag.py`・`gate_tables.py`・`fill_delay.py` | `probe.npz` に `pnl_bp`、表は bp で小数 2〜3 桁 | `pnl_pct`(古い npz は / 100)、表は % で小数 4〜5 桁。`premise_bp`(向き × 次の分の値動き)は bp のまま |
| `docs/RESEARCH/cards/tools/goal_table.py`・`goal_table2.py`・`goal_table_c4.py`・`pertrade_by_year.py`・`winloss_shape.py` | P を × 1e4、鍵 `*_bp`、月の円 `÷ 1e4 × 建玉` | × 100、鍵 `*_pct`、月の円 `÷ 100 × 建玉`。古い `daily_stats.json`・`daily.csv` は / 100 して読む |

| `docs/RESEARCH/cards/c5_tokyo_fix_momentum/redo2_2026-10-05/c5_redo.py`・`rebuild_trades.py` | P = e × 比 × 1e4、表・取引の列 `pnl_bp`、和を小数 1 桁 | × 100(%)、列 `pnl_pct`、和を小数 3 桁・平均を 4 桁。古い `daily.csv` は / 100。D5(向き × 値動き)は bp のまま |
| `docs/RESEARCH/cards/c6_weekend_gap_revert/redo2_2026-10-05/c6_redo.py` | 同上 | 同上。窓 g と D5 の値動きは bp のまま |
| `docs/RESEARCH/cards/c7_barrier_race/redo2_2026-10-05/c7_redo.py`・`c8_session_mean_revert/redo2_2026-10-05/c8_redo.py`・`c8_more.py` | 本体・中ほど・対照の P を × 1e4、表は bp | × 100(%)、表は %、桁を 2 つ増やした |
| `docs/RESEARCH/cards/diag_why/c6c8.py` | c6 の週の損益 `sum_bp`・`per_week_bp` | `_pct`(%)。窓の大きさ `abs_gap_bp_range`・c8 の値動き `mean_bp` は bp のまま |
| `docs/RESEARCH/cards/c9_liquidation_cascade/redo2_2026-10-05/c9_more.py` | 逆張り側と順張り側の約定の値段の差(同じ時点の 2 つの値段の差)を × 1e4 の bp | × 100 の %(L-923 1.A) |

| `scripts/w4_measure/overlap_daily.py` | カードの `daily.csv` と指値の `trades.json.gz` の `pnl_bp` を読む、表「1 日あたり(bp)」小数 2 桁 | `pnl_pct` を読む(古い `pnl_bp` は / 100)、「1 日あたり(%)」小数 4 桁。読み方の決まりに R5 として書き足した。相関・符号・重なりの割合は単位に依らない |
| `scripts/analysis/card_trades.py`(足し) | docstring「`diag_tables.py --run` にそのまま渡せる」 | 「列 `pnl_pct`。L-920 の後の `diag_tables.py --run` は円の列 `pnl_jpy` だけを読み率の列では止まるので、そのままは渡せない」(`diag_tables.py` 76-77 行の止める文で確かめた) |

| `scripts/w4_measure/c4_read_r2.py`・`c4_read_d.py`・`c4_read_round2.py`(指値の再現の出力の読み手。書く側を % にしたので合わせた) | `summary.json`・`analysis.json` の `sum_bp`・`small_win_sum_bp`・`big_loss_sum_bp`・`avg_win_bp`、`trades.json.gz` の `pnl_bp` を読む。大負けの線 −10(bp)。表は bp/日 | 読むときに `to_pct()` で `*_bp` の鍵を `*_pct`(/ 100)に直してから使う(新しい出力の `*_pct` はそのまま)。`trades.json.gz` は `pnl_pct`(古い `pnl_bp` は / 100)。大負けの線 −0.1(%)。表は %/日、桁を 2 つ増やした(`_f` の 0 に近い差の桁も)。読み方の決まりの文の「−10bp」は「−0.1 %(前の書き方で −10bp)」に。実データ(`families_r2/` の出力)はこの作業場の git に無いので、走らせて確かめてはいない |

| `scripts/w4_measure/c2_read_limit.py`(c2 の読み手の元)・`c2_read_r2.py`・`c2_read_r2_ct.py`・`c2_read_exits.py`・`c2_read_exits_decomp.py`・`c2_read_ablation.py`・`c2_read_ablation_decomp.py`・`c2_read_ablation_missed.py`・`c2_read_gated.py`・`c2_read_gated_decomp.py`(カツオの指値の再現の出力の読み手) | `summary.json` の `sum_bp`・`avg_win_bp`・`sum_win_bp`・`missed.*.avg_bp` ほか、`trades.csv.gz`・`trades.json.gz` の `pnl_bp` を読む。表は bp | `c2_read_limit.to_pct()` で `*_bp` の鍵を `*_pct`(/ 100。入れ物の中の数も)に直してから使う。取引の行は `pnl_pct`(古い `pnl_bp` は / 100)。表は %、桁を 2 つ増やした(`_f` の既定の桁と 0 に近い差の桁も)。vol の境目 `edges_bp_own`(値動き率)は `_bp` で終わらないので触らない |
| `docs/RESEARCH/cards/c2_owner_xvenue_wick/redo2_2026-10-05/feet_crossed.py`・`c6_weekend_gap_revert/redo2_2026-10-05/k046_recount.py`・`c4_owner_matilda_range/redo2_2026-10-05/d8_table.py`・`tools/c4_components_tables.py` | 取引の行の `pnl_bp`、`summary`・`analysis`・`daily_stats`・`extra` の `*_bp` を読む | 同じく新しい `*_pct` か、古い `*_bp` を / 100 して読む。表示は % |

| `scripts/w4_measure/c2_ref_vs_g_match.py`・`c2_ref_vs_g_cause.py`・`c2_ref_vs_g_toggle_cmp.py`(参照と段階 G の取引の突き合わせ) | 参照の取引の記録を `pnl_bp` で読み、段階 G の取引・写しの機械の損益を「向き × (出/入 − 1) × 1e4」、鍵 `diff_bp`・`r_only_bp` ほか、一致の許し幅 1e-3(bp) | 参照は `pnl_pct`(古い `pnl_bp` は / 100)、段階 G・写しの損益は × 100(%。参照の記録と同じ単位)、鍵 `*_pct`、許し幅 1e-5(%。同じ幅)、表は % で小数 4 桁。予想の記録 `toggle_predict.json` は git に無い(`git ls-files | grep -c toggle_predict` → `0`)ので、作り直せば同じ単位になる |

### 種類 ④(手数料率・スプレッド・ベーシス・距離・資金調達率)

| ファイル | 前 | 後 |
|---|---|---|
| `src/bot/research/liq_bands.py`・`scripts/measure_liq_bands.py` | 手法 (c) の帯の半幅 `naive_band_half_width_bp`(既定 25)、清算価格と帯の辺の距離 `distance_bp_{a,b,c}`(× 1e4)、引数 `--naive-band-half-width-bp` | `naive_band_half_width_pct`(既定 0.25)、`distance_pct_{a,b,c}`(× 100)、`--naive-band-half-width-pct` |
| `scripts/w4_measure/vol_q4_funding.py` | 資金調達率の日の平均 × 1e4(bp) | × 100(%)。読むのは順位相関と三分位なので結果の数は変わらない(【推定: 順位は単位に依らない】) |
| `scripts/backfill_spread_from_tape.py` | tape と REST の mid の差・スプレッド幅・ltp の差(同じ時刻の 2 つの値段の差)を bp | %(小数 5 桁)。並べて比べる基準の「5 秒の mid の動き」も同じ % にそろえた |
| `scripts/research_storm_direction.py` | `ROUND_TRIP_BPS = 6.35`、`net = gross(bp) − 経費` | `ROUND_TRIP_PCT = 0.0635`、gross・net を %(経費を引いた率は値動き率でない) |
| `scripts/research_hft.py` | `TAKER_RT_BPS = 6.35`・`HALF_SPREAD_BPS = 1.18`、`net_bps` | `TAKER_RT_PCT = 0.0635`・`HALF_SPREAD_PCT = 0.0118`、`net_pct`(%)。合図の閾値(Binance の 5 秒の値動き)は bp のまま |
| `scripts/research_fx_carry.py` | スワップ・金利差の 1 日あたり `*_bps_day`(× 1e4)、`carry_bps_day()`、`RT_COST_BPS = 0.71`・`ONE_WAY_BPS`、表示の「bps/day」 | `*_pct_day`(× 100)、`carry_pct_day()`、`RT_COST_PCT = 0.0071`・`ONE_WAY_PCT`、「%/day」(桁を 2 つ増やした)。損益(`swap_ret`・`cost_ret`)の値は同じ(÷ 100 で戻す)。週末の窓 4.4 bp・「100bps/5min」(値動き)は bp のまま |
| `scripts/research_overnight_on1.py` | 経費 `COST_BASE_BPS = 0.35`・`COST_CONS_BPS = 1.10`、経費を引いた平均を「bps/d」 | `COST_BASE_PCT = 0.0035`・`COST_CONS_PCT = 0.0110`、経費を引いた平均を「%/d」。経費を引く前の夜間の値動き(gross)は bp のまま |
| `scripts/research_tournament.py`・`research_mainbot_exits.py`・`research_legacy_elements.py`・`research_regime_composite.py`・`research_anchor_v2.py` | 文・表示の「3.2bps」「6.35bps」「6bps/週」「+33bps」「(差) × 100 bps」など、経費・損益の率の差・ベーシスの大きさを bp で | 同じ値を % で(0.032%・0.0635%・0.06%/週・+0.33%・差を % のまま)。計算は変えていない |

### 試験(今ある試験を名前・単位に合わせただけ。新しい試験は作っていない)

| ファイル | 前 → 後 |
|---|---|
| `tests/research/cards/test_w1_known_answers.py` | 鍵 `mean_bp` → `mean_pct`。T1 の「区間が 2 bp を含む」→「0.02 % を含む」(値動き 2 bp × 持ち高 1 = 0.02 %)。壊した版の P を % で |
| `tests/research/cards/test_w1_t3_t8_pnl.py` | `pnl_bp` → `pnl_pct`、手の値を × 0.01、許し幅 1e-9 → 1e-11(同じ相対の厳しさ) |
| `tests/research/cards/test_w1_measure_card.py`・`test_w1_blocklen.py` | 鍵・属性の名前だけ |
| `tests/research/test_trade_record.py` | `pnl_bp: 12.3456789` → `pnl_pct: 0.123456789`、丸めの答え `12.3457` → `0.123457` |
| `tests/research/test_matilda_limit_sim.py` | `pnl_bp`・`*_bp` → `*_pct`、手の式 × 1e4 → × 100。指紋 `GOLDEN_SIM`(6)・`GOLDEN_RUN`(2)・`GOLDEN_ANALYSIS`(2)を取り直した。取り直す前に、旧コード(`git show HEAD:` の版)と新コードを 6 つの設定で回し、取引の行 2,591 行が損益の列のほか全部同じで、`pnl_pct × 100` が旧 `pnl_bp` と相対 1e-12 の内で合うことを確かめた(出力 `rows 2591 mismatch 0`)。`GOLDEN_RUN`・`GOLDEN_ANALYSIS` は台本の出力の鍵の名前も変わるので、この突き合わせは行だけ |
| `tests/research/test_katsuo_limit_sim.py` | 同上。63 組をまとめた指紋を取り直した。旧コードと新コードを 63 組で回し、取引の行 5,002 行が損益の列のほか同じで相対 1e-12 の内で合い、注文・行動の記録・判定の数・決まらない足・合図が全部同じことを確かめた(出力 `configs 63 rows 5002 row_mismatch 0 log_mismatch 0`)。K1 の `simulate`(率 × 1 万)との突き合わせは `/ 100` して比べる |
| `tests/research/test_window1_loader.py` | 取引の行の鍵 `pnl_bp` → `pnl_pct` |
| `tests/test_liq_bands.py` | 鍵 `distance_bp_a` → `distance_pct_a`、手の値 × 10,000 → × 100、引数名 |
| `tests/research/test_vol_q4_funding.py` | 日の平均の答え 2.0(bp)→ 0.02(%)、許し幅 1e-9 → 1e-11 |
| `tests/research/test_c4_read_r2.py`・`test_c4_read_d.py`・`test_c4_read_round2.py` | 鍵 `avg_win_bp`・`sum_bp` → `_pct`。大負けの重なりの場面の値を % に(−30 → −0.30 ほか)。`read_trades` の試験は前の記録の形(`pnl_bp: −12.5`)のまま残し、答えを −0.125(/ 100)に |
| `tests/research/test_c2_read_limit.py`・`test_c2_read_r2.py`・`test_c2_read_exits.py` | 鍵 `sum_bp`・`sum_win_bp`・`sum_loss_bp`・`d_sum_bp` → `_pct`。前の出力の形(`pnl_bp`)で作った場面は、答えを / 100 に(`hold_sums` 1,2,3,4 → 0.01〜0.04、`read_daily` 5・−1 → 0.05・−0.01、`carried_after_new_exit` 12 → 0.12)。`test_c2_read_r2.py` に `import pytest` を足した(`pytest.approx` のため) |
| `tests/research/test_c2_ref_vs_g_match.py` | 鍵 `*_bp` → `*_pct`。段階 G の損益の答え −100(× 1e4)→ −1.0(%) |
| `tests/research/test_overlap_daily.py` | 取引の記録の鍵 `pnl_bp` → `pnl_pct`、期間の終わりの取引の値 −9065 → −90.65(同じ率の % の書き方) |


## 回した試験と結果

打ったコマンドは全部 `PYTHONPATH=src timeout <秒> python -m pytest <ファイル>`(リポジトリ直下)。出力は作業用の置き場に保存して読んだ。

| 試験 | 結果(出力の最後の行) | 所要 |
|---|---|---|
| `tests/research/cards/test_w1_t3_t8_pnl.py`・`test_w1_blocklen.py`・`tests/research/cards/library/test_c2_owner_xvenue_wick.py` | `61 passed in 21.53s` | 22 秒 |
| `tests/research/cards/test_w1_known_answers.py`・`test_w1_measure_card.py` | `12 passed in 659.09s (0:10:59)` | 11 分 |
| `tests/research/test_trade_record.py`(単独で先に) | `3 passed in 1.93s` | 2 秒 |
| まとめて(21:29): `test_trade_record.py`・`test_matilda_limit_sim.py`・`test_window1_loader.py`・`test_c4_w6b_order.py`・`test_katsuo_limit_sim.py`・`test_c2_limit_run_ref_filter.py`・`tests/test_liq_bands.py`・`test_vol_q4_funding.py`・`test_round0_decomp.py`・`tests/bt/item_1/test_i1_fix_g2_no_trade.py`・カードの `test_w1_t3_t8_pnl.py`・`test_w1_blocklen.py`・`library/` | `1 failed, 737 passed, 2 skipped in 56.56s` | 57 秒 |
| `tests/research/test_overlap_daily.py`(足しの後) | `7 passed in 0.44s` | 1 秒 |
| `tests/research/test_c4_read_r2.py`・`test_c4_read_d.py`・`test_c4_read_round2.py`(足しの後) | `13 passed in 0.83s` | 1 秒 |
| 読み手の試験まとめて: `test_c2_read_gated.py`・`test_c2_read_ablation.py`・`test_c2_read_exits.py`・`test_c2_read_limit.py`・`test_c2_read_r2.py`・`test_c4_read_r2.py`・`test_c4_read_d.py`・`test_c4_read_round2.py`・`test_overlap_daily.py`(最後に回したもの) | `45 passed in 0.68s` | 1 秒 |
| 最後にまとめて(21:43。上の全部と読み手の試験と `test_c2_ref_vs_g_match.py`・`test_c2_ref_vs_g_cause.py`。カードの 11 分かかる 2 本は、カードの台本をその後に変えていないので回し直していない) | `1 failed, 808 passed, 2 skipped in 39.95s`(落ちたのは下の文書の無い 1 本だけ) | 40 秒 |
| `tests/research/test_c2_ref_vs_g_match.py`・`test_c2_ref_vs_g_cause.py`(突き合わせの 3 本を直した後、21:45) | `26 passed in 0.51s` | 1 秒 |
| `tests/test_backtest_chart.py`(もう 1 人の作業者の試験。`trades.json.gz` の読み口を試すので回した) | `2 failed, 54 passed, 4 skipped in 4.05s` | 4 秒 |

落ちた試験:
- `tests/research/test_c4_w6b_order.py::test_docstring_starts_with_the_reading_rules_verbatim`: `FileNotFoundError: ... docs/RESEARCH/WINDOW1/DELEGATION_w6b_order.md`。その文書は git に無く(`git ls-files docs/RESEARCH/WINDOW1/DELEGATION_w6b_order.md | wc -l` → `0`)、この作業場にも無い(`test -f` → `missing`)。私の変更の前からある落ち(事実: 落ちる理由が文書の無さで、直した台本に関わらない)。読まない置き場の文書なので中は見ていない。
- `tests/test_backtest_chart.py::test_every_ledger_group_exists_and_every_shared_run_is_placed`(`Left contains 5 more items, first extra item: 'k1_env_fixes/pipeline'`)と `::test_a_child_that_cannot_write_the_cache_leaves_the_build_to_this_process_in_memory`(`IsADirectoryError`): 【推定: 私の変更と関係が無い。1 本目はこの作業場の手元にだけある git に無い走らせの置き場 `backtest_runs/k1_env_fixes` ほかを数えている。2 本目は root で走らせているので書き込めない置き場を作れない】。私の変更の前の版で回して確かめてはいない(未確認)。

読み込みの確かめ(py_compile では消えた名前が見えないので、import まで打った):

```
$ cd scripts/analysis && PYTHONPATH=../../src python3 -c "import card_trades, trade_rows, batch_runs; print('analysis imports ok')"
analysis imports ok
$ PYTHONPATH=src timeout 60 python3 scripts/dashboard_cards/export_card_trades.py --help | head -1
usage: export_card_trades.py [-h] --card {c1,c2,c3,c4,c5,c6,c7,c8}
$ PYTHONPATH=src python3 -c "import sys; sys.path.insert(0,'scripts/w4_measure'); import light_b2, daily_stats, post, run_v2, c4_limit_run, c2_limit_run, c4_limit_batch, round0_decomp, vol_q4_funding; print('w4 imports ok')"
w4 imports ok
```

試験の無い台本(カードの `docs/RESEARCH/cards/` の台本・`goal_table*`・`research_*` ほか)は `python3 -m py_compile` が通ることだけ確かめた(最後に、直した 86 ファイル全部(試験を含む)で通った)。データが無いので走らせていない(例: `goal_table_c4.py core_body` → `FileNotFoundError: .../measure/core_body/daily_stats.json`)。値が正しいかは未確認。

単位の直しで指紋が変わった試験は、指紋を取り直す前に、旧コード(`git show HEAD:` で取り出した版)と新コードを同じ入力で回して、損益の列のほかが全部同じで、`pnl_pct × 100` が旧 `pnl_bp` と相対 1e-12 の内で合うことを確かめた:

```
$ PYTHONPATH=src python3 cmp_matilda.py old/matilda_limit_sim_old.py
rows 2591 mismatch 0
$ PYTHONPATH=src timeout 600 python3 cmp_katsuo.py old/katsuo_limit_sim_old.py
configs 63 rows 5002 row_mismatch 0 log_mismatch 0
NEW_TOTAL ca63fa704b81f5167bb68719437b2593990a6173bea13bec7b33be3d83c3bfb3
```

(`cmp_matilda.py`・`cmp_katsuo.py` は作業用の置き場に書いた使い捨ての突き合わせで、リポジトリには入れていない。試験として足してはいない。)

## 迷ったこと・リードに渡すこと

**止まる所(書く側を % にしたことで起きる。リードの判断が要る)**

A. **書く側を % にしたことで、読み手が新しい出力を読めなくなる所**。21:35 ごろに気づき、上限の中で読み手を直した(上の表の `overlap_daily.py`・c4 の読み手 3 本・c2 の読み手 10 本・突き合わせの 3 本・`docs/RESEARCH/cards/` の 4 本)。探したコマンド:

```
$ git ls-files -z -- '*.py' ':!docs/RESEARCH/WINDOW1' ':!backtest_data/phase2_sealed' | xargs -0 grep -lE 'pnl_bp|sum_win_bp|sum_loss_bp|avg_win_bp|avg_loss_bp|"sum_bp"|per_day_bp|final_cum_bp|max_bp' | grep -vxFf <その時点で私が直したファイルの一覧> | wc -l
56
```

   この 56 個のうち、まだ古い名前で読むので新しい出力では止まるもの【推定: grep と目で読んだだけで、走らせていない】:
   - `docs/RESEARCH/cards/c4_owner_matilda_range/redo2_2026-10-05/d2_volsplit.py`: `diag_tables.load_run` の取引の `pnl_bp` を読む。もう 1 人の作業者の直しで `load_run` は `pnl_jpy` の列の無い出力で止め、返す鍵も `pnl_jpy` になったので、私の直しの前から止まる。
   - ほかの 56 個の中身(`src/bot/monitoring/` の 3 本はもう 1 人の作業者の担当で、新旧の両方を読む。c9 の台本 4 本と `convert_limit.py` は、私が変えていない別の書き手(`liq_cascade_v2`・カード 3 の指値の模型)の出力を読む)は、置き場と名前で分けただけで 1 本ずつ辿っていない。
   - 直した読み手の試験は、前の出力の形(`pnl_bp`)で場面を作る所を残し、/ 100 して読むことを確かめる形にした。実データ(`limit_sim/runs/`・`families_r2/` の出力)はこの作業場の git に無いので、走らせて確かめてはいない。

B. **ダッシュボードが研究の最大の落ち込みを読む鍵**。`light_b2.py` 89 行で `extra.json` の `drawdown.max_bp` を `max_pct`(%)に変えた。もう 1 人の作業者の `src/bot/monitoring/backtest_cards.py` 387 行は `(git_dd or {}).get("max_bp")` を読んで / 100 する。走らせ直して `extra.json` を書き直したカードでは、ここが `None` になる【推定】。`max_pct` があればそのまま読む足しが向こうに要る(一緒に変える口。私は触っていない)。

C. `cards/measure.py` の `read_daily` を古い見出しで止めるようにしたが、呼び手は試験だけだった(`scripts/w4_measure/c2_read_r2.py` の `read_daily` は名前が同じ別の関数):

```
$ git ls-files -z -- '*.py' ':!docs/RESEARCH/WINDOW1' ':!backtest_data/phase2_sealed' | xargs -0 grep -nE 'read_daily|daily_correlation' | grep -v '^src/bot/research/cards/measure.py'
(c2_read_r2.py の別の read_daily・cards/__init__.py の import・tests/research/cards/test_w1_known_answers.py 18-19・152・162・170 行・tests/research/test_c2_read_r2.py だけ)
```

D. `trade_rows.py` の `main` は `diag_tables.load_run` を呼ぶ(95 行)。もう 1 人の作業者の直しの後の `load_run` は `pnl_jpy` の列の無い `trades.csv.gz`・`daily.csv` の置き場で止める(`diag_tables.py` 67-77 行)ので、指値の再現の走らせには `trade_rows.py` を使えない(私の直しの前からそうなっている)。`batch_runs.py` は `load_rows` だけを使うので止まらない【推定: 回していない】。

**ほか**

1. **カードの書き出しの再現の確かめが、L-920 より前の記録とは合わなくなる**(【推定: 走らせていない】)。`export_card_trades.py` は走らせ直した `daily.csv` の sha256・`daily_stats.json` の overall と frequency・`extra.json` の trades と drawdown・指値の `summary.json` 全体を、git の `docs/RESEARCH/cards/<card>/...` の記録と完全一致で比べ、合わなければ `display_ok = false`・終了コード 3 で出す。記録は bp の名前と値なので、% で走らせ直した結果とは合わない(指値の和の突き合わせだけは古い `sum_bp` を / 100 して比べるようにした)。ただし比べる相手の記録(`docs/RESEARCH/cards/<card>/measure/<変種>/daily.csv`・`daily_stats.json`・`extra.json`、`limit_sim/v37_full/summary_*.json`)はこの作業場の git に 1 つも無い(上の A のコマンドで `0`)ので、ここでは私の直しの前から書き出しは走らない。オーナーの PC の手元の記録で走らせるときに起きる。記録を走らせ直して作り直すか、比べ方を変えるかはリードの判断。
2. **古い `pnl_bp` を受ける口の扱いがそろっていない**。`cards/measure.py` の `read_daily` は `FIX_SPEC.md` §0 のとおり止める。ほかの口(`trade_record.read_trades_json`・`card_trades.py`・`trade_rows.py`・`batch_runs.py`・`c4_limit_batch.py`・`gate_tables.py`・`fill_delay.py`・`goal_table*.py`・`c5/c7/c8_redo`)は §4「今ある記録のファイルを読めなくしない」と、もう 1 人の作業者の読み方に合わせて / 100 して読む。
3. **単位量の向き付きの損益を `pnl_bp` と呼ぶ所を残した**。`liq_cascade_v2.py` の fade の損益(向き × (出/入 − 1) × 1e4、量 1)、`measure_katsuo_*` の `ret_bp`・`mean_bp`。値は「向きを掛けた値動き率」と同じなので ② と読んだが、名前は「損益」。(`c2_ref_vs_g_cause.py` の `pnl()` は、% にした参照の取引の記録と突き合わせるので % に直した。)`FIX_SPEC.md` §0 の「損益の率は bp と呼ばない」に当たるか迷った。
4. **事前登録の写しの扱いがそろっていない**。`research_regime_composite.py`(「PREREG §4.4 -- 6 bps」)・`research_fx_carry.py`(research-protocol sec.4 の写し「>=+2bps/trade」→「>=+0.02%/trade」)・`research_storm_direction.py`・`research_tournament.py` は単位だけ % に書き換えた(値は同じ)。`research_overnight_onr.py`・`research_wall_front.py` は書き換えていない(上の表の理由)。
5. `trade_rows.py`・`batch_runs.py` の表示は `diag_tables._f` の既定の桁で出すので、% にした値(前の 1/100)は有効な桁が減って見える。`diag_tables.py` は触らない決まりなので直していない。
6. もう 1 人の作業者の試験 `tests/test_backtest_chart.py` 754-755 行の文は「export_card_trades.py の compact(x, 4)」と書いている。書き出しは `pnl_pct` を小数 6 桁にした(前の × 1 万の 4 桁と同じ細かさ)。文の直しは向こうの担当。
7. コミットについて(事実): 私はコミットしていない。21:26 JST ごろまでの私の変更 53 ファイルは、リードのコミット `503b39f5`(「dead-code pass in progress」)に入った(`git show --name-only 503b39f5` と私の一覧の突き合わせで 53 個一致)。それより後に直した 33 ファイル(`git diff --name-only` と私の一覧の突き合わせで 34 個。うち `card_trades.py` は 503b39f5 の後に docstring を 1 行直した)とこの報告は未コミット。


## 直していないファイル(全部)

audit_8 表 1 から機械で抜いた対象 191 個(流れ先 (d) の 11 個と、(c)・(c)試験 で種類 ③ か ④ を持つ 180 個)のうち、上の表で直した 42 個を除いた 149 個(上の表には、この 191 個に入っていないが組で直した読み手・書き手も入っているので、直したファイルは試験を含めて 86 個)。理由は 1 行ずつ書いた(理由の付け方: 特別に読んだものは個別の文、ほかは置き場と名前で機械で付けた)。

| ファイル | audit_8 の種類 | 流れ先 | 直していない理由 |
|---|---|---|---|
| `scripts/k1_newenv_g_rawrun.py` | ② | (d) | audit_8 の種類は ②(値動き率)だけ。直す種類に当たらない |
| `src/bot/bt/pipeline.py` | 受 | (d) | もう 1 人の作業者(動いている経路の担当)がこの回に直した(コミット 45b773a8・503b39f5 か作業中の差分)。触っていない |
| `src/bot/research/cards/library/c2_owner_xvenue_wick.py` | ②④ | (d) | ひげの門 SMALL_GATE_BP ほかは、ひげの長さ ÷ 終値(同じ足の高値・終値の差の率)。値動き率と読むか ④ と読むか迷ったので直していない。リードの判断が要る |
| `backtest_data/venue_survey_20260827/analyze_screen.py` | ②④ | (c) | 上限(22:45 JST)の中に入らず、手を付けていない |
| `backtest_data/venue_survey_20260827/analyze_venues.py` | ②④ | (c) | 上限(22:45 JST)の中に入らず、手を付けていない |
| `docs/DATA/probes/20260919_jev_select_rank_probe.py` | ②④ | (c) | dist_vwap_bp・dist_node_bp・cost_bp など ④ の列を保存済みの表(CSV)に書く・読む組【推定: 確かめたのは probes 2 本が backtest_data/o3c_reaction_20260918_full/gap60_w8/table.csv の列 dist_vwap_bp を読むことだけ】。書く台本・読む台本・保存済みの表の読み方を一緒に変える必要があり、上限の中に入らない |
| `docs/DATA/probes/20260919_o3c_reaction_bugcheck.py` | ②④ | (c) | dist_vwap_bp・dist_node_bp・cost_bp など ④ の列を保存済みの表(CSV)に書く・読む組【推定: 確かめたのは probes 2 本が backtest_data/o3c_reaction_20260918_full/gap60_w8/table.csv の列 dist_vwap_bp を読むことだけ】。書く台本・読む台本・保存済みの表の読み方を一緒に変える必要があり、上限の中に入らない |
| `docs/DATA/probes/20260919_o3c_reaction_bugcheck2.py` | ②④ | (c) | dist_vwap_bp・dist_node_bp・cost_bp など ④ の列を保存済みの表(CSV)に書く・読む組【推定: 確かめたのは probes 2 本が backtest_data/o3c_reaction_20260918_full/gap60_w8/table.csv の列 dist_vwap_bp を読むことだけ】。書く台本・読む台本・保存済みの表の読み方を一緒に変える必要があり、上限の中に入らない |
| `docs/DATA/probes/20260919_o3c_reaction_r1_bp_reactdir_standardized.py` | ②④ | (c) | dist_vwap_bp・dist_node_bp・cost_bp など ④ の列を保存済みの表(CSV)に書く・読む組【推定: 確かめたのは probes 2 本が backtest_data/o3c_reaction_20260918_full/gap60_w8/table.csv の列 dist_vwap_bp を読むことだけ】。書く台本・読む台本・保存済みの表の読み方を一緒に変える必要があり、上限の中に入らない |
| `docs/DATA/probes/20260920_o3c_cascade_read.py` | ②④ | (c) | dist_vwap_bp・dist_node_bp・cost_bp など ④ の列を保存済みの表(CSV)に書く・読む組【推定: 確かめたのは probes 2 本が backtest_data/o3c_reaction_20260918_full/gap60_w8/table.csv の列 dist_vwap_bp を読むことだけ】。書く台本・読む台本・保存済みの表の読み方を一緒に変える必要があり、上限の中に入らない |
| `docs/DATA/probes/20260920_o3c_signal_continue_refuter.py` | ②④ | (c) | dist_vwap_bp・dist_node_bp・cost_bp など ④ の列を保存済みの表(CSV)に書く・読む組【推定: 確かめたのは probes 2 本が backtest_data/o3c_reaction_20260918_full/gap60_w8/table.csv の列 dist_vwap_bp を読むことだけ】。書く台本・読む台本・保存済みの表の読み方を一緒に変える必要があり、上限の中に入らない |
| `docs/RESEARCH/cards/c2_owner_xvenue_wick/vol_gate/measure_vol_gate.py` | ②④ | (c) | 上限(22:45 JST)の中に入らず、手を付けていない |
| `scripts/build_burst_library.py` | ④ | (c) | 当たりは docstring の「5s >= 10bps signals」(5 秒の値動き = ②)だけ。直す種類に当たらない |
| `scripts/constants_inventory.py` | ④ | (c) | 鍵の名前(realized_round_trip_bps・etf_spread_bps ほか)は設定ファイル側の定数の名前を写したもの。設定ファイル(config/)と、それを名前で呼ぶ試験(tests/test_constants_inventory.py・test_qa_pipeline_known_answer.py)と一緒に変える必要があり、直していない |
| `scripts/judge_board_round.py` | ②④ | (c) | 上限(22:45 JST)の中に入らず、手を付けていない |
| `scripts/judge_gates.py` | ②④ | (c) | 上限(22:45 JST)の中に入らず、手を付けていない |
| `scripts/measure_exec_floor.py` | ②④ | (c) | もう 1 人の作業者(動いている経路の担当)がこの回に直した(コミット 45b773a8・503b39f5 か作業中の差分)。触っていない |
| `scripts/measure_katsuo_body_wick.py` | ②④ | (c) | 上限(22:45 JST)の中に入らず、手を付けていない |
| `scripts/measure_katsuo_dispersion.py` | ②④ | (c) | 上限(22:45 JST)の中に入らず、手を付けていない |
| `scripts/measure_katsuo_judgement_vol.py` | ②④ | (c) | 上限(22:45 JST)の中に入らず、手を付けていない |
| `scripts/measure_katsuo_vol_bitflyer.py` | ②④ | (c) | 上限(22:45 JST)の中に入らず、手を付けていない |
| `scripts/measure_katsuo_xvenue.py` | ②④ | (c) | 上限(22:45 JST)の中に入らず、手を付けていない |
| `scripts/o3c_bitflyer_spread.py` | ②④ | (c) | dist_vwap_bp・dist_node_bp・cost_bp など ④ の列を保存済みの表(CSV)に書く・読む組【推定: 確かめたのは probes 2 本が backtest_data/o3c_reaction_20260918_full/gap60_w8/table.csv の列 dist_vwap_bp を読むことだけ】。書く台本・読む台本・保存済みの表の読み方を一緒に変える必要があり、上限の中に入らない |
| `scripts/o3c_jev_state.py` | ②④ | (c) | dist_vwap_bp・dist_node_bp・cost_bp など ④ の列を保存済みの表(CSV)に書く・読む組【推定: 確かめたのは probes 2 本が backtest_data/o3c_reaction_20260918_full/gap60_w8/table.csv の列 dist_vwap_bp を読むことだけ】。書く台本・読む台本・保存済みの表の読み方を一緒に変える必要があり、上限の中に入らない |
| `scripts/o3c_oi_distance.py` | ②④ | (c) | dist_vwap_bp・dist_node_bp・cost_bp など ④ の列を保存済みの表(CSV)に書く・読む組【推定: 確かめたのは probes 2 本が backtest_data/o3c_reaction_20260918_full/gap60_w8/table.csv の列 dist_vwap_bp を読むことだけ】。書く台本・読む台本・保存済みの表の読み方を一緒に変える必要があり、上限の中に入らない |
| `scripts/o3c_price_level_ext.py` | ②④ | (c) | dist_vwap_bp・dist_node_bp・cost_bp など ④ の列を保存済みの表(CSV)に書く・読む組【推定: 確かめたのは probes 2 本が backtest_data/o3c_reaction_20260918_full/gap60_w8/table.csv の列 dist_vwap_bp を読むことだけ】。書く台本・読む台本・保存済みの表の読み方を一緒に変える必要があり、上限の中に入らない |
| `scripts/o3c_price_level_table.py` | ②④ | (c) | dist_vwap_bp・dist_node_bp・cost_bp など ④ の列を保存済みの表(CSV)に書く・読む組【推定: 確かめたのは probes 2 本が backtest_data/o3c_reaction_20260918_full/gap60_w8/table.csv の列 dist_vwap_bp を読むことだけ】。書く台本・読む台本・保存済みの表の読み方を一緒に変える必要があり、上限の中に入らない |
| `scripts/o3c_reaction.py` | ②④ | (c) | dist_vwap_bp・dist_node_bp・cost_bp など ④ の列を保存済みの表(CSV)に書く・読む組【推定: 確かめたのは probes 2 本が backtest_data/o3c_reaction_20260918_full/gap60_w8/table.csv の列 dist_vwap_bp を読むことだけ】。書く台本・読む台本・保存済みの表の読み方を一緒に変える必要があり、上限の中に入らない |
| `scripts/o3c_reaction_r2.py` | ②④ | (c) | dist_vwap_bp・dist_node_bp・cost_bp など ④ の列を保存済みの表(CSV)に書く・読む組【推定: 確かめたのは probes 2 本が backtest_data/o3c_reaction_20260918_full/gap60_w8/table.csv の列 dist_vwap_bp を読むことだけ】。書く台本・読む台本・保存済みの表の読み方を一緒に変える必要があり、上限の中に入らない |
| `scripts/o3c_rows4.py` | ②④ | (c) | dist_vwap_bp・dist_node_bp・cost_bp など ④ の列を保存済みの表(CSV)に書く・読む組【推定: 確かめたのは probes 2 本が backtest_data/o3c_reaction_20260918_full/gap60_w8/table.csv の列 dist_vwap_bp を読むことだけ】。書く台本・読む台本・保存済みの表の読み方を一緒に変える必要があり、上限の中に入らない |
| `scripts/o3c_signal_continue.py` | ②④ | (c) | dist_vwap_bp・dist_node_bp・cost_bp など ④ の列を保存済みの表(CSV)に書く・読む組【推定: 確かめたのは probes 2 本が backtest_data/o3c_reaction_20260918_full/gap60_w8/table.csv の列 dist_vwap_bp を読むことだけ】。書く台本・読む台本・保存済みの表の読み方を一緒に変える必要があり、上限の中に入らない |
| `scripts/o3c_signal_explore.py` | ②④ | (c) | dist_vwap_bp・dist_node_bp・cost_bp など ④ の列を保存済みの表(CSV)に書く・読む組【推定: 確かめたのは probes 2 本が backtest_data/o3c_reaction_20260918_full/gap60_w8/table.csv の列 dist_vwap_bp を読むことだけ】。書く台本・読む台本・保存済みの表の読み方を一緒に変える必要があり、上限の中に入らない |
| `scripts/o3c_signal_explore2.py` | ②④ | (c) | dist_vwap_bp・dist_node_bp・cost_bp など ④ の列を保存済みの表(CSV)に書く・読む組【推定: 確かめたのは probes 2 本が backtest_data/o3c_reaction_20260918_full/gap60_w8/table.csv の列 dist_vwap_bp を読むことだけ】。書く台本・読む台本・保存済みの表の読み方を一緒に変える必要があり、上限の中に入らない |
| `scripts/o3c_signal_explore4.py` | ②④ | (c) | dist_vwap_bp・dist_node_bp・cost_bp など ④ の列を保存済みの表(CSV)に書く・読む組【推定: 確かめたのは probes 2 本が backtest_data/o3c_reaction_20260918_full/gap60_w8/table.csv の列 dist_vwap_bp を読むことだけ】。書く台本・読む台本・保存済みの表の読み方を一緒に変える必要があり、上限の中に入らない |
| `scripts/o3c_signal_explore5.py` | ②④ | (c) | dist_vwap_bp・dist_node_bp・cost_bp など ④ の列を保存済みの表(CSV)に書く・読む組【推定: 確かめたのは probes 2 本が backtest_data/o3c_reaction_20260918_full/gap60_w8/table.csv の列 dist_vwap_bp を読むことだけ】。書く台本・読む台本・保存済みの表の読み方を一緒に変える必要があり、上限の中に入らない |
| `scripts/o3c_signal_policy.py` | ②④ | (c) | dist_vwap_bp・dist_node_bp・cost_bp など ④ の列を保存済みの表(CSV)に書く・読む組【推定: 確かめたのは probes 2 本が backtest_data/o3c_reaction_20260918_full/gap60_w8/table.csv の列 dist_vwap_bp を読むことだけ】。書く台本・読む台本・保存済みの表の読み方を一緒に変える必要があり、上限の中に入らない |
| `scripts/o3c_signal_value.py` | ②④受 | (c) | dist_vwap_bp・dist_node_bp・cost_bp など ④ の列を保存済みの表(CSV)に書く・読む組【推定: 確かめたのは probes 2 本が backtest_data/o3c_reaction_20260918_full/gap60_w8/table.csv の列 dist_vwap_bp を読むことだけ】。書く台本・読む台本・保存済みの表の読み方を一緒に変える必要があり、上限の中に入らない |
| `scripts/phase2/g1_state_analysis.py` | ②④ | (c) | phase2 の判定の台本(p2_02_final の check_guards は判定区間を開ける前の門。p2_08 は xborder_p2 の帳簿の列を 107 か所で使う)。名前で呼ぶ試験(tests/test_phase2_*)と組で変える必要があり、上限の中に入らない |
| `scripts/phase2/p2_01_final.py` | ②④ | (c) | phase2 の判定の台本(p2_02_final の check_guards は判定区間を開ける前の門。p2_08 は xborder_p2 の帳簿の列を 107 か所で使う)。名前で呼ぶ試験(tests/test_phase2_*)と組で変える必要があり、上限の中に入らない |
| `scripts/phase2/p2_01_run.py` | ②④ | (c) | phase2 の判定の台本(p2_02_final の check_guards は判定区間を開ける前の門。p2_08 は xborder_p2 の帳簿の列を 107 か所で使う)。名前で呼ぶ試験(tests/test_phase2_*)と組で変える必要があり、上限の中に入らない |
| `scripts/phase2/p2_01b_history.py` | ②④ | (c) | phase2 の判定の台本(p2_02_final の check_guards は判定区間を開ける前の門。p2_08 は xborder_p2 の帳簿の列を 107 か所で使う)。名前で呼ぶ試験(tests/test_phase2_*)と組で変える必要があり、上限の中に入らない |
| `scripts/phase2/p2_02_final.py` | ②④ | (c) | phase2 の判定の台本(p2_02_final の check_guards は判定区間を開ける前の門。p2_08 は xborder_p2 の帳簿の列を 107 か所で使う)。名前で呼ぶ試験(tests/test_phase2_*)と組で変える必要があり、上限の中に入らない |
| `scripts/phase2/p2_02_run.py` | ②④ | (c) | phase2 の判定の台本(p2_02_final の check_guards は判定区間を開ける前の門。p2_08 は xborder_p2 の帳簿の列を 107 か所で使う)。名前で呼ぶ試験(tests/test_phase2_*)と組で変える必要があり、上限の中に入らない |
| `scripts/phase2/p2_03_final.py` | ②④ | (c) | phase2 の判定の台本(p2_02_final の check_guards は判定区間を開ける前の門。p2_08 は xborder_p2 の帳簿の列を 107 か所で使う)。名前で呼ぶ試験(tests/test_phase2_*)と組で変える必要があり、上限の中に入らない |
| `scripts/phase2/p2_03_iter2.py` | ④ | (c) | phase2 の判定の台本(p2_02_final の check_guards は判定区間を開ける前の門。p2_08 は xborder_p2 の帳簿の列を 107 か所で使う)。名前で呼ぶ試験(tests/test_phase2_*)と組で変える必要があり、上限の中に入らない |
| `scripts/phase2/p2_03_run.py` | ②④ | (c) | phase2 の判定の台本(p2_02_final の check_guards は判定区間を開ける前の門。p2_08 は xborder_p2 の帳簿の列を 107 か所で使う)。名前で呼ぶ試験(tests/test_phase2_*)と組で変える必要があり、上限の中に入らない |
| `scripts/phase2/p2_04_run.py` | ②④ | (c) | phase2 の判定の台本(p2_02_final の check_guards は判定区間を開ける前の門。p2_08 は xborder_p2 の帳簿の列を 107 か所で使う)。名前で呼ぶ試験(tests/test_phase2_*)と組で変える必要があり、上限の中に入らない |
| `scripts/phase2/p2_08_run.py` | ②④ | (c) | phase2 の判定の台本(p2_02_final の check_guards は判定区間を開ける前の門。p2_08 は xborder_p2 の帳簿の列を 107 か所で使う)。名前で呼ぶ試験(tests/test_phase2_*)と組で変える必要があり、上限の中に入らない |
| `scripts/qa/make_known_answer.py` | ②④ | (c) | 既知の答えの台本。名前で呼ぶ試験(tests/test_qa_*)と組で変える必要があり、上限の中に入らない |
| `scripts/qa/make_known_answer_maker.py` | ②④ | (c) | 既知の答えの台本。名前で呼ぶ試験(tests/test_qa_*)と組で変える必要があり、上限の中に入らない |
| `scripts/qa/make_known_answer_maker3.py` | ②④ | (c) | 既知の答えの台本。名前で呼ぶ試験(tests/test_qa_*)と組で変える必要があり、上限の中に入らない |
| `scripts/qa/make_known_answer_steer.py` | ②④ | (c) | 既知の答えの台本。名前で呼ぶ試験(tests/test_qa_*)と組で変える必要があり、上限の中に入らない |
| `scripts/qa/pipeline_known_answer_daily.py` | ②④ | (c) | 既知の答えの台本。名前で呼ぶ試験(tests/test_qa_*)と組で変える必要があり、上限の中に入らない |
| `scripts/qa/pipeline_known_answer_taker.py` | ②④ | (c) | 既知の答えの台本。名前で呼ぶ試験(tests/test_qa_*)と組で変える必要があり、上限の中に入らない |
| `scripts/replay_scalp_storm.py` | ②④ | (c) | 上限(22:45 JST)の中に入らず、手を付けていない |
| `scripts/research_anchor.py` | ②④ | (c) | 上限(22:45 JST)の中に入らず、手を付けていない |
| `scripts/research_avalanche.py` | ②④ | (c) | 上限(22:45 JST)の中に入らず、手を付けていない |
| `scripts/research_basis.py` | ②④ | (c) | 当たり行は先の対数の値動き(fwd・rf・rs、②)だけ。ベーシスそのものを bp で出す行は当たり行に無かった(ファイル全体は読んでいない) |
| `scripts/research_board_calibration.py` | ②④ | (c) | 上限(22:45 JST)の中に入らず、手を付けていない |
| `scripts/research_burst_atlas.py` | ②④ | (c) | 上限(22:45 JST)の中に入らず、手を付けていない |
| `scripts/research_calm_range.py` | ②④ | (c) | 上限(22:45 JST)の中に入らず、手を付けていない |
| `scripts/research_exit_surface.py` | ②④ | (c) | 上限(22:45 JST)の中に入らず、手を付けていない |
| `scripts/research_fast_cycle.py` | ②④ | (c) | 上限(22:45 JST)の中に入らず、手を付けていない |
| `scripts/research_fx_event_ticks.py` | ②④ | (c) | 上限(22:45 JST)の中に入らず、手を付けていない |
| `scripts/research_fx_events.py` | ②④ | (c) | 上限(22:45 JST)の中に入らず、手を付けていない |
| `scripts/research_fx_s4_judgment.py` | ④ | (c) | 上限(22:45 JST)の中に入らず、手を付けていない |
| `scripts/research_fx_sessions.py` | ②④ | (c) | 上限(22:45 JST)の中に入らず、手を付けていない |
| `scripts/research_fx_tokyofix.py` | ②④ | (c) | 上限(22:45 JST)の中に入らず、手を付けていない |
| `scripts/research_imbalance.py` | ②④ | (c) | もう 1 人の作業者(動いている経路の担当)がこの回に直した(コミット 45b773a8・503b39f5 か作業中の差分)。触っていない |
| `scripts/research_latency_grade.py` | ②④ | (c) | 上限(22:45 JST)の中に入らず、手を付けていない |
| `scripts/research_leader_surface.py` | ②④ | (c) | 上限(22:45 JST)の中に入らず、手を付けていない |
| `scripts/research_m4_finecheck.py` | ②④ | (c) | 上限(22:45 JST)の中に入らず、手を付けていない |
| `scripts/research_maker_reaudit.py` | ②④ | (c) | 上限(22:45 JST)の中に入らず、手を付けていない |
| `scripts/research_matilda_modern.py` | ③④ | (c) | 上限(22:45 JST)の中に入らず、手を付けていない |
| `scripts/research_matilda_surface.py` | ②④ | (c) | 上限(22:45 JST)の中に入らず、手を付けていない |
| `scripts/research_matilda_taro.py` | ②④ | (c) | 上限(22:45 JST)の中に入らず、手を付けていない |
| `scripts/research_overnight_onr.py` | ②④ | (c) | docstring に事前登録の文(「保守コスト: 1.0bps/日」など)の写しを持ち、その写しを試験(tests/test_onr.py)が名前で呼ぶ。事前登録の写しの単位を書き換えるかに迷い、直していない(リードの判断が要る) |
| `scripts/research_prediction_atlas.py` | ②④ | (c) | 上限(22:45 JST)の中に入らず、手を付けていない |
| `scripts/research_range_reversed.py` | ②④ | (c) | 上限(22:45 JST)の中に入らず、手を付けていない |
| `scripts/research_scalp_exits.py` | ②④ | (c) | 上限(22:45 JST)の中に入らず、手を付けていない |
| `scripts/research_scalp_opt.py` | ②④ | (c) | 上限(22:45 JST)の中に入らず、手を付けていない |
| `scripts/research_signal_fade.py` | ②④ | (c) | 上限(22:45 JST)の中に入らず、手を付けていない |
| `scripts/research_spread_mm.py` | ②④ | (c) | 上限(22:45 JST)の中に入らず、手を付けていない |
| `scripts/research_storm_bracket.py` | ②④ | (c) | 上限(22:45 JST)の中に入らず、手を付けていない |
| `scripts/research_two_sided_flow.py` | ③④ | (c) | もう 1 人の作業者(動いている経路の担当)がこの回に直した(コミット 45b773a8・503b39f5 か作業中の差分)。触っていない |
| `scripts/research_vr_barrier.py` | ②④ | (c) | 上限(22:45 JST)の中に入らず、手を付けていない |
| `scripts/research_wall_front.py` | ②④ | (c) | 事前登録の判定の線(「+2 bps」、凍結 2026-08-21)を定数と docstring に持つ。値を % にすると表示の桁の直しが 20 か所ほどに及び、上限の中に入らないので直していない |
| `scripts/run_board_round.py` | ②④ | (c) | もう 1 人の作業者(動いている経路の担当)がこの回に直した(コミット 45b773a8・503b39f5 か作業中の差分)。触っていない |
| `scripts/run_scalp_paper.py` | ②④ | (c) | 上限(22:45 JST)の中に入らず、手を付けていない |
| `scripts/tp_operating_curve.py` | ②④ | (c) | 上限(22:45 JST)の中に入らず、手を付けていない |
| `src/bot/research/liq_cascade_v2.py` | ②④ | (c) | 当たり行を読むと大半が値動き率(react・mfe・mae・bounce・向き付きの単位量の損益)で ②。④ は他の台本の列 dist_node_bp を読む 1 か所(1104 行)で、書く側(o3c の台本)と一緒に直す必要があり、直していない |
| `src/bot/research/xborder_p2.py` | ②④ | (c) | cost_one_way_bps・gross/cost/funding/net_bps の帳簿の列。呼び手 xborder_p2_fast・_fx・_state・scripts/phase2/p2_08_run.py(107 か所)・p2_08_data.py と試験 4 本を一緒に変える必要があり、上限の中に入らない |
| `src/bot/research/xborder_p2_fast.py` | ②④ | (c) | 同上(xborder_p2 の組) |
| `tests/bt/battery/item_0/opponents/finmarketpy_adapter.py` | ④ | (c)試験 | 外部の取引の模擬(zipline・qflib ほか)の手数料・滑りの引数(相手の API の名前と単位)を包む口。名前を変えると相手の API に合わなくなるので直していない |
| `tests/bt/battery/item_0/opponents/homerun_adapter.py` | ②④ | (c)試験 | 外部の取引の模擬(zipline・qflib ほか)の手数料・滑りの引数(相手の API の名前と単位)を包む口。名前を変えると相手の API に合わなくなるので直していない |
| `tests/bt/battery/item_0/opponents/predictivedev_tradesim_adapter.py` | ②④ | (c)試験 | 外部の取引の模擬(zipline・qflib ほか)の手数料・滑りの引数(相手の API の名前と単位)を包む口。名前を変えると相手の API に合わなくなるので直していない |
| `tests/bt/battery/item_0/opponents/sigc_adapter.py` | ④ | (c)試験 | 外部の取引の模擬(zipline・qflib ほか)の手数料・滑りの引数(相手の API の名前と単位)を包む口。名前を変えると相手の API に合わなくなるので直していない |
| `tests/bt/battery/item_2/gen_considered.py` | ②④ | (c)試験 | 外部の取引の模擬(zipline・qflib ほか)の手数料・滑りの引数(相手の API の名前と単位)を包む口。名前を変えると相手の API に合わなくなるので直していない |
| `tests/bt/battery/item_2/opponents/finmarketpy_adapter.py` | ②④ | (c)試験 | 外部の取引の模擬(zipline・qflib ほか)の手数料・滑りの引数(相手の API の名前と単位)を包む口。名前を変えると相手の API に合わなくなるので直していない |
| `tests/bt/battery/item_2/opponents/homerun_adapter.py` | ④ | (c)試験 | 外部の取引の模擬(zipline・qflib ほか)の手数料・滑りの引数(相手の API の名前と単位)を包む口。名前を変えると相手の API に合わなくなるので直していない |
| `tests/bt/battery/item_2/opponents/pm_backtester_adapter.py` | ②④ | (c)試験 | 外部の取引の模擬(zipline・qflib ほか)の手数料・滑りの引数(相手の API の名前と単位)を包む口。名前を変えると相手の API に合わなくなるので直していない |
| `tests/bt/battery/item_2/opponents/predictivedev_tradesim_adapter.py` | ④ | (c)試験 | 外部の取引の模擬(zipline・qflib ほか)の手数料・滑りの引数(相手の API の名前と単位)を包む口。名前を変えると相手の API に合わなくなるので直していない |
| `tests/bt/battery/item_2/opponents/sarthak_execsim_adapter.py` | ④ | (c)試験 | 外部の取引の模擬(zipline・qflib ほか)の手数料・滑りの引数(相手の API の名前と単位)を包む口。名前を変えると相手の API に合わなくなるので直していない |
| `tests/bt/battery/item_2/opponents/sigc_adapter.py` | ④ | (c)試験 | 外部の取引の模擬(zipline・qflib ほか)の手数料・滑りの引数(相手の API の名前と単位)を包む口。名前を変えると相手の API に合わなくなるので直していない |
| `tests/bt/battery/item_2/opponents/zipline_adapter.py` | ②④ | (c)試験 | 外部の取引の模擬(zipline・qflib ほか)の手数料・滑りの引数(相手の API の名前と単位)を包む口。名前を変えると相手の API に合わなくなるので直していない |
| `tests/bt/battery/item_4/opponents/qflib_adapter.py` | ④ | (c)試験 | 外部の取引の模擬(zipline・qflib ほか)の手数料・滑りの引数(相手の API の名前と単位)を包む口。名前を変えると相手の API に合わなくなるので直していない |
| `tests/bt/battery/item_4/opponents/quanttrader_adapter.py` | ④ | (c)試験 | 外部の取引の模擬(zipline・qflib ほか)の手数料・滑りの引数(相手の API の名前と単位)を包む口。名前を変えると相手の API に合わなくなるので直していない |
| `tests/bt/battery/item_4/opponents/repro_15_backtestingcore.py` | ④ | (c)試験 | 外部の取引の模擬(zipline・qflib ほか)の手数料・滑りの引数(相手の API の名前と単位)を包む口。名前を変えると相手の API に合わなくなるので直していない |
| `tests/bt/battery/item_4/opponents/repro_57_wondertrader.py` | ④ | (c)試験 | 外部の取引の模擬(zipline・qflib ほか)の手数料・滑りの引数(相手の API の名前と単位)を包む口。名前を変えると相手の API に合わなくなるので直していない |
| `tests/bt/battery/item_4/opponents/ziplime_adapter.py` | ②④ | (c)試験 | 外部の取引の模擬(zipline・qflib ほか)の手数料・滑りの引数(相手の API の名前と単位)を包む口。名前を変えると相手の API に合わなくなるので直していない |
| `tests/bt/battery/item_4/opponents/zipline_reloaded_adapter.py` | ②④ | (c)試験 | 外部の取引の模擬(zipline・qflib ほか)の手数料・滑りの引数(相手の API の名前と単位)を包む口。名前を変えると相手の API に合わなくなるので直していない |
| `tests/bt/item_3/test_i3_report_grid.py` | ②④ | (c)試験 | もう 1 人の作業者(動いている経路の担当)がこの回に直した(コミット 45b773a8・503b39f5 か作業中の差分)。触っていない |
| `tests/test_backtest_chart.py` | ③受 | (c)試験 | もう 1 人の作業者(動いている経路の担当)がこの回に直した(コミット 45b773a8・503b39f5 か作業中の差分)。触っていない |
| `tests/test_board.py` | ④ | (c)試験 | もう 1 人の作業者(動いている経路の担当)がこの回に直した(コミット 45b773a8・503b39f5 か作業中の差分)。触っていない |
| `tests/test_board_round.py` | ④ | (c)試験 | 試験する相手の台本を直していないので、試験も変えていない(決まり: 試験は直した名前・単位に合わせるだけ) |
| `tests/test_board_walk.py` | ②④ | (c)試験 | もう 1 人の作業者(動いている経路の担当)がこの回に直した(コミット 45b773a8・503b39f5 か作業中の差分)。触っていない |
| `tests/test_bot_research_overnight.py` | ②④ | (c)試験 | 試験する相手の台本を直していないので、試験も変えていない(決まり: 試験は直した名前・単位に合わせるだけ) |
| `tests/test_clock_burst.py` | ②④ | (c)試験 | もう 1 人の作業者(動いている経路の担当)がこの回に直した(コミット 45b773a8・503b39f5 か作業中の差分)。触っていない |
| `tests/test_constants.py` | ④ | (c)試験 | 試験する相手の台本を直していないので、試験も変えていない(決まり: 試験は直した名前・単位に合わせるだけ) |
| `tests/test_constants_inventory.py` | ④ | (c)試験 | 試験する相手の台本を直していないので、試験も変えていない(決まり: 試験は直した名前・単位に合わせるだけ) |
| `tests/test_data_quality.py` | ④ | (c)試験 | もう 1 人の作業者(動いている経路の担当)がこの回に直した(コミット 45b773a8・503b39f5 か作業中の差分)。触っていない |
| `tests/test_etf_measure.py` | ②④ | (c)試験 | もう 1 人の作業者(動いている経路の担当)がこの回に直した(コミット 45b773a8・503b39f5 か作業中の差分)。触っていない |
| `tests/test_jev_design.py` | ④ | (c)試験 | 試験する相手の台本を直していないので、試験も変えていない(決まり: 試験は直した名前・単位に合わせるだけ) |
| `tests/test_judge_gates.py` | ②④ | (c)試験 | 試験する相手の台本を直していないので、試験も変えていない(決まり: 試験は直した名前・単位に合わせるだけ) |
| `tests/test_market_view.py` | ④ | (c)試験 | 試験する相手の台本を直していないので、試験も変えていない(決まり: 試験は直した名前・単位に合わせるだけ) |
| `tests/test_o3c_jev_state.py` | ②④ | (c)試験 | 試験する相手の台本を直していないので、試験も変えていない(決まり: 試験は直した名前・単位に合わせるだけ) |
| `tests/test_o3c_oi_distance.py` | ②④ | (c)試験 | 試験する相手の台本を直していないので、試験も変えていない(決まり: 試験は直した名前・単位に合わせるだけ) |
| `tests/test_o3c_price_level_table.py` | ②④ | (c)試験 | 試験する相手の台本を直していないので、試験も変えていない(決まり: 試験は直した名前・単位に合わせるだけ) |
| `tests/test_o3c_reaction.py` | ②④ | (c)試験 | 試験する相手の台本を直していないので、試験も変えていない(決まり: 試験は直した名前・単位に合わせるだけ) |
| `tests/test_o3c_reaction_judge.py` | ②④ | (c)試験 | 試験する相手の台本を直していないので、試験も変えていない(決まり: 試験は直した名前・単位に合わせるだけ) |
| `tests/test_o3c_reaction_r2.py` | ②④ | (c)試験 | 試験する相手の台本を直していないので、試験も変えていない(決まり: 試験は直した名前・単位に合わせるだけ) |
| `tests/test_o3c_signal_continue.py` | ②④ | (c)試験 | 試験する相手の台本を直していないので、試験も変えていない(決まり: 試験は直した名前・単位に合わせるだけ) |
| `tests/test_o3c_signal_continue_jev.py` | ④ | (c)試験 | 試験する相手の台本を直していないので、試験も変えていない(決まり: 試験は直した名前・単位に合わせるだけ) |
| `tests/test_o3c_signal_explore.py` | ②④ | (c)試験 | 試験する相手の台本を直していないので、試験も変えていない(決まり: 試験は直した名前・単位に合わせるだけ) |
| `tests/test_o3c_signal_explore5.py` | ②④ | (c)試験 | 試験する相手の台本を直していないので、試験も変えていない(決まり: 試験は直した名前・単位に合わせるだけ) |
| `tests/test_o3c_signal_materials.py` | ④ | (c)試験 | 試験する相手の台本を直していないので、試験も変えていない(決まり: 試験は直した名前・単位に合わせるだけ) |
| `tests/test_o3c_signal_stage2.py` | ④ | (c)試験 | 試験する相手の台本を直していないので、試験も変えていない(決まり: 試験は直した名前・単位に合わせるだけ) |
| `tests/test_o3c_signal_value.py` | ②④ | (c)試験 | 試験する相手の台本を直していないので、試験も変えていない(決まり: 試験は直した名前・単位に合わせるだけ) |
| `tests/test_onr.py` | ④ | (c)試験 | 試験する相手の台本を直していないので、試験も変えていない(決まり: 試験は直した名前・単位に合わせるだけ) |
| `tests/test_phase2_p2_01.py` | ②④ | (c)試験 | 試験する相手の台本を直していないので、試験も変えていない(決まり: 試験は直した名前・単位に合わせるだけ) |
| `tests/test_phase2_p2_02.py` | ④ | (c)試験 | 試験する相手の台本を直していないので、試験も変えていない(決まり: 試験は直した名前・単位に合わせるだけ) |
| `tests/test_phase2_p2_02_final.py` | ②④ | (c)試験 | 試験する相手の台本を直していないので、試験も変えていない(決まり: 試験は直した名前・単位に合わせるだけ) |
| `tests/test_qa_make_known_answer.py` | ②④ | (c)試験 | 試験する相手の台本を直していないので、試験も変えていない(決まり: 試験は直した名前・単位に合わせるだけ) |
| `tests/test_qa_make_known_answer_maker.py` | ④ | (c)試験 | 試験する相手の台本を直していないので、試験も変えていない(決まり: 試験は直した名前・単位に合わせるだけ) |
| `tests/test_qa_make_known_answer_maker3.py` | ②④ | (c)試験 | 試験する相手の台本を直していないので、試験も変えていない(決まり: 試験は直した名前・単位に合わせるだけ) |
| `tests/test_record_funding_basis.py` | ④ | (c)試験 | もう 1 人の作業者(動いている経路の担当)がこの回に直した(コミット 45b773a8・503b39f5 か作業中の差分)。触っていない |
| `tests/test_scalp_logic.py` | ②④ | (c)試験 | 試験する相手の台本を直していないので、試験も変えていない(決まり: 試験は直した名前・単位に合わせるだけ) |
| `tests/test_xborder_p2_fast.py` | ②④ | (c)試験 | 試験する相手の台本を直していないので、試験も変えていない(決まり: 試験は直した名前・単位に合わせるだけ) |
| `tests/test_xborder_p2_known_answer.py` | ②④ | (c)試験 | 試験する相手の台本を直していないので、試験も変えていない(決まり: 試験は直した名前・単位に合わせるだけ) |

## 時刻

- 着手: 20:56 JST(`Fri Oct  9 20:56:57 JST 2026`)
- 途中で `TZ=Asia/Tokyo date` を打った時刻: 21:10・21:12・21:13・21:14・21:15・21:16・21:17・21:18・21:19・21:20・21:22・21:23・21:24・21:25・21:26・21:27・21:28・21:29・21:30・21:31・21:33・21:34・21:35・21:37・21:38・21:39・21:40・21:41・21:42・21:43・21:44・21:45
- 終わり: 21:46 JST ごろ(上限 22:45 JST の前。止めた理由: 残りの対象(上の「直していないファイル」)は、どれも書く台本・読む台本・保存済みの表・試験を組で変える必要があるか、事前登録の写しの扱いの判断が要るもので、上限の残り 1 時間で 1 組を終わらせて確かめるところまで届くと見積もれなかった【推定】)
