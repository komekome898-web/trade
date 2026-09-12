# O-3c 調達票 補遺C — Hyperliquid(オンチェーン無期限DEX、BTC無期限)(2026-09-12)

需要: O-3c(強制決済フローの直接観測 → bitFlyer FX_BTC_JPY の戻り)の補遺C。Hyperliquid について
C1(清算個別履歴)・C2(1分足/約定/OI/資金調達率)・C3(清算の時刻精度・一次資料)・C4(突き合わせ用の
建玉/出来高規模)を調べる。オーナー要請(2026-09-12)。

**前提確認**: `docs/DATA/surveys/LIQUIDATION_HISTORY_SURVEY.md`(2026-09-08)、
`docs/DATA/surveys/O3C_PROCUREMENT_2026-09-12.md`、`docs/DATA.md` §2 を読んだ。Hyperliquid に関する
既存記載は「S3アーカイブは Requester Pays バケット、中身は未確認、匿名アクセスは403」の1行のみ
(`LIQUIDATION_HISTORY_SURVEY.md` L38/L73)。**本票はこれの後継として新規に調べる差分**であり、
既知事項の繰り返しはしない。

プローブの生ログ: `docs/DATA/probes/20260912_o3c_supp_c_hyperliquid.log`(方法・URL・HTTPコード・
バイト数・先頭200〜300文字・UTC時刻)。curl は `$HTTPS_PROXY` 経由、`info` エンドポイントは POST
JSON(小さいリクエストのみ)。ドキュメント確認は WebFetch。S3 は一覧のみ(オブジェクト取得なし、
requester-pays のため匿名では一覧すら不可と判明 — 詳細は §1)。

---

## 要点(先に)

| # | 要点 | 印 |
|---|---|---|
| 1 | **清算は `userFills`/`userFillsByTime`/WS `userEvents` の fill オブジェクトの `liquidation` フィールドで識別できる**(`FillLiquidation { liquidatedUser?, markPx, method: "market"\|"backstop" }`)。**ただし `trades`(WS `WsTrade` / 想定される `recentTrades`)には清算を示すフィールドが無い** — 他取引所(Bybit/BitMEX)と同型の制約 | 事実(一次資料) |
| 2 | **`candleSnapshot` は「直近5000本のみ」**(1分足なら約3.47日)。この環境からの実測でも**3日前は取得でき4日前は空**と、一次資料の宣言と整合した | 事実(一次資料+実測で一致) |
| 3 | **`userFills` は直近2000件、`userFillsByTime` も直近10000件までしか遡れない**(ページングしても壁がある) | 事実(一次資料) |
| 4 | **S3アーカイブ2種(`hyperliquid-archive`=market data、`hl-mainnet-node-data`=node data)はいずれも Requester Pays で、匿名では一覧(list)すら403**。市場データの月次アップロード頻度・欠測許容が一次資料に明記されている | 事実(一次資料+実測) |
| 5 | 清算の一次資料(維持証拠金率・清算価格式・HLP vaultバックストップ・ADL)は `hyperliquid.gitbook.io` に**別々の2ページ**に分かれて存在する(Liquidations ページに ADL の記述は無い) | 事実(一次資料) |
| 6 | **清算の時刻精度そのものを明記した一次資料は見つかっていない**(`FillLiquidation` に時刻フィールドは無く、時刻は fill オブジェクト側の `time` を使う推定)。**未確認** | 未確認 |
| 7 | C4: **info API から自分で取得した現在値**(2026-09-12 06:45 UTC)で BTC OI ≒ 35,905 BTC(≒$2.77B)、24h想定出来高 ≒ $3.58B。同時刻の OKX BTC-USDT-SWAP は OI ≒ 27,443 BTC(≒$2.12B)、24h出来高(base) ≒ 105,124 BTC。Binance/Bybit はこの環境から地域制限で直接測れない(既報) | 事実(一次観測、単一時点) |
| 8 | Hypurrscan・公式statsページはいずれも JS レンダリングの SPA で、この環境からの静的フェッチ(WebFetch)ではヘッダーしか取得できない。中身は未確認 | 事実(実測の限界) |

---

## C1. 清算イベントの個別履歴

固定カテゴリ: この環境 / オーナーPC / 公開アーカイブ・API / 第三者データ / 有料

| カテゴリ | 経路 | 結果 |
|---|---|---|
| この環境 | `api.hyperliquid.xyz/info`(POST）の `userFills` / `userFillsByTime` | **到達確認済み(HTTP 200)**。`userFillsByTime` を任意アドレスに対して実行できることを確認(1時間窓・2024年某日、対象アドレスに該当期間の fill が無かったため空配列。**エンドポイント自体は生きている**ことの確認であり、特定アドレスの清算有無は未確認)。一次資料(下記)で fill オブジェクトが `liquidation` フィールドを持つと確認したので、**清算を含むアドレスに対して呼べば個別清算を識別できる**(実際に清算を経験したアドレスでの検証はしていない — 未確認) |
| この環境 | WS `userEvents` | 未試行(WS 接続はこの環境の1回のプローブでは検証していない。ドキュメント上は `WsFill.liquidation` を持つと確認 — 一次資料で確認) |
| この環境 | `recentTrades` / WS `trades`(`WsTrade`) | **一次資料で `WsTrade` に liquidation を示すフィールドが無いと確認**。清算約定を通常約定と区別する手段がこの経路には無い(Bybit/BitMEXと同型の制約、`O3C_PROCUREMENT_2026-09-12.md` §1.2/1.4 既報と整合) |
| オーナーPC | 同上 API(REST/WS とも地域制限は今のところ確認されていない可能性が高い — bitFlyer/Binance等と異なりHyperliquidは今回この環境からも200が返ったため、地域制限の有無自体が争点にならない。念のため**PCでの到達確認は推奨**するが優先度は低い) | PCでの到達確認は可能(未実施) |
| 公開アーカイブ・API | S3 `hyperliquid-archive`(market data、`asset_ctxs/[date].csv.lz4` 等)。清算専用のパスは一次資料に明記が無い。`hl-mainnet-node-data`(node data、`node_fills_by_block`)は**全 fill を含み得る**が Hyperliquid のバリデータノードが生成するブロック単位データであり、清算 fill が識別可能な形で入っているかは一次資料に明記が無い | **試行して不可(匿名アクセス、HTTP 403 "Anonymous users cannot invoke requests against Requester Pays buckets"。方法: GET(S3 ListObjectsV2 REST)、実測 2026-09-12)**。ログ: 22〜24行目。Requester Pays を通す(AWS 認証+課金)先の中身は未確認 |
| 第三者データ | Hypurrscan(`hypurrscan.io`) — オンチェーンエクスプローラでポジション・清算を扱っていると想定される。HypurrDash も同系統 | **中身未確認**: トップページ・`/liquidations` パスとも SPA で静的フェッチはヘッダーのみ取得(JS実行後のコンテンツは取得不可)。API を推測(`api.hypurrscan.io/liquidations`)して叩いたが **HTTP 404**(正しいエンドポイント名を特定できておらず「無い」とは断定できない、**未確認**) |
| 第三者データ | Coinglass(Hyperliquid対応) | 未試行。他取引所の同種エンドポイント(`liquidation/order`)が鍵必須・401なのは既報(`O3C_PROCUREMENT_2026-09-12.md`)であり、Hyperliquid個別ページも同様の制約と推定される(未確認) |
| 第三者データ | Dune / Allium / Goldsky(オンチェーンインデクサ、Hyperliquidはオンチェーンなのでダッシュボード化が技術的に可能) | 未試行。クエリの作成・実行が対話的な操作を要し、今回のプローブ予算(小さいGET数件)の範囲を超えるため見送った。**未試行**であって「無い」ではない |
| 有料 | Coinglass有料プラン、Kaiko/Amberdata等 | 未試行(鍵・契約が必要。存在の有無のみ:一次資料上も既報の同種サービスと同様に存在すると推定) |

### C1の結論(この段では)

- **識別可能性そのものは一次資料で確認できた**: `userFills`/`userFillsByTime`/WS `userEvents` の fill が
  `liquidation: {liquidatedUser?, markPx, method}` を持つ。ただし **`userFills` は直近2000件、
  `userFillsByTime` も直近10000件までしか遡れない**(§C1一次資料引用は下記C3参照)。
  **深い履歴は個別アドレスのAPIでは無理**で、S3の `node_fills_by_block`(Requester Pays)か
  第三者インデクサに依存する。
- S3・第三者とも**中身(清算を含むか、どの粒度か)は未確認**。次段で当たる価値があるのは
  Requester Pays を通す少額コスト(AWS アカウントとバケット内の1オブジェクト取得程度)。

---

## C2. 同期間の1分足・約定・OI・資金調達率

| カテゴリ | 経路 | 結果 |
|---|---|---|
| この環境 | `candleSnapshot`(1分足) | **一次資料で「直近5000本のみ」と明記**(`for-developers/api/info-endpoint`)。1分足なら約3.47日。**この環境からの実測でも整合**: 2026-09-12 06:00 UTC 起点で、1日前・3日前の1時間窓は非空(データあり)、4日前・4.5日前・5日前以降は空。**境界は3日〜4日の間**(1時間粒度の探索なのでこれ以上は詰めていない)。ログ5〜21行目 |
| この環境 | `metaAndAssetCtxs`(OI・資金調達率・出来高の**現在値**) | **到達確認済み(HTTP 200)**。BTC: `openInterest=35904.56266`(BTC建て)、`funding=0.000005864`(直近該当時間の資金調達率)、`dayNtlVlm=3579640197.664888382`(USD建て24h想定出来高)、`dayBaseVlm=46081.56484`(BTC建て)、`markPx=77285.0`。**ただし履歴ではなく現在のスナップショットのみ**(このエンドポイントに時系列パラメータは無い)。ログ4行目・末尾の抽出行 |
| 公開アーカイブ・API | S3 `hyperliquid-archive` の `market_data/[date]/[hour]/[datatype]/[coin].lz4`(L2板含む想定)・`asset_ctxs/[date].csv.lz4`(OI/資金調達率の日次アーカイブと推定) | **一次資料で確認**: パス形式は `s3://hyperliquid-archive/market_data/[date]/[hour]/[datatype]/[coin].lz4` および `s3://hyperliquid-archive/asset_ctxs/[date].csv.lz4`。**保持期間は「約月1回のアップロード、更新の適時性は保証されずデータが欠けることがある」**(原文引用は§3)。**Requester Pays**(`--request-payer requester` が必要、転送料は要求者負担)。**匿名アクセスは403**(実測、ログ22〜23行目)。**datatype に `l2Book` が含まれるかは一次資料本文に明示のコード例が無く、未確認**(WebFetchの要約では `[datatype]` は変数としか示されなかった) |
| 第三者データ | Coinalyze / Coinglass(Hyperliquidの資金調達率・OI集計) | 未試行。他取引所での同種サービスの深さ(1分足7日・日次1年超、`LIQUIDATION_HISTORY_SURVEY.md`)から類推すると同様の窓がある可能性(推定、未確認) |
| 有料 | Kaiko / Amberdata(Hyperliquid対応の有無含め) | 未試行 |

### C2の結論(この段では)

- **APIから遡れる1分足は3〜4日が壁**。それより古い1分足・L2板は **S3(Requester Pays)しか経路が無い**
  (一次資料上の推測であり、L2板が実際にそのパスに存在するかは中身未確認)。
- OI・資金調達率は**現在値は無料で取れる**が、履歴は `asset_ctxs/[date].csv.lz4`(推定)か
  第三者集計サービスに依存。

---

## C3. 清算の時刻精度・一次資料

一次資料: `https://hyperliquid.gitbook.io/hyperliquid-docs/trading/liquidations`
(取得日 2026-09-12、WebFetch)。見出し構成は **Overview / Motivation / Partial Liquidations /
Liquidator Vault / Computing Liquidation Price** の5節。

### 引用(WebFetchが抽出した原文)

- 維持証拠金率: `"The maintenance margin is half of the initial margin at max leverage, which varies from 3-40x"`
- 清算価格の算出式: `liq_price = price - side * margin_available / position_size / (1 - l * side)`
  (`l = 1 / MAINTENANCE_LEVERAGE`、`side` はロング=1・ショート=-1)
- HLP vault によるバックストップ: `"Backstop liquidations on Hyperliquid are democratized through the
  liquidator vault, which is a component strategy of HLP."`(維持証拠金の2/3を下回ったポジションが対象、
  利益は HLP コミュニティに還元)

ADL は**同ページに記述が無い**。別ページ
`https://hyperliquid.gitbook.io/hyperliquid-docs/trading/auto-deleveraging`(取得日 2026-09-12)で確認:

- `"Auto-deleveraging strictly ensures that the platform stays solvent."`
- ソート指標: `(mark_price / entry_price) * (notional_position / account_value)`
- 不変性: `"a user who has no open positions will not socialize any losses of the platform"`

**清算の時刻精度**: `FillLiquidation`(`https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/websocket/subscriptions`、
取得日 2026-09-12)は `{liquidatedUser?: string; markPx: number; method: "market"|"backstop"}` のみで、
**専用の時刻フィールドを持たない**。時刻は同じ fill オブジェクトが共通して持つ `time`(fillの約定時刻)を
使うほかない、というのがこの調査での**推定**(一次資料に「liquidationの時刻はfillのtimeを使え」という
明示の記述は確認できていない)。**清算判定の遅延(オンチェーンのブロック確定との時差)についての記述は
見つかっていない → 未確認**。

`userFills`/`userFillsByTime` のレート限界(C1関連、一次資料引用):
- `userFills`: `"at most 2000 most recent fills"`
- `userFillsByTime`: `"at most 2000 fills per response and only the 10000 most recent fills are available"`
- `candleSnapshot`: `"Only the most recent 5000 candles are available"`

### C3の結論

一次資料で**確認できたもの**: 維持証拠金率の算出根拠、清算価格式、HLP vaultの役割、ADLのソート指標。
**確認できなかったもの(未確認)**: 清算イベント自体の時刻精度・粒度(ミリ秒か秒か、オンチェーン確定との
時差)。

---

## C4. bitFlyerとの突き合わせに要る規模の目安

**方法**: 公式 `metaAndAssetCtxs` から自分で取得した現在値(この環境から2026-09-12 06:45 UTC実測)。
公式stats(`app.hyperliquid.xyz/stats`)はSPAで静的フェッチ不可だったため、**info APIの生データを一次資料として使用**(自己観測。ドキュメントページの二次的な数値ではない)。

| 取引所 | 商品 | OI(建玉) | 24h出来高 | 取得方法・時刻(UTC) |
|---|---|---|---|---|
| **Hyperliquid** | BTC 無期限 | **35,904.56 BTC**(markPx 77,285 換算で ≒ $2.77B) | **$3,579,640,198**(想定ドル建て、`dayNtlVlm`)/ 46,081.56 BTC(`dayBaseVlm`) | `api.hyperliquid.xyz/info` `metaAndAssetCtxs`、POST、2026-09-12T06:43:15Z(ログ4行目) |
| OKX | BTC-USDT-SWAP(無期限、USDT建ての1本のみ。OKXは他にBTC-USD建ての無期限も別途存在し、これはOKXのBTC無期限全体ではない) | 27,442.95 BTC(`oiCcy`、≒$2.12B `oiUsd`) | 105,123.55 BTC(`volCcy24h`)、~~≒$10.51B(`vol24h`のUSDT建て名目)~~→`vol24h`(10,512,355.09)はコントラクト枚数(`volCcy24h`÷0.01と一致、105123.5509/0.01=10512355.09。USD名目値ではない)。ドル換算(自己算出、独立の一次資料での検算ではない): 同時刻のticker `last`=77,290 USDT(ログ28行目、2026-09-12T06:45:40Z)を使い 105,123.5509 BTC×77,290 ≒ $8.12B(訂正 2026-09-13、検収§2) | `www.okx.com/api/v5/public/open-interest`, `.../market/ticker`、GET、2026-09-12T06:45:39〜40Z(ログ27〜28行目) |
| Binance | BTCUSDT 無期限 | 未取得 | 未取得 | **試行して不可(この環境からHTTP 451地域制限、既報 `docs/DATA.md` §2)**。オーナーPCでの再測が必要 |
| Bybit | BTCUSDT 無期限 | 未取得 | 未取得 | **試行して不可(この環境からHTTP 403地域ブロック、既報)**。オーナーPCでの再測が必要 |
| Gate | BTC_USDT 無期限 | 未取得 | 未取得 | 未試行(本票では手を付けていない) |

### C4の結論

**単一時点(2026-09-12 06:45 UTC前後)の比較でのみ**: Hyperliquid の BTC OI(約35.9k BTC)は、
同時刻の OKX の USDT建てBTC無期限1本(約27.4k BTC)より**大きい**。ただし OKX は他にコイン建て
(USD建て)の無期限市場も別に持っており、これは OKX の BTC無期限**全体**ではないため、
「Hyperliquid が OKX 全体を上回る」という一般化はできない(**未確認、射程外**)。
Binance/Bybit は地域制限でこの環境から直接測れず、比較は**PCでの実測を待つ必要がある**。
**この数値は単一時点のスナップショットであり、時系列での規模比較(トレンド)は本票の範囲外**。

---

## 生ログとの対応

`docs/DATA/probes/20260912_o3c_supp_c_hyperliquid.log` の行番号対応(2026-09-12実行分、全て本票用に新規取得):

- 2行目: `userFillsByTime` 到達確認(空配列、アドレスは検証目的の任意アドレス)
- 3〜4行目: `meta` / `metaAndAssetCtxs` 到達確認・BTC現在値
- 5〜21行目: `candleSnapshot` の保持期間探索(1h窓・複数日数バック)
- 22〜24行目: S3バケット2種の匿名アクセス403(Requester Pays)
- 25行目: hypurrscan API推測パスの404(未確認、正しいパス不明)
- 26行目: infoエンドポイントのGET拒否(405、POST限定の確認)
- 27〜28行目: OKX比較用数値
- 29行目以降: WebFetchによる一次資料確認の記録(historical-data / liquidations / info-endpoint /
  websocket subscriptions / auto-deleveraging / hypurrscan / app.hyperliquid.xyz/stats)

---

## `docs/DATA.md` への追記案(§2 海外暗号資産・無期限先物、末尾に追加。マージはリード判断)

| 資産 | 所在 | 範囲 | 状態 | 最終確認日 | プローブのログ | 使った単位 |
|---|---|---|---|---|---|---|
| Hyperliquid BTC無期限 `userFills`/`userFillsByTime`(清算識別可、`liquidation`フィールド) | `https://api.hyperliquid.xyz/info`(POST, type=userFills/userFillsByTime) | 直近2000件(userFills)/直近10000件(userFillsByTime、一次資料記載の上限) | 未試行(到達性のみ確認、実際の清算含有アドレスでの検証は未実施) | 2026-09-12 | `docs/DATA/probes/20260912_o3c_supp_c_hyperliquid.log` | 未使用 |
| Hyperliquid BTC無期限 `candleSnapshot`(1分足) | 同上(type=candleSnapshot) | **直近5000本(1分足で約3.47日、一次資料+実測で確認)** | 試行して不可(それより古い1分足はこのAPI経由では不可。方法: POST、実測 2026-09-12) | 2026-09-12 | 同上 | 未使用 |
| Hyperliquid BTC無期限 `metaAndAssetCtxs`(OI・資金調達率・出来高、現在値のみ) | 同上(type=metaAndAssetCtxs) | 現在のスナップショットのみ(履歴機能なし) | 取得済(現在値、2026-09-12T06:43:15Z: OI 35904.57 BTC, dayNtlVlm $3.58B) | 2026-09-12 | 同上 | 未使用 |
| Hyperliquid S3アーカイブ(`hyperliquid-archive`=market data、`hl-mainnet-node-data`=node data) | `s3://hyperliquid-archive/market_data/[date]/[hour]/[datatype]/[coin].lz4` 等(一次資料記載パス) | 月次アップロード目安、欠測許容(一次資料明記)。中身は未確認 | 試行して不可(匿名アクセスは403、Requester Pays。方法: GET S3 ListObjectsV2、実測 2026-09-12) | 2026-09-12 | 同上 | 未使用 |

---

## 予算消化状況

実時間: 約20分以内で完了(超過なし)。トークン: 見積もり5万以内(超過の兆候なし)。**すべての手順を完了**。
