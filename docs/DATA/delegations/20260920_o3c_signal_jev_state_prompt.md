# 委任: Jev に渡す状態を「トレーダーが言う英文の列」で組む code と、前半 200 件の下見(渡し方 3 通りの比較)(2026-09-20)

## 0. 対応表(CLAUDE.md §0.1)
| やること | オーナーの原文の該当語(逐語) |
|---|---|
| 材料を「Jev が判断できる言葉で書けるか」で選び、英文の列で渡す | 「**jevが判断しやすいような言葉かどうかが、材料の判断基準になるのでは？**」(L-308)、「**その基準と案で進めてください**」(L-309) |
| 問いは 1 つ(60 秒以内に同じ側の次の清算が来るか) | 「**清算を検知→jevでこの清算は続くか判断**」(L-262)、「**あなたはこの問いと材料を混同してませんか？**」(L-303) |
| 前半 200 件で渡し方 3 通りを比べてから後半へ | L-309 の承認(設計 §6.5 = L-308 の返答で示した手順) |
| 数値の結果は `data/jev/` にだけ | `docs/JEV.md` §4-7(リードの規則。§6.4 はオーナーの決定待ち) |

**出力はすべて日本語(code の文字列は英語)。判定語(陽性/陰性/有意/差あり/検出されず/支持/棄却)を書かない。`paper_logs/` を開かない。後半のプリントに Jev を呼ばない。Jev の確率・一致率・較正の数値はリポジトリに入るファイルに書かない(`data/jev/state_preview/` にだけ)。Do not commit. Do not push.**

## 1. 読むもの(順に)
設計 `docs/PHASE2/O3C/SIGNAL/SIGNAL_MATERIALS_DESIGN_2026-09-20.md` **§6 全部**(§6.2 の文の型 13 本と基準、§6.3 の問い、§6.5 の下見)/ 手引き `docs/JEV.md` §2・§4・§7 / 包み `scripts/jev/client.py`(版 `jev-1.13.0` 固定、鍵で答えを読む。SDK は使わない)/ 前段の Jev の呼び方 `scripts/o3c_signal_continue.py`(`jev_state_for_print`、`JEV_QUESTIONS`、`run_jev_preview` の層化抽出 = 同じ 200 件を使う)/ 試作 `docs/DATA/probes/20260920_o3c_jev_state_proto.py`(帯の境界の計算。ここから定数を起こす)/ 行データ `backtest_data/o3c_signal_materials_20260920/rows_materials.csv.gz`(候補 24 本。`cand_R1`・`cand_F5` は委任先 2 が足した列。無ければ止めて報告)と `backtest_data/o3c_signal_continue_20260920/rows_continue.csv.gz`(mat の生の列)、探索段 5 の `rows_prints.csv.gz`(`kind == print` の ts・side・notional)。約定は 60 秒の値幅・5 秒 / 10 秒 / 60 秒の変位・連鎖の開始からの値動きに要る(`o3c_signal_continue.py` の読み込みを流用)。

## 2. 作るもの
1. `scripts/o3c_jev_state.py`: (a) 帯の境界を**前半だけ**から計算して `config/o3c_jev_state_bands.yaml` に書く(五分位。1 か所の定数)/ (b) `build_state_sentences(print_id) -> list[str]` = 設計 §6.2 の文の型 13 本をそのまま(1 件目は 2 の 1 件目の文だけで 3・4・8・9 を書かない。欠測は "unknown")/ (c) `build_state_raw(print_id) -> dict` = 前段の `jev_state_for_print` から `price_path_bp_last_60s` を除いたもの(V3)/ (d) `--stage preview`: 前半 200 件(前段と同じ層化抽出・種)に V1(英文 + criteria)・V2(英文、criteria 無し)・V3(生の数 + 前段の criteria)を送り、答えを `data/jev/state_preview/answers.jsonl`(print_id・組・prob・input_tokens・latency)に記録。2 件/秒。
2. `tests/test_o3c_jev_state.py`: (1) 文の型が設計の 13 本と一致(合成の値で各文を手計算と比較。BUY / SELL の向きの語、1 件目で連鎖の行が無い、欠測 "unknown")/ (2) ts 以後を使わない(ts 以後の約定を変えても同じ文。**p₀ に当たる約定の価格を書き換えても同じ文**)/ (3) 帯の境界が前半だけから計算される(後半の値を変えても境界が同じ)/ (4) 同じ入力で同じ文(決定性)/ (5) `paper_logs/` を開かない / (6) 判定語が出力の markdown に無い。
3. 表(`data/jev/state_preview/tables.md`、**リポジトリに入れない**): 組ごとに 答えの 0.05 刻みの分布 / 前半のラベル(`label_60`)との一致(閾値 0.5)/ code の規則(`cand_1 >= 1` を「続く」)との一致 / 入力トークンの平均。
4. リポジトリに置くもの: `docs/PHASE2/O3C/SIGNAL/JEV_STATE_PREVIEW_2026-09-20.md` = 報告((0) 件数と呼び出し数 / (1) §0 の対応表 / (2) 実行したコマンド / (3) **state の実物 10 件**(単発 3・多件の最初 3・途中 2・最後 2、V1 の英文をそのまま)/ (4) 設計に無い判断(全部)/ (5) サニティ(未来を使わない検査、決定性、境界が前半だけ)/ (6) 限界 / (7) 作ったファイル / (8) テストの末尾行)。**性能の数値(一致率・分布)は書かない。「表は `data/jev/state_preview/tables.md`」とだけ書く。**

## 3. 制約
read-only(入力を書き換えない)・冪等・後半に触れない・Jev の呼び出しは 600 回だけ(超えるなら止めて報告)。既定値を変えるなら列挙して理由を書く。モデル名(Claude 等)を書かない。上に書いたファイル以外を変更しない。文の型を変えたくなったら止めて報告する(設計はオーナー承認済み)。
