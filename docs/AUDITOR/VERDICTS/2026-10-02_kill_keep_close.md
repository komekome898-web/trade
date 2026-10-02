# 批評家の記録: キルスイッチが送ったばかりの決済を取り消す件・RunLock の空の鍵(LIVE の前に直すもの)

対象: `src/bot/main.py`・`src/bot/order_management/manager.py`・`src/bot/jpx/run_lock.py`・`scripts/record_deribit_oi.py`、試験 `tests/test_resilience.py`・`tests/test_orders.py`・`tests/test_on1_live.py`(未コミット)。

## 1 回目の批評家(2026-10-02)

止める 1・直す 5・聞く 1

**読み(逐語)**: 欠陥 2(空の鍵を mtime で年齢づけする)と record_deribit_oi の案内文はそのままコミットしてよい。欠陥 1 はコミットしてはいけない。残した決済が発動中に約定すると bot は記帳しない。その結果、発動中は帳簿・status.json・KILL の通知が「LONG 0.01」のままになり(場所は板ではなく取引所の建玉が平らのとき)、解除して再起動すると最初の巡回でその約定を二重に記帳する。bot は存在しない SHORT -0.01 を持っていると思い込み、キルスイッチは発動していない状態で動き出す。直す前の版では、発動時の全取消しが約定を読み直して記帳していたので、この経路は今回の変更で新しくできたものである。しかも決済は MARKET で送るので、「板に残る」はたいてい直後に約定し、まれな場合ではなく普通に起きる。そのほか、試験が守っていない箇所が 3 つ変異で生き残った。また通知の英語の文が「手で閉じろ」と言い、残した決済と食い違っている。

- **[止める]** 残した決済が発動中に約定すると、再起動の後に存在しない逆の建玉を記帳する / `_adopt_fill_watermarks`(470 行付近)× `step` の `if not tripped: self._sweep_open_orders()`(702 行)/ 再現: `after boot position 0.0 tripped False` → `after first sweep position -0.01 trades 1` → `E assert -0.01 == 0.0`。原因: `_adopt_fill_watermarks` は記帳済みの印を手元の `filled_size`(0)まで進めるだけで、取引所の executed_size を見ない。直す前の版との比較(送った直後は ACTIVE、発動までに COMPLETED): `HEAD : state=FILLED cancels=1 pos=0.0` / `作業 : state=SUBMITTED cancels=0 pos=0.01`。直す方向: (a) 発動中も残した注文だけを読み直して記帳する(GET だけ)/ (b) `_adopt_fill_watermarks` を取引所の executed_size まで進める。
- **[直す]** 通知の英語の文が残した決済と食い違う(O-1 にも当たる): 日本語の行は「確かめてから」、英語の行は「The bot will NOT close it … Close it by hand」。
- **[直す]** 送信で `OrderStateUnknown` になった決済は、通知の行に載らず「手で閉じろ」とだけ案内される。`[timeout] state=STATE_UNKNOWN reason=order_state_unknown sends=1 cancels=0 pos=0.01`。自動の取消し・再送は無く、CLAUDE.md §1 は守られている。通知の detail は日次損失、`reason` は `order_state_unknown`。
- **[直す]** 送った後に `_submit_checked` が例外を出すと `sent` が None のままで、全取消しが決済を取り消す【推定】。
- **[直す]** RunLock の docstring「空のまま 900 秒を超えたものは死んだプロセスの残りでしかありえない」は言い過ぎ(作ってから書くまでの間に一時停止したプロセスも残しうる。隙間はマイクロ秒で、新しく弱まるわけではない)【推定】。
- **[直す]** 試験の不足: 変異 M5(PARTIALLY_FILLED を外す)・M7(mtime を `self._clock` と比べる)・M9(store の読み直しを省く)が `271 passed` で生き残る。通知の試験は `"ACC-CLOSE" in msg` だけ。発動中の約定→再起動・送信後発動前の約定・`OrderStateUnknown` と日次損失の重なりの試験が無い。
- **[聞く]** 直す方向 (a) は、L-532(発動中は巡回を止め、データだけを記録する)に触れる。読むだけなら範囲内とみなすか。
- ほかの発動の経路(KILL ファイル・API の誤りの連続・一時停止・未処理の例外)は `cancel_all_active(product_code)` のまま変わらない【事実】。欠陥 2: 台本は clock を渡していない(11 か所)ので mtime を `time.time()` と比べる理由は正しい【事実】。試験の実行 `737 passed`。

## リードの応答(1 回目)

- **[止める]** → (a) と (b) の両方で直す。作業者に差し戻した(2 回目)。
- **[聞く] L-532** → (a) は範囲内。L-532 の依頼は「**キルスイッチでデータの取得まで止まってしまう**」で、答えは「発動中も取得・記録を続け、取引だけ止める」だった(`docs/OWNER_STATUS.md` の L-532 の行)。注文の状態を読むのは取得・記録で、送信も取消しもしない。
- **[直す]** は全部直す: `_kill_message` 全体を日本語にし、残した決済・状態不明の決済があるときは「手で決済しない」案内にする。`OrderStateUnknown` と日次損失の両方の理由を出す。送信後の例外でも決済を外せるようにする。docstring を正確にする。試験の不足を埋める。
- 計画 §4-1 により、2 回目の批評家にも [止める] が出たら、直し続けずに止めて原因を出す。

## 2 回目の批評家(2026-10-02)

止める 1・直す 3・聞く 0

**読み(逐語)**: 1 回目に指摘した 3 つの再現は、直した版ではすべて正しく振る舞う。発動中の読み直しは、step を回した端から端までの試験でも送信・取消しが 0 件で、L-532 の「取引だけ止める」を守っている。PAPER と、注文が残っていない毎晩の LIVE の再起動は、`venue_fill` で止まらない。ただし新しく足した `_resume_kept_watch` が、発動したままの再起動のときに STATE_UNKNOWN と PENDING_SUBMIT も見張りに載せる。それを `match_once` で確定して記帳するので、1 回目と同じ種類の二重記帳が別の入口から戻ってきている。具体的には、起動のときに取り込んだ建玉(getpositions)の上に、その中にすでに入っている約定をもう一度記帳する。さらに起動直後は照合の基準に「前に見た注文」が無いので、1 週間前のオーナーの手の決済まで「bot の決済」として取り込み、取引所は LONG 0.01 なのに bot は平らと思い込む。毎晩 04:02 に再起動するので、この経路は普通に通る。ここを直すまではコミットしてはいけない。

- **[止める]** 発動したまま再起動すると、STATE_UNKNOWN の決済を照合で確定し、取り込んだ建玉の上に二重に記帳する。古い手の注文も取り込む / `_resume_kept_watch` × `recheck_kept` の `match_once` × `_adopt_fill_watermarks` / 再現: `[bot_real_order] … after watch pos=-0.01 rec=FILLED acc=ACC-BOT writes=[]`、`[owner_hand_close] … after watch pos=-0.01 … acc=ACC-HAND`、`[oldhand] venue=LONG 0.01 boot pos=0.01 after watch pos=0.0 rec=FILLED acc=ACC-OLDHAND`。原因: `adopt_stale_pending` が起動時に確定するのは PENDING_SUBMIT だけで印より前。STATE_UNKNOWN は印の段で素通りし、見張りが後で確定して記帳する。`AutoReconciler._match` は時刻で選り分けず、起動直後は `_observed` が空。
- 確かめたこと: 1 回目の再現 5 件は直った(`5 passed`)。発動後の送信・取消しは 0 件(`writes_after=[]`)。毎晩の再起動の普通の場合は止まらない(`[ok_flat_no_orders] tripped=False getchild_calls=0`)。指定の 14 ファイル `747 passed`。
- **[直す]** 変異の生き残り: N1(再起動時の見張りから STATE_UNKNOWN/PENDING を外す)・N3(見張りの間隔)・N4(LIVE だけの条件)・N5・N6 が `227 passed`。
- **[直す]** 発動中(再起動していない)にも、確かめた後のオーナーの手の決済を bot の決済として取り込みうる【推定】。
- **[直す・別件]** `tests/test_record_liquidations.py::test_a_second_that_still_saturates_is_recorded_as_truncated` は時間ではなく記憶に依存(`counts` が 6,481,800 項目、見積もり約 910MB + 返す行 約 810MB)。仮想記憶 950MB で単独に回すと `MemoryError`。
- 欠陥 2(鍵): docstring は直った。M7 を落とす試験が足された。

## リードの応答(2 回目)

- 計画 §4-1 により、欠陥 1 は直し続けずに止めた。原因と次の設計の不変条件は `docs/DISCUSSIONS/2026-10-02_kill_keep_close/README.md`。2 回目の差分は同じ置き場の `attempt_r2_shelved.patch` に退避し、作業ツリーから戻した。**2 回目の [止める] の直接の原因は、リードが追加で指示した「STATE_UNKNOWN・PENDING_SUBMIT も見張りに戻す」**。
- 欠陥 2 と Deribit の案内文は、2 回とも [止める] 無しなのでコミットした。
- [直す・別件] 清算の記録の試験の記憶 → 試験を直す(別のコミット)。
