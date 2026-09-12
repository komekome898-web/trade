# Binance COIN-M (BTCUSD_PERP) liquidationSnapshot + metrics

O-3c(強制決済フローの直接観測)向けの一括取得。Binance Vision は USD-M 側の同種アーカイブを既に
配信停止しており(全期間 KeyCount=0)、COIN-M 側も 2024-10-14 で配信が止まっている
(アーカイブごと取り下げられる可能性があるため、取り下げ前に一括取得した)。

## 取得情報

- 取得日時(UTC): 2026-09-12T16:21:00Z 〜 2026-09-12T16:43:53Z(liquidationSnapshot 約15分 + metrics 約8分)
- URL: `https://data.binance.vision/data/futures/cm/daily/<kind>/BTCUSD_PERP/BTCUSD_PERP-<kind>-YYYY-MM-DD.zip`
  (+同名 `.CHECKSUM`)。`<kind>` = `liquidationSnapshot` / `metrics`
- スクリプト: `scripts/fetch_binance_cm_o3c.py`(新規作成。既存の `scripts/fetch_binance_vision.py` は
  `spot`/`futures/um` の klines・aggTrades 専用で COIN-M の liquidationSnapshot/metrics に対応していないため、
  新規に書いた。`$HTTPS_PROXY` 経由、CA バンドル `/root/.ccr/ca-bundle.crt`、日次 zip + `.CHECKSUM` を取得して
  sha256 検証、キャッシュ済みで検証済みの zip は再取得しない)
- 期間: 2023-06-25 〜 2024-10-14(全478日、UTC日次)
- 取得ログ: `docs/DATA/probes/20260913_binance_cm_o3c_fetch.log`(1日1行 ×478日 ×2種別=956行。各行:
  UTC時刻・kind・day・URL・HTTPコード・バイト数・CHECKSUM一致可否)

## 日ごとの取得可否(欠測日を明記)

### liquidationSnapshot: 478日中 **472日 OK / 6日 欠測(404)**

欠測日: `2023-09-09`, `2023-09-23`, `2023-09-25`, `2024-06-01`, `2024-06-11`, `2024-06-12`
(`2024-06-01` は事前報告どおりの既知欠測。他の5日は今回の取得で新たに確認)。
上記6日以外の472日はすべて OK(zip取得・CHECKSUM検証とも成功)。

### metrics: 478日中 **379日 OK / 99日 欠測(404)**

欠測日は2グループ:
- 単発2日: `2023-09-25`, `2023-11-19`
- **連続97日の大穴**: `2024-03-04` 〜 `2024-06-08`(この期間は1日も配信されていない)

上記99日以外の379日はすべて OK(zip取得・CHECKSUM検証とも成功)。
**注記(事実)**: metrics の連続欠測期間はこの取得で確認した事実であり、原因は未確認(Binance側の配信欠落か、
COIN-M metrics 自体がこの期間存在しなかったかは未調査)。liquidationSnapshot 側は同期間で欠測していない
(`2024-06-01/11/12` の3日のみ)ため、2種別間で欠測パターンが一致しない。

## aggTrades(2026-09-13 追記: 取得完了。以下は取得前の見積りメモ、原文のまま残す)

取得は行っていない(委任元の指示により、この回は容量見積のみで終える)。

- サンプル13日(期間全体に分散: 2023-06-25, 08-01, 10-01, 12-01 / 2024-02-01, 03-15, 04-15, 06-01, 06-15,
  08-01, 09-01, 10-01, 10-14)の zip サイズ実測: 最小 1,086,108 bytes、最大 9,483,027 bytes、
  13日平均 3,089,463 bytes/日
- 478日換算の見積り: 平均 × 478 ≈ **1.48 GB**(サンプル13日のみの外挿。実測ではない)
- 見積りは 10 GB を大きく下回るため容量上の障害はない(このコンテナの空き容量は約13GB)が、
  **取得の実施はこの回のスコープ外**(委任元指示)。次回、この見積りとともに実施可否を判断すること。

## aggTrades 取得結果(2026-09-13 実施。上記見積りに基づきリード承認済みの取得単位)

- 取得日時(UTC): 2026-09-12T16:45:49Z 〜 2026-09-12T17:00:07Z(約14分)
- URL: `https://data.binance.vision/data/futures/cm/daily/aggTrades/BTCUSD_PERP/BTCUSD_PERP-aggTrades-YYYY-MM-DD.zip`
  (+同名 `.CHECKSUM`)
- スクリプト: `scripts/fetch_binance_cm_o3c.py --kind aggTrades`(既存スクリプトを流用。sha256 検証・失敗時1回再取得は実装済み)
- 期間: 2023-06-25 〜 2024-10-14(全478日、UTC日次)
- 取得ログ: `docs/DATA/probes/20260913_binance_cm_o3c_fetch.log`(1日1行 ×478行、kind=aggTrades。
  各行: UTC時刻・kind・day・URL・HTTPコード・バイト数・CHECKSUM一致可否)

### 日ごとの取得可否(欠測日を明記)

**478日中 475日 OK / 3日 欠測(404) / CHECKSUM失敗 0日**(再取得は一度も発動しなかった)。

欠測日: `2023-09-25`, `2024-06-11`, `2024-06-12`
(この3日はいずれも liquidationSnapshot 側でも欠測と記録済みの日と一致する。原因は未調査 — 事実として
「この3日はCOIN-M側のアーカイブ自体が404だった」ことのみ確認、Binance側の配信欠落か該当日にデータが
存在しなかったかは未調査)。

上記3日以外の475日はすべて OK(zip取得・CHECKSUM検証とも成功)。

### ファイル数・バイト数(実測)

| kind | 対象日数 | OK | 欠測 | CHECKSUM失敗 | zipファイル数 | 総バイト数(実測、zip+.CHECKSUM) |
|---|---|---|---|---|---|---|
| aggTrades | 478 | 475 | 3 | 0 | 475 | 1,263,157,187 bytes(約1.18 GiB / 1.26 GB) |

ファイル総数(zip + .CHECKSUM 合計): **950**(475 × 2)。

### CHECKSUM検証

全475件のダウンロードについて、Binance Vision配布の `.CHECKSUM`(sha256)との一致を検証。
**成功475 / 失敗0**。取得後に全475件を独立に再検証(sha256sum突合)しても不一致は0件だった。

### 中身の確認(1日分を解凍・列名と先頭3行)

`BTCUSD_PERP-aggTrades-2023-06-25.zip`

列名: `agg_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker`

```
261091940,30542.8,1.0,640356821,640356821,1687651202018,true
261091941,30542.9,12.0,640356822,640356822,1687651203499,false
261091942,30542.8,2.0,640356823,640356823,1687651207509,true
```

### git の扱い(実測根拠)

**実測 1,263,157,187 bytes(約1.18 GiB)は100MBの閾値を大きく超えるため、本体(zip・.CHECKSUM)を
`.gitignore` で除外した**(追加行: `backtest_data/binance_cm_o3c_20260913/aggTrades/**/*.zip` と
同 `*.CHECKSUM`)。README.md・MD5SUMS はこれまでの liquidationSnapshot/metrics と同様に追跡対象のまま
残している(このディレクトリ配下のもう一つの `MD5SUMS` に aggTrades 分475件×2=950行を追記済み)。

## ファイル数・バイト数(実測)

| kind | 対象日数 | OK | 欠測 | CHECKSUM失敗 | zipファイル数 | 総バイト数(apparent, zip+.CHECKSUM) |
|---|---|---|---|---|---|---|
| liquidationSnapshot | 478 | 472 | 6 | 0 | 472 | 1,240,117 bytes (1.2MB) |
| metrics | 478 | 379 | 99 | 0 | 379 | 2,471,902 bytes (2.4MB) |
| **合計** | | **851** | **105** | **0** | **851** | **3,712,019 bytes (約3.5MB)** |

ファイル総数(zip + .CHECKSUM 合計): **1,702**(liquidationSnapshot 944 = 472×2、metrics 758 = 379×2)。

## CHECKSUM検証

全851件のダウンロード(liquidationSnapshot 472 + metrics 379)について、Binance Vision配布の
`.CHECKSUM`(sha256)との一致を検証。**成功851 / 失敗0**。失敗時は1回再取得のリトライ実装済みだが、
今回は一度も発動しなかった(取得ログの956行がすべて1回目の試行で `OK` または `404`)。

## `MD5SUMS`

このディレクトリ配下の全ファイル(README.md自身を除く)のmd5。`md5sum -c MD5SUMS` で検証可能
(ディレクトリを cd してから実行)。1,702行(liquidationSnapshot + metrics 時点)。
**2026-09-13 追記: aggTrades 分950行(475ファイル×2)を追記し、現在は合計2,653行。**

## 中身の確認(1日分を解凍・列名と先頭3行)

### liquidationSnapshot(`BTCUSD_PERP-liquidationSnapshot-2023-06-25.zip`)

列名: `time,side,order_type,time_in_force,original_quantity,price,average_price,order_status,last_fill_quantity,accumulated_fill_quantity`

```
1687656471926,BUY,LIMIT,IOC,7,30741.3,30631.6,FILLED,6,7
1687656471926,BUY,LIMIT,IOC,7,30741.3,30631.6,FILLED,6,7
1687656473356,BUY,LIMIT,IOC,43,30756.6,30631.6,FILLED,1,43
```

### metrics(`BTCUSD_PERP-metrics-2023-06-25.zip`)

列名: `create_time,symbol,sum_open_interest,sum_open_interest_value,count_toptrader_long_short_ratio,sum_toptrader_long_short_ratio,count_long_short_ratio,sum_taker_long_short_vol_ratio`

```
2023-06-25 00:00:00,BTCUSD_PERP,5578700.00000000,18265.00911826,"","","",0.00855776
2023-06-25 00:05:00,BTCUSD_PERP,5578209.00000000,18261.90678854,"","","",1.19645130
2023-06-25 00:10:00,BTCUSD_PERP,5574401.00000000,18244.30356547,"","","",2.90028011
```

(`count_toptrader_long_short_ratio` 等が空文字列になっている行がある。原因未調査。
`sum_taker_long_short_vol_ratio` は全行で値が入っている。)

## git の扱い(実測根拠)

合計 **3,712,019 bytes(約3.5MB)** — 100MBの閾値を大きく下回るため、**本体(zip・.CHECKSUM)も
README・MD5SUMSと同様に追跡対象にしてよい**。`.gitignore` への除外行は不要(追加していない)。

## この環境から到達可能だったか

**到達可能**(禁止事由なし)。`$HTTPS_PROXY` 経由・CA バンドル `/root/.ccr/ca-bundle.crt` で
`data.binance.vision` への全リクエストが成功(404は「日が存在しない」であり経路の失敗ではない)。

## `docs/DATA.md` §2 追記案(**未反映**。台帳への追記は委任元が判断)

| 資産 | 所在 | 範囲 | 状態 | 最終確認日 | プローブのログ | 使った単位 |
|---|---|---|---|---|---|---|
| Binance COIN-M BTCUSD_PERP liquidationSnapshot(強制決済イベント) | `backtest_data/binance_cm_o3c_20260913/liquidationSnapshot/BTCUSD_PERP/`(日次zip、472/478日) | 2023-06-25〜2024-10-14、欠測6日(`2023-09-09/23/25`, `2024-06-01/11/12`) | 取得済(配信停止前の退避) | 2026-09-12 | `docs/DATA/probes/20260913_binance_cm_o3c_fetch.log` | O-3c(未使用) |
| Binance COIN-M BTCUSD_PERP metrics(建玉`sum_open_interest`・L/S比、5分粒度) | `backtest_data/binance_cm_o3c_20260913/metrics/BTCUSD_PERP/`(日次zip、379/478日) | 2023-06-25〜2024-10-14、欠測99日(単発2日+`2024-03-04`〜`2024-06-08`の連続97日) | 取得済(配信停止前の退避) | 2026-09-12 | `docs/DATA/probes/20260913_binance_cm_o3c_fetch.log` | O-3c(未使用) |

**注記**: metrics の連続97日欠測(2024-03-04〜06-08)は本単位では未調査の事実として記録するのみで、
原因(配信欠落 or 該当期間データ非存在)についての主張はしない。

## fundingRate(2026-09-13 追記)

O-3c Q2(価格帯予測)の入力の1つ「建玉の積み上げ + 資金調達率 + L/S比」のうち、資金調達率が
`metrics`(日次アーカイブ)には列として存在しないため、**別系統の月次アーカイブ**から取得した。

- 取得日時(UTC): 2026-09-12T17:48:58Z 〜 2026-09-12T17:49:16Z(約18秒)
- URL: `https://data.binance.vision/data/futures/cm/monthly/fundingRate/BTCUSD_PERP/BTCUSD_PERP-fundingRate-YYYY-MM.zip`
  (+同名 `.CHECKSUM`)。**日次版は存在しない**(`.../cm/daily/fundingRate/BTCUSD_PERP/` は Key 0 件、
  リードが事前確認済み)。月次アーカイブは Key 96 件、最古 `BTCUSD_PERP-fundingRate-2022-07.zip`。
- スクリプト: `scripts/fetch_binance_cm_o3c.py --kind fundingRate`(既存スクリプトを拡張。
  `MONTHLY_KINDS = {"fundingRate"}` で月次パス(`cm/monthly/...-YYYY-MM.zip`)とURLの月次生成
  `month_range()` を追加。`fetch_day` は `fetch_period` に一般化し、日次/月次のどちらでも
  sha256 検証・失敗時1回再取得の既存ロジックをそのまま使う。他の kind の挙動・パスは変更していない)
- 期間: **2023-05 〜 2024-11**(19か月。O-3c の窓 2023-06-25〜2024-10-14 の前後1か月の余裕を持たせた)
- 取得ログ: `docs/DATA/probes/20260913_binance_cm_o3c_fetch.log`(1か月1行 ×19行、kind=fundingRate。
  各行: UTC時刻・kind・period(YYYY-MM)・URL・HTTPコード・バイト数・CHECKSUM一致可否)

### 取得できた月・欠測月

**19か月中 19か月 OK / 欠測0 / CHECKSUM失敗0**(再取得は一度も発動しなかった)。
2023-05 〜 2024-11 の全月が揃っている。

### ファイル数・バイト数(実測)

| kind | 対象月数 | OK | 欠測 | CHECKSUM失敗 | zipファイル数 | 総バイト数(実測、zip+.CHECKSUM) |
|---|---|---|---|---|---|---|
| fundingRate | 19 | 19 | 0 | 0 | 19 | 16,952 bytes(約16.6 KiB) |

ファイル総数(zip + .CHECKSUM 合計): **38**(19 × 2)。

### CHECKSUM検証

全19件のダウンロードについて、Binance Vision配布の `.CHECKSUM`(sha256)との一致をスクリプト内で検証
(成功19 / 失敗0)。取得後に全19件を独立に `sha256sum` で再検証しても不一致は0件だった。

### 中身の確認(1か月分を解凍・列名と先頭3行)

`BTCUSD_PERP-fundingRate-2023-06.zip`

列名: `calc_time,funding_interval_hours,last_funding_rate`

```
1685577600011,8,0.00010000
1685606400000,8,0.00010000
1685635200001,8,0.00010000
```

(`calc_time` は ms の UNIX 時刻。上記3行を UTC 変換すると `2023-06-01T00:00:00.011Z` /
`2023-06-01T08:00:00Z` / `2023-06-01T16:00:00.001Z` — 8時間ごとの資金調達時刻(00/08/16時 UTC)と一致。
これは時刻列そのものの変換であり、価格・レートの値には触れていない。)

### git の扱い(実測根拠)

実測 **16,952 bytes(約16.6 KiB)は100MBの閾値を大きく下回るため、本体(zip・.CHECKSUM)も
README・MD5SUMSと同様に追跡対象のまま**とした。`.gitignore` への除外行は追加していない
(確認: 既存の `.gitignore` に `binance_cm_o3c_20260913/aggTrades/**/*.zip` 等の除外行はあるが
`fundingRate/` に対する行は無く、今回も追加していない)。

### `MD5SUMS` 追記

fundingRate 分38行(19ファイル×2)を追記。追記前2,653行 → 追記後2,691行。

## `metrics` の `create_time` が UTC かどうかの確認(2026-09-13、時刻列のみの確認・判定用データの測定ではない)

**方法**: `metrics/BTCUSD_PERP/BTCUSD_PERP-metrics-2023-06-25.zip` と
`liquidationSnapshot/BTCUSD_PERP/BTCUSD_PERP-liquidationSnapshot-2023-06-25.zip`(同じ日)を解凍し、
liquidationSnapshot 側の `time`(ms の UNIX 時刻、UTC が確定)を UTC 変換して日付レンジを確認、
metrics 側の `create_time`(タイムゾーン表記のないナイーブな日時文字列、5分刻み)の日付レンジと突き合わせた。

**観測事実**:
- metrics-2023-06-25.csv: `create_time` は `2023-06-25 00:00:00` 始まり `2023-06-25 23:55:00` 終わり
  (5分刻み288行、全行が単一の日付 `2023-06-25` に収まる。日付の飛び出しなし)
- liquidationSnapshot-2023-06-25.csv: `time`(ms epoch)の最小値 `1687656471926` → UTC変換で
  `2023-06-25T01:27:51.926Z`、最大値 `1687732427835` → UTC変換で `2023-06-25T22:33:47.835Z`。
  いずれも `2023-06-25` の範囲内(この日はliquidationイベントが日付境界の近くに無く、
  境界そのものの厳密な検証にはなっていない)
- 別途、今回取得した `fundingRate-2023-06.zip` の `calc_time`(ms epoch)を UTC 変換すると
  `1685577600011` → `2023-06-01T00:00:00.011Z`、`1685606400000` → `2023-06-01T08:00:00Z`、
  `1685635200001` → `2023-06-01T16:00:00.001Z` となり、Binance の資金調達時刻(00/08/16時UTC)と
  一致した(これは `fundingRate` の epoch 列自体がUTCであることの確認であり、`metrics` の
  `create_time` を直接検証するものではない)

**限界(なぜ3値のうち「UTCと一致」と断定できないか、事実として明記)**: `metrics` の
`create_time` には UNIX epoch のような曖昧さのない時刻表現が無く、ナイーブな日時文字列のみである。
liquidationSnapshot 側と比較して「同じ日付ラベルの範囲に収まっている」ことは確認できたが、これは
必要条件であって十分条件ではない。**もし `create_time` が UTC ではなく固定オフセット
(例: JST=UTC+9)で、かつファイル分割の基準も `create_time` 自身の暦日(そのタイムゾーンでの
0時〜24時)であった場合**、ファイル名は同じ `2023-06-25` になり、かつファイル内は同様に
`00:00:00`〜`23:55:00` のきれいな288行に収まってしまうため、**この検証方法では区別できない**
(liquidationSnapshot 側は真のUTC暦日で分割されている一方、metrics側が別タイムゾーンの暦日で
分割されていても、ラベルの一致という点では見分けがつかない)。`metrics` 内に epoch 等の
独立した時刻アンカーが無く、`liquidationSnapshot`/`fundingRate` との間に「同一の実時刻の
出来事」を指し示す共有点も無いため、これ以上の突き合わせでは価格・サイズに触れずに検証を
進める手段が無かった。

**結論: 判断できない**(UTCと一致でも矛盾でもない=違反は見つからなかったが、上記の理由で
UTCであることの証明にはならない)。一次資料(Binance公式ドキュメントでの `create_time` の
定義)による確認、または本番運用のAPIリクエスト(このアーカイブ経由でない生きたAPI呼び出し)
による突き合わせが必要。**実装が UTC と仮定している箇所は、この不確実性を前提にしたまま
残っている**ことを記録する。
