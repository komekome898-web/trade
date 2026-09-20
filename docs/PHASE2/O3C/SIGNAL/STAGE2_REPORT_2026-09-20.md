# 段2(後半5,000件): Jev V1 + 前半で固定した logistic を一度だけ当てた報告(2026-09-20)

委任文: `docs/DATA/delegations/20260920_o3c_signal_v4_stage2_prompt.md`
設計: `docs/PHASE2/O3C/SIGNAL/SIGNAL_MATERIALS_DESIGN_2026-09-20.md` §7.4〜§7.6(特に §7.5.1)
段1: `docs/PHASE2/O3C/SIGNAL/V4_STAGE1_REPORT_2026-09-20.md`
反証者レビュー7: `docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW7_2026-09-20.md`(末尾の再確認・リードの処置まで読んだ)

**性能の数値(較正・的中・一致率・較正の良さ・順位分離など)はこの報告に一切書かない。**
表は `data/jev/v4/stage2/tables.md`(リポジトリに入れない)。**Do not commit. Do not push。**

## (0) 件数・呼び出し数・エラー数・経過

| 項目 | 値 |
|---|---|
| 選定(委任文の対象、`selection_manifest.json`) | 5,000 件(呼び出し順 = 選定順) |
| 位置の内訳 | 1件目 1,667 件・連鎖の中 3,333 件 |
| Jev 呼び出し数 | **5,000 回**(選定 5,000 件に 1 回ずつ。5,000 件を超えていない) |
| エラー数 | **0 件** |
| 再開で読み飛ばした件数 | 0 件(中断なく 1 回で完走) |
| 経過秒(logistic の予測計算 + Jev 5,000 回) | 2554.2 秒(logistic 43 秒を含む) |
| `answers.jsonl` の行数 / print_id の重複 | 5,000 行 / 重複 0 |
| `calls/calls_2026-09-20.jsonl` の行数(`JevClient` の呼び出しログ) | 5,000 行(`answers.jsonl` と一致) |

## (1) §0 の対応表(委任文どおり)

| やること | オーナーの原文の該当語(逐語) |
|---|---|
| 後半 5,000 件に Jev と code の logistic を並べて一度だけ当て、較正の良い方を方策の模擬に使う | 「**codeでの判断が勝てるならjevを使う意味はありません**」(L-321)、「**全てやってください。**」(L-323) |
| Jev の遅延を実測して記録する | 「**判断→注文のタイムロスは後々に成績直結します**」(L-321) |
| Jev の形は V1(前半で選んだ) | 設計 §7.5 の段 1 の結果を受けた決定(リード) |

## (2) コマンド

```
# 1. Jev V1 を 5,000 回・logistic の予測(再開可能。バックグラウンドで実行、約43分完走)
PYTHONPATH=src python3 scripts/o3c_signal_stage2.py --stage run

# 2. 表(answers.jsonl を読むだけ。data/jev/ にだけ置く)
PYTHONPATH=src python3 scripts/o3c_signal_stage2.py --stage tables

# 3. 全スイート
PYTHONPATH=src python -m pytest
```

## (3) 設計に無い判断(全部)

1. **道具の形**: 委任文は「`scripts/o3c_jev_state.py --stage second-half`(または新しい
   `scripts/o3c_signal_stage2.py`)」のどちらでもよいとしていた。既存の凍結済みコード
   (`o3c_jev_state.py`・`o3c_signal_logit.py`)に手を入れない形の方が「前半で固定した
   ものを一切変えない」の確認がしやすいと考え、**新しい `scripts/o3c_signal_stage2.py`
   を作り、`o3c_jev_state.py`・`o3c_signal_logit.py`・`o3c_signal_calib.py` は一切変更
   せず import だけした**(実際に diff が出ていないことは (4) の MD5 で確認)。
2. **表(`tables.md`)の「1 件目 / 連鎖の中 それぞれに」の適用範囲**: 設計 §7.5【作るもの】2
   は較正・順位分離・閾値ごとの適合率・一致・較正の良さ・遅延・入力トークンを列挙するが、
   「それぞれに」が遅延・入力トークンにも掛かるかは文面だけでは一意に決まらない。**両方
   出した**: 位置別(1 件目 / 連鎖の中)の遅延・入力トークンに加え、段1 の下見の表
   (`preview_tables.md`)の書式に揃えて「全 5,000 回」の合算も出した。
3. **0.01 刻みの較正表の作り方**: `scripts/o3c_signal_calib.py` は 0.05 刻み・20 本固定
   (「較正の良さ」の計算専用)しか実装しておらず、0.01 刻みの表は設計にも既存コードにも
   無い。`calibration_goodness` と同じ床関数の考え方(浮動小数の丸め対策込み)を
   `bin_width` をパラメータにして書き直した(`_bin_table`)。**§7.5.1 の「件数 20 未満は
   外す」規則は、設計上「較正の良さ」の値の計算にだけ課されたものと読み、この記述用の
   0.01/0.05 刻みの表には適用していない**(全帯をそのまま出す。件数の少ない帯がそのまま
   見える)。
4. **順位相関の方法**: 「Jev と logistic の…順位相関」としか書いておらず、方法の指定が
   無い。Spearman(`pandas.Series.corr(method="spearman")`)を使った(順位相関の標準的な
   読み方として)。
5. **Jev と logistic の一致・順位相関・較正の良さ(一致節)の対象**: 両方の確率が有限な
   行だけに絞って計算した(`jev_prob`・`logit_prob` の両方が欠測でない行)。実際には
   5,000 件とも両方とも欠測が無かったため、絞り込みの効果は無かった(§(4) で確認)。
6. **基準率の母集団**: 「後半の続く割合」は、材料の表(`rows_materials.csv.gz`)の
   `half=="後半"` の行(段1 の報告・反証者レビュー7 D3 と同じ、30,162 件)に `label_60`
   を結合したものとした。前段 `rows_continue.csv.gz` の生の後半行(52,707 件、欠測が多い
   ことをこの段2 の作業中に確認)ではなく、材料の表の screening を経た後半集団を使った
   (段1・反証者レビュー7 が既に使っている定義との一貫性のため)。
7. **再開の粒度**: `answers.jsonl` に既に記録がある `print_id`(成功・エラーを問わず)は
   Jev を呼び直さない実装にした。委任文は「再開可能に」としか書いておらず、エラーだった
   行を自動再試行するかは書いていない。**エラーが起きたときに際限なく呼び直す経路を
   作らない**ことを優先し、エラーも「1 回試みた」記録として扱った(実行では終始
   エラー 0 件だったので、この判断は実測には影響していない)。
8. **Jev クライアントの使い回し**: 段1 の `run_preview_v4` と同じ流儀で、5,000 回を通じて
   1 つの `JevClient(keep_alive=True)` を使い回し、実行の最後に 1 回だけ閉じた。

## (4) サニティ(固定したものを変えていないことの確認)

- **前半で固定した logistic の係数・切り値(経験分布)の MD5 は、段1 報告 (10) の表と
  実行の前後で完全に一致**(段2 は読むだけで、書き換わっていない):

  | ファイル | MD5(段1報告の値・今回の実測とも一致) |
  |---|---|
  | `scripts/o3c_signal_logit.py` | `c60fa4eae7ea6cb15be3f887cfd5ae76` |
  | `scripts/o3c_signal_calib.py` | `b7503692fe6829a42b2e276ad4c81862` |
  | `scripts/o3c_jev_state.py` | `8b710da4fef88cffaf74fb00f773dc50` |
  | `config/o3c_signal_logit_first.yaml` | `9bafb01d675272c97b2f9cf55c75402c` |
  | `config/o3c_signal_logit_chain.yaml` | `96ec0710a46bcb9b5ac0233182f0d9e9` |
  | `backtest_data/o3c_signal_materials_20260920/logit_ecdf_first.npz` | `0187fba59e3526a958582fc5f65327d3` |
  | `backtest_data/o3c_signal_materials_20260920/logit_ecdf_chain.npz` | `da24154bb12064af56a59ceb8b4a1959` |

  (`config/o3c_jev_state_bands.yaml` の MD5 も段2 の実行前後で不変。値自体は段1 報告に
  載っていないので比較表には入れていないが、この実行では読むだけで書き換えていない。)

- **問いの英文(`JEV_QUESTIONS_V1`)の sha256**: `scripts/o3c_jev_state.py` の MD5 が
  段1 報告の値と完全一致している(上表)ため、その中の `JEV_QUESTIONS_V1` はバイト単位で
  段1 と同一である(ファイルの MD5 が変わっていない以上、中の定数も変わりようがない)。
  今回改めて計算した値: `JEV_QUESTIONS_V1` を `json.dumps(..., sort_keys=True,
  ensure_ascii=False)` した文字列の sha256 = `12a339697bb3f9750336c2211cac5bc5b95a5604ef120fec4143c3e5c5549f09`。
- **`build_ecdf`(前半だけから経験分布を作る関数)は段2 の実行で 1 度も呼んでいない**こと
  を、`compute_logit_probs` が `load_ecdf_npz` → `apply_frozen_rank` だけを呼ぶ実装で
  あることをソースで確認し、`tests/test_o3c_signal_stage2.py` の
  `test_logit_probs_use_frozen_files_only_and_switch_by_position` で `build_ecdf` を
  スパイして呼び出し回数 0 を機械的に検査した(反証者7 D5)。
- **`answers.jsonl` は 5,000 行、print_id の重複 0、エラー 0、`jev_prob`・`logit_prob`・
  `label_60` の欠測 0**(すべて実測、コマンドは (2))。位置の内訳(1件目 1,667 / 連鎖の中
  3,333)は選定の層(`group` = `0` / `1-2` / `3+`)の件数(1,667 / 1,667 / 1,666)と、
  `1-2`+`3+` = 連鎖の中 という段1・反証者レビュー7 D3 と同じ対応で一致する。
- **`calls/calls_2026-09-20.jsonl` の行数(5,000)が `answers.jsonl` の行数と一致**
  (`JevClient` は呼び出しのたびに必ず 1 行ログを追記する実装であり、二重送信をしていない
  ことの状況証拠)。
- **判定語・`paper_logs/`**: `tests/test_o3c_signal_stage2.py` の
  `test_no_banned_words_in_source` / `test_no_banned_words_in_built_tables` /
  `test_source_never_opens_paper_logs` で機械的に検査(全スイートに含む、(7))。
  `data/jev/v4/stage2/tables.md` の生成自体も `check_no_banned` を通してから書いている
  (`o3c_signal_stage2.py: build_stage2_tables`)。

## (5) 限界

- **後半 5,000 件の層化(選定 `selection_manifest.json`)は「1 件目 : 連鎖の中」が
  33.3% : 66.7% で、後半全体の自然な比率(41.5% : 58.5%、反証者レビュー7 D3)からずれて
  いる。** 段2 は位置ごとに較正・順位分離などを分けて出しているのでこのずれは較正曲線
  そのものを歪めないが(D3 のリードの処置のとおり)、**「全 5,000 回」の合算(遅延・
  入力トークンの平均)は、自然な母集団比率で重み付けしていない**(単純平均)。
- **0.01 刻みの較正表(§(3)-3)は少数帯を外していない。** 帯によっては件数が 1 桁の
  ものがあり、実際に続いた割合の値そのものが不安定である(較正の良さの値の計算
  〈§7.5.1〉ではこの少数帯を外しているが、記述用の 0.01 刻み表では外していない)。
- **Jev と logistic の一致・順位相関・較正の良さ(一致節)を「両方の確率が有限」な行に
  絞る実装(§(3)-5)は、今回 5,000 件とも欠測が無かったため、絞り込みが実際に効いたかは
  検査していない**(合成データでの n=1 のケースはユニットテストで NaN の扱いを確認済み
  だが、実データでの欠測混在ケースは今回発生していない)。
- **基準率(§(3)-6)は材料の表(`rows_materials.csv.gz`)の screening を経た後半集団
  (30,162 件)を使っており、`rows_continue.csv.gz` の生の後半行(52,707 件、うち
  `label_60` 欠測 42.7%)全体には触れていない。** どちらを「後半」と呼ぶべきかは段1・
  反証者レビュー7 の用法を踏襲した選択であり、段2 独自に再検討していない。
- **遅延の実測はこの環境(TLS 接続込みの `keep_alive=True`)のものであり、オーナー PC
  からの遅延は未測定**(設計 §7.6 に既に明記されている限界の繰り返し)。
- **性能そのもの(較正・的中・一致・較正の良さの値・choose_better の答え)はこの報告には
  一切書いていない。** `data/jev/v4/stage2/tables.md` にだけ書いてある。

## (6) 作ったファイル

- `scripts/o3c_signal_stage2.py`(新規。段2 の本体: `load_selection`・`compute_logit_probs`・
  `run_stage2`・`build_stage2_tables`・`main`)
- `tests/test_o3c_signal_stage2.py`(新規、9 件: 再開の冪等性 2 件、logistic が定数
  ファイルだけで決まる/位置で切り替わる 2 件、`position_of` 1 件、記録される項目の検査
  1 件、判定語・`paper_logs` 3 件)
- `data/jev/v4/stage2/answers.jsonl`(5,000 行、数値、リポジトリ外)
- `data/jev/v4/stage2/tables.md`(数値、リポジトリ外)
- `data/jev/v4/stage2/run_notes.json`(件数・エラー数・経過秒、リポジトリ外)
- `data/jev/v4/stage2/calls/calls_2026-09-20.jsonl`(`JevClient` の呼び出しログ。state の
  本文は書かない仕様どおり、リポジトリ外)
- `docs/PHASE2/O3C/SIGNAL/STAGE2_REPORT_2026-09-20.md`(本書)

`docs/DATA/delegations/20260920_o3c_signal_v4_stage2_prompt.md` に書かれたファイル以外は
変更していない(`git status` で確認。`scripts/o3c_signal_policy.py`・
`tests/test_o3c_signal_policy.py`・`backtest_data/o3c_reaction_20260918_full/**` は本委任の
前から存在した未追跡ファイルで、今回変更していない)。

## (7) テストの末尾行(全スイート、`-q` 無し)

```
2761 passed, 5 skipped, 1 warning in 458.10s (0:07:38)
```

(段1 の末尾行 `2752 passed, 5 skipped, 1 warning in 456.57s` に対し、今回追加した
`tests/test_o3c_signal_stage2.py` の 9 件が増えている: 2752 + 9 = 2761。)
