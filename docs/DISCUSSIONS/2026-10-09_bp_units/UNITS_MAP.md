# マチルダ本測定の数の単位の地図(L-915 の調べ。突き合わせの作業者が最初に読む)

リードがコードを読んで作った(2026-10-09 17:5x JST)。行番号は 9d35f590 の時点。

## 1. 量と単位

| 名前 | 中身 | 作る場所 | 1 単位 |
|---|---|---|---|
| pnl_jpy | 取引 1 本の損益(円) | `scripts/analysis/simple_trades.py:83`(取引の行 `backtest_runs_shared/matilda_main_trades/<本>/trades.csv.gz` の列) | 1 円 |
| pnl_bp(マチルダ) | pnl_jpy ÷ 200,000 × 10,000(口座 20 万円に対する bp) | `simple_trades.py:83`(同じ取引の行の列) | **1 bp = 20 円** |
| move_bp | 値段の変化率 × 10,000(値動き。損益ではない) | `scripts/analysis/diag_paths.py:111-112`(MFE・MAE)、`:119`(出の後の値動き)、`:127`(合図の後の値動き) | 値段の 0.01% |
| カードの pnl_bp | 建玉 × 値段の変化率 × 10,000 の和(`scripts/analysis/card_trades.py:11`・`:102`) | カードの測定の台本 | マチルダ本測定では使っていない(使っていたら誤り) |

## 2. 出力ファイルごとの単位

| 出力 | 作る台本 | 損益の単位 | 値動きの単位 |
|---|---|---|---|
| `docs/RESEARCH/matilda_main/<本>/diag_tables.md`・`.json` | `diag_tables.py` | **pnl_bp(bp と書いてある。1 bp = 20 円)**。D1 bp/日、D3 bp・bp/取引、D6 bp/取引、D7 bp/日・突き合わせの和 bp | 無し |
| `docs/RESEARCH/matilda_main/<本>/diag_paths.md`・`.json` | `diag_paths.py` | D4 の群の「損益の和」は **pnl_bp**(単位名なし) | MFE・MAE・出の後・D5 は move_bp(「bp」とだけ書いてある) |
| `docs/RESEARCH/matilda_main/<族>/fam_tables.md` | `fam_tables.py`(`diag_tables.json`・`diag_paths.json` を読み、損益は `y()` で × 20 して円) | 円(D1・D3・D6・D7・D4 の和) | move_bp(D4 の MFE・MAE、出の後、D5)はそのまま |
| `half_diff.out`・`half_diff_rest.out`・`both_halves.out`・`same_bar_daily*.out`・`foot/foot_boundary` の出力 | `half_diff.py`・`both_halves.py`・`same_bar_daily.py`・`foot/foot_boundary.py`(読み口の関数で bp を計算し × 20) | 円 | 無し |
| `compare.md`(族ごと)・`band_migration.out`・`six_bands.out`・`zero_reason.out`・`held_blocked.out`・`gate_overlap.out`・`levels_band.out`・`levels_reason.out`・`scene_diff.out`・`d7_fullperiod.out` ほか | `compare_family.py`・`band_migration.py` ほか(pnl_jpy を直接読む) | 円 | 無し |
| `blocked_<本>.md`(外した合図の読み) | `diag_paths.py --blocked-from` | D4 の和は pnl_bp | move_bp |

## 3. 分かっている問題(リードが見つけたもの。作業者は鵜呑みにせず確かめる)

- 読み口の D7 は 2 本の期間の共通の日だけで差を取る(`diag_tables.py:367`)。期間の始まりが基準と違う本は基準だけの日が落ちる(range_hi_p75・p90・break_len_mult_4・count_80・foot_5・count_20)。
- 段数の族の文書 `levels.md` は D1 の年ごと・D6・D7・突き合わせを bp のまま載せている。台帳 K-317 の「+42.83 bp/日」。
- range_hi の文書 D4 の表は円の値なのに出所を `diag_paths.md`(bp)と書いている。
