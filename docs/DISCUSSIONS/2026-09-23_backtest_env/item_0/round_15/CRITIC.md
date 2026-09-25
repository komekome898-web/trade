# 批評家の記録(項目 0「核」、第 15 周。新しく起こされた批評家)

委任文: `docs/DATA/delegations/20260923_backtest_env_prompt.md`(`sha256sum … | cut -c1-12` → `cdf623e4fb24`。起動文の指紋と一致。全 169 行を読んだ)。
合意した完了の形(委任文 §0 の逐語): 「**すべてが調査結果以上の信頼性と再現性に優れたものにすること。**」
手元に置いたもの: 固定した要件 `item_0/REQUIREMENTS.md`(§1 の行、§2 の P0-1〜P0-7、§3 の調査結果の行)、場面集 `tests/bt/battery/item_0/DEFINITIONS.md`・`scenes.py`・`grid_c.py`・`opponents/CONSIDERED.md`、作業者の根本原因 `round_15/ROOTCAUSE.md`、場面係の `ROOTCAUSE_r15-1.md`、監査役(場面)r15-1 の出力とリードの答え(`docs/AUDITOR/VERDICTS/2026-09-23_backtest_env_run11_item0.md` の第 15 周の節)、第 14 周の `CRITIC.md`。
行番号は作業木のもの(HEAD `40fd7f8`。作業者と場面係の変更はこのコミットまでに入っている。`src/` と `tests/bt/battery/` に未コミットの差分は無い)。
`<S>` = `/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt`。この周の試しは `<S>/r15_critic/` に置いた。

## 前の周の指摘の直り(自分で確かめた)

- **i0-r14-01(止める)**: 直っている。登録の前に作った辞書 `{Fraction(1): "a", Decimal(2**61): "b"}` を extra に持つ同じ実行を、登録なし → 別の実行の戦略が `numbers.Rational.register(Decimal)` → もう一度、と同じプロセスで回すと 3 回とも `run ok 15e4ca0f3da3`(`<S>/r15_critic/item0_r15_critic_recheck_r14_01.out`)。第 14 周の批評家の試し `item0_r14_critic_probe_fraction_decimal_eq.py register/rerun/account` は今も AttributeError を出すが、あの試しは登録の**あと**に送り手自身の呼び出しの中で辞書のリテラルを組むので、例外は送り手自身のコード(ライブラリの `Fraction.__eq__`)から出ている。核の道ではない(第 14 周の試験は辞書を読み込み時に作る形で、下の実行で通る)。
- **i0-r14-02(止める)**: 直っている。`item0_r14_critic_probe_lazy_rebuilder_cache.py fresh/poisoned` → `run B (clean strategy), same process, after run A : ['maker']`、持ち主の呼び出しの外で走った戦略の `fields` は `[]`。核の全ファイルの AST で、関数の中の import・`sys.modules` は 0 件、`compile`/`exec` は `values.py` 1475・1476・1503・1505 行(`_make_copier` / `_make_rebuilder`)だけで、どちらも読み込み時の `bind_carriers`(1446・1447 行)からだけ呼ばれる(`<S>/r15_critic/item0_r15_critic_probe_runtime_imports.py`)。
- **i0-r14-03(止める)**: 指摘した形(Fraction を先に float にする・longdouble を float に丸める)は直っている(`to_nanos(np.longdouble('1700000000.123456789'), 's')` は TimestampUnitError)。**ただし同じ族の別の形が残る**: 下の i0-r15-01(float と、float に正確に移った longdouble が、最短の十進表記で丸められる)。
- **i0-r14-04(止める)**: 直っている。`item0_r14_critic_probe_timedelta_unit.py` → timedelta64 / datetime64 は `settle` で Unsettled、`validate_nanos` と `to_nanos` で TimestampUnitError、遅延の模型の答えは LatencyModelError(`<S>/r15_critic/item0_r15_critic_recheck_r14_probes.out`)。
- **i0-r14-05(直す)**: 指摘した形は直っている(`item0_r14_critic_probe_stack_depth.py` → 戦略自身の積み上がり 600・800・900 × 入れ子 10・50・98 が全部 `accepted | run ok`)。ふつうの入れ子の `freeze` が要る枠は入れ子 1・50・97 で 7 のまま、`engine.run()` は 24 のまま(`<S>/r15_critic/item0_r15_critic_probe_headroom.out`)。**同じ族の残り**: 下の i0-r15-02・i0-r15-03。
- **i0-r14-06(直す、場面集)**: 一覧(`grid_c.unplaced`)は足され、見出しに「升目に当たらない場面 4」が並ぶ。リードの答え(br15-1-1: (iii) の形を当面採る)どおり。**残り**: 下の i0-r15-06。
- 規則 8(批評家の試験自身の誤り): 作業者の第 15 周の根本原因(`round_15/ROOTCAUSE.md` §8)は、前の周までの批評家の試験を全部通したと書き、試験自身の誤りの申告は無い。落ちる前の周の批評家の試験は無かった(下の実行)。取り下げる試験は無い。
- 作業者が書き直した自分の試験 4 本(`test_bt0_r8_sender_adversary.py`・`test_bt0_values.py`・`test_bt0_r14_process_state.py`・`_r14_state_child.py`)は、核がもう作らない型(ライブラリの `Fraction` / `Decimal`)を表から外して `PlainFraction` / `PlainDecimal` に替え、契約の版を `core-16` にしただけで、試す中身は弱めていない(`git diff 563661d HEAD -- …` を読んだ)。
- 前の周の [直す]・[示唆] で [止める] に付け直すもの: i0-r14-03 と同じ族の float の道を、下の i0-r15-01 で [止める] にした(第 14 周の批評家は「float は最短の十進表記で読む」を約束として残したが、float が正確に持つ値を丸めるので、TIME_CONTRACT の「rounding: none」に反する)。

実行した試験:
- `PYTHONPATH=src python -m pytest tests/bt/item_0 tests/bt/critic/item_0 tests/bt/battery/item_0 -p no:cacheprovider -rf`(この周の新しい試験を置く前に集めた)→ `3298 passed, 2 skipped, 1 warning in 527.76s (0:08:47)`(`<S>/r15_critic/pytest_item0_r15_critic_all0.log`)。
- 新しい試験を置いたあと `PYTHONPATH=src python -m pytest tests/bt/critic/item_0 -p no:cacheprovider` → `26 failed, 184 passed in 254.18s (0:04:14)`(`<S>/r15_critic/pytest_item0_r15_critic_criticdir.log`。落ちた 26 件は全部この周の新しい試験 2 本)。3 本目の新しい試験(i0-r15-03)は後から置き、単独で 2 回 `2 failed, 4 passed`。
- 場面集: `PYTHONPATH=src python3 tests/bt/battery/item_0/gen_definitions.py --check` → `OK`。`python3 scripts/check_bt_considered.py tests/bt/battery/item_0/opponents/CONSIDERED.md` → `OK 誤り 0 件`。`PYTHONPATH=src python3 tests/bt/battery/item_0/mutant.py --check` → `changed scenes: ['p4-received-time']` / `OK`。

## 指摘

この周の [止める] は 2 件(実装 1・場面集 1)、[直す] は 4 件(実装 3・場面集 1)、[示唆] は 1 件(実装)。

### i0-r15-01 [止める](相手: 実装、repeat_of: i0-r14-03、場当たり: いいえ)

**`to_nanos` は float を最短の十進表記(`float.__repr__`、`time.py` 184 行)で読むので、float が正確に持つ時刻を、表記の桁数に丸めた値に黙って替える。第 15 周に直した longdouble の道も、float が正確に持てると確かめた(`values._exactly_converted`)あとで同じ所を通る。**

- `to_nanos(1700000000123456.75, "us")` → `1700000000123456800`。float はこの値を正確に持つ(1.7e15 の近くの間隔は 0.25)ので、値が言うのは `1700000000123456750` ns。50 ns ずれ、断りは出ない。入力の文字どおりの値とも、float が持つ値とも違う。
- `to_nanos(2816833943301389824.0, "ns")`(float が正確に持つ整数)→ `2816833943301390000`(+176 ns)。
- numpy の float64、longdouble も同じ(`np.longdouble("1700000000123456.75")` は float が正確に持てるので `_exactly_converted` を通り、最短表記で .8 になる)。
- 契約との食い違い: `time.py` 8 行「Conversion is exact」、70 行 `"rounding": "none (inputs with sub-nanosecond digits are rejected)"`、docstring「floats … convert without binary-float rounding; a value whose decimal representation has sub-nanosecond digits is rejected instead of being rounded silently」「a numpy longdouble only when a float holds its value exactly (else refused, never rounded)」。最短表記は 17 桁以下への**十進の丸め**で、float が持つ値を変える。
- 要件 §1「時刻は UTC の int64 ナノ秒」と観点 P0-2「既知の時刻…を投入し、核が保持する値が同じ int64 ナノ秒と一致するか」に対し、核の唯一の変換口が黙って違う時刻を返す。
- 根本原因(私の読み): 第 15 周の直しの神託は「値が言うナノ秒」を、float については最短表記の十進として置いた(作業者の ROOTCAUSE §4「float は今の約束どおり最短の十進表記」)。最短表記が float の持つ値と違うときを格子の列に入れていない。i0-r14-03 と同じ「変換の途中で値を狭めてから読む」族。
- 格付け: 「黙って誤った値」で [止める]。第 14 周の批評家はこの読み方を約束として残したので、前の周の判断を付け直す理由をここに書く: float が**正確に持つ**整数ナノ秒(0.75 µs)を別の値にするのは、どの読み方(入力の文字・float の値)でも正解にならない。
- 直し方の向き(作業者が決める): float を `float.as_integer_ratio`(正確な値)で読み、ナノ秒より細かい桁があれば断る(作業者の申告の規則「正確に変換できなければ断る」)。こうすると `1700000000.1234567`(秒)の float は、持つ値にナノ秒より細かい桁があるので断られる。受け付け方を変えるので契約の文も直す。

根拠:
- `PYTHONPATH=src python3 <S>/r15_critic/item0_r15_critic_probe_float_shortest_repr.py` → `float(1700000000123456.8) unit=us: holds 1700000000123456750 ns (whole: True) | to_nanos -> 1700000000123456800  <-- off by 50 ns` / `float(2.81683394330139e+18) unit=ns: holds 2816833943301389824 ns (whole: True) | to_nanos -> 2816833943301390000  <-- off by 176 ns` / `longdouble(1700000000123456.8) unit=us: … <-- off by 50 ns` / `longdouble(2.81683394330139e+18) unit=ns: … <-- off by 176 ns`(`…_float_shortest_repr.out`)。第 14 周の核(`git archive 563661d`)でも同じ出力(前からある振る舞い)。
- 格子(`<S>/r15_critic/item0_r15_critic_probe_to_nanos_grid.py`、種 15、7,800 件 = 値 300 × 単位 4 × 型 6〜7): 契約どおりの longdouble の断り(297 件)を除いて、黙って違う値が 1 件 `('longdouble(value it holds)', 'ns', 'gave 2816833943301390000, the value states 2816833943301389824')`。
- 試験(残す。作業者が直す): `PYTHONPATH=src python -m pytest tests/bt/critic/item_0/test_i0r15_float_time_rounded_by_shortest_repr.py -p no:cacheprovider` → `6 failed, 3 passed`(`to_nanos(float(1700000000123456.75), 'us') gave 1700000000123456800, the value holds 1700000000123456750 (+50 ns)` ほか)。

直すファイル: `src/bot/bt/core/time.py`(`to_nanos` の float の道と TIME_CONTRACT・docstring)。

### i0-r15-02 [直す](相手: 実装、repeat_of: i0-r14-05、場当たり: いいえ)

**送り手が signaling NaN の Decimal を辞書の鍵・集合の要素に持つと(送り手自身の Decimal の子が hash を持てば作れる)、核はそれを基の型で読んで `PlainDecimal('sNaN')` を作り、自分の辞書・集合を作るとき(`values.py` 946 行 `_dict_of` の `d[k] = x`、953 行 `_set_of`)に Decimal の C の hash が組み込みの `TypeError("Cannot hash a signaling NaN value")` を出す。`_walk` が捕まえるのは RecursionError だけ(927 行)なので、TypeError がそのまま出る。**

- `values.freeze` / `values.settle` → `TypeError`(契約の「`ValueError`」「`Unsettled`」でない)。
- 戦略の `place_order`(on_event の中)→ `TypeError`(OrderApiError でない)。
- 出口の箱に書いた注文(on_event が返ったあとに核が `_take_message` で settle する)→ 実行が `TypeError` で FAILED になる(OrderApiError でない)。
- 口座の強制注文の道は AccountSocketError になる(この道だけは正しい)。
- 契約 `type_decisions`(`contract.py` 304-305 行)「a refusal is the error type of the place it enters」と `scope`(132 行)「a refusal is always the entry's own error」に反する。
- 第 13・14 周の核でも同じ 20 件が落ちる(前からある振る舞い)。第 15 周の作業者は signaling NaN を値に持つ FrozenDict の hash を扱った(`_pairs_hash`)が、鍵と要素の形は列の外だった。
- 格付け: 黙って誤った値は無く、断りの型だけが違う。前の周の同じ格(i0-r11-01・i0-r14-05)に合わせて [直す]。族は i0-r14-05(核が入れ物を作るときにインタプリタが出す例外を、歩きが入口の誤りに替えない。第 15 周の直しは RecursionError だけを替えた)。

根拠:
- `PYTHONPATH=src python3 <S>/r15_critic/item0_r15_critic_probe_snan_keys.py` → `dict key freeze: builtins.TypeError: Cannot hash a signaling NaN value` / `set element in a tuple settle: builtins.TypeError: …` / `place_order raised inside on_event: TypeError Cannot hash a signaling NaN value`(`…_snan_keys.out`)。
- 試験(残す): `PYTHONPATH=src python -m pytest tests/bt/critic/item_0/test_i0r15_unhashable_key_refusal_type.py -p no:cacheprovider` → `20 failed, 5 passed`(freeze 5・settle 5・place_order 5・出口の箱 5 が落ち、口座の 5 が通る。`an outbox message with an sNaN dict-key: the engine failed with TypeError` ほか)。第 13 周(`e13fec6`)と第 14 周(`563661d`)の核で同じ試験 → どちらも `20 failed, 5 passed`。

直すファイル: `src/bot/bt/core/values.py`(`_dict_of` / `_set_of` / `_walk` で hash できない鍵・要素を入口の誤りにする)。

### i0-r15-03 [直す](相手: 実装、repeat_of: i0-r14-05、場当たり: いいえ)

**契約 `process_state`(`contract.py` 180-181 行)と `values.py` 635 行・933 行は「hash の等しい別々の入れ子の値を比べるとき、インタプリタは入れ物 1 つに再帰の上限を 1 つ使う(測った: 98 段で 106 枠)」と書く。入れ子の FrozenDict の鍵では、比べるのが核自身の `FrozenDict.__eq__`(1262・1271 行: Python の method が dict を 2 つ作って比べる)なので、1 段に約 3 枠を使う。**

- 衝突する入れ子の鍵 2 つの `freeze` が要る枠: tuple は 10 段 16・50 段 56・97 段 103(1 段 1 枠 = 契約どおり)。FrozenDict は 10 段 34・30 段 94(試験の中では 99)・48 段 148(同 153)。98 段なら約 300 枠で、契約の「106 枠」の約 3 倍。
- 断りの型は入口の誤り(ValueError)のままで、黙って誤った値は無い。事実の文が、核の型で違う。
- 格付け: 契約の事実の誤りで、受け付け・断り・値は変わらないので [直す]。族は i0-r14-05(入れ子の断りが呼び手の積み上がりで決まる範囲の文)。

根拠:
- `PYTHONPATH=src python3 <S>/r15_critic/item0_r15_critic_probe_headroom.py` → `freeze(dict with 2 colliding tuple keys, 97 levels): 103 (one less -> ValueError)` / `freeze(dict with 2 colliding FrozenDict keys, 10 levels): 34` / `… 30 levels): 94` / `… 48 levels): 148 (one less -> ValueError)`(`…_headroom.out`)。
- 試験(残す): `PYTHONPATH=src python -m pytest tests/bt/critic/item_0/test_i0r15_colliding_frozendict_frames.py -p no:cacheprovider` → 2 回とも `2 failed, 4 passed`(`two colliding 30-level FrozenDict keys need 99 frames of headroom; the contract allows one per container of the two: 90` / `… 48-level … need 153 … : 126`)。上限は契約を最も甘く読んだ「2 つの値の入れ物の数 = 2 × 段数」+ CALL_FRAMES。

直すファイル: `src/bot/bt/core/contract.py`(process_state の文)、`src/bot/bt/core/values.py`(MAX_NESTING・CALL_FRAMES の注釈と `_recursion_text`。または FrozenDict の比べを枠を積まない形にする)。

### i0-r15-04 [直す](相手: 実装、repeat_of: i0-r14-03、場当たり: いいえ)

**作業者は「数の変換は正確に変換できなければ断る」にしたと申告し、`values._now`(755 行)の説明も「Convert a foreign number once, now, EXACTLY」と書くが、float の欄(`as_float` 1160 行、`take_float` 1058 行)は int を `_now(float, int)` で float にし、int は `_exactly_converted` の検めを素通りするので、丸めて受け付ける。同じ値でも、numpy の longdouble なら断る。**

- 2**53 + 1 を価格(`as_float`)・手数料(`take_float`)に: int・numpy int64・Fraction → `9007199254740992.0`(黙って丸める)、numpy longdouble → 断る(`a float cannot hold exactly`)。`Fraction(1, 3)` → `0.3333333333333333`、`np.longdouble(1)/np.longdouble(3)` → 断る。
- float の欄は float と宣言されているので、丸めること自体は欄の意味の中と読める(作業者の ROOTCAUSE §4「float の欄の宣言どおりの丸め」)。問題は規則が型で分かれること(同じ値が「受け付けて丸める」と「断る」に分かれる)と、`_now` の説明と作業者の申告が事実と違うこと。
- 格付け: 欄の宣言の中の丸めで、要件の値の場面を外れないので [直す]。族は i0-r14-03(変換の結果を値と照らさない)。直し方は、float の欄の規則を 1 つに決める(全ての型を最も近い float に丸めると書いて longdouble も受け付けるか、全ての型で正確でなければ断るか)。

根拠: `PYTHONPATH=src python3 <S>/r15_critic/item0_r15_critic_probe_float_field_exactness.py` → `int as_float: 9007199254740992.0` / `numpy int64 take_float: 9007199254740992.0` / `Fraction take_float: 9007199254740992.0` / `numpy longdouble as_float: refused (ValueError: price holds a numpy.longdouble whose value a float cannot hold exactly)` / `values._now docstring first line: Convert a foreign number once, now, EXACTLY, and build what the`(`…_float_field_exactness.out`)。

直すファイル: `src/bot/bt/core/values.py`(`_now`・`as_float`・`take_float`・PLAIN_DATA_RULE)、`src/bot/bt/core/contract.py`(plug_in_answers の文)。

### i0-r15-05 [止める](相手: 場面集、repeat_of: null、場当たり: いいえ)

**観点 P0-2 の文は「全事象の時刻が UTC 起点の int64 ナノ秒で表現され、他の単位(秒・ミリ・ISO 文字列)が核の内部表現に混入しないこと」と単位を名指す(`REQUIREMENTS.md` 18 行)。場面集の P0-2 は ISO の 2 場面(`p2-iso-utc`・`p2-iso-offset`)と int ナノ秒の 2 場面(`p2-event-time-exact`・`p2-one-ns-apart`)だけで、秒・ミリ(とマイクロ秒)の値を入れる場面が 1 つも無い。**

- `grep -n '"p2-' tests/bt/battery/item_0/scenes.py` → 275・283・289・296 行の 4 場面だけ。場面集の観点の要約(`DEFINITIONS.md` 96 行)も「時刻が UTC の int64 ナノ秒で表されること」で、「他の単位が混入しない」の部分を落としている。
- 升目の表は秒・ミリの升目を「測っていない」と記録しているので、記録は測っていないことを隠してはいない。しかし、盲検で比べる表に P0-2 の秒・ミリの変換が 1 セルも無く、観点の文が名指す部分を比べていない。現に、この周の i0-r15-01(float の秒・マイクロ秒の時刻が黙って丸められる)はこの穴の中にあり、場面集では見えない。
- 第 14 周の批評家は、Fraction・longdouble・timedelta64 の入力の形を足すかを [示唆] とした(固定した測り方が入力の形を決めていないため)。秒・ミリはそれと違い、観点の文そのものが名指す単位なので、場面集が観点を覆っているかの問題として付け直した。
- 格付け: 批評家は毎周「場面集が要件の観点を全部覆っているか」を見る(委任文 §3「場面集」)。観点の文の一部を覆っていないので [止める](委任文 §3「迷ったら重い方」。規則 3 の「各観点に値の場面を 1 つ以上」は満たしている)。場面集の側なので、項目 0 の通過は止めず、並行の直し(L-441)に入る。
- 直し方の向き(場面係が決める): 既知の時刻を秒・ミリ・マイクロ秒で、文字列と float(float が正確に持つ値と持たない値の両方)で入れ、対象自身の変換で int ナノ秒にした値を正解(手計算)と照らす値の場面。

根拠: 上の grep と `REQUIREMENTS.md` 18 行、`DEFINITIONS.md` 96 行・171-180 行(P0-2 の見出しと一覧)。

直すファイル: `tests/bt/battery/item_0/scenes.py`、`tests/bt/battery/item_0/adapters/new_impl.py`(と相手の adapter)、`tests/bt/battery/item_0/run_battery.py`、`tests/bt/battery/item_0/gen_definitions.py`(`DEFINITIONS.md` はそこから作る)。

### i0-r15-06 [直す](相手: 場面集、repeat_of: i0-r14-06、場当たり: いいえ)

**第 r15-1 回の直しで見出しに「升目に当たらない場面 4」と一覧が並んだが、P0-2 の 160 升目の判断の欄は全部「測っていない(固定した測り方の外)」のままで、括弧の中の理由が事実と違う。** P0-2 の固定した測り方は「既知の時刻…を投入し、核が保持する値が同じ int64 ナノ秒と一致するか」で、一覧の 4 場面はまさにその測り方で ISO と int ナノ秒を測っている(一覧の説明文自身も「一覧の場面はその観点を測っている」と書く、`DEFINITIONS.md` 111 行)。秒・ミリの升目も、測っていないのは場面が無いからで(上の i0-r15-05)、固定した測り方の外だからではない。

- リードの答え(br15-1-1)は升目の判断(2 値)を変えない (iii) の形を当面採り、「足りるかは批評家が第 15 周に読む」とした。私の読み: 見出しと一覧で「P0-2 が 1 つも測られていない」という誤読は防げている。残るのは、判断の欄の括弧が「測り方の外」と理由を断定する点で、同じ表の一覧の説明文と食い違う。
- 格付け: 向きは通過に不利(測った物を測っていない側に置く)で、場面・正解・比較の表のセルは変わらないので [直す]。直し方は F を変えずにできる: 判断の値は 2 値のまま、「(固定した測り方の外)」の括弧を、升目に当たらない場面がその観点にあるときは機械で別の文(例「測っていない(升目の型を入力が決めない場面が同じ観点を測る: 一覧)」)にするか、括弧を外す。

根拠: `sed -n 171,185p tests/bt/battery/item_0/DEFINITIONS.md` → `### P0-2(升目 160: 場面にした 0 / 測っていない(固定した測り方の外) 160 / 升目に当たらない場面 4)` と `| 約定 | 戦略の呼び出しに届く物 | int64 ナノ秒 | 測っていない(固定した測り方の外) | — |`、111 行の一覧の説明。

直すファイル: `tests/bt/battery/item_0/grid_c.py`、`tests/bt/battery/item_0/gen_definitions.py`。

### i0-r15-07 [示唆](相手: 実装、repeat_of: null、場当たり: いいえ)

`to_nanos(np.longdouble('1700000000.123456789'), 's')` の断りの文は「timestamp value for unit 's' must be int, float, Decimal, Fraction or numeric str, got numpy.longdouble」で、float が正確に持てる longdouble は受け付けるのに、型そのものを断ったように読める(`time.py` の `scalar` の ValueError を捨てて一般の文を出している)。`values.scalar` が出した理由(「a float cannot hold exactly」)を断りの文に残すとよい。

根拠: `<S>/r15_critic/item0_r15_critic_recheck_r14_probes.out` の `== to_nanos_exact` の節。

直すファイル: `src/bot/bt/core/time.py`。

## 場面集の側で確かめたこと

- 検め: `gen_definitions.py --check` → `OK`、`check_bt_considered.py` → `OK 誤り 0 件`、`mutant.py --check` → `OK`(上)。
- 第 14 周の批評家が見た版(`563661d`)からの差分は `DEFINITIONS.md`・`ROOTCAUSE_r15-1.md`・`gen_definitions.py`・`grid_c.py`・判断の表 2 つ・`scenes.py`(入力の事象を読む関数 `input_events` の切り出しだけ。場面の欄は変わらない)・試験 3 本。adapter・再現(`opponents/`)・runner・`survey_results/` は第 13 周の版(`40c2525`)から変わっていない(`git diff 40c2525 HEAD --stat -- …/adapters …/opponents …/run_battery.py …/survey_results` → 出力なし)。
- adapter の公平さ・検討表のスキップの理由・再現の忠実さ: この周に変更が無いことを差分で確かめた。41 本の adapter と再現 1 本を、この周に全部読み直してはいない(限界)。第 13・14 周の批評家が読んだ範囲は各周の CRITIC.md にある。
- `requests` の記録の数の注記(br13-1-2)は `DEFINITIONS.md` の節の注記に機械で出ている(相手: 記録しない 37・設定つき対象 41、再現: 記録しない 1・設定つき対象 13)。
- 規則 1〜9: 能力を申告で数えている場面は見つからなかった(第 r15-1 回は場面の欄を変えていない)。

## 提出前の吟味(批評家の文)

- 指摘ごとに根拠を自分で再現した: i0-r15-01 は試しと格子と試験の 3 通り(第 14 周の核でも同じ出力)。i0-r15-02 は試しと試験、第 13・14 周の核でも同じ落ち方。i0-r15-03 は試しと試験を 2 回(同じ結果)。i0-r15-04 は試し。i0-r15-05・06 はファイルの行。
- 格付けを基準に照らした: i0-r15-01 は float が正確に持つ時刻を黙って替えるので「黙って誤った値」で [止める]。i0-r15-05 は観点の文が名指す単位を場面集が覆わないので [止める](迷ったので重い方)。i0-r15-02・03 は断りの型と契約の事実の文で、前の周の同じ格(i0-r11-01・i0-r14-05)に合わせて [直す]。i0-r15-04 は float の欄の宣言の中の丸めで [直す]。
- 前の周の指摘の直りを自分で確かめた(上の節)。直ったもの(i0-r14-01・02・04、i0-r14-03・05 の指摘した形)は指摘に挙げていない。第 14 周の試しが今も例外を出すもの(fraction_decimal_eq の register)は、送り手自身のコードの例外であることを確かめ、登録の前に作った辞書で核の道が直っていることを示した。
- 相手の付け違い: i0-r15-01〜04・07 の直すファイルは全部 `src/bot/bt/core/` の下で、相手は実装。i0-r15-05・06 は `tests/bt/battery/item_0/` の下だけで、相手は場面集。05 は実装の欠陥ではなく場面の抜けで、実装の欠陥(i0-r15-01)は別に実装の側で挙げた。
- 場当たりの直しは見つからなかった(作業者の直しは型の作り替え・反復の歩き・読み込み時の表で、試験だけの特別扱いや閾値の移しは無い。書き直した試験も弱めていない)。
- 置いた試験: `tests/bt/critic/item_0/test_i0r15_float_time_rounded_by_shortest_repr.py`(9 件、6 件落ちる)、`test_i0r15_unhashable_key_refusal_type.py`(25 件、20 件落ちる)、`test_i0r15_colliding_frozendict_frames.py`(6 件、2 件落ちる)。落ちるのは全部この周の指摘の根拠で、作業者が直す。
