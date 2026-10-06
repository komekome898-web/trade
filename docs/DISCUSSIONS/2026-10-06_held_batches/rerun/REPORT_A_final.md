# 担当 A の最終の報告(2026-10-06、逐語)

## 報告(逐語)

# 担当 A の最終の報告(リードの決め 6 つを入れた後)

全体の試験は終わりました。担当 A の変更が原因の失敗は見つかっていません。落ちた試験 1 件と読み込みのエラー 2 件は、どれも担当 A のファイルを読まない試験です。本走らせ・コミット・押し出しはしていません。

## 全体の試験の結果

`PYTHONPATH=src python -m pytest -p no:cacheprovider --continue-on-collection-errors -rfE` → `1 failed, 22410 passed, 14 skipped, 4 warnings, 2 errors in 2294.02s`、終わりの値 1【事実】。

- **落ちた試験: `tests/bt/item_3/test_i3_battery_scenes.py::test_scene[v8-run-id]`**
  - 出力: `AssertionError: 等しい組 [[0], [1, 2], [3], [4]]、正解 [[0, 1, 2], [3], [4]]`。実行 ID が内容のハッシュになっているかを見る場面の試験です。
  - このファイルを単独で打つと `54 passed in 35.76s` でした【事実】。
  - このファイルが読むのは `i3_driver`・`i3_judge`・`i3_scenes` で、担当 A のファイルは読みません【事実: import の行】。
  - 同じファイルは全部の走らせのたびに違う場面で落ちています(1 回目は v16・v19、2 回目は 0 件、今回は v8)。ほかの担当の走らせと重なって負荷が高いときに揺れる試験と見ています【推定】。
- **読み込みのエラー: `tests/research/test_c8_binance.py`・`tests/research/test_d1b_g3.py`**
  - どちらも `ImportError: cannot import name ... from 'common' (tests/bt/battery/item_0/adapters/common.py)` で、同じ名前 `common` の別のファイルとぶつかっています。
  - 前者は HEAD の中身でも同じエラーが出ます。後者はほかの担当の新しい未追跡のファイルです。
  - 単独なら、前者は今回 `test_w4_rerun_cols.py` などとまとめて打った 581 passed の中で通り(前回は単独で 26 passed)、後者は単独で 19 passed です【事実】。

担当 A の台本を読む試験だけをまとめて打つと、`test_w4_rerun_cols.py` など 8 ファイルで `581 passed, 2 skipped in 81.33s` でした【事実】。

## 前回の報告からの差分(リードの決め 6 つを入れた分)

| ファイル | 変更 | 理由 |
|---|---|---|
| `scripts/w4_measure/rerun_check.py` | `write_trades_check` を足した。既にある読み口 `scripts/analysis/card_trades.py` の `build`・`write_trades`・`load_daily` を import して(写さない)、`run.npz` から `trades.csv.gz`(signal_t・entry_t・exit_t・side・pnl_bp)を書き、確かめる | 決め 3 (i) |
| 同上 | `write_signals` を足した。カード 2 の `signals.csv.gz`(signal_t = 海外の足の終わり・side・signal_color・signal_strong、並びは signal_log のまま)を書き、行の数が signal_log と同じかを見る | 決め 3 (ii) |
| 同上 | 終わりの値に (4)(5) を足した。3 のときは `run.npz` を消さずに残す決まりを説明に書いた | 決め 1 |
| `tests/research/test_w4_rerun_cols.py` | 試験を 4 つ足した(16 → 20 件) | 決めの最後の「試験」 |
| `docs/DISCUSSIONS/2026-10-06_held_batches/rerun/A_jobs.md` | 下の「A_jobs.md の変更」 | 決め 1・2・4・6 |

足した 4 つの試験:
1. 日本時間の 0 時をまたぐ取引が無い作り物で、`trades.csv.gz` を合図の日ごとに足した和が `daily.csv` と一致する。
2. 取引の行を 1 行落とすと確かめが止まる(3 を返す)。
3. `signals.csv.gz` の行の数が `signal_log` と一致し、4 通り(強い買い・弱い売り・弱い買い・強い売り)の値と時刻がそろう。
4. 行の数がそろわなければ書かない。

A_jobs.md の変更:
- 1 本ごとの順を「走らせる → `rerun_check.py`(確かめと小さな出力)→ 0 のときだけ `run.npz` を消す」にし、24 本のコマンドの終わりに `&& rm …/run.npz` を足した。
- git に入れるものを並べ、`.gitignore` はリードが足すと書いた。
- 「2023 年の USDJPY のファイルは CARD.md の『使うデータ』に無い。check_card はこのファイルを見ない」を 1 行書いた。
- 「`run_v2.py` は `--no-measure` の経路だけを使う」の注を足した。
- 大きさの見込みを書き直した。消す `run.npz` は 1 本 約 50〜110MB【推定】。git に入れる `trades.csv.gz` は全期間でカード 3 1h が約 6MB、ほかは 0.2〜3MB【推定: 14 日の確かめの大きさに比例と見た】。

変えていないもの:
- `scripts/analysis/card_trades.py`: 引数を足す必要は無かったので、変えていません。`main()` は `extra.json` を要るので使わず、`build`・`write_trades` を直接呼んでいます。
- `run_v2.py`・`run_b2.py`・`common.py`: 前回の報告から変えていません。
- `.gitignore`・カード 6 の CARD.md: 触っていません。
- カード 1 の npz に Binance の値は足していません(決め 5)。

`trades.csv.gz` の日ごとの和について(実データで分かったこと):
- 判定に使うのは、card_trades が決定の日ごとに計算し直した和と `daily.csv` の一致、および取引の和と `daily.csv` の和の一致(小数 6 桁の丸めの分だけ許す)です。
- 取引を合図の日に寄せた日ごとの和は、日本時間の 0 時をまたいで持った取引の日で `daily.csv` と合わないのが正しいので、判定に入れず数だけ書いています。短い期間の確かめでは、14 日のうち 6〜14 日がこれに当たりました【事実】。作り物の試験では、0 時をまたがない作り物で日ごとの一致を確かめています。

## 確かめの走らせ(打ち直し)

コマンドは A_jobs.md と同じ形(走らせ → `rerun_check` → 0 なら `run.npz` を消す)で、出力は一時置き場です。

| 走らせ | 終わりの値 | 元との日の突き合わせ | 取引の行 | 合図の行 |
|---|---|---|---|---|
| カード 1 default、〜2017-09-01 | 0 | 14 日すべて一致 | 624 本(買い 302・売り 322)、決定の日ごとの和の食い違い 0、和 986.015903 / 986.015906 | — |
| カード 2 a_1m・a_15m・b_15m・c_15m | すべて 0 | 13〜14 日すべて一致 | 158〜295 本、食い違い 0 | 415 / 856 / 363 / 542 行 = signal_log の行の数 |
| カード 3 1h・1d・1w | すべて 0 | 14 日すべて一致 | 3,744 / 1,762 / 837 本、食い違い 0 | — |
| カード 6 btc・usdjpy、2017-08 | 0 | 30 日すべて一致 | 各 4 本、食い違い 0 | — |
| カード 6 延長、2022-12-18〜2023-01-15、`--usdjpy-2023` 付き | 走らせは 0 | — | — | — |

- どの走らせでも、終わった後の置き場に `run.npz` は残っていません【事実: ls】。
- カード 6 の延長では、封印の門が 2023 年のファイルの 1,640,160 行を読み、範囲の中の 18,180 行を使いました。週明けの行は 3 つ(2022-12-25・2023-01-01・2023-01-08)で、書き直しとの食い違いは 0 でした【事実】。

台本と試験:
- /home/user/trade/scripts/w4_measure/rerun_check.py
- /home/user/trade/scripts/w4_measure/run_v2.py
- /home/user/trade/scripts/w4_measure/run_b2.py
- /home/user/trade/scripts/w4_measure/common.py
- /home/user/trade/tests/research/test_w4_rerun_cols.py

走らせ直しの一覧:
- /home/user/trade/docs/DISCUSSIONS/2026-10-06_held_batches/rerun/A_jobs.md
