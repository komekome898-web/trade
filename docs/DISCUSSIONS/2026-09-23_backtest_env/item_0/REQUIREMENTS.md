# 項目 0(核)要件の固定 — 2026-09-23

委任文: `docs/DATA/delegations/20260923_backtest_env_prompt.md`(指紋 `20260923_backtest_env_prompt.md@4ce1be0fa30b`)。この資料は §3「要件と判定の固定」に従い、項目 0 の 1 周目の前に要件・観点・調査結果の側を固定する。**周回の途中でここを緩めない、後から厳しくもしない。**

## 1. 委任文 §2 項目 0 の行(逐語)

| # | 項目 | 持ち物 | 最低の要件(これ以上は上に積む) |
|---|---|---|---|
| 0 | 核(先に単独で作る) | `src/bot/bt/core/` | 時刻は UTC の int64 ナノ秒。事象の型(約定・板の写真・板の差分・足・資金調達・清算・時計・注文の受付/拒否/約定の通知)。**戦略は「受け取れた時刻 ≤ 今」の事象しか見られない**(構造でルックアヘッドを不能にする)。決定的な事象の順序(同時刻の並びの規則を明記)。戦略の API(事象ごとの呼び出し・発注・取消)。他項目が差し込む口(約定模型・遅延模型・費用・口座) |

## 2. 比較の観点(測れる形。軸 = オーナー逐語「**すべてが調査結果以上の信頼性と再現性に優れたものにすること**」)

観点は §1 の行を分解したもの。各観点は「値の場面」(正解の値と一致するか)または「能力の場面」(その能力を使って出るはずの結果が出るか)のどちらかで測れる形にした。

| # | 観点 | 測り方(値/能力の場面) | どちらの軸か |
|---|---|---|---|
| P0-1 | 核の設計が事象駆動(型を持つ事象をイベントバス/イベントループで流す構造)であり、同期のバー逐次ループではないこと | 能力: 事象を型で投入し、投入順ではなく時刻順に処理されるかを見る | 信頼性(構造が模擬の前提と一致する) |
| P0-2 | 全事象の時刻が UTC 起点の int64 ナノ秒で表現され、他の単位(秒・ミリ・ISO 文字列)が核の内部表現に混入しないこと | 値: 既知の時刻(例 UTC 2026-01-01T00:00:00.123456789)を投入し、核が保持する値が同じ int64 ナノ秒と一致するか | 信頼性 |
| P0-3 | 8 種の事象型(約定・板の写真・板の差分・足・資金調達・清算・時計・注文の受付/拒否/約定の通知)をすべて核の事象として表現し受理できること | 能力: 型ごとに 1 件ずつ投入し、核が拒否せず対応する事象として保持するかを見る(型が無ければ「対応なし」) | 信頼性(§1「事象の型」の網羅性) |
| P0-4 | 戦略が「受け取れた時刻 ≤ 今」の事象しか見えないことが、注意書きや呼び出し規約ではなく型・API の構造で強制されること | 能力: 戦略側から未来時刻の事象を読もうとするコードが、実行時エラーか型エラーで止まるかを見る(素通りしたら不合格) | 信頼性(ルックアヘッドの構造的不能化。§1 直書き) |
| P0-5 | 同時刻の複数事象に決定的な並び規則が明記され、同じ入力を 2 回実行して同じ順序・同じ結果になること | 値+再現: 同時刻に複数型の事象を仕込んだ入力を作り、規則どおりの順で処理されるか(値)、2 回実行して一致するか(再現) | 信頼性+再現性 |
| P0-6 | 戦略 API が「事象ごとの呼び出し」「発注」「取消」の 3 つを備え、戦略側がこれらを直接呼べること | 能力: 戦略から `place`/`cancel` に相当する呼び出しを行い、核がそれを注文の受付/拒否/約定の通知の事象として返すか | 信頼性(§1「戦略の API」直書き) |
| P0-7 | 他項目(約定模型・遅延模型・費用・口座)が核を書き換えずに差し込める口(インターフェース)を持つこと | 能力: 各口にダミー実装を差し込み、核のコードを変えずに動くか | 信頼性+再現性(差し替えても同じ骨格で再現できる) |

## 3. 調査結果の側

**候補の抽出は機械的。**手作業での足し引きはしていない。

### P0-1(事象駆動アーキテクチャ)— `tools_catalog.tsv` に該当列あり

コマンド:
```
awk -F'\t' 'NR==1{next} $7=="○"{print $1"\t"$2}' docs/DATA/tools_catalog.tsv
```
出力(列7 = イベント駆動、印 ○ の行を全部):
```
1	Basana
6	Ziplime
13	DeviaVir/zenbot
18	zipline-reloaded
23	hftbacktest
37	ThePredictiveDev/Automated-Financial-Market-Trading-System
41	prediction-market-backtesting
52	QuantConnect
53	Rqalpha
57	WonderTrader
58	nautilus_trader
61	barter-rs
62	qf-lib
63	trade-frame
65	aat
68	quanttrader
69	gobacktest
91	braedonsaunders/homerun
123	carlos8f/zenbot
```
**この観点には `段(機構)`/`段(既定)` の列が無い**(その 2 列は `区分1-市場影響と約定の模型`(項目 3 の観点)専用で、TOOLS_CATALOG.md の記載どおり「段の表は 52 行(市場影響と約定の模型の印を持つ候補と同じ集合)」に限られる。P0-1 に段は付けられない)。代わりに、SCAN の一次資料で構造の裏付けが最も強い候補を書く: **候補 58 `nautilus_trader`**。SCAN 6061 行「登録情報の説明の逐語は『Production-grade Rust-native trading engine with **deterministic event-driven architecture**』」+ 6061 行「イベント駆動・ティック・足・板のすべてを検証の入力として名乗っている」(一次資料、README 60 行目)。

### P0-2(時刻表現: UTC int64 ナノ秒)— 該当列なし。SCAN へ grep

grep の語(先出し): `ナノ秒|nanosecond|マイクロ秒|microsecond`
コマンド:
```
grep -n "ナノ秒\|nanosecond\|マイクロ秒\|microsecond" docs/DATA/SCAN_2026-09-21_tools.md
```
当たった候補(全部):
- 候補 58 `nautilus_trader` — SCAN 247 行・6061 行・6152 行: 「historical quote tick, trade tick, bar, order book, and custom data with **nanosecond resolution**」(一次資料、PyPI description)。UTC かどうかの明記は本行に無い。
- 候補 34 `SLMolenaar/QuantCore` — SCAN 4275・4419・4428 行: 入力型 `TickData(symbol, timestamp_ns, ...)`、`timestamp_ns` は整数ナノ秒(実測)。**UTC かどうかは未確認**(SCAN 4428 行「時間帯の扱いは公開名 `TradingCalendar` にあるが中身は見ていない。UTC かどうかは未確認」)。
- 候補 44 `lo2cin4bt` — SCAN 5889 行: 契約スキーマの逐語 `"time_standard": {"const": "UTC"}` と `"precision": {"const": "nanosecond"}`(一次資料、`bar-time-contract-v1.schema.json`)。

**段(機構)相当の判定**: この観点にも `段` 列は無い(P0-1 と同じ理由)。3 候補のうち UTC とナノ秒の両方を一次資料の契約(スキーマの `const`)で固定しているのは**候補 44 `lo2cin4bt` のみ**であり、他 2 候補はナノ秒は確認できても UTC は未確認/本行に無い。よって最も強い機構は**候補 44、SCAN 5889 行**。

### P0-3(8 種の事象型の網羅性)— 該当列なし。SCAN へ grep(型ごと)

grep の語(先出し、型ごと): `資金調達|funding rate|funding_rate` / `清算|liquidation` / `板の差分|板スナップショット|板の写真|order book snapshot|depth update|incremental` / `決定的.*順序`(足・注文受付/拒否/約定通知は他観点の grep と重複するためそちらに集約)
コマンド:
```
grep -n "資金調達\|funding rate\|funding_rate" docs/DATA/SCAN_2026-09-21_tools.md
grep -n "清算\|liquidation" docs/DATA/SCAN_2026-09-21_tools.md
grep -n "板の差分\|板スナップショット\|板の写真\|order book snapshot\|depth update\|incremental" docs/DATA/SCAN_2026-09-21_tools.md
```
当たった候補(抜粋。件数が多いため事象型と紐づく行のみ):
- 候補 41 `prediction-market-backtesting`(NautilusTrader の拡張) — SCAN 4112 行: 「清算・資金調達の無い場の検証という点で当方に無い型」= **この候補自身が清算・資金調達を持たない場の道具**(能力として無いことを一次資料相当の記述で確認)。SCAN 6070 行: README 逐語「Book replay order book deltas with trade ticks」= **板の差分(P0-3 の一部)を持つ**(一次資料)。
- 候補 34 `SLMolenaar/QuantCore` — SCAN 4427 行(実測): 「清算・資金調達率に当たる入口は公開名に無い」。
- 候補 40 `OpenMarket`(ライブラリではなくチャート型サービス) — SCAN 5694・5771 行: 一次資料(サイト本文)で「Real-time liquidation maps」「funding」を謳うが、**未着手/料金未確認**で粒度(足より細かいか)の記述が無い。
- 候補 103 `IsaacCheng9/order-book-simulator` — SCAN 5512 行(実測): 板の差分(deltas)を持つ。試験名 `test_order_book_deltas.py` 等。ただし SCAN 5241 行「浅い。単体の関数として呼ぶ経路が配布物から読み取れない」。

**判定**: 8 種のうち「資金調達」「清算」を一次資料で明確に持つと確認できた候補は、この grep の範囲では **0 件**(候補 40 `OpenMarket` はサイト本文でその 2 語を謳うが未着手・粒度未確認で、機構として実装を確かめていない)。板の差分は候補 41・103 で確認。**段の判定は付けない**(候補が揃わないため、この観点は「調査結果の側でも 8 種全部を機構として確認できた候補は無い」という状態を報告に持ち越す)。

### P0-4(ルックアヘッド禁止の構造性)— 該当列なし。SCAN へ grep

grep の語(先出し): `先読み|未来の情報|将来の情報|データスヌーピング|data snooping`
コマンド:
```
grep -n "先読み\|未来の情報\|将来の情報\|データスヌーピング\|data snooping\|peek" docs/DATA/SCAN_2026-09-21_tools.md
```
当たった候補:
- 候補 unknown(SCAN 3166 行、`区分1-足` 系の候補。文中の逐語のみで候補番号は本行に無い) — 実測: 「建玉は `enter_long`/`enter_short`/`close_position` の 3 つだけで、いずれも次の足の始値で必ず約定する…**先読みは防いでいるが、約定しない可能性は模型に無い**」。
- 候補 62 `qf-lib` — SCAN 6118・6154 行: 「日の寄りと引けをイベントとして刻み、**先読みの偏りを防ぐ道具**つきで検証する」(未確認: 導入・最小実行。原文の逐語は本行に「先読みの偏りを防ぐ道具を持つと書いている」)。

**判定**: この 2 件はいずれも「先読みを防ぐ」という**記述**止まりで、型・API による構造的な禁止(P0-4 の測り方=未来時刻の読み出しが実行時に止まるか)を実測で確認した行は grep の範囲に無い。**段は付けない**(構造的な確認が取れた候補が無いため)。

### P0-5(同時刻事象の決定的順序)— 該当列なし。SCAN へ grep

grep の語(先出し): `決定的|deterministic|同時刻|順序`
コマンド:
```
grep -n "決定的\|deterministic\|同時刻\|tie.break\|順序" docs/DATA/SCAN_2026-09-21_tools.md
```
当たった候補:
- 候補 44 `lo2cin4bt` — SCAN 5890 行(一次資料、契約スキーマの不変条件): `"same_timestamp_lifecycle_order_is_data_derived_signal_order_fill"`。**同時刻の中で「データ→派生→信号→注文→約定」の順を契約(スキーマ)として固定している**。P0-5 の要件(同時刻の並びの規則を明記)に直接対応する記述。
- 候補 101 `akurkar07/OrderBook` — SCAN 4881 行: 説明の逐語「deterministic tests」。SCAN 5418 行(実測): 「時間優先は決定的…ただし `timestamp` が実時計なので、再現には並べる順序に頼る」。
- 候補不明(SCAN 3505・3584 行、`PySystemtrade` 系) — 実測: 「同じ入力を 2 回走らせた約定の表が `DETERMINISTIC_TWO_RUNS_IDENTICAL=True`」(再現性の実測だが、同時刻の複数事象型をまたぐ順序規則ではなく単一系列の再現)。

**段の判定**: 同時刻・複数事象型の並び規則を一次資料(スキーマ)で明記しているのは**候補 44 のみ**。よって最も強い機構は**候補 44、SCAN 5890 行**。

### P0-6(戦略 API: 事象ごとの呼び出し・発注・取消)— 該当列なし。SCAN へ grep

grep の語(先出し): `on_bar|on_tick|コールバック|callback|プラガブル|差し替え可能`
コマンド:
```
grep -n "on_bar\|on_tick\|コールバック\|callback\|戦略 API\|strategy interface\|プラガブル\|差し替え可能\|モジュール式\|pluggable" docs/DATA/SCAN_2026-09-21_tools.md
```
当たった候補(発注・取消の API に直接触れる行):
- 候補 13 `DeviaVir/zenbot` — SCAN 6812 行(実測、ソース逐語): `eventBus.on('trade', queueTrade)` / `s.strategy.onPeriod.call(s.ctx, s, function () {` = **事象ごとのコールバック(trade 事象・期間ごとの周期)を持つ**。ただし SCAN 6812 行「板の待ち行列は無い」。
- 候補 1 `Basana` — SCAN 1680 行(推定、コードの外挿): 「Exchange の API(`subscribe_to_bar_events`/`dispatcher`)…バーの到着を購読して注文を出す形」= 事象購読 + 発注呼び出しの形。SCAN 1823 行: 「注文のイベントの購読(`subscribe_to_order_events`)」を持つと明記(当方に無いものの一覧に列挙、原資料に存在の確認あり)。

**段の判定**: 発注(`place` 相当)・取消・事象購読の 3 つが揃って一次資料の API 名で確認できたのは**候補 1 `Basana`**(`subscribe_to_bar_events`・`subscribe_to_order_events` の 2 種の購読 API がコードに実在、SCAN 1823 行)。候補番号 1、SCAN 1680・1823 行。

### P0-7(他項目の差し込み口: 約定模型・遅延模型・費用・口座)— 該当列なし。SCAN へ grep

grep の語(先出し): `差し替え可能|差し替えながら|列の模型を差し替え|流動性の模型を差し替え`
コマンド:
```
grep -n "差し替え\|プラガブル\|モジュール式\|pluggable" docs/DATA/SCAN_2026-09-21_tools.md
```
当たった候補:
- 候補 52 `QuantConnect`(`Lean`) — SCAN 6151 行: 「足とティックの両方を入力にして、**約定の模型を差し替えながら**イベント駆動で回す」「約定の模型を差し替え可能な部品として外に出していること」(未確認: 導入。README と約定の模型のみ読んだ)。
- 候補 1 `Basana` — SCAN 7176・7666 行(実測、ソース逐語): `liquidity_strategy.on_bar(...)` / `order.try_fill(bar, liquidity_strategy)` = **流動性(約定)の模型が差し替え可能な引数として渡されている**。既定は「影響あり」側(SCAN 7666 行)。
- 候補 23 `hftbacktest`(`nkaz001/hftbacktest`) — SCAN 9234 行: 「列の模型を差し替えられる形で持ち、深さの変化と約定を別の口で受ける」(未確認: 導入。実装の原典に到達)。

**段の判定**: 約定模型の差し替えをソースコードの呼び出し経路(実測)まで確認できたのは**候補 1 `Basana`**(`liquidity_strategy` を `order_mgr.py`/`liquidity.py` が受け取って呼ぶ経路、SCAN 7176 行)。候補 52・23 は README 相当の記述に留まる(未確認)。よって候補番号 1、SCAN 7176・7666 行。遅延模型・費用・口座の差し込み口については、この grep の範囲で一次資料の実装確認は無い(未確認のまま報告に持ち越す)。

## 4. 当方の現状(旧 `src/bot/backtest/` ほか)

- **設計全体(P0-1 の裏返し)**: `src/bot/backtest/engine.py:273` `for i in range(len(candles)):` — 単一の足(bar)を添字で逐次処理する同期ループであり、型を持つ複数の事象をイベントバスで流す構造ではない(イベント駆動ではない)。
- **時刻表現(P0-2)**: `src/bot/backtest/engine.py` 全 398 行に `timestamp`/`int64`/`nanosecond`/`ナノ秒` の出現は **0 件**(`grep -c` で実測)。時刻は `candles` の行番号 `i` でのみ扱われ、UTC・ナノ秒いずれの明示的表現も無い。
- **事象型(P0-3)**: `src/bot/backtest/engine.py` が扱うのは足(OHLCV の `candles`)のみ。板の写真・板の差分は `src/bot/research/board.py:26-37`(`SNAPSHOT_PREFIX`・`is_snapshot_channel`・`is_diff_channel`)に別モジュールとして存在するが、`engine.py` とは統合されていない。資金調達・清算・時計・注文の受付/拒否/約定の通知に相当する事象型は `src/bot/backtest/engine.py` に無い。
- **ルックアヘッド禁止(P0-4)**: `src/bot/backtest/engine.py:3-11`(モジュール docstring)に「Anti-look-ahead design: The strategy at bar i sees candles[0..i] only」とあり、`src/bot/strategy/base.py:38`「Implementations must only use rows 0..i to decide at i (backtest engine enforces this by slicing).」で足の範囲はエンジン側のスライスにより強制されている。ただしこれは足という単一の事象型に対する規約であり、複数事象型(板・資金調達等)をまたいだ「受け取れた時刻 ≤ 今」の構造的強制は存在しない(そもそも複数事象型が無い)。
- **決定的順序(P0-5)**: 単一系列(足)の逐次処理のため同時刻の複数事象という概念自体が無く、並び規則を明記する対象が存在しない。
- **戦略 API(P0-6)**: `src/bot/strategy/base.py:29-47` の `Strategy.on_candles(candles: pd.DataFrame) -> Signal` が唯一の入口。事象ごとの複数コールバック(on_tick/on_orderbook 等)は無く、戦略から直接 `place`/`cancel` を呼ぶ API も無い(戦略は `Signal` を返すだけで、発注・取消は `engine.py` 内部の `open_position`/`close_position` が行う。`src/bot/strategy/base.py:2-4` 「Strategies see candles and return a Signal. They know nothing about orders, sizes, balances or the exchange API」)。
- **差し込み口(P0-7)**: `src/bot/backtest/engine.py:99` の `CostModel` クラスが費用(手数料・スプレッド)を持つが、約定模型・遅延模型・口座会計は `engine.py` 内部の関数(`open_position`/`close_position`/`entry_ok` 等、`engine.py:134` 以降の `run_backtest` 内のクロージャ)にハードコードされており、核を書き換えずに差し替える口はコード上確認できない(該当する差し替え用インターフェースの定義行は無い)。
