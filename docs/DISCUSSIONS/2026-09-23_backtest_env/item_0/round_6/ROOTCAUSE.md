# 項目 0「核」第 6 周 — 直す前の根本原因(作業者)

委任文: `docs/DATA/delegations/20260923_backtest_env_prompt.md`(起動文の指紋 `4c4cfc6e4052`。作業木の版を `sha256sum | cut -c1-12` で確かめて一致。全 162 行を読んだ)。
§3「根本的解決」に従い、起動文が渡した未解消の指摘 1 件ごとに「なぜ起きたか」と「どの構造を変えるか」を、直す前に書く。
合意した完了の形(委任文 §0 の逐語): 「**すべてが調査結果以上の信頼性と再現性に優れたものにすること。**」
固定した要件: `docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/REQUIREMENTS.md`(変えない)。行番号は第 5 周の終わり(この周の初め)の作業木のファイル。
一時ファイル: scratchpad の `bt/item0_r6_worker_*`。

## 0. この周に直す指摘

| id | 格 | 相手 | 前の指摘 | この周の初めに確かめたこと |
|---|---|---|---|---|
| i0-r5-01 | 止める | 実装 | i0-r4-02 の続き(2 周目) | 批評家の試験 `test_i0r5_fields_crossing_a_path_stay_live.py` → `4 failed`。下の A |
| i0-r5-05 | 直す | 実装 | なし | 下の B の再現で `FuturePositionError`(`LookAheadError` の子)を確かめた |
| i0-r5-07 | 示唆 | 実装 | なし | 起動文の対象ではないが、同じ「範囲の意味」の書き方の抜けなので C で契約に書く |
| i0-r5-02・03・04・06 | 止める・示唆 | 場面集 | — | 場面係の持ち物。作業者は変えない |

## A. i0-r5-01 路を渡る物が、`extra` の外で今も値になっていない(i0-r4-02 の続き)

### 再現(この周の初め、変える前)

- 批評家の試験 4 件が落ちる(`PYTHONPATH=src python3 -m pytest -p no:cacheprovider tests/bt/critic/item_0/test_i0r5_fields_crossing_a_path_stay_live.py` → `4 failed in 0.08s`)。
- 同じ根の別の穴を自分で探した(`scratchpad/bt/item0_r6_worker_probe_same_root.py`、出力は `…before.txt`。注文の遅れ 10 秒、戦略が変えるのは送った次の呼び出しの自分の変数だけ):
  - `side` に文字列でない物(何とでも等しいと答える物)を入れると通り、取引所の側で `repr` が送ったあとの戦略の状態を読む: `side=AnyEq(): [('OrderRequest', 'AnyEq(changed)', False, 1.0)]`。`in` の検査は「等しいと答えるか」しか見ない。
  - `post_only` は検査が無く、真偽を問われた時に戦略の状態を読む物が通る: `post_only=LiveBool(): [('OrderRequest', "'buy'", True, 1.0)]`(送った時は偽、届いた時は真)。`reduce_only`・`time_in_force` も検査が無い。
  - `OrderRequest` の子の class(読み出しを自分で書いたもの)が通る: `OrderRequest subclass: [('Sub', "'buy'", True, 1.0)]`。
  - 自分の `client_order_id` を付けた注文は、戦略が持つ物そのものが取引所まで渡り、`object.__setattr__` で送ったあとに大きさを変えられる: `object.__setattr__ after send (own id): [('OrderRequest', "'buy'", False, 500.0)]`(id を付けない注文は、核が id を入れるときに作り直すので 1.0 のまま。作り直すかどうかが id の有無という関係の無い条件で決まっていた)。
  - 逆向きの路: 約定の報告の `liquidity` に文字列でない物を入れると、戦略に届く通知の欄にその物がそのまま入る: `fill liquidity seen by strategy: ['placed', 'AnyEq(sent)']`。
  - 入力の路: データ源が核の事象の子の class や、事象に後から付けた属性を渡すと、戦略にそのまま届く: `source subclass / attached attr: [('LeakyTrade', 'source state', None), ('TradeEvent', None, "the source's iterator")]`。

### なぜ起きたか(3 段)

1. **「値である」の定義が、入れ物の形(リスト・辞書)にしか当てられていなかった。**第 5 周の根本原因 B は「路を渡る物は、作った時点で中身まで値である」と書いたが、固めたのは `extra` の入れ物だけで、スカラーの欄は「型の名前の検査」(`isinstance(…, str)`、`numbers.Real` の子、`in` による一致)で済ませた。型の名前の検査は「その型の**子**」を通す。子は送り手が書いた class で、自分の method(比べる・掛ける・文字にする)を持ち、それは受け手が使う時(届いた時刻)に走る。`in` の検査は `==` を呼ぶので、文字列ですらない物が通る。「値」を「値の型に属する」と取り違え、「その型そのもの(送り手の class ではない)」であることを求めていなかった。`freeze` が `Enum` の要素を受けたのも同じ(要素の class は戦略が書いた class)。
2. **欄ごとに検査を書き、全部の欄に当てる仕組みが無かった。**`OrderRequest`・`CancelRequest`・約定の報告(`Ack` ほか)・`FillNotice`・12 の事象型は、欄ごとに手で検査を書いていた。`post_only`・`reduce_only`・`time_in_force` のように検査が 1 行も無い欄があっても気づけない。第 5 周の試験 (f) は「ハッシュが取れるか」を見ていたが、`str` の子も何とでも等しいと答える物もハッシュが取れるので、穴を見つけられない(批評家の指摘のとおり)。
3. **路の入口で、受け手に渡す物が送り手の物と別であることを決めていなかった。**戦略 → 取引所の路は、id を付けない注文だけ作り直し(`dataclasses.replace`)、付けた注文は戦略の物をそのまま運んでいた。口座の強制注文は口座が作った物を戦略の注文の見え方にそのまま入れていた。データ源の事象は、核の class かどうかを見ていなかった。「作った時に値にする(第 5 周)」だけでは、送り手が同じ物を持ち続け、凍結を迂回して書き換える道が残る。

### どの構造を変えるか

「**路を渡る物は、核の class そのものの、欄が全部組み込みの型そのもの(子ではない)の値である**」を、1 つの部品と、全部の運び手に当てる 1 つの仕組みにする。

1. **値の部品を 1 つにする**(`src/bot/bt/core/values.py`)。欄の値を作る関数を 1 か所に置く: 文字(`as_text`)・数(`as_float`)・整数(`as_int`)・真偽(`as_flag`)・選択肢(`as_choice`、文字にしてから比べる)。どれも「組み込みの型そのもの」を返す。組み込みの型の**子**は、組み込みの型の側の読み出し(`str.__str__`・`float.__float__`・`int.__index__`・`complex.__complex__`・`bytes.__bytes__`)で中身だけを取り出す(子の method は 1 度も走らず、路を渡らない)。それ以外は受けない(呼び手が自分の誤りの型で包む)。`freeze` のスカラーも同じ関数で作る: `Enum` の要素は受けない(`IntEnum`・`StrEnum` は `int`・`str` の子なので中身の数・文字になる)。
2. **全部の運び手の全部の欄を、作る時にこの部品に通す**。`OrderRequest`(`post_only`・`reduce_only`・`time_in_force` を含む全部)、`CancelRequest`、約定の報告 `Ack`・`Reject`・`Fill`・`Canceled`・`StateUnknown`、`FillNotice`、12 の事象型の全部の欄(`seq`・`trade_id`・`tag`・`side` など)。報告の型の誤りは `VenueProtocolError`、事象は `EventValidationError`、注文は `OrderApiError`。
3. **運び手は属性を後から足せない形にする**(全部の運び手を `slots` の凍結データクラスにする。事象に「データ源の続き」を付けて運べなくなる)。
4. **路の入口で、核の class そのものだけを受け、受け手には送り手が持たない物を渡す**。戦略の発注・取消(`_OrderPort.place`・`cancel`)と口座の強制注文(`_force`)は、`type(x) is OrderRequest` / `CancelRequest` を求め、欄から作り直した新しい物を取引所の側に渡す(戦略の注文の見え方と取引所の側は別の物を持つ。id の有無で変わらない)。データ源の事象は、`type(event)` が核の 12 の class のどれかそのものであることを求める(子は `SourceEventTypeError`)。事象は作り直さない: 戦略に届くのは配達の時の写し(`engine.py` の `_deliver`)で、取引所の側に渡る元の物は、欄が値で属性を足せず子でもないので、データ源が凍結を `object.__setattr__` で迂回しない限り変わらない(迂回は解釈系の覗き見と同じく契約の外、と `CORE_CONTRACT` に書く。作り直すと 1 事象あたり約 2.4 マイクロ秒(`timeit` で 10 万回の構築を測った)、今の核の 1 事象あたり 14.5 マイクロ秒の約 17% が増える)。
5. **契約に運び手の一覧を機械で読める形で載せる**(`CORE_CONTRACT["channel_payloads"]["carriers"]`、class そのものから作る)。
6. **試験は欄を名指さずに、全部の運び手の全部の欄に当てる**(`tests/bt/item_0/`)。運び手ごとに正しい見本を 1 つ持ち、欄を 1 つずつ「その値の型の子で、読むたびに送り手の状態を返す物」に差し替えて作り直し、どの欄の値も組み込みの型そのもの(入れ子のタプルの中まで)で、差し替えた物の method が 1 度も呼ばれていないことを確かめる。核の凍結データクラスで運び手の一覧に無いものがあれば落ちる(新しい運び手の足し忘れを捕まえる)。加えて、戦略・口座・約定の模型・データ源の 4 つの送り手から、上の再現の全部が値になって届くことを実行で確かめる。

## B. i0-r5-05 区間を切った答え(過去)の外を名指すと「まだ届いていない」と言う

### 再現(この周の初め、変える前)

`scratchpad/bt/item0_r6_worker_probe_past_answer.py`(5 日分の日足、4 日目の呼び出し):
```
answer [101.0, 102.0]
delivered 4
2 ('FuturePositionError', True, '[2]: the index 2 names a position after the last event of this answer (it holds 2, positio')
slice(2, None, None) ('FuturePositionError', True, '[2:None:None]: the forward slice start 2 names a position after the last event of this ans')
reversed[len] ('FuturePositionError', True)
```
最後の行は同じ根の別の形: 届いた全部を後ろ向きに並べた答え `[::-1]` の最後の次は最も古い事象より前(過去)だが、これも「まだ届いていない」と言う。

### なぜ起きたか

**答え(`DeliveredEvents`)が「自分の最後の次に何があるか」という事実を持っていなかった。**第 5 周の位置の規則(`window.py` の `POSITION_RULE`)は「どこまで名指せるか」を 1 つの表から導くが、名指しが外れたときの**誤りの種類**は「答えの最後の次は、まだ届いていない事象」という 1 つの前提で決めていた。この前提が成り立つのは、答えが届いた最新の事象で終わるときだけで、`until_ns` で過去に切った答え、区間の区間で最新より前に終わる答え、後ろ向きに並べた答えでは成り立たない。答えを作る所(`api.py` の `visible_events`)は自分がどこで切ったかを知っているのに、その事実を答えに渡していなかった。

### どの構造を変えるか

1. **答えが「最後の次」の事実を持つ**(`window.py`)。`DeliveredEvents` は「最後の次の位置は、まだ届いていない事象か(`next_is_undelivered`)」を持つ。事実は class で持つ(値を後から変えられない。タプルの子は属性の場所を持てないため): 最新で終わる答えと、届いた過去の中で終わる答えの 2 つの class が `DeliveredEvents` の子になる。作る時に事実を必ず渡す(`DeliveredEvents(items, next_is_undelivered=…)`、既定値なし)。
2. **作る所が事実を決める**(`api.py` の `visible_events`): 答えの終わりが、その読み出しが見る届いた事象の列(型を絞ればその型の列)の終わりと同じなら「まだ届いていない」、そうでなければ「届いた過去の中」。
3. **区間の区間も事実を引き継ぐ**(`window.py` の `__getitem__`): 前向きの区間の結果の「最後の次」は、元の答えの位置 `start + len * step` に当たる。そこが元の答えの外(`>= len`)なら元の答えの事実を引き継ぎ、中なら「届いた過去の中」。後ろ向きの区間の結果の「最後の次」は、元の答えのより古い側なので常に「届いた過去の中」。
4. **誤りの種類を事実から決める**。名指せる範囲は今までどおり `POSITION_RULE` の 1 つの表から決め、外れたときに、答えの事実が「まだ届いていない」なら `FuturePositionError`(`LookAheadError` の子)、「届いた過去の中」なら新しい `OutsideAnswerError`(`IndexError` の子で `LookAheadError` の子ではない。文は「その位置の事象は届いているが、この答えの範囲の外。範囲を広げて読み直す」)。どちらも黙って空や切り詰めを返さない(i0-r4-01 の規則は変えない)。
5. 契約(`CORE_CONTRACT["visibility"]["position_rule"]`)に「誤りの種類は答えの事実で決まる」を書く。
6. 試験: 過去で切った答え(`until_ns`)・最新より前で終わる区間の区間・後ろ向きの答えは `OutsideAnswerError` で `LookAheadError` ではないこと。最新で終わる答え(型を絞った答え・`n` で絞った答え・`since_ns` の答えを含む)は今までどおり `FuturePositionError`。事実の決め方は実装を読まずに作った方法(同じ読み出しを、あとに届く事象を足した世界で行い、名指した位置に「届いた事象」があれば過去)で突き合わせる。

## C. i0-r5-07(示唆)実行の時刻の範囲は時計を縛らない

**なぜ起きたか**: `time_span_ns` の役目は「入力の事象の時刻の単位の誤りを捕まえる」ことだが、名前と説明が「この実行の時刻の範囲」と読めるのに、何に当てて何に当てないかを契約に書いていなかった。

**どの構造を変えるか**: 振る舞いは変えない(時計や通知の時刻は核が作る時刻で、単位を取り違える入力ではない。範囲の外の時計を断ると、範囲の終わりの直後に建玉を閉じる時計のような正当な使い方を断ることになる)。契約 `CORE_CONTRACT["run_settings"]["time_span_ns"]` と `CoreEngine` の説明に「入力の事象の 2 つの時刻だけを検める。戦略の時計・通知・発注の時刻は縛らない(実行の終わりは `end_time_ns`)」と書き、試験で固定する。

## D. 変える構造のまとめ(この周)

1. 路を渡る物の値の部品を 1 つにし(`values.py` の `as_text`・`as_float`・`as_int`・`as_flag`・`as_choice`・`freeze`)、全部の運び手の全部の欄を作る時に通す。運び手は `slots` の凍結データクラス。路の入口は核の class そのものだけを受け、戦略と口座の注文は作り直して渡す(A)。
2. 履歴の答えが「最後の次」の事実を class で持ち、誤りの種類をそこから決める(B)。
3. 実行の時刻の範囲が何を縛るかを契約に書く(C)。

## E. 直している途中で見つけて足したこと(同じ根。直した後に追記)

- **差し込み口の答えと流れの名前**: 遅延の模型の遅れ(`int(value)` で子の `__int__` を読んでいた)、費用の模型の手数料(`float(fee)`)、口座の拒否の理由(`not reason` で子の `__len__` を呼んでいた)、流れの名前(`sorted` が子の `__lt__` を呼び、併合の順を決めていた)も、返された時に 1 度だけ組み込みの値として読む(`engine.py` の `_check_delay`・`_handle_reports`・`_venue_order`・`_SourceMerger.__init__`)。名前が組み込みの文字に直して重なれば断る。契約 `CORE_CONTRACT["channel_payloads"]["plug_in_answers"]`。
- **配達の写しの作り方**: 事象を `slots` にしたら `copy.copy` が `__getstate__`/`__setstate__` を通って 1 回 4.4 マイクロ秒かかり、核が 1 事象あたり 16.2 → 20.3 マイクロ秒に遅くなった(`scratchpad/bt/item0_r6_worker_digest_speed.py`、5 万事象の 3 回の最小)。配達の写しを欄ごとの写し(`engine.py` の `_delivered_copy`、核の class そのものだけが届くので欄の一覧は class から作る)に替え、14.2 マイクロ秒(第 5 周の 16.2 より速い)。配達の要約(`delivery_digest`)は第 5 周と同じ値 `35269aee…` のまま(同じ入力で突き合わせた)。
- **数の上限**: 浮動小数に入らない整数(`10**400`)は、`OverflowError` のまま漏れず、運び手の誤りの型で断る(`values.as_float`)。
