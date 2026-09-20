# 委任: 清算の連鎖 30 本の実物の抽出(O3C SIGNAL、続く / 止まるの単位の前段。2026-09-20)

## 0. オーナーとの対応表(逐語。この委任の範囲はここまで)

| やること | オーナーの原文の該当語(逐語) |
|---|---|
| 連鎖 30 本(続いた 15 / 止まった 15)を実物で読めるように抽出する | 「**その空の行もそれでいいです**」(L-263。空の行 = 「連鎖 30 本を実物で読む」) |
| 平均で潰さず、1 本ずつ・1 件ずつの列で出す | 「**平均で計算したらわからなくなって当然やろ**」(L-260) |
| 材料 8〜11 のデータの有無を確かめる | 「**その7つで足りているか検討しましたか**」(L-262)。材料の具体はリードの選択 |

**判定はしない。判定語(陽性/陰性/有意/差あり/検出されず/支持)を書かない。paper_logs/ を開かない。**

## 1. 入力(全部この環境にある)
- 清算のプリント行データ: `backtest_data/o3c_signal_explore5_20260920/rows_prints.csv.gz`(kind == "print" の 52,000 件。列: print_id, day, side, ts_ms, t0_ms, p0, p_pre, k, d, bundle_id, bundle_pos(最初/途中/最後/束の外), bundle_pos_single, notional, m_10, m_60, dist_node_bp, implied_leverage, oi_covered, next_same_side_gap_s, r_t0_* など)
- 約定: `backtest_data/binance_cm_o3c_20260913/aggTrades/BTCUSD_PERP/BTCUSD_PERP-aggTrades-YYYY-MM-DD.zip`(列 agg_trade_id, price, quantity, first_trade_id, last_trade_id, transact_time(ms), is_buyer_maker)。読み込みは `scripts/o3c_signal_explore5.py` の `load_day_trades` と同じ経路を使ってよい(`oid.load_agg_trades_with_maker`)
- 建玉の指標: `backtest_data/binance_cm_o3c_20260913/metrics/BTCUSD_PERP/`(5 分値)。距離 `dist_node_bp` の出所は `backtest_data/o3c_oi_distance_20260917` と `scripts/o3c_signal_explore5.py: build_oi_context`(`oid` モジュール)

## 2. 抽出の規則(機械的に。乱数の種は 20260920)
- 束 = explore 4 の gap 60 の束(`bundle_id`)。**続いた束** = プリントが 3 件以上の束。**止まった束** = 単発(`bundle_pos_single == 1`)。
- 456 日を 3 等分(日付順)し、各期間から 続いた束 5 本・止まった束 5 本を無作為に取る(合計 30 本)。同じ日から 2 本以上取らない。
- 30 本の一覧(束 id・日・側・件数・最初と最後の ts)を先に出す。

## 3. 1 本ごとに出すもの(markdown の表。数値は丸めて 4 桁まで)
A. **プリントの列**(1 件 1 行): 束の最初からの秒数 / 側 / 想定元本 USD / p₀ / k(bp とティック数 = |p₀ − p_pre| / 0.1)/ 直前の同じ側のプリントからの秒数 / 次の同じ側のプリントまでの秒数(無ければ「無し」)/ 直前 5 秒の成行の偏り = (買い成行の数量 − 売り成行の数量) ÷ (両方の合計)(is_buyer_maker == false が買い成行)/ 直前のプリントの p₀ からこのプリントの p₀ までの bp / d / dist_node_bp。
B. **値段の列**: 束の最初の ts の 60 秒前から、最後のプリントの t₀ の 120 秒後まで、**1 秒刻み**の最終約定価格(bp、最初のプリントの p₀ = 0 とし、清算の向きが正)。1 行に 10 秒ずつ並べる。プリントの起きた秒に ★ を付ける。
C. **その束の m_60(最初のプリント)・d(最初と最後)・dist_node_bp(最初と最後)・最後のプリントの後 60 秒 / 300 秒の bp**。

## 4. 材料 8〜11 の可否(調べて事実として書く。無ければ「この環境では無い」と、どこを見たかを併記)
8. この先 X bp 以内(5 / 10 / 20)にある建玉の量: `o3c_oi_distance_20260917` と `oid` モジュールから、帯ごとの建玉の量が出せるか(距離だけか)。出せるなら 30 本の最初のプリントについて値を出す。
9. 直前 5 秒の成行の偏り: A で出す(可)。
10. 資金調達率: この環境に Binance の fundingRate のアーカイブがあるか(`backtest_data/` を `ls`)。metrics の列名(建玉・ロングショート比)を列挙する。
11. 清算の大きさ ÷ 直前 60 秒の値幅: 約定から 60 秒の高値 − 安値(bp)を出し、想定元本と並べる(30 本の最初のプリント)。

## 5. 出力
- `docs/DATA/probes/20260920_o3c_cascade_read.md`(30 本の表。上の 2〜4)
- `docs/DATA/probes/20260920_o3c_cascade_read.py`(抽出のスクリプト。再実行で同じ 30 本が出る)
- 報告の先頭に §0 の対応表の写し、末尾に「実行したコマンドと出力の要所」「仕様に無い判断(全部)」「作ったファイル」「テストの末尾行(あれば)」。
- **他のファイルを変更しない。コミットしない。日本語で書く。**
