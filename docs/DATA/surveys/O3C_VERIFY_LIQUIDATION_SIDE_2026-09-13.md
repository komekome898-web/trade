# O3C 清算イベントの向き検証(一次資料確認モード)

調査班(下位モデル)。プローブ生ログ: `docs/DATA/probes/20260913_o3c_liquidation_side.log`

---

## 主張1
Binance COIN-M(dapi)の強制決済レコードで `side=SELL` は**ロング建玉の強制決済**、`side=BUY` は**ショート建玉の強制決済**を表す。

### 一次資料
- URL(正規): `https://developers.binance.com/docs/derivatives/coin-margined-futures/...`(現行)
- 到達状況: この環境からは AWS WAF チャレンジ(`awswaf.com`)により本文不可(HTTP 202、JS必須)。WebFetch も製品トップページしか返さない。→ 代替経路として旧公式ドメインのアーカイブを使用。
- 使用したURL: `https://web.archive.org/web/20240521073544/https://binance-docs.github.io/apidocs/delivery/en/`(旧公式ドキュメント `binance-docs.github.io` の2024-05-21時点保存)
- 取得日: 2026-09-12(UTC)/ 取得方法: curl(archive.org経由、$HTTPS_PROXY)

### 引用(原文そのまま)
Liquidation Order Streams のペイロード例:
> `"S":"SELL",                     // Side`
(このオブジェクトは `"o":"LIMIT"`, `"f":"IOC"`, `"X":"FILLED"` など**注文**を表すフィールドで構成される。「Side」は建玉の向きラベルではなく**この強制決済注文自体の売買方向**。)

同ドキュメントの `ORDER_TRADE_UPDATE`(自分の建玉が清算されたときの account stream)の例では、清算注文(`"c"` が `"autoclose-"` で始まる)の同一オブジェクト内に:
> `"S":"SELL",                 // Side`
> `"ps":"LONG",                // Position Side`
が並記されている(SELL の清算注文で Position Side が LONG)。

さらに一般規則として(`STOP_MARKET, TAKE_PROFIT_MARKET` の `closePosition=true` の説明):
> `If triggered,close all current long position( if SELL) or current short position( if BUY).`

### 引用の検算
保存した生HTMLファイル(`binance_delivery_20240521.html`)に対し `grep` で該当行を検索し、上記3箇所とも行番号(7619, 7644, 4954付近)に文字単位で一致することを確認した。一致。

### 判定
**一次資料で確認**(ただし「SELL=ロング清算」という結論は、`side` フィールド自体の定義文からの直接一文ではなく、①`side` は清算注文の売買方向であること、②同ドキュメント内の別セクションでの「SELL=ロングを閉じる/BUY=ショートを閉じる」という一般規則、③自分の建玉清算時の実例(SELL+LONG併記)、の3点を組み合わせた確認。単独の一文で「position方向」と明記されているわけではない)。

### 代替経路を試したか
はい(経路: developers.binance.com 現行ページ→WAF不可 → WebFetch→トップページのみ → archive.org の旧公式ドキュメント保存版で成功)。

---

## 主張2
Gate.io の清算約定(`GET /futures/{settle}/liq_orders`)の `size` の符号がロング/ショートのどちらを指すか。

### 一次資料
- URL: `https://www.gate.io/docs/developers/apiv4/en/`(現行) および同ページの archive.org 保存版
- 到達状況: この環境からは `www.gate.io` / `www.gate.com` いずれも Akamai(`errors.edgesuite.net`)により HTTP 403(Access Denied)。WebFetch は changelog の断片のみ返し、目的のレスポンススキーマ表には到達しなかった。→ 代替経路として (a) archive.org 保存版、(b) Gate.io公式GitHub組織(`github.com/gateio/gateapi-python`、公式SDKの自動生成ドキュメント)を使用。
- 取得日: 2026-09-12(UTC)

### 引用(原文そのまま)
archive.org 保存版(`web.archive.org/web/20250318011445/.../apiv4/en/`、`GET /futures/{settle}/liq_orders` の Response Schema 表):
> `» size | integer(int64) | User position size`

同じ内容が公式GitHub `gateapi-python` の `docs/FuturesLiqOrder.md` にも:
> `**size** | **int** | User position size | [optional] [readonly]`

Gate.io の符号規則(同ドキュメント内、注文の `size` の説明。`liq_orders` の項目自体には符号の説明文は繰り返されていない):
> `Order size. Specify positive number to make a bid, and negative number to ask`
(`FuturesOrder.md`: `Trading quantity. Positive for buy, negative for sell.`)

### 引用の検算
archive.org保存版HTML(`gate_wayback_20250318.html`)と GitHub生ファイル(`gate_spec.yaml`=FuturesLiqOrder.md, `gate_futuresorder.md`)を `grep` で検索し、両者の文言が一致することを確認した(GitHub版とドキュメントサイト保存版の記述は同一)。一致。

### 判定
**一次資料で確認**(`size` は**清算された建玉のサイズ**そのもの、Binanceのような「取引所が出す反対売買注文の向き」ではない。符号の正負がlong/shortのどちらかは、`liq_orders` 項目自体の一文には無く、Gate.io全体の符号規則〔正=buy/long側、負=sell/short側〕からの適用。Binanceとは**意味づけが異なる**〔Binanceは注文の売買方向、Gateは建玉サイズの符号〕ことは確認できた)。

### 代替経路を試したか
はい(経路: gate.io/gate.com 現行→403 → WebFetch→断片のみ → archive.orgのドキュメントサイト保存版、および公式GitHub SDKドキュメントの2つで成功・相互一致)。

---

## 主張3(傍証。判定ではない)
手元データ(`backtest_data/binance_cm_o3c_20260913/liquidationSnapshot/BTCUSD_PERP/`、2023-06-25〜27の3日分を解凍)で、`side` ごとの近傍価格の動きが主張1と整合するか。

### 方法
3日分のCSV(542行、重複除去後271行)を時刻順に並べ、60秒以内に連続する同一 `side` の「バースト」(3件以上)を28件抽出し、バースト内の `average_price` が始点→終点でどちら向きに動いたかを見た。

### 結果(数値の結論ではなく整合性の確認のみ)
SELL側バースト15件は全て価格が下降、BUY側バースト13件は全て価格が上昇していた(下降/上昇0件の逆方向なし)。

### 判定
**一次資料と整合する**(傍証。SELL=強制売り=ロング清算が価格を下げる方向、BUY=強制買い=ショート清算が価格を上げる方向、という主張1の向きと矛盾する観測は無かった。標本は3日・28バーストのみで、これはO3Cの効果量やエッジの有無を判定するものではない)。

---

## 測定器への含意
`src/bot/research/liq_response.py` の Binance 分岐(`side="long" if side=="SELL" else "short"`)は一次資料の確認結果と一致しており変更不要だが、Gate 分岐(`side="long" if float(row["size"])<0 else "short"`)は本調査で確認した符号規則(正=long側、負=short側)と**逆**になっている可能性があるため、コードを変更せずリードが要確認とすること。
