# 項目 1 第 1 周 資料係(表)の実行の記録 — 作り直し(監査役(表)の指摘を受けた 1 回だけの作り直し)

## どの表が何か(mapping.tsv と同じ。ファイル名は前の版と同じものを使った)

| 表 | ファイル | 行 A | 行 B |
|---|---|---|---|
| current_1 | 表_t3iayt.md | 新実装 | 当方の現状 |
| current_2 | 表_e7a6km.md | 当方の現状 | 新実装 |
| survey_1 | 表_daka83.md | 新実装 | 調査結果の側(寄せた行) |
| survey_2 | 表_v1fm0q.md | 調査結果の側(寄せた行) | 新実装 |
| mutant_1 | 表_z7pngl.md | 新実装 | 試金石 |
| mutant_2 | 表_n4uatt.md | 試金石 | 新実装 |

## 直したこと

1. [止める] adapter の root と path の二重結合: `tests/bt/battery/item_1/adapters/new_impl.py` の `_load` は、runner が渡す `root` と場面の `paths` をそのまま `bot.bt.data.load(root, datasets)` に渡す(`os.path.abspath`・`os.path.join` を消した)。sha256 の記録は `LoadResult.hashes()`(渡した path がそのまま鍵)をそのまま返す。差分は `new_impl_adapter.diff`(前の版 ae9eb44 との差)。相対の path を root に対して解くのはデータ層自身(`src/bot/bt/data/allowlist.py` の `AllowList.check`: `os.path.join(root_abs, path)`)。
2. [直す] 「結果なし」の注記: `make_tables.py` の注記に、実際に試したこと(場面の入力を対象の公開の口に渡し、別々のプロセスで 2 回)と、出たエラーの文を逐語で書くようにした。道具を特定できる語(ASCII の名前・path・時刻、「現状」「再現」と道具の種類の語)は `〔名〕`・`〔時刻〕` に置き換える(`redact`)。置き換える前の逐語は `runs/*.tsv` と `survey_breakdown.tsv` にある。調査結果の側の寄せた行で全対象が結果なしの場面は、14 対象それぞれのエラーの文を同じ文ごとにまとめて件数つきで書いた。

## 走らせたもの

- 対象 17 件(`targets_list.tsv`)を 2 通りの `--out` で、それぞれ 2 回ずつ走らせた。1 回の実行の中で各場面を別々のプロセスで 2 回走らせる(`run_battery.py`)。
  - 相対の `--out`(`run_battery.py` の冒頭の使用例の形): `logs/relative_out_all_targets/`(runs・runs_2・run_log.tsv・run_all.sh・標準出力)。
  - 絶対の `--out`(表の元): `runs/`・`runs_2/`、`run_log.tsv`、`run_all.sh`。
- 2 通りの突き合わせ(`compare_relroot.out`): 1190 行のうち違いは 2 行だけで、どちらも当方の現状の `v5-sealed-window`(絶対 = 正解と一致、相対 = 結果なし `SealedDataError: backtest_data/bf_exec_sealtest_20260105/trades.csv is not one of unit 'SYNTH-UNIT''s sealed files`)。新実装は 2 通りとも 35 場面の全部が同じ(正しさと要約)。当方の現状の違いの原因は、場面集の `i1_protocol.dataset_paths` が「Absolute paths」と書きながら `os.path.join(root, p)` を返す(root が相対なら相対)ことと、当方の現状の adapter がそれを `sealed.load_unsealed(path, unit, root=root)` に渡して root が二重に付くこと(場面集の側のファイルなので資料係は変えていない)。**表は絶対の `--out` の実行から作った**(当方の現状に、場面集の側の path の扱いで失う結果を出さないため。新実装はどちらでも同じ)。
- 相手の道具の結果の再利用はしていない(全対象をこの作り直しで走らせ直した)。場面集の指紋は `fingerprint.txt`。
- 調査結果の側の venv 12 件は全部あった(入れ直しは無し)。入れた道具に渡したのは場面集の合成データだけ。
- 前の版の実行・表・記録は `logs/previous_build_abs_root/` に移した(前の版の 6 枚の表の写しを含む)。前の版の最初の試み(相対の `--out` で新実装が 26 場面 PathRefused)は `logs/first_attempt_relative_root/` のまま。

## 確かめたこと

- `compare_runs.out`: 17 対象 × 35 場面 = 595 行で、1 回の実行の中の 2 回の違い 0、1 回目と 2 回目の実行(runs と runs_2)の違い 0、場面係の survey_results との違い 0。
- `recount.out`(make_tables.py を使わない数え直し、runs と runs_2 の生の tsv から): 新実装 35 / 35、当方の現状 2 / 35(V2 1・V5 1)、試金石 32 / 35(V1 7/9・V2 2/3)。
- `recount_from_tables.out`(表の本文のセルから数え直し): 6 枚の各行 A・B の観点ごとの数が表の集計の行と一致(不一致 0)。
- `recount_survey.out`(寄せた行を make_tables.py を使わずに作り直した数え): 正解と一致 4(V6 1・V7 3)、2 回の実行で同じ 10。表と一致。観点ごとの全対象 × 全場面の正しさの内訳も出した(V3 は 70 のうち 不一致 5・対応なし 3・結果なし 62、V5 は 98 の全部が結果なし)。
- `md5sum_pairs.txt`: 3 組とも 2 通りの表はバイト単位で違う。
- `check_names.out`(`check_names.py`): 6 枚の表に、道具・モジュール・関数の名前 52 語と時刻、注記の行の「現状」「再現」と道具の種類の語は 0 件。
- `pytest_item1_r1_shiryo.out`: `tests/bt/battery/item_1 tests/bt/item_1` で 3969 passed / 1 failed。落ちたのは前の版と同じ `test_new_impl_is_the_mouth_only`(adapter の本体が空であることを確かめる試験。資料係が本体を書くと必ず落ちる。今回は root の無い入力を渡すので `KeyError: 'root'`。場面集の試験は資料係が変えない)。
