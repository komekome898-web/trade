# 項目 0「核」第 1 周 批評家の記録(5 回目の起動の再開後、新しく起こされた批評家)

委任文: `docs/DATA/delegations/20260923_backtest_env_prompt.md`(指紋 `20260923_backtest_env_prompt.md@f9fe736bfcff`)。
手元に置いたもの: 固定した要件 `item_0/REQUIREMENTS.md`、場面集 `tests/bt/battery/item_0/DEFINITIONS.md`(`scenes.py` から生成。`python3 gen_definitions.py --check` → `OK`)、検討表 `tests/bt/battery/item_0/opponents/CONSIDERED.md`、資料係の adapter `adapters/new_impl.py`、この周の実行の表 `round_1/materials/runs/*.tsv`。
合意した完了の形(委任文 §0 の逐語): 「**すべてが調査結果以上の信頼性と再現性に優れたものにすること。**」

## 0. 実行したコマンドと出力(要点)

- `PYTHONPATH=src python -m pytest tests/bt/item_0 tests/bt/critic/item_0 tests/bt/battery/item_0`(着手時、自分の試験を足す前)→ `4 failed, 223 passed in 3.16s`。落ちたのは前の批評家(17:52 に書かれ、指摘の記録が残っていない)の試験 `test_r5c1_*` の 4 件。
- 自分の試験を足したあと `PYTHONPATH=src python -m pytest tests/bt/critic/item_0` → `11 failed, 11 passed in 0.48s`(記録 `/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/pytest_item0_r1_critic.log`)。
- `PYTHONPATH=src python3 tests/bt/battery/item_0/run_battery.py --target new_impl --out …/item0_r1_critic_new_impl.tsv` → `{'正解と一致': 32}; 2 回で違う=0`。`PYTHONPATH=src python3 tests/bt/battery/item_0/mutant.py --check` → `changed scenes: ['p4-received-time']` / `OK`。
- `python3 scripts/check_bt_considered.py tests/bt/battery/item_0/opponents/CONSIDERED.md` → `OK 誤り 0 件`(形と語だけの検査。中身は下の i0-r1-16・i0-r1-17 で見た)。
- 規模の実測 `…/scratchpad/bt/item0_r1_critic_scale.py`(記録 `item0_r1_critic_scale.log`): 約定 25,000 / 100,000 / 200,000 件で 1.90 s / 8.49 s / 17.82 s(tracemalloc を付けた計測)。件数に比例しており、二乗ではない。

## 1. 前の周の指摘(i0-r1-01〜04)を自分で確かめ直した結果

| id | 前の格付け | 確かめ方 | 結果 |
|---|---|---|---|
| i0-r1-01 | [止める] | `test_order_request_id_consistency.py` を実行 → 通過。`api.py:180-193` で `place` が採番した `client_order_id` を入れた要求を outbox に積み、`engine.py:540` がそれを記録する | 直った |
| i0-r1-02 | [直す] | `test_visible_events_n_zero.py` → 通過。`api.py:382-384` で `n <= 0` は空 | 直った([止める] に付け直す必要なし) |
| i0-r1-03 | [止める] | `test_engine_run_scales_quadratically.py` → 通過。自分でも 25,000〜200,000 件で測り、時間は件数に比例(上の記録) | 直った |
| i0-r1-04 | [直す] | `test_liquidation_has_no_account_hook.py` の 2 件 → 通過。`interfaces.py:162`・`engine.py:557-558` | 直った |

**場面集の規則 8(批評家の試験の誤り)**: 作業者は `test_liquidation_has_no_account_hook.py` の 2 件目が試験自身の誤りで落ちると報告した((a) `side="long"`、(b) 記録用の口座に `apply_liquidation`・`on_market_event`・`check_order` が無い)。自分で確かめた: `events.py:291` は清算の向きに `buy`/`sell` しか受けず、`engine.py:231-237` の `_require_protocol` は口座の 5 つの方法が無いと構築時に拒む。よって作業者の診断は正しい(試験自身の誤り)。この試験は 17:52 に前の批評家が 2 点とも直しており(ファイル冒頭の注記)、主張(清算が口座の口に届く)は変わっていない。直した版は通る。取り下げるものは無い。

## 2. この周の指摘

格付けは委任文 §3「格付けの基準」どおり。根拠の行番号は着手時のファイル。

### 実装(`src/bot/bt/core/`)

**i0-r1-05 [止める] 発注の路が FIFO でない(取消が新規に追い越される)**
- `engine.py:14-19` と `ordering.py` の `ORDERING_RULE["channels_fifo"]`(221 行)は「戦略 → 取引所の注文・取消は FIFO、後の要求は前の要求を追い越さない」と言う。一方 `_drain`(engine.py:538・545)は着く時刻だけを単調にし、同じ時刻に着いた要求は優先度 `VENUE_ORDER = 10 < VENUE_CANCEL = 11`(ordering.py:179-180)で並ぶ。規則の文(ordering.py:90-91「then orders arriving at that instant, then cancels」)と FIFO の約束が食い違っている。
- 試験 `tests/bt/critic/item_0/test_r5c1_outbound_channel_fifo.py`(前の批評家が書いたもの。自分で読み、実行して確かめた): 取消 X → 新規 Y の順に送ると、取引所は `[('new','X'), ('new','Y'), ('cancel','X')]` の順で受ける。例外は出ない(黙って順が変わる)。

**i0-r1-06 [止める] 通知の路が FIFO でない(戦略の見る注文の状態が取引所と食い違う)**
- `_handle_reports`(engine.py:676-680)は届く時刻を `max(venue_time + delay, self._last_notice)` で揃えるので、遅い通知と速い通知が同じ時刻に並び、そこから先は型の優先度(ORDER_ACK < ORDER_FILL < ORDER_STATE_UNKNOWN、ordering.py:158-162)で並ぶ。
- 試験 `test_r5c1_notice_channel_fifo.py`(同上): 状態不明(10 ms)→ 受付・約定(0 ms)の順に取引所が出すと、戦略には `['ORDER_ACK','ORDER_FILL','ORDER_STATE_UNKNOWN']` の順で届き、取引所の台帳は FILLED、戦略の見る状態は STATE_UNKNOWN のまま終わる。

**i0-r1-07 [止める] 取引所側の台帳が STATE_UNKNOWN で履歴を失い、矛盾した報告を通す**
- `_VenueLedger.apply` は取消に対する StateUnknown でも注文の状態を UNKNOWN に書き換え(engine.py:211-212)、UNKNOWN からは 2 回目の Ack(180-182)と新規の拒否(184-187)を受ける。受付済み・一部約定済みの注文が REJECTED で終わる。`interfaces.py:8-16` の「矛盾は VenueProtocolError で止める」に反し、約定の模型の誤りを黙って通す。
- 試験 `test_r5c1_ledger_accepts_contradictions_after_unknown.py`(同上): 2 件とも `VenueProtocolError` が出ない。対照(Canceled で解消)は通る。

**i0-r1-08 [止める] 未来の時刻からの読み出し(`since_ns > now_ns`)が止まらず空で返る(P0-4)**
- 固定した要件 P0-4(REQUIREMENTS.md:20)の測り方の逐語: 「戦略側から未来時刻の事象を読もうとするコードが、実行時エラーか型エラーで止まるかを見る(**素通りしたら不合格**)」。`visible_events` は `until_ns > now_ns` だけを `LookAheadError` で止め(api.py:354-359)、`since_ns > now_ns` は空の組を返す(api.py:362・377-388)。
- 資料係の実行の記録にも出ている: `round_1/materials/runs/new_impl.tsv` の p4-future-read-attempt「ctx.visible_events(since_ns=5 本目の時刻) -> []」。
- 試験 `tests/bt/critic/item_0/test_i0r1_since_future_is_silent.py`: `returned ()`。

**i0-r1-09 [止める] 戦略の見る注文の状態から STATE_UNKNOWN が、取引所の答え無しに消える**
- `_OrderPort.cancel` は STATE_UNKNOWN を PENDING_CANCEL に替え(api.py:203-206)、取消の拒否が届くと、受付を一度でも受けていれば OPEN、無ければ PENDING_NEW に戻す(api.py:250-252)。注文そのものについて取引所は何も解消していない(台帳は STATE_UNKNOWN のまま)。CLAUDE.md §1 の「状態不明は確定するまで保持」と `events.py:355-360`・`api.py:113` の約束に反し、黙って誤った状態を見せる。
- 試験 `test_i0r1_state_unknown_lost_on_cancel_reject.py`: 台帳 `STATE_UNKNOWN`、戦略の見る状態 `OrderState.OPEN`。

**i0-r1-10 [止める] 1 本の入力の中の同時刻・別の型の事象を、入力の順ではなく型の順に並べ替える**
- `ordering.py:120-126` は同じ型なら 1 本の入力の中の順(「取引所の出した順」)を守ると書くが、別の型なら同じ流れの中でも型の順(ordering.py の TYPE_ORDER、151-164 行)で入れ替える。取引所が 1 本の記録で「約定 → その約定で減った板の差分」の順に出したものが、約定の模型と戦略には「差分 → 約定」で届く。データ層がこの順を保つ手段も無い。項目 3 の「列の位置の追跡」では、同時刻の約定と板の減りの前後がそのまま「約定で消えたか取消か」の情報なので、信頼性を崩す。
- 試験 `test_i0r1_same_stream_cross_type_reordered.py`: 取引所側 `['BOOK_DELTA','TRADE']`。

**i0-r1-11 [止める] 長さ 0 で値幅のある足(始まりの時刻で打たれた足)を受け付ける**
- `events.py:24-27` は「足は完成の時刻で打つ。始まりの時刻で届けると高値・安値・終値が先に見える」と書くが、検査(254-261 行)は `start_time_ns > exchange_time_ns` しか拒まない。`start_time_ns == exchange_time_ns` で高値 110・安値 90 の足が通り、始まりの時刻に届く = 文書が防ぐと言う先読み(P0-4)がそのまま通る。
- 試験 `test_i0r1_zero_length_bar_with_range.py`: `DID NOT RAISE EventValidationError`。

**i0-r1-12 [止める] 配信の遅延が揺れると、1 本の入力が自分自身を追い越す**
- `ordering.py:116-118`「Inside one stream the stream's own order is kept」。しかし `_ingest`(engine.py:407-417)は事象ごとに `received_time_ns + feed_delay_ns(event)` で届けるだけで、同じ流れの前の事象との前後を保たない。項目 4 の「実測の分布・種つきの乱数」の遅延を差すと、同じ流れの後の約定が前の約定より先に戦略に届く。注文と通知の路には FIFO の揃えがあるのに、配信の路だけに無い。
- 試験 `test_i0r1_feed_delay_reorders_one_stream.py`: 戦略が受けた順 `[101.0, 100.0]`。

**i0-r1-13 [止める] `end_time_ns` が int64 ナノ秒として検められず、`history_limit` は走行の途中で落ちる(P0-2)**
- P0-2(REQUIREMENTS.md:18)「他の単位が核の内部表現に混入しないこと」。`CoreEngine.__init__` は `end_time_ns` をそのまま持ち(engine.py:347)、float でも受けて待ち行列の時刻と比べる(430 行)。秒の値(1,700,006,400)も黙って受けて 0 件で終わる(`stopped_at_end_time=True`)。`history_limit=2.5` は構築を通り、5 件を届けたあと `TypeError: slice indices must be integers` で落ちる(engine.py:528)。
- 実測(python3 の試し打ち): `end_time 1.7e+18 accepted; processed 0 stopped True` / `end_time 1700006400 accepted; processed 0 stopped True` / `hl 2.5 TypeError slice indices must be integers or None or have an __index__ method`。
- 試験 `test_i0r1_end_time_not_validated.py`(2 件とも落ちる)。

### 場面集・検討表(場面係の持ち物)

**i0-r1-14 [止める] P0-4 の能力の場面が、固定した要件より弱い正解を置いている**
- REQUIREMENTS.md:20 は「実行時エラーか型エラーで止まるか(素通りしたら不合格)」。場面 `p4-future-read-attempt` の導き方は「どの公開の手段でも 104 は得られない(**例外・空の結果・拒否のどれか**)」(scenes.py の該当の add)で、空の結果・切り詰めた結果を正解と一致に数える。
- 結果: 調査結果の側で qf-lib は「get_price(..., 5 本目の日 + 1 日) -> [100.0, 101.0, 102.0, 103.0]」(黙って切り詰めた)で正解と一致(`runs/opp_qf_lib.tsv`)、zipline-reloaded は値を返したまま正解と一致(`runs/opp_zipline_reloaded.tsv`)、新実装も `since_ns` の空で素通りしている(i0-r1-08)。要件どおりに測れば、この場面の正誤は変わりうる。場面集が要件の観点を満たしていない。

**i0-r1-15 [止める] P0-5 の「規則どおりの順で処理されるか(値)」を測る場面が無い**
- REQUIREMENTS.md:21 の測り方は「値+再現: 同時刻に複数型の事象を仕込んだ入力を作り、**規則どおりの順で処理されるか(値)**、2 回実行して一致するか(再現)」。場面集の P0-5 は `p5-same-time-twice`(正解 `same_order_in_two_runs: True` = 2 回の一致。種別は「値」だが中身は再現)、`p5-hand-over-order`(異なる並びの数 = 1)、`p5-same-stream-order`(同じ型 2 件の入力の順)の 3 つで、複数の型の同時刻の並びが、その対象が明記した規則と一致するかを見る場面が 1 つも無い。規則と違う順で処理しても、毎回同じなら 3 場面とも正解と一致になる。

**i0-r1-16 [止める] 検討表の「上位互換」が 1 能力ずつ裏付けられていない**
- 規則(委任文 §3「動かせない候補の検討と再現」): 上位互換 =「スキップする候補のその観点の能力を 1 つ残らず含むことを、調査報告の行で 1 能力ずつ示す」。
- 例: 候補 70 PineForge(P0-5、CONSIDERED.md の P0-5 の表)。SCAN 7974 行の機構は「**足の内側の道筋を幾何として持ち、交差の時刻を事象の座標にする形**」(足の中の事象に交差の時刻を与えて並べる)。検討表はこれを hftbacktest の `p5-hand-over-order`(4 つの入力を渡す順によらない並び)に対にしているが、この場面は足の内側の順番付けを測らない。実装で確かめた候補(「確かめた(7974 行は実装の原典に到達した記録)」)なので、上位互換が立たなければ再現の対象になる。
- 仕組みの問題: 各観点の冒頭で「この観点の能力は N つ(REQUIREMENTS.md …)」と場面の数だけ能力を決め、候補の能力をその場面に写しているため、場面に無い能力は検討表に現れようがない(例: 候補 52 QuantConnect の P0-6 行は「発注・取消の API の名前は 6151 行に無い」とするだけで、6151 行の「約定の模型を差し替え可能な部品として外に出していること」は P0-7 でも Backtrader の 1 場面に写すだけ)。

**i0-r1-17 [止める] grep で当たったのに候補に写せなかった 90 行が、検討表で 1 件も検討されていない**
- `pool.tsv` の末尾「# unmapped grep hits」は 90 行(P0-2: 1、P0-3: 74、P0-4: 1、P0-5: 10、P0-7: 4。`sed -n '/# unmapped/,$p' pool.tsv | tail -n +2 | cut -f1 | sort | uniq -c` の出力)。CONSIDERED.md にはこの 90 行への言及が無い(`grep -n "unmapped" CONSIDERED.md` → 0 件)。
- 例: P0-4 の SCAN 3166 行は、REQUIREMENTS.md:98 が P0-4 の当たりとして挙げた行(「先読みは防いでいるが、約定しない可能性は模型に無い」)。SCAN 3163-3166 行の表の 3 行目が `Luczinsritter/event_driven_backtesting_engine`(候補 16)、4 行目(3166 行)は「同エンジンには…」で同じ候補を指す。それでも CONSIDERED.md の P0-4 は「動かせなかった候補 0 件: この観点の候補の集まりは 62 qf-lib の 1 件だけ」と書く。L-413「動かせないからと言って機構を検討せず無視することを避ける」と、委任文の「候補は…機械で全部抜き出す(人が足し引きしない)」に反する。

### 資料係の adapter の公平さ(見た結果、指摘なし)

- `adapters/new_impl.py` は `core.<名前>` だけで核を呼び、約定の模型(`_ArrivalFill`)と口座(`_CashAccount`)は公開の差し込み口に差した小さな代役(場面が許す「対象の公開の差し込み口」)。核の属性の書き換えは無い。`mutant.py --check` は `OK`。
- 場面ごとの呼び方で新実装だけ有利になる箇所は見つからなかった。調査結果の側は「動かせた道具のうち最も良い結果」を寄せており(例: backtrader は既定の `preload=True` では 104.0 を読めたが、`preload=False` の結果を寄せた = 相手を強くする向き)、新実装に有利な向きではない。
- 当方の現状の adapter(`current_impl`)は p2 の時刻の変換に pandas を当てるなど、相手を強くする向きの呼び方で、新実装に有利な向きではない。

## 3. 周の数え(委任文 §3「周回の数え方と止める条件」4)

- 引き継いだ指摘 i0-r1-01〜04 は、自分で確かめて全部直っていた(上の §1)。今回の指摘に、前の指摘と同じ原因のものは無い(repeat_of は全部空)。
- i0-r1-05〜07 は 17:52 に前の批評家が試験だけを残したもので、その批評家の指摘の記録は渡されていない。この周の指摘として自分で確かめ直して挙げた(試験のファイル名は変えていない)。
- 場当たりの直し(試験だけの特別扱い・閾値や既定値のずらし・文言合わせ・機能を外す)は、前の周の直った 4 件について見つからなかった(どれも構造の変更: 採番済みの要求を記録する / 空を返す分岐 / 履歴の窓 / 口座の口の追加)。

## 4. 置いた試験(`tests/bt/critic/item_0/`。壊れたまま残す。作業者が直す)

- `test_i0r1_since_future_is_silent.py`(i0-r1-08)
- `test_i0r1_state_unknown_lost_on_cancel_reject.py`(i0-r1-09)
- `test_i0r1_same_stream_cross_type_reordered.py`(i0-r1-10)
- `test_i0r1_zero_length_bar_with_range.py`(i0-r1-11)
- `test_i0r1_feed_delay_reorders_one_stream.py`(i0-r1-12)
- `test_i0r1_end_time_not_validated.py`(i0-r1-13、2 件)
- 前の批評家の試験で、この周の指摘の根拠にしたもの: `test_r5c1_outbound_channel_fifo.py`(i0-r1-05)、`test_r5c1_notice_channel_fifo.py`(i0-r1-06)、`test_r5c1_ledger_accepts_contradictions_after_unknown.py`(i0-r1-07)
