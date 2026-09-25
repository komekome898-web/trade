# 批評家の記録(項目 0「核」、第 14 周。新しく起こされた批評家)

委任文: `docs/DATA/delegations/20260923_backtest_env_prompt.md`(`sha256sum … | cut -c1-12` → `cdf623e4fb24`。起動文の指紋と一致。全 169 行を読んだ)。
合意した完了の形(委任文 §0 の逐語): 「**すべてが調査結果以上の信頼性と再現性に優れたものにすること。**」
手元に置いたもの: 固定した要件 `item_0/REQUIREMENTS.md`(§1 の行、§2 の P0-1〜P0-7、§3 の調査結果の行)、場面集 `tests/bt/battery/item_0/DEFINITIONS.md`・`scenes.py`・`opponents/CONSIDERED.md`、作業者の根本原因 `round_14/ROOTCAUSE.md` と返り値(`docs/AUDITOR/VERDICTS/2026-09-23_backtest_env_run11_item0.md` の第 14 周の節。リードの答えを含む)、第 13 周の `CRITIC.md`。
行番号は作業木のもの(HEAD `563661d`。作業者の変更はこのコミットに入っている)。
`<S>` = `/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt`。この周の試しは `<S>/r14_critic/` に置いた。

## 前の周の指摘の直り(自分で確かめた)

- **i0-r13-01(止める、実装)**: 指摘した 4 つの形は直っている。第 13 周の試しを今の核で回し直した(`<S>/r14_critic/item0_r14_critic_recheck_r13_probes.out`)。registry: `register -> run ok | fee seen by the account: [0.75]`・`hook -> … [0.75] | hook calls: 0`。rerun: `run A again, same input, same process : ('ok', [0.75], [0])`・`delay 1.5 as float32, after the registration : ('raised LatencyModelError', …)`。fill_price: `register -> … [100.5]`。numpy_bool_attr: `patch True -> run raised OrderApiError … | []`。第 13 周の試験 `test_i0r13_process_global_state_decides_core_values.py` も通る(下の 159 passed に入っている)。**ただし同じ族(核の判断がプロセス全体の状態で決まり、外の者のコードが持ち主の呼び出しの外で走る)の別の形が残っている**: 下の i0-r14-01・i0-r14-02。
- **i0-r11-01(直す、実装)・i0-r11-03(直す、実装)**: 直っている。第 11 周の試験 3 本(`test_i0r11_class_dict_key_runs_foreign_code.py`・`test_i0r11_pinned_dropped_facts_fail_the_core_step.py`・`test_i0r11_history_limit_exact_refusal.py`)は下の実行で全部通った。
- 規則 8(批評家の試験自身の誤り): 作業者は第 14 周の返り値で「当たる試験は無い」と書いた。前の周までの批評家の試験で落ちるものは無かった(下の実行)。取り下げる試験は無い。
- 作業者が書き直した既存の試験 2 本(`test_bt0_sender_types.py`・`test_bt0_r11_foreign_objects.py`)は、ABC への登録を ABC の継承に替えただけで、試す中身(送り手の変換が投げると入口の誤りになる)は弱めていない(`git diff e13fec6 563661d -- …` を読んだ)。
- 前の周の [直す]・[示唆] で [止める] に付け直すものは無い(残っている前の周の [直す] は無い)。

実行した試験:
- `PYTHONPATH=src python -m pytest tests/bt/item_0 tests/bt/critic/item_0 tests/bt/battery/item_0 -p no:cacheprovider -rf`(この周の新しい試験を置く前に集めた)→ `2101 passed, 2 skipped in 453.18s (0:07:33)`(`<S>/r14_critic/pytest_item0_r14_critic_all0.log`)。
- 新しい試験を置いたあと `PYTHONPATH=src python -m pytest tests/bt/critic/item_0 -p no:cacheprovider` → `17 failed, 159 passed in 226.13s (0:03:46)`(`<S>/r14_critic/pytest_item0_r14_critic_criticdir.log`)。落ちた 17 件は全部この周の新しい試験 3 本(下の指摘の根拠)。

## 指摘

この周の [止める] は 4 件(全部、相手: 実装)、[直す] は 2 件(実装 1・場面集 1)。

### i0-r14-01 [止める](相手: 実装、repeat_of: i0-r13-01、場当たり: いいえ)

**核は、落ち着かせた値から集合と辞書を作り直すとき(`values.py` 570 行・576 行 `_settle`、848 行・851 行 `_freeze`)、hash の衝突した要素どうしを比べる。Fraction と Decimal(または float・complex)の等しさはライブラリのコードで、numbers の ABC に聞く(`fractions.py` の `Fraction.__eq__` は `isinstance(b, numbers.Rational)`、C の decimal も `isinstance(w, Rational)`)。よって ABC の登録簿とフックが、核の受け付け・断り・結果を決め、戦略のフックが戦略の呼び出しの外で走る。** `Fraction(1)` と `Decimal(2**61)` は hash が同じ(2**61-1 を法として 1)で、等しくない。

- (a) **再現性**: 戦略が `extra=(("k", {Fraction(1): "a", Decimal(2**61): "b"}),)` の注文を出す同じ実行が、新しいプロセスでは `run ok` で、別の実行の戦略が `numbers.Rational.register(Decimal)` を呼んだあとは同じプロセスで `AttributeError`('decimal.Decimal' object has no attribute 'numerator')で止まる。契約 `process_state`(`contract.py` 138-166 行)の「a registration, a subclass hook … made by any party, in any earlier run of the process -- changes no value, refusal or result of the core」に反する。
- (b) **別の者の答えを変える**: 口座(別の者)の強制注文の extra に同じ値があるとき、戦略が自分の on_event で登録しただけで、口座の注文が `AttributeError` で止まる(登録しなければ `run ok`)。
- (c) **外のコードが持ち主の呼び出しの外で走る**: 戦略が `numbers.Rational` の子でメタクラスに `__subclasscheck__` を持つ class を作り、どの ABC でも 1 回登録すると(負の覚えが消える)、核が注文を作り直すとき(`engine.py` `_settled_request` → `OrderRequest` の `_frozen_extra` → `values.freeze`、on_event の外)にそのフックが走る。フックが「はい」と答えると `AttributeError` になり、断りが入口の誤り(OrderApiError)にならない。
- 根本原因(私の読み): 作業者の格子は「核のソースが ABC に聞かない」ことを、核のファイルの `isinstance` / `issubclass` / `is_a` を読んで示した(`test_bt0_r14_process_state.py` の説明「the core's source asks no ABC at all」)。核が呼ぶライブラリのコード(Fraction・Decimal の比較)が ABC に聞くことは列の外だった。hash の衝突の試しも FrozenDict と frozenset の組だけで、数の型をまたぐ衝突が無い。
- 格付け: 「信頼性か再現性を崩すもの」に当たるので [止める]。族は i0-r13-01(核の判断がプロセス全体の状態で決まる)で、repeat_of は i0-r13-01。

根拠:
- `PYTHONPATH=src python3 <S>/r14_critic/item0_r14_critic_probe_fraction_decimal_eq.py {none,hook,hook_true,hook_outside_true,register,rerun,account}`(1 つずつ新しいプロセス)→ `none -> ('run ok', [])` / `hook -> ('run ok', [('hook', 'inside', 'Decimal'), ('hook', 'OUTSIDE on_event', 'Decimal')])` / `hook_outside_true -> ("run raised AttributeError: 'decimal.Decimal' object has no attribute 'numerator'", [..., ('hook', 'OUTSIDE on_event', 'Decimal')])` / `run A, fresh process : ('run ok', [])` / `run B (registers Decimal) : ("run raised AttributeError: …")` / `run A again, same input : ("run raised AttributeError: …")` / `account's forced order, strategy registers nothing: run ok` / `account's forced order, strategy registered Decimal with Rational in its on_event: run raised AttributeError: …`(`…_fraction_decimal_eq.out`)。
- 場所: `<S>/r14_critic/item0_r14_critic_probe_eq_sites.out` → `values.settle({Fraction(1): …, Decimal(2**61): …})`・`values.freeze(…)`・`values.settle(frozenset([...]))` が登録のあと全部 `AttributeError`(`fractions.py` 683 行、`Unsettled` でも `ValueError` でもない)。
- 試験(残す。作業者が直す): `tests/bt/critic/item_0/test_i0r14_process_state_through_library_code.py` の 3 件(`test_another_runs_registration_does_not_change_the_same_run` → `the same run in one process: ok before, AttributeError after another run's registration` / `test_the_strategys_registration_does_not_change_the_accounts_forced_order` → `ok without, AttributeError after the strategy's registration` / `test_no_hook_of_the_strategy_runs_outside_its_call_through_numeric_equality` → `ok | ['Decimal']`)。

直すファイル: `src/bot/bt/core/values.py`(集合・辞書を作り直すときに、値自身の `__eq__` を通さずに等しさを決めるか、型をまたいで hash が衝突する数の組を断る)、`src/bot/bt/core/contract.py`(process_state の文)。

### i0-r14-02 [止める](相手: 実装、repeat_of: i0-r13-01、場当たり: いいえ)

**`values.py` の `_make_copier`(948 行)と `_make_rebuilder`(985 行)は、関数の中で `import dataclasses` を実行する(= 実行中に `sys.modules` を読む)。しかも作った copier / rebuilder を、ある carrier の class を初めて写す・取るときに作って、モジュールの表 `_COPIERS`(929 行)・`_REBUILDERS`(964 行)にプロセスの残りの間ずっと置く。** 戦略が自分の 1 回の呼び出しの間だけ `sys.modules['dataclasses']` を自分のモジュールに替えて、次の呼び出しで元に戻すと:

- (a) **黙って誤った値**: 約定の模型が `Fill(…, liquidity="maker")` を返したのに、口座には `liquidity='taker'` で届く(戦略の `fields` が `liquidity` を落とし、作り直しで既定値 "taker" が入る)。断りは出ない。
- (b) **再現性**: その後、同じプロセスで別の実行(何もしない戦略)を走らせても `taker` のまま(新しいプロセスでは `maker`)。戦略は `sys.modules` を元に戻している(`True`)のに、核自身が実行中に作った表が戦略の影響をプロセスの残りに持ち越す。
- (c) **外のコードが走る**: 戦略の `fields` が戦略の呼び出しの外で 7 回走った(OrderRequest・Ack・Fill・FillNotice・OrderAckEvent の copier / rebuilder を作るとき)。
- 契約 `process_state` は「sys.modules or a module's attributes are never read to decide」「made by any party, in any earlier run of the process -- changes no value, refusal or result」と書く。作業者の返り値は「核が型や値を決めるために実行中に引く名前は無い」「numpy の名前の付け替え 10 種と sys.modules の差し替えは、格子で変化 0 を示した」と書き、リードの答えもそれを「測って変化 0 だった」として契約に分けて書くよう求めた。格子が差し替えたのは `sys.modules['numpy']` だけで、`dataclasses` は列の外だった。この指摘は関数の名前の付け替え(契約の「Not covered: rebinding a name the core CALLS」)ではなく、`sys.modules` の中のモジュールの差し替えである。
- 格付け: 黙って誤った値と再現性の崩れで [止める]。族は i0-r13-01 の (d)(`sys.modules` をたどる)で、repeat_of は i0-r13-01。i0-r14-01 と同じ根(作業者の探し方が核のソースの文字列の grep で、実行中に走る物=関数の中の import・遅れて作る表・ライブラリのコードを列べていない)。

根拠:
- `PYTHONPATH=src python3 <S>/r14_critic/item0_r14_critic_probe_lazy_rebuilder_cache.py fresh` → `run B (clean strategy), fresh process : ['maker']`。同 `poisoned` → `run A (its strategy swaps sys.modules['dataclasses'] for one callback): ['taker']` / `sys.modules['dataclasses'] is the real module again: True` / `run B (clean strategy), same process, after run A : ['taker']` / `["strategy's fields() ran inside for OrderRequest", "strategy's fields() ran OUTSIDE its call for OrderRequest", "… OUTSIDE its call for Ack", "… for Fill", "… for Ack", "… for FillNotice", "… for Fill", "… for OrderAckEvent"]`(`…_lazy_rebuilder_cache.out`)。
- 試験(残す): `tests/bt/critic/item_0/test_i0r14_process_state_through_library_code.py::test_a_module_swapped_in_sys_modules_for_one_callback_changes_nothing_in_this_or_a_later_run` → `run A (its strategy swapped sys.modules['dataclasses'] for one callback): taker`。

直すファイル: `src/bot/bt/core/values.py`(核の carrier の class は決まった集まりなので、copier / rebuilder を読み込み時に全部作り、実行中に import しない)、`src/bot/bt/core/contract.py`。

### i0-r14-03 [止める](相手: 実装、repeat_of: null、場当たり: いいえ)

**`to_nanos` は「Conversion is exact」「rounding: none (inputs with sub-nanosecond digits are rejected)」(`time.py` 8 行・63 行)と書くが、Fraction を先に float にし(174 行 `float.__repr__(float(v))`)、numpy の longdouble を `scalar`(162 行。`NUMBER_BASES` の `numpy.floating → float`)で float にしてから正確さを検めるので、値が持つ桁を落とした結果を黙って受け付ける。**

- `to_nanos(Fraction(1700000000123456789), "ns")` → `1700000000123456800`(11 ns ずれる)。`to_nanos(Fraction(1700000000123456789, 10**9), "s")` → `1700000000123456700`(89 ns)。`to_nanos(Fraction(1700000000123456789, 1000), "us")` → `…800`。`np.longdouble('1700000000.123456789')`(この値を持つ。`np.format_float_positional` で確かめた)を "s" で → `…700`。同じ時刻の int は `1700000000123456789` のまま。
- 要件 §1「時刻は UTC の int64 ナノ秒」と観点 P0-2 の「既知の時刻…が同じ int64 ナノ秒と一致するか」に対し、核の唯一の変換口が黙って誤った時刻を返す。前の周からある振る舞いで、前の批評家も場面集も測っていなかった(場面集の P0-2 は ISO と int だけ)。
- 格付け: 「黙って誤った値」で [止める]。新しい族なので repeat_of は null。

根拠: `PYTHONPATH=src python3 <S>/r14_critic/item0_r14_critic_probe_to_nanos_exact.py` → `longdouble holds: 1700000000.123456789` / `to_nanos(longdouble, s) -> 1700000000123456700` / `Fraction exact ns: 1700000000123456789` / `to_nanos(Fraction, s) -> 1700000000123456700` / `to_nanos(Fraction(1700000000123456789), ns) -> 1700000000123456800` / `to_nanos(1700000000123456789, ns) (int, for comparison) -> 1700000000123456789`(`…_to_nanos_exact.out`)。試験(残す): `tests/bt/critic/item_0/test_i0r14_time_values_silently_changed.py::test_to_nanos_is_exact_or_refuses` の 4 件(`gave 1700000000123456700, the value states 1700000000123456789 (off by -89 ns)` ほか)。

直すファイル: `src/bot/bt/core/time.py`(Fraction は分子と分母の整数の計算で正確に、longdouble は正確に変換するか断る)、`src/bot/bt/core/values.py`(時刻の変換が float に狭める前の値を読めるように)。

### i0-r14-04 [止める](相手: 実装、repeat_of: null、場当たり: いいえ)

**`numpy.timedelta64` は `numpy.signedinteger` の子なので、`values.NUMBER_BASES`(269 行)が int と決め、`int()` がその単位での数を返す。単位を持つ長さが、その数のナノ秒として黙って受け付けられる。** 時刻の関門 `validate_nanos`(`time.py` 105 行、121 行 `as_int`)・`values.settle`・差し込み口の答え(`take_int`)の全部で起きる。

- `validate_nanos(np.timedelta64(5, "Y"))` → `5`、`np.timedelta64(5, "M")` → `5`、`np.timedelta64(5000, "fs")`(5 ps)→ `5000`、`np.timedelta64(5, "ps")` → `5`。`values.settle` も同じ。ms・us の小さな数は `int()` が `datetime.timedelta` を経て断られるが、`np.timedelta64(1700000000000000000, "ms")` は `1700000000000000000` として通る(単位によって、また数の大きさによって、断るか黙って数を取るかが変わる)。
- 遅延の模型が `np.timedelta64(5_000, "ps")`(= 5 ns)を返すと、注文は 5000 ns 後に取引所に着く(`OrderAckEvent` が T0 + 5000)。
- 要件 §1「時刻は UTC の int64 ナノ秒」と、差し込み口(遅延模型)の答えに対し、単位の違う値が黙って 1000 倍・年や月の数で入る。前の周から(ABC が numpy の integer を Integral としていたとき)ある振る舞いで、この周に数の種類を表で決め直したときも列の外だった。
- 格付け: 「黙って誤った値」で [止める]。repeat_of は null。

根拠: `PYTHONPATH=src python3 <S>/r14_critic/item0_r14_critic_probe_timedelta_unit.py` → `MRO: ['timedelta64', 'signedinteger', 'integer', 'number', 'generic', 'object']` / `number_kind(timedelta64): <class 'int'>` / `np.timedelta64(5, 'ps') validate_nanos -> 5` / `np.timedelta64(5000, 'fs') validate_nanos -> 5000` / `np.timedelta64(5, 'Y') validate_nanos -> 5` / `np.timedelta64(5, 'M') settle -> 5` / `np.timedelta64(5, 'ms') settle -> raised Unsettled` / `np.timedelta64(1700000000000000000, 'ms') validate_nanos -> 1700000000000000000` / `run ok | what the strategy saw (type, ns after T0): [..., ('OrderAckEvent', 5000), ('OrderFillEvent', 5000), ...]`(`…_timedelta_unit.out`)。試験(残す): `test_i0r14_time_values_silently_changed.py::test_a_duration_with_a_unit_is_not_taken_as_that_many_ns` の 5 件と `test_the_latency_models_delay_in_picoseconds_is_not_taken_as_nanoseconds`(`the order reached the venue [5000] ns after it was sent; the model said 5 ns`)。

直すファイル: `src/bot/bt/core/values.py`(`NUMBER_BASES` で numpy の timedelta64・datetime64 を数と数えない、または単位で正確に換算する)、`src/bot/bt/core/time.py`、`src/bot/bt/core/contract.py`(PLAIN_DATA_RULE と process_state の文)。

### i0-r14-05 [直す](相手: 実装、repeat_of: i0-r13-01、場当たり: いいえ)

**契約 `process_state`(158 行)は入れ子の上限を「the core's own bound, not the recursion limit or the stack depth of the call」と書き、リードの答えは格子 4 を「101 段で落ちるのが RecursionError でなく核の型つきの断り」を示すものとして読んだ(「批評家が読む」)。格子 4 が試した戦略自身の積み上がりは {0, 300} だけで、それより深いところから呼ぶと、上限の中の値でも RecursionError になる。** 戦略が自分の積み上がり 800 から `extra` の入れ子 98 段(MAX_NESTING 100 の中)の注文を出すと `RecursionError: maximum recursion depth exceeded while getting the str of an object`、900 からなら 50 段でも同じ。0・300・600 からは受け付ける。受け付けるか断るかと断りの型(OrderApiError でない)が、呼び出しの積み上がりで変わる。起きるのは戦略自身の呼び出しの中で、黙って誤った値は無く、同じ戦略なら毎回同じなので [直す] とした(i0-r11-01 と同じ「断りの型が契約と違う」の格)。契約の文を事実に合わせるか(核が要る残りの深さを書く)、核の歩きで RecursionError を入口の誤りに替えるかのどちらかが要る。

根拠: `PYTHONPATH=src python3 <S>/r14_critic/item0_r14_critic_probe_stack_depth.py` → `strategy's own depth 600 | extra nesting 98 -> place_order: accepted` / `strategy's own depth 800 | extra nesting 98 -> place_order: RecursionError: maximum recursion depth exceeded while getting the str of an object` / `strategy's own depth 900 | extra nesting 50 -> place_order: RecursionError …`(`…_stack_depth.out`)。試験(残す): `tests/bt/critic/item_0/test_i0r14_nesting_refusal_depends_on_the_callers_stack.py` → `3 failed, 12 passed`(`extra nesting 98 (<= MAX_NESTING 100) from the strategy's stack depth 800: RecursionError; from depth 0: taken` ほか)。

直すファイル: `src/bot/bt/core/values.py`、`src/bot/bt/core/contract.py`。

### i0-r14-06 [直す](相手: 場面集、repeat_of: i0-r11-02、場当たり: いいえ)

**升目の表の P0-2 は「升目 160: 場面にした 0 / 測っていない(固定した測り方の外) 160」で、全升目の判断が「固定した測り方の外」になっている(`DEFINITIONS.md` 163 行〜)。P0-2 の固定した測り方は「値: 既知の時刻…を投入し、核が保持する値が同じ int64 ナノ秒と一致するか」で、場面 p2-iso-utc・p2-iso-offset(ISO 文字列 → int64 ナノ秒)と p2-event-time-exact・p2-one-ns-apart(int64 ナノ秒の事象)はまさにその測り方で測っている。** 0 になったのは、第 r13-1 回の正の定義(F)で升目の事象の型を入力から機械で出すことにし、p2-iso-* は事象を持たず、p2-event-time-* は型を対象が選ぶため、どの升目にも当たらなくなったからである。升目の軸(事象 × 見る道 × 時刻の単位)に「事象の型を入力が決めない場面」「事象を持たない変換の場面」を載せる行が無い。この表は「測っていない範囲の記録」としてオーナーへの報告に渡るので、P0-2 が 1 つも測られていないと読める。向きは通過に不利な側(測った物を測っていない側に置く)で、場面・正解・比較の表のセルは変わらないので [直す] とした。r11-02(升目の判断が場面の測る物と合わない)と同じ族で、向きが逆。F の文どおりの結果なので、場面係は直す前に、F の範囲で「固定した測り方の外」と「測ったが升目の型を入力が決めない」を分ける形があるかを確かめ、無ければリードに聞く(ROOTCAUSE の節「リードに聞くこと」)。

根拠: `sed -n 163,175p tests/bt/battery/item_0/DEFINITIONS.md` → `### P0-2(升目 160: 場面にした 0 / 測っていない(固定した測り方の外) 160)` と、`| 約定 | 戦略の呼び出しに届く物 | int64 ナノ秒 | 測っていない(固定した測り方の外) | — |` ほか。場面の定義は同じファイルの 715-747 行(p2-iso-utc・p2-iso-offset・p2-event-time-exact・p2-one-ns-apart)。

直すファイル: `tests/bt/battery/item_0/grid_c.py`、`tests/bt/battery/item_0/scenes.py`、`tests/bt/battery/item_0/gen_definitions.py`(`DEFINITIONS.md` はそこから作る)。

## 場面集の側で確かめたこと(この周の新しい [止める] は無し)

- `PYTHONPATH=src python3 tests/bt/battery/item_0/gen_definitions.py --check` → `OK`。`python3 scripts/check_bt_considered.py tests/bt/battery/item_0/opponents/CONSIDERED.md` → `OK 誤り 0 件`。
- 場面集は第 13 周の批評家が見た版から、`ROOTCAUSE_r13-1.md` と判断の表 2 つしか変わっていない(`git diff --stat 40c2525 HEAD -- tests/bt/battery/item_0` → 4 files、場面・adapter・runner・検討表・再現の変更なし)。資料係の再利用も指紋が第 13 周と同じことによる(VERDICTS の表 0#14 の notes)。
- 規則 4(動かせた道具は全部の場面に通す): `survey_results/*.tsv` の 54 本は全部 33 行(見出し + 32 場面)。
- 検討表: P0-2・P0-5 の「再現できない(危険)」の行(44・58・120)は道具台帳 §3 の 11 件で、(a) の書き写しの行(SCAN 5889・5890・6061・5874 行)と合っている。P0-1 の「上位互換」のスキップ 4 行(13・57・63・123)と P0-3 の 11 OctoBot の行は、能力ごとに「含む:」の候補と結果の TSV を名指しし、`test_battery_item0.py` が今の出力と照らす(上の 2101 passed に入っている)。
- 限界: 相手の adapter 41 本と再現 1 本を、この周に全部読み直してはいない(第 13 周から変更が無いことを差分で確かめた)。候補 35 の adapter は第 13 周の批評家が読んだ。
- この周の指摘 i0-r14-03・i0-r14-04 の入力(Fraction・longdouble・timedelta64 の時刻)は場面集に無い。P0-2 の固定した測り方は入力の形を決めていないので、場面集の規則違反とはしなかった。場面係が P0-2 に値の場面を足すかは [示唆] の範囲。

## 提出前の吟味(批評家の文)

- 指摘ごとに根拠を自分で再現した。i0-r14-01・02 は ABC の登録と `sys.modules` の差し替えが取り消せないので、試しも試験も 1 つずつ新しいプロセスで走らせた。i0-r14-01 は、フックが戦略の呼び出しの中で先に聞かれて負の覚えに入ると外では聞かれないので、戦略の呼び出しの最後にもう 1 回登録して覚えを消す形にした(最初の版の試しは外で走らず、直した)。試験は 2 回回して同じ落ち方だった。
- 格付け: i0-r14-01・02・03・04 は「黙って誤った値」か「再現性の崩れ」に当たるので [止める]。i0-r14-05 は戦略自身の呼び出しの中で断りの型が変わるだけで、同じ戦略なら毎回同じなので、前の周の同じ格(i0-r11-01・03)に合わせて [直す]。i0-r14-06 は記録の事実の誤りだが、向きが通過に不利で、セルと正解を変えないので [直す]。
- 前の周の指摘の直り: i0-r13-01 の 4 つの形、i0-r11-01・03 は試しと試験で直っていることを確かめた。直ったものは指摘に挙げていない。i0-r13-01 の族の別の形(01・02)は repeat_of で i0-r13-01 を名指した。
- 相手の付け違い: 01〜05 の直す場所は全部 `src/bot/bt/core/` の下で、相手は実装。06 は `tests/bt/battery/item_0/` の下だけで、相手は場面集。06 は実装の欠陥ではない(核は P0-2 の場面を全部通る: 表 0#14 の notes「新実装: 正しさ 32/32」)。
- 場当たりの直しは見つからなかった。作業者の「登録だけの class を断る」は第 13 周の批評家が指定した直し方で、書き直した試験も弱めていない。
- 置いた試験: `tests/bt/critic/item_0/test_i0r14_process_state_through_library_code.py`(4 件、全部落ちる)、`test_i0r14_time_values_silently_changed.py`(10 件、全部落ちる)、`test_i0r14_nesting_refusal_depends_on_the_callers_stack.py`(15 件のうち 3 件落ちる)。落ちるのは全部この周の指摘の根拠で、作業者が直す。
