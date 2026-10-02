# Binance USD-M 先物 BTCUSDT 1 分足 2020-01-01 〜 2023-12-17(取得日 2026-10-02)

カード `c2_owner_xvenue_wick` の変種 (b) のシグナルの足として調達した(`docs/RESEARCH/cards/c2_owner_xvenue_wick/PROCUREMENT.md` の ③ (b))。
`scripts/check_card.py` の市場の表では `binance_um:BTCUSDT`(型 `backtest_data/binance_um_BTCUSDT_*/*`)に当たる。

## 出所

- 月ごと: `https://data.binance.vision/data/futures/um/monthly/klines/BTCUSDT/1m/BTCUSDT-1m-YYYY-MM.zip`(2020-01〜2023-11 の 47 本)と、それぞれの `.CHECKSUM`
- 日ごと: `https://data.binance.vision/data/futures/um/daily/klines/BTCUSDT/1m/BTCUSDT-1m-2023-12-DD.zip`(2023-12-01〜2023-12-17 の 17 本)と、それぞれの `.CHECKSUM`
- 公開アーカイブの読み取りだけ。API キーは使っていない。取得 2026-10-02(UTC 10 時台)。
- 取れる最初の月: HEAD 要求(2026-10-02T09:58Z)で 2019-09・2019-10・2019-11・2019-12 の月ごとの zip は 404、2020-01 は 200。確かめたのは 2019-09〜12 の月ごとの zip だけで、2019-01〜08 の月ごとの zip と 2019 年の日ごとのファイルは確かめていない。この置き場には 2020-01 より前の行は無い。
- 2023-12 の月ごとの zip は取っていない(期間の終わりを 2023-12-17 にするため、12 月は日ごとのファイルで取った)。

## 中身

| ファイル | 中身 |
|---|---|
| `raw/BTCUSDT-1m-YYYY-MM.zip` + `.zip.CHECKSUM` | 月ごとの原本 47 本(取ったまま) |
| `raw/daily_2023_12/BTCUSDT-1m-2023-12-DD.zip` + `.zip.CHECKSUM` | 日ごとの原本 17 本(取ったまま) |
| `binance_um_BTCUSDT_1m_YYYY.csv.gz` | 年ごとにまとめたもの(2020・2021・2022・2023) |
| `MANIFEST.json` | 年ごとの行数・最初と最後の時刻・md5・バイト数・検めの結果・load の結果・封印の確かめ |
| `MD5SUMS` | この置き場の全ファイル(MD5SUMS 自身を除く)の md5。`md5sum -c MD5SUMS` で照合できる |

### 列(現物の置き場 `backtest_data/binance_BTCUSDT_1m_20170801_20231231/` と同じ名前・同じ単位)

`open_time,open,high,low,close,volume,quote_volume,n_trades,taker_buy_base`

- `open_time`: 分の始まり。ISO-8601、UTC(`2020-01-01 00:00:00+00:00` の形)。原本の列 0(ミリ秒の epoch。64 本すべてミリ秒で、マイクロ秒の行は 0)を変換した。
- `open`〜`close`: USDT。`volume`: BTC(基軸の数量)。`quote_volume`: USDT。`n_trades`: 約定の件数。`taker_buy_base`: BTC。原本の列 1,2,3,4,5,7,8,9。
- 原本の `close_time`・`taker_buy_quote`・`ignore` は落とした(現物の置き場と同じ)。
- `volume` が BTC であること: 最初の行 `volume=246.092`、`quote_volume=1767430.16121` で、割ると 7182 になり、その分の価格(7177〜7190.52)に収まる。
- 現物とそろえられなかった所: 無い。ただし先物の価格は現物の価格ではない(同じ時刻でも値が違う)。

| 年 | 行数 | 最初 | 最後 | バイト数 | md5 |
|---|---|---|---|---|---|
| 2020 | 527,040 | 2020-01-01 00:00 | 2020-12-31 23:59 | 16,564,324 | 15d4795871be01063c3cb399d15288ca |
| 2021 | 525,600 | 2021-01-01 00:00 | 2021-12-31 23:59 | 18,260,639 | ce806cc3fcb5f01a2a25ea35a7d9e89e |
| 2022 | 525,600 | 2022-01-01 00:00 | 2022-12-31 23:59 | 16,829,285 | 1906ddd3390e74c8e184361015d73113 |
| 2023 | 505,440 | 2023-01-01 00:00 | 2023-12-17 23:59 | 15,487,528 | dc9ea079448941c9ea25e3020169a3f5 |
| 計 | 2,083,680 | | | | |

行数は暦の分の数と一致する(2020 は 366 日 × 1440 = 527,040、2021・2022 は 365 × 1440 = 525,600、2023 は 1-01〜12-17 の 351 日 × 1440 = 505,440)。

## 検め(すべて機械。目視していない)

| 検め | 結果 |
|---|---|
| 各 zip の `.CHECKSUM`(SHA-256)の照合 | 64 / 64 一致(取得の時に照合し、ディスクに置いた後にもう一度照合) |
| 行数 | 上の表。原本から読んだ行数 2,083,680 = 書いた行数 |
| 時刻の重複 | 0 |
| 時刻の逆順 | 0 |
| 時刻の抜け(隣の行との差が 60 秒でない所) | 0 か所。抜けた分の合計 0。最長の抜け: 無し(年の境をまたぐ差も数えた) |
| 高値 < 安値 | 0 |
| 高値 < max(始値, 終値) | 0 |
| 安値 > min(始値, 終値) | 0 |
| 価格 ≤ 0 | 0 |
| 出来高 < 0 | 0 |
| `n_trades == 0` の行(参考) | 243(2020: 2、2021: 59、2022: 64、2023: 118)。243 行すべて 始値=高値=安値=終値、出来高 0 |

抜けの数は、まとめる処理とは別に書き出した csv.gz を読み直して数えても 0 だった。現物の置き場には抜けが 35 か所あるが、この先物の原本には抜けが 0 か所で、`n_trades=0` の行が 243 行ある(ここまで事実)。約定の無い分を原本が `n_trades=0` の行で埋めている、というのは推定(Binance の資料では確かめていない)。

## `bot.bt.data` の load で読めること(2026-10-02)

仕様は `scripts/k1_newenv_g_loadprof.py` の `SPEC` と同じ(`synthetic` は `n_trades` が `0` の行)。範囲は各年の 1 月 1 日〜翌年 1 月 1 日、2023 年は 2023-01-01〜2023-12-18(封印の外だけ)。

| 年 | 読んだ行 | 残した行 | 封印の単位 | 異常 |
|---|---|---|---|---|
| 2020 | 527,040 | 527,040 | 無し | synthetic 2 |
| 2021 | 525,600 | 525,600 | 無し | synthetic 59 |
| 2022 | 525,600 | 525,600 | 無し | synthetic 64 |
| 2023 | 505,440 | 505,440 | 無し | synthetic 118 |

gap・off_grid の異常は 0。`checks_not_run` は空。

## 封印

- `binance_um:BTCUSDT` の封印の境は 2026-08-23T00:00:00Z(`scripts/check_card.py` の `boundaries` が台帳 `backtest_data/phase2_sealed/*/SEALED.json` から出した値。台帳の `binance_um` の行は P2-08b の aggTrades 2026-07-23〜09-06 だけ)。
- この置き場の最後の行は 2023-12-17 23:59 UTC で、境より前。この置き場のファイルは台帳に 1 つも載っていない。
- 参考: 現物 `binance:BTCUSDT` の境は 2023-12-18T00:00:00Z。この置き場の最後の行はそれよりも前。

## 作り方

`scripts/build_binance_um_btcusdt_1m.py`(この置き場を作ったものをそのまま置いた)。`scripts/fetch_binance_vision.py` の `fetch_one`・`iter_zip_rows`・`normalize_epoch`・`verify_checksum` を呼ぶ。その中の `consolidate()` は使っていない(重複を黙って 1 行にし、1 本のファイルにまとめるため)。

```
python3 scripts/build_binance_um_btcusdt_1m.py fetch   # 取得(照合済みの zip は取り直さない)
python3 scripts/build_binance_um_btcusdt_1m.py build   # 照合のやり直し・年ごとの csv.gz・検め・MANIFEST.json
```

`build` は `MANIFEST.json` を書き直すので、その後に足した `load_check`・`seal_check` は消える(この 2 つは上の節の結果を手で足した)。MD5SUMS は最後に `find . -type f ! -name MD5SUMS | sed 's|^\./||' | sort | xargs md5sum > MD5SUMS` で作った。

## 2026-10-02 リードの追記(git に入れる範囲)

- git に入れるのは年ごとの csv.gz・README・MANIFEST・MD5SUMS だけ。`raw/`(月・日の zip と .CHECKSUM、約 86MB)は `.gitignore` で外した(既存の置き場の作法と同じ)。
- `MD5SUMS` は git に入るファイルだけを載せる形に分けた。`raw/` の照合は `raw/MD5SUMS`(この容器の中だけにある)。分けた後に両方で `md5sum -c` → 失敗 0。
