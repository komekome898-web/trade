# 担当 G1(# 1・# 2・# 3・# 9 の 1 分足の部分)の本走らせ — 測定用セッションまたはこの容器がそのまま打つ形

委任文: `docs/DISCUSSIONS/2026-10-06_held_batches/DELEGATION_d1b_impl.md`。問いの立て方: `D1B_FRAMINGS.md` の # 1・# 2・# 3・# 9 の行。
台本: `scripts/d1b/g1/`(共通部 `g1common.py`、項目ごと `c1_venue.py`・`c2_wick.py`・`c3_premium.py`・`c9_liq1m.py`)。試験: `tests/research/test_d1b_g1.py`。
批評家 1 回目: `docs/AUDITOR/VERDICTS/2026-10-06_d1b_g1_critic1.md`、2 回目: `docs/AUDITOR/VERDICTS/2026-10-06_d1b_g1_critic2.md`(どちらも # 9 に [止める]。直した形がこの一覧。2 回目の後の確かめはリード)。

- 上限: 1 周・各コマンド 1 回(L-718「**各束 1 周**」)。落ちたら直さずに止めて、ログをリードに渡す。
- 出力: `docs/RESEARCH/d1b/<#>_<カード>/` に RESULT*.md と result*.json(数は台本が出す)。カード 1 の走らせの記録(npz)は `data/d1b_g1/`(git の外)。
- 2023-12-17T15:00Z より後は読まない(台本が拒む)。`backtest_data/phase2_sealed/`・`docs/RESEARCH/WINDOW1/` は読まない。
- 定義はリードの決め(2026-10-06、G1 の問い 7 つへの答え)と、批評家 1 回目へのリードの応答のとおり。台本の既定がその形。
- 見込みの時間はすべて【推定】。出所 = この容器で 2026-10-06 に打った件数の数え上げの所要(下の表)と、数日の確かめの所要。並列で他の走らせがあると延びる。

## 打つ順(前の作業を待つもの)

| 項目 | 待つもの | 理由 |
|---|---|---|
| # 1 | 担当 A の `scripts/w4_measure/common.py` の変更(`usdjpy_ref_dataset(..., extend=True)`)のコミット | X を USDJPY でそろえる(ln(Binance × USDJPY) − ln bitFlyer)。2023 年の USDJPY は extend=True で読む |
| # 2 | 台本のコミット(批評家 2 回目の後) | 批評家の判断で、このまま走らせてよい |
| # 3 | 担当 A の同じ変更のコミット | 期間を 2023-12-17T15:00Z まで延ばした(extend=True)。件数の数え上げも作り直す |
| # 9 | 担当 C の境で切った走らせ直しの出力 `data/c9_run_a/rerun_quote_20230625_20231217/`(controls.csv.gz と run_meta.json)。**C の走らせ直しが終わるまで # 9 は打たない** | 対照 (ii) の起点を、境より後を読まずに作ったものに替える。件数の数え上げも作り直す。台本は controls を開く前に run_meta.json を確かめる(下の「# 9 の読む前の確かめ」) |

## 前に打つもの

```
cd /home/user/trade
git pull && pip install -e ".[dev]"
PYTHONPATH=src python -m pytest tests/research/test_d1b_g1.py
```

## 1. 件数の数え上げ

| 項目 | コマンド | 状態・所要(実測) | 出力 |
|---|---|---|---|
| # 9 | `PYTHONPATH=src python3 scripts/d1b/g1/c9_liq1m.py --counts` | **作り直す**(C の走らせ直しの後)。前の数え(4 秒)は境より後の行を読んでいた(批評家 1 回目 問 4)。ファイルの頭に印を付けた | `9_card9/COUNTS.md` |
| # 2 USD-M | `PYTHONPATH=src python3 scripts/d1b/g1/c2_wick.py --source um --counts` | 済み。142 秒 | `2_card2/COUNTS_um.md` |
| # 2 現物 | `PYTHONPATH=src python3 scripts/d1b/g1/c2_wick.py --source spot --counts` | 済み。558 秒(容器の再起動の直後) | `2_card2/COUNTS_spot.md` |
| # 3(1 件 = onset、主) | `PYTHONPATH=src python3 scripts/d1b/g1/c3_premium.py --counts` | **作り直す**(A のコミットの後)。前の数え(353 秒)は 2022 年末まで | `3_card3/COUNTS_outside_onset_last1m.md` |
| # 3(every、件数だけ並べる) | `PYTHONPATH=src python3 scripts/d1b/g1/c3_premium.py --counts --event every` | 同上(前の数え 338 秒) | `3_card3/COUNTS_outside_every_last1m.md` |
| # 1 | `PYTHONPATH=src python3 scripts/d1b/g1/c1_venue.py --counts --cache data/d1b_g1/c1_run.npz` | 済み。1,192 秒(カードの走らせ。年あたり 178〜197 秒)。npz `data/d1b_g1/c1_run.npz` はこの容器だけ。合図の数は USDJPY の直しで変わらない | `1_card1/COUNTS.md` |

## 2. 本走らせ

| # | どこで | コマンド(リポジトリの直下で) | 見込みの時間【推定】 |
|---|---|---|---|
| 1 | 測定用セッション(データは git の中)。A のコミットの後 | `PYTHONPATH=src python3 scripts/d1b/g1/c1_venue.py --cache data/d1b_g1/c1_run.npz` | npz があれば 10〜20 分(Binance の始値・終値と USDJPY 6.4 年の読み込み + 戻るまでの分。3 日の確かめは 65 秒)。npz が無ければ(測定用セッション)先にカードを走らせるので +約 20 分(件数の数え上げの実測 1,192 秒) |
| 2 | 測定用セッション | `PYTHONPATH=src python3 scripts/d1b/g1/c2_wick.py --source um` | 10〜15 分(USD-M 4 本値 136〜300 秒 + bitFlyer の足 4 年 + 表 144 個) |
| 2 | 測定用セッション | `PYTHONPATH=src python3 scripts/d1b/g1/c2_wick.py --source spot` | 15〜25 分(現物 4 本値 529 秒 + bitFlyer の足 6.4 年 + 表 144 個) |
| 3 | 測定用セッション。A のコミットの後。期間 2017-08-17T15:00Z〜2023-12-17T15:00Z。USDJPY の脚は as-of のまま(カードの定義)で、古さが 1 分を越えた件の数を表に出す | `PYTHONPATH=src python3 scripts/d1b/g1/c3_premium.py`(= `--edge outside --event onset --cause last1m`。`--event every` は件数だけで、本走らせでは台本が拒む) | 12〜25 分(読み込みと上乗せ 350 秒に 2023 年分 + 表 720 個) |
| 9 | **この容器**(下の理由)。C の走らせ直しの後 | `PYTHONPATH=src python3 scripts/d1b/g1/c9_liq1m.py`(= `--binance coinm,spot --controls data/c9_run_a/rerun_quote_20230625_20231217/controls.csv.gz`、期間 2023-06-25T00:00Z〜2023-12-17T00:00Z。COIN-M の約定から作る 1 分足が主、現物の 1 分足を並べる。出力 `RESULT_coinm.md`・`RESULT_spot.md`) | 3〜10 分(前の 3 日の確かめで両方合わせて 41 秒。半年分の読み込みが主)。直した後の短い確かめは打っていない(境より後を読むため、リードの指示) |

- **# 9 の読み口と失う時間**: 清算と COIN-M の約定は、担当 C の境で切った読み口 `data/c9_run_a/cut_root_20231216`(2023-12-16 までの UTC の日次 zip へのリンク、C の `make_cut_root.py` が作る)から読む。2023-12-17 の zip(境 15:00Z の後の行を含む)に触れないので、**2023-12-17 の 00:00〜15:00Z の清算・約定は失う**(日本時間の最後の日 2023-12-17 は 0〜9 時だけ)。この印は出力の頭にも出る。台本は終わりが 2023-12-17T00:00Z を越えれば、何も開かずに拒む。
- **# 9 を「どこで測るか」の列(測定用セッション)と違ってこの容器で打つ理由**(リードの決め 7): 対照 (ii) の起点(担当 C の走らせ直しの出力)と、主の値段を作る COIN-M の約定(境で切った読み口のリンク先 `backtest_data/binance_cm_o3c_20260913/aggTrades/`)が、どちらも git の外でこの容器にしか無いため。
- **# 9 の読む前の確かめ**(台本が行う。欠ければ止まる):
  1. C の `run_meta.json` の「期間」(`scripts/c9_run_a.py` の `[args.start, args.end]`)の終わりが 2023-12-17 以前。
  2. 同じ `run_meta.json` の「約定の欠けた日(窓の中)」に 2023-12-17 が入っている(= 境で切った読み口で走らせた。元の置き場なら 2023-12-17 の約定は欠けない)。
  3. 1・2 を確かめてから controls.csv.gz を開く。起点が 2023-12-17T15:00Z 以降の行があれば、落とさずに止まる。2023-12-17 の 00:00〜15:00Z の起点は残し、値動き・相関は足が無いので NaN として数える(件数を出力の頭に書く)。
  4. C の `chunks/meta/<日>.json` の `prints`(その UTC の日の全部のプリントの数)と、台本の UTC の日ごとの清算の数を照らし、1 日でも違えば止まる(ref_id と print_id の照らしの前提)。
  5. `ref_id`(C の (ii) の行では、その対照を求めた清算の `print_id`。`c9_run_a.py` の `add_ctrl`)に入る行だけを使い、入らなかった件数を出力の頭に書く。
- 10 分を超えるものは切り離して打つ(例: `setsid nohup <コマンド> > data/d1b_g1/<名前>.log 2>&1 < /dev/null &`)。
- # 1 の bitFlyer の損益は、台本の中で測定器の `pnl` と一致することを確かめてから書く(合わなければ止まる)。
