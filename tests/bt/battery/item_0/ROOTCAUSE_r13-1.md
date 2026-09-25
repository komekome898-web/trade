# 場面集への指摘の根本原因と主張の表(項目 0、第 r13-1 回の直し、場面係、2026-09-25)

合意した完了の形(オーナー逐語、L-405): 「**すべてが調査結果以上の信頼性と再現性に優れたものにすること。**」

この回の場面集への指摘は [止める] 1 件(i0-r11-02)。起動文の逐語「直しの前に ROOTCAUSE_r13-1.md に根本原因と主張の表(導く関数 / 手書きが残る部分 / 手書きが残れば落ちる試験 / mutant)を書き、そのまま直す」(L-443。定義の段は廃止)に従い、§1〜§5 を直す前に書き、§6 以降を直したあとに書いた。前の起動(10 回目)の場面係はこの回の定義の段を 2 版書き(第 2 版に監査役(定義) r13-1-2 が [止める] 0・[聞く] 2)、直しの途中で L-443 により止まった。前の版の全文は `<S>item0_r13-1_scenekeeper_fix_prev_def2_ROOTCAUSE.md` に写し、作業木の途中の変更はコミット dc9e04a に在る。`<S>` = `/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/r13-1e/`。この回の出力は `<S>` に置き、ここでは path と項の見出しで指す。

## 0. 対応表(CLAUDE.md §0.1。右は起動文の逐語)

| やること | 起動文の該当語(逐語) |
|---|---|
| 直しの前に根本原因と主張の表をこのファイルに書く | 「直しの前に … ROOTCAUSE_r13-1.md に、この直しが触る主張の族ごとに 4 列の表を書く」 |
| 散文の定義を新しく書かない | 「散文の定義は書かない(定義の段は無い)」 |
| F を規則として直す。変えた点は §8 と `lead_answer_changes` に書く | 「F の内容を変える必要があると読むなら、変えた点と理由を ROOTCAUSE_r13-1.md の節「リードに聞くこと」に書き、同じ文を返り値の lead_answer_changes に返す」 |
| §9.2 の 33・34・36 の直し、ROOTCAUSE_r12-1.md の見出し、批評家の試験 13 件を変えずに通す | 「直しは §9.2 の 33・34・36 のとおり。ROOTCAUSE_r12-1.md は「採らなかった案(第 12 周の定義 3 版)」と見出しを付けて残す。批評家の試験 … (13 件)を変えずに通す。」 |
| 同じ種類の欠陥を場面集の全体で探して直す | 「指摘の文言だけに合わせる直しをしない: 同じ種類の欠陥を場面集の全体(全観点・全場面・検討表の全行)で探して直す」 |
| 候補 35 を同じ 3 手で走らせ、検討表の行を直す | 「候補 35 はリードが走らせた(§9.2 の 36)。場面係が同じ 3 手で走らせ、検討表の行を直す。」 |
| 実装(`src/bot/bt/`)と作業者の試験(`tests/bt/item_0/`)に触れない | 「実装(src/bot/bt/ の下)と作業者の試験(tests/bt/item_0/)には触れない」 |
| 直した規則ごとに全格子の敵対者の試験を先に書き、列に入れなかった物を試験のファイルに書く | 「(6) 直した規則ごとに、その規則の入力の空間を全格子で列べる敵対者の試験 … を先に書き、規則を直したあと通す。列に入れなかったものを試験のファイルに書く」 |
| 返す前に `git diff --name-only HEAD` の出力を末尾に貼る | 「返す前に「git diff --name-only HEAD」を走らせ、その出力を rootcause のファイルの末尾に貼る」 |

## 1. 指摘の一覧

| id | 格 | 相手 | repeat_of | この回で扱う物 |
|---|---|---|---|---|
| i0-r11-02 | [止める] | 場面集 | null | 升目の表の「場面にした」が、手で書いた宣言 `covers` から出て、場面の入力より広い |
| i0-r11-02 の「人の読みで残る点」 | (指摘の文の中) | 場面集 | — | p6-place-then-cancel の宣言(注文の受付の通知, 読む物)は、場面が読む物(未決の注文の数)と合わない |
| 監査役(定義) r13-1-2 の [聞く] 1 | [聞く] | 定義(前の起動) | AUD-1 | 注文の 3 つの通知のどれを数えるかを宣言が決めるまま直しに進んでよいか(§8 の 4 に答える) |
| 監査役(定義) r13-1-2 の [聞く] 2 | [聞く] | 定義(前の起動) | — | p6-place-then-cancel の宣言を変えない根拠(§2 の根 13 と §5 の 4 で答え、宣言を直す) |

## 2. なぜ起きたか(根本原因)

- **根 1(「走らせうる」を「測った」として宣言した)**: `scenes.py` の `COVERS` の注(第 r11-1 回の版)は「型を対象に任せる場面は、走らせうる市場の事象の型の全部を覆う」と決めた。「どの型でも走る」は「その型が入力にある」ではない。
- **根 2(同じ事実の元を 2 つ持ち、照らす機械が無かった)**: 場面が何を入力に持つかの元は `scenes.py` の入力で、`covers` はそれと別に手で書いた一覧だった。第 r11-1 回に升目の判断を `covers` だけから決める形にしたとき、`covers` を入力と照らす機械も試験も置かなかった。第 r11-1 回の試験は表を `covers` と照らすだけで、神託と実装の元が同じ `covers` だった。
- **根 3(知っていた幅を直さずに文で説明した)**: 第 r11-1 回の場面係は `covers` が場面の測る物より広いことを吟味の候補に挙げ(ROOTCAUSE_r11-1.md §7)、宣言の仕方の 1 文を足してリードに上げただけで、表の値は誤ったまま出た。
- **根 4(型と見る道の組を持つ物が宣言しか無い)**: 升目は (e, v, x) の 3 つ組で、入力は型の集まりだけを、(v, x) の宣言は見る道と追加の軸だけを持つ。F は e を入力から、(v, x) を宣言から別々に取るので、字のまま計算すると積になり、入力に 2 つ以上の型を持ち 2 つ以上の (v, x) を宣言した場面で、場面が組にしていない升目が「場面にした」になる(i0-r11-02 と同じ向き)。実測は前の起動の出力 `/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/item0_r13-1_scenekeeper_def1_measure.txt` の項「== F(発注→3 通知)」。この回の出力 `<S>item0_r13-1_scenekeeper_fix_product.txt` で今の場面集について計算し直す(§6)。
- **根 5(頼みを読む欄が無かった)**: F は時計・通知の升目を「入力の戦略の頼み」から出すが、頼みは `strategy` の文にしか無かった。文を語で探す読み方は言い換えで黙って外れる。前の起動の直しで入力に欄 `requests` を足したが、その欄が戦略の実際の頼みと合うかを照らす機械が無い(欄が根 2 と同じ「照らさない 2 つ目の元」になる)。
- **根 6(発注の頼みは 3 つの通知を一緒に出す)**: 注文の受付・拒否・約定のどれが起きるかは、頼みと市場と口座の帰結で、入力から機械で決めるには F が使わないとした物(対象の出力・記録・正解の名指し)を読むことになる。この 3 つの間の選びは宣言にしか無い。
- **根 7(記録の型の欄が adapter の申告に拠る)**: 前の起動の直しで足した runner の記録 `types_in`(§9.2 の 33)は、戦略に届いた列を持たない場面では「渡した入力の型から、adapter が共通の部品 `as_bar` で代えた型を除いた物」だった。`as_bar` を通さずに型を代える adapter のコード(例: `opponents/luczinsritter_adapter.py` の p4-received-time は約定を自分で足の行に作り替える)では、入らなかった型が「入った」と記録される。記録から出す注記(対象ごとの測っていない範囲)を狭く見せる向きで、i0-r11-02 と同じ向き。記録 `requests` も adapter が申告した物で、前の起動の版ではどの adapter も申告しない(`records_requests` が全部 False)ので、欄は全部 null だった。
- **根 8(注記の関数が無かった)**: §9.2 の 33 の「資料係の表の注記に、対象ごとの「場面にしたが、この対象には型が入らなかった升目」を機械で出す」の関数 `grid_c.not_entered` は、DEFINITIONS.md の申し送りと runner の注が名指すだけで、コードに無かった(`grep -n not_entered tests/bt/battery/item_0/*.py` → 注の 2 か所だけ)。
- **根 9(見る道の宣言を測る物と照らさなかった)**: p6-place-then-cancel の宣言(注文の受付の通知, 戦略が対象の公開の手段で読む物)は、場面の測る物(2 回目と 3 回目に読んだ未決の注文の数)と合わない。未決の注文の数は受付の通知の事象ではない。要件 P0-6 の測り方は「核がそれを注文の受付/拒否/約定の通知の事象として返すか」で、この場面の測る物はそれに当たらない。前の起動の定義は「批評家の読みに任せる」として宣言を変えなかったが、批評家は読んだうえで合わないと書いている(i0-r11-02 の「人の読みで残る点」)。
- **なぜ前の回の試験で見つけられなかったか**: 根 2 のとおり、試験の入力の空間を `covers` から作っていた。入力から型を独立に出す神託が無く、記録と欄についても、入力と独立に照らす神託が無かった。

## 3. 升目の規則の文(DEFINITIONS.md に `gen_definitions.py` の `R13_DEFINITION` から写す文)

この文は前の起動の定義の段の第 2 版の §3 で、監査役(定義) r13-1-2 が [止める] 0 で通した物である。この回に新しく書いた定義ではなく、機械(§4 の関数)が計算する物を DEFINITIONS.md の読み手に示す文として残す。F から変えた点は §8 の 1・2。

**升目を「場面にした」と数える物**: 升目 (e, v, x) を場面 s が「場面にした」と数えるのは、s がその升目 (e, v, x) を宣言し、かつ型 e が s の入力から機械で出るときだけである。宣言と入力の両方が要り、どちらか一方だけでは数えない(入力は s が宣言しない升目を足せない)。入力から機械で出る型は次の 2 つだけである。市場の事象の型(約定・板の写真・板の差分・足・資金調達・清算)は、scenes.py が s の入力に載せた事象(`events` と `streams` の中身)の型の欄そのもので、型の欄 1 つが型 1 つを出す(`type_plan` の場面は `for_target_types(s, TYPE_ORDER)` の入力の型の欄。批評家 i0-r11-02 の神託 `_kinds(scene)` と同じ計算。型の欄の無い事象と、事象を持たない場面からは型を出さず、adapter が代えた型は数えない)。市場の事象の型では入力が型そのものを決めるので、宣言は入力に無い型の升目を足せない。時計・注文の受付の通知・注文の拒否の通知・注文の約定の通知・取消の通知は、s の入力が欄として持つ戦略の頼みから出る: 時計の頼みは時計を、発注の頼みは注文の受付・拒否・約定の通知の 3 つを一緒に、取消の頼みは取消の通知を出す。取消の通知は要件 §1 の事象の型の外で、升目の表の事象の軸に入れず、`scenes.py` の `OUTSIDE_AXES` の区分の軸の外の升目として別に出す。入力の文(`strategy` の文など)を読んで頼みを決めない。発注の頼みについて入力が機械で決めるのは 3 つの通知が一緒に出ることまでで、3 つのうち s がどれを測るかは入力から機械では決まらない(決めるには、下で使わないとした対象の出力・runner の記録・「正解がその事象を名指すか」を読むことになる)。よって注文の 3 つの通知の升目では、機械が決めるのは「発注の頼みを持たない s の宣言は数えない」までで、3 つのどれを数えるかは s の宣言だけが決める。宣言の e が入力から出ない升目は数えず、そういう宣言があれば試験が落ちる(黙って捨てない)。adapter が書く値・対象の出力・runner が残す記録・「正解がその事象を名指すか」「その道を通さなければ正解にならないか」の意味の読みは使わない。判断は機械で 2 値。宣言した升目が s の測る物と合うか(注文の 3 つの通知のどれを数えるかの宣言を含む)と、s の入力がその道を実際に呼ぶかは批評家が読む(LEAD_DESIGN.md §8.5 の 24)。この定義は升目の表と `covers` だけに当て、場面の正解・採点・比較の表のセルを変えない。

## 4. 主張の表(この直しが触る主張の族ごと。直す前に書いた)

| 主張の族 | (a) 導く関数 | (b) 手書きが残る部分と、機械で導けない理由 | (c) 手書きの主張が 1 つでも残っていれば落ちる試験 | (d) 主張を作る機械への mutant の試験 |
|---|---|---|---|---|
| 1. 升目 (市場の事象の型, v, x) が「場面にした」 | `scenes.py:input_types`(`events`・`streams` の型の欄、`type_plan` の場面は `for_target_types(s, TYPE_ORDER)` の入力)→ `scenes.py:covers_of` → `grid_c.py:verdict`・`grid_c.py:table` → `gen_definitions.py:grid_section` | 宣言 `COVERS` の組(どの型をどの見る道・追加の軸で測るか)。入力は型だけを持ち、見る道を持たない。どの道で測るかは場面の測る物の読みで、F はそれを批評家に置く(根 4) | `tests/bt/critic/item_0/test_i0r11_covers_within_scene_input.py:test_a_scene_covers_only_market_types_its_input_runs`、`test_battery_r13_covers_of.py:test_every_scene_declares_only_cells_its_input_gives`、同 `test_covers_follow_the_definition_on_every_copy`(入力の写しの全格子) | `test_battery_r13_claim_mutants.py:test_mutants_of_the_market_type_machine_are_caught`(`input_types` に: 型の欄の無い事象を約定と数える / `type_plan` を無視する / 6 型を全部足す / `streams` を読まない、`covers_of` に: 宣言をそのまま返す、`grid_c.verdict` に: 宣言から数える、を当て、どれも (c) の神託で落ちることを見る) |
| 2. 升目 (時計・取消の通知, v, x) と、注文の通知の升目の「発注の頼みがある」 | `scenes.py:input_types`(欄 `requests` → `REQUEST_TYPES`)→ `scenes.py:covers_of` | 欄 `requests` の値。戦略は文で書かれ、文から頼みを決めるのは意味の読み(根 5)。ただし欄の値は、当方の参照の戦略(`adapters/new_impl.py` の各場面の戦略)が実際に出した頼みと機械で照らす | `test_battery_r13_claims.py:test_the_requests_field_is_what_the_reference_strategy_asks`(新実装の adapter で全場面を走らせ、記録した頼みの集まりが欄と等しい)、`test_battery_r13_covers_of.py:test_every_scene_declares_only_cells_its_input_gives` | `test_battery_r13_claim_mutants.py:test_mutants_of_the_request_machine_are_caught`(`input_types` に: 欄を読まない / 発注を時計と取り違える、欄の写しに: 取消を落とす・時計を足す、を当てて落ちることを見る) |
| 3. 注文の受付・拒否・約定の 3 つのうちどれを場面が測るか | 無い(機械は主張 2 の「発注の頼みがある」までを決める) | 宣言の通知の種類。3 つのどれが起きるかは頼みと市場と口座の帰結で、入力から決めるには F が使わないとした物を読む(根 6)。批評家が読む | 手書きが残るので、残れば落ちる試験は無い。宣言の通知を 3 つの中の別の通知に替えた写しを機械が落とさないことを `test_battery_r13_covers_of.py:test_swapping_one_order_notice_for_another_is_left_to_the_declaration` が示す(残っていることの試験) | 無い(機械が無い) |
| 4. 取消の通知の升目は事象の軸の外 | `grid_c.py:axes`(要件の文の判断から軸を作る)、`scenes.py:OUTSIDE_AXES`、`gen_definitions.py:grid_section` | `OUTSIDE_AXES` の理由の文(要件 §1 の通知は 3 つで取消の通知を名指さないこと)。要件の文を読む判断で、`grid_c_judgments.tsv` と同じく場面係の判断 | `test_battery_r13_covers_of.py:test_the_cancel_notice_stays_outside_the_event_axis` | `test_battery_r13_claim_mutants.py:test_a_mutant_that_puts_the_cancel_notice_on_the_event_axis_is_caught` |
| 5. 記録 `types_in`・`types_added`(対象に入った市場の事象の型)| `run_battery.py:records_of`(戦略に届いた列がある場面は届いた型、無い場面は渡した入力の型から `as_bar` などの共通の部品で代えた型を除き、設定つき対象の持つ型(p3 の採点、L-438 (2))に限る) | 戦略に届いた列を持たない場面で、adapter が型を代えたことは adapter のコードが共通の部品を通すことに拠る。対象ごとの API に渡した物を runner は見られない(根 7)。残る穴は「持つ型なのに共通の部品を通さず代える」形で、adapter のコードの形を検める試験で塞ぐ | `test_battery_r13_claims.py:test_records_types_in_within_the_input_handed`(`survey_results/` の全行)、同 `test_no_adapter_builds_a_substitute_event_outside_common`(adapter と相手のコードの全部を構文木で読み、場面の事象から型の欄を持つ辞書を作る所が共通の部品の外に在れば落ちる)、同 `test_records_of_on_every_case`(記録の関数の入力の全格子) | `test_battery_r13_claim_mutants.py:test_mutants_of_the_records_machine_are_caught`(`records_of` に: 代えた型を除かない / 持つ型に限らない / 届いた列を読まない、を当てる) |
| 6. 記録 `requests`(戦略が出した頼み) | `adapters/common.py:request`・`requests_taken` → `run_battery.py:records_of` | adapter の戦略が頼む所で `request` を呼ぶこと(adapter の申告)。対象ごとの API の呼び出しを runner は見られない。新実装と当方の現状の adapter だけが申告し、相手の adapter は null(§8 の 5 に上げる) | `test_battery_r13_claims.py:test_records_requests_within_the_field`(`survey_results/` と、新実装・当方の現状を走らせた記録で、記録 ⊆ 欄)、同 `test_the_requests_field_is_what_the_reference_strategy_asks` | `test_battery_r13_claim_mutants.py:test_mutants_of_the_records_machine_are_caught`(`records_of` に: 申告しない adapter の欄を [] にする、を当てる) |
| 7. 注記「場面にしたが、この対象には型が入らなかった升目」 | `grid_c.py:not_entered`(升目の表と記録から) | 無い | `test_battery_r13_claims.py:test_not_entered_on_every_case` | `test_battery_r13_claim_mutants.py:test_mutants_of_not_entered_are_caught` |

族 1〜4 は升目の表の主張、族 5〜7 は §9.2 の 33 の記録と注記の主張である。どれも比較の表のセル(正しさ・再現)を変えない。

## 5. どの作りを変えるか

1. `scenes.py`: `COVERS` を升目の宣言として残し、`covers_of` で入力から出る型の升目だけを数える(前の起動の直しのとおり)。p6-place-then-cancel の宣言を空にする(根 9)。ほかの全場面の宣言を、場面の測る物と入力に照らして読み直す(結果は §6)。
2. `grid_c.py`: `not_entered` を足す(根 8)。
3. `run_battery.py`: `records_of` で、戦略に届いた列を持たない場面の `types_in` を設定つき対象の持つ型に限る(根 7)。
4. adapter と相手のコード: 場面の事象の型を代える所を共通の部品(`adapters/common.py` の `as_bar` と新しい `substitute`)に寄せる(根 7)。新実装・当方の現状の adapter の戦略が頼む所で `request` を呼ぶ(根 5・根 7)。
5. 試験: §4 の (c)・(d) の試験を直す前に書く。敵対者の格子は前の起動の `test_battery_r13_covers_of.py`(族 1〜4)と、この回の `test_battery_r13_claims.py` の `test_records_of_on_every_case`・`test_not_entered_on_every_case`(族 5・7)。
6. DEFINITIONS.md(`gen_definitions.py` から作る)、`def_axes/jC.tsv`(正の定義 C の段落の切片の判断)、`line_judgments.tsv`・`term_judgments.tsv`(正の定義 B・D)を直す。
7. 全対象を走らせ直して `survey_results/` の記録の列を埋める。候補 35 を 3 手で走らせ、`RUNNABILITY.tsv`・検討表・adapter を直す。
8. `ROOTCAUSE_r12-1.md` に「採らなかった案(第 12 周の定義 3 版)」の見出しを付ける。
