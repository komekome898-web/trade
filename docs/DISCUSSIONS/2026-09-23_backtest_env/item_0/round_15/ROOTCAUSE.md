# 項目 0「核」第 15 周 — 直す前の根本原因(作業者)

委任文: `docs/DATA/delegations/20260923_backtest_env_prompt.md`(`sha256sum … | cut -c1-12` → `cdf623e4fb24`。起動文の指紋と一致。全 169 行を読んだ)。
合意した完了の形(委任文 §0 の逐語): 「**すべてが調査結果以上の信頼性と再現性に優れたものにすること。**」
固定した要件: `item_0/REQUIREMENTS.md`(変えない)。リードの設計: `round_7/LEAD_DESIGN.md`(§2・§3.1〜§3.4・§9.2・§9.3・§11 を読んだ)。リードの第 14 周の答え: `docs/AUDITOR/VERDICTS/2026-09-23_backtest_env_run11_item0.md` の「リードの答え(作業者 0#14 の問い)」。
一時ファイルは `/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/r15_worker/`(以下 `<W>`)。

## 0. この周に直す対象と、この周の初めに確かめたこと

| id | 格 | 相手 | repeat_of | この周の初めの確かめ |
|---|---|---|---|---|
| i0-r14-01 | 止める | 実装 | i0-r13-01 | `PYTHONPATH=src python -m pytest tests/bt/critic/item_0/test_i0r14_process_state_through_library_code.py tests/bt/critic/item_0/test_i0r14_time_values_silently_changed.py tests/bt/critic/item_0/test_i0r14_nesting_refusal_depends_on_the_callers_stack.py -p no:cacheprovider` → `17 failed, 12 passed in 1.18s`(`<W>/pytest_item0_r15_worker_start.log`)。この指摘の 3 件が落ちる |
| i0-r14-02 | 止める | 実装 | i0-r13-01 | 同じ実行で `test_a_module_swapped_in_sys_modules_for_one_callback_…` が落ちる |
| i0-r14-03 | 止める | 実装 | null | 同じ実行で `test_to_nanos_is_exact_or_refuses` の 4 件が落ちる |
| i0-r14-04 | 止める | 実装 | null | 同じ実行で `test_a_duration_with_a_unit_…` の 5 件と `test_the_latency_models_delay_in_picoseconds_…` が落ちる |
| i0-r14-05 | 直す | 実装 | i0-r13-01 | 同じ実行で `[800-98]`・`[900-50]`・`[900-98]` の 3 件が落ちる |
| i0-r11-01・03 | 直す | 実装 | i0-r9-02 | 第 12 周に直した。第 14 周の批評家が直りを確かめた(`round_14/CRITIC.md`「前の周の指摘の直り」)。この周は構造を変えない |
| i0-r14-06 | 直す | 場面集 | i0-r11-02 | 場面係の持ち物(`tests/bt/battery/`)。作業者は直さない |

## 1. 共通の根(i0-r14-01・02・05): 探し方が「核のソースの文字列」だった

第 14 周の私は「核がプロセス全体の状態を読まない」ことを、核のファイルの `isinstance` / `issubclass` / `is_a` / `sys.` を grep して示した。批評家の指摘 3 件は全部その列の外にある:

- 核が**呼ぶライブラリのコード**が状態を読む(`Fraction.__eq__` の `isinstance(b, numbers.Rational)`、C の decimal の比較の `isinstance(w, Rational)`)。核のソースには ABC の名前が 1 つも出てこない。
- 核が**実行中に初めて走らせる**コード(関数の中の `import dataclasses`、初めて写すときに作って表に残す copier / rebuilder)。grep は「その行が何時走るか」を見ない。
- 核の**歩きの深さ**が呼び手の積み上がりに足される(再帰で書いた歩き)。grep は呼び出しの深さを見ない。

**探し方を替えた(実測)**: 核の全ての入口を 1 回の実行で通す作業量 `tests/bt/item_0/_r15_workload.py` を書き、`sys.setprofile` の下で走らせて、「一番近いライブラリでない枠が核の枠であるときに入った、核の外の Python の関数」と「核が呼んだ C の関数」を全部列べた(`<W>/item0_r15_worker_probe_library_calls.py`、出力 `…_library_calls.out`)。核のソースを読まずに、走ったものを列べる。結果(2 回目の実行。1 回目は遅れて作る表を埋めるので別に数える):

| 走ったライブラリの Python のコード | 回数 | どこから(`…_abc_origin.out`) |
|---|---|---|
| `abc.ABCMeta.__instancecheck__` / `__subclasscheck__` | 1199 / 109 | `Fraction.__eq__` と C の `Decimal` の比較から。`values.py` の `_freeze`・`_settle`・`thaw`・`_renew_frozenset`・`_renew_frozen_set`・`FrozenDict._from_pairs`(集合と辞書を作るときの hash の衝突) |
| `fractions.Fraction.__eq__` / `__hash__` / `__new__` / `numerator` / `denominator` | 545 / 461 / 499 / 111 / 111 | 同じ場所と `_new_fraction`、`_now`(`float(Fraction)` = `numbers.Rational.__float__`) |
| `numbers.Rational.__float__` | 2 | `values.py` `_now` |
| `dataclasses.replace` / `fields` / `_is_dataclass_instance` / `_recursive_repr` | 37 / 18 / 37 / 12 | `api.py` の見え方の更新、`engine.py` の `_settled_request`・`_deliver`(`repr(delivered)`) |
| `enum.Enum.__hash__` / `EnumType.__iter__` | 296 / 5 | 事象の型を鍵にする表(`history.py`・`engine.py`・`ordering.py`) |

そのほかに `Decimal == float` は C のコードがスレッドの十進の文脈に FloatOperation の旗を**書く**(`<W>/item0_r15_worker_probe_misc.out`: `FloatOperation flag after Decimal(1) == 1.0: True`)。核が作る値どうしの比較が、ほかの者の読める状態を書き換える道でもある。

この表のうち、答えがプロセス全体の状態で変わるのは ABC に聞く行(`Fraction` と `Decimal` の等しさ)だけである。`dataclasses` と `enum` のコードは核自身の class の欄と核の Enum の名前しか読まない(名前の付け替えは契約の対象外 = プログラムの変更)。この列べを**試験にする**(下の §6 格子 A): 作業量を走らせ、核の代わりに入ったライブラリのコードが、理由を書いた表の中に収まることを毎回の pytest で確かめる。核が新しいライブラリのコードを呼ぶように変わったら落ちる。

## 2. i0-r14-01(ライブラリの等しさがプロセス全体の状態を読む)

### なぜ起きたか(根本原因)

核が作る平らな値の型のうち、`Fraction` と `Decimal` は、**等しさ(`==`)がライブラリのコードで、そのコードが ABC の登録簿と覚え、ABC の子のフックを読む**(`Fraction.__eq__` は `type(b) is int` 以外の相手で `isinstance(b, numbers.Rational)` と `isinstance(b, numbers.Complex)` を問う。C の decimal は int・float・complex・Decimal 以外の相手で `isinstance(w, Rational)` を問う)。核は集合・辞書を作るたびに(`_freeze`・`_settle`・`renew`・`thaw`・`FrozenDict` の表と hash)、hash の等しい要素どうしをこの `==` で比べさせる。だから、ほかの者の登録やフックが、核の受け付け・断り・結果を決め、フックが持ち主の呼び出しの外で走る。第 13・14 周の直し(「核は ABC に聞かない」)は核自身の判断にだけ当て、**核が作った値の型が持つ判断**を列べていなかった。

同じ根の全箇所(§1 の実行の列べから):
1. `Fraction` と、int 以外の型の値(float・complex・Decimal・str・bytes・None・tuple・frozenset・FrozenDict)の比較 = hash が衝突すれば起きる(`Fraction(P+1)` と `1.0`、`Fraction(hash(s))` と `s` …。`P = sys.hash_info.modulus`)。
2. `Decimal` と、int・float・complex・Decimal 以外の型の値の比較(str・bytes・None・tuple・frozenset・Fraction)。
3. `Decimal` と float・complex の比較がスレッドの十進の文脈に旗を書く。
4. `thaw`(`extra_dict()`)が受け手の呼び出しの中で作る dict / set も同じ比較をする: 戦略の登録で、口座の `extra_dict()` の答えが変わる。
5. `FrozenDict.__hash__` は `hash(frozenset(items))` で項目の組を frozenset に入れるので、組どうしの hash が衝突すると組の中の値を比べる。

### どの構造を変えるか

**核が作る値は、等しさと hash を核自身のコードか組み込みの型の C のコードで持つ**(値だけで決まり、ライブラリのコードも状態も読まない):

- `Fraction` と `Decimal` の値は、核が自分の class **`values.PlainFraction`(`Fraction` の子)・`values.PlainDecimal`(`Decimal` の子)**として作る(`__slots__ = ()`)。`__eq__` / `__ne__` は核の関数 `_number_equal` で、両方の値を正確な有理数(int・float・complex・Fraction・Decimal を MRO の同一性で読み、`float.as_integer_ratio`、Fraction の slot、`Decimal.as_tuple` から)にして比べる。Decimal を含む比較は、呼ぶたびに固定の設定から作る十進の文脈(`time.py` と同じ作り方)の `compare` で行い、スレッドの文脈を読みも書きもしない。`__hash__` は `PlainDecimal` が `Decimal.__hash__`(C、自分の最大の文脈で計算)、`PlainFraction` が核の関数(`Fraction.__hash__` と同じ式を int の演算で。数の hash の約束を守る)。作るときも `Fraction.__new__` を呼ばず、`math.gcd` で約して slot に書く。`float(PlainFraction)` は `int.__truediv__`(正しく丸める)。
- 送り手の `Fraction` / `Decimal`(その子も)は、今と同じく基の型の slot か C の方法で読み、`PlainFraction` / `PlainDecimal` として作り直す。`thaw` も `PlainFraction` / `PlainDecimal` を返す(受け手の dict / set も状態を読まない)。
- `FrozenDict` の hash は、作るときに下から上へ計算して覚える。式は `hash(frozenset(items))` と同じ値のまま(第 14 周の格子の子が `hash(_FD) == hash(_TWIN)` を使う)、組を比べずに作る: 組ごとの `hash(pair)` を、自分の hash だけを返し同一性で比べる小さな物に包んで frozenset にする(CPython の frozenset の hash は要素の hash と個数だけで決まる)。
- 振る舞いの変化: `extra` の中の Fraction / Decimal を受け手が読むと `type(v) is Fraction` ではなく `PlainFraction`(`isinstance(v, Fraction)` は真、演算の結果はライブラリの `Fraction` / `Decimal`)。契約 `PLAIN_DATA_RULE` と `process_state` に書く。

採らなかった案: (a) 型をまたいで hash が衝突する組を断る — 批評家の試験は `{Fraction(1): "a", Decimal(2**61): "b"}` を受け付けることを求めており(`a1 == "ok"`)、正しい Python の dict を断るのは要件から逃げる直しになる。また str の hash はプロセスごとに違うので、断るかどうかが hash の種で変わる。(b) 核の入れ物を hash の表でない形に作り替える — `thaw` が作る受け手の dict / set が残り、`FrozenSet` が `frozenset` でなくなると既存の試験の歩き(`isinstance(v, frozenset)`)が変わる。値の型の等しさを核のものにすれば、核が作る全ての入れ物と `thaw` の答えが同時に閉じる。

## 3. i0-r14-02(実行中の import と、プロセスの残りに残る表)

### なぜ起きたか(根本原因)

`_make_copier` / `_make_rebuilder` は**初めて使うとき**に作られ(関数の中の `import dataclasses` = そのときの `sys.modules` を読む)、モジュールの表 `_COPIERS` / `_REBUILDERS` にプロセスの残りの間置かれた。「核は読み込み時に束ねた物で決める」という第 14 周の規則を、私は numpy の型と数の表にだけ当て、**核自身が遅れて作る物**(関数の中の import、初めて使うときに埋まる表)を列べていなかった。遅れて作る物は、作った時点の状態(誰かが差し替えた `sys.modules`)を焼き付け、後の全ての実行に持ち越す。

同じ根の全箇所: 核の全ファイルの AST で、関数の中の import・`exec`・`eval`・`compile`・`sys.modules` を列べた → `values.py` 948 行と 985 行の `import dataclasses`、960 行と 993 行の `exec` だけ(`<W>` の実行記録は本文の下 §7)。`lru_cache`・`global` は 0 件。実行中に埋まる表は、下の格子 B(読み込みの後の核のモジュールの状態と、作業量を走らせた後の状態を比べる)で機械に列べる。

### どの構造を変えるか

- copier / rebuilder は、**核が読み込まれるときに、核の carrier の class 全部(`contract.PATH_CARRIERS`)について作る**(`values.bind_carriers`。`contract.py` が `PATH_CARRIERS` を決めた直後に 1 回だけ呼ぶ。2 回目は断る)。表は同一性で引く `IdTable` で、作った後は変わらない。表に無い class は核の誤り(`TypeError`)。
- `values.py` は `dataclasses` をモジュールの先頭で import する(読み込み時)。核の関数の中に import を置かない。
- 試験(格子 B): (1) 核の全ファイルの AST に、関数の中の import・`__import__`・`importlib`・`sys.modules` が無い。(2) 作業量を走らせる前と後で、核の全モジュールの大域の名前と、それが指す入れ物の中身(dict・list・set の要素の同一性、`IdTable` の表)と、核の class の辞書が同じ。(3) 批評家の試験(`sys.modules['dataclasses']` の差し替え)を、核が使う全てのモジュール(`dataclasses`・`fractions`・`decimal`・`numbers`・`heapq`・`hashlib`・`math`・`types`・`re`・`datetime`・`bisect`・`enum`・`typing`・`collections.abc`・`numpy`・`sys`)に広げる。

## 4. i0-r14-03・04(時刻と数の変換が値を黙って変える)

### なぜ起きたか(根本原因)

数の種類の表(`NUMBER_BASES`)は**型の種類だけで行き先の型を決め、その行き先の型の構築子で変換した**。これが値を保つかを確かめていなかった:
- 行き先より広い型(numpy の `longdouble`・`clongdouble`)は、`float()` / `complex()` で**丸められる**(`<W>/item0_r15_worker_probe_numpy_kinds.out`: `longdouble … float(v)==v exact? False`、`clongdouble … complex(v) exact? False`)。
- 単位を持つ型(`numpy.timedelta64` は `signedinteger` の子)は、`int()` が**その単位での数**を返す(`int(np.timedelta64(5,'ps'))=5`)。`datetime64` は `generic` の子なので数と数えていなかった。
- `to_nanos` は `Fraction` を先に `float` にしてから正確さを検めた(`time.py` 174 行)。

要件「時刻は UTC の int64 ナノ秒」と `TIME_CONTRACT` の「rounding: none」、`freeze` の「An equal … form」は、変換が値を保つことを前提にしていたのに、変換の結果を元の値と照らす所が無かった。

同じ根の全箇所: numpy の全ての数の class を numpy 自身の表(`np.sctypeDict`)から列べた(`…_numpy_kinds.out`): int8〜int64・uint8〜uint64・longlong・ulonglong(int に正確)、float16・float32・float64(float に正確)、complex64・complex128(complex に正確)、**longdouble・clongdouble(丸める)**、**timedelta64(単位を落とす)**、datetime64・bool・str_・bytes_・void・object_(数でない)。Python の型: `Fraction` → `to_nanos` だけが float を通す。`take_float` / `as_float` の `Fraction` → float は float の欄の宣言どおりの丸め(欄が float と決まっている)。

### どの構造を変えるか

- 数の種類の表の規則を「**正確に変換する、できなければ断る**」にする: `timedelta64` と `datetime64`(単位を持つ数)は数と数えない(読み込み時に束ねた class を MRO の同一性で除く)。`longdouble` と `clongdouble` は変換の後に、元の値と変換した値の正確な整数比(`as_integer_ratio`、numpy の C のコード)を比べ、違えば断る。int と float16/32/64・complex64/128 は変換が正確なので今のまま。
- `to_nanos` は受け付ける値をどれも正確な有理数で換算する: int と `PlainFraction` は int の演算(分子 × 倍率が分母で割り切れなければ「ナノ秒より細かい桁」として断る)、float は今の約束どおり最短の十進表記、文字列と `PlainDecimal` は固定の文脈の十進。float を通すのは float だけ。
- 試験(格子 C): 値の型(numpy の全ての数の class・int・float・Fraction・Decimal・文字列)× 単位(s・ms・us・ns)× 入口(`to_nanos`・`validate_nanos`・事象の時刻・遅延の答え・`set_timer`・`freeze`)× 値(正確に表せる物・表せない物・単位つきの長さの全ての単位)で、神託 =「値が言うナノ秒の int と同じ、または断る」「平らな値は元の値と正確に等しい、または断る」。

## 5. i0-r14-05(断るかどうかが呼び手の積み上がりで変わる)

### なぜ起きたか(根本原因)

核の歩き(`_freeze`・`_settle`・`renew`・`thaw`)は再帰で書いてあり、1 段に 1〜3 枠を使う。インタプリタの再帰の上限は**呼び手の枠と核の枠の和**に掛かるので、入れ子の上限(`MAX_NESTING`)で段数を抑えても、呼び手が深いところから呼べば上限の中の値でも `RecursionError` になる。第 14 周の格子 4 は呼び手の深さを {0, 300} しか試さず、「核の上限は再帰の上限に依らない」と書いた契約の文の根拠が足りなかった。

同じ根の全箇所: 核の再帰の歩き = `_freeze`・`_settle`・`renew`(`_renew_tuple` ほか)・`thaw`・`FrozenDict.__hash__`(入れ子の `FrozenDict` の hash が Python の枠を積む)。ほかに、インタプリタ自身の再帰: hash の等しい別々の入れ子の値を 1 つの集合・辞書に入れると、インタプリタの C の比較が入れ物 1 段ごとに再帰の上限を 1 つ使う(`<W>/item0_r15_worker_probe_misc.out`: 98 段の `(((-1,),),…)` と `(((-2,),),…)` は hash が等しく、`frozenset` にすると深さ 850 では作れ、900 では `RecursionError`)。

### どの構造を変えるか

- 核の歩きを全部**反復**(明示の積み上げ)にする: `_freeze`・`_settle`・`renew`・`thaw` を 1 つの反復の道具で書き、段数によらず決まった枠しか使わない。
- `FrozenDict` の hash は作るときに下から計算して覚える(§2)ので、hash を取っても Python の枠は積まれない。
- 残るのはインタプリタ自身の比較の再帰(hash の等しい**別々の入れ子の値**が同じ集合・辞書に入るときだけ)。核はこれを避けられない(Python の集合は hash の等しい要素を必ず `==` で比べる)。核の値を作る入口でこの `RecursionError` を捕まえ、入口の誤り(`ValueError` → 呼び手の誤りの型)にし、契約に「残り」として事実を書く(核の歩きは段数によらず K 枠 = 実測、インタプリタの比較は hash の衝突した入れ子の値だけで 1 段 1 枠)。これを完全に閉じる案(核の tuple・frozenset を、平らな鍵で比べる核の class にする)は、`extra` の tuple / frozenset の型を変えるので、この周は作らずリードに聞く。
- 試験(格子 D): 呼び手の積み上がりを「インタプリタの再帰の上限までに残る枠(headroom)」で数える(pytest の枠の数に依らないため。書いたときの予定は深さ {0, 300, 600, 800, 900, 940} だったが、pytest 自身の枠で 940 が上限を越えるので、残りの枠に替えた)。残りの枠 {CALL_FRAMES, CALL_FRAMES+5, 60, 200} × 入れ子 {1, 10, 50, MAX_NESTING-2, MAX_NESTING, MAX_NESTING+1} × 入れ物(list・tuple・dict・入れ子の tuple を持つ set・dict の鍵の中に入れ子の FrozenDict)× 入口(freeze・settle・renew・thaw・on_event の中の place_order・on_event の中の order() と extra_dict())。神託 = 積み上がりが空のときと同じ結果(受け付けるか、入口の誤りで断るか)。hash の衝突した入れ子の値(`(((-1,),…)` と `(((-2,),…)` の frozenset)は「残り」として別の試験で、残りの枠が少ないときも `RecursionError` でなく入口の誤りになること、CALL_FRAMES + 段数 + 30 の枠があれば空のときと同じことを確かめる。

## 6. 先に書く敵対者の試験(委任文 §3「提出前の吟味」(6))

`tests/bt/item_0/test_bt0_r15_library_code.py`(補助: `_r15_workload.py`、子のプログラム `_r15_state_child.py`)。入力の空間は実装の場合分けから作らない:
- **格子 A(走ったものの列べ)**: 作業量を `sys.setprofile` の下で走らせ、核の代わりに入った核の外の Python の関数の集合 ⊆ 理由を書いた表。表に ABC・`importlib`・`decimal` の文脈の関数は入れない。
- **格子 B(プロセスの状態 × ライブラリのコードの道)**: 状態の変更 = `numbers` と `collections.abc` の全ての ABC × {作業量が使う全ての型を登録 / True を返すフックの子(負の覚えを消してから)}、十進の文脈(精度・丸め・罠・FloatOperation の罠・capitals)、`sys.modules` の核が使う全てのモジュールを 1 回の呼び出しの間だけ差し替え。場所 = 作業量の全て(戦略の `extra`、口座の強制注文、出口の箱の作り直し、受け手への写し、`extra_dict()`、hash の衝突する組の全ての型の対 = `colliding_pairs()`)。神託 = 新しいプロセスの実行と同じ結果、持ち主の呼び出しの外で変える者のコードが 0 回、スレッドの十進の旗が核の比較で立たない。1 つの変更を 1 つの新しいプロセスで。
- **格子 B'**: 核のモジュールの状態が作業量の前後で同じ・関数の中の import が無い(§3)。
- **格子 C・D**: §4・§5 のとおり(格子 D は §5 の最後の項の形で書いた)。

## 7. 厳しい批評家が [止める] にしそうな点(返す前に潰す一覧)

1. `PlainFraction` / `PlainDecimal` は「核が作る物は組み込みの型そのもの」に反しないか → 欄(`as_text` ほか)は今も組み込みの型そのもの。`extra` の平らな値は既に核の class(`FrozenList`・`FrozenDict`・`FrozenSet`)を含む。契約の文を書き替え、受け手が読める形(`isinstance(v, Fraction)`、演算の結果)を試験で縛る。
2. 核の `_number_equal` が Python の数の等しさと違う答えを出さないか → 格子 A の補助に、素のプロセスで、全ての型の対 × 値(0・-0.0・1・大きな値・分数・inf・nan・大きな指数の Decimal)について `_number_equal(a, b) == (a == b)` を確かめる試験を置く(signaling NaN は Python が断るので除き、核は「等しくない」と決める = 列べて書く)。
3. 大きな指数の Decimal(`Decimal('1E+999999999')`)で比較が止まらないか → 比較は十進の文脈の `compare` で行い、巨大な int を作らない。試験に入れる。
4. `RecursionError` を捕まえる直しは場当たりではないか → 核の歩きは反復にして(捕まえるのはインタプリタの比較の残りだけ)、残りの範囲を契約と試験で固定する。
5. 速さ → 直した後に第 14 周と同じ測り(`<W>/item0_r14_worker_speed.py` の形)で測って書く。

## 7'. 返す前に潰した点(§7 の結果)

1. `PlainFraction` / `PlainDecimal` と「組み込みの型そのもの」: 欄は今も組み込みの型そのもの。契約 `channel_payloads.rule` に「平らな値の Fraction / Decimal は核の PlainFraction / PlainDecimal」と書き(contract.py 229 行)、`PLAIN_DATA_RULE` にも書いた。受け手の読み方(`isinstance(v, Fraction)`、演算の結果)は `test_fractions_and_decimals_read_back_as_the_cores_own_subclasses` で縛った。
2. 核の等しさと Python の等しさ: `test_the_cores_number_equality_is_pythons_in_a_clean_process`(15 の値 × 36 の相手 × 両向き・`!=`・hash)。ライブラリ自身が答えられない対(C の decimal と numpy の整数: `Decimal('0.5') == np.int64(100)` がライブラリで `TypeError`)は、核が例外を出さずに真偽を返すことだけを確かめる。signaling NaN はライブラリの答えが文脈の罠で変わるので、核は「等しくない」と決め、罠を外しても同じことを `test_a_signaling_nan_…` で確かめた。
3. 大きな指数の Decimal: `Decimal('1E+999999')`・`Decimal('1E-999999')` を等しさの試験に入れた(十進の文脈の `compare` で比べ、巨大な int を作らない)。
4. `RecursionError` を捕まえる所: 核の歩きは反復にしたので、捕まえるのはインタプリタの比較の残り(hash の衝突した別々の入れ子の値)だけ。範囲は `test_colliding_nested_values_…` と契約の文で固定した。
5. 速さ: §8。
6. 追加で見つけて直したもの(同じ族): (a) 核が作った Decimal の `str` / `repr` / `f"{}"` がスレッドの文脈の `capitals` を読む(ライブラリの `Decimal.__str__`)。別の者が文脈を変えると受け手が読む文字が変わるので、核の文脈で書く形にした(`test_the_text_of_a_decimal_the_core_built_…`)。書式を指定した整形(`format(d, '.2f')`)はライブラリの定義で文脈の丸めを使う = 読み手が自分の呼び出しで選ぶ物として残し、class の説明に書いた。(b) 送り手の dict / 集合では別々だった鍵が、核が作り直すと等しくなる場合(送り手の float の子が `__eq__` を常に偽にしたもの)、以前は黙って 1 つにまとめていた(値が 1 つ消える)。断る形にした(`_dict_of` / `_set_of`、`test_keys_distinct_for_the_sender_but_equal_as_plain_data_are_refused_not_merged` 9 件)。
7. 事象の型の表を hash の順に回していないか(Enum の hash は名前の str の hash で、プロセスごとに種が違う): 核が表を作るときは `for t in EventType`(Enum の定義順。history.py 213-217・245・262 行、api.py 593 行)。事象の型の集合(`MARKET_EVENT_TYPES` ほか)を回すのは contract.py 34-36 行の `sorted(...)` だけで、ほかは所属の判定(`grep -n "for .* in .*_TYPES\|set(\|frozenset(" src/bot/bt/core/*.py` の出力を 1 行ずつ読んだ)。

## 8. 直したあとの確かめ(コマンドと出力)

直した場所(ファイル:行は直した後の作業木):
- i0-r14-01: `src/bot/bt/core/values.py` の `PlainFraction`(357 行)・`PlainDecimal`(369 行。`str` / `repr` / 空の書式も核の文脈で書く = 受け手が読む核の値の文字がスレッドの `capitals` に従わない)・`_number_equal`(307 行)・`_number_parts`・`_decimal_equal`・`_fraction_hash`・`_make_fraction`・`exact_context`・`_new_decimal`、BUILD に 2 つの class を足した表、`FrozenDict` の `_pairs_hash` / `_HashOnly` / `_fd_fill`(hash を作るときに組を比べずに計算)。`thaw` も `PlainFraction` / `PlainDecimal` を返す。
- i0-r14-02: `values.py` の `bind_carriers`・`_CARRIER_TABLES`(IdTable 2 つ)・`copy_carrier`・`rebuild_carrier`・`_make_copier` / `_make_rebuilder`(`_dataclasses` は先頭で import、コードは `<bot.bt.core.values copier of …>` の名前で compile)。`src/bot/bt/core/contract.py` が `PATH_CARRIERS` の直後に `bind_carriers(PATH_CARRIERS)` を 1 回呼ぶ。
- i0-r14-03・04: `values.py` の `UNIT_CLASSES`・`number_kind`(単位を持つ型は None)・`_exactly_converted` / `_same_real`(`longdouble` / `clongdouble` の整数比を照らす)・`_now`(正確でなければ断る)・`fraction_float` / `decimal_float`。`src/bot/bt/core/time.py` の `to_nanos`(`PlainFraction` は int の演算、十進の演算は全部 `exact_context()` の `compare` / `quantize` / `to_sci_string`)。
- i0-r14-05: `values.py` の `_walk`(明示の積み上げの反復)と、それを使う `freeze` / `settle` / `renew` / `thaw`、`CALL_FRAMES = 30`、`_recursion_text`。
- 契約: `contract.py` の `process_state`(測って変化 0 だったものと、測っていない対象外を分けて書いた = 第 14 周のリードの答えの条件)・`channel_payloads.rule`・版 `core-16`。`PLAIN_DATA_RULE`(values.py)。`src/bot/bt/core/__init__.py` が `PlainFraction` / `PlainDecimal` を公開する。

確かめ:
- 第 14 周の批評家の試験 3 本 + 第 13 周の 1 本 + 第 11 周の 3 本: `PYTHONPATH=src python -m pytest tests/bt/critic/item_0/test_i0r14_process_state_through_library_code.py tests/bt/critic/item_0/test_i0r14_time_values_silently_changed.py tests/bt/critic/item_0/test_i0r14_nesting_refusal_depends_on_the_callers_stack.py tests/bt/critic/item_0/test_i0r13_process_global_state_decides_core_values.py tests/bt/critic/item_0/test_i0r11_class_dict_key_runs_foreign_code.py tests/bt/critic/item_0/test_i0r11_pinned_dropped_facts_fail_the_core_step.py tests/bt/critic/item_0/test_i0r11_history_limit_exact_refusal.py -p no:cacheprovider` → `59 passed in 3.76s`(`<W>/pytest_item0_r15_worker_critic_after.log`)。直す前は第 14 周の 3 本が `17 failed, 12 passed`。
- 新しい格子(§6): 直す前 `167 failed, 942 passed`(`<W>/pytest_item0_r15_worker_prefix.log`。落ちたのは格子 A の 2 件、格子 B の numbers の ABC 8 通りと `sys_modules:dataclasses`、十進の旗、格子 B' の 2 件、格子 C の 94 件、格子 D の 42 件ほか)。直した後、第 14 周の格子と合わせて `1213 passed`(`<W>/pytest_item0_r15_worker_grids_after.log`)。
- 核の入口が要る枠(`<W>/item0_r15_worker_probe_headroom.out`): freeze 12・settle 12・renew 12・thaw 9・on_event の中の place_order 22・order() と extra_dict() 11(入れ子 1〜101、入れ物 5 種の最大)。hash の衝突した別々の入れ子の値: 10 段 18、50 段 58、98 段 106。
- 速さ(第 14 周と同じ測り `<W>/item0_r15_worker_speed.py`、2 万本の足、ほかの試験と同時): HEAD `66.50` / `65.21` us/bar、この周 `64.80` / `65.60` us/bar(`<W>/item0_r15_worker_speed.out`)。
- 書き直した前の周までの自分の試験(消した試験は無い): `test_bt0_r8_sender_adversary.py`(核が作る型の表 `_CORE_BUILT` の `Fraction` / `Decimal` を `PlainFraction` / `PlainDecimal` に替えた = 核がもう作らない型を外したので弱めていない。`type(...) is Fraction` の 2 行も同じ)、`test_bt0_values.py`(`_builtin_only` の型の表を同じく)、`test_bt0_r14_process_state.py` と子 `_r14_state_child.py`(契約の版 `core-16`。格子 2 の「ABC と同じ答え」から numpy の単位を持つ 2 つの class を外し、外した物がちょうど `timedelta64`(ABC は int、核は数でない)と `datetime64`(どちらも数でない)であることを試験で確かめる)。
- 核が実行中に入るライブラリのコード(項目 0 と批評家の試験の全部を `sys.setprofile` の下で走らせた。読み込み時の枠は除く。`<W>/item0_r15_worker_profile_plugin.py`): 直す前(`<W>/item0_r15_worker_profile_runtime_before.tsv`)は `fractions.Fraction.__new__` 1053 回・`__hash__` 56・`numerator` / `denominator` 65・`numbers.Rational.__float__` 65 と、実行中に作る copier / rebuilder(`<string>` の `copier` 4,464,001 回ほか)。直した後(`<W>/item0_r15_worker_profile_runtime_after.tsv`)は `fractions.Fraction.__hash__` 5 回だけで、出所は試験のコードが自分の呼び出しの中で公開の `FrozenDict(...)` をライブラリの Fraction で作った所(`<W>/item0_r15_worker_sites.tsv`: `values.py:1223 _pairs_hash`)。ほかは `dataclasses`(`replace` ほか)・`enum`(`Enum.__hash__` ほか)・核の class のために読み込み時に書かれたコード(`<string>` の `__init__` / `__repr__` / namedtuple の `__new__`)で、どれも格子 A の表に理由を書いた。`Field.__init__`・`_EnumDict.__setitem__`・`abstractmethod` は核の class の本体(engine.py 223-237 行 `EngineResult`、api.py 247-254 行 `OrderState`、events.py 52-64 行 `EventType`、strategy.py 11 行)が読み込み時に 1 回ずつ走らせたもの。
- 項目 0・批評家の試験(最後の版): `PYTHONPATH=src python -m pytest tests/bt/item_0 tests/bt/critic/item_0 -p no:cacheprovider -rf` → `3080 passed, 2 skipped, 1 warning in 428.64s (0:07:08)`(`<W>/pytest_item0_r15_worker_final.log`)。
- 全試験(場面集を含む。場面集はこの 1 回だけ回した): `PYTHONPATH=src python -m pytest -p no:cacheprovider -rf`(切り離して)→ `6199 passed, 6 skipped, 2 warnings in 950.89s (0:15:50)`(`<W>/pytest_item0_r15_worker_full.log`)。その後に変えたのは試験のファイル 1 本(格子 A の表に `enum` の 3 行を足した)だけで、その試験は `1120 passed`(`<W>/pytest_item0_r15_worker_grid_final.log`)。

