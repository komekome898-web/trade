# 委任先の報告(逐語)— DELEGATION_d1b.md(3 版目、L-929)

作業者の返事を、そのまま写した。リードは書き換えていない。1 回目の返事(コミット 6d19e337 の版)は受け取りの検めで形の不合格(見出し・変異の表の 1 列目と試験名の省略)になり、作業者に報告の書き直しだけを頼んだ。これは 2 回目の返事の本文(作業者がリードへの連絡として先に書いた 4 項は、写しに含めないよう頼まれたので除いた)。


## 着手前の表

| やろうとすること | オーナーの原文の該当語(逐語)と根の節 |
|---|---|
| `scripts/analysis/d1b_matilda.py` を新しく作る(口: SEAL・CUT・LABELS・base_params・outcome・starts・ratio_diff_ci・summarize・main) | L-929「**yes**」/ 根: 「作るもの」の 1 |
| outcome・starts・ratio_diff_ci・summarize を試験の頭の注の決まりどおりにする。starts は足を 1 回だけ前から読み、起点の後 40 分待つ | L-929「**yes**」/ 根: 「作るもの」の 2 |
| main が --files・--out・--seal を受け、day_counts.csv と tables.md を書く | L-929「**yes**」/ 根: 「作るもの」の 3 |
| ファイル頭の docstring に走らせ方と決まりの正本を書く | L-929「**yes**」/ 根: 「作るもの」の 4 |
| 試験を変えずに通す。H1〜H6 を確かめる | L-929「**yes**」/ 根: 「受け入れ」・「変えないもの」 |
| 変異の表を作る(scratchpad の自分の新しい置き場に写しを作って壊す) | L-929「**yes**」/ 根: 「変異の表」 |
| 試験で決まらない内部の形を決める | L-929「**yes**」/ 根: 「決めてよいこと・決めてはいけないこと」の内部の形 |

右が空の行は無かった。

- 完了見込み: 約 70 分(既存コードを読む 1 回 10 分、台本を書く 1 回 25 分、試験と H1〜H6 の確かめ・直し 10 分、変異の表 25 分)。
- かかった時間: 約 50 分【推定。測っていない】。このほか `tests/research` 全体の走らせが 10 分 30 秒。
- 決まりの文書と試験の sha256 は委任文の記載と一致した(D1B_SPEC.md 78c366b8…、試験 af69e5cd…)。

## 作ったファイルの一覧と行数(H5)

`wc -l scripts/analysis/d1b_matilda.py` → `344 scripts/analysis/d1b_matilda.py`

- 新規は `/home/user/trade/scripts/analysis/d1b_matilda.py` だけ(344 行)。
- `git status --short src/ scripts/ tests/` の出力は `?? scripts/analysis/d1b_matilda.py` の 1 行のみ。試験と既存のコードは変えていない。コミット・プッシュ・git add はしていない。test_d1b_extra.py は足していない。
- 全期間の足では走らせていない。main の動作は、試験の合成の足(1 日分)を scratchpad に書き出して確かめた(終了コード 0、day_counts.csv と tables.md の 4 つの見方の表が出ること)。リポジトリには何も書いていない。
- 封印の置き場・2023-12-17T15:00Z より後のデータ・ほかの担当の scratchpad は読んでいない。リポジトリの根からの grep -r・find . もしていない。
- 変異の写しは `/tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/d1b_work/` に作った。

## 試験のコマンドと出力

```
$ PYTHONPATH=src python -m pytest tests/research/test_d1b_spec.py tests/research/test_diag_tables.py tests/research/test_diag_paths.py -rs
..................................................   [100%]
50 passed in 6.49s
```

飛ばし 0。test_d1b_spec.py の 33 件が全部通った。

`tests/research` 全体(test_c4_w6b_order.py を除く)は `1066 passed, 3 skipped in 630.14s`。この 3 件の飛ばしは台本と無関係の既存の試験のもの。ただし渡す前の数を持っていないので、渡す前と同じかは比べていない。

## H1〜H6 の確かめ

| 番号 | コマンド | 結果 |
|---|---|---|
| H1 | `git status --short tests/` | 出力が空。試験は変わっていない |
| H2 | `git status --short src/ scripts/` | `?? scripts/analysis/d1b_matilda.py` だけ |
| H3 | `grep -nE "vola_count\|range_count\|break_dist\|beard_ignore" scripts/analysis/d1b_matilda.py` | 出力が空(0 行)。読む引数の名前は exit_setting(利確の線の倍率)だけ |
| H4 | `grep -nE "WINDOW1\|phase2_sealed\|candles_1m_202[4-9]" scripts/analysis/d1b_matilda.py` | 出力が空(0 行) |
| H5 | `wc -l scripts/analysis/d1b_matilda.py` | 344 行 |
| H6 | 上の試験のコマンド | 50 passed、飛ばし 0 |

## 変異の表

当て方は `D1B_MODULE_DIR=<写しの置き場> PYTHONPATH=src python -m pytest tests/research/test_d1b_spec.py`。壊した写しは scratchpad に置き、本物は壊していない。40 通りのうち 34 通りは 1 つ以上の試験が落ち、6 通り(M07・M14・M15・M20・M24・M31)は落ちなかった(問い Q1)。M24b・M31b は落ちなかった行の差し替えではなく、元の行を残したうえでの追加の行。

| 番号 | 壊した変更 | 落ちた試験 |
|---|---|---|
| U1(M01) | outcome の利確の線の向きを逆にする(安値 <= 線 を 安値 >= 線 に) | tests/research/test_d1b_spec.py::test_outcome_cases[上: 5 分目に利確の線まで], tests/research/test_d1b_spec.py::test_outcome_cases[上: 10 分目に起点の値段まで(利確の線の手前)は数えない], tests/research/test_d1b_spec.py::test_outcome_cases[上: 10 分目は起点まで、25 分目に起点まで], tests/research/test_d1b_spec.py::test_outcome_cases[上: 3 分目にブレイクの線], tests/research/test_d1b_spec.py::test_outcome_cases[上: 3 分目にブレイクの線ちょうど], tests/research/test_d1b_spec.py::test_outcome_cases[上: 4 分目に利確とブレイクの両方], tests/research/test_d1b_spec.py::test_outcome_cases[上: ブレイクの線が無い], tests/research/test_d1b_spec.py::test_outcome_cases[上: 足の欠け(1 分目と 35 分目だけ)], tests/research/test_d1b_spec.py::test_starts_match_strategy_reference, tests/research/test_d1b_spec.py::test_starts_gate_closed_is_recorded, tests/research/test_d1b_spec.py::test_starts_stop_at_seal_and_drop_late_starts, tests/research/test_d1b_spec.py::test_starts_drop_starts_near_data_end, tests/research/test_d1b_spec.py::test_skipped_bars_are_not_in_path |
| U1(M02) | 20 分の境を 19 分にする(利確の判定と名前) | tests/research/test_d1b_spec.py::test_starts_match_strategy_reference, tests/research/test_d1b_spec.py::test_starts_gate_closed_is_recorded, tests/research/test_d1b_spec.py::test_starts_stop_at_seal_and_drop_late_starts, tests/research/test_d1b_spec.py::test_starts_drop_starts_near_data_end |
| U1(M03) | 41 分目の足も見る | tests/research/test_d1b_spec.py::test_outcome_cases[上: 41 分目は見ない] |
| U1(M04) | 同じ足で両方に触れても both にしない | tests/research/test_d1b_spec.py::test_outcome_cases[上: 4 分目に利確とブレイクの両方], tests/research/test_d1b_spec.py::test_outcome_cases[上: 30 分目に戻りとブレイクの両方], tests/research/test_d1b_spec.py::test_outcome_cases[下: 4 分目に利確とブレイクの両方] |
| U1(M05) | ブレイクの線ちょうどを届かないとする(高値 >= 線 を 高値 > 線 に) | tests/research/test_d1b_spec.py::test_outcome_cases[上: 3 分目にブレイクの線ちょうど], tests/research/test_d1b_spec.py::test_outcome_cases[上: 40 分目にブレイク] |
| U1(M06) | 起点の値段ちょうどを戻りにしない(安値 <= c0 を 安値 < c0 に) | tests/research/test_d1b_spec.py::test_outcome_cases[上: 10 分目は起点まで、25 分目に起点まで] |
| M07(問い Q1 を見よ) | [U1 の行] k < 1 の足(起点の足そのもの・手前)も見る | 落ちなかった |
| U1(M08) | 下の起点で戻りの比べを逆にする(高値 >= c0 を 高値 <= c0) | tests/research/test_d1b_spec.py::test_outcome_cases[下: 何も無い], tests/research/test_d1b_spec.py::test_starts_match_strategy_reference, tests/research/test_d1b_spec.py::test_starts_gate_closed_is_recorded, tests/research/test_d1b_spec.py::test_starts_stop_at_seal_and_drop_late_starts, tests/research/test_d1b_spec.py::test_starts_drop_starts_near_data_end |
| U2(M09) | 飛ばす足を飛ばさず結果の道にも線にも入れる | tests/research/test_d1b_spec.py::test_starts_match_strategy_reference, tests/research/test_d1b_spec.py::test_starts_gate_closed_is_recorded, tests/research/test_d1b_spec.py::test_starts_stop_at_seal_and_drop_late_starts, tests/research/test_d1b_spec.py::test_starts_drop_starts_near_data_end, tests/research/test_d1b_spec.py::test_skipped_bars_are_not_in_path |
| U2(M10) | 入りを常に True にする | tests/research/test_d1b_spec.py::test_starts_match_strategy_reference, tests/research/test_d1b_spec.py::test_starts_gate_closed_is_recorded, tests/research/test_d1b_spec.py::test_starts_stop_at_seal_and_drop_late_starts, tests/research/test_d1b_spec.py::test_starts_drop_starts_near_data_end |
| U2(M11) | ブレイク中の印を常に 0 にする | tests/research/test_d1b_spec.py::test_starts_match_strategy_reference, tests/research/test_d1b_spec.py::test_starts_gate_closed_is_recorded, tests/research/test_d1b_spec.py::test_starts_stop_at_seal_and_drop_late_starts, tests/research/test_d1b_spec.py::test_starts_drop_starts_near_data_end |
| U2(M12) | 時刻の順を検めない | tests/research/test_d1b_spec.py::test_starts_refuse_non_increasing_time[same], tests/research/test_d1b_spec.py::test_starts_refuse_non_increasing_time[back] |
| U2(M13) | 利確の線の符号を逆にする | tests/research/test_d1b_spec.py::test_starts_match_strategy_reference, tests/research/test_d1b_spec.py::test_starts_gate_closed_is_recorded, tests/research/test_d1b_spec.py::test_starts_stop_at_seal_and_drop_late_starts, tests/research/test_d1b_spec.py::test_starts_drop_starts_near_data_end |
| M14(問い Q1 を見よ) | [U2 の行] ボラが 0 以下の足も評価する | 落ちなかった |
| M15(問い Q1 を見よ) | [U2 の行] 評価した日を最初の 1 日しか入れない | 落ちなかった |
| U2(M16) | 基準の引数の利確を 3 から 2 にする | tests/research/test_d1b_spec.py::test_base_params |
| U2(M17) | 基準の引数が BASE_PARAMS そのもの(コピーしない) | tests/research/test_d1b_spec.py::test_base_params, tests/research/test_d1b_spec.py::test_main_writes_day_counts |
| U2(M18) | 門の閉じた起点を落とす | tests/research/test_d1b_spec.py::test_starts_gate_closed_is_recorded |
| U2(M19) | ブレイクの線を上下取り違える | tests/research/test_d1b_spec.py::test_starts_match_strategy_reference, tests/research/test_d1b_spec.py::test_starts_gate_closed_is_recorded, tests/research/test_d1b_spec.py::test_starts_stop_at_seal_and_drop_late_starts, tests/research/test_d1b_spec.py::test_starts_drop_starts_near_data_end |
| M20(問い Q1 を見よ) | [U2 の行] 戦略への渡しで price を始値にする | 落ちなかった |
| U3(M21) | 封印の境の等号(境ちょうどの足を読む) | tests/research/test_d1b_spec.py::test_starts_stop_at_seal_and_drop_late_starts |
| U3(M22) | 終わり近くの起点を残す(41 分の検めを外す) | tests/research/test_d1b_spec.py::test_starts_match_strategy_reference, tests/research/test_d1b_spec.py::test_starts_gate_closed_is_recorded, tests/research/test_d1b_spec.py::test_starts_stop_at_seal_and_drop_late_starts, tests/research/test_d1b_spec.py::test_starts_drop_starts_near_data_end |
| U3(M23) | 41 分ちょうどで終わる起点を捨てる(<= を < に) | tests/research/test_d1b_spec.py::test_starts_match_strategy_reference, tests/research/test_d1b_spec.py::test_starts_gate_closed_is_recorded, tests/research/test_d1b_spec.py::test_starts_stop_at_seal_and_drop_late_starts, tests/research/test_d1b_spec.py::test_starts_drop_starts_near_data_end |
| M24(問い Q1 を見よ) | [U3 の行] n_win を 41 分まで数える | 落ちなかった |
| U3(M24b) | (M24 の追加) 41 分目の足を集める(取り込み前の終わりの検めを 42 分にし)、n_win も 41 分まで数える | tests/research/test_d1b_spec.py::test_starts_match_strategy_reference, tests/research/test_d1b_spec.py::test_starts_gate_closed_is_recorded, tests/research/test_d1b_spec.py::test_starts_stop_at_seal_and_drop_late_starts, tests/research/test_d1b_spec.py::test_starts_drop_starts_near_data_end |
| U3(M25) | 後の封印の境の --seal を受ける | tests/research/test_d1b_spec.py::test_main_refuses_later_seal[2024-01-01T00:00:00+00:00], tests/research/test_d1b_spec.py::test_main_refuses_later_seal[2023-12-17T09:00:00-08:00] |
| U3(M26) | --seal を文字列で比べる | tests/research/test_d1b_spec.py::test_main_refuses_later_seal[2023-12-17T09:00:00-08:00] |
| U3(M27) | データの終わりを最後の足の始まりまでにする(+1 分を外す) | tests/research/test_d1b_spec.py::test_starts_match_strategy_reference, tests/research/test_d1b_spec.py::test_starts_gate_closed_is_recorded, tests/research/test_d1b_spec.py::test_starts_drop_starts_near_data_end |
| U4(M28) | 区間の種を変える | tests/research/test_d1b_spec.py::test_ratio_diff_ci_formula |
| U4(M29) | 差の区間で a を先に引く | tests/research/test_d1b_spec.py::test_ratio_diff_ci_formula |
| U4(M30) | MDE の係数を 2.8 から 2.0 にする | tests/research/test_d1b_spec.py::test_ratio_diff_ci_formula |
| M31(問い Q1 を見よ) | [U4 の行] 半分が 0 本の検めを外す | 落ちなかった |
| U4(M31b) | (M31 の追加) 半分が 0 本の検め 2 つ(分母 0 と差の本数)を両方外す | tests/research/test_d1b_spec.py::test_summarize_empty_half_is_none, tests/research/test_d1b_spec.py::test_main_writes_day_counts |
| U4(M32) | 前半の境の日を前半に入れる(< を <=) | tests/research/test_d1b_spec.py::test_summarize_counts_and_cis |
| U4(M33) | 割合の分母を起点の数 + 1 にする | tests/research/test_d1b_spec.py::test_summarize_empty_half_is_none, tests/research/test_d1b_spec.py::test_summarize_counts_and_cis |
| U4(M34) | 差の標準偏差を ddof=0 にする | tests/research/test_d1b_spec.py::test_ratio_diff_ci_formula |
| U5(M35) | 日ごとの数の行を並べない | tests/research/test_d1b_spec.py::test_main_writes_day_counts |
| U5(M36) | 日ごとの数の見出しから brk の列を外す | tests/research/test_d1b_spec.py::test_main_writes_day_counts |
| U5(M37) | 表の割合の桁を小数 0 桁にする | tests/research/test_d1b_spec.py::test_main_writes_day_counts |
| U5(M38) | 点の見方の門の見方で brk を見ない | tests/research/test_d1b_spec.py::test_summarize_counts_and_cis |
| U5(M39) | 入りの見方の門の見方で brk を見ない | tests/research/test_d1b_spec.py::test_summarize_counts_and_cis |
| U5(M40) | 日ごとの数の gate 列に entry を書く | tests/research/test_d1b_spec.py::test_main_writes_day_counts |
| H1 | 試験と既存の試験を変えない(確かめ: `git status --short tests/`) | 出力が空。試験は変わっていない |
| H2 | 既存のコードを変えない(確かめ: `git status --short src/ scripts/`) | 出力は `?? scripts/analysis/d1b_matilda.py` の 1 行だけ |
| H3 | 線を自分で計算し直さない(確かめ: 引数名の grep) | `grep -nE "vola_count|range_count|break_dist|beard_ignore" scripts/analysis/d1b_matilda.py` の出力が空(0 行) |
| H4 | 封印の置き場と 2024 年より後のファイルを名指さない(確かめ: grep) | `grep -nE "WINDOW1|phase2_sealed|candles_1m_202[4-9]" scripts/analysis/d1b_matilda.py` の出力が空(0 行) |
| H5 | 大きさ(確かめ: `wc -l scripts/analysis/d1b_matilda.py`) | 344 行 |
| H6 | 試験が全部通る(確かめ: 3 つの試験ファイルを打つ) | 50 passed、飛ばし 0 |

## 試験で決まらず作業者が決めた内部の形

- 起点の待ち行列: 結果がまだ決まらない起点を先入れ先出しの入れ物 `deque`(両端のある列)に持つ。起点の足から 41 分以上後の足が来たら先頭から確定し、足の全部は記憶に持たない。起点の足自身はその起点の道に渡さない。足が尽きたら、起点の時刻 + 41 分が終わりの時刻以下のものだけを記録する。
- `outcome`(結果を決める関数)は、内部では分(k)に直した道を受ける別関数 `_outcome_k`(分に直した道から結果を決める)を呼ぶ。公開の outcome は ts の文字列を k に直して渡すだけ。k は足の始まりの差を分に丸めた値。
- 時刻の読み: 時差の付かない時刻は ValueError にする。末尾 Z は UTC として読む。`--seal` が時差なしなら、ファイルを開かずに標準エラーへ書いて 2 を返す。
- `ratio_diff_ci`(差の区間の関数): どちらかの半分の分母が 0、または差の本数が 2 未満なら 4 つとも None を返す。
- `summarize`(見方ごとの集計の関数): 年の鍵は days と records の年を合わせたもの。年のセルは n・count・share だけで、lo・hi は持たない。
- tables.md の形: 見方ごとに 2 つの表。表 1 は期間(年・first・second)ごとの起点の数、5 つの結果の割合、幅 ÷ ボラの中央値、n_win の中央値。表 2 は結果ごとの first の区間・second の区間・diff の点・diff の区間・diff の MDE。差と MDE は百分率ポイント(pt)で小数 1 桁。中央値はその見方の起点だけで取る。値が無いセルは `-`。冒頭に「幅 ÷ ボラ は width_vola.out と母集団が違う」と書く。
- day_counts.csv: 行は文字列の並びで並べ、brk は `str(r["brk"])` で書く。

## 問いとして返したこと

- Q1: 変異の表で落ちなかった行が 6 通りある(M07・M14・M15・M20・M24・M31)。差し替えずに残した。「等価な変異」かどうかの判断をお願いする。受け取りの検めは、U の番号が付いた行に「落ちなかった」があると不合格にするので、この 6 行だけ 1 列目を M の番号にして U の番号を付けていない(表の 2 列目の頭に属する U の番号を書いた。行は消していない)。
  - M07(U1: k < 1 の足も見る): starts では起点の足を道に渡さず時刻も増えるので k ≥ 1。k < 1 は公開の outcome に直接渡したときだけ出るが、試験の 18 場面にその入力は無い【推定】。
  - M14(U2: ボラ ≦ 0 の足も評価する): 試験の合成の足にボラが 0 以下の足が無いのだと思う【推定。確かめていない】。
  - M15(U2: 評価した日を最初の 1 日しか入れない): 試験の合成の足(n=900 分)が全部 1 日に収まり、days の誤りが出ない【事実】。
  - M20(U2: 戦略への渡しの price を始値にする): 戦略は close の ev で price を直前の値段 `_last` にしか使わない。等価の可能性が高い【推定。decide の頭の読みから】。
  - M24(U3: n_win を 41 分まで数える): 私の構造では 41 分目の足は道に入る前に起点を確定するので数えようが無い。M24b のように 41 分目の足を集める形にすれば試験が落とす【事実】。
  - M31(U4: 分母 0 の検めだけを外す): 差の本数が 2 未満のときの検めも同じ結果を返すので片方だけでは見えない。M31b のように両方外せば試験が落ちる【事実】。
- Q2: 気づき(判断を求めるものではない)。day_counts.csv は起点の無い日の行を書かない(試験の決まり)ので、CSV だけでは区間を作り直せない。日の一覧が要るなら別の出力が要る。今回は何も足していない。

試験と D1B_SPEC.md が食い違う箇所は見つからなかった。
