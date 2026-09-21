# 段 A 事前登録から移した実測の出力(20 ブロック)

2026-09-19、L-228。元は `docs/PHASE2/O3C/PRICE_LEVEL/REACTION_PREREG_2026-09-18.md`(移す前の版 = コミット fef6abb 時点の行番号)。出力の日付は各ブロックの直前の表示のとおり(2026-09-18)。

## #1(元: 1. 意図と実装の突き合わせ(§0.5。無ければ事前登録を書かない) / 旧 行 555-563)

```
行数: 17
  ○ = 4
  △ = 8
  ✕ = 4
  ＋ = 1
内訳の合計: 17
I-12 の印: △
```

## #2(元: 2. 対象データ(パス・期間・行数) / 旧 行 629-632)

```
清算 zip: 472 本 / 暦日: 478 日 / 在庫に無い日: 6
在庫に無い日の一覧: ['2023-09-09', '2023-09-23', '2023-09-25', '2024-06-01', '2024-06-11', '2024-06-12']
```

## #3(元: 3. 分割(探索 / 判定の境界) / 旧 行 699-704)

  ```
  判定区間の日数: 456
  約定欠落 2023-09-25: 判定区間に入る = False / 清算 zip 在庫 = False
  約定欠落 2024-06-11: 判定区間に入る = False / 清算 zip 在庫 = False
  約定欠落 2024-06-12: 判定区間に入る = False / 清算 zip 在庫 = False
  ```

## #4(元: 4. 構成ファミリー(列挙する。後から追加しない) / 旧 行 1090-1121)

```
--- gap60_w8(control_uniform 225 行 / control_matched 213 行)---
  bin_pct                    uniform  225 / matched  213
  doi_pre_1h                 uniform  225 / matched  211
  dist_node_bp               uniform  225 / matched  213
  dist_vwap_bp               uniform  225 / matched  213
  oi_dist_node_bp            uniform  213 / matched  192
  oi_dist_vwap_bp            uniform  213 / matched  192
  dist_node_bp_liqdir        uniform    0 / matched    0
  dist_vwap_bp_liqdir        uniform    0 / matched    0
  oi_dist_node_bp_liqdir     uniform    0 / matched    0
  oi_dist_vwap_bp_liqdir     uniform    0 / matched    0
  implied_leverage           uniform    0 / matched    0
  bundle_n_events_dedup      uniform    0 / matched    0
  bundle_total_qty_accum     uniform    0 / matched    0
  side                       uniform    0 / matched    0
--- gap60_w24(control_uniform 225 行 / control_matched 216 行)---
  bin_pct                    uniform  225 / matched  216
  doi_pre_1h                 uniform  225 / matched  215
  dist_node_bp               uniform  225 / matched  216
  dist_vwap_bp               uniform  225 / matched  216
  oi_dist_node_bp            uniform  186 / matched  177
  oi_dist_vwap_bp            uniform  186 / matched  177
  dist_node_bp_liqdir        uniform    0 / matched    0
  dist_vwap_bp_liqdir        uniform    0 / matched    0
  oi_dist_node_bp_liqdir     uniform    0 / matched    0
  oi_dist_vwap_bp_liqdir     uniform    0 / matched    0
  implied_leverage           uniform    0 / matched    0
  bundle_n_events_dedup      uniform    0 / matched    0
  bundle_total_qty_accum     uniform    0 / matched    0
  side                       uniform    0 / matched    0
```

## #5(元: 6. 主指標と帰無(§4.2) / 旧 行 1408-1412)

  ```
  束の合計(mixed 込み) = 225 / mixed = 1 / 非 mixed = 224
  control_matched_made = 213 / 候補なし = 12 / 和 = 225
  作成率 = made / 束(mixed 込み) = 0.946667
  ```

## #6(元: 8. 検出力(MDE)— 走らせる前に書く(§4.1) / 旧 行 1767-1775)

```
0.05         z=1.9600 z合計=2.801585 倍率=1.000000000
0.05/2640    z=4.2770 z合計=5.118662 倍率=1.827059263
0.05/47520   z=4.8816 z合計=5.723239 倍率=2.042857500
0.05/576     z=3.9248 z合計=4.766411 倍率=1.701326397
検定数 48*2*6 = 576
t=2.0 の両側 p = 0.04550026389635842
α=0.05/576 の両側 z = 3.924789651405654
```

## #7(元: 8. 検出力(MDE)— 走らせる前に書く(§4.1) / 旧 行 2019-2021)

```
照合したセル: 152 / 一致 152 / 食い違い 0
```

## #8(元: 8. 検出力(MDE)— 走らせる前に書く(§4.1) / 旧 行 2235-2240)

  ```
  判定区間の日数: 456
  metrics の zip がある判定区間の日: 359 / 456
  当日 + 前日の両方がある日: 356 / 456
  当日の zip が無い日: 97
  ```

## #9(元: 8. 検出力(MDE)— 走らせる前に書く(§4.1) / 旧 行 2284-2291)

  ```
  判定区間の日数: 456
  metrics の zip が無い判定区間の日: 97
    塊: 2023-11-19 〜 2023-11-19 (1 日)
    塊: 2024-03-04 〜 2024-05-31 (89 日)
    塊: 2024-06-02 〜 2024-06-08 (7 日)
  2024-06-01 は判定区間に入っているか: False
  ```

## #10(元: 8. 検出力(MDE)— 走らせる前に書く(§4.1) / 旧 行 2295-2301)

  ```
  2023-11-19,
  2024-03-04 〜 2024-03-31 (28 日),
  2024-04-01 〜 2024-04-30 (30 日),
  2024-05-01 〜 2024-05-31 (31 日),
  2024-06-02 〜 2024-06-08 (7 日)
  ```

## #11(元: 11. サニティ(§6・§8。走行の前に通す) / 旧 行 3058-3063)

```
backtest_data/o3c_reaction_20260918_anchor/table.csv
  行数: 22036 / anchor_lag_ms 最小: 0.0 / 負の件数: 0
backtest_data/o3c_reaction_20260918_anchor_trades/table.csv
  行数: 22036 / anchor_lag_ms 最小: 0.0 / 負の件数: 0
```

## #12(元: 12. 射程(何を測っていないか。「検出されず」「測定不能」を書くときに必ず併記する) / 旧 行 3180-3185)

  ```
  gap60_w8  SELL n=117 順(fwd)=18(15.385%) 逆=111(94.872%)
  gap60_w8  BUY  n=107 順(fwd)=22(20.561%) 逆=95(88.785%)
  gap60_w24 SELL n=117 順(fwd)=22(18.803%) 逆=107(91.453%)
  gap60_w24 BUY  n=107 順(fwd)=40(37.383%) 逆=87(81.308%)
  ```

## #13(元: 12. 射程(何を測っていないか。「検出されず」「測定不能」を書くときに必ず併記する) / 旧 行 3299-3303)

  ```
  ('metrics', 'COIN-M') は 1 行も出ない(0 日分)
  ('清算', 'COIN-M') 9 日分 2026-09-09 〜 2026-09-17
  ('約定', 'COIN-M 以外') 66 日分 2024-11-01 〜 2026-09-05
  ```

## #14(元: 14. 走行の手順(リードが走らせる。委任先は走らせない) / 旧 行 3582-3587)

```
1日あたり=1.3667秒 1束あたり=0.027333秒
456日で外挿: 2.61+456*1.3667 = 625.8秒 = 10.4分
21198束で外挿: 2.61+21198*0.027333 = 582.0秒 = 9.7分
6本: 58〜63分
```

## #15(元: 14. 走行の手順(リードが走らせる。委任先は走らせない) / 旧 行 4122-4134)

```
W = 8h:
日数 456 / 束 21378(mixed 180)
非 mixed 束 21198 / fwd_node 定義できる 5876
  SELL 12097 中 3651 / BUY 9101 中 2225
(real 5m32s)

W = 24h:
日数 456 / 束 21378(mixed 180)
非 mixed 束 21198 / fwd_node 定義できる 8590
  SELL 12097 中 5276 / BUY 9101 中 3314
(real 5m12s)
```

## #16(元: 14. 走行の手順(リードが走らせる。委任先は走らせない) / 旧 行 4246-4263)

```
gap60_w8/table.csv: 行×列 (662, 157) -> (662, 157) / 列名の並び一致 True / 全列一致 True
gap60_w8/table_mixed.csv: 行×列 (1, 157) -> (1, 157) / 列名の並び一致 True / 全列一致 True
gap60_w8/summary.json: 食い違い 5 件 -> .elapsed_sec: 9.94 -> 9.76 / .tool_commit: b5dd8e1c65ac… -> f154bb06f0cd… / .tool_dirty.git diff --quiet HEAD の終了コード: (無し) -> 1 / .tool_dirty.変更ファイル: [… backtest_data/o3c_reaction_20260918_sample/gap60_w8/MD5SUMS, …/summary.json, docs/AUDITOR/TRACE/2026-09-18_fa7bf0d4.json, scripts/…, tests/… ] -> (無し) / .tool_dirty.見た範囲: (無し) -> ["scripts/o3c_reaction.py", "scripts/o3c_reaction_judge.py"]
gap60_w8/MD5SUMS: 変わったファイル ['summary.json']
gap60_w24/table.csv: 行×列 (665, 157) -> (665, 157) / 列名の並び一致 True / 全列一致 True
gap60_w24/table_mixed.csv: 行×列 (1, 157) -> (1, 157) / 列名の並び一致 True / 全列一致 True
gap60_w24/summary.json: 食い違い 5 件 -> .elapsed_sec: 9.46 -> 9.61 / .tool_commit: b5dd8e1c65ac… -> f154bb06f0cd… / .tool_dirty の 3 鍵の入れ替え
gap60_w24/MD5SUMS: 変わったファイル ['summary.json']
gap30_w8/table.csv: 行×列 (784, 157) -> (784, 157) / 列名の並び一致 True / 全列一致 True
gap30_w8/table_mixed.csv: 行×列 (1, 157) -> (1, 157) / 列名の並び一致 True / 全列一致 True
gap30_w8/summary.json: 食い違い 5 件 -> .elapsed_sec: 10.7 -> 10.29 / .tool_commit: b5dd8e1c65ac… -> f154bb06f0cd… / .tool_dirty の 3 鍵の入れ替え
gap30_w8/MD5SUMS: 変わったファイル ['summary.json']
gap180_w8/table.csv: 行×列 (503, 157) -> (503, 157) / 列名の並び一致 True / 全列一致 True
gap180_w8/table_mixed.csv: 行×列 (2, 157) -> (2, 157) / 列名の並び一致 True / 全列一致 True
gap180_w8/summary.json: 食い違い 5 件 -> .elapsed_sec: 9.4 -> 9.24 / .tool_commit: b5dd8e1c65ac… -> f154bb06f0cd… / .tool_dirty の 3 鍵の入れ替え
gap180_w8/MD5SUMS: 変わったファイル ['summary.json']
```

## #17(元: 14. 走行の手順(リードが走らせる。委任先は走らせない) / 旧 行 4278-4295)

```
gap60_w8/table.csv: 行×列 (662, 157) -> (662, 157) / 列名の並び一致 True / 全列一致 True
gap60_w8/table_mixed.csv: 行×列 (1, 157) -> (1, 157) / 列名の並び一致 True / 全列一致 True
gap60_w8/summary.json: 食い違い 5 件 -> .elapsed_sec: 10.48 -> 9.94 / .tool_commit: 759f0920e7cb56174cc97239a0989c7a474d2432 -> b5dd8e1c65ac7d7dd993f6fb23b723e36688bfda / .tool_dirty.変更ファイル: (無し) -> [...] / .tool_dirty.汚れているか: (無し) -> True / .tool_dirty.状態: (無し) -> dirty
gap60_w8/MD5SUMS: 変わったファイル ['summary.json']
gap60_w24/table.csv: 行×列 (665, 157) -> (665, 157) / 列名の並び一致 True / 全列一致 True
gap60_w24/table_mixed.csv: 行×列 (1, 157) -> (1, 157) / 列名の並び一致 True / 全列一致 True
gap60_w24/summary.json: 食い違い 5 件 -> .elapsed_sec: 10.31 -> 9.46 / .tool_commit: 759f0920e7cb… -> b5dd8e1c65ac… / .tool_dirty の 3 鍵の追加
gap60_w24/MD5SUMS: 変わったファイル ['summary.json']
gap30_w8/table.csv: 行×列 (784, 157) -> (784, 157) / 列名の並び一致 True / 全列一致 True
gap30_w8/table_mixed.csv: 行×列 (1, 157) -> (1, 157) / 列名の並び一致 True / 全列一致 True
gap30_w8/summary.json: 食い違い 5 件 -> .elapsed_sec: 10.67 -> 10.7 / .tool_commit: 759f0920e7cb… -> b5dd8e1c65ac… / .tool_dirty の 3 鍵の追加
gap30_w8/MD5SUMS: 変わったファイル ['summary.json']
gap180_w8/table.csv: 行×列 (503, 157) -> (503, 157) / 列名の並び一致 True / 全列一致 True
gap180_w8/table_mixed.csv: 行×列 (2, 157) -> (2, 157) / 列名の並び一致 True / 全列一致 True
gap180_w8/summary.json: 食い違い 5 件 -> .elapsed_sec: 9.95 -> 9.4 / .tool_commit: 759f0920e7cb… -> b5dd8e1c65ac… / .tool_dirty の 3 鍵の追加
gap180_w8/MD5SUMS: 変わったファイル ['summary.json']
```

## #18(元: 14. 走行の手順(リードが走らせる。委任先は走らせない) / 旧 行 4316-4333)

```
gap60_w8/table.csv: 行×列 (662, 157) -> (662, 157) / 列名の並び一致 True / 全列一致 True
gap60_w8/table_mixed.csv: 行×列 (1, 157) -> (1, 157) / 列名の並び一致 True / 全列一致 True
gap60_w8/summary.json: 食い違い 2 件 -> .elapsed_sec: 10.8 -> 10.48 / .tool_commit: (無し) -> 759f0920e7cb56174cc97239a0989c7a474d2432
gap60_w8/MD5SUMS: 変わったファイル ['summary.json']
gap60_w24/table.csv: 行×列 (665, 157) -> (665, 157) / 列名の並び一致 True / 全列一致 True
gap60_w24/table_mixed.csv: 行×列 (1, 157) -> (1, 157) / 列名の並び一致 True / 全列一致 True
gap60_w24/summary.json: 食い違い 2 件 -> .elapsed_sec: 10.24 -> 10.31 / .tool_commit: (無し) -> 759f0920e7cb56174cc97239a0989c7a474d2432
gap60_w24/MD5SUMS: 変わったファイル ['summary.json']
gap30_w8/table.csv: 行×列 (784, 157) -> (784, 157) / 列名の並び一致 True / 全列一致 True
gap30_w8/table_mixed.csv: 行×列 (1, 157) -> (1, 157) / 列名の並び一致 True / 全列一致 True
gap30_w8/summary.json: 食い違い 2 件 -> .elapsed_sec: 11.18 -> 10.67 / .tool_commit: (無し) -> 759f0920e7cb56174cc97239a0989c7a474d2432
gap30_w8/MD5SUMS: 変わったファイル ['summary.json']
gap180_w8/table.csv: 行×列 (503, 157) -> (503, 157) / 列名の並び一致 True / 全列一致 True
gap180_w8/table_mixed.csv: 行×列 (2, 157) -> (2, 157) / 列名の並び一致 True / 全列一致 True
gap180_w8/summary.json: 食い違い 2 件 -> .elapsed_sec: 10.18 -> 9.95 / .tool_commit: (無し) -> 759f0920e7cb56174cc97239a0989c7a474d2432
gap180_w8/MD5SUMS: 変わったファイル ['summary.json']
```

## #19(元: 14. 走行の手順(リードが走らせる。委任先は走らせない) / 旧 行 4342-4359)

```
gap60_w8/table.csv: 行×列 (662, 157) -> (662, 157) / 列名の並び一致 True / 全列一致 True
gap60_w8/table_mixed.csv: 行×列 (1, 157) -> (1, 157) / 列名の並び一致 True / 全列一致 True
gap60_w8/summary.json: 食い違い 1 件 -> .elapsed_sec: 10.04 -> 10.8
gap60_w8/MD5SUMS: 変わったファイル ['summary.json']
gap60_w24/table.csv: 行×列 (665, 157) -> (665, 157) / 列名の並び一致 True / 全列一致 True
gap60_w24/table_mixed.csv: 行×列 (1, 157) -> (1, 157) / 列名の並び一致 True / 全列一致 True
gap60_w24/summary.json: 食い違い 1 件 -> .elapsed_sec: 9.56 -> 10.24
gap60_w24/MD5SUMS: 変わったファイル ['summary.json']
gap30_w8/table.csv: 行×列 (784, 157) -> (784, 157) / 列名の並び一致 True / 全列一致 True
gap30_w8/table_mixed.csv: 行×列 (1, 157) -> (1, 157) / 列名の並び一致 True / 全列一致 True
gap30_w8/summary.json: 食い違い 1 件 -> .elapsed_sec: 9.9 -> 11.18
gap30_w8/MD5SUMS: 変わったファイル ['summary.json']
gap180_w8/table.csv: 行×列 (503, 157) -> (503, 157) / 列名の並び一致 True / 全列一致 True
gap180_w8/table_mixed.csv: 行×列 (2, 157) -> (2, 157) / 列名の並び一致 True / 全列一致 True
gap180_w8/summary.json: 食い違い 1 件 -> .elapsed_sec: 9.4 -> 10.18
gap180_w8/MD5SUMS: 変わったファイル ['summary.json']
```

## #20(元: 14. 走行の手順(リードが走らせる。委任先は走らせない) / 旧 行 4924-4950)

```
--- 予測できる ---
ファイル数: 1
行数: docs/PHASE2/O3C/PRICE_LEVEL/REACTION_PREREG_2026-09-18.md:6
ファイルごとの出現数:       6 docs/PHASE2/O3C/PRICE_LEVEL/REACTION_PREREG_2026-09-18.md
出現数の合計: 6
--- 使える ---
ファイル数: 1
行数: docs/PHASE2/O3C/PRICE_LEVEL/REACTION_PREREG_2026-09-18.md:6
ファイルごとの出現数:       6 docs/PHASE2/O3C/PRICE_LEVEL/REACTION_PREREG_2026-09-18.md
出現数の合計: 6
--- 有効 ---
ファイル数: 1
行数: docs/PHASE2/O3C/PRICE_LEVEL/REACTION_PREREG_2026-09-18.md:14
ファイルごとの出現数:      21 docs/PHASE2/O3C/PRICE_LEVEL/REACTION_PREREG_2026-09-18.md
出現数の合計: 21
--- 差なし ---
ファイル数: 1
行数: docs/PHASE2/O3C/PRICE_LEVEL/REACTION_PREREG_2026-09-18.md:12
ファイルごとの出現数:      16 docs/PHASE2/O3C/PRICE_LEVEL/REACTION_PREREG_2026-09-18.md
出現数の合計: 16
--- 陰性 ---
ファイル数: 1
行数: docs/PHASE2/O3C/PRICE_LEVEL/REACTION_PREREG_2026-09-18.md:29
ファイルごとの出現数:      36 docs/PHASE2/O3C/PRICE_LEVEL/REACTION_PREREG_2026-09-18.md
出現数の合計: 36
```
