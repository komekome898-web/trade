# 作業者の報告(作る:0#13、agent a7d45996bbf7943de。Workflow の記録の返り値から逐語で書き出し)

## 変えたファイル

- src/bot/bt/core/contract.py(visibility.history_limit の文だけ。LEAD_DESIGN §9.3 の 38 の 88.2 バイト/件と 16.9 バイト/件の実測を足した。同じ文にあった第 12 周の誤り「an array of about 64 bytes」を実測の値に直した(sys.getsizeof で 80 バイト + 1 件 16 バイト、pending の list の欄 8 バイト、1 回に落とすのは history_limit + 1 件)。実装のコードは変えていない)
- tests/bt/item_0/test_bt0_r13_dropped_fact_storage.py(新規、25 件。契約の文の数を実装に縛る試験)
- docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/round_13/ROOTCAUSE.md(新規。i0-r11-01・i0-r11-03 の根本原因と変えた構造(第 12 周)、この周の初めの確かめ、§9.3 の 37〜41 への対応、厳しい批評家が止めそうな点)

## 足した試験の数

25

## 試験のコマンド

PYTHONPATH=src python -m pytest tests/bt/item_0 tests/bt/critic/item_0 -p no:cacheprovider(ほかに、作業の最後に場面集を 1 回: PYTHONPATH=src python -m pytest tests/bt/battery/item_0 -p no:cacheprovider。全試験は setsid nohup で切り離して 1 回: PYTHONPATH=src python -m pytest -p no:cacheprovider。ログは /tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/r13_worker/pytest_item0_r13_worker_{mid,battery,full}.log)

## 試験の末尾の行

項目 0・核・批評家の試験: 「13 failed, 1817 passed, 2 skipped in 345.21s (0:05:45)」。落ちる 13 件はすべて tests/bt/critic/item_0/test_i0r11_covers_within_scene_input.py(i0-r11-02。相手は場面集で、場面係が直している最中)。場面集(最後に 1 回): 「78 passed in 35.37s」。全試験: 「14 failed, 4791 passed, 6 skipped, 1 warning in 837.89s (0:13:57)」。14 件のうち 13 件は上と同じ covers_within。残りの 1 件 tests/bt/battery/item_0/test_battery_def_grids.py::test_the_machine_agrees_with_the_definition_on_every_cell_run[D] は、全試験が走っている間に場面係が書きかけていた場面集の語の判断(line_judgments.tsv・term_judgments.tsv の変更と、追跡されていない ROOTCAUSE_r13-1.md)を読んだときの落ち。作業者は場面集に触れていない。その後、作業木の今の版で term_marks.problems を回すと 0 件、場面集を回し直すと 78 passed(同じ試験を含む)。実装の側で落ちる試験は 0 件(`grep -E '^(FAILED|ERROR)' … | grep -v covers_within` → 上の [D] の 1 行だけ)。

## 要件の各行を満たした根拠(ファイル:行)

- 時刻は UTC の int64 ナノ秒: src/bot/bt/core/time.py:55(TIME_CONTRACT)・75(validate_nanos)。この周の変更なし
- 事象の型(約定・板の写真・板の差分・足・資金調達・清算・時計・注文の受付/拒否/約定の通知): src/bot/bt/core/events.py:52(EventType)。この周の変更なし
- 戦略は「受け取れた時刻 ≤ 今」の事象しか見られない(構造で): src/bot/bt/core/api.py:717(visible_events)・921(_time_arg)、src/bot/bt/core/window.py:61(POSITION_RULE)。落とした事実の読み出しは history.py:158(read_dropped)。この周に足した試験 tests/bt/item_0/test_bt0_r13_dropped_fact_storage.py で、落とした事実が入力だけから出した神託と一致することを確かめた(25 passed)
- 決定的な事象の順序(同時刻の並びの規則を明記): src/bot/bt/core/ordering.py:161(ORDERING_RULE)。この周の変更なし
- 戦略の API(事象ごとの呼び出し・発注・取消): src/bot/bt/core/api.py:949(STRATEGY_API)・892(place_order)・898(cancel_order)・509(_bring_up)、src/bot/bt/core/engine.py:1117(on_event の呼び出し)・1122(_show)。外の者の呼び出しの外で、その者のコードを走らせないこと: tests/bt/item_0/test_bt0_r12_party_hooks.py:824(格子 1)・932(格子 2)。この周の全試験で通った
- 他項目が差し込む口(約定模型・遅延模型・費用・口座): src/bot/bt/core/interfaces.py:153(FillModel)・173(LatencyModel)・193(CostModel)・200(Account)・226(SOCKETS)。答えの取り方は src/bot/bt/core/values.py:395(settle)・481(take_int)・490(take_float)・503(take_items)。この周の変更なし
- 契約: src/bot/bt/core/contract.py:15(CORE_VERSION core-14)・81(history_limit。この周に 88.2 / 16.9 バイト/件の実測と塊の大きさの実測値を足した)・102(scope)・166(ownership)・217(plug_in_answers)・229(type_decisions)

## 満たせなかった行とその理由

- 満たせなかった要件の行: 無し。以下は委任文 §3「提出前の吟味」の記録。<S> = /tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt、<W> = <S>/r13_worker。
- (1) i0-r11-01 の直り(第 12 周の直し)をこの周の初めに確かめた: `PYTHONPATH=src python -m pytest tests/bt/critic/item_0/test_i0r11_class_dict_key_runs_foreign_code.py tests/bt/critic/item_0/test_i0r11_pinned_dropped_facts_fail_the_core_step.py tests/bt/critic/item_0/test_i0r11_history_limit_exact_refusal.py -p no:cacheprovider` → 「23 passed in 0.75s」。批評家の試しを回し直した結果(<W>/item0_r13_worker_recheck_r11_critic_probes.out)は次のとおり。module_key_nometa → 'step/run/result -> EngineFailedError | is EngineFailedError: True'・'Key.__eq__ ran in: []'。outbox_key → 'Msg -> run raised OrderApiError | OrderApiError: True'・'[]'。registry_key → 'raise: True -> run ok [('mine-1', 'FILLED')]'・'strategy code outside on_event: 0 []'。outbox_metahash → 'run raised OrderApiError | OrderApiError: True'・'[]'。直した構造は values.py:219 IdTable、values.py:252 class_parts、engine.py:1122 _show(list.append)、api.py:509 _bring_up、api.py:216 fresh_request。
- (1) i0-r11-03 の直り: 上の 23 passed に test_i0r11_pinned_dropped_facts_fail_the_core_step.py が入っている。批評家の試し array_export → 'hold views: True -> run ok, events 12 digest 06cfb720ce34'(持たないときの 'hold views: False -> run ok, events 12 digest 06cfb720ce34' と同じ)。直した構造は history.py:134 DroppedFacts・history.py:158 read_dropped。この周に足した試験の read_each_pinned の列(history_limit 1〜6 × 配達数 0〜6·limit+3)でも、view を持ったまま読みが全部返ることを確かめた。
- (1) §9.3 の 38(88.2 バイト/件を契約に残す): contract.py:81 の history_limit の文。測り直した: `python3 <W>/item0_r13_worker_fact_bytes.py` → 'array('q') x2: 16.9 bytes/fact | list of int x2: 88.2 bytes/fact'(Python 3.11.15)。37・39・40・41 は答えのとおり変えていない。
- (2) 同じ根の箇所: 88.2 を足した同じ文に、第 12 周の誤り「an array of about 64 bytes plus the facts」があった。`python3 <W>/item0_r13_worker_chunk_bytes.py` → 'sys.getsizeof(array('q')) = 80 | sys.getsizeof(chunk) = 96 | tracemalloc per chunk incl. the list slot: 104.1 bytes'。1 回に落とすのは history_limit + 1 件である(history.py:276-277 `if … len(facts) >= 2 * limit: cut = len(facts) - (limit - 1)`)。この 2 点に合わせて文を直し、試験で縛った。
- (3) 批評家の試験は全部回した。落ちるのは test_i0r11_covers_within_scene_input.py の 13 件だけで、相手は場面集(i0-r11-02。場面係の持ち物)。試験自身の誤りで落ちる批評家の試験(規則 8)は無い。場面集の試験は最後に 1 回回して 78 passed。
- (4) 厳しい批評家が [止める] にしそうな点(ROOTCAUSE §E): (a) 「前の周から変わった構造が無い周」。この周はリードの §9.3 の 41 と起動文が実装を変えずに待つよう指示した周で、変えたのは契約の文と試験だけ。周に数えるかは台本とリードが決める。(b) 数の ABC の穴。契約 scope の「対象外」に書かれた物を実測した: `PYTHONPATH=src python3 <W>/item0_r13_worker_probe_numbers_abc.py` → 'run -> LatencyModelError order_delay_ns must return an int of ns: order_delay_ns must be an int, got numpy.float32' / "party __subclasscheck__ calls: [('outside', 'float32')]"。戦略が on_event の中で numbers.Integral の子をメタクラスつきで作ると、核の values._settle(values.py:471 `issubclass(t, abc)`)が ABC の仕組みを通して、そのフックを戦略の呼び出しの外で走らせる。断りの型は入口の誤りのままで、黙って誤った値は無い。実装を変えない指示の外なので直していない。リードに聞く。(c) 契約の文の数が実測と違っていた点は (2) で直した。
- (5) 場当たりの直しはしていない: 試験だけの特別扱い・閾値や既定値のずらし・文言合わせ・機能を外すことはしていない。足した試験の神託は入力だけから出し(2 × limit 件を持つときに古い limit + 1 件を落とす)、実装の場合分けから作っていない。契約の文に語があるかを見る 1 件は、試験の残りの 24 件が数を実装で確かめたうえで、文が数を載せていることを縛るためのもの。
- (6) この周に直した規則は無い(実装を変えていない)。契約の文の数に対して、入力の空間を全格子で列べる試験を先に書いてから通した: history_limit 1〜6 × 1 つの型の配達数 0〜(6·limit+3) × 読み方 3 通り(最後にだけ読む / 毎回読む / 毎回読んで memoryview を持つ)。列に入れなかった物(sys.getsizeof の絶対値、複数の型を同時に落とすこと、tracemalloc の数そのもの)は、理由と一緒に試験のファイルの説明に書いた。

## 外部の道具を入れたときの §4 の検査の結果

入れていない(外部の道具は導入も実行もしていない。ネットワークも使っていない)。

## リードに聞くこと

- 契約 scope の対象外「numbers の ABC に派生・登録した、__subclasshook__ かメタクラスのフックを持つ class(class を定義することはプログラムを変えること)」について。戦略が on_event の中で普通に書く class の定義(numbers.Integral の子で、メタクラスが __subclasscheck__ を持つ)で、そのフックが戦略の呼び出しの外で走ることを実測した(<W>/item0_r13_worker_probe_numbers_abc.py → "party __subclasscheck__ calls: [('outside', 'float32')]"、断りは LatencyModelError のまま、<W> = /tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/r13_worker)。族は i0-r9-02(外の物のコードが核の手順の中で走る)で、第 12 周に対象外として書いたもの。この周は実装を変えない指示なので直していない。これを「プログラムを変えること」として対象外のまま残すか、次の周で直すかを決めてほしい。直す場合の候補は、静的な型の数かどうかを ABC に聞かずに決める形(静的な型の MRO の中の型を、数の ABC に登録された型と同一性で比べる)である。numpy の型の扱いが今と同じになるかは測っていない(未確認)。
- 契約 history_limit の文にあった第 12 周の誤り(塊を「about 64 bytes」)を、§9.3 の 38 で指示された同じ文の中で、実測の値(sys.getsizeof で 80 バイト + 1 件 16 バイト、pending の list の欄 8 バイト、1 回に落とすのは history_limit + 1 件)に直した。指示は 88.2 の実測を残すことだけだったので、この直しが指示の範囲の中かを確かめたい。範囲の外なら戻す。

## この周で変えた構造

この周は実装の構造を変えていない(LEAD_DESIGN §9.3 の 41 と起動文の「実装を変えずに待つ」のとおり)。変えたのは次の 2 つ。(1) 契約 visibility.history_limit の文に、落とした事実の持ち方とその理由の実測(array('q') 16.9 バイト/件、int の list 88.2 バイト/件)を足した。同じ文の塊の大きさの誤り(約 64 バイト)を実測の値に直した。(2) その文の数(1 件 16 バイト、1 回に落とすのは history_limit + 1 件、落とすたびに塊が 1 つ、読むと塊がまとまる、view を持っていても読みは全部)を実装に縛る試験を足した。
