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
| 監査役(定義) r13-1-2 の [聞く] 2 | [聞く] | 定義(前の起動) | — | p6-place-then-cancel の宣言を変えない根拠(§2 の根 9 と §6.2 で答え、宣言を直した) |

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

## 3. 第 r13-1 回の正の定義(DEFINITIONS.md に `gen_definitions.py` の `R13_DEFINITION` から写す文)

この文は前の起動の定義の段の第 2 版の §3 で、監査役(定義) r13-1-2 が [止める] 0 で通した物である。この回に新しく書いた定義ではなく、機械(§4 の関数)が計算する物を DEFINITIONS.md の読み手に示す文として残す。F から変えた点は §8 の 1・2。

**升目を「場面にした」と数える物**: 升目 (e, v, x) を場面 s が「場面にした」と数えるのは、s がその升目 (e, v, x) を宣言し、かつ型 e が s の入力から機械で出るときだけである。宣言と入力の両方が要り、どちらか一方だけでは数えない(入力は s が宣言しない升目を足せない)。入力から機械で出る型は次の 2 つだけである。市場の事象の型(約定・板の写真・板の差分・足・資金調達・清算)は、scenes.py が s の入力に載せた事象(`events` と `streams` の中身)の型の欄そのもので、型の欄 1 つが型 1 つを出す(`type_plan` の場面は `for_target_types(s, TYPE_ORDER)` の入力の型の欄。批評家 i0-r11-02 の神託 `_kinds(scene)` と同じ計算。型の欄の無い事象と、事象を持たない場面からは型を出さず、adapter が代えた型は数えない)。市場の事象の型では入力が型そのものを決めるので、宣言は入力に無い型の升目を足せない。時計・注文の受付の通知・注文の拒否の通知・注文の約定の通知・取消の通知は、s の入力が欄として持つ戦略の頼みから出る: 時計の頼みは時計を、発注の頼みは注文の受付・拒否・約定の通知の 3 つを一緒に、取消の頼みは取消の通知を出す。取消の通知は要件 §1 の事象の型の外で、升目の表の事象の軸に入れず、`scenes.py` の `OUTSIDE_AXES` の区分の軸の外の升目として別に出す。入力の文(`strategy` の文など)を読んで頼みを決めない。発注の頼みについて入力が機械で決めるのは 3 つの通知が一緒に出ることまでで、3 つのうち s がどれを測るかは入力から機械では決まらない(決めるには、下で使わないとした対象の出力・runner の記録・「正解がその事象を名指すか」を読むことになる)。よって注文の 3 つの通知の升目では、機械が決めるのは「発注の頼みを持たない s の宣言は数えない」までで、3 つのどれを数えるかは s の宣言だけが決める。宣言の e が入力から出ない升目は数えず、そういう宣言があれば試験が落ちる(黙って捨てない)。adapter が書く値・対象の出力・runner が残す記録・「正解がその事象を名指すか」「その道を通さなければ正解にならないか」の意味の読みは使わない。判断は機械で 2 値。宣言した升目が s の測る物と合うか(注文の 3 つの通知のどれを数えるかの宣言を含む)と、s の入力がその道を実際に呼ぶかは批評家が読む(LEAD_DESIGN.md §8.5 の 24)。この定義は升目の表と `covers` だけに当て、場面の正解・採点・比較の表のセルを変えない。

## 4. 主張の表(この直しが触る主張の族ごと。直す前に書いた)

| 主張の族 | (a) 導く関数 | (b) 手書きが残る部分と、機械で導けない理由 | (c) 手書きの主張が 1 つでも残っていれば落ちる試験 | (d) 主張を作る機械への mutant の試験 |
|---|---|---|---|---|
| 1. 升目 (市場の事象の型, v, x) が「場面にした」 | `scenes.py:input_types`(`events`・`streams` の型の欄、`type_plan` の場面は `for_target_types(s, TYPE_ORDER)` の入力)→ `scenes.py:covers_of` → `grid_c.py:verdict`・`grid_c.py:table` → `gen_definitions.py:grid_section` | 宣言 `COVERS` の組(どの型をどの見る道・追加の軸で測るか)。入力は型だけを持ち、見る道を持たない。どの道で測るかは場面の測る物の読みで、F はそれを批評家に置く(根 4) | `tests/bt/critic/item_0/test_i0r11_covers_within_scene_input.py:test_a_scene_covers_only_market_types_its_input_runs`、`test_battery_r13_covers_of.py:test_every_scene_declares_only_cells_its_input_gives`、同 `test_covers_follow_the_definition_on_every_copy`(入力の写しの全格子) | `test_battery_r13_claim_mutants.py:test_mutants_of_the_market_type_machine_are_caught`(`input_types` に: 型の欄の無い事象を約定と数える / `type_plan` を無視する / 6 型を全部足す / `streams` を読まない)、同 `test_a_mutant_covers_of_that_returns_the_declaration_is_caught`(`covers_of` が宣言をそのまま返す)、同 `test_a_mutant_verdict_that_reads_the_declaration_is_caught`(`grid_c.verdict` が宣言から数える)。どれも (c) の神託で落ちることを見る |
| 2. 升目 (時計・取消の通知, v, x) と、注文の通知の升目の「発注の頼みがある」 | `scenes.py:input_types`(欄 `requests` → `REQUEST_TYPES`)→ `scenes.py:covers_of` | 欄 `requests` の値。戦略は文で書かれ、文から頼みを決めるのは意味の読み(根 5)。ただし欄の値は、当方の参照の戦略(`adapters/new_impl.py` の各場面の戦略)が実際に出した頼みと機械で照らす | `test_battery_r13_claims.py:test_the_requests_field_is_what_the_reference_strategy_asks`(新実装の adapter で全場面を走らせ、記録した頼みの集まりが欄と等しい)、`test_battery_r13_covers_of.py:test_every_scene_declares_only_cells_its_input_gives` | `test_battery_r13_claim_mutants.py:test_a_mutant_that_does_not_read_the_requests_field_is_caught`(`input_types` が欄を読まない)、同 `test_a_mutant_request_mapping_is_caught`(時計と発注の対応の取り違え)、同 `test_mutants_of_the_requests_field_are_caught`(全場面の欄の写しに頼みを 1 つ落とす・1 つ足す) |
| 3. 注文の受付・拒否・約定の 3 つのうちどれを場面が測るか | 無い(機械は主張 2 の「発注の頼みがある」までを決める) | 宣言の通知の種類。3 つのどれが起きるかは頼みと市場と口座の帰結で、入力から決めるには F が使わないとした物を読む(根 6)。批評家が読む | 手書きが残るので、残れば落ちる試験は無い。宣言の通知を 3 つの中の別の通知に替えた写しを機械が落とさないことを `test_battery_r13_covers_of.py:test_swapping_one_order_notice_for_another_is_left_to_the_declaration` が示す(残っていることの試験) | 無い(機械が無い) |
| 4. 取消の通知の升目は事象の軸の外 | `grid_c.py:axes`(要件の文の判断から軸を作る)、`scenes.py:OUTSIDE_AXES`、`gen_definitions.py:grid_section` | `OUTSIDE_AXES` の理由の文(要件 §1 の通知は 3 つで取消の通知を名指さないこと)。要件の文を読む判断で、`grid_c_judgments.tsv` と同じく場面係の判断 | `test_battery_r13_covers_of.py:test_the_cancel_notice_stays_outside_the_event_axis` | `test_battery_r13_claim_mutants.py:test_a_mutant_that_puts_the_cancel_notice_on_the_event_axis_is_caught` |
| 5. 記録 `types_in`・`types_added`(対象に入った市場の事象の型)| `run_battery.py:records_of`(戦略に届いた列がある場面は届いた型、無い場面は渡した入力の型から `as_bar` などの共通の部品で代えた型を除き、設定つき対象の持つ型(p3 の採点、L-438 (2))に限る) | 戦略に届いた列を持たない場面で、adapter が型を代えたことは adapter のコードが共通の部品を通すことに拠る。対象ごとの API に渡した物を runner は見られない(根 7)。残る穴は「設定つき対象の持つ型なのに共通の部品を通さず代える」形で、adapter のコードの形を検める試験で塞ぐ | `test_battery_r13_claims.py:test_records_types_in_within_the_input_handed`(`survey_results/` の全行)、同 `test_no_adapter_builds_a_substitute_event_outside_common`(adapter と相手のコードの全部を構文木で読み、場面の事象から型の欄を持つ辞書を作る所が共通の部品の外に在れば落ちる)、同 `test_records_of_on_every_case`(記録の関数の入力の全格子) | `test_battery_r13_claim_mutants.py:test_mutants_of_the_records_machine_are_caught`(`records_of` に: 代えた型を除かない / 設定つき対象の持つ型に限らない / 届いた列を読まない、を当てる) |
| 6. 記録 `requests`(戦略が出した頼み) | `adapters/common.py:request`・`requests_taken` → `run_battery.py:records_of` | adapter の戦略が頼む所で `request` を呼ぶこと(adapter の申告)。対象ごとの API の呼び出しを runner は見られない。新実装と当方の現状の adapter だけが申告し、相手の adapter は null(§8 の 5 に上げる) | `test_battery_r13_claims.py:test_records_requests_within_the_field`(`survey_results/` の全行で記録 ⊆ 欄)、同 `test_the_current_implementations_requests_are_within_the_field`(当方の現状の adapter で記録 ⊆ 欄)、同 `test_the_requests_field_is_what_the_reference_strategy_asks` | `test_battery_r13_claim_mutants.py:test_mutants_of_the_records_machine_are_caught`(`records_of` に: 申告しない adapter の欄を [] にする、を当てる) |
| 7. 注記「場面にしたが、この対象には型が入らなかった升目」 | `grid_c.py:not_entered`(升目の表と記録から) | 無い | `test_battery_r13_claims.py:test_not_entered_on_every_case` | `test_battery_r13_claim_mutants.py:test_mutants_of_not_entered_are_caught` |

族 1〜4 は升目の表の主張、族 5〜7 は §9.2 の 33 の記録と注記の主張である。どれも比較の表のセル(正しさ・再現)を変えない。この表は直す前に書き、直したあとで (c)・(d) の列の試験の名を、書いた試験の実際の名に合わせた(中身は変えていない)。

## 5. どの作りを変えるか

1. `scenes.py`: `COVERS` を升目の宣言として残し、`covers_of` で入力から出る型の升目だけを数える(前の起動の直しのとおり)。p6-place-then-cancel の宣言を空にする(根 9)。ほかの全場面の宣言を、場面の測る物と入力に照らして読み直す(結果は §6)。
2. `grid_c.py`: `not_entered` を足す(根 8)。
3. `run_battery.py`: `records_of` で、戦略に届いた列を持たない場面の `types_in` を設定つき対象の持つ型に限る(根 7)。
4. adapter と相手のコード: 場面の事象の型を代える所を共通の部品(`adapters/common.py` の `as_bar` と新しい `substitute`)に寄せる(根 7)。新実装・当方の現状の adapter の戦略が頼む所で `request` を呼ぶ(根 5・根 7)。
5. 試験: §4 の (c)・(d) の試験を直す前に書く。敵対者の格子は前の起動の `test_battery_r13_covers_of.py`(族 1〜4)と、この回の `test_battery_r13_claims.py` の `test_records_of_on_every_case`・`test_not_entered_on_every_case`(族 5・7)。
6. DEFINITIONS.md(`gen_definitions.py` から作る)、`def_axes/jC.tsv`(正の定義 C の段落の切片の判断)、`line_judgments.tsv`・`term_judgments.tsv`(正の定義 B・D)を直す。
7. 全対象を走らせ直して `survey_results/` の記録の列を埋める。候補 35 を 3 手で走らせ、`RUNNABILITY.tsv`・検討表・adapter を直す。
8. `ROOTCAUSE_r12-1.md` に「採らなかった案(第 12 周の定義 3 版)」の見出しを付ける。

## 6. 直した結果(指摘ごとの根拠。§1〜§5 を書いたあとに直した)

`<S>` の出力の先頭には、打った版とコマンドを書いた。版は、前の起動のリードのコミット c6d88e8(この回の §1〜§5 と試験の最初の版を含む)の上の作業木。

### 6.1 i0-r11-02(主張の族 1〜4)

- 升目の判断は `scenes.py:covers_of`(651 行)が `scenes.py:input_types`(625 行)と宣言 `COVERS`(589 行)から出し、`grid_c.py:verdict` はそれだけを読む(前の起動の直しのまま。この回は試験で確かめた)。批評家の試験 `test_i0r11_covers_within_scene_input.py` は変えずに全部通る(§6.7)。
- 「場面にした」の升目の数(DEFINITIONS.md の観点ごとの見出し。第 r11-1 回の版 → この回): P0-1 6 → 4、P0-2 12 → 0、P0-3 13 → 13、P0-4 4 → 2、P0-5 6 → 4、P0-6 2 → 1、P0-7 7 → 3(計 50 → 27)。打ったコマンド: `git show dc9e04a~1:tests/bt/battery/item_0/DEFINITIONS.md | grep '^### P0-[0-9](升目'` と、この作業木の DEFINITIONS.md の同じ行。P0-2 が 0 になるのは、P0-2 の 4 場面の入力の事象に型の欄が無い(2 場面)か事象が無い(2 場面)からで、F の「型の欄の無い事象と、事象を持たない場面からは型を出さない」のとおり。場面係は条件を足していない。
- F を字のまま積で数えた場合と比べた計算は `<S>item0_r13-1_scenekeeper_fix_product.txt`(項「== cells the product counts that the rule used does not (broadened by the product)」: 17 升目。例: p3-notice-accepted の入力の約定から、(約定, 発注の呼び出しがその場で返す物) が数えられる)。この回の数え方が積より広げる升目は 0(同じ出力の最後の項)。§8 の 1 の根拠。

### 6.2 宣言の読み直し(同じ種類の欠陥を全場面で探した。§2 の根 9)

読み方: 場面の `measures` が、結果を見る道としてその見る道を名指し、かつその道で見る物がその事象の中身であるときだけ、その升目を宣言する(`scenes.py` の `COVERS` の前の注、579 行)。見る道の略: R = 戦略の呼び出しに届く物、O = 発注の呼び出しがその場で返す物、Q = 戦略が対象の公開の手段で読む物。

| 場面 | 直した後の宣言 | 読み |
|---|---|---|
| p1-merge-by-time・p1-typed-events・p5-same-time-twice・p5-hand-over-order | 6 型を持つ対象のために作る入力の型 × R | 測る物は戦略の呼び出しに届いた列の型と時刻。型は `type_plan` の入力から機械で出る。変えていない |
| p1-one-call-per-event・p3-trade〜p3-liquidation・p3-mixed-one-run・p4-received-time・p5-same-stream-order | 入力の型 × R | 測る物は戦略の呼び出しに届いた物。変えていない |
| p2-iso-utc・p2-iso-offset・p2-event-time-exact・p2-one-ns-apart | 無し | 入力に型の欄が無いか事象が無い。F により型を出さない |
| p3-clock-timer | (時計, R) | 測る物は時計の事象として戦略が呼ばれた時刻。変えていない |
| p3-notice-accepted・p3-notice-rejected・p3-notice-filled | (その通知, R)・(その通知, O) | `measures` が「戦略の呼び出しに事象として届いたか、発注の呼び出しの戻り値・例外としてその場で返ったこと」と 2 つの道を名指す。変えていない(どちらか一方の道で結果が出るので、道ごとには分けて測っていない。§7 に書いた) |
| p4-visible-at-step・p4-future-read-attempt | (足, Q) | 測る物は戦略が対象の公開の手段で読んだ過去の足。変えていない |
| p6-place-then-cancel | 無し(前は (注文の受付の通知, Q)) | 読むのは未決の注文の数で、受付の通知の事象ではない。未決の数は、受付を通知しない対象でも発注の直後に 1 になりうる(受付と区別できない)。批評家の「人の読みで残る点」のとおり |
| p6-cancel-notice | (取消の通知, R) | 軸の外の升目(`OUTSIDE_AXES`)。変えていない |
| p6-fill-seen-by-strategy | (注文の約定の通知, Q) | 読むのはその注文の約定済みの数量で、約定の通知の中身(埋まった数量)。約定が無ければ 0 のままなので、約定と区別できる。変えていない |
| p7-fill-model-swap・p7-latency-model-swap・p7-cost-model-swap・p7-cost-per-unit | (注文の約定の通知, R, その口)(前は Q も) | `measures` の 2 つ目の道は「実行の結果の約定の記録」で、実行のあとに読む物であり、戦略が対象の公開の手段で読む物(Q)ではない。Q を外した |
| p7-account-swap | 無し(前は (注文の約定の通知, Q, 口座)) | 読むのは差し替えた口座自身の記録で、戦略は何も読まない。見る道の軸(R・O・X・Q)のどれにも当たらない。§8 の 6 に上げた |

### 6.3 記録と注記(主張の族 5〜7、§9.2 の 33)

- `run_battery.py:records_of`(776 行): 戦略に届いた列を持たない場面の `types_in` を、共通の部品で代えた型を除き、設定つき対象の持つ型(`target_types(p3_1)`、859 行)に限った(789 行)。
- `adapters/common.py:substitute`(27 行)を足し、adapter と相手のコードの中で場面の事象を市場の事象の型の辞書に作り替える 32 か所を全部 `C.substitute` に替えた(対象自身の形 "tick" に作る `opponents/gobacktest_adapter.py` の 1 か所は、場面の型の間の作り替えではないので替えていない)(書き換えの前後: `<S>item0_r13-1_scenekeeper_fix_substitute_rewrite.txt`)。どれも同じ値の辞書を返す形のままで、辞書に無かった欄を足していない。
- `adapters/new_impl.py` の戦略の 6 か所(発注 4・時計 1・取消 1)と `adapters/current_impl.py` の戦略(HOLD 以外の合図を返す所、62 行)で `C.request` を呼び、両方の adapter に `records_requests = True` を置いた。
- `grid_c.py:not_entered`(155 行)・`records_from_tsv`(177 行)・`not_entered_note`(188 行)を足した(根 8)。`python3 grid_c.py <runner の出力>…` が設定つき対象ごとに注記の 1 行を出す。資料係への申し送り(DEFINITIONS.md)に書いた。
- 全対象を走らせ直して `survey_results/` の記録の列を埋めた(§6.4)。

### 6.4 全対象の走らせ直しと候補 35

- 全対象の走らせ直し: 台本 `<S>item0_r13-1_scenekeeper_fix_run_all.sh`(対象と interpreter の対応は第 11 周の資料係の `run_all.sh` と同じで、候補 35 を足した)。記録 `<S>logs/run_all.log`: `run_battery.py --list-targets` の 57 の設定つき対象が全部 rc=0(02:58:53〜03:09:59 UTC)。相手と再現の 54 の出力を `survey_results/` に写した(新実装・当方の現状・試金石の出力は資料係が周ごとに作るので写していない。`<S>runs/` に在る)。
- 注記: `<S>item0_r13-1_scenekeeper_fix_not_entered.txt`(項「== 場面にした升目(事象の軸) 27」の下に設定つき対象ごとの「入らなかった」「記録なし」の数、項「== note lines」に注記の 1 行)。新実装と試金石は両方 0、当方の現状は入らなかった 15・記録なし 0、相手は頼みを記録しないので通知と時計の升目が「記録なし」になる。
- 候補 35: リードの 3 手を同じく打った(`<S>item0_r13-1_scenekeeper_fix_c35_run.log`、`survey_results/attempts/35.log` の最後の節。道具が出した費用の値は、道具自身の合成の価格の道から出た物で、記録から外した)。`main.py` は rc=0。adapter `opponents/thirupathikannan_execsim_adapter.py` を書き、`run_battery.py` の `OPPONENTS` と `TARGET_DISTS`(85・295 行)に足し、写しを指す .pth を venv に置いて全 32 場面に通した: 32 場面とも「対応なし」(各場面で `execute_order` を実際に呼んだ結果つき。P0-7 の場面では差し込みの物をキーワードで渡して `TypeError: execute_order() got an unexpected keyword argument` が出る)、再現は 32 場面とも 2 回で同じ(`survey_results/opp_thirupathikannan_execsim.tsv`)。`opponents/RUNNABILITY.tsv` の 35 の行を「走った」に直し、検討表の P0-7 の動かせた候補に移して検討表の行を外した。`python3 scripts/check_bt_considered.py tests/bt/battery/item_0/opponents/CONSIDERED.md --write` → 「OK 誤り 0 件」。

### 6.5 そのほか

- `ROOTCAUSE_r12-1.md` の 1 行目に「採らなかった案(第 12 周の定義 3 版)」の見出しを付け、その下に採らなかった理由と出所の段落を足した(本文は変えていない)。
- DEFINITIONS.md(`gen_definitions.py` から作る): 正の定義の節に F の逐語(`LEAD_F`)と第 r13-1 回の正の定義(`R13_DEFINITION`、§3 と同じ文)を置き、両方の文の一致を `test_battery_r13_claims.py:test_the_rule_texts_are_the_sources_character_for_character` が照らす。欄 `requests` と記録の列の申し送りの文を、§6.3 のとおりに直した。
- `def_axes/jC.tsv`: 正の定義 C の段落は前の起動の直し(§9.2 の 34)で `covers` の決め方の文が替わり、切片が 93 → 105 になっていた。新しい切片 62〜77 に判断を付け、78〜105 は前の 66〜93 の判断を移した。移した判断の理由の欄の切片の番号のうち、前の版から今の段落と合っていなかった物(例: 前の 72「77 の中身」は 71 を指すべきだった)も、今の段落の番号に直した(前後: `<S>item0_r13-1_scenekeeper_fix_jC_before.tsv` と今のファイル)。
- `line_judgments.tsv`・`term_judgments.tsv`(正の定義 B・D): 変えた行と足した行の判断を足し、行の無くなった判断を消した(§6.7)。

### 6.6 走らせ直しの前後で結果が変わっていないこと

`<S>item0_r13-1_scenekeeper_fix_compare.py` で、正しさ・2 回目の正しさ・再現・両方の実行の状態と出力・期待の欄を、前の結果(相手と再現は HEAD の `survey_results/`、新実装・当方の現状・試金石は第 11 周の資料係の `runs/`)と場面ごとに照らした(一時フォルダの名の乱数 8 字は伏せた)。出力 `<S>item0_r13-1_scenekeeper_fix_compare.txt`: 56 対象(候補 35 は前が無い)のうち違いは 1 対象 2 欄だけで、`opp_predictivedev_tradesim` の p7-latency-model-swap の出力の約定の時刻の値(その道具が壁時計の時刻を使うため。正しさ「不一致」と再現「2 回で違う」は前と同じ)。宣言・欄 `requests`・作り替えの書き方・記録の列の直しは、比較の表のセルを変えていない。

### 6.7 試験・mutant・検討表

- 直す前(この起動の始め、HEAD d2a6254 の上の前の起動の途中の変更): `<S>item0_r13-1_scenekeeper_fix_pytest_before.txt`。批評家の試験は前の起動の直しで既に通り、場面集の試験 4 件が落ちていた(正の定義 C の段落の切片の判断・語と行の判断が、前の起動の文の置き換えに追いついていなかった)。
- 試験を先に書いた記録: `<S>item0_r13-1_scenekeeper_fix_tests_first.txt`(直す前に `test_battery_r13_claims.py`・`test_battery_r13_claim_mutants.py` を回し、12 件が落ちた)。
- 直した後: `<S>item0_r13-1_scenekeeper_fix_pytest_after.txt` の 3 つの項。`PYTHONPATH=src python -m pytest tests/bt/battery/item_0 tests/bt/critic/item_0 -p no:cacheprovider` → 「310 passed」。批評家の試験 `test_i0r11_covers_within_scene_input.py`(変えていない)→ 「32 passed」(指摘の文の 13 場面を含む)。主張の表の試験 3 ファイル → 「91 passed」。
- 主張の表の (d): `test_battery_r13_claim_mutants.py` の mutant は、市場の型の機械に 4 種(型の欄の無い事象を約定と数える / `type_plan` を読まない / 6 型を全部足す / `streams` を読まない)、`covers_of` に 1 種、`grid_c.verdict` に 1 種、頼みの機械に 2 種(欄を読まない / 時計と発注の取り違え)、欄 `requests` の写しに全場面 × 1 つ落とす・1 つ足す、軸に 1 種、`records_of` に 4 種、`not_entered` に 3 種。どれも捕まり、機械そのものは神託と一致する(`test_the_machine_itself_agrees_with_the_oracle`)。
- 場面集の試金石: `PYTHONPATH=src python3 tests/bt/battery/item_0/mutant.py --check` → 「changed scenes: ['p4-received-time']」「OK」(`<S>item0_r13-1_scenekeeper_fix_mutant.txt`)。
- 検討表: `python3 scripts/check_bt_considered.py tests/bt/battery/item_0/opponents/CONSIDERED.md --write` → 「OK 誤り 0 件」。
- 全試験: __FULL__

## 7. 提出前の吟味(委任文 §3「提出前の吟味」(1)〜(6))

読み直した物: 委任文(全 169 行)、固定した要件 REQUIREMENTS.md(§1・§2)、場面集の規則 1〜9、LEAD_DESIGN.md の §8.2・§8.5・§8.6・§9・§10、指摘 i0-r11-02 の逐語と批評家の試験、監査役(定義) r13-1-1・r13-1-2 の逐語(`docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/battery/AUDIT.md`)。

| 非常に厳しい批評家なら [止める] にする候補 | 何をしたか |
|---|---|
| i0-r11-02: 宣言の市場の型が入力より広い | 批評家の試験 32 件(指摘の文が落ちると書いた 13 場面を含む)が通る(§6.7)。宣言の型が入力から出なければ `covers_problems` が名指し、試験が落ちる。入力の写しの全格子で神託と照らす(`test_battery_r13_covers_of.py`)。升目の機械を壊す mutant 6 種(市場の型の機械 4・`covers_of` 1・`verdict` 1)がどれも捕まる(§6.7) |
| 同じ族の別の形 1: F を字のまま積で数えると同じ向きに広がる | この回の数え方は宣言した 3 つ組と入力の両方を要る形(§3)。積より広げる升目は 0(§6.1)。§8 の 1 に上げた |
| 同じ族の別の形 2: 欄 `requests` が手書きで、戦略の実際の頼みと照らさない 2 つ目の元になる | 新実装の adapter の戦略を全場面で走らせ、記録した頼みが欄と等しいことを試験にした。欄から 1 つ落とす・1 つ足す写しを全部捕まえる mutant の試験を置いた |
| 同じ族の別の形 3: 記録 `types_in` が adapter の作り替えを取りこぼして「入った」と広く出る | 設定つき対象の持つ型に限り、作り替えを共通の部品に寄せ、共通の部品の外の作り替えを構文木で探す試験を置いた(§6.3)。辞書を使わずに対象の API に直に作り替えて渡す形は構文木では見えない(試験のファイルの「Not in the grids」に書いた)。そのときも設定つき対象の持つ型に限る所で、その対象の持たない型は入らない側に出る |
| 同じ族の別の形 4: 宣言した見る道が場面の測る物でない | 全 32 場面を読み直し(§6.2)、p6-place-then-cancel・p7 の 4 場面の Q・p7-account-swap を外した。p3 の通知の 3 場面と p7 の 4 場面は、`measures` が 2 つの道のどちらか一方で結果が出る形で、道ごとには分けて測っていない。宣言はどちらの道も「測る物が名指す道」として残した(批評家が読む。§8 の 4) |
| 注記の関数が無い(§9.2 の 33 の「機械で出す」を満たさない) | `grid_c.not_entered` を足し、入力の全格子(記録 5 通り × 4 場面 = 625 通り)で神託と照らし、mutant 3 種を捕まえる |
| 記録 `requests` が相手の adapter で null | 作らずに止め、§8 の 5 に上げた(注記は「記録なし」と分けて出し、入ったとは数えない) |
| P0-2 が 0 升目になる | F の文のとおり。場面係は条件を足していない。§6.1 に書いた |
| 候補 35 を「走った」にしたのに場面に通していない | 全 32 場面に通した(§6.4)。検討表の行を外し、動かせた候補の行に移し、`check_bt_considered.py` を誤り 0 件にした |
| 候補 35 の検討表の根拠が消える | 外した行の能力ごとの根拠(行の番号)を adapter の注に写した |
| 実装(`src/bot/bt/`)と作業者の試験(`tests/bt/item_0/`)に触れる | 触れていない(§9 の差分) |
| 場面の正解・採点・比較の表のセルが変わる | 変えたのは宣言・記録の列・adapter の作り替えの書き方・候補 35 の追加だけ。走らせ直しの前後で、全対象の全場面の正しさ・再現・出力が同じかを照らした(§6.6) |
| 前の版の試験を消した・書き直した | 消していない。`test_battery_r13_covers_of.py` はこの回の宣言に合わせて変える所が無かった(宣言を読むのは `scenes.COVERS`) |
| 自分の作業の採点を書く(O-10) | この表は候補と、したことだけを書き、通るかの判定は書いていない |

## 8. リードに聞くこと

### 8.1 正の定義 F の内容を変えた点(返り値の `lead_answer_changes` と同じ文)

1. 升目の数え方を、F の「s が (v, x) を宣言し、かつ型 e が s の入力から機械で出る」(型と見る道を別々に取った積)から、「s が升目 (e, v, x) を宣言し、かつ型 e が s の入力から機械で出る」(宣言と入力の両方が要る)に変えた。理由: 升目は型と見る道と追加の軸の 3 つ組で、どの型をどの見る道で見るかの組は入力にも (v, x) の宣言にも無い。F を字のまま積で数えると、今の場面集では 17 升目が広がる(例: p3-notice-accepted の入力の約定から (約定, 発注の呼び出しがその場で返す物) が数えられる。`<S>item0_r13-1_scenekeeper_fix_product.txt`)。向きは i0-r11-02 と同じ(測っていない範囲を狭く見せる)。批評家の神託は型が入力にあるかだけを見るので積の広がりを捕まえない。変えた形の升目は F の升目の部分集合で、F が数えない升目を足さない(同じ出力の最後の項)。これに伴い、F の「手書きの宣言…は使わない」は「手書きの宣言は升目の上限としてだけ使い、宣言だけでは数えない。宣言の型が入力から出なければ試験が落ちる」に、§9.2 の 34 の「`COVERS` の事象の手書きの一覧を消し、(v, x) の宣言だけを残し」は「`COVERS` を升目 (e, v, x) の宣言として残し、入力から出ない型の宣言を消し、`covers_of(s)` を宣言と入力の両方から計算する」に替わる。注文の受付・拒否・約定の 3 つの通知の升目では、機械が決めるのは発注の頼みの有無までで、3 つのどれを数えるかは宣言が決め、批評家が読む(F の積の形では 3 つとも数える)。
2. 戦略の頼みの読み方を、F の「s の入力の戦略の頼み」から「s の入力が欄 `requests` として持つ戦略の頼み(入力の文を読んで頼みを決めない)」に変えた。理由: F は判断を機械で 2 値とするが、頼みを入力のどの欄から読むかを決めていない。頼みは `strategy` の文にしか無く、文を語で探す読み方は言い換えで黙って外れる。欄の値は、新実装の adapter の戦略が実際に出した頼みと等しいことを試験で照らす(`test_battery_r13_claims.py:test_the_requests_field_is_what_the_reference_strategy_asks`)。
3. §9.2 の 33 の試験「全記録の `types_in` ⊆ F で出した型」を、「全記録の `types_in` ⊆ runner がその設定つき対象に渡した入力の型」に変えた。理由: `type_plan` の 4 場面では、F で出す型は 6 型を全部持つ対象のために作る入力の型だが、runner が設定つき対象に渡す入力は設定つき対象の持つ型から作る(L-438 (2))。6 型を全部は持たない設定つき対象では、渡した型が F の型の外になりうるので、字のままの試験は adapter が型を足していなくても落ちる。`type_plan` の無い場面では 2 つは同じ物である。

### 8.2 そのほか

4. **注文の 3 つの通知のどれを数えるか(監査役(定義) r13-1-2 の [聞く] 1)**: 答え: 前の起動の定義の段で上げたまま、宣言が決めて批評家が読む形で直しに進んだ(この回の起動文は「F を規則として…直す」と直しの段を求め、定義の段は L-443 で無い)。機械で閉じるには F が使わないとした物(正解の欄が名指す通知の種類・対象の出力・記録)のどれかを使う決定が要り、場面係は決めない。3 つの升目を「測っていない」に振るのは場面が測る升目を測っていない側に置くので採らなかった。同じく、p3 の通知の 3 場面と p7 の 4 場面は `measures` が 2 つの道のどちらか一方で結果が出る形で、道ごとには分けて測っていない(§6.2)。この扱いでよいか、閉じる決定をするかを聞く。
5. **相手の adapter の記録 `requests`**: 記録するのは新実装・当方の現状・試金石の adapter だけで、相手の 37 の adapter(41 の設定つき対象)と再現の 1 つ(13 の設定つき対象)は null。相手の adapter の戦略は対象ごとの API で頼みを出し、runner はそれを見られないので、記録には adapter の各場面の戦略に `request` を書き足すことが要る(38 ファイル × 最大 12 場面)。書き足しても adapter の申告で、照らせるのは「記録 ⊆ 欄」だけである。§9.2 の 33 の記録をこの形で相手の全部に要るかを聞く。答えが来るまで、注記は相手の通知・時計の升目を「頼みの記録が無く入ったかを決められない升目」と分けて出す(入ったとは数えない)。
6. **P0-7 の差し込んだ口座(と、実行のあとに読む約定の記録)を見る道が升目の軸に無い**: 見る道の軸は要件の文から機械で作った R・O・X・Q の 4 つで(`grid_c_judgments.tsv`)、「差し替えた口座が受け取った物」「実行のあとに読む約定の記録」はどれにも当たらない。よって p7-account-swap は升目を宣言せず、P0-7 の口座の 40 升目は全部「測っていない」になった(場面 p7-account-swap は口座の口を測っている)。軸の値は要件の文の判断から作る物で、場面係が足す物ではない。要件の文を読む判断(`grid_c_judgments.tsv`)をリードが見直すかを聞く。
