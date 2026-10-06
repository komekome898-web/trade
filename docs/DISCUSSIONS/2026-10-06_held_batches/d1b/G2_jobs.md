# 担当 G2(# 4・5・6・7・8・11)の本走らせ — 測定用セッションまたはこの容器がそのまま打つ形

委任文: `docs/DISCUSSIONS/2026-10-06_held_batches/DELEGATION_d1b_impl.md`。問いの立て方: `D1B_FRAMINGS.md` の # 4〜8・# 11 の行。
台本: `scripts/d1b/g2/run_g2.py`(共通部 `g2lib.py`、項目ごと `g2_item4.py`〜`g2_item11.py`)。試験: `tests/research/test_d1b_g2.py`。

行に無かった境・向き・対照は、リードの決め(2026-10-06、G2 の報告 7 への答え)で台本の中に固定した。引数で替えない。
- # 4 の比の区分 3 の境 = 前半(2015-11-29〜2019-12-07)の 1 回の離れの比の 3 分位。台本が計算し、全期間に当てる。
- # 7 の起点の前の向き = window_move(起点の前の、幅を決めたのと同じ長さの窓の値動きの符号)。前の向き 0 の起点は数えず、
  数を出す。幅の帯 3 の境 = 窓ごとに前半の数える起点の w の 3 分位。
- # 6 の対照 = 週明けの 1 時間と同じ時刻(日本時間)の、週明けでない平日(火〜金)の 1 時間。週ごとに平均して 1 件。
- # 11 の平均からの離れ = # 8 の 区切り jst_day・時間 15 分・起点 約定の値段・1 分目を除く。
- # 5 の相関 = 時刻 t ごとの日をまたいだ r(t) の表と、t の平均 r̄。
- # 4 の 1 回の離れごとの行と # 7 の起点ごとの行は git に入れない(`--records-dir`、既定 `/tmp/d1b_g2`)。

## 前に打つもの

```
cd /home/user/trade
git pull && pip install -e ".[dev]"
PYTHONPATH=src python -m pytest tests/research/test_d1b_g2.py
```

使うデータ(どれも git の中。封印の門を通して読む。USDJPY は終値・高値・安値の 3 列を読む): `backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_{2015..2023}.csv.gz`
(`scripts/w4_measure/common.py` の `load_bars`)、`backtest_data/fx_usdjpy_1m_20170801_20221231/usdjpy_1m.csv.gz`(# 6 だけ。
`common.usdjpy_ref_dataset` + `bot.bt.data.reference.load_reference`)。2023-12-17T15:00Z より後は読まない(台本が拒む)。

## 1. 件数の数え上げ(済み。この容器で 2026-10-06 に、批評家 1 回目の直しを入れた台本で打った。509 秒・最大 RSS 2.59 GB)

```
PYTHONPATH=src python3 scripts/d1b/g2/run_g2.py --mode counts --items 4,5,6,7,8,11
```

出力: `docs/RESEARCH/d1b/{4_card4,5_card5,6_card6,7_card7,8_card8,11_cards5_7_8}/COUNTS.md`・`COUNTS.json`(境の値と読みの行を含む)。

## 1b. 短い確かめ(数日。出力は必ず一時置き場に向ける)

`--out-root` の既定は git の中の `docs/RESEARCH/d1b`(表を上書きする)なので、短い確かめでは `--out-root` と `--records-dir` を
一時置き場に向ける:

```
PYTHONPATH=src python3 scripts/d1b/g2/run_g2.py --mode full --items 4,5,6,7,8,11 --lo 2020-01-08T15:00:00Z --hi 2020-01-15T15:00:00Z \
  --out-root /tmp/d1b_g2_check/out --records-dir /tmp/d1b_g2_check/rec
```

## 2. 本走らせ(値動きを計算する全期間の実行。まだ打っていない)

10 分を超えるので切り離して打つ:

```
cd /home/user/trade
PYTHONPATH=src setsid nohup python3 scripts/d1b/g2/run_g2.py --mode full --items 4,5,6,7,8,11 > /tmp/g2_full.log 2>&1 < /dev/null &
# 待つ(1 回 30 分まで。終わらなければ同じ行をもう一度、合計 3 回まで。終わりの印は最後の行「済み」、止まったら Traceback)
for k in $(seq 1 600); do grep -qE "済み$|Traceback|Error|拒否|Killed" /tmp/g2_full.log && break; sleep 3; done; tail -20 /tmp/g2_full.log
```

出力(各項目の置き場 `docs/RESEARCH/d1b/<#>_<カード>/`):

| 項目 | 表 | 事象ごとの行 |
|---|---|---|
| # 4 | `TABLES.md`・`TABLES.json` | `/tmp/d1b_g2/4_card4_episodes.csv.gz`(git の外。1 回の離れごと) |
| # 5 | `TABLES.md`・`TABLES.json`(ほかの窓の r(t) の表は JSON だけ) | なし |
| # 6 | `TABLES.md`・`TABLES.json` | `weeks.csv.gz`(282 行。週ごとの本体と対照) |
| # 7 | `TABLES.md`・`TABLES.json` | `/tmp/d1b_g2/7_card7_origins.csv.gz`(git の外。起点ごと、3 窓で約 21 万行) |
| # 8 | `TABLES.md`・`TABLES.json` | なし |
| # 11 | `TABLES.md`・`TABLES.json` | なし |

項目を分けて打ってもよい(`--items 8` など)。ただし # 11 は # 5・# 7 と # 8 の区切り 15 時を同じ起動の中で計算する。

## 見込みの時間と記憶

【推定。根拠は下の実測】合計 45〜75 分、最大 RSS 約 3 GB(4 コア・15 GB の容器)。

- 読み込み: bitFlyer の 1 分足 2015〜2023 で 4〜7 分(数え上げの起動 3 回の実測)。USDJPY(# 6)は終値・高値・安値の 3 列を門が 1 回ずつ読むので 1〜2 分(7 日の確かめで 78 秒)。
- 計算と表(作り物のデータで全期間と同じ長さの格子 4,240,800 分を作って測った。台本はリポジトリに無い(容器の一時置き場で打った)。実データではない):
  # 4 は計算 7 秒・表 6 秒、# 5 は 967 秒(時刻ごとの相関の区間。24 窓 × 3 期間の r̄ と、朝の窓の 594 時刻 × 3 期間)・表 3 秒
  (この測りの後に、朝の窓 − 窓 k の r̄ の差の区間 23 窓 × 3 期間を足したので、# 5 はさらに 10〜15 分延びる【推定】)、
  # 7 は 6 秒・5 秒、# 8 は区切り 2 本で計算 45 秒・表 20 秒 → 24 本で約 13 分。実データでは離れ・レースの長さが違うので、
  # 4・# 7 は数倍になりうる。
- 実データ 7 日の確かめ(全部の項目、批評家 1 回目の直しを入れた台本)は 136 秒。
