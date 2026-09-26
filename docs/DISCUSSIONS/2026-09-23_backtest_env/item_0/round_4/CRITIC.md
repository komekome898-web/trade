# 項目 0「核」第 4 周 — 批評家の記録

委任文: `docs/DATA/delegations/20260923_backtest_env_prompt.md`。起動文が示す指紋は `362bf666dfac`(コミット `ebbaf34` の版)。今の作業木の版は `a25b24aa10c9`(コミット `385172e`、`sha256sum | cut -c1-12` で確かめた)。`git diff ebbaf34 385172e -- docs/DATA/delegations/20260923_backtest_env_prompt.md` の差は §0 の「無駄を出さない」の行に L-429 の注記を足した 1 行だけで、批評の規則(§3「批評家」「場面集の規則」、§4)には触れていない。全 158 行を読んだ。この食い違いはリードの手順の誤りとリードが記録している(`docs/AUDITOR/VERDICTS/2026-09-23_backtest_env_run6_item0.md` の r4-1 の処置 2)ので、場面係への指摘にしない。
合意した完了の形(委任文 §0 の逐語): 「**すべてが調査結果以上の信頼性と再現性に優れたものにすること。**」
手元に置いたもの: 固定した要件 `docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/REQUIREMENTS.md`、場面集 `tests/bt/battery/item_0/scenes.py`(`python3 gen_definitions.py --check` → `OK`、場面 32)、検討表 `tests/bt/battery/item_0/opponents/CONSIDERED.md`(`python3 scripts/check_bt_considered.py …` → `OK 誤り 0 件`)、場面係の `tests/bt/battery/item_0/ROOTCAUSE_r4-1.md`、作業者の `round_4/ROOTCAUSE.md`、この周の資料 `round_4/materials/`、前の周の `round_3/CRITIC.md`、調査報告 `docs/DATA/SCAN_2026-09-21_tools.md` の該当行(3166・3195・3292・6812・7539・8806・9153 行ほか)。

## 0. 構造の変化(前の周から)

あり。作業者の申告の 3 点を実物(コミット `ccfed73`)で確かめた。
- (1) 寿命の状態: `engine.py:583-596`(`step()` が本体を包み、`BaseException` を `_failure` に置いて投げ直す)、`engine.py:567-581`(`_usable` が再入を `EngineReentryError`、失敗後を `EngineFailedError` で断る)、`run()`・`result()` も `_usable` を通る(`engine.py:629-637`)。`CORE_CONTRACT["lifecycle"]`(`contract.py:45-55`)。
- (2) 段ごとの表 `_PATHS`(`ordering.py` の表、各段に `fifo`)、`channels_fifo` は表から作る。出力: `ORDERING_RULE['channels_fifo']` → `['venue:input', 'venue:request', 'deliver:input (per input stream, reception order)', 'deliver:notice']`、`not_fifo` → `{'deliver:timer': 'the requested time exactly …'}`。
- (3) `DeliveredEvents`(`window.py:25-60`)を `visible_events` が返す(`api.py:466-472`)。

## 1. 前の周までの指摘を自分で確かめ直した結果

コマンド: `PYTHONPATH=src python -m pytest -p no:cacheprovider tests/bt/item_0 tests/bt/critic/item_0 tests/bt/battery/item_0`。この周の試験を足す前は `1 failed, 394 passed`(落ちたのは下の 1.1 の 1 件だけ)。

### 1.1 批評家の試験の誤り(場面集の規則 8)

- `test_i0r2_battery_p5_grading.py::test_single_input_form_of_hand_over_order_agrees_with_keeping_one_input_in_order`: 作業者(返り値、VERDICTS の「作業者の第 4 周」)と場面係(`ROOTCAUSE_r4-1.md` の i0-r3-04 の節)がどちらも「場面の正解の鍵 `distinct_orders` が無くなったための `KeyError`」と報告した。**確かめた結果、試験自身の誤り。**書き直した。性質は同じ(1 本の入力の順を守る対象を正解と一致にし、固定の型の順を「規則」と申告して観測と合わない対象は一致にしない)を、今の採点(`run_battery.correctness(…, sc)` = `graded_from` の採点)で見る形にした。実の核で 24 通りの連結を走らせて 24 通りの並びになること(`len(seen) == 24`)も残した。→ 通る。
- 同じファイルの `test_dropping_three_of_four_same_time_events_is_not_graded_as_correct`: 書き直していない。今は通る(i0-r3-03 が直った)。

### 1.2 前の周の指摘

| id | 確かめ方 | 結果 |
|---|---|---|
| i0-r3-01(例外のあとも走る) | 前の周の `test_i0r3_resume_after_exception.py` の 2 件が通る。`engine.py:583-596`・`567-581` を読んだ。核の中に例外を握りつぶす所が無いこと: `grep -n "except\|finally" src/bot/bt/core/*.py` → 核の `except` は `engine.py:365`(流れの終わりの `StopIteration`)・`464`・`518`(単位の誤りの言い直し)と `events.py`・`time.py` の検査だけ。戦略の呼び出しの中で同期に呼ばれる差し込み口は無い(`_OrderPort.place`・`cancel`・`set_timer` は核の外のコードを呼ばない、`api.py:221-276`)ので、戦略が例外を受け止めて歩が半端に続く道も無い | 直った |
| i0-r3-09(時計を先入れ先出しと書く) | 上の 0 の (2) の出力。加えて +10 ns・+5 ns の順に予約して `clock b 5` → `clock a 10` と届くことを実行で見た。表の主張(`fifo: False`・頼んだ時刻)と一致 | 直った |
| i0-r3-02(p4 の正解が弱い) | `scenes.py:256-276` の正解は `{every_attempt_stopped_by_error: True, future_value_obtained: False}`、採点は `run_battery.py:114-119`(名指した試しが 1 つ以上あり全部が例外)。この周の新実装の実行で、空を返した試し 1 つで不一致になった(下の i0-r4-01)= 空・切り詰めを素通りと数える | 直った |
| i0-r3-03(P0-5 の値の場面) | `run_battery.py:126-130`。前の周の試験 `test_dropping_three_of_four…` が通る | 直った(残りの弱さは i0-r4-05) |
| i0-r3-04(1 本の形の正解の矛盾) | 1.1 の書き直した試験が通る | 直った |
| i0-r3-05(QuantCore の既定の上限) | `opponents/quantcore_adapter.py:48` は既定のまま(`enabled = False` の行は無い)。場面係の試験 `test_no_survey_adapter_switches_off_a_protective_default` が通る | 直った |
| i0-r3-06(上位互換の対の中身) | 検討表を作り直し、能力を要件の文から並べ、観点の外の能力を分けた(`CONSIDERED.md` の各観点の冒頭)。PineForge・16・P0-5 の各行の対は直っている。ただし「行に無い能力」を「在るとしても」で覆う書き方が新しく全観点に入った → i0-r4-03 | 形は直った。同じ原因が別の形で残る(i0-r4-03) |
| i0-r3-07(写せなかった 90 行) | `CONSIDERED.md` の節「grep で当たって候補に写せなかった行」、場面係の試験 `test_every_unmapped_line_is_reviewed_in_the_table` が通る。P0-4 に 16(SCAN 3166 行)が入った | 直った |
| i0-r3-08(書かれていないことで「持たない」) | 8・15・107・38 の判断を「持たないと確認した」から「上位互換」に替えた。一次資料 (b) は読んでいない(`ROOTCAUSE_r4-1.md` の i0-r3-08 の節「8 OpenTrader の (b) 一次資料は読んでいない」) | **直っていない → i0-r4-03** |
| i0-r3-10(P0-2 の拒否の側) | 場面にしていないことと理由が `DEFINITIONS.md` の「場面にしていない観点・側面」に書かれた。批評家が見る側面なので、この周に核の振る舞いを確かめた → i0-r4-06 | 記録は直った。振る舞いは i0-r4-06 |
| i0-r3-11(検討表の指紋) | `CONSIDERED.md:3` は `362bf666dfac`。今の版 `a25b24aa10c9` との差はリードの手順の誤り(上の冒頭)なので指摘にしない | 直った(リードの分を除く) |
| i0-r1-*・i0-r2-* | 前の周までの批評家の試験がすべて通る(上のコマンド) | 直ったまま |

リードの記録(VERDICTS の r4-1 の処置 1)は「場面係は今回 P0-2 に拒否の側の場面を足したと返している」と書くが、場面集に P0-2 の拒否の側の場面は無い。コマンド: `PYTHONPATH=src python3 -c "…scenes.SCENES…"` → P0-2 の場面は `['p2-iso-utc', 'p2-iso-offset', 'p2-event-time-exact', 'p2-one-ns-apart']` で、前の周(`2b60eec`)の場面の id の並びと同じ。`DEFINITIONS.md` の「場面にしていない観点・側面」も「場面にしていない」と書く。**記録の食い違いとして書いておく**(場面集の中身は場面係の `ROOTCAUSE_r4-1.md` の「場面は足さない」と一致している)。

## 2. この周の指摘

### [止める] i0-r4-01 最新の次の位置から始まる区間が、黙って空を返す(target: 実装、repeat_of: なし)

場面 p4-future-read-attempt(`scenes.py:256-276`)の正解は、5 本目を**位置で**名指す読み出し(「今の最新の次の位置を、添字・先の参照・次を覗く手段で読む」)も例外で止まること、「空の結果・切り詰めた結果…は素通りで、正解ではない」。4 本目の呼び出しで最新は位置 3、位置 4 は 5 本目(まだ届いていない)。核は `[4]`・`[4:5]`・`[3:5]` を `FuturePositionError` で断るが、**位置 4 から始まる区間 `[4:]`・`[4::]`・`[4::2]`・`[len(bars):]` は `()` を黙って返す**。原因は `window.py:47` の前向きの区間の始点の検査が `start > n` で、`start >= n` ではないこと。作業者自身の規則(`round_4/ROOTCAUSE.md` D「位置 `0 .. len-1` は届いた事象、`len` 以後は未来」)とも合わない(添字は `i >= n` で断り、区間の始点だけ `n` を過去に数える)。
- 場面の結果: 資料係のこの周の実行で、新実装の p4-future-read-attempt は**不一致**(`round_4/materials/runs/new_impl.tsv:22`、試し `ctx.visible_events()[4:]` → `raised: null, returned: []`)。調査結果の側の組の表は新実装 31 / 32・調査結果の側 32 / 32(`round_4/表_hdj4yo.md` の「観点ごとの正解と一致の数」、P0-4 が 2 / 3 対 3 / 3)。**この組では新実装が調査結果の側を下回る。**
- 作業者の試験は、この空の答えを正しいものとして固定している(`tests/bt/item_0/test_bt0_future_position.py:77`「"from position 4 on" = nothing new yet」、`:87` `got["from_end"] == []`)。種つき乱数の試験の「正解」は実装の式をそのまま写している(`test_bt0_future_position.py:125` の `ahead = …` は `window.py:46-49` と同じ式)ので、この穴を見つけられない。作業者の場面集の試験(`test_bt0_scene_set.py:404-408`)は `[4:]` を試していない。
- リードは作業者の問い 3 に「末尾から先の空は今までどおり…場面 p4 の正解に揃っている」と答えている(VERDICTS の「作業者の問いへのリードの答え」3)。**揃っていない**: 上の実行の記録で、場面の採点はこの空を素通り(不一致)にした。この周の場面の正解は場面係が固定したもので、正解を緩めて `[4:]` の空を一致にするのは委任文 §3「要件と判定の固定」の「緩めない」に当たる。よって直すのは実装の側と判断した。リードの読みを残すなら、場面の正解との食い違いをリードが決める必要がある(私は決めない)。
- 根拠: 置いた試験 `tests/bt/critic/item_0/test_i0r4_open_slice_from_next_position.py`(区間 5 通り + 場面を runner で採点する 1 件)。出力: `AssertionError: visible_events(BAR)[4:] at the 4th bar names position 4 (the 5th bar, not delivered) and returned () silently` ほか 4 件、場面の採点 `AssertionError: scene p4-future-read-attempt: graded.get('every_attempt_stopped_by_error')=False; named reads that did not stop: [{… 'means': 'ctx.visible_events()[4:](最新の次の位置から先の区間)', 'raised': None, 'returned': []}]`。

### [止める] i0-r4-02 送った注文を、戦略があとの呼び出しから書き換えられる(target: 実装、repeat_of: なし)

`OrderRequest` は凍結されているが、`extra`(`api.py:89`「anything else a venue model needs」)は「タプルであること」しか検めない(`api.py:103-104`)ので、中に変えられる物(リスト・辞書)を入れられる。核は同じ物を送りの路に載せ(`api.py:247` `self._outbox.append(("new", request, now))`)、届いた時刻に `account.check_order` と `fill_model.on_order` にそのまま渡す(`engine.py:782-800`)。戦略が注文を送った呼び出しが終わったあと、**注文がまだ路の上にある間に、次の呼び出しから `extra` の中身を変えると、取引所の側はその変えた中身を受け取る**。実際の接続では、要求は送った時点の中身で、あとから変えるには訂正か取消の要求を送るしかない。`api.py` の冒頭の保証「No acting later … any later attempt to … act raises `StaleContextError`」と、戦略 → 取引所の路が「送ったもの」を運ぶという並びの規則(`ordering.py` の `venue:request`)が破れている。項目 2 は注文の種類(OCO の組・氷山の見せる量など)をこの `extra` で運ぶ見込みが高く(`OrderRequest` の説明「the set is item 2's to define」)、戦略が 1 つの辞書を使い回すだけで、取引所の側が見る注文が黙って変わる = 実現できない約定を作る。信頼性を崩す。
- 根拠: 置いた試験 `tests/bt/critic/item_0/test_i0r4_order_extra_mutated_in_flight.py`(注文の遅れ 10 秒、1 秒後の呼び出しで中身を変える)。出力: `AssertionError: the venue received ['sent', 'changed later'] at arrival: the strategy changed an order in flight from a later callback, without sending anything` / `AssertionError: the venue received {'iceberg_show': 0.0} at arrival: the strategy changed an order in flight`。

### [止める] i0-r4-03 「上位互換」を、中身の分からない能力に「在るとしても覆われる」で当てている(target: 場面集、repeat_of: i0-r3-08、場当たり)

前の周に「持たないと確認した」の根拠が無いと指摘した 8 OpenTrader・15 Mendl-Labs・107 sigc(と同じ種類の 38 MarS)は、一次資料 (b) を読まずに、判断を「上位互換」に替えただけで直された。理由の欄は、SCAN に書かれていない能力について「在るかは未確認…在るとしても 4 つの対が正解と一致」(`CONSIDERED.md` の P0-7 の表の 8・15・38・107 の行)。同じ書き方が、P0-5 の表のほぼ全行(3 PySystemtrade「並びの規則は…行に無い。在るとしても能 1〜3 は Basana の … が正解と一致」、11・37・70・98・99・101・104・105)、P0-7 の 3・11・13・52・63・98・123 にもある。
- 委任文 §3 は「スキップしてよいのは…**調査結果から明らかに弱いことがわかっている機構**だけ」「段の無い観点: 使える理由は『上位互換』の 1 本だけ = 動かせた候補か再現した候補の機構が、スキップする候補のその観点の能力を 1 つ残らず含むことを、**調査報告の行で 1 能力ずつ示す**」「『たぶん弱い』のような推測のスキップは禁止」。中身が分からない能力は「弱いことがわかっている」ではなく、行で示した対でもない。
- 「在るとしても覆われる」は、動かせた候補の最良が場面を全部取れば、どの候補のどの能力にも当てられる(この周の調査結果の側は 32 / 32、`round_4/表_hdj4yo.md`)。つまり一次資料を読まずに全部の候補を外せる理屈で、L-413「**動かせないからと言って機構を検討せず無視することを避ける**」を空にする。場面は 1 つの口につき 1 つのダミーを差し込むだけなので、場面で一致したことは、読んでいない機構(例: 15 の `variable_latency.rs` の揺らぎつきの遅延、SCAN 9153 行)が場面の測らない所で強いかを何も言わない。
- 場当たりとした理由: 前の周の指摘は「(b) を読めるのに読んでいない」(i0-r3-08)で、直しは判断の名前を、根拠の要求の緩い方(規則 9 の機械は「上位互換」の語しか見ない)に替えた。指摘の文言(「持たない」の根拠)だけを外し、求めた中身(口の有無を行か一次資料で示す)を満たしていない = 委任文 §3「根本的解決」の「指摘の文言だけに合わせる」。
- 求める形: 行に無い能力は、(b) で一次資料を読んで口の有無を書く(8 OpenTrader は台帳 §3 の 11 件ではない)。読めないときは (a)(b) の両方で材料が足りない理由を書いて「再現できない」にする。

### [止める] i0-r4-04 動かせる候補 16 を走らせず、この周に動いた 54 を「動かせなかった」と載せたまま(target: 場面集、repeat_of: なし)

- 16 Luczinsritter/event_driven_backtesting_engine は、道具サーベイで「隔離 venv に導入し、合成データで成行の往復を通した。状態は『導入して最小実行まで通した』で確定」(SCAN 3195 行)。場面係はこの周に導入を**試していない**(`CONSIDERED.md` の「読み方」の節「共有の環境の容量を使い切る導入は試していない」、空き 333 MB)。委任文 §3「動かせるものを**全部**同じ場面集に通す」と場面集の規則 4「動かせた道具は全部の場面に通す…試して動かなかった場面は、何を試したかと出たエラーを表の注記に書く」に当たる。試していないので「動かなかった」の記録も無い。空きはその後に作られている(リードが venv 7 本とキャッシュを消して 9,213 MB、VERDICTS の r4-1 の処置 4。いま `df -m /` → Available 7316 MB)。
- 54 finmarketpy は、資料係がこの周に同じ wheel で入れ直して 32 場面を通した(`round_4/materials/logs/finmarketpy_attempt.log`「68 秒で成功」、`logs/run_all.log` の `opp_finmarketpy … rc=0`)。資料係は「動かせなかった道具が無い」として表の注記を付けていない(`materials/commands.txt`)。一方、検討表は 54 を「この周は動かせなかった」として P0-7 の動かせなかった候補の行に載せ、上位互換でスキップしている(`CONSIDERED.md` の P0-7 の表の 54 の行)。規則 9「動かせた候補は検討表の行に載せない」と食い違い、どちらの記録が正しいかが資料の間で割れている。
- 16 は P0-3・P0-4・P0-7 の検討表に載る(P0-4 は「持たないと確認した」、一次資料を読んで能 1〜3 の口が無いことを行で示している)。走らせれば、これらは一次資料の読みではなく実行の結果で決まる(規則 6「動かせた候補なら実際に呼んで失敗した(コマンドと出力)」)。

### [直す] i0-r4-05 P0-5 の「規則どおり」の正解の列を、採点の外の adapter が書き、runner は検めない(target: 場面集、repeat_of: なし)

p5-same-time-twice・p5-hand-over-order の `follows_stated_rule` は、adapter が書いた `stated_rule.predicted`(規則を手で入力に当てた列)と観測の列の一致で決まる(`run_battery.py:126-144`)。場面の正解の値そのもの(この入力での並び)は場面係が決めておらず、各 adapter の書き手が決める。runner は `predicted` が `quote` から導けるかを見ない。新実装の `predicted` は `_TYPE_ORDER_QUOTED` を手で写した列から作る(`adapters/new_impl.py` の `_predicted`)。規則 1(申告を数えない)の趣旨からは、対象ごとの並びの正解を場面係が走らせる前に場面の側に固定する(対象の文書から写した規則と、それを当てた列を場面集の側に置く)方が強い。この周に実害は見つからなかったので [直す]。あわせて、adapter が核の規則を行番号で引いている(`adapters/new_impl.py` の `_RULE_SOURCE = "src/bot/bt/core/ordering.py 43-55 行…"`)。今は `sed -n 43,56p` で該当の段落に当たるが、核の説明が 1 行ずれると引用先が黙って外れる。名前(`ORDERING_RULE["source_merge"]`)で引く(リードも同じ直しを VERDICTS の作業者の問い 2 で求めている)。

### [直す] i0-r4-06 秒・ミリ秒の整数を、ナノ秒として黙って受ける(target: 実装、repeat_of: i0-r3-10)

P0-2 の拒否の側は場面にしない、批評家が見る、と場面集に書かれた(`DEFINITIONS.md` の「場面にしていない観点・側面」)ので、振る舞いを確かめた。出力(`TradeEvent(received_time_ns=v, …)`): `1700006400`(秒)→ 受理、`1700006400000`(ミリ秒)→ 受理、`1700006400.5`・`1.7000064e+18`・ISO 文字列・`True` → `TimestampUnitError`。秒の流れとナノ秒の流れを混ぜて渡すと、秒の流れは 1970 年の事象として先頭に並ぶ。`end_time_ns` には単位の誤りの検査がある(`engine.py:455-466`・`_step` の「is end_time_ns in another unit」)が、事象の時刻には無い。固定した測り方(受け入れの側の一致)は満たしているので [止める] にはしない(後から厳しくしない)。直す案: 実行の設定で「時刻の下限」を呼び手に明示させ、下回る事象を断る、など(作業者が決める)。

### [示唆] i0-r4-07 `extra` が (鍵, 値) の組であることを発注の時に検めない(target: 実装、repeat_of: なし)

`extra=(("a",),)` のような形の誤りは発注の時には通り、取引所の側が `extra_dict()` を呼んだ時刻(注文が届いた時刻)に `ValueError` で実行が失敗する(`api.py:103-107`)。誤りは大きく出るので信頼性は崩さないが、出る所が戦略の呼び出しから離れる。i0-r4-02 を直すときに、発注の時に組の形と中身を検めて写すとよい。

## 3. 場面集・表・検討表・adapter の点検

- **規則 1〜9**: 規則 4 に反するもの 1 件(i0-r4-04)、規則 6・9 の中身(上位互換の裏付け)に反するもの 1 件(i0-r4-03)。規則 3(観点ごとに値の場面 1 つ以上): P0-1〜P0-7 のすべてに値の場面がある(`scenes.SCENES` を数えた、`round_3` から変わっていない観点と、P0-5 の値の場面 2・P0-7 の値の場面 `p7-cost-per-unit`)。規則 7 の置き場所は守られている。規則 1 の「申告を数えない」: p4・p5 は採点の値を runner が観測から作るようになった。p5 の `predicted` の出所は i0-r4-05。
- **表**: 3 組とも左右 2 枚は違う(`round_4/materials/md5sum_pairs.txt`、`current: differ` / `survey: differ` / `mutant: differ`)。仕込みの効きは `mutant.py --check` → `changed scenes: ['p4-received-time']`。表の注記に道具名は無い(`logs/grep_tool_names.out`、該当 0 件)。調査結果の組は新実装 31 / 32 対 32 / 32(i0-r4-01)。
- **adapter の公平さ**: この周の資料係の変更は `adapters/new_impl.py` の p4 の試しに位置の名指し 4 つを足しただけ(`git diff HEAD -- tests/bt/battery/item_0/adapters/new_impl.py`、14 行)。場面の定義「当てはまる名指し方を全部試し」どおりで、新実装に不利な向き(試しが増えるほど止まらない試しに当たりやすい)の変更。新実装だけ有利にする呼び方の変更は無い。調査結果の側で p4 が一致の 3 件(Basana・hftbacktest・QuantCore)は、時刻や位置を取る読み出しが無く、戦略が書く呼び出しがそのまま型エラーで止まったもので、場面の入力の注記どおり。
- **再現(候補 33)**: この周の変更は数量 2 の費用の場面(`opponents/repro_33_execution_simulator.py` の `scene_p7_cost_per_unit`、`TransactionCostModel.calculate_cost(notional, quantity, …)` の子)。一次資料の setter(`set_cost_model`、execution_simulator.hpp 33-44 行、検討表の 33 の行)の形どおりで、弱めていない。一次資料をこの周に取り直して突き合わせてはいない(未確認)。
- **観点の網羅**: 要件の 7 観点はすべて場面がある。P0-2 の拒否の側は場面の外(i0-r4-06 で振る舞いを見た)。

## 4. 場当たりの直しの点検

- 場面集の側: i0-r4-03(判断の名前を替えて根拠の要求を外した)。
- 実装の側: 見つからなかった。寿命の状態・段の表・`DeliveredEvents` はどれも構造の変更で、前の周の試験の期待を緩めたものは無い(前の周までの批評家の試験は書き直した 1 件を除きそのまま通る)。ただし作業者の `test_bt0_future_position.py` の種つき乱数の試験は、正解を実装と同じ式で作っており(i0-r4-01)、実装の誤りを試験が写す形になっている。場当たりではないが、試験が実装を確かめる力を持たない。

## 5. 置いた試験(`tests/bt/critic/item_0/`。落ちるものは残す)

| ファイル | 指摘 | 今の結果 | 直す者 |
|---|---|---|---|
| `test_i0r4_open_slice_from_next_position.py`(6 件) | i0-r4-01 | 6 件とも落ちる | 作業者 |
| `test_i0r4_order_extra_mutated_in_flight.py`(2 件) | i0-r4-02 | 2 件とも落ちる | 作業者 |
| `test_i0r2_battery_p5_grading.py`(2 件目を書き直し) | i0-r3-04 の確かめ直し(1.1) | 通る | — |

コマンド: `PYTHONPATH=src python -m pytest -p no:cacheprovider tests/bt/item_0 tests/bt/critic/item_0 tests/bt/battery/item_0` → 下の 6 の末尾の行。
全試験: `setsid nohup env PYTHONPATH=src python -m pytest -p no:cacheprovider > <scratchpad>/bt/pytest_item0_r4_critic_full.log 2>&1 &` → 下の 6 の末尾の行。

## 6. 試験の末尾の行

- 項目 0 + 批評家 + 場面集: `8 failed, 395 passed in 58.92s`。落ちたのは上の 5 の表の 8 件(この周に置いた批評家の試験)だけ。
- 全試験(`<scratchpad>` = `/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad`、ログ `bt/pytest_item0_r4_critic_full.log`): 末尾の行 `8 failed, 3282 passed, 4 skipped, 1 warning in 474.29s (0:07:54)`。落ちたのは同じ 8 件だけ(`grep "^FAILED"` で確かめた)。場面係の記録にあった `tests/test_jev_delegate.py` の 1 件はこの走行では通った。
