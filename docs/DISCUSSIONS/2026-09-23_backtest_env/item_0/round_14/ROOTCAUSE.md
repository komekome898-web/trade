# 項目 0「核」第 14 周 — 直す前の根本原因(作業者)

委任文: `docs/DATA/delegations/20260923_backtest_env_prompt.md`(`sha256sum … | cut -c1-12` → `cdf623e4fb24`。起動文の指紋と一致。全 169 行を読んだ)。
合意した完了の形(委任文 §0 の逐語): 「**すべてが調査結果以上の信頼性と再現性に優れたものにすること。**」
固定した要件: `item_0/REQUIREMENTS.md`(変えない)。リードの設計: `round_7/LEAD_DESIGN.md`(§2・§3.1〜§3.4・§9.2・§9.3 を読んだ)。
一時ファイルは `/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/r14_worker/`(以下 `<W>`)。

## 0. この周に直す対象と、この周の初めに確かめたこと

| id | 格 | 相手 | repeat_of | この周の初めの確かめ(コマンドと出力) |
|---|---|---|---|---|
| i0-r11-01 | 直す | 実装 | i0-r9-02 | `PYTHONPATH=src python -m pytest tests/bt/critic/item_0/test_i0r11_class_dict_key_runs_foreign_code.py tests/bt/critic/item_0/test_i0r11_pinned_dropped_facts_fail_the_core_step.py tests/bt/critic/item_0/test_i0r11_history_limit_exact_refusal.py tests/bt/critic/item_0/test_i0r13_process_global_state_decides_core_values.py -p no:cacheprovider` → `7 failed, 23 passed in 1.68s`(`<W>/pytest_item0_r14_worker_start.log`)。通った 23 件が i0-r11 の 3 本。第 13 周の批評家も直りを確かめた(`round_13/CRITIC.md`「前の周の指摘の直り」) |
| i0-r11-03 | 直す | 実装 | i0-r9-02 | 同じ実行の中で `test_i0r11_pinned_dropped_facts_fail_the_core_step.py` が通る |
| i0-r13-01 | 止める | 実装 | i0-r11-01 | 同じ実行で `test_i0r13_process_global_state_decides_core_values.py` の 7 件が全部落ちる(落ち方は批評家の記録と同じ: `('ok', [0.0])` / `['hook']` / `[('OrderApiError', []), ('TimestampUnitError', ['Foo.__bool__'])]`) |

i0-r11-01・03 は第 12 周に直した構造(`values.py` の `IdTable`・`class_parts`、`engine.py` の `_show`、`history.py` の `DroppedFacts`)のままで、この周は変えない。

## A. i0-r13-01(核の数の判断が、プロセス全体で共有された状態で決まる)

### なぜ起きたか(根本原因)

第 12 周の規則は「持ち主の呼び出しの外で、核がその者の物について決めることは、核が作って誰にも届かない物か、静的な(C の)型だけで決まる」だった。私はこの規則を**核が触る物**(渡された値とその class)について確かめ、**核の判断が読む状態**については確かめなかった。`issubclass(numpy.float32, numbers.Integral)` に渡す物は静的な型だけだが、答えは ABC の登録簿と覚え(`numbers.Integral` の登録・正と否定の覚え・全 ABC で 1 つの無効化の数)から読まれ、ABC の子の class のメタクラスのフックにも聞く。これはどの者も公開の API(`register`、class の定義)で実行中に変えられる状態で、変えた結果はプロセスの残りの全ての実行に残る。`_numpy_bool` の `sys.modules['numpy'].bool_` も、settle のたびに読むモジュールの属性である。

第 12 周の格子の軸は「外の者が渡す物 × その物の方法」で、「核の判断が読む、プロセス全体の状態」という軸が無かった(LEAD_DESIGN §2 と同じ形: 扱う物の一覧の外)。そのうえ第 12 周の契約は、ABC のフックを「class を定義することはプログラムを変えること」として対象外に書いた。登録は状態の変更であり、第 11・12 周の格子は戦略が定義する class を範囲に入れていたので、この理由は合っていなかった(批評家の指摘のとおり)。

第 12・13 周で見つけられなかった理由: 私の試験自身が、数でない class を数にするために ABC に**登録していた**(`tests/bt/item_0/test_bt0_sender_types.py:352`、`tests/bt/item_0/test_bt0_r11_foreign_objects.py:924`)。登録簿を「数を決める仕組み」として使っていて、「ほかの誰が登録できるか」を問わなかった。第 13 周に (c) のフックを見つけたときも、対象外の文の中の話としてリードに聞いた。

### 同じ根の全箇所(探し方と実測)

探し方: 核の全ファイルで `issubclass(`・`isinstance(`・`is_a(` の第 2 引数が ABC のもの、`sys.` の読み、実行中に読むほかのモジュールの属性を grep し、さらに「核の計算が読むプロセス全体の設定」(十進の文脈、int と文字列の桁の上限、再帰の上限)を 1 つずつ試した。

| # | 箇所 | 読む状態 | 実測(`<W>` のファイル) |
|---|---|---|---|
| 1 | `values.py` `_settle`(470-476 行) | 数の ABC の登録・覚え・フック | 批評家の (a)(b)(c)。手数料 0.75 → 0.0、遅延 1.5 が 1 ns で通る、同じ実行の結果が変わる |
| 2 | `values.py` `_plain_scalar`(381-386 行) | 同上(送り手の呼び出しの中だが、登録簿はほかの者と共有) | 批評家の (a)。約定の報告の価格 100.5 → 100.0 |
| 3 | `values.py` `_numpy_bool`(322-325 行) | `sys.modules['numpy'].bool_` を毎回読む | 批評家の (d)。`Foo.__bool__` が on_event の外で走り、断りが TimestampUnitError に変わる |
| 4 | `engine.py:763`・`ordering.py:189` `is_a(events, Mapping)` | `collections.abc.Mapping` の登録・フック | `item0_r14_worker_probe_other_global_state.out`: 前の実行の戦略が `Mapping.register(list)` → 後の実行の構築が `('raised', 'AttributeError')`。フックの形 → 後の実行の呼び手の構築の中で前の戦略のフックが走る(`['hook ran']`) |
| 5 | `time.py` `to_nanos`(`dec * factor`) | スレッドの十進の文脈(精度・丸め・罠) | 同じファイル: 戦略が `decimal.getcontext().prec = 5` にした後、`to_nanos(Decimal("1700000000.123456789"), "s")` が `1700000000123456789` → `1700000000000000000`(黙って誤った値) |
| 6 | 大きな int を文にする所(`values.py` `_arg_text`、`time.py` `validate_nanos`・`_check_plausible`、`engine.py` `_check_delay`・`_push`、`api.py` `_count_arg` ほか) | int と文字列の桁の上限(プロセスの設定。既定 4300 桁) | `item0_r14_worker_probe_other_global_state.out`: 戦略が 5000 桁の int を持つ例外を投げると、2 回目の `run()` が `ValueError`(EngineFailedError でない)。`item0_r14_worker_probe_limits.out`: `validate_nanos`・`to_nanos`・`BarEvent`・`set_timer` が 5000 桁の int で `ValueError`(入口の誤りでない) |
| 7 | 入れ子の値を辿る所(`freeze`・`_settle`・`renew`・`thaw`) | 再帰の上限とその時の積み上がりの深さ | `item0_r14_worker_probe_depth.out`: `extra` の入れ子 600 段で `place_order` の中が `RecursionError`(OrderApiError でない)。`item0_r14_worker_probe_limits.out`: 出口の箱の 10 万段で on_event の外が `RecursionError`。受け付けるかどうかが値ではなく積み上がりで決まる |

作業中に先に書いた格子(下の「先に書く敵対者の試験」)が見つけた、同じ根の残り 2 つ(直す前に落ちることを確かめてから直した):

| # | 箇所 | 読む状態 | 実測(`<W>` のファイル) |
|---|---|---|---|
| 8 | `values.py` `FrozenDict`(`Mapping` から継いだ `__eq__`) | `Mapping.__eq__` が `isinstance(other, Mapping)` を問う = Mapping の登録簿。核が辞書・集合を組むとき、hash が衝突した鍵どうしで呼ばれる(`FrozenDict` の hash は項目の frozenset の hash と同じなので、その frozenset と必ず衝突する) | `item0_r14_worker_probe_frozendict_eq.out`: 継いだ `__eq__` のままだと、戦略が `Mapping.register(frozenset)` した後、`freeze`・`settle`・`place_order` の `extra`・出口の箱の 16 か所すべてが `AttributeError` に変わる(`changed cells: … 16 of 16`)。直した後は `0 of 16` |
| 9 | `values.py` `_new_str`(`str.encode(…, "surrogatepass").decode(…, "surrogatepass")`) | codecs の誤りの処理の登録簿(`codecs.register_error`)。孤立したサロゲートの復号で引かれる | `pytest_item0_r14_worker_after5.log`: `test_a_change_of_process_state_changes_nothing_the_core_decides[codecs_error:surrogatepass]` が落ちる(`hooks_in_core` に戦略の処理が 3 回)。直した後は `pytest_item0_r14_worker_after6.log` で 94 件通る |

直し: 8 は `FrozenDict.__eq__` を自分で持ち、相手の型を `is_mapping`(MRO の同一性)で決める。9 は `_new_str` を `str` 自身の切り出しと連結で作り、符号化を使わない。

付随(同じ族の断りの型): `freeze` は辞書の鍵ごとに `where` の文を `{k!r}` で先に作る(`values.py` 691-692 行)。送り手の鍵の `__repr__` が走り、それが投げるか大きな int なら、断りが入口の誤りにならない。

### どの構造を変えるか

規則を次に替える: **核が受け付ける・断る・計算する物は、値そのものと、核が読み込まれたときに束ねた物だけで決まる。核は実行中に、プロセス全体の状態(ABC の登録簿と覚え、`sys.modules` とモジュールの属性、十進の文脈、桁の上限、再帰の上限と積み上がり)を読んで判断しない。**

1. **数の種類**(1・2): `values.py` に読み込み時の表 `NUMBER_BASES` を置く。`numbers.Integral → int`、`numbers.Real → float`、`numbers.Complex → complex`(継承だけで数える)と、numpy が自分で登録する基の型(`numpy/_core/numerictypes.py` 627-629 行: `numbers.Integral.register(integer)`・`numbers.Complex.register(inexact)`・`numbers.Real.register(floating)`)を同じ順で。型の MRO を `type` の欄で読み、表の型と同一性で比べる(`number_kind`)。登録簿は読まない。`_settle`(静的な型だけ)と `_plain_scalar` の両方がこの 1 つの関数を使う。
   - 素のプロセスでの等価性: `item0_r14_worker_static_number_classes.out` = numpy・pandas・核を読み込んだプロセスの全ての静的な型のうち、ABC が数と答えるものは numpy の型と組み込みの型だけで、表の答えと違うのは `numpy.inexact`(抽象で値を作れない)だけ。表に `inexact` を入れて一致させる。
   - 振る舞いの変化: 継承せずに登録だけした Python の class(`numbers.Real.register(X)`)は数と数えない(断る)。numpy 以外の C の数の型は、この環境には無い(上の列べで 0 件)。あれば断る。契約と規則の文に書く。
2. **numpy の型**(3): `values.py` が読み込み時に `numpy` を import する(依存に既にある: `pyproject.toml` 15 行 `"numpy>=1.24"`)。`numpy.bool_` とその `__bool__`、`integer`・`floating`・`inexact` をそのとき束ね、静的な C の型でなければ読み込みを止める(読み込みの前に書き換えられた numpy は使わない)。実行中は `sys.modules` を読まない。
3. **写像の判断**(4): `values.is_a` を `issubclass` から MRO の同一性の歩きに替える(核の型・組み込みの型では同じ答え)。写像かどうかは `values.is_mapping` = MRO に `dict`・`types.MappingProxyType`・`collections.abc.Mapping` のどれかがあるか。素のプロセスでの等価性: `item0_r14_worker_mapping_classes.out` = ABC の答えと食い違う class は 0 件。
4. **十進の文脈**(5): `time.py` に読み込み時の文脈 `_DECIMAL`(最大精度・偶数丸め・罠つき)を置き、`to_nanos` の変換・掛け算・整数判定を全部それで行う。int に直す前に桁の大きさ(`adjusted()`、文脈を読まない)で範囲の外を断る(`"1e999999999"` のような文で巨大な int を作らない)。
5. **int の文**(6): `values.int_text` = 桁の上限の最小値(640 桁)より短い int(2000 ビット以下 = 603 桁以下)は `int.__repr__`、長い int は「an int of N bits」。核の文が送り手の int を載せる所は全部これを使う(`_arg_text` を通す所を含む)。
6. **入れ子の深さ**(7): 平らな値の入れ子の上限 `MAX_NESTING = 100` を核に固定し、`freeze`・`_settle` が辿る道の上の容器の数で数えて、超えたら `ValueError`(呼び手が入口の誤りに包む)。値の根拠: 1 段あたりの積み上がりは最大 3 フレーム(`renew`)、核が on_event を呼ぶ深さは呼び手から 6、実行の中の最も深い組み立ては 20(`item0_r14_worker_frames.out`)。100 段で約 320 フレームで、既定の再帰の上限 1000 の半分に収まり、呼び手と戦略に残りを残す。C の中の hash・`==` も入れ子で深くなるので、Python の歩きを反復に書き換えるだけでは足りず、上限が要る。
7. **付随**: `freeze` の `where` の文は鍵の `repr` を使わず、`_arg_text`(送り手のコードを走らせない)で作る。
8. **契約**(`contract.py` の scope): 「対象外」から ABC のフックの文を消す。新しい欄 `process_state` に上の規則を書く。対象外は「モジュールの名前の付け替え(組み込み・ライブラリ・核の関数を別の物にすること = プログラムのコードを変えること)、解釈系のフック(`sys.settrace`・`setprofile`・監査のフック・gc の知らせ・信号・戦略が立てたスレッド)、核が要る深さより低い再帰の上限、メモリ」に限る。核が型や値を決めるために実行中に名前を引く所は無い(数の表・numpy の型・十進の文脈は読み込み時に束ねる)ので、付け替えで変わるのは核が呼ぶ関数のコードだけである。

### 先に書く敵対者の試験(委任文 §3「提出前の吟味」(6))

`tests/bt/item_0/test_bt0_r14_process_state.py`。入力の空間は実装の場合分けからではなく、**プロセスの状態の側**から列べる:
- 状態の変更 = `numbers` の全 ABC と `collections.abc` の全 ABC(モジュールの `__all__` から機械で)× {値の型を全部登録する / メタクラスのフックが True を返す子を作る}、十進の文脈(精度 1・丸め・罠を外す)、桁の上限 640、numpy の名前の付け替え(`bool_`・`integer`・`floating`・`inexact`・`float32`)、`sys.modules['numpy']` の差し替え。1 つの変更を 1 つの新しいプロセスで(登録は取り消せない)。
- 場所 = 核が値を決める全ての入口(差し込み口の答え: 手数料・遅延・約定の報告の価格、出口の箱の時計の値、注文の欄、構築の入力の写像/列、`to_nanos`・`validate_nanos`)× 値の型(numpy の全ての具体の数の型、組み込みの型、分数、十進、登録だけの Python の class、継承した Python の class)。
- 神託: 変更の前後で全ての場所の結果(値か断りの型)が同じ、かつ戦略のフックが戦略の呼び出しの外で 0 回。
- 大きな int: 入口(戦略の API の int 引数・差し込み口の int の答え・事象の int の欄・構築の int 引数・時刻の関数)× {±10**5000, ±2**2000 の境目, 2**63} × 桁の上限 {既定, 640} → 断りは入口の誤りの型。
- 入れ子: 深さ 0〜MAX_NESTING+3 × 容器の種類 5 × 入口 {`place_order` の `extra`、出口の箱} × 戦略が先に使った深さ {0, 300} → MAX_NESTING 以下は受け付け、超えたら入口の誤り、結果は積み上がりに依らない。
列に入れなかった物は試験のファイルの説明に書く。

## B. 厳しい批評家が [止める] にしそうな点(返す前に潰す一覧。直したあとで結果を書く)

1. 登録だけの Python の class を断るのは「機能を外して要件から逃げる」ではないか → 要件は「数の種類を登録簿に聞かずに決める」(批評家の直し方の指定)。数であることは class 自身の継承で示せる。素のプロセスで変わる型は 0 件(上の列べ)。契約の文と試験で振る舞いを縛る。
2. 束ねた numpy を読み込みの前に書き換えられたら → 読み込み時に静的な C の型かを確かめ、違えば読み込みを止める。
3. 入れ子の上限 100 は根拠の無い値ではないか → 上の実測の積み上がりから導いた。値はリードに確かめる(報告の「リードに聞くこと」)。
4. 残る穴: 組み込みやライブラリの関数の付け替え(`builtins.len = …`、`heapq.heappush = …`)は核が呼ぶコードを変える。これはプログラムの変更として対象外に書く。核が型や値を決めるために実行中に引く名前は無いことを試験(numpy の名前の付け替え)で示す。

## C. 直したあとの確かめ(コマンドと出力)

- 新しい格子(直す前): `PYTHONPATH=src python -m pytest tests/bt/item_0/test_bt0_r14_process_state.py -p no:cacheprovider -q -rf`(`<W>/pytest_item0_r14_worker_prefix_full.log`)→ 落ちたのは `register:numbers.{Complex,Integral,Rational,Real}`・`register:collections.abc.{Mapping,MutableMapping}`・`hook:numbers.{Complex,Integral,Rational,Real}`・`decimal:{prec1,floor3,emax}`・`numpy_name:bool_`・`sys_modules:numpy`・大きな int の 2 件・等価性・規則・ソースの 2 件。`hook:collections.abc.Mapping` はこの時点では落ちなかった(試験の誤り: 負の覚えを消すための `Sized.register` 自身がフックに「既に Sized」と答えられ、登録が起きていなかった。自分の ABC に登録する形に直すと、直す前の核で `['raised', 'AttributeError']` と `hooks_in_core` 3 件が出た)。
- 新しい格子(直した後): `<W>/pytest_item0_r14_worker_after6.log` → `94 passed in 12.59s`。
- 批評家の試験: `PYTHONPATH=src python -m pytest tests/bt/critic/item_0/test_i0r13_process_global_state_decides_core_values.py tests/bt/critic/item_0/test_i0r11_class_dict_key_runs_foreign_code.py tests/bt/critic/item_0/test_i0r11_pinned_dropped_facts_fail_the_core_step.py tests/bt/critic/item_0/test_i0r11_history_limit_exact_refusal.py -p no:cacheprovider` → `30 passed in 1.54s`(直す前は `7 failed, 23 passed`)。
- 速さ(参考。ほかの試験と同時に走らせた測り): `<W>/item0_r14_worker_speed.py`(2 万本の足、50 本ごとに注文)→ HEAD の核 `57.58 us/bar`、この周の核 `48.95 us/bar`。遅くはなっていない。
- 項目 0・批評家・場面集の試験(最後の版): `PYTHONPATH=src python -m pytest tests/bt/item_0 tests/bt/critic/item_0 tests/bt/battery/item_0 -p no:cacheprovider -rf` → `2101 passed, 2 skipped in 463.15s (0:07:43)`(`<W>/pytest_item0_r14_worker_final.log`)。
- 全試験(切り離して 1 回。途中で `time.py` の十進の設定を tuple に束ね直したので、上の最後の版の実行で項目 0 を回し直した): `PYTHONPATH=src python -m pytest -p no:cacheprovider -rf` → `5002 passed, 6 skipped, 1 warning in 887.46s (0:14:47)`(`<W>/pytest_item0_r14_worker_full.log`)。
- 書き直した既存の試験(消した試験は無い): `tests/bt/item_0/test_bt0_sender_types.py`(`NotConvertible` を登録ではなく `numbers.Real` の継承で数にする)、`tests/bt/item_0/test_bt0_r11_foreign_objects.py`(`_failing_number` を同じく継承で)。説明文だけ直した: `test_bt0_r12_party_hooks.py`・`test_bt0_r10_strategy_side.py`(ABC のフックを対象外とした理由の文を、この周の格子への参照に替えた)。
