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
