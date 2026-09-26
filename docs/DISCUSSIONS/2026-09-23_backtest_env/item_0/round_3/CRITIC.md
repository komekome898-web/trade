# 項目 0「核」第 3 周 — 批評家の記録

委任文: `docs/DATA/delegations/20260923_backtest_env_prompt.md`(指紋 `20260923_backtest_env_prompt.md@f9fe736bfcff`。`sha256sum | cut -c1-12` で確かめ、全 158 行を読んだ)。
合意した完了の形(委任文 §0 の逐語): 「**すべてが調査結果以上の信頼性と再現性に優れたものにすること。**」
手元に置いたもの: 固定した要件 `docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/REQUIREMENTS.md`、場面集 `tests/bt/battery/item_0/scenes.py`(`python3 gen_definitions.py --check` → `OK`)、検討表 `tests/bt/battery/item_0/opponents/CONSIDERED.md`(`python3 scripts/check_bt_considered.py …` → `OK 誤り 0 件`)、この周の資料 `round_3/materials/`、作業者の `round_3/ROOTCAUSE.md`、前の周の `round_2/CRITIC.md`、調査報告 `docs/DATA/SCAN_2026-09-21_tools.md` の該当行。

## 0. 構造の変化(前の周から)

あり。作業者の申告の 3 点を実物で確かめた。
- (1) FIFO の路が 1 つの型 `_FifoChannel`(`engine.py:304-320`、前の時刻は `None` で始まる)。注文の口の「今」は `Optional[int]`(`api.py:209-214`)、待ち行列の鍵の 3 つ目の既定は項目の時刻(`engine.py:503-504`)、`FillNotice.venue_time_ns` は既定なしの必須(`interfaces.py:100-106`)。
- (2) 取消の答え待ちは件数 `cancels_in_flight`(`api.py:175`・`259`・`303-306`)。取引所に取消 1 つへ答えちょうど 1 つを求める(`engine.py:744-761`)。取消の成立の通知に `answers`(`events.py:87-90`・`356-368`、`engine.py:798-806`)。
- (3) 履歴の保持は新しいファイル `history.py`(`git status` で未追跡の新規)の `DeliveredHistory` 1 つ。捨てた部分に掛かる読み出しは `HistoryTruncatedError`(`api.py:462-488`)。

## 1. 前の周までの指摘を自分で確かめ直した結果

コマンド: `PYTHONPATH=src python -m pytest tests/bt/critic/item_0 tests/bt/item_0 tests/bt/battery/item_0`。この周の試験を足す前は `3 failed, 298 passed`。落ちたのは `test_i0r2_battery_p5_grading.py` の 2 件(場面係の持ち物、i0-r2-06・07)と `test_i0r2_history_limit_views_disagree.py`(下の 1.1)。

### 1.1 批評家の試験の誤り(場面集の規則 8)

この周の作業者の報告(返り値)は私に渡されていないので、作業者が「試験自身の誤り」と報告したかは確かめられない(未確認)。落ちた試験は自分で読んで判断した。

- `test_i0r2_history_limit_views_disagree.py`(i0-r2-03 の試験): **試験自身の誤りと判断し、書き直した。**旧い試験は `ctx.visible_events()` を例外を受けずに呼んでいた。第 3 周の核は、捨てた部分に掛かる読み出しを `HistoryTruncatedError` で断る(i0-r2-03 が求めた「切られたことを知らせる」振る舞い)。旧い試験はその断りで落ちており、食い違いで落ちていたのではない(出力 `HistoryTruncatedError: visible_events(event_type=None, since_ns=None, n=None) reaches into the TRADE history dropped by history_limit …`)。性質を言い直した: (a) 同じ窓への 2 つの読み出しがどちらも答えるときは、型で引いたもの = 全体を型で抜いたもの、(b) 答えた読み出しは上限なしの実行と同じ、(c) 上限 N で必ず答えられる読み出し(最後の n ≤ N 件、全体でも型ごとでも)は断られない(何でも断る核が (a)(b) を素通りしないため)。25 種 × 上限 1・2・5 で**通る**。書き直した理由はファイル冒頭に書いた。
- `test_i0r2_battery_p5_grading.py` の 2 件: 試験の誤りではない(場面の正解の誤り・弱さを測る試験)。場面集が変わっていないので今も落ちる。取り下げない。

### 1.2 前の周の指摘

| id | 確かめ方 | 結果 |
|---|---|---|
| i0-r1-05・06・07・09・10・12 | 前の周の乱数の試験 `test_i0r2_channels_random.py` と、個別の試験(`test_r5c1_*`・`test_i0r1_*`)が通る | 直ったまま |
| i0-r1-08・11・13 | `test_i0r1_since_future_is_silent.py`・`test_i0r1_zero_length_bar_with_range.py`・`test_i0r1_end_time_not_validated.py` が通る | 直ったまま |
| i0-r2-01(時刻 0 に飛ぶ) | `test_i0r2_negative_time_jumps_to_epoch.py` 通過。加えて自分で**時刻をずらしても同じ実行になるか**の試験を書いた(`test_i0r3_shift_and_cancel_count.py`。乱数の取引所・乱数の遅延・取消の二重送り・時計、15 種 × ずらし 4 通り = 1970 年ちょうど・1970 年をまたぐ・1970 年より 3 秒前から・2 倍前)。届いた事象・通知・注文の見え方・約定がずらした分だけずれて一致 → **通る** | 直った |
| i0-r2-02(取消 2 つ) | `test_i0r2_second_cancel_in_flight_shown_open.py` 通過。加えて、毎回の呼び出しで全注文の `cancels_in_flight` = (送った取消の数)−(届いた取消への答えの数。通知の公開の欄から独立に数える)を 100 種で確かめた(取消は 300 件超、2 つ重ねた取消は 30 件超)。終わりに件数 0・戦略の見る状態 = 台帳 → **通る** | 直った |
| i0-r2-03(履歴の 2 つの問い) | 上の 1.1 で書き直した試験が通る。作業者の `test_bt0_history_limit.py` も通る | 直った |
| i0-r2-10([直す] 説明の言い過ぎ) | `api.py:17-29`・`engine.py:34-39`・`contract.py:39-41` に保証の範囲が書かれた | 直った |
| i0-r2-11([直す] 負の n) | `ctx.visible_events(n=-1)` → `OrderApiError`(`api.py:527-535`、作業者の試験 `test_count_argument_is_checked_in_one_place` 通過) | 直った |
| i0-r1-14 / i0-r2-05 | 場面集は変わっていない(`git status --short tests/bt/battery` → `adapters/new_impl.py` の説明 3 行だけ、`git diff --stat HEAD -- tests/bt/battery` → `1 file changed, 3 insertions(+)`)。`scenes.py:260-262` の導き方は今も「例外・空の結果・拒否のどれか」 | **直っていない → i0-r3-02** |
| i0-r1-15 / i0-r2-06 | 同上。`scenes.py:276`・`284`・`293` の正解は今も `{same_order_in_two_runs: True}` / `{distinct_orders: 1}` / `{prices: [100.0, 101.0]}`。`run_battery.py:88-91` の `_matches` は余分な鍵を見ない。試験が今も落ちる | **直っていない → i0-r3-03** |
| i0-r2-07 | 同上。試験が今も落ちる | **直っていない → i0-r3-04** |
| i0-r2-04 | `opponents/quantcore_adapter.py:48-50` に今も `limits.enabled = False` | **直っていない → i0-r3-05** |
| i0-r1-16 / i0-r2-08 | `CONSIDERED.md:107`(PineForge)と P0-5 の表(`CONSIDERED.md:102-112`)は変わっていない | **直っていない → i0-r3-06** |
| i0-r1-17 / i0-r2-09 | `grep -c unmapped …/CONSIDERED.md` → `0`。`sed -n '/# unmapped/,$p' tests/bt/battery/item_0/pool.tsv \| tail -n +2 \| cut -f1 \| sort \| uniq -c` → `1 # P0-2 / 74 # P0-3 / 1 # P0-4 / 10 # P0-5 / 4 # P0-7` | **直っていない → i0-r3-07** |
| i0-r2-12([直す]) | 場面集は同じ。付け直しは下の i0-r3-10 に理由 | **直っていない → i0-r3-10** |

場面集・検討表・adapter への指摘(i0-r1-14〜17・i0-r2-04〜09)は、第 1 周・第 2 周・第 3 周と 3 周続けて同じ原因のまま残っている。作業者の `ROOTCAUSE.md` §F は、作業者の持ち物の外なので原因の読みだけを書いたとしている(正しい)。場面係はこの周も起こされていない(場面集が変わっていないことから)。**場面集への指摘の数えは台本が行う**(委任文 §3「周回の数え方と止める条件」4)。

## 2. この周の指摘

### [止める] i0-r3-01 例外が 1 歩の途中で出たあと、エンジンが食い違った状態のまま走り続ける(repeat_of: なし)

`CoreEngine.step()` は公開で、例外が出たあとにもう一度呼ぶことを止めない。1 歩は不可分になっていない:
- 戦略が `place_order` のあとで例外を出すと、注文は戦略の見る注文に PENDING_NEW で載る(`api.py:238-244`)が、`_deliver` の `finally` が送り箱を捨て(`engine.py:660-664`)、`_drain`(`engine.py:665`)は呼ばれない。
- 遅延の模型が `_drain` の 2 件目で例外を出すと、1 件目は待ち行列に入り、残りは消える(`engine.py:667-681`)。
- ほかに、報告の途中の `VenueProtocolError`(`engine.py:763-813` は 1 件ずつ台帳に当てて通知を積む)や、`_FifoChannel.admit` が `_push` の検査より前に前の時刻を進める(`engine.py:673-675`・`811-813`)のも同じ形。

その後 `run()` を呼ぶと、例外は出ず、戦略には送られていない注文が PENDING_NEW のまま見え続け、実行の結果にも開いた注文として載る。`errors.py:1-3` は「the core never downgrades one of these to a warning and carries on」と書くが、続けることを断っていない。黙って誤った状態を見せる = 信頼性を崩す。直し方は「例外が出た 1 歩のあとはエンジンを止まったものにし、以後の `step()` を断る」か「1 歩を不可分にする」のどちらか(作業者が決める)。
根拠: `tests/bt/critic/item_0/test_i0r3_resume_after_exception.py` の出力:
```
AssertionError: the run went on with orders the strategy sees but that were never sent: [('core-1', 'PENDING_NEW')]
AssertionError: the run went on with orders the strategy sees but that were never sent: [('core-2', 'PENDING_NEW'), ('core-3', 'PENDING_NEW')]
```

### [止める] i0-r3-02 p4-future-read-attempt の正解が固定した要件より弱いまま(repeat_of: i0-r2-05)

第 1 周(i0-r1-14)・第 2 周(i0-r2-05)と同じ原因。`scenes.py:260-262` の導き方は「例外・空の結果・拒否のどれか」で、要件(`REQUIREMENTS.md:20`)の「実行時エラーか型エラーで止まるか(素通りしたら不合格)」に合わない。この周の実行の記録でも、黙って切り詰めた道具と値を返した道具が正解と一致に数えられる形のまま(`round_3/materials/runs/opp_qf_lib.tsv`・`opp_zipline_reloaded.tsv`。qf-lib の行は「get_price(ticker, Close, 最初の日, 5 本目の日) -> [100.0, 101.0, 102.0, 103.0]」で正解と一致。資料係の突き合わせ `logs/compare_survey_results.out` は場面係の `survey_results` との差 0 セル)。

### [止める] i0-r3-03 P0-5 に「規則どおりの順」を測る値の場面が無く、事象を落とした対象を正解と一致にする(repeat_of: i0-r2-06)

第 1 周(i0-r1-15)・第 2 周(i0-r2-06)と同じ原因。要件 `REQUIREMENTS.md:21`「規則どおりの順で処理されるか(値)」に当たる場面が無い。採点の `_matches`(`run_battery.py:88-91`)は余分な鍵を見ない。
根拠: `test_i0r2_battery_p5_grading.py::test_dropping_three_of_four_same_time_events_is_not_graded_as_correct` が今も落ちる(`AssertionError: a run that delivered 1 of the 4 same-time events is graded 正解と一致`)。

### [止める] i0-r3-04 p5-hand-over-order の「1 本しか受けない対象」の形の正解が、1 本の入力の順を守る規則と矛盾する(repeat_of: i0-r2-07)

第 2 周と同じ原因(`scenes.py:279-289`)。根拠: `test_i0r2_battery_p5_grading.py::test_single_input_form_of_hand_over_order_agrees_with_keeping_one_input_in_order` が今も落ちる(`scene expects 1 order(s) for the single-input form; keeping one input in its own order gives 24`)。

### [止める] i0-r3-05 資料係の adapter が、調査結果の側の道具の既定の拒否の仕組みを切ったまま(repeat_of: i0-r2-04)

`opponents/quantcore_adapter.py:48-50` は今も `limits = qc.RiskLimits(); limits.enabled = False`。新実装の adapter は拒否を自分で書いた `_CashAccount` で作る(`adapters/new_impl.py:194-226`・`314-319`)。この周の資料係は `adapters/new_impl.py` の説明を 3 行足しただけで、相手の adapter の既定を外した設定は見直していない(`git diff --stat HEAD -- tests/bt/battery` → 1 ファイル 3 行)。ほかの adapter を grep した範囲(`grep -n "limits\|risk\|= False\|=False\|preload\|process_only" opponents/*.py`)では、既定を外して相手を弱める設定は quantcore の 1 件だけ(backtrader は既定と `preload=False` の両方を走らせ良い方を採る = 相手を強くする向き、freqtrade の `process_only_new_candles = False` と市場の定義は取引所の資料を落とさずに動かすための設定)。

### [止める] i0-r3-06 検討表の「上位互換」の裏付けが、能力と合わない場面・中身の無い一致に乗ったまま(repeat_of: i0-r2-08)

第 1 周(i0-r1-16)・第 2 周(i0-r2-08)と同じ原因。`CONSIDERED.md:107`(70 PineForge: 足の内側の道筋の順番付けを、それを測らない p5-hand-over-order に対にする)と P0-5 の表(`CONSIDERED.md:102-112`、i0-r3-03 の弱い一致に乗る)は変わっていない。この周に読んだ同じ原因の例をもう 1 つ足す: P0-7 の 16 Luczinsritter(`CONSIDERED.md:140`)は、能力に「データの取り込みの口を差し替える」を挙げ、それを Backtrader の p7-fill-model-swap・p7-account-swap の一致に対にしている。データの取り込みは P0-7 の能力(約定・遅延・費用・口座、`REQUIREMENTS.md:23`)ではなく、対にした場面はそれを測らない。1 能力ずつの対応になっていない(委任文 §3「段の無い観点: 使える理由は『上位互換』の 1 本だけ = … 1 能力ずつ示す」)。

### [止める] i0-r3-07 grep で当たって候補に写せなかった 90 行を、検討表が 1 件も検討していない(repeat_of: i0-r2-09)

第 1 周(i0-r1-17)・第 2 周(i0-r2-09)と同じ原因。コマンドと出力は 1.2 の表。P0-4 は今も「動かせなかった候補 0 件」(`CONSIDERED.md:88-92`)で、`REQUIREMENTS.md` が P0-4 の当たりに挙げた SCAN 3166 行(候補 16 を指す)を検討していない。

### [止める] i0-r3-08 「持たないと確認した」を、調査報告に書かれていないことで決めている(場面集の規則 6 違反、repeat_of: なし)

規則 6 は「持たないと確認した」を、動かせない候補なら「コードの書き写しか一次資料で、その能力の口が無いことを行を引いて示したとき」に限る。P0-7 の能力は 4 つ(約定・遅延・費用・口座)。
- 8 OpenTrader(`CONSIDERED.md:136`): 約定の口が無いことは SCAN 7539 行の書き写しで示すが、遅延・費用・口座は「SCAN の P0-7 の行(`pool.tsv`)に無い」を理由にしている。調査報告に書かれていないことは、口が無いことの書き写しでも一次資料でもない。この候補は道具台帳 §3 の 11 件ではないので (b) 一次資料を読める(委任文 §3)が、読んでいない。
- 15 Mendl-Labs/BacktestingCore(`CONSIDERED.md:139`): 遅延と影響の式について行を引くが、費用と口座の口については何も書いていない。
- 107 sigc(`CONSIDERED.md:148`): 費用と影響について 8806 行を引くが、遅延と口座の口については何も書いていない。
`scripts/check_bt_considered.py` は理由の欄に「行」があるかしか見ない(規則 9)ので通っている。行の中身が 4 つの能力の全部に当たっているかは批評家と監査役が見る決まりで、当たっていない。

### [直す] i0-r3-09 時計(戦略の予約)の路を「先入れ先出し」と書いているが、そうなっていない(repeat_of: なし)

`ordering.py:3-4`「every channel is FIFO: nothing on a channel ever overtakes something sent on it earlier」と、機械で読む規則 `ORDERING_RULE["channels_fifo"]`(`ordering.py:144-145`)は `deliver:timer` を含む。実際は、あとで予約した早い時刻の時計が先に届く(時計は予約した時刻に届くのが正しい振る舞いで、振る舞いは誤っていない)。規則の文と機械で読む規則が、実際の振る舞いと食い違っている。同じ時刻の中の並びが「予約した順」なのは正しい(`ordering.py:142`)。
根拠(`PYTHONPATH=src python3 -c …` の出力。1 回の呼び出しで +10 ns、次に +5 ns の順に予約): `[('set-second-at+5', 5), ('set-first-at+10', 10)]`、`ORDERING_RULE['channels_fifo']` → `[…, 'deliver:notice', 'deliver:timer']`。
振る舞いは正しく、同時刻の並びの規則(P0-5 の中身)には当たらないので [直す] にした。

### [直す] i0-r3-10 P0-2 の「他の単位が混入しないこと」を拒否の側から測る場面が無い(repeat_of: i0-r2-12)

前の周の [直す] を見直した。固定した測り方(`REQUIREMENTS.md:18`「既知の時刻を投入し、核が保持する値が同じ int64 ナノ秒と一致するか」)は 4 場面で満たされている。拒否の側の場面を求めるのは固定した測り方より厳しくすることになる(委任文 §3「後から厳しくもしない」)ので、[止める] には付け直さない。

### [直す] i0-r3-11 検討表の冒頭が古い版の委任文の指紋を指す(repeat_of: なし)

`CONSIDERED.md:3` は「指紋 `2b06c02832be`」。今の版は `f9fe736bfcff`。どの版の規則で作ったかの記録が今の版と合わない(版の間で場面集の規則 4・9 の文と §3 の段落が変わっている)。

### [示唆] i0-r3-12 状態不明を確定させる「照合の問い合わせ」の口が核に無い(repeat_of: なし)

戦略の見る状態不明(新規・取消とも)が解けるのは、取引所の側が確定の報告(約定・取消・受付・拒否)を自分から出したときだけ(`api.py:46-49`)。CLAUDE.md §1 の「`reconcile_unknown` で状態確定するまで再送禁止」に当たる、読み取り専用の照会を戦略から取引所へ送る路が無い。固定した要件(差し込み口 = 約定模型・遅延模型・費用・口座)の外なので [示唆]。項目 2 が異常系を作るときに核の口が要るかを先に決めておくとよい。

## 3. 場面集・表・検討表・adapter の点検

- **規則 1〜9**: 規則 1・5 に反するもの 2 件(i0-r3-03・04)、規則 6 に反するもの 1 件(i0-r3-08)、規則 6・9 の中身(上位互換の裏付け・検討の漏れ)に反するもの 2 件(i0-r3-06・07)。規則 3(観点ごとに値の場面 1 つ以上): `scenes.SCENES` を数えた出力 `('P0-1','value'): 2, ('P0-2','value'): 3, ('P0-3','value'): 1, ('P0-4','value'): 2, ('P0-5','value'): 2, ('P0-6','value'): 1, ('P0-7','value'): 1` で形は満たす(P0-5 の値の場面の中身は i0-r3-03)。規則 4 の時間・容量の記録: 動かなかった 1 件は `round_3/materials/logs/finmarketpy_attempt.log`(開始・停止の時刻と空き容量の実測、27 秒で 146 MB < 150 MB)に実測がある。規則 7 の置き場所は守られている。
- **能力を申告で数えていないか**: 能力の場面の出力は、どれも対象を実際に呼んだ結果で決まっている(新実装の adapter は `ok(...)` に呼んだ結果だけを入れる)。ただし p4-future-read-attempt は「得られたか」の真偽 1 つに畳まれていて、空の結果・切り詰めた結果・例外の区別が採点に届かない(i0-r3-02)。
- **表**: 調査結果の組の 2 枚はバイト単位で同じ(`round_3/materials/md5sum_pairs.txt` の `survey: identical`)。試金石の表は 2 枚が違う(`mutant: differ`)。仕込みの効きは `mutant.py --check` で p4-received-time だけが変わる(`commands.txt`)。この周に見つけた核の欠陥(i0-r3-01)は、場面集のどの場面にも当たらない。
- **adapter の公平さ**: i0-r3-05。新実装の adapter(`adapters/new_impl.py`)は、この周の変更が冒頭の説明 3 行だけで、場面のメソッドは変わっていない(`git diff HEAD -- tests/bt/battery/item_0/adapters/new_impl.py`)。`_ArrivalFill.on_cancel` は取消 1 つに `Canceled` を 1 つ返し、第 3 周の核の「答えちょうど 1 つ」に合う。新実装だけ有利になる呼び方の変更は無い。
- **再現(候補 33)**: `opponents/repro_33_execution_simulator.py` を読んだ。一次資料で決まっていない同時刻の並びを「積んだ順」に置き、P0-7 の場面は同時刻に依らないと書く(冒頭 24-27 行)。遅延の場面の設定(`order_submit_latency_ns=7,000,000`、ほかは 0)で、市場の事象と注文・約定の報告が同じ時刻に並ぶ組み合わせは場面の入力(1 日おきの約定)からは起きないと読んだ。一次資料をこの周に取り直して突き合わせてはいない(未確認)。
- **観点の網羅**: P0-5 の「規則どおりの順」(i0-r3-03)。P0-2 の拒否の側(i0-r3-10、[直す])。

## 4. 場当たりの直しの点検

見つからなかった。作業者の直しは 3 つとも構造の変更(路の型・答えと要求の 1 対 1・保持の規則 1 つと断り)。作業者が書き直した試験 `tests/bt/item_0/test_bt0_time_window.py::test_history_limit_applies_per_type_too` は、「全部の約定を読むと断られる」を足しただけで、前の確かめ(足が残る・最後の 10 件)は残している。`test_bt0_engine_source.py:45-51` も、保持の件数を断りのかからない形で読むように替えたもので、上限の確かめは残っている。期待を緩めたものは見当たらない。

## 5. 置いた試験(`tests/bt/critic/item_0/`。落ちるものは残す)

| ファイル | 指摘 | 今の結果 | 直す者 |
|---|---|---|---|
| `test_i0r3_resume_after_exception.py`(2 件) | i0-r3-01 | 2 件とも落ちる | 作業者 |
| `test_i0r3_shift_and_cancel_count.py`(5 件) | i0-r2-01・02 の確かめ直し | 通る | — |
| `i0r3_harness.py` | 上の試験の乱数の取引所・遅延・戦略(試験ではない部品) | — | — |
| `test_i0r2_history_limit_views_disagree.py`(書き直し) | i0-r2-03 の確かめ直し(1.1) | 通る | — |
| `test_i0r2_battery_p5_grading.py`(2 件、前の周のまま) | i0-r3-03・04 | 2 件とも落ちる | 場面係 |

コマンド: `PYTHONPATH=src python -m pytest tests/bt/critic/item_0 tests/bt/item_0 tests/bt/battery/item_0` → `4 failed, 304 passed in 58.01s`。`PYTHONPATH=src python -m pytest tests/bt` → `4 failed, 304 passed in 58.31s`(同じ 4 件)。
全試験: `setsid nohup env PYTHONPATH=src python -m pytest -p no:cacheprovider > <scratchpad>/bt/pytest_item0_r3_critic.log 2>&1 &` → 末尾の行 `4 failed, 3191 passed, 4 skipped, 1 warning in 483.02s (0:08:03)`。落ちたのは上の 4 件だけ(批評家の試験)。
