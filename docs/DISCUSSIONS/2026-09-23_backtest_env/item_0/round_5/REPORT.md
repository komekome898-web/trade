# 作業者の報告(作る:0#5、agent a77c425d9138c4ad8。Workflow の記録の返り値から逐語で書き出し)

## 変えたファイル

- src/bot/bt/core/window.py
- src/bot/bt/core/values.py(新規)
- src/bot/bt/core/api.py
- src/bot/bt/core/events.py
- src/bot/bt/core/engine.py
- src/bot/bt/core/contract.py
- src/bot/bt/core/__init__.py
- tests/bt/item_0/test_bt0_future_position.py(書き直し)
- tests/bt/item_0/test_bt0_values.py(新規)
- tests/bt/item_0/test_bt0_time_span.py(新規)
- tests/bt/item_0/test_bt0_scene_set.py
- tests/bt/item_0/test_bt0_extension_points.py
- docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/round_5/ROOTCAUSE.md(新規。直す前に書いた)

## 足した試験の数

80

## 試験のコマンド

PYTHONPATH=src python -m pytest -p no:cacheprovider tests/bt/item_0 tests/bt/critic/item_0 tests/bt/battery/item_0(項目 0・批評家・場面集)/ 全試験: setsid nohup env PYTHONPATH=src python -m pytest -p no:cacheprovider > /tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/pytest_item0_r5_worker.log 2>&1 &

## 試験の末尾の行

項目 0・批評家・場面集: 「1 failed, 492 passed in 61.22s (0:01:01)」/ 全試験(ログ scratchpad/bt/pytest_item0_r5_worker.log): 「1 failed, 3379 passed, 4 skipped, 1 warning in 481.54s (0:08:01)」。どちらも落ちたのは同じ 1 件 tests/bt/critic/item_0/test_i0r2_battery_p5_grading.py::test_single_input_form_of_hand_over_order_agrees_with_keeping_one_input_in_order だけ(grep "^FAILED" で確かめた)。この 1 件は核を変える前の版(HEAD の src を git archive で取り出して PYTHONPATH に置いた)でも同じく落ちる(「1 failed, 1 passed」)。原因は場面係が作業中の採点の変更(run_battery.correctness が対象の名前 target を取り、P0-5 の規則を stated_rules.py から当てる形。adapter が出す stated_rule は読まなくなった)で、試験は target を渡していない。場面集の規則 8 に従い、批評家の試験は変えていない。足した試験 80 件の内訳: test_bt0_future_position.py 14 → 37(+23)、test_bt0_values.py 39(新規)、test_bt0_time_span.py 17(新規)、test_bt0_scene_set.py +1。

## 要件の各行を満たした根拠(ファイル:行)

- 合意した完了の形(委任文 §0 の逐語):「すべてが調査結果以上の信頼性と再現性に優れたものにすること。」根本原因は直す前に docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/round_5/ROOTCAUSE.md に書いた(指摘ごとに「なぜ起きたか」と「どの構造を変えるか」)
- 時刻は UTC の int64 ナノ秒: src/bot/bt/core/time.py:54(TIME_CONTRACT)・:74(validate_nanos。int64 の外・小数・真偽値を断る)・:103(to_nanos。単位の札つきの変換)。この周に足した実行の時刻の範囲: src/bot/bt/core/engine.py:360(_validate_time_span)・:376(_check_in_span)・:428(入力の流れを読む所で両方の時刻を検める)・:512(与えなければ defaults_used に time_span が載る)。試験 tests/bt/item_0/test_bt0_time_span.py(秒・ミリ秒・マイクロ秒 × 取引所の時刻・受け取った時刻の 6 通りが断られる。秒の流れを混ぜた実行は、何も届く前に止まる)
- 事象の型(約定・板の写真・板の差分・足・資金調達・清算・時計・注文の受付/拒否/約定の通知): src/bot/bt/core/events.py:187・224・235・248・285・297・315・325・336・349・368・384・401(ALL_EVENT_CLASSES)。この周に足したこと: 通知の文の欄を str で検める(events.py:331・344・379・397)。全ての事象型がハッシュの取れる値であることを tests/bt/item_0/test_bt0_values.py::test_every_event_type_is_a_value で確かめる
- 戦略は「受け取れた時刻 ≤ 今」の事象しか見られない(構造): 時刻の引数が今より後なら LookAheadError(src/bot/bt/core/api.py:576 _time_arg)。位置の規則はこの周に表 1 つにした: src/bot/bt/core/window.py:37(POSITION_RULE)・:46(_check_bound)・:58(DeliveredEvents)。[4:]・[4::2]・[len:]・[4:4]・[:4:-1] も FuturePositionError で断る。試験 tests/bt/item_0/test_bt0_future_position.py: 実装の表を読まない正解(素のタプルで確かめる)と、長さ 0〜6 の全部の区間(端 None・-9..9、歩幅 None・±1・±2・±3)を突き合わせる。前の周の式をこの正解に当てると 2,219 通りを素通りさせていた(scratchpad/bt/item0_r5_worker_oracle_vs_old.py の出力)。批評家の試験 test_i0r4_open_slice_from_next_position.py は 6 件とも通る
- 決定的な事象の順序(同時刻の並びの規則を明記): src/bot/bt/core/ordering.py:96(TYPE_ORDER)・:112-116(段)・:132(_PATHS)・:160(ORDERING_RULE)・:181(merge_key)。この周は変えていない。i0-r3-09 の試験(test_bt0_paths_rule.py・test_bt0_channels.py)は通る
- 戦略の API(事象ごとの呼び出し・発注・取消): src/bot/bt/core/strategy.py:12(on_event)・src/bot/bt/core/api.py:546(place_order)・:552(cancel_order)・:556(set_timer)・:600(STRATEGY_API)。この周に足したこと: 送った物は値になった(api.py:112 extra_dict・:118 _frozen_extra、src/bot/bt/core/values.py:101 freeze・:139 thaw)。試験 test_bt0_values.py(送ったあとに戦略が中身を変えても、届いた時刻に取引所の側が受け取るのは送った時点の中身。取引所の側が変えても、戦略の見る注文と結果の記録は変わらない)。批評家の試験 test_i0r4_order_extra_mutated_in_flight.py は 2 件とも通る
- 他項目が差し込む口(約定模型・遅延模型・費用・口座): src/bot/bt/core/interfaces.py:112・132・152・159・185(SOCKETS)、engine.py:504(_require_protocol)。取引所の側の報告の文の欄の検査: engine.py:228-241(_VenueLedger.apply。str でなければ VenueProtocolError)
- 機械で読む契約: src/bot/bt/core/contract.py:30(position_rule)・:52(lifecycle)・:63(channel_payloads)・:70(run_settings)。CORE_VERSION を core-8 に上げた
- P0-1〜P0-7 の場面: 資料係の adapter で新実装を全場面に通した結果、32 / 32 が「正解と一致・2 回の実行で同じ」(PYTHONPATH=src python3 tests/bt/battery/item_0/run_battery.py --target new_impl --out scratchpad/bt/item0_r5_worker_battery_new_impl.tsv)。試金石(mutant)は p4-received-time だけが不一致のまま(mutant.py --check → changed scenes: ['p4-received-time'] OK)。当方の現状(current_impl)は 10 / 32 が一致
- i0-r3-01(1 歩の途中の例外のあとも走る): 第 4 周の寿命の状態(engine.py:630 _usable・:646 step)のまま。批評家の試験 test_i0r3_resume_after_exception.py と作業者の test_bt0_lifecycle.py は通る。この周に足した範囲の検査も、1 歩の中で出た例外でエンジンを「失敗」にする(test_bt0_time_span.py::test_a_refused_event_later_in_the_run_leaves_the_engine_failed)。報告の文の誤りも同じ(test_bt0_values.py::test_a_report_whose_text_is_not_text_is_refused_at_the_venue が EngineFailedError を確かめる)
- i0-r4-07([示唆]): extra の形(2 つ組・鍵は空でない文字列・鍵の重複なし)を、作る時に検めるようにした(api.py:118)。試験 test_bt0_values.py::test_the_shape_of_extra_is_checked_when_the_request_is_made
- 作業者の試験のうち書き直した主張(規則 8: 設計を変えたときに書き直してよいが報告に書く): (a) test_bt0_future_position.py の「[4:] は空を返す」(旧 :77・:87)を消し、「届いた範囲の読み出し」を [3:]・[:3:-1]・[3:3] に替えた。理由: この周の位置の規則では [4:] は未来を名指す。(b) 同じファイルの種つき乱数の試験(旧 :102-132。正解が実装の式の写しだった)を消し、実装の表を読まない正解との総当たりの試験 2 本に替えた。(c) test_bt0_extension_points.py の defaults_used の期待に「time_span」を足し、4 つの口を全部与える試験では time_span_ns も与える形にした。(d) test_bt0_scene_set.py の p5 の driver から、adapter が書いていた規則の欄(stated_rule)を消した。理由: 場面係の直しで runner が読まなくなったため。採点には target="new_impl" を渡す

## 満たせなかった行とその理由

- なし。要件の表の各行と P0-1〜P0-7 は下の根拠で満たした。資料係の adapter(tests/bt/battery/item_0/run_battery.py --target new_impl)でも、32 場面すべてが「正解と一致・2 回の実行で同じ」になった(出力は scratchpad/bt/item0_r5_worker_battery_new_impl.tsv)。ただし i0-r4-06([直す])の直しは、範囲を与えた実行だけで断る形にした。与えない実行は今までどおり全部の int64 を受け、そのことを defaults_used に記録する。既定で下限を置かない理由: 核の規則「全ての int64 は時刻」(test_bt0_no_time_sentinel.py、i0-r2-01)と、場面集の側・既存の試験が小さい時刻や負の時刻を使っていること。範囲を必須にするかはリードに聞く(「リードに聞くこと」2)。

## 外部の道具を入れたときの §4 の検査の結果

入れていない(この周は外部の道具を導入も実行もしていない。ネットワークも使っていない)。

## リードに聞くこと

- 1. 委任文の指紋が食い違っています。起動文の指紋は 362bf666dfac で、これはコミット ebbaf34 の版です。作業木の今の版は c9e8800bf176(コミット 9b42123)です。git diff ebbaf34 9b42123 で見た差は、通過の判定の定義(部品は同等以上・項目 13 は圧倒、L-431・L-432)と L-429 の注記だけで、作業者の手順(§2〜§4・§6)には触れていません。今の版を全 159 行読み、その指示に従いました。どちらの版を正とするかはリードが決めてください。
- 2. i0-r4-06: time_span_ns は任意の設定にしました(与えなければ defaults_used に「time_span」が載る)。必須にすると、場面集の adapter・批評家の試験・既存の試験がどれも CoreEngine を範囲なしで作っているので、全部が落ちます(私の持ち物ではないので直せません)。項目 1(データ層)・8(再現性)・13(統合)で実データを通すときに範囲を必須にするか(たとえば、それらの層の入口で必須にして核に渡す)を決めてください。
- 3. 場面係が作業中の直しで、採点が対象の名前 target を取る形になりました。そのため批評家の試験 test_i0r2_battery_p5_grading.py::test_single_input_form_of_hand_over_order_agrees_with_keeping_one_input_in_order は、核に関係なく落ちます(核を変える前の版でも同じく落ちることを確かめました)。規則 8 に従い変えていません。次の周の批評家が直すか、取り下げるかを決める件です。作業者自身の試験 test_bt0_scene_set.py は、採点に target="new_impl" を渡す形に合わせました。あわせて、場面係の写した規則(stated_rules.py の new_impl)と、核の ORDERING_RULE["source_merge"] を手で当てた並びが一致することを確かめる試験を足しました。
- 4. i0-r4-02 の直しで、OrderRequest.extra に入れられるのは値のデータだけになりました(None・bool・int・float・complex・str・bytes・Decimal・Fraction と、値が素の数・文字列の列挙の値。それらを入れたタプル・リスト・辞書・集合)。関数・任意のオブジェクト・numpy の数・bytearray は、作る時に OrderApiError で断ります。項目 2(注文の種類を extra で運ぶ見込み)はこの範囲で表す必要があります。numpy の数は float() などで変換する必要があります。この範囲でよいか、確認をお願いします。

## この周で変えた構造

(1) 読み出しの位置の規則を、端の役(添字・前向きの始点・前向きの終点・後ろ向きの始点・後ろ向きの終点)ごとの上限の表 1 つ(window.py の POSITION_RULE)から導く形にした。形ごとに手で書いた不等式の並びはやめた。(2) 路を渡る物は、作る時点で中身まで値にする: OrderRequest.extra を作る時に検めて、変えられない値のデータにする(新しい部品 values.py。extra_dict() は毎回新しい写しを返す)。通知の事象の文の欄は str に限る。(3) 実行の設定に時刻の範囲 time_span_ns を足し、入力の事象の時刻をそこに突き合わせる。与えない実行は defaults_used に「time_span」が載る。
