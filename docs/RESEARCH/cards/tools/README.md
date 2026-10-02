# 結果の文書の表を作った台本(2026-10-03 にリポジトリへ移した)

結果の文書(`../W4_first3_RESULTS.md`・`../W4_overnight_RESULTS.md`)と「なぜ」の診断(`../diag_why/`・`../c2_owner_xvenue_wick/diag_leadlag/`)の数字の出所。台本ははじめ会話の作業場所(scratchpad、セッションが終わると消える)に置いていた。

| 台本 | 何を出したか | 出力 |
|---|---|---|
| `goal_table.py` | 最初の 3 枚の表 1 の目標の列(1 取引あたり・勝率・保有・月の円・最大の落ち込みほか) | `goal_table.json`・`goal_table.out` |
| `goal_table2.py` | 夜の 20 本の表 1 の目標の列 | `goal_table2.json` |
| `winloss_shape.py` | 夜の結果の「勝ち負けの形」(カード 5・8) | `winloss_shape.out` |
| `pertrade_by_year.py` | カード 2(現物 1m・3m、USD-M 1m、BitMEX 1m・3m)とカード 1 の年ごとの取引の回数・1 取引あたり | `pertrade_by_year.out` |

- 入力の 1 分ごとの npz のうち、カード 1・2・3 の分(`scratchpad/w4/measure/runs/…`)は大きいのでリポジトリに入れていない。作り直し方は各 `measure/README.md` の走らせ方。カード 5〜8 の npz は各 `measure/<変種>/run.npz`(git の外、`.gitignore`)。
- 台本の中のパスは scratchpad を指したまま(書き換えていない)。
- 夜の表の「最大の落ち込み」「最悪の月」「プラスの月」は、`goal_table2.py` の値ではなく測定器の `daily.csv` から計算し直した値を載せた(`../W4_overnight_RESULTS.md` の「読み方」)。
