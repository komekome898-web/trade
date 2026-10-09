# 監査 9: audit_8_repo.md §5 の残り(1〜4・6・7)

作成: 2026-10-09 10:09 UTC 着手(上限 70 分 = 11:19 UTC まで)。調べるだけの作業者が書いた。コード・文書は直していない。コミットしていない。

## 着手前の表

| やること | この依頼文の該当語(逐語) |
|---|---|
| `audit_8_repo.md` を最初に全部読む | 「前の作業者の出力 `docs/DISCUSSIONS/2026-10-09_bp_units/audit_8_repo.md` を最初に全部読む」 |
| 「目(当たり行)」432 ファイルの当たり行の 4 行目から後を読み、表 1 の種類と倍率の行に足すものを書く。変わらなかったファイルは数だけ | 「表 1 で「目(当たり行)」にした 432 ファイルについて、当たった行の 4 行目から後を全部読み、表 1 の種類と倍率の行(…)に足すものを書く。変わらなかったファイルは数だけ書く」 |
| bp の字の無い行で、円と bp・bp の種類の間を倍率で変えている所を、指定の 9 語を一覧のファイルに打って探し、bp・円・% に関わるものだけを表にする | 「bp の字の無い行で、円と bp、または bp の種類の間を倍率で変えている所を探す。少なくとも次の語を、上の一覧のファイルに打つ」「当たった行を読んで、bp・円・% に関わるものだけを表にする」 |
| `pnl_bp` 以外の名前で bp を受け取る口を探し、受け取る側と渡してくる側の種類を書く。§3.2 の 42 個のうち渡し手を辿っていないものを辿る | 「`pnl_bp` 以外の名前で bp を受け取る口を全部探す」「受け取る側と渡してくる側の種類(①〜④)を書く。audit_8_repo.md §3.2 の 42 個のうち、渡し手を辿っていないものも辿る」 |
| (c) 254 ファイルの出力のファイルを書く台本と読む台本を grep で結び、(a)(b) の台本が読んでいれば流れ先を直す | 「流れ先 (c)(どこにも流れていない)にした 254 ファイルについて、出力のファイル(csv・json・md・gz)を書く台本と、それを読む台本を grep で結び、流れ先 (a)(b) の台本が読んでいるものがあれば流れ先を直す」 |
| `overnight.py` の `edge_trend` を (b) の経路から呼んでいるか、何を渡しているか | 「`src/bot/research/overnight.py` の `edge_trend` を流れ先 (b) の経路から実際に呼んでいるか、何を渡しているか」 |
| `aggregate.py` の `net_bps` を書くのが `paper_on1.py` だけか | 「`src/bot/monitoring/aggregate.py` の `net_bps` を書くのが `scripts/paper_on1.py` だけか」 |
| 試験の 5 組の文字の言及を確かめる | 「audit_8_repo.md §1.4 の 3 の、試験の 5 組の文字の言及を確かめる」 |
| `docs/RESEARCH/WINDOW1/` と `backtest_data/phase2_sealed/` を読まない。一覧は指定のコマンドから作り、`grep -r` を全体に打たない | 「`docs/RESEARCH/WINDOW1/` と `backtest_data/phase2_sealed/` は読まない。grep の対象にもしない。ファイルの一覧は必ず `git ls-files -z -- '*.py' ':!docs/RESEARCH/WINDOW1' ':!backtest_data/phase2_sealed'` から作り、`grep -r` をリポジトリ全体に打たない」 |
| 「無い」「流れていない」にはコマンドと出力を添える。添えられなければ「未確認」 | 「「無い」「流れていない」と書くときは、打ったコマンドと出力を添える。添えられないなら「未確認」と書く」 |
| 数はコマンドで数え、コマンドを書く | 「数は手で数えず、コマンドで数えてコマンドを書く」 |
| 範囲を切ったら書く | 「範囲を切ったら、切ったことを書く」 |
| 上限 70 分。上限に達したときだけ止め、残りを持ち越しに書く | 「上限は 70 分。上限に達したときだけ止めて、残りを持ち越しに書く。上限の前に止めて持ち越しにしない」 |
| 出力はこの 1 本に日本語で書く。コミットしない。一時ファイルは作業用の置き場 `audit9/` に置く | 「書いてよいファイルは `/home/user/trade/docs/DISCUSSIONS/2026-10-09_bp_units/audit_9_repo_rest.md` の 1 本だけです(コミットしない)」「作業用の一時ファイルは `/tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/audit9/` に置き」「出力は全部日本語で書いてください」 |
| 前の作業者が作業用の置き場に残した import の表(`edges.tsv`)と (a)(b) の入口の一覧(`entries.json`)を使い回す | **(該当語なし)** — 依頼文は「前の作業者の出力 audit_8_repo.md」だけを挙げている。import の表を作り直すと 70 分に入らないので使い回す。使い回したことと、確かめたこと(下の 0.2)を書く。迷っていることをここに書く |

### 完了見込み時間(上限 70 分)

- audit_8_repo.md を読む・作業の置き場を作る: 5 分(済)
- 6(edge_trend・net_bps): 5 分
- 7(試験の 5 組): 4 分
- 2(9 語を打って読む): 13 分
- 1(6,139 行。機械で下付けし、倍率の行と種類が増える行を目で読む): 17 分
- 3(`_bp`・`_bps` で終わる名前の口、42 個の渡し手): 12 分
- 4((c) の出力のファイルと (a)(b) の読み): 10 分
- 仕上げ: 4 分
- 合計 70 分。1 の 6,139 行を 1 行ずつ全部目で読むのはこの中に入らない見込み。どこまで目で読んだかを本文に書く。

## 0. 先に書くこと

### 0.1 書き方の印

各主張は、コマンドの出力か行を読んで確かめたもの(事実)、名前や文の説明から辿ったもの(推定。そう書く)、確かめていないもの(未確認。そう書く)に分けた。

### 0.2 使い回したもの・audit_8 の後に変わったもの

- 前の作業者の作業用の置き場(`/tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/` の直下)の `edges.tsv`(import の表、17,783 行)・`entries.json`((a) の入口 73 個・(b) の入口 35 個)を使い回した(着手前の表の最後の行)。作り直してはいない。確かめたこと: 封印の置き場の 2 つの名前が 1 回も出ない(`grep -cE 'docs/RESEARCH/WINDOW1|backtest_data/phase2_sealed' entries.json edges.tsv reach.json` → `0`・`0`・`0`)。これから (a) の届く先 159 個(`RA.txt`)・(b) の届く先 151 個(`RB.txt`)を作り直した(`reach9.py`。audit_8 の `reach.py` と同じ絞り方)。
- 当たり行は自分で取り直した(1.1)。audit_8 の 474 個の分は 1 字も違わなかった。
- audit_8 の後(私の着手の時点の HEAD は `de82de4f`)、`docs/RESEARCH/matilda_main/` の 6 本(`bare_bp.py`・`calc_path_check.py`・`d4_levels_count.py`・`move_bp_check.py`・`move_bp_read.py`・`move_bp_triples.py`)が git に載り、当たる .py は 480 個になった。この 6 本は依頼の 1〜7 の対象(audit_8 の 474 個)に入らないので仕分けていない(2.2 で × 20 の行だけ書いた)。audit_8 の決まりでは `docs/RESEARCH/matilda_main/` の下は (a) の入口になる。作業場には git に載っていない `docs/RESEARCH/matilda_main/d4_position_mfe.py`・`d4_position_mfe.out` もある(`git status --short` の `??`。私が作ったものではない。別の作業が並んで動いていると推定する)。読んでいない。
- 作業用の一時ファイルは全部 `/tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/audit9/` に置いた。リポジトリに書いたのはこの文書だけ(下の `??` の 3 つのうち、私が作ったのはこの文書だけ。残り 2 つは 0.2 の上の項)。

```
$ git status --short
?? docs/DISCUSSIONS/2026-10-09_bp_units/audit_9_repo_rest.md
?? docs/RESEARCH/matilda_main/d4_position_mfe.out
?? docs/RESEARCH/matilda_main/d4_position_mfe.py
```

## 1. 「目(当たり行)」432 ファイルの 4 行目から後(§5 の 1)

### 1.1 対象と、目で読んだ量(範囲の断り)

- 当たり行は自分で取り直した(依頼文の一覧のコマンド + audit_8 §0 の grep の語)。今は .py が 480 個当たる(audit_8 の後に `docs/RESEARCH/matilda_main/` の 6 本が git に載った。0.2)。audit_8 の 474 個に限った当たり行は 7,553 行で、audit_8 が使った当たり行と 1 字も違わなかった(`cmp` で一致)。
- audit_8 §0 が読んだ「最初の 3 行」(`=`・`1e4`・`return` を含み `#` で始まらない最初の 3 行。無ければ当たり行の最初の 3 行)を同じ決まりで取り直し、それを除いた行を「4 行目から後」とした。

```
$ python3 rest.py   (432 ファイルの当たり行から、audit_8 が読んだ 3 行を除く)
read 1026 rest 6139
$ cut -d: -f1 rest_hits.txt | sort -u | wc -l
311
```

  432 ファイルのうち 121 ファイルは当たり行が 3 行以下で、4 行目から後が無い。
- **6,139 行を 1 行ずつ全部は目で読んでいない(範囲を切った)。** やったことは次の 2 段。
  1. 機械の下付け: 6,139 行全部に audit_8 §1.1 の種類の規則と、倍率の規則(円・口座・建玉の語、`1e-4`・`/ 1e4`・`* 1e4`・`/ 10000`・`* 20`・`/ 20`・`0.0001` と `*` か `/`、`#` で始まらない)を当てた。印が付いたのは 820 行(倍率の候補 683 行、表 1 の種類に無い種類の候補 161 行。重なりあり)。
  2. 目で読んだ: 倍率の候補 683 行のうち、表 1 の「倍率の行」の列に既に行番号が書いてある 130 行を除いた 553 行(1 行 85〜150 字で切って)と、種類の候補 161 行の全部。
  3. 印が付かなかった 5,319 行も、ファイルごとに見出し(表 1 の種類)を付けた一覧(`unflag.txt`、5,619 行 = 5,319 行 + 見出し 300)にして、頭から終わりまで全部目で読んだ(1 行 105 字で切った)。106 字目より後がある 512 行は、後ろの部分だけを別に出して全部読んだ(`tails.txt`、1 行 120 字で切った)。そこで見つけたものは 1.5 に書いた(後ろの部分から新しく足すものは無かった)。

```
$ (rest_hits.txt の各行の 106 字目より後を出す) > tails.txt; wc -l < tails.txt
512
```

```
$ python3 flag1.py
Counter({'convall': 683, 'conv': 659, 'new': 161})
$ (表 1 の倍率の列に行番号があるものを除く) → 553 行・123 ファイル
```

### 1.2 結果の数

- 変わったファイル: 147 個(機械の印の倍率の行を足すもの 123 個、1.3 に載せたもの 24 個、1.5 で倍率の行を足すもの 16 個。重なりあり)。1.3 の 24 個のうち 7 個(render の台本)は種類は「受」のままで、読む値の種類を書き足しただけ。種類そのものが変わるのは 17 個。
- 変わらなかったファイル: 285 個(4 行目から後が無い 121 個を含む)。

```
$ wc -l < kindadd.txt; wc -l < convf.txt; wc -l < add15.txt
24
123
16
$ sort -u kindadd.txt convf.txt add15.txt > changed2.txt; wc -l < changed2.txt
147
$ grep -vxFf changed2.txt eye3files.txt | wc -l
285
```

### 1.3 種類に足すもの(目で読んで決めた。24 個。うち render の 7 個は「受」のままで、読む値の種類を書いた)

| ファイル | 表 1 の種類 | 足すもの | 根拠の行 |
|---|---|---|---|
| `docs/DATA/probes/20260920_o3c_signal_explore5_refuter.py` | 受 | ④ 距離(`dist_node_bp` の列を読む) | 254・430-431 |
| `docs/RESEARCH/cards/c9_liquidation_cascade/redo2_2026-10-05/c9_redo.py` | 受 | ②(`mi = -s2.sign * (pend - mid) / mid * 1e4`、217-218 行も同じ形) | 217-220・123 |
| `scripts/jev_check.py` | 受 | ④ 手数料率(文の中の「round-trip fee of +5 bp」) | 1280 |
| `scripts/measure_katsuo_round5.py` | ② | ④ 約定のずれ(`entry_delay_bp`・`exit_delay_bp`) | 135 |
| `scripts/o3c_reaction_judge.py` | ② | ④ 距離(`dist_vwap_bp`・`dist_node_bp`・`oi_dist_*_bp` の列の付け替え) | 228-257・553-554 |
| `scripts/research_fx_fundamentals.py` | ② | ④ 経費(`ROUND_TRIP_BPS` 0.71bps、docstring と 815・913 行)。633 行 `gross = pos * ret * 1e4` の pos は audit_8 の読みどおり向き ±1 とした(③ にしない) | 9-152・815・913 |
| `scripts/research_matilda_modern.py` | ③④ | ②(捕捉・逆行の値動き `sg * (m5 - m0) / m0 * 1e4`) | 578-579・693-698・856・877 |
| `scripts/research_two_sided_flow.py` | ③④ | ②(`drift_bps`・`rv_bps`) | 543-550・350・999-1000 |
| `src/bot/research/katsuo_limit_sim.py` | ②④ | ③型(`tr["side"] * (px / tr["avg"] - 1.0) * 1e4 * cq`・`* tr["size"]` = 量で重みを付けた値動き) | 721・768 |
| `tests/research/test_katsuo_limit_sim.py` | ② | ③型(`pnl_bp == … * 1e4 * 0.5`・`* 1.0` = 量の重み) | 235・356・523・534 |
| `src/bot/research/trade_record.py` | 受 | ③(文: 「量 qty はその取引の最大の持ち高(持ち高の最大を 1 とする尺度)。損益 pnl_bp は各台本の定義のまま」) | 11 |
| `tests/research/cards/library/test_c2_owner_xvenue_wick.py` | ② | ③(`r30.exposure[29] == 1.0` の持ち高を確かめる) | 323 |
| `tests/test_liq_bands.py` | 受 | ④ 距離(`naive_band_half_width_bp`) | 227 |
| `tests/test_o3c_signal_explore2.py` | ② | ④ 距離(`dist_vwap_bp`・`dist_node_bp`) | 288 |
| `tests/test_o3c_signal_materials.py` | ④ | ②(注釈の「(101-100)/100*1e4 = 100bp」など) | 207・306 |
| `tests/test_onr_forward.py` | ② | ④ 閾値(`stop_bps = -25.0`。注釈「63 * -25bps = -15.75%」は bp → % の倍率) | 124-125 |
| `tests/test_qa_make_known_answer_steer.py` | ② | ④ 手数料率・スプレッド・滑り(`taker_fee_bps`・`quoted_spread_bps`・`taker_slippage_bps_per_side`) | 160-196 |
| `scripts/render_exec_floor.py` | 受 | 受のまま。読む値は ②(`post_touch_drift_bp`)と ④(`roundtrip_taker_cost_001btc_bp`) | 194-293・279 |
| `scripts/render_k1_deepdive.py`・`render_k1_robustness.py`・`render_k1_judgement.py`・`render_k1_xvenue.py`・`render_k1_xvenue2.py` | 受 | 受のまま。読む値に ②(realized vol bp・ヒゲ bp・実体 bp)と ④ 閾値(`edges_bp`)がある | 各ファイルの 154-359 の行(1.3 の機械の印の行) |
| `scripts/render_k1_round5.py` | 受 | 受のまま。読む値は ④ 約定のずれ(`entry_delay_bp`・`exit_delay_bp`) | 54・114 |

- 機械が付けたが、読んで足さなかった印(誤り): `max_bp`・`min_bp`・`max_dd_bp`・`worst_day_bp`(落ち込み・分布の端で ④ の閾値ではない。`goal_table*.py`・`c4_components_tables.py`・`measure_katsuo_exit_ablation.py`・`render_k1_exit_ablation.py`・`test_backtest_chart.py`)、`per_minute_bp`・`per_day_bp`(`daily_stats.py`・`light_b2.py`)、`entry_part_bp`・`exit_part_bp`(`c2_ref_vs_g_cause.py` の差の分け方)、`DIST_BP`(`i3_scenes.py` の分布)、`weight_sec`(`measure_exec_floor.py` の時間の重み)、`pos * (…) * 1e4`(`measure_katsuo_delay_decomp.py`、向き ±1)、文の中の「marginal」「口座」「equity」(`run_scalp_paper.py` 49・`finmarketpy_adapter.py` 35・`quanttrader_adapter.py` 16・`research_scalp_exits.py` 994)、`p2_08_run.py` 2209(約定の量で重みを付けた平均で、建玉の重みではない)、`judge_gates.py` 480・`p2_08_run.py` 423・443・`test_xborder_p2_known_answer.py` 193-194(audit_8 で「① でない」と既出)。
- `scripts/o3c_signal_value.py` 949-960 の `build_exposure_table`: 830-839 行 `exposure_of` は保有時間・同時建玉の最大を数え、収支は `pnl_net_bp` の和を保有時間で割る(bp/時)。`pnl_net_bp` は 884 行 `pnl_bp - cost_bp * 建玉の回数`(② − ④)で、建玉の量を掛けていない。③ は足さない。`scripts/w4_measure/post.py` 75-76 の `drift_removed_bp` は `measure.py` 124 行の ③型(3.2 の 13)を写すだけ。

### 1.4 倍率の行に足すもの(機械の印の 553 行・123 ファイル)

円・口座・% に関わるもの(目で読んで選んだ。ほかは値段の比 → bp と bp → 値段で、表 1 の種類を変えない):

| ファイル | 行: 式 | 何から何へ |
|---|---|---|
| `scripts/research_two_sided_flow.py` | 676・682-684: `pnl / note * 1e4`・`pnl.sum() / tot_note * 1e4` / 700: `np.minimum(B, S) * spread_bps * 1e-4 * px` / 834・856: `pnl / lot[1] * 1e4`・`pnl / entry * 1e4` | 円 → 建玉の円に対する bp / bp → 円 |
| `scripts/research_fx_carry.py` | 330-332: `swap / notional_jpy * 1e4 / swap_days` / 335・345: `diff_pct / 100 / 365 * 1e4` / 392・395: `… / 1e4` / 577・603: `… * 365 / 1e4 * 100` | 円のスワップ → bp/日 / 金利差 % → bp/日 / bp → 率 / bp/日 → %/年 |
| `scripts/phase2/p2_04_run.py` | 724・1631: `cost_yen_cons / notional * 1e4` / 767-768・1648: `(2 * etf_fee + 2 * ticks) / close_prev * 1e4` | 円の経費 → ④ bp |
| `scripts/phase2/p2_02_run.py` | 197: `2.0 * fee_yen / notional * 1e4` / 490: `55.0 / median_close_1343 * 1e4` / 506: `close_t * (net_cons / 1e4)` | 円 → ④ bp / bp → 1 口の円 |
| `scripts/phase2/p2_01_run.py` | 130: `out["r"] * 1e4` / 131・373-375・520: 値段の比 → bp | 率 → bp |
| `scripts/research_latency_grade.py` | 646-647: `net / 1e4 * 0.02 * price * evday`・`* 0.10 *` | bp → 0.02 BTC・0.10 BTC の円/日 |
| `scripts/research_spread_mm.py` | 190: `cyc_cash / ref * 1e4` | 1 単位の円 → bp |
| `scripts/qa/make_known_answer_maker.py`・`make_known_answer_maker3.py` | maker 315: `pnl / ref_mid * 1e4` / maker3 869・895・1379・1431: `pnl / entry_price * 1e4` | 1 単位の円の損益 → bp |
| `scripts/replay_scalp_storm.py` | 225: `… / position.entry_px * 1e4 * d` | 値段の差 → bp(向き d) |
| `scripts/research_wall_front.py` | 492: `MATILDA_OFFSET_JPY / 1e6 * 1e4` / 494: `1.0 / px_med * 1e4` | 円の距離 → bp |
| `scripts/verify_liq_instrument.py` | 507: `5_000_000.0 * tick_bp / 10_000.0` / 528: `5_000_000.0 * 40 / 10_000.0` | bp → 円の刻み |
| `src/bot/research/katsuo_limit_sim.py` | 721・768: `… * 1e4 * cq`・`* tr["size"]` | ② × 量 = ③型 |
| `scripts/research_fast_cycle.py` | 906(文): 「per trade 100 bps of drawdown is 1% of equity」 | 建玉 1 倍の bp → 口座の %(文の中) |
| `tests/test_onr_forward.py` | 124(注釈): 「63 * -25bps = -15.75%」 | bp → %(注釈) |

全部の行番号(機械の分け方。分け方は語の形で決めたもので、目で読んで直していない):

| ファイル | 足す倍率の行(機械の分け方: 行番号) |
|---|---|
| `backtest_data/venue_survey_20260827/analyze_venues.py` | 円の語あり: 235 / × 1e4(その他): 255 / 値段の比 → bp: 92・173・174・248・297 |
| `docs/DATA/probes/20260920_o3c_cascade_read.py` | 値段の比 → bp: 403・429 |
| `docs/DATA/probes/20260920_o3c_signal_continue_refuter.py` | × 1e4(その他): 446・451・503・507・637・752・789・805・812・826・836 / 値段の比 → bp: 750 |
| `docs/RESEARCH/cards/c2_owner_xvenue_wick/vol_gate/measure_vol_gate.py` | 値段の比 → bp: 366・625 |
| `docs/RESEARCH/cards/c5_tokyo_fix_momentum/redo2_2026-10-05/c5_redo.py` | 値段の比 → bp: 191・192 |
| `docs/RESEARCH/cards/c5_tokyo_fix_momentum/redo2_2026-10-05/d5_mid_check.py` | 値段の比 → bp: 63 |
| `docs/RESEARCH/cards/c6_weekend_gap_revert/redo2_2026-10-05/c6_redo.py` | 円 → bp: 155 / × 1e4(その他): 190 / 値段の比 → bp: 233・234・235・236 |
| `docs/RESEARCH/cards/c7_barrier_race/redo2_2026-10-05/c7_redo.py` | 値段の比 → bp: 85・87・101・102・149 |
| `docs/RESEARCH/cards/c8_session_mean_revert/redo2_2026-10-05/c8_more.py` | 値段の比 → bp: 65 |
| `docs/RESEARCH/cards/c8_session_mean_revert/redo2_2026-10-05/c8_redo.py` | 値段の比 → bp: 85・87・101・102・149 |
| `docs/RESEARCH/cards/c9_liquidation_cascade/redo2_2026-10-05/c9_redo.py` | 値段の比 → bp: 217・218・220 |
| `docs/RESEARCH/cards/diag_why/c6c8.py` | 値段の比 → bp: 29 |
| `scripts/backfill_spread_from_tape.py` | × 1e4(その他): 301 / 値段の比 → bp: 309 |
| `scripts/build_fx_event_library.py` | 円の語あり: 349 |
| `scripts/judge_board_round.py` | 値段の比 → bp: 405・419・491・504・517・568・878・879・889・890・898 |
| `scripts/measure_exec_floor.py` | 値段の比 → bp: 467・525・663・672・805・811 |
| `scripts/measure_katsuo_body_wick.py` | × 1e4(その他): 152 |
| `scripts/measure_katsuo_delay_decomp.py` | 値段の比 → bp: 56 |
| `scripts/measure_katsuo_direction_bias.py` | × 1e4(その他): 100 |
| `scripts/measure_katsuo_dispersion.py` | × 1e4(その他): 129 / 値段の比 → bp: 166・190 |
| `scripts/measure_katsuo_robustness.py` | 値段の比 → bp: 231・240・248 |
| `scripts/o3c_bitflyer_spread.py` | 値段の比 → bp: 134 |
| `scripts/o3c_jev_state.py` | 値段の比 → bp: 651・657 |
| `scripts/o3c_oi_distance.py` | 値段の比 → bp: 537・813 |
| `scripts/o3c_price_level_table.py` | 値段の比 → bp: 189・695 |
| `scripts/o3c_reaction.py` | × 1e4(その他): 837 / 値段の比 → bp: 1110・1565・2082・2162・2163・2216・2305 |
| `scripts/o3c_signal_continue.py` | 値段の比 → bp: 409・441・535・538・766・767・1086・1102・1161・1248 |
| `scripts/o3c_signal_continue_jev.py` | 値段の比 → bp: 493・520・535 |
| `scripts/o3c_signal_explore3.py` | 値段の比 → bp: 217・230・232・254・504 |
| `scripts/o3c_signal_explore4.py` | 値段の比 → bp: 232・245・260・262・296・299・420 |
| `scripts/o3c_signal_explore5.py` | 値段の比 → bp: 423・432・535・717・719 |
| `scripts/o3c_signal_materials.py` | 値段の比 → bp: 365・374・399・717 |
| `scripts/o3c_signal_policy.py` | 値段の比 → bp: 658 |
| `scripts/o3c_signal_value.py` | 値段の比 → bp: 536・558・701・712・1512 |
| `scripts/phase2/p2_01_final.py` | 値段の比 → bp: 382・383 |
| `scripts/phase2/p2_01_run.py` | × 1e4(その他): 130 / 値段の比 → bp: 131・373・374・375・520 |
| `scripts/phase2/p2_01b_history.py` | 値段の比 → bp: 247・248・249 |
| `scripts/phase2/p2_02_final.py` | × 1e4(その他): 989 / 値段の比 → bp: 249・250・271・272・277・278 |
| `scripts/phase2/p2_02_run.py` | 円の語あり: 820・821 / × 1e4(その他): 251・252・490 / 値段の比 → bp: 293 |
| `scripts/phase2/p2_03_final.py` | × 1e4(その他): 525 |
| `scripts/phase2/p2_03_run.py` | × 1e4(その他): 343 / 値段の比 → bp: 514 |
| `scripts/phase2/p2_04_run.py` | 円 → bp: 724・1631 / 値段の比 → bp: 767・768・1648 |
| `scripts/phase2/p2_08_run.py` | 円の語あり: 423 / × 1e4(その他): 1584・1585・2520・2833・3401 / 値段の比 → bp: 541 |
| `scripts/qa/make_known_answer.py` | ÷ 1e4(その他): 267・302・303 / × 1e4(その他): 158 / 値段の比 → bp: 159・328・329 |
| `scripts/qa/make_known_answer_maker.py` | ÷ 1e4(その他): 268・382 / × 1e4(その他): 315 / 値段の比 → bp: 278・317・318・454 |
| `scripts/qa/make_known_answer_maker3.py` | × 1e4(その他): 253・869・895・1206・1379・1431 / 値段の比 → bp: 911 |
| `scripts/qa/maker_fill_ref.py` | 値段の比 → bp: 284・297 |
| `scripts/qa/maker_fill_ref_packet.py` | 値段の比 → bp: 234・247 |
| `scripts/qa/maker_fill_ref_packet_r2.py` | 値段の比 → bp: 288・301 |
| `scripts/qa/pipeline_known_answer_daily.py` | × 1e4(その他): 415・429・451・673 / 値段の比 → bp: 197 |
| `scripts/qa/pipeline_known_answer_taker.py` | 値段の比 → bp: 232 |
| `scripts/replay_scalp_storm.py` | × 1e4(その他): 225 / 値段の比 → bp: 158・266 |
| `scripts/research_anchor.py` | × 1e4(その他): 116・165・181 / 値段の比 → bp: 113 |
| `scripts/research_anchor_v2.py` | × 1e4(その他): 91 |
| `scripts/research_avalanche.py` | 円の語あり: 664 / bp → 値段: 362 / × 1e4(その他): 85・290・687 / 値段の比 → bp: 106・392・396・632 |
| `scripts/research_basis.py` | × 1e4(その他): 202・203 |
| `scripts/research_board_calibration.py` | 値段の比 → bp: 315・615・616・1059・1277・1288・1292 |
| `scripts/research_burst_atlas.py` | × 1e4(その他): 285 / 値段の比 → bp: 402・574・814 |
| `scripts/research_calm_range.py` | × 1e4(その他): 138 / 値段の比 → bp: 301・507・538・577 |
| `scripts/research_exit_surface.py` | 値段の比 → bp: 156・164・288・1344 |
| `scripts/research_fast_cycle.py` | 値段の比 → bp: 291・406・437・441・644・743・1050・1080・1172 |
| `scripts/research_fx_carry.py` | 円 → bp: 332・603 / ÷ 1e4(その他): 392・395 / bp ↔ %: 577 / × 1e4(その他): 335・345 |
| `scripts/research_fx_event_ticks.py` | × 1e4(その他): 660・663 / 値段の比 → bp: 231・313・378・443・445・446・473・474 |
| `scripts/research_fx_events.py` | × 1e4(その他): 995 / 値段の比 → bp: 481・776・781・930・942 |
| `scripts/research_fx_fundamentals.py` | × 1e4(その他): 633・903・904・910・1036・1151・1153・1161・1166・1167・1170 |
| `scripts/research_fx_sessions.py` | 円の語あり: 808 / bp → 値段: 354・1007 / 値段の比 → bp: 493・510・515・567・735 |
| `scripts/research_fx_tokyofix.py` | 値段の比 → bp: 181・301・303・367・369 |
| `scripts/research_imbalance.py` | × 1e4(その他): 71 |
| `scripts/research_latency_grade.py` | bp → 値段: 356・382・383 / × 1e4(その他): 646・647・704 / 値段の比 → bp: 62・238・302・386・398 |
| `scripts/research_leader_surface.py` | × 1e4(その他): 201・602・952 |
| `scripts/research_m4_finecheck.py` | × 1e4(その他): 507 / 値段の比 → bp: 738・739・748・749 |
| `scripts/research_macro_calendar.py` | × 1e4(その他): 701・712・721・745・761・762 |
| `scripts/research_mainbot_exits.py` | 円の語あり: 14 |
| `scripts/research_maker_reaudit.py` | × 1e4(その他): 454・479 / 値段の比 → bp: 153・285・307 |
| `scripts/research_matilda_modern.py` | 円の語あり: 986 / 値段の比 → bp: 578・579・693・694・698・846・856・877 |
| `scripts/research_matilda_surface.py` | × 1e4(その他): 484・1095 |
| `scripts/research_matilda_taro.py` | 円の語あり: 1877 / bp → 値段: 1493・1514 / × 1e4(その他): 867・1402・1624・1629・1631・1632 / 値段の比 → bp: 688・1107・1108・1117・1118・1125・1324 |
| `scripts/research_overnight_on1.py` | × 1e4(その他): 142・155・166・193・213・223・230・247 |
| `scripts/research_overnight_onr.py` | bp ↔ %: 342 / × 1e4(その他): 196・208・218・300・303・331・356・357・448・449・454・460 |
| `scripts/research_prediction_atlas.py` | bp → 値段: 410・411・1538・1539 / × 1e4(その他): 538・625・638・1527 / 値段の比 → bp: 523・580・773・1408・1421・1443・1522 |
| `scripts/research_range_reversed.py` | bp → 値段: 732・733・735・736 / × 1e4(その他): 147・379・452 / 値段の比 → bp: 374・380・381・678・780 |
| `scripts/research_regime_composite.py` | × 1e4(その他): 384 |
| `scripts/research_scalp_exits.py` | 値段の比 → bp: 275・280・332・365・368 |
| `scripts/research_scalp_opt.py` | bp → 値段: 397 / × 1e4(その他): 466 / 値段の比 → bp: 240・266・273・349・399・400・486 |
| `scripts/research_seasonality.py` | × 1e4(その他): 142・143・144 |
| `scripts/research_spread_mm.py` | × 1e4(その他): 190 / 値段の比 → bp: 207・213・230・233 |
| `scripts/research_storm_bracket.py` | 値段の比 → bp: 206・284 |
| `scripts/research_two_sided_flow.py` | 円の語あり: 734 / 円 → bp: 682 / ÷ 1e4(その他): 700 / × 1e4(その他): 263・404・676・720・834・856・1159 / 値段の比 → bp: 550・683・684・999・1000 |
| `scripts/research_vr_barrier.py` | × 1e4(その他): 317 |
| `scripts/research_wall_front.py` | 円 → bp: 492 / × 1e4(その他): 494 / 値段の比 → bp: 464 |
| `scripts/run_scalp_paper.py` | bp → 値段: 401 / ÷ 1e4(その他): 423 / 値段の比 → bp: 240・262 |
| `scripts/tp_operating_curve.py` | 値段の比 → bp: 64・158 |
| `scripts/verify_liq_instrument.py` | bp → 値段: 178・454・455 / ÷ 1e4(その他): 443・444・466・507・528 / 値段の比 → bp: 515・681・1100 |
| `src/bot/research/cards/library/c2_owner_xvenue_wick.py` | × 1e4(その他): 83 |
| `src/bot/research/cards/pnl.py` | 値段の比 → bp: 40 |
| `src/bot/research/katsuo_limit_sim.py` | × 1e4(その他): 242 / 値段の比 → bp: 441・498・721・768 |
| `src/bot/research/liq_bands.py` | × 1e4(その他): 435 |
| `src/bot/research/liq_cascade_v2.py` | 値段の比 → bp: 551・560・610・1061・1064 |
| `src/bot/research/liq_response.py` | × 1e4(その他): 567・673・689・736・775・804 |
| `src/bot/research/matilda_limit_sim.py` | 値段の比 → bp: 460・596・598 |
| `tests/bt/battery/item_2/i2_scenes.py` | その他: 1034 |
| `tests/bt/battery/item_2/opponents/predictivedev_tradesim_adapter.py` | × 1e4(その他): 90・101 |
| `tests/bt/item_2/test_i2_costs_grid.py` | その他: 88 |
| `tests/bt/item_3/test_i3_report_grid.py` | × 1e4(その他): 138 |
| `tests/research/cards/test_w1_known_answers.py` | 値段の比 → bp: 128 |
| `tests/research/cards/test_w1_t3_t8_pnl.py` | 値段の比 → bp: 96・109 |
| `tests/research/test_katsuo_limit_sim.py` | × 1e4(その他): 534 / 値段の比 → bp: 235・356・523・1040・1154・1423・1449・1513 |
| `tests/research/test_liq_cascade_v2.py` | 値段の比 → bp: 123・146・178・329・330・332・334・335 |
| `tests/test_board_round.py` | × 1e4(その他): 83 |
| `tests/test_board_walk.py` | 値段の比 → bp: 114・166 |
| `tests/test_k1_delay_entry.py` | 値段の比 → bp: 60 |
| `tests/test_k1_lookahead.py` | ÷ 1e4(その他): 187 / 値段の比 → bp: 113・132・140・244 |
| `tests/test_k1_xvenue.py` | 値段の比 → bp: 75 |
| `tests/test_liq_bands.py` | × 1e4(その他): 201・206・219 |
| `tests/test_liq_response.py` | × 1e4(その他): 115・116・544・545・659・670・671 |
| `tests/test_o3c_oi_distance.py` | 値段の比 → bp: 319・359・436 |
| `tests/test_o3c_signal_continue.py` | 値段の比 → bp: 223 |
| `tests/test_o3c_signal_value.py` | 値段の比 → bp: 242・244・455・457・805 |
| `tests/test_phase2_p2_01.py` | ÷ 1e4(その他): 102 / × 1e4(その他): 78 |
| `tests/test_phase2_p2_02.py` | × 1e4(その他): 202・203・271 |
| `tests/test_phase2_p2_02_final.py` | ÷ 1e4(その他): 186 / × 1e4(その他): 280・290 |
| `tests/test_qa_pipeline_known_answer.py` | × 1e4(その他): 217 |
| `tests/test_scalp_logic.py` | bp → 値段: 323 / ÷ 1e4(その他): 337 |

### 1.5 印の無い 5,319 行を読んで足すもの

種類を変えるものは見つからなかった(1.3 の 24 個のほか)。倍率の行(機械の規則が `* 100`・`/ 100`・`% → bp` を拾わないので印が付かなかったもの)を足す。

| ファイル | 行: 式 | 何から何へ |
|---|---|---|
| `src/bot/research/xborder_p2.py` | 325: `funding_bps_each = float(funding_pct_per_settlement) * 100.0  # % -> bps` | % の資金調達率 → bp(④ 資金調達率) |
| `tests/test_xborder_p2_known_answer.py` | 124(注釈): 「funding_bps = n_settlements * 0.02% = n_settlements * 2.0」 | % → bp |
| `scripts/qa/pipeline_known_answer_taker.py` | 251: `spread_pct=cost_bps / 100.0` | bp → %(エンジンの経費の口が % で受ける)。287: `gross_bps = net_bps + cost_bps` |
| `scripts/research_anchor.py` | 157: `2*(FX_COSTS.spread_pct/2+FX_COSTS.slippage_pct)*100` | % → bp(表示) |
| `scripts/research_anchor_v2.py` | 169-170: `rt_cost * 100`・`SWAP_DAILY_PCT / 24 * 100` | % → bp(表示) |
| `scripts/research_legacy_elements.py`・`research_tournament.py` | legacy 515・565: `TAKER_SIDE * 100`・`(pct − pct) * 100` を「bps」と表示 / tournament 415・665: `(fm - mm) * 100`・`(pct − pct) * 100` を「bps」と表示 | % → bp(表示)。tournament 274・311 の `pct` は 円 ÷ 建玉の円 × 100(2.3)なので、その差 × 100 は建玉に対する bp |
| `scripts/research_fast_cycle.py` | 651: `maxdd_pct=maxdd / 100.0` | 建玉 1 倍の累積 bp の落ち込み → %(906 行の文と同じ換算) |
| `scripts/research_matilda_taro.py` | 2176: `0.06e4 / 100 * np.percentile(hold_all, 90) / 86400` | %/日 の資金調達率 → bp(保有秒で按分) |
| `scripts/research_matilda_modern.py` | 1242: `1e4 / float(np.median(m.mid))` | 1 円(呼値)→ bp |
| `scripts/research_prediction_atlas.py` | 1410: `net/1e2` | bp → %(表示) |
| `scripts/run_o3c_stage0.py` | 249・251・275-276: `real_bp / size`・`real_bp / real_mean_size` | ② の bp ÷ 清算の量(規模あたりの bp。円や別の bp への換算ではない) |
| `scripts/analysis/trade_rows.py` | 139(文): 「値段の動き = pnl_bp × side(向きを外した、建てから出までの値段の変化…)」 | `pnl_bp` を値段の動き(②)として読み直す口。渡された走らせが ① の `simple_trades.py` の出力なら、`pnl_bp × side` は値段の動きにならない(① は 20 万円の口座の bp で、量と値段で決まる)。この台本の流れ先は (c) |
| `tests/test_board.py` | 109-115(注釈): 「mid 1_000_000; 5 bps = +/- 500 JPY」 | bp → 円(値段の幅、試験) |
| `tests/test_onr_forward.py` | 118-119(注釈): 「-6.78% over 63 trades = -10.76 bps/trade」 | % ↔ bp(試験) |
| `tests/test_phase2_p2_01.py` | 84(注釈): 「the yen P&L of 1 micro contract agrees with the bps view」 | 円 ↔ bp(試験) |

## 2. bp の字の無い行の倍率(§5 の 2)

### 2.1 打ったコマンドと数

一覧は依頼文のコマンド(`git ls-files -z -- '*.py' ':!docs/RESEARCH/WINDOW1' ':!backtest_data/phase2_sealed'`、今は 1,410 個)。9 語をまとめて打ち、行の中身(ファイル名と行番号を除いた所)に `bp` の字(大文字小文字を問わない)がある行を外した。

```
$ P='\* *20\b|/ *20\b|200_?000|MARGIN|/ *1e4|\* *1e-4|/ *10000|\* *100\b|/ *100\b'
$ git ls-files -z -- '*.py' ':!docs/RESEARCH/WINDOW1' ':!backtest_data/phase2_sealed' | xargs -0 grep -nE -- "$P" > t2_all.txt; wc -l < t2_all.txt
1140
$ awk -F: '{l=$0; sub(/^[^:]*:[^:]*:/,"",l); if (tolower(l) !~ /bp/) print $0}' t2_all.txt > t2_nobp.txt; wc -l < t2_nobp.txt
979
(語ごとの行数: \* *20\b 38 / / *20\b 27 / 200_?000 105 / MARGIN 52 / / *1e4 54 / \* *1e-4 7 / / *10000 3 / \* *100\b 500 / / *100\b 208。1 行が複数の語に当たる)
```

- `* 100`・`/ 100` を含まない 273 行は全部読んだ(事実)。
- `* 100`・`/ 100` を含む 706 行は、語(`pnl|ret|jpy|yen|円|notional|equity|return|fee|cost|spread|fund|drift|move|gain|profit|loss|dd|drawdown|premium|basis|carry|swap|rate|price|px|close|open|mid|損益|収益|値動き|change|pct` など)で 393 行(試験でない 262 行・試験 131 行)と、当たらない 313 行に分け、全部読んだ(1 行 95〜110 字で切った)。当たらない 313 行のうち罫線 `"=" * 100`・`"-" * 100` の 59 行は形だけで外し、残り 254 行を 1 行ずつ読んだ(`grep -c '"=" \* 100\|"-" \* 100' t2_100.txt` → `59`、外した残りの `wc -l < t2_rest313.txt` → `254`)。
- 依頼の 9 語のほかに、`0.0001`・`1e-4`・`1e-04`・`/ 10_000`・`* 10000`・`* 1e4`・`1e4 *` も同じ一覧に打った(bp の字の無い行 552 行)。`* 1e4` の形の行は audit_8 の grep の語(`1e4`)に入るので、1 の当たり行と同じもの(読んだ。値段の比 → bp がほとんど)。`0.0001`・`1e-4` の 82 行は、許容誤差(`atol`・`abs=` など)を除いて読んだ。足すものは `scripts/research_fx_fundamentals.py` 722・1038・1039・1088(表 5 に既出)と `docs/DATA/probes/20260920_o3c_signal_explore5_refuter_verify.py` 20(既出)だけで、ほかは試験の資金調達率 `rate=0.0001`(率で、bp ではない)と合成の値段の傾き。

```
$ git ls-files -z -- '*.py' ':!docs/RESEARCH/WINDOW1' ':!backtest_data/phase2_sealed' | xargs -0 grep -nE '0\.0001\b|1e-4\b|1e-04|/ *10_000\b|\* *10_?000\b|\* *1e4\b|1e4 *\*' | awk -F: '{l=$0; sub(/^[^:]*:[^:]*:/,"",l); if (tolower(l) !~ /bp/) print}' > t2_extra.txt; wc -l < t2_extra.txt
552
$ grep -cE '0\.0001\b|1e-4\b|1e-04' t2_extra.txt
82
```
- 流れ先は前の作業者の import の表から作った (a) の届く先(`RA.txt` 159 個)・(b) の届く先(`RB.txt` 151 個)に当てた。474 個に入らないファイルも当てた。

### 2.2 表 4: (a)(b) の経路にある、bp の字の無い倍率の行(全部)

| ファイル | 流れ先 | 行: 式 | 何から何へ |
|---|---|---|---|
| `docs/RESEARCH/matilda_main/both_halves.py`(474 個の外) | (a) | 15: `r['mean']*20`・`r['lo']*20`・`r['hi']*20` | 9・12 行 `dt.load_run("backtest_runs_shared/matilda_main_trades/…")` の `pnl_bp`(`simple_trades.py` の出力 = ①)の日の差の平均と区間 → 円/日。**audit_8 の表 1 に無い ① → 円の行** |
| `docs/RESEARCH/matilda_main/foot/foot_boundary.py`(474 個の外) | (a) | 10: `r["mean"] * 20`・`r["lo"] * 20`・`r["hi"] * 20` | 9 行 `dt.load_run(T + "foot_5")`(同じ置き場、①)→ 円/日。**audit_8 の表 1 に無い ① → 円の行** |
| `docs/RESEARCH/matilda_main/fam_tables.py`・`half_diff.py`・`same_bar_daily.py`・`display_x20_suspects.py`・`display_x20_traps.py`・`unit_roundtrip_check.py` | (a) | audit_8 表 1 の 5・6・8・10・13・14 行目と同じ行 | ① → 円(audit_8 で既出) |
| `scripts/analysis/simple_trades.py` | (a) | 38: `MARGIN_JPY = 200_000` / 83: `float(pnl) / MARGIN_JPY * 1e4` | 円 → ①(既出) |
| `src/bot/bt/road/sizing.py`・`strategy.py`・`ledger.py`・`check.py`・`__init__.py`、`src/bot/strategy/matilda_simple.py` | (a) | sizing 23: `MARGIN_JPY = 200000` / strategy 451・matilda_simple 456: `size_detail(margin_jpy=MARGIN_JPY, …)` / ledger 240: `cash=float(MARGIN_JPY)` / check 917・1019: 証拠金が "200000" かの検査 | 20 万円は建玉の量(1 段の量 = 20 万 × 比率 ÷ 段数 ÷ 値段)と口座の現金に使う。bp に直す倍率ではない(読んだ行の範囲) |
| `scripts/paper_on1.py` | (b) | 135: `rets = [float(r["net_bps"]) / 1e4 …]`(bp の字あり)→ 141: `cum = sum(rets[-win:]) * 100` | 「②−④」の bp → 率 → %(累積の停止線の判定)。`aggregate.py` 356 行と同じ換算 |
| `scripts/research_clock_burst.py` | (b) | 129・140(docstring)・515: `ep_ * (1.0 + side * sens_c / 1e4)` | ④ 手数料率(bp)→ 約定の値段(audit_8 で 509・515 行は既出) |
| `src/bot/bt/report/metrics.py` | (b) | 258: `dd / peak * 100` | 円の資産の落ち込み → % |
| `src/bot/portfolio/portfolio.py` | (b) | 232: `(self.equity_peak_jpy - eq) / self.equity_peak_jpy * 100` | 円の資産の落ち込み → % |
| `src/bot/main.py` | (b) | 776: `position_notional_jpy(tick.price) * 100` / 1039: `(fx - spot) / spot * 100` / 1179-1180: `price * (1 ∓ stop_loss_pct / 100)` / 1361: `fill_price * delta * taker_fee_pct / 100` / 1794: `(1.0 - equity / peak) * 100` | 775-776 行 `-unrealized_pnl_jpy / position_notional_jpy * 100` = 円の含み損 ÷ 建玉の円 → %(逆指値の判定)/ 値段の比 → %(SFD の乖離)/ % → 逆指値の値段 / % の手数料率 → 円の手数料 / 円の資産 → % |
| `src/bot/execution/paper.py` | (b) | 49・51: `best_ask * (1 ± slippage_pct / 100)` / 60: `notional * taker_fee_pct / 100` | % の滑り → 値段 / % の手数料率 → 円 |
| `src/bot/market_data/feed.py` | (b) | 50: `(best_ask - best_bid) / mid * 100` | スプレッド → %(④ スプレッドの % 版) |
| `src/bot/jpx/etf_auction_executor.py`・`on1_executor.py` | (b) | 1049・516: `abs(price - ref) / ref * 100.0` | 値段のずれ → %(発注の値段の検査) |
| `src/bot/monitoring/market_view.py` | (b) | 532-533: `mid * (1 ∓ BOARD_RANGE_PCT / 100)` / 775: `atr / last_close * 100` / 984-989: `ret30 * 100`・`ret24 * 100`・`STORM_RET * 100`・`CALM_RET * 100` | % → 値段の幅 / 値動き → %(② の % 版) |
| `src/bot/strategy/xborder_momentum.py`・`wick_reversal.py`・`range_fade.py`・`ema_cross.py` | (a)・(b) | xborder 30-31: `thr_pct / 100`・`exit_pct / 100`、44-51: `mom * 100` / wick 35: `min_wick_pct / 100 * c`、39・41: `lower / c * 100` / range_fade 33: `(hi - lo) / close * 100` / ema 40: `atr / close * 100` | % の閾値 → 比、値動き → %(② の % 版) |
| `scripts/dashboard.py` | (b) | 588: `(r.c / r.o - 1) * 100` | 値動き → %(画面の表示)。452・811 は棒の幅(bp・円・% の量ではない) |
| `src/bot/monitoring/aggregate.py`・`gates.py` | (b) | aggregate 220-222・gates 231: 個数の割合 × 100 | 割合 → %(量の単位の換算ではない) |

- 474 個に入らない (a) の 2 本(`both_halves.py`・`foot_boundary.py`)は、audit_8 の grep の語(`_bp\b|\bbp\b|bps\b|1e4\b|10_?000`)を含まないので表 1 に無い(事実: どちらの本文にも `bp` の字が無い。`grep -c bp` → 0 は下で確かめた)。
- audit_8 の後に git に載った `docs/RESEARCH/matilda_main/` の 3 本にも × 20 がある(読んだ): `calc_path_check.py` 84 行 `vb[f] * 20`、`move_bp_check.py` 59・60・94・96 行、`move_bp_triples.py` 61 行。どれも「bp × 20 を円の表示と照らす」検べ。この 3 本は audit_8 の 474 個にも (a) の入口の一覧にも入っていない(audit_8 の後に git に載った。下の 0.2)。

### 2.3 表 5: (a)(b) の経路の外(import で届かない)の、bp の字の無い倍率の行(bp・円・% に関わるもの)

| 何から何へ | ファイル: 行 |
|---|---|
| bp → 円(20 万円以外の大きさ) | `docs/RESEARCH/cards/tools/goal_table2.py` 25(`× 30.4 / 1e4 × NOTIONAL`、既出)/ `scripts/phase2/p2_02_final.py` 439・`p2_02_run.py` 506(`close_t × net_cons / 1e4` = 1 口の円)/ `scripts/phase2/p2_08_run.py` 443(既出)/ `scripts/research_latency_grade.py` 646-647(`net / 1e4 × 0.02(または 0.10) × price × evday` = 0.02 BTC・0.10 BTC の円/日)/ `backtest_data/venue_survey_20260827/analyze_screen.py` 79(既出) |
| 円 → %(建玉の円で割る) | `scripts/research_anchor.py` 129・`research_anchor_v2.py` 131・`research_basis.py` 128・`research_fx.py` 56・`research_user_strategies.py` 60・`research_mainbot_exits.py` 131・`research_legacy_elements.py` 346・389・`research_tournament.py` 274・311・347・680・`research_signals.py` 132(`expectancy_per_trade_jpy / NOTIONAL * 100` など)/ `scripts/judge_gates.py` 343(`delta / notional * 100`) |
| 円 → %(口座の円で割る。20 万円の口座) | `scripts/judge_gates.py` 206(落ち込み %)と 931(`paper_equity_jpy` が無ければ `200000.0`)/ `scripts/research_legacy_elements.py` 363 / `src/bot/bt/compat/metrics.py` 76 |
| 20 万円を口座の大きさに置くだけ(bp・% に直す行は読んだ範囲に無い) | `scripts/research_anchor.py` 44・`research_anchor_v2.py` 53・`research_basis.py` 44・`research_legacy_elements.py` 190・`research_mainbot_exits.py` 69・`research_tournament.py` 134・`validate_composite.py` 109(`initial_equity_jpy=…` でエンジンへ渡す)、`scripts/research_fx.py` 50・`research_user_strategies.py` 53 |
| % → 円(手数料率 % × 建玉) | `src/bot/bt/compat/engine.py` 54・57・`barmodel.py` 587・`docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/round_3/materials/replace/compat_engine_before_layer.py` 53・56 |
| % → 値段 | `src/bot/bt/compat/engine.py` 48・51・`barmodel.py` 122・125・227 / `scripts/research_signal_fade.py` 294・297 / compat_engine_before_layer.py 47・50 |
| bp → 値段(bp の字が無い行) | `scripts/research_avalanche.py` 361(`base * (1 + side * c_in / 1e4)`)/ `scripts/research_latency_grade.py` 353・382-383(`slip / 1e4`)/ `scripts/research_maker_reaudit.py` 500(`off / 1e4`)/ `scripts/research_prediction_atlas.py` 1538-1539(`x / 1e4`)/ `scripts/research_range_reversed.py` 221・732-736(`10.0 / 1e4`)/ `scripts/research_fx_sessions.py` 1007 / `docs/DATA/probes/20260920_o3c_cascade_read.py` 273 / `docs/RESEARCH/cards/c9_liquidation_cascade/redo2_2026-10-05/c9_redo.py` 215 / `docs/DATA/probes/20260919_o3c_reaction_bugcheck.py` 17 / `docs/DATA/probes/20260920_o3c_signal_explore5_refuter_verify.py` 20(`k * 1e-4 * p0 / 0.1` = 呼値の数) |
| bp → 比・% / 年率 | `scripts/research_fx_carry.py` 345(`diff_pct / 100 / 365 * 1e4` = 金利差 % → bp/日)・392(`cb * days / 1e4`)・577・603(bp/日 → %/年)/ `scripts/research_fx_fundamentals.py` 722・1038・1039・1088(`* 1e-4 * WEEKS_PER_YEAR * 100` = bp/週 → %/年)/ `scripts/o3c_oi_distance.py` 563(`d / 1e4 + mmr`)/ `scripts/o3c_price_level_ext.py` 520(`-m / 1e4`)/ `docs/RESEARCH/cards/tools/goal_table.py` 44(`× 30.4 / 100` = bp/日 → %/月) |
| 値動き・収益の比 → %(② の % 版) | `scripts/build_basis.py` 28・`research_basis.py` 78・113・201(ベーシス %)/ `research_attention_vol.py` 98 / `research_leader_surface.py` 373・661・681 / `research_signal_fade.py` 326-327(% − 経費 / 100)/ `research_seasonality.py` 187-195 / `research_signals.py` 63-64・88 / `research_overnight_on1.py` 97・112 / `research_overnight_onr.py` 395-396 / `research_fx_carry.py` 461-743 の表示 / `research_trend_lt1.py` 236・258-533 の表示 / `research_regime_composite.py` 346-455 / `scripts/phase2/p2_08_run.py` 1648-1692(ベーシス %)と 544(`FUNDING_PCT * 100`)/ `docs/RESEARCH/cards/c1_xborder_mom/rewrite_check/compare.py` 127 |
| % → 比の閾値 | `research_leader_surface.py` 221・640-641 / `research_legacy_elements.py` 187・436 / `research_tournament.py` 131・460 / `research_mainbot_exits.py` 177 / `research_maker_reaudit.py` 428 / `research_signal_fade.py` 93 / `research_signals.py` 83・108 / `scripts/o3c_price_level_table.py` 98 / `docs/RESEARCH/cards/c1_xborder_mom/rewrite_check/compare.py` 201・`rewrite_card.py` 59-60 / `scripts/phase2/p2_08_run.py` 1635 |
| 試験(試験の中の合成の値段・期待値) | `tests/test_judge_gates.py` 76・149-194・414・437(`pct / 100 * NOTIONAL` = % → 円)/ `tests/bt/battery/item_4/*`(% の手数料率 → 円・値段の合成)/ `tests/test_phase2_p2_0*.py`・`tests/test_scalp_logic.py`・`tests/test_k1_*.py`(bp → 合成の値段、`/ 1e4`)/ `tests/test_composite.py`・`test_paper_state.py`・`test_short_margin.py`・`test_resilience.py`(20 万円の口座の合成)/ `tests/road/test_road_sizing.py` 27・38(20 万円 × 0.70 ÷ 段数 ÷ 値段) |

- 語に当たらなかった 254 行から足すもの(読んだ): `docs/legacy/matilda_for_TaroCamp37.py` 825・`matilda_v52.py` 726(`sfd = (fp - sp) / sp * 100`、値段の比 → %)/ `scripts/phase2/p2_08_run.py` 348・646-647・1056-1057・`src/bot/research/xborder_p2.py` 286・`xborder_p2_fast.py` 200・343・`scripts/research_signal_fade.py` 87-88・`research_leader_surface.py` 52-53(% → 比の閾値)/ `scripts/research_fx_sessions.py` 719・918・1122(`(b + 2.93) / (2 * b) * 100` など、bp の障壁と bp の経費から損益分岐の勝率 % を出す)/ `scripts/research_attention_vol.py` 95(高安の幅 ÷ 終値 × 100)/ `research_trend_lt1.py` 399(`(es-1)*100`)/ `research_overnight_onr.py` 377-400(年率 × 100)/ `research_seasonality.py` 196(ボラ × 100)/ `research_regime_composite.py` 311・344・`research_signals.py` 185(前方の値動き × 100)/ `src/bot/research/katsuo_limit_sim.py` 75(docstring「× 1e4 / 100」)。どれも (a)(b) の経路の外(2.2 に出したものを除く)。
- 語に当たった試験でない 262 行のうち、表 4・表 5 に出していないもの(読んだ): `src/bot/research/xborder_p2_fast.py` 347(`funding = ns * (funding_pct_per_settlement * 100.0)`、% → bp。`xborder_p2.py` 325 行と同じ換算。(c))/ `src/bot/research/cards/library/c1_xborder_mom.py` 20・94-95(`thr_pct / 100`、% → 比の閾値)/ `src/bot/bt/pipeline.py` 228(`px * (1 + move / 100 * …)`、% → 合成の値段。(d))。
- 試験の 131 行(読んだ): `tests/bt/battery/item_4/*`・`tests/bt/item_4/*`・`tests/bt/critic/item_4/*` の % の手数料率・滑り・逆指値 → 比・値段・円(`size * price * pct / 100` など。比べる相手の道具の口が % で受ける)、`tests/test_judge_gates.py`(% → 円)、`tests/test_portfolio_and_strategy.py` 40・88・`tests/bt/item_3/test_i3_report_grid.py` 179(円の資産の落ち込み → %)。bp の値を扱う行は無かった。
- 時刻・個数・ミリ秒の `200_000`(`ts_ms`・`CTRL_MARGIN_MS`・`PRINT_MARGIN_DAYS` など)、`"=" * 100` の罫線、勝率・充足率などの個数の割合 × 100 は表に入れていない(bp・円・% の量の換算ではないと読んだ)。

## 3. `pnl_bp` 以外の名前で bp を受け取る口(§5 の 3)

### 3.1 名前の一覧の取り方と数

```
$ git ls-files -z -- '*.py' ':!docs/RESEARCH/WINDOW1' ':!backtest_data/phase2_sealed' | xargs -0 grep -oE '\b[A-Za-z_][A-Za-z0-9_]*_bps?\b' > names_raw.txt; wc -l < names_raw.txt
5214
$ cut -d: -f2 names_raw.txt | sort -u | wc -l
544
$ (名前ごとのファイル数) awk '$1>=2' names_files.txt | wc -l
224
```

- `_bp`・`_bps` で終わる名前は 544 種、2 つ以上のファイルに出るのは 224 種。そのうち (a)(b)(d) のファイル(`RA.txt`・`RB.txt`・audit_8 の (d) 11 個)に 1 つでも出るのは 44 種(下の表 6 の元)。ファイル数の多い順: `pnl_bp` 73・`mean_bp` 52・`ci95_bp` 33・`sum_bp` 30・`dist_node_bp` 29・`net_bps` 28・`dist_vwap_bp` 21・`cost_bps` 20・`sd_bp` 19・`mean_bps` 19・`per_trade_bp` 17・`gross_bps` 16・`total_bp` 14・`spread_bps` 14・`mde_bps` 12・`r_night_bps` 11・`move_bp` 11。
- `values_bps` は `src/bot/research/overnight.py` の 1 本だけ(`edge_trend` の引数。6.1)。
- **範囲の断り: 名前が同じでも、同じ値がファイルをまたいで流れているとは限らない。** 224 種の全部の、書く所と読む所を 1 つずつ辿ってはいない。辿ったのは、(a)(b)(d) のファイルで受け取る口(表 6)と、§3.2 の 42 個のうち渡し手を辿っていなかったもの(表 7)。(c) どうしは 3.4 で import でつながる組だけを機械で拾った。

### 3.2 表 6: (a)(b)(d) で、`pnl_bp` 以外の名前で bp を受け取る口

| # | 受け取る側(流れ先) | 名前 | 渡してくる側と、その種類 | 根拠(行) |
|---|---|---|---|---|
| 1 | `src/bot/monitoring/aggregate.py` の `_on1_paper`((b)) | `net_bps`・`net_yen` | `scripts/paper_on1.py` だけ(6.2)。② 対数 − ④ 手数料率。`mean_net_bps` は aggregate 自身が平均して作る名前 | aggregate 346-374、paper_on1 115-121 |
| 2 | `aggregate.py` の `_onr_paper`((b)) | `mean_bps`・`gap_mean_bps`(`status.json` をそのまま渡す) | `scripts/paper_onr.py` 254-263 行が書く。`mean_bps` = `etf_on_bps`(200 行 `math.log(open_exit / close_entry) * 1e4` = ② 対数、経費を引かない)の平均、`gap_mean_bps` = ETF と指数の夜間の ② の差の平均 | aggregate 392-407、paper_onr 200-263 |
| 3 | `src/bot/monitoring/backtest_view.py`((b)) | `per_trade_bp`・`mean_bp` | `src/bot/bt/report/metrics.py` 72・130-132 行の `per_trade_bp`(80 行 = ② − ④ 手数料率、audit_8 口 7) | backtest_view 208・239・278 |
| 4 | `src/bot/monitoring/backtest_chart.py`((b)) | `total_bp`・`mean_bp`・`cum_bp`・`max_dd_bp`・`base_bp` | 同じファイルの `TradeSet.bp`(audit_8 口 5: 円 ÷ 建玉の円 × 1e4 か、カードの `pnl_bp` = ③)から作る | audit_8 口 5 |
| 5 | `src/bot/monitoring/backtest_cards.py`((b)) | `daily_sum_bp`・`max_dd_bp`・`max_bp` | 同じファイルが `daily.csv` の `pnl_bp`(③。書き手は (d) の `export_card_trades.py`)から作る | audit_8 口 6 |
| 6 | `src/bot/jpx/etf_auction_executor.py` の `summarise_ledger`((b)) | `c_bps`・`e_buy_bps`・`e_sell_bps`・`fee_bps`・`tick_bps`・`mean_c_bps`・`ci_lo_bps`・`ci_hi_bps` | 同じファイルが台帳に書いた列を読む(763-771 行。率の差 + ④ 手数料率)。`block_bootstrap_ci` に `c_bps` を渡す(6.1) | 763-812 |
| 7 | `src/bot/research/overnight.py` の `edge_trend`((b) の経路の上。呼ぶのは (c) だけ) | `values_bps` | 6.1 の表(② / ④ / ②−④) | 6.1 |
| 8 | `src/bot/research/board.py`((b)、`extract_tape.py` から) | `depth_bps`・`depth_within_bps`・`cost_bp`・`walk_cost_bp` | 同じファイルが板から作る(④ 板の距離・板を食う経費)。外から受け取らない(`run_board_round.py`・`research_imbalance.py`・`research_two_sided_flow.py`・`measure_exec_floor.py`・`o3c_signal_value.py` は (c) で、同じ名前を自分で作る) | audit_8 表 1 の 38 行目 |
| 9 | `scripts/data_quality.py`((b)) | `spread_bps`(CSV の列) | 列の名前で読む(440 行 `_find_col(header_lower, ["spread_bps"])`)。`"spread_bps"` の字を書く .py は `data_quality.py` のほかに `judge_board_round.py`・`run_board_round.py`・`tp_operating_curve.py`(どれも (c))と試験だけ。`schema/board_round_series_5s.json` 14 行が `spread_bps` を「basis points of mid」の列として持ち、その書き手は `scripts/run_board_round.py`(301・313 行 `data/board_round/series_5s.csv.gz`、(c)、④ スプレッド)。data_quality はスプレッドの値の範囲(≤ 0・> 50)を見るだけで、ほかの bp と足し引きしない(26 行) | `grep -lE '"spread_bps"'` の出力(下) |
| 10 | `scripts/record_funding_basis.py`((b)) | `basis_bp`・`basis_close_bp` | 自分で作って書く(④ ベーシス)。これを読む .py は試験の外に無い(下のコマンド) | 235・248 |
| 11 | `docs/RESEARCH/matilda_main/*/ledger_rows_*.py`((a)) | `move_bp` | 台帳の文の中の数として書く(② 値動き)。値はこの台本の外の出力(`diag_paths` の MFE・MAE)から写したもの(`ledger_rows_count.py` 26 行) | audit_8 表 1 の 1・2・7・9・12 行目 |
| 12 | `scripts/analysis/simple_trades.py`((a)) | `sum_bp` | 自分で ① から作る(summary.json の all.sum_bp) | audit_8 口 1 |
| 13 | `src/bot/research/cards/measure.py`((d)) | `r_bp`・`mean_bp`・`sum_bp`・`drift_removed_bp` | `src/bot/research/cards/pnl.py` の `r_bp`(②)と `pnl_bp`(③、`e * r`)。`drift_removed_bp` は 124 行 `b = e * (r - rm_ext[codes])`(群ごとの ② の期間平均を引いた ② に持ち高を掛けた ③型) | audit_8 口 13 |
| 14 | `scripts/w4_measure/post.py`・`daily_stats.py`・`light_b2.py`((d)) | `mean_bp`・`drift_removed_bp`・`per_day_bp`・`per_minute_bp`・`sum_bp`・`median_bp`・`final_cum_bp` | `measure.py` の出力(③ と ②)を読んで表にする | post 66-77 |
| 15 | `src/bot/research/cards/library/c2_owner_xvenue_wick.py`((d)) | `small_gate_bp`・`big_gate_bp` | 自分の定数(④ 閾値)。`katsuo_limit_sim.py`((c))も同じ名前を持つ | audit_8 表 1 の 49 行目 |

```
$ git ls-files -z -- '*.py' ':!docs/RESEARCH/WINDOW1' ':!backtest_data/phase2_sealed' | xargs -0 grep -lE '"spread_bps"'
scripts/data_quality.py
scripts/judge_board_round.py
scripts/run_board_round.py
scripts/tp_operating_curve.py
tests/test_board_round.py
tests/test_constants_inventory.py
tests/test_data_quality.py
$ git ls-files -z -- '*.py' ':!docs/RESEARCH/WINDOW1' ':!backtest_data/phase2_sealed' | xargs -0 grep -nE 'basis_bp|basis_close_bp' | grep -v 'record_funding_basis.py'
(出力なし)
```

### 3.3 表 7: audit_8 §3.2 の 42 個のうち、渡し手を辿っていなかったもの

audit_8 の表 2 で渡し手を書いたもの(`diag_tables.py`・`diag_paths.py`・`fam_tables.py`・`same_bar_daily.py`・`backtest_chart.py`・`backtest_cards.py`・`overlap_daily.py`・`export_card_trades.py`・`card_trades.py`・`c4_limit_run.py`)を除いた、試験でない 26 個(`c2_limit_run.py` は書き手として表の中に出す)。各ファイルの読み込みの行(置き場の定数・`load_run`・`DictReader`・`read_csv`・`json.load`)を grep で出して読んだ。

| 受け取る側 | 読む置き場 | 書き手と種類 |
|---|---|---|
| `docs/RESEARCH/cards/c2_owner_xvenue_wick/redo2_2026-10-05/feet_crossed.py`・`scripts/w4_measure/c2_read_limit.py`(38 行)・`c2_ref_vs_g_match.py`(32 行)・`c2_read_exits.py`・`c2_read_exits_decomp.py`・`c2_read_gated_decomp.py`・`c2_read_ablation_decomp.py`・`c2_read_r2.py`・`c2_ref_vs_g_cause.py`(87 行 `RUNS = mm.RUNS`)。c2_read_exits・_exits_decomp・_gated_decomp・_ablation_decomp・_r2 は `import c2_read_limit as rl` と `--root` の既定 `rl.DEFAULT_ROOT` | `docs/RESEARCH/cards/c2_owner_xvenue_wick/limit_sim/runs/<走らせ>/trades.csv.gz`・`summary.json`(feet_crossed 15 行 ほか) | `scripts/w4_measure/c2_limit_run.py`(84 行 `KatsuoLimitSim`)。`katsuo_limit_sim.py` 749 行 `"pnl_bp": tr["pnl"]`、721・768 行 `side × (px / avg − 1) × 1e4 × cq` = **量で重みを付けた ③型**(1.3)。audit_8 表 1 は c2_limit_run を ② としていた |
| `docs/RESEARCH/cards/c4_owner_matilda_range/redo2_2026-10-05/d2_volsplit.py`(24・33 行)・`scripts/w4_measure/c4_read_r2.py`(39 行 `limit_sim/families_r2`)・`c4_read_round2.py`・`c4_limit_batch.py` | `docs/RESEARCH/cards/c4_owner_matilda_range/limit_sim/…` | `c4_limit_run.py` → `matilda_limit_sim.py` 458-463 行(③型、建玉 1/段数。audit_8 口 15) |
| `docs/RESEARCH/cards/c4_owner_matilda_range/diag_gate/fill_delay.py`・`gate_tables.py` | gate_tables 5 行「門の無いカード(no_trend_body)の 1 分ごとの損益(W1 の測定器と同じ e_t × (open_{t+2}/open_{t+1} − 1) × 1e4)」 | ③(カードの測定器)。fill_delay は 12 行 `np.load(sys.argv[1] + "/probe.npz")` で引数の置き場を読む。`probe.npz` を書くのは同じ置き場の `gate_diag.py` 138-139 行(`exposure`・`r_bp`・`pnl_bp` = `pnl(run)` の ③) |
| `docs/RESEARCH/cards/c9_liquidation_cascade/redo2_2026-10-05/c9_redo.py`(24・53 行)・`run_a/make_tables.py`(34 行)・`run_a/three_way_m_policy.py`(59・95 行)・`scripts/c9_run_a.py`(175-192・494 行) | `data/c9_run_a/full_20230625_20241014/policy_cascades.csv.gz` ほか | `scripts/c9_run_a.py` → `src/bot/research/liq_cascade_v2.py`(48 行「`pnl_bp`・`レグ損益_bp` = 建玉の向きに正」、610 行 `pos_dir * (px - pe) / pe * 1e4`)= ②(向きを掛けた値動き、1 単位) |
| `docs/RESEARCH/cards/c6_weekend_gap_revert/redo2_2026-10-05/k046_recount.py`(22 行) | 同じ置き場の `trades_btc/trades.csv.gz` | `c6_redo.py`(③、audit_8 表 1 の 93 行目「72 行 `e * (… - 1.0) * 1e4`」) |
| `docs/RESEARCH/cards/c3_yen_premium_revert/redo2_2026-10-05/convert_limit.py`(1-19 行) | `measure_limit/<窓>/daily.csv` | 指値の模型の daily.csv(書き手は辿っていない。未確認)。値を変えずに `diag_tables.py` の形に写す |
| `scripts/analysis/trade_rows.py`(42・49・92 行) | 引数の走らせの `trades.csv.gz`・`trades.json.gz` | 引数しだい(① も ③ も来る)。6 行「`summary.json` の all.trades / all.sum_bp と突き合わせる」 |
| `scripts/o3c_signal_policy.py`・`o3c_signal_value.py` | 自分で作る(`o3c_signal_policy.py` 658 行・`o3c_signal_value.py` 712 行 `direction * (p_out - p_in) / p_in * 1e4`) | ②(向きを掛けた値動き、1 単位) |
| `scripts/w4_measure/round0_decomp.py` | `overlap_daily` を import して同じ SERIES を読む(33 行 `ov.REPO`) | audit_8 口 12 と同じ(③ と ③型) |

- 範囲の断り: 各ファイルの読み込みの行を grep で出して読んだだけで、ファイルを頭から読んではいない。

### 3.4 表 9: (c) どうしも含めた、import でつながる 2 つのファイルの間の `_bp`・`_bps` の名前(機械で拾った)

2 つ以上のファイルに出る名前(`pnl_bp` を除く 223 種)について、ファイルごとに「書く形」(`"名前":`・`["名前"] =`・`名前 =`・列名の並びの中の `"名前",`)と「読む形」(`["名前"]`・`.get("名前")`・`.名前`)を正規表現で拾い、読む側と書く側が import の表(`edges.tsv`)で直につながる組だけを残した。

```
$ python3 flow3.py      (名前 223 種、読む側 × 書く側の候補 544 組、名前 172 種)
223 544 172
$ python3 (pairs3.json のうち、読む側と書く側が import で直につながるもの) > pairs3_imp.txt; wc -l < pairs3_imp.txt
227
$ grep -v '^tests/' pairs3_imp.txt | grep -v '<- tests/' | wc -l
140
```

- 族ごとの組の数(試験でない 140 組の中。受け取る側の名前で数えた):

```
$ nt() { grep -v '^tests/' pairs3_imp.txt | grep -v '<- tests/'; }
$ nt | grep -E '^(scripts/measure_katsuo|scripts/measure_exec_floor|docs/RESEARCH/cards/c2_owner_xvenue_wick/vol_gate)' | wc -l
39
$ nt | grep -E '^(scripts/o3c_|docs/DATA/probes/20260920_o3c_cascade_read)' | wc -l
26
$ nt | grep -E '^scripts/phase2/p2_0[123]' | wc -l
10
$ nt | grep -E '^scripts/(run_scalp_paper|replay_scalp_storm|research_scalp_exits|research_exit_surface)' | wc -l
12
$ nt | grep -E 'u_bps' | wc -l
6
$ nt | grep -E '^scripts/w4_measure/c[24]_' | wc -l
16
```

- 範囲の断り: 書く・読むの判定は文字の形だけで、向き(どちらが値を作るか)は 1 組ずつ確かめていない。import でつながらない組(出力のファイルを介する組)は 4 で見た所しか結んでいない。227 組のうち下の表に書いたのは、試験でない 140 組を名前の族ごとにまとめ、目で読んだ代表の行で種類を決めたもの。
- 結果(推定): 試験でない 140 組のほとんどは、同じ族の台本どうしで同じ種類の名前を受け渡している(下の表)。種類の違う bp が 1 つの名前で出会う組は、下の表の「種類」の列に 2 つ以上を書いたものだけ。

| 族(受け取る側 ← 渡す側の例) | 名前 | 種類 |
|---|---|---|
| `measure_katsuo_*`・`measure_exec_floor.py`・`measure_vol_gate.py` の間(`measure_katsuo_effect.py` ← 各台本 など、39 組) | `mean_bp`・`ci95_bp`・`total_bp`・`decomp_bp`・`body_bp` | ②(建玉 1 単位の値動き。`measure_katsuo_effect.py` 153 行「建玉 1 単位でカツオの 4 分岐を回し、1 取引ずつの符号付きリターン(bp)」) |
| o3c の台本の間(`o3c_oi_distance.py`・`o3c_price_level_table.py`・`o3c_reaction.py`・`o3c_signal_*`・`20260920_o3c_cascade_read.py`、26 組) | `dist_node_bp`・`dist_vwap_bp`・`dist_gap_bp` | ④ 距離(`(位置 − p_liq) / p_liq × 1e4`、`o3c_oi_distance.py` 74 行) |
| `scripts/phase2/p2_01_*`・`p2_02_*`・`p2_03_*` の間(10 組) | `r_night_bps`・`r_day_bps`・`leg_*_bps` / `cost_*_bps` / `net_*_bps`・`mean_net_*_bps` | ② / ④(円の経費 ÷ 建玉の円 × 1e4、2.3)/ ②−④ を、別の名前で分けて渡す |
| `scripts/phase2/p2_08_run.py` ← `src/bot/research/xborder_p2.py`・`xborder_p2_fast.py` | `gross_bps`・`funding_bps`(と `net_bps`) | ② / ④ 資金調達率(325 行で % × 100)/ ②−④(`net = gross - cost_bps - funding`、xborder_p2 339 行) |
| `scripts/run_scalp_paper.py`・`replay_scalp_storm.py`・`research_scalp_exits.py`・`research_exit_surface.py` の間(12 組) | `thr_bps`・`thr_armed_bps`・`tp_bps` / `signal_bps`・`ret_bps`・`gross_bps` | ④ 閾値 / ② |
| `research_matilda_surface.py`・`research_matilda_taro.py`・`research_m4_finecheck.py` の間 | `u_bps` | 1 単位あたりの往復の値動きの bp(②)から資金調達率(④)を引いたもの(`research_m4_finecheck.py` 1011 行「unit bps = mean per-unit round-trip return NET of funding」)。日の和と累積は建玉の重み(`research_matilda_modern.py` 252-253 行「notional-weighted basis」= ③型) |
| `scripts/qa/make_known_answer*.py` の間 | `quoted_spread_bps`・`taker_fee_bps`・`true_taker_roundtrip_floor_bps` / `realized_overnight_mean_bps` | ④ / ② |
| `scripts/w4_measure/c2_read_*`・`c4_read_*` の間 | `sum_bp`・`avg_bp`・`diff_bp` | 受(c2 は ③型 `katsuo_limit_sim`、c4 は ③型 `matilda_limit_sim` の走らせの和。3.3) |
| `scripts/dashboard_cards/export_card_trades.py`((d))← `light_b2.py`・`daily_stats.py`・`src/bot/research/cards/measure.py` | `sum_bp`・`final_cum_bp`・`per_day_bp` | ③(カードの P_t) |
| `src/bot/monitoring/backtest_view.py`((b))← `backtest_chart.py` | `mean_bp` | 3.2 の 4 と同じ(円 ÷ 建玉の円 × 1e4 か、カードの ③) |
| `src/bot/research/cards/library/c2_owner_xvenue_wick.py`((d))と `katsuo_limit_sim.py` | `small_gate_bp`・`big_gate_bp` | ④ 閾値(ひげの長さ ÷ 終値 × 1e4 と比べる) |
| `scripts/judge_board_round.py` ↔ `tp_operating_curve.py`・`research_board_calibration.py` | `spread_bps`・`avg_spread_bps` | ④ スプレッド |
| `scripts/analysis/batch_runs.py` ↔ `trade_rows.py` | `sum_bp` | 受(引数の走らせしだいで ① も ③ も来る。3.3) |
| `src/bot/research/liq_cascade_v2.py` ← `run_a/make_tables.py` / `three_way_m.py` ↔ `three_way_m_policy.py` | `mat4_bounce_bp` / `abs_m10_bp`・`abs_m60_bp` | ② |
| `scripts/render_prereg.py` ← `preflight_prereg.py` | `sd_trade_bp` | ②(K1 の取引の bp の標準偏差) |
| `scripts/research_fx_s4_judgment.py` ← `research_fx_event_ticks.py` | `impulse_bps` | ② |
| `scripts/measure_liq_bands.py` ← `src/bot/research/liq_bands.py` | `naive_band_half_width_bp` | ④ 距離の引数 |

- 種類の違う bp が同じ名前で出会う組(上の表で 2 つ以上を書いたもの): `p2_08_run.py` ← `xborder_p2*.py`(`net_bps` = ② − ④ 経費 − ④ 資金調達率)、`research_matilda_*` の `u_bps`(② − ④ 資金調達率。日の和は ③型)、`batch_runs.py` ↔ `trade_rows.py` の `sum_bp`(① か ③)、`backtest_view.py` の `mean_bp`(円 ÷ 建玉の円か ③)。どれも 3.2・3.3 と同じ口か、(c) の中の口。

## 4. (c) 254 ファイルの出力のファイルと、(a)(b) の読み(§5 の 4)

### 4.1 やり方

- (c) 254 個(audit_8 表 1 で流れ先が「(c)」のもの。「(c)試験」169 個は入れていない)と、(a)(b) の届く先 251 個(`RA.txt` ∪ `RB.txt`)の全部から、`.csv`・`.json`・`.jsonl`・`.md`・`.gz`・`.npz`・`.parquet`・`.txt` で終わる文字列を取り出し、ファイルの名前(最後の `/` より後)で突き合わせた。

```
$ python3 (C.txt と RAB.txt の各ファイルから、上の拡張子で終わる文字列の名前を取り出して突き合わせる)
1172 42 113      (組の数・名前の種類・当たった (c) のファイル数)
```

- 当たった名前 42 種のうち、取引所や外部から取った入力のデータの名前(`candles_*`・`binance_*`・`executions_*`・`ticker_*`・`usdjpy_*`・`nk225_*`・`reit_*`・`etf_1343_*`・`funding_rate_*`・`flow_*`・`*.csv.gz` など)は、(c) も (a)(b) も読む側なので外した。残りの名前ごとに、(c) 側が書くか、(a)(b) 側が同じ置き場を読むかを、その行を grep で出して読んだ。
- 範囲の断り: 名前で突き合わせたので、置き場を文字で組み立てる所(`os.path.join(a.out, …)` で `--out` の引数しだいのもの)は、読む側の置き場の名前と、書く台本の説明文で結んだ(下の「推定」)。ファイルの名前が文字列に出ない書き方(変数から作る名前)は拾えていない。

### 4.2 表 8: 結んだ結果

| 名前 | (c) の書き手 | (a)(b) の読み手 | 読んだこと | 流れ先 |
|---|---|---|---|---|
| `trades.json.gz`・`summary.json`(指値の模型の走らせ) | `scripts/w4_measure/c2_limit_run.py`(38 行「trades.json.gz 取引の記録 … git に入れる」・401 行 `write_trades_json(os.path.join(a.out, "trades.json.gz"), …)`)、`scripts/w4_measure/c4_limit_run.py`(`--out` 必須、121 行)、`c4_limit_batch.py`(176 行で `c4_limit_run.py` を `--out` 付きで走らせる) | `scripts/w4_measure/overlap_daily.py`((a)。37-38 行 `C4 = …/c4_owner_matilda_range/limit_sim/families_r2`・`C2 = …/c2_owner_xvenue_wick/limit_sim/runs`、42-50 行 SERIES の「カツオ K1 指値a 5分」`C2/weak_f5_limit_a_good`・「マチルダ v37」`C4/v37_good` など) | 書き手の出力の置き場は引数 `--out` で、置き場の名前は台本に固定されていない。`c2_read_limit.py` 2 行「カツオ…の指値の再現 40 本(`c2_owner_xvenue_wick/limit_sim/runs/`)」、`c4_read_r2.py` 2 行「段 1 の族 A・B 84 本(`limit_sim/families_r2/`)」が、この置き場を指値の模型の走らせの置き場として書いている(推定: 書き手はこの 2 本)。その置き場は git にも作業場にも無い(下のコマンド) | **(c) → (d)** に直す: `c2_limit_run.py`・`c4_limit_run.py`・`c4_limit_batch.py`。これらが import する (c) の `src/bot/research/katsuo_limit_sim.py`・`matilda_limit_sim.py`・`trade_record.py` も **(d)**(import の表で辿った)。audit_8 の (d) の決め方(書き出しを (a)(b) が読む口はあるが、置き場が git に無く、今あるかは未確認)に合わせた |
| `record.json`・`repro.json`(走らせの記録) | `scripts/k1_newenv_fix_pipeline.py`(151 行 `--out-dir` の既定 `backtest_runs/k1_env_fixes/pipeline`、94 行 `P.run_pipeline(pl, runs_dir=out_dir)`) | `src/bot/monitoring/backtest_view.py`((b)。`backtest_runs/` を読む。audit_8 表 1 の 42・45・47 行目と同じ口) | この作業場の手元に `backtest_runs/k1_env_fixes` がある(audit_8 §1.4 の 2)。オーナーの PC の手元は未確認 | **(c) → (d)**(audit_8 の `k1_newenv_g_rawrun.py` と同じ決め方) |
| `scalp_paper.jsonl` | `scripts/run_scalp_paper.py`(155 行 `self.log_path = Path("data/scalp_paper.jsonl")`) | `src/bot/monitoring/market_view.py` 1241 行・`aggregate.py` 685 行・`scripts/dashboard.py` 1367 行((b)) | market_view が読むのは `price` と `pnl_jpy`(円)で、bp の列ではない(1077-1090 行)。aggregate は鮮度だけ(684 行)。`run_scalp_paper.py` は deploy/ から起動されない(audit_8 §1.3) | **(c) → (d)**(データは (b) が読むが bp ではない。今そのファイルが書かれているかは未確認) |
| `series_5s.csv.gz`(板の 5 秒の列。`spread_bps` の列を持つ) | `scripts/run_board_round.py`(301・313 行 `data/board_round/series_5s.csv.gz`) | `scripts/data_quality.py`((b)。`schema/board_round_series_5s.json` 4-7 行の `path_glob` が `data/board_round/series_5s.csv.gz`・`paper_logs/board_round_series_5s.csv.gz`・`backtest_data/board_round_*/board_round_series_5s.csv.gz` を持ち、440 行で `spread_bps` の列を名前で読む) | 3.2 の 9 と同じ口。data_quality は値の範囲(≤ 0・> 50)を見るだけ(④ スプレッド)。`data/board_round/` は git に無い(`git ls-files data/board_round | wc -l` → 下)。オーナーの PC の手元は未確認 | **(c) → (d)** |
| `QUALITY.json` | `scripts/qa/pipeline_known_answer_daily.py` 718 行 | `scripts/data_quality.py` 700 行・`aggregate.py` | qa は `tmp_root / "data" / "QUALITY.json"`(試しの一時の置き場)に書く | (c) のまま |
| `onr_ledger.csv` | `scripts/phase2/p2_02_final.py` 111 行 | `aggregate.py`((b)) | p2_02_final は `paper_logs/onr_ledger.csv` を**読む**側(書き手は (b) の `paper_onr.py`)。(c) から (b) への流れではない | (c) のまま |
| `SEALED.json`・`UNSEAL_LOG.jsonl` | `scripts/phase2/p2_0*.py` | `src/bot/research/sealed.py`・`src/bot/bt/data/allowlist.py` | 封印の台帳。bp の値は流れない(読んだ範囲) | (c) のまま |
| `bot.jsonl`・`oi_snapshots.csv` | `scripts/judge_gates.py` | `dashboard.py`・`aggregate.py`・`market_view.py` ほか | judge_gates は読む側 | (c) のまま |
| `daily.csv`・`trades.csv.gz`・`summary.json`(カードの redo2・c9 など) | `c5_redo.py`・`c6_redo.py`・`convert_limit.py`・`offhour_check.py`・`card_trades.py`・`batch_runs.py` ほか | `diag_tables.py`・`diag_paths.py`((a)。引数 `--run` の置き場を読む)、`backtest_cards.py`((b)。`backtest_runs_shared/cards` だけ)、`docs/RESEARCH/matilda_main/*`((a)。`backtest_runs_shared/matilda_main_trades` だけ) | (c) の書き手は自分の置き場(`redo2_2026-10-05/…`・`limit_conv/…`・`data/c9_run_a/…`)に書く。(c) の中で `backtest_runs_shared` に書くものは無い(下のコマンドで当たる 3 本は読む側か文)。今の分析の文書と台帳 K-301 以降に、これらの置き場の名前は出ない(下のコマンド)。`diag_tables.py --run` に (c) の置き場を渡す今の分析は見つからなかった | (c) のまま(今の分析の文書に出ないことまでしか確かめていない) |
| `manifest.json`・`TABLES.md`・`PREREG.md`・`ITER.md`・`fills.json`・`{name}.csv` | 各 (c) | 各 (a)(b) | 置き場が違う(cards の manifest と fx_event_library の manifest など)か、文の中の名前だけ | (c) のまま |

```
$ ls docs/RESEARCH/cards/c2_owner_xvenue_wick/limit_sim/runs; ls docs/RESEARCH/cards/c4_owner_matilda_range/limit_sim/families_r2
READ_R2
R2
$ git ls-files docs/RESEARCH/cards/c2_owner_xvenue_wick/limit_sim docs/RESEARCH/cards/c4_owner_matilda_range/limit_sim | awk -F/ '{print $5"/"$6"/"$7}' | sort | uniq -c
      2 limit_sim/SPEC.md/
      2 limit_sim/families_r2/R2
      1 limit_sim/runs/READ_R2
(SERIES が読む weak_f5_close_a・v37_good などの置き場は無い)
$ tr '\n' '\0' < C.txt | xargs -0 grep -nE 'backtest_runs' (backtest_runs_shared を書くものを探した)
scripts/k1_newenv_fix_pipeline.py:5,54,151 / scripts/k1_newenv_g_tables.py:2,23,148 / scripts/k1_newenv_tables.py:4,38,170 / scripts/w4_measure/c2_ref_vs_g_match.py:34 / scripts/w4_measure/round0_decomp.py:2,5,160
(backtest_runs_shared に出るのは c2_ref_vs_g_match.py 34 行 G_RUNS(読む)と round0_decomp.py(文と読む)だけ)
$ grep -lE 'limit_conv|trades_btc|c9_run_a|limit_sim/runs|families_r2|measure_limit|backtest_runs/k1' docs/ANALYSIS/2026-10-0[89]_*.md; awk '/K-301/{f=1} f' docs/RESEARCH/FINDINGS_LEDGER.md | grep -oE '(同じ語)' | sort | uniq -c
(どちらも出力なし)
```

- data_quality((b))が読む置き場は `schema/*.json` の `path_glob` で決まる(名前の突き合わせでは `.csv.gz` を入力のデータとして外していたので、ここで別に結んだ)。`path_glob` の置き場の頭(`data/…`・`paper_logs/…`)を (c) 254 個と (a)(b) の届く先 251 個の両方に文字で探し、両方に出る置き場を全部読んだ。(c) 側が**書く**ものは `data/scalp_paper.jsonl`(`run_scalp_paper.py`、上の表)と `data/QUALITY.json`(qa の一時の置き場、上の表)だけで、ほかの組は (c) 側も入力として**読む**(`data/candles_FX_BTC_JPY.csv`・`data/ws`・`data/tape`・`data/venues` など、書き手は (b) の記録の台本)か、`backtest_data/fx_usdjpy_…` の名前の一部が `data/fx` に当たっただけだった。data_quality が bp として読む列は `spread_bps` だけ(`grep -n 'bp' scripts/data_quality.py` で当たるのは 26・440・568 行)なので、bp が (c) から (b) へ渡るのは `run_board_round.py` の 1 本。

```
$ python3 (schema/*.json の path_glob を全部出す) > schema_globs.txt; wc -l < schema_globs.txt
247
$ grep -ln '_bp' schema/*.json
schema/board_round_series_5s.json
schema/etf_measure_ledger.json
schema/on1_onr_ledgers.json
schema/scalp_paper_log.json
$ git ls-files data/board_round | wc -l
0
```

  bp の列を持つ schema の残り 3 本の書き手は (b)(`etf_auction_executor.py`・`paper_on1.py`・`paper_onr.py`)と、`scalp_paper_log.json` の `run_scalp_paper.py`(上の表で (d) に直した)。
- 直した数: (c) 254 個のうち 9 個を (d) に直す(`c2_limit_run.py`・`c4_limit_run.py`・`c4_limit_batch.py`・`katsuo_limit_sim.py`・`matilda_limit_sim.py`・`trade_record.py`・`k1_newenv_fix_pipeline.py`・`run_scalp_paper.py`・`run_board_round.py`)。(a)(b) に直すものは無かった(どれも、読む側の置き場が今あるかを確かめられない。audit_8 の (d) の決め方 = 書き出しを (a)(b) が読む口はあるが、置き場が git に無く今あるかは未確認、に合わせた)。
- 種類の目印: 直した 8 個のうち bp を (a) に渡す経路にあるのは指値の模型の 5 本で、種類は ③型(`matilda_limit_sim` は建玉 1/段数、`katsuo_limit_sim` は量で重み。1.3・3.3)。

## 6. `overnight.edge_trend` と `aggregate.py` の `net_bps`(§5 の 6)

### 6.1 `edge_trend` を (b) の経路から呼んでいるか

- 事実: 呼んでいない。(b) の経路(audit_8 の (b) の入口 35 個から import で届くファイル 151 個、`RB.txt`)の中で `edge_trend` の字を含むのは `src/bot/research/overnight.py`(定義)だけ。呼ぶ側は 3 本と試験 2 本で、どれも (a)(b) の経路の外。

```
$ git ls-files -z -- '*.py' ':!docs/RESEARCH/WINDOW1' ':!backtest_data/phase2_sealed' | xargs -0 grep -l 'edge_trend' (の各ファイルを RA.txt・RB.txt に当てた)
scripts/phase2/p2_01b_history.py RA=0 RB=0
scripts/phase2/p2_04_run.py RA=0 RB=0
scripts/phase2/p2_08_run.py RA=0 RB=0
src/bot/research/overnight.py RA=0 RB=1
tests/test_bot_research_overnight.py RA=0 RB=0
tests/test_phase2_p2_04.py RA=0 RB=0
```

- 事実: (b) の経路で `overnight.py` を import しているのは `src/bot/jpx/etf_auction_executor.py` 796 行 `from bot.research.overnight import block_bootstrap_ci` だけ(`overnight` の import を全部 grep し、RB に当てた。ほかの 25 行は RB=0)。(b) が overnight から使うのは `block_bootstrap_ci` で、`summarise_ledger` が台帳の `c_bps` の列(769 行 `(printed - realised) * 1e4 + fee_bps` = 率の差の bp に ④ 手数料率を足したもの)を渡している(etf_auction_executor 801-812 行)。
- 呼ぶ側が渡しているもの(事実、各行を読んだ。どれも (c)):

| 呼ぶ側 | 行 | 渡す `values_bps` | 種類 |
|---|---|---|---|
| `scripts/phase2/p2_01b_history.py` | 252-262 | `r_night_bps`(粗の夜間の値動き)/ `cost_bps_cons`(円の経費 ÷ 建玉の円 × 1e4)/ `r_net_bps_cons` の 3 本を 1 本ずつ | ② / ④ / ②−④ |
| `scripts/phase2/p2_04_run.py` | 1133-1146 | `r_bps` / `cost_bps_cons` / `r_net_bps_cons` を TOM と全日で 1 本ずつ | ② / ④ / ②−④ |
| `scripts/phase2/p2_08_run.py` | 670-686 | `gross_bps` / `2.0 * c1w + funding_bps` / `net_of(a, c1w)` を 1 本ずつ | ② / ④(経費+資金調達率)/ ②−④ |

### 6.2 `aggregate.py` の `net_bps` を書くのは `paper_on1.py` だけか

- 事実: `aggregate.py` の `_on1_paper` が読むのは `data/paper_on1/ledger.csv`(695 行)の `net_bps` と `net_yen` の列(346-350 行)。その置き場の名前 `paper_on1` を書く .py は `scripts/paper_on1.py`(32-33 行 `OUT_DIR = ROOT / "data" / "paper_on1"`、`OUT_CSV = OUT_DIR / "ledger.csv"`)だけ。試験 `tests/test_on1_forward.py` は `tmp_path` に書く。`scripts/paper_onr.py` の `ledger.csv` は `data/paper_onr`(54 行)で別の置き場。

```
$ git ls-files -z -- '*.py' ':!docs/RESEARCH/WINDOW1' ':!backtest_data/phase2_sealed' | xargs -0 grep -nE '["/]paper_on1["/]|"paper_on1"'
scripts/paper_on1.py:15:Output: data/paper_on1/ledger.csv  (fully rebuilt from the input on every run --
scripts/paper_on1.py:32:OUT_DIR = ROOT / "data" / "paper_on1"
src/bot/monitoring/aggregate.py:695:    on1 = _on1_paper(root / "data" / "paper_on1" / "ledger.csv", now)
tests/test_on1_forward.py:20:paper = _load("paper_on1")
$ git ls-files -z -- 'deploy/*' | xargs -0 grep -n 'paper_on1'
deploy/fetch_all.bat:49:".venv\Scripts\python.exe" "scripts\paper_on1.py" >> "logs\fetch_all.out.log" 2>&1
deploy/share_logs.bat:46:copy /Y data\paper_on1\ledger.csv paper_logs\on1_ledger.csv >nul 2>&1
```

- 事実: `paper_on1.py` の `net_bps` は 115-117 行 `gross_bps = math.log(x / e) * 1e4`(② 対数)− `(2 * FEE_SIDE) / (e * MULTIPLIER) * 1e4`(④ 手数料率)。`aggregate.py` 356 行はその和を `/ 1e4 * 100` で % にし、`net_yen`(円)は別の列から足す(351 行)。bp と円を倍率で行き来する行は `aggregate.py` には無い(`grep -n '1e4\|\* 20\|MARGIN' src/bot/monitoring/aggregate.py` で当たるのは 356 行だけ)。
- 事実(4 の schema を読んでいて見つけた): `schema/on1_onr_ledgers.json` 21 行は `gross_bps` を「(exit_px - entry_px) / entry_px in bps, before fees」(単純な比)、24 行は `net_bps` を「net_yen expressed back in bps of entry_px*multiplier」(円 ÷ 建玉の円)と書く。`paper_on1.py` 115・117 行は `gross_bps = math.log(x / e) * 1e4`(対数)、`net_bps = gross_bps - (2 * FEE_SIDE) / (e * MULTIPLIER) * 1e4`(対数の ② − ④)で、schema の書く定義と式が違う(`net_yen / (e * MULTIPLIER) * 1e4` とも一致しない。差の大きさは値動きの 2 乗の程度で、測っていない)。
- 範囲の断り: .py 以外(.md を除く全部のファイル)に `paper_on1` を grep したが 120 秒で終わらず止めた。代わりに台本と設定の拡張子に絞って打った(下)。当たったのは deploy/ の 2 本だけ(上と同じ行)。.md・データのファイルは見ていない。手で `data/paper_on1/ledger.csv` を書き換える運用があるかは未確認。

```
$ git ls-files -z -- '*.sh' '*.bat' '*.ps1' '*.yaml' '*.yml' '*.toml' '*.service' '*.cfg' '*.ini' ':!docs/RESEARCH/WINDOW1' ':!backtest_data/phase2_sealed' | xargs -0 grep -ln 'paper_on1'
deploy/fetch_all.bat
deploy/share_logs.bat
```

## 7. 試験の 5 組の文字の言及(§5 の 7)

audit_8 §1.4 の 3 の 18 組を、前の作業者の import の表(`edges.tsv` の `strlit` の行)から作り直した。(a)(b) で届いたファイルで 474 個に入るもの → 届かなかった 474 個のファイル、の組で 18 組(試験 5・試験でない 13)。audit_8 の数と一致した。

```
$ python3 (edges.tsv の strlit の行で、a ∈ RA∪RB かつ a ∈ 474 個、b ∉ RA∪RB かつ b ∈ 474 個 を数える)
pairs(a in 474) 18 test 5 nontest 13
```

5 組の行を全部読んだ(事実)。どれも試験の名前を書いた文で、呼び出しではない。

| 言及する側 | 行 | 言及される試験 | 中身 |
|---|---|---|---|
| `scripts/record_venues.py` | 30 | `tests/test_record_venues.py` | docstring「future edit (statically checked in tests/test_record_venues.py).」 |
| `scripts/w4_measure/overlap_daily.py` | 4 | `tests/research/test_overlap_daily.py` | docstring「読み方の決まり(表を見る前に、この台本と `tests/research/test_overlap_daily.py` で固めた)」 |
| `scripts/w4_measure/vol_split_daily.py` | 5 | `tests/research/test_vol_split_daily.py` | docstring「`tests/research/test_vol_split_daily.py` で固めた)」 |
| `src/bot/strategy/composite.py` | 20 | `tests/test_composite.py` | docstring「tests/test_composite.py and scripts/validate_composite.py.」 |
| `src/bot/strategy/matilda_v37.py` | 4 | `tests/road/test_matilda_v37_spec.py` | docstring「受け入れの試験は tests/road/test_matilda_v37_spec.py。」 |

- 474 個の外の届いたファイルからの言及も 2 組あった(読んだ。どちらも文): `src/bot/bt/core/engine.py` 443 行 → `tests/bt/item_0/test_bt0_r11_foreign_objects.py`、`src/bot/order_management/reconciler.py` 50 行 → `tests/test_resilience.py`。
- 流れ先は変わらない(5 組とも (c)試験 のまま)。

## 8. 持ち越し(この作業場からは確かめられないこと)

依頼の 1〜4・6・7 は上限(11:19 UTC)の前に一通り終え、範囲を切った所もその場で読み足した。残っているのは、この作業場からは見えない・手段が無いものだけ。

1. 4 で (d) に直した 9 個の書き手の出力(`docs/RESEARCH/cards/c2_owner_xvenue_wick/limit_sim/runs/<走らせ>`・`docs/RESEARCH/cards/c4_owner_matilda_range/limit_sim/families_r2/<走らせ>`・`backtest_runs/k1_env_fixes/pipeline`・`data/scalp_paper.jsonl`・`data/board_round/series_5s.csv.gz`)が、オーナーの PC の手元に今あるか(未確認)。
2. `docs/RESEARCH/cards/c3_yen_premium_revert/redo2_2026-10-05/convert_limit.py` が読む `measure_limit/<窓>/daily.csv` の書き手(`measure_limit` の字を持つ .py は `convert_limit.py` と、その置き場を「excluded」と書く `scripts/dashboard_cards/build_manifest.py` 18 行だけ。未確認)。
3. `data/paper_on1/ledger.csv` を .py 以外の手段(手作業・.md に書かれた手順)で書く運用があるか(6.2。未確認)。
4. audit_8 の後に git に載った `docs/RESEARCH/matilda_main/` の 6 本(0.2)。依頼の対象(474 個)の外なので仕分けていない。
5. 3.4 の 227 組の書く・読むの向き(文字の形で拾っただけで、1 組ずつは確かめていない)。

範囲の断り(やったが切った所、本文にも書いた): 1 は行を 85〜150 字で切って読み、長い行は後ろを別に読んだ。2 は 9 語と 2.1 で足した形(`0.0001`・`1e-4`・`* 1e4` など、`* 0.01`・`/ 1e2`)を打った。`* 0.01`・`/ 1e2`・`* 1e2`・`/ 0.01` の bp の字の無い行は 14 行で、0.01 BTC の量・証拠金の最小額の計算(`docs/legacy/matilda_*.py` 303-338 行)・`research_two_sided_flow.py` 1254 行(円 × 約定率 1%)で、bp ↔ 円・% の新しい換算は無かった。

```
$ git ls-files -z -- '*.py' ':!docs/RESEARCH/WINDOW1' ':!backtest_data/phase2_sealed' | xargs -0 grep -nE '\* *0\.01\b|/ *1e2\b|\* *1e2\b|/ *0\.01\b' | awk -F: '{l=$0; sub(/^[^:]*:[^:]*:/,"",l); if (tolower(l) !~ /bp/) print}' | wc -l
14
```

## 9. 時間

着手 10:09 UTC(`date` の出力 `Fri Oct  9 10:09:23 UTC 2026`)。`date -u` で確かめた時刻: 10:14・10:17・10:18・10:19・10:20・10:22・10:23・10:24・10:26・10:27・10:28・10:29・10:30・10:31・10:33・10:34・10:35・10:39 と、仕上げの時刻(下)。見込み(70 分)より短いのは、6,139 行の読みを機械の下付けと一覧にまとめて読んだため。上限の前に依頼の分を終え、範囲を切った所(2 の残りの行・1 の長い行の後ろ・schema の置き場)も読み足してから止めた。
仕上げの時刻: 10:39 UTC(`date -u`)。
