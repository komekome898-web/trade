# 作業者の報告(作る:0#3、agent ab6128b21ba9ccb4e。Workflow の記録の返り値から逐語で書き出し)

## 変えたファイル

- src/bot/bt/core/engine.py
- src/bot/bt/core/api.py
- src/bot/bt/core/history.py(新規)
- src/bot/bt/core/events.py
- src/bot/bt/core/interfaces.py
- src/bot/bt/core/ordering.py
- src/bot/bt/core/errors.py
- src/bot/bt/core/contract.py
- src/bot/bt/core/__init__.py
- tests/bt/item_0/test_bt0_history_limit.py(新規)
- tests/bt/item_0/test_bt0_no_time_sentinel.py(新規)
- tests/bt/item_0/test_bt0_cancel_count.py(新規)
- tests/bt/item_0/test_bt0_orders.py
- tests/bt/item_0/test_bt0_engine_source.py
- tests/bt/item_0/test_bt0_time_window.py
- tests/bt/item_0/test_bt0_contract.py
- docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/round_3/ROOTCAUSE.md(新規。直す前に書いた根本原因)

## 足した試験の数

25

## 試験のコマンド

PYTHONPATH=src python -m pytest tests/bt/item_0 tests/bt/critic/item_0 tests/bt/battery/item_0 (項目 0 = 核なので、自分の項目の試験と核の試験は同じ tests/bt/item_0。ログ: scratchpad bt/pytest_item0_r3_worker_all.log と pytest_item0_r3_worker_item.log)

## 試験の末尾の行

tests/bt/item_0 だけ: 「263 passed in 5.33s」。tests/bt/item_0 + tests/bt/critic/item_0 + tests/bt/battery/item_0: 「3 failed, 298 passed in 7.04s」。落ちる 3 件: (1)(2) test_i0r2_battery_p5_grading.py の 2 件 = 場面集(scenes.py・run_battery.py)の欠陥 i0-r2-06・07 を測る試験で、直すのは場面係(作業者の持ち物の外、起動文で「変えない」)。(3) test_i0r2_history_limit_views_disagree.py = 規則 8 に当たると読む(試験自身の前提の誤り): この試験は history_limit=3 で事象が捨てられた後も ctx.visible_events()(範囲も件数も付けない全部の読み出し)が答えを返す前提で書かれている。この周の直しで、捨てた部分に掛かる読み出しは HistoryTruncatedError で断る(同じ指摘の後半「どちらの答えも切られたことを知らせず…黙って短い答えを返す」への直し)ので、試験は食い違いではなく例外で落ちる(出力 api.py:483 HistoryTruncatedError)。試験は変えていない。試験の主張(型で引いた答え = 全体を型で抜いた答え)は、答えが返るすべての読み出しについて tests/bt/item_0/test_bt0_history_limit.py が確かめている(切らない実行との突き合わせ 40 種 × 上限 4 通り、同じ入力の場面 test_critic_scene_bar_then_trades_limit_3)。次の周の批評家に確かめてほしい。第 2 周で落ちていた test_i0r2_negative_time_jumps_to_epoch.py と test_i0r2_second_cancel_in_flight_shown_open.py は通る。

## 要件の各行を満たした根拠(ファイル:行)

- 時刻は UTC の int64 ナノ秒: src/bot/bt/core/time.py:54(TIME_CONTRACT)・74(validate_nanos)。事象の時刻は src/bot/bt/core/events.py:132(Event の検査)、待ち行列のすべての時刻は src/bot/bt/core/engine.py:481(_push で validate_nanos)。この周で、「まだ無い」を時刻 0 で表す所を無くした: engine.py:304(_FifoChannel、前の時刻は None)・473-474、api.py の _OrderPort._time(最初の呼び出しの前は OrderApiError)、engine.py:504(鍵の 3 つ目はその項目の時刻)、interfaces.py:102(FillNotice.venue_time_ns は必須で int64 を検める)。試験 tests/bt/item_0/test_bt0_no_time_sentinel.py(1970 年より前・0・int64 の下端の近くで、注文の着く時刻と受付の届く時刻が送った時刻 + 遅れのまま)
- 事象の型(約定・板の写真・板の差分・足・資金調達・清算・時計・注文の受付/拒否/約定の通知): src/bot/bt/core/events.py:178・215・226・239・276・288・306・316・326・338・357・372。取消の成立の通知は何への答えかを持つ(events.py:357 の answers、CANCELED_ANSWERS)。場面集を新実装に通した結果 32 場面すべて「正解と一致」・2 回で違う 0(scratchpad bt/item0_r3_worker_new_impl.tsv)
- 戦略は「受け取れた時刻 ≤ 今」の事象しか見られない(構造): src/bot/bt/core/api.py:413(visible_events)・538(_time_arg、未来の時刻は LookAheadError)、src/bot/bt/core/window.py(配信済みの一覧だけを見せる)、engine.py:622(_deliver)。保証の範囲(文脈と属性で辿れる物。処理系の内部を覗く手段は含まない)を api.py と engine.py の冒頭と contract.py:39(visibility.scope)に書いた(i0-r2-10)。捨てた履歴に掛かる読み出しは api.py:468(__refuse_truncated)で HistoryTruncatedError(errors.py:45)
- 決定的な事象の順序(同時刻の並びの規則を明記): src/bot/bt/core/ordering.py の冒頭(路ごとの FIFO と鍵 (時刻, 段, 受け取りの時刻 か その項目の時刻, 位置))・96(TYPE_ORDER、別々の入力の先頭どうしの併合にだけ使う)・128(ORDERING_RULE)・161(merge_key)・194(order_events)。試験 tests/bt/item_0/test_bt0_ordering.py・test_bt0_queue_key.py・test_bt0_streams.py・test_bt0_channels.py
- 戦略の API(事象ごとの呼び出し・発注・取消): src/bot/bt/core/strategy.py:12(on_event)、api.py:508(place_order)・514(cancel_order)・518(set_timer)。戦略の見る注文は事実で持ち、取消の答え待ちは件数 cancels_in_flight(api.py:175)、状態は api.py:144(_derive_state)で導く。取引所は 1 つの取消に答えをちょうど 1 つ(engine.py:272 _is_cancel_answer、engine.py:754)。試験 tests/bt/item_0/test_bt0_cancel_count.py(第 2 周の批評家の場面・乱数 120 種で件数 = 送った取消 − 届いた答え)
- 他項目が差し込む口(約定模型・遅延模型・費用・口座): src/bot/bt/core/interfaces.py:112(FillModel)・132(LatencyModel)・152(CostModel)・159(Account)。試験 tests/bt/item_0/test_bt0_extension_points.py・test_bt0_account_socket.py・test_bt0_latency.py(変更なしで通る)

## 満たせなかった行とその理由

- 場面集・adapter・検討表の指摘 i0-r1-14/i0-r2-05(p4-future-read-attempt の正解が要件より弱い)、i0-r1-15/i0-r2-06(P0-5 に規則どおりの順を値で測る場面が無い・3 件落とした対象を一致にする)、i0-r2-07(p5-hand-over-order の 1 本の入力の形の正解が矛盾)、i0-r2-04(adapter が相手の既定の拒否の仕組みを切っている)、i0-r1-16/i0-r2-08(検討表の上位互換の裏付け)、i0-r1-17/i0-r2-09(grep で写せなかった 90 行を検討していない)、i0-r2-12([直す]、P0-2 の拒否の側の場面が無い)は直していない。どれも tests/bt/battery/item_0/ の中で、委任文 §2 の作業者の持ち物の外、起動文も「読めるが変えない」「場面だけを特別扱いする直しは [止める]」と定めている。原因の読みは round_3/ROOTCAUSE.md §F に書いた。i0-r1-14〜17 は第 1 周から、場面係が起こされずに同じ原因のまま 3 周目に入っている(同じ未達理由の数えは台本が行う)。
- 全試験(PYTHONPATH=src python -m pytest)は回していない。起動文の指示どおり自分の項目と核の試験だけを回した。代わりに、src と scripts と tests/bt の外に bot.bt を import するファイルが無いことを grep で確かめた(出力 0 件)。

## 外部の道具を入れたときの §4 の検査の結果

入れていない(外部の道具は導入も実行もしていない。ネットワークも使っていない。場面集の実行は既存の run_battery.py で new_impl・mutant・current_impl の 3 つだけを scratchpad に書き出して走らせた)。

## リードに聞くこと

- history_limit の意味を「型ごとに最新の N〜2N 件を残す(全体は型が残したものの和)。捨てた部分に掛かる読み出しは HistoryTruncatedError で断る」とした。これで、範囲も件数も付けない ctx.visible_events() は、何かが捨てられた後は例外になる(第 2 周の批評家の試験 test_i0r2_history_limit_views_disagree.py はこの呼び方をしているので例外で落ちる)。捨てた後の全部の読み出しを「残した分を返す」と定める読み方もあるが、それは指摘の後半(黙って短い答え)に当たると読んで取らなかった。この読みは要件の逐語には無い(要件は history_limit に触れていない)。
- 場面係が第 1 周から起こされておらず、場面集の指摘(i0-r1-14〜17 → i0-r2-05・06・08・09)が同じ原因のまま 3 周目に入っている。作業者の周では直せない(持ち物の外)。場面係を起こすか、台本の数えでどう扱うかを決めてほしい。

## この周で変えた構造

(1) 「まだ何も無い」を時刻の値(0)で表すのをやめ、FIFO の路を 1 つの型 _FifoChannel(前の時刻は None で始まる)にし、注文の口の「今」・待ち行列の鍵の 3 つ目・FillNotice.venue_time_ns からも定義域の中の既定値を外した。(2) 取消の答え待ちを注文ごとの bool から件数 cancels_in_flight に替え、取引所に 1 つの取消へ答えをちょうど 1 つ返させ、取消の成立の通知に何への答えか(answers: cancel / new / venue)を載せて、答えと要求を 1 対 1 に結んだ。(3) 履歴の保持を 2 つの入れ物・2 つの規則から、型ごとの 1 つの規則(全体は型が残したものの和)を持つ DeliveredHistory(history.py)に替え、捨てた事実を型ごとに持って、捨てた部分に掛かる読み出しを HistoryTruncatedError で断るようにした。
