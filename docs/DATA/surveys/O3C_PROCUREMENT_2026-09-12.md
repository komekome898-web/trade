# O-3c 調達票 — 強制決済フローの個別履歴 + 突き合わせ用 1 分足(2026-09-12)

需要: O-3c(強制決済フローの直接観測 → bitFlyer FX_BTC_JPY の戻り、`docs/STRATEGY_IDEAS.md` O-3c/O-6)の
1 段目に必要な (a) 海外高レバ取引所の清算イベント個別履歴、(b) 同期間の 1 分足、(c) 清算の時刻精度。

**前提として読んだもの**: `docs/DATA/surveys/LIQUIDATION_HISTORY_SURVEY.md`(2026-09-08、全経路実測)、
`docs/DATA/surveys/LIQUIDATION_FEED_REACHABILITY.md`(2026-09-08〜09、オーナー PC 実測)、`docs/DATA.md` §2。
**既知事項は繰り返さない**。本票は差分(未確認だった経路の実測・新たに判明した経路)のみを追加する。

プローブの生ログ: `docs/DATA/probes/20260912_o3c_liquidation_history.log`(89 行、方法・URL・HTTP コード・
バイト数・先頭200文字・UTC時刻)。方法はすべて GET(HEAD は使っていない)。この環境の egress からの実測。

---

## 0. 前回調査からの差分(要点)

| # | 差分 | 印 |
|---|---|---|
| 1 | **Binance COIN-M(dapi)の `liquidationSnapshot` は Binance Vision に実在する**(前回は UM/BTCUSDT の 1 経路だけを見て「配布していない」と一般化していた)。**1 件ごと**、鍵不要、2023-06-25〜2024-10-14(約 16 か月)。UM は今回も全シンボル・全期間で KeyCount=0 を再確認 | 事実(実測) |
| 2 | **Gate.io の 1 分足 REST(`futures/usdt/candlesticks`)は「too long ago」エラーで約 5〜8 日より前に遡れない**(from/to 指定でも)。清算履歴(90 日)よりずっと浅い | 事実(実測) |
| 3 | **OKX の 1 分足(`history-candles`)は少なくとも 2020-01-01 まで遡れ、2019-10-01 では空**(境界は 2019-10〜2020-01 の間、これ以上は絞っていない) | 事実(実測、範囲は概算) |
| 4 | **BitMEX の清算(Liquidation)WS/REST オブジェクトには時刻フィールドが無い**(公式 swagger 定義で確認: `orderID/symbol/side/price/leavesQty` のみ)。時刻は受信側(recorder の `recv_us`)しか持てない | 事実(一次資料: BitMEX 公式 swagger.json) |
| 5 | **Bybit・BitMEX とも清算専用の公開バルクアーカイブは存在しない**(ディレクトリ一覧を直接確認。前回の「約定アーカイブに清算フラグが無い」よりさらに強い — そもそも清算という名のフォルダ自体が無い) | 事実(実測) |
| 6 | **CoinGlass に個別イベント清算エンドポイント(`/api/futures/liquidation/order`)が存在するが鍵必須**(401 実測)。深さは鍵を取らないと不明 | 事実(到達性)/推定(深さ) |

---

## 1. 需要 (a): 清算イベント個別履歴 — 取引所ごとの経路

固定カテゴリ: この環境 / オーナー PC / 公開アーカイブ・API / 第三者データ / 有料

### 1.1 Binance(USDT-M / COIN-M)

| カテゴリ | 経路 | 結果 |
|---|---|---|
| この環境 | `fapi.binance.com/fapi/v1/allForceOrders`, `dapi.binance.com/dapi/v1/allForceOrders` | **試行して不可(HTTP 451、地域制限。方法: GET、実測 2026-09-12)**。ログ: 本票冒頭のログ 1〜2 行目。オーナー PC からは fapi REST が 200 と既報(`LIQUIDATION_FEED_REACHABILITY.md` L-032)なので dapi 側もオーナー PC で測り直す価値がある(**未試行、PC での到達確認が必要**) |
| オーナー PC | 同上 REST。過去に fapi 200 を確認済みだが `allForceOrders` 自体(限定的な直近ウィンドウのみ返す仕様)はオーナー PC でも未実測 | PC での到達確認が必要 |
| 公開アーカイブ・API | **Binance Vision `data/futures/cm/daily/liquidationSnapshot/<SYMBOL>/`**(COIN-M のみ) | **取得済み範囲を実測**: `BTCUSD_PERP-liquidationSnapshot-YYYY-MM-DD.zip`(CSV、1 件ごと、鍵不要)。**2023-06-25〜2024-10-14** が存在(2024-10-14 が最後に存在した日、2024-10-15 以降は KeyCount=0)。**2024-06-01 のみ単発欠測**(前後は存在)。**UM(USDT-M)の同アーカイブは全シンボル・全期間で KeyCount=0**(`BTCUSDT`・root とも再確認)。サンプル1件(`2023-06-25.zip`, 1733 bytes)を解凍し中身を確認: `time(ms),side,order_type,time_in_force,original_quantity,price,average_price,order_status,last_fill_quantity,accumulated_fill_quantity` — **1 件ごとの強制決済(force order)そのもの** |
| 第三者データ | CoinGlass(個別イベント `liquidation/order` エンドポイント、鍵必須)、Tardis.dev(取引所別データセットに liquidation が含まれるか未確認) | CoinGlass: **試行して不可(~~HTTP 401~~→HTTP 200(本文JSONが`{"code":"401","msg":"API key missing."}`)、鍵必須。方法: GET、実測 2026-09-12)**(訂正 2026-09-13、検収§2)。深さ不明。Tardis: 未試行(`DATA.md` にメタデータ到達のみの既存記録あり) |
| 有料 | CoinGlass 有料プラン(鍵で解放される可能性)、Kaiko / Amberdata 等の機関向けティックデータ | 未試行(価格・契約が必要。ドキュメントの存在のみ確認: `docs.coinglass.com/reference/liquidation-order` に到達、200) |

**Binance の結論(この段では)**: **COIN-M(dapi、BTCUSD_PERP)は Binance Vision で 2023-06-25〜2024-10-14 の約 16 か月分を 1 件ごと・鍵不要で取得できる。USD-M(fapi、BTCUSDT)はこの経路では過去分ゼロ**(ライブ WS のみ、`data/liquidations` 記録開始 2026-09-08 以降しか存在しない、既報どおり)。

### 1.2 Bybit

| カテゴリ | 経路 | 結果 |
|---|---|---|
| この環境 | `api.bybit.com/v5/*` | **試行して不可(HTTP 403、CloudFront 地域ブロック。方法: GET、実測 2026-09-12 で再確認)**。オーナー PC からは 200 と既報 |
| オーナー PC | 同上。清算の個別履歴 REST エンドポイント自体が公式に存在するか(v5 に `market/recent-trade` 等はあるが「清算履歴」専用 REST は無い)は未確認 | PC での到達確認が必要 |
| 公開アーカイブ・API | `public.bybit.com/` ディレクトリ一覧を実測: `kline_for_metatrader4/`, `premium_index/`, `spot_index/`, `trading/`, `spot/` の 5 フォルダのみ。**「清算」名のフォルダは存在しない**(前回調査の「約定アーカイブに清算フラグが無い」をさらに裏付け、清算専用配布そのものが無いと確認) | 試行して不可(ディレクトリ一覧に該当なし。方法: GET、実測 2026-09-12) |
| 第三者データ | CoinGlass(`exchange=Bybit` を指定できる想定、鍵必須)、Coinalyze(集計値、既知) | CoinGlass: 上記と同じ 401。個別未確認 |
| 有料 | 同上(Kaiko 等) | 未試行 |

**Bybit の結論**: 個別履歴の無料経路は無い(この環境・公開アーカイブとも)。ライブ WS 記録(2026-09-08〜)より前は存在しない。

### 1.3 OKX

| カテゴリ | 経路 | 結果 |
|---|---|---|
| この環境 | `www.okx.com/api/v5/public/liquidation-orders` | 既報どおりローリング約 24 時間(再実測はしていない、前回の実測で十分と判断) |
| オーナー PC | 同上 | 既に「使える」と確認済み(`LIQUIDATION_FEED_REACHABILITY.md`) |
| 公開アーカイブ・API | OKX の公式バルクダウンロードページ(`www.okx.com/cdn/okex/traderecords/liquidation/` 等の推測パス) | **試行して不可(HTTP 404、方法: GET、実測 2026-09-12)**。正しいパスを特定できておらず、「無い」と断定はできない — **未確認**として扱う |
| 第三者データ | CoinGlass(`exchange=OKX`)、Coinalyze | 未試行(個別) |
| 有料 | 同上 | 未試行 |

**OKX の結論**: 無料の個別履歴は現状ローリング 24 時間のみ確認。公式バルクアーカイブの有無は**未確認**(推測パスが 404 だっただけで、正しい URL を特定できていない)。

### 1.4 BitMEX

| カテゴリ | 経路 | 結果 |
|---|---|---|
| この環境 | `www.bitmex.com/api/v1/liquidation` | 200 だが**現在オープンの清算注文のみ**(空配列)。履歴ではない(既報どおり、再確認済み) |
| オーナー PC | 同上 | 既に「使える」(WS)と確認済み(記録用) |
| 公開アーカイブ・API | `public.bitmex.com` の S3 REST(`s3-eu-west-1.amazonaws.com/public.bitmex.com`)を `delimiter=/` で列挙 | **試行して不可(トップレベルフォルダは `porl/`, `quote/`, `trade/` の 3 つのみ。「liquidation」名のフォルダは存在しない。方法: GET(S3 REST list-objects)、実測 2026-09-12)** |
| 第三者データ | CoinGlass(`exchange=BitMEX`) | 未試行(個別) |
| 有料 | 同上 | 未試行 |

**BitMEX の結論**: 個別履歴の無料経路は無い。加えて **BitMEX の清算メッセージ自体が取引所発の時刻を持たない**(§3 参照)ため、仮に過去ログを得ても「いつ起きたか」は受信側の記録にしか無い。**2026-09-16 に XBTUSD が上場廃止予定**(`docs/DATA.md` §9.2)なので、ライブ WS 記録も長くは続かない。

### 1.5 Gate

前回調査(`LIQUIDATION_HISTORY_SURVEY.md`)で確定済み: `GET /api/v4/futures/usdt/liq_orders` が**1 件ごと・鍵不要・ローリング約 90 日**。手元に `backtest_data/gate_liquidations_20260908/` として 2026-06-10〜09-08(79,183 件)を確保済み。本票では再測していない(差分なし)。

### 1.6 (a) の総括表(取引所 × 個別履歴が届く最長の過去)

| 取引所 | 個別履歴が届く経路 | 遡れる深さ | 状態 |
|---|---|---|---|
| **Binance COIN-M**(BTCUSD_PERP) | Binance Vision `liquidationSnapshot`(公開アーカイブ、鍵不要) | **2023-06-25〜2024-10-14 の約 16 か月**(その後は配布終了、以降はライブ WS のみ) | 未取得(この環境から到達性のみ確認。本体は小サンプル1件のみダウンロード) |
| **Binance USD-M**(BTCUSDT) | 無し(アーカイブは全期間空) | 2026-09-08〜(自前 WS 記録のみ)。ただし既報どおり `fstream` の `!forceOrder@arr` は届かない(binance_cm で代替中) | 試行して不可(アーカイブ側。方法: GET S3 list、ログ本票) |
| **Gate** | `liq_orders` REST(鍵不要) | ローリング約 90 日(動く窓) | 取得済み(90日分、`backtest_data/gate_liquidations_20260908/`) |
| **OKX** | `liquidation-orders` REST(鍵不要) | ローリング約 24 時間 | 既報のとおり(未取得の追加取得はしていない) |
| **Bybit** | 無し(無料) | 2026-09-08〜(自前 WS 記録のみ) | 試行して不可(公開アーカイブにフォルダ自体無し) |
| **BitMEX** | 無し(無料。かつ時刻フィールド自体が無い) | 2026-09-08〜(自前 WS 記録のみ、時刻は受信時刻) | 試行して不可(公開アーカイブにフォルダ自体無し) |
| 全取引所横断(有料) | CoinGlass 個別イベントエンドポイント | 未確認(鍵必須、~~401~~→HTTP 200・本文JSON `code:401`(訂正 2026-09-13、検収§2)) | 試行して不可(鍵無し。方法: GET、ログ本票) |

---

## 2. 需要 (b): 同期間の 1 分足(OKX・Gate・BitMEX の有無確認)

| 取引所 | 経路 | 遡れる深さ【実測】 | 状態 |
|---|---|---|---|
| **OKX** | `GET /api/v5/market/history-candles?instId=BTC-USDT-SWAP&bar=1m`(鍵不要) | **2020-01-01 には存在、2019-10-01 には存在しない**(境界は 2019-10〜2020-01 の間、これ以上絞っていない)。現在まで連続(現行 `market/candles` と接続) | 未取得(到達性・範囲のみ確認。本体未ダウンロード) |
| **Gate** | `GET /api/v4/futures/usdt/candlesticks?contract=BTC_USDT&interval=1m`(鍵不要) | **約 5〜8 日より前は "Candlestick too long ago. Maximum 10000 points recently are allowed" で 400**(from/to を過去に振っても同じ)。**清算履歴(90日)よりずっと浅い** | 試行して不可(この分解能でこの窓を超えて遡る経路は本 API には無い。方法: GET、境界を 5日/8日/10日/15日/30日で実測、ログ本票) |
| **BitMEX** | `GET /api/v1/trade/bucketed?binSize=1m&symbol=XBTUSD`(鍵不要) | **2017-01-01 で実データ確認**(手元の 1 秒足アーカイブ 2017〜2021 と重なる区間)。取引所発足はさらに前(2016)だが本票では未確認 | 手元に代替あり(`backtest_data/bitmex_trade_1s_XBTUSD/`、2017〜2021、1 秒足から 1 分足を再構成可能。API 自体も生きている) |

**含意(推定)**: Gate の清算履歴(90日)と Gate 自身の 1 分足 REST(5〜8日)は**深さが逆転している**。Gate の清算窓 90 日ぶんに対応する自市場 1 分足は、この REST からは取れない。**bitFlyer 側の 1 分足(2015〜2026)と突き合わせるだけなら bitFlyer 側は足りているが、Gate 自身の値動きを 1 分足で見たい場合は 90 日分を別経路(自前記録の継続、または Gate の他エンドポイント)で確保する必要がある**(本票では Gate の代替 1 分足経路までは調べていない — 未確認)。

---

## 3. 需要 (c): 清算イベントの時刻精度

| 取引所 | フィールド | 精度【実測/一次資料】 | bitFlyer 1 分足との突き合わせに十分か |
|---|---|---|---|
| **Gate**(`liq_orders`) | `time` | **秒**(10 桁 Unix epoch、例 `1788883066`) | 十分(1 分足の分解能に対して過剰なほど細かい必要はないが、秒単位なら分の境界は一意に決まる) |
| **Binance COIN-M アーカイブ**(`liquidationSnapshot`) | `time` | **ミリ秒**(13 桁、例 `1687656471926`) | 十分 |
| **Binance ライブ WS**(`forceOrder`) | `T`(注文時刻)/`E`(イベント時刻) | **ミリ秒**(実測サンプルで確認) | 十分 |
| **OKX**(`liquidation-orders`) | `details[].ts` | **ミリ秒**(13 桁、実測サンプルで確認) | 十分 |
| **Bybit**(`allLiquidation`) | `data[].T` | **ミリ秒**(13 桁、実測サンプルで確認) | 十分 |
| **BitMEX**(WS `liquidation` テーブル / REST `/liquidation`) | **無し** | **取引所発の時刻フィールドが存在しない**(一次資料: BitMEX 公式 `swagger.json` の `Liquidation` モデル定義。プロパティは `orderID, symbol, side, price, leavesQty` のみ、`required: [orderID]`)。当リポジトリの記録器が付ける `recv_us`(受信時刻、マイクロ秒)が唯一の時刻 | **不十分・要注意**: 受信時刻は取引所の約定時刻ではなく、ネットワーク遅延・記録器の処理遅延を含む。1 分足との突き合わせで「その分に起きた」と言うには**受信遅延の分だけ誤差がありうる**(具体的な遅延の大きさは未測定 — `data/latency/ws_vm.csv` は 1 回 9.6 分間のみで一般化不可、`docs/DATA.md` §8 損失14に既出) |

**総括**: Gate・Binance・OKX・Bybit は**すべて実測でミリ秒または秒精度**を確認しており、bitFlyer 1 分足(分解能 1 分)との突き合わせには十分。**BitMEX だけは取引所発の時刻情報がそもそも存在しない**構造的な制約で、受信時刻での代用は分単位の誤差を持ちうる(未測定)。これは経路の問題ではなく BitMEX の API 設計そのものである。

---

## 4. `docs/DATA.md` に追記する行の案(未マージ。リード検収待ち)

### §2(海外暗号資産)への追記候補

| 資産 | 所在 | 範囲 | 状態 | 最終確認日 | プローブのログ | 使った単位 |
|---|---|---|---|---|---|---|
| Binance COIN-M 個別清算(liquidationSnapshot、公開アーカイブ) | `https://data.binance.vision/data/futures/cm/daily/liquidationSnapshot/BTCUSD_PERP/` | 2023-06-25〜2024-10-14(約16か月、2024-06-01のみ単発欠測、以降は配布終了) | 未試行(到達性・1件のサンプルDLのみ確認。本体一括取得は未実施) | 2026-09-12 | `docs/DATA/probes/20260912_o3c_liquidation_history.log` | 未使用 |
| Binance USD-M 個別清算アーカイブ(liquidationSnapshot) | `https://data.binance.vision/data/futures/um/daily/liquidationSnapshot/` | 該当なし | **試行して不可(全シンボル・全期間で KeyCount=0。方法: GET S3 list-objects、実測 2026-09-12)** | 2026-09-12 | `docs/DATA/probes/20260912_o3c_liquidation_history.log` | 未使用 |
| Bybit・BitMEX 個別清算(公開バルクアーカイブ) | `public.bybit.com/`, `public.bitmex.com/`(S3 REST) | 該当なし | **試行して不可(いずれもディレクトリ一覧に「清算」名のフォルダが存在しない。方法: GET、実測 2026-09-12)** | 2026-09-12 | `docs/DATA/probes/20260912_o3c_liquidation_history.log` | 未使用 |
| CoinGlass 個別イベント清算(`/api/futures/liquidation/order`) | `https://open-api-v4.coinglass.com/api/futures/liquidation/order` | 不明(鍵必須) | **試行して不可(~~HTTP 401~~→HTTP 200(本文JSONが`code:401`「API key missing」)。方法: GET、実測 2026-09-12。訂正 2026-09-13、検収§2)** | 2026-09-12 | `docs/DATA/probes/20260912_o3c_liquidation_history.log` | 未使用 |
| OKX 1分足(無期限、history-candles) | `https://www.okx.com/api/v5/market/history-candles?instId=BTC-USDT-SWAP&bar=1m` | 2020-01-01〜現在(2019-10-01は空、境界未特定) | 未試行(到達性・範囲のみ確認、本体未取得) | 2026-09-12 | `docs/DATA/probes/20260912_o3c_liquidation_history.log` | 未使用 |
| Gate 1分足(無期限、futures candlesticks REST) | `https://api.gateio.ws/api/v4/futures/usdt/candlesticks?contract=BTC_USDT&interval=1m` | 直近 約5〜8日のみ(それ以前は"too long ago"で400) | **試行して不可(APIの遡及上限。方法: GET、from/toを5/8/10/15/30日前で実測、実測2026-09-12)** | 2026-09-12 | `docs/DATA/probes/20260912_o3c_liquidation_history.log` | 未使用 |
| BitMEX 1分足(bucketed trade REST) | `https://www.bitmex.com/api/v1/trade/bucketed?binSize=1m&symbol=XBTUSD` | 2017-01-01に実データ確認(手元1秒足2017〜2021と重複区間あり) | 未試行(到達性のみ確認、本体は手元の1秒足から代替可能) | 2026-09-12 | `docs/DATA/probes/20260912_o3c_liquidation_history.log` | 未使用 |

### §1 または schema への追記候補(BitMEX 清算の時刻精度についての注記)

`schema/liquidations.json` の BitMEX 関連 `known_defects` に追加候補:
「BitMEX の Liquidation オブジェクト(WS/REST とも)は取引所発の時刻フィールドを持たない(一次資料: 公式 swagger.json の Liquidation モデル定義、`orderID/symbol/side/price/leavesQty` のみ)。当データセットの `recv_us` は受信時刻であり、取引所の約定時刻の代用として使う場合は受信遅延ぶんの誤差が未測定のまま残る。」

---

## 5. 「取れない」と書いた項目の一覧(範囲・方法・ログの再掲)

CLAUDE.md §5.2 / research-squad SKILL §3 の規則により、本票で「試行して不可」とした全項目を再掲する
(範囲・方法は各項目に明記済み。ログはすべて `docs/DATA/probes/20260912_o3c_liquidation_history.log`)。

1. Binance USD-M/COIN-M `allForceOrders` REST — この環境から HTTP 451(地域制限)。オーナー PC は未試行。
2. Binance Vision UM `liquidationSnapshot` — 全シンボル・全期間で KeyCount=0(公開アーカイブ側の性質、経路とは無関係)。
3. Bybit REST 全般 — この環境から HTTP 403(地域制限、既報の再確認)。
4. Bybit・BitMEX の清算専用公開バルクアーカイブ — ディレクトリ一覧にフォルダ自体が存在しない。
5. CoinGlass 個別イベント清算エンドポイント — ~~HTTP 401~~→HTTP 200(本文JSONが`code:401`)(鍵必須)(訂正 2026-09-13、検収§2)。
6. Gate 1 分足の 5〜8 日より前 — API 自体の遡及上限(400 "too long ago")。
7. OKX 公式バルクダウンロード(推測パス) — HTTP 404。ただし正しい URL を特定できていないため「無い」ではなく**未確認**として扱う(取れないの4分類には入れていない)。

---

## 6. 判定はしていない

本票はデータの当否・戦略への使えなさを判定していない(research-squad SKILL §2 の禁止事項)。
上記はすべて到達性・範囲・精度の実測であり、O-3c の機構仮説の成否とは無関係である。
