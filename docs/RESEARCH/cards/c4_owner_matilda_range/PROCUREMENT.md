# カード c4_owner_matilda_range: 調達票(研究手順書 §14)

研究手順書 §14 の表。到達確認は、データの置き場の目録(README・MD5SUMS・`candles_1m_index.json`・`gaps_gt5min.txt` の冒頭の集計)と `ls -l` だけで行った。**データの行は開いていない**(封印の中も外も。測定はまだ)。`md5sum -c` も打っていない(2023 年のファイルは封印の境をまたぐ行を含み、照合は中身のバイトを読むため)。
主張の印: 【事実】= この回にファイルを読んで確かめた / 【推定】/ 【未確認】= この回に叩いていない。

## 1. 主に使うデータ(CARD.md の「使うデータと遅れ」)

最小 n: 定めない。W1 の測定器が検出力(C5 の e、有意 5%・検出力 80% で検出できる最小の平均)を出し、効果が見えないときに「不明(検出力が足りない)」と「小さい」を分ける(W1 の仕様 C5)。n を先に決めて足切りしない(A-8)。

| 必要データ(市場・粒度・期間・最小 n) | 入手経路の候補(3 つ以上) | 到達確認(日付・方法・結果) | 欠けと対処 |
|---|---|---|---|
| bitFlyer FX_BTC_JPY・1 分足(始値・高値・安値・終値・出来高)・2017-08-17T15:00Z〜2023-12-17T15:00Z(日本時間 2017-08-18 0 時〜2023-12-18 0 時。CARD.md の測る期間)。窓の分(40 分、変種なら最長 1 週)の足を開始の前にも置ける・最小 n は上の注 | (1) **bitFlyer の lightchart**(`lightchart.bitflyer.com/api/ohlc`、公開・無認証・文書の無い API)— 手元 `backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/` (2) bitFlyer 公開 REST の約定履歴から 1 分足を組む — 約 31 日分しか遡れない(N-002)ので、この期間には使えない (3) 自前の記録(`paper_logs/tape/`)— 2026 年の分だけ【推定: この回は読んでいない。置き場の名前とカード 3 の調達票の記述】、と手元 `backtest_data/fx_btc_jpy_1m_continuous_20260906/`(README の期間 2026-07-23〜2026-09-05)— この期間には届かない【事実: README の Span】 (4) 第三者の有料の履歴(Tardis など)— bitFlyer FX の 2017〜2023 の 1 分足を持つかは【未確認】 (5) lightchart の生のページ `raw_YYYY.tar`(同じ置き場)— 1 分足の CSV を作り直す材料【事実: `ls`】 | 2026-10-02、`ls -l`・README・`candles_1m_index.json`・MD5SUMS・`gaps_gt5min.txt` の冒頭を読んだ。結果【事実】: 年ごとのファイル 2017〜2023 があり(13,007,293〜25,498,413 バイト)、目録の行数は 2017 年 525,596 行(最初 2017-01-01 00:00)、2018・2019・2021・2022・2023 年 525,600 行、2020 年 526,668 行。2023 年の最後の行 2023-12-31 23:59 UTC。時刻の列 `ts` は 1 分の始まり(UTC)。MD5SUMS に 2017〜2023 の 7 ファイルが載り、目録の md5 と同じ値 | (a) 約定 0 の分は OHLC が null・量 0(README「294,741 rows are null-OHLC」)。カードは出来高 0 の足を窓に入れず(INTENT_MAP P-3)、その分では呼ばれない(run.py)。(b) 5 分を超える空き(`gaps_gt5min.txt`: 2017 年 391 件・5,470 分、2018 年 312 件・4,429 分、2019 年 374 件・5,988 分、2020 年 389 件・7,423 分、2021 年 395 件・5,949 分、2022 年 375 件・5,039 分、2023 年 1,316 件・12,589 分)。窓は時刻で切るので、空きの後の窓は足が少ない(INTENT_MAP P-1)。空けた時間は測定器が記録する。(c) 2017〜2018 年に 1 分で 10% を超える動きが約 15 件(README)。除かない(置き場の決まり「flag-only」)。このカードは窓の端と平均実体にその足が入る。(d) 保守の時間(19:00〜19:10 UTC)の平らな足 1,483 本(README)。除かない。(e) 他の bitFlyer の系列との一致は 2026 年の重なりで 88.5%(README)。2017〜2023 年の別の出所との突き合わせは無い【未確認】。(f) 2023 年のファイルは封印の台帳に載る(`backtest_data/phase2_sealed/P2-08/SEALED.json`・`P2-08b/SEALED.json` に `FX_BTC_JPY` の語がある【事実: grep】)。測る期間は境 2023-12-18 の前で終わる(`scripts/check_card.py` が通る) |

## 2. 意図の地図の △ を切り分けるためのデータ(INTENT_MAP.md §2)

| 必要データ | 入手経路の候補(3 つ以上) | 到達確認 | 欠けと対処 |
|---|---|---|---|
| I-8(△)の基準を「値段に対する割合」にした変種を作るなら: 同じ 1 分足の終値(上の行と同じ) | 上の行と同じ | 上の行と同じ | 新しいデータは要らない。変種を足すかはオーナーの問い 4 の答えの後 |
| I-9(△)の「大きく動いた」を、オーナーの当時の見方(原典の別の版)と照らす: マチルダの別の版のコード | (1) 手元 `docs/legacy/` の 2 本(v37・v52)【事実: `ls`】 (2) オーナーの手元の別の版(v38〜v51 など)【未確認: 有るかどうかを聞いていない】 (3) オーナーが配った先(コードの冒頭の配布の記録)【未確認】 | 2026-10-02、`docs/legacy/README.md` を読んだ。v37 と v52 の 2 本だけ【事実】 | v52 のコメント「41から 不安定なブレイクをやめて」により、v41〜v51 の版があった【推定】。リードがオーナーに有無を聞くかを決める(INTENT_MAP §7 の問い 5 と一緒に聞ける) |
| 段(I-19)を執行層で測るとき: bitFlyer の板・約定 | (1) オーナーの PC の生 WS の記録(L-099 の記録)【未確認: 期間】 (2) 手元 `backtest_data/auto_bitflyer_executions_*`【事実: `ls` で名前だけ】 (3) bitFlyer 公開 REST の約定(約 31 日、N-002) | この回は目録を読んでいない | 執行層の単位で調達票を書く。このカードでは使わない |

## 3. 否定的事実の引用

- N-002(bitFlyer 公開 REST の約定履歴は約 31 日分のみ。2026-08 登録、賞味 90 日): 期限内(2026-10-02 時点。登録月の終わり 2026-08-31 から数えても 32 日)。同じ行の注「lightchart.bitflyer.com は 2015-11 まで分足を返す」のとおり、1 分足は lightchart で取れている【事実: `docs/NEGATIVE_FACTS.md` 6 行】。

## 4. この回に打ったコマンド(到達確認)

```
ls -la backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/
cat backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/README.md
cat backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_index.json | head -60
python3 -c "import json; d=json.load(open('backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_index.json')); print(d['years']['2023'])"
  # {'rows': 525600, 'first': '2023-01-01 00:00:00+00:00', 'last': '2023-12-31 23:59:00+00:00', 'md5': 'a69c911da1a0946d720613d28aa9ebec', 'bytes': 18962595}
grep -n "candles_1m_20\(17\|18\|19\|20\|21\|22\|23\)" backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/MD5SUMS   # 7 行(3〜9 行目)
head -20 backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/gaps_gt5min.txt   # 年ごとの集計(上の表の (b))
ls backtest_data/fx_btc_jpy_1m_continuous_20260906/; head -12 backtest_data/fx_btc_jpy_1m_continuous_20260906/README.md
ls backtest_data/phase2_sealed/; grep -l "FX_BTC_JPY" backtest_data/phase2_sealed/*/SEALED.json   # P2-08・P2-08b
grep -n "N-002" docs/NEGATIVE_FACTS.md
python scripts/check_card.py docs/RESEARCH/cards/c4_owner_matilda_range/CARD.md   # 通る
```

## 5. リード盲点監査

まだ(リードが安い監査者 1 名に、この票と CARD.md だけを渡して行う。W4 の仕様 §2 の 6)。
