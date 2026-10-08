# 委任先の報告(逐語)— DELEGATION_s1.md(3 版目、L-823)

作業者の返事を、そのまま写した。リードは書き換えていない。1 回目の返事は受け取りの検めで形の不合格(変異の表の試験名の省略・着手前の表の番号の位置)になり、作業者に報告の書き直しだけを頼んだ。これは 2 回目の返事。

## 着手前の表

| やろうとすること | オーナーの原文の該当語(逐語)と根の節 |
|---|---|
| 新しい包み `src/bot/bt/simple/` を作り、`run, read_bars, check_numbers, SimpleRoadError` を読めるようにする | L-823「**yes**」/ 根: 「作るもの」の 1 |
| 約定の関数を SPEC.md §2・§3 のとおりに作る | L-823「**yes**」/ 根: 「作るもの」の 2 |
| 走らせ `run` を作る(約定 → 知らせ → 判定、止める場面は `SimpleRoadError`) | L-823「**yes**」/ 根: 「作るもの」の 3 |
| `read_bars` を作る(値段の空の足を飛ばし、封印の境の行で終わり、境の年より後のファイルは開かずに止める) | L-823「**yes**」/ 根: 「作るもの」の 4 |
| 残し方を作る(orders・fills・signals・run の各ファイルを書き足し、最後に `book` で trades・summary を作る) | L-823「**yes**」/ 根: 「作るもの」の 5 |
| `check_numbers` を作る(`book` で約定から計算し直し、書いた数と比べる) | L-823「**yes**」/ 根: 「作るもの」の 6 |
| 試験 `tests/simple/test_s1_spec.py` と `tests/road` を通す | L-823「**yes**」/ 根: 「受け入れ」・「終わる条件と上限」 |
| 変異の表を作り(tmp の写しで壊して試験が落ちるのを見る)、H1〜H5 の確かめを打つ | L-823「**yes**」/ 根: 「変異の表」・「変えないもの」 |

右が空の行は無かった。

## 作ったファイルの一覧と行数(H5)

`wc -l src/bot/bt/simple/*.py`

```
  7 __init__.py   48 bars.py   49 check.py   64 common.py   82 fills.py   224 run.py   474 total
```

- `__init__.py`: 口の再公開。
- `common.py`: 止める場面の型・時刻の読み・数の書き方・刻みへの切り捨て・量の刻みの検め。
- `bars.py`: `read_bars`。
- `fills.py`: 注文の状態 `Order` と約定の関数 `fill_bar`。
- `run.py`: `run`・注文の形の検め・参照の検め・合図の扱い・ファイルの書き足し。
- `check.py`: `check_numbers`。

## 試験のコマンドと出力

`PYTHONPATH=src python -m pytest tests/simple tests/road` → `365 passed in 21.22s`

`PYTHONPATH=src python -m pytest tests/simple -rs` → `50 passed in 1.10s`(飛ばし 0)

## H1〜H5 の確かめ

- H1: `git diff --stat tests/` → 空。tests/ の既存ファイルは変更なし、`tests/simple/test_s1_extra.py` も作っていない。
- H2: `git diff --stat src/` → 空。`git status --short -uall src/ tests/` → `?? src/bot/bt/simple/` の 6 ファイルだけ。
- H3: `grep -rn "bot.bt.fill\|bot.bt.core\|bot.bt.road.strategy\|bot.bt.pipeline" src/bot/bt/simple/` → 出力なし(終了コード 1)。import は標準ライブラリと `bot.bt.road.ledger`(`book`・`LedgerError`)だけ。
- H4: `PYTHONPATH=src python -m pytest tests/road` → `315 passed in 17.94s`。
- H5: 上の行数。合計 474 行。

モデル名の grep (`claude|sonnet|opus|haiku|gpt`、大文字小文字を区別しない) → 該当なし。

## 変異の表

壊した変更は `<scratchpad>/mut_src`(src の写し)にだけ当てた。本物の src は壊していない。全行を写しでもう一度当て直し、落ちた試験を 1 つずつ書いた(今回の当て直しで、前回と同じ結果になった)。

注意: `pyproject.toml` の `pythonpath = ["src"]` が先に効くので、写しを当てるには `PYTHONPATH` だけでなく `-o pythonpath=<写し>` が要る。最初の 1 回目は全部「落ちなかった」と出たが、これはこの指定漏れが原因で、指定し直して全部やり直した。

| 番号 | 壊した変更 | 落ちた試験 |
|---|---|---|
| U1a | 段を根の足(anchor_bar)で約定させない | `tests/simple/test_s1_spec.py::test_t1_levels_from_root_fill[optimistic]`, `tests/simple/test_s1_spec.py::test_t1_levels_from_root_fill[pessimistic]`, `tests/simple/test_s1_spec.py::test_t2_sell_level_floored[optimistic]`, `tests/simple/test_s1_spec.py::test_t2_sell_level_floored[pessimistic]`, `tests/simple/test_s1_spec.py::test_t2_decimal_sum[optimistic]`, `tests/simple/test_s1_spec.py::test_t2_decimal_sum[pessimistic]`, `tests/simple/test_s1_spec.py::test_t4_exit_on_level` |
| U1b | 段の値段を約定値段 F でなく根の注文の値段から出す | `tests/simple/test_s1_spec.py::test_t1_levels_from_root_fill[optimistic]`, `tests/simple/test_s1_spec.py::test_t1_levels_from_root_fill[pessimistic]`, `tests/simple/test_s1_spec.py::test_t2_buy_level_floored[optimistic]`, `tests/simple/test_s1_spec.py::test_t2_buy_level_floored[pessimistic]`, `tests/simple/test_s1_spec.py::test_t2_sell_level_floored[optimistic]`, `tests/simple/test_s1_spec.py::test_t2_sell_level_floored[pessimistic]`, `tests/simple/test_s1_spec.py::test_t2_decimal_sum[optimistic]`, `tests/simple/test_s1_spec.py::test_t2_decimal_sum[pessimistic]`, `tests/simple/test_s1_spec.py::test_t4_exit_on_level`, `tests/simple/test_s1_spec.py::test_t9_level_and_exit_open_on_later_bar[optimistic]`, `tests/simple/test_s1_spec.py::test_t9_level_and_exit_open_on_later_bar[pessimistic]` |
| U1c | 根の足で、段が範囲の外でも段の値段で約定させる | `tests/simple/test_s1_spec.py::test_t1_levels_from_root_fill[optimistic]`, `tests/simple/test_s1_spec.py::test_t1_levels_from_root_fill[pessimistic]`, `tests/simple/test_s1_spec.py::test_t2_buy_level_floored[optimistic]`, `tests/simple/test_s1_spec.py::test_t2_buy_level_floored[pessimistic]`, `tests/simple/test_s1_spec.py::test_t9_level_and_exit_open_on_later_bar[optimistic]`, `tests/simple/test_s1_spec.py::test_t9_level_and_exit_open_on_later_bar[pessimistic]` |
| U2a | 切り捨てを切り上げ(ROUND_CEILING)にする | `tests/simple/test_s1_spec.py::test_t1_levels_from_root_fill[optimistic]`, `tests/simple/test_s1_spec.py::test_t1_levels_from_root_fill[pessimistic]`, `tests/simple/test_s1_spec.py::test_t2_buy_level_floored[optimistic]`, `tests/simple/test_s1_spec.py::test_t2_buy_level_floored[pessimistic]`, `tests/simple/test_s1_spec.py::test_t2_sell_level_floored[optimistic]`, `tests/simple/test_s1_spec.py::test_t2_sell_level_floored[pessimistic]`, `tests/simple/test_s1_spec.py::test_t2_decimal_sum[optimistic]`, `tests/simple/test_s1_spec.py::test_t2_decimal_sum[pessimistic]`, `tests/simple/test_s1_spec.py::test_t2_limit_floored_and_calc_kept[optimistic]`, `tests/simple/test_s1_spec.py::test_t2_limit_floored_and_calc_kept[pessimistic]`, `tests/simple/test_s1_spec.py::test_t3_limit_cases_and_market[optimistic]`, `tests/simple/test_s1_spec.py::test_t3_limit_cases_and_market[pessimistic]`, `tests/simple/test_s1_spec.py::test_t4_exit_on_level`, `tests/simple/test_s1_spec.py::test_t4_exit_after_parent_filled_is_plain_limit`, `tests/simple/test_s1_spec.py::test_t5_root_and_level_withdrawn[optimistic]`, `tests/simple/test_s1_spec.py::test_t5_root_and_level_withdrawn[pessimistic]`, `tests/simple/test_s1_spec.py::test_t6_next_bar_is_next_present_bar[optimistic]`, `tests/simple/test_s1_spec.py::test_t6_next_bar_is_next_present_bar[pessimistic]`, `tests/simple/test_s1_spec.py::test_t7_stops[同じ番号で中身が違う]`, `tests/simple/test_s1_spec.py::test_t7_stops[約定した番号をまた返す]`, `tests/simple/test_s1_spec.py::test_t7_stops[根が約定した後に初めて出た段]`, `tests/simple/test_s1_spec.py::test_t7_stops[消えた番号をまた返す]`, `tests/simple/test_s1_spec.py::test_t8_files_signals_and_numbers`, `tests/simple/test_s1_spec.py::test_t8_check_numbers_reads_trades`, `tests/simple/test_s1_spec.py::test_t8_records_are_written_while_running`, `tests/simple/test_s1_spec.py::test_t9_data_end[optimistic]`, `tests/simple/test_s1_spec.py::test_t9_data_end[pessimistic]`, `tests/simple/test_s1_spec.py::test_t9_same_bar_fills_in_placed_order[optimistic]`, `tests/simple/test_s1_spec.py::test_t9_same_bar_fills_in_placed_order[pessimistic]`, `tests/simple/test_s1_spec.py::test_t9_level_and_exit_open_on_later_bar[optimistic]`, `tests/simple/test_s1_spec.py::test_t9_level_and_exit_open_on_later_bar[pessimistic]`, `tests/simple/test_s1_spec.py::test_t2_sell_limit_and_exit_floored[optimistic]`, `tests/simple/test_s1_spec.py::test_t2_sell_limit_and_exit_floored[pessimistic]`, `tests/simple/test_s1_spec.py::test_t4_exit_beyond_range_on_parent_bar_waits[optimistic]`, `tests/simple/test_s1_spec.py::test_t4_exit_beyond_range_on_parent_bar_waits[pessimistic]`, `tests/simple/test_s1_spec.py::test_t8_rerun_same_dir_starts_fresh` |
| U2b | 段の値段を浮動小数の和(10 進に直す前)で作る | `tests/simple/test_s1_spec.py::test_t2_decimal_sum[optimistic]`, `tests/simple/test_s1_spec.py::test_t2_decimal_sum[pessimistic]` |
| U2c | limit・exit の値段を切り捨てずに使う | `tests/simple/test_s1_spec.py::test_t2_limit_floored_and_calc_kept[optimistic]`, `tests/simple/test_s1_spec.py::test_t2_limit_floored_and_calc_kept[pessimistic]`, `tests/simple/test_s1_spec.py::test_t2_sell_limit_and_exit_floored[optimistic]`, `tests/simple/test_s1_spec.py::test_t2_sell_limit_and_exit_floored[pessimistic]` |
| U2d | 注文の行の px_calc 欄に切り捨てた値段を書く | `tests/simple/test_s1_spec.py::test_t1_levels_from_root_fill[optimistic]`, `tests/simple/test_s1_spec.py::test_t1_levels_from_root_fill[pessimistic]`, `tests/simple/test_s1_spec.py::test_t2_limit_floored_and_calc_kept[optimistic]`, `tests/simple/test_s1_spec.py::test_t2_limit_floored_and_calc_kept[pessimistic]`, `tests/simple/test_s1_spec.py::test_t2_sell_limit_and_exit_floored[optimistic]`, `tests/simple/test_s1_spec.py::test_t2_sell_limit_and_exit_floored[pessimistic]` |
| U3a | 範囲の外の向きを逆にする(買いは安値より下で始値) | `tests/simple/test_s1_spec.py::test_t1_levels_from_root_fill[optimistic]`, `tests/simple/test_s1_spec.py::test_t1_levels_from_root_fill[pessimistic]`, `tests/simple/test_s1_spec.py::test_t2_buy_level_floored[optimistic]`, `tests/simple/test_s1_spec.py::test_t2_buy_level_floored[pessimistic]`, `tests/simple/test_s1_spec.py::test_t2_sell_level_floored[optimistic]`, `tests/simple/test_s1_spec.py::test_t2_sell_level_floored[pessimistic]`, `tests/simple/test_s1_spec.py::test_t2_decimal_sum[optimistic]`, `tests/simple/test_s1_spec.py::test_t2_decimal_sum[pessimistic]`, `tests/simple/test_s1_spec.py::test_t3_limit_cases_and_market[optimistic]`, `tests/simple/test_s1_spec.py::test_t3_limit_cases_and_market[pessimistic]`, `tests/simple/test_s1_spec.py::test_t4_exit_on_level`, `tests/simple/test_s1_spec.py::test_t4_exit_after_parent_filled_is_plain_limit`, `tests/simple/test_s1_spec.py::test_t5_root_and_level_withdrawn[optimistic]`, `tests/simple/test_s1_spec.py::test_t5_root_and_level_withdrawn[pessimistic]`, `tests/simple/test_s1_spec.py::test_t6_next_bar_is_next_present_bar[optimistic]`, `tests/simple/test_s1_spec.py::test_t6_next_bar_is_next_present_bar[pessimistic]`, `tests/simple/test_s1_spec.py::test_t7_stops[約定した番号をまた返す]`, `tests/simple/test_s1_spec.py::test_t8_files_signals_and_numbers`, `tests/simple/test_s1_spec.py::test_t8_records_are_written_while_running`, `tests/simple/test_s1_spec.py::test_t9_same_bar_fills_in_placed_order[optimistic]`, `tests/simple/test_s1_spec.py::test_t9_same_bar_fills_in_placed_order[pessimistic]`, `tests/simple/test_s1_spec.py::test_t9_level_and_exit_open_on_later_bar[optimistic]`, `tests/simple/test_s1_spec.py::test_t9_level_and_exit_open_on_later_bar[pessimistic]`, `tests/simple/test_s1_spec.py::test_t2_sell_limit_and_exit_floored[optimistic]`, `tests/simple/test_s1_spec.py::test_t2_sell_limit_and_exit_floored[pessimistic]`, `tests/simple/test_s1_spec.py::test_t4_exit_beyond_range_on_parent_bar_waits[optimistic]`, `tests/simple/test_s1_spec.py::test_t4_exit_beyond_range_on_parent_bar_waits[pessimistic]`, `tests/simple/test_s1_spec.py::test_t8_rerun_same_dir_starts_fresh` |
| U3b | 成行を始値でなく終値で約定させる | `tests/simple/test_s1_spec.py::test_t3_limit_cases_and_market[optimistic]`, `tests/simple/test_s1_spec.py::test_t3_limit_cases_and_market[pessimistic]` |
| U3c | 範囲の内を安値 < 値段 < 高値(端を含めない)にする | `tests/simple/test_s1_spec.py::test_t4_exit_after_parent_filled_is_plain_limit`, `tests/simple/test_s1_spec.py::test_t2_sell_limit_and_exit_floored[optimistic]`, `tests/simple/test_s1_spec.py::test_t2_sell_limit_and_exit_floored[pessimistic]` |
| U3d | 範囲の外の向きでも、始値でなく値段で約定させる | `tests/simple/test_s1_spec.py::test_t1_levels_from_root_fill[optimistic]`, `tests/simple/test_s1_spec.py::test_t1_levels_from_root_fill[pessimistic]`, `tests/simple/test_s1_spec.py::test_t2_buy_level_floored[optimistic]`, `tests/simple/test_s1_spec.py::test_t2_buy_level_floored[pessimistic]`, `tests/simple/test_s1_spec.py::test_t2_sell_level_floored[optimistic]`, `tests/simple/test_s1_spec.py::test_t2_sell_level_floored[pessimistic]`, `tests/simple/test_s1_spec.py::test_t2_decimal_sum[optimistic]`, `tests/simple/test_s1_spec.py::test_t2_decimal_sum[pessimistic]`, `tests/simple/test_s1_spec.py::test_t3_limit_cases_and_market[optimistic]`, `tests/simple/test_s1_spec.py::test_t3_limit_cases_and_market[pessimistic]`, `tests/simple/test_s1_spec.py::test_t4_exit_on_level`, `tests/simple/test_s1_spec.py::test_t4_exit_after_parent_filled_is_plain_limit`, `tests/simple/test_s1_spec.py::test_t6_next_bar_is_next_present_bar[optimistic]`, `tests/simple/test_s1_spec.py::test_t6_next_bar_is_next_present_bar[pessimistic]`, `tests/simple/test_s1_spec.py::test_t8_files_signals_and_numbers`, `tests/simple/test_s1_spec.py::test_t9_same_bar_fills_in_placed_order[optimistic]`, `tests/simple/test_s1_spec.py::test_t9_same_bar_fills_in_placed_order[pessimistic]`, `tests/simple/test_s1_spec.py::test_t9_level_and_exit_open_on_later_bar[optimistic]`, `tests/simple/test_s1_spec.py::test_t9_level_and_exit_open_on_later_bar[pessimistic]`, `tests/simple/test_s1_spec.py::test_t4_exit_beyond_range_on_parent_bar_waits[optimistic]`, `tests/simple/test_s1_spec.py::test_t4_exit_beyond_range_on_parent_bar_waits[pessimistic]`, `tests/simple/test_s1_spec.py::test_t8_rerun_same_dir_starts_fresh` |
| U4a | 悪い側でも親の足で利確を試す | `tests/simple/test_s1_spec.py::test_t4_exit_on_level`, `tests/simple/test_s1_spec.py::test_t2_sell_limit_and_exit_floored[pessimistic]` |
| U4b | 良い側の親の足で、範囲の外の利確を始値で約定させる | `tests/simple/test_s1_spec.py::test_t4_exit_beyond_range_on_parent_bar_waits[optimistic]` |
| U4c | 親が約定した後に出た利確にも「親の足」の扱いを当てる | `tests/simple/test_s1_spec.py::test_t4_exit_on_level`, `tests/simple/test_s1_spec.py::test_t4_exit_after_parent_filled_is_plain_limit`, `tests/simple/test_s1_spec.py::test_t9_level_and_exit_open_on_later_bar[optimistic]`, `tests/simple/test_s1_spec.py::test_t9_level_and_exit_open_on_later_bar[pessimistic]`, `tests/simple/test_s1_spec.py::test_t2_sell_limit_and_exit_floored[pessimistic]`, `tests/simple/test_s1_spec.py::test_t4_exit_beyond_range_on_parent_bar_waits[optimistic]`, `tests/simple/test_s1_spec.py::test_t4_exit_beyond_range_on_parent_bar_waits[pessimistic]` |
| U5a | 根が約定しないまま消えた段の値段を、空にせず書く | `tests/simple/test_s1_spec.py::test_t5_root_and_level_withdrawn[optimistic]`, `tests/simple/test_s1_spec.py::test_t5_root_and_level_withdrawn[pessimistic]` |
| U5b | 消えた注文の行を書かない | `tests/simple/test_s1_spec.py::test_t3_limit_cases_and_market[optimistic]`, `tests/simple/test_s1_spec.py::test_t3_limit_cases_and_market[pessimistic]`, `tests/simple/test_s1_spec.py::test_t5_root_and_level_withdrawn[optimistic]`, `tests/simple/test_s1_spec.py::test_t5_root_and_level_withdrawn[pessimistic]` |
| U6a | 値段の空の足を飛ばさない | `tests/simple/test_s1_spec.py::test_t6_read_bars_skips_null_and_ends_at_seal` |
| U6b | 封印の境の行を見ない(境以後の行も読む) | `tests/simple/test_s1_spec.py::test_t6_read_bars_skips_null_and_ends_at_seal` |
| U6c | 境の年より後の年のファイルを止めない | `tests/simple/test_s1_spec.py::test_t6_read_bars_refuses_files_after_seal_year` |
| U6d | run が境以後の足を止めない | `tests/simple/test_s1_spec.py::test_t6_run_refuses_bars_after_seal` |
| U6e | 欠けた分の後の足では注文を約定させない(次の足 = 時刻 + 60 秒) | `tests/simple/test_s1_spec.py::test_t6_next_bar_is_next_present_bar[optimistic]`, `tests/simple/test_s1_spec.py::test_t6_next_bar_is_next_present_bar[pessimistic]` |
| U7a | 同じ番号で中身が違っても止めない | `tests/simple/test_s1_spec.py::test_t7_stops[同じ番号で中身が違う]` |
| U7b | 約定した番号・消えた番号をまた返しても止めない | `tests/simple/test_s1_spec.py::test_t7_stops[約定した番号をまた返す]`, `tests/simple/test_s1_spec.py::test_t7_stops[消えた番号をまた返す]` |
| U7c | 根・親が無い参照を飛ばす(止めない) | `tests/simple/test_s1_spec.py::test_t7_stops[根の無い段]`, `tests/simple/test_s1_spec.py::test_t7_stops[親の無い利確]` |
| U7d | 段の距離の向きを見ない | `tests/simple/test_s1_spec.py::test_t7_stops[段の距離の向きが違う]` |
| U7e | 段の売買が根と違っても止めない | `tests/simple/test_s1_spec.py::test_t7_stops[段の売買が根と違う]` |
| U7f | 根が limit でなくても止めない | `tests/simple/test_s1_spec.py::test_t7_stops[根が段の段]` |
| U7g | 根が約定した後に初めて出た段を止めない | `tests/simple/test_s1_spec.py::test_t7_stops[根が約定した後に初めて出た段]` |
| U7h | 量が刻みの外でも(0 より大きければ)止めない | `tests/simple/test_s1_spec.py::test_t7_stops[量が刻みの外]` |
| U7i | 量が 0 でも止めない | `tests/simple/test_s1_spec.py::test_t7_stops[量が 0]` |
| U7j | 知らない形も受け付ける | `tests/simple/test_s1_spec.py::test_t7_stops[知らない形]` |
| U7k | 親が limit でも level でもない利確を止めない | `tests/simple/test_s1_spec.py::test_t7_stops[親が成行の利確]` |
| U7l | 売買が親と同じ利確を止めない | `tests/simple/test_s1_spec.py::test_t7_stops[売買が親と同じ利確]` |
| U7m | 量が親と違う利確を止めない | `tests/simple/test_s1_spec.py::test_t7_stops[量が親と違う利確]` |
| U8a | 数の作り直しが trades を見ない | `tests/simple/test_s1_spec.py::test_t8_check_numbers_reads_trades` |
| U8b | 数の作り直しが summary を見ない | `tests/simple/test_s1_spec.py::test_t8_files_signals_and_numbers` |
| U8c | 注文の行をすぐファイルに出さない(flush しない) | `tests/simple/test_s1_spec.py::test_t8_records_are_written_while_running` |
| U8d | 同じディレクトリの前の走らせの中身を残す(w を a に) | `tests/simple/test_s1_spec.py::test_t8_rerun_same_dir_starts_fresh` |
| U8e | run_<側>.json に git の版を書かない | `tests/simple/test_s1_spec.py::test_t8_files_signals_and_numbers` |
| U9a | 約定させる順を exit → level にする | `tests/simple/test_s1_spec.py::test_t4_exit_on_level` |
| U9b | 同じ形の中を、出した順でなく番号の文字順にする | `tests/simple/test_s1_spec.py::test_t9_same_bar_fills_in_placed_order[optimistic]`, `tests/simple/test_s1_spec.py::test_t9_same_bar_fills_in_placed_order[pessimistic]` |
| U9c | データの終わりに、最後の判定で出た注文にも最後の足を書く | `tests/simple/test_s1_spec.py::test_t9_data_end[optimistic]`, `tests/simple/test_s1_spec.py::test_t9_data_end[pessimistic]` |
| U9d | データの終わりまで消えなかった合図の理由を空にする | `tests/simple/test_s1_spec.py::test_t9_data_end[optimistic]`, `tests/simple/test_s1_spec.py::test_t9_data_end[pessimistic]` |
| H1 | `git diff --stat tests/` | 空(試験は変えていない) |
| H2 | `git diff --stat src/`・`git status --short -uall src/ tests/` | 空 / 新しい 6 ファイルだけ |
| H3 | `grep -rn "bot.bt.fill\|bot.bt.core\|bot.bt.road.strategy\|bot.bt.pipeline" src/bot/bt/simple/` | 出力なし |
| H4 | `PYTHONPATH=src python -m pytest tests/road` | 315 passed |
| H5 | `wc -l src/bot/bt/simple/*.py` | 合計 474 行 |

最初に作った U1c(根の足で、段が範囲の外なら始値で約定させる)は、どの試験も落とさなかった。この変更は等価な変異で、試験が足りないのではない。買いの段の値段は F より低く、F は高値以下なので、段の値段が高値を超える場面が起きない(売りは逆向きで同じ)。距離が 0 でなければ到達できないので、範囲の外でも約定させる U1c に差し替えた。U6b も最初は等価な変異(`return` を `continue` にしただけ)で、境の行を見ない形に差し替えた。

U7c は「写しの壊し方」の都合で、落ち方が `SimpleRoadError` でなく別の例外になった。落ちたこと自体は確かめた(U7j も同じ)。

## 試験で決まらず作業者が決めた内部の形

- 約定の関数: `fill_bar(live, bar, side, tick)`(`fills.py`)。出ている注文の状態 `Order`(seq・番号・形・売買・量・戦略が出した値段・根・距離・親・切り捨てた値段・状態・約定の足と値段・約定しうる最初と最後の足・case・根と親の参照)を更新して、約定した注文を約定させた順に返す。
- 注文の行は、約定した時(約定の直後)、消えた時(判定で返さなかった時)、データの終わり(出たままの注文)に書く。出す列は SPEC.md §4 のとおり。market の px_calc・px・root・offset・parent は空。
- from_ts は注文が初めて足にさらされた足、to_ts はさらされた最後の足。判定の足で出た注文は次の足から。さらされなければ両方空。
- 段の値段は、根が約定した瞬間に、その根を持つ出ている段全部へ決める。根の約定値段が始値のときは始値を F とする。
- 参照の検めは、判定で返された段・利確だけに行う(返さなかった注文は消えるので検めない)。
- 刻みへの切り捨ては、`Decimal(repr(値段)) / Decimal(repr(刻み))` を `ROUND_FLOOR` で整数にして刻みを掛け、float に戻す。
- 量の刻みの検めは、`Decimal(repr(量)) % Decimal("0.001") == 0` かつ量が 0 より大きい。`bot.bt.road.sizing` の `STEP_BTC` は使わず、`common.py` に同じ値を持った。
- 合図の value_json は `json.dumps(value, ensure_ascii=False, sort_keys=True)`。合図の行は、終わった時に書く。データの終わりまで消えなかった合図は、データの終わりに出た順で書く。
- fills・orders・signals は 1 行ごとに flush する。run は始めに、その側の trades と summary の前の中身を消す(途中で止まったときに前の走らせの数が残らないため)。
- run_<側>.json は meta の写しに tick・side・git を足して `indent=1` で書く。git は `git rev-parse HEAD` で、このパッケージのディレクトリに未コミットの変更か未追跡のファイルがあれば末尾に「+未コミットの変更あり」を付ける。git が使えなければ "unknown"。
- trades_<側>.csv は `TRADE_KEYS` の 7 列(None は空欄)。summary_<側>.json は fill_count・closed_trades・pnl_jpy・open_trades の 4 つ。
- `check_numbers`: 約定のファイルを読んで `book` に渡し、summary の 4 つと trades の 7 列を行ごとに文字列で比べる。ファイルが読めない・`book` が受け付けない場合は、例外にせず食い違いの 1 行として返す。
- `read_bars`: 年の検めは全ファイルを先に名前だけで行い、その後に 1 つずつ開く。読みは生成器で、境の行に届いたら残りのファイルは開かない。
- 日時の比べはすべて datetime にして行う(文字列の大小は使わない)。

## 問いとして返したこと

- Q1: 段の距離が 0 のとき。委任文は「買いで正、売りで負なら止める」としか書いておらず、0 は書いていない。今は文字どおりに読み、止めずに通す(段の値段は F と同じ)。止めるなら 1 行の直しで、試験は今どちらでも通る。
- Q2: `run` の meta に `seal` が無いとき。今は止める(封印の境が分からないと境以後の足を止める検めができないため)。止めずに通す選びもありうる。
- Q3: 合図の出来事の不正(同じ id を二度 start・出ていない id の end・知らない op)の扱いは、SPEC.md にも試験にも無い。今は止める。
- Q4: `run` に渡った足が古い順でない・足の値が数でないときの扱いは、SPEC.md にも試験にも無い。今は止める。
- Q5: 足のファイルの名前が `_YYYY.csv.gz` の形でないときの扱いは、SPEC.md にも試験にも無い。今は年の検めを掛けずに開く。境の行で終わる検めは掛かる。
- Q6: limit・exit の値段が 0 以下、または切り捨てた値段が 0 以下のときは止める。段の値段が 0 以下になる場合は止めず、最後に `book` が止める(`LedgerError`)。SPEC.md にも試験にも無い。
- Q7: 試験が見ていない止め方が 2 つある。いずれも実装したが、変異で確かめていない。
  - 出ている段の根を取り下げて段だけ残したとき(止める)。
  - 出ている利確の親を取り下げて利確だけ残したとき(止める)。
  SPEC.md の「根が出ていなくて約定もしていない level」の文言から導いた。
- Q8: SPEC.md の「止める注文」の一覧に載っていない余計な鍵が注文の辞書に付いていたときは、無視する。
