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

- **float の時刻は、float が持つ正確な値(`float.as_integer_ratio`)で読み、int の演算で倍率を掛け、ナノ秒より細かい桁があれば断る**(批評家の直し方の向きと同じ)。最短の表記は読まない。`1700000000123456.75` us(float が正確に持つ)は 1700000000123456750 ns、`1700000000.123` s(持つ値は 1700000000.1229999065399169921875)は断る。断りの文には持つ値を書く(`… (it holds 1700000000.1229999065399169921875) has sub-nanosecond digits`)。
- **numpy longdouble も持つ値で読む**(numpy 自身の C の `as_integer_ratio`)。float が持てるかどうかに依らない。これで断りの文も「型を断った」ではなく「持つ値にナノ秒より細かい桁がある」になる(i0-r15-07)。numpy の float16/32/64 は今と同じく float に正確に移してから同じ規則。
- 型を断るとき(平らな値でない型)と、数の正確な変換が失敗したときの断りの文を分ける(`values.plain_scalar` の理由を文に残す = i0-r15-07)。
- int・Fraction・Decimal・文字列は今のまま(値そのもの)。
- 契約の文(`time.py` の説明・`TIME_CONTRACT` の rounding)を、この規則に書き替える。受け付けが変わる振る舞い(`to_nanos(1700000000.123456, "s")` を断る。前は最短表記で ...123456000 と受け付けた)を、自分の試験 `test_bt0_time.py` の書き替えと理由で残す。

**途中で規則を替えた記録**: 最初は「2 つの読み方(持つ値と最短表記)が同じ数を言うときだけ受け付ける」にした(float が持つ値と、呼び手が打った十進の両方で黙って違う値を出さないため)。書いた後に、場面係が並行して作っている P0-2 の単位の場面(`tests/bt/battery/item_0/ROOTCAUSE_r16-1.md` の主張 11)が、正解を「入力が持つ値(float は二進の値)× 倍率がナノ秒の整数ならその整数」と置いていることを読んだ。批評家 i0-r15-01 の向きも同じ。核が見えるのは float が持つ値だけで、Python 自身も `float("1700000000123456.8") == 1700000000123456.75` と答える(打った十進は float に残っていない)。「一致するときだけ」の規則は、float が正確に持つ整数ナノ秒(`1704067200.001953125` s など)を断り、場面の正解と合わない(規則 5 の「対応なし」)。よって持つ値で読む形に替えた。場面集は読むだけで、正解を核に合わせたのではない(場面係の正解は核を見ずに閉じた式で決めてある)。

採らなかった案: (a) 「2 つの読み方が一致するときだけ受け付ける」 — 上のとおり、float が正確に持つ時刻を断る。(b) 今の最短表記のまま — float が持つ値を黙って替える(指摘そのもの)。

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

- **格子 T(時刻)**: 値の型(Python の float・numpy float16/32/64・longdouble・int・Fraction・Decimal・文字列)× 単位(s・ms・us・ns)× 値(種つきの乱数で作る「十進で打った時刻」と「float が持つ値」の両方、整数の float、float の間隔が 1 ns より粗い大きな値、負、0、-0.0、inf、nan、float が持てない longdouble)。神託 = 入力が持つ値(文字列と Decimal はその十進、float と numpy の浮動小数は `as_integer_ratio`、int と Fraction はそれ自身)× 倍率が int64 の範囲のナノ秒の整数ならその整数、でなければ断る。最短表記は読まない。神託は `fractions.Fraction` と `decimal.Decimal` のライブラリで計算する(試験のプロセスは素のまま)。前の周の自分の格子 C の神託 `_stated_ns` は float を最短表記で読んでいた(実装の読み方を写していた)ので、同じ規則に書き替える。
- **格子 N(float の欄)**: 値の型(int・numpy の全ての整数・float・numpy float16/32/64・longdouble・Fraction・Decimal・文字列・bool・complex)× 値(2**53+1・1/3・0.1・大きな値・float の範囲の外・inf・nan)× 入口(`as_float`・`as_float(numbers_only=False)`・`take_float`・事象の価格・費用の模型の手数料)。神託 = 正確な値に最も近い float(`Fraction` と `float(Fraction)` のライブラリの正しい丸め)、または断る(bool・複素数・範囲の外・入口が受け付けない型)。同じ値が型で「受け付ける」と「断る」に分かれないこと。
- **格子 E(hash の無い値)**: §4 のとおり。
- **格子 F(衝突した入れ子の比べ)**: §5 のとおり。

列に入れなかったもの(試験のファイルに書く): numpy の複素数の欄(複素数は float の欄では断るので、型だけ 1 つ置く)、`datetime` の値(時刻の入口は `to_nanos(…, "iso")` で文字列だけ)、スレッドの文脈を替えた状態での格子 T(第 15 周の格子 B で `to_nanos` を含めて測った)。

## 7. 厳しい批評家が [止める] にしそうな点と、返す前に潰した結果

1. **float の時刻を持つ値で読むと、打った十進と違う時刻を返さないか**(`float("1700000000123456.8")` は ...456750 ns になる)→ 核が受け取るのは float だけで、その float は Python でも `== 1700000000123456.75`。打った十進は float に残っていない。十進の時刻は文字列か Decimal で渡す、と `time.py` の説明と断りの文に書いた。場面係の単位の場面(持つ値 × 倍率)とも、批評家の i0-r15-01 の神託とも合う(`test_bt0_scene_set.py` の単位の場面が全部通る)。
2. **float の時刻で受け付けを狭めた(`1700000000.123456` s を断る)のは「機能を外して要件から逃げる」ではないか** → 持つ値にナノ秒より細かい桁がある値を丸めずに断る、は契約の「rounding: none」そのもの。int・文字列・Decimal は全部の時刻を運べる。断りの文に持つ値を書く。前の周まで受け付けていたのは最短表記で読んで値を替えていたから(i0-r15-01)。自分の試験 `test_bt0_time.py` の 1 か所を理由つきで書き替えた。
3. **float の欄で桁の多い値を丸めて受け付けるのは「黙って値を替える」ではないか** → 欄の型が float と宣言されているので、最も近い float は欄の意味(文字列の価格 "0.1" も同じ)。変えたのは、型によって丸めと断りが分かれていたこと(同じ値の答えが型で違う)で、今は全ての型で同じ答え(格子 N の `test_one_value_is_taken_alike_by_every_class_that_holds_it`)。有限の値を inf にすることはしない(範囲の外は全ての型で同じ文で断る = `_beyond`)。平らな値(`freeze`・`settle`)は今も正確でなければ断る(`_now`、int → float の検めを足した)。
4. **核の比べ `_plain_equal` が Python の `==` と違う答えを出さないか** → 格子 F の (a) と、種 16 の乱数の核の値 200 個の組 3,000 以上を、ライブラリの型に写した神託(同じ物は同じ写しにして、インタプリタの同一性の近道を保つ)と照らした。核が作らない入れ物(公開の `FrozenDict(...)` に入れた dict など)はその型の `==` に任せる(`test_a_caller_made_frozendict_holding_a_dict_compares_as_python_says`)。
5. **hash の検めを足した所は、入口の誤りに替える以外に振る舞いを変えないか** → hash を持つ値の道は同じ(`_hashed` は hash を取るだけ)。hash を持たない値は前もインタプリタの TypeError で止まっていたので、受け付けが狭まった値は無い。値や list の要素の sNaN は今も受け付け、thaw・renew も通る(格子 E)。
6. **i0-r15-03 は批評家の試験の上限(2 × 段数)に合わせただけではないか** → 比べの作りを反復に替え、FrozenDict から下は段数によらず 11〜14 枠(実測)。自分の試験は契約の文どおりの「CALL_FRAMES + 段数」で縛り、批評家の上限より厳しい。
7. **場面集だけを特別扱いしていないか** → 核の変更に場面の id・場面の値の分岐は無い(`git diff 0f2e07d -- src/bot/bt/core` に scenes の語は無い)。場面集は読むだけで、自分の場面の試験(`tests/bt/item_0/test_bt0_scene_set.py`)に単位の場面の駆動を足した(正解が「無い」場面は断ることを確かめる = 規則 5)。
8. **速さ** → 第 15 周と同じ測り(2 万本の足、ほかの試験と同時): この周 77.89 / 72.74 us/bar、直す前の核(0f2e07d)72.80 / 70.32 us/bar(`<W>/item0_r16_worker_speed.out`)。ほかの試験が同時に走っていて揺れが大きく、差は揺れの中と読む(未確認: 静かな機械で測っていない)。

## 8. 直したあとの確かめ(コマンドと出力)

直した場所(ファイル:行は直した後の作業木。リードが途中の版を 2786cd4 にコミットしたので、差分は `git diff 0f2e07d` で見る):
- i0-r15-01・07: `src/bot/bt/core/time.py` 175 行(longdouble は `values.longdouble_ratio` で持つ値)、201 行(float は `float.as_integer_ratio`)、212 行(断りの文に持つ値)、188 行(数の変換の失敗の理由を残す)、80 行(`TIME_CONTRACT` の rounding)、説明の文 13〜31 行。`values.py` 1205 行 `is_longdouble`・1210 行 `longdouble_ratio`・1221 行 `plain_scalar`。
- i0-r15-04: `values.py` 827 行 `_beyond`・834 行 `_nearest_of`・868 行 `_longdouble_nearest`・794 行 `decimal_float`(有限の値を inf にしない)・1155 行 `take_float`・1279 行 `as_float`・588 行(`_exactly_converted` に int → float の検め。`_now` の「EXACTLY」を事実にした)。
- i0-r15-02: `values.py` 1032 行 `_hashed`、1043 行 `_dict_of`、1056 行 `_set_of`。
- i0-r15-03: `values.py` 1429 行 `_container_kind`・1439 行 `_match`・1471 行 `_plain_equal`、1387 行(`FrozenDict.__eq__` が使う)、647・657 行の注釈。
- 契約: `contract.py` 15 行(版 `core-17`)、process_state の比べの文(182 行から)と hash の無い鍵の文、plug_in_answers の fee の文。`PLAIN_DATA_RULE`・`FIELD_RULE`(values.py)。

確かめ:
- 批評家の第 15 周の試験 3 本 + 第 14 周の時刻の試験: `PYTHONPATH=src python -m pytest tests/bt/critic/item_0/test_i0r15_float_time_rounded_by_shortest_repr.py tests/bt/critic/item_0/test_i0r15_unhashable_key_refusal_type.py tests/bt/critic/item_0/test_i0r15_colliding_frozendict_frames.py tests/bt/critic/item_0/test_i0r14_time_values_silently_changed.py -p no:cacheprovider` → `50 passed in 0.21s`(`<W>/pytest_item0_r16_worker_critic_after.log`)。直す前は第 15 周の 3 本が `28 failed, 12 passed`。
- 批評家の試し `item0_r15_critic_probe_float_field_exactness.py` → int・numpy int64・Fraction・numpy longdouble の 2**53+1 が全部 `9007199254740992.0`、Fraction 1/3 と longdouble 1/3 が全部 `0.3333333333333333`(前は longdouble だけ断った)。
- 新しい格子(§6、`tests/bt/item_0/test_bt0_r16_one_reading.py`): 直す前の核(`git archive 0f2e07d src/bot` を `<W>/head_src` に取り出し、`-o pythonpath=` で差し替え)で `563 failed, 2466 passed`(`<W>/pytest_item0_r16_worker_prefix3.log`: 格子 T 499・格子 N 31 + 5 + 1・格子 E 16・格子 F 9 ほか)。直した後 `3029 passed`。
- 衝突した入れ子の値の freeze が要る枠(`<W>/item0_r16_worker_probe_frames_after.out`): tuple・FrozenList・frozenset・FrozenSet は 1・10・30・48・97 段で 10・16・36・54・103、FrozenDict の値の側は 10・11・11・11・11、鍵の側は 10・12・12・12・12、混ぜた並びは 10・13・13・13・14。直す前の FrozenDict は 10 段 34・30 段 94・48 段 148(1 段 3 枠)。
- 項目 0・批評家・場面集を含む全試験(切り離して 1 回。場面集の実行はこの 1 回): `PYTHONPATH=src python -m pytest -p no:cacheprovider -rf` → `13 failed, 9349 passed, 6 skipped, 4 warnings in 987.24s (0:16:27)`(`<W>/pytest_item0_r16_worker_full.log`)。落ちた 13 件は全部 `tests/bt/battery/item_0/` の場面集の試験で、場面係が並行して直している途中の物(落ち方の文: 升目の判断の文言が「測っていない」と「測っていない(固定した測り方の外)」で食い違う / 足した単位の場面 `p2-*-{text,int,float-*}` を相手の結果がまだ持たない `('1', 'opp_basana')` / DEFINITIONS の段落の数 108 と 105)。`git status --short tests/bt/battery` で場面係の未コミットの変更(adapter・grid_c・CONSIDERED ほか)が見える。核の値に触れる落ち方は無い。`tests/bt/item_0` と `tests/bt/critic/item_0` に落ちたものは無い。
- 書き直した自分の試験(消した試験は無い): `test_bt0_time.py`(float 1700000000.123456 s は持つ値にナノ秒より細かい桁があるので断る、に書き替え。1700000000.5 s と文字列を足した)、`test_bt0_r15_library_code.py`(格子 C の神託 `_stated_ns` を最短表記から持つ値に。longdouble も持つ値)、`test_bt0_r14_process_state.py`(版 `core-17`)、`test_bt0_scene_set.py`(場面係が足した単位の場面の駆動。正解が「無い」場面は断ることを確かめる)。
