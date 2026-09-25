# 批評家の記録(項目 0「核」、第 13 周。新しく起こされた批評家)

委任文: `docs/DATA/delegations/20260923_backtest_env_prompt.md`(指紋 `cdf623e4fb24`。`sha256sum … | cut -c1-12` で確かめ、全 169 行を読んだ)。
合意した完了の形(委任文 §0 の逐語): 「**すべてが調査結果以上の信頼性と再現性に優れたものにすること。**」
手元に置いたもの: 固定した要件 `item_0/REQUIREMENTS.md`(§1 の行、§2 の P0-1〜P0-7、§3 の調査結果の行)、場面集 `tests/bt/battery/item_0/DEFINITIONS.md` と `scenes.py`、作業者の報告 `round_12/REPORT.md`・`round_13/REPORT.md`、リードの設計 `round_7/LEAD_DESIGN.md`(§8.6 の 29〜31、§9.2 の 32〜36、§9.3 の 37〜41)、第 11 周の `CRITIC.md`。
行番号は作業木のもの(HEAD `40c2525`。場面係の第 r13-1 回の変更の一部は未コミット)。
`<S>` = `/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt`。この周の試しは `<S>/r13_critic/` に置いた。

## 前の周の指摘の直り(自分で確かめた)

- **i0-r11-01(直す、実装)**: 直っている。第 11 周の試しを今の作業木で回し直した(`<S>/r13_critic/item0_r13_critic_recheck_r11_probes.out`)。結果は次のとおり。module_key_nometa: `step/run/result -> EngineFailedError | is EngineFailedError: True`・`Key.__eq__ ran in: []`。outbox_key: `Msg -> run raised OrderApiError | OrderApiError: True`・`[]`。registry_key: `raise: True -> run ok [('mine-1', 'FILLED')]`・`strategy code outside on_event: 0 []`。outbox_metahash: `run raised OrderApiError`・`[]`。試験 `test_i0r11_class_dict_key_runs_foreign_code.py` は通る(下の 55 passed に入っている)。
- **i0-r11-03(直す、実装)**: 直っている。array_export の結果は `hold views: True -> run ok, events 12 digest 06cfb720ce34` で、view を持たないときと同じ値だった。試験 `test_i0r11_pinned_dropped_facts_fail_the_core_step.py` も通る。
- **i0-r11-02(止める、場面集)**: 直っている。`PYTHONPATH=src python -m pytest tests/bt/critic/item_0/test_i0r11_covers_within_scene_input.py tests/bt/critic/item_0/test_i0r11_class_dict_key_runs_foreign_code.py tests/bt/critic/item_0/test_i0r11_pinned_dropped_facts_fail_the_core_step.py tests/bt/critic/item_0/test_i0r11_history_limit_exact_refusal.py -p no:cacheprovider` の結果は `55 passed in 0.77s` だった。`covers_of` は `input_types` から出す(`scenes.py` 626-654 行)。`gen_definitions.py --check` の結果は `OK`。第 11 周に「人の読みで残る点」とした p6-place-then-cancel は、宣言を持たなくなった(`scenes.py` 603 行)。
- 批評家と場面集の試験の全部: `PYTHONPATH=src python -m pytest tests/bt/critic/item_0 tests/bt/battery/item_0 -p no:cacheprovider` の結果は `310 passed in 256.80s`(ログは `<S>/r13_critic/pytest_item0_r13_critic_critic_battery.log`)。この実行は、下の新しい試験を置く前に集めたものである。
- 作業者の試験: `PYTHONPATH=src python -m pytest tests/bt/item_0 -p no:cacheprovider` の末尾の行は `1690 passed, 2 skipped in 142.55s`(`<S>/r13_critic/pytest_item0_r13_critic_worker_tests.log`)。
- 規則 8(批評家の試験自身の誤り): 作業者は第 12 周・第 13 周とも「当たる試験は無い」と報告している。確かめたところ、前の周までの批評家の試験で落ちるものは無かったので、取り下げる試験は無い。
- `python3 scripts/check_bt_considered.py tests/bt/battery/item_0/opponents/CONSIDERED.md` の結果は `OK 誤り 0 件`。第 r13-1 回に候補 35 を「走った」に移した件も確かめた。adapter `opponents/thirupathikannan_execsim_adapter.py` は、全 32 場面で道具を実際に呼んでいる(P0-7 は差し込みの物をキーワード引数で渡し、ほかは `execute_order` を平らな価格の道で呼ぶ)。その結果は全部「対応なし・2 回の実行で同じ」だった(`survey_results/opp_thirupathikannan_execsim.tsv` の 5 列目を `sort | uniq -c` → `32 対応なし`)。道具は発注の計画を価格の道に当てるだけの模擬器である。事象・戦略・注文を受ける名前が無いことは、adapter の注と一次資料の行に合っている。弱めた呼び方は見当たらなかった。上位互換のスキップの「含む」の根拠を 2 件、結果と照らした。98 mihircoding の p7-latency-model-swap と 65 aat の p7-fill-model-swap は、どちらも `正解と一致・2 回の実行で同じ` だった。
- 新実装の adapter は、P0-7 の約定を戦略に届いた通知から読む(`adapters/new_impl.py` 160 行・545 行)。宣言した道(戦略の呼び出しに届く物)と合っている。

## 指摘

この周の [止める] は 1 件(i0-r13-01、相手: 実装)。

### i0-r13-01 [止める](相手: 実装、repeat_of: i0-r11-01、場当たり: いいえ)

**核は「静的な(C の)数の class が何の数か」を、プロセス全体で共有された numbers の ABC に聞いて決める(`values.py` 470-476 行 `_settle`、381-386 行 `_plain_scalar`)。その ABC の登録は、戦略が自分の呼び出しの中で公開の API(`numbers.Integral.register`)で変えられる状態である。変えると、ほかの者(費用の模型・約定の模型・遅延の模型)の答えを、核が黙って誤った値にする。その変化はプロセスの残りの全ての実行に残る。**

- (a) **黙って誤った値**: 費用の模型が `numpy.float32(0.75)` を返し、戦略が `on_event` の中で `numbers.Integral.register(numpy.float32)` を呼ぶ(フックも class の定義も無い、ただの登録)。すると、口座に渡る手数料が 0.75 でなく **0.0** になる(`int(0.75)`)。断りは出ない。約定の模型が自分の呼び出しの中で作った報告の価格 `numpy.float32(100.5)` も、戦略に届くときには **100.0** になる(`_plain_scalar`)。遅延の模型の `numpy.float32(1.5)` は、登録の前は `LatencyModelError` で断られる。登録の後は 1 ns として黙って受け取られる。
- (b) **再現性**: 同じプロセスで同じ入力を 2 回走らせても、間に別の実行の戦略が登録すると結果が変わる(手数料 0.75 → 0.0)。ABC は正の答えを覚えておくので、元には戻らない。P0-5 の「同じ入力を 2 回実行して同じ順序・同じ結果」と、契約 scope の「the strategy changing ANY state object it can reach ... reaches only what the strategy itself reads」に反する。
- (c) **持ち主の呼び出しの外で走る外のコード**(i0-r11-01 と同じ機構): `numbers.Integral` の子で、メタクラスの `__subclasscheck__` が True を返す class を戦略が作ったとする。すると、核が費用の模型の答えを取るとき(戦略の呼び出しの外)に、そのフックが走って答えを決める(手数料 0.0)。どの ABC でも 1 回の登録があれば、ABC 全体の無効化の数が進んで、前の否定の覚えが消える。そのあとは、先の実行で否定が覚えられていても、フックがまた聞かれる。ふつうの `collections.abc.Sized.register(cls)` でも起きる。
- (d) 同じ根の 2 つ目の形: `values.py` 322-325 行 `_numpy_bool` は、settle のたびに `sys.modules['numpy'].bool_` を読む。戦略がこの属性を自分の class にすると、出口の箱の時計の値を取るときに、その class の `__bool__` が `on_event` の外で走る。断りの型も `OrderApiError` から `TimestampUnitError` に変わる。契約の「a refusal is always the entry's own error」と食い違う。

契約の「Not covered」にある「classes derived from or registered with the numbers ABCs that carry a __subclasshook__ or a metaclass hook ... (defining classes changes the program)」は、(a)(b) の**フックの無い登録**を覆っていない。理由の「class を定義することはプログラムを変えること」も、第 11 周・第 12 周の格子と合わない。そこでは戦略が class を定義した場合(`__eq__` を持つ鍵、`type()` で作った class)を契約の範囲に入れて直している。ABC の登録は核のコードではなく、実行中に変わる状態である。第 13 周の作業者は (c) を自分で見つけ、「リードに聞くこと」に上げた。リードの答え(§9.3 の 41「作業者は待つ」)より後の実測なので、この周には答えが無い。格付けは委任文 §3「格付けの基準」の「黙って誤った値を返すなど、信頼性か再現性を崩すもの」に当たるので [止める] とした。族は i0-r9-02 → i0-r11-01(核が、外の者が変えられる物に頼って判断し、外のコードを持ち主の呼び出しの外で走らせる)で、repeat_of は i0-r11-01 とした。場当たりの直しを見つけたのではないので patchwork は「いいえ」。ただし、この穴を契約の対象外の文で閉じるのは「機能を外して要件から逃げる」に当たる。直すときは、数の種類を ABC の登録に聞かずに決める(静的な型の MRO を、核が持つ型の表と同一性で比べる)ことと、`sys.modules` をたどらないことの両方が要る。

根拠:
- `PYTHONPATH=src python3 <S>/r13_critic/item0_r13_critic_probe_numbers_registry.py {none,register,hook}`(1 つずつ新しいプロセスで)→ `none -> run ok | fee seen by the account: [0.75] | hook calls: 0` / `register -> run ok | fee seen by the account: [0.0] | hook calls: 0` / `hook -> run ok | fee seen by the account: [0.0] | hook calls: 1`(`…_numbers_registry.out`)。
- `<S>/r13_critic/item0_r13_critic_probe_numbers_rerun.py` → `run A (clean strategy), fresh process : ('ok', [0.75], [0])` / `delay 1.5 as float32, fresh : ('raised LatencyModelError', …)` / `run B (its strategy registers np.float32) : ('ok', [0.0], [0])` / `run A again, same input, same process : ('ok', [0.0], [0])` / `delay 1.5 as float32, after the registration : ('ok', [0.0], [1])`(`…_numbers_rerun.out`)。
- `<S>/r13_critic/item0_r13_critic_probe_numbers_fill_price.py {none,register}` → `none -> fill price the strategy received: [100.5]` / `register -> fill price the strategy received: [100.0]`(`…_numbers_fill_price.out`)。
- `<S>/r13_critic/item0_r13_critic_probe_numpy_bool_attr.py` → `patch False -> run raised OrderApiError …` / `patch True -> run raised TimestampUnitError timestamp must be an int of nanoseconds, got bool | ['Foo.__bool__ ran OUTSIDE on_event']`(`…_numpy_bool_attr.out`)。
- 試験(残す。作業者が直す): `tests/bt/critic/item_0/test_i0r13_process_global_state_decides_core_values.py`。ABC の登録は取り消せないので、全ての場合を新しいプロセスで走らせる。`PYTHONPATH=src python -m pytest tests/bt/critic/item_0/test_i0r13_process_global_state_decides_core_values.py -p no:cacheprovider` の結果は、3 回とも `7 failed`(`<S>/r13_critic/pytest_item0_r13_critic_new_test.log`)。落ち方は `('ok', [0.0]) []`・`('ok', [0.0]) ['hook']`・`False ('ok', [0.75]) ('ok', [0.0])`・`[('OrderApiError', []), ('TimestampUnitError', ['Foo.__bool__'])]`。

直すファイル: `src/bot/bt/core/values.py`(`_settle`・`_plain_scalar`・`_numpy_bool`)、`src/bot/bt/core/contract.py`(scope の対象外の文)。

## 提出前の吟味(批評家の文)

- 指摘の根拠は全部自分で再現した。試しは新しいプロセスで回し、試験は 3 回回した(毎回同じ `7 failed`)。フックの形は、最初は class が回収されるかどうかで結果が揺れた。そこで試験の中で戦略が class を持つようにし、実際に無効化の数が進む登録(まだ Sized でない class)に直した。直した後は毎回同じ結果になった。
- 格付け: (a) は黙って誤った値、(b) は再現性の崩れで、どちらも [止める] の基準に当たる。前の周の i0-r11-01・i0-r11-03 は、FAILED で止まる経路なので [直す] だった。この指摘はそれと違い、実行が通ったまま値が変わる。
- 前の周の指摘は、3 件とも直っていることを試しと試験で確かめた。直ったものはこの記録の指摘には挙げていない。前の周の [直す]・[示唆] で [止める] に付け直すものは無かった。
- 相手の付け違い: 直す場所は核の `values.py` と `contract.py` だけで、場面集には無い。よって相手は「実装」とした。fix_files は src/bot/bt/core/ の下だけである。
- この周に場面集の側で新しい [止める] は見つからなかった。確かめたのは次のとおり。升目の数(`covers_of`)と `gen_definitions.py --check`。検討表の機械の検め。候補 35 の adapter と結果。P0-7 の宣言した道と新実装の adapter の読み方。
