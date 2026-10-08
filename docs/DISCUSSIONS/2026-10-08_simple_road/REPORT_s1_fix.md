# 委任先の報告(逐語)— DELEGATION_s1_fix.md(3 版目、L-826)

作業者の返事を、そのまま写した。リードは書き換えていない。1 回目の返事で、試験が見分けられない変異 2 つ(Q1・Q2)が返り、リードが試験を 2 通り足した。2 回目は変異の表の欄に経緯の文があり受け取りの検めが「落ちなかった」と読んだので、書き方だけを直させた。これは 3 回目の返事。

## 着手前の表

| やろうとすること | オーナーの原文の該当語(逐語) |
|---|---|
| 1 本の足の記す順を 成行 → 前の足までに親が約定した利確 → 指値 → 段 → この足で親が約定した利確(同じ組の中は seq 順)にする | L-826「**両方yes**」(根: 直すもの 1・受け入れ U1。内容の根は目的の L-824「**(a)**」) |
| 封印の境の行より先を読まないことを、コードを変えずに試験で確かめる | L-826「**両方yes**」(根: 直すもの 2・受け入れ U2) |
| 安値が高値より高い足を `read_bars`(足の読み込み)・`run`(走らせ)で `SimpleRoadError`(道が先へ進めない時の例外)にする | L-826「**両方yes**」(根: 直すもの 3・受け入れ U3) |
| `check_numbers`(数の作り直し)を SPEC.md §5 の 2 のとおりに直す | L-826「**両方yes**」(根: 直すもの 4・受け入れ U4) |
| 消えた注文の中身を記憶に持たず、seq を数え上げで出す | L-826「**両方yes**」(根: 直すもの 5・受け入れ U5・U6) |
| `run_<側>.json` の git の版の印を `src/` 全体と未追跡のファイルで付ける | L-826「**両方yes**」(根: 直すもの 6・変えないもの H6) |
| 変異の表を scratchpad の写しで作る | L-826「**両方yes**」(根: 変異の表) |
| 報告を委任文の「報告」の形で返事に出す | L-826「**両方yes**」(根: 報告) |

右が空になる行は無かった。

## 直したファイルの一覧と、直す前と後の行数(H5)

`src/bot/bt/simple/` の下の 5 ファイルだけ(`git status --short src/` の出力は下の H2)。

| ファイル | 直す前 | 直した後 |
|---|---|---|
| `__init__.py` | 7 | 7 |
| `bars.py`(足の読み込み) | 48 | 50 |
| `check.py`(数の作り直し) | 49 | 71 |
| `common.py`(共通の部品) | 64 | 79 |
| `fills.py`(約定の関数) | 82 | 94 |
| `run.py`(走らせ) | 224 | 233 |
| 合計 | 474 | 534 |

足した試験ファイル(`tests/simple/test_s1_fix_extra.py`)は無い。コードは、リードが Q1・Q2 に答えた後も変えていない。

## 試験のコマンドと出力

コマンド: `PYTHONPATH=src python -m pytest tests/simple/test_s1_spec.py tests/simple/test_s1_fix_spec.py tests/road`

出力の末尾(リードが試験を 2 通り足した後に打ち直した): `400 passed in 23.75s`(飛ばし 0・落ち 0。`tests/simple` の 85 件と `tests/road` の 315 件)。足す前は `398 passed in 22.50s`。着手前の同じ 2 つの試験は `19 failed, 64 passed`(委任文の「読んだ事実」と同じ)。

## H1〜H6 の確かめ

- H1: `git status --short tests/` → 打ち直した時点で出力は空(私は試験を変えていない。途中でリードが試験を足し、その変更は私の作業ではない)。
- H2: `git status --short src/` → `M src/bot/bt/simple/bars.py`・`check.py`・`common.py`・`fills.py`・`run.py` の 5 行だけ。
- H3: `(git ls-files src/bot/bt/simple; git ls-files -o --exclude-standard src/bot/bt/simple) | xargs grep -nE "bot\.bt\.(fill|core|road\.strategy|pipeline)|from \.\.(fill|core|pipeline)|from \.\.road(\.strategy| import strategy)"` → 出力は空。表示された `rc=123` は、`xargs` が「grep がどのファイルでも 1 件も見つけなかった」ことを返した数で、失敗ではない。
- H4: 上の試験のコマンドに `tests/road` が入っていて全部通った(`400 passed` の中)。
- H5: `wc -l src/bot/bt/simple/*.py` → 合計 534(直す前は 474。上の表に 1 ファイルずつ)。
- H6: 直したコード(`src/bot/bt/simple/run.py:35-47` の `_git_version`、git の版の印を作る関数):

```python
    here = os.path.dirname(os.path.abspath(__file__))
    try:
        top = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=here, capture_output=True, text=True,
                             check=True).stdout.strip()
        src = os.path.join(top, "src")
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=top, capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all", "--", src], cwd=top,
                               capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return head + ("+未コミットの変更あり" if dirty else "")
```

  git に渡す道を絶対の道にして示したコマンドと出力(コードと同じ手順で `top` を求めて `os.path.join(top, "src")` を出した):
  - `渡す道: /home/user/trade/src`
  - `期待: /home/user/trade/src`(`$(git rev-parse --show-toplevel)/src`)→ 同じ。
  - その道で `git status --porcelain --untracked-files=all -- <道>` → 直した 5 ファイルの `M` が出た(黙っていない)。`_git_version()` の戻り値は `b2284616a81d96e19b210dedb087555bd6e73a1f+未コミットの変更あり`。
  - 未追跡のファイルの検め: scratchpad の使い捨ての git で同じコマンド。きれいな時は `clean:[]`、`src/a/new.py` を足すと `untracked:[?? src/a/new.py]`(リポジトリのファイルは書き換えていない)。

## 変異の表

壊した変更は `/tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/s1fix_worker/copy/` の `src/` の写しに当て(本物は壊していない)、`-o pythonpath=<写し>` と `PYTHONPATH=<写し>` を付けて `tests/simple/test_s1_spec.py` と `tests/simple/test_s1_fix_spec.py` を走らせた。各回、読み込まれた `bot.bt.simple` は `.../s1fix_worker/copy/bot/bt/simple/__init__.py` だった。リードが試験を 2 通り足した後、U4-c と U4-i を当て直し、さらに念のため全部の変異を当て直した(表は当て直した後の結果。足した 2 つの試験が加わったのは U3-c・U4-c・U4-i の 3 行だけで、ほかの行は前と同じ)。表の写しは同じ置き場の `mutation_table_final.md`(変異を当てる台本は `mut.py`)。試験の名前の `\uXXXX` は pytest が日本語の引数名を出す形そのままで、直後の括弧の中に日本語に直したものを添えた。

H の行は下の 6 行(確かめのコマンドと結果は上の「H1〜H6 の確かめ」)。

| 番号 | 壊した変更 | 落ちた試験 |
|---|---|---|
| U1-a | 前の足までに親が約定した利確を、元どおり段の後ろ(この足の親の利確と同じ組)にする | tests/simple/test_s1_fix_spec.py::test_f1_exit_of_earlier_parent_before_new_limit[利確を根と一緒に出す-optimistic](利確を根と一緒に出す-optimistic); tests/simple/test_s1_fix_spec.py::test_f1_exit_of_earlier_parent_before_new_limit[利確を根と一緒に出す-pessimistic](利確を根と一緒に出す-pessimistic); tests/simple/test_s1_fix_spec.py::test_f1_exit_of_earlier_parent_before_new_limit[利確を根の約定の後に出す-optimistic](利確を根の約定の後に出す-optimistic); tests/simple/test_s1_fix_spec.py::test_f1_exit_of_earlier_parent_before_new_limit[利確を根の約定の後に出す-pessimistic](利確を根の約定の後に出す-pessimistic) |
| U1-b | 前の足までに親が約定した利確を成行より先にする | tests/simple/test_s1_fix_spec.py::test_f1_market_before_exit_of_earlier_parent[optimistic]; tests/simple/test_s1_fix_spec.py::test_f1_market_before_exit_of_earlier_parent[pessimistic] |
| U1-c | この足で親が約定する利確も、指値より先の組に入れる | tests/simple/test_s1_spec.py::test_t4_exit_on_level; tests/simple/test_s1_spec.py::test_t2_sell_limit_and_exit_floored[optimistic]; tests/simple/test_s1_fix_spec.py::test_f1_exit_of_same_bar_parent_stays_after[optimistic] |
| U1-d | 同じ組の中を、番号を出した順の逆にする | tests/simple/test_s1_spec.py::test_t9_same_bar_fills_in_placed_order[optimistic]; tests/simple/test_s1_spec.py::test_t9_same_bar_fills_in_placed_order[pessimistic] |
| U1-e | 段を指値より先にする | tests/simple/test_s1_spec.py::test_t1_levels_from_root_fill[optimistic]; tests/simple/test_s1_spec.py::test_t1_levels_from_root_fill[pessimistic]; tests/simple/test_s1_spec.py::test_t2_sell_level_floored[optimistic]; tests/simple/test_s1_spec.py::test_t2_sell_level_floored[pessimistic]; tests/simple/test_s1_spec.py::test_t2_decimal_sum[optimistic]; tests/simple/test_s1_spec.py::test_t2_decimal_sum[pessimistic]; tests/simple/test_s1_spec.py::test_t4_exit_on_level |
| U2-a | 封印の境の行に届いても読み続ける(`return` を `continue` に) | tests/simple/test_s1_fix_spec.py::test_f2_read_bars_does_not_read_past_seal_row |
| U3-a | `run` の安値 > 高値の検めを外す | tests/simple/test_s1_fix_spec.py::test_f3_run_stops_on_low_above_high |
| U3-b | `read_bars` の安値 > 高値の検めを外す | tests/simple/test_s1_fix_spec.py::test_f3_read_bars_stops_on_low_above_high |
| U3-c | `run` の検めを、安値 = 高値(平らな足)でも止める形にする | tests/simple/test_s1_spec.py::test_t1_levels_from_root_fill[optimistic]; tests/simple/test_s1_spec.py::test_t1_levels_from_root_fill[pessimistic]; tests/simple/test_s1_spec.py::test_t2_buy_level_floored[optimistic]; tests/simple/test_s1_spec.py::test_t2_buy_level_floored[pessimistic]; tests/simple/test_s1_spec.py::test_t2_sell_level_floored[optimistic]; tests/simple/test_s1_spec.py::test_t2_sell_level_floored[pessimistic]; tests/simple/test_s1_spec.py::test_t2_decimal_sum[optimistic]; tests/simple/test_s1_spec.py::test_t2_decimal_sum[pessimistic]; tests/simple/test_s1_spec.py::test_t2_limit_floored_and_calc_kept[optimistic]; tests/simple/test_s1_spec.py::test_t2_limit_floored_and_calc_kept[pessimistic]; tests/simple/test_s1_spec.py::test_t3_limit_cases_and_market[optimistic]; tests/simple/test_s1_spec.py::test_t3_limit_cases_and_market[pessimistic]; tests/simple/test_s1_spec.py::test_t4_exit_on_level; tests/simple/test_s1_spec.py::test_t4_exit_after_parent_filled_is_plain_limit; tests/simple/test_s1_spec.py::test_t5_root_and_level_withdrawn[optimistic]; tests/simple/test_s1_spec.py::test_t5_root_and_level_withdrawn[pessimistic]; tests/simple/test_s1_spec.py::test_t6_next_bar_is_next_present_bar[optimistic]; tests/simple/test_s1_spec.py::test_t6_next_bar_is_next_present_bar[pessimistic]; tests/simple/test_s1_spec.py::test_t8_files_signals_and_numbers; tests/simple/test_s1_spec.py::test_t8_check_numbers_reads_trades; tests/simple/test_s1_spec.py::test_t8_records_are_written_while_running; tests/simple/test_s1_spec.py::test_t9_data_end[optimistic]; tests/simple/test_s1_spec.py::test_t9_data_end[pessimistic]; tests/simple/test_s1_spec.py::test_t9_same_bar_fills_in_placed_order[optimistic]; tests/simple/test_s1_spec.py::test_t9_same_bar_fills_in_placed_order[pessimistic]; tests/simple/test_s1_spec.py::test_t9_level_and_exit_open_on_later_bar[optimistic]; tests/simple/test_s1_spec.py::test_t9_level_and_exit_open_on_later_bar[pessimistic]; tests/simple/test_s1_spec.py::test_t2_sell_limit_and_exit_floored[optimistic]; tests/simple/test_s1_spec.py::test_t2_sell_limit_and_exit_floored[pessimistic]; tests/simple/test_s1_spec.py::test_t4_exit_beyond_range_on_parent_bar_waits[optimistic]; tests/simple/test_s1_spec.py::test_t4_exit_beyond_range_on_parent_bar_waits[pessimistic]; tests/simple/test_s1_spec.py::test_t8_rerun_same_dir_starts_fresh; tests/simple/test_s1_fix_spec.py::test_f1_exit_of_earlier_parent_before_new_limit[利確を根と一緒に出す-optimistic](利確を根と一緒に出す-optimistic); tests/simple/test_s1_fix_spec.py::test_f1_exit_of_earlier_parent_before_new_limit[利確を根と一緒に出す-pessimistic](利確を根と一緒に出す-pessimistic); tests/simple/test_s1_fix_spec.py::test_f1_exit_of_earlier_parent_before_new_limit[利確を根の約定の後に出す-optimistic](利確を根の約定の後に出す-optimistic); tests/simple/test_s1_fix_spec.py::test_f1_exit_of_earlier_parent_before_new_limit[利確を根の約定の後に出す-pessimistic](利確を根の約定の後に出す-pessimistic); tests/simple/test_s1_fix_spec.py::test_f1_exit_of_same_bar_parent_stays_after[optimistic]; tests/simple/test_s1_fix_spec.py::test_f1_exit_of_same_bar_parent_stays_after[pessimistic]; tests/simple/test_s1_fix_spec.py::test_f1_market_before_exit_of_earlier_parent[optimistic]; tests/simple/test_s1_fix_spec.py::test_f1_market_before_exit_of_earlier_parent[pessimistic]; tests/simple/test_s1_fix_spec.py::test_f4_check_numbers_refuses_broken_records[fills と trades が 0 バイト・summary が 0](fills と trades が 0 バイト・summary が 0); tests/simple/test_s1_fix_spec.py::test_f4_check_numbers_refuses_broken_records[fills の見出しがでたらめ・行なし・summary が 0](fills の見出しがでたらめ・行なし・summary が 0); tests/simple/test_s1_fix_spec.py::test_f4_check_numbers_refuses_broken_records[fills の見出しに余計な列](fills の見出しに余計な列); tests/simple/test_s1_fix_spec.py::test_f4_check_numbers_refuses_broken_records[trades の見出しに余計な列](trades の見出しに余計な列); tests/simple/test_s1_fix_spec.py::test_f4_check_numbers_refuses_broken_records[summary が []](summary が []); tests/simple/test_s1_fix_spec.py::test_f4_check_numbers_refuses_broken_records[summary が null](summary が null); tests/simple/test_s1_fix_spec.py::test_f4_check_numbers_refuses_broken_records[summary の値を全部文字に](summary の値を全部文字に); tests/simple/test_s1_fix_spec.py::test_f4_check_numbers_refuses_broken_records[summary に余計な鍵](summary に余計な鍵); tests/simple/test_s1_fix_spec.py::test_f4_check_numbers_refuses_broken_records[trades が UTF-8 でない](trades が UTF-8 でない); tests/simple/test_s1_fix_spec.py::test_f4_check_numbers_refuses_broken_records[fills が UTF-8 でない](fills が UTF-8 でない); tests/simple/test_s1_fix_spec.py::test_f4_check_numbers_refuses_broken_records[trades の行を 1 つ足す](trades の行を 1 つ足す); tests/simple/test_s1_fix_spec.py::test_f4_check_numbers_refuses_broken_records[trades の行を 1 つ消す](trades の行を 1 つ消す); tests/simple/test_s1_fix_spec.py::test_f4_check_numbers_refuses_broken_records[summary の値を真偽値に](summary の値を真偽値に); tests/simple/test_s1_fix_spec.py::test_f4_check_numbers_refuses_broken_records[summary の値を小数に](summary の値を小数に); tests/simple/test_s1_fix_spec.py::test_f4_check_numbers_refuses_broken_records[約定の行の欄が足りない](約定の行の欄が足りない); tests/simple/test_s1_fix_spec.py::test_f4_check_numbers_refuses_broken_records[約定の行の欄が多すぎる](約定の行の欄が多すぎる); tests/simple/test_s1_fix_spec.py::test_f4_check_numbers_refuses_broken_records[fills だけが 0 バイト・trades と summary は約定 0 本](fills だけが 0 バイト・trades と summary は約定 0 本); tests/simple/test_s1_fix_spec.py::test_f4_check_numbers_refuses_broken_records[trades の中身の行の末尾に余計な欄](trades の中身の行の末尾に余計な欄); tests/simple/test_s1_fix_spec.py::test_f4_check_numbers_refuses_broken_records[trades の改行を CRLF に](trades の改行を CRLF に); tests/simple/test_s1_fix_spec.py::test_f4_check_numbers_passes_true_zero_fill_run; tests/simple/test_s1_fix_spec.py::test_f6_gone_orders_are_not_kept; tests/simple/test_s1_fix_spec.py::test_f7_seq_is_unique_and_counts_up |
| U4-a | summary の値を型まで比べず、等号だけで比べる | tests/simple/test_s1_fix_spec.py::test_f4_check_numbers_refuses_broken_records[summary の値を真偽値に](summary の値を真偽値に); tests/simple/test_s1_fix_spec.py::test_f4_check_numbers_refuses_broken_records[summary の値を小数に](summary の値を小数に) |
| U4-b | fills の見出しの行を見ない | tests/simple/test_s1_fix_spec.py::test_f4_check_numbers_refuses_broken_records[fills の見出しがでたらめ・行なし・summary が 0](fills の見出しがでたらめ・行なし・summary が 0); tests/simple/test_s1_fix_spec.py::test_f4_check_numbers_refuses_broken_records[fills の見出しに余計な列](fills の見出しに余計な列) |
| U4-c | fills の各行の欄の数を見ない | tests/simple/test_s1_fix_spec.py::test_f4_check_numbers_refuses_broken_records[約定の行の欄が多すぎる](約定の行の欄が多すぎる)(1 failed, 84 passed) |
| U4-d | 読めない入力で `OSError` しか拾わない | tests/simple/test_s1_fix_spec.py::test_f4_check_numbers_refuses_broken_records[fills が UTF-8 でない](fills が UTF-8 でない) |
| U4-e | trades の比べで CRLF と LF を同じとみなす | tests/simple/test_s1_fix_spec.py::test_f4_check_numbers_refuses_broken_records[trades の改行を CRLF に](trades の改行を CRLF に) |
| U4-f | trades を行の数だけで比べる | tests/simple/test_s1_spec.py::test_t8_check_numbers_reads_trades; tests/simple/test_s1_fix_spec.py::test_f4_check_numbers_refuses_broken_records[trades の見出しに余計な列](trades の見出しに余計な列); tests/simple/test_s1_fix_spec.py::test_f4_check_numbers_refuses_broken_records[trades の中身の行の末尾に余計な欄](trades の中身の行の末尾に余計な欄); tests/simple/test_s1_fix_spec.py::test_f4_check_numbers_refuses_broken_records[trades の改行を CRLF に](trades の改行を CRLF に) |
| U4-g | summary の余計な鍵を許す | tests/simple/test_s1_fix_spec.py::test_f4_check_numbers_refuses_broken_records[summary に余計な鍵](summary に余計な鍵) |
| U4-h | 約定 0 本の走らせを食い違いにする | tests/simple/test_s1_fix_spec.py::test_f4_check_numbers_passes_true_zero_fill_run |
| U4-i | 0 バイトの fills を約定 0 本として通す | tests/simple/test_s1_fix_spec.py::test_f4_check_numbers_refuses_broken_records[fills だけが 0 バイト・trades と summary は約定 0 本](fills だけが 0 バイト・trades と summary は約定 0 本)(1 failed, 84 passed) |
| U5-a | 消えた注文を引ける所に残し、根・親が出ていなくて約定もしていない検めを外す | tests/simple/test_s1_fix_spec.py::test_f5_withdrawn_reference_stops[段](段); tests/simple/test_s1_fix_spec.py::test_f5_withdrawn_reference_stops[利確](利確); tests/simple/test_s1_fix_spec.py::test_f6_gone_orders_are_not_kept |
| U6-a | 消えた注文の中身を記憶に持ち続ける | tests/simple/test_s1_fix_spec.py::test_f6_gone_orders_are_not_kept |
| U6-b | seq を記憶に持つ注文の数から出す | tests/simple/test_s1_fix_spec.py::test_f7_seq_is_unique_and_counts_up |
| U6-c | 消えた注文の番号の使い回しの検めを外す | tests/simple/test_s1_spec.py::test_t7_stops[消えた番号をまた返す](消えた番号をまた返す) |
| U7-a | 根が約定した足の段の case を range にする | tests/simple/test_s1_spec.py::test_t1_levels_from_root_fill[optimistic]; tests/simple/test_s1_spec.py::test_t1_levels_from_root_fill[pessimistic]; tests/simple/test_s1_spec.py::test_t2_sell_level_floored[optimistic]; tests/simple/test_s1_spec.py::test_t2_sell_level_floored[pessimistic]; tests/simple/test_s1_spec.py::test_t2_decimal_sum[optimistic]; tests/simple/test_s1_spec.py::test_t2_decimal_sum[pessimistic] |
| U7-b | 成行を始値でなく高値で約定させる | tests/simple/test_s1_spec.py::test_t3_limit_cases_and_market[optimistic]; tests/simple/test_s1_spec.py::test_t3_limit_cases_and_market[pessimistic]; tests/simple/test_s1_fix_spec.py::test_f1_market_before_exit_of_earlier_parent[optimistic]; tests/simple/test_s1_fix_spec.py::test_f1_market_before_exit_of_earlier_parent[pessimistic] |
| U7-c | 良い側と悪い側の利確の扱いを入れ替える | tests/simple/test_s1_spec.py::test_t4_exit_on_level; tests/simple/test_s1_spec.py::test_t2_sell_limit_and_exit_floored[optimistic]; tests/simple/test_s1_spec.py::test_t2_sell_limit_and_exit_floored[pessimistic]; tests/simple/test_s1_fix_spec.py::test_f1_exit_of_same_bar_parent_stays_after[optimistic]; tests/simple/test_s1_fix_spec.py::test_f1_exit_of_same_bar_parent_stays_after[pessimistic] |
| U7-d | 買いの段の距離の向きの検めを外す | tests/simple/test_s1_spec.py::test_t7_stops[段の距離の向きが違う](段の距離の向きが違う) |
| H1 | (確かめ)`git status --short tests/` | 出力は空 |
| H2 | (確かめ)`git status --short src/` | `src/bot/bt/simple/` の下の 5 ファイルだけ |
| H3 | (確かめ)委任文の `xargs grep -nE` | 出力は空(`rc=123` は grep が 0 件だったことを `xargs` が返した数) |
| H4 | (確かめ)`tests/road` | 全部通った(`400 passed` の中) |
| H5 | (確かめ)`wc -l` | 474 → 534 |
| H6 | (確かめ)絶対の道の一致と未追跡の検め | 道が一致し(`/home/user/trade/src`)、未追跡のファイルで `??` が出た |

U4-c と U4-i の 2 行は、リードが試験を 2 通り足した後の当て直しの結果で、足す前は試験が 1 つも落ちず、Q1・Q2 として返した。

## 試験で決まらず作業者が決めた内部の形の一覧

- `_rank`(`fills.py`。1 本の足の中で約定させる組の番号を返す関数): 組の番号は、足に入る時点の親の状態(`parent_order.state == "filled"` なら前の足までに約定した利確)で決める。`sorted` は鍵を全部先に作るので、足の中で約定した注文の状態では変わらない。
- 組の番号の定数 5 つ(`RANK_MARKET`・`RANK_EXIT_EARLIER`・`RANK_LIMIT`・`RANK_LEVEL`・`RANK_EXIT_SAME_BAR`。成行・前の足までに親が約定した利確・指値・段・この足で親が約定した利確)が、元の `RANK`(形から番号への辞書)に代わった。
- 記憶の持ち方(`run.py`): `recs`(番号から注文の辞書)をやめ、`filled`(約定した注文の辞書。中身を持つ)・`seen`(受けた注文の番号の集合。消えた注文は番号だけ)・`n_seen`(受けた注文を数え上げる整数。seq の元)にした。出ている注文は、その足で `by_id`(出ている注文の辞書)を作って引く。
- `_links`(根・親の参照を結んで検める関数)は、辞書の代わりに「番号から出ている・約定した注文を引く関数」を受け取る。
- `trades_text`(`common.py`。取引のファイルの全文を作る関数)を、走らせの書き出しと数の作り直しの比べで共有した。あわせて `FILL_COLS`・`TRADE_COLS`・`SUMMARY_COLS`(約定・取引・まとめの列)を `common.py` に移した。
- `check_numbers` は中身を `_check`(本体)に分け、外側で `except Exception` を使って、読めない入力を食い違いの行で返す。
- trades の比べは、作り直した全文を UTF-8 の bytes にして、ファイルの bytes と 1 字違わず(CRLF も区別して)比べる。
- fills の見出しは、最初の行の文字列を `ts,id,side,qty,px,case` と比べる(`csv` の読みには通さない)。欄の数は `csv.reader` で読んだ各行を見出しの欄の数と比べる。
- summary は `type(値) is type(作り直した値)` と等号の両方で比べる(`bool` と `int`、`float` と `int` を区別する)。
- git の版の印: `git rev-parse --show-toplevel` で求めたリポジトリの根の `src` に対し、`git status --porcelain --untracked-files=all -- <絶対の道>` で未コミットの変更と未追跡のファイルを見る。
- 消えた注文の記憶の増え方: 1 注文あたり約 97 バイト(`_peak(2000)` と `_peak(12000)` の差 ÷ 10,000。試験の閾値は 200)。

## 問いとして返したこと

- Q1: 変異 U4-c(fills の各行の欄の数を見ない検めを外す)で、試験が 1 つも落ちなかった。差し替えずに返す。仕組み: 試験の改ざん `_t_fills_row_short`(`test_f4_check_numbers_refuses_broken_records[約定の行の欄が足りない]`)は最終行を 2 欄に縮めるだけなので、欄の数の検めを外しても `r[3]` の参照で `IndexError` が出て、外側の `except Exception` が食い違いの行にする。この試験は「欄の数の検め」と「全部の例外を拾う外側」を区別できない。欄が見出しより多い fills の行(例 7 欄)を入れる試験は無く、その場合は検めが無ければ余計な欄が黙って捨てられる。等価な変異かどうかの判定はリードに任せる。
- Q2: 変異 U4-i(0 バイトの fills を約定 0 本として通す)で、試験が 1 つも落ちなかった。差し替えずに返す。仕組み: 試験の改ざん `_t_zero_bytes`(`test_f4_check_numbers_refuses_broken_records[fills と trades が 0 バイト・summary が 0]`)は fills と trades を両方 0 バイトにする。fills を約定 0 本として通しても、作り直した trades は見出しだけの全文で、0 バイトの trades とは一致せず、trades の比べが食い違いを出す。この試験は「fills が 0 バイトであること」を単独では見分けられない。fills だけを 0 バイトにして trades・summary は約定 0 本の正しい中身、という入力の試験は無い。等価な変異かどうかの判定はリードに任せる。

補足(問いではない): 二つ目の受け入れ `tests/simple/test_s2_spec.py` は委任文のとおり見ていない。`tests/simple/test_s1_fix_extra.py` は足していない。リードの答え(Q1・Q2 に試験を 2 通り足した)を受けて、コードは変えず、U4-c・U4-i を当て直し、足した 2 つの試験が落ちることを確かめた(上の表の 2 行)。
