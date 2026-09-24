# 作業者の報告(作る:0#4、agent ab04d50cbd9451c11。Workflow の記録の返り値から逐語で書き出し)

## 変えたファイル

- src/bot/bt/core/engine.py
- src/bot/bt/core/errors.py
- src/bot/bt/core/ordering.py
- src/bot/bt/core/window.py
- src/bot/bt/core/api.py
- src/bot/bt/core/contract.py
- src/bot/bt/core/__init__.py
- tests/bt/item_0/test_bt0_lifecycle.py(新規)
- tests/bt/item_0/test_bt0_paths_rule.py(新規)
- tests/bt/item_0/test_bt0_future_position.py(新規)
- tests/bt/item_0/test_bt0_scene_set.py
- docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/round_4/ROOTCAUSE.md(新規。直す前に書いた根本原因。A = i0-r3-01、B = i0-r3-09、C = 作業者の場面集の試験のずれ、D = 自分で見つけた位置の名指しの穴)

## 足した試験の数

78

## 試験のコマンド

PYTHONPATH=src python -m pytest tests/bt/item_0 tests/bt/critic/item_0 tests/bt/battery/item_0 -p no:cacheprovider(項目 0 = 核なので、自分の項目の試験と核の試験は同じ tests/bt/item_0)。全試験: setsid nohup env PYTHONPATH=src python -m pytest -p no:cacheprovider > /tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/pytest_item0_r4_worker_all.log 2>&1 &

## 試験の末尾の行

tests/bt/item_0 だけ:「341 passed in 5.55s」。tests/bt/item_0 + tests/bt/critic/item_0 + tests/bt/battery/item_0:「1 failed, 394 passed in 59.34s」。全試験:「1 failed, 3281 passed, 4 skipped, 1 warning in 474.79s (0:07:54)」。落ちるのは両方とも同じ 1 件 tests/bt/critic/item_0/test_i0r2_battery_p5_grading.py::test_single_input_form_of_hand_over_order_agrees_with_keeping_one_input_in_order。原因は KeyError: 'distinct_orders'(90 行目)。場面係が p5-hand-over-order の正解を作り直して(起動文「変えた場面」)、正解の辞書から distinct_orders の鍵が無くなった。批評家の試験が、もう無い古い鍵を読んでいる。場面集の規則 8 の「試験自身の誤り」に当たると私は読んだので、試験は変えていない。この試験が確かめようとしていた性質(1 本の入力の形では、入力の順を守れば一致になる)は、今の場面の採点の規則(run_battery.py の _grade_hand_over の same_order_whatever_the_hand_over で、single_input なら真)に入っている。次の周の批評家に確かめてほしい。第 3 周の [止める] i0-r3-01 の試験 test_i0r3_resume_after_exception.py は 2 件とも通るようになった。場面集を新実装に通した結果は 32 場面すべて「正解と一致」、2 回で違う 0。mutant.py --check は OK(変わるのは p4-received-time だけ)。記録は scratchpad の bt/item0_r4_worker_new_impl.tsv と bt/item0_r4_worker_mutant.tsv。

## 要件の各行を満たした根拠(ファイル:行)

- 時刻は UTC の int64 ナノ秒: src/bot/bt/core/time.py:54(TIME_CONTRACT)・74(validate_nanos)。事象の時刻は events.py の Event の検査で、待ち行列のすべての時刻は engine.py の _push で validate_nanos を通す(この周は変えていない)。場面集の P0-2 の 4 場面は新実装で「正解と一致」(scratchpad bt/item0_r4_worker_new_impl.tsv)。
- 事象の型(約定・板の写真・板の差分・足・資金調達・清算・時計・注文の受付/拒否/約定の通知): src/bot/bt/core/events.py:178(Trade)・215(BookSnapshot)・226(BookDelta)・239(Bar)・276(Funding)・288(Liquidation)・306(Clock)・316(OrderAck)・326(OrderReject)・338(OrderFill)・357(OrderCanceled)・372(OrderStateUnknown)。P0-3 の場面はすべて「正解と一致」。
- 戦略は「受け取れた時刻 ≤ 今」の事象しか見られない(構造で): 時刻での名指しは src/bot/bt/core/api.py:544(_time_arg、今より後は LookAheadError)。この周に、位置での名指しを src/bot/bt/core/window.py:25-62(DeliveredEvents。添字 ≥ len と、末尾より後の端を持つ区間は FuturePositionError)で断るようにした。答えの型は api.py:472(return DeliveredEvents(events[lo:hi]))、例外の型は errors.py:49。試験 tests/bt/item_0/test_bt0_future_position.py(名指し 11 通り、届いた範囲の読み出し、乱数 3,000 回)と test_bt0_scene_set.py::test_future_read_attempts_are_refused_not_shortened(時刻で名指す 4 通りは LookAheadError、位置で名指す 5 通りは FuturePositionError)。場面 p4-future-read-attempt は runner の採点で every_attempt_stopped_by_error=true・future_value_obtained=false。
- 決定的な事象の順序(同時刻の並びの規則を明記): src/bot/bt/core/ordering.py:1-41(冒頭の説明。4 つの路は FIFO、時計は頼んだ時刻に届き、同時刻は予約した順)・43-55(入力の流れの併合の規則)・96(TYPE_ORDER)・132-150(_PATHS。段ごとの fifo の旗と時刻の決め方)・160-165(ORDERING_RULE。channels_fifo と not_fifo は表から作る)・181(merge_key)。試験 tests/bt/item_0/test_bt0_paths_rule.py(種 60 通りの乱数の実行で、段ごとに送った順と着いた順を突き合わせる。表の段の名前の集合と、確かめる手続きの集合も突き合わせる)と、既存の test_bt0_ordering.py・test_bt0_channels.py・test_bt0_streams.py。場面 p5-same-time-twice・p5-hand-over-order は、規則を手で当てた並びと一致(runner の採点)。
- 決定的・再現(実行の信頼性): src/bot/bt/core/engine.py:45-57(Lifecycle の説明)・562(failure)・567(_usable)・583-597(step。外へ出た例外は元のまま投げ直し、エンジンを失敗にする)・629(run)・635(result。どちらも失敗と再入を断る)。errors.py:104(EngineFailedError)・114(EngineReentryError)。contract.py:45(CORE_CONTRACT['lifecycle'])。試験 tests/bt/item_0/test_bt0_lifecycle.py(1 歩の中の 18 か所で 1〜3 回目に例外を出す 50 通り、核の例外 4 種、KeyboardInterrupt、再入、戦略が受け止めた例外では失敗にならないこと、乱数 150 回)。批評家の試験 test_i0r3_resume_after_exception.py は 2 件とも通る。
- 戦略の API(事象ごとの呼び出し・発注・取消): src/bot/bt/core/strategy.py:12(on_event)、api.py:514(place_order)・520(cancel_order)・524(set_timer)。P0-6 の場面はすべて「正解と一致」。
- 他項目が差し込む口(約定模型・遅延模型・費用・口座): src/bot/bt/core/interfaces.py:112(FillModel)・132(LatencyModel)・152(CostModel)・159(Account)。場面 p7-cost-per-unit(数量 2 × 1 単位 0.375 = 0.75)を、試験の側に書いた PerUnitCost で満たす(tests/bt/item_0/test_bt0_scene_set.py)。新実装の adapter でも「正解と一致」。

## 満たせなかった行とその理由

- 全試験で 1 件落ちる: tests/bt/critic/item_0/test_i0r2_battery_p5_grading.py::test_single_input_form_of_hand_over_order_agrees_with_keeping_one_input_in_order(KeyError: 'distinct_orders')。場面係が作り直した場面の正解にこの鍵が無くなったのに、批評家の試験が古い鍵を読んでいる。場面集の規則 8 のとおり、試験は変えずに理由をここに書く。
- i0-r3-12([示唆]、状態不明を確定させる読み取り専用の照会の口)は作っていない。固定した要件の差し込み口は約定模型・遅延模型・費用・口座の 4 つで、この口はその外にあるため(リードに聞くことに書いた)。
- 場面集の側の指摘(i0-r3-02〜08・10・11)は、作業者の持ち物の外なので直していない。起動文によれば場面係がこの周の前に直した。作業者は読んだだけで、tests/bt/battery/item_0/ は 1 行も変えていない。

## 外部の道具を入れたときの §4 の検査の結果

入れていない。外部の道具の導入も実行もしておらず、ネットワークも使っていない。場面集の実行は、既存の run_battery.py で new_impl と mutant の 2 つを走らせ、結果を scratchpad に書き出しただけ。

## リードに聞くこと

- 起動文が示す委任文の指紋は 362bf666dfac(コミット ebbaf34 の版)。今の作業木の委任文は a25b24aa10c9(コミット 385172e、sha256sum | cut -c1-12 で確かめた)。差は §0 の「無駄を出さない」の行に L-429(opus は claude-opus-5-5)を足した 1 行だけで、この周の作業の規則には触れていない。今の版を全部読んで、それに従った。VERDICTS に記録があるのは 362bf666dfac の版なので、指紋の記録を今の版に合わせるかどうかはリードが決めてください。
- 場面集の adapter tests/bt/battery/item_0/adapters/new_impl.py:394 は、核の規則の出所を「src/bot/bt/core/ordering.py 43-55 行」と行番号で引いている。この周に ordering.py の冒頭の説明を書き直したが、引かれている節(「Merging input streams」)は今も 43〜55 行にある(行数を合わせた)。行番号での引用は、核の文を直すたびにずれる形。場面係に、ORDERING_RULE['source_merge'] のように名前で引く形へ替えてもらうかどうかを決めてください。
- 履歴の読み出しの答えの型を、素のタプルから DeliveredEvents(タプルの派生)に替えた。位置で未来を名指すと、FuturePositionError で断る。例: 4 本しか届いていないときの bars[4:5]・bars[3:5]・bars[:5]。今までは空や短いタプルを黙って返していた。一方、bars[-10:] のように先頭より前へはみ出す区間は、過去の側なので今までどおり切り詰める。bars[len(bars):](末尾から先 = まだ何も無い)も空を返す。この線の引き方は要件の逐語には無く、私が p4-future-read-attempt の正解(「名指した読み出しが全部例外で止まる」「空・切り詰めは素通り」)と、時刻での名指しの規則(i0-r1-08)に揃えて決めた。これでよいか確かめてください。
- i0-r3-12([示唆]): CLAUDE.md §1 の reconcile_unknown に当たる読み取り専用の照会(戦略から取引所へ状態を問い合わせる路)を、核の口として持つかどうか。固定した要件の 4 つの差し込み口の外なので、この周では作らなかった。項目 2(注文と取引所の規則・異常系)で要るなら、核に口を足す判断が要ります。

## この周で変えた構造

(1) エンジンに寿命の状態を持たせた。step() から外へ出た例外は、種類を問わず元のまま投げ直し、エンジンを「失敗」にする。以後の step/run/result は EngineFailedError で断り、途中の状態から結果を作らない。戦略の呼び出しの中から同じエンジンを呼ぶ再入は EngineReentryError で断る。1 歩を不可分にする直し方は取らなかった。戦略と差し込み口の中身は核が巻き戻せないため(i0-r3-01)。(2) 並びの規則を、段ごとに fifo の旗と時刻の決め方を持つ 1 つの表(_PATHS)に替えた。先入れ先出しの一覧(channels_fifo)は手で持たず、表から作る。時計は路ではなく、頼んだ時刻に届く予約として書き直した。表の段ごとの主張は、振る舞いの試験で段ごとに確かめる(i0-r3-09)。(3) 履歴の読み出しの答えを、位置の規則を持つ DeliveredEvents 型(タプルの派生)に替えた。届いた最新より後の位置を添字や区間の端で名指すと、FuturePositionError(LookAheadError かつ IndexError)で断る。時刻での名指しと同じく、黙って短い答えは返さない(自分で見つけた穴。ROOTCAUSE.md の D)。
