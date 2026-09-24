# 項目 0「核」第 2 周 — 批評家の記録

委任文: `docs/DATA/delegations/20260923_backtest_env_prompt.md`(指紋 `20260923_backtest_env_prompt.md@f9fe736bfcff`、`sha256sum | cut -c1-12` で確かめた)。
合意した完了の形(委任文 §0 の逐語): 「**すべてが調査結果以上の信頼性と再現性に優れたものにすること。**」
手元に置いたもの: 固定した要件 `docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/REQUIREMENTS.md`、場面集 `tests/bt/battery/item_0/scenes.py`(`python3 gen_definitions.py --check` → `OK`)、検討表 `tests/bt/battery/item_0/opponents/CONSIDERED.md`(`python3 scripts/check_bt_considered.py …` → `OK 誤り 0 件`)、この周の実行の記録 `round_2/materials/runs/*.tsv`、作業者の `round_2/ROOTCAUSE.md`、調査報告 `docs/DATA/SCAN_2026-09-21_tools.md` の該当行。

## 0. 構造の変化(前の周から)

あり。`git diff HEAD --stat -- src/bot/bt/core tests/bt/item_0` → 12 本、715 行足し 332 行削り。待ち行列の鍵は `(時刻, 路の段, 受け取りの時刻, 位置)`(`engine.py:447-468`、`ordering.py:110-154`)、取引所の台帳と戦略の見る注文は事実を持つ形(`engine.py:138-157`、`api.py:134-165`)、時刻の引数は `_time_arg` の 1 か所(`api.py:456-464`)。作業者の申告どおり。

## 1. 前の周の指摘を自分で確かめ直した結果

コマンド: `PYTHONPATH=src python -m pytest tests/bt/critic/item_0 tests/bt/item_0 tests/bt/battery/item_0` → `269 passed in 2.44s`(この周の試験を足す前)。
前の周の批評家の試験で、作業者が「試験自身の誤り」と報告したものは無い(全部通っている)。取り下げるものは無い。

| id | 確かめ方 | 結果 |
|---|---|---|
| i0-r1-05 | `test_r5c1_outbound_channel_fifo.py` 通過。加えて自分の乱数の試験(`test_i0r2_channels_random.py`、150 種、発注と取消の遅れを乱数に)で、取引所に着いた要求が送った順の部分列であることを確かめた → 通過 | 直った |
| i0-r1-06 | `test_r5c1_notice_channel_fifo.py` 通過。乱数の試験で、戦略が受けた通知の列 = 遅延の模型の `notice_delay_ns` が呼ばれた順(= 取引所が出した順)を 150 種で確かめた → 通過 | 直った |
| i0-r1-07 | `test_r5c1_ledger_accepts_contradictions_after_unknown.py` 3 件通過。`engine.py:199-264` は事実に照らして検める | 直った |
| i0-r1-08 | `test_i0r1_since_future_is_silent.py` 通過。`api.py:389-391` で両方の時刻の引数が `_time_arg` を通る。この周の実行の記録でも `since_ns` → `LookAheadError`(`runs/new_impl.tsv` の p4-future-read-attempt) | 直った |
| i0-r1-09 | `test_i0r1_state_unknown_lost_on_cancel_reject.py` 通過。乱数の試験で、通知を全部届けた後の戦略の見る状態が台帳と一致することを 150 種で確かめた → 通過。**ただし同じ「事実」の作りに別の欠陥がある(i0-r2-02)** | 直った(別の欠陥あり) |
| i0-r1-10 | `test_i0r1_same_stream_cross_type_reordered.py` 通過。独立に書いた規則の読み(別々の入力の先頭を (取引所の時刻, TYPE_ORDER, 名前) で併合、1 本の入力はその順、戦略へは (受け取りの時刻, 併合の位置))と、遅延 0 の実行を 300 種で突き合わせた → 取引所の側・戦略の側とも一致 | 直った |
| i0-r1-11 | `test_i0r1_zero_length_bar_with_range.py` 通過(`events.py:256-268`) | 直った |
| i0-r1-12 | `test_i0r1_feed_delay_reorders_one_stream.py` 通過。乱数の試験(配信の遅れ 0/1/3 ms、記録された受け取りの時刻も揺らす)で 1 本の入力が受け取りの順で届くことを 150 種で確かめた → 通過 | 直った |
| i0-r1-13 | `test_i0r1_end_time_not_validated.py` 2 件通過(`engine.py:408-419`、秒の値は `engine.py:507-513` で最初の一歩で止まる) | 直った |
| i0-r1-14 | 場面集は前の周から変わっていない(`git log -1 -- tests/bt/battery/item_0` → 67c1136、`git status --short tests/bt/battery` → 空)。`scenes.py` の p4-future-read-attempt の導き方は今も「例外・空の結果・拒否のどれか」 | **直っていない → i0-r2-05** |
| i0-r1-15 | 同上。P0-5 の 3 場面の正解は今も `{same_order_in_two_runs: True}` / `{distinct_orders: 1}` / `{prices: [100.0, 101.0]}` | **直っていない → i0-r2-06** |
| i0-r1-16 | `CONSIDERED.md:107` の 70 PineForge の行は変わっていない | **直っていない → i0-r2-08** |
| i0-r1-17 | `grep -c unmapped CONSIDERED.md` → `0`。`sed -n '/# unmapped/,$p' pool.tsv \| tail -n +2 \| cut -f1 \| sort \| uniq -c` → `1 # P0-2 / 74 # P0-3 / 1 # P0-4 / 10 # P0-5 / 4 # P0-7` | **直っていない → i0-r2-09** |

作業者の `ROOTCAUSE.md` §G は、i0-r1-14〜17 を場面係の持ち物として直していないと書いている(作業者の持ち物の外なのは正しい)。場面係はこの周に起こされておらず、場面集と検討表は前の周のまま。この 4 件は同じ原因のまま 2 周目に入った(場面集への指摘の数えは台本が行う)。

前の周の [直す]・[示唆] は、渡された一覧(i0-r1-05〜17)に無い。前の周の記録 `round_1/CRITIC.md` §1 の i0-r1-02・04([直す])は直っており、付け直すものは無い。

## 2. この周の指摘

### [止める] i0-r2-01 1970 年より前の時刻で、注文と通知が 1970-01-01 に飛ぶ(repeat_of: なし)

時刻は int64 のナノ秒で、`validate_nanos` は負の値(1970 年より前)を受け、`CoreEngine` もその事象を受けて走る。ところが要求の路と通知の路の FIFO の揃えは「前の要素なし」ではなく 0 から始まる(`engine.py:439-440` の `self._last_outbound = 0`・`self._last_notice = 0`)。`max(送った時刻 + 遅れ, 0)`(`engine.py:644・651`)と `max(取引所の時刻 + 遅れ, 0)`(`engine.py:783`)で、負の時刻に出した注文は 0 に着き、その受付も 0 に届く。例外は出ず、値はもっともらしい。黙って誤った時刻を返す = 信頼性を崩す。
根拠: `tests/bt/critic/item_0/test_i0r2_negative_time_jumps_to_epoch.py` の出力 `AssertionError: order sent at -10000000000 reached the venue at [0]`。

### [止める] i0-r2-02 取消を 2 つ出していると、1 つ目の拒否で「取消の答え待ち」が消える(repeat_of: なし)

`PENDING_CANCEL` は「取消を送り、答えがまだ無い」(`api.py:116`)で、事実 `cancel_pending` は注文ごとに bool 1 つ(`api.py:163`)。`cancel` で立ち(`api.py:230`)、どの取消への答えでも倒れる(取消の拒否 `api.py:280`、取消の状態不明 `api.py:298`)。取消を 2 つ出し、1 つ目が拒否されると、2 つ目にまだ答えが無いのに戦略には OPEN・`cancel_pending=False` が見え、そのあと 2 つ目で CANCELED になる。前の周の i0-r1-09 の直し(事実を持つ形)は、「答え待ちの取消が何件あるか」を持てていない。
根拠: `test_i0r2_second_cancel_in_flight_shown_open.py` の出力 `(t - T0 ns, state, cancel_pending) = [(5000000, 'OPEN', False), (5500000, 'OPEN', False), (6000000, 'OPEN', False)]`(最後は CANCELED)。

### [止める] i0-r2-03 `history_limit` を付けると、同じ履歴への 2 つの問いが違う答えを返す(repeat_of: なし)

`StrategyContext.__init__` の説明(`api.py:326-328`)は、型ごとの履歴は「`visible_events` と同じもの・同じ順で、`visible_events(event_type)` を速くするだけ」と約束する。エンジンは全体の履歴と型ごとの履歴を別々の周期で切り詰める(`engine.py:604-606・630-636`)。そのため `visible_events(BAR)` と「`visible_events()` から足を抜き出したもの」が食い違い、どちらも切られたことを知らせない。`since_ns` の窓が残した範囲より前に及ぶときも、黙って短い答えを返す(`api.py:406-417`)。
根拠: `test_i0r2_history_limit_views_disagree.py` の出力 `[(7000000, 'BAR', 0, 1), (7000000, 'TRADE', 3, 6), (8000000, 'BAR', 0, 1)]`(時刻, 型, 全体から抜いた件数, 型で引いた件数)。

### [止める] i0-r2-04 資料係の adapter が、調査結果の側の道具の既定の拒否の仕組みを切っている(repeat_of: なし)

p3-notice-rejected(現金 1,000 円で 100 万円の成行)で、新実装の adapter は自分で書いた現金の口座 `_CashAccount` を口座の口に差し、拒否の理由をその口座が作る(`tests/bt/battery/item_0/adapters/new_impl.py:191-221・311-316`)。一方、QuantCore の adapter は全場面で道具の既定の危険の上限を**切って**から走らせる(`opponents/quantcore_adapter.py:48-50` `limits = qc.RiskLimits(); limits.enabled = False`)。道具の既定は `enabled: True`(下の実測)。既定のまま走らせると正解と一致し、adapter の設定では不一致になる。新実装には拒否の仕組みを adapter が書き足し、相手には既定の拒否の仕組みを外している = 新実装だけ有利・相手が不利になる呼び方。この場面の調査結果の行は別の道具の一致で埋まっているので表の値は変わらないが、adapter が公平でないこと自体が場面集の規則(場面が新実装に有利な範囲に偏っていないか)と委任文 §3「資料係の adapter」の点検に反する。他の adapter にも既定を外した設定が無いかを全部見直す必要がある。
根拠(実測。QuantCore の隔離した環境の python で、adapter の `set_risk_limits` に渡す上限の `enabled` だけを替えた。スクリプトは scratchpad の `bt/i0_r2_critic/quantcore_default_limits.py`):
```
RiskLimits の既定: {'enabled': True, 'max_leverage': 2.0, 'max_loss_pct': 0.5, 'max_order_value': 0.0, 'max_position_pct': 0.2}
limits.enabled = False -> output={'notices': ['filled']}   (adapter の設定。表では 不一致)
limits.enabled = True  -> output={'notices': ['rejected']} (道具の既定。正解と一致)
```

### [止める] i0-r2-05 p4-future-read-attempt の正解が固定した要件より弱いまま(repeat_of: i0-r1-14)

`scenes.py` の導き方は今も「例外・空の結果・拒否のどれか」。要件(`REQUIREMENTS.md:20`)は「実行時エラーか型エラーで止まるか(素通りしたら不合格)」。この周の実行でも、qf-lib は `get_price(..., 5 本目の日 + 1 日) -> [100.0, 101.0, 102.0, 103.0]`(黙って切り詰めた)で正解と一致、zipline-reloaded は `data.current(asset,'close') -> 102.0`・窓を伸ばして `[103.0]` で正解と一致(`round_2/materials/runs/opp_qf_lib.tsv`・`opp_zipline_reloaded.tsv`)。検討表の P0-4 の「動かせた候補」は qf-lib 1 件(`CONSIDERED.md:90`)で、その一致がこの弱い正解に依っている。

### [止める] i0-r2-06 P0-5 に「規則どおりの順」を測る値の場面が無く、事象を落とした対象まで正解と一致にしている(repeat_of: i0-r1-15)

前の周の指摘に、この周の実行で起きた実例が加わった。p5-same-time-twice の正解は `{same_order_in_two_runs: True}` だけで、採点は出力の余分な鍵を見ない(`run_battery.py:88-91` `_matches`)。調査結果の側の道具の 1 つは、同時刻の 4 件(約定・足・資金調達・清算)のうち約定 1 件しか届けず(adapter の注記「足・資金調達・清算は未定義の番号」、`opponents/hftbacktest_adapter.py:353-357`)、出力 `{"orders": [[["trade", 1700092800000000000]], [["trade", 1700092800000000000]]], "same_order_in_two_runs": true}` が正解と一致と採点された(`round_2/materials/runs/opp_hftbacktest.tsv`)。p5-hand-over-order も同じ道具が 1 件だけの列で `distinct_orders: 1` = 正解と一致。黙って 3 件を落とすのは規則 5 で最も悪い部類なのに、最上位に数えている(場面集の規則 1 違反)。
根拠: `test_i0r2_battery_p5_grading.py::test_dropping_three_of_four_same_time_events_is_not_graded_as_correct` の出力 `AssertionError: a run that delivered 1 of the 4 same-time events is graded 正解と一致`。

### [止める] i0-r2-07 p5-hand-over-order の「1 本しか受けない対象」の形の正解が、1 本の入力の順を守る規則と矛盾する(repeat_of: なし)

p5-hand-over-order は、1 本しか受けない対象には 4 つの入力を「その回の順で連結して」渡し、24 回とも同じ並び(`distinct_orders: 1`)を正解とする。1 本しか受けない対象にとって連結の順はその入力自身の順で、p5-same-stream-order(と第 2 周の核の規則、i0-r1-10)はそれを守れと言う。核自身も 24 通りの連結から 24 通りの並びを出す(作業者の試験 `tests/bt/item_0/test_bt0_scene_set.py` が `len(by_concat) == 24` を確かめている)。この正解は、1 本の入力を型で並べ替える対象を一致にし、入力の順を守る対象を不一致にする。場面の正解が誤っている(場面集の規則 1・5)。
根拠: `test_i0r2_battery_p5_grading.py::test_single_input_form_of_hand_over_order_agrees_with_keeping_one_input_in_order` の出力 `scene expects 1 order(s) for the single-input form; keeping one input in its own order gives 24`。

### [止める] i0-r2-08 検討表の「上位互換」の裏付けが、中身の無い一致に乗っている(repeat_of: i0-r1-16)

前の周の PineForge の行(`CONSIDERED.md:107`)は変わっていない。加えて P0-5 の表の 9 行(3 PySystemtrade・11 OctoBot・37 ThePredictiveDev・70 PineForge・98 mihircoding・99 NickGardi・101 akurkar07・104 jxm35・105 DaniyalMlk、`CONSIDERED.md:102-112`)は、上位互換の根拠を「hftbacktest の p5-same-time-twice / p5-hand-over-order / p5-same-stream-order が正解と一致」に置く(98 と 101 は p5-same-stream-order のみに置く箇所もある)。うち p5-same-time-twice と p5-hand-over-order の一致は、i0-r2-06 のとおり 4 件中 3 件を落とした出力で、能力を示していない。スキップの理由が調査結果の行(と実行の結果)で裏付けられていない。観点の能力を場面の数で決めてから候補を写す循環(i0-r1-16 の後半)も残っている(`CONSIDERED.md:98`「この観点の能力(`REQUIREMENTS.md` 21 行): …(p5-same-time-twice)/ …(p5-hand-over-order)/ …(p5-same-stream-order)」)。

### [止める] i0-r2-09 grep で当たって候補に写せなかった 90 行を、検討表が 1 件も検討していない(repeat_of: i0-r1-17)

`grep -c unmapped tests/bt/battery/item_0/opponents/CONSIDERED.md` → `0`。`pool.tsv` の未対応の行は前の周と同じ 90 行(P0-2: 1 / P0-3: 74 / P0-4: 1 / P0-5: 10 / P0-7: 4)。例: P0-4 の SCAN 3166 行(`sed -n 3163,3166p` の 4 行目「同エンジンには指値の概念が無い…建玉は `enter_long` / `enter_short` / `close_position` の 3 つだけ」、3 行目が候補 16 `Luczinsritter/event_driven_backtesting_engine` を名指す)。`REQUIREMENTS.md` は P0-4 の当たりとしてこの行を挙げているのに、`CONSIDERED.md:88-92` の P0-4 は動かせなかった候補を 1 件も載せていない。

### [直す] i0-r2-10 「未来の事象はどこからも届かない」という説明が言い過ぎ(repeat_of: なし)

`engine.py:33-35` は「no future event is held anywhere a strategy could reach」と書く。戦略のコードは呼び出しの積み重ね(`sys._getframe`)からエンジンに届き、併合器が持つ次の事象を読める。
根拠(scratchpad `bt/i0_r2_critic/probe4.py`): T0 + 4 日の呼び出しで `sys._getframe(1)` を遡って `CoreEngine` を見つけ、`eng._merger._heads` を読むと `via call stack: [104.0]`(5 本目の終値)。要件(`REQUIREMENTS.md:20`)の測り方は公開の手段(型・API)で、公開の手段では止まるので [止める] ではない。説明を「公開の手段と文脈から辿れる範囲では」と限るか、戦略を別の処理の単位で動かすかを書く。調査結果の側の道具も同じ弱さを持つ(どれも同じ処理の中で戦略を呼ぶ)。

### [直す] i0-r2-11 `visible_events(n=負の数)` が黙って空を返す(repeat_of: なし)

`api.py:411-413` は `n <= 0` を空で返す。`n` は「件数」(`api.py:382`)で、負の件数は戦略の誤り。時刻の引数(未来は `LookAheadError`)と揃えず、黙って空を返す。
根拠: `ctx.visible_events(n=-1) -> ()`、`n=-5 -> ()`(`PYTHONPATH=src python3 -c …` の出力 `n=-1 -> ()  n=-5 -> ()`)。

### [直す] i0-r2-12 P0-2 の「他の単位が混入しないこと」を拒否の側から測る場面が無い(repeat_of: なし)

観点 P0-2(`REQUIREMENTS.md:18`)は「他の単位(秒・ミリ・ISO 文字列)が核の内部表現に混入しないこと」。固定した測り方は「既知の時刻を投入し…同じ int64 ナノ秒と一致するか」で、4 場面(p2-iso-utc・p2-iso-offset・p2-event-time-exact・p2-one-ns-apart)はこれを満たす。ただ、秒の整数や float の時刻を渡したときに止めるか・黙って受けるかを見る場面は無い(新実装は `validate_nanos` で float を止める)。測り方の定めは満たしているので [直す] にした。

## 3. 場面集・表・検討表の点検

- **規則 1〜9**: 規則 1・5 に反するものが 2 件(i0-r2-06・07)、規則 6・9 の中身(上位互換の裏付け・検討の漏れ)に反するものが 2 件(i0-r2-08・09)。規則 2(作りの形を試さない)・3(観点ごとの集計と値の場面)・7(置き場所)は守られている(`scenes.py` 末尾の assert、表の観点ごとの集計)。規則 4 の時間の記録: 1 件の道具が動かなかった理由は「導入の途中で空きの容量が下限を割り…導入の開始から止めるまで 20 秒」で、`round_2/materials/logs/finmarketpy_attempt.log` に開始・停止の時刻と空き容量の実測がある(実測つき)。
- **表**: 調査結果の組の 2 枚はバイト単位で同じ(`md5sum_pairs.txt` の `survey: identical`)。新実装と調査結果の側の最良の行が 32 場面すべてで「正解と一致・2 回の実行で同じ」。うち P0-4 の p4-future-read-attempt(i0-r2-05)と P0-5(i0-r2-06・07)は、場面の正解の弱さか誤りのうえでの一致で、この「同等」は場面集が観点を測れていないことの表れでもある。この周に見つけた新実装の欠陥(i0-r2-01〜03)は、どれも場面集のどの場面にも当たっていない。
- **試金石**: 新実装と仕込んだ版の違いは p4-received-time の 1 場面だけ(`diff` の出力 `p4-received-time 正解と一致` ↔ `不一致`)。仕込みは設計どおりに効いている。
- **adapter の公平さ**: i0-r2-04。ほかに、backtrader の p4-future-read-attempt は既定(`preload=True`)で 104 が見え、adapter は `preload=False` の良い方を採った(`runs/opp_backtrader.tsv`)= 相手を強くする側で、新実装に有利ではない。
- **観点の網羅**: P0-5 の「規則どおりの順」(i0-r2-06)。P0-2 の拒否の側(i0-r2-12)。

## 4. 場当たりの直しの点検

見つからなかった。作業者の直しはどれも構造の変更(路ごとの FIFO と鍵、事実の台帳、時刻の引数の 1 か所の検査、足の区間の定義、走らせ方の設定の検査)。作業者の試験の変更 3 本(`test_bt0_scene_set.py`・`test_bt0_streams.py`・`test_bt0_venue_order.py`)は新しい規則に合わせた書き直しで、期待を緩めたものではない(`git diff HEAD -- tests/bt/item_0/…` で確かめた。例: 1 本の入力の順を型の順から入力の順に替え、別々の入力の併合は型の順のまま確かめている)。

## 5. 置いた試験(`tests/bt/critic/item_0/`。落ちるものは残す。作業者か場面係が直す)

| ファイル | 指摘 | 今の結果 | 直す者 |
|---|---|---|---|
| `test_i0r2_negative_time_jumps_to_epoch.py` | i0-r2-01 | 落ちる | 作業者 |
| `test_i0r2_second_cancel_in_flight_shown_open.py` | i0-r2-02 | 落ちる | 作業者 |
| `test_i0r2_history_limit_views_disagree.py` | i0-r2-03 | 落ちる | 作業者 |
| `test_i0r2_battery_p5_grading.py`(2 件) | i0-r2-06・07 | 2 件とも落ちる | 場面係(作業者の持ち物の外) |
| `test_i0r2_channels_random.py`(2 件) | 前の周の i0-r1-05・06・07・09・10・12 の確かめ直し | 通る | — |

コマンド: `PYTHONPATH=src python -m pytest tests/bt/critic/item_0` → `5 failed, 24 passed in 1.26s`。
