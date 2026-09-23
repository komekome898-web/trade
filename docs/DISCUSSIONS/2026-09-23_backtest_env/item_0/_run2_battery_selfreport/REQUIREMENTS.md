# 要件書 — 項目 0「核」(2026-09-23、資料係)

委任文 `docs/DATA/delegations/20260923_backtest_env_prompt.md`(指紋 `20260923_backtest_env_prompt.md@c4d453ab0b09`)§3「要件と判定の固定」「調査結果の側の選び方」に従い、
1 周目の前にこの項目の要件を固定する。**周回の途中でこの要件・観点・圧倒の判定を緩めない、後から厳しくもしない。**

---

## 1. 委任文 §2 の項目 0 の行(逐語)

| # | 項目 | 持ち物 | 最低の要件(これ以上は上に積む) |
|---|---|---|---|
| 0 | 核(先に単独で作る) | `src/bot/bt/core/` | 時刻は UTC の int64 ナノ秒。事象の型(約定・板の写真・板の差分・足・資金調達・清算・時計・注文の受付/拒否/約定の通知)。**戦略は「受け取れた時刻 ≤ 今」の事象しか見られない**(構造でルックアヘッドを不能にする)。決定的な事象の順序(同時刻の並びの規則を明記)。戦略の API(事象ごとの呼び出し・発注・取消)。他項目が差し込む口(約定模型・遅延模型・費用・口座) |

出典: `docs/DATA/delegations/20260923_backtest_env_prompt.md` 63 行目。

---

## 2. 比較の観点(観点ごとに 1 行、測れる形)

オーナーの完了の形(逐語、委任文 6 行目): 「**すべてが調査結果以上の信頼性と再現性に優れたものにすること。**」を軸に、上の項目 0 の行を 7 つの測れる観点に分けた。各観点は「候補が持つ/持たない」または「候補が扱える事象型の数」で数えられる形にした。

| 観点 | 測り方(測れる形) |
|---|---|
| 観点 1: 事象駆動アーキテクチャ | 足の走査や一括のベクトル化ではなく、個々の事象ごとに戦略を駆動する構造を持つか(持つ/持たない の二値) |
| 観点 2: 事象型の網羅性 | 約定・板の写真・板の差分・足・資金調達・清算・時計・注文の受付/拒否/約定の通知、の 8 種類のうち、実装のコードで確かめられる形で扱える事象型の数(0〜8 のカウント) |
| 観点 3: 時刻の精度 | UTC の int64 ナノ秒(またはそれと同等以上の精度)で時刻を保持しているか(持つ/持たない の二値。原典の型定義・契約で確認する) |
| 観点 4: ルックアヘッド防止の構造化 | 戦略が「受け取れた時刻 ≤ 今」の事象しか参照できないことを、構造(型・API の作り)で強制しているか(強制する/しない の二値。README の主張だけでなく実装のコードで確認する) |
| 観点 5: 同時刻事象の決定的順序 | 同一タイムスタンプに複数の事象が来たときの順序を決定的に定める規則(明記された tie-break)を、実装または契約として持つか(持つ/持たない の二値) |
| 観点 6: 戦略 API の完全性 | 事象ごとのコールバック・発注・取消の 3 種の呼び口をすべて持つか(0〜3 のカウント) |
| 観点 7: 拡張口(モジュール性) | 約定模型・遅延模型・費用・口座の 4 つを、核を書き換えずに差し替え可能な口として持つか(0〜4 のカウント) |

**該当する要素の列がある観点**: 観点 1(`tools_catalog.tsv` の「イベント駆動」列)、観点 2 のうち 約定≈「ティック」列・足≈「足」列・板の差分/待ち行列≈「板の待ち行列」列の 3 要素。
**該当する要素の列が無い観点**: 観点 2 の残り 5 要素(板の写真・資金調達・清算・時計・注文の受付/拒否/約定の通知)、観点 3、観点 4、観点 5、観点 6、観点 7。これらは `docs/DATA/SCAN_2026-09-21_tools.md` への grep で候補を取った(§3)。

---

## 3. 調査結果の側

**呼び名**: 「台帳」= `docs/DATA/tools_catalog.tsv`。「SCAN」= `docs/DATA/SCAN_2026-09-21_tools.md`(10,694 行)。候補番号は台帳の 1 列目。
**危険な兆候がある 11 件(導入も実行もしない。委任文 §4)**: 44・74・120・41・58・19・112・111・97・51・118。下で候補番号として出てくる場合は都度明記する。

### 3.1 観点 1: 事象駆動アーキテクチャ(該当列あり)

コマンド:
```
awk -F'\t' '$7=="○"{print $1}' docs/DATA/tools_catalog.tsv
```
結果(19 件、機械的に全部): 1, 6, 13, 18, 23, 37, 41, 52, 53, 57, 58, 61, 62, 63, 65, 68, 69, 91, 123

段(機構)の最も高い機構(最大値 6。同値タイのため全部書く): 候補 1 `Basana`(SCAN 6836 行)・候補 6 `Ziplime`(SCAN 9650 行)・候補 18 `zipline-reloaded`(SCAN 9857 行)・候補 37 `ThePredictiveDev/Automated-Financial-Market-Trading-System`(SCAN 10426 行、段(機構) 5・6)・候補 91 `braedonsaunders/homerun`(SCAN 7858 行、段(機構) 3・4・5・6)。

### 3.2 観点 2: 事象型の網羅性

#### 3.2.1 台帳の列がある 3 要素(機械的に全部抜き出し)

コマンド:
```
awk -F'\t' '$4=="○"{print $1}' docs/DATA/tools_catalog.tsv   # 足 → 「足」事象に対応
awk -F'\t' '$5=="○"{print $1}' docs/DATA/tools_catalog.tsv   # ティック → 「約定」事象に対応
awk -F'\t' '$6=="○"{print $1}' docs/DATA/tools_catalog.tsv   # 板の待ち行列 → 「板の差分」事象に対応(「板の写真」は別途 §3.2.2)
```

- 足(55 件): 1,2,3,4,5,6,7,8,10,11,13,15,16,18,19,20,21,40,43,44,45,46,48,50,51,52,53,54,55,56,57,58,60,61,62,67,68,69,70,72,73,74,75,80,85,86,87,92,94,107,111,120,121,122,123
  段(機構)最大値 6 のもの: 候補 1(SCAN 6836)・候補 4 `PyBroker`(SCAN 6845)・候補 6(SCAN 9650)・候補 15 `Mendl-Labs/BacktestingCore`(SCAN 6879)・候補 18(SCAN 9857)・候補 21 `Qlib`(SCAN 6899)・候補 92 `Quentin-Piot/prediction-market-backtester`(SCAN 7859)
- ティック(19 件): 13,20,23,31,41,45,52,53,57,58,59,61,63,68,90,91,95,119,123
  段(機構)最大値 6 のもの: 候補 91(SCAN 7858)・候補 119 `peernagy/lob_bench`(SCAN 9405)
- 板の待ち行列(19 件): 23,33,37,38,57,65,90,91,95,96,97,98,99,100,101,102,103,104,109
  段(機構)最大値 6 のもの: 候補 37(SCAN 10426)・候補 91(SCAN 7858)

**「板の写真」だけを取り出す列は台帳に無い**(「板の待ち行列」は待ち行列の追跡=差分寄りの概念で、写真(スナップショット)そのものを別扱いする列ではない)。下の §3.2.2 に回す。

#### 3.2.2 台帳の列が無い 5 要素(SCAN への grep)

検索語を先に書く:
- 板の写真: `板の写真` `snapshot`
- 資金調達: `資金調達` `funding rate` `funding_rate`
- 清算: `清算` `liquidation`
- 時計: `時計` `クロック` `clock event` `ClockEvent`
- 注文の受付/拒否/約定の通知: `注文の受付` `order accept` `order reject` `OrderAccepted` `OrderRejected` `約定通知` `fill notification` `OrderFilled` `FillEvent`

コマンドと結果:
```
grep -n "板の写真\|snapshot" docs/DATA/SCAN_2026-09-21_tools.md            # 大半がデータファイル一覧の雑音。候補固有の一次資料の記述は取れず
grep -n "資金調達\|funding rate\|funding_rate" docs/DATA/SCAN_2026-09-21_tools.md   # 5 件
grep -n "清算\|liquidation" docs/DATA/SCAN_2026-09-21_tools.md              # 87 件(候補に紐づく行を目視で絞る)
grep -n "時計\|クロック\|clock event\|ClockEvent" docs/DATA/SCAN_2026-09-21_tools.md # 14 件
grep -n "注文の受付\|order accept\|order reject\|OrderAccepted\|OrderRejected\|約定通知\|fill notification\|OrderFilled\|FillEvent" docs/DATA/SCAN_2026-09-21_tools.md
```

結果(候補ごと。実装のコードで確かめたものを優先し、README だけの主張は「README 止まり」と明記):

- **板の写真**: 候補固有の一次資料の記述は取れなかった(`snapshot` の当たりはデータファイル名の列挙などの雑音のみ)。**未確認**(この grep の範囲では見つからない。§4「無い・取れない」の規則により、試した語と範囲をここに残す)。
- **資金調達**: 実装のコードで確かめた候補は **0 件**。候補 40 `OpenMarket`(SCAN 5694 行)がサイトの謳い文句「track CVD, funding or open interest」で触れるのみ(README/サイト止まり、一次資料は未取得、"浅い")。候補 41 `prediction-market-backtesting`(SCAN 4112 行、**危険リスト該当・導入不可**)は逆に「清算・資金調達の無い場の検証という点で当方に無い型」と明記(=持たない側の記録)。
- **清算**: 実装のコード(一次資料)で確かめた最も強い候補は **候補 61 `barter-rs`**(SCAN 6305 行・6422 行・6653 行)。Rust の `DataKind` 列挙が足・約定のティック・L1・L2・**清算**の 5 型を同じ検証の流れに載せる設計で、公式サンプルのソースまで確認済み。段(機構)は該当列(市場影響と約定の模型)に印が無いため数値は無い(該当なし)。
- **時計**: 候補 11(索引 `docs/DATA/TOOLS_CATALOG.md` §1 は `OctoBot` と呼ぶが、台帳 tsv の名前欄は `python3` — **索引と台帳の名前が食い違っており未確認**)の模擬が `time_updater` という時計を進める仕組みを持つ(SCAN 4153 行)。ただし検証の実行経路がそれを回すには拡張の取引の型が要り、9 回目の実行では代わりに価格事象を 1 回注入する迂回で済ませたと記録されている(=機構はあるが、そのままでは呼ばれない側)。段(機構)は該当なし。
- **注文の受付/拒否/約定の通知**: 拒否は候補 61 `barter-rs` に実装のコードで確認(`ApiError::OrderRejected`、SCAN 6567 行。ただし取消は `unimplemented!()` で未実装、受け付けるのは成行のみ)。約定の通知は候補 58 `nautilus_trader`(**危険リスト該当・導入不可**)で `OrderFilled` イベントが実測(リードが打ち直して確認、SCAN 898 行、rc=0 の実行ログ)。候補 69 `gobacktest`(SCAN 6068 行)は README で「data event, signal event, **order event**, **fill event**」の 4 種を名乗るが、この回は README 止まりで実装のコードまでは降りていない。

### 3.3 観点 3: 時刻の精度(該当列なし → grep)

検索語を先に書く: `ナノ秒` `nanosecond` `int64`
コマンド:
```
grep -n "ナノ秒\|nanosecond\|int64" docs/DATA/SCAN_2026-09-21_tools.md
```
結果(9 件)。実装のコードまたは機械可読の契約で「UTC・ナノ秒」を確認できた候補:
- **候補 44 `lo2cin4bt`**(**危険リスト該当・導入不可**。SCAN 5889 行): `bar-time-contract-v1.schema.json` の逐語 `"time_standard": {"const": "UTC"}` と `"precision": {"const": "nanosecond"}`。一次資料の JSON Schema そのもので確認。
- **候補 58 `nautilus_trader`**(**危険リスト該当・導入不可**。SCAN 247 行・6061 行): README 逐語「historical quote tick, trade tick, bar, order book, and custom data with **nanosecond resolution**」。段(機構)は該当列に印が無く数値なし。
- **候補 34 `SLMolenaar/QuantCore`**(SCAN 4428 行、実測、危険リストに該当しない): 入力の型 `timestamp_ns` はナノ秒の整数と実測で確認済みだが、**UTC かどうかは未確認**(逐語「時間帯の扱いは公開名 `TradingCalendar` にあるが中身は見ていない。UTC かどうかは未確認」)。台帳の 6 要素の印はすべて空欄で段(機構)も無い。

候補 44・58 は委任文 §4 の危険リスト 11 件に含まれ、**導入も実行もしない**(§3 の「(a) の書き写しの範囲だけ」)。候補 34 は危険リストに無いが UTC の確認が未了で、「ナノ秒かつ UTC」の両方を満たすと確認できた候補は現時点で **0 件**。この観点は「一次資料の書き写しでしか確認できない」ことを記録し、実行による再現はしない。

### 3.4 観点 4: ルックアヘッド防止の構造化(該当列なし → grep)

検索語を先に書く: `ルックアヘッド` `look-ahead` `lookahead` `先読み`
コマンド:
```
grep -n "ルックアヘッド\|look-ahead\|lookahead\|先読み" docs/DATA/SCAN_2026-09-21_tools.md
```
結果(14 件、うち候補固有の実測は 2 件)。実装のコードで確かめた最も強い候補:
- **候補 16 `Luczinsritter/event_driven_backtesting_engine`**(SCAN 3166 行、**実測**): `get_execution_price` が常に `self.data['Open'].iloc[ind_nbr + 1]`(次の足の始値)を返す構造で、先読みを構造上防いでいる。ただし同じ知見に「約定しない可能性は模型に無い」という限界の記録も併記されている。段(機構)は該当列に印なし(数値なし)。
- 候補 62 `qf-lib`(SCAN 6067 行)は README で「Tools to prevent look-ahead bias」を明記するが、この回は README 止まりで実装のコードまで降りていない(未確認)。

### 3.5 観点 5: 同時刻事象の決定的順序(該当列なし → grep)

検索語を先に書く: `同時刻` `同じ時刻` `同一時刻` `tie-break` `tiebreak` `deterministic order` `決定的な順序` `順序の規則`、および広めに `順序`
コマンド:
```
grep -c "同時刻" docs/DATA/SCAN_2026-09-21_tools.md          # 0
grep -c "同じ時刻" docs/DATA/SCAN_2026-09-21_tools.md         # 4
grep -c "同一時刻" docs/DATA/SCAN_2026-09-21_tools.md         # 0
grep -c "tie-break" docs/DATA/SCAN_2026-09-21_tools.md        # 0
grep -c "tiebreak" docs/DATA/SCAN_2026-09-21_tools.md         # 0
grep -c "deterministic order" docs/DATA/SCAN_2026-09-21_tools.md   # 0
grep -c "決定的な順序" docs/DATA/SCAN_2026-09-21_tools.md      # 0
grep -n "順序" docs/DATA/SCAN_2026-09-21_tools.md
```
結果: 「tie-break」系の英語語彙は 0 件。「順序」の広い検索(15 件)を目視で絞ると、候補固有で同時刻の順序規則を明記しているのは 1 件だけ見つかった:
- **候補 44 `lo2cin4bt`**(**危険リスト該当・導入不可**。SCAN 5890 行、一次資料の JSON Schema): 契約の不変条件の逐語 `"same_timestamp_lifecycle_order_is_data_derived_signal_order_fill"`。同じ時刻の中でデータ→派生→信号→注文→約定の順を固定すると明記。段(機構)は該当列に印なし(数値なし)。
この候補も危険リスト該当のため、書き写しの範囲だけを参照し、導入・実行はしない。

### 3.6 観点 6: 戦略 API の完全性(該当列なし → grep)

検索語を先に書く: `コールバック` `callback`
コマンド:
```
grep -n "コールバック\|callback" docs/DATA/SCAN_2026-09-21_tools.md
```
結果(1 件、SCAN 6812 行): **候補 13 `DeviaVir/zenbot`** と **候補 123 `carlos8f/zenbot`**(同じ実装と記録されている)。逐語 `eventBus.on('trade', queueTrade)` と `s.strategy.onPeriod.call(s.ctx, s, function () {...})` — 事象(取引)ごとのコールバック `onPeriod` を実装のコードで確認。ただし発注・取消を別の明示 API として持つかはこの回の記述からは読めない(未確認)。
段(機構)最大値(両候補とも 3・4、タイ): 候補 13(SCAN 6874 行)・候補 123(SCAN 7298 行)。

### 3.7 観点 7: 拡張口(モジュール性、該当列なし → grep)

検索語を先に書く: `差し替え` `プラグ` `差し込み`
コマンド:
```
grep -n "差し替え" docs/DATA/SCAN_2026-09-21_tools.md | grep -iE "模型|model|口|slippage|fill|cost|latency|遅延|費用|account|口座"
grep -n "プラグ" docs/DATA/SCAN_2026-09-21_tools.md
grep -n "差し込み" docs/DATA/SCAN_2026-09-21_tools.md
```
結果: 「差し替え」の当たりの大半は約定・滑りの模型(項目 3 の領域)。核(項目 0)の観点として意味を持つのは「複数の層が独立に差し替え可能」という設計そのもの:
- **候補 6 `Ziplime`**(SCAN 2399 行・2483 行、実測): 滑りの模型・手数料の模型・取引所の暦が別ファイルで差し替え可能、同じ算法ファイルを模擬と実弾で共有。4 要素中「約定模型・費用」の 2 要素を実装のコードで確認。遅延・口座の差し替え口はこの回の記述に無い。
- **候補 11**(索引は `OctoBot`、台帳 tsv 名前欄は `python3` — 名前の食い違い未確認。SCAN 2836 行、実測): 戦略を「評価器→戦略→取引の型」の 3 段に分け差し替え式にしているが、これは戦略層の拡張であり、項目 0 が求める「約定模型・遅延模型・費用・口座」の 4 要素そのものではない(部分一致)。
段(機構)はこの観点の該当候補では市場影響列に印がある候補(6)のみ値を持つ: 候補 6、段(機構) 4・6(SCAN 9650 行、§3.1 と同じ記載)。

---

## 4. 当方の現状(旧 `src/bot/backtest/` ほか)の該当箇所

| 観点 | 当方の現状 | ファイル:行 |
|---|---|---|
| 観点 1(事象駆動) | 事象駆動ではない。`for i in range(len(candles))` による足単位の逐次ループのみ。約定・板・資金調達・清算・時計・注文通知を独立した事象として扱う構造は無い | `src/bot/backtest/engine.py:273` |
| 観点 2(事象型網羅性) | 「足」1 種類のみ。約定・板の写真・板の差分・資金調達・清算・時計・注文の受付/拒否/約定の通知はいずれも 0 件(`grep -n "funding\|liquidation\|orderbook\|order_book\|清算\|資金調達\|板" src/bot/backtest/engine.py` の当たり 0 件、2026-09-23 実測) | `src/bot/backtest/engine.py`(全体、398 行) |
| 観点 3(時刻精度) | 時刻型を持たない。ループは `candles` の DataFrame の**位置インデックス** `i`(整数)で進み、UTC・ナノ秒どころかタイムスタンプそのものを直接扱うコードが無い | `src/bot/backtest/engine.py:273`(ループ本体全体で `timestamp` 系の変数名・列アクセスなし。`grep -n "timestamp" src/bot/backtest/engine.py` の当たり 0 件、2026-09-23 実測) |
| 観点 4(ルックアヘッド防止) | 構造化されている。ドキュメント化された設計: 「The strategy at bar i sees candles[0..i] only (an expanding slice)」 | `src/bot/backtest/engine.py:3-4`(docstring)。実装は `src/bot/strategy/base.py:30-35`(`Strategy` の docstring と `on_candles` の契約) |
| 観点 5(同時刻順序) | 「同時刻」という概念自体が無い(足単位・位置インデックスのため、同一タイムスタンプの複数事象という状況が構造上発生しない。裏を返せば tie-break 規則も存在しない) | `src/bot/backtest/engine.py:273`(ループの型自体に同時刻の概念なし) |
| 観点 6(戦略 API) | 事象ごとのコールバックは `on_candles` 1 本のみ。発注・取消を戦略が明示的に呼ぶ API は無い(`Signal` を返すだけで、約定判定は engine 側が行う) | `src/bot/strategy/base.py:46`(`on_candles` 抽象メソッド)、`src/bot/strategy/base.py:15-19`(`SignalType` は BUY/SELL/CLOSE/HOLD の決定型であり、発注/取消 API ではない) |
| 観点 7(拡張口) | 費用は `CostModel` として分離されている(部分的に拡張口あり)。約定模型は engine 内にハードコードで段 1 相当(自ら「楽観的」と明記)。遅延模型・口座モデルの独立した差し替え口は無い | `src/bot/backtest/engine.py:99-118`(`CostModel`)、`src/bot/backtest/engine.py:45-53`(maker 約定の docstring、「optimistic」の自己申告) |

---

## リードに聞くこと

なし(この文書は §3「要件と判定の固定」の資料づくりのみで、判断が要る分岐には未到達)。
