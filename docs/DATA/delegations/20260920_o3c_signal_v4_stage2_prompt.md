# 委任: 段 2 — 後半 5,000 件に Jev V1 と前半で固定した logistic を一度だけ当てる(2026-09-20)

## 0. 対応表(CLAUDE.md §0.1)
| やること | オーナーの原文の該当語(逐語) |
|---|---|
| 後半 5,000 件に Jev と code の logistic を並べて一度だけ当て、較正の良い方を方策の模擬に使う | 「**codeでの判断が勝てるならjevを使う意味はありません**」(L-321)、「**全てやってください。**」(L-323) |
| Jev の遅延を実測して記録する | 「**判断→注文のタイムロスは後々に成績直結します**」(L-321) |
| Jev の形は V1(前半で選んだ) | 設計 §7.5 の段 1 の結果を受けた決定(リード) |

**出力はすべて日本語(code の文字列は英語)。判定語を書かない。`paper_logs/` を開かない。Jev の確率・較正・的中・一致率の数値はリポジトリに入るファイルに書かず `data/jev/v4/stage2/` にだけ置く。呼び出しは 5,000 回だけ(再送は client の再試行に任せ、自分で二重に送らない)。前半で固定したもの(logistic の係数・前半の経験分布 `logit_ecdf_{first,chain}.npz`・帯 `config/o3c_jev_state_bands.yaml`・問い・criteria)を一切変えない。**後半に対して `build_ecdf` や帯の再計算を絶対に呼ばない(反証者 7 D5)。順位は `apply_frozen_rank` で npz から引くだけ。**Do not commit. Do not push。**

## 1. 読むもの
設計 §7.4〜§7.6、段 1 の報告 `V4_STAGE1_REPORT_2026-09-20.md`、反証者レビュー 7 `REFUTER_REVIEW7_2026-09-20.md`(致命があればリードが直してから、この委任が出る)、`scripts/o3c_jev_state.py`(`build_state_sentences` = V1 の英文、`JEV_QUESTIONS_V1`)、`scripts/o3c_signal_logit.py`(`config/o3c_signal_logit_{first,chain}.yaml` と `logit_ecdf_{first,chain}.npz` を読んで予測。`apply_frozen_rank` を使う)、`scripts/o3c_signal_calib.py`(較正の良さ `calibration_goodness` / `choose_better`)、`scripts/jev/client.py`(`keep_alive=True`)、選定 `backtest_data/o3c_signal_continue_20260920/jev/selection_manifest.json`(後半 5,000 件、呼び出し順 = 選定順)。

## 2. 作るもの
1. `scripts/o3c_jev_state.py --stage second-half`(または新しい `scripts/o3c_signal_stage2.py`): 5,000 件それぞれに (a) V1 の英文 + V1 の criteria で Jev を 1 回(`jev-1.13.0`、`keep_alive=True`、2 件/秒、遅延を記録)、(b) logistic の予測(1 件目 / 連鎖の中で係数を切り替え)。`data/jev/v4/stage2/answers.jsonl`(print_id・位置(1 件目 / 連鎖の中)・jev_prob・logit_prob・label_60・input_tokens・latency_s)。再開可能に。
2. 表 `data/jev/v4/stage2/tables.md`(**リポジトリに入れない**): 1 件目 / 連鎖の中 それぞれに、Jev と logistic の 0.01 刻みと 0.05 刻みの較正(件数 / 実際に続いた割合)、順位分離(ブートストラップ SE)、閾値 0.5/0.6/0.7/0.8 の適合率と件数、Jev と logistic の一致(閾値 0.5)と順位相関、**§7.5.1 の「較正の良さ」= `scripts/o3c_signal_calib.py` の `calibration_goodness`(固定 20 帯、件数 20 未満の帯は外す)を Jev と logistic の両方に当て、`choose_better` の答え(jev / code)と外した帯を書く**、遅延 p50/p90/p99、入力トークン平均。基準率(後半の続く割合、この 5,000 件の続く割合)。
3. 報告 `docs/PHASE2/O3C/SIGNAL/STAGE2_REPORT_2026-09-20.md`: (0) 件数・呼び出し数・エラー数・経過 / (1) §0 の表 / (2) コマンド / (3) 設計に無い判断(全部)/ (4) サニティ(固定したものを変えていないことの確認 = 係数と切り値の MD5、問いの英文の sha256 が段 1 と同じ)/ (5) 限界 / (6) 作ったファイル / (7) テストの末尾行。**性能の数値は書かない。「表は data/jev/v4/stage2/tables.md」とだけ書く。**
4. 試験: 再開の冪等性、logistic の予測が定数ファイルだけから決まる、位置の切り替え、判定語なし。

## 3. 制約
read-only(入力を書き換えない)。既定値を変えるなら列挙して理由を書く。モデル名(Claude 等)を書かない。上に書いたファイル以外を変更しない。5,000 件を超えて呼ばない。
