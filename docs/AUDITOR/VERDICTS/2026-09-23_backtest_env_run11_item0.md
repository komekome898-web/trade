# バックテスト環境 11 回目(run `wf_bdb3a806-5e1`、委任文 cdf623e4fb24、枠組みの指紋 2ccfc354e4e7)項目 0 の記録

起動 2026-09-25 02:27 UTC(新しい run、第 13 周から、L-443 の体制)。段の時刻は agent の記録の最初の時刻 → 最終書き込み時刻(リードの実測、04:33 UTC の見回り)。

## 第 13 周

| 段 | 開始 | 終了 |
|---|---|---|
| 作る:0#13 | 02:29:00 | 02:51:56 |
| 場面の直し:0#r13-1 | 02:29:00 | 03:41:33 |
| 監査役(場面):0#r13-1 | 03:41:34 | 03:50:13 |
| 表:0#13 | 03:50:14 | 04:16:19 |
| 批評:0#13 | 04:16:20 | 04:25:29 |
| 作る:0#14 | 04:25:30 | (進行中) |

審査員は起きていない(L-443 (3): 実装の側の [止める] があり、構造の変化なし(`structural_change_since_prev: false`)、最初の周でもない → 第 11 周の判定を持ち越し)。

### 場面係 r13-1 の返り値 `lead_answer_changes`(逐語)

- 升目の数え方を、F の「s が (v, x) を宣言し、かつ型 e が s の入力から機械で出る」(型と見る道を別々に取った積)から、「s が升目 (e, v, x) を宣言し、かつ型 e が s の入力から機械で出る」(宣言と入力の両方が要る)に変えた。理由: 升目は型と見る道と追加の軸の 3 つ組で、どの型をどの見る道で見るかの組は入力にも (v, x) の宣言にも無い。F を字のまま積で数えると、今の場面集では 17 升目が広がる(例: p3-notice-accepted の入力の約定から (約定, 発注の呼び出しがその場で返す物) が数えられる。`<S>item0_r13-1_scenekeeper_fix_product.txt`)。向きは i0-r11-02 と同じ(測っていない範囲を狭く見せる)。批評家の神託は型が入力にあるかだけを見るので積の広がりを捕まえない。変えた形の升目は F の升目の部分集合で、F が数えない升目を足さない(同じ出力の最後の項)。これに伴い、F の「手書きの宣言…は使わない」は「手書きの宣言は升目の上限としてだけ使い、宣言だけでは数えない。宣言の型が入力から出なければ試験が落ちる」に、§9.2 の 34 の「`COVERS` の事象の手書きの一覧を消し、(v, x) の宣言だけを残し」は「`COVERS` を升目 (e, v, x) の宣言として残し、入力から出ない型の宣言を消し、`covers_of(s)` を宣言と入力の両方から計算する」に替わる。注文の受付・拒否・約定の 3 つの通知の升目では、機械が決めるのは発注の頼みの有無までで、3 つのどれを数えるかは宣言が決め、批評家が読む(F の積の形では 3 つとも数える)。
- 戦略の頼みの読み方を、F の「s の入力の戦略の頼み」から「s の入力が欄 `requests` として持つ戦略の頼み(入力の文を読んで頼みを決めない)」に変えた。理由: F は判断を機械で 2 値とするが、頼みを入力のどの欄から読むかを決めていない。頼みは `strategy` の文にしか無く、文を語で探す読み方は言い換えで黙って外れる。欄の値は、新実装の adapter の戦略が実際に出した頼みと等しいことを試験で照らす(`test_battery_r13_claims.py:test_the_requests_field_is_what_the_reference_strategy_asks`)。
- §9.2 の 33 の試験「全記録の `types_in` ⊆ F で出した型」を、「全記録の `types_in` ⊆ runner がその設定つき対象に渡した入力の型」に変えた。理由: `type_plan` の 4 場面では、F で出す型は 6 型を全部持つ対象のために作る入力の型だが、runner が設定つき対象に渡す入力は設定つき対象の持つ型から作る(L-438 (2))。6 型を全部は持たない設定つき対象では、渡した型が F の型の外になりうるので、字のままの試験は adapter が型を足していなくても落ちる。`type_plan` の無い場面では 2 つは同じ物である。

`questions_for_lead`: None。検査器の出力: `OK 誤り 0 件`。走らせなかった対象(逐語): ["8 OpenTrader: 危険(§6-1)", "11 OctoBot: 動かなかった", "13 DeviaVir/zenbot: 危険(§6-1)", "15 Mendl-Labs/BacktestingCore: 鍵・登録", "38 microsoft/MarS: 一括の取得(数百 MB 以上)", "40 OpenMarket: 外部の場", "41 prediction-market-backtesting: 危険(台帳 §3 の 11 件)", "44 lo2cin4: 危険(台帳 §3 の 11 件)", "49 GFT Backtest Software: 鍵・登録", "52 QuantConnect: 一括の取得(数百 MB 以上)。再現 repro_lean52 を走らせた", "57 WonderTrader: 導入前の検査を通せない・依存が repository の外", "58 nautilus_trader: 危険(台帳 §3 の 11 件)", "63 trade-frame: 動かなかった", "120 wbt: 危険(台帳 §3 の 11 件)", "123 carlos8f/zenbot: 危険(§6-1)"]

### 監査役(場面) r13-1 の出力(逐語)

- **br13-1-1** [聞く](repeat_of: i0-r11-02)
  ROOTCAUSE_r13-1.md §4 の主張の族 3(注文の受付・拒否・約定の3つのうち場面がどれを測るか)は (c)(d) の試験が『無い』と明記され、宣言(手書き)が永続的に機械の外に残る設計(§8.2 の 4 でリードに保留のまま提出)。この族は i0-r11-02 が指摘した『covers の手書きの宣言が測る物と食い違いうる』のと同じ根(根9で見つかった p6-place-then-cancel の食い違いと同型)であり、機械で閉じない限り同種の食い違いが将来の場面追加で再発しうる。批評家が毎周読むことが唯一の歯止めで、この設計のまま『通過』を出してよいかは、族1〜2・4・5〜7が機械化された今、リードが明示的に良しとするかを確認したいところ。
- **br13-1-2** [聞く](repeat_of: i0-r11-02)
  ROOTCAUSE_r13-1.md §8.2 の 5 のとおり、requests の記録は new_impl・当方の現状・試金石の adapter にしか無く、相手(調査結果の側)37 adapter・41 設定つき対象では null のまま(注記は『記録なし』で『入った』と数えない扱い)。これは i0-r11-02 が指摘した『測っていない範囲を狭く見せる向き』の閉じ残りが、比較対象の大多数(相手側)にはまだ及んでいないことを意味する。今回の直しで『場面にした』の総数が 50→27 に縮んだことが、相手側についても同じ厳密さで確認された結果なのか、それとも相手側は『記録なし』のまま外から見えない領域が残っているのかを、次にこの升目の表を通過判定や報告に使う際、区別して書く必要があるか確認したい。
- **br13-1-3** [聞く](repeat_of: None)
  tests/bt/battery/item_0/opponents/gobacktest_adapter.py 107行は約定を common.substitute を通さず `{"kind": "tick", ...}` の辞書に直接作り替えており、ROOTCAUSE_r13-1.md §6.3 は『対象自身の形 "tick" に作るので替えていない』とだけ理由を書いている。test_battery_r13_claims.py:test_the_substitution_finder_sees_every_form はこの形(kind="tick")を意図的に検出対象外(not_found)にしており、機構としては一貫しているが、この特定の対象(gobacktest)について、types_in がこの trade→tick の作り替えを『代えた型』として正しく除外している(過大に数えていない)ことを示す個別の実測・試験参照が ROOTCAUSE 本文に無い。family 5 の格子試験がこの具体的な経路(kind の無い自前形式への変換)を代表的な1ケースとして含んでいるかを確認したい。

### 批評家 0#13 の出力(逐語)

- **i0-r13-01** [止める](target: 実装, repeat_of: i0-r11-01, fix_files: ['src/bot/bt/core/values.py', 'src/bot/bt/core/contract.py'])
  核は「静的な(C の)数の class が何の数か」を、プロセス全体で共有された numbers の ABC に聞いて決める(values.py 470-476 行 _settle、381-386 行 _plain_scalar)。その ABC の登録は、戦略が自分の呼び出しの中で公開の API(numbers.Integral.register)で変えられる状態である。(a) 黙って誤った値: 戦略が on_event で numbers.Integral.register(numpy.float32) を呼ぶ(フックも class の定義も無い、ただの登録)。すると、費用の模型の手数料 numpy.float32(0.75) は口座に 0.0 で渡り、約定の模型が自分の呼び出しの中で作った報告の価格 numpy.float32(100.5) は戦略に 100.0 で届く。どちらも断りは出ない。遅延の模型の numpy.float32(1.5) は、登録の前は LatencyModelError で断られ、登録の後は 1 ns として黙って受け取られる。(b) 再現性: 同じプロセスで同じ入力を走らせても、間に別の実行の戦略が登録すると結果が変わる(手数料 0.75 → 0.0)。ABC は正の答えを覚えておくので、元には戻らない。P0-5 の「同じ入力を 2 回実行して同じ結果」と、契約 scope の「the strategy changing ANY state object it can reach ... reaches only what the strategy itself reads」に反する。(c) i0-r11-01 と同じ機構: numbers.Integral の子で、メタクラスの __subclasscheck__ を持つ class を戦略が作る。すると、戦略の呼び出しの外で核が費用の答えを取るときに、そのフックが走って答えを決める。どの ABC でも 1 回の登録(ふつうの collections.abc.Sized.register でも)があれば否定の覚えが消えるので、先の実行で否定が覚えられていても、フックはまた聞かれる。(d) 同じ根の 2 つ目の形: values.py 322-325 行 _numpy_bool は、settle のたびに sys.modules['numpy'].bool_ を読む。戦略がこの属性を自分の class にすると、出口の箱の値を取るときに、その class の __bool__ が on_event の外で走る。断りの型も OrderApiError から TimestampUnitError に変わる。契約の対象外の文「classes derived from or registered with the numbers ABCs that carry a __subclasshook__ or a metaclass hook ... (defining classes changes the program)」は、フックの無い登録を覆っていない。その理由の文も、第 11 周・第 12 周に戦略が定義した class を範囲に入れて直した格子と合わない。ABC の登録は核のコードではなく、実行中に変わる状態である。黙って誤った値と再現性の崩れにあたるので [止める]。対象外の文で閉じるのは要件から逃げる直しになる。直すときは、数の種類を ABC の登録に聞かずに決めること(静的な型の MRO を核が持つ型の表と同一性で比べる)と、sys.modules をたどらないことの両方が要る。第 13 周の作業者は (c) を自分で見つけてリードに聞いている(round_13/REPORT.md「リードに聞くこと」)。
  証拠: PYTHONPATH=src python3 <S>/r13_critic/item0_r13_critic_probe_numbers_registry.py {none,register,hook}(1 つずつ新しいプロセスで)→ 'none -> run ok | fee seen by the account: [0.75] | hook calls: 0' / 'register -> run ok | fee seen by the account: [0.0] | hook calls: 0' / 'hook -> run ok | fee seen by the account: [0.0] | hook calls: 1'。<S>/r13_critic/item0_r13_critic_probe_numbers_rerun.py → 'run A (clean strategy), fresh process : ('ok', [0.75], [0])' / 'delay 1.5 as float32, fresh : ('raised LatencyModelError', ...)' / 'run B (its strategy registers np.float32) : ('ok', [0.0], [0])' / 'run A again, same input, same process : ('ok', [0.0], [0])' / 'delay 1.5 as float32, after the registration : ('ok', [0.0], [1])'。<S>/r13_critic/item0_r13_critic_probe_numbers_fill_price.py {none,register} → 'none -> fill price the strategy received: [100.5]' / 'register -> fill price the strategy received: [100.0]'。<S>/r13_critic/item0_r13_critic_probe_numpy_bool_attr.py → 'patch False -> run raised OrderApiError ...' / "patch True -> run raised TimestampUnitError timestamp must be an int of nanoseconds, got bool | ['Foo.__bool__ ran OUTSIDE on_event']"。試験(残す。作業者が直す。ABC の登録は取り消せないので全部を新しいプロセスで走らせる): PYTHONPATH=src python -m pytest tests/bt/critic/item_0/test_i0r13_process_global_state_decides_core_values.py -p no:cacheprovider → 3 回とも '7 failed'(落ち方: "('ok', [0.0]) []" / "('ok', [0.0]) ['hook']" / "False ('ok', [0.75]) ('ok', [0.0])" / "[('OrderApiError', []), ('TimestampUnitError', ['Foo.__bool__'])]")。前の周の直りの確かめ: 第 11 周の試験 4 本 → '55 passed in 0.77s'。tests/bt/critic/item_0 + tests/bt/battery/item_0 → '310 passed'。tests/bt/item_0 → '1690 passed, 2 skipped'。<S> = /tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt

`structural_change_since_prev`: False。記録: `docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/round_13/CRITIC.md`。

### 作業者 0#13 の `questions_for_lead`(逐語)

- (前の 2 回の版からの繰り返し。LEAD_DESIGN にまだ答えが無い)契約 scope の対象外「numbers の ABC に派生・登録した、__subclasshook__ かメタクラスのフックを持つ class(class を定義することはプログラムを変えること)」(contract.py:137-138)について聞く。戦略は on_event の中で普通に class を書ける(numbers.Integral の子で、メタクラスが __subclasscheck__ を持つもの)。その class があると、核の values.settle(values.py:470-471 `issubclass(t, abc)`)が ABC の仕組みを通して、そのフックを戦略の呼び出しの外で走らせる。3 回目の実測: `PYTHONPATH=src python3 /tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/r13_worker_run11/item0_r13_worker_run11_probe_numbers_abc.py` → "party __subclasscheck__ calls: [('outside', 'float32')]"。断りは LatencyModelError のままである。族は i0-r9-02(外の物のコードが核の手順の中で走る)。これを「プログラムを変えること」として対象外のまま残すか、次の周で直すかを決めてほしい。直す場合の候補: 静的な型が数かどうかを ABC に聞かずに決める(静的な型の MRO の中の型を、数の ABC に登録された型と同一性で比べる)。numpy の型の扱いが今と同じになるかは測っていない(未確認)。
- (前の 2 回の版からの繰り返し)契約 history_limit の文にあった第 12 周の誤り(塊を「about 64 bytes」と書いていた)を、§9.3 の 38 で指示された同じ文の中で実測の値に直した。実測の値は、sys.getsizeof で 80 バイト + 1 件 16 バイト、pending の list の欄 8 バイト、1 回に落とすのは history_limit + 1 件である。指示は 88.2 の実測を残すことだけだったので、この直しが指示の範囲に入るかを確かめたい。範囲の外なら戻す。

試験の末尾(逐語): 項目 0・核・批評家の試験: 「1830 passed, 2 skipped in 342.18s (0:05:42)」(飛ばした 2 件は前からあるもの: tests/bt/item_0/test_bt0_carriers.py:144「bool cannot be subclassed」、tests/bt/critic/item_0/test_i0r5_battery_opponent_grading.py:130 は調査の venv が無いときに飛ばす)。i0-r11 の批評家の試験 4 本とこの周の 25 件: 「80 passed in 0.84s」。全試験: 「4 failed, 4874 passed, 6 skipped, 1 warning in 845.70s (0:14:05)」。落ちた 4 件はすべて tests/bt/battery/item_0/(test_battery_def_grids.py の 2 件と test_battery_item0.py の 2 件)。場面集(最後に 1 回): 「7 failed, 162 passed in 57.83s」。落ちた 7 件は上の 4 件、test_battery_item0.py::test_definitions_in_sync_with_scenes、test_battery_r13_claims.py の 2 件。どれも、同じ時間に場面係が直している場面集の途中の物である(§9.2 の 34 で正の定義 C の文を置き換えている途中の語の判断。例: ('segment text differs', 62, '`covers` は', '`covers` は場面の宣言で')。§9.2 の 33 の types_in・requests の試験)。作業木で変わっていたのは tests/bt/battery/item_0/ の 30 本と、追跡されていない test_battery_r13_claim_mutants.py だけだった。実装の側で落ちた試験は 0 件。場面集を回したあとに批評家の i0-r11 の 3 本(covers_within を含む)を回し直した結果は「45 passed in 0.09s」。

## リードの答え(2026-09-25 04:40 UTC。段の途中で規則は足さない。次の起動の lead_notes に写す)

- 場面係の変えた点 1(升目は宣言と入力の両方が要る = F の部分集合): **採る。**F の目的は「測っていない範囲を狭く見せない」ことで、変えた形は F が数えない升目を足さず、積の広がり 17 升目を数えない側に閉じる。「手書きの宣言は上限としてだけ使い、宣言の型が入力から出なければ試験が落ちる」も採る。
- 変えた点 2(頼みは入力の欄 `requests` から読む、参照の戦略の実際の頼みと試験で照らす): **採る。**F が決めていなかった所を機械で埋めたもの。
- 変えた点 3(`types_in` ⊆ runner が設定つき対象に渡した入力の型): **採る。**L-438 (2) と同じ物で、`type_plan` の無い場面では 33 と同じ。
- br13-1-1 [聞く]: リードの答え = **この設計で通過を出してよい。ただし条件つき。**族 3(受付・拒否・約定のどれを測るか)の宣言は上限としてだけ働き、入力から出ない型は試験で落ちる。どれを数えるかの読みは批評家が毎周読む(§8.5 の 24 と同じ分担)。通過の報告には「人の読みで残る点」としてこの族を逐語で載せる。機械で閉じる案(場面の `strategy` が出す頼みの種類ごとに 3 つのどれかを `requests` の欄から機械で決める)は次の場面集の直しの周に場面係が試し、できなければ理由を ROOTCAUSE に書く。
- br13-1-2 [聞く]: リードの答え = **区別して書く。**升目の表の注記に「相手の adapter 37・設定つき対象 41 は `requests` の記録なし = 『入った』と数えない」を数とともに書き、通過の報告の「測っていない範囲」に同じ文を載せる。「50 → 27」は宣言と入力から出る升目の数の変化で、相手の側を同じ厳密さで確かめた結果ではない(リードは相手の側の記録を読んでいない = 未確認)。
- br13-1-3 [聞く]: リードの答え = **次の場面集の直しで、gobacktest の trade → tick の作り替えを族 5 の格子の 1 ケースとして試験に入れる**(`types_in` がこの経路を「代えた型」として除外していることの実測を ROOTCAUSE に書く)。今は場面係の §6.3 の理由だけで、リードも実測していない(未確認)。
- 作業者の問い 1(数の ABC の対象外): **直す。**この問いは第 12 周の版から 3 回繰り返されていて、リードが答えていなかった(リードの側の不履行 = 第 12 周の戻しと同じ「答えの時機」の族)。批評家 i0-r13-01 が同じ根を [止める] にしたので、第 14 周の作業者は批評家の指摘のとおり直す(数の種類を ABC の登録に聞かない = 静的な型の MRO を核が持つ型の表と同一性で比べる / `sys.modules` をたどらない)。numpy の型の扱いが同じになるかは試験で測って報告に書く(未確認のまま通さない)。
- 作業者の問い 2(「about 64 bytes」の直し): **範囲の中。**同じ文の事実の誤りを実測の値に直すのは §9.3 の 38 の「実測を残す」に含まれる。戻さない。

## 第 14 周(進行中。05:37 UTC の見回りで写した分)

| 段 | 開始 | 終了 |
|---|---|---|
| 作る:0#14 | 04:25:30 | 05:28:17 |
| 表:0#14 | 05:28:19 | 05:33:31 |
| 批評:0#14 | 05:33:32 | (進行中) |

### 作業者 0#14 の返り値(逐語。`unmet` は提出前の吟味の記録)

- `structural_change`: 核が値を受け付ける・断る・計算するときに、プロセス全体の状態を実行中に読まない形にした。読まなくなった状態は、ABC の登録簿と覚え、sys.modules とモジュールの属性、スレッドの十進の文脈、codecs の誤り処理の登録簿、int と文字列の桁の上限、再帰の上限と積み上がり。数の種類と写像は、読み込み時に束ねた表(values.NUMBER_BASES・_MAPPING_BASES、numpy の型を含む)と型自身の MRO の同一性で決める(values.is_a も MRO の同一性にした)。FrozenDict は ABC を問わない自分の __eq__ を持つ。str は切り出しで作る。to_nanos は呼ぶたびに固定の設定から文脈を作る。エラー文の int は長さに依らず作り(int_text・value_text)、平らな値の入れ子は核の上限 MAX_NESTING=100 で、値を持つ欄から数える。
- `tests_added`: 94 / `test_tail`: 項目 0・批評家・場面集の試験(最後の版): 「2101 passed, 2 skipped in 463.15s (0:07:43)」。全試験: 「5002 passed, 6 skipped, 1 warning in 887.46s (0:14:47)」。全試験を走らせている途中で time.py の十進の設定を読み込み時の tuple に束ね直したので、そのあと最後の版で項目 0・批評家・場面集を回し直した(上の 2101 passed)。批評家の i0-r13-01 の試験は、直す前が「7 failed, 23 passed」、直した後が「30 passed in 1.54s」(i0-r11 の 3 本を含む)。新しい格子は「94 passed in 12.59s」。
- `changed_files`: ["src/bot/bt/core/values.py", "src/bot/bt/core/time.py", "src/bot/bt/core/engine.py", "src/bot/bt/core/ordering.py", "src/bot/bt/core/api.py", "src/bot/bt/core/events.py", "src/bot/bt/core/contract.py", "tests/bt/item_0/test_bt0_r14_process_state.py(新規)", "tests/bt/item_0/_r14_state_child.py(新規。上の試験が新しいプロセスで走らせる子のプログラム)", "tests/bt/item_0/test_bt0_sender_types.py(書き直し: 登録ではなく numbers.Real の継承で数にする)", "tests/bt/item_0/test_bt0_r11_foreign_objects.py(書き直し: _failing_number を継承で数にする)", "tests/bt/item_0/test_bt0_r12_party_hooks.py(説明文だけ)", "tests/bt/item_0/test_bt0_r10_strategy_side.py(説明文だけ)", "docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/round_14/ROOTCAUSE.md(新規。直す前に書いた根本原因と構造、作業中に見つけた同じ根の 2 つ、確かめ)"]
- `unmet`:
  - 満たせなかった要件の行: 無し。以下は委任文 §3「提出前の吟味」の記録。<W> = /tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/r14_worker。
  - (1) i0-r13-01([止める]、実装)。直した根拠は次のとおり。values.py:276 number_kind と :269 NUMBER_BASES(numbers の ABC を継承の基として扱い、numpy が自分で登録する integer / floating / inexact を並べた表。numpy/_core/numerictypes.py 627-629 行を写した)を置いた。これを _plain_scalar(:479)と _settle(:540)が使い、ABC には問わない。numpy の bool は values.py:262 _NP_BOOL で読み込み時に束ねた(sys.modules を読まない)。確かめ: 批評家の試験は直す前が「7 failed, 23 passed in 1.68s」(<W>/pytest_item0_r14_worker_start.log)、直した後が「30 passed in 1.54s」。
  - (1) i0-r11-01・i0-r11-03([直す]、第 12 周に直した)。この周の初めと終わりに批評家の試験を回した。上の 30 passed の中に test_i0r11_class_dict_key_runs_foreign_code.py・test_i0r11_pinned_dropped_facts_fail_the_core_step.py・test_i0r11_history_limit_exact_refusal.py が入っている。第 13 周の批評家も直りを確かめている(round_13/CRITIC.md)。この周は構造を変えていない。
  - (2) 同じ根の全箇所。核の全ファイルで ABC への問い合わせ・sys.modules・実行中の設定の読みを grep し、1 つずつ試した(ROOTCAUSE.md §A の表の 1〜9)。(4) engine.py:764・ordering.py:189 の is_a(events, Mapping) を values.py:294 is_mapping に替えた(<W>/item0_r14_worker_probe_other_global_state.out: 前の実行の戦略が登録すると、後の実行の構築が AttributeError になり、前の戦略のフックが走っていた)。(5) time.py の to_nanos を time.py:91 _decimal_context に替えた(同じ出力: prec=5 で 1700000000123456789 → 1700000000000000000 と黙って誤っていた)。(6) 大きな int の文を values.py:305 int_text・:313 value_text にし、time.py・engine.py:555,873・api.py の _count_arg と読みの断り・exception_text で使う(<W>/item0_r14_worker_probe_limits.out: 5000 桁で ValueError になっていた)。(7) 入れ子の上限 values.py:337 MAX_NESTING を置き、freeze(:825)と _settle で数える。extra は api.py:179 で outer=2 とした(<W>/item0_r14_worker_probe_depth.out: 600 段で RecursionError になっていた)。(8) FrozenDict.__eq__(values.py:781)。継いだ Mapping.__eq__ が Mapping の登録簿を問うていた(<W>/item0_r14_worker_probe_frozendict_eq.out: 継いだままだと 16 of 16、直すと 0 of 16)。(9) values.py:110 _new_str を切り出しと連結にし、codecs の登録簿を引かないようにした(<W>/pytest_item0_r14_worker_after5.log で codecs_error:surrogatepass が落ち、after6 で通る)。付随: freeze の where の文は鍵の repr を使わない(values.py _key_text)。数の欄の断りの文は、送り手の repr ではなく変換した float を載せる(api.py _require_positive、events.py _finite/_positive)。
  - (3) 批評家の試験と場面集の試験を全部回し、落ちるものは無い(最後の版で 2101 passed, 2 skipped)。規則 8(批評家の試験自身の誤り)に当たるものは無い。
  - (4) 厳しい批評家が [止める] にしそうな点と、その処置。(a) 登録だけの Python の class を数と数えなくした。これは批評家が指定した直し方(登録簿に聞かない)どおりで、数であることは class 自身の継承で示せる。素のプロセスで答えが変わる型は 0 件だった(試験 test_in_a_clean_process_the_core_decides_numbers_and_mappings_as_the_abcs_do。numpy・pandas・核を読み込み、全ての class を列べた)。振る舞いは契約 contract.py:138 process_state と PLAIN_DATA_RULE に書き、試験 test_the_battery_itself_decides_the_values_by_the_rule で縛った。(b) numpy を読み込みの前に書き換えた場合は、核の読み込みを止める(試験 test_the_core_refuses_to_load_with_a_numpy_changed_before_it、4 件)。(c) 残る対象外は契約に書いた。核が呼ぶ名前の付け替え(builtins・heapq・核のモジュール)、解釈系のフック、核が要る深さより低い再帰の上限、メモリ。核が型や値を決めるために実行中に引く名前は無い。numpy の名前の付け替え 10 種と sys.modules の差し替えは、格子で変化 0 を示した。(d) 格子の中の試験の誤りを 1 つ直した。hook:collections.abc.Mapping は最初、負の覚えを消すための Sized.register がフック自身に「既に Sized」と答えられ、登録が起きていなかった。自分の ABC に登録する形に直すと、直す前の核で AttributeError と hooks_in_core 3 件が出た(ROOTCAUSE.md §C)。
  - (5) 場当たりの直しはしていない。試験だけを特別扱いする所・閾値や既定値をずらした所・文言だけ合わせた所・機能を外した所は無い。MAX_NESTING=100 は新しい上限で、根拠は実測(1 段あたり最大 3 フレーム、run の中は約 20、<W>/item0_r14_worker_frames.out)。値はリードに聞く。
  - (6) 直した規則ごとに、入力の空間を全格子で列べる試験を先に書き、直す前に落ちることを確かめてから直した。tests/bt/item_0/test_bt0_r14_process_state.py は 4 つの格子からなる。格子 1 はプロセスの状態の変更 80 通り(numbers と collections.abc の全 ABC × {全型の登録, True を返すフック}、十進の文脈 5 種、桁の上限 640、numpy の名前 10 種、sys.modules、警告を誤りに、np.seterr、codecs の誤り処理 2 種)× 核が値を決める全ての場所 × numpy の全ての数の型と組み込みの型ほか。格子 2 は素のプロセスでの等価性。格子 3 は大きな int が入る入口 19 × 値 7 × 桁の上限 2。格子 4 は入れ子の深さ 0〜103 × 容器 5 × 入口 5 × 先に使った積み上がり {0, 300}。列に入れなかったもの(核が呼ぶ名前の付け替え、解釈系のフック、低い再帰の上限、ほかのモジュールの ABC とその理由)は試験の説明文に書いた。消した試験は無い。書き直した既存の試験は 2 本(test_bt0_sender_types.py の 1 件、test_bt0_r11_foreign_objects.py の _failing_number)で、どちらも登録ではなく継承で数にした。理由は、この周の規則で登録だけでは数と数えなくなったこと。
- `questions_for_lead`:
  - 入れ子の上限 MAX_NESTING = 100(values.py:337)は、この周に私が置いた値です。根拠は実測で、核の最も深い歩き(renew)が 1 段あたり 3 フレーム、run の中の積み上がりが約 20 でした(/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/r14_worker/item0_r14_worker_frames.out)。この値なら既定の再帰の上限 1000 の半分に収まります。数え方は値を持つ欄から数え、extra ではその tuple と組の 2 段を含みます。上限を置くこと自体と、この値のままでよいかを決めてください。
  - 契約の process_state の「対象外」(contract.py:138)を次の範囲にしました。核が呼ぶ名前の付け替え(builtins・heapq などライブラリの関数・核のモジュールの名前)、解釈系のフック(sys.settrace/setprofile・監査のフック・gc の知らせ・信号・戦略が立てたスレッド)、核が要る深さより低い再帰の上限、メモリです。付け替えを外した理由は、プログラムのコードを変えることにあたり、核が呼ぶ標準ライブラリの Python のコードも同じ builtins を引くからです。この範囲でよいかを確かめたいです。
  - 振る舞いの変化が 2 つあります(契約 core-15 と PLAIN_DATA_RULE に書きました)。(1) numbers の ABC に登録しただけで継承していない Python の class は、数と数えず断ります。素のプロセスでは、この変化で答えが変わる型は 0 件でした。(2) 核は読み込み時に numpy を import します(依存に既にあります)。項目 11・13 は契約を読む前提ですが、別の周知が要るかを決めてください。

### 表 0#14 の `notes`(逐語)

再利用(L-435): 場面集の指紋 dff3bc733c6e6041c1e9759c20085ab29c5501088417d583c17e583185b6ca98 は第 13 周と同じだった。当方の現状と調査結果の側の設定つき対象 54 件の結果は、第 13 周の materials の runs/・runs_2/ から写して使った(写した記録は materials/reuse_round13.sh と logs/reuse_round13.out、指紋は logs/scene_set_fingerprint.txt)。新実装と試金石はこの周に 2 回ずつ走らせ、4 回とも rc=0 だった。

手順 1: 新実装の adapter tests/bt/battery/item_0/adapters/new_impl.py は既にあったので変えていない。この周の核でも、使う公開の名前 18 個がすべて __all__ にあり、32 場面を通った。adapter を変えると場面集の指紋が変わる。

提出前の吟味:
- 観点ごとの一致の数は、runs/*.tsv から make_tables.py を使わずに recount.py で数え直した。6 枚の表の数の行との不一致は 0。表のセルを数える recount_cells.py でも不一致は 0。
- 数の行の中身:
  - 新実装: 正しさ 32/32、再現 32/32
  - 当方の現状: 正しさ 8/32(P0-1 1/3、P0-2 2/4、P0-3 1/11、P0-4 1/3、P0-5 1/3、P0-6 0/3、P0-7 2/5)、再現 32/32
  - 調査結果の側: 正しさ 31/32(P0-3 10/11)、再現 32/32
  - 試金石: 正しさ 31/32(P0-4 2/3)、再現 32/32
- 全対象を全場面に通したか: 57 対象がすべて 32 場面の行を持つ(make_tables の load が欠けを検める)。場面ごとの結果なしは、調査の側の注記に「試したこと・出たもの・実測の所要の秒数」として出ている。grep '未記録' は 6 枚とも 0。
- 注記に道具を特定できる語が無いか: 175 語の型で grep した。当たったのは調査の側の 2 枚の候補の注記の一般の語「書き直」2 件だけ。全対象の base 名 41 が型に入っていることは check_notes.py で確かめた(漏れ 0)。時刻の形も 6 枚とも 0。型の組の 1 文は 6 枚とも 1 回ある。
- 注記の行は、grid_c.py の CLI の出力と照らした。not_entered.tsv との違いは 0、表の注記で not_entered.tsv に無い行も 0。
- md5: 組ごとの 2 通りの表は 3 組とも違う(identical は全部 false)。第 1 回と第 2 回の実行から作った同じ表 id の表は、pass2_tables では 6 枚ともバイト単位で同じだった。pass2_tables_ownlog では、調査の側の 2 枚が注記の所要の秒数だけ違う。
- 記録は全部 materials/ に置いた(対応表.md・mapping.tsv・commands.txt・logs/ ほか)。

未確認の点:
- 6 枚とも、同じ表 id の第 13 周の表と題の周番号を除いて同じだった。新実装の結果が第 13 周と同じ 32/32 のため。
- 核のファイルの sha256 は、走らせたあとにだけ記録した(logs/final_state.txt)。走らせる前の値は記録していないので、走らせている間に核が変わらなかったかは未確認。
- 写した 3 対象で、第 1 回と第 2 回の出力の値の欄が違う(正しさと再現の欄は同じ)。第 13 周と同じ具体で、表のセルには出ない。

### リードの答え(作業者 0#14 の問い。段の途中で規則は足さない。次の起動の lead_notes に写す)

- 問い 1(MAX_NESTING = 100): **上限を置くこと自体は採る**(再帰の上限というプロセスの状態を核が読まない形にするには核自身の上限が要る)。**値 100 も採る。**根拠は作業者の実測(1 段 3 フレーム、run の中の積み上がり約 20、既定の再帰の上限 1000 の半分)で、これを契約の文に逐語で残す(A-12 = 根拠のない設定値を置かない、の要件は実測で満たす)。101 段で落ちるのが RecursionError でなく核の型つきの断りであることは格子 4(0〜103 段 × 積み上がり {0, 300})が示している。批評家が読む。
- 問い 2(process_state の対象外の範囲): **採る。**名前の付け替えと解釈系のフックは「プログラムのコードを変えること」で、核が呼ぶ標準ライブラリも同じ builtins を引くという理由は成り立つ。条件: 対象外の各項に「測っていない」と「測って変化 0 だった」(numpy の名前 10 種・sys.modules の差し替え)を分けて契約に書く(§5.2 「棄却には射程を書く」)。
- 問い 3(振る舞いの変化 2 つ): (1) 登録だけの class を断る = **採る**(批評家 i0-r13-01 の指定した直し方で、素のプロセスで答えが変わる型 0 件を試験で示した)。(2) 読み込み時の numpy の import = **採る。**項目 11(参照実装は委任文 §2 と要件だけから書く)は契約 core-15 を読む前提で足りる。項目 13(統合)には次の起動の lead_notes["13"] に「核は読み込み時に numpy を import し、numpy が読み込み前に書き換えられていれば読み込みを止める(core-15)」の 1 行を足す。段の途中で規則は足さない。

### 批評家 0#14 の出力(逐語。06:40 UTC の見回りで写した)

- **i0-r14-01** [止める](target: 実装, repeat_of: i0-r13-01, fix_files: ['src/bot/bt/core/values.py', 'src/bot/bt/core/contract.py'])
  核は落ち着かせた値から集合と辞書を作り直すとき(values.py 570・576 行 _settle、848・851 行 _freeze)、hash の衝突した要素どうしを比べる。Fraction と Decimal(float・complex)の等しさはライブラリのコードで numbers の ABC に聞く(Fraction.__eq__ の isinstance(b, numbers.Rational)、C の decimal の isinstance(w, Rational))。Fraction(1) と Decimal(2**61) は hash が同じで等しくない。(a) 再現性: その 2 つを鍵に持つ extra の注文を出す同じ実行が、新しいプロセスでは run ok、別の実行の戦略が numbers.Rational.register(Decimal) を呼んだあとは同じプロセスで AttributeError で止まる。(b) 戦略の登録だけで、別の者(口座)の強制注文が AttributeError で止まる。(c) 戦略が Rational の子でメタクラスに __subclasscheck__ を持つ class を作ると、核が注文を作り直すとき(_settled_request → _frozen_extra → freeze、on_event の外)にそのフックが走り、True なら断りが OrderApiError でなく AttributeError。契約 process_state の「a registration, a subclass hook … in any earlier run of the process -- changes no value, refusal or result of the core, and runs no code of that party」に反する。根本原因: 作業者の格子は核のソースの isinstance/issubclass/is_a を読んで「ABC に聞かない」を示したが、核が呼ぶライブラリのコードが ABC に聞くことと、数の型をまたぐ hash の衝突は列の外だった。再現性の崩れなので [止める]。族は i0-r13-01。
  証拠: PYTHONPATH=src python3 <S>/r14_critic/item0_r14_critic_probe_fraction_decimal_eq.py {none,hook,hook_outside_true,register,rerun,account}(1 つずつ新しいプロセス)→ 'none -> ("run ok", [])' / "hook -> ('run ok', [('hook', 'inside', 'Decimal'), ('hook', 'OUTSIDE on_event', 'Decimal')])" / 'run A, fresh process : ("run ok", [])' / "run B (registers Decimal) : ('run raised AttributeError: 'decimal.Decimal' object has no attribute 'numerator'')" / 'run A again, same input : (run raised AttributeError …)' / "account's forced order, strategy registers nothing: run ok" / '… strategy registered Decimal with Rational in its on_event: run raised AttributeError'。<S>/r14_critic/item0_r14_critic_probe_eq_sites.out: 登録のあと values.settle / values.freeze / settle(frozenset) が AttributeError(fractions.py 683 行)。試験(残す): PYTHONPATH=src python -m pytest tests/bt/critic/item_0/test_i0r14_process_state_through_library_code.py -p no:cacheprovider → 4 failed のうち 3 件がこの指摘('the same run in one process: ok before, AttributeError after another run's registration' / 'ok without, AttributeError after the strategy's registration' / "ok | ['Decimal']")。<S> = /tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt
- **i0-r14-02** [止める](target: 実装, repeat_of: i0-r13-01, fix_files: ['src/bot/bt/core/values.py', 'src/bot/bt/core/contract.py'])
  values.py の _make_copier(948 行)と _make_rebuilder(985 行)は関数の中で import dataclasses を実行し(実行中に sys.modules を読む)、作った copier / rebuilder を carrier の class を初めて写す・取るときに作って、モジュールの表 _COPIERS(929 行)・_REBUILDERS(964 行)にプロセスの残りの間置く。戦略が自分の 1 回の呼び出しの間だけ sys.modules['dataclasses'] を自分のモジュールに替え、次の呼び出しで戻すと、(a) 約定の模型の Fill(liquidity='maker') が口座に 'taker' で届く(黙って誤った値。戦略の fields が liquidity を落とし既定値が入る)、(b) sys.modules を戻したあと同じプロセスで走らせた別の(何もしない)戦略の実行も 'taker'(新しいプロセスでは 'maker')= 核自身の表が影響を持ち越す、(c) 戦略の fields が戦略の呼び出しの外で 7 回走る。契約 process_state の「sys.modules or a module's attributes are never read to decide」「in any earlier run of the process -- changes no value」と、作業者の「sys.modules の差し替えは格子で変化 0」(格子が替えたのは numpy だけ)に反する。関数の名前の付け替え(契約の対象外)ではなく sys.modules のモジュールの差し替え。黙って誤った値と再現性の崩れで [止める]。族は i0-r13-01 (d)。i0-r14-01 と同じ根(探し方が核のソースの文字列の grep で、実行中に走る import・遅れて作る表・ライブラリのコードを列べていない)。
  証拠: PYTHONPATH=src python3 <S>/r14_critic/item0_r14_critic_probe_lazy_rebuilder_cache.py fresh → "run B (clean strategy), fresh process : ['maker']"。同 poisoned → "run A (its strategy swaps sys.modules['dataclasses'] for one callback): ['taker']" / "sys.modules['dataclasses'] is the real module again: True" / "run B (clean strategy), same process, after run A : ['taker']" / "strategy's fields() ran OUTSIDE its call for OrderRequest / Ack / Fill / Ack / FillNotice / Fill / OrderAckEvent"(…_lazy_rebuilder_cache.out)。試験(残す): tests/bt/critic/item_0/test_i0r14_process_state_through_library_code.py::test_a_module_swapped_in_sys_modules_for_one_callback_changes_nothing_in_this_or_a_later_run → "run A (its strategy swapped sys.modules['dataclasses'] for one callback): taker"。<S> = /tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt
- **i0-r14-03** [止める](target: 実装, repeat_of: None, fix_files: ['src/bot/bt/core/time.py', 'src/bot/bt/core/values.py'])
  to_nanos は「Conversion is exact」「rounding: none (inputs with sub-nanosecond digits are rejected)」(time.py 8・63 行)と書くが、Fraction を先に float にし(174 行 float.__repr__(float(v)))、numpy の longdouble を scalar(162 行。NUMBER_BASES の numpy.floating → float)で float にしてから正確さを検めるので、値が持つ桁を落とした結果を黙って受け付ける。to_nanos(Fraction(1700000000123456789), 'ns') → 1700000000123456800(11 ns ずれる)、Fraction(…, 10**9) を 's' で → …700(89 ns)、np.longdouble('1700000000.123456789')(この桁を持つ)を 's' で → …700。要件 §1「時刻は UTC の int64 ナノ秒」と観点 P0-2 に対し、核の唯一の時刻の変換口が黙って誤った時刻を返す(前の周からある振る舞いで、場面集の P0-2 は ISO と int しか入れない)。黙って誤った値で [止める]。
  証拠: PYTHONPATH=src python3 <S>/r14_critic/item0_r14_critic_probe_to_nanos_exact.py → 'longdouble holds: 1700000000.123456789' / 'to_nanos(longdouble, s) -> 1700000000123456700' / 'Fraction exact ns: 1700000000123456789' / 'to_nanos(Fraction, s) -> 1700000000123456700' / 'to_nanos(Fraction(1700000000123456789), ns) -> 1700000000123456800' / 'to_nanos(1700000000123456789, ns) (int, for comparison) -> 1700000000123456789'。試験(残す): PYTHONPATH=src python -m pytest tests/bt/critic/item_0/test_i0r14_time_values_silently_changed.py -p no:cacheprovider → '10 failed'、うち test_to_nanos_is_exact_or_refuses の 4 件('gave 1700000000123456700, the value states 1700000000123456789 (off by -89 ns)' ほか)。<S> = /tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt
- **i0-r14-04** [止める](target: 実装, repeat_of: None, fix_files: ['src/bot/bt/core/values.py', 'src/bot/bt/core/time.py', 'src/bot/bt/core/contract.py'])
  numpy.timedelta64 は numpy.signedinteger の子なので values.NUMBER_BASES(269 行)が int と決め、int() がその単位での数を返す。単位を持つ長さが、その数のナノ秒として黙って受け付けられる。時刻の関門 validate_nanos(time.py 105・121 行 as_int)・values.settle・差し込み口の答え(take_int)で起きる: validate_nanos(np.timedelta64(5,'Y')) → 5、(5,'M') → 5、(5000,'fs')(5 ps)→ 5000、(5,'ps') → 5。ms・us の小さな数は断られるが np.timedelta64(1700000000000000000,'ms') は 1700000000000000000 として通る(単位と数の大きさで断るか黙って数を取るかが変わる)。遅延の模型が np.timedelta64(5000,'ps')(= 5 ns)を返すと、注文は 5000 ns 後に取引所に着く。要件 §1 の int64 ナノ秒と遅延模型の口に対し、黙って 1000 倍・年や月の数が入る。この周に数の種類を表で決め直したときも列の外だった。黙って誤った値で [止める]。
  証拠: PYTHONPATH=src python3 <S>/r14_critic/item0_r14_critic_probe_timedelta_unit.py → "MRO: ['timedelta64', 'signedinteger', 'integer', 'number', 'generic', 'object']" / "number_kind(timedelta64): <class 'int'>" / "np.timedelta64(5, 'ps') validate_nanos -> 5" / "np.timedelta64(5000, 'fs') validate_nanos -> 5000" / "np.timedelta64(5, 'Y') validate_nanos -> 5" / "np.timedelta64(5, 'M') settle -> 5" / "np.timedelta64(5, 'ms') settle -> raised Unsettled" / "np.timedelta64(1700000000000000000, 'ms') validate_nanos -> 1700000000000000000" / "run ok | what the strategy saw: [..., ('OrderAckEvent', 5000), ('OrderFillEvent', 5000), ...]"。試験(残す): tests/bt/critic/item_0/test_i0r14_time_values_silently_changed.py の test_a_duration_with_a_unit_is_not_taken_as_that_many_ns 5 件と test_the_latency_models_delay_in_picoseconds_is_not_taken_as_nanoseconds('the order reached the venue [5000] ns after it was sent; the model said 5 ns')。<S> = /tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt
- **i0-r14-05** [直す](target: 実装, repeat_of: i0-r13-01, fix_files: ['src/bot/bt/core/values.py', 'src/bot/bt/core/contract.py'])
  契約 process_state(contract.py 158 行)は入れ子の上限を「the core's own bound, not the recursion limit or the stack depth of the call」と書き、リードの答えは格子 4 を「101 段で落ちるのが RecursionError でなく核の型つきの断り」を示すものと読んだ(批評家が読む、とした)。格子 4 が試した戦略自身の積み上がりは {0, 300} だけで、戦略が積み上がり 800 から extra の入れ子 98 段(MAX_NESTING 100 の中)の注文を出すと RecursionError、900 からなら 50 段でも同じ(0・300・600 からは受け付ける)。受け付けるか・断りの型が呼び出しの積み上がりで変わり、契約の文と食い違う。起きるのは戦略自身の呼び出しの中で、黙って誤った値は無く、同じ戦略なら毎回同じなので、前の周の同じ格(断りの型が契約と違う、i0-r11-01・03)に合わせて [直す]。契約の文を事実に合わせる(核が要る残りの深さを書く)か、核の歩きで RecursionError を入口の誤りに替えるかが要る。
  証拠: PYTHONPATH=src python3 <S>/r14_critic/item0_r14_critic_probe_stack_depth.py → 'strategy's own depth 600 | extra nesting 98 -> place_order: accepted' / 'strategy's own depth 800 | extra nesting 98 -> place_order: RecursionError: maximum recursion depth exceeded while getting the str of an object' / 'strategy's own depth 900 | extra nesting 50 -> place_order: RecursionError …'。試験(残す): PYTHONPATH=src python -m pytest tests/bt/critic/item_0/test_i0r14_nesting_refusal_depends_on_the_callers_stack.py -p no:cacheprovider → '3 failed, 12 passed'('extra nesting 98 (<= MAX_NESTING 100) from the strategy's stack depth 800: RecursionError; from depth 0: taken' ほか)。<S> = /tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt
- **i0-r14-06** [直す](target: 場面集, repeat_of: i0-r11-02, fix_files: ['tests/bt/battery/item_0/grid_c.py', 'tests/bt/battery/item_0/scenes.py', 'tests/bt/battery/item_0/gen_definitions.py'])
  升目の表の P0-2 は「升目 160: 場面にした 0 / 測っていない(固定した測り方の外) 160」で、全升目の判断が「固定した測り方の外」(DEFINITIONS.md 163 行〜)。P0-2 の固定した測り方「既知の時刻を投入し、核が保持する値が同じ int64 ナノ秒と一致するか」を、p2-iso-utc・p2-iso-offset(ISO → int64 ナノ秒)と p2-event-time-exact・p2-one-ns-apart はそのまま測っている。0 になったのは第 r13-1 回の正の定義(F)で升目の事象の型を入力から機械で出すことにし、p2-iso-* は事象を持たず、p2-event-time-* は型を対象が選ぶため、どの升目にも当たらなくなったから。升目の軸に「事象の型を入力が決めない場面」「事象を持たない変換の場面」を載せる行が無く、オーナーへ渡る「測っていない範囲の記録」で P0-2 が 1 つも測られていないと読める。向きは通過に不利(測った物を測っていない側に置く)で、場面・正解・比較の表のセルは変わらないので [直す]。r11-02(升目の判断が場面の測る物と合わない)と同じ族で向きが逆。F の文どおりの結果なので、場面係は F の範囲で「固定した測り方の外」と「測ったが升目の型を入力が決めない」を分ける形があるかを確かめ、無ければリードに聞く。
  証拠: sed -n 163,175p tests/bt/battery/item_0/DEFINITIONS.md → '### P0-2(升目 160: 場面にした 0 / 測っていない(固定した測り方の外) 160)' と '| 約定 | 戦略の呼び出しに届く物 | int64 ナノ秒 | 測っていない(固定した測り方の外) | — |' ほか。同じファイル 715-747 行に p2-iso-utc・p2-iso-offset・p2-event-time-exact・p2-one-ns-apart の定義(値の場面・能力の場面)。PYTHONPATH=src python3 tests/bt/battery/item_0/gen_definitions.py --check → 'OK'(表は機械の出力どおりで、F の文の結果であることを確かめた)

`structural_change_since_prev`: True。記録: `docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/round_14/CRITIC.md`。

### 審査員 0#14(構造の変化ありのため 6 体が起きた。逐語)

| 段 | 開始 | 終了 |
|---|---|---|
| 批評:0#14 | 05:33:32 | 05:58:11 |
| 盲検:0#14:current0〜2 | 05:58:12 | 05:58:45 |
| 盲検:0#14:survey0〜2 | 05:58:38 | 05:59:30 |
| 作る:0#15 / 場面の直し:0#r15-1 | 05:59:31 | (進行中) |

#### 盲検:0#14:current0

- choice: 左
- reasons(逐語): 表のセルを自分で数え直した。「正解と一致」の数は観点ごとに次のとおりで、表の集計行と一致した。行 A: P0-1 3/3、P0-2 4/4、P0-3 11/11、P0-4 3/3、P0-5 3/3、P0-6 3/3、P0-7 5/5、計 32/32。行 B: P0-1 1/3(p1-one-call-per-event のみ一致、ほか 2 件は対応なし)、P0-2 2/4(p2-event-time-exact と p2-one-ns-apart が一致、p2-iso-utc と p2-iso-offset は対応なし)、P0-3 1/11(p3-bar のみ一致、ほか 10 件は対応なし)、P0-4 1/3(p4-visible-at-step が一致、p4-received-time は対応なし、p4-future-read-attempt は不一致で every_attempt_stopped_by_error=false)、P0-5 1/3(p5-same-stream-order のみ一致)、P0-6 0/3(3 件とも対応なし)、P0-7 2/5(fill-model-swap と cost-model-swap が一致、latency-model-swap・cost-per-unit・account-swap は対応なし)、計 8/32。
再現(2 回の実行で同じ)は両方とも全観点で満点(A 32/32、B 32/32)なので、再現では差が無い。
正しさでは、7 観点のすべてで A が B 以上で、どの観点でも A が上回っている(P0-6 は B が 0/3)。場面の多い P0-3 を除いても、残りの 6 観点すべてで A が上である。B には対応なしに加えて、P0-4 の未来の読み出しの試しで黙って違う結果を返した不一致が 1 件ある(A はこの場面で正解と一致)。表の注記によると、行 B の対象には 15 の升目で型が入っていない(P0-3 の 6 升目、P0-1 と P0-5 の約定・板の写真・板の差分など)。行 A にはそのような升目が無い。よって A の方が正しく、再現性は同等である。
- missing_in_choice(逐語): 行 A は、表に載った 32 場面のすべてで正解と一致し、2 回の実行でも同じだった。表の結果の中に A の欠けは無い。ただし定義の升目の表を見ると、場面にしていない升目が多く残っている。P0-1 は 40 升目のうち場面にした物が 4、P0-2 は 160 升目のうち 0 で、時刻の単位を升目として測る場面が無い。加えて、資金調達・清算・時計・通知が発注や取消の呼び出しでその場で返る道、戦略が公開の手段で読む道も場面になっていない。これらについて A の能力は、この表からは分からない(未確認)。

#### 盲検:0#14:current1

- choice: 右
- reasons(逐語): 表から自分で数え直した結果。正しさ(正解と一致の数)は観点ごとに行 A と行 B の順で、P0-1: 1/3 と 3/3(A は p1-one-call-per-event だけ一致、merge-by-time と typed-events は対応なし)、P0-2: 2/4 と 4/4(A は iso-utc と iso-offset が対応なし)、P0-3: 1/11 と 11/11(A は p3-bar だけ一致、残りの 10 件は対応なし)、P0-4: 1/3 と 3/3(A は received-time が対応なし、future-read-attempt が不一致 {"every_attempt_stopped_by_error": false, "future_value_obtained": false})、P0-5: 1/3 と 3/3(A は same-stream-order だけ一致)、P0-6: 0/3 と 3/3(A は 3 件とも対応なし)、P0-7: 2/5 と 5/5(A は fill-model-swap と cost-model-swap だけ一致)。合計は A が 8/32、B が 32/32 で、表の集計の行と一致する。7 観点のすべてで B が A を上回り、A が上回る観点も並ぶ観点も無い。したがって場面の多い P0-3 に引きずられた差ではない。能力の場面(typed-events・one-ns-apart は A も一致・future-read-attempt・hand-over-order・cancel-notice・fill-seen・latency/account swap など)でも、A には「対応なし」または「不一致」が多い。再現(2 回の実行で同じ)は、A も B も全観点で満点(32/32)なので差は無い。注記によると、A は 15 の升目で型が入らなかった。B は入らなかった升目も、頼みの記録が無く入ったかを決められない升目も「無し」である。以上から、正しさで B が全観点で優れ、再現は同等なので、行 B(右)を選ぶ。
- missing_in_choice(逐語): 行 B に足りない場面は、表の上では無い。定義にある 32 場面(P0-1 は 3、P0-2 は 4、P0-3 は 11、P0-4 は 3、P0-5 は 3、P0-6 は 3、P0-7 は 5)がすべて表に載っており、B はすべてで「正解と一致」かつ「2 回の実行で同じ」である。型が入らなかった升目も、決められない升目も「無し」。ただし、この表は場面にした升目(計 27)だけを測っている。場面にしていない升目については、B の能力を表からは判断できない。

#### 盲検:0#14:current2

- choice: 左
- reasons(逐語): 表の各セルから数え直した。数え直した数は表の集計行と一致した。

【正しさ(正解と一致の数)】7 つの観点のすべてで行 A が上回るか同じで、下回る観点は 1 つも無い。
- P0-1: A 3/3、B 1/3。B は p1-merge-by-time と p1-typed-events が「対応なし」。
- P0-2: A 4/4、B 2/4。B は p2-iso-utc と p2-iso-offset が「対応なし」。
- P0-3: A 11/11、B 1/11。B で一致したのは p3-bar だけで、残りの 10 件は「対応なし」。
- P0-4: A 3/3、B 1/3。B は p4-received-time が「対応なし」。p4-future-read-attempt は「不一致」で、値は every_attempt_stopped_by_error=false。未来の値は取れていないが、すべての試みが誤りで止められてはいない。
- P0-5: A 3/3、B 1/3。B は p5-same-time-twice と p5-hand-over-order が「対応なし」。
- P0-6: A 3/3、B 0/3。B は 3 件すべてが「対応なし」。
- P0-7: A 5/5、B 2/5。B は p7-latency-model-swap、p7-cost-per-unit、p7-account-swap が「対応なし」。
- 計: A 32/32、B 8/32。
B は 7 つの観点のすべてで A を下回る。場面の数が多い P0-3 を除いても、残りの 6 観点すべてで A が上なので、場面数の偏りに引きずられた判断ではない。
能力の場面でも差がある。B は p1-typed-events・P0-3 の能力の場面(p3-bar を除く)・p5-hand-over-order・p6-cancel-notice・p6-fill-seen-by-strategy・p7-latency-model-swap・p7-account-swap で能力を示していない。表の注記には、B に型が入らなかった升目が 15 個あると書かれている。

【再現(2 回の実行で同じ数)】A も B も、7 つの観点すべてで満点(計 32/32)。この観点では差が無い。

以上から、正しさでは全観点で A が上、再現では同等なので、A(左)を選ぶ。
- missing_in_choice(逐語): 表の範囲では、行 A に足りない場面は無い。全 32 場面が「正解と一致」かつ「2 回の実行で同じ」で、注記も「型が入らなかった升目: 無し」。ただし表に載っていない升目(定義側で場面にしていない組)での振る舞いは、この表からは分からない(未確認)。

#### 盲検:0#14:survey0

- choice: 左
- reasons(逐語): 表の各セルを自分で数え直した(行ごとに「正解と一致」「2 回の実行で同じ」の出現数を数えた)。表の集計と一致した。
正しさ(正解と一致の数、A / B): P0-1 3/3 と 3/3、P0-2 4/4 と 4/4、P0-3 11/11 と 10/11、P0-4 3/3 と 3/3、P0-5 3/3 と 3/3、P0-6 3/3 と 3/3、P0-7 5/5 と 5/5。計は A 32/32、B 31/32。
再現(2 回の実行で同じ、A / B): 7 観点すべてで両者とも満点。P0-1 3、P0-2 4、P0-3 11、P0-4 3、P0-5 3、P0-6 3、P0-7 5 で、計はどちらも 32/32。
観点ごとに比べると、7 観点のうち 6 観点(P0-1・P0-2・P0-4・P0-5・P0-6・P0-7)は正しさも再現も同点。差が出たのは P0-3 だけ。B は場面 p3-mixed-one-run(値の場面。8 種の事象を 1 回の実行に混ぜる)が「対応なし」で、A は「正解と一致」。定められた良い順は 正解と一致 > 対応なし なので、この場面では A が上になる。B が A より上の観点・場面は 1 つも無い。再現はどちらも満点なので差にならない。
この差は場面の多い P0-3 の中の 1 場面にすぎないが、他の観点がすべて同点なので、観点ごとに比べた上でも A が一方的に上になる。したがって行 A(左)を選ぶ。差は 1 場面と小さい。
補足: 注記によると行 B は 54 の設定つき対象から場面ごとに最良の結果を寄せた行で、行 A は 1 つの対象の行。採点は表の結果だけで行い、この違いは判定に使っていない。
- missing_in_choice(逐語): 選んだ行 A に足りない場面は、この表の上では無い(32 場面すべてで「正解と一致」かつ「2 回の実行で同じ」)。参考として、行 B に足りない場面は P0-3 の p3-mixed-one-run(対応なし)の 1 件。

#### 盲検:0#14:survey1

- choice: 右
- reasons(逐語): 表の各セルを自分で数え直した(行ごとに「正解と一致」「対応なし」「2 回の実行で同じ」を数えた)。数えた値は表の上の集計表と一致した。
正しさ(正解と一致の数、A / B): P0-1 3/3 と 3/3、P0-2 4/4 と 4/4、P0-3 10/11 と 11/11、P0-4 3/3 と 3/3、P0-5 3/3 と 3/3、P0-6 3/3 と 3/3、P0-7 5/5 と 5/5、計 31/32 と 32/32。A には不一致も結果なしも無く、「正解と一致」でない 1 件は P0-3 の p3-mixed-one-run の「対応なし」である。この場面は 8 種の事象を 1 回の実行に混ぜる値の場面。B はここで正解と一致している。
再現(2 回の実行で同じ): 7 観点すべてで A・B とも満点(計 32/32 ずつ)なので、差は無い。
観点ごとに見ると、6 観点(P0-1・P0-2・P0-4・P0-5・P0-6・P0-7)は正しさも再現も同点。差があるのは P0-3 の 1 観点だけで、そこでは B が上回る。B が下回る観点は無い。
補足として、行 A は 54 の設定つき対象から最も良い結果を寄せた行である。p3-bar では寄せた対象のうち 1 件が TypeError で結果なしになり、他の対象の結果で埋めている。また注記には、型が入らなかった升目や、入ったかを決められない升目が多く並ぶ。これに対して行 B は、型が入らなかった升目も決められない升目も「無し」と書かれている。
以上から、差は 1 観点・1 場面と小さいものの、観点を単位に見て B が片方向に優れている。よって B(右)を選ぶ。
- missing_in_choice(逐語): B は表の 32 場面をすべて正解と一致させ、2 回の実行でも同じ結果を出した。表の中に、B が足りない場面は無い。
ただし DEFINITIONS.md の升目の表(第 13 周の後の版)を見ると、場面にしていない升目が大きく残っている。B について未確認なのはこの部分である。
- P0-1: 升目 40 のうち 4 だけ場面にした
- P0-2: 升目 160 のうち 0(時刻の表現は p2-* の 4 場面でしか測っていない)
- P0-3: 升目 40 のうち 13
- P0-4: 升目 40 のうち 2
- P0-5: 升目 40 のうち 4
- P0-6: 升目 40 のうち 1
- P0-7: 升目 160 のうち 3(約定模型・遅延模型・費用・口座を差し替えた組み合わせの大半が未測定)
特に次の場面が足りない。
- P0-2 の升目をひとつも場面にしていない
- P0-7 で、注文の約定の通知が戦略の呼び出しに届く経路を、約定模型・遅延模型・費用と組み合わせた場面
- P0-6 で、戦略が公開の手段で約定の通知を読む升目以外の側面

#### 盲検:0#14:survey2

- choice: 左
- reasons(逐語): 表の各セル(A・B 各 32 場面、計 64 セル)を自分で数え直した結果は次のとおり。grep で「正しさ: 正解と一致」63 件、「正しさ: 対応なし」1 件、「再現: 2 回の実行で同じ」64 件で、表の集計の行と合っている。
観点ごとの正しさ(A / B):
- P0-1: 3/3 対 3/3
- P0-2: 4/4 対 4/4
- P0-3: 11/11 対 10/11。B は p3-mixed-one-run が「対応なし」。6 種の市場の事象を 1 回の実行に混ぜる場面。
- P0-4: 3/3 対 3/3
- P0-5: 3/3 対 3/3
- P0-6: 3/3 対 3/3
- P0-7: 5/5 対 5/5
- 計: A 32/32、B 31/32
再現は全観点で両方とも満点(A 32/32、B 32/32)。差が出たのは P0-3 の 1 場面だけで、ほかの 6 観点はすべて同点。場面の数が多い P0-3 に引きずられないよう観点ごとに比べると、A が上回るのは 1 観点、B が上回る観点は 0。したがって A は、正しさで同等以上かつ一部で上、再現では同等になる。
さらに注記によると、行 B は 54 件の設定つき対象から場面ごとに最良を寄せた行で、1 つの道具・1 つの設定の振る舞いではない。その寄せ集めでも p3-mixed-one-run は正解に届かなかった。多くの設定つき対象には「場面にしたが型が入らなかった升目」があり、多数の場面で結果なしが出ている(例: p2-iso-utc 13 件、p6 16 件、p7-fill-model-swap 18 件)。行 A は実行の前に決めた 1 つの対象で全場面が一致し、型が入らなかった升目も「無し」。このことも A を選ぶ理由になる(推定)。
- missing_in_choice(逐語): 表の結果の範囲では、行 A に足りない場面は無い(32 場面すべてが正解と一致、かつ 2 回の実行で同じ)。表は、「場面にした」とされた升目 27 個に対応する 32 場面しか測っていない。「測っていない(固定した測り方の外)」とされた升目での A の振る舞いは、この表からは分からない。例: P0-3 で、発注・取消の呼び出しがその場で返す物、戦略が公開の手段で読む物(一部を除く)。

### リードの読み(2026-09-25 06:45 UTC)

- 第 14 周は実装の側の [止める] 4(i0-r14-01・02 = i0-r13-01 と同じ根 = 核が呼ぶライブラリのコードと遅れて作る表が ABC・sys.modules を読む / 03 = to_nanos が Fraction・longdouble の桁を落として黙って受け付ける / 04 = numpy.timedelta64 の単位を落として int と数える)・[直す] 1(i0-r14-05 = 入れ子の断りが呼び手の積み上がりで変わる)・場面集の側の [直す] 1(i0-r14-06 = P0-2 の升目が F の文どおり 0 になり測った物が「測っていない」側に置かれる。向きは通過に不利)。
- 審査員は対現状・対調査とも 3 体が新実装の側を選んだ(左右の割り当ては `round_14/materials/mapping.tsv`。current1・survey1 は右 = 新実装が右の表)。連敗の鎖は 0/0 のまま。
- i0-r14-01・02 は作業者の格子(核のソースの grep)の外で、批評家が根本原因を「探し方」に置いている。第 15 周の作業者はこの探し方の穴(核が呼ぶライブラリのコード・実行中の import・遅れて作る表)ごと直す。リードは段の途中で規則を足さない。
- i0-r14-06 は F の文どおりの結果で、場面係が F の範囲で「固定した測り方の外」と「測ったが升目の型を入力が決めない」を分ける形を確かめ、無ければ `lead_answer_changes` で聞く(批評家の指示のとおり)。リードの事前の答え: 分ける形を採ってよい(升目の軸に「事象を持たない変換の場面」「型を対象が選ぶ場面」の行を足す = F が数えない升目を「場面にした」に足すのではなく、測った物を別の欄に出す)。

## 第 15 周(進行中。07:42 UTC の見回りで写した分)

| 段 | 開始 | 終了 |
|---|---|---|
| 作る:0#15 | 05:59:31 | (進行中、07:38:58 に書き込みあり) |
| 場面の直し:0#r15-1 | 05:59:31 | 06:45:26 |
| 監査役(場面):0#r15-1 | 06:45:29 | 06:57:17 |

### 場面係 r15-1 の返り値(逐語)

- definitions: /home/user/trade/tests/bt/battery/item_0/DEFINITIONS.md(gen_definitions.py から作り直した。--check は OK。升目の判断は F と §8.2 の 1 のとおり 2 値のまま。観点ごとの見出しに「升目に当たらない場面 N」を足し、見出しの下に grid_c.unplaced の一覧を出す。一覧は升目に当たらない場面を入力から機械で区分する。P0-2 は p2-iso-utc・p2-iso-offset が「事象を持たない」、p2-event-time-exact・p2-one-ns-apart が「事象の型を入力が決めない」。同じ種類の欠陥として P0-6 の p6-place-then-cancel と P0-7 の p7-account-swap も出る(区分は「入力から型は出るが、その型の升目を宣言していない」)。このほか、br13-1-2 の requests の記録の数(相手: 記録しない 37・設定つき対象 41、再現: 記録しない 1・設定つき対象 13)を節の注記に機械で出す)
- runner: /home/user/trade/tests/bt/battery/item_0/run_battery.py(変えていない。場面の定義 32 件の全部の欄と input_types・covers_of の値が HEAD と同じことを確かめた: /tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/r15-1/item0_r15-1_scenekeeper_same_scenes.txt。よって比較の表のセルと正解は変わらない)
- mutant: PYTHONPATH=src python3 tests/bt/battery/item_0/mutant.py --check → changed scenes: ['p4-received-time'] / OK。主張の表の mutant(test_battery_r15_unplaced.py): unplaced に 5 種、input_events に 2 種、一覧を出さない 1 種、request_recording に 3 種で、どれも捕まる。test_battery_r13_claim_mutants.py には「対象自身の形の型を渡した約定と数える」を足し、足した tick の場合だけで捕まることを示した
- survey_run: ["この回は相手を走らせ直していない。runner・adapter・opponents・場面の定義は変えていない(HEAD と同じことを確かめた)。survey_results/ は第 r13-1 回のまま(54 本、全部 32 場面)"]
- rootcause: `/home/user/trade/tests/bt/battery/item_0/ROOTCAUSE_r15-1.md` / check_output: `OK 誤り 0 件` / lead_answer_changes: []

### 監査役(場面) r15-1 の出力(逐語)

- **br15-1-1** [聞く](repeat_of: i0-r14-06)
  tests/bt/battery/item_0/DEFINITIONS.md:171 — 第 r15-1 回の直し後も P0-2 の見出しは「場面にした 0 / 測っていない(固定した測り方の外) 160 / 升目に当たらない場面 4」のままで、升目の判断(0)自体は変わっていない(ROOTCAUSE_r15-1.md §5.2 の 1 で場面係自身が『升目の単位では分けられなかった』『(i)(ii)(iii)のどれかをリードが決める必要がある』『この回は(iii)の形で直し、(i)(ii)は作っていない』と明記)。追加された『升目に当たらない場面』一覧はヘッダの直下にあるが、ヘッダの数字(場面にした 0)だけを読む読者には、i0-r14-06 が問題にした『P0-2 は 1 つも測られていないと読める』という誤読可能性が形の上では残る。この一覧の追加で当該の誤読リスクは実務上十分に解消されたとリードは判断しているか、それとも(i)(ii)の案(升目単位での値の分離)への追加の答えを別途出す予定か(P-xx: research-protocol §0.2 なぜの欠落と同族、P2 に近い可読性の論点)。
- **br15-1-2** [聞く](repeat_of: None)
  docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/round_7/LEAD_DESIGN.md §9.2 の 34・ROOTCAUSE_r15-1.md §6(『場面の定義(32 場面の全部の欄)と input_types・covers_of の値は HEAD と同じ』)— この回の直しは升目の判断機構(covers_of・table)そのものを変えず、『升目に当たらない場面』という新しい観点(annotation)を追加しただけであることを場面係自身が明記している。この設計(F を書き換えず、読み手向けの注記だけを足す)は、批評家 i0-r11-02 の神託(`test_i0r11_covers_within_scene_input.py`)を変えずに通すという制約の下では機械的に妥当だが、P0-6・P0-7 の軸の見直し(読む物・見る道を升目の軸に足すか)という根本的な論点(§5.2 の 2)は、この回でも前回(r13-1 §8.2 の 6)でも未着手のまま持ち越されている。この論点の扱い(軸の見直しをリードが検討する予定か、それとも当面は一覧での注記のみで運用する方針を確定するか)を明示的に決める時期はいつか。

### リードの答え(2026-09-25 07:45 UTC。段の途中で規則は足さない。次の起動の lead_notes に写す)

- br15-1-1 [聞く]: リードの答え = **(iii) の形(升目の判断は変えず、観点ごとに「升目に当たらない場面」の一覧を機械で出す)を当面採る。**(i)(ii)(升目の単位で値を分ける)は今は作らない。理由: F の「場面にした」は入力から機械で出る型だけで決める(監査 52〜56 回目を通した定義)ので、升目の数を動かす形は F を変えることになり、それは枠組みの変更に近い。誤読の防ぎ方は表の側で: 通過の報告と升目の表の見出しには「場面にした N / 升目に当たらない場面 M(一覧)」を必ず並べて出し、見出しの数字だけを切り出さない。これで足りるかは批評家が第 15 周に読む(i0-r14-06 の repeat)。
- br15-1-2 [聞く]: リードの答え = **決める時期は、項目 0 の通過の報告のあと、場面集の並行の直し(batteryFollowUp)の最初の周。**P0-6・P0-7 の軸(読む物・見る道)の見直しは、項目 1〜12 の格子(`LEAD_DESIGN_items_1-12.md` の共通の設計)が同じ F を継ぐので、そこで一度に決める。それまでは一覧の注記だけで運用する(方針を確定)。今の周では決めない(段の途中で規則を足さない)。

### 第 15 周の残りの段(08:44 UTC の見回りで写した)

| 段 | 開始 | 終了 |
|---|---|---|
| 作る:0#15 | 05:59:31 | 07:48:08 |
| 表:0#15 | 07:48:10 | 08:16:43 |
| 批評:0#15 | 08:16:44 | 08:40:34 |
| 盲検:0#15:current0〜2 | 08:40:36 | 08:41:06 |
| 盲検:0#15:survey0〜2 | 08:40:55 | 08:41:52 |
| 作る:0#16 / 場面の直し:0#r16-1 | 08:41:53 | (進行中) |

### 作業者 0#15 の返り値(逐語)

- `structural_change`: 核が作る値は、等しさと hash を核自身のコードか組み込みの型の C のコードで持つ形にしました(Fraction と Decimal は核の子の型 PlainFraction / PlainDecimal として作る。等しさは正確な値を比べ、Decimal は核の十進の文脈で比べる)。数の変換は「正確に変換できなければ断る」にし、単位を持つ numpy の型(timedelta64 / datetime64)は数と数えません。copier / rebuilder は読み込み時に全部作って、実行中には import も表の書き足しもしません。平らな値の歩きは反復にし、段数によらず決まった枠数で済むようにしました。
- `tests_added`: 1120 / `test_tail`: 項目 0・批評家の試験(最後の版): 「3080 passed, 2 skipped, 1 warning in 428.64s (0:07:08)」(飛ばした 2 件は前からあるもの)。全試験(場面集を含む): 「6199 passed, 6 skipped, 2 warnings in 950.89s (0:15:50)」。その後に変えたのは試験のファイル 1 本(格子 A の表に enum の 3 行を足した)だけで、その試験は「1120 passed, 1 warning in 10.66s」。第 14 周の批評家の試験 3 本: 直す前「17 failed, 12 passed in 1.18s」→ 直した後、第 13 周の 1 本と第 11 周の 3 本を合わせて「59 passed in 3.76s」。新しい格子: 直す前「167 failed, 942 passed」→ 直した後、第 14 周の格子と合わせて「1213 passed」。一時ファイルとログ: /tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/r15_worker/(pytest_item0_r15_worker_*.log)。
- `changed_files`: ["src/bot/bt/core/values.py(PlainFraction / PlainDecimal と核の等しさ _number_equal、exact_context、単位を持つ numpy の型を数と数えない UNIT_CLASSES、正確な変換 _exactly_converted、反復の歩き _walk と freeze / settle / renew / thaw、FrozenDict の hash を作るときに組を比べずに計算、読み込み時に作る copier / rebuilder の表 bind_carriers、CALL_FRAMES、送り手の入れ物で別々だった鍵がまとまる場合を断る)", "src/bot/bt/core/time.py(to_nanos: Fraction は int の演算で正確に、十進の演算は全部核の文脈で)", "src/bot/bt/core/contract.py(process_state と channel_payloads.rule の文、bind_carriers(PATH_CARRIERS) を読み込み時に 1 回、版 core-16)", "src/bot/bt/core/__init__.py(PlainFraction / PlainDecimal を公開)", "tests/bt/item_0/test_bt0_r15_library_code.py(新規。格子 A・B・B'・C・D と等しさの神託、1120 件)", "tests/bt/item_0/_r15_workload.py(新規。核の全ての入口を通す作業量)", "tests/bt/item_0/_r15_state_child.py(新規。1 つの状態の変更を新しいプロセスで当てる子)", "tests/bt/item_0/test_bt0_r14_process_state.py(書き直し: 契約の版 core-16、格子 2 で数と数えない numpy の単位の型がちょうど timedelta64 と datetime64 であることを確かめる)", "tests/bt/item_0/_r14_state_child.py(書き直し: 格子 2 の比較から単位を持つ型を外して列べて返す)", "tests/bt/item_0/test_bt0_r8_sender_adversary.py(書き直し: 核が作る型の表の Fraction / Decimal を PlainFraction / PlainDecimal に替えた。核がもう作らない型を外したので弱めていない)", "tests/bt/item_0/test_bt0_values.py(書き直し: 同じく型の表)", "docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/round_15/ROOTCAUSE.md(新規。直す前に書いた根本原因と構造、直した後の確かめ)"]
- `unmet`:
  - 満たせなかった要件の行: 無し。以下は委任文 §3「提出前の吟味」の記録。<W> = /tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/r15_worker。
  - (1) i0-r14-01([止める]、実装、repeat_of i0-r13-01)。直した根拠: values.py:357 PlainFraction、:369 PlainDecimal、:307 _number_equal、:282 _decimal_equal、:343 _fraction_hash、:163 exact_context、:1215 _pairs_hash、:1286 _fd_fill。確かめ: tests/bt/critic/item_0/test_i0r14_process_state_through_library_code.py は直す前 4 件とも落ち、直した後は通る(上の 59 passed の中)。格子 B(test_bt0_r15_library_code.py:260)は、numbers の ABC に対する登録とフックの 8 通りが直す前に落ち、直した後は 86 通り全部が通る。十進の旗の試験(同じファイル :268)も、直す前は核の比較が FloatOperation の旗を立てて落ち、直した後は通る。
  - (1) i0-r14-02([止める]、実装、repeat_of i0-r13-01)。直した根拠: values.py:1441 bind_carriers、:1438 _CARRIER_TABLES、:1451 copy_carrier、:1480 rebuild_carrier。contract.py:28 で bind_carriers(PATH_CARRIERS) を 1 回呼ぶ。dataclasses はモジュールの先頭で import する。確かめ: 批評家の試験 test_a_module_swapped_in_sys_modules_… が通る。格子 B では、核が import する 18 のモジュール(AST から機械で列べた)の差し替えが全部変化 0。格子 B'(:274 関数の中の import が 0 件、:333 作業量の前後で核のモジュールの状態が同じ)は、直す前は 2 件とも落ちていた。
  - (1) i0-r14-03([止める]、実装、repeat_of null)。直した根拠: time.py:143 to_nanos(:174 で PlainFraction を int の演算で扱い、十進の演算は :191-201 で核の文脈の compare / quantize / to_sci_string を使う)、values.py:576 _exactly_converted、:755 _now。確かめ: 批評家の test_to_nanos_is_exact_or_refuses 4 件が通る。格子 C の to_nanos(:507、numpy の全ての数の型と Python の型 × 4 単位)は、直す前に 58 件落ち、直した後は全部通る。
  - (1) i0-r14-04([止める]、実装、repeat_of null)。直した根拠: values.py:536 UNIT_CLASSES、:548 number_kind。確かめ: 批評家の 6 件が通る。格子 C の validate_nanos(:517)、遅延(:566)、平らな値(:470)も、timedelta64 の全ての単位と datetime64 を断る。
  - (1) i0-r14-05([直す]、実装、repeat_of i0-r13-01)。直した根拠: values.py:886 _walk(明示の積み上げの反復)、:1298 freeze、:842 settle、:1396 renew、:1356 thaw、:649 CALL_FRAMES。確かめ: 批評家の 15 件が通る。格子 D(:686)は直す前に 30 件落ち、直した後は全部通る。実測(<W>/item0_r15_worker_probe_headroom.out): 入口が要る枠は最大 22 で、入れ子の段数によらない。
  - (1) i0-r11-01・03([直す]): この周は構造を変えていない。第 11 周の試験 3 本は上の 59 passed の中にある。
  - (2) 同じ根の全箇所。探し方を「核のソースの grep」から「実行して走ったものを列べる」に替えた。項目 0 と批評家の試験の全部を sys.setprofile の下で走らせ、核の代わりに入ったライブラリのコードを列べた(直す前 <W>/item0_r15_worker_profile_runtime_before.tsv、直した後 …_after.tsv)。直した後に残る fractions のコードは Fraction.__hash__ の 5 回だけで、出所は試験のコードが自分の呼び出しの中で公開の FrozenDict(...) を作った所(<W>/item0_r15_worker_sites.tsv)。この列べを格子 A(:196)として毎回の pytest で確かめ、表に無いコードを核が呼ぶようになれば落ちる。作業中に同じ族を 2 つ見つけて直した。(a) 核が作った Decimal の str / repr / f"{}" が、スレッドの文脈の capitals を読んでいた(:744 の試験)。(b) 送り手の dict / 集合では別々だった鍵が、核が作り直すと等しくなる場合に、黙って 1 つにまとめていた(values.py:941 _dict_of・:952 _set_of、:732 の試験 9 件)。
  - (3) 批評家の試験と場面集の試験を全部回し、落ちるものは無い(全試験 6199 passed)。規則 8(批評家の試験自身の誤り)に当たるものは無い。
  - (4) 厳しい批評家が [止める] にしそうな点と処置は ROOTCAUSE.md の §7・§7' に書いた。要点は 4 つ。1 つ目: Plain 型と「組み込みの型そのもの」の文との食い違いは、契約 contract.py:229 と PLAIN_DATA_RULE に書いて閉じた。2 つ目: 核の等しさが Python の等しさと同じことは :356 で確かめた(15 の値 × 36 の相手 × 両向き・!=・hash)。3 つ目: 大きな指数の Decimal でも比較は止まらない。4 つ目: RecursionError を捕まえるのは、インタプリタの比較の残りだけに限った。
  - (5) 場当たりの直しはしていない。試験だけを特別扱いした所・閾値や既定値をずらした所・文言だけ合わせた所・機能を外した所は無い。前の周までの自分の試験 4 本の書き直しは、型の表を新しい規則に合わせたものだけで、消した試験は無い。
  - (6) 直した規則ごとに、全格子の敵対者の試験を先に書き、直す前に正しい理由で落ちることを確かめた(直す前 167 failed。落ち方は <W>/pytest_item0_r15_worker_prefix.log)。そのあとで直した。列に入れなかったもの(核が呼ぶ名前の付け替え、解釈系のフック、低い再帰の上限、signaling NaN を Python が比べる場合、numbers / collections.abc 以外の ABC、-b で起動したインタプリタ)は、試験のファイルの説明に書いた。試験自身の誤りを作業中に 3 つ直した。1 つ目: 新しいプロセスの実行の鍵の数の数え方。2 つ目: numpy の bool を is で比べていた。3 つ目: 時刻の神託が int64 の範囲を検めていなかった。3 つとも核に合わせた直しではなく、神託を値から出す直し。
- `questions_for_lead`:
  - 振る舞いの変化が 4 つあります(契約 core-16 と PLAIN_DATA_RULE に書きました)。(1) extra の中の Fraction / Decimal は、読み戻すと核の子の型 PlainFraction / PlainDecimal になります。isinstance(v, Fraction) は真のままで、演算の結果はライブラリの型です。type(v) is Fraction は偽になります。(2) numpy の timedelta64 / datetime64 は、どの入口でも断ります。(3) float / complex に正確に入らない numpy の longdouble / clongdouble の値は断ります。(4) 送り手の dict / 集合では別々だった鍵が平らな値として等しくなる場合も断ります(以前は黙って 1 つにまとめていた)。項目 11・13 は契約を読む前提で足りるか、別に知らせる必要があるかを決めてください。
  - 残りを 1 つ契約に書きました。hash の等しい別々の入れ子の値(例: 98 段の (((-1,),…) と (((-2,),…))が同じ集合・辞書に入ると、インタプリタ自身の比較が、入れ物 1 段ごとに再帰の上限を 1 つ使います。実測では 98 段で 106 枠でした。残りの枠が足りないときは、RecursionError ではなく入口の誤りで断ります。受け付けるかどうかが呼び手の深さで変わる形は、この場合だけ残ります。完全に閉じる案は、extra の tuple / frozenset を「平らな鍵で比べる核の class」にすることです。ただし extra の中の tuple / frozenset の型が変わるので、この周は作っていません。進めるかを決めてください。
  - MAX_NESTING = 100 の根拠が変わりました。第 14 周の根拠は「再帰の歩きが 1 段 3 枠」でしたが、この周に歩きを反復にしました。今の上限は、インタプリタ自身が 1 つの値に対して行う再帰(上の比較、repr)を抑える物として残しています。値 100 のままでよいかを確かめたいです。CALL_FRAMES = 30 も、この周に置いた値です(実測の最大 22 に余裕を足した)。

### 表 0#15 の `notes`(逐語)

資料係(表)として提出前に確かめたこと:

(1) 観点ごとの一致の数
- 数え直しの方法: 数は 2 つのスクリプトで数え直した。recount.py は runs/*.tsv から make_tables.py を使わずに数え、6 枚の数の行と突き合わせた(不一致 0)。recount_cells.py は各観点の節のセルを数え、数の行と突き合わせた(不一致 0)。logs/count_rows.out の行も自分で読み、下の数と合っていることを確かめた。
- 新実装: 全 7 観点で「正解と一致」が満点(P0-1 3/3、P0-2 4/4、P0-3 11/11、P0-4 3/3、P0-5 3/3、P0-6 3/3、P0-7 5/5、計 32/32)。
- 当方の現状: P0-1 1/3、P0-2 2/4、P0-3 1/11、P0-4 1/3、P0-5 1/3、P0-6 0/3、P0-7 2/5、計 8/32。
- 調査結果の側: P0-3 だけ 10/11 で、ほかの観点は満点。計 31/32。
- 試金石: P0-4 だけ 2/3 で、ほかの観点は満点。計 31/32。
- 「2 回の実行で同じ」は 4 つの対象とも全観点で満点(32/32)。

(2) 全対象を全場面に通したか
- 新実装・当方の現状・調査結果の側の設定つき対象 54 件・試金石の計 57 対象を、全 32 場面に 2 回通した。全部 rc=0 で、時間の打ち切りは 0 件。
- 結果なしになった場面には、表の注記に試したことと出たもの(例外の型、または機構が無い旨)と実測の所要秒数を書いた。
- 表に「未記録」は 0 件。

(3) 注記に道具を特定できる語が無いか
- 道具の名前の語の型(175 語)で表を検索した。当たったのは調査結果の側の 2 枚の「書き直」2 件だけで、これは一般の語。
- 時刻の形(hh:mm)は 6 枚とも 0 件。
- 道具の名前・時刻・結果なしの対象は materials/commands.txt、survey_failures.tsv、survey_best.tsv、not_entered.tsv にだけ書いた。
- check_notes.py の結果: 漏れ 0、grid_c の出力との違い 0。

(4) md5
- 組ごとの 2 通りの表は 3 組とも違った(md5sum_pairs.txt)。どの組も L-422 の「同等」には当たらない。
- 第 2 回の実行から作った表(pass2_tables)は、6 枚とも第 1 回の表とバイト単位で同じ。
- pass2_tables_ownlog では、調査結果の側の 2 枚だけが注記の所要秒数で違う。

(5) 相手の道具の結果の再利用はしていない
- 場面集の指紋が第 14 周の dff3bc73… から cb42e201… に変わった。変わったファイルは ROOTCAUSE_r15-1.md、DEFINITIONS.md、scenes.py などで、git diff --stat d92658e HEAD で確かめた。
- そのため前の周の結果は使わず、全部走らせ直した。
- 走らせたあとも指紋は cb42e201… のままで、src/bot/bt と tests/bt に変更は無い(logs/final_state.txt)。

(6) 第 14 周の表との比べ(logs/diff_vs_round14_tables.out)
- 6 枚とも、題の周の番号と注記の所要秒数のほかは第 14 周の同じ表 id の表と同じ。
- 場面係の確かめ(場面の定義が HEAD と同じ)の写しは logs/scenekeeper_same_scenes_copy.txt に置いた。

(7) 第 1 回と第 2 回の違い
- 出力の値の欄だけが 3 対象の各 1 場面で違った。正しさと再現の欄は 2 回とも同じ。
- どれも表のセルには出ない(第 13 周と同じ具体。commands.txt に記録)。

(8) 試金石
- mutant.py --check の結果: changed scenes: ['p4-received-time'] / OK。
- 主張の表の mutant の試験(test_battery_r15_unplaced.py と test_battery_r13_claim_mutants.py)は battery の pytest に含まれ、218 件すべて通った。

(9) adapter と保存先
- 新実装の adapter(tests/bt/battery/item_0/adapters/new_impl.py)は既にあったので変えていない。変えると場面集の指紋が変わるため。公開された口だけを呼んでいることは check_new_impl_names.py で確かめた。
- 記録はすべて /home/user/trade/docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/round_15/materials/ に保存した。対応表は 対応表.md と mapping.tsv。
- 実データから出た数値は入れていない。git commit はしていない。

### 批評家 0#15 の出力(逐語)

- **i0-r15-01** [止める](target: 実装, repeat_of: i0-r14-03, fix_files: ['src/bot/bt/core/time.py'])
  to_nanos は float を最短の十進表記(time.py 184 行 float.__repr__)で読むので、float が正確に持つ時刻を、表記の桁数に丸めた値に黙って替える。第 15 周に直した longdouble の道も、float が正確に持てると確かめた(values._exactly_converted)あとで同じ所を通る。to_nanos(1700000000123456.75, 'us') は 1700000000123456800 を返す(float はこの値を正確に持つので、値が言うのは 1700000000123456750 ns。50 ns ずれ、断りは出ない)。float が正確に持つ整数 2816833943301389824.0 を 'ns' で渡すと 2816833943301390000(+176 ns)。numpy の float64・longdouble も同じ。time.py 8 行「Conversion is exact」、70 行 rounding: none、docstring「convert without binary-float rounding … rejected instead of being rounded silently」「a numpy longdouble only when a float holds its value exactly (else refused, never rounded)」に反する。最短表記は 17 桁以下への十進の丸めである。要件 §1「時刻は UTC の int64 ナノ秒」と観点 P0-2 の値の測り方に対し、核の唯一の変換口が黙って違う時刻を返すので「黙って誤った値」で [止める]。第 14 周の批評家はこの読み方を約束として残したが、float が正確に持つ整数ナノ秒を別の値にするのは、どの読み方(入力の文字・float の値)でも正解にならないので付け直した。根本原因: 作業者の格子の神託が、float の「値が言うナノ秒」を最短表記の十進として置いていた(ROOTCAUSE §4)。i0-r14-03 と同じ「値を狭めてから読む」族。直し方の向き: float を as_integer_ratio(正確な値)で読み、ナノ秒より細かい桁があれば断る(作業者の申告の規則「正確に変換できなければ断る」)。受け付け方が変わるので契約の文も直す。前からある振る舞い(第 14 周の核でも同じ出力)。
  証拠: PYTHONPATH=src python3 <S>/r15_critic/item0_r15_critic_probe_float_shortest_repr.py → 'float(1700000000123456.8) unit=us: holds 1700000000123456750 ns (whole: True) | to_nanos -> 1700000000123456800  <-- off by 50 ns' / 'float(2.81683394330139e+18) unit=ns: holds 2816833943301389824 ns (whole: True) | to_nanos -> 2816833943301390000  <-- off by 176 ns' / 'longdouble(1700000000123456.8) unit=us: … off by 50 ns'。格子 <S>/r15_critic/item0_r15_critic_probe_to_nanos_grid.py(種 15、7,800 件)→ 契約どおりの longdouble の断り 297 件を除き、黙って違う値 1 件 "('longdouble(value it holds)', 'ns', 'gave 2816833943301390000, the value states 2816833943301389824')"。第 14 周の核(git archive 563661d)でも同じ出力。試験(残す): PYTHONPATH=src python -m pytest tests/bt/critic/item_0/test_i0r15_float_time_rounded_by_shortest_repr.py -p no:cacheprovider → '6 failed, 3 passed'('to_nanos(float(1700000000123456.75), 'us') gave 1700000000123456800, the value holds 1700000000123456750 (+50 ns)' ほか)。<S> = /tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt
- **i0-r15-05** [止める](target: 場面集, repeat_of: None, fix_files: ['tests/bt/battery/item_0/scenes.py', 'tests/bt/battery/item_0/adapters/new_impl.py', 'tests/bt/battery/item_0/run_battery.py', 'tests/bt/battery/item_0/gen_definitions.py'])
  観点 P0-2 の文は「全事象の時刻が UTC 起点の int64 ナノ秒で表現され、他の単位(秒・ミリ・ISO 文字列)が核の内部表現に混入しないこと」と単位を名指す(REQUIREMENTS.md 18 行)。場面集の P0-2 は ISO の 2 場面(p2-iso-utc・p2-iso-offset)と int ナノ秒の 2 場面(p2-event-time-exact・p2-one-ns-apart)だけで、秒・ミリ(とマイクロ秒)の値を入れる場面が 1 つも無い。DEFINITIONS.md 96 行の観点の要約も「時刻が UTC の int64 ナノ秒で表されること」で、「他の単位が混入しない」を落としている。升目の表は秒・ミリの升目を「測っていない」と記録しており隠してはいないが、盲検で比べる表に P0-2 の秒・ミリの変換が 1 セルも無く、観点の文が名指す部分を比べていない。現にこの周の i0-r15-01(float の秒・マイクロ秒の時刻が黙って丸められる)はこの穴の中にあり、場面集では見えない。第 14 周の批評家は Fraction・longdouble・timedelta64 の入力の形を [示唆] としたが、秒・ミリは観点の文そのものが名指す単位なので、場面集が観点を覆っているかの問題として付け直した。規則 3(各観点に値の場面 1 つ以上)は満たしている。「場面集が要件の観点を全部覆っているか」を満たさないので [止める](委任文 §3「迷ったら重い方」)。場面集の側なので項目 0 の通過は止めず並行の直し(L-441)に入る。直し方の向き: 既知の時刻を秒・ミリ・マイクロ秒で、文字列と float(float が正確に持つ値と持たない値の両方)で入れ、対象自身の変換で int ナノ秒にした値を手計算の正解と照らす値の場面。
  証拠: grep -n '"p2-' tests/bt/battery/item_0/scenes.py → 275・283・289・296 行の 4 場面だけ(p2-iso-utc / p2-iso-offset / p2-event-time-exact / p2-one-ns-apart)。docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/REQUIREMENTS.md 18 行(P0-2 の文が「秒・ミリ・ISO 文字列」を名指す)。tests/bt/battery/item_0/DEFINITIONS.md 96 行(観点の要約)・171-180 行(P0-2 の見出しと一覧)。
- **i0-r15-02** [直す](target: 実装, repeat_of: i0-r14-05, fix_files: ['src/bot/bt/core/values.py'])
  送り手が signaling NaN の Decimal を辞書の鍵・集合の要素に持つと(送り手自身の Decimal の子が hash を持てば作れる)、核はそれを基の型で読んで PlainDecimal('sNaN') を作り、自分の辞書・集合を作るとき(values.py 946 行 _dict_of の d[k] = x、953 行 _set_of)に Decimal の C の hash が組み込みの TypeError('Cannot hash a signaling NaN value') を出す。_walk が捕まえるのは RecursionError だけ(927 行)なので、そのまま出る。values.freeze / settle → TypeError(ValueError / Unsettled でない)。戦略の place_order(on_event の中)→ TypeError(OrderApiError でない)。出口の箱に書いた注文(on_event が返ったあとの _take_message の settle)→ 実行が TypeError で FAILED(OrderApiError でない)。口座の強制注文の道だけは AccountSocketError になる。契約 type_decisions(contract.py 304-305 行)と scope(132 行)の「a refusal is always the entry's own error」に反する。黙って誤った値は無く、断りの型だけが違うので、前の周の同じ格(i0-r11-01・i0-r14-05)に合わせて [直す]。族は i0-r14-05(核が入れ物を作るときにインタプリタが出す例外を、歩きが入口の誤りに替えない。第 15 周の直しは RecursionError だけを替えた)。第 13・14 周の核でも同じ(前からある振る舞い)。
  証拠: PYTHONPATH=src python3 <S>/r15_critic/item0_r15_critic_probe_snan_keys.py → 'dict key freeze: builtins.TypeError: Cannot hash a signaling NaN value' / 'set element in a tuple settle: builtins.TypeError: …' / 'place_order raised inside on_event: TypeError Cannot hash a signaling NaN value'。試験(残す): PYTHONPATH=src python -m pytest tests/bt/critic/item_0/test_i0r15_unhashable_key_refusal_type.py -p no:cacheprovider → '20 failed, 5 passed'(freeze 5・settle 5・place_order 5・出口の箱 5 が落ち、口座 5 が通る。'an outbox message with an sNaN dict-key: the engine failed with TypeError' ほか)。第 13 周(e13fec6)・第 14 周(563661d)の核で同じ試験 → どちらも '20 failed, 5 passed'。<S> = /tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt
- **i0-r15-03** [直す](target: 実装, repeat_of: i0-r14-05, fix_files: ['src/bot/bt/core/contract.py', 'src/bot/bt/core/values.py'])
  契約 process_state(contract.py 180-181 行)と values.py 635 行・933 行は「hash の等しい別々の入れ子の値を比べるとき、インタプリタは入れ物 1 つに再帰の上限を 1 つ使う(測った: 98 段で 106 枠)」と書く。入れ子の FrozenDict の鍵では、比べるのが核自身の FrozenDict.__eq__(1262・1271 行: Python の method が dict を 2 つ作って比べる)なので、1 段に約 3 枠を使う。衝突する入れ子の鍵 2 つの freeze が要る枠は、tuple は 10 段 16・50 段 56・97 段 103(契約どおり)、FrozenDict は 10 段 34・30 段 94・48 段 148(98 段なら約 300 枠、契約の 106 の約 3 倍)。断りの型は入口の誤り(ValueError)のままで、黙って誤った値は無く、契約の事実の文が核の型で違う。受け付け・断り・値は変わらないので [直す]。族は i0-r14-05(入れ子の断りが呼び手の積み上がりで決まる範囲の文)。直し方: 契約と注釈の文を事実に合わせるか、FrozenDict の比べを枠を積まない形にする。
  証拠: PYTHONPATH=src python3 <S>/r15_critic/item0_r15_critic_probe_headroom.py → 'freeze(dict with 2 colliding tuple keys, 97 levels): 103 (one less -> ValueError)' / 'freeze(dict with 2 colliding FrozenDict keys, 10 levels): 34' / '… 30 levels): 94' / '… 48 levels): 148 (one less -> ValueError)'。試験(残す): PYTHONPATH=src python -m pytest tests/bt/critic/item_0/test_i0r15_colliding_frozendict_frames.py -p no:cacheprovider → 2 回とも '2 failed, 4 passed'('two colliding 30-level FrozenDict keys need 99 frames of headroom; the contract allows one per container of the two: 90' / '48-level … need 153 … : 126')。上限は契約を最も甘く読んだ 2 × 段数 + CALL_FRAMES。<S> = /tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt
- **i0-r15-04** [直す](target: 実装, repeat_of: i0-r14-03, fix_files: ['src/bot/bt/core/values.py', 'src/bot/bt/core/contract.py'])
  作業者は「数の変換は正確に変換できなければ断る」にしたと申告し、values._now(755 行)の説明も「Convert a foreign number once, now, EXACTLY」と書くが、float の欄(as_float 1160 行、take_float 1058 行)は int を _now(float, int) で float にし、int は _exactly_converted の検めを素通りするので丸めて受け付ける。同じ値でも numpy の longdouble なら断る。2**53+1 を価格・手数料に: int・numpy int64・Fraction → 9007199254740992.0(黙って丸める)、numpy longdouble → 断る。Fraction(1,3) → 0.3333333333333333、np.longdouble(1)/np.longdouble(3) → 断る。float の欄は float と宣言されているので、丸めること自体は欄の意味の中と読める。問題は規則が型で分かれること(同じ値が受け付けて丸めると断るに分かれる)と、_now の説明と作業者の申告が事実と違うこと。要件の値の場面を外れないので [直す]。族は i0-r14-03(変換の結果を値と照らさない)。直し方: float の欄の規則を 1 つに決める(全ての型を最も近い float に丸めると書き longdouble も受け付けるか、全ての型で正確でなければ断るか)。
  証拠: PYTHONPATH=src python3 <S>/r15_critic/item0_r15_critic_probe_float_field_exactness.py → 'int as_float: 9007199254740992.0' / 'numpy int64 take_float: 9007199254740992.0' / 'Fraction take_float: 9007199254740992.0' / 'numpy longdouble as_float: refused (ValueError: price holds a numpy.longdouble whose value a float cannot hold exactly)' / 'values._now docstring first line: Convert a foreign number once, now, EXACTLY, and build what the'。<S> = /tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt
- **i0-r15-06** [直す](target: 場面集, repeat_of: i0-r14-06, fix_files: ['tests/bt/battery/item_0/grid_c.py', 'tests/bt/battery/item_0/gen_definitions.py'])
  第 r15-1 回の直しで P0-2 の見出しに「升目に当たらない場面 4」と一覧が並び、「P0-2 が 1 つも測られていない」という誤読は防げている(リードの答え br15-1-1 の (iii) の形。足りるかを批評家が読む)。残るのは、P0-2 の 160 升目の判断の欄が全部「測っていない(固定した測り方の外)」のままで、括弧の中の理由が事実と違う点。P0-2 の固定した測り方は「既知の時刻…を投入し、核が保持する値が同じ int64 ナノ秒と一致するか」で、一覧の 4 場面はまさにその測り方で ISO と int ナノ秒を測っている(一覧の説明文自身も「一覧の場面はその観点を測っている」と書く、DEFINITIONS.md 111 行)。秒・ミリの升目も、測っていないのは場面が無いから(i0-r15-05)で、測り方の外だからではない。同じ表の中で判断の欄と一覧の説明が食い違う。向きは通過に不利で、場面・正解・比較の表のセルは変わらないので [直す]。F を変えずに直せる: 判断の値は 2 値のまま、升目に当たらない場面がその観点にあるときは括弧の文を機械で別の文にするか、括弧を外す。
  証拠: sed -n 171,185p tests/bt/battery/item_0/DEFINITIONS.md → '### P0-2(升目 160: 場面にした 0 / 測っていない(固定した測り方の外) 160 / 升目に当たらない場面 4)' と '| 約定 | 戦略の呼び出しに届く物 | int64 ナノ秒 | 測っていない(固定した測り方の外) | — |'。同ファイル 111 行の一覧の説明。docs/AUDITOR/VERDICTS/2026-09-23_backtest_env_run11_item0.md の第 15 周のリードの答え br15-1-1。
- **i0-r15-07** [示唆](target: 実装, repeat_of: None, fix_files: ['src/bot/bt/core/time.py'])
  to_nanos(np.longdouble('1700000000.123456789'), 's') の断りの文は「timestamp value for unit 's' must be int, float, Decimal, Fraction or numeric str, got numpy.longdouble」で、float が正確に持てる longdouble は受け付けるのに、型そのものを断ったように読める(to_nanos が values.scalar の ValueError を捨てて一般の文を出している)。scalar が出した理由(a float cannot hold exactly)を断りの文に残すとよい。
  証拠: PYTHONPATH=src python3 <S>/r14_critic/item0_r14_critic_probe_to_nanos_exact.py → 'bot.bt.core.errors.TimestampUnitError: timestamp value for unit 's' must be int, float, Decimal, Fraction or numeric str, got numpy.longdouble'(<S>/r15_critic/item0_r15_critic_recheck_r14_probes.out の == to_nanos_exact の節)。<S> = /tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt

`structural_change_since_prev`: True。記録: `/home/user/trade/docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/round_15/CRITIC.md`。

### 審査員 0#15(構造の変化ありのため 6 体が起きた。逐語。左右の割り当ては `round_15/materials/mapping.tsv` と台本の `v = (k + attempt) % 2 === 0 ? 1 : 2`: k=0,2 は表 2(A = 当方の現状 / 調査結果、B = 新実装)、k=1 は表 1(A = 新実装))

#### 盲検:0#15:current0

- choice: 右
- reasons(逐語): 表の各セルを数え直した結果、表の集計と一致した。
正しさ(正解と一致の数):
- P0-1: A 1/3(p1-one-call-per-event のみ。merge-by-time・typed-events は対応なし)/ B 3/3
- P0-2: A 2/4(event-time-exact・one-ns-apart。iso-utc・iso-offset は対応なし)/ B 4/4
- P0-3: A 1/11(p3-bar のみ。残り 10 件は対応なし)/ B 11/11
- P0-4: A 1/3(visible-at-step。received-time は対応なし、future-read-attempt は不一致 {"every_attempt_stopped_by_error": false, "future_value_obtained": false})/ B 3/3
- P0-5: A 1/3(same-stream-order のみ)/ B 3/3
- P0-6: A 0/3(3 件すべて対応なし)/ B 3/3
- P0-7: A 2/5(fill-model-swap・cost-model-swap。latency-model-swap・cost-per-unit・account-swap は対応なし)/ B 5/5
- 計: A 8/32、B 32/32
再現(2 回の実行で同じ): 7 つの観点すべてで A・B とも全件一致(A 32/32、B 32/32)なので、再現ではどちらが優れるとも言えない。
7 つの観点のどれでも、B は A と同じか上回っていて、B が劣る観点は無い。場面の多い P0-3(11 件)を除いても、残り 6 観点すべてで B が上回る(P0-6 では A は 0 件)。A には不一致が 1 件(P0-4 の p4-future-read-attempt)あり、構造で未来を読めなくする能力が確かめられていない。B に不一致・結果なしは 1 件も無い。表の注記でも、A は 15 升目に型が入らず、B は入らなかった升目が無い。以上から、正しさでは B(行 B)がはっきり優れ、再現は同等である。
- missing_in_choice(逐語): 表の 32 場面では、行 B に足りない場面は無い(正しさ・再現とも全件一致)。ただし表は、升目に当たらない場面(DEFINITIONS の grid_c.unplaced にある p2-iso-utc・p2-iso-offset・p2-event-time-exact・p2-one-ns-apart・p6-place-then-cancel・p7-account-swap)を升目の網羅として区分していない。だから、B が升目に対して全部の型を扱えることまでは、この表からは言えない(未確認)。

#### 盲検:0#15:current1

- choice: 左
- reasons(逐語): 表から観点ごとに数え直した(表の集計行と一致する)。正しさ(正解と一致)は、A と B がそれぞれ P0-1 3/3 と 1/3、P0-2 4/4 と 2/4、P0-3 11/11 と 1/11、P0-4 3/3 と 1/3、P0-5 3/3 と 1/3、P0-6 3/3 と 0/3、P0-7 5/5 と 2/5、計 32/32 と 8/32。7 観点のすべてで A が B を上回る。場面が 11 件ある P0-3 を除いても、A は他の 6 観点すべてで上回るので、場面の多い観点に引きずられた結論ではない。B の不一致でない場面は大半が「対応なし」で、能力が無いことを示す。P0-3 で B が一致したのは足(bar)の 1 種だけだった。このため P0-1 と P0-5 の型の組の場面(最低 2 種)も対応なしになったと読める(注記で B は 15 升目に型が入らなかった。A は無し)。さらに B は p4-future-read-attempt で「不一致」(every_attempt_stopped_by_error=false、future_value_obtained=false)を出した。黙って違う結果を返したので、対応なしより悪い。再現(2 回の実行で同じ)は A・B とも全観点で満点、計 32/32 で差が無い。したがって、正しさで A が全観点で優れ、再現では並ぶ。全体として A(左)が優れる。
- missing_in_choice(逐語): 表の範囲では、A に正解と一致しない場面も再現しない場面も無い(32/32、32/32)。足りない場面は表からは挙げられない。ただし表の外の注意点として、定義の見出しでは、どの升目にも当たらない場面が P0-2 に 4、P0-6 と P0-7 に 1 ずつある(p2-iso-utc・p2-iso-offset・p2-event-time-exact・p2-one-ns-apart・p6-place-then-cancel・p7-account-swap)。また各観点で「測っていない(固定した測り方の外)」升目が多数残っている(例: P0-2 は 160、P0-7 は 157)。この部分での A の振る舞いは、この表では確かめられていない。

#### 盲検:0#15:current2

- choice: 右
- reasons(逐語): 表のセルを観点ごとに自分で数え直した。数えた結果は表の集計行と一致する。
正しさ(正解と一致の数)は、観点ごとに A 対 B で次のとおり。
- P0-1: 1/3 対 3/3。A で一致したのは p1-one-call-per-event だけ。merge-by-time と typed-events は対応なし。
- P0-2: 2/4 対 4/4。A は iso-utc と iso-offset が対応なし。
- P0-3: 1/11 対 11/11。A で一致したのは p3-bar だけで、残り 10 件は対応なし。
- P0-4: 1/3 対 3/3。A は p4-received-time が対応なし。p4-future-read-attempt は不一致で、値は every_attempt_stopped_by_error=false。未来の値の読み取りを、構造上エラーとして止めていないことを示す。
- P0-5: 1/3 対 3/3。
- P0-6: 0/3 対 3/3。A は 3 件すべて対応なし。
- P0-7: 2/5 対 5/5。A で一致したのは fill-model-swap と cost-model-swap。
合計は A が 8/32、B が 32/32。
B は 7 観点すべてで A と同じか上回り、7 観点すべてで A より厳密に上である。したがって、場面数の多い P0-3 を除いても結論は変わらない。
再現(2 回の実行で同じ)は、A・B とも全観点で 32/32 だった。この点では差が無い。
A の「対応なし」は、表の注記によると多くが「この対象には型が入らなかった升目」(15 升)に当たる。これは能力が欠けていることを示している。
以上から、正しさと能力の有無では行 B が明確に優れ、再現は同等なので、行 B を選ぶ。
- missing_in_choice(逐語): 行 B について、表に示された 32 場面の中に欠けている場面は無い(すべて正解と一致し、2 回の実行で同じ)。ただし、定義文書にある升目に当たらない場面(p2-iso-utc、p2-iso-offset、p2-event-time-exact、p2-one-ns-apart、p6-place-then-cancel、p7-account-swap)は、升目の判断を 2 値で決めていない。このため、これらの場面での一致が型の升目の能力まで示すかは、この表からは確かめられない。

#### 盲検:0#15:survey0

- choice: 右
- reasons(逐語): 表のセルを自分で数え直した。正しさ(正解と一致)は、行 A が P0-1 3/3・P0-2 4/4・P0-3 10/11・P0-4 3/3・P0-5 3/3・P0-6 3/3・P0-7 5/5 で計 31/32。行 B は 7 観点すべて満点で計 32/32。差は P0-3 の p3-mixed-one-run の 1 場面だけで、この場面は 1 回の実行に 6 種の型を混ぜて入れ、値を見る。行 A は「対応なし」、行 B は「正解と一致」だった。再現(2 回の実行で同じ)は両行とも全観点で満点(32/32)で、差は無い。観点ごとに比べると、B が A を下回る観点は 1 つも無く、P0-3 だけで B が上回る。差は 1 場面なので、場面数の多い観点に引きずられた結果ではない。P0-3 は「8 種の事象型を扱えること」で、1 回の実行で型を混ぜて扱えるかは核の能力そのものに当たるので、この差を実質的な差とみた。補足すると、行 A は 54 件の設定つき対象から場面ごとに最良を寄せた合成の行である。注記によれば、寄せた対象の多くは型が入らない升目や結果なしの場面を抱えている(例: p2-iso-utc で 13 件、p6-place-then-cancel で 16 件、p7-fill-model-swap で 18 件が結果なし)。一方、行 B の注記は、型が入らなかった升目も、頼みの記録が無く入ったかを決められない升目も「無し」としている。1 つの対象で全場面を満たしている点でも B が上とみる。
- missing_in_choice(逐語): 表の 32 場面では、行 B に正しさ・再現のどちらでも足りない場面は無い。ただし、DEFINITIONS に書かれた升目に当たらない場面(P0-2 の p2-iso-utc・p2-iso-offset・p2-event-time-exact・p2-one-ns-apart、P0-6 の p6-place-then-cancel、P0-7 の p7-account-swap)は升目の表では区分されていない。そのため、これらの場面で B の能力が升目の上でも網羅されているかは、この表からは確かめられない。

#### 盲検:0#15:survey1

- choice: 左
- reasons(逐語): 表の各セルを観点ごとに自分で数え直した。数えた結果は表の集計(正解と一致: A 32/32、B 31/32。2 回の実行で同じ: A 32/32、B 32/32)と合っている。

正しさ(正解と一致の数、A 対 B):
- P0-1: 3/3 対 3/3
- P0-2: 4/4 対 4/4
- P0-3: 11/11 対 10/11
- P0-4: 3/3 対 3/3
- P0-5: 3/3 対 3/3
- P0-6: 3/3 対 3/3
- P0-7: 5/5 対 5/5

違いは P0-3 の 1 観点だけで、B の p3-mixed-one-run(値の場面)が「対応なし」になっている。この場面は、6 種の市場の事象を 1 回の実行に混ぜて入れ、型と時刻の列を見るもの。B は型ごとの場面 p3-trade〜p3-liquidation ではすべて正解と一致しているのに、混ぜて入れる 1 回の実行ができていない。

再現(2 回の実行で同じ)は、7 観点すべてで両者とも満点(A 32/32、B 32/32)で、差は無い。

観点ごとに見ると、A が B に劣る観点は 1 つも無く、P0-3 では A が 1 場面上回り、ほかの 6 観点は同点。場面の多い観点に引きずられた判断ではない。差はどの観点で見ても A 側に傾いている。したがって行 A を選ぶ。
- missing_in_choice(逐語): 表に示された結果の中には、行 A が正解と一致しない場面も、2 回の実行で違う場面も無い(7 観点 32 場面すべてが「正解と一致」かつ「2 回の実行で同じ」)。足りない場面は表からは見つからない。

#### 盲検:0#15:survey2

- choice: 右
- reasons(逐語): 表の場面の欄を 1 つずつ自分で数え直し、表の上にある観点ごとの集計の表と照らした。

正しさ(正解と一致の数、行 A / 行 B)
- P0-1: 3/3 / 3/3
- P0-2: 4/4 / 4/4
- P0-3: 10/11 / 11/11
- P0-4: 3/3 / 3/3
- P0-5: 3/3 / 3/3
- P0-6: 3/3 / 3/3
- P0-7: 5/5 / 5/5
- 計: 31/32 / 32/32

差は P0-3 の p3-mixed-one-run の 1 場面だけにある。行 A は「対応なし」、行 B は「正解と一致」。この場面は、6 種の市場の事象を 1 回の実行に混ぜて入れたとき、型と時刻の列が入力どおりに出るかを測る。行 A はこの能力を 1 回の実行では示せていない。

再現(2 回の実行で同じの数): 両方とも全 7 観点で満点(P0-1 3/3、P0-2 4/4、P0-3 11/11、P0-4 3/3、P0-5 3/3、P0-6 3/3、P0-7 5/5、計 32/32)。差は無い。

観点ごとの比べ: P0-3 は行 B が上で、残りの 6 観点は同点。行 A が上の観点は 1 つも無い。P0-3 は場面が 11 件と多い観点だが、観点の単位で見ても「1 観点で優、6 観点で同等」になり、場面の数の多さに引きずられた判断ではない。

補足(判断の材料にはしていない): 表の注記によると、行 A は設定つき対象 54 件から場面ごとに最良を寄せた行で、1 つの道具・1 つの設定の振る舞いではない。それでも p3-mixed-one-run で「正解と一致」に届いた設定つき対象は 1 件も無い。行 B は 1 つの対象で全場面が正解と一致しており、その意味でも行 B が上である。

以上から、正しさは行 B がわずかに上(P0-3 で 1 場面)、再現は同等なので、行 B(右)を選ぶ。

吟味: reasons に書いた観点ごとの数(A 計 31/32、B 計 32/32、再現は両方 32/32)を表の各セルから数え直し、表の上の集計の表と一致することを確かめた。行 A の p3-notice-filled の欄は、画面の出力で末尾が切れていた。ただし「正しさ: 正解と一致」の部分は読めており、集計の 10/11 とも合っている。
- missing_in_choice(逐語): 表の 32 場面では、行 B に足りない場面は無い(全場面で正解と一致、かつ 2 回の実行で同じ)。ただしこれは表に載った 32 場面の中での話で、次の升目はこの表では測られておらず、どちらの側についても評価できない。(1) 定義にある「測っていない(固定した測り方の外)」の升目。例: P0-3 の各型の「発注の呼び出しがその場で返す物」「戦略が対象の公開の手段で読む物」。(2) 升目に当たらない場面。

### リードの読みと答え(2026-09-25 08:50 UTC。段の途中で規則は足さない。次の起動の lead_notes に写す)

- 審査員は対現状・対調査とも 3 体が新実装の側(k=0,2 は右 = 新実装、k=1 は左 = 新実装)。連敗の鎖は 0/0 のまま。
- 批評家は実装の側 [止める] 1(i0-r15-01 = to_nanos が float の最短表記で読むので float が正確に持つ時刻を丸める。i0-r14-03 と同じ「値を狭めてから読む」族)・[直す] 3(i0-r15-02 sNaN の鍵の断りの型 / 03 FrozenDict の比べの枠数が契約の文と違う / 04 float の欄の規則が型で分かれる)・[示唆] 1。場面集の側 [止める] 1(i0-r15-05 = P0-2 に秒・ミリ・マイクロ秒の値の場面が無い。観点の文が名指す単位を場面集が覆っていない)・[直す] 1(i0-r15-06 = P0-2 の判断の欄の括弧の理由が事実と違う)。第 16 周は作業者と場面係が並行(L-441)。
- 作業者の問い 1(振る舞いの変化 4 つ): **採る。**項目 11・13 は契約 core-16 を読む前提で足りる。項目 13 への周知は次の起動の lead_notes["13"] に 1 行(core-15 の numpy の行と同じ所)。
- 作業者の問い 2(hash の等しい入れ子の値の比較で残る枠数の依存。extra の tuple / frozenset を核の class にする案): **進める。**批評家 i0-r15-03 も同じ根を [直す] とし「FrozenDict の比べを枠を積まない形にする」を挙げている。型が変わることは契約に書く(PlainFraction と同じ形 = isinstance は真のまま)。「契約の文を事実に合わせる」だけで閉じる方は採らない(要件から逃げる直し)。
- 作業者の問い 3(MAX_NESTING = 100 の根拠の変更、CALL_FRAMES = 30): **値は両方とも採る。**根拠の文を契約で書き換える(100 = インタプリタ自身の 1 つの値への再帰(比較・repr)を抑える上限 / 30 = 実測の最大 22 に余裕を足した)。A-12 の要件は実測で満たす。
- i0-r15-05(場面集の [止める]): 第 16 周の場面係が批評家の「直し方の向き」のとおり(既知の時刻を秒・ミリ・マイクロ秒で、文字列と float(正確に持つ値と持たない値)で入れ、対象自身の変換で int ナノ秒にした値を手計算の正解と照らす値の場面)に直す。リードの事前の答え: 正解は手計算の int ナノ秒 1 つで、float が正確に持たない値では「断る」も正解に入れる(黙って丸めた値は不一致)。これは F の升目の判断を変えない(秒・ミリの升目が「場面にした」に入るのは入力から機械で出るときだけ)。

## 第 16 周(進行中。09:48 UTC の見回りで写した分)

**終わった項目 0 / 14。項目 0 は第 16 周。通過に残るもの = 第 16 周の批評家の実装の側の [止める] 0(L-445 の射程の中だけが対象)。**

| 段 | 開始 | 終了 |
|---|---|---|
| 作る:0#16 | 08:41:53 | 09:34:12 |
| 場面の直し:0#r16-1 | 08:41:53 | (進行中、09:46:46 に書き込みあり) |

### 作業者 0#16 の返り値(逐語)

- `structural_change`: 時刻の変換 to_nanos は、float と numpy longdouble を持つ正確な値(as_integer_ratio)で読むようにした。最短の十進表記は読まない。float の欄(as_float・take_float)は、受け付ける全ての実数を「正確な値に最も近い float」という 1 つの規則で読むようにし、有限の値を inf にせず断る。核が辞書と集合を作るときは、鍵と要素の hash を先に取り、hash を持たない値は入口の誤りで断る。FrozenDict どうしの等しさは、核の反復の比べ values._plain_equal(明示の積み上げ + hash の表による対応づけ)で決めるようにした。これで、衝突した入れ子の比べは FrozenDict から下で段数によらない枠数になる。契約は core-17。
- `tests_added`: 3030 / `test_tail`: 13 failed, 9349 passed, 6 skipped, 4 warnings in 987.24s (0:16:27)。落ちた 13 件は全部 tests/bt/battery/item_0/ の場面集の試験(test_battery_def_grids.py 3 件、test_battery_item0.py 7 件、test_battery_r15_unplaced.py 2 件、test_battery_r16_units.py 1 件)で、場面係が並行して直している途中の物。落ち方の文は次の 3 種で、核の値に触れるものは無い: (1) 升目の判断の文言が「測っていない」と「測っていない(固定した測り方の外)」で食い違う、(2) 足した単位の場面を相手の結果がまだ持たない('1', 'opp_basana')、(3) DEFINITIONS の段落の数が 108 と 105 で合わない。tests/bt/item_0 と tests/bt/critic/item_0 に落ちたものは無い。批評家の第 15 周の試験 3 本 + 第 14 周の時刻の試験 → 50 passed in 0.21s(直す前は第 15 周の 3 本が 28 failed, 12 passed)。新しい格子 test_bt0_r16_one_reading.py → 3029 passed(直す前の核 0f2e07d では 563 failed, 2466 passed)。test_bt0_scene_set.py → 51 passed。tests_added の 3030 は新しい格子 3029 件と、場面の試験の単位の場面の駆動(1 関数。場面 15 件を足した)を合わせた数。
- `changed_files`: ["/home/user/trade/src/bot/bt/core/time.py", "/home/user/trade/src/bot/bt/core/values.py", "/home/user/trade/src/bot/bt/core/contract.py", "/home/user/trade/tests/bt/item_0/test_bt0_r16_one_reading.py", "/home/user/trade/tests/bt/item_0/test_bt0_time.py", "/home/user/trade/tests/bt/item_0/test_bt0_r15_library_code.py", "/home/user/trade/tests/bt/item_0/test_bt0_r14_process_state.py", "/home/user/trade/tests/bt/item_0/test_bt0_scene_set.py", "/home/user/trade/docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/round_16/ROOTCAUSE.md"]
- `unmet`:
  - 満たせなかった要件の行: 無し。以下は提出前の吟味の記録(委任文 §3。全文は round_16/ROOTCAUSE.md §7・§8)。
  - (1) 指摘ごとの直した根拠: i0-r15-01 = time.py 175 行(longdouble は持つ値)・201 行(float.as_integer_ratio)・212 行(断りの文に持つ値)。to_nanos(1700000000123456.75,'us') → 1700000000123456750、to_nanos(1700000000.123,'s') → 断る。断りの文は 'it holds 1700000000.1229999065399169921875'。i0-r15-02 = values.py 1032 行 _hashed を 1043 行 _dict_of と 1056 行 _set_of から呼ぶ。批評家の試験 25 件が全部通る。i0-r15-03 = values.py 1429〜1500 行 _container_kind・_match・_plain_equal、1387 行。freeze に要る枠の実測は、FrozenDict の値の側で 1・10・30・48・97 段とも 10〜11(前は 30 段 94・48 段 148)。i0-r15-04 = values.py 827 行 _beyond・834 行 _nearest_of・868 行 _longdouble_nearest・588 行(_now の int → float の検め)。批評家の試しで 2**53+1 が全部の型で 9007199254740992.0 になった。i0-r15-07 = time.py 188 行と、longdouble を持つ値で読む形にしたこと。断りの文は型ではなく「持つ値にナノ秒より細かい桁がある」を言う。
  - (2) 同じ根の全箇所: 核で数を文字の表記を通して読む所を grep で列べた。値の読みに使っていたのは time.py の float.__repr__ だけで、api.py 243 行・events.py 112/119 行の float.__repr__ は断りの文の中だけ。float の欄の入口は as_float と take_float の 2 つで、events.py の _finite・carrier の欄・fee を通る。辞書と集合を作る所は _dict_of と _set_of だけで、freeze・settle の全ての入れ物がここを通る。thaw と renew は核が作った入れ物からだけ作るので、変えていない(格子 E で確かめた)。
  - (3) 試験: tests/bt/item_0 と tests/bt/critic/item_0 に落ちたものは無い(全試験の実行で確かめた)。場面集の 13 件は場面係の途中の変更で落ちている(test_tail)。
  - (4) 厳しい批評家が止めそうな点は ROOTCAUSE §7 の 8 項に書いた。主なものは次のとおり。float の時刻を持つ値で読むと、打った十進(…456.8)と違う時刻(…456.75)になる → 核が見えるのは float だけで、Python でも両者は同じ float。十進の時刻は str か Decimal で渡す、と説明と断りの文に書いた。float の時刻で受け付けが狭まった(1700000000.123456 s を断る) → 持つ値にナノ秒より細かい桁がある値を丸めずに断るのは契約の「rounding: none」そのもの。_plain_equal と Python の == の一致は、乱数の組 3,000 以上とライブラリの神託で照らした。
  - (5) 場当たりでないこと: 核の差分に場面の id・場面集の語は無い(git diff 0f2e07d -- src/bot/bt/core | grep -ciE 'scene|p2-|battery' → 0)。批評家の試験は変えていない。自分の試験の枠の上限は、批評家の上限(2 × 段数)より厳しい契約どおりの CALL_FRAMES + 段数にした。
  - (6) 敵対者の格子を先に書いた: tests/bt/item_0/test_bt0_r16_one_reading.py。格子 T(時刻)・N(float の欄)・E(hash の無い値)・F(衝突した入れ子の比べ + 乱数の核の値)の 4 つ。神託はライブラリで入力から計算し、実装の場合分けからは作っていない。列に入れなかったもの(numpy の複素数は complex128 の 1 つだけ、datetime の値、スレッドの文脈を替えた状態の格子 T、clongdouble)は試験のファイルの先頭に書いた。
  - 途中で規則を 1 回替えた(ROOTCAUSE §2 の「途中で規則を替えた記録」): 最初は、float の時刻を「持つ値と最短表記が一致するときだけ」受け付ける規則にした。書いた後、場面係の単位の場面の正解が「float が持つ値 × 倍率」と置かれていること(ROOTCAUSE_r16-1 の主張 11)、批評家 i0-r15-01 の向きも同じであることを読み、持つ値で読む規則に替えた。場面集は読むだけで、変えていない。
  - 速さの測りは、ほかの試験と同時に走らせたので揺れが大きい。この周 77.89 / 72.74 us/bar、直す前 72.80 / 70.32 us/bar。静かな機械では測っていない(未確認)。
- `questions_for_lead`:
  - [振る舞いの変化の周知] to_nanos は、float と numpy longdouble の時刻を持つ正確な値で読むようになった(core-17)。持つ値にナノ秒より細かい桁がある float(例: 1700000000.123 s)は断る。前は最短表記で読み、1700000000123000000 として受け付けていた。項目 1(データ層)が float の秒やミリ秒の時刻を to_nanos に渡すなら、文字列・Decimal・int で渡す必要がある。項目 1 の要件を固定するときに、この 1 行を lead_notes に入れるかを決めてほしい(契約と time.py の説明には書いた)。
  - [L-444 との関係] LEAD_DESIGN.md §12 の案 1(射程を要件に書く)は、この周の作業では前提にしていない。この周に直した 4 件のうち、i0-r15-01(float の時刻の丸め)と i0-r15-04(float の欄の規則が型で分かれる)は、プロセスを書き換えなくても起きる値の誤り・食い違いで、案 1 の射程の中にある。i0-r15-02・03 は断りの型と枠の事実の問題。オーナーの決定のあと、批評家に渡す射程の文を決めるとき、この区別を使えるかを確かめてほしい。

### リードの答え(2026-09-25 09:50 UTC。段の途中で規則は足さない。次の起動の lead_notes に写す)

- 問い 1(to_nanos が float の時刻を持つ値で読む = 十進の時刻は str か Decimal で渡す): **項目 1 の lead_notes に入れる。**文面「核の to_nanos は float・longdouble を持つ正確な値で読み、ナノ秒より細かい桁があれば断る(core-17)。秒・ミリ秒の時刻は str・Decimal・int で渡す」。
- 問い 2(L-444/L-445 の射程との区別): **そのとおり。**i0-r15-01・04 はプロセスを書き換えなくても起きる値の誤りで射程の中、i0-r15-02・03 は断りの型と枠の事実の問題で射程の中(断りの型が契約と違うのは射程の外ではない)。射程の外に置くのは「戦略が Python のプロセス自体を書き換える形」(sys.modules・builtins・class の定義・ABC への登録・インタプリタの設定)だけで、要件 §0 に L-445 の文としてもう置いてある(09:05 UTC。この周の作業者が読んだ版より後)。第 16 周の批評家はこの §0 で測る。

## 第 16 周(続き。10:50 UTC の見回りで写した分)

**終わった項目 0 / 5(L-447 の数え)。項目 0 は第 16 周。通過に残るもの = 批評家 0#16(10:47 UTC〜)の実装の側の [止める] 0(L-445 の射程の中)。**

| 段 | 開始 | 終了 |
|---|---|---|
| 場面の直し:0#r16-1 | 08:41:53 | 10:10:05 |
| 監査役(場面):0#r16-1 | 10:10:07 | 10:16:28 |
| 表:0#16 | 10:16:29 | 10:47:45 |
| 批評:0#16 | 10:47:46 | (進行中) |

### 場面係 r16-1 の返り値(逐語)

- definitions: /home/user/trade/tests/bt/battery/item_0/DEFINITIONS.md
- runner: /home/user/trade/tests/bt/battery/item_0/run_battery.py
- scenarios: 46 / mutant: /home/user/trade/tests/bt/battery/item_0/mutant.py(--check → changed scenes: ['p4-received-time'] / OK。入力の事象の受け取れる時刻を取引所の時刻に置き換える試金石で、変わるのは p4-received-time だけ)
- survey_run: ["相手 37 と再現 1(設定つき対象は合わせて 54)を全部、46 場面に通した。記録は scratchpad の bt/r16-1/logs/run_all.log で、57 の設定つき対象(新実装・当方の現状・試金石を含む)が全部 rc=0。aat は、場面の側のイベントループの誤りを直したあとに走らせ直して rc=0。出力は tests/bt/battery/item_0/survey_results/ に写した", "時刻の単位を読む入口を持つのは aat・backtrader・barter・basana・freqtrade・hftbacktest・pyalgotrade・quantcore の 8 つ。道具ごとの入口は ROOTCAUSE_r16-1.md §6.1 の表にある。barter は、道具自身の epoch の変換を呼べるよう driver を作り直した(survey_results/attempts/61.log)。quantcore には、Parquet を読むのに要る pyarrow 25.0.1 を検査したうえで venv に入れた(survey_results/attempts/34.log)", "残りの道具は単位つきの時刻の入口が無く「対応なし」。探した範囲と打ったコマンドは survey_results/attempts/r16-1_unit_entries.txt(この環境の各 venv で確かめた。オーナー PC は未確認)"]
- rootcause: `/home/user/trade/tests/bt/battery/item_0/ROOTCAUSE_r16-1.md` / check_output: `OK 誤り 0 件` / lead_answer_changes: ["判断の第 2 の値の名: LEAD_DESIGN.md §8.2 の 1 の「測っていない(固定した測り方の外)」を「測っていない」に替え、括弧にはその升目を数える場面が無い理由を、宣言と入力から機械で出す(「この升目を宣言した場面が無い」/「宣言した場面はあるが、その事象の型が場面の入力から出ない」)。値は 2 つのままで、決め方(covers から機械で)も変えていない。理由: §8.2 の 1 は判定の基準(測り方の文が名指す組)を撤回して「covers に持つ場面が無い」に置き換えたが、値の名には撤回した基準の理由「固定した測り方の外」が残っており、その理由を確かめる機械は無い(批評家 i0-r15-06)。同じ名が正の定義 C の凍結した段落(gen_definitions.py の FROZEN_DEFINITIONS['C'])にもあるので、その 1 か所を新しい名と「括弧の理由は機械で出す」に替えた。C の段落のほかの文は変えていない。正の定義 F も変えていない。"]

### 監査役(場面) r16-1 の出力(逐語。11 回目の run はこの役を持つ古い台本で走っている = L-448 は 12 回目から)

- **F1** [聞く](repeat_of: None)
  tests/bt/battery/item_0/DEFINITIONS.md:175(および 200-206) — P0-2 の升目(事象型×観測経路、160 セル)の見出しは、この回の直し(i0-r15-05 対応)の前後で『場面にした 0』のまま変わっていない(修正前 0f2e07d 版も『場面にした 0 / 測っていない 160』、`git show 0f2e07d:tests/.../DEFINITIONS.md` で確認)。今回足した 14 個の単位場面(p2-s-*/ms-*/us-*)は入力に `events` を持たないため、正の定義 F の下でどの (事象型, 観測経路) セルにも当たらず(ROOTCAUSE_r16-1.md §2『根 1』も自認)、恒久的に升目を動かせない設計になっている。i0-r15-05 の批評家の指摘は『場面集が要件の観点を全部覆っているか』を問うたもので、対応として新設した『観点の文が名指す値ごとの場面』という並行集計(升目とは別建て)がこの問いに実質的に答えていると言えるか。升目の被覆が恒久的に 0/160 のままであることは、P0-2 が主語とする『事象』の時刻表現(戦略に届く物・発注/取消の応答・対象の公開の読み手段のいずれかの経路)が一度も実測されていないことを意味しないか(P3/P6)。
- **F2** [聞く](repeat_of: None)
  tests/bt/battery/item_0/scenes.py:306-321(_UNIT_NOTE) — P0-2 の単位場面は『対象が単位…の時刻として読む入口(対象のデータの入口の時刻の欄、または対象が公開する時刻の変換の関数)』を直接呼ぶ形で測っている。委任文(docs/DATA/delegations/20260923_backtest_env_prompt.md:114)の場面集の規則 2 は『場面は振る舞いを試し、作りの形を試さない』とし、例として『注文の通知は、データ源から入るか内部で作るかを問わず、戦略に届いたか・中身が正しいかで見る』を挙げている。P0-2 の要件文(REQUIREMENTS.md §2)は『全事象の時刻が…』と事象(戦略に配送される物)を主語にしているのに対し、単位場面は事象配送の経路を経由せず対象の変換関数を単体で呼ぶ。これは『戦略に届いた結果』ではなく変換ルーチン単体の出力を見ており、規則 2 の『作りの形ではなく振る舞いを試す』の要求に対して、対象の内部にある変換関数の存在・戻り値という実装の形に近づいていないか。
- **F3** [聞く](repeat_of: None)
  tests/bt/battery/item_0/ROOTCAUSE_r16-1.md:84(§5.2 の 3(a)) — この回で aat アダプタの ISO 場面(p2-iso-utc・p2-iso-offset)の判定入口を単位場面の追加のついでに変更し、結果が『対応なし』から『不一致』に変わったと自己申告している(『第 r15 周までの adapter は「取引所の実装の一つ」として使っていなかった』)。この入口の選び直しは aat の他の P0-2 場面(p2-event-time-exact・p2-one-ns-apart 等)には及んでいるか、及んでいないなら同じ対象の中で場面ごとに入口選定の基準が揃っていない状態にならないか。
- **F4** [聞く](repeat_of: None)
  tests/bt/battery/item_0/ROOTCAUSE_r16-1.md:155(§6.4) — 直す前に試験を回した記録(`test_battery_r16_units.py` が実装前に失敗すること)や、走らせ直しの記録・比較の出力は、すべて `<S>` = scratchpad 配下(`/tmp/claude-0/.../scratchpad/bt/r16-1/`)に置かれ、リポジトリにもコミットにも残らない(このセッションから到達不能)。この回の『試験を直す前に書き、通ることを確かめた』(委任文 §3 の吟味(6))という主張は、後から独立に(この監査を含め)再現・照合する手段が無い状態になっていないか。

### 表 0#16 の `notes`(逐語)

起動文の委任文の指紋 cdf623e4fb24 は 1 つ前の版(dc3f666)で、現行の版は 20487e2d8aec(abb256d)。2 つの版の違いは L-445 の射程の行と批評家の段落の 1 文だけで、資料係の手順は変わっていない。現行の版を読んで従った(commands.txt に記録)。

手順 1: 新実装の adapter(tests/bt/battery/item_0/adapters/new_impl.py)は既にあったので変えていない(変えると場面集の指紋が変わる)。公開された口だけを呼ぶことは check_new_impl_names.py で確かめた(18 個とも core.__all__ にあり、_ で始まる名前 0、bot.bt の import 0)。

手順 6(L-435): 場面集の指紋は 38460620…で、第 15 周の cb42e201… と違う。前の周の結果は使わず、57 対象(新実装・当方の現状・試金石と、調査結果の側の設定つき対象 54 件 = 候補 38 件)を全部 2 回ずつ走らせた。114 回とも rc=0。全対象を全 46 場面に通した(make_tables.py の load は場面が 1 つでも欠けると止まるが、止まらなかった)。

観点ごとの「正解と一致」の数(P0-1..P0-7 / 計)。出力から数え直した結果を recount.py と recount_cells.py で突き合わせ、不一致 0:
- 新実装: 3/3, 13/18, 11/11, 3/3, 3/3, 3/3, 5/5 = 41/46
- 当方の現状: 1/3, 2/18, 1/11, 1/3, 1/3, 0/3, 2/5 = 8/46
- 調査結果の側: 3/3, 8/18, 10/11, 3/3, 3/3, 3/3, 5/5 = 35/46
- 試金石: 3/3, 13/18, 11/11, 2/3, 3/3, 3/3, 5/5 = 40/46
「2 回の実行で同じ」は 4 行とも全観点で満点(46/46)。行 A と行 B を入れ替えた表どうしで数は同じ。

md5: 3 組とも 2 通りの表はバイト単位で違う。したがって L-422 の「同等」には当たらない。第 1 回と第 2 回の実行から作った同じ表は 6 枚とも同じ。所要の秒数も第 2 回の実測を使うと、survey の 2 枚が注記の秒数の分だけ違う。第 1 回と第 2 回で正しさ・再現の欄は全対象・全場面で同じ。値の欄だけが違ったのは 3 対象の各 1 場面で、表のセルには出ない。場面係の survey_results との違うセルは 0。

結果なしの場面の注記には、試したこと・出たもの・実測の所要の秒数が入っている。時間の打ち切りは 0 件で、「未記録」は 6 枚とも 0。動かせなかった候補ごとの欠けは件数と理由の内訳だけを注記に書いた。

注記の漏れの確認: 道具名の型 175 語で grep した。該当は survey の 2 枚の「書き直」(一般の語)だけ。時刻は 0。型の 1 文は 6 枚とも 1 回。道具名・時刻・候補番号は materials/commands.txt、survey_best.tsv、survey_failures.tsv にだけ書いた。

保存: 表を作るスクリプト、実行の記録(runs/、runs_2/、logs/)、対応表(対応表.md と mapping.tsv)、md5(md5sum_pairs.txt)、確認に打ったコマンドの出力は、全部 /home/user/trade/docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/round_16/materials/ に置いた。stale/ は空で、前の起動の表は無かった。
