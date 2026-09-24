# 作業者の報告(作る:0#12、agent aa34e2a49faee8527。Workflow の記録の返り値から逐語で書き出し)

## 変えたファイル

- src/bot/bt/core/values.py(型の判断を同一性だけにする is_one_of・derives・is_static・IdTable を新設。class_parts は Python で作った class のモジュールを class の辞書の反復で読み、検索しない。settle は同一性で型を決め、静的な C の数の型(numpy)は C のコードで変換し、Python で書いた数の class は断る。take_int・take_float・take_items を新設。rebuild_carrier は各欄を settle してから作り直す(_as_taken)。_freeze の `in` を is_one_of に)
- src/bot/bt/core/engine.py(_CLASS_TO_TYPE を IdTable に。REPORT_CLASSES との照合を同一性で。_check_delay は take_int、手数料は take_float。約定模型の報告の列と口座の強制注文の列は take_items。_pull と _take_reports は作り直しの Unsettled を入口の誤り(EventValidationError / VenueProtocolError)に。_show は dict.__setitem__ をやめ、戦略の側の shown の列へ list.append。_StrategySide に shown を追加し、呼び出しの tuple に載せる。dropped_of は read_dropped を呼ぶ。_VenueLedger.apply は型を確かめてから名前を読む。説明の文を事実に合わせた)
- src/bot/bt/core/api.py(_bring_up を新設し、口の関数(place・cancel・order・open_orders・knows)の初めで、戦略の呼び出しの中で台帳を shown から更新する。port_* の引数に shown を追加。_OrderPort に _shown。fresh_request の断りの文を type_name に)
- src/bot/bt/core/history.py(DroppedFacts と read_dropped を新設。核は落とすたびに新しい array('q') の塊を戦略の側の pending の列へ list.append するだけにし、array.extend をやめた。まとめるのは戦略の読み出しの中で行い、まとめる先が buffer を書き出していれば新しい配列を作る。dropped_arrays を dropped_facts に)
- src/bot/bt/core/contract.py(core-14。scope・lifecycle・ownership・type_decisions・plug_in_answers・出口の箱の settle・history_limit の文。対象外に「送出中の例外のメタクラスの __subclasscheck__(解釈系が聞く)」「numbers の ABC に登録・派生したフックつきの class」を書いた)
- tests/bt/item_0/test_bt0_r12_party_hooks.py(新規。格子 1・2 と、値ごとの取り方の試験、例外の後の呼び出しの試験。全 126 件)
- tests/bt/item_0/test_bt0_r11_foreign_objects.py(第 11 周の自分の試験 test_the_core_s_own_reference_lists_are_not_reached の、核が持つ物の列を新しい属性 dropped・_pending に書き換えた。消した試験は無い)
- docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/round_12/ROOTCAUSE.md(新規。直す前の根本原因 §0〜§B と、直しの途中で見つけた同じ根の箇所 §C、リードの §8.6 の 31 との対応 §D)

## 足した試験の数

126

## 試験のコマンド

PYTHONPATH=src python -m pytest tests/bt/item_0 tests/bt/critic/item_0 -p no:cacheprovider(ほかに場面集の試験を 1 回: PYTHONPATH=src python -m pytest tests/bt/battery/item_0 -p no:cacheprovider。全試験は setsid nohup で切り離して 1 回: PYTHONPATH=src python -m pytest -p no:cacheprovider。ログは /tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/r12_worker/pytest_item0_r12_worker_{mid4,battery,full}.log)

## 試験の末尾の行

項目 0・核・批評家の試験: 「13 failed, 1792 passed, 2 skipped in 382.23s (0:06:22)」。場面集: 「78 passed in 37.09s」。全試験: 「13 failed, 4765 passed, 6 skipped, 1 warning in 894.97s (0:14:54)」。落ちる 13 件は、どの実行でも tests/bt/critic/item_0/test_i0r11_covers_within_scene_input.py の 13 場面(i0-r11-02。相手は場面集で、場面係の持ち物)だけ。実装の側で落ちる試験は 0 件(`grep "^FAILED" … | grep -vc covers_within` → 0)。

## 要件の各行を満たした根拠(ファイル:行)

- 時刻は UTC の int64 ナノ秒: src/bot/bt/core/time.py:55(TIME_CONTRACT)・75(validate_nanos)。この周の変更なし
- 事象の型(約定・板の写真・板の差分・足・資金調達・清算・時計・注文の受付/拒否/約定の通知): src/bot/bt/core/events.py:52(EventType)。この周の変更なし
- 戦略は「受け取れた時刻 ≤ 今」の事象しか見られない(構造で): api.py:717(visible_events)・921(_time_arg。今より後は LookAheadError)、window.py:61(POSITION_RULE)。落とした事実を読み出しの中でまとめる作り(history.py:158 read_dropped)に変えたあとも、批評家の神託で 908,526 件が ok、wrong・silent_short・over_refused・place_wrong はどれも 0 件
- 決定的な事象の順序(同時刻の並びの規則を明記): ordering.py:161(ORDERING_RULE)。この周の変更の前と後で配達の要約が同じ(cbc4e7073082 / 23b27a7a143c、<W>/item0_r12_worker_digest_compare.out)
- 戦略の API(事象ごとの呼び出し・発注・取消): api.py:949(STRATEGY_API)・892(place_order)・898(cancel_order)、engine.py:1117(on_event の呼び出し)。台帳は口の呼び出しの中で更新する(api.py:509 _bring_up)。核が外の者の呼び出しの外で、その者のコードを走らせないこと: tests/bt/item_0/test_bt0_r12_party_hooks.py:824(格子 1)・932(格子 2)
- 他項目が差し込む口(約定模型・遅延模型・費用・口座): interfaces.py:226(SOCKETS)。答えの取り方は values.py:395(settle)・481(take_int)・490(take_float)・503(take_items)、engine.py:546(_check_delay)・1223(強制注文)・1305(_take_reports)
- 契約: contract.py:15(core-14)・81(history_limit。まとめる前の塊)・95(scope。全ての相手に当てる規則と対象外)・159(ownership。list.append だけ)・210(plug_in_answers)・222(type_decisions。同一性)

## 満たせなかった行とその理由

- 満たせなかった要件の行: 無し。以下は委任文 §3「提出前の吟味」の記録。判定の語は書かず、候補ごとに何をしたかだけを書く。<S> = /tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt、<W> = <S>/r12_worker
- (1) i0-r11-01 を直した根拠: values.py:252 class_parts(Python で作った class は _PROXY_ITEMS(_TYPE_DICT(t)) を反復する。検索しない)、values.py:219 IdTable、values.py:196・204 is_one_of・derives、engine.py:598 _CLASS_TO_TYPE、engine.py:1122 _show(list.append)、api.py:509 _bring_up、api.py:216 fresh_request。コマンド `PYTHONPATH=src python -m pytest tests/bt/critic/item_0/test_i0r11_class_dict_key_runs_foreign_code.py tests/bt/critic/item_0/test_i0r11_pinned_dropped_facts_fail_the_core_step.py tests/bt/critic/item_0/test_i0r11_history_limit_exact_refusal.py -p no:cacheprovider` の結果は、直す前が「13 failed, 10 passed」、直した後が「23 passed in 0.81s」。批評家の試し 6 本を回し直した(<W>/item0_r12_worker_recheck_r11_critic_probes.out)。結果は module_key_nometa → 'step/run/result -> EngineFailedError | is EngineFailedError: True' / 'Key.__eq__ ran in: []'、outbox_key → 'Msg -> run raised OrderApiError | OrderApiError: True' / '[]'、registry_key → 'raise: True -> run ok [('mine-1', 'FILLED')]' / 'strategy code outside on_event: 0 []'、outbox_metahash(補足のメタクラスの __hash__)→ 'run raised OrderApiError' / '[]'
- (1) i0-r11-03 を直した根拠: history.py:134 DroppedFacts、history.py:158 read_dropped、history.py:239(核が行うのは塊の list.append だけ)。批評家の試し array_export の結果は 'hold views: True -> run ok, events 12 digest 06cfb720ce34'(持たないときと同じ)。批評家の試験 test_i0r11_pinned_dropped_facts_fail_the_core_step.py は通る(上の 23 passed に入っている)
- (1) i0-r9-01 の確かめ直し: 批評家の神託 `PYTHONPATH=src python3 <S>/r11_critic/item0_r11_critic_probe_history_oracle2.py 1001 1060` → {'ok': 908526, 'refused_ok': 205930, 'wrong': 0, 'silent_short': 0, 'over_refused': 0, 'place_wrong': 0, 'ex': []}(<W>/item0_r12_worker_recheck_history_oracle2.out)。落とした事実を読み出しの中でまとめる作りに変えたあとの結果である。test_bt0_r10_history_read_oracle.py と test_i0r11_history_limit_exact_refusal.py も通る
- (1) i0-r9-02 の確かめ直し: 批評家の試し `PYTHONPATH=src python3 <S>/r11_critic/item0_r11_critic_probe_reach_swap.py` → 'callbacks with core state shared: []' / 記録用の class を付けた型の一覧に新しい DroppedFacts が入る / 'uses of those classes OUTSIDE on_event: [] count 0' / 'digest 780a441aafb0cf8f'(<W>/item0_r12_worker_recheck_reach_swap.out)
- (2) 同じ根の全箇所: 族を「核が外の物に、その物のコードが走りうる操作をする」と読み直した。操作は、ハッシュ表の検索と書き込み(鍵の __eq__)、探す鍵の hash、タプルの in(==)、サイズの変更(buffer)、真偽・長さ・反復、数の変換、普通の属性の読みである。この族として探し、直したのは次のとおり(ROOTCAUSE §A の 1・§C): class_parts、BUILD.get(t)(values.py の 2 か所)、_CLASS_TO_TYPE.get、REPORT_CLASSES との in(engine.py の 2 か所と _is_cancel_answer)、_base_of・_settle の in mro、_freeze の not in、台帳への dict.__setitem__、array.extend、`raw or ()` とその反復、口座の `or ()` とその反復、_check_delay と手数料の数の変換、rebuild_carrier の欄、fresh_request の __module__・__qualname__、_VenueLedger.apply の名前の読みの順序。直す前の試し <W>/item0_r12_worker_probe_same_root.py の出力は、Answer.__bool__・__iter__、Meta.__eq__、Num.__index__、NameMeta __module__/__qualname__ が呼び出しの外で走った(.before.out)。直した後は 4 つとも 'party code outside its call: []'(.after.out)
- (3) 批評家の試験と場面集の試験: tests/bt/critic/item_0 のうち実装の側の試験は全部通る。落ちるのは test_i0r11_covers_within_scene_input.py の 13 件だけで、相手は場面集(i0-r11-02。場面係が直す)。場面集の試験は 78 passed。規則 8 に当たる試験(批評家の試験自身の誤りで落ちるもの)は無い
- (4) 非常に厳しい批評家が [止める] にしそうな候補と、したこと: (a) 「class_parts はまだ外の class の __qualname__ と __module__ を読んでいる(§8.6 の 31)」→ C の欄の読みと辞書の反復だけにした。格子 1 の dict の置き場所で、140 の名前それぞれと同じ hash の鍵を置いて、鍵が走らないことを確かめた。読み方はリードに聞く。(b) 「台帳の更新を口の呼び出しまで遅らせると、shown の列が伸びる」→ 伸びるのは、口の最後の呼び出しの後に見せた見え方の数だけで、注文の変化の数で上が決まる。契約 ownership に書いた。(c) 「落とした事実の配列は今も buffer を出す(§8.6 の 31 の 2 つの案と違う)」→ 核はその配列を二度と変えない。int の list は 88.2 バイト/件(<W>/item0_r12_worker_fact_bytes.out)なので採らなかった。リードに聞く。(d) 「振る舞いが変わった」→ 変わったのは 3 つ。Python で書いた数の class の差し込み口の答えを断る。Sequence の答えは list か tuple に限る(生成器は断る)。出口の箱で numpy の数を受ける。契約 plug_in_answers と scope に書き、試験を足した(test_a_c_number_class_s_answer_is_taken…・test_a_sequence_answer_that_is_not_a_list_or_tuple_is_refused)。(e) 「送出中の例外のメタクラスの __subclasscheck__ を格子から外した」→ 核が無くても解釈系が聞く(<W>/item0_r12_worker_dbg2_interpreter_subclasscheck.out で 3 回)。例外が抜けた後の step・run・result がメタクラスの方法を 1 つも走らせないことを、15 入口で試験に固定した。契約 scope に書いた。(f) 速さ → 同じ入力を直す前と後で 2 回ずつ実行した。配達の要約は同じ(台本の実行 cbc4e7073082、5 万約定 23b27a7a143c)。1 事象あたり、直す前 67.78・65.94 マイクロ秒、直した後 68.05・67.03 マイクロ秒(<W>/item0_r12_worker_digest_compare.out)
- (5) 場当たりの直しの確かめ: 試験だけを特別扱いする分岐、閾値や既定値のずらし、文言合わせ、機能を外すことはしていない。直しは規則 1 つ(ROOTCAUSE §A)を、核が外の物に触る全ての操作に当てたものである。read_dropped が BufferError を受けて新しい配列を作るのは戦略自身の呼び出しの中で、戦略が持つ view が戦略自身の読みを変えないためである(ROOTCAUSE §A の 4)
- (6) 敵対者の試験は直す前に書いた: tests/bt/item_0/test_bt0_r12_party_hooks.py。入力の空間は実装の場合分けからではなく、次の軸で作った。入口(SOCKETS・socket_methods・入力の流れ・戦略)× 宣言した型から出す形(100 の組)× 仕掛け(組み込みの型 13 種の特殊な方法から機械で列べた 81 個、メタクラスは 83 個。1 つずつと全部同時)× 置き場所(class / メタクラス / class の辞書に 140 の名前と同じ hash の鍵)。格子 1 は約 16,600 回の実行、格子 2 は戦略が届く物の全部に buffer の view と鍵を置く。直す前の src(HEAD b7cbd63 を git archive で取り出し、-o pythonpath で指定)では「98 failed, 13 passed」(<W>/item0_r12_worker_newtests_on_oldsrc.out)、直した後は 126 件が全部通る。列に入れなかったもの(作るときの方法、__subclasshook__ と数の ABC、後始末、__class__、ctypes や gc、中身の変更は第 9 周・第 11 周の格子の持ち物、核自身の class、送出中の例外のメタクラスの __subclasscheck__、相手の物そのもののフック)は、試験のファイルの説明に理由つきで書いた

## 外部の道具を入れたときの §4 の検査の結果

入れていない(外部の道具は導入も実行もしていない。ネットワークも使っていない)。

## リードに聞くこと

- §8.6 の 31「外の class の属性(__module__・__name__ を含む)を読まない」の読み方を確かめたい。この周の作りでは、断りの文と result().models の型の名前を、__qualname__ は type の C の欄から、__module__ は class の辞書を反復して取る。どちらも検索も普通の読みもせず、外のコードは走らない(格子 1 の dict とメタクラスの置き場所で確かめた)。文字どおり「読まない」にすると、型の名前を文に書けなくなる。その場合、契約 type_decisions の『naming the real type in full』と、第 11 周の格子 1 の神託『文に実際の型の名前がある』を変える必要がある。この読みでよいか、決めてほしい
- §8.6 の 31 の「落とした事実の array は戦略に buffer を出さない = memoryview を作れない型か、写しを渡す」について。この周は第 3 の形を取った。核は戦略に渡した配列を二度と変えず、落とすたびに新しい小さな配列を戦略の側の list に足すだけにした。まとめる操作は戦略の読み出しの中で行い、まとめる先が固定されていれば新しい配列を作る。採らなかった理由は 2 つ。int の list は 88.2 バイト/件(実測、<W>/item0_r12_worker_fact_bytes.out)で、契約の 16 バイトの 5 倍を超える。呼び出しごとの写しは件数に比例して遅くなる(§7.4 の 19)。この形でよいか、決めてほしい
- 振る舞いの変化が 3 つある。(a) 差し込み口の数の答えのうち、Python で書いた数の class(数の塔に登録や派生したもの)を入口の誤りで断る(numpy の数は受ける)。(b) 約定模型と口座の Sequence の答えを list か tuple に限る(生成器などは断る)。(c) 出口の箱の値で numpy の数を受ける。3 つとも契約 core-14 に書いた。別に周知する必要があるか
- shown の列(台帳へまだ反映していない見え方)は、戦略が口を呼ぶまで伸びる。上限は注文の変化の数で決まる。契約 ownership に書いた。上限を付けるかは、項目 12・13 の要件を固定するときに決めてよいか
- (独立の項目)起動文 (3) の候補 35 の権限の分類器の拒否は、場面係と監査役あての項目なので、作業者は扱っていない
- i0-r11-02(場面集の covers)の批評家の試験 13 件は、この周の終わりの作業木でも落ちたままである。場面係が同時に直している最中と読み、作業者は変えていない

## この周で変えた構造

(1) 外の者(戦略・差し込み口・入力の流れ)の呼び出しの外では、核が外の物について行う判断を、同一性(is)と静的な C の型だけで決まる操作に限った。外の class をハッシュしない、== で比べない、検索しない、普通の読み方で属性を読まない(IdTable・is_one_of・derives、class_parts は辞書を反復して読む)。答えは settle / take_int / take_float / take_items で取り、真偽・長さ・反復・変換を答えの物には聞かない。運び手は欄を settle してから作り直す。(2) 核が戦略の側へ書くのは、自分が作った list への list.append だけにした。台帳の dict と落とした事実の配列は、戦略自身の呼び出しの中で、その list をもとに更新する(api._bring_up、history.read_dropped)。
