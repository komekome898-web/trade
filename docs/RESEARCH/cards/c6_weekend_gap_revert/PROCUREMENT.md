カード 6(週末ギャップの1時間平均回帰)の調達票

研究手順書 §14 の表。到達確認は、データの置き場の目録(README・MD5SUMS・`candles_1m_index.json`・`gaps_gt5min.txt` の冒頭の集計・`QUALITY.json`・取得の目録 `_work/USDJPY_1m.csv.bid.manifest.json`)と `ls` だけで行った。**データの行は開いていない**(封印の中も外も。測定はまだ)。`md5sum -c` も打っていない(中身のバイトを読むため)。
主張の印: 【事実】= この回にファイルを読んで確かめた / 【推定】/ 【未確認】= この回に叩いていない。

## 1. 主に使うデータ(CARD.md の「使うデータと遅れ」)

最小 n: 定めない。W1 の測定器が、検出力(C5 の e)を出し、効果が見えないときに「不明(検出力が足りない)」と「小さい」を分ける(W1 の仕様 C5)。n を先に決めて足切りしない(A-8)。週明けは 1 年に約 52 回なので、測る期間(約 5 年 5 か月)の週明けは約 280 回【推定: 置き場の README の週の閉まり 278 回と合う】。

| 必要データ(市場・粒度・期間・最小 n) | 入手経路の候補(3 つ以上) | 到達確認(日付・方法・結果) | 欠けと対処 |
|---|---|---|---|
| bitFlyer FX_BTC_JPY・1 分足(OHLCV)・2017-08-01T15:00Z〜2022-12-31T15:00Z(CARD.md の測る期間)・最小 n は上の注 | (1) **bitFlyer の lightchart**(公開・無認証・文書の無い API)— 手元 `backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/` (2) bitFlyer 公開 REST の約定履歴から 1 分足を組む — 約 31 日分しか遡れない(N-002)ので、この期間には使えない (3) 自前の記録(`paper_logs/tape/`)— 2026 年の分だけ【推定: 置き場の名前から。中身は読んでいない】 (4) 第三者の履歴の業者 — bitFlyer の 2017〜2022 の 1 分足を持つかは【未確認】 | 2026-10-02、`ls`・README・`candles_1m_index.json`・MD5SUMS・`gaps_gt5min.txt` の冒頭を読んだ。結果【事実】: 年ごとのファイル `candles_1m_2017.csv.gz`〜`candles_1m_2022.csv.gz` がある。目録の 2017 は「first 2017-01-01 00:00:00+00:00」「last 2017-12-31 23:59:00+00:00」。README「`ts` — start of the 1-minute bucket, ISO-8601 UTC」。MD5SUMS に `candles_1m_20` の行が 12 本。5 分を超える空きの年の合計(2017 年 5,470 分〜2022 年 5,039 分)は、週末に毎週閉まる場合の 1 年 149,760 分以上よりずっと小さい → 週末も取引されている | (a) 約定 0 の分は OHLC が null・量 0(README)。空の足としてカードは呼ばれない(W1 の C2)。週明けの分が空なら持ち始めが遅れる(INTENT_MAP.md C-8)。(b) 毎日 19:00〜19:10 UTC の整備の時間(README の `maintenance_window`)は週明け(日曜 21〜22 時 UTC【推定】)と重ならない【推定】。(c) 別の出所との突き合わせは無い【未確認】 |
| USDJPY・1 分足(BID の close)・2017-08-01〜2022-12-31(週の閉まりと週明けの時計、変種 "usdjpy" のギャップ) | (1) **Dukascopy の公開の履歴**(`datafeed.dukascopy.com`、無認証)— 手元 `backtest_data/fx_usdjpy_1m_20170801_20221231/usdjpy_1m.csv.gz` (2) GMO の FX 公開 API — 過去の 1 分足をどこまで遡れるかは【未確認】 (3) HistData.com などの公開の 1 分足【未確認】 (4) 2023-01-01 からの同じ出所の置き場 `backtest_data/fx_usdjpy_1m_20260822.csv.gz`(期間の延長用。CARD.md 迷った点 4) | 2026-10-02、README・MD5SUMS・`QUALITY.json`・取得の目録を読み、`ls -l` を打った。結果【事実】: 「2,422,080 rows, 2017-08-01 00:00:00+00:00 .. 2022-12-30 23:59:00+00:00」。MD5SUMS に `793d6c83f0f6282d5e1a45fdeb58a13b  usdjpy_1m.csv.gz`(封印の台帳 P2-08 の md5 と同じ)。29,075,142 バイト。`QUALITY.json` の 60 分を超える空き 288 件のうち週の閉まり 278 件(定義「gap start weekday == Friday AND gap end weekday in {Sunday, Monday}」)、平日の空き 10 件(どれも日本時間の週をまたがない。§4 のコマンド)。取得の目録の曜日ごとの数: 日曜 "ok" 278・土曜 "empty" 281・金曜 "ok" 279 | (a) **閉まっている間の行の形**: 日曜の日のファイルに行があり、平日の空き 4 件が日曜 00:00 UTC に終わる(例 `2020-12-31 23:59:00+00:00 → 2021-01-03 00:00:00+00:00`)ので、日曜は UTC の 0 時から行がある(為替が開く前の値の動かない行)と読める【推定】。カードは値の動かない行を週明けにしない(INTENT_MAP.md C-5)。測定の回に週明けの時刻の分布で確かめる(INTENT_MAP.md §5)。(b) BID だけ(README)。窓の符号には BID と仲値の差がほぼ効かない【推定】。(c) `timestamp` が 1 分の始まりであることは取得の道具の説明からの【推定】(カード 3 の調達票と同じ) |

## 2. 意図の地図の △・✕ を切り分けるためのデータ(INTENT_MAP.md §4・CARD.md 迷った点。このカードの持ち高には使わない)

| 必要データ | 入手経路の候補(3 つ以上) | 到達確認 | 欠けと対処 |
|---|---|---|---|
| CME の BTC 先物・1 分足・2017-12〜2022(迷った点 1 (a): 暗号資産の「週末の窓」の別の読み) | (1) CME の公式の履歴(DataMine)— 有料【推定】 (2) 第三者の履歴の業者(Databento・FirstRate Data など)— 有料か、期間はどこまでかは【未確認】 (3) 公開の相場サイトの 1 分足の書き出し — 遡れる長さは【未確認】 | 到達確認は未(この回は叩いていない)。手元に無い【事実: `ls backtest_data \| grep -i 'cme\|futures\|n225'` の出力は `n225f_225labo_20260828` と `audit_fetch_JPX_n225f_months_20260906` だけ】 | 「取れない」とは書かない。経路 (3) の無料の範囲を先に確かめるかはリードが決める。有料の経路は収益の算段が立つ前に提案しない(A-3)。市場の表 `MARKETS` に CME は無いので、足すなら表に足す必要がある |
| 日経 225 先物・1 分足(迷った点 1 (b)・INTENT_MAP.md §4-1: 別の市場の週明け) | (1) **225labo の無料の配布**(手元 `backtest_data/n225f_225labo_20260828/`) (2) JPX の公式の履歴データ — 有料【推定】 (3) 証券会社の取引の道具の書き出し【未確認】 | 2026-10-02、`ls` と `README_SOURCE.md` の冒頭を読んだ。結果【事実】: `bars_1min.csv.gz`・`MD5SUMS` がある。README「分足データ: 2001年〜」(配布元のページの記述)、「本スナップショット(N225f_2026.xlsx)は**ラージ(日経225先物)**の継続系列」。手元のファイルの期間は目録で確かめていない【未確認】 | 市場の表の `jpx:n225_futures` に当たる。期間と夜間の時間帯(週の閉まりの形)は測定の回の前に目録で確かめる。利用条件は外部公開の禁止(README) |
| USDJPY・1 分足・2023-01-01〜2023-12-17(迷った点 4: 期間の延長) | (1) 手元 `backtest_data/fx_usdjpy_1m_20260822.csv.gz`(Dukascopy) (2) Dukascopy から同じ道具 `scripts/fetch_dukascopy.py` で取り直す【未確認】 (3) GMO の FX 公開 API【未確認】 | 2026-10-02、2017〜2022 の置き場の README を読んだ。結果【事実】: 「Extends `backtest_data/fx_usdjpy_1m_20260822.csv.gz` (2023-01-01 onward)」「the existing snapshot's first row is 2023-01-01 00:00 UTC」「Safe to concatenate」。最後の行の日付は目録に無い【未確認】。封印の台帳 P2-08 に名前が無い【事実: `grep -n -A6 '20260822' backtest_data/phase2_sealed/P2-08/SEALED.json` が空】。ルートの `backtest_data/MD5SUMS` には行がある(26 行) | 封印の境(2023-12-18)の後の行を含むかは【未確認】。含むと読んで `md5sum -c` は打たない。延ばすかはリードが決める |

## 3. 否定的事実の引用

- N-002(bitFlyer 公開 REST の約定履歴は約 31 日分のみ。2026-08 登録、賞味 90 日): 期限内(2026-10-02 時点)。1 分足は lightchart で取れている(上の到達確認)。

## 4. この回に打ったコマンド(到達確認)

```
ls backtest_data/fx_usdjpy_1m_20170801_20221231/ backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/
cat backtest_data/fx_usdjpy_1m_20170801_20221231/README.md
grep -n -i 'maint\|weekend\|メンテ\|gap\|null\|ts ' backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/README.md
head -20 backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/gaps_gt5min.txt
grep -n '"2017"' -A4 backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_index.json
grep -c candles_1m_20 backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/MD5SUMS      # 12
grep 'usdjpy_1m.csv.gz' backtest_data/fx_usdjpy_1m_20170801_20221231/MD5SUMS
ls -l backtest_data/fx_usdjpy_1m_20170801_20221231/usdjpy_1m.csv.gz
grep -n -i 'usdjpy\|seal_from' backtest_data/phase2_sealed/P2-08/SEALED.json
grep -n -A6 '20260822' backtest_data/phase2_sealed/P2-08/SEALED.json; grep -rn '20260822' backtest_data/MD5SUMS
ls backtest_data | grep -i 'cme\|futures\|n225'
head -15 backtest_data/n225f_225labo_20260828/README_SOURCE.md
# QUALITY.json の平日の空き 10 件を日本時間の週の番号に直す(行は開かない)
python3 -c "import json,datetime as dt; q=json.load(open('backtest_data/fx_usdjpy_1m_20170801_20221231/QUALITY.json')); [print(x['from'],'->',x['to'],(dt.datetime.fromisoformat(x['from'])+dt.timedelta(hours=9)).isocalendar()[1],(dt.datetime.fromisoformat(x['to'])+dt.timedelta(hours=9)).isocalendar()[1]) for x in q['gaps_over_60min']['non_weekend_gaps']]"
#   出力: 10 行とも 2 つの週の番号が同じ(例 2020-12-31 23:59:00+00:00 -> 2021-01-03 00:00:00+00:00 53 53)
# 取得の目録の曜日ごとの数
python3 -c "import json,datetime as dt,collections; m=json.load(open('backtest_data/fx_usdjpy_1m_20170801_20221231/_work/USDJPY_1m.csv.bid.manifest.json'))['days']; print(sorted(collections.Counter((dt.date.fromisoformat(k).strftime('%a'),v) for k,v in m.items()).items()))"
#   出力: [(('Fri','empty'),1),(('Fri','ok'),279),(('Mon','ok'),279),(('Sat','empty'),281),(('Sun','empty'),1),(('Sun','ok'),278),(('Thu','ok'),283),(('Tue','ok'),283),(('Wed','ok'),280)]
```
