# 批評家の記録(項目 0「核」、第 16 周。新しく起こされた批評家)

委任文: `docs/DATA/delegations/20260923_backtest_env_prompt.md`(全文を読んだ。`wc -l` → 170)。**指紋の食い違い**: 起動文は `@cdf623e4fb24` と書くが、作業木とコミット abb256d の版を `sha256sum … | cut -c1-12` で測ると `20487e2d8aec`。`cdf623e4fb24` は 1 つ前の版(コミット dc3f666)。違いは L-445(核の約束の射程)の行と批評家の格付けの文の追加で、起動文の「委任文が優先する」に従い今の版(射程つき)で測った。
合意した完了の形(委任文 §0 の逐語): 「**すべてが調査結果以上の信頼性と再現性に優れたものにすること。**」
手元に置いたもの: 固定した要件 `item_0/REQUIREMENTS.md`(§0 の射程 L-445、§1 の行、§2 の P0-1〜P0-7、§3 の調査結果の行)、場面集 `tests/bt/battery/item_0/`(`DEFINITIONS.md`・`scenes.py`・`run_battery.py`・`adapters/common.py`・`adapters/new_impl.py`・`opponents/CONSIDERED.md`・`survey_results/`)、場面係の `ROOTCAUSE_r16-1.md`、作業者の `round_16/ROOTCAUSE.md` と返り値、リードの答え(`docs/AUDITOR/VERDICTS/2026-09-23_backtest_env_run11_item0.md` の第 15 周末と第 16 周の節)、第 15 周の `CRITIC.md`、この周の表 6 枚(`round_16/表_*.md`、`materials/mapping.tsv`)。
行番号は作業木のもの(HEAD `dd1b337`。`src/` と `tests/bt/battery/` に未コミットの差分は無い)。
`<S>` = `/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt`。この周の試しは `<S>/r16_critic/` に置いた。

射程(要件 §0、L-445): 戦略がプロセス自体を書き換える形(sys.modules・builtins・class の定義・ABC への登録・インタプリタの設定)は [示唆] にする。この周の実装の指摘 3 件は、どれも戦略が**核の公開の class(FrozenDict・FrozenSet・FrozenList)と int・tuple だけ**で作る自分の値で起き、プロセスを書き換えない(射程の中)。

## 前の周の指摘の直り(自分で確かめた)

- **i0-r15-01(止める)**: 直っている。`<S>/r16_critic/item0_r16_critic_probe_to_nanos_grid.py`(種 1616、1,600 組 = 値 400 × 単位 4。型は float・負の float・非正規数・大きな値と inf/nan・十進の文字列・longdouble・numpy float32・int・Fraction。神託は入力が持つ値(`as_integer_ratio`・十進・int)× 倍率が int64 の整数ならその整数、でなければ断る)→ `differing from the oracle: 0`。`to_nanos(1700000000123456.75, 'us')` → `1700000000123456750`、`to_nanos(1700000000.123, 's')` → 断る(`…_recheck_r15_01_07.out`)。第 15 周の試験 `test_i0r15_float_time_rounded_by_shortest_repr.py` も通る(下の全体の実行)。
- **i0-r15-02(直す)**: 直っている(`test_i0r15_unhashable_key_refusal_type.py` 25 件が通る)。**ただし同じ族の別の形が残る**: 下の i0-r16-02(受け付けた鍵を `thaw` が hash の無い型に戻す)。
- **i0-r15-03(直す)**: 指摘した形(各段で候補が 1 つの衝突)は直っている(`test_i0r15_colliding_frozendict_frames.py` が通る)。**同じ族の残り**: 下の i0-r16-01(相手の側に同じ hash の鍵が複数ある段では `_plain_equal` が段ごとに入れ子で呼ばれる)。
- **i0-r15-04(直す)**: 直っている。`<S>/r16_critic/item0_r16_critic_probe_float_field_grid.py`(float の範囲の端: 最大の float・丸めで inf になる境 2^1024 − 2^970 の前後・2^1024・非正規数の端・2^53+1・±1/3・0・±10^400・10^-400 を、Fraction・十進の文字列・Decimal・int・longdouble の全部の形で `as_float(numbers_only=False)` と `take_float` に通し、`float(Fraction)` と照らす)→ `differing from the nearest-float oracle: 0`。第 15 周の試し `item0_r15_critic_probe_float_field_exactness.py` → 2**53+1 は全部の型で `9007199254740992.0`、1/3 は全部 `0.3333333333333333`(`…_recheck_r15_04.out`)。
- **i0-r15-05(止める、場面集)**: 直っている。P0-2 に秒・ミリ・マイクロ秒 × 5 形の値の場面 14 件が足され(`scenes.py` 327-384 行)、観点の要約は要件の文そのものになった。**ただし足した場面のうち 5 件に規則 1 の欠陥がある**: 下の i0-r16-04。
- **i0-r15-06(直す、場面集)**: 直っている。判断の欄は「測っていない(この升目を宣言した場面が無い)」で、理由は `grid_c.why` が宣言と入力から出す(`DEFINITIONS.md` 175・210 行〜)。
- **i0-r15-07(示唆)**: 直っている。`to_nanos(np.longdouble('1700000000.123456789'), 's')` の断りの文は「(it holds 1700000000.12345678894780576229095458984375) has sub-nanosecond digits」。
- 規則 8(批評家の試験自身の誤り): 第 16 周の作業者と場面係は、前の周までの批評家の試験の誤りを申告していない。`git diff --stat 0f2e07d HEAD -- tests/bt/critic/` → 出力なし(誰も変えていない)。取り下げる試験は無い。
- 前の周の [直す]・[示唆] で [止める] に付け直すもの: 無し(i0-r15-02・03・04 は直りを確かめ、残りは下で新しい指摘として格付けした)。

実行した試験:
- `PYTHONPATH=src python -m pytest tests/bt/item_0 tests/bt/critic/item_0 tests/bt/battery/item_0 -p no:cacheprovider -rf`(この周の新しい試験を置く前に集めた)→ `6461 passed, 2 skipped, 3 warnings in 659.73s (0:10:59)`(`<S>/r16_critic/pytest_item0_r16_critic_all0.log`)。前の周までの批評家の試験は全部通る。
- 新しい試験を置いたあと `PYTHONPATH=src python -m pytest tests/bt/critic/item_0 -p no:cacheprovider` → `20 failed, 232 passed in 309.97s (0:05:09)`(`<S>/r16_critic/pytest_item0_r16_critic_criticdir.log`。落ちた 20 件は全部この周の新しい試験 4 本)。
- 場面集: `PYTHONPATH=src python3 tests/bt/battery/item_0/gen_definitions.py --check` → `OK`。`PYTHONPATH=src python3 tests/bt/battery/item_0/mutant.py --check` → `changed scenes: ['p4-received-time']` / `OK`(`<S>/r16_critic/item0_r16_critic_battery_checks.out`)。`python3 scripts/check_bt_considered.py tests/bt/battery/item_0/opponents/CONSIDERED.md` → `OK 誤り 0 件`。

## 指摘

この周の [止める] は 2 件(実装 1・場面集 1)、[直す] は 2 件(実装 2)、[示唆] は 1 件(場面集)。

### i0-r16-01 [直す](相手: 実装、repeat_of: i0-r15-03、場当たり: いいえ)

**`values._plain_equal` が反復なのは、どの鍵にも相手の側に同じ hash の鍵が 1 つしか無いときだけ。相手の側に同じ hash の鍵が複数ある段では、`_match`(values.py 1439 行〜)の `for y in cands` の枝が候補ごとに `_plain_equal(kx, ky)` を入れ子で呼ぶ(1 段に `_match` と `_plain_equal` の 2 枠)。各段で鍵の hash が衝突する鎖では、枠は段数に比例して増える。**

- 鎖: X_0 = 5、Y_0 = 5 + (2^61 − 1)(hash が同じで等しくない)。X_k = FrozenDict({X_{k-1}: 0, Z_k: 0})、Y_k = FrozenDict({Y_{k-1}: 0, Z_k: 0})。Z_k は hash が hash(X_{k-1}) の int。戦略が公開の `FrozenDict(...)` と int だけで作れる(射程の中)。
- `freeze({X_n: 1, Y_n: 2})` に要る枠: 1 段 13・5 段 25・10 段 35・20 段 55・40 段 95・60 段 135・90 段 195。
- 契約 core-17 `process_state`(contract.py 179-187 行)は「FrozenDicts at most 12 at any depth」「at most CALL_FRAMES + one frame per level for every container kind」と書き、「with that much headroom whether a value is taken never depends on the stack depth of the call」と約束する。20 段で 55 > 30 + 20、90 段で 195 > 30 + 90。契約が足りると書く余裕(CALL_FRAMES + 段数)では断られ、それより深い余裕では受け付けられる = 受け付けが呼び出しの積み上がりで決まる。
- 根本原因(私の読み): 第 16 周の作業者の格子 F は、衝突の置き方を「一番下で違う・途中で違う・等しい」で列べ、「相手の側に同じ hash の鍵が複数ある段」を列に入れていない(`round_16/ROOTCAUSE.md` §5 の格子 F)。入れ子の呼び出しを積み上げに載せる直しが、候補が 1 つの枝だけに当たった。i0-r15-03 と同じ「衝突した入れ子の比べの枠数が契約の文と違う」族。
- 格付け: 断りの型は入口の誤り(ValueError)のままで、黙って誤った値は無い。前の周の同じ族(i0-r14-05・i0-r15-03)の格に合わせて [直す]。ただし契約の余裕の約束(積み上がりに依らない)が破れるので、直すときは文を事実に合わせるだけで閉じず、候補が複数の枝も積み上げに載せる(相手の候補ごとの比べを、同じ積み上げの上の「どれか 1 つが等しい」の段として持つ)か、契約の余裕の約束を測った形に書き直すかを作業者が決める。
- 列に入れていない形(試験のファイルに書いた): 1 段に 3 つ以上の衝突する鍵を持つ鎖では、候補ごとの入れ子の比べが全部深く潜るので、枠だけでなく仕事の量も段数の指数になる(下の i0-r16-03 と同じ「仕事の量が渡された物の大きさで決まらない」形)。

根拠:
- `PYTHONPATH=src python3 <S>/r16_critic/item0_r16_critic_probe_plain_equal_chain.py` → `levels   1: … needs 13 frames of headroom` / `levels  20: … needs 55 … CALL_FRAMES + levels = 50` / `levels  40: … needs 95 … = 70` / `levels  90: … needs 195 … = 120`(`…_plain_equal_chain.out`)。
- 試験(残す。作業者が直す): `PYTHONPATH=src python -m pytest tests/bt/critic/item_0/test_i0r16_colliding_frozendict_chain_frames.py -p no:cacheprovider` → `3 failed, 1 passed`(`two colliding 20-level FrozenDict chains need 55 frames of headroom; the contract says CALL_FRAMES + levels = 50 is enough` ほか)。上限は契約の文そのもの(CALL_FRAMES + 段数)。

直すファイル: `src/bot/bt/core/values.py`(`_match`・`_plain_equal`)、`src/bot/bt/core/contract.py`(process_state の文)。

### i0-r16-02 [止める](相手: 実装、repeat_of: i0-r15-02、場当たり: いいえ)

**`freeze` は、核自身が作る入れ物(公開の `FrozenDict`・`FrozenSet`、`FrozenList` を持つ tuple)を辞書の鍵・集合の要素として受け付け、class を保つ。受け手が `thaw`(values.py 1567 行、`OrderRequest.extra_dict()` = api.py 164-167 行)で読むと、その鍵を dict / set / list(「元の形」)に戻してから新しい辞書・集合を作るので、インタプリタが `TypeError: unhashable type` を出す。核が受け付けた値を、核の文書どおりの読み手が読めない。**

- 形 5 つ(FrozenDict を辞書の鍵 / FrozenSet を辞書の鍵 / FrozenList を持つ tuple を辞書の鍵 / FrozenDict を集合の要素 / FrozenSet を frozenset の要素)の全部で、`freeze` は受け付け、`thaw` は TypeError。
- 発注: 戦略が `place_order(... extra=(("k", {FrozenDict({"a": 1}): 3}),))` を出すと受け付けられる。約定の模型(他項目の差し込み口)が自分の `on_order` の中で `order.extra_dict()` を呼ぶと TypeError。約定の模型が捕まえなければ、実行はインタプリタの `TypeError: unhashable type: 'dict'` で止まる(契約のどの誤りの型でもなく、落ち度の無い約定の模型の呼び出しの中で)。
- 契約との食い違い: values.py 92 行「each remembers what it was, so `thaw` gives back a fresh list / dict / set」、`PLAIN_DATA_RULE`「become new immutable containers and are read back as fresh copies」、api.py 165 行「`extra` as a fresh dict, lists / dicts / sets as they were given」。第 16 周の作業者は「受け手の thaw と renew は、核が作った入れ物からしか作らない(鍵は作った時に hash を取れた)ので、変えない」と書いた(`round_16/ROOTCAUSE.md` §4)が、`thaw` は鍵の型を変えるので「作った時に hash を取れた」は `thaw` の後の鍵に当たらない。
- 第 15 周の核(`git archive 0f2e07d`)でも同じ試験が落ちる(前からある振る舞い)。
- 根本原因(私の読み): 「元の形に戻す」(thaw の約束)と「辞書の鍵・集合の要素は hash を持つ」(インタプリタの規則)の食い違いを、受け付けの規則(freeze)も読み手(thaw)も見ていない。i0-r15-02 と同じ「核が辞書・集合を作るとき、鍵・要素が hash を持つかを確かめていない」族で、第 16 周の格子 E は freeze と settle の側だけを列べ、thaw は「作れた物は thaw も通る」として sNaN の位置だけで確かめた。
- 格付け: [止める]。前の周までの [直す](i0-r9-02 (a)・i0-r11-01・i0-r15-02)は、どれも既に断る・止まる道で誤りの型だけが違うものだった。これは正しい入力(要件どおりの平らなデータを出す戦略と、公開の読み手を呼ぶ約定の模型)で実行が止まる振る舞いで、止まる場所も落ち度の無い別の者(約定の模型)の呼び出しの中になる。要件 §1 の「他項目が差し込む口(約定模型…)」を通る注文の値が、口の側から読めない。黙って誤った値は無いが、信頼性を崩すので [止める](迷ったので重い方)。
- 直し方の向き(作業者が決める): 鍵・要素の位置の入れ物は thaw でも hash を持つ形のまま返す(FrozenDict・FrozenSet・FrozenList を鍵に保つ、または鍵の位置では tuple・frozenset に作る)と契約に書くか、そういう鍵を freeze で入口の誤りとして断る。どちらでも「受け付けた値は読み手が読める」を全ての入れ物の型 × 位置の格子で確かめる。

根拠:
- `PYTHONPATH=src python3 <S>/r16_critic/item0_r16_critic_probe_thaw_container_keys.py` → `FrozenDict as a dict key: freeze accepted -> thaw: TypeError: unhashable type: 'dict' | the fill model's order.extra_dict(): ["TypeError: unhashable type: 'dict'"] | run ok` ほか 4 形(`…_thaw_container_keys.out`)。約定の模型が捕まえない形: `<S>/r16_critic/item0_r16_critic_probe_thaw_uncaught.out` → `run raised TypeError unhashable type: 'dict'`。
- 試験(残す): `PYTHONPATH=src python -m pytest tests/bt/critic/item_0/test_i0r16_accepted_keys_read_back.py -p no:cacheprovider` → `10 failed`(`freeze took frozendict-dict-key; thaw raised TypeError: unhashable type: 'dict'` / `the order with frozendict-dict-key was accepted; the fill model's extra_dict() raised TypeError: …`)。第 15 周の核(`PYTHONPATH=<S>/r16_critic/head_0f2e07d/src … -o pythonpath=`)でも同じ 10 件が落ちる。

直すファイル: `src/bot/bt/core/values.py`(`thaw`・`_thaw_open`、または `freeze` の鍵・要素の規則と `PLAIN_DATA_RULE`)、`src/bot/bt/core/api.py`(`extra_dict` の説明)、`src/bot/bt/core/contract.py`(plain_data の文)。

### i0-r16-03 [直す](相手: 実装、repeat_of: null、場当たり: いいえ)

**核の歩き(values.py 977 行 `_walk`。freeze・settle・renew・thaw)は、入れ物を物ごとではなく道ごとに作り直す。戦略が同じ入れ物を 2 か所から指す値(循環ではない共有。`_walk` が断るのは自分の道の上にある入れ物だけ)を渡すと、核はそれを展開した木として作り、仕事の量が渡された物の数の指数になる。**

- t_k = (t_{k-1}, t_{k-1}) を n 回(戦略が持つ tuple は n + 1 個、入れ子は n で MAX_NESTING = 100 の中): `freeze` は n = 18 で 0.65 秒、20 で 2.8 秒、22 で 11.7 秒。
- 発注の道: 入れ子 20(戦略の tuple 21 個)の extra で、`place_order` の実行は 34.4 秒、出口の箱(on_event が返ったあとに核が settle する)の実行は 23.2 秒。入れ子 40 なら実行は終わらない。値は正しく、断りも出ない。核は受け付けも断りもしないまま止まらない。
- 格付け: 黙って誤った値・非決定性は無く、要件の行が求める値も変わらないので [直す]。ただし核の外の誰の落ち度でもない小さな値(21 個の物)で実行が数十秒〜終わらなくなるので、共有を物ごとに 1 回だけ作り直す(`id` で覚える)か、展開した大きさに上限を置いて入口の誤りで断るかを作業者が決め、契約に書く。
- 列に入れていない形: 相手の側に同じ hash の深い候補が 2 つずつある FrozenDict の比べ(i0-r16-01 の枝)も、同じ理由で指数の仕事になる(試していない)。

根拠:
- `PYTHONPATH=src python3 <S>/r16_critic/item0_r16_critic_probe_shared_dag.py` → `nesting 18 (the sender holds 19 tuples): freeze took 0.654 s` / `nesting 20 …: 2.834 s` / `nesting 22 …: 11.652 s`(`…_shared_dag.out`)。`<S>/r16_critic/item0_r16_critic_probe_shared_dag_engine.py` → `nesting 20 via place_order: run ok in 34.42 s` / `nesting 20 via outbox: run ok in 23.17 s`(`…_shared_dag_engine.out`)。
- 試験(残す): `PYTHONPATH=src python -m pytest tests/bt/critic/item_0/test_i0r16_shared_containers_bounded_work.py -p no:cacheprovider` → `2 failed in 40.13s`(入れ子 30 の freeze と settle が、子のプロセスで 20 秒以内に受け付けも断りもしない)。

直すファイル: `src/bot/bt/core/values.py`(`_walk`)、`src/bot/bt/core/contract.py`(plain_data / process_state の文)。

### i0-r16-04 [止める](相手: 場面集、repeat_of: null、場当たり: いいえ)

**第 r16-1 回に足した P0-2 の単位の場面のうち、正解が `NO_INT`(入力が持つ値にナノ秒より細かい端数がある)の 5 場面(`p2-s-text-subns`・`p2-s-float-subns`・`p2-ms-text-subns`・`p2-ms-float-subns`・`p2-us-text-subns`)は、丸めずに断る対象と、時刻の変換を持たない対象を見分けられない。どちらも「対応なし」になり、どの対象も「正解と一致」にならない。**

- 場面の測るもの(`scenes.py` の `_UNIT_MEASURES`)は「ナノ秒の整数にならない値を黙って丸めないか」、検討表の能力(能 3)も「ナノ秒の整数にならない値を黙って丸めない」。その能力を使った結果(断る)が、`adapters/common.py` 147-148 行(入口が無い → `not_supported`)と 153-154 行(入口が断る → `not_supported`)で同じ状態になり、`run_battery.py` の `correctness` は `not_supported` を全部「対応なし」にする。
- この周の表: 対 調査結果の側の表(`round_16/表_vhkby5.md` = `survey_1`)で、行 A(新実装)と行 B(調査結果の側)の 5 場面は両方とも「対応なし」。行 B の最良は、時刻の単位の入口を 1 つも持たない対象から来る(`survey_results/opp_gobacktest.tsv` の 14 場面は全部 `対応なし	not_supported`)。黙って丸めた対象(`opp_freqtrade.tsv`・`opp_barter.tsv` の `*-subns` は「不一致」)より上に寄るので、能力を持たない対象が、能力を持つ新実装と同じセルになる。P0-2 の数えは新実装 13 / 18・調査結果の側 8 / 18 で、この 5 場面は誰にも数えられない。
- 規則 1「能力があるかは、その能力を使ったときに出るはずの結果(正解)が出たかで決める」に反する(能力の欠如と能力の結果が同じ表の値になる)。リードの答え(VERDICTS run11 item0、2026-09-25 08:50 UTC、i0-r15-05 について)は「正解は手計算の int ナノ秒 1 つで、float が正確に持たない値では「断る」も正解に入れる(黙って丸めた値は不一致)」。場面係はこの答えを受け取る前に作り(第 r16-1 回の起動は 08:41:53)、`ROOTCAUSE_r16-1.md` §5.2 の 1 で「断ることを「正解と一致」に数える形にするかはリードが決める」と聞いている。答えは既にあるので、次の直しで当てる。
- 格付け: 場面集の規則 1 に反するので [止める]。場面集の側なので、項目 0 の通過は止めず、並行の直し(L-441)に入る。
- 直し方の向き(場面係が決める): 「入口がある・その入口が断った」と「入口が無い」を採点で分け、前者を NO_INT の場面の正解と一致に数える(十進の文字列でナノ秒より細かい桁の場面も同じ)。入口が断ったかは、今の `unit_time` の結果の文(例外)と別の欄で機械に持たせる(文の読みで採点しない)。

根拠:
- 試験(残す、場面係が直す): `PYTHONPATH=src python -m pytest tests/bt/critic/item_0/test_i0r16_no_int_scene_tells_refusal_from_no_entry.py -p no:cacheprovider` → `5 failed, 1 passed`(`p2-s-text-subns: the target that refuses to round (not_supported: core.to_nanos(値, 's') に '1704067200.1234567891'(単位 s)を渡した -> 例外で止まった TimestampUn…) and a target with no time conversion both grade '対応なし'` ほか)。新実装の adapter の結果と、入口の無い対象(`common.unit_time(sc, [])`)を `run_battery.correctness` で採点して照らす。
- 表: `round_16/表_vhkby5.md` 130-133 行(P0-2 の 18 場面の行 A・行 B を `正しさ:` の欄で読んだ)。`awk -F'\t' '$2 ~ /^p2-(s|ms|us)-/' survey_results/opp_gobacktest.tsv` → 14 行とも `対応なし	not_supported`。

直すファイル: `tests/bt/battery/item_0/run_battery.py`(`_grade_unit_time`・`correctness` の単位の場面の扱い)、`tests/bt/battery/item_0/adapters/common.py`(`unit_time`)、`tests/bt/battery/item_0/scenes.py`(`NO_INT` の正解の文)、`tests/bt/battery/item_0/gen_definitions.py`(`DEFINITIONS.md` はそこから作る)。

### i0-r16-05 [示唆](相手: 場面集、repeat_of: null、場当たり: いいえ)

マイクロ秒の「float が持つ値にナノ秒より細かい端数がある」形は、既知の時刻を 2024-01-01 に固定したので作れない(この大きさの float の刻みは 0.25 µs = 250 ns)と試験で示している(`test_unit_scenes_cover_every_form_of_every_unit`)。刻みがナノ秒より細かくなる小さい時刻(例: 1970 年 1 月の数日のうち、2^40 µs 未満)を既知の時刻に使えば、この形も値の場面にできる。要件は既知の時刻を 1 つに決めていないので、格子の欠けを埋められる。

根拠: `scenes.py` 377-383 行(p2-us-float-held の導き方の最後の文)。

直すファイル: `tests/bt/battery/item_0/scenes.py`。

## 場面集の側で確かめたこと

- 検め: `gen_definitions.py --check` → `OK`、`check_bt_considered.py` → `OK 誤り 0 件`、`mutant.py --check` → `OK`(上)。場面集の指紋 `git ls-files -z tests/bt/battery/item_0 | xargs -0 sha256sum | sha256sum | cut -c1-12` → `384606206fdf`。
- 場面集が要件の観点を覆うか: P0-2 の文が名指す単位(秒・ミリ・ISO)は、第 r16-1 回の単位の場面と ISO の場面で入力に現れる(`DEFINITIONS.md` の「観点の文が名指す値ごとの場面」)。「内部表現に混入しない」は、`p2-one-ns-apart`(float で持てば 2 つが同じ値になる)と `p2-event-time-exact` で振る舞いとして測られていると読んだ。
- adapter の公平さ(この周に変わった所): 単位の場面の共通の手順 `common.unit_time` は、場面の単位と入力の型を読む入口のうち adapter の並びで最初の 1 つだけを呼ぶ。同じ単位・同じ型の入口を 2 つ持つ道具は freqtrade のミリ秒の整数(`dt_from_ts` と `ohlcv_to_dataframe`)だけで、`p2-ms-int` は前者で「正解と一致」なので、最初の 1 つに限ったことで弱めた結果は無い(`opp_freqtrade.tsv`)。新実装は `core.to_nanos` を既定の窓で呼ぶだけで、特別な扱いは見つからなかった(`adapters/new_impl.py` 295-305 行)。aat の ISO の入口を CSV の取引所に替えて「対応なし」→「不一致」になった件(`ROOTCAUSE_r16-1.md` §5.2 の 3 (a))は、道具自身の時刻の入口で、表の最良(ISO の 2 場面は「正解と一致」)は変わらない。quantcore に足した pyarrow は導入前の検査の記録がある(`survey_results/attempts/34.log` 32-49 行: PyPI と GitHub の一致・公開日・sha256・`--no-deps`)。
- 検討表: この周の変更は P0-2 の節の能力の文(能 3)だけで、行は変わらない(`git diff 0f2e07d HEAD -- tests/bt/battery/item_0/opponents/CONSIDERED.md`)。P0-2 の動かせなかった候補 44・58 は「再現できない(危険)」で、2 件とも道具台帳 §3 の 11 件に入る(委任文 §4 の番号の列で確かめた)。
- 再現(`opponents/`): この周に変わったのは単位の場面の口だけ。再現 1 本の全体をこの周に読み直してはいない(限界)。
- 規則 1〜9: 能力の申告で数えている場面は見つからなかった。規則 1 の欠陥は上の i0-r16-04(能力の欠如と能力の結果が同じ値になる)。

## 提出前の吟味(批評家の文)

- 指摘ごとに根拠を自分で再現した: i0-r16-01 は試し(7 段数)と試験。i0-r16-02 は試し(5 形 × thaw と約定の模型)、捕まえない形の試し、試験、第 15 周の核での試験。i0-r16-03 は試し(freeze の 5 段数と、発注・出口の箱の 2 道)と試験。i0-r16-04 は試験、この周の表の P0-2 の行、`survey_results` の行。i0-r16-05 はファイルの行。
- 格付けを基準に照らした: i0-r16-02 は、正しい入力で実行が止まり、落ち度の無い差し込み口の呼び出しの中で止まるので [止める](前の周の [直す] の前例は、既に断る道で型だけが違うものだった点で違う。迷ったので重い方)。i0-r16-04 は規則 1 に反するので [止める]。i0-r16-01 は同じ族の前例(i0-r14-05・i0-r15-03)と同じく断りの型は正しく値も変わらないので [直す]。i0-r16-03 は値・再現を崩さない仕事の量の問題で [直す]。
- 前の周の指摘の直りを自分で確かめた(上の節)。直ったもの(i0-r15-01・04・05・06・07、i0-r15-02・03 の指摘した形)は指摘に挙げていない。
- 相手の付け違い: i0-r16-01〜03 の直すファイルは `src/bot/bt/core/` の下で、相手は実装。i0-r16-04・05 は `tests/bt/battery/item_0/` の下だけで、相手は場面集。i0-r16-04 は核の欠陥ではない(核は正しく断る。採点が断りを能力の欠如と同じに数える)。
- 射程(L-445): 実装の 3 件は、戦略が核の公開の class と int・tuple だけで作る値で起き、sys.modules・builtins・class の定義・ABC・インタプリタの設定に触れない。
- 場当たりの直しは見つからなかった(作業者の直しは読み方の規則の作り替え・hash の検め・反復の比べで、試験だけの特別扱いや閾値の移しは無い。`git diff 0f2e07d HEAD -- src/bot/bt/core | grep -ciE "scene|p2-|battery"` → `0`)。
- 置いた試験: `tests/bt/critic/item_0/test_i0r16_colliding_frozendict_chain_frames.py`(4 件、3 件落ちる)、`test_i0r16_accepted_keys_read_back.py`(10 件、10 件落ちる)、`test_i0r16_shared_containers_bounded_work.py`(2 件、2 件落ちる。1 件 20 秒の子のプロセス)、`test_i0r16_no_int_scene_tells_refusal_from_no_entry.py`(6 件、5 件落ちる)。落ちるのは全部この周の指摘の根拠で、i0-r16-04 の試験は場面係が、ほかは作業者が直す。
