# 走らせ直しの一覧 — 担当 B(カード 4)

- 委任文: `docs/DISCUSSIONS/2026-10-06_held_batches/DELEGATION_rerun_impl.md`(担当 B: カード 4)
- 中身(委任文の表): 「利確を中心から測る形(中心 4:3)の良い側・悪い側を、取引の行(決まらない足・出の理由)を出す形で」2 本
- 元の文書: `docs/ANALYSIS/2026-10-05_card4_matilda.md` D10「走らせ直しの一覧に足すもの」(「A1_center_4_3 の良い側・悪い側を、`trades.csv.gz`(取引ごとの決まらない足・出の理由・比の列つき)を出す形で走らせ直す(families_r2 と同じ引数。v37 は `c4rerun/` で済み)」)
- 台本の直し: **無し**。`scripts/w4_measure/c4_limit_run.py` は既定で `trades.csv.gz` に `undecided`・`exit_reason`・`ratio` の列を書く(元の走らせはその `trades.csv.gz` を git に入れなかっただけ)。新しい引数は足していない。

## 走らせる前に(リポジトリの直下で)

```
PYTHONPATH=src python -m pytest tests/research/test_matilda_limit_sim.py
```

全部通ることを確かめる(`test_run_script_default_outputs_are_unchanged` が `c4_limit_run.py` の既定の出力の指紋を検める)。担当 A が `scripts/w4_measure/common.py` などを変えたコミットの後に走らせるときも、これを打ってから走らせる。短い期間の確かめはコミット 4395b5e0 で行った(着手の時点は 7a22ab48。`git diff --stat 7a22ab48 4395b5e0 -- src scripts tests` は空)。

## 走らせ(1 行 = 1 本)

| # | コマンド(リポジトリの直下で) | 出力先 | 見込みの時間 |
|---|---|---|---|
| 1 | `PYTHONPATH=src python3 scripts/w4_measure/c4_limit_run.py --fill-side good --out docs/RESEARCH/cards/c4_owner_matilda_range/limit_sim/rerun_2026-10-06/A1_center_4_3_good --exit-form center --entry 4 --exit-setting 3 && PYTHONPATH=src:scripts/w4_measure python3 -c "import c4_limit_batch; c4_limit_batch.analyse('docs/RESEARCH/cards/c4_owner_matilda_range/limit_sim/rerun_2026-10-06/A1_center_4_3_good')"` | `docs/RESEARCH/cards/c4_owner_matilda_range/limit_sim/rerun_2026-10-06/A1_center_4_3_good/` | 約 5.5 分(元の走らせ 314.5 秒・最大 RSS 1.45 GB)+ `analyse` 十数秒 |
| 2 | `PYTHONPATH=src python3 scripts/w4_measure/c4_limit_run.py --fill-side bad --out docs/RESEARCH/cards/c4_owner_matilda_range/limit_sim/rerun_2026-10-06/A1_center_4_3_bad --exit-form center --entry 4 --exit-setting 3 && PYTHONPATH=src:scripts/w4_measure python3 -c "import c4_limit_batch; c4_limit_batch.analyse('docs/RESEARCH/cards/c4_owner_matilda_range/limit_sim/rerun_2026-10-06/A1_center_4_3_bad')"` | `docs/RESEARCH/cards/c4_owner_matilda_range/limit_sim/rerun_2026-10-06/A1_center_4_3_bad/` | 約 5.5 分(元の走らせ 318.9 秒・最大 RSS 1.41 GB)+ `analyse` 十数秒 |

- 上限: 1 周・2 本・合わせて約 15 分(L-718「**各束 1 周**」)。下の検めで 1 つでも違えば止めて報告する。
- 見込みの時間は【推定】: 元の走らせの run_record の値。短い期間の確かめ(区切り 1 だけ)は 9.1 秒で、元の区切り 1 の 7.0 秒より 3 割ほど遅かった。
- 2 本は同時に走らせてよい(合わせて最大 RSS 約 3 GB)。
- 期間は既定(2015-11-28T15:00Z〜2023-12-17T15:00Z。封印の門 `common.load_bars` が 2023-12-18 より後を拒む)。`--start`・`--end` は付けない。
- 出るもの: `trades.csv.gz`(列 entry_t・exit_t・side・levels・entry_price・exit_price・exit_reason・pnl_bp・undecided・width・vola・ratio・brk・close_k)・`trades.json.gz`・`summary.json`・`run_record.json`、`analyse` の `analysis.json`。`trades.csv.gz` の大きさの見込みは 良い側 約 20 MB・悪い側 約 14 MB【推定: 短い期間の 651 行で 28,208 バイト、v37 の 1,178,542 行で 51,325,733 バイト = 1 行 約 43 バイト × 取引の数 467,800・324,589】。git に入れるかは決まっていない(報告の問い)。
- `analyse` の `c4_limit_batch.analyse` は import して呼ぶだけ(写さない)。families_r2 の `analysis.json` を作った関数と同じ。

## 走らせの後の検め(元の走らせの再現)

元 = `docs/RESEARCH/cards/c4_owner_matilda_range/limit_sim/families_r2/A1_center_4_3_<側>/`。2 本それぞれで、`<側>` を good・bad に替えて打つ。

```
N=docs/RESEARCH/cards/c4_owner_matilda_range/limit_sim/rerun_2026-10-06/A1_center_4_3_good
O=docs/RESEARCH/cards/c4_owner_matilda_range/limit_sim/families_r2/A1_center_4_3_good
cmp $N/summary.json $O/summary.json && echo "summary.json 同一"
cmp $N/analysis.json $O/analysis.json && echo "analysis.json 同一"
PYTHONPATH=src python3 -c "from bot.research.trade_record import read_trades_json as r; print('trades.json.gz 同一', r('$N/trades.json.gz') == r('$O/trades.json.gz'))"
python3 -c "import json; a=json.load(open('$N/run_record.json')); b=json.load(open('$O/run_record.json')); print({k: a[k] == b[k] for k in ('params','period','chunks','inputs','trades','undecided_bars_total')})"
```

全部が同一 / True なら、取引の行は元の走らせと同じ取引に列を足したもの。1 つでも違えば、その走らせは元の走らせの再現ではないので読まずに止めて報告する。

この検めが効くことの確かめ(2026-10-06): v37 の走らせ直し(前の会話の一時置き場 `c4rerun/v37_good`・`v37_bad`)で、`summary.json` は families_r2 の v37 と同一、`run_record.json` の上の 6 つの鍵も同一、その `trades.csv.gz` に `analyse` を当てた `analysis.json` も families_r2 の v37 と同一だった。

## 得られるもの・得られないもの(D10 の写し)

得られるもの: 「D8 で止める組の代表について、仮定に左右されない部分の区間と前半・後半(スキル D1 の「3 本で並べる」の 3 本目)、出の理由ごとの区間」。得られないもの: 「損益の符号(仮定次第のまま)」。
