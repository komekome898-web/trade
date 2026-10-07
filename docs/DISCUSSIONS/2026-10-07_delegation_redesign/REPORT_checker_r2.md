<!-- 作業者が tmp の置き場に書いた report_r2.md をリードがそのまま写した(作業者の道具はファイルを書けない。委任文 4 版目の「報告」の節)。 -->
# 報告: 委任文の検めと報告の受け取りの検めの道具(DELEGATION_checker.md 4 版目、作り直しの 1 周)

委任文の終わる条件(逐語): 「`tests/delegation/test_spec.py` が飛ばし 0 で全部通り、U16 と H1〜H3 が通り、変異の表の全部の行で壊した変更が試験を落とした。」
作り直しは 1 周で終えた(リードの依頼文の上限「作り直し 1 周」の中)。

## 着手前の表

| やろうとすること | オーナーの原文の該当語(逐語)/根になる委任文の節 |
|---|---|
| `scripts/delegation/check_delegation.py` を直した試験に合わせて直す | L-797「**yes**」/ 節「作るもの」 |
| `scripts/delegation/check_report.py` を直した試験に合わせて直す | L-797「**yes**」/ 節「作るもの」 |
| `tests/delegation/test_spec.py` を変えずに、飛ばし 0 で全部通す | L-797「**yes**」/ 節「受け入れ」・「決めてよいこと」の 確かめ方 |
| `tests/delegation/test_extra.py` の U16 の試験に `--require-approval` を付け、目的の外の引用の試験を足す | L-797「**yes**」/ 節「受け入れ」U16・「決めてよいこと」の 出力の置き場 |
| U16 を tmp の写しで `--require-approval` 付きで確かめる | L-797「**yes**」/ 節「受け入れ」U16 |
| H1〜H3 を確かめる | L-797「**yes**」/ 節「変えないもの」 |
| 変異の表を tmp の写しで作り直す | L-797「**yes**」/ 節「変異の表」 |
| 試験で決まらない拾い方を決め、報告に書く | L-797「**yes**」/ 節「決めてよいこと」の 分母・数え方・絞り方・選び方・失敗の文の言い回し |
| 報告を返事に出す | L-797「**yes**」/ 節「報告」 |

右の列が空の行は無い。

## 作ったファイルの一覧

```
$ git status --short
 M docs/AUDITOR/TRACE/2026-10-07_220780c0.json
 M scripts/delegation/check_delegation.py
 M scripts/delegation/check_report.py
 M tests/delegation/test_extra.py
```

- `scripts/delegation/check_delegation.py`(直した)
- `scripts/delegation/check_report.py`(直した。委任文の検めの部品は check_delegation.py の「共通の部品」の写し)
- `tests/delegation/test_extra.py`(直した。U16 の試験に `--require-approval` を付けた。`test_quote_outside_purpose_ignores_reading_column` を足した)

直した中身(批評家 1 回目の指摘と試験の場面ごと):
- 承認: `## オーナーの承認` の引用が通り、かつ OWNER_LOG のその番号の行のうち、逐語の欄に引用を含む行が、行のどこかに委任文の名前(渡したパスの最後の部分)と今の事前の批評の sha256 を含むときだけ approved(L-796)。
- 目的の節: 番号の付いた引用が 1 つも無ければ「目的」で失敗。引用は、逐語の欄の区切りで始まり区切りで終わる所に含まれなければ失敗。
- 引用の比べの前に `<br>` を空白にする(OWNER_LOG と引用の両方)。
- 要る見出しが 2 つ以上・要る見出しの本文が空白だけ、を「見出し」で失敗。
- 終わる条件と上限は、行頭の `- 終わる条件:`・`- 上限:` の行と、コロンの後の中身を見る。
- 事前の批評の記録の指摘は、試験の注の正規表現(番号・星・字下げ・太字・[止める])で数える。
- 読んだ事実の `パス:行`: バッククォートの中身が丸ごと `<パス>:<行>` なら日本語の名前も拾う。
- 封印は、畳んだ絶対のパスに `/docs/research/window1/`・`/backtest_data/phase2_sealed/` を含むかでも見る(`--root` によらない)。
- check_report: 委任文の検めを承認つきでやり直す。問いは、途中の決めの同じ番号の行が問いの文を含むかで比べる。報告の着手前の表を見る。

`test_extra.py` は `import test_spec as S` で試験の作り物を使う(名前で取り込まないので、test_spec の試験は二重に集まらない)。同じ名前のファイルがほかに無いことと、試験全体の集めに誤りが無いことを確かめた: `find tests -name 'test_spec.py' -o -name 'test_extra.py'` → `tests/delegation/test_extra.py`・`tests/delegation/test_spec.py` の 2 つだけ/`PYTHONPATH=src python -m pytest --collect-only -q tests` → 終了コード 0、集めの誤り 0。
コミット・プッシュ・git add・git worktree add はしていない。フック・設定・`.claude/agents/` は変えていない。封印の置き場は読んでいない。`docs/` の下の印(`DELEGATION_checker.stamp.json`)はリードがコミットしたもので、作業者は触れていない(`git status` に出ない)。

## 試験のコマンドと出力

```
$ PYTHONPATH=src python -m pytest tests/delegation
...............                                                          [100%]
15 passed in 12.94s
```

(15 = `test_spec.py` の 12 + `test_extra.py` の 3。飛ばし 0。)

## U16・H1〜H3 の確かめのコマンドと出力

U16(委任文 4 版目と記録 1〜4 を、名前を変えずに tmp の 1 つの置き場に写し、`--require-approval` を付けて当てた):

```
$ SP=<作業者の tmp の置き場>; mkdir $SP/u16r2 && cp docs/DISCUSSIONS/2026-10-07_delegation_redesign/DELEGATION_checker.md docs/DISCUSSIONS/2026-10-07_delegation_redesign/DELEGATION_checker_premortem{1,2,3,4}.md $SP/u16r2/
$ python3 scripts/delegation/check_delegation.py $SP/u16r2/DELEGATION_checker.md --root /home/user/trade --require-approval; echo "終了コード $?"
合格: $SP/u16r2/DELEGATION_checker.md(種類: 作る、承認: あり)
印: $SP/u16r2/DELEGATION_checker.stamp.json
終了コード 0
$ cat $SP/u16r2/DELEGATION_checker.stamp.json
{
  "delegation_sha256": "e79ee3ea33724bff9510d77d7925db620538692d0c0fc67a2082204886cd8fb4",
  "body_sha256": "026413be2dfbffe7d5c9a9dda9746959d1de741bb62f865c21eaa04f4c3af1c0",
  "kind": "作る",
  "premortem": "$SP/u16r2/DELEGATION_checker_premortem4.md",
  "approved": true
}
```

(`$SP` は `/tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad`。出力のパスを `$SP` に縮めて書いたのはこの塊だけ。)
事実: body_sha256 026413be… は、OWNER_LOG の L-797 の行の「版 026413be2dfbffe7d5c9a9dda9746959d1de741bb62f865c21eaa04f4c3af1c0」と同じ(`grep -n "^| L-797" docs/OWNER_LOG.md` → 857 行目)。承認はこの行で結び付いた。

批評家 1 回目の壊し方を、本物の委任文の写しで打ち直した(台本は作業者の置き場の `attack.py`。全部 `--require-approval` 付き):
- 承認の引用を `- L-791「**根本的な**」` に替えた → 終了コード 1「承認: …委任文の名前 DELEGATION_checker.md と今の事前の批評の sha256 026413be2dfb… を含む行がある引用が無い」
- 本文の「外の呼び出し(jev ほか)はしない。…」を「をしてよい。」に替えた → 1「承認: …sha256 0767eace9ae1… を含む行がある引用が無い」
- 目的の引用を `- L-791「**て**」` に替えた → 1「引用: 13 行目の L-791 の引用「て」は、逐語の欄の区切りで始まり区切りで終わる所に無い…」
- 2 つ目の `## 決まった制約` を足した → 1「見出し: 「## 決まった制約」が 2 つある」
- 記録 4 に「1. [直す]」「* [直す]」「  - [直す]」「- **[直す]**」「- [止める]」を足した → 1「応答: 記録 DELEGATION_checker_premortem4.md の 107 行目の指摘に「応答: 」の行が無い」ほか
- 確かめの欄を日本語の名前の `docs/DISCUSSIONS/2026-09-14_instruction_adherence/01_長文脈での指示追従の劣化.md:1` に替えた → 読んだ事実の失敗は出ず、本文を替えたことによる「承認」の失敗だけ

H1:

```
$ git diff --stat -- scripts/jev_delegate.py scripts/jev_report_intake.py scripts/check_bt_delegation.py tests/delegation/test_spec.py
(何も出ない)
$ git diff --stat
 docs/AUDITOR/TRACE/2026-10-07_220780c0.json |  34 +++-
 scripts/delegation/check_delegation.py      | 208 ++++++++++++++++------
 scripts/delegation/check_report.py          | 256 +++++++++++++++++++++-------
 tests/delegation/test_extra.py              |  19 ++-
 4 files changed, 396 insertions(+), 121 deletions(-)
```

(`docs/AUDITOR/TRACE/2026-10-07_220780c0.json` は作業者が書いたものではない。H3 の前の出力のとおり、試験の前から `M` だった。)

H2:

```
$ PYTHONPATH=src python -m pytest tests/test_jev_delegate.py tests/test_jev_report_intake.py tests/test_check_bt_delegation.py
100 passed in 2.55s
```

H3:

```
$ git status --short docs .claude > before.txt; PYTHONPATH=src python -m pytest tests/delegation; git status --short docs .claude > after.txt; diff before.txt after.txt && echo H3同じ; cat before.txt
...............                                                          [100%]
15 passed in 12.94s
H3同じ
 M docs/AUDITOR/TRACE/2026-10-07_220780c0.json
```

## 変異の表

壊し方: 2 本の道具を作業者の tmp の置き場に写し、写しだけを書き換えた。それを `DELEGATION_TOOLS_DIR=<写しの置き場> PYTHONPATH=src python -m pytest tests/delegation/test_spec.py tests/delegation/test_extra.py` で当てた(台本は作業者の置き場の `mutate.py`。本物の道具は壊していない)。共通の部品を壊すときは、2 本の写しの両方を同じように壊した。2 列目の「場面」は、試験が落ちたときに出た場面の名前。表で回す試験は表の行の名前、表の外の試験は落ちた試験の名前で書いた。

| 番号 | 壊した変更 | 落ちた試験 |
|---|---|---|
| U1 | check_delegation の入力の誤りの終了コードを 2 から 1 に(場面: 無い委任文 → 2) | tests/delegation/test_spec.py::test_input_errors_exit_2_and_all_failures_listed |
| U1 | check_delegation で失敗のときに古い印を消さない(場面: 失敗で印が消える) | tests/delegation/test_spec.py::test_valid_passes_writes_stamp_and_failure_removes_it |
| U2 | 種類の行を 6 行目まで見る(場面: 種類 6 行目) | tests/delegation/test_spec.py::test_form_checks |
| U3 | 見出しの一覧から「報告」を消す(場面: 見出し ## 報告・空の節 ## 報告) | tests/delegation/test_spec.py::test_form_checks、tests/delegation/test_spec.py::test_input_errors_exit_2_and_all_failures_listed、tests/delegation/test_spec.py::test_valid_passes_writes_stamp_and_failure_removes_it |
| U3 | 要る見出しが 2 つ以上あるかを見ない(場面: 見出しが 2 つ) | tests/delegation/test_spec.py::test_form_checks |
| U3 | 要る見出しの本文が空かを見ない(場面: 空の節 ## 着手前の表・空の節 ## 報告・空の節 ## 変異の表) | tests/delegation/test_spec.py::test_form_checks |
| U4 | 区切りの比べ(目的の節)の相手に OWNER_LOG の 4 列目より後ろ(読みの列)も入れる(場面: 引用 読みの列にだけある文) | tests/delegation/test_spec.py::test_form_checks |
| U4 | 目的の外の比べの相手に OWNER_LOG の 4 列目より後ろ(読みの列)も入れる(場面: 目的の外の 読みの列・「L-100 結果」の行) | tests/delegation/test_extra.py::test_quote_outside_purpose_ignores_reading_column |
| U4 | 目的の節の引用を区切りで比べない(含まれるかだけ)(場面: 目的 語の途中で切った引用) | tests/delegation/test_spec.py::test_form_checks |
| U4 | 目的の節に番号の付いた引用が要ることを見ない(場面: 目的 番号の付いた引用が無い) | tests/delegation/test_spec.py::test_form_checks |
| U4 | `<br>` を空白に置き換えない(場面: 引用 <br> は空白として比べる、ほかに U16) | tests/delegation/test_spec.py::test_form_checks、tests/delegation/test_extra.py::test_u16_real_delegation_passes |
| U5 | 行の番号の比べを 1 ゆるめる(場面: 事実 行の数 +1・事実 日本語の名前の行の数 +1・事実 範囲の後ろで比べる) | tests/delegation/test_spec.py::test_form_checks |
| U5 | バッククォートの中身が丸ごと パス:行 の形(日本語の名前)を拾わない(場面: 事実 バッククォートの中の日本語の名前) | tests/delegation/test_spec.py::test_form_checks |
| U6 | 封印の比べで小文字にしない(絶対のパスと相対のパスの両方)(場面: 封印 そのまま・封印 大文字小文字・封印 根の中の絶対パス・封印 根の外を通って根の中へ、ほかに報告の 封印の下の試験のファイル) | tests/delegation/test_spec.py::test_form_checks、tests/delegation/test_spec.py::test_report_checks、tests/delegation/test_spec.py::test_seal_regardless_of_root |
| U6 | 封印を --root からの相対のパスでだけ見る(場面: --root を docs にした封印) | tests/delegation/test_spec.py::test_seal_regardless_of_root |
| U7 | 決めてよいことの一覧から「依存」を消す(場面: 決め 依存 無し・決め 依存 空) | tests/delegation/test_spec.py::test_form_checks、tests/delegation/test_spec.py::test_input_errors_exit_2_and_all_failures_listed |
| U8 | 壊す場面の並びを見ない(場面: 場面 並び) | tests/delegation/test_spec.py::test_form_checks |
| U9 | 受け入れの U の重なりを見ない(場面: U 重なり) | tests/delegation/test_spec.py::test_form_checks |
| U10 | 決まった制約の比べで行末の空白を除かない(場面: 制約 行末の空白・空行は可) | tests/delegation/test_spec.py::test_form_checks |
| U11 | 「- 上限:」の行を探さない(場面: 上限の語が無い・上限の後が空) | tests/delegation/test_spec.py::test_form_checks |
| U11 | 「- 終わる条件:」「- 上限:」の後が空かを見ない(場面: 終わる条件の後が空・上限の後が空) | tests/delegation/test_spec.py::test_form_checks |
| U12 | 「事前の批評の後の変更」の見た版を使わず、いつも今の本文の sha256 と比べる(場面: 事前の批評の後の変更 見た版が合う、ほかに U16) | tests/delegation/test_spec.py::test_premortem_checks、tests/delegation/test_extra.py::test_u16_real_delegation_passes |
| U12 | 番号が 2 以上の最後の回の「直した」を通す(場面: 2 回目に直した・3 回目に直した) | tests/delegation/test_spec.py::test_premortem_checks |
| U12 | 指摘を行頭の「- [直す]」「- [聞く]」だけで数える(1 周目の形)(場面: 指摘の書き方 の 5 つ) | tests/delegation/test_spec.py::test_premortem_checks |
| U13 | 承認の行に今の事前の批評の sha256 があるかを見ない(場面: 承認の後に本文を変えたら承認は効かない) | tests/delegation/test_spec.py::test_require_approval_and_stamp_flag |
| U13 | 承認の行に委任文の名前と sha256 があるかを見ない(1 周目の形)(場面: 版の印の無い L-200 の行だけでは承認にならない) | tests/delegation/test_spec.py::test_require_approval_and_stamp_flag |
| U14 | 委任文を検めの前にもう 1 回 `Path.read_bytes()` で読む(場面: `^READS 1$` が出ない) | tests/delegation/test_spec.py::test_reads_delegation_once |
| U15 | check_report で変異の表の試験の関数があるかを見ない(場面: 関数が無い) | tests/delegation/test_spec.py::test_report_checks |
| U15 | check_report で委任文の検めをやり直さない(場面: 本文を直した後の受け取りは sha256 で 1) | tests/delegation/test_spec.py::test_report_stamp_and_delegation_recheck |
| U15 | check_report で承認をやり直さない(場面: 受け取りは承認つきで委任文を検め直す) | tests/delegation/test_spec.py::test_report_stamp_and_delegation_recheck |
| U15 | check_report で問いを番号だけで比べる(場面: 問いの Q3 の文が途中の決めと違う) | tests/delegation/test_spec.py::test_report_checks |
| U15 | check_report で報告の着手前の表を見ない(場面: 着手前の表が無い ほか) | tests/delegation/test_spec.py::test_report_checks |
| U16 | 事前の批評の記録の応答の行の頭の空白を除かない(本物の記録の「応答:」は 2 字下げ) | tests/delegation/test_extra.py::test_u16_real_delegation_passes、tests/delegation/test_spec.py::test_form_checks、tests/delegation/test_spec.py::test_premortem_checks、tests/delegation/test_spec.py::test_input_errors_exit_2_and_all_failures_listed、tests/delegation/test_spec.py::test_report_checks、tests/delegation/test_spec.py::test_report_stamp_and_delegation_recheck、tests/delegation/test_spec.py::test_require_approval_and_stamp_flag、tests/delegation/test_spec.py::test_valid_passes_writes_stamp_and_failure_removes_it |
| U16 | 目的の節の区切りから「？」を外す(本物の委任文の L-794 の引用は「？」の直後から始まる) | tests/delegation/test_extra.py::test_u16_real_delegation_passes |
| H1 | `git diff --stat -- scripts/jev_delegate.py scripts/jev_report_intake.py scripts/check_bt_delegation.py tests/delegation/test_spec.py` | 何も出ない(4 本とも変わっていない) |
| H2 | `PYTHONPATH=src python -m pytest tests/test_jev_delegate.py tests/test_jev_report_intake.py tests/test_check_bt_delegation.py` | 100 passed |
| H3 | `PYTHONPATH=src python -m pytest tests/delegation` の前後の `git status --short docs .claude` を diff | 前後で同じ(どちらも ` M docs/AUDITOR/TRACE/2026-10-07_220780c0.json` の 1 行だけ) |

全部の行で、壊した変更が試験を 1 つ以上落とした(「落ちなかった」の行は無い)。

変異で見つかったことが 2 つある(どちらも事実):
- 「目的の外の比べの相手に読みの列も入れる」は、はじめ `test_spec.py` のどの試験も落とさなかった。読みの列と「L-100 結果」の行の囮の場面は、目的の節の中にしか無い。目的の節は今は区切りの比べを通るので、目的の外の「含まれるか」の比べを見る場面が無かった。作業者が `test_extra.py::test_quote_outside_purpose_ignores_reading_column` を足して落ちるようにした(「決めてよいこと」の 出力の置き場 の範囲)。リードが同じ場面を `test_spec.py` に移すかは、リードが決めること。
- 「封印の比べで、--root からの相対のパスだけ小文字にしない」は、どの試験も落とさなかった。相対のパスの比べは、絶対のパスの比べに含まれる(根は絶対のパスなので、相対のパスが封印の置き場で始まれば、絶対のパスは `/docs/research/window1/` などを含む)。効きが同じ書き換えなので表には載せず、両方の小文字を外す変更に替えた。試験の注が挙げる 2 つの比べは、両方そのまま残している。

## 試験で決まらず作業者が決めた拾い方の一覧

1 周目の 22 の拾い方のうち、10 と 15 を直した(10 は批評家 1 回目の指摘どおり誤りだった)。ほかは変えていない。足したものは 23 から。

1. 行の数: `\n` の数。最後の行に改行が無ければ 1 足す(空のファイルは 0 行)。CR だけの改行は数えない。
2. 行の番号 0 と逆向きの範囲(`a-b` で a > b)は「読んだ事実」の失敗。範囲は後ろの b をファイルの行の数と比べる。
3. 引用の前後の両方に番号があるとき: 前の番号か後ろの番号のどちらか一方で、並びの全部の引用が通れば通す。通らなければ両方の番号を出す。番号と引用の間、並びの引用どうしの間は、半角の空白とタブだけを許す。行をまたぐ引用は見ない。番号の直前が英数字か `-` のときは番号と見ない。
4. OWNER_LOG の表の区切り: バッククォートの対の中と `\|` は区切りでない。対にならないバッククォートはただの字として扱う。
5. 事前の批評の記録の番号: 数字を整数で比べ、一番大きいものを最後の回とする(同じ数が 2 つあれば名前の並びで後ろ)。記録がディレクトリか UTF-8 でないときは「事前の批評」の失敗(終了コード 1)。
6. 指摘の範囲の終わりは、次の指摘の行か、行頭が `#` 1〜6 個と空白の見出しの行。応答の行は、空白を除いた行頭が「応答」と `:` か `：` の行を数え、ちょうど 1 つ要る。形は `応答: <4 つの語>` + 半角か全角の開き括弧 + 1 字以上 + 行末の閉じ括弧(半角と全角が混ざってもよい)。
7. 最後の回の 1 行目は `委任文 sha256: <小文字 64 桁>`(行末の空白は可)。最後の回でない記録の 1 行目は見ない。
8. `見た版の sha256:` の行が 2 つ以上あって値が違う、または小文字 64 桁でない行があれば「sha256」の失敗。節か行が無ければ、今の本文の事前の批評の sha256 と比べる。
9. 決めてよいことの表に同じ名前の行が 2 つ以上あるときは、全部の行の 2 列目が空でないことを求める。
10. (直した)要る見出しが 2 つ以上あれば「見出し」で失敗する(試験の注のとおり)。要る見出しでない見出しの重なりは失敗にしない。本文は、重なった節をつないで検める。
11. 終了コードの順位: 入力の誤りがあれば検めをせず、入力の誤りを全部出して 2。無ければ失敗を全部出して 1。印は 0 以外のとき(2 のときも)消す。
12. CRLF・BOM: 委任文の sha256 と事前の批評の sha256 は、バイトのまま計算する。検めでは先頭の BOM を除き、`str.splitlines()` で行に分ける。
13. `--root` が無いディレクトリでも入力の誤りにしない(確かめのパスが「無い」で 1)。
14. 表の行は、空白を除いた行頭が `|` の行。区切りの行(全部の欄が `:?-+:?`)と、その直前の行(見出しの行)を除く。
15. (直した)`パス:行` は 2 通りで拾う。(1) バッククォートの中身が丸ごと `(\S*/\S*?):(\d+)(-(\d+))?` に当たるもの(日本語の名前も可)。(2) それ以外の所(コマンドの中も。Q2 の答えのとおり)では、英数字と `._~+-/` の並びで `/` を含み、直後が `:数字` か `:数字-数字` のもの。`パス:行` の形でないパスは開かない。
16. 壊す場面の欄の U の参照と、報告の変異の表の 1 列目の `U数字`・`H数字` は、前が英数字でないものだけを拾う。報告に委任文に無い番号があっても失敗にしない。関数があるかは `ast` でたどる。
17. 報告の問いの節に「問いとして返したことは無い。」と `- Q数字:` の行の両方があるときも、Q を途中の決めと比べる。
18. 印の premortem は、渡された委任文のパスの置き場 + 記録の名前(resolve しない)。名前が `.md` で終わらない委任文は、名前全体に `.stamp.json` を足す。
19. 引数の読みに argparse を使わない(英語の文を出さないため)。`--opt=値` の形も受ける。`--help` は 0。知らない引数・値の欠けは 2。
20. 想定していない例外は「入力の誤り: 道具の中で想定していない誤り(…)」を標準出力に出して 2(印は消す)。
21. 種類の値の後ろの空白は除く。決まった制約の比べには見出しの行も含める。
22. check_report は、種類が 作る なら変異の表、読む なら結果の表を見る。批評 と種類が読めないときは、問いの節と着手前の表だけを見る。
23. 目的の節の区切りの比べ: OWNER_LOG の逐語の欄の「**」「**」を空白にし、`<br>` を空白にし、空白をそろえて両端を除いたものと比べる(欄の端 = 引用符の内側の頭と終わり)。区切りに当たる場所が 1 か所でもあれば通す。含まれるが区切りに当たらないときは「語の途中で切っている」と出す。
24. `<br>` は `<br>`・`<br/>`・`<br />` と大文字を空白にする。
25. 承認: 委任文の名前は渡したパスの最後の部分。行全体(OWNER_LOG の生の行)に、名前と今の事前の批評の sha256(見た版ではなく、今の本文の値)が文字として含まれるかを見る。承認の節の引用の比べは「含まれるか」(区切りの比べは目的の節だけ)。
26. 封印: 封印に当たれば、根の外より先に「封印」と出す(根の外で封印の名前を含むパスも「封印」)。
27. 終わる条件と上限: 行頭ちょうど `- 終わる条件:`・`- 上限:`(全角のコロンは不可)。同じ行が 2 つ以上あれば、1 つでもコロンの後に中身があれば通す。
28. 空の節: 本文が空白と空行だけのときに空とする(表の見出しの行だけの節は空としない)。
29. 報告の問い: `- Q数字:` の後ろの文を、空白をそろえて両端を除き、途中の決めの同じ番号の行(空白をそろえた行全体)に含まれるかで比べる。問いの文が空なら失敗。
30. 報告の着手前の表: 2 列目に番号の付いた引用の並びがあれば、全部を「含まれるか」で比べる(区切りの比べは当てない)。番号の無い引用しか無い行は、引用が無い行として扱う。その行の 1 列目の文(空白をそろえて両端を除いたもの)は、問いの節の `- Q数字:` の行全体のどれかに含まれれば通す。1 列目が空なら通さない。
31. check_report の承認の失敗は「委任文の検め: 承認: …」と出す(印は読まない)。

## 問いとして返したこと

問いとして返したことは無い。

## 報告の受け取りの検めの確かめ

この報告(作業者の tmp の置き場の写し `report_r2.md`)に、作った道具を当てた(委任文の検めは承認つきでやり直される):

```
$ python3 scripts/delegation/check_report.py $SP/report_r2.md --delegation docs/DISCUSSIONS/2026-10-07_delegation_redesign/DELEGATION_checker.md --root /home/user/trade; echo "終了コード $?"
合格: 報告 $SP/report_r2.md(委任文 docs/DISCUSSIONS/2026-10-07_delegation_redesign/DELEGATION_checker.md、種類: 作る)
終了コード 0
```
