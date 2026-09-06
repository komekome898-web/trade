# 否定的事実の台帳(「無い・できない」の記録。日付・方法・賞味期限つき。期限切れは再確認してから使う)

| ID | 日付 | 事実 | 確認方法 | 賞味期限 | 状態 |
|---|---|---|---|---|---|
| N-001 | 2026-09-05 | bitflyer.com(企業サイト)はこの環境から 403(Akamai) | curl 経由 | 30 日 | 2026-09-06 再確認: 依然 403。api / lightchart は 200 |
| N-002 | 2026-08 | bitFlyer 公開 REST API の約定履歴は約 31 日分のみ | API 仕様・実測 | 90 日 | 有効。ただし lightchart.bitflyer.com は 2015-11 まで分足を返す(2026-09-06 確認)→ 「履歴が無い」への一般化は誤りだった |
| N-003 | 2026-09-06 | ccxt の bitflyer は fetchOHLCV 未実装 | `ccxt.bitflyer().has` | 180 日 | 有効 |
| N-004 | 2026-09-06 | CryptoCompare は無料キー無しで 401、かつ現物のみ | 実測 | 180 日 | 有効 |
| N-005 | 2026-09-04 | 東証 REIT 指数の全期間四本値は無料で入手不能 | 6 ソース試行 | 180 日 | 有効(`reit_onr` schema) |
| N-006 | 2026-09-06 | bitflyer.com の個別ページ(`/ja-jp/s/press`、`/en-jp/faq/65`、`/en-jp/faq/maintenance`、`/en-eu/faq/maintenance_eu` 等)も N-001 と同様に到達不能。WebFetch では `EGRESS_BLOCKED domain=bitflyer.com` と明示エラー。apex ドメイン全体がプロキシ egress でブロックされている(Akamai 403 は curl 側症状、実体はプロキシブロック) | curl(HTTP/2 stream reset)・WebFetch 実測、`backtest_data/audit_fetch_P2-08_docs_20260906/` | 90 日 | 有効。bitFlyer 公式の毎日メンテナンス窓(04:00-04:10 JST / 19:00-19:10 GMT)の一次文書は本環境から直接確認不能 → 二次情報(WebSearch 要約)止まり |
| N-007 | 2026-09-06 | help.bitflyer.com は 502(トンネル失敗)、web.archive.org は TLS 接続が繰り返しリセットされプロキシ経由で到達不能 | curl 実測(2回) | 90 日 | 有効。SFD 料率変遷の一次資料(bitFlyer 自身のお知らせ)を Wayback 経由で遡る代替経路も不可 |
