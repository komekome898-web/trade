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
