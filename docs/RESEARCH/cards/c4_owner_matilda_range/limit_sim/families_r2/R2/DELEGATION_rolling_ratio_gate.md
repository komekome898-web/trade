# 委任文: マチルダの「走らせる前の期間だけから決める比の門」の実装(改良の周 2、2026-10-04)

あなたは本リポジトリの実装エージェントです。以下を実装し、報告してください。コミット・プッシュはしない。

## 着手前の表

やろうとすること × オーナーの原文の該当語(逐語)の 2 列を、着手前に報告の冒頭に出す。右が空の行は着手せず、問いとして返す(CLAUDE.md §0.1)。
該当するオーナーの原文: L-628「**ア では進めてください 測定ができるものが出来次第、測定用セッションを起こしてください。**」。
段取り(`docs/OWNER_STATUS.md` の L-627)の 2「比の門の境を走らせる前の期間だけから決め直す」は、知見台帳 `docs/RESEARCH/FINDINGS_LEDGER.md` のマチルダのカードの節「次に打てる手」にある(リードが書いた。オーナーの逐語ではない)。

## 読了必須(先頭から)

- `src/bot/research/matilda_limit_sim.py`(とくにモジュールの説明の族 D、`RATIO_GATES`、`_ratio`、`_ratio_ok`、`__init__` の検査)
- `scripts/w4_measure/c4_limit_run.py`・`scripts/w4_measure/c4_limit_batch.py`
- 既存の試験 `tests/research/` のうち matilda / c4 の名を含むもの(`ls tests/research | grep -i -e matilda -e c4`)

## 何を作るか

いまの比の門(`ratio_gate=12.96`)は、全期間の分の比の十分位の 7 番目の境(70% 点)で、走らせる期間と同じデータから決めた値(標本の中)。これを、**その時点より前のデータだけ**から決める門を足す。

1. `MatildaLimitSim` に引数 `ratio_gate_mode`(`"fixed"` 既定 = 今のまま / `"rolling"`)を足す。`rolling` のときの決まり:
   - 比の量は `_ratio(q)` と同じ(入りの判定で使う量)。**全部の分**(足ごとに q が作られる分。持ち高の有無・入ったかどうかに関係なく)の比を、UTC の日ごとに溜める。有限の値だけを溜める。
   - UTC の日 d の境は、日 d−365〜d−1(前の 365 日。その日を含まない)に溜めた比の 70% 点(`numpy.percentile(..., 70)` の既定の補間)。日 d の最初の足を処理する前に 1 回だけ計算し、その日の間は変えない。
   - 前の 365 日に溜めた日が 180 日未満のときは、その日は門を掛けない(v37 と同じに入る)。門を掛けなかった日の数を数える。
   - 入りの判定は今の `_ratio_ok` と同じ向き(比が境以上なら入らない。比が無限なら入らない)。
   - 先読みをしない: その日とそれより後の比は、その日の境に入れない。これを試験で示す(下)。
2. `rolling` は `ratio_gate` と同時に指定させない(どちらか 1 つ)。`ratio_gate_mode="rolling"` の値の表を `RATIO_GATE_MODES = ("fixed", "rolling")` のように置き、表の外の値は既存の `_in` と同じに拒む。
3. `c4_limit_run.py` に `--ratio-gate-mode rolling` を足す。既定の走らせの summary.json・run_record.json の引数の欄は今と変えない(既存の `--ratio-gate` と同じ扱い。指定したときだけ kw に入れる)。summary.json に、日ごとの境の要約(年ごとの境の最小・中央・最大、門を掛けなかった日の数)を `ratio_gate_rolling` の鍵で出す。
4. `c4_limit_batch.py` に改良の周 2 の走らせの一覧を足す(名前 `R2_...`、族 `"R2"`、良い側・悪い側の両方)。`--r2` の引数で、この一覧だけを走らせる(既存の一覧の走らせ方は変えない)。一覧(この 3 変種 × 2 側 = 6 本。**追加禁止**):
   - `R2_ratio_gate12.96_center_4_3` = `--ratio-gate 12.96 --exit-form center --entry 4 --exit-setting 3`
   - `R2_ratio_gate_rolling` = `--ratio-gate-mode rolling`
   - `R2_ratio_gate_rolling_center_4_3` = `--ratio-gate-mode rolling --exit-form center --entry 4 --exit-setting 3`
   `analyse()` は今のまま全部の走らせに当てる。

## 試験(新しく足す。件数を報告)

- 先読みが無い: 合成の足の列で、日 d の境が日 d とそれより後の比に依らないこと(後ろの日の比を極端に変えても日 d の境と入りが変わらない)。
- 180 日未満は門なし: 履歴が短い間の入りが v37(門なし)と同じ。
- 境の値: 合成の比で、70% 点が `numpy.percentile` と一致する。
- 既定(`ratio_gate_mode` を渡さない)の挙動が今と同じ: 既存の試験が全部通ること。
- `rolling` と `ratio_gate` の同時指定、表の外の値を拒む。
- `c4_limit_batch.py --r2 --list` が 6 本を出す。

## 実走の確かめ

`PYTHONPATH=src python3 scripts/w4_measure/c4_limit_run.py --fill-side good --ratio-gate-mode rolling --start 2017-01-01T00:00:00Z --end 2017-03-01T00:00:00Z --out <scratchpad>/smoke_r2` を 1 回だけ走らせ、summary.json の `ratio_gate_rolling` と取引の数を報告に貼る。全期間の走らせはしない(測定はリードが別に起こす)。出力は scratchpad に置き、リポジトリに置かない。

## テスト

`PYTHONPATH=src python -m pytest tests/research`(`addopts = "-q"` があるので `-q` を足さない)を回し、結果の末尾の行を報告に貼る。

## 差分・禁止

- 最小の差分。無関係な整形・改名・作り替えをしない。既定値を変えない。
- 取引の記録: 測定台本は 1 回の実行ごとに `trades.json.gz` を出す(今の c4_limit_run.py がすでに出している。壊さない)。
- 封印の境(2023-12-18)より後のデータを読まない(`load_bars` の門をそのまま使う)。
- コード・コメント・ログ・文書にモデル名を書かない。
- 結果の読み・判定・「効く/効かない」の言葉を書かない(分析はリード)。
- Do not commit. Do not push.

## 報告(この順)

1. 着手前の表 2. 変えたファイルと行 3. 足した試験と件数 4. pytest の末尾の行 5. 実走の確かめの出力 6. 迷った点と、決めた理由(委任文に無い判断をしたら全部書く)

終わる条件: 上の 1〜4 ができ、試験が通った。上限: 作業 1 回(差し戻しは 1 回まで)。
