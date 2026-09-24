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


### 第 7 周の結果(run は 11:17 UTC ごろに止まった。台本の返り値 `status: 'escalate'` = 項目 0 ではリードへの戻し、L-436)

| 組 | 審査員 3 体の選択 | 通過(L-432) |
|---|---|---|
| 対 当方の現状 | 3/3 が新実装(32/32 対 8/32) | 通過 |
| 対 調査結果の側 | 3/3 が新実装(32/32 対 31/32。差は P0-3 の 1 場面) | 通過 |
| 批評家 | [止める] 2(**実装 2** = i0-r7-01(i0-r6-01 の続き 2 回目)・i0-r7-02(i0-r4-02 → i0-r5-01 の続き **3 回目**))、[直す] 3(場面集)、[示唆] 1 | **同じ理由 3 回 → リードへ戻す(L-436)** |

### 監査役(場面)r7-1 の出力(逐語。[止める] 0 で資料係へ進んだ。[聞く] 2 件はリードが下で答える)

- **br7-1-1 [聞く]**: P0-3 以外の4場面(p1-merge-by-time・p1-typed-events・p5-same-time-twice・p5-hand-over-order)の実際の入力・期待値は、要件の文だけからは定まらず、同じ実行のp3-<型>場面への「対象自身の応答」(run_battery.py target_types()、p3_results)から機械的に決まる(scenes.py TYPE_RULE、for_target_types)。委任文の監査観点「場面が振る舞いでなく作りの形を試していないか(期待の値が要件の文から独立に出せるか)」、および場面集の規則1「(値の場面は)エンジンを見ずに手計算・閉じた式で出した正解」「呼んだ結果を正解と突き合わせる」(正解は対象の振る舞いを見る前に決まっている、という前提)に照らすと、この4場面は「正解」自体が対象の別の場面での実行結果に依存する構造になっている。i0-r6-02(型固定によるバイアス)を除くための意図的な設計変更であることはROOTCAUSE_r7-1.mdに明記されているが、この設計(場面の具体的な中身が対象ごとに実行時に決まる)が委任文の「場面集は1周目の前に固定する」「期待の値が要件の文から独立に出せる」の要求を満たすと読んでよいかは記録に書かれておらず、リード/オーナーの確認が要る。
- **br7-1-2 [聞く]**: run_battery.py target_types() は、p3-<型>のSceneResultについて status=='ok' かつ受けた列が空でなく型が全部その型、だけを見て「対象の型」と判定し、値(価格・数量など)の正しさ(correctness=='正解と一致')は問わない。したがって、その型を受け取るが値が誤っている対象(該当p3場面がcorrectness='不一致')でも「型を持つ」と数えられ、p1-merge-by-time・p5-same-time-twice等の型構成に採用される。DEFINITIONS.md 23行目の「対象の型」の定義(受けた型が全部その型、であって値の一致は要求しない)には文言上は合致するが、値の誤りを持つ対象をそのまま他観点の型選定に使ってよいという判断が委任文・ROOTCAUSE_r7-1.mdのどこにも明記されておらず、意図した設計か確認が要る。

### 作業者 `作る:0#7` の返り(要点)

構造の変え方(逐語): (1) 履歴の答え DeliveredEvents が、読み出しの列の中での自分の場所 AnswerPlace を持つようにした。場所は、始まりの位置 first・歩幅 step・読み出しの時に届いていた数 delivered・history_limit が落とした数 dropped の 4 つ。誤りの種類は、名指した位置をその列の位置に戻して決める。まだ届いていない位置は FuturePositionError(LookAheadError の子)。届いたが答えの外の位置は OutsideAnswerError。落とした事象の位置は DroppedPositionError。何も届いていない所は BeforeFirstEventError。負の添字もこの規則に入れ、区間の境界は 1 度だけ読む。場所を言えない空の答えは断る。(2) 送り手の値の型の判定は、核の全体で本当の型だけで行う(values.is_a = issubclass(type(x), C))。外来の値を受ける決まりは values.scalar の 1 つにまとめた(組み込みの子・numpy の真偽・数の塔)。断るときは、その所の誤りの型で、本当の型の完全な名前を書く。

試験(逐語): 全試験: 1 failed, 3808 passed, 6 skipped, 1 warning in 518.96s (0:08:38)。落ちたのは tests/bt/critic/item_0/test_i0r2_battery_p5_grading.py::test_single_input_form_of_hand_over_order_agrees_with_keeping_one_input_in_order の 1 件だけ。/ 項目 0 と批評家の試験(最後の文言の直しの後にも回した): 1 failed, 865 passed, 2 skipped in 81.62s。落ちたのは同じ 1 件。原因は場面集の側: 批評家の試験の 72 行目 `LiquidationEvent(... price=d["price"] ...)` が、場面係がこの周に書き換えた scenes.py の場面データ(`git diff --stat 6e6d6ae -- tests/bt/battery/item_0/scenes.py` → 228 行が変わった)で KeyError: 'price' になる。src/bot/bt/core と作業者の試験の側で起きたものではない。第 6 周の批評家の試験のうち、実装の側の test_i0r6_past_answer_names_undelivered.py は 6 件とも通る(直す前は 4 failed, 2 passed)。場面集の側の test_i0r6_battery_p5_measures_order_not_types.py も、全試験の回では通っている。場面集の実行(最後の 1 回): run_battery.py --target new_impl → 32 場面すべて「正解と一致・2 回の実行で同じ」。mutant → 31 場面が一致、1 場面が不一致。current_impl → 一致 8、対応なし 23、不一致 1。

リードに聞くこと(逐語): ["リードが作業木を途中でコミットした(6e6d6ae → e73d98d → bfc207a → 9514c3c → 4082053)ため、この周の差分は `git diff 6e6d6ae` で見てほしい。この周の作業の前の版は 6e6d6ae で、ROOTCAUSE.md の行番号もこの版のもの。", "tests/bt/critic/item_0/test_i0r2_battery_p5_grading.py が、場面係のこの周の scenes.py の書き換えで KeyError: 'price' になって落ちる。試験自身が場面データの鍵を前提にしているため。直すのは場面係か次の周の批評家になる。作業者は変えていない。"]

### 資料係 `表:0#7` の注記(要点)

手順 1: 新実装の adapter(tests/bt/battery/item_0/adapters/new_impl.py)は既にある(場面係が r7-1 で更新し、コミット 4082053 に入っている)。資料係は変えていない。使っているのは bot.bt.core の公開された名前 18 個だけ(すべて __all__ にあり、_ で始まる名前は 0 個)。src/bot/bt は変えていない(git diff --stat HEAD で差分なし)。

相手の道具の結果の再利用: しなかった。場面集の指紋は 3e13290eb361…(この周)で、第 6 周の 5eb3e2f76129… と違うので、40 対象すべてを走らせ直した(logs/scene_set_fingerprint.txt)。

走行: 40 対象(新実装・当方の現状・試金石・動かせた調査の道具 36・書き直し 1)を全 32 場面に通し、runner が各場面を 2 回、別々の adapter で走らせた。40 対象すべて rc=0。試金石の --check の出力は「changed scenes: ['p4-received-time']」と「OK」。

提出前の吟味(資料係・表):
- 一致の数を数え直した。recount.py が runs/*.tsv から make_tables.py を使わずに観点ごとの数を数え直し、6 枚の表の数の行と突き合わせた。不一致 0。新実装: 正しさ 32/32、再現 32/32。当方の現状: 正しさ 8/32(P0-1 1/3、P0-2 2/4、P0-3 1/11、P0-4 1/3、P0-5 1/3、P0-6 0/3、P0-7 2/5)、再現 32/32。調査結果の側(寄せた行): 正しさ 31/32(P0-3 が 10/11)、再現 32/32。試金石: 正しさ 31/32(P0-4 が 2/3)、再現 32/32。
- 全対象を全場面に通した。結果なしの場面の注記には、何が出たかと、その対象を全場面に 2 回ずつ通した所要の秒数(run_all.log の実測)を書いた。調査の側で結果なしになったのは 17 場面。書き直しの対象 1 件が「機構を実装していない」と返したもの 17 件と、例外が 1 件(p6-place-then-cancel、所要 104 秒。時間の打ち切りではない)。どの道具が、何時に、を書いた記録は materials にだけ置いた(commands.txt・survey_failures.tsv)。動かせなかった候補 16 件は、候補ごとの欠けとして、理由の種類ごとの件数を表の注記に書いた。
- 表の注記に道具を特定できる語が無いかを確かめた。165 語の型で grep した。当たったのは「書き直」2 件だけ(調査の側の 2 枚の同じ集計の注記で、どの道具かは言っていない)。時刻は 6 枚とも 0 件。
- 組ごとの 2 通りの表を md5 で確かめた。current・survey・mutant の 3 組とも違う(md5sum_pairs.txt)。よって、どの組も L-422 の「同一は同等で通過」には当たらない。
- 記録はすべて materials に保存した。保存したもの: 走らせた台本、表を作るスクリプト、runs、ログ、対応表(mapping.tsv)、寄せた行の中身(survey_best.tsv)、結果なしの詳細、md5、数え直し、grep の出力、pytest の出力(58 passed)、最後の状態。
- 迷っている点: 調査の側の行で正解と一致しなかったのは p3-mixed-one-run だけ。この場面は、動かせた対象のどれでも最良が「対応なし」だった。
- この周は 表_*.md を 1 回しか作っていないので、stale/ は空。
- 実データから出た数値は入れていない(場面はすべて合成)。

### 批評家 `批評:0#7` の出力(逐語)

- **i0-r7-01 [止める]** 相手=実装 repeat_of=i0-r6-01 場当たり=False: 後ろ向きの答え(ans[::-1]、place.step == -1、新しい順)の負の区間の境界が、まだ届いていない位置だけを名指しても、黙って空を返す。window.py 40-43 行の POSITION_RULE の説明と contract.py 45-47 行は「負の区間の境界は最新から数え、tuple と同じく答えの端で切る(切り詰めは答えの中にしか届かない)」と言うが、これは配達順の答えでだけ正しい。後ろ向きの答えでは負の境界は最も古い側から数え、位置 -1 は r[0](最新)より新しい側 = まだ届いていない事象である。第 7 周は負の添字を名指した位置で決める規則に入れた(r[-5] は FuturePositionError)が、負の区間の境界は符号だけで切り詰める(_check_bounds は b >= 0 の境界しか見ない、window.py 178-185 行。切り詰めは 169 行の tuple.__getitem__)。前向きの鏡像 a[4:5] は FuturePositionError で止まるのに、r[-6:-5]・r[-6:-4]・r[-5::-1]・r[-6:-5:-1] は () で素通りする。固定した要件 P0-4 の測り方「素通りしたら不合格」と場面の正解「空の結果…は素通り」に合わない。作業者は根本原因 A の構造 2 で「負の区間の境界が切り詰められる決まりも変えない(切り詰めは答えの中にしか届かない)」と書き、後ろ向きの答えで切り詰めた先が未来になることを確かめず、神託の試験も負の区間の境界を試していない(同じ根の全箇所の探し漏れ)。添字と非負の境界の種類は、独立の神託(6 種、計 21,888 の名指し)で誤り 0 件で、そこは直っている。
  - 根拠: PYTHONPATH=src python3 <scratchpad>/bt/item0_r7_critic_probe_backward_negslice.py → 'a[4:6] -> FuturePositionError' / 'r[-5] -> FuturePositionError' / 'r[-6:-5] -> returned []' / 'r[-6:-4] -> returned []' / 'r[-5::-1] -> returned []' / 'r[-6:-5:-1] -> returned []'。試験 tests/bt/critic/item_0/test_i0r7_backward_answer_negative_bounds.py → 4 failed。src/bot/bt/core/window.py 40-43・169・178-185 行、src/bot/bt/core/contract.py 45-47 行。神託 <scratchpad>/bt/item0_r7_critic_probe_kind_oracle_keptcoords.py → seed 1〜6 とも wrong 0
- **i0-r7-02 [止める]** 相手=実装 repeat_of=i0-r5-01 場当たり=False: OrderRequest.extra の Fraction は同じ物のまま路を渡り、送り手が後の呼び出しから書き換えると、取引所は着いた時刻に書き換えた値を読む。values.py 64-66 行の _SCALARS は Fraction を不変の値の組に入れ、_plain_scalar(140 行)は同じ物を返す。fractions.Fraction は Python で書かれた class で __slots__ ('_numerator', '_denominator') は代入できる。values.py の説明の決まり「路を渡る物は送り手の変わりうる状態を持たない」を破り、路の遅れを飛ばす道になる(i0-r4-02・i0-r5-01 と同じ根)。同じ試しで FrozenDict は取引所の側で作り直されていて書き換えは届かず、Fraction だけが届いた。第 7 周の根本原因 B は「本当の型で判定する」を直したが、_SCALARS の各型の値が本当に不変かを確かめていない。Fraction の子は数の塔として float に直すのに Fraction そのものは直さずに持つ食い違いもある。
  - 根拠: PYTHONPATH=src python3 <scratchpad>/bt/item0_r7_critic_probe_frozen_private.py → 'strategy holds request 139718587063472 extra d type FrozenDict' / 'venue saw at 1700000010000000000 request 139718587063584 extra {'d': {'a': 1}, 'f': Fraction(7, 3)}'(送ったのは Fraction(1, 3)、遅れ 10 秒、T0+1 秒で ._numerator = 7)。試験 tests/bt/critic/item_0/test_i0r7_fraction_in_extra_stays_live.py → 1 failed('assert Fraction(999, 3) == Fraction(1, 3)')。src/bot/bt/core/values.py 64-66・140 行
- **i0-r7-03 [直す]** 相手=場面集 repeat_of=i0-r6-04 場当たり=False: LEAN の再現は、同じ銘柄に約定の Tick の購読と TradeBar の購読を同時に持たせるが、利用者がこの組を作れる根拠の行が注釈に無い。opponents/repro_lean52.py 89-115 行の _sources は、場面の事象の型ごとに data_manager_add で購読を 1 つずつ作る(約定 → Tick、足 → TradeBar、資金調達 → MarginInterestRate)。注釈(repro_engines/lean52.py 150-163 行)は利用者の経路を AddCryptoFuture → AddSecurity<T> と書くが、その経路の型は LookupSubscriptionConfigDataTypes が解像度から決め(DataManager.cs 626 行、747-773 行、768 行 LeanData.GetDataType(resolution, tickType))、約定の型は Tick か TradeBar の片方になる。この組が p1-typed-events・p1-merge-by-time の再現の正解と一致を決めている。委任文 §3「再現の根拠は…注釈に 1 対 1 で書く。一次資料に無い工夫を足さない」に当たる。調査結果の側を強くする向きで、この 2 場面の最良は Basana でも正解と一致なので表は変わらず、[直す] とする。
  - 根拠: <scratchpad>/bt/item0_r7-1_scenekeeper_DataManager.cs 626 行 'dataTypes = LookupSubscriptionConfigDataTypes(symbol.SecurityType, resolution ?? _algorithm.UniverseSettings.Resolution, symbol.IsCanonical());'、768 行 '.Select(tickType => new Tuple<Type, TickType>(LeanData.GetDataType(resolution, tickType), tickType))'。tests/bt/battery/item_0/opponents/repro_lean52.py 89-115 行。docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/round_7/materials/survey_best.tsv の p1-merge-by-time・p1-typed-events
- **i0-r7-04 [直す]** 相手=場面集 repeat_of=None 場当たり=False: 検討表の共通の決まりの文(opponents/CONSIDERED.md 15 行)に、第 r7-1 回で成り立たなくなった前提「p1-merge-by-time・p5-same-time-twice・p5-hand-over-order は資金調達か清算を含む」が残る。第 r7-1 回から、この 3 場面の型は対象の型から runner が作る(scenes.py 182-201・403-419 行、DEFINITIONS.md 12 行)。場面係は P0-1・P0-5 の冒頭の文と 11 の行を直したが(ROOTCAUSE_r7-1.md 47・111 行)、この共通の文を直していない(同じ根の全箇所の探し漏れ)。
  - 根拠: grep -n '資金調達か清算' tests/bt/battery/item_0/opponents/CONSIDERED.md → 15 行。tests/bt/battery/item_0/scenes.py 182・403・413 行、DEFINITIONS.md 12 行
- **i0-r7-05 [直す]** 相手=場面集 repeat_of=None 場当たり=False: 「受け取れた時刻 ≤ 今」を注文の通知について測る場面が無い。固定した要件 §1 の行の事象の型は注文の受付/拒否/約定の通知を含むが、P0-4 の 3 場面は市場の事象だけで、p4-received-time の受け取りの遅れも市場の事象だけ。通知の遅れがあるとき、通知が届く前の呼び出しで戦略が注文の見え方(約定済みの数量・未決の数)から取引所の出来事を読めてしまう対象を、今の場面集は見分けない(P0-6 は遅れ 0 の既定で測る)。新実装は正しく扱う(試しで確かめた)。P0-4 の固定した測り方の外なので [直す] に留める。
  - 根拠: PYTHONPATH=src python3 <scratchpad>/bt/item0_r7_critic_probe_notice_latency_view.py(通知の遅れ 5 秒)→ '(4, 'TradeEvent', None, 0.0, 1)' / '(5, 'OrderFillEvent', None, 1.0, 0)'。tests/bt/battery/item_0/DEFINITIONS.md の P0-4 の 3 場面の入力
- **i0-r7-06 [示唆]** 相手=場面集 repeat_of=None 場当たり=False: p4-future-read-attempt は、過去を読む手段を持たない対象に、存在しない引数で書いた呼び出し(形 no_means)の TypeError で正解と一致を与える。調査結果の側の P0-4 の行は場面ごとに最良を寄せるので、過去を読める対象の p4-visible-at-step と、過去を読めない対象の p4-future-read-attempt が 1 行に並び、「過去を読めて未来の読み出しは止まる」対象が調査結果の側に無くても 3 / 3 になる。新実装に不利な向きなので害は無いが、表の P0-4 の意味を定義の注記に 1 文書いておくとよい。
  - 根拠: tests/bt/battery/item_0/survey_results/opp_basana.tsv の p4-future-read-attempt: 'exchange.get_bid_ask(pair, 5 本目の時刻) TypeError: Exchange.get_bid_ask() takes 2 positional arguments but 3 were given'。同じ場面で正解と一致は opp_basana・opp_predictivedev_tradesim・opp_quantcore で、どれも p4-visible-at-step は正解と一致でない

### 審査員 6 体の出力(逐語。左右の割り当ては `round_7/JUDGES.md`)

- 盲検:0#7:current0: 選択 **右** — 表から数え直した「正解と一致」の数(行 A / 行 B)は次のとおり。P0-1: 1/3 と 3/3。P0-2: 2/4 と 4/4。P0-3: 1/11 と 11/11。P0-4: 1/3 と 3/3。P0-5: 1/3 と 3/3。P0-6: 0/3 と 3/3。P0-7: 2/5 と 5/5。合計は 8/32 と 32/32 で、表の計の欄と合っている。

7 観点すべてで B が A と同じか上回り、実際には全観点で B が上回った。場面の数が多い P0-3(11 件)を除いても、A は 7/21、B は 21/21 で、差は変わらない。

- A の P0-3: 一致は p3-bar の 1 件だけ。残りの 10 場面は「対応なし」。
- A の P0-1(p1-merge-by-time・p1-typed-events)と P0-5(p5-same-time-twice・p5-hand-over-order): 定義上、最低 2 種の型が要る場面である。A は p3 で足しか届けていないため「対応なし」になっている。
- A の P0-4: p4-future-read-attempt が「不一致」。every_attempt_stopped_by_error が false で、未来を読もうとした試しを止めていない。ただし future_value_obtained も false なので、値の漏れは表に出ていない。
- A の P0-6: 3 場面すべてが「対応なし」。

再現の欄は、両者とも全観点で「2 回の実行で同じ」(32/32)。再現性には差が無い。

以上から、正しさで B が明確に上回り、再現では同等なので、B(右)を選ぶ。
- 盲検:0#7:current1: 選択 **左** — 正しさ(正解と一致の数、表のセルから数え直した値): 行 A は全観点で満点(P0-1 3/3、P0-2 4/4、P0-3 11/11、P0-4 3/3、P0-5 3/3、P0-6 3/3、P0-7 5/5、計 32/32)。行 B は P0-1 1/3(p1-one-call-per-event のみ。merge-by-time と typed-events は対応なし)、P0-2 2/4(event-time-exact と one-ns-apart。iso-utc と iso-offset は対応なし)、P0-3 1/11(p3-bar のみ。他 10 件は対応なし)、P0-4 1/3(visible-at-step。received-time は対応なし、future-read-attempt は不一致 = every_attempt_stopped_by_error が false)、P0-5 1/3(same-stream-order のみ)、P0-6 0/3(3 件とも対応なし)、P0-7 2/5(fill-model-swap と cost-model-swap。latency-model-swap・cost-per-unit・account-swap は対応なし)、計 8/32。数え直した値は表の要約行と一致した。観点ごとに見ても、7 観点のうち A が B を下回る観点は 1 つも無く、7 観点すべてで A が上回る(場面数の多い P0-3 を除いても 6 観点すべてで A が上)。B には不一致が 1 件(p4-future-read-attempt。未来の値を取れてはいないが、読み出しの試みがエラーで止められていない)あり、A には不一致も対応なしも無い。再現(2 回の実行で同じ): A・B ともに全観点で満点(各 32/32)なので差は無い。したがって正しさの差で行 A が優れる。
- 盲検:0#7:current2: 選択 **右** — 表の各セルを数え直した結果、「正解と一致」の数は見出しの集計表と同じだった。行 B(右)は 7 観点すべてで行 A を上回るか、同じである。観点ごとに行 A / 行 B の順で次のとおり。
- P0-1: 1/3 と 3/3。A は p1-one-call-per-event だけ一致し、p1-merge-by-time と p1-typed-events は対応なし。
- P0-2: 2/4 と 4/4。A は p2-iso-utc と p2-iso-offset が対応なし。
- P0-3: 1/11 と 11/11。A は p3-bar だけ一致し、残り 10 場面は対応なし。
- P0-4: 1/3 と 3/3。A は p4-received-time が対応なし。p4-future-read-attempt は不一致(every_attempt_stopped_by_error=false、future_value_obtained=false)。
- P0-5: 1/3 と 3/3。A は p5-same-time-twice と p5-hand-over-order が対応なし。
- P0-6: 0/3 と 3/3。A は 3 場面とも対応なし。
- P0-7: 2/5 と 5/5。A は p7-latency-model-swap、p7-cost-per-unit、p7-account-swap が対応なし。
計は 8/32 と 32/32。

どの観点でも B は全場面が正解と一致しているので、場面の多い P0-3 を除いても結論は変わらない。A が B より上の場面は 1 つも無い。A の欠けは大半が対応なし(能力が無い)で、不一致は P0-4 の 1 件だけである。

再現(2 回の実行で同じ)は、A と B とも全観点で 32/32(P0-1 3/3、P0-2 4/4、P0-3 11/11、P0-4 3/3、P0-5 3/3、P0-6 3/3、P0-7 5/5)。この点に差は無い。

よって、正しさでは B が全観点で優れ、再現では同等なので、B を選ぶ。
- 盲検:0#7:survey0: 選択 **右** — 表から自分で数え直した。正しさ(正解と一致の数)は、P0-1: A 3/3・B 3/3、P0-2: A 4/4・B 4/4、P0-3: A 10/11・B 11/11、P0-4: A 3/3・B 3/3、P0-5: A 3/3・B 3/3、P0-6: A 3/3・B 3/3、P0-7: A 5/5・B 5/5。計は A 31/32、B 32/32 で、表の集計と一致する。再現(2 回の実行で同じ)は、7 観点すべてで A・B とも満点(32/32)で差は無い。違いは P0-3 の 1 場面だけ。p3-mixed-one-run は 6 種の市場の事象(約定・板の写真・板の差分・足・資金調達・清算)を 1 回の実行に混ぜ、型と時刻の列を正しく出せるかを見る値の場面である。ここで A は「対応なし」、B は「正解と一致」だった。A は 6 種を 1 種ずつ流す能力の場面(p3-trade〜p3-liquidation)では全部一致しているので、6 種を 1 本の流れにまとめる所で能力が欠けていることになる。他の 6 観点は両者とも全場面が一致で同じ。つまり B が勝る観点は 1 つ(P0-3)で、A が勝る観点は 1 つも無い。場面の多い P0-3 に引きずられたのではなく、差が出た唯一の観点で B が上だったので B を選ぶ。ただし差は 1 場面分と小さい。また、表の各行は複数の対象(計 37)のうち最も良い結果を寄せたもので、p2-iso-utc や p6-place-then-cancel などでは行の中の一部の対象が結果なしだった(注記より)。この注記がどちらの行のものかは表から区別できず、比較の材料にはしていない。
- 盲検:0#7:survey1: 選択 **左** — 表から観点ごとに数え直した。正しさ(正解と一致)は次のとおり。P0-1: A 3/3、B 3/3。P0-2: A 4/4、B 4/4。P0-3: A 11/11、B 10/11。P0-4: A 3/3、B 3/3。P0-5: A 3/3、B 3/3。P0-6: A 3/3、B 3/3。P0-7: A 5/5、B 5/5。計は A 32/32、B 31/32 で、表の集計の行と一致する。再現(2 回の実行で同じ)は、7 観点すべてで A・B とも満点(計 32/32 ずつ)で、差は無い。

差が出たのは P0-3 の p3-mixed-one-run の 1 場面だけ。B はこの場面が「対応なし」(再現は 2 回で同じ)、A は「正解と一致」。この場面の定義(DEFINITIONS.md)は「約定・板の写真・板の差分・足・資金調達・清算の 6 種を 1 回の実行に混ぜて入れ、型と時刻の列が入力どおりに出るか」である。B は 6 種を 1 種ずつ入れる場面(p3-trade〜p3-liquidation)ではすべて正解と一致したが、6 種を 1 本の流れに混ぜる場面には対応していない。A は混ぜた場合も正しく流した。

ほかの 6 観点は、両方とも全場面で正解と一致し、2 回の実行でも同じだった。どちらかが劣る観点は無い。P0-3 は 7 観点のうち 1 つで、場面の数が多い観点ではある。ただし A が劣る観点は 1 つも無いので、場面の数の重みを除いても A が上と言える。再現は同等で、正しさは P0-3 の 1 観点で A が上。以上から A(左)を選ぶ。

注: 表の注記によると、各行は複数の候補の最も良い結果をまとめたものである。どちらの対象がこうした行なのかは表からは分からないため、判定には使っていない。
- 盲検:0#7:survey2: 選択 **右** — 表から観点ごとに数え直した。正しさ(正解と一致の数)は、行 A が P0-1 3/3、P0-2 4/4、P0-3 10/11、P0-4 3/3、P0-5 3/3、P0-6 3/3、P0-7 5/5 で計 31/32。行 B は全観点で満点、P0-3 も 11/11 で計 32/32。再現(2 回の実行で同じ)は、A も B も全 7 観点で満点(32/32)で差は無い。
差が出たのは P0-3 の 1 場面 p3-mixed-one-run だけ。A は「対応なし」、B は「正解と一致」だった。定義によると、この場面は 6 種の市場の事象(約定・板の写真・板の差分・足・資金調達・清算)を 1 回の実行に混ぜて入れ、(型, 時刻)の列が入力どおりになるかを見る。A は 6 型を 1 種ずつ入れた場面(p3-trade〜p3-liquidation)ではすべて正解と一致したが、6 種を同じ流れに載せる場面には対応していない。B はこれができる。
残りの 6 観点(P0-1・P0-2・P0-4・P0-5・P0-6・P0-7)は両者とも全場面が正解と一致かつ再現も一致で、差は無い。
場面の数の多い観点に引きずられないよう観点ごとに比べた。その結果、1 観点(P0-3)で B が上回り、B が劣る観点は 1 つも無い。したがって B(右)を選ぶ。
ただし差は 1 場面だけで、両者はほぼ同じ水準である。
なお、注記によると、多くの場面で行に寄せた対象の一部が「結果なし」だった。行の値はその場面で残りの対象の最も良い結果である。どちらの行に付いた注記かは表の本文から特定できないため、比較には使っていない。

## リードの戻しの処置(L-436。2026-09-24 11:20〜 UTC)

- 根本原因の読みと設計の直し: `docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/round_7/LEAD_DESIGN.md`(§2 = 「保つ物の一覧」を書く設計の向きが逆 / §3 = 核が作り直した物しか渡らない・全ての名指しを 1 つの座標に戻す・敵対者の試験を全格子で先に書く / §4 = 監査役(場面)r7-1 の [聞く] 2 件への答え / §5 = 手順の直し 3 点)。
- 台本・委任文・検査の直し(委任文の版 c5e13b09346c): (1) 監査役(場面)・批評家の repeat_of を「同じ根本原因の族」で必ず埋める(schema で必須)。(2) 場面係の直しの前に「正の定義」を書かせ、定義だけを監査役(`監査役(定義):`)に先に通す(`defineThenAudit`。定義の監査の [止める] も同じ鎖で数える)。(3) 作業者・場面係の吟味に (6)「直した規則の入力の空間を全格子で列べる敵対者の試験を先に書く」を足した。(4) 委任文 §3 4 に「リードに戻して設計を直したあと、直した族の鎖は 0 から数え直し、直していない族は引き継ぐ」を書いた。
- 8 回目の鎖の引き継ぎ(上の規則で決めた): 実装の側 = i0-r4-02 → i0-r5-01 → i0-r7-02 の族(路を渡る物)は設計を直したので 0 から。i0-r6-01 → i0-r7-01 の族(答えの外の名指し)は設計 §3.2 を渡すが鎖は 2 のまま引き継ぐ(第 8 周で続けば 3 = 戻し)。場面集の側 = i0-r6-02(P0-5 の型の欠け、第 7 周の場面係が直した)・i0-r7-03(i0-r6-04 の続き、[直す])・i0-r7-04・05 を第 8 周の場面係に渡す。battery_chain は 7 回目の場面集の監査の [止める](br6-1-1・br6-2-1、いずれも 1)を引き継ぐ。
- 候補 35(権限の分類器の拒否、br6-3-1): 8 回目の場面係への指示に「報告の『リードに聞くこと』に独立の項目として書く」を入れる。リード自身の試行は 8 回目の run と重ならない時機に行う(場面集の指紋が変わるため)。
