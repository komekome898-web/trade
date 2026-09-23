# 検討表 — 項目 0「核」の、動かせなかった調査結果の候補(場面係、2026-09-23 作り直し)

委任文 `docs/DATA/delegations/20260923_backtest_env_prompt.md`(指紋 `2b06c02832be`)§3「動かせない候補の検討と再現」と場面集の規則 6・9 に従う。
合意した完了の形の逐語(委任文 §3): 「**動かせなかった候補は、1 件も機構を検討せずに外さない**」「場面係は観点ごとに、動かせなかった候補の全部を `tests/bt/battery/item_<番号>/opponents/CONSIDERED.md` の検討表に 1 行ずつ載せる」。

## 読み方

- 候補の集まりは `pool.tsv`(`gen_pool.py` が機械で抜き出す。P0-1 は台帳 `docs/DATA/tools_catalog.tsv` の 7 列目 = ○、P0-2〜P0-7 は `REQUIREMENTS.md` の grep の語で `docs/DATA/SCAN_2026-09-21_tools.md`(以下 SCAN)を引いた行)。人は足し引きしていない。
- 「動かせた候補」= scratchpad の venv に入れて 32 場面を全部通せた候補。結果は `survey_results/<target>.tsv`(各場面を 2 回走らせた表)。観点の候補の集まりに入っている候補だけを「動かせた候補」の行に書く。
- 項目 0 の 7 観点には `段(機構)`/`段(既定)` の列が無い(その 2 列は項目 3 の観点専用。`REQUIREMENTS.md` 57 行)。**全観点が「段の無い観点」**で、スキップに使える理由は「上位互換」だけ(委任文 §3)。
- 「上位互換」の書き方: 候補のその観点の能力を SCAN の行から 1 つずつ挙げ、各能力に当たる場面で、動かせた候補(または再現した候補)が **正解と一致** した結果(`survey_results/…tsv` の行)を対にする。
- 道具台帳 §3 の 11 件(44・74・120・41・58・19・112・111・97・51・118)は導入も実行も (b) もしない。材料は (a) SCAN の書き写しだけ。
- 動かせた候補(と再現した候補)の、観点ごとの正解と一致の数。`python3 survey_counts.py` の出力をそのまま貼った(`survey_results/*.tsv` から数える。比較の表そのものは資料係が作る):

| 候補 | 対象 | P0-1 | P0-2 | P0-3 | P0-4 | P0-5 | P0-6 | P0-7 | 2 回の実行で同じ |
|---|---|---|---|---|---|---|---|---|---|
| 1 | opp_basana | 3/3 | 0/4 | 11/11 | 2/3 | 3/3 | 3/3 | 3/5 | 32/32 |
| 2 | opp_backtrader | 1/3 | 0/4 | 4/11 | 2/3 | 1/3 | 3/3 | 4/5 | 32/32 |
| 4 | opp_lib_pybroker | 1/3 | 2/4 | 1/11 | 1/3 | 0/3 | 1/3 | 4/5 | 32/32 |
| 6 | opp_ziplime | 1/3 | 2/4 | 1/11 | 1/3 | 0/3 | 1/3 | 4/5 | 31/32 |
| 10 | opp_fast_trade | 0/3 | 2/4 | 0/11 | 0/3 | 0/3 | 0/3 | 0/5 | 32/32 |
| 12 | opp_pybotters | 0/3 | 0/4 | 1/11 | 0/3 | 0/3 | 0/3 | 0/5 | 32/32 |
| 18 | opp_zipline_reloaded | 1/3 | 2/4 | 0/11 | 1/3 | 0/3 | 2/3 | 3/5 | 32/32 |
| 20 | opp_vnpy | 1/3 | 0/4 | 4/11 | 1/3 | 1/3 | 3/3 | 1/5 | 32/32 |
| 23 | opp_hftbacktest | 0/3 | 2/4 | 4/11 | 3/3 | 3/3 | 3/3 | 3/5 | 32/32 |
| 33 | repro_33_execution_simulator | 0/3 | 0/4 | 0/11 | 0/3 | 0/3 | 0/3 | 4/5 | 32/32 |
| 34 | opp_quantcore | 1/3 | 2/4 | 2/11 | 2/3 | 1/3 | 1/3 | 2/5 | 32/32 |
| 53 | opp_rqalpha | 0/3 | 2/4 | 3/11 | 0/3 | 0/3 | 2/3 | 4/5 | 32/32 |
| 54 | opp_finmarketpy | 0/3 | 2/4 | 0/11 | 0/3 | 0/3 | 0/3 | 0/5 | 32/32 |
| 55 | opp_backtesting | 0/3 | 2/4 | 0/11 | 1/3 | 0/3 | 0/3 | 2/5 | 32/32 |
| 62 | opp_qf_lib | 1/3 | 2/4 | 2/11 | 2/3 | 0/3 | 1/3 | 3/5 | 32/32 |
| 68 | opp_quanttrader | 1/3 | 4/4 | 3/11 | 1/3 | 0/3 | 1/3 | 0/5 | 32/32 |
| 75 | opp_freqtrade | 0/3 | 2/4 | 1/11 | 0/3 | 0/3 | 0/3 | 1/5 | 32/32 |
| 121 | opp_qstrader | 0/3 | 2/4 | 0/11 | 0/3 | 0/3 | 0/3 | 2/5 | 32/32 |
| 122 | opp_pyalgotrade | 1/3 | 0/4 | 3/11 | 1/3 | 0/3 | 3/3 | 4/5 | 32/32 |

### 観点 P0-1(事象駆動の設計)

動かせた候補: 7 件(1 Basana, 6 Ziplime, 18 zipline-reloaded, 23 hftbacktest, 53 Rqalpha, 62 qf-lib, 68 quanttrader)

この観点の能力は 3 つ(`REQUIREMENTS.md` 17 行): (能 1)型を持つ事象を流す(場面 p1-typed-events)/(能 2)事象ごとに戦略を呼ぶ(p1-one-call-per-event)/(能 3)複数の入力を渡した順ではなく時刻順に処理する(p1-merge-by-time)。**Basana は 3 場面とも正解と一致**(`survey_results/opp_basana.tsv` の p1-typed-events・p1-one-call-per-event・p1-merge-by-time)。

| 候補 | 機構(書き写しの行か一次資料の URL) | 実装(実装のコードで確かめたか) | 判断 | 理由 |
|---|---|---|---|---|
| 13 DeviaVir/zenbot | SCAN 6812 行: `eventBus.on('trade', queueTrade)` / `async.queue(...)` / `s.strategy.onPeriod.call(s.ctx, s, ...)`、6874 行(印) | 確かめた(SCAN 6812 行はコードの逐語) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を SCAN 6812 行から 1 つずつ: 約定を事象の列で受ける(`eventBus.on('trade', ...)`)= 能 1・能 3 → Basana の p1-typed-events・p1-merge-by-time が正解と一致 / 足ごとに戦略を呼ぶ(`onPeriod.call`)= 能 2 → Basana の p1-one-call-per-event が正解と一致。この候補が SCAN に持つ P0-1 の能力はこの 2 つで、どちらも Basana が含む |
| 37 ThePredictiveDev/Automated-Financial-Market-Trading-System | SCAN 4324 行: README の逐語 "Limit order book with strict price-time priority" "Order book snapshotting ... and deterministic replay"、10426 行: 価格帯ごとの `Deque[Order]` | 確かめた(10426 行は照合の機関の原典を読んだ記録) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ: 注文と板の写真という型の事象を持つ(4324 行)= 能 1 → Basana の p1-typed-events・p3-book_snapshot が正解と一致 / 記録を時刻の順に再生する(4324 行 "deterministic replay")= 能 2・能 3 → Basana の p1-one-call-per-event・p1-merge-by-time が正解と一致 |
| 41 prediction-market-backtesting | SCAN 6070 行: README の逐語 "Book replay order book deltas with trade ticks"、6106 行(印 イベント駆動・ティック) | 確かめていない(README の逐語だけ) | 再現できない(危険) | 危険: 道具台帳 §3 の 11 件で、導入・実行・(b) 一次資料の読みをしない。(a) SCAN の書き写しは README の逐語だけで、事象を流す実装のコードが無く、一次資料どおりの再現に要る材料が足りない |
| 52 QuantConnect | SCAN 7292 行(印 足・イベント駆動)、6151 行: 「足とティックの両方を入力にして、約定の模型を差し替えながらイベント駆動で回す」 | 確かめていない(README と約定の模型の文書だけ。6151 行「未確認」) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ: 足とティックを事象として受ける(6151 行)= 能 1 → Basana の p1-typed-events・p3-bar・p3-trade が正解と一致 / イベント駆動で戦略を呼ぶ(6151 行)= 能 2・能 3 → Basana の p1-one-call-per-event・p1-merge-by-time が正解と一致 |
| 57 WonderTrader | SCAN 7852 行(印 足・ティック・板の待ち行列・イベント駆動・市場影響と約定の模型。C++ の構築が要る) | 確かめていない(7852 行は印と到達の記録。P0-1 の実装の逐語は SCAN に無い) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ(7852 行の印): 足とティックを事象として受ける = 能 1 → Basana の p1-typed-events・p3-bar・p3-trade が正解と一致 / イベント駆動 = 能 2・能 3 → Basana の p1-one-call-per-event・p1-merge-by-time が正解と一致。PyPI の `wtpy` 0.9.9.3 は導入しなかった(理由は StructuredOutput の survey_not_run) |
| 58 nautilus_trader | SCAN 6061 行: README の逐語 "historical quote tick, trade tick, bar, order book, and custom data with nanosecond resolution"、"deterministic event-driven architecture" | 確かめていない(README の逐語だけ) | 再現できない(危険) | 危険: 道具台帳 §3 の 11 件で、導入・実行・(b) をしない。(a) の書き写しは README の逐語だけで、再現に要る実装のコードが無い |
| 61 barter-rs | SCAN 6302 行: `pub enum DataKind { Trade(PublicTrade), OrderBookL1(OrderBookL1), OrderBook(OrderBookEvent), Candle(Candle), Liquidation(Liquidation) }`、6305 行: `trait BacktestMarketData { ... fn stream(&self) -> ... impl Stream<Item = MarketStreamEvent<...>> }` | 確かめた(6302・6305 行は一次資料 event.rs・market_data.rs の逐語) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ: 5 つの型を 1 つの列挙で受ける(6302 行)= 能 1 → Basana の p1-typed-events と p3-mixed-one-run(6 種を 1 回の実行で)が正解と一致 / 1 本の流れを読んで戦略へ渡す(6305 行)= 能 2・能 3 → Basana の p1-one-call-per-event・p1-merge-by-time が正解と一致 |
| 63 trade-frame | SCAN 6119 行(印 ティック・イベント駆動・市場影響と約定の模型) | 確かめていない(6119 行は印の記録) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ(6119 行の印): ティックを事象として受ける = 能 1 → Basana の p1-typed-events・p3-trade が正解と一致 / イベント駆動 = 能 2・能 3 → Basana の p1-one-call-per-event・p1-merge-by-time が正解と一致 |
| 65 aat | SCAN 10429 行: 「合成の取引所は価格帯ごとの到着順の列で埋め、CSV と IEX の機関は注文の値のまま必ず埋める」(3 つの機関の原典を読んだ) | 確かめた(10429 行は原典を読んだ記録) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ: 取引所の機関が事象(注文・データ)を受けて埋める(10429 行)= 能 1・能 2 → Basana の p1-typed-events・p1-one-call-per-event が正解と一致 / 台帳 7 列目のイベント駆動 = 能 3 → Basana の p1-merge-by-time が正解と一致 |
| 69 gobacktest | SCAN 6124 行: 「README からイベント駆動と足を確定」 | 確かめていない(README だけ) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ(6124 行): 足を事象として受ける = 能 1 → Basana の p1-typed-events・p3-bar が正解と一致 / イベント駆動 = 能 2・能 3 → Basana の p1-one-call-per-event・p1-merge-by-time が正解と一致 |
| 91 braedonsaunders/homerun | SCAN 7820 行: `async for snapshot in book_source.iter_snapshots():`(足は回さない)、7858 行(印) | 確かめた(7820 行は実装の逐語) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ: 板の写真を順に回す(7820 行)= 能 1・能 2 → Basana の p3-book_snapshot・p1-one-call-per-event が正解と一致 / 事象の順序で処理する(7820 行、1 つの流れ)= 能 3 → Basana の p1-merge-by-time が正解と一致(複数の流れを時刻で合わせる点で Basana が上) |
| 123 carlos8f/zenbot | SCAN 7298 行: 「123 番が本家で、13 番はその分岐」、6812 行: 13 番は本家と同じ 4 つの性質(`eventBus.on('trade', ...)`・`onPeriod.call` ほか) | 確かめた(6812 行はコードの逐語) | スキップ: 明らかに弱い(上位互換) | 上位互換: 13 番と同じ(6812 行が本家と同じ性質と書く): 約定を事象で受ける = 能 1・能 3 → Basana の p1-typed-events・p1-merge-by-time が正解と一致 / 足ごとに戦略を呼ぶ = 能 2 → Basana の p1-one-call-per-event が正解と一致 |

### 観点 P0-2(時刻の表現: UTC の int64 ナノ秒)

動かせた候補: 1 件(34 SLMolenaar/QuantCore)

この観点の能力(`REQUIREMENTS.md` 18 行): ISO(UTC・時差つき)をナノ秒の整数に直す(p2-iso-utc・p2-iso-offset)/ 事象の時刻をナノ秒のまま保つ(p2-event-time-exact)/ 1 ns 違いを区別する(p2-one-ns-apart)。**68 quanttrader は 4 場面とも正解と一致**(`survey_results/opp_quanttrader.tsv`。この観点の候補の集まりには入っていないが、動かせた候補として全場面を通した)。34 QuantCore はナノ秒の 2 場面が正解と一致(`survey_results/opp_quantcore.tsv`)。

| 候補 | 機構(書き写しの行か一次資料の URL) | 実装(実装のコードで確かめたか) | 判断 | 理由 |
|---|---|---|---|---|
| 44 lo2cin4 | SCAN 5889 行: 契約の逐語 `"time_standard": {"const": "UTC"}` と `"precision": {"const": "nano...`(bar-time-contract-v1.schema.json) | 確かめていない(契約のスキーマだけ) | 再現できない(危険) | 危険: 道具台帳 §3 の 11 件で、導入・実行・(b) をしない。(a) の書き写しはスキーマの定数だけで、時刻を保持・変換する実装のコードが無い |
| 58 nautilus_trader | SCAN 6061 行: README の逐語 "... with nanosecond resolution" | 確かめていない(README だけ) | 再現できない(危険) | 危険: 道具台帳 §3 の 11 件。(a) は README の逐語だけで実装のコードが無い |
| 102 3yit/Limit-Order-Book-Simulator | SCAN 4882 行: 説明の逐語 "C++20 limit order book simulator ... microsecond latency, and Python bindings" | 確かめていない(説明文だけ。「未着手」) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ(4882 行): マイクロ秒の単位の時間(遅延)を扱う → 68 quanttrader の p2-event-time-exact・p2-one-ns-apart(ナノ秒をそのまま保つ・1 ns を区別する)が正解と一致で、マイクロ秒より細かい。ISO の読みは 4882 行に無い(quanttrader は p2-iso-utc・p2-iso-offset も正解と一致) |

### 観点 P0-3(8 種の事象の型)

動かせた候補: 10 件(1 Basana, 2 Backtrader, 4 PyBroker, 6 Ziplime, 10 fast-trade, 12 pybotters, 18 zipline-reloaded, 23 hftbacktest, 34 SLMolenaar/QuantCore, 121 mhallsmoore/qstrader)

この観点の能力(`REQUIREMENTS.md` 19 行): 約定・板の写真・板の差分・足・資金調達・清算・時計・注文の受付/拒否/約定の通知を型として受ける(場面 p3-trade・p3-book_snapshot・p3-book_delta・p3-bar・p3-funding・p3-liquidation・p3-mixed-one-run・p3-clock-timer・p3-notice-accepted・p3-notice-rejected・p3-notice-filled)。**Basana は 11 場面とも正解と一致**(`survey_results/opp_basana.tsv`)。

| 候補 | 機構(書き写しの行か一次資料の URL) | 実装(実装のコードで確かめたか) | 判断 | 理由 |
|---|---|---|---|---|
| 11 OctoBot | SCAN 4140 行: 「`.data` は SQLite で `description` と `ohlcv` の 2 つの表に書けばよい」「当方の約定・清算をそのまま渡す口は無く、足に直してから入れる」。導入した配布物 octobot_trading 2.1.1 の `octobot_trading/enums.py` 485 行 `LIQUIDATIONS = 'liquidations'`・490 行 `FUNDING = 'funding'`(事象の通り道の名前) | 確かめた(SCAN 4140 行は実測。enums.py は導入した配布物の原文) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ: 足(ohlcv)を受ける(4140 行)→ Basana の p3-bar が正解と一致 / 清算・資金調達の通り道の名前がある(enums.py 485・490 行。検証に渡す口は 4140 行で無い)→ Basana の p3-liquidation・p3-funding が正解と一致。OctoBot は導入できたが検証は動かせなかった(理由は survey_not_run) |
| 16 Luczinsritter/event_driven_backtesting_engine | SCAN 3297 行: 「データ源は yfinance だけで、板も清算も持たない」 | 確かめた(実測の記録 `docs/DATA/probes/20260922_tools_1_run9.log:68`) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ(3297 行): 足だけを受ける → Basana の p3-bar が正解と一致。板・清算は 3297 行が「持たない」と書く |
| 40 OpenMarket | SCAN 5694 行: 場の本文の逐語 "Real-time liquidation maps and heatmaps" "track CVD, funding or open interest" "backtest over history"、4111 行: 「資金調達率・清算・不利な価格での約定を含む模擬」と主張、5771 行 | 確かめていない(場の宣伝文だけ。登録はしない) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ: 清算(5694 行)→ Basana の p3-liquidation が正解と一致 / 資金調達(5694 行)→ Basana の p3-funding が正解と一致 / 値動きのティック(5694 行 "watch values tick live")→ Basana の p3-trade が正解と一致 / 足(チャート上の検証)→ Basana の p3-bar が正解と一致 |
| 41 prediction-market-backtesting | SCAN 6070 行: "Book replay order book deltas with trade ticks"、4112 行: 「清算・資金調達の無い場の検証」 | 確かめていない(README だけ) | 再現できない(危険) | 危険: 道具台帳 §3 の 11 件で、導入・実行・(b) をしない。(a) は README の逐語だけで、板の差分を事象にする実装のコードが無い |
| 57 WonderTrader | SCAN 7852 行(印 足・ティック・板の待ち行列)、7858 行(91 番の行で 57 番に触れる) | 確かめていない(印と到達の記録だけ) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ(7852 行の印): 足 → Basana の p3-bar / ティック → Basana の p3-trade / 板(待ち行列)→ Basana の p3-book_snapshot・p3-book_delta。どれも正解と一致 |
| 58 nautilus_trader | SCAN 6150 行・6107 行(41 番の上流として)、6061 行: "quote tick, trade tick, bar, order book, and custom data" | 確かめていない(README だけ) | 再現できない(危険) | 危険: 道具台帳 §3 の 11 件。(a) は README の逐語だけで実装のコードが無い |
| 61 barter-rs | SCAN 6302 行: `pub enum DataKind { Trade(PublicTrade), OrderBookL1(OrderBookL1), OrderBook(OrderBookEvent), Candle(Candle), Liquidation(Liquidation) }`、6305・6422・6653 行 | 確かめた(6302 行は一次資料 `barter-data/src/event.rs` の逐語) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ(6302 行): Trade → Basana の p3-trade / OrderBookL1 と OrderBook(板の写真と更新)→ Basana の p3-book_snapshot・p3-book_delta / Candle → Basana の p3-bar / Liquidation → Basana の p3-liquidation / 5 つを 1 つの流れで(6305 行)→ Basana の p3-mixed-one-run。どれも正解と一致(Basana は資金調達・時計・通知も一致) |
| 91 braedonsaunders/homerun | SCAN 7820 行: `async for snapshot in book_source.iter_snapshots():`、7804 行(book_replay.py の在処)、7818 行 | 確かめた(7820・7818 行は実装の逐語) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ: 板の写真を回す(7820 行)→ Basana の p3-book_snapshot が正解と一致。足は回さない(7820 行) |
| 103 IsaacCheng9/order-book-simulator | SCAN 5512 行: 「板の差分(deltas)を持つ。試験の名前に `test_order_book_deltas.py`…」、5611 行 | 確かめた(実測の記録 `docs/DATA/probes/20260922_tools_1_run17.log:282`) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ: 板の差分(5512 行)→ Basana の p3-book_delta が正解と一致 / 板(5611 行)→ Basana の p3-book_snapshot が正解と一致 |

### 観点 P0-4(戦略が見られるのは受け取れた時刻 ≤ 今の事象だけ)

動かせた候補: 1 件(62 qf-lib)

動かせなかった候補 0 件: この観点の候補の集まりは 62 qf-lib の 1 件だけで、それは動かせた。候補の集まりを出したコマンド `grep -n "先読み\|未来の情報\|将来の情報\|データスヌーピング\|data snooping\|peek" docs/DATA/SCAN_2026-09-21_tools.md`(`REQUIREMENTS.md` 95 行。行を候補番号へ写す規則は `gen_pool.py`、結果は `pool.tsv` の P0-4 の行)。

### 観点 P0-5(同時刻の事象の決定的な並び)

動かせた候補: 5 件(23 hftbacktest, 55 backtesting.py, 75 Freqtrade, 121 mhallsmoore/qstrader, 122 gbeced/pyalgotrade)

この観点の能力(`REQUIREMENTS.md` 21 行): 同じ入力を 2 回走らせて同じ順序・結果(p5-same-time-twice)/ 同時刻の事象を、渡した順によらない決まった規則で並べる(p5-hand-over-order)/ 同じ流れの同時刻の事象を渡した順に届ける(p5-same-stream-order)。**23 hftbacktest は 3 場面とも正解と一致**(`survey_results/opp_hftbacktest.tsv`)。1 Basana も 3 場面とも正解と一致(`survey_results/opp_basana.tsv`)。

| 候補 | 機構(書き写しの行か一次資料の URL) | 実装(実装のコードで確かめたか) | 判断 | 理由 |
|---|---|---|---|---|
| 3 PySystemtrade | SCAN 3584 行: 「決定的。同じ入力で 2 回走らせた約定の表が一致し、DETERMINISTIC_TWO_RUNS_IDENTICAL=True。模擬の側に乱数は無い」 | 確かめた(実測の記録 `docs/DATA/probes/20260922_tools_1_run10.log:637`) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ(3584 行): 同じ入力の 2 回で同じ → hftbacktest の p5-same-time-twice が正解と一致(32 場面すべて「2 回の実行で同じ」)。同時刻の複数の型の並びの規則は 3584 行に無い(hftbacktest は p5-hand-over-order も一致) |
| 11 OctoBot | SCAN 4138 行: 「決定的かどうかを記録として示せない。乱数の種の旗は `--help` の全文に無い」 | 確かめていない(4138 行が「未確認」) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ: 4138 行が挙げるのは「同じ入力での打ち直し」の 1 つだけで、それも未確認 → hftbacktest の p5-same-time-twice が正解と一致。並びの規則は 4138 行に無い |
| 37 ThePredictiveDev/Automated-Financial-Market-Trading-System | SCAN 4324 行: README の逐語 "strict price-time priority" と "Order book snapshotting (interval-based or on demand) and deterministic" replay | 確かめていない(README の逐語。10426 行で照合の原典は読んだ) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ: 決定的な再生(4324 行)→ hftbacktest の p5-same-time-twice が正解と一致 / 値段と時刻の優先 = 時刻の順に処理する規則(4324 行)→ hftbacktest の p5-hand-over-order・p5-same-stream-order が正解と一致 |
| 44 lo2cin4 | SCAN 5890 行: 契約の不変条件の逐語 `"same_timestamp_lifecycle_order_is_data_derived_signal_order_fill"`、5942 行 | 確かめていない(契約のスキーマだけ) | 再現できない(危険) | 危険: 道具台帳 §3 の 11 件で、導入・実行・(b) をしない。(a) の書き写しは不変条件の名前だけで、並べる実装のコードが無い |
| 58 nautilus_trader | SCAN 6061 行: "deterministic event-driven architecture" | 確かめていない(README だけ) | 再現できない(危険) | 危険: 道具台帳 §3 の 11 件。(a) は README の逐語だけで実装のコードが無い |
| 70 PineForge | SCAN 4653 行: 説明 "runs deterministic offline backtests on user-provided OHLCV data"、7974 行: 「足の内側に価格の道筋を引いて交差の時刻で順番を作る」 | 確かめた(7974 行は実装の原典に到達した記録) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ: 決定的な再生(4653 行)→ hftbacktest の p5-same-time-twice が正解と一致 / 足の中の事象を、計算した交差の時刻という決まった規則で並べる(7974 行)→ hftbacktest の p5-hand-over-order(渡した順によらない決まった並び)が正解と一致 |
| 98 mihircoding/limitOrderBook | SCAN 5117 行: 「到着の順序で並べる。時刻の引数を取らない」、9011 行: `class LatencyModel:` と `self._rng = np.random.default_rng(self.seed)`(種を取るので決定的) | 確かめた(5117 行は実測、9011 行は一次資料 `src/latency.py` の逐語) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ: 到着の順に並べる(5117 行)→ hftbacktest の p5-same-stream-order が正解と一致 / 種を固定して 2 回で同じ(9011 行)→ hftbacktest の p5-same-time-twice が正解と一致 |
| 99 NickGardi/orderbooksim | SCAN 5161 行: 「`timestamp` を明示すれば決定的。既定は現在時刻」 | 確かめた(実測の記録 `docs/DATA/probes/20260922_tools_1_run16.log:334`) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ(5161 行): 時刻を渡せば 2 回で同じ → hftbacktest の p5-same-time-twice が正解と一致(hftbacktest は時刻を必ずデータから取る) |
| 101 akurkar07/OrderBook | SCAN 5418 行: 「時間優先は決定的。ただし `timestamp` が実時計なので、再現には並べる順序に頼る」、4881・5415・5427 行 | 確かめた(実測の記録 `docs/DATA/probes/20260922_tools_1_run17.log:843`) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ: 並べた順による時間優先(5418 行)→ hftbacktest の p5-same-stream-order が正解と一致 / 決定的な試験(4881・5415 行)→ hftbacktest の p5-same-time-twice が正解と一致 |
| 104 jxm35/LimitOrderBook-MatchingEngine | SCAN 5547 行: 「待ち行列の順位は決定的。実時計は順位に効かない」 | 確かめた(実測の記録 `docs/DATA/probes/20260922_tools_1_run17.log:1399`) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ(5547 行): 順位が決定的で実時計に依らない → hftbacktest の p5-same-time-twice・p5-same-stream-order が正解と一致 |
| 105 DaniyalMlk/slippage | SCAN 5204 行: 「乱数を使わない関数を呼んだ範囲では決定的」 | 確かめた(実測の記録 `docs/DATA/probes/20260922_tools_1_run16.log:272`) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ(5204 行): 同じ入力で同じ → hftbacktest の p5-same-time-twice が正解と一致 |
| 120 wbt | SCAN 5874 行: README の逐語 "dt: bar end timestamp" と "equity-curve PnL is a deterministic function of weight changes and bar returns" | 確かめていない(README だけ) | 再現できない(危険) | 危険: 道具台帳 §3 の 11 件で、導入・実行・(b) をしない。(a) は README の逐語だけで実装のコードが無い |

### 観点 P0-6(戦略の API: 事象ごとの呼び出し・発注・取消)

動かせた候補: 2 件(1 Basana, 23 hftbacktest)

この観点の能力(`REQUIREMENTS.md` 22 行): 戦略から発注と取消を呼び、未決の注文の数が変わる(p6-place-then-cancel)/ 取消の成立が戦略に届く(p6-cancel-notice)/ 約定を戦略が読める(p6-fill-seen-by-strategy)/ 事象ごとに戦略を呼ぶ(P0-1 の p1-one-call-per-event)。**Basana は 3 場面とも正解と一致**(`survey_results/opp_basana.tsv`。p1-one-call-per-event と P0-3 の通知 3 場面も一致)。

| 候補 | 機構(書き写しの行か一次資料の URL) | 実装(実装のコードで確かめたか) | 判断 | 理由 |
|---|---|---|---|---|
| 13 DeviaVir/zenbot | SCAN 6812 行: `eventBus.on('trade', queueTrade)` / `s.strategy.onPeriod.call(s.ctx, s, ...)` / `let size = Math.min(buy_order.remaining_size, trade.size)`(模擬の取引所 `extensions/exchanges/sim`) | 確かめた(6812 行はコードの逐語) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ: 足ごとに戦略を呼ぶ(`onPeriod.call`)→ Basana の p1-one-call-per-event が正解と一致 / 模擬の取引所で注文を約定で埋める(`Math.min(buy_order.remaining_size, trade.size)`)→ Basana の p6-fill-seen-by-strategy が正解と一致。取消と取消の知らせは 6812 行に無い(Basana は p6-place-then-cancel・p6-cancel-notice も一致) |
| 52 QuantConnect | SCAN 6151 行: 「足とティックの両方を入力にして、約定の模型を差し替えながらイベント駆動で回す」 | 確かめていない(6151 行「未確認」、README と約定の模型の文書だけ) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ: イベント駆動で戦略を呼ぶ(6151 行)→ Basana の p1-one-call-per-event が正解と一致 / 約定の模型で注文を埋める(6151 行)→ Basana の p6-fill-seen-by-strategy・p7-fill-model-swap が正解と一致。発注・取消の API の名前は 6151 行に無い(Basana は p6-place-then-cancel・p6-cancel-notice も一致) |
| 123 carlos8f/zenbot | SCAN 6812 行(13 番は本家 123 番と同じ 4 つの性質)、7298 行 | 確かめた(6812 行はコードの逐語) | スキップ: 明らかに弱い(上位互換) | 上位互換: 13 番と同じ(6812 行): 足ごとの戦略の呼び出し → Basana の p1-one-call-per-event / 模擬の取引所の約定 → Basana の p6-fill-seen-by-strategy。どちらも正解と一致 |

### 観点 P0-7(約定の模型・遅延の模型・費用・口座の差し込み口)

動かせた候補: 8 件(1 Basana, 4 PyBroker, 6 Ziplime, 10 fast-trade, 18 zipline-reloaded, 20 VnPy, 23 hftbacktest, 54 finmarketpy)

この観点の能力(`REQUIREMENTS.md` 23 行): 約定の模型の差し込み(p7-fill-model-swap)/ 遅延の模型の差し込み(p7-latency-model-swap)/ 費用の模型の差し込み(p7-cost-model-swap・p7-cost-zero)/ 口座の差し込み(p7-account-swap)。**4 つを 1 つの候補で全部満たした動かせた候補は無い。**約定・費用・口座は 2 Backtrader と 53 Rqalpha が正解と一致(`survey_results/opp_backtrader.tsv`・`opp_rqalpha.tsv`。どちらもこの観点の集まりの外だが動かせた候補)、遅延と費用は 23 hftbacktest が正解と一致(`survey_results/opp_hftbacktest.tsv`)。

| 候補 | 機構(書き写しの行か一次資料の URL) | 実装(実装のコードで確かめたか) | 判断 | 理由 |
|---|---|---|---|---|
| 3 PySystemtrade | SCAN 3354 行: 「段ごとに別の class として差し替えられる。会計の段に、注文と約定を別の表として出す注文模擬(systems/accounts/order_simulator)が付く」、3462 行 | 確かめた(3353-3354 行は配布物から読んだ段の構成) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ: 注文模擬(埋まり方)を段の class として差し替える(3354・3462 行)→ Backtrader の p7-fill-model-swap が正解と一致 / 会計の段を差し替える(3354 行)→ Backtrader の p7-account-swap が正解と一致。遅延の模型は 3354・3462 行に無い |
| 8 OpenTrader | SCAN 7539 行: `if (candlestick.close <= smartTrade.entryOrder.price!) {` と `filledPrice: candlestick.close,`、「差し替える模型を持たない。機構と既定が同じ」 | 確かめた(7539 行はコードの逐語) | 持たないと確認した | 7539 行: 約定の値は足の終値に直書きで、差し替える模型を持たない。遅延・費用・口座の口は SCAN の P0-7 の行(`pool.tsv`)に無い |
| 11 OctoBot | SCAN 2836 行: 「戦略を『評価器 → 戦略 → 取引の型』の 3 段に分け、それぞれを差し替え式の拡張にしている」。導入した配布物 octobot_trading 2.1.1 の `constants.py` 190 行 `CONFIG_DEFAULT_SIMULATOR_FEES = 0`(手数料は設定の値) | 確かめた(導入した配布物の octobot_trading の *.py を、語 slippage と語 latency で grep -il して当たり 0 件) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ: 手数料を設定の値で変える(constants.py 190 行)→ Backtrader の p7-cost-model-swap・p7-cost-zero が正解と一致 / 戦略の 3 段を差し替える(2836 行)は戦略の側の差し替えで、約定・遅延・費用・口座の模型ではない(滑り・遅延のコードは配布物に当たり 0 件) |
| 13 DeviaVir/zenbot | SCAN 6812 行: `c.avg_slippage_pct = process.env.ZENBOT_AVG_SLIPPAGE_PCT`(無ければ `0.045`)、6989 行: 「模擬の取引所で maker と taker の約定・滑り・手数料を入れて検証」「滑りの既定値を環境変数で差し替えられる形」 | 確かめた(6812 行はコードの逐語) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ: 滑りの率を環境変数で変える = 約定の値の変更(6812 行)→ Backtrader の p7-fill-model-swap が正解と一致 / maker・taker の手数料(6989 行)→ Backtrader の p7-cost-model-swap・p7-cost-zero が正解と一致 |
| 15 Mendl-Labs/BacktestingCore | SCAN 8806 行: 「型 1 — 機構はあるが、検証の実行経路が呼ばない … 差し替えの旗では届かず、コードを書き換えないと効かない」、9153 行: 遅延の模型 `//! Variable latency simulation with jitter, ...` も型 1、7555 行: 影響の式は実行経路が直に呼ぶので差し替えの余地が無い | 確かめた(9153 行は一次資料 `config/src/variable_latency.rs` の逐語、7555 行は実装の逐語) | 持たないと確認した | 8806・9153 行: 遅延の模型と合成の板は検証の実行経路が呼ばず、コードを書き換えないと効かない = 核を書き換えずに差し込む口が無い。7555 行: 影響の式は直に呼ばれ差し替えの余地が無い |
| 16 Luczinsritter/event_driven_backtesting_engine | SCAN 3292 行: 「get_data を差し替えるだけで当方の形の表を入れられる」 | 確かめた(実測の記録 `docs/DATA/probes/20260922_tools_1_run9.log:169`) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ: データの取り込みの口を差し替える(3292 行)→ 動かせた候補は全部、場面の合成データを自分の取り込みの口で受けて 32 場面を走った(例: Backtrader の p7-fill-model-swap・p7-account-swap が正解と一致)。約定・遅延・費用・口座の口は 3292 行に無い |
| 33 SarthakDalmia1/backtesting_execution_simulator | SCAN 7189・7255 行: `execution_price = slippage_model_->get_execution_price(` と既定の `ZeroSlippageModel`、9012 行: `Timestamp submit_time = clock_.now() + config_.latency.order_submit_latency_ns;`。一次資料 https://raw.githubusercontent.com/SarthakDalmia1/backtesting_execution_simulator/main/cpp/execution/execution_simulator.hpp(33-44 行 `set_slippage_model` / `set_cost_model` / `set_event_callback`)ほか、取得日 2026-09-23 | 確かめた(一次資料の C++ を読んだ) | 再現した | 再現のファイル `opponents/repro_33_execution_simulator.py`(一次資料の行を 1 対 1 で注釈)。32 場面を通した結果 `survey_results/repro_33_execution_simulator.tsv`: p7-fill-model-swap・p7-latency-model-swap・p7-cost-model-swap・p7-cost-zero が正解と一致、p7-account-swap は対応なし(口座を差し替える setter が無い、execution_simulator.hpp 33-44 行)。1 つの候補で約定・遅延・費用を全部持つのはこの候補だけで、動かせた候補のどれとも「上位互換」にならないので再現した |
| 35 thirupathikannan-ai/Optimal-Execution-And-Market-Impact-Simulator- | SCAN 8194 行: 「機関を持たない単体の模型」、7559 行: 「引数を与えて呼ぶ単体の模型で、差し替える既定が無い」 | 確かめた(7559 行は実装の逐語 `temporary_impact=0.01,` ほか) | 持たないと確認した | 8194・7559 行: 模擬の機関(核)を持たない単体の関数なので、核に差し込む口がそもそも無い |
| 38 microsoft/MarS | SCAN 7551 行: 「差し替える模型ではなく模擬そのもの」 | 確かめた(7551 行は実装の逐語 `max_passive_volume_ratio=0.9,` ほか) | 持たないと確認した | 7551 行: 約定は模擬そのもので、差し替える模型として外に出ていない |
| 49 GFT Backtest Software | SCAN 5732 行: 「塞いでいるのは地域でも環境でもなく登録という関門」 | 確かめていない(登録の奥で未到達) | 再現できない | (a) SCAN の書き写しは 5732 行の「登録の関門で原典に届かない」だけで機構の材料が無い。(b) 一次資料は登録の奥にあり、委任文 §4「鍵・登録・署名・発注・支払いをしない」により登録しないので読めない。(a) と (b) の両方で材料が足りない |
| 52 QuantConnect | SCAN 6151 行: 「約定の模型を差し替えながらイベント駆動で回す」「約定の模型を差し替え可能な部品として外に出していること」 | 確かめていない(6151 行「未確認」、README と約定の模型の文書) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ(6151 行): 約定の模型の差し替え → Backtrader の p7-fill-model-swap が正解と一致。遅延・費用・口座は 6151 行に無い |
| 87 PyTrendFollow | SCAN 8151 行: 実装の逐語 `return (self.positions.shift(2).multiply((self.panama_prices()).diff(), axis=0).fillna(0) * self.point_values()) * self.rates()` と `slippage_multiplier = .5`、7871 行: 「注文の物が無い。滑りは『その日の値動きの半分』で、これも定率」、8010 行 | 確かめた(8151・7871 行は一次資料 `trading/accountcurve.py` の逐語、7802 行が在処) | 持たないと確認した | 8151・7871 行: 損益は建玉の差分と値動きの掛け算で、滑りは定数 `slippage_multiplier = .5` の直書き。注文の物が無いので、約定・遅延・費用・口座を差し込む口が無い(8010 行も「模型の差し替え口が無い」) |
| 98 mihircoding/limitOrderBook | SCAN 7550 行: 「照合そのものが値段と時刻の優先なので、差し替える余地がなく」、9011 行: `class LatencyModel:` と `send(sent_at, participant, action) -> runs at sent_at + latency(participant)` | 確かめた(9011 行は一次資料 `src/latency.py` の逐語) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ: 遅延の模型(9011 行)→ hftbacktest の p7-latency-model-swap が正解と一致。照合は差し替えの余地が無い(7550 行)。費用・口座の口は SCAN の P0-7 の行に無い |
| 107 sigc | SCAN 8806 行: 「型 1 — 機構はあるが、検証の実行経路が呼ばない」に 107 `sigc`(費用と影響の模型) | 確かめた(8806 行は呼び出しの当たりを数えた記録) | 持たないと確認した | 8806 行: 費用と影響の模型は検証の実行経路から呼ばれず、コードを書き換えないと効かない = 核を書き換えずに差し込む口が無い |

<!-- 集計ここから -->

## 集計(`scripts/check_bt_considered.py --write` が書く。手で直さない)

| 観点 | 動かせた | 動かせない(検討表の行) | 動かせない割合 | 再現した | 持たないと確認した | スキップ | 再現できない |
|---|---|---|---|---|---|---|---|
| 観点 P0-1(事象駆動の設計) | 7 | 12 | 63% | 0 | 0 | 10 | 2 |
| 観点 P0-2(時刻の表現: UTC の int64 ナノ秒) | 1 | 3 | 75% | 0 | 0 | 1 | 2 |
| 観点 P0-3(8 種の事象の型) | 10 | 9 | 47% | 0 | 0 | 7 | 2 |
| 観点 P0-4(戦略が見られるのは受け取れた時刻 ≤ 今の事象だけ) | 1 | 0 | 0% | 0 | 0 | 0 | 0 |
| 観点 P0-5(同時刻の事象の決定的な並び) | 5 | 12 | 71% | 0 | 0 | 9 | 3 |
| 観点 P0-6(戦略の API: 事象ごとの呼び出し・発注・取消) | 2 | 3 | 60% | 0 | 0 | 3 | 0 |
| 観点 P0-7(約定の模型・遅延の模型・費用・口座の差し込み口) | 8 | 14 | 64% | 1 | 6 | 6 | 1 |
| 計(観点ごとの延べ) | 34 | 53 | 61% | 1 | 6 | 36 | 10 |

再現もできなかった候補(圧倒の判定では「その候補とは比べていない」と候補名を付けて報告する):

- 観点 P0-1(事象駆動の設計): 41 prediction-market-backtesting
- 観点 P0-1(事象駆動の設計): 58 nautilus_trader
- 観点 P0-2(時刻の表現: UTC の int64 ナノ秒): 44 lo2cin4
- 観点 P0-2(時刻の表現: UTC の int64 ナノ秒): 58 nautilus_trader
- 観点 P0-3(8 種の事象の型): 41 prediction-market-backtesting
- 観点 P0-3(8 種の事象の型): 58 nautilus_trader
- 観点 P0-5(同時刻の事象の決定的な並び): 44 lo2cin4
- 観点 P0-5(同時刻の事象の決定的な並び): 58 nautilus_trader
- 観点 P0-5(同時刻の事象の決定的な並び): 120 wbt
- 観点 P0-7(約定の模型・遅延の模型・費用・口座の差し込み口): 49 GFT Backtest Software

<!-- 集計ここまで -->
