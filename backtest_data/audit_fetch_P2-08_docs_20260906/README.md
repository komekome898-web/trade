# P2-08 一次資料スナップショット(2026-09-06)

BLINDSPOT_AUDIT.md #5(メンテ窓)・#9(Binance Vision の分境界)向け、および#4(SFD)の到達性調査。
全て `raw/` に生データ(HTML/MD/JSON)を保存。ネットワークはプロキシ経由(CA `/root/.ccr/ca-bundle.crt`)。

| ファイル | URL | 取得時刻(UTC) | HTTP | 内容・要点 |
|---|---|---|---|---|
| `binance_spot_api_docs_market_data_md.md` | https://raw.githubusercontent.com/binance/binance-spot-api-docs/master/rest-api.md | 2026-09-06 13:26 | 200 | **一次資料**。`GET /api/v3/klines` 定義。open time 例 `1499040000000`、close time 例 `1499644799999`(= open + interval − 1ms)。分境界は open time が UTC 起点(00 秒)であることが明記されている |
| `data_binance_vision.html` | https://data.binance.vision/ | 13:26 | 200 | Binance Vision の配布 UI トップ(索引ページのみ、フィールド定義は上記 rest-api.md 側) |
| `status_bitflyer_com.html` | https://status.bitflyer.com/ | 13:26 | 200 | ステータスページ全体。個別インシデント例: 2026-08-26 03:30〜05:00 JST 予定メンテ(取引所・API 停止)。凡例に Maintenance カテゴリあり。**毎日 04:00-04:10 JST の定例メンテ自体の一次記述はこのページには無い**(インシデント単位の告知のみ) |
| `lightning_bitflyer_docs.html` | https://lightning.bitflyer.com/docs | 13:27 | 200 | **一次資料**。API リファレンス内に `sfd` フィールド定義: "Accumulated Lightning FX SFD (Special Fee for Deviation) charges for the position." 用語定義のみ、料率表・発動履歴は無い |
| `coinotaku_sfd.html` | https://coinotaku.com/posts/13923 | 13:29 | 200 | 二次資料(解説記事)。SFD 制度の解説・料率変遷の記述あり(未検証の二次情報として扱う) |
| `zerozero_sfd.html` | https://www.zerozero-kasoutasuka.com/entry/bitflyer-sfd | 13:29 | 200 | 同上、二次資料 |
| `note_hht_sfd.html` | https://note.com/hht/n/n04d56caf3108 | 13:29 | 200 | 同上、二次資料(SFD 収益試算の個人ブログ) |
| `prtimes_search_sfd.html` | https://prtimes.jp/main/action.php?run=html&page=searchkey&search_word=bitFlyer+SFD | 13:27 | 200 | 検索結果ページを取得したが bitFlyer 関連の PR 個別記事リンクを抽出できず(JS 描画依存の可能性)。**不使用・参考のみ** |
| `archive_availability_sfd.json` | https://archive.org/wayback/available?url=bitflyer.com/ja-jp/faq/sfd | 13:27 | 200 | `archived_snapshots: {}`(推測 URL がそもそも外れ。CDX 検索は N-007 によりブロックされ未実施) |
| `cdx_test.json` / `cdx_test2.json` | https://web.archive.org/cdx/search/cdx?... | — | 000 | 取得失敗(TLS reset)。**空ファイル未生成、記録のみ**。詳細は `docs/NEGATIVE_FACTS.md` N-007 |

## 到達できなかったもの(`docs/NEGATIVE_FACTS.md` 参照)

- `bitflyer.com` apex ドメイン全体(`/ja-jp/s/press`、`/en-jp/faq/65`、`/en-jp/faq/maintenance`、`/en-eu/faq/maintenance_eu`)— N-001(既存)を N-006 で再確認・詳細化。WebFetch は `EGRESS_BLOCKED domain=bitflyer.com` を明示的に返す(プロキシ egress ブロック、Akamai 403 は表面症状)。
  そのため bitFlyer 公式の「毎日 04:00-04:10 JST(=19:00-19:10 GMT)定例メンテ」の一次記述、および SFD 料率表(5%で0.50%〜20%以上で2.00%、と WebSearch 要約に出た数値)の一次資料は本セッションでは未確認 — WebSearch の要約止まり、直接ページは未取得。
- `help.bitflyer.com`、`web.archive.org`(CDX 検索含む)— N-007。SFD 発動履歴の一次資料をこれらの代替経路からも取得できず。

## 結論(このデータで言えること)

- Binance klines の分境界(#9)は一次資料で確認済み: open time は UTC 分起点、close time は次の open time − 1ms。
- SFD の用語定義(bitFlyer が「価格乖離に対する特別手数料」と呼んでいること)は一次資料(lightning.bitflyer.com/docs)で確認済み。**料率表・発動時間帯の履歴そのものは一次資料未確認**(#4 は依然オープン、二次資料の数値は反証可能な形で「未検証」と明記して使うこと)。
- 定例メンテ窓の一次記述(#5)も同様に未確認。G2棚卸しの実測(REST candles の 19:00 UTC 前後フラット行)が現状もっとも直接的な根拠のまま。
