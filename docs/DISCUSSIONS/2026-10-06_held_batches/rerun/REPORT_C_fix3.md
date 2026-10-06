# 担当 C の報告 — 批評家 2 回目の直し(2026-10-06、逐語)

リードの確かめ: `PYTHONPATH=src python -m pytest tests/research/test_liq_cascade_fill.py tests/research/test_liq_cascade_v2.py` → 104 passed。壊し方 Q9(`c9_run_a.py:107` の `fill.TakerBook(tr, present_days)` を `fill.TakerBook(tr)`)をリードが当てて 1 failed、戻して 64 passed(test_liq_cascade_fill.py)。C_jobs.md の検めは 12-16 まで元と比べ、12-17 は新しい出力だけを数える形になったことを読んだ。リードの答え(問い 1・2)は `docs/AUDITOR/VERDICTS/2026-10-06_c9_rerun_critic2.md` に渡した批評家への依頼に書いた: 気配の時刻は transaction_time、前の日の気配は古さ 300 秒以内なら可。

## 報告(逐語)

批評家 2 回目の直しを全部入れました。試験は全部通り、壊した写しでは 9 通りとも試験が落ちました。07-01 の短い走らせでは、新しい検めも含めて違いと外れの合計が 0 です。本走らせ・コミット・押し出しはしていません。

## 1. 着手前の表

| やろうとすること | 原文の該当語(逐語) |
|---|---|
| C_jobs.md から 12-16〜12-17 の検めを消す。元との突き合わせは 12-16 までにし、12-17 は新しい出力だけ数える | リード「C_jobs.md L44 の … 検めは … 消す。check_repro の元との突き合わせは 2023-12-16 までにし、12-17 は新しい出力だけを数える(元のファイルを開かない)形に書き直す」 |
| `--orig` 側で 2023-12-17 以後の日を開こうとしたら止まる守り(試験つき) | リード「check_repro 自体にも、--orig の側で 2023-12-17 以後の日を開こうとしたら止まる守りを足す(試験つき)」 |
| 付け方ごとの値の欠けの数を出す。09-21 の気配の穴を書く | リード「付け方(主の気配・元の付け方・(b)・(a))ごとの値の欠けの数(レグ・連鎖)を出す。2023-09-21 の気配の穴 … を C_jobs.md に書く」 |
| 注文の大きさを考えない約定を限界として書く | リード「注文の大きさを考えない約定 … を、限界として C_jobs.md に 1 段書く(取り直しはしない)」 |
| Q9・Q10・Q11〜Q13・Q15 を捕まえる試験を足す | リード「試験を足す: Q9 … Q10 … Q11〜Q13 … Q15 … を、それぞれ捕まえる形」 |
| `in_px`・`out_px` を気配の表と突き合わせる検めを足す | リード「in_px・out_px を気配の表(data/c9_bookticker/days)と突き合わせる検めを足す(買いは売り気配・売りは買い気配)」 |
| 段 3 の窓の式を関数 `stage3_window` に切り出す(Q10 の試験のため) | (オーナーの逐語なし)リード「Q10(段 3 の窓を元に戻す)… を捕まえる形」 |

## 2. 元の走らせの表(変わらず)

| 項目 | 中身 |
|---|---|
| 台本 | `scripts/c9_run_a.py` と `src/bot/research/liq_cascade_v2.py`。状態機械は `scripts/o3c_signal_policy.py` |
| 引数 | `--start 2023-06-25 --end 2024-10-14 --out data/c9_run_a/full_20230625_20241014`。`--resume` で 3 回に分けて完走 |
| run_record | カード 9 には `run_record.json` がありません【事実】 |
| 指紋(sha256) | `run_meta.json` `0852ebb6…6fe2`、`policy_cascades.csv.gz` `657ae5b4…202d5b`、`policy_legs.csv.gz` `8b00c84b…e503b`。MANIFEST.md と一致【事実】 |

## 3. 直した台本の置き場と差分の要約

- **`docs/RESEARCH/cards/c9_liquidation_cascade/rerun_2026-10-06/check_repro.py`**
  - 守り: `read_orig` は 2023-12-17 以後の日を開こうとすると止まります。12-16 より後の日は元と比べず、新しい出力の行の数だけを数えます。
  - 足した検め `quote_checks`: `in_px`・`out_px`・`in_fill_ms`・`out_fill_ms` を、気配の表から `QuoteBook` で引き直した値と比べます(買いは売り気配・売りは買い気配)。表の置き場は `--quotes-dir` で渡します。
  - 足した数え上げ `missing_counts`: 付け方ごと(主の気配・元の付け方・(b)・(a))に、欠けた連鎖の数、その連鎖のレグの数、損益の列が NaN のレグの数を、日ごとと合計で出します。
- **`scripts/c9_run_a.py`**: 段 3 の窓の式を `stage3_window(day, fill_side)` に切り出しただけで、値は変わりません。
- **`tests/research/test_liq_cascade_fill.py`**: 試験を 7 つ足しました。

| 試験 | 捕まえるもの |
|---|---|
| `test_make_sim_passes_present_days_to_taker_columns` | Q9 |
| `test_stage3_window` | Q10 |
| `test_check_repro_specific_checks` | Q11〜Q13(1 つの検めだけが外れる形) |
| `test_read_quotes_orders_same_ms_by_update_id` | Q15(zip の中の同じ ms の行を逆順に置いた) |
| `test_check_repro_never_opens_orig_after_seal` | 守り(`read_orig` が止まる。`main` を 12-16〜17 で打っても、元の置き場の 12-17 は開かない) |
| `test_check_repro_quote_table_check` | 気配の表との突き合わせ |
| `test_check_repro_missing_counts` | 付け方ごとの欠けの数 |

- **`C_jobs.md`**(`docs/DISCUSSIONS/2026-10-06_held_batches/rerun/C_jobs.md`)
  - L44 の 12-16〜12-17 の検めは消しました。検めは `--start 2023-06-25 --end 2023-12-17` を 1 回打つ形にし、元と比べるのは 12-16 まで、12-17 は新しい出力だけを数えます。
  - 「限界と、データの穴」の節を足し、次の 3 つを書きました。
    - 注文の大きさを考えない約定(数量の列は取得で落とし、取り直しはしない)。
    - 2023-09-21 の気配の穴。
    - 2023-09-25 は気配のファイルが無い(目標の時刻 0 個)。
  - 状態の行を、批評家 2 回目の「走らせてよい(直しの後)」に合わせて直しました。

## 4. 走らせ直しの一覧

- 本数は 1 本、コマンドは前回と同じです。見込みは約 30〜60 分です【推定】。
- 走らせの後の検めの 1 行は次のとおりです。
  ```
  check_repro.py --orig data/c9_run_a/full_20230625_20241014 \
      --new data/c9_run_a/rerun_quote_20230625_20231217 \
      --start 2023-06-25 --end 2023-12-17 --ignore period --skip-policy 規則_3択 \
      --quotes-dir data/c9_bookticker
  ```
- 2023-09-21 の穴は、14 個とも同じ日の気配(最後が 18:05:10)で古さが 300 秒を越えるので、主の値が欠けになります【事実: `days/2023-09-21.csv.gz` の 414 個を数えた。目標の時刻は 19:11:20〜19:16:06】。欠けになる連鎖・レグの数は、走らせの後に (4) の数え上げで出ます。

## 5. 試験の結果

- `PYTHONPATH=src python -m pytest tests/research/test_liq_cascade_fill.py tests/research/test_liq_cascade_v2.py` は全部通りました。壊した写しを元に戻した後にも打ち直して、全部通りました。
- **壊して確かめた結果**: 台本 `scratchpad/mut/run_mut.py` で、ファイルを 1 か所ずつ書き換えて試験を打ち、そのつど元に戻しました。古いバイトコードが混ざらないよう、`PYTHONDONTWRITEBYTECODE=1` と毎回新しい `PYTHONPYCACHEPREFIX` を付けています。戻した後に `.mutbak` が残っていないことと、`git diff` も確かめました。9 通りとも試験が 1 つずつ落ちました。

| 壊し方 | 落ちた試験 |
|---|---|
| Q9 `fill.TakerBook(tr, present_days)` → `fill.TakerBook(tr)` | `test_make_sim_passes_present_days_to_taker_columns` |
| Q10 段 3 の窓を `window_days(day, 0, 1)` に戻す | `test_stage3_window` |
| Q11 「古さ > 300 秒」の数を 0 にする | `test_check_repro_specific_checks` |
| Q12 「連鎖の pnl_bp ≠ レグの和」の数を 0 にする | `test_check_repro_specific_checks` |
| Q13 「order_out ≠ −order_in」の数を 0 にする | `test_check_repro_specific_checks` |
| Q15 `read_quotes` の並びを update_id の逆順にする | `test_read_quotes_orders_same_ms_by_update_id` |
| 守り 1: `read_orig` の止めを消す | `test_check_repro_never_opens_orig_after_seal` |
| 守り 2: `main` が 12-17 以後も元と比べる | 同上 |
| 守り 3: 元の 12-17 を `read_orig` を通さずに開く | 同上 |

## 6. 確かめの走らせの結果(2023-07-01、境より前だけの読み口)

- 走らせ: `c9_run_a.py --start 2023-07-01 --end 2023-07-01 --data-root data/c9_run_a/cut_root_20231216 --fill-side quote --leg-path --quotes-dir data/c9_bookticker` → 終了コード 0。
- 検め: `check_repro.py … --start 2023-07-01 --end 2023-07-01 --ignore period --skip-policy 規則_3択` → 終了コード 0、出力の要点は次のとおりです。
  - 再現: 連鎖 276/276、レグ 298/298 で、違う値は無し。
  - 主の値の検め: レグ 298・欠けの無い連鎖 276 で、外れは無し。
  - 気配の表との突き合わせ: 引き直したレグ 298 で、外れは無し。
  - 付け方ごとの値の欠け: 主・元の付け方・(b)・(a) とも、欠けた連鎖 0・その連鎖のレグ 0・損益の列が NaN のレグ 0。
  - 違いと外れの合計: 0。
- 新しい検めが効くことの確かめ: 写しの 1 行の `in_px` を 0.1 下げると、「in_px・in_fill_ms ≠ 気配の表」が 1、「pnl_bp ≠ 値段から計算」が 1 になり、終了コード 1 でした。

## 7. 決めきれなかったこと(問い)

- 前回の問い 1(気配の時刻に `transaction_time` を使う)と問い 2(前の日の最後の気配を使う。今回の目標では 0 回)には、まだ答えをもらっていません。そのままの形で進めています。
- 読みの文書に限界を書くことは、リードの扱いなので触っていません。
