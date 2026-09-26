# 作業者の報告(作る:0#8、agent ababf383cbcfebd3a。Workflow の記録の返り値から逐語で書き出し)

## 変えたファイル

- src/bot/bt/core/window.py
- src/bot/bt/core/values.py
- src/bot/bt/core/engine.py
- src/bot/bt/core/api.py
- src/bot/bt/core/history.py
- src/bot/bt/core/contract.py
- tests/bt/item_0/test_bt0_r8_named_position_grid.py
- tests/bt/item_0/test_bt0_r8_sender_adversary.py
- tests/bt/item_0/test_bt0_future_position.py
- tests/bt/item_0/test_bt0_paths_rule.py
- tests/bt/item_0/test_bt0_queue_key.py
- docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/round_8/ROOTCAUSE.md

## 足した試験の数

67

## 試験のコマンド

PYTHONPATH=src python -m pytest -p no:cacheprovider(全試験。setsid nohup で切り離し、ログ <scratchpad>/bt/pytest_item0_r8_worker_full2.log)/ 周の途中: PYTHONPATH=src python -m pytest tests/bt/item_0 tests/bt/critic/item_0 -p no:cacheprovider / 場面集: PYTHONPATH=src python3 tests/bt/battery/item_0/run_battery.py --target new_impl --out <scratchpad>/bt/item0_r8_worker_battery_new_impl.tsv(1 回だけ)

## 試験の末尾の行

全試験(最後の変更の後): 3891 passed, 6 skipped, 1 warning in 581.44s (0:09:41) / 項目 0 + 批評家: 938 passed, 2 skipped in 117.61s / 場面集(新実装): new_impl: 32 scenes; {'正解と一致': 32}; 2 回で違う=0。この 1 回は最後の変更(受け手に渡す時刻の int を渡すたびに新しく作る)の前に回した。その変更は同じ値の新しい int を渡すだけで、変更の後に全試験と項目 0 の試験を回し直した

## 要件の各行を満たした根拠(ファイル:行)

- P0-1 事象駆動: src/bot/bt/core/engine.py:531(CoreEngine)、671(優先度つき待ち行列への積み)、741(_step が 1 件ずつ処理)。この周は構造を変えていない。場面集の p1 の場面は「正解と一致」
- P0-2 UTC の int64 ナノ秒: src/bot/bt/core/time.py:55(TIME_CONTRACT)と 75(validate_nanos。as_int を通り、values.py:208 で新しい int に作り直す)。場面集の p2 の場面は「正解と一致」
- P0-3 8 種の事象の型: src/bot/bt/core/events.py:52(EventType)、196〜391(型ごとの class)、408(ALL_EVENT_CLASSES)。どの型も、受け取った所で engine.py:500 で作り直す。敵対者の格子 tests/bt/item_0/test_bt0_r8_sender_adversary.py:394 で、12 の事象の class すべての全ての欄を試した。場面集の p3 の場面は「正解と一致」
- P0-4 構造でルックアヘッドを不能にする: src/bot/bt/core/window.py:59(役ごとの範囲の表)、158(resolve_key: 切り詰める前に置いて検める)、208・280(DeliveredEvents と index)、292・346(EventWindow)、src/bot/bt/core/history.py:36(DeliveredList: 同じ規則を当て、外からの変更を断る)、src/bot/bt/core/api.py:537・684(時刻の検めに核の時刻を使う)。試験: tests/bt/item_0/test_bt0_r8_named_position_grid.py:198・224・255・285・345・410・447・491・511。批評家の試験 test_i0r7_backward_answer_negative_bounds.py は通った。場面集の p4-future-read-attempt は「正解と一致」
- P0-5 決定的な並び: src/bot/bt/core/ordering.py:161(ORDERING_RULE)と 182(merge_key)。この周は変えていない。配達の要約は直す前と直した後で同じ 35269aeea5ca。tests/bt/item_0/test_bt0_paths_rule.py(中身の列で FIFO を検める形に直した)と test_bt0_queue_key.py は通った。場面集の p5 の場面は「正解と一致」「2 回の実行で同じ」
- P0-6 戦略の API(事象ごとの呼び出し・発注・取消): src/bot/bt/core/strategy.py:12(on_event)、src/bot/bt/core/api.py:655(place_order)・661(cancel_order)・665(set_timer)、src/bot/bt/core/engine.py:878(_drain: コールバックの終わりに出口の箱から取り、作り直し、核の時刻で送る)。場面集の p6 の場面は「正解と一致」
- P0-7 差し込み口: src/bot/bt/core/interfaces.py:153(FillModel)・173(LatencyModel)・193(CostModel)・200(Account)・226(SOCKETS)。受け手ごとの写しは engine.py:691・902・925・928・958・980・996・1042・1050・1074。場面集の p7 の場面は「正解と一致」
- 信頼性(路を渡る物): src/bot/bt/core/values.py:132(BUILD)・470(renew)・484(copy_carrier)・519(rebuild_carrier)、src/bot/bt/core/contract.py:15(core-10)・78(scope)・106(ownership)。試験は tests/bt/item_0/test_bt0_r8_sender_adversary.py の 32 件(運び手 20 × 欄 × 種類の格子と、エンジンの全ての路の全ての受け手)

## 満たせなかった行とその理由

- 満たせなかった要件の行として挙げる物: 無し(P0-1〜P0-7。判定は批評家と監査役に任せる)。
- 【吟味(1) i0-r7-01 を直した根拠】src/bot/bt/core/window.py:59-73(役ごとの範囲の表と、その文 POSITION_RULE_TEXT)、window.py:110-205(_named / _outside / resolve_key / resolve_search: 全ての境界を切り詰める前に置いて検める)、window.py:208 以降(DeliveredEvents.__getitem__ と window.py:280 の index)、window.py:292 以降(EventWindow)、history.py:36-78(DeliveredList)、contract.py:43-60(range_by_role / bounds / applies_to)。批評家の試験 tests/bt/critic/item_0/test_i0r7_backward_answer_negative_bounds.py は、直す前は 4 failed、直した後は通った(項目 0 と批評家の 938 件の中)。批評家の試し item0_r7_critic_probe_backward_negslice.py を打ち直した出力(<S>/item0_r8_worker_critic_probes_after.out): r[-6:-5] / r[-6:-4] / r[-5::-1] / r[-6:-5:-1] / r[-5:] / r[-5] → FuturePositionError、a[-6:-5] / a[-5] → BeforeFirstEventError。r[:-5:-1] は [100, 101, 102, 103] を返す。これは後ろ向きの終わり c=-1(最も古いものまで)で、鏡にあたる a[:4] と同じ読み出しである。種類の神託 item0_r7_critic_probe_kind_oracle_keptcoords.py を seed 1〜6 で打った出力: どの seed も wrong 0(<S>/item0_r8_worker_probe_kind_oracle_after.out)。
- 【吟味(1) i0-r7-02 を直した根拠】values.py:132(受け付ける型の表 BUILD。どの型も新しい物を作り、同じ物を返すのは None / True / False だけ)、values.py:83-129(型ごとに、その型自身の方法と slot で読んで作り直す。Fraction は values.py:115)、values.py:208(_plain_scalar)、values.py:244(as_text)、values.py:321-339(FrozenDict の中の表を mappingproxy にした)、values.py:409(_frozen_pairs)、values.py:470・484・519(renew / copy_carrier / rebuild_carrier)。engine.py:332・500(データ源の事象を受け取った所で作り直す)、engine.py:878-913(出口の箱から取る所で作り直し、送った時刻は核の時刻にする)、engine.py:1007(報告を取る所で作り直す)、engine.py:691・902・925・928・958・980・996・1042・1050・1074(受け手ごとの写しと時刻の int)、engine.py:786 以降と engine.py:341(結果の写し)、api.py:197(fresh_request)。批評家の試験 test_i0r7_fraction_in_extra_stays_live.py は、直す前は 1 failed、直した後は通った。批評家の試し item0_r7_critic_probe_frozen_private.py は、試しの中の `._map["a"] = 999` の行が、いまは読み取り専用の mappingproxy なので TypeError で止まり、Fraction の部分まで進まない。その行だけを try で包んだ写し <S>/item0_r8_worker_probe_frozen_private_wrapped.py の出力: 'venue saw at 1700000010000000000 ... extra {'d': {'a': 1}, 'f': Fraction(1, 3)}'(<S>/item0_r8_worker_probe_frozen_private_wrapped.out)。批評家のファイルは変えていない。
- 【吟味(2) 同じ根の全箇所】docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/round_8/ROOTCAUSE.md の §D の表に 9 行書いた。族 A: 窓・背後の列・index()。族 B: 出口の箱・結果の見え方・ctx.now_ns・送る前に壊した FrozenDict・時刻の int・Decimal の子と Fraction の子の扱い。どれも同じ構造で直した。
- 【吟味(3) 試験】項目 0 と批評家の試験: 938 passed, 2 skipped。全試験: 3891 passed, 6 skipped。場面集の新実装: 32 場面すべて「正解と一致」「2 回の実行で同じ」。規則 8(試験自身の誤りで落ちる批評家の試験): 該当なし。
- 【吟味(4)(6) 敵対者の試験を先に書いた記録】名指しの試験 tests/bt/item_0/test_bt0_r8_named_position_grid.py と、送り手の敵対者の試験 tests/bt/item_0/test_bt0_r8_sender_adversary.py は、規則を直す前に書いた。直す前の実装(git archive で scratchpad に取り出したもの。pytest の pythonpath を -o で差し替えて当てた)に当てた結果: 名指しは 32 failed / 2 passed(<S>/item0_r8_worker_grid_on_head.log)、敵対者は 23 failed / 1 passed(<S>/item0_r8_worker_adversary_on_head.log。Fraction の書き換えが LIED として届く、受け手の書き換えが核自身の読みに届いて ValueError で止まる)。一方、背後の列・核の時刻・結果の見え方・出口の箱・送る前に壊した値の 5 つは、規則と同じ段で書いた試験である。直す前の実装に当てると 9 failed / 1 passed(<S>/item0_r8_worker_later_tests_on_head.log)。時刻の int の試験は、1 つ前の版(4f0bb0e)に当てると two receivers share で落ちた。列に入れなかったもの(|歩幅|>3、len+3 を超える境界(±10**30 だけ別に試した)、基の型の方法を直に呼ぶこと、ctypes、核の gc と呼び出しの積み重ねを覗くこと、列挙の要素のような定数など)は、両方の試験ファイルの説明の文に書いた。
- 【吟味(4) 厳しい批評家が挙げそうな候補と、何をしたか】(a) tuple.__getitem__(ans, key) や list.__getitem__(win._log, key) のように基の型の方法を直に呼ぶ → 直していない。契約 contract.py:55 の applies_to に規則の範囲の外と書いた(Python では止められない)。(b) tuple(ans)[4:5] や ans + () → 答えではない素の tuple なので、同じ applies_to に書いた。(c) visible_events(n=5) が届いた件数より少なく返す → n は位置の名指しではなく「最後の n 件まで」の絞り込み(api.py の説明の文)なので、変えていない。(d) 戦略が私的な属性で _StrategyContext__now や DeliveredEvents の _place を書き換える → 自分を欺くだけなので、範囲の外として window.py の説明の文と契約の scope に書いた。公開の ctx.current_event を書き換えても ctx.now_ns と時刻の検めは動かないようにした(api.py:465・495・537、試験は grid の 491 行)。(e) 速さ → 測った値を ROOTCAUSE §D に書いた(下の「リードに聞くこと」)。(f) 出口の箱に発注口を通さない物を入れる → OrderApiError で断るようにした(engine.py:878-913、試験 6 本)。(g) 送る前に slot を壊した FrozenDict や Fraction → 核の中の TypeError ではなく、API の誤りとして断るようにした(values.py:115・409、試験 1 本)。(h) 受け手どうしで時刻の int を共有する → 渡すたびに新しく作るようにした(engine.py の 8 か所)。
- 【吟味(5) 場当たりの直しの有無の確かめ】場面集は読んだだけで、変えていない。場面だけを特別扱いする分岐は足していない。閾値と既定値は変えていない。消した試験は無い。書き直した自分の項目の試験は 3 本。test_bt0_future_position.py は、旧い神託が「負の区間の境界は符号で切り詰める」という実装の場合分けを写していたので、新しい原則に直した。旧い試験で a[-10:] が 4 件を返すとしていた行は、BeforeFirstEventError を期待する形にした。test_bt0_paths_rule.py と test_bt0_queue_key.py の 1 本は、受け手が id() で物を見分けていた。新しい設計では受け手の物が全部別の物になるので、中身の列と合流の順で見分ける形に直した。

## 外部の道具を入れたときの §4 の検査の結果

外部の道具は入れていません(pip install も venv も作っていません)。ネットワークも使っていません。

## リードに聞くこと

- 速さ: 約定 5 万件の測り(<S>/item0_r8_worker_speed.py)で、直す前は 12.31 マイクロ秒/事象(読み出しあり 21.02)、直した後は 29.43〜30.56(読み出しあり 38.61〜42.19)でした(<S>/item0_r8_worker_speed_after.txt)。受け手ごとの写しと、受け取った所での作り直しの分です。配達の要約(digest)は直す前と同じ 35269aeea5ca です。固定した要件に速さの行は無いので、測った値だけを書きました。速さを要件にするかどうかはリード(またはオーナー)が決めることなので、ここに挙げます。
- 振る舞いの変化が 2 つあります。(1) 答えの最も古い事象より前へはみ出す負の区間の境界(4 件の答えに a[-10:] など)は、切り詰めずに断ります(何も無い所なら BeforeFirstEventError)。第 4 周から a[:10] を断っていたのと同じ扱いです。後の項目の戦略が「最後の k 件まで」の意味で [-k:] を書くと、届いた件数が k より少ないときに止まります(代わりの書き方は visible_events(n=k))。(2) Decimal の子を受け付けるようになりました(基の型の方法で読み、Decimal として作り直す)。どちらも契約 core-10 に書きました。後の項目への周知が要るかどうかを判断してください。

## この周で変えた構造

名指しの位置: 答え・文脈が持つ窓・その背後の履歴の列(新設の history.DeliveredList)のどれでも、明示された境界は符号や向きによらず、まず答えの座標に置いてから役ごとの両側の範囲の表 1 つ(window.POSITION_RULE、resolve_key)で検めます。tuple での切り詰めは、その後にしか走りません。送り手と受け手の間の物: 「そのまま渡してよい型の一覧」(_SCALARS)を捨てました。核は、送り手から受け取った所で運び手をコンストラクタで作り直し、以後はそれしか持ちません(データ源の事象・出口の箱の要求・取引所の報告・強制注文)。受け手(遅延の模型・取引所・口座・費用の模型・戦略・結果)には、呼ぶたびにその受け手だけの写し(copy_carrier と renew。組み込みの型の値と時刻の int も新しく作る)を渡します。
