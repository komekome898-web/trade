# 委任: V4(1 件目 / 連鎖の中で分けた state と criteria)・前半で固定した logistic・後半 5,000 件の一度きりの測定(2026-09-20)

## 0. 対応表(CLAUDE.md §0.1)
| やること | オーナーの原文の該当語(逐語) |
|---|---|
| 効く情報は残し、邪魔・無関係は外し、逆に効く情報は逆で与える(決定表 §7.1) | 「**効いている情報は残し、邪魔していたり無関係な情報は排除して、逆に効く情報は逆で与えるべきではないんですか？**」(L-318)、「**全てやってください。**」(L-323) |
| code の logistic を並べ、較正の良い方を方策の模擬に使う | 「**codeでの判断が勝てるならjevを使う意味はありません**」(L-321)、L-323 |
| Jev の遅延を実測し、遅延の項目を足す | 「**判断→注文のタイムロスは後々に成績直結します**」(L-321) |
| 1 件目に「新しい値段の領域」の事実を足す(前半で分かれれば) | L-320 (2) の案に対する L-323 |
| 後半は一度だけ、反証者レビューの後 | 設計 §4・§7.5(リードの規則) |

**出力はすべて日本語(code の文字列は英語)。判定語(陽性/陰性/有意/差あり/検出されず/支持/棄却)を書かない。`paper_logs/` を開かない。Jev の確率・較正・一致率の数値はリポジトリに入るファイルに書かない(`data/jev/v4/` にだけ)。この委任は 2 段に分かれる: 段 1(実装 + 前半の確認)で止まって渡す。段 2(後半)はリードが反証者レビューのあとに別に指示する。Do not commit. Do not push。**

## 1. 読むもの
設計 `docs/PHASE2/O3C/SIGNAL/SIGNAL_MATERIALS_DESIGN_2026-09-20.md` **§6 と §7 全部** / 道具 `scripts/o3c_jev_state.py`(文の型 13 本、帯の定数、下見)と試験 `tests/test_o3c_jev_state.py` / 包み `scripts/jev/client.py`(**`keep_alive=True` を使う**)/ 行データ `backtest_data/o3c_signal_materials_20260920/rows_materials.csv.gz`(24 本)、`backtest_data/o3c_signal_continue_20260920/rows_continue.csv.gz`(mat の生の列、label_60、half)/ 前段の選定 `backtest_data/o3c_signal_continue_20260920/jev/selection_manifest.json`(後半 5,000 件。段 2 で使う。**段 1 では後半に触れない**)。

## 2. 段 1 で作るもの
1. `scripts/o3c_jev_state.py` に V4 を足す: `build_state_v4(print_id)` = §7.1 の決定表どおりに文を残す / 外す(1 件目と連鎖の中で別の文の集合)。`JEV_QUESTIONS_V4_FIRST` / `JEV_QUESTIONS_V4_CHAIN` = §7.3 の criteria(英文はそのまま)。位置は `cand_1 == 0` で code が決める。
2. N1・N2(§7.2)の計算(ts 以前の約定だけ。p₀ を使わない)と、**前半だけ**での分かれ方(順位確率、前段の `o3c_signal_materials.py` と同じ数え方)。|確率 − 0.5| ≥ 0.03 なら V4 の 1 件目の文に足す(足した文の型を報告に書く)。表は `backtest_data/o3c_signal_materials_20260920/screen_N.csv`(2 行)。
3. logistic(§7.4): `scripts/o3c_signal_logit.py`。入力 = 決定表の材料(1 件目 9 本 + N1/N2 のうち分かれたもの / 連鎖の中 11 本)を前半の五分位の順位(0〜1、欠測 0.5)にしたもの。前半全件で当てはめ(numpy のニュートン法、L2 1e-3。sklearn は無い)、係数を `config/o3c_signal_logit_first.yaml` / `_chain.yaml` に書く。前半の 5-fold out-of-fold の順位分離・的中(0.5)・閾値 0.6/0.7/0.8 の適合率と件数を `data/jev/v4/logit_firsthalf.md` に書く(**数値はリポジトリに入れない**)。
4. 試験 `tests/test_o3c_jev_state.py` に足す: V4 の 1 件目に「外す」文が無い / 連鎖の中に「外す」文が無い / criteria が位置で切り替わる / N1・N2 が ts 以後を使わない(p₀ 書き換え不変)/ logistic の係数が前半だけから決まる(後半の値を変えても同じ)/ 予測が決定的。
5. 前半の確認(Jev を呼ぶ): 前半から 1 件目 600 件 + 連鎖の中 300 件(種 20260920、層化は前段と同じ側 × 材料 1 の 3 群のうち該当する群、日を跨いで偏らないよう 1 日 3 件まで)に V1 と V4 を当てる(1,800 回、`keep_alive=True`、2 件/秒)。`data/jev/v4/preview_answers.jsonl`(print_id・組・prob・input_tokens・latency_s)。表 `data/jev/v4/preview_tables.md`: 1 件目 / 連鎖の中 それぞれの順位分離(ブートストラップ SE つき)、0.05 刻みの分布、閾値ごとの適合率、logistic(out-of-fold)との比較、遅延の p50/p90/p99。**数値はリポジトリに入れない。**
6. 報告 `docs/PHASE2/O3C/SIGNAL/V4_STAGE1_REPORT_2026-09-20.md`: (0) 件数と呼び出し数 / (1) §0 の表 / (2) コマンド / (3) V4 の state の実物 6 件(1 件目 3・連鎖の中 3、英文そのまま)と criteria の英文 / (4) N1・N2 の分かれ方の表(これは前半の材料の表なので数値を書いてよい)/ (5) 設計に無い判断(全部)/ (6) サニティ / (7) 限界 / (8) 作ったファイル / (9) テストの末尾行(全スイート、`-q` 無し)。**Jev の性能の数値は書かない。**

## 3. 制約
read-only(入力を書き換えない)・冪等・後半に触れない(段 1)・Jev の呼び出しは 1,800 回まで。既定値を変えるなら列挙して理由を書く。モデル名(Claude 等)を書かない。上に書いたファイル以外を変更しない。文の型や criteria を変えたくなったら止めて報告する。
