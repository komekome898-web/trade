<!-- 作業者が tmp の置き場に書いた report_final.md をリードがそのまま写した(作業者の道具ではファイルを書けなかったため。Q1)。作業者の返事の文とは、数か所の言い回しだけが違う。 -->
# 報告: 委任文の検めと報告の受け取りの検めの道具(DELEGATION_checker.md 3.2 版目)

委任文の終わる条件(逐語): 「`tests/delegation/test_spec.py` が飛ばし 0 で全部通り、U16 と H1〜H3 が通り、変異の表の全部の行で壊した変更が試験を落とした。」
作り直しの周: 1 周目で全部通った(作り直し 0 周)。上限(2 周または 3 時間)の中。

## 着手前の表

| やろうとすること | オーナーの原文の該当語(逐語)/根になる委任文の節 |
|---|---|
| `scripts/delegation/check_delegation.py` を作る | L-795「**yes**」/ 節「作るもの」 |
| `scripts/delegation/check_report.py` を作る | L-795「**yes**」/ 節「作るもの」 |
| `tests/delegation/test_spec.py` を変えずに、飛ばし 0 で全部通す | L-795「**yes**」/ 節「受け入れ」・「決めてよいこと」の 確かめ方 |
| `tests/delegation/test_extra.py` に U16 の試験を足す | L-795「**yes**」/ 節「決めてよいこと」の 出力の置き場(「作業者が足したい試験は `tests/delegation/test_extra.py` に置いてよい」) |
| U16 を tmp の写しで確かめる | L-795「**yes**」/ 節「受け入れ」U16 |
| H1〜H3 を確かめる | L-795「**yes**」/ 節「変えないもの」 |
| 変異の表を tmp の写し(`DELEGATION_TOOLS_DIR`)で作る | L-795「**yes**」/ 節「変異の表」 |
| 試験で決まらない拾い方を決め、報告に書く | L-795「**yes**」/ 節「決めてよいこと」の 分母・数え方・絞り方・選び方・失敗の文の言い回し |
| 報告を `REPORT_checker.md` に書く | 中身: L-795「**yes**」/ 節「報告」。置き場は委任文に無い(リードの依頼文「…REPORT_checker.md に書き」による) |

右の列が空の行は無い。ただし最後の行は書けなかった(Q1)。

## 作ったファイルの一覧

```
$ git status --short
 M docs/AUDITOR/TRACE/2026-10-07_220780c0.json
?? scripts/delegation/
?? tests/delegation/test_extra.py
$ ls docs/DISCUSSIONS/2026-10-07_delegation_redesign/ | grep -c stamp
0
```

- `scripts/delegation/check_delegation.py`(委任文の検め。合格のとき委任文の横に `<名前>.stamp.json`)
- `scripts/delegation/check_report.py`(報告の受け取りの検め。委任文の検めをやり直す。印は読まず書かない)
- `tests/delegation/test_extra.py`(作業者が足した試験 2 つ: `test_u16_real_delegation_passes` = U16 を写しで当てる/`test_shared_part_is_identical` = 2 本の道具の「共通の部品」が一字違わず同じ)

2 本は 1 ファイルずつで完結している(互いに import しない)。check_report.py の委任文の検めの部品は、check_delegation.py の `# ==== 共通の部品(ここから…` から `…(ここまで) ====` までの写し(作業者の置き場の組み立ての台本で写した)。片方だけ直すと `test_shared_part_is_identical` が落ちる。
`docs/DISCUSSIONS/2026-10-07_delegation_redesign/REPORT_checker.md` は書けていない(Q1)。この報告は最後の返事にだけある。
コミット・プッシュ・git add・git worktree add はしていない。フック・設定・`.claude/agents/` は変えていない。封印の置き場は読んでいない。

## 試験のコマンドと出力

```
$ PYTHONPATH=src python -m pytest tests/delegation
.............                                                            [100%]
13 passed in 9.55s
```

(13 = `test_spec.py` の 11 + `test_extra.py` の 2。飛ばし 0。)

## U16・H1〜H3 の確かめのコマンドと出力

U16(委任文と記録 1〜4 を名前を変えずに tmp の 1 つの置き場に写して当てた):

```
$ SP=<作業者の tmp の置き場>; mkdir $SP/u16 && cp docs/DISCUSSIONS/2026-10-07_delegation_redesign/DELEGATION_checker.md docs/DISCUSSIONS/2026-10-07_delegation_redesign/DELEGATION_checker_premortem{1,2,3,4}.md $SP/u16/
$ python3 scripts/delegation/check_delegation.py $SP/u16/DELEGATION_checker.md --root /home/user/trade; echo "終了コード $?"
合格: $SP/u16/DELEGATION_checker.md(種類: 作る、承認: あり)
印: $SP/u16/DELEGATION_checker.stamp.json
終了コード 0
$ cat $SP/u16/DELEGATION_checker.stamp.json
{
  "delegation_sha256": "f4a31608910d86d53d1cdeb9648e2d8801f3b0ff0e452cee037ca3ff2a346153",
  "body_sha256": "47f4caff274e562f17caacb9762e59fd741e4b5f333bc1138f4b0f3b922c7fd8",
  "kind": "作る",
  "premortem": "$SP/u16/DELEGATION_checker_premortem4.md",
  "approved": true
}
```

(`$SP` は `/tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad`。出力のパスを `$SP` に縮めて書いたのはこの塊だけ。)
事実: 今の本文の事前の批評の sha256 は 47f4caff…で、記録 4 の 1 行目(49018bcc…)とは違う。合格は `## 事前の批評の後の変更` の「見た版の sha256: 49018bcc…」と記録 4 の 1 行目が一致することによる(試験の注の決まりどおり)。印は tmp に書かれ、`docs/` には書いていない。同じ確かめを `tests/delegation/test_extra.py::test_u16_real_delegation_passes` が毎回行う(既定のパスに頼らず `--owner-log`・`--fixed`・`--scenes` を渡す)。
事実(作業者の台本で道具の部品を当てて数えた): 記録 1〜4 の指摘 40・33・43・19 件、応答の行 40・33・43・19 行、形の合う応答 40・33・43・19(委任文の手の検めの記録の件数と同じ)。委任文の引用 6 か所(9・13・14・15・16・162 行目)。読んだ事実の確かめの欄の `パス:行` 8 か所(7 行。手の検めの記録の「8 か所」と同じ)。

H1:

```
$ git diff --stat -- scripts/jev_delegate.py scripts/jev_report_intake.py scripts/check_bt_delegation.py tests/delegation/test_spec.py
(何も出ない)
$ git diff --stat
 docs/AUDITOR/TRACE/2026-10-07_220780c0.json | 33 ++++++++++++++++++++++++++---
 1 file changed, 30 insertions(+), 3 deletions(-)
$ git status --short
 M docs/AUDITOR/TRACE/2026-10-07_220780c0.json
?? scripts/delegation/
?? tests/delegation/test_extra.py
```

(`docs/AUDITOR/TRACE/2026-10-07_220780c0.json` は作業者が書いたものではない。H3 の前の出力のとおり、試験の前からもう `M` だった。)

H2:

```
$ PYTHONPATH=src python -m pytest tests/test_jev_delegate.py tests/test_jev_report_intake.py tests/test_check_bt_delegation.py
........................................................................ [ 72%]
............................                                             [100%]
100 passed in 4.23s
```

H3:

```
$ git status --short docs .claude > before.txt; PYTHONPATH=src python -m pytest tests/delegation; git status --short docs .claude > after.txt; diff before.txt after.txt && echo H3同じ; cat before.txt
.............                                                            [100%]
13 passed in 9.55s
H3同じ
 M docs/AUDITOR/TRACE/2026-10-07_220780c0.json
```

## 変異の表

壊した変更は、2 本の道具を作業者の tmp の置き場に写し、写しだけを書き換え、`DELEGATION_TOOLS_DIR=<写しの置き場> PYTHONPATH=src python -m pytest tests/delegation/test_spec.py tests/delegation/test_extra.py` で当てた(台本は作業者の置き場の `mutate.py`。本物の道具は壊していない)。共通の部品を壊すときは 2 本の写しの両方を同じに壊した。2 列目の「場面」は、試験が落ちたときに出した場面の名前(表の試験は表の行の名前、表の外の試験は落ちた assert の行)。

| 番号 | 壊した変更 | 落ちた試験 |
|---|---|---|
| U1 | check_delegation の入力の誤りの終了コードを 2 から 1 に(場面: `test_spec.py:262` の「無い委任文 → 2」の assert `1 == 2`) | tests/delegation/test_spec.py::test_input_errors_exit_2_and_all_failures_listed |
| U1 | check_delegation で失敗のときに古い印を消さない(場面: `test_spec.py:258` の「失敗で印が消える」の assert) | tests/delegation/test_spec.py::test_valid_passes_writes_stamp_and_failure_removes_it |
| U2 | 種類の行を 6 行目まで見る(場面: 種類 6 行目) | tests/delegation/test_spec.py::test_form_checks |
| U3 | 見出しの一覧から「報告」を消す(場面: 見出し ## 報告、ほかに 2 つの試験の「## 報告X」の assert) | tests/delegation/test_spec.py::test_form_checks、tests/delegation/test_spec.py::test_input_errors_exit_2_and_all_failures_listed、tests/delegation/test_spec.py::test_valid_passes_writes_stamp_and_failure_removes_it |
| U4 | 引用を OWNER_LOG の 4 列目より後ろ(読みの列)とも比べる(場面: 引用 読みの列にだけある文) | tests/delegation/test_spec.py::test_form_checks |
| U5 | 行の番号の比べを 1 ゆるめる(場面: 事実 行の数 +1・事実 範囲の後ろで比べる) | tests/delegation/test_spec.py::test_form_checks |
| U6 | 封印の比べで小文字にしない(場面: 封印 そのまま・封印 大文字小文字・封印 根の中の絶対パス・封印 根の外を通って根の中へ、ほかに報告の 封印の下の試験のファイル) | tests/delegation/test_spec.py::test_form_checks、tests/delegation/test_spec.py::test_report_checks |
| U7 | 決めてよいことの一覧から「依存」を消す(場面: 決め 依存 無し・決め 依存 空、ほかに全部の失敗を出す試験の「依存」) | tests/delegation/test_spec.py::test_form_checks、tests/delegation/test_spec.py::test_input_errors_exit_2_and_all_failures_listed |
| U8 | 壊す場面の並びを見ない(場面: 場面 並び) | tests/delegation/test_spec.py::test_form_checks |
| U9 | 受け入れの U の重なりを見ない(場面: U 重なり) | tests/delegation/test_spec.py::test_form_checks |
| U10 | 決まった制約の比べで行末の空白を除かない(場面: 制約 行末の空白・空行は可) | tests/delegation/test_spec.py::test_form_checks |
| U11 | 終わる条件と上限の語から「上限」を外す(場面: 上限の語が無い) | tests/delegation/test_spec.py::test_form_checks |
| U12 | 「事前の批評の後の変更」の見た版を使わず、いつも今の本文の sha256 と比べる(場面: 事前の批評の後の変更 見た版が合う、ほかに U16) | tests/delegation/test_spec.py::test_premortem_checks、tests/delegation/test_extra.py::test_u16_real_delegation_passes |
| U12 | 番号が 2 以上の最後の回の「直した」を通す(場面: 2 回目に直した・3 回目に直した) | tests/delegation/test_spec.py::test_premortem_checks |
| U13 | 承認の節の引用を承認として数えない(場面: `test_spec.py:497` の「承認の節を足すと --require-approval で 0」の assert `1 == 0`) | tests/delegation/test_spec.py::test_require_approval_and_stamp_flag |
| U14 | 委任文を検めの前にもう 1 回 `Path.read_bytes()` で読む(場面: `test_spec.py:529` の `^READS 1$` が出ない) | tests/delegation/test_spec.py::test_reads_delegation_once |
| U15 | check_report で変異の表の試験の関数があるかを見ない(場面: 関数が無い) | tests/delegation/test_spec.py::test_report_checks |
| U15 | check_report で委任文の検めをやり直さない(場面: `test_spec.py:580` の「本文を直した後の受け取りは sha256 で 1」の assert `0 == 1`) | tests/delegation/test_spec.py::test_report_stamp_and_delegation_recheck |
| U16 | 事前の批評の記録の応答の行の頭の空白を除かない(本物の記録の「応答:」は 2 字下げなので U16 が落ちる。場面: 種類 5 行目・途中の決めを足しても記録はそのまま・事前の批評の後の変更 見た版が合う・事実 コマンドと出力・`事実 バッククォートの中の | は区切りでない`・事実 無い(全角の括弧)・事実 無い(理由 1 字)・事実 行の数ちょうど・制約 行末の空白・空行は可・引用 目的の外のバッククォートの中は可・引用 逆向き・並び・枝番号・D 番号・同じ番号の 2 行・引用 逐語の一部(頭を落とす)は可・応答 全角の括弧・応答 括弧の入れ子・応答 直さない・最後の回は番号の一番大きい記録・次の版で直す 本文がそのまま・2 回目に直さない・2 回目に直した・3 回目に直した・H0 は可・U 飛びは可) | tests/delegation/test_extra.py::test_u16_real_delegation_passes、tests/delegation/test_spec.py::test_form_checks、tests/delegation/test_spec.py::test_premortem_checks、tests/delegation/test_spec.py::test_valid_passes_writes_stamp_and_failure_removes_it、tests/delegation/test_spec.py::test_input_errors_exit_2_and_all_failures_listed、tests/delegation/test_spec.py::test_require_approval_and_stamp_flag、tests/delegation/test_spec.py::test_report_checks、tests/delegation/test_spec.py::test_report_stamp_and_delegation_recheck |
| U16 | 「事前の批評の後の変更」の見た版を使わない(場面: 本物の委任文の写しが sha256 で落ちる、と 事前の批評の後の変更 見た版が合う) | tests/delegation/test_extra.py::test_u16_real_delegation_passes、tests/delegation/test_spec.py::test_premortem_checks |
| H1 | `git diff --stat -- scripts/jev_delegate.py scripts/jev_report_intake.py scripts/check_bt_delegation.py tests/delegation/test_spec.py` | 何も出ない(4 本とも変わっていない) |
| H2 | `PYTHONPATH=src python -m pytest tests/test_jev_delegate.py tests/test_jev_report_intake.py tests/test_check_bt_delegation.py` | 100 passed |
| H3 | `PYTHONPATH=src python -m pytest tests/delegation` の前後の `git status --short docs .claude` を diff | 前後で同じ(どちらも ` M docs/AUDITOR/TRACE/2026-10-07_220780c0.json` の 1 行だけ) |

全部の行で、壊した変更が試験を 1 つ以上落とした(「落ちなかった」の行は無い)。

## 試験で決まらず作業者が決めた拾い方の一覧

1. 行の数: `\n` の数。最後の行に改行が無ければ 1 足す(空のファイルは 0 行)。CR だけの改行は数えない。
2. 行の番号 0 と逆向きの範囲(`a-b` で a > b)は「読んだ事実」の失敗。範囲は後ろの b をファイルの行の数と比べる。
3. 引用の前後の両方に番号があるとき: 前の番号か後ろの番号のどちらか一方で、並びの全部の引用が含まれれば通す。通らなければ両方の番号を出す。番号と引用の間、並びの引用どうしの間は、半角の空白とタブだけを許す。行をまたぐ引用は見ない。番号の直前が英数字か `-` のときは番号と見ない。
4. OWNER_LOG の表の区切り: バッククォートの対の中と `\|` は区切りでない。対にならないバッククォートはただの字として扱う(本物の OWNER_LOG の L-125 の行に対にならないバッククォートがある)。
5. 事前の批評の記録の番号: `<名前>_premortem<数字>.md` の数字を整数で比べ、一番大きいものが最後の回(同じ数が 2 つあれば名前の並びで後ろ)。記録がディレクトリか UTF-8 でないときは「事前の批評」の失敗(終了コード 1。入力の誤りの 2 にはしない)。
6. 指摘の範囲の終わり: 次の行頭 `- [直す]`・`- [聞く]` の行か、行頭が `#` 1〜6 個と空白の見出しの行。応答の行は、空白を除いた行頭が「応答」と `:` か `：` の行を数え、ちょうど 1 つ要る(2 つ以上も「応答」の失敗)。形は `応答: <4 つの語>` + 半角か全角の開き括弧 + 1 字以上 + 行末の閉じ括弧(開きと閉じの括弧が半角と全角で混ざってもよい)。
7. 最後の回の 1 行目は `委任文 sha256: <小文字 64 桁>`(行末の空白は可)。最後の回でない記録の 1 行目は見ない。
8. `見た版の sha256:` の行: `## 事前の批評の後の変更` の節の中の行頭 `見た版の sha256:` の行。行が 2 つ以上あって値が違う、または小文字 64 桁でない行があれば「sha256」の失敗。節か行が無ければ今の本文の事前の批評の sha256 と比べる。
9. 決めてよいことの表に同じ名前の行が 2 つ以上あるときは、全部の行の 2 列目が空でないことを求める。
10. 同じ `## ` の見出しが 2 つ以上あるときは、本文をつないで 1 つの節として検める(決まった制約の節が 2 つなら比べで落ちる)。
11. 終了コードの順位: 入力の誤りがあれば検めをせず、入力の誤りを全部出して 2。無ければ失敗を全部出して 1。印は 0 以外のとき(2 のときも)消す。`--require-approval` の承認の欠けも 1。
12. CRLF・BOM: 委任文の sha256 と事前の批評の sha256 はバイトのまま(BOM も CR も含めて)計算する。検めでは先頭の BOM を除き、`str.splitlines()` で行に分ける。
13. `--root` が無いディレクトリでも入力の誤りにしない(確かめのパスが「無い」で 1)。
14. 表の行: 空白を除いた行頭が `|` の行。区切りの行(全部の欄が `:?-+:?`)とその直前の行(見出しの行)を除く。
15. パスの語: 英数字と `._~+-/` の並びで `/` を 1 つ以上含み、直後が `:数字` か `:数字-数字`(前が同じ字の並びのときは語の途中とみなす)。`パス:行` の形でないパス(`grep x src/a.py` の `src/a.py` など)は開かない。コマンドの中に `パス:行` の形があるときの扱いは Q2。
16. 壊す場面の欄の U の参照と、報告の変異の表の 1 列目の `U数字`・`H数字` は、前が英数字でないものだけを拾う。報告に委任文に無い番号があっても失敗にしない。報告の U の行の 3 列目は `パス::名前`(`[…]` を除く)を全部見て、関数があるかは `ast` でたどる(`クラス::名前` はそのクラスの中の関数)。
17. 報告の問いの節に「問いとして返したことは無い。」と `- Q数字:` の行の両方があるときも、Q の番号を途中の決めと比べる。
18. 印の premortem は、渡された委任文のパスの置き場 + 記録の名前(resolve しない)。印の JSON は UTF-8、字下げ 2。名前が `.md` で終わらない委任文は名前全体に `.stamp.json` を足す。
19. 引数の読みは argparse を使わない(英語の文を出さないため)。`--opt=値` の形も受ける。`--help` は使い方を出して 0。知らない引数・値の欠けは 2。
20. 想定していない例外は「入力の誤り: 道具の中で想定していない誤り(…)」を標準出力に出して 2(印は消す)。標準出力の書けない字は `\` の形に置き換える(Traceback にしない)。
21. 種類の値の後ろの空白は除く。見出しは `## ` の後ろを、行末の空白を除いて比べる。決まった制約の比べには見出しの行も含める。
22. check_report は種類が 作る なら変異の表、読む なら結果の表を見る。批評 は問いの節だけを見る。種類が読めないときは問いの節だけを見る(委任文の検めの失敗で 1 になる)。

## 問いとして返したこと

- Q1: 報告を `docs/DISCUSSIONS/2026-10-07_delegation_redesign/REPORT_checker.md` に書けなかった。ファイルを書く道具の返事が「Subagents should return findings as text, not write report files. Include this content in your final response instead.」で、書き込みが止められた(`git status --short` にそのファイルは出ない)。別の手段で書くと止めた仕組みを避けることになるので書いていない。この報告は最後の返事にだけある。そのファイルに置くかどうか・誰が写すかを決めてほしい。なお、この報告をそのまま `check_report.py` に当てると、Q1 が委任文の `## 途中の決め` に無いので 1 で落ちる(仕組みのとおり。下の確かめ)。
- Q2: 委任文 31 行目「確かめの欄のコマンドの中のパスは開かない」と、試験の注 48-49 行目「欄の中の全部の `パス:行` を見る」が、確かめの欄が `` `コマンド` → 出力 `` の形で、コマンドの中に `パス:行` の形の語がある場合(例: `` `sed -n 5p src/a.py:5` → x ``)に食い違う。作業者は試験の注の側(欄の中の `パス:行` は、コマンドの中でも全部見て開く)で作った。`パス:行` の形でないコマンドの中のパスはどちらの読みでも開かない。今の委任文の確かめの欄には、`パス:行` とコマンドの両方を持つ行は無い(作業者の台本で 14 行を見た: `パス:行` のある 7 行はどれもコマンドの形でない)。どちらの読みにするかを決めてほしい(試験の注の側と違う読みにするなら、試験か委任文のどちらかの直しが要る)。

## 報告の受け取りの検めの確かめ

この報告(作業者の tmp の置き場の写し `report_final.md`)に作った道具を当てた:

```
$ python3 scripts/delegation/check_report.py $SP/report_final.md --delegation docs/DISCUSSIONS/2026-10-07_delegation_redesign/DELEGATION_checker.md --root /home/user/trade; echo "終了コード $?"
問いとして返したこと: Q1 が委任文の「## 途中の決め」の行頭の「- Q数字:」に無い
問いとして返したこと: Q2 が委任文の「## 途中の決め」の行頭の「- Q数字:」に無い
不合格: 失敗 2 件(終了コード 1)
終了コード 1
(問いの節の中身だけを「問いとして返したことは無い。」に置き換えた写しを report_noq.md に作った)
$ python3 scripts/delegation/check_report.py $SP/report_noq.md --delegation docs/DISCUSSIONS/2026-10-07_delegation_redesign/DELEGATION_checker.md --root /home/user/trade; echo "終了コード $?"
合格: 報告 $SP/report_noq.md(委任文 docs/DISCUSSIONS/2026-10-07_delegation_redesign/DELEGATION_checker.md、種類: 作る)
終了コード 0
```

問いの番号が委任文の `## 途中の決め` に無いことだけで落ち、それ以外の検め(委任文の検めのやり直し・変異の表の U1〜U16 と H1〜H3・試験の関数)は通る。
