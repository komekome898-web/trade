# O-3c 調達票 5 本 検収 第1部: 整合性の検査(2026-09-13)

**本票は整合性の検査であり、採否の判断を含まない(判断はリード)。** 以下は「調達票の主張」と「対応する
プローブの生ログ」の事実の突き合わせのみを行った結果である。

対象: `O3C_PROCUREMENT_2026-09-12.md`(本票)、`_SUPP_A_`、`_SUPP_B_`、`_SUPP_C_HYPERLIQUID_`、
`_SUPP_D_VENUE_UNIVERSE_`(いずれも `docs/DATA/surveys/`)と対応する5本のログ(`docs/DATA/probes/`)。

---

## §1 検査の要約表

| 調達票 | 照合した主張数(概算) | 一致 | 不一致 | ログに該当なし(先頭200字外・記録形式の限界) | 「取れない」書式の欠け | 印が強すぎる疑い | 検算の不一致 |
|---|---|---|---|---|---|---|---|
| 本票(親票) | 約25 | 22 | 1(CoinGlass 401) | 2(BitMEX/Bybitのフォルダ名列挙、BitMEX swagger詳細) | 0 | 1(CoinGlass「401」を事実と印) | 0 |
| 補遺A | 約20 | 17 | 1(ログ[17][18]がHTTP403ではない) | 1(swagger詳細の再引用) | 0 | 0 | 0 |
| 補遺B | 約22 | 20 | 0 | 2(Binance Vision metrics CSVの行内容、Gate limit=2000の件数) | 2(§6の一部行に方法の明記が表参照頼み) | 1(CSVの重複行の有無を「事実」と印) | 1(63エントリ→実測61) |
| 補遺C | 約15 | 13 | 1(OKX vol24hを$10.51Bと誤読) | 0 | 0 | 0 | 0 |
| 補遺D | 約25 | 22 | 1(要点#1の「9位相当」と表の8位が矛盾) | 2(WhiteBIT13件・bitFlyer volumeがログの先頭200字外) | 0 | 0 | 1(Hyperliquid検算のmarkPxがログに見えない) |

(件数は本検査で個別に照合した主張の概算。網羅的な逐語カウントではない。)

---

## §2 不一致・欠け・疑いの全件明細

1行1件。ファイル・行番号は各調達票内の行番号(Read出力の行番号)。

| # | 調達票:行 | 記述 | ログ:行 | 問題 |
|---|---|---|---|---|
| 1 | 本票:39,94,134,155 / 補遺A:64(転記) | 「CoinGlass … HTTP 401(鍵必須)」と繰り返し記載 | `20260912_o3c_liquidation_history.log:86` | ログの実際の HTTP ステータスは **200**。本文 JSON が `{"code":"401","msg":"API key missing."}` を返しており、「401」はアプリケーション層のエラーコードで、トランスポート層の HTTP ステータスではない。調達票は両者を区別せず「HTTP 401」と書いている(HTTPコード欄の一致確認で不一致) |
| 2 | 補遺A:90(A3の表・この環境行) | 「ログ[17]〜[22]」を一括で「HTTP 403、WAFの`Access Denied`」の根拠として引用 | `20260912_o3c_supp_a_bitflyer_bitmex.log:[17][18]` | [17]は curl エラー52(Empty reply from server)、[18]は curl エラー92(HTTP/2 stream reset)。いずれも **HTTP 403 ではなく、コネクションレベルの失敗**。実際に403本文(Access Denied)が確認できるのは[19][20][21][22]のみ。範囲[17]〜[22]の一括引用は不正確 |
| 3 | 補遺B:12(冒頭) | 「プローブの生ログ…63 エントリ」 | `20260912_o3c_supp_b_oi_vap_gate1m.log` 全体 | 実際の GET エントリ数は **61**(`grep -c` で確認)。63 は過大 |
| 4 | 補遺C:132(C4表、OKX行) | 「105,123.55 BTC(`volCcy24h`)/ ≒$10.51B(`vol24h`のUSDT建て名目)」 | `20260912_o3c_supp_c_hyperliquid.log:28` | ログの実値は `vol24h:"10512355.09"`。これは `volCcy24h`(105,123.55)を0.01で割った値と一致し(105123.5509/0.01=10512355.09)、**契約数量(コントラクト数)であって USD 名目値ではない**。「≒$10.51Bのドル名目」という換算はログの値の性質を読み違えており、実際の値(10,512,355.09)を USD だと読んでも$10.51M程度にしかならず、いずれにせよ$10.51Bという記載を裏付けるログ上の根拠はない |
| 5 | 補遺D:22(要点#1) | 「…MEXC→…→Hyperliquid(**9位相当**)の順」 | 補遺D:48(D1表、8行目がHyperliquid) | 同じ文書内のD1表ではHyperliquidは**8位**(Binance,Gate,Bybit,WEEX,MEXC,Bitget,Toobit,Hyperliquidの8番目)。要点表の「9位相当」と本文の表が矛盾している(内部不整合) |
| 6 | 本票:74 | 「トップレベルフォルダは `porl/`, `quote/`, `trade/` の 3 つのみ」(BitMEX S3) | `20260912_o3c_liquidation_history.log:66` | ログの`head200`は先頭200文字で切れており、実際のフォルダ名(CommonPrefixes)を含む本体部分は記録されていない。方法・URL・HTTPコード(200)は一致するが、**フォルダ名の具体的な列挙自体はログから確認できない**(ログの記録仕様上の限界) |
| 7 | 本票:50 | 「`kline_for_metatrader4/`, `premium_index/`, `spot_index/`, `trading/`, `spot/` の5フォルダのみ」(Bybit) | `20260912_o3c_liquidation_history.log:59` | 同上。head200が先頭200文字で切れており、5フォルダの具体名はログから確認できない |
| 8 | 本票:22 / 補遺A:19,69-71 | BitMEXのLiquidationオブジェクトが`orderID/symbol/side/price/leavesQty`のみ、という具体的フィールド列挙(swagger.json / ccxtソース) | `20260912_o3c_liquidation_history.log:68`, `20260912_o3c_supp_a_bitflyer_bitmex.log:[15]` | swagger.json(197KB)・ccxtソース(161KB)ともログのhead200は先頭200文字のみで、具体的なフィールド列挙はログ本文に残っていない。到達性(200、バイト数)は一致するが、フィールド列挙の正確性はログ単体では検証できない |
| 9 | 補遺B:23(差分表#1) | Binance Vision `metrics` CSVの列内容・「UM実測ではタイムスタンプに重複行あり=288ユニーク、CMは重複なし288行」 | `20260912_o3c_supp_b_oi_vap_gate1m.log:10-11` | ログの head200 は `(zip binary)` のプレースホルダのみで、解凍後のCSV行内容はログに一切記録されていない。288行/重複の有無はログから検証不能(ダウンロードした本人の後日的な検査結果である可能性はあるが、ログにその形跡がない) |
| 10 | 補遺B:135(B4) | 「1リクエストあたり実測で約1,990件返る(`limit=2000`指定時)」 | `20260912_o3c_supp_b_oi_vap_gate1m.log:62` | ログには `bytes=1223721` のみが記録され、レコード件数を示す `records=` 等のフィールドが無い。1,990件という数字はログから直接検算できない(1レコード平均バイト数からの逆算と推定されるが、その計算過程はログにない) |
| 11 | 補遺D:69(bitFlyer行) | 「1,160.87 BTC(24h出来高)」 | `20260912_o3c_supp_d_venue_universe.log:86` | head200が `"ltp":` の途中で切れており、`volume` フィールドがログの記録範囲に入っていない。GMO側(同ログ89行目)は`"volume":"1261.395"`が記録されており検算できるが、**bitFlyer側の値はログから検算できない** |
| 12 | 補遺D:94(WhiteBIT行) | 「公開エンドポイント13件を全カテゴリ確認」 | `20260912_o3c_supp_d_venue_universe.log:82` | ログはWebFetchの結果を要約した1行の説明文のみで、13件の実際のリスト(生データ)は記録されていない。調達票とログの文言はほぼ同一だが、これは同一著者の記述の転記であり独立した裏付けにはならない |
| 13 | 補遺D:97(BingX行) | 「推測RESTinsuranceFundは的外れで404相当」 | `20260912_o3c_supp_d_venue_universe.log:37,60` | 実際のHTTPステータスは200(`code:100400`のJSONエラー本文)。「404相当」と明記して近似であることを示してはいるが、#1のCoinGlassの件と同種の「アプリ層コードとHTTPステータスの混同」に近い表現である |

**問題なしと判定した項目**: 上記13件以外に照合した主張(本票の Gate 90日確保件数=79,183件〈`backtest_data/gate_liquidations_20260908/BTC_USDT.manifest.json`の`rows`と一致、検算済み〉、Binance COIN-M liquidationSnapshotの2023-06-25〜2024-10-14・2024-06-01単発欠測、OKX 1分足2019-10-01空/2020-01-01存在、Gate candlesticksの5日OK/8日NG、Gate contract_statsの179日OK/180日超エラー、OKX OI history・LS比の各境界、Hyperliquid candleSnapshotの3日OK/4日NG、Hyperliquid C4数値(OI・出来高・funding)、HTX/KuCoin/Phemex/Kraken/dYdX/Paradexの個別到達結果 等)は、ログの該当行とHTTPコード・URL・数値がいずれも一致した。**なし(この範囲では他に不一致は検出されていない)**。

---

## §3 検算の結果

| # | 主張 | 報告値 | ログからの計算値 | 一致か |
|---|---|---|---|---|
| 1 | 本票 1.5: Gate清算90日分の確保件数 | 79,183件 | `backtest_data/gate_liquidations_20260908/BTC_USDT.manifest.json` の `rows: 79183`(ログではなく既存マニフェストで検算) | 一致 |
| 2 | 本票 冒頭: プローブログの行数 | 89行 | `wc -l` = 89 | 一致 |
| 3 | 補遺A 冒頭: プローブログのエントリ数 | 27エントリ | ログ内 `[1]`〜`[27]` の番号付け = 27 | 一致 |
| 4 | 補遺B 冒頭: プローブログのエントリ数 | 63エントリ | `grep -c` による GET 行数 = 61 | **不一致**(§2 #3) |
| 5 | 補遺B B4: 90日×1分の点数、必要リクエスト数 | 129,600点、約65リクエスト | 90×24×60=129,600(算術は正しい)。129,600/1,990≒65.1(算術は正しいが「1,990件」自体がログから検算不能、§2 #10) | 算術は一致・入力値は未検算 |
| 6 | 補遺C C4 / 補遺D D1: Hyperliquid BTC OI・出来高等の現在値 | OI 35,904.56〜35,922.33 BTC(取得時刻により差)、dayNtlVlm ≒$3.58B 等 | ログの `metaAndAssetCtxs` 抽出値と一致(補遺C: 35904.56266 / 補遺D: 35922.3333、いずれも別時刻のスナップショットとして整合) | 一致 |
| 7 | 補遺C/D: OKX BTC-USDT-SWAP OI(USD) | $2,120,856,867 前後 | ログ `oiUsd` = 2120856866.98745904816477(補遺D) / 2120917274.45772925869508(補遺C、別時刻) | 一致(四捨五入も正しい) |
| 8 | 補遺C/D: OKX BTC-USDT-SWAP 24h出来高(USD換算) | 「≒$10.51B」 | ログ `vol24h`=10512355.09 は USD ではなく契約数量相当(§2 #4) | **不一致** |
| 9 | 補遺D D1: Hyperliquidの検算(35,922.33 BTC × markPx ≒ $2,775,867,000、差0.03%) | 差0.03%、整合 | markPx の値自体がログのhead200に写っていないため乗算の再現ができない。算術結果の妥当性は評価できるが入力値は未検算 | 検算不能(入力値がログに無い) |

---

## §4 未マージの確認結果

`docs/DATA.md` と `docs/STRATEGY_IDEAS.md` を対象に、5本の調達票が挙げた資産名・エンドポイント名・
プローブのログファイル名(`20260912_o3c_*`)で検索した。

- `grep -n "20260912_o3c" docs/DATA.md docs/STRATEGY_IDEAS.md` → **該当なし**
- `grep -n "liquidationSnapshot|contract_stats|Hyperliquid|hyperliquid|WhiteBIT|WEEX|Toobit" docs/DATA.md docs/STRATEGY_IDEAS.md` → **該当なし**
- `docs/STRATEGY_IDEAS.md` の O-3c / O-6 の記述(29〜45行目)は本調達票発行前と同一の文言で、
  今回の調達票の実測内容(取引所別の遡れる深さ・清算識別可否等)は反映されていない

**結論: 5本の調達票の内容は `docs/DATA.md` / `docs/STRATEGY_IDEAS.md` に無審査でマージされていない。**

**関連する観察(未マージ違反ではないが記録)**: `docs/DATA.md` 93行目に「BitMEX 保険基金 日次残高」の行が
2026-09-12付・状態「取得済」で既に存在する(2016-02-28〜2026-09-11、9,804レコード、プローブログ
`docs/DATA/probes/20260912_bitmex_insurance_fetch.log`)。これは補遺Aが実測した`/api/v1/insurance`
(サンプル数件のみ)とは**別のログ・別の取得作業**(本件収の対象5ログには含まれない)であり、
補遺Aの調達候補行の文言がそのままマージされたわけではない。ただし同一エンドポイントについて、
補遺Aの調達提案とは独立に、より大規模な取得が同日中に既に実行・記録されている点は事実として記す。

---

## 付記: 「取れない」の書式(範囲・方法・ログ)の欠けについて

5本を通じて、「試行して不可」と明記した項目は総じて範囲・方法・ログパスの3点を備えていた
(各票の§末尾の再掲リスト、および`docs/DATA.md`追記候補の各行を個別に確認)。明確な「欠け」は
検出されなかった。補遺Bの§6再掲リストのみ、方法の記載が再掲行内には無く同票内の本表を
参照しないと分からない箇所が2件あったが、同一文書内で完結しており実質的な欠落とは言えないため
「欠け」としてはカウントしていない(§1の要約表に注記として残した)。

---

## §5 訂正の記録(2026-09-13)

**方法**: §2・§3で不一致とされた5件(#1〜#5、上記番号に対応)について、生ログを正として調達票側を
機械的に訂正した(元の誤り箇所は削除せず取り消し線+訂正後の値を追記、各所に
「(訂正 2026-09-13、検収§2)」を付記)。判断・結論は変更していない。新規の調査・プローブは行っていない。

| # | ファイル:行 | 訂正前 | 訂正後 |
|---|---|---|---|
| 1a | `O3C_PROCUREMENT_2026-09-12.md`:39 | CoinGlass: 試行して不可(HTTP 401、鍵必須。…) | 試行して不可(HTTP 200(本文JSONが`{"code":"401","msg":"API key missing."}`)、鍵必須。…) |
| 1b | `O3C_PROCUREMENT_2026-09-12.md`:94 | 未確認(鍵必須、401) | 未確認(鍵必須、HTTP 200・本文JSON `code:401`) |
| 1c | `O3C_PROCUREMENT_2026-09-12.md`:134 | 試行して不可(HTTP 401。方法: GET、実測 2026-09-12) | 試行して不可(HTTP 200(本文JSONが`code:401`「API key missing」)。方法: GET、実測 2026-09-12) |
| 1d | `O3C_PROCUREMENT_2026-09-12.md`:155 | CoinGlass 個別イベント清算エンドポイント — HTTP 401(鍵必須)。 | 同 — HTTP 200(本文JSONが`code:401`)(鍵必須)。 |
| 1e | `O3C_PROCUREMENT_SUPP_A_2026-09-12.md`:64 | CoinGlass: 親票で既報(鍵必須、401)。 | 親票で既報(鍵必須、HTTP 200・本文JSON `code:401`)。 |
| 2 | `O3C_PROCUREMENT_SUPP_A_2026-09-12.md`:90 | 403 の根拠としてログ[17]〜[22]を一括引用 | 根拠をログ[19]〜[22]に限定。[17](curlエラー52 Empty reply)・[18](curlエラー92 HTTP/2 stream reset)は403応答ではなくコネクションレベルの失敗として別記し除外 |
| 3 | `O3C_PROCUREMENT_SUPP_B_2026-09-12.md`:12 | プローブの生ログ…(63 エントリ、…) | …(61 エントリ、…)〈`grep -c`実測〉 |
| 4a | `O3C_PROCUREMENT_SUPP_C_HYPERLIQUID_2026-09-12.md`:132(OKX行) | 105,123.55 BTC(`volCcy24h`、≒$10.51B `vol24h`のUSDT建て名目) | `vol24h`(10,512,355.09)はコントラクト枚数(`volCcy24h`÷0.01と一致、USD名目ではない)。ドル換算(自己算出): 同時刻ticker `last`=77,290 USDT(ログ28行目)使用で 105,123.5509 BTC×77,290 ≒ $8.12B |
| 4b | `O3C_PROCUREMENT_SUPP_D_VENUE_UNIVERSE_2026-09-12.md`(D1表末尾に注記追加) | (該当する誤記述は無し) | D1の順位表はCoinGecko出典1の建玉(OI)降順であり、OKX自社API`vol24h`の単位取り違え(4a)はD1のどの数値・順位にも使われていないため**順位表(1〜15位)は訂正前後で不変**、と明記 |
| 5 | `O3C_PROCUREMENT_SUPP_D_VENUE_UNIVERSE_2026-09-12.md`:22(要点#1) | …Hyperliquid(9位相当)…の順 | …Hyperliquid(8位、D1表の順位と統一)…の順 |

**順位の変化の有無(訂正4bに関連)**: 補遺Dの§D1順位表(建玉USD降順、1〜15位)は**訂正前→訂正後で変化なし**
(単位の取り違えは出来高列の一部数値のみに影響し、順位付けの根拠である建玉には影響しないため)。

---

## §6 台帳への反映(2026-09-13)

Binance COIN-M アーカイブの実取得(`backtest_data/binance_cm_o3c_20260913/`)により判明した欠測を受けて、
`docs/PHASE2/O3C/DATA_AVAILABILITY.md` を訂正し、調達票5本+実取得README由来の候補行を `docs/DATA.md` §2
へ反映した(機械的な訂正・反映のみ。判断・結論は変更していない)。

### (1) `docs/DATA.md` §2 に追加した行(資産名、20件)

1. Binance COIN-M BTCUSD_PERP liquidationSnapshot
2. Binance COIN-M BTCUSD_PERP metrics
3. Binance USD-M liquidationSnapshot アーカイブ(全シンボル、KeyCount=0)
4. BitMEX 公開バルクアーカイブの清算専用フォルダ(存在しない)
5. CoinGlass 個別イベント清算(`/api/futures/liquidation/order`)
6. OKX 1分足(無期限、history-candles)
7. Gate 1分足(candlesticks、真のOHLC)
8. ccxt `fetchLiquidations`(bitmex)実装
9. Tardis.dev BitMEX `liquidation`チャネル
10. Binance USD-M BTCUSDT metrics
11. Binance COIN-M BTCUSD_PERP aggTrades/trades
12. OKX rubik open-interest-history(保持期間の実測)
13. OKX rubik long-short-account-ratio(保持期間の実測)
14. Gate contract_stats(建玉・L/S比・mark_price)
15. BitMEX instrument 建玉(openInterest、現在値のみ)
16. CryptoCompare(CoinDesk Data) histominute(gate.io)
17. Hyperliquid `userFills`/`userFillsByTime`
18. Hyperliquid `candleSnapshot`
19. Hyperliquid `metaAndAssetCtxs`
20. Hyperliquid S3アーカイブ(板 L2Book想定)

### (2) 重複のため追加しなかったもの

- Bybit 公開バルクアーカイブの清算フォルダ無し(親票候補) — `docs/DATA.md` 既存行(Bybit静的アーカイブ
  `public.bybit.com`、「板・清算・資金調達率は無く約定のみ」)に既に記載済み
- BitMEX 1分足(bucketed trade REST、親票候補) — `docs/DATA.md` 既存行(BitMEX XBTUSD 1秒足、2017〜2021、
  取得済のローカルアーカイブ)が同一資産をより高い状態(取得済)で既に包含
- BitMEX 保険基金 日次残高(補遺A候補) — `docs/DATA.md` 既存行(2026-09-12付、状態「取得済」、
  2016-02-28〜2026-09-11・9,804件)に既に記載済み(本検収票冒頭の「関連する観察」で既報)
- Bybit v5 open-interest(補遺B候補) — `docs/DATA.md` 既存行(Bybit REST API 全般、HTTP 403 CloudFront
  地域ブロック)が同一の否定的事実を既に包括的に記載

### (3) 既存行を更新したもの

なし(該当する既存行はいずれも期間・状態が現行のまま有効で、更新の必要は無かった)。

### (4) `DATA_AVAILABILITY.md` で訂正した箇所

- 冒頭注記: 2026-09-13の実取得で欠測が判明し窓を訂正した旨を追記(取り消し線方式ではなく新規注記行)
- §1主表: Binance COIN-M の「清算イベント」行(期間・状態を472/478日の実測に更新)、「建玉・L/S比」行
  (期間・状態をO-3c窓内379/478日の実測に更新)。「約定」行は本体未取得のため無変更
- §2a: Binance COIN-M「清算+約定」行 — 約定側が本体未取得のため「約477日」を撤回し「不明」に訂正
- §2b: Binance COIN-M「3点が揃う窓」行 — liquidationSnapshot∩metrics の実ファイル突き合わせにより、
  「約477日」を撤回し、**375日・7区間**(2023-06-25〜09-08[76日]/09-10〜09-22[13日]/09-24[1日]/
  09-26〜11-18[54日]/11-20〜2024-03-03[105日]/06-09〜06-10[2日]/06-13〜10-14[124日])に訂正
- §4: 「Binance COIN-M `liquidationSnapshot` … 本体一括取得は未実施」行を「取得済(2026-09-13、
  472/478日)」に訂正

いずれも元の誤った値は取り消し線で残し、訂正後の値を追記した(追記専用の原則)。

---

## §7 台帳 §1 への反映(2026-09-13)

補遺A(`O3C_PROCUREMENT_SUPP_A_2026-09-12.md`)のうち bitFlyer 自身の事実(A1・A3)を
`docs/DATA.md` §1 へ反映した(機械的な反映のみ。判断・結論は変更していない)。BitMEX に関する行
(A2・§4候補)は §2 の領域のため、重複を grep で確認したうえで §2 側に反映した。

### (1) 更新した既存行(§1、1件)

- 「清算・強制決済(losscut) 履歴」— 旧内容(状態: 試行して不可。範囲・方法: 「本 pilot では未探索」、
  最終確認日 2026-09-11、ログ `20260911_crypto_cfd_board_liq_funding_basis.log`)を、補遺A A1 の実測に
  基づき更新: 範囲・方法を「bitFlyer Lightning の公開 API リファレンスと実測スキーマ(`/v1/executions`・
  `getticker`・`getboardstate`)の両方で、約定に清算を識別するフィールドが存在しないことを確認。清算履歴の
  専用エンドポイントも見つからない」に、最終確認日を 2026-09-12 に、プローブのログを
  `docs/DATA/probes/20260912_o3c_supp_a_bitflyer_bitmex.log` に、使った単位を「O-3c(調達、2026-09-12)」に
  書き換えた。状態の値自体は「試行して不可(範囲・方法)」のまま(内容のみ更新)。

### (2) 追加した行(3件)

- §1: 「bitFlyer SFD・証拠金維持率・ロスカット閾値の一次資料(公式FAQ)」— 補遺A A3 に基づく新規行。
  所在は補遺Aから正確に転記(SFD: `https://bitflyer.com/ja-jp/faq/7-33`、証拠金維持率・ロスカット:
  `https://bitflyer.com/ja-jp/faq/7-23`, `7-11`, `7-9`)。状態は「試行して不可(範囲・方法)」
  (この環境から curl HTTP/1.1・HTTP/2・WebFetch の3通りで HTTP 403(WAF)、`lightning.bitflyer.com/docs`
  は同一環境から200で到達できることからホスト固有の遮断と判断)。**数値の閾値(SFD 乖離率・維持率%)は
  補遺Aで原文未確認のため台帳には記載していない。**
- §2: 「archive.org(public.bitmex.com 過去スナップショット確認経路)」— 補遺A A2(ii) に基づく新規行
  (grep で §2 に該当行が無いことを確認済み)。状態は「試行して不可(WebFetch はツール側ブロック、curl は
  HTTPS 接続リセット)」。
- §2: 「`deploy/mirror_bitmex.bat` の保全対象範囲」— 補遺A に基づく新規行(grep で §2 に該当行が無いことを
  確認済み)。状態は「取得済(コード確認、ダウンロードそのものではない)」。対象は trade/quote/porl の3種の
  みで liquidation は対象外。

### (3) 重複のため触らなかったもの(§2、3件)

- ccxt `fetchLiquidations`(bitmex)実装 — `docs/DATA.md` §2 に既存行あり(§6反映#8 で既に追加済み)。
- Tardis.dev BitMEX `liquidation`チャネル — `docs/DATA.md` §2 に既存行あり(§6反映#9 で既に追加済み)。
- BitMEX 保険基金 日次残高(insurance) — `docs/DATA.md` §2 に既存行あり(2026-09-12付「取得済」、
  §6の「関連する観察」で既報の別ログ・別取得作業)。補遺A A2(i) のサンプル数件のみの実測はこの既存行を
  上書きしていない。
