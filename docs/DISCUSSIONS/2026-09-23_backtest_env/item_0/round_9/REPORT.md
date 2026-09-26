# 作業者の報告(作る:0#9、agent a2f46bb4590a47089。Workflow の記録の返り値から逐語で書き出し)

## 変えたファイル

- src/bot/bt/core/api.py
- src/bot/bt/core/engine.py
- src/bot/bt/core/history.py
- src/bot/bt/core/window.py
- src/bot/bt/core/contract.py
- tests/bt/item_0/bt0_util.py
- tests/bt/item_0/test_bt0_lookahead.py
- tests/bt/item_0/test_bt0_r8_named_position_grid.py
- tests/bt/item_0/test_bt0_r8_sender_adversary.py
- tests/bt/item_0/test_bt0_r9_reachable_state_adversary.py
- tests/bt/item_0/test_bt0_r9_history_owner.py
- tests/bt/item_0/test_bt0_r9_context_graph.py
- docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/round_9/ROOTCAUSE.md

## 足した試験の数

219

## 試験のコマンド

全試験: setsid nohup で切り離して PYTHONPATH=src python -m pytest -p no:cacheprovider(ログ <S>/pytest_item0_r9_worker_full.log)/ 項目 0・批評家・場面集: PYTHONPATH=src python -m pytest tests/bt/item_0 tests/bt/critic/item_0 tests/bt/battery/item_0 -p no:cacheprovider(ログ <S>/pytest_item0_r9_worker_core.log)/ 場面集の新実装: PYTHONPATH=src python3 tests/bt/battery/item_0/run_battery.py --target new_impl --out <S>/item0_r9_worker_battery_new_impl.tsv。<S> = /tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt

## 試験の末尾の行

全試験(最後のコードの変更の後): 4128 passed, 6 skipped, 1 warning in 786.54s (0:13:06) / 項目 0 + 批評家 + 場面集: 1233 passed, 2 skipped in 286.42s (0:04:46) / 場面集(新実装): new_impl: 32 scenes; {'正解と一致': 32}; 2 回で違う=0。足した試験 219 件は新しい 3 本のファイルの件数(test_bt0_r9_reachable_state_adversary.py・test_bt0_r9_history_owner.py・test_bt0_r9_context_graph.py、--collect-only で 219)。test_bt0_r8_sender_adversary.py のパラメータ 1 件を外した(理由は unmet の吟味 (5))。

## 要件の各行を満たした根拠(ファイル:行)

- P0-1 事象駆動: src/bot/bt/core/engine.py:586(CoreEngine)、712(_push: 優先度つき待ち行列への積み)、806(_step: 1 件ずつ処理)。この周は並びの構造を変えていない。場面集の p1 の場面は「正解と一致」(<S>/item0_r9_worker_battery_new_impl.tsv)
- P0-2 UTC の int64 ナノ秒: src/bot/bt/core/time.py:55(TIME_CONTRACT)と 75(validate_nanos)。この周は変えていない。場面集の p2 の場面は「正解と一致」
- P0-3 8 種の事象の型: src/bot/bt/core/events.py:52(EventType)、408(ALL_EVENT_CLASSES)。この周は変えていない。場面集の p3 の場面は「正解と一致」
- P0-4 構造でルックアヘッドを不能にする: src/bot/bt/core/api.py:543(StrategyContext: slot を持ち代入を断り、値・凍った今の事象・窓・関数だけを持つ)、src/bot/bt/core/window.py:304(EventWindow: 核の列は読む関数の閉じ込めの中だけに置き、代入を断る。位置の規則 61 行 POSITION_RULE・160 行 resolve_key は変えていない)、src/bot/bt/core/history.py:57(DeliveredList)・127(DeliveredHistory: 列には届けた事象だけを足す)、engine.py:357(_alive_switch)・967(コールバックの終わりに文脈と窓を取り消す)。試験: tests/bt/item_0/test_bt0_lookahead.py(関数の閉じ込めまで歩いても未来の事象に届かない)、test_bt0_r9_context_graph.py、test_bt0_r8_named_position_grid.py。批評家の試験 test_context_leaks_engine_via_private_attrs.py・test_i0r7_backward_answer_negative_bounds.py は通る。場面集の p4-future-read-attempt は「正解と一致」
- P0-5 決定的な並び: src/bot/bt/core/ordering.py:161(ORDERING_RULE)と 182(merge_key)。この周は変えていない。配達の要約は直す前と同じ 35269aeea5ca(<S>/item0_r9_worker_speed_compare.txt)。場面集の p5 の場面は「正解と一致」「2 回の実行で同じ」
- P0-6 戦略の API(事象ごとの呼び出し・発注・取消): src/bot/bt/core/strategy.py:12(on_event)、src/bot/bt/core/api.py:821(place_order)・827(cancel_order)・831(set_timer)・662(visible_events)、engine.py:375(_context_calls: 注文の口の方法を閉じ込めた関数)、engine.py:976(_drain)・1003(_take_message: API の規則を核の台帳と時刻に対してもう一度当てる)、api.py:428(_OrderBook)。場面集の p6 の場面は「正解と一致」
- P0-7 差し込み口: src/bot/bt/core/interfaces.py:153(FillModel)・173(LatencyModel)・193(CostModel)・200(Account)・226(SOCKETS)。この周は変えていない。場面集の p7 の場面は「正解と一致」
- 信頼性(持ち主の規則、i0-r8-01 の族): src/bot/bt/core/contract.py:121(channel_payloads.ownership)と 86(visibility.scope)、CORE_VERSION は core-11(contract.py:15)。試験 tests/bt/item_0/test_bt0_r9_reachable_state_adversary.py(文脈から届く全ての物 × 変え方 × 時機 5 つの格子、規則を破る升 0)、test_bt0_r9_context_graph.py(リードの追記 §3.4 の到達性の試験)

## 満たせなかった行とその理由

- 満たせなかった要件の行として挙げる物: 無し(P0-1〜P0-7)。判定は批評家と監査役に任せる。
- 【吟味(1) i0-r8-01 を直した根拠】核の台帳 src/bot/bt/core/api.py:428(_OrderBook)、送り手と核が同じ規則を当てる関数 api.py:403(check_new_id)と 417(check_timer)、戦略の口 api.py:465(_OrderPort、slot を持ち、戦略の写しと箱だけを持つ)、engine.py:694(核の台帳と、核が自分で持つ写しの台帳 _shown と箱 _box)、engine.py:976(_drain: 核の参照で箱を読み、口の属性が差し替えられていれば断る)と 1003(_take_message: 本当の型で読み、API の規則を核の台帳に当てる)、engine.py:971(_show: 写しを書くだけで読み返さない)、engine.py:854(結果の orders は核の台帳から作る)、api.py:527・534(order()/open_orders() は呼ぶたびに新しい物)。批評家の試験 tests/bt/critic/item_0/test_i0r8_order_port_state_written_around_api.py は、直す前は 2 failed、直した後は通る(1233 passed の中)。この試験の歩き方は関数の閉じ込めに入らないので、閉じ込めから口に届く形の試しも書いた: <S>/item0_r9_worker_probe_port_registry_write_closure.py → 'with_forced False result orders: ['real'] ghost: None venue saw: ['real']' / 'with_forced True refused: OrderApiError client_order_id 'forced-1': the prefix 'forced-' is reserved ... venue saw: []'。批評家の試し orderview_shared → 'same object as open_orders()[0]: False' / 'result orders['a']: filled_size 0.0 venue_order_id '''(<S>/item0_r9_worker_after_probes.out)。
- 【吟味(1) i0-r8-02 を直した根拠】src/bot/bt/core/history.py:57(DeliveredList: 作ったあとの __init__ を断る 84 行、属性の代入と削除を断る 91 行、list の中身を変える方法を全部断る 49・122 行)、history.py:127・155(DeliveredHistory: 核が持つ事実だけで保ち方を決め、列からは何も読み返さない)。批評家の試し deliveredlist_change → '__init__ -> TypeError' / 'dropped = -> AttributeError' / 'visible_events() after: [0, 1, 2]'(<S>/item0_r9_worker_after_probes.out)。試験 tests/bt/item_0/test_bt0_r9_history_owner.py は、list の方法を dir(list) から機械で列べ、変える方法を全部試す。直す前の実装では 21 failed(<S>/item0_r9_worker_history_on_head.log)、直した後は通る。
- 【吟味(1) i0-r8-03 を直した根拠】src/bot/bt/core/contract.py:55(position_rule.last_k: [-k:] は断ることと、代わりが visible_events(n=k) であることを同じ箇所に書いた)、api.py の visible_events の説明の文。試験 test_bt0_r9_history_owner.py の test_the_contract_says_how_to_read_the_last_k_events と test_the_last_k_reads_as_the_contract_says で、契約の文と振る舞い(k が届いた件数より多いとき [-k:] は BeforeFirstEventError、n=k は届いた全部)が一致することを確かめる。
- 【吟味(1) i0-r7-01・i0-r7-02(前の周で直った物)が壊れていない根拠】批評家の試験 test_i0r7_backward_answer_negative_bounds.py・test_i0r7_fraction_in_extra_stays_live.py は通る。批評家の試し backward_negslice → r[-6:-5] / r[-6:-4] / r[-5::-1] / r[-6:-5:-1] はどれも FuturePositionError。批評家の独立の神託 item0_r8_critic_probe_semantic_oracle.py の seed 1〜6 → どれも SILENT 0 / WRONG 0 / UNDER 0 / IDX_SILENT 0(<S>/item0_r9_worker_semantic_oracle_after.out)。Fraction の試し(try で包んだ写し)→ 'venue saw ... 'f': Fraction(1, 3)'。
- 【吟味(2) 同じ根の全箇所】指摘の場所の一覧からではなく、文脈から届く全ての物を歩く試験の出力から探した。docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/round_9/ROOTCAUSE.md の §A-3(コードを変える前に見つけた 4 つの形)と §E の表(直しの途中で試験が見つけた 5 つの形: 箱をコールバックのたびに取り替えていた / 壊した slot で核の作り直しが落ちた / 落とした事実の tuple を核の物のまま渡していた / 文脈に置かれた _revoke を呼んでいた / 取り消しの印の容れ物が空にされると核の書き込みが落ちた)に書き、どれも同じ構造で直した。
- 【吟味(3) 試験】項目 0・批評家・場面集の試験: 1233 passed, 2 skipped。全試験: 4128 passed, 6 skipped。場面集の新実装: 32 場面すべて「正解と一致」「2 回の実行で同じ」。規則 8(試験自身の誤りで落ちる批評家の試験): 該当なし(落ちる批評家の試験は無い)。
- 【吟味(4)(6) 敵対者の試験を先に書いた記録】test_bt0_r9_reachable_state_adversary.py はコードを変える前に書き、直す前の実装に当てて落ちることを確かめた(格子の 5 つの時機で合わせて 3,000 升を超えて規則を破った。<S>/item0_r9_worker_adversary_on_head.log。最後の版を第 8 周の実装に当てると 108 failed / 85 passed、<S>/item0_r9_worker_adversary_on_head_final.log)。格子は、文脈から属性・slot・結び付いた方法の __self__・関数の閉じ込め・入れ物の中身で届く全ての物 × 変え方(基の型の方法で入れ物に偽物 7 種を足す・消す・入れ替える・空にする・逆にする、属性と slot を object.__setattr__ で偽物 7 種に書き換える・消す、方法の名前を実例の属性で覆う)× 時機 5 つ(同じコールバック / 持ち続けて後のコールバック)で、最後の版は 22〜58 の物、1 つの時機あたり 1,099〜3,155 升を全部走らせ、規則を破った升 0。出口の箱は規則どおり別の格子(規則に合う知らせ 3 種・知らせの中身を合う値に変える 5 種 → API の呼び出しと同じ結果 / 合わない知らせ 17 種・中身を合わない値に変える 8 種 → CoreError で断り、それまでに何も送らない / 知らせを取り戻す / 箱を差し替える / 口の写しを壊してから呼ぶ 3 種)× 時機 5 つ。リードの追記 §3.4 の試験 test_bt0_r9_context_graph.py(gc.get_referents で深さの上限なく歩き、文脈から届く物と核の変わりうる物が is で交わらず、届く物に変わりうる型が 0 件)は、追記を読んだ後、直す前に書いた。第 8 周の実装に当てると 1 failed(<S>/item0_r9_worker_context_graph_on_head.log)。test_bt0_r9_history_owner.py は直しと同じ段で書いた(試験の説明の文に書いた)。列に入れなかった物は各試験ファイルの説明の文に書いた(ctypes、インタプリタの覗き込み、核のコード(class・関数・モジュール)の書き換え、コールバックの自分の API 呼び出しの最中の変更、差し込み口からの攻撃(第 8 周の敵対者の試験で扱う)、__class__ の代入)。
- 【吟味(4) 厳しい批評家が挙げそうな候補と、何をしたか】(a) 口を通らずに箱に書いた、規則に合う知らせが受け付けられる → API の規則を核の台帳に当てる設計なので、API の呼び出しと同じ結果になることを試験で確かめ(test_a_message_by_the_api_rules_has_the_effect_of_the_api_call ほか)、契約 contract.py:121 に書いた。(b) 戦略が自分の箱から知らせを取り戻すと、戦略の見え方には送っていない注文が PENDING_NEW で残る → 核・取引所・結果には何も届かないこと(送らなかったのと同じ)を試験 test_removing_a_sent_message_is_not_sending_it で確かめた。見え方は戦略自身の物で、核は読まない(契約の scope に書いた)。(c) 戦略が自分の写しの台帳に、自分の __eq__ を持つ鍵を入れると、核が写しを書くときにその __eq__ が走りうる → 直していない。走るのはその配達の時刻で、戦略が届く物はその時刻までに届いた物だけであり、核の状態には届かない(格子で確かめた)。例外なら engine は FAILED になり結果を出さない。(d) 関数の閉じ込めは __closure__ で届く → 格子は閉じ込めの中まで歩いて攻撃し、規則を破る升が 0 であることを確かめた。(e) 核のコード(class・関数・モジュール)の書き換え → 契約の scope に範囲の外として書いた(プログラムを変えることで、状態ではない)。(f) 速さ → ROOTCAUSE §E とリードに聞くことに書いた。(g) visible_events の答えの中の事象は呼び出しごとの写しではない → リードに聞くことに書いた。
- 【吟味(5) 場当たりの直しの有無】場面集は読んだだけで変えていない。場面だけを特別扱いする分岐は足していない。閾値と既定値は変えていない。消した試験は無い。書き直した自分の試験: test_bt0_r8_sender_adversary.py(口が登録していない id の新しい注文を断ることを期待したパラメータ 1 件を外した。第 9 周の規則ではこの知らせは place_order と同じ結果になり、それを test_bt0_r9_reachable_state_adversary.py で確かめる。口に届く道を find に替えた)、test_bt0_lookahead.py(歩き方を、名前の変わった slot と関数の閉じ込めまで追う形にした)、test_bt0_r8_named_position_grid.py(核の列に届く道を窓の読む関数の閉じ込めに替えた)。ほかに bt0_util.py に歩く関数 reachable と find を足した。

## 外部の道具を入れたときの §4 の検査の結果

外部の道具は入れていない(pip install も venv も作っていない)。ネットワークも使っていない。

## リードに聞くこと

- 速さ(要件の行には無い): 約定 5 万件の測り(<S>/item0_r8_worker_speed.py)を直す前(792a22a の src/bot)と直した後で交互に走らせた結果、読み出しなし 32.35 → 39.84、読み出しあり 43.38 → 54.2 マイクロ秒/事象(<S>/item0_r9_worker_speed_compare.txt)。配達の要約は直す前と同じ 35269aeea5ca。批評家の試験 test_i0r3_shift_and_cancel_count.py の 1 回の実行は 0.24〜0.40 秒 → 0.50〜0.74 秒(order() を呼ぶたびに見え方の写しを作る分)。全試験は 13 分 06 秒。速さを要件にするかはリード(またはオーナー)の判断なので挙げる。
- LEAD_DESIGN §3.4 の「呼び出しが返す物(order()・open_orders()・visible_events() の答え)は毎回作った写し」の読み方: order()・open_orders() は呼ぶたびに新しい見え方の物を返す。中の注文(OrderRequest)は核が変更のたびに書いた戦略の写しで、呼び出しの間で同じ物(凍っていて slot を持つ。変えるには object.__setattr__ を使うほかなく、変わるのは戦略自身が後で読む物だけ)。visible_events() の答えの tuple と場所は呼ぶたびに新しいが、中の事象は戦略の写しの同じ物(凍っている)。事象や注文まで呼ぶたびに写すと、読み出しのたびに件数に比例して遅くなる。この読み方でよいか判断してほしい。
- 振る舞いの変化: 口を通らずに出口の箱に書いた知らせのうち、API の規則に合うものは、第 8 周は一律に断っていたが、第 9 周は核の台帳に対して API の規則を当てるので、その API の呼び出しと同じ結果になる(規則に合わないものは第 8 周と同じく OrderApiError で断る)。契約 core-11 の channel_payloads.ownership に書いた。後の項目への周知が要るか判断してほしい。

## この周で変えた構造

戦略の注文の事実は、どこからも届かない核の台帳(_OrderBook)だけが持つようにした。戦略が届くのは自分の写しと出口の箱だけで、核は箱を API の呼び出しの引数として 1 度だけ読み、API の規則を核の台帳と時刻に対してもう一度当てる。文脈と窓は変わりうる物を 1 つも持たない(slot の代入を断り、核の列と注文の口は関数の閉じ込めの中でしか届かない。取り消しはエンジンが持つ閉じ込めた変数で行う)。履歴の保ち方は核が持つ事実(配達の番号・受け取った時刻・型)だけで決め、戦略の届く列からは何も読み返さない。リードの追記 LEAD_DESIGN §3.4 は作業の途中(コミット 161121c)で読み、そこから当てた。
