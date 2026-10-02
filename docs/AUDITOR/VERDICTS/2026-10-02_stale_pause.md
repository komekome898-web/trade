# 批評家の記録: データが古いときの PAPER の一時停止(1c37399b、L-544)

- 対象: 1c37399b(作業ブランチ。PC のブランチには未反映)。
- 批評家: コードを変える委任の批評家(O-5)。指摘はオーナーへの返答に逐語で出した(O-4)。
- 応答の印: `直した` / `上申` / `採用しない` / `記録`(批評家が確かめた結果の報告で、直すものが無い項)。

---

## 批評家の出力(全文)

批評家の報告です。対象は 1c37399b(stale のとき PAPER だけ一時停止にする変更)。ファイルは何も変更していません。変異試験と実験は、src・tests・config を scratchpad に写した複製の上で行いました。実行後に複製と /tmp/pytest-of-root は消してあり、`git status --short` の出力は空です。

前提(事実): レビュー中に HEAD が 5ccb935f(merge)まで進みました。`git diff --stat 1c37399b HEAD -- src tests` の出力は空なので、以下の行番号は現在の HEAD でもそのまま使えます。
新しい試験 21 件は通りました(`PYTHONPATH=src python -m pytest tests/test_composite.py -k "stale or pause or resume or restart_does_not or price_jump_across or non_stale or no_data_ever or candles_from_before"` → 21 passed)。

### 1. [直す] 急変の検査を、一時停止の間ずっと外している(リードが足した変更、問い 5)

- 根拠: main.py:700 `self.feed.accept_price_jumps = tripped or self._stale_pause is not None`。データが戻ってから、新しいデータの足が 1 本完成するまで(60〜120 秒)のあいだ、すべての tick で急変の検査が外れています。再開を決める tick(10_260)の検査も外れています。feed.py:163 で急変を受け入れたあと、feed.py:147 でその値が `last_tick`(次の比較の基準)になります。
- 再現(実測。`_gap_app`・`max_price_jump_pct=5.0`、終了は 10_400):
  - A: `rig.hooks[10_250]` で +6%(ltp 10_600_000)、`rig.hooks[10_255]` で元の値段に戻す → 発動しない(`kill_switch.state` が None)。10_260 で再開。再開後に残る最初の足 10_200 の high と close が 10_600_000 になる。
  - A2: `rig.hooks[10_255]` で +6% にしてそのまま → 発動しない。再開後もその値段で動き続ける(終了時の `last_tick.price` は 10_600_000)。平常時なら同じ +6% は発動します。
  - A3: `rig.hooks[10_255]` で +6%、`rig.hooks[10_260]` で戻す → 再開の直後に「abnormal price jump 5.66% (from 10600000.0 to 10000000.0)」で永続の発動になる(誤った値段が基準になったための発動)。
- 害(推定): 本番の戦略 xborder は判断にリーダー(Binance)の値段を使います。そのため A・A2 の誤った値段は、paper の約定値段・損切りの判定・足の記録に入ります。A3 は安全側への誤発動です。「新しい足 1 本」の条件は、足の窓が空白をまたがないことは守っていますが、値段が正しいかどうかは何も確かめていません。
- 直し方の案: 急変を受け入れるのを、データが戻った最初の 1 tick だけに絞る。`accept_price_jumps = tripped or (self._stale_pause is not None and self._stale_pause["fresh_since"] is None)`。こうすると 2 tick 目からは平常時と同じ検査になります。

**応答: 直した。** 案のとおりの式にした(main.py の `accept_price_jumps`)。試験 `test_a_price_jump_after_the_first_fresh_tick_still_trips`(10_250 の終わりに +6%、10_255 の tick で発動、再開しない)。直す前の式に戻すとこの試験が落ちる(実測「1 failed, 1 passed」、もう 1 件は外れの間の急変を受け入れる既存の試験で、両方の式で通る)。

### 2. [聞く] §0.1 の照合: オーナーの承認文に該当語の無い挙動

| やろうとすること(実装) | オーナーの原文の該当語(逐語) |
|---|---|
| stale のとき建玉を閉じ、注文を止める | 「建玉を閉じて注文を止め」 |
| PAPER だけ | 「まず PAPER だけに入れます」 |
| 一時停止の間、急変の検査を外す(main.py:700) | **(該当語なし)** |
| 再開は「新しいデータだけでできた足が 1 本完成」してから。それより前の足を捨てる(main.py:1642) | **(該当語なし)**。原文は「データが戻ったら自動で再開する」 |

- 足を捨てる影響(事実): xborder の `min_history = k + 2`(xborder_momentum.py:25-26)、config の k は 30。再開してから 32 本(約 32 分)そろうまで、戦略は「insufficient history」で HOLD します。通知の「再開しました」と、実際に新しく建てられるようになる時刻が約 30 分ずれます。オーナーに見せるか、リードが判断してください。

**応答: 上申(L-547 で、急変の上限そのものが要るかを問われ、調べて答えた。上限を外すかと、再開の待ち方の 2 点が答え待ち)。** §0.1 により、該当語の無い行はオーナーに聞く。1 番を直したあとの実装は「データが戻った最初の 1 tick だけ急変を受け入れる」で、この形と、再開前の足を捨てる(再開後に約 32 分建てない)ことを `docs/OWNER_STATUS.md` の判断が要る項目に載せた。

### 3. [直す] 一時停止の通知が届かない筋書きがあり、再開の通知に決済の情報が無い(問い 6)

- 根拠(事実): paper_logs/bot.jsonl では、2026-09-27 06:07:53 の stale の発動と同じ時刻に `notify_failed SSLError` が出ています。PC 自身のネットワークが落ちていたということです。`_notify` は失敗を握りつぶします(main.py:548-554)。このため、一時停止の通知(main.py:1562)だけが失われ、オーナーには「データ回復」の通知だけが届く筋書きがあります(推定。観測は 1 回)。
- 再開の通知(main.py:1654)には「何を・いくらで決済したか」がありません。決済の文を再開の通知にも入れるか、データが戻った最初の tick で一時停止の通知を送り直す案があります。

**応答: 直した。** 再開の通知に、一時停止の理由と決済の文を入れた(一時停止の記録に `closed` を持たせた)。試験 `test_pause_and_resume_alerts_are_japanese_and_the_resume_repeats_the_close`。決済の文を外すとこの試験が落ちる(実測「1 failed」)。

### 4. [直す] 再び stale になったとき(relapse)の試験がない(問い 4・8)

- 変異 M9(main.py:1538 の `fresh_since = None` を消す)では、新しい試験 21 件がすべて通ります。
- 元のコードの挙動は正しいことを確かめました(実測 C)。データが 10_180 に戻り、10_230〜10_330 にまた途切れ、10_290 に再び stale になるようにしました。再開は 10_440、最初の足は 10_380、通知は 3 本(BOT START・停止・回復)でした。この筋書きをそのまま試験にできます(ticker を差し替え、`10_230 <= rig.now < 10_330` の間は `rig.error` を投げる)。

**応答: 直した。** その筋書きを試験にした(`test_stale_again_before_the_resume_restarts_the_resume_clock`。再開 10_440、最初の足 10_380、通知 3 本)。M9 を当てるとこの試験が落ちる(実測「1 failed」)。

### 5. [聞く] 決済が拒否されると建玉が残る(問い 3)

- 実測 B: `_close_for_stale_pause` の中で `_try_order` が None を返すようにしました → 建玉は -0.013 のまま残り、一時停止は続き、発動はしません。一時停止のあいだ注文の呼び出しは 0 件(損切りも再試行も無し)。通知には「0.013 が残っています」と出ます。
- 拒否が実際に起こりうる経路(コードで確かめた範囲): 端数の建玉(main.py の dust の分岐)、`DuplicateOrderError`。日次損失などリスク上限の拒否は `_on_kill` で発動に回るので、建玉が残る経路にはなりません。
- 建玉が残る間、一時停止が守っているのは「古いデータで新しく判断しないこと」だけです。建玉には再開まで損切りがありません。旧コードの発動も同じく損切りなしで凍結していたので、悪くはなっていません。違いは凍結が一時的になったことです。
- 選択肢は 2 つです: (a) 決済に失敗したら従来どおり発動する (b) データが戻った最初の tick で決済を試し直す。原文は「建玉を閉じて」です。PC に入れるのを止める理由にはなりません。

**応答: 上申 → オーナー決定 L-547「2.(a)」→ 直した。** 決済が拒否されて建玉が残ったら、従来どおり発動する(`test_a_refused_stale_pause_close_trips_as_before`。発動の分岐を外すと落ちる、実測「1 failed」)。

### 6. [注記] LIVE が一時停止に入る経路は見つからなかった(問い 1)

- 一時停止を設定しているのは main.py:1798-1803 の 1 か所だけで、`self.settings.mode is Mode.PAPER` が条件になっています。執行先(main.py:222・265)も同じ `settings.mode` で選ばれます。
- `resolve_mode`(settings.py:92-115)は Enum を返し、設定が中途半端な LIVE は起動を拒否します。PAPER に落ちて動き続けることはありません。
- 起動時の LIVE の照合に失敗すると発動になり(main.py:540 付近)、その後の stale は `tripped` の分岐で処理されます。
- 変異 M1(`Mode.PAPER` → `True`)は LIVE の試験 1 件で落ちます。
- `MarketDataStale` を投げるのは feed.py:196 だけで、`check_freshness` を呼ぶのは main.py:1788 だけです(`git grep` で他の利用者 0)。

**応答: 記録。**

### 7. [注記] stale 以外の異常が一時停止に化ける筋書きはない。逆に、stale を検出できない既存の穴がある(問い 2)

- 板の交差・スプレッド・非正の値段・急変は、step の中(main.py:718-723)で発動になり、ループ側の分岐には届きません。「データが一度も来ない」は `MarketDataAnomaly`(Stale ではない、feed.py:192-193)なので発動します。新しい試験で確かめられており、変異 M2(isinstance → True)は no_data_ever の試験で落ちます。
- 既存の穴 F(実測): 1 回の sleep で時計が 10_040 から 10_295 に飛び、起きた直後の取得は成功する、という筋書きです(PC のスリープ、または 1 回の取得が 60 秒を超えて結局成功した場合)。一時停止にも発動にもならず、戦略は空白をまたいだ窓 `[9960, 10020, 10260]` で判断しました。原因は、stale の判定が「取得に失敗した周の後」にしか効かないことです。今回の変更で生じた後退ではありませんが、「`_run_loop` の 1 か所で十分か」の答えは「十分ではない」です。
- 既存 D(実測): データが止まっている最中に再起動すると、「no market data received yet」で永続の発動になります。nightly_restart は 04:02 JST(deploy/nightly_restart.bat:26)で、bitFlyer の日次メンテナンス 04:00–04:10 JST(docs/OPERATIONS.md:634)と重なります。ただし過去にこの発動は 0 回でした(`grep -c "no market data received yet" paper_logs/bot.jsonl` → 0)。
- 未確認: メンテナンス中に ticker が 4xx(REJECTED、数えられる)を返すと、5 回 × 5 秒 = 25 秒で API_ERRORS の発動になり、60 秒の一時停止より先に来ます。メンテナンス用の HTML 本文なら `classify_body` で SAFE_RETRY 扱いになり、数えられません。bitFlyer が実際に何を返すかは未確認です。参考として、過去の発動 7 回はすべて `market data stale` で、`grep -c '"api_errors"' paper_logs/bot.jsonl` → 0 でした。

**応答: 記録。** 既存の穴 F と D は今回の変更で生じた後退ではない【事実: 批評家の実測】。この件では直さず、計画 第 5 版 W0(段 1 を閉じる報告・同時停止の原因)の入力に渡す。D(04:02 の再起動と 04:00〜04:10 のメンテナンスの重なり)は、起きれば永続の発動で paper が止まるので、W0 の報告で直し方の案を出す。

### 8. [注記] 時計・足・`candles.completed` を切る処理(問い 4)

- flow でない経路では、`fresh_since` も足の開始時刻も feed の時計(`tick.timestamp`)を使っており、一致しています。`time.time()` は `since` と `paused_sec`(表示のみ)にしか使われていません。
- `use_flow_candles` は既定 False(main.py:176)で、config に設定がありません(grep の結果 0 件)。この経路は今は使われていません。有効にすると、ローカルの時計と取引所の exec_date の時刻がずれます。また、ticker は正常で executions だけ失敗し続けると、再開できないまま止まり続けます。
- `completed[:]` をその場で書き換えても問題はありません。`.completed` を参照しているのは main.py だけで、毎周その場で読み直しています(grep で確認)。overlay と status は足に依存していません。

**応答: 記録。** `use_flow_candles` を有効にするときは、この 2 点を先に直す(今は使われていない)。

### 9. [直す] 表示・ログの小さな件(問い 6)

- status.py:79-87 の `format_report` に一時停止が無い。
- decision_text.py の `SIGNAL_JA` に `STALE_PAUSE` が無く、コンソールには英語のまま出る。
- ダッシュボードの main_bot の状態(aggregate.py:689-692)は status.json の更新時刻だけで決まるので、一時停止中も平常と同じに見える。
- 日本語の通知文の中に英語の detail(「market data stale: 65s > 60.0s」、main.py:1563)がそのまま入る(O-1)。
- 量は問題ありません。ログは開始時に 1 行、relapse ごとに 1 行で、周ごとに増える行はありません。status.json は従来どおり毎周書かれます。なお、データが止まっている間は 1 時間ごとの STATUS 報告が飛ばされます(既存)。

**応答: 直した(ダッシュボードの 1 点を除く)。** `format_report` に一時停止の行、`SIGNAL_JA` に `STALE_PAUSE`、決済の理由の日本語、通知の detail を日本語(`MarketDataStale.detail_ja`)にした。ダッシュボード(aggregate.py)は、W6 のレーン(L1)が同じファイルを作業中なので、L1 が終わってから直す。

### 10. [聞く] 最後に受け取った値段での決済が成績と判定に入る(問い 7)

- 大きさの見積もり(推定): 実測の元データは paper_logs/spread_FX_BTC_JPY.csv(42.7 日、529,690 行)です。60 秒〜1 時間の空白 48 回について、空白の前後の mid 価格の差を測りました。
  - 絶対値: 中央値 0.015%、上位 10% の境 0.13%、最大 0.36%。
  - 符号付き平均: -0.011%(方向の偏りは見えない)。
  - 1 回あたりの建玉(上限 13 万円)に換算すると、中央値で約 20 円、最大で約 465 円。
  - 48 回にはプロセスが止まっていた時間も含むので、頻度は上限です。
  - 過去の stale の発動 7 回は、すべて建玉 0.0 でした。
- 問題は偏りより、LIVE ではこの決済そのものが執行できないことです。
- 記録: main.py:1594-1602 に `STALE_PAUSE` として残り、spread CSV から前後の値段を後で復元できます。ただし `execution_price` が無いので、判定(scripts/judge_gates.py:289-330、gates.py:371-405、market_view.py の位置による組)はこれを普通の手仕舞いとして数え、値段には古い ltp を使います。損益は連敗数(portfolio.py:195、5 回で発動)にも入ります。
- 標本から外すか、印を付けるかを決めてください。

**応答: 上申 → オーナー決定 L-547「3.(ア)」→ 直した。** 標本に残し、`scripts/judge_gates.py` が `exit_signal == "STALE_PAUSE"` の手仕舞いを数えて G1 の注記に出す(`test_a_stale_pause_close_is_counted_and_marked`。数えを外すと落ちる、実測「1 failed」)。ダッシュボードの側(`src/bot/monitoring/gates.py`・`market_view.py`)の表示はまだ印を出していない。

### 11. [注記] 試験は主張を確かめているか(問い 8)

- 1c37399b~1(変更前)の src で新しい試験を回すと 21 件すべて落ちます。うち 9 件は `KeyError: 'data_stale_pause'` だけが理由です(LIVE 1、NON_STALE_FAULTS 7、no_data_ever 1)。これらは「挙動が変わらないこと」の回帰の見張りです。PAPER の NON_STALE_FAULTS 7 件は変更していない step の経路しか通らず、新しいコードへの変異では 1 件も落ちません。
- 変異の結果(新しい試験 21 件で): M1 Mode.PAPER→True → LIVE の試験 1 件が落ちる / M2 isinstance→True → no_data_ever 1 件 / M3 step の早期 return を外す → 3 件 / M4 ceil→floor → 4 件 / M5 足を捨てない → 2 件 / M6 accept=tripped に戻す → 1 件 / M8 決済を外す → 4 件 / M11 足の完成を待たない → 4 件 / M12 fresh_since を設定しない → 4 件 / M13 `_enter_data_only` で一時停止を消さない → kill_file の 1 件 / M14 停止の通知を外す → 9 件 / M9 relapse で fresh_since を戻さない → **全部通る**(4 番の穴) / M7 `_on_kill` で一時停止を消さない → 全部通る / M10 `not is_tripped` を外す → 全部通る
- M7 と M10 が生き残るのは、そのコードが `_enter_data_only` と `_kill_notified` と同じことを重ねてしているためで、試験が弱いからではありません。

**応答: 記録。** M9 の穴は 4 番で塞いだ。

### PC のブランチ(PAPER で動いている bot)に入れてよいか

1 番を直してから入れる、という読みです。直すのは main.py:700 の 1 式で、急変の受け入れを最初の新しい tick だけにします。LIVE と実弾に害が及ぶ経路は見つかりませんでした(6 番)。止める理由も見つかりませんでした。2 番(該当語なしの 2 行)は、入れる前にオーナーに見せるかどうかをリードが決めてください。3・4・5・9・10 番は、入れた後に直しても安全側を崩しません。過去の stale の発動 7 回はすべて建玉 0 だったので、入れた直後に決済の値段が成績へ与える影響は小さいと推定します。

**応答:** 1 番は直した。PC への反映(W7)の承認は、2・5・10 番の答えと W6(ダッシュボード)の批評家が済んでから求める。

---

# 2 回目の批評家(対象 a732b858)

## 批評家の出力(全文)

批評家(2 回目)の報告です。対象は a732b858 です。リポジトリのファイルは変えていません。commit・stash・checkout・reset も打っていません。

**作業の環境**
- 試験と変異は、`git archive a732b858 src tests config pyproject.toml | tar -x -C <scratchpad>/critic2` で取り出した複製の上で行いました。作業ツリーには W6 の未コミットの変更があるため、作業ツリーからは写していません。比べるために、1c37399b の src・config も `critic2/old` に取り出しました。
- 注意: pyproject の `pythonpath = ["src"]` が PYTHONPATH より優先されます。このため old の実行は `-o pythonpath=old/src` で行い、読み込まれたモジュールのパス `.../critic2/old/src/bot/main.py` を出力して確かめました。
- 終了時に、自分が作ったもの(src・tests・config・scripts・pyproject.toml・old・mut_c2.py・critic2_pt)は消しました。critic2 に残っている g7_check.py・mut.py・mut2.py・__pycache__ は 10-01 の日付で、私が作ったものではないので残しています。
- `git status --short` の M と ?? はすべて、私の作業ではありません。M は aggregate.py・dashboard.py・test_dashboard.py・docs/OPERATIONS.md・deploy/*.bat など、?? は scripts/record_*.py・tests/research/ などです。
- **レビューの間に HEAD が 68108933 まで進みました。** 新しく入った 59927c6d(「決済が拒否されたら発動する」、main.py に +10 行)は、この批評の範囲外で、検査していません。下に書く行番号はすべて a732b858 のものです。

### 問い 1. 1 番の直しは A・A2・A3 を塞いだか

**[注記] 塞いだ(事実)。**

コマンド: 一時的な試験ファイルで、`_gap_app(until=10_400)`、`max_price_jump_pct=5.0`、hooks で値段を差し替えました。新しいコードは `PYTHONPATH=src python -m pytest tests/test_zz_critic2.py ... -s`、古いコードは `-o pythonpath=old/src` で回しました。

新しいコード(a732b858)の結果:
```
[A]  trip_t=10255.0 state=abnormal price jump 6.00% (from 10000000.0 to 10600000.0) ... alerts=['BOT START','データ停滞: 取引を一時停止','KILL SWITCH'] strat_after=[]
[A2] trip_t=10260.0 state=abnormal price jump 6.00% (from 10000000.0 to 10600000.0) ... strat_after=[]
[A3] trip_t=10260.0 state=abnormal price jump 6.00% (from 10000000.0 to 10600000.0) ... strat_after=[]
```

古いコード(1c37399b)の結果。1 回目の批評家の再現と一致します:
```
[A]  trip_t=None resume_t=10260.0 first_candle=(10200, 10600000.0, 10600000.0) strat_after=[10260.0, 10320.0, 10380.0]
[A2] trip_t=None resume_t=10260.0 last_tick=10600000.0
[A3] trip_t=10265.0 state=abnormal price jump 5.66% (from 10600000.0 to 10000000.0) alerts=[...,'データ回復: 取引を再開','KILL SWITCH'] strat_after=[10260.0]
```

読み:
- A・A2・A3 はどれも、誤った値段の tick そのもので発動するようになりました。発動の記録は「from 正 to 誤」です。
- 発動は再開の前に起きます。戦略は呼ばれません。

新しく生じた害: オーナーが例に挙げた「データが戻った最初の tick が誤った値段」の筋書きを回しました。比べるために、平常時の 1 tick だけの誤値(N)も回しています。

```
新: [B1] hooks{10_175:+6%, 10_180:戻す} → trip_t=10185.0 state=abnormal price jump 5.66% (from 10600000.0 to 10000000.0) strat_after=[]
新: [B2] hooks{10_175:+6%, 10_255:戻す} → trip_t=10260.0 state=... (from 10600000.0 to 10000000.0) strat_after=[]
新: [B3] hooks{10_175:+6% のまま}      → trip_t=None resume_t=10260.0 first_candle=(10200, 10600000.0, 10600000.0) strat_after=[10260.0, ...]
旧: [B1] trip_t=None resume_t=10260.0   旧: [B2] trip_t=None first_candle=(10200, 10600000.0, ...)   旧: [B3] 新と同じ
対照 [N] 平常時に 1 tick の +6% → trip_t=9705.0 (from 10000000.0 to 10600000.0)
```

- [注記] B1・B2 は 1 回目の A3 と同じ形です。誤った値段が基準になり、正しい値段に戻る動きが急変として扱われて、永続の発動になります。
- ただし A3 より悪くはなっていません(事実、上の出力)。古い A3: 再開の後に発動し、その前に戦略が 1 回呼ばれていました(`strat_after=[10260.0]`)。新しい B1: 再開の前(10_185)に発動します。建玉は一時停止のときに閉じてあり、戦略は呼ばれません。平常時(N)でも、1 tick の誤値は発動します。新しいコードの B1 は、平常時と同じ安全側の発動が 1 tick 遅れて来るものです。古いコードでは B1 は発動しませんでした。発動が増えたのは、この直しの代わりに生じた変化です。
- [注記] 発動の記録が「from 誤 to 正」になります。調べる人には、正しい値段のほうが急変の行き先に見えます。調べる人を誤らせうる点です。
- [注記] B3(最初の tick が誤っていて、その値段が続く)では、誤った値段の上で再開します。これは新旧で同じです。今回の後退ではなく、「データが戻った最初の 1 tick は検査しない」という設計の残りです。この設計はリードがオーナーへ上申している 2 番です。リーダー(Binance)の値段と突き合わせる案はありますが、必須ではありません。
- 起こる頻度: 実測(事実):
  ```
  python3 -c "...paper_logs/spread_FX_BTC_JPY.csv ..."
  rows 529691 days 42.7 / gaps>60s 57
  first->second fresh tick ltp jump %: max 0.781 median 0.0106 n>5% 0
  across-gap ltp jump %: max 7.471 ... n>5% 1   (この 1 件は 2026-09-21T01:29 の 693,876 秒 = 約 8 日の停止をまたいだもの)
  ```
  読み(推定): B1 の形は 57 回の空白で 0 回でした。未確認: bitFlyer のメンテナンス明けの最初の tick が不正確になりやすいかどうか。

### 問い 2. 3 番の直し: 再開の通知に理由と決済が入ったか、「None」が出る経路はあるか

[注記] 入りました。「None」が出る経路は、たどった範囲で見つかりませんでした(事実)。

コードの読み:
- `closed` は main.py:1545-1547 で None として作られ、決済が成功し、かつ発動していないときだけ main.py:1564 で設定されます。
- 決済の途中で例外が出たとき(1555-1561)と、決済が発動を起こしたとき(1562-1563)は、`_on_kill`(1436)か、次の周の `_enter_data_only`(1481)で `_stale_pause = None` になります。
- step は発動中なら、再開を判定する前に return します(main.py:758-760)。発動中は再開の通知に届きません。
- relapse(1536-1543)は早めに return するので、`closed` は残ります。

実測(`_gap_app` で筋書きを作り、通知の本文を出力しました):

| 経路 | 通知 | 通知の本文に「None」 |
|---|---|---|
| P1 決済の途中で例外 | BOT START, KILL SWITCH(pause=None) | False |
| P2 決済の中で発動(`_on_kill` を通らない) | BOT START, KILL SWITCH(pause=None) | False |
| P3 relapse(建玉あり) | 停止・回復の 2 本。再開の本文は「一時停止のときの決済: 売り建玉 0.013 を最後に受け取った値段(買値 9999000.0 / 売値 10001000.0)で決済しました」 | False |
| P4 決済が拒否された | 再開の本文は「…決済ができず、0.013 が残っています」 | False |
| P5 建玉なし | 「一時停止のときの決済: 建玉はありません」 | False |

- P4 は、HEAD の 59927c6d で「発動する」に変わっています。その版は検査していません(未確認)。
- 変異 M17(main.py:1564 を消す。再開の通知に「None」が出る)は、`test_pause_and_resume_alerts_are_japanese_and_the_resume_repeats_the_close` で落ちます。結果は「1 failed, 25 passed」です。
- [注記] 細かい点: 本文は「(最後に市場データを受け取ってから 65 秒(上限 60 秒))」と括弧が二重になります。値段は「9999000.0」と .0 付きで出ます。読めないものではありません。

### 問い 3. 4 番の試験は M9 を捕まえるか

[注記] 捕まえます(事実)。
- 変異 M9: main.py:1542 の `self._stale_pause["fresh_since"] = None` を `pass` に置き換え。
- 結果:
  ```
  == M9 relapse does not reset fresh_since
  FAILED tests/test_composite.py::test_stale_again_before_the_resume_restarts_the_resume_clock
  1 failed, 25 passed, 164 deselected
  ```
- 同じ回に当てたほかの変異(試験は、一時停止に関係する 26 件): M15 古い式に戻す(一時停止の間ずっと急変を受け入れる) → `test_a_price_jump_after_the_first_fresh_tick_still_trips` が落ちる / M16 一時停止の間は一度も受け入れない → `test_a_price_jump_across_the_outage_resumes_instead_of_tripping` が落ちる / M17 `closed` を保存しない → 3 番の試験が落ちる / M18 再開の通知から決済を外す → 3 番の試験が落ちる / M19 停止の通知の理由を英語の detail に戻す → 3 番の試験が落ちる / M20 再開の通知の理由を英語の detail に戻す → 3 番の試験が落ちる。すべて 1 failed でした。終了後に main.py を元に戻し、差分が 0 であることを確かめました。

### 問い 4. 英語の残り、例外のメッセージ、別の引数で作っている箇所

- **[直す] 小さな件。`format_report` に足した一時停止の行(status.py:87-89)が英語で、Unix の時刻をそのまま出しています。**
  - この文は STATUS の通知としてオーナーに送られます(main.py:1802 `self.notifier.send("STATUS", self.status.format_report())`)。
  - 実測の出力:
    ```
    errors=0 kill_switch=None
    data_stale_pause=since 1790489273.512 fresh_since=1790489310.0
    ```
  - STATUS の報告の既存の行もすべて英語です。ただ、この行は 9 番の直しとしてこのコミットで新しく足されたもので、O-1 と O-6(意味の分からない数字)に当たります。
  - 送られる時期: `check_freshness` を通った後なので、データが戻ってから再開するまで(約 60〜120 秒、relapse があれば延びる)の間に、1 時間ごとの報告の時刻が重なったときだけです。
  - 「fresh_since=None」はこの経路では実際には出ません。成功した poll と同じ step で `fresh_since` が設定されるためです(main.py:717-721)。
  - 日本語の文と JST の時刻にする案があります。
- [注記] 通知の本文は日本語になりました。停止の通知(1568-1574)と再開の通知(1664-1670)は、英語の detail を含みません。P3〜P5 の本文で確かめました。`signal_ja('STALE_PAUSE')` は「データ停滞で一時停止」、決済の理由は「データ停滞: 最後に受け取った値段で paper の建玉を決済」になります(実測)。残っている英語(この差分の外で、前からあるもの): KILL SWITCH の通知の本文(`_kill_message` の「OPEN POSITION … The bot will NOT close it …」と、`str(e)` の detail。P1 の本文は「unhandled exception while pausing on stale data: RuntimeError('x')」)/ ダッシュボードの `reason_ja('market data stale: 65s > 60.0s')` は英語のまま返る(実測)/ コンソールの StreamHandler(logging_setup.py:63)に出るログは英語(docstring は「英語はログ用」)/ HEAD の 59927c6d の発動の detail は、英語の文に日本語の `closed` を挟んでいる(読んだだけで、検査していない)。
- [注記] 例外のメッセージの文字列は前と同じです(事実)。前と後の式は同じ `f"market data stale: {age:.0f}s > {limit}s"` で、limit には同じ `self.max_staleness_sec` が渡されます。実測: (65.4, 60.0) → `'market data stale: 65s > 60.0s' True`、(65.4, 60) → `'…60s' True`、(900.0, 60.0) → True、(61.0, 90.0) → True。`e.args == (msg,)` で、`isinstance(e, MarketDataAnomaly)` も True でした。ログを読む側の `grep "market data stale"` は壊れません。前からある注意: 1c37399b 以降、一時停止の開始・relapse・決済の判断ログにも "market data stale" という語が入っています。発動の回数をこの語の grep で数えると、多めに数えます。
- [注記] `MarketDataStale` を別の引数で作っている箇所はありません。コマンド: `git grep -n "MarketDataStale" a732b858 -- src tests scripts deploy`。作っているのは feed.py:205 の `raise MarketDataStale(age, self.max_staleness_sec)` だけでした。ほかは import と isinstance と docstring です。試験は `MarketDataAnomaly("market data stale…")` を使っていて、`MarketDataStale` は作っていません。
- [注記] 独自の __init__ の副作用として、copy と pickle が壊れます。実測: `copy FAIL TypeError MarketDataStale.__init__() missing 1 required positional argument: 'limit_sec'`。pickle も同じエラーです。`grep -rn "QueueHandler\|multiprocessing\|pickle\|copy.copy\|deepcopy" src/bot` の結果、bot の実行経路には該当がありませんでした。今は害がありません。

### 問い 5. 差分を敵対的に読む

- [注記] 関係する試験はすべて通ります。コマンド: `PYTHONPATH=src python -m pytest tests/test_app_fx_integration.py tests/test_composite.py tests/test_dashboard.py tests/test_market_data.py tests/test_market_view.py tests/test_paper_state.py tests/test_realtime_recorder.py tests/test_resilience.py tests/test_xborder.py tests/test_judge_gates.py --basetemp=… -p no:cacheprovider`。結果: 657 passed。複製に scripts も写して回しました。全部の試験は、複製に docs が無いため回していません(未確認)。
- [注記] relapse と新しい式の組み合わせ。relapse で `fresh_since` が None に戻るので、次にデータが戻った最初の tick でも急変を受け入れます。設計と一致しています。60 秒未満の短い途切れでは relapse にならず、平常時と同じ検査になります。
- [注記] `_stale_pause_view` に `detail_ja` と `closed` が増え、status.json に出るようになりました。どちらも文字列なので JSON にできます。
- 壊したものは見つかりませんでした。

### PC のブランチ(PAPER で動いている bot)に入れてよいか

入れてよい、という読みです。[止める] はありません。1 番の直しで A・A2・A3 は実測で塞がっていて、誤った値段で戦略が動く筋書きはなくなりました。新しく生じた発動(B1・B2)は、平常時の 1 tick の誤値と同じ安全側の発動です。再開の前に起き、建玉も 0 です。実データの 57 回の空白では 0 回でした。[直す] は STATUS の報告の英語の 1 行(status.py:87-89)だけで、送られる時期はまれです。入れた後に直しても安全側を崩しません。上申中の 2・5・10 番は、リード自身の記録どおり、PC に入れる前の関門として残っています。HEAD の 59927c6d(5 番の (a) の実装)は、この批評では見ていません。PC に入れるのがその版なら、別に批評家を通してください。

## リードの応答

- 問い 4 の [直す](STATUS の報告の英語の行): **直した。** 日本語の文と JST の時刻にした(`_stale_pause_line`、試験 `test_status_report_shows_the_pause_in_japanese_with_jst_times`)。
- 問い 1 の [注記] B1・B2・B3: **記録。** どれも「急変の上限」の挙動。オーナーが L-547 で上限そのものが要るかを問い、リードは外す案を出して答えを待っている。外すなら B1〜B3 は消え、残すなら B1 の「from 誤 to 正」の記録の読みにくさを直す。
- 59927c6d(決済が拒否されたら発動)とこの直しは、2 回目の批評の範囲外。急変の上限の答えを受けてコードが決まったところで、まとめて 1 回批評家に通す(監査を増やさないため。F6)。PC への反映はその後。
- その他の [注記]: **記録。**

## オーナーの決定 L-548 の反映

- 「1.外す」: 急変の上限(`max_price_jump_pct`)を feed・main・config から外した。2 回目の批評家の B1〜B3 はこれで消えた(急変を理由とする発動が無くなったため)。試験は、上限を戻す変異で 4 件落ちる(実測「4 failed, 194 passed」)。
- 「後半はこのまま」: 再開の待ち方は変えない。
