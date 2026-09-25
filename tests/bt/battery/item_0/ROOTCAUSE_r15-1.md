# 場面集への指摘の根本原因と主張の表(項目 0、第 r15-1 回の直し、場面係、2026-09-25)

合意した完了の形(オーナー逐語、L-405): 「**すべてが調査結果以上の信頼性と再現性に優れたものにすること。**」

この回の場面集への指摘は [直す] 1 件(i0-r14-06、repeat_of i0-r11-02)。起動文の逐語「直しの前に … ROOTCAUSE_r15-1.md に、この直しが触る主張の族ごとに 4 列の表を書く」(L-443)に従い、§1〜§5 を直す前に書き、§6 以降を直したあとに書いた。`<S>` = `/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/r15-1/`(この回の出力の置き場所。ここでは path と項の見出しで指す)。

## 0. 対応表(CLAUDE.md §0.1。右は起動文・指摘・リードの答えの逐語)

| やること | 該当語(逐語) |
|---|---|
| 直しの前に根本原因と主張の表をこのファイルに書く | 起動文「直しの前に /home/user/trade/tests/bt/battery/item_0/ROOTCAUSE_r15-1.md に、この直しが触る主張の族ごとに 4 列の表を書く」 |
| 散文の定義を書かない | 起動文「散文の定義は書かない(定義の段は無い)」 |
| F の範囲で「固定した測り方の外」と「測ったが升目の型を入力が決めない」を分ける形があるかを確かめ、無い部分はリードに聞く | 指摘 i0-r14-06「場面係は F の範囲で「固定した測り方の外」と「測ったが升目の型を入力が決めない」を分ける形があるかを確かめ、無ければリードに聞く」 |
| 同じ種類の欠陥を場面集の全体で探して直す | 起動文「指摘の文言だけに合わせる直しをしない: 同じ種類の欠陥を場面集の全体(全観点・全場面・検討表の全行)で探して直す」 |
| 族 5 の格子に gobacktest の trade → tick の作り替えを 1 ケースとして入れ、実測を書く | リードの答え(`docs/AUDITOR/VERDICTS/2026-09-23_backtest_env_run11_item0.md`、br13-1-3)「次の場面集の直しで、gobacktest の trade → tick の作り替えを族 5 の格子の 1 ケースとして試験に入れる(`types_in` がこの経路を「代えた型」として除外していることの実測を ROOTCAUSE に書く)」 |
| 升目の表の注記に、`requests` を記録しない相手の adapter と設定つき対象の数を書く | 同じ記録、br13-1-2「升目の表の注記に「相手の adapter 37・設定つき対象 41 は `requests` の記録なし = 『入った』と数えない」を数とともに書き」 |
| 注文の 3 つの通知のどれを測るかを機械で閉じる案を試し、できなければ理由を書く | 同じ記録、br13-1-1「機械で閉じる案(…)は次の場面集の直しの周に場面係が試し、できなければ理由を ROOTCAUSE に書く」 |
| リードの答えを変えるなら「リードに聞くこと」と `lead_answer_changes` に書く | 起動文「変えた点と理由を ROOTCAUSE_r15-1.md の節「リードに聞くこと」に書き、同じ文を lead_answer_changes に返す(無ければ空の配列)」 |
| 実装(`src/bot/bt/`)と作業者の試験(`tests/bt/item_0/`)に触れない | 起動文「実装(src/bot/bt/ の下)と作業者の試験(tests/bt/item_0/)には触れない」 |
| 直した規則ごとに全格子の敵対者の試験を先に書き、列に入れなかった物を試験のファイルに書く | 起動文「(6) 直した規則ごとに、その規則の入力の空間を全格子で列べる敵対者の試験 … を先に書き、規則を直したあと通す。列に入れなかったものを試験のファイルに書く」 |
| 検討表を検査器で誤り 0 件にする | 起動文「python3 scripts/check_bt_considered.py … --write を走らせて誤り 0 件にし」 |
| 返す前に `git diff --name-only HEAD` の出力を末尾に貼る | 起動文「返す前に「git diff --name-only HEAD」を走らせ、その出力を rootcause のファイルの末尾に貼る」 |

br13-1-1〜3 のリードの答えは、記録の見出しに「次の起動の lead_notes に写す」とあり、この起動の起動文には入っていない。3 つとも「次の場面集の直し」を名指し、i0-r14-06 と同じ族(i0-r11-02)の主張なので、この回に扱った(扱い方は §6.4)。

## 1. 指摘の一覧

| id | 格 | 相手 | repeat_of | この回で扱う物 |
|---|---|---|---|---|
| i0-r14-06 | [直す] | 場面集 | i0-r11-02 | 升目の表の P0-2 が「場面にした 0 / 測っていない(固定した測り方の外) 160」で、P0-2 を測る 4 場面がどこにも現れない |

## 2. なぜ起きたか(根本原因)

- **根 1(表が場面から升目への写しの像だけを出す)**: 升目の表は観点の範囲を升目だけで表し、場面は升目に当たるときだけ表に現れる。F は升目に当たる条件を「型が入力から機械で出る」に限ったので、事象を持たない場面(p2-iso-utc・p2-iso-offset)と、事象の型を入力が決めない場面(p2-event-time-exact・p2-one-ns-apart)は、どの升目にも当たらず表から消えた。表が持つのは「升目ごとに当たった場面」だけで、「観点を測る場面のうち升目に当たらなかった物」を出す機械が無い。
- **根 2(第 r13-1 回に知っていて表の上で直さなかった)**: 第 r13-1 回の場面係は P0-2 が 12 → 0 になることを実測し、「F の文のとおり」と ROOTCAUSE_r13-1.md §6.1 と §7 の表に書いた。その 0 が読み手(オーナーへ渡る「測っていない範囲の記録」)に「P0-2 は 1 つも測っていない」と読まれることを、表の上で直さなかった。第 r13-1 回の根 3(知っていた幅を直さずに文で説明した)と同じ形である。
- **根 3(試験が場面の側から表を照らさなかった)**: 升目の表の試験(`test_battery_item0.py:test_grid_table_lists_every_cell_of_every_viewpoint_once` ほか)は、升目ごとの判断を神託と照らすだけで、「観点の場面の全部が、表の升目か別の一覧のどちらかに現れる」を照らす試験が無かった。P0-2 の 4 場面・P0-6 の p6-place-then-cancel・P0-7 の p7-account-swap の 6 場面が表から消えても落ちる試験が無い。
- **根 4(判断の第 2 の値の名が F の意味より強い)**: 判断の第 2 の値「測っていない(固定した測り方の外)」の名は LEAD_DESIGN.md §8.2 の 1 の物で、F の下での意味は「宣言と入力から出る升目に当たる場面が無い」である。P0-2 の (約定〜清算, 戦略の呼び出しに届く物, int64 ナノ秒) は、p2-event-time-exact・p2-one-ns-apart が対象の選ぶ 1 型で測る。その升目に「固定した測り方の外」と書くのは、F の意味より強い。値は F と §8.2 の 1 が 2 値と決めているので、升目ごとに第 3 の値を置くことも値の名を替えることもリードの答えを変える(§5)。

同じ種類の欠陥を場面集の全体で探した方法: 全 32 場面について、入力の事象の数・型の欄の有る事象と無い事象の数・欄 `requests`・`input_types`・宣言の数・`covers_of` の数を機械で出した(`<S>item0_r15-1_scenekeeper_survey.txt`、打った道具は同じ置き場所の `item0_r15-1_scenekeeper_survey.py`)。`covers_of` が空の場面は 6 つ: P0-2 の 4 場面(事象を持たない 2 / 事象の型を入力が決めない 2)、P0-6 の p6-place-then-cancel、P0-7 の p7-account-swap(どちらも入力から型は出るが、宣言した升目が無い = 読む物か見る道が升目の軸に無い。第 r13-1 回の §6.2 で宣言を外した物)。升目に当たりながら型の欄の無い事象を含む場面は 0。検討表の行は升目の表に拠らないので、この族の欠陥は無い(§6.3 で検査器を回す)。

## 3. どの作りを変えるか

1. `scenes.py`: 場面の入力の事象(`type_plan` の場面は全 6 型を持つ対象のために作る入力)を列べる関数 `input_events` を置き、`input_types` はそれを使う(同じ事象の集まりを 2 か所で数えない)。
2. `grid_c.py`: 関数 `unplaced` を足す。観点ごとに、升目に当たらない場面(`covers_of` が空)と、升目に当たるが型の欄の無い事象を含む場面を、入力から機械で区分する: 事象を持たない / 事象の型を入力が決めない / 入力から型は出るが宣言した升目が無い / 升目に当たるが型の欄の無い事象を含む。升目の判断は変えない(F の 2 値のまま)。
3. `gen_definitions.py`: 観点ごとの見出しに「升目に当たらない場面 N」を足し、見出しの下に `unplaced` の一覧(場面 id・場面の種類・区分)を出す。節の始めの文に一覧の意味を 1 文足す。
4. `grid_c.py`: 関数 `request_recording` を足す(br13-1-2)。`run_battery.py` の対象の表と各 adapter のファイルの構文木から、`records_requests = True` を持つ adapter と持たない adapter、その設定つき対象の数を出す。`gen_definitions.py` が升目の表の注記に出す。
5. 試験: 直す前に `test_battery_r15_unplaced.py` を書く(§4 の (c)・(d))。`test_battery_r13_claims.py` の族 5 の格子に、対象自身の形の型(`tick`)が届いた場合を足す(br13-1-3)。
6. DEFINITIONS.md を `gen_definitions.py` から作り直し、行と語の判断(`line_judgments.tsv`・`term_judgments.tsv`)を足す。

## 4. 主張の表(この直しが触る主張の族ごと。直す前に書いた)

| 主張の族 | (a) 導く関数 | (b) 手書きが残る部分と、機械で導けない理由 | (c) 手書きの主張が 1 つでも残っていれば落ちる試験 | (d) 主張を作る機械への mutant の試験 |
|---|---|---|---|---|
| 8. 観点ごとの「升目に当たらない場面」とその区分(事象を持たない / 事象の型を入力が決めない / 入力から型は出るが宣言した升目が無い / 升目に当たるが型の欄の無い事象を含む) | `scenes.py:input_events` → `scenes.py:input_types`・`scenes.py:covers_of` → `grid_c.py:unplaced` → `gen_definitions.py:grid_section` | 区分そのものには無い。3 つ目の区分(宣言した升目が無い)は宣言 `COVERS` が空であることから出るので、宣言の手書き(族 1 の (b))に拠る。宣言が空である理由(読む物・見る道が升目の軸に無い)は場面の測る物の読みで、批評家が読む(LEAD_DESIGN.md §8.5 の 24)。一覧は場面 id・場面の種類・区分だけを出し、場面の中身は書き写さない | `test_battery_r15_unplaced.py:test_unplaced_follows_the_rule_on_every_copy`(全場面 × 入力の写しの全格子で、規則の文から書いた神託と照らす)、同 `test_every_scene_is_in_the_table_or_in_the_list`(場面ごとに、升目の表の場面の欄か一覧のどちらかにちょうど 1 回現れる)、同 `test_the_definitions_show_the_list_the_rule_gives`(DEFINITIONS.md の観点の節を読み、見出しの数と一覧の行を神託と照らす) | `test_battery_r15_unplaced.py:test_mutants_of_unplaced_are_caught`(`unplaced` に: 型の欄の無い事象を型の有る事象と数える / 事象を持たない場面を落とす / 升目に当たる場面も列べる / 区分を取り違える / 型の欄の無い事象を含む場面を落とす、`input_events` に: `streams` を読まない / `type_plan` を読まない、`grid_section` に: 一覧を出さない) |
| 1'. 観点ごとの見出しの数(升目の数・「場面にした」の数・「測っていない(固定した測り方の外)」の数・升目に当たらない場面の数) | `grid_c.py:table`・`grid_c.py:unplaced` → `gen_definitions.py:grid_section` | 無い | 族 8 の `test_the_definitions_show_the_list_the_rule_gives`(見出しの 4 つの数を神託から数え直す)、既存の `test_battery_item0.py:test_definitions_in_sync_with_scenes` | 族 8 の mutant(見出しの数が神託と違えば落ちる) |
| 5'. 記録 `types_in` は、対象自身の形の型(場面の型でない `tick` など)に作り替えて戦略に届いた型を、入ったと数えない(br13-1-3) | `run_battery.py:records_of`(戦略に届いた列を持つ場面は、渡した型のうち届いた型だけ) | 無い(対象自身の形の名は届いた列の値そのもの) | `test_battery_r13_claims.py:test_records_of_on_every_case`(届いた列の値に `["tick"]`・`["tick", "bar"]` を足した格子) | 既存の `test_battery_r13_claim_mutants.py:test_mutants_of_the_records_machine_are_caught`(同じ格子を使うので、足した値も mutant に当たる)。足した値だけで捕まる mutant(届いた列の対象自身の形の型を、渡した約定と数える)を同じファイルに足す |
| 9. `requests` を記録する adapter と記録しない adapter、その設定つき対象の数(br13-1-2) | `grid_c.py:request_recording`(`run_battery.py` の `OPPONENTS`・`_repro_targets`・`configured_targets` と adapter のファイルの構文木)→ `gen_definitions.py:grid_section` | adapter の `records_requests = True` は adapter の申告(adapter の戦略が `request` を呼ぶこと)。申告どおりに呼ぶかは、新実装と当方の現状では既存の試験(`test_battery_r13_claims.py:test_the_requests_field_is_what_the_reference_strategy_asks` ほか)が照らし、相手の adapter は申告しない側にしか居ない | `test_battery_r15_unplaced.py:test_request_recording_counts_are_the_adapters`(adapter のファイルの文字を読む独立の神託で数え直し、DEFINITIONS.md の文と照らす) | `test_battery_r15_unplaced.py:test_mutants_of_request_recording_are_caught`(全部を記録すると数える / 設定つき対象でなく adapter の数を出す / 再現の対象を落とす) |
| 3. 注文の受付・拒否・約定の 3 つのうちどれを場面が測るか(br13-1-1) | 無い(第 r13-1 回のまま) | 宣言の通知の種類。機械で閉じる案を試した結果と、閉じない理由は §6.4 | 第 r13-1 回のまま(`test_battery_r13_covers_of.py:test_swapping_one_order_notice_for_another_is_left_to_the_declaration` = 残っていることの試験) | 無い(機械が無い) |

族の番号は ROOTCAUSE_r13-1.md §4 の番号に続けた(1'・5' はその族の主張の、この回で足す部分)。どれも比較の表のセル(正しさ・再現)と場面の正解を変えない。

## 5. リードに聞くこと

### 5.1 正の定義 F とリードの答えの内容を変えた点(返り値の `lead_answer_changes` と同じ文)

無い。升目の判断は F と LEAD_DESIGN.md §8.2 の 1 のとおり 2 値のままで、この回に足した一覧(§3 の 2)は升目の判断を変えない。

### 5.2 聞くこと(F の範囲で分けられなかった部分)

1. **升目ごとに「固定した測り方の外」と「測ったが升目の型を入力が決めない」を分けるか**: F の範囲で分けられたのは観点の単位(観点ごとの「升目に当たらない場面」の一覧)までで、升目の単位では分けられなかった。理由: p2-event-time-exact・p2-one-ns-apart が測る升目は (対象が選ぶ 1 型, 戦略の呼び出しに届く物, int64 ナノ秒) で、どの型の升目かは対象が選ぶ(入力の外)。その場面を型の行に当てるには、「型の欄の無い事象はどの型の行に当たるか」を決めることになり、F の「型 e が s の入力から機械で出る」「判断は機械で 2 値」に反する。p2-iso-utc・p2-iso-offset は事象を持たず、見る道(対象のデータの入口に渡した文字列を対象が変換した値)も軸の 4 つの道のどれでもない。升目の単位で分けるには、(i) 第 2 の値の名を F の意味(「升目に当たる場面が無い」など)に替える、(ii) 第 3 の値(例:「型を入力が決めない場面がこの (見る道, 追加の軸) を測る」)を置き、型の欄の無い事象を 6 つの市場の型の行に当てる、(iii) 升目の表は替えず、観点ごとの一覧で足りるとする、のどれかをリードが決める必要がある。この回は (iii) の形で直し、(i)(ii) は作っていない。
2. **P0-6・P0-7 の同じ形**: p6-place-then-cancel(未決の注文の数を読む)と p7-account-swap(差し込んだ口座自身の記録を読む)は、入力から型は出るが、読む物か見る道が升目の軸に無いので升目に当たらない。ROOTCAUSE_r13-1.md §8.2 の 6 で上げた問い(要件の文を読む判断 `grid_c_judgments.tsv` をリードが見直すか)は、記録 run11 のリードの答えに答えが無い。この回は一覧に出す形で扱い、軸は替えていない。

## 6. 直した結果(指摘ごとの根拠。§1〜§5 を書いたあとに直した)

版: HEAD 563661d の上の作業木。場面の定義(32 場面の全部の欄)と `input_types`・`covers_of` の値は HEAD と同じ(`<S>item0_r15-1_scenekeeper_same_scenes.txt`: 「identical: True」「input_types / covers_of differing scenes: 0」。`run_battery.py`・`adapters/`・`opponents/` は変えていない)。よって比較の表のセル・場面の正解・runner の記録は変わらない。

### 6.1 i0-r14-06(主張の族 8・1')

- `scenes.py:input_events`(入力の事象の列べ。`input_types` はこれを使う)、`grid_c.py:unplaced`(升目に当たらない場面と区分)、`gen_definitions.py:grid_section`(見出しの数と一覧)を足した。
- 観点ごとの見出し(HEAD → この回。`<S>item0_r15-1_scenekeeper_headings.txt`): 升目の判断の数は 7 観点とも変わらず、見出しに「升目に当たらない場面」の数が付いた。P0-2 は「場面にした 0 / 測っていない(固定した測り方の外) 160 / 升目に当たらない場面 4」で、見出しの下に p2-iso-utc・p2-iso-offset(事象を持たない)と p2-event-time-exact・p2-one-ns-apart(事象の型を入力が決めない)が出る。同じ種類の欠陥の P0-6 の p6-place-then-cancel と P0-7 の p7-account-swap(入力から型は出るが、その型の升目を宣言していない)も出る。ほかの 4 観点は「無し」。
- 節の始めの文に、一覧の意味(その観点を測る場面だが升目に当たらない、升目の判断は変えない)を足した。
- 升目の単位で分けること(根 4)は F の範囲ではできず、§5.2 の 1 に上げた。

### 6.2 br13-1-2(主張の族 9)

- `grid_c.py:request_recording` と `request_recording_sentence` を足し、升目の表の注記(節の始め)に出した。出力: 「新実装・当方の現状・試金石: 記録する 3(設定つき対象 3)/ 記録しない 0(設定つき対象 0)。相手: 記録する 0(設定つき対象 0)/ 記録しない 37(設定つき対象 41)。再現: 記録する 0(設定つき対象 0)/ 記録しない 1(設定つき対象 13)」。リードの答えの数(相手の adapter 37・設定つき対象 41)と同じ。

### 6.3 br13-1-3(主張の族 5')

- `test_battery_r13_claims.py:_cases` の届いた列の値に `["tick"]`・`["tick", "bar"]` を足した(格子 4 × 3 × 4 × … → 4 × 3 × 6 × …)。`run_battery.py:records_of` は、戦略に届いた列を持つ場面では渡した型のうち届いた型だけを `types_in` にするので、`tick` だけが届けば約定は入らず、`types_added` に `tick` が出る(神託と一致。変える所は無かった)。
- mutant: `test_battery_r13_claim_mutants.py` に「対象自身の形の型を渡した約定と数える」を足し、捕まるのが足した `tick` の場合だけであることを `test_a_record_that_takes_a_targets_own_form_for_the_trade_is_caught_only_by_the_tick_cases` で示した。
- 実測: gobacktest の trade → tick の作り替えは `opponents/gobacktest_adapter.py` の 107 行(p1-typed-events)だけにある。`survey_results/opp_gobacktest.tsv` の p1-typed-events は `status_1 = not_supported`・`types_1 = null`・`types_in = []` で、この場面は型の組を設定つき対象の持つ型から決める場面であり、gobacktest の持つ型は足 1 種で最低の 2 種に足りないので、runner は adapter を呼んでいない(detail_1「設定つき対象の持つ型 ['bar'] は 1 種で、この場面の最低 2 種に足りない」)。よって実際の実行でこの作り替えの経路は走っておらず、`types_in` がこの経路を除くことは格子の場合で示した物で、実際の実行では確かめていない(未確認)。

### 6.4 br13-1-1(主張の族 3)を機械で閉じる案を試した結果

- 試したこと: F が読んでよい物(入力の事象の型の欄と欄 `requests`)だけの関数で、注文の 3 つの通知のどれを場面が測るかを場面ごとに違えて決められるかを調べた。`<S>item0_r15-1_scenekeeper_survey.txt` のとおり、p3-notice-accepted・p3-notice-rejected・p3-notice-filled の 3 場面は、入力の事象の型(約定)も欄 `requests`(`["place"]`)も同じである。F が読んでよい物が同じ 3 場面に、その物だけの関数が違う通知を返すことはできない。よって F の範囲では閉じない。
- 閉じるには、3 場面で違う物(欄 `account` の現金、`strategy` の文、正解の欄)を読むことになる。どの通知が起きるかは、頼みと市場と口座の帰結で、対象の規則(証拠金の検め・拒否の条件)にも依る。これを読むのは F が使わないとした「正解がその事象を名指すか」「対象の出力」に当たる。欄 `requests` に頼みの種類を細かく書く形(例: 拒否されるはずの発注)は、帰結を手で書いた欄を置くだけで、参照の戦略の頼みとの照合(`test_the_requests_field_is_what_the_reference_strategy_asks`)でも発注の頼みがあることしか照らせない。宣言を手書きの欄へ移すだけなので作らなかった。族 3 は第 r13-1 回のまま(宣言が上限、批評家が読む。リードの答え br13-1-1 のとおり通過の報告に「人の読みで残る点」として載る)。

### 6.5 試験・mutant・検討表

- 試験を先に書いた記録: `<S>item0_r15-1_scenekeeper_tests_first.txt`(直す前に `test_battery_r15_unplaced.py` を回し、収集の段で `scenes.input_events` が無くて落ちた)。
- 主張の表の試験: `test_battery_r15_unplaced.py` の全部(格子 = 全 32 場面 × 第 r13-1 回の入力の写し × 型の欄を 1 つ外す・事象でない物を足す写し、規則の文から書いた神託と照らす。区分 4 つと「列べない」「断る」の全部が格子に現れることも照らす)。mutant は `unplaced` に 5 種・`input_events` に 2 種・一覧を出さない 1 種・`request_recording` に 3 種で、どれも捕まる。結果は §6.6。
- 場面集の試金石: `<S>item0_r15-1_scenekeeper_checks.txt` の `mutant.py --check` →「changed scenes: ['p4-received-time']」「OK」。
- 検討表: 同じ出力の `check_bt_considered.py … --write` →「OK 誤り 0 件」(検討表は変わっていない)。
- DEFINITIONS.md: 同じ出力の `gen_definitions.py --check` →「OK」。

### 6.6 試験の結果

(§7 を書いたあとに打った。出力は `<S>item0_r15-1_scenekeeper_pytest_after.txt` と `<S>pytest_item0_r15-1_scenekeeper.log`。末尾の行を下に写す。)

## 7. 提出前の吟味(委任文 §3「提出前の吟味」(1)〜(6))

読み直した物: 委任文(全 169 行)、固定した要件 REQUIREMENTS.md(§1・§2)、場面集の規則 1〜9、LEAD_DESIGN.md の §8.2・§8.5・§8.6・§9・§10・§11、記録 `docs/AUDITOR/VERDICTS/2026-09-23_backtest_env_run11_item0.md`(リードの答え br13-1-1〜3)、指摘 i0-r14-06 の逐語と第 14 周の CRITIC.md の場面集の節、ROOTCAUSE_r13-1.md の全部。

| 非常に厳しい批評家なら [止める]・[直す] にする候補 | 何をしたか |
|---|---|
| i0-r14-06: P0-2 を測る 4 場面が表から消え、P0-2 が 1 つも測られていないと読める | 観点ごとに升目に当たらない場面を機械で列べ、見出しに数を出した(§6.1)。場面ごとに「表の升目か一覧のどちらかにちょうど 1 回」を試験にした(`test_every_scene_is_in_the_table_or_in_the_list`) |
| 同じ族の別の形 1: 升目の値「測っていない(固定した測り方の外)」が F の意味より強いまま | F と §8.2 の 1 の 2 値の範囲では替えられない。§5.2 の 1 に案 3 つを付けて上げた。この回は升目の値を替えていない |
| 同じ族の別の形 2: P0-6・P0-7 の場面(読む物・見る道が軸に無い)も表から消えている | 同じ機械の一覧に出る(§6.1)。軸を見直すかは §5.2 の 2 に上げた |
| 一覧が手書きになる / 区分を場面係が選ぶ | 区分は入力と宣言から機械で出し、格子で神託と照らし、mutant 8 種を捕まえる。一覧は場面の中身を書き写さない(場面 id・種類・区分だけ) |
| 格子が実装の場合分けから作られている | 入力の写しは第 r13-1 回の格子(入力の空間から作った物)に、型の欄を 1 つ外す・事象でない物を足す写しを足した。区分 4 つ・列べない・断る の全部が格子に現れることを試験にした(`test_the_grid_reaches_every_class`)。列に入れなかった物は試験のファイルの冒頭に書いた |
| 一覧が升目の判断を変えている | 升目の判断の機械(`grid_c.verdict`・`table`)は変えていない。見出しの 2 つの数は HEAD と同じ(§6.1) |
| 場面の定義・正解・比較の表のセルが変わる | 変えていない(§6 の冒頭、32 場面の全部の欄が HEAD と同じ) |
| br13-1-2 の数が手で書かれている | adapter のファイルから機械で数え、別の読み方(正規表現)の神託で照らし、mutant 3 種を捕まえる |
| br13-1-3 の実測が無い | 格子に入れ、mutant が足した場合だけで捕まることを示した。実際の実行ではこの経路が走っていないこと(runner が adapter を呼ばない)を記録から示し、未確認と書いた(§6.3) |
| br13-1-1 を試さずに残した | F が読んでよい物が 3 場面で同じことを記録で示し、閉じない理由を書いた(§6.4) |
| 実装(`src/bot/bt/`)と作業者の試験(`tests/bt/item_0/`)に触れる | 触れていない(§8 の差分) |
| 既存の試験を弱めた・消した | 消していない。`test_battery_r13_claims.py` は格子を広げ(数の assert を 4 → 6 に)、`test_battery_r13_claim_mutants.py` は mutant を足しただけ。升目の節に「未決」の語を入れないために、一覧に場面の「何を測るか」を写す最初の版をやめた(既存の試験 `test_grid_table_lists_every_cell_of_every_viewpoint_once` は変えていない) |
| 自分の作業の採点を書く(O-10) | この表は候補と、したことだけを書き、通るかの判定は書いていない |
