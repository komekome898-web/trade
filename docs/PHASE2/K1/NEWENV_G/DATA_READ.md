# K1 段階 G — 読んだデータ

委任文 §2-5「実行と試験はすべてデータの門の下で回し、門が止めた `open` が 0 件、読んだファイルの一覧(パス・最初と最後の ts)を出す。**最後の ts が 2023-12-17T23:59:00Z を越える行を 1 行も読んでいないこと**を、環境の `SealedRangeError` の記録と自前の確認の両方で示す」。

## 1. データの門

- 門: `scripts/k1_newenv_g_datagate.py`(段階 A の `k1_newenv_fix_datagate.py` と同じ仕組み、許可の一覧だけこの委任用)。畳み・実行・試験・封印の確認のスクリプトはすべて最初にこれを import する(`k1_newenv_g_fold.py`・`k1_newenv_g_run.py`・`k1_newenv_g_selftest.py`・`k1_newenv_g_seal_check.py`)。表と違いのスクリプト(`k1_newenv_g_tables.py`・`k1_newenv_g_diff.py`・`k1_newenv_g_old.py`)はデータの置き場を開かない(実行記録・`results/`・`docs/` だけ)。
- 門が止めた `open`: **実行・畳み・試験・封印の確認では 0 件**(記録先 `K1G_DATAGATE_LOG` の `gate_fold.log`・`gate_run.log`・`gate_selftest.log`・`gate_seal.log` は作られていない = 1 行も書かれていない。`cat <scratchpad>/gate_*.log | wc -l` → 1、その 1 行は次の確かめのもの)。
- **門が効くことの確かめ(わざと止めた 1 件)**: 05:10 UTC、`probe.py` で `backtest_data/binance_BTCUSDT_1m_20240101_20260831/binance_BTCUSDT_1m_20240101_20260831.csv.gz` を開こうとし、`PermissionError k1g datagate: … is outside the data the delegation allows` で止まった(`gate_probe.log` の 1 行)。中身は 1 byte も読んでいない(open の前に止まる)。

## 2. 読んだ生のファイル(畳みの段、`scripts/k1_newenv_g_fold.py`、出所 `backtest_data/k1_newenv_g_20261001/FOLD_MANIFEST.json: inputs`)

Binance はデータ層(`bot.bt.data.load`、`range_ns` の終わり = 次の年の頭か境 2023-12-18T00:00Z の早い方)で読んだ。bitFlyer はデータ層が空の欄を読めない(ENV_DEFECTS.md G-2)ので、自前で gzip を読み、空の行と「足の終わり > 境」の行を落とした写しを作り、写しをデータ層で読んだ(写しは読んだあと消した)。
「最初の ts / 最後の ts」は使った行(範囲と方針の後)のもの。

| 読んだファイル | 封印の単位 | 範囲(データ層の range_ns) | 範囲内の行 | 方針の後に使った行 | 最初の ts | 最後の ts | sha256(先頭 12) |
|---|---|---|---|---|---|---|---|
| `backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_2017.csv.gz` | P2-08 | 2017-01-01T00:00:00 〜 2018-01-01T00:00:00 | 196,544 | 172,848 | 2017-08-17T04:00:00 | 2017-12-31T23:59:00 | 590178034c6e |
| `backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_2017.csv.gz`(自前の読み: 空の行 6,524 行と境以降の行 0 行を落として写しへ) | P2-08 | 自前で 足の終わり <= 境 | 525,596(ファイルの全行) | 519,072(写し) | 2017-01-01T00:00:00+00:00 | 2017-12-31T23:59:00+00:00 | 6d84ad5319ae |
| `backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_2018.csv.gz` | P2-08 | 2018-01-01T00:00:00 〜 2019-01-01T00:00:00 | 521,624 | 521,604 | 2018-01-01T00:00:00 | 2018-12-31T23:59:00 | f66cc2228c3b |
| `backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_2018.csv.gz`(自前の読み: 空の行 4,293 行と境以降の行 0 行を落として写しへ) | P2-08 | 自前で 足の終わり <= 境 | 525,600(ファイルの全行) | 521,307(写し) | 2018-01-01T00:00:00+00:00 | 2018-12-31T23:59:00+00:00 | 1385d1ebf85b |
| `backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_2019.csv.gz` | P2-08 | 2019-01-01T00:00:00 〜 2020-01-01T00:00:00 | 523,836 | 523,760 | 2019-01-01T00:00:00 | 2019-12-31T23:59:00 | ffb1fde499ae |
| `backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_2019.csv.gz`(自前の読み: 空の行 5,708 行と境以降の行 0 行を落として写しへ) | P2-08 | 自前で 足の終わり <= 境 | 525,600(ファイルの全行) | 519,892(写し) | 2019-01-01T00:00:00+00:00 | 2019-12-31T23:59:00+00:00 | 07b74645997c |
| `backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_2020.csv.gz` | P2-08 | 2020-01-01T00:00:00 〜 2021-01-01T00:00:00 | 525,788 | 525,738 | 2020-01-01T00:00:00 | 2020-12-31T23:59:00 | 655ab3497125 |
| `backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_2020.csv.gz`(自前の読み: 空の行 6,701 行と境以降の行 0 行を落として写しへ) | P2-08 | 自前で 足の終わり <= 境 | 526,668(ファイルの全行) | 519,967(写し) | 2020-01-01T00:00:00+00:00 | 2020-12-31T23:59:00+00:00 | 8da834bd5acd |
| `backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_2021.csv.gz` | P2-08 | 2021-01-01T00:00:00 〜 2022-01-01T00:00:00 | 524,607 | 524,518 | 2021-01-01T00:00:00 | 2021-12-31T23:59:00 | 56d016ad1900 |
| `backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_2021.csv.gz`(自前の読み: 空の行 6,970 行と境以降の行 0 行を落として写しへ) | P2-08 | 自前で 足の終わり <= 境 | 525,600(ファイルの全行) | 518,630(写し) | 2021-01-01T00:00:00+00:00 | 2021-12-31T23:59:00+00:00 | 79de9fd56e06 |
| `backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_2022.csv.gz` | P2-08 | 2022-01-01T00:00:00 〜 2023-01-01T00:00:00 | 525,600 | 525,600 | 2022-01-01T00:00:00 | 2022-12-31T23:59:00 | cdc318ee4488 |
| `backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_2022.csv.gz`(自前の読み: 空の行 4,716 行と境以降の行 0 行を落として写しへ) | P2-08 | 自前で 足の終わり <= 境 | 525,600(ファイルの全行) | 520,884(写し) | 2022-01-01T00:00:00+00:00 | 2022-12-31T23:59:00+00:00 | 62b691086660 |
| `backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_2023.csv.gz` | P2-08 | 2023-01-01T00:00:00 〜 2023-12-18T00:00:00 | 505,360 | 505,288 | 2023-01-01T00:00:00 | 2023-12-17T23:59:00 | 1a83012af928 |
| `backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_2023.csv.gz`(自前の読み: 空の行 47,601 行と境以降の行 20,160 行を落として写しへ) | P2-08 | 自前で 足の終わり <= 境 | 525,600(ファイルの全行) | 457,839(写し) | 2023-01-01T00:00:00+00:00 | 2023-12-17T23:59:00+00:00 | d0e7bb576a16 |

**注意(正直に書く。2026-10-01 第 2 回で Binance と bitFlyer を分けて事実どおりに書き直した = 批評家の [直す] 2、`docs/AUDITOR/VERDICTS/2026-10-01_k1_stage_g_close.md` 指摘 2)**: 2023 のファイルは境(2023-12-18T00:00Z)以降の行も入っている。どちらのファイルも、ファイルの bytes を全部ほどき、各行を csv の欄(文字)に分けてから境以降の行を捨てた。捨てるまでに何を読んだかは 2 つのファイルで違う。

- **Binance 2023**(`binance_BTCUSDT_1m_2023.csv.gz`、データ層 `read_layer` → `load`、範囲の終わり = 境): 段階 G の時点のデータ層は、行を作る `_build`(全部の欄を数に直し、`BarEvent` を作る)が範囲の判定 `_in_range` より前だった(`git show 5627b4ad^:src/bot/bt/data/loader.py` の 474・475 行)。そのため境以降の 20,160 行も **OHLCV を数に直し、`BarEvent` を作ってから**捨てていた。「時刻だけ読んだ」は当てはまらない。【事実】第 2 回の着手時の loader(`git show HEAD:src/bot/bt/data/loader.py`、HEAD = 627503d8。同じ順)をスクラッチパッドの src の写しに置き、同じ spec・範囲で読んで数えた: 「"rows_read": 525520, "rows_kept": 505360, "no_trade_rows": 0, "BarEvent_made": 525520, "num_calls": 2627600, "max_BarEvent_start": "2023-12-31T23:59:00"」(`FIXES.md` §11)。
- **bitFlyer 2023**(`candles_1m_2023.csv.gz`、段階 G の自前の読み `filter_bitflyer`、`git show 5627b4ad^:scripts/k1_newenv_g_fold.py` の 144〜147 行。時刻を読むのが 144 行、境以降なら飛ばすのが 145〜147 行): 境以降の 20,160 行は、時刻の欄を読んだところで飛ばした(値は数に直していない。写しにも入れていない)。**「時刻だけ読んだ」が当てはまるのはこちらだけ。**
- どちらも、境以降の行から作ったもの(Binance の `BarEvent`)は範囲の外として捨てられ、畳みに渡っていない。【事実】畳みに渡った事象の最後の開始は 2023-12-17T23:59:00(`FOLD_MANIFEST.json` の `self_check.max_input_event_start`)。
- **G-7 を直した後の読み方**(`FIXES.md` §11): データ層は各行の時刻を先に読み、範囲の外の行(と、範囲の中でも封印の境以降の行)は値を読まない。ファイルの bytes を全部ほどき、各行を csv の欄(文字)に分けるのは前と同じ。【事実】G-7 の後のコードで同じ 2 ファイルを段階 G の畳みと同じ spec・範囲で読んで数えた(段階 G の門の下): Binance 「"rows_read": 525520, "rows_kept": 505360, "no_trade_rows": 0, "BarEvent_made": 505360, "num_calls": 2526800, "max_BarEvent_start": "2023-12-17T23:59:00"」(数に直した回数 2,526,800 = 範囲の中の 505,360 行 × 5 欄)、bitFlyer(G-2 の宣言 `no_trade` で読む。写しは作らない)「"rows_read": 525600, "rows_kept": 505440, "no_trade_rows": 47601, "BarEvent_made": 457839, "num_calls": 2336796, "max_BarEvent_start": "2023-12-17T23:59:00"」(2,336,796 = 457,839 行 × 5 欄 + 約定の無い 47,601 行 × volume の 1 欄)。境以降の 20,160 行は、どちらのファイルでも時刻の欄だけを数に直した。
- 「1 行も読んでいない」を「ファイルの bytes に触れていない」の意味では、G-7 の後も満たしていない(§7 の「満たせなかった条件」1。段階 G の返り値 (c) には書かれていなかった = 前回の批評家の [直す] 1)。
変種(DIFF.md D-1 の確かめ)では Binance 2018・2019 と bitFlyer 2018・2019 をもう 1 回同じ方法で読んだ(`VARIANT_2018_2019_offgriddrop.json`)。

## 3. 戦略に渡したファイル(実行の段)

実行の入力は畳んだ足だけ(`backtest_data/k1_newenv_g_20261001/*.csv.gz`)。生のファイルは実行に渡していない(記録の口は範囲を付けて読めないので渡せない = G-3)。各実行の `data_quality.json.gz` に読んだファイルと sha256 がある。

## 4. 境を越える行が無いことの確かめ(`PYTHONPATH=scripts:src python3 scripts/k1_newenv_g_seal_check.py` の出力の逐語)

1・2 = 環境の `SealedRangeError`(データ層と記録の口が生の 2023 のファイルを境の後まで読むことを拒んだ記録)。3 = 自前の確認(畳んだ全ファイルをデータ層で読み直し、最後の足の終わりが境以下)。

```
1 binance_2023 range 無し: SealedRangeError: 'backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_2023.csv.gz' is sealed (unit P2-08) from 1702857600000000000 ns; give range_ns with an en
1 binance_2023 終わり = 境 + 1 分: SealedRangeError: 'backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_2023.csv.gz': range end 1702857660000000000 ns is after the seal cutoff 17028576000000000
2 binance_2023 runner.plan_run: ReproError: data 'backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_2023.csv.gz': SealedRangeError: 'backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_2023.csv.gz' is seale
1 bitflyer_2023 range 無し: SealedRangeError: 'backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_2023.csv.gz' is sealed (unit P2-08) from 1702857600000000000 ns; give range_ns with an end 
1 bitflyer_2023 終わり = 境 + 1 分: SealedRangeError: 'backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_2023.csv.gz': range end 1702857660000000000 ns is after the seal cutoff 1702857600000000000
2 bitflyer_2023 runner.plan_run: ReproError: data 'backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_2023.csv.gz': SealedRangeError: 'backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_2023.csv.gz' is sealed (u
3 backtest_data/k1_newenv_g_20261001/binance_15m_2018_2019_offgriddrop.csv.gz: rows 69481 first 2018-01-01T00:00:00 last 2019-12-31T23:45:00 last_end 2020-01-01T00:00:00 <= cut True sealed_unit None
3 backtest_data/k1_newenv_g_20261001/binance_15m_2018_2021.csv.gz: rows 139333 first 2018-01-01T00:00:00 last 2021-12-31T23:45:00 last_end 2022-01-01T00:00:00 <= cut True sealed_unit None
3 backtest_data/k1_newenv_g_20261001/binance_15m_2022_20231217.csv.gz: rows 68638 first 2022-01-01T00:00:00 last 2023-12-17T23:45:00 last_end 2023-12-18T00:00:00 <= cut True sealed_unit None
3 backtest_data/k1_newenv_g_20261001/binance_15m_full.csv.gz: rows 221000 first 2017-08-17T04:00:00 last 2023-12-17T23:45:00 last_end 2023-12-18T00:00:00 <= cut True sealed_unit None
3 backtest_data/k1_newenv_g_20261001/binance_15m_full_unjoined.csv.gz: rows 221506 first 2017-08-17T04:00:00 last 2023-12-17T23:45:00 last_end 2023-12-18T00:00:00 <= cut True sealed_unit None
3 backtest_data/k1_newenv_g_20261001/binance_1m_2022_20231217.csv.gz: rows 978571 first 2022-01-01T00:00:00 last 2023-12-17T23:59:00 last_end 2023-12-18T00:00:00 <= cut True sealed_unit None
3 backtest_data/k1_newenv_g_20261001/binance_30m_2022_20231217.csv.gz: rows 34327 first 2022-01-01T00:00:00 last 2023-12-17T23:30:00 last_end 2023-12-18T00:00:00 <= cut True sealed_unit None
3 backtest_data/k1_newenv_g_20261001/binance_3m_2022_20231217.csv.gz: rows 338253 first 2022-01-01T00:00:00 last 2023-12-17T23:57:00 last_end 2023-12-18T00:00:00 <= cut True sealed_unit None
3 backtest_data/k1_newenv_g_20261001/binance_5m_2018_2019_offgriddrop.csv.gz: rows 207662 first 2018-01-01T00:00:00 last 2019-12-31T23:55:00 last_end 2020-01-01T00:00:00 <= cut True sealed_unit None
3 backtest_data/k1_newenv_g_20261001/binance_5m_2018_2021.csv.gz: rows 416233 first 2018-01-01T00:00:00 last 2021-12-31T23:55:00 last_end 2022-01-01T00:00:00 <= cut True sealed_unit None
3 backtest_data/k1_newenv_g_20261001/binance_5m_2022_20231217.csv.gz: rows 204458 first 2022-01-01T00:00:00 last 2023-12-17T23:55:00 last_end 2023-12-18T00:00:00 <= cut True sealed_unit None
3 backtest_data/k1_newenv_g_20261001/binance_5m_full.csv.gz: rows 658860 first 2017-08-17T04:00:00 last 2023-12-17T23:55:00 last_end 2023-12-18T00:00:00 <= cut True sealed_unit None
3 backtest_data/k1_newenv_g_20261001/binance_5m_full_unjoined.csv.gz: rows 663749 first 2017-08-17T04:00:00 last 2023-12-17T23:55:00 last_end 2023-12-18T00:00:00 <= cut True sealed_unit None
3 backtest_data/k1_newenv_g_20261001/binance_60m_2022_20231217.csv.gz: rows 17169 first 2022-01-01T00:00:00 last 2023-12-17T23:00:00 last_end 2023-12-18T00:00:00 <= cut True sealed_unit None
3 backtest_data/k1_newenv_g_20261001/bitflyer_15m_2018_2019_offgriddrop.csv.gz: rows 69481 first 2018-01-01T00:00:00 last 2019-12-31T23:45:00 last_end 2020-01-01T00:00:00 <= cut True sealed_unit None
3 backtest_data/k1_newenv_g_20261001/bitflyer_15m_2018_2021.csv.gz: rows 139333 first 2018-01-01T00:00:00 last 2021-12-31T23:45:00 last_end 2022-01-01T00:00:00 <= cut True sealed_unit None
3 backtest_data/k1_newenv_g_20261001/bitflyer_15m_2022_20231217.csv.gz: rows 68638 first 2022-01-01T00:00:00 last 2023-12-17T23:45:00 last_end 2023-12-18T00:00:00 <= cut True sealed_unit None
3 backtest_data/k1_newenv_g_20261001/bitflyer_15m_full.csv.gz: rows 221000 first 2017-08-17T04:00:00 last 2023-12-17T23:45:00 last_end 2023-12-18T00:00:00 <= cut True sealed_unit None
3 backtest_data/k1_newenv_g_20261001/bitflyer_1m_2022_20231217.csv.gz: rows 978571 first 2022-01-01T00:00:00 last 2023-12-17T23:59:00 last_end 2023-12-18T00:00:00 <= cut True sealed_unit None
3 backtest_data/k1_newenv_g_20261001/bitflyer_30m_2022_20231217.csv.gz: rows 34327 first 2022-01-01T00:00:00 last 2023-12-17T23:30:00 last_end 2023-12-18T00:00:00 <= cut True sealed_unit None
3 backtest_data/k1_newenv_g_20261001/bitflyer_3m_2022_20231217.csv.gz: rows 338253 first 2022-01-01T00:00:00 last 2023-12-17T23:57:00 last_end 2023-12-18T00:00:00 <= cut True sealed_unit None
3 backtest_data/k1_newenv_g_20261001/bitflyer_5m_2018_2019_offgriddrop.csv.gz: rows 207662 first 2018-01-01T00:00:00 last 2019-12-31T23:55:00 last_end 2020-01-01T00:00:00 <= cut True sealed_unit None
3 backtest_data/k1_newenv_g_20261001/bitflyer_5m_2018_2021.csv.gz: rows 416233 first 2018-01-01T00:00:00 last 2021-12-31T23:55:00 last_end 2022-01-01T00:00:00 <= cut True sealed_unit None
3 backtest_data/k1_newenv_g_20261001/bitflyer_5m_2022_20231217.csv.gz: rows 204458 first 2022-01-01T00:00:00 last 2023-12-17T23:55:00 last_end 2023-12-18T00:00:00 <= cut True sealed_unit None
3 backtest_data/k1_newenv_g_20261001/bitflyer_5m_full.csv.gz: rows 658860 first 2017-08-17T04:00:00 last 2023-12-17T23:55:00 last_end 2023-12-18T00:00:00 <= cut True sealed_unit None
3 backtest_data/k1_newenv_g_20261001/bitflyer_60m_2022_20231217.csv.gz: rows 17169 first 2022-01-01T00:00:00 last 2023-12-17T23:00:00 last_end 2023-12-18T00:00:00 <= cut True sealed_unit None
3 files over the cut: 0
```

畳みの段の自前の確認(`FOLD_MANIFEST.json: self_check`): `{"signal_minutes_collided_by_floor": 0, "price_minutes_collided_by_floor": 0, "max_bar_end_written": "2023-12-18T00:00:00", "max_bar_end_le_cut": true, "max_input_event_start": "2023-12-17T23:59:00", "max_input_event_end_le_cut": true}`。
使った最後の 1 分足は 2023-12-17T23:59:00(開始)= 2023-12-18T00:00:00(終わり)。境と同じ時刻で終わる足は「区間 [開始, 終わり) が境より前」なので境の前の行(データ層の range_ns の定義と同じ)。

## 5. 読んでいないもの

Binance `binance_BTCUSDT_1m_20240101_20260831/`、bitFlyer 2024〜2026 と 2015・2016 のファイル、Bybit のファイル(ディスクに無い、G-5)、2026-08-28 以降のデータ。門の許可の一覧に無いので、開けば止まる(§1 の確かめ)。

## 6. 追記(2026-10-01 08:1x UTC、続きの作業者)

- 段 A〜D(`driver.sh`、05:5x〜07:54 UTC)の記録先 `K1G_DATAGATE_LOG=<scratchpad>/gate_run.log` は作られていない(`ls <scratchpad>/gate_run.log` → No such file or directory)= 門が止めた `open` は 0 件。
- 続きで回したもの(すべて門の下): `k1_newenv_g_tables.py`・`k1_newenv_g_diff.py`(記録先 `gate_tables.log`)と、sameclose の変種 2 升(`k1_newenv_g_run.py --modes sameclose --ranges 2018_2019_offgriddrop --feet 15 5 --gates s19/b24 --strengths weak`、記録先 `gate_run2.log`)。どちらの記録先も作られていない = 止めた `open` は 0 件。わざと止めた 1 件(`gate_probe.log`、§1)だけが記録。
- 続きで新しく読んだ生のファイルは無い。実行の入力は畳んだ足だけで、各升の `opened` は `runs_index.json` にある(封印の台帳 `backtest_data/phase2_sealed/*/SEALED.json` 8 つと畳んだ足 2 つ)。畳んだ足の最後の足の終わり = 2023-12-18T00:00:00 以下(§4 の 3、`files over the cut: 0`)。
- 第 18 部の Bybit のファイルはディスクに無いので読んでいない(ENV_DEFECTS.md G-5)。

## 7. 満たせなかった条件(2026-10-01 09:0x UTC 追記、批評家の [直す] 1)

批評家の指摘(`docs/AUDITOR/VERDICTS/2026-10-01_k1_stage_g.md` の「批評家」の節、指摘 1)を受けて、段階 G の返り値 (c) に無かったものをここに書く(同じことを `DIFF.md` §6 にも書いた)。委任文 `docs/DATA/delegations/20261001_k1_stage_g_close.md` §1(L-499a「**案1だけど**」)。

1. **委任文 §2-5 の「最後の ts が 2023-12-17T23:59:00Z を越える行を 1 行も読んでいないこと」は満たしていない。**
   - 2023 の 2 ファイルは、境(2023-12-18T00:00Z)以降の行も含めてファイルの bytes を全部ほどき、各行を csv の欄に分けてから境以降の行を捨てた。捨てるまでに読んだものは 2 つで違う(§2 の「注意」、第 2 回で書き直した): Binance 2023 はデータ層が境以降の 20,160 行も OHLCV を数に直し `BarEvent` を作ってから捨てた。bitFlyer 2023 は自前の読みが境以降の 20,160 行を時刻を読んだところで飛ばした。G-7 の後は、どちらも境以降の行は時刻だけを読む。
   - 数の出所 `backtest_data/k1_newenv_g_20261001/FOLD_MANIFEST.json: inputs`(09:0x UTC にデータの門の下で読み直した。記録先 `K1G_DATAGATE_LOG=<scratchpad>/gate_workerA.log` は作られていない = 門が止めた `open` は 0 件):
     - Binance `binance_BTCUSDT_1m_2023.csv.gz`: `rows_read` 525520、`rows_kept_in_range` 505360(差 20,160 行が境以降として読んで捨てた行)。
     - bitFlyer `candles_1m_2023.csv.gz`(写しの元): `copy_of.rows_read` 525600、`dropped_at_or_after_cut` 20160。
   - 境以降の行から作ったものは、畳みに渡っていない(第 2 回で確かめた: `FOLD_MANIFEST.json` の `self_check.max_input_event_start` = 2023-12-17T23:59:00。§2 の「注意」)。実行記録・表は畳んだ足からだけ作っている(§3)。
   - 封印 P2-08 の破りに当たるかの判断: 時刻だけの読み(bitFlyer 2023 の段階 G の読み)は、オーナーの決定 L-499 ②「時刻だけをほどいて捨てる読み方 = 封印を破っていないとみなす」で決まった。Binance 2023 を値まで読んだ件(段階 G の時点のデータ層)と、第 2 回の作業者が直す前の loader で 2023 の 2 ファイルの境以降の行を値まで読み直した件は、その決定の範囲の外で、まだ決まっていない(L-499d で上申)。
2. 満たしている部分(§1・§4 の再掲、事実): 門が止めた `open` は 0 件(わざと止めた 1 件を除く)。環境の `SealedRangeError` は 2023 の生のファイルを境の後まで読むことを拒んだ(§4 の 1・2)。畳んだ全ファイルの最後の足の終わりは境以下(§4 の 3、`files over the cut: 0`)。
