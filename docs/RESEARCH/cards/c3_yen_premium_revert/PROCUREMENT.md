カード 3(円の上乗せの戻り)の調達票

研究手順書 §14 の表。到達確認は、データの置き場の目録(README・MD5SUMS・`*_index.json`・`QUALITY.json`・`gaps_gt5min.txt` の冒頭の集計)と `ls -l` だけで行った。**データの行は開いていない**(封印の中も外も。測定はまだ)。`md5sum -c` も打っていない(中身のバイトを読むため)。
主張の印: 【事実】= この回にファイルを読んで確かめた / 【推定】/ 【未確認】= この回に叩いていない。

## 1. 主に使うデータ(CARD.md の「使うデータと遅れ」)

最小 n: 定めない。W1 の測定器が、検出力(C5 の e、有意 5%・検出力 80% で検出できる最小の平均)を出し、効果が見えないときに「不明(検出力が足りない)」と「小さい」を分ける(W1 の仕様 C5)。n を先に決めて足切りしない(A-8)。

| 必要データ(市場・粒度・期間・最小 n) | 入手経路の候補(3 つ以上) | 到達確認(日付・方法・結果) | 欠けと対処 |
|---|---|---|---|
| bitFlyer FX_BTC_JPY・1 分足(OHLCV)・2017-08-17T15:00Z〜2022-12-31T15:00Z(日本時間 2017-08-18 0 時〜2023-01-01 0 時。CARD.md の測る期間)・最小 n は上の注 | (1) **bitFlyer の lightchart**(`lightchart.bitflyer.com/api/ohlc`、公開・無認証・文書の無い API)— 手元 `backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/` (2) bitFlyer 公開 REST の約定履歴から 1 分足を組む — 約 31 日分しか遡れない(N-002、2026-08 登録・賞味 90 日で期限内)ので、この期間には使えない (3) 自前の記録(`paper_logs/tape/`)— 2026 年の分だけ【推定: 置き場の名前と fx_btc_jpy_1m_continuous の README の記述】 (4) 第三者の有料の履歴(Tardis など)— bitFlyer の 2017〜2022 の 1 分足を持つかは【未確認】 | 2026-10-02、`ls -l` と README・`candles_1m_index.json`・MD5SUMS・`gaps_gt5min.txt` の冒頭を読んだ。結果【事実】: 年ごとのファイル 2017〜2022 があり(大きさ 13,007,293〜25,498,413 バイト)、目録の行数は 2017 年 525,596 行(最初 2017-01-01 00:00)・2018〜2022 年は 525,600〜526,668 行。時刻の列 `ts` は 1 分の始まり(UTC)。MD5SUMS に年ごとのファイルが載っている | (a) 約定 0 の分は OHLC が null・量 0(README「294,741 rows are null-OHLC」)。空の足としてカードは呼ばれず、損益は次の空でない足の始値で約定(W1 の C2)。(b) 5 分を超える空き(`gaps_gt5min.txt`: 2017 年 391 件・5,470 分、2018 年 312 件、2019 年 374 件、2020 年 389 件、2021 年 395 件、2022 年 375 件)。空けた時間は測定器が記録する。(c) 2017〜2018 年に 1 分で 10% を超える動きが約 15 件(README)。除かない(置き場の決まり「flag-only」)。(d) 他の bitFlyer の系列との一致は 2026 年の重なりで 88.5%(README)。2017〜2022 年の別の出所との突き合わせは無い【未確認】 |
| Binance BTCUSDT・1 分足の close・2017-08-17T15:00Z〜2022-12-31T15:00Z(日本時間 2017-08-18 0 時〜2023-01-01 0 時。CARD.md の測る期間)。参照の系列は置き場の `open_time` のまま、遅れ 60 秒 | (1) **Binance Vision の月ごとの zip**(`data.binance.vision`、公開)— 手元 `backtest_data/binance_BTCUSDT_1m_20170801_20231231/`、取得時に公開の SHA-256 で 77/77 照合済み(README) (2) Binance 公開 REST の klines(`/api/v3/klines`)【未確認: この回に叩いていない】 (3) 第三者の公開データセット(CryptoDataDownload など)【未確認】 (4) 第三者の有料の履歴(Tardis など。手元に `binance_BTCUSDT_aggTrades_tardis_days` の置き場がある)【未確認: 期間は読んでいない】 | 2026-10-02、`ls -l` と README・`binance_1m_index.json`・MD5SUMS を読んだ。結果【事実】: 年ごとのファイル 2017〜2022 があり(4,982,605〜19,734,685 バイト)、目録の最初の行 2017-08-17 04:00 UTC、時刻の列 `open_time`(1 分の始まり)。2022 年 525,600 行 | (a) 毎分の行の間隔が 60 秒でない所が全期間で 35 件(README、年ごとの内訳なし)。その分は参照の行が無く、カードは 0 を持つ(同じ分の規則)。(b) 2017-08-17 04:00 UTC より前は無い → 測る期間の開始を、そのあとの最初の日本時間の 0 時(2017-08-17T15:00Z)にした。(c) BTCUSD でなく BTCUSDT(意図の地図 I-1b の △) |
| USDJPY・1 分足の close・2017-08-17T15:00Z〜2022-12-31T15:00Z(日本時間 2017-08-18 0 時〜2023-01-01 0 時。CARD.md の測る期間)。参照の系列は置き場の `timestamp` のまま、遅れ 60 秒、as-of で読む | (1) **Dukascopy の公開の履歴**(`datafeed.dukascopy.com`、無認証)— 手元 `backtest_data/fx_usdjpy_1m_20170801_20221231/`(BID だけ) (2) GMO の FX 公開 API — 第 3 版 §5-1B で「現在値 200」、過去の 1 分足をどこまで遡れるかは【未確認】。案 D1-D-21 は「本番は GMO の FX 公開 API」と書く (3) HistData.com などの公開の 1 分足【未確認】 (4) Dukascopy の ASK 側(同じ出所の `ASK_candles_min_1.bi5`)— 取得の道具 `scripts/fetch_dukascopy.py` が ASK も扱う【事実: 道具の冒頭の説明】、この期間の ASK は取っていない(README「BID only」) | 2026-10-02、`ls -l` と README・`QUALITY.json`・MD5SUMS を読んだ。結果【事実】: `usdjpy_1m.csv.gz` 29,075,142 バイト、2,422,080 行、2017-08-01 00:00〜2022-12-30 23:59 UTC、重複 0、価格 0 以下 0。時刻の列 `timestamp` | (a) BID だけ(仲値でない)。対処: 位置は幅がほぼ一定ならずれない【推定】。ASK を足すなら経路 (4)。(b) 土日の休み 278 回と、土日でない 1〜2 日の空き 10 回(QUALITY.json)。その間、カードは t までに届いた最後の行を使う(as-of。リードの答え 2026-10-02)。行の古さの分布と、古さが 0 でない足の割合は測定の回に診断として出す(INTENT_MAP.md §4-6)。(c) `timestamp` が 1 分の始まりかは README・schema に明記が無い。取得の道具の説明(その日の最初の足が 0 秒)から始まりと読める【推定】。カードはこの推定の上で、行の時刻をずらさず遅れ 60 秒を宣言する(リードの答え 2026-10-02)。推定が外れて `timestamp` が 1 分の終わりなら、遅れ 60 秒は 1 分余分に待つ側(未来を読む側ではない)にずれる【推定】。測定を組む前に、Binance の 1 分足と USDJPY の時刻を合わせた BTCJPY の合成値と bitFlyer の値の相関が、ずらし 0 分と ±1 分のどこで最大かを見れば確かめられる(この回はデータを開かないので未実施) |

## 2. 意図の地図の △ を切り分けるためのデータ(INTENT_MAP.md §4)

リードの答え(2026-10-02): bitFlyer 現物は測定の回に診断(§4-1 の (4))で使う。Coinbase と USDT/USD は、今回は W4 の仕様どおり代理(Binance BTCUSDT)で測り、取得の候補を落とさずに残す(到達確認は未)。

| 必要データ | 入手経路の候補(3 つ以上) | 到達確認 | 欠けと対処 |
|---|---|---|---|
| bitFlyer BTC_JPY(現物)・1 分足・同じ期間(§4-1 の (4): FX と現物の乖離の切り分け) | (1) **lightchart の BTC_JPY** — 手元 `backtest_data/bitflyer_lightchart_BTC_JPY_1m_20260906/` (2) bitFlyer 公開 REST の約定履歴 — 約 31 日分(N-002)で使えない (3) オーナーの PC の `basis_log.csv`(第 3 版 §5-1B)— 期間は【未確認】、開かない (4) 第三者の有料の履歴【未確認】 | 2026-10-02、README と `candles_1m_index.json` を読んだ。結果【事実】: 2015-08-02 02:07〜2026-09-06 12:00 UTC、2017〜2022 年の年ごとのファイルがある。時刻の列 `ts`。市場の表(`scripts/check_card.py` の `MARKETS`)に `bitflyer:BTC_JPY` として載っている | 使うなら CARD.md の使うデータに足し、check_card を通し直す |
| Coinbase BTC-USD・1 分足・同じ期間(§4-1 の (2): 原文の使うデータ) | (1) Coinbase Exchange の公開 API の candles — 第 3 版 §5-1B で「A(2024-04-01 を確認)」、2017〜2022 年は【未確認】 (2) 第三者の公開データセット【未確認】 (3) 第三者の有料の履歴【未確認】 (4) 手元の `daily_btcusd_coinbase_20260828.csv.gz` は名前から日足【推定】で、1 分足ではない | 到達確認は未(この回は叩いていない) | 今回は代理(Binance BTCUSDT)で測る(リードの答え 2026-10-02)。取るときは新しい置き場と、市場の表 `MARKETS` への追加が要る |
| USDT/USD・1 分足・同じ期間(§4-1 の (1): BTCUSDT と BTCUSD の差) | (1) Kraken の USDT/USD の公開 OHLC【未確認】 (2) Coinbase の USDT-USD【未確認】 (3) Binance の BTCUSDT と Coinbase の BTC-USD の比(上の行が取れれば作れる) | 到達確認は未(この回は叩いていない) | 同上(今回は代理で測る。候補は残す) |

## 3. 否定的事実の引用

- N-002(bitFlyer 公開 REST の約定履歴は約 31 日分のみ。2026-08 登録、賞味 90 日): 期限内(2026-10-02 時点)。同じ行の注「lightchart.bitflyer.com は 2015-11 まで分足を返す」のとおり、1 分足は lightchart で取れている。
- N-001(bitflyer.com の企業サイトは 403。2026-09-05 登録、賞味 30 日): 期限内。この票の経路は企業サイトを使わない。

## 4. この回に打ったコマンド(到達確認)

```
ls -l backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_20{17..22}.csv.gz \
      backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_20{17..22}.csv.gz \
      backtest_data/fx_usdjpy_1m_20170801_20221231/usdjpy_1m.csv.gz
cat backtest_data/{fx_usdjpy_1m_20170801_20221231,binance_BTCUSDT_1m_20170801_20231231,bitflyer_lightchart_FX_BTC_JPY_1m_20260906,bitflyer_lightchart_BTC_JPY_1m_20260906}/README.md
cat backtest_data/{fx_usdjpy_1m_20170801_20221231,binance_BTCUSDT_1m_20170801_20231231}/MD5SUMS
grep -n "candles_1m_20\(17\|18\|19\|20\|21\|22\)\.csv\.gz" backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/MD5SUMS   # 2017〜2022 の 6 行が載っている
python3 -c "import json; print(json.load(open('.../candles_1m_index.json')))"   # bitFlyer FX・現物、Binance の目録
head -c 3000 backtest_data/fx_usdjpy_1m_20170801_20221231/QUALITY.json
head -12 backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/gaps_gt5min.txt
```
