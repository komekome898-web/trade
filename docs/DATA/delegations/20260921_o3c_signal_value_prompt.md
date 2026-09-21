あなたは本リポジトリの研究・実装エージェントです。設計 `docs/PHASE2/O3C/SIGNAL/SIGNAL_VALUE_DESIGN_2026-09-21.md`(オーナー承認 L-344)の**段 1 = 前半だけ**の道具・テスト・数表・報告を作ってください。**後半(`half == "後半"`)の行はこの委任では一切読まない**(段 2 は別の委任で一度だけ)。

【対応表(CLAUDE.md §0.1)】設計 §0.1 の表を報告の冒頭にそのまま写す(右列は L-344 で全部埋まっている)。設計に無い判断が必要になったら**そこで止めて報告する**(勝手に決めない。「未決」の節に書く)。

【読了必須】設計の全文(用語表・§2〜§5・§7・§8 を先に)/ `scripts/o3c_signal_policy.py`(状態機械 `simulate_cascade`・`simulate_baseline`・`price_at_or_after`・`judge_*`・出力の形。**再利用し、複製しない**)/ `scripts/o3c_signal_logit.py`(`fit_beta_front_half(label_col=...)`・`apply_frozen_rank`・`kfold_indices`・yaml/npz の保存形)/ `scripts/o3c_signal_continue.py`(約定の読み `DEFAULT_DATA_ROOT`・`at_or_after`・定数)/ `scripts/fetch_tardis_samples.py`(tardis 形式の列)/ 前段の報告 `POLICY_STAGE1_REPORT_2026-09-20.md`(報告の形)/ `tests/test_o3c_signal_policy.py`(テストの形)。

【データ(読むだけ)】`backtest_data/o3c_signal_continue_20260920/rows_continue.csv.gz`(`kind == "print"` かつ `half == "前半"` = 21,838 行、連鎖 8,931。列 `value_continuation_60` が値段のラベル、`label_60` が清算のラベル。**同じファイルの `kind == "q7_candidate"` 22,545 行は使わない**)/ `backtest_data/o3c_signal_materials_20260920/rows_materials.csv.gz`(材料の列。前半だけ読む)/ Binance の約定(前段と同じ経路、`o3c_signal_policy.py` の読み方をそのまま)/ bitFlyer 約定 `data/tardis/bitflyer_FX_BTC_JPY_trades/FX_BTC_JPY_YYYYMM01.csv.gz`(16 日、gitignore 域。**生データも抜粋もリポジトリに入れない。集計だけ**)/ bitFlyer 1 分足 `backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_2023.csv.gz`・`2024`。

【作るもの】
1. `scripts/o3c_signal_value.py`(サブコマンド `stage1` / `stage2`。**`stage2` はこの委任では実装だけして走らせない**。`stage1` は `half == "前半"` 以外の行を読んだら例外で止まる)。
   - ① の判断(設計 §3): `fit_beta_front_half(label_col="value_continuation_60")` を 1 件目(材料 14・8・C3・C4・11・A6・R1・9・15・N2)/ 連鎖の中(F5・1・F3・14・A6・C4・15・11・C3・8・2)で当てはめ、係数と経験分布を `config/o3c_signal_logit_value_{first,chain}.yaml` と `backtest_data/o3c_signal_value_20260921/logit_ecdf_value_{first,chain}.npz` に保存(前段の清算ラベルの係数は触らない)。**帯(Q1)**: 前半 5 分割 OOF の確率を 0.02 刻みで切り、帯ごとの続く割合と 2 SE を出し、基準率と 2 SE で区別できない帯を「わからない」とする(L-277 の規則、`SIGNAL_POLICY_DESIGN` R2.2 と同じ形)。2 値(基準率)の閾値 = 前半の値段のラベルの割合(1 件目 / 連鎖の中で別々)。到達時間の分布(値段のラベル = 1 のプリントで p₀ から 5 bp に初めて達するまでの秒。p10/p25/p50/p75/p90 と、1 秒・2 秒未満の割合)。
   - ② の格子(設計 §5): ノブ = 位置 3 × 条件 7(なし / 材料 12・14・15 の前半 p75・p90 以上)× 出口 3(連鎖の終わり + d / 最後のプリント + 300 秒 + d / 入ってから 300 秒 + d)× 損切り 3(なし / 含み損 20 bp / 50 bp。約定は「含み損が閾値に達した最初の約定の時刻 + d」以後の最初の約定)= **189 組**、遅れ d = 1 秒、費用込み。前半の全連鎖 8,931 本に当て、組ごとに 総収支(合計 bp)・中央値・p25/p75・負の割合・日等重み平均・日クラスタ SE・入った本数・建玉の回数・前半を日付順に 2 分割した前後の総収支。**選ぶ規則**(§5、事前固定): (a) 2 分割の両側で総収支 > 0、(b) 中央値 > 0、を満たす組の中で総収支が最大の 1 組。満たす組が無ければ「規則を満たす組は無かった」と書く(緩めない)。選んだ組について 1 ノブずつ他を固定して動かした総収支の差(4 表)。
   - 費用(設計 §4、Q5): `scripts/o3c_bitflyer_spread.py` — 標本日ごとに、1 秒以内に隣り合う買い約定と売り約定の価格差 ÷ 中値(bp)の分布(p25/p50/p75/p90、対の数)を、全時刻と「Binance の清算の直後 t₀ + 1〜5 秒」の 2 通りで出す。清算の時刻は `rows_continue.csv.gz` の `ts_ms`(**後半の標本日 8 日については ts_ms だけを使い、ラベル・価格・材料の列は読まない**。報告にそう書く)。主の c = 清算直後の 16 日プールの中央値、p75 を併記。出力は `backtest_data/o3c_signal_value_20260921/spread/spread_by_day.csv`(集計だけ)。
   - 費用の引き方: 連鎖 1 本 = c × 建玉の回数(型 B のドテン 1 回 = c)。① の方策・②・素・完全な判断のすべてに同じ c。
   - 前半の動作確認: 前段と同じく前半の連鎖 200 本(種 20260920)に ① の 7 方策 × 型 A/B × 遅れ 3 を通し、`dist_table` 等を前段と同じ形で出す(費用なし / 費用あり c・p75)。合成の連鎖で状態機械・損切り・出口 3 種・費用の加算の道筋を `synthetic_traces.csv` に出す。
   - Q5b (a) 前半分: 標本日に掛かる前半の連鎖 285 本で、入る・出る・損切りの約定を bitFlyer の約定の `at_or_after` に置き換えた損益と Binance の損益の対差(全部逆張り(素)と ① 3 択 A。②opt は選ばれた組)。(b) 1 分足の道具: 入る・出る時刻の次の 1 分の始値で損益を出す関数を作り、前半で Binance の同じ近似との対差を確かめる(後半には走らせない)。
2. `tests/test_o3c_signal_value.py`: 値段のラベルの再計算が既存列と一致(前半の抽出 200 件)/ 帯の規則(合成の確率列で「わからない」が基準率の周りに出る)/ 費用 = c × 建玉の回数(型 B のドテン 1 回)/ 損切り・出口 3 種の約定が ts + d 以後(合成)/ 格子の列挙が 189 / 選ぶ規則 (a)(b) と「無かった」の分岐 / `stage1` が後半の行で例外 / 判定語(陽性・陰性・有意・差あり・検出されず)が出力の文字列に無い / `paper_logs/` を開かない / 実効スプレッドの対の作り方(合成の約定列)。
3. 報告 `docs/PHASE2/O3C/SIGNAL/VALUE_STAGE1_REPORT_2026-09-21.md`: (0) 表の行数と数値セル数の数え直し(設計 §9 の見積もり 673 との差)/ (1) 設計 §0.1 の表 / (2) 実行したコマンドと出力(全部)/ (3) Q0・Q1・Q3・Q5・Q5b(a) の表と、前半 200 本の動作確認の表 / (4) **なぜ**(research-protocol §0.2 の 3 問。② で選ばれた組はどのノブが総収支を作ったか、① の帯は前段の清算ラベルの帯とどう違うか)/ (5) 未決・逸脱・限界 / (6) テストの件数と全スイートの結果。判定語を使わない。オーナーに見える文は日本語。

【出力】`backtest_data/o3c_signal_value_20260921/stage1_firsthalf/`(`grid.csv`・`grid_selected.json`・`knob_contrib.csv`・`calib_first.csv`・`calib_chain.csv`・`time_to_target.csv`・`dist_table.csv`・`position_breakdown.csv`・`judge_counts.csv`・`synthetic_traces.csv`・`q5b_secs_firsthalf.csv`・`summary.json`・`tables.md`・`MD5SUMS`)と `spread/`。

【長時間処理】10 分を超えるなら日ごとの chunk で再開できる形に(`setsid nohup … > <scratchpad>/run.log 2>&1 < /dev/null &`、監視は回数上限つき)。全スイート `PYTHONPATH=src python -m pytest`(`-q` を足さない)。

【制約】read-only(入力を書き換えない)・冪等・ネットワークなし・seed 固定。既定値を変えるなら列挙して理由を書く。最小 diff。コード・コメント・ログ・文書にモデル名を書かない。**後半に触れない。**Do not commit. Do not push.

【完了の形】上の 1〜3 が揃い、テストが全件通り、報告の (2) にコマンドと出力があり、(4) の「なぜ」が 3 問とも埋まっていること。設計に無い判断が出たら止めて報告に書く。

---
前段(jev_delegate、2026-09-21): TimeoutError: The read operation timed out
