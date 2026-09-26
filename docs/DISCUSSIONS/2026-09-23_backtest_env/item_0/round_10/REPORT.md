# 作業者の報告(作る:0#10、agent a506cd0704a223e41。Workflow の記録の返り値から逐語で書き出し)

## 変えたファイル

- src/bot/bt/core/api.py
- src/bot/bt/core/engine.py
- src/bot/bt/core/history.py
- src/bot/bt/core/values.py
- src/bot/bt/core/window.py
- src/bot/bt/core/contract.py
- tests/bt/item_0/test_bt0_r10_history_read_oracle.py(新規)
- tests/bt/item_0/test_bt0_r10_strategy_side.py(新規)
- tests/bt/item_0/test_bt0_history_limit.py(書き直し: 神託を「制限なしの答えが落とした事象を含むときだけ断る」に。第 9 周の神託は実装の条件を写していた)
- tests/bt/item_0/test_bt0_future_position.py(書き直し: test_an_empty_answer_cut_inside_the_dropped_part_is_refused → …_is_placed_there。空の答えは断らず、落とした位置の中・前に位置づける設計に変えたため)
- tests/bt/item_0/test_bt0_engine_source.py(1 行: eng._history.overall → eng._history.count()。履歴の列が戦略の側の入れ物へ移ったため)
- tests/bt/item_0/test_bt0_r9_context_graph.py(書き直し: 核の状態の歩きを _StrategySide で止め、規則 2 を「届く変わりうる物は全部戦略の側の物」に。Enum の要素と結び付いた方法そのものはプログラムとして除く)
- tests/bt/item_0/test_bt0_r9_reachable_state_adversary.py(test_a_replaced_outbox_is_refused → test_a_replaced_outbox_attribute_changes_nothing_that_is_sent に書き直し。説明の「__class__ の代入は核の物が slot か組み込みの型なので列の外」という事実と違う理由を直し、第 10 周の格子を指す)
- docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/round_10/ROOTCAUSE.md(新規。直す前の根本原因 §A〜§D と、直しの途中で見つけた同じ根の箇所 §E)
- (git commit はしていない。作業の途中の版はリードのチェックポイント 24329ca に入っている)

## 足した試験の数

163

## 試験のコマンド

PYTHONPATH=src python -m pytest tests/bt/item_0 tests/bt/critic/item_0 -p no:cacheprovider(このほか、場面集 1 回: PYTHONPATH=src python -m pytest tests/bt/battery/item_0 -p no:cacheprovider / 全試験を切り離して 1 回: PYTHONPATH=src python -m pytest -p no:cacheprovider。ログは /tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/pytest_item0_r10_worker_{mid2,battery,full}.log)

## 試験の末尾の行

項目 0 と核と批評家の試験: 「1333 passed, 2 skipped in 291.03s (0:04:51)」(この周の初めは 1170 passed, 2 skipped)。場面集: 「3 failed, 72 passed in 23.96s」。全試験: 「3 failed, 4300 passed, 6 skipped, 1 warning in 825.32s (0:13:45)」。落ちた 3 件は全部場面集の試験(test_battery_def_grids.py::test_the_machine_agrees_with_the_definition_on_every_cell_run[D]、test_battery_item0.py::test_every_line_the_scene_keeper_writes_is_listed_and_every_marked_line_judged、同 ::test_every_use_of_the_scene_keepers_terms_is_judged)。原因は、場面係が同じ時間に書いている未コミットのファイル tests/bt/battery/item_0/ROOTCAUSE_r10-1.md の行(出力は「('ROOTCAUSE_r10-1.md', 1, '# 項目 0 場面集 — 第 r10-1 回の直しの前の定義、第 2 版…')」「('判断なし', '升目', 'ROOTCAUSE_r10-1.md:13')」)。核とは関係しない。確かめ方: 同じ場面集を直す前の核(コミット 04e3088 の src を git archive で取り出したもの)で回しても、同じ 3 件が落ちる(scratchpad/bt/pytest_item0_r10_worker_battery_oldsrc.log)。

## 要件の各行を満たした根拠(ファイル:行)

- 時刻は UTC の int64 ナノ秒: src/bot/bt/core/time.py 55(TIME_CONTRACT)・75-98(validate_nanos。int64 の範囲外は TimestampUnitError)。この周の変更なし。
- 事象の型(約定・板の写真・板の差分・足・資金調達・清算・時計・注文の受付/拒否/約定の通知): src/bot/bt/core/events.py 52(EventType)。この周の変更なし。
- 戦略は「受け取れた時刻 ≤ 今」の事象しか見られない(構造で): api.py 696-(visible_events)・900(_time_arg。今より後の時刻は LookAheadError)、window.py の POSITION_RULE。この周では history_limit の下でも、返す答えは全部制限なしの答えと同じになった(api.py 790-・807-)。空の答えの位置も事実から出す。格子 tests/bt/item_0/test_bt0_r10_history_read_oracle.py(36 格子 + 批評家の場面 1)が通る。戦略が届く物の class を差し替えても、戦略のコードは on_event の中でしか走らない(engine.py 389-・476-・1063、test_bt0_r10_strategy_side.py の class の差し替えの格子)。
- 決定的な事象の順序(同時刻の並びの規則を明記): ordering.py 161(ORDERING_RULE)。この周の変更なし。配達の要約は直す前と同じ 35269aeea5ca(速さの測りの出力)。
- 戦略の API(事象ごとの呼び出し・発注・取消): api.py 928(STRATEGY_API)・871(place_order)・877(cancel_order)、engine.py 1061(on_event の呼び出し)。この周では、呼び出しを変えられない tuple に結び付けた方法にした(engine.py 476-)。API を通さずに箱へ書いた知らせは、settle で作り直してから API の規則を当てる(engine.py 450-(_settled_request)、values.py 250-(settle))。
- 他項目が差し込む口(約定模型・遅延模型・費用・口座): interfaces.py 226(SOCKETS)、contract.py の sockets。この周の変更なし(試験は差し込み口に記録する受け手を入れて回した)。
- 契約: contract.py 15(CORE_VERSION = core-12)・81-(history_limit)・132-(ownership)・scope の文を、この周の振る舞いに合わせた。

## 満たせなかった行とその理由

- 満たせなかった要件の行: 無し(下は委任文 §3「提出前の吟味」の記録。判定の語は書かず、候補ごとに何をしたかだけを書く)
- (1) 指摘 1 件ごとの直した根拠 — i0-r9-01: api.py 807-(`__refuse_truncated`)と 790-(`__empty_answer`)を、定義(制限なしの答えが落とした事象を含むか)を 1 つの関数で判定する形に作り替えた。history.py 130-(`HistoryLists`、落とした事実の array)・241-/255-(`dropped_in_range`・`dropped_before`)。contract.py 81- の history_limit の文を振る舞いに合わせた。コマンドと出力: 批評家の試し `item0_r9_critic_probe_history_until.py` → `until_ns=T0+3s -> [1, 2] place (0, 1, 3, 0)` / `n=1, until_ns=T0+3s -> [2] place (1, 1, 3, 0)` / `until_ns=T0 (before every event) -> [] place (0, 1, 3, 0)`。批評家の神託 `item0_r9_critic_probe_history_oracle.py 80` → `{'ok': 375671, 'wrong': 0, 'silent_short': 0, 'over_refused': 0, 'place_wrong': 0, 'over_refused_nonempty': 0, 'over_refused_empty': 0}`(直す前は over_refused 55305)。批評家の試験 test_i0r9_history_limit_read_oracle.py は通る(全体の実行に含む)。
- (1) i0-r9-02 (a)(`__class__` を代入した口に、核が on_event の外で書いた): engine.py 389-(`_StrategySide`)・476-(`_context_calls`。変えられない tuple に結び付けた方法)・1063 行(`kill()` だけにした。`port._now` の書き込みと `StrategyContext._revoke` の呼び出しは消した)・1071-(`_drain`。箱は核の参照から list の方法で読む)、window.py 297 行(`type()` で判定)。コマンドと出力: 批評家の試しの find_port は tuple に入らないので口を見つけられず、tuple に入るように 1 行足した版 `item0_r10_worker_probe_port_class_swap_tuple.py` で試した → 直した後は `port class now: Hook` だけで、OUTSIDE の記録も実行の失敗も無い / 直す前の src(04e3088)では `('_now', 1700000001000000000, 'OUTSIDE on_event')` と `run raised: builtins RuntimeError strategy code raised inside the core`。
- (1) i0-r9-02 (b)(閉じ込めをたどると核の持つ物に届く。到達性の試験が関数に入らず、核の状態を名前の一覧で選んでいた): 核の状態は、エンジンから歩いて(関数の閉じ込め・既定値・結び付いた方法の __self__ に入る)`_StrategySide` で止めて出す。名前の一覧は使わない。試し `item0_r10_worker_probe_closure_reach.py` → 全 31 配達で `shared with the core's own state: []`、`callbacks with anything shared: 0`。戦略の側の物(DeliveredList・OrderView・_OrderPort・dict・list・array など)は全部入れ物から届く。試験 test_bt0_r10_strategy_side.py::test_the_strategy_reaches_nothing_of_the_core_s_own_state は通る。出口の箱は振る舞いで見つけ(place_order で 1 つ増える list)、入れ物の中にあること・核の状態から届かないことを確かめる(LEAD_DESIGN §7.4 の 20)。
- (1) 前の周までの [止める]・[直す] の直りの確かめ直し: i0-r8-01・i0-r7-01・i0-r7-02・i0-r8-02・i0-r8-03 の批評家の試験(test_i0r8_order_port_state_written_around_api.py・test_i0r7_backward_answer_negative_bounds.py・test_i0r7_fraction_in_extra_stays_live.py ほか tests/bt/critic/item_0 の全部)は、上の 1333 passed に入っている。批評家の試し `item0_r9_critic_recheck_r8_registry.py` は、この版では口を見つけられず TypeError で止まる(試しが名前で口を探すため)。同じことを確かめる試験として、test_bt0_r9_reachable_state_adversary.py の台帳と箱への書き込みの格子(A〜E の時機)が通る。
- (2) 同じ根の全箇所: 核が、戦略の届く物にその物の class を通して触る箇所を、engine.py・api.py・window.py・history.py で探した。port._now・_drain の object.__getattribute__・_revoke の object.__setattr__・window の isinstance・_take_message の送り手の変換(数の塔)・断りの文の repr(子の __repr__)・Fraction の ABC 判定の 7 か所(ROOTCAUSE §B-1・§E)を直した。探し漏れは class の差し替えの格子で見た。場面 4 時機で、Hook に差し替えた物は StrategyContext・EventWindow・_OrderPort・DeliveredList・OrderView・事象の各 class・OrderRequest・CancelRequest。記録は on_event の外で 0 件、結果は同じ。
- (3) 批評家の試験と場面集の試験: 批評家の試験は全部通る(1333 passed に入っている)。場面集は 3 件落ちる。場面係の書いている途中のファイルが原因で、直す前の核でも同じく落ちる(test_tail)。批評家の試験が試験自身の誤りで落ちるもの(規則 8)は無い。
- (4) 非常に厳しい批評家が [止める] にしそうな候補 → したこと: (a) 「落とした事実を全部残すと、history_limit の記憶の上限が効かない」→ 契約 history_limit に「保つ事象の数を抑え、事実(1 件 2 つの int64)は抑えない」と書いた(contract.py 81-)。上限の要否はリードに聞く。(b) 「戦略の側の物(箱・台帳・列)をエンジンがまだ持つ = §3.4 に反する」→ 入れ物 1 つに分け、核の状態から届かないことを試験で確かめた。箱を配達ごとに新しくする案は取らなかった(持ち続けた箱に後の呼び出しで書いた知らせが、黙って消えるため)。解釈をリードに聞く。(c) 「送った後に知らせの値を子や数の塔に替えると、核が送り手のコードを走らせる」→ settle と格子 (3)。子の方法(repr・eq・hash・変換)が走ったら記録する形で試した(154 升目)。(d) 「空の答えの位置が負になり、窓の規則と食い違う」→ `_checked_place` は空の答えの first を検めない。その位置で名指すと、落とした位置は DroppedPositionError、その前は BeforeFirstEventError になることを、test_bt0_future_position.py の書き直した試験で確かめた。(e) 「速さが落ちた」→ 5 万約定の速さを交互に 2 回測った。直す前 40.19・39.63 / 57.4・54.9 マイクロ秒/事象、直した後 38.73・40.42 / 55.01・55.85(読み出しなし / あり)。配達の要約は同じ 35269aeea5ca(scratchpad/bt/item0_r10_worker_speed_compare.txt)。(f) 「自分の試験を書き換えて通した」→ 書き換えた 5 本と理由は changed_files に書いた。消した試験は無い。どれも設計の変更(断る → 答える、口の属性の差し替え → 断らずに影響なし)に合わせたもの。
- (5) 場当たりの直しの確かめ: 試験だけを特別扱いする分岐・閾値や既定値のずらし・文言合わせ・機能を外すことはしていない。断る読み出しは、定義から二分探索で決める 1 つの関数になった。口の属性の差し替えは、断る関門を消して、呼び出しの行き先を変えられない形にした。
- (6) 敵対者の試験を直す前に書いた。直す前の src で回した出力: `56 failed, 87 passed`(内訳: 履歴の読み出しの格子 36・批評家の場面 1・知らせの値の格子 14・class の差し替え 4 時機・到達性 1。scratchpad/bt/item0_r10_worker_newtests_on_oldsrc.out)。直した後は全部通る。格子の数は機械で出す。履歴の読み出しは 1 試験あたり最大 68,544 升目で、全部を走らせる(LEAD_DESIGN §7.2 の 12)。class の差し替えは時機 A・B・D が 44 対象、C が 62 対象で、全部を走らせる。知らせの値は 154 升目(軸の積と一致することを試験で確かめる)。列に入れなかった物は各試験ファイルの説明の「NOT in the grid(s)」に書いた。

## 外部の道具を入れたときの §4 の検査の結果

入れていない(外部の道具は導入も実行もしていない。ネットワークも使っていない)。

## リードに聞くこと

- LEAD_DESIGN §7.4 の 22「第 10 周で (b) を必ず閉じる(到達性 0)」の読み方を確かめたい。この周の実装では、到達性 0 を次の意味で満たしている: 文脈から関数の閉じ込めまで歩いて届く物のうち、核の状態(エンジンから `_StrategySide` を通らずに届く物)に当たるものが 0 件。一方で、戦略の側の物(写しの台帳・出口の箱・口・履歴の列・落とした事実)は、§7.4 の 19・20 のとおり戦略が届く物で、エンジンは入れ物 `_StrategySide` の中にだけそれを持つ(書くだけで、読むのは箱を 1 度写すときだけ)。「エンジンが持つ物には戦略は 1 つも届かない」という意味なら、台帳と列は配達ごとに作り直すことになり、注文と事象の数に比例して遅くなる(§7.4 の 19 が取らないとした作り)。箱だけは配達ごとに新しくできるが、そうすると、戦略が持ち続けた前の箱に後の呼び出しで書いた知らせは、黙って読まれずに消える。どちらの読みにするか決めてほしい。
- 落とした事象の事実(1 件あたり 16 バイト、型ごとの array)は実行の間ずっと増える。history_limit が抑えるのは保つ事象の数で、事実の数は抑えない(契約 contract.py 81- に書いた)。制限なしの答えと同じ答えを返すか正しく断るには、落とした事象の時刻が全部要る(隙間があるので両端だけでは足りない)。事実の数にも上限が要るかは要件の外なので、判断を求める(上限を付けるなら、上限を超えた部分では断りすぎが戻る)。
- i0-r9-04 [示唆](集合の反復の順が PYTHONHASHSEED で変わる)は、この周では核の集合の型を変えていない。変えると契約の plain_data の規則が変わり、固定した要件の外の判断になる。項目 8(再現性)の要件を固定するときに、PYTHONHASHSEED を実行記録に載せるか、核が集合を決まった順で持つかを決めてほしい。
- 場面集の試験が 3 件落ちる。原因は、場面係が同じ時間に書いている未コミットの tests/bt/battery/item_0/ROOTCAUSE_r10-1.md(直す前の核でも同じ 3 件が落ちる)。作業者は場面集を変えていない。場面係の直しが終わった後に場面集を回し直す必要がある。
- 監査役の 2 件(round_9 の JUDGES.md が無い / DEFINITIONS.md の「未決」)は作業者の持ち物の外なので、手を付けていない。LEAD_DESIGN §7.4 の 21・23(コミット 3416e9c)でリードと場面係の側に割り当てられたことを読んだ。起動文 (3) の候補 35 の権限の分類器の拒否も、場面係・監査役あての項目なので扱っていない。

## この周で変えた構造

(1) 戦略が届いて呼び出しをまたいで残る物(注文の口・写しの台帳・出口の箱・履歴の列と事象の写し・落とした事象の事実)を、エンジンの 1 つの入れ物 `_StrategySide` にまとめた。核の状態はそこを参照しない。核がそこの物に触るのは、自分で作った組み込みの型の入れ物に基の型の C の関数を使うときだけで、物の class は通さない。呼び出しは配達ごとに作る方法で、変えられない tuple(口・台帳・箱・時刻・alive)に結び付けた。口の時刻 `_now` の書き込みと `_revoke` の呼び出しはやめた。箱の知らせは `values.settle` で組み込みの型そのものに作り直してから読む。(2) 履歴を、核の記録 `DeliveredHistory` と戦略の側 `HistoryLists` に分けた。落とした事象は全部について (配達の番号, 受け取った時刻) を型ごとの array に残す。読み出しは、制限なしの答えが落とした事象を含むときだけ断る(二分探索で決める)。空の答えの位置は事実から出す。
