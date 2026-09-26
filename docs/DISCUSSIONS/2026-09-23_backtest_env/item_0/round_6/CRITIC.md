# 項目 0「核」第 6 周 — 批評家の記録

委任文: `docs/DATA/delegations/20260923_backtest_env_prompt.md`。起動文の指紋 `4c4cfc6e4052` と作業木の版は同じ(`sha256sum … | cut -c1-12` → `4c4cfc6e4052`)。全 162 行を読んだ。
合意した完了の形(委任文 §0 の逐語): 「**すべてが調査結果以上の信頼性と再現性に優れたものにすること。**」
手元に置いたもの: 固定した要件 `docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/REQUIREMENTS.md`、場面集 `tests/bt/battery/item_0/DEFINITIONS.md`(32 場面)、検討表 `tests/bt/battery/item_0/opponents/CONSIDERED.md`(`python3 scripts/check_bt_considered.py …` → `OK 誤り 0 件`)、作業者の `round_6/ROOTCAUSE.md`、場面係の `tests/bt/battery/item_0/ROOTCAUSE_r6-1.md`〜`r6-3.md`、この周の表 `round_6/表_*.md` と `materials/`(`mapping.tsv`・`survey_best.tsv`・`md5sum_pairs.txt`)。一時ファイルは `/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/item0_r6_critic_*`。

## 0. 構造の変化(前の周から)

あり。`git diff --stat 46d79d3 -- src/bot/bt/core tests/bt/item_0` → 16 ファイル、1,378 行追加 217 行削除。作業者の申告の 3 点を実物で確かめた。
- (1) 値の部品: `values.py` の `as_text`・`as_float`・`as_int`・`as_flag`・`as_choice`・`scalar`・`freeze`。運び手 `contract.py` の `PATH_CARRIERS`(`OrderRequest`・`CancelRequest`・5 つの報告・`FillNotice`・12 の事象型)は全部 `slots` の凍結データクラスで、欄は作る時に上の関数を通る(`api.py` の `OrderRequest.__post_init__`、`interfaces.py` の `_make_fields`、`events.py` の `_value`)。
- (2) 路の入口: `api.py` の `fresh_request`(`type(x) is cls` を求めて作り直す)を `_OrderPort.place`・`cancel` と `engine.py` の `_force` が使う。データ源は `engine.py` の `_SourceMerger._pull` が `type(event) is EVENT_TYPE_TO_CLASS[etype]` を求める。差し込み口の答えは `_check_delay`・`as_float(fee)`・`as_text(reason)`・流れの名前の `as_text`。
- (3) 履歴の答え: `window.py` の `DeliveredEvents` と子 `_EndsAtNewest`・`_EndsInPast`、`_check_bound` が事実から `FuturePositionError` / `OutsideAnswerError` を選ぶ。`api.py` の `visible_events` が `ends_at_newest = hi == len(events)` で事実を決める。

## 1. 前の周までの指摘を自分で確かめ直した結果

コマンド: `PYTHONPATH=src timeout 600 python3 -m pytest -p no:cacheprovider tests/bt/critic/item_0 tests/bt/item_0 tests/bt/battery/item_0` → この周の試験を足す前は `6 failed, 787 passed, 2 skipped in 69.86s`。落ちたのは下の 1.1 の 6 件だけ。

### 1.1 批評家の試験の誤り(場面集の規則 8)

- `test_i0r5_battery_opponent_grading.py::test_basana_is_not_credited_with_an_event_type_its_adapter_wrote`(6 件): 場面係が `ROOTCAUSE_r6-1.md` の i0-r5-02 の結果の節で「試験自身の誤り」と報告した。**確かめた結果、試験自身の誤り。**60 行の `assert "class Generic(bs.Event)" in adapter` は直す前の adapter の形を前提にしており、指摘どおりその class を消すと、直ったかどうかに関わらず落ちる。また前提の「Basana 1.11 の事象の class は `Event` と `BarEvent` だけ」は `dir(basana)`(最上位の名前だけ)から出したもので、配布物は約定・板の写真・板の差分の class を `basana.external.*` に持つ(場面係の pkgutil の一覧、`ROOTCAUSE_r6-1.md` 89 行)。**直した**: 確かめたい性質を記録から読む形に書き直した。資金調達・清算・6 種を混ぜた回は正解と一致でないこと、約定・板の写真・板の差分は、正解と一致なら記録の carrier の class を定義したファイルが Basana の配布物(`/site-packages/basana/`)にあり場面集の中に無いこと。結果 `9 passed`。消した主張は無い(adapter の class に戻せば carrier の `type_file` が場面集の中になり落ちる)。

### 1.2 前の周の指摘

| id | 確かめ方 | 結果 |
|---|---|---|
| i0-r5-01(路を渡る物が `extra` の外で値でない) | 第 5 周の試験 `test_i0r5_fields_crossing_a_path_stay_live.py` の 4 件が通る。自分で、`__class__` を偽る物(`isinstance` をだます)・numpy のスカラーを全部の運び手の欄に入れた(`scratchpad/bt/item0_r6_critic_probe_values.py`、出力 `…_probe_values.out`)。偽る物は全部断られ、中身が路を渡ることは無い。numpy の数は組み込みの `float`・`int` になる | 直った。断り方の型の抜けは **i0-r6-03** |
| i0-r5-02(Basana に無い型を adapter の class で運んだ) | `grep -n "class .*(bs\.Event)\|class Generic" tests/bt/battery/item_0/opponents/*.py tests/bt/battery/item_0/adapters/*.py` → 0 件。`survey_results/opp_basana.tsv` の p3-funding・p3-liquidation・p3-mixed-one-run は対応なし、p3-trade・p3-book_snapshot・p3-book_delta の carrier は `basana.external.bitstamp.trades.TradeEvent`・`basana.external.binance.order_book_diff.OrderBookDiffEvent` ほか(`type_file` は Basana の配布物、`passed_by` は Basana の dispatcher)。上の 1.1 の試験が通る | 直った |
| i0-r5-03(hftbacktest の p4 が開いた区間を試さない) | 名指し方の一覧は `scenes.py` に固定され、`adapters/common.py` の `try_position_namings`・`try_time_namings` で全 adapter に同じに当たる(新実装の adapter の 410-417 行も同じ部品)。`opp_hftbacktest.tsv` の p4-future-read-attempt は不一致(detail に `[position [n:]] … -> []`) | 直った |
| i0-r5-04(上位互換の「含む」を Basana の基の class で当てた) | 第 5 周の試験 `test_no_superset_skip_rests_on_basanas_generic_event_carrier` が通る。P0-1 の 13 の行・P0-7 の 52 の行を読み、含む側が走った候補の自分の型・口(`DataKind`・aat の取引所の口・gobacktest の `SetPortfolio` ほか)と場面の結果で書かれていることを確かめた | 直った |
| i0-r5-05(過去で切った答えの外で「まだ届いていない」と言う) | 最後の次の位置(`[len]`・`[len:]`)は直った(下の試験の通る 2 件)。**ただし最後の次より先の位置は、答えの事実 1 つで誤りの種類を決めるので、届いていない事象を名指しても「届いた」と言う** → **i0-r6-01**(付け直し: [止める]) | 同じ原因が残る |
| i0-r5-06 [示唆](読み出しの手段を持たない対象が p4 で正解と一致) | 場面係は `shape = no_means` で記録を分けた(`ROOTCAUSE_r6-1.md` 70-72 行)。固定した測り方の範囲なので付け直さない | 答えを確かめた |
| i0-r5-07 [示唆](時計は実行の時刻の範囲の外でも届く) | `contract.py` 100-107 行の `run_settings.time_span_ns` に「入力の事象の 2 つの時刻だけを検める。時計・通知・到着は縛らない」、`engine.py` の `CoreEngine.__init__` の説明にも同じ | 直った |
| i0-r4-*・i0-r3-*・i0-r2-*・i0-r1-* | 前の周までの批評家の試験が全部通る(上のコマンド。1.1 の 6 件を除く) | 直ったまま |

## 2. この周の指摘

### i0-r6-01 [止める] 実装 — 過去で終わる答えの先を名指すと、届いていない事象でも「届いた」と言い、`LookAheadError` にならない(repeat_of: i0-r5-05)

作業者は根本原因 B で「答えが『自分の最後の次に何があるか』という事実を持っていなかった」と書き、答えに事実 `next_is_undelivered` を 1 つ持たせた。誤りの種類はその 1 つで決まる(`window.py` の `_check_bound` は、名指した位置がどこであっても `next_is_undelivered` だけを見る)。しかし事実は**最後の次の 1 位置**のことで、過去で終わる答え(`until_ns` で切った答え、歩幅つきの前向きの区間)の、さらに先の位置は**まだ届いていない事象**を名指しうる。そこでも `OutsideAnswerError`(`LookAheadError` の子ではない)を出し、文は「the events after it were delivered but are outside this answer」と言う。未来を読もうとした名指しが、先読みの誤りの型でなく、しかも「届いた」という誤った事実を書いて返る。

確かめた出力(`scratchpad/bt/item0_r6_critic_probe_answer_kind.py`、日足 12 本、10 本目の呼び出し = 届いたのは 10 本):
```
until day 6 (7 bars) [7]: named reads[7] = delivered -> OutsideAnswerError …
until day 6 (7 bars) [12]: named reads[12] = NOT delivered yet -> OutsideAnswerError: …so the events after it were delivered but are outside this answer…
all[0:6:3] -> (0,3) [4]: named reads[12] = NOT delivered yet -> OutsideAnswerError: …were delivered…
all[::-1] [10]: named reads[-1] = nothing (before the oldest) -> OutsideAnswerError: …were delivered…
```
作業者自身が根本原因 B の 6 に書いた決め方(「名指した位置に『届いた事象』があれば過去」)は、名指した位置で決めると言っている。実装はそうなっていない。作業者の試験はこの穴を見つけられない: `test_the_fact_agrees_with_the_input_at_every_callback` は `ans[len(ans)]` の 1 位置だけを試し、`test_every_index_and_slice_matches_the_probe_oracle` は「最後より先のどの名指しも誤りの種類は答えの事実と同じ」(`assert isinstance(info.value, LookAheadError) is fact`)を正解に置いており、実装の規則をそのまま写している(規則から独立した神託になっていない)。

格付け: 第 5 周の i0-r5-05 は、過去を「まだ届いていない」と言う向き(偽の先読みの報せ)で、値を返さないので [直す] だった。今度は逆向きで、**未来を読もうとした名指しが `LookAheadError` として捕まらない**(先読みの見落とし)。核は `LookAheadError` の系統で先読みの試みを他の誤りと分ける契約を持ち(`contract.py` の `visibility`)、そこに誤った型と誤った事実の文を返すのは、先読みの構造的な検出(P0-4 の側面)の信頼性を崩す。さらに作業者が前の周の指摘の直しとして「同じ根の全箇所」を直していない(委任文 §3「提出前の吟味」(2))。迷うので重い方(委任文 §3「批評家」)に付ける。patchwork とはしない(事実を答えに持たせる作りは構造の変更で、欠けは範囲の不足)。

批評家の試験 `tests/bt/critic/item_0/test_i0r6_past_answer_names_undelivered.py` の 6 件のうち 4 件が落ちる(`4 failed, 2 passed`)。通る 2 件は「届いた位置は `LookAheadError` でない」側で、第 5 周の直りを守る。

### i0-r6-02 [止める] 場面集 — P0-5 の 2 場面は、調査結果の側を「清算・資金調達の型が無い」ことで対応なしにしており、P0-5 ではなく P0-3 を測っている

固定した要件 P0-5 の測り方は「同時刻に**複数型**の事象を仕込んだ入力を作り、規則どおりの順で処理されるか」。p5-same-time-twice と p5-hand-over-order は約定・足・資金調達・清算の 4 型を同じ時刻に置く(`DEFINITIONS.md` 205-219 行)。走った候補と再現した候補に、この 4 型を全部持つものは無い(`survey_results/*.tsv` の p3-<型> で全部が正解と一致の対象は 0 件)。よって調査結果の側の最良は 2 場面とも「対応なし」で、それは P0-5 の並びの規則ではなく、P0-3 がすでに測っている型の欠け(p3-funding・p3-liquidation・p3-mixed-one-run)で決まっている。

場面係自身の試し(`tests/bt/battery/item_0/survey_results/attempts/1.log` 12-21 行、probe r6-1)は、同じ入力を Basana の持つ型(約定と足)だけにすると `P5 hand_over ['trades', 'bars'] … FOLLOWS True`・`P5 hand_over ['bars', 'trades'] … FOLLOWS True`・`P5 distinct_orders_over_hand_overs 1` で、並びの規則を満たすことを示している。ところが表(`round_6/表_oh7l5v.md` と `表_1s1zhl.md`)は P0-5 を新実装 3 / 3、調査結果の側 1 / 3 と出す。調査結果の組の 32 場面で違うセルは 3 つだけ(`materials/survey_best.tsv`: p3-mixed-one-run・p5-same-time-twice・p5-hand-over-order)で、うち 2 つがこれである。審査員は観点ごとに比べる(場面集の規則 3)ので、記録が示していない「並びの差」を P0-5 の差として読ませる。委任文 §3「場面集」の監査の観点「場面が新実装に有利な範囲に偏っていないか」に当たる。場面係は `ROOTCAUSE_r6-1.md` の提出前の吟味 5 の [判断] でこの形を書き、直し方(対象が持つ型で時刻合わせと同時刻の並びを測る場面を足す)まで挙げたうえで、場面を変えずに残した。

同じ作りは p1-merge-by-time(P0-1。資金調達を含む)にもある。今は再現した LEAN が 3 型を全部持つので最良が正解と一致になり、表には出ていない。P0-5 の要件の文(複数型)は、4 型でなく、対象が持つ 2 型以上で満たせるので、場面を直しても要件を緩めることにはならない。

批評家の試験 `tests/bt/critic/item_0/test_i0r6_battery_p5_measures_order_not_types.py` の 3 件のうち 2 件が落ちる(p5-same-time-twice・p5-hand-over-order。p1-merge-by-time は最良が正解と一致なので通る)。試験の条件: 複数型の場面で調査結果の側の最良が正解と一致でないなら、その場面が入れる型を全部持つ(p3-<型> が全部正解と一致の)調査結果の側の対象が 1 つはあること。

### i0-r6-03 [直す] 実装 — 組み込みの型を偽る物・numpy の真偽は、運び手の誤りの型でなく生の `TypeError` か、誤った文で断られる

`values.py` の `as_text`・`as_float`・`scalar` は `isinstance` で組み込みの型の子かを見てから、組み込みの型の読み出し(`str.__str__`・`float.__float__`)を呼ぶ。`isinstance` は物の `__class__` を読むので、`__class__` を偽る物は子として通り、次の読み出しで生の `TypeError` が出る。値は路を渡らない(断られる)が、`values.py` の説明「anything else … raises `ValueError`; the caller wraps it in its own error type」と、核の契約(注文は `OrderApiError`、報告は `VenueProtocolError`、事象は `EventValidationError`)から外れる。また `post_only=np.bool_(True)` は `OrderApiError: post_only must be a bool, got bool` と断る(numpy の真偽の型の名が `bool` なので、文が「bool を渡して bool でないと言われた」になる)。numpy の数(`np.float64`・`np.int64`)は受けて組み込みの値にするのに、pandas の比較で普通に出る numpy の真偽は断る、という食い違いもある。
確かめた出力(`scratchpad/bt/item0_r6_critic_probe_values.out`):
```
size=Spoof(float) REFUSED builtins.TypeError descriptor '__float__' requires a 'float' object but received a 'Spoof'
Fill.price=Spoof(float) REFUSED builtins.TypeError …
Trade trade_id=Spoof(str) REFUSED builtins.TypeError …
post_only=np.bool_ REFUSED bot.bt.core.errors.OrderApiError post_only must be a bool, got bool
size=np.float64 ACCEPTED type <class 'float'>
```
値を黙って返さず、断ることは保たれているので [直す]。

### i0-r6-04 [直す] 場面集 — LEAN の再現は、書き写した行にある `IsInternalFeed` の条件を落としており、そのことを注釈に書いていない

`opponents/repro_engines/lean52.py` の `time_slice_create` は、注釈で `TimeSliceFactory.cs` の 184 行と 365-372 行を書き直したと言う。場面係が保存した同じ版の原文(`scratchpad/bt/r6-3/item0_r6-3_scenekeeper_TimeSliceFactory.cs`)では、184 行の `allDataForAlgorithm.Add(baseData)` は 181 行の `if (!packet.Configuration.IsInternalFeed)` の中、資金調達の率を `Slice` に入れる 365-372 行は 329 行の `else if ((delisting = baseData as Delisting) != null || !packet.Configuration.IsInternalFeed)` の中にある。つまり LEAN が資金調達の率を `OnData` に渡すのは、その購読が内部の購読でないときだけである。再現はこの条件を持たず、場面の購読が利用者の(内部でない)購読であることも、利用者がどの公開の口でそう購読するかも書いていない。ファイルの冒頭は「Nothing is added to and nothing is weakened from the primary source」と言う。p1-merge-by-time・p3-funding の調査結果の側の最良(正解と一致)は、この再現から来ている(`materials/survey_best.tsv` 2・13 行)。暗号資産の先物の資金調達の購読が既定で内部の購読かは、**私は確かめていない**(この環境では中身を取らない clone しか無く、ネットワークで一次資料を取り直していない)。向きは調査結果の側を強くする向き(新実装が勝ちにくい向き)なので [止める] にはしないが、委任文 §3「再現の根拠は、書き写しの行か一次資料の URL と取得日を、再現のコードの注釈に 1 対 1 で書く」に照らし、落とした条件と、場面の購読が内部でないとする根拠(行)を注釈に書く必要がある。

## 3. 場面集が要件の観点を覆っているか・adapter の公平さ・検討表・再現

- 観点 P0-1〜P0-7 はすべて場面があり、各観点に値の場面が 1 つ以上ある(`DEFINITIONS.md` の見出し)。P0-5 の測り方の偏りが i0-r6-02。
- 新実装の adapter: この周は変わっていない(資料係の `materials/commands.txt` の「git status で差分なし」、`git log -- adapters/new_impl.py` の最後は c2cbc41)。p4 の試しは全対象と同じ共通の部品(`adapters/common.py` 242-270 行)。`time_span_ns` は渡していない。新実装だけ有利になる呼び方は見つからなかった。
- Basana の adapter: 配布物の class(`basana.external.*`)を配布物の公開の入口(`FifoQueueEventSource` → dispatcher)に渡し、戦略に届いた物を記録する(`passed_by` = Basana の dispatcher)。新実装の adapter が `core.TradeEvent(...)` を組んで `CoreEngine` に渡すのと同じ形で、公平と判断した。
- 検討表: `check_bt_considered.py` → `OK 誤り 0 件`。P0-1 の 13・P0-7 の 52 の行を読み、能力ごとに「在る/無い」と出所の行、含む側の走った候補(または再現した LEAN)の機構と場面の結果が書かれていることを確かめた。場面係の試験 `test_every_skip_names_what_it_lacks_for_each_scene_the_survey_side_misses` が「最良が正解と一致でない場面」の文を行ごとに確かめる。
- 再現: `repro_lean52` を読んだ。型(TradeBar・Tick・MarginInterestRate)・100 ns 刻みの時刻・frontier・同期・Slice・`OnData` は注釈の行と対応する。欠けは i0-r6-04。再現しなかった機構の 17 場面を「結果なし」にしたのは、「対応なし」にすると LEAN が持たないと書くことになるので、場面係の判断(`ROOTCAUSE_r6-3.md` 147 行)に同意する。`OnData` の中で Slice を Bars・Ticks・MarginInterestRates の順に並べ直すのは adapter の選んだ順だが、同じ Slice に 2 型が入る場面(同時刻の複数型)は清算を含み対応なしで決まるので、今の表には効かない(i0-r6-02 を直して同時刻の 2 型の場面を作るときは、この並べ直しが並びを決めないようにする必要がある)。
- 前の周の [直す]・[示唆] を [止める] の基準で見直した: i0-r5-05 を付け直した(i0-r6-01)。i0-r5-06 は付け直さない(1.2)。

## 4. 試験

- 足した批評家の試験: `tests/bt/critic/item_0/test_i0r6_past_answer_names_undelivered.py`(6 件、実装。4 件落ちる)、`tests/bt/critic/item_0/test_i0r6_battery_p5_measures_order_not_types.py`(3 件、場面集。2 件落ちる)。壊れた試験は残し、作業者(実装)と場面係(場面集)が直す。
- 書き直した批評家の試験: `test_i0r5_battery_opponent_grading.py` の `test_basana_is_not_credited_with_an_event_type_its_adapter_wrote`(1.1。6 件とも通る)。
- 全試験: `setsid nohup … python3 -m pytest -p no:cacheprovider > scratchpad/bt/pytest_item0_r6_critic.log`(末尾の行は下に追記)。

## 5. 返す前の吟味(委任文 §3「提出前の吟味」の批評家の文)

- 指摘ごとの根拠を自分で再現した: i0-r6-01 は probe と試験(4 failed)、i0-r6-02 は試験(2 failed)と `attempts/1.log`・`survey_best.tsv`、i0-r6-03 は probe の出力、i0-r6-04 は保存された原文の 181・329・365-372 行。
- 格付け: i0-r6-01 は「迷ったら重い方」で [止める](理由は本文)。i0-r6-02 は委任文の監査の観点(新実装に有利な偏り)と規則 3 に当たるので [止める]。i0-r6-03・04 は要件と正解を崩さず、黙って誤った値を返さないので [直す]。
- 前の周の指摘の直りは 1.2 で 1 件ずつ確かめた(直ったものは 2 章に挙げていない)。
- 相手の付け違い: i0-r6-01・03 は `src/bot/bt/core/` と作業者の試験 = 実装。i0-r6-02・04 は `tests/bt/battery/item_0/`(場面の定義・再現)= 場面集。
- 全試験の結果(2026-09-24T09:58:59Z に開始、記録 `scratchpad/bt/pytest_item0_r6_critic.log`): `6 failed, 3690 passed, 6 skipped, 1 warning in 504.89s (0:08:24)`。落ちた 6 件は、この周に足した批評家の試験の 6 件だけ(`grep ^FAILED` の全行が `test_i0r6_past_answer_names_undelivered.py` の 4 件と `test_i0r6_battery_p5_measures_order_not_types.py` の 2 件)。それ以外の既存の試験は全部通る(書き直した `test_i0r5_battery_opponent_grading.py` を含む)。
