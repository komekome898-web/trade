# 委任先の報告(逐語、1 周目)— DELEGATION_record_form.md

## 報告(委任文 DELEGATION_record_form.md)

コミット・押し出し・`git add` はしていません。core(`src/bot/bt/core/`)・口座・フック・settings.json・githooks・`bot.bt.fill.venue` も変えていません。

**結論【事実】:** 受け入れの場面 1〜6 は試験としてすべて通りました。`tests/road tests/bt` も最終のコードで全部通りました。止めて問いにしたことが 7 件あり、下の「止めて問いにしたこと」に書きました。うち 3 件((a) 合図の番号を extra に入れない、(c) USDT、(d) 全部売り)は仕様どおりにできなかった点です。

### 1. 着手前の表

右が「(該当語なし)」の行は私が決めたことです(仮定)。オーナーの語がある作業を止めないものなので、L-488 4(b) に従って作業を続け、問いとして返します。

| やろうとすること | オーナーの原文の該当語(逐語) |
|---|---|
| 帳簿の約定ごとの行と取引ごとの行に、使った USDJPY の値と相場の時刻を足す | L-766「ドル円変換に使ったusd/jpyの値」/ L-763・L-764(取引開始時点での最新の値) |
| 合図の発生・消失を、土台が `ctx.now_ns` で時刻を押して記録する。消失 = 条件が成り立たなくなった時刻 | L-766「シグナルの発生・消失の時間」/ L-767「c １つ目」 |
| 戦略は量を渡さず、土台が `size_per_level` で量を決め、計算に使った値を注文の表に残す。量が 0 の段も 1 行残す | L-767「b残す」/ L-745「20万×○%÷段数÷その時の価格=1段の単位やろ」/ L-746「70% 段数は戦略毎に変える(基本は1で計算) 0.001以下は切り捨て」 |
| 注文の表(出した・受け付けられた・取り消した・期限が切れた時刻、最後の状態、約定した量)を残す | L-767「a 残す」 |
| 7 つの表と SCHEMA.json を gzip した CSV / JSON で書き出す | L-766「再利用、分解が可能な形」「生の約定履歴(時間、価格、数量…など)」 |
| 書き出しを道の走らせが行い、検査で欠け・ずれを止める | L-754「この計算が確実にできるツールを作ることと、そのツールが必ず使われる仕組み」 |
| 合図の番号を `OrderRequest.extra` に入れない(土台の記録だけでつなぐ) | **(該当語なし)** → 問い (a) |
| 期限が切れた時刻 = `OrderCanceledEvent` で `answers == "venue"` | **(該当語なし)** → 問い (b) |
| 合図の時刻の足の検査 = 分の区切り + その時刻に閉じた 1 分足がある | **(該当語なし)** → 問い (e) |
| 試験の「全部売り」を `place(sell, market, None, 段数 1, …)` で行う | **(該当語なし)** → 問い (d) |

### 2. 作ったファイル・変えたファイル

新しく作ったもの:
- `/home/user/trade/src/bot/bt/road/strategy.py`
  - 道の戦略の土台 `RoadStrategy` です。合図は `signal_start` / `signal_end`、注文は `place` / `cancel`。
  - 注文の一生は、届いた知らせから記録します。
  - 記録は `road_record()` で取り出します。
- `/home/user/trade/src/bot/bt/road/tables.py`
  - `SCHEMA`(7 つの表の列・単位・生か作ったものか)、生の表の作成、`derive`(生の表から帳簿のツールで `ledger_fills` / `trades` / `summary` を作る関数)、書き出しと読み込み。
  - 書き出しも検査も同じ `derive` を使います。
- `/home/user/trade/tests/road/road_scene_strategy.py`: 試験用の戦略。試験の中で `bot.strategy.road_scene_test` の名で読み込みます。
- `/home/user/trade/tests/road/test_road_record.py`: 受け入れの場面 1〜5 の試験。

変えたもの:
- `/home/user/trade/src/bot/bt/road/ledger.py`
  - 約定の行に `pnl_quote`・`usdjpy`・`usdjpy_t_ns` を足しました。取引の行には `usdjpy`・`usdjpy_t_ns` を足しました。
  - 円建ては値 "1"・時刻は空(None)です。
  - `TRADE_KEYS`・`SUMMARY_KEYS` とまとめの形は変えていません。
- `/home/user/trade/src/bot/bt/road/sizing.py`: 切り捨て前の量も返す `size_detail` を足しました。`size_per_level` の答えは同じです。
- `/home/user/trade/src/bot/bt/road/check.py`: 表の形の置き場に (i)〜(v) を当てる `check_tables` を足しました。従来の置き場は (a)(b) のままです。
- `/home/user/trade/src/bot/bt/road/__init__.py`
- `/home/user/trade/src/bot/bt/pipeline.py`(道の書き出しを呼ぶ口だけ)
  - `InstrumentResult.road`(既定 None)を足しました。
  - `execute_once` の最後で `<out_dir>/road/` に書きます。
  - `_digests` は 1 段下のディレクトリも数えます。読む口の一覧(`exports`)はディレクトリを飛ばします。
  - docstring に 1 文足しました。record.json・metrics などの既存の書き出しは変えていません。
- `/home/user/trade/scripts/road/check_outputs.py`: 説明と使い方の文だけ。

`docs/AUDITOR/TRACE/2026-10-07_220780c0.json` が変更ありと出ますが、私の変更ではありません。開始時は未追跡で、別のものが書いています。

### 3. 受け入れの場面の試験の結果【事実】

コマンド: `PYTHONPATH=src python -m pytest tests/road/test_road_record.py -p no:cacheprovider -vv`

試験と場面の対応:
- 場面 1:
  - `test_scene1_seven_tables_schema_and_check_pass`: 7 つの表と SCHEMA がそろい、2 回の実行が同じバイトで、検査と CLI が通る。
  - `test_scene1_signal_order_fill_trade_is_one_chain`: 合図 s1 → 注文 road-0/1/2 → 約定 0/1/2 → 取引 0 が 1 本につながる。
    - 合図 s1 は 0:03 に発生、0:06 に消失。取引 0 の合図は s1。
    - 段 2、最大の建玉 0.028、保有 3 分、損益 "0"。
  - `test_scene1_order_lifecycle_times`
  - `test_scene1_limit_order_canceled_times`
  - `test_scene1_random_walk_store_passes_check`
- 場面 2:
  - `test_scene2_size_values_are_all_recorded`: 0.014。計算の値は margin_jpy 200000、use_ratio 0.7、levels 2、size_px 5000000.0、qty_raw 0.014。
  - `test_scene2_zero_size_is_not_sent_and_leaves_one_row`: 段数 100 で qty_raw 0.00028 → qty 0.0、状態「量が 0 で出さない」、出した時刻は空、約定は無し。
- 場面 3:
  - `test_scene3_bad_signal_use_stops_the_run`: 発生していない番号の消失、発生していない合図の番号の注文、二度の発生のどれも `RoadStrategyError` で止まる。
  - `test_scene3_signal_alive_at_data_end`: 消えなかった合図は消失の時刻が空、理由が「データの終わり」。
- 場面 4:
  - `test_scene4_tampered_store_fails_in_japanese`: 書き換え 6 通りがどれも失敗し、CLI が日本語の行を出す。
  - `test_scene4_signal_shifted_later_also_breaks_the_order_link`
- 場面 5:
  - `test_scene5_usd_rate_and_quote_time_on_ledger_rows`
    - 注文の量は 0.015 / 0.015 / 0.03。
    - 帳簿の約定と取引の行の usdjpy は "150"、相場の時刻は 0:02。取引の開始以前の最後の相場と一致する。
    - 0:06 の決済も 151 でなく 150 で円にしている。
  - `test_scene5_ledger_rows_carry_rate_and_time_doten`: ドテンの約定の行は閉じた側の 150、新しい取引は 151。円建ては "1" と None。
- 場面 6: 既存の `tests/road/` は変えずに全部通りました(下の 4.)。

20 の試験は全部 PASSED でした。

場面 4 の CLI の出力(`... -k test_scene4_tampered_store_fails_in_japanese -s`、パスは省略):
```
検査 失敗: …/store(失敗した行 1)
  (ii) 行 ledger_fills の 3 行目(銘柄 BTCJPY・側 pessimistic・約定 0): avg_px_after の書かれた値 '5000001' と生の表から作り直した値 '5000000' が違う
検査 失敗: …(失敗した行 1)
  (v) 行 orders の 3 行目(銘柄 BTCJPY・側 pessimistic・注文 road-0): 注文の量 '0.015' が、記録した量の計算の値から計算し直した量 '0.014' と違う
検査 失敗: …(失敗した行 3)
  (iii) 行 orders の 3 行目(…注文 road-0): 注文を受けた時刻 1700000220000000000 が合図 s1 の発生の時刻 1700000240000000000 より前
  (iii) 行 orders の 4 行目(…注文 road-1): 注文を受けた時刻 1700000220000000000 が合図 s1 の発生の時刻 1700000240000000000 より前
  (iv) 行 signals の 1 行目(…合図 s1): 発生の時刻 1700000240000000000 が分の区切りから 20000000000 ns ずれている
検査 失敗: …(失敗した行 1)
  (iv) 行 signals の 1 行目(…合図 s1): 発生の時刻 1700000200000000000 が分の区切りから 40000000000 ns ずれている
検査 失敗: …(失敗した行 3)
  (ii) 行 trades の 1 行目(…取引 0): signal_id の書かれた値 's1' と生の表から作り直した値 'zz' が違う
  (iii) 行 fills の 3 行目(…約定 0): 約定の合図の番号 'zz' が注文の合図の番号 's1' と違う
  (iii) 行 fills の 3 行目(…約定 0): 約定の合図の番号 'zz' の合図が signals に無い
検査 失敗: …(失敗した行 1)
  (i) 行 fx: 表 fx の列が SCHEMA と違う: 欠けた列 ['source']
```
合図の発生の時刻は、20 秒後ろにずらしても 20 秒前にずらしても失敗します。

### 4. `tests/road tests/bt` の結果【事実】

コア 4 つで xdist が無く、全体を 1 本で流すと遅いため、委任文のコマンドをディレクトリで 4 つに分けて並べて流しました。範囲は同じです。最後の 2 つの編集(docstring だけ)の後にも 4 つとも流し直しました。CLAUDE.md §3「件数は書かない」に従い、件数は省き、終了コードだけを出します。
- `PYTHONPATH=src python -m pytest tests/road tests/bt/item_4 tests/bt/item_3 -p no:cacheprovider` → EXIT 0
- `PYTHONPATH=src python -m pytest tests/bt/critic -p no:cacheprovider` → EXIT 0
- `PYTHONPATH=src python -m pytest tests/bt/item_0 -p no:cacheprovider` → EXIT 0(numpy の RuntimeWarning 3 件のみ)
- `PYTHONPATH=src python -m pytest tests/bt/battery tests/bt/item_1 tests/bt/item_2 -p no:cacheprovider` → EXIT 0

どれも失敗は 0 です。

モデル名の検索: `grep -rniE 'claude|opus|sonnet|haiku|anthropic|gpt' src/bot/bt/road tests/road scripts/road src/bot/bt/pipeline.py --include=*.py` → 該当なし(grep exit 1)。

### 5. core を変えずに注文の一生の時刻をどう取ったか【事実】

- 注文の知らせは、他の出来事と同じく戦略の `on_event` に届きます(`src/bot/bt/core/engine.py` 1128 行 `self._strategy.on_event(delivered, ctx)`)。土台の `on_event` → `_observe` が先に記録し、その後に継ぐ側の `step` を呼びます。
- 知らせの時刻(engine.py 1375〜1394 行の `_handle_reports`):
  - `received_time_ns` = 戦略に届いた時刻。これは届いたときの `ctx.now_ns` と同じです。
  - `exchange_time_ns` = 取引所での時刻。
  - 取り消しの `answers` は 1382 / 1384 / 1386 行で決まります。
- 出来事の型(`src/bot/bt/core/events.py`): `OrderAckEvent` 342 行、`OrderRejectEvent` 353 行、`OrderFillEvent` 366 行、`OrderCanceledEvent` 385 行、`OrderStateUnknownEvent` 401 行、`CANCELED_ANSWERS` 104 行。
- 各時刻と値の取り方:
  - 出した時刻: `ctx.place_order` を呼んだ時刻(`ctx.now_ns`)。
  - 受け付けられた時刻: `OrderAckEvent` が届いた時刻。
  - 取り消した時刻: `answers == "cancel"` の `OrderCanceledEvent` が届いた時刻。
  - 期限が切れた時刻: `answers == "venue"` の `OrderCanceledEvent` が届いた時刻。
  - 閉じた時刻・閉じ方・理由: 生の列 `closed_t_ns` / `closed_venue_t_ns` / `close_kind` / `close_reason` に残します。
  - 最後の状態: 知らせのたびに `ctx.order(番号)`(`src/bot/bt/core/api.py` 882 行)の状態を読みます。
  - 約定した量: `OrderFillEvent` の量の和。
- `ctx.now_ns` はメソッドでなく property です(api.py 710 行)。委任文の `ctx.now_ns()` は `ctx.now_ns` として実装しました。

### 6. 止めて問いにしたこと

- (a) 合図の番号を `OrderRequest.extra` に入れると、注文が全部取引所に拒まれます【事実】。
  - 試しの出力: `close_reason = rejected_by_venue: unknown_extra:['road_signal']`。取引所の模型(`src/bot/bt/fill/venue.py` 414〜417 行)は知らない extra の鍵を拒み、その試験(`tests/bt/item_2/test_i2_venue_edges.py` 100 行)もあります。
  - 今は extra に入れず、つなぎを土台の記録(注文の表の `signal_id`)だけで持たせています。
  - 案は 3 つ: ① 取引所の模型が道の印の鍵を通す ② 門(pipeline)が取引所に渡す前に外す ③ 今のまま記録だけ。
  - ③ で失うのは、約定の合図の番号と注文の合図の番号の突き合わせの出所が 1 つになる点だけです。
- (b) 期限が切れた時刻の取り方【事実+仮定】。
  - 取引所の模型には期限つきの注文がありません(`TIME_IN_FORCE = ("GTC","IOC","FOK")`)。
  - core の定義で期限切れにあたる `answers == "venue"` を使いましたが、門が預かった成行を取引所が拒んだ場合も `answers=venue`(理由 "rejected_by_venue: …")で届くことを試しで確かめました。
  - 生の列 `close_kind` / `close_reason` を残してあるので、どれを期限切れと呼ぶかは後から決め直せます。
  - `answers == "new"`(IOC・成行の残りなど)は、取り消し・期限切れのどちらの列にも入れていません。
- (c) USDT は道の走らせで回せません【事実】。口座が `currency must be a 3-letter code, got 'USDT'` で止めます(試験で確かめました)。帳簿のツールの USDT は既存の場面 6 で見ています。
- (d) 土台に「量 = 建玉」で決済する操作がありません。試験の全部売りがちょうど 0 になるのは、値段が動かない足の上だからです【事実】。決済の口を土台に足すかを問います。
- (e) 合図の時刻の足の検査(分の区切り + その時刻に閉じた 1 分足)は、足で動く戦略で足の遅れ(feed)が 0 の走らせを前提にしています。足の遅れが 0 でない走らせは (iv) で落ちます【推定】。
- (f) 合図・注文・約定のどれも無い (銘柄, 側) は、`summary` に行が出ません【事実】。
- (g) 口座の強制の注文(`forced-`)は出所「口座の強制」の行として残しますが、試験はしていません(試験は清算なし)。
