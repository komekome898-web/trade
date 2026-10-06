# 担当 A の報告 — 批評家 1 回目の直し(2026-10-06、逐語)

## 報告(逐語)

# 担当 A の報告(批評家 1 回目の直し)

批評家の指摘 3 つを直し、どれも試験で確かめました。直しを外した写しでは、3 つとも試験が落ちます。本走らせ・コミット・押し出しはしていません。

批評家の全文 `docs/AUDITOR/VERDICTS/2026-10-06_rerun_A_critic1.md` は最初に全部読みました。

## 直したこと

**1. [止める] 1: カード 3 の目的の列が、消す run.npz にしか無い**(`scripts/w4_measure/rerun_check.py`)
- 置き場の `run_record.json` のカードが `c3_yen_premium_revert` のとき、または決定の持ち高に −1・0・+1 以外の値があるとき、`run.npz` を消す前に次の 2 つを書きます。
- `daily_lag1.csv`(day・pnl_bp・n):
  - 持ち高を 1 本遅らせた損益の、日本時間の日ごとの和です。
  - P1_t = e_t × (open_{t+3} ÷ open_{t+2} − 1) × 10,000。t+k は t の後の k 本目の空でない足で、`pnl.py` と同じ数え方です。
  - 最後の 3 決定には P1 がありません。
  - 書き出しは測定器の `daily_rows`・`write_daily` を使い、日は `daily.csv` と同じく決定の時刻の日です。
- `positions.npz`:
  - 決定の足の終わり `t_end_min`(int32、単位は分)と持ち高 `e`(float32)を、圧縮して書きます。
  - 読み返して、時刻が一致し、持ち高の差が 1e-6 以内であることを確かめます。
- 大きさの見込み:
  - 14 日(決定 20,526)の確かめで、1h が 52,547 バイト、1w が 64,325 バイトでした【事実】。
  - 全期間は 1 本 約 7〜9MB、3 本で 約 25MB です【推定: 決定の数に比例と見た】。
  - `daily_lag1.csv` は 1 本 約 80KB です【推定】。
  - git に入れる大きさかどうかの判断材料として A_jobs.md に書きました。

**2. [止める] 2: 再現していない 3 通りを 0 で通して npz を消す**(`rerun_check.py`)
- `--require-identical` を足しました。付けたときは、`daily.csv` の sha256 が元と同じとき(日の数・最後の日を含む全部の行)だけ通します。
- 満たさなければ 3 を返し、`run.npz` は残ります。A_jobs.md のコマンドは 0 のときだけ npz を消す形です。
- 調べるための数(`same_n_days`・`same_last_line` と日ごとの突き合わせ)は、通らないときも `rerun_check.json` に残します。
- A_jobs.md の A01〜A22(カード 1・2・3 の 22 本)にこの引数を足しました。A23・A24(カード 6 の延長)は付けず、今の形のままです。

**3. [直すとよい] 延長の終わりの境**(`scripts/w4_measure/common.py`)
- `usdjpy_ref_dataset(extend=True)` は、終わりが 2023-12-17T15:00Z を越えたら拒むようにしました(`USDJPY_EXTEND_END`)。
- 既定の `extend=False` と、ほかの口が使う `check_end`(境は 2023-12-18T00:00Z のまま)は変えていません。

**試験**(`tests/research/test_w4_rerun_cols.py`、20 件から 25 件に)
- 足した 5 件:
  - breaks.py の 7・8・9 の形を作り物で作り、`--require-identical` で 3 になり、壊さない形は 0 になる。
  - 引数なし(カード 6 の延長の形)では 8・9 の形が今までどおり通る。
  - 1 本遅らせた損益の手計算(下)。
  - 持ち高が ±1 のカードには `positions.npz` を書かない。
  - extend の終わりの上限。
- 手計算の試験: 8 本の足で、添字 2 は量 0。添字 0 は 0.5 × (104 ÷ 103 − 1) × 1e4、添字 1 は −0.25 × (105 ÷ 104 − 1) × 1e4、添字 3 は 1 × (106 ÷ 105 − 1) × 1e4、添字 4 は 0 です。日ごとの和(n = 4)と `positions.npz` の読み返しまで確かめます。
- 試験ファイルの頭で「`run_v2` と `common` が同じものか」を確かめていた行は、ほかの試験(d1b)が先に `run_v2` を読み込むと読み込みの段階で落ちました。この行をやめ、`run_b2` の関数が見ている `common` を使う形に直しました。

**変えていないもの**: `run_v2.py`・`run_b2.py`(この回は変更なし)、`card_trades.py`、`.gitignore`、カード 6 の CARD.md。

## 試験の結果

**足した試験のファイル**

`PYTHONPATH=src python -m pytest tests/research/test_w4_rerun_cols.py` → `25 passed in 1.99s`

**A のファイルを読む試験の全部**

`grep -rlE "w4_measure|card_trades|rerun_check|d1b" tests/` で見つかった 30 ファイルを打ちました。

`PYTHONPATH=src python -m pytest -p no:cacheprovider --continue-on-collection-errors -rfE <30 ファイル>` → `804 passed, 2 skipped in 85.70s`、終わりの値 0。

**批評家の breaks.py に `--require-identical` を足した写しで、批評家の短い走らせ(a_15m)を打った結果**

| 壊し方 | 終わりの値 | 落ちた確かめ |
|---|---|---|
| 0 壊さない | 0 | — |
| 1 中ほどの日に +1e-6 bp | 3 | reproduce・npz_vs_daily・trades |
| 2 持ち高を 1 決定だけ 0 に | 3 | reproduce・npz_vs_daily・trades |
| 3 high を 1 本だけ始値より下に | 3 | reproduce・high_low |
| 4 signal_color を 1 行反転 | 3 | reproduce・c2_kind |
| 5 signal_color を 1 行短く | 3 | reproduce・c2_kind・signals |
| 6 中ほどの日を 1 行消す | 3 | reproduce・npz_vs_daily・trades |
| **7 最後の日だけ +123 bp** | **3** | reproduce |
| **8 7 日 × 全期間の元** | **3** | reproduce |
| **9 元に最後の日が無い** | **3** | reproduce |

1〜6 で reproduce も落ちているのは、元が全期間で走らせ直しが 7 日のためです。

## 誤りを戻した写しで試験が落ちるか

一時置き場に台本と試験を写し、直しを 1 つずつ `if False:` で外して試験のファイルを打ちました。差分は 1 行ずつです。

| 写し | 外した直し | 結果 |
|---|---|---|
| 1 | `if needs_positions(z, a.dir):` | `2 failed, 23 passed`(test_lag1_pnl_by_hand・test_positions_written_only_for_card3_or_non_ternary) |
| 2 | `if require_identical:` | `1 failed, 24 passed`(test_require_identical_refuses_breaks_7_8_9) |
| 3 | `if extend and hi_ns > iso(USDJPY_EXTEND_END):` | `1 failed, 24 passed`(test_usdjpy_extend_end_capped_at_2023_12_17_15z) |

## 確かめの走らせ(カード 3、〜2017-09-01)

- 1h・1w とも、`rerun_check` は 0 を返し、`lag1_positions.ok` は True でした。
  - 1 本遅らせた損益は 20,523 決定分、持ち高は 20,526 決定分です。時刻の読み返しは一致し、float32 との差の最大は 2.9e-8 でした。
- 同じ短い置き場に `--require-identical` を付けると、どちらも 3 を返しました。元は全期間なので、そうなるのが正しい形です。
- 1w の最初の日の `daily_lag1` が 0.0 なのは、1 週の窓が埋まるまで持ち高が 0 だからです(カード 3 のコード)。

## A_jobs.md の変更

- A01〜A22 のコマンドに `--require-identical` を足しました。
- 終わる条件に「カード 1・2・3 は sha256 が元と同じ、カード 6 の延長は今の形」を書きました。
- git に入れるものに、カード 3 の `daily_lag1.csv`・`positions.npz` を足しました。
- 出力の表に、上の 2 つの意味と大きさの見込みを書き足しました。

台本と試験:
- /home/user/trade/scripts/w4_measure/rerun_check.py
- /home/user/trade/scripts/w4_measure/common.py
- /home/user/trade/tests/research/test_w4_rerun_cols.py

走らせ直しの一覧:
- /home/user/trade/docs/DISCUSSIONS/2026-10-06_held_batches/rerun/A_jobs.md

一時置き場の写し(breaks.py の写し・誤りを戻した写し・試験のログ):
- /tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/A_fix1/
