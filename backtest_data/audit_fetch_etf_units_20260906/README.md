# audit_fetch_etf_units_20260906 — ETF 売買単位(最小売買口数)と発注仕様の一次資料

取得日: 2026-09-06(JST)。取得元は下表の URL を curl でそのまま保存(HTML/PDF/YAML は無加工)。
`*.txt` は PDF から pypdf で抽出した派生テキスト(検証用。一次資料は PDF のほう)。
チェックサムは `MD5SUMS`。

## 何を確かめに行ったか

`docs/PHASE2/EXEC_MEASUREMENT/PREREG.md` の実測は「最小口数 1 口」を前提に書かれかけていた。
1343 と 1591 の**実際の売買単位**を一次資料で確認するのが目的。

## 結論(2 つの独立な一次資料で一致)

| 銘柄 | 売買単位 | 1 売買単位あたりの金額 | 出所 |
|---|---|---|---|
| 1343 NEXT FUNDS 東証REIT指数連動型上場投信 | **10 口** | 19,250 円(2026-09-04 終値 1,925.0 円 × 10) / 21,670 円(2026-02-27 時点、JPX 資料) | `nextfunds_1343.html`(発行会社)、`jpx_1343-j.pdf`(東証) |
| 1591 NEXT FUNDS JPX日経インデックス400連動型上場投信 | **1 口** | 37,000 円(2026-09-04 終値) / 35,720 円(2026-02-27 時点、JPX 資料) | `nextfunds_1591.html`、`jpx_1591-j.pdf` |

→ **1343 は「1 口 ≈ 2,000 円」では発注できない**。最小発注は 10 口 ≈ 19,250 円。

## 期限のある事実(実測の暦を縛る)

`td_260825a.pdf`(野村アセットマネジメント 適時開示 2026-08-25)より:

- **1591**: 受益権 1 口 → 100 口に分割、**分割効力発生日 2027-02-01**(分割基準日 2027-01-31)。
  売買単位は **1 口以上 1 口単位 → 10 口以上 10 口単位、変更実施日 2027-01-28**。
  分割後の 1 口は約 370 円になるため、JPX 呼値表(`config/constants.yaml: jpx_cash_equity.etf_tick_size_yen_by_price_band`、
  10,000 円以下 = 1 円)では **1 ティック ≈ 27bps/片側**。現在の 10 円 = 2.7bps から一桁悪化する。
  実測も、実測結果に基づく本番投入も、**2027-01-28 より前**に成立させる必要がある(それ以降は別銘柄・別前提の話になる)。
- **1321**(P2-03 の参照系列、本実測の対象外): 1 口 → 100 口分割、効力発生 2026-10-07、売買単位変更 2026-10-05。
- 1343 は本開示の対象 ETF に**含まれない**(分割・売買単位変更の予定なし、2026-09-06 時点)。

## 発注仕様(kabuステーションAPI, `kabu_STATION_API.yaml` info.version 1.5)

- `POST /sendorder`(現物・信用)。`RequestSendOrder.required` =
  `Symbol, Exchange, SecurityType, Side, CashMargin, DelivType, AccountType, Qty, Price, ExpireDay, FrontOrderType`。
- `FrontOrderType`: **13 = 寄成（前場）/ 16 = 引成（後場）**(いずれも Price は 0)。10 = 成行、15 = 引成（前場）、14 = 寄成（後場）。
- `Exchange`(市場コード): 1 = 東証 / 9 = SOR / 27 = 東証+。**仕様書の注記**:
  「※SORまたは、東証+がメンテナンス中は現物のみ東証への指定が可能です。**通常時に東証を指定しての新規発注はできません。**」
  → `Exchange: 1` は通常時に使えない。実測の既定は `Exchange: 9`(SOR。手数料 0 円の前提もこちら)。
  **不明**: SOR が引成/寄成をどこに回送するか(東証の板寄せに参加するのか)は仕様書に記述がない。実測前に検証ポート 18081 で確認する。
- `CashMargin: 1`(現物)。現物買は `DelivType` 指定必須(2 = お預り金)、`FundType` 指定必須(02 = 保護)。
  現物売は `DelivType: 0`(指定なし)、`FundType` は**半角スペース 2 つ**。
- `SecurityType: 1`(株式)、`AccountType`: 2 = 一般 / 4 = 特定 / 12 = 法人(口座に合わせる。オーナー確認事項)。
- `ExpireDay: 0` = kabuステーション上の「本日」。引け後は翌営業日に解釈される旨が仕様書にある(引成の発注時刻に注意)。
- 約定価格の取得: `GET /orders?product=1&id=<OrderId>` の `Details[]` で `RecType: 8`(約定)の行に
  `Price`(約定値段)・`Qty`・`ExecutionDay`・`Commission`・`CommissionTax` がある。**手数料 0 円の主張もここで実測できる**。
- `GET /symbol/{symbol}@1` は `TradingUnit`(売買単位)・`PriceRangeGroup`(呼値グループ)・`UpperLimit`/`LowerLimit`(値幅)を返す。
  → 発注前サニティで `Qty == TradingUnit` を突き合わせられる(「1 口」を定数で決め打たない)。
  呼値グループの定義値: 10003 = 売買単位が 10 口以上の ETF 等(1343 側)、10004 = 売買単位が 1 口の ETF 等(1591 側)。

## ファイル

| ファイル | 取得 URL | HTTP |
|---|---|---|
| `nextfunds_1343.html` | https://nextfunds.jp/lineup/1343/ | 200 |
| `nextfunds_1591.html` | https://nextfunds.jp/lineup/1591/ | 200 |
| `jpx_etf_issues_01.html` | https://www.jpx.co.jp/equities/products/etfs/issues/01.html | 200 |
| `jpx_1343-j.pdf` / `.txt` | https://www.jpx.co.jp/equities/products/etfs/issues/files/1343-j.pdf | 200 |
| `jpx_1591-j.pdf` / `.txt` | https://www.jpx.co.jp/equities/products/etfs/issues/files/1591-j.pdf | 200 |
| `td_260825a.pdf` / `.txt` | https://nextfunds.jp/data/2026/td_260825a.pdf | 200 |
| `pros_Y11343.pdf` / `.txt` | https://www.nomura-am.co.jp/fund/pros_gen/Y1141343.pdf | 200 |
| `pros_Y11591.pdf` / `.txt` | https://www.nomura-am.co.jp/fund/pros_gen/Y1141591.pdf | 200 |
| `kabu_STATION_API.yaml` | https://raw.githubusercontent.com/kabucom/kabusapi/master/reference/kabu_STATION_API.yaml | 200 |

注: 交付目論見書(`pros_Y1*.pdf`)には売買単位の記載が**ない**ため、単位の根拠には使っていない(取得した事実のみ記録)。
JPX の ETF 一覧ページ(`jpx_etf_issues_01.html`)にも売買単位の列はなく、銘柄別 PDF に載る。
