# K1 段階 G — 違いの裁き(第 17 部、2018〜2023-12-17)

委任文 `docs/DATA/delegations/20261001_k1_stage_g.md` §2-3「**違いの裁き**: 升ごとに 当時の値 / 新しい値 / 差 / 裁き(一致・環境の欠陥・当時の誤り・不明・比べられない(封印))/ 根拠」。方針(オーナー逐語 L-479a)「**既にやった研究と同じ入力をして結果がどうなるかで評価しないと意味ないんじゃないの？**」= 過去の結果は正解ではなく違いの検出器。

生成: `PYTHONPATH=scripts:src python3 scripts/k1_newenv_g_old.py`(当時の値を `results/PHASE2/K1/xvenue/effect_*.json` と `results/PHASE2/K1/binance/effect_flip_noinval_delay.json` から機械で読む → `old_values.json`。別の書き方の読み直し 2 つ: ① `k1_newenv_g_old.py --check` = `XVENUE_TABLES.md` の表 (a)(b) の本文から読んで突き合わせ、`check_parse_old.txt`「cells read 412 / mismatches 0」。これは design の升だけを覆う ② sameclose・single・期間の行も覆うため、`diff_rows.json` の当時の値 130 行を `old_values.json` を通さずに当時の json から直接たどる別のコード(スクラッチパッド `check2.py`、08:2x UTC)で照合 → 「rows 130 ok 130 ng 0」。② は同じ json の別の読みで、md の表からの読みではない)→ `python3 scripts/k1_newenv_g_tables.py` → `python3 scripts/k1_newenv_g_diff.py && python3 scripts/k1_newenv_g_diff.py --md`。升ごとの全行 = `diff_table.md`(130 行)、機械の行 = `diff_rows.json`、件数 = `diff_summary.json`。

## 1. 件数(事実、出所 `diff_summary.json`)

| 裁き | 行数 |
|---|---|
| 一致(取引数が同じ かつ 平均 bp を小数 3 桁に丸めて同じ) | 118 |
| 当時の誤り(D-1) | 12 |
| 環境の欠陥 | 0 |
| 不明 | 0 |

比べた升: `design|full`(年 2018〜2022)・`design|2018_2021`(年 2018〜2021 と期間)・`design|2022_20231217` の 2022(78 升)・`sameclose` の同じ 3 種(参考列 (iii))・`single|full_unjoined`(参考列 (i)、当時 `effect_flip_noinval_delay.json`)。「一致」は数が同じという事実だけで、それ以上を言わない。

## 2. 比べられない升(印)

| 升 | 印 | 根拠 |
|---|---|---|
| 年 2023(全升) | **比べられない(封印、2023 は区間が違う)** | 当時は 2023-01-01〜12-31、今回は 2023-12-17 まで。当時の json に日次・取引ごとの記録が無い(`effect_binance_to_bitflyer.json` の鍵の一覧に `per_year` の n・mean_bp はあるが日・取引の欄が無い。鍵を全部たどった python の出力で確かめた)ので 12-17 で切って比べられない。例: 当時 `design|full|5` の 2023 = n 652 / +2.154、今回 641 / +1.96 は並べるだけ |
| 年 2024・2025・2026、期間 2022〜2026 | **比べられない(封印)** | 委任文 L-495「**案1で進めてください**」。代わりに新しい環境で 2022-01-01〜2023-12-17 の合計を出した(TABLES.md (a)、当時の値は無い) |
| 区間(95%) | 比べられない(D-3) | 当時と乱数の使い方(ブロックの取り方・乱数の呼び順)が同じと確かめていない。並べるだけ(`diff_table.md` の期間の行) |
| 年 2017 | 比べていない | 委任文 §2-2 の年別は 2018〜2023。当時の 2017 は n 2723(5 分)だが、今回は表に出していない |
| 参考列 (ii)・ボラ三分位 (d)・両方/強い (f) | 比べられない(出していない) | 委任文 §2-2、INTENT_MAP X-5・X-13・X-21 |
| 第 18 部(Bybit → bitFlyer)全升 | 比べられない(測っていない) | 入力がディスクに無い(ENV_DEFECTS.md G-5) |

## 3. D-1 当時の誤り: 分の境界に乗っていない Binance の行を当時の結合が落とした(12 行)

- 違い(事実): 2018 の年と、2018 を含む期間 2018〜2021 だけが違う。5 分で当時 4,744〜4,745 / 今回 4,768〜4,769、15 分で当時 3,395〜3,396 / 今回 3,413〜3,414。2019〜2022 は design・sameclose・single の全升で一致。
- 規則の文: `XVENUE_PREREG.md` §2「揃え方」= **UTC の分**で内部結合。
- 当時の読み(規則の読み取りにだけ使った): 当時の json `load.signal.open_time_off_minute = 21521`(分の頭でない行の数)、`alignment.per_year.2018.minutes_both = 516136`。今回の `FOLD_MANIFEST.json: alignment` の 2018 の両方 = 517,326。当時のコードは時刻が秒まで同じ行だけを結合した(推定。当時のスクリプトの算術は写していない)。
- 確かめ(事実): 格子外れの行を落として畳んだ変種 `*_2018_2019_offgriddrop` を回すと、2018 が当時と同じ数になった。`diff_summary.json: variant_2018`:
  - design 5 分 [4745, 2.487] = 当時 [4745, 2.487] / design 15 分 [3396, 5.141] = 当時 [3396, 5.141]
  - sameclose 5 分 [4745, 2.754] = 当時 [4745, 2.754] / sameclose 15 分 [3396, -0.012] = 当時 [3396, -0.012](sameclose の変種は 2026-10-01 08:1x UTC に回した。run_id `1b4d6c20…`・`f8e8925e…`)
- 裁き: **当時の誤り**(規則の文「UTC の分」に対し、当時の結合は分の頭に乗らない行を落とした)。新しい環境の値が規則の文どおり。single(結合しない Binance)には D-1 が無く、全升一致したことも同じ原因と矛盾しない(推定)。

## 4. 78 升の 2022 の符号(表 (b))

`diff_summary.json: sign_2022` = 新 63 / 78 升が正、当時 `effect_binance_to_bitflyer_2022_2026.json` の 2022 も 63、当時 `effect_binance_to_bitflyer.json`(2017 から読んだ 1 本)の 2022 も 63(数が同じという事実だけ)。78 升の 2022 の行は `diff_table.md` で全部「一致」。2023 の符号(新 24 / 78)は当時と比べられない(§2)。

## 5. 判断していないこと

- D-1 の「どちらが正しいか」は規則の文で決めた。オーナー・リードが当時の結合を意図していたかは確かめていない(仮定: 規則の文が意図)。
