# 項目 0「核」第 13 周 — 直す前の根本原因(作業者)

委任文: `docs/DATA/delegations/20260923_backtest_env_prompt.md`(起動文の指紋 `56394f7b1686`。`sha256sum … | cut -c1-12` → `56394f7b1686` で作業木の版と一致。全 165 行を読んだ)。
合意した完了の形(委任文 §0 の逐語): 「**すべてが調査結果以上の信頼性と再現性に優れたものにすること。**」
固定した要件: `item_0/REQUIREMENTS.md`(変えない)。リードの設計: `round_7/LEAD_DESIGN.md`。この周の作業者に当たるのは §9.3 の 37〜41 で、41 の逐語は「作業者は第 13 周で、批評家が i0-r11-01・03 の直りを確かめるのを待つ(新しい実装の側の指摘は無い)」。起動文の作業者あての文は「契約の文に 88.2 バイト/件の実測を残す以外は、実装を変えずに待つ(周の試験と報告だけ)」。
一時ファイルは `/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/r13_worker/`(以下 `<W>`)。`<S>` = その 1 つ上。

## 0. この周に直す対象の指摘と、この周の初めに確かめたこと

| id | 格 | 相手 | repeat_of | この周の初めに確かめたこと(コマンドと出力) |
|---|---|---|---|---|
| i0-r11-01 | 直す | 実装 | i0-r9-02 | `PYTHONPATH=src python -m pytest tests/bt/critic/item_0/test_i0r11_class_dict_key_runs_foreign_code.py tests/bt/critic/item_0/test_i0r11_pinned_dropped_facts_fail_the_core_step.py tests/bt/critic/item_0/test_i0r11_history_limit_exact_refusal.py -p no:cacheprovider` → `23 passed in 0.75s`。批評家の試しを回し直した(`<W>/item0_r13_worker_recheck_r11_critic_probes.out`): module_key_nometa → `step/run/result -> EngineFailedError | is EngineFailedError: True`・`Key.__eq__ ran in: []`、outbox_key → `Msg -> run raised OrderApiError | OrderApiError: True`・`[]`、registry_key → `raise: True -> run ok [('mine-1', 'FILLED')]`・`strategy code outside on_event: 0 []`、outbox_metahash → `run raised OrderApiError | OrderApiError: True`・`[]` |
| i0-r11-03 | 直す | 実装 | i0-r9-02 | 同じ試験の実行に入っている(`test_i0r11_pinned_dropped_facts_fail_the_core_step.py` は通る)。批評家の試し array_export → `hold views: True -> run ok, events 12 digest 06cfb720ce34`(持たないときの `hold views: False -> run ok, events 12 digest 06cfb720ce34` と同じ) |

(場面集の側の i0-r11-02 は場面係が直す。作業者は場面集を変えない。)

## A. i0-r11-01(外の class の辞書の鍵・戦略の台帳の鍵の `__eq__` が、持ち主の呼び出しの外で走る)

### なぜ起きたか(根本原因)
第 11 周の規則は「外の物には、その物の class を通さず、基の型の C の関数と `type` の記述子だけを使う」という**呼ぶ関数の一覧**で書かれていた。外のコードが走るかどうかは、呼ぶ関数ではなく**その操作が参照する状態**で決まる。ハッシュ表の検索と書き込みは表の中の鍵の `__eq__` を呼ぶ(class の辞書で `'__module__'` を引く `type` の記述子、戦略の台帳への `dict.__setitem__`)。探す鍵の hash はメタクラスの `__hash__` を呼ぶ。タプルの `in` は `==` を呼ぶ。第 11 周の格子は「外の物の種類 × その物の方法」を列べ、「核の操作が参照する状態」の軸を持たなかった(LEAD_DESIGN §2 と同じ、扱う物の一覧の外)。詳細は `round_12/ROOTCAUSE.md` §A の 1〜3。

### どの構造を変えたか(第 12 周。この周は変えない)
規則を「外の者の呼び出しの外で、核がその者の物に行う操作は、核が作って誰にも届かない物か、静的な(C の)型だけで結果が決まる操作に限る」に替えた。型の判断は同一性だけ(`values.py` の `IdTable`・`is_one_of`・`derives`)。名前は `type` の C の欄と class の辞書の反復で読み、検索しない(`class_parts`)。核が戦略の側へ書くのは `list.append` だけにし、台帳の更新は戦略の口の呼び出しの中で行う(`engine.py` `_show`、`api.py` `_bring_up`)。

## B. i0-r11-03(戦略が持つ memoryview で、核の `array.extend` が BufferError で落ちる)

### なぜ起きたか(根本原因)
A と同じ根。第 10 周の区分(`_StrategySide`)は「核の状態から戦略の側を参照しない」を決めたが、**核が戦略の側へ書く操作の種類**を決めていなかった。書く操作のうち、戦略が何をしていても必ず同じ結果で終わり外のコードを走らせないのは、核が作った list への `list.append` だけで、`array.extend`(buffer を書き出している間は大きさを変えられない)は違う。詳細は `round_12/ROOTCAUSE.md` §A の 2。

### どの構造を変えたか(第 12 周。この周は変えない)
核は落とすたびに新しい `array('q')` の塊を戦略の側の pending の list に `list.append` するだけにし、まとめる操作は戦略の読み出し(`history.read_dropped`)の中で行う。まとめる先が buffer を書き出していれば新しい配列を作る(`history.py` `DroppedFacts`・`read_dropped`・`_grown`)。

## C. リードの答え(LEAD_DESIGN §9.3)とこの周にすること

| 番号 | リードの答え(要旨ではなく該当語) | この周にすること |
|---|---|---|
| 37 | 「**認める**」(`__qualname__` を type の C の欄から、`__module__` を class の辞書の反復で取る読み方) | 変えない |
| 38 | 「**認める**。88.2 バイト/件の実測を契約 history_limit の文に残す」 | 契約の文に足す(下の D)。実測はこの周に測り直した |
| 39 | 「契約 core-14 に書いたことで足りる」 | 変えない |
| 40 | 「項目 12・13 の要件を固定するときに決める」 | 変えない |
| 41 | 「作業者は第 13 周で、批評家が i0-r11-01・03 の直りを確かめるのを待つ」 | 実装を変えない。周の試験と報告だけ |

## D. この周の変更(契約の文だけ。実装の構造は変えない)

1. **88.2 バイト/件の実測を契約 `visibility.history_limit` に残した**(§9.3 の 38)。測り直し: `python3 <W>/item0_r13_worker_fact_bytes.py` → `array('q') x2: 16.9 bytes/fact | list of int x2: 88.2 bytes/fact`(Python 3.11.15。第 12 周の `<S>/r12_worker/item0_r12_worker_fact_bytes.py` の写しで、同じ値)。
2. **同じ文の中の誤りを直した**: 第 12 周の文は落とすたびの塊を「an array of about 64 bytes plus the facts」と書いていたが、実測は違う。`python3 <W>/item0_r13_worker_chunk_bytes.py` → `sys.getsizeof(array('q')) = 80 | sys.getsizeof(chunk) = 96 | tracemalloc per chunk incl. the list slot: 104.1 bytes`。また 1 回に落とすのは `history_limit + 1` 件である(`history.py` の `DeliveredHistory.append`: `cut = len(facts) - (limit - 1)` を `len(facts) >= 2 * limit` のときに行う)。文を「a drop removes history_limit + 1 events of one type: by sys.getsizeof 80 bytes plus 16 per dropped event, and 8 for its slot in the pending list, on CPython 3.11」に替えた。
3. **契約の文を実装に縛る試験を足した**: `tests/bt/item_0/test_bt0_r13_dropped_fact_storage.py`(25 件)。入力は history_limit 1〜6 × 1 つの型の配達数 0〜(6 × limit + 3) × 読み方 3 通り(最後にだけ読む / 毎回読む / 毎回読んで memoryview を持つ)。神託は入力だけから出す(2 × limit 件を持つときに古い limit + 1 件を落とす)。確かめる物: 塊は落とすたびに 1 つで中身はその回に落とした事実、塊の大きさの伸びは 1 件 16 バイト、読み出しの後の配列は 1 件 8 バイト(と array 自身の割り増し)、pending は空、view を持っても読みは全部。列に入れなかった物は試験のファイルの説明に書いた。

## E. 厳しい批評家が [止める] にしそうな点と、したこと

1. **「前の周から変わった構造が無い周」**(委任文 §3「根本的解決」): この周の作業者の変更は契約の文と試験だけで、実装の構造は変えていない。リードの §9.3 の 41 と起動文が「実装を変えずに待つ」と指示した周である。周に数えるかは台本とリードが決める(作業者は判定しない)。
2. **数の ABC の穴(契約 `scope` の「対象外」)を実測した**: 契約は「numbers の ABC に派生・登録した、`__subclasshook__` かメタクラスのフックを持つ class」を対象外にし、理由を「class を定義することはプログラムを変えること」としている。戦略が `on_event` の中で `numbers.Integral` の子をメタクラスつきで作り、遅延の模型が `numpy.float32` を返すと、核が `values._settle` の静的な型の分岐で `issubclass(t, numbers.Integral)` を聞き、ABC の仕組みが戦略の class の `__subclasscheck__` を**戦略の呼び出しの外で**呼ぶ: `PYTHONPATH=src python3 <W>/item0_r13_worker_probe_numbers_abc.py` → `run -> LatencyModelError order_delay_ns must return an int of ns: order_delay_ns must be an int, got numpy.float32` / `party __subclasscheck__ calls: [('outside', 'float32')]`。断りの型は入口の誤り(LatencyModelError)のままで、黙って誤った値は無い。第 12 周の格子の説明と契約に対象外として書かれている物で、この周の指示(実装を変えない)の外なので直していない。「戦略が on_event の中で書く class の定義」を「プログラムを変えること」と数えてよいかは作業者が決められないので、リードに聞く(報告の「リードに聞くこと」)。直すなら、ABC に聞かずに、静的な型の MRO の中の型を同一性で数の ABC の登録と比べる形が候補になる。ただし numpy の型の扱いが変わるかは測っていない(未確認)。
3. **契約の文の数が実測と違っていた**(D の 2): 直した。ほかの数(16 バイト/件、N..2N)は試験で縛った。
