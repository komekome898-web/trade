# 項目 2 の場面集 — 定義(執行の模型: 注文・約定・遅延・費用・口座)

**この文書は `gen_definitions.py` が `i2_scenes.py` から作る。手で直さない**(末尾の「提出前の吟味」の節だけは場面係の文で、生成器はそのまま残す)。
期待の値は全部、場面ごとの正解の関数(エンジンを見ない閉じた式)が場面の入力から計算したもので、手で打った数は無い。
固定した要件: `docs/DISCUSSIONS/2026-09-23_backtest_env/item_2/REQUIREMENTS.md` の観点 C2-1〜C2-12。

## 0. 読み方

- **値の場面** = その値が正しいか(合成の入力と、閉じた式で出した正解)。**能力の場面** = X ができるかを、X を使ったときに出るはずの観測できる結果(正解)で見る。どちらも、対象を実際に呼んだ結果を正解と突き合わせる(場面集の規則 1)。「持っている」という申告は数えない。
- **対になった場面**(「変形」の欄がある場面): 対照の入力で正解と一致し、**かつ**変形の入力を断ったときだけ「正解と一致」。変形で単一の結果を返したら「不一致」。対照が正解と合わなければ、その不一致をそのまま記録する。
- **正しさ**の分類(良い順。場面集の規則 5): 正解と一致 > 対応なし(対象が明示的に拒否した・例外を出した)> 不一致(黙って違う値を返した)> 結果なし(その場面を対象に渡せなかった。何を試したかを注記に書く)。
- **再現**: 同じ場面を別々の process で 2 回走らせ、正しさの分類と観測(出力の全体の正規化した JSON の sha256)が同じなら「2 回の実行で同じ」。
- 時刻は UTC の int64 ナノ秒。T0 = 2026-01-05 00:00:00 UTC。「T0+5ms」は T0 から 5 ミリ秒後。JST は UTC+9。

## 1. 入力の形(全場面で同じ)

| 鍵 | 意味 |
|---|---|
| product | 商品: symbol・venue・tick(呼値)・min_qty(最小数量)・qty_step・quote_ccy(値の通貨)・margin(証拠金取引か) |
| rules | 取引所の規則の宣言(例: off_tick = reject / round_passive、post_only = reject_if_crossing、market_remainder = cancel、self_trade = cancel_taker、sessions_jst、price_limit、closed_utc_ns、outside_session = queue_to_next_open、amend_qty_down = keep_priority、mark = last_trade、market_ref = last_trade) |
| market | 市場の事象の列(時刻順。同じ時刻は列の順): book(板の写真: bids・asks = [値, 量] の良い順。当方の注文は含まない外部の板)/ trade(約定: px・qty・aggressor)/ bar(足: t = 足の終わり、span_ns、o・h・l・c・v)/ funding(資金調達: rate・mark)/ rollover(FX の日替わり)/ corporate(分割・併合: ratio)/ fx_rate(為替)/ l3_add・l3_cancel(注文ごとの板の出入り) |
| actions | 戦略の行為の列(時刻 = 戦略が出した時刻): place(ref・side・type = market / limit / stop・qty・px・stop_px・tif = GTC / IOC / FOK・post_only・reduce_only・oco = 相手の ref)/ cancel(ref)/ amend(ref・px・qty)/ kill(Kill Switch) |
| fill_model | 約定の模型の宣言: tier(道具台帳 §2.1 の段 0〜6)・cancel_stance(先行注文の取り消しの扱い)・impact(市場影響の関数)・range(楽観側 optimistic と悲観側 pessimistic の 2 つの模型)。null = 場面が模型を問わない(どの段でも正解が同じになるように作ってある) |
| latency | 遅延の宣言: feed(配信)・order(発注)・cancel(取消)・notice(受付・拒否の知らせ)の 4 つを別々に。kind = constant(ns)/ empirical(samples_ns と seed) |
| costs | 費用の宣言: maker_rate・taker_rate(負 = 払い戻し)・spread・funding・swap・fee_table と、出所の欄 source。**費用を測らない場面も 0 と出所を明示する**(既定値を持たない、の場面と矛盾しないため) |
| account | 口座: currency・cash・leverage・maint_ratio・liquidation_price・source |
| inject | 異常系の注入: kind = reject / timeout / unknown と ref |
| checkpoints | 途中の時点の名前 → 時刻(累計の約定量を見る) |
| end_t | 場面の終わりの時刻 |

**市場の事象の整合(全場面に同じ規則)**: 約定が、表示中の最良の気配より悪い値で出るとき(売りの約定が最良の買いより下、買いの約定が最良の売りより上)は、同じ時刻の約定の直前に、その値より良い側の値位を除いた板の写真を置く(`i2_scenes.consistent`)。板を実際に照合する対象でも、約定の列だけを見る対象でも、同じ市場として読めるようにするため。気配の内側の値の約定(例: 外部の買い 9999 / 売り 10001 のときの 10000)は、外部の板に表示されない量の約定か、当方の注文(外部の板には含めない)に当たった約定として読む(例: c2-5 の段の場面の 9994 は、当方の 9995 の買いを跨いで出た約定)。

## 2. 期待の鍵(観測から同じ手順で導く。どの対象も同じコードで読む)

| 鍵 | 意味 |
|---|---|
| status.<ref> | 注文の終わりの状態(filled / open / canceled / rejected / state_unknown) |
| filled.<ref> | 約定量の合計 |
| avg_px.<ref> | 約定量で重みを付けた平均の約定値 |
| first_fill_t.<ref> | 最初の約定の取引所の時刻 |
| cum.<ref>@<点> | その時点までの累計の約定量 |
| fee.<ref> | 約定ごとの手数料の合計(払い。払い戻しは負) |
| lat_in.<ref> | 最初の約定の時刻 − 出した時刻 |
| sent.<ref> | 取引所に届いた発注の回数 |
| notice.<ref>.<種類> | 戦略がその知らせを見た時刻(ack / reject / fill / cancel、terminal = reject と cancel の早い方) |
| seen.<印> | 印の付いた市場の事象を戦略が見た時刻 |
| account.<欄> | 場面の終わりの口座の値(position・realized・unrealized・avg_px・exposure_ns・liquidated_t・realized_jpy) |
| costs.<欄> | 場面の間に払った資金調達・スワップ(受け取りは負) |
| range.<側>.<鍵> | 楽観側・悲観側それぞれの同じ鍵 |

値の比べ方: 文字列と整数は完全一致、小数は絶対・相対とも 1e-9 以内。`ge v` は v 以上、`in [..]` はどれかと一致。

## 3. 対象の走らせ方

`python3 tests/bt/battery/item_2/run_battery.py --target <対象> --out <出力.tsv>`。全場面を、場面ごとに対象の interpreter の別の process で 2 回走らせ、2 回の一致を再現の欄に書く。対象の一覧は `--list-targets`。
新実装の adapter(`adapters/new_impl.py`)は口だけを決めてある(本体は資料係が毎周、新実装の公開の口だけを呼んで書く): `TARGET.run(場面の入力) -> 観測`。エンジンが全体を断ったら `Refused`、注文 1 つを断ったらその注文を rejected と記録して続ける、場面を渡す公開の口が無ければ `NotExpressible(試したこと)`。正解の関数・期待の値・場面の id を読まない。

## 4. 場面(観点ごと)

### C2-1 発注の型(場面 8: 値 8・能力 0)

要件の語 → 場面: 成行 → c2-1-market / 指値 → c2-1-limit / post-only → c2-1-postonly / IOC → c2-1-ioc / FOK → c2-1-fok / 逆指値 → c2-1-stop / reduce-only → c2-1-reduceonly / OCO → c2-1-oco

#### c2-1-market(値の場面)— 成行の買いは、出した時の売りの気配で埋まる

- **何を測るか**: 成行(market)の受付と約定の状態遷移と約定値
- **入力(言葉で)**: 出した時刻の板(外部の気配)の売り側を良い方から数量まで辿った加重平均値。1 は最良の 5 以下なので最良の売り値そのもの。
- **期待(正解の関数が入力から計算した値)**: `status.o1` = "filled" / `filled.o1` = 1.0 / `avg_px.o1` = 10001.0
- **入力(全文)**: `{"product":{"symbol":"FX_BTC_JPY","venue":"bitflyer_cfd","tick":1.0,"min_qty":0.01,"qty_step":1e-08,"quote_ccy":"JPY","margin":true},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade"},"market":[{"t":1767571200000000000,"type":"book","bids":[[9999,5],[9998,5]],"asks":[[10001,5],[10002,5]]},{"t":1767571200000000000,"type":"trade","px":10000.0,"qty":0.1,"aggressor":"buy"},{"t":1767571200002000000,"type":"trade","px":10001.0,"qty":1.0,"aggressor":"buy"}],"actions":[{"t":1767571200001000000,"op":"place","ref":"o1","side":"buy","type":"market","qty":1.0,"px":null,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null}],"fill_model":null,"latency":null,"costs":{"maker_rate":0.0,"taker_rate":0.0,"source":"場面の定義(費用を測らない場面なので 0 と明示する)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{},"end_t":1767571260000000000}`

#### c2-1-limit(値の場面)— 指値の買いは、約定の値が指値に届くまで埋まらず、埋まるときは指値で埋まる

- **何を測るか**: 指値(limit)の待機と約定の状態遷移。約定値は指値。値が届く前に埋まらない
- **入力(言葉で)**: 指値 9990 の買い。出した後の約定の列で値が 9990 以下になる最初の時刻より前には埋まらない(first_fill_t ≥ その時刻)。埋まる値は指値そのもの。指値の値位には外部の待ちが無い(板の買いは 9999・9998 だけ)ので、どの約定の模型でも全量が埋まる。
- **期待(正解の関数が入力から計算した値)**: `status.o1` = "filled" / `filled.o1` = 1.0 / `avg_px.o1` = 9990.0 / `first_fill_t.o1` = ge 1767571200020000000
- **入力(全文)**: `{"product":{"symbol":"FX_BTC_JPY","venue":"bitflyer_cfd","tick":1.0,"min_qty":0.01,"qty_step":1e-08,"quote_ccy":"JPY","margin":true},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade"},"market":[{"t":1767571200000000000,"type":"book","bids":[[9999,5],[9998,5]],"asks":[[10001,5],[10002,5]]},{"t":1767571200000000000,"type":"trade","px":10000.0,"qty":0.1,"aggressor":"buy"},{"t":1767571200010000000,"type":"book","bids":[],"asks":[[10001,5],[10002,5]]},{"t":1767571200010000000,"type":"trade","px":9995.0,"qty":2.0,"aggressor":"sell"},{"t":1767571200020000000,"type":"trade","px":9990.0,"qty":10.0,"aggressor":"sell"},{"t":1767571200030000000,"type":"trade","px":9985.0,"qty":5.0,"aggressor":"sell"}],"actions":[{"t":1767571200001000000,"op":"place","ref":"o1","side":"buy","type":"limit","qty":1.0,"px":9990.0,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null}],"fill_model":null,"latency":null,"costs":{"maker_rate":0.0,"taker_rate":0.0,"source":"場面の定義(費用を測らない場面なので 0 と明示する)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{},"end_t":1767571260000000000}`

#### c2-1-postonly(値の場面)— post-only は、出した時に反対側の気配に届く値なら拒否され、届かない値なら待つ

- **何を測るか**: post-only の拒否と待機(規則 post_only = reject_if_crossing)
- **入力(言葉で)**: o1 = 10001 の post-only 買い。出した時の最良の売りが 10001 なので取る側になる → 約定 0 で終わる(拒否か、着いた時点の取消)。o2 = 9990 の post-only 買い(対照)。最良の売り未満で、以後の約定は 9990 以下に来ない → 待ったまま(open)、約定 0。
- **期待(正解の関数が入力から計算した値)**: `status.o1` = in ["rejected", "canceled"] / `filled.o1` = 0.0 / `status.o2` = "open" / `filled.o2` = 0.0
- **入力(全文)**: `{"product":{"symbol":"FX_BTC_JPY","venue":"bitflyer_cfd","tick":1.0,"min_qty":0.01,"qty_step":1e-08,"quote_ccy":"JPY","margin":true},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade"},"market":[{"t":1767571200000000000,"type":"book","bids":[[9999,5],[9998,5]],"asks":[[10001,5],[10002,5]]},{"t":1767571200000000000,"type":"trade","px":10000.0,"qty":0.1,"aggressor":"buy"},{"t":1767571200010000000,"type":"trade","px":10001.0,"qty":1.0,"aggressor":"buy"}],"actions":[{"t":1767571200001000000,"op":"place","ref":"o1","side":"buy","type":"limit","qty":1.0,"px":10001.0,"stop_px":null,"tif":"GTC","post_only":true,"reduce_only":false,"oco":null},{"t":1767571200002000000,"op":"place","ref":"o2","side":"buy","type":"limit","qty":1.0,"px":9990.0,"stop_px":null,"tif":"GTC","post_only":true,"reduce_only":false,"oco":null}],"fill_model":null,"latency":null,"costs":{"maker_rate":0.0,"taker_rate":0.0,"source":"場面の定義(費用を測らない場面なので 0 と明示する)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{},"end_t":1767571260000000000}`

#### c2-1-ioc(値の場面)— IOC は、出した時に指値までにある分だけ埋まり、残りは取り消される

- **何を測るか**: IOC の部分約定と残りの取消
- **入力(言葉で)**: 板の売り 10001 x 0.3・10005 x 5。指値 10002 の IOC 買い 1 は、10002 以下の 0.3 だけ埋まり(値 10001)、残り 0.7 は取り消し(status canceled)。
- **期待(正解の関数が入力から計算した値)**: `status.o1` = "canceled" / `filled.o1` = 0.3 / `avg_px.o1` = 10001.0
- **入力(全文)**: `{"product":{"symbol":"FX_BTC_JPY","venue":"bitflyer_cfd","tick":1.0,"min_qty":0.01,"qty_step":1e-08,"quote_ccy":"JPY","margin":true},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade"},"market":[{"t":1767571200000000000,"type":"book","bids":[[9999,5]],"asks":[[10001,0.3],[10005,5]]}],"actions":[{"t":1767571200001000000,"op":"place","ref":"o1","side":"buy","type":"limit","qty":1.0,"px":10002.0,"stop_px":null,"tif":"IOC","post_only":false,"reduce_only":false,"oco":null}],"fill_model":null,"latency":null,"costs":{"maker_rate":0.0,"taker_rate":0.0,"source":"場面の定義(費用を測らない場面なので 0 と明示する)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{},"end_t":1767571260000000000}`

#### c2-1-fok(値の場面)— FOK は、全量が埋まらないなら 1 つも埋まらず、全量が埋まるなら全量が埋まる

- **何を測るか**: FOK の全量か無しか
- **入力(言葉で)**: 板の売り 10001 x 0.3・10005 x 5。o1 = 指値 10002 の FOK 買い 1: 10002 以下は 0.3 < 1 → 約定 0 で終わる(取消か拒否)。o2 = 指値 10002 の FOK 買い 0.2(対照): 0.3 ≥ 0.2 → 全量 0.2 が 10001 で埋まる。
- **期待(正解の関数が入力から計算した値)**: `status.o1` = in ["canceled", "rejected"] / `filled.o1` = 0.0 / `status.o2` = "filled" / `filled.o2` = 0.2 / `avg_px.o2` = 10001.0
- **入力(全文)**: `{"product":{"symbol":"FX_BTC_JPY","venue":"bitflyer_cfd","tick":1.0,"min_qty":0.01,"qty_step":1e-08,"quote_ccy":"JPY","margin":true},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade"},"market":[{"t":1767571200000000000,"type":"book","bids":[[9999,5]],"asks":[[10001,0.3],[10005,5]]}],"actions":[{"t":1767571200001000000,"op":"place","ref":"o1","side":"buy","type":"limit","qty":1.0,"px":10002.0,"stop_px":null,"tif":"FOK","post_only":false,"reduce_only":false,"oco":null},{"t":1767571200002000000,"op":"place","ref":"o2","side":"buy","type":"limit","qty":0.2,"px":10002.0,"stop_px":null,"tif":"FOK","post_only":false,"reduce_only":false,"oco":null}],"fill_model":null,"latency":null,"costs":{"maker_rate":0.0,"taker_rate":0.0,"source":"場面の定義(費用を測らない場面なので 0 と明示する)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{},"end_t":1767571260000000000}`

#### c2-1-stop(値の場面)— 逆指値の買いは、約定の値が逆指値に届いた時に成行になり、その時の売りの気配で埋まる

- **何を測るか**: 逆指値(stop)の発動と約定
- **入力(言葉で)**: 逆指値 10010 の買い 1。出した後の約定で 10010 以上になる最初は 10013(T0+20ms)。その時の板の最良の売りは 10013 → 10013 で全量。10005 の約定では発動しない(first_fill_t ≥ 発動の時刻)。
- **期待(正解の関数が入力から計算した値)**: `status.o1` = "filled" / `filled.o1` = 1.0 / `avg_px.o1` = 10013.0 / `first_fill_t.o1` = ge 1767571200020000000
- **入力(全文)**: `{"product":{"symbol":"FX_BTC_JPY","venue":"bitflyer_cfd","tick":1.0,"min_qty":0.01,"qty_step":1e-08,"quote_ccy":"JPY","margin":true},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade"},"market":[{"t":1767571200000000000,"type":"book","bids":[[9999,5],[9998,5]],"asks":[[10001,5],[10002,5]]},{"t":1767571200000000000,"type":"trade","px":10000.0,"qty":0.1,"aggressor":"buy"},{"t":1767571200010000000,"type":"book","bids":[[9999,5],[9998,5]],"asks":[]},{"t":1767571200010000000,"type":"trade","px":10005.0,"qty":1.0,"aggressor":"buy"},{"t":1767571200019000000,"type":"book","bids":[[10011,5]],"asks":[[10013,5],[10014,5]]},{"t":1767571200020000000,"type":"trade","px":10013.0,"qty":1.0,"aggressor":"buy"},{"t":1767571200030000000,"type":"trade","px":10013.0,"qty":1.0,"aggressor":"buy"}],"actions":[{"t":1767571200001000000,"op":"place","ref":"o1","side":"buy","type":"stop","qty":1.0,"px":null,"stop_px":10010.0,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null}],"fill_model":null,"latency":null,"costs":{"maker_rate":0.0,"taker_rate":0.0,"source":"場面の定義(費用を測らない場面なので 0 と明示する)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{},"end_t":1767571260000000000}`

#### c2-1-reduceonly(値の場面)— reduce-only は建玉を減らす向きにだけ埋まり、増やす向きには埋まらない

- **何を測るか**: reduce-only の拒否と約定
- **入力(言葉で)**: o0 = 成行の買い 2 で建玉 +2。o1 = reduce-only の成行の買い 1 は建玉を増やす → 約定 0(取消か拒否)。o2 = reduce-only の成行の売り 1(対照)は建玉を減らす → 1 埋まる。建玉 = 2 − 1 = 1。
- **期待(正解の関数が入力から計算した値)**: `filled.o0` = 2.0 / `filled.o1` = 0.0 / `status.o1` = in ["canceled", "rejected"] / `filled.o2` = 1.0 / `account.position` = 1.0
- **入力(全文)**: `{"product":{"symbol":"FX_BTC_JPY","venue":"bitflyer_cfd","tick":1.0,"min_qty":0.01,"qty_step":1e-08,"quote_ccy":"JPY","margin":true},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade"},"market":[{"t":1767571200000000000,"type":"book","bids":[[9999,5],[9998,5]],"asks":[[10001,5],[10002,5]]},{"t":1767571200000000000,"type":"trade","px":10000.0,"qty":0.1,"aggressor":"buy"},{"t":1767571200005000000,"type":"trade","px":10001.0,"qty":1.0,"aggressor":"buy"},{"t":1767571200006000000,"type":"trade","px":9999.0,"qty":1.0,"aggressor":"sell"},{"t":1767571200007000000,"type":"trade","px":9999.0,"qty":1.0,"aggressor":"sell"}],"actions":[{"t":1767571200001000000,"op":"place","ref":"o0","side":"buy","type":"market","qty":2.0,"px":null,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null},{"t":1767571200002000000,"op":"place","ref":"o1","side":"buy","type":"market","qty":1.0,"px":null,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":true,"oco":null},{"t":1767571200003000000,"op":"place","ref":"o2","side":"sell","type":"market","qty":1.0,"px":null,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":true,"oco":null}],"fill_model":null,"latency":null,"costs":{"maker_rate":0.0,"taker_rate":0.0,"source":"場面の定義(費用を測らない場面なので 0 と明示する)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{},"end_t":1767571260000000000}`

#### c2-1-oco(値の場面)— OCO は、片方が埋まるともう片方が取り消される

- **何を測るか**: OCO の連動の取消
- **入力(言葉で)**: o0 = 成行の買い 1 で建玉 +1。o1 = 指値 10020 の売り 1 と o2 = 逆指値 9980 の売り 1 を OCO で結ぶ。10025 の約定で o1 が 10020 で埋まり、o2 は取り消し(後の 9970 の約定でも発動しない)。建玉 0。
- **期待(正解の関数が入力から計算した値)**: `status.o1` = "filled" / `filled.o1` = 1.0 / `avg_px.o1` = 10020.0 / `first_fill_t.o1` = ge 1767571200020000000 / `status.o2` = "canceled" / `filled.o2` = 0.0 / `account.position` = 0.0
- **入力(全文)**: `{"product":{"symbol":"FX_BTC_JPY","venue":"bitflyer_cfd","tick":1.0,"min_qty":0.01,"qty_step":1e-08,"quote_ccy":"JPY","margin":true},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade"},"market":[{"t":1767571200000000000,"type":"book","bids":[[9999,5],[9998,5]],"asks":[[10001,5],[10002,5]]},{"t":1767571200000000000,"type":"trade","px":10000.0,"qty":0.1,"aggressor":"buy"},{"t":1767571200005000000,"type":"trade","px":10001.0,"qty":1.0,"aggressor":"buy"},{"t":1767571200010000000,"type":"book","bids":[[9999,5],[9998,5]],"asks":[]},{"t":1767571200010000000,"type":"trade","px":10010.0,"qty":1.0,"aggressor":"buy"},{"t":1767571200020000000,"type":"trade","px":10025.0,"qty":5.0,"aggressor":"buy"},{"t":1767571200030000000,"type":"book","bids":[],"asks":[]},{"t":1767571200030000000,"type":"trade","px":9970.0,"qty":5.0,"aggressor":"sell"}],"actions":[{"t":1767571200001000000,"op":"place","ref":"o0","side":"buy","type":"market","qty":1.0,"px":null,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null},{"t":1767571200002000000,"op":"place","ref":"o1","side":"sell","type":"limit","qty":1.0,"px":10020.0,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":"o2"},{"t":1767571200002000000,"op":"place","ref":"o2","side":"sell","type":"stop","qty":1.0,"px":null,"stop_px":9980.0,"tif":"GTC","post_only":false,"reduce_only":false,"oco":"o1"}],"fill_model":null,"latency":null,"costs":{"maker_rate":0.0,"taker_rate":0.0,"source":"場面の定義(費用を測らない場面なので 0 と明示する)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{},"end_t":1767571260000000000}`

### C2-2 取消と訂正・部分約定(場面 4: 値 2・能力 2)

要件の語 → 場面: 取消 → c2-2-cancel, c2-2-partial / 訂正 → c2-2-amend-price, c2-2-amend-qty / 部分約定 → c2-2-partial, c2-1-ioc / 待ち行列上の位置 → c2-2-amend-qty / 残数量 → c2-2-partial

#### c2-2-cancel(値の場面)— 取り消した指値は、後で値が届いても埋まらない

- **何を測るか**: 取消の状態遷移
- **入力(言葉で)**: 指値 9990 の買いを T0+1ms に出し T0+5ms に取り消す(遅延 0)。T0+10ms の 9985 の約定は取消の後 → 約定 0、status canceled。
- **期待(正解の関数が入力から計算した値)**: `status.o1` = "canceled" / `filled.o1` = 0.0
- **入力(全文)**: `{"product":{"symbol":"FX_BTC_JPY","venue":"bitflyer_cfd","tick":1.0,"min_qty":0.01,"qty_step":1e-08,"quote_ccy":"JPY","margin":true},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade"},"market":[{"t":1767571200000000000,"type":"book","bids":[[9999,5],[9998,5]],"asks":[[10001,5],[10002,5]]},{"t":1767571200000000000,"type":"trade","px":10000.0,"qty":0.1,"aggressor":"buy"},{"t":1767571200010000000,"type":"book","bids":[],"asks":[[10001,5],[10002,5]]},{"t":1767571200010000000,"type":"trade","px":9985.0,"qty":5.0,"aggressor":"sell"}],"actions":[{"t":1767571200001000000,"op":"place","ref":"o1","side":"buy","type":"limit","qty":1.0,"px":9990.0,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null},{"t":1767571200005000000,"op":"cancel","ref":"o1"}],"fill_model":null,"latency":null,"costs":{"maker_rate":0.0,"taker_rate":0.0,"source":"場面の定義(費用を測らない場面なので 0 と明示する)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{},"end_t":1767571260000000000}`

#### c2-2-amend-price(値の場面)— 値を訂正した指値は、新しい値で埋まる

- **何を測るか**: 訂正(値)の反映
- **入力(言葉で)**: 指値 9980 の買いを T0+5ms に 9990 へ訂正。T0+10ms の 9989 の約定は 9990 に届き 9980 には届かない → 新しい値 9990 で 1 埋まる。
- **期待(正解の関数が入力から計算した値)**: `status.o1` = "filled" / `filled.o1` = 1.0 / `avg_px.o1` = 9990.0
- **入力(全文)**: `{"product":{"symbol":"FX_BTC_JPY","venue":"bitflyer_cfd","tick":1.0,"min_qty":0.01,"qty_step":1e-08,"quote_ccy":"JPY","margin":true},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade"},"market":[{"t":1767571200000000000,"type":"book","bids":[[9999,5],[9998,5]],"asks":[[10001,5],[10002,5]]},{"t":1767571200000000000,"type":"trade","px":10000.0,"qty":0.1,"aggressor":"buy"},{"t":1767571200010000000,"type":"book","bids":[],"asks":[[10001,5],[10002,5]]},{"t":1767571200010000000,"type":"trade","px":9989.0,"qty":5.0,"aggressor":"sell"},{"t":1767571200020000000,"type":"trade","px":9995.0,"qty":1.0,"aggressor":"buy"}],"actions":[{"t":1767571200001000000,"op":"place","ref":"o1","side":"buy","type":"limit","qty":1.0,"px":9980.0,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null},{"t":1767571200005000000,"op":"amend","ref":"o1","px":9990,"qty":null}],"fill_model":null,"latency":null,"costs":{"maker_rate":0.0,"taker_rate":0.0,"source":"場面の定義(費用を測らない場面なので 0 と明示する)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{},"end_t":1767571260000000000}`

#### c2-2-amend-qty(能力の場面)— 数量を減らす訂正は列の順位を保つ(規則 amend_qty_down = keep_priority、列の模型 = 段 5)

- **何を測るか**: 訂正(数量)と待ち行列の位置の保持
- **入力(言葉で)**: 9990 の外部の買いの待ち 3 の後ろに買い 2 を付ける(先行 3)。後から外部の 2 が後ろに付く(板 5)。数量を 1 に減らす訂正は順位を保つので先行は 3 のまま。9990 の約定 4 → 先行 3 を消化し残り 1 → 自分に min(1, 1) = 1。順位を失えば先行 5 で 0。
- **期待(正解の関数が入力から計算した値)**: `filled.o1` = 1.0 / `status.o1` = "filled"
- **入力(全文)**: `{"product":{"symbol":"FX_BTC_JPY","venue":"bitflyer_cfd","tick":1.0,"min_qty":0.01,"qty_step":1e-08,"quote_ccy":"JPY","margin":true},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade","amend_qty_down":"keep_priority","amend_price":"lose_priority"},"market":[{"t":1767571200000000000,"type":"book","bids":[[9990,3],[9989,5]],"asks":[[10001,5]]},{"t":1767571200002000000,"type":"book","bids":[[9990,5],[9989,5]],"asks":[[10001,5]]},{"t":1767571200010000000,"type":"trade","px":9990.0,"qty":4.0,"aggressor":"sell"}],"actions":[{"t":1767571200001000000,"op":"place","ref":"o1","side":"buy","type":"limit","qty":2.0,"px":9990.0,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null},{"t":1767571200003000000,"op":"amend","ref":"o1","px":null,"qty":1.0}],"fill_model":{"tier":5,"cancel_stance":"none"},"latency":null,"costs":{"maker_rate":0.0,"taker_rate":0.0,"source":"場面の定義(費用を測らない場面なので 0 と明示する)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{},"end_t":1767571260000000000}`

#### c2-2-partial(能力の場面)— 部分約定した指値は残りが待ち、取り消すと約定済みの分だけ残る(約定の模型 = 段 4)

- **何を測るか**: 部分約定と、部分約定の後の取消
- **入力(言葉で)**: 指値 9990 の買い 3。9985 の約定 1(段 4 = 値に届いた約定の数量まで埋まる)→ 1 埋まり 2 が残る(c1 の時点で累計 1)。取り消した後の 9980 の約定 5 では埋まらない → 終わりの約定 1、status canceled。
- **期待(正解の関数が入力から計算した値)**: `cum.o1@c1` = 1.0 / `filled.o1` = 1.0 / `status.o1` = "canceled"
- **入力(全文)**: `{"product":{"symbol":"FX_BTC_JPY","venue":"bitflyer_cfd","tick":1.0,"min_qty":0.01,"qty_step":1e-08,"quote_ccy":"JPY","margin":true},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade"},"market":[{"t":1767571200000000000,"type":"book","bids":[[9999,5],[9998,5]],"asks":[[10001,5],[10002,5]]},{"t":1767571200000000000,"type":"trade","px":10000.0,"qty":0.1,"aggressor":"buy"},{"t":1767571200010000000,"type":"book","bids":[],"asks":[[10001,5],[10002,5]]},{"t":1767571200010000000,"type":"trade","px":9985.0,"qty":1.0,"aggressor":"sell"},{"t":1767571200030000000,"type":"trade","px":9980.0,"qty":5.0,"aggressor":"sell"}],"actions":[{"t":1767571200001000000,"op":"place","ref":"o1","side":"buy","type":"limit","qty":3.0,"px":9990.0,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null},{"t":1767571200020000000,"op":"cancel","ref":"o1"}],"fill_model":{"tier":4},"latency":null,"costs":{"maker_rate":0.0,"taker_rate":0.0,"source":"場面の定義(費用を測らない場面なので 0 と明示する)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{"c1":1767571200015000000},"end_t":1767571260000000000}`

### C2-3 取引所固有の規則(場面 7: 値 6・能力 1)

要件の語 → 場面: 呼値の拒否 → c2-3-tick / 呼値の丸め → c2-3-round / 最小数量の拒否 → c2-3-minqty / 自己約定防止 → c2-3-stp / FX_BTC_JPY の規則 → c2-3-tick, c2-3-minqty / JPX の取引時間 → c2-3-jpx-session / JPX の値幅制限 → c2-3-jpx-limit / FX の規則 → c2-3-fx-weekend

#### c2-3-tick(値の場面)— 呼値(1 円)に乗らない値の指値は拒否され、乗る値は受け付けられる

- **何を測るか**: 呼値の拒否(規則 off_tick = reject、FX_BTC_JPY の呼値 1)
- **入力(言葉で)**: o1 = 9990.5 は呼値 1 の整数倍でない → 拒否・約定 0。o2 = 9990(対照)は受け付けられ、9985 の約定で 9990 で 1 埋まる。
- **期待(正解の関数が入力から計算した値)**: `status.o1` = "rejected" / `filled.o1` = 0.0 / `filled.o2` = 1.0 / `avg_px.o2` = 9990.0
- **入力(全文)**: `{"product":{"symbol":"FX_BTC_JPY","venue":"bitflyer_cfd","tick":1.0,"min_qty":0.01,"qty_step":1e-08,"quote_ccy":"JPY","margin":true},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade"},"market":[{"t":1767571200000000000,"type":"book","bids":[[9999,5],[9998,5]],"asks":[[10001,5],[10002,5]]},{"t":1767571200000000000,"type":"trade","px":10000.0,"qty":0.1,"aggressor":"buy"},{"t":1767571200010000000,"type":"book","bids":[],"asks":[[10001,5],[10002,5]]},{"t":1767571200010000000,"type":"trade","px":9985.0,"qty":5.0,"aggressor":"sell"}],"actions":[{"t":1767571200001000000,"op":"place","ref":"o1","side":"buy","type":"limit","qty":1.0,"px":9990.5,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null},{"t":1767571200002000000,"op":"place","ref":"o2","side":"buy","type":"limit","qty":1.0,"px":9990.0,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null}],"fill_model":null,"latency":null,"costs":{"maker_rate":0.0,"taker_rate":0.0,"source":"場面の定義(費用を測らない場面なので 0 と明示する)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{},"end_t":1767571260000000000}`

#### c2-3-minqty(値の場面)— 最小数量(0.01)未満の注文は拒否され、最小数量ちょうどは受け付けられる

- **何を測るか**: 最小数量の拒否(規則 below_min_qty = reject)
- **入力(言葉で)**: o1 = 成行の買い 0.005 < 0.01 → 拒否・約定 0。o2 = 成行の買い 0.01(対照)→ 最良の売り 10001 で 0.01 埋まる。
- **期待(正解の関数が入力から計算した値)**: `status.o1` = "rejected" / `filled.o1` = 0.0 / `filled.o2` = 0.01 / `avg_px.o2` = 10001
- **入力(全文)**: `{"product":{"symbol":"FX_BTC_JPY","venue":"bitflyer_cfd","tick":1.0,"min_qty":0.01,"qty_step":1e-08,"quote_ccy":"JPY","margin":true},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade"},"market":[{"t":1767571200000000000,"type":"book","bids":[[9999,5],[9998,5]],"asks":[[10001,5],[10002,5]]},{"t":1767571200000000000,"type":"trade","px":10000.0,"qty":0.1,"aggressor":"buy"},{"t":1767571200005000000,"type":"trade","px":10001.0,"qty":1.0,"aggressor":"buy"}],"actions":[{"t":1767571200001000000,"op":"place","ref":"o1","side":"buy","type":"market","qty":0.005,"px":null,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null},{"t":1767571200002000000,"op":"place","ref":"o2","side":"buy","type":"market","qty":0.01,"px":null,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null}],"fill_model":null,"latency":null,"costs":{"maker_rate":0.0,"taker_rate":0.0,"source":"場面の定義(費用を測らない場面なので 0 と明示する)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{},"end_t":1767571260000000000}`

#### c2-3-round(能力の場面)— 呼値に乗らない値を、受け身の側(買いは下、売りは上)へ丸めて受け付ける(規則 off_tick = round_passive)

- **何を測るか**: 呼値への丸め
- **入力(言葉で)**: o1 = 買い 9990.7 → 床 9990。o2 = 売り 10010.2 → 天井 10011。9985 の約定で o1 が 9990 で、10015 の約定で o2 が 10011 で埋まる。
- **期待(正解の関数が入力から計算した値)**: `avg_px.o1` = 9990.0 / `filled.o1` = 1.0 / `avg_px.o2` = 10011.0 / `filled.o2` = 1.0
- **入力(全文)**: `{"product":{"symbol":"FX_BTC_JPY","venue":"bitflyer_cfd","tick":1.0,"min_qty":0.01,"qty_step":1e-08,"quote_ccy":"JPY","margin":true},"rules":{"off_tick":"round_passive","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade"},"market":[{"t":1767571200000000000,"type":"book","bids":[[9999,5],[9998,5]],"asks":[[10001,5],[10002,5]]},{"t":1767571200000000000,"type":"trade","px":10000.0,"qty":0.1,"aggressor":"buy"},{"t":1767571200010000000,"type":"book","bids":[],"asks":[[10001,5],[10002,5]]},{"t":1767571200010000000,"type":"trade","px":9985.0,"qty":5.0,"aggressor":"sell"},{"t":1767571200020000000,"type":"book","bids":[],"asks":[]},{"t":1767571200020000000,"type":"trade","px":10015.0,"qty":5.0,"aggressor":"buy"}],"actions":[{"t":1767571200001000000,"op":"place","ref":"o1","side":"buy","type":"limit","qty":1.0,"px":9990.7,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null},{"t":1767571200002000000,"op":"place","ref":"o2","side":"sell","type":"limit","qty":1.0,"px":10010.2,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null}],"fill_model":null,"latency":null,"costs":{"maker_rate":0.0,"taker_rate":0.0,"source":"場面の定義(費用を測らない場面なので 0 と明示する)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{},"end_t":1767571260000000000}`

#### c2-3-stp(値の場面)— 自分の指値に自分の成行が当たるときは、当たる側(後の注文)を取り消す(規則 self_trade = cancel_taker)

- **何を測るか**: 自己約定防止
- **入力(言葉で)**: o1 = 売り指値 10000(外部の最良の売り 10001 より良い = 自分が最良の売り)。o2 = 成行の買い 1 は最良の売り = 自分の o1 に当たる → o2 を取り消し(約定 0)、o1 は待ったまま。
- **期待(正解の関数が入力から計算した値)**: `status.o2` = "canceled" / `filled.o2` = 0.0 / `status.o1` = "open" / `filled.o1` = 0.0
- **入力(全文)**: `{"product":{"symbol":"FX_BTC_JPY","venue":"bitflyer_cfd","tick":1.0,"min_qty":0.01,"qty_step":1e-08,"quote_ccy":"JPY","margin":true},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade","self_trade":"cancel_taker"},"market":[{"t":1767571200000000000,"type":"book","bids":[[9999,5]],"asks":[[10001,5]]}],"actions":[{"t":1767571200001000000,"op":"place","ref":"o1","side":"sell","type":"limit","qty":1.0,"px":10000.0,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null},{"t":1767571200002000000,"op":"place","ref":"o2","side":"buy","type":"market","qty":1.0,"px":null,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null}],"fill_model":null,"latency":null,"costs":{"maker_rate":0.0,"taker_rate":0.0,"source":"場面の定義(費用を測らない場面なので 0 と明示する)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{},"end_t":1767571260000000000}`

#### c2-3-jpx-session(値の場面)— JPX の昼休み(11:30-12:30)に出した成行は、後場の始まりに後場の最初の値で埋まる

- **何を測るか**: JPX の取引時間(規則 sessions_jst・outside_session = queue_to_next_open)
- **入力(言葉で)**: 11:45 JST の成行の買い 100。前場の最後の約定 1500(11:29)では埋まらない。後場の最初の約定 1510(12:30:00)で全量、時刻は 12:30 以後。
- **期待(正解の関数が入力から計算した値)**: `filled.o1` = 100.0 / `avg_px.o1` = 1510.0 / `first_fill_t.o1` = ge 1767670200000000000
- **入力(全文)**: `{"product":{"symbol":"JPX_STOCK_A","venue":"jpx_equity","tick":1.0,"min_qty":100.0,"qty_step":100.0,"quote_ccy":"JPY","margin":false},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade","sessions_jst":[["09:00","11:30"],["12:30","15:30"]],"outside_session":"queue_to_next_open","source":"東京証券取引所の立会時間(前場 9:00-11:30、後場 12:30-15:30)。一次資料の頁の確認は本役では未実施(委任文 §4 のネットワークの規則)"},"market":[{"t":1767666540000000000,"type":"book","bids":[[1499,5000]],"asks":[[1501,5000]]},{"t":1767666540000000000,"type":"trade","px":1500.0,"qty":1000.0,"aggressor":"buy"},{"t":1767670200000000000,"type":"book","bids":[[1509,5000]],"asks":[[1510,5000]]},{"t":1767670200000000000,"type":"trade","px":1510.0,"qty":5000.0,"aggressor":"buy"},{"t":1767670260000000000,"type":"book","bids":[[1509,5000]],"asks":[]},{"t":1767670260000000000,"type":"trade","px":1512.0,"qty":1000.0,"aggressor":"buy"}],"actions":[{"t":1767667500000000000,"op":"place","ref":"o1","side":"buy","type":"market","qty":100.0,"px":null,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null}],"fill_model":null,"latency":null,"costs":{"maker_rate":0.0,"taker_rate":0.0,"source":"場面の定義(費用を測らない場面なので 0 と明示する)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{},"end_t":1767672000000000000}`

#### c2-3-jpx-limit(値の場面)— JPX の値幅制限の外の指値は拒否され、内の指値は受け付けられる

- **何を測るか**: JPX の値幅制限(基準値 1000 円 → 制限値幅 300 円 = 700〜1300 円)
- **入力(言葉で)**: 基準値 1000・値幅 300 → 700〜1300。o1 = 買い 1350 は外 → 拒否(受け付けたら最良の売り 1252 に当たる)。o2 = 買い 1250(対照)は内で、最良の売り 1252 未満・1250 に外部の待ちなし → 待ち、1250 の約定で 100 が 1250 で埋まる。
- **期待(正解の関数が入力から計算した値)**: `status.o1` = "rejected" / `filled.o1` = 0.0 / `filled.o2` = 100.0 / `avg_px.o2` = 1250.0
- **入力(全文)**: `{"product":{"symbol":"JPX_STOCK_A","venue":"jpx_equity","tick":1.0,"min_qty":100.0,"qty_step":100.0,"quote_ccy":"JPY","margin":false},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade","sessions_jst":[["09:00","11:30"],["12:30","15:30"]],"outside_session":"queue_to_next_open","source":"東京証券取引所の立会時間(前場 9:00-11:30、後場 12:30-15:30)。一次資料の頁の確認は本役では未実施(委任文 §4 のネットワークの規則)","price_limit":{"base":1000.0,"width":300.0,"source":"東京証券取引所の制限値幅の表(基準値段 1,000 円以上 1,500 円未満 → 300 円)。一次資料の頁の確認は本役では未実施(委任文 §4)"}},"market":[{"t":1767661200000000000,"type":"book","bids":[[1249,5000]],"asks":[[1252,5000]]},{"t":1767661200000000000,"type":"trade","px":1251.0,"qty":100.0,"aggressor":"buy"},{"t":1767661500000000000,"type":"trade","px":1250.0,"qty":1000.0,"aggressor":"sell"},{"t":1767661560000000000,"type":"book","bids":[],"asks":[[1252,5000]]},{"t":1767661560000000000,"type":"trade","px":1240.0,"qty":1000.0,"aggressor":"sell"}],"actions":[{"t":1767661260000000000,"op":"place","ref":"o1","side":"buy","type":"limit","qty":100.0,"px":1350.0,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null},{"t":1767661320000000000,"op":"place","ref":"o2","side":"buy","type":"limit","qty":100.0,"px":1250.0,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null}],"fill_model":null,"latency":null,"costs":{"maker_rate":0.0,"taker_rate":0.0,"source":"場面の定義(費用を測らない場面なので 0 と明示する)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{},"end_t":1767663000000000000}`

#### c2-3-fx-weekend(値の場面)— FX の週末(金 22:00 UTC 〜 日 22:00 UTC)に出した成行は、週明けの最初の気配で埋まる

- **何を測るか**: FX の取引時間(規則 closed_utc_ns・outside_session = queue_to_next_open)
- **入力(言葉で)**: 土曜 03:00 UTC の成行の買い 10000。金曜の最後の気配(売り 150.003)では埋まらない。日曜 22:00 UTC の最初の気配の売り 150.103 で全量、時刻は再開以後。
- **期待(正解の関数が入力から計算した値)**: `filled.o1` = 10000.0 / `avg_px.o1` = 150.103 / `first_fill_t.o1` = ge 1768168800000000000
- **入力(全文)**: `{"product":{"symbol":"USDJPY","venue":"fx","tick":0.001,"min_qty":1000.0,"qty_step":1.0,"quote_ccy":"JPY","margin":true},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade","closed_utc_ns":[[1767996000000000000,1768168800000000000]],"outside_session":"queue_to_next_open","source":"FX の週末の閉場(冬時間、金曜 17:00 ニューヨーク〜日曜 17:00 ニューヨーク)。一次資料の頁の確認は本役では未実施(委任文 §4)"},"market":[{"t":1767995940000000000,"type":"book","bids":[[150.0,1000000.0]],"asks":[[150.003,1000000.0]]},{"t":1767995940000000000,"type":"trade","px":150.001,"qty":10000.0,"aggressor":"buy"},{"t":1768168800000000000,"type":"book","bids":[[150.1,1000000.0]],"asks":[[150.103,1000000.0]]},{"t":1768168800001000000,"type":"trade","px":150.103,"qty":10000.0,"aggressor":"buy"}],"actions":[{"t":1768014000000000000,"op":"place","ref":"o1","side":"buy","type":"market","qty":10000.0,"px":null,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null}],"fill_model":null,"latency":null,"costs":{"maker_rate":0.0,"taker_rate":0.0,"source":"場面の定義(費用を測らない場面なので 0 と明示する)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{},"end_t":1768172400000000000}`

### C2-4 異常系の注入(場面 4: 値 4・能力 0)

要件の語 → 場面: 拒否 → c2-4-reject / 時間切れ → c2-4-timeout / 状態不明を保持し自動で再送しない → c2-4-unknown, c2-4-timeout / Kill Switch での停止 → c2-4-kill

#### c2-4-reject(値の場面)— 注入した拒否で、その注文は拒否され、戦略に拒否の知らせが届く

- **何を測るか**: 拒否の注入
- **入力(言葉で)**: o1 に拒否を注入 → status rejected・約定 0・拒否の知らせが o1 を出した時刻以後に届く。o2(対照、注入なし)は 10001 で 1 埋まる。
- **期待(正解の関数が入力から計算した値)**: `status.o1` = "rejected" / `filled.o1` = 0.0 / `notice.o1.reject` = ge 1767571200001000000 / `filled.o2` = 1.0 / `avg_px.o2` = 10001
- **入力(全文)**: `{"product":{"symbol":"FX_BTC_JPY","venue":"bitflyer_cfd","tick":1.0,"min_qty":0.01,"qty_step":1e-08,"quote_ccy":"JPY","margin":true},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade"},"market":[{"t":1767571200000000000,"type":"book","bids":[[9999,5],[9998,5]],"asks":[[10001,5],[10002,5]]},{"t":1767571200000000000,"type":"trade","px":10000.0,"qty":0.1,"aggressor":"buy"},{"t":1767571200005000000,"type":"trade","px":10001.0,"qty":1.0,"aggressor":"buy"}],"actions":[{"t":1767571200001000000,"op":"place","ref":"o1","side":"buy","type":"market","qty":1.0,"px":null,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null},{"t":1767571200002000000,"op":"place","ref":"o2","side":"buy","type":"market","qty":1.0,"px":null,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null}],"fill_model":null,"latency":null,"costs":{"maker_rate":0.0,"taker_rate":0.0,"source":"場面の定義(費用を測らない場面なので 0 と明示する)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[{"kind":"reject","ref":"o1"}],"checkpoints":{},"end_t":1767571260000000000}`

#### c2-4-timeout(値の場面)— 発注の時間切れは状態不明として保持され、自動で再送されない

- **何を測るか**: 時間切れの注入(CLAUDE.md §1: 曖昧な失敗は STATE_UNKNOWN、自動で再送しない)
- **入力(言葉で)**: o1 の発注に時間切れ(応答なし)を注入 → 状態不明のまま終わる・取引所に届いた発注は 1 回(再送 0)・約定を仮定しない(0)。
- **期待(正解の関数が入力から計算した値)**: `status.o1` = "state_unknown" / `sent.o1` = 1 / `filled.o1` = 0.0
- **入力(全文)**: `{"product":{"symbol":"FX_BTC_JPY","venue":"bitflyer_cfd","tick":1.0,"min_qty":0.01,"qty_step":1e-08,"quote_ccy":"JPY","margin":true},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade"},"market":[{"t":1767571200000000000,"type":"book","bids":[[9999,5],[9998,5]],"asks":[[10001,5],[10002,5]]},{"t":1767571200000000000,"type":"trade","px":10000.0,"qty":0.1,"aggressor":"buy"},{"t":1767571200005000000,"type":"trade","px":10001.0,"qty":1.0,"aggressor":"buy"}],"actions":[{"t":1767571200001000000,"op":"place","ref":"o1","side":"buy","type":"market","qty":1.0,"px":null,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null}],"fill_model":null,"latency":null,"costs":{"maker_rate":0.0,"taker_rate":0.0,"source":"場面の定義(費用を測らない場面なので 0 と明示する)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[{"kind":"timeout","ref":"o1"}],"checkpoints":{},"end_t":1767571260000000000}`

#### c2-4-unknown(値の場面)— 曖昧な失敗は状態不明として保持され、自動で再送されない

- **何を測るか**: 状態不明の注入(CLAUDE.md §1)
- **入力(言葉で)**: o1 の発注の応答に曖昧な失敗を注入 → 状態不明・届いた発注 1 回・約定を仮定しない(0)。
- **期待(正解の関数が入力から計算した値)**: `status.o1` = "state_unknown" / `sent.o1` = 1 / `filled.o1` = 0.0
- **入力(全文)**: `{"product":{"symbol":"FX_BTC_JPY","venue":"bitflyer_cfd","tick":1.0,"min_qty":0.01,"qty_step":1e-08,"quote_ccy":"JPY","margin":true},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade"},"market":[{"t":1767571200000000000,"type":"book","bids":[[9999,5],[9998,5]],"asks":[[10001,5],[10002,5]]},{"t":1767571200000000000,"type":"trade","px":10000.0,"qty":0.1,"aggressor":"buy"},{"t":1767571200005000000,"type":"trade","px":10001.0,"qty":1.0,"aggressor":"buy"}],"actions":[{"t":1767571200001000000,"op":"place","ref":"o1","side":"buy","type":"market","qty":1.0,"px":null,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null}],"fill_model":null,"latency":null,"costs":{"maker_rate":0.0,"taker_rate":0.0,"source":"場面の定義(費用を測らない場面なので 0 と明示する)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[{"kind":"unknown","ref":"o1"}],"checkpoints":{},"end_t":1767571260000000000}`

#### c2-4-kill(値の場面)— Kill Switch の後の新しい注文は取引所へ送られず拒否され、その後も戻らない

- **何を測るか**: Kill Switch での停止
- **入力(言葉で)**: T0+5ms に Kill Switch。o2(T0+6ms)と o3(T0+20ms)は送られず(届いた発注 0)拒否・約定 0。自動で戻らないので o3 も拒否。
- **期待(正解の関数が入力から計算した値)**: `status.o2` = "rejected" / `sent.o2` = 0 / `filled.o2` = 0.0 / `status.o3` = "rejected" / `sent.o3` = 0 / `filled.o3` = 0.0
- **入力(全文)**: `{"product":{"symbol":"FX_BTC_JPY","venue":"bitflyer_cfd","tick":1.0,"min_qty":0.01,"qty_step":1e-08,"quote_ccy":"JPY","margin":true},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade"},"market":[{"t":1767571200000000000,"type":"book","bids":[[9999,5],[9998,5]],"asks":[[10001,5],[10002,5]]},{"t":1767571200000000000,"type":"trade","px":10000.0,"qty":0.1,"aggressor":"buy"},{"t":1767571200010000000,"type":"trade","px":10001.0,"qty":1.0,"aggressor":"buy"},{"t":1767571200025000000,"type":"trade","px":10001.0,"qty":1.0,"aggressor":"buy"}],"actions":[{"t":1767571200001000000,"op":"place","ref":"o1","side":"buy","type":"limit","qty":1.0,"px":9990.0,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null},{"t":1767571200005000000,"op":"kill"},{"t":1767571200006000000,"op":"place","ref":"o2","side":"buy","type":"market","qty":1.0,"px":null,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null},{"t":1767571200020000000,"op":"place","ref":"o3","side":"buy","type":"market","qty":1.0,"px":null,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null}],"fill_model":null,"latency":null,"costs":{"maker_rate":0.0,"taker_rate":0.0,"source":"場面の定義(費用を測らない場面なので 0 と明示する)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{},"end_t":1767571260000000000}`

### C2-5 約定/待ち行列の段(場面 8: 値 1・能力 7)

要件の語 → 場面: 段 0 → c2-5-tier0 / 段 1 → c2-5-tier1 / 段 2 → c2-5-tier2 / 段 3 → c2-5-tier3 / 段 4 → c2-5-tier4 / 段 5 → c2-5-tier5 / 段 6 → c2-5-tier6 / 列の位置の値 → c2-5-queue-value

#### c2-5-tier0(能力の場面)— 約定の模型の段 0 を選べ、選んだ段の規則どおりに埋まる

- **何を測るか**: 段 0 を選べること(選んだ段の埋まり方の累計が正解と一致)
- **入力(言葉で)**: 指値 9995 の買い 2(T0+500ms)。板の最良の買い 9995 に外部の 2。約定 9995 x 1(T0+1010ms)・9995 x 1.5(1020ms)・9994 x 2(1030ms)。段 0 = 出した時点で指値で全量が埋まる。c1〜cend の累計 2、最初の約定の時刻 = 出した時刻。(段の規則の文は道具台帳 §2.1 の 1 行の定義を、この場面の入力で測れる形に場面係が具体にしたもの)
- **期待(正解の関数が入力から計算した値)**: `cum.o1@c1` = 2.0 / `cum.o1@c2` = 2.0 / `cum.o1@c3` = 2.0 / `cum.o1@cend` = 2.0 / `first_fill_t.o1` = 1767571200500000000
- **入力(全文)**: `{"product":{"symbol":"FX_BTC_JPY","venue":"bitflyer_cfd","tick":1.0,"min_qty":0.01,"qty_step":1e-08,"quote_ccy":"JPY","margin":true},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade"},"market":[{"t":1767571200000000000,"type":"book","bids":[[9995,2],[9990,5]],"asks":[[10001,5]]},{"t":1767571200000000000,"type":"trade","px":9998.0,"qty":0.1,"aggressor":"buy"},{"t":1767571201010000000,"type":"trade","px":9995.0,"qty":1.0,"aggressor":"sell"},{"t":1767571201020000000,"type":"trade","px":9995.0,"qty":1.5,"aggressor":"sell"},{"t":1767571201030000000,"type":"book","bids":[[9990,5]],"asks":[[10001,5]]},{"t":1767571201030000000,"type":"trade","px":9994.0,"qty":2.0,"aggressor":"sell"}],"actions":[{"t":1767571200500000000,"op":"place","ref":"o1","side":"buy","type":"limit","qty":2.0,"px":9995.0,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null}],"fill_model":{"tier":0,"cancel_stance":"none","bar_ns":1000000000},"latency":null,"costs":{"maker_rate":0.0,"taker_rate":0.0,"source":"場面の定義(費用を測らない場面なので 0 と明示する)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{"c1":1767571201015000000,"c2":1767571201025000000,"c3":1767571201035000000,"cend":1767571202500000000},"end_t":1767571203000000000}`

#### c2-5-tier1(能力の場面)— 約定の模型の段 1 を選べ、選んだ段の規則どおりに埋まる

- **何を測るか**: 段 1 を選べること(選んだ段の埋まり方の累計が正解と一致)
- **入力(言葉で)**: 指値 9995 の買い 2(T0+500ms)。板の最良の買い 9995 に外部の 2。約定 9995 x 1(T0+1010ms)・9995 x 1.5(1020ms)・9994 x 2(1030ms)。段 1 = 値が指値を跨いだ(買いなら指値より下の約定)最初の時点で全量。9995 の約定 2 本は跨いでいない、9994(T0+1030ms)で跨ぐ → c1・c2 は 0、c3・cend は 2。(段の規則の文は道具台帳 §2.1 の 1 行の定義を、この場面の入力で測れる形に場面係が具体にしたもの)
- **期待(正解の関数が入力から計算した値)**: `cum.o1@c1` = 0.0 / `cum.o1@c2` = 0.0 / `cum.o1@c3` = 2.0 / `cum.o1@cend` = 2.0 / `first_fill_t.o1` = 1767571201030000000
- **入力(全文)**: `{"product":{"symbol":"FX_BTC_JPY","venue":"bitflyer_cfd","tick":1.0,"min_qty":0.01,"qty_step":1e-08,"quote_ccy":"JPY","margin":true},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade"},"market":[{"t":1767571200000000000,"type":"book","bids":[[9995,2],[9990,5]],"asks":[[10001,5]]},{"t":1767571200000000000,"type":"trade","px":9998.0,"qty":0.1,"aggressor":"buy"},{"t":1767571201010000000,"type":"trade","px":9995.0,"qty":1.0,"aggressor":"sell"},{"t":1767571201020000000,"type":"trade","px":9995.0,"qty":1.5,"aggressor":"sell"},{"t":1767571201030000000,"type":"book","bids":[[9990,5]],"asks":[[10001,5]]},{"t":1767571201030000000,"type":"trade","px":9994.0,"qty":2.0,"aggressor":"sell"}],"actions":[{"t":1767571200500000000,"op":"place","ref":"o1","side":"buy","type":"limit","qty":2.0,"px":9995.0,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null}],"fill_model":{"tier":1,"cancel_stance":"none","bar_ns":1000000000},"latency":null,"costs":{"maker_rate":0.0,"taker_rate":0.0,"source":"場面の定義(費用を測らない場面なので 0 と明示する)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{"c1":1767571201015000000,"c2":1767571201025000000,"c3":1767571201035000000,"cend":1767571202500000000},"end_t":1767571203000000000}`

#### c2-5-tier2(能力の場面)— 約定の模型の段 2 を選べ、選んだ段の規則どおりに埋まる

- **何を測るか**: 段 2 を選べること(選んだ段の埋まり方の累計が正解と一致)
- **入力(言葉で)**: 指値 9995 の買い 2(T0+500ms)。板の最良の買い 9995 に外部の 2。約定 9995 x 1(T0+1010ms)・9995 x 1.5(1020ms)・9994 x 2(1030ms)。段 2 = 1 秒の足。出した足(0 秒目)より後の足で安値が指値に届いた最初の足の終わり(T0+2s)に全量。c1〜c3 は 0、cend は 2。(段の規則の文は道具台帳 §2.1 の 1 行の定義を、この場面の入力で測れる形に場面係が具体にしたもの)
- **期待(正解の関数が入力から計算した値)**: `cum.o1@c1` = 0.0 / `cum.o1@c2` = 0.0 / `cum.o1@c3` = 0.0 / `cum.o1@cend` = 2.0 / `first_fill_t.o1` = 1767571202000000000
- **入力(全文)**: `{"product":{"symbol":"FX_BTC_JPY","venue":"bitflyer_cfd","tick":1.0,"min_qty":0.01,"qty_step":1e-08,"quote_ccy":"JPY","margin":true},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade"},"market":[{"t":1767571200000000000,"type":"book","bids":[[9995,2],[9990,5]],"asks":[[10001,5]]},{"t":1767571200000000000,"type":"trade","px":9998.0,"qty":0.1,"aggressor":"buy"},{"t":1767571201010000000,"type":"trade","px":9995.0,"qty":1.0,"aggressor":"sell"},{"t":1767571201020000000,"type":"trade","px":9995.0,"qty":1.5,"aggressor":"sell"},{"t":1767571201030000000,"type":"book","bids":[[9990,5]],"asks":[[10001,5]]},{"t":1767571201030000000,"type":"trade","px":9994.0,"qty":2.0,"aggressor":"sell"}],"actions":[{"t":1767571200500000000,"op":"place","ref":"o1","side":"buy","type":"limit","qty":2.0,"px":9995.0,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null}],"fill_model":{"tier":2,"cancel_stance":"none","bar_ns":1000000000},"latency":null,"costs":{"maker_rate":0.0,"taker_rate":0.0,"source":"場面の定義(費用を測らない場面なので 0 と明示する)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{"c1":1767571201015000000,"c2":1767571201025000000,"c3":1767571201035000000,"cend":1767571202500000000},"end_t":1767571203000000000}`

#### c2-5-tier3(能力の場面)— 約定の模型の段 3 を選べ、選んだ段の規則どおりに埋まる

- **何を測るか**: 段 3 を選べること(選んだ段の埋まり方の累計が正解と一致)
- **入力(言葉で)**: 指値 9995 の買い 2(T0+500ms)。板の最良の買い 9995 に外部の 2。約定 9995 x 1(T0+1010ms)・9995 x 1.5(1020ms)・9994 x 2(1030ms)。段 3 = 指値に届いた約定の事象が来た時点で全量。9995(T0+1010ms)で届く → c1 から 2、最初の約定の時刻 T0+1010ms。(段の規則の文は道具台帳 §2.1 の 1 行の定義を、この場面の入力で測れる形に場面係が具体にしたもの)
- **期待(正解の関数が入力から計算した値)**: `cum.o1@c1` = 2.0 / `cum.o1@c2` = 2.0 / `cum.o1@c3` = 2.0 / `cum.o1@cend` = 2.0 / `first_fill_t.o1` = 1767571201010000000
- **入力(全文)**: `{"product":{"symbol":"FX_BTC_JPY","venue":"bitflyer_cfd","tick":1.0,"min_qty":0.01,"qty_step":1e-08,"quote_ccy":"JPY","margin":true},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade"},"market":[{"t":1767571200000000000,"type":"book","bids":[[9995,2],[9990,5]],"asks":[[10001,5]]},{"t":1767571200000000000,"type":"trade","px":9998.0,"qty":0.1,"aggressor":"buy"},{"t":1767571201010000000,"type":"trade","px":9995.0,"qty":1.0,"aggressor":"sell"},{"t":1767571201020000000,"type":"trade","px":9995.0,"qty":1.5,"aggressor":"sell"},{"t":1767571201030000000,"type":"book","bids":[[9990,5]],"asks":[[10001,5]]},{"t":1767571201030000000,"type":"trade","px":9994.0,"qty":2.0,"aggressor":"sell"}],"actions":[{"t":1767571200500000000,"op":"place","ref":"o1","side":"buy","type":"limit","qty":2.0,"px":9995.0,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null}],"fill_model":{"tier":3,"cancel_stance":"none","bar_ns":1000000000},"latency":null,"costs":{"maker_rate":0.0,"taker_rate":0.0,"source":"場面の定義(費用を測らない場面なので 0 と明示する)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{"c1":1767571201015000000,"c2":1767571201025000000,"c3":1767571201035000000,"cend":1767571202500000000},"end_t":1767571203000000000}`

#### c2-5-tier4(能力の場面)— 約定の模型の段 4 を選べ、選んだ段の規則どおりに埋まる

- **何を測るか**: 段 4 を選べること(選んだ段の埋まり方の累計が正解と一致)
- **入力(言葉で)**: 指値 9995 の買い 2(T0+500ms)。板の最良の買い 9995 に外部の 2。約定 9995 x 1(T0+1010ms)・9995 x 1.5(1020ms)・9994 x 2(1030ms)。段 4 = 指値に届いた約定の数量まで埋まる(列なし)。1010ms に 1、1020ms に残り 1 → c1 = 1、c2 以後 2。(段の規則の文は道具台帳 §2.1 の 1 行の定義を、この場面の入力で測れる形に場面係が具体にしたもの)
- **期待(正解の関数が入力から計算した値)**: `cum.o1@c1` = 1.0 / `cum.o1@c2` = 2.0 / `cum.o1@c3` = 2.0 / `cum.o1@cend` = 2.0 / `first_fill_t.o1` = 1767571201010000000
- **入力(全文)**: `{"product":{"symbol":"FX_BTC_JPY","venue":"bitflyer_cfd","tick":1.0,"min_qty":0.01,"qty_step":1e-08,"quote_ccy":"JPY","margin":true},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade"},"market":[{"t":1767571200000000000,"type":"book","bids":[[9995,2],[9990,5]],"asks":[[10001,5]]},{"t":1767571200000000000,"type":"trade","px":9998.0,"qty":0.1,"aggressor":"buy"},{"t":1767571201010000000,"type":"trade","px":9995.0,"qty":1.0,"aggressor":"sell"},{"t":1767571201020000000,"type":"trade","px":9995.0,"qty":1.5,"aggressor":"sell"},{"t":1767571201030000000,"type":"book","bids":[[9990,5]],"asks":[[10001,5]]},{"t":1767571201030000000,"type":"trade","px":9994.0,"qty":2.0,"aggressor":"sell"}],"actions":[{"t":1767571200500000000,"op":"place","ref":"o1","side":"buy","type":"limit","qty":2.0,"px":9995.0,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null}],"fill_model":{"tier":4,"cancel_stance":"none","bar_ns":1000000000},"latency":null,"costs":{"maker_rate":0.0,"taker_rate":0.0,"source":"場面の定義(費用を測らない場面なので 0 と明示する)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{"c1":1767571201015000000,"c2":1767571201025000000,"c3":1767571201035000000,"cend":1767571202500000000},"end_t":1767571203000000000}`

#### c2-5-tier5(能力の場面)— 約定の模型の段 5 を選べ、選んだ段の規則どおりに埋まる

- **何を測るか**: 段 5 を選べること(選んだ段の埋まり方の累計が正解と一致)
- **入力(言葉で)**: 指値 9995 の買い 2(T0+500ms)。板の最良の買い 9995 に外部の 2。約定 9995 x 1(T0+1010ms)・9995 x 1.5(1020ms)・9994 x 2(1030ms)。段 5 = 列: 出した時の 9995 の表示 2 が先行。1010ms の 1 と 1020ms の 1.5 で先行 2 を消化し 0.5 が自分へ、1030ms の 9994 x 2 は跨ぐので残り 1.5 → c1 = 0、c2 = 0.5、c3・cend = 2。(段の規則の文は道具台帳 §2.1 の 1 行の定義を、この場面の入力で測れる形に場面係が具体にしたもの)
- **期待(正解の関数が入力から計算した値)**: `cum.o1@c1` = 0.0 / `cum.o1@c2` = 0.5 / `cum.o1@c3` = 2.0 / `cum.o1@cend` = 2.0 / `first_fill_t.o1` = 1767571201020000000
- **入力(全文)**: `{"product":{"symbol":"FX_BTC_JPY","venue":"bitflyer_cfd","tick":1.0,"min_qty":0.01,"qty_step":1e-08,"quote_ccy":"JPY","margin":true},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade"},"market":[{"t":1767571200000000000,"type":"book","bids":[[9995,2],[9990,5]],"asks":[[10001,5]]},{"t":1767571200000000000,"type":"trade","px":9998.0,"qty":0.1,"aggressor":"buy"},{"t":1767571201010000000,"type":"trade","px":9995.0,"qty":1.0,"aggressor":"sell"},{"t":1767571201020000000,"type":"trade","px":9995.0,"qty":1.5,"aggressor":"sell"},{"t":1767571201030000000,"type":"book","bids":[[9990,5]],"asks":[[10001,5]]},{"t":1767571201030000000,"type":"trade","px":9994.0,"qty":2.0,"aggressor":"sell"}],"actions":[{"t":1767571200500000000,"op":"place","ref":"o1","side":"buy","type":"limit","qty":2.0,"px":9995.0,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null}],"fill_model":{"tier":5,"cancel_stance":"none","bar_ns":1000000000},"latency":null,"costs":{"maker_rate":0.0,"taker_rate":0.0,"source":"場面の定義(費用を測らない場面なので 0 と明示する)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{"c1":1767571201015000000,"c2":1767571201025000000,"c3":1767571201035000000,"cend":1767571202500000000},"end_t":1767571203000000000}`

#### c2-5-queue-value(値の場面)— 段 5(列の位置)で、先行の量を約定が消化した残りだけ自分が埋まる(値)

- **何を測るか**: 段 5 の列の位置の計算の値(先行 1.2、約定 0.5・0.9・0.4)
- **入力(言葉で)**: 9995 の外部の買い 1.2 の後ろに買い 1。0.5 で先行 0.7、0.9 で先行 0 になり残り 0.2 が自分へ、0.4 で 0.4 → c1 = 0、c2 = 0.2、c3 = 0.6。
- **期待(正解の関数が入力から計算した値)**: `cum.o1@c1` = 0.0 / `cum.o1@c2` = 0.2 / `cum.o1@c3` = 0.6 / `first_fill_t.o1` = 1767571200020000000
- **入力(全文)**: `{"product":{"symbol":"FX_BTC_JPY","venue":"bitflyer_cfd","tick":1.0,"min_qty":0.01,"qty_step":1e-08,"quote_ccy":"JPY","margin":true},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade"},"market":[{"t":1767571200000000000,"type":"book","bids":[[9995,1.2],[9990,5]],"asks":[[10001,5]]},{"t":1767571200000000000,"type":"trade","px":10000.0,"qty":0.1,"aggressor":"buy"},{"t":1767571200010000000,"type":"trade","px":9995.0,"qty":0.5,"aggressor":"sell"},{"t":1767571200020000000,"type":"trade","px":9995.0,"qty":0.9,"aggressor":"sell"},{"t":1767571200030000000,"type":"trade","px":9995.0,"qty":0.4,"aggressor":"sell"}],"actions":[{"t":1767571200001000000,"op":"place","ref":"o1","side":"buy","type":"limit","qty":1.0,"px":9995.0,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null}],"fill_model":{"tier":5,"cancel_stance":"none","bar_ns":1000000000},"latency":null,"costs":{"maker_rate":0.0,"taker_rate":0.0,"source":"場面の定義(費用を測らない場面なので 0 と明示する)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{"c1":1767571200015000000,"c2":1767571200025000000,"c3":1767571200035000000},"end_t":1767571201000000000}`

#### c2-5-tier6(能力の場面)— 約定の模型の段 6(市場影響の関数)を選べ、関数どおりの値で埋まる

- **何を測るか**: 段 6 を選べること(一時的な影響 = 最良の売り + k × 数量)
- **入力(言葉で)**: 成行の買い 3、k = 2 円/単位。最良の売り 10001 + 2 × 3 = 10007 で全量。
- **期待(正解の関数が入力から計算した値)**: `filled.o1` = 3.0 / `avg_px.o1` = 10007.0
- **入力(全文)**: `{"product":{"symbol":"FX_BTC_JPY","venue":"bitflyer_cfd","tick":1.0,"min_qty":0.01,"qty_step":1e-08,"quote_ccy":"JPY","margin":true},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade"},"market":[{"t":1767571200000000000,"type":"book","bids":[[9999,5],[9998,5]],"asks":[[10001,5],[10002,5]]},{"t":1767571200000000000,"type":"trade","px":10000.0,"qty":0.1,"aggressor":"buy"},{"t":1767571200005000000,"type":"trade","px":10001.0,"qty":5.0,"aggressor":"buy"}],"actions":[{"t":1767571200001000000,"op":"place","ref":"o1","side":"buy","type":"market","qty":3.0,"px":null,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null}],"fill_model":{"tier":6,"impact":{"kind":"linear_temporary","k":2.0,"basis":"best_ask"}},"latency":null,"costs":{"maker_rate":0.0,"taker_rate":0.0,"source":"場面の定義(費用を測らない場面なので 0 と明示する)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{},"end_t":1767571260000000000}`

### C2-6 列の位置の追跡・先行注文の取り消しの扱い(場面 6: 値 1・能力 5)

要件の語 → 場面: 何もしない → c2-6-none / 出した瞬間に割り引く → c2-6-discount-at-entry / 取消の時点で繰り上がる → c2-6-l3 / 印を付けて列に残す → c2-6-l3 / 写真の量で先行を下げる → c2-6-snapshot-cap / 確率型の列の模型 → c2-6-prob, c2-6-prob-power2

#### c2-6-none(能力の場面)— 先行注文の取り消しの扱い「何もしない(先行の取消は見えないので繰り上がらない)」を選べ、その規則どおりに埋まる

- **何を測るか**: 先行注文の取り消しの扱いを選べること(埋まる量が立場の規則の正解と一致)
- **入力(言葉で)**: 9995 の外部の買い 5 の後ろに買い 3(先行 5)。外部の 3 が後ろに付き(板 8)、4 が取り消される(板 4。L3 の場面では e1・e2・e3・e6)。9995 の約定 4.5。先行 5 のまま。約定 4.5 < 5 → 0。
- **期待(正解の関数が入力から計算した値)**: `filled.o1` = 0.0
- **入力(全文)**: `{"product":{"symbol":"FX_BTC_JPY","venue":"bitflyer_cfd","tick":1.0,"min_qty":0.01,"qty_step":1e-08,"quote_ccy":"JPY","margin":true},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade"},"market":[{"t":1767571200000000000,"type":"book","bids":[[9995,5],[9990,5]],"asks":[[10001,5]]},{"t":1767571200002000000,"type":"book","bids":[[9995,8],[9990,5]],"asks":[[10001,5]]},{"t":1767571200003000000,"type":"book","bids":[[9995,4],[9990,5]],"asks":[[10001,5]]},{"t":1767571200010000000,"type":"trade","px":9995.0,"qty":4.5,"aggressor":"sell"}],"actions":[{"t":1767571200001000000,"op":"place","ref":"o1","side":"buy","type":"limit","qty":3.0,"px":9995.0,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null}],"fill_model":{"tier":5,"cancel_stance":"none"},"latency":null,"costs":{"maker_rate":0.0,"taker_rate":0.0,"source":"場面の定義(費用を測らない場面なので 0 と明示する)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{},"end_t":1767571200050000000}`

#### c2-6-discount-at-entry(能力の場面)— 先行注文の取り消しの扱い「出した瞬間に 1 回、平均の取消率 r で先行を割り引く(r = 0.4)」を選べ、その規則どおりに埋まる

- **何を測るか**: 先行注文の取り消しの扱いを選べること(埋まる量が立場の規則の正解と一致)
- **入力(言葉で)**: 9995 の外部の買い 5 の後ろに買い 3(先行 5)。外部の 3 が後ろに付き(板 8)、4 が取り消される(板 4。L3 の場面では e1・e2・e3・e6)。9995 の約定 4.5。先行 5 × (1 − 0.4) = 3。約定 4.5 − 3 = 1.5 → min(3, 1.5) = 1.5。
- **期待(正解の関数が入力から計算した値)**: `filled.o1` = 1.5
- **入力(全文)**: `{"product":{"symbol":"FX_BTC_JPY","venue":"bitflyer_cfd","tick":1.0,"min_qty":0.01,"qty_step":1e-08,"quote_ccy":"JPY","margin":true},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade"},"market":[{"t":1767571200000000000,"type":"book","bids":[[9995,5],[9990,5]],"asks":[[10001,5]]},{"t":1767571200002000000,"type":"book","bids":[[9995,8],[9990,5]],"asks":[[10001,5]]},{"t":1767571200003000000,"type":"book","bids":[[9995,4],[9990,5]],"asks":[[10001,5]]},{"t":1767571200010000000,"type":"trade","px":9995.0,"qty":4.5,"aggressor":"sell"}],"actions":[{"t":1767571200001000000,"op":"place","ref":"o1","side":"buy","type":"limit","qty":3.0,"px":9995.0,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null}],"fill_model":{"tier":5,"cancel_stance":"discount_at_entry","cancel_rate":0.4},"latency":null,"costs":{"maker_rate":0.0,"taker_rate":0.0,"source":"場面の定義(費用を測らない場面なので 0 と明示する)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{},"end_t":1767571200050000000}`

#### c2-6-snapshot-cap(能力の場面)— 先行注文の取り消しの扱い「板の写真の量が先行量を下回ったら、先行量をその量まで下げる」を選べ、その規則どおりに埋まる

- **何を測るか**: 先行注文の取り消しの扱いを選べること(埋まる量が立場の規則の正解と一致)
- **入力(言葉で)**: 9995 の外部の買い 5 の後ろに買い 3(先行 5)。外部の 3 が後ろに付き(板 8)、4 が取り消される(板 4。L3 の場面では e1・e2・e3・e6)。9995 の約定 4.5。T0+2ms の 8 では変わらず、T0+3ms の 4 で先行 = min(5, 4) = 4。4.5 − 4 = 0.5。
- **期待(正解の関数が入力から計算した値)**: `filled.o1` = 0.5
- **入力(全文)**: `{"product":{"symbol":"FX_BTC_JPY","venue":"bitflyer_cfd","tick":1.0,"min_qty":0.01,"qty_step":1e-08,"quote_ccy":"JPY","margin":true},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade"},"market":[{"t":1767571200000000000,"type":"book","bids":[[9995,5],[9990,5]],"asks":[[10001,5]]},{"t":1767571200002000000,"type":"book","bids":[[9995,8],[9990,5]],"asks":[[10001,5]]},{"t":1767571200003000000,"type":"book","bids":[[9995,4],[9990,5]],"asks":[[10001,5]]},{"t":1767571200010000000,"type":"trade","px":9995.0,"qty":4.5,"aggressor":"sell"}],"actions":[{"t":1767571200001000000,"op":"place","ref":"o1","side":"buy","type":"limit","qty":3.0,"px":9995.0,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null}],"fill_model":{"tier":5,"cancel_stance":"snapshot_cap"},"latency":null,"costs":{"maker_rate":0.0,"taker_rate":0.0,"source":"場面の定義(費用を測らない場面なので 0 と明示する)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{},"end_t":1767571200050000000}`

#### c2-6-l3(能力の場面)— 先行注文の取り消しの扱い「取り消された注文が列から抜ける(取消の時点で繰り上がる / 印を付けて通り過ぎる。2 つの立場の埋まる量は同じ)」を選べ、その規則どおりに埋まる

- **何を測るか**: 先行注文の取り消しの扱いを選べること(埋まる量が立場の規則の正解と一致)
- **入力(言葉で)**: 9995 の外部の買い 5 の後ろに買い 3(先行 5)。外部の 3 が後ろに付き(板 8)、4 が取り消される(板 4。L3 の場面では e1・e2・e3・e6)。9995 の約定 4.5。先行 e1〜e5 のうち e1・e2・e3 が取消 → 先行 2(後ろの e6 の取消は先行に響かない)。4.5 − 2 = 2.5 → min(3, 2.5) = 2.5。
- **期待(正解の関数が入力から計算した値)**: `filled.o1` = 2.5
- **入力(全文)**: `{"product":{"symbol":"FX_BTC_JPY","venue":"bitflyer_cfd","tick":1.0,"min_qty":0.01,"qty_step":1e-08,"quote_ccy":"JPY","margin":true},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade"},"market":[{"t":1767571200000000000,"type":"l3_add","id":"e1","side":"bid","px":9995.0,"qty":1.0},{"t":1767571200000000000,"type":"l3_add","id":"e2","side":"bid","px":9995.0,"qty":1.0},{"t":1767571200000000000,"type":"l3_add","id":"e3","side":"bid","px":9995.0,"qty":1.0},{"t":1767571200000000000,"type":"l3_add","id":"e4","side":"bid","px":9995.0,"qty":1.0},{"t":1767571200000000000,"type":"l3_add","id":"e5","side":"bid","px":9995.0,"qty":1.0},{"t":1767571200000000000,"type":"book","bids":[[9995,5],[9990,5]],"asks":[[10001,5]]},{"t":1767571200002000000,"type":"l3_add","id":"e6","side":"bid","px":9995.0,"qty":1.0},{"t":1767571200002000000,"type":"l3_add","id":"e7","side":"bid","px":9995.0,"qty":1.0},{"t":1767571200002000000,"type":"l3_add","id":"e8","side":"bid","px":9995.0,"qty":1.0},{"t":1767571200003000000,"type":"l3_cancel","id":"e1"},{"t":1767571200003000000,"type":"l3_cancel","id":"e2"},{"t":1767571200003000000,"type":"l3_cancel","id":"e3"},{"t":1767571200003000000,"type":"l3_cancel","id":"e6"},{"t":1767571200010000000,"type":"trade","px":9995.0,"qty":4.5,"aggressor":"sell"}],"actions":[{"t":1767571200001000000,"op":"place","ref":"o1","side":"buy","type":"limit","qty":3.0,"px":9995.0,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null}],"fill_model":{"tier":5,"cancel_stance":"l3"},"latency":null,"costs":{"maker_rate":0.0,"taker_rate":0.0,"source":"場面の定義(費用を測らない場面なので 0 と明示する)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{},"end_t":1767571200050000000}`

#### c2-6-prob(能力の場面)— 先行注文の取り消しの扱い「確率型の列: 板の減少のうち前にあった割合 = f(後ろ)/(f(後ろ)+f(前))、f(x) = x」を選べ、その規則どおりに埋まる

- **何を測るか**: 先行注文の取り消しの扱いを選べること(埋まる量が立場の規則の正解と一致)
- **入力(言葉で)**: 9995 の外部の買い 5 の後ろに買い 3(先行 5)。外部の 3 が後ろに付き(板 8)、4 が取り消される(板 4。L3 の場面では e1・e2・e3・e6)。9995 の約定 4.5。T0+2ms の増加 5→8 は後ろだけ(前 5・後ろ 3)。T0+3ms の減少 4: prob = 3/8、前 = 5 − (1 − 3/8) × 4 + min(3 − 3/8 × 4, 0) = 2.5。4.5 − 2.5 = 2 → 2。
- **期待(正解の関数が入力から計算した値)**: `filled.o1` = 2.0
- **入力(全文)**: `{"product":{"symbol":"FX_BTC_JPY","venue":"bitflyer_cfd","tick":1.0,"min_qty":0.01,"qty_step":1e-08,"quote_ccy":"JPY","margin":true},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade"},"market":[{"t":1767571200000000000,"type":"book","bids":[[9995,5],[9990,5]],"asks":[[10001,5]]},{"t":1767571200002000000,"type":"book","bids":[[9995,8],[9990,5]],"asks":[[10001,5]]},{"t":1767571200003000000,"type":"book","bids":[[9995,4],[9990,5]],"asks":[[10001,5]]},{"t":1767571200010000000,"type":"trade","px":9995.0,"qty":4.5,"aggressor":"sell"}],"actions":[{"t":1767571200001000000,"op":"place","ref":"o1","side":"buy","type":"limit","qty":3.0,"px":9995.0,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null}],"fill_model":{"tier":5,"cancel_stance":"prob","prob_f":"power","prob_n":1},"latency":null,"costs":{"maker_rate":0.0,"taker_rate":0.0,"source":"場面の定義(費用を測らない場面なので 0 と明示する)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{},"end_t":1767571200050000000}`

#### c2-6-prob-power2(値の場面)— 確率型の列で f(x) = x² のとき、先行の減り方が式どおりの値になる(値)

- **何を測るか**: 確率型の列の模型の値(f(x) = x²)
- **入力(言葉で)**: c2-6-prob と同じ入力で f(x) = x²。T0+3ms の減少 4: prob = 3² / (3² + 5²) = 9/34、前 = 5 − (25/34) × 4 + min(3 − (9/34) × 4, 0) = 5 − 100/34。9995 の約定 4.5 − 前 → 自分へ min(3, 4.5 − 前)。
- **期待(正解の関数が入力から計算した値)**: `filled.o1` = 2.441176470588
- **入力(全文)**: `{"product":{"symbol":"FX_BTC_JPY","venue":"bitflyer_cfd","tick":1.0,"min_qty":0.01,"qty_step":1e-08,"quote_ccy":"JPY","margin":true},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade"},"market":[{"t":1767571200000000000,"type":"book","bids":[[9995,5],[9990,5]],"asks":[[10001,5]]},{"t":1767571200002000000,"type":"book","bids":[[9995,8],[9990,5]],"asks":[[10001,5]]},{"t":1767571200003000000,"type":"book","bids":[[9995,4],[9990,5]],"asks":[[10001,5]]},{"t":1767571200010000000,"type":"trade","px":9995.0,"qty":4.5,"aggressor":"sell"}],"actions":[{"t":1767571200001000000,"op":"place","ref":"o1","side":"buy","type":"limit","qty":3.0,"px":9995.0,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null}],"fill_model":{"tier":5,"cancel_stance":"prob","prob_f":"power","prob_n":2},"latency":null,"costs":{"maker_rate":0.0,"taker_rate":0.0,"source":"場面の定義(費用を測らない場面なので 0 と明示する)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{},"end_t":1767571200050000000}`

### C2-7 板を辿る成行・市場影響の関数(場面 4: 値 2・能力 2)

要件の語 → 場面: 板を辿る成行 → c2-7-walk, c2-7-walk-exhaust / 市場影響の関数 → c2-7-impact-sqrt, c2-7-impact-permanent, c2-5-tier6

#### c2-7-walk(値の場面)— 板の厚みを超える成行は、良い方から値位をまたいで埋まる

- **何を測るか**: 板を辿る成行
- **入力(言葉で)**: 売り 10001 x 0.5・10002 x 0.7・10005 x 5 に成行の買い 1.5 → 0.5@10001 + 0.7@10002 + 0.3@10005、加重平均 = (5000.5 + 7001.4 + 3001.5) / 1.5。
- **期待(正解の関数が入力から計算した値)**: `filled.o1` = 1.5 / `avg_px.o1` = 10002.266666666666 / `status.o1` = "filled"
- **入力(全文)**: `{"product":{"symbol":"FX_BTC_JPY","venue":"bitflyer_cfd","tick":1.0,"min_qty":0.01,"qty_step":1e-08,"quote_ccy":"JPY","margin":true},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade"},"market":[{"t":1767571200000000000,"type":"book","bids":[[9999,5]],"asks":[[10001,0.5],[10002,0.7],[10005,5]]}],"actions":[{"t":1767571200001000000,"op":"place","ref":"o1","side":"buy","type":"market","qty":1.5,"px":null,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null}],"fill_model":null,"latency":null,"costs":{"maker_rate":0.0,"taker_rate":0.0,"source":"場面の定義(費用を測らない場面なので 0 と明示する)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{},"end_t":1767571260000000000}`

#### c2-7-walk-exhaust(値の場面)— 板の全部より大きい成行は、ある分だけ埋まり残りは取り消される(規則 market_remainder = cancel)

- **何を測るか**: 板を辿る成行(板が尽きる)
- **入力(言葉で)**: 売り 10001 x 0.5・10002 x 0.7 だけに成行の買い 2 → 1.2 埋まり(加重平均 (5000.5 + 7001.4) / 1.2)、残り 0.8 は取り消し。
- **期待(正解の関数が入力から計算した値)**: `filled.o1` = 1.2 / `avg_px.o1` = 10001.583333333334 / `status.o1` = "canceled"
- **入力(全文)**: `{"product":{"symbol":"FX_BTC_JPY","venue":"bitflyer_cfd","tick":1.0,"min_qty":0.01,"qty_step":1e-08,"quote_ccy":"JPY","margin":true},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade"},"market":[{"t":1767571200000000000,"type":"book","bids":[[9999,5]],"asks":[[10001,0.5],[10002,0.7]]}],"actions":[{"t":1767571200001000000,"op":"place","ref":"o1","side":"buy","type":"market","qty":2.0,"px":null,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null}],"fill_model":null,"latency":null,"costs":{"maker_rate":0.0,"taker_rate":0.0,"source":"場面の定義(費用を測らない場面なので 0 と明示する)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{},"end_t":1767571260000000000}`

#### c2-7-impact-sqrt(能力の場面)— 平方根の市場影響の関数を渡すと、その関数どおりの値で埋まる

- **何を測るか**: 市場影響の関数(値 = 仲値 × (1 + η √(数量 / 1 日の出来高)))
- **入力(言葉で)**: 仲値 10000、η = 0.1、1 日の出来高 100、成行の買い 1 → 10000 × (1 + 0.1 × √0.01) = 10100。
- **期待(正解の関数が入力から計算した値)**: `filled.o1` = 1.0 / `avg_px.o1` = 10100.0
- **入力(全文)**: `{"product":{"symbol":"FX_BTC_JPY","venue":"bitflyer_cfd","tick":1.0,"min_qty":0.01,"qty_step":1e-08,"quote_ccy":"JPY","margin":true},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade"},"market":[{"t":1767571200000000000,"type":"book","bids":[[9999,5],[9998,5]],"asks":[[10001,5],[10002,5]]},{"t":1767571200000000000,"type":"trade","px":10000.0,"qty":0.1,"aggressor":"buy"},{"t":1767571200005000000,"type":"trade","px":10000.0,"qty":5.0,"aggressor":"buy"}],"actions":[{"t":1767571200001000000,"op":"place","ref":"o1","side":"buy","type":"market","qty":1.0,"px":null,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null}],"fill_model":{"tier":6,"impact":{"kind":"sqrt_temporary","eta":0.1,"adv":100.0,"basis":"mid"}},"latency":null,"costs":{"maker_rate":0.0,"taker_rate":0.0,"source":"場面の定義(費用を測らない場面なので 0 と明示する)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{},"end_t":1767571260000000000}`

#### c2-7-impact-permanent(能力の場面)— 恒久的な市場影響は、自分の約定の後の値を動かし、次の約定の値に効く

- **何を測るか**: 市場影響の関数(恒久的な影響 = γ × 約定した数量だけ以後の値が動く)
- **入力(言葉で)**: γ = 5 円/単位。成行の買い 1 → 最良の売り 10001。以後の値は +5 → 次の成行の買い 1 は 10006。
- **期待(正解の関数が入力から計算した値)**: `avg_px.o1` = 10001 / `avg_px.o2` = 10006.0 / `filled.o2` = 1.0
- **入力(全文)**: `{"product":{"symbol":"FX_BTC_JPY","venue":"bitflyer_cfd","tick":1.0,"min_qty":0.01,"qty_step":1e-08,"quote_ccy":"JPY","margin":true},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade"},"market":[{"t":1767571200000000000,"type":"book","bids":[[9999,5],[9998,5]],"asks":[[10001,5],[10002,5]]},{"t":1767571200000000000,"type":"trade","px":10000.0,"qty":0.1,"aggressor":"buy"},{"t":1767571200005000000,"type":"trade","px":10001.0,"qty":5.0,"aggressor":"buy"}],"actions":[{"t":1767571200001000000,"op":"place","ref":"o1","side":"buy","type":"market","qty":1.0,"px":null,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null},{"t":1767571200002000000,"op":"place","ref":"o2","side":"buy","type":"market","qty":1.0,"px":null,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null}],"fill_model":{"tier":6,"impact":{"kind":"linear_permanent","gamma":5.0,"k":0.0,"basis":"best_ask"}},"latency":null,"costs":{"maker_rate":0.0,"taker_rate":0.0,"source":"場面の定義(費用を測らない場面なので 0 と明示する)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{},"end_t":1767571260000000000}`

### C2-8 楽観側・悲観側の幅(場面 2: 値 1・能力 1)

要件の語 → 場面: 楽観側と悲観側の両方で回す → c2-8-range, c2-8-both-required / 幅で出す → c2-8-range

#### c2-8-range(値の場面)— 同じ場面を楽観側と悲観側の両方で回し、埋まる量を幅で出す

- **何を測るか**: 楽観側(段 3 = 触れたら埋まる)と悲観側(段 1 = 跨いだら埋まる)の幅
- **入力(言葉で)**: 段 5 の場面から跨ぐ約定(9994)を除いた入力。楽観側は 9995 に触れた時点で 2、悲観側は跨がないので 0 → 幅 [0, 2]。
- **期待(正解の関数が入力から計算した値)**: `range.optimistic.cum.o1@cend` = 2.0 / `range.pessimistic.cum.o1@cend` = 0.0
- **入力(全文)**: `{"product":{"symbol":"FX_BTC_JPY","venue":"bitflyer_cfd","tick":1.0,"min_qty":0.01,"qty_step":1e-08,"quote_ccy":"JPY","margin":true},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade"},"market":[{"t":1767571200000000000,"type":"book","bids":[[9995,2],[9990,5]],"asks":[[10001,5]]},{"t":1767571200000000000,"type":"trade","px":9998.0,"qty":0.1,"aggressor":"buy"},{"t":1767571201010000000,"type":"trade","px":9995.0,"qty":1.0,"aggressor":"sell"},{"t":1767571201020000000,"type":"trade","px":9995.0,"qty":1.5,"aggressor":"sell"}],"actions":[{"t":1767571200500000000,"op":"place","ref":"o1","side":"buy","type":"limit","qty":2.0,"px":9995.0,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null}],"fill_model":{"range":{"optimistic":{"tier":3,"cancel_stance":"none"},"pessimistic":{"tier":1,"cancel_stance":"none"}}},"latency":null,"costs":{"maker_rate":0.0,"taker_rate":0.0,"source":"場面の定義(費用を測らない場面なので 0 と明示する)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{"cend":1767571202500000000},"end_t":1767571203000000000}`

#### c2-8-both-required(能力の場面)— 片側だけを指定した実行は、単一の値を出さずに断る

- **何を測るか**: 楽観側と悲観側の両方を必ず回すこと(片側だけでは断る)
- **入力(言葉で)**: 対照 = 両側を指定(c2-8-range と同じ正解)。変形 = 楽観側だけを指定 → 断る(単一の値を返したら不一致)。
- **期待(正解の関数が入力から計算した値)**: `range.optimistic.cum.o1@cend` = 2.0 / `range.pessimistic.cum.o1@cend` = 0.0
- **変形**: 対照の入力との違い = fill_model.range.pessimistic を欠く。変形は断るのが正解。
- **入力(全文)**: `{"product":{"symbol":"FX_BTC_JPY","venue":"bitflyer_cfd","tick":1.0,"min_qty":0.01,"qty_step":1e-08,"quote_ccy":"JPY","margin":true},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade"},"market":[{"t":1767571200000000000,"type":"book","bids":[[9995,2],[9990,5]],"asks":[[10001,5]]},{"t":1767571200000000000,"type":"trade","px":9998.0,"qty":0.1,"aggressor":"buy"},{"t":1767571201010000000,"type":"trade","px":9995.0,"qty":1.0,"aggressor":"sell"},{"t":1767571201020000000,"type":"trade","px":9995.0,"qty":1.5,"aggressor":"sell"}],"actions":[{"t":1767571200500000000,"op":"place","ref":"o1","side":"buy","type":"limit","qty":2.0,"px":9995.0,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null}],"fill_model":{"range":{"optimistic":{"tier":3,"cancel_stance":"none"},"pessimistic":{"tier":1,"cancel_stance":"none"}}},"latency":null,"costs":{"maker_rate":0.0,"taker_rate":0.0,"source":"場面の定義(費用を測らない場面なので 0 と明示する)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{"cend":1767571202500000000},"end_t":1767571203000000000}`
- **変形の入力(全文)**: `{"product":{"symbol":"FX_BTC_JPY","venue":"bitflyer_cfd","tick":1.0,"min_qty":0.01,"qty_step":1e-08,"quote_ccy":"JPY","margin":true},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade"},"market":[{"t":1767571200000000000,"type":"book","bids":[[9995,2],[9990,5]],"asks":[[10001,5]]},{"t":1767571200000000000,"type":"trade","px":9998.0,"qty":0.1,"aggressor":"buy"},{"t":1767571201010000000,"type":"trade","px":9995.0,"qty":1.0,"aggressor":"sell"},{"t":1767571201020000000,"type":"trade","px":9995.0,"qty":1.5,"aggressor":"sell"}],"actions":[{"t":1767571200500000000,"op":"place","ref":"o1","side":"buy","type":"limit","qty":2.0,"px":9995.0,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null}],"fill_model":{"range":{"optimistic":{"tier":3,"cancel_stance":"none"}}},"latency":null,"costs":{"maker_rate":0.0,"taker_rate":0.0,"source":"場面の定義(費用を測らない場面なので 0 と明示する)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{"cend":1767571202500000000},"end_t":1767571203000000000}`

### C2-9 遅延の模型(場面 5: 値 4・能力 1)

要件の語 → 場面: 配信の遅れ → c2-9-order-feed / 発注の遅れ → c2-9-order-feed, c2-9-cancel-late / 取消の遅れ → c2-9-cancel-late, c2-9-cancel-early / 定数 → c2-9-order-feed / 実測の分布 → c2-9-empirical / 種つきの乱数 → c2-9-empirical / 受付・拒否の通知の事象 → c2-9-notice

#### c2-9-order-feed(値の場面)— 発注の遅れの分だけ遅れて取引所に届き、その時の板で埋まる。配信の遅れの分だけ遅れて戦略に見える

- **何を測るか**: 配信の遅れ(5ms)と発注の遅れ(10ms)を別々に
- **入力(言葉で)**: T0+5ms(戦略の時刻)の成行の買いは T0+15ms に届く。T0+12ms に最良の売りが 10003 に変わっている → 10003 で埋まり、約定の時刻 T0+15ms。T0+12ms の板(印 b12)は戦略に T0+17ms に見える。
- **期待(正解の関数が入力から計算した値)**: `avg_px.o1` = 10003 / `first_fill_t.o1` = 1767571200015000000 / `seen.b12` = 1767571200017000000
- **入力(全文)**: `{"product":{"symbol":"FX_BTC_JPY","venue":"bitflyer_cfd","tick":1.0,"min_qty":0.01,"qty_step":1e-08,"quote_ccy":"JPY","margin":true},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade"},"market":[{"t":1767571200000000000,"type":"book","bids":[[9999,5]],"asks":[[10001,5]]},{"t":1767571200012000000,"type":"book","bids":[[10000,5]],"asks":[[10003,5]],"label":"b12"}],"actions":[{"t":1767571200005000000,"op":"place","ref":"o1","side":"buy","type":"market","qty":1.0,"px":null,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null}],"fill_model":null,"latency":{"feed":{"kind":"constant","ns":5000000},"order":{"kind":"constant","ns":10000000},"cancel":{"kind":"constant","ns":0},"notice":{"kind":"constant","ns":0}},"costs":{"maker_rate":0.0,"taker_rate":0.0,"source":"場面の定義(費用を測らない場面なので 0 と明示する)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{},"end_t":1767571260000000000}`

#### c2-9-cancel-late(値の場面)— 取消の遅れ(20ms)は発注の遅れ(0)と別に効く

- **何を測るか**: 取消の遅れを発注の遅れと別々に
- **入力(言葉で)**: 指値 9990 の買い(T0+1ms、発注の遅れ 0)を T0+5ms に取り消す。取消は T0+25ms に届く。T0+15ms の 9985 の約定が先 → 1 埋まる(取消は間に合わない)。
- **期待(正解の関数が入力から計算した値)**: `status.o1` = "filled" / `filled.o1` = 1.0
- **入力(全文)**: `{"product":{"symbol":"FX_BTC_JPY","venue":"bitflyer_cfd","tick":1.0,"min_qty":0.01,"qty_step":1e-08,"quote_ccy":"JPY","margin":true},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade"},"market":[{"t":1767571200000000000,"type":"book","bids":[[9999,5],[9998,5]],"asks":[[10001,5],[10002,5]]},{"t":1767571200000000000,"type":"trade","px":10000.0,"qty":0.1,"aggressor":"buy"},{"t":1767571200015000000,"type":"book","bids":[],"asks":[[10001,5],[10002,5]]},{"t":1767571200015000000,"type":"trade","px":9985.0,"qty":5.0,"aggressor":"sell"}],"actions":[{"t":1767571200001000000,"op":"place","ref":"o1","side":"buy","type":"limit","qty":1.0,"px":9990.0,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null},{"t":1767571200005000000,"op":"cancel","ref":"o1"}],"fill_model":null,"latency":{"feed":{"kind":"constant","ns":0},"order":{"kind":"constant","ns":0},"cancel":{"kind":"constant","ns":20000000},"notice":{"kind":"constant","ns":0}},"costs":{"maker_rate":0.0,"taker_rate":0.0,"source":"場面の定義(費用を測らない場面なので 0 と明示する)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{},"end_t":1767571260000000000}`

#### c2-9-cancel-early(値の場面)— 取消の遅れ(5ms)は発注の遅れ(0)と別に効く

- **何を測るか**: 取消の遅れを発注の遅れと別々に
- **入力(言葉で)**: 指値 9990 の買い(T0+1ms、発注の遅れ 0)を T0+5ms に取り消す。取消は T0+10ms に届く。T0+15ms の 9985 の約定より先 → 取り消し、約定 0。
- **期待(正解の関数が入力から計算した値)**: `status.o1` = "canceled" / `filled.o1` = 0.0
- **入力(全文)**: `{"product":{"symbol":"FX_BTC_JPY","venue":"bitflyer_cfd","tick":1.0,"min_qty":0.01,"qty_step":1e-08,"quote_ccy":"JPY","margin":true},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade"},"market":[{"t":1767571200000000000,"type":"book","bids":[[9999,5],[9998,5]],"asks":[[10001,5],[10002,5]]},{"t":1767571200000000000,"type":"trade","px":10000.0,"qty":0.1,"aggressor":"buy"},{"t":1767571200015000000,"type":"book","bids":[],"asks":[[10001,5],[10002,5]]},{"t":1767571200015000000,"type":"trade","px":9985.0,"qty":5.0,"aggressor":"sell"}],"actions":[{"t":1767571200001000000,"op":"place","ref":"o1","side":"buy","type":"limit","qty":1.0,"px":9990.0,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null},{"t":1767571200005000000,"op":"cancel","ref":"o1"}],"fill_model":null,"latency":{"feed":{"kind":"constant","ns":0},"order":{"kind":"constant","ns":0},"cancel":{"kind":"constant","ns":5000000},"notice":{"kind":"constant","ns":0}},"costs":{"maker_rate":0.0,"taker_rate":0.0,"source":"場面の定義(費用を測らない場面なので 0 と明示する)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{},"end_t":1767571260000000000}`

#### c2-9-notice(値の場面)— 受付と拒否の知らせも事象で、発注の遅れ + 知らせの遅れの後に戦略に届く

- **何を測るか**: 受付・拒否の知らせの事象と遅れ
- **入力(言葉で)**: 発注の遅れ 10ms、知らせの遅れ 7ms。o1 = 交差する post-only(T0+1ms)→ 約定なしで終わった知らせ(拒否か取消)が T0+18ms。o2 = 交差しない post-only(T0+2ms)→ 受付の知らせ T0+19ms。
- **期待(正解の関数が入力から計算した値)**: `notice.o1.terminal` = 1767571200018000000 / `notice.o2.ack` = 1767571200019000000 / `status.o1` = in ["rejected", "canceled"] / `status.o2` = "open"
- **入力(全文)**: `{"product":{"symbol":"FX_BTC_JPY","venue":"bitflyer_cfd","tick":1.0,"min_qty":0.01,"qty_step":1e-08,"quote_ccy":"JPY","margin":true},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade"},"market":[{"t":1767571200000000000,"type":"book","bids":[[9999,5],[9998,5]],"asks":[[10001,5],[10002,5]]},{"t":1767571200000000000,"type":"trade","px":10000.0,"qty":0.1,"aggressor":"buy"}],"actions":[{"t":1767571200001000000,"op":"place","ref":"o1","side":"buy","type":"limit","qty":1.0,"px":10001.0,"stop_px":null,"tif":"GTC","post_only":true,"reduce_only":false,"oco":null},{"t":1767571200002000000,"op":"place","ref":"o2","side":"buy","type":"limit","qty":1.0,"px":9990.0,"stop_px":null,"tif":"GTC","post_only":true,"reduce_only":false,"oco":null}],"fill_model":null,"latency":{"feed":{"kind":"constant","ns":0},"order":{"kind":"constant","ns":10000000},"cancel":{"kind":"constant","ns":0},"notice":{"kind":"constant","ns":7000000}},"costs":{"maker_rate":0.0,"taker_rate":0.0,"source":"場面の定義(費用を測らない場面なので 0 と明示する)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{},"end_t":1767571260000000000}`

#### c2-9-empirical(能力の場面)— 実測の分布(標本の列)と種から発注の遅れを引き、引いた遅れで届く

- **何を測るか**: 実測の分布・種つきの乱数の遅れ
- **入力(言葉で)**: 発注の遅れ = 標本 {3, 7, 11}ms から種 7 で引く。3 本の成行の買いの(約定の時刻 − 出した時刻)が、どれも標本のどれかに一致する。同じ種の 2 回の実行が同じになるかは再現の欄で見る。
- **期待(正解の関数が入力から計算した値)**: `lat_in.o1` = in [3000000, 7000000, 11000000] / `lat_in.o2` = in [3000000, 7000000, 11000000] / `lat_in.o3` = in [3000000, 7000000, 11000000]
- **入力(全文)**: `{"product":{"symbol":"FX_BTC_JPY","venue":"bitflyer_cfd","tick":1.0,"min_qty":0.01,"qty_step":1e-08,"quote_ccy":"JPY","margin":true},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade"},"market":[{"t":1767571200000000000,"type":"book","bids":[[9999,5],[9998,5]],"asks":[[10001,5],[10002,5]]},{"t":1767571200000000000,"type":"trade","px":10000.0,"qty":0.1,"aggressor":"buy"}],"actions":[{"t":1767571200001000000,"op":"place","ref":"o1","side":"buy","type":"market","qty":0.1,"px":null,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null},{"t":1767571200100000000,"op":"place","ref":"o2","side":"buy","type":"market","qty":0.1,"px":null,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null},{"t":1767571200200000000,"op":"place","ref":"o3","side":"buy","type":"market","qty":0.1,"px":null,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null}],"fill_model":null,"latency":{"feed":{"kind":"constant","ns":0},"order":{"kind":"empirical","samples_ns":[3000000,7000000,11000000],"seed":7},"cancel":{"kind":"constant","ns":0},"notice":{"kind":"constant","ns":0}},"costs":{"maker_rate":0.0,"taker_rate":0.0,"source":"場面の定義(費用を測らない場面なので 0 と明示する)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{},"end_t":1767571260000000000}`

### C2-10 費用(既定値なし)(場面 8: 値 6・能力 2)

要件の語 → 場面: maker 手数料 → c2-10-maker / taker 手数料 → c2-10-taker / スプレッド → c2-10-spread / 資金調達(FX_BTC_JPY) → c2-10-funding / スワップ(FX) → c2-10-swap / JPX の手数料 → c2-10-jpx-fee / 既定値を持たない(欠けたら拒否) → c2-10-no-default / 出所の欄が必須 → c2-10-source

#### c2-10-taker(値の場面)— 成行の約定に taker の手数料が掛かる

- **何を測るか**: taker の手数料
- **入力(言葉で)**: 成行の買い 1 が 10001 で埋まる。taker の率 0.0005 → 0.0005 × 10001 × 1 = 5.0005。
- **期待(正解の関数が入力から計算した値)**: `fee.o1` = 5.0005 / `avg_px.o1` = 10001
- **入力(全文)**: `{"product":{"symbol":"FX_BTC_JPY","venue":"bitflyer_cfd","tick":1.0,"min_qty":0.01,"qty_step":1e-08,"quote_ccy":"JPY","margin":true},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade"},"market":[{"t":1767571200000000000,"type":"book","bids":[[9999,5],[9998,5]],"asks":[[10001,5],[10002,5]]},{"t":1767571200000000000,"type":"trade","px":10000.0,"qty":0.1,"aggressor":"buy"},{"t":1767571200005000000,"type":"trade","px":10001.0,"qty":1.0,"aggressor":"buy"}],"actions":[{"t":1767571200001000000,"op":"place","ref":"o1","side":"buy","type":"market","qty":1.0,"px":null,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null}],"fill_model":null,"latency":null,"costs":{"maker_rate":0.0002,"taker_rate":0.0005,"source":"場面の定義(手数料の率を測るための合成の値。取引所の料率ではない)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{},"end_t":1767571260000000000}`

#### c2-10-maker(値の場面)— 待っていた指値の約定に maker の手数料(負 = 払い戻し)が掛かる

- **何を測るか**: maker の手数料(払い戻しを含む)
- **入力(言葉で)**: 指値 9990 の買い 1 が 9985 の約定で 9990 で埋まる。maker の率 −0.0001 → −0.0001 × 9990 × 1 = −0.999(払い戻し)。
- **期待(正解の関数が入力から計算した値)**: `fee.o1` = -0.999 / `filled.o1` = 1.0
- **入力(全文)**: `{"product":{"symbol":"FX_BTC_JPY","venue":"bitflyer_cfd","tick":1.0,"min_qty":0.01,"qty_step":1e-08,"quote_ccy":"JPY","margin":true},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade"},"market":[{"t":1767571200000000000,"type":"book","bids":[[9999,5],[9998,5]],"asks":[[10001,5],[10002,5]]},{"t":1767571200000000000,"type":"trade","px":10000.0,"qty":0.1,"aggressor":"buy"},{"t":1767571200010000000,"type":"book","bids":[],"asks":[[10001,5],[10002,5]]},{"t":1767571200010000000,"type":"trade","px":9985.0,"qty":5.0,"aggressor":"sell"}],"actions":[{"t":1767571200001000000,"op":"place","ref":"o1","side":"buy","type":"limit","qty":1.0,"px":9990.0,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null}],"fill_model":null,"latency":null,"costs":{"maker_rate":-0.0001,"taker_rate":0.0005,"source":"場面の定義(合成の値)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{},"end_t":1767571260000000000}`

#### c2-10-spread(値の場面)— スプレッドの費用: 板の無い場面で、成行の買いは基準の値(直前の約定)+ スプレッドの半分で埋まる

- **何を測るか**: スプレッド(規則 market_ref = last_trade。板を渡さないので、スプレッドの模型を使わずにこの値は出ない)
- **入力(言葉で)**: 板は無く、約定は 10000 だけ。スプレッド 2 → 成行の買い 1 は 10000 + 2 / 2 = 10001。スプレッドを掛けなければ 10000 になる。
- **期待(正解の関数が入力から計算した値)**: `avg_px.o1` = 10001.0 / `filled.o1` = 1.0
- **入力(全文)**: `{"product":{"symbol":"FX_BTC_JPY","venue":"bitflyer_cfd","tick":1.0,"min_qty":0.01,"qty_step":1e-08,"quote_ccy":"JPY","margin":true},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade","market_ref":"last_trade"},"market":[{"t":1767571200000000000,"type":"trade","px":10000.0,"qty":0.1,"aggressor":"buy"},{"t":1767571200005000000,"type":"trade","px":10000.0,"qty":5.0,"aggressor":"buy"}],"actions":[{"t":1767571200001000000,"op":"place","ref":"o1","side":"buy","type":"market","qty":1.0,"px":null,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null}],"fill_model":null,"latency":null,"costs":{"maker_rate":0.0,"taker_rate":0.0,"source":"場面の定義(費用を測らない場面なので 0 と明示する)","spread":2.0},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{},"end_t":1767571260000000000}`

#### c2-10-funding(値の場面)— 資金調達の事象で、建玉 × 値 × 率が払われる(FX_BTC_JPY)

- **何を測るか**: 資金調達(FX_BTC_JPY)
- **入力(言葉で)**: 買い 1 の建玉。T0+1h の資金調達の事象(率 0.0001、値 10000)→ 買いの側が 0.0001 × 10000 × 1 = 1.0 を払う。
- **期待(正解の関数が入力から計算した値)**: `costs.funding` = 1.0
- **入力(全文)**: `{"product":{"symbol":"FX_BTC_JPY","venue":"bitflyer_cfd","tick":1.0,"min_qty":0.01,"qty_step":1e-08,"quote_ccy":"JPY","margin":true},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade"},"market":[{"t":1767571200000000000,"type":"book","bids":[[9999,5],[9998,5]],"asks":[[10001,5],[10002,5]]},{"t":1767571200000000000,"type":"trade","px":10000.0,"qty":0.1,"aggressor":"buy"},{"t":1767571200005000000,"type":"trade","px":10001.0,"qty":1.0,"aggressor":"buy"},{"t":1767574800000000000,"type":"funding","rate":0.0001,"mark":10000.0}],"actions":[{"t":1767571200001000000,"op":"place","ref":"o1","side":"buy","type":"market","qty":1.0,"px":null,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null}],"fill_model":null,"latency":null,"costs":{"maker_rate":0.0,"taker_rate":0.0,"source":"場面の定義(費用を測らない場面なので 0 と明示する)","funding":"apply_events"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{},"end_t":1767574801000000000}`

#### c2-10-swap(値の場面)— FX のスワップは、日をまたぐ時点(ロールオーバー)の建玉に付く

- **何を測るか**: スワップ(FX)
- **入力(言葉で)**: USDJPY の買い 10000。22:00 UTC のロールオーバー 1 回。買いの受け取り 0.015 円/単位/日 → 150 円の受け取り(払いは −150)。
- **期待(正解の関数が入力から計算した値)**: `costs.swap` = -150.0
- **入力(全文)**: `{"product":{"symbol":"USDJPY","venue":"fx","tick":0.001,"min_qty":1000.0,"qty_step":1.0,"quote_ccy":"JPY","margin":true},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade"},"market":[{"t":1767733200000000000,"type":"book","bids":[[150.0,1000000.0]],"asks":[[150.003,1000000.0]]},{"t":1767733200000000000,"type":"trade","px":150.001,"qty":10000.0,"aggressor":"buy"},{"t":1767733200001000000,"type":"trade","px":150.003,"qty":10000.0,"aggressor":"buy"},{"t":1767736800000000000,"type":"rollover"}],"actions":[{"t":1767733200001000000,"op":"place","ref":"o1","side":"buy","type":"market","qty":10000.0,"px":null,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null}],"fill_model":null,"latency":null,"costs":{"maker_rate":0.0,"taker_rate":0.0,"source":"場面の定義(費用を測らない場面なので 0 と明示する)","swap":{"long_credit_per_unit_per_day":0.015,"short_credit_per_unit_per_day":-0.02}},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{},"end_t":1767736801000000000}`

#### c2-10-jpx-fee(値の場面)— JPX の手数料を約定代金の段階表で渡すと、その段階の額が掛かる

- **何を測るか**: JPX の手数料(約定代金の段階表)
- **入力(言葉で)**: 段階表 ≤5万 55 / ≤10万 99 / ≤20万 115 / ≤50万 275 / それ以上 535(場面の合成の表)。1500 × 100 = 15 万 → 115。
- **期待(正解の関数が入力から計算した値)**: `fee.o1` = 115.0
- **入力(全文)**: `{"product":{"symbol":"JPX_STOCK_A","venue":"jpx_equity","tick":1.0,"min_qty":100.0,"qty_step":100.0,"quote_ccy":"JPY","margin":false},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade","sessions_jst":[["09:00","11:30"],["12:30","15:30"]],"outside_session":"queue_to_next_open","source":"東京証券取引所の立会時間(前場 9:00-11:30、後場 12:30-15:30)。一次資料の頁の確認は本役では未実施(委任文 §4 のネットワークの規則)"},"market":[{"t":1767661200000000000,"type":"book","bids":[[1499,5000]],"asks":[[1500,5000]]},{"t":1767661200000000000,"type":"trade","px":1500.0,"qty":100.0,"aggressor":"buy"},{"t":1767661260000000000,"type":"trade","px":1500.0,"qty":1000.0,"aggressor":"buy"}],"actions":[{"t":1767661230000000000,"op":"place","ref":"o1","side":"buy","type":"market","qty":100.0,"px":null,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null}],"fill_model":null,"latency":null,"costs":{"maker_rate":0.0,"taker_rate":0.0,"fee_table":[[50000,55],[100000,99],[200000,115],[500000,275],[null,535]],"source":"場面の定義(合成の段階表。証券会社の料率ではない)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{},"end_t":1767663000000000000}`

#### c2-10-no-default(能力の場面)— 費用を 1 つでも欠いた実行は、既定値で埋めずに断る

- **何を測るか**: 既定値を持たない(欠けたら拒否)
- **入力(言葉で)**: 対照 = 全部の費用を明示(c2-10-taker と同じ正解)。変形 = maker の率を欠く → 断る(既定値で走ったら不一致)。
- **期待(正解の関数が入力から計算した値)**: `fee.o1` = 5.0005 / `avg_px.o1` = 10001
- **変形**: 対照の入力との違い = costs.maker_rate を欠く。変形は断るのが正解。
- **入力(全文)**: `{"product":{"symbol":"FX_BTC_JPY","venue":"bitflyer_cfd","tick":1.0,"min_qty":0.01,"qty_step":1e-08,"quote_ccy":"JPY","margin":true},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade"},"market":[{"t":1767571200000000000,"type":"book","bids":[[9999,5],[9998,5]],"asks":[[10001,5],[10002,5]]},{"t":1767571200000000000,"type":"trade","px":10000.0,"qty":0.1,"aggressor":"buy"},{"t":1767571200005000000,"type":"trade","px":10001.0,"qty":1.0,"aggressor":"buy"}],"actions":[{"t":1767571200001000000,"op":"place","ref":"o1","side":"buy","type":"market","qty":1.0,"px":null,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null}],"fill_model":null,"latency":null,"costs":{"maker_rate":0.0002,"taker_rate":0.0005,"source":"場面の定義(手数料の率を測るための合成の値。取引所の料率ではない)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{},"end_t":1767571260000000000}`
- **変形の入力(全文)**: `{"product":{"symbol":"FX_BTC_JPY","venue":"bitflyer_cfd","tick":1.0,"min_qty":0.01,"qty_step":1e-08,"quote_ccy":"JPY","margin":true},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade"},"market":[{"t":1767571200000000000,"type":"book","bids":[[9999,5],[9998,5]],"asks":[[10001,5],[10002,5]]},{"t":1767571200000000000,"type":"trade","px":10000.0,"qty":0.1,"aggressor":"buy"},{"t":1767571200005000000,"type":"trade","px":10001.0,"qty":1.0,"aggressor":"buy"}],"actions":[{"t":1767571200001000000,"op":"place","ref":"o1","side":"buy","type":"market","qty":1.0,"px":null,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null}],"fill_model":null,"latency":null,"costs":{"taker_rate":0.0005,"source":"場面の定義(手数料の率を測るための合成の値。取引所の料率ではない)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{},"end_t":1767571260000000000}`

#### c2-10-source(能力の場面)— 費用に出所の欄が無い実行は断る

- **何を測るか**: 出所の欄が必須
- **入力(言葉で)**: 対照 = 出所つき(c2-10-taker と同じ正解)。変形 = 出所の欄を欠く → 断る。
- **期待(正解の関数が入力から計算した値)**: `fee.o1` = 5.0005 / `avg_px.o1` = 10001
- **変形**: 対照の入力との違い = costs.source を欠く。変形は断るのが正解。
- **入力(全文)**: `{"product":{"symbol":"FX_BTC_JPY","venue":"bitflyer_cfd","tick":1.0,"min_qty":0.01,"qty_step":1e-08,"quote_ccy":"JPY","margin":true},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade"},"market":[{"t":1767571200000000000,"type":"book","bids":[[9999,5],[9998,5]],"asks":[[10001,5],[10002,5]]},{"t":1767571200000000000,"type":"trade","px":10000.0,"qty":0.1,"aggressor":"buy"},{"t":1767571200005000000,"type":"trade","px":10001.0,"qty":1.0,"aggressor":"buy"}],"actions":[{"t":1767571200001000000,"op":"place","ref":"o1","side":"buy","type":"market","qty":1.0,"px":null,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null}],"fill_model":null,"latency":null,"costs":{"maker_rate":0.0002,"taker_rate":0.0005,"source":"場面の定義(手数料の率を測るための合成の値。取引所の料率ではない)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{},"end_t":1767571260000000000}`
- **変形の入力(全文)**: `{"product":{"symbol":"FX_BTC_JPY","venue":"bitflyer_cfd","tick":1.0,"min_qty":0.01,"qty_step":1e-08,"quote_ccy":"JPY","margin":true},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade"},"market":[{"t":1767571200000000000,"type":"book","bids":[[9999,5],[9998,5]],"asks":[[10001,5],[10002,5]]},{"t":1767571200000000000,"type":"trade","px":10000.0,"qty":0.1,"aggressor":"buy"},{"t":1767571200005000000,"type":"trade","px":10001.0,"qty":1.0,"aggressor":"buy"}],"actions":[{"t":1767571200001000000,"op":"place","ref":"o1","side":"buy","type":"market","qty":1.0,"px":null,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null}],"fill_model":null,"latency":null,"costs":{"maker_rate":0.0002,"taker_rate":0.0005},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{},"end_t":1767571260000000000}`

### C2-11 口座と会計(場面 8: 値 8・能力 0)

要件の語 → 場面: 円建て → c2-11-jpy / 証拠金・レバレッジ → c2-11-margin / 強制決済 → c2-11-liquidation / 建玉の時間(露出の時計) → c2-11-exposure / 脚ごとの費用 → c2-11-legs / 実現/評価損益 → c2-11-pnl / 分割/併合の建玉反映 → c2-11-split, c2-11-reverse-split

#### c2-11-pnl(値の場面)— 実現の損益と評価の損益を円で出す

- **何を測るか**: 実現と評価の損益(値 = 最後の約定、規則 mark = last_trade)
- **入力(言葉で)**: 買い 1 @10001、売り 0.4 @10101 → 実現 (10101 − 10001) × 0.4 = 40。残り 0.6、最後の約定 10051 → 評価 (10051 − 10001) × 0.6 = 30。
- **期待(正解の関数が入力から計算した値)**: `account.realized` = 40.0 / `account.position` = 0.6 / `account.unrealized` = 30.0
- **入力(全文)**: `{"product":{"symbol":"FX_BTC_JPY","venue":"bitflyer_cfd","tick":1.0,"min_qty":0.01,"qty_step":1e-08,"quote_ccy":"JPY","margin":true},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade"},"market":[{"t":1767571200000000000,"type":"book","bids":[[9999,5],[9998,5]],"asks":[[10001,5],[10002,5]]},{"t":1767571200000000000,"type":"trade","px":10000.0,"qty":0.1,"aggressor":"buy"},{"t":1767571200002000000,"type":"trade","px":10001.0,"qty":1.0,"aggressor":"buy"},{"t":1767571200005000000,"type":"book","bids":[[10101,5]],"asks":[[10103,5]]},{"t":1767571200011000000,"type":"trade","px":10101.0,"qty":1.0,"aggressor":"sell"},{"t":1767571200020000000,"type":"book","bids":[],"asks":[[10103,5]]},{"t":1767571200020000000,"type":"trade","px":10051.0,"qty":0.1,"aggressor":"sell"}],"actions":[{"t":1767571200001000000,"op":"place","ref":"o1","side":"buy","type":"market","qty":1.0,"px":null,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null},{"t":1767571200010000000,"op":"place","ref":"o2","side":"sell","type":"market","qty":0.4,"px":null,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null}],"fill_model":null,"latency":null,"costs":{"maker_rate":0.0,"taker_rate":0.0,"source":"場面の定義(費用を測らない場面なので 0 と明示する)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{},"end_t":1767571260000000000}`

#### c2-11-margin(値の場面)— 証拠金 × レバレッジを超える建玉の注文は拒否される

- **何を測るか**: 証拠金・レバレッジ
- **入力(言葉で)**: 証拠金 1000 円、レバレッジ 2 → 建玉の上限 2000 円。o1 = 買い 0.3 × 10001 = 3000.3 > 2000 → 拒否。o2 = 買い 0.1 × 10001 = 1000.1(対照)→ 埋まる。
- **期待(正解の関数が入力から計算した値)**: `status.o1` = "rejected" / `filled.o1` = 0.0 / `filled.o2` = 0.1
- **入力(全文)**: `{"product":{"symbol":"FX_BTC_JPY","venue":"bitflyer_cfd","tick":1.0,"min_qty":0.01,"qty_step":1e-08,"quote_ccy":"JPY","margin":true},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade"},"market":[{"t":1767571200000000000,"type":"book","bids":[[9999,5],[9998,5]],"asks":[[10001,5],[10002,5]]},{"t":1767571200000000000,"type":"trade","px":10000.0,"qty":0.1,"aggressor":"buy"},{"t":1767571200005000000,"type":"trade","px":10001.0,"qty":1.0,"aggressor":"buy"}],"actions":[{"t":1767571200001000000,"op":"place","ref":"o1","side":"buy","type":"market","qty":0.3,"px":null,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null},{"t":1767571200002000000,"op":"place","ref":"o2","side":"buy","type":"market","qty":0.1,"px":null,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null}],"fill_model":null,"latency":null,"costs":{"maker_rate":0.0,"taker_rate":0.0,"source":"場面の定義(費用を測らない場面なので 0 と明示する)"},"account":{"currency":"JPY","cash":1000.0,"leverage":2.0},"inject":[],"checkpoints":{},"end_t":1767571260000000000}`

#### c2-11-liquidation(値の場面)— 証拠金維持率が下限を割った時点の値で強制決済される

- **何を測るか**: 強制決済
- **入力(言葉で)**: 証拠金 1000、レバレッジ 2、維持率の下限 0.5。買い 0.19 @10001。維持率 = (1000 + (値 − 10001) × 0.19) / (値 × 0.19 / 2)。9000 → 0.947、7000 → 0.646、6000 → 0.421 < 0.5 → 6000 の時点(T0+3s)で決済、実現 (6000 − 10001) × 0.19、建玉 0。
- **期待(正解の関数が入力から計算した値)**: `account.liquidated_t` = 1767571203000000000 / `account.position` = 0.0 / `account.realized` = -760.19
- **入力(全文)**: `{"product":{"symbol":"FX_BTC_JPY","venue":"bitflyer_cfd","tick":1.0,"min_qty":0.01,"qty_step":1e-08,"quote_ccy":"JPY","margin":true},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade"},"market":[{"t":1767571200000000000,"type":"book","bids":[[9999,5],[9998,5]],"asks":[[10001,5],[10002,5]]},{"t":1767571200000000000,"type":"trade","px":10000.0,"qty":0.1,"aggressor":"buy"},{"t":1767571200005000000,"type":"trade","px":10001.0,"qty":0.19,"aggressor":"buy"},{"t":1767571201000000000,"type":"book","bids":[],"asks":[[10001,5],[10002,5]]},{"t":1767571201000000000,"type":"trade","px":9000.0,"qty":1.0,"aggressor":"sell"},{"t":1767571202000000000,"type":"trade","px":7000.0,"qty":1.0,"aggressor":"sell"},{"t":1767571203000000000,"type":"trade","px":6000.0,"qty":1.0,"aggressor":"sell"},{"t":1767571204000000000,"type":"trade","px":6500.0,"qty":1.0,"aggressor":"buy"}],"actions":[{"t":1767571200001000000,"op":"place","ref":"o1","side":"buy","type":"market","qty":0.19,"px":null,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null}],"fill_model":null,"latency":null,"costs":{"maker_rate":0.0,"taker_rate":0.0,"source":"場面の定義(費用を測らない場面なので 0 と明示する)"},"account":{"currency":"JPY","cash":1000.0,"leverage":2.0,"maint_ratio":0.5,"liquidation_price":"mark","source":"場面の定義(合成の規則)"},"inject":[],"checkpoints":{},"end_t":1767571260000000000}`

#### c2-11-exposure(値の場面)— 建玉を持っていた時間(露出の時計)を足し合わせる

- **何を測るか**: 建玉の時間(露出の時計)
- **入力(言葉で)**: 買い 1(T0+1ms)→ 売り 1(T0+1.001s)で 1 秒、買い 1(T0+2.001s)→ 終わり(T0+5s)で 2.999 秒 → 合計 3.999 秒(遅延 0 なので約定の時刻 = 出した時刻)。
- **期待(正解の関数が入力から計算した値)**: `account.exposure_ns` = 3999000000
- **入力(全文)**: `{"product":{"symbol":"FX_BTC_JPY","venue":"bitflyer_cfd","tick":1.0,"min_qty":0.01,"qty_step":1e-08,"quote_ccy":"JPY","margin":true},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade"},"market":[{"t":1767571200000000000,"type":"book","bids":[[9999,5],[9998,5]],"asks":[[10001,5],[10002,5]]},{"t":1767571200000000000,"type":"trade","px":10000.0,"qty":0.1,"aggressor":"buy"}],"actions":[{"t":1767571200001000000,"op":"place","ref":"o1","side":"buy","type":"market","qty":1.0,"px":null,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null},{"t":1767571201001000000,"op":"place","ref":"o2","side":"sell","type":"market","qty":1.0,"px":null,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null},{"t":1767571202001000000,"op":"place","ref":"o3","side":"buy","type":"market","qty":1.0,"px":null,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null}],"fill_model":null,"latency":null,"costs":{"maker_rate":0.0,"taker_rate":0.0,"source":"場面の定義(費用を測らない場面なので 0 と明示する)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{},"end_t":1767571205000000000}`

#### c2-11-legs(値の場面)— 脚(入りと出)ごとに費用を分けて出す

- **何を測るか**: 脚ごとの費用
- **入力(言葉で)**: 入り = 指値 9990 の買い 1(maker 0.0002)→ 1.998。出 = 成行の売り 1 が 9980 で(taker 0.0005)→ 4.99。
- **期待(正解の関数が入力から計算した値)**: `fee.o1` = 1.998 / `fee.o2` = 4.99
- **入力(全文)**: `{"product":{"symbol":"FX_BTC_JPY","venue":"bitflyer_cfd","tick":1.0,"min_qty":0.01,"qty_step":1e-08,"quote_ccy":"JPY","margin":true},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade"},"market":[{"t":1767571200000000000,"type":"book","bids":[[9999,5],[9998,5]],"asks":[[10001,5],[10002,5]]},{"t":1767571200000000000,"type":"trade","px":10000.0,"qty":0.1,"aggressor":"buy"},{"t":1767571200010000000,"type":"book","bids":[],"asks":[[10001,5],[10002,5]]},{"t":1767571200010000000,"type":"trade","px":9985.0,"qty":5.0,"aggressor":"sell"},{"t":1767571200020000000,"type":"book","bids":[[9980,5]],"asks":[[9982,5]]},{"t":1767571200022000000,"type":"trade","px":9980.0,"qty":1.0,"aggressor":"sell"}],"actions":[{"t":1767571200001000000,"op":"place","ref":"o1","side":"buy","type":"limit","qty":1.0,"px":9990.0,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null},{"t":1767571200021000000,"op":"place","ref":"o2","side":"sell","type":"market","qty":1.0,"px":null,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null}],"fill_model":null,"latency":null,"costs":{"maker_rate":0.0002,"taker_rate":0.0005,"source":"場面の定義(合成の値)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{},"end_t":1767571260000000000}`

#### c2-11-split(値の場面)— 分割・併合の事象を建玉と平均取得値に反映する

- **何を測るか**: 分割・併合の建玉への反映
- **入力(言葉で)**: JPX の買い 100 株 @1500。翌日の寄りの前に比率 2.0 の事象。1 株を 2 株に分割 → 建玉 200 株、平均取得値 750。
- **期待(正解の関数が入力から計算した値)**: `account.position` = 200.0 / `account.avg_px` = 750.0
- **入力(全文)**: `{"product":{"symbol":"JPX_STOCK_A","venue":"jpx_equity","tick":1.0,"min_qty":100.0,"qty_step":100.0,"quote_ccy":"JPY","margin":false},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade","sessions_jst":[["09:00","11:30"],["12:30","15:30"]],"outside_session":"queue_to_next_open","source":"東京証券取引所の立会時間(前場 9:00-11:30、後場 12:30-15:30)。一次資料の頁の確認は本役では未実施(委任文 §4 のネットワークの規則)"},"market":[{"t":1767661200000000000,"type":"book","bids":[[1499,5000]],"asks":[[1500,5000]]},{"t":1767661200000000000,"type":"trade","px":1500.0,"qty":100.0,"aggressor":"buy"},{"t":1767661260000000000,"type":"trade","px":1500.0,"qty":1000.0,"aggressor":"buy"},{"t":1767740400000000000,"type":"corporate","action":"split","ratio":2.0}],"actions":[{"t":1767661230000000000,"op":"place","ref":"o1","side":"buy","type":"market","qty":100.0,"px":null,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null}],"fill_model":null,"latency":null,"costs":{"maker_rate":0.0,"taker_rate":0.0,"source":"場面の定義(費用を測らない場面なので 0 と明示する)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{},"end_t":1767744000000000000}`

#### c2-11-reverse-split(値の場面)— 分割・併合の事象を建玉と平均取得値に反映する

- **何を測るか**: 分割・併合の建玉への反映
- **入力(言葉で)**: JPX の買い 100 株 @1500。翌日の寄りの前に比率 0.5 の事象。2 株を 1 株に併合 → 建玉 50 株、平均取得値 3000。
- **期待(正解の関数が入力から計算した値)**: `account.position` = 50.0 / `account.avg_px` = 3000.0
- **入力(全文)**: `{"product":{"symbol":"JPX_STOCK_A","venue":"jpx_equity","tick":1.0,"min_qty":100.0,"qty_step":100.0,"quote_ccy":"JPY","margin":false},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade","sessions_jst":[["09:00","11:30"],["12:30","15:30"]],"outside_session":"queue_to_next_open","source":"東京証券取引所の立会時間(前場 9:00-11:30、後場 12:30-15:30)。一次資料の頁の確認は本役では未実施(委任文 §4 のネットワークの規則)"},"market":[{"t":1767661200000000000,"type":"book","bids":[[1499,5000]],"asks":[[1500,5000]]},{"t":1767661200000000000,"type":"trade","px":1500.0,"qty":100.0,"aggressor":"buy"},{"t":1767661260000000000,"type":"trade","px":1500.0,"qty":1000.0,"aggressor":"buy"},{"t":1767740400000000000,"type":"corporate","action":"reverse-split","ratio":0.5}],"actions":[{"t":1767661230000000000,"op":"place","ref":"o1","side":"buy","type":"market","qty":100.0,"px":null,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null}],"fill_model":null,"latency":null,"costs":{"maker_rate":0.0,"taker_rate":0.0,"source":"場面の定義(費用を測らない場面なので 0 と明示する)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{},"end_t":1767744000000000000}`

#### c2-11-jpy(値の場面)— 円以外で値が付く商品の損益を、決済の時点の為替で円に直す

- **何を測るか**: 円建て
- **入力(言葉で)**: EURUSD の買い 10000 @1.1000、売り 10000 @1.1010 → 10 ドル。決済の時点の USDJPY 150.0 → 1500 円。
- **期待(正解の関数が入力から計算した値)**: `account.realized_jpy` = 1499.999999999835
- **入力(全文)**: `{"product":{"symbol":"EURUSD","venue":"fx","tick":1e-05,"min_qty":1000.0,"qty_step":1.0,"quote_ccy":"USD","margin":true},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade"},"market":[{"t":1767733200000000000,"type":"book","bids":[[1.0999,1000000.0]],"asks":[[1.1,1000000.0]]},{"t":1767733200000000000,"type":"fx_rate","pair":"USDJPY","px":150.0},{"t":1767733200002000000,"type":"trade","px":1.1,"qty":10000.0,"aggressor":"buy"},{"t":1767733200005000000,"type":"book","bids":[[1.101,1000000.0]],"asks":[[1.1011,1000000.0]]},{"t":1767733200011000000,"type":"trade","px":1.101,"qty":10000.0,"aggressor":"sell"}],"actions":[{"t":1767733200001000000,"op":"place","ref":"o1","side":"buy","type":"market","qty":10000.0,"px":null,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null},{"t":1767733200010000000,"op":"place","ref":"o2","side":"sell","type":"market","qty":10000.0,"px":null,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null}],"fill_model":null,"latency":null,"costs":{"maker_rate":0.0,"taker_rate":0.0,"source":"場面の定義(費用を測らない場面なので 0 と明示する)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{},"end_t":1767733260000000000}`

### C2-12 JPX データ待ちの扱い(場面 2: 値 1・能力 1)

要件の語 → 場面: データ待ちの明示(足で代用しない) → c2-12-jpx-wait / 足の段は JPX でも使える → c2-12-jpx-bar-value

#### c2-12-jpx-bar-value(値の場面)— JPX の 1 分足だけの場面で、足の段(段 2)の指値は足の値どおりに埋まる(データ待ちになるのは板・ティックの段だけ)

- **何を測るか**: JPX の足での約定の値(段 2。出した足の中の安値は使わない)
- **入力(言葉で)**: 10:01:30 JST に指値 1496 の買い 100。出した足(10:01〜10:02、安値 1495)は使わない。次の足(10:02〜10:03)の安値 1494 ≤ 1496 → その足の終わり 10:03 に 1496 で 100。
- **期待(正解の関数が入力から計算した値)**: `filled.o1` = 100.0 / `avg_px.o1` = 1496.0 / `first_fill_t.o1` = 1767661380000000000
- **入力(全文)**: `{"product":{"symbol":"JPX_STOCK_A","venue":"jpx_equity","tick":1.0,"min_qty":100.0,"qty_step":100.0,"quote_ccy":"JPY","margin":false},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade","sessions_jst":[["09:00","11:30"],["12:30","15:30"]],"outside_session":"queue_to_next_open","source":"東京証券取引所の立会時間(前場 9:00-11:30、後場 12:30-15:30)。一次資料の頁の確認は本役では未実施(委任文 §4 のネットワークの規則)"},"market":[{"t":1767661260000000000,"type":"bar","span_ns":60000000000,"o":1500.0,"h":1502.0,"l":1497.0,"c":1500.0,"v":10000.0},{"t":1767661320000000000,"type":"bar","span_ns":60000000000,"o":1499.0,"h":1500.0,"l":1495.0,"c":1497.0,"v":8000.0},{"t":1767661380000000000,"type":"bar","span_ns":60000000000,"o":1498.0,"h":1499.0,"l":1494.0,"c":1495.0,"v":9000.0},{"t":1767661440000000000,"type":"bar","span_ns":60000000000,"o":1495.0,"h":1497.0,"l":1493.0,"c":1496.0,"v":7000.0}],"actions":[{"t":1767661290000000000,"op":"place","ref":"o1","side":"buy","type":"limit","qty":100.0,"px":1496.0,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null}],"fill_model":{"tier":2},"latency":null,"costs":{"maker_rate":0.0,"taker_rate":0.0,"source":"場面の定義(費用を測らない場面なので 0 と明示する)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{},"end_t":1767661500000000000}`

#### c2-12-jpx-wait(能力の場面)— JPX の板・ティックが無いまま列の模型(段 5)を求めると、足で代用せずに断る(データ待ち)

- **何を測るか**: JPX のデータ待ちの扱い
- **入力(言葉で)**: 対照 = 暗号資産の板と約定で段 5(c2-5-tier5 と同じ正解)。変形 = JPX の 1 分足だけで段 5 を求める → 断る(足で埋めたら不一致)。
- **期待(正解の関数が入力から計算した値)**: `cum.o1@c1` = 0.0 / `cum.o1@c2` = 0.5 / `cum.o1@c3` = 2.0 / `cum.o1@cend` = 2.0 / `first_fill_t.o1` = 1767571201020000000
- **変形**: 対照の入力との違い = actions が [{"t": 1767661290000000000, "op": "place", "ref": "o1", "side": "buy", "type": "limit", "qty": 100.0, "px": 1496.0, "sto・checkpoints.c1 を欠く・checkpoints.c2 を欠く・checkpoints.c3 を欠く・checkpoints.cend を欠く・end_t が 1767661500000000000・fill_model.bar_ns を欠く・market が [{"t": 1767661260000000000, "type": "bar", "span_ns": 60000000000, "o": 1500.0, "h": 1502.0, "l": 1497.0, "c": 1500.0, "・product.margin が false・product.min_qty が 100.0・product.qty_step が 100.0・product.symbol が "JPX_STOCK_A"・product.venue が "jpx_equity"・rules.outside_session を足す・rules.sessions_jst を足す・rules.source を足す。変形は断るのが正解。
- **入力(全文)**: `{"product":{"symbol":"FX_BTC_JPY","venue":"bitflyer_cfd","tick":1.0,"min_qty":0.01,"qty_step":1e-08,"quote_ccy":"JPY","margin":true},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade"},"market":[{"t":1767571200000000000,"type":"book","bids":[[9995,2],[9990,5]],"asks":[[10001,5]]},{"t":1767571200000000000,"type":"trade","px":9998.0,"qty":0.1,"aggressor":"buy"},{"t":1767571201010000000,"type":"trade","px":9995.0,"qty":1.0,"aggressor":"sell"},{"t":1767571201020000000,"type":"trade","px":9995.0,"qty":1.5,"aggressor":"sell"},{"t":1767571201030000000,"type":"book","bids":[[9990,5]],"asks":[[10001,5]]},{"t":1767571201030000000,"type":"trade","px":9994.0,"qty":2.0,"aggressor":"sell"}],"actions":[{"t":1767571200500000000,"op":"place","ref":"o1","side":"buy","type":"limit","qty":2.0,"px":9995.0,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null}],"fill_model":{"tier":5,"cancel_stance":"none","bar_ns":1000000000},"latency":null,"costs":{"maker_rate":0.0,"taker_rate":0.0,"source":"場面の定義(費用を測らない場面なので 0 と明示する)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{"c1":1767571201015000000,"c2":1767571201025000000,"c3":1767571201035000000,"cend":1767571202500000000},"end_t":1767571203000000000}`
- **変形の入力(全文)**: `{"product":{"symbol":"JPX_STOCK_A","venue":"jpx_equity","tick":1.0,"min_qty":100.0,"qty_step":100.0,"quote_ccy":"JPY","margin":false},"rules":{"off_tick":"reject","below_min_qty":"reject","post_only":"reject_if_crossing","market_remainder":"cancel","mark":"last_trade","sessions_jst":[["09:00","11:30"],["12:30","15:30"]],"outside_session":"queue_to_next_open","source":"東京証券取引所の立会時間(前場 9:00-11:30、後場 12:30-15:30)。一次資料の頁の確認は本役では未実施(委任文 §4 のネットワークの規則)"},"market":[{"t":1767661260000000000,"type":"bar","span_ns":60000000000,"o":1500.0,"h":1502.0,"l":1497.0,"c":1500.0,"v":10000.0},{"t":1767661320000000000,"type":"bar","span_ns":60000000000,"o":1499.0,"h":1500.0,"l":1495.0,"c":1497.0,"v":8000.0},{"t":1767661380000000000,"type":"bar","span_ns":60000000000,"o":1498.0,"h":1499.0,"l":1494.0,"c":1495.0,"v":9000.0},{"t":1767661440000000000,"type":"bar","span_ns":60000000000,"o":1495.0,"h":1497.0,"l":1493.0,"c":1496.0,"v":7000.0}],"actions":[{"t":1767661290000000000,"op":"place","ref":"o1","side":"buy","type":"limit","qty":100.0,"px":1496.0,"stop_px":null,"tif":"GTC","post_only":false,"reduce_only":false,"oco":null}],"fill_model":{"tier":5,"cancel_stance":"none"},"latency":null,"costs":{"maker_rate":0.0,"taker_rate":0.0,"source":"場面の定義(費用を測らない場面なので 0 と明示する)"},"account":{"currency":"JPY","cash":100000000.0,"leverage":1.0},"inject":[],"checkpoints":{},"end_t":1767661500000000000}`

## 5. 場面にしなかった要件の語(理由つき。批評家が見る)

| 観点 | 語 | 理由 |
|---|---|---|
| C2-5 | 段(既定)= そのまま使ったときの段 | 要件の行(REQUIREMENTS §2 C2-5)は候補の道具の性質として段(既定)を挙げる。新実装に既定の約定の模型を持たせるべきか・持たせないべきかは §2 の行(委任文 §2 の項目 2「段 0〜6 を全部選べる」)に無く、正解を決めると要件を足すことになる。場面にできない観点として批評家が見る。 |
| C2-6 | 取消の時点で繰り上がる立場と、印を付けて通り過ぎる立場の区別 | 取消の時点で繰り上がる立場と、印を付けて通り過ぎる立場は、どの約定の列でも自分の埋まる量と時刻が同じ(先行の取消済みの分はどちらでも約定の数量を消費しない)。観測できる結果に差が出ないので、1 つの場面(c2-6-l3)で両方を測る。 |
| C2-12 | 完了の判定に混ぜずに別立てで書く | 報告の書き方(委任文 §3「完了の条件」)であり、エンジンの振る舞いではない。場面にできない観点として批評家が見る。 |

## 提出前の吟味

場面係(最初の作り、項目 2、2026-09-25)。読み直したもの: 固定した要件 `docs/DISCUSSIONS/2026-09-23_backtest_env/item_2/REQUIREMENTS.md` の C2-1〜C2-12、
委任文 §3 の場面集の規則 1〜9・「動かせない候補の検討と再現」・比較の観点、§4 の禁止と安全。数え直しのコマンドと出力は下の各項に書いた。

### 厳しい監査役・批評家なら [止める] にするもの(観点ごと)と、潰した記録

1. **規則 1(能力の場面も正解と突き合わせる)**: 能力の場面 22 件は、どれも「使ったら出るはずの値」か「断るはずの変形」を正解に持つ(対照と変形の組は c2-8-both-required・c2-10-no-default・c2-10-source・c2-12-jpx-wait)。申告だけで数える場面は無い(試験 `test_variant_scenes_differ_from_control`・`test_judge_accepts_a_faithful_observation_and_rejects_a_perturbed_one`)。
2. **規則 3(各観点に値の場面)**: 66 場面 = 値 44・能力 22(`python3 -c "import i2_scenes as S, collections; print(collections.Counter(s['kind'] for s in S.SCENES))"`)。C2-1〜C2-12 の全部に値の場面がある(試験 `test_every_viewpoint_has_a_value_scene`)。
3. **規則 4(動かせた道具は全部の場面に通す)**: 調査結果の側の対象 42 本(実物 40 本 + 再現 2 本)が 66 場面の全部を走った(試験 `test_every_survey_target_ran_every_scene`、結果は `survey_results/*.tsv`)。候補ごとの欠け = `opponents/RUNNABILITY.tsv`(66 候補: 走った 39・走らなかった 27、走らなかった理由つき。試験 `test_every_pool_candidate_has_an_install_record`)。場面ごとの欠け = 各表の「結果なし」の行の adapter の理由。時間の超過は実測を付けた(ziplime の 1 秒の足: `timeout 240` で打ち切り、`real 4m0.147s`、試しの台本 scratchpad bt/item_2/zl/i2_r1_scenekeeper_zl_probe.py)。
4. **規則 5(最も良い結果の順)**: 判定の順は i2_judge.py の分類(正解と一致 > 対応なし > 不一致 > 結果なし)。場面集の側で順を変えていない。
5. **規則 6・9(検討表)**: `python3 scripts/check_bt_considered.py tests/bt/battery/item_2/opponents/CONSIDERED.md --write` → `OK 誤り 0 件`(試験 `test_considered_passes_the_checker_and_has_no_blank_row`)。再現した候補は 2 件(57 WonderTrader の MatchEngine = `opponents/repro_57_wondertrader_match.py`、94 mote/backtest = `opponents/repro_94_mote_backtest.py`)。どちらも一次資料の行を注釈に 1 対 1 で書き、工夫を足していない(94 の成行の値だけは一次資料が決めておらず、足が約定 1 件の場面では 2 案(始値・終値)が同じ値になることを注釈に書いた)。
6. **段で外した行(C2-5・C2-7)**: 段の値は tools_catalog.tsv の列 10・11 から機械で写した(gen_considered.py の `catalog()`)。段(機構)が空欄の候補(100・109)は段で外さず、SCAN の「付けない。該当なし」の行で「持たないと確認した」にした。段 6 の動かせない候補(15・21・36・106・116・119)は、動かせた候補の機構で上位互換(15 → 33 の平方根の影響、SCAN 7189・7555 行。106・116 → 105 の線形の恒久と一時、SCAN 5222・5572・5895 行)か、約定を決める口が無い(36 = 当てはめの台本 SCAN 7191 行、119 = 測る側 SCAN 9405 行)と確かめてから外した。21 は動かせた(試しの対象で全場面「結果なし」)。
7. **C2-6 を段で外していない**: 5 つの立場に順位は無い(REQUIREMENTS §3.1)。立場を持つ動かせない候補は再現(57)か上位互換(38・97 → 104、SCAN 8820・9149・10537 行)。段 5 未満の候補は「先行注文が立たない」を段の表の行で書いた。
8. **mutant**: `mutant.py` は新実装を包み、taker の約定に maker の率で手数料を掛ける 1 か所だけを誤らせる(新実装の本体は変えない)。試験 `test_mutant_breaks_taker_fee_scenes_and_leaves_others` が c2-10-taker・c2-11-legs で落ち、c2-10-maker で変わらないことを見る。
9. **adapter が正解を計算していない**: adapter は i2_scenes の正解の関数を読まない(試験 `test_adapters_do_not_read_the_answer`)。道具の口に無いものは結果なし(adapter の理由つき)にし、道具の外で値を作らない。37 の市場影響の係数だけは場面の k(円/単位)を道具の単位(約定値の bps / 100 株)に直しており、その換算に場面の最良の売り(基準 best_ask)を使うことを adapter の注釈に書いた。
10. **§4 の禁止**: git commit / push をしていない。場面集の外(src/bot/ ほか)に触れていない(`git status --short` の item_2 以外の変更は他の役のもの: item_1・item_3・docs/AUDITOR/TRACE・mlruns/。mlruns/ は 18:13:40〜18:14:12Z にできており、この役の Qlib の実行 18:01:42Z・QTradeX の実行 18:12:54Z の後で、この役の実行の時刻とは合わない)。入れた道具に渡したのは合成の場面だけ。道具台帳 §3 の 11 件(19・41・51・58・97・111 がこの項目の候補)は導入も実行も (b) もしていない。(b) は読むだけ(15・57・63・94 と、再現の根拠の clone / raw の取得。記録 scratchpad bt/venvs/item_2/logs/i2_r1_scenekeeper_read.log)。

### 持ち越し(直していない、または確かめきれていないもの。リードに聞くこと)

- **他の役に消された venv**: 対象 3・4・10・16・18・53・87 の venv(item_0 の下)は、この役の最後の実行(17:04〜17:19Z)のあとに消えた(この役は消していない)。結果は今の場面集と今の共通部品で取ったものだが、場面集を変えると入れ直すまで走らせ直せない。
- **C2-9 に発注の遅れだけの場面が無い**: 発注の遅れだけを持つ道具(37)は c2-9 の場面を 1 つも取れない(c2-9-order-feed は配信の遅れも要る)。発注だけの場面を足すと、上の 7 対象を走らせ直せず規則 4 を破るので、この起動では足さなかった。
- **REQUIREMENTS.md の読み替え**: C2-1 の「15 BacktestingCore(SCAN 1819・1823 行)」の 2 行は候補 1 Basana の節。候補 5 は台帳の名が Lean CLI だが SCAN 6849 行は bt(bt として導入した)。候補 11 の台帳の名は python3 だが SCAN 8452 行は OctoBot。§3.1 の「52 件」の awk は列の名が 1 つずれている($9 は市場影響と約定の模型、$10 が段(機構))。§3.1 の「92 の段(既定)= 6」は台帳の列 11 では 0。
- **遅延の「持たないと確認した」の範囲**: C2-9 で、導入できなかった候補の多くは SCAN の段の表の遅延の欄(「未確認(走査 N 本。当たり 0 件)」)を根拠にした。走査の範囲は各行に書いたが、全ファイルを読んだものではない(67 lumibot は走査 1 本)。
- **上位互換の根拠の一部は結果の表**: 37 の maker・taker の手数料と口座の損益は SCAN に書き写しの行が無く、survey_results の行(c2-10-maker・c2-10-taker・c2-11-pnl が正解と一致)を根拠にした(11・13・123 の行)。
- **導入しなかった候補**: 60 Hikyuu(依存 104 件、PySide6 を含む)と 67 lumibot(依存 320 件)は `pip install --dry-run --report` で読んだところで止めた(委任文 §4 の一括の取得)。検討表は段の表の行で判断した。
