# 作業者の報告(作る:0#6、agent a05ae2f2d76dcda3d。Workflow の記録の返り値から逐語で書き出し)

## 変えたファイル

- src/bot/bt/core/values.py
- src/bot/bt/core/api.py
- src/bot/bt/core/events.py
- src/bot/bt/core/interfaces.py
- src/bot/bt/core/engine.py
- src/bot/bt/core/window.py
- src/bot/bt/core/errors.py
- src/bot/bt/core/time.py
- src/bot/bt/core/contract.py
- src/bot/bt/core/__init__.py
- tests/bt/item_0/test_bt0_carriers.py(新規)
- tests/bt/item_0/test_bt0_path_senders.py(新規)
- tests/bt/item_0/test_bt0_future_position.py
- tests/bt/item_0/test_bt0_values.py
- tests/bt/item_0/test_bt0_time_span.py
- tests/bt/item_0/test_bt0_paths_rule.py(書き直し。理由は unmet の欄の (1))
- docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/round_6/ROOTCAUSE.md(新規。直す前に書き、§E は直している途中で見つけた同じ根の箇所の追記)

## 足した試験の数

268

## 試験のコマンド

項目 0・批評家: PYTHONPATH=src python3 -m pytest -p no:cacheprovider tests/bt/item_0 tests/bt/critic/item_0 / 全試験(場面集を含む。作業の最後に 1 回だけ): setsid nohup env PYTHONPATH=src python -m pytest -p no:cacheprovider > /tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/pytest_item0_r6_worker.log 2>&1 &

## 試験の末尾の行

項目 0・批評家: 「9 failed, 735 passed, 2 skipped in 66.80s (0:01:06)」。落ちた 9 件は全部 tests/bt/critic/item_0/test_i0r5_battery_opponent_grading.py(批評家が場面集の側に出した i0-r5-02・03・04 の試験。場面係の持ち物で、作業者は直せない)。/ 全試験(ログ scratchpad/bt/pytest_item0_r6_worker.log): 「10 failed, 3656 passed, 6 skipped, 1 warning in 494.39s (0:08:14)」。落ちた 10 件は、上の場面集の側の 9 件と、tests/bt/battery/item_0/test_battery_item0.py::test_definitions_in_sync_with_scenes(場面係が作業中の DEFINITIONS.md と gen_definitions.render() の食い違い。差分は場面の定義の文「場面が測るもの…は、対象の配布物のコードが出したものだけを数える」の段落。核には関わらない)。`grep -E "^(FAILED|ERROR)"` で全行を確かめた。

## 要件の各行を満たした根拠(ファイル:行)

- 合意した完了の形(委任文 §0 の逐語): 「すべてが調査結果以上の信頼性と再現性に優れたものにすること。」根本原因は直す前に docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/round_6/ROOTCAUSE.md に書いた(指摘ごとに「なぜ起きたか」と「どの構造を変えるか」)。
- 時刻は UTC の int64 ナノ秒(P0-2): src/bot/bt/core/time.py:74 validate_nanos(int の子も int そのものとして返す。time.py:86-90)、time.py:54 TIME_CONTRACT、engine.py の time_span_ns の検め(engine.py:517、説明 535 行から。入力の事象だけを検めることを契約 contract.py:104 に書いた)。
- 事象の型(約定・板の写真・板の差分・足・資金調達・清算・時計・注文の受付/拒否/約定の通知、P0-3): src/bot/bt/core/events.py:52 EventType、events.py:196-391 の 12 の class(全部 slots=True の凍結データクラス、events.py:150 ほか)。全部の欄が作る時に組み込みの値になる(events.py の _value・_finite・_choice・_str、試験 tests/bt/item_0/test_bt0_carriers.py)。
- 戦略は「受け取れた時刻 ≤ 今」の事象しか見られない(構造でルックアヘッドを不能にする、P0-4): api.py:497 visible_events(時刻の引数は _time_arg で今より後を断る)、位置の規則は window.py:39 POSITION_RULE と window.py:48 _check_bound、答えの事実 window.py:66 DeliveredEvents と :126・:134 の 2 つの子、api.py:551 で作る所が事実を決める。外れた名指しは、最新で終わる答えなら errors.py:49 FuturePositionError、過去で終わる答えなら errors.py:59 OutsideAnswerError(i0-r5-05)。路を渡る物が値であることは values.py:78 scalar・:95-133 の関数、api.py:182 fresh_request、engine.py:243(報告の class そのもの)・:461(事象の class そのもの)・:881(強制注文)・:815(戦略の見え方には別の物)。
- 決定的な事象の順序(同時刻の並びの規則を明記、P0-5): src/bot/bt/core/ordering.py:160 ORDERING_RULE・:181 merge_key・:118 PHASES、engine.py:726 の待ち行列。流れの名前は組み込みの文字にしてから並べる(engine.py:436)。配達の要約は第 5 周と同じ入力で同じ値(scratchpad/bt/item0_r6_worker_digest_speed.py: 35269aee…)。
- 戦略の API(事象ごとの呼び出し・発注・取消、P0-6): src/bot/bt/core/strategy.py:12 on_event、api.py:602 place_order・:608 cancel_order・api.py:657 STRATEGY_API。発注と取消は核の class そのものだけを受け、取引所の側には作り直した別の物を渡す(api.py:304・:328・:334)。
- 他項目が差し込む口(約定模型・遅延模型・費用・口座、P0-7): src/bot/bt/core/interfaces.py:153 FillModel・:173 LatencyModel・:193 CostModel・:200 Account・:226 SOCKETS。差し込み口の答え(遅れ・手数料・拒否の理由)は返された時に組み込みの値として読む(engine.py:352・:967・:908、契約 contract.py:95 plug_in_answers、試験 test_bt0_path_senders.py::test_plug_in_answers_and_stream_names_are_taken_as_builtin_values)。
- 機械で読める契約: src/bot/bt/core/contract.py:19 PATH_CARRIERS、:45 position_rule.error、:94 carriers、CORE_VERSION は core-9(contract.py:15)。

## 満たせなかった行とその理由

- 満たせなかった要件の行は無い(下の requirement_evidence)。以下は提出前の吟味の記録(委任文 §3「提出前の吟味」(1)〜(5))。
- (1) 指摘 1 件ごとの直した根拠 — i0-r5-01 [止める]: 根本原因は round_6/ROOTCAUSE.md の A。直した根拠: 批評家の試験 `PYTHONPATH=src python3 -m pytest -p no:cacheprovider tests/bt/critic/item_0/test_i0r5_fields_crossing_a_path_stay_live.py tests/bt/critic/item_0/test_i0r4_order_extra_mutated_in_flight.py tests/bt/critic/item_0/test_i0r4_open_slice_from_next_position.py` → 変える前は r5 の試験が `4 failed in 0.08s`、変えた後は 3 本合わせて `12 passed in 0.06s`。同じ根の再現(scratchpad/bt/item0_r6_worker_probe_same_root.py)の変える前 → 変えた後: `side=AnyEq(): [('OrderRequest', 'AnyEq(changed)', False, 1.0)]` → `[('refused', 'OrderApiError')]`、`post_only=LiveBool(): [(…, True, 1.0)]` → `[('refused', 'OrderApiError')]`、`OrderRequest subclass: [('Sub', …)]` → `[('refused', 'OrderApiError')]`、`Fill liquidity AnyEq` → `('run refused', 'VenueProtocolError', 'Fill.liquidity must be a str, got AnyEq')`、データ源の事象に属性を足す → `AttributeError: 'TradeEvent' object has no attribute 'attached'`(slots)。4 つの送り手の試験 tests/bt/item_0/test_bt0_path_senders.py(16 件)は第 5 周の src(HEAD を git archive で取り出し `-o pythonpath=` で差し替え)では `14 failed, 1 passed`(通った 1 件は第 5 周でも安全だった口座の id なしの形)、この周の src では全部通る(記録 scratchpad/bt/item0_r6_worker_senders_on_head.txt)。
- (1) 続き — i0-r5-05 [直す]: 根本原因は ROOTCAUSE.md の B。再現 scratchpad/bt/item0_r6_worker_probe_past_answer.py の変える前 → 変えた後: `2 ('FuturePositionError', True, …)` → `2 ('OutsideAnswerError', False, …)`、`slice(2, None, None) ('FuturePositionError', True, …)` → `('OutsideAnswerError', False, …)`、同じ根の別の形 `reversed[len] ('FuturePositionError', True)` → `('OutsideAnswerError', False)`。試験 test_bt0_future_position.py の test_a_read_cut_in_the_past_names_delivered_events_outside_it(批評家の場面そのもの)・test_the_fact_agrees_with_the_input_at_every_callback(核の規則を読まず、入力の列と呼び出しの時刻から「答えの最後の次の事象は届いていたか」を決めて突き合わせる。1000 回を超える読み出し)・両方の事実での総当たりの oracle(14 件)。i0-r5-07 [示唆] も契約に範囲を書いて試験で固定した(test_bt0_time_span.py::test_the_span_checks_input_events_only_and_does_not_bound_the_run)。
- (2) 同じ根の全箇所: 指摘は OrderRequest の欄・freeze の Enum・逆向きの文字の欄の 3 つだったが、同じ根(型の名前だけを見る検査・欄ごとに手で書く検査・送り手と同じ物を渡す)を全部の運び手の全部の欄に広げた: post_only・reduce_only・time_in_force(検査が 1 行も無かった)、CancelRequest、5 つの報告、FillNotice、12 の事象型の全欄(seq・trade_id・tag・side・liquidity など。`in` の検査は文字でない物を通していた)、validate_nanos(子の __int__ を読んでいた)、timer の tag、口座の強制注文(id を付けると口座の物が戦略の見え方に入っていた)、id を付けた戦略の注文(戦略の物が取引所まで渡っていた)、データ源の事象の子の class と後から足した属性、差し込み口の遅れ・手数料・拒否の理由、流れの名前(ROOTCAUSE.md §E)。欄を名指さない試験 test_bt0_carriers.py で全部の運び手の全部の欄に「子の値」と「何とでも等しい物」を入れて確かめ、核の凍結データクラスで一覧に無いものがあれば落ちる。この試験が足し忘れを捕まえることを変異で確かめた(src の写しで trade_id と reduce_only の扱いを外す → `4 failed, 229 passed`、記録 scratchpad/bt/item0_r6_worker_mutation_carriers.txt)。
- (3) 批評家の試験と場面集の試験: 批評家の試験は tests/bt/critic/item_0 のうち実装の側は全部通る。落ちるのは場面集の側の test_i0r5_battery_opponent_grading.py の 9 件だけで、場面係が同時に直している(作業者は場面集を変えられない)。場面集の実行は作業の最後に全試験の中で 1 回: test_battery_item0.py は test_definitions_in_sync_with_scenes の 1 件だけ落ち、原因は場面係が作業中の DEFINITIONS.md の文の段落(核には関わらない)。別に新実装と試金石を場面集に通した結果(出力は scratchpad だけ): `new_impl: 32 scenes … {'正解と一致': 32}; 2 回で違う=0`、`mutant: 32 scenes … {'正解と一致': 31, '不一致': 1}`。p4-future-read-attempt の新実装の試し 22 件は位置の名指し 16 件が全部 FuturePositionError、時刻 4 件が LookAheadError(答えは最新で終わるので、この周の変更で種類は変わらない)。
- (4) 厳しい批評家なら何を [止める] にするかを列べて潰したもの: (a) 送ったあと object.__setattr__ で凍結を迂回して変える → 戦略・口座の注文は入口で作り直すので届かない(試験 test_strategy_bypassing_frozen_after_sending_reaches_no_one[ ]・[mine]、test_account_forced_order_reaches_venue_and_strategy_as_sent[forced-a])。データ源の事象は作り直さない(1 事象あたり約 2.4 マイクロ秒、核の約 17%)。戦略に届くのは配達の時の写しで、元の物は欄が値で属性を足せず子でもない。データ源が自分の物を迂回して書き換えることは契約の scope に「契約の外」と書いた。(b) slots にして核が遅くなる → copy.copy が 4.4 マイクロ秒かかり 16.2 → 20.3 マイクロ秒/事象になったので、配達の写しを欄ごとの写しに替えて 14.2(第 5 周より速い)。delivery_digest は第 5 周と同じ入力で同じ値 35269aee…(scratchpad/bt/item0_r6_worker_digest_speed.py)。(c) 浮動小数に入らない整数が OverflowError のまま漏れる → 運び手の誤りの型で断る(試験 3 件)。(d) 名前を組み込みの文字に直した結果の重なりを黙って上書き → 断る。(e) DeliveredEvents の事実を作り手が書き忘れる → 既定値なしの必須のキーワードで、class で持つので後から変えられない(試験 test_the_fact_cannot_be_left_out_or_changed)。(f) 契約と説明の文が古い → CORE_CONTRACT の visibility.strategy・position_rule.error・channel_payloads(rule・fields・carriers・plug_in_answers)・run_settings.time_span_ns・scope、api/engine/events/interfaces/values の説明を書き直し、CORE_VERSION を core-9 にした。
- (5) 場当たりの直しでないこと: 試験だけの特別扱い・閾値や既定値のずらし・機能を外すことはしていない。書き直した自分の試験(前の周に作ったもの。規則 8 の後半): test_bt0_paths_rule.py は要求を id(送った物) で見分けていたが、この周の設計で取引所に届くのは戦略が作った物と別の物になる(それが直しそのもの)ため、遅延の模型が送る時に 1 回ずつ呼ばれることを使って、核が運ぶ物に送った順の番号を付ける形に替えた(消した主張は無い。送った数と番号を付けた数が一致することを足した)。test_bt0_values.py の乱数の値から平の Enum の要素を外し(断る側の試験に移した)、IntEnum・StrEnum・float の子を足した。test_bt0_future_position.py は DeliveredEvents を作る時に事実を渡す形に替え、type(x) is DeliveredEvents を isinstance に替えた(具体の class は事実ごとの子になったため)。消した試験は無い。
- 未解消のまま残るもの(作業者の持ち物の外): 批評家の i0-r5-02・03・04([止める]、場面集)と i0-r5-06([示唆]、場面集)は場面係の持ち物。

## 外部の道具を入れたときの §4 の検査の結果

入れていない(外部の道具は導入も実行もしていない。ネットワークは使っていない)。

## リードに聞くこと

- 1. OrderRequest.extra の数の扱いが変わりました: float の子(numpy.float64 を含む)と IntEnum・StrEnum の要素は、中身の組み込みの値(float・int・str)として受けます。平の Enum の要素は断ります(第 5 周は受けていた)。numpy.int64 は int の子ではないので今までどおり断ります。第 5 周の「リードに聞くこと」4 と合わせて、項目 2 がこの範囲で注文の種類を表せるかを確認してください。
- 2. データ源の事象は、入口で核の class そのものかを検めるだけで、作り直していません(作り直すと 1 事象あたり約 2.4 マイクロ秒、核の約 17% 増える)。データ源が自分の渡した事象を object.__setattr__ で凍結を迂回して書き換えることは契約の scope に「契約の外」と書きました。戦略に届くのは配達の時の写しです。これで足りるか、遅くなっても作り直すかを決めてください。
- 3. 全試験で落ちた 10 件は全部場面集の側です(test_i0r5_battery_opponent_grading.py の 9 件と、場面係が作業中の DEFINITIONS.md の食い違い 1 件)。場面係の直しが入ったあとの全試験は、この周の作業者の記録には入っていません。
- 4. この周の作業(src/bot/bt/core と tests/bt/item_0 と round_6/ROOTCAUSE.md)は、作業中にリードの側でコミット c2cbc41("Checkpoint run 7 round 6 work in progress")に入っていました。作業者は git commit をしていません。そのコミットのあとに作業者が変えたファイルは無いことを `git status --short` で確かめました。

## この周で変えた構造

(1) 路を渡る物の値の部品を values.py の 1 か所(as_text・as_float・as_int・as_flag・as_choice と、同じスカラーの規則を使う freeze)にまとめ、全部の運び手(PATH_CARRIERS = OrderRequest・CancelRequest・5 つの報告・FillNotice・12 の事象型)の全部の欄を、作る時にそこに通す。欄には組み込みの型そのものだけが入る(子は組み込みの型の側の読み出しで中身だけ取り出し、Enum の要素・関数・何とでも等しいと答える物は断る)。運び手は slots の凍結データクラスにして属性を後から足せない。(2) 路の入口(発注・取消・強制注文・報告・データ源)は核の class そのものだけを受け、戦略と口座の注文は欄から作り直した別の物を取引所の側と戦略の見え方に渡す。差し込み口の答え(遅れ・手数料・拒否の理由)と流れの名前も返された時に組み込みの値として読む。(3) 履歴の答え DeliveredEvents が「最後の次は、まだ届いていない事象か」(next_is_undelivered)を class で持ち、外れた名指しの誤りを FuturePositionError と新しい OutsideAnswerError(LookAheadError の子ではない)のどちらにするかをその事実から決める。
