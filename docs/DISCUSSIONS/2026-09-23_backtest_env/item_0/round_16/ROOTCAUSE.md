# 項目 0「核」第 16 周 — 直す前の根本原因(作業者)

委任文: `docs/DATA/delegations/20260923_backtest_env_prompt.md`(`sha256sum … | cut -c1-12` → `cdf623e4fb24`。起動文の指紋と一致。全 169 行を読んだ)。
合意した完了の形(委任文 §0 の逐語): 「**すべてが調査結果以上の信頼性と再現性に優れたものにすること。**」
固定した要件: `item_0/REQUIREMENTS.md`(変えない)。リードの設計: `round_7/LEAD_DESIGN.md`(§2・§3.1〜§3.4・§9.2・§9.3・§11 を読んだ)。批評家の記録: `round_15/CRITIC.md`。前の周の自分の根本原因: `round_15/ROOTCAUSE.md`。
一時ファイルは `/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/r16_worker/`(以下 `<W>`)。HEAD は `0f2e07d`。

## 0. この周に直す対象と、この周の初めに確かめたこと

`PYTHONPATH=src python -m pytest tests/bt/critic/item_0/test_i0r15_float_time_rounded_by_shortest_repr.py tests/bt/critic/item_0/test_i0r15_unhashable_key_refusal_type.py tests/bt/critic/item_0/test_i0r15_colliding_frozendict_frames.py -p no:cacheprovider` → `28 failed, 12 passed in 0.30s`(`<W>/pytest_item0_r16_worker_start.log`)。

| id | 格 | 相手 | repeat_of | この周の初めの確かめ |
|---|---|---|---|---|
| i0-r15-01 | 止める | 実装 | i0-r14-03 | 上の実行で `test_to_nanos_gives_the_ns_the_float_holds_or_refuses` の 6 件が落ちる |
| i0-r15-02 | 直す | 実装 | i0-r14-05 | 上の実行で 20 件が落ちる(freeze 5・settle 5・place_order 5・出口の箱 5) |
| i0-r15-03 | 直す | 実装 | i0-r14-05 | 上の実行で `[FrozenDict-30]`・`[FrozenDict-48]` の 2 件が落ちる。自分で測った比べ 1 回の枠: FrozenDict 10 段 29・30 段 89・48 段 143、tuple 10 段 11・30 段 31・48 段 49(`<W>/item0_r16_worker_probe_fdeq.py`)。`FrozenDict.__eq__` を `dict.__eq__(dict(..), dict(..))` に替えても 29・89・143 のまま(Python の method の枠 + 比べの入口 2 つで 1 段 3 枠) |
| i0-r15-04 | 直す | 実装 | i0-r14-03 | 批評家の試し `item0_r15_critic_probe_float_field_exactness.py` と同じ: 2**53+1 は int・numpy int64・Fraction で丸めて受け付け、numpy longdouble だけ断る |
| i0-r15-07 | 示唆 | 実装 | null | `to_nanos(np.longdouble('1700000000.123456789'), 's')` の断りの文が「must be int, float, Decimal, Fraction or numeric str, got numpy.longdouble」 |
| i0-r15-05・06 | 止める・直す | 場面集 | null・i0-r14-06 | 場面係の持ち物(`tests/bt/battery/`)。作業者は直さない |
| i0-r11-01・03 | 直す | 実装 | i0-r9-02 | 第 12 周に直し、第 14・15 周の批評家が直りを確かめた。この周は構造を変えない |
| i0-r13-01・i0-r14-01・02・04 | 止める | 実装 | — | 第 15 周の批評家が直りを確かめた(`round_15/CRITIC.md`)。この周は構造を変えない |

## 1. 3 つの指摘に共通する根: 「1 つの値の読み方」を、型ごと・道ごとに別々に決めていた

第 15 周の私は「正確に変換できなければ断る」を規則にしたが、**同じ値を読む道が複数あり、道ごとに違う読み方が残っていた**:

- 時刻の float は「最短の十進表記」で読み、同じ関数の Fraction と int は「値そのもの」で読んだ(i0-r15-01)。
- float の欄は int・Fraction を最も近い float に丸め、longdouble だけ正確でなければ断った(i0-r15-04)。
- 核が作る入れ物の「作れない」を、再帰の上限(RecursionError)だけ入口の誤りに替え、hash が無い(TypeError)は替えなかった(i0-r15-02)。
- 衝突した入れ子の値の比べは、tuple と frozenset はインタプリタの C、FrozenDict だけ核の Python の method で、枠の使い方が型で違った(i0-r15-03)。

どれも、第 15 周の格子が「型 × 入口」を列べたのに、神託を**型ごとの約束(最短表記・欄の宣言・RecursionError だけ)から作った**ので、約束そのものの食い違いが列の外だった(i0-r15-01 は、私の格子 C の神託 `_stated_ns` 自身が float を最短表記で読んでいた = 実装の読み方を写していた。リードの設計 §3.2「神託を実装の場合分けから作らない」に反していた)。

## 2. i0-r15-01(float の時刻を最短の十進表記で読む)

### なぜ起きたか(根本原因)

`to_nanos` は float を `float.__repr__`(最短の十進表記)で読んだ(`time.py` 184 行)。最短表記は、float が持つ値を 17 桁以下の十進に**丸めた**もので、float が持つ値と違うことがある。核は、呼び手が打った文字を見られない。見えるのは float が持つ値だけである。だから、最短表記で読むと float が持つ値を黙って替え(`1700000000123456.75` us → 800 ns)、値そのもので読むと打った文字を黙って替える(`1700000000123456.8` と打った float は `…456.75` を持つので 750 ns)。**どちらか一方の読み方を決めても、もう一方の読み方では黙って違う値になる入力が残る。**第 15 周の私はこの 2 つの読み方の食い違いを列べなかった。

### どの構造を変えるか

- float の時刻は、**2 つの読み方が同じ値を言うときだけ受け付ける**: float が持つ正確な値(`float.as_integer_ratio`)と、その最短の十進表記の値が等しく、かつその値がナノ秒の整数であるとき、そのナノ秒。等しくなければ「float は打った十進を持たない(持つ値は …)。int・文字列・Decimal で渡す」と断る。こうすると、どちらの読み方をしても黙って違う値は出ない(`1.5` s・`1700000000.0` s・`0.25` s は受け付け、`1700000000.123` s・`1700000000123456.75` us・`2.81683394330139e+18` ns は断る)。
- 比べは核の固定の文脈で行う(`exact_context().create_decimal_from_float` は float が持つ値を正確に十進にする。`create_decimal(float.__repr__(f))` と `compare`)。スレッドの文脈は読まない。
- numpy の float16/32/64 は、今と同じく float に正確に移してから同じ規則。longdouble は、float が正確に持てるときだけ float に移して同じ規則(今のまま。移せなければ断る。断りの文に `scalar` の理由を残す = i0-r15-07)。
- int・Fraction・Decimal・文字列は今のまま(値そのもの = 打った値。食い違う 2 つの読み方が無い)。
- 契約の文(`time.py` の説明・`TIME_CONTRACT`)を、この規則に書き替える。受け付けを狭める振る舞いの変化(`to_nanos(1700000000.123456, "s")` を断る)を、自分の試験 `test_bt0_time.py` 40 行の書き替えと理由で残す。

採らなかった案: (a) 批評家の向き「float を `as_integer_ratio` で読み、細かい桁があれば断る」だけ — `1700000000123456.8` と打った float(持つ値は `.75`)を 750 ns で黙って受け付ける。打った文字の読み方で黙って違う値になる。(b) 今の最短表記のまま — float が持つ値を黙って替える(指摘そのもの)。

## 3. i0-r15-04(float の欄の規則が型で分かれる)

### なぜ起きたか(根本原因)

float の欄(`as_float`・`take_float`)は、int・Fraction・Decimal・文字列を**最も近い float に丸めて**受け付けていたのに、numpy longdouble だけは平らな値の規則(`_now`: 正確でなければ断る)を通していた。欄の規則(float の欄 = 最も近い float)と、平らな値の規則(値を保つ = 正確でなければ断る)の 2 つを、**型によってどちらかに振り分けていた**。`_now` の説明「EXACTLY」も、float の欄の int の道(`_now(float, int)`: int は正確さの検めを素通りする)では事実と違った。

### どの構造を変えるか

- **float の欄の規則を 1 つにする: 受け付ける全ての実数(int・float・Fraction・numpy の整数と浮動小数(longdouble を含む)、`numbers_only=False` なら Decimal と数の文字列)を、その正確な値に最も近い float にする**(偶数への丸め。int の割り算 `int.__truediv__` で計算し、浮動小数の丸めの状態を読まない)。float の範囲を超える値と複素数は断る。欄が float と宣言されているので、桁の多い値を断らない(`"0.1"` のような文字列の価格を断るのは欄の意味から外れる)。
- `_now` は平らな値の変換(正確でなければ断る)だけに使い、float の欄は新しい関数 `_nearest_float` を通す。`_now` の説明は事実どおり「正確」のまま。
- 契約 `plug_in_answers` と `FIELD_RULE`・`as_float` の説明に書く。

採らなかった案: 全ての型で正確でなければ断る — `as_float("0.1", numbers_only=False)`(事象の価格の文字列)を断ることになり、要件の事象の型(約定・足の価格)の値の場面を外れる。

## 4. i0-r15-02(hash の無い鍵・要素が組み込みの TypeError で出る)

### なぜ起きたか(根本原因)

核の歩き(`_walk`)は、核が作り直した値から辞書と集合を作るときにインタプリタが出す例外のうち、**再帰の上限(RecursionError)だけ**を入口の誤りに替えた。第 15 周の私は「インタプリタが入れ物を作るときに出す例外」を列べず、測った 1 つ(再帰)だけを扱った。核が作る値で hash を持たないのは、signaling NaN の `PlainDecimal`(Decimal の C の hash が断る)と、それを中に持つ tuple・FrozenList・FrozenDict だけである(ほかの型の hash は C か核の関数で、例外を出さない)。

### どの構造を変えるか

- 核が辞書の鍵・集合の要素にする値は、入れる前に核が hash を取り(`_hash_of`)、hash を持たない値は**入口の誤り**(freeze の ValueError、settle の Unsettled。place_order・出口の箱・口座はそれぞれの入口の誤りに替わる = 今の ValueError の道と同じ)で断る。`_dict_of`・`_set_of` の 2 か所で、辞書と集合の全ての作り方(freeze・settle の dict / set / frozenset / FrozenSet / FrozenDict)を通る。
- 受け手の `thaw` と `renew` は、核が作った入れ物からしか作らない(鍵は作った時に hash を取れた)ので、変えない。これを試験で確かめる(格子 E の「作れた物は thaw・renew も通る」)。
- 同じ根の全箇所: 核が作る値の型ごとに hash が例外を出すかを列べる(格子 E: BUILD の全ての型 × 値(sNaN・NaN・無限・0・大きな値)、入れ物 5 種 × 中の sNaN の位置)。

## 5. i0-r15-03(衝突した入れ子の FrozenDict の比べが 1 段 3 枠)

### なぜ起きたか(根本原因)

`FrozenDict.__eq__` は Python の method で、中で 2 つの dict を作り、インタプリタの dict の比べに渡す。値がまた FrozenDict なら、その比べがまた Python の method を呼ぶ。1 段ごとに「Python の枠 + 比べの入口 2 つ」の 3 枠を使う(実測 29・89・143)。第 15 周の私は核の歩きを反復にしたが、**核の値の等しさ**(インタプリタが hash の衝突のときに呼ぶ)は再帰のまま残し、契約には tuple で測った「1 段 1 枠」を全ての入れ物の事実として書いた。

### どの構造を変えるか

- **核の入れ物どうしの等しさを、核の反復の比べ `_plain_equal` にする**: 明示の積み上げで (x, y) の組を比べる。同一の物は等しい(インタプリタの入れ物の比べと同じ)。tuple・FrozenList は位置ごと、FrozenDict は鍵の対応ごと、frozenset・FrozenSet は要素の対応ごと、それ以外(平らな値)はその型の `==`。鍵と要素の対応は、相手の鍵を hash で引く表(鍵は核が作った物で hash を持つ。int の表なので比べは走らない)で作り、候補が 1 つならその組を積み、候補が複数(相手の中で hash が衝突する鍵)のときだけ候補ごとに `_plain_equal` を呼んで等しい物を探す。辞書の引きを使わない(辞書の引きは衝突した鍵の `==` を呼び、そこで再帰に戻るため)。
- `FrozenDict.__eq__` は、相手が FrozenDict ならこの比べを使う(外の Mapping との比べは今のまま、読み手自身の呼び出しの中)。
- これで、衝突した入れ子の値の比べは、tuple・frozenset の段は今のまま 1 段 1 枠(インタプリタの C)、FrozenDict から下は段数によらず決まった枠になる。契約の「1 段 1 枠」は事実になる(FrozenDict の段は 0 枠)。契約と `values.py` の注釈に、測った枠を型ごとに書く。
- 試験(格子 F): 入れ物の型の並び(tuple・FrozenList・frozenset・FrozenSet・FrozenDict の値の側・FrozenDict の鍵の側、混ぜた並び)× 段数 {1, 10, 30, 48, 97} × 衝突の置き方(一番下で違う・途中で違う・等しい)で、(a) `_plain_equal` と Python の `==`(素のプロセス、十分な枠)の答えが同じ、(b) freeze が要る枠が CALL_FRAMES + 2 × 段数 以下(批評家の試験と同じ上限)。

## 6. 先に書く敵対者の試験(委任文 §3「提出前の吟味」(6))

`tests/bt/item_0/test_bt0_r16_one_reading.py`。入力の空間は実装の場合分けから作らない:

- **格子 T(時刻)**: 値の型(Python の float・numpy float16/32/64・longdouble・int・Fraction・Decimal・文字列)× 単位(s・ms・us・ns)× 値(種つきの乱数で作る「十進で打った時刻」と「float が持つ値」の両方、整数の float、float の間隔が 1 ns より粗い大きな値、負、0、-0.0、inf、nan)。神託 = 2 つの読み方(型が持つ正確な値、型の十進の表記 = 文字列と Decimal はその文字、float は最短表記)が同じナノ秒の整数を言うならそのナノ秒、言わないなら断る。`to_nanos` の答えが神託と同じ。神託は `fractions.Fraction` と `decimal.Decimal` のライブラリで計算する(試験のプロセスは素のまま)。
- **格子 N(float の欄)**: 値の型(int・numpy の全ての整数・float・numpy float16/32/64・longdouble・Fraction・Decimal・文字列・bool・complex)× 値(2**53+1・1/3・0.1・大きな値・float の範囲の外・inf・nan)× 入口(`as_float`・`as_float(numbers_only=False)`・`take_float`・事象の価格・費用の模型の手数料)。神託 = 正確な値に最も近い float(`Fraction` と `float(Fraction)` のライブラリの正しい丸め)、または断る(bool・複素数・範囲の外・入口が受け付けない型)。同じ値が型で「受け付ける」と「断る」に分かれないこと。
- **格子 E(hash の無い値)**: §4 のとおり。
- **格子 F(衝突した入れ子の比べ)**: §5 のとおり。

列に入れなかったもの(試験のファイルに書く): numpy の複素数の欄(複素数は float の欄では断るので、型だけ 1 つ置く)、`datetime` の値(時刻の入口は `to_nanos(…, "iso")` で文字列だけ)、スレッドの文脈を替えた状態での格子 T(第 15 周の格子 B で `to_nanos` を含めて測った)。
