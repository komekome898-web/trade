# 項目 0「核」第 7 周 — 直す前の根本原因(作業者)

委任文: `docs/DATA/delegations/20260923_backtest_env_prompt.md`(起動文の指紋 `4c4cfc6e4052`。作業木の版を `sha256sum | cut -c1-12` で確かめて一致。全 162 行を読んだ)。
§3「根本的解決」に従い、起動文が渡した未解消の指摘(実装の側)1 件ごとに「なぜ起きたか」と「どの構造を変えるか」を、直す前に書く。
合意した完了の形(委任文 §0 の逐語): 「**すべてが調査結果以上の信頼性と再現性に優れたものにすること。**」
固定した要件: `docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/REQUIREMENTS.md`(変えない)。行番号はこの周の初め(コミット `6e6d6ae` の作業木)のファイル。
一時ファイル: `/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/item0_r7_worker_*`。

## 0. この周に直す指摘

| id | 格 | 相手 | 前の指摘 | この周の初めに確かめたこと |
|---|---|---|---|---|
| i0-r6-01 | 止める | 実装 | i0-r5-05 の続き | 批評家の試験 `test_i0r6_past_answer_names_undelivered.py` → `4 failed, 2 passed`。自分の試し(下の A)で、192 通りの名指しのうち 63 通りで誤りの種類が違う |
| i0-r6-03 | 直す | 実装 | なし | 自分の試し(下の B)で、送り手の値を入れた 54 通りのうち 37 通りで断る型がその所の誤りの型でなく(`grep -c WRONG-TYPE` → 37)、1 通り(`visible_events(event_type=偽の EventType)`)は黙って空の答えを返す |
| i0-r5-01 | 止める | 実装 | i0-r4-02 | 第 6 周で直った(批評家の 1.2 の確かめ)。同じ根の残り(`isinstance` が物の申告を信じる)が i0-r6-03 で、下の B で一緒に直す |
| i0-r5-05 | 直す | 実装 | なし | i0-r6-01 に付け直された。下の A で直す |
| i0-r6-02・i0-r6-04 | 止める・直す | 場面集 | — | 場面係の持ち物。作業者は変えない |

## A. i0-r6-01 過去で終わる答えの先を名指すと、届いていない事象でも「届いた」と言い、`LookAheadError` にならない

### 再現(この周の初め、変える前)

- 批評家の試験: `PYTHONPATH=src python3 -m pytest -p no:cacheprovider tests/bt/critic/item_0/test_i0r6_past_answer_names_undelivered.py` → `4 failed, 2 passed in 0.07s`。
- 同じ根の別の形を自分で探した(`scratchpad/bt/item0_r7_worker_probe_answer_kind.py`、日足 12 本、10 本目の呼び出し。答えの形 8 つ × 答えの先の 12 位置と前の 12 位置。名指した位置を「その読み出しが読む列」の位置に戻し、入力でそこが「届いた / まだ届いていない / 何も無い」かを決める。核の規則は読まない)。出力 `…answer_kind.before.txt`: `checked 192 namings, wrong kind 63`。内訳(`awk` で数えた):
  - `until day6` の答え(7 本)の先: まだ届いていない位置 9 通りが `OutsideAnswerError`(批評家の指摘の形)。
  - `all[0:6:3]`・`all[1:8:2]`(歩幅つきの区間): まだ届いていない位置 10 通り・11 通りが `OutsideAnswerError`(批評家の指摘の形)。
  - **後ろ向きの答え(`all[::-1]`・`n=3[::-1]`・`until day6[::-1]`)に負の添字で答えの前(= 新しい側)を名指すと**、まだ届いていない位置 12・12・9 通りが**ただの `IndexError`**(`tuple` の既定の誤り)。批評家が挙げていない、同じ根の別の穴。
  - 誤りの文の誤り: 後ろ向きの答えの最後の次(最も古い事象より前 = 何も無い)を名指すと「the events after it were delivered」と言う(批評家の probe の `all[::-1] [10]`)。

### なぜ起きたか

1. **答えが持つ事実が「最後の次の 1 位置」のことだけだった。**第 6 周の直し(根本原因 B)は、答えに「最後の次の位置は、まだ届いていない事象か」(`next_is_undelivered`)を 1 つ持たせ、`window.py` の `_check_bound` は、名指した位置がどこであってもこの 1 つだけで誤りの種類を選んだ。しかし名指しは最後の次より先にも、答えの前(負の添字)にも届く。答えの中の位置と「その読み出しが読む列」の位置の対応(どこから始まり、どちら向きに何個おきか)と、その列のうち何個が届いていたかを答えが持っていなかったので、名指した位置が届いた事象か・まだ届いていない事象か・何も無いかを**決める材料が答えに無かった**。作業者自身が第 6 周の根本原因 B-6 に「名指した位置に『届いた事象』があれば過去」と書いたのに、実装はその材料を持たなかった。
2. **負の添字は規則の外に置いていた。**`_check_bound` は `b >= 0` の名指ししか見ず、負の添字で答えの前を名指すと `tuple.__getitem__` の既定の `IndexError` がそのまま出た。前向きの答えでは答えの前は「過去」なので害が見えなかったが、後ろ向きの答えでは答えの前は新しい側で、まだ届いていない事象を名指す。
3. **試験が実装の規則を写していた。**`test_every_index_and_slice_matches_the_probe_oracle` は「最後より先のどの名指しも答えの事実と同じ種類」を正解に置き、`test_the_fact_agrees_with_the_input_at_every_callback` は `ans[len(ans)]` の 1 位置しか試さなかった。入力から決める神託を、全部の名指しに当てていなかった。
4. (同じ根の小さい穴)区間の境界(`slice` の `start`・`stop`・`step`)は、検める時と `tuple` で切る時に、それぞれ `__index__` を呼んでいた。呼ばれるたびに違う数を返す物を境界に渡すと、検めた数と切った数が違い、検めを素通りできる(自分で気づいた。変える前の実物で確かめる試験を足す)。

### どの構造を変えるか

1. **答えが「読み出しが読む列の中の自分の場所」を持つ**(`window.py`)。`DeliveredEvents` は、答えの位置 `i` が読み出しの列の位置 `first + i * step` に当たること、その列のうち読み出しの時に届いていた数 `delivered`、列の最も古い事象より前に `history_limit` が落とした事象があるか `dropped_before` を持つ(`AnswerPlace`、読むだけ。作った後に変えられない)。区間の区間は、元の答えの場所から自分の場所を計算して持つ(`first + start * step`、`step * st`)。
2. **誤りの種類を、名指した位置から決める**。名指した位置 `q`(添字、区間の各境界が名指す位置。負の添字も)を列の位置 `u = first + q * step` に戻し、`u >= delivered` なら `FuturePositionError`(`LookAheadError` の子)、`0 <= u < delivered` なら `OutsideAnswerError`(届いたが答えの外)、`u < 0` なら、落とした事象があれば `DroppedPositionError`(`OutsideAnswerError` と `HistoryTruncatedError` の子)、無ければ `BeforeFirstEventError`(`OutsideAnswerError` の子。その位置には何も届いていない)。区間の境界が 2 つとも外れたときは、まだ届いていない位置を名指す方を先に報せる(先読みの試みは必ず `LookAheadError` で捕まる)。名指せる範囲そのもの(`POSITION_RULE` の表)は変えない。負の区間の境界が切り詰められる決まり(`tuple` と同じ)も変えない(切り詰めは答えの中にしか届かない)。
3. **誤りに事実を載せる**: 名指した答えの位置・列の位置・届いていた数を誤りの属性に持たせ、文にも書く(「読み出しの時に届いていた数」と書き、答えを後の呼び出しまで持ち越したときの意味も明記する)。
4. **区間の境界は 1 度だけ読む**: `operator.index` で 1 度だけ整数にした `slice` を作り、検めと切り出しと場所の計算に同じ物を使う。添字と区間の判定は `type(index) is slice`(`slice` は子を作れない。`__class__` を偽る物で分岐が変わらない)。
5. **作る所が場所を決める**(`api.py` の `visible_events`): 答えの最初の事象の列の位置 `lo`(空の答えは切った所 `hi`)、`step = 1`、`delivered = len(列)`、`dropped_before`(型を絞った読み出しは、その型に落とした事象があるか。全部の読み出しは、列の最も古い事象の配達番号が 1 より大きいか。配達番号は 1 から欠けなく振られ、落とされなかった事象は全部列に残るので、1 より大きければその前は落とされた)。
6. **契約**(`CORE_CONTRACT["visibility"]["position_rule"]`)に、誤りの種類は名指した位置が列のどこに当たるかで決まることと、4 つの種類を書く。
7. **試験**(`tests/bt/item_0/`): 入力から決める神託(名指した位置を列に戻し、入力とその呼び出しの時刻で「届いた / まだ / 何も無い / 落とした」を決める)を、全部の読み出しの形(型・全部・`until_ns`・`since_ns`・`n`・`history_limit`)と、全部の添字(負を含む)と区間の区間(区間の区間の区間まで)に当てる。前の周の試験のうち、実装の規則を写した 2 本(`test_every_index_and_slice_matches_the_probe_oracle` の種類の判定と `test_the_fact_agrees_with_the_input_at_every_callback`)は、この神託で書き直す(消す主張は報告に書く)。

## B. i0-r6-03 組み込みの型を偽る物・numpy の真偽が、運び手の誤りの型でなく生の `TypeError` か、誤った文で断られる

### 再現(この周の初め、変える前)

`scratchpad/bt/item0_r7_worker_probe_senders.py`(送り手の値が核に入る所を全部並べ、`__class__` を偽る物と numpy の値を入れる。期待する誤りの型は、その所の説明に書かれた型)。出力 `…senders.before.txt` から抜き出す:

```
OrderRequest.size=Spoof(float)	REFUSED	builtins.TypeError	WRONG-TYPE	descriptor '__float__' requires a 'float' object but received a 'Spoof'
OrderRequest.post_only=np.bool_	REFUSED	bot.bt.core.errors.OrderApiError	ok	post_only must be a bool, got bool
OrderRequest.extra=Spoof(tuple)	REFUSED	builtins.TypeError	WRONG-TYPE	'Spoof' object is not iterable
OrderRequest.extra=(('k',np.int64(3)),)	REFUSED	bot.bt.core.errors.OrderApiError	ok	extra['k'] holds a numpy.int64, which is not plain data …
OrderRequest.size=np.float32	ACCEPTED		<class 'float'>
Ack(Spoof(str))	REFUSED	builtins.TypeError	WRONG-TYPE	…
Trade.received_time_ns=Spoof(int)	REFUSED	builtins.TypeError	WRONG-TYPE	descriptor '__index__' requires a 'int' object …
to_nanos(Spoof(str),'iso')	REFUSED	builtins.AttributeError	WRONG-TYPE	'Spoof' object has no attribute 'strip'
ctx.visible_events(Spoof(EventType))	ACCEPTED	_EndsAtNewest	()
ctx.visible_events(n=np.int64(1))	REFUSED	bot.bt.core.errors.OrderApiError	ok	n must be an int, got np.int64(1)
answer[Spoof(slice)]	REFUSED	builtins.AttributeError	WRONG-TYPE	'Spoof' object has no attribute 'start'
latency.order_delay=Spoof(int)	REFUSED	builtins.TypeError	WRONG-TYPE	…
cost=Spoof(float)	REFUSED	builtins.TypeError	WRONG-TYPE	…
account.check_order=Spoof(str)	REFUSED	builtins.TypeError	WRONG-TYPE	…
source yields Spoof(TradeEvent)	REFUSED	builtins.AttributeError	WRONG-TYPE	'Spoof' object has no attribute 'EVENT_TYPE'
history_limit=Spoof(int)	REFUSED	builtins.TypeError	WRONG-TYPE	'<' not supported between instances of 'Spoof' and 'int'
history_limit=np.int64(3)	ACCEPTED	int	3
```

批評家が挙げた `values.py` の 3 関数のほかに、同じ根の所が核の全体にある: 注文・取消・報告・事象の全部の欄、時刻の変換(`validate_nanos`・`to_nanos`)、履歴の読み出しの引数(`event_type`・`n`・`since_ns`)、答えの添字、差し込み口の答え(遅れ・手数料・拒否の理由・強制注文)、データ源(流れの名前・事象)、実行の設定(`time_span_ns`・`end_time_ns`・`history_limit`)。**`visible_events(event_type=偽の EventType)` は誤りを出さず、黙って空の答えを返す**(信頼性を崩す形。批評家は挙げていない)。numpy の数も所によって受けたり断ったりする(`size=np.float32` は受けるのに `extra` の `np.int64` と `n=np.int64(1)` は断る、`history_limit=np.int64(3)` は受ける)。

### なぜ起きたか

1. **型の判定に `isinstance` を使い、物の申告を信じていた。**`isinstance(x, C)` は、本当の型 `type(x)` が `C` の子でなくても、物の `__class__` が `C` の子なら真を返す。`__class__` は物が自分で答える属性なので、送り手の物は好きな型を名乗れる。核はその後で本当の型を求める読み出し(`float.__float__`・`str.__str__`・`int.__index__`、`.strip()`、属性)を呼ぶので、判定と読み出しが**違う事実**(申告と本当の型)を見ていた。判定を通った物が読み出しで生の誤りを出すのはそのため。第 6 周で「路を渡る物は組み込みの型そのもの」と決めたが、「その型かどうか」を物の申告で決めていた。
2. **「どの外来の値を受けるか」を所ごとに書いていた。**numpy の数を受けるかどうかは、`as_float` は `numbers.Real`、`as_int` と `validate_nanos` は `numbers.Integral`、`_count_arg` は `int` の子だけ、`scalar`(`extra`)は組み込みの子だけ、`as_flag` は `bool` だけ、と所ごとに違う決まりだった。決まりが 1 つでないので、同じ値が所によって受けられたり断られたりし、断る文も型の短い名(`__name__`)を使うので `numpy.bool` を「bool」と書いた。
3. **断り方の型を、所ごとに包み直していた。**`values.py` は `ValueError` を出し、呼び手が包む約束だったが、呼び手の一部は `values.py` を呼ぶ前に自分で `isinstance` の判定を持ち(`_require_positive`・`_check_delay`・手数料・拒否の理由・`_count_arg`・流れの名前)、`values.py` の `ValueError` を包まずに通す所もあった(流れの名前・拒否の理由)。

### どの構造を変えるか

1. **型の判定は本当の型だけで行う**(`values.py` に 1 つの部品): `is_a(x, C)` = `issubclass(type(x), C)`。`type(x)` は物が答えを変えられない(`__class__` を偽っても変わらない)。組み込みの読み出し(`str.__str__` など)が確かめるのも同じ本当の型なので、判定を通った物は読み出しで落ちない。核の中で送り手の値の型を判定する所は全部これにする(`events.py`・`api.py`・`interfaces.py`・`engine.py`・`time.py`・`ordering.py`・`window.py`)。核が自分で作った物の判定(配達した通知の型など)は変えない。
2. **外来の値を受ける決まりを 1 つにする**(`values.py` の `scalar`): 組み込みの型そのもの → そのまま / 組み込みの型の子 → 組み込みの型の読み出しで中身だけ / numpy の真偽 → numpy の読み出し(`numpy.bool_.__bool__`)で `bool` / 数の塔(`numbers.Integral` → `int`、`numbers.Real` → `float`、`numbers.Complex` → `complex`)→ いま 1 度だけ変換し、組み込みの型そのものにする / それ以外 → 断る。`as_text`・`as_float`・`as_int`・`as_flag` は、この 1 つの決まりで値にしてから、自分の欄の型(文字・数・整数・真偽)を求める。numpy の真偽を真偽の欄に受ける(pandas・numpy の比較が普通に作る値で、`bool` にしかならない)。数の欄には真偽を受けない(今までどおり)。numpy は取り込まない(`sys.modules` に既にあるときだけ見る。numpy の値があるなら numpy は取り込み済み)。
3. **断る文は本当の型の完全な名前**(`モジュール.名前`)を書く(`numpy.bool` を「bool」と書かない)。
4. **断り方の型は所の型にする**: `values.py` は `ValueError` だけを出し(送り手の変換の中の誤りも `ValueError` に包む)、呼び手は必ず自分の誤りの型で包む。呼び手が `values.py` の前に持っていた自分の型の判定は外し、`values.py` の 1 つの決まりに任せる(判定が 2 つあると、また食い違う)。
5. **履歴の読み出しの `event_type` は `EventType` の要素そのもの**(`type(x) is EventType`)を求め、偽る物は `OrderApiError` で断る(黙って空を返さない)。
6. **試験**: 送り手の値が入る所を全部並べた表で、偽る物・numpy の値・普通の値を入れ、(a) 断るなら所の誤りの型で断ること、(b) 受けるなら欄の値が組み込みの型そのもので、偽る物の method が 1 度も走っていないこと、(c) 同じ値は所によらず同じ扱い(数の欄どうし・整数の欄どうし・真偽の欄どうし)であること、を確かめる。表に無い所が増えたら落ちる仕組みは第 6 周の運び手の一覧(`PATH_CARRIERS`)の試験が持つ。

## C. 変える構造のまとめ(この周)

1. 履歴の答えが「読み出しの列の中の自分の場所」を持ち、誤りの種類を名指した位置から 4 つのどれかに決める(A)。
2. 送り手の値の型は本当の型で判定し、外来の値を受ける決まりを 1 つにし、断る型は所の型にする(B)。

## D. 直している途中で見つけて足したこと(同じ根。直した後に追記)

- **落とした事象の数(A の同じ根)**: `history_limit` の下では、答えの最も古い事象より前の位置が「落とした事象」か「何も無い」かを分けるには、落とした数が要る。第 1 案の「落としたか(真偽)」では、落とした数より前(何も届いていない所)まで「落とした」と言った(自分の神託の試験 `test_every_named_position_with_a_history_limit` が 102 件の食い違いで見つけた)。履歴に型ごとの落とした数を持たせ(`history.py` の `dropped_count`)、答えの場所は `dropped`(数)を持つ。全部の読み出しの落とした数は、列の最も古い事象の配達番号 − 1(配達番号は欠けなく振られ、落とされなかった事象は全部残るため)。
- **場所を言えない空の答え**: `until_ns` が落とした事象の間で切った空の答えは、切った所が落とした事象のどこかで、履歴はそれを覚えていないので、場所を言えない。黙って誤った場所を言わず、`HistoryTruncatedError` で断る(落とした部分に届く読み出しを断る今の決まりと同じ扱い)。切った所が落とした最も新しい事象以後なら場所は正確に決まるので答える(`api.py` の `__empty_answer`、試験 `test_an_empty_answer_cut_inside_the_dropped_part_is_refused`)。
- **注文の見え方の読み出し** `ctx.order(id)`: 文字でない物(文字を名乗る物を含む)を渡すと、黙って `None`(知らない注文)を返していた。`visible_events(event_type=偽)` の黙った空と同じ形なので、id を本当の型で文字にし、違えば `OrderApiError`。
- **データ源の事象の型**: 核の `Event` の子で自分の型(`EVENT_TYPE`)を持たない class を流すと、`SourceEventTypeError` でなく生の `AttributeError` が出た。核の 12 の class そのものから型への対応(`engine.py` の `_CLASS_TO_TYPE`)で引き、無ければ `SourceEventTypeError`。
- **内部の履歴の見え方** `EventWindow`: 文脈の私的な属性から届くので、添字と区間の判定を本当の型(`type(index) is slice`、`operator.index`)にそろえた。
- **速さ**: 答えを作るたびに場所を検めると、読み出しの多い戦略で 1 事象あたり 18.6 → 23.6 マイクロ秒になった(`scratchpad/bt/item0_r7_worker_speed.py`、5 万事象、3 回の最小)。核の中で作る答え(`visible_events` と区間)は場所が作りから正しいので検めない作り方(`DeliveredEvents._placed`)に分け、外から作るときだけ検める。直した後(読み出しなし / あり、1 事象あたりマイクロ秒、`scratchpad/bt/item0_r7_worker_speed.txt`): 1 回目は始めの版 13.49 / 22.6、今の版 12.34 / 21.78。2 回目は始めの版 14.13 / 21.05、今の版 14.34 / 22.48。差は回ごとのばらつきの幅の中。配達の要約(`delivery_digest`)は始めの版と同じ `35269aeea5ca…`。
