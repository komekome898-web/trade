# 場面集への指摘ごとの根本原因と直し(項目 0、第 r4-1 回の直し、場面係、2026-09-24)

委任文: `docs/DATA/delegations/20260923_backtest_env_prompt.md`(指紋 `362bf666dfac`。`sha256sum | cut -c1-12` で確かめ、全 158 行を読んだ)。
指摘の逐語: 起動文に貼られた監査役の指摘 9 件(i0-r3-02〜08・10・11)と、その全文 `docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/round_3/CRITIC.md`。
合意した完了の形(委任文 §0 の逐語): 「**すべてが調査結果以上の信頼性と再現性に優れたものにすること。**」。この直しで使った委任文の決まり: §3「根本的解決」(直す前に指摘ごとの根本原因と変える作りを書く / 指摘の文言だけに合わせない)、§3「場面集」「場面集の規則」1〜9、「調査結果の側の選び方」「動かせない候補の検討と再現」、§3「要件と判定の固定」(周回の途中で要件を緩めない、後から厳しくもしない)。

**共通の根本原因**: 7 件の [止める] は第 1 周から 3 周続けて同じ原因のまま残った。直接の原因は、場面係が 1 周目の前にしか起こされなかったこと(委任文 §3「場面集」の段落が書く 5 回目の起動の事情、L-426・L-427)。ただし場面集の側にも作りの原因があった: (1) 場面の正解を固定した要件の文から導く手順が無く、「対象が出せそうな値」から書いていた、(2) 採点が adapter の書いた真偽値をそのまま見ていた(adapter が「得られたか」「同じか」を自分で畳んでいた)、(3) 検討表の「上位互換」と「持たない」を、観点の能力の一覧(要件の文)ではなく場面の一覧に写していた、(4) 機械で止める仕組みが、検討表の形(規則 9)と DEFINITIONS の同期にしか無かった。下の各項はこの 4 つのどれを変えたかを書く。

## i0-r3-02 [止める] p4-future-read-attempt の正解が要件より弱い(repeat_of: i0-r2-05・i0-r1-14)

- **なぜ起きたか**: 正解を「未来の値が得られない」と書き、得られない形として「例外・空の結果・拒否」をまとめていた。固定した要件 P0-4 の測り方「実行時エラーか型エラーで止まるか(素通りしたら不合格)」を文から写さず、「未来が漏れない」という別の性質に言い換えていた(上の共通の原因 1)。加えて、adapter が試しの結果を `future_value_obtained` の真偽 1 つに畳んでから返していたので、黙って切り詰めた結果・空の結果・例外の区別が採点に届かなかった(共通の原因 2)。
- **どの作りを変えるか**:
  - 場面の正解を要件の文どおりにした: `{"every_attempt_stopped_by_error": true, "future_value_obtained": false}`(`scenes.py` の p4-future-read-attempt。導き方に要件の逐語を引いた)。
  - adapter は**試しを 1 つずつ**(手段・名指し方 time / position / other・例外の名前か返った値)返すだけにし、採点の値は runner が作る(`run_battery.py` の `GRADERS` と `_grade_future_reads`。場面に `graded_from` の欄を足し、DEFINITIONS に「採点に使う値」として出る)。名指した読み出し(time / position)が 1 つ以上あり、全部が例外で止まったときだけ正解と一致。空・切り詰め・NaN は素通り(不一致)。
  - 試しを記録する部品を 1 つにした(`adapters/common.py` の `Attempts`)。全 adapter(当方の現状・新実装・調査結果の側 16・再現 1)をこの形に替えた。
  - 機械で止める: `test_battery_item0.py::test_p4_only_an_error_on_every_named_read_is_correct`(切り詰め・空・NaN・名指さない読みだけ・other で 104 が漏れる、の各形が不一致になること)。
- **結果**(この周の実行): qf-lib は `get_price(…, 5 本目の日)` が `[100.0, 101.0, 102.0, 103.0]` を黙って返し不一致(指摘のとおり)。zipline-reloaded・backtrader・当方の現状(`shift(-1)` が NaN を黙って返す)も不一致になった。正解と一致は新実装・Basana・hftbacktest・QuantCore。Basana・hftbacktest・QuantCore は、戦略に時刻や位置を取る読み出しの手段が無く、戦略が書く呼び出しがそのまま型エラーで止まったもの(場面の入力に「時刻も位置も取る手段が 1 つも無い対象では…実際に書いて呼び、出た例外を記録する」と書いた)。

## i0-r3-03 [止める] P0-5 に「規則どおりの順」を測る値の場面が無く、事象を落とした対象を正解と一致にする(repeat_of: i0-r2-06・i0-r1-15)

- **なぜ起きたか**: P0-5 の値の場面の正解を「2 回で同じ」(`same_order_in_two_runs: true`)にしていた。これは再現で、要件の「規則どおりの順で処理されるか(値)」ではない。規則は対象ごとに違うので「場面係がエンジンを見ずに 1 つの値を置く」ことができず、置ける値(2 回の一致)に逃げていた(共通の原因 1)。さらに正解が落とした事象を見ていなかった(4 件中 1 件だけ届けた対象が一致)。
- **どの作りを変えるか**:
  - p5-same-time-twice の正解を要件の文から 2 つに分けた: (1) 4 件がちょうど 1 回ずつ届く(`delivered_as_multiset` = 入力の 4 件、場面係が入力から決める値)、(2) 届いた順が**対象が明記した規則**をこの入力に当てた順と同じ(`follows_stated_rule`)。「明記」は要件の文(§1「同時刻の並びの規則を明記」)で、規則が見つからない対象は (2) を満たさない。2 回の一致は表の「再現」の欄で見る。
  - adapter は届いた列と、対象の規則の出所・逐語・その規則を手で入力に当てた列(`stated_rule`)を返すだけ。規則は対象の文書か公開のコードから写し、走らせた結果から作らない(`adapters/protocol.py` の約束事に書いた)。採点は runner(`_grade_stated_rule_once`)。
  - 新実装の規則は `src/bot/bt/core/ordering.py` 43-55 行の説明の逐語、Basana は `core/dispatcher/base.py` 92 行の並べ方の鍵と `core/event.py` 88-92 行の priority、hftbacktest は `data/validation.py` 59-62 行の説明から写した(各 adapter の `_RULE_SOURCE`・`_RULE_QUOTE`)。
  - 機械で止める: `test_p5_same_time_needs_every_event_and_the_written_rule`(落とす・自分の規則に従わない・規則が無い、が不一致)。批評家の試験 `test_i0r2_battery_p5_grading.py::test_dropping_three_of_four_same_time_events_is_not_graded_as_correct` も通る。
- **同じ種類の欠陥を全体で探した**: 「正解が、能力が無くても出る値になっている」を全 32 場面で機械で探す試験を足した(`test_no_expected_is_met_by_a_target_that_reports_nothing_or_zeros`: 何も返さない・全部 0 / 空 / 偽の出力が正解と一致にならないこと)。これで 2 件見つかり、直した:
  - **p7-cost-zero**(正解 `fee: 0.0`): 費用の口が効かない対象でも、既定の費用が 0 なら一致する。場面を **p7-cost-per-unit** に替えた(数量 1 単位あたり 0.375 円の模型に差し替え、数量 2 の成行。正解 0.75。模型が数量を受け取らないと出ない値)。当方の現状は費用の口が約定代金しか受けないので対応なし(`CostModel.fee` に渡る引数を記録して確かめた)。
  - **p5-same-stream-order**(入力 100 → 101、正解 [100, 101]): 価格で昇順に並べ替える対象でも一致する。入力を 101 → 99 → 100 の 3 件にした(昇順でも降順でもない)。試験 `test_p5_same_stream_input_is_not_in_price_order`。
  - 残りの場面の正解は、列を全部書くか(p1・p3 の `sequence`、p3-notice-* の通知の列)、0 でない値を含む(p6-place-then-cancel の 1 → 0 など)ので、この試験を通る。

## i0-r3-04 [止める] p5-hand-over-order の「1 本しか受けない対象」の形の正解が、1 本の入力の順を守る規則と矛盾(repeat_of: i0-r2-07)

- **なぜ起きたか**: 1 つの正解(異なる並びの数 = 1)を、複数の入力を受ける対象と 1 本しか受けない対象の両方に当てていた。1 本の入力では連結の順がその入力の中身そのものなので、順を守れば 24 通りになるのが正しい。形ごとに正解を導いていなかった(共通の原因 1)。
- **どの作りを変えるか**: 正解を形によらない 3 つの値にした: `every_run_delivers_each_once`(24 回とも 4 件が 1 回ずつ)/ `every_run_follows_stated_rule`(24 回とも、その回の入力に対象の規則を当てた順)/ `same_order_whatever_the_hand_over`(複数の入力を受ける形では 24 回が 1 通り。1 本の形では真 = 渡す順がその回の入力そのものなので)。adapter は形(`multi_input` / `single_input`)と各回の列・各回の規則の当てはめを返し、runner が採点する(`_grade_hand_over`)。複数の入力を受ける対象は必ず multi_input で走らせる(場面の入力の注記)。
- **機械で止める**: `test_p5_hand_over_single_input_keeping_its_order_is_correct_and_multi_input_must_not_move`(1 本の形で入力の順を守れば一致 / 複数の形で渡す順で並びが動けば不一致 / 落とせば不一致)と、実の核で 1 本の形を 24 回走らせて採点する `test_single_input_form_is_graded_correct_for_the_core_keeping_one_input_in_order`(24 通りの並びで正解と一致)。
- **批評家の試験への影響**(場面集の規則 8): `tests/bt/critic/item_0/test_i0r2_battery_p5_grading.py::test_single_input_form_of_hand_over_order_agrees_with_keeping_one_input_in_order` は、場面の正解に `distinct_orders` の鍵があることを前提に `sc.expected["distinct_orders"] == 24` を見ている。正解の形を変えたのでこの鍵は無く、`KeyError: 'distinct_orders'` で落ちる。この試験が確かめたかった性質(1 本の形で入力の順を守る対象を正解と一致にする)は、上の 2 つの試験で満たしている。批評家の試験は批評家の持ち物なので変えていない。次の周の批評家が確かめ、書き直すか取り下げる。

## i0-r3-05 [止める] 調査結果の側の adapter が QuantCore の既定の危険の上限を切ったまま(repeat_of: i0-r2-04)

- **なぜ起きたか**: adapter を書くときの約束事(`adapters/protocol.py`)に「相手の既定の守りを外さない」が無く、道具を動かしやすくする設定を全場面に入れても何も止めなかった(共通の原因 4)。
- **どの作りを変えるか**:
  - `opponents/quantcore_adapter.py` の `set_risk_limits(<enabled = False>)` を消し、道具の既定のまま走らせる。既定の値は実測で書いた(`RiskLimits()` → `enabled=True, max_leverage=2.0, max_loss_pct=0.5, max_order_value=0.0, max_position_pct=0.2`)。
  - 約束事に「相手の既定の守り(危険の上限・現金の検査・先読みの守り)を外さない。既定と違う設定は、場面が書いたときか、既定と両方を走らせて両方を記録するときだけ」を足した(`adapters/protocol.py`)。
  - 機械で止める: `test_no_survey_adapter_switches_off_a_protective_default`(`opponents/*.py` に `enabled = False` や `set_risk_limits(` があれば落ちる)。
- **結果**: QuantCore の p3-notice-rejected が不一致 → 正解と一致に変わり、ほかの場面は悪くならなかった(前の周の表と突き合わせた、`item0_r4-1_scenekeeper_diff.py`)。
- **同じ種類を全体で探した**: 全 adapter を grep(`limits\|risk\|= False\|preload\|process_only`)。既定を外して相手を弱める設定はほかに無い。backtrader の `preload` は既定と両方を走らせて良い方を採る(この直しで、両方の試しを detail に残し、選び方を「全部止まった方 → 104 が漏れなかった方 → 既定」と書いた)。ziplime も足の日付の 2 通りを両方走らせる形で同じ。

## i0-r3-06 [止める] 検討表の「上位互換」が能力と合わない場面・中身の無い一致に乗っている(repeat_of: i0-r2-08・i0-r1-16)

- **なぜ起きたか**: 観点の能力を場面の一覧から数え、候補の能力を「近い場面」に写していた(共通の原因 3)。そのため (1) 観点の外の能力(データの取り込み、足の内側の約定の順)を観点の場面に対にし、(2) 観点の中の能力でも、その能力を測らない場面(P0-5 の弱い一致)に対にしていた。能力が観点の中か外かを判断する欄が無かった。
- **どの作りを変えるか**(`opponents/CONSIDERED.md` を全部作り直した):
  - 各観点の冒頭の能力の一覧を**固定した要件の文**(§1 の行と §2 の観点)から書き、各能力を測る場面を書いた。
  - 各行で候補の能力を 1 つずつ、(1) 観点の中 → 測る場面での正解と一致の対、(2) 観点の外 → 「観点の外」と理由(対にしない)、(3) 行に無い能力 → 「在るとしても」観点の残りの能力が全部正解と一致で覆われることを書く。観点の能力のどれかがどの動かせた候補でも正解と一致でなければ上位互換にしない(読み方の節)。
  - 指摘の例: 70 PineForge の「足の内側の道筋から交差の時刻を作る」は約定の模型(項目 3・14)で観点の外とし、P0-5 では決定的な再生(能 4)だけを対にした。16 の `get_data` の差し替えはデータの取り込み(項目 1)で観点の外とし、P0-7 は一次資料で約定の値のメソッド(`get_execution_price`)を確かめて対にした。P0-5 の各行は、i0-r3-03 の直しの後の場面(規則どおり・落とさない)で正解と一致の Basana に対にした。
  - 同じ種類をほかの行でも直した: 37(値段と時刻の優先 = 照合の規則で観点の外)、65(埋め方で観点の外)、13(`Math.min` の約定の量で観点の外)、52 の P0-6 の行(前の版は P0-7 の場面に対にしていた)、11 の P0-7 の行(戦略の 3 段は観点の外)、101・104(板の中の優先・順位で観点の外)。
- **機械で止められない部分**: 能力が観点の中か外かの判断は語の有無では決まらない(規則 9 の道具は語だけを見る)。判断の理由を各行に書き、監査役と批評家が読んで確かめる(規則 9)。

## i0-r3-07 [止める] grep で当たって候補に写せなかった 90 行を検討していない(repeat_of: i0-r2-09・i0-r1-17)

- **なぜ起きたか**: `gen_pool.py` が写せなかった行を `pool.tsv` の末尾に書き出すだけで、それを読む手順も、読んだことを確かめる機械も無かった(共通の原因 4)。写す規則も、SCAN の書き方の一部(道具ごとの段落の頭の名前・番号つきの「知見」の表の続きの行・見出しの名前の書き方の違い)を拾えていなかった。
- **どの作りを変えるか**:
  - `gen_pool.py` に写す規則を 3 つ足した(3b 道具ごとの段落の頭の `**\`名前\`` / 3c 番号つきの表の続きの行は同じ表の前の行の候補 / 見出しの名前は大小・`_`・`-`・空白を無視)。3c は最初に全部の表に当てたところ、`| \`bt\` |` の行を前の行の PyBroker に写したので、行の頭が番号の表だけに限った(`gen_pool.py` の説明に書いた)。規則で写せず道具を指す 2 行(3617・8407)は `READ_BY_HAND` に根拠の行つきで置いた。
  - 写せなかった行(76 組)を、`gen_unmapped_review.py` が `CONSIDERED.md` の節「grep で当たって候補に写せなかった行」に 1 行ずつ書く。種類は SCAN の中の場所で決める(当方のリポジトリの一覧の見出しの下 = 道具を指さない)。それ以外は 1 行ずつ読んで理由を書いた(`bt` の 3 行・調査の手順の文 10 行)。
  - 機械で止める: `test_every_unmapped_line_is_reviewed_in_the_table`(写せなかった行の組と検討の行の組が一致しなければ落ちる)。`test_pool_reproducible` で候補の集まりが生成器から再現することも見る。
- **結果**: P0-4 に候補 16(SCAN 3166 行。3163-3166 行の表で名指し)、P0-7 に候補 63・123(SCAN 8407 行)が加わり、検討表に載せた。16 は一次資料(読むだけ)を読み、P0-4 の 3 つの能力の口が無いことを行で示して「持たないと確認した」にした。`bt` は道具台帳に番号が無い(`awk -F'\t' '$2=="bt"' docs/DATA/tools_catalog.tsv | wc -l` → 0)ので候補の集まりに入らない。台帳から抜けていることはリードに聞く。

## i0-r3-08 [止める] 「持たないと確認した」を調査報告に書かれていないことで決めている(場面集の規則 6)

- **なぜ起きたか**: 「持たない」を観点の能力の 1 つ(多くは約定)について示したところで、観点全体の判断にしていた。観点の能力を全部並べて 1 つずつ根拠を当てる欄が無く、書かれていない能力を「P0-7 の行に無い」で済ませた(共通の原因 3)。
- **どの作りを変えるか**: 「持たないと確認した」は、観点の能力の**全部**について口が無いことを行か一次資料で示したときだけにした(読み方の節)。指摘の 3 件(8 OpenTrader・15 Mendl-Labs・107 sigc)は、約定・遅延・費用・口座のうち行で「無い」と示せるのは一部だけなので、「上位互換」(示せた能力の対 + 行に無い能力も在るとすれば 4 つの対で覆われる)に替えた。同じ種類の 38 MarS も上位互換に替えた。残した「持たない」は 35(核が無い = 4 つの口の全部に当たる 1 つの根拠、8194 行)、87(4 つの口ごとに 7871・8151 行)、P0-4 の 16(3 つの能力ごとに一次資料の行)。
- 8 OpenTrader の (b) 一次資料は読んでいない。遅延・費用・口座の口の有無を決めなくても、上位互換の判断(4 つの口の全部が動かせた候補の正解と一致で覆われる)は変わらないため。

## i0-r3-10 [直す] P0-2 の「他の単位が混入しないこと」を拒否の側から測る場面が無い(repeat_of: i0-r2-12)

- **なぜ起きたか**: 固定した測り方は受け入れの側の一致だけで、拒否の側は場面にすると測り方より厳しくなる(批評家の見立てのとおり、委任文 §3「後から厳しくもしない」)。その境界を場面集のどこにも書いていなかった。
- **どの作りを変えるか**: 場面は足さない。DEFINITIONS の「場面にしていない観点・側面」に、P0-2 の拒否の側を場面にしていないことと理由、この側面は審査員ではなく批評家が見ること(委任文 §3「場面にできない観点は場面係が記録し、審査員ではなく批評家が見る」)を書いた(`gen_definitions.py`)。

## i0-r3-11 [直す] 検討表の冒頭が古い版の委任文の指紋を指す

- **なぜ起きたか**: 版の記録を手で書き写し、委任文の版が進んでも見直す手順が無かった。
- **どの作りを変えるか**: 冒頭を今の版の指紋 `362bf666dfac` にし、前の版から今の版までの差分を確かめたコマンドを書いた(`git diff 8b5dd73 ebbaf34 -- docs/DATA/delegations/20260923_backtest_env_prompt.md`。場面集の規則 1〜9 の行は差分に現れず、変わったのは周回の数え方の段落・L-422・場面集の側の指摘の直し手)。批評家は規則 4・9 が変わったと書いたが、この 2 つの版の間ではその行は差分に無い(`git diff … | grep "^[-+][0-9]\. "` で出るのは周回の数え方の 2〜4 だけ)。場面集の中でほかに版を名指すファイルは無い(`grep -rn "指紋" tests/bt/battery/item_0`)。版の突き合わせを試験にすると、リードが委任文を直すたびに全試験が落ちるので、試験にはしていない。

## この直しで変えたもの(場面係の持ち物)

- 場面: `scenes.py`(p4-future-read-attempt・p5-same-time-twice・p5-hand-over-order・p5-same-stream-order・p7-cost-zero → p7-cost-per-unit。`Scene.graded_from` を足した)/ `DEFINITIONS.md`(`gen_definitions.py` で作り直し)/ `gen_definitions.py`。
- runner: `run_battery.py`(`GRADERS` と `graded_output`。出力の列は採点に使う値 + `raw`)。
- adapter: `adapters/common.py`(`Attempts`・`plain`・`stated_rule`)/ `adapters/protocol.py`(約束事)/ `adapters/current_impl.py` / `adapters/new_impl.py`(資料係の持ち物だが、場面の出力の形を替えたので形だけ合わせた。冒頭に書いた。資料係が読み直す)/ `opponents/*_adapter.py` の 16 本 / `opponents/repro_33_execution_simulator.py`(数量 2 の費用の場面)。
- 結果: `survey_results/*.tsv`(全部走らせ直した。54 finmarketpy はこの周に導入できず、前の周の表を `survey_results/stale/` に移した)。
- 検討表: `opponents/CONSIDERED.md`(作り直し)/ `gen_pool.py` / `pool.tsv` / `gen_unmapped_review.py`(新規)。
- 試験: `test_battery_item0.py`(9 件を足した)。
- mutant: 変えていない。`PYTHONPATH=src python3 mutant.py --check` → `changed scenes: ['p4-received-time']` `OK`。

## 作業者に届く影響

作業者の試験 `tests/bt/item_0/test_bt0_scene_set.py` は場面集を読んで核を採点する。場面の出力の形と正解を替えたので、5 件(`test_every_scene_has_a_driver`・p4-future-read-attempt・p5-hand-over-order・p5-same-time-twice・p7-cost-per-unit)が落ちる。作業者の持ち物なので変えていない。作業者は runner の `run_battery.GRADERS` と同じ採点で見る形に直す必要がある(場面集は読めるが変えない)。

## 試験の結果(この直しのあと)

- 場面集の試験: `PYTHONPATH=src python -m pytest -p no:cacheprovider tests/bt/battery/item_0` → 全部通る(`test_battery_item0.py` 18 件、`18 passed`)。
- 全試験: `setsid nohup env PYTHONPATH=src python -m pytest -p no:cacheprovider > <scratchpad>/bt/pytest_item0_r4-1_scenekeeper.log 2>&1 &` → 末尾の行 `9 failed, 3195 passed, 4 skipped, 1 warning in 474.51s (0:07:54)`。落ちた 9 件: 批評家の試験 `test_i0r2_battery_p5_grading.py` の 1 件(上の i0-r3-04 の `KeyError: 'distinct_orders'`)/ 批評家の試験 `test_i0r3_resume_after_exception.py` の 2 件(実装への指摘 i0-r3-01。この直しの前から落ちている)/ 作業者の試験 `test_bt0_scene_set.py` の 5 件(上の「作業者に届く影響」)/ `tests/test_jev_delegate.py::test_calibrate_dry_run_sends_nothing_and_still_lists_the_delegations` 1 件(この直しの間にリードのコミット `385172e`・`cb52745` が Jev の段の設定と試験を替えた。場面集の持ち物の外で、原因は確かめていない = 未確認)。
- 検討表: `python3 scripts/check_bt_considered.py tests/bt/battery/item_0/opponents/CONSIDERED.md --write` → `OK 誤り 0 件`。
- 定義: `python3 gen_definitions.py --check` → `OK`。
