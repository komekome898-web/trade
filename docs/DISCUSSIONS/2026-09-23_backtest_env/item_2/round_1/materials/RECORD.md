# 項目 2 第 1 周 資料係(表)の実行の記録

## どの表が何か(mapping.tsv と同じ)

| 表 | ファイル | 行 A | 行 B |
|---|---|---|---|
| current_1 | 表_az3umc.md | 新実装 | 当方の現状 |
| current_2 | 表_0pnhsh.md | 当方の現状 | 新実装 |
| survey_1 | 表_kfau3j.md | 新実装 | 調査結果の側(寄せた行) |
| survey_2 | 表_c5pwpg.md | 調査結果の側(寄せた行) | 新実装 |
| mutant_1 | 表_i6bjdn.md | 新実装 | 試金石 |
| mutant_2 | 表_qjqwvv.md | 試金石 | 新実装 |

## 走らせたもの

- 対象 45 件(`targets_list.tsv` = 新実装・当方の現状・試金石・調査結果の側 42 件)を `run_all.sh` でそれぞれ 2 回走らせた(1 回目 = `runs/`、2 回目 = `runs_2/`)。1 回の実行の中で各場面を別々のプロセスで 2 回走らせる(`run_battery.py`)。開始・終わりの時刻と所要は `run_log_part1.tsv`・`run_log_part2.tsv`・`run_log_part3.tsv`(同じ対象が複数の表にあるときは最後の行が表に使った実行)。
- 相手の道具の結果の再利用はしていない: 第 1 周で前の周が無い。全対象をこの周で走らせた。場面集の指紋は `fingerprint.txt`(資料係が adapter の本体を書いた後。表を作った後の `fingerprint_after.txt` も同じ値)。
- 新実装の adapter の本体を資料係が書いた(`tests/bt/battery/item_2/adapters/new_impl.py`。差分は `new_impl_adapter.diff`)。呼ぶのは公開の包み `bot.bt.core`・`orders`・`fill`・`latency`・`costs`・`portfolio` が `__all__` で出している名前だけ。場面の入力が開けたままにしている選択(fill_model が null のときの段 4、latency が null のときの遅延 0、sessions_jst の JST・平日、funding の event_mark ほか)は adapter の docstring に 1 か所で書いた。この選択は作業者の `tests/bt/item_2/i2_driver.py` の選択と同じ(同じ公開の口を読むと他に選びようが無かった。場面ごとの特別扱い・正解の読み込みは無い)。
- 試金石(`mutant.py`)は新実装の adapter を包むだけで、本体は変えていない。試験 `test_mutant_breaks_taker_fee_scenes_and_leaves_others` は通った(`pytest_item2_r1_shiryo_mutant.out`)。表の上で試金石は 5 場面(C2-10 の 4 つと C2-11 の 1 つ)で「不一致」、ほかは新実装と同じ。
- 場面集と作業者の場面の試験: `pytest_item2_r1_shiryo.out`(150 passed)。

## 調査結果の側の venv の入れ直し(他の役に消されていたもの)

周の始めに、`i2_targets.py` の venv のうち 14 件が無いか壊れていた(backtrader・zipline-reloaded・c103(interpreter の link 切れ)・c35_run・c107・c3・c87・fast-trade-r17・quantcore・luczinsritter・lib-pybroker・rqalpha・c37・c65)(`opponents/RUNNABILITY.tsv` に「他の役に消された」と記録のあるもの)。項目 0 の導入の記録(`tests/bt/battery/item_0/survey_results/attempts/*.log`)と同じ版・同じ commit で入れ直し、走らせた(記録: `logs/reinstall_venvs.log`・`logs/reinstall_venvs_3.log`、各導入の出力: `logs/i2_r1_shiryo_install_*.log`、台本: `reinstall_venvs.sh`・`reinstall_venvs_3.sh`)。入れた道具に渡したのは場面集の合成データだけ。

- ディスクの空きが 4 GB 弱しか無く、1 回目の一括の導入で空きが 776 MB まで下がった(空き 1200 MB を下回ったら打ち切る見張りで zipline-reloaded・c37・luczinsritter・c103 の導入を打ち切った)。そこで「入れる → 2 回走らせる → 消す」を 1 件ずつ回した(`reinstall_venvs_3.sh`)。このため、この周で入れ直した venv(backtrader・c103・c3/c87 の link を除く)は走らせた後に消してある。批評家が走らせ直すときは同じ台本で入れ直す。
- c3・c87: 項目 1 の資料係が同じ commit を取り直した venv(item_1/c3・item_1/c87)へ item_0/c3・item_0/c87 から symlink を張った。
- backtrader: 項目 0 の記録(attempts/2.log の「add pandas」)どおり pandas を足した。
- vnpy: 項目 1 の資料係が入れ直した venv に vnpy_ctastrategy が無く、最初の実行は全場面「対象を読み込めない」だった。項目 0 の記録(attempts/20.log)どおり `vnpy_ctastrategy==1.4.1 --no-deps` を足して走らせ直した。
- c103(Python 3.14 が要る): uv 0.8.17 の一覧に 3.14.7 が無く最初は失敗(rc=2、2 秒)。項目 0 の 3 回目の試し(attempts/103.log)どおり、補助の venv に新しい uv を入れて 3.14.7 を入れ、走らせた。
- c107(sigc。cargo で CLI を構築): **動かなかった**。試したこと: commit aa5f616f を取り出し、`cargo build -p sigc`(項目 0 は全体を構築して target が 2.0 GB)。開始 2026-09-25T20:23:42Z、空きが 1200 MB を下回って打ち切り 20:25:15Z(93 秒、エラー: polars-core の書き出しで容量不足、`logs/i2_r1_shiryo_install_c107.log`)。このため opp_sigc の 66 場面は「結果なし(実行が行を残さなかった: venv の python が無い)」。場面係の前の実行(survey_results/opp_sigc.tsv)でも、この道具は全場面「結果なし(公開の口に場面を渡す手段が無い)」で、正しさの欄は同じ。
- finmarketpy: venv はあるが、道具の import が `plotly.figure_factory._ohlc` の無いことで落ちる(66 場面「対象を読み込めない」)。場面係の前の実行と同じ。

## 確かめたこと

- `compare_runs.out`: 45 対象 × 66 場面 = 2970 行で、1 回の実行の中の 2 回の違い 0、1 回目と 2 回目の実行(runs と runs_2)の違い 0、場面係の survey_results との違い(正しさと観測の指紋)0(新実装と試金石は survey_results に無いので比べていない)。
- `recount.out`(make_tables.py を使わない、runs/*.tsv からの数え直し): 新実装 66 / 66 が正解と一致、66 / 66 が 2 回の実行で同じ。当方の現状 4 / 66(同じ 19)、試金石 61 / 66(同じ 66)、調査結果の側を寄せた行 38 / 66(同じ 49)。観点ごとの数も `table_counts.tsv` と一致。
- `recount_from_tables.out`(表の本文のセルから数え直し): 6 枚とも各観点と計の集計の行がセルと一致。
- `md5sum_pairs.txt`: 3 組とも 2 通りの表はバイト単位で違う(どの組も「同等」にはならない)。
- `check_names.out`: 6 枚の表に、道具の名前(対象の名・adapter の名・台帳の名の語・venv の名)・時刻・日付・commit の 16 進は 0 件。
- 道具ごと・場面ごとの結果と理由(道具の名前つき)は `survey_breakdown.tsv`。寄せた行でどの道具を選んだかは「picked」の列。
- 表_*.md はこの周の 6 枚のほかに無かった(round_1/ には materials/ だけがあった)。`materials/stale/` への移動は無し。
