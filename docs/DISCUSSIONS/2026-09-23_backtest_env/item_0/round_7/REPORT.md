# 作業者の報告(作る:0#7、agent aefcff1f7861e63bd。Workflow の記録の返り値から逐語で書き出し)

## 変えたファイル

- /home/user/trade/docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/round_7/ROOTCAUSE.md
- /home/user/trade/src/bot/bt/core/__init__.py
- /home/user/trade/src/bot/bt/core/api.py
- /home/user/trade/src/bot/bt/core/contract.py
- /home/user/trade/src/bot/bt/core/engine.py
- /home/user/trade/src/bot/bt/core/errors.py
- /home/user/trade/src/bot/bt/core/history.py
- /home/user/trade/src/bot/bt/core/ordering.py
- /home/user/trade/src/bot/bt/core/time.py
- /home/user/trade/src/bot/bt/core/values.py
- /home/user/trade/src/bot/bt/core/window.py
- /home/user/trade/tests/bt/item_0/test_bt0_future_position.py
- /home/user/trade/tests/bt/item_0/test_bt0_sender_types.py

## 足した試験の数

120

## 試験のコマンド

PYTHONPATH=src setsid nohup python3 -m pytest -p no:cacheprovider > /tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/pytest_item0_r7_worker.log 2>&1 &(全試験。10:37:38Z 開始)/ 項目と核の試験: PYTHONPATH=src timeout 600 python3 -m pytest -p no:cacheprovider tests/bt/item_0 tests/bt/critic/item_0

## 試験の末尾の行

全試験: 1 failed, 3808 passed, 6 skipped, 1 warning in 518.96s (0:08:38)。落ちたのは tests/bt/critic/item_0/test_i0r2_battery_p5_grading.py::test_single_input_form_of_hand_over_order_agrees_with_keeping_one_input_in_order の 1 件だけ。/ 項目 0 と批評家の試験(最後の文言の直しの後にも回した): 1 failed, 865 passed, 2 skipped in 81.62s。落ちたのは同じ 1 件。原因は場面集の側: 批評家の試験の 72 行目 `LiquidationEvent(... price=d["price"] ...)` が、場面係がこの周に書き換えた scenes.py の場面データ(`git diff --stat 6e6d6ae -- tests/bt/battery/item_0/scenes.py` → 228 行が変わった)で KeyError: 'price' になる。src/bot/bt/core と作業者の試験の側で起きたものではない。第 6 周の批評家の試験のうち、実装の側の test_i0r6_past_answer_names_undelivered.py は 6 件とも通る(直す前は 4 failed, 2 passed)。場面集の側の test_i0r6_battery_p5_measures_order_not_types.py も、全試験の回では通っている。場面集の実行(最後の 1 回): run_battery.py --target new_impl → 32 場面すべて「正解と一致・2 回の実行で同じ」。mutant → 31 場面が一致、1 場面が不一致。current_impl → 一致 8、対応なし 23、不一致 1。

## 要件の各行を満たした根拠(ファイル:行)

- 時刻は UTC の int64 ナノ秒: src/bot/bt/core/time.py:75 validate_nanos(:91 で値を 1 つの決まり as_int に通し、int64 の範囲を確かめる)、:111 to_nanos、:55 TIME_CONTRACT
- 事象の型(約定・板の写真・板の差分・足・資金調達・清算・時計・注文の受付/拒否/約定の通知): src/bot/bt/core/events.py:52 EventType、:408 ALL_EVENT_CLASSES、:423 EVENT_TYPE_TO_CLASS。データ源は核の class そのものに限る: src/bot/bt/core/engine.py:395 _CLASS_TO_TYPE、:471
- 戦略は「受け取れた時刻 ≤ 今」の事象しか見られない(構造): src/bot/bt/core/api.py:498 visible_events(時刻の引数が今より後なら LookAheadError)。src/bot/bt/core/window.py:95 DeliveredEvents、:61 AnswerPlace、:187 _outside(まだ届いていない位置を名指すと必ず FuturePositionError = LookAheadError)。試験は tests/bt/item_0/test_bt0_future_position.py の test_every_named_position_agrees_with_the_input_at_every_callback ほか
- 決定的な事象の順序(同時刻の並びの規則を明記): src/bot/bt/core/ordering.py:97 TYPE_ORDER、:119 PHASES、:161 ORDERING_RULE、:182 merge_key。配達の要約はこの周の前後で同じ 35269aeea5ca(scratchpad/bt/item0_r7_worker_speed.txt)
- 戦略の API(事象ごとの呼び出し・発注・取消): src/bot/bt/core/api.py:646 place_order、:652 cancel_order、:699 STRATEGY_API。src/bot/bt/core/engine.py:812 _deliver。送り手の値は本当の型で判定する: src/bot/bt/core/api.py:537、:637、:665
- 他項目が差し込む口(約定模型・遅延模型・費用・口座): src/bot/bt/core/interfaces.py:153 FillModel、:173 LatencyModel、:193 CostModel、:200 Account。差し込み口の答えは値として 1 度だけ読み、その所の誤りの型で断る: src/bot/bt/core/engine.py:350、:888、:918、:983
- 値の場面・能力の場面の全観点 P0-1〜P0-7: tests/bt/battery/item_0/run_battery.py --target new_impl → 32 場面すべて「正解と一致・2 回の実行で同じ」(scratchpad/bt/item0_r7_worker_new_impl.tsv)

## 満たせなかった行とその理由

- 満たせなかった要件の行: なし(下の requirement_evidence)。
- 提出前の吟味(1) 指摘 1 件ごとの直した根拠。i0-r6-01 [止める]: 誤りの種類を、名指した位置をその列の位置に戻して選ぶようにした(src/bot/bt/core/window.py:187 `_outside`、:178 `_check_bounds`、:158 区間の境界を 1 度だけ読む。場所は src/bot/bt/core/api.py:560-601 で作る)。批評家の試験 test_i0r6_past_answer_names_undelivered.py: 直す前は 4 failed, 2 passed、直した後は 6 件とも通る。自分の試し scratchpad/bt/item0_r7_worker_probe_answer_kind.py: 直す前は `checked 192 namings, wrong kind 63`(…before.txt)、直した後は `wrong kind 0`(…after.txt)。批評家の probe item0_r6_critic_probe_answer_kind.py: `until day 6 [12]` と `all[0:6:3] [4]` は FuturePositionError(LookAheadError) になった。`all[::-1] [10]` の文は「nothing is there」になった。
- 吟味(1) の続き。i0-r6-03 [直す]: values.py の型の判定を本当の型にした(src/bot/bt/core/values.py:97 is_a、:136 _plain_scalar、:188 as_flag、:198 as_int、:208 as_float)。自分の試し scratchpad/bt/item0_r7_worker_probe_senders.py は送り手の値を 54 通り入れる。直す前は 37 通りで誤りの型が違い(`grep -c WRONG-TYPE` → 37)、`visible_events(event_type=偽)` は黙って空を返した(…before.txt)。直した後は 0 通り(…after.txt)。批評家の probe item0_r6_critic_probe_values.py は、size=Spoof(float) → OrderApiError、Fill.price → VenueProtocolError、Trade.price → EventValidationError、post_only=np.bool_ → bool として受ける、となった。i0-r5-01・i0-r5-05 は、この 2 件の直しに入っている。
- 吟味(2) 同じ根の全箇所。批評家が挙げていない所も直した。i0-r6-01 の根では、後ろ向きの答えに負の添字で届いていない側を名指すと生の IndexError が出ていた(43 通り)。落とした数の区別も入れた(history.py:40,51)。場所を言えない空の答えは断る(api.py:580)。i0-r6-03 の根では、time.py(:91, :132, :163)、履歴の読み出しの引数(api.py:537 event_type と _count_arg)、ctx.order(api.py:637。黙って None を返していた)、差し込み口の答え(engine.py:350 遅延、:918 拒否の理由、:983 手数料、:888 強制注文)、データ源(engine.py:445 流れの名前、:471 事象の型は _CLASS_TO_TYPE で引く)、実行の設定(engine.py:403 time_span、:552 events、:594 history_limit)、ordering.py、EventWindow(window.py:252)を直した。
- 吟味(3) 試験。批評家の試験と場面集の試験を回し、落ちるのは場面集の側の 1 件(test_i0r2_battery_p5_grading.py)だけ。この試験自身が場面データの 'price' の鍵を前提にしており、場面係の直しで鍵が変わって落ちる。試験は変えていない(規則 8)。次の周の批評家と場面係が確かめる。消した試験・書き直した試験(規則 8): test_bt0_future_position.py のうち、前の周の実装の規則を写していた次の 3 つを書き直した。test_every_index_and_slice_matches_the_probe_oracle は、fact の引数を外し、8 つの場所 × 全部の鍵で、列から決める神託にした。test_the_fact_agrees_with_the_input_at_every_callback は、test_every_named_position_agrees_with_the_input_at_every_callback(全部の位置、1 万件を超える名指し)と test_the_fact_after_the_last_event_agrees_with_the_input に分けた。test_the_fact_cannot_be_left_out_or_changed は test_the_place_cannot_be_left_out_or_changed に書き直した。test_negative_index_before_the_oldest_is_a_plain_index_error は ..._is_before_the_first_event に書き直した(今は BeforeFirstEventError を期待する)。消した主張は「最後より先のどの名指しも答えの 1 つの事実と同じ種類」だけで、これは i0-r6-01 が誤りと示したもの。
- 吟味(4) 厳しい批評家なら止めそうなことを、自分で列べて潰した。(a) history_limit の下で、落とした事象と何も無い所を取り違える: 自分の神託の試験が 102 件の食い違いで見つけ、落とした数を持たせて直した。(b) 区間の境界の __index__ が呼ぶたびに違う値を返すと、検めを素通りする: test_a_slice_bound_is_read_once。(c) 答えを作るたびに検めると遅くなる: 読み出しの多い戦略で 18.6 → 23.6 µs/事象になった。核の中で作る答えは検めない作り方(_placed)に分け、直した後はばらつきの幅の中(scratchpad/bt/item0_r7_worker_speed.txt)。配達の要約は始めと同じ 35269aeea5ca。(d) numpy の数の扱いが所によって違う: 数の欄・整数の欄・真偽の欄のすべての所に同じ値を入れる試験で固めた。(e) 偽る物の method が走る: 45 の所の全部で RAN == [] を確かめた。
- 吟味(5) 場当たりの直しではないか。場面集には触れていない。閾値・既定値も変えていない。文言だけ合わせた所も無い。機能も外していない。変えた振る舞いは 3 つある。numpy の真偽・numpy の整数を extra・n・post_only で受けるようになった(前は断っていた)。場所を言えない空の答えを断るようになった。事象の欄の値(numbers_only=False)は、数値を表す文字・Decimal・数の塔の数だけを受け、bytes や __float__ だけを持つ物は断るようになった。3 つとも契約(contract.py の channel_payloads.type_decisions と visibility)に書いた。
- 確かめの限界: 新しい試験(AnswerPlace などの新しい名前を import する)は、この周の初めの版 6e6d6ae の核では集め(collection)の段で止まる(`2 errors`、scratchpad/bt/item0_r7_worker_tests_on_6e6d6ae.txt)。このため、古い核で落ちることの根拠は、上の 2 つの試しの直す前の出力と、批評家の試験の 4 failed になる。

## 外部の道具を入れたときの §4 の検査の結果

入れていない(外部の道具は導入も実行もしていない。ネットワークも使っていない)。

## リードに聞くこと

- リードが作業木を途中でコミットした(6e6d6ae → e73d98d → bfc207a → 9514c3c → 4082053)ため、この周の差分は `git diff 6e6d6ae` で見てほしい。この周の作業の前の版は 6e6d6ae で、ROOTCAUSE.md の行番号もこの版のもの。
- tests/bt/critic/item_0/test_i0r2_battery_p5_grading.py が、場面係のこの周の scenes.py の書き換えで KeyError: 'price' になって落ちる。試験自身が場面データの鍵を前提にしているため。直すのは場面係か次の周の批評家になる。作業者は変えていない。

## この周で変えた構造

(1) 履歴の答え DeliveredEvents が、読み出しの列の中での自分の場所 AnswerPlace を持つようにした。場所は、始まりの位置 first・歩幅 step・読み出しの時に届いていた数 delivered・history_limit が落とした数 dropped の 4 つ。誤りの種類は、名指した位置をその列の位置に戻して決める。まだ届いていない位置は FuturePositionError(LookAheadError の子)。届いたが答えの外の位置は OutsideAnswerError。落とした事象の位置は DroppedPositionError。何も届いていない所は BeforeFirstEventError。負の添字もこの規則に入れ、区間の境界は 1 度だけ読む。場所を言えない空の答えは断る。(2) 送り手の値の型の判定は、核の全体で本当の型だけで行う(values.is_a = issubclass(type(x), C))。外来の値を受ける決まりは values.scalar の 1 つにまとめた(組み込みの子・numpy の真偽・数の塔)。断るときは、その所の誤りの型で、本当の型の完全な名前を書く。
