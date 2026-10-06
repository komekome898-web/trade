# 担当 A(カード 1・2・3・6)の報告(逐語、2026-10-06。この後リードの決め 6 つを返した)

# 担当 A(カード 1・2・3・6)の報告

台本の直し・試験・走らせ直しの一覧・短い期間の確かめは全部そろいました。ただし、走らせ直しで足す npz の見込み(約 1.8GB)が今の空き容量(1.4〜1.8GB)とほぼ同じで、このままでは 24 本を打ち切れない見込みです。本走らせ・コミット・押し出しはしていません。

## 1. 着手前の表

着手する前にこの表を出していませんでした。いまここで出します。

| やろうとすること | オーナーの原文の該当語(逐語) |
|---|---|
| カード 1・2・3・6 の走らせ直しの準備をする | L-717「**走らせ直し 27 本 … これ全部開始していいです**」 |
| 自分では走らせず、一覧を測定用のセッションに渡す | L-717「**測定は別のセッション**」 |
| 1 周で終える | L-718「**各束 1 周**」 |
| 足す列を、引数 `--extra-cols` を付けたときだけ出す | (オーナーの逐語なし)委任文「足す列は引数で出す」 |
| カード 2 の強い・弱いを、カードの判定の関数を import して記録する | (オーナーの逐語なし)委任文「カードの本体は写さず import する」 |
| 出力先を `rerun_2026-10-06/<変種>/run.npz` とする | (オーナーの逐語なし)委任文「走らせ直しの一覧のファイル」(根拠は弱い) |
| カード 6 の延長に `--usdjpy-2023` を足し、この引数なしで終わりが 2023 年に入るなら止める | **(該当語なし)** → 7 の問い 4 |

## 2. 元の走らせの表

カード 1・2・3 には `run_record.json` がありません【事実】。代わりに `measure.json`(無ければ `daily_stats.json`)の sha256 を載せます。sha256 はどれも先頭 16 桁です。

| カード・変種 | 台本と引数(各 `measure/README.md`) | 出力の置き場 | 記録の sha256 | daily.csv の sha256 |
|---|---|---|---|---|
| 1 default | `run_v2.py --card c1` → `measure_card` → `add_daily.py` | `c1_xborder_mom/measure/default` | measure.json `f787108536006645` | `6f25e2cec7c87fdd` |
| 2 a_1m | `run_c2_a_as_run.py`(全期間を一度に読んでから区切る。別の台本) | `c2_owner_xvenue_wick/measure/a_1m` | measure.json `6a78dedea673554e` | `7e9c8e1cc23d097b` |
| 2 a_3m | `run_v2.py --card c2 --variant a --foot 3` + `measure_card` | `…/measure/a_3m` | measure.json `61397c7473c926d3` | `4843c3b50c8db35c` |
| 2 a_5m | `run_v2.py --card c2 --variant a --foot 5` + `measure_card` | `…/measure/a_5m` | measure.json `44351c550d97a2f3` | `612e93a9ac5ba627` |
| 2 a_15m | `run_v2.py --card c2 --variant a --foot 15` + `measure_card` | `…/measure/a_15m` | measure.json `8109a968d434dbef` | `57137662207445e2` |
| 2 a_30m | `run_v2.py --card c2 --variant a --foot 30` + `measure_card` | `…/measure/a_30m` | measure.json `ab12ab7357b2635a` | `51d5fd2edc767c9a` |
| 2 a_60m | `run_v2.py --card c2 --variant a --foot 60` + `measure_card` | `…/measure/a_60m` | measure.json `27f91ea03cd103ab` | `3f6ce7c8f6a0a4d7` |
| 2 b_1m | `run_v2_bc.py --card c2 --variant b --foot 1 --light` | `…/measure/b_1m` | daily_stats.json `4e100d148605d4d3` | `51f6b50acecc93a3` |
| 2 b_3m | 同上(`--foot 3`) | `…/measure/b_3m` | daily_stats.json `fb367a74458ca0f6` | `d70d053348df8c32` |
| 2 b_5m | 同上(`--foot 5`) | `…/measure/b_5m` | daily_stats.json `8d9749921953ffe0` | `706c3c2b98a43e86` |
| 2 b_15m | 同上(`--foot 15`) | `…/measure/b_15m` | daily_stats.json `42cac4d27fd2b0b8` | `1de07323c9d1e2de` |
| 2 b_30m | 同上(`--foot 30`) | `…/measure/b_30m` | daily_stats.json `d6ddbeeb1e660137` | `91f4ceaa65ebba97` |
| 2 b_60m | 同上(`--foot 60`) | `…/measure/b_60m` | daily_stats.json `3ff0619ab1dc3f0e` | `845acadba332e047` |
| 2 c_1m | `run_v2_bc.py --card c2 --variant c --foot 1 --light` | `…/measure/c_1m` | daily_stats.json `7e52c9e0bf52d7ea` | `b09f376ca4c942b7` |
| 2 c_3m | 同上(`--foot 3`) | `…/measure/c_3m` | daily_stats.json `ea3417a0f18c9e33` | `92ed7e5ff4541c2d` |
| 2 c_5m | 同上(`--foot 5`) | `…/measure/c_5m` | daily_stats.json `46c751da5c9c1092` | `53e7ce64b1e00ecd` |
| 2 c_15m | 同上(`--foot 15`) | `…/measure/c_15m` | daily_stats.json `60d2722c76e8bede` | `32d6af860e012713` |
| 2 c_30m | 同上(`--foot 30`) | `…/measure/c_30m` | daily_stats.json `e76ad026a12afd5b` | `bc547dbc4da5e757` |
| 2 c_60m | 同上(`--foot 60`) | `…/measure/c_60m` | daily_stats.json `05304582966499e1` | `03985f3160f3c308` |
| 3 1h | `run_v2.py --card c3 --window 1h --from-npz` | `c3_yen_premium_revert/measure/1h` | measure.json `45e821edb6cb4d4c` | `31786686ebc5175c` |
| 3 1d | `run_v2.py --card c3 --window 1d --from-npz` | `…/measure/1d` | measure.json `ca9f06a03ff29cb9` | `7830610c22f28ec4` |
| 3 1w | `run_v2.py --card c3 --window 1w --from-npz --light` | `…/measure/1w` | daily_stats.json `279386a0528f8994` | `38c944a0dca7af82` |
| 6 btc | `run_b2.py --card c6 --variant btc` | `c6_weekend_gap_revert/measure/btc` | run_record.json `0de0be513c3e9f75` | `f4d08e644328bd46` |
| 6 usdjpy | `run_b2.py --card c6 --variant usdjpy` | `…/measure/usdjpy` | run_record.json `8d1aa93da95eb6f1` | `07fefce50d6091d6` |

【事実: `sha256sum` と各 README】。カード 2 の b・c を走らせた `run_v2_bc.py` は、`run_v2.py` に「npz に高値・安値を足す 1 行」を加えた写しです(README の diff)。

## 3. 直した台本の置き場と差分

既定(引数なし)の挙動は変えていません。直したのは次の 4 つです。

- **`scripts/w4_measure/run_v2.py`**
  - 引数 `--extra-cols` を足しました。`--no-measure` と `--save-root` を一緒に付けたときだけ動き、`--light`・`--from-npz` とは一緒に使えません。元の置き場 `measure/<変種>/` には書きません。
  - 付けたときの npz は `<置き場>/run.npz` で、今までの 7 列に高値 `high`・安値 `low` が加わります。
  - カード 2 は合図ごとに `signal_color`(+1 陽線 / −1 陰線)と `signal_strong`(色と合図の向きが同じ = 強い)を、`signal_log` と同じ並びで残します。
  - 色の取り方: カードのクラスを継ぎ、`_apply` の前にカードの `classify_detail` を import して呼び、`signal_log` に行が足された判定のときだけ色を記録します。持ち高の更新はカードの `_apply` のままです。
  - 同じ置き場に `daily.csv`(測定器の `daily_rows`・`write_daily`)と `run_record.json`(引数・区切り・入力の sha256・所要・npz の列)を書きます。
  - 引数なしのときの名前・列は今までと同じです(試験で確かめました)。
- **`scripts/w4_measure/common.py`**(共通の道具)
  - `USDJPY_PATH_2023 = "backtest_data/fx_usdjpy_1m_20260822.csv.gz"` を足しました。
  - `usdjpy_ref_dataset(..., extend=False)`: `extend=True` で、終わりが 2023-01-01 より後のときだけ上のファイルを後ろに足します。既定は今までと同じ 1 ファイルです。封印の境より後は今までどおり拒みます。
- **`scripts/w4_measure/run_b2.py`**
  - 引数 `--usdjpy-2023` を足しました(カード 6 だけ)。`check()` の経路にも渡します。
  - カード 6 で終わりが 2023-01-01 より後なのにこの引数が無ければ、読む前に止めます。止めないと、2023 年の週明けが 1 つも無い走らせになります。
- **`scripts/w4_measure/rerun_check.py`**(新規)
  - 元の `daily.csv` との突き合わせ: 全部同じなら sha256 が一致します。期間が違うときは、短い方の最後の日より前の日を行の文字列で突き合わせます。
  - 足した列の意味: 量が 0 でない足で高値 ≥ 始値・終値、安値 ≤ 始値・終値。カード 2 は `signal_color` と `signal_log` の行の数がそろい、強い = 色と向きが同じ。
  - npz から計算し直した日ごとの和が、同じ置き場の `daily.csv` と同じか。
  - 結果は `rerun_check.json` に書き、全部通れば 0、どれかが通らなければ 3 を返します。
- **試験**: `tests/research/test_w4_rerun_cols.py`(新規。作り物のデータだけ使います)。

## 4. 走らせ直しの一覧

- 置き場: `docs/DISCUSSIONS/2026-10-06_held_batches/rerun/A_jobs.md`
- 本数: 24 本(カード 1 が 1 本、カード 2 が 18 本、カード 3 が 3 本、カード 6 の延長が 2 本)。
- 見込みの時間: 1 本ずつなら合計 約 30,500 秒(約 8.5 時間)、3 本同時なら約 3 時間【推定】。
  - 1 本ごとの元になる数は、前の回の「区切りの run_card」の秒です【事実: 各 README】。カード 1 は 1,154 秒、カード 2 の a は 1,814〜1,888 秒、b は 955〜1,106 秒、c は 1,075〜1,272 秒、カード 3 は 1,073〜1,087 秒。
  - カード 6 は、前の回の 678 秒 × 日数の比で 約 800 秒と見ました【推定】。
- 一覧のファイルには、終わる条件・上限(1 周)・`rerun_check` が 3 を返したらそのカードの残りを打たずに止めること・空き容量を先に見ること・npz をコミットしないこと・「未コミットの直しが前提」の 1 行を書きました。
- 出力先は `docs/RESEARCH/cards/<カード>/rerun_2026-10-06/<変種>/` です。カード 6 は `…/rerun_2026-10-06/ext_2023-12-17/<変種>/` です。
- 再現の見込み【推定】:
  - カード 1・2・3 は元と同じ期間なので、`daily.csv` の sha256 が元と一致するはずです。
  - カード 6 は、元の最後の日(2022-12-31)を除いた 1,977 日が一致し、2023 年の日が足されるはずです。

## 5. 試験の結果

**足した試験だけ**

`PYTHONPATH=src python -m pytest tests/research/test_w4_rerun_cols.py` → `16 passed in 0.77s`

**台本を読む試験とあわせて**

`PYTHONPATH=src python -m pytest -rfE tests/research/test_w4_rerun_cols.py tests/research/test_window1_loader.py tests/research/test_c8_binance.py tests/test_backtest_chart.py tests/research/test_katsuo_limit_sim.py tests/research/test_matilda_limit_sim.py tests/research/test_c2_limit_run_ref_filter.py tests/research/test_c4_w6b_order.py` → `577 passed, 2 skipped in 193.91s`

**全部の試験(容器の再起動の後に打ち直したもの)**

`PYTHONPATH=src python -m pytest -p no:cacheprovider --continue-on-collection-errors -rfE --junitxml=…` → `22384 passed, 14 skipped, 4 warnings, 2 errors in 2860.50s`、終わりの値 1。

2 つの errors はどちらも試験の読み込みでのエラーで、担当 A の変更が原因ではありません【事実】:

- **`tests/research/test_c8_binance.py`**: `ImportError: cannot import name 'BIN_DIR' from 'common' (…/tests/bt/battery/item_0/adapters/common.py)`。同じ名前 `common` の別のファイルとぶつかっています。HEAD の中身(`git archive HEAD` で写したもの)で読み込むだけの試験を打っても、同じ `ImportError` が出ました。単独なら `26 passed`。
- **`tests/research/test_d1b_g3.py`**: `ImportError: cannot import name 'MIN_NS' from 'common' (…/adapters/common.py)`。同じぶつかり方です。ほかの担当の未追跡の新しいファイルです。単独なら `19 passed`。

再起動の前の 1 回目の全部の走らせ(93% で止まった回)には F が 3 つありました。進み具合の印と集めた試験の並びから、`test_i3_battery_scenes.py::test_scene[v16-run-tabs]`・`[v19-warning-all-tabs]`・`test_backtest_chart.py::test_two_runs_share_one_store_and_the_second_does_not_parse` と推しました【推定】。この 3 つは単独で `3 passed`、打ち直した全部の走らせでも F は 0 でした。

## 6. 確かめの走らせの結果

確かめはどれも、元の期間の始まりから打ちました。出力は作業用の一時置き場です。

| 走らせ | 決定 | 元との突き合わせ(最後の日を除く) | 高値・安値 | カード 2 の強い・弱い |
|---|---|---|---|---|
| カード 1 default、〜2017-09-01 | 20,526 | 14 日すべて一致 | 違反 0 | — |
| カード 2 a_15m | 20,526 | 14 日すべて一致 | 違反 0 | 合図 856 = 色 856(強い買い 202・強い売り 235・弱い買い 190・弱い売り 229) |
| カード 2 b_15m、2020-01-01T15Z〜01-15 | 19,091 | 13 日すべて一致 | 違反 0 | 363 = 363 |
| カード 2 c_15m | 20,526 | 14 日すべて一致 | 違反 0 | 542 = 542 |
| カード 2 a_1m(元は別の台本) | 20,526 | 14 日すべて一致 | 違反 0 | 415 = 415 |
| カード 3 1h・1w | 20,526 | 14 日すべて一致 | 違反 0 | — |
| カード 6 btc・usdjpy、2017-08-01T15Z〜09-01 | 43,377 | 30 日すべて一致。保存済みの `run.npz` と同じ足 43,378 本で、持ち高・高値・安値がビット一致 | 違反 0 | — |

どの走らせでも、npz から計算し直した日ごとの和は同じ置き場の `daily.csv` と同じでした【事実】。

**カード 6 の延長(2022-12-18T15Z〜2023-01-15T15Z、`--usdjpy-2023` 付き)**

- 引数なしで打つと、読む前に「…2023 年からの USDJPY を読むには --usdjpy-2023 が要る」で止まり、出力の置き場は作られませんでした【事実】。
- 引数ありでは、封印の門(`load_reference`)が 2023 年のファイルを通しました。記録の中身は `["backtest_data/fx_usdjpy_1m_20260822.csv.gz", "a08b4ae1…", 1640160, 18180]` で、読んだ行 1,640,160 のうち範囲の中の 18,180 行を使った形です【事実】。範囲の外の行は値を使わずに飛ばしています(`reference.py` 378 行)。
- 週明けの行は 2022-12-25T22:04Z・2023-01-01T22:00Z・2023-01-08T22:00Z の 3 つで、2023 年の 2 つが見つかりました。
- 書き直しとの突き合わせ: 窓の外で持ち高が 0 でない決定 0、usdjpy で向きの食い違い 0。
- 2022-12-25〜31 の持ち高は、保存済みの `run.npz` とビット一致しました【事実】。
- 2023 年のファイルの close が BID の値かは【推定】です。2017〜2022 年の置き場の README が、列の並びをこのファイルにそろえたと書いていることからの推しで、ファイルそのものは開いていません。

## 7. 決めきれなかったこと(問い)

1. **空き容量**: `df -h /` の空きは 1.4〜1.8GB【事実】、24 本の npz の見込みは約 1.8GB【推定】で、このままでは足りない見込みです。打つ前にどう空けるかを決めてもらう必要があります。一時置き場の 3.4GB の大半はリードの別の作業のファイルなので、私は消していません。
2. **`.gitignore`**: 出力先の `run.npz` は今の無視の型(`docs/RESEARCH/cards/*/measure/*/run.npz`)に当たりません。`docs/RESEARCH/cards/*/rerun_2026-10-06/**/run.npz` を足すかを決めてもらう必要があります。
3. **カード 6 の CARD.md(迷った点 4)**: 2023 年のファイルを「使うデータと遅れ」に足さないと `check_card` がこのファイルを見ない、と CARD.md に書かれています。CARD.md は変えていません。
4. **`--usdjpy-2023` と止め**: どちらも私が決めた形で、オーナーの逐語はありません。別の形は「終わりが 2023-01-01 を越えたら自動で足す」です。
5. **カード 1 の Binance の値**: npz に参照の値(`ref_time`・`ref_value`)は足していません。D0 が「Binance の 1 分足は別に読む」と書いているのに合わせました。足すかを決めてもらう必要があります。
6. **`run_v2.py` の欠けた import**: `run_v2.py` は `run_c2`・`run_c3`・`check_v2` を読みますが、どれもリポジトリにありません。カード 2・3 の測定の経路と `--light` の経路はこのままでは動きません。走らせ直しは `--no-measure` なので影響はなく、範囲の外なので手を付けていません。

台本と試験:
- /home/user/trade/scripts/w4_measure/run_v2.py
- /home/user/trade/scripts/w4_measure/run_b2.py
- /home/user/trade/scripts/w4_measure/common.py
- /home/user/trade/scripts/w4_measure/rerun_check.py
- /home/user/trade/tests/research/test_w4_rerun_cols.py

走らせ直しの一覧:
- /home/user/trade/docs/DISCUSSIONS/2026-10-06_held_batches/rerun/A_jobs.md
