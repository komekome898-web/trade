# 検討表 — 項目 0「核」の、動かせなかった調査結果の候補(場面係。2026-09-24 第 r4-1 回の直しで作り直し)

委任文 `docs/DATA/delegations/20260923_backtest_env_prompt.md`(指紋 `362bf666dfac`。`sha256sum … | cut -c1-12` で確かめ、全 158 行を読んだ)§3「調査結果の側の選び方」「動かせない候補の検討と再現」と場面集の規則 6・9 に従う。前の版は指紋 `2b06c02832be` の委任文で作っていた(批評 i0-r3-11)。その版から今の版までの差分(`git diff 8b5dd73 ebbaf34 -- docs/DATA/delegations/20260923_backtest_env_prompt.md`)で、この表に効くのは「場面集の側の指摘を周の途中で場面係が直す」段落と L-422(表が左右同一なら同等)で、検討の規則(規則 6・9、「動かせない候補の検討と再現」の段落)の中身は変わっていない。
合意した完了の形の逐語(委任文 §3): 「**動かせなかった候補は、1 件も機構を検討せずに外さない**」「場面係は観点ごとに、動かせなかった候補の全部を `tests/bt/battery/item_<番号>/opponents/CONSIDERED.md` の検討表に 1 行ずつ載せる」。

## 読み方

- 候補の集まりは `pool.tsv`(`gen_pool.py` が機械で抜き出す。P0-1 は台帳 `docs/DATA/tools_catalog.tsv` の 7 列目 = ○、P0-2〜P0-7 は `REQUIREMENTS.md` の grep の語で `docs/DATA/SCAN_2026-09-21_tools.md`(以下 SCAN)を引いた行)。人は足し引きしていない。行を候補の番号に写す規則は `gen_pool.py` の冒頭に書いた。第 r4-1 回に規則を 3 つ足した(SCAN の道具ごとの段落の頭の名前 / 番号つきの「知見」の表の続きの行 / 見出しの名前の書き方の違い)。それでも写せない行のうち道具を指す 2 行は `gen_pool.py` の `READ_BY_HAND` に根拠の行つきで置いた。**写せなかった行は全部、この文書の最後の節で 1 行ずつ検討した**(批評 i0-r3-07)。この直しで P0-4 に 16、P0-7 に 63・123 が加わった。
- 「動かせた候補」= scratchpad の venv に入れて 32 場面を全部通せた候補。結果は `survey_results/<target>.tsv`(各場面を 2 回走らせた表。第 r4-1 回の場面集で走らせ直した)。観点の候補の集まりに入っている候補だけを「動かせた候補」の行に書く。
- この周に動かせなかった道具が 2 つある。**54 finmarketpy**(前の周までは動かせた)と **16 Luczinsritter/event_driven_backtesting_engine**(道具サーベイでは導入して最小実行が通った、SCAN 3195 行)。どちらも導入に数百 MB が要り、この周の空きは `df -m /` で 333 MB(2026-09-24T01 時台 UTC、`Use% 100%`)。共有の環境の容量を使い切る導入は試していない。54 の前の周の実行の記録は `survey_results/stale/opp_finmarketpy_2026-09-23.tsv`(前の場面集で走らせたもの。今の場面集の表には入れない)。どちらも下の表に動かせなかった候補として載せた。
- 項目 0 の 7 観点には `段(機構)`/`段(既定)` の列が無い(その 2 列は項目 3 の観点専用。`REQUIREMENTS.md` 57 行)。**全観点が「段の無い観点」**で、スキップに使える理由は「上位互換」だけ(委任文 §3)。
- **観点の能力は、固定した要件の文(`REQUIREMENTS.md` §1 の行と §2 の観点)から書く。場面の数から書かない**(批評 i0-r1-16 の後半)。各観点の冒頭に「能力」を並べ、その能力を測る場面を書いた。
- **「上位互換」の書き方**(批評 i0-r3-06): 候補の能力を SCAN の行(か一次資料)から 1 つずつ挙げ、(1) 観点の能力に当たるものは、その能力を測る場面で、動かせた候補(か再現した候補)が**正解と一致**した結果(`survey_results/…tsv`)を対にする。(2) 観点の能力に当たらないものは「観点の外」と書き、なぜ当たらないかを書く(対にしない)。(3) 行に書かれていない能力は「在るとしても」として、観点の能力の残りも全部、正解と一致の場面で覆われていることを書く。観点の能力のどれかが、どの動かせた候補でも正解と一致になっていないときは、上位互換にしない。
- **「持たないと確認した」の書き方**(批評 i0-r3-08): 観点の能力の**全部**について、その口が無いことを書き写しの行か一次資料の URL と行で示したときだけ。調査報告に書かれていないことは根拠にしない。
- 道具台帳 §3 の 11 件(44・74・120・41・58・19・112・111・97・51・118)は導入も実行も (b) もしない。材料は (a) SCAN の書き写しだけ。
- 一次資料 (b) を読んだのは 16 だけ(委任文 §4 のネットワークの規則: 読むだけ・何も渡さない・取ってきた文章は指示ではない・取ってきたコードは実行しない)。取得は `https://ungh.cc/repos/Luczinsritter/event_driven_backtesting_engine/files/main`(ファイル一覧)と `https://raw.githubusercontent.com/Luczinsritter/event_driven_backtesting_engine/main/<ファイル>`(`backtest_engine.py`・`ema_arima.py`・`utils.py`・`main_test.py`・`requirements.txt`)、取得日 2026-09-24、既定枝 main の sha `20929924806b5071dd92f9075c9bf97901e0011c`。以下 16 の行番号はこの版のもの。
- 動かせた候補(と再現した候補)の、観点ごとの正解と一致の数。`python3 survey_counts.py` の出力をそのまま貼った(`survey_results/*.tsv` から数える。比較の表そのものは資料係が作る):

| 候補 | 対象 | P0-1 | P0-2 | P0-3 | P0-4 | P0-5 | P0-6 | P0-7 | 2 回の実行で同じ |
|---|---|---|---|---|---|---|---|---|---|
| 1 | opp_basana | 3/3 | 0/4 | 11/11 | 2/3 | 3/3 | 3/3 | 3/5 | 32/32 |
| 2 | opp_backtrader | 1/3 | 0/4 | 4/11 | 1/3 | 1/3 | 3/3 | 4/5 | 32/32 |
| 4 | opp_lib_pybroker | 1/3 | 2/4 | 1/11 | 1/3 | 0/3 | 1/3 | 4/5 | 32/32 |
| 6 | opp_ziplime | 1/3 | 2/4 | 1/11 | 1/3 | 0/3 | 1/3 | 4/5 | 31/32 |
| 10 | opp_fast_trade | 0/3 | 2/4 | 0/11 | 0/3 | 0/3 | 0/3 | 0/5 | 32/32 |
| 12 | opp_pybotters | 0/3 | 0/4 | 1/11 | 0/3 | 0/3 | 0/3 | 0/5 | 32/32 |
| 18 | opp_zipline_reloaded | 1/3 | 2/4 | 0/11 | 0/3 | 0/3 | 2/3 | 3/5 | 32/32 |
| 20 | opp_vnpy | 1/3 | 0/4 | 4/11 | 1/3 | 1/3 | 3/3 | 1/5 | 32/32 |
| 23 | opp_hftbacktest | 0/3 | 2/4 | 4/11 | 3/3 | 1/3 | 3/3 | 3/5 | 32/32 |
| 33 | repro_33_execution_simulator | 0/3 | 0/4 | 0/11 | 0/3 | 0/3 | 0/3 | 4/5 | 32/32 |
| 34 | opp_quantcore | 1/3 | 2/4 | 3/11 | 2/3 | 1/3 | 1/3 | 1/5 | 32/32 |
| 53 | opp_rqalpha | 0/3 | 2/4 | 3/11 | 0/3 | 0/3 | 2/3 | 4/5 | 32/32 |
| 55 | opp_backtesting | 0/3 | 2/4 | 0/11 | 1/3 | 0/3 | 0/3 | 2/5 | 32/32 |
| 62 | opp_qf_lib | 1/3 | 2/4 | 2/11 | 1/3 | 0/3 | 1/3 | 3/5 | 32/32 |
| 68 | opp_quanttrader | 1/3 | 4/4 | 3/11 | 1/3 | 0/3 | 1/3 | 0/5 | 32/32 |
| 75 | opp_freqtrade | 0/3 | 2/4 | 1/11 | 0/3 | 0/3 | 0/3 | 0/5 | 32/32 |
| 121 | opp_qstrader | 0/3 | 2/4 | 0/11 | 0/3 | 0/3 | 0/3 | 1/5 | 32/32 |
| 122 | opp_pyalgotrade | 1/3 | 0/4 | 3/11 | 1/3 | 0/3 | 3/3 | 4/5 | 32/32 |

### 観点 P0-1(事象駆動の設計)

動かせた候補: 7 件(1 Basana, 6 Ziplime, 18 zipline-reloaded, 23 hftbacktest, 53 Rqalpha, 62 qf-lib, 68 quanttrader)

この観点の能力(`REQUIREMENTS.md` §2 P0-1「型を持つ事象をイベントバス/イベントループで流す構造…投入順ではなく時刻順に処理されるか」): (能 1)型を持つ事象を流す → 場面 p1-typed-events / (能 2)事象ごとに戦略を呼ぶ(ループで流す)→ p1-one-call-per-event / (能 3)渡した順ではなく時刻順に処理する → p1-merge-by-time。**1 Basana は 3 場面とも正解と一致**(`survey_results/opp_basana.tsv`)。

| 候補 | 機構(書き写しの行か一次資料の URL) | 実装(実装のコードで確かめたか) | 判断 | 理由 |
|---|---|---|---|---|
| 13 DeviaVir/zenbot | SCAN 6812 行: `eventBus.on('trade', queueTrade)` / `var tradeProcessingQueue = async.queue(...)` / `s.strategy.onPeriod.call(s.ctx, s, ...)`、6874 行(印) | 確かめた(SCAN 6812 行はコードの逐語) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ(6812 行): 約定を型つきの事象として事象の口で受ける(`eventBus.on('trade', ...)`)= 能 1 → Basana の p1-typed-events が正解と一致 / 期間ごとに戦略を呼ぶ(`onPeriod.call`)= 能 2 → Basana の p1-one-call-per-event が正解と一致 / 約定を列(`async.queue`)で順に処理する = 能 3 → Basana の p1-merge-by-time が正解と一致。観点の外: `Math.min(buy_order.remaining_size, trade.size)`(約定の量の決め方 = 約定の模型、項目 3) |
| 37 ThePredictiveDev/Automated-Financial-Market-Trading-System | SCAN 4324 行: README の逐語 "Limit order book with strict price-time priority" "Order book snapshotting ... and deterministic replay"、10426 行: 価格帯ごとの `Deque[Order]` | 確かめた(10426 行は照合の機関の原典を読んだ記録) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ: 板の写真を事象として持つ(4324 行)= 能 1 → Basana の p1-typed-events が正解と一致 / 記録を再生して処理する(4324 行 "deterministic replay")= 能 2・能 3 → Basana の p1-one-call-per-event・p1-merge-by-time が正解と一致。観点の外: 値段と時刻の優先の照合(4324・10426 行。板の待ち行列 = 項目 3) |
| 41 prediction-market-backtesting | SCAN 6070 行: README の逐語 "Book replay order book deltas with trade ticks"、6106 行(印 イベント駆動・ティック) | 確かめていない(README の逐語だけ) | 再現できない(危険) | 危険: 道具台帳 §3 の 11 件で、導入・実行・(b) 一次資料の読みをしない。(a) SCAN の書き写しは README の逐語だけで、事象を流す実装のコードが無く、一次資料どおりの再現に要る材料が足りない |
| 52 QuantConnect | SCAN 7292 行(印 足・イベント駆動)、6151 行: 「足とティックの両方を入力にして、約定の模型を差し替えながらイベント駆動で回す」 | 確かめていない(README と約定の模型の文書だけ。6151 行「未確認」) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ: 足とティックを事象として受ける(6151 行)= 能 1 → Basana の p1-typed-events が正解と一致 / イベント駆動で回す(6151 行)= 能 2・能 3 → Basana の p1-one-call-per-event・p1-merge-by-time が正解と一致。観点の外: 約定の模型の差し替え(P0-7 の能力。P0-7 の表で扱う) |
| 57 WonderTrader | SCAN 7852 行(印 足・ティック・板の待ち行列・イベント駆動・市場影響と約定の模型。C++ の構築が要る) | 確かめていない(7852 行は印と到達の記録。P0-1 の実装の逐語は SCAN に無い) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ(7852 行の印): 足とティックを事象として受ける = 能 1 → Basana の p1-typed-events が正解と一致 / イベント駆動 = 能 2・能 3 → Basana の p1-one-call-per-event・p1-merge-by-time が正解と一致。観点の外: 板の待ち行列・市場影響(項目 3)。PyPI の `wtpy` 0.9.9.3 は導入しなかった(理由は StructuredOutput の survey_not_run) |
| 58 nautilus_trader | SCAN 6061 行: README の逐語 "historical quote tick, trade tick, bar, order book, and custom data with nanosecond resolution"、"deterministic event-driven architecture" | 確かめていない(README の逐語だけ) | 再現できない(危険) | 危険: 道具台帳 §3 の 11 件で、導入・実行・(b) をしない。(a) の書き写しは README の逐語だけで、再現に要る実装のコードが無い |
| 61 barter-rs | SCAN 6302 行: `pub enum DataKind { Trade(PublicTrade), OrderBookL1(OrderBookL1), OrderBook(OrderBookEvent), Candle(Candle), Liquidation(Liquidation) }`、6305 行: `trait BacktestMarketData { ... fn stream(&self) -> ... impl Stream<Item = MarketStreamEvent<...>> }` | 確かめた(6302・6305 行は一次資料 event.rs・market_data.rs の逐語) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ: 5 つの型を 1 つの列挙で受ける(6302 行)= 能 1 → Basana の p1-typed-events が正解と一致 / 1 本の流れを読んで事象ごとに渡す(6305 行)= 能 2 → Basana の p1-one-call-per-event が正解と一致 / 流れの時刻順の処理(6305 行の `Stream`)= 能 3 → Basana の p1-merge-by-time が正解と一致 |
| 63 trade-frame | SCAN 6119 行(印 ティック・イベント駆動・市場影響と約定の模型) | 確かめていない(6119 行は印の記録) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ(6119 行の印): ティックを事象として受ける = 能 1 → Basana の p1-typed-events が正解と一致 / イベント駆動 = 能 2・能 3 → Basana の p1-one-call-per-event・p1-merge-by-time が正解と一致。観点の外: 市場影響と約定の模型(項目 3) |
| 65 aat | SCAN 10429 行: 「合成の取引所は価格帯ごとの到着順の列で埋め、CSV と IEX の機関は注文の値のまま必ず埋める」(3 つの機関の原典を読んだ)、台帳 7 列目 = ○(イベント駆動) | 確かめた(10429 行は原典を読んだ記録) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ: 機関が事象(データ・注文)を受けて回る(10429 行、台帳のイベント駆動の印)= 能 1・能 2 → Basana の p1-typed-events・p1-one-call-per-event が正解と一致 / 事象の時刻順の処理(イベント駆動の印)= 能 3 → Basana の p1-merge-by-time が正解と一致。観点の外: 到着順の列で埋める・注文の値で埋める(約定の模型、項目 3) |
| 69 gobacktest | SCAN 6124 行: 「README からイベント駆動と足を確定」 | 確かめていない(README だけ) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ(6124 行): 足を事象として受ける = 能 1 → Basana の p1-typed-events が正解と一致 / イベント駆動 = 能 2・能 3 → Basana の p1-one-call-per-event・p1-merge-by-time が正解と一致 |
| 91 braedonsaunders/homerun | SCAN 7820 行: `async for snapshot in book_source.iter_snapshots():`(足は回さない)、7858 行(印) | 確かめた(7820 行は実装の逐語) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ: 板の写真を事象として順に回す(7820 行)= 能 1・能 2 → Basana の p1-typed-events・p1-one-call-per-event が正解と一致 / 1 つの流れを順に処理する(7820 行)= 能 3 → Basana の p1-merge-by-time が正解と一致(複数の流れを時刻で合わせる点で Basana が上) |
| 123 carlos8f/zenbot | SCAN 7298 行: 「123 番が本家で、13 番はその分岐」、6812 行: 13 番は本家と同じ 4 つの性質(`eventBus.on('trade', ...)`・`onPeriod.call` ほか) | 確かめた(6812 行はコードの逐語) | スキップ: 明らかに弱い(上位互換) | 上位互換: 13 番と同じ(6812 行が本家と同じ性質と書く): 約定を事象の口で受ける = 能 1 → Basana の p1-typed-events / 期間ごとに戦略を呼ぶ = 能 2 → Basana の p1-one-call-per-event / 列で順に処理 = 能 3 → Basana の p1-merge-by-time。どれも正解と一致 |

### 観点 P0-2(時刻の表現: UTC の int64 ナノ秒)

動かせた候補: 1 件(34 SLMolenaar/QuantCore)

この観点の能力(`REQUIREMENTS.md` §2 P0-2「全事象の時刻が UTC 起点の int64 ナノ秒で表現され、他の単位…が核の内部表現に混入しない」): (能 1)事象の時刻をナノ秒の整数のまま保つ → 場面 p2-event-time-exact・p2-one-ns-apart / (能 2)UTC に直した int64 ナノ秒で表す → p2-iso-utc・p2-iso-offset。**68 quanttrader は 4 場面とも正解と一致**(`survey_results/opp_quanttrader.tsv`。この観点の候補の集まりには入っていないが、動かせた候補として全場面を通した)。

| 候補 | 機構(書き写しの行か一次資料の URL) | 実装(実装のコードで確かめたか) | 判断 | 理由 |
|---|---|---|---|---|
| 44 lo2cin4 | SCAN 5889 行: 契約の逐語 `"time_standard": {"const": "UTC"}` と `"precision": {"const": "nano...`(bar-time-contract-v1.schema.json) | 確かめていない(契約のスキーマだけ) | 再現できない(危険) | 危険: 道具台帳 §3 の 11 件で、導入・実行・(b) をしない。(a) の書き写しはスキーマの定数だけで、時刻を保持・変換する実装のコードが無い |
| 58 nautilus_trader | SCAN 6061 行: README の逐語 "... with nanosecond resolution"、247 行(PyPI の説明の逐語。Rust の核と型の安全) | 確かめていない(README と PyPI の説明だけ) | 再現できない(危険) | 危険: 道具台帳 §3 の 11 件。(a) は README と説明の逐語だけで実装のコードが無い |
| 102 3yit/Limit-Order-Book-Simulator | SCAN 4882 行: 説明の逐語 "C++20 limit order book simulator ... microsecond latency, and Python bindings" | 確かめていない(説明文だけ。「未着手」) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ(4882 行): マイクロ秒の単位の時間を扱う = 能 1 → 68 quanttrader の p2-event-time-exact・p2-one-ns-apart(ナノ秒をそのまま保つ・1 ns を区別する)が正解と一致で、マイクロ秒より細かい / 能 2(UTC への変換)は 4882 行に無い。在るとしても 68 quanttrader の p2-iso-utc・p2-iso-offset が正解と一致 |

### 観点 P0-3(8 種の事象の型)

動かせた候補: 10 件(1 Basana, 2 Backtrader, 4 PyBroker, 6 Ziplime, 10 fast-trade, 12 pybotters, 18 zipline-reloaded, 23 hftbacktest, 34 SLMolenaar/QuantCore, 121 mhallsmoore/qstrader)

この観点の能力(`REQUIREMENTS.md` §1 の行「事象の型(約定・板の写真・板の差分・足・資金調達・清算・時計・注文の受付/拒否/約定の通知)」): 型ごとに 1 つ = 約定 → p3-trade / 板の写真 → p3-book_snapshot / 板の差分 → p3-book_delta / 足 → p3-bar / 資金調達 → p3-funding / 清算 → p3-liquidation / 時計 → p3-clock-timer / 注文の通知 → p3-notice-accepted・p3-notice-rejected・p3-notice-filled。6 種を 1 回の実行に混ぜる → p3-mixed-one-run。**1 Basana は 11 場面とも正解と一致**(`survey_results/opp_basana.tsv`)。

| 候補 | 機構(書き写しの行か一次資料の URL) | 実装(実装のコードで確かめたか) | 判断 | 理由 |
|---|---|---|---|---|
| 11 OctoBot | SCAN 4140 行: 「`.data` は SQLite で `description` と `ohlcv` の 2 つの表に書けばよい」「当方の約定・清算をそのまま渡す口は無く、足に直してから入れる」。導入した配布物 octobot_trading 2.1.1 の `octobot_trading/enums.py` 485 行 `LIQUIDATIONS = 'liquidations'`・490 行 `FUNDING = 'funding'`(事象の通り道の名前) | 確かめた(SCAN 4140 行は実測。enums.py は導入した配布物の原文) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ: 足(ohlcv)を受ける(4140 行)→ Basana の p3-bar が正解と一致 / 清算・資金調達の通り道の名前がある(enums.py 485・490 行。検証に渡す口は 4140 行で無い)→ 在るとしても Basana の p3-liquidation・p3-funding が正解と一致 / 行に無い型(約定・板・時計・通知)も、在るとしても Basana の p3-trade・p3-book_snapshot・p3-book_delta・p3-clock-timer・p3-notice-* が正解と一致。OctoBot は導入できたが検証は動かせなかった(理由は survey_not_run) |
| 16 Luczinsritter/event_driven_backtesting_engine | SCAN 3297 行: 「データ源は yfinance だけで、板も清算も持たない」、3372 行: 「当方に無いもの: 保有期間を時間差のまま記録に持つ点だけ。それ以外(指値・板・費用・清算)は当方の方が持っている」。一次資料 https://raw.githubusercontent.com/Luczinsritter/event_driven_backtesting_engine/main/backtest_engine.py 13-19 行(`get_data` が `raw_df[['Open', 'High', 'Low', 'Close', 'Volume']]` だけを返す)、取得日 2026-09-24 | 確かめた(一次資料のコードを読んだ) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ: 足だけを受ける(backtest_engine.py 13-19 行)→ Basana の p3-bar が正解と一致。板・清算は 3297 行が「持たない」と書き、ほかの型を受ける口は backtest_engine.py に無い(足の列の DataFrame だけ)。この周は動かせなかった(読み方の節の容量) |
| 40 OpenMarket | SCAN 5694 行: 場の本文の逐語 "Real-time liquidation maps and heatmaps" "track CVD, funding or open interest" "backtest over history"、4111 行: 「資金調達率・清算・不利な価格での約定を含む模擬」と主張、5771 行 | 確かめていない(場の宣伝文だけ。登録はしない) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ: 清算(5694 行)→ Basana の p3-liquidation が正解と一致 / 資金調達(5694 行)→ Basana の p3-funding が正解と一致 / 値動きのティック(5694 行 "watch values tick live")→ Basana の p3-trade が正解と一致 / 足(チャート上の検証)→ Basana の p3-bar が正解と一致 / 行に無い型(板・時計・通知)も在るとしても Basana の該当の場面が正解と一致 |
| 41 prediction-market-backtesting | SCAN 6070 行: "Book replay order book deltas with trade ticks"、4112 行: 「清算・資金調達の無い場の検証」 | 確かめていない(README だけ) | 再現できない(危険) | 危険: 道具台帳 §3 の 11 件で、導入・実行・(b) をしない。(a) は README の逐語だけで、板の差分を事象にする実装のコードが無い |
| 57 WonderTrader | SCAN 7852 行(印 足・ティック・板の待ち行列)、7858 行(91 番の行で 57 番に触れる) | 確かめていない(印と到達の記録だけ) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ(7852 行の印): 足 → Basana の p3-bar / ティック → Basana の p3-trade / 板(待ち行列)→ Basana の p3-book_snapshot・p3-book_delta。どれも正解と一致。行に無い型も在るとしても Basana の該当の場面が正解と一致 |
| 58 nautilus_trader | SCAN 6150 行・6107 行(41 番の上流として)、6061 行: "quote tick, trade tick, bar, order book, and custom data" | 確かめていない(README だけ) | 再現できない(危険) | 危険: 道具台帳 §3 の 11 件。(a) は README の逐語だけで実装のコードが無い |
| 61 barter-rs | SCAN 6302 行: `pub enum DataKind { Trade(PublicTrade), OrderBookL1(OrderBookL1), OrderBook(OrderBookEvent), Candle(Candle), Liquidation(Liquidation) }`、6305・6422・6653 行 | 確かめた(6302 行は一次資料 `barter-data/src/event.rs` の逐語) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ(6302 行): Trade → Basana の p3-trade / OrderBookL1 と OrderBook(板の写真と更新)→ Basana の p3-book_snapshot・p3-book_delta / Candle → Basana の p3-bar / Liquidation → Basana の p3-liquidation / 5 つを 1 つの流れで(6305 行)→ Basana の p3-mixed-one-run。どれも正解と一致(Basana は資金調達・時計・通知も一致) |
| 91 braedonsaunders/homerun | SCAN 7820 行: `async for snapshot in book_source.iter_snapshots():`、7804 行(book_replay.py の在処)、7818 行 | 確かめた(7820・7818 行は実装の逐語) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ: 板の写真を回す(7820 行)→ Basana の p3-book_snapshot が正解と一致。足は回さない(7820 行)。行に無い型も在るとしても Basana の該当の場面が正解と一致 |
| 103 IsaacCheng9/order-book-simulator | SCAN 5512 行: 「板の差分(deltas)を持つ。試験の名前に `test_order_book_deltas.py`…」、5514・5611 行 | 確かめた(実測の記録 `docs/DATA/probes/20260922_tools_1_run17.log:282`) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ: 板の差分(5512 行)→ Basana の p3-book_delta が正解と一致 / 板(5611 行)→ Basana の p3-book_snapshot が正解と一致。行に無い型も在るとしても Basana の該当の場面が正解と一致 |

### 観点 P0-4(戦略が見られるのは受け取れた時刻 ≤ 今の事象だけ)

動かせた候補: 1 件(62 qf-lib)

この観点の能力(`REQUIREMENTS.md` §2 P0-4「戦略側から未来時刻の事象を読もうとするコードが、実行時エラーか型エラーで止まるか(素通りしたら不合格)」と §1 の行「受け取れた時刻 ≤ 今」): (能 1)未来を名指す読み出しが例外で止まる → 場面 p4-future-read-attempt / (能 2)受け取れた時刻より前に見せない → p4-received-time / (能 3)今までの事象だけが見える → p4-visible-at-step。この観点の動かせた候補 62 qf-lib は、p4-future-read-attempt が不一致(5 本目の日を名指した `get_price` が 4 本目までを黙って返した、`survey_results/opp_qf_lib.tsv`)。

| 候補 | 機構(書き写しの行か一次資料の URL) | 実装(実装のコードで確かめたか) | 判断 | 理由 |
|---|---|---|---|---|
| 16 Luczinsritter/event_driven_backtesting_engine | SCAN 3166 行: 「建玉は `enter_long` / `enter_short` / `close_position` の 3 つだけで、いずれも次の足の始値で必ず約定する(`get_execution_price` が `self.data['Open'].iloc[ind_nbr + 1]` を返す)。先読みは防いでいる」。一次資料 https://raw.githubusercontent.com/Luczinsritter/event_driven_backtesting_engine/main/backtest_engine.py 10 行(`self.data = self.get_data(...)` = 全期間の表)・30-36 行(戦略は `EventBased` の子)・54-57 行(`get_date_price(self, ind_nbr)` は添字の行を返し、添字の上限を見ない)・59-63 行(先読みを避けるのは約定を次の足の始値にすることだけ)、https://raw.githubusercontent.com/Luczinsritter/event_driven_backtesting_engine/main/ema_arima.py 19-20 行(戦略は `for i in range(len(self.data) - 1):` で全期間の `self.data` の `.iloc[i]` を読む)、取得日 2026-09-24 | 確かめた(一次資料のコードを読んだ) | 持たないと確認した | 能 1: 戦略は全期間の表 `self.data`(backtest_engine.py 10 行)を持つ `EventBased` の子(30-36 行)で、`get_date_price(ind_nbr + 1)` や `self.data['Close'].iloc[i + 1]`(54-57 行、ema_arima.py 19-20 行)は未来の行を例外なしに返す = 未来の読み出しを止める口が無い / 能 2: 事象は時刻を 1 つ(表の添字)しか持たず、受け取れる時刻を持つ口が無い(backtest_engine.py 13-19 行、列は Open/High/Low/Close/Volume だけ)/ 能 3: 今までの行だけを渡す口が無い(戦略が全期間の表をそのまま読む、10 行・ema_arima.py 19-20 行)。SCAN 3166 行の「先読みは防いでいる」は約定を次の足にすることで、戦略の読み出しを止めることではない(backtest_engine.py 59-63 行の注釈 `Function used to avoid look ahead bias by taking position at the next period`) |

### 観点 P0-5(同時刻の事象の決定的な並び)

動かせた候補: 5 件(23 hftbacktest, 55 backtesting.py, 75 Freqtrade, 121 mhallsmoore/qstrader, 122 gbeced/pyalgotrade)

この観点の能力(`REQUIREMENTS.md` §1 の行「決定的な事象の順序(同時刻の並びの規則を明記)」と §2 P0-5「同時刻の複数事象に決定的な並び規則が明記され、同じ入力を 2 回実行して同じ順序・同じ結果になること」): (能 1)同時刻の複数の型の事象を、明記した規則どおりに落とさず並べる → 場面 p5-same-time-twice / (能 2)その並びがデータの中身と無関係な渡す順に左右されない → p5-hand-over-order / (能 3)1 本の入力の中の同時刻の事象は入力の順を守る → p5-same-stream-order / (能 4)同じ入力を 2 回走らせて同じ → 表の「再現」の欄(全場面を 2 回走らせる)。**1 Basana は能 1〜3 の 3 場面とも正解と一致、しかも全 32 場面で「2 回の実行で同じ」**(`survey_results/opp_basana.tsv`)。この観点の動かせた候補 23 hftbacktest は p5-same-time-twice・p5-hand-over-order が不一致(同時刻の 4 件のうち約定の 1 件だけを届けた)。

「同時刻の並び」は、核が受け取った複数の事象(型の違う入力)の並びのこと。**約定の模型が足の中や板の中で決める順(値段と時刻の優先・足の内側の道筋)は項目 3・14 の観点で、この観点の外**とした(固定した要件の P0-5 の測り方は「同時刻に複数型の事象を仕込んだ入力を作り、規則どおりの順で処理されるか」で、入力の事象の並びを見る)。

| 候補 | 機構(書き写しの行か一次資料の URL) | 実装(実装のコードで確かめたか) | 判断 | 理由 |
|---|---|---|---|---|
| 3 PySystemtrade | SCAN 3584 行: 「決定的。同じ入力で 2 回走らせた約定の表が一致し、DETERMINISTIC_TWO_RUNS_IDENTICAL=True。模擬の側に乱数は無い」、3505・3617 行(同じ実測)、3598 行: 入力は価格の系列と最適建玉の系列の 2 本 | 確かめた(実測の記録 `docs/DATA/probes/20260922_tools_1_run10.log:637`) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ: 同じ入力の 2 回で同じ(3584 行)= 能 4 → Basana の 32 場面すべて「2 回の実行で同じ」 / 同時刻の複数の型の並びの規則は 3584・3598 行に無い(入力は価格と建玉の 2 本の系列)。在るとしても能 1〜3 は Basana の p5-same-time-twice・p5-hand-over-order・p5-same-stream-order が正解と一致 |
| 11 OctoBot | SCAN 4138 行: 「決定的かどうかを記録として示せない。乱数の種の旗は `--help` の全文に無い」 | 確かめていない(4138 行が「未確認」) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ: 4138 行が挙げるのは「同じ入力での打ち直し」(能 4)の 1 つだけで、それも未確認 → Basana の 32 場面すべて「2 回の実行で同じ」 / 並びの規則は 4138 行に無い。在るとしても能 1〜3 は Basana の p5 の 3 場面が正解と一致 |
| 37 ThePredictiveDev/Automated-Financial-Market-Trading-System | SCAN 4324 行: README の逐語 "strict price-time priority" と "Order book snapshotting (interval-based or on demand) and deterministic" replay | 確かめていない(README の逐語。10426 行で照合の原典は読んだ) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ: 決定的な再生(4324 行)= 能 4 → Basana の 32 場面すべて「2 回の実行で同じ」。観点の外: "strict price-time priority"(板の中の注文の優先 = 照合の規則、項目 3。入力の同時刻の事象の並びではない)。能 1〜3 は行に無い。在るとしても Basana の p5 の 3 場面が正解と一致 |
| 44 lo2cin4 | SCAN 5890 行: 契約の不変条件の逐語 `"same_timestamp_lifecycle_order_is_data_derived_signal_order_fill"`、5942 行 | 確かめていない(契約のスキーマだけ) | 再現できない(危険) | 危険: 道具台帳 §3 の 11 件で、導入・実行・(b) をしない。(a) の書き写しは不変条件の名前だけで、並べる実装のコードが無い |
| 58 nautilus_trader | SCAN 6061 行: "deterministic event-driven architecture" | 確かめていない(README だけ) | 再現できない(危険) | 危険: 道具台帳 §3 の 11 件。(a) は README の逐語だけで実装のコードが無い |
| 70 PineForge | SCAN 4653 行: 説明 "runs deterministic offline backtests on user-provided OHLCV data"、7974 行: 「足の内側に価格の道筋を引いて交差の時刻で順番を作る」 | 確かめた(7974 行は実装の原典に到達した記録) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ: 決定的な再生(4653 行)= 能 4 → Basana の 32 場面すべて「2 回の実行で同じ」 / 入力は OHLCV の 1 本(4653 行)で、同時刻の複数の型の入力を並べる規則は行に無い。在るとしても能 1〜3 は Basana の p5 の 3 場面が正解と一致。観点の外: 足の内側の道筋から交差の時刻を作って約定の順を決める(7974 行。1 本の足の中の約定の順 = 約定の模型、項目 3・14 の「足内の TP/SL」。入力の事象の並びではない。前の版はこれを p5-hand-over-order に対にしていた = 批評 i0-r1-16・i0-r3-06) |
| 98 mihircoding/limitOrderBook | SCAN 5117 行: 「到着の順序で並べる。時刻の引数を取らない」、9011 行: `class LatencyModel:` と `self._rng = np.random.default_rng(self.seed)`、5547・9148 行 | 確かめた(5117 行は実測、9011 行は一次資料 `src/latency.py` の逐語) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ: 渡した順(到着の順)のまま処理する(5117 行)= 能 3 → Basana の p5-same-stream-order が正解と一致 / 種を固定して 2 回で同じ(9011 行)= 能 4 → Basana の 32 場面すべて「2 回の実行で同じ」。能 1・能 2(複数の型の入力の並びの規則)は行に無い。在るとしても Basana の p5-same-time-twice・p5-hand-over-order が正解と一致 |
| 99 NickGardi/orderbooksim | SCAN 5161 行: 「`timestamp` を明示すれば決定的。既定は現在時刻」 | 確かめた(実測の記録 `docs/DATA/probes/20260922_tools_1_run16.log:334`) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ(5161 行): 時刻を渡せば 2 回で同じ = 能 4 → Basana の 32 場面すべて「2 回の実行で同じ」。能 1〜3 は行に無い。在るとしても Basana の p5 の 3 場面が正解と一致 |
| 101 akurkar07/OrderBook | SCAN 5418 行: 「時間優先は決定的。ただし `timestamp` が実時計なので、再現には並べる順序に頼る」、4881・5415・5427 行 | 確かめた(実測の記録 `docs/DATA/probes/20260922_tools_1_run17.log:843`) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ: 並べた順に頼って 2 回で同じ(5418 行)= 能 3・能 4 → Basana の p5-same-stream-order が正解と一致・32 場面すべて「2 回の実行で同じ」 / 決定的な試験(4881・5415 行)= 能 4 → 同じ。観点の外: 板の中の時間優先(照合の規則、項目 3)。能 1・能 2 は行に無い。在るとしても Basana の p5-same-time-twice・p5-hand-over-order が正解と一致 |
| 104 jxm35/LimitOrderBook-MatchingEngine | SCAN 5547 行: 「待ち行列の順位は決定的。実時計は順位に効かない」 | 確かめた(実測の記録 `docs/DATA/probes/20260922_tools_1_run17.log:1399`) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ(5547 行): 実時計に依らず決定的 = 能 4 → Basana の 32 場面すべて「2 回の実行で同じ」。観点の外: 待ち行列の順位(板の中の注文の順 = 項目 3)。能 1〜3 は行に無い。在るとしても Basana の p5 の 3 場面が正解と一致 |
| 105 DaniyalMlk/slippage | SCAN 5204 行: 「乱数を使わない関数を呼んだ範囲では決定的」 | 確かめた(実測の記録 `docs/DATA/probes/20260922_tools_1_run16.log:272`) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ(5204 行): 同じ入力で同じ = 能 4 → Basana の 32 場面すべて「2 回の実行で同じ」。能 1〜3 は行に無い(滑りの関数で、事象を並べる機関を持たない)。在るとしても Basana の p5 の 3 場面が正解と一致 |
| 120 wbt | SCAN 5874 行: README の逐語 "dt: bar end timestamp" と "equity-curve PnL is a deterministic function of weight changes and bar returns" | 確かめていない(README だけ) | 再現できない(危険) | 危険: 道具台帳 §3 の 11 件で、導入・実行・(b) をしない。(a) は README の逐語だけで実装のコードが無い |

### 観点 P0-6(戦略の API: 事象ごとの呼び出し・発注・取消)

動かせた候補: 2 件(1 Basana, 23 hftbacktest)

この観点の能力(`REQUIREMENTS.md` §1 の行「戦略の API(事象ごとの呼び出し・発注・取消)」と §2 P0-6): (能 1)事象ごとに戦略を呼ぶ → 場面 p1-one-call-per-event / (能 2)戦略から発注し、その結果が戦略に返る → p6-place-then-cancel(発注の部分)・p6-fill-seen-by-strategy / (能 3)戦略から取り消し、その結果が戦略に返る → p6-place-then-cancel(取消の部分)・p6-cancel-notice。**1 Basana は 4 場面とも正解と一致**(`survey_results/opp_basana.tsv`)。

| 候補 | 機構(書き写しの行か一次資料の URL) | 実装(実装のコードで確かめたか) | 判断 | 理由 |
|---|---|---|---|---|
| 13 DeviaVir/zenbot | SCAN 6812 行: `eventBus.on('trade', queueTrade)` / `s.strategy.onPeriod.call(s.ctx, s, ...)` / `let size = Math.min(buy_order.remaining_size, trade.size)`(模擬の取引所 `extensions/exchanges/sim`) | 確かめた(6812 行はコードの逐語) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ: 期間ごとに戦略を呼ぶ(`onPeriod.call`)= 能 1 → Basana の p1-one-call-per-event が正解と一致 / 買いの注文を模擬の取引所が約定で埋める(`buy_order.remaining_size`)= 能 2 → Basana の p6-place-then-cancel・p6-fill-seen-by-strategy が正解と一致 / 取消は 6812 行に無い。在るとしても能 3 は Basana の p6-place-then-cancel・p6-cancel-notice が正解と一致。観点の外: 約定の量の決め方(`Math.min`、約定の模型) |
| 52 QuantConnect | SCAN 6151 行: 「足とティックの両方を入力にして、約定の模型を差し替えながらイベント駆動で回す」 | 確かめていない(6151 行「未確認」、README と約定の模型の文書だけ) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ: イベント駆動で戦略を呼ぶ(6151 行)= 能 1 → Basana の p1-one-call-per-event が正解と一致 / 発注・取消の API の名前は 6151 行に無い。在るとしても能 2・能 3 は Basana の p6-place-then-cancel・p6-fill-seen-by-strategy・p6-cancel-notice が正解と一致。観点の外: 約定の模型の差し替え(P0-7 の表で扱う) |
| 123 carlos8f/zenbot | SCAN 6812 行(13 番は本家 123 番と同じ 4 つの性質)、7298 行 | 確かめた(6812 行はコードの逐語) | スキップ: 明らかに弱い(上位互換) | 上位互換: 13 番と同じ(6812 行): 期間ごとの戦略の呼び出し = 能 1 → Basana の p1-one-call-per-event / 模擬の取引所で注文を埋める = 能 2 → Basana の p6-place-then-cancel・p6-fill-seen-by-strategy / 取消は行に無く、在るとしても能 3 は Basana の p6-place-then-cancel・p6-cancel-notice。どれも正解と一致 |

### 観点 P0-7(約定の模型・遅延の模型・費用・口座の差し込み口)

動かせた候補: 7 件(1 Basana, 4 PyBroker, 6 Ziplime, 10 fast-trade, 18 zipline-reloaded, 20 VnPy, 23 hftbacktest)

この観点の能力(`REQUIREMENTS.md` §1 の行「他項目が差し込む口(約定模型・遅延模型・費用・口座)」と §2 P0-7「各口にダミー実装を差し込み、核のコードを変えずに動くか」)は 4 つ: (約定)約定の模型の口 → 場面 p7-fill-model-swap / (遅延)遅延の模型の口 → p7-latency-model-swap / (費用)費用の模型の口 → p7-cost-model-swap・p7-cost-per-unit / (口座)口座の口 → p7-account-swap。**4 つを 1 つの候補で全部満たした動かせた候補は無い。**正解と一致の対(下の表で「4 つの対」と書く): 約定 → 2 Backtrader の p7-fill-model-swap / 遅延 → 23 hftbacktest の p7-latency-model-swap / 費用 → 2 Backtrader の p7-cost-model-swap・p7-cost-per-unit / 口座 → 2 Backtrader の p7-account-swap(`survey_results/opp_backtrader.tsv`・`opp_hftbacktest.tsv`。2 Backtrader はこの観点の集まりの外だが動かせた候補)。この 4 つの対で、観点の能力の全部が正解と一致の場面で覆われる。

データの取り込みの口(入力の表の形を替える)は、この観点の 4 つの口のどれでもない(項目 1 の観点)ので、「観点の外」とした(批評 i0-r3-06)。

| 候補 | 機構(書き写しの行か一次資料の URL) | 実装(実装のコードで確かめたか) | 判断 | 理由 |
|---|---|---|---|---|
| 3 PySystemtrade | SCAN 3354 行: 「段ごとに別の class として差し替えられる。会計の段に、注文と約定を別の表として出す注文模擬(systems/accounts/order_simulator)が付く」、3462 行。台帳の遅延(原文)の列: 「当たり 1 件 `# No delaying done here so we assume positions are already delayed`」 | 確かめた(3353-3354 行は配布物から読んだ段の構成) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ: 注文模擬(埋まり方)を段の class として差し替える(3354・3462 行)= 約定 → 2 Backtrader の p7-fill-model-swap が正解と一致 / 会計の段を差し替える(3354 行)= 口座 → 2 Backtrader の p7-account-swap が正解と一致 / 遅延は台帳の原文の列で「遅らせない」の注記だけ。在るとしても 23 hftbacktest の p7-latency-model-swap が正解と一致 / 費用の口は行に無い。在るとしても 2 Backtrader の p7-cost-model-swap・p7-cost-per-unit が正解と一致 |
| 8 OpenTrader | SCAN 7539 行: `if (candlestick.close <= smartTrade.entryOrder.price!) {` と `filledPrice: candlestick.close,`、「差し替える模型を持たない。機構と既定が同じ」、9402 行 | 確かめた(7539 行はコードの逐語) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ: 約定の値は足の終値に直書き(7539 行)= 約定の口は無い / 遅延・費用・口座の口は SCAN の書き写しに無い(在るかは未確認。前の版はこれを「持たない」の根拠にしていた = 批評 i0-r3-08)。在るとしても 4 つの対(遅延 → 23 hftbacktest の p7-latency-model-swap、費用 → 2 Backtrader の p7-cost-model-swap・p7-cost-per-unit、口座 → 2 Backtrader の p7-account-swap)が正解と一致 |
| 11 OctoBot | SCAN 2836 行: 「戦略を『評価器 → 戦略 → 取引の型』の 3 段に分け、それぞれを差し替え式の拡張にしている」。導入した配布物 octobot_trading 2.1.1 の `constants.py` 190 行 `CONFIG_DEFAULT_SIMULATOR_FEES = 0`(手数料は設定の値)、2712・2827 行 | 確かめた(導入した配布物の octobot_trading の *.py を、語 slippage と語 latency で grep -il して当たり 0 件) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ: 手数料を設定の値で変える(constants.py 190 行)= 費用 → 2 Backtrader の p7-cost-model-swap・p7-cost-per-unit が正解と一致 / 滑り・遅延のコードは配布物に当たり 0 件(遅延の口は無い見込み)。在るとしても 23 hftbacktest の p7-latency-model-swap が正解と一致 / 約定・口座の口は行に無い。在るとしても 2 Backtrader の p7-fill-model-swap・p7-account-swap が正解と一致。観点の外: 戦略の 3 段の差し替え(2836 行。戦略の側の差し替えで、4 つの口のどれでもない) |
| 13 DeviaVir/zenbot | SCAN 6812 行: `c.avg_slippage_pct = process.env.ZENBOT_AVG_SLIPPAGE_PCT`(無ければ `0.045`)、6989 行: 「模擬の取引所で maker と taker の約定・滑り・手数料を入れて検証」「滑りの既定値を環境変数で差し替えられる形」、8407 行(段 3 の 4 件は「事象の受け口に旗が無く、差し替えずに働く」) | 確かめた(6812 行はコードの逐語) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ: 滑りの率を環境変数で変える = 約定の値の変更(6812 行)= 約定 → 2 Backtrader の p7-fill-model-swap が正解と一致 / maker・taker の手数料(6989 行)= 費用 → 2 Backtrader の p7-cost-model-swap・p7-cost-per-unit が正解と一致 / 遅延・口座の口は行に無い。在るとしても 23 hftbacktest の p7-latency-model-swap・2 Backtrader の p7-account-swap が正解と一致 |
| 15 Mendl-Labs/BacktestingCore | SCAN 8806 行: 「型 1 — 機構はあるが、検証の実行経路が呼ばない … 差し替えの旗では届かず、コードを書き換えないと効かない」、9153 行: 遅延の模型 `//! Variable latency simulation with jitter, ...` も型 1、7555 行: 影響の式は実行経路が直に呼ぶので差し替えの余地が無い | 確かめた(9153 行は一次資料 `config/src/variable_latency.rs` の逐語、7555 行は実装の逐語) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ: 遅延の模型は検証の実行経路が呼ばない(8806・9153 行)= 遅延の口は無い / 影響の式は実行経路が直に呼ぶ(7555 行)= 約定の口は無い / 費用・口座の口は SCAN の書き写しに無い(在るかは未確認。前の版は触れていなかった = 批評 i0-r3-08)。在るとしても 4 つの対(費用 → 2 Backtrader の p7-cost-model-swap・p7-cost-per-unit、口座 → 2 Backtrader の p7-account-swap。約定・遅延も 2 Backtrader の p7-fill-model-swap・23 hftbacktest の p7-latency-model-swap)が正解と一致 |
| 16 Luczinsritter/event_driven_backtesting_engine | SCAN 3292 行: 「get_data を差し替えるだけで当方の形の表を入れられる」。一次資料 https://raw.githubusercontent.com/Luczinsritter/event_driven_backtesting_engine/main/backtest_engine.py 59-63 行(`get_execution_price` が次の足の始値を返す、`EventBased` のメソッド)・38-42 行(現金は `self.current_balance` の数)・74-90 行(`enter_long` が現金を直に減らす)、取得日 2026-09-24。`backtest_engine.py`・`ema_arima.py`・`utils.py` を語 fee・commission・cost・slippage・latency・delay で grep して当たり 0 件 | 確かめた(一次資料のコードを読んだ) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ: 約定の値を決めるのは `EventBased` のメソッド `get_execution_price`(59-63 行)で、戦略はこの子なので上書きできる = 約定 → 2 Backtrader の p7-fill-model-swap が正解と一致 / 費用・遅延は 3 つのファイルに当たり 0 件(口は無い)/ 口座は `self.current_balance` の数を `enter_long` などが直に変える(38-42・74-90 行。差し込む口は無い)。遅延・費用・口座も在るとすれば 23 hftbacktest の p7-latency-model-swap・2 Backtrader の p7-cost-model-swap・p7-cost-per-unit・p7-account-swap が正解と一致。観点の外: `get_data` の差し替え(3292 行。データの取り込みの口で、4 つの口のどれでもない。前の版はこれを p7-fill-model-swap・p7-account-swap に対にしていた = 批評 i0-r3-06) |
| 33 SarthakDalmia1/backtesting_execution_simulator | SCAN 7189・7255 行: `execution_price = slippage_model_->get_execution_price(` と既定の `ZeroSlippageModel`、9012 行: `Timestamp submit_time = clock_.now() + config_.latency.order_submit_latency_ns;`。一次資料 https://raw.githubusercontent.com/SarthakDalmia1/backtesting_execution_simulator/main/cpp/execution/execution_simulator.hpp(33-44 行 `set_slippage_model` / `set_cost_model` / `set_event_callback`)ほか、取得日 2026-09-23 | 確かめた(一次資料の C++ を読んだ) | 再現した | 再現のファイル `opponents/repro_33_execution_simulator.py`(一次資料の行を 1 対 1 で注釈)。32 場面を通した結果 `survey_results/repro_33_execution_simulator.tsv`: p7-fill-model-swap・p7-latency-model-swap・p7-cost-model-swap・p7-cost-per-unit が正解と一致、p7-account-swap は対応なし(口座を差し替える setter が無い、execution_simulator.hpp 33-44 行)。1 つの候補で約定・遅延・費用の 3 つの口を持つ実装を確かめた候補なので、上位互換で外さず再現した |
| 35 thirupathikannan-ai/Optimal-Execution-And-Market-Impact-Simulator- | SCAN 8194 行: 「機関を持たない単体の模型」、7559 行: 「引数を与えて呼ぶ単体の模型で、差し替える既定が無い」(`temporary_impact=0.01,` ほか) | 確かめた(7559 行は実装の逐語) | 持たないと確認した | 8194・7559 行: 模擬の機関(核)を持たない単体の関数なので、差し込む先の核が無い。約定・遅延・費用・口座の 4 つの口はどれも、差し込まれる核があって初めて在る口で、8194 行がその核が無いことを書く(4 つの全部に当たる 1 つの根拠) |
| 38 microsoft/MarS | SCAN 7551 行: 「差し替える模型ではなく模擬そのもの」(`max_passive_volume_ratio=0.9,` ほか) | 確かめた(7551 行は実装の逐語) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ: 約定は模擬そのもので差し替える模型として外に出ていない(7551 行)= 約定の口は無い / 遅延・費用・口座の口は SCAN の書き写しに無い(在るかは未確認)。在るとしても 4 つの対(遅延 → 23 hftbacktest の p7-latency-model-swap、費用 → 2 Backtrader の p7-cost-model-swap・p7-cost-per-unit、口座 → 2 Backtrader の p7-account-swap)が正解と一致 |
| 49 GFT Backtest Software | SCAN 5732 行: 「塞いでいるのは地域でも環境でもなく登録という関門」 | 確かめていない(登録の奥で未到達) | 再現できない | (a) SCAN の書き写しは 5732 行の「登録の関門で原典に届かない」だけで機構の材料が無い。(b) 一次資料は登録の奥にあり、委任文 §4「鍵・登録・署名・発注・支払いをしない」により登録しないので読めない。(a) と (b) の両方で材料が足りない |
| 52 QuantConnect | SCAN 6151 行: 「約定の模型を差し替えながらイベント駆動で回す」「約定の模型を差し替え可能な部品として外に出していること」 | 確かめていない(6151 行「未確認」、README と約定の模型の文書) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ(6151 行): 約定の模型の差し替え = 約定 → 2 Backtrader の p7-fill-model-swap が正解と一致 / 遅延・費用・口座は 6151 行に無い。在るとしても 4 つの対(23 hftbacktest の p7-latency-model-swap、2 Backtrader の p7-cost-model-swap・p7-cost-per-unit・p7-account-swap)が正解と一致 |
| 54 finmarketpy | SCAN 8010 行: 「54 番と 87 番…どちらも費用を値段に当てるだけで、模型の差し替え口が無い」、7851 行(印)。前の周の実行の記録 `survey_results/stale/opp_finmarketpy_2026-09-23.tsv` の p7 の 5 行: `Backtest().calculate_trading_PnL(BacktestRequest, 価格の DataFrame 3 行, 信号の DataFrame 3 行, None)` を呼び、「約定/遅延/口座の差し込み口が無い(費用は BacktestRequest.spot_tc_bp の率)」 | 確かめた(前の周に隔離した venv で実際に呼んだ記録) | スキップ: 明らかに弱い(上位互換) | この周は動かせなかった(読み方の節の容量)。上位互換: 能力を 1 つずつ: 費用は `spot_tc_bp` の率の設定だけ(前の周の記録、8010 行)= 費用 → 2 Backtrader の p7-cost-model-swap・p7-cost-per-unit が正解と一致(率より広い模型を差し込める)/ 約定・遅延・口座の口は前の周の記録で無い(信号の表と価格の表を受けて損益を返す形)。在るとしても 4 つの対が正解と一致 |
| 63 trade-frame | SCAN 8407 行: 段 3 の 4 件(13・123・63・23)は「事象の受け口に旗が無く、差し替えずに働く」、6119 行(印)。台帳の遅延(原文)の列: 「在る。`m_dtQueueDelay`(50 から 100ms)。注文を時刻つきの遅延の列に入れ、気配の到着で取り出す」 | 確かめていない(8407 行は段の当てはめの記録、遅延は台帳の原文の列の逐語) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ: 約定は旗なしで働き差し替えない(8407 行)= 約定の口は無い / 遅延は `m_dtQueueDelay` の列(台帳の遅延(原文))= 遅延 → 23 hftbacktest の p7-latency-model-swap が正解と一致(差し替えられる口かは未確認で、在るとしても一致で覆われる)/ 費用・口座の口は行に無い。在るとしても 2 Backtrader の p7-cost-model-swap・p7-cost-per-unit・p7-account-swap が正解と一致 |
| 87 PyTrendFollow | SCAN 8151 行: 実装の逐語 `return (self.positions.shift(2).multiply((self.panama_prices()).diff(), axis=0).fillna(0) * self.point_values()) * self.rates()` と `slippage_multiplier = .5`、7871 行: 「注文の物が無い。滑りは『その日の値動きの半分』で、これも定率」、8010 行 | 確かめた(8151・7871 行は一次資料 `trading/accountcurve.py` の逐語、7857 行が在処) | 持たないと確認した | 約定・遅延: 注文の物が無い(7871 行)ので、注文を埋める模型も注文を遅らせる模型も差し込む先が無い / 費用: 滑りは定数 `slippage_multiplier = .5` の直書き(8151・7871 行)で差し込む口が無い / 口座: 損益は建玉の系列と値動きの掛け算を式で直に出し(8151 行 `self.positions.shift(2).multiply(...)`)、口座の物が無い。8010 行も「模型の差し替え口が無い」 |
| 98 mihircoding/limitOrderBook | SCAN 7550 行: 「照合そのものが値段と時刻の優先なので、差し替える余地がなく」、9011 行: `class LatencyModel:` と `send(sent_at, participant, action) -> runs at sent_at + latency(participant)` | 確かめた(9011 行は一次資料 `src/latency.py` の逐語) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ: 遅延の模型(9011 行)= 遅延 → 23 hftbacktest の p7-latency-model-swap が正解と一致 / 照合は差し替えの余地が無い(7550 行)= 約定の口は無い / 費用・口座の口は行に無い。在るとしても 2 Backtrader の p7-cost-model-swap・p7-cost-per-unit・p7-account-swap が正解と一致 |
| 107 sigc | SCAN 8806 行: 「型 1 — 機構はあるが、検証の実行経路が呼ばない」に 107 `sigc`(費用と影響の模型)、6917 行(`Skelf-Research/sigc`) | 確かめた(8806 行は呼び出しの当たりを数えた記録) | スキップ: 明らかに弱い(上位互換) | 上位互換: 能力を 1 つずつ: 費用と影響の模型は検証の実行経路が呼ばない(8806 行)= 費用・約定の口は無い / 遅延・口座の口は SCAN の書き写しに無い(在るかは未確認。前の版は触れていなかった = 批評 i0-r3-08)。在るとしても 4 つの対(遅延 → 23 hftbacktest の p7-latency-model-swap、口座 → 2 Backtrader の p7-account-swap。費用・約定も 2 Backtrader の p7-cost-model-swap・p7-cost-per-unit・p7-fill-model-swap)が正解と一致 |
| 123 carlos8f/zenbot | SCAN 8407 行(段 3 の 4 件、13 番の本家)、7298 行、6812 行(13 番は本家と同じ性質) | 確かめた(6812 行はコードの逐語) | スキップ: 明らかに弱い(上位互換) | 上位互換: 13 番と同じ(6812・7298 行): 約定の値の変更(滑りの率)→ 2 Backtrader の p7-fill-model-swap / 費用(maker・taker の手数料、6989 行は 13 番の行)→ 2 Backtrader の p7-cost-model-swap・p7-cost-per-unit / 遅延・口座は行に無く、在るとしても 23 hftbacktest の p7-latency-model-swap・2 Backtrader の p7-account-swap。どれも正解と一致 |

## grep で当たって候補に写せなかった行

`gen_pool.py` の規則で候補の番号に写せなかった grep の当たり(`pool.tsv` の末尾の「# unmapped」)を、1 行ずつ検討した(批評 i0-r1-17・i0-r2-09・i0-r3-07)。前の版はこの行を 1 件も見ていなかった。写せた行(規則 3b・3c と `READ_BY_HAND`)は上の表に入っている(P0-4 の 16、P0-7 の 63・123 はこの直しで入った)。

<!-- 写せなかった行ここから -->

`gen_unmapped_review.py` が書く(手で直さない)。`pool.tsv` の「# unmapped」の行を、観点と SCAN の行の組ごとに 1 行ずつ(同じ行が語の違う grep で 2 度当たったものは 1 行)。

| 観点 | SCAN の行 | 行の頭 | 種類 | 扱いと理由 |
|---|---|---|---|---|
| P0-3 | 44 | - src/bot/research: 11 / board.py gz_members.py liq_bands.py | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「src/bot(package: ファイル数 / ファイル名)」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 50 | - fetch_*: 28 / fetch_aggtrades.py fetch_attention.py fetch_ | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「scripts(サブディレクトリは名前/、最上位は接頭辞。.py だけ)」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 59 | - check_*: 7 / check_api.py check_data_ledger.py check_k1_bi | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「scripts(サブディレクトリは名前/、最上位は接頭辞。.py だけ)」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 60 | - record_*: 5 / record_funding_basis.py record_liquidations. | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「scripts(サブディレクトリは名前/、最上位は接頭辞。.py だけ)」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 67 | - repair_*: 2 / repair_gz_listing.py repair_liquidation_gz.p | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「scripts(サブディレクトリは名前/、最上位は接頭辞。.py だけ)」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 73 | - liquidation_*: 1 / liquidation_report.py | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「scripts(サブディレクトリは名前/、最上位は接頭辞。.py だけ)」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 95 |   tests/conftest.py tests/fixtures/jev_ops/decisions.json te | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「tests(ファイル): 139」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 110 |   docs/AUDITOR/ACTION_LOG.md docs/AUDITOR/COVERAGE_2026-09-1 | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「docs(.md): 291」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 113 |   147: MD5SUMS audit_fetch_1306_split_20260906 audit_fetch_H | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「backtest_data(ディレクトリ数)」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 399 | - src/bot/research: 11 / board.py gz_members.py liq_bands.py | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「src/bot(package: ファイル数 / ファイル名)」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 405 | - fetch_*: 28 / fetch_aggtrades.py fetch_attention.py fetch_ | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「scripts(サブディレクトリは名前/、最上位は接頭辞。.py だけ)」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 414 | - check_*: 7 / check_api.py check_data_ledger.py check_k1_bi | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「scripts(サブディレクトリは名前/、最上位は接頭辞。.py だけ)」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 415 | - record_*: 5 / record_funding_basis.py record_liquidations. | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「scripts(サブディレクトリは名前/、最上位は接頭辞。.py だけ)」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 422 | - repair_*: 2 / repair_gz_listing.py repair_liquidation_gz.p | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「scripts(サブディレクトリは名前/、最上位は接頭辞。.py だけ)」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 428 | - liquidation_*: 1 / liquidation_report.py | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「scripts(サブディレクトリは名前/、最上位は接頭辞。.py だけ)」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 450 |   tests/conftest.py tests/fixtures/jev_ops/decisions.json te | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「tests(ファイル): 139」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 465 |   docs/AUDITOR/ACTION_LOG.md docs/AUDITOR/COVERAGE_2026-09-1 | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「docs(.md): 291」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 468 |   147: MD5SUMS audit_fetch_1306_split_20260906 audit_fetch_H | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「backtest_data(ディレクトリ数)」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 965 | - src/bot/research: 11 / board.py gz_members.py liq_bands.py | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「src/bot(package: ファイル数 / ファイル名)」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 971 | - fetch_*: 28 / fetch_aggtrades.py fetch_attention.py fetch_ | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「scripts(サブディレクトリは名前/、最上位は接頭辞。.py だけ)」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 979 | - check_*: 8 / check_api.py check_data_ledger.py check_k1_bi | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「scripts(サブディレクトリは名前/、最上位は接頭辞。.py だけ)」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 981 | - record_*: 5 / record_funding_basis.py record_liquidations. | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「scripts(サブディレクトリは名前/、最上位は接頭辞。.py だけ)」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 988 | - repair_*: 2 / repair_gz_listing.py repair_liquidation_gz.p | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「scripts(サブディレクトリは名前/、最上位は接頭辞。.py だけ)」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 994 | - liquidation_*: 1 / liquidation_report.py | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「scripts(サブディレクトリは名前/、最上位は接頭辞。.py だけ)」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 1016 |   tests/conftest.py tests/fixtures/jev_ops/decisions.json te | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「tests(ファイル): 139」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 1031 |   docs/AUDITOR/ACTION_LOG.md docs/AUDITOR/COVERAGE_2026-09-1 | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「docs(.md): 294」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 1034 |   147: MD5SUMS audit_fetch_1306_split_20260906 audit_fetch_H | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「backtest_data(ディレクトリ数)」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 1493 | - src/bot/research: 11 / board.py gz_members.py liq_bands.py | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「src/bot(package: ファイル数 / ファイル名)」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 1499 | - fetch_*: 28 / fetch_aggtrades.py fetch_attention.py fetch_ | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「scripts(サブディレクトリは名前/、最上位は接頭辞。.py だけ)」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 1507 | - check_*: 8 / check_api.py check_data_ledger.py check_k1_bi | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「scripts(サブディレクトリは名前/、最上位は接頭辞。.py だけ)」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 1509 | - record_*: 5 / record_funding_basis.py record_liquidations. | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「scripts(サブディレクトリは名前/、最上位は接頭辞。.py だけ)」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 1516 | - repair_*: 2 / repair_gz_listing.py repair_liquidation_gz.p | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「scripts(サブディレクトリは名前/、最上位は接頭辞。.py だけ)」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 1522 | - liquidation_*: 1 / liquidation_report.py | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「scripts(サブディレクトリは名前/、最上位は接頭辞。.py だけ)」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 1544 |   tests/conftest.py tests/fixtures/jev_ops/decisions.json te | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「tests(ファイル): 139」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 1559 |   docs/AUDITOR/ACTION_LOG.md docs/AUDITOR/COVERAGE_2026-09-1 | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「docs(.md): 295」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 1562 |   147: MD5SUMS audit_fetch_1306_split_20260906 audit_fetch_H | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「backtest_data(ディレクトリ数)」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 1803 | \| `bt` \| 当方データ投入 \| 日付を index にした終値の DataFrame をそのまま渡せた。約定 | 道具の行(台帳の外) | 道具 `bt` の行(SCAN 1618 行「5. [深掘り] `bt`」の節)。`bt` は道具台帳に番号が無い(`awk -F'\t' '$2=="bt"' docs/DATA/tools_catalog.tsv | wc -l` → 0)ので、候補の集まり(台帳の番号で数える)に入らない。行の中身は「終値の DataFrame は入るが、約定・清算のような明細を入れる形ではない」= P0-3 の型のうち足しか受けない。候補にしたとしても、足を受ける能力は 1 Basana の p3-bar が正解と一致(`survey_results/opp_basana.tsv`)で上位互換。台帳から抜けていることはリードに返す |
| P0-3 | 1849 | - **当方の用途との相性**: 終値の DataFrame は入るが、約定・清算のような明細を入れる形ではない(実測) | 道具の行(台帳の外) | 道具 `bt` の行(SCAN 1618 行「5. [深掘り] `bt`」の節)。`bt` は道具台帳に番号が無い(`awk -F'\t' '$2=="bt"' docs/DATA/tools_catalog.tsv | wc -l` → 0)ので、候補の集まり(台帳の番号で数える)に入らない。行の中身は「終値の DataFrame は入るが、約定・清算のような明細を入れる形ではない」= P0-3 の型のうち足しか受けない。候補にしたとしても、足を受ける能力は 1 Basana の p3-bar が正解と一致(`survey_results/opp_basana.tsv`)で上位互換。台帳から抜けていることはリードに返す |
| P0-3 | 1971 | - src/bot/research: 11 / board.py gz_members.py liq_bands.py | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「src/bot(package: ファイル数 / ファイル名)」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 1977 | - fetch_*: 28 / fetch_aggtrades.py fetch_attention.py fetch_ | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「scripts(サブディレクトリは名前/、最上位は接頭辞。.py だけ)」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 1985 | - check_*: 8 / check_api.py check_data_ledger.py check_k1_bi | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「scripts(サブディレクトリは名前/、最上位は接頭辞。.py だけ)」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 1987 | - record_*: 5 / record_funding_basis.py record_liquidations. | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「scripts(サブディレクトリは名前/、最上位は接頭辞。.py だけ)」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 1994 | - repair_*: 2 / repair_gz_listing.py repair_liquidation_gz.p | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「scripts(サブディレクトリは名前/、最上位は接頭辞。.py だけ)」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 2000 | - liquidation_*: 1 / liquidation_report.py | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「scripts(サブディレクトリは名前/、最上位は接頭辞。.py だけ)」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 2022 |   tests/conftest.py tests/fixtures/jev_ops/decisions.json te | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「tests(ファイル): 139」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 2037 |   docs/AUDITOR/ACTION_LOG.md docs/AUDITOR/COVERAGE_2026-09-1 | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「docs(.md): 296」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 2040 |   147: MD5SUMS audit_fetch_1306_split_20260906 audit_fetch_H | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「backtest_data(ディレクトリ数)」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 2295 | - src/bot/research: 11 / board.py gz_members.py liq_bands.py | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「src/bot(package: ファイル数 / ファイル名)」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 2301 | - fetch_*: 28 / fetch_aggtrades.py fetch_attention.py fetch_ | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「scripts(サブディレクトリは名前/、最上位は接頭辞。.py だけ)」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 2309 | - check_*: 8 / check_api.py check_data_ledger.py check_k1_bi | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「scripts(サブディレクトリは名前/、最上位は接頭辞。.py だけ)」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 2311 | - record_*: 5 / record_funding_basis.py record_liquidations. | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「scripts(サブディレクトリは名前/、最上位は接頭辞。.py だけ)」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 2318 | - repair_*: 2 / repair_gz_listing.py repair_liquidation_gz.p | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「scripts(サブディレクトリは名前/、最上位は接頭辞。.py だけ)」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 2324 | - liquidation_*: 1 / liquidation_report.py | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「scripts(サブディレクトリは名前/、最上位は接頭辞。.py だけ)」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 2346 |   tests/conftest.py tests/fixtures/jev_ops/decisions.json te | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「tests(ファイル): 139」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 2361 |   docs/AUDITOR/ACTION_LOG.md docs/AUDITOR/COVERAGE_2026-09-1 | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「docs(.md): 297」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 2364 |   147: MD5SUMS audit_fetch_1306_split_20260906 audit_fetch_H | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「backtest_data(ディレクトリ数)」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 2595 | - src/bot/research: 11 / board.py gz_members.py liq_bands.py | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「src/bot(package: ファイル数 / ファイル名)」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 2601 | - fetch_*: 28 / fetch_aggtrades.py fetch_attention.py fetch_ | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「scripts(サブディレクトリは名前/、最上位は接頭辞。.py だけ)」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 2609 | - check_*: 8 / check_api.py check_data_ledger.py check_k1_bi | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「scripts(サブディレクトリは名前/、最上位は接頭辞。.py だけ)」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 2611 | - record_*: 5 / record_funding_basis.py record_liquidations. | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「scripts(サブディレクトリは名前/、最上位は接頭辞。.py だけ)」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 2618 | - repair_*: 2 / repair_gz_listing.py repair_liquidation_gz.p | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「scripts(サブディレクトリは名前/、最上位は接頭辞。.py だけ)」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 2624 | - liquidation_*: 1 / liquidation_report.py | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「scripts(サブディレクトリは名前/、最上位は接頭辞。.py だけ)」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 2646 |   tests/conftest.py tests/fixtures/jev_ops/decisions.json te | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「tests(ファイル): 139」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 2661 |   docs/AUDITOR/ACTION_LOG.md docs/AUDITOR/COVERAGE_2026-09-1 | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「docs(.md): 298」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 2664 |   147: MD5SUMS audit_fetch_1306_split_20260906 audit_fetch_H | 当方のリポジトリの一覧 | SCAN が当方の道具立てを数えた一覧の行(見出し「backtest_data(ディレクトリ数)」)。当たった語は当方のファイル名で、調査結果の側の道具を指さない |
| P0-3 | 6850 |    根拠は 4 回目の節 `#### 4. bt(深掘り)`(報告書 1848 行と 1849 行)の逐語「**終値の | 道具の行(台帳の外) | 道具 `bt` の行(SCAN 1618 行「5. [深掘り] `bt`」の節)。`bt` は道具台帳に番号が無い(`awk -F'\t' '$2=="bt"' docs/DATA/tools_catalog.tsv | wc -l` → 0)ので、候補の集まり(台帳の番号で数える)に入らない。行の中身は「終値の DataFrame は入るが、約定・清算のような明細を入れる形ではない」= P0-3 の型のうち足しか受けない。候補にしたとしても、足を受ける能力は 1 Basana の p3-bar が正解と一致(`survey_results/opp_basana.tsv`)で上位互換。台帳から抜けていることはリードに返す(6850 行は 1848・1849 行の逐語の引用) |
| P0-5 | 563 | **導入前の検査と導入の順序(監査 1 回目の問い 11 への答え)**: ハーネスの記録で手番を数えると、`pip d | 調査の手順・規則の文 | 調査の手順の文(導入前の検査と導入の順序。語「順序」に当たった)。道具の機構を書いていない |
| P0-5 | 1612 | 発見順(3 回目から引き継いだ順序のまま)。行頭の `[深掘り]` は §4.0 の表に語彙のすべての項目の行を持つもの | 調査の手順・規則の文 | SCAN の候補の一覧の並べ方の説明(「発見順」。語「順序」に当たった)。道具を指さない |
| P0-5 | 2100 | 発見順(3 回目から引き継いだ順序のまま)。行頭の `[深掘り]` は §4.0 の表に語彙のすべての項目の行を持つもの | 調査の手順・規則の文 | 同上(1612 行と同じ文。次の回の候補の一覧の頭) |
| P0-5 | 2412 | 発見順(3 回目から引き継いだ順序のまま)。行頭の `[深掘り]` は §4.0 の表に語彙のすべての項目の行を持つもの | 調査の手順・規則の文 | 同上(1612 行と同じ文) |
| P0-5 | 2721 | 発見順(3 回目から引き継いだ順序のまま)。行頭の `[深掘り]` は §4.0 の表に語彙のすべての項目の行を持つもの | 調査の手順・規則の文 | 同上(1612 行と同じ文) |
| P0-5 | 2980 | 発見順(3 回目から引き継いだ順序のまま)。行頭の `[深掘り]` は §4.0 の表に語彙のすべての項目の行を持つもの | 調査の手順・規則の文 | 同上(1612 行と同じ文) |
| P0-5 | 5015 | 起動の指定の逐語「**委任文 §2 の順序のとおり、この回は新しい検索計画を打ちません。**」と | 調査の手順・規則の文 | 調査の回の起動の指定の引用(「委任文 §2 の順序のとおり」。語「順序」に当たった)。道具を指さない |
| P0-5 | 5022 | **この回は検索計画を打っていない。**起動の指定の逐語「**委任文 §2 の順序のとおり、この回は新しい検索計画を打ち | 調査の手順・規則の文 | 同上(5015 行と同じ引用) |
| P0-7 | 7520 | 「**段は 2 つ書く。段(機構) = 差し替えれば届く高さ。段(既定) = そのまま使ったときの高さ。**」 | 調査の手順・規則の文 | 段の表の書き方の規則(「段(機構) = 差し替えれば届く高さ」。語「差し替え」に当たった)。道具を指さない |
| P0-7 | 7532 | **段(機構)に数える条件**: 「差し替えれば届く」とは、**設定・引数・模型の差し替えで実行経路が呼べる**ことであ | 調査の手順・規則の文 | 段(機構)に数える条件の定義(語「差し替え」に当たった)。道具を指さない |

<!-- 写せなかった行ここまで -->

<!-- 集計ここから -->

## 集計(`scripts/check_bt_considered.py --write` が書く。手で直さない)

| 観点 | 動かせた | 動かせない(検討表の行) | 動かせない割合 | 再現した | 持たないと確認した | スキップ | 再現できない |
|---|---|---|---|---|---|---|---|
| 観点 P0-1(事象駆動の設計) | 7 | 12 | 63% | 0 | 0 | 10 | 2 |
| 観点 P0-2(時刻の表現: UTC の int64 ナノ秒) | 1 | 3 | 75% | 0 | 0 | 1 | 2 |
| 観点 P0-3(8 種の事象の型) | 10 | 9 | 47% | 0 | 0 | 7 | 2 |
| 観点 P0-4(戦略が見られるのは受け取れた時刻 ≤ 今の事象だけ) | 1 | 1 | 50% | 0 | 1 | 0 | 0 |
| 観点 P0-5(同時刻の事象の決定的な並び) | 5 | 12 | 71% | 0 | 0 | 9 | 3 |
| 観点 P0-6(戦略の API: 事象ごとの呼び出し・発注・取消) | 2 | 3 | 60% | 0 | 0 | 3 | 0 |
| 観点 P0-7(約定の模型・遅延の模型・費用・口座の差し込み口) | 7 | 17 | 71% | 1 | 2 | 13 | 1 |
| 計(観点ごとの延べ) | 33 | 57 | 63% | 1 | 3 | 43 | 10 |

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
