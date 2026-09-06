# INVENTORY: nk225_events_20260904 (P2-07 データ準備)

MD5SUMS 4件 OK。px.tar.gz を `px/` に展開(189ファイル、元ファイルは削除・変更せず保持)。
「usable」= 該当 ticker の px ファイルが存在し、effective_date の前後10営業日(ファイル内の行インデックス基準)が確保できる。

## 年別 usable/total(add / delete)

| 年 | add | delete | | 年 | add | delete |
|---|---|---|---|---|---|---|
| 2000 | 20/38 | 0/38 | | 2014 | 0/1 | 0/1 |
| 2001 | 9/13 | 2/13 | | 2015 | 2/2 | 2/2 |
| 2002 | 6/12 | 2/12 | | 2016 | 2/4 | 2/4 |
| 2003 | 3/6 | 1/6 | | 2017 | 4/4 | 2/4 |
| 2004 | 4/4 | 2/4 | | 2018 | 2/2 | 1/2 |
| 2005 | 9/10 | 1/10 | | 2019 | 4/4 | 1/4 |
| 2006 | 3/4 | 2/4 | | 2020 | 4/4 | 1/4 |
| 2007 | 3/3 | 2/3 | | 2021 | 3/3 | 3/4 |
| 2008 | 5/7 | 2/7 | | 2022 | 4/6 | 4/5 |
| 2009 | 1/2 | 0/2 | | 2023 | 6/6 | 6/6 |
| 2010 | 4/6 | 0/6 | | 2024 | 5/5 | 5/5 |
| 2011 | 5/6 | 0/6 | | 2025 | 4/4 | 3/4 |
| 2012 | 2/3 | 0/3 | | 2026 | 3/3 | 2/3 |
| 2013 | 1/3 | 1/3 | | | | |

合計 330件中 usable 165件(50%)。内訳: no_px_file 125件(92 ticker、fetch_log = no timestamps 65 / HTTP 404 27)、insufficient_window 40件(px はあるが前後10営業日に届かない=IPO・上場廃止近接)。delete 側は生存バイアスで一貫して usable 率が低い(特に2000-2016年、KNOWLEDGE_JP.md の既存指摘と一致)。

## カバレッジの欠陥(QUALITY_px.json, schema/nk225_events.json known_defects に記録)

- px 189ファイル全件が schema にマッチ(schema_undefined 0)。extreme_return 7142件/188ファイル、split_candidate 15件/4ファイル → close は株式分割未調整(adjclose は調整済み)。
- zero_volume 23507件/183ファイル。原因は2つ混在: (a) **確認済み**: 一部ティッカー(189中139)の初期(~2000-2001年)データに祝日の平坦・繰越行(例 px/1301.csv の2001-01-01〜03, 01-08、始値=高値=安値=終値=前日終値・出来高0)が混入 — px/IDX_N225.csv や2020年台の抜き取り確認では見られない、限定的な取得アーティファクト。(b) 通常の薄商い日。行インデックスを営業日カウントに使う本チェック・research_nk225_events.py 双方がこの影響を受けうる(未定量化、事前登録時に要考慮)。
- gaps 185件/183ファイル(GW10連休など既知の休場、実害なし)。

## Seal(P2-07)

`PYTHONPATH=src python scripts/phase2_seal.py --unit P2-07 --files events.csv + px/*.csv(189, 全件データあり) --primary events.csv`
→ 境界日 **2018-06-12**(events.csv の 2000-03-28〜2026-04-01 の70%点、unit全体に適用)。
dev: 256件(usable 104)、sealed: 74件(usable 61)。SEALED.json: `backtest_data/phase2_sealed/P2-07/SEALED.json`。
※ events.csv の時刻列は `effective_date` で `sealed.py` の TS_CANDIDATES 未対応だったため同ファイルに追加(`intake_ledger.py` 側は変更せず、data_quality.py の挙動に影響なし)。

## イベント日付の規約(事前登録用)

**UNKNOWN ではない**: `scripts/research_nk225_events.py` の `get_calendar_points()` が既に規約を明記—`effective_date` は入替が index に反映される最初の日で、リバランス取引(パッシブ勢の売買)は **effective_date の前営業日の引け(closing auction)**。出典: `docs/KNOWLEDGE_JP.md`(IR1 項)/ `RESEARCH_REPORT_2026-09-04ao.md`。P2-07 もこの規約に従うこと。
