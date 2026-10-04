# 委任文: 今の paper bot と週末ギャップの「なぜ」の分解の表(L-627 の段取り 4、2026-10-04)

あなたは本リポジトリの実装エージェントです。表を作る台本を書き、走らせ、表を出して報告してください。読み・「なぜ」・判定はリードが書くので、あなたは書かない。コミット・プッシュはしない。

## 着手前の表

やろうとすること × オーナーの原文の該当語(逐語)の 2 列を報告の冒頭に出す(CLAUDE.md §0.1)。オーナーの原文: L-628「**ア では進めてください**」。中身は `docs/RESEARCH/cards/ROUND0_SIX_2026-10-04.md` の「次にすること」1・2(リードが書いた)。右が空の行は着手せず問いとして返す。

## 読了必須

`docs/RESEARCH/cards/ROUND0_SIX_2026-10-04.md`、`scripts/w4_measure/overlap_daily.py`(SERIES と読み込み)、`scripts/w4_measure/vol_split_daily.py`(日の区分 classify)、`scripts/w4_measure/common.py` の `load_bars`、`src/bot/research/trade_record.py`(trades.json.gz の形)。

## 作るもの: `scripts/w4_measure/round0_decomp.py`(読むだけ・冪等・ネットワークなし)と試験 `tests/research/test_round0_decomp.py`

読み方の決まり(この文を台本の docstring の冒頭にそのまま写す。変えない・足さない):

D1 今の paper bot(`backtest_runs_shared/cards/c1_xborder_mom/default/`、overlap_daily.py の SERIES と同じ読み込み)の日ごとの損益を、
   暦年(日本時間の日の年)× 前の日のボラの区分(vol_split_daily.py の classify、低・中・高・区分なし)で分け、升ごとに
   日数・損益の和・1 日あたりの平均を出す。各年の行に、その年の損益の和に占める各区分の割合も出す。
D2 週末ギャップ BTC(`backtest_runs_shared/cards/c6_weekend_gap_revert/btc/trades.json.gz`)の取引ごとに、
   窓の大きさ g = (取引の入りの値段 / 入りの時刻より前の最後の金曜(日本時間)の bitFlyer FX_BTC_JPY の 1 分足の最後の終値 − 1) × 1e4(bp)
   を出す。足は common.load_bars(封印の門をそのまま使う。2023-12-18 以降を読まない)。g の符号と持ち高の向きが逆か同じか
   (窓を埋める向きか広げる向きか)、|g| の 3 つの帯(全取引の |g| の 1/3・2/3 分位。分位の値も出す)、暦年 で分け、
   升ごとに取引の数・損益の和・1 取引あたり・勝ちの数を出す。入りの値段は trades.json.gz の entry_px。
D3 区間・検定・境は出さない。経費なし。数字は手で書かない。

出力: `docs/RESEARCH/cards/ROUND0_DECOMP/TABLES.md` と `decomp.json`。

試験: D1 の升の和が年の和に一致する、D2 の「最後の金曜の終値」の取り方(合成の足で、金曜の 23:59 JST の足を拾い、土曜の足を拾わない)、|g| の帯の境。

## 制約

- `PYTHONPATH=src python -m pytest tests/research`(`-q` を足さない)を回し、末尾の行を報告に貼る。
- 最小の差分。既存のファイルを変えない(新しい 2 ファイルと出力だけ)。
- モデル名を書かない。結果の読み・「効く/効かない」の語を書かない。
- Do not commit. Do not push.

## 報告(この順)

1. 着手前の表 2. 作ったファイル 3. 試験の件数と pytest の末尾 4. 走らせのコマンドと所要時間 5. 迷った点と決めた理由

終わる条件: 2 つの表が出て試験が通った。上限: 作業 1 回。
