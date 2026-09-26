# 項目 4 場面集の第 r2-2 回の直し — 根本原因と主張の表(直す前に書いた)

場面係(作業者でも資料係でもない)。起動文が渡した指摘(逐語):

```
[{"id":"br2-1-touch","level":"止める","repeat_of":null,"text":"場面係の差分に場面集の外のファイルがある(L-448 の機械の検査): docs/AUDITOR/TRACE/2026-09-26_220780c0.json, docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-1/after_fix_pytest_battery_and_critic.txt"}]
```

記号: `<S>` = `/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/i4_r2-2_scenekeeper`、
`<M>` = `docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-2`(記録の規則どおり、ここに写しを置く)。

## 1. 直す前の再現(コマンドと出力)

HEAD = `d70387060c01482d5d18439bc3cf22afe45c10d5`(リードのチェックポイントのコミット)。

```
$ git diff --name-only HEAD
docs/AUDITOR/TRACE/2026-09-26_220780c0.json
docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-1/after_fix_pytest_battery_and_critic.txt
tests/bt/battery/item_4/ROOTCAUSE_r2-1.md
tests/bt/battery/item_4/test_battery_item4_claims.py
```

台本の `checkBattery` を、`tests/workflows/backtest_env_logic.test.mjs` と同じやり方(台本の文から関数を切り出す)で node で走らせた
(`<M>/check_before.json`):

```
{"findings":[{"id":"br2-2-touch","level":"止める","repeat_of":"br2-1-touch","text":"場面係の差分に場面集の外のファイルがある(L-448 の機械の検査): docs/AUDITOR/TRACE/2026-09-26_220780c0.json, docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-1/after_fix_pytest_battery_and_critic.txt"}]}
```

= 直す前の状態のまま返せば、同じ族(`-touch`)の 2 回目として止まる。

2 つの外のファイルの差分(`git diff HEAD -- …`):
- `docs/AUDITOR/TRACE/2026-09-26_220780c0.json`: `"Bash": 60 → 62`・`"Read": 19 → 20`・`"n_tools": 99 → 102` ほか。数えられている道具に
  `Workflow`・`mcp__Claude_Code_Remote__send_later`・`ReadNotifications` がある(場面係はこれらの道具を持たない)。
- `…/materials/r2-1/after_fix_pytest_battery_and_critic.txt`: `200 passed in 18.88s` → `200 passed in 19.50s` の 1 行だけ。

場面集と批評家の試験を直す前に回した(`<M>/before_fix_pytest.txt`): `200 passed in 19.49s`(rc=0)。回す前と後の
`git status --porcelain --untracked-files=all` は同じ(`<M>/status_before_tests.txt`・`status_after_tests.txt`)= 試験を回すことは
場面集の外に何も書かない。

## 2. 根本原因(指摘 1 件 = br2-1-touch。外のファイル 2 つで原因が違う)

### 2.1 `docs/AUDITOR/TRACE/2026-09-26_220780c0.json` — 場面係が書いた物ではない

- 書き手: `.claude/settings.json` の `Stop` のフック `.claude/hooks/trace_snapshot.sh` が `scripts/trace_metrics.py` を走らせ、
  `TRACE_DIR = REPO / "docs" / "AUDITOR" / "TRACE"`(`scripts/trace_metrics.py:36`)に書く。中身はリードの会話の道具の数
  (`Workflow`・`send_later` を数えている)。
- なぜ場面係の差分に出るか: 台本の機械の検査は場面係の返す `git diff --name-only HEAD` を読む。これは**共有の作業木が最後のコミットから
  どう変わったか**であって、**場面係が何を書いたか**ではない。作業木はリードのフック・並行する作業者・前の回の場面係と共有で、
  コミットされていない変更には書き手の記録が無い。リードのフックが `Stop` のたびに TRACE を書き換えるので、場面係が何をしても
  (何もしなくても)この行は出る。
- 場面係の側で直せるか: 直せない。フックは変えない(CLAUDE.md §0.2 A-16・委任文 §4)。TRACE を元に戻すのはリードの記録を消すことで、
  しかも次の `Stop` でまた書かれる。**= 台本の検査の作り(差分の取り方)の付け違い。§5 に書いてリードに返す。**

### 2.2 `…/materials/r2-1/after_fix_pytest_battery_and_critic.txt` — 場面係(前の回)が、コミット済みの記録を上書きした

- 経緯(git の記録): 前の回(r2-1)の場面係が `after_fix_pytest_battery_and_critic.txt` を書き、リードがその途中でチェックポイントの
  コミット d703870 に入れた。そのあと前の回の場面係が試験を回し直し、**同じファイルに上書きした**(`18.88s → 19.50s`)。
- 根本原因(場面係の側): **記録(materials)を上書きしてよい物として扱っていた。**リードは作業の途中でもチェックポイントのコミットを
  入れる(`git log` の d703870・e96c378・b454e6a はどれも途中の回の物)ので、場面係が一度書いた記録は、いつでも「HEAD にある物」に
  なりうる。上書きすれば、(1) コミット済みの記録が黙って変わり(最初の走らせの出力が消える)、(2) 検査の差分に場面集の外の行が出る。
  場面係の記録の書き方に「追記だけ(同じ path を二度書かない)」の規則も、それを検める機械も無かった。
- 根本原因(台本の側、場面係では直せない): 起動文の記録の規則は「場面係は写しを `docs/DISCUSSIONS/2026-09-23_backtest_env/item_<N>/battery/materials/<回>/`
  に置く」と場面集の外を指定し、検査は場面集の外を全部止める。新しいファイルは `git diff --name-only HEAD` に出ない(未追跡の
  ファイルは出ない)ので、今は「新しく書く分には止まらず、上書きすると止まる」という形でたまたま両立している。§5 に書く。

### 2.3 同じ種類の欠陥を場面集の全体で探した(「場面係の差分の申告が、場面係の行いを表していない」族)

| 探したもの | 方法 | 結果 |
|---|---|---|
| 場面集のコードが場面集の外に書くか | `grep -n "open(.*w\|write_text\|\.write(" *.py adapters/*.py opponents/*.py` と、出た書き先の定義の行 | `gen_considered.py`・`gen_definitions.py` は `HERE` の下、`run_battery.py` は呼び手の `--out`・`tempfile`、adapter は `tempfile.mkdtemp` だけ。リポジトリの追跡されたファイルには書かない |
| 試験を回すと場面集の外に書くか | 回す前と後の `git status --porcelain --untracked-files=all` を比べた | 同じ(§1) |
| 場面集の中のファイルが検査に「外」と読まれる形 | 捨てるリポジトリ(`<S>/qp`)で `表.md` を変えて `git diff --name-only HEAD` | `"tests/bt/battery/item_4/\350\241\250.md"` と引用符つきで出る → 台本の `startsWith` は外と読む(誤って止める)。今の場面集に ASCII 以外の名のファイルは 0 件(`git ls-files -z tests/bt/battery \| tr '\0' '\n' \| LC_ALL=C grep -c '[^ -~]'` → 0)。§5 に書く |
| 検査に出ない、場面集の外への書き込み | `git diff --name-only HEAD` は未追跡のファイルを出さない | 場面集の外に新しく作ったファイルは検査に見えない(この回の `<M>` の写しも見えない)。自分で `git status` を併記して明かす(§4 の機械) |
| 前の回の ROOTCAUSE の「git diff」の節 | `ROOTCAUSE_r2-1.md` §9 | 手で貼った節で、外の 2 行の理由も手書き。前の回の記録なので書き換えない(§3 の試験の除外に名を挙げる) |

## 3. どの作りを変えるか

1. **差分の申告を機械で作る**: `tests/bt/battery/item_4/diff_scope.py` を足す。`git diff --name-only HEAD`(返り値の `changed_files` に
   そのまま入れる行)と `git status --porcelain --untracked-files=all`(検査に見えない未追跡の分も明かす)を取り、**台本の
   `checkBattery` そのものを node で走らせて**(台本の文から切り出す。場面係が検査を書き写さない)止まるかを出し、記録の上書き
   (追記だけの規則の破れ)を列べ、ROOTCAUSE の末尾に貼る節を、自分の中身の sha256 つきで吐く。手で貼らない。
2. **記録は追記だけ**: 場面係の記録(`docs/DISCUSSIONS/2026-09-23_backtest_env/item_<N>/battery/materials/<回>/`)は、一度書いた path を
   書き直さない。走らせ直しは新しい名前で書く。これを検める試験を場面集に置く(今の作業木で、追跡されている materials の
   ファイルが HEAD と違えば落ちる)。
3. **前の回の上書きを戻す**: `…/r2-1/after_fix_pytest_battery_and_critic.txt` を HEAD の中身(最初の走らせの出力、`18.88s`)に戻し、
   上書きしていた走らせ直しの出力(`19.50s`)は消さずに `<M>/r2-1_after_fix_rerun_that_overwrote.txt` に写す(両方の走らせの記録が残る)。
4. **TRACE は触らない**。§5 に付け違いとして書き、返り値の `changed_files` にはそのまま載せる(申告を削らない)。

## 4. 主張の表(この直しが触る主張の族)

| 族 | (a) 主張を導く関数 | (b) 手書きが残る部分 | (c) 手書きが残れば落ちる試験 | (d) 機械への mutant の試験 |
|---|---|---|---|---|
| F1 場面係の差分の申告(ROOTCAUSE の末尾の `git diff --name-only HEAD` の節・返り値の `changed_files`) | `diff_scope.py:scope_report`(`git_lines` で `git diff --name-only HEAD` と `git status --porcelain --untracked-files=all` を取り、節を組む)・`diff_scope.py:section_markdown`(節の本文と sha256) | 外の行ごとの「誰が書いたか」の説明(§2.1・§2.2 の文)。git はコミットされていない変更の書き手を記録しないので機械で導けない。節の中には書かず、節の外の散文に置く | `test_battery_item4_diffscope.py:test_rootcause_diff_sections_are_machine_made`(この回以後の ROOTCAUSE の節が `diff_scope` の印と本文の sha256 を持ち、本文を 1 字でも手で変えれば落ちる) | `test_battery_item4_diffscope.py:test_section_hash_catches_hand_edits`(節の本文の 1 行を変える・行を落とす・行を足すの 3 通りで、検めが落ちることを確かめる) |
| F2 機械の検査が止まるかの予測 | `diff_scope.py:run_check`(台本 `scripts/workflows/backtest_env.js` の `checkBattery` を文から切り出して node で走らせる。書き写さない) | 無し | `test_battery_item4_diffscope.py:test_check_matches_delegation_text_on_grid`(path の格子 × 項目の番号で、委任文 §0 の L-448 の行の文「その項目の場面集 `tests/bt/battery/item_<番号>/` の外のファイルがあれば止める。項目 4 の場面係だけは項目 0 の場面集にも触れてよい」から独立に出した答えと、`run_check` の答えが一致する) | `test_battery_item4_diffscope.py:test_check_grid_catches_mutants`(台本の文を 4 通りに壊して切り出し(`./` を剥がさない・区切りの `/` を落とす・項目 0 の許しを落とす・何も止めない)、格子が不一致を出すことを確かめる) |
| F3 記録は追記だけ(materials の上書きが無い) | `diff_scope.py:materials_overwrites`(`git diff --name-only HEAD` の行のうち `docs/DISCUSSIONS/…/item_<N>/battery/materials/` の下の物 = HEAD にあって中身が違う記録)・`diff_scope.py:is_materials` | 無し | `test_battery_item4_diffscope.py:test_materials_records_are_never_rewritten`(今の作業木で上書きが 1 件でもあれば落ちる)・`test_materials_classifier_grid`(path の格子で独立の答えと一致) | `test_battery_item4_diffscope.py:test_materials_classifier_catches_mutants`(接頭辞を項目 4 だけにする・`battery/` を落とす・`materials/` の区切りを落とす・何も拾わない、の 4 通りで格子が不一致を出す) |

## 5. リードの台本への付け違い(場面集の側で直せないもの。止めて返す)

1. **検査の差分の取り方**: `checkBattery` は場面係の返す `git diff --name-only HEAD` を「場面係の差分」として読むが、これは共有の作業木の
   最後のコミットからの差分で、リードの `Stop` のフックが書く `docs/AUDITOR/TRACE/<日付>_<会話>.json` が毎回入る(§2.1)。場面係が
   何をしてもこの行は消えないので、**この形のままでは `-touch` の族は場面係の直しで閉じない**(3 回続けばリードに戻る)。
   直すのは台本の側(例: 場面係を起こす直前の `git status` を台本が取り、返りの差分から引く / TRACE を検査の外に置く)。どちらを採るかは
   リードの決めること。
2. **記録の規則と検査の食い違い**: 起動文の記録の規則は場面係の写しを `docs/DISCUSSIONS/…/item_<N>/battery/materials/<回>/`(場面集の外)に
   置かせ、検査は場面集の外を全部止める。今は未追跡の新しいファイルが `git diff` に出ないので両立して見えるだけ(§2.2)。
3. **検査に見えない書き込み**: `git diff --name-only HEAD` は未追跡のファイルを出さないので、場面係が場面集の外(`src/bot/bt/` を含む)に
   **新しいファイル**を作っても検査は止まらない。`diff_scope.py` は `git status --porcelain --untracked-files=all` も並べて明かすが、
   検査そのものは台本の側。
4. **引用符つきの path**: ASCII 以外の名のファイルは `git diff --name-only` が `"…\350\241\250.md"` の形で出すので、場面集の中の
   ファイルでも検査は外と読む(§2.3。今の場面集には該当 0 件)。`git diff --name-only -z` か `core.quotepath=false` で取るのは台本の側。

## リードに聞くこと

無し(リードの答え・注記の内容は変えない。記録の規則の置き場所も変えない。§5 は付け違いの報告で、答えの変更ではない)。

## 6. 直した記録(直した根拠。ファイル:行・コマンドと出力)

1. 試験を先に書いた: `tests/bt/battery/item_4/test_battery_item4_diffscope.py` を `diff_scope.py` より先に書き、道具を書いたあと直す前に回した
   (`<M>/before_fix_pytest_diffscope.txt`): `2 failed, 13 passed` — 落ちたのは `test_materials_records_are_never_rewritten`
   (`records rewritten (write a new file instead): ['docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-1/after_fix_pytest_battery_and_critic.txt']`)
   と `test_rootcause_diff_sections_are_machine_made`(機械の節がまだ無い)。最初の版では mutant の試験 2 件も落ちた: 台本の文の
   置き換えが `checkBattery` の外(同じ文を持つ場面係への起動文)に当たっていた → 置き換えを `checkBattery` の中に限った
   (`_mutate`)。4 つの mutant は全部、格子が不一致を出す。
2. 前の回の上書きを戻した: `git diff HEAD -- …/r2-1/after_fix_pytest_battery_and_critic.txt` を `<M>/r2-1_overwrite.diff` に、上書きしていた
   中身(`200 passed in 19.50s`)を `<M>/r2-1_after_fix_rerun_that_overwrote.txt` に写してから `git checkout HEAD -- <その path>`。
   戻したあとの `tail -1` = `200 passed in 18.88s`、`git diff --name-only HEAD` から消えた。
3. 検討表: `python3 scripts/check_bt_considered.py /home/user/trade/tests/bt/battery/item_4/opponents/CONSIDERED.md --write` → `OK 誤り 0 件`
   (`<M>/check_bt_considered.out`。検討表の中身は変わっていない = `git status` に出ない)。
4. 場面・runner・adapter・mutant・DEFINITIONS は変えていない: この指摘は場面集の中身ではなく場面係の差分の記録の族で、§2.3 の探索で
   場面集のコードが場面集の外に書く箇所は 0 件だった。

## 7. 提出前の吟味(非常に厳しい批評家なら何を [止める] にするか / どう潰したか / 残る物)

- 「r2-1 の記録を戻したのは検査を通すための書き換えだ」→ 両方の走らせの記録を残した(HEAD の最初の走らせ、`<M>` に上書きしていた走らせ直し)。
  戻したのは「コミット済みの記録を黙って変えた」ことで、追記だけの規則は試験で機械にした。検査が止まる行(TRACE)は消していない。
- 「TRACE が残るので、この回も `-touch` で止まる」→ そのとおり。場面係の側では消せない(§2.1)。返り値の `changed_files` から削らない
  (申告を削れば偽の申告)。**残る**: §5-1 はリードの台本の直しを待つ。この形のままなら、同じ族はリードに戻る。
- 「場面集の外に新しいファイル(`<M>` の写し)を書いたのに検査に出ない」→ 記録の規則の指定どおりの置き場所で、節の
  「未追跡で場面集の外」に全部を並べて明かした。**残る**: 検査が未追跡を見ないこと自体は台本の側(§5-3)。
- 「`diff_scope.py` は検査を書き写しており、台本が変われば嘘になる」→ 書き写していない。台本の文から `checkBattery` を切り出して node で
  走らせる。台本の検査が委任文の L-448 の行の文から外れれば、格子の試験が落ちる(答えは文から独立に書いた)。
- 「node・git が無ければ試験が飛ぶ」→ この環境では両方あり、`-rs` で飛んだ試験は 0 件。飛ぶのは道具が無い環境だけで、理由を skip の文に書いた。
- 「生きた作業木を読む試験は、並行する者の書き込みで揺れる」→ 読むのはこの項目の場面係の記録(item_4/battery/materials)の上書きだけで、
  落ちるのは上書きが起きたときだけ。項目 0 の記録は並行する別の場面係が書くので読まない(試験の文に名を挙げた)。
- 「格子から外した物がある」→ 引用符つきの path・`./` つき・絶対 path・項目の無い呼び出しは格子に入れず、理由を試験のファイルの先頭に書いた。
  引用符つきは `test_quoted_paths_are_reported` で道具が名指すことだけを見る。
- 「ROOTCAUSE の末尾の節を手で貼った」→ `diff_scope.py --markdown` の出力をそのまま足し、本文の sha256 を試験が検める。

## 8. 末尾の節の読み方(節の外の散文。書き手は git が記録しないので、ここは手書き)

- `docs/AUDITOR/TRACE/2026-09-26_220780c0.json`: リードの `Stop` のフックの記録(§2.1)。場面係は書いていない。検査はこの行で止まる(§5-1)。
- `docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/round_2/materials/full_suite.txt`(未追跡): この回の場面係が着手した時点の
  `git status --short` にすでにあった(この回の最初のコマンドの出力)。場面係の物ではない。
- `…/battery/materials/r2-2/` の未追跡のファイル: この回の場面係の記録(起動文の記録の規則の置き場所。全部新しい名前で書いた)。
- 場面集の中の変更: `ROOTCAUSE_r2-1.md`・`test_battery_item4_claims.py` は前の回の場面係の変更(チェックポイントのコミットの後の分)、
  `ROOTCAUSE_r2-2.md`・`diff_scope.py`・`test_battery_item4_diffscope.py` はこの回の物。実装(`src/bot/bt/`)・作業者の試験(`tests/bt/item_4/`)・
  項目 0 の場面集(`tests/bt/battery/item_0/`)には触れていない(節の差分と未追跡の一覧に 1 行も無い)。

## `git diff --name-only HEAD` の節(`diff_scope.py` が作った。手で変えない)

<!-- diff_scope:begin sha256=0fae91464cc834fdeaec0092eb4a0d7d2886e3f932b6fe53c4a50785f9818b3d -->
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
?? docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-2/before_fix_pytest.txt
?? docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-2/before_fix_pytest_diffscope.txt
?? docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-2/check_before.json
?? docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-2/check_bt_considered.out
?? docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-2/diff_before.txt
?? docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-2/r2-1_after_fix_rerun_that_overwrote.txt
?? docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-2/r2-1_overwrite.diff
?? docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-2/status_after_tests.txt
?? docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-2/status_before_tests.txt
?? docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/round_2/materials/full_suite.txt
?? tests/bt/battery/item_4/ROOTCAUSE_r2-2.md
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
docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-2/before_fix_pytest.txt
docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-2/before_fix_pytest_diffscope.txt
docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-2/check_before.json
docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-2/check_bt_considered.out
docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-2/diff_before.txt
docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-2/r2-1_after_fix_rerun_that_overwrote.txt
docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-2/r2-1_overwrite.diff
docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-2/status_after_tests.txt
docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-2/status_before_tests.txt
docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/round_2/materials/full_suite.txt

引用符つきの path(git の引用の形。場面集の中でも検査は外と読む):
(無し)
```
<!-- diff_scope:end -->

