# 項目 4 第 3 周 批評家の記録(統合の周)

委任文 `docs/DATA/delegations/20260926_backtest_env_finish.md@ec283fb43be1`(親 `20260925_backtest_env_prompt.md@388d55cdeb32`)。起こされた時刻 14:03 UTC、期限 14:35 UTC。射程は委任文 §2 の逐語「[止める] にするのは **正しさ(場面集の正解・規則の文・独立の参照と食い違う)・安全(実データ・事前登録・封印の規則を迂回できる)・統合(部品が繋がっていない、試験が落ちる)・場面集の規則 1〜9 の違反(比べの結果を変えるもの)**」「報告の書き方・注記の言い回し(比べの結果を変えないもの)は **[直す] 以下**」。

## 0. 対応表(CLAUDE.md §0.1)

| やろうとすること | 委任文・起こし文の該当語(逐語) |
|---|---|
| 第 2 周の [止める] 9 件が閉じたかを VERDICTS と round_3/ の根本原因で確かめる | 「第 2 周の [止める] 9 件(委任文 §1 の i4-r2-01〜09 と「直し方の決め」)が閉じたか」 |
| barmodel.py・engine.py・pipeline.py・bar_sim.py・SPEC.md・格子・場面集を読む | 「実装: src/bot/bt/compat/barmodel.py・engine.py、src/bot/bt/pipeline.py(…)、独立の参照 …、格子 …、場面集 …」 |
| bar_rules.py を import する 12 件を bar_sim の口に付け替える | 「削除された src/bot/bt/reference/bar_rules.py を import する 12 件は、あなたが bar_sim(…)か compat の口に付け替えて直す」 |
| 落ちる試験と対照を tests/bt/critic/item_4/ に足す | 「批評家の試験は `tests/bt/critic/item_4/` に足す(落ちる試験 + 対照)」 |
| 3 役の途中の落ちは「途中(誰の物)」と書く | 「これら 3 つの途中の落ちは、その役が返る前は [止める] にせず「途中(誰の物)」と書く」 |
| 14:35 UTC で途中でも返す | 「返す期限 **14:35 UTC**(…時間が来たら途中でも返す)」 |

## 1. 整備(批評ではない): bar_rules の付け替え

`tests/bt/critic/item_4/test_i4r1_pending_signal_before_intrabar_exit.py:100` の `from bot.bt.reference.bar_rules import run_rules` を `bot.bt.reference.bar_sim.run_bars(bars, signals, options)` に付け替えた。場面集の config → 参照の options の写し(`_ref_options`: initial_equity → capital、order_notional → order_amount、bar_seconds、undecided = リードの値 U1 `use_available`・U2 `keep`)を同じファイルに置いた(作業者の `i4w_drive.reference_options` と同じ形だが、作業者のファイルは import していない)。
結果: `PYTHONPATH=src python -m pytest --basetemp=<私有> -p no:cacheprovider tests/bt/critic/item_4/test_i4r1_pending_signal_before_intrabar_exit.py` → **36 passed in 0.77s**(付け替えた 12 件を含む。独立の参照も R-T1 の答えを返す)。

## 2. 第 2 周の [止める] 9 件が閉じたか(自分で確かめた範囲)

| id | 確かめ方(読んだ所・打ったもの) | 結果 |
|---|---|---|
| i4-r2-01 | `adapters/new_impl.py:199-209` `_run_reference` が `bot.bt.reference.bar_sim.run_bars` を呼ぶ。`bar_rules.py` は作業木に無い(`ls src/bot/bt/reference/` = SPEC.md・bar_sim.py・event_sim.py・num.py)。格子 `test_i4_engine_vs_independent_bar_sim.py` は下の全体の実行に含めて回した | 閉じた(場面集の口が独立の参照を呼ぶ) |
| i4-r2-02 | 私の第 2 周の試験 `test_i4r2_time_exit_at_the_open.py` が通る(下の全体の実行)。作業者の ROOTCAUSE_worker.md §1(`time_exit_at_open`、spec のみ) | 閉じた |
| i4-r2-03 | `pipeline.py:387-425` `row_evidence`: データ層で読んだ行の (時刻, 値) を市場のフォルダのファイルの行と照らす。`:623-636` 合成は `{name, generator}` からだけ(`origin: "synthetic"` の宣言は断る)。私の第 2 周の試験 `test_i4r2_origin_survives_reencoding.py` が通る | 閉じた |
| i4-r2-04 | `test_i4r2_considered_unread_is_not_confirmed.py` が通る | 閉じた |
| i4-r2-05 | `pipeline.py:602-616`: `prereg_sha256` は断る、`prereg` は root の下のファイル、空は断る、研究はファイル必須。`test_i4r2_research_needs_a_real_preregistration.py` が通る | 閉じた |
| i4-r2-06 | `pipeline.py:117-129` の import に fill(SimVenue・FillRange)・latency(LatencyModel)・costs(ScheduleCostModel)・portfolio(MarginAccount)。`:968-984` で銘柄ごとに差す。`:516-518` `_check_fill` は両側必須、`:1039` 両側を回す。自前の 4 つの名は無い(`grep -n "FirstObservedFill\|NullAccount\|_Latency\|_Fee" pipeline.py` = 0) | 閉じた(ただし口座の差し込みに新しい欠陥 = i4-r3-01) |
| i4-r2-07 | VERDICTS の場面係の返り値: 検査した版 5e62602c を取り直したが、この環境の許可の判定が構築・実行を止めた(道具は 1 度も呼んでいない)。リードの決め(12:52)「比べていない(…)のまま進める」 | 測定では閉じていない。リードの決めで「比べていない(理由つき)」の記録に置き換え = [注記](i4-r3-03) |
| i4-r2-08 | 作業者 ROOTCAUSE_worker.md §5(`maker_mask_at_signal`・`maker_same_side_keeps`、spec のみ)、場面係が R-E4・R-M6 と場面 5 つを足した(VERDICTS 12:33) | 閉じた |
| i4-r2-09 | `test_battery_item4_diffscope.py` が通る(下の全体の実行) | 閉じた |

## 3. 指摘

### i4-r3-01 [止める] 安全・統合(target=実装)口座の差し込み口が、統合の口で遅らせた証拠金の検査の観測を MarginAccount に 2 度見せ、その観測で出た強制清算の注文を落とす
- **作業者の I-2(甲)の途中の部品**である(起こし文「作業者(I-2 = …)」)。作業者が返った時点でこの形のままなら [止める]。作業者が返る前は「途中(作業者)」の印も付ける。
- 読んだ所: `src/bot/bt/pipeline.py:816-855` `DeferredMarginAccount`。docstring は「each event reaches the MarginAccount once」と書き、`observe`(:836)が `id(event)` を憶え、`on_market_event`(:846)が同じ `id` のときだけ憶えた答えを返す。しかし核は受け手ごとに**別の写し**を渡す: `src/bot/bt/core/engine.py:1219`(約定模型 = ArrivalGate へ `copy_carrier(event)`)と `:1222`(口座へ別の `copy_carrier(event)`)。`values.py:1935-1939`「each receiver holds objects no one else holds」。よって `id` は決して一致せず、`_seen` は捨てられ `inner.on_market_event` が**もう 1 度**呼ばれる。
- 結果を変える所: `src/bot/bt/portfolio/account.py:339-354` `_maybe_liquidate` は `_forced_pending = True` を立てて強制清算の注文を**1 度だけ**返す。1 度目(`observe`、答えは核に渡らない)で立った旗のせいで、2 度目(核が受け取る方)は `[]`。**保留した成行を値付けする観測で証拠金が維持率を割ると、清算の注文が消え、その口座は以後 2 度と清算されない**(`_forced_pending` が立ったまま)。悲観側の幅・証拠金の結果(要件 I4-5・委任文 §1 i4-r2-06「証拠金が実行記録に出ること」)が誤る。
- 試験: `tests/bt/critic/item_4/test_i4r3_deferred_account_sees_each_event_once.py`(格子 = 観測 {trade・bar・book} × 渡し方 {核の写し・同じ物(対照)})→ **3 failed, 3 passed**。落ちた 3 件の文: `the MarginAccount saw the trade observation 2 times (stated: once)`(bar・book も同じ)。対照 3 件(同じ物を渡す)は通る = 試験は空でない。
- fix_files: `src/bot/bt/pipeline.py`(`DeferredMarginAccount`。`id` でなく、値の等しさ + 時刻、または「次に核から来る同じ時刻・同じ型の観測 1 件を写しと見なす」印で照らす。もしくは `observe` を消し、`recheck` で口座の `_to(t)` と mark の更新だけを別の口で行う)。核(`engine.py` の写し)は変えない(核の契約 = 受け手ごとに別の物、は正しい)。
- 打ったコマンド: `PYTHONPATH=src python -m pytest --basetemp=<私有> -p no:cacheprovider tests/bt/critic/item_4/test_i4r3_deferred_account_sees_each_event_once.py` → `3 failed, 3 passed in 0.46s`。

### i4-r3-02 途中(場面係)場面集の統合の場面 `i4-5-fills` が落ちる
- `tests/bt/item_4/test_i4_battery_scenes.py::test_scene_is_answered_right_and_the_same_twice[i4-5-fills]` → `fills[pessimistic:bf]: None 件(正解 4 件)`。起こし文「場面係(統合の場面 5 つの正解を I-1〜I-5 の規則で導き直す)」の途中の落ちなので [止める] にしない。場面係が返ったあとに残れば [止める](統合)。

### i4-r3-03 [注記] 場面集(target=場面集)PineForge は 3 周続けて 1 場面も走っていない(場面集の規則 4)
- 第 2 周の i4-r2-07 は測定では閉じていない。VERDICTS の記録: 検査した版 5e62602c を取り直したが「構築・実行へ進む操作をこの環境の許可の判定がまた止めた。PineForge は道具を 1 度も呼んでいない」。リードの決め(12:52 UTC)「比べていない(この環境の許可の判定が構築・実行を止めた。道具は呼んでいない)」のまま進め、「測っていない範囲」に載せる。
- 比べの結果は変えない(相手が 1 つ減るだけで、新エンジンの正解との一致は変わらない)ので [注記]。完了の報告の「測っていない範囲」に、規則 4 の文どおり「この周では未実行」ではなく理由(許可の判定)と、走らせるのに要るもの(オーナーの許可の規則)が書かれていることをリードが確かめること。

### i4-r3-04 [注記] 実装(target=実装)作業者の I-2 の試験は印なしで作業木にあるが、i4-r3-01 の経路を含まない
- `grep -rn "xfail" tests/bt/item_4/*.py` = 0 件(14:09 UTC)。`tests/bt/item_4/test_i4_pipeline.py:351` `test_i2_an_order_before_the_first_observation_fills_at_it` は印なし(作業者が (甲) = `DeferredMarginAccount` を置いて印を外した途中の状態と読む。推定)。この試験が見るのは「最初の観測で埋まる」と「1 JPY の口座で遅らせた検査が断る」の 2 つで、保留した成行の値付けの観測で清算が起きる経路(i4-r3-01)と、口座がその観測を 1 度だけ見ることは見ていない。比べの結果は変えないので [注記]。作業者が返るときに i4-r3-01 の試験が通ることを返り値に書くこと。
