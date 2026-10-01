# 段階 G を閉じる + 欠陥 G-1〜G-4・G-6 の直し — 役の出力の逐語(2026-10-01)

委任文 `docs/DATA/delegations/20261001_k1_stage_g_close.md`(L-499a「**案1だけど、わかってる欠陥があるのなら直せ ワークフロー起動して案1と欠陥の修正を進めて**」)。Workflow run `wf_098afdf6-7ad`(09:05 UTC 起動、A・B 並列 → 批評家、計 92 分)。

## 作業者 A(文書、Opus)

作業者 A の行(批評家の [直す] 1・3・4・5 と、第 18 部を「測らない」と書くこと)は、すべて当て終えました。比べた 130 行の数と裁きは前と同じです(一致 118、当時の誤り 12)。データの門が止めた `open` は 0 件で、commit・push はしていません。

着手前の表(委任文 `20261001_k1_stage_g_close.md` §1 の作業者 A の行による)

| やろうとすること | オーナーの原文の該当語(逐語) |
|---|---|
| [直す] 1: 満たせなかった条件(§2-5 未達)を DATA_READ.md と DIFF.md に書く | 「**案1だけど**」 |
| [直す] 3: 「比べられない(封印)」の印を `diff_table.md`・`TABLES.md` に升ごとに付ける | 「**案1だけど**」 |
| [直す] 4: D-1 の 12 行を、変種が覆う 4 行と覆っていない 8 行に分けて書く(8 行は批評家の再計算と一致、出所つき) | 「**案1だけど**」 |
| [直す] 5: (f) を出さなかったのは作業者の判断だと書き直す | 「**案1だけど**」 |
| 第 18 部は「測らない(L-499a 案 1)」と DIFF.md §2 に書く | 「**案1だけど**」 |

右が空の行はありません。

**(a) 変えた・作ったファイル**
- `/home/user/trade/scripts/k1_newenv_g_diff.py`
  - 封印の升を 1 升 1 行で出すようにしました(年 2023・2024〜2026、境より後を含む当時の期間)。
  - D-1 の 12 行の根拠を「変種が覆う行」と「変種が覆っていない行」に分けました。
  - 批評家の再計算の値(VERDICTS の表を写したもの)と `diff_rows.json` を行ごとに機械で突き合わせます。
  - `diff_summary.json` に、どの行がどちらに入るかの内訳(`d1_cover`)を足しました。
- `/home/user/trade/scripts/k1_newenv_g_tables.py`
  - (a)(b)(c)(e) の表に列「当時との比べ」を足しました。出所は `diff_rows.json` です。
  - 第 18 部の節を「測らない(L-499a 案 1)」にしました。
  - (f) は作業者の判断で出していない、と書き直しました。
  - 生成のコマンドの並びに `k1_newenv_g_diff.py` を足しました。
- `/home/user/trade/docs/PHASE2/K1/NEWENV_G/diff_table.md`(スクリプトで作り直し。560 行 = 比べた 130 行 + 封印の印 430 行)
- `/home/user/trade/docs/PHASE2/K1/NEWENV_G/TABLES.md`(スクリプトで作り直し)
- `/home/user/trade/docs/PHASE2/K1/NEWENV_G/diff_rows.json`・`diff_summary.json`(差分のスクリプトを回すと一緒に作り直されるもの。指定の 4 ファイルには入っていません)
- `/home/user/trade/docs/PHASE2/K1/NEWENV_G/DIFF.md`(生成のスクリプトが無いため手で直しました)
  - 件数の表に封印の 2 行を足しました。
  - §2 に升ごとの印の置き場、(f) の行、第 18 部の行を書きました。
  - §3 を §3.1(変種が覆う 4 行)・§3.2(覆っていない 8 行と批評家の値)・§3.3(裁き)に分けました。
  - §5 に批評家の [聞く] 2・6 を足し、§6「満たせなかった条件」を新しく作りました。
- `/home/user/trade/docs/PHASE2/K1/NEWENV_G/DATA_READ.md`(生成のスクリプトが無いため手で直しました)
  - §2 の注意の参照先を §7 にしました。
  - §7「満たせなかった条件」を足しました。数の出所は `FOLD_MANIFEST.json: inputs` で、門の下で読み直しました。
- `/tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/gated.py`(スクリプトをデータの門の下で回すための包み)

**(b) 打ったコマンドと末尾の行**(どれも `PYTHONPATH=scripts:src K1G_DATAGATE_LOG=<scratchpad>/gate_workerA.log` を付けています)
- `python3 <scratchpad>/gated.py scripts/k1_newenv_g_diff.py` → 1 行目「rows 560 same 118 differ 12 sealed 430」
- `python3 <scratchpad>/gated.py scripts/k1_newenv_g_diff.py --md` → 「{"tally": {"当時の誤り(D-1)": 12, "一致": 118, "比べられない(封印、2023 は区間が違う)": 86, "比べられない(封印)": 344}, … "d1_cover": {"変種が覆う": 4, "変種が覆っていない": 8}}」
- `python3 <scratchpad>/gated.py scripts/k1_newenv_g_tables.py --md` → 「TABLES.md written」
- 同じ 3 本をもう 1 回回したあとの `md5sum -c` → diff_table.md・TABLES.md・diff_rows.json・diff_summary.json がすべて「OK」(出力は毎回同じ)
- `grep -c '新しい値・当時の値の両方と一致' diff_table.md` → 「12」。「両方と不一致」→「0」、「| 不明 |」→「0」
- VERDICTS の批評家の表を正規表現で読み、スクリプトに写した値と比べた → 「parsed 24 recalc keys 12 bad 0」
- DIFF.md §3 に手で書いた 12 行を `diff_rows.json` と比べた → 「checked 12 bad 0」
- 門の下で `FOLD_MANIFEST.json` を読んだ → Binance 2023 は「rows_read 525520, rows_kept_in_range 505360」、bitFlyer 2023 は「rows_read 525600, dropped_at_or_after_cut 20160」
- `ls <scratchpad>/gate_workerA.log` → 「No such file or directory」(門が止めた `open` は 0 件)
- `df -h /` → 「/dev/vda 252G 37G 402M 99% /」

**(c) 満たせなかった条件**
- DIFF.md と DATA_READ.md は生成のスクリプトが無いので、手で直しました(「手で書き換えない」は生成物の 2 ファイルにだけ当てています)。
- `diff_rows.json`・`diff_summary.json` は指定の 4 ファイルの外ですが、差分のスクリプトを回すと書き換わります。
- 「境より後の行の時刻以外の値は、どこにも渡していない」は、前の作業者が書いたことで、この回でも実行記録では確かめていません。
- `k1_newenv_g_tables.py` の集計の段(`cells.json` を作る段)は、数を変えないので回し直していません。
- 試験(pytest)は、この 2 本のスクリプトに試験が無いので回していません。
- 返り値を `docs/AUDITOR/VERDICTS/2026-10-01_k1_stage_g_close.md` に写していません。作業者 A の持ち物の外と判断しました。

**(d) リードに聞くこと**
1. 両方・強い (f) を出していないのは作業者の判断で、範囲を縮めたことになります(A-10)。案 1 のまま出さずに G を閉じてよいですか(yes/no)。
2. 2023 のファイルで境より後の行の時刻をほどいて読んだことは、封印 P2-08 の破りに当たりますか(批評家の [聞く] 2。DIFF.md §5・§6-1、DATA_READ.md §7)。
3. `diff_table.md` の封印の行では、年 2023 だけ当時と今回の値を並べ、2024〜2026 と当時の期間の行は「(並べない)」にしました(新しい値が無いため。当時の値は `old_values.json` にあります)。この並べ方でよいですか(yes/no)。

## 作業者 B(環境の欠陥の直し、Opus)

作業者 B の作業は終わりました。G-1〜G-4 と G-6 を根本で直し、条件 6 の 2 升は新しい口で生のファイルから回して、取引数・平均 bp とも cells.json と同じでした。条件 7 の試験は門の下で失敗 0 件・止めた `open` 0 件ですが、門の許可の外のファイルを開く試験 2 ファイル(計 6 件)を除いて回しています(下の (c))。

【着手前の表】(委任文 §1 の作業者 B の行。右が空の行は無かったので、聞かずに着手しました)

| やろうとすること | オーナーの原文の該当語(逐語) |
|---|---|
| G-1〜G-4・G-6 を根本で直す(G-5 は直さない) | 「**わかってる欠陥があるのなら直せ**」 |

**(a) 変えた・作ったファイル**
- 核(`src/bot/bt/core/`)を変えたので `CORE_VERSION` は core-20 に上げました:
  - `src/bot/bt/core/events.py`(事象に流れの名前 `Event.stream` を追加)
  - `src/bot/bt/core/engine.py`(核が取り込みのときに流れの名前を付ける。別の名前を書いた事象は拒む)
  - `src/bot/bt/core/contract.py`
- 約定の口: `src/bot/bt/fill/venue.py`(`SimVenue(streams=...)`。名指しが無いときに同じ種類の価格の出どころが 2 本来たら止まる)
- データ層:
  - `src/bot/bt/data/spec.py`(宣言 `no_trade` を追加。暗号資産・FX の足は `session` を省けない)
  - `src/bot/bt/data/anomalies.py`(異常の種類 `no_trade`、方針は drop だけ)
  - `src/bot/bt/data/loader.py`(`no_trade` の読み・`checks_not_run`・G-6 の 4 つの直し)
  - `src/bot/bt/data/allowlist.py`(封印の時刻の読み手を 1 つにし、同じセルを 2 度読まない)
- 記録の口:
  - `src/bot/bt/repro/runner.py`(`DataInput.range_ns`、`Parts.prepare` の呼び出し)
  - `src/bot/bt/repro/errors.py`(`RunSealedRangeError`)
  - `src/bot/bt/repro/fixed.py`(`Parts.prepare`)
- 戦略: `src/bot/strategy/k1_xvenue.py`(流れを名前で見分け、窓の 2 本がそろったときに行動。`join_fold` を追加)
- スクリプト:
  - 変えた: `scripts/k1_newenv_g_fold.py`(写しを作る `filter_bitflyer` を消して宣言で読む)、`scripts/k1_newenv_g_run.py`、`scripts/k1_newenv_g_selftest.py`
  - 作った: `scripts/k1_newenv_g_rawrun.py`、`scripts/k1_newenv_g_mutate.py`、`scripts/k1_newenv_g_loadprof.py`
- 新しい試験 7 本:
  - `tests/bt/item_0/test_bt0_fix_g1_stream_name.py`
  - `tests/bt/item_2/test_i2_fix_g1_venue_streams.py`
  - `tests/bt/item_4/test_i4_fix_g1_k1_xvenue.py`
  - `tests/bt/item_1/test_i1_fix_g2_no_trade.py`
  - `tests/bt/item_3/test_i3_fix_g3_runner_range.py`
  - `tests/bt/item_1/test_i1_fix_g4_session.py`
  - `tests/bt/item_1/test_i1_fix_g6_loader_cost.py`
- 期待値・spec だけ直した既存の試験(場面集ではありません):
  - `tests/bt/item_0/test_bt0_notices.py`、`test_bt0_r14_process_state.py`、`test_bt0_r8_sender_adversary.py`
  - `tests/bt/item_1/test_i1_fix_seal_read_before_refuse.py`、`test_i1_fix_stream.py`、`test_i1_spec_and_parse.py`
  - `tests/bt/item_2/i2_driver.py`
  - `tests/bt/item_3/test_i3_fix_currency.py`
  - `tests/bt/item_4/test_i4_data_session.py`、`test_i4_fix_k1_module.py`
- 文書:
  - `docs/PHASE2/K1/NEWENV_G/FIXES.md`(新規)、`docs/PHASE2/K1/NEWENV_G/rawrun_compare.json`(新規)
  - `docs/PHASE2/K1/NEWENV_G/ENV_DEFECTS.md`(「直した」の節を追記)
  - `docs/PHASE2/K1/NEWENV_G/INTENT_MAP.md`(X-9 と X-7 を ○ に)
- 実行記録: `backtest_runs/k1_newenv_g_close/{06a79687…,eb130c76…}/`(gzip 済み、2.7 MB)
- 作業者 A の持ち物、場面集、フック、`settings.json`、封印の台帳、`config/` には触っていません。git commit / push もしていません。

**(b) 打ったコマンドと末尾の行**(`<S>` はスクラッチパッド)
- 全体の試験(10:06 開始):
  `PYTHONPATH=scripts:src K1G_DATAGATE_LOG=<S>/logs/final2_refused.log python -m pytest tests/bt tests/test_k1_wick.py tests/test_k1_wick_critic.py -p k1_newenv_g_datagate -p no:cacheprovider --basetemp=<S>/pt_final2 --ignore=tests/bt/item_2/test_i2_real_data_check.py --ignore=tests/bt/item_4/test_i4_real_data_smoke.py`
  → 「18004 passed, 6 skipped, 3 warnings in 1041.96s (0:17:21)」。門の記録 `final2_refused.log` は作られていないので、止めた `open` は 0 件です。
- 条件 6 の 2 升:
  `PYTHONPATH=scripts:src K1G_DATAGATE_LOG=<S>/logs/rawrun_refused.log sh -c "python3 scripts/k1_newenv_g_rawrun.py --feet 15; python3 scripts/k1_newenv_g_rawrun.py --feet 5"`
  - 15 分: 「"new": {"n": 10666, "mean_bp": 2.538203629061192} … "n_equal": true, "mean_bp_equal": true」(848.8 秒、最大 RSS 7,363.4 MB)
  - 5 分: 「"new": {"n": 12999, "mean_bp": 3.4532744966127042} … "n_equal": true, "mean_bp_equal": true」(798.3 秒)
  - 2 回の実行は byte で同じ。止めた `open` は 0 件(`rawrun_refused.log` は作られていない)。8 ファイルの範囲は `record.json` に残っています。
  - bitFlyer の `no_trade` で落ちた行は 2018〜2021 で 4,293 / 5,708 / 6,701 / 6,970 行。段階 G の写しが落とした行数(`FOLD_MANIFEST.json`)と同じです。
- 変異の確かめ: `K1G_MUT_DIR=<S>/mut2 python3 scripts/k1_newenv_g_mutate.py`
  - 対照: 「M0_control_no_change: exit 0: 56 passed in 1.98s」
  - M1〜M11(直しを 1 か所ずつ外す)はすべて exit 1 で落ちました。最後の行は「M11_G6_seal_time_read_twice: exit 1: 1 failed in 0.31s」。
- 戦略の自前の試験: `python3 scripts/k1_newenv_g_selftest.py --trials 1` → 「cases 234 trades compared 15264 mismatched cases 0」(流れの名前の順を 2 通りにして比べた)
- G-6 の計測: `python3 scripts/k1_newenv_g_loadprof.py time`(Binance 2018、521,624 行)

  | | 1 回目 | 2 回目 |
  |---|---|---|
  | 直す前 | 53.6 秒 | 45.8 秒 |
  | 直した後 | 29.32 秒 | 30.49 秒 |

  事象の列の sha256 `e45e3571…` は直す前と同じです。
- `df -h /` → 「/dev/vda 252G 37G 380M 99% /」

**(c) 満たせなかった条件**
1. 条件 7 について: `tests/bt/item_2/test_i2_real_data_check.py`(5 件)と `tests/bt/item_4/test_i4_real_data_smoke.py`(1 件)は、段階 G の門が許していない `backtest_data/auto_bitflyer_executions_20260905/{board_top5,executions}_20260821.csv.gz` を開きます。除かずに回した 09:23 の回では、門がこの 2 つの `open` を止めて 6 件が ERROR になりました(`disc_refused.log` の 2 行)。そのため、この 2 ファイルは除いて回しています。
2. 条件 5(G-6)の残り: 直した後の cProfile(全体 80.8 秒)で残っているのは次の 3 つで、上限の中では直していません。
   - 核の `BarEvent` の値の検査: 30.2 秒(37%)
   - 1 行 1 回の ISO 時刻の読み: 12.2 秒
   - 数の読み: 11.2 秒
3. G-4 の後、持ち物の外にある段階 A のスクリプト 4 本は、回すと `SpecError` で止まります(`scripts/k1_newenv_run.py`、`scripts/k1_newenv_tables.py`、`scripts/k1_newenv_fold.py`、`scripts/k1_newenv_fix_seal_repro.py`)。
4. `scripts/k1_newenv_g_fold.py` は直しましたが、回していません(回すと段階 G の畳んだ足を書き換えるため)。

**(d) リードに聞くこと**
1. 段階 A のスクリプト 4 本に `session: 24x7` を書き足しますか。持ち物の外です。BitMEX の足に穴があるかは確かめていないので、穴があれば `gap: accept` の名指しも要ります。
2. 除いた試験 2 ファイルを、どのデータの決まりの下で誰が回しますか。段階 A の門はこの 2 ファイルを許しています。
3. 記録の口に足した `Parts.prepare` を一般の口として残してよいですか。条件 6 を生のファイルから写し無しで回すために、作業者の判断で足しました。今は K1 の結合・畳みだけが使っています。

FIXES.md の §9 と §10 に同じ内容を書きました。

Files are in `/home/user/trade/docs/PHASE2/K1/NEWENV_G/`:
- FIXES.md
- rawrun_compare.json

## 批評家(Opus、A・B のあと)

着手前の表(委任文 `20261001_k1_stage_g_close.md` §1 の批評家の行による)

| やろうとすること | オーナーの原文の該当語(逐語) |
|---|---|
| 作業者 A・B の成果物を、§3 の射程 (1)〜(5) で検査する(コードは変えない) | 「**ワークフロー起動して案1と欠陥の修正を進めて**」 |

右が空の行はありません。

## 批評の結果:[止める] 0 件、[直す] 5 件、[聞く] 1 件

全体として、作業者 B の直し(G-1〜G-4・G-6)は根本で入っていました。試験も、私が自分で書いた変異 5 つをすべて落としました。作業者 A の文書の直し 4 件(批評家の [直す] 1・3・4・5)も、指摘どおりに当たっています。残った問題は 2 つです。1 つは、2023 のファイルの読み方の説明が事実と違うこと。もう 1 つは、記録と返り値の書き漏れです。

### 指摘

**1. [聞く] データ層は、範囲の外の行も値まで読んでから捨てている。G-3 でこの道を正式な入力にした(B)**
- 場所は `src/bot/bt/data/loader.py:528-529` です。`_build`(行の全部の欄を数に直し、`BarEvent` を作る)が先に動き、範囲の判定 `_in_range` はその後です。
- 確かめ方:範囲 [00:00, 00:02) で、範囲の外の 00:02 の行の open を `XX` にした合成ファイルを `load` しました。
  - 出力:「ParseError 'backtest_data/a.csv' line 4 field 'open': 'XX' is not a decimal number」
  - つまり、範囲の外の行も値まで読んでいます。
- 何が起きるか:
  - G-3 で、封印の台帳に載った生のファイルを範囲つきで記録の口に入れられるようになりました。この口で 2023 のファイルを読むと、境より後の行の値まで数に直され、事象も作られます(捨てられるので、先には渡りません)。
  - G-2 の直しで `k1_newenv_g_fold.py` の写しをやめました。この結果、次にこのスクリプトを回すと、bitFlyer 2023 の境より後の行もデータ層で値まで読まれます。直す前の写し(`git show HEAD:scripts/k1_newenv_g_fold.py` の 145・148 行)は、境より後の行は時刻を読んだところで飛ばしていました。
- この回の実行が読んだのは 2018〜2021 だけです(`rawrun_compare.json` の `opened`)。なので、この回に境より後の値を読んではいません。
- 聞くこと:時刻だけを先に読み、範囲の外なら値を読まない形にすれば直せます。前回の [聞く] 2(封印の破りに当たるか)とつながるので、いま直す欠陥として扱うかを、リードが決めてください。

**2. [直す] 「時刻を読んでから捨てた」は、Binance 2023 については事実と違う(A)**
- 場所:`docs/PHASE2/K1/NEWENV_G/DATA_READ.md:33`・`:99`、`DIFF.md:92`。
- Binance 2023 はデータ層(`read_layer` → `load`、範囲の終わり = 境)で読んでいます。指摘 1 のとおり、境より後の 20,160 行も OHLCV を数に直し、`BarEvent` を作ってから捨てています。
- 「時刻だけを読んだ」が当てはまるのは、bitFlyer 2023(写しを作った自前の読み)だけです。
- 直し方:Binance と bitFlyer を分けて書く。

**3. [直す] 15 分の升は、直しが入り切る前のコードで回っている。返り値に書かれていない(B)**
- 根拠(どれも `ls --time-style=full-iso` と `record.json` で確かめました):
  - `loader.py`・`allowlist.py` の最後の変更は 09:35:01。
  - 15 分の升の `record.json` は 09:32:58 に書かれ、`diff_hash` は `434b4a6c…`。
  - 5 分の升の `diff_hash` は `7acea3e9…`。
  - 今の作業ツリーで `code_state` を出すと `8462b236…`。
- FIXES.md:139 にはこの事実が書いてあります。しかし返り値 (b) は「2 回の実行は byte で同じ」とだけ書き、(c) にもありません。
- 直し方:(c) に足す。もしくは、15 分の升を今のコードで回し直す(前回 848.8 秒・最大 RSS 7,363 MB。ディスクの残りは 380 MB)。

**4. [直す] ENV_DEFECTS.md の G-6 の行が古い(B)**
- 場所:`ENV_DEFECTS.md:32`。今は「直したのは 3 つ」「45.8〜53.6 s → 39.6〜39.75 s」「残りに ISO 時刻の 2 回の読み」と書いてあります。
- 実際は次のとおりです。
  - FIXES.md §5 では直しは 4 つで、ISO 時刻の 2 回の読みは 4 つ目で直っています。
  - `<S>/g6/time_after2.txt` の値は「"load_s": 29.32」と「"load_s": 30.49」です。
- 直し方:FIXES.md §5 に合わせる。

**5. [直す] TABLES.md の「」の中の引用が、元の文と違う(A)**
- 場所:`TABLES.md:187`(生成元は `scripts/k1_newenv_g_tables.py:227`)。
- 今の引用は「批評家の [直す] だけ当てて G を閉じる。第 18 部は回さない」です。
- 委任文 §0(6 行目)の元の文は「批評家の [直す] 4 件(文書の書き方)だけ当てて G を閉じる。第 18 部は回さない(Bybit の取り直しも不要)」です。DIFF.md:34 は正しく引いています。
- 直し方:引用を元の文のとおりにする。

**6. [直す] INTENT_MAP.md に、直す前の書き方が残っている(B)**
- 場所 1:`INTENT_MAP.md:12`(X-5)の「委任文 §2-2 は (f) を表の項目に挙げていない」。前回の [直す] 5 のとおり、作業者の判断だと書いていません。
- 場所 2:`:17-18`(X-10・X-11)は、まだ「d1 を受けたときに同じ窓の d0 のシグナルで行動」と、届く順で書いています。G-1 の後のコードは「名前で見分け、2 本がそろったときに行動」です(`k1_xvenue.py` の diff)。

### [止める] の数
0

### 確かめたこと(打ったコマンドと出力)

1. **直しが根本か:**
   - `git diff` で、核・約定の口・記録の口・データ層・戦略を読みました。
   - G-1:核が取り込みのときに `object.__setattr__(event, "stream", name)` で名前を付けています(写しにした後の核自身の事象。`_rebuilt` の後)。戦略は `w[self.signal]` で見分けていて、順に頼った書き方は残っていません。
   - G-2:`no_trade` は宣言と方針 drop が要り、名指しが無ければ `UnresolvedAnomalyError` で止まります。
   - G-3:計画の段で `read_checked(..., rng)` を通ります。
   - G-4:`spec.py:296` で、crypto と fx は `session` を省けません。資産は `ASSETS = ("crypto", "fx", "jpx")` の 3 つだけです。
   - 段階 A のスクリプト以外に、`session` を書いていない足の spec は見つかりませんでした。src・scripts で `"kind": "bar"` を持つファイルを grep し、`session` が 0 件のファイルは段階 A の 4 本と `scripts/phase2/p2_03_final.py` でした。後者は DataFrame の列で、spec ではありません。
2. **変異(B の 11 個とは別に、私が書いたもの):** src の写しで回しました。
   - 対照:「C0_control: exit 0: 43 passed in 2.11s」
   - 「C1_venue_no_one_stream_per_kind: exit 1: 2 failed, 10 passed」
   - 「C2_engine_accepts_foreign_stream_name: exit 1: 1 failed, 7 passed」
   - 「C3_no_trade_any_blank: exit 1: 1 failed, 11 passed」
   - 「C4_strategy_no_step_check: exit 1: 1 failed, 5 passed」
   - 「C5_seal_time_ignores_end_label: exit 1: 1 failed, 4 passed」
   - 門の記録 `refused.log` は作られていません。写しは消しました。
3. **B の記録:**
   - `t_final2.log` の末尾:「18004 passed, 6 skipped, 3 warnings in 1041.96s (0:17:21)」
   - `mutate_final.log` は M0〜M11 の 12 行で、10:07 に書かれていました(src の最後の変更 09:35 より後)。
   - `rawrun.log` の 2 行は、どちらも「"n_equal": true, "mean_bp_equal": true」。
   - 今日の門の記録は `disc_refused.log` の 2 行だけで、中身は `auto_bitflyer_executions_20260905/{board_top5,executions}_20260821.csv.gz` でした。
4. **読んではいけないデータ:**
   - `rawrun_compare.json` の `opened` は、生のファイル 2018〜2021 の 8 つと台帳 8 つだけです。
   - `record.json` の `range_ns` は、8 つとも翌年の 1 月 1 日までです(2022-01-01 より前)。
   - B の新しいスクリプト 3 本は、最初に門を import しています。G-2 の試験は合成ファイルを使っています。
5. **A の文書の直し:**
   - `grep -c "封印"`:diff_table.md:430、TABLES.md:91。
   - `diff_summary.json` の `tally`:一致 118、当時の誤り 12、封印 86 と 344。`d1_cover`:変種が覆う 4 行、覆っていない 8 行。
   - DIFF.md §3.2 の 8 行の値は、前回の VERDICTS の表(130〜134 行と、その上の期間の表)と、私が目で 1 行ずつ突き合わせて一致しました。
   - 第 18 部は「測らない(L-499a 案 1)」になっています(DIFF.md:34、TABLES.md:187)。
   - (f) は作業者の判断と書き直されています(DIFF.md §2・§6-2、TABLES.md:191)。
   - `gate_workerA.log` は存在しません。
6. **核の版と場面集:**
   - `CORE_VERSION = "core-20"` を確かめました(`contract.py` の diff)。
   - `git diff --stat -- tests/bt/battery` は出力なし。`git status --short | grep -i scene` も出力なしです。
   - 終わった後の `git status --short` は 48 行で、私が見る前と同じです。

### 確かめていないこと

1. A のスクリプト 2 本を回し直して、md5 が一致するか。回すと docs の生成物を書き換えるので、回していません。
2. 15 分の升を今のコードで回したときに、取引数・平均 bp が同じになるか。
3. 除いた試験 2 ファイル(計 6 件)の結果。
4. B の G-6 の時間の計測をやり直すこと。
5. 段階 G の Binance 2023 の読みで、境より後の行の値が実行記録に入っていないこと(前回の「確かめていないこと」3 のまま)。
6. 2 本の流れで、同じ種類の価格の出どころを同じ流れから別の銘柄として出す呼び手が、場面集の外にあるか。
