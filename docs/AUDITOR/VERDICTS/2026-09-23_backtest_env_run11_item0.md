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
