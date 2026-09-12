# O-3c 調達票 補遺A — bitFlyer自身の清算識別 / BitMEX清算の代替経路 / bitFlyer SFD・ロスカット一次資料(2026-09-12)

**前提として読んだもの**: `docs/DATA/surveys/LIQUIDATION_HISTORY_SURVEY.md`(2026-09-08)、
`docs/DATA/surveys/O3C_PROCUREMENT_2026-09-12.md`(本補遺の親票、同日)、`docs/DATA.md` §2。
既知事項(Gate.io 90日、OKX 24h、Binance COIN-M 16か月アーカイブ、Bybit/BitMEX個別清算アーカイブ無し、
BitMEX清算オブジェクトに時刻フィールド無し等)は**繰り返さない**。本票はA1/A2/A3の**差分のみ**。

プローブの生ログ: `docs/DATA/probes/20260912_o3c_supp_a_bitflyer_bitmex.log`(27エントリ、方法・URL・
HTTPコード・バイト数・先頭200文字・UTC時刻)。方法はcurl(`$HTTPS_PROXY`経由)とWebFetch。

---

## 0. 前回調査からの差分(要点)

| # | 差分 | 印 |
|---|---|---|
| 1 | **bitFlyer公式ドキュメント上、`executions`(HTTP Private "Get Executions")のフィールドは `id, child_order_id, side, price, size, commission, exec_date, child_order_acceptance_id` のみで、清算/ロスカットを識別するフィールド・フラグ・エンドポイントは存在しない**(公開APIの実測でも `id/side/price/size/exec_date/buy_child_order_acceptance_id/sell_child_order_acceptance_id` のみで同様)。親票・LIQUIDATION_HISTORY_SURVEYはbitFlyer**自身**の清算識別を扱っていなかった新規項目 | 事実(一次資料+実測) |
| 2 | **BitMEXの `insurance`(保険基金残高)日次エンドポイントは2016-02-28〜現在まで生きている**(鍵不要、200)。ただし個々の清算イベントではなく**日次の保険基金ウォレット残高**のみで、清算を1件ごとに識別する情報は無い | 事実(実測) |
| 3 | **ccxtの`fetchLiquidations`(bitmex)はREST `/liquidation`をstartTime/endTime/count付きで呼ぶだけで、親票が実測した公開APIと同一エンドポイント**。実装コード自身が`parse_liquidation`で`timestamp: None, datetime: None`を明示しており、**ccxt開発者もBitMEXの清算オブジェクトに時刻が無いことを実装レベルで認めている**。startTime指定でも過去分は返らない(本票で`startTime=2020-01-01`を実測、結果は空配列) | 事実(一次資料=ccxtソース、実測) |
| 4 | **Tardis.dev はBitMEX向けに`liquidation`チャネル("Liquidation events stream")を公式にドキュメント化している**(親票は未確認としていた)。ただし料金・提供期間の本文までは今回未取得(時間予算のため) | 事実(到達性)/未確認(範囲・料金) |
| 5 | **archive.org(web.archive.org)は本環境から到達不能**: WebFetchはツール側でweb.archive.orgをブロックリストしており明示エラー、curlはHTTPS接続がリセットされる(プレーンHTTPはプロキシ側がCONNECT以外を拒否)。BitMEX清算アーカイブの過去スナップショット確認は**この環境からは不可** | 事実(実測、環境固有) |
| 6 | **bitflyer.com(FAQ/SFDページを含むメインサイト)は本環境からWAFで一貫して403**(`Access Denied`、リファレンス番号付き)。`lightning.bitflyer.com`(APIドキュメント)は同じ環境から200で到達可能——**ホストが分かれておりWAFの適用範囲が異なる**。SFD・証拠金維持率・ロスカットの公式FAQ本文(`bitflyer.com/ja-jp/faq/7-33`, `7-23`)は**この環境からは原文を取得できず**、URLと検索エンジンのスニペット要約までしか確認できていない | 事実(実測)/未確認(本文原文) |
| 7 | **`deploy/mirror_bitmex.bat`(`scripts/mirror_bitmex_archive.py`)が対象とするのは `data/trade/`・`data/quote/`・`data/porl/` の3プレフィックスのみ**。「liquidation」名のプレフィックスは存在せず、保全対象にも含まれない(バケット側に無いことは親票で既知、本票は取得スクリプト側のコードで再確認) | 事実(コード確認) |

---

## 1. (A1) bitFlyer自身の清算データ

固定カテゴリ:

| カテゴリ | 経路 | 結果 |
|---|---|---|
| この環境 | `api.bitflyer.com/v1/executions`, `getticker`, `getboardstate`(公開API、実測) | **一次資料で該当なし**。`executions`は`id/side/price/size/exec_date/buy_child_order_acceptance_id/sell_child_order_acceptance_id`のみ(実測、ログ[1][2])。`getticker`/`getboardstate`にもSFD・清算関連フィールドは無い(実測、ログ[3][4]) |
| この環境 | `lightning.bitflyer.com/docs`(公式APIリファレンス、WebFetch) | **一次資料で該当なし**。"Get Executions"の全フィールドを確認したが清算識別子は無い。"Get Margin Status"に`margin_call_amount`/`margin_call_due_date`はあるが、これは口座単位の追証情報であり**個々の約定が清算による物かを識別するものではない**(ログ[5]) |
| オーナーPC | 私設API(要鍵)の`executions`(private)や`getpositions`等、公開APIと同一スキーマの可能性が高い | **PCでの到達確認が必要**(要鍵エンドポイントに公開版と異なる追加フィールドがあるかは未確認。ただしbitFlyer API全体の設計思想からして、privateの`executions`も同じフィールド構成である可能性が高い=推定) |
| 公開アーカイブ・API | 該当なし(bitFlyerは自社清算データの過去アーカイブを配布していない。少なくとも本票の探索範囲では発見できず) | 未確認(探索範囲: 公式APIドキュメントとFAQタイトルのみ。ヘルプセンター全文検索は本環境のWAFブロックのため未実施) |
| 第三者データ | 該当なし(bitFlyerの清算を集計・配信する第三者サービスは本票の検索では見つからず) | 未確認 |
| 有料 | 該当なし | 該当なし |

**A1の結論**: **一次資料(公式APIドキュメント+公開APIの実測スキーマ)の両方で、bitFlyerの`executions`に強制決済を識別するフィールドは存在しない**。これは「配布していない」という否定的事実だが、確認した一次資料はAPIドキュメントと実際のレスポンススキーマの2つに限られる(私設APIの追加フィールド、および利用規約・約款上の定義は未確認)。

---

## 2. (A2) BitMEXの過去清算を識別する代替経路

### (i) BitMEXが過去に配布した経路

| カテゴリ | 経路 | 結果 |
|---|---|---|
| この環境 | `GET /api/v1/liquidation?startTime=...`(パラメータ受理を実測) | **試行して不可**(パラメータは受理されるが過去分を返さない。`startTime=2020-01-01`で空配列。方法: GET、実測、ログ[8]) |
| この環境 | `GET /api/v1/insurance`(保険基金日次残高) | **取得できるが清算の代理にならない**。2016-02-28〜現在まで日次残高は取れる(実測、ログ[6][7])が、**個々の清算イベントを特定する情報は含まれない**(通貨・日付・残高の3列のみ) |
| 公開アーカイブ・API | `public.bitmex.com`のS3バケット直下(`trade/`, `quote/`, `porl/`のみ、親票で既確認) | 試行して不可(親票の既報を再確認。フォルダ自体が無い) |
| オーナーPC | 同上REST(insurance/liquidation)。地域制限の対象外の可能性 | PCでの到達確認は不要(この環境で200が取れているため、地域制限の問題ではない) |
| 公式ブログ・データページ | BitMEXの公式ブログ・データページで過去に清算履歴セットを配布した告知 | **未確認**(本票では検索していない。時間予算のため次点) |

### (ii) 第三者データ

| 経路 | 結果 |
|---|---|
| **Tardis.dev** | BitMEX向け`liquidation`チャネル("Liquidation events stream")を公式ドキュメントに明記(WebFetch、ログ[16])。**範囲・料金は未確認**(ドキュメントページの別セクション、時間予算のため未取得)。次点で`docs.tardis.dev/api/data-types`のliquidation定義本文を読む価値がある |
| **Kaiko** | 未試行(本票では検索していない) |
| **CryptoTick** | 未試行(本票では検索していない) |
| **archive.org**(public.bitmex.comの過去スナップショット) | **この環境からは到達不能**(WebFetchはweb.archive.orgをブロックリスト、curlはHTTPS接続リセット。方法・ログ[9]〜[14])。オーナーPCでの到達確認が必要 |
| **CoinGlass** | 親票で既報(鍵必須、~~401~~→HTTP 200・本文JSON `code:401`(訂正 2026-09-13、検収§2))。BitMEX個別は未確認のまま |

### (iii) ccxtの`fetchLiquidations`(bitmex)

ソース確認(`ccxt/python/ccxt/bitmex.py`、GitHub raw、ログ[15]):
- `fetch_liquidations(symbol, since, limit, params)`は`GET /liquidation`を`symbol`/`startTime`(=since)/`count`(=limit)/`endTime`(=until)付きで呼ぶ**だけ**。親票・本票が実測した公開エンドポイントと**完全に同一**。
- レスポンス例のコメントは`orderID/symbol/side/price/leavesQty`のみで時刻フィールドが無い。
- `parse_liquidation`は`'timestamp': None, 'datetime': None`を**明示的に**セットしている。
- **結論**: ccxt経由でも過去の清算履歴は取れない。ccxtは「現在オープンの清算注文のみ」という同じ制約を継承しているだけで、別のデータソースにアクセスしているわけではない。

### オーナーPCの保全アーカイブ(`deploy/mirror_bitmex.bat`)に何が含まれるか

`scripts/mirror_bitmex_archive.py`(55行目)を読んだ事実:
```
PREFIXES = {"trade": "data/trade/", "quote": "data/quote/", "porl": "data/porl/"}
```
対象は**約定(trade、47.9GB)・最良気配更新(quote、197.8GB)・porl(porl/)の3種類のみ**。
「liquidation」という名のプレフィックスはコード上に無く、S3バケット側にもそもそも存在しない
(親票で確認済み)。**この保全アーカイブに清算情報は含まれない**(事実、コード確認)。

---

## 3. (A3) bitFlyerのSFD・証拠金維持率・強制決済ルールの一次資料

| カテゴリ | 経路 | 結果 |
|---|---|---|
| この環境 | `bitflyer.com/ja-jp/sfd`, `bitflyer.com/en-jp/sfd`, `bitflyer.com/ja-jp/faq/7-23`, `7-33` | **試行して不可(HTTP 403、WAFの`Access Denied`。方法: curl(HTTP/1.1・HTTP/2 双方)およびWebFetch、実測2026-09-12、~~ログ[17]〜[22]~~→ログ[19]〜[22](訂正 2026-09-13、検収§2: [17]はcurlエラー52 Empty reply from server、[18]はcurlエラー92 HTTP/2 stream reset。いずれも403応答ではなくコネクションレベルの失敗のため根拠から除外。実際に403本文`Access Denied`が確認できるのは[19][20][21][22]のみ))**。同じ環境から`lightning.bitflyer.com/docs`(APIリファレンス、別ホスト)は200で到達できており、**地域制限ではなくbitflyer.comメインサイトのWAF/Bot対策**と見られる(推定) |
| オーナーPC | 同上 | **PCでの到達確認が必要**(通常のブラウザ相当のアクセスであれば到達する可能性が高い=推定。この環境固有のブロックである可能性が高いため) |
| 公開アーカイブ・API | `lightning.bitflyer.com/docs`(公式APIリファレンス) | 到達可能(200)だが、**証拠金維持率の数値しきい値(%)やロスカット発動条件の記載はAPIリファレンスには無い**(実測、ログ[24])。これらはFAQ/約款側の文書であり、APIドキュメントの対象外 |
| 第三者データ | 個人ブログ・解説サイト(`zerokara-blog.com`, `zerozero-kasoutasuka.com`等、WebSearchのスニペットで確認) | **一次資料ではない**(本skill §5の規則により一次資料として不採用。参考情報としてのみ扱う) |
| 有料 | 該当なし | 該当なし |

**URLは特定できたが、この環境からは原文を取得できなかった**:
- SFD: `https://bitflyer.com/ja-jp/faq/7-33`(「SFDはいつ付与・徴収されますか」)
- 証拠金維持率・ロスカット: `https://bitflyer.com/ja-jp/faq/7-23`(「追証・ロスカットのルールについて教えてください」)、`7-11`(計算方法)、`7-9`(維持率の確認方法)

WebSearchのAI要約(スニペットベース、**原文の引用検算はできていない**)によれば:
- SFD: 現物とLightning FXの価格乖離が**5%**以上でSFD発生、乖離率に応じて**0.25%〜2.00%**(20%以上で上限)のレートが適用される(推定 — 原文未確認)。
- ロスカット: 証拠金維持率が**50%**を下回ると新規注文が取り消され、全建玉が強制決済される(推定 — 原文未確認)。

**これらの数値はWebSearchの要約であり、CLAUDE.md §5.2・本skill §5の「原文をそのまま引用」の基準を満たしていない。** 一次資料の原文引用は、この環境からのアクセスがWAFで一貫してブロックされているため**未確認のまま**である。オーナーPCまたは通常のブラウザ環境での確認が必要。

---

## 4. `docs/DATA.md` に追記する行の案(未マージ。リード検収待ち)

| 資産 | 所在 | 範囲 | 状態 | 最終確認日 | プローブのログ | 使った単位 |
|---|---|---|---|---|---|---|
| bitFlyer `executions`の清算識別可否 | `https://lightning.bitflyer.com/docs`(公式APIリファレンス)、`https://api.bitflyer.com/v1/executions` | 該当なし(識別フィールド無し) | **試行して不可(公式ドキュメント+実測スキーマとも清算識別フィールド無し。私設APIの追加フィールドは未確認)** | 2026-09-12 | `docs/DATA/probes/20260912_o3c_supp_a_bitflyer_bitmex.log` | 未使用 |
| BitMEX `insurance`(保険基金日次残高) | `https://www.bitmex.com/api/v1/insurance?symbol=XBTUSD` | 2016-02-28〜現在(日次) | 未試行(到達性のみ確認。清算個別イベントの代理にはならない) | 2026-09-12 | 同上 | 未使用 |
| ccxt `fetchLiquidations`(bitmex)の実装 | `ccxt/python/ccxt/bitmex.py`(GitHub) | 該当なし(公開`/liquidation`の薄いラッパーで、過去分は返らない) | **試行して不可(ソース確認済み。timestampを自ら null にしている)** | 2026-09-12 | 同上 | 未使用 |
| Tardis.dev BitMEX `liquidation`チャネル | `https://docs.tardis.dev/historical-data-details/bitmex` | 未確認(チャネル存在は確認、範囲・料金は未取得) | 未試行(到達性のみ確認、深さ・料金は次回調査が必要) | 2026-09-12 | 同上 | 未使用 |
| archive.org(BitMEX/bitFlyer過去スナップショット確認経路) | `web.archive.org` | 該当なし | **試行して不可(この環境からWebFetch・curl双方で到達不能。方法: WebFetch(ツール側ブロック)、curl HTTPS(接続リセット)。実測2026-09-12)** | 2026-09-12 | 同上 | 未使用。オーナーPCでの到達確認が必要 |
| bitFlyer SFD公式FAQ | `https://bitflyer.com/ja-jp/faq/7-33` | 未確認(原文未取得) | **試行して不可(HTTP 403、WAF。方法: curl/WebFetch、実測2026-09-12)** | 2026-09-12 | 同上 | 未使用。オーナーPCでの到達確認が必要 |
| bitFlyer 証拠金維持率・ロスカット公式FAQ | `https://bitflyer.com/ja-jp/faq/7-23`, `7-11`, `7-9` | 未確認(原文未取得。WebSearchスニペットのみ: 維持率50%が閾値との情報あり=推定) | **試行して不可(HTTP 403、WAF。方法: curl/WebFetch、実測2026-09-12)** | 2026-09-12 | 同上 | 未使用。オーナーPCでの到達確認が必要 |
| `deploy/mirror_bitmex.bat`の保全対象範囲 | `scripts/mirror_bitmex_archive.py`(PREFIXES定義) | trade/quote/porlの3種のみ、liquidationは対象外 | 取得済(コード確認、ダウンロードそのものではない) | 2026-09-12 | 同上(コード確認、プローブではない) | 未使用 |

---

## 5. 「取れない」と書いた項目の一覧(範囲・方法・ログの再掲)

1. bitFlyer `executions`(公開API+公式APIドキュメント)に清算識別フィールドが無い — 一次資料本文とレスポンススキーマの両方で確認、ログ[1][2][5]。
2. BitMEX `/liquidation`にstartTime指定しても過去分が返らない — 実測、ログ[8]。
3. archive.org(web.archive.org)への到達 — WebFetchはツール側ブロック、curlはHTTPS接続リセット、ログ[9]〜[14]。
4. bitflyer.com メインサイト(SFD/FAQページ)への到達 — HTTP 403(WAF)、curl(HTTP/1.1・HTTP/2)・WebFetch全てで確認、ログ[17]〜[22]。

---

## 6. 判定はしていない

本票はデータの当否・戦略への使えなさを判定していない(research-squad SKILL §2の禁止事項)。
上記は到達性・スキーマ・一次資料の存否の実測であり、O-3cの機構仮説の成否とは無関係である。
