# 作業者の報告(作る:0#2、agent a4ecfdcb168fe0cb1。Workflow の記録の返り値から逐語で書き出し)

## 変えたファイル

- /home/user/trade/src/bot/bt/core/ordering.py
- /home/user/trade/src/bot/bt/core/engine.py
- /home/user/trade/src/bot/bt/core/api.py
- /home/user/trade/src/bot/bt/core/events.py
- /home/user/trade/src/bot/bt/core/errors.py
- /home/user/trade/src/bot/bt/core/contract.py
- /home/user/trade/src/bot/bt/core/__init__.py
- /home/user/trade/tests/bt/item_0/test_bt0_channels.py(新規)
- /home/user/trade/tests/bt/item_0/test_bt0_order_facts.py(新規)
- /home/user/trade/tests/bt/item_0/test_bt0_run_settings.py(新規)
- /home/user/trade/tests/bt/item_0/test_bt0_ordering.py(新しい規則に合わせて書き直した)
- /home/user/trade/tests/bt/item_0/test_bt0_queue_key.py(参照の実装を新しい規則に替え、揺れる配信の遅延の試験を足した)
- /home/user/trade/tests/bt/item_0/test_bt0_scene_set.py(2 件を書き直した)
- /home/user/trade/tests/bt/item_0/test_bt0_streams.py(1 行)
- /home/user/trade/tests/bt/item_0/test_bt0_venue_order.py
- /home/user/trade/docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/round_2/ROOTCAUSE.md(新規。起動文の指示で直す前に書いた)

## 足した試験の数

32

## 試験のコマンド

PYTHONPATH=src python -m pytest tests/bt/item_0 tests/bt/critic/item_0 tests/bt/battery/item_0(項目の試験と核の試験)。全試験は setsid nohup env PYTHONPATH=src python -m pytest > /tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/pytest_item0_r2_worker.log で切り離して回した

## 試験の末尾の行

項目 0 と核: 「269 passed in 2.68s」(批評家の試験 tests/bt/critic/item_0 も含む。前の周に落ちていた 11 件も全部通る)。全試験: 「3156 passed, 4 skipped, 1 warning in 470.83s (0:07:50)」。場面集: run_battery.py --target new_impl → 「32 scenes …; {'正解と一致': 32}; 2 回で違う=0」、gen_definitions.py --check → OK、mutant.py --check → OK

## 要件の各行を満たした根拠(ファイル:行)

- 時刻は UTC の int64 ナノ秒: src/bot/bt/core/time.py:74(validate_nanos)・54(TIME_CONTRACT)・103(to_nanos)。走らせ方の設定 end_time_ns は src/bot/bt/core/engine.py の CoreEngine.__init__ で validate_nanos を通し、最初の処理より前で終わる窓は step で TimestampUnitError にします(engine.py の 'end_time_ns … is before the first entry')。history_limit は整数で 1 以上に限ります(engine.py:418)。試験は tests/bt/item_0/test_bt0_run_settings.py と tests/bt/critic/item_0/test_i0r1_end_time_not_validated.py(i0-r1-13)
- 事象の型(約定・板の写真・板の差分・足・資金調達・清算・時計・注文の受付/拒否/約定/取消/状態不明の通知): src/bot/bt/core/events.py:46(EventType)・174・211・222・235・272・284・302・312・322・334・353・363。足は [始まり, 終わり) の正の長さを必須にしました(events.py:258、i0-r1-11。試験は test_bt0_run_settings.py::test_bar_start_must_be_before_its_close)
- 戦略は「受け取れた時刻 ≤ 今」の事象しか見られない(構造で): src/bot/bt/core/api.py:371(visible_events)と :456(_time_arg。時刻の引数はどれも今より後なら LookAheadError。i0-r1-08)、:339(_revoke)。engine.py:611-614(届いた事象だけの窓)。入力→戦略の路は受け取りの時刻で届け、遅延が揺れても同じ入力の前の事象を追い越しません(engine.py:564 _deliver_input)。試験は tests/bt/item_0/test_bt0_lookahead.py・test_bt0_run_settings.py::test_any_time_argument_after_now_stops・test_bt0_channels.py
- 決定的な事象の順序(同時刻の並びの規則を明記): src/bot/bt/core/ordering.py の冒頭の説明(5 本の FIFO の路と鍵)、:94(TYPE_ORDER。入力の先頭どうしの併合だけに使う)、:110-114(路の段)、:126(ORDERING_RULE。機械で読める形)、:157(merge_key)、:169(merge_order)、:190(order_events)。engine.py:447(_push。鍵 = 時刻・段・受け取り・位置)、:480(_ingest)、:564(_deliver_input)、:644・:651(要求の路 1 本)、:783(通知の路)。手で書いた正解との突き合わせは tests/bt/item_0/test_bt0_ordering.py::test_every_phase_at_one_instant_by_hand。規則の参照の実装との突き合わせ(遅延なしで 200 種、揺れる遅延で 200 種)は test_bt0_queue_key.py。路の FIFO は test_bt0_channels.py(i0-r1-05・06・10・12)。2 回の実行の一致は test_bt0_ordering.py::test_two_runs_give_the_identical_sequence_and_digest と test_bt0_determinism.py
- 戦略の API(事象ごとの呼び出し・発注・取消): src/bot/bt/core/api.py:193(place)・221(cancel)・237(set_timer)・311(StrategyContext)、engine.py:624(事象 1 件ごとに on_event を呼ぶ)。戦略が見る注文の状態は事実から導きます(api.py:134 _derive_state・265 _apply_notice)。STATE_UNKNOWN は、それを解く通知が届くまで保ちます(i0-r1-09。試験は tests/bt/item_0/test_bt0_order_facts.py)
- 他項目が差し込む口(約定模型・遅延模型・費用・口座): src/bot/bt/core/interfaces.py:106(FillModel)・126(LatencyModel)・146(CostModel)・153(Account)、engine.py:390-394(_require_protocol)。約定の模型の報告は、取引所の台帳が事実に照らして検めます(engine.py:139 _VenueOrder・159 _VenueLedger。状態不明のあとに矛盾した報告が来たら VenueProtocolError。i0-r1-07)。試験は test_bt0_extension_points.py・test_bt0_account_socket.py・test_bt0_order_facts.py
- 場面集 32 場面: run_battery.py --target new_impl の出力(scratchpad の bt/item0_r2_worker_new_impl.tsv)は 32 場面すべて「正解と一致」で、2 回の実行で違ったものは 0 件

## 満たせなかった行とその理由

- i0-r1-14(p4-future-read-attempt の正解が要件より弱い): 直していません。場面集は場面係の持ち物で、起動文にも「読めるが変えない」とあるためです。核のほうは、since_ns・until_ns のどちらでも今より後なら LookAheadError で止めるように直しました。場面集の上でも新実装の結果は正解と一致したままです。
- i0-r1-15(P0-5 の「規則どおりの順」を値で見る場面が無い): 場面集には足していません(場面係の持ち物のため)。代わりに作業者の試験 tests/bt/item_0/test_bt0_ordering.py::test_every_phase_at_one_instant_by_hand を置きました。同時刻に 4 種の入力・発注・通知・時計が並ぶ場面で、手で書いた正解の順と突き合わせます。場面集の代わりにはなりません。
- i0-r1-16・i0-r1-17(検討表の上位互換が 1 能力ずつ裏付けられていない / grep で当たったのに写せなかった 90 行): 直していません。tests/bt/battery/item_0/opponents/CONSIDERED.md と pool.tsv は場面係の持ち物で、作業者の実装では直せません。原因の読みは round_2/ROOTCAUSE.md の G 節に書きました。

## 外部の道具を入れたときの §4 の検査の結果

入れていません(外部の道具の導入も、ネットワークの使用もしていません)。

## リードに聞くこと

- i0-r1-14〜17 は場面係の持ち物(場面集・検討表)への指摘なので、作業者は直していません。この周の中で場面係を起こして直させるかどうかを決めてください。
- 新しい規則で、同じ時刻の順が前の周と 1 か所変わりました。入力の時計の事象(心拍)は、これまでは同時刻の注文の通知より後でしたが、今は前に来ます(入力→戦略の路が通知の路より先の段にあるため)。戦略が自分で頼んだ時計は、これまでどおり最後です。要件の行にはこの細部についての語が無く、リードが判断することです。
- 1 本の入力の中の順を守るようにしたため(i0-r1-10)、同時刻の複数の型を 1 本に連結して渡すと、渡した順のまま処理します。4 つの入力を別々に渡せば、並びは 24 通りの渡し方のどれでも同じ 1 通りです。資料係の adapter は別々に渡しているので、場面 p5-hand-over-order は正解と一致したままです。前の周の自分の試験 test_hand_over_permutations_of_single_concatenated_stream_also_agree は、この新しい規則と矛盾するので書き直しました(規則 8 の後半にあたります。消した試験は 0 件で、書き直したものは次の欄に書きます)。
- 書き直した前の周の試験は次のとおりです。いずれも設計の変更によるもので、消したものはありません。test_bt0_ordering.py: 1 本の入力の中の型の並べ替えを期待していた試験を、別々の入力の型の順と 1 本の入力の中の順の 2 本に分けました。ORDERING_RULE の鍵の名前も新しいものにしました。test_bt0_queue_key.py: 参照の実装を「先頭の型の順で併合 → (届く時刻, 受け取りの時刻, 併合の位置)で並べる」に替えました。test_bt0_scene_set.py: since_future は [] ではなく LookAheadError を期待するようにし、連結の試験は上の問いのとおり書き直しました。test_bt0_streams.py・test_bt0_venue_order.py: 併合の規則の書き方を新しいものに合わせました。

## この周で変えた構造

待ち行列の鍵を「事象の型の優先度」から「(時刻, 路の段, 受け取りの時刻, 路の中の位置)」に替えました。すべての経路を 5 本の FIFO の路(入力→取引所 / 要求→取引所(新規と取消で 1 本)/ 入力→戦略(入力 1 本ごとに受け取った順。遅れて届く事象は、同じ入力でそれより前に受け取った事象を追い越さない)/ 通知→戦略 / 時計)にしています。型の順を使うのは、別々の入力の先頭どうしを併合するときだけです。取引所の台帳と、戦略が見る注文は、状態の文字列 1 つではなく事実(受付・約定の数量・取消の答え待ち・新規についての不明・取消についての不明・終わり)を持つ形にし、状態はそこから導きます。時刻の引数と走らせ方の設定は、どれも 1 つの検査口を通します。
