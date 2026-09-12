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

## aggTrades(未取得・容量見積のみ)

取得は行っていない(委任元の指示により、この回は容量見積のみで終える)。

- サンプル13日(期間全体に分散: 2023-06-25, 08-01, 10-01, 12-01 / 2024-02-01, 03-15, 04-15, 06-01, 06-15,
  08-01, 09-01, 10-01, 10-14)の zip サイズ実測: 最小 1,086,108 bytes、最大 9,483,027 bytes、
  13日平均 3,089,463 bytes/日
- 478日換算の見積り: 平均 × 478 ≈ **1.48 GB**(サンプル13日のみの外挿。実測ではない)
- 見積りは 10 GB を大きく下回るため容量上の障害はない(このコンテナの空き容量は約13GB)が、
  **取得の実施はこの回のスコープ外**(委任元指示)。次回、この見積りとともに実施可否を判断すること。

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
(ディレクトリを cd してから実行)。1,702行。

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
