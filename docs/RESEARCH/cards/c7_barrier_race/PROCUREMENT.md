カード 7(バリアレース逆張り)の調達票

研究手順書 §14 の表。到達確認は、データの置き場の目録(README・MD5SUMS・`candles_1m_index.json`・`gaps_gt5min.txt` の冒頭の集計)と `ls -l` だけで行った。**データの行は開いていない**(封印の中も外も。測定はまだ)。`md5sum -c` も打っていない(中身のバイトを読むため。2023 年のファイルは封印の行を含む)。
主張の印: 【事実】= この回にファイルを読んで確かめた / 【推定】/ 【未確認】= この回に叩いていない。

## 1. 主に使うデータ(CARD.md の「使うデータと遅れ」)

最小 n: 定めない。W1 の測定器が、検出力(C5 の e)を出し、効果が見えないときに「不明(検出力が足りない)」と「小さい」を分ける(W1 の仕様 C5)。n を先に決めて足切りしない(A-8)。

| 必要データ(市場・粒度・期間・最小 n) | 入手経路の候補(3 つ以上) | 到達確認(日付・方法・結果) | 欠けと対処 |
|---|---|---|---|
| bitFlyer FX_BTC_JPY・1 分足(OHLCV。カードが読むのは終値だけ、損益は始値)・2015-11-28T15:00Z〜2023-12-17T15:00Z(日本時間 2015-11-29 0 時〜2023-12-18 0 時。CARD.md の測る期間)・最小 n は上の注 | (1) **bitFlyer の lightchart**(`lightchart.bitflyer.com/api/ohlc`、公開・無認証・文書の無い API)— 手元 `backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/` (2) bitFlyer 公開 REST の約定履歴から 1 分足を組む — 約 31 日分しか遡れない(N-002、2026-08 登録・賞味 90 日で 2026-10-02 時点は期限内)ので、この期間には使えない (3) 自前の記録(`paper_logs/tape/`)— 2026 年の分だけ【推定: 置き場の名前から。中身は読んでいない】 (4) 第三者の有料の履歴(Tardis など)— bitFlyer の 2015〜2023 の 1 分足を持つかは【未確認】 | 2026-10-02、`ls -l` と README・`candles_1m_index.json`・MD5SUMS・`gaps_gt5min.txt` の冒頭を読んだ。結果【事実】: 年ごとのファイル `candles_1m_2015.csv.gz`〜`candles_1m_2023.csv.gz` がある(2015 年 201,672 バイト・2016 年 5,816,109 バイト・2017 年 13,007,293 バイト・2018 年 25,498,413 バイト・2019 年 25,380,765 バイト・2020 年 25,341,365 バイト・2021 年 23,254,963 バイト・2022 年 23,382,295 バイト・2023 年 18,962,595 バイト)。目録の 2015 の `first` は 2015-11-28 04:54 UTC、2016 は 2016-01-01 00:03〜12-31 23:59、2017〜2023 は各年 01-01 00:00〜12-31 23:59。README「`ts` — start of the 1-minute bucket, ISO-8601 UTC」「**null** when the minute had zero executions」「`volume` … 0 on a null-OHLC minute」。MD5SUMS に 2015〜2023 年の 9 ファイルの行がある | (a) 約定 0 の分は OHLC が null・量 0(README)。空の足ではカードは呼ばれず、損益は次の空でない足の始値で約定(W1 の C2)。空きの間の値動きは、空きの後の最初の足の r にまとめて入る(INTENT_MAP.md §5)。(b) 5 分を超える空き(`gaps_gt5min.txt` の冒頭の集計: 2015 年 1,521 件・38,553 分、2016 年 6,685 件・76,036 分、2017 年 391 件・5,470 分、2018 年 312 件・4,429 分、2019 年 374 件・5,988 分、2020 年 389 件・7,423 分、2021 年 395 件・5,949 分、2022 年 375 件・5,039 分、2023 年 1,316 件・12,589 分)。幅の窓は時刻で切る(INTENT_MAP.md C-2)ので、空きの多い年は窓の中の r の数が少ない。開始を 2017-08 にそろえるかはリードが決める(CARD.md 迷った点 6)。(c) 2023 年のファイルは 2023-12-18 以後の封印の行を含む。測る期間の終わりで切る(測定器の側)。(d) 2015〜2023 年の別の出所との突き合わせは無い【未確認】 |

## 2. 意図の地図の △ を切り分けるため・「なぜ」を確かめるためのデータ(このカードの持ち高には使わない)

| 必要データ | 入手経路の候補(3 つ以上) | 到達確認 | 欠けと対処 |
|---|---|---|---|
| 同じ bitFlyer の 1 分足の高値・安値(迷った点 4: 当たりを終値でなく高値・安値で判定する別の形) | (1) 上の §1 と同じファイルの `high`・`low` の列 (2) bitFlyer の約定の記録から組み直す — 公開 REST は約 31 日分のみ(N-002) (3) 第三者の有料の履歴【未確認】 | 2026-10-02、上の README の列の説明を読んだ【事実: `open`, `high`, `low`, `close` の列がある】 | 新しい取得は要らない。使うかはリードが決める |
| 強制決済(清算)の記録(CARD.md「なぜ」の仮説: 継続は清算の連鎖、反転は燃料の尽き) | (1) 手元 `backtest_data/liquidations_repaired_20260912/`・`liquidations_repaired_20260917/` (2) 手元 `backtest_data/coinalyze_liquidations_20260921/` (3) 手元 `backtest_data/gate_liquidations_20260908/` | 2026-10-02、`ls backtest_data \| grep -i 'liq\|force'` で上の 4 つの置き場の名前を見ただけ【事実: 名前】。中身・期間・取引所・封印の扱いは読んでいない【未確認】。`docs/RESEARCH/ideas/round1/DERIVATION_D.md` 28 行は「Binance の COIN 建てを手元に 2023-06-25〜2024-10-14」と書く【未確認: この回に置き場の README で確かめていない】 | 測る期間(〜2023-12-17)と重なるのは、上の記述どおりなら 2023-06-25〜2023-12-17 の約半年だけ【推定】。bitFlyer の清算の記録は手元に無いと読んだが、置き場の一覧を名前で見ただけ【未確認】。「なぜ」の切り分けに使うかはリードが決める |

## 3. 否定的事実の引用

- N-002(bitFlyer 公開 REST の約定履歴は約 31 日分のみ。2026-08 登録、賞味 90 日): 2026-10-02 時点で期限内。台帳の注記「lightchart.bitflyer.com は 2015-11 まで分足を返す」【事実: `docs/NEGATIVE_FACTS.md` 6 行】。1 分足は lightchart で取れている(上の到達確認)。

## 4. この回に打ったコマンド(到達確認)

```
ls -l backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/
sed -n 1,60p backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/README.md
grep -n '"20' backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_index.json
sed -n 1,14p backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/gaps_gt5min.txt
grep -n 'candles' backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/MD5SUMS
grep -n "N-002" docs/NEGATIVE_FACTS.md
ls backtest_data | grep -i "liq\|force"
```
