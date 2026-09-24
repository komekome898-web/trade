# 9 回目の起動(run `wf_a29e5ac0-1a4`、指紋 d3eae0d221c9、2026-09-24 19:48 UTC 起動 → 22:45 UTC に台本が戻し)の項目 0 の記録

Workflow の記録(journal)から `scripts/export_workflow_judges.py` で逐語に書き出した物の写しと、リードの処置。逐語の原本: `docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/round_11/`・`round_12/`・`battery/AUDIT.md`。

## 第 11 周

### 結果

| 組 | 判定 |
|---|---|
| 対 当方の現状 / 対 調査結果の側 | 3/3・3/3 が新実装(新実装 32/32、当方の現状 8/32、調査結果の最良 31/32) |
| 場面集の直し r11-1 の監査 | [止める] 0 |
| 批評家 | [止める] 1(場面集 i0-r11-02)、[直す] 2(実装 i0-r11-01・03)、[示唆] 1 → 未達、第 12 周へ |

### 場面の直し r11-1 と監査役(場面)r11-1 の出力(逐語)

## 場面の直し:0#r11-1(agent afcb010dd4b6ec9b2)

- 根本原因の記録: /home/user/trade/tests/bt/battery/item_0/ROOTCAUSE_r11-1.md(i0-r9-03 の根本原因: 根 1 = 第 r8-1 回の正の定義 C が升目の判断の値に手続きの状態を入れていた(3 つ目の値「測り方の文の語で決まらない…リードに上げる」)。根 2 = grid_c.py の rule() が要件の文の読みを if の枝で持ち、枝が決めない升目を全部その値に落としていた。見つけられなかった理由 = 試験が 3 つ目の値を許し、入力を実装の場合分けから作っていた。変えた作り = 判断を covers だけの関数にして 2 値にし、正の定義 C の該当の文を §8.2 の 1 の文に置き換えた。敵対者の試験を先に書いた(test_battery_item0.py:1421 は全 408 升目 × 覆う場面の 4 つの状態、1450 は全升目 × 判断の候補 7 つ)。この 2 件が直す前の grid_c.py で落ちる出力は <S>item0_r11-1_scenekeeper_grid_tests_first.txt。§7 = 提出前の吟味(正の定義 E の 2 列の形)。§8 = リードに聞くこと: (1) 候補 35(独立の項目、L-438 (3))、(2) 型を対象に任せる場面の covers の宣言の仕方と p6-place-then-cancel の covers、(3) 注文の状態の意味の「未決」、(4) ROOTCAUSE_r10-1.md の本文を版固定の参照にしたこと、(5) ROOTCAUSE_r8-1.md §9 の 2・3・8 の扱い。試験: 場面集は「78 passed in 38.48s」(直す前は 3 failed, 72 passed)、批評家は「85 passed in 206.70s」、全試験は「4597 passed, 6 skipped, 1 warning in 863.98s」。全試験のログは <S>pytest_item0_r11-1_scenekeeper.log。全試験は ROOTCAUSE の文を直す前に走らせ、文を直したあとには場面集の試験を回した)
- 検討表の道具の出力: OK 誤り 0 件
- 動かせた: ['opp_3yit_lob', 'opp_aat', 'opp_akurkar07_orderbook', 'opp_backtesting', 'opp_backtrader@preload=false', 'opp_backtrader@preload=true', 'opp_barter', 'opp_basana', 'opp_daniyalmlk_slippage', 'opp_fast_trade', 'opp_finmarketpy', 'opp_freqtrade', 'opp_gobacktest', 'opp_hftbacktest', 'opp_homerun', 'opp_isaaccheng_obsim', 'opp_jxm35_lob', 'opp_lib_pybroker', 'opp_luczinsritter', 'opp_mihircoding_lob', 'opp_nickgardi_orderbooksim', 'opp_pineforge@tf=1D', 'opp_pineforge@tf=1S', 'opp_predictivedev_tradesim', 'opp_pyalgotrade', 'opp_pybotters', 'opp_pysystemtrade', 'opp_pytrendfollow', 'opp_qf_lib', 'opp_qstrader', 'opp_quantcore', 'opp_quanttrader', 'opp_rqalpha', 'opp_sarthak_execsim@md_latency=0', 'opp_sarthak_execsim@md_latency=default', 'opp_sigc', 'opp_vnpy', 'opp_ziplime@label=close', 'opp_ziplime@label=start', 'opp_zipline_reloaded', 'repro_lean52(再現。13 の設定つき対象: daily/hour/minute/second/tick と tick+各解像度の bar・trade)', '(この回は survey_results を走らせ直していない。場面の入力・runner・adapter は変えていないが、場面集の指紋は DEFINITIONS.md などが変わったので前の周と違う。資料係は L-435 どおり全部を走らせ直す)']
- 動かせなかった: ['8 OpenTrader(持たないと確認した)', '11 OctoBot(スキップ: 上位互換)', '13 DeviaVir/zenbot(スキップ: 上位互換)', '15 Mendl-Labs/BacktestingCore(持たないと確認した)', '35 Optimal-Execution-And-Market-Impact-Simulator(持たないと確認した。権限の分類器の拒否は、リードの答え §7 の 1 のとおり場面係は試していない。ROOTCAUSE_r11-1.md §8 の 1 に独立の項目として書いた)', '38 microsoft/MarS(スキップ: 上位互換)', '40 OpenMarket(再現できない)', '41 prediction-market-backtesting(再現できない: 危険)', '44 lo2cin4(再現できない: 危険)', '49 GFT Backtest Software(再現できない)', '52 QuantConnect LEAN(再現した = repro_lean52)', '57 WonderTrader(スキップ: 上位互換)', '58 nautilus_trader(再現できない: 危険)', '63 trade-frame(スキップ: 上位互換)', '120 wbt(再現できない: 危険)', '123 carlos8f/zenbot(スキップ: 上位互換)', '集計: 観点ごとの延べで 動かせた 59 / 検討表の行 31(34%)/ 再現した 1 / 持たないと確認した 4 / スキップ 15 / 再現できない 11(opponents/CONSIDERED.md の集計の区画。この回は変えていない)']

## 監査役(場面):0#r11-1(agent ae7d31b1d437acf90)

- [聞く] ROOTCAUSE_r11-1.md §8 の 2(場面係が自分で挙げた未解決の問い)は、升目の判断が `covers` だけから機械で決まる今の設計では、`covers` が「その場面を走らせうる市場の事象の型の全部」を宣言できる(`scenes.py` の `COVERS` の注)ため、実際に 1 回の実行で試された型より広い範囲を『場面にした』と表に出せることを認めている。DEFINITIONS.md の P0-1 の表では、`p1-merge-by-time` ほか 3 場面が事象の軸 6 種(約定・板の写真・板の差分・足・資金調達・清算)すべてで『場面にした』と出ているが、この一致は場面の測る物と `covers` が『合うか』を批評家が読んで確かめる(機械では確かめない)ことに依存している。この table は審査員・オーナーへの通過報告の『測っていない範囲の記録』の裏の『測った範囲』の主張でもある。この乖離を許容する設計(§8.2 の 1)自体はリードが決めたことだが、`covers` の宣言を『1 回の実行が必ず入れる型』に狭めるかは場面係がリードに上げたまま未解決であり、場面が新実装に有利な向き(測った範囲を実際より広く見せる)に効きうるかの判断が付いていない。この点はリードが答えるまで、升目の表の『場面にした』の意味を額面どおり『その升目が実際に 1 回の実行で検証された』と読んでよいかが確定していない(P3/P9 に近い、測定の網羅性の主張と実装の一致の問い)。
- [聞く] 候補 35(権限の分類器の拒否)は第 8〜11 周にわたり『リードが run の止まった時機に試す』として据え置かれたままで、リードが実際に試した記録(コマンドと出力)がまだ無い。項目 0 の通過報告に、この 1 件を『比べていない候補』として候補名つきで明記する運びになっているか(委任文 §3「動かせなかった候補の数と割合…再現もできなかった候補があるとき…比べていない…候補名を付けて報告する」)を確認したか。


### 批評家 `批評:0#11` の出力(逐語)

(出所の注記、監査 52 回目の 52-5: 下は批評家自身が書いたファイル `round_11/CRITIC.md` の写し。台本に返した構造化の返り値(journal)は同じ批評家の文で、接続の語が 2 か所違う(「走る。断りの型も」↔「走り、断りの型が」/「の 18 升目は」↔「のうち 18 升目は」)。10 回目の引数の last_findings は返り値の側の逐語。)

# 批評家の記録(項目 0「核」、第 11 周。新しく起こされた批評家)

委任文: `docs/DATA/delegations/20260923_backtest_env_prompt.md`(指紋 `d3eae0d221c9`。`sha256sum … | cut -c1-12` で確かめ、全 164 行を読んだ)。
合意した完了の形(委任文 §0 の逐語): 「**すべてが調査結果以上の信頼性と再現性に優れたものにすること。**」
手元に置いたもの: 固定した要件 `item_0/REQUIREMENTS.md`(§1 の行・§2 の P0-1〜P0-7・§3 の調査結果の行)、場面集 `tests/bt/battery/item_0/DEFINITIONS.md`、作業者の根本原因 `round_11/ROOTCAUSE.md` と報告 `round_11/REPORT.md`、リードの設計 `round_7/LEAD_DESIGN.md`(§3.4・§7.4・§7.5・§8.1〜§8.5)、第 9 周の `CRITIC.md`。
行番号は作業木(HEAD `b7cbd63`。作業者と場面係の第 11 周の変更はリードのチェックポイントに入っている)のもの。
`<S>` = `/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt`、この周の試しは `<S>/r11_critic/`。

## 指摘

この周の [止める] は 1 件(i0-r11-02、相手: 場面集)。実装の側は [直す] 2 件(どちらも第 9 周の i0-r9-02 と同じ族)。

### i0-r11-01 [直す](相手: 実装、repeat_of: i0-r9-02)

**第 11 周の直し「外のコードが作った物を、核が持ち主の呼び出しの外で扱うときは、その class を通さない」は、dict の検索が鍵の `__eq__` を走らせることを見落としており、外のコードが持ち主の呼び出しの外で走る。**断りの型も契約と違う。

作業者の規則は「`type` 自身の記述子と基の型の C の関数は外のコードを走らせない」を前提にしている(`values.py` 194-203 行 `class_parts`: 「no code of the class, its metaclass or what its body set `__module__` to runs」、契約 `lifecycle`「no code of the failure ... runs and the refusal is always EngineFailedError (round 11)」、`type_decisions`「no code of the class or its metaclass runs ... a refusal is the error type of the place it enters」、`channel_payloads.ownership`「The core touches it only through base-type C functions ... never through the objects' own classes」)。前提が崩れる形が 2 つある。どちらも**メタクラスを使わない**(契約 `scope` が除外する「メタクラスが属性の読みで走るもの」には当たらない)。

- (a) **class の辞書の鍵**: `type` の `__module__` の記述子(`values.py` 181 行 `_TYPE_MODULE`)は、class 自身の辞書で `'__module__'` を検索する。`type()` そのもので、先頭の鍵が `'__module__'` と同じ hash を持つ送り手の物である辞書から作った class では、その検索が鍵の `__eq__` を呼ぶ。核が外の物の型を名指す所(`type_name` / `exception_text` の全部の読み手)の全部で、送り手のコードが持ち主の呼び出しの外で走り、そこで投げた例外が断りに代わる。
  - 戦略の例外(`engine.py` 884-900 行 `_usable` → `exception_text`)と、その例外の引数(`values.py` 217 行 `_arg_text` → `type_name`): FAILED の後の `step()`・`run()`・`result()` が `EngineFailedError` でなく送り手の `RuntimeError` になる。
  - 出口の箱の知らせと、箱の中の注文の物(`engine.py` 1109-1117 行 `_take_message`、462-472 行 `_settled_request`): `on_event` が返った後に戦略のコードが走り、断りが `OrderApiError` でなく `RuntimeError`。
  - 約定の模型の報告(1260-1270 行 `_take_reports`)・口座の強制注文(1185-1189 行 `_force`)・入力の流れの事象(634-652 行 `_pull`): 断りが `VenueProtocolError` / `AccountSocketError` / `SourceEventTypeError` でなく `RuntimeError`。
- (b) **戦略の側の注文の台帳の鍵**: 核は `on_event` が返った後に、戦略の台帳(戦略が届く普通の dict)へ新しい見え方を `dict.__setitem__` で書く(`engine.py` 1087-1090 行 `_show`。知らせの受け取り・発注・取消のたび)。戦略が次の注文の id と同じ hash の鍵を台帳に入れておくと、その書き込みが鍵の `__eq__` を `on_event` の外で走らせる(投げなければ 3 回走って実行は通る。投げれば実行は `RuntimeError` で FAILED)。

どの形でも、走る所は同じ時刻の配達の途中か失敗した後で、核の判断・送る物・結果・配達の要約は変わらない(黙って誤った値は無い。先の事象も見えない)。第 9 周の i0-r9-02 (a)(戦略のコードが `on_event` の外で走り、実行が `RuntimeError` で FAILED になる)と同じ結果の類で、リードの答え §7.5 の 22 は (a) を「FAILED で止まる経路」として [直す] のまま置いた。よって [直す]。族は i0-r9-02(核が、外のコードが変えられる物・作った物に後で触れ、そのコードを持ち主の呼び出しの外で走らせる)で、作業者自身が `round_11/ROOTCAUSE.md` §B-2 でこの周の直しを i0-r9-02 と同じ根の箇所と書いている。

加えて(読みが分かれるので書く): 箱の時計の知らせの値の class にメタクラスの `__hash__` を持たせると、`_settle` の `BUILD.get(t)`(`values.py` 340 行)がそれを `on_event` の外で走らせる(断りは `OrderApiError` のまま)。契約の除外は「メタクラスが属性の読みで走るもの」で、hash はそれに入るかが読み分かれる。

根拠:
- `PYTHONPATH=src python3 <S>/r11_critic/item0_r11_critic_probe_module_key_nometa.py` → `metaclass of Boom: <class 'type'>` / `step -> RuntimeError | is EngineFailedError: False` / `run -> RuntimeError | …: False` / `result -> RuntimeError | …: False` / `Key.__eq__ ran in: ['engine.step', 'engine.run', 'engine.result']`(`…_nometa.out`)。
- `<S>/r11_critic/item0_r11_critic_probe_outbox_key.py` → `plain object() -> run raised OrderApiError | OrderApiError: True` / `Msg -> run raised RuntimeError | OrderApiError: False | strategy code ran outside on_event` / `['Key.__eq__ OUTSIDE on_event']`(`…_outbox_key.out`)。
- `<S>/r11_critic/item0_r11_critic_probe_sockets_key.out` → `fill_model -> RuntimeError | sender code outside its call: 1` / `account -> RuntimeError | … 1` / `stream -> RuntimeError | … 1`。
- `<S>/r11_critic/item0_r11_critic_probe_registry_key.py` → `raise: False -> run ok [('mine-1', 'FILLED')]` / `strategy code outside on_event: 3 ['mine-1', 'mine-1', 'mine-1']` / `raise: True -> run raised RuntimeError | CoreError: False`(`…_registry_key.out`)。
- メタクラスの hash: `<S>/r11_critic/item0_r11_critic_probe_outbox_metahash.py` → `run raised OrderApiError | OrderApiError: True` / `['M.__hash__ OUTSIDE on_event']`。
- 試験(残す。作業者が直す): `tests/bt/critic/item_0/test_i0r11_class_dict_key_runs_foreign_code.py` → `PYTHONPATH=src python -m pytest tests/bt/critic/item_0/test_i0r11_class_dict_key_runs_foreign_code.py -p no:cacheprovider` → `12 failed`(格子: 戦略の例外 × {型, 引数} × {step, run, result} = 6、箱 × {知らせ, 注文の物} = 2、{約定の模型, 口座, 入力の流れ} = 3、台帳 = 1。落ち方は 12 件とも `the …'s code ran outside …` の assert で、送り手の鍵の `__eq__` の記録が残る)。

### i0-r11-02 [止める](相手: 場面集、repeat_of: null)

**升目の表の「場面にした」の 18 升目は、それを `covers` に持つ場面のどれも、その事象の型を入力に持たない。**`covers` は手で書いた宣言で(`scenes.py` 554-605 行、`COVERS` は 565 行から。注に「A scene whose events the scene leaves to the target … covers each market type it may be run with」)、第 r11-1 回から升目の判断は `covers` だけで決まる(`grid_c.py` 107-111 行 `verdict`)。リードの設計 §8.2 の 1 は「`covers` は場面の宣言で、批評家が『場面の測る物と covers が合わない』と見れば [直す]/[止める] にする」とし、§8.5 の 24(20:58 UTC)は「`covers` の事象の軸は、その場面の入力(scenes.py の入力の事象と `type_plan` で作る事象)に実際に含まれる型から機械で出す」と決めた。今の `covers` はこれと合わない:

- 型を対象が 1 つ選ぶ場面(p1-one-call-per-event・p2-event-time-exact・p2-one-ns-apart・p5-same-stream-order)は、1 回の実行で 1 つの型しか走らないのに市場の事象の 6 型を全部宣言する。新実装の adapter は p2 の 2 場面を約定だけで走らせる(`adapters/new_impl.py` 293-311 行)。
- p2-iso-utc・p2-iso-offset は事象を 1 件も持たない(入力は ISO の文字列だけ)のに、6 型 × 「戦略が対象の公開の手段で読む物」× ISO 文字列 を宣言する。
- `type_plan` の 4 場面は、6 型を全部持つ対象でも 2〜4 型しか作らない(p1-merge-by-time = 約定・板の写真・板の差分、p1-typed-events = 約定・板の写真、p5-* = 約定・板の写真・板の差分・足)のに 6 型を宣言する。資金調達・清算を入れる場面が P0-1・P0-5 に無い。
- P0-4 の 3 場面は入力が足だけ・約定だけなのに、約定と足の両方を宣言する。

結果、市場の事象の軸で「場面にした」の 35 升目のうち 18 升目(P0-2 は 12 升目の全部、P0-1 2、P0-4 2、P0-5 2)が、どの場面の入力にもその型の事象が無い。この表は §8.2 の 2 の文どおり「測っていない範囲の記録」で、項目 0 の通過の報告でオーナーに渡る。測っていない升目を「場面にした」と書くのは、測っていない範囲を実際より狭く見せる向き(新実装の通過の報告に有利な向き。第 r11-1 回の監査役の [聞く] br11-1-1 が挙げた向き)で、場面集の出力が黙って誤った値を出している。

格付け: 場面の入力・正解・比較の表のセルは変わらないので [直す] とも読める(第 9 周の i0-r9-03 は DEFINITIONS の語の未適用を [直す] にした)。一方、これは語ではなく「何を測ったか」の事実の誤りで、表の唯一の目的(測っていない範囲の記録)を損ない、18 升目は機械で数えられる。委任文 §3「迷ったら重い方」により [止める] とした。族は i0-r9-03(升目の判断に測定でない値「未決」が入っていた)と同じ表だが、機構は違う(判断の値の種類ではなく、宣言が測った物より広い)ので repeat_of は null。

根拠:
- `PYTHONPATH=src:. python3 -` で `grid_c.table(scenes.SCENES)` の「場面にした」升目ごとに、覆う場面の入力の事象の型(`events`・`streams` の `kind`)を突き合わせた → `場面にした cells (market event axis): 35 of which no covering scene's input holds the type: 19`。うち 1 件(P0-3 の 時計)は時計の事象が戦略の頼みで作られるので誤りではなく、残る 18 件(`Counter({'P0-2': 12, 'P0-1': 2, 'P0-4': 2, 'P0-5': 2})`)。
- `type_plan` の場面を 6 型を全部持つ対象で作った入力: `scenes.for_target_types(s, scenes.TYPE_ORDER)` → `p1-merge-by-time ['book_delta', 'book_snapshot', 'trade']` / `p1-typed-events ['book_snapshot', 'trade']` / `p5-same-time-twice ['bar', 'book_delta', 'book_snapshot', 'trade']` / `p5-hand-over-order` 同じ。
- 試験(残す。場面係が直す): `tests/bt/critic/item_0/test_i0r11_covers_within_scene_input.py`(場面ごとに、`covers` の市場の事象の型 ⊆ 入力の事象の型。`type_plan` の場面は 6 型を持つ対象で作る)→ `13 failed, 19 passed`(落ちる 13 場面: p1-merge-by-time・p1-one-call-per-event・p1-typed-events・p2-iso-utc・p2-iso-offset・p2-event-time-exact・p2-one-ns-apart・p4-visible-at-step・p4-received-time・p4-future-read-attempt・p5-same-time-twice・p5-hand-over-order・p5-same-stream-order)。
- 人の読みで残る 1 点(機械では測っていない): p6-place-then-cancel の `covers` = (注文の受付の通知, 戦略が対象の公開の手段で読む物)。場面が読むのは未決の注文の数で、受付の通知そのものは読まない。場面係が ROOTCAUSE_r11-1.md §8 の 2 でリードに上げている。

### i0-r11-03 [直す](相手: 実装、repeat_of: i0-r9-02)

**戦略が、届く物を何も書き換えずに読むための view を持つだけで、核の手順が `BufferError` で落ちる。**落とした事象の事実の `array('q')`(`history.py` 132 行からの `HistoryLists` の `dropped_seqs`・`dropped_recvs`)は戦略の側の物で、文脈の `dropped_of` の既定値(`engine.py` 1060-1063 行)から届く。核は落とすたびにそれを `array.array.extend` で伸ばす(`history.py` 176-177 行)。戦略がその array の `memoryview` を持っている間は array の大きさを変えられないので、次に落とすときに核の `extend` が `BufferError: cannot resize an array that is exporting buffers` を投げ、`on_event` の外(核の配達の手順の中)で実行が FAILED になる。契約 `scope`「So is the strategy changing ANY state object it can reach, by any means … such a change reaches only what the strategy itself reads」と、engine.py の説明「nothing it changes there, by any means, reaches the core, the venue, another receiver or the caller's result」に反する(ここでは何も変えていないのに、呼び手の結果が失敗に変わる)。作業者の変更の格子(`test_bt0_r11_foreign_objects.py` 格子 2)は、型が持つ変更の方法(dir の差)を列べるので、buffer の書き出しで大きさを固める道は列の外。

失敗で止まる経路で、黙って誤った値は無いので、i0-r9-02 (a) と同じく [直す]。族は i0-r9-02(核が、戦略が届いて API を通さずに作用できる物に後で触れる)。

根拠:
- `PYTHONPATH=src python3 <S>/r11_critic/item0_r11_critic_probe_array_export.py` → `hold views: False -> run ok, events 12 digest 06cfb720ce34` / `hold views: True -> run raised BufferError | CoreError: False | cannot resize an array that is exporting buffers | views held: 24`(`…_array_export.out`)。
- 試験(残す。作業者が直す): `tests/bt/critic/item_0/test_i0r11_pinned_dropped_facts_fail_the_core_step.py` → `1 failed`(`E BufferError: cannot resize an array that is exporting buffers`)。

### i0-r11-04 [示唆](相手: 場面集、repeat_of: null)

検討表の 13 DeviaVir/zenbot(P0-6)の行は、能 3 を「無い(戦略に渡る口に取消が無い。`cancelOrder` は engine が値を追い直すときに自分で呼ぶ内側の関数(835-888 行))」とする。一次資料の同じ版の engine.js 831-835 行は `checkOrder` で「signal switched during …, aborting → `return cancelOrder(order, type, false, cb)`」で、戦略が信号を切り替えると engine が注文を取り消す。取消の結果を戦略に返す口は無い(戦略に渡る口は 104-109 行の `orderExecuted` ほか)ので、能 3(取り消し、その結果が戦略に返る)を「無い」とする結論は変わらず、スキップも成り立つ(含む側の 1 Basana の p6-place-then-cancel・p6-cancel-notice が「正解と一致」)。理由の欄に「信号の切り替えで engine が取り消す道(831-835 行)はあるが、結果は戦略に返らない」を足すと、読む者が同じ確かめをしなくて済む。

根拠: `curl -sS https://raw.githubusercontent.com/DeviaVir/zenbot/52872fb4b5f9d10e2f891d95daec05da0b721ceb/lib/engine.js`(読むだけ。実行していない。`<S>/r11_critic/zenbot_engine_52872fb.js`、1009 行)→ 831-835 行 `function checkOrder (order, type, cb) { if (!s[type + '_order']) { // signal switched, stop checking order … return cancelOrder(order, type, false, cb)`。

## 前の周の指摘の直りを確かめた記録(直ったものは上に挙げない)

| 前の指摘 | 確かめたこと(コマンドと出力) | 結論 |
|---|---|---|
| i0-r9-01(history_limit の下の断りすぎと、事実と違う断りの文) | 第 9 周の最小の再現 `item0_r9_critic_probe_history_until.py` → `until_ns=T0+3s -> [1, 2] place (0, 1, 3, 0)` / `n=1, until_ns=T0+3s -> [2] place (1, 1, 3, 0)` / `until_ns=T0 (before every event) -> [] place (0, 1, 3, 0)`(制限なしと同じ事象の列)。自分の神託 `<S>/r11_critic/item0_r11_critic_probe_history_oracle2.py 1001 1060`(契約の文だけから作った。4 型・同時刻の束・N 1〜4・60 件まで・n 9 まで・空の答えの place も見る)→ `{'ok': 908526, 'refused_ok': 205930, 'wrong': 0, 'silent_short': 0, 'over_refused': 0, 'place_wrong': 0}`。断りの文の勧め(「since_ns を名指した事象の受け取り時刻より後」「n <= 保たれた最新の件数」)は `api.py` 807-848 行 `__refuse_truncated` の作りで、名指すのは答えの中の落とした事象のうち最新の物なので、どちらの勧めでも落とした事象は答えから外れる(読みで確かめた)。直りを固定する試験 `tests/bt/critic/item_0/test_i0r11_history_limit_exact_refusal.py`(断りすぎと空の答えの place も見る)→ `10 passed` | 直った |
| i0-r9-02(`__class__` の代入で核が戦略のコードを `on_event` の外で走らせる / 閉じ込めから核の物に届く) | 第 9 周の試しは名前で口を探すので今の版では動かない(リードの §8.5 の 28 のとおり批評家が作り直す)。作業者の試しを使わずに書いた `<S>/r11_critic/item0_r11_critic_probe_reach_swap.py`: 26 回の呼び出しのたびに、文脈から gc の参照(関数の cell・既定値・kwdefaults・`__dict__`、結び付いた方法の `__self__`)で歩いて届く物と、エンジンから(戦略の側の入れ物と戦略に入らずに)歩いて届く物を突き合わせ、届いた物のうち class を変えられる物の全部に、特殊な方法と `__getattribute__`・`__setattr__` を記録する子 class を `__class__` で与えた → `callbacks with core state shared: []`、記録の付いた class 13 種(`_OrderPort`・`StrategyContext`・`EventWindow`・`DeliveredList`・`OrderView`・事象 7 種・`array`)、`uses of those classes OUTSIDE on_event: [] count 0`。結果は当てない実行と同じ(`digest 780a441aafb0cf8f`、約定 2 件、注文 3 件の状態が同じ。`…_reach_swap.out`) | 第 9 周の 2 つの道は直った。同じ族の別の形が残る = i0-r11-01・i0-r11-03 |
| i0-r9-03(DEFINITIONS の「未決」の升目) | `grep -c '未決' DEFINITIONS.md` → `4`。4 行とも p6-place-then-cancel の文(884・888・889 行)で、注文の状態の「未決の注文」。升目の判断の値は `grid_c.py` 102 行 `VERDICTS` の 2 つだけ。表の節の頭(101 行)に §8.2 の 2 の 1 文がある。`test_battery_item0.py` 1474 行の試験(正の定義 0〜E の凍結)を含む場面集の試験は通る(下) | 直った |
| i0-r9-04 [示唆](集合の反復の順と PYTHONHASHSEED) | リードの答え §8.3: 項目 8 の要件を固定するときに決める | リードの決定で持ち越し |
| 前の周までの [止める](i0-r8-01・i0-r7-01・i0-r7-02 ほか) | 批評家の試験の全部を今の作業木で回した: `PYTHONPATH=src python -m pytest tests/bt/item_0 tests/bt/critic/item_0 -p no:cacheprovider` → `1624 passed, 2 skipped in 320.15s`(この周の私の試験を足す前。`<S>/pytest_item0_r11_critic_core.log`) | 直ったまま |

### 付け直しの見直し(前の周の [直す]・[示唆])

前の周の [直す] 3 件は直った。[示唆] i0-r9-04 はリードの決定で持ち越し、[止める] の基準(要件・正解・試験・信頼性と再現性・場当たり・§4・場面集の規則)のどれにも当たらない(核の配達の要約は種によらず同じ = 第 9 周の実測)。付け直す物は無い。

### 規則 8(作業者が「試験自身の誤り」と報告した批評家の試験)

第 10 周・第 11 周の作業者の報告(`round_10/REPORT.md` 51 行、`round_11/REPORT.md` の (3))は、どちらも「批評家の試験が試験自身の誤りで落ちるものは無い」。第 9 周の後に批評家の試験は消されても書き換えられてもいない(`git diff --stat 5092565 HEAD -- tests/bt/critic/item_0` は第 9 周の私の前任の試験 1 本の追加だけ)。取り下げる試験は無い。

## 場面集の側で見たこと

- 場面集の試験: `PYTHONPATH=src python -m pytest tests/bt/battery/item_0 -p no:cacheprovider` → `78 passed in 38.33s`(`<S>/pytest_item0_r11_critic_battery.log`)。検討表の機械の検め: `python3 scripts/check_bt_considered.py tests/bt/battery/item_0/opponents/CONSIDERED.md` → `OK 誤り 0 件`。
- 第 9 周から場面集で変わったのは DEFINITIONS・ROOTCAUSE_r10-1/r11-1・def_axes/jC・def_grids・gen_definitions・grid_c・line/term の判断・試験で、adapter・runner・検討表・再現・mutant・scenes.py は変わっていない(`git diff --stat 5092565 HEAD -- tests/bt/battery/item_0`)。
- 正の定義 C の置き換え: `ROOTCAUSE_r8-1.md` 555 行の C を「。」で切ると、置き換わったのは第 9〜12 文(3 値の判断・測り方の文の語で決める・リードの決定・その当て方)だけで、ほかは同じ(`test_battery_item0.py` 1474 行の試験が照らし、通る)。
- **リードの答え §7.3 の 16 (a) の続き(検討表の「スキップ(上位互換)」を番号の順に 3 行)**: 第 9 周の批評家の名指しどおり 13 DeviaVir/zenbot(P0-6)・13(P0-7)・38 microsoft/MarS(P0-7)を読んだ。
  - 含む側に引かれた結果は全部「正解と一致」: `survey_results/opp_basana.tsv` の p1-one-call-per-event・p6-place-then-cancel・p6-cancel-notice・p6-fill-seen-by-strategy・p7-fill-model-swap・p7-cost-model-swap・p7-cost-per-unit、`opp_aat.tsv` の p7-fill-model-swap、`opp_mihircoding_lob.tsv` の p7-latency-model-swap、`opp_gobacktest.tsv` の p7-account-swap(`awk -F'\t' '$2 ~ /^p1-one-call|^p6-|^p7-/ {print $2, $5, $7}'` の出力)。含む側の Basana の行は資料係の venv の配布物に実在する(`basana/core/dispatcher/base.py` 155 行 `def subscribe(`、`basana/backtesting/exchange.py` 361 行 `def subscribe_to_order_events(`・103 行 `fee_strategy: fees.FeeStrategy = fees.NoFee(),`、`basana/backtesting/fees.py` 35 行 `class FeeStrategy`)。
  - 一次資料の読み(読むだけ): zenbot の engine.js 104-109 行(`orderExecuted`)・792-800 行(`cancelOrder`)は行のとおり。831-835 行の信号の切り替えによる取消は i0-r11-04。MarS の mlib/core/engine.py 35-39 行(`Engine(exchange: Exchange, …)`)・143-144 行(`wakeup_time + agent.computation_delay + agent.communication_delay`)は行のとおり。3 行ともスキップは成り立つ。
  - 次の周の批評家は、番号の順で次の 3 行(52 QuantConnect(P0-6)・52(P0-7)・57 WonderTrader(P0-1))を読む。
- 資料係の表: 6 枚の組の 2 通りは 3 組とも違う(`round_11/materials/md5sum_pairs.txt`)。場面集の指紋が第 9 周と違うので相手の道具を全部走らせ直した(`materials/commands.txt`、L-435 どおり)。新実装の行は `materials/runs/new_impl.tsv` で 32 / 32 が「正解と一致・2 回の実行で同じ」。
- adapter の公平さ: adapter は第 9 周から変わっておらず、第 9 周の批評家の読み(新実装の adapter が約定の模型に場面集の側の小さな模型を渡すのは公開の差し込み口の範囲)を変える物は無い。型を対象が選ぶ場面で新実装の adapter が約定を選ぶこと(`new_impl.py` 294 行)は、他の対象も 1 型を選ぶ規則(場面の note)の範囲で、表のセルの勝ち負けを決めていない。これが升目の表の宣言と合わないことは i0-r11-02。
- 覆い: 固定した要件 §2 の P0-1〜P0-7 の全観点に値の場面が 1 つ以上ある(`scenes.py` 612-614 行の assert)。升目の表の「場面にした」の過大は i0-r11-02。

## 構造の変化

前の周から構造は変わった(`structural_change_since_prev = true`)。コードで確かめたもの: 外のコードが作った例外と class を核が扱うとき、型の名前を `type` の記述子で読み(`values.py` 194-213 行 `class_parts`・`type_name`)、FAILED の断りの文を例外の事実だけから作る(`values.py` 230-249 行 `exception_text`、`engine.py` 884-900 行)/ 差し込み口の名前を構築のときに 1 度だけ読む(`engine.py` 758-763 行 `_models`、`result()` は差し込み口の class を読まない)/ `values._now` の断りの文も `exception_text`。第 10 周の構造(戦略の側の物を `_StrategySide` 1 か所にまとめ、核の状態から参照しない)は、私の試しで到達性 0 を確かめた(上の表)。

## 提出前の吟味(批評家の文: 指摘ごとに根拠を自分で再現し、格付けを基準に照らし、前の周の指摘の直りを自分で確かめ、相手の付け違いが無いか確かめる)

| 指摘 | 根拠を自分で再現したか | 格付けを基準に照らした結果 | 相手 |
|---|---|---|---|
| i0-r11-01 | 試し 5 本と試験 1 本(12 升目)を打ち、出力を上に逐語で写した。最初の試しは自分の print が `type(exc).__module__` を読んで鍵の `__eq__` を走らせた(自分の誤り)ので、印を付けてから読むように直して打ち直した。試験の落ち方が試験自身の誤りでないことを、pytest を通さない同じ組み立て(`item0_r11_critic_probe_sockets_key.out`)で確かめた | 走るのは同じ時刻の配達の途中か失敗の後で、核の判断・送る物・結果・配達の要約は変わらない。失敗で止まる経路は i0-r9-02 (a) と同じ類で、リードの §7.5 の 22 が [直す] のまま置いた。[止める] の基準(要件・正解・試験・信頼性と再現性・場当たり・§4・場面集の規則)のどれにも当たらない = [直す]。作業者の直しは読み方の規則を全部の読み手に当てた物で、場当たりではない(前提の誤り) | 実装(`src/bot/bt/core/values.py`・`engine.py`・`contract.py`) |
| i0-r11-02 | 升目と入力の型の突き合わせを打ち、試験を書いて打った(13 failed)。時計の升目は自分の数えの誤り(時計の事象は入力でなく戦略の頼みで作られる)なので数えから外した | 場面・正解・表のセルは変わらないので [直す] とも読めるが、測っていない 18 升目を「場面にした」とする事実の誤りで、表の目的(測っていない範囲の記録)を損ない、通過の報告に有利な向き。迷ったので重い方の [止める] | 場面集(`tests/bt/battery/item_0/scenes.py` の `COVERS`、その出力の DEFINITIONS.md) |
| i0-r11-03 | 試しと試験を打った(`BufferError`) | 失敗で止まる経路で、黙って誤った値は無い = [直す](i0-r9-02 (a) と同じ類) | 実装(`src/bot/bt/core/history.py`・`engine.py`) |
| i0-r11-04 | 一次資料の同じ版を読み、行を写した | 結論とスキップは変わらない。要件の外の改善 = [示唆] | 場面集(検討表) |

場当たりの直し(試験だけの特別扱い・閾値や既定値をずらす・文言合わせ・機能を外す)は見つからなかった。

この周に足した批評家の試験(`tests/bt/critic/item_0/`): `test_i0r11_class_dict_key_runs_foreign_code.py`(12 件、全部落ちる = i0-r11-01)、`test_i0r11_covers_within_scene_input.py`(32 件、13 件落ちる = i0-r11-02)、`test_i0r11_pinned_dropped_facts_fail_the_core_step.py`(1 件、落ちる = i0-r11-03)、`test_i0r11_history_limit_exact_refusal.py`(10 件、通る = i0-r9-01 の直りの固定)。批評家の試験の全部: `PYTHONPATH=src python -m pytest tests/bt/critic/item_0 -p no:cacheprovider` → `26 failed, 114 passed in 199.64s`(`<S>/pytest_item0_r11_critic_criticdir.log`。落ちる 26 件はこの周の 3 本だけ)。


### 審査員 6 体の出力(逐語。左右の割り当ては `round_11/JUDGES.md`)

# 盲検の審査員の出力(項目 0 第 11 周、Workflow の記録から逐語で書き出し)

## 盲検:0#11:current0(agent ada05215ae42ca420)

```json
{
  "choice": "右",
  "reasons": "表のセルから自分で数え直した結果。正しさ(正解と一致の数)は、行 A が P0-1 で 1/3(p1-one-call-per-event だけ)、P0-2 で 2/4(p2-event-time-exact・p2-one-ns-apart)、P0-3 で 1/11(p3-bar だけ)、P0-4 で 1/3(p4-visible-at-step。p4-future-read-attempt は不一致で、every_attempt_stopped_by_error=false。未来の値は取れていないが、試みが誤りとして止められていない)、P0-5 で 1/3(p5-same-stream-order)、P0-6 で 0/3、P0-7 で 2/5(p7-fill-model-swap・p7-cost-model-swap)。計 8/32 で、表の数と合う。行 B は 7 観点すべてで全件一致し、計 32/32。行 B は観点ごとに見ても 7 観点すべてで行 A 以上で、行 B が劣る観点は 1 つも無い。特に行 A は P0-6(戦略の API)が 0/3 で、P0-3(8 種の事象型)は 11 件中 10 件が対応なしなので、能力そのものが欠けている。再現(2 回の実行で同じ)は、行 A・行 B とも 7 観点すべてで全件同じ(各 32/32)で、差は無い。したがって、正しさで行 B が明確に優れ、再現は同等なので、行 B を選ぶ。",
  "missing_in_choice": "表に示された 32 場面の中には、行 B に足りない場面はありません。表が示すかぎり、行 B は全場面で「正解と一致」かつ「2 回の実行で同じ」です。"
}
```

## 盲検:0#11:current1(agent a651d746abff1581c)

```json
{
  "choice": "左",
  "reasons": "表のセルから観点ごとに数え直すと、数は表の集計と合っていました。\n\n正しさ(正解と一致の数)は、7 観点のすべてで行 A が行 B と同じか上でした。\n- P0-1: A 3/3、B 1/3(B は p1-merge-by-time と p1-typed-events が対応なし)\n- P0-2: A 4/4、B 2/4(B は p2-iso-utc と p2-iso-offset が対応なし)\n- P0-3: A 11/11、B 1/11(B で一致したのは p3-bar だけ。残り 10 件は対応なし)\n- P0-4: A 3/3、B 1/3(B は p4-received-time が対応なし。p4-future-read-attempt は不一致で、every_attempt_stopped_by_error が false)\n- P0-5: A 3/3、B 1/3(B は p5-same-time-twice と p5-hand-over-order が対応なし)\n- P0-6: A 3/3、B 0/3(B は 3 件とも対応なし)\n- P0-7: A 5/5、B 2/5(B は p7-latency-model-swap・p7-cost-per-unit・p7-account-swap が対応なし)\n- 計: A 32/32、B 8/32\n\nどの観点でも B が A より上になることはありません。P0-3 のように場面の多い観点を除いても、残り 6 観点すべてで A が上です。\n\n再現(2 回の実行で同じ)は、A も B も 7 観点すべてで満点(32/32)で、差はありません。ただし B の「2 回の実行で同じ」は、多くが「対応なし」を 2 回返した結果です。\n\n以上から、正しさ(正解との一致・能力の有無)では A がはっきり優れ、再現性は同じです。よって行 A を選びます。",
  "missing_in_choice": "表に示された結果の範囲では、行 A に足りない場面はありません(32 場面すべてで正解と一致し、2 回の実行でも同じ)。"
}
```

## 盲検:0#11:current2(agent a7932d56403306578)

```json
{
  "choice": "右",
  "reasons": "表のセルから観点ごとに数え直した。表の集計行と一致した。\n正しさ(正解と一致):\n- P0-1: A 1/3(p1-one-call-per-event だけ一致。残り 2 件は対応なし)、B 3/3\n- P0-2: A 2/4(p2-iso-utc と p2-iso-offset は対応なし)、B 4/4\n- P0-3: A 1/11(一致は p3-bar だけ。ほかの 10 件は対応なし)、B 11/11\n- P0-4: A 1/3(p4-received-time は対応なし。p4-future-read-attempt は不一致で、値は every_attempt_stopped_by_error=false)、B 3/3\n- P0-5: A 1/3、B 3/3\n- P0-6: A 0/3(3 件とも対応なし)、B 3/3\n- P0-7: A 2/5(p7-fill-model-swap と p7-cost-model-swap だけ一致)、B 5/5\n- 計: A 8/32、B 32/32\n再現(2 回の実行で同じ): 7 観点すべてで A・B とも全件が同じ。計はどちらも 32/32 で、差は無い。\n判断: 7 観点のどれでも、正しさは B が A 以上。A より B が多い観点は 7 つ全部なので、場面の数が多い P0-3 に引きずられた結果ではない。A には不一致が 1 件(P0-4 の未来を読もうとする場面で、読み出しが誤りで止められていない)あり、B には対応なしも不一致も無い。再現は同点なので、差は正しさだけから出ている。よって行 B(右)を選ぶ。",
  "missing_in_choice": "この表の範囲で、B に足りない場面は無い(32 場面すべてで正しさが「正解と一致」、再現が「2 回の実行で同じ」)。ただし、表が扱うのは 7 観点の 32 場面だけである。場面の定義で「測っていない(固定した測り方の外)」とされた升目については、表から何も言えない。"
}
```

## 盲検:0#11:survey0(agent a2aaeb5db28bf65b6)

```json
{
  "choice": "右",
  "reasons": "正しさ(「正解と一致」の数)を表の各セルから数え直した。行 A: P0-1 3/3、P0-2 4/4、P0-3 10/11、P0-4 3/3、P0-5 3/3、P0-6 3/3、P0-7 5/5、計 31/32。行 B: P0-1 3/3、P0-2 4/4、P0-3 11/11、P0-4 3/3、P0-5 3/3、P0-6 3/3、P0-7 5/5、計 32/32。この数は表の集計行(51〜52 行目)と一致する。再現(「2 回の実行で同じ」)は、A も B も 7 観点すべてで満点(計 32/32)。2 つの対象に差があるのは P0-3 の p3-mixed-one-run の 1 場面だけ。この場面で A は「対応なし」、B は「正解と一致」だった。p3-mixed-one-run は P0-3 で唯一の値を見る場面(8 種の事象型を 1 回の実行に混ぜて流す)で、ほかの 10 場面は能力を見る場面である。A は型を 1 種ずつ流す場面では全部一致したが、混ぜた実行には対応していなかった。残る 6 観点は正しさも再現も同じなので、1 観点での差でも B が上と言える。場面の多い観点に引きずられた判断ではない。差の場面は 1 件だけなので、差の大きさは小さい。",
  "missing_in_choice": "行 B は、表の上では 32 場面すべてで「正解と一致」かつ「2 回の実行で同じ」なので、欠けた場面は無い。ただし行 B は候補の結果を寄せ集めた行である。注記によると、候補 52 件のうち、動かせた 36 件と、機構を書き直して走らせた 1 件の結果しか入っておらず、15 件は入っていない。また次の場面では、寄せた対象のうち 13〜18 件が結果なし(機構が未実装・例外・出所の検めで退けられた)で、行には残りの対象の最も良い結果が置かれている: p2-iso-utc、p2-iso-offset、p3-bar、p3-clock-timer、p3-notice-accepted/rejected/filled、p4-visible-at-step、p4-received-time、p4-future-read-attempt、p6-place-then-cancel、p6-cancel-notice、p6-fill-seen-by-strategy、p7 の 5 場面。このため、1 つの対象が全場面を満たしたとは表からは言えない。"
}
```

## 盲検:0#11:survey1(agent a9ad8290ac8bd7363)

```json
{
  "choice": "左",
  "reasons": "表の各セルを数え直した結果を観点ごとに比べる。正しさ(正解と一致の数)では、P0-1(3 件)、P0-2(4 件)、P0-4(3 件)、P0-5(3 件)、P0-6(3 件)、P0-7(5 件)の 6 観点で A と B が同じく全件一致した。差が出たのは P0-3(11 件)だけで、A は 11/11、B は 10/11。B が外したのは表の 86 行目の 7 列目、p3-mixed-one-run(値の場面)で、「正しさ: 対応なし」になっている。この場面は、6 種の市場の事象を 1 回の実行に混ぜて入れたときに出る型と時刻の列を見るもので、B はこの能力を示せていない。再現(2 回の実行で同じ)は、表中に「2 回で違う」も「結果なし」も 1 件も無く、A・B とも 7 観点すべてで全件一致した(32/32)。合計では、正しさが A 32/32、B 31/32、再現は両方 32/32。7 観点のうち 6 観点は同等、1 観点(P0-3)で A が上回り、B が上回る観点は無い。場面の数が多い観点に引きずられたのではなく、差のある観点がこの 1 つだけで、その向きが A 優位である。差は 1 場面だけだが、正解と一致しなかったのが値の場面で、しかも「対応なし」なので、能力の有無の差として A を選ぶ。数え直しの確認: 「正しさ: 正解と一致」の出現は A の行が 3+4+11+3+3+3+5=32、B の行が 3+4+10+3+3+3+5=31。「対応なし」は 86 行目の 1 件だけ。表の集計(A 32/32・B 31/32、再現は両方 32/32)と合う。",
  "missing_in_choice": "表の範囲では、A が正解と一致しなかった場面も、2 回の実行で違った場面も無い(32/32)。ただし、場面の定義の升目で「測っていない(固定した測り方の外)」とされた部分(各事象型について、発注・取消の呼び出しがその場で返す物、戦略が対象の公開の手段で読む物)は場面になっていない。この部分で A が正しいかは、この表からは分からない。"
}
```

## 盲検:0#11:survey2(agent ad324ddcfb5d6b90e)

```json
{
  "choice": "右",
  "reasons": "表の各セルを自分で数え直した(67〜122 行の各行で「正解と一致」と「2 回の実行で同じ」を数えた)。結果は冒頭の集計表(51〜59 行)と一致した。\n正しさ(正解と一致の数): P0-1 は A 3/3・B 3/3、P0-2 は 4/4・4/4、P0-3 は A 10/11・B 11/11、P0-4 は 3/3・3/3、P0-5 は 3/3・3/3、P0-6 は 3/3・3/3、P0-7 は 5/5・5/5。計は A 31/32、B 32/32。\nA の 1 件の欠けは P0-3 の p3-mixed-one-run で、「対応なし」だった。この場面は、6 種の市場の事象(約定・板の写真・板の差分・足・資金調達・清算)を 1 回の実行に混ぜて入れたとき、型と時刻の列が入力どおりに出るかを見る値の場面である。B は正解と一致した。\n再現(2 回の実行で同じ): 7 観点すべてで A・B とも満点(計 32/32 ずつ)なので、差は無い。\n観点ごとに比べると、7 観点のうち 6 観点は同点、1 観点(P0-3)で B が上、A が上の観点は無い。したがって B の方がより正しく、再現性は同等である。差は 1 場面だけだが、「対応なし」は良い順で「正解と一致」の下にあたるので、方向ははっきりしている。\n注意点: 行 A か行 B の一方は、多数の候補を寄せた行である。その行の値は「残りの対象の最も良い結果」を採っている(注記 11〜45 行)。このため、その行の満点は 1 つの対象の能力を示すとは限らない。ただ、表に示された結果の比較としては B が優れる。",
  "missing_in_choice": "表の上では、B(右)に足りない場面は無い(32 場面すべてで正解と一致し、2 回の実行でも同じ)。ただし表の外の話として、次の 2 点がある。(1) 寄せた行では、場面ごとに最も良い結果を採っている(p2-iso-utc・p3-clock-timer・p3-notice-* ・p4-* ・p6-* ・p7-* では 13〜18 件が結果なし、p3-bar では 1 件が TypeError)。B がその行だった場合、1 つの対象としての欠けはこの表からは読み取れない。(2) DEFINITIONS の「測っていない(固定した測り方の外)」の升目は、場面になっていないので比べられない。"
}
```


## 第 12 周

### 結果(台本の返り値 `status: 'escalate'`、`reason`: 「定義の段が 3 回で通らなかった(LEAD_DESIGN §8.2 の 3)」。作業者 `作る:0#12` は完了(全試験 4765 passed、落ちるのは場面集の側の批評家の試験 13 件だけ)。表・批評家・審査員はこの周には無い)

### 定義 r12-1-1〜r12-1-3 と監査役(定義)r12-1-1〜r12-1-3 の出力(逐語)

## 定義:0#r12-1-1(agent a6addc6afa28ec51f)

- 根本原因と定義の記録: /home/user/trade/tests/bt/battery/item_0/ROOTCAUSE_r12-1.md

定義(逐語):

**升目を場面にしたと数える物**: 升目(事象の軸の値 e・見る道 v・観点の追加の軸の値 x)を場面 s が「場面にした」と数えるのは、s を scenes.py が載せた入力のまま走らせる対象(入力に書いた型を全部持つ対象。`type_plan` の場面では scenes.py が載せる組 = 6 型を持つ対象の組で、LEAD_DESIGN.md §8.5 の 24 の「`type_plan` で作る事象」)のどれもが、型 e の事象を見る道 v を通して x の下で戦略に届けなければ s の正解と一致にならない、と s の文(入力・正解・正解の出し方・測る物・採点の元)だけから言えるときだけである(対象の出力は読まない)。型 e の事象とは、市場の事象の型なら s の入力に型 e と書いてある事象、時計・注文の通知・取消の通知なら s の入力の戦略の頼み(時計の頼み・発注・取消)に対象が応えて作る事象で、どちらも正解が名指すのがその事象そのもの(届いたこと・件数・順・型・時刻・欄の値)であるときに限る。次の物は、s の `covers` に書いてあっても「場面にした」としない: 型を対象か adapter が選べる事象の型(型を書かない事象、「型は対象が受ける型を 1 つ選んでよい」の類の注。入力に書いた型を全部持つ対象でも別の型で走らせてよいので、どの型も要らない)/ 事象を 1 件も持たない場面の事象の軸の値 / 入力の型を持たない対象にだけ許した代え(`any_type`・「足を受けない対象は約定で代えてよい」の類)で入る型 / 正解と一致に複数の見る道のどれか 1 つで足りる場面の、それぞれの道 / 戦略の呼び出しの外で読んだ記録でも正解と一致になりうる場面の見る道 / 公開の読み出しの手段を持たない対象でも正解と一致になりうる場面の「戦略が対象の公開の手段で読む物」/ 正解が事象そのものでなく対象の別の状態(注文の状態・約定済みの数量・口座の記録)から出る場面の、その事象の型 / 上の条件を s の文で示せない物(既定は「場面にした」としない)。`covers` はこの条件を満たす升目だけを持ち、升目の判断は LEAD_DESIGN.md §8.2 の 1 のとおり `covers` から機械で 2 値に決める。`covers` の市場の事象の型は s の入力(と `type_plan` の載せた組)から機械で出し(同 §8.5 の 24)、時計・通知の型・見る道・観点の追加の軸の値は場面係が s の文から上の条件で書き、批評家と監査役が同じ条件で読んで確かめる(同 §8.2 の 1)。この定義は `covers` と升目の表だけに当て、場面の入力・正解・採点・比較の表のセルを変えない。表の「場面にした」を狭める向きにだけ効く。

## 監査役(定義):0#r12-1-1(agent a6e10026a8caaa08f)

- [止める] tests/bt/battery/item_0/ROOTCAUSE_r12-1.md:38(正の定義)/48(§4表・§8.5の24の行) — §3の定義の「型eの事象とは…どちらも正解が名指すのがその事象そのもの(届いたこと・件数・順・型・時刻・欄の値)であるときに限る」と、除外項目「正解が事象そのものでなく対象の別の状態(注文の状態・約定済みの数量・口座の記録)から出る場面の、その事象の型」は、covers の**市場の事象の型の軸**に「正解がその事象自体を名指すか」という意味読解の条件を課している。これは LEAD_DESIGN.md §8.5 の 24「`covers`の事象の軸は…実際に含まれる型から機械で出す」という機械的(入力に型があるかだけを見る)ルールを超える判断であり、§4 の表自身が同じ行で「市場の事象の型の部分は 24 の文どおり」と主張しているのと文面が食い違う。§8「リードに聞くこと」は見る道(v)の逸脱だけを問い、この事象の型(e)軸への逸脱には触れていない。固定した規則(§8.5の24)に無断で反していないか、あるいはなぜ機械的ルールの範囲内と言えるのかを問う(委任文§3「定義は…新しい一般規則…を足さない」、LEAD_DESIGN.md §8.2の4「固定した規則に反しないか」)。
- [止める] tests/bt/battery/item_0/ROOTCAUSE_r12-1.md:38(正の定義)/95(§8「リードに聞くこと」1) — §3の定義は見る道(v)の軸にも「型eの事象を見る道vを通して…届けなければsの正解と一致にならない」という**必要性**の条件を課しているが、これは LEAD_DESIGN.md §8.5の24が定めた「見る道の軸は場面の宣言のままでよいが、その道を実際に呼ぶ入力であることを批評家が読む」(=実際に呼ばれるかの確認であって、正解との一致への必要性の確認ではない)より狭い基準である。§8の1自身がこの逸脱を認めて「これを当てるとよいか」とリードに聞いているのに、§3の定義本文(このファイルが監査役に通そうとしている「正の定義」そのもの)は既にこの狭い基準を確定したものとして書かれ、除外(e)(f)(h)がそれに基づいて適用されている。リードの承認前に、承認を要する論点を確定事項として定義に織り込んでよいか。
- [直す] tests/bt/battery/item_0/ROOTCAUSE_r12-1.md 全体(§2・§3・§5・§7・§8のどこにも無い) — 指摘 i0-r11-02 の逐語は「人の読みで残る点: p6-place-then-cancel の covers(注文の受付の通知, 読む物)は、場面が読むのは未決の注文の数で受付の通知ではない」と、この場面を名指しで挙げている。ところがこのファイルの本文は p6-place-then-cancel に一度も触れていない。§5の出力 `<S>item0_r12-1_scenekeeper_def_forms.txt` の (g) には p6-place-then-cancel が「正解が事象の中身でなく対象の別の状態から出る」形として機械的に拾われているが、それが指摘の挙げた「残る点」を解消するのか、なお別途人の判断が要るのかを本文のどこにも書いていない。§7(提出前の吟味)の表にもこの指摘固有の論点への対応が項目として無い。
- [聞く] tests/bt/battery/item_0/ROOTCAUSE_r12-1.md:38 — 「正解が**名指す**のがその事象そのもの…であるときに限る」という語は、LEAD_DESIGN.md §8.2の1が明示的に退けた「要件の文を切片に切って**名指し**を決める機械は置かない(定義Gは採らない)」の「名指し」と同じ字面である。対象(要件の文の切片 vs 場面の正解の言明)は違うが、第10周で退けた「名指し」という考え方そのものを、語を変えずに別の場所(covers の中身を絞る条件)へ持ち込んでいないか。CLAUDE.md §0.2 O-7(用語の意味を変えて使い回す禁止の裏返し = 退けた概念を同じ語のまま別の場所で復活させること)に照らし、別の語にすべきではないか。
- [聞く] tests/bt/battery/item_0/ROOTCAUSE_r12-1.md:38・61-64(§5表) — 除外項目 (e)〜(h) は、§5「同じ根の探し」で場面集の全場面を機械的に走査し、指摘の文が挙げなかった形を場面係が追加で見つけた結果として書かれている(§5表の「挙げていない(場面係が足した)」の欄)。§7は「定義は形を列べる規則でなく…1つの条件で書き、形は『としない』の例として置いた」と自己弁護するが、実際の成り立ちは「見つかった具体例ごとに除外節を書き足す」という手順であり、結果として8つの『/』区切りの除外節を持つ。これは委任文§3「場所や形の一覧ではなく、どの形にも当たる1段落の規則」が禁じる「一覧」の実質と、どこで区別されるか。逆(先に一般条件があり、(a)〜(h)がその条件の単なる適用例であって、条件を書くために場面を探したのではない)であることを示す記述が本文に無い。

## 定義:0#r12-1-2(agent a2ee6d2f3e8409898)

- 根本原因と定義の記録: /home/user/trade/tests/bt/battery/item_0/ROOTCAUSE_r12-1.md(第 2 版の定義。コード・場面・DEFINITIONS.md は変えていない。

ファイルの中身: i0-r11-02 の根本原因は §2.1。監査役の第 1 版への指摘 5 件(dr12-1-1-1〜5)の根本原因は §2.2・§2.3 に書いた。第 1 版は、見つけた形ごとに除外を書き足し、§8.5 の 24 にも正の定義 C にも無い「要る」の条件を足していた。

p6-place-then-cancel への答え(指摘 3)は §5.1 にある。定義の機械の部分では決まらず、正の定義 C の人の読みで決まる。場面係の読みは「合わない」で、直しの段で外す。

リードに聞くことは §8 に 5 件: 「要る」の条件を足すか / 定義を当てたあとの表 / 候補 35 / 定義の置き場所 / O-10(正の定義 E)。

作業木で変えたのはこのファイルと、line_judgments.tsv(+21 行)・term_judgments.tsv(+55 行)だけ。第 1 版で足した判断は戻した。場面集の試験は 78 passed。批評家の試験 test_i0r11_covers_within_scene_input.py は 13 failed のまま(コードを変えない段のため)。

出力の置き場所: /tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/r12-1/ の下の item0_r12-1_scenekeeper_def2_{readings,cells,judge,pytest,status,lines_after,terms_after}.txt)

定義(逐語):

**升目を場面にしたと数える物**: 升目(事象の軸の値 e・見る道 v・観点の追加の軸の値 x)を場面 s が「場面にした」と数えるのは、その升目が s の `covers` にあるときだけで、判断は `covers` から機械で 2 値に決める(LEAD_DESIGN.md §8.2 の 1)。`covers` に置く升目は、固定した 2 つの文 — §8.5 の 24(事象の軸は場面の入力に実際に含まれる型から機械で出す。見る道は場面の宣言のままで、その道を実際に呼ぶ入力であることを批評家が読む)と、凍結した正の定義 C(`covers` は場面の宣言で、場面の測る物と `covers` が合うかは批評家が読んで確かめる)— だけから決め、この定義はほかの条件を足さない。e が市場の事象の型(約定・板の写真・板の差分・足・資金調達・清算)の升目は、場面係が s に宣言した市場の事象の見る道 v と x の組ごとに、s の入力の事象(scenes.py の入力の `events` と `streams` の事象。`type_plan` の場面では scenes.py が 6 型を全部持つ対象のために作る事象)の型の欄(`kind`)に書いてある型の全部について機械で置き、それ以外の市場の事象の型には置かない。機械が読むのは型の欄の値だけで、注の文・代えの許し(`any_type` の類)・型の欄の無い事象からは型を出さず、測る物の文も読まない。市場の事象の見る道を宣言しない場面には、入力に市場の事象があっても市場の事象の型の升目を置かない。e が市場の事象の型でない値(時計・注文の受付/拒否/約定の通知・取消の通知)の升目と、全部の升目の v と x は、場面係が s の宣言として書き、批評家と監査役が s の文(入力・正解・正解の出し方・測る物)を読んで、s の測る物と合うこと(正の定義 C)と、v については s の入力がその道を実際に呼ぶこと(§8.5 の 24)を確かめる。測る物と合わない升目と、入力が呼ばない道の升目は `covers` に置かない。この定義は `covers` と升目の表だけに当て、場面の入力・正解・採点・比較の表のセルを変えない。

## 監査役(定義):0#r12-1-2(agent a1a5dcf7746db2d9b)

- [止める](repeat_of i0-r11-02) tests/bt/battery/item_0/ROOTCAUSE_r12-1.md:60(§3 正の定義)/66(§4 表「正の定義Aの型の組」の行)/100(§6 の 1「型は入力…の型の欄から機械で出す」「runner・adapter…は変えない」) — §3 は `type_plan` の場面(p1-merge-by-time・p1-typed-events・p5-same-time-twice・p5-hand-over-order の 4 場面のみ、`L438_2_SCENES`)の市場の事象の型を「scenes.py が **6 型を全部持つ対象のために作る事象**」から機械で置くと定義している(実際の読みの道具 `<S>item0_r12-1_scenekeeper_def2_readings.py` も `scenes.for_target_types(s, scenes.TYPE_ORDER)` で 6 型固定に計算している)。これは LEAD_DESIGN.md §8.6 の項目 29(「**場面係は定義 r12-1-2/3 でこれを当てる**」と明記され、時刻は §8.5 の 24〈20:58 UTC〉より後の 22:00 UTC。第 1 版への監査 dr12-1-1 への直接の答え)が明示する規則「`covers` の事象の軸は、その場面を**走らせた記録**(runner が場面ごと・設定つき対象ごとに残す入力の事象の型)から機械で出す。**scenes.py の手書きの宣言も…使わない**」「**型を対象が選ぶ場面は、走った対象ごとに実際に入った型だけを数える(6 型を宣言しても 1 型しか走らなければ 1 型)**」と正面から食い違う(静的な 6 型仮定 vs 対象ごとの走った記録)。加えて L-438 (2) の承認条件「**値が不一致の型は『持つ』と数えない**」(LEAD_DESIGN.md §3.4 相当行)も、この 4 場面の型の有無を対象ごとの実測で決めることを求めており、静的な 6 型仮定と整合しない。このファイルは §8.5 の 24 だけを繰り返し引用し(§0・§4・§7)、項目 29 の文言(「走らせた記録」「runner」)を本文中に一度も引かず、§6 の直しの計画でも「runner…は変えない」としており、項目 29 を実装するための runner の記録機構を作る予定にも触れていない。この静的仮定は、i0-r11-02 の族(升目の表の「場面にした」が場面の入力・測る物より広い宣言から出る)と同じ向き(実際に走らせた範囲より広く「場面にした」を計上する)に効く。定義が固定した文(§8.5 の 24)だけから書かれ、より新しくこの回に直接名指しで当てるよう指示された §8.6 の 29 に反していないか、反していないなら 29 との不一致をどう読んだかを本文のどこにも書いていない点を問う。
- [聞く](repeat_of dr12-1-1-2) tests/bt/battery/item_0/ROOTCAUSE_r12-1.md:66(§4 表 1 行目) — §4 は「24 の文を字のまま全部の場面に当てると…升目が足される」「24 は『宣言を狭める』答えで広げる向きには書かれていないので、24 の 2 つの半分(型は入力から機械で / 見る道は宣言のまま)を合わせ、**宣言した見る道の無い場面には市場の事象の升目を置かない**と読んだ」と書く。これは §8.5 の 24 の逐語(「事象の軸は…入力に実際に含まれる型から機械で出す」「見る道の軸は場面の宣言のままでよい」)を場面係が独自に組み合わせて導いた読みであり、24 の文自体には書かれていない結論(宣言に無い見る道の場面では市場型の升目を一切置かない)である。dr12-1-1-2 の根本原因(§2.2 根 6)は「第 1 版は見る道の条件を §8 の 1 でリードに聞きながら、同じ条件を定義の本文に確定した物として書いた」であったが、この第 2 版の§4 のこの読みも、固定した文の字面を超える解釈を場面係が単独で確定し(結果が今の場面集で他の読みと一致することを根拠に済ませ)、リードに聞く候補にも挙げていない(§8 の 1〜5 のどこにもこの論点が無い)。今の場面集で結果が変わらないことは今回たまたまの事実であり、定義の読みそのものが固定した文を超えていないかとは別問題ではないか。この解釈上の分岐点を「リードに聞くこと」に挙げず、§4 の表の中で確定事項として書いてよいか。

## 定義:0#r12-1-3(agent a47b6e40bf3b92934)

- 根本原因と定義の記録: /home/user/trade/tests/bt/battery/item_0/ROOTCAUSE_r12-1.md

定義(逐語):

**升目を場面にしたと数える物**: 升目 (e, v, x)(事象の軸の値 e・見る道 v・観点の追加の軸の値 x)を場面 s が「場面にした」と数えるのは、この場面集の走った記録のどれか 1 本(どの設定つき対象の記録でもよい)で型 e の事象が s の入力として対象に入っており、かつ s が見る道 v と x の組 (v, x) を宣言しているときだけで、判断は機械で 2 値に決める(LEAD_DESIGN.md §8.6 の 29、§8.2 の 1)。e は事象の軸の全部の値について同じく、runner が場面ごと・設定つき対象ごとに、その実行で対象に入った入力の事象の型として残した記録だけから機械で出す。scenes.py の手書きの宣言(`covers` の事象の値・注・`type_plan` の場面の作りの手本・`any_type` の許し)も、adapter が書いた値も、「正解がその事象を名指すか」「その道を通さなければ正解にならないか」という意味の読みも使わない。型を対象か adapter が選ぶ場面は、走った設定つき対象ごとに実際に入った型だけを数え(6 型を宣言しても 1 型しか入らなければ 1 型)、記録に型の無い事象と、入力が対象に入らなかった実行(runner が対象を呼ばずに「対応なし」にした実行を含む)からは型を出さない。(v, x) は場面の宣言のままで(正の定義 C)、記録から出た e と宣言した (v, x) の全部の組を数え、宣言した見る道が市場の事象を見る道かどうかなど、この 2 つのほかの条件を足さない。宣言した (v, x) が s の測る物と合うか、s の入力がその道を実際に呼ぶかは批評家が読む(§8.5 の 24・正の定義 C)。この定義は升目の表と `covers` だけに当て、場面の入力・正解・採点・比較の表のセルを変えない。

(このファイルの §8「リードに聞くこと」に次を上げ、答えが来るまで直しの段に進まないと書いた。
1. 29 を字のまま当てると、時計・通知・取消の通知の升目はどの場面の入力にも無いので全部「測っていない」になり、入力の約定(adapter が代えた場合は足)が、宣言した (v, x) と組になって足される。
2. どの記録(`survey_results/` か、周の materials の新実装・当方の現状の記録か)を使い、表をどこ(DEFINITIONS.md か materials か)で作るか。凍結した正の定義 C の「場面の定義と升目の軸から機械で作り」と食い違い、L-435 の指紋による再利用にも響く。

§8 の 3 は、候補 35 の権限の分類器の拒否を独立の項目として置いた。

実測で分かったこと: 今の runner は、対象に入った型を `type_plan` の場面の `types_1` の欄にしか残していない(出力 <S>item0_r12-1_scenekeeper_def3_records.txt)。このため直しの段では、この記録を作る機構を足す(§6 の 1)。

批評家の試験 test_i0r11_covers_within_scene_input.py の神託は作りの手本に基づいていて、29 と違う。場面集の規則 8 のとおり、この試験は変えない(§6 の 5)。

<S> = /tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/r12-1/。

場面集の試験は 78 passed(<S>item0_r12-1_scenekeeper_def3_pytest.txt)。変えたのは、このファイルと、行・語の判断の tsv の 2 本だけ。)

## 監査役(定義):0#r12-1-3(agent ac98dcfe8142e7755)

- [止める](repeat_of i0-r11-02) tests/bt/battery/item_0/ROOTCAUSE_r12-1.md:66(§2.4 根11「今、runnerは、対象に入った型を`type_plan`の場面の`types_1`の欄にしか残していない」)/74(§3 定義「scenes.pyの手書きの宣言(...)も…使わない」)/94(§5「同じ根の探し」が挙げる形は「手書きのcoversの事象の値の全部」と「type_planの作りの手本の全部」の2つだけ) — 根11は type_plan 以外の場面には対象ごとの型の実測記録が無いと明記する。ところが定義の妥当性を示す証拠として本文が繰り返し引用する `<S>item0_r12-1_scenekeeper_def3_readings.py`(27-33 行)は、`type_plan is None` かつ `any_type=False` の場面(p1-one-call-per-event・p3-trade・p3-book_snapshot・p3-book_delta・p3-bar・p3-funding・p3-liquidation・p4-visible-at-step・p4-future-read-attempt・p5-same-stream-order 等。`<S>item0_r12-1_scenekeeper_def3_records.txt` でこれらは全レコード `types_1={'null': 53}` = 実測の型情報が皆無)について、CSV の記録行ではなく `s.input`(=scenes.py の静的な宣言。`by = {s.id: s for s in scenes.SCENES}` から取る)を「types known handed … (from records)」として計算し、`<S>item0_r12-1_scenekeeper_def3_readings.txt` に p3-trade: ['約定']・p1-one-call-per-event: ['足'] 等の非空の値を出している。これは §3 の禁止(「scenes.py の手書きの宣言…使わない」)に正面から反し、族は i0-r11-02・dr12-1-2-1 と同じ(走った記録の代わりに書いた物から升目を出す)。この宣言由来の値だけで、本文が §3 の妥当性の根拠に挙げる「letter of item 29 on known records: 17」セルのうち少なくとも 7 セル(P0-3 の 6・P0-4 の 1。readings.txt 21-53 行から算出)が成立しており、根11 の記述(記録が無い)と引用した出力(非空の値がある)が本文中で矛盾したまま提出されている。§2.4 も §4 の対応表も §5 の同根探索も、この第3の形(type_plan 以外の固定型の場面での宣言依存)を族の一員として名指していない。この定義は現状のまま監査を通せる正の規則か、それとも証拠そのものが定義の禁止条項に違反した方法で作られている状態を見落としているか。
- [聞く](repeat_of dr12-1-2-2) tests/bt/battery/item_0/ROOTCAUSE_r12-1.md:74(§3「型を対象かadapterが選ぶ場面は、走った設定つき対象ごとに実際に入った型だけを数え」)/80(§4 表 1 行目「型を対象が選ぶ場面の数え方…は29の文のとおり」) — LEAD_DESIGN.md §8.6 の 29(round_7/LEAD_DESIGN.md:135)の逐語は「型を対象が選ぶ場面は、走った対象ごとに実際に入った型だけを数える」であり、「adapter が選ぶ」という主体は 29 の文に無い。§3 はこの主体を「対象かadapter」に広げているが、§4 の対応表はこの広げを 29 と食い違う変更として挙げず(dr12-1-2-1 の「type_planの作りの手本」の除去だけを挙げる)、「29の文のとおり」と読める書き方のまま通している。根9(§2.4)は「型を対象かadapterが選ぶ場面(type_plan・any_type・型の欄の無い事象)」と述べて対象の外延を広げる理由を書いているが、これが 29 の一般文(升目 (e,v,x) を『場面にした』と数えるのは…型 e の事象が入力にあり…のとき)の単なる敷衍であって狭め・広げのどちらでもないという判断は場面係が独自にしたものであり、dr12-1-2-2 が指摘した『固定した文の字面を超える読みを、聞かずに定義側で確定した』のと同じ形に見える。§8 の『リードに聞くこと』にこの論点は挙がっていない。この拡張は 29 の一般文から機械的に導けるものとして扱ってよいか、それとも聞く候補に挙げるべき解釈の分岐か。


### 作業者 `作る:0#12` の報告(逐語の全文は `round_12/REPORT.md`。ここには「リードに聞くこと」)

## リードに聞くこと

- §8.6 の 31「外の class の属性(__module__・__name__ を含む)を読まない」の読み方を確かめたい。この周の作りでは、断りの文と result().models の型の名前を、__qualname__ は type の C の欄から、__module__ は class の辞書を反復して取る。どちらも検索も普通の読みもせず、外のコードは走らない(格子 1 の dict とメタクラスの置き場所で確かめた)。文字どおり「読まない」にすると、型の名前を文に書けなくなる。その場合、契約 type_decisions の『naming the real type in full』と、第 11 周の格子 1 の神託『文に実際の型の名前がある』を変える必要がある。この読みでよいか、決めてほしい
- §8.6 の 31 の「落とした事実の array は戦略に buffer を出さない = memoryview を作れない型か、写しを渡す」について。この周は第 3 の形を取った。核は戦略に渡した配列を二度と変えず、落とすたびに新しい小さな配列を戦略の側の list に足すだけにした。まとめる操作は戦略の読み出しの中で行い、まとめる先が固定されていれば新しい配列を作る。採らなかった理由は 2 つ。int の list は 88.2 バイト/件(実測、<W>/item0_r12_worker_fact_bytes.out)で、契約の 16 バイトの 5 倍を超える。呼び出しごとの写しは件数に比例して遅くなる(§7.4 の 19)。この形でよいか、決めてほしい
- 振る舞いの変化が 3 つある。(a) 差し込み口の数の答えのうち、Python で書いた数の class(数の塔に登録や派生したもの)を入口の誤りで断る(numpy の数は受ける)。(b) 約定模型と口座の Sequence の答えを list か tuple に限る(生成器などは断る)。(c) 出口の箱の値で numpy の数を受ける。3 つとも契約 core-14 に書いた。別に周知する必要があるか
- shown の列(台帳へまだ反映していない見え方)は、戦略が口を呼ぶまで伸びる。上限は注文の変化の数で決まる。契約 ownership に書いた。上限を付けるかは、項目 12・13 の要件を固定するときに決めてよいか
- (独立の項目)起動文 (3) の候補 35 の権限の分類器の拒否は、場面係と監査役あての項目なので、作業者は扱っていない
- i0-r11-02(場面集の covers)の批評家の試験 13 件は、この周の終わりの作業木でも落ちたままである。場面係が同時に直している最中と読み、作業者は変えていない

## この周で変えた構造

(1) 外の者(戦略・差し込み口・入力の流れ)の呼び出しの外では、核が外の物について行う判断を、同一性(is)と静的な C の型だけで決まる操作に限った。外の class をハッシュしない、== で比べない、検索しない、普通の読み方で属性を読まない(IdTable・is_one_of・derives、class_parts は辞書を反復して読む)。答えは settle / take_int / take_float / take_items で取り、真偽・長さ・反復・変換を答えの物には聞かない。運び手は欄を settle してから作り直す。(2) 核が戦略の側へ書くのは、自分が作った list への list.append だけにした。台帳の dict と落とした事実の配列は、戦略自身の呼び出しの中で、その list をもとに更新する(api._bring_up、history.read_dropped)。


## リードの戻しの処置

根本原因の読みと設計の直しは `docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/round_7/LEAD_DESIGN.md` §9(§9.1 = 実測の時系列と根本原因 3 つ(どれもリードの側)、§9.2 = 正の定義 F・記録の欄・covers_of・台本と手順の直し・候補 35 の試行の記録、§9.3 = 作業者の問いへの答え)。手順の直しは委任文 `docs/DATA/delegations/20260923_backtest_env_prompt.md`(版 40365240c384)の §0 の行と §3「場面集」の段落、台本 `scripts/workflows/backtest_env.js`(`lead_definitions` / `VERSION_RULE`)。監査 52 回目の記録は `2026-09-23_backtest_env_prompt.md`。

### 候補 35 の試行(§8.5 の 25。リードが 2026-09-24 22:50〜22:51 UTC に実行。コマンドと出力)

```
# C = <S>/venvs/item_0/_dl/c35 (clone 794fa647), S = <scratchpad>/c35_trial
rm -rf $S; mkdir -p $S && cp -r $C/. $S/ && mkdir -p $S/src && for f in "$S"/src\ *.py; do b=$(basename "$f"); mv "$f" "$S/src/${b#src }"; done; ls $S $S/src
  -> src/: __init__.py execution.py impact.py metrics.py models.py simulator.py strategies.py visualization.py
python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt   -> pip rc=1 (requirements.txt は Markdown の囲みつき: 先頭行 '`requirements.txt`' と '```text')
rm -rf .venv && python3 -m venv --system-site-packages .venv && .venv/bin/pip install --no-cache-dir -q matplotlib   -> pip rc=0
MPLBACKEND=Agg timeout 600 .venv/bin/python main.py   -> run rc=1, FileExistsError: [Errno 17] File exists: 'outputs' (公開の版の 'outputs' は 1,139 バイトのファイル)
mv outputs outputs_file_as_published.txt && MPLBACKEND=Agg timeout 600 .venv/bin/python main.py   -> run rc=0
============================================================
OPTIMAL EXECUTION & MARKET IMPACT SIMULATOR
============================================================

Initial Price      : 100.00
Order Quantity     : 100,000
Execution Horizon  : 1.00
Time Steps         : 20
Monte Carlo Paths   : 5000

Strategy Results
------------------------------------------------------------

TWAP
Mean Cost                : 52496075.8166
Cost Std                 : 625606.6286
Cost / Share             : 524.960758
Implementation Shortfall : 52496075.8166
Cost (bps)               : 52496.0758

Front-Loaded
Mean Cost                : 53279733.9190
Cost Std                 : 498283.8779
Cost / Share             : 532.797339
Implementation Shortfall : 53279733.9190
Cost (bps)               : 53279.7339

Optimal
Mean Cost                : 52496198.5979
Cost Std                 : 624384.3775
Cost / Share             : 524.961986
Implementation Shortfall : 52496198.5979
Cost (bps)               : 52496.1986

============================================================
Experiment completed successfully.
============================================================

Generated files:
  - outputs/cost_distribution.png
  - outputs/cost_risk_frontier.csv
  - outputs/cost_risk_frontier.png
  - outputs/execution_summary.csv
  - outputs/execution_trajectories.png
```

生成物: outputs/cost_distribution.png(35,065 B)・cost_risk_frontier.csv(307 B)・cost_risk_frontier.png(53,723 B)・execution_summary.csv(361 B)・execution_trajectories.png(68,723 B)。置き換えの操作(ファイルの移動)は権限の分類器に止められなかった。
