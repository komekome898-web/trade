# カード c2_owner_xvenue_wick: 調達票(研究手順書 §14)

作成: 2026-10-02。**封印のデータの中身は開いていない。封印の外の期間(2023-12-17 まで)の行も、この回は開いていない**(測定はまだ)。
到達確認は、置き場の目録(README・MANIFEST・`*_index.json`・MD5SUMS)を読むことと、MD5SUMS との照合(`md5sum -c`)で行った。

**事実(差し戻し 1 回目で明記)**: `md5sum -c` は、2023-12-18 以降の封印の行を含むファイル(`binance_BTCUSDT_1m_2023.csv.gz` と `candles_1m_2023.csv.gz`)のバイトを読んだ。行は読み解いていない(出力は「OK」の文字だけ)。**今後は、封印の行を含むファイルには `md5sum -c` を打たない**(目録の記載を読むだけにする)。置き場に無い経路は、公開アーカイブへの HEAD 要求(中身は受け取らない)で確かめた。

## 1. 調達票

| 必要データ(市場・粒度・期間・最小 n) | 入手経路の候補 | 到達確認(日付・方法・結果) | 欠けと対処 |
|---|---|---|---|
| **① 執行の足**: bitFlyer FX_BTC_JPY、1 分足 OHLCV、2017-08-17〜2023-12-17。最小 n: 置かない(原文に根拠が無い。検出力は測定器 C5 e の MDE で出し、足りなければ「不明」と書く) | (a) **置き場** `backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/`(bitFlyer のチャートの裏の API、2015-11-28〜2026-09-06)/ (b) `backtest_data/fx_btc_jpy_1m_continuous_20260906/`(2026-07-23〜09-05 のみ。期間に掛からない)/ (c) bitFlyer 公式 REST の約定履歴(約 31 日分のみ、N-002)/ (d) 自前の記録 `paper_logs/tape/`(2026-08〜のみ) | 2026-10-02。README と `candles_1m_index.json` を読んだ: 2017〜2023 の各年ファイルの行数・最初と最後の時刻・バイト数が載っている【事実】。`md5sum -c`(MD5SUMS の該当行): `candles_1m_2017.csv.gz`〜`candles_1m_2023.csv.gz` と `candles_1m_index.json` の 8 件すべて OK【事実】。期間を覆うのは (a) だけ | 約定 0 の分は OHLC が null(README: 全体で 294,741 行)→ 空の足として扱う(W1 C2)。毎日 19:00 UTC 前後の保守の時間と 5 分を超える空き(README の年ごとの表、2023 年は 1,316 件と多い。原因は未調査と README に書かれている)→ カードは空きの間に閉じた 15 分足を、次に呼ばれたときに古い順に全部判定する(INTENT_MAP P-3)。2023 年のファイルは 2023-12-18 以降の封印の行を含む → 読み込みの範囲を測る期間の終わり 2023-12-17T15:00:00Z(日本時間 12-18 0 時)で切る(データ層の封印の検査は 2023-12-18T00:00:00Z で止める) |
| **② シグナルの足(この版)**: Binance BTCUSDT **現物**、1 分足 OHLC、2017-08-17〜2023-12-17。最小 n: 同上 | (a) **置き場** `backtest_data/binance_BTCUSDT_1m_20170801_20231231/`(Binance Vision の月次アーカイブ、SHA-256 照合済みと README)/ (b) Binance Vision から再取得(`scripts/fetch_binance_vision.py`、README に手順)/ (c) Binance の公開 REST の klines(この回は未確認)/ (d) CryptoCompare(無料キー無しで 401、N-004) | 2026-10-02。README と `binance_1m_index.json` を読んだ: 2017 年の最初の行 2017-08-17 04:00 UTC、時刻の列は `open_time`(分の始まり)【事実】。`md5sum -c`: `binance_BTCUSDT_1m_2017.csv.gz`〜`2023.csv.gz` と `binance_1m_index.json` の 8 件すべて OK【事実】 | README: 1 分刻みでない行の間が 35 か所(個別には未調査)→ 欠けた分は埋めず、ある行だけで 15 分足を作る(INTENT_MAP P-4)。時刻の列が分の始まりなので遅れ 60 秒を宣言(W4 の仕様 §3 のリードの訂正と同じ)。2023 年のファイルは ① と同じく範囲を切る |
| **③ シグナルの足(変種 (b)・(c)。I-11a が ○ になる版。調達・表の追加の後に測る。測る順は ② の (a) が先)**: 海外の**高レバ**取引所の BTC 無期限の 1 分足(またはそれに畳める細かい足)、2017-08〜2023-12-17 のうち取れる範囲 | (a) **置き場** `backtest_data/bitmex_trade_1s_XBTUSD/`(BitMEX XBTUSD、約定から作った 1 秒足、2017-01-01〜2021-12-31)/ (b) Binance Vision の USD-M BTCUSDT 1 分足(`data.binance.vision/data/futures/um/monthly/klines/BTCUSDT/1m/`)/ (c) Bybit BTCUSDT 無期限(`public.bybit.com/kline_for_metatrader4/`、置き場 `backtest_data/bybit_BTCUSDT_1m_20260910/` は 2022-01〜)/ (d) Binance COIN-M BTCUSD_PERP の約定(置き場 `backtest_data/binance_cm_o3c_20260913/`、2023-06-25〜2024-10-14) | 2026-10-02。(a) `MANIFEST.json` を読んだ: 範囲 2017-01-01〜2021-12-31、`days_absent_from_archive: 0`【事実】。年ごとのファイル数 365 / 365 / 365 / 366 / 365【事実: `ls … \| wc -l`】。(b) HEAD 要求: 2020-01 と 2023-11 の月次 zip は 200、2019-08 / 09 / 12 は 404【事実】→ 2020-01 から取れる。(c) 置き場は `MANIFEST.md` だけで、データのファイルはこの環境に無い【事実: `ls`】。公開アーカイブの 2020・2021・2022 年のフォルダは HEAD で 200【事実】。(d) README を読んだ: 期間 2023-06-25〜2024-10-14【事実】 | **変種 (c) = (a) の BitMEX**: `scripts/check_card.py` の市場の表 `MARKETS` に BitMEX の行が無く、CARD.md に書くと拒まれる → 市場の表への行の追加と封印の確かめはリードが行い、その後に測る。1 秒足から 1 分足を作る(行の時刻は 1 分の始まり、遅れ 60 秒にそろえる)。BitMEX は 2026-09-23 に閉鎖と MANIFEST に書かれている(2026-09-09 時点の取引所の告知)が、公開アーカイブは 2026-10-02 の HEAD で 200。**変種 (b) = (b) の Binance USD-M**: 2020-01〜で、2017-08〜2019-12 は欠ける → 期間を分けて並べる。調達はリードが別の回で手配する(この回では取得しない)。市場の表には `binance_um:BTCUSDT` が既にある。(c) は 2020〜2021 の取得と UTC+3 の時刻の補正(置き場の MANIFEST に記載)が要る。(d) は期間の終わりの半年だけ |
| **④ 清算の記録(I-11b・I-15 の切り分け。射程外、別のカード)**: 高レバ取引所の強制決済の量と向き、期間は ③ と同じ | (a) Binance Vision COIN-M の `liquidationSnapshot`(置き場 `backtest_data/binance_cm_o3c_20260913/`、2023-06-25〜2024-10-14)/ (b) Coinalyze の 1 分の清算の集計(置き場 `backtest_data/coinalyze_liquidations_20260921/`。生の取得は 2026-09-14 以降)/ (c) Gate.io の清算(置き場 `backtest_data/gate_liquidations_20260908/`)/ (d) BitMEX の約定の中の清算(公開アーカイブ。印の有無は未確認) | 2026-10-02。(a) README を読んだ: 478 日中 472 日 OK、欠測 6 日【事実】。(b) `markets.json` の先頭と `raw/` の名前を読んだ: 取得の始まりが 2026-09-14【事実】→ 期間に掛からない。(c)(d) は目録を読んでいない(未確認) | USD-M の `liquidationSnapshot` は Binance Vision に無い、COIN-M は 2024-10-13 まで(**N-012**、2026-09-19 確認、賞味期限 90 日 → 2026-12-18 まで有効)。2017〜2023 を通して清算を直接見る経路は、この回の範囲では見つかっていない(未確認であって「無い」ではない) |

## 2. 否定的事実の引用

| ID | 中身(台帳から) | 確認日 | 賞味期限 | この票での使い方 |
|---|---|---|---|---|
| N-002 | bitFlyer 公開 REST の約定履歴は約 31 日分のみ(lightchart は 2015-11 まで分足を返す) | 2026-09 | 90 日 | ① の候補 (c) が期間を覆わない理由 |
| N-004 | CryptoCompare は無料キー無しで 401、現物のみ | 2026-09-06 | 180 日 | ② の候補 (d) |
| N-012 | Binance Vision の `liquidationSnapshot` は COIN-M で 2024-10-13 まで、USD-M は無い | 2026-09-19 | 90 日 | ④ の候補 (a) の範囲 |

## 3. 実行したコマンド(出力つき)

```
$ cd backtest_data/binance_BTCUSDT_1m_20170801_20231231 && grep -E "binance_BTCUSDT_1m_20(1[7-9]|2[0-3])\.csv\.gz|index" MD5SUMS | md5sum -c -
binance_BTCUSDT_1m_2017.csv.gz: OK
binance_BTCUSDT_1m_2018.csv.gz: OK
binance_BTCUSDT_1m_2019.csv.gz: OK
binance_BTCUSDT_1m_2020.csv.gz: OK
binance_BTCUSDT_1m_2021.csv.gz: OK
binance_BTCUSDT_1m_2022.csv.gz: OK
binance_BTCUSDT_1m_2023.csv.gz: OK
binance_1m_index.json: OK
$ cd backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906 && grep -E "candles_1m_20(1[7-9]|2[0-3])\.csv\.gz|candles_1m_index" MD5SUMS | md5sum -c -
candles_1m_2017.csv.gz: OK
candles_1m_2018.csv.gz: OK
candles_1m_2019.csv.gz: OK
candles_1m_2020.csv.gz: OK
candles_1m_2021.csv.gz: OK
candles_1m_2022.csv.gz: OK
candles_1m_2023.csv.gz: OK
candles_1m_index.json: OK
$ for y in 2017 2018 2019 2020 2021; do echo $y $(ls backtest_data/bitmex_trade_1s_XBTUSD/$y | wc -l); done
2017 365
2018 365
2019 365
2020 366
2021 365
$ curl -sS -o /dev/null -I -w "%{http_code} len=%header{content-length}\n" <URL>   (2026-10-02T09:13Z)
data.binance.vision/data/futures/um/monthly/klines/BTCUSDT/1m/BTCUSDT-1m-2020-01.zip  200 len=1829116
data.binance.vision/data/futures/um/monthly/klines/BTCUSDT/1m/BTCUSDT-1m-2023-11.zip  200 len=1783820
data.binance.vision/data/futures/um/monthly/klines/BTCUSDT/1m/BTCUSDT-1m-2019-08.zip  404
data.binance.vision/data/futures/um/monthly/klines/BTCUSDT/1m/BTCUSDT-1m-2019-09.zip  404
data.binance.vision/data/futures/um/monthly/klines/BTCUSDT/1m/BTCUSDT-1m-2019-12.zip  404
s3-eu-west-1.amazonaws.com/public.bitmex.com/data/trade/20190101.csv.gz               200 len=20284377
public.bybit.com/kline_for_metatrader4/BTCUSDT/2020/ 2021/ 2022/                      200
$ python scripts/check_card.py の boundaries(台帳だけを読む): bitflyer:FX_BTC_JPY と binance:BTCUSDT の封印の境 = 2023-12-18 00:00:00 UTC
```

## 4. リード盲点監査

W4 の仕様 §2 の 6(安い監査者 1 名、≤ 15 ツール呼び出し)。**この回は行っていない**(作業者の仕事の範囲に入っていない)。リードが掛ける。
