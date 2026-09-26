# 批評家の記録(項目 0「核」、第 11 周。新しく起こされた批評家)

委任文: `docs/DATA/delegations/20260923_backtest_env_prompt.md`(指紋 `d3eae0d221c9`。`sha256sum … | cut -c1-12` で確かめ、全 164 行を読んだ)。
合意した完了の形(委任文 §0 の逐語): 「**すべてが調査結果以上の信頼性と再現性に優れたものにすること。**」
手元に置いたもの: 固定した要件 `item_0/REQUIREMENTS.md`(§1 の行・§2 の P0-1〜P0-7・§3 の調査結果の行)、場面集 `tests/bt/battery/item_0/DEFINITIONS.md`、作業者の根本原因 `round_11/ROOTCAUSE.md` と報告 `round_11/REPORT.md`、リードの設計 `round_7/LEAD_DESIGN.md`(§3.4・§7.4・§7.5・§8.1〜§8.5)、第 9 周の `CRITIC.md`。
行番号は作業木(HEAD `b7cbd63`。作業者と場面係の第 11 周の変更はリードのチェックポイントに入っている)のもの。
`<S>` = `/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt`、この周の試しは `<S>/r11_critic/`。

## 指摘

この周の [止める] は 1 件(i0-r11-02、相手: 場面集)。実装の側は [直す] 2 件(どちらも第 9 周の i0-r9-02 と同じ族)。

### i0-r11-01 [直す](相手: 実装、repeat_of: i0-r9-02)

**第 11 周の直し「外のコードが作った物を、核が持ち主の呼び出しの外で扱うときは、その class を通さない」は、dict の検索が鍵の `__eq__` を走らせることを見落としており、外のコードが持ち主の呼び出しの外で走る。**断りの型も契約と違う。

作業者の規則は「`type` 自身の記述子と基の型の C の関数は外のコードを走らせない」を前提にしている(`values.py` 194-203 行 `class_parts`: 「no code of the class, its metaclass or what its body set `__module__` to runs」、契約 `lifecycle`「no code of the failure ... runs and the refusal is always EngineFailedError (round 11)」、`type_decisions`「no code of the class or its metaclass runs ... a refusal is the error type of the place it enters」、`channel_payloads.ownership`「The core touches it only through base-type C functions ... never through the objects' own classes」)。前提が崩れる形が 2 つある。どちらも**メタクラスを使わない**(契約 `scope` が除外する「メタクラスが属性の読みで走るもの」には当たらない)。

- (a) **class の辞書の鍵**: `type` の `__module__` の記述子(`values.py` 181 行 `_TYPE_MODULE`)は、class 自身の辞書で `'__module__'` を検索する。`type()` そのもので、先頭の鍵が `'__module__'` と同じ hash を持つ送り手の物である辞書から作った class では、その検索が鍵の `__eq__` を呼ぶ。核が外の物の型を名指す所(`type_name` / `exception_text` の全部の読み手)の全部で、送り手のコードが持ち主の呼び出しの外で走り、そこで投げた例外が断りに代わる。
  - 戦略の例外(`engine.py` 884-900 行 `_usable` → `exception_text`)と、その例外の引数(`values.py` 217 行 `_arg_text` → `type_name`): FAILED の後の `step()`・`run()`・`result()` が `EngineFailedError` でなく送り手の `RuntimeError` になる。
  - 出口の箱の知らせと、箱の中の注文の物(`engine.py` 1109-1117 行 `_take_message`、462-472 行 `_settled_request`): `on_event` が返った後に戦略のコードが走り、断りが `OrderApiError` でなく `RuntimeError`。
  - 約定の模型の報告(1260-1270 行 `_take_reports`)・口座の強制注文(1185-1189 行 `_force`)・入力の流れの事象(634-652 行 `_pull`): 断りが `VenueProtocolError` / `AccountSocketError` / `SourceEventTypeError` でなく `RuntimeError`。
- (b) **戦略の側の注文の台帳の鍵**: 核は `on_event` が返った後に、戦略の台帳(戦略が届く普通の dict)へ新しい見え方を `dict.__setitem__` で書く(`engine.py` 1087-1090 行 `_show`。知らせの受け取り・発注・取消のたび)。戦略が次の注文の id と同じ hash の鍵を台帳に入れておくと、その書き込みが鍵の `__eq__` を `on_event` の外で走らせる(投げなければ 3 回走って実行は通る。投げれば実行は `RuntimeError` で FAILED)。

どの形でも、走る所は同じ時刻の配達の途中か失敗した後で、核の判断・送る物・結果・配達の要約は変わらない(黙って誤った値は無い。先の事象も見えない)。第 9 周の i0-r9-02 (a)(戦略のコードが `on_event` の外で走り、実行が `RuntimeError` で FAILED になる)と同じ結果の類で、リードの答え §7.5 の 22 は (a) を「FAILED で止まる経路」として [直す] のまま置いた。よって [直す]。族は i0-r9-02(核が、外のコードが変えられる物・作った物に後で触れ、そのコードを持ち主の呼び出しの外で走らせる)で、作業者自身が `round_11/ROOTCAUSE.md` §B-2 でこの周の直しを i0-r9-02 と同じ根の箇所と書いている。

加えて(読みが分かれるので書く): 箱の時計の知らせの値の class にメタクラスの `__hash__` を持たせると、`_settle` の `BUILD.get(t)`(`values.py` 340 行)がそれを `on_event` の外で走らせる(断りは `OrderApiError` のまま)。契約の除外は「メタクラスが属性の読みで走るもの」で、hash はそれに入るかが読み分かれる。

根拠:
- `PYTHONPATH=src python3 <S>/r11_critic/item0_r11_critic_probe_module_key_nometa.py` → `metaclass of Boom: <class 'type'>` / `step -> RuntimeError | is EngineFailedError: False` / `run -> RuntimeError | …: False` / `result -> RuntimeError | …: False` / `Key.__eq__ ran in: ['engine.step', 'engine.run', 'engine.result']`(`…_nometa.out`)。
- `<S>/r11_critic/item0_r11_critic_probe_outbox_key.py` → `plain object() -> run raised OrderApiError | OrderApiError: True` / `Msg -> run raised RuntimeError | OrderApiError: False | strategy code ran outside on_event` / `['Key.__eq__ OUTSIDE on_event']`(`…_outbox_key.out`)。
- `<S>/r11_critic/item0_r11_critic_probe_sockets_key.out` → `fill_model -> RuntimeError | sender code outside its call: 1` / `account -> RuntimeError | … 1` / `stream -> RuntimeError | … 1`。
- `<S>/r11_critic/item0_r11_critic_probe_registry_key.py` → `raise: False -> run ok [('mine-1', 'FILLED')]` / `strategy code outside on_event: 3 ['mine-1', 'mine-1', 'mine-1']` / `raise: True -> run raised RuntimeError | CoreError: False`(`…_registry_key.out`)。
- メタクラスの hash: `<S>/r11_critic/item0_r11_critic_probe_outbox_metahash.py` → `run raised OrderApiError | OrderApiError: True` / `['M.__hash__ OUTSIDE on_event']`。
- 試験(残す。作業者が直す): `tests/bt/critic/item_0/test_i0r11_class_dict_key_runs_foreign_code.py` → `PYTHONPATH=src python -m pytest tests/bt/critic/item_0/test_i0r11_class_dict_key_runs_foreign_code.py -p no:cacheprovider` → `12 failed`(格子: 戦略の例外 × {型, 引数} × {step, run, result} = 6、箱 × {知らせ, 注文の物} = 2、{約定の模型, 口座, 入力の流れ} = 3、台帳 = 1。落ち方は 12 件とも `the …'s code ran outside …` の assert で、送り手の鍵の `__eq__` の記録が残る)。

### i0-r11-02 [止める](相手: 場面集、repeat_of: null)

**升目の表の「場面にした」の 18 升目は、それを `covers` に持つ場面のどれも、その事象の型を入力に持たない。**`covers` は手で書いた宣言で(`scenes.py` 554-605 行、`COVERS` は 565 行から。注に「A scene whose events the scene leaves to the target … covers each market type it may be run with」)、第 r11-1 回から升目の判断は `covers` だけで決まる(`grid_c.py` 107-111 行 `verdict`)。リードの設計 §8.2 の 1 は「`covers` は場面の宣言で、批評家が『場面の測る物と covers が合わない』と見れば [直す]/[止める] にする」とし、§8.5 の 24(20:58 UTC)は「`covers` の事象の軸は、その場面の入力(scenes.py の入力の事象と `type_plan` で作る事象)に実際に含まれる型から機械で出す」と決めた。今の `covers` はこれと合わない:

- 型を対象が 1 つ選ぶ場面(p1-one-call-per-event・p2-event-time-exact・p2-one-ns-apart・p5-same-stream-order)は、1 回の実行で 1 つの型しか走らないのに市場の事象の 6 型を全部宣言する。新実装の adapter は p2 の 2 場面を約定だけで走らせる(`adapters/new_impl.py` 293-311 行)。
- p2-iso-utc・p2-iso-offset は事象を 1 件も持たない(入力は ISO の文字列だけ)のに、6 型 × 「戦略が対象の公開の手段で読む物」× ISO 文字列 を宣言する。
- `type_plan` の 4 場面は、6 型を全部持つ対象でも 2〜4 型しか作らない(p1-merge-by-time = 約定・板の写真・板の差分、p1-typed-events = 約定・板の写真、p5-* = 約定・板の写真・板の差分・足)のに 6 型を宣言する。資金調達・清算を入れる場面が P0-1・P0-5 に無い。
- P0-4 の 3 場面は入力が足だけ・約定だけなのに、約定と足の両方を宣言する。

結果、市場の事象の軸で「場面にした」の 35 升目のうち 18 升目(P0-2 は 12 升目の全部、P0-1 2、P0-4 2、P0-5 2)が、どの場面の入力にもその型の事象が無い。この表は §8.2 の 2 の文どおり「測っていない範囲の記録」で、項目 0 の通過の報告でオーナーに渡る。測っていない升目を「場面にした」と書くのは、測っていない範囲を実際より狭く見せる向き(新実装の通過の報告に有利な向き。第 r11-1 回の監査役の [聞く] br11-1-1 が挙げた向き)で、場面集の出力が黙って誤った値を出している。

格付け: 場面の入力・正解・比較の表のセルは変わらないので [直す] とも読める(第 9 周の i0-r9-03 は DEFINITIONS の語の未適用を [直す] にした)。一方、これは語ではなく「何を測ったか」の事実の誤りで、表の唯一の目的(測っていない範囲の記録)を損ない、18 升目は機械で数えられる。委任文 §3「迷ったら重い方」により [止める] とした。族は i0-r9-03(升目の判断に測定でない値「未決」が入っていた)と同じ表だが、機構は違う(判断の値の種類ではなく、宣言が測った物より広い)ので repeat_of は null。

根拠:
- `PYTHONPATH=src:. python3 -` で `grid_c.table(scenes.SCENES)` の「場面にした」升目ごとに、覆う場面の入力の事象の型(`events`・`streams` の `kind`)を突き合わせた → `場面にした cells (market event axis): 35 of which no covering scene's input holds the type: 19`。うち 1 件(P0-3 の 時計)は時計の事象が戦略の頼みで作られるので誤りではなく、残る 18 件(`Counter({'P0-2': 12, 'P0-1': 2, 'P0-4': 2, 'P0-5': 2})`)。
- `type_plan` の場面を 6 型を全部持つ対象で作った入力: `scenes.for_target_types(s, scenes.TYPE_ORDER)` → `p1-merge-by-time ['book_delta', 'book_snapshot', 'trade']` / `p1-typed-events ['book_snapshot', 'trade']` / `p5-same-time-twice ['bar', 'book_delta', 'book_snapshot', 'trade']` / `p5-hand-over-order` 同じ。
- 試験(残す。場面係が直す): `tests/bt/critic/item_0/test_i0r11_covers_within_scene_input.py`(場面ごとに、`covers` の市場の事象の型 ⊆ 入力の事象の型。`type_plan` の場面は 6 型を持つ対象で作る)→ `13 failed, 19 passed`(落ちる 13 場面: p1-merge-by-time・p1-one-call-per-event・p1-typed-events・p2-iso-utc・p2-iso-offset・p2-event-time-exact・p2-one-ns-apart・p4-visible-at-step・p4-received-time・p4-future-read-attempt・p5-same-time-twice・p5-hand-over-order・p5-same-stream-order)。
- 人の読みで残る 1 点(機械では測っていない): p6-place-then-cancel の `covers` = (注文の受付の通知, 戦略が対象の公開の手段で読む物)。場面が読むのは未決の注文の数で、受付の通知そのものは読まない。場面係が ROOTCAUSE_r11-1.md §8 の 2 でリードに上げている。

### i0-r11-03 [直す](相手: 実装、repeat_of: i0-r9-02)

**戦略が、届く物を何も書き換えずに読むための view を持つだけで、核の手順が `BufferError` で落ちる。**落とした事象の事実の `array('q')`(`history.py` 132 行からの `HistoryLists` の `dropped_seqs`・`dropped_recvs`)は戦略の側の物で、文脈の `dropped_of` の既定値(`engine.py` 1060-1063 行)から届く。核は落とすたびにそれを `array.array.extend` で伸ばす(`history.py` 176-177 行)。戦略がその array の `memoryview` を持っている間は array の大きさを変えられないので、次に落とすときに核の `extend` が `BufferError: cannot resize an array that is exporting buffers` を投げ、`on_event` の外(核の配達の手順の中)で実行が FAILED になる。契約 `scope`「So is the strategy changing ANY state object it can reach, by any means … such a change reaches only what the strategy itself reads」と、engine.py の説明「nothing it changes there, by any means, reaches the core, the venue, another receiver or the caller's result」に反する(ここでは何も変えていないのに、呼び手の結果が失敗に変わる)。作業者の変更の格子(`test_bt0_r11_foreign_objects.py` 格子 2)は、型が持つ変更の方法(dir の差)を列べるので、buffer の書き出しで大きさを固める道は列の外。

失敗で止まる経路で、黙って誤った値は無いので、i0-r9-02 (a) と同じく [直す]。族は i0-r9-02(核が、戦略が届いて API を通さずに作用できる物に後で触れる)。

根拠:
- `PYTHONPATH=src python3 <S>/r11_critic/item0_r11_critic_probe_array_export.py` → `hold views: False -> run ok, events 12 digest 06cfb720ce34` / `hold views: True -> run raised BufferError | CoreError: False | cannot resize an array that is exporting buffers | views held: 24`(`…_array_export.out`)。
- 試験(残す。作業者が直す): `tests/bt/critic/item_0/test_i0r11_pinned_dropped_facts_fail_the_core_step.py` → `1 failed`(`E BufferError: cannot resize an array that is exporting buffers`)。

### i0-r11-04 [示唆](相手: 場面集、repeat_of: null)

検討表の 13 DeviaVir/zenbot(P0-6)の行は、能 3 を「無い(戦略に渡る口に取消が無い。`cancelOrder` は engine が値を追い直すときに自分で呼ぶ内側の関数(835-888 行))」とする。一次資料の同じ版の engine.js 831-835 行は `checkOrder` で「signal switched during …, aborting → `return cancelOrder(order, type, false, cb)`」で、戦略が信号を切り替えると engine が注文を取り消す。取消の結果を戦略に返す口は無い(戦略に渡る口は 104-109 行の `orderExecuted` ほか)ので、能 3(取り消し、その結果が戦略に返る)を「無い」とする結論は変わらず、スキップも成り立つ(含む側の 1 Basana の p6-place-then-cancel・p6-cancel-notice が「正解と一致」)。理由の欄に「信号の切り替えで engine が取り消す道(831-835 行)はあるが、結果は戦略に返らない」を足すと、読む者が同じ確かめをしなくて済む。

根拠: `curl -sS https://raw.githubusercontent.com/DeviaVir/zenbot/52872fb4b5f9d10e2f891d95daec05da0b721ceb/lib/engine.js`(読むだけ。実行していない。`<S>/r11_critic/zenbot_engine_52872fb.js`、1009 行)→ 831-835 行 `function checkOrder (order, type, cb) { if (!s[type + '_order']) { // signal switched, stop checking order … return cancelOrder(order, type, false, cb)`。

## 前の周の指摘の直りを確かめた記録(直ったものは上に挙げない)

| 前の指摘 | 確かめたこと(コマンドと出力) | 結論 |
|---|---|---|
| i0-r9-01(history_limit の下の断りすぎと、事実と違う断りの文) | 第 9 周の最小の再現 `item0_r9_critic_probe_history_until.py` → `until_ns=T0+3s -> [1, 2] place (0, 1, 3, 0)` / `n=1, until_ns=T0+3s -> [2] place (1, 1, 3, 0)` / `until_ns=T0 (before every event) -> [] place (0, 1, 3, 0)`(制限なしと同じ事象の列)。自分の神託 `<S>/r11_critic/item0_r11_critic_probe_history_oracle2.py 1001 1060`(契約の文だけから作った。4 型・同時刻の束・N 1〜4・60 件まで・n 9 まで・空の答えの place も見る)→ `{'ok': 908526, 'refused_ok': 205930, 'wrong': 0, 'silent_short': 0, 'over_refused': 0, 'place_wrong': 0}`。断りの文の勧め(「since_ns を名指した事象の受け取り時刻より後」「n <= 保たれた最新の件数」)は `api.py` 807-848 行 `__refuse_truncated` の作りで、名指すのは答えの中の落とした事象のうち最新の物なので、どちらの勧めでも落とした事象は答えから外れる(読みで確かめた)。直りを固定する試験 `tests/bt/critic/item_0/test_i0r11_history_limit_exact_refusal.py`(断りすぎと空の答えの place も見る)→ `10 passed` | 直った |
| i0-r9-02(`__class__` の代入で核が戦略のコードを `on_event` の外で走らせる / 閉じ込めから核の物に届く) | 第 9 周の試しは名前で口を探すので今の版では動かない(リードの §8.5 の 28 のとおり批評家が作り直す)。作業者の試しを使わずに書いた `<S>/r11_critic/item0_r11_critic_probe_reach_swap.py`: 26 回の呼び出しのたびに、文脈から gc の参照(関数の cell・既定値・kwdefaults・`__dict__`、結び付いた方法の `__self__`)で歩いて届く物と、エンジンから(戦略の側の入れ物と戦略に入らずに)歩いて届く物を突き合わせ、届いた物のうち class を変えられる物の全部に、特殊な方法と `__getattribute__`・`__setattr__` を記録する子 class を `__class__` で与えた → `callbacks with core state shared: []`、記録の付いた class 13 種(`_OrderPort`・`StrategyContext`・`EventWindow`・`DeliveredList`・`OrderView`・事象 7 種・`array`)、`uses of those classes OUTSIDE on_event: [] count 0`。結果は当てない実行と同じ(`digest 780a441aafb0cf8f`、約定 2 件、注文 3 件の状態が同じ。`…_reach_swap.out`) | 第 9 周の 2 つの道は直った。同じ族の別の形が残る = i0-r11-01・i0-r11-03 |
| i0-r9-03(DEFINITIONS の「未決」の升目) | `grep -c '未決' DEFINITIONS.md` → `4`。4 行とも p6-place-then-cancel の文(884・888・889 行)で、注文の状態の「未決の注文」。升目の判断の値は `grid_c.py` 102 行 `VERDICTS` の 2 つだけ。表の節の頭(101 行)に §8.2 の 2 の 1 文がある。`test_battery_item0.py` 1474 行の試験(正の定義 0〜E の凍結)を含む場面集の試験は通る(下) | 直った |
| i0-r9-04 [示唆](集合の反復の順と PYTHONHASHSEED) | リードの答え §8.3: 項目 8 の要件を固定するときに決める | リードの決定で持ち越し |
| 前の周までの [止める](i0-r8-01・i0-r7-01・i0-r7-02 ほか) | 批評家の試験の全部を今の作業木で回した: `PYTHONPATH=src python -m pytest tests/bt/item_0 tests/bt/critic/item_0 -p no:cacheprovider` → `1624 passed, 2 skipped in 320.15s`(この周の私の試験を足す前。`<S>/pytest_item0_r11_critic_core.log`) | 直ったまま |

### 付け直しの見直し(前の周の [直す]・[示唆])

前の周の [直す] 3 件は直った。[示唆] i0-r9-04 はリードの決定で持ち越し、[止める] の基準(要件・正解・試験・信頼性と再現性・場当たり・§4・場面集の規則)のどれにも当たらない(核の配達の要約は種によらず同じ = 第 9 周の実測)。付け直す物は無い。

### 規則 8(作業者が「試験自身の誤り」と報告した批評家の試験)

第 10 周・第 11 周の作業者の報告(`round_10/REPORT.md` 51 行、`round_11/REPORT.md` の (3))は、どちらも「批評家の試験が試験自身の誤りで落ちるものは無い」。第 9 周の後に批評家の試験は消されても書き換えられてもいない(`git diff --stat 5092565 HEAD -- tests/bt/critic/item_0` は第 9 周の私の前任の試験 1 本の追加だけ)。取り下げる試験は無い。

## 場面集の側で見たこと

- 場面集の試験: `PYTHONPATH=src python -m pytest tests/bt/battery/item_0 -p no:cacheprovider` → `78 passed in 38.33s`(`<S>/pytest_item0_r11_critic_battery.log`)。検討表の機械の検め: `python3 scripts/check_bt_considered.py tests/bt/battery/item_0/opponents/CONSIDERED.md` → `OK 誤り 0 件`。
- 第 9 周から場面集で変わったのは DEFINITIONS・ROOTCAUSE_r10-1/r11-1・def_axes/jC・def_grids・gen_definitions・grid_c・line/term の判断・試験で、adapter・runner・検討表・再現・mutant・scenes.py は変わっていない(`git diff --stat 5092565 HEAD -- tests/bt/battery/item_0`)。
- 正の定義 C の置き換え: `ROOTCAUSE_r8-1.md` 555 行の C を「。」で切ると、置き換わったのは第 9〜12 文(3 値の判断・測り方の文の語で決める・リードの決定・その当て方)だけで、ほかは同じ(`test_battery_item0.py` 1474 行の試験が照らし、通る)。
- **リードの答え §7.3 の 16 (a) の続き(検討表の「スキップ(上位互換)」を番号の順に 3 行)**: 第 9 周の批評家の名指しどおり 13 DeviaVir/zenbot(P0-6)・13(P0-7)・38 microsoft/MarS(P0-7)を読んだ。
  - 含む側に引かれた結果は全部「正解と一致」: `survey_results/opp_basana.tsv` の p1-one-call-per-event・p6-place-then-cancel・p6-cancel-notice・p6-fill-seen-by-strategy・p7-fill-model-swap・p7-cost-model-swap・p7-cost-per-unit、`opp_aat.tsv` の p7-fill-model-swap、`opp_mihircoding_lob.tsv` の p7-latency-model-swap、`opp_gobacktest.tsv` の p7-account-swap(`awk -F'\t' '$2 ~ /^p1-one-call|^p6-|^p7-/ {print $2, $5, $7}'` の出力)。含む側の Basana の行は資料係の venv の配布物に実在する(`basana/core/dispatcher/base.py` 155 行 `def subscribe(`、`basana/backtesting/exchange.py` 361 行 `def subscribe_to_order_events(`・103 行 `fee_strategy: fees.FeeStrategy = fees.NoFee(),`、`basana/backtesting/fees.py` 35 行 `class FeeStrategy`)。
  - 一次資料の読み(読むだけ): zenbot の engine.js 104-109 行(`orderExecuted`)・792-800 行(`cancelOrder`)は行のとおり。831-835 行の信号の切り替えによる取消は i0-r11-04。MarS の mlib/core/engine.py 35-39 行(`Engine(exchange: Exchange, …)`)・143-144 行(`wakeup_time + agent.computation_delay + agent.communication_delay`)は行のとおり。3 行ともスキップは成り立つ。
  - 次の周の批評家は、番号の順で次の 3 行(52 QuantConnect(P0-6)・52(P0-7)・57 WonderTrader(P0-1))を読む。
- 資料係の表: 6 枚の組の 2 通りは 3 組とも違う(`round_11/materials/md5sum_pairs.txt`)。場面集の指紋が第 9 周と違うので相手の道具を全部走らせ直した(`materials/commands.txt`、L-435 どおり)。新実装の行は `materials/runs/new_impl.tsv` で 32 / 32 が「正解と一致・2 回の実行で同じ」。
- adapter の公平さ: adapter は第 9 周から変わっておらず、第 9 周の批評家の読み(新実装の adapter が約定の模型に場面集の側の小さな模型を渡すのは公開の差し込み口の範囲)を変える物は無い。型を対象が選ぶ場面で新実装の adapter が約定を選ぶこと(`new_impl.py` 294 行)は、他の対象も 1 型を選ぶ規則(場面の note)の範囲で、表のセルの勝ち負けを決めていない。これが升目の表の宣言と合わないことは i0-r11-02。
- 覆い: 固定した要件 §2 の P0-1〜P0-7 の全観点に値の場面が 1 つ以上ある(`scenes.py` 612-614 行の assert)。升目の表の「場面にした」の過大は i0-r11-02。

## 構造の変化

前の周から構造は変わった(`structural_change_since_prev = true`)。コードで確かめたもの: 外のコードが作った例外と class を核が扱うとき、型の名前を `type` の記述子で読み(`values.py` 194-213 行 `class_parts`・`type_name`)、FAILED の断りの文を例外の事実だけから作る(`values.py` 230-249 行 `exception_text`、`engine.py` 884-900 行)/ 差し込み口の名前を構築のときに 1 度だけ読む(`engine.py` 758-763 行 `_models`、`result()` は差し込み口の class を読まない)/ `values._now` の断りの文も `exception_text`。第 10 周の構造(戦略の側の物を `_StrategySide` 1 か所にまとめ、核の状態から参照しない)は、私の試しで到達性 0 を確かめた(上の表)。

## 提出前の吟味(批評家の文: 指摘ごとに根拠を自分で再現し、格付けを基準に照らし、前の周の指摘の直りを自分で確かめ、相手の付け違いが無いか確かめる)

| 指摘 | 根拠を自分で再現したか | 格付けを基準に照らした結果 | 相手 |
|---|---|---|---|
| i0-r11-01 | 試し 5 本と試験 1 本(12 升目)を打ち、出力を上に逐語で写した。最初の試しは自分の print が `type(exc).__module__` を読んで鍵の `__eq__` を走らせた(自分の誤り)ので、印を付けてから読むように直して打ち直した。試験の落ち方が試験自身の誤りでないことを、pytest を通さない同じ組み立て(`item0_r11_critic_probe_sockets_key.out`)で確かめた | 走るのは同じ時刻の配達の途中か失敗の後で、核の判断・送る物・結果・配達の要約は変わらない。失敗で止まる経路は i0-r9-02 (a) と同じ類で、リードの §7.5 の 22 が [直す] のまま置いた。[止める] の基準(要件・正解・試験・信頼性と再現性・場当たり・§4・場面集の規則)のどれにも当たらない = [直す]。作業者の直しは読み方の規則を全部の読み手に当てた物で、場当たりではない(前提の誤り) | 実装(`src/bot/bt/core/values.py`・`engine.py`・`contract.py`) |
| i0-r11-02 | 升目と入力の型の突き合わせを打ち、試験を書いて打った(13 failed)。時計の升目は自分の数えの誤り(時計の事象は入力でなく戦略の頼みで作られる)なので数えから外した | 場面・正解・表のセルは変わらないので [直す] とも読めるが、測っていない 18 升目を「場面にした」とする事実の誤りで、表の目的(測っていない範囲の記録)を損ない、通過の報告に有利な向き。迷ったので重い方の [止める] | 場面集(`tests/bt/battery/item_0/scenes.py` の `COVERS`、その出力の DEFINITIONS.md) |
| i0-r11-03 | 試しと試験を打った(`BufferError`) | 失敗で止まる経路で、黙って誤った値は無い = [直す](i0-r9-02 (a) と同じ類) | 実装(`src/bot/bt/core/history.py`・`engine.py`) |
| i0-r11-04 | 一次資料の同じ版を読み、行を写した | 結論とスキップは変わらない。要件の外の改善 = [示唆] | 場面集(検討表) |

場当たりの直し(試験だけの特別扱い・閾値や既定値をずらす・文言合わせ・機能を外す)は見つからなかった。

この周に足した批評家の試験(`tests/bt/critic/item_0/`): `test_i0r11_class_dict_key_runs_foreign_code.py`(12 件、全部落ちる = i0-r11-01)、`test_i0r11_covers_within_scene_input.py`(32 件、13 件落ちる = i0-r11-02)、`test_i0r11_pinned_dropped_facts_fail_the_core_step.py`(1 件、落ちる = i0-r11-03)、`test_i0r11_history_limit_exact_refusal.py`(10 件、通る = i0-r9-01 の直りの固定)。批評家の試験の全部: `PYTHONPATH=src python -m pytest tests/bt/critic/item_0 -p no:cacheprovider` → `26 failed, 114 passed in 199.64s`(`<S>/pytest_item0_r11_critic_criticdir.log`。落ちる 26 件はこの周の 3 本だけ)。
