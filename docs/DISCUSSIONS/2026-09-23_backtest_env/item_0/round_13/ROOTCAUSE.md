# 項目 0「核」第 13 周 — 直す前の根本原因(作業者)

委任文: `docs/DATA/delegations/20260923_backtest_env_prompt.md`(10 回目の再開の起動文の指紋 `e1952f4a41cf`。`sha256sum docs/DATA/delegations/20260923_backtest_env_prompt.md | cut -c1-12` → `e1952f4a41cf` で作業木の版と一致。全 166 行を読んだ)。
**この版について**: 第 13 周の作業者は、コンテナの再起動で止まった run の最初の起動(委任文 `56394f7b1686` の版)で一度走り、その成果(下の D の契約の文と試験)は途中保存のコミット(`115112d`・`dc9e04a`)で作業木にある。委任文の版が変わったので作業者が走り直した(LEAD_DESIGN §9.9 の 45)。走り直しの作業者(この版の書き手)は、下の 0 の確かめと D の実測を作業木の今の版でやり直し、結果を同じ表に書いた(走り直しの一時ファイルは `<S>/r13_worker_rerun/`。最初の版の一時ファイル `<S>/r13_worker/` は残してある)。実装・契約・試験は、この走り直しでは変えていない。
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

## F. 走り直し(10 回目の再開、委任文 `e1952f4a41cf`)で作業木の今の版に対して確かめ直したこと

`<R>` = `<S>/r13_worker_rerun`。実装・契約・試験はこの走り直しでは変えていない(`git status --short` で `src/bot/bt/`・`tests/bt/item_0/` に差分なし。最初の版の成果はコミット `115112d`・`dc9e04a` にある)。

1. **i0-r11-01・03 の直り**(批評家の試験): `PYTHONPATH=src python -m pytest tests/bt/critic/item_0/test_i0r11_class_dict_key_runs_foreign_code.py tests/bt/critic/item_0/test_i0r11_pinned_dropped_facts_fail_the_core_step.py tests/bt/critic/item_0/test_i0r11_history_limit_exact_refusal.py tests/bt/item_0/test_bt0_r13_dropped_fact_storage.py -p no:cacheprovider` → `48 passed in 0.89s`(批評家の 23 件 + この周の 25 件)。
2. **批評家の試しを回し直した**(`<R>/item0_r13_worker_rerun_recheck_r11_critic_probes.out`): array_export → `hold views: True -> run ok, events 12 digest 06cfb720ce34`(持たないときと同じ)/ module_key_nometa → `step/run/result -> EngineFailedError | is EngineFailedError: True`・`Key.__eq__ ran in: []` / outbox_key → `Msg -> run raised OrderApiError | OrderApiError: True`・`[]` / outbox_metahash → `run raised OrderApiError | OrderApiError: True`・`[]` / registry_key → `raise: True -> run ok [('mine-1', 'FILLED')]`・`strategy code outside on_event: 0 []` / reach_swap → `callbacks with core state shared: []`・`uses of those classes OUTSIDE on_event: [] count 0`。sockets_key は `.out` だけで試しの本体が scratchpad に無い(`find <S> -name '*sockets_key*'` → `.out` の 1 件)ので回し直せない。同じ 3 つの口(約定の模型・口座・入力の流れ)は批評家の試験 `test_i0r11_class_dict_key_runs_foreign_code.py` の 12 件に入っており、それは上の 1 で通った。history_oracle2 は引数を 2 つ取る試しで、i0-r11-01・03 の対象ではないので回していない。
3. **88.2 バイト/件の実測を測り直した**(§9.3 の 38): `python3 <R>/item0_r13_worker_rerun_fact_bytes.py` → `array('q') x2: 16.9 bytes/fact | list of int x2: 88.2 bytes/fact`(Python 3.11.15)。`PYTHONPATH=src python3 <R>/item0_r13_worker_rerun_chunk_bytes.py` → `sys.getsizeof(array('q')) = 80 | sys.getsizeof(chunk) = 96 | tracemalloc per chunk incl. the list slot: 104.1 bytes`。契約 `src/bot/bt/core/contract.py:81-93` の文と同じ値。
4. **E の 2(数の ABC のフック)を測り直した**: `PYTHONPATH=src python3 <R>/item0_r13_worker_rerun_probe_numbers_abc.py` → `run -> LatencyModelError order_delay_ns must return an int of ns: order_delay_ns must be an int, got numpy.float32` / `party __subclasscheck__ calls: [('outside', 'float32')]`。最初の版と同じで、LEAD_DESIGN にまだ答えが無い(§9.9〜§9.14 に該当の語なし: `grep -n 'ABC\|subclasscheck\|作る:0#13' round_7/LEAD_DESIGN.md` → §9.9 の 45 の「作る:0#13」(走り直しの説明)だけ)。この周の指示(実装を変えない)の外なので直さず、報告の「リードに聞くこと」に再び書く。

## G. 11 回目の起動(委任文 `cdf623e4fb24`)での走り直し

委任文を全部読んだ(`wc -l` → 169 行、`sha256sum docs/DATA/delegations/20260923_backtest_env_prompt.md | cut -c1-12` → `cdf623e4fb24` で起動文の指紋と一致)。LEAD_DESIGN は §9.3 の 37〜41 と §9.9〜§10.2 を読み直した。上の「リードに聞くこと」の 2 件(数の ABC のフック / 契約の文の塊の大きさの直しが指示の範囲か)への答えは、まだ無い(`grep -n 'ABC\|subclasscheck\|about 64' round_7/LEAD_DESIGN.md` → 該当なし)。よってこの走り直しでも実装・契約・試験を変えていない(`git status --short src/bot/bt tests/bt/item_0` → 出力なし)。`<N>` = `<S>/r13_worker_run11`。

1. **i0-r11-01・03 の直り(批評家の試験)**: `PYTHONPATH=src python -m pytest tests/bt/critic/item_0/test_i0r11_class_dict_key_runs_foreign_code.py tests/bt/critic/item_0/test_i0r11_pinned_dropped_facts_fail_the_core_step.py tests/bt/critic/item_0/test_i0r11_history_limit_exact_refusal.py tests/bt/critic/item_0/test_i0r11_covers_within_scene_input.py tests/bt/item_0/test_bt0_r13_dropped_fact_storage.py -p no:cacheprovider -rs` → `80 passed in 0.84s`(批評家の i0-r11 の試験 4 本と、この周の 25 件。場面集の側の covers_within の 13 件も今の作業木では通る)。
2. **項目 0 と批評家の試験の全部**: `PYTHONPATH=src python -m pytest tests/bt/item_0 tests/bt/critic/item_0 -p no:cacheprovider` → `1830 passed, 2 skipped in 342.18s (0:05:42)`。飛ばした 2 件は前からの物(`tests/bt/item_0/test_bt0_carriers.py:144` 「bool cannot be subclassed」、`tests/bt/critic/item_0/test_i0r5_battery_opponent_grading.py:130` 調査の venv が無いとき)。
3. **批評家の試しを回し直した**(`<N>/item0_r13_worker_run11_recheck_r11_critic_probes.out`): array_export → `hold views: True -> run ok, events 12 digest 06cfb720ce34`(持たないときと同じ)/ module_key_nometa → `step/run/result -> EngineFailedError | is EngineFailedError: True`・`Key.__eq__ ran in: []` / module_key → `strategy code run outside on_event: []` / outbox_key → `Msg -> run raised OrderApiError | OrderApiError: True`・`[]` / outbox_metahash → `run raised OrderApiError | OrderApiError: True`・`[]` / registry_key → `raise: True -> run ok [('mine-1', 'FILLED')]`・`strategy code outside on_event: 0 []` / reach_swap → `callbacks with core state shared: []`・`uses of those classes OUTSIDE on_event: [] count 0`。
4. **88.2 バイト/件を測り直した**(§9.3 の 38): `python3 <N>/item0_r13_worker_run11_fact_bytes.py` → `array('q') x2: 16.9 bytes/fact | list of int x2: 88.2 bytes/fact`、`PYTHONPATH=src python3 <N>/item0_r13_worker_run11_chunk_bytes.py` → `sys.getsizeof(array('q')) = 80 | sys.getsizeof(chunk) = 96 | tracemalloc per chunk incl. the list slot: 104.1 bytes`(Python 3.11.15)。契約 `src/bot/bt/core/contract.py:81-93` の文と同じ値。
5. **E の 2(数の ABC のフック)を測り直した**: `PYTHONPATH=src python3 <N>/item0_r13_worker_run11_probe_numbers_abc.py` → `run -> LatencyModelError order_delay_ns must return an int of ns: order_delay_ns must be an int, got numpy.float32` / `party __subclasscheck__ calls: [('outside', 'float32')]`。同じ根の箇所を全部列べた(`grep -n "numbers\.\|issubclass(" src/bot/bt/core/*.py`): 数の ABC に聞くのは `values.py:381-385`(`_settle` の中。コメントは「送り手の呼び出しの中」)と `values.py:470-471`(`settle` の静的な型の分岐。持ち主の呼び出しの外)の 2 か所。上の試しで外で走ったのは後者。`window.py:298-300` は `list`・`tuple`(ABC でない)、`values.py:178` の `is_a` は核の型に対して使う。契約 `contract.py:137-138` が対象外に書いた物で、答えが無いので直していない。報告の「リードに聞くこと」に 3 回目として書く。
6. **全試験**(`setsid nohup` で切り離して 1 回: `PYTHONPATH=src python -m pytest -p no:cacheprovider`、02:35 UTC 開始)→ `4 failed, 4874 passed, 6 skipped, 1 warning in 845.70s (0:14:05)`。落ちた 4 件はすべて `tests/bt/battery/item_0/`(`test_battery_def_grids.py` の 2 件・`test_battery_item0.py` の 2 件)。同じ時間に場面係が場面集を直しており(`git status --short` → 変わったのは `tests/bt/battery/item_0/` の 30 本(この書き込みの時点、場面係が書き続けている)と追跡されていない `test_battery_r13_claim_mutants.py` だけ。`src/bot/bt/`・`tests/bt/item_0/`・`tests/bt/critic/` は差分なし)、落ちの中身は DEFINITIONS.md の正の定義 C の文の置き換え(§9.2 の 34)の途中の語の判断(`('segment text differs', 62, '`covers` は', '`covers` は場面の宣言で')` など)。実装の側で落ちた試験は 0 件。
7. **場面集(作業の最後に 1 回)**: `PYTHONPATH=src python -m pytest tests/bt/battery/item_0 -p no:cacheprovider` → `7 failed, 162 passed in 57.83s`。落ちたのは上の 4 件と `test_battery_item0.py::test_definitions_in_sync_with_scenes`・`test_battery_r13_claims.py` の 2 件(場面係がこの周に書いている `types_in`・`requests` の記録の試験)で、全部場面係の直しの途中の物。その直後に批評家の i0-r11 の 3 本を回し直した → `45 passed in 0.09s`。作業者は場面集に触れていない。
