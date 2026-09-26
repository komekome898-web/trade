# 項目 4 場面集の第 r2-3 回の直し — 根本原因と主張の表(直す前に書いた)

場面係(作業者でも資料係でもない)。起動文が渡した指摘(逐語):

```
[{"id":"br2-2-touch","level":"止める","repeat_of":"br2-1-touch","text":"場面係の差分に場面集の外のファイルがある(L-448 の機械の検査): docs/AUDITOR/TRACE/2026-09-26_220780c0.json"}]
```

記号: `<S>` = `/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/i4_r2-3_scenekeeper`、
`<M>` = `docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-3`(記録の規則の置き場所。全部新しい名前で書き、上書きしない)。

## 1. 直す前の再現(コマンドと出力)

この回の**最初の書き込み**として、作業木の状態の写し(基準)を取った: `<M>/baseline_at_start.json`(取った時刻 `2026-09-26T10:17:00Z`、
HEAD `d70387060c01482d5d18439bc3cf22afe45c10d5`、`git status --porcelain -z --untracked-files=all` の全行と各ファイルの sha256)。
その時点ですでに:

```
$ git diff --name-only HEAD          (<M>/diff_at_start.txt)
docs/AUDITOR/TRACE/2026-09-26_220780c0.json
tests/bt/battery/item_4/ROOTCAUSE_r2-1.md
tests/bt/battery/item_4/test_battery_item4_claims.py
```

`docs/AUDITOR/TRACE/2026-09-26_220780c0.json` は着手の時点で HEAD と違っていた(基準の sha256 `2da60da1…`)。差分(`<M>/trace_diff_at_start.txt`)は
`"Bash": 60 → 62`・`"Read": 19 → 20`・`"n_tools": 99 → 102`・`P5 max 99 → 102` で、数えられている道具は `Workflow`・
`mcp__Claude_Code_Remote__send_later`・`ReadNotifications`(場面係の持たない道具)= リードの会話の記録。

台本の `checkBattery` を台本の文から切り出して走らせた(`python3 tests/bt/battery/item_4/diff_scope.py --json` → `<M>/check_before.json`):
`[{'id': 'bself-touch', 'level': '止める', ..., 'text': '場面係の差分に場面集の外のファイルがある(L-448 の機械の検査): docs/AUDITOR/TRACE/2026-09-26_220780c0.json'}]`
= 何も直さずに返せば同じ族(`-touch`)の 3 回目として止まる。

場面集と批評家の試験(直す前、`<M>/before_fix_pytest.txt`): `215 passed in 20.30s`。回したあとの `git status` は基準の行 + この回の `<M>` の
4 ファイルだけ(`<M>/status_after_before_tests.txt`)= 試験を回すことは場面集の外に何も書かない。

台本の `checkBattery` は前の回(r2-2)のあと変わっていない: `git log --oneline -3 -- scripts/workflows/backtest_env.js` の最新は `381fd66`
(d703870 より前)。HEAD は前の回と同じ `d703870`。

## 2. 根本原因(指摘 1 件 = br2-2-touch)

### 2.1 外の行を書いたのは誰か

前の回の §2.1 と同じ: `.claude/settings.json` の `Stop` のフック(`trace_snapshot.sh`)が `scripts/trace_metrics.py` を走らせ、
`docs/AUDITOR/TRACE/<日付>_<会話>.json` をリードの会話の記録から作り直す。リードの返答が終わるたびに書かれるので、場面係が何をしても
(何もしなくても)この行は `git diff --name-only HEAD` に出る。この回は着手の時点ですでに出ていた(§1 の基準)。

### 2.2 なぜ同じ指摘が 2 回目も返ってきたか(前の回の場面係の側の欠陥)

前の回は原因を「台本の検査の差分の取り方の付け違い」と書き(ROOTCAUSE_r2-2.md §5-1)、返り値の `changed_files` から TRACE を削らなかった。
ここまでは正しい。欠陥は、**「場面係が書いていない」という主張が手書きの散文だけだった**こと:

- ROOTCAUSE_r2-2.md の主張の表の F1 の (b) は「外の行ごとの誰が書いたか … 機械で導けない。節の外の散文に置く」とし、§8 の散文で
  「リードの Stop のフックの記録。場面係は書いていない」と書いた。**この主張を場面係の行いの記録から導く機械が無かった**。
  台本の検査は `changed_files` しか読まず、散文は読まない。リードは同じ指摘で場面係を起こし直した(起動の注記に §5-1 への言及は無い)。
- 「誰が書いたか」は機械で導けないが、**「場面係の作業のあいだに変わったか」は機械で導ける**: 着手の最初に作業木の各ファイルの sha256 を
  写しておき、返す直前の sha256 と比べればよい。前の回はこれをせず、「導けない」の範囲を広く取りすぎた(= 手書きの残りを必要以上に残した)。

### 2.3 場面係の側では閉じない部分(付け違い。§5 に書いてリードに返す)

- 起動文は `changed_files` に「git diff --name-only HEAD の出力の全行」を入れよと言い、検査はその中に場面集の外の行があれば止める。
  TRACE はリードのフックが書くので、**正直に申告する限り、この検査は場面係の直しで通らない**。TRACE を HEAD に戻す(`git checkout`)・
  `assume-unchanged` で隠す・申告から削る、はどれも検査を通すための書き換え(リードの監査の入力を場面係が書き換える / 偽の申告)なので、しない。
- よってこの回の返り値の `changed_files` にも TRACE は載り、台本の検査は `-touch` の 3 回目として止まり、§3「周回の数え方と止める条件」4 の
  とおりリードに戻る。これが、リードの台本の付け違いを直すための決められた経路である。

### 2.4 同じ種類の欠陥を場面集の全体で探した(「場面係の差分の主張が、場面係の行いの記録から導かれていない」族)

| 探したもの | 方法 | 結果 |
|---|---|---|
| 場面集の ROOTCAUSE の中の、差分の書き手についての手書きの主張 | `grep -n "書いていない\|書いた物ではない\|場面係の物ではない\|前の回の場面係" tests/bt/battery/item_4/ROOTCAUSE_r2-*.md` | r2-1 §9・r2-2 §2.1/§8 に散文。どちらも前の回の記録なので書き換えない。この回以後は機械の帰属(§3-1)を節の中に置き、散文は「誰が」だけに縮める |
| 場面集のコードが場面集の外に書くか | 前の回 §2.3 と同じ `grep` と、この回の試験の前後の `git status`(§1) | 前の回から場面集のコードの書き先は変わっていない(`git diff HEAD -- tests/bt/battery/item_4/*.py` の差分は `test_battery_item4_claims.py` の前の回の分だけ)。試験の前後で外に増えた行は `<M>` のこの回の記録だけ |
| 場面・runner・adapter・検討表・再現・mutant の中の同じ族 | この族は「場面係の差分の申告」で、場面の正解・対象の結果には関わらない | 該当なし(場面集の中身は変えない。検討表は §6 で検査器だけ回す) |

## 3. どの作りを変えるか

1. **差分の行ごとの帰属を機械で作る**(`tests/bt/battery/item_4/diff_scope.py`):
   - `snapshot()`: 作業木の状態の写し(HEAD と、`git status --porcelain -z --untracked-files=all` の各行の path・状態・中身の sha256)。
     `--baseline-out <path>` で着手の最初に書く(この回の `<M>/baseline_at_start.json` は、この関数を書く前に同じ本体のコードで取った。
     形が `snapshot()` と同じことを試験が見る)。
   - `attribute(baseline, diff_lines, now)`: `git diff --name-only HEAD` の各行を、基準と今の写しから 4 つに分ける:
     「着手時にすでに HEAD と違い、作業中に中身は変わっていない」/「着手時にすでに HEAD と違い、作業中に中身が変わった」/
     「着手時は HEAD と同じで、作業中に変わった」/「判定できない(HEAD が作業中に変わった)」。
   - 節(`--markdown --baseline <path>`)に、基準の path と sha256・行ごとの帰属・検査が止める行の帰属を入れる(本文の sha256 で手の変更を検める)。
2. **この回以後の ROOTCAUSE の節は基準つき**: 試験が、ROOTCAUSE_r2-3 以後の節に基準の参照と帰属の段があること、基準がその回の書き込みより
   前に取られたこと(基準の中にその回の ROOTCAUSE と `<M>` の他のファイルが 1 つも無いこと)を検める。
3. **TRACE には触らない**。返り値の `changed_files` は `git diff --name-only HEAD` の全行のまま(削らない)。

## 4. 主張の表(この直しが触る主張の族)

| 族 | (a) 主張を導く関数 | (b) 手書きが残る部分 | (c) 手書きが残れば落ちる試験 | (d) 機械への mutant の試験 |
|---|---|---|---|---|
| F1 場面係の差分の申告(末尾の節・返り値の `changed_files`) | `diff_scope.py:scope_report`・`diff_scope.py:section_markdown`(前の回のまま。この回は帰属の段と基準の参照を足す) | 無し(節の中は全部機械。節の外の散文は F4 (b) の「誰が」だけ) | `test_battery_item4_diffscope.py:test_rootcause_diff_sections_are_machine_made`(本文の sha256。この回から、r2-3 以後の節に基準と帰属の段が無ければ落ちる) | `test_battery_item4_diffscope.py:test_section_hash_catches_hand_edits`(前の回の 3 通り + 帰属の行を書き換える 1 通り) |
| F4 外の行の帰属(着手時にすでにあったか・作業中に変わったか) | `diff_scope.py:snapshot`・`diff_scope.py:attribute`(基準と今の写しの sha256 と HEAD を比べる) | **誰が**書いたか(リードのフック・並行する作業者など)。git はコミットされていない変更の書き手を記録せず、作業木は共有なので導けない。**作業中に変わったか**は機械で導く(前の回は両方を手書きにしていた = §2.2)。もう 1 つ: 基準を「最初に」取ったことは場面係の手順で、機械はその回の書き込みが基準に無いことだけを見る | `test_battery_item4_diffscope.py:test_rootcause_baseline_predates_the_round`(r2-3 以後の ROOTCAUSE が参照する基準に、その回の ROOTCAUSE・`<M>` の他のファイルが載っていれば落ちる)・`test_attribution_matches_rule_on_grid`(基準の有無 × 中身の同じ/違う/消えた × HEAD の同じ/違う の全格子で、規則の文から独立に書いた答えと一致)・`test_baseline_file_has_snapshot_shape` | `test_battery_item4_diffscope.py:test_attribution_grid_catches_mutants`(sha256 を見ない・HEAD の変化を見ない・基準に無い行を「すでにあった」にする・全部「変わっていない」にする、の 4 通りで格子が不一致を出す) |

F2(検査が止まるかの予測)・F3(記録は追記だけ)はこの直しで触らない(前の回の表のまま。試験は回す)。

## 5. リードの台本への付け違い(場面集の側で直せないもの。止めて返す)

前の回の §5-1〜§5-4 はそのまま残っている(台本 `checkBattery` は変わっていない)。この回で足す根拠と、決めてほしいこと:

1. **この回の返り値でも `-touch` は止まる(3 回目)**: §2.3。TRACE はこの回の着手の時点ですでに HEAD と違い(基準 `<M>/baseline_at_start.json`)、
   末尾の節の帰属の段がその行を機械で分類する。場面係の直しでは閉じない族なので、3 回で止めてリードに戻るのが決められた経路。
2. **決めてほしいこと(どれを採るかはリードの判断。場面係は台本を変えない)**:
   (a) 検査が `docs/AUDITOR/TRACE/` を外に数えない(書き手がリードのフックと決まっている path を名指しで除く)/
   (b) 場面係に基準(`diff_scope.py --baseline-out`)を最初に取らせ、返り値に「着手時にすでに HEAD と違い、作業中に変わっていない」行を別の欄で返させ、
   検査はそれを外に数えない(申告なので、次の周の批評家が基準の写しと `git diff` で裏を取る)/
   (c) 場面係を起こす直前にリードが TRACE を含めてチェックポイントのコミットを入れる(ただし、リードの返答が終わるたびに `Stop` のフックが
   TRACE を書き直すので、Workflow の実行中にリードの返答が 1 回でも終われば同じことが起きる = (c) だけでは閉じない)。

## リードに聞くこと

リードの答え・注記の内容は変えない(lead_answer_changes は空)。§5-2 の (a)〜(c) のどれを採るかは台本の設計の判断なので、リードに返す。

## 6. 直した記録(直した根拠。ファイル:行・コマンドと出力)

1. 試験を先に書いた: `test_battery_item4_diffscope.py` に F4 の試験(`test_attribution_matches_rule_on_grid`・`test_attribution_grid_catches_mutants` 4 通り・
   `test_snapshot_parses_renames`・`test_baseline_file_has_snapshot_shape`・`test_live_snapshot_has_the_same_shape`・`test_rootcause_baseline_predates_the_round`)と、
   F1 の 2 つの試験への追加(r2-3 以後の節に基準と帰属が無ければ落ちる / 帰属の 1 行の手の書き換えを捕まえる)を、`diff_scope.py` を直す前に書いて回した
   (`<M>/before_fix_pytest_diffscope.txt`): `11 failed, 13 passed`(足した関数が無い = `AttributeError`、この ROOTCAUSE の節がまだ無い)。
2. `diff_scope.py` を直した(`parse_status_z`・`snapshot`・`attribute`・`load_baseline`・`baseline_refs`、`scope_report(baseline_path=)`、`_body` の基準と帰属の段、
   `--baseline`・`--baseline-out`。`--baseline-out` は既にある path には書かない = 記録は追記だけ)。直した直後の mutant の試験は、切り出した
   関数を `exec` する名前空間に `__file__` が無く 4 件とも `NameError` で落ちた → 試験の名前空間に `__file__` を渡した(試験の側の誤り)。
   そのあと mutant 4 通りは全部、格子が不一致を出す。
3. 検討表: `python3 scripts/check_bt_considered.py /home/user/trade/tests/bt/battery/item_4/opponents/CONSIDERED.md --write` → `OK 誤り 0 件`
   (`<M>/check_bt_considered.out`。検討表の中身は変わっていない = `git status` に出ない)。
4. 場面・runner・adapter・検討表・再現・mutant(`mutant.py`)・DEFINITIONS は変えていない(§2.4: この族は場面係の差分の申告で、場面の中身に無い)。
5. 末尾の節は `python3 tests/bt/battery/item_4/diff_scope.py --markdown --baseline <M>/baseline_at_start.json` の出力をそのまま足した。節のあとに、
   場面集と批評家の試験を回した出力を `<M>/after_section_pytest.txt` に書く(節より後に作るので節の未追跡の一覧には載らない。この 1 件だけ)。

## 7. 提出前の吟味(非常に厳しい批評家なら何を [止める] にするか / どう潰したか / 残る物)

- 「3 回目の `-touch` を出す直しは、直していない」→ 場面係の側で閉じる部分(「書いていない」の主張を機械の帰属にする)は閉じた。閉じない部分は
  リードの台本の検査(§5)で、正直な申告では通らない。検査を通すための書き換え(TRACE を戻す・隠す・申告から削る)はしない(§2.3)。**残る**: 台本の検査は止まる。
- 「基準を最初に取ったというのは自己申告だ」→ 取った時刻と、基準にこの回のファイル(この ROOTCAUSE・`<M>` の他の記録)が 1 つも無いことを
  試験が見る(`test_rootcause_baseline_predates_the_round`)。**残る**: 基準より前に書いて消した物は見えない(git に記録が無い)。
- 「基準の JSON は `snapshot()` を書く前の手打ちのコードで作った」→ 形(鍵の集合)が `snapshot()` と同じことを試験が見る。中身の sha256 は節が名指し、
  基準のファイルを後から変えれば `load_baseline` が落とす。本体のコードは `snapshot()` と同じ(rename の扱いだけは `snapshot()` で足した。この回の着手時の
  `git status` に rename は 0 件 = 基準の `status` の値に `R`・`C` が無い)。
- 「作業中に TRACE が書き換わったら、場面係が書いたように読める」→ 帰属は「作業中に中身が変わった」と書くだけで、書き手を言わない(F4 (b))。
- 「生きた作業木を読む試験(`test_live_snapshot_has_the_same_shape`)は揺れる」→ 形だけを見る。中身は見ない。
- 「格子から外した物がある」→ rename・copy(`test_snapshot_parses_renames` で別に見る)、引用符つきの path(格子の「今の git status に無い」の値で入る)。
  試験のファイルの先頭に書いた。
- 「全試験を回していない」→ 変えたのは場面集の試験のファイルと場面集の道具だけで、実装・作業者の試験・核には触れていない。場面集と批評家の試験を回した(`<M>/after_section_pytest.txt`)。
  全試験(10 分超)は回していない。

## 8. 末尾の節の読み方(節の外の散文)

- 節の「差分の行ごとの帰属」は機械が分けた物。**誰が**書いたかは git に記録が無いので、ここだけ手書き: `docs/AUDITOR/TRACE/2026-09-26_220780c0.json` は
  リードの `Stop` のフックの記録(§2.1)。
- `ROOTCAUSE_r2-1.md`・`test_battery_item4_claims.py` は前の回(r2-1)の場面係の変更(チェックポイントのコミットの後の分)。この回は触っていない
  (帰属が「作業中に中身は変わっていない」なら機械で裏付く)。

## `git diff --name-only HEAD` の節(`diff_scope.py` が作った。手で変えない)

<!-- diff_scope:begin sha256=193957ec1522ffa9071b9dfa2f900c4893f74241f028b2b747a6c5b6220262fe -->
```text
HEAD: d70387060c01482d5d18439bc3cf22afe45c10d5

$ git diff --name-only HEAD
docs/AUDITOR/TRACE/2026-09-26_220780c0.json
tests/bt/battery/item_4/ROOTCAUSE_r2-1.md
tests/bt/battery/item_4/test_battery_item4_claims.py

$ git status --porcelain --untracked-files=all
 M docs/AUDITOR/TRACE/2026-09-26_220780c0.json
 M tests/bt/battery/item_4/ROOTCAUSE_r2-1.md
 M tests/bt/battery/item_4/test_battery_item4_claims.py
?? docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-2/after_fix_pytest_battery_and_critic_before_section.txt
?? docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-2/after_fix_pytest_battery_and_critic_final.txt
?? docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-2/before_fix_pytest.txt
?? docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-2/before_fix_pytest_diffscope.txt
?? docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-2/check_before.json
?? docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-2/check_bt_considered.out
?? docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-2/diff_before.txt
?? docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-2/r2-1_after_fix_rerun_that_overwrote.txt
?? docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-2/r2-1_overwrite.diff
?? docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-2/status_after_tests.txt
?? docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-2/status_before_tests.txt
?? docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-3/baseline_at_start.json
?? docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-3/before_fix_pytest.txt
?? docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-3/before_fix_pytest_diffscope.txt
?? docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-3/check_before.json
?? docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-3/check_bt_considered.out
?? docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-3/diff_at_start.txt
?? docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-3/status_after_before_tests.txt
?? docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-3/trace_diff_at_start.txt
?? docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/round_2/materials/full_suite.txt
?? tests/bt/battery/item_4/ROOTCAUSE_r2-2.md
?? tests/bt/battery/item_4/ROOTCAUSE_r2-3.md
?? tests/bt/battery/item_4/diff_scope.py
?? tests/bt/battery/item_4/test_battery_item4_diffscope.py

台本の checkBattery(項目 4、node で台本の文から切り出して走らせた。tests_passed は真として渡す)の指摘:
{"id": "bself-touch", "level": "止める", "repeat_of": null, "text": "場面係の差分に場面集の外のファイルがある(L-448 の機械の検査): docs/AUDITOR/TRACE/2026-09-26_220780c0.json"}

検査が止める行(場面集の外):
docs/AUDITOR/TRACE/2026-09-26_220780c0.json

記録の上書き(HEAD にある materials の記録が変わっている = 追記だけの規則の破れ):
(無し)

未追跡で場面集の外(git diff に出ないので検査に見えない):
docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-2/after_fix_pytest_battery_and_critic_before_section.txt
docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-2/after_fix_pytest_battery_and_critic_final.txt
docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-2/before_fix_pytest.txt
docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-2/before_fix_pytest_diffscope.txt
docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-2/check_before.json
docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-2/check_bt_considered.out
docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-2/diff_before.txt
docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-2/r2-1_after_fix_rerun_that_overwrote.txt
docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-2/r2-1_overwrite.diff
docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-2/status_after_tests.txt
docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-2/status_before_tests.txt
docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-3/baseline_at_start.json
docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-3/before_fix_pytest.txt
docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-3/before_fix_pytest_diffscope.txt
docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-3/check_before.json
docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-3/check_bt_considered.out
docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-3/diff_at_start.txt
docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-3/status_after_before_tests.txt
docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-3/trace_diff_at_start.txt
docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/round_2/materials/full_suite.txt

引用符つきの path(git の引用の形。場面集の中でも検査は外と読む):
(無し)

基準: docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-3/baseline_at_start.json sha256=112b7043750f4f284121943d5e1d79c9595cb592a2f097d18e58d54f22d9ad3d
(取った時刻 2026-09-26T10:17:00Z、そのときの HEAD d70387060c01482d5d18439bc3cf22afe45c10d5。場面係の最初の書き込みとして取った写し)

差分の行ごとの帰属(基準と今の写しの sha256・HEAD から機械で分けた。書き手は git に記録が無いので出さない):
着手時にすでに HEAD と違い、作業中に中身は変わっていない	docs/AUDITOR/TRACE/2026-09-26_220780c0.json
着手時にすでに HEAD と違い、作業中に中身は変わっていない	tests/bt/battery/item_4/ROOTCAUSE_r2-1.md
着手時にすでに HEAD と違い、作業中に中身は変わっていない	tests/bt/battery/item_4/test_battery_item4_claims.py

検査が止める行の帰属:
着手時にすでに HEAD と違い、作業中に中身は変わっていない	docs/AUDITOR/TRACE/2026-09-26_220780c0.json
```
<!-- diff_scope:end -->

