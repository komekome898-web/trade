カード 5(東京仲値・前モメンタム)の調達票

研究手順書 §14 の表。到達確認は、データの置き場の目録(README・MD5SUMS・`candles_1m_index.json`・`gaps_gt5min.txt` の冒頭の集計)と `ls -l` だけで行った。**データの行は開いていない**(封印の中も外も。測定はまだ)。`md5sum -c` も打っていない(中身のバイトを読むため。2023 年のファイルは封印の行を含む)。
主張の印: 【事実】= この回にファイルを読んで確かめた / 【推定】/ 【未確認】= この回に叩いていない。

## 1. 主に使うデータ(CARD.md の「使うデータと遅れ」)

最小 n: 定めない。W1 の測定器が、検出力(C5 の e)を出し、効果が見えないときに「不明(検出力が足りない)」と「小さい」を分ける(W1 の仕様 C5)。n を先に決めて足切りしない(A-8)。

| 必要データ(市場・粒度・期間・最小 n) | 入手経路の候補(3 つ以上) | 到達確認(日付・方法・結果) | 欠けと対処 |
|---|---|---|---|
| bitFlyer FX_BTC_JPY・1 分足(OHLCV)・2015-11-28T15:00Z〜2023-12-17T15:00Z(日本時間 2015-11-29 0 時〜2023-12-18 0 時。CARD.md の測る期間)・最小 n は上の注 | (1) **bitFlyer の lightchart**(`lightchart.bitflyer.com/api/ohlc`、公開・無認証・文書の無い API)— 手元 `backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/` (2) bitFlyer 公開 REST の約定履歴から 1 分足を組む — 約 31 日分しか遡れない(N-002)ので、この期間には使えない (3) 自前の記録(`paper_logs/tape/`)— 2026 年の分だけ【推定: 置き場の名前から。中身は読んでいない】 (4) 第三者の有料の履歴(Tardis など)— bitFlyer の 2015〜2023 の 1 分足を持つかは【未確認】 | 2026-10-02、`ls -l` と README・`candles_1m_index.json`・MD5SUMS・`gaps_gt5min.txt` の冒頭を読んだ。結果【事実】: 年ごとのファイル `candles_1m_2015.csv.gz`〜`candles_1m_2023.csv.gz` がある(2015 年 201,672 バイト・2016 年 5,816,109 バイト・2023 年 18,962,595 バイト。2017〜2022 年は 13,007,293〜25,498,413 バイト)。目録の 2015 の `first` は 2015-11-28 04:54 UTC、2016 は 2016-01-01 00:03〜12-31 23:59、2023 は 2023-01-01 00:00〜12-31 23:59。README「`ts` — start of the 1-minute bucket, ISO-8601 UTC」。MD5SUMS に 2015・2016・2023 の行がある(2017〜2022 はカード 3 の調達票で確認済みの記述と同じ置き場) | (a) 約定 0 の分は OHLC が null・量 0(README)。空の足としてカードは呼ばれず、損益は次の空でない足の始値で約定(W1 の C2)。日本時間 0 時の足が空なら、その日の錨は次の約定のある足の始値(INTENT_MAP.md C-4)。9 時 55 分に終わる足が空なら、持ち高が仲値の後まで残る(INTENT_MAP.md §5)。(b) 5 分を超える空き(`gaps_gt5min.txt`: 2015 年 1,521 件・38,553 分、2016 年 6,685 件・76,036 分、2017 年 391 件・5,470 分、2018 年 312 件、2019 年 374 件、2020 年 389 件、2021 年 395 件、2022 年 375 件、2023 年 1,316 件・12,589 分)。2015〜2016 年は空きが多い。開始を 2017-08 にそろえるかはリードが決める(CARD.md 迷った点 5)。(c) 2023 年のファイルは 2023-12-18 以後の封印の行を含む。測る期間の終わりで切る(測定器の側)。(d) 2017〜2023 年の別の出所との突き合わせは無い【未確認】 |

## 2. 意図の地図の △・✕ を切り分けるためのデータ(INTENT_MAP.md §4。このカードの持ち高には使わない)

| 必要データ | 入手経路の候補(3 つ以上) | 到達確認 | 欠けと対処 |
|---|---|---|---|
| USDJPY・1 分足・測る期間(§4-2: 為替の仲値前の値動きとの一致。CARD.md 迷った点 3 の別の形の材料) | (1) **Dukascopy の公開の履歴**(`datafeed.dukascopy.com`、無認証)— 手元 `backtest_data/fx_usdjpy_1m_20170801_20221231/`(2017-08-01〜2022-12-31、BID だけ)と `backtest_data/fx_usdjpy_1m_20260822.csv.gz`(README によれば 2023-01-01 から) (2) GMO の FX 公開 API — 過去の 1 分足をどこまで遡れるかは【未確認】 (3) HistData.com などの公開の 1 分足【未確認】 | 2026-10-02、`fx_usdjpy_1m_20170801_20221231/README.md` の冒頭を読み、`ls -l backtest_data/fx_usdjpy_1m_20260822.csv.gz`(20,750,659 バイト)を打った。結果【事実】: 前者の README は「USDJPY 1-minute BID, 2017-08-01..2022-12-31」「Extends `backtest_data/fx_usdjpy_1m_20260822.csv.gz` (2023-01-01 onward) backward」。後者は置き場の直下のファイルだが、`scripts/check_card.py` の `market_of` で `fx:USDJPY` に当たる(出力 `['fx:USDJPY']`。コマンドは §4) | (a) 2015-11〜2017-07 の USDJPY は手元に無い【事実: 上の README の範囲】。取るなら経路 (1) の同じ道具 `scripts/fetch_dukascopy.py` で遡れるかを確かめる【未確認】。(b) 2023 年の分は後者で取れる。2 つのファイルの継ぎ目(2022-12-31 と 2023-01-01)と、後者が封印の台帳に載っているか(`grep` で見たのは前者が P2-08 の台帳にあることだけ)は【未確認】。(c) BID だけ |
| 日本の祝日の暦・2015〜2023 年(§4-3: 仲値の決まらない平日の切り分け) | (1) 内閣府の「国民の祝日」の CSV(`www8.cao.go.jp/chosei/shukujitsu/syukujitsu.csv`)【未確認: この回に叩いていない】 (2) Python の `holidays` などの暦のパッケージ【未確認: 手元に入っているかは見ていない】 (3) 東京の銀行の休業日(年末年始 12-31〜1-03 を含む)の一覧を金融機関の公開ページから【未確認】 | 到達確認は未(この回は叩いていない)。`ls backtest_data` に祝日の暦の名前の置き場は無かった【事実: `ls backtest_data \| grep -i 'holiday\|calendar\|syukujitsu'` が空】 | 足すまでは、祝日・年末年始も持つ(CARD.md 迷った点 2)。足すなら新しい置き場と、測定の場面の変数への宣言が要る |
| 仲値の時刻の一次資料(CARD.md 水準とその出所) | (1) 銀行の外国為替相場のページ(公示の時刻の説明)【未確認】 (2) 全国銀行協会などの解説【未確認】 (3) 一般向けの解説(https://myforex.com/ja/glossary/ttm.html 、https://media.moneyforward.com/articles/7810)| 2026-10-02、WebSearch「仲値 決定 時刻 9時55分 TTM 銀行」で (3) を検索の要約として読んだ【事実】。結果: 「毎営業日の 9 時 55 分ごろ」。一次資料 (1)(2) は開いていない | 一次資料で確かめるかはリードが決める(CARD.md 迷った点 6) |

## 3. 否定的事実の引用

- N-002(bitFlyer 公開 REST の約定履歴は約 31 日分のみ。2026-08 登録、賞味 90 日): 期限内(2026-10-02 時点)。1 分足は lightchart で取れている(上の到達確認)。

## 4. この回に打ったコマンド(到達確認)

```
ls -l backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/
sed -n 1,60p backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/README.md
grep -n '2023\|2015\|2016' backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_index.json
sed -n 1,14p backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/gaps_gt5min.txt
grep -n '2015\|2016\|2023' backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/MD5SUMS | grep candles
sed -n 1,25p backtest_data/fx_usdjpy_1m_20170801_20221231/README.md
ls -l backtest_data/fx_usdjpy_1m_20260822.csv.gz
ls backtest_data | grep -i 'holiday\|calendar\|syukujitsu'
python -c "import sys; sys.path.insert(0,'scripts'); import check_card as c; print(c.market_of('backtest_data/fx_usdjpy_1m_20260822.csv.gz', c.MARKETS))"   # ['fx:USDJPY']
grep -n 'P2-08\|usdjpy' backtest_data/phase2_sealed/*/SEALED.json | grep -i usdjpy   # P2-08 の台帳の 187 行に 2017〜2022 のファイル
```
