# 項目 0(核)— 要件の固定

指紋: `20260923_backtest_env_prompt.md@a723df99ad38` §3「要件と判定の固定」「調査結果の側の選び方」に従って書く。**このファイル以外は書かない。**

## 1. 委任文 §2 の項目 0 の行(逐語)

> | 0 | 核(先に単独で作る) | `src/bot/bt/core/` | 時刻は UTC の int64 ナノ秒。事象の型(約定・板の写真・板の差分・足・資金調達・清算・時計・注文の受付/拒否/約定の通知)。**戦略は「受け取れた時刻 ≤ 今」の事象しか見られない**(構造でルックアヘッドを不能にする)。決定的な事象の順序(同時刻の並びの規則を明記)。戦略の API(事象ごとの呼び出し・発注・取消)。他項目が差し込む口(約定模型・遅延模型・費用・口座) |

(委任文 `docs/DATA/delegations/20260923_backtest_env_prompt.md` 54 行目)

## 2. 比較の観点(観点ごとに 1 行、測れる形)

オーナーの完了の形「**すべてが調査結果以上の信頼性と再現性に優れたものにすること**」(委任文 §0)を軸に、項目 0 の行の各要素を測れる形に分解する。

| # | 観点 | 測れる形 |
|---|---|---|
| V1 | 時刻表現の一貫性 | 全事象の時刻が単一の型(UTC・int64・ナノ秒)で表現され、単位の混在(秒・ミリ秒・マイクロ秒・ISO 文字列)を機構(型・変換関数)で検出・拒否できるか。コード上のその箇所をファイル:行で指せるか |
| V2 | 事象型の網羅性 | 約定・板の写真・板の差分・足・資金調達・清算・時計・注文の受付/拒否/約定通知(8 種以上)を、単一の型システム(enum・dataclass 等)で列挙しているか。列挙している型の個数を数えられるか |
| V3 | ルックアヘッド不能性 | 戦略コードが「受け取れた時刻 ≤ 今」より先の事象を、規約ではなく構造(スコープ・型・引数の絞り込み)で参照不能にされているか。参照可能な抜け道の有無をコードで確かめられるか |
| V4 | 決定的な事象順序 | 同時刻に複数の事象が発生したときの並びの規則が明文化され、同じ入力を何度流しても常に同じ順序が再現するか。複数事象型が同時刻で衝突する場面を持つか(1 種類の事象しか扱わない実装は、この観点で「規則が要らない」ため測れない) |
| V5 | 戦略 API の疎結合性 | 戦略がエンジンの内部状態(口座残高・建玉・発注簿)へ直接アクセスする経路を持たず、事象ごとの呼び出し・発注・取消という決められた API だけでエンジンとやり取りするか。戦略から到達可能なエンジン内部の変数・メソッドの数を数えられるか |
| V6 | 拡張点(差し込み口)の分離 | 約定模型・遅延模型・費用・口座が、核のコードを書き換えずに差し替えられる独立した部品(インターフェース・パラメータ)として外に出ているか、それとも核の関数の中に直接書き込まれているか |

## 3. 調査結果の側

### 3.1 候補の機械抽出(該当する要素の列 = 「イベント駆動」)

項目 0(核)の内容(事象駆動アーキテクチャ・事象の型・戦略 API・ルックアヘッド不能性)に対応する道具台帳の要素の列は「イベント駆動」列である(道具台帳の 6 要素 = 足・ティック・板の待ち行列・イベント駆動・ベクトル化・市場影響と約定の模型のうち、この列だけが項目 0 の中身に対応する。列が存在するので SCAN への grep 抜き出しは行わない)。

打ったコマンド:

```
awk -F'\t' 'NR==1{for(i=1;i<=NF;i++) h[i]=$i} NR>1 && $7=="○" {print $1"\t"$2"\t段機構="$10"\t段既定="$11"\t報告書行="$17}' docs/DATA/tools_catalog.tsv
```

出力(19 件、人が足し引きしていない):

```
1	Basana	段機構=4・6	段既定=4・6	報告書行=6836
6	Ziplime	段機構=4・6	段既定=4	報告書行=9650
13	DeviaVir/zenbot	段機構=3・4	段既定=3・4	報告書行=6874
18	zipline-reloaded	段機構=4・6	段既定=4	報告書行=9857
23	hftbacktest	段機構=3・5	段既定=3・5	報告書行=6906
37	ThePredictiveDev/Automated-Financial-Market-Trading-System	段機構=5・6	段既定=5	報告書行=10426
41	prediction-market-backtesting	段機構=	段既定=	報告書行=6106
52	QuantConnect	段機構=	段既定=	報告書行=7292
53	Rqalpha	段機構=3・4	段既定=4	報告書行=7850
57	WonderTrader	段機構=3・4・5	段既定=3・4・5	報告書行=7852
58	nautilus_trader	段機構=	段既定=	報告書行=6345
61	barter-rs	段機構=	段既定=	報告書行=6926
62	qf-lib	段機構=	段既定=	報告書行=6117
63	trade-frame	段機構=3・4	段既定=3・4	報告書行=6119
65	aat	段機構=5(合成の取引所)・0(CSV の取引所)・0(IEX の取引所)	段既定=同上(既定未確認)	報告書行=10429
68	quanttrader	段機構=	段既定=	報告書行=6382
69	gobacktest	段機構=	段既定=	報告書行=6124
91	braedonsaunders/homerun	段機構=3・4・5・6	段既定=3・4・5	報告書行=7858
123	carlos8f/zenbot	段機構=3・4	段既定=3・4	報告書行=7298
```

（`docs/DATA/TOOLS_CATALOG.md` §1 の「印を持つ候補 19」と一致することを確認済み。）

**段(機構)についての限界(正直に書く)**: 「段(機構)」は道具台帳 §2.1 で「指値の埋まり方の尺度(0〜6)」として定義された、**市場影響と約定の模型(項目 3 の軸)専用の尺度**である。項目 0 の観点(V1〜V6、事象駆動アーキテクチャそのものの質)を直接測る尺度ではない。19 件のうち 段機構 が埋まっているのは 11 件(1・6・13・18・23・37・53・57・63・91・123)で、最高値は 6(候補 1・6・18・37・91)。この値は上表に機械的に載せた(指示どおり)が、**V1〜V6 の「最も高い機構」の選定根拠としては使わない**(尺度が合わない道具を無理に当てはめると弱い根拠になる)。代わりに、観点ごとに SCAN の実測(逐語)で具体的な機構を持つと分かる候補を選ぶ(3.2)。

### 3.2 観点ごとに最も高い機構(候補番号 + SCAN の行)

19 件の候補プールの中から、各観点に直接効く逐語が SCAN 報告書に見つかった候補を選ぶ。打った grep とその出力:

```
$ grep -n "deterministic event-driven architecture" docs/DATA/SCAN_2026-09-21_tools.md
6061:| 8 | **候補 58 `nautilus_trader` は、区分 1 の 6 要素のうち少なくとも 4 つを同時に持つ。**README の逐語は「**Backtesting**: Multiple venues, instruments, and strategies
 simultaneously using historical quote tick, trade tick, bar, order book, and custom data with nanosecond resolution.」で、登録情報の説明の逐語は「Production-grade
 Rust-native trading engine with deterministic event-driven architecture」である。(…) | 一次資料 | `https://raw.githubusercontent.com/nautechsystems/nautilus_trader/
develop/README.md`(2026-09-22 取得)の 60 行、`20260922_tools_1_run20.log:125`・`:113` |
```

```
$ grep -n "先読みの偏りを防ぐ道具" docs/DATA/SCAN_2026-09-21_tools.md
6118:   **刻むのは日の寄りと引けで、先読みの偏りを防ぐ道具を持つと書いている**(知見 14)。未確認: 許諾・料金・導入・最小実行・データ供給元の鍵の要否。
6154:| `qf-lib` | 日の寄りと引けをイベントとして刻み、先読みの偏りを防ぐ道具つきで検証する | 未確認(…) | **先読みの偏りを防ぐ道具**と、結果を文書にまとめる雛形 | **可**(原典に到達。導入はしていない) |
```

```
$ grep -n "約定の模型を差し替え可能な部品として外に出している" docs/DATA/SCAN_2026-09-21_tools.md
6151:| `QuantConnect/Lean` | 足とティックの両方を入力にして、約定の模型を差し替えながらイベント駆動で回す | 未確認(…) | **約定の模型を差し替え可能な部品として外に出していること**と、足とティックで約定の判定を分ける作り | **可**(原典に到達。導入はしていない) |
```

```
$ grep -n "型を持つ事象の列で駆動され" docs/DATA/SCAN_2026-09-21_tools.md
7177:| 4 | **候補 6 `Ziplime` は、型を持つ事象の列で駆動され、その事象を振り分けている。**(…)型は SimulationEvent.SESSION_START / BAR / SESSION_END など |
7180:| 7 | **候補 18 `zipline-reloaded` は、型を持つ事象の列で駆動され、その事象を振り分けている。**逐語は `for dt, action in self.clock:` と `if action == BAR:` と
`elif action == SESSION_START:` で、型は `BAR` `SESSION_START` `SESSION_END` `MINUTE_END` `BEFORE_TRADING_START_BAR` の 5 つである | 実測 | `.../src/zipline/gens/
tradesimulation.py` 取得日 2026-09-22 / `20260922_tools_1_run24.log` の `evidence_run24` の `c18` の節 |
```

観点ごとの選定:

| 観点 | 最も高い機構 | 候補番号・名前 | SCAN の行 | 根拠(逐語) |
|---|---|---|---|---|
| V1(時刻表現) | ナノ秒分解能を一次資料で明記 | 58 `nautilus_trader` | 6061 | 「with nanosecond resolution」(README) |
| V2(事象型の網羅性) | 明示的な型を持つ事象を列挙(確認できた最多 5 種) | 18 `zipline-reloaded` | 7180 | 型は `BAR` `SESSION_START` `SESSION_END` `MINUTE_END` `BEFORE_TRADING_START_BAR` の 5 つ |
| V3(ルックアヘッド不能性) | 「先読みの偏りを防ぐ道具」を明記(原典に到達済み。中身の実装までは未確認) | 62 `qf-lib` | 6118 / 6154 | 「Tools to prevent look-ahead bias in the backtesting environment.」(README、知見 14 の逐語) |
| V4(決定的な事象順序) | 「deterministic event-driven architecture」を登録情報で明記 | 58 `nautilus_trader` | 6061 | 「deterministic event-driven architecture」(登録情報の説明) |
| V5(戦略 API の疎結合性) | 直接の逐語なし(3.3 参照) | — | — | — |
| V6(拡張点の分離) | 約定模型を差し替え可能な部品として外出し | 52 `QuantConnect/Lean` | 6151 | 「約定の模型を差し替えながらイベント駆動で回す」/「約定の模型を差し替え可能な部品として外に出していること」 |

### 3.3 V5 について(正直に書く)

V5(戦略 API の疎結合性 = 戦略がエンジン内部状態に直接触れず、事象コールバック・発注・取消という決められた API だけを持つか)を直接裏付ける逐語は、今回の grep(`callback`・`on_bar`・`on_tick`・`戦略.{0,6}API`・`戦略.{0,6}インターフェース` を含む)では nautilus_trader の「Customizable: User-defined components, or assemble entire systems from scratch using the cache and message bus」(3 行目、pypi の description、根拠 `docs/DATA/SCAN_2026-09-21_tools.md:247`)以外に見つからなかった。この逐語は「戦略が発注・取消・事象購読だけに限定されているか」までは言っていない(疎結合の**保証**ではなく、部品を組み替えられるという**一般的な柔軟性**の主張)。**この観点は、19 件のどれが最も高いかを一次資料の逐語だけでは決めきれない、と正直に書く(A-18: 安全側に振れて「無い」と決めつけない代わりに、分からないことを分からないと書く)。**

## 4. 当方の現状(該当箇所をファイル:行で)

| 観点 | 当方の現状 | ファイル:行 |
|---|---|---|
| V1(時刻表現) | `candles.index`(pandas の索引)をそのまま使い、UTC・int64・ナノ秒への統一や単位検出の機構は無い(`engine.py` 内に `int64`/`ns`/`UTC` の当たりは 0 件、実測 `grep -n "int64\|UTC\|nanosecond" src/bot/backtest/engine.py` の出力なし) | `src/bot/backtest/engine.py:396`(`equity_curve = pd.Series(equity, index=candles.index)`) |
| V2(事象型の網羅性) | 事象は「足(bar)」1 種類のみ。約定・板の写真・板の差分・資金調達・清算・時計・注文の受付/拒否/約定通知の型は存在しない | `src/bot/strategy/base.py:46`(`def on_candles(self, candles: pd.DataFrame) -> Signal`) |
| V3(ルックアヘッド不能性) | 「足」という 1 種類の事象については、構造(スライス渡し)で強制している。事象が増えたときにも同じ強制が効くかは、事象が 1 種類しか無い現状のコードからは判定できない | `src/bot/backtest/engine.py:371`(`signal = strategy.on_candles(candles.iloc[: i + 1])`)、ループ本体は `src/bot/backtest/engine.py:273`(`for i in range(len(candles)):`) |
| V4(決定的な事象順序) | 事象型が「足」1 種類しか無いため、同時刻の複数事象型の並びを決める規則そのものが存在しない(規則を書く対象が無い) | `src/bot/backtest/engine.py:273`(単一の逐次ループ) |
| V5(戦略 API の疎結合性) | 戦略は `on_candles` 1 メソッドだけを持ち、口座・発注・取消には触れない設計方針は明記されている(「Strategies see candles and return a Signal. They know nothing about orders, sizes, balances or the exchange API」)が、事象ごとの呼び出し・発注・取消という複数の API には分かれていない(返り値の `Signal` 1 個で表現) | `src/bot/strategy/base.py:3-4`(モジュール docstring)、`src/bot/strategy/base.py:30-35`(`Strategy` クラス docstring) |
| V6(拡張点の分離) | `CostModel` はエンジンと同じファイルに埋め込まれた dataclass(独立インターフェースではない)。口座(`cash`・`position` 等)と約定判定(`execution: str = "taker"/"maker"` という文字列引数での分岐)は `run_backtest` 関数の内部にローカル変数・分岐として直接書かれており、差し替え可能な部品として外に出ていない。遅延模型は無い(`遅延`・`latency` に相当する概念そのものが `engine.py` に無い) | `src/bot/backtest/engine.py:99`(`class CostModel`)、`src/bot/backtest/engine.py:141`(`execution: str = "taker"`)、`src/bot/backtest/engine.py:187-188`(`cash = initial_equity_jpy` / `position = 0.0` 等のローカル変数) |
