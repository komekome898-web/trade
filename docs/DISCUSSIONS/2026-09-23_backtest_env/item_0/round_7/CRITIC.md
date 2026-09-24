# 項目 0「核」第 7 周 — 批評家の記録

委任文: `docs/DATA/delegations/20260923_backtest_env_prompt.md`。起動文の指紋 `4c4cfc6e4052` と作業木の版は同じ(`sha256sum … | cut -c1-12` → `4c4cfc6e4052`)。全 162 行を読んだ。
合意した完了の形(委任文 §0 の逐語): 「**すべてが調査結果以上の信頼性と再現性に優れたものにすること。**」
手元に置いたもの: 固定した要件 `docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/REQUIREMENTS.md`(P0-1〜P0-7 と §3 調査結果の側の行)、場面集 `tests/bt/battery/item_0/DEFINITIONS.md`(`python3 gen_definitions.py --check` → `OK`)、検討表 `tests/bt/battery/item_0/opponents/CONSIDERED.md`(`python3 scripts/check_bt_considered.py …` → `OK 誤り 0 件`)、作業者の `round_7/ROOTCAUSE.md`、場面係の `tests/bt/battery/item_0/ROOTCAUSE_r7-1.md`、この周の表 `round_7/表_*.md` と `materials/`(`survey_best.tsv`・`md5sum_pairs.txt`)。
一時ファイル: `/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/item0_r7_critic_*`(以下 `<S>`)。

## 0. 構造の変化(前の周から)

あり。
- 履歴の答え: 第 6 周の `_EndsAtNewest`・`_check_bound`(答えの事実 1 つ)は消え(`grep -c "_EndsAtNewest\|_check_bound\b" src/bot/bt/core/window.py` → `0`、第 6 周のコミット `c2cbc41` の版では `4`)、`AnswerPlace(first, step, delivered, dropped)` と、名指した位置を読み出しの列の位置 `u = first + q*step` に戻して誤りを選ぶ `_outside` になった(`window.py` 61-80・166-229 行、`api.py` 554-601 行)。
- 送り手の値: `values.is_a`(`issubclass(type(x), C)`)と 1 つの決まり `_plain_scalar` / `scalar`(`values.py` 97-165 行。`c2cbc41` の版には `is_a` が無い)。
- 場面集: 型を測らない観点の場面の型を対象の p3 の結果から runner が作る(`scenes.py` 140-176・546-558 行、`run_battery.py` 600-686 行)。LEAN の再現に `IsInternalFeed`・購読の並べ替え・`Slice.AllData`(`repro_engines/lean52.py` 133-335 行)。

## 1. 前の周までの指摘を自分で確かめ直した結果

コマンド(この周の試験を足す前): `PYTHONPATH=src timeout 600 python -m pytest -p no:cacheprovider tests/bt/critic/item_0 tests/bt/item_0` → `1 failed, 865 passed, 2 skipped in 80.77s`(`<S>/item0_r7_critic_pytest_core.log`)。落ちたのは下の 1.1 の 1 件だけ。

### 1.1 批評家の試験の誤り(場面集の規則 8)

- `test_i0r2_battery_p5_grading.py::test_single_input_form_of_hand_over_order_agrees_with_keeping_one_input_in_order`: 場面係が `ROOTCAUSE_r7-1.md` 127 行で「試験自身の誤り」と報告した。**確かめた結果、試験自身の誤り。**試験の `_event`(64-72 行)は約定・足・資金調達だけを型ごとに作り、ほかは全部清算として作る。第 r7-1 回から定義に載る p5 の入力は 6 種を持つ対象の例(約定・板の写真・板の差分・足)なので、板の写真で `KeyError: 'price'` になる(出力は `<S>/item0_r7_critic_pytest_core.log`)。確かめたい性質(1 本の入力の順を守る対象は、その形の規則で正解と一致、型の固定の順で並べ直す対象は不一致)は型に依らない。**直した**: 場面を `scenes.for_target_types(…, ["trade", "bar", "funding", "liquidation"])` で `_event` が作れる 4 種の対象の場面にし、渡す順が 24 通りであることを確かめる行を足した。消した主張は無い。結果 `2 passed`。

### 1.2 前の周の指摘

| id | 確かめ方 | 結果 |
|---|---|---|
| i0-r6-01(過去で終わる答えの先を名指すと「届いた」と言う) | 第 6 周の試験 `test_i0r6_past_answer_names_undelivered.py` → 通る。第 6 周の試し `<S>/item0_r6_critic_probe_answer_kind.py` を打ち直した(`…answer_kind.r7recheck.out`): `until day 6 (7 bars) [12]: … -> FuturePositionError(LookAheadError)`、`all[0:6:3] -> (0,3) [4]: … -> FuturePositionError(LookAheadError)`。さらに入力から決める独立の神託(`<S>/item0_r7_critic_probe_kind_oracle_keptcoords.py`。戦略が自分で受けた列と history.py の保持の規則を自分で模して、名指した位置を「届いた・保持・落とした・何も無い・まだ」に分ける。型・全部・`until_ns`・`since_ns`・`n`・`history_limit` 1〜3・区間の区間 2 段まで・添字は答えの外の前後 6 位置ずつ)を 6 つの種で打った: `seed 1 checked 3648 wrong 0` 〜 `seed 6 checked 3684 wrong 0` | **添字と非負の区間の境界は直った。**負の区間の境界は名指した位置で決めておらず、後ろ向きの答えで先読みが素通りする → **i0-r7-01** |
| i0-r6-03(偽る物・numpy の真偽の断り方) | 第 6 周の試し `<S>/item0_r6_critic_probe_values.py` を打ち直した(`…values.r7recheck.out`): `size=Spoof(float) REFUSED bot.bt.core.errors.OrderApiError`、`Fill.price=Spoof(float) REFUSED bot.bt.core.errors.VenueProtocolError`、`post_only=np.bool_ ACCEPTED`。作業者の試し `item0_r7_worker_probe_senders.py` も打ち直した(`<S>/item0_r7_critic_recheck_worker_senders.out`、54 行、`WRONG-TYPE` 0 件) | 直った |
| i0-r5-01(路を渡る物が値でない) | 第 5 周の試験が通る。**ただし `Fraction` は同じ物のまま路を渡り、送り手が後の呼び出しから書き換えられる** → **i0-r7-02**(同じ根) | 同じ根が残る |
| i0-r5-02(Basana に無い型を adapter の class で運んだ) | `opponents/basana_adapter.py` 44-46・104-105 行: 足 `basana.core.bar.BarEvent`・約定 `basana.external.bitstamp.trades.TradeEvent`・板 `PartialOrderBookEvent`・`OrderBookDiffEvent`(配布物の class)。p3-funding の最良は 52 LEAN の再現(下の確かめ) | 直った |
| i0-r5-03(hftbacktest の p4 の名指し) | 名指しの一覧は `scenes.py` 70-78 行に固定、runner がそろいを検める(`DEFINITIONS.md` の p4-future-read-attempt の `graded_from`) | 直った |
| i0-r5-04(上位互換の「含む」を Basana の基の class で当てた) | `CONSIDERED.md` 15・29 行が基の class を含む側に引かないと書き、`test_every_scene_a_containment_cites_as_correct_is_correct_in_the_records` が通る | 直った。ただし 15 行の文に第 r7-1 回で古くなった前提が残る → **i0-r7-04** |
| i0-r5-05 | i0-r6-01 に付け直し済み(上) | 上と同じ |
| i0-r6-02(P0-5 が型の欠けで決まる) | 批評家の試験 `test_i0r6_battery_p5_measures_order_not_types.py` → 通る。`survey_results/*.tsv` から場面ごとに正解と一致の対象を数えた: `p5-same-time-twice ['opp_basana']`・`p5-hand-over-order ['opp_basana']`・`p1-merge-by-time ['opp_basana', 'repro_lean52']`。`materials/survey_best.tsv` の P0-5 は 3 場面とも正解と一致 | 直った |
| i0-r6-04(LEAN の再現が IsInternalFeed を落とした) | `repro_engines/lean52.py` 319・322・329 行に 181・194・329 行の条件、注釈 282-311 行に書き直さない条件と理由。**ただし再現が組む購読の組(同じ銘柄に約定の Tick と TradeBar)を利用者が作れる根拠の行が注釈に無く、原文は解像度で片方を選ぶ** → **i0-r7-03**(同じ根) | 同じ根が残る |

### 1.3 そのほか確かめたこと(指摘にしない)

- 試金石: `PYTHONPATH=src python3 mutant.py --check` → `changed scenes: ['p4-received-time']` / `OK`。
- 場面集と批評家の試験(自分の試験を足した後): `PYTHONPATH=src python -m pytest -p no:cacheprovider tests/bt/battery/item_0 tests/bt/critic/item_0` → `5 failed, 124 passed in 79.14s`。落ちた 5 件は全部この周に足した試験(i0-r7-01 の 4 件、i0-r7-02 の 1 件)。
- `tests/bt/` の全部(`setsid nohup env PYTHONPATH=src python -m pytest -p no:cacheprovider tests/bt/ > <S>/pytest_item0_r7_critic.log`)→ `5 failed, 924 passed, 2 skipped in 87.43s`。落ちたのは同じ 5 件だけ。
- 戦略の文脈から辿れる物: `gc.get_referents` で文脈から辿れる物を全部歩いた(`<S>/item0_r7_critic_probe_reach_future.py`、31 個)。まだ届いていない事象と engine は 0 件。呼び手のフレーム(`sys._getframe(1)`)からは engine に届く(`<S>/item0_r7_critic_probe_frame.py` → `caller frame self: CoreEngine`)が、核の文書 `api.py` 28-31 行・`contract.py` 73 行・`engine.py` 49 行がこの限界を書いている。
- 通知の遅れの間の注文の見え方: 通知の遅れ 5 秒で、約定の知らせが届く前の呼び出しでは `filled_size 0.0`・未決 1 件、届いた後に `1.0`・0 件(`<S>/item0_r7_critic_probe_notice_latency_view.py`)。核は正しい。場面集は測っていない → **i0-r7-05**。
- 資料係の表: `round_7/表_*.md` の調査結果の側は 31 / 32(p3-mixed-one-run だけ正解と一致でない)。`materials/md5sum_pairs.txt` に組ごとの md5 がある。

## 2. 指摘

### i0-r7-01 [止める] 実装(同じ原因: i0-r6-01)

**後ろ向きの答えの負の区間の境界が、まだ届いていない位置だけを名指しても、黙って空を返す。**
`window.py` の `POSITION_RULE` の説明(40-43 行)と `contract.py` 45-47 行は「負の区間の境界は最新から数え、tuple と同じく答えの端で切る(切り詰めは答えの中にしか届かない)」と言う。これは配達順の答えでだけ正しい。後ろ向きの答え(`ans[::-1]`、`place.step == -1`、新しい順)では負の境界は**最も古い側から**数え、位置 -1 は `r[0]`(最新)より新しい側 = まだ届いていない事象である。第 7 周の直しは負の**添字**を名指した位置で決める規則に入れた(`r[-5]` → `FuturePositionError`)が、負の**区間の境界**は符号だけで切り詰める(`_check_bounds` は `b >= 0` の境界しか見ない、`window.py` 178-185 行。切り詰めは 169 行の `tuple.__getitem__`)。そのため:

```
PYTHONPATH=src python3 <S>/item0_r7_critic_probe_backward_negslice.py   (日足 6 本、4 本目の呼び出し。a = visible_events(BAR)、r = a[::-1])
a[4:6] -> FuturePositionError
r[-5] -> FuturePositionError
r[-6:-5] -> returned []        (名指すのは r の位置 -2・-1 = 最新より 2 つ・1 つ先。どちらもまだ届いていない)
r[-6:-4] -> returned []
r[-5::-1] -> returned []       (最新の 1 つ先から古い向き)
r[-6:-5:-1] -> returned []
```

前向きの鏡像 `a[4:5]` は `FuturePositionError` で止まるのに、同じ未来を後ろ向きの答えで名指すと空の答えで素通りする。固定した要件 P0-4 の測り方「戦略側から未来時刻の事象を読もうとするコードが、実行時エラーか型エラーで止まるか(素通りしたら不合格)」、場面の正解「空の結果・切り詰めた結果…は素通りで、正解ではない」に当たる。値は漏れないが、先読みの誤りが捕まらない。作業者は根本原因 A-2 で「負の添字は規則の外に置いていた」を直し、変える構造 2 で「負の区間の境界が切り詰められる決まり(tuple と同じ)も変えない(切り詰めは答えの中にしか届かない)」と書いたが、後ろ向きの答えでは切り詰めた先が未来になることを確かめていない。作業者の神託の試験も負の区間の境界を試していない(同じ根の全箇所を探していない)。
試験: `tests/bt/critic/item_0/test_i0r7_backward_answer_negative_bounds.py` → `4 failed`(`r[-6:-5]`・`r[-6:-4]`・`r[-5::-1]`・`r[-6:-5:-1]`)。
(前向きの答えの負の区間の境界が答えより古い側で切られ、黙って空・短い答えになる形 `a[-6:-5] -> []` は、docstring の「黙って短くした答えを返さない」とも食い違うが、名指すのは過去なので、この指摘の [止める] の根拠には入れない。直すときに同じ規則で扱うかは作業者が決めて書くこと。)

### i0-r7-02 [止める] 実装(同じ原因: i0-r5-01)

**`OrderRequest.extra` の `Fraction` は同じ物のまま路を渡り、送り手が後の呼び出しから書き換えると、取引所は着いた時刻に書き換えた値を読む。**
`values.py` 64-66 行の `_SCALARS` は `Fraction` を「組み込みの不変の値」の組に入れ、`_plain_scalar`(140 行)は同じ物を返す。`fractions.Fraction` は Python で書かれた class で、`__slots__ = ('_numerator', '_denominator')` は代入できる。モジュールの説明(values.py 1-18 行)の決まり「路を渡る物は送り手の変わりうる状態を持たない」を破る。

```
PYTHONPATH=src python3 <S>/item0_r7_critic_probe_frozen_private.py
strategy holds request 139718587063472 extra d type FrozenDict
venue saw at 1700000010000000000 request 139718587063584 extra {'d': {'a': 1}, 'f': Fraction(7, 3)}
```

(戦略は T0 に `extra=(("d", {"a": 1}), ("f", Fraction(1, 3)))` で送り、注文の遅れは 10 秒、T0+1 秒の呼び出しで手元の物に `._map["a"] = 999` と `._numerator = 7` を書いた。取引所が受けた注文は別の物で、`FrozenDict` は作り直されていて `{'a': 1}` のまま。`Fraction` だけが同じ物で `7/3` になった。)
信頼性を崩す(路の遅れを飛ばす道。i0-r4-02・i0-r5-01 と同じ根)。第 7 周の作業者の根本原因 B は「本当の型で判定する」を直したが、「その型の値が本当に不変か」を `_SCALARS` の全部について確かめていない。`Fraction` の子は数の塔の `numbers.Real` として `float` に直すのに、`Fraction` そのものは直さずに持つという食い違いもある。
試験: `tests/bt/critic/item_0/test_i0r7_fraction_in_extra_stays_live.py` → `1 failed`(`Fraction(999, 3) == Fraction(1, 3)` が偽)。

### i0-r7-03 [直す] 場面集(同じ原因: i0-r6-04)

**LEAN の再現は、同じ銘柄に約定の `Tick` の購読と `TradeBar` の購読を同時に持たせるが、利用者がこの組を作れる根拠の行が注釈に無い。原文は解像度で片方だけを選ぶ。**
`opponents/repro_lean52.py` 89-115 行の `_sources` は、場面の事象の型ごとに `lean52.data_manager_add(SYM, CryptoFuture, [(t, TickType)])` で購読を 1 つずつ作る(約定 → `Tick`、足 → `TradeBar`、資金調達 → `MarginInterestRate`)。注釈は「利用者の CryptoFuture は `AddCryptoFuture` → `AddSecurity<T>` で足す」(`repro_engines/lean52.py` 150-163 行)と書くが、その経路では型は `LookupSubscriptionConfigDataTypes` が解像度から決める: 場面係がこの周に取った原文 `<S>/item0_r7-1_scenekeeper_DataManager.cs` 626 行 `dataTypes = LookupSubscriptionConfigDataTypes(symbol.SecurityType, resolution ?? …)`、747-773 行(768 行 `LeanData.GetDataType(resolution, tickType)`)。つまり 1 回の追加では、約定の型は `Tick`(解像度 Tick)か `TradeBar`(それ以外)の片方で、両方は出ない。両方を持つには別の解像度でもう 1 度足すなどの経路が要り、その経路と、そのとき 2 つの購読がどう並ぶかは注釈に無い。この組は p1-typed-events・p1-merge-by-time の再現の結果(正解と一致)を決めている(`survey_results/repro_lean52.tsv`)。委任文 §3「再現の根拠は…注釈に 1 対 1 で書く。一次資料に無い工夫を足さない」に当たる。調査結果の側を強くする向きで、この 2 場面の最良は Basana も正解と一致(`materials/survey_best.tsv`)なので表は変わらない。よって [直す]。直し方は、組を作る利用者の経路を原文の行で示すか、示せなければ解像度ごとに片方の型だけで走らせる(取りうる値を 2 つ以上走らせる規則)こと。

### i0-r7-04 [直す] 場面集

**検討表の共通の決まりの文(`opponents/CONSIDERED.md` 15 行)に、第 r7-1 回で成り立たなくなった前提が残る。**
「場面が含む側の候補に無い型を入力に持つため場面の結果が対応なしのとき(p1-merge-by-time・p5-same-time-twice・p5-hand-over-order は資金調達か清算を含む)は…試しの記録(`survey_results/attempts/<番号>.log`)を引く」。第 r7-1 回から、この 3 場面の型は対象の型から runner が作り、資金調達・清算を必ず含むことはない(`scenes.py` 182-201・403-419 行、`DEFINITIONS.md` 12 行)。場面係の `ROOTCAUSE_r7-1.md` 47・111 行は P0-1・P0-5 の冒頭の文と 11 の行を直したと書くが、この共通の文は直していない(同じ根の全箇所の探し漏れ)。読む監査役・批評家に、今の場面の作りと違う決まりを示す。

### i0-r7-05 [直す] 場面集

**「受け取れた時刻 ≤ 今」を、注文の通知について測る場面が無い。**
固定した要件 §1 の行は「戦略は「受け取れた時刻 ≤ 今」の事象しか見られない」で、事象の型に注文の受付/拒否/約定の通知を含む。場面集の P0-4 の 3 場面は市場の事象(足・約定)だけを使い、p4-received-time が受け取りの遅れを測るのも市場の事象だけ。通知の遅れがあるときに、通知が届く前の呼び出しで戦略が注文の見え方(約定済みの数量・未決の数)から取引所の出来事を読めてしまう対象は、今の場面集では見分けられない(P0-6 の場面は遅れ 0 の既定で測る)。新実装はこれを正しく扱う(上の 1.3)。P0-4 の固定した測り方(先読みの呼び出しが止まるか)の外なので [直す] に留める。

### i0-r7-06 [示唆] 場面集

p4-future-read-attempt は、過去を読む手段を持たない対象に、存在しない引数で書いた呼び出し(形 no_means)の `TypeError` で正解と一致を与える(`survey_results/opp_basana.tsv`: `exchange.get_bid_ask(pair, 5 本目の時刻) … TypeError: … takes 2 positional arguments but 3 were given`)。調査結果の側の P0-4 の行は、場面ごとに最良を寄せるので、過去を読める対象の p4-visible-at-step と、過去を読めない対象の p4-future-read-attempt が 1 行に並び、「過去を読めて未来の読み出しは止まる」対象が調査結果の側に 1 つもなくても 3 / 3 になる。新実装に不利な向きなので害は無いが、審査員が読む表の P0-4 の意味を、定義の注記に 1 文書いておくとよい。

## 3. 提出前の吟味(批評家の文)

- 指摘ごとに根拠を自分で再現した: i0-r7-01 は試しの出力と試験 4 件の失敗、i0-r7-02 は試しの出力と試験 1 件の失敗、i0-r7-03 は原文の行(DataManager.cs 626・747-773・768)と `repro_lean52.py` 89-115 行、i0-r7-04 は `grep -n "資金調達か清算" opponents/CONSIDERED.md` → 15 行、i0-r7-05 は `DEFINITIONS.md` の P0-4 の 3 場面の入力と `<S>/item0_r7_critic_probe_notice_latency_view.py` の出力。
- 格付け: i0-r7-01 は要件 P0-4 の測り方と場面の正解に合わない振る舞い(素通り)なので [止める]。i0-r7-02 は路を渡る値が送り手の状態のまま残り、信頼性を崩すので [止める]。i0-r7-03 は注釈の 1 対 1 の抜けで、調査結果の側を強くする向き・表を変えないので [直す](前の周の i0-r6-04 と同じ格)。i0-r7-04 は文の古さで要件・正解に響かないので [直す]。i0-r7-05 は固定した測り方の外の抜けなので [直す]。i0-r7-06 は要件の外の改善なので [示唆]。前の周の [直す](i0-r6-03・i0-r6-04)は直ったか、同じ根の残りを上に付けた。
- 場当たりの直しは見つけなかった: 作業者の第 7 周の直しは答えの場所と 1 つの値の決まりという作りの変更で、試験だけの分岐・閾値のずらしは無い(`grep -n -i "battery\|pytest\|scene" src/bot/bt/core/*.py` → `contract.py:4` と `testing.py:5` の説明文の 2 行だけで、分岐は無い)。場面係の直しも対象の名前を見る分岐は無い(`run_battery.py` 632-649 行は `type_plan` の有無だけを見る)。
- 相手の付け違い: i0-r7-01・i0-r7-02 は `src/bot/bt/core/` の振る舞いなので実装。i0-r7-03〜06 は `tests/bt/battery/item_0/` の再現・検討表・場面なので場面集。
- 試験の置き場所: この周に足した試験は `tests/bt/critic/item_0/test_i0r7_backward_answer_negative_bounds.py`・`test_i0r7_fraction_in_extra_stays_live.py`。直した試験は `test_i0r2_battery_p5_grading.py`(1.1)。
