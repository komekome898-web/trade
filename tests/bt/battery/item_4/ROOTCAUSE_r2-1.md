# 場面集への指摘の根本原因と主張の表(項目 4、第 r2-1 回の直し、場面係、2026-09-26)

合意した完了の形(オーナー逐語、L-405): 「**すべてが調査結果以上の信頼性と再現性に優れたものにすること。**」

委任文 `docs/DATA/delegations/20260925_backtest_env_prompt.md` の指紋は `sha256sum` の先頭 12 桁で `388d55cdeb32`(起動文と一致)。
起動文の逐語「**直す前に** … ROOTCAUSE_r2-1.md に、指摘 1 件ごとに「なぜ起きたか(根本原因)」と「どの作りを変えるか」を書く」
「直しの前に … この直しが触る主張の族ごとに 4 列の表を書く」(L-443)に従い、§1〜§5 は直す前に書いた。§6 以降は直したあとに書く。
`<S>` = `/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt`。

## 0. 対応表(CLAUDE.md §0.1。右は起動文・指摘・委任文の逐語)

| やること | 該当語(逐語) |
|---|---|
| 足 j の始値の合図と足 j の範囲の逆指値・利確の順を決める規則の文を足し、legacy と spec の 2 出力の場面と spec の値の場面を置く | i4-r1-02「規則の文を足し、legacy と spec の 2 出力の場面と spec の値の場面を置くこと」 |
| 足 0 の合図・maker と taker で違う手数料のような、観点の本題でない条件で道具が「結果なし」になる偏りを除く | i4-r1-05「観点の本題でない条件で強い足の道具が『結果なし』になる偏り」 |
| I4-2 の性質の場面を、逆指値・利確・maker・持ち越し・時間切れ・構造的な逆指値の経路に広げ、正解なしで不変条件で判定する | i4-r1-06「性質の場面は正解なしで不変条件だけで判定できるので、手で正解を出せない経路こそ性質で見ること」 |
| I4-3 に核の粒度の値の場面を置く | i4-r1-07「核の粒度の値の場面が無く、外した理由も DEFINITIONS.md に無い」 |
| 検討表の「読んでいない」「読んだ範囲に無い」を「持たないと確認した」に数えない | i4-r1-08「読むか、『再現できない』に直すこと」 |
| 変形の能力の場面に、同じ能力が通る対照を置く | i4-r1-09「price_rule が通る対照が無い」「事前登録つきの研究が通る対照が無い」 |
| 新実装の互換の出力を旧の名前・旧の引数の口から取る | i4-r1-10、委任文 §3「互換の口(旧と同じ名前・同じ引数で旧と同じ出力)と新エンジン本来の模型の両方を持つもの全体」 |
| lumibot・Hikyuu・zvt の導入を試み、容量で止めるならその実測を記録に足す | i4-r1-11「導入の試み(容量で止めるならその実測)を記録に足すこと」 |
| 項目 0 の場面集 i0-r16-05 | 起動文のリードの注記「項目 0 の場面集 tests/bt/battery/item_0/ には触れない」(§2.9 で扱う) |
| 同じ種類の欠陥を場面集の全体で探して直す | 起動文「同じ種類の欠陥を場面集の全体(全観点・全場面・検討表の全行)で探して直す」 |
| 実装(src/bot/bt/)と作業者の試験(tests/bt/item_4/)に触れない | 起動文「実装(src/bot/bt/ の下)と作業者の試験(tests/bt/item_4/)には触れない」 |
| 場面の期待は要件の文から独立に出し、新実装の内部の名前・形を写さない | 起動文「場面の期待は要件の文から独立に出せる振る舞いで書き、新実装の内部の名前・形を写さない(規則 2)」 |
| 直した規則ごとに全格子の敵対者の試験を先に書き、列に入れなかった物を試験のファイルに書く | 起動文 (6) |

## 1. 指摘の一覧

| id | 格 | repeat_of | 相手のファイル |
|---|---|---|---|
| i4-r1-02 | [止める] | null | i4_scenes.py・gen_definitions.py・DEFINITIONS.md |
| i4-r1-05 | [止める] | null | i4_scenes.py・CONSIDERED.md・gen_considered.py・gen_definitions.py・DEFINITIONS.md |
| i4-r1-06 | [止める] | null | i4_scenes.py・i4_judge.py・gen_definitions.py・DEFINITIONS.md |
| i4-r1-07 | [止める] | null | i4_scenes.py・gen_definitions.py・DEFINITIONS.md |
| i4-r1-08 | [止める] | null | CONSIDERED.md・gen_considered.py |
| i4-r1-09 | [直す] | null | i4_scenes.py・run_battery.py |
| i4-r1-10 | [直す] | null | adapters/new_impl.py |
| i4-r1-11 | [直す] | null | RUNNABILITY.tsv・CONSIDERED.md |
| i4-r1-13 | [直す] | i0-r16-05 | tests/bt/battery/item_0/scenes.py |

## 2. なぜ起きたか(根本原因)

### 2.1 i4-r1-02(同じ足の中の順が規則の文に無い)
- **根**: 規則の文(「足の模型の仕様」)を、出来事ごと(R-T1・R-P3・R-P4・R-X1・R-H1・R-W3・R-M1)に 1 つずつ書き、**同じ足で 2 つ以上が起きうるときの順**を出来事の組ごとに決めていなかった。書いた順は R-P3(逆指値と利確)・R-H3(時間切れの足の逆指値)・R-H2 と R-W3(始値の出口は待つ合図を捨てる)の 4 組だけで、残りの組(始値の合図 × 範囲の逆指値・利確・maker の利確、構造的な逆指値 × 利確、待つ決済の指値 × 逆指値・利確・時間切れ・構造的な逆指値、率の利確 × maker の利確)は文が無い。文が無い組では、正解が規則から出せず、場面も置けなかった。
- **検出の欠け**: 手で置いた決済の足と値が、規則の順から出る値と一致するかを機械で確かめる試験が無かった(場面ごとの注記を人が書くだけ)。どの組を場面が固めているかを数える機械も無かった。
- **同じ種類の探し方**: 出来事の全部の組(8 個の出来事から 2 個、両立しない組を除く)を列べ、組ごとに「規則の文があるか」「その組を含み、勝つ側が決済になる場面があるか」を機械で数える(§4 A)。

### 2.2 i4-r1-05(観点の本題でない条件で結果なし)
- **根**: 場面を観点の本題(逆指値の先・maker の利確・時間切れ・持ち越し・指標)で作るとき、**本題でない選択肢**(足 0 の合図、費用、maker と taker の違う率)を、場面の正解を面白くするために足した。場面が「本題だけを要する最小の形」を 1 つも持つかを確かめる機械が無かった。そのため、本題の能力を持つ道具が、本題でない口(足 0 で戦略を呼ばない・手数料の率が 1 つ・手数料の口が無い)だけで「結果なし」になり、検討表はそれを観点の能力が無いと書いた(規則 6 の「その能力に当たる口」でない口で判断した)。
- **判定しない費用**: 同じ根で、判定する鍵(fills と missed_fills だけ)からは見えない手数料の率を置いた場面がある(i4-9-strict・i4-9-short-strict・i4-16-missed の maker の率、i4-8 の taker だけの場面の maker の率 0.05)。見えない費用は答えを変えないのに、手数料の口の無い道具を「結果なし」にする。
- **同じ種類の探し方**: 足の場面の全部について、(1) 足 0 の合図、(2) 0 でない費用、(3) 違う 2 つの手数料の率、(4) 判定する鍵から見えない費用、を機械で数え、足の観点(I4-8〜I4-17)ごとに (1)〜(4) の無い値の場面があるかを見る(§4 B)。検討表の側は、観点の行の判断が最小の場面の理由に基づくかを機械で見る(§4 G)。

### 2.3 i4-r1-06(性質の場面が taker だけ)
- **根**: 性質の場面(I4-2)の格子を「正解つき」で作ろうとしたため、正解を関数で出せる taker だけの規則(taker_rule)の範囲に縮めた。不変条件も taker の手数料の率だけで式を立て、正解と完全に突き合わせたあとに検めるので、正解が満たす式から自動で従い、何も新しく捕まえなかった。**性質の場面の価値は正解なしで判定できることで、正解を出せない経路にこそ使うべき**という役割の取り違え。
- **同じ種類の探し方**: 格子の場合の設定が、足の模型の選択肢(執行 2・逆指値・利確・maker の利確・持ち越し・保有の上限・構造的な逆指値・建てのマスクと向き・ショート・費用 4・足の秒)のそれぞれを 1 つ以上含むかを機械で数える。不変条件の式が、観測した約定から出るもの(規則の場合分けを写さない)だけで立つかを読む(§4 C)。

### 2.4 i4-r1-07(核の粒度の値の場面が無い)
- **根**: 要件 I4-3「核・参照実装・新エンジン全体のそれぞれの粒度に」を、場面を作るときに観点の粒度の語として読まず、新エンジン全体の 2 場面と参照実装の 2 場面(I4-1)で足りるとした。場面にできない観点の一覧(I4-7・I4-19・I4-20)にも載せず、説明なく縮めた(A-10)。
- **同じ種類の探し方**: 要件 §2 の観点の文にある「それぞれ」「全」「両方」のような列べの語を全部拾い、列べの各項に場面があるかを機械で数える(§4 D)。

### 2.5 i4-r1-08(読んでいないことを「持たないと確認した」に数えた)
- **根**: 検討表を作る gen_considered.py が、再現の理由の文のうち「再現していない」だけを「確かめていない」印として扱い、「読んでいない」「読んだ範囲に無い」を確かめた無さ(行を引いた「無い」)と同じに扱った。判断の条件が「場面ごとに、確かめた無さが 1 つ以上ある」になっていなかった。
- **同じ種類の探し方**: 検討表の全行の理由を部分に割り、部分ごとに「確かめた無さ」(行・URL を引き、読んでいない語が無い)か「確かめていない」(読んでいない・読んだ範囲に無い・再現していない)かを機械で分け、場面ごとに確かめた無さが 1 つ以上あるかを見る(§4 G)。

### 2.6 i4-r1-09(変形の場面が断りの理由を見ない)
- **根**: 変形(断るのが正解の入力)の場面の対照を、「その機能を使わない普通の入力」にした。対照が通っても、**変形が使う機能**(値で決める戦略・目的「研究」・率の逆指値)を対象が持つことは示されないので、その機能を全く持たない対象が変形を断っても満点になる。
- **同じ種類の探し方**: 変形のある全場面(i4-6-signal-refused・i4-6-research-refused・i4-11-refuse-stack・i4-12-refuse・i4-18-refuse)について、変形の入力が使う機能のそれぞれが、正解つきで通る対照のどれかで使われているかを機械で見る(§4 E)。

### 2.7 i4-r1-10(互換の出力を旧の口から取っていない)
- **根**: new_impl の adapter の「legacy」を、新エンジンの足の模型の規則の組「legacy」を直接呼んで取った。委任文 §3 は旧 14 の部分の新実装を「互換の口(旧と同じ名前・同じ引数)と本来の模型の両方を持つもの全体」として通すと定めるので、互換の出力は旧の名前・旧の引数の口(`run_backtest`・`CostModel`・`split_data`)から取るべきだった。adapter の約束の文(docstring)も「compatibility mouth」と書きながら、それを確かめる試験が無かった。
- **同じ種類の探し方**: 「legacy」を返す全ての op(bars・split)で、adapter が呼ぶ口の名を見る。

### 2.8 i4-r1-11(導入を試さず依存の数で再現に置き換えた)
- **根**: 導入の判断の基準に、委任文 §4 に無い「依存の数」を使い、試みの記録(何を試し、どこで止まったか、止めた理由の実測)を残さなかった。
- **同じ種類の探し方**: RUNNABILITY.tsv の「再現した」「走らなかった」の全行の tried 欄を読み、止めた理由が §4 の検査項目・危険・構築の失敗・容量の実測のどれかに当たるかを見る。

### 2.9 i4-r1-13(項目 0 の場面集、i0-r16-05)
- **根**: p2-us-float-held の導き方が「「持つ値にナノ秒より細かい端数がある」float はマイクロ秒では作れない」と範囲を書かずに言う。これは 2^50〜2^51 マイクロ秒の範囲でだけ正しい(小さい時刻では、刻みが 250 ns より細かく、ナノ秒より細かい端数を持つ float がある)。s・ms にある float-subns の形が us に無い。
- **この回の扱い**: 起動文のリードの注記「項目 0 の場面集 tests/bt/battery/item_0/ には触れない」(場面係が並行して直している)に従い、**直さない**。委任文 §0 の L-448 の行は項目 4 の場面係が項目 0 の場面集に触れることを「してよい」とするが、せよとは言わないので、リードの注記と食い違わない。直すなら: `_UNIT_PLAN` に `("us", "float-subns", 1.0000001, NO_INT, …)`(`to_nanos(1.0000001, 'us')` が「1.0000001000000000583867176828789524734020233154296875」を持つと断る = 指摘の根拠のコマンド)を足し、p2-us-float-held の導き方の最後の文を「2^50〜2^51 マイクロ秒の範囲の float は」に限る。持ち越しとして報告する。

## 3. どの作りを変えるか

1. **規則の文**(gen_definitions.py の「足の模型の仕様」): **R-O1**(同じ足の中の順。始値の出来事が範囲の出来事より先、時間切れの足の例外 R-H3、範囲の中の順)と **R-M5**(取り逃しに数えるのは R-M2・R-M3 だけ。建玉が閉じて捨てた指値・データの終わりに待っていた指値は数えない)を足す。互換の計算に **L-5**(待つ合図は範囲の出口と時間切れのあと)を足す。protocol の missed_fills の文を R-M5 に合わせる。
2. **i4_scenes.py**:
   - 同じ足の出来事を入力と期待の約定から導く `exit_events`・規則の順 `ORDER_SPEC`・`ORDER_LEGACY`・勝つ出来事とその約定の値 `winner`・`exit_fill` を足す。
   - 出来事の組を固める場面を足す(I4-10・I4-11・I4-12・I4-13・I4-16 に値の場面、legacy と spec の 2 出力の場面 3 つ)。
   - `barriers(scene)`(足 0 の合図・0 でない費用・違う率・判定から見えない費用)を足し、足の観点ごとに障害の無い値の場面を置く。判定から見えない費用を 0 にする(i4-8 の 2 場面の maker の率、i4-9 の 2 場面、i4-16-missed)。SW の足に先頭の足を足し、合図を 1 つずらす(I4-15・I4-17)。
   - I4-2: 全経路の格子(不変条件だけで判定)と、経路ごとの格子、先頭の部分(prefix)との突き合わせ(先読みの不変条件)を足す。taker の正解つきの格子は残す。
   - I4-3: 核の粒度の値の場面(op "delivery": 戦略に届く足と時刻)を 2 つ足す。粒度の対応(核 / 参照実装 / 全体)を `GRANULARITY` に書く。
   - 変形のある場面に `more_controls`(変形が使う機能を正解つきで使う対照)を足す: 合成と宣言したデータの price_rule(F-2 を規則に足す)、事前登録のハッシュつきの「研究」、率の逆指値だけ。
3. **i4_judge.py**: 不変条件を全経路に広げる(執行で決まる建ての率、決済の率は 2 つのどちらか、持ち越し、保有の上限、飛ばさない出口、方向とマスク、prefix の一致)。`calls` の判定を足す。
4. **run_battery.py**: `more_controls` を全部通したうえで変形の断りを数える。格子の場合の期待が無い(不変条件だけ)場合と prefix の組を扱う。
5. **i4_protocol.py**: op "delivery" と `more_controls` と `missed_fills` の文(R-M5)。
6. **adapters/new_impl.py**: legacy の足を `bot.bt.compat.run_backtest`(旧と同じ名前・同じ引数)で、legacy の分け方を `split_data` で取る。op "delivery" を核の公開の口(CoreEngine と Strategy)で書く。**adapters/current_impl.py**: op "delivery" を旧の run_backtest の戦略の口で書く。**opponents/**: op "delivery" を、足ごとに戦略を呼ぶ口を持つ道具では道具が戦略に渡す物から書き、持たない道具では理由を行で書く。
7. **gen_considered.py**: 理由の部分を「確かめた無さ」と「確かめていない」に分け、観点の障害の無い場面のそれぞれに確かめた無さがあるときだけ「持たないと確認した」、ほかは「再現できない」(読んでいない部分の名を書く)。
8. **導入の試み**: lumibot・Hikyuu・zvt を `pip install --dry-run --report` で解決し、解決した全ファイルの大きさを PyPI の公開の情報から足した実測と、そのときの空き容量を記録し(opponents/attempts/)、RUNNABILITY.tsv の tried 欄に書く。
9. **mutant.py**: 変えない(maker の寿命の 1 本ずれ。新しい場面でも壊す場面を試験で数える)。

## 4. 主張の表(この直しが触る主張の族ごと)

| 族 | (a) 主張を場面の入力と実行の記録から導く関数 | (b) 手書きが残る部分と、機械で導けない理由 | (c) 手書きの主張が 1 つでも残っていれば落ちる試験 | (d) 主張を作る機械への mutant の試験 |
|---|---|---|---|---|
| A 同じ足の中の順(i4-r1-02) | `i4_scenes.py: exit_events`(入力の足・合図・設定と、期待の建ての約定から、決済の足で起きうる出来事の集合)、`winner`(規則の順 ORDER_SPEC / ORDER_LEGACY で勝つ出来事)、`exit_fill`(勝つ出来事の約定の値と率)、`pinned_pairs`(場面の集まりが固める順の組) | 規則の順そのもの(ORDER_SPEC・ORDER_LEGACY)と規則の文 R-O1・L-5。順は規則の決めで、入力から導く物ではない。場面の期待の約定は手で書く(`how` の文) | `test_battery_item4.py: test_every_close_is_the_winner_of_its_bar`(全ての足の場面の手書きの決済の足と値が、exit_events と winner と exit_fill から出る値と一致しなければ落ちる)、`test_every_order_pair_is_pinned`(両立する全ての組が spec で、legacy と spec が違う全ての組が legacy で、場面に固められていなければ落ちる) | `test_swapping_any_pair_of_the_order_breaks_a_scene`(順の中の両立する 2 つを入れ替えた順ごとに、手書きの決済と食い違う場面が 1 つ以上あること) |
| B 本題でない障害(i4-r1-05) | `i4_scenes.py: barriers`(場面の入力と判定する鍵から、足 0 の合図・0 でない費用・違う率・判定から見えない費用を列べる) | 観点ごとの「本題」は要件の文の読み(どの観点も最小の場面を持つかだけを見るので、本題の一覧は要らない) | `test_every_bar_viewpoint_has_a_barrier_free_value_scene`、`test_no_scene_sets_a_cost_its_judged_keys_cannot_see` | `test_barriers_names_each_barrier`(障害を 1 つずつ入れた入力で、その障害の名が出ること) |
| C 性質の格子(i4-r1-06) | `i4_scenes.py: property_cases`(種つきの乱数で全選択肢を引く)、`paths_of`(場合の設定から通る経路)、`i4_judge.py: invariants`(観測した約定・損益・資産と入力だけから式で検める)、`prefix_agrees` | 不変条件の式の一覧(I1〜I11。規則の帰結で、式として書く) | `test_property_grids_reach_every_path`(全経路の格子と経路ごとの格子が、各経路を含まなければ落ちる)、`test_invariants_hold_on_the_existing_engine_and_the_hand_answers`(正解つきの格子の正解と、当方の現状の出力で不変条件が崩れれば落ちる) | `test_invariants_catch_each_perturbation`(観測を 1 箇所ずつ壊す mutant(値・数量・足・損益・資産・向き・先読み・保有の上限・飛ばした出口)の全部を捕まえること) |
| D 粒度(i4-r1-07) | `i4_scenes.py: GRANULARITY`(場面の op と reference から粒度 = 核 / 参照実装 / 全体)、`granularity_of(scene)` | 粒度の名の一覧(要件 I4-3 の文の 3 語) | `test_i4_3_has_a_value_scene_at_each_granularity` | `test_granularity_of_names_each_op`(op を入れ替えた場面で粒度が変わること) |
| E 変形の対照(i4-r1-09) | `i4_scenes.py: features(inp)`(入力が使う機能の集合)、`control_features(scene)` | 機能の名の一覧(入力の鍵から機械で出す) | `test_every_variant_feature_is_used_by_a_passing_control` | `test_runner_credits_a_refusal_only_after_all_controls`(対照の 1 つを壊した対象が「正解と一致」にならないこと) |
| F 互換の口(i4-r1-10) | `adapters/new_impl.py: _legacy_bars`・`_legacy_split`(旧の名前・旧の引数の口を呼ぶ) | なし | `test_new_impl_legacy_goes_through_the_old_mouths`(run_backtest と split_data を差し替えて数え、legacy の出力がそこを通らなければ落ちる) | 同じ試験の中で、差し替えた口が別の値を返すと legacy の出力も変わること |
| G 検討表の判断(i4-r1-05・08) | `gen_considered.py: split_reason`・`verified_absence`・`judge_row`(理由の部分を分け、障害の無い場面ごとに確かめた無さを見る) | 「確かめていない」を表す語の一覧(読んでいない・読んだ範囲に無い・再現していない) | `test_considered_rows_rest_on_verified_absence`(「持たないと確認した」の行の理由に確かめていない語だけの場面があれば落ちる)、`test_considered_table_passes_the_checker` | `test_judge_row_changes_with_unread_parts`(確かめた無さを消した入力で判断が「再現できない」になること) |
| H 導入の試み(i4-r1-11) | `gen_considered.py: NOT_INSTALLED`(試みの記録の path と実測の数) | 実測の数(容量)は 1 回の測りの結果で、場面の入力からは出ない | `test_runnability_records_an_attempt_for_every_reproduction`(再現した全候補の tried 欄が、試みの記録の path か §4 の理由の語を持たなければ落ちる) | なし(記録の有無だけの試験) |

## 5. リードに聞くこと

- なし(リードの答えの内容は変えていない)。


## 6. 直した根拠(指摘 1 件ごと。ファイル:行、コマンドと出力)

`<B>` = `tests/bt/battery/item_4`。走らせ直しの出力・比較の出力・直す前に落ちた試験の出力の写しは
`docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-1/`(before_fix_pytest_battery_and_critic.txt = 直す前 40 failed, 39 passed /
after_fix_pytest_battery_and_critic.txt / rerun_all_targets.log / rerun_classes_by_target.tsv / compare_before_after.tsv / check_bt_considered.out /
fingerprint_tracked_files_after.txt / run_all_r2-1.sh)。

### i4-r1-02(同じ足の中の順)
- 規則: `<B>/gen_definitions.py` の「足の模型の仕様」に **R-O1**(同じ足の中の順)・**R-M5**(取り逃しの数え方)、「互換の計算」に **L-5** を足した
  (生成した DEFINITIONS.md の 87〜100 行・127〜129 行)。①〜⑦ の順のうち、始値の出来事が範囲の出来事より先なのは R-T1 の「始値」から導き、
  ④ 逆指値が先は R-P3、② の中の逆指値が先は R-H3、⑤ → ⑥ → ⑦ は既存の文書に無く既存の計算の順に置いた(ここは legacy と spec が同じ。§8 の 1)。
- 機械: `<B>/i4_scenes.py:210-217`(EXIT_EVENTS・ORDER_SPEC・ORDER_LEGACY・NEVER_TOGETHER・SAME_FILL)、`:259 exit_events`・`:290 winner`・
  `:295 exit_fill`・`:341 order_findings`・`:377 order_pairs`。
- 場面: spec の値の場面 i4-10-signal-first(`:1287`)・i4-10-signal-first-short・i4-10-stop-first-plain・i4-12-tp-before-maker-tp・i4-11-wick-first・
  i4-11-wick-before-exit-limit・i4-13-stop-on-time-bar・i4-13-time-first・i4-13-time-before-exit-limit・i4-13-stop-on-time-bar-maker・
  i4-16-stop-before-exit-limit・i4-16-tp-before-exit-limit・i4-16-maker-tp-before-exit-limit、legacy と spec の 2 出力の場面
  i4-10-signal-first-two-models(`:1305`)・i4-13-time-first-two-models・i4-13-time-maker-tp-two-models、参照実装の場面 i4-3-ref-signal-first(`:1434`)。
- 同じ根の全箇所: 起きうる出口の組 20 組の全部(両立しない 5 組と、どれも始値の taker で同じ約定になる 3 組 = wick/time/signal を除く)を
  spec の順で、legacy と spec で順が違う 5 組を legacy の順で、場面が固める。既存の全場面の手の決済(round trip の全部)も同じ機械で検めた:
  `test_every_close_is_the_winner_of_its_bar` が 0 件の食い違い。順の 2 つを入れ替えた順ごとに食い違う場面がある(`test_swapping_any_pair_of_the_order_breaks_a_scene`、
  20 組 × spec と、違う 5 組 × legacy)。この入れ替えの試験で (time, signal)・(wick, signal) が同じ約定になることが見つかり、SAME_FILL に入れた(最初の版の
  「22 組」は誤りで、DEFINITIONS.md の文も 20 組に直した)。
- 批評家の試験: `tests/bt/critic/item_4/test_i4r1_scene_set_coverage.py::test_a_scene_pins_a_pending_signal_against_an_intrabar_exit` は直す前に落ち、
  直したあと通る(materials の before / after)。
- 実装の側: 新実装(spec)と参照実装は、この起動の作業者の直しのあと全 67 場面で正解と一致(`survey_results/new_impl.tsv`)。当方の現状(旧エンジン)は
  L-5 の 6 場面で「不一致」(`<B>/test_battery_item4.py` の DEVIATIONS に足し、その 13 場面以外の一致を毎回確かめる)。

### i4-r1-05(本題でない障害)
- 機械: `<B>/i4_scenes.py:416 barriers`(足 0 の合図・0 でない費用・違う 2 つの率・判定から見えない費用・費用 0 の場面の損益と資産の判定)。
- 直した場面: 判定から見えない費用を 0 にした(C_TAK の maker の率 `:494`、C_E の maker の率 `:501`、i4-9 の 2 場面 `_CM`・`_CMS` `:1009`・`:1020`、
  i4-16-missed `_CMF` `:1183`、I4-2 の格子は `trim_costs` `:586`)。SW の足に平らな足 0 を足して合図をずらした(`:1161`、I4-15・I4-17)。
  新しい順の場面は全部 費用 0・足 0 に合図なし・判定は約定(と取り逃し)だけ(`_WO`・`_WOM` `:1278`)。i4-12-refuse は費用を損益で見るようにした。
- 同じ根の全箇所: 足の観点 I4-8〜I4-17 の全部に障害の無い値の場面がある(`test_every_bar_viewpoint_has_a_barrier_free_value_scene`。各観点の場面の名は
  `python3 -c` で列べた: I4-8 i4-8-no-short / I4-9 i4-9-strict・i4-9-short-strict / I4-10 3 場面 / I4-11 4 / I4-12 1 / I4-13 4 / I4-14 1 / I4-15 2 /
  I4-16 4 / I4-17 1)。判定から見えない費用を置いた場面は 0(`test_no_scene_sets_a_cost_its_judged_keys_cannot_see`)。
- 検討表: 「持たないと確認した」は、観点の障害の無い値の場面のそれぞれに確かめた無さがあるときだけ(`<B>/gen_considered.py:231 judge_row`)。
  足 0・違う率の理由は確かめた無さに数えない(`BARRIER_WORDS`)。結果: 走らせ直しで Backtrader・backtesting.py・PyBroker が I4-10・I4-12・I4-13 の障害の無い
  場面で「正解と一致」になり、その観点の「動かせた候補」に入った(CONSIDERED.md の各観点の「動かせた候補」の行)。
- 批評家の試験: test_a_value_scene_without_a_bar_0_signal[I4-10/12/13/15/17]・test_the_stop_priority_viewpoint_has_a_scene_with_one_fee_rate が通る。

### i4-r1-06(性質の場面が taker だけ)
- `<B>/i4_scenes.py:668 property_cases`・`:617 paths_of`・`:700 i4-2-grid-all`(全経路 24 の場合 + 先頭の部分)と経路ごとの格子 7 つ。
  不変条件は `<B>/i4_judge.py:117 INVARIANTS`(I1〜I12)・`:140 invariants`・`:227 _skipped_exits`・`:274 _skipped_entries`・`:323 prefix_diff`。
  I2 は「建ての数量 = 発注額 / 建値」を外して数量の保存だけにした(建値で数量を決めない道具が、経路ごとの格子で数量の決め方(R-A1、正解つきの場面の
  観点)だけで落ちたため = 本題でない障害。R-A1 は i4-2-grid と正解つきの場面で見る)。
- 当方の現状・新実装: 全 9 格子で正解と一致。何もしない対象・1 箇所ずつ壊した観測(値・数量・足・向き・損益・資産・何もしない・建玉を残す・先頭の部分だけ違う)は
  全 9 格子で不一致(`test_invariants_catch_each_perturbation`)。試金石は i4-2-grid-all でも不一致(`survey_results/mutant.tsv`)。
  Backtrader の経路ごとの格子で、同じ足で逆指値と合図の決済が両方約定する二重の決済が不変条件 I1 で見つかった(道具の振る舞い。表の不一致)。
- 批評家の試験: test_the_property_grid_reaches_the_path[6 件] が通る。

### i4-r1-07(核の粒度)
- `<B>/i4_scenes.py:468 GRANULARITY`・`:471 granularity_of`、場面 i4-3-core-delivery(`:1419`)・i4-3-core-delivery-gap・i4-3-ref-signal-first(`:1434`)。
  規則 C-1(DEFINITIONS.md 149 行〜)。判定は見えた物の移り変わり(`<B>/i4_judge.py:343 views`)。最初の版は呼び出しの回数も数えていたが、暦の毎分で
  戦略を呼ぶ道具(zipline-reloaded・ziplime・qf-lib)が本題(先の足が見えない・足を飛ばさない)でない回数で落ちたので、見えた物の移り変わりに直した。
- op "delivery" を protocol に足し、当方の現状・新実装(核の CoreEngine と Strategy)・足ごとに戦略を呼ぶ口を持つ調査結果の側の道具 14 の adapter に書いた(戦略を呼ぶ口の無い 3 つ = Luczinsritter・PineForge(構築物が消えている)・prediction-market-backtester と、口の無い軽い adapter 9 つ・再現 13 は理由を返す)。
  走らせ直しで一致: 当方の現状・新実装・Backtrader・Basana・PyAlgoTrade・PyBroker・qf-lib・quanttrader・rqalpha・VnPy・ziplime・zipline-reloaded。
  不一致: backtesting.py(足 0 で戦略を呼ばない)・bt(先頭に 1 行足した表を渡す)・QTradeX(最初の足を渡さない)・vectorbt(順の関数に全部の足の配列を渡す)。
- `test_i4_3_has_a_value_scene_at_each_granularity`・`test_delivery_answers_follow_c1`。

### i4-r1-08(読んでいないことを数えた)
- `<B>/gen_considered.py:202 UNVERIFIED`・`:206 ADAPTER_WORDS`・`:214 verified_absence`・`:231 judge_row`。再現は行を引いた「無い」だけを、venv で動かした道具は
  道具を呼んだ adapter の答え(adapter 自身の選び = 「この adapter は…」を除く)を確かめた無さに数える。「持たないと確認した」の理由には確かめた無さの部分だけを書く。
- コマンドと出力: `awk '/^### 観点/{vp=$3} /\| 持たないと確認した \|/ && /読んでいない|読んだ範囲に無い/{print NR, vp}' <B>/opponents/CONSIDERED.md | wc -l` → 0
  (指摘の時点では 22 行)。`python3 scripts/check_bt_considered.py <B>/opponents/CONSIDERED.md --write` → 「OK 誤り 0 件」。

### i4-r1-09(変形の対照)
- `<B>/run_battery.py:145`(more_controls を全部通ってから変形の断りを数える。対照を拒めば「対応なし」)。
- `<B>/i4_scenes.py:966`(i4-6-signal-refused: 合成と宣言した bf の約定に price_rule、F-2 の手の計算)・`:975`(i4-6-research-refused: 事前登録の
  ハッシュつきの研究)・`:1076`(i4-11-refuse-stack: 率の逆指値だけ)。`features`・`control_features`(`:445`・`:460`)で、変形の使う機能が全部対照で
  使われることを検める(`test_every_variant_feature_is_used_by_a_passing_control`)。対照を 1 つ拒む偽の対象は「正解と一致」にならない
  (`test_runner_credits_a_refusal_only_after_all_controls`、3 場面)。新実装は 3 場面とも正解と一致(対照 2 も通る)。

### i4-r1-10(互換の口)
- `<B>/adapters/new_impl.py:111 _legacy_bars`(`run_backtest`・`CostModel` と旧の Strategy の口)・`:157 _legacy_split`(`split_data`)・`:245`。
- `test_new_impl_legacy_goes_through_the_old_mouths`(口を数えて 1 回ずつ、口を差し替えると legacy の出力が変わる)。

### i4-r1-11(導入の試み)
- `opponents/attempts/i4_r2-1_scenekeeper_install_size_measure.txt`: `pip install --dry-run --ignore-installed --report` の解決 = lumibot 320 ファイル 572.3 MiB、
  hikyuu 104 ファイル 470.5 MiB(PySide6 の 2 本で 243 MiB)、zvt 57 ファイル 121.4 MiB。測ったときの空き 826,646,528 バイト(`df -B1 /`、08:44Z)。
  取得の大きさで空きの 15〜73 % で、展開後はさらに大きく、並行する役の作業(第 17 周に空きが 19 MB まで落ちた実測)を止めるので導入を止めた。
  RUNNABILITY.tsv の 56・60・67 の tried 欄(`<B>/gen_considered.py:384 MEASURED`)。`test_runnability_records_an_attempt_for_every_reproduction`。
- 導入前の検査(PyPI と GitHub の一致など)は、導入しないので行っていない(解決と大きさの取得は PyPI の公開の情報を読むだけ)。

### i4-r1-13(項目 0 の場面集)
- 直していない(§2.9。リードの注記「項目 0 の場面集 tests/bt/battery/item_0/ には触れない」)。直し方は §2.9 に書いた。持ち越し。

## 7. 提出前の吟味(委任文 §3「提出前の吟味」(1)〜(6))

1. 読み直した物: 固定した要件(REQUIREMENTS.md §2 の I4-1〜I4-20)・場面集の規則 1〜9・この回の指摘 9 件。根拠は §6。
2. 同じ根の全箇所: §6 の各項の「同じ根の全箇所」。場面の全 67・格子の全場合・検討表の全行を機械で検めた(試験の名は §4)。
3. 試験: `PYTHONPATH=src python -m pytest -p no:cacheprovider -o tmp_path_retention_policy=none tests/bt/battery/item_4 tests/bt/critic/item_4` →
   「200 passed」(直す前は 40 failed, 39 passed)。
   `tests/bt` の全体(上の批評家の試験の 1 本を --ignore)も 1 回回した: この項目の場面集の試験のうち `test_runner_credits_a_refusal_only_after_all_controls`
   の 3 件が、ほかの項目にも `run_battery` という名の module があるため名前で import すると別の物を読んで落ちた → path で読む形に直し
   (`_load(HERE / "run_battery.py", ...)`)、項目 0 の場面集と一緒に回して通ることを確かめた。ほかに 1876 件が `FileNotFoundError: /tmp/pytest-of-root/pytest-487`
   で止まった(並行する実行が pytest の一時の場所を消した。場面集の変更とは関わらない。記録 `<S>/i4_r2-1_scenekeeper/pytest_bt_all_r2-1_scenekeeper.log`)。
4. 非常に厳しい批評家なら何を [止める] にするか(列べて潰した物 / 残る物):
   - 同じ足の順の決めのうち ⑤ → ⑥ → ⑦ は文書に無く既存の計算に合わせた: legacy と spec が同じ所だけで、新実装に有利な向きの決めではない(両方に同じ答え)。
     文で明記した(R-O1)。**残る**: この決めが要件の文から出ないことはリードに見せる(§8 の 1)。
   - 核の粒度の場面が「呼び出しの回数」で暦の毎分の道具を落とす偏り → 見えた物の移り変わりに直した(§6 i4-r1-07)。
   - 経路ごとの格子が数量の決め方で道具を落とす偏り → I2 を数量の保存に直した(§6 i4-r1-06)。
   - 費用 0 の場面で損益を判定し、決済ごとの損益を出さない道具(VnPy・zipline-reloaded)を落とす偏り → 順の場面の判定を約定だけにし、barriers に足した。
   - 調査結果の側の adapter の弱さ: ziplime の adapter は指値・逆指値の口(LimitOrder / StopOrder)を使わず成行だけを送る(r1 からの物)。検討表ではこの部分を
     「確かめた無さ」に数えず「再現できない」にした。**残る(持ち越し)**: adapter に指値・逆指値を書き足すこと。
   - 批評家の試験 `tests/bt/critic/item_4/test_i4r1_pending_signal_before_intrabar_exit.py` は `from new_impl import TARGET` を名前で import するので、
     `pytest tests/bt`(全体)で項目 0 の批評家の試験が先に `tests/bt/battery/item_0/adapters/new_impl.py` を `new_impl` として読み込むと、収集で
     ImportError になり全体が止まる(`--collect-only -q tests/bt/critic` で再現。項目 4 の場面集の変更とは関わらない)。批評家の試験なので変えない(規則 8)。
     **次の周の批評家に渡す**(直し方: `importlib.util.spec_from_file_location` で別の名前で読む)。
   - 作業者の試験 `tests/bt/item_4/test_i4_battery_scenes.py` は新しい op "delivery" の場面を作業者の driver で走らせる。この起動の途中の走行では 2 件が
     落ちたが、作業者が driver に op "delivery" を書き足した(`tests/bt/item_4/i4w_drive.py` 99 行)。場面係は触れていない。
5. 場当たりでないか: 指摘の文言(I4-10 の手数料・足 0)だけを直さず、障害を名前にする機械と観点ごとの試験を置いた。順は 1 組でなく起きうる全 20 組を固めた。
   性質の格子は経路を 1 つずつと全経路を置いた。
6. 敵対者の格子の試験(先に書いた): `<B>/test_battery_item4_claims.py` の `test_exit_events_grid`(単独の出口の集合 8 と起きうる組 20 のうち重ならない 19、計 27 の集合 × 買い建て・売り建て =
   54 の場合)・`test_order_matches_the_rule_text`(規則の文から書いた表との突き合わせ 20 組)・`test_invariants_catch_each_perturbation`(9 格子 × 9 種の壊し方)。
   列に入れなかった物は同じファイルの冒頭に書いた(3 つ以上の同時の出口・始値が水準を越える足・4 以外の足の出口・0 でない費用・2 以外の建ての足 /
   全部の恒等式を保つ壊し方)。

## 8. 持ち越しとリードに見せる物

1. R-O1 の ⑤ → ⑥ → ⑦(率の利確 → maker の利確 → 待つ決済の指値)は、既存の文書に無く既存の計算の順に置いた決め(オーナーの逐語にもリードの答えにも無い)。
   legacy と spec が同じ所なので、新実装と当方の現状の比べには効かない。違う順が要るならリードが決める。
2. i4-r1-13(項目 0 の p2-us-float-subns)は直していない(§2.9)。
3. ziplime の adapter の指値・逆指値(§7 の 4)。
4. 批評家の試験の import の名前のぶつかり(§7 の 4)。
5. 前の版からの持ち越し(definitions_review.md の「持ち越し」1〜4)は変わらず。

## 9. `git diff --name-only HEAD`(返す前、2026-09-26。この起動の途中でリードのチェックポイントのコミット d703870・e96c378 が入ったので、差分はその後の分)

```
docs/AUDITOR/TRACE/2026-09-26_220780c0.json
docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-1/after_fix_pytest_battery_and_critic.txt
tests/bt/battery/item_4/ROOTCAUSE_r2-1.md
tests/bt/battery/item_4/test_battery_item4_claims.py
```

- `tests/bt/battery/` の外の 2 行: `docs/AUDITOR/TRACE/2026-09-26_220780c0.json` はハーネスの記録(① TRACE。場面係は書いていない)。
  `docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-1/` は起動文の記録の規則「場面係は「直す前に落ちた試験の出力」「走らせ直しの出力」
  「比較の出力」の写しを docs/DISCUSSIONS/2026-09-23_backtest_env/item_<N>/battery/materials/<回>/ に置く」による写し(最後の試験の出力)。
- 実装(`src/bot/bt/`)・作業者の試験(`tests/bt/item_4/`)・項目 0 の場面集(`tests/bt/battery/item_0/`)には触れていない(チェックポイントの前の差分に
  出ていた `src/bot/bt/`・`tests/bt/item_4/`・`docs/.../item_4/round_2/` は並行する作業者の物)。
