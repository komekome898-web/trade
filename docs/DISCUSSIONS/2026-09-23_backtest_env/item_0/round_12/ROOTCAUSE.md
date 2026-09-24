# 項目 0「核」第 12 周 — 直す前の根本原因(作業者)

委任文: `docs/DATA/delegations/20260923_backtest_env_prompt.md`(起動文の指紋 `d3eae0d221c9`。`sha256sum … | cut -c1-12` で作業木の版と一致を確かめ、全 164 行を読んだ)。
合意した完了の形(委任文 §0 の逐語): 「**すべてが調査結果以上の信頼性と再現性に優れたものにすること。**」
固定した要件: `item_0/REQUIREMENTS.md`(変えない)。リードの設計: `round_7/LEAD_DESIGN.md`(作業者に当たるのは §3.3・§3.4・§7.4 の 19・20・§8.3・§8.5 の 26・27)。
行番号はこの周の初め(HEAD `b7cbd63` の作業木)のもの。一時ファイルは `/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/r12_worker/`(以下 `<W>`)。

## 0. この周に直す指摘と、この周の初めに確かめたこと

| id | 格 | 相手 | repeat_of | この周の初めに確かめたこと(コマンドと出力) |
|---|---|---|---|---|
| i0-r9-01 | 直す | 実装 | null | 第 11 周の批評家が「直った」と確かめた(`round_11/CRITIC.md` の表)。この周の終わりに批評家の神託と試験で確かめ直す(報告の (1)) |
| i0-r9-02 | 直す | 実装 | i0-r8-01 | 同上(第 9 周の 2 つの道は直った。同じ族の別の形が i0-r11-01・i0-r11-03) |
| i0-r11-01 | 直す | 実装 | i0-r9-02 | `PYTHONPATH=src python -m pytest tests/bt/critic/item_0/test_i0r11_class_dict_key_runs_foreign_code.py -p no:cacheprovider` → 12 件とも落ちる |
| i0-r11-03 | 直す | 実装 | i0-r9-02 | `… test_i0r11_pinned_dropped_facts_fail_the_core_step.py` → `E BufferError: cannot resize an array that is exporting buffers`(`history.py:176`) |

(i0-r11-02・i0-r11-04 は相手が場面集で、場面係が直す。作業者は場面集を変えない。)

## A. 根本原因(i0-r11-01 と i0-r11-03 は同じ根。族 i0-r8-01 → i0-r9-02)

### なぜ起きたか

1. **第 11 周の規則は「誰の関数を呼ぶか」で書かれていた。**規則は「外の物に触るときは、その物の class を通さず、基の型の C の関数と `type` 自身の記述子だけを使う。これらは外のコードを走らせない」だった。この前提は偽である。外のコードが走るか、操作が失敗するかは、**呼ぶ関数ではなく、その操作が参照する状態**で決まる。基の型の C の関数でも、外の者が決められる状態を参照すれば、外のコードが走るか、失敗する:
   - **ハッシュ表の検索と書き込み**は、表にすでにある鍵の `__eq__` を呼ぶ(同じ hash のとき)。`type.__dict__["__module__"]` の記述子は、class 自身の辞書で `'__module__'` を検索する(`values.py:181`・`200`)。class の辞書の鍵は、その class を作った者が決められる(i0-r11-01 (a))。戦略の注文の台帳は戦略が届く dict で、戦略が鍵を足せる。核は `on_event` の後に `dict.__setitem__` で書く(`engine.py:1087-1090` `_show`。i0-r11-01 (b))。
   - **ハッシュ表の検索**は、探す鍵の hash を呼ぶ。外の class を鍵にした `BUILD.get(t)`(`values.py:297`・`340`)・`_CLASS_TO_TYPE.get(type(event))`(`engine.py:644`)は、その class のメタクラスの `__hash__` を走らせる(i0-r11-01 の補足)。
   - **`x in タプル`** は、要素ごとに `==` を呼ぶ。`type(report) not in REPORT_CLASSES`(`engine.py:293`・`1266`)・`base in mro`(`values.py:287`)・`c in mro`(`values.py:344`)・`nb in mro`(`values.py:376`)・`t not in (tuple, …)`(`values.py:542`)は、外の class のメタクラスの `__eq__` を走らせる。
   - **その場での大きさの変更**は、その物が buffer を書き出していると断られる。落とした事象の事実の `array('q')` は戦略が届く物で(`engine.py:1060-1063` の `dropped_of` の既定値)、核は落とすたびに `array.extend` で伸ばす(`history.py:176-177`)。戦略が `memoryview` を持つだけで核の手順が `BufferError` で落ちる(i0-r11-03)。
   - **真偽・長さ・反復**は、その物の `__bool__`・`__len__`・`__iter__` を呼ぶ。約定模型と口座の答え(`engine.py:1265` `raw or ()`・`1181` `… or ()` とその反復)。
   - **数の変換**は、その数の `__index__`・`__int__`・`__float__` を呼ぶ。差し込み口の答えの数(`engine.py:519-526` `_check_delay`・`1296` の手数料 → `values.py:258-272` `_now`)は、Python の class の数(数の塔に登録した物)なら、その class のコードを呼び出しの後で走らせる。
   - **属性の普通の読み**は、メタクラスの `__getattribute__` と class の辞書の鍵を走らせる。`api.py:226-229` `fresh_request` の断りの文は `type(request).__module__`・`__qualname__` を普通に読む(口座の強制注文が `OrderRequest` の子のとき)。
   確かめ(直す前): `PYTHONPATH=src python3 <W>/item0_r12_worker_probe_same_root.py` →
   `fill model answer is a list subclass: run -> ok | party code outside its call: ['Answer.__bool__', 'Answer.__bool__', 'Answer.__iter__', 'Answer.__bool__', 'Answer.__bool__']` /
   `fill model report of a class with a metaclass __eq__: run -> VenueProtocolError | party code outside its call: ['Answer.__bool__', 'Meta.__eq__', …]` /
   `latency answer is a numeric-tower number of a Python class: run -> ok | party code outside its call: ['Num.__index__', 'Num.__index__', 'Num.__index__']` /
   `account's forced order of an OrderRequest subclass: run -> AccountSocketError | party code outside its call: ['NameMeta __module__', 'NameMeta __qualname__']`(出力 `<W>/item0_r12_worker_probe_same_root.before.out`)。
2. **核は、戦略の側の物をその場で書き換えていた。**第 10 周の区分(`_StrategySide`)は「核の状態から戦略の側を参照しない」を決めたが、核が戦略の側へ書く操作の種類は決めていなかった。書く操作のうち、戦略が何をしていても必ず同じ結果で終わり外のコードを走らせないのは、核が作った list への `list.append`(と、戦略から届かない核の入れ物の差し替え)だけで、`dict.__setitem__`(鍵の `__eq__`)と `array.extend`(buffer の書き出し)は違う。
3. **なぜ第 11 周の試験で見つけられなかったか**: 第 11 周の格子は「外の物の種類 × その物の方法」(例外の作り 14 種、型が持つ変更の方法)を列べた。**核の操作が参照する状態**(ハッシュ表の中の鍵、探す鍵の hash、`==`、buffer の書き出し、真偽・反復、数の変換)の軸が無かった。LEAD_DESIGN §2 と同じ形(扱う物の一覧の外)。

### どの構造を変えるか(規則は 1 つ。契約 `channel_payloads.ownership`・`scope`・`lifecycle`・`type_decisions` に同じ趣旨を置く)

**規則**: 外の者(戦略・差し込み口・入力の流れ)の呼び出しの外で、核がその者の作った物・届く物に行う操作は、**核が作って誰にも届かない物か、静的な型(C で書かれ、外の者が振る舞いを変えられない型)だけで結果が決まる操作**に限る。

1. **型の判断は同一性(`is`)だけで行う**(`values.py`): 表の検索は `id(型)` を鍵にした核の表(鍵は核が作った int だけ)と `is` の確かめ、MRO の中の探索は `is` の比較。外の class をハッシュ表の鍵にしない、`==` で比べない。
2. **型の名前は検索せずに読む**(`values.class_parts`): 名前は `type` の C の欄(`__qualname__`)。モジュールは、静的な型なら `type` の記述子(`tp_name` から作る。辞書を引かない)、Python で作った型なら **class 自身の辞書を反復して**、鍵がちょうど str の `'__module__'` である値を取る(反復は鍵を比べない)。
3. **答えの取り方(呼び出しの後)を 1 つにする**(`values.settle`): 値は、組み込みの型(とその子。基の型の方法で読む)、静的な型の数(numpy の数。C のコードで変換する)、組み込みの入れ物(とその子。基の型の方法で反復する)だけを受け、Python の class の数(数の塔)・それ以外は、そのコードを走らせずに入口の誤りで断る。これを出口の箱(第 10 周から)に加え、**差し込み口の数の答え**(遅延・手数料)・**差し込み口の入れ物の答え**(約定模型の報告の列・口座の強制注文の列: 規約の `Sequence` どおり list / tuple とその子を基の型で反復)・**運び手の作り直し**(`rebuild_carrier`: 各欄を settle してから作り直す。送り手が後から欄に入れた物のコードを走らせない)に当てる。呼び出しの中(送り手が運び手を作るとき)の変換は今までどおり(その者の呼び出しの中)。
4. **核が戦略の側へ書くのは `list.append` だけにする**(`engine.py` `_show`、`history.py` `HistoryLists`): 注文の見え方は戦略の側の記録の列(list)に足し、台帳(dict)への反映は**戦略の呼び出しの中**で、口の呼び出し(`order`・`open_orders`・`place_order`・`cancel_order`)の初めに行う。落とした事象の事実は、落とすたびに新しい小さな `array('q')` を戦略の側の列に足し、戦略の読み出し(`dropped_of`)の中で大きな配列へまとめる(まとめる先が buffer を書き出していれば新しい配列を作る)。戦略が届く物に何をしていても、核の書き込みは同じ結果で終わり、外のコードを走らせない。戦略の変更が効くのは戦略自身が読む物だけ(契約 `scope`)。

### 試験(先に書く。LEAD_DESIGN §3.3)

`tests/bt/item_0/test_bt0_r12_party_hooks.py`: 規則の入力の空間を、実装の場合分けからではなく、**入口の宣言した型**(差し込み口の規約の戻りの注釈 `socket_methods` と `typing.get_type_hints`、入力の流れの `Event`、戦略の例外と出口の箱の知らせ)× **形**(宣言した型の子 / 宣言した型の中身に外の値 / 宣言と無関係な物)× **仕掛け**(Python の特殊な方法の名前を組み込みの型から機械で列べた全部)× **置き場所**(物の class / メタクラス / class の辞書に同じ hash の鍵)で列べる。加えて、戦略が届く物の全部(gc の参照で歩く)に「内容を変えずに操作を縛る」仕掛け(辞書と集合に核が書きうる全ての鍵と同じ hash の鍵、buffer を書き出す物の memoryview)を置く。神託: 仕掛けたコードが、仕掛けた者の呼び出しの外で 0 回走る、かつ、実行が仕掛けない実行と同じか、入口の誤り(`CoreError`)で断る(以後は `EngineFailedError`)。列に入れなかった物は試験のファイルに書く。

## B. i0-r9-01・i0-r9-02(第 11 周の批評家が直りを確かめた物)

構造は変えない。A の直しの後で、第 11 周の批評家の神託(`item0_r11_critic_probe_history_oracle2.py`)・到達性の試し(`item0_r11_critic_probe_reach_swap.py`)・試験(`test_i0r11_history_limit_exact_refusal.py`・第 9〜11 周の格子)を回し直す。A の 4(落とした事実のまとめを読み出しの中へ移す)は i0-r9-01 の読み出しの規則に触れるので、神託の全格子を回して確かめる。

## C. 直しの途中で見つけた同じ根の箇所(上の §A・§B はコードを変える前に書いたもの)

| 見つけた形 | なぜ同じ根か | 直した構造 |
|---|---|---|
| `api.py:226-229` `fresh_request` の断りの文が `type(request).__module__`・`__qualname__` を普通に読む(口座の強制注文が `OrderRequest` の子のとき、メタクラスの `__getattribute__` と class の辞書の鍵が走る) | 外の class の属性を普通に読む(§A の 1 の最後の形) | `type_name` を使う(検索しない読み) |
| `engine.py:287` `_VenueLedger.apply` が型を確かめる**前に** `type(report).__name__` を普通に読む | 同上(今は核が作り直した報告しか来ないが、順序が規則と逆) | 同一性の確かめの後に移した |
| `values.py:542` `_freeze` の `t not in (tuple, …)` | タプルの `in` は `==` を呼ぶ(§A の 1) | `is_one_of`(同一性) |
| 例外のメタクラスの `__subclasscheck__` は、例外が枠(関数の呼び出し)を抜けるたびに**解釈系自身**が聞く(核のコードが無くても起きる: `<W>/item0_r12_worker_dbg2_interpreter_subclasscheck.py` → `subclasscheck E <class '__main__.E'>` が 3 回) | 核の操作ではない(解釈系が例外を運ぶ仕組み)。契約 `lifecycle` は例外を変えずに投げ直すと決めている | 構造は変えない。契約 `scope` の「対象外」に後始末と並べて書き、試験で「例外が抜けた後の `step`・`run`・`result` はメタクラスの方法を 1 つも走らせない」を固定した(`test_after_a_raised_exception_escaped_the_later_calls_ask_nothing_of_its_class`) |

## D. リードの答え §8.6 の 31(22:00 UTC。この周の作業の途中で出た)との対応

- 「外の物を dict の鍵にしない」: 核が外の物を鍵にする表は無くなった(`IdTable` の鍵は核が作った int。戦略の台帳への書き込みは戦略の呼び出しの中だけ)。
- 「外の class の属性(`__module__`・`__name__` を含む)を読まない」: 普通の読み(`getattr`・`.` での読み)はしない。名前は `type` の C の欄から、モジュールは class の辞書を**反復**して取る(検索しない。どちらもコードを走らせない。格子の `dict` の置き場所で全ての名前と同じ hash の鍵を置いて確かめた)。「読まない」を文字どおりに取ると、断りの文と `result().models` に型の名前を書けなくなる(契約 `type_decisions`「naming the real type in full」、第 11 周の格子 1 の神託「文に実際の型の名前がある」)。この読みでよいかを報告の「リードに聞くこと」に書く。
- 「外の物の buffer を参照で持たない(落とした事実の array は戦略に buffer を出さない = memoryview を作れない型か、写しを渡す)」: この周の作りは第 3 の形である。核は、戦略に渡した配列を**二度と変えない**(落とすたびに新しい小さな配列を戦略の側の list に足すだけ)。まとめる操作は戦略の読み出しの中で行い、まとめる先が固定されていれば新しい配列を作る。核の手順は戦略が持つ buffer に一切依存しない。memoryview を作れない型(int の list)は 1 件あたり 88.2 バイト(`<W>/item0_r12_worker_fact_bytes.py` → `array('q') x2: 16.9 bytes/fact | list of int x2: 88.2 bytes/fact`)で、契約の 16 バイトの 5 倍を超え、呼び出しごとの写しは件数に比例して遅くなる(§7.4 の 19 が「件数に比例して遅くする作りは取らない」とした)。この形でよいかを「リードに聞くこと」に書く。
- 「格子は外の物の型の方法を全部差し替える敵対者で回す」: 格子 1 は、組み込みの型から機械で列べた特殊な方法 81 個(メタクラスは 83 個)を、1 つずつと全部同時に、物の class とメタクラスに置き、class の辞書には 140 の名前と同じ hash の鍵を置く。
