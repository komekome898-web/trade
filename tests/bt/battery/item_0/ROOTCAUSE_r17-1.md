# 場面集への指摘の根本原因と主張の表(項目 0、第 r17-1 回の直し、場面係、2026-09-25)

合意した完了の形(オーナー逐語、L-405): 「**すべてが調査結果以上の信頼性と再現性に優れたものにすること。**」

この回の場面集への指摘は [止める] 1 件(i0-r16-04、repeat_of null)。起動文の逐語「直しの前に … ROOTCAUSE_r17-1.md に、この直しが触る主張の族ごとに 4 列の表を書く」(L-443)に従い、§1〜§5 を直す前に書き、§6 以降を直したあとに書く。`<S>` = `/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/r17-1/`(この回の一時の出力の置き場所)。版: 起動の始めの HEAD は 1d8a107。

委任文の指紋: 起動文は `20260923_backtest_env_prompt.md@cdf623e4fb24` と書くが、今のファイルの sha256 の先頭 12 桁は `20487e2d8aec`(コミット abb256d、オーナー決定 L-445)。cdf623e4fb24 は 1 つ前のコミット dc3f666 の版で、2 つの版の違いは L-445 の射程の行と批評家の格付けの段落の 1 文だけ(`git diff dc3f666 abb256d -- docs/DATA/delegations/20260923_backtest_env_prompt.md` の出力は 2 行の追加と 1 行の削除)。場面係の手順の文は変わっていない。今の版を全部読んで従った。

## 0. 対応表(CLAUDE.md §0.1。右は起動文・指摘・リードの答えの逐語)

| やること | 該当語(逐語) |
|---|---|
| 直しの前に根本原因と主張の表をこのファイルに書く | 起動文「直しの前に /home/user/trade/tests/bt/battery/item_0/ROOTCAUSE_r17-1.md に、この直しが触る主張の族ごとに 4 列の表を書く」 |
| 散文の定義を書かない | 起動文「散文の定義は書かない(定義の段は無い)」 |
| 「入口があり、その入口が断った」と「入口が無い」を採点で分ける。文の読みでなく機械の欄で | 指摘 i0-r16-04「直し方の向き: 「入口があり、その入口が断った」と「入口が無い」を採点で分け(文の読みでなく機械の欄で)」 |
| 入口が断ったことを、NO_INT の場面の正解と一致に数える | 指摘 i0-r16-04「前者を NO_INT の場面の正解と一致に数える」 |
| リードの答え「断る」も正解に入れる(黙って丸めた値は不一致)を当てる | 指摘 i0-r16-04 が引くリードの答え「float が正確に持たない値では「断る」も正解に入れる(黙って丸めた値は不一致)」と「答えは既にあるので次の直しで当てる」 |
| 直すファイルは run_battery.py・adapters/common.py・scenes.py・gen_definitions.py | 指摘 i0-r16-04 の fix_files |
| 批評家の試験 `test_i0r16_no_int_scene_tells_refusal_from_no_entry.py` を変えずに通す | 指摘 i0-r16-04「試験(残す、場面係が直す)」 |
| 同じ種類の欠陥を場面集の全体で探して直す | 起動文「指摘の文言だけに合わせる直しをしない: 同じ種類の欠陥を場面集の全体(全観点・全場面・検討表の全行)で探して直す」 |
| リードの答えを変えるなら「リードに聞くこと」と `lead_answer_changes` に書く | 起動文「変えた点と理由を ROOTCAUSE_r17-1.md の節「リードに聞くこと」に書き、同じ文を lead_answer_changes に返す(無ければ空の配列)」 |
| 実装(`src/bot/bt/`)と作業者の試験(`tests/bt/item_0/`)に触れない | 起動文「実装(src/bot/bt/ の下)と作業者の試験(tests/bt/item_0/)には触れない」 |
| 直した規則ごとに全格子の敵対者の試験を先に書き、列に入れなかった物を試験のファイルに書く | 起動文「(6) 直した規則ごとに、その規則の入力の空間を全格子で列べる敵対者の試験 … を先に書き、規則を直したあと通す。列に入れなかったものを試験のファイルに書く」 |
| 場面の期待は要件の文から独立に出し、新実装の内部の名前・形を写さない | 起動文「場面の期待は要件の文から独立に出せる振る舞いで書き、新実装の内部の名前・形を写さない(規則 2)」 |
| 検討表を検査器で誤り 0 件にする | 起動文「python3 scripts/check_bt_considered.py … --write を走らせて誤り 0 件にし」 |
| 返す前に `git diff --name-only HEAD` の出力を末尾に貼る | 起動文「返す前に「git diff --name-only HEAD」を走らせ、その出力を rootcause のファイルの末尾に貼る」 |
| 直す前に落ちた試験・走らせ直し・比較の出力の写しを scratchpad の外にも置く | リードの答え F4(VERDICTS run11 item0、10:55 UTC)「場面係は「直す前に落ちた試験の出力」「走らせ直しの出力」「比較の出力」の写しを `docs/DISCUSSIONS/2026-09-23_backtest_env/item_<N>/battery/materials/<回>/` に置く(scratchpad だけに置かない)」。起動文の lead_notes には無い(§5.2 の 2) |
| P0-2 の全場面で入口の基準を揃える(F3) | **(この起動の該当語なし)**。リードの答え F3 は VERDICTS run11 item0 にあり「次の起動の lead_notes に写す」とされたが、この起動の lead_notes には無い。この回は当てず、§5.2 の 1 で聞く |

## 1. 指摘の一覧

| id | 格 | 相手 | repeat_of | この回で扱う物 |
|---|---|---|---|---|
| i0-r16-04 | [止める] | 場面集 | null | 正解が NO_INT の 5 場面で、入口が断った対象と入口の無い対象が同じ「対応なし」になり、どの対象も「正解と一致」にならない |

## 2. なぜ起きたか(根本原因)

- **根 1(結果の欄に「入口を呼んで断られた」を持つ機械の欄が無かった)**: 場面の結果の状態は ok / not_supported / error の 3 つで、`not_supported` は「その能力の口が無い」と「口を呼んだら断った」の両方に使われていた(`adapters/common.py` の `unit_time` の 147-148 行 = 入口が無い、153-154 行 = 入口が例外で止まった。どちらも `not_supported(文)`)。区別は `detail` の文の中にしか無く、runner の `correctness`(`run_battery.py` 705-710 行)は状態だけを見て `not_supported` を全部「対応なし」にした。文は採点に使わない(場面集の規則 1・2)ので、区別する機械が場面集のどこにも無かった。
- **根 2(場面の正解に、どの振る舞いでも届かなかった)**: NO_INT の 5 場面の期待は `{"int64_ns": NO_INT}` で、NO_INT は文字列。runner の採点(`_grade_unit_time`)は int64 の整数か null しか出さないので、この期待はどの対象の出力とも一致しない。場面集の規則 1「能力があるかは、その能力を使ったときに出るはずの結果(正解)が出たかで決める」の「出るはずの結果」が、NO_INT の場面では「断る」なのに、正解の欄が「断る」を表せなかった。第 r16-1 回の場面係はこれを規則 5 の順(対応なし > 不一致)で済ませ、正解の形を変えずにリードに聞いた(ROOTCAUSE_r16-1.md §5.2 の 1)。
- **根 3(正解に届く振る舞いがあるかを見る試験が無かった)**: 場面ごとに「どの振る舞いなら正解と一致になるか」を機械で示す試験が無く、全場面のうち正解に届かない場面があっても試験は落ちなかった。第 16 周の表で、新実装は P0-2 の 18 場面のうち 13 場面しか「正解と一致」にならず、欠けた 5 場面がちょうど NO_INT の 5 場面だった(VERDICTS run11 item0 の資料係の数え「新実装: 3/3, 13/18, …」)。

同じ種類の欠陥を場面集の全体で探した方法(結果は §6.3):
- 正解に届く振る舞いが無い場面: 全 46 場面の期待を、runner が出しうる採点の値(場面ごとの採点の関数の出力の型)と照らす。場面の期待が「断る」のときは、断りの記録を通す採点の道があるかを見る。
- 「口が無い」と「口が断った」を混ぜる採点: runner の全ての採点の道(`correctness`・`GRADERS` の 5 種・`_attempts_problem`)で、断ることが正解になる場面があるかを見る。P0-4 の `p4-future-read-attempt` は断りを試しごとの記録(`common.Attempts` の `raised` と投げた所)で採点していて、状態 `not_supported` に頼らない(混ぜていない)。
- 同じ文を持つ場所: 「断れば「対応なし」」と書いた文(`scenes.py` の `_UNIT_NOTE`・`_NO_INT_TAIL`、`gen_definitions.py` の正しさの行、`protocol.py`・`common.py`・`run_battery.py` の docstring、DEFINITIONS.md)を全部探す。
- 検討表: 行は採点の規則に拠らない(P0-2 の動かせなかった候補 44・58 は「再現できない(危険)」)。検査器を回して確かめる。

## 3. どの作りを変えるか

1. `adapters/common.py`:
   - `refusal(exc, field, handed)` を足す: 対象の入口を場面の入力の欄 `field` の物 `handed` で呼んで例外が出たとき、その例外の物から記録を作る(例外の型と文、トレースバックの枠のファイルを外から内へ、最も内の枠のファイルと、それが場面集の側の raise 文か、翻訳した道具の driver が印した断り `CompiledRefusal` か)。記録は `Record` で、`made_here` に載る(手で書いた dict は runner が拒む)。
   - `CompiledRefusal` を足す: 翻訳した道具(Rust・Go など)の driver が印した道具自身の断り(例: Rust の `Err`)を、adapter がその文のまま運ぶ例外。
   - `unit_time`: 入口が例外で止まったとき、状態は今までどおり `not_supported`、`provenance` に `{"reader": 入口の名, "refusal": refusal(例外, "time", 入力の物)}` を載せる。入口が無いときは `provenance` を持たない(断りの記録が無い)。
2. `run_battery.py`:
   - `refusal_problem(res, scene, target, roots)`: 断りを対象に帰せない理由、または None。条件(全部): 状態が `not_supported` / `provenance["refusal"]` が common.py で例外から作った記録 / 断った入口(`provenance["reader"]`)が対象の物(`_reader_problem`)/ 入口に渡した物が場面の入力のその欄と同じ型・同じ値 / Python の入口なら、トレースバックに対象の配布物の枠があり、その最も外の対象の枠より内側に場面集の側のファイルの枠が無く、最も内の枠が場面集の側の raise 文でない / 翻訳した道具の入口なら、例外が `CompiledRefusal`(driver が印した道具の断り)。
   - `expects_refusal(expected)`: 期待が「断る」を正解とするか(期待の辞書の鍵 `scenes.REFUSED` が True)。
   - `correctness`: `not_supported` のうち、期待が「断る」で `refusal_problem` が None のものを「正解と一致」。ほかの `not_supported` は今までどおり「対応なし」。ok は採点の値で照らす(期待が「断る」の場面では、何かの時刻を作った ok は「不一致」)。
   - `graded_output`: 断りの記録を持つ `not_supported` は `{"refused_by_entry": 帰せたか, "refusal_problem": 理由}` を採点の値として出す(表の出力の欄に機械の判断が出る)。`_grade_unit_time` は ok に `"refused_by_entry": False` を足す。
   - `compact`: 断りの記録の枠のファイルの列は、対象の配布物のファイルと数だけを残す(`touched` と同じ扱い)。
3. `scenes.py`:
   - `REFUSED = "refused_by_entry"` を置き、NO_INT の 5 場面の期待を `{"int64_ns": NO_INT, "refused_by_entry": True}` にする(正解は「対象の入口が断る」。どの整数を返しても「不一致」)。値の正解がある場面の期待は変えない(断りは「対応なし」)。
   - `_UNIT_NOTE`・`_UNIT_GRADED`・`_NO_INT_TAIL` の文を、機械の採点どおりに直す(断れば正解と一致 = 正解が「断る」の場面、ほかの場面の断りは対応なし、入口が無ければ対応なし)。
4. `gen_definitions.py`: 正しさの行に「期待が「断る」の場面では、対象の入口が場面の入力で呼ばれて断ったこと(runner が断りの記録と出所から確かめた物)が正解と一致」を足す。良い順の行もそれに合わせる。
5. `adapters/protocol.py`: 規則の文に「断りの記録は `common.refusal` で作る。runner は `detail` の文を読まない」を足す。
6. `opponents/barter_adapter.py`: driver が道具の断り(`de_error` = Rust の `Err` の文)を印したときは `C.CompiledRefusal` で運ぶ。driver が何も出さなかったときは今までどおり adapter の例外(断りに数えない)。
7. 試験(直す前に書く): `test_battery_r17_refusal.py`(§4 の (c)・(d))。既存の `test_battery_r16_units.py` の正解の神託を、正解が「断る」の場面の期待に合わせて直す(規則 8: 前の周に作った試験は設計を変えたときに書き直してよい。消さない)。
8. 全対象を走らせ直して `survey_results/` を作り直す。DEFINITIONS.md を作り直し、行と語の判断を足す。直す前に落ちた試験の出力・走らせ直しの出力・比較の出力の写しを `docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/battery/materials/r17-1/` に置く(リードの答え F4)。

## 4. 主張の表(この直しが触る主張の族ごと。直す前に書いた)

| 主張の族 | (a) 導く関数 | (b) 手書きが残る部分と、機械で導けない理由 | (c) 手書きの主張が 1 つでも残っていれば落ちる試験 | (d) 主張を作る機械への mutant の試験 |
|---|---|---|---|---|
| 15. 断りを対象の入口に帰す(「入口があり、その入口が断った」と「入口が無い」を機械の欄で分ける) | `adapters/common.py:refusal`・`adapters/common.py:unit_time` → `run_battery.py:refusal_problem` | 翻訳した道具の断り: driver のコードが道具の `Err` を印したことは Python のトレースバックに現れないので、`CompiledRefusal` を運んだ adapter の文が道具の断りの写しかは機械で確かめられない(批評家が driver のコードを読む。今この形を使うのは barter の 1 つ)。各道具のどの入口がどの単位を読むかは第 r16-1 回と同じ手書き(adapter の注釈に行) | `test_battery_r17_refusal.py:test_refusal_rule_on_every_cell_of_the_grid`(記録の出所 × 入口の出所 × 例外の道筋 × 渡した物 × 状態 の全格子を、規則の文から書いた神託と照らす。本物の例外を、対象の配布物に見立てた一時のフォルダのファイル・第三者のファイル・場面集のファイルから投げて作る)、同 `test_unit_time_records_a_refusal_only_when_an_entry_raised`(入口の組 × 入力 × 入口の結果 の全格子)、批評家の `test_i0r16_no_int_scene_tells_refusal_from_no_entry.py`(変えずに通す) | 同 `test_mutants_of_the_refusal_rule_are_caught`(記録の出所を見ない / 入口の出所を見ない / 道筋に対象の枠を求めない / 対象の枠より内の場面集の枠を見ない / 渡した物を見ない / raise 文を見ない / 翻訳した道具の印を見ない)、同 `test_mutants_of_unit_time_refusal_are_caught`(入口が無くても記録を作る / 断りに記録を付けない / 別の物を渡した物として記録する) |
| 16. 正解が「断る」の場面の集合 = 入力が持つ値 × 倍率 がナノ秒の整数にならない場面 | `scenes.py`(`_UNIT_PLAN` の期待と `REFUSED`) | 正解そのものは場面係が手で書く(委任文 §3「値の場面 … エンジンを見ずに手計算・閉じた式で出した正解」)。機械は照らす側だけ | `test_battery_r17_refusal.py:test_refusal_is_the_answer_exactly_where_no_int_is`(全場面で、期待が「断る」の場面 = `fractions.Fraction` で作り直した値が整数にならない単位の場面、ほかの場面の期待は断りを求めない)、`test_battery_r16_units.py:test_unit_scene_answers_are_the_closed_form`(神託を直す) | 同 `test_mutants_of_the_refusal_answer_set_are_caught`(神託に: float を最短の表記で読む / 整数の場面にも断りを求める / 断りの印を外す) |
| 17. 採点: 期待が「断る」の場面で、帰せた断りだけが正解と一致、口が無い・帰せない断りは対応なし、時刻を作れば不一致。ほかの場面の断りは対応なし | `run_battery.py:correctness`・`run_battery.py:expects_refusal`・`run_battery.py:graded_output`・`run_battery.py:_grade_unit_time` | 無い | `test_battery_r17_refusal.py:test_grades_on_every_cell_of_the_grid`(状態 × 断りの記録の有無と帰属 × 期待の種類(断り / 値の単位の場面 / ほかの場面)× ok の値の型 の全格子を、規則 5 と指摘の文から書いた神託と照らす)、同 `test_every_scene_has_a_behavior_graded_as_its_answer`(全場面について、正解と一致になる振る舞いが採点の道にあることを示す) | 同 `test_mutants_of_the_grade_are_caught`(断りの記録があれば全部一致にする / 期待を見ない / 帰属を見ない / 断りを不一致にする / ok でも断りの印で一致にする) |
| 18. 断りの採点を述べる文(場面の注・導き方・採点の文・定義の正しさの行・docstring)が機械の採点と同じ | `scenes.py:_UNIT_NOTE`・`_UNIT_GRADED`・`_NO_INT_TAIL`、`gen_definitions.py:render`(正しさの行) | 文そのものは手書き(散文。機械の判断の値を名指す定型の文だけを試験が照らす) | `test_battery_r17_refusal.py:test_texts_state_the_grade_the_machine_gives`(正解が「断る」の場面の DEFINITIONS.md の節が「断れば正解と一致」の定型の文を持ち、場面集の書くファイル(この回より前の ROOTCAUSE を除く)のどこにも「断れば「対応なし」」の古い文が NO_INT の場面について残らない) | 同 `test_a_stale_refusal_text_is_caught`(古い文を 1 つ戻すと落ちる) |

族の番号は ROOTCAUSE_r16-1.md §4 の番号に続けた。族 15・17 は機械の関数を持つ。族 16 は場面の正解そのもの(手計算)で、機械は照らす側だけにある。族 18 は文で、機械は定型の文の有無だけを照らす。

## 5. リードに聞くこと

### 5.1 リードの答えの内容を変えた点(返り値の `lead_answer_changes` と同じ文)

1. **「断る」を正解に入れる場面の範囲**: リードの答え(VERDICTS run11 item0、i0-r15-05 への事前の答え)は「float が正確に持たない値では「断る」も正解に入れる(黙って丸めた値は不一致)」と float の場面を名指す。この回は、ナノ秒より細かい桁を持つ十進の文字列の 3 場面(秒・ミリ秒・マイクロ秒の `text-subns`)にも同じく「断る」を正解とした(float の 2 場面 `s-float-subns`・`ms-float-subns` と合わせて 5 場面)。理由: 3 場面とも、入力が持つ値 × 倍率 がナノ秒の整数にならず、正解の int64 ナノ秒が無い理由が float の 2 場面と同じ。批評家 i0-r16-04 の向きも「前者を NO_INT の場面の正解と一致に数える」で 5 場面を名指す。また、この 5 場面では正解の整数が無いので、「断る」が唯一の正解になる(「も」の片方の整数は無い)。float が持つ値がナノ秒で割り切れる場面(`float-held` の 3 場面。マイクロ秒の場面は書いた十進 …456.789 を float が持てないが、入力の物 1704067200123456.75 そのものは正確に持つ)は、正解は整数 1 つのままで、断りは「対応なし」とした。

### 5.2 聞くこと(この回に決めずに残した物と、決めた物のうちリードが違うと言えば戻す物)

1. **F3(P0-2 の全場面で入口の基準を揃える)をこの回は当てていない**: リードの答え F3「次の場面集の直しで、対象ごとに P0-2 の全場面(ISO・int・単位)で同じ入口の基準(公開のデータの入口 → 無ければ公開の変換の関数)を当て、対象ごとの入口を materials に記録する」は、同じ段落で「次の起動の lead_notes に写す」とされ、この起動の lead_notes(9 回目の戻しの注記)には無い。当てると道具ごとに次の分岐が出て、どれも起動文と指摘の文に無い判断になる(CLAUDE.md §0.1「作業中に、原文に無い判断が必要になったら、そこで止めて追加で擦り合わせる」): (a) 「無ければ」を単位ごとに読むか(単位 × 型ごとに読むか)。例: freqtrade のミリ秒はデータの入口 `ohlcv_to_dataframe`(整数。時間足で切り下げる)と変換の関数 `dt_from_ts`(整数・float)があり、単位ごとなら float も前者に渡す / (b) データの入口に渡せる型をどう決めるか(文字の表(CSV)は 3 つの型を文字に書いて渡せるが、Parquet・JSON は型を持つ)。例: pyalgotrade の秒はデータの入口 `CSVTradeFeed`(欄を `int()` で読む)があり、揃えると整数・float もこちらに文字で渡すことになり、`s-float-subns` は変換の関数で黙って丸めた「不一致」から、データの入口の断り(この回の採点で「正解と一致」)に変わる / (c) 「int」を事象の場面(`p2-event-time-exact`・`p2-one-ns-apart`)と読むなら、事象を渡す道(P0-1・P0-3 と共有の、対象の事象の型で渡す道)を P0-2 だけ別のデータの入口に替えるか / (d) barter の秒・ミリ秒は今は変換の関数(`barter_integration::serde::de` の関数)で、道具の取引所の文の型(データの入口)に替えるには Rust の driver を作り直す。この回の採点の直しで、正解が「断る」の場面の調査結果の側の最良は入口の選び方に依るようになった(上の pyalgotrade の例)。当てるなら (a)〜(d) の答えがほしい。
2. **F4(記録の写しを scratchpad の外に置く)は当てた**: F4 も「次の起動の lead_notes に規則として書く」とされたが、分岐が無く、この回の主張(直す前に落ちた試験・走らせ直し・比較)を後から照らせるようにするだけなので当てた。置き場所は F4 の逐語どおり `docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/battery/materials/r17-1/` で、`tests/bt/battery/` の外になる(§8 に理由を書く)。起動文の「一時ファイルとログは … scratchpad/bt の下に」は一時の物に当て、写しだけを置いた。違うと言えば消す。
3. **断りを正解と数える射程**: 正解が「断る」の場面では、対象の入口が場面の入力で呼ばれて例外を出せば、何を理由に断ったかは問わない(例: 入口がナノ秒より細かい桁を見て断ったのか、十進の小数を全部断るのか)。同じ単位・同じ型で正解の整数がある対の場面(`text`・`float-held`)が、その入口が値を読めるかを別に示す(全部を断る入口はそちらで「対応なし」)。例外の理由(文)で分けるのは文の読みになり、指摘の「文の読みでなく機械の欄で」に反するので、しなかった。
4. **翻訳した道具の断り**: Rust・Go などの道具の断りは Python のトレースバックに道具の枠が出ないので、driver が印した道具の `Err` の文を adapter が `CompiledRefusal` で運び、runner はそれを入口の名(対象の名前の頭)と合わせて帰す。driver のコードが本当に道具の断りを印したかは批評家が読む(§4 の族 15 の (b))。
