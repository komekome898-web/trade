# バックテスト環境 7 回目(run `wf_4c6278b6-0bf`、指紋 4c4cfc6e4052)の項目 0 の記録

起動: 2026-09-24 15:21 JST(15:16 JST の run `wf_0b4adc34-1f2` は台本の誤りで 36 ms で落ちた。`2026-09-23_backtest_env_prompt.md` の「起動に使う版の記録(7 回目の起動)」)。項目 0 は第 6 周から(周の上限なし、L-433)。場面係の直しと作業者は同時(L-434)。

## 第 6 周(作業者 `作る:0#6`、場面係の直し r6-1〜r6-3)

### 結果の表

| 組 | 審査員 3 体の選択 | 通過(L-432: 相手が 2 体以上でなければ通過) |
|---|---|---|
| 対 当方の現状 | 3/3 が新実装(32/32 対 8/32) | 通過 |
| 対 調査結果の側 | 3/3 が新実装(32/32 対 29/32。差は P0-3 の 1 場面と P0-5 の 2 場面) | 通過 |
| 批評家 | [止める] 2(実装 1 = i0-r6-01、場面集 1 = i0-r6-02)、[直す] 2(実装 i0-r6-03、場面集 i0-r6-04) | **未達 → 第 7 周へ** |

台本の数え(L-436 の鎖): 実装の側 i0-r6-01 は i0-r5-05([直す])の続きで、[止める] としては 1 回目。i0-r4-02 → i0-r5-01 の鎖(2 回)は、批評家が i0-r6-01 をその続きとしなかったので途切れた。場面集の側 i0-r6-02 は新規(1 回目)。

### 監査役(場面)の出力(逐語。周の中の場面係の直しの監査、L-427/L-428 で第 6 周に含める)

**r6-1**(場面係の直しの対象: 第 5 周の i0-r5-02・03・04・06)
- **br6-1-1 [止める]**: runner の出所の検め(`run_battery.py` の `_carrier_problem`・`made_by_scene_set`、203-207 行・223-227 行・230-245 行)は、carrier の文字列の先頭のモジュール名が `BATTERY_TOPS`(場面集自身のファイル)かだけを見ており、同じファイルの p2-iso 読み手の検め(314-320 行)が使う `FOREIGN_READER_TOPS`(`builtins` を含む)を当てていない。DEFINITIONS.md の共通の決まり(6 行目)は『辞書や関数に型の印を付けた物』を adapter が作った型として明示的に禁じているが、`carrier()`(`adapters/common.py:250-253`)は `type(obj).__module__` を返すだけなので、adapter が組み立てた `dict`・関数オブジェクトはモジュールが `builtins` になり、`made_by_scene_set` に引っかからずに通る。実際に `survey_results/opp_predictivedev_tradesim.tsv:7-8`(carriers `["builtins.dict"]`、p2-event-time-exact・p2-one-ns-apart とも『正解と一致』)と `survey_results/opp_mihircoding_lob.tsv:25`(carriers `["builtins.function", ...]`、p5-same-stream-order が『正解と一致』)がこの carrier で採点されている。`ROOTCAUSE_r6-1.md:117` は `builtins.dict` を「carriers はどれも対象の物」と一括りに書いており、これは class ベースの carrier(barter-rs の `DataKind::Trade` など、由来が対象のモジュールで検証できる)と同列に扱っているが、`dict`・関数は由来をモジュールで検証できない(場面集の側が自分で組んだ dict でも同じ `builtins.dict` になる)。i0-r5-02 が塞いだはずの『adapter が作った物を正解と一致に数える』穴と同じ形が、この周に新設した検めの機構自体に残っていないか。
- **br6-1-2 [直す]**: `carrier_tag()`(`adapters/common.py:256-262`)が返す文字列は `f"{carrier(obj)}[{tt.__module__}.{tt.__qualname__}.{name}]"` の形で、`made_by_scene_set` の判定は `name.split('.')[0]`(文字列全体の最初のドット区切り = `obj` の class のモジュールだけ)しか見ない。タグ(`tag`)側のモジュールが `BATTERY_TOPS`(場面集の側)であっても、`obj` 自体が対象のモジュールの物なら検めを素通りする。現状は `opponents/aat_adapter.py:189,249` の 1 箇所だけで、タグは aat 自身の `EventType`(aat.config.enums)なので今は問題を起こしていないが、この形の carrier を使う場面が増えたときに `_carrier_problem` がタグの出所を見ない構造のままか。

**r6-2**(直しの対象: br6-1-1・br6-1-2)
- **br6-2-1 [止める]**: run_battery.py の origin_problem(313 行台)は、carrier の型が対象の配布物の中に定義されている(`roots.has_file(rec.get("type_file"))`)場合、`base_ok = True` を無条件に確定し、共有型の分岐で使っている held_by/passed_by の検めを一切当てない。ところが opponents/basana_adapter.py の `_event()`(69-90 行台)と opponents/aat_adapter.py の `_event()`(60-70 行)は、いずれも adapter(場面集の側、`in_scene_set` が真の `opponents/` 配下)自身のコードが、対象の公開の class(`basana.core.bar.BarEvent`・`basana.external.bitstamp.trades.TradeEvent`、`aat.core.Event`/`Trade`)を、場面の生データから直接組み立てている。common.py の `_stack_facts` は own-class の carrier にも `passed_by`/`held_by` を実際に計算しているが(carrier()/carrier_tag() は無条件に `_stack_facts(obj)` を呼ぶ)、origin_problem の own-class 分岐はこの結果を読まずに捨てている。これは br6-1-1 が指摘した欠陥(adapter が組んだ物を対象の物と数える)と同じ型で、対象を『共有型(dict・関数)』から『対象自身の class』に変えただけの穴である。ROOTCAUSE_r6-2.md の限界 1 は『34 QuantCore・12 pybotters・121 QSTrader の 3 対象だけが passed_by 等を持たない(母語のコードからの呼び出しのため)』と書くが、この書き方は残りの own-class carrier(Basana・aat を含む)には passed_by 等が存在し、それによって正しさが裏付けられているかのように読める。しかし origin_problem のコードはその値を一度も参照しないので、『存在する』ことは『検めに使われている』ことを意味しない。test_battery_item0.py の r6-2 の試験(587-761 行台)は fake_tool の `event()`(対象自身のモジュール内で `Event(...)` を組む関数)を通した経路しか確かめておらず、`opponents/*.py`(scene-set 側)が対象の class を直接コンストラクタで組み立てて common.carrier に渡すケース(実際の basana_adapter.py・aat_adapter.py の `_event()` と同じ形)を機械的に再現した試験が無い。CONSIDERED.md の『含む』の論拠の大半(観点 P0-1・P0-3・P0-5 ほか、ほぼ全ての『上位互換』の行)は 1 Basana の p1-typed-events・p3-trade などの『正解と一致』を裏付けに引いている。この own-class の無検めが、adapter 自身が組んだ場面のデータをそのまま対象の class に詰めて『対象の物』と数えている可能性を残したまま、検討表の大半の『含む』の論拠が組み立てられていないか。
- **br6-2-2 [聞く]**: CONSIDERED.md の集計(258-268 行)では、全観点合計で『動かせない(検討表の行)』31 件のうち『再現した』が 0 件、『スキップ(上位互換)』が 16 件で、実装のコードで『確かめた』と書かれた候補(表中の多数の行)がすべて『再現した』ではなく『スキップ: 明らかに弱い(上位互換)』に流れている。委任文 §3『段の無い観点』の既定は『実装のコードで確かめられる候補を全部再現する』で、スキップは『調査結果から明らかに弱いことがわかっている機構』のときの例外のはずである。7 観点すべてで再現 0 件という結果は、br6-2-1 で指摘した own-class carrier の無検めにより Basana・aat などの『含む』側の証拠(正解と一致)自体の裏付けが弱いまま、それを根拠に他の全候補をスキップできている構造になっていないか。上位互換の判定(委任文 §3『使える理由は「上位互換」の 1 本だけ』)が、1 能力ずつ調査報告の行で示す規則どおりに厳格に運用されているか、それとも実質的に『再現の手間を避けるための言い訳』(KA-06/KA-24 と同型の族の縮小)になっていないか。

**r6-3**(直しの対象: br6-2-1・br6-2-2)— [止める] 0 で資料係へ進んだ
- **br6-3-1 [聞く]**: opponents/CONSIDERED.md の「読み方」冒頭(10 行目)に、候補 35(thirupathikannan-ai/Optimal-Execution-And-Market-Impact-Simulator-)について「ファイルの置き場所を公開の版のまま直して走らせる手を、この環境の権限の検査(自動の分類器)が拒否したので走らせていない(リードに上げる)」と書かれている。これは委任文 §0「作業中に、この表に無い判断が要るところに来たら、自分で決めない。報告の『リードに聞くこと』に書いて、その部分は作らずに止める」に当たる事案に見えるが、場面係の成果物(DEFINITIONS.md・CONSIDERED.md・ROOTCAUSE_r6-3.md のいずれ)にも、委任文 §3「提出前の吟味」の場面係向けの記入欄(最初の作り = DEFINITIONS.md の末尾、直し = rootcause)にも、この『リードへ上げる』事項が独立した項目として明示されていない(検討表の 1 行の理由欄に埋もれている)。この環境の権限の分類器がこの候補を拒否した件は、リードが実際に読んで拾える形(例えば ROOTCAUSE_r6-3.md や報告の別項目)で明示的に切り出されているか、それとも検討表の中の 1 文に埋もれたままか。
- **br6-3-2 [聞く]**: ROOTCAUSE_r6-3.md『この検めが見ないもの(限界)』の 1 は『returned_by は、読みが戦略の呼び出しの中で行われたかを見ない。対象の関数が返した物は、adapter が戦略の外で呼んで記録しても「返した」になる』と自己申告している。br6-2-1 が指摘した欠陥(adapter が組んだ/持つだけの物を『対象が届けた』と数えてしまう)と同じ型の穴が、型を『対象の class を直接構築する』から『対象の関数を戦略の呼び出しの外で呼んで返り値を記録する』に変えた形でまだ残っている(この周に確認した 55 backtesting.py・2 Backtrader・12 pybotters の adapter は per-event の callback の中で `C.attr`/`C.aiterate` を呼んでおり、現状の実装では戦略の呼び出しの中で読んでいるように見えるが、この検めがそれを機械で強制していない以上、今後の候補・adapter の直しでこの経路を戦略の呼び出しの外で使っても origin_problem は拒まない)。この残った穴は、動かせなかった候補の『上位互換』の含む側の根拠には現状使われていない(63 の依拠先はすべて 1 Basana・61 barter-rs・23 hftbacktest・65 aat・69 gobacktest・98 mihircoding・52 LEAN の直接届いた carrier)ため即座に検討表の結論を動かすものではないが、この委任(バックテスト環境刷新)の完了の形『すべてが調査結果以上の信頼性と再現性に優れたものにすること』に照らし、この穴を項目 0 の作業者の 1 周目が始まる前に閉じる(戦略の呼び出しの中で読まれたことを機械で確かめる)か、閉じずに残す判断(閉じない理由とその範囲)を委任文に明記するかは、リードが決めることではないか。

### リードの答え(r6-3 の [聞く] 2 件。台本は走行中なので直接は渡せない。次の起動の `lead_notes` / `prior_battery_record` に入れ、この周の批評家・場面係の作業には委任文 §0 の「リードに聞くこと」の経路で届く)

1. br6-3-1(候補 35 のファイルの置き場所を直す手が、この環境の権限の分類器に拒否された): **リードが受け取った。**検討表の 1 行に埋もれたままにしない。次の起動で場面係に「報告の『リードに聞くこと』に独立の項目として書く」を求める。リード自身がこの操作(公開の版どおりの置き場所へ移す)を試すのは、場面係が同じ場所で作業している間は行わず、run が止まった段で行う(同時に触ると指紋が変わる)。分類器の拒否はリードの権限では変えない(A-16)。
2. br6-3-2(`returned_by` が「戦略の呼び出しの中で読まれたか」を見ない穴を、閉じるか、閉じない理由と範囲を委任文に書くか): **閉じる。**根拠はオーナーの逐語「**すべてが調査結果以上の信頼性と再現性に優れたものにすること**」(L-405)。閉じない理由を委任文に足すのは、族・検めを説明なく縮める形(A-10)に近い。次の起動の場面係への指示に「戦略の呼び出しの中で読まれたことを機械で確かめる」を入れる。この周の批評家(i0-r6-02・04)はこの穴を挙げていないので、場面係 r7-1 の作業には含まれていない可能性がある — 次の周の監査役(場面)が見る。

### 資料係(表)`表:0#6` の注記(要点。全文は `docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/round_6/materials/`)

観点ごとの「正解と一致」: 新実装 32/32、当方の現状 8/32、試金石 31/32(p4-received-time の 1 場面)、調査結果の側を寄せた行 29/32(p3-mixed-one-run・p5-same-time-twice・p5-hand-over-order はどの対象も最良が「対応なし」)。「2 回の実行で同じ」は 4 行とも 32/32。走らせた対象 40、すべて rc=0、場面係の survey_results との差 0 セル。相手の道具の結果の再利用(L-435)は、第 5 周の materials に場面集の指紋の記録が無く、場面集が 87 ファイル変わっていたので行わず、全部走らせ直した(この周の指紋 5eb3e2f76129…、走る前後で同じ)。

### 批評家 `批評:0#6` の出力(逐語)

- **i0-r6-01 [止める]** 相手=実装 repeat_of=i0-r5-05 場当たり=False: 答えが過去で終わっているとき(until_ns で切った答え、または歩幅つきの前向きの区間)、最後の次より先の位置を名指すと、まだ届いていない事象を名指していても OutsideAnswerError が出る。この型は LookAheadError の子ではなく、文は「the events after it were delivered」と言う。誤りの種類を、名指した位置ではなく、答えが持つ 1 つの事実 next_is_undelivered(最後の次の 1 位置のこと)だけで決めているため(window.py の _check_bound)。未来を読もうとした名指しが先読みの誤りとして捕まらず、しかも「届いた」という誤った事実を返す。作業者は根本原因 B-6 で「名指した位置に届いた事象があれば過去」と書いたが、実装はそうなっていない。作業者の試験も見つけられない: test_the_fact_agrees_with_the_input_at_every_callback は ans[len(ans)] しか試さず、test_every_index_and_slice_matches_the_probe_oracle は「最後より先のどの名指しも答えの事実と同じ種類」を正解に置いて、実装の規則を写している。第 5 周(過去を未来と言う向き)は [直す] だったが、今度は先読みを見落とす向きで、同じ根の全箇所も直していない。迷ったので重い方に付けた。
  - 根拠: scratchpad/bt/item0_r6_critic_probe_answer_kind.out: 'until day 6 (7 bars) [12]: named reads[12] = NOT delivered yet -> OutsideAnswerError: ...so the events after it were delivered but are outside this answer' / 'all[0:6:3] -> (0,3) [4]: named reads[12] = NOT delivered yet -> OutsideAnswerError'。試験 tests/bt/critic/item_0/test_i0r6_past_answer_names_undelivered.py → 4 failed, 2 passed。src/bot/bt/core/window.py の _check_bound(next_is_undelivered だけで種類を選ぶ)。tests/bt/item_0/test_bt0_future_position.py の 191-222 行と 291-340 行
- **i0-r6-02 [止める]** 相手=場面集 repeat_of=None 場当たり=False: P0-5 の p5-same-time-twice と p5-hand-over-order は、約定・足・資金調達・清算の 4 型を同時刻に置く。この 4 型を全部持つ調査結果の側の対象(走った候補と再現)は 0 件なので、調査結果の側の最良は 2 場面とも対応なしになる。これを決めているのは並びの規則ではなく、P0-3 がすでに測っている型の欠けである。場面係自身の probe r6-1 では、同じ入力を Basana が持つ型だけにすると FOLLOWS True・distinct_orders 1 で、並びの規則を満たしている。それでも表は P0-5 を新実装 3/3、調査結果の側 1/3 と出す。調査結果の組で違う 3 セルのうち 2 つがこれで、観点ごとに比べる審査員(規則 3)に、記録が示していない「並びの差」を読ませる。委任文 §3 の監査の観点「新実装に有利な範囲への偏り」に当たる。場面係は ROOTCAUSE_r6-1 の [判断] でこの形を書き、直し方まで挙げたが、場面は変えずに残した。p1-merge-by-time にも同じ作りがある(今は LEAN の再現が最良を正解と一致にしているので表には出ていない)。P0-5 の要件は「複数型」なので、対象が持つ 2 型以上で測れば要件を緩めずに直せる。
  - 根拠: 試験 tests/bt/critic/item_0/test_i0r6_battery_p5_measures_order_not_types.py → 2 failed(p5-same-time-twice, p5-hand-over-order), 1 passed。tests/bt/battery/item_0/survey_results/attempts/1.log 12-21 行(P5 ... FOLLOWS True, distinct_orders_over_hand_overs 1)。round_6/表_oh7l5v.md の P0-5 は A 3/3、B 1/3。materials/survey_best.tsv の 23-24 行は対応なし。DEFINITIONS.md 205-219 行
- **i0-r6-03 [直す]** 相手=実装 repeat_of=None 場当たり=False: values.py の as_text・as_float・scalar は、isinstance で組み込みの型の子かを見てから組み込みの読み出しを呼ぶ。そのため __class__ を偽る物は子として通り、次の読み出しで生の TypeError が出る。運び手の誤りの型(OrderApiError・VenueProtocolError・EventValidationError)にならず、values.py の説明「ValueError を出し、呼び手が包む」とも核の契約とも食い違う(値は路を渡らず、断られてはいる)。また post_only=np.bool_ は「post_only must be a bool, got bool」という誤った文で断られる。np.float64・np.int64 は受けて組み込みの値にするのに、np.bool_ だけ断るという食い違いもある。
  - 根拠: scratchpad/bt/item0_r6_critic_probe_values.out: 'size=Spoof(float) REFUSED builtins.TypeError descriptor '__float__' requires a 'float' object but received a 'Spoof'' / 'Fill.price=Spoof(float) REFUSED builtins.TypeError' / 'post_only=np.bool_ REFUSED bot.bt.core.errors.OrderApiError post_only must be a bool, got bool' / 'size=np.float64 ACCEPTED type <class 'float'>'
- **i0-r6-04 [直す]** 相手=場面集 repeat_of=None 場当たり=False: LEAN の再現 opponents/repro_engines/lean52.py の time_slice_create は、注釈で TimeSliceFactory.cs の 184 行と 365-372 行を書き直したと言う。しかし原文では、この 2 か所はそれぞれ 181 行と 329 行の !packet.Configuration.IsInternalFeed の条件の中にある。再現はこの条件を落としており、場面の購読が内部の購読でない根拠(行)も注釈に書いていない。冒頭には「nothing is added / weakened」とある。p1-merge-by-time と p3-funding の調査結果の側の最良はこの再現から来ている。既定の購読が内部の購読かは、批評家は確かめていない(中身を取らない clone しか無く、ネットワークで取り直していない)。調査結果の側を強くする向きなので [直す] に留めるが、委任文 §3 の「注釈に 1 対 1 で書く」に照らして直す必要がある。
  - 根拠: scratchpad/bt/r6-3/item0_r6-3_scenekeeper_TimeSliceFactory.cs 181-184 行('if (!packet.Configuration.IsInternalFeed) { allDataForAlgorithm.Add(baseData); }')と 329・365-372 行('else if ((delisting = baseData as Delisting) != null || !packet.Configuration.IsInternalFeed)' の中の marginInterestRates)。tests/bt/battery/item_0/opponents/repro_engines/lean52.py の time_slice_create に IsInternalFeed が無い。materials/survey_best.tsv の 2・13 行 = repro_lean52

### 審査員 6 体の出力(逐語。左右の割り当ては `round_6/JUDGES.md`)

- 盲検:0#6:current0: 選択 **左** — 正しさ(正解との一致)は、7 つの観点すべてで行 A が行 B を上回るか同じ数であり、A の方が劣る観点は 1 つもない。表の各セルを自分で数え直した結果は次のとおりで、表の集計と一致した。
- P0-1: A 3/3、B 1/3(B は p1-merge-by-time と p1-typed-events が対応なし)
- P0-2: A 4/4、B 2/4(B は p2-iso-utc と p2-iso-offset が対応なし)
- P0-3: A 11/11、B 1/11(B で正解と一致したのは p3-bar だけで、残り 10 件は対応なし)
- P0-4: A 3/3、B 1/3(B は p4-received-time が対応なし、p4-future-read-attempt が不一致。不一致の値は every_attempt_stopped_by_error=false で、未来の値の読み出しを構造で止められていない)
- P0-5: A 3/3、B 1/3(B は p5-same-time-twice と p5-hand-over-order が対応なし)
- P0-6: A 3/3、B 0/3(B は 3 件とも対応なし)
- P0-7: A 5/5、B 2/5(B は p7-latency-model-swap、p7-cost-per-unit、p7-account-swap が対応なし)
- 計: A 32/32、B 8/32

場面数の多い P0-3 を除いても、残る 6 観点すべてで A が上回る。したがって、場面数の多い観点に引きずられた結果ではない。能力の有無についても、B には能力を示せない場面が多い。例として、P0-6 の発注・取消・約定の通知はすべて対応なしで、P0-7 では遅延模型と口座の差し替えが対応なしだった。

再現(2 回の実行で同じ)は、A も B も全観点で満点だった(P0-1 3/3、P0-2 4/4、P0-3 11/11、P0-4 3/3、P0-5 3/3、P0-6 3/3、P0-7 5/5、計 32/32)。この点では差が無い。

以上から、再現は同等で、正しさは全観点で A が優れるため、行 A を選ぶ。
- 盲検:0#6:current1: 選択 **右** — 表の各セルから数え直した(要約表の数と一致)。正しさ(正解と一致の数): P0-1 は A 1/3・B 3/3、P0-2 は A 2/4・B 4/4、P0-3 は A 1/11・B 11/11、P0-4 は A 1/3・B 3/3、P0-5 は A 1/3・B 3/3、P0-6 は A 0/3・B 3/3、P0-7 は A 2/5・B 5/5。計は A 8/32、B 32/32。7 観点すべてで B が A 以上で、しかもすべての観点で B が上回っている。したがって、場面の数が多い P0-3 に引きずられた差ではない。A は残り 24 場面のうち 23 場面が「対応なし」、1 場面(p4-future-read-attempt)が「不一致」だった。この「不一致」の値は {"every_attempt_stopped_by_error": false, "future_value_obtained": false}。未来の値は取れていないが、試みがエラーで止められてもいない。P0-6(戦略の API)では A の一致は 0 件で、能力がまったく示されていない。再現(2 回の実行で同じ)は A・B ともに全観点で満点(32/32)なので、差は無い。正しさで B が全観点で上回り、再現は同じなので、B(行 B)がより正しく、再現性は同じ水準と判断する。
- 盲検:0#6:current2: 選択 **左** — 正しさ(正解と一致)を表の各場面セルから数え直した。行 A は 7 つの観点すべてで満点だった(P0-1 3/3、P0-2 4/4、P0-3 11/11、P0-4 3/3、P0-5 3/3、P0-6 3/3、P0-7 5/5、計 32/32)。行 B は P0-1 1/3(p1-one-call-per-event のみ)、P0-2 2/4(p2-event-time-exact・p2-one-ns-apart)、P0-3 1/11(p3-bar のみ)、P0-4 1/3(p4-visible-at-step。p4-future-read-attempt は不一致、p4-received-time は対応なし)、P0-5 1/3(p5-same-stream-order)、P0-6 0/3、P0-7 2/5(p7-fill-model-swap・p7-cost-model-swap)で、計 8/32。行 B の残り 24 場面は、23 件が対応なし(能力が無い)、1 件が不一致だった。数え直した値は、表の集計欄とすべて一致した。

観点ごとに比べると、7 観点すべてで A が B を上回った。B が A と並ぶ観点も、B が A を上回る観点も無い。場面の多い P0-3(11 件)を除いても、残り 6 観点のすべてで A が上回る。したがって、場面の多い観点に引きずられた結論ではない。

再現(2 回の実行で同じ)は、A・B ともに全 32 場面で同じだった(両者とも 7 観点すべてで満点、計 32/32)。この点に差は無い。

以上から、再現性は同等で、正しさと能力の有無では A がすべての観点で上回る。よって A(左)を選ぶ。
- 盲検:0#6:survey0: 選択 **左** — 表の各セルから自分で数え直した。
正しさ(正解と一致の数): 行 A は P0-1 3/3、P0-2 4/4、P0-3 11/11、P0-4 3/3、P0-5 3/3、P0-6 3/3、P0-7 5/5 で、計 32/32。行 B は P0-1 3/3、P0-2 4/4、P0-3 10/11、P0-4 3/3、P0-5 1/3、P0-6 3/3、P0-7 5/5 で、計 29/32。B が欠けた 3 件はどれも「対応なし」で、不一致や結果なしは 0 件だった。内訳は p3-mixed-one-run(P0-3)、p5-same-time-twice と p5-hand-over-order(P0-5)。
再現(2 回の実行で同じ): A も B も全観点で満点で、32/32 ずつ。
観点ごとに比べると、7 観点のうち 5 観点(P0-1・P0-2・P0-4・P0-6・P0-7)は同点、2 観点(P0-3・P0-5)は A が上だった。B が上の観点は 0 だった。
P0-5(同時刻の事象の並びが決定的で、規則に従うこと)では B が 1/3 にとどまる。P0-5 は場面の少ない観点でもあるので、場面数に引きずられずに見ても差ははっきりしている。
P0-3 の 1 件は、8 種の事象を 1 回の実行に混ぜる場面(値の場面)だった。B にはこの能力が無い。
再現には差が無い。正しさと能力の有無で A が上回るので、A(左)を選ぶ。
表の注記によると、A の行はいくつかの場面で、複数の候補のうち最も良い結果を寄せたものである。資料の書き方は採点の対象にしないので、判定は表に出た結果だけで行った。
- 盲検:0#6:survey1: 選択 **右** — 正しさ: 観点ごとに場面の各セルを数え直した。表の集計行と一致した。P0-1 は A 3/3・B 3/3、P0-2 は A 4/4・B 4/4、P0-4 は A 3/3・B 3/3、P0-6 は A 3/3・B 3/3、P0-7 は A 5/5・B 5/5 で、この 5 観点に差は無い。差が出たのは 2 観点。P0-3 は A 10/11・B 11/11 で、A は p3-mixed-one-run が「対応なし」。P0-5 は A 1/3・B 3/3 で、A は p5-same-time-twice と p5-hand-over-order が「対応なし」。P0-5 は同時刻の事象の並びが決定的で規則に従うことを見る観点で、A はこの観点の場面 3 件のうち 2 件に対応していない。場面の多い P0-3 に引きずられないよう観点ごとに比べた。差があるのは 7 観点のうち 2 観点で、どちらも B が上。B が劣る観点は無い。合計は A 29/32、B 32/32。「不一致」と「結果なし」のセルは、どちらの行にも無い。再現: 両者とも全 7 観点で「2 回の実行で同じ」が満点(A 32/32・B 32/32)で、差は無い。まとめ: 正しさでは B が 2 観点で上回り、残りの観点と再現は同等なので、B(右)を選ぶ。注意点: 表の注記によると、各行は複数の候補の最も良い結果を場面ごとに寄せたもの。B の行でも、p6-place-then-cancel を含む 16 場面で、寄せた候補のうち 1〜2 件は結果なし(例外、または機構を実装していない)だった。
- 盲検:0#6:survey2: 選択 **左** — 表を自分で数え直した。正しさ(正解と一致の数)は、行 A が P0-1 3/3、P0-2 4/4、P0-3 11/11、P0-4 3/3、P0-5 3/3、P0-6 3/3、P0-7 5/5 で、計 32/32。行 B は P0-1 3/3、P0-2 4/4、P0-3 10/11、P0-4 3/3、P0-5 1/3、P0-6 3/3、P0-7 5/5 で、計 29/32。行 B の 3 件はどれも「対応なし」で、「不一致」と「結果なし」は無い。内訳は、P0-3 の p3-mixed-one-run(6 種の市場の事象を 1 回の実行に混ぜる、値の場面)と、P0-5 の p5-same-time-twice(値)・p5-hand-over-order(能力)。再現(2 回の実行で同じ)は、行 A・行 B とも全 7 観点で満点(32/32)で、差は無い。
観点ごとに比べると、P0-1・P0-2・P0-4・P0-6・P0-7 の 5 観点は同等。P0-3 は行 A が 11/11、行 B が 10/11 で行 A が上。P0-5 は行 A が 3/3、行 B が 1/3 で、行 A が大きく上。P0-5 は場面が 3 件しかない観点なので、場面の数の多い観点に引きずられた差ではない。同時刻の事象の並びが決定的で規則に従うこと(P0-5)を、行 B は 3 場面のうち 2 場面で満たせていない。行 B が行 A を上回る観点は 1 つも無い。以上から、正しさでは行 A が優れ、再現性は同等なので、行 A を選ぶ。
付記: 行 A は複数の候補を 1 行に寄せたもので、16 場面では寄せた対象のうち 1 件(p6-place-then-cancel では 2 件)が結果なしだった。表では残りの対象の最も良い結果をその場面の行に載せている。このことは表の注記に書いてあるが、比べる対象はあくまで表に示された行の結果とした。

## 第 7 周(走行中: `場面の直し:0#r7-1`(i0-r6-02・i0-r6-04)と `作る:0#7`(i0-r6-01・i0-r6-03)を同時に)

(見回りのたびに追記する)
