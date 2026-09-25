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
