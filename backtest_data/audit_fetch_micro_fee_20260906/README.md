# Audit fetch: 日経225マイクロ先物 手数料・商品仕様 — 2026-09-06

`config/constants.yaml: jpx_nikkei225_micro_futures.*`(fee 11円/片側、呼値 5円、
乗数 10円/ポイント)の一次資料を、G1 コスト検証(docs/PHASE2/G1_COST_VERIFICATION.md)
のために**再取得**したもの。既存ファイルは一切変更していない。

## 取得方法

```
export HTTPS_PROXY=http://127.0.0.1:32843
curl -sS --max-time 60 --cacert /root/.ccr/ca-bundle.crt -o <file> "<url>"
```

## ファイル

- `kabu_com_cost_default_html.html` — https://kabu.com/cost/default.html (HTTP 200)
  「先物取引 / 取扱銘柄 / 約定1枚あたり手数料（税込） 立会手数料 | J-NET手数料」表。
  逐語: `日経225マイクロ先物 | 11円 | -`(J-NET は取扱なし)。
  注記「1注文毎の手数料1円未満は切り捨て」「取引チャネルにかかわらず上記手数料」
  「大阪取引所立会取引での約定は立会手数料が適用」。SQ・最終決済に関する
  先物側の追加手数料の記載は**無い**(最終決済の記述はオプションの権利放棄のみ)。
- `kabu_com_item_fop_cost.html` — https://kabu.com/item/fop/cost.html (HTTP 200)
  同社の詳細ページ。同じ表で `日経225マイクロ先物 11円`。
- `kabu_225micro_detail.html` — https://kabu.com/item/fop/f_detail/225micro-futures.html (HTTP 200)
  逐語:「日経225マイクロ先物の取引単位は、日経225を10倍した金額です」
  (乗数 10 円/ポイントの業者側の裏取り)。
- `matsui_news_20230731.html` — https://www.matsui.co.jp/news/2023/detail_0731_02.html (HTTP 200)
  **別業者(松井証券)の一次資料**。逐語:「通常のマイクロ先物取引の手数料について
  15円(税込16.5円)から、10円(税込11円)へと引き下げます」(2023年8月4日)。
- `matsui_fop_top.html` — https://www.matsui.co.jp/fop/ (HTTP 200)
  逐語:「日経225マイクロ先物は約定1枚当たり税込11円」(現時点の掲示)。
- `www_jpx_co_jp_derivatives_products_domestic_225micro-futures_01_html.html`
  — https://www.jpx.co.jp/derivatives/products/domestic/225micro-futures/01.html (HTTP 200)
  JPX 商品概要表。逐語:`取引単位 = 日経平均株価×10円`、`呼値の単位 = 5円`、
  `取引最終日 = 各限月の第2金曜日...の前日に終了する取引日`、`SQ日 = 取引最終日の翌営業日`。
- `jpx_derivatives_fees.html` — https://www.jpx.co.jp/derivatives/rules/fees/index.html
  **HTTP 404**(ページ無し)。取引所取引手数料(取引参加者負担分)の一次表は
  この URL では確認できなかった。記録として保存。

## 結論(数値のみ)

- 片側手数料 11 円(税込)= 2 社の一次掲示で一致。往復 22 円。
- 呼値 5 ポイント × 乗数 10 円/ポイント = 50 円/片側、往復 100 円。
- 保守往復コスト = 22 + 100 = **122 円/往復**(現行制度)。
- 顧客に別建てで課される取引所手数料・SQ 決済手数料の記載は、上記 2 社のページには無い。
  取引所側の一次表は 404 のため未確認(残る不確実性)。

See `MD5SUMS` for content hashes.
