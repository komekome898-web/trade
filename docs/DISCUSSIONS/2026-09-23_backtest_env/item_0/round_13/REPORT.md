# 作業者の報告(作る:0#13、agent a50adb32e31f917d4。Workflow の記録の返り値から逐語で書き出し)

## 変えたファイル

- docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/round_13/ROOTCAUSE.md(節 G を追記: 11 回目の起動(委任文 cdf623e4fb24)での走り直しで、作業木の今の版に対して確かめ直したこと。A〜F は前の版のまま)
- (実装・契約・試験はこの走り直しでは変えていない。第 13 周の契約の文 src/bot/bt/core/contract.py:81-93 と試験 tests/bt/item_0/test_bt0_r13_dropped_fact_storage.py(25 件)は最初の版の成果で、コミット 115112d・dc9e04a に入っている。`git status --short src/bot/bt tests/bt/item_0 tests/bt/critic` → 出力なし)

## 足した試験の数

0

## 試験のコマンド

PYTHONPATH=src python -m pytest tests/bt/item_0 tests/bt/critic/item_0 -p no:cacheprovider(ほかに: 全試験を setsid nohup で切り離して 1 回 = PYTHONPATH=src python -m pytest -p no:cacheprovider / 作業の最後に場面集を 1 回 = PYTHONPATH=src python -m pytest tests/bt/battery/item_0 -p no:cacheprovider。ログは /tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/r13_worker_run11/pytest_item0_r13_worker_run11_{mid,full,battery}.log)

## 試験の末尾の行

項目 0・核・批評家の試験: 「1830 passed, 2 skipped in 342.18s (0:05:42)」(飛ばした 2 件は前からあるもの: tests/bt/item_0/test_bt0_carriers.py:144「bool cannot be subclassed」、tests/bt/critic/item_0/test_i0r5_battery_opponent_grading.py:130 は調査の venv が無いときに飛ばす)。i0-r11 の批評家の試験 4 本とこの周の 25 件: 「80 passed in 0.84s」。全試験: 「4 failed, 4874 passed, 6 skipped, 1 warning in 845.70s (0:14:05)」。落ちた 4 件はすべて tests/bt/battery/item_0/(test_battery_def_grids.py の 2 件と test_battery_item0.py の 2 件)。場面集(最後に 1 回): 「7 failed, 162 passed in 57.83s」。落ちた 7 件は上の 4 件、test_battery_item0.py::test_definitions_in_sync_with_scenes、test_battery_r13_claims.py の 2 件。どれも、同じ時間に場面係が直している場面集の途中の物である(§9.2 の 34 で正の定義 C の文を置き換えている途中の語の判断。例: ('segment text differs', 62, '`covers` は', '`covers` は場面の宣言で')。§9.2 の 33 の types_in・requests の試験)。作業木で変わっていたのは tests/bt/battery/item_0/ の 30 本と、追跡されていない test_battery_r13_claim_mutants.py だけだった。実装の側で落ちた試験は 0 件。場面集を回したあとに批評家の i0-r11 の 3 本(covers_within を含む)を回し直した結果は「45 passed in 0.09s」。

## 要件の各行を満たした根拠(ファイル:行)

- 時刻は UTC の int64 ナノ秒: src/bot/bt/core/time.py:55(TIME_CONTRACT)・75(validate_nanos)。この周の変更なし
- 事象の型(約定・板の写真・板の差分・足・資金調達・清算・時計・注文の受付/拒否/約定の通知): src/bot/bt/core/events.py:52(EventType)。この周の変更なし
- 戦略は「受け取れた時刻 ≤ 今」の事象しか見られない(構造で): src/bot/bt/core/api.py:717(visible_events)・921(_time_arg)、src/bot/bt/core/window.py:61(POSITION_RULE)、落とした事実の読み出しは src/bot/bt/core/history.py:158(read_dropped)。tests/bt/item_0/test_bt0_r13_dropped_fact_storage.py(25 件、入力だけから出した神託)がこの走り直しでも通った
- 決定的な事象の順序(同時刻の並びの規則を明記): src/bot/bt/core/ordering.py:161(ORDERING_RULE)。この周の変更なし
- 戦略の API(事象ごとの呼び出し・発注・取消): src/bot/bt/core/api.py:949(STRATEGY_API)・892(place_order)・898(cancel_order)・509(_bring_up)、src/bot/bt/core/engine.py:1117(on_event の呼び出し)・1122(_show)。外の者の呼び出しの外で、その者のコードを走らせないこと: tests/bt/item_0/test_bt0_r12_party_hooks.py:824(格子 1)・932(格子 2)。この走り直しの全試験で通った
- 他項目が差し込む口(約定模型・遅延模型・費用・口座): src/bot/bt/core/interfaces.py:153(FillModel)・173(LatencyModel)・193(CostModel)・200(Account)・226(SOCKETS)。答えの取り方は src/bot/bt/core/values.py:395(settle)・481(take_int)・490(take_float)・503(take_items)。この周の変更なし
- 契約: src/bot/bt/core/contract.py:15(CORE_VERSION core-14)・81-93(history_limit。88.2 / 16.9 バイト/件と、塊の大きさの実測値。この走り直しで測り直した値と同じ)・102(scope)・166(ownership)・217(plug_in_answers)・229(type_decisions)

## 満たせなかった行とその理由

- 満たせなかった要件の行: 無し。以下は委任文 §3「提出前の吟味」の記録。<S> = /tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt、<N> = <S>/r13_worker_run11。
- (1) i0-r11-01 の直り(第 12 周の直し)を作業木の今の版で確かめた: `PYTHONPATH=src python -m pytest tests/bt/critic/item_0/test_i0r11_class_dict_key_runs_foreign_code.py tests/bt/critic/item_0/test_i0r11_pinned_dropped_facts_fail_the_core_step.py tests/bt/critic/item_0/test_i0r11_history_limit_exact_refusal.py tests/bt/critic/item_0/test_i0r11_covers_within_scene_input.py tests/bt/item_0/test_bt0_r13_dropped_fact_storage.py -p no:cacheprovider -rs` → 「80 passed in 0.84s」。批評家の試しを回し直した結果(<N>/item0_r13_worker_run11_recheck_r11_critic_probes.out)。module_key_nometa → 'step/run/result -> EngineFailedError | is EngineFailedError: True' と "Key.__eq__ ran in: []"。module_key → 'strategy code run outside on_event: []'。outbox_key → 'Msg -> run raised OrderApiError | OrderApiError: True' と '[]'。outbox_metahash → 'run raised OrderApiError | OrderApiError: True' と '[]'。registry_key → "raise: True -> run ok [('mine-1', 'FILLED')]" と 'strategy code outside on_event: 0 []'。reach_swap → 'uses of those classes OUTSIDE on_event: [] count 0'。直した構造: values.py:219 IdTable、values.py:252 class_parts、engine.py:1122 _show、api.py:509 _bring_up。
- (1) i0-r11-03 の直り: 上の 80 passed に test_i0r11_pinned_dropped_facts_fail_the_core_step.py が入っている。批評家の試し array_export → 'hold views: True -> run ok, events 12 digest 06cfb720ce34'(view を持たないときの 'hold views: False -> run ok, events 12 digest 06cfb720ce34' と同じ)。直した構造: history.py:134 DroppedFacts、history.py:158 read_dropped。
- (1) §9.3 の 38(88.2 バイト/件を契約に残す): contract.py:81-93。測り直した: `python3 <N>/item0_r13_worker_run11_fact_bytes.py` → "array('q') x2: 16.9 bytes/fact | list of int x2: 88.2 bytes/fact"、`PYTHONPATH=src python3 <N>/item0_r13_worker_run11_chunk_bytes.py` → "sys.getsizeof(array('q')) = 80 | sys.getsizeof(chunk) = 96 | tracemalloc per chunk incl. the list slot: 104.1 bytes"(Python 3.11.15)。契約の文と同じ値である。37・39・40・41 は答えのとおり変えていない。
- (2) 同じ根の箇所(数の ABC に聞く所)を全部列べた。コマンドは `grep -n "numbers\.\|issubclass(" src/bot/bt/core/*.py`。values.py:381-385(_settle。コメントでは送り手の呼び出しの中で聞く)と values.py:470-471(settle の静的な型の分岐。持ち主の呼び出しの外で聞く)の 2 か所があり、外で走ったのは後者である。ABC の Mapping に聞く所(engine.py:763、ordering.py:189)は、実行を作る呼び手の呼び出しの中にある。window.py:298-300 は list と tuple で、ABC ではない。
- (3) 批評家の試験は全部回した(tests/bt/critic/item_0 を含めて 1830 passed, 2 skipped)。試験自身の誤りで落ちる批評家の試験(規則 8)は無い。場面集の試験は最後に 1 回回し、7 failed / 162 passed だった。7 件は全部、場面係が同じ時間に直している場面集の途中の物で、作業者は場面集に触れていない。全試験では、実装の側で落ちた試験は 0 件。
- (4) 厳しい批評家が [止める] にしそうな点(ROOTCAUSE §E・§G)は 2 つある。(a)「前の周から変わった構造が無い周」: この周は、リードの §9.3 の 41 と起動文が実装を変えずに待つよう指示した周である。周に数えるかは台本とリードが決める。(b) 数の ABC の穴(契約 scope の対象外、contract.py:137-138): 3 回目の実測でも "party __subclasscheck__ calls: [('outside', 'float32')]"(<N>/item0_r13_worker_run11_probe_numbers_abc.out)。断りの型は LatencyModelError のままで、黙って誤った値は無い。リードの答えがまだ無い(`grep -n 'ABC\|subclasscheck\|about 64' round_7/LEAD_DESIGN.md` → 該当なし)。実装を変えない指示の外なので直していない。「リードに聞くこと」に書いた。
- (5) 場当たりの直しはしていない。この走り直しでは実装・契約・試験を 1 行も変えていない。
- (6) この周に直した規則は無い。契約の文の数に対する全格子の試験は最初の版で先に書いた。格子は history_limit 1〜6 × 配達数 0〜(6·limit+3) × 読み方 3 通りで、列に入れなかった物は試験のファイルの説明(tests/bt/item_0/test_bt0_r13_dropped_fact_storage.py:18-24)に書いてある。

## 外部の道具を入れたときの §4 の検査の結果

入れていない。外部の道具は導入も実行もしておらず、ネットワークも使っていない。

## リードに聞くこと

- (前の 2 回の版からの繰り返し。LEAD_DESIGN にまだ答えが無い)契約 scope の対象外「numbers の ABC に派生・登録した、__subclasshook__ かメタクラスのフックを持つ class(class を定義することはプログラムを変えること)」(contract.py:137-138)について聞く。戦略は on_event の中で普通に class を書ける(numbers.Integral の子で、メタクラスが __subclasscheck__ を持つもの)。その class があると、核の values.settle(values.py:470-471 `issubclass(t, abc)`)が ABC の仕組みを通して、そのフックを戦略の呼び出しの外で走らせる。3 回目の実測: `PYTHONPATH=src python3 /tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/r13_worker_run11/item0_r13_worker_run11_probe_numbers_abc.py` → "party __subclasscheck__ calls: [('outside', 'float32')]"。断りは LatencyModelError のままである。族は i0-r9-02(外の物のコードが核の手順の中で走る)。これを「プログラムを変えること」として対象外のまま残すか、次の周で直すかを決めてほしい。直す場合の候補: 静的な型が数かどうかを ABC に聞かずに決める(静的な型の MRO の中の型を、数の ABC に登録された型と同一性で比べる)。numpy の型の扱いが今と同じになるかは測っていない(未確認)。
- (前の 2 回の版からの繰り返し)契約 history_limit の文にあった第 12 周の誤り(塊を「about 64 bytes」と書いていた)を、§9.3 の 38 で指示された同じ文の中で実測の値に直した。実測の値は、sys.getsizeof で 80 バイト + 1 件 16 バイト、pending の list の欄 8 バイト、1 回に落とすのは history_limit + 1 件である。指示は 88.2 の実測を残すことだけだったので、この直しが指示の範囲に入るかを確かめたい。範囲の外なら戻す。

## この周で変えた構造

この周は実装の構造を変えていない(LEAD_DESIGN §9.3 の 41 と起動文の「実装を変えずに待つ」のとおり)。第 13 周で変えたのは最初の版の 2 点だけである。(1) 契約 visibility.history_limit の文に 88.2 / 16.9 バイト/件の実測を残し、同じ文にあった塊の大きさの誤りを実測の値に直した。(2) その文の数を実装に縛る試験を足した。この走り直しでは何も変えず、確かめ直しだけをした。
