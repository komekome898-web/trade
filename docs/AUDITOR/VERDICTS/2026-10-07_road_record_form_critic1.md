# 批評家 1 回目(逐語)— 道の記録の形(委任文 DELEGATION_record_form_critic.md)

# 批評家の報告: 道の記録の形(L-766・L-767)

コード・リポジトリの文書は変えていません。commit・push・git add・worktree はしていません。封印の置き場も 2023-12-17T15:00Z より後のデータも読んでいません(試しは全部、合成の足 `random_walk`、2023-11-14 の時刻です)。試しの台本は全部 `/tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/critic/` に置きました: `probe_strategy.py`・`probe.py`・`sweep.py`・`compound.py`・`notices.py`・`sides.py`・`sides2.py`・`fifo.py`・`dcancel.py`・`derive_sides.py`。どれも `cd /home/user/trade; PYTHONPATH=src python <台本> [名前]` で回せます。

既存の試験 `PYTHONPATH=src python -m pytest tests/road -p no:cacheprovider` は全部通りました(終了コード 0)。

着手前の表(§0.1)
| やろうとすること | 委任文の原文の該当語(逐語) |
|---|---|
| 問 0〜6 に、問ごとに印と根拠(ファイル:行)を付けて答える | 「1 件ずつ、[止める] / [直す] / [聞く] / [問題なし] の印と根拠(ファイル:行)をつけて答える」 |
| 穴があれば、試しで走らせが止まるか・検査が落ちるかを確かめる | 「走らせが止まるか・検査が落ちるかを試しで確かめる」 |
| 書き換えの試しを、全部の表の全部の欄に 1 欄ずつ当てる | 「1 欄ずつ」 |
| 試しの台本を scratchpad に置く | 「試しの台本は scratchpad に置く」 |

---

## 問 0 [直す](止めるではない)

**結論【事実】:** L-766・L-767 で求められたものは、どれも列として残っています。生の約定は `fills`(t_ns・venue_t_ns・side・qty・px・ccy・fee・liquidity)、USDJPY は生の表 `fx` と、作った表 `ledger_fills.usdjpy/usdjpy_t_ns`・`trades.usdjpy/usdjpy_t_ns`、注文の `orders.usdjpy/usdjpy_t_ns` にあります。合図の発生と消失は `signals.start_t_ns/end_t_ns/end_reason`、注文の一生と量の計算の値は `orders` にあります(`src/bot/bt/road/tables.py:53-173`)。表どうしは番号でつながるので、分解して使い直せます。形として欠けたものは無いので、止めるにはしていません。

[直す] にしたのは、L-754「**そのツールが必ず使われる仕組み**」の半分が欠けているためです。
- 【事実】道の土台を継がない戦略でも走らせは止まりません。`road/` が書かれないだけです(`src/bot/bt/pipeline.py:1262` の `if any(r.road is not None …)`)。
  - 試し: `probe.py plain` → `走らせの置き場: ['data_quality.json', 'fills.json', 'metrics.json', 'orders.json', 'record.json', 'repro.json', 'trades.json']`、`road/ がある: False`。
  - 検査をこの置き場に当てれば落ちます(`置き場が読めない`)。ただし検査を押し出しの関門につなぐのは次の段です(`check.py:5`、L-755)。
- 【事実】問 1・2・5 に書くとおり、記録を偽っても検査が通る道があり、正直な記録が検査に落ちる場面もあります。

「限界・近似・前提」にあたる所(コードに語としては無いので、意味でたどりました。`grep -n "限界\|近似\|前提"` は road のコードに該当なし):
- `ledger.py:14-19, 34`: 割り切れない値は 1e-12 の位で丸めます → **調べた事実**として書かれています(Decimal 版を分数の計算と突き合わせ、2 万本で 1,925 本ずれた、と書いてある)。私は再現していません。
- `sizing.py:62-63`: 切り捨て前の量は Decimal の 28 桁 → **調べた事実**(書き出しと検査が同じ関数を使う作り)。
- `strategy.py:40-41`: 取引所の模型に GTD が無い・門の拒否は venue で届く → **調べた事実**(「2026-10-07 に試しで確かめた」)。ただし、そこから期限切れの列がどうなるかは追っていません → その部分は**作業を省いた**(問 4)。
- `check.py:40-41`: 足の遅れが 0 でないと (iv) が必ず落ちる → **調べた事実**(`test_r2_feed_latency_fails_signal_bar_check`)。
- `check.py:46`: 「知らせの遅れがある走らせでは (v) に落ちる」→ **作業を省いた**(r2 の報告でも【推定】、試験は無い)。しかも条件が誤りで、遅れ 0 でも落ちます(問 5 で試した事実)。
- `strategy.py:22-23`: 成行の量の計算の値段 = 直近の足の終値など → 記録はされますが、検査はその値段を足と突き合わせません → **作業を省いた**(問 1)。
- RECORD_FORM §1【未確認】「数年分の置き場の大きさ」→ r1・r2 では測っていません(`grep -n "大きさ\|MB" REPORT_record_form_r1.md` は該当なし) → **作業を省いた**。
- RECORD_FORM §2 の `record.json` の「族の格子の中のどの点か」→ pipeline の record.json には git_sha・diff_hash・prereg_sha256 はありますが(`pipeline.py:798-799`)、格子の点の欄は見当たりません【事実: grep で grid/family/格子 は無し】。この委任の範囲外です。
- r2 (c) USDT は道で回せない → **調べた事実**(口座の誤りの文を引いている)。r2 (d) 建玉 0 の flatten は「量が 0 で出さない」の行を残す → 仕様に無い**仮定**(報告にもそう書いてある)。

---

## 問 1 [直す]

**止まる穴【事実】**
- `ctx.place_order` を直に呼ぶ → 走らせが止まります。`probe.py direct` → `止まった: RoadStrategyError 土台を通さずに出した注文 'mine-1' の知らせが届いた…`(`strategy.py:214-216`)。
- 番号を `forced-` にする → core が止めます。`probe.py forced_id` → `OrderApiError client_order_id 'forced-1': the prefix 'forced-' is reserved…`(`core/api.py:413-416`)。この文は英語ですが core の文なので、ここでは直しを求めません(O-1 の事実としてだけ書きます)。
- `on_event` を上書きして記録を飛ばし、直に注文する → 約定があれば、書き出しの時点で止まります(走らせ全体が終わった後)。`probe.py skip_observe` → `止まった: TableError 銘柄 BTCJPY・側 optimistic: 約定 0 の注文 'mine-2' が土台の記録に無い`(`tables.py:227-228`)。

**通ってしまう穴【事実: どれも検査の失敗 0】**
1. 証拠金を道の外で変える。戦略の `__init__` で `bot.bt.road.strategy.MARGIN_JPY = 1_000_000` にします。
   - `probe.py margin_patch` → 注文 `('road-0', '1000000', '0.7', '1', '5000000.0', '0.14', '0.14')`、`検査の失敗: 0`。
   - 原因: 検査 (v) は、記録された `margin_jpy`/`use_ratio` で計算し直します(`check.py:561-564`)。L-743「**俺は20万って言ってたのに**」・L-746「**70%**」の値には縛っていません。
2. 量の計算の値段を偽る。place の前に `self._px` を半分にします。
   - `probe.py fake_px` → 注文の `size_px` は `'2500000.0'`(出所の欄は '直近の足の終値')、量 `0.056`。約定の値段は 5,000,000。`検査の失敗: 0`。
   - 原因: `size_px` を足と突き合わせる所が無いためです(`check.py` は size_px を計算の入力にしか使わない)。
3. 土台の記録を書き換える。
   - `probe.py edit_records` では、発生の時刻を 1 分前、消失の時刻を 1 分後にずらしました。さらに注文の行を `margin_jpy=100000`・`qty=0.014` に書き換えましたが、実際に送った量は 0.028 です。
   - 結果: 合図 `('s1', '1700000160000000000', '1700000460000000000')`(本当は T0+3M=…220…、T0+6M=…400…)、注文 `('road-0', '100000', '0.014', '0.014', '0.028')`、約定 `('road-0', '0.028')`、`検査の失敗: 0`。
   - 注文の量と、約定した量・約定の和は突き合わせていません。
4. 取り消しを `ctx.cancel_order` で直に出す。
   - `dcancel.py` → `('road-0', '', '1700000340000000000', 'cancel', 'CANCELED')`(取り消しを出した時刻が空なのに、取り消した時刻はある)、`検査の失敗: 0`。
   - 原因: `strategy.py:229-231` は、`cancel` を通ったかを見ていません。
5. 土台を継がない(問 0 の 1 点目)。

**直す案(推定)**
- (v) で `margin_jpy`・`use_ratio` を `sizing.MARGIN_JPY`/`USE_RATIO` と比べます。モジュールを書き換えられても効くのは、検査を別のプロセスで回すとき(CLI はそう)だけです。
- `size_px_source == 直近の足の終値` の行は、`placed_t_ns` に閉じた足の終値と比べます(足は既に検査に渡している)。指値の行は `limit_px == size_px` を見ます。
- `orders.qty` を pipeline の `orders.json` の `qty`(core が持つ `o.request.size`、`pipeline.py:1123`)と比べます。これで 3 が落ちます。
- 注文ごとに Σ`fills.qty` == `filled_qty` ≤ `qty` を見ます。
- `orders.usdjpy/usdjpy_t_ns` を、`fx` の `placed_t_ns` 以前の最後の相場と比べます。
- 取り消しの答えの前に `cancel_sent_t_ns` があるかを見ます。または土台で止めます。

**[聞く]**: 戦略の中で `self._signals` を書き換えるもの(3 の合図の時刻)には、外から照らせる記録がありません。案は、戦略の源(sha256 は `pipeline.py:533` で記録済み)を機械で走査し、土台の `self._` の名への書き込みと `bot.bt.road.*` のモジュールの値への代入を止めることです。これを足すかどうかを聞きます。

---

## 問 2 [直す]

`sweep.py JPY|USD|LIMIT` で、表ごと・欄ごとに、悲観側の最初の行を 1 欄ずつ書き換えました(時刻は +1 分なので、足はある)。

**書き換えても通った欄【事実】**
- JPY(基本の場面): `signals.kind, direction, value_json('…x' の壊れた JSON でも), end_t_ns, end_reason` / `orders.side('buyx'), order_type('marketx'), limit_px, placed_t_ns, sent_t_ns, acked_t_ns, acked_venue_t_ns, cancel_sent_t_ns, canceled_t_ns, expired_t_ns, rejected_t_ns, closed_t_ns, closed_venue_t_ns, close_kind, close_reason, state, filled_qty, size_px_source, usdjpy_t_ns, position_at_send(量の計算の行)` / `fills.venue_t_ns, fee, liquidity`
- USD では上に加えて: `fx.instrument, fx.range`(知らない組に移した行は `tables.py:271-273` で黙って捨てられる)、`fx.t_ns`・`fx.rate`(使われていない行)
- LIMIT(指値と取り消し)では上に加えて: `orders.order_id`(約定の無い注文)

**落ちた欄【事実】**
- `trades` の全欄(`hold_ns 180000000000→240000000000: 落ちる ['ii']`、`levels 2→3: 落ちる ['ii']` を含む)
- `ledger_fills` の全欄
- `fills` の t_ns・qty・px・side・ccy・signal_id・order_id・fill_id
- `orders.qty, margin_jpy, use_ratio, levels, size_px, quote_ccy, usdjpy, qty_raw, qty_source, origin, signal_id`
- `signals.start_t_ns`(+1 分は (iii) で落ちる)
- `fx.pair`
- 使われた相場の行の `fx.rate` だけを変えたとき(`compound.py` (e): `検査の失敗 4 ['ii']`)

**生の表と作った表をそろえて書き換えたとき【事実、`compound.py`】**(作った表は道の `write_tables` で作り直しました)
- (a) 決済の約定の量を 0.028→0.027 にする → `検査の失敗 0`(取引は途中のまま、閉じた取引は 0 になる)
- (c) 注文の usdjpy を 150→100 にし、量 0.023・切り捨て前の量をそろえる → `検査の失敗 0`(`fx` とつないでいない)
- (d) 使われた相場を 150→140 にし、作り直す → `検査の失敗 0`
- (b) 買いの約定の量を変える → (v) の決済の行で落ちます。
- どの場合も `repro.json` の `sha256` に road/ の指紋があり(`pipeline.py:1286-1291`)、書き換えたファイルがそこで分かりました。例: (a) `['road/fills.csv.gz', 'road/ledger_fills.csv.gz', 'road/summary.json', 'road/trades.csv.gz']`。
- 検査は repro.json を読んでいません: `grep -n "repro" src/bot/bt/road/check.py` → exit 1。

**直す案(推定)**
- 書き出した後の書き換え: 検査の最初に、road/ の指紋を `repro.json` と比べます。ただし repro.json も書き換えられるので、最後の錨は押し出しの関門(L-755 で次の段)です。
- 書き出す前の偽り: 問 1 の突き合わせが要ります。
- 値の形の確かめ: `side`/`order_type`/`state`/`close_kind` が決まった値の中にあるか、`value_json` が JSON として読めるか、時刻の順(出した ≤ 受け付けられた ≤ 閉じた)、`fx` の組が走らせの組の中にあるか、を足します。

---

## 問 3 [聞く]

**守られている所【事実】**(`probe.py doten`: 買い 0.014 → 売り 0.028 でドテン)
- JPY: `trades [('0','s1',…,'closed',…), ('1','s2',…,'open',…,'-0.014')]`、summary `closed_trades 1・open_trades 1`。ドテンの約定の `trade_id 0`・`opens_trade_id 1`。
- USD: 閉じた取引は最初の約定 0:03 以前の最後の相場 `150 / 1700000160000000000(0:02)`、ドテンで始まった取引は `151 / …280…(0:04)`。ドテンの約定の行は、閉じた側の 150 を使っています。どちらも検査の失敗 0。
- 道の表は全部 `ledger.book` から作られます。`grep -rn round_trips src/bot/bt/road/` は説明の文 2 か所(`ledger.py:37`・`tables.py:17`「使わない」)だけで、コードでは使っていません。

**聞くこと**
1. 同じ走らせの置き場に、FIFO の数え方の書き出しが並んでいます。`fifo.py` → `pipeline trades.json の悲観側の行: ['road-0>road-2#1', 'road-1>road-2#2']`、`metrics.json /data/trades/n 2`、`道の trades の悲観側: [('0', 'closed')]`。
   - `pipeline.py:113-117` によれば、ダッシュボード(`bot.monitoring.backtest_view`)はこの書き出しを映すので、オーナーが退けた数え方(L-749・L-750)の 2 回が画面に出ます。
   - 道の表には混ざっていません。ただ、既存の書き出しを変えないのは委任文の制約なので、この扱いを聞きます(道の走らせで metrics の取引の数に印を付ける・映さない・そのまま、など)。
2. 「取引開始時点」の時刻に何を使うか。帳簿は約定の `t_ns`(値段を決めた観測の時刻 = 足の始まり 0:03、`pipeline.py:880,1119`)で相場を引いています。`venue_t_ns`(0:04)で引くと、上の USD の試しでは 150 が 151 に変わります。どちらを「取引開始時点」とするかを聞きます。

---

## 問 4 [直す]

1. 【事実】3 か所の文が食い違っています。
   - コード: `refused_by_account` も拒否に入れる(`strategy.py:90`「`VENUE_REJECT_PREFIXES = ("rejected_by_venue", "refused_by_account")`」、`strategy.py:233-236`)。
   - SCHEMA の説明: 期限切れ = 「answers = venue … で理由が rejected_by_venue で始まらないもの」(`tables.py:80-83`)。これだと `refused_by_account` は期限切れになります。
   - r2 の報告: 「(`refused_by_account: …`、`answers=venue`)は、答えの決まりどおり期限切れの列に入ります」。
   - 置き場に書かれて人が読むのは SCHEMA.json なので、SCHEMA の説明を直す必要があります。
2. 【事実】取引所の模型には期限つきの注文がありません(`strategy.py:40`)。そのため `expired_t_ns` に入るのは、期限切れでない「取引所が自分で閉じたもの」です。
   - `notices.py` → `venue + market_remainder: {'expired_t_ns': …}`、`venue + reduce_only: {'expired_t_ns': …}`、`venue + oco: {'expired_t_ns': …}`。
   - core は on_market_event で出たものを全部 `answers="venue"` にします(`core/engine.py:1381-1386`)。門が成行を放すのもそこです(`pipeline.py:878-881`)。
   - 道の走らせ(1 分足・tier 2)で market_remainder を実際に起こすことはできませんでした(`probe.py big`: 140 BTC でも 1 回で全部約定)。走らせで起こるかは【未確認】です。
3. 【事実】時刻の列に入らない知らせがあります。
   - 取り消しの拒否(`OrderRejectEvent(request_kind="cancel")`)と `OrderStateUnknownEvent` は、どの時刻の列にも残りません(`notices.py` → `Reject(request_kind=cancel): {}`・`StateUnknown(new): {}`。表示された state は試しの偽の文脈の値なので無視してください)。
   - `strategy.py:238` は `request_kind == "new"` だけを扱い、StateUnknown は扱っていません。
4. 【事実】`answers=new` で理由が `post_only_would_take` などのもの(中身は拒否)は、どの列にも入らず、生の列にだけ残ります(`notices.py` → `{'closed_t_ns':…, 'close_kind': 'new', 'close_reason': 'post_only_would_take'}`)。2 周目の答え (b) のとおりですが、これでよいかを [聞く]。
5. 【事実】門が預かる成行の「受け付けられた時刻」は、門がその場で返す受け付けです(`pipeline.py:912`「acknowledged now, priced later」)。取引所の受け付けではないので、SCHEMA の説明に書く必要があります。
6. 直に出した取り消しは `cancel_sent_t_ns` が空になります(問 1 の 4)。

---

## 問 5 [直す]

【事実】仕様と検査の定義が違います。
- 仕様: 委任文 2 周目 (d) は、量 = 「**送る時点の建玉の絶対値(土台が約定の知らせから持つ建玉)**」と書いています。土台はそのとおりに作られています(`strategy.py:372-374`)。
- 検査: `check.py:44-45, 510-528` は「注文を受けた時刻以前の約定(この注文より前の注文の約定)」、つまり約定の `t_ns ≤ placed_t_ns` で建玉を作ります。

【事実】このため、知らせの遅れが 0 でも、正直な記録が落ちます。試し `probe.py quick_flatten` では、0:03 に買いを 2 つ出し、次の足 0:04 で flatten しました。
- 遅れ 0 の結果:
  - 注文 `('road-2', '', '0.0', '建玉', '0', '1700000280000000000', '量が 0 で出さない')`
  - 約定 `('road-0', '1700000220000000000', '0.014'), ('road-1', …, '0.014')`
  - `trades [('0', 'open', '0.028')]`
  - `検査の失敗: 8`(側ごとに 4 つ。例: 「注文の量 '0.0' が、送る時刻以前の約定までの建玉 0.028 の絶対値 '0.028' と違う」)
- 遅れ 90 秒でも同じでした。
- 起きていること: 約定の `t_ns` は足の始まり 0:03 です(`pipeline.py:880,1119`)が、取引所での時刻 `venue_t_ns` は 0:04 で、約定の知らせは 0:04 の足の後に届きます。土台は 0:04 の時点で建玉 0 と見ていて、建玉は開いたまま残ります。
- `check.py:46` の「知らせの遅れがある走らせでは」という条件は誤りです。

**直す案(推定)**: 土台は約定の知らせをすべて見ています(`strategy.py:224-228`)。知らせが届いた時刻(と届いた順)を `fills` か土台の記録に残し、(v) は「flatten の行より前に届いた知らせの約定」で建玉を作り直します。

**[聞く]**: 注文がまだ途中(出していて、閉じていない)のときに flatten が来たら、止めるか・印を付けるか。今は「量が 0 で出さない」の行だけが残り、戦略には閉じたように見えます。

**誤って通る場面**: 見つけていません。理由は推定です。知らせが届く時刻は、約定の t_ns 以上です。また、土台が数える約定は、検査が数える約定の部分集合です(口座の強制の注文の行は知らせが届いた時点で作られる、`strategy.py:215-218`)。このため、両者が一致したときは正しい建玉になる、と考えます。試しでは確かめていません。

---

## 問 6 [問題なし]

- 【事実】戦略は銘柄 × 側 × 実行ごとに作り直されます(`pipeline.py:535` の説明「built fresh for one instrument, one side and one execution」。`_run_instrument(…, side)` の中の `pipeline.py:1085`)。
- 【事実】表と検査は全部、(銘柄, 側) で分けています(`tables.py:212-218, 272-273`、`check.py:411, 435, 455, 517-527`)。
- 【事実】側ごとに違う約定を `derive` に渡すと、側ごとに分かれて手計算と合いました。`derive_sides.py` → `[('optimistic', '1400'), ('pessimistic', '1120')]`(手計算: (5,100,000−5,000,000)×0.014 = 1,400、(5,090,000−5,010,000)×0.014 = 1,120)。
- 【事実】走らせで両側の値段を違えることはできませんでした(`sides2.py`: 広がり 2000・tier 2 でも両側同じ値段)。そのため、走らせを通した側の分かれは「違う値で」は試せていません。
- 小さな点: `RANGES` は pipeline の `SIDES` の手写しです(`tables.py:40`、`pipeline.py:168`。今は同じ値)。fx の行が知らない組に移されると黙って捨てられる件は、問 2 に書きました。

---

## リードの応答(1 件ずつ)

- **問 0 [直す]**: 直す。仕組みの半分(検査を押し出しの関門につなぐ)は L-755 の次の段で行う。道の土台を継がない戦略で pipeline が止まらないのは、pipeline が道以外の走らせにも使われるため変えない。道の置き場であることは検査が要求する(road/ が無ければ失敗)。置き場の大きさはマチルダのパイロットで測る。record.json の族の格子の点は契約(M3)の段で入れる。
- **問 1 [直す]**: 直す(3 周目)。(1) 検査は証拠金 200,000 円・比率 0.70 を検査の側の定数で縛る(L-743・L-746)。(2) 量の計算の値段: 「直近の足の終値」の行は、出した時刻以前に閉じた最後の足の終値と、指値の行は指値の値段と突き合わせる。(3) `orders.qty` を pipeline の `orders.json` の量と、注文ごとの約定の和を `filled_qty` と突き合わせ、和 ≤ 量を見る。(4) 注文の USDJPY を `fx` の出した時刻以前の最後の相場と突き合わせる。(5) 土台を通さない取り消しは走らせを止める。[聞く](戦略の源の走査): 足さない。Python の中で戦略が土台の内部を書き換えるのを機械で塞ぎ切る手は無い。外から照らせる記録(pipeline の約定・注文、足、fx)との突き合わせを (1)〜(5) で増やし、残る穴(合図の時刻の書き換え)は限界として SCHEMA の説明と報告に書く。
- **問 2 [直す]**: 直す(3 周目)。値の形(売買・種類・状態・閉じ方が決まった値か、`value_json` が読めるか)、時刻の順(出した ≤ 受け付けられた ≤ 閉じた、発生 ≤ 消失)、`fx` の組が走らせの組の中にあるか(黙って捨てずに失敗)、road/ の指紋を `repro.json` と比べる、を検査に足す。書き出す前の偽りは問 1 の突き合わせで塞ぐ。
- **問 3 [聞く]**: (1) pipeline の FIFO の書き出しは、既存の書き出しを変えない制約のまま残す。道の走らせの読み口は road/ の表だけとし、SCHEMA.json に「pipeline の trades.json・metrics の取引の数は FIFO の数え方で、道の数え方ではない」と書く。ダッシュボードの扱いはオーナーに事実として伝える。(2) 取引開始時点の時刻 = 約定の `t_ns`(その約定の値段が付いた時刻。1 分足の成行は次の足の始まり = その足の始値の時刻、`pipeline.py` 877〜881 行)。`venue_t_ns` はその足が閉じて知らせが届いた時刻で、値段の時刻ではない。このまま。
- **問 4 [直す]**: 直す(3 周目)。(1) SCHEMA の説明をコードに合わせる。(2) 取引所の模型に期限つきの注文が無いので、`expired_t_ns` の説明を「取引所が自分で閉じた時刻(期限切れ・成行の残り・reduce_only など。理由は close_reason)」とする。(3) 取り消しの拒否と状態不明を、時刻の列(`cancel_rejected_t_ns`・`state_unknown_t_ns`)に残す。(4) `answers=new` で中身が拒否のもの(post_only_would_take など)は拒否の列に入れる。(5) 門の受け付けは取引所の受け付けではないことを SCHEMA の説明に書く。(6) 問 1 (5)。
- **問 5 [直す]**: 直す(3 周目)。正直な記録が落ちるのは土台の欠陥(建てた注文の約定の知らせが届く前の flatten が 0 になり、建玉が残る)。flatten は「決済の意図」とし、出ている注文を取り消し、知っている建玉を決済し、その後に届いた約定の知らせのぶんも建玉が 0 で注文が残らなくなるまで決済を出し続ける。約定ごとに知らせが土台に届いた時刻を記録し、検査 (v) は「決済の注文を出した時刻より前に知らせが届いた約定」で建玉を作り直す。[聞く](途中の注文があるときの flatten): 上のとおり止めずに取り消してから決済する。
- **問 6 [問題なし]**: そのまま。
