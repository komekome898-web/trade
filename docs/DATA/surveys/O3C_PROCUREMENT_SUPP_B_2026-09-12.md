# O-3c 調達票 補遺B — 建玉・価格ごとの約定量・L/S比・Gate 1分足の代替(2026-09-12)

需要: O-3c(強制決済フローの直接観測)の補遺B。オーナーの問い「価格ごとの約定履歴の積み上げから、
どの価格帯で清算が起きるかを予測できるか」に必要な入力データの調達。
(B1) 建玉(OI)履歴 / (B2) 価格ごとの約定量の材料 / (B3) レバレッジ分布・L/S比の履歴 /
(B4) Gate 1分足の代替経路。

**前提として読んだもの**: `docs/DATA/surveys/LIQUIDATION_HISTORY_SURVEY.md`、
`docs/DATA/surveys/O3C_PROCUREMENT_2026-09-12.md`、`docs/DATA.md` §2。**既知事項は繰り返さない**。
本票は差分(未確認だった経路の実測・新たに判明した経路)のみを追加する。

プローブの生ログ: `docs/DATA/probes/20260912_o3c_supp_b_oi_vap_gate1m.log`(~~63~~→61 エントリ(訂正 2026-09-13、検収§2、`grep -c`実測)、方法・URL・
HTTP コード・バイト数・先頭200文字・UTC時刻)。方法はすべて GET。この環境の egress からの実測
(`$HTTPS_PROXY` 経由の curl)。うち 1 件(Gate `contract_stats` limit=2000 の確認)は約1.2MBの応答
だったが単発リクエストで一括ダウンロードではない。

---

## 0. 前回調査からの差分(要点)

| # | 差分 | 印 |
|---|---|---|
| 1 | **Binance Vision の `metrics`(UM/CM とも)は `liquidationSnapshot` とは別系統のアーカイブで、現在も配信が続いている。** UM(BTCUSDT)は **2020-09-01〜**、CM(BTCUSD_PERP)は **2021-07-08〜**、ともに 2026-09-01 時点でも存在を確認(現在まで継続中と推定)。列は `create_time,symbol,sum_open_interest,sum_open_interest_value,count_toptrader_long_short_ratio,sum_toptrader_long_short_ratio,count_long_short_ratio,sum_taker_long_short_vol_ratio`(**OI とロング/ショート比が同じ行に同居**)。粒度は**5分**(1日ファイルに288行、UM実測ではタイムスタンプに重複行あり=288ユニーク、CMは重複なし288行) | 事実(実測) |
| 2 | **Gate.io の `futures/usdt/contract_stats` エンドポイントが `interval=1m` を受け付け、実データを返す。** `candlesticks`(前回票で5〜8日の壁を確認)とは別のエンドポイントで、**1分粒度で少なくとも179日前まで実測で遡れ**、180日を超えるリクエストは明示的に `"message":"from time exceeds 180-day limit"` で拒否される(=**保持期間180日が一次資料的に確定**)。清算窓(2026-06-10〜09-08、最大94日前)を**十分にカバーする**。ただし返るのは `mark_price`(単一値)であり OHLC/出来高ではない(下記§4参照) | 事実(実測) |
| 3 | **OKX `rubik/stat/contracts/open-interest-history` の保持期間を自前記録ではなく公式REST自体で実測**: `period=5m` は **3日前は取得可・7日前は空**(境界3〜6日)、`period=1H` は **30日前は取得可・60日前は空**(境界30〜59日)。`docs/DATA.md` の自前記録の欠測観察(5m:2〜3日、1H:30日)と**符合**(裏付けが取れた、新規判明ではなく確認) | 事実(実測) |
| 4 | **OKX `rubik/stat/contracts/long-short-account-ratio` は保持期間が OI history よりずっと短い**: `period=5m` は **1日前まではOK、2日前以降は `code:50030 "Illegal time range"`**(境界1〜2日)。`period=1D` は **90日前まで `code:0` で確認**(上限は未特定、それ以上は未試行) | 事実(実測) |
| 5 | **Binance COIN-M の `aggTrades` と `trades`(生の1件ごと約定)アーカイブは、清算アーカイブ(liquidationSnapshot)と同じ期間(2023-06-25〜2024-10-14)を両端とも実在確認**。さらに両方とも 2020-08-11 まで遡れる(aggTrades の最古キーで確認)。liquidationSnapshot は2024-10-14で配信終了しているが、**aggTrades/trades がその後も続くかは未確認**(今回は期間の両端の存在確認のみ、直近日は未チェック) | 事実(実測) |
| 6 | **CryptoCompare(現 CoinDesk Data)の無料匿名 histominute は鍵必須化されている**(`HTTP 401 "API key required...developers.coindesk.com"`)。Gate 1分足の第三者代替として試したが、無鍵では不可 | 事実(実測) |
| 7 | **Bybit `v5/market/open-interest` はこの環境から HTTP 403(CloudFront地域ブロック)**。既知の Bybit REST 地域ブロックパターン(既報)と同一の壁で、OI 専用の別の壁ではない | 事実(実測) |
| 8 | **BitMEX `instrument` の `openInterest` は現在値スナップショット1点のみ**(パラメータで過去日を指定する術がAPIに無い)。BitMEX公開アーカイブ(`porl/quote/trade`の3フォルダのみ、既報)にもOI専用フォルダは無い | 事実(実測+既報の確認) |

---

## 1. 需要 (B1): 建玉(OI)履歴 — 取引所ごとの経路

固定カテゴリ: この環境 / オーナーPC / 公開アーカイブ・API / 第三者データ / 有料

### 1.1 Binance(USDT-M / COIN-M)

| カテゴリ | 経路 | 結果 |
|---|---|---|
| この環境 | `fapi.binance.com/futures/data/openInterestHist` 等の REST | **試行して不可(HTTP 451、地域制限。方法: GET、実測 2026-09-12、既知パターンの再確認)** |
| オーナーPC | 同上 REST | PC での到達確認が必要(未試行) |
| 公開アーカイブ・API | **Binance Vision `data/futures/{um,cm}/daily/metrics/<SYMBOL>/`** | **取得済み範囲を実測**: UM(BTCUSDT)**2020-09-01〜**、CM(BTCUSD_PERP)**2021-07-08〜**、ともに2026-09-01時点で存在(継続中と推定)。**5分粒度**、鍵不要。サンプル1件ずつ解凍し列を確認(`sum_open_interest`列あり、§0-1参照) |
| 第三者データ | Coinalyze(既報、鍵取得済みか未確認)、CoinGlass(鍵必須) | 既報どおり未確認(本票では再試行していない) |
| 有料 | Kaiko / Amberdata 等 | 未試行 |

### 1.2 OKX

| カテゴリ | 経路 | 結果 |
|---|---|---|
| この環境 | `www.okx.com/api/v5/rubik/stat/contracts/open-interest-history` | **実測**: `period=5m` は3日前まで(7日前は空)、`period=1H` は30日前まで(60日前は空)。鍵不要 |
| オーナーPC | 同上 | 到達性は既に確認済み(既報) |
| 公開アーカイブ・API | 自前記録済み(`backtest_data/auto_okx_open_interest_5m_*`、既報)。公式バルクアーカイブは無し(未確認・未探索) | 既報のとおり |
| 第三者データ | Coinalyze / CoinGlass | 未試行(既報のまま) |
| 有料 | 同上 | 未試行 |

### 1.3 Gate.io

| カテゴリ | 経路 | 結果 |
|---|---|---|
| この環境 | `api.gateio.ws/api/v4/futures/usdt/contract_stats?contract=BTC_USDT&interval={1m,5m,1h,...}` | **実測**: `open_interest` 列を含み、**1分粒度で179日前まで実データ取得を確認、180日超は明示エラーで拒否**(§0-2参照)。鍵不要 |
| オーナーPC | 同上 | 該当なし(この環境で完結、PC確認は不要) |
| 公開アーカイブ・API | 静的アーカイブは未探索(本票では検索していない、Binance Vision 型のS3公開バケットが存在するかは**未確認**) | 未確認(試行していない) |
| 第三者データ | Coinalyze(既報)、CoinGlass(鍵必須) | 未試行 |
| 有料 | 同上 | 未試行 |

### 1.4 Bybit

| カテゴリ | 経路 | 結果 |
|---|---|---|
| この環境 | `api.bybit.com/v5/market/open-interest` | **試行して不可(HTTP 403、CloudFront地域ブロック。方法: GET、実測 2026-09-12)** |
| オーナーPC | 同上 | PC での到達確認が必要(未試行。既報の Bybit REST 200 事例から通る可能性が高いが本エンドポイント個別には未確認) |
| 公開アーカイブ・API | `public.bybit.com` に OI 専用フォルダ無し(既報の清算調査時の一覧で確認済み、5フォルダの中に該当なし。本票では再確認していない) | 該当なし(既報) |
| 第三者データ | Coinalyze / CoinGlass | 未試行 |
| 有料 | 同上 | 未試行 |

### 1.5 BitMEX

| カテゴリ | 経路 | 結果 |
|---|---|---|
| この環境 | `www.bitmex.com/api/v1/instrument?symbol=XBTUSD&columns=openInterest,timestamp` | **実測**: 現在値スナップショット1点のみを返す(過去日指定パラメータが公式APIに存在しない構造上の制約)。REST自体は200・鍵不要 |
| オーナーPC | 同上 | 該当なし(構造上の制約は経路と無関係) |
| 公開アーカイブ・API | `public.bitmex.com`(S3)に `porl/quote/trade` の3フォルダのみ(既報)。OI専用フォルダ無し | **試行して不可(ディレクトリ一覧に該当なし、既報の再掲。本票では再確認していない)** |
| 第三者データ | Coinalyze / CoinGlass | 未試行 |
| 有料 | 同上 | 未試行 |

### 1.6 (B1) 総括表

| 取引所 | OI履歴が届く経路 | 粒度 | 遡れる深さ【実測】 |
|---|---|---|---|
| Binance UM/CM | Binance Vision `metrics`(鍵不要) | 5分 | UM 2020-09-01〜、CM 2021-07-08〜(ともに継続中と推定) |
| OKX | `rubik/open-interest-history` REST(鍵不要) | 5分/1時間等 | 5分=約3〜6日、1時間=約30〜59日(自前記録の既知値と符合) |
| Gate | `contract_stats` REST(鍵不要) | **1分**(5m/1h等も可) | **179日前まで実測、180日が保持上限(一次資料的に確定)** |
| Bybit | 無し(無料、この環境からは403) | — | オーナーPCでの確認が必要 |
| BitMEX | 無し(現在値のみ) | — | 構造上不可能(過去日指定手段が無い) |

---

## 2. 需要 (B2): 価格ごとの約定量(volume at price)の材料

| 取引所 | 経路 | 結果 |
|---|---|---|
| Binance COIN-M(BTCUSD_PERP) | Binance Vision `data/futures/cm/daily/{aggTrades,trades}/BTCUSD_PERP/` | **実測**: 清算アーカイブと同じ期間の両端(2023-06-25、2024-10-14)で `aggTrades`・`trades` とも実在確認。さらに最古は2020-08-11まで遡れる(aggTrades確認)。鍵不要。**清算個別履歴(1件ごと)と1件ごと約定の両方が同一期間で揃う**ため、価格帯ごとの出来高集計はこの期間内で構築可能 |
| Binance USD-M(BTCUSDT) | 同種アーカイブ | 未試行(本票では対象外、既知: 別期間で取得済み、`docs/DATA.md` L79) |
| Bybit | `public.bybit.com/trading/BTCUSDT/`(既報、2020-03-25〜、清算フラグ無し) | 既報のとおり(価格・出来高列はあるため volume-at-price 自体には使える。本票では再確認していない) |
| OKX | 公式バルクトレードアーカイブ | **未確認**(前回票で推測パスが404だったのみで正しいURLを特定できていない。本票でも再探索していない) |
| 第三者データ | Tardis.dev(有料、既報にメタデータ到達のみ) | 未試行 |
| 有料 | Kaiko / Amberdata | 未試行 |

---

## 3. 需要 (B3): レバレッジ分布・ロング/ショート比の履歴

| 経路 | 結果 |
|---|---|
| Binance REST(`globalLongShortAccountRatio` 等) | **試行して不可(HTTP 451、地域制限。方法: GET、実測 2026-09-12)**。オーナーPCでの確認が必要(未試行) |
| **Binance Vision `metrics`** | **実測で同等列を確認**: `count_toptrader_long_short_ratio`, `sum_toptrader_long_short_ratio`, `count_long_short_ratio`, `sum_taker_long_short_vol_ratio` が **OIと同じCSVに同居**。範囲は§1.1と同じ(UM 2020-09-01〜、CM 2021-07-08〜)、5分粒度 |
| OKX `rubik/long-short-account-ratio` | **実測**: `period=5m` は保持期間が非常に短い(1日前OK、2日前以降 `code:50030 Illegal time range`)。`period=1D` は少なくとも90日前までOK(上限未特定) |
| Gate `contract_stats` | `lsr_taker`(テイカーL/S比)・`lsr_account`(アカウントL/S比)・`top_lsr_size`/`top_lsr_account`(上位トレーダーL/S比、サイズ・口座数ベース)を**1分粒度で179日分**含む(§1.3のOIと同一エンドポイント・同一深さ) |
| Bybit / BitMEX | 未試行(この環境からBybitは403の壁に阻まれると推定、既報の地域ブロックパターンと同一と考えられるが本エンドポイント個別には未確認) |
| 第三者データ・有料 | Coinalyze(既報)、CoinGlass(鍵必須) | 未試行 |

**レバレッジ分布そのもの(建玉の証拠金倍率別内訳)を直接返す無料APIは、本票で確認した範囲では見つかっていない**(L/S比・上位トレーダー比が代理指標として存在するのみ)。これは「無い」ではなく**未確認**(専用の検索を行っていない)として扱う。

---

## 4. 需要 (B4): Gate.io 1分足の代替経路

前回票で確定: `futures/usdt/candlesticks` は約5〜8日より前に "Candlestick too long ago" で400。
清算窓90日(2026-06-10〜09-08)には遠く及ばない。

| カテゴリ | 経路 | 結果 |
|---|---|---|
| この環境(別エンドポイント) | **`futures/usdt/contract_stats?interval=1m`** | **実測で解決**: `candlesticks` とは別のエンドポイントで、`mark_price` を含む1分粒度のレコードを**少なくとも179日前まで**取得できることを実測(清算窓の最古 2026-06-10 = 94日前を余裕でカバー)。180日を超えると明示的にエラーで拒否される。**ただし `mark_price` は各分の単一値であり、OHLC(始値/高値/安値/終値)でも出来高でもない**(candlestickの代替として使う場合、値動きの「点」は追えるが「レンジ」と「出来高」は失う)。1リクエストあたり実測で約1,990件返る(`limit=2000`指定時)ため、90日×1分=約129,600点を得るには**約65リクエストの分割取得が必要**(レート制限は本票では未測定) |
| この環境(`interval`違い) | `contract_stats` の `5m/1h` 等、同じ180日窓 | 実測で同じ180日の壁(§1.3)。1分より粗い粒度でも深さは同じ180日 |
| 公開アーカイブ | Binance Vision型のGate公式静的アーカイブ | **未確認**(本票では探索していない。存在有無ともに不明) |
| 第三者データ | CryptoCompare(現CoinDesk Data)`histominute`(`e=gateio`) | **試行して不可(HTTP 401、鍵必須。方法: GET、実測 2026-09-12)**。無料匿名アクセスは廃止されている |
| 第三者データ(未試行) | Kaiko / Amberdata / Tardis.dev の Gate.io データセット | 未試行(有料・鍵前提のため) |
| オーナーPC | 同じ `contract_stats` REST | 該当なし(この環境で完結、地域制限の壁が無いエンドポイントのため PC 確認は不要と考えられるが、未検証) |

**結論**: Gate自身の90日窓に対応する1分粒度データは、`candlesticks`ではなく**`contract_stats`(mark_price、OHLCではない)経路で確保できる**ことを実測で確認した。真のOHLC 1分足(出来高付き)が必要な場合はこの代替では満たせない。

---

## 5. `docs/DATA.md` に追記する行の案(未マージ。リード検収待ち)

| 資産 | 所在 | 範囲 | 状態 | 最終確認日 | プローブのログ | 使った単位 |
|---|---|---|---|---|---|---|
| Binance Vision metrics(OI+L/S比、UM/CM) | `https://data.binance.vision/data/futures/{um,cm}/daily/metrics/{BTCUSDT,BTCUSD_PERP}/` | UM 2020-09-01〜、CM 2021-07-08〜(ともに2026-09-01時点で存在確認、5分粒度) | 未試行(到達性・1件サンプルDLのみ確認、本体一括取得は未実施) | 2026-09-12 | `docs/DATA/probes/20260912_o3c_supp_b_oi_vap_gate1m.log` | 未使用 |
| Binance COIN-M aggTrades/trades(BTCUSD_PERP、清算窓対応期間) | `https://data.binance.vision/data/futures/cm/daily/{aggTrades,trades}/BTCUSD_PERP/` | 2020-08-11〜(2023-06-25・2024-10-14の存在を個別確認、清算窓と一致) | 未試行(到達性のみ確認、本体未取得) | 2026-09-12 | `docs/DATA/probes/20260912_o3c_supp_b_oi_vap_gate1m.log` | 未使用 |
| OKX rubik open-interest-history(REST) | `https://www.okx.com/api/v5/rubik/stat/contracts/open-interest-history` | 5m=約3〜6日、1H=約30〜59日(自前記録と符合) | 未試行(REST到達性・境界のみ実測、本体保存は自前記録で別途継続中) | 2026-09-12 | `docs/DATA/probes/20260912_o3c_supp_b_oi_vap_gate1m.log` | 未使用 |
| OKX rubik long-short-account-ratio(REST) | `https://www.okx.com/api/v5/rubik/stat/contracts/long-short-account-ratio` | 5m=約1〜2日のみ、1D=少なくとも90日(上限未特定) | 未試行(境界のみ実測) | 2026-09-12 | `docs/DATA/probes/20260912_o3c_supp_b_oi_vap_gate1m.log` | 未使用 |
| Gate contract_stats(OI・L/S比・mark_price、1分粒度) | `https://api.gateio.ws/api/v4/futures/usdt/contract_stats?contract=BTC_USDT&interval=1m` | 直近〜179日前(180日が保持上限、一次資料的に確定) | 未試行(到達性・境界・サンプルのみ確認、90日分の一括取得は未実施) | 2026-09-12 | `docs/DATA/probes/20260912_o3c_supp_b_oi_vap_gate1m.log` | 未使用 |
| Bybit v5 open-interest(REST) | `https://api.bybit.com/v5/market/open-interest` | 該当なし | **試行して不可(HTTP 403、CloudFront地域ブロック。方法: GET、実測 2026-09-12)** | 2026-09-12 | `docs/DATA/probes/20260912_o3c_supp_b_oi_vap_gate1m.log` | 未使用 |
| BitMEX instrument openInterest | `https://www.bitmex.com/api/v1/instrument` | 該当なし(現在値1点のみ、過去日指定不可) | **試行して不可(API構造上、過去日を指定する手段が無い。方法: GET、実測 2026-09-12)** | 2026-09-12 | `docs/DATA/probes/20260912_o3c_supp_b_oi_vap_gate1m.log` | 未使用 |
| CryptoCompare(CoinDesk Data) histominute(gate.io) | `https://min-api.cryptocompare.com/data/v2/histominute?e=gateio` | 該当なし | **試行して不可(HTTP 401、鍵必須。無料匿名アクセスは廃止。方法: GET、実測 2026-09-12)** | 2026-09-12 | `docs/DATA/probes/20260912_o3c_supp_b_oi_vap_gate1m.log` | 未使用 |

---

## 6. 「取れない」と書いた項目の一覧(範囲・方法・ログの再掲)

CLAUDE.md §5.2 / research-squad SKILL §3 の規則により、本票で「試行して不可」とした全項目を再掲する
(範囲・方法は各項目に明記済み。ログはすべて `docs/DATA/probes/20260912_o3c_supp_b_oi_vap_gate1m.log`)。

1. Binance `futures/data/globalLongShortAccountRatio` 等の REST — この環境から HTTP 451(地域制限、既知パターンの再確認)。オーナーPC未試行。
2. Bybit `v5/market/open-interest` — この環境から HTTP 403(CloudFront地域ブロック、既知パターン)。オーナーPC未試行。
3. BitMEX `instrument` の OI — 過去日を指定する手段がAPI自体に無い(構造上の制約、経路とは無関係)。
4. CryptoCompare(CoinDesk Data)`histominute`(gate.io)— HTTP 401(鍵必須、無料匿名アクセス廃止)。

上記以外(OKXの各種保持期間の「境界より先が空」、Binance Vision UMのliquidationSnapshot等)は
**前回票までに既報**のため本票では「取れない」の新規項目として数えていない。

---

## 7. 判定はしていない

本票はデータの当否・戦略への使えなさを判定していない(research-squad SKILL §2 の禁止事項)。
上記はすべて到達性・範囲・粒度の実測であり、O-3c の機構仮説の成否とは無関係である。

## 8. 未完了・積み残し(次回に回すもの)

予算内で完了。ただし以下は**未確認のまま**残っている(「取れない」ではなく「探していない」):
- OKXの公式バルクトレードアーカイブの正しいURL(推測パスの404のみ、既報から変化なし)
- Gate.io自身にBinance Vision型の静的アーカイブがあるか
- レバレッジ分布(証拠金倍率別の建玉内訳)そのものを返す無料API
- Bybit `v5/market/open-interest` のオーナーPCからの到達性(個別エンドポイントとしては未実測)
- Gate `contract_stats` のレート制限(90日分・約65リクエストを連続実行した場合の挙動)
